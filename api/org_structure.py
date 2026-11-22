"""Team structure: departments, teams, leads, members and reporting lines.

The governance policy knows departments only on a client installation, and
there they are rendered centrally from client.yaml (``api/governance/
delegation.py``). HQ has no organisation block at all. Teams, team leads and
reporting lines exist nowhere yet. This module keeps them in one small
document under the WebUI state directory, layered on top of the policy:

* departments of the policy (client installations) appear read-only by key
  and name; extra departments can be added here (that is how HQ gets any);
* teams always live here, each under one department key, optionally under a
  parent team of the same department (sub-teams);
* people carry an optional title and ``reports_to``.

Who may see and change what
---------------------------
``view_scope(identity)`` answers it once per request and every handler
filters through it:

    all          platform admins and organisation admins (delegation.py)
    departments  department admins from the policy, plus the ``admins`` of a
                 department in this document
    teams        leads of a team see their team; members see their own team
    none         everybody else

Editing: ``all`` edits everything; a department admin edits the teams of
their own departments. Team leads and members read only. Every mutation is
written atomically under a file lock and appended to ``audit.jsonl``.

Partners
--------
``partners`` is one list for the whole installation: the staff of the
supplier that the central Cloud assigned to it (consultant, developer, qa),
each with a start and an end. The normal source is a pull from the control
plane (``api/studio_report.py``, ``source: cloud``); an organisation admin
can add local ones. A current partner gets ``ViewScope.partner_role`` and
nothing else: Studio reads that role to let a consultant or developer work
on the use cases, backlog and playbooks of the teams. It never widens
``scope``, so a partner edits no structure and sees no rates or Management
figures, and the moment the assignment ends or is removed the role is gone.

The document is organisation data, not authorisation: it never grants a
tool, a profile or a route. Rights stay in the governance policy.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from api.helpers import j

logger = logging.getLogger(__name__)

VERSION = 1
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
_EMAIL_RE = re.compile(r"^[^@\s]{1,128}@[^@\s]{1,253}$")
_NAME_MAX = 80
_TITLE_MAX = 80
_TEAMS_MAX = 400
_MEMBERS_MAX = 500
_LOCK = threading.Lock()

SCOPE_ALL = "all"
SCOPE_DEPARTMENTS = "departments"
SCOPE_TEAMS = "teams"
SCOPE_NONE = "none"

PARTNER_ROLES = ("consultant", "developer", "qa")
PARTNER_EDIT_ROLES = ("consultant", "developer")
PARTNER_ORG = "synthwave"
PARTNER_SOURCES = ("cloud", "local")
_PARTNERS_MAX = 50


# ── Storage ──────────────────────────────────────────────────────────────────

def _dir() -> Path:
    from api.config import STATE_DIR

    path = Path(STATE_DIR) / "org_structure"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path() -> Path:
    return _dir() / "structure.json"


def _empty() -> dict:
    return {"version": VERSION, "departments": {}, "teams": {}, "people": {}, "partners": [],
            "updated_at": None, "updated_by": None}


def load() -> dict:
    """The stored document; a missing or damaged file reads as empty."""
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _empty()
    except (OSError, ValueError):
        logger.warning("org structure unreadable; treating as empty", exc_info=True)
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    base = _empty()
    for key in ("departments", "teams", "people"):
        value = data.get(key)
        base[key] = value if isinstance(value, dict) else {}
    partners = data.get("partners")
    base["partners"] = [p for p in partners if isinstance(p, dict)] if isinstance(partners, list) else []
    base["updated_at"] = data.get("updated_at")
    base["updated_by"] = data.get("updated_by")
    return base


@contextmanager
def _locked():
    lock_path = _dir() / ".lock"
    with _LOCK:
        with open(lock_path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)


def _write(data: dict) -> None:
    path = _path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _audit(actor: str, action: str, detail: dict) -> None:
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "actor": actor, "action": action, "detail": detail}
    try:
        with open(_dir() / "audit.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("org structure audit append failed", exc_info=True)
    try:
        from api.governance.audit import append_audit_event

        append_audit_event("org_structure_changed", subject_email=actor, subject_user_id="",
                           path="/api/org/structure", method="POST", reason=action,
                           extra={k: v for k, v in detail.items() if k != "members"})
    except Exception:
        logger.debug("governance audit append failed", exc_info=True)


# ── Validation helpers ───────────────────────────────────────────────────────

def norm_email(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _EMAIL_RE.match(text) else ""


def _clean_text(value: Any, limit: int, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    text = " ".join(value.split())
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise ValueError(f"Invalid {field_name}")
    if len(text) > limit:
        raise ValueError(f"{field_name} is at most {limit} characters")
    return text


def slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text[:40] or "team"


def _rate(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("Hourly rate must be a number")
    if number < 0 or number > 10000:
        raise ValueError("Hourly rate must be between 0 and 10000")
    return round(number, 2)


# ── Partners: staff of the supplier assigned to this installation ────────────

def _instant(value: Any, *, end: bool = False) -> float | None:
    """Epoch seconds of a date (``2026-12-01``) or an ISO date-time; None when empty.

    A bare date as an end counts through the whole of that day (UTC). Raises
    ValueError on anything else.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            moment = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if end:
                moment += timedelta(days=1)
            return moment.timestamp()
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Use a date such as 2026-12-01")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _when(value: Any, field_name: str) -> str:
    """A stored start or end: a date, or a UTC date-time, or ""."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        stamp = _instant(text)
    except ValueError:
        raise ValueError(f"{field_name} must be a date such as 2026-12-01")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_partner(raw: Any, source: str) -> dict:
    """One validated partner row. Raises ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("Invalid partner")
    email = norm_email(raw.get("email"))
    if not email:
        raise ValueError("A partner needs an e-mail address")
    role = str(raw.get("role") or "").strip().lower()
    if role not in PARTNER_ROLES:
        raise ValueError("A partner is a consultant, a developer or qa")
    if source not in PARTNER_SOURCES:
        raise ValueError("Unknown partner source")
    starts, ends = _when(raw.get("starts_at"), "Start"), _when(raw.get("ends_at"), "End")
    if starts and ends and _instant(ends, end=True) <= _instant(starts):
        raise ValueError("The end lies before the start")
    return {"email": email, "name": _clean_text(raw.get("name"), _NAME_MAX, "Name"), "role": role,
            "org": PARTNER_ORG, "starts_at": starts, "ends_at": ends, "source": source}


def partner_is_current(row: dict, now: float | None = None) -> bool:
    """Inside its start and end. A row that cannot be read is not current."""
    if not isinstance(row, dict) or row.get("role") not in PARTNER_ROLES or not norm_email(row.get("email")):
        return False
    now = time.time() if now is None else now
    try:
        starts, ends = _instant(row.get("starts_at")), _instant(row.get("ends_at"), end=True)
    except ValueError:
        return False
    return (starts is None or now >= starts) and (ends is None or now < ends)


def current_partners(data: dict | None = None, now: float | None = None) -> list[dict]:
    """The partners assigned right now, one row per e-mail (a central assignment wins)."""
    data = data or load()
    rows: dict[str, dict] = {}
    for row in data.get("partners") or []:
        if not partner_is_current(row, now):
            continue
        email = norm_email(row.get("email"))
        if email not in rows or (row.get("source") == "cloud" and rows[email].get("source") != "cloud"):
            rows[email] = row
    return [partner_public(rows[e]) for e in sorted(rows, key=lambda e: (PARTNER_ROLES.index(rows[e]["role"]), e))]


def partner_public(row: dict) -> dict:
    return {"email": norm_email(row.get("email")), "name": str(row.get("name") or ""), "role": row.get("role"),
            "org": PARTNER_ORG, "starts_at": row.get("starts_at") or "", "ends_at": row.get("ends_at") or "",
            "source": row.get("source") if row.get("source") in PARTNER_SOURCES else "local"}


def partner_for(email: str, data: dict | None = None, now: float | None = None) -> dict | None:
    """The current assignment of ``email``, or None."""
    email = norm_email(email)
    if not email:
        return None
    return next((p for p in current_partners(data, now) if p["email"] == email), None)


def cloud_partner_for(email: str, data: dict | None = None, now: float | None = None) -> dict | None:
    """The current assignment of ``email`` that came from the control plane, or None.

    This is the only partner fact the governance resolver reads (the
    ``synthwave_partner`` role, see ``api/governance/resolver.py``): a partner
    that an organisation admin added locally works in Studio but gets no
    sign-in and no route from it.
    """
    partner = partner_for(email, data, now)
    return partner if partner and partner.get("source") == "cloud" else None


def replace_cloud_partners(assignments: list, actor: str = "cloud") -> dict:
    """Replace every ``source: cloud`` partner by ``assignments``; local ones stay.

    Rows that do not validate are skipped (counted), so one bad row from the
    control plane never removes the others. Written and audited only when the
    list changed. Returns ``{"changed", "count", "skipped"}``.
    """
    clean, skipped, seen = [], 0, set()
    for raw in (assignments or [])[:_PARTNERS_MAX * 2]:
        try:
            row = clean_partner(raw, "cloud")
        except ValueError:
            skipped += 1
            continue
        if row["email"] in seen or len(clean) >= _PARTNERS_MAX:
            skipped += 1
            continue
        seen.add(row["email"])
        clean.append(row)
    clean.sort(key=lambda r: r["email"])
    with _locked():
        data = load()
        before = [p for p in data["partners"] if p.get("source") == "cloud"]
        local = [p for p in data["partners"] if p.get("source") != "cloud"]
        changed = sorted(before, key=lambda r: str(r.get("email"))) != clean
        if changed:
            data["partners"] = clean + local
            _touch(data, actor)
            _write(data)
    if changed:
        _audit(actor, "partners.sync", {"partners": [{"email": r["email"], "role": r["role"], "ends_at": r["ends_at"]} for r in clean],
                                        "removed": sorted({str(p.get("email")) for p in before} - seen)})
    return {"changed": changed, "count": len(clean), "skipped": skipped}


# ── Policy view ──────────────────────────────────────────────────────────────

def _policy():
    from api.governance import loader

    try:
        return loader.get_policy()
    except Exception:
        logger.warning("governance policy unavailable for org structure", exc_info=True)
        return None


def _policy_departments(policy) -> dict:
    from api.governance import delegation

    if policy is None or not delegation.organization_id(policy):
        return {}
    out = {}
    for key, dept in (policy.departments or {}).items():
        out[key] = {
            "name": dept.name or key,
            "admins": sorted(dept.admins),
            "source": "policy",
            "members": list(delegation.department_members(policy, key)),
        }
    return out


def departments(data: dict | None = None, policy=None) -> dict:
    """Policy departments (read-only names) merged with local ones."""
    data = data or load()
    merged = _policy_departments(policy if policy is not None else _policy())
    for key, row in (data.get("departments") or {}).items():
        if not isinstance(row, dict):
            continue
        base = merged.get(key, {"name": key, "admins": [], "source": "local", "members": []})
        local_admins = [e for e in (row.get("admins") or []) if norm_email(e)]
        merged[key] = {
            "name": base["name"] if base.get("source") == "policy" else (row.get("name") or key),
            "admins": sorted(set(base.get("admins", [])) | set(local_admins)),
            "source": base.get("source", "local"),
            "members": base.get("members", []),
            "hourly_rate": row.get("hourly_rate"),
        }
    return merged


# ── Scope ────────────────────────────────────────────────────────────────────

@dataclass
class ViewScope:
    email: str = ""
    scope: str = SCOPE_NONE
    departments: set[str] = field(default_factory=set)
    lead_teams: set[str] = field(default_factory=set)
    member_teams: set[str] = field(default_factory=set)
    # Set for a current partner (consultant, developer, qa). Separate from
    # ``scope`` on purpose: it opens Studio work, never structure or money.
    partner_role: str | None = None

    @property
    def is_none(self) -> bool:
        return self.scope == SCOPE_NONE

    @property
    def is_partner(self) -> bool:
        return self.partner_role in PARTNER_ROLES

    @property
    def partner_edits(self) -> bool:
        """Consultants and developers work on Studio content; qa only reads."""
        return self.partner_role in PARTNER_EDIT_ROLES

    @property
    def partner_read_only(self) -> bool:
        """A partner that only reads (qa) and has no place of their own in the structure."""
        return self.is_partner and not self.partner_edits and self.scope == SCOPE_NONE

    def sees_department(self, key: str) -> bool:
        return self.scope == SCOPE_ALL or key in self.departments

    def sees_team(self, team_key: str, team: dict | None = None) -> bool:
        if self.scope == SCOPE_ALL:
            return True
        dept = (team or {}).get("department") or team_key.split("/", 1)[0]
        return dept in self.departments or team_key in self.lead_teams or team_key in self.member_teams

    def edits_team(self, team_key: str, team: dict | None = None) -> bool:
        if self.scope == SCOPE_ALL:
            return True
        dept = (team or {}).get("department") or team_key.split("/", 1)[0]
        return dept in self.departments

    @property
    def can_edit(self) -> bool:
        return self.scope in (SCOPE_ALL, SCOPE_DEPARTMENTS)

    @property
    def sees_money(self) -> bool:
        """Org-wide numbers (rates, totals) need at least department scope."""
        return self.scope in (SCOPE_ALL, SCOPE_DEPARTMENTS)

    def to_dict(self) -> dict:
        return {"email": self.email, "scope": self.scope, "departments": sorted(self.departments),
                "lead_teams": sorted(self.lead_teams), "member_teams": sorted(self.member_teams),
                "can_edit": self.can_edit,
                "partner": {"role": self.partner_role, "org": PARTNER_ORG} if self.is_partner else None}


def identity_email(identity) -> str:
    if isinstance(identity, dict):
        return norm_email(identity.get("email"))
    return norm_email(getattr(identity, "email", ""))


def scope_for(email: str, data: dict | None = None, policy=None, subject=None) -> ViewScope:
    """The caller's reach in the structure. Fails closed to none."""
    from api.governance import delegation

    email = norm_email(email)
    view = ViewScope(email=email)
    if not email:
        return view
    data = data or load()
    policy = policy if policy is not None else _policy()
    try:
        if policy is not None:
            designation = delegation.delegated_scope(policy, subject) if subject is not None else None
            if designation is None and delegation.is_platform_admin(policy, email):
                view.scope = SCOPE_ALL
            elif designation is not None and designation.scope in (delegation.SCOPE_PLATFORM, delegation.SCOPE_ORG):
                view.scope = SCOPE_ALL
            elif designation is not None and designation.scope == delegation.SCOPE_DEPARTMENT:
                view.departments.update(designation.departments)
    except Exception:
        logger.warning("delegated scope failed in org structure", exc_info=True)
    for key, row in departments(data, policy).items():
        if email in (row.get("admins") or []):
            view.departments.add(key)
    for key, team in (data.get("teams") or {}).items():
        if not isinstance(team, dict):
            continue
        if norm_email(team.get("lead")) == email:
            view.lead_teams.add(key)
        if email in [norm_email(m) for m in team.get("members") or []]:
            view.member_teams.add(key)
    if view.scope != SCOPE_ALL:
        if view.departments:
            view.scope = SCOPE_DEPARTMENTS
        elif view.lead_teams or view.member_teams:
            view.scope = SCOPE_TEAMS
    # Read on every request, so an assignment that ended or was removed stops
    # working at once. It only sets the role; the scope above is untouched.
    try:
        partner = partner_for(email, data)
    except Exception:
        logger.warning("partner lookup failed in org structure", exc_info=True)
        partner = None
    view.partner_role = partner["role"] if partner else None
    return view


def request_scope(handler) -> ViewScope:
    from api.governance.enforce import _request_identity, subject_from_identity

    identity = _request_identity(handler)
    policy = _policy()
    try:
        subject = subject_from_identity(identity, policy) if policy is not None else None
    except Exception:
        subject = None
    email = identity_email(identity) or norm_email(getattr(subject, "email", ""))
    return scope_for(email, policy=policy, subject=subject)


# ── Read model ───────────────────────────────────────────────────────────────

def team_of(email: str, data: dict | None = None) -> str:
    """First team (sorted) that lists ``email`` as member or lead, else ""."""
    email = norm_email(email)
    if not email:
        return ""
    data = data or load()
    for key in sorted(data.get("teams") or {}):
        team = data["teams"][key]
        if not isinstance(team, dict):
            continue
        if norm_email(team.get("lead")) == email or email in [norm_email(m) for m in team.get("members") or []]:
            return key
    return ""


def team_keys(data: dict | None = None) -> list[str]:
    data = data or load()
    return sorted(k for k, v in (data.get("teams") or {}).items() if isinstance(v, dict))


def team_rate(team_key: str, data: dict | None = None, policy=None) -> float | None:
    data = data or load()
    team = (data.get("teams") or {}).get(team_key) or {}
    if team.get("hourly_rate") is not None:
        return team.get("hourly_rate")
    dept = departments(data, policy).get(team.get("department") or team_key.split("/", 1)[0]) or {}
    return dept.get("hourly_rate")


def snapshot(view: ViewScope, data: dict | None = None, policy=None) -> dict:
    """What ``view`` may see: departments, teams and people, filtered."""
    data = data or load()
    depts = departments(data, policy)
    teams = {}
    for key, team in (data.get("teams") or {}).items():
        # A partner reads every team (names and members, to place a use case); no rates, no editing.
        if not isinstance(team, dict) or not (view.sees_team(key, team) or view.is_partner):
            continue
        row = {
            "key": key,
            "name": team.get("name") or key,
            "department": team.get("department") or key.split("/", 1)[0],
            "lead": norm_email(team.get("lead")),
            "members": sorted({norm_email(m) for m in team.get("members") or [] if norm_email(m)}),
            "chat_space": team.get("chat_space") or "",
            "parent": team.get("parent") or "",
            "editable": view.edits_team(key, team),
        }
        if view.sees_money:
            row["hourly_rate"] = team.get("hourly_rate")
        teams[key] = row
    visible_depts = {}
    for key, dept in depts.items():
        if view.sees_department(key) or any(t["department"] == key for t in teams.values()):
            row = {"key": key, "name": dept.get("name") or key, "admins": dept.get("admins", []),
                   "source": dept.get("source", "local"),
                   "editable": view.scope == SCOPE_ALL or (key in view.departments and dept.get("source") != "policy")}
            if view.sees_money:
                row["hourly_rate"] = dept.get("hourly_rate")
            visible_depts[key] = row
    people_keys = set()
    for team in teams.values():
        people_keys.update(team["members"])
        if team["lead"]:
            people_keys.add(team["lead"])
    for dept in visible_depts.values():
        people_keys.update(dept["admins"])
    partners = current_partners(data)
    by_email = {p["email"]: p for p in partners}
    people_keys.update(by_email)
    people = {}
    for email in sorted(people_keys):
        row = (data.get("people") or {}).get(email) or {}
        people[email] = {"email": email, "title": row.get("title") or "", "reports_to": norm_email(row.get("reports_to"))}
        if email in by_email:
            people[email]["partner"] = {"role": by_email[email]["role"], "org": PARTNER_ORG}
            people[email]["name"] = by_email[email]["name"]
    out = {"departments": visible_depts, "teams": teams, "people": people, "partners": partners,
           "updated_at": data.get("updated_at"), "viewer": view.to_dict()}
    if view.scope == SCOPE_ALL:
        # The admin also sees assignments that have not started yet or have ended.
        out["partners_all"] = [dict(partner_public(p), current=partner_is_current(p)) for p in data.get("partners") or []]
    return out


# ── Mutations ────────────────────────────────────────────────────────────────

def _touch(data: dict, actor: str) -> None:
    data["version"] = VERSION
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    data["updated_by"] = actor


def _check_reports_to(data: dict, email: str, manager: str) -> None:
    if not manager:
        return
    if manager == email:
        raise ValueError("Someone cannot report to themselves")
    seen = {email}
    cursor = manager
    for _ in range(50):
        if cursor in seen:
            raise ValueError("This reporting line would form a circle")
        seen.add(cursor)
        cursor = norm_email(((data.get("people") or {}).get(cursor) or {}).get("reports_to"))
        if not cursor:
            return
    raise ValueError("Reporting line too deep")


def apply(view: ViewScope, body: dict) -> dict:
    """One mutation. ``body['op']`` picks it. Returns the new snapshot.

    Raises PermissionError (403), KeyError (404) or ValueError (400).
    """
    if not isinstance(body, dict):
        raise ValueError("Invalid request")
    op = str(body.get("op") or "")
    if not view.can_edit:
        raise PermissionError("Only organisation or department admins can change the team structure")
    policy = _policy()
    with _locked():
        data = load()
        depts = departments(data, policy)
        if op == "department.save":
            key = str(body.get("key") or "") or slug(body.get("name") or "")
            if not _KEY_RE.match(key):
                raise ValueError("Use lowercase letters, digits and dashes for the key")
            existing = depts.get(key)
            if existing and existing.get("source") == "policy" and view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins change a department from the policy")
            if existing is None and view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins add departments")
            if existing is not None and view.scope != SCOPE_ALL and key not in view.departments:
                raise PermissionError("You do not administer this department")
            row = dict((data["departments"].get(key) or {}))
            name = _clean_text(body.get("name"), _NAME_MAX, "Name")
            if name:
                row["name"] = name
            elif not row.get("name") and not existing:
                raise ValueError("A department needs a name")
            if "admins" in body:
                if view.scope != SCOPE_ALL:
                    raise PermissionError("Only organisation admins choose department admins")
                admins = body.get("admins") or []
                if not isinstance(admins, list) or len(admins) > 50:
                    raise ValueError("Invalid admins")
                row["admins"] = sorted({norm_email(a) for a in admins if norm_email(a)})
            if "hourly_rate" in body:
                row["hourly_rate"] = _rate(body.get("hourly_rate"))
            data["departments"][key] = row
            detail = {"department": key}
        elif op == "department.delete":
            key = str(body.get("key") or "")
            if view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins remove departments")
            if key not in data["departments"]:
                raise KeyError("Department not found")
            if any((t or {}).get("department") == key for t in data["teams"].values()):
                raise ValueError("Move or remove the teams of this department first")
            data["departments"].pop(key)
            detail = {"department": key}
        elif op == "team.save":
            dept = str(body.get("department") or "")
            if dept not in depts:
                raise KeyError("Department not found")
            key = str(body.get("key") or "")
            if not key:
                key = f"{dept}/{slug(body.get('name') or '')}"
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}/[a-z0-9][a-z0-9-]{0,39}", key):
                raise ValueError("Invalid team key")
            team = dict(data["teams"].get(key) or {})
            if team and team.get("department") != dept:
                raise ValueError("A team keeps its department; create a new team to move it")
            if not view.edits_team(key, {"department": dept}):
                raise PermissionError("You do not administer this department")
            if not team and len(data["teams"]) >= _TEAMS_MAX:
                raise ValueError("Too many teams")
            name = _clean_text(body.get("name"), _NAME_MAX, "Name") or team.get("name")
            if not name:
                raise ValueError("A team needs a name")
            team.update({"name": name, "department": dept})
            if "lead" in body:
                team["lead"] = norm_email(body.get("lead"))
                if body.get("lead") and not team["lead"]:
                    raise ValueError("Lead must be an e-mail address")
            if "members" in body:
                members = body.get("members") or []
                if not isinstance(members, list) or len(members) > _MEMBERS_MAX:
                    raise ValueError("Invalid members")
                clean = sorted({norm_email(m) for m in members if norm_email(m)})
                if len(clean) != len({str(m).strip().lower() for m in members if str(m).strip()}):
                    raise ValueError("Every member must be an e-mail address")
                team["members"] = clean
            if "hourly_rate" in body:
                team["hourly_rate"] = _rate(body.get("hourly_rate"))
            if "parent" in body:
                parent = str(body.get("parent") or "")
                if parent:
                    if parent == key:
                        raise ValueError("A team cannot sit under itself")
                    above = data["teams"].get(parent)
                    if not above:
                        raise KeyError("Parent team not found")
                    if above.get("department") != dept:
                        raise ValueError("A sub-team stays in the department of its parent")
                    cursor, seen = parent, set()
                    while cursor and cursor not in seen:
                        if cursor == key:
                            raise ValueError("This would put the team under itself")
                        seen.add(cursor)
                        cursor = (data["teams"].get(cursor) or {}).get("parent") or ""
                team["parent"] = parent
            if "chat_space" in body:
                space = str(body.get("chat_space") or "").strip()
                if space and not re.fullmatch(r"spaces/[A-Za-z0-9_-]{4,64}", space):
                    raise ValueError("Chat space looks like spaces/AAAA...")
                team["chat_space"] = space
            if team.get("lead") and team["lead"] not in team.get("members", []):
                team.setdefault("members", []).append(team["lead"])
                team["members"] = sorted(set(team["members"]))
            data["teams"][key] = team
            detail = {"team": key, "members": team.get("members", [])}
        elif op == "team.delete":
            key = str(body.get("key") or "")
            team = data["teams"].get(key)
            if team is None:
                raise KeyError("Team not found")
            if not view.edits_team(key, team):
                raise PermissionError("You do not administer this department")
            data["teams"].pop(key)
            for child in data["teams"].values():
                if isinstance(child, dict) and child.get("parent") == key:
                    child["parent"] = team.get("parent") or ""
            detail = {"team": key}
        elif op == "member.move":
            email = norm_email(body.get("email"))
            to_key = str(body.get("to") or "")
            from_key = str(body.get("from") or "")
            if not email:
                raise ValueError("E-mail required")
            if to_key and to_key not in data["teams"]:
                raise KeyError("Team not found")
            for key in (from_key, to_key):
                if key and not view.edits_team(key, data["teams"].get(key)):
                    raise PermissionError("You do not administer this department")
            if from_key and from_key in data["teams"]:
                team = data["teams"][from_key]
                team["members"] = [m for m in team.get("members") or [] if norm_email(m) != email]
                if norm_email(team.get("lead")) == email:
                    team["lead"] = ""
            if to_key:
                team = data["teams"][to_key]
                team["members"] = sorted(set((team.get("members") or []) + [email]))
            detail = {"email": email, "from": from_key, "to": to_key}
        elif op == "person.save":
            email = norm_email(body.get("email"))
            if not email:
                raise ValueError("E-mail required")
            visible = snapshot(view, data, policy)["people"]
            if view.scope != SCOPE_ALL and email not in visible:
                raise PermissionError("This person is not in your departments")
            row = dict((data["people"].get(email) or {}))
            if "title" in body:
                row["title"] = _clean_text(body.get("title"), _TITLE_MAX, "Title")
            if "reports_to" in body:
                manager = norm_email(body.get("reports_to"))
                if body.get("reports_to") and not manager:
                    raise ValueError("Reports to must be an e-mail address")
                _check_reports_to(data, email, manager)
                row["reports_to"] = manager
            data["people"][email] = row
            detail = {"person": email}
        elif op == "partner.save":
            if view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins change the assigned partners")
            row = clean_partner(body, "local")
            if any(norm_email(p.get("email")) == row["email"] and p.get("source") == "cloud" for p in data["partners"]):
                raise ValueError("This partner is assigned centrally; change it there")
            others = [p for p in data["partners"] if not (norm_email(p.get("email")) == row["email"] and p.get("source") != "cloud")]
            if len(others) >= _PARTNERS_MAX:
                raise ValueError("Too many partners")
            data["partners"] = others + [row]
            detail = {"partner": row["email"], "role": row["role"], "ends_at": row["ends_at"]}
        elif op == "partner.remove":
            if view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins change the assigned partners")
            email = norm_email(body.get("email"))
            match = [p for p in data["partners"] if norm_email(p.get("email")) == email]
            if not match:
                raise KeyError("Partner not found")
            if all(p.get("source") == "cloud" for p in match):
                raise ValueError("This partner is assigned centrally; remove it there")
            data["partners"] = [p for p in data["partners"] if not (norm_email(p.get("email")) == email and p.get("source") != "cloud")]
            detail = {"partner": email, "removed": True}
        elif op == "import":
            if view.scope != SCOPE_ALL:
                raise PermissionError("Only organisation admins import a structure")
            proposal = body.get("structure") or {}
            if not isinstance(proposal, dict):
                raise ValueError("Invalid structure")
            for dkey, drow in (proposal.get("departments") or {}).items():
                if not _KEY_RE.match(str(dkey)) or not isinstance(drow, dict):
                    raise ValueError(f"Invalid department {dkey}")
                data["departments"].setdefault(dkey, {})["name"] = _clean_text(drow.get("name"), _NAME_MAX, "Name") or dkey
            depts = departments(data, policy)
            for tkey, trow in (proposal.get("teams") or {}).items():
                if not isinstance(trow, dict) or trow.get("department") not in depts:
                    raise ValueError(f"Invalid team {tkey}")
                members = sorted({norm_email(m) for m in trow.get("members") or [] if norm_email(m)})
                data["teams"][tkey] = {"name": _clean_text(trow.get("name"), _NAME_MAX, "Name") or tkey,
                                       "department": trow["department"], "lead": norm_email(trow.get("lead")),
                                       "members": members}
            detail = {"import": True, "teams": len(proposal.get("teams") or {})}
        else:
            raise ValueError("Unknown operation")
        _touch(data, view.email)
        _write(data)
    _audit(view.email, op, detail)
    return snapshot(view, load(), policy)


# ── HTTP ─────────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    path = str(getattr(parsed, "path", "") or "")
    if path not in ("/api/org/structure", "/api/org/structure/me"):
        return False
    view = request_scope(handler)
    if path == "/api/org/structure/me":
        payload = view.to_dict()
        payload["has_structure"] = bool(load().get("teams"))
        payload["can_view"] = not view.is_none
        payload["can_manage"] = view.scope in (SCOPE_ALL, SCOPE_DEPARTMENTS)
        j(handler, payload)
        return True
    if view.is_none and not view.is_partner:
        j(handler, {"error": "forbidden", "reason": "org_scope", "viewer": view.to_dict()}, status=403)
        return True
    j(handler, snapshot(view))
    return True


def handle_post(handler, parsed, body) -> bool:
    if str(getattr(parsed, "path", "") or "") != "/api/org/structure":
        return False
    view = request_scope(handler)
    try:
        payload = apply(view, body)
    except PermissionError as e:
        j(handler, {"error": str(e), "reason": "org_scope"}, status=403)
    except KeyError as e:
        j(handler, {"error": str(e).strip("'")}, status=404)
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except Exception:
        logger.exception("org structure mutation failed")
        j(handler, {"error": "internal_error"}, status=500)
    else:
        j(handler, payload)
    return True
