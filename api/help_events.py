"""Help and tour usage counts, ``POST /api/help/events`` (plan section 6, W4).

The help system reports four things: a tour was started, a tour was
completed, "Explain this page" was clicked, and "This did not help" was
pressed. Each report adds one to a counter per event, per page (or tour) and
per UTC day, kept in ``help_events.json`` in the WebUI state directory. The
counts are reviewed monthly to decide which help content and screens to fix.

Counts only: the request's identity, address, headers and any other body
field are never read or stored. The file holds dates, the four event names,
page or tour ids and integers, nothing else; a file that holds anything else
is cleaned on the next write. The route always answers 204, also for a
report it drops (an unknown event, a malformed id, a non-object body), so the
browser never retries or shows an error for a usage counter.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Event name -> the body field that names what it counts.
EVENTS = {
    "tour_started": "tour",
    "tour_completed": "tour",
    "explain_clicked": "page",
    "did_not_help": "page",
}
FILE_NAME = "help_events.json"
FILE_VERSION = 1
# Help page and tour ids are short snake_case names (static/help-content.js).
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Bounds that keep the file small whatever a client sends: a new id is not
# added once an event already has this many ids on one day, counts stop at
# MAX_COUNT, and days older than the retention window are dropped.
MAX_KEYS_PER_EVENT_PER_DAY = 100
MAX_COUNT = 1_000_000_000
DEFAULT_RETENTION_DAYS = 400
RETENTION_ENV = "HERMES_WEBUI_HELP_EVENTS_RETENTION_DAYS"

_LOCK = threading.Lock()


def events_path() -> Path:
    """The counter file, resolved at call time so tests and profiles can move it."""
    from api import config

    return Path(config.STATE_DIR) / FILE_NAME


def retention_days() -> int:
    """Days of counts to keep (default 400, so a full year can be compared)."""
    raw = os.getenv(RETENTION_ENV, "").strip()
    if raw:
        try:
            value = int(raw)
        except ValueError:
            value = 0
        if 1 <= value <= 3650:
            return value
    return DEFAULT_RETENTION_DAYS


def normalize(body: Any) -> tuple[str, str] | None:
    """Return ``(event, id)`` for a valid report, otherwise None."""
    if not isinstance(body, dict):
        return None
    event = body.get("event")
    if not isinstance(event, str) or event not in EVENTS:
        return None
    key = body.get(EVENTS[event])
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        return None
    return event, key


def _clean(raw: Any) -> dict:
    """Keep only ``{day: {event: {id: count}}}`` entries of the documented shape."""
    days: dict[str, dict[str, dict[str, int]]] = {}
    source = raw.get("days") if isinstance(raw, dict) else None
    if not isinstance(source, dict):
        return days
    for day, bucket in source.items():
        if not isinstance(day, str) or not _DAY_RE.fullmatch(day) or not isinstance(bucket, dict):
            continue
        kept_bucket: dict[str, dict[str, int]] = {}
        for event, counts in bucket.items():
            if event not in EVENTS or not isinstance(counts, dict):
                continue
            kept = {}
            for key, count in counts.items():
                if (isinstance(key, str) and _KEY_RE.fullmatch(key)
                        and isinstance(count, int) and not isinstance(count, bool) and count > 0):
                    kept[key] = min(count, MAX_COUNT)
                if len(kept) >= MAX_KEYS_PER_EVENT_PER_DAY:
                    break
            if kept:
                kept_bucket[event] = kept
        if kept_bucket:
            days[day] = kept_bucket
    return days


def _load(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        logger.warning("help events: unreadable counter file, starting a new one")
        return {}
    return _clean(raw)


def _write(path: Path, days: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": FILE_VERSION, "days": days}
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".help_events.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _prune(days: dict, today: date) -> None:
    oldest = (today - timedelta(days=retention_days() - 1)).isoformat()
    for day in [d for d in days if d < oldest]:
        del days[day]


def record(event: str, key: str, *, today: date | None = None) -> bool:
    """Add one to ``event`` for ``key`` today. Returns False when it was dropped."""
    if event not in EVENTS or not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        return False
    today = today or datetime.now(timezone.utc).date()
    day = today.isoformat()
    path = events_path()
    with _LOCK:
        days = _load(path)
        counts = days.setdefault(day, {}).setdefault(event, {})
        if key not in counts and len(counts) >= MAX_KEYS_PER_EVENT_PER_DAY:
            return False
        counts[key] = min(counts.get(key, 0) + 1, MAX_COUNT)
        _prune(days, today)
        _write(path, days)
    return True


def summary(month: str | None = None) -> dict:
    """Totals per event and id for one ``YYYY-MM`` month (default: all kept days).

    For the monthly review of which help content to fix; reads the file only.
    """
    if month is not None and not re.fullmatch(r"\d{4}-\d{2}", str(month)):
        raise ValueError("month must look like YYYY-MM")
    with _LOCK:
        days = _load(events_path())
    totals: dict[str, dict[str, int]] = {}
    for day, bucket in days.items():
        if month is not None and not day.startswith(month + "-"):
            continue
        for event, counts in bucket.items():
            target = totals.setdefault(event, {})
            for key, count in counts.items():
                target[key] = target.get(key, 0) + count
    return totals


def _no_content(handler) -> None:
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def handle_post(handler, body) -> bool:
    """Count one help event. Always 204; nothing about the caller is read."""
    try:
        report = normalize(body)
        if report is not None:
            record(*report)
    except Exception:  # a usage counter never fails the request
        logger.warning("help events: could not record a count", exc_info=True)
    _no_content(handler)
    return True
