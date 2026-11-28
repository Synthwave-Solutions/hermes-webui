"""Per-person connector selection within a conversation. Accounts stay with their provider."""
import re
import sqlite3
import subprocess
from collections import defaultdict
from contextlib import closing

from api import personal_context, chat_connection_inventory

_SOURCES = ("hosted", "nango")
_CREATE = "CREATE TABLE IF NOT EXISTS disabled (session TEXT, connector TEXT, PRIMARY KEY(session, connector))"


def disabled(identity, sid):
    if not sid:
        return set()
    db = personal_context._safe(personal_context.home(identity) / "chat-connectors.sqlite3")
    if not db.exists():
        return set()
    with closing(sqlite3.connect(db, timeout=10)) as conn:
        conn.execute(_CREATE)
        return {row[0] for row in conn.execute("SELECT connector FROM disabled WHERE session = ?", (sid,))}


def set_enabled(identity, sid, source, key, enabled):
    if source not in _SOURCES or not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,160}", key) or type(enabled) is not bool:
        raise ValueError("Invalid connector selection")
    root = personal_context.ensure_home(identity)
    db = personal_context._safe(root / "chat-connectors.sqlite3")
    with closing(sqlite3.connect(db, timeout=10)) as conn, conn:
        conn.execute(_CREATE)
        params = (sid, source + ":" + key)
        if enabled:
            conn.execute("DELETE FROM disabled WHERE session=? AND connector=?", params)
        else:
            conn.execute("INSERT OR IGNORE INTO disabled VALUES (?, ?)", params)


def source_rows(identity, source):
    from api import app_connections, hosted_connectors, integrations
    from api.ownership import identity_is_admin
    accounts = defaultdict(list)
    shared = set()
    if source == "hosted":
        for row in hosted_connectors.account_rows(identity):
            if row["disabled"] or not row["connectionId"]:
                continue
            accounts[row["connector"]].append({"id": row["connectionId"], "label": row["label"] or row["alias"],
                                               "active": str(row["status"]).lower() == "active"})
        catalog = [(row["slug"], row["name"], ["api"]) for row in hosted_connectors.catalog_for(identity)]
    else:
        email = personal_context.actor_email(identity)
        result = integrations.get_catalog(email, is_admin=identity_is_admin(identity))
        if not result["nango"]["available"]:
            raise RuntimeError("Connector catalog unavailable")
        for row in app_connections.Resolver(identity).visible_connections():
            if row["scope"] == "organization":
                if not row.get("errors"):
                    shared.add(row["provider_config_key"])
                continue
            accounts[row["provider_config_key"]].append({"id": row["connection_id"], "label": None,
                                                        "active": not row.get("errors")})
        catalog = []
        for row in result["providers"]:
            if not row["configured"] or not row["unique_key"]:
                continue
            kinds = ["mcp"] if row.get("auth_mode") == "MCP_OAUTH2" else ["api"]
            if row.get("cli_env"):
                kinds.append("cli")
            catalog.append((row["unique_key"], row["display_name"], kinds))
    return [{"key": key, "name": name, "connected": key in shared or any(a["active"] for a in accounts[key]),
             "organization": key in shared,
             "accounts": accounts[key], "kinds": kinds} for key, name, kinds in catalog]


def available_in_chat(handler, session, source):
    from api.config import _resolve_cli_toolsets, chat_mode_toolsets, get_config_for_profile_home
    from api.profiles import get_hermes_home_for_profile
    from api.governance.resource_scope import access_for, allowed
    from toolsets import resolve_toolset
    tool = "app_connections" if source == "nango" else "manage_connections"
    access = access_for(handler)
    if not allowed(access, "tools", tool):
        return False
    config = get_config_for_profile_home(get_hermes_home_for_profile(session.profile or "default"))
    groups = session.enabled_toolsets or _resolve_cli_toolsets(config)
    return any(tool in resolve_toolset(group) for group in chat_mode_toolsets(groups, session.chat_mode))


def handle(handler, data, *, write=False):
    from api.models import is_safe_session_id
    from api.ownership import _request_identity
    from api.routes import j
    identity = _request_identity(handler)
    sid, source = data.get("session_id"), data.get("source")
    if not is_safe_session_id(sid) or source not in (*_SOURCES, *chat_connection_inventory.SOURCES):
        return j(handler, {"error": "Invalid chat or connector source"}, status=400)
    try:
        personal_context.actor_email(identity)
        session = personal_context.session_for(identity, sid)
        if source in chat_connection_inventory.SOURCES:
            if write:
                return j(handler, {"error": "This connection is managed by the profile"}, status=400)
            rows = chat_connection_inventory.rows_for(handler, identity, session, source)
            return j(handler, {"connectors": rows})
        if write:
            set_enabled(identity, sid, source, data.get("key"), data.get("enabled"))
            return j(handler, {"ok": True})
        can_use = available_in_chat(handler, session, source)
        hidden = disabled(identity, sid)
        rows = source_rows(identity, source)
        for row in rows:
            row["selected"] = source + ":" + row["key"] not in hidden
        return j(handler, {"connectors": rows, "chat_available": can_use})
    except (KeyError, FileNotFoundError):
        return j(handler, {"error": "Conversation not found"}, status=404)
    except PermissionError:
        return j(handler, {"error": "Access denied"}, status=403)
    except ValueError:
        return j(handler, {"error": "Invalid selection"}, status=400)
    except (RuntimeError, OSError, sqlite3.Error, subprocess.SubprocessError):
        return j(handler, {"error": "Connector status unavailable. Try again."}, status=503)
