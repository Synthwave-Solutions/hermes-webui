"""Which left-navigation items a caller may see.

Reported 27 Aug 2026 ("Let administrators configure visible left-navigation
items by user group"): customers were shown menu items for features their
deployment or their permissions do not include, so every one of those was a
dead end.

Navigation is DERIVED from effective access rather than configured twice. Each
panel names the permission its own API already requires, so a group that is
not granted that permission simply does not get the menu item, and the item
cannot come back through a client-side setting. Two consequences worth stating:

* Enforcement does not live here. The APIs behind each panel are gated by the
  route catalog; this module only stops a user from walking into a wall.
* An administrator changes navigation the same way they change everything
  else: by granting or withholding the permission on the group. There is no
  second, drifting list of "visible tabs" per group.

``essential`` panels are never hidden: a user must always keep chat, their own
settings and the help surfaces, however narrow their grants.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# panel id (data-panel in static/index.html) -> permission its API requires.
PANEL_PERMISSIONS = {
    "tasks": "cron:read",
    "kanban": "kanban:read",
    # Projects hub (ticket 12): every aggregated section inside the payload
    # is re-gated by the permission its own route requires, so the panel
    # itself deliberately carries the widest of the set, which is also what
    # /api/projects and the hub route already need.
    "projects": "sessions:read",
    "skills": "skills:read",
    "memory": "memory:read",
    "workspaces": "files:read",
    "files": "files:read",
    "profiles": "profiles:read",
    "todos": "todos:read",
    "insights": "analytics:read",
    "logs": "logs:read",
    "governance": "governance:read",
    "integrations": "integrations:read",
}

# NOT listed above: "dashboard" is an external link out of the app, not a
# panel, so hiding it here would silently do nothing.

# Never hidden, whatever the grants: the user would otherwise lose the ability
# to work, to reach their own preferences, or to ask for help.
ESSENTIAL_PANELS = frozenset({"chat", "settings"})


def _permissions(access) -> frozenset:
    """The caller's effective permissions, or None when unreadable.

    None is distinct from the empty set on purpose: an empty set is a real
    narrow user (hide everything they cannot use), while an unreadable access
    object is our failure and must not lock a person out of their own
    navigation. Hiding is presentation; the APIs stay the real gate.
    """
    try:
        return frozenset(getattr(getattr(access, "grants", None), "permissions", None) or ())
    except Exception:
        logger.debug("nav permission read failed", exc_info=True)
        return None


def _has(permissions: frozenset, permission: str) -> bool:
    if "*" in permissions or permission in permissions:
        return True
    # A "<area>:admin" grant implies the area's read.
    return f"{permission.split(':', 1)[0]}:admin" in permissions


def hidden_panels(access, policy=None) -> list:
    """Panels the caller must not see, newest policy state included.

    Returns an empty list when governance is off or the caller holds a
    wildcard: nothing is hidden that the person could actually use.
    """
    try:
        if policy is not None and not getattr(policy, "enabled", True):
            return []
        if policy is not None and str(getattr(policy, "mode", "")) == "report_only":
            # report_only never enforces, here as everywhere else.
            return []
        permissions = _permissions(access)
        if permissions is None:
            return []
        hidden = []
        for panel, permission in PANEL_PERMISSIONS.items():
            if panel in ESSENTIAL_PANELS:
                continue
            if not _has(permissions, permission):
                hidden.append(panel)
        return sorted(hidden)
    except Exception:
        logger.debug("nav visibility resolution failed", exc_info=True)
        return []


def visible_panels(access, policy=None) -> list:
    """The complement of hidden_panels, for a preview of a group's navigation."""
    hidden = set(hidden_panels(access, policy))
    return sorted(
        [p for p in PANEL_PERMISSIONS if p not in hidden] + sorted(ESSENTIAL_PANELS)
    )
