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
_RESOLUTIONS = ContextVar("webui_skill_learning_resolutions", default=None)
_INSTALL_LOCK = threading.Lock()
_MAX_BYTES = 128 * 1024
_MAX_EVENTS = 100
_RETENTION = 30 * 86400
_KINDS = ("created", "patched", "updated")
_MAX_SKILLS = 50
# Memory files a turn can change (see api/streaming._PERSISTENT_MEMORY_FILES).
_MEMORY_KEYS = ("memory", "user", "soul", "profile_memory", "profile_user", "profile_soul")
_SOURCES = ("review", "turn")


def _skill_identifier(value):
    # Native skill identifiers may have one category. Never retain a path,
    # description, tool output, or arbitrary model prose as the display name.
    if not isinstance(value, str) or not re.fullmatch(
            r"(?:[A-Za-z0-9][A-Za-z0-9._-]{0,63}/)?[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        return None
    return value


def _display_name(value):
    identifier = _skill_identifier(value)
    return identifier.rsplit("/", 1)[-1] if identifier else None


@dataclass(frozen=True)
class ReviewScope:
    actor: str
    run_id: str
    profile_home: str
    session_id: str


class _ResolvedSkills:
    """Observe existing native lookups; never perform a second skill lookup."""
    def __init__(self, profile_home):
        self.profile_home = profile_home
        self.lock = threading.Lock()
        self.names = {}

    def observe(self, name, result):
        if not _skill_identifier(name) or not isinstance(result, dict) or not result.get("path"):
            return
        resource = None
        try:
            root = _safe(Path(self.profile_home).absolute() / "skills").resolve()
            target = _safe(Path(result["path"]).absolute()).resolve()
            resource = _skill_identifier(target.relative_to(root).as_posix())
        except (OSError, TypeError, ValueError):
            pass
        with self.lock:
            if name in self.names or len(self.names) < 256:
                choices = self.names.setdefault(name, set())
                # Two distinct choices are enough to keep this name ambiguous.
                if len(choices) < 2:
                    choices.add(resource)

    def get(self, name):
        with self.lock:
            choices = self.names.get(name, ())
            return next(iter(choices)) if len(choices) == 1 else None


def _operation_resource(operation, arguments, result, resolutions):
    name = _skill_identifier(operation.get("name") or arguments.get("name"))
    if not name:
        return None
    if operation.get("action") == "create":
        # Native create takes category separately; its name must be a basename.
        if "/" in name:
            return None
        category = operation.get("category")
        if category:
            if not _skill_identifier(category) or "/" in category:
                return None
            name = category + "/" + name
        # Flat native create returns this relative path; batch results omit it.
        if "path" in result and result["path"] != name:
            return None
        return name
    # Explicit native category/name lookups have exact relative-path semantics.
    if "/" in name:
        return name
    # Bare-name patch/edit can target any category or external root. A name
    # without an observed unique native resolution is deliberately not exposed.
    return resolutions.get(name) if resolutions is not None else None


def _actor(value):
    value = str(value or "").strip().lower()
    if not re.fullmatch(r"[^\s@<>/\\]{1,160}@[^\s@<>/\\]{1,160}", value):
        raise ValueError("Signed-in user required")
    return value


def successful_skill_changes(messages, prior, *, resolutions=None):
    """Join native structured calls/results. Ambiguous evidence is ignored."""
    counts = dict.fromkeys(_KINDS, 0)
    skills = {}
    if not isinstance(messages, list) or not isinstance(prior, list):
        return counts, []
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
                           and out.get("success") is True and not out.get("error")
                           and not out.get("staged") and not out.get("pending_id")
                           and out.get("action") == op.get("action")
                           for op, out in zip(operations, results, strict=True)):
                    continue
            else:
                operations = [arguments]
            for index, operation in enumerate(operations):
                action = operation.get("action")
                if action == "patch" and operation.get("old_string") == operation.get("new_string"):
                    continue
                kind = {"create": "created", "patch": "patched", "edit": "updated",
                        "write_file": "updated", "remove_file": "updated"}.get(action)
                if kind:
                    counts[kind] += 1
                    outcome = result["results"][index] if "results" in result and arguments.get("operations") is not None else result
                    resource = _operation_resource(operation, arguments, outcome, resolutions)
                    if resource:
                        key = (resource, kind)
                        if key in skills or len(skills) < _MAX_SKILLS:
                            skills[key] = skills.get(key, 0) + 1
        except (ValueError, TypeError):
            continue
    return counts, [{"name": _display_name(resource), "resource": resource, "kind": kind, "count": count}
                    for (resource, kind), count in skills.items()]


def successful_skill_counts(messages, prior):
    return successful_skill_changes(messages, prior)[0]


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


def _counts(value, *, allow_empty=False):
    return (isinstance(value, dict) and set(value) == set(_KINDS)
            and all(type(v) is int and 0 <= v <= 10000 for v in value.values())
            and (allow_empty or any(value.values())))


def _memory(value):
    return (isinstance(value, list) and len(value) <= len(_MEMORY_KEYS)
            and len(set(value)) == len(value) and all(v in _MEMORY_KEYS for v in value))


def _skills(value, counts):
    if not isinstance(value, list) or len(value) > _MAX_SKILLS:
        return False
    totals, seen = dict.fromkeys(_KINDS, 0), set()
    for row in value:
        if (not isinstance(row, dict) or set(row) not in (
                {"name", "kind", "count"}, {"name", "resource", "kind", "count"})
                or _display_name(row.get("name")) != row.get("name")
                or not isinstance(row.get("name"), str) or "/" in row["name"]
                or row.get("kind") not in _KINDS or type(row.get("count")) is not int
                or not 1 <= row["count"] <= 10000
                or _display_name(row.get("resource", row["name"])) != row["name"]):
            return False
        key = (row.get("resource", row["name"]), row["kind"])
        if key in seen:
            return False
        seen.add(key)
        totals[row["kind"]] += row["count"]
    return all(totals[k] <= counts[k] for k in _KINDS)


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
        if not isinstance(row, dict):
            raise ValueError("Invalid activity storage")
        keys = set(row)
        if not {"id", "session", "created_at", "counts"} <= keys or not keys <= {
                "id", "session", "created_at", "counts", "skills", "memory", "source"}:
            raise ValueError("Invalid activity storage")
        memory = row.get("memory", [])
        if (not re.fullmatch(r"[0-9a-f]{64}", str(row.get("id", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("session", "")))
                or type(row.get("created_at")) is not int
                or row["created_at"] < 0
                or not _memory(memory)
                or not _counts(row.get("counts"), allow_empty=bool(memory))
                or not _skills(row.get("skills", []), row["counts"])
                or row.get("source", "review") not in _SOURCES):
            raise ValueError("Invalid activity storage")
    return [row for row in data if now - _RETENTION <= row["created_at"] <= now + 300]


def record(scope, counts, *, skills=None, memory=None, source="review", now=None):
    """Best effort; persistence failure must never change a review outcome."""
    memory = [] if memory is None else list(memory)
    if (not _memory(memory) or not _counts(counts, allow_empty=bool(memory))
            or not _skills([] if skills is None else skills, counts) or source not in _SOURCES):
        return False
    now = int(time.time() if now is None else now)
    try:
        path, lock = _paths(scope.actor)
        ident = hashlib.sha256((scope.actor + "\0" + scope.run_id).encode()).hexdigest()
        with _locked(lock):
            rows = _load(path, now)
            if any(row["id"] == ident for row in rows):
                return True
            row = {"id": ident, "session": hashlib.sha256(scope.session_id.encode()).hexdigest(),
                   "created_at": now, "counts": dict(counts),
                   "skills": [{**skill, "resource": skill.get("resource", skill["name"])} for skill in skills or []]}
            if memory:
                row["memory"] = memory
            if source != "review":
                row["source"] = source
            rows.append(row)
            rows = sorted(rows, key=lambda row: row["created_at"])[-_MAX_EVENTS:]
            # Name metadata must not make a valid store unreadable at its byte cap.
            encoded = json.dumps(rows, separators=(",", ":")).encode("utf-8")
            while len(encoded) > _MAX_BYTES:
                rows.pop(0)
                encoded = json.dumps(rows, separators=(",", ":")).encode("utf-8")
            fd, temp = tempfile.mkstemp(prefix=".activity-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encoded)
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


def read_activity(actor, session_id, *, now=None, access=None):
    from api.governance.resource_scope import allowed
    path, lock = _paths(_actor(actor))
    with _locked(lock):
        rows = _load(path, int(time.time() if now is None else now))
    session_key = hashlib.sha256(session_id.encode()).hexdigest()
    events = []
    for row in reversed(rows):
        if row["session"] != session_key:
            continue
        counts, names = dict(row["counts"]), {}
        for skill in row.get("skills", []):
            name, kind = skill["name"], skill["kind"]
            if not allowed(access, "skills_view", skill.get("resource", name), (name,)):
                counts[kind] -= skill["count"]
                continue
            key = (name, kind)
            names[key] = names.get(key, 0) + skill["count"]
        memory = list(row.get("memory", []))
        if not any(counts.values()) and not memory:
            continue
        events.append({"id": row["id"], "created_at": row["created_at"], "counts": counts,
                       "skills": [{"name": name, "kind": kind, "count": count}
                                  for (name, kind), count in names.items()],
                       "memory": memory, "source": row.get("source", "review")})
    return {"events": events, "coverage": "observed_changes_only",
            "retention_days": 30}


def install_adapter():
    """Observe native structured results without changing engine outcomes."""
    try:
        from agent import background_review as native
        from tools import skill_manager_tool as manager
        with _INSTALL_LOCK:
            finder = manager._find_skill
            if not getattr(finder, "_webui_skill_resolution", False):
                @functools.wraps(finder)
                def observed_find(*args, **kwargs):
                    result = finder(*args, **kwargs)
                    capture = _RESOLUTIONS.get()
                    if capture is not None:
                        try:
                            capture.observe(args[0] if args else kwargs.get("name"), result)
                        except Exception:
                            pass  # Optional metadata never changes a tool result.
                    return result
                observed_find._webui_skill_resolution = True
                manager._find_skill = observed_find
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
                    resolution_token = _RESOLUTIONS.set(_ResolvedSkills(captured.profile_home))
                    try:
                        return target()
                    finally:
                        _RESOLUTIONS.reset(resolution_token)
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
                            counts, skills = successful_skill_changes(review_messages, prior_snapshot or [], resolutions=_RESOLUTIONS.get())
                            record(scope, counts, skills=skills)
                        except Exception:
                            logger.warning("Could not observe private skill learning activity")
            spawn._webui_skill_activity = True
            native.summarize_background_review_actions = summarize
            native.spawn_background_review_thread = spawn
        return True
    except (ImportError, AttributeError, TypeError, ValueError):
        return False


def record_turn_changes(changes, *, now=None):
    """Persist what THIS turn changed on disk (api/streaming's file-signature
    diff) as a notice for the person who spoke. Complements the background
    review path: that one only sees the review thread's own skill_manage
    calls, so a skill the agent created or a memory note it saved during the
    conversation itself never showed up after the toast faded.
    """
    scope = _TURN.get()
    if scope is None or not isinstance(changes, dict):
        return False
    counts = dict.fromkeys(_KINDS, 0)
    skills = {}
    for change in changes.get("skills") or []:
        if not isinstance(change, dict):
            continue
        kind = "created" if change.get("action") == "created" else "updated"
        rel = str(change.get("path") or "")
        resource = _skill_identifier(rel[:-len("/SKILL.md")] if rel.endswith("/SKILL.md") else rel.rsplit("/SKILL.md", 1)[0]) if rel else None
        name = _display_name(resource) if resource else _display_name(change.get("name"))
        if not name:
            continue
        counts[kind] += 1
        key = (resource or name, kind)
        if key in skills or len(skills) < _MAX_SKILLS:
            skills[key] = skills.get(key, 0) + 1
    memory = [key for key in (changes.get("memory") or []) if key in _MEMORY_KEYS]
    if not any(counts.values()) and not memory:
        return False
    return record(scope, counts,
                  skills=[{"name": _display_name(resource), "resource": resource, "kind": kind, "count": count}
                          for (resource, kind), count in skills.items()],
                  memory=memory, source="turn", now=now)


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
        from api.governance.resource_scope import access_for
        data = read_activity(actor, ids[0], access=access_for(handler))
    except Exception:
        return j(handler, {"error": "Skill activity is unavailable. Please try again."}, status=503, extra_headers=headers)
    return j(handler, data, extra_headers=headers)
