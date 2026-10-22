"""Bot ownership of scheduled jobs (Michael Ramirez, 18 Oct 2026).

Asked for: "scheduled jobs aan een bot kunnen koppelen, dus dat een bot
bepaalde scheduled jobs owned. Scheduled jobs die een bot aanmaakt horen
automatisch aan hem gekoppeld. En bij terugkoppeling van de job hoort er een
chat te openen met context van die scheduled job."

The model is the one the engine already runs on, made visible:

* **The owning bot of a job is the profile whose cron store holds it.** Cron
  is per profile in the engine (cron/jobs.py anchors every store at the
  profile's HERMES_HOME) and the multiplexed ticker fires each store under its
  own home, so a job in ``profiles/<bot>/cron/jobs.json`` runs with that bot's
  config, skills and secrets. ``default`` (the root store) is SynthPulse. No
  extra field is stored: a second source of truth would drift from where the
  job actually runs.
* **Auto-link** follows from that: the cronjob tool writes to the store of the
  profile it runs in. A WebUI chat binds the session's bot
  (api/streaming.py, ``_STREAMING_CRON_PROFILE_HOME``), a delegated bot turn
  runs as its target bot (api/bot_delegation.py), and a profile gateway runs
  in its own home. Existing jobs need no backfill; scripts/cron_bot_owner_migration.py
  reports the per-bot counts and the rows whose legacy ``profile`` field or
  originating chat points at another bot.
* **Changing the owner** moves the job record to the other bot's store
  (``move_job``): removed from the old store first, then added to the new
  one, so it can never fire twice; the old store gets it back when the add
  fails. Its saved run output moves along.
* **Job chats**: a run's result lands in a chat of the owning bot. The chat
  the job was created in keeps getting it while that chat belongs to the
  owning bot; otherwise one chat per job and bot ("🗓️ <name>"), owned by the
  person the job runs for, is created on the first result and reused.
  ``context_prompt`` gives every turn in such a chat the job's live context,
  so "waarom faalde dit?" or "pas de tijd aan" works with that bot.
* **Responsible bot** (19 Oct 2026, "welke jobs ze ownen, alsof ze bepaalde
  taken automatisch uitvoeren"): most business jobs are script jobs in the
  root store, and moving a script job breaks it (the engine resolves scripts
  inside the running profile only). ``assign_job`` therefore records the bot
  that answers for a job in ``assigned_bot`` without moving it: the job keeps
  running where it runs, and the Bots page, the Tasks list and its filter show
  it under that bot. ``job_bot`` is the one rule: the assigned bot, else the
  store's bot.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT_PROFILE = "default"
JOB_CHATS_FILENAME = "cron_job_chats.json"
JOB_CHAT_EMOJI = "\U0001f5d3️"  # spiral calendar, the Tasks panel icon
MAX_PROMPT_CHARS = 4000
MAX_RUN_EXCERPT_CHARS = 600
CONTEXT_RUNS = 5

_CHATS_LOCK = threading.Lock()


# -- Profiles and stores -------------------------------------------------------

def normalize_profile(name) -> str:
    """Canonical owner name: ``default`` for the root profile and its aliases."""
    raw = str(name or "").strip()
    if not raw:
        return ROOT_PROFILE
    try:
        from api.profiles import _is_root_profile

        if _is_root_profile(raw):
            return ROOT_PROFILE
    except Exception:
        if raw == ROOT_PROFILE:
            return ROOT_PROFILE
    return raw


def normalize_job_link(value) -> Optional[dict]:
    """The ``cron_job`` field of a session: ``{"job_id", "profile"}`` or None."""
    if not isinstance(value, dict):
        return None
    job_id = str(value.get("job_id") or "").strip()
    if not job_id or len(job_id) > 128:
        return None
    profile = str(value.get("profile") or "").strip() or ROOT_PROFILE
    return {"job_id": job_id, "profile": profile, **({"kind": "scout"} if value.get("kind") == "scout" else {})}


def profile_for_home(home) -> str:
    """The profile a cron store home belongs to (``profiles/<name>`` or root)."""
    try:
        path = Path(home).expanduser()
    except Exception:
        return ROOT_PROFILE
    if path.parent.name == "profiles" and path.name:
        return path.name
    return ROOT_PROFILE


def home_for_profile(profile) -> Path:
    from api.profiles import get_hermes_home_for_profile

    return Path(get_hermes_home_for_profile(normalize_profile(profile)))


def _home_key(home) -> str:
    try:
        return str(Path(home).expanduser().resolve(strict=False))
    except Exception:
        return str(home)


def store_homes() -> list[tuple[str, Path]]:
    """``(profile, home)`` of every bot's cron store, root first, each once.

    Every profile counts, visible or not: visibility is a sidebar choice, and
    a hidden bot's jobs still run and still owe their person a result. An
    isolated-profile deployment has exactly one store.
    """
    import api.profiles as profiles

    homes: list[tuple[str, Path]] = []
    seen: set[str] = set()

    def _add(name, home):
        key = _home_key(home)
        if key in seen:
            return
        seen.add(key)
        homes.append((normalize_profile(name), Path(home)))

    if profiles._is_isolated_profile_mode():
        _add(profiles.get_active_profile_name() or ROOT_PROFILE, profiles.get_active_hermes_home())
        return homes
    _add(ROOT_PROFILE, profiles.get_hermes_home_for_profile(ROOT_PROFILE))
    try:
        rows = profiles.list_profiles_api(fast=True, include_skill_counts=False)
    except TypeError:
        rows = profiles.list_profiles_api()
    except Exception:
        logger.warning("cron bots: profile listing failed", exc_info=True)
        rows = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        home = profiles.get_hermes_home_for_profile(name)
        if Path(home).is_dir():
            _add(name, home)
    return homes


def read_store_jobs(home) -> list[dict]:
    """A store's jobs without engine imports or cron locks (read-only)."""
    from api.cron_webui_delivery import _load_jobs_from_home

    return _load_jobs_from_home(Path(home))


def find_job(job_id: str, profile=None) -> tuple[Optional[dict], str]:
    """``(job, owning profile)`` for a job id, read-only. With ``profile`` only
    that bot's store is read; otherwise every store, root first."""
    job_id = str(job_id or "")
    if not job_id:
        return None, ""
    if profile is not None:
        owner = normalize_profile(profile)
        for row in read_store_jobs(home_for_profile(owner)):
            if str(row.get("id") or "") == job_id:
                return row, owner
        return None, ""
    for owner, home in store_homes():
        for row in read_store_jobs(home):
            if str(row.get("id") or "") == job_id:
                return row, owner
    return None, ""


def bot_label(profile) -> str:
    """The bot's display title, falling back to its id (SynthPulse for root)."""
    owner = normalize_profile(profile)
    try:
        from api.bot_metadata import read_profile

        title = str((read_profile(owner).get("bot") or {}).get("title") or "").strip()
        if title:
            return title
    except Exception:
        logger.debug("cron bots: bot title unavailable for %s", owner, exc_info=True)
    return "SynthPulse" if owner == ROOT_PROFILE else owner


# -- The person a job reports to ----------------------------------------------

def job_person_email(job: dict, session_owner=None) -> str:
    """Who sees this job's results: the identity it runs as (``owner_email``),
    else the WebUI creator (``origin.user_id``, or the owner of the chat it was
    created in). Empty when nobody can be named (CLI, messaging, imported)."""
    if not isinstance(job, dict):
        return ""
    owner = str(job.get("owner_email") or "").strip().lower()
    if owner:
        return owner
    origin = job.get("origin")
    if not isinstance(origin, dict) or str(origin.get("platform") or "").strip().lower() != "webui":
        return ""
    stamped = str(origin.get("user_id") or "").strip().lower()
    if stamped:
        return stamped
    chat_id = str(origin.get("chat_id") or "").strip()
    if not chat_id:
        return ""
    if session_owner is None:
        from api.cron_scope import _session_owner_email as session_owner
    try:
        return str(session_owner(chat_id) or "").strip().lower()
    except Exception:
        return ""


def session_serves_bot(session, profile) -> bool:
    """A chat belongs to a bot when it is that bot's chat or the bot takes part
    in it (a group chat where the bot was added or delegated to)."""
    if session is None:
        return False
    owner = normalize_profile(profile)
    if normalize_profile(getattr(session, "profile", None)) == owner:
        return True
    bots = getattr(session, "bot_participants", None) or []
    return owner in {normalize_profile(b) for b in bots if b}


# -- Job chats -----------------------------------------------------------------

def _chats_path() -> Path:
    from api import config as _cfg

    return Path(_cfg.STATE_DIR) / JOB_CHATS_FILENAME


def _load_chats() -> dict:
    try:
        data = json.loads(_chats_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"chats": {}}
    except Exception:
        logger.warning("cron bots: job chat map unreadable; starting fresh", exc_info=True)
        return {"chats": {}}
    if isinstance(data, dict) and isinstance(data.get("chats"), dict):
        return data
    return {"chats": {}}


def _save_chats(data: dict) -> None:
    from api.paths import _atomic_write_text

    path = _chats_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(data, indent=1, default=str))


def _chat_key(job_id, profile) -> str:
    return f"{normalize_profile(profile)}/{job_id}"


def job_chat_title(job: dict) -> str:
    name = str((job or {}).get("name") or (job or {}).get("id") or "Geplande taak").strip()
    return (name if job.get("managed_by") == "scout" else f"{JOB_CHAT_EMOJI} {name}")[:120]


_NL_DAYS = ("zondag", "maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag")


def _nl_time(hour: str, minute: str) -> str | None:
    if not (hour.isdigit() and minute.isdigit()):
        return None
    h, m = int(hour), int(minute)
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return f"{h:02d}:{m:02d}"


def schedule_in_words(expr) -> str:
    """A cron expression or interval in plain Dutch ("0 9 * * 1" becomes
    "elke maandag om 09:00"). Anything it does not recognise comes back as
    it was. The Tasks panel has the same rules in static/panels.js
    (_cronScheduleInWords), with the words from the language pack."""
    raw = str(expr or "").strip()
    low = raw.lower()
    if low.startswith("every "):
        amount = low[6:].strip()
        for suffix, unit_one, unit_many in (("m", "minuut", "minuten"), ("h", "uur", "uur"), ("d", "dag", "dagen")):
            if amount.endswith(suffix) and amount[:-1].isdigit():
                n = int(amount[:-1])
                return f"elke {unit_one}" if n == 1 else f"elke {n} {unit_many}"
        return raw
    parts = raw.split()
    if len(parts) != 5:
        return raw
    minute, hour, dom, month, dow = parts
    if month != "*":
        return raw
    if minute.startswith("*/") and minute[2:].isdigit() and hour == dom == dow == "*":
        n = int(minute[2:])
        return "elke minuut" if n == 1 else f"elke {n} minuten"
    if minute.isdigit() and hour == dom == dow == "*":
        return f"elk uur om {int(minute):02d} minuten over"
    at = _nl_time(hour, minute)
    if at is None:
        return raw
    if dom == "*" and dow == "*":
        return f"elke dag om {at}"
    if dom == "*" and dow in ("1-5", "mon-fri"):
        return f"elke werkdag om {at}"
    if dom == "*" and dow.isdigit() and 0 <= int(dow) <= 7:
        return f"elke {_NL_DAYS[int(dow) % 7]} om {at}"
    if dow == "*" and dom.isdigit() and 1 <= int(dom) <= 31:
        return f"elke {int(dom)}e van de maand om {at}"
    return raw


def _schedule_text(job: dict) -> str:
    sched = job.get("schedule")
    display = job.get("schedule_display") or (sched.get("display") if isinstance(sched, dict) else None)
    if display:
        return str(display)
    if isinstance(sched, dict):
        return str(sched.get("expr") or sched.get("run_at") or sched.get("kind") or "")
    return str(sched or "")


def _excerpt(text, limit) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " (...)"


def job_chat_intro(job: dict, profile) -> str:
    """The first message of a job chat: what this chat is and the job at a glance."""
    if job.get("managed_by") == "scout":
        return ("Hier deelt Scout voorbereidingen, onderzoek en voorstellen van " + bot_label(profile)
                + ". Vraag gerust door of geef aan wat je wilt laten oppakken. "
                "Je bepaalt hoe vaak Scout kijkt bij de Scout-instellingen van deze bot.")
    name = str(job.get("name") or job.get("id") or "Geplande taak")
    lines = [
        f"{JOB_CHAT_EMOJI} Deze chat hoort bij de geplande taak **{name}**.",
        "Hier komt het resultaat van elke run binnen. Vraag gerust door, bijvoorbeeld "
        "waarom een run faalde of om de tijd aan te passen.",
        "",
        f"- Bot: {bot_label(profile)}",
    ]
    schedule = _schedule_text(job)
    if schedule:
        words = schedule_in_words(schedule)
        if words == schedule:
            # The chat's markdown reads a cron expression's "* *" as emphasis
            # even when escaped; the asterisk operator looks the same.
            words = schedule.replace("*", "\u2217")
        lines.append("- Wanneer: " + words)
    prompt = _excerpt(job.get("prompt"), 500)
    if prompt:
        lines.append(f"- Opdracht: {prompt}")
    return "\n".join(lines)


def find_job_chat(job_id, profile, person: str) -> Optional[str]:
    """The existing job chat of this job in this bot for this person, if it is
    still there. A chat that was deleted, or that now belongs to someone else,
    is forgotten so a fresh one is made."""
    key = _chat_key(job_id, profile)
    with _CHATS_LOCK:
        entry = (_load_chats().get("chats") or {}).get(key)
    if not isinstance(entry, dict):
        return None
    sid = str(entry.get("session_id") or "")
    if not sid:
        return None
    try:
        from api.models import get_session, is_safe_session_id

        if not is_safe_session_id(sid):
            return None
        session = get_session(sid, metadata_only=True)
    except Exception:
        return None
    if session is None:
        return None
    if str(getattr(session, "owner_email", "") or "").strip().lower() != str(person or "").strip().lower():
        return None
    link = normalize_job_link(getattr(session, "cron_job", None))
    if not link or link["job_id"] != str(job_id) or normalize_profile(link["profile"]) != normalize_profile(profile):
        return None
    return sid


def ensure_job_chat(job: dict, profile, person: str) -> tuple[Optional[str], bool]:
    """``(session_id, created)`` of the job chat, creating it when missing.

    The chat is an ordinary conversation of the owning bot, owned by
    ``person``: nobody else sees it unless that person shares it. It opens
    with an intro message; the job's live context reaches the agent through
    ``context_prompt`` on every turn.
    """
    person = str(person or "").strip().lower()
    job_id = str((job or {}).get("id") or "")
    if not person or not job_id:
        return None, False
    existing = find_job_chat(job_id, profile, person)
    if existing:
        if job.get("managed_by") == "scout":
            from api.models import get_session
            session = get_session(existing)
            if session and session.cron_job.get("kind") != "scout":
                session.cron_job = {**session.cron_job, "kind": "scout"}
                if session.title.startswith(JOB_CHAT_EMOJI): session.title = job_chat_title(job)
                session.save()
        return existing, False
    owner = normalize_profile(profile)
    from api.models import new_session

    # The job's working folder when it has one, else the usual default.
    workdir = str(job.get("workdir") or "").strip()
    workspace = workdir if workdir and Path(workdir).expanduser().is_dir() else None
    session = new_session(workspace=workspace, profile=owner)
    session.owner_email = person
    session.title = job_chat_title(job)
    session.manual_title = True
    session.llm_title_generated = True
    session.cron_job = {"job_id": job_id, "profile": owner, **({"kind": "scout"} if job.get("managed_by") == "scout" else {})}
    session.messages.append({
        "role": "assistant",
        "content": job_chat_intro(job, owner),
        "timestamp": time.time(),
        "cron_context": {"job_id": job_id, "profile": owner},
    })
    session.save()
    with _CHATS_LOCK:
        data = _load_chats()
        data.setdefault("chats", {})[_chat_key(job_id, owner)] = {
            "session_id": session.session_id,
            "owner_email": person,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            _save_chats(data)
        except Exception:
            logger.warning("cron bots: job chat map write failed for %s", job_id, exc_info=True)
    try:
        from api.session_events import publish_session_list_changed

        publish_session_list_changed("cron_job_chat", profile=owner, session_id=session.session_id)
    except Exception:
        logger.debug("cron bots: session list publish failed", exc_info=True)
    return session.session_id, True


def annotate_job_chats(rows, viewer) -> None:
    """Add ``job_chat_session_id`` to the listing rows whose job chat belongs
    to ``viewer`` (one map read for the whole list). Someone else's job chat
    is never named: it is that person's conversation."""
    viewer = str(viewer or "").strip().lower()
    if not viewer or not rows:
        return
    with _CHATS_LOCK:
        chats = _load_chats().get("chats") or {}
    if not chats:
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry = chats.get(_chat_key(row.get("id"), row.get("owner_profile")))
        if isinstance(entry, dict) and str(entry.get("owner_email") or "").lower() == viewer:
            sid = str(entry.get("session_id") or "")
            if sid:
                row["job_chat_session_id"] = sid


# -- Live job context for the agent ------------------------------------------

def _recent_runs(home: Path, job_id: str, limit: int = CONTEXT_RUNS) -> list[tuple[str, str]]:
    """``(file stem, response excerpt)`` of the newest saved runs."""
    from api.cron_webui_delivery import _extract_response_body

    out_dir = Path(home) / "cron" / "output" / str(job_id)
    try:
        files = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:limit]
    except OSError:
        return []
    runs = []
    for f in files:
        try:
            body = _extract_response_body(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        runs.append((f.stem, _excerpt(body, MAX_RUN_EXCERPT_CHARS)))
    return runs


def job_refs_for_session(session, limit: int = 3) -> list[tuple[str, str]]:
    """The jobs a chat is about: its job link, then the jobs whose results were
    posted into its recent messages (the chat a job was created in)."""
    refs: list[tuple[str, str]] = []

    def _add(job_id, profile):
        ref = (str(job_id), normalize_profile(profile))
        if ref[0] and ref not in refs:
            refs.append(ref)

    link = normalize_job_link(getattr(session, "cron_job", None))
    if link:
        _add(link["job_id"], link["profile"])
    messages = getattr(session, "messages", None) or []
    for message in reversed(messages[-40:]):
        if len(refs) >= limit:
            break
        meta = message.get("cron_delivery") if isinstance(message, dict) else None
        if isinstance(meta, dict) and meta.get("job_id"):
            _add(meta.get("job_id"), meta.get("profile") or getattr(session, "profile", None))
    return refs[:limit]


def job_context_text(job: dict, profile, home: Path) -> str:
    job_id = str(job.get("id") or "")
    state = "paused" if job.get("enabled") is False or job.get("state") == "paused" else "active"
    lines = [
        f"- Job: {job.get('name') or job_id} (job_id {job_id})",
        f"- Owning bot: {bot_label(profile)} (profile {normalize_profile(profile)})",
        f"- Schedule: {_schedule_text(job) or 'unknown'} ({schedule_in_words(_schedule_text(job))}); state {state}; next run {job.get('next_run_at') or 'none'}",
        f"- Delivers to: {job.get('deliver') or 'origin'}",
    ]
    notify = job.get("notify")
    if isinstance(notify, dict):
        lines.append(f"- Notify: in_app {notify.get('in_app') or 'all'}, delivery {notify.get('delivery') or 'all'}")
    if job.get("last_run_at"):
        lines.append(f"- Last run: {job.get('last_run_at')} status {job.get('last_status') or 'unknown'}")
    if job.get("last_error"):
        lines.append(f"- Last error: {_excerpt(job.get('last_error'), 800)}")
    if job.get("last_delivery_error"):
        lines.append(f"- Last delivery error: {_excerpt(job.get('last_delivery_error'), 400)}")
    if job.get("no_agent"):
        lines.append(f"- Script job (no agent): {job.get('script') or ''}")
    prompt = _excerpt(job.get("prompt"), MAX_PROMPT_CHARS)
    if prompt:
        lines.append("- Instructions (the job's prompt):\n" + "\n".join("    " + ln for ln in prompt.splitlines()))
    runs = _recent_runs(home, job_id)
    if runs:
        lines.append("- Recent saved runs, newest first:")
        for stem, excerpt in runs:
            lines.append(f"    * {stem}: {excerpt.replace(chr(10), ' ')}" if excerpt else f"    * {stem}: (no response captured)")
    return "\n".join(lines)


def context_prompt(session, identity=None) -> str:
    """Ephemeral system context for a turn in a chat about scheduled jobs.

    Read live at turn start, so a changed schedule or a new failure is what
    the agent sees. A job the speaker could not see in the Tasks panel adds
    nothing (api/cron_scope.py decides, as for the listing). Never persisted.
    """
    try:
        refs = job_refs_for_session(session)
    except Exception:
        return ""
    if not refs:
        return ""
    blocks = []
    for job_id, profile in refs:
        try:
            job, owner = find_job(job_id, profile)
            if job is None:
                job, owner = find_job(job_id)
            if job is None:
                continue
            if identity is not None:
                import api.cron_scope as cron_scope

                if not cron_scope.identity_sees_cron_row(identity, job, store_profile=owner):
                    continue
            blocks.append(job_context_text(job, owner, home_for_profile(owner)))
        except Exception:
            logger.debug("cron bots: context for job %s unavailable", job_id, exc_info=True)
    if not blocks:
        return ""
    return (
        "Scheduled job context for this conversation (read live at the start of this turn). "
        "Results of these scheduled jobs are posted in this chat; follow-up questions are usually "
        "about them. To change one (time, instructions, pause, resume, run now) use the cronjob tool "
        "with its job_id; a job owned by the bot answering here lives in that bot's own job store. "
        "Explain failures from the last error and the saved runs below before guessing.\n"
        + "\n\n".join(blocks)
    )


# -- Changing the owning bot ---------------------------------------------------

class OwnerChangeError(Exception):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.message = message


def _job_is_running(job: dict) -> bool:
    return bool(job.get("run_claim") or job.get("fire_claim"))


def _locked(cj):
    lock = getattr(cj, "_jobs_lock", None)
    if lock is None:
        import contextlib

        return contextlib.nullcontext()
    return lock()


def _save(cj, jobs, removed_ids=None):
    saver = getattr(cj, "_save_jobs_unlocked", None) if getattr(cj, "_jobs_lock", None) else None
    if saver is not None:
        saver(jobs, removed_ids=removed_ids)
    else:
        cj.save_jobs(jobs, removed_ids=removed_ids)


def _take_from_store(home: Path, job_id: str) -> dict:
    from api.profiles import cron_profile_context_for_home

    with cron_profile_context_for_home(home):
        import cron.jobs as cj

        with _locked(cj):
            jobs = cj.load_jobs()
            match = next((j for j in jobs if str(j.get("id") or "") == job_id), None)
            if match is None:
                raise OwnerChangeError(404, "job_not_found", "Job not found")
            if _job_is_running(match):
                raise OwnerChangeError(409, "job_running", "This task is running right now. Try again when the run is done.")
            _save(cj, [j for j in jobs if str(j.get("id") or "") != job_id], removed_ids={job_id})
            return dict(match)


def _put_in_store(home: Path, job: dict) -> None:
    from api.profiles import cron_profile_context_for_home

    with cron_profile_context_for_home(home):
        import cron.jobs as cj

        with _locked(cj):
            jobs = cj.load_jobs()
            if any(str(j.get("id") or "") == str(job.get("id")) for j in jobs):
                raise OwnerChangeError(409, "job_id_taken", "The other bot already has a task with this id.")
            jobs.append(job)
            _save(cj, jobs)


def _move_outputs(src_home: Path, dst_home: Path, job_id: str) -> None:
    src = Path(src_home) / "cron" / "output" / job_id
    dst = Path(dst_home) / "cron" / "output" / job_id
    if not src.is_dir() or dst.exists():
        return
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    except Exception:
        logger.warning("cron bots: run output of %s stayed in %s", job_id, src, exc_info=True)


def move_job(job_id: str, from_profile, to_profile) -> dict:
    """Make ``to_profile`` the owning bot of a job: move its record between
    cron stores. Returns the moved job. Raises OwnerChangeError.

    Remove first, add second: between the two the job is in no store, so no
    ticker can fire it twice. A failed add puts it back where it was. The
    legacy per-job ``profile`` override is cleared, so the WebUI's Run now
    and the scheduler both run it as its new bot.
    """
    job_id = str(job_id or "")
    src_profile = normalize_profile(from_profile)
    dst_profile = normalize_profile(to_profile)
    src_home = home_for_profile(src_profile)
    dst_home = home_for_profile(dst_profile)
    if _home_key(src_home) == _home_key(dst_home):
        job, _owner = find_job(job_id, src_profile)
        if job is None:
            raise OwnerChangeError(404, "job_not_found", "Job not found")
        return job
    if not Path(dst_home).is_dir():
        raise OwnerChangeError(404, "bot_not_found", "Bot not found")
    if find_job(job_id, src_profile)[0] is None:
        raise OwnerChangeError(404, "job_not_found", "Job not found")
    if any(str(j.get("id") or "") == job_id for j in read_store_jobs(dst_home)):
        raise OwnerChangeError(409, "job_id_taken", "The other bot already has a task with this id.")
    job = _take_from_store(src_home, job_id)
    moved = dict(job)
    moved["profile"] = None
    try:
        _put_in_store(dst_home, moved)
    except Exception:
        logger.warning("cron bots: adding %s to %s failed; putting it back", job_id, dst_profile, exc_info=True)
        _put_in_store(src_home, job)
        raise
    _move_outputs(src_home, dst_home, job_id)
    return moved


# -- Responsible bot (no move) --------------------------------------------------

def job_bot(job: dict, store_profile=None) -> str:
    """The bot that answers for a job: ``assigned_bot`` when set, else the bot
    whose store holds it."""
    assigned = str((job or {}).get("assigned_bot") or "").strip()
    if assigned:
        return normalize_profile(assigned)
    return normalize_profile(store_profile if store_profile is not None else (job or {}).get("owner_profile"))


def assign_job(job_id: str, store_profile, bot) -> dict:
    """Record ``bot`` as the responsible bot of a job in its own store, or
    clear it when ``bot`` is empty or the store's own bot. The record stays
    where it is, so the run itself does not change. Raises OwnerChangeError."""
    from api.profiles import cron_profile_context_for_home

    job_id = str(job_id or "")
    store = normalize_profile(store_profile)
    home = home_for_profile(store)
    target = normalize_profile(bot) if str(bot or "").strip() else ""
    if target and not Path(home_for_profile(target)).is_dir():
        raise OwnerChangeError(404, "bot_not_found", "Bot not found")
    with cron_profile_context_for_home(home):
        import cron.jobs as cj

        with _locked(cj):
            jobs = cj.load_jobs()
            match = next((j for j in jobs if str(j.get("id") or "") == job_id), None)
            if match is None:
                raise OwnerChangeError(404, "job_not_found", "Job not found")
            if target and target != store:
                match["assigned_bot"] = target
            else:
                match.pop("assigned_bot", None)
            _save(cj, jobs)
            return dict(match)
