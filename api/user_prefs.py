"""Per-person presentation and run preferences (not shared with colleagues).

Today: the thinking level ("reasoning effort") picked in the composer. It used
to be written into the bot's config.yaml, so one person's choice changed it for
everyone using that bot. A signed-in person's pick is now stored here, keyed by
profile, and used for their own turns; the bot's config.yaml value stays the
admin-set default for people who never picked one.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path

_LOCK = threading.Lock()


def _dir() -> Path:
    from api.config import STATE_DIR
    return Path(STATE_DIR) / "user_prefs"


def _file(email: str) -> Path:
    slug = re.sub(r"[^a-z0-9._@+-]", "_", str(email).strip().lower())[:160] or "unknown"
    return _dir() / f"{slug}.json"


def _load(email: str) -> dict:
    try:
        data = json.loads(_file(email).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save(email: str, data: dict) -> None:
    path = _file(email)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".prefs-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _profile_key(profile) -> str:
    return str(profile or "default").strip() or "default"


def get_reasoning_effort(email, profile) -> str | None:
    """The person's own effort for this bot, or None when they never picked."""
    if not email:
        return None
    value = (_load(email).get("reasoning_effort") or {}).get(_profile_key(profile))
    return value if isinstance(value, str) else None


def set_reasoning_effort(email, profile, effort: str) -> None:
    """Store ('' clears) the person's own effort for this bot."""
    if not email:
        raise ValueError("signed-in person required")
    with _LOCK:
        data = _load(email)
        per = dict(data.get("reasoning_effort") or {})
        if effort:
            per[_profile_key(profile)] = effort
        else:
            per.pop(_profile_key(profile), None)
        data["reasoning_effort"] = per
        _save(email, data)



def get_workspace_order(email, profile) -> list:
    if not email:
        return []
    value = (_load(email).get("workspace_order") or {}).get(_profile_key(profile))
    return [str(p) for p in value] if isinstance(value, list) else []


def set_workspace_order(email, profile, paths) -> None:
    if not email:
        raise ValueError("signed-in person required")
    clean = []
    for p in paths or []:
        p = str(p or "").strip()
        if p and p not in clean:
            clean.append(p)
    with _LOCK:
        data = _load(email)
        per = dict(data.get("workspace_order") or {})
        per[_profile_key(profile)] = clean[:500]
        data["workspace_order"] = per
        _save(email, data)


def apply_order(rows, order) -> list:
    """Rows sorted by a personal order; unknown rows keep their default order after."""
    if not order:
        return list(rows)
    rank = {p: i for i, p in enumerate(order)}
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda t: (rank.get(t[1].get("path"), len(rank) + t[0])))
    return [r for _, r in indexed]
