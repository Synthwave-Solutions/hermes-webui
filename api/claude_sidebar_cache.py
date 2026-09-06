"""Disposable, private sidebar metadata; original JSONL remains authoritative."""
import json
import math
import os
import tempfile
from pathlib import Path

VERSION = 1
MAX_BYTES = 2 * 1024 * 1024

def signature(path, max_messages):
    stat = path.stat()
    return [stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns, max_messages]

def load(path):
    try:
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            return {}
        data = json.loads(path.read_text())
        entries = data.get("entries", {})
        if data.get("version") != VERSION or not isinstance(entries, dict) or len(entries) > 1000:
            return {}
        return entries
    except (OSError, ValueError, AttributeError):
        return {}

def metadata(path, entries, *, parse, title, max_messages):
    key = str(path.resolve())
    try:
        stamp = signature(path, max_messages)
    except OSError:
        return None, None
    cached = entries.get(key)
    if isinstance(cached, dict) and cached.get("signature") == stamp:
        row = cached.get("row")
        if (isinstance(row, dict) and set(row) == {"title", "message_count", "first_ts", "last_ts"}
                and isinstance(row.get("title"), str)
                and len(row["title"]) <= 80
                and type(row.get("message_count")) is int
                and 0 <= row["message_count"] <= max_messages
                and all(v is None or (type(v) in (int, float) and math.isfinite(v))
                        for v in (row.get("first_ts"), row.get("last_ts")))):
            return dict(row), cached
    messages, summary, first, last = parse(path, max_messages=max_messages)
    row = {"title": title(messages, summary), "message_count": len(messages),
           "first_ts": first, "last_ts": last}
    # Never stamp a parse as fresh if the source changed while being read.
    try:
        if signature(path, max_messages) != stamp:
            return row, None
    except OSError:
        return row, None
    return row, {"signature": stamp, "row": row}

def save(path, entries):
    """Atomic replacement with mode 0600; cache failures never fail listing."""
    blob = json.dumps({"version": VERSION, "entries": entries}, ensure_ascii=False)
    if len(blob.encode("utf-8")) > MAX_BYTES:
        return
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            return
        fd, temporary = tempfile.mkstemp(prefix=".claude-sidebar-", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(blob)
        os.replace(temporary, path)
    except OSError:
        pass
    finally:
        if temporary:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
