"""Governance denial -> admin approvals bridge (kind "grant").

The agent-side tool gate spools every grantable governance denial into
``~/.hermes/webui/governance-grant-requests.json`` (see
hermes_cli.dashboard_governance.grant_requests). This module ingests that
spool into the api/approvals registry so denials show up in the admins'
governance screen as pending rows with the other self-service kinds, and it
applies an approved request to the governance policy document.

Ingest rules: a spool item becomes a pending registry row once; while the row
is pending its payload count/last_seen keeps tracking the spool. A decided
row (approved or rejected) is never re-created by ingest, so a rejection
stays quiet even when the user keeps hitting the denial.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SPOOL_NAME = "governance-grant-requests.json"


def _spool_path() -> Path:
    """Resolve the spool lazily from config.STATE_DIR so a test override never
    reads or writes the live admin queue."""
    from api import config

    return Path(config.STATE_DIR) / _SPOOL_NAME

# gkind -> (top-level grants section, nested path) applied on approval.
_GRANT_TARGETS = {
    "skill": ("skills", ("view", "load")),
    "cli": ("cli", ("commands",)),
    "workdir": ("cli", ("workdir_roots",)),
    "file_read": ("files", ("read_roots",)),
    "file_write": ("files", ("write_roots",)),
    "mcp": ("mcp", ("servers",)),
    "tool": ("tools", ("builtins",)),
    "toolset": ("tools", ("toolsets",)),
    "profile": ("profiles", ()),
    "workspace": ("workspaces", ()),
    # An API route the caller was blocked from. Approving adds the path to the
    # user's routes allowlist; the permission layer still applies, so a route
    # grant alone never confers an admin capability.
    "route": ("routes", ()),
    # A secret-bearing path a governed user was blocked from by a denied glob.
    # Approving adds the exact path to files.allow_globs, a per-person exception
    # that overrides denied_globs for that one path (see the engine tool_policy).
    "secret_glob": ("files", ("allow_globs",)),
}


def _load_spool() -> dict:
    try:
        data = json.loads(_spool_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def _request_label(item: dict) -> str:
    gkind = str(item.get("gkind") or "")
    value = str(item.get("value") or "")
    labels = {
        "cli": "CLI command",
        "skill": "Skill",
        "workdir": "CLI workdir",
        "file_read": "File read access",
        "file_write": "File write access",
        "mcp": "MCP server",
        "tool": "Tool",
        "toolset": "Toolset",
        "profile": "Profile",
        "workspace": "Workspace",
        "route": "API route",
        "secret_glob": "Secret file access",
    }
    return f"{labels.get(gkind, gkind)}: {value}"


def _route_is_requestable(path: str, method: str) -> bool:
    """A route denial is one-click-grantable only when it is not an admin or
    governance-mutation surface. Those stay hard-denied: a route grant adds the
    path to the caller's allowlist, and while the permission layer still guards
    the action, we do not even offer governance/admin routes in the queue."""
    try:
        from api.governance.catalog import route_permission
    except Exception:
        return False
    for m in ("GET", method.upper()):
        perm = route_permission(path, m) or ""
        if perm.startswith("governance:") or perm.endswith(":admin"):
            return False
    return True


def record_route_denial(email: str, path: str, method: str = "GET") -> bool:
    """Spool a route_not_allowed denial as a grantable request (kind route).

    Route denials happen at the HTTP layer, not the agent tool layer, so the
    engine's tool-denial spool never sees them; this is the webui-side writer.
    Writes the same spool the engine uses, so ingest_spool turns it into a
    pending Access row. Best-effort, never raises, admin routes excluded."""
    try:
        email = str(email or "").strip().lower()
        path = (str(path or "").split("?", 1)[0]).strip()
        if not email or not path or not path.startswith("/api/"):
            return False
        if not _route_is_requestable(path, method):
            return False
        key = f"{email}|route|{path}"
        now = time.time()
        spool_file = _spool_path()
        spool_file.parent.mkdir(parents=True, exist_ok=True)
        lock_path = spool_file.with_suffix(".lock")
        with open(lock_path, "w") as lock_fh:
            try:
                import fcntl
                fcntl.flock(lock_fh, fcntl.LOCK_EX)
            except Exception:
                pass
            spool = _load_spool()
            entry = spool.get(key)
            if isinstance(entry, dict):
                entry["count"] = int(entry.get("count") or 0) + 1
                entry["last_seen"] = now
            else:
                spool[key] = {
                    "email": email, "gkind": "route", "value": path,
                    "tool": "", "reason": "route_not_allowed", "detail": path,
                    "count": 1, "first_seen": now, "last_seen": now,
                }
            tmp = spool_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(spool, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(spool_file)
        return True
    except Exception as exc:  # pragma: no cover
        logger.debug("route denial spool failed: %s", exc)
        return False


def ingest_spool() -> int:
    """Sync the denial spool into the approvals registry. Returns how many
    pending grant rows exist afterwards. Never raises."""
    try:
        from api import approvals

        spool = _load_spool()
        pending = 0
        for skey, item in spool.items():
            if not isinstance(item, dict):
                continue
            email = str(item.get("email") or "").strip().lower()
            gkind = str(item.get("gkind") or "")
            value = str(item.get("value") or "")
            if not email or gkind not in _GRANT_TARGETS or not value:
                continue
            rk = f"{approvals.KIND_GRANT}:{skey}"
            with approvals._REGISTRY_LOCK:
                registry = approvals.load()
                entry = registry.get(rk)
                payload = {
                    "email": email,
                    "gkind": gkind,
                    "value": value,
                    "reason": str(item.get("reason") or ""),
                    "tool": str(item.get("tool") or ""),
                    "detail": str(item.get("detail") or ""),
                    "count": int(item.get("count") or 1),
                }
                if entry is None:
                    registry[rk] = {
                        "kind": approvals.KIND_GRANT,
                        "key": skey,
                        "label": _request_label(item),
                        "owner_email": email,
                        "status": "pending",
                        "requested_at": float(item.get("first_seen") or 0.0),
                        "payload": payload,
                    }
                    approvals.save(registry)
                    pending += 1
                elif str(entry.get("status") or "pending") == "pending":
                    entry["payload"] = payload
                    approvals.save(registry)
                    pending += 1
        return pending
    except Exception as exc:  # pragma: no cover: queue must render regardless
        logger.debug("grant request ingest failed: %s", exc)
        return 0


def drop_from_spool(spool_key: str) -> None:
    """Remove one decided item from the spool (best-effort)."""
    try:
        spool = _load_spool()
        if spool_key in spool:
            spool.pop(spool_key)
            spool_file = _spool_path()
            tmp = spool_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(spool, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, spool_file)
    except Exception as exc:
        logger.debug("grant request spool drop failed: %s", exc)


def apply_grant_to_policy(raw: dict, payload: dict) -> tuple[str, str] | None:
    """Apply an approved grant request to the raw policy document in place.

    Returns (before, after) audit strings, or None when the payload does not
    describe an applicable grant. The grant lands on the USER entry (never a
    group or role), so approving a request widens exactly one person.
    """
    email = str(payload.get("email") or "").strip().lower()
    gkind = str(payload.get("gkind") or "")
    value = str(payload.get("value") or "")
    target = _GRANT_TARGETS.get(gkind)
    if not email or not value or target is None:
        return None
    section, subkeys = target
    users = raw.setdefault("users", {})
    user = users.get(email)
    if user is None:
        # Only grant to users the policy already knows; an unknown email is
        # an ingest artefact, not a reason to create a policy entry.
        return None
    grants = user.setdefault("grants", {})
    added = []
    if not subkeys:
        lst = grants.setdefault(section, [])
        if value not in lst:
            lst.append(value)
            added.append(f"{section}+{value}")
    else:
        sec = grants.setdefault(section, {})
        for sub in subkeys:
            lst = sec.setdefault(sub, [])
            if value not in lst:
                lst.append(value)
                added.append(f"{section}.{sub}+{value}")
        # An MCP server grant is useless without a tool allowance.
        if gkind == "mcp":
            tools = sec.setdefault("tools", {})
            names = tools.setdefault(value, [])
            if "*" not in names:
                names.append("*")
                added.append(f"{section}.tools.{value}+*")
    before = "absent"
    after = ", ".join(added) if added else "already granted"
    return before, after
