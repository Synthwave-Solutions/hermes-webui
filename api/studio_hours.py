"""Hours of the month for this installation, read from the central Cloud (22 Nov 2026).

``GET /api/studio/hours?period=YYYY-MM`` proxies the signed
``GET /v1/customer/hours?period=YYYY-MM`` of the control plane (the control
key binds the organisation; nothing here sends an organisation id) and hands
the browser a fixed, bounded shape: per department the package, per role the
allocated, used and remaining minutes with the people behind them, and the
assigned team. Hours only: no rates and no amounts.

For organisation admins, department admins and assigned partners. Answers are
kept for five minutes per period. Without a configured control plane, or when
it cannot be reached, the answer is a friendly empty state and never an error.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from urllib.parse import parse_qs

from api import control_plane_client, org_structure
from api.helpers import j

logger = logging.getLogger(__name__)

HOURS_PATH = "/v1/customer/hours"
CACHE_S = 300.0
ROLES = ("developer", "consultant", "qa")
MAX_DEPARTMENTS = 64
MAX_PEOPLE = 50
_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, dict]] = {}


def current_period() -> str:
    return time.strftime("%Y-%m")


def _text(value, limit: int = 120) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, (str, int)) and not isinstance(value, bool) else ""


def _minutes(value):
    """Whole minutes, or None when the Cloud does not know yet."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(round(value))


def _role(raw) -> dict | None:
    if not isinstance(raw, dict) or raw.get("role") not in ROLES:
        return None
    people = [{"name": _text(p.get("name"), 80), "used_minutes": _minutes(p.get("used_minutes")) or 0}
              for p in (raw.get("people") if isinstance(raw.get("people"), list) else [])[:MAX_PEOPLE]
              if isinstance(p, dict) and _text(p.get("name"), 80)]
    return {"role": raw["role"], "label": _text(raw.get("label"), 60), "allocated_minutes": _minutes(raw.get("allocated_minutes")) or 0,
            "used_minutes": _minutes(raw.get("used_minutes")), "remaining_minutes": _minutes(raw.get("remaining_minutes")),
            "people": people}


def _department(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    roles = [r for r in (_role(x) for x in (raw.get("roles") if isinstance(raw.get("roles"), list) else [])[:12]) if r]
    team = [{"role": t.get("role") if t.get("role") in ROLES else "", "label": _text(t.get("label"), 60), "name": _text(t.get("name"), 80),
             "hours_per_week": t.get("hours_per_week") if isinstance(t.get("hours_per_week"), (int, float)) and not isinstance(t.get("hours_per_week"), bool) else None}
            for t in (raw.get("team") if isinstance(raw.get("team"), list) else [])[:MAX_PEOPLE]
            if isinstance(t, dict) and _text(t.get("name"), 80)]
    return {"department_id": _text(raw.get("department_id"), 80), "name": _text(raw.get("name"), 120),
            "tier": _text(raw.get("tier"), 40) or None, "tier_name": _text(raw.get("tier_name"), 80) or None,
            "term_ends_at": _text(raw.get("term_ends_at"), 40) or None, "planned_tier_change": bool(raw.get("planned_tier_change")),
            "roles": roles, "team": team}


def clean_hours(data, period: str) -> dict:
    """The bounded shape for the browser, from whatever the control plane answered."""
    data = data if isinstance(data, dict) else {}
    as_of = data.get("usage_as_of")
    productive = data.get("productive") if isinstance(data.get("productive"), dict) else {}
    return {"configured": True, "available": True, "period": period,
            "usage_as_of": as_of if isinstance(as_of, (int, float)) and not isinstance(as_of, bool) else None,
            "departments": [d for d in (_department(x) for x in (data.get("departments") if isinstance(data.get("departments"), list) else [])[:MAX_DEPARTMENTS]) if d],
            "productive": {"status": _text(productive.get("status"), 40)}}


def hours(period: str | None = None, now: float | None = None) -> dict:
    """The hours of ``period`` (default this month). Never raises; raises ValueError only for a malformed period."""
    period = str(period or "").strip() or current_period()
    if not _PERIOD_RE.match(period):
        raise ValueError("The period is a month such as 2026-11")
    try:
        if not control_plane_client.configured():
            return {"configured": False, "available": False, "period": period, "departments": []}
    except Exception:
        return {"configured": False, "available": False, "period": period, "departments": []}
    now = time.time() if now is None else now
    with _LOCK:
        hit = _CACHE.get(period)
        if hit and now - hit[0] < CACHE_S:
            return hit[1]
    try:
        status, data = control_plane_client.call("GET", f"{HOURS_PATH}?period={period}", timeout=10)
    except Exception:
        logger.warning("hours request failed", exc_info=True)
        status, data = 0, None
    if status != 200 or not isinstance(data, dict):
        # Not kept: the next look asks again.
        return {"configured": True, "available": False, "period": period, "departments": [], "status": status}
    result = clean_hours(data, period)
    with _LOCK:
        _CACHE[period] = (now, result)
        for key in sorted(_CACHE, key=lambda k: _CACHE[k][0])[:-12]:
            _CACHE.pop(key, None)
    return result


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def can_view(view) -> bool:
    return view.scope in (org_structure.SCOPE_ALL, org_structure.SCOPE_DEPARTMENTS) or view.is_partner


def handle_get(handler, parsed) -> bool:
    if str(getattr(parsed, "path", "") or "") != "/api/studio/hours":
        return False
    view = org_structure.request_scope(handler)
    if not view.email:
        j(handler, {"error": "Sign in first"}, status=401)
        return True
    if not can_view(view):
        j(handler, {"error": "Only organisation admins, department admins and assigned partners see the hours", "reason": "org_scope"}, status=403)
        return True
    try:
        j(handler, hours((parse_qs(parsed.query or "").get("period") or [""])[0]))
    except ValueError as e:
        j(handler, {"error": str(e)}, status=400)
    except Exception:
        logger.exception("GET /api/studio/hours failed")
        j(handler, {"error": "internal_error"}, status=500)
    return True
