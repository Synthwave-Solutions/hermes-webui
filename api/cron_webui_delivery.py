"""WebUI-side delivery bridge for cron jobs created in WebUI conversations.

Root cause this module fixes: a cron job created inside a Hermes WebUI
conversation is stamped with ``origin = {platform: "webui", chat_id:
<webui session id>}``, but the engine's ``cron.scheduler._deliver_result``
only knows gateway platforms (telegram, slack, google_chat, ...). A
``deliver=origin`` run therefore fails with ``unknown platform 'webui'`` (or
is skipped entirely), the failure only lands in the job's
``last_delivery_error`` field, and ``last_status`` stays ``ok`` - so the run
looks healthy while the user never receives the update in the conversation
that scheduled it (scheduler-delivery / polling-completion-update tickets,
reported 2026-08-26; evidence: job ccb3ea157bc7 run 15:46 CEST with
``last_delivery_error: "unknown platform 'webui'"``).

The engine cannot reach WebUI sessions (they are JSON sidecars owned by this
server), so the bridge lives here:

  * A daemon thread polls the active profile's ``cron/jobs.json`` (read-only,
    no engine imports, no cron locks) for jobs whose origin is a WebUI
    session and whose ``last_run_at`` advanced past the per-job watermark in
    the delivery ledger.
  * For each newly completed run it posts ONE concise assistant update into
    the originating WebUI conversation (sidecar append + ``session-updated``
    SSE frame so an open tab re-syncs incrementally), honouring the engine's
    ``[SILENT]`` suppression contract.
  * The outcome is recorded in a persistent ledger, SEPARATE from the
    engine's run status, so "ran ok but was never delivered" is a visible,
    distinct state (surfaced via ``delivery_state_for_job`` in
    ``/api/crons/recent``).
  * A duplicate-run refusal never advances ``last_run_at``, so the watermark
    is untouched and the NEXT completed run still delivers - a refused run
    cannot swallow the following update.

Delivery scope: jobs whose ``deliver`` value resolves to the origin (or that
fell back to ``local`` because WebUI has no gateway channel) get the run
output posted. Jobs that deliver to an external platform are not mirrored,
but an external delivery FAILURE recorded by the engine is posted into the
originating conversation as an actionable notice.

Bot-owned jobs (18 Oct 2026, api/cron_bots.py): the bridge reads every
bot's cron store, and a run's result goes to a chat of the bot that owns the
job: the chat it was created in while that chat belongs to the bot, else the
job's own chat ("🗓️ <name>") of the person it runs for, opened on its first
result. Jobs made outside the WebUI only take part once their person turned
their notifications on in the Tasks panel (``_bridge_scope``).

Per-job notify settings (plan 3.1): the job's ``notify.delivery`` level gates
every post, as the engine gates its own delivery. ``failures`` mutes the post
of a successful run, ``off`` mutes every post; a muted run is recorded as
``suppressed_muted`` and reported as ``muted``. A silent run (``[SILENT]``,
or a monitor tick with no change) posts nothing, whatever the level. Until
the engine records muted and silent outcomes itself (its ``mark_job_run``
taking ``delivery_outcome``), the WebUI's Run now records them in this ledger
too (``record_run_outcome``), so the Tasks panel shows "Muted" instead of
"Delivered" for those runs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from api._notify_policy_fallback import OUTCOME_MUTED as _POLICY_OUTCOME_MUTED

logger = logging.getLogger(__name__)

LEDGER_FILENAME = "cron_webui_delivery.json"

# Seconds between bridge polls. Cron cadences are minutes-grained, so a low
# tens-of-seconds poll keeps conversation delivery prompt without measurable
# load (the tick is one small JSON read when nothing changed).
POLL_INTERVAL = int(os.environ.get("HERMES_WEBUI_CRON_DELIVERY_POLL_INTERVAL", "15") or 15)

# A run that finished more than this many seconds before the bridge first
# sees the job is treated as historical: the watermark is initialized without
# posting, so enabling the bridge (or a long server outage) does not flood
# conversations with stale updates. Fresh restarts are covered by the
# persisted ledger, which survives the process.
FRESH_RUN_WINDOW_SECS = int(
    os.environ.get("HERMES_WEBUI_CRON_DELIVERY_FRESH_WINDOW", "900") or 900
)

# Cap for the response body posted into the conversation. Full output stays
# available in the Tasks panel (cron output files); the conversation gets the
# concise update the tickets ask for.
MAX_DELIVERY_CHARS = 6000

_ledger_lock = threading.Lock()

# In-memory watermark of runs handled during this process lifetime, keyed
# job_id -> ledger entry. It is merged OVER the disk ledger on every tick
# (memory wins), so neither a persistently unwritable state dir nor a ledger
# corrupted on disk can forget a delivery this process already made. Without
# it, a failed ledger write would re-post the same update every poll tick.
# Mutated only under _ledger_lock; read sites take an atomic dict() snapshot.
_MEMORY_WATERMARKS: dict[str, dict] = {}

_BRIDGE_THREAD: Optional[threading.Thread] = None
_BRIDGE_STOP = threading.Event()
_BRIDGE_LIFECYCLE_LOCK = threading.Lock()

# Delivery outcomes recorded in the ledger. "failed" carries an error string.
OUTCOME_DELIVERED = "delivered"
OUTCOME_FAILED = "failed"
OUTCOME_SILENT = "suppressed_silent"
OUTCOME_SKIPPED_EXTERNAL = "skipped_external"
OUTCOME_EXTERNAL_FAILED = "external_delivery_failed"
OUTCOME_SKIPPED_STALE = "skipped_stale"
# The job's notify.delivery level muted the run (the engine's own value).
OUTCOME_MUTED = _POLICY_OUTCOME_MUTED

# Outcomes the WebUI's Run now may record for a run (record_run_outcome).
RUN_NOW_OUTCOMES = frozenset({OUTCOME_MUTED, OUTCOME_SILENT})


# -- Ledger ------------------------------------------------------------------

def _ledger_path() -> Path:
    from api import config as _cfg

    return Path(_cfg.STATE_DIR) / LEDGER_FILENAME


def _load_ledger_state() -> tuple[dict, bool]:
    """Load the delivery ledger; returns ``(ledger, corrupt)``.

    ``corrupt`` is True only when a ledger file EXISTS but cannot be parsed:
    a genuinely missing file is a first boot, not corruption. The bridge tick
    uses the flag to fall back to watermark-only first sightings, so a wiped
    or garbled ledger never replays runs inside the fresh window.
    """
    try:
        raw = _ledger_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"jobs": {}}, False
    except Exception:
        logger.warning("cron delivery ledger unreadable; starting fresh", exc_info=True)
        return {"jobs": {}}, True
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("jobs"), dict):
            return data, False
    except Exception:
        logger.warning("cron delivery ledger unreadable; starting fresh", exc_info=True)
        return {"jobs": {}}, True
    logger.warning("cron delivery ledger has unexpected shape; starting fresh")
    return {"jobs": {}}, True


def load_ledger() -> dict:
    """Load the delivery ledger; a missing or corrupt file yields a fresh one."""
    ledger, _corrupt = _load_ledger_state()
    return ledger


def _save_ledger(ledger: dict) -> None:
    from api.paths import _atomic_write_text

    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(ledger, indent=1, default=str))


def _record_outcome(
    ledger: dict,
    job: dict,
    *,
    outcome: str,
    error: str | None = None,
    session_id: str | None = None,
    profile: str | None = None,
    target: str | None = None,
) -> None:
    entry = {
        "run_at": job.get("last_run_at"),
        "outcome": outcome,
        "error": error,
        "session_id": session_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    if profile is not None:
        entry["profile"] = profile
    if target is not None:
        entry["target"] = target
    ledger.setdefault("jobs", {})[str(job.get("id", ""))] = entry


def _record_and_persist(
    ledger: dict,
    job: dict,
    *,
    outcome: str,
    error: str | None = None,
    session_id: str | None = None,
    profile: str | None = None,
    target: str | None = None,
) -> bool:
    """Record the outcome in the ledger, the in-memory watermark AND on disk.

    Returns True when the disk write succeeded. A failed write is deliberate
    best-effort: the in-memory watermark already holds the entry, so even a
    persistently unwritable state dir cannot re-post the same run on later
    ticks; at worst a process restart with a still-broken disk re-posts once.
    """
    _record_outcome(ledger, job, outcome=outcome, error=error, session_id=session_id,
                    profile=profile, target=target)
    job_id = str(job.get("id", ""))
    _MEMORY_WATERMARKS[job_id] = dict(ledger["jobs"][job_id])
    try:
        _save_ledger(ledger)
        return True
    except Exception:
        logger.warning(
            "cron delivery ledger write failed; in-memory watermark still "
            "guards job %s against re-posting", job_id, exc_info=True,
        )
        return False


# -- Job classification ------------------------------------------------------

def _webui_origin_session_id(job: dict) -> str | None:
    """Return the originating WebUI session id, or None for non-WebUI jobs."""
    origin = job.get("origin")
    if not isinstance(origin, dict):
        return None
    if str(origin.get("platform") or "").strip().lower() != "webui":
        return None
    chat_id = str(origin.get("chat_id") or "").strip()
    if not chat_id:
        return None
    try:
        from api.models import is_safe_session_id

        if not is_safe_session_id(chat_id):
            return None
    except Exception:
        return None
    return chat_id


def _has_explicit_notify(job: dict) -> bool:
    notify = job.get("notify")
    return isinstance(notify, dict) and bool(notify.get("delivery"))


def _bridge_scope(job: dict) -> str | None:
    """Which jobs this bridge reports into a chat of the owning bot.

    ``webui``: every job made in the WebUI (a chat or the Tasks panel), as
    before; a Tasks panel job has no originating chat and now gets its job
    chat. ``owner``: a job made elsewhere (CLI, Telegram, imported) whose
    person turned on its notifications in the Tasks panel (an explicit
    ``notify.delivery``) and who can be named (api/cron_bots.job_person_email).
    Everything else stays where it was: Telegram-made jobs answer in Telegram.
    """
    origin = job.get("origin")
    if isinstance(origin, dict) and str(origin.get("platform") or "").strip().lower() == "webui":
        return "webui"
    if _has_explicit_notify(job) and str(job.get("owner_email") or "").strip():
        return "owner"
    return None


def _deliver_tokens(job: dict) -> list[str]:
    raw = job.get("deliver")
    if raw is None:
        return []
    return [p.strip().lower() for p in str(raw).split(",") if p.strip()]


def _job_wants_webui_delivery(job: dict) -> bool:
    """True when the run output belongs in the originating WebUI conversation.

    An empty ``deliver`` defaults to origin engine-side; ``origin`` is the
    explicit form. ``local`` is included deliberately: agents pick ``local``
    for WebUI-created jobs exactly because the engine cannot deliver to
    ``webui``, and the originating conversation is the only surface the user
    ever sees (the scheduler-delivery ticket's lost one-shot reminders were
    all ``deliver=local`` WebUI-origin jobs).
    """
    tokens = _deliver_tokens(job)
    if _bridge_scope(job) == "owner":
        # A job from a messaging platform delivers "origin" (or nothing) to
        # that platform; only its saved-locally runs are the chat's to post.
        origin = job.get("origin")
        has_platform = isinstance(origin, dict) and bool(origin.get("platform"))
        return "local" in tokens or (not tokens and not has_platform)
    if not tokens:
        return True
    return "origin" in tokens or "local" in tokens


# -- Output extraction -------------------------------------------------------

_SILENCE_TOKENS = frozenset({"[silent]", "silent", "no_reply", "no reply"})


def _is_silent_response(text: str) -> bool:
    """Mirror the engine's cron silence contract without importing the engine.

    Suppress when a silence token is the whole response or its own first or
    last line; a token buried mid-sentence is real content (parity with
    ``cron.scheduler._is_cron_silence_response``).
    """
    stripped = (text or "").strip()
    if not stripped:
        return False
    if stripped.lower() in _SILENCE_TOKENS:
        return True
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not lines:
        return False
    return lines[0].lower() in _SILENCE_TOKENS or lines[-1].lower() in _SILENCE_TOKENS


# A monitor tick whose source did not change writes a run record without a
# Response section: "**Status:** no_change (agent run suppressed)". Its final
# response is the engine's silence marker, so it is a silent run.
_MONITOR_NO_CHANGE_RE = re.compile(r"^\*\*Status:\*\*\s*no_change\b", re.MULTILINE)


def _has_response_heading(text: str) -> bool:
    return any(
        line.startswith("## Response") or line.startswith("# Response")
        for line in (text or "").split("\n")
    )


def output_is_silent(text: str) -> bool:
    """Whether a cron output file records a silent run: its response is a
    silence token, or it is a monitor tick with no change (no response)."""
    if text is None:
        return False
    if _is_silent_response(_extract_response_body(text)):
        return True
    return not _has_response_heading(text) and bool(_MONITOR_NO_CHANGE_RE.search(text))


def _extract_response_body(text: str) -> str:
    """Return the agent response from a cron output .md file.

    Contract shared with ``routes._cron_output_snippet``: front matter is
    followed by a ``## Response`` (or ``# Response``) heading; everything
    after it is the reply. Without the heading the whole text is returned.
    """
    lines = (text or "").split("\n")
    response_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("## Response") or line.startswith("# Response"):
            response_idx = i
            break
    body = ("\n".join(lines[response_idx + 1:]) if response_idx >= 0 else "\n".join(lines))
    return body.strip()


def latest_output_text(
    job_output_dir: Path, run_dt: Optional[datetime] = None
) -> str | None:
    """Read the newest output file in *job_output_dir* (one job's output
    directory), or None.

    When *run_dt* is known, an output file written long before the run is
    rejected so an errored run that produced no file cannot repost an earlier
    run's body.
    """
    out_dir = Path(job_output_dir)
    try:
        files = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for f in files[:1]:
        if run_dt is not None:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime < run_dt - timedelta(hours=1):
                    return None
            except OSError:
                return None
        try:
            return f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            logger.debug("cron delivery bridge: unreadable output file %s", f)
    return None


# -- Message building --------------------------------------------------------

def _truncate_body(body: str) -> str:
    if len(body) <= MAX_DELIVERY_CHARS:
        return body
    return body[:MAX_DELIVERY_CHARS].rstrip() + "\n\n(truncated: full output is in the Tasks panel)"


def capacity_failure_text(job: dict, run_error: str | None) -> str | None:
    """Plain-language update when a run failed because upstream capacity ran out.

    Reported 27 Aug 2026 ("Telegram alerts do not work when all upstream
    accounts are unavailable"): when every upstream account is spent, the run
    that would have produced the alert cannot run either, and the user was left
    with either silence or a raw provider error. The scheduled task now reports
    the outage in its own words, an administrator is alerted, and the message
    says an admin was notified only when that alert was actually recorded.
    Returns None when the failure was not a capacity failure.
    """
    try:
        from api.capacity_alerts import record_capacity_event, user_facing_message
        from api.streaming import _classify_provider_error
    except Exception:
        return None
    try:
        classification = _classify_provider_error(str(run_error or ""), None,
                                                  silent_failure=not bool(run_error))
        if classification.get("category") != "capacity":
            return None
        outcome = record_capacity_event(
            classification.get("type"),
            provider=job.get("provider") or job.get("provider_snapshot"),
            model=job.get("model") or job.get("model_snapshot"),
            detail=str(run_error or "")[:500],
            source="scheduled task",
        )
        name = str(job.get("name") or job.get("id") or "scheduled task")
        message = user_facing_message(classification.get("type"),
                                      notified=bool(outcome.get("notified")))
        return (
            f"Scheduled task \"{name}\" could not run. {message}\n"
            f"The task stays scheduled and will run again on its next turn "
            f"(job {job.get('id', '?')})."
        )
    except Exception:
        logger.debug("capacity failure text unavailable", exc_info=True)
        return None


def deliver_external_notice(destination: str, text: str) -> tuple[bool, str | None]:
    """Send one short notice to an external destination (platform:chat_id).

    Used by api/capacity_alerts.py to reach an administrator outside the WebUI.
    Returns (ok, error) and never claims a send it cannot confirm: an
    unavailable backend is reported as an error, not as success.
    """
    destination = str(destination or "").strip()
    if not destination:
        return False, "no destination configured"
    try:
        from tools.send_message_tool import send_message_tool  # type: ignore
    except Exception:
        return False, "external delivery backend unavailable"
    try:
        response = send_message_tool({"action": "send", "target": destination, "message": text})
        result = json.loads(response) if isinstance(response, str) else response
        ok = isinstance(result, dict) and result.get("success") is True and not result.get("skipped")
        return ok, None if ok else "external delivery not confirmed"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def build_update_text(job: dict, *, body: str | None, run_ok: bool, run_error: str | None) -> str:
    """One concise update for the originating conversation."""
    name = str(job.get("name") or job.get("id") or "scheduled task")
    if not run_ok:
        capacity_text = capacity_failure_text(job, run_error)
        if capacity_text is not None:
            return capacity_text
        detail = (run_error or "no error detail recorded").strip()
        return (
            f"Scheduled task \"{name}\" failed on its last run: {detail}\n"
            f"Details are in the Tasks panel (job {job.get('id', '?')})."
        )
    if body:
        return f"Scheduled task update: {name}\n\n{_truncate_body(body)}"
    return (
        f"Scheduled task \"{name}\" completed its run. No output was captured; "
        f"see the Tasks panel (job {job.get('id', '?')}) for the run record."
    )


def build_external_failure_text(job: dict, delivery_error: str) -> str:
    name = str(job.get("name") or job.get("id") or "scheduled task")
    target = str(job.get("deliver") or "its configured target")
    return (
        f"Scheduled task \"{name}\" ran, but delivering its result to {target} "
        f"failed: {delivery_error.strip()}\n"
        f"The output is saved in the Tasks panel (job {job.get('id', '?')}). "
        f"Fix the delivery target or ask me to resend it."
    )


# -- Conversation delivery ---------------------------------------------------

def deliver_update_to_session(
    session_id: str, text: str, job: dict, *, profile: str | None = None,
) -> tuple[bool, str | None]:
    """Append one assistant update to the WebUI session and notify open tabs.

    ``profile`` is the owning bot; it rides on the message so a follow-up in
    that chat finds the job (api/cron_bots.job_refs_for_session). Returns
    (ok, error). Never raises.
    """
    try:
        from api.models import get_session

        session = get_session(session_id)
    except KeyError:
        return False, f"originating session {session_id} not found"
    except Exception as exc:
        return False, f"failed to load originating session {session_id}: {exc}"
    if session is None:
        return False, f"originating session {session_id} not found"
    try:
        session.messages.append(
            {
                "role": "assistant",
                "content": text,
                "timestamp": time.time(),
                "cron_delivery": {
                    "job_id": job.get("id"),
                    "job_name": job.get("name"),
                    "run_at": job.get("last_run_at"),
                    "profile": profile,
                    "status": str(job.get("last_status") or "ok"),
                },
            }
        )
        session.save()
    except Exception as exc:
        return False, f"failed to persist update into session {session_id}: {exc}"

    # Live view: an open tab re-syncs incrementally on the session-updated
    # frame (same frame the per-session SSE self-heal path uses). Closed tabs
    # pick the message up from the sidecar on next load.
    try:
        from api.background_process import get_session_channel

        ch = get_session_channel(session_id)
        if ch is not None:
            ch.emit(
                "session-updated",
                {
                    "session_id": session_id,
                    "message_count": len(session.messages),
                    "source": "cron_delivery",
                },
            )
    except Exception:
        logger.debug("cron delivery bridge: session-updated emit failed", exc_info=True)
    try:
        from api.session_events import publish_session_list_changed

        publish_session_list_changed("cron_delivery", session_id=session_id)
    except Exception:
        logger.debug("cron delivery bridge: session list publish failed", exc_info=True)
    return True, None


# -- Core tick ---------------------------------------------------------------

def _parse_run_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


parse_run_at = _parse_run_at


# -- Notify settings (plan 3.1) ---------------------------------------------

def _notify_policy():
    """The notify policy without importing the engine from this thread."""
    try:
        from api.cron_notifications import notify_policy

        return notify_policy(import_engine=False)
    except Exception:
        from api import _notify_policy_fallback

        return _notify_policy_fallback


def _notify_mutes(job: dict, *, success: bool) -> bool:
    """True when the job's ``notify.delivery`` level mutes a post about a
    run that succeeded (``success``) or failed. Jobs without notify deliver
    everything, as before."""
    policy = _notify_policy()
    status = str(job.get("last_status") or "").strip().lower()
    alert_kind = status if status in policy.ALERT_KINDS else None
    try:
        deliver, _outcome = policy.should_deliver(job, success=success, alert_kind=alert_kind)
    except Exception:
        logger.debug("cron delivery bridge: notify policy failed for %s", job.get("id"), exc_info=True)
        return False
    return not deliver


def _engine_muted(job: dict) -> bool:
    """The engine recorded that its notify gate muted this run (E1)."""
    return str(job.get("last_delivery_outcome") or "") == OUTCOME_MUTED


def _load_jobs_from_home(home: Path) -> list[dict]:
    """Read cron jobs from *home* without engine imports or cron locks."""
    path = Path(home) / "cron" / "jobs.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception:
        logger.debug("cron delivery bridge: unreadable jobs file %s", path, exc_info=True)
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else data
    return [jb for jb in jobs if isinstance(jb, dict)] if isinstance(jobs, list) else []


def _active_hermes_home() -> Path:
    try:
        from api.profiles import get_active_hermes_home

        return Path(get_active_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _session_busy(session_id: str) -> bool:
    """True while a live agent turn owns the session transcript."""
    try:
        from api.background_process import _session_has_active_turn

        return _session_has_active_turn(session_id)
    except Exception:
        return False


# -- Where a result goes (bot-owned jobs, 18 Oct 2026) ----------------------

TARGET_ORIGIN = "origin"
TARGET_JOB_CHAT = "job_chat"


def _load_session_quiet(session_id: str):
    try:
        from api.models import get_session

        return get_session(session_id, metadata_only=True)
    except Exception:
        return None


def _resolve_target(job: dict, profile: str, *, create: bool) -> dict:
    """The chat a job's result belongs in, inside its owning bot ``profile``.

    The chat the job was created in, while it exists and belongs to that bot;
    otherwise the job chat of the job's person (api/cron_bots.py), made only
    when ``create`` (the moment there is something to post). Returns
    ``{"session_id", "kind", "error"}``; ``session_id`` is None when there is
    nowhere to post yet (no job chat made so far) or nowhere at all
    (``error`` set: no chat and nobody to make one for).
    """
    from api import cron_bots

    origin_sid = _webui_origin_session_id(job)
    origin_session = _load_session_quiet(origin_sid) if origin_sid else None
    if origin_session is not None and cron_bots.session_serves_bot(origin_session, profile):
        return {"session_id": origin_sid, "kind": TARGET_ORIGIN, "error": None}
    person = cron_bots.job_person_email(job)
    if not person:
        if origin_sid:
            return {"session_id": None, "kind": TARGET_ORIGIN,
                    "error": f"originating session {origin_sid} not found"}
        return {"session_id": None, "kind": TARGET_JOB_CHAT,
                "error": "nobody to report this task to"}
    sid = cron_bots.find_job_chat(job.get("id"), profile, person)
    if sid is None and create:
        try:
            sid, _created = cron_bots.ensure_job_chat(job, profile, person)
        except Exception as exc:
            logger.warning("cron delivery bridge: job chat for %s not created", job.get("id"), exc_info=True)
            return {"session_id": None, "kind": TARGET_JOB_CHAT,
                    "error": f"could not open the task chat: {exc}"}
    return {"session_id": sid, "kind": TARGET_JOB_CHAT, "error": None}


def _store_homes() -> list[tuple[str, Path]]:
    try:
        from api.cron_bots import store_homes

        return store_homes()
    except Exception:
        logger.debug("cron delivery bridge: store listing failed; active store only", exc_info=True)
        home = _active_hermes_home()
        from api.cron_bots import profile_for_home

        return [(profile_for_home(home), home)]


def process_jobs_once(
    jobs: list[dict] | None = None,
    *,
    home: Path | None = None,
    now: datetime | None = None,
    profile: str | None = None,
) -> list[dict]:
    """Run one bridge pass; returns a list of action records (for tests/logs).

    Without ``jobs`` and ``home`` every bot's cron store is read (each job's
    result goes to a chat of the bot that owns it). With ``home`` only that
    store; with ``jobs`` those rows, owned by ``profile`` (default: the
    profile of ``home``).

    Each record: {"job_id", "outcome", "error", "session_id", "profile",
    "target"}. Jobs skipped because nothing changed produce no record.
    """
    from api.cron_bots import normalize_profile, profile_for_home

    if jobs is not None or home is not None:
        resolved_home = Path(home) if home is not None else _active_hermes_home()
        owner = normalize_profile(profile) if profile else profile_for_home(resolved_home)
        batches = [(owner, resolved_home, jobs if jobs is not None else _load_jobs_from_home(resolved_home))]
    else:
        batches = [(name, store, _load_jobs_from_home(store)) for name, store in _store_homes()]
    now_dt = now or datetime.now(timezone.utc)

    actions: list[dict] = []
    with _ledger_lock:
        ledger, ledger_corrupt = _load_ledger_state()
        # Memory wins over disk: the in-memory watermark holds every run this
        # process already handled, so a corrupt or write-failed disk ledger
        # cannot resurrect an already-delivered run within this process.
        jobs_map = ledger.setdefault("jobs", {})
        for jid, entry in _MEMORY_WATERMARKS.items():
            jobs_map[jid] = dict(entry)
        for owner, store, store_jobs in batches:
            for job in store_jobs:
                action = _process_one_job(
                    job, ledger, store, now_dt, ledger_corrupt=ledger_corrupt, profile=owner
                )
                if action is not None:
                    actions.append(action)
    return actions


def record_run_outcome(job: dict, outcome: str, *, error: str | None = None) -> bool:
    """Record ``outcome`` for the job's latest run (its ``last_run_at``).

    Used by the WebUI's Run now for muted and silent runs while the engine
    cannot record them itself (plan 3.1). The entry is the run's watermark,
    so the bridge never posts that run into the originating conversation,
    and ``delivery_state_for_job`` reports it. A corrupt ledger on disk is
    left for the bridge tick to rebuild (only the in-memory watermark is
    set), so this write can never turn a damaged ledger into one that
    replays the fresh window. Returns True when the entry reached disk.
    """
    if outcome not in RUN_NOW_OUTCOMES:
        raise ValueError(f"unsupported run outcome: {outcome}")
    job_id = str(job.get("id") or "")
    if not job_id or not job.get("last_run_at"):
        return False
    session_id = _webui_origin_session_id(job)
    with _ledger_lock:
        ledger, ledger_corrupt = _load_ledger_state()
        jobs_map = ledger.setdefault("jobs", {})
        for jid, entry in _MEMORY_WATERMARKS.items():
            jobs_map[jid] = dict(entry)
        if ledger_corrupt:
            _record_outcome(ledger, job, outcome=outcome, error=error, session_id=session_id)
            _MEMORY_WATERMARKS[job_id] = dict(ledger["jobs"][job_id])
            return False
        return _record_and_persist(
            ledger, job, outcome=outcome, error=error, session_id=session_id
        )


def _process_one_job(
    job: dict, ledger: dict, home: Path, now_dt: datetime, *,
    ledger_corrupt: bool = False, profile: str = "default",
) -> dict | None:
    job_id = str(job.get("id") or "")
    if not job_id:
        return None
    if _bridge_scope(job) is None:
        return None
    last_run_at = job.get("last_run_at")
    if not last_run_at:
        return None

    entry = (ledger.get("jobs") or {}).get(job_id)
    if entry and entry.get("run_at") == last_run_at:
        # Already handled this run. A duplicate-run refusal or a retry never
        # bumps last_run_at, so it lands here and cannot double-post; the
        # NEXT completed run gets a fresh last_run_at and is delivered.
        return None

    # Where this run's result belongs, without creating anything yet.
    target = _resolve_target(job, profile, create=False)
    session_id = target["session_id"]

    def _action(outcome, error=None):
        return {
            "job_id": job_id,
            "outcome": outcome,
            "error": error,
            "session_id": session_id,
            "profile": profile,
            "target": target["kind"],
        }

    def _persist(outcome, error=None):
        return _record_and_persist(
            ledger, job, outcome=outcome, error=error, session_id=session_id,
            profile=profile, target=target["kind"],
        )

    run_dt = _parse_run_at(last_run_at)
    if entry is None and (
        ledger_corrupt
        or (
            run_dt is not None
            and now_dt - run_dt > timedelta(seconds=FRESH_RUN_WINDOW_SECS)
        )
    ):
        # First sighting of a historical run: initialize the watermark
        # without posting so enabling the bridge does not replay history.
        # A corrupt on-disk ledger gets the same watermark-only treatment
        # even inside the fresh window: those runs were most likely already
        # delivered before the ledger got damaged, and dropping at most one
        # genuine update beats replaying the whole fresh window into the
        # conversation.
        _persist(OUTCOME_SKIPPED_STALE)
        return _action(OUTCOME_SKIPPED_STALE)

    if session_id and _session_busy(session_id):
        # A live turn owns the transcript; deliver on the next tick. The
        # watermark is NOT advanced, so the update is deferred, never lost.
        return None

    run_ok = str(job.get("last_status") or "").lower() in ("", "ok")
    outcome: str
    error: str | None = None
    text: str | None = None

    if not _job_wants_webui_delivery(job):
        engine_delivery_error = job.get("last_delivery_error")
        if run_ok and not engine_delivery_error:
            # External delivery succeeded, or the engine's notify gate muted
            # it; either way nothing is duplicated into the chat.
            outcome = OUTCOME_MUTED if _engine_muted(job) else OUTCOME_SKIPPED_EXTERNAL
        elif not run_ok:
            if _engine_muted(job) or _notify_mutes(job, success=False):
                outcome = OUTCOME_MUTED
            else:
                text = build_update_text(
                    job, body=None, run_ok=False, run_error=job.get("last_error")
                )
                outcome = OUTCOME_DELIVERED
        else:
            # The engine tried an external delivery and it failed. The
            # notice counts as a failure alert: only delivery "off" keeps it
            # out of the conversation, and the failure stays recorded.
            outcome = OUTCOME_EXTERNAL_FAILED
            error = str(engine_delivery_error)
            if not _notify_mutes(job, success=False):
                text = build_external_failure_text(job, str(engine_delivery_error))
    else:
        if run_ok:
            output = latest_output_text(Path(home) / "cron" / "output" / job_id, run_dt)
            body = None if output is None else _extract_response_body(output)
            if output is not None and output_is_silent(output):
                outcome = OUTCOME_SILENT
            elif _engine_muted(job) or _notify_mutes(job, success=True):
                outcome = OUTCOME_MUTED
            else:
                text = build_update_text(job, body=body, run_ok=True, run_error=None)
                outcome = OUTCOME_DELIVERED
        elif _engine_muted(job) or _notify_mutes(job, success=False):
            outcome = OUTCOME_MUTED
        else:
            text = build_update_text(
                job, body=None, run_ok=False, run_error=job.get("last_error")
            )
            outcome = OUTCOME_DELIVERED

    if text is not None and session_id is None and target["error"] is None:
        # First result of a job without a chat to post in: open its job chat.
        target = _resolve_target(job, profile, create=True)
        session_id = target["session_id"]

    if text is not None and session_id is None:
        # Nowhere to post: record the failure so it shows in the Tasks panel.
        outcome = OUTCOME_FAILED
        error = target["error"] or "no conversation to post this update into"
        logger.warning("cron delivery bridge: job %s update NOT delivered: %s", job_id, error)
        _persist(outcome, error)
        return _action(outcome, error)

    if text is not None:
        # Persist-then-deliver, on purpose: the watermark (with the optimistic
        # outcome) is written to memory and disk BEFORE the update is posted.
        # A crash between persist and deliver loses at most one notification,
        # which beats the deliver-then-persist alternative where a failed or
        # crashed ledger write re-posts the same update on every later tick.
        _persist(outcome, error)
        ok, deliver_error = deliver_update_to_session(session_id, text, job, profile=profile)
        if not ok:
            outcome = OUTCOME_FAILED
            error = deliver_error
            logger.warning(
                "cron delivery bridge: job %s update NOT delivered to session %s: %s",
                job_id, session_id, deliver_error,
            )
            # Correct the optimistic record so the failure stays visible in
            # /api/crons/recent; the watermark itself does not move.
            _persist(outcome, error)
        else:
            logger.info(
                "cron delivery bridge: job %s run %s delivered to session %s (%s)",
                job_id, last_run_at, session_id, target["kind"],
            )
    else:
        _persist(outcome, error)
    return _action(outcome, error)


# -- Status surfacing --------------------------------------------------------

def delivery_state_for_job(job: dict, ledger: dict | None = None) -> tuple[str, str | None]:
    """Return (delivery_status, delivery_error) for a job's latest run.

    The WebUI ledger is authoritative for WebUI-origin jobs: the engine's own
    delivery attempt for those ALWAYS fails ("unknown platform 'webui'"), so
    its ``last_delivery_error`` is noise once the bridge has delivered.

    ``muted`` means the job's notify delivery level kept the run from being
    delivered (plan 3.1). Jobs that only save their output stay ``local``.
    """
    if ledger is None:
        ledger = load_ledger()
    job_id = str(job.get("id") or "")
    # The in-memory watermark wins over the disk entry: it also holds runs
    # whose ledger write failed, which would otherwise surface as a bogus
    # "pending" (and, worse, be re-posted) after a disk failure. dict() takes
    # an atomic snapshot, so no lock is needed on this read-only path.
    entry = dict(_MEMORY_WATERMARKS).get(job_id) or (ledger.get("jobs") or {}).get(job_id)

    if _bridge_scope(job) is not None:
        if entry and entry.get("run_at") == job.get("last_run_at"):
            outcome = str(entry.get("outcome") or "")
            if outcome == OUTCOME_DELIVERED:
                return "delivered", None
            if outcome == OUTCOME_SILENT:
                return "silent", None
            if outcome == OUTCOME_MUTED:
                return "muted", None
            if outcome == OUTCOME_SKIPPED_STALE:
                return "skipped", None
            if outcome == OUTCOME_SKIPPED_EXTERNAL:
                return "delivered", None
            if outcome == OUTCOME_EXTERNAL_FAILED:
                return "failed", entry.get("error") or job.get("last_delivery_error")
            return "failed", entry.get("error") or "delivery to originating conversation failed"
        # The bridge has not processed this run yet. A job made in a chat
        # always waits for it; a job without a chat that delivers elsewhere
        # (a Tasks panel or opted-in job) is reported by the engine's own
        # delivery record below until the bridge has seen the run.
        if _webui_origin_session_id(job) is not None or _job_wants_webui_delivery(job):
            return "pending", None

    local_only = _deliver_tokens(job) in ([], ["local"])
    if not local_only:
        # Muted or silent (plan 3.1): a Run now the engine could not record
        # itself is in the ledger for exactly this run; an engine with the
        # notify gate records a muted run on the job.
        if entry and entry.get("run_at") == job.get("last_run_at"):
            outcome = str(entry.get("outcome") or "")
            if outcome == OUTCOME_MUTED:
                return "muted", None
            if outcome == OUTCOME_SILENT:
                return "silent", None
        if _engine_muted(job):
            return "muted", None
    deliver_error = job.get("last_delivery_error")
    if deliver_error:
        return "failed", str(deliver_error)
    if local_only:
        return "local", None
    return "delivered", None


def delivered_session_for_job(job: dict, ledger: dict | None = None) -> str | None:
    """The chat the bridge posted the job's latest run into, or None.

    Lets a completion notice open that chat (the job chat, or the chat the job
    was made in) instead of the engine's raw run transcript.
    """
    if ledger is None:
        ledger = load_ledger()
    job_id = str(job.get("id") or "")
    entry = dict(_MEMORY_WATERMARKS).get(job_id) or (ledger.get("jobs") or {}).get(job_id)
    if not entry or entry.get("run_at") != job.get("last_run_at"):
        return None
    if str(entry.get("outcome") or "") not in (OUTCOME_DELIVERED, OUTCOME_EXTERNAL_FAILED):
        return None
    sid = str(entry.get("session_id") or "")
    return sid or None


# -- Daemon thread -----------------------------------------------------------

def _bridge_loop() -> None:
    logger.info("cron WebUI delivery bridge thread started")
    while not _BRIDGE_STOP.is_set():
        try:
            process_jobs_once()
        except Exception:
            logger.debug("cron delivery bridge tick failed", exc_info=True)
        _BRIDGE_STOP.wait(POLL_INTERVAL)
    logger.info("cron WebUI delivery bridge thread stopped")


def start_cron_delivery_thread() -> bool:
    """Start the bridge daemon (idempotent). Returns True when started."""
    global _BRIDGE_THREAD
    with _BRIDGE_LIFECYCLE_LOCK:
        if _BRIDGE_THREAD is not None and _BRIDGE_THREAD.is_alive():
            return False
        _BRIDGE_STOP.clear()
        _BRIDGE_THREAD = threading.Thread(
            target=_bridge_loop, daemon=True, name="cron-webui-delivery"
        )
        _BRIDGE_THREAD.start()
        return True


def stop_cron_delivery_thread(timeout: float = 2.0) -> None:
    global _BRIDGE_THREAD
    with _BRIDGE_LIFECYCLE_LOCK:
        thread = _BRIDGE_THREAD
        _BRIDGE_THREAD = None
    _BRIDGE_STOP.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=timeout)
