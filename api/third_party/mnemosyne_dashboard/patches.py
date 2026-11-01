"""Hardening patches for the vendored ``dashboard_core`` (plan addendum 6.6.7).

Applied once, at import, by the package ``__init__``. The upstream file stays
byte-identical to the pinned release; everything below replaces behaviour
that the Memory explorer must never have:

* connections are always closed when their ``with`` block ends (upstream
  leaks them), are opened ``mode=ro`` (never ``immutable``) with
  ``query_only`` on, and only for a path in the registry allowlist;
* ``DashboardStore()`` without a path raises, and ``default_db_path`` and
  ``plugin_data_dir`` raise, so nothing falls back to a default memory store
  or writes under the service home;
* every write method, the read-write connection, the full-database backup,
  the content audit log and the file-path diagnostics raise;
* search patterns are anchored, so a search is linear in the memory length
  (the quadratic upstream pattern took about 13 s on a large store);
* long queries stop at a per-request deadline through SQLite's progress
  handler;
* derived labels never carry an internal product name.
"""

from __future__ import annotations

import os
import re
import sqlite3
import stat
import threading
import time
from pathlib import Path
from urllib.parse import quote

_LOCK = threading.Lock()
_ALLOWED: frozenset[str] = frozenset()
_DEADLINE = threading.local()

# Names that never appear in text the explorer shows (plan 0.4 rule 7 and the
# addendum's denylist).
_DENYLIST_RE = re.compile(r"mnemosyne|mnemo-hub|hermes|omniroute|langgraph|litellm|n8n", re.IGNORECASE)

_WRITE_METHODS = (
    "connect_rw",
    "_audit",
    "audit_log",
    "backup_database",
    "invalidate_memory",
    "set_memory_importance",
    "set_memory_veracity",
    "set_memory_expiry",
    "supersede_memory",
    "diagnostics",
    "realtime_status",
    "realtime_event_snapshot",
    "realtime_event_delta",
)


class ReaderRefused(PermissionError):
    """An operation the Memory explorer never performs."""


def allow_paths(paths) -> frozenset[str]:
    """Replace the allowlist of store files this process may open."""
    global _ALLOWED
    cleaned = frozenset(os.path.realpath(str(p)) for p in paths if str(p).strip())
    with _LOCK:
        _ALLOWED = cleaned
    return cleaned


def allowed_paths() -> frozenset[str]:
    with _LOCK:
        return _ALLOWED


def set_deadline(seconds: float | None) -> None:
    """Stop SQLite work of this thread after ``seconds`` (None clears it)."""
    _DEADLINE.value = None if seconds is None else time.monotonic() + float(seconds)


def _deadline_passed() -> int:
    deadline = getattr(_DEADLINE, "value", None)
    return 1 if deadline is not None and time.monotonic() > deadline else 0


class _ClosingConnection(sqlite3.Connection):
    """A connection that closes when its ``with`` block ends."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def checked_path(raw) -> str:
    """The real path of an allowlisted, regular, owner-held store file."""
    if raw is None or not str(raw).strip():
        raise ReaderRefused("no store path")
    text = str(raw)
    if "\x00" in text:
        raise ReaderRefused("invalid store path")
    real = os.path.realpath(text)
    if real not in allowed_paths():
        raise ReaderRefused("store path is not in the registry")
    try:
        info = os.lstat(real)
    except OSError as exc:
        raise FileNotFoundError("store not found") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ReaderRefused("store is not a regular file")
    if info.st_uid != os.getuid():
        raise ReaderRefused("store is not owned by the service user")
    return real


def _connect(self):
    path = checked_path(self.db_path)
    uri = "file:" + quote(path, safe="/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=2, factory=_ClosingConnection, check_same_thread=True)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only=1")
        con.create_function("REGEXP", 2, self._regexp, deterministic=True)
        con.set_progress_handler(_deadline_passed, 2000)
    except Exception:
        con.close()
        raise
    return con


def _refuse(name):
    def refused(*_args, **_kwargs):
        raise ReaderRefused(f"{name} is not available in the Memory explorer")

    refused.__name__ = name
    return refused


def _init(self, db_path=None):
    if db_path is None or not str(db_path).strip():
        raise ReaderRefused("a store path is required")
    self.db_path = Path(str(db_path))


def _prefix_pattern(cls, value: str) -> str:
    # Upstream builds (?=.*(?:^|[^\w])term)... and runs re.search, which
    # retries every start position: quadratic on long memories. Anchored at
    # \A with DOTALL it is linear. Terms may sit on different lines.
    terms = cls._search_terms(value)
    if not terms:
        return r"a^"
    return r"(?s)\A" + "".join(rf"(?=.*?(?<!\w){re.escape(term)})" for term in terms)


def neutral_label(text) -> str:
    value = str(text or "")
    if _DENYLIST_RE.search(value):
        return "Assistant"
    return value


def apply(module) -> None:
    """Patch ``module`` (the vendored dashboard_core) in place, once."""
    if getattr(module, "_memdash_patched", False):
        return
    store = module.DashboardStore
    store.__init__ = _init
    store.connect = _connect
    for name in _WRITE_METHODS:
        setattr(store, name, _refuse(name))
    store._prefix_pattern = classmethod(_prefix_pattern)
    original_origin = store._pattern_origin_label

    def _origin_label(source, kind="memory"):
        return neutral_label(original_origin(source, kind))

    store._pattern_origin_label = staticmethod(_origin_label)
    from api.memdash_graph import install as install_graph
    install_graph(store)
    module.default_db_path = _refuse("default_db_path")
    module.plugin_data_dir = _refuse("plugin_data_dir")
    module._memdash_patched = True
