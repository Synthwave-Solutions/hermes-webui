"""Private metadata for confirmed automatic skill changes; never content."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
try:
    import fcntl
except ImportError:  # Optional observability must not disable Windows chat.
    fcntl = None
import functools
import hashlib
import inspect
import json
import logging
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time
import uuid
from urllib.parse import parse_qs

from api.helpers import j

logger = logging.getLogger(__name__)
_TURN = ContextVar("webui_skill_learning_turn", default=None)
_REVIEW = ContextVar("webui_skill_learning_review", default=None)
_INSTALL_LOCK = threading.Lock()
_MAX_BYTES = 128 * 1024
_MAX_EVENTS = 100
_RETENTION = 30 * 86400
_KINDS = ("created", "patched", "updated")


@dataclass(frozen=True)
class ReviewScope:
    actor: str
    run_id: str
    profile_home: str
    session_id: str


def _actor(value):
    value = str(value or "").strip().lower()
    if not re.fullmatch(r"[^\s@<>/\\]{1,160}@[^\s@<>/\\]{1,160}", value):
        raise ValueError("Signed-in user required")
    return value


def successful_skill_counts(messages, prior):
    """Join native structured calls/results. Ambiguous evidence is ignored."""
    counts = dict.fromkeys(_KINDS, 0)
    if not isinstance(messages, list) or not isinstance(prior, list):
        return counts
    old = {m.get("tool_call_id") for m in prior if isinstance(m, dict)
           and isinstance(m.get("tool_call_id"), str)}
    for msg in prior:
        if isinstance(msg, dict):
            for call in msg.get("tool_calls", []) or []:
                if isinstance(call, dict) and isinstance(call.get("id"), str):
                    old.add(call.get("id"))
    calls, duplicate = {}, set()
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for call in msg.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            cid, fn = call.get("id"), call.get("function")
            if not isinstance(cid, str) or not cid or not isinstance(fn, dict):
                continue
            if cid in calls:
                duplicate.add(cid)
            calls[cid] = fn
    seen = set()
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "tool":
            continue
        cid = msg.get("tool_call_id")
        if not isinstance(cid, str) or cid in old or cid in seen or cid in duplicate:
            continue
        seen.add(cid)
        fn = calls.get(cid, {})
        if fn.get("name") != "skill_manage":
            continue
        try:
            raw, args = msg.get("content"), fn.get("arguments")
            if not isinstance(raw, str) or not isinstance(args, str) or max(len(raw), len(args)) > 1024 * 1024:
                continue
            result, arguments = json.loads(raw), json.loads(args)
            if (not isinstance(result, dict) or result.get("success") is not True
                    or result.get("staged") or result.get("pending_id") or result.get("error")
                    or not isinstance(arguments, dict)):
                continue
            operations = arguments.get("operations")
            if operations is not None:
                results = result.get("results")
                if (not isinstance(operations, list) or not isinstance(results, list)
                        or len(operations) != len(results)
                        or type(result.get("operations_applied")) is not int
                        or result["operations_applied"] != len(operations)):
                    continue
                if not all(isinstance(op, dict) and isinstance(out, dict)
                           and out.get("success") is True and out.get("action") == op.get("action")
                           for op, out in zip(operations, results, strict=True)):
                    continue
            else:
                operations = [arguments]
            for operation in operations:
                action = operation.get("action")
                if action == "patch" and operation.get("old_string") == operation.get("new_string"):
                    continue
                kind = {"create": "created", "patch": "patched", "edit": "updated",
                        "write_file": "updated", "remove_file": "updated"}.get(action)
                if kind:
                    counts[kind] += 1
        except (ValueError, TypeError):
            continue
    return counts


def _safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise OSError("Unsafe activity storage")
    return path


def _paths(actor):
    from api.config import STATE_DIR
    if fcntl is None or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "getuid"):
        raise OSError("Private activity storage unavailable")
    root = _safe(Path(STATE_DIR).absolute() / "skill_learning_activity")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise OSError("Unsafe activity storage")
    key = hashlib.sha256(_actor(actor).encode()).hexdigest()
    return _safe(root / (key + ".json")), _safe(root / (key + ".lock"))


def _open_regular(path, flags):
    fd = os.open(_safe(path), flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        os.close(fd)
        raise OSError("Unsafe activity file")
    return fd


@contextmanager
def _locked(path):
    fd = _open_regular(path, os.O_RDWR | os.O_CREAT)
    try:
        deadline = time.monotonic() + 1
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OSError("Activity storage busy") from None
                time.sleep(0.01)
        yield
    finally:
        os.close(fd)


def _counts(value):
    return (isinstance(value, dict) and set(value) == set(_KINDS)
            and all(type(v) is int and 0 <= v <= 10000 for v in value.values())
            and any(value.values()))


def _load(path, now):
    try:
        fd = _open_regular(path, os.O_RDONLY)
    except FileNotFoundError:
        return []
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError("Activity storage exceeds limit")
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) > _MAX_EVENTS:
        raise ValueError("Invalid activity storage")
    for row in data:
        if (not isinstance(row, dict) or set(row) != {"id", "session", "created_at", "counts"}
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("id", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("session", "")))
                or type(row.get("created_at")) is not int
                or row["created_at"] < 0 or not _counts(row.get("counts"))):
            raise ValueError("Invalid activity storage")
    return [row for row in data if now - _RETENTION <= row["created_at"] <= now + 300]


def record(scope, counts, *, now=None):
    """Best effort; persistence failure must never change a review outcome."""
    if not _counts(counts):
        return False
    now = int(time.time() if now is None else now)
    try:
        path, lock = _paths(scope.actor)
        ident = hashlib.sha256((scope.actor + "\0" + scope.run_id).encode()).hexdigest()
        with _locked(lock):
            rows = _load(path, now)
            if any(row["id"] == ident for row in rows):
                return True
            rows.append({"id": ident, "session": hashlib.sha256(scope.session_id.encode()).hexdigest(),
                         "created_at": now, "counts": dict(counts)})
            rows = sorted(rows, key=lambda row: row["created_at"])[-_MAX_EVENTS:]
            fd, temp = tempfile.mkstemp(prefix=".activity-", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(rows, stream, separators=(",", ":"))
                    stream.flush()
                    os.fsync(stream.fileno())
                _safe(path)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
        return True
    except Exception:
        logger.warning("Could not record private skill learning activity")
        return False


def read_activity(actor, session_id, *, now=None):
    path, lock = _paths(_actor(actor))
    with _locked(lock):
        rows = _load(path, int(time.time() if now is None else now))
    session_key = hashlib.sha256(session_id.encode()).hexdigest()
    events = [{k: row[k] for k in ("id", "created_at", "counts")}
              for row in reversed(rows) if row["session"] == session_key]
    return {"events": events, "coverage": "observed_changes_only",
            "retention_days": 30}


def install_adapter():
    """Observe native structured results without changing engine outcomes."""
    try:
        from agent import background_review as native
        with _INSTALL_LOCK:
            original_spawn = native.spawn_background_review_thread
            original_summary = native.summarize_background_review_actions
            if getattr(original_spawn, "_webui_skill_activity", False):
                return True
            signature = inspect.signature(original_spawn)

            @functools.wraps(original_spawn)
            def spawn(*args, **kwargs):
                target, prompt = original_spawn(*args, **kwargs)
                scope = _TURN.get()
                bound = signature.bind_partial(*args, **kwargs).arguments
                if scope is None or bound.get("focus") is not None:
                    return target, prompt
                captured = ReviewScope(scope.actor, scope.run_id + ":" + uuid.uuid4().hex,
                                       scope.profile_home, scope.session_id)

                def observed_target():
                    token = _REVIEW.set(captured)
                    try:
                        return target()
                    finally:
                        _REVIEW.reset(token)
                return observed_target, prompt

            @functools.wraps(original_summary)
            def summarize(review_messages, prior_snapshot=None, *args, **kwargs):
                try:
                    return original_summary(review_messages, prior_snapshot, *args, **kwargs)
                finally:
                    scope = _REVIEW.get()
                    if scope is not None:
                        try:
                            record(scope, successful_skill_counts(review_messages, prior_snapshot or []))
                        except Exception:
                            logger.warning("Could not observe private skill learning activity")
            spawn._webui_skill_activity = True
            native.summarize_background_review_actions = summarize
            native.spawn_background_review_thread = spawn
        return True
    except (ImportError, AttributeError, TypeError, ValueError):
        return False


@contextmanager
def turn_scope(actor, run_id, profile_home, session_id):
    try:
        scope = ReviewScope(_actor(actor), str(run_id), str(profile_home), str(session_id))
    except ValueError:
        scope = None
    install_adapter()
    token = _TURN.set(scope)
    try:
        yield
    finally:
        _TURN.reset(token)


def handle_get(handler, query):
    from api.ownership import _request_identity
    from api.personal_context import session_for
    headers = {"Cache-Control": "no-store"}
    identity = _request_identity(handler)
    try:
        actor = _actor((identity or {}).get("email"))
    except ValueError:
        return j(handler, {"error": "Sign in to view your skill activity"}, status=401, extra_headers=headers)
    params = parse_qs(query, keep_blank_values=True)
    ids = params.get("session_id", [])
    if set(params) != {"session_id"} or len(ids) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", ids[0]):
        return j(handler, {"error": "A single conversation is required"}, status=400, extra_headers=headers)
    try:
        if session_for(identity, ids[0]) is None:
            raise KeyError("Missing conversation")
    except (KeyError, PermissionError):
        return j(handler, {"error": "Conversation unavailable"}, status=404, extra_headers=headers)
    try:
        return j(handler, read_activity(actor, ids[0]), extra_headers=headers)
    except (OSError, ValueError, TypeError):
        return j(handler, {"error": "Skill activity is unavailable. Please try again."}, status=503, extra_headers=headers)
