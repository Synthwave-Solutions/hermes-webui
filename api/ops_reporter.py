"""Operational error reporting from the WebUI to the control plane (W7).

Plan 3.3 ("all errors central"): the WebUI reports its own crashes, upstream
capacity incidents and, only when support telemetry is on, browser errors to
control-api's ``POST /v1/events`` with the installation's ingest key.

Switches (Appendix D), read on every call so a render change needs no code:

* ``SP_OPERATIONAL_TELEMETRY=1`` turns the reporter on. Without it, or without
  ``SP_CONTROL_URL`` and a usable ``SP_INGEST_KEY_FILE``, every function here
  returns at once: nothing is queued, spooled or sent and no thread starts.
* ``SP_DIAGNOSTIC_PAYLOADS`` (off by default, decision D6) adds redacted
  messages and allowlisted context. Browser errors are diagnostic payloads,
  so ``browser_reporting_enabled()`` (the ``support_telemetry`` flag of
  ``GET /api/settings``) also needs it. control-api enforces the
  organisation's own flag whatever the installation sends.

Guarantees:

* Never raises and never blocks a request: reporting builds one small event,
  runs it through the allowlist and the redaction, and appends it to a bounded
  in-memory queue. A background thread sends batches off the request path.
* Allowlist and redaction happen before anything is queued or written to the
  spool, and again when a spool file is read back.
* Failed sends go to a bounded spool in the WebUI state directory
  (``ops-reporter/spool``, files 0600) and are retried later with backoff;
  nothing is retried synchronously and a send failure is never reported back.
* No key material reaches a browser: the browser only ever sees a boolean.
"""

from __future__ import annotations

import atexit
import collections
import functools
import hashlib
import json
import logging
import os
import random
import re
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from api import control_plane_client

logger = logging.getLogger(__name__)

__all__ = [
    "enabled",
    "operational_telemetry_enabled",
    "diagnostic_payloads_enabled",
    "browser_reporting_enabled",
    "report_exception",
    "report_capacity",
    "handle_client_error",
    "start",
    "flush",
    "stats",
]

OPERATIONAL_ENV = "SP_OPERATIONAL_TELEMETRY"
DIAGNOSTIC_ENV = "SP_DIAGNOSTIC_PAYLOADS"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

SERVICE = "webui"
SENDER_THREAD_NAME = "sp-ops-reporter"

# Queue and batches (Appendix B: at most 100 events and 256 KB per request).
MAX_QUEUE = 200
MAX_BATCH_EVENTS = 50
MAX_BATCH_BYTES = 128 * 1024
BATCH_DELAY_S = 2.0
IDLE_WAIT_S = 30.0
IDLE_EXIT_S = 300.0
SEND_TIMEOUT_S = 10.0
BACKOFF_BASE_S = 30.0
BACKOFF_MAX_S = 900.0

# Spool (plan 2.5 bounds the core reporter's spool at 50 MB; the WebUI keeps less).
SPOOL_SUBDIR = ("ops-reporter", "spool")
SPOOL_MAX_BYTES = 5 * 1024 * 1024
SPOOL_MAX_FILES = 200
SPOOL_MAX_AGE_S = 7 * 86400
SPOOL_FILE_MAX_BYTES = 512 * 1024
SPOOL_DRAIN_FILES = 5

# POST /api/client-errors (Appendix C): at most 16 KB, 30 per minute per user.
CLIENT_ERROR_MAX_BYTES = 16 * 1024
CLIENT_ERROR_RATE_MAX = 30
CLIENT_ERROR_RATE_WINDOW_S = 60.0
_RATE_MAX_KEYS = 5000

# Field bounds.
MAX_FRAMES = 30
MAX_TEXT_IN = 4096
MAX_MESSAGE = 1024
MAX_CONTEXT_TEXT = 200

LEVELS = frozenset({"debug", "info", "warning", "error", "fatal"})
# The error_events kinds (plan 2.3) this reporter produces.
KINDS = frozenset({"error", "health", "client_error"})
# Allowlisted context keys and their types; context is sent only with
# diagnostic payloads on.
CONTEXT_KEYS = {
    "thread": str,
    "capacity_kind": str,
    "provider": str,
    "source": str,
    "url_path": str,
    "event": str,
}

_REPO_ROOT = Path(__file__).resolve().parent.parent
_IDENT_RE = re.compile(r"[^A-Za-z0-9_.:<>$-]")
_RELEASE_RE = re.compile(r"[^A-Za-z0-9._+-]")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{40}$")
_STATIC_MODULE_RE = re.compile(r"^static/[A-Za-z0-9_./-]{1,200}\.m?js$")


# ── Switches ─────────────────────────────────────────────────────────────────

def _env_flag(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().lower() in _TRUTHY


def operational_telemetry_enabled() -> bool:
    return _env_flag(OPERATIONAL_ENV)


def diagnostic_payloads_enabled() -> bool:
    return _env_flag(DIAGNOSTIC_ENV)


def enabled() -> bool:
    """Whether the reporter may queue and send anything. Never raises."""
    try:
        return operational_telemetry_enabled() and control_plane_client.ingest_configured()
    except Exception:
        return False


def browser_reporting_enabled() -> bool:
    """The ``support_telemetry`` flag of ``GET /api/settings``. Never raises."""
    try:
        return enabled() and diagnostic_payloads_enabled()
    except Exception:
        return False


# ── Redaction (patterns written for this module, not imported) ──────────────

_REDACTIONS = (
    # Authorization values: our own schemes first, then bearer and basic.
    (re.compile(r"\bSP-HMAC-SHA256\s+[^\s,\"'<>]+(?:,\s*[A-Za-z]+=[^\s,\"'<>]+)*", re.I), "[redacted]"),
    (re.compile(r"\b(?:SP-Ingest|Bearer|Basic|Token)\s+[A-Za-z0-9._~+/=:-]+", re.I), "[redacted]"),
    # JSON web tokens.
    (re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}"), "[jwt]"),
    # API key shapes.
    (re.compile(
        r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]{10,}"
        r"|xox[a-z]-[A-Za-z0-9-]{8,}|(?:test|live)_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_-]{20,}"
        r"|AKIA[A-Z0-9]{16})"), "[redacted]"),
    # Secrets passed as key=value.
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|sentry_key|auth)=[^\s&\"'<>]+"), r"\1=[redacted]"),
    # Credentials inside URLs.
    (re.compile(r"((?:https?|wss?)://)[^\s/@\"'<>]+@", re.I), r"\1"),
    # E-mail addresses.
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    # URL query strings and fragments.
    (re.compile(r"((?:https?|wss?)://[^\s?#\"'<>]*)[?#][^\s\"'<>]*", re.I), r"\1"),
    # IBANs.
    (re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,3})?\b"), "[iban]"),
    # UUIDs and long opaque hex identifiers.
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "[id]"),
    (re.compile(r"\b[0-9a-fA-F]{24,}\b"), "[id]"),
    # Phone-like numbers and long digit runs.
    (re.compile(r"(?<![\w.])\+?\d[\d \-().]{6,24}\d(?![\w.])"), None),
    (re.compile(r"\d{6,}"), "[number]"),
)


def _phone_or_keep(match: re.Match) -> str:
    text = match.group(0)
    return "[number]" if sum(ch.isdigit() for ch in text) >= 8 else text


def redact(text, limit: int = MAX_MESSAGE):
    """Scrub one string. Returns None when it cannot be scrubbed (fail closed)."""
    if text is None:
        return None
    try:
        out = str(text)[:MAX_TEXT_IN]
        for pattern, replacement in _REDACTIONS:
            out = pattern.sub(_phone_or_keep if replacement is None else replacement, out)
        out = "".join(ch if ch.isprintable() else " " for ch in out).strip()
        return out[:limit] or None
    except Exception:
        return None


# ── Event building ───────────────────────────────────────────────────────────

def _ident(value, limit: int = 128):
    if value is None:
        return None
    text = _IDENT_RE.sub("_", str(value))[:limit]
    return text or None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _release():
    module = sys.modules.get("api.updates")
    value = getattr(module, "WEBUI_VERSION", None) if module is not None else None
    if not isinstance(value, str) or not value or value == "unknown":
        return None
    return _RELEASE_RE.sub("_", value)[:64] or None


@functools.lru_cache(maxsize=1024)
def _module_for(filename: str):
    """Dotted module name of a WebUI source file, or None when not in-app."""
    try:
        path = Path(filename).resolve()
        rel = path.relative_to(_REPO_ROOT)
    except (OSError, ValueError, RuntimeError):
        return None
    parts = rel.parts
    if not parts or rel.suffix != ".py" or any(p.startswith(".") or p in ("site-packages", "node_modules") for p in parts):
        return None
    return _ident(".".join(rel.with_suffix("").parts), 200)


def _python_frames(tb) -> list:
    frames = []
    steps = 0
    while tb is not None and steps < 512:
        steps += 1
        code = tb.tb_frame.f_code
        module = _module_for(code.co_filename)
        if module:
            name = getattr(code, "co_qualname", None) or code.co_name
            frames.append({"function": _ident(name) or "?", "module": module, "in_app": True})
        tb = tb.tb_next
    return frames[-MAX_FRAMES:]


def _safe_str(value):
    if value is None:
        return None
    try:
        return str(value)[:MAX_TEXT_IN]
    except Exception:
        return None


def _exception_type_name(exc_type) -> str:
    name = getattr(exc_type, "__qualname__", None) or getattr(exc_type, "__name__", None) or "Exception"
    module = getattr(exc_type, "__module__", "") or ""
    if module and module not in ("builtins", "__main__"):
        name = f"{module}.{name}"
    return _ident(name) or "Exception"


def _clean_context(context) -> dict | None:
    if not isinstance(context, dict):
        return None
    out = {}
    for key, kind in CONTEXT_KEYS.items():
        value = context.get(key)
        if value is None or not isinstance(value, kind) or isinstance(value, bool):
            continue
        cleaned = redact(value, MAX_CONTEXT_TEXT)
        if cleaned:
            out[key] = cleaned
    return out or None


def _clean_frames(frames) -> list | None:
    if not isinstance(frames, list):
        return None
    out = []
    for frame in frames[-MAX_FRAMES:]:
        if not isinstance(frame, dict) or frame.get("in_app") is not True:
            continue
        module = frame.get("module")
        function = _ident(frame.get("function")) or "?"
        if not isinstance(module, str):
            continue
        if module.startswith("static/"):
            if not _STATIC_MODULE_RE.fullmatch(module) or ".." in module:
                continue
        else:
            module = _ident(module, 200)
            if not module:
                continue
        out.append({"function": function, "module": module, "in_app": True})
    return out or None


def sanitize_event(event, *, diagnostic: bool | None = None) -> dict | None:
    """The allowlisted, redacted form of one event, or None when unusable.

    Applied before an event is queued or spooled and again when a spool file
    is read back. Without diagnostic payloads ``message``, ``exception.value``
    and ``context`` are dropped here, before anything is written.
    """
    try:
        if not isinstance(event, dict):
            return None
        diagnostic = diagnostic_payloads_enabled() if diagnostic is None else bool(diagnostic)
        kind = event.get("kind")
        level = event.get("level")
        ts = event.get("ts")
        if kind not in KINDS or level not in LEVELS or not isinstance(ts, str) or not _TS_RE.fullmatch(ts):
            return None
        out = {"ts": ts, "service": SERVICE, "kind": kind, "level": level}
        name = _ident(event.get("logger"))
        if name:
            out["logger"] = name
        release = event.get("release")
        if isinstance(release, str):
            release = _RELEASE_RE.sub("_", release)[:64]
            if release:
                out["release"] = release
        fingerprint = event.get("fingerprint")
        if isinstance(fingerprint, str) and _FINGERPRINT_RE.fullmatch(fingerprint):
            out["fingerprint"] = fingerprint
        if kind == "client_error" or event.get("public_origin") is True:
            out["public_origin"] = True
        exc = event.get("exception")
        if isinstance(exc, dict):
            exc_out = {"type": _ident(exc.get("type")) or "Error"}
            frames = _clean_frames(exc.get("frames"))
            if frames:
                exc_out["frames"] = frames
            if diagnostic:
                value = redact(exc.get("value"))
                if value:
                    exc_out["value"] = value
            out["exception"] = exc_out
        if diagnostic:
            message = redact(event.get("message"))
            if message:
                out["message"] = message
            context = _clean_context(event.get("context"))
            if context:
                out["context"] = context
        return out
    except Exception:
        return None


# ── Queue, sender thread and spool ───────────────────────────────────────────

class _State:
    def __init__(self):
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.queue: collections.deque = collections.deque()
        self.thread: threading.Thread | None = None
        self.stopping = False
        self.in_flight = 0
        self.failures = 0
        self.backoff_until = 0.0
        self.counts = {"queued": 0, "dropped": 0, "sent": 0, "spooled": 0, "rejected": 0}
        self.rate: dict[str, list] = {}
        self.rate_lock = threading.Lock()
        # Spool files that were handled but could not be deleted; never resent.
        self.done_files: set[str] = set()


_S = _State()
_ATEXIT_REGISTERED = False


def _after_fork_in_child() -> None:
    # A forked child inherits no running thread and possibly a held lock.
    global _S
    _S = _State()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork_in_child)


def _event_size(event) -> int:
    return len(json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _spool_dir():
    try:
        from api import config

        return Path(config.STATE_DIR).joinpath(*SPOOL_SUBDIR)
    except Exception:
        return None


def _spool_files(directory: Path) -> list:
    try:
        return sorted(p for p in directory.iterdir() if p.suffix == ".json" and p.is_file())
    except OSError:
        return []


def _spool_prune(directory: Path) -> None:
    now = time.time()
    try:
        for stale in directory.glob("*.tmp"):
            try:
                if now - stale.stat().st_mtime > 3600:
                    stale.unlink()
            except OSError:
                pass
    except OSError:
        pass
    entries = []
    for path in _spool_files(directory):
        try:
            st = path.stat()
        except OSError:
            continue
        if now - st.st_mtime > SPOOL_MAX_AGE_S:
            try:
                path.unlink()
            except OSError:
                pass
            continue
        entries.append((path, st.st_size))
    total = sum(size for _, size in entries)
    while entries and (len(entries) > SPOOL_MAX_FILES or total > SPOOL_MAX_BYTES):
        path, size = entries.pop(0)
        try:
            path.unlink()
        except OSError:
            pass
        total -= size


def _spool_write(events: list) -> bool:
    """Write already sanitized events to the spool. Never raises."""
    directory = _spool_dir()
    if directory is None or not events:
        return False
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass
        written = False
        for start in range(0, len(events), MAX_BATCH_EVENTS):
            chunk = events[start:start + MAX_BATCH_EVENTS]
            data = json.dumps({"v": 1, "events": chunk}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(data) > SPOOL_FILE_MAX_BYTES:
                with _S.lock:
                    _S.counts["dropped"] += len(chunk)
                continue
            name = f"{time.time_ns():020d}-{secrets.token_hex(4)}.json"
            tmp = directory / (name + ".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, directory / name)
            written = True
            with _S.lock:
                _S.counts["spooled"] += len(chunk)
        _spool_prune(directory)
        return written
    except Exception:
        logger.debug("ops report spool write failed", exc_info=True)
        return False


def _read_spool_file(path: Path):
    try:
        if path.stat().st_size > SPOOL_FILE_MAX_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        return None
    events = [e for e in (sanitize_event(item) for item in data["events"][:100]) if e]
    return events


def _register_atexit() -> None:
    global _ATEXIT_REGISTERED
    if _ATEXIT_REGISTERED:
        return
    try:
        atexit.register(_shutdown)
        _ATEXIT_REGISTERED = True
    except Exception:
        pass


def _ensure_thread_locked() -> None:
    thread = _S.thread
    if thread is not None and thread.is_alive():
        return
    thread = threading.Thread(target=_run, name=SENDER_THREAD_NAME, daemon=True)
    _S.thread = thread
    _register_atexit()
    thread.start()


def _enqueue(event: dict, *, sync: bool = False) -> bool:
    if sync:
        return _spool_write([event])
    size = _event_size(event)
    with _S.cond:
        if _S.stopping:
            stopping = True
        else:
            stopping = False
            if len(_S.queue) >= MAX_QUEUE:
                _S.counts["dropped"] += 1
                return False
            _S.queue.append((event, size))
            _S.counts["queued"] += 1
            _ensure_thread_locked()
            _S.cond.notify_all()
    if stopping:
        return _spool_write([event])
    return True


def _take_batch() -> list:
    batch, total = [], 0
    with _S.cond:
        while _S.queue and len(batch) < MAX_BATCH_EVENTS:
            event, size = _S.queue[0]
            if batch and total + size > MAX_BATCH_BYTES:
                break
            _S.queue.popleft()
            batch.append(event)
            total += size
        if batch:
            _S.in_flight += 1
    return batch


def _batch_done() -> None:
    with _S.cond:
        _S.in_flight = max(0, _S.in_flight - 1)
        _S.cond.notify_all()


def _backoff() -> None:
    with _S.lock:
        _S.failures += 1
        delay = min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** min(_S.failures - 1, 10)))
        delay *= 0.9 + random.random() * 0.2
        _S.backoff_until = time.monotonic() + delay


def _post(events: list) -> str:
    """Send one batch. Returns ``sent``, ``retry`` or ``rejected``."""
    status, _body = control_plane_client.post_events(events, timeout=SEND_TIMEOUT_S)
    if 200 <= status < 300:
        with _S.lock:
            _S.failures = 0
            _S.backoff_until = 0.0
            _S.counts["sent"] += len(events)
        return "sent"
    if status == 0 or status in (408, 425, 429) or status >= 500:
        _backoff()
        return "retry"
    # Any other answer (400, 401, 403, 413, 422) will not change on a retry.
    logger.warning("control plane refused an ops report batch with status %s; the batch is dropped", status)
    with _S.lock:
        _S.counts["rejected"] += len(events)
    _backoff()
    return "rejected"


def _drain_spool() -> int:
    directory = _spool_dir()
    if directory is None:
        return 0
    sent = 0
    pending = [p for p in _spool_files(directory) if p.name not in _S.done_files]
    for path in pending[:SPOOL_DRAIN_FILES]:
        if time.monotonic() < _S.backoff_until:
            break
        events = _read_spool_file(path)
        outcome = _post(events) if events else "rejected"
        if outcome == "retry":
            break
        try:
            path.unlink()
        except OSError:
            # Remember it, so a file that cannot be removed is never resent.
            if len(_S.done_files) < 10000:
                _S.done_files.add(path.name)
        if outcome == "sent":
            sent += len(events)
    return sent


def _spill_queue() -> None:
    with _S.cond:
        events = [event for event, _ in _S.queue]
        _S.queue.clear()
        _S.cond.notify_all()
    if events:
        _spool_write(events)


def _wait(seconds: float) -> bool:
    """Sleep up to ``seconds``; True when the reporter is stopping."""
    with _S.cond:
        return _S.cond.wait_for(lambda: _S.stopping, timeout=max(0.0, seconds))


def _run() -> None:
    me = threading.current_thread()
    last_activity = time.monotonic()
    busy = True  # the first pass looks at the spool at once
    try:
        while True:
            with _S.cond:
                if _S.stopping or _S.thread is not me:
                    return
                if not _S.queue and not busy:
                    _S.cond.wait(timeout=IDLE_WAIT_S)
                if _S.stopping:
                    return
                has_queue = bool(_S.queue)
            busy = False
            if not enabled():
                # Switched off at runtime: keep nothing in memory, send nothing.
                with _S.cond:
                    _S.counts["dropped"] += len(_S.queue)
                    _S.queue.clear()
                    if _S.thread is me:
                        _S.thread = None
                    _S.cond.notify_all()
                return
            wait = _S.backoff_until - time.monotonic()
            if wait > 0:
                if has_queue:
                    _spill_queue()
                if _wait(min(wait, IDLE_WAIT_S)):
                    return
                continue
            if has_queue:
                if BATCH_DELAY_S > 0 and _wait(BATCH_DELAY_S):
                    return
                batch = _take_batch()
                if batch:
                    try:
                        outcome = _post(batch)
                        if outcome == "retry":
                            _spool_write(batch)
                    finally:
                        _batch_done()
                    last_activity = time.monotonic()
                    busy = True
                    if outcome == "retry":
                        continue
            if _drain_spool():
                last_activity = time.monotonic()
                busy = True
                continue
            with _S.cond:
                if _S.queue or _S.stopping or busy:
                    continue
                if time.monotonic() - last_activity >= IDLE_EXIT_S:
                    directory = _spool_dir()
                    if directory is None or all(p.name in _S.done_files for p in _spool_files(directory)):
                        _S.thread = None
                        return
    except Exception:
        logger.debug("ops reporter sender stopped", exc_info=True)
        with _S.cond:
            if _S.thread is me:
                _S.thread = None
            _S.cond.notify_all()


def _shutdown() -> None:
    """atexit: keep what is still queued in the spool; send nothing."""
    try:
        with _S.cond:
            _S.stopping = True
            events = [event for event, _ in _S.queue]
            _S.queue.clear()
            _S.cond.notify_all()
        if events:
            _spool_write(events)
    except Exception:
        pass


def start() -> bool:
    """Start the sender at startup when spooled reports are waiting. Never raises."""
    try:
        if not enabled():
            return False
        directory = _spool_dir()
        if directory is None or not _spool_files(directory):
            return False
        with _S.cond:
            if _S.stopping:
                return False
            _ensure_thread_locked()
            _S.cond.notify_all()
        return True
    except Exception:
        return False


def flush(timeout: float = 5.0) -> bool:
    """Wait until the queue is empty and no batch is being sent (tests, diagnostics)."""
    deadline = time.monotonic() + max(0.0, float(timeout))
    with _S.cond:
        _S.cond.notify_all()
        while _S.queue or _S.in_flight:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            _S.cond.wait(timeout=min(remaining, 0.05))
    return True


def stats() -> dict:
    """Counters only (no event content, no key material)."""
    with _S.lock:
        out = dict(_S.counts)
        out["pending"] = len(_S.queue)
        out["sender_running"] = bool(_S.thread is not None and _S.thread.is_alive())
    return out


def _reset_for_tests() -> None:
    global _S
    old = _S
    with old.cond:
        old.stopping = True
        thread = old.thread
        old.cond.notify_all()
    if thread is not None and thread is not threading.current_thread():
        thread.join(timeout=5)
    _S = _State()
    control_plane_client.clear_cache()


# ── Reporting entry points ───────────────────────────────────────────────────

def _submit(event: dict, *, sync: bool = False) -> bool:
    clean = sanitize_event(event)
    if clean is None:
        return False
    return _enqueue(clean, sync=sync)


def report_exception(exc_type, exc_value, exc_tb, *, level: str = "error", logger_name: str | None = None,
                     message: str | None = None, context: dict | None = None, sync: bool = False) -> bool:
    """Report one uncaught exception. ``sync`` writes straight to the spool
    (the main thread is about to die, so no sender would get to run).
    Returns whether the report was kept. Never raises."""
    try:
        if not enabled() or exc_type is None:
            return False
        if threading.current_thread().name == SENDER_THREAD_NAME:
            return False  # the reporter never reports itself
        event = {
            "ts": _now_iso(),
            "kind": "error",
            "level": level if level in LEVELS else "error",
            "logger": logger_name,
            "release": _release(),
            "exception": {
                "type": _exception_type_name(exc_type),
                "value": _safe_str(exc_value),
                "frames": _python_frames(exc_tb),
            },
            "message": message,
            "context": context,
        }
        return _submit(event, sync=sync)
    except Exception:
        return False


def report_capacity(kind, provider=None, *, source=None) -> bool:
    """Report one upstream capacity incident (a fresh alert in capacity_alerts).

    Operational telemetry keeps the incident kind in the logger name and an
    explicit fingerprint per kind and provider; the provider name itself is
    context, sent only with diagnostic payloads. Never raises."""
    try:
        if not enabled():
            return False
        kind = _ident(kind, 40)
        if not kind:
            return False
        provider = str(provider or "unknown").strip().lower()[:64] or "unknown"
        fingerprint = hashlib.sha1(f"{SERVICE}|capacity|{kind}|{provider}".encode("utf-8")).hexdigest()
        event = {
            "ts": _now_iso(),
            "kind": "health",
            "level": "warning",
            "logger": f"capacity.{kind}",
            "release": _release(),
            "fingerprint": fingerprint,
            "message": f"Upstream capacity incident: {kind}",
            "context": {"capacity_kind": kind, "provider": provider, "source": str(source or "")[:80] or None},
        }
        return _submit(event)
    except Exception:
        return False


# ── POST /api/client-errors ──────────────────────────────────────────────────

def _no_content(handler) -> bool:
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return True


def _close_connection(handler) -> None:
    """The request body was left unread: the connection must not be reused."""
    try:
        handler.close_connection = True
    except Exception:
        pass


def _refuse(handler, status: int, code: str, extra_headers: dict | None = None) -> bool:
    if status == 413:
        _close_connection(handler)
    try:
        from api.helpers import j

        j(handler, {"error": code}, status=status, extra_headers=extra_headers)
    except Exception:
        data = json.dumps({"error": code}).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        for key, value in (extra_headers or {}).items():
            handler.send_header(key, value)
        handler.end_headers()
        handler.wfile.write(data)
    return True


def _content_length(handler):
    headers = getattr(handler, "headers", None)
    raw = None
    if headers is not None:
        try:
            raw = headers.get("Content-Length")
        except Exception:
            raw = None
    if raw in (None, ""):
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _rate_key(handler) -> str:
    try:
        from api.ownership import request_owner_email

        email = request_owner_email(handler)
        if email:
            return "user:" + str(email).strip().lower()
    except Exception:
        pass
    try:
        address = getattr(handler, "client_address", None)
        if address:
            return "ip:" + str(address[0])
    except Exception:
        pass
    return "anonymous"


def _client_error_rate_limited(key: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    cutoff = now - CLIENT_ERROR_RATE_WINDOW_S
    with _S.rate_lock:
        stamps = [ts for ts in _S.rate.get(key, ()) if ts > cutoff]
        if len(stamps) >= CLIENT_ERROR_RATE_MAX:
            _S.rate[key] = stamps
            return True
        stamps.append(now)
        _S.rate[key] = stamps
        if len(_S.rate) > _RATE_MAX_KEYS:
            for stale in [k for k, v in _S.rate.items() if not v or v[-1] <= cutoff]:
                del _S.rate[stale]
            while len(_S.rate) > _RATE_MAX_KEYS:
                del _S.rate[next(iter(_S.rate))]
    return False


def _browser_module(value):
    """``static/<file>.js`` from a script URL of this WebUI, or None."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:1024].split("#", 1)[0].split("?", 1)[0]
    marker = text.rfind("/static/")
    if marker < 0:
        if not text.startswith("static/"):
            return None
        module = text
    else:
        module = text[marker + 1:]
    if ".." in module or not _STATIC_MODULE_RE.fullmatch(module):
        return None
    return module


def _client_error_event(body: dict):
    frames = []
    raw_frames = body.get("frames")
    if isinstance(raw_frames, list):
        for frame in raw_frames[:50]:
            if not isinstance(frame, dict):
                continue
            module = _browser_module(frame.get("file"))
            if module:
                frames.append({"function": frame.get("function") or "?", "module": module, "in_app": True})
    event_kind = body.get("kind")
    url_path = body.get("url_path")
    if isinstance(url_path, str):
        url_path = url_path[:512].split("#", 1)[0].split("?", 1)[0]
    message = body.get("message") if isinstance(body.get("message"), str) else None
    error_type = body.get("type") if isinstance(body.get("type"), str) else None
    if not error_type and not message and not frames:
        return None
    return {
        "ts": _now_iso(),
        "kind": "client_error",
        "level": "error",
        "logger": "browser",
        "release": _release(),
        "public_origin": True,
        "exception": {"type": (error_type or "Error")[:128], "value": message, "frames": frames},
        "message": message,
        "context": {
            "url_path": url_path if isinstance(url_path, str) else None,
            "event": event_kind if event_kind in ("error", "unhandledrejection") else None,
        },
    }


def handle_client_error(handler, body) -> bool:
    """``POST /api/client-errors`` (Appendix C, a self route).

    Answers 204 and stores nothing unless support telemetry is on. Otherwise
    the body may be at most 16 KB, each user may send 30 reports a minute,
    and a report is reduced to the allowlisted fields, redacted, marked
    ``public_origin`` and queued. ``body`` may be None, in which case this
    handler reads the body itself with the 16 KB cap. Never raises.
    """
    try:
        length = _content_length(handler)
        # With body None the caller left the body to this handler; every
        # answer given before reading it must close the connection.
        unread = body is None and length != 0
        if not browser_reporting_enabled():
            if unread:
                _close_connection(handler)
            return _no_content(handler)
        if length is None:
            _close_connection(handler)
            return _refuse(handler, 400, "invalid_content_length")
        if length > CLIENT_ERROR_MAX_BYTES:
            return _refuse(handler, 413, "report_too_large")
        if _client_error_rate_limited(_rate_key(handler)):
            if unread:
                _close_connection(handler)
            return _refuse(handler, 429, "rate_limited", {"Retry-After": str(int(CLIENT_ERROR_RATE_WINDOW_S))})
        if body is None:
            raw = handler.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode("utf-8")) if raw else None
            except (UnicodeDecodeError, ValueError):
                body = None
        if not isinstance(body, dict):
            return _refuse(handler, 400, "invalid_report")
        try:
            if len(json.dumps(body, ensure_ascii=False).encode("utf-8")) > CLIENT_ERROR_MAX_BYTES:
                return _refuse(handler, 413, "report_too_large")
        except (TypeError, ValueError):
            return _refuse(handler, 400, "invalid_report")
        event = _client_error_event(body)
        if event is None:
            return _refuse(handler, 400, "invalid_report")
        _submit(event)
        return _no_content(handler)
    except Exception:
        logger.debug("client error report failed", exc_info=True)
        _close_connection(handler)  # the body may be partly unread
        try:
            return _no_content(handler)
        except Exception:
            return True
