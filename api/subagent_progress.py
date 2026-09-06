"""Project operational delegation events into UI-only activity rows."""
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
