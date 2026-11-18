"""Short per-viewer memo for read-only JSON endpoints that every open tab polls.

Several tabs of the same person ask the same question seconds apart, and each
answer is rebuilt under the interpreter lock while chats are streaming. The
memo is keyed on the request's own credentials (cookie and authorization
header), so an answer is only ever replayed to the browser session it was
built for. Any write request drops everything.

``HERMES_WEBUI_POLL_MEMO=0`` switches it off.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time

# path -> seconds an answer may be replayed
_PATHS = {
    "/api/kanban/waiting": 15.0,
    "/api/governance/approvals": 15.0,
    "/api/governance/approvals/mine": 15.0,
    "/api/org/chart": 60.0,
    "/api/mcp/tools": 60.0,
}
# Writes that never change what these endpoints return.
_QUIET_WRITES = (
    "/api/session/draft",
    "/api/client-events/log",
    "/api/chat/prewarm",
    "/api/session/anchor-scene",
)
_MAX = 256
_LOCK = threading.Lock()
_MEMO: dict = {}


def _enabled() -> bool:
    return os.environ.get("HERMES_WEBUI_POLL_MEMO", "1").strip().lower() not in {"0", "false", "off", "no"}


def _key(handler, parsed):
    headers = getattr(handler, "headers", None)
    if headers is None:
        return None
    credentials = "\n".join(str(headers.get(name) or "") for name in ("Cookie", "Authorization"))
    if not credentials.strip():
        return None
    # The identity proxy puts the signed-in person in forwarded headers.
    for name in ("X-Forwarded-Email", "X-Forwarded-User", "X-Auth-Request-Email"):
        credentials += "\n" + str(headers.get(name) or "")
    digest = hashlib.sha256(credentials.encode("utf-8", "replace")).hexdigest()
    return (digest, parsed.path, parsed.query or "")


def serve(handler, parsed) -> bool:
    """Replay a fresh answer (True), or arm capture of the one about to be built."""
    handler._poll_memo_capture = None
    ttl = _PATHS.get(parsed.path)
    if not ttl or not _enabled():
        return False
    key = _key(handler, parsed)
    if key is None:
        return False
    now = time.monotonic()
    with _LOCK:
        entry = _MEMO.get(key)
    if entry is not None and 0 <= now - entry[0] < ttl:
        from api.helpers import send_json_body

        send_json_body(handler, entry[1])
        return True
    raw_path = getattr(handler, "path", None)
    generation = _GENERATION[0]

    def capture(body: bytes) -> None:
        if getattr(handler, "command", "") != "GET" or getattr(handler, "path", None) != raw_path:
            return
        with _LOCK:
            if generation != _GENERATION[0]:
                return  # a write landed while this answer was being built
            if key not in _MEMO and len(_MEMO) >= _MAX:
                _MEMO.pop(min(_MEMO, key=lambda k: _MEMO[k][0]), None)
            _MEMO[key] = (time.monotonic(), body)

    handler._poll_memo_capture = capture
    return False


_GENERATION = [0]


def invalidate(path: str = "") -> None:
    """A write request: forget everything unless it cannot affect the answers."""
    if path in _QUIET_WRITES:
        return
    with _LOCK:
        _GENERATION[0] += 1
        _MEMO.clear()
