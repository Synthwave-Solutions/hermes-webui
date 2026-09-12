"""Private, bounded clarification preferences; never a grant or approval store."""
from contextlib import contextmanager
import json
import os
import re
import stat
import tempfile
import time

try:
    import fcntl
except ImportError:  # Windows: never silently replace a process lock with no lock.
    fcntl = None

from api import personal_context

_MODES = {"balanced", "minimal"}
_SID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_MAX_BYTES = 128 * 1024
_MAX_TASKS = 1000
_MISSING = object()


class ConflictError(ValueError):
    """Another tab saved a newer revision."""


class StoreError(ValueError):
    """An existing store cannot be safely read or replaced."""


def _session(identity, sid):
    if sid is None or sid == "":
        return None
    if not isinstance(sid, str) or not _SID.fullmatch(sid):
        raise ValueError("Invalid conversation")
    personal_context.session_for(identity, sid)
    return sid


def _path(identity):
    return personal_context._safe(personal_context.home(identity) / "interaction-preferences.json")


def _validate(data):
    if not isinstance(data, dict) or set(data) != {"version", "revision", "user_mode", "tasks"}:
        raise StoreError("Preferences could not be read")
    if data["version"] != 1 or type(data["revision"]) is not int or data["revision"] < 0:
        raise StoreError("Preferences could not be read")
    if not isinstance(data["user_mode"], str) or data["user_mode"] not in _MODES:
        raise StoreError("Preferences could not be read")
    tasks = data["tasks"]
    if not isinstance(tasks, dict) or len(tasks) > _MAX_TASKS or any(
        not isinstance(sid, str) or not _SID.fullmatch(sid)
        or not isinstance(mode, str) or mode not in _MODES
        for sid, mode in tasks.items()
    ):
        raise StoreError("Preferences could not be read")
    return data


def _load(identity):
    path = _path(identity)
    if not hasattr(os, "O_NOFOLLOW"):
        raise OSError("Safe preference storage is unavailable on this platform")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return {"version": 1, "revision": 0, "user_mode": "balanced", "tasks": {}}
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise StoreError("Preferences could not be read")
            raw = stream.read(_MAX_BYTES + 1)
        if len(raw.encode()) > _MAX_BYTES:
            raise StoreError("Preferences could not be read")
        return _validate(json.loads(raw))
    except (ValueError, UnicodeError) as exc:
        raise StoreError("Preferences could not be read") from exc


def _view(data, sid):
    override = data["tasks"].get(sid) if sid else None
    return {"revision": data["revision"], "user_mode": data["user_mode"],
            "session_id": sid, "task_mode": override,
            "effective_mode": override or data["user_mode"]}


def read(identity, session_id=None):
    sid = _session(identity, session_id)
    return _view(_load(identity), sid)


@contextmanager
def _write_lock(identity):
    if fcntl is None or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("Safe preference updates are unavailable on this platform")
    root = personal_context.ensure_home(identity)
    path = personal_context._safe(root / ".interaction-preferences.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), 0o600)
    locked = False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise StoreError("Preference lock is unavailable")
        deadline = time.monotonic() + 2
        while not locked:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise OSError("Preferences are busy") from None
                time.sleep(0.025)
        yield
    finally:
        if locked:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def write(identity, body):
    if not isinstance(body, dict) or set(body) - {"revision", "user_mode", "session_id", "task_mode"}:
        raise ValueError("Invalid preferences")
    revision, mode, override = body.get("revision"), body.get("user_mode"), body.get("task_mode")
    if type(revision) is not int or revision < 0 or not isinstance(mode, str) or mode not in _MODES:
        raise ValueError("Invalid preferences")
    if override is not None and (not isinstance(override, str) or override not in _MODES):
        raise ValueError("Invalid conversation preference")
    sid = _session(identity, body.get("session_id"))
    if override is not None and sid is None:
        raise ValueError("Select a conversation first")
    with _write_lock(identity):
        # Recheck after waiting: membership can change while another tab saves.
        _session(identity, sid)
        data = _load(identity)
        if data["revision"] != revision:
            raise ConflictError("Preferences changed in another tab. Reload before saving.")
        data["user_mode"] = mode
        if sid:
            if override is None:
                data["tasks"].pop(sid, None)
            else:
                data["tasks"][sid] = override
        if len(data["tasks"]) > _MAX_TASKS:
            raise ValueError("Conversation preference limit reached")
        data["revision"] += 1
        raw = json.dumps(data, ensure_ascii=True, sort_keys=True) + "\n"
        if len(raw.encode()) > _MAX_BYTES:
            raise ValueError("Preference storage limit reached")
        target = _path(identity)
        fd, temp = tempfile.mkstemp(prefix=".preferences-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            personal_context._safe(target)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return _view(data, sid)


def prompt_for(actor_email: str, session_id: str | None = None) -> str:
    """Fixed guidance for the current signed caller, refreshed for each turn."""
    try:
        mode = read({"email": actor_email}, session_id)["effective_mode"]
    except (PermissionError, ValueError, KeyError, OSError):
        return ""
    common = (
        "Clarification preference of the authenticated user: " + mode + ". "
        "Reuse answers and choices already supplied for this task. "
        "This preference only concerns routine clarification questions; it does not "
        "grant access, approve actions, override governance, or bypass a required approval. "
    )
    if mode == "minimal":
        return common + (
            "Use sensible defaults for reversible details and state material assumptions. "
            "Ask only when missing information blocks a correct result or a meaningful "
            "user decision; do not repeatedly ask whether to continue work already requested."
        )
    return common + "Ask concise questions when a missing choice materially affects the result."


def handle(handler, *, query=None, body=_MISSING):
    from api.governance.enforce import _request_identity
    from api.routes import bad, j
    from urllib.parse import parse_qs
    try:
        identity = _request_identity(handler)
        result = (read(identity, parse_qs(query or "").get("session_id", [None])[0])
                  if body is _MISSING else write(identity, body))
        return j(handler, result)
    except ConflictError as exc:
        return bad(handler, str(exc), 409)
    except PermissionError:
        return bad(handler, "These preferences require your own account and conversation access", 403)
    except StoreError:
        return bad(handler, "Preferences could not be read. Your saved choices were preserved.", 503)
    except (ValueError, KeyError):
        return bad(handler, "Invalid clarification preferences or conversation", 400)
    except OSError:
        return bad(handler, "Preferences are temporarily unavailable. Please retry.", 503)
