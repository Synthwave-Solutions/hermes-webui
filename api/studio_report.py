"""Studio and the central Cloud: who is assigned here, and how far the use cases are.

A customer department has its own installation. The central Cloud assigns a
consultant and a developer of the supplier to it; they work in Studio here and
the Cloud wants one summary per installation. Both directions go upward
through ``api/control_plane_client.call`` (signed with the installation's
control key, which binds the organisation; nothing here sends or accepts an
organisation id) and there is still no inbound route.

Pull   ``GET /v1/customer/assignments``
       expects ``{"assignments": [{"email", "name", "role", "starts_at", "ends_at"}]}``
       and replaces the partners with ``source: cloud`` in the team structure
       (``org_structure.replace_cloud_partners``); local ones stay.

Push   ``POST /v1/customer/studio/summary``, shortly after a Studio save and
       on a timer. Body: ``{"generated_at", "use_cases": [...], "partners":
       [{"email", "role"}]}``. Per use case: id, title, phase, backlog_status,
       team, consultant, updated_at, hours_week_before, hours_week_after,
       hours_week_saved, measured_hours_saved_30d. With a roadmap in Studio
       the body also carries ``roadmap``: report_version, updated_at, per
       block its name and rows_total, rows_built, rows_live, the same three
       counts for the whole roadmap and measured_hours_week_saved.

Privacy of the push: installation state only. No e-mail address or name of
anybody at the customer (the owner of a use case is left out), no notes, no
process description, no data notes, no goals. The only addresses in it are
those of the supplier's own assigned staff.

Guarantees: nothing here raises into a request. Without a configured control
plane every function is a no-op: nothing is sent, spooled or changed. A push
that cannot be delivered leaves one small pending file in the WebUI state
directory (``studio-report/spool``, 0600) and is retried later with backoff,
always with the state of that moment, because a summary replaces the one
before it.

``GET /api/studio/summary`` is the same table for people in the installation
(organisation admins, department admins for their teams, partners), with the
owner's display name added.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from api import control_plane_client, org_structure
from api.helpers import j

logger = logging.getLogger(__name__)

ASSIGNMENTS_PATH = "/v1/customer/assignments"
SUMMARY_PATH = "/v1/customer/studio/summary"

SWITCH_ENV = "SP_STUDIO_REPORT"            # "0" switches pull, push and the thread off
THREAD_NAME = "sp-studio-report"
TICK_S = 15.0
START_DELAY_S = 45.0
DEBOUNCE_S = float(os.environ.get("SP_STUDIO_REPORT_DEBOUNCE", "20"))
PUSH_INTERVAL_S = float(os.environ.get("SP_STUDIO_REPORT_PUSH_INTERVAL", "3600"))
PULL_INTERVAL_S = float(os.environ.get("SP_STUDIO_REPORT_PULL_INTERVAL", "900"))
BACKOFF_BASE_S = 60.0
BACKOFF_MAX_S = 1800.0
SEND_TIMEOUT_S = 10.0

MAX_USE_CASES = 500
MAX_ASSIGNMENTS = 100
MEASURE_DAYS = 30
SPOOL_SUBDIR = ("studio-report", "spool")
SPOOL_FILE = "pending.json"
SPOOL_MAX_BYTES = 256 * 1024
SPOOL_MAX_AGE_S = 7 * 86400

_LOCK = threading.Lock()
_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_dirty_at = 0.0          # when Studio last changed and has not been pushed since
_failures = 0
_last = {"pull": None, "push": None, "pull_at": None, "push_at": None}


# ── Switches ─────────────────────────────────────────────────────────────────

def enabled() -> bool:
    """On unless switched off, and only with a configured control plane."""
    if os.environ.get(SWITCH_ENV, "1").strip() == "0":
        return False
    try:
        return bool(control_plane_client.configured())
    except Exception:
        return False


def _iso(stamp) -> str:
    try:
        return datetime.fromtimestamp(float(stamp), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


# ── The summary ──────────────────────────────────────────────────────────────

def _backlog_status(items: list[dict]) -> dict[str, str]:
    """Per use case the status of the backlog idea it was worked out in.

    With several ideas the furthest one counts; a parked idea only when it is
    the only one.
    """
    from api import studio_library

    order = {s: i for i, s in enumerate(studio_library.STATUSES)}
    out: dict[str, str] = {}
    for item in items:
        uc, status = item.get("use_case"), item.get("status")
        if not uc or status not in order:
            continue
        current = out.get(uc)
        if current is None or current == "parked" or (status != "parked" and order[status] > order[current]):
            out[uc] = status
    return out


def _measured_hours() -> dict[str, float]:
    try:
        from api import value_tracking

        now = time.time()
        minutes = value_tracking.saved_minutes_by_use_case(now - MEASURE_DAYS * 86400, now + 1)
        return {uc: round(m / 60, 1) for uc, m in minutes.items()}
    except Exception:
        logger.debug("measured savings per use case unavailable", exc_info=True)
        return {}


def _number(value):
    return round(float(value), 1) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _documents() -> list[dict]:
    from api import studio

    docs = []
    for path in sorted(studio._dir().glob("uc_*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and studio._ID_RE.match(str(doc.get("id") or "")):
            docs.append(doc)
    return sorted(docs, key=lambda d: -(d.get("updated_at") or 0))


def use_case_rows(structure: dict | None = None) -> list[tuple[dict, dict]]:
    """``(row, document)`` per use case, newest first. The row holds only what may leave the installation."""
    from api import studio, studio_library

    structure = structure or org_structure.load()
    partners = {p["email"] for p in org_structure.current_partners(structure)}
    status = _backlog_status(studio_library.backlog_items())
    measured = _measured_hours()
    rows = []
    for doc in _documents():
        process = doc.get("process") if isinstance(doc.get("process"), dict) else {}
        base = process.get("baseline") if isinstance(process.get("baseline"), dict) else {}
        before, after = _number(base.get("hours_week_before")), _number(base.get("hours_week_after"))
        saved = round(max(0.0, before - after), 1) if before is not None and after is not None else None
        consultant = org_structure.norm_email(doc.get("consultant"))
        rows.append(({
            "id": doc["id"],
            "title": studio._txt(doc.get("title"), 120),
            "phase": doc.get("phase") if doc.get("phase") in studio.PHASES else "discover",
            "backlog_status": status.get(doc["id"], ""),
            "team": str(doc.get("team") or ""),
            # Only somebody who is assigned here right now; never a customer address.
            "consultant": consultant if consultant in partners else "",
            "updated_at": _iso(doc.get("updated_at")),
            "hours_week_before": before,
            "hours_week_after": after,
            "hours_week_saved": saved,
            "measured_hours_saved_30d": measured.get(doc["id"], 0.0),
        }, doc))
    return rows


def build_summary() -> dict:
    """The body of the push. See the module text for what is and is not in it."""
    structure = org_structure.load()
    rows = [row for row, _doc in use_case_rows(structure)]
    body = {"generated_at": _iso(time.time()),
            "use_cases": rows[:MAX_USE_CASES],
            "partners": [{"email": p["email"], "role": p["role"]} for p in org_structure.current_partners(structure)]}
    if len(rows) > MAX_USE_CASES:
        body["truncated"] = True
    try:
        from api import studio_roadmap

        roadmap = studio_roadmap.summary_block()
    except Exception:
        logger.warning("roadmap progress left out of the summary", exc_info=True)
        roadmap = None
    if roadmap is not None:
        # Counts and block names only; present only when the installation has a roadmap.
        body["roadmap"] = roadmap
    return body


# ── Pull: assignments ────────────────────────────────────────────────────────

def pull_assignments() -> dict:
    """Fetch the assignments and replace the cloud partners. Never raises.

    Returns ``{"ok": bool, "reason"?: str, "changed"?: bool, "count"?: int}``.
    An answer that is not the expected shape changes nothing: an unreachable
    or confused control plane never removes a consultant from the structure.
    """
    try:
        if not enabled():
            return {"ok": False, "reason": "not_configured"}
        status, data = control_plane_client.call("GET", ASSIGNMENTS_PATH, timeout=SEND_TIMEOUT_S)
        rows = data.get("assignments") if isinstance(data, dict) else None
        if status != 200 or not isinstance(rows, list) or len(rows) > MAX_ASSIGNMENTS:
            result = {"ok": False, "reason": "unavailable" if status != 200 else "invalid_response", "status": status}
        else:
            result = dict(org_structure.replace_cloud_partners(rows), ok=True)
            if result.get("changed"):
                note_change()
    except Exception:
        logger.warning("assignment pull failed", exc_info=True)
        result = {"ok": False, "reason": "error"}
    with _LOCK:
        _last.update(pull=result, pull_at=time.time())
    return result


# ── Push: summary, with a pending file when it cannot be delivered ───────────

def _spool_dir() -> Path | None:
    try:
        from api import config

        return Path(config.STATE_DIR).joinpath(*SPOOL_SUBDIR)
    except Exception:
        return None


def _spool_path() -> Path | None:
    directory = _spool_dir()
    return directory / SPOOL_FILE if directory is not None else None


def spool_pending() -> bool:
    """A summary is still owed to the control plane (also after a restart)."""
    path = _spool_path()
    try:
        if path is None or not path.is_file():
            return False
        if time.time() - path.stat().st_mtime > SPOOL_MAX_AGE_S:
            path.unlink()
            return False
        return True
    except OSError:
        return False


def _spool_write(body: dict, reason: str) -> bool:
    """Keep the one undelivered summary. Bounded: one file, replaced each time."""
    path = _spool_path()
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        data = json.dumps({"v": 1, "reason": reason, "spooled_at": _iso(time.time()), "body": body},
                          ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(data) > SPOOL_MAX_BYTES:
            data = json.dumps({"v": 1, "reason": reason, "spooled_at": _iso(time.time()), "body": None},
                              separators=(",", ":")).encode("utf-8")
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
        return True
    except Exception:
        logger.debug("studio summary spool write failed", exc_info=True)
        return False


def _spool_clear() -> None:
    path = _spool_path()
    try:
        if path is not None:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def push_summary() -> str:
    """Send the summary of this moment. Never raises.

    Returns ``sent``, ``spooled`` (kept for a retry), ``rejected`` (the
    control plane refused it; retrying the same thing would not help) or
    ``off``.
    """
    global _dirty_at, _failures
    try:
        if not enabled():
            return "off"
        started = time.time()
        body = build_summary()
        status, _data = control_plane_client.call("POST", SUMMARY_PATH, body=body, timeout=SEND_TIMEOUT_S)
        if 200 <= status < 300:
            outcome = "sent"
            _spool_clear()
        elif status in (0, 408, 425, 429) or status >= 500:
            outcome = "spooled" if _spool_write(body, f"status_{status}") else "failed"
        else:
            outcome = "rejected"
            _spool_clear()
            logger.warning("studio summary rejected by the control plane (status %s)", status)
        with _LOCK:
            if outcome in ("sent", "rejected"):
                _failures = 0
                if _dirty_at <= started:
                    _dirty_at = 0.0
            else:
                _failures += 1
            _last.update(push=outcome, push_at=time.time())
        return outcome
    except Exception:
        logger.warning("studio summary push failed", exc_info=True)
        return "failed"


def note_change() -> None:
    """Studio changed: push a little later (debounced by the timer thread). Cheap, never raises."""
    global _dirty_at
    _dirty_at = time.time()


def stats() -> dict:
    with _LOCK:
        return dict(_last, dirty=bool(_dirty_at), failures=_failures, pending=spool_pending())


# ── Timer ────────────────────────────────────────────────────────────────────

def _backoff_s() -> float:
    return min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** max(0, min(_failures, 10) - 1)))


def run_due(now: float, state: dict) -> list[str]:
    """One tick of the timer: what was done. ``state`` keeps ``next_pull`` and ``next_push``."""
    done = []
    if not enabled():
        return done
    if now >= state.get("next_pull", 0):
        state["next_pull"] = now + PULL_INTERVAL_S
        pull_assignments()
        done.append("pull")
    due = bool(_dirty_at) and now - _dirty_at >= DEBOUNCE_S
    if (due or spool_pending() or now >= state.get("next_push", 0)) and now >= state.get("retry_at", 0):
        outcome = push_summary()
        state["next_push"] = now + PUSH_INTERVAL_S
        state["retry_at"] = now + _backoff_s() if outcome in ("spooled", "failed") else 0
        done.append("push:" + outcome)
    return done


def _loop() -> None:
    state: dict = {}
    _STOP.wait(START_DELAY_S)
    while not _STOP.is_set():
        try:
            run_due(time.time(), state)
        except Exception:
            logger.warning("studio report tick failed", exc_info=True)
        _STOP.wait(TICK_S)


def start_thread() -> bool:
    """Start the timer daemon (idempotent). Off with SP_STUDIO_REPORT=0 or without a control plane."""
    global _THREAD
    if not enabled():
        return False
    if _THREAD is not None and _THREAD.is_alive():
        return False
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, daemon=True, name=THREAD_NAME)
    _THREAD.start()
    return True


def stop_thread(timeout: float = 2.0) -> None:
    global _THREAD
    thread, _THREAD = _THREAD, None
    _STOP.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=timeout)


def _reset_for_tests() -> None:
    global _dirty_at, _failures
    stop_thread()
    with _LOCK:
        _dirty_at, _failures = 0.0, 0
        _last.update(pull=None, push=None, pull_at=None, push_at=None)


# ── The same table for people in the installation ────────────────────────────

def display_name(email: str, policy=None) -> str:
    """A readable name for an address: the policy's display name, else the local part."""
    email = org_structure.norm_email(email)
    if not email:
        return ""
    user = (getattr(policy, "users", None) or {}).get(email) if policy is not None else None
    stored = str(getattr(user, "display_name", "") or "").strip() if user is not None else ""
    if stored:
        return stored
    parts = [p for p in email.split("@", 1)[0].replace("_", ".").replace("-", ".").split(".") if p]
    return " ".join(p[:1].upper() + p[1:] for p in parts) if parts else email


def can_view_summary(view) -> bool:
    return view.scope in (org_structure.SCOPE_ALL, org_structure.SCOPE_DEPARTMENTS) or view.is_partner


def summary_for(view) -> dict:
    """Progress per use case for a customer-facing view. Raises PermissionError."""
    if not can_view_summary(view):
        raise PermissionError("Only organisation admins, department admins and assigned partners see the progress overview")
    structure = org_structure.load()
    policy = org_structure._policy()
    teams = structure.get("teams") or {}
    partners = org_structure.current_partners(structure)
    names = {p["email"]: p["name"] or display_name(p["email"]) for p in partners}
    rows = []
    for row, doc in use_case_rows(structure):
        team = row["team"]
        if view.scope == org_structure.SCOPE_ALL:
            pass
        elif team and (view.is_partner or (view.scope == org_structure.SCOPE_DEPARTMENTS and view.edits_team(team))):
            pass
        elif doc.get("owner") == view.email:
            pass
        else:
            continue
        rows.append(dict(row, owner_name=display_name(doc.get("owner"), policy),
                         team_name=(teams.get(team) or {}).get("name") or team,
                         consultant_name=names.get(row["consultant"], "")))
    numbers = [r for r in rows if r["hours_week_saved"] is not None]
    return {"generated_at": _iso(time.time()), "use_cases": rows,
            "partners": [{k: p[k] for k in ("email", "name", "role", "org")} for p in partners],
            "totals": {"use_cases": len(rows),
                       "hours_week_saved": round(sum(r["hours_week_saved"] for r in numbers), 1),
                       "measured_hours_saved_30d": round(sum(r["measured_hours_saved_30d"] for r in rows), 1)},
            "viewer": view.to_dict()}


def handle_get(handler, parsed) -> bool:
    if str(getattr(parsed, "path", "") or "") != "/api/studio/summary":
        return False
    view = org_structure.request_scope(handler)
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    try:
        j(handler, summary_for(view))
    except PermissionError as e:
        j(handler, {"error": str(e), "reason": "org_scope"}, status=403)
    except Exception:
        logger.exception("GET /api/studio/summary failed")
        j(handler, {"error": "internal_error"}, status=500)
    return True
