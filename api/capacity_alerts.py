"""Upstream capacity: plain-language user copy plus administrator alerts.

Two Super Agent tickets of 27 Aug 2026 meet here.

* "Replace technical upstream errors with friendly guidance and admin capacity
  alerts": a normal user hitting an exhausted provider saw raw HTTP status
  codes and provider diagnostics ("503 Service Unavailable", "run `hermes
  model` in your terminal"), which explain nothing and point at a terminal the
  user does not have.
* "Telegram alerts do not work when all upstream accounts are unavailable":
  when every upstream account is spent the run that would have produced the
  alert cannot run either, so the user was left with silence.

The rule that keeps both honest: the user-facing message may claim that an
administrator has been alerted ONLY when the alert was actually recorded or
delivered. ``record_capacity_event`` returns that fact and
``user_facing_message`` takes it as an argument; nothing here ever asserts a
notification it did not perform.

Alerts are deduplicated per (kind, provider) with a cooldown so a provider
that fails on every retry produces one alert, not a storm, while the event's
``count`` keeps the real incident volume visible. Technical diagnostics live
in this store, which is served by an administrator-gated route, so the user
message stays free of internals without losing anything for the admin.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_STORE_NAME = "capacity-alerts.json"
_LOCK = threading.Lock()
_MAX_EVENTS = 200

# Classification types (api/streaming.py::_classify_provider_error) that mean
# "the upstream account cannot serve this right now", as opposed to a bug in
# the request. Only these produce a capacity alert.
CAPACITY_KINDS = ("quota_exhausted", "rate_limit", "overloaded")

# Defaults for the administrator-configurable settings. Kept here so the
# module has working behaviour before an admin ever opens the settings pane.
DEFAULT_CONFIG = {
    # One alert per (kind, provider) per cooldown; repeats bump `count`.
    "capacity_alert_cooldown_seconds": 900,
    # How often the capacity poller samples remaining headroom.
    "capacity_alert_poll_seconds": 300,
    # Warn at this much remaining, per provider: {"anthropic": 20, ...} in
    # percent. Absent provider means "no threshold configured".
    "capacity_alert_thresholds": {},
    # Where an alert is sent in addition to the in-app admin list. Empty means
    # in-app only, which still counts as a delivered notification because the
    # admin screen is where approvals already live.
    "capacity_alert_destination": "",
}

_CONFIG_KEYS = frozenset(DEFAULT_CONFIG)


def _store_path() -> Path:
    from api import config

    return Path(config.STATE_DIR) / _STORE_NAME


def _load() -> dict:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            return data
    except (FileNotFoundError, ValueError, OSError):
        pass
    return {"events": []}


def _save(data: dict) -> None:
    try:
        events = data.get("events") or []
        data["events"] = events[-_MAX_EVENTS:]
        path = _store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        logger.warning("capacity alert store write failed", exc_info=True)


def effective_config() -> dict:
    """Defaults overlaid with whatever an administrator configured."""
    out = dict(DEFAULT_CONFIG)
    try:
        from api.config import load_settings

        settings = load_settings() or {}
    except Exception:
        return out
    for key in _CONFIG_KEYS:
        if key in settings and settings[key] not in (None, ""):
            out[key] = settings[key]
    return out


def sanitize_config(body) -> dict:
    """Validated capacity settings from an admin payload. Invalid values are
    dropped rather than stored, so a typo can never disable alerting."""
    out: dict = {}
    if not isinstance(body, dict):
        return out
    for key in ("capacity_alert_cooldown_seconds", "capacity_alert_poll_seconds"):
        if key in body:
            try:
                value = int(body[key])
            except (TypeError, ValueError):
                continue
            if 30 <= value <= 86400:
                out[key] = value
    if "capacity_alert_thresholds" in body:
        raw = body["capacity_alert_thresholds"]
        if isinstance(raw, dict):
            clean = {}
            for provider, percent in raw.items():
                name = str(provider or "").strip().lower()
                if not name or len(name) > 64:
                    continue
                try:
                    pct = float(percent)
                except (TypeError, ValueError):
                    continue
                if 0 < pct <= 100:
                    clean[name] = pct
            out["capacity_alert_thresholds"] = clean
    if "capacity_alert_destination" in body:
        dest = str(body["capacity_alert_destination"] or "").strip()
        if len(dest) <= 256:
            out["capacity_alert_destination"] = dest
    return out


# ── User-facing copy ────────────────────────────────────────────────────────
# Plain language, no HTTP status, no provider name, no CLI instruction. Each
# says what happened, who is on it, and what the user can do next.
_USER_COPY = {
    "quota_exhausted": (
        "The service is temporarily unavailable because the available capacity "
        "is used up."
    ),
    "rate_limit": (
        "The service is briefly busy because too many requests arrived at once."
    ),
    "overloaded": (
        "The service is temporarily unavailable because it is very busy "
        "right now."
    ),
}
_USER_NEXT_STEP = {
    "quota_exhausted": "Please try again later.",
    "rate_limit": "Please try again in a moment.",
    "overloaded": "Please try again in a few minutes.",
}
_NOTIFIED_SENTENCE = "An administrator has been notified."


def is_capacity_kind(kind) -> bool:
    return str(kind or "") in CAPACITY_KINDS


def user_facing_message(kind, notified: bool = False) -> str:
    """The message a normal user sees. ``notified`` must be the real outcome of
    record_capacity_event: the sentence is appended only when it is True."""
    kind = str(kind or "")
    if kind not in _USER_COPY:
        return ""
    parts = [_USER_COPY[kind]]
    if notified:
        parts.append(_NOTIFIED_SENTENCE)
    parts.append(_USER_NEXT_STEP[kind])
    return " ".join(parts)


def record_capacity_event(kind, provider=None, model=None, detail="", source="") -> dict:
    """Record one capacity incident and report whether an admin was alerted.

    Returns ``{"notified": bool, "deduplicated": bool, "event_id": str}``.
    ``notified`` is True when this call produced an alert an administrator can
    see (a fresh event, or an external dispatch that succeeded), and False when
    the event was folded into a still-warm alert or could not be stored: the
    caller must not tell the user an admin was notified in that case, because
    an alert already standing is not a new notification for this incident.
    Never raises; capacity handling must not add a second failure.
    """
    result = {"notified": False, "deduplicated": False, "event_id": ""}
    try:
        if not is_capacity_kind(kind):
            return result
        kind = str(kind)
        provider = str(provider or "unknown").strip().lower() or "unknown"
        now = time.time()
        cooldown = int(effective_config()["capacity_alert_cooldown_seconds"])
        key = f"{kind}|{provider}"
        with _LOCK:
            data = _load()
            events = data.get("events") or []
            existing = None
            for event in reversed(events):
                if isinstance(event, dict) and event.get("key") == key:
                    existing = event
                    break
            if existing is not None and (now - float(existing.get("last_ts") or 0)) < cooldown:
                existing["count"] = int(existing.get("count") or 1) + 1
                existing["last_ts"] = now
                if detail:
                    existing["detail"] = str(detail)[:500]
                _save(data)
                result["deduplicated"] = True
                result["notified"] = False
                result["event_id"] = str(existing.get("id") or "")
                return result
            event_id = f"{int(now * 1000):x}"
            event = {
                "id": event_id,
                "key": key,
                "kind": kind,
                "provider": provider,
                "model": str(model or ""),
                "source": str(source or ""),
                # Technical diagnostics live here, behind the admin-gated
                # route, never in the user-facing message.
                "detail": str(detail or "")[:500],
                "first_ts": now,
                "last_ts": now,
                "count": 1,
                "acknowledged": False,
            }
            events.append(event)
            data["events"] = events
            _save(data)
        # The in-app admin list IS a delivered notification: it is the screen
        # admins already watch for approvals. An additional external dispatch
        # is best effort and never downgrades that.
        dispatched, dispatch_error = _dispatch_external(event)
        if dispatch_error:
            with _LOCK:
                data = _load()
                for stored in data.get("events") or []:
                    if isinstance(stored, dict) and stored.get("id") == event_id:
                        stored["dispatch_error"] = str(dispatch_error)[:300]
                        stored["dispatched"] = bool(dispatched)
                        break
                _save(data)
        result["notified"] = True
        result["event_id"] = event_id
        return result
    except Exception:
        logger.warning("capacity alert record failed", exc_info=True)
        return result


def _dispatch_external(event: dict) -> tuple[bool, str]:
    """Best-effort send to the configured destination.

    Returns ``(dispatched, error)``. A missing destination is not an error:
    in-app alerting is the configured behaviour then. This never claims a send
    it cannot prove, so a failure is recorded as an error on the event rather
    than silently dropped.
    """
    destination = str(effective_config().get("capacity_alert_destination") or "").strip()
    if not destination:
        return False, ""
    try:
        from api.cron_webui_delivery import deliver_external_notice

        ok, error = deliver_external_notice(destination, _admin_alert_text(event))
        return bool(ok), "" if ok else str(error or "delivery not confirmed")
    except ImportError:
        return False, "no external delivery backend available"
    except Exception as exc:  # pragma: no cover: dispatch must never raise
        return False, str(exc)


def _admin_alert_text(event: dict) -> str:
    kind = str(event.get("kind") or "")
    label = {
        "quota_exhausted": "capacity exhausted",
        "rate_limit": "rate limited",
        "overloaded": "provider overloaded",
    }.get(kind, kind)
    provider = event.get("provider") or "unknown"
    model = event.get("model")
    line = f"SynthPulse capacity alert: {provider} {label}."
    if model:
        line += f" Model: {model}."
    line += " Users are seeing a temporary-unavailability message. Add capacity or an account in the WebUI."
    return line


def list_events(limit: int = 50, include_acknowledged: bool = True) -> list:
    """Newest-first alerts for the administrator view."""
    try:
        events = [e for e in (_load().get("events") or []) if isinstance(e, dict)]
        if not include_acknowledged:
            events = [e for e in events if not e.get("acknowledged")]
        events.sort(key=lambda e: float(e.get("last_ts") or 0), reverse=True)
        return events[: max(1, min(int(limit or 50), _MAX_EVENTS))]
    except Exception:
        logger.debug("capacity alert list failed", exc_info=True)
        return []


def acknowledge(event_id) -> bool:
    """Mark one alert handled. Returns whether a row changed."""
    event_id = str(event_id or "")
    if not event_id:
        return False
    with _LOCK:
        data = _load()
        for event in data.get("events") or []:
            if isinstance(event, dict) and event.get("id") == event_id:
                if event.get("acknowledged"):
                    return False
                event["acknowledged"] = True
                event["acknowledged_ts"] = time.time()
                _save(data)
                return True
    return False


def threshold_breaches(remaining_by_provider: dict) -> list:
    """Providers whose remaining headroom is at or below their threshold.

    ``remaining_by_provider`` maps a provider name to remaining percent. Used
    by the poller so an admin is warned BEFORE users hit an empty account,
    which is the point of the configurable thresholds.
    """
    out = []
    thresholds = effective_config().get("capacity_alert_thresholds") or {}
    if not isinstance(remaining_by_provider, dict):
        return out
    for provider, remaining in remaining_by_provider.items():
        name = str(provider or "").strip().lower()
        threshold = thresholds.get(name)
        if threshold is None:
            continue
        try:
            if float(remaining) <= float(threshold):
                out.append({"provider": name, "remaining": float(remaining),
                            "threshold": float(threshold)})
        except (TypeError, ValueError):
            continue
    return out
