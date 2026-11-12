"""Reuse a parsed ``profile.yaml`` while the file on disk is unchanged.

Every chat turn builds the bot team directory, and that read each profile's
``profile.yaml`` about three times (the access check, the public card, the
managed settings): roughly 150 YAML parses and 2 MB of text per turn for 54
profiles (measured 12 Nov 2026: 0.6 s median inside a busy server).

``load(path, loader)`` returns what ``loader(path)`` returns and keeps the
result for as long as the file's identity is the same: device, inode, size,
modification time and change time. Any write, in place or by replacement,
changes at least one of those. A file touched in the last two seconds is never
kept, so two writes inside one timestamp tick cannot leave a stale entry.
Errors are never kept: a missing, unreadable, symlinked or invalid file goes
through ``loader`` on every call, exactly as before.

The returned object is shared between callers. Treat it as read only and copy
whatever is handed on or changed.
"""
from __future__ import annotations

import os
import stat
import threading
import time

_LOCK = threading.Lock()
_ENTRIES: dict = {}
_MAX_ENTRIES = 512
_RACY_NS = 2_000_000_000


def _signature(path):
    try:
        info = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def load(path, loader):
    """``loader(path)``, served from memory while the file is unchanged."""
    before = _signature(path)
    if before is None:
        return loader(path)
    key = (os.fspath(path), loader)
    with _LOCK:
        entry = _ENTRIES.get(key)
    if entry is not None and entry[0] == before:
        return entry[1]
    value = loader(path)
    settled = time.time_ns() - max(before[3], before[4]) > _RACY_NS
    if settled and _signature(path) == before:
        with _LOCK:
            if len(_ENTRIES) >= _MAX_ENTRIES and key not in _ENTRIES:
                _ENTRIES.clear()
            _ENTRIES[key] = (before, value)
    return value


def clear():
    with _LOCK:
        _ENTRIES.clear()
