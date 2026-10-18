"""Project operational delegation events into UI-only activity rows.

Besides the per-stream worklog projection (``remember``), this module keeps a
small per-conversation record of delegated workers (``record`` / ``snapshot``).
Top-level delegations run in the background, so workers usually keep going
after the parent turn has finished and its event stream has closed. Without a
record that outlives the stream, their later progress and completion never
reach the browser, which is why worker activity disappeared from the chat.

Only operational state is kept: status, the short assigned-work label that the
engine already sanitises, counters, timestamps and the NAMES of the tools a
worker used. Tool arguments, previews and model reasoning are never stored.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

_TERMINAL = {"completed", "failed", "cancelled"}
_RANK = {"queued": 0, "running": 1, "completed": 2, "failed": 2, "cancelled": 2}
_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_TOOL_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
_MAX_SESSIONS = 200
_MAX_WORKERS = 32
_MAX_STEPS = 40
_PERSIST_INTERVAL = 2.0

_lock = threading.Lock()
_threads: "OrderedDict[str, OrderedDict[str, dict]]" = OrderedDict()
_last_persist: dict[str, float] = {}


def normalize(event, payload):
    try:
        from tools.delegation_progress import normalize_subagent_progress
    except ImportError:
        return None  # Older engine: optional capability, not a chat failure.
    return normalize_subagent_progress(event, payload)


def remember(rows, data):
    """Update the existing UI fallback projection, never engine message context."""
    tid = "subagent:" + data["id"]
    for row in rows:
        if row.get("tid") == tid:
            target = row
            if target.get("done") and data["status"] in {"queued", "running"}:
                return
            break
    else:
        target = {"name": "subagent_progress", "tid": tid}
        rows.append(target)
    target.update({
        "args": {k: data.get(k) for k in ("status", "task_index", "task_count", "tool_count")},
        "preview": data["summary"], "done": data["status"] in {"completed", "failed", "cancelled"},
        "is_error": data["status"] == "failed",
    })
    target["args"]["task"] = data["summary"]


# ── Conversation-scoped worker threads ─────────────────────────────────────

def _store_dir() -> Path | None:
    try:
        from api.config import STATE_DIR
    except Exception:
        return None
    return Path(STATE_DIR) / "subagent_threads"


def _int(value, cap=100000):
    return max(0, min(cap, value)) if type(value) is int else 0


def _clean_tool(name) -> str:
    text = str(name or "").strip()
    return text if _TOOL_RE.match(text) and not text.startswith("_") else ""


def record(session_id, data, tool_name=None, now=None):
    """Fold one normalized worker event into the conversation record.

    ``tool_name`` is the child tool that produced the event (only its name is
    kept). Returns the updated worker dict, or None when the event is ignored.
    """
    if not isinstance(data, dict) or not _SID_RE.match(str(session_id or "")):
        return None
    wid = str(data.get("id") or "")
    status = str(data.get("status") or "")
    if not _ID_RE.match(wid) or status not in _RANK:
        return None
    now = float(now if now is not None else time.time())
    with _lock:
        workers = _threads.get(session_id)
        if workers is None:
            workers = _load_locked(session_id)
        _threads[session_id] = workers
        _threads.move_to_end(session_id)
        while len(_threads) > _MAX_SESSIONS:
            _threads.popitem(last=False)
        prior = workers.get(wid)
        if prior is None:
            if len(workers) >= _MAX_WORKERS:
                workers.popitem(last=False)
            prior = {"id": wid, "status": status, "started_at": now, "steps": []}
            workers[wid] = prior
        elif prior["status"] in _TERMINAL or _RANK[prior["status"]] > _RANK[status]:
            return None
        changed_status = prior.get("status") != status or prior.get("updated_at") is None
        prior["status"] = status
        summary = " ".join(str(data.get("summary") or "").split())[:120]
        if summary:
            prior["task"] = summary
        for key in ("task_index", "task_count"):
            if key in data:
                prior[key] = _int(data.get(key), 1000)
        prior["tool_count"] = max(_int(data.get("tool_count")), int(prior.get("tool_count") or 0))
        duration = data.get("duration_seconds")
        if type(duration) in (int, float) and duration >= 0 and duration == duration:
            prior["duration_seconds"] = float(duration)
        elif status in _TERMINAL and "duration_seconds" not in prior:
            prior["duration_seconds"] = max(0.0, now - float(prior.get("started_at") or now))
        tool = _clean_tool(tool_name)
        if tool and status == "running":
            steps = prior.setdefault("steps", [])
            steps.append({"tool": tool, "at": round(now, 3)})
            if len(steps) > _MAX_STEPS:
                del steps[: len(steps) - _MAX_STEPS]
                prior["steps_truncated"] = True
        prior["updated_at"] = now
        result = dict(prior, steps=list(prior.get("steps") or []))
        if changed_status or now - _last_persist.get(session_id, 0) >= _PERSIST_INTERVAL:
            _last_persist[session_id] = now
            _persist_locked(session_id, workers)
    return result


def snapshot(session_id):
    """Workers of one conversation, oldest first (copies, safe to serialise)."""
    if not _SID_RE.match(str(session_id or "")):
        return []
    with _lock:
        workers = _threads.get(session_id)
        if workers is None:
            workers = _load_locked(session_id)
            if workers:
                _threads[session_id] = workers
        return [dict(w, steps=list(w.get("steps") or [])) for w in workers.values()]


def seed_from_rows(rows):
    """Rebuild workers from persisted worklog rows (older conversations).

    Used only when no record exists, e.g. for conversations from before this
    record existed. Nothing is written to disk.
    """
    workers: "OrderedDict[str, dict]" = OrderedDict()
    for row in rows or []:
        tool = row.get("tool") if isinstance(row, dict) else None
        if not isinstance(tool, dict) or tool.get("name") != "subagent_progress":
            continue
        tid = str(tool.get("id") or row.get("tool_call_id") or "")
        wid = tid[9:] if tid.startswith("subagent:") else ""
        args = tool.get("args") if isinstance(tool.get("args"), dict) else {}
        status = str(args.get("status") or "")
        if not _ID_RE.match(wid) or status not in _RANK:
            continue
        prior = workers.get(wid)
        if prior and _RANK[prior["status"]] > _RANK[status]:
            continue
        created = row.get("created_at") if type(row.get("created_at")) in (int, float) else None
        workers[wid] = {
            "id": wid, "status": status, "task": " ".join(str(args.get("task") or "").split())[:120],
            "task_index": _int(args.get("task_index"), 1000), "task_count": _int(args.get("task_count"), 1000),
            "tool_count": _int(args.get("tool_count")), "started_at": created, "updated_at": created,
            "steps": [], "restored": True,
        }
        if type(tool.get("duration")) in (int, float):
            workers[wid]["duration_seconds"] = float(tool["duration"])
    return list(workers.values())


def _path(session_id) -> Path | None:
    base = _store_dir()
    return base / f"{session_id}.json" if base else None


def _load_locked(session_id) -> "OrderedDict[str, dict]":
    workers: "OrderedDict[str, dict]" = OrderedDict()
    path = _path(session_id)
    if not path or not path.exists():
        return workers
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return workers
    for item in raw.get("workers", []) if isinstance(raw, dict) else []:
        if isinstance(item, dict) and _ID_RE.match(str(item.get("id") or "")) and item.get("status") in _RANK:
            workers[item["id"]] = item
    return workers


def _persist_locked(session_id, workers) -> None:
    path = _path(session_id)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": 1, "workers": list(workers.values())}), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass  # Display-only state: losing it must never break a chat turn.


def _reset_for_tests() -> None:
    with _lock:
        _threads.clear()
        _last_persist.clear()
