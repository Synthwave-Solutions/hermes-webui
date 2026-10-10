"""Views and actions of the Memory explorer, and the response filter.

Plan addendum 6.6.5. The frame's app calls ``/api/<path>``; the parent panel
forwards only these paths, and the server has a view for nothing else:

* read views (for the store's owner and for admins in scope): the upstream
  server's routes with its ``_safe_int`` bounds applied again here;
* synthetic answers (``auth/status``, ``health``, ``realtime/status``,
  ``admin/audit``) that never touch a store;
* changes (hub mode only): ``admin/memory/invalidate|supersede|importance|
  veracity|expiry``.

Refused and never forwarded: ``config`` (GET and POST), ``diagnostics`` (file
paths), ``runtime/status`` (pids and paths), ``realtime/events`` (server-sent
events), ``admin/backup``, ``auth/login``.

The response filter drops bytes and every ``db_path``, ``path``, ``log`` or
``pid`` key, caps strings at 50,000 characters and, for another person's
store, passes text through ``api.helpers._redact_text`` so secrets are masked
(``memory_admin_mask_secrets``, decision D76).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

STRING_CAP = 50_000
PARAM_CAP = 512
_DROP_KEYS = frozenset({"db_path", "path", "log", "pid"})
_NO_MASK_KEY_RE = re.compile(r"(^id$|_id$|_ids$|^ids$|^ref$|_at$|^at$|^timestamp$|^created$|^updated$|^valid_until$|^valid_from$|^last_recalled$|^degraded_at$)")


@dataclass(frozen=True)
class Param:
    name: str
    kind: str = "str"            # str | int | enum | flag
    default: Any = ""
    minimum: int = 1
    maximum: int = 1000
    choices: tuple[str, ...] = ()
    target: str = ""             # keyword argument name when it differs


@dataclass(frozen=True)
class ViewSpec:
    method: str                  # DashboardStore method, '' for synthetic
    params: tuple[Param, ...] = ()
    wrap: str = ""               # wrap a list result as {wrap: result}
    log_action: str = "view"     # access-log action: view | item | search
    synthetic: bool = False


def _limit(default, maximum, minimum=1):
    return Param("limit", "int", default, minimum, maximum)


_OFFSET = Param("offset", "int", 0, 0, 100000)
_Q = Param("q")

VIEWS: dict[str, ViewSpec] = {
    "stats": ViewSpec("stats"),
    "digest/today": ViewSpec("today_digest", (Param("day"), _limit(80, 300))),
    "review": ViewSpec("review_queues", (
        Param("queue", default="contaminated"), _Q, Param("min_importance"), _limit(100, 500), _OFFSET)),
    "lifecycle": ViewSpec("lifecycle_dashboard", (_limit(50, 200),)),
    "profile/inferred": ViewSpec("inferred_profile", (Param("limit", "int", 10, 1, 30, target="limit_per_section"),)),
    "patterns": ViewSpec("pattern_insights", (_limit(10, 30),)),
    "constellation": ViewSpec("constellation", (_limit(240, 600, 40),)),
    "search": ViewSpec("global_search", (_Q, _limit(30, 100)), log_action="search"),
    "recall-debug": ViewSpec("recall_debug", (_Q, _limit(20, 100)), log_action="search"),
    "timeline": ViewSpec("timeline", (_Q, Param("group", "enum", "day", choices=("day", "session")), _limit(300, 1000))),
    "memories": ViewSpec("list_memories", (
        Param("kind", "enum", "all", choices=("all", "working", "episodic")), _Q, Param("source"), Param("scope"),
        Param("session_id"), Param("sort", "enum", "recent", choices=("recent", "oldest", "importance", "recall")),
        Param("status", "enum", "active", choices=("active", "all", "expired", "superseded")), Param("veracity"),
        Param("degradation_tier"), Param("contaminated_only"), Param("degraded_only"),
        Param("due_for_degradation"), _limit(100, 500), _OFFSET), wrap="items"),
    "memory": ViewSpec("get_memory", (Param("id", target="memory_id"),), log_action="item"),
    "session": ViewSpec("session_detail", (Param("id", target="session_id"), _limit(200, 500)), log_action="item"),
    "triples": ViewSpec("triples", (
        _Q, Param("subject"), Param("predicate"), Param("object", target="object_"), _limit(200, 1000)), wrap="items"),
    "graph": ViewSpec("graph", (_Q, _limit(300, 1000))),
    "consolidations": ViewSpec("consolidations", (_Q, _limit(100, 500)), wrap="items"),
    "memoria/stats": ViewSpec("memoria_stats"),
    "memoria/facts": ViewSpec("memoria_facts", (_Q, _limit(200, 1000), _OFFSET), wrap="items"),
    "memoria/timelines": ViewSpec("memoria_timelines", (_Q, _limit(200, 1000), _OFFSET), wrap="items"),
    "memoria/instructions": ViewSpec("memoria_instructions", (_Q, _limit(200, 1000), _OFFSET), wrap="items"),
    "memoria/kg": ViewSpec("memoria_kg", (_Q, _limit(200, 1000), _OFFSET), wrap="items"),
    "memoria/preferences": ViewSpec("memoria_preferences", (_Q, _limit(200, 1000), _OFFSET), wrap="items"),
    # Synthetic answers: no store is read.
    "auth/status": ViewSpec("", synthetic=True),
    "health": ViewSpec("", synthetic=True),
    "realtime/status": ViewSpec("", synthetic=True),
    "admin/audit": ViewSpec("", (_limit(100, 1000),), synthetic=True),
}

ACTIONS = ("invalidate", "supersede", "importance", "veracity", "expiry")
# Access-log action per change (addendum 6.6.8).
ACTION_LOG = {"invalidate": "forget", "supersede": "edit", "importance": "meta", "veracity": "meta", "expiry": "meta"}
VERACITIES = ("stated", "inferred", "tool", "imported", "unknown")
REFUSED = frozenset({"config", "diagnostics", "runtime/status", "realtime/events", "admin/backup", "auth/login"})
# Query parameters the panel may send next to the view's own ones.
CONTROL_PARAMS = frozenset({"bank", "view", "reason_code", "reason_text"})


class ViewError(ValueError):
    """A request that names no known view or carries unusable parameters."""


def _safe_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value if value not in (None, "") else default).strip())
    except (TypeError, ValueError):
        parsed = int(default)
    return max(minimum, min(parsed, maximum))


def normalize(view: str, raw: dict) -> dict:
    """The keyword arguments for ``view`` from raw query values.

    Unknown parameters are dropped; strings are capped; integers are bounded
    exactly like upstream's server (``_safe_int``).
    """
    spec = VIEWS.get(view)
    if spec is None:
        raise ViewError("unknown view")
    out: dict[str, Any] = {}
    for param in spec.params:
        value = raw.get(param.name)
        if isinstance(value, list):
            value = value[-1] if value else None
        key = param.target or param.name
        if param.kind == "int":
            out[key] = _safe_int(value, param.default, param.minimum, param.maximum)
        elif param.kind == "enum":
            text = str(value or param.default)
            out[key] = text if text in param.choices else param.default
        else:
            text = "" if value is None else str(value)
            if "\x00" in text:
                raise ViewError("invalid parameter")
            out[key] = text[:PARAM_CAP]
    return out


def to_query(view: str, kwargs: dict) -> dict:
    """Normalised keyword arguments back under their query names.

    Backends receive these (the reader child and the hub normalise again, so
    the step is idempotent).
    """
    spec = VIEWS.get(view)
    if spec is None:
        raise ViewError("unknown view")
    out = {}
    for param in spec.params:
        key = param.target or param.name
        if key in kwargs:
            out[param.name] = kwargs[key]
    return out


def is_search(view: str, kwargs: dict) -> bool:
    """Whether a view request carries search text (logged as ``search``)."""
    spec = VIEWS.get(view)
    if spec is None:
        return False
    if spec.log_action == "search":
        return True
    return any(str(kwargs.get(k) or "").strip() for k in ("q", "subject", "predicate", "object_"))


def log_action(view: str, kwargs: dict) -> str:
    spec = VIEWS[view]
    if spec.log_action == "item":
        return "item"
    return "search" if is_search(view, kwargs) else "view"


def item_id(view: str, kwargs: dict) -> str:
    if view == "memory":
        return str(kwargs.get("memory_id") or "")
    if view == "session":
        return str(kwargs.get("session_id") or "")
    return ""


def call(store, view: str, kwargs: dict):
    """Run one read view on a (patched) DashboardStore; used by the reader."""
    spec = VIEWS.get(view)
    if spec is None or spec.synthetic:
        raise ViewError("unknown view")
    method = getattr(store, spec.method)
    if view == "memory":
        memory_id = kwargs.get("memory_id") or ""
        item = method(memory_id) if memory_id else None
        return {"item": item}, (200 if item else 404)
    if view == "session":
        return method(kwargs.get("session_id") or "", limit=kwargs.get("limit", 200)), 200
    result = method(**kwargs)
    if spec.wrap:
        result = {spec.wrap: result}
    return result, 200


def normalize_action(body: dict) -> dict:
    """Validate a change request; raises ``ViewError`` (400) when unusable."""
    action = str(body.get("action") or "")
    if action not in ACTIONS:
        raise ViewError("unknown action")
    memory_id = str(body.get("memory_id") or "").strip()
    if not memory_id or len(memory_id) > 200 or "\x00" in memory_id:
        raise ViewError("memory_id is required")
    out: dict[str, Any] = {"action": action, "memory_id": memory_id}
    if action == "supersede":
        content = body.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > STRING_CAP:
            raise ViewError("content is required")
        out["content"] = content
        updated_at = body.get("updated_at")
        if isinstance(updated_at, str) and updated_at.strip():
            out["updated_at"] = updated_at.strip()[:64]
        if body.get("importance") is not None:
            out["importance"] = _importance(body.get("importance"))
    elif action == "importance":
        out["importance"] = _importance(body.get("importance"))
    elif action == "veracity":
        veracity = str(body.get("veracity") or "")
        if veracity not in VERACITIES:
            raise ViewError("unknown veracity")
        out["veracity"] = veracity
    elif action == "expiry":
        value = body.get("valid_until")
        if value in (None, ""):
            out["valid_until"] = ""
        elif isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}([T ][0-9:.+Z-]{0,40})?$", value.strip()):
            out["valid_until"] = value.strip()
        else:
            raise ViewError("invalid expiry")
    return out


def _importance(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ViewError("invalid importance") from exc
    if not math.isfinite(number) or number < 0 or number > 1:
        raise ViewError("invalid importance")
    return number


def filter_response(value, *, mask: bool, _key: str = ""):
    """Drop bytes and path, log and pid keys; cap strings; mask secrets."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return None
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k)
            if key in _DROP_KEYS or isinstance(v, (bytes, bytearray, memoryview)):
                continue
            out[key] = filter_response(v, mask=mask, _key=key)
        return out
    if isinstance(value, (list, tuple)):
        return [filter_response(v, mask=mask, _key=_key) for v in value if not isinstance(v, (bytes, bytearray, memoryview))]
    if isinstance(value, str):
        text = value[:STRING_CAP]
        if mask and text and not _NO_MASK_KEY_RE.search(_key):
            text = _mask(text)
        return text
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _mask(text: str) -> str:
    try:
        from api.helpers import _redact_text

        return _redact_text(text, _enabled=True)
    except Exception:
        # Masking must never be skipped silently for another person's store.
        return "[REDACTED]"
