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
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

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
) -> None:
    ledger.setdefault("jobs", {})[str(job.get("id", ""))] = {
        "run_at": job.get("last_run_at"),
        "outcome": outcome,
        "error": error,
        "session_id": session_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def _record_and_persist(
    ledger: dict,
    job: dict,
    *,
    outcome: str,
    error: str | None = None,
    session_id: str | None = None,
) -> bool:
    """Record the outcome in the ledger, the in-memory watermark AND on disk.

    Returns True when the disk write succeeded. A failed write is deliberate
    best-effort: the in-memory watermark already holds the entry, so even a
    persistently unwritable state dir cannot re-post the same run on later
    ticks; at worst a process restart with a still-broken disk re-posts once.
    """
    _record_outcome(ledger, job, outcome=outcome, error=error, session_id=session_id)
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


def _latest_output_response(
    home: Path, job_id: str, run_dt: Optional[datetime] = None
) -> str | None:
    """Read the newest output file's response body for *job_id*, or None.

    When *run_dt* is known, an output file written long before the run is
    rejected so an errored run that produced no file cannot repost an earlier
    run's body.
    """
    out_dir = Path(home) / "cron" / "output" / str(job_id)
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
            return _extract_response_body(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            logger.debug("cron delivery bridge: unreadable output file %s", f)
    return None


# -- Message building --------------------------------------------------------

def _truncate_body(body: str) -> str:
    if len(body) <= MAX_DELIVERY_CHARS:
        return body
    return body[:MAX_DELIVERY_CHARS].rstrip() + "\n\n(truncated: full output is in the Tasks panel)"


def build_update_text(job: dict, *, body: str | None, run_ok: bool, run_error: str | None) -> str:
    """One concise update for the originating conversation."""
    name = str(job.get("name") or job.get("id") or "scheduled task")
    if not run_ok:
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

def deliver_update_to_session(session_id: str, text: str, job: dict) -> tuple[bool, str | None]:
    """Append one assistant update to the WebUI session and notify open tabs.

    Returns (ok, error). Never raises.
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


def process_jobs_once(
    jobs: list[dict] | None = None,
    *,
    home: Path | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Run one bridge pass; returns a list of action records (for tests/logs).

    Each record: {"job_id", "outcome", "error", "session_id"}. Jobs skipped
    because nothing changed produce no record.
    """
    resolved_home = Path(home) if home is not None else _active_hermes_home()
    if jobs is None:
        jobs = _load_jobs_from_home(resolved_home)
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
        for job in jobs:
            action = _process_one_job(
                job, ledger, resolved_home, now_dt, ledger_corrupt=ledger_corrupt
            )
            if action is not None:
                actions.append(action)
    return actions


def _process_one_job(
    job: dict, ledger: dict, home: Path, now_dt: datetime, *,
    ledger_corrupt: bool = False,
) -> dict | None:
    job_id = str(job.get("id") or "")
    if not job_id:
        return None
    session_id = _webui_origin_session_id(job)
    if session_id is None:
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
        _record_and_persist(
            ledger, job, outcome=OUTCOME_SKIPPED_STALE, session_id=session_id
        )
        return {
            "job_id": job_id,
            "outcome": OUTCOME_SKIPPED_STALE,
            "error": None,
            "session_id": session_id,
        }

    if _session_busy(session_id):
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
            # External delivery succeeded; do not duplicate it in the chat.
            outcome = OUTCOME_SKIPPED_EXTERNAL
        elif not run_ok:
            text = build_update_text(
                job, body=None, run_ok=False, run_error=job.get("last_error")
            )
            outcome = OUTCOME_DELIVERED
        else:
            text = build_external_failure_text(job, str(engine_delivery_error))
            outcome = OUTCOME_EXTERNAL_FAILED
            error = str(engine_delivery_error)
    else:
        if run_ok:
            body = _latest_output_response(home, job_id, run_dt)
            if body is not None and _is_silent_response(body):
                outcome = OUTCOME_SILENT
            else:
                text = build_update_text(job, body=body, run_ok=True, run_error=None)
                outcome = OUTCOME_DELIVERED
        else:
            text = build_update_text(
                job, body=None, run_ok=False, run_error=job.get("last_error")
            )
            outcome = OUTCOME_DELIVERED

    if text is not None:
        # Persist-then-deliver, on purpose: the watermark (with the optimistic
        # outcome) is written to memory and disk BEFORE the update is posted.
        # A crash between persist and deliver loses at most one notification,
        # which beats the deliver-then-persist alternative where a failed or
        # crashed ledger write re-posts the same update on every later tick.
        _record_and_persist(
            ledger, job, outcome=outcome, error=error, session_id=session_id
        )
        ok, deliver_error = deliver_update_to_session(session_id, text, job)
        if not ok:
            outcome = OUTCOME_FAILED
            error = deliver_error
            logger.warning(
                "cron delivery bridge: job %s update NOT delivered to session %s: %s",
                job_id, session_id, deliver_error,
            )
            # Correct the optimistic record so the failure stays visible in
            # /api/crons/recent; the watermark itself does not move.
            _record_and_persist(
                ledger, job, outcome=outcome, error=error, session_id=session_id
            )
        else:
            logger.info(
                "cron delivery bridge: job %s run %s delivered to session %s",
                job_id, last_run_at, session_id,
            )
    else:
        _record_and_persist(
            ledger, job, outcome=outcome, error=error, session_id=session_id
        )
    return {
        "job_id": job_id,
        "outcome": outcome,
        "error": error,
        "session_id": session_id,
    }


# -- Status surfacing --------------------------------------------------------

def delivery_state_for_job(job: dict, ledger: dict | None = None) -> tuple[str, str | None]:
    """Return (delivery_status, delivery_error) for a job's latest run.

    The WebUI ledger is authoritative for WebUI-origin jobs: the engine's own
    delivery attempt for those ALWAYS fails ("unknown platform 'webui'"), so
    its ``last_delivery_error`` is noise once the bridge has delivered.
    """
    if ledger is None:
        ledger = load_ledger()
    job_id = str(job.get("id") or "")
    # The in-memory watermark wins over the disk entry: it also holds runs
    # whose ledger write failed, which would otherwise surface as a bogus
    # "pending" (and, worse, be re-posted) after a disk failure. dict() takes
    # an atomic snapshot, so no lock is needed on this read-only path.
    entry = dict(_MEMORY_WATERMARKS).get(job_id) or (ledger.get("jobs") or {}).get(job_id)
    webui_session = _webui_origin_session_id(job)

    if webui_session is not None:
        if entry and entry.get("run_at") == job.get("last_run_at"):
            outcome = str(entry.get("outcome") or "")
            if outcome == OUTCOME_DELIVERED:
                return "delivered", None
            if outcome == OUTCOME_SILENT:
                return "silent", None
            if outcome == OUTCOME_SKIPPED_STALE:
                return "skipped", None
            if outcome == OUTCOME_SKIPPED_EXTERNAL:
                return "delivered", None
            if outcome == OUTCOME_EXTERNAL_FAILED:
                return "failed", entry.get("error") or job.get("last_delivery_error")
            return "failed", entry.get("error") or "delivery to originating conversation failed"
        # The bridge has not processed this run yet.
        return "pending", None

    deliver_error = job.get("last_delivery_error")
    if deliver_error:
        return "failed", str(deliver_error)
    if _deliver_tokens(job) in ([], ["local"]):
        return "local", None
    return "delivered", None


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
