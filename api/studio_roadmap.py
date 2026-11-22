"""The quickscan roadmap in Studio, with proof that it is being carried out (22 Nov 2026).

A quickscan ends with a roadmap: a Gantt in months and weeks with a start
group and one group per block, steering sessions, a card per block, a systems
overview and process diagrams. This module keeps that roadmap for the
installation and ties every row and every block to what really exists here:
scheduled tasks, bots, skills, use cases and playbooks.

Storage
    ``STATE_DIR/studio/roadmap.json``: one roadmap per installation, with its
    ``report_version``. Every change is appended to ``roadmap_audit.jsonl``.

Model (see ``clean_roadmap``)
    start_date (the Monday of week 1), weeks, steering_weeks, groups (blocks)
    with rows of kind fundament, agent, werksessie or borging (start week and
    number of weeks), phases (the block cards), systems, notes, diagrams.
    An import replaces the whole document and is validated strictly: bounded
    sizes, known fields only, no markup, no long dashes.

Execution
    A row and a phase carry ``links`` (job, bot, skill, use_case, playbook),
    a manual ``status``, ``delivered_at`` and ``note``. A link must exist, and
    be visible to the person who saves it, at the moment it is saved.

Evidence
    Computed on every read and never stored: for a task whether it is on, its
    schedule, the last run and its result, runs in the last 30 days and the
    hours saved from the value ledger; for a bot whether it exists, is active
    and which tasks it owns; for a skill whether it is installed and switched
    on; for a use case its phase and baseline; for a playbook whether it is
    published and how often it was followed. The status of a row is derived:
    ``live`` only when a linked task completed a run in the last 30 days or a
    linked bot is active, ``built`` when links exist but nothing ran, else the
    manual status. Details of something the viewer may not see are left out;
    the derived status is the same for everybody.

Rights: everybody with a place in the structure, and every partner, reads.
Organisation admins and partners with the role consultant or developer edit.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from api import org_structure, studio
from api.helpers import j

logger = logging.getLogger(__name__)

VERSION = 1
ROW_KINDS = ("fundament", "agent", "werksessie", "borging")
STATUSES = ("planned", "in_progress", "built", "live", "parked")
LINK_TYPES = ("job", "bot", "skill", "use_case", "playbook")
SYSTEM_STATUSES = ("te_valideren", "te_bevestigen", "voorgesteld", "onbekend", "alleen_genoemd", "bevestigd")
EVIDENCE_DAYS = 30

MAX_WEEKS = 104
MAX_GROUPS = 16
MAX_ROWS = 24             # per group
MAX_PHASES = 16
MAX_SYSTEMS = 60
MAX_DIAGRAMS = 16
MAX_LINKS = 12            # per row or phase
MAX_LIST = 20
MAX_DIAGRAM_CHARS = 6000
MAX_IMPORT_BYTES = 200 * 1024

_LOCK = threading.Lock()
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@ -]{0,119}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()/-]{0,39}$")
_DIAGRAM_START = re.compile(r"^(flowchart|graph)\s+(TD|TB|LR|RL|BT)\b")
_DIAGRAM_BANNED = re.compile(r"(?i)\b(click|href|javascript:|call\s|%%\{)")

_ROADMAP_KEYS = {"version", "report_version", "title", "start_date", "weeks", "steering_weeks", "planning_note", "notes",
                 "prerequisites", "open_points", "pilot_criteria", "groups", "safeguarding", "phases", "systems", "diagrams",
                 "updated_at", "updated_by"}
_GROUP_KEYS = {"id", "name", "short", "phase", "rows"}
_ROW_KEYS = {"id", "name", "kind", "start_week", "weeks", "status", "delivered_at", "note", "links"}
_PHASE_KEYS = {"id", "name", "summary", "prerequisites", "human_role", "steps", "pilot_criteria", "ready_when",
               "status", "delivered_at", "note", "links"}
_SYSTEM_KEYS = {"name", "status", "note"}
_DIAGRAM_KEYS = {"id", "title", "phase", "source"}
_NOTE_KEYS = {"proposal", "estimate", "start"}
_LONG_DASHES = (chr(0x2013), chr(0x2014))      # en dash and em dash: not allowed in roadmap text
_NBSP = chr(0xA0)


# ── Storage ──────────────────────────────────────────────────────────────────

def _path() -> Path:
    return studio._dir() / "roadmap.json"


def load() -> dict | None:
    """The stored roadmap, or None when there is none (or it cannot be read)."""
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        logger.warning("studio roadmap unreadable", exc_info=True)
        return None
    return data if isinstance(data, dict) and isinstance(data.get("groups"), list) else None


def _write(doc: dict, actor: str) -> dict:
    doc["version"] = VERSION
    doc["updated_at"] = time.time()
    doc["updated_by"] = actor
    path = _path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    studio._changed()         # the roll-up is part of the central summary
    return doc


def _audit(actor: str, action: str, detail: dict) -> None:
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "actor": actor, "action": action, "detail": detail}
    try:
        with open(studio._dir() / "roadmap_audit.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("studio roadmap audit append failed", exc_info=True)
    try:
        from api.governance.audit import append_audit_event

        append_audit_event("studio_roadmap_changed", subject_email=actor, subject_user_id="",
                           path="/api/studio/roadmap", method="POST", reason=action, extra=detail)
    except Exception:
        logger.debug("governance audit append failed", exc_info=True)


# ── Validation ───────────────────────────────────────────────────────────────

def _text(value, limit: int, name: str, *, required: bool = False) -> str:
    """Plain text: no markup, no control characters, no long dashes, bounded."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    text = " ".join(value.replace(_NBSP, " ").split())
    if len(text) > limit:
        raise ValueError(f"{name} is at most {limit} characters")
    if "<" in text or ">" in text:
        raise ValueError(f"{name} cannot contain markup")
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise ValueError(f"{name} contains a control character")
    if any(dash in text for dash in _LONG_DASHES):
        raise ValueError(f"{name} contains a long dash; use a colon, a comma or parentheses")
    if required and not text:
        raise ValueError(f"{name} is required")
    return text


def _texts(value, count: int, limit: int, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    if len(value) > count:
        raise ValueError(f"{name} has at most {count} entries")
    return [t for t in (_text(v, limit, name) for v in value) if t]


def _int(value, lo: int, hi: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a whole number")
    if value < lo or value > hi:
        raise ValueError(f"{name} must be between {lo} and {hi}")
    return value


def _keys(raw, allowed: set, name: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"Unknown field in {name}: " + ", ".join(sorted(str(k) for k in extra)))
    return raw


def _id(value, name: str, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    if not _ID_RE.match(text):
        raise ValueError(f"{name} must be lowercase letters, digits, dashes or underscores")
    return text


def _date(value, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{name} must be a date such as 2026-12-07")


def clean_links(raw, name: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_LINKS:
        raise ValueError(f"{name} has at most {MAX_LINKS} links")
    out, seen = [], set()
    for item in raw:
        item = _keys(item, {"type", "ref"}, name + " link")
        kind, ref = item.get("type"), str(item.get("ref") or "").strip()
        if kind not in LINK_TYPES:
            raise ValueError("A link is a job, bot, skill, use_case or playbook")
        if not _REF_RE.match(ref):
            raise ValueError("Invalid link reference")
        if (kind, ref) not in seen:
            seen.add((kind, ref))
            out.append({"type": kind, "ref": ref})
    return out


def _execution(raw: dict, name: str) -> dict:
    status = raw.get("status") or "planned"
    if status not in STATUSES:
        raise ValueError(f"{name}: status is planned, in_progress, built, live or parked")
    return {"status": status, "delivered_at": _date(raw.get("delivered_at"), name + " delivered_at"),
            "note": _text(raw.get("note"), 400, name + " note"), "links": clean_links(raw.get("links"), name)}


def _row(raw, weeks: int, name: str, fallback_id: str, kind: str | None = None) -> dict:
    raw = _keys(raw, _ROW_KEYS, name)
    row_kind = kind or raw.get("kind") or "agent"
    if row_kind not in ROW_KINDS:
        raise ValueError(f"{name}: kind is fundament, agent, werksessie or borging")
    start = _int(raw.get("start_week"), 1, weeks, name + " start_week")
    length = _int(raw.get("weeks", 1), 1, weeks, name + " weeks")
    if start + length - 1 > weeks:
        raise ValueError(f"{name} runs past the last week of the roadmap")
    return dict({"id": _id(raw.get("id"), name + " id", fallback_id), "name": _text(raw.get("name"), 120, name + " name", required=True),
                 "kind": row_kind, "start_week": start, "weeks": length}, **_execution(raw, name))


def clean_roadmap(raw) -> dict:
    """The validated roadmap document. Raises ValueError with what is wrong."""
    raw = _keys(raw, _ROADMAP_KEYS, "roadmap")
    version = str(raw.get("report_version") or "").strip()
    if not _VERSION_RE.match(version):
        raise ValueError("report_version is required (for example 1.0)")
    start = _date(raw.get("start_date"), "start_date")
    if not start:
        raise ValueError("start_date is required: the Monday of week 1")
    monday = date.fromisoformat(start)
    monday -= timedelta(days=monday.weekday())
    weeks = _int(raw.get("weeks"), 4, MAX_WEEKS, "weeks")
    steering = raw.get("steering_weeks") or []
    if not isinstance(steering, list) or len(steering) > 30:
        raise ValueError("steering_weeks must be a list of week numbers")
    steering = sorted({_int(wk, 1, weeks, "steering week") for wk in steering})
    notes = _keys(raw.get("notes") or {}, _NOTE_KEYS, "notes")

    phases, phase_ids = [], set()
    raw_phases = raw.get("phases") or []
    if not isinstance(raw_phases, list) or len(raw_phases) > MAX_PHASES:
        raise ValueError(f"phases has at most {MAX_PHASES} entries")
    for i, item in enumerate(raw_phases):
        name = f"phase {i + 1}"
        item = _keys(item, _PHASE_KEYS, name)
        pid = _id(item.get("id"), name + " id", f"p{i + 1}")
        if pid in phase_ids:
            raise ValueError(f"{name}: id {pid} is used twice")
        phase_ids.add(pid)
        phases.append(dict({"id": pid, "name": _text(item.get("name"), 120, name + " name", required=True),
                            "summary": _text(item.get("summary"), 600, name + " summary"),
                            "prerequisites": _texts(item.get("prerequisites"), MAX_LIST, 300, name + " prerequisites"),
                            "human_role": _text(item.get("human_role"), 400, name + " human_role"),
                            "steps": _texts(item.get("steps"), MAX_LIST, 300, name + " steps"),
                            "pilot_criteria": _texts(item.get("pilot_criteria"), MAX_LIST, 300, name + " pilot_criteria"),
                            "ready_when": _text(item.get("ready_when"), 400, name + " ready_when")}, **_execution(item, name)))

    groups, row_ids, group_ids = [], set(), set()
    raw_groups = raw.get("groups")
    if not isinstance(raw_groups, list) or not raw_groups or len(raw_groups) > MAX_GROUPS:
        raise ValueError(f"groups needs between 1 and {MAX_GROUPS} blocks")
    for g, item in enumerate(raw_groups):
        name = f"group {g + 1}"
        item = _keys(item, _GROUP_KEYS, name)
        gid = _id(item.get("id"), name + " id", f"g{g}")
        if gid in group_ids:
            raise ValueError(f"{name}: id {gid} is used twice")
        group_ids.add(gid)
        phase = str(item.get("phase") or "").strip()
        if phase and phase not in phase_ids:
            raise ValueError(f"{name}: phase {phase} is not one of the phases")
        raw_rows = item.get("rows") or []
        if not isinstance(raw_rows, list) or len(raw_rows) > MAX_ROWS:
            raise ValueError(f"{name} has at most {MAX_ROWS} rows")
        rows = []
        for r, row in enumerate(raw_rows):
            clean = _row(row, weeks, f"{name} row {r + 1}", f"{gid}r{r + 1}")
            if clean["id"] in row_ids:
                raise ValueError(f"{name}: row id {clean['id']} is used twice")
            row_ids.add(clean["id"])
            rows.append(clean)
        groups.append({"id": gid, "name": _text(item.get("name"), 120, name + " name", required=True),
                       "short": _text(item.get("short"), 24, name + " short"), "phase": phase, "rows": rows})
    if raw.get("safeguarding"):
        # The closing row of the planning (documentation, handover). Kept as a last block of one row.
        row = _row(raw["safeguarding"], weeks, "safeguarding", "safeguarding", kind="borging")
        if row["id"] in row_ids or "safeguarding" in group_ids:
            raise ValueError("safeguarding: id is used twice")
        groups.append({"id": "safeguarding", "name": row["name"], "short": "", "phase": "", "rows": [row]})
    if len(groups) > MAX_GROUPS:
        raise ValueError(f"groups needs between 1 and {MAX_GROUPS} blocks")

    systems = []
    raw_systems = raw.get("systems") or []
    if not isinstance(raw_systems, list) or len(raw_systems) > MAX_SYSTEMS:
        raise ValueError(f"systems has at most {MAX_SYSTEMS} entries")
    for i, item in enumerate(raw_systems):
        item = _keys(item, _SYSTEM_KEYS, f"system {i + 1}")
        status = item.get("status") or "onbekend"
        if status not in SYSTEM_STATUSES:
            raise ValueError(f"system {i + 1}: status is one of " + ", ".join(SYSTEM_STATUSES))
        systems.append({"name": _text(item.get("name"), 80, f"system {i + 1} name", required=True), "status": status,
                        "note": _text(item.get("note"), 300, f"system {i + 1} note")})

    diagrams, diagram_ids = [], set()
    raw_diagrams = raw.get("diagrams") or []
    if not isinstance(raw_diagrams, list) or len(raw_diagrams) > MAX_DIAGRAMS:
        raise ValueError(f"diagrams has at most {MAX_DIAGRAMS} entries")
    for i, item in enumerate(raw_diagrams):
        name = f"diagram {i + 1}"
        item = _keys(item, _DIAGRAM_KEYS, name)
        did = _id(item.get("id"), name + " id", f"d{i + 1}")
        if did in diagram_ids:
            raise ValueError(f"{name}: id {did} is used twice")
        diagram_ids.add(did)
        phase = str(item.get("phase") or "").strip()
        if phase and phase not in phase_ids:
            raise ValueError(f"{name}: phase {phase} is not one of the phases")
        diagrams.append({"id": did, "title": _text(item.get("title"), 120, name + " title", required=True), "phase": phase,
                         "source": clean_diagram(item.get("source"), name)})

    return {"version": VERSION, "report_version": version, "title": _text(raw.get("title"), 120, "title"),
            "start_date": monday.isoformat(), "weeks": weeks, "steering_weeks": steering,
            "planning_note": _text(raw.get("planning_note"), 600, "planning_note"),
            "notes": {k: _text(notes.get(k), 600, "notes " + k) for k in sorted(_NOTE_KEYS)},
            "prerequisites": _texts(raw.get("prerequisites"), MAX_LIST, 300, "prerequisites"),
            "open_points": _texts(raw.get("open_points"), MAX_LIST, 300, "open_points"),
            "pilot_criteria": _texts(raw.get("pilot_criteria"), MAX_LIST, 300, "pilot_criteria"),
            "groups": groups, "phases": phases, "systems": systems, "diagrams": diagrams}


def clean_diagram(value, name: str) -> str:
    """A Mermaid flowchart source: plain flowchart text only, no markup and no click or link directives."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} needs a Mermaid source")
    source = value.replace("\r\n", "\n").strip()
    if len(source) > MAX_DIAGRAM_CHARS:
        raise ValueError(f"{name} is at most {MAX_DIAGRAM_CHARS} characters")
    if not _DIAGRAM_START.match(source):
        raise ValueError(f"{name} must start with flowchart TD")
    if "<" in source or "`" in source or _DIAGRAM_BANNED.search(source):
        raise ValueError(f"{name} cannot contain markup, links or click actions")
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127 for c in source):
        raise ValueError(f"{name} contains a control character")
    if any(dash in source for dash in _LONG_DASHES):
        raise ValueError(f"{name} contains a long dash; use a colon, a comma or parentheses")
    return source


# ── Who may do what, and what exists ─────────────────────────────────────────

def can_view(view) -> bool:
    return bool(view.email) and (view.scope != org_structure.SCOPE_NONE or view.is_partner)


def can_edit(view) -> bool:
    return bool(view.email) and (view.scope == org_structure.SCOPE_ALL or view.partner_edits)


class World:
    """What exists in the installation, read once per request.

    ``sees_job(profile, job)`` and ``view`` narrow it to what the caller may
    see; without them (the central summary) everything counts, and only
    numbers leave.
    """

    def __init__(self, view=None, sees_job=None, now: float | None = None):
        self.view = view
        self.sees_job = sees_job
        self.now = time.time() if now is None else now
        self._jobs = self._bots = self._runs = self._chats = self._saved = self._skills = None

    # jobs: key "profile:id"; a bare id also resolves when it is unique
    def jobs(self) -> dict:
        if self._jobs is None:
            self._jobs = {}
            try:
                from api import value_tracking

                for profile, job in value_tracking.iter_store_jobs():
                    if job.get("id"):
                        self._jobs[f"{profile}:{job['id']}"] = (profile, job)
            except Exception:
                logger.warning("roadmap could not read the scheduled tasks", exc_info=True)
        return self._jobs

    def job(self, ref: str):
        jobs = self.jobs()
        if ref in jobs:
            return jobs[ref]
        hits = [v for k, v in jobs.items() if k.split(":", 1)[1] == ref]
        return hits[0] if len(hits) == 1 else None

    def job_visible(self, profile: str, job: dict) -> bool:
        if self.sees_job is None:
            return True
        try:
            return bool(self.sees_job(profile, job))
        except Exception:
            return False

    def bots(self) -> set:
        if self._bots is None:
            try:
                from api import profiles

                self._bots = {str(p.get("name")) for p in profiles.list_profiles_api(fast=True, include_skill_counts=False)
                              if isinstance(p, dict) and p.get("name")}
            except Exception:
                logger.warning("roadmap could not read the bots", exc_info=True)
                self._bots = set()
        return self._bots

    def skills(self) -> dict:
        """Installed skill names with whether they are switched on."""
        if self._skills is None:
            self._skills = {}
            try:
                from api.profiles import get_hermes_home_for_profile

                root = Path(get_hermes_home_for_profile("default")) / "skills"
                names = {p.parent.name for pattern in ("*/SKILL.md", "*/*/SKILL.md", "*/*/*/SKILL.md") for p in root.glob(pattern)}
                try:
                    from api.routes import _get_disabled_skill_names_for_profile

                    off = _get_disabled_skill_names_for_profile()
                except Exception:
                    off = set()
                self._skills = {name: name not in off for name in names}
            except Exception:
                logger.warning("roadmap could not read the skills", exc_info=True)
        return self._skills

    def _ledger(self) -> None:
        if self._runs is not None:
            return
        self._runs, self._chats, self._saved = [], [], {}
        try:
            from api import value_tracking

            start = self.now - EVIDENCE_DAYS * 86400
            self._runs = value_tracking.runs_between(start, self.now + 1)
            self._chats = value_tracking.chats_between(start, self.now + 1)
            per = {key: ((job.get("value") or {}).get("per") if isinstance(job.get("value"), dict) else None)
                   for key, (_p, job) in self.jobs().items()}
            self._saved = value_tracking.saved_minutes_by_job(start, self.now + 1, per)
        except Exception:
            logger.warning("roadmap could not read the value ledger", exc_info=True)

    def runs(self, key: str) -> list[dict]:
        self._ledger()
        return [r for r in self._runs if f"{r.get('store')}:{r.get('job_id')}" == key]

    def saved_minutes(self, key: str) -> int:
        self._ledger()
        return int(self._saved.get(key, 0))

    def bot_active(self, name: str) -> bool:
        """A bot is active when one of its tasks completed a run, or somebody chatted with it, in the period."""
        self._ledger()
        return any(r.get("bot") == name and r.get("status") == "ok" for r in self._runs) or any(
            c.get("bot") == name for c in self._chats)


def _stamp(value) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _job_key(world: World, ref: str) -> str:
    hit = world.job(ref)
    return f"{hit[0]}:{hit[1]['id']}" if hit else ""


def check_links(links: list[dict], world: World) -> None:
    """Every link must exist and be visible to the person who saves it. Raises ValueError."""
    from api import studio_library

    view = world.view
    for link in links:
        kind, ref = link["type"], link["ref"]
        if kind == "job":
            hit = world.job(ref)
            ok = bool(hit) and world.job_visible(*hit)
        elif kind == "bot":
            ok = ref in world.bots()
        elif kind == "skill":
            ok = ref in world.skills()
        elif kind == "use_case":
            try:
                ok = view is None or studio._visible(view, studio._load(ref))
            except (KeyError, OSError, ValueError):
                ok = False
        else:
            try:
                ok = view is None or studio_library._pb_visible(view, studio_library._pb_load(ref))
            except (KeyError, OSError, ValueError):
                ok = False
        if not ok:
            raise ValueError(f"Linked {kind.replace('_', ' ')} not found: {ref}")


# ── Evidence and derived status ──────────────────────────────────────────────

def link_evidence(link: dict, world: World) -> dict:
    """What is true right now about one link. ``visible`` False means the details are left out."""
    from api import cron_bots, studio_library

    kind, ref = link["type"], link["ref"]
    out = {"type": kind, "ref": ref, "found": False, "visible": True, "live": False}
    if kind == "job":
        hit = world.job(ref)
        if not hit:
            return out
        profile, job = hit
        key = f"{profile}:{job['id']}"
        runs = world.runs(key)
        ok_runs = [r for r in runs if r.get("status") == "ok"]
        last = _stamp(job.get("last_run_at"))
        status = str(job.get("last_status") or "").lower()
        result = "ok" if status in ("ok", "success", "completed") else "failed" if status in ("error", "failed", "failure") else ""
        ledger_last = max((r.get("finished_at") or 0 for r in runs), default=0) or None
        if ledger_last and (last is None or ledger_last > last):
            newest = max(runs, key=lambda r: r.get("finished_at") or 0)
            last, result = ledger_last, newest.get("status") or result
        recent_ok = bool(ok_runs) or (result == "ok" and last is not None and world.now - last <= EVIDENCE_DAYS * 86400)
        out.update(found=True, live=recent_ok, visible=world.job_visible(profile, job))
        if out["visible"]:
            out.update(name=str(job.get("name") or job["id"]), store=profile, job_id=str(job["id"]),
                       bot=cron_bots.job_bot(job, profile),
                       enabled=job.get("enabled") is not False and job.get("state") != "paused",
                       schedule=str(job.get("schedule_display") or ""), last_run_at=last, last_result=result,
                       runs_30d=len(runs), ok_runs_30d=len(ok_runs),
                       hours_saved_30d=round(world.saved_minutes(key) / 60, 1))
        return out
    if kind == "bot":
        if ref not in world.bots():
            return out
        owned = [(p, job) for p, job in world.jobs().values() if cron_bots.job_bot(job, p) == ref]
        out.update(found=True, live=world.bot_active(ref), name=ref, active=world.bot_active(ref),
                   tasks=[{"name": str(job.get("name") or job.get("id")), "enabled": job.get("enabled") is not False and job.get("state") != "paused"}
                          for p, job in owned if world.job_visible(p, job)][:20],
                   tasks_total=len(owned))
        return out
    if kind == "skill":
        skills = world.skills()
        if ref in skills:
            out.update(found=True, name=ref, installed=True, enabled=bool(skills[ref]), last_used_at=None)
        return out
    if kind == "use_case":
        try:
            doc = studio._load(ref)
        except (KeyError, OSError, ValueError):
            return out
        base = ((doc.get("process") or {}).get("baseline") or {}) if isinstance(doc.get("process"), dict) else {}
        before, after = base.get("hours_week_before"), base.get("hours_week_after")
        saved = round(max(0.0, before - after), 1) if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None
        out.update(found=True, phase=doc.get("phase") if doc.get("phase") in studio.PHASES else "discover",
                   hours_week_before=before, hours_week_after=after, hours_week_saved=saved,
                   visible=world.view is None or studio._visible(world.view, doc))
        if out["visible"]:
            out["name"] = studio._txt(doc.get("title"), 120)
        return out
    try:
        pb = studio_library._pb_load(ref)
    except (KeyError, OSError, ValueError):
        return out
    stats = studio_library.run_stats(pb)
    out.update(found=True, published=pb.get("status") == "published", runs=stats["runs"], last_run_at=stats["last_at"],
               visible=world.view is None or studio_library._pb_visible(world.view, pb))
    if out["visible"]:
        out["name"] = studio._txt(pb.get("title"), 120)
    return out


def derive(item: dict, world: World) -> dict:
    """Evidence and status of one row or phase.

    ``live`` only with a completed run of a linked task in the period or an
    active linked bot; ``built`` when something that exists is linked but
    nothing ran; otherwise what was set by hand.
    """
    evidence = [link_evidence(link, world) for link in item.get("links") or []]
    manual = item.get("status") if item.get("status") in STATUSES else "planned"
    found = [e for e in evidence if e["found"]]
    if any(e["live"] for e in found if e["type"] in ("job", "bot")):
        status, derived = "live", True
    elif found:
        status, derived = "built", True
    else:
        status, derived = manual, False
    return {"status": status, "manual": manual, "derived": derived, "differs": derived and status != manual,
            "evidence": evidence}


def _job_keys(item: dict, world: World) -> set:
    return {k for k in (_job_key(world, link["ref"]) for link in item.get("links") or [] if link["type"] == "job") if k}


def _use_cases(item: dict) -> set:
    return {link["ref"] for link in item.get("links") or [] if link["type"] == "use_case"}


def _baseline(refs: set) -> float:
    total = 0.0
    for ref in refs:
        try:
            base = ((studio._load(ref).get("process") or {}).get("baseline") or {})
        except (KeyError, OSError, ValueError, AttributeError):
            continue
        before, after = base.get("hours_week_before"), base.get("hours_week_after")
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and before > after:
            total += before - after
    return round(total, 1)


def _per_week(minutes: int) -> float:
    return round(minutes / 60 / (EVIDENCE_DAYS / 7), 1)


def assess(doc: dict, world: World) -> dict:
    """Status and evidence per row and phase, and the roll-up per block and for the whole roadmap."""
    rows, phases, blocks = {}, {}, []
    all_jobs, all_cases = set(), set()
    for phase in doc.get("phases") or []:
        phases[phase["id"]] = derive(phase, world)
    for group in doc.get("groups") or []:
        counts = {"planned": 0, "built": 0, "live": 0}
        jobs, cases = set(), set()
        linked_phase = next((p for p in doc.get("phases") or [] if p["id"] == group.get("phase")), None)
        for row in group.get("rows") or []:
            result = derive(row, world)
            rows[row["id"]] = result
            counts[result["status"] if result["status"] in ("built", "live") else "planned"] += 1
            jobs |= _job_keys(row, world)
            cases |= _use_cases(row)
        if linked_phase is not None:
            jobs |= _job_keys(linked_phase, world)
            cases |= _use_cases(linked_phase)
        all_jobs |= jobs
        all_cases |= cases
        blocks.append({"id": group["id"], "name": group["name"], "rows_total": len(group.get("rows") or []),
                       "rows_planned": counts["planned"], "rows_built": counts["built"], "rows_live": counts["live"],
                       "measured_hours_week_saved": _per_week(sum(world.saved_minutes(k) for k in jobs)),
                       "baseline_hours_week_saved": _baseline(cases)})
    for phase in doc.get("phases") or []:
        all_jobs |= _job_keys(phase, world)
        all_cases |= _use_cases(phase)
    total = sum(b["rows_total"] for b in blocks)
    return {"rows": rows, "phases": phases,
            "rollup": {"blocks": blocks, "rows_total": total,
                       "rows_planned": sum(b["rows_planned"] for b in blocks),
                       "rows_built": sum(b["rows_built"] for b in blocks),
                       "rows_live": sum(b["rows_live"] for b in blocks),
                       "measured_hours_week_saved": _per_week(sum(world.saved_minutes(k) for k in all_jobs)),
                       "baseline_hours_week_saved": _baseline(all_cases), "period_days": EVIDENCE_DAYS}}


def summary_block() -> dict | None:
    """The roadmap progress for the central summary: counts and block names only."""
    doc = load()
    if doc is None:
        return None
    rollup = assess(doc, World())["rollup"]
    stamp = doc.get("updated_at")
    return {"report_version": str(doc.get("report_version") or ""),
            "updated_at": datetime.fromtimestamp(float(stamp), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if isinstance(stamp, (int, float)) else "",
            "blocks": [{"name": b["name"], "rows_total": b["rows_total"], "rows_built": b["rows_built"], "rows_live": b["rows_live"]}
                       for b in rollup["blocks"]],
            "rows_total": rollup["rows_total"], "rows_built": rollup["rows_built"], "rows_live": rollup["rows_live"],
            "measured_hours_week_saved": rollup["measured_hours_week_saved"]}


# ── Reading and changing ─────────────────────────────────────────────────────

def read(view, world: World | None = None) -> dict:
    if not can_view(view):
        raise PermissionError("The roadmap is for people with a place in the organisation and for assigned partners")
    world = world or World(view=view)
    doc = load()
    out = {"roadmap": doc, "editable": can_edit(view), "viewer": view.to_dict(), "today": date.today().isoformat(),
           "kinds": list(ROW_KINDS), "statuses": list(STATUSES), "link_types": list(LINK_TYPES)}
    if doc is not None:
        out.update(assess(doc, world))
    return out


def import_roadmap(view, raw, world: World | None = None) -> dict:
    """Replace the roadmap by a validated document. Raises PermissionError or ValueError."""
    if not can_edit(view):
        raise PermissionError("Only organisation admins and assigned consultants or developers change the roadmap")
    try:
        size = len(json.dumps(raw, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        raise ValueError("The roadmap must be a JSON document")
    if size > MAX_IMPORT_BYTES:
        raise ValueError("The roadmap document is too large")
    doc = clean_roadmap(raw)
    world = world or World(view=view)
    for group in doc["groups"]:
        for row in group["rows"]:
            check_links(row["links"], world)
    for phase in doc["phases"]:
        check_links(phase["links"], world)
    with _LOCK:
        before = load()
        _write(doc, view.email)
    _audit(view.email, "import", {"report_version": doc["report_version"], "previous_version": (before or {}).get("report_version"),
                                  "groups": len(doc["groups"]), "rows": sum(len(g["rows"]) for g in doc["groups"]),
                                  "phases": len(doc["phases"])})
    return doc


def update_item(view, body: dict, world: World | None = None) -> dict:
    """Set status, delivered_at, note and links of one row or phase."""
    if not can_edit(view):
        raise PermissionError("Only organisation admins and assigned consultants or developers change the roadmap")
    target, item_id = body.get("target"), str(body.get("id") or "")
    if target not in ("row", "phase"):
        raise ValueError("Target is row or phase")
    extra = set(body) - {"op", "target", "id", "status", "delivered_at", "note", "links"}
    if extra:
        raise ValueError("Unknown field: " + ", ".join(sorted(extra)))
    world = world or World(view=view)
    with _LOCK:
        doc = load()
        if doc is None:
            raise KeyError("There is no roadmap yet")
        items = doc.get("phases") or [] if target == "phase" else [r for g in doc.get("groups") or [] for r in g.get("rows") or []]
        item = next((i for i in items if i.get("id") == item_id), None)
        if item is None:
            raise KeyError("Row not found" if target == "row" else "Phase not found")
        merged = {k: body[k] if k in body else item.get(k) for k in ("status", "delivered_at", "note", "links")}
        clean = _execution(merged, target)
        added = [link for link in clean["links"] if link not in (item.get("links") or [])]
        check_links(added, world)       # what was linked before may stay, also when it has gone since
        item.update(clean)
        _write(doc, view.email)
    _audit(view.email, target + ".update", {"id": item_id, "status": clean["status"], "delivered_at": clean["delivered_at"],
                                           "links": [f"{link['type']}:{link['ref']}" for link in clean["links"]]})
    return doc


def remove(view) -> None:
    if view.scope != org_structure.SCOPE_ALL:
        raise PermissionError("Only organisation admins remove the roadmap")
    with _LOCK:
        doc = load()
        if doc is None:
            raise KeyError("There is no roadmap yet")
        _path().unlink()
        studio._changed()
    _audit(view.email, "remove", {"report_version": doc.get("report_version")})


def link_options(view, world: World) -> dict:
    """What the caller can link, each under their own rights."""
    from api import cron_bots, studio_library

    if not can_edit(view):
        raise PermissionError("Only organisation admins and assigned consultants or developers change the roadmap")
    jobs = [{"value": key, "label": str(job.get("name") or job.get("id")), "hint": cron_bots.job_bot(job, profile)}
            for key, (profile, job) in sorted(world.jobs().items()) if world.job_visible(profile, job)]
    return {"job": jobs[:500],
            "bot": [{"value": name, "label": name} for name in sorted(world.bots())][:200],
            "skill": [{"value": name, "label": name} for name in sorted(world.skills())][:500],
            "use_case": [{"value": row["id"], "label": row.get("title") or row["id"]} for row in studio.list_for(view)][:500],
            "playbook": [{"value": row["id"], "label": row.get("title") or row["id"]} for row in studio_library.playbooks_for(view)][:500]}


# ── HTTP ─────────────────────────────────────────────────────────────────────

ROUTES = ("/api/studio/roadmap", "/api/studio/roadmap/options")


def _world(handler, view) -> World:
    def sees_job(profile, job):
        from api import cron_scope

        return cron_scope.identity_sees_cron_row(cron_scope._identity_for(handler), job, store_profile=str(profile))

    return World(view=view, sees_job=sees_job)


def handle_get(handler, parsed) -> bool:
    path = str(getattr(parsed, "path", "") or "")
    if path not in ROUTES:
        return False
    view = org_structure.request_scope(handler)
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        world = _world(handler, view)
        if path == "/api/studio/roadmap/options":
            j(handler, link_options(view, world))
            return True
        try:
            from api import value_tracking

            value_tracking.collect()        # rate limited; keeps the run evidence fresh
        except Exception:
            logger.debug("value collect skipped for the roadmap", exc_info=True)
        j(handler, read(view, world))
    except PermissionError as e:
        j(handler, {"error": str(e), "reason": "org_scope"}, status=403)
    except Exception:
        logger.exception("GET %s failed", path)
        j(handler, {"error": "internal_error"}, status=500)
    return True


def handle_post(handler, parsed, body) -> bool:
    if str(getattr(parsed, "path", "") or "") != "/api/studio/roadmap":
        return False
    view = org_structure.request_scope(handler)
    body = body if isinstance(body, dict) else {}
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        world = _world(handler, view)
        op = body.get("op")
        if op == "import":
            import_roadmap(view, body.get("roadmap"), world)
        elif op == "update":
            update_item(view, body, world)
        elif op == "remove":
            remove(view)
        else:
            raise ValueError("Unknown operation")
        j(handler, read(view, world))
    except PermissionError as e:
        j(handler, {"error": str(e), "reason": "org_scope"}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except Exception:
        logger.exception("POST /api/studio/roadmap failed")
        j(handler, {"error": "internal_error"}, status=500)
    return True
