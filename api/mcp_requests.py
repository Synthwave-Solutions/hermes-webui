"""Self-service MCP server requests and admin-approved installation.

Adding an MCP server is an RCE-grade action: today PUT /api/mcp/servers/{name}
writes straight into the active profile's ``config.yaml`` and is only kept
away from non-admins by the governance ``mcp:write`` permission. This module
adds the missing middle step so a normal user can ASK for a server without
being able to install one:

    user  -> request_server(...)        approvals registry, status "pending"
    admin -> governance approvals queue -> approve
    then  -> sync_approved()            writes the entry into config.yaml

The registry entry is inert: nothing is written to config.yaml until the
approval flips to ``approved``. Only remote (http/https) servers can be
requested; ``command``/``args``/``env`` stdio servers stay admin-only,
because a stdio entry is a literal shell command.

Secrets never enter the registry. A request may name the auth header it
needs (``Authorization``, ``X-Api-Key``, ...) but never its value: the
installed entry gets an EMPTY header placeholder and is written with
``enabled: false``, so the admin fills the real value through the existing
PUT (which has the masked-value preservation) and then enables it. Requests
without an auth header install enabled and become active on the next reload.

House style: pure logic, no HTTP handler code. Functions raise ValueError
(-> 400), PermissionError (-> 403) and KeyError (-> 404); api/routes.py
translates them into responses.
"""
from __future__ import annotations

import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)

# Server names end up as YAML mapping keys and as the approvals registry key,
# so keep them boring: no path separators, no control characters, no colon
# (the registry uses "<kind>:<key>").
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
# RFC 7230 token characters, minus the exotic ones nobody uses in practice.
_HEADER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_MAX_URL_LEN = 2048
_MAX_DESCRIPTION_LEN = 500

# Keys a caller must NOT send: they either carry a secret or turn the request
# into a stdio (command) install. Rejected loudly instead of ignored so the
# UI cannot believe it submitted an authenticated server.
_REJECTED_BODY_KEYS = ("headers", "header_value", "auth_value", "token", "secret", "env", "command", "args")

STATUS_PENDING_APPROVAL = "pending_approval"
STATUS_ACTIVE = "active"

_AUDIT_EVENT = "mcp_server_install"
_AUDIT_UNINSTALL_EVENT = "mcp_server_uninstall"


# ── Normalisation ────────────────────────────────────────────────────────────

def normalize_name(name) -> str:
    """Validate an MCP server name. Raises ValueError when unusable."""
    value = str(name or "").strip()
    if not value:
        raise ValueError("name is required")
    if not _NAME_RE.match(value):
        raise ValueError(
            "name may only contain letters, digits, spaces, '.', '_' and '-' (max 64 chars)"
        )
    return value


def normalize_url(url) -> str:
    """Validate a remote MCP server URL (http/https only)."""
    value = str(url or "").strip()
    if not value:
        raise ValueError("url is required")
    if len(value) > _MAX_URL_LEN:
        raise ValueError("url is too long")
    parts = urllib.parse.urlsplit(value)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("url must be http(s)")
    if not parts.netloc:
        raise ValueError("url must include a host")
    return value


def normalize_auth_header(header) -> str | None:
    """Validate an auth header NAME (never a value). None when not needed."""
    value = str(header or "").strip()
    if not value:
        return None
    if not _HEADER_RE.match(value):
        raise ValueError("auth_header must be a plain header name, e.g. 'Authorization'")
    return value


def reject_secret_fields(body) -> None:
    """Raise when a request body carries a secret or a stdio command.

    The registry is readable by admins in the approvals queue and lands in a
    plain JSON sidecar, so a request may describe WHICH header is needed but
    never its value; and a stdio server (command/args/env) is not requestable
    at all.
    """
    if not isinstance(body, dict):
        return
    for key in _REJECTED_BODY_KEYS:
        if body.get(key):
            raise ValueError(
                f"'{key}' cannot be part of a request: only a remote url and an "
                "auth header name are stored; secrets are set by an admin after approval"
            )


def _active_profile_name() -> str:
    """Best-effort name of the profile whose config.yaml an install targets."""
    try:
        from api.profiles import get_active_profile_name

        return str(get_active_profile_name() or "")
    except Exception:
        logger.debug("Failed to resolve active profile name for MCP request", exc_info=True)
        return ""


# ── Requesting ───────────────────────────────────────────────────────────────

def build_payload(url, auth_header=None, description=None) -> dict:
    """The approvals payload for an MCP request (never contains a secret)."""
    payload = {
        "transport": "http",
        "url": normalize_url(url),
        "auth_header": normalize_auth_header(auth_header),
        "profile": _active_profile_name(),
    }
    note = str(description or "").strip()
    if note:
        payload["description"] = note[:_MAX_DESCRIPTION_LEN]
    return payload


def request_server(
    owner_email, name, url, auth_header=None, description=None, *, is_admin=False
) -> dict:
    """Record a pending request for a remote MCP server; returns the entry.

    Idempotent through api.approvals.request: re-requesting a pending server
    returns the stored entry, and requesting an already decided one is a
    no-op that returns the decision. Nothing is written to config.yaml here.

    Name squatting: an MCP server name is the only thing an admin reads in the
    approvals queue, so if the name is already taken by a request pointing at
    a different URL, api.approvals raises PayloadConflict and the route answers
    409. An admin passes ``is_admin=True`` to take the name over, which
    replaces the payload and re-records the row under the admin.
    """
    from api import approvals

    owner = str(owner_email or "").strip().lower()
    if not owner:
        raise PermissionError("authentication required to request an MCP server")
    key = normalize_name(name)
    payload = build_payload(url, auth_header, description)
    return approvals.request(
        approvals.KIND_MCP, key, owner, label=key, payload=payload, force=bool(is_admin)
    )


def get_request(name) -> dict | None:
    """The registry entry for an MCP server request, or None."""
    from api import approvals

    return approvals.get(approvals.KIND_MCP, str(name or "").strip())


def list_requests(owner_scope=None) -> list:
    """MCP requests visible to ``owner_scope`` ('all' or an email), oldest first."""
    from api import approvals

    return approvals.list_all(kinds=approvals.KIND_MCP, owner_scope=owner_scope)


# ── Installation of approved requests ────────────────────────────────────────

def server_config_from_entry(entry) -> tuple[dict, bool]:
    """Build the config.yaml server block for an approved entry.

    Returns ``(server_cfg, needs_secret)``. When the request named an auth
    header the block carries an EMPTY placeholder for it and is written
    disabled, because sending an empty Authorization header to a remote
    server is worse than not connecting at all: the admin sets the real value
    with the existing PUT /api/mcp/servers/{name} and flips it on.
    """
    payload = entry.get("payload") if isinstance(entry, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    cfg: dict = {"url": normalize_url(payload.get("url"))}
    auth_header = normalize_auth_header(payload.get("auth_header"))
    needs_secret = bool(auth_header)
    if auth_header:
        cfg["headers"] = {auth_header: ""}
        cfg["enabled"] = False
    return cfg, needs_secret


def _audit_install(row: dict, decided_by: str | None, *, path: str, event: str = _AUDIT_EVENT) -> None:
    """Audit one install; a broken audit sink never undoes the install."""
    try:
        from api.governance.audit import append_audit_event

        append_audit_event(
            event,
            subject_email=str(decided_by or ""),
            path=path,
            method="POST",
            reason="approvals.install",
            extra={
                "op": row.get("op") or "mcp.install_approved",
                "target": row.get("name"),
                "key": "mcp:" + str(row.get("name") or ""),
                "owner": row.get("owner_email") or "",
                "profile": row.get("profile") or "",
                "enabled": row.get("enabled"),
                "needs_secret": row.get("needs_secret"),
            },
        )
    except Exception:
        logger.debug("MCP install audit failed", exc_info=True)


def sync_approved(decided_by=None, *, path: str = "/api/mcp/servers/sync-approved") -> dict:
    """Write every approved-but-not-yet-installed MCP request into config.yaml.

    Idempotent and safe to call from any code path: a server name that
    already exists in the config is left completely alone (an admin's own
    entry is never overwritten), and the config file is only rewritten when
    something actually changed. Each install appends a governance audit line.
    """
    from api import approvals
    from api.config import (
        _get_config_path,
        _save_yaml_config_file,
        get_config,
        reload_config,
    )

    result: dict = {"installed": [], "skipped": [], "changed": False}
    try:
        rows = [
            entry
            for entry in approvals.list_all(kinds=approvals.KIND_MCP)
            if str(entry.get("status") or "") == approvals.STATUS_APPROVED
        ]
    except Exception:
        logger.debug("Failed to read approved MCP requests", exc_info=True)
        return result
    if not rows:
        return result

    cfg = get_config()
    servers = cfg.get("mcp_servers", {})
    if not isinstance(servers, dict):
        servers = {}
    for entry in rows:
        name = str(entry.get("key") or "").strip()
        if not name:
            continue
        if name in servers:
            result["skipped"].append({"name": name, "reason": "already_configured"})
            continue
        try:
            server_cfg, needs_secret = server_config_from_entry(entry)
        except ValueError as exc:
            # A malformed payload must never block the other installs.
            result["skipped"].append(
                {"name": name, "reason": "invalid_request", "message": str(exc)}
            )
            continue
        servers[name] = server_cfg
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        result["installed"].append({
            "name": name,
            "url": server_cfg.get("url"),
            "enabled": bool(server_cfg.get("enabled", True)),
            "needs_secret": needs_secret,
            "owner_email": entry.get("owner_email"),
            "profile": payload.get("profile") or "",
        })
    if not result["installed"]:
        return result

    cfg["mcp_servers"] = servers
    _save_yaml_config_file(_get_config_path(), cfg)
    reload_config()
    result["changed"] = True
    for row in result["installed"]:
        _audit_install(row, decided_by, path=path)
    return result


def sync_approved_quietly(decided_by=None, *, path: str = "/api/mcp/servers") -> dict:
    """sync_approved() that can never raise into a request handler."""
    try:
        return sync_approved(decided_by, path=path)
    except Exception:
        logger.warning("Approved MCP servers could not be installed", exc_info=True)
        return {"installed": [], "skipped": [], "changed": False}


def uninstall(name, decided_by=None, *, path: str = "/api/governance/approvals/decide") -> bool:
    """Remove a self-service installed MCP server from config.yaml.

    Called when an admin REJECTS a request that was already approved and
    installed. Without it, "rejected" only blocks FUTURE installs while the
    live server keeps running: an approved-then-rejected item has to become
    unusable again, not merely unrequestable.

    Never touches a server an admin configured directly: the entry is only
    removed when the approvals registry knows the name AND the configured
    ``url`` is still the one that was approved, so an admin who re-pointed or
    re-created the server by hand owns it from then on.
    """
    from api import approvals
    from api.config import (
        _get_config_path,
        _save_yaml_config_file,
        get_config,
        reload_config,
    )

    key = str(name or "").strip()
    if not key:
        return False
    entry = approvals.get(approvals.KIND_MCP, key)
    if not isinstance(entry, dict):
        return False
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    approved_url = str(payload.get("url") or "").strip()
    cfg = get_config()
    servers = cfg.get("mcp_servers", {})
    if not isinstance(servers, dict) or key not in servers:
        return False
    current = servers.get(key)
    current_url = str(current.get("url") or "").strip() if isinstance(current, dict) else ""
    if not approved_url or current_url != approved_url:
        return False
    del servers[key]
    cfg["mcp_servers"] = servers
    _save_yaml_config_file(_get_config_path(), cfg)
    reload_config()
    _audit_install(
        {
            "op": "mcp.uninstall_rejected",
            "name": key,
            "owner_email": entry.get("owner_email"),
            "profile": payload.get("profile") or "",
            "enabled": False,
            "needs_secret": bool(payload.get("auth_header")),
        },
        decided_by,
        path=path,
        event=_AUDIT_UNINSTALL_EVENT,
    )
    return True


def uninstall_quietly(name, decided_by=None, *, path: str = "/api/governance/approvals/decide") -> bool:
    """uninstall() that can never raise into a request handler."""
    try:
        return uninstall(name, decided_by, path=path)
    except Exception:
        logger.warning("Rejected MCP server %r could not be uninstalled", name, exc_info=True)
        return False


def forget(name) -> bool:
    """Drop the approval entry for a server name; False when there was none.

    Called when an admin deletes an installed server: without this the
    approval would still say "approved" and the next sync_approved() would
    resurrect the entry the admin just removed. Never raises.
    """
    from api import approvals

    try:
        return approvals.remove(approvals.KIND_MCP, str(name or "").strip())
    except Exception:
        logger.debug("Failed to drop MCP approval for %r", name, exc_info=True)
        return False


def install_state(name) -> str:
    """'installed' | 'not_installed' for an MCP server name (config lookup)."""
    try:
        from api.config import get_config

        servers = get_config().get("mcp_servers", {})
    except Exception:
        return "not_installed"
    if isinstance(servers, dict) and str(name or "").strip() in servers:
        return "installed"
    return "not_installed"
