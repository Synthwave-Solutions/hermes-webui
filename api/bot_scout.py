"""Scout per bot: one daily, read-only look-out job in the bot's own cron store.

The settings live in the bot's profile.yaml (ui_meta.hermes-bots.scout,
api/bot_metadata.save_scout); the Scout collector reads them from there. This
module keeps the bot's Scout job in step with them:

* **One job per bot**, in the cron store of the bot itself (api/cron_bots.py:
  the store a job lives in is its owner), recognised by ``managed_by: "scout"``.
  Turning Scout on creates it, or updates and resumes the one that is there;
  turning it off pauses it and never deletes it, so its history stays.
* **The runner is the bot's own copy.** The engine runs a cron ``script`` only
  when it resolves inside the job's own ``<HERMES_HOME>/scripts/`` and gives it
  no arguments, so the job names ``scout/scout_collect.py`` and turning Scout on
  copies the runner files from the shared source (``~/.hermes/scripts/scout/``,
  the root profile's own folder) into ``<bot home>/scripts/scout/`` as real
  files. Without the source nothing is changed and the caller gets an error.
* **Wake gate**: the collector prints ``{"wakeAgent": false}`` when there is
  nothing new, so a quiet day costs no agent run and posts nothing.
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

from api import bot_metadata

SCRIPT = "scout/scout_collect.py"
RUNNER_FILES = ("scout_collect.py", "scout_ledger.py", "prompt.md")
REQUIRED_FILES = ("scout_collect.py", "scout_ledger.py")
MANAGED_BY = "scout"
JOB_NAME = "Scout"
JOB_CATEGORY = "Scout"
# terminal runs scout_ledger.py, kanban files triage tasks; web only searches
# the bot's topics, so it is left out while there are none.
BASE_TOOLSETS = ("terminal", "kanban")
TOPIC_TOOLSETS = ("web",)
# The user switched job notifications off; the digest still lands in the
# bot's job chat (delivery all), a quiet run posts nothing.
NOTIFY = {"in_app": "off", "delivery": "all"}
MAX_PROMPT_CHARS = 12000

DEFAULT_PROMPT = """Je bent de Scout van deze bot. Het script hiervoor heeft nieuwe items verzameld; ze staan hierboven als context.

Regels:
- Je werkt alleen lezend. Je verstuurt nooit berichten, mails of chats en je wijzigt niets buiten het takenbord.
- Kies per item precies een uitkomst: negeren, stil bewaren, aan project koppelen of melden.
- Negeren: niet relevant of al bekend. Noem het niet.
- Stil bewaren: misschien later nuttig. Zet het kort onder Bewaard.
- Aan project koppelen: hoort bij een lopend project. Noem het project en waarom.
- Melden: vraagt aandacht of actie. Maak per actiepunt een kanbantaak in triage met een duidelijke titel, de bron en de voorgestelde volgende stap, in plaats van zelf te handelen.
- Leg elk item dat je hebt beoordeeld vast met python3 "$HERMES_HOME/scripts/scout/scout_ledger.py", zodat je het morgen niet opnieuw ziet.
- Schrijf hooguit een digest per run: kort, in het Nederlands, gegroepeerd per uitkomst, met bronlinks.
- Is er niets om te melden, te koppelen of te bewaren, antwoord dan alleen met [SILENT]."""

_LOCK = threading.Lock()


class ScoutError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _root_home() -> Path:
    from api.profiles import _DEFAULT_HERMES_HOME

    return Path(_DEFAULT_HERMES_HOME)


def source_dir() -> Path:
    return _root_home() / "scripts" / "scout"


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return a.resolve(strict=False) == b.resolve(strict=False)
    except OSError:
        return False


def install_runner(home) -> Path:
    """Copy the runner files into ``<home>/scripts/scout/`` (idempotent: only
    files whose content differs are written). Returns that folder."""
    home = Path(home)
    src = source_dir()
    missing = [n for n in REQUIRED_FILES if not (src / n).is_file()]
    if missing:
        raise ScoutError(503, "Scout is not installed on this server yet (missing %s in %s)." % (", ".join(missing), src))
    dest = home / "scripts" / "scout"
    if _same_dir(dest, src):
        return dest
    for part in (home / "scripts", dest):
        if part.is_symlink():
            raise ScoutError(400, "The bot's scripts folder cannot be a symlink")
    dest.mkdir(parents=True, exist_ok=True)
    for name in RUNNER_FILES:
        source = src / name
        if not source.is_file():
            continue
        target = dest / name
        if target.is_symlink():
            raise ScoutError(400, "Scout file %s in this bot is a symlink" % name)
        blob = source.read_bytes()
        if target.is_file() and target.read_bytes() == blob:
            continue
        fd, tmp = tempfile.mkstemp(dir=dest, prefix="." + name + ".")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(blob)
            os.chmod(tmp, 0o755 if name.endswith(".py") else 0o644)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return dest


def job_prompt(home, topics) -> str:
    """The bot's own prompt.md, else the built-in default, plus its topics."""
    path = Path(home) / "scripts" / "scout" / "prompt.md"
    text = ""
    try:
        if path.is_file() and not path.is_symlink():
            text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        text = ""
    text = (text or DEFAULT_PROMPT)[:MAX_PROMPT_CHARS]
    if topics:
        text += "\n\nOnderwerpen van deze bot: " + "; ".join(topics) + "."
    else:
        text += "\n\nEr zijn geen onderwerpen ingesteld; volg de rol en beschrijving van de bot."
    return text


def schedule_for(digest_time: str) -> str:
    hour, minute = digest_time.split(":")
    return "%d %d * * *" % (int(minute), int(hour))


def toolsets_for(topics) -> list:
    return [*BASE_TOOLSETS, *(TOPIC_TOOLSETS if topics else ())]


def scout_jobs(jobs) -> list:
    return [j for j in jobs if isinstance(j, dict) and j.get("managed_by") == MANAGED_BY]


def _mark_scout(cj, job_id: str) -> None:
    """Stamp ``managed_by: "scout"``. The engine's create/update accept only
    synthwave or client there (and readers fall back to client for anything
    else), so the marker goes into the store record directly."""
    from api.cron_bots import _locked, _save

    with _locked(cj):
        jobs = cj.load_jobs()
        for row in jobs:
            if str(row.get("id") or "") == job_id:
                row["managed_by"] = MANAGED_BY
                _save(cj, jobs)
                return
    raise ScoutError(500, "The Scout job disappeared while it was being set up")


def sync_job(home, scout: dict, owner_email: str | None):
    """Make the store at ``home`` match ``scout``. Returns the Scout job (or
    None when Scout is off and never had one)."""
    from api.profiles import cron_profile_context_for_home

    with cron_profile_context_for_home(Path(home)):
        import cron.jobs as cj

        existing = scout_jobs(cj.load_jobs())
        if not scout["enabled"]:
            for job in existing:
                if job.get("enabled", True) and job.get("state") != "paused":
                    cj.pause_job(job["id"], reason="Scout uitgezet")
            return cj.get_job(existing[0]["id"]) if existing else None
        fields = {
            "name": JOB_NAME,
            "prompt": job_prompt(home, scout["topics"]),
            "schedule": schedule_for(scout["digest_time"]),
            "script": SCRIPT,
            "enabled_toolsets": toolsets_for(scout["topics"]),
        }
        if existing:
            job = existing[0]
            # A second Scout job (written by hand) would digest twice: pause it.
            for extra in existing[1:]:
                if extra.get("enabled", True) and extra.get("state") != "paused":
                    cj.pause_job(extra["id"], reason="Dubbele Scout")
            cj.update_job(job["id"], fields)
            if not job.get("enabled", True) or job.get("state") == "paused":
                cj.resume_job(job["id"])
            return cj.get_job(job["id"])
        kwargs = dict(fields, deliver="local", notify=dict(NOTIFY), category=JOB_CATEGORY)
        if owner_email:
            # As a Tasks panel job: run as this person, results in the bot's job chat.
            kwargs["origin"] = {"platform": "webui", "chat_id": None, "user_id": owner_email}
            kwargs["owner_email"] = owner_email
        job = cj.create_job(**kwargs)
        try:
            _mark_scout(cj, job["id"])
        except Exception:
            cj.remove_job(job["id"])
            raise
        return cj.get_job(job["id"])


def apply(name: str, body: dict, owner_email: str | None) -> dict:
    """Save the bot's Scout settings and bring its job in line.

    Order: runner copy first (the likely failure, nothing saved yet), then the
    settings (revision checked), then the job. A failing job write puts the
    previous settings back, so the toggle never shows a state that is not real.
    """
    if not isinstance(body, dict):
        raise ScoutError(400, "Invalid request")
    from api.cron_bots import home_for_profile

    with _LOCK:
        current = bot_metadata.read_profile(name)
        if body.get("enabled") is True and current.get("bot_kind") != "bot":
            raise ScoutError(400, "Scout is only for bots, not for a person's profile")
        stored = (current.get("bot") or {}).get("scout") or {}
        scout = bot_metadata.validate_scout(
            body.get("enabled"),
            body["topics"] if "topics" in body else stored.get("topics"),
            body["digest_time"] if "digest_time" in body else stored.get("digest_time"),
        )
        home = home_for_profile(name)
        if scout["enabled"]:
            install_runner(home)
        saved = bot_metadata.save_scout(name, scout, body.get("revision"))
        try:
            job = sync_job(home, scout, owner_email)
        except Exception:
            previous = stored or {"enabled": False, "topics": [], "digest_time": bot_metadata.SCOUT_DEFAULT_TIME}
            bot_metadata.save_scout(name, previous, saved["bot_revision"])
            raise
        return {**bot_metadata.read_profile(name), "scout_job": _job_summary(job)}


def _job_summary(job):
    if not isinstance(job, dict):
        return None
    return {
        "id": job.get("id"),
        "enabled": bool(job.get("enabled", True)) and job.get("state") != "paused",
        "schedule_display": job.get("schedule_display"),
        "next_run_at": job.get("next_run_at"),
    }
