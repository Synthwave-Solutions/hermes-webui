"""Sidecar ownership registry for user-added skills.

Implements the skills ownership model from docs/user-isolation-design.md
(section 6): skills created via /api/skills/save by a non-admin are written to
disk as usual and registered here as ``pending``, owned by the creator's
identity email. Pending skills are visible and usable only to their owner and
to admins. Approving a skill (status ``approved``) makes it global for
everyone while keeping the added_by annotation; rejecting deletes the skill
directory and removes the registry entry.

The registry lives at STATE_DIR/skill_ownership.json and maps a stable skill
key (``category/name`` for categorized skills, bare ``name`` for flat skills;
both are the on-disk directory names) to::

    {"owner_email": "user@example.com", "added_at": <epoch>, "status": "pending"}

Skills with no registry entry are global (pre-existing/admin-managed skills).
Writes are atomic (same-directory temp file + os.replace) and serialized under
a module lock, matching the other STATE_DIR sidecar files.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"

_REGISTRY_LOCK = threading.Lock()


def _registry_file() -> Path:
    """Resolve the registry path lazily so test STATE_DIR overrides apply."""
    from api import config

    return Path(config.STATE_DIR) / "skill_ownership.json"


def skill_key(name, category=None) -> str:
    """Return the stable registry key for a skill.

    ``name`` and ``category`` are the on-disk directory names (the same
    identity /api/skills/save and /api/skills/delete operate on):
    ``category/name`` when the skill lives under a category directory,
    otherwise the bare ``name``.
    """
    name = str(name or "").strip()
    category = str(category or "").strip()
    if category:
        return f"{category}/{name}"
    return name


def load() -> dict:
    """Load the full registry as {key: entry}. Returns {} on any failure."""
    path = _registry_file()
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Failed to load skill ownership registry", exc_info=True)
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def save(registry: dict) -> None:
    """Persist the registry with an atomic same-directory replace."""
    path = _registry_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get(key) -> dict | None:
    """Return the registry entry for ``key``, or None when unregistered."""
    if not key:
        return None
    return load().get(str(key))


def owner_of(key) -> str | None:
    """Return the lowercased owner email for ``key``, or None."""
    entry = get(key)
    if not entry:
        return None
    owner = str(entry.get("owner_email") or "").strip().lower()
    return owner or None


def register_skill(key, owner_email) -> dict:
    """Register ``key`` as a pending skill owned by ``owner_email``.

    Idempotent: an existing entry is returned unchanged so re-saving a skill
    never resets its status or reassigns its owner.
    """
    key = str(key or "").strip()
    if not key:
        raise ValueError("skill key required")
    owner = str(owner_email or "").strip().lower()
    if not owner:
        raise ValueError("owner_email required")
    with _REGISTRY_LOCK:
        registry = load()
        existing = registry.get(key)
        if existing is not None:
            return existing
        entry = {
            "owner_email": owner,
            "added_at": time.time(),
            "status": STATUS_PENDING,
        }
        registry[key] = entry
        save(registry)
        return entry


def set_status(key, status) -> bool:
    """Set the status of an existing entry. Returns False when key is absent."""
    if status not in (STATUS_PENDING, STATUS_APPROVED):
        raise ValueError(f"invalid skill ownership status: {status!r}")
    with _REGISTRY_LOCK:
        registry = load()
        entry = registry.get(str(key or ""))
        if entry is None:
            return False
        entry["status"] = status
        save(registry)
        return True


def remove(key) -> bool:
    """Delete the entry for ``key``. Returns False when key is absent."""
    with _REGISTRY_LOCK:
        registry = load()
        if str(key or "") not in registry:
            return False
        del registry[str(key)]
        save(registry)
        return True


def list_pending() -> list:
    """Return pending entries as [{key, owner_email, added_at, status}, ...].

    Sorted oldest-first so the stage-3 approvals API can render a stable
    queue.
    """
    rows = []
    for key, entry in load().items():
        if str(entry.get("status") or "") != STATUS_PENDING:
            continue
        rows.append(
            {
                "key": key,
                "owner_email": str(entry.get("owner_email") or "").strip().lower() or None,
                "added_at": entry.get("added_at"),
                "status": STATUS_PENDING,
            }
        )
    rows.sort(key=lambda r: (r["added_at"] is None, r["added_at"] or 0, r["key"]))
    return rows


def entry_visible_to_scope(entry, owner_scope) -> bool:
    """Return whether a skill with registry ``entry`` is visible to a scope.

    ``owner_scope`` follows api.ownership.request_owner_scope: 'all' for
    admins / identity-less requests / isolation off, otherwise the requester's
    lowercased email (possibly empty for an identity without an email).
    Unregistered skills (entry None) and approved skills are global; pending
    skills are visible only to admins and their owner.
    """
    if entry is None:
        return True
    if owner_scope == "all":
        return True
    if str(entry.get("status") or "") == STATUS_APPROVED:
        return True
    owner = str(entry.get("owner_email") or "").strip().lower()
    return bool(owner_scope) and owner == str(owner_scope)
