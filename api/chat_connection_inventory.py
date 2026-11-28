"""Display metadata for connections supplied by a profile or terminal.

Do not run commands, start MCP servers, or read credentials to build the list.
"""
import os
import re
import shutil
from pathlib import Path

from api.governance.models import grant_matches
from api.governance.resource_scope import allowed

SOURCES = ("mcp", "cli", "profile_api")
_COMMAND = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]{0,127}")


def _row(key, name, kind, status, available, origin):
    return {"key": key, "name": name, "kinds": [kind], "status": status,
            "available": available, "origin": origin, "managed": True}


def mcp_rows(config, groups, access, ceiling):
    from api.routes import _mcp_resource_visible, _parse_mcp_enabled
    if access is not None and not access.has_permission("mcp:read"):
        return []
    servers = config.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return []
    rows = []
    for raw_name, definition in servers.items():
        name = str(raw_name)
        if not _mcp_resource_visible(access, name) or (ceiling and not ceiling.allows("mcp_servers", name)):
            continue
        if not isinstance(definition, dict) or not (definition.get("url") or definition.get("command")):
            status = "invalid"
        elif not _parse_mcp_enabled(definition.get("enabled", True)):
            status = "disabled"
        else:
            status = "configured"
        group = "mcp-" + name
        available = (status == "configured" and (name in groups or group in groups)
                     and allowed(access, "toolsets", group, (name,)))
        rows.append(_row(name, name, "mcp", status, available, "profile"))
    return rows


def _installed_cli_names():
    """Include independently installed integration CLIs even with a wildcard grant."""
    for directory in dict.fromkeys(os.get_exec_path()):
        if not directory or not os.path.isabs(directory):
            continue
        try:
            for item in Path(directory).iterdir():
                if ((item.name.endswith("-cli") or item.name.startswith("cli-anything-"))
                        and item.is_file() and os.access(item, os.X_OK)):
                    yield item.name
        except OSError:
            continue


def cli_rows(config, tools, access, ceiling, policy):
    if access is not None and not access.allows("tools", "terminal"):
        return []
    commands = set()
    for entry in (*policy.roles.values(), *policy.groups.values(), *policy.users.values()):
        commands.update(entry.grants.cli_commands)
    if access:
        commands.update(access.grants.cli_commands)
    if ceiling:
        commands.update(ceiling.grants.cli_commands)
    terminal = config.get("terminal") or {}
    local = (terminal.get("env_type") or terminal.get("backend") or os.getenv("TERMINAL_ENV", "local")) == "local"
    if local:
        commands.update(_installed_cli_names())
    rows = []
    for name in sorted(commands):
        if not _COMMAND.fullmatch(name) or (access and (not access.allows("cli_commands", name)
                                                       or grant_matches(access.grants.cli_denied_commands, name))):
            continue
        if ceiling and not ceiling.allows("cli_commands", name):
            continue
        status = "installed" if local and shutil.which(name) else "declared"
        rows.append(_row(name, name, "cli", status, "terminal" in tools, "terminal"))
    return rows


def api_rows(config, groups, active_groups, access):
    from api.config import _custom_provider_entries, _custom_provider_slug_from_name
    from tools.registry import registry
    rows = []
    if access is None or access.has_permission("config:read"):
        configured = config.get("providers")
        providers = {}
        if isinstance(configured, dict):
            for key, spec in configured.items():
                if isinstance(spec, dict) and any(spec.get(field) for field in ("base_url", "api_key_env", "api_key")):
                    providers[str(key)] = str(key)
        model = config.get("model")
        if isinstance(model, dict) and model.get("base_url") and model.get("provider"):
            key = str(model["provider"])
            providers[key] = key
        for provider in _custom_provider_entries(config):
            name = str(provider.get("name") or "").strip()
            if name and provider.get("base_url"):
                providers[_custom_provider_slug_from_name(name)] = name
        for key, name in providers.items():
            if key and allowed(access, "model_providers", key):
                rows.append(_row(key, name, "api", "configured", None, "model"))
    api_groups = set()
    for entry in registry.get_all_entries():
        if entry.toolset not in groups or not allowed(access, "tools", entry.name) or not allowed(access, "toolsets", entry.toolset):
            continue
        if any(str(var).endswith(("_API_KEY", "_TOKEN", "_API_SECRET")) for var in entry.requires_env or ()):
            api_groups.add(entry.toolset)
    rows.extend(_row("toolset:" + name, name, "api", "declared", name in active_groups, "toolset")
                for name in sorted(api_groups))
    return rows


def rows_for(handler, identity, session, source):
    from api import bot_builder
    from api.config import _resolve_cli_toolsets, chat_mode_toolsets, get_config_for_profile_home
    from api.governance.enforce import is_profile_allowed_for
    from api.governance.loader import get_policy
    from api.governance.resource_scope import access_for
    from api.profiles import get_hermes_home_for_profile
    from toolsets import resolve_toolset

    profile = session.profile or "default"
    if not is_profile_allowed_for(identity, profile):
        raise PermissionError("Profile unavailable")
    access = access_for(handler)
    policy = get_policy()
    ceiling = None
    if bot_builder.managed(profile) is not None:
        if not policy.enabled:
            raise PermissionError("Managed profile unavailable")
        rights = access or bot_builder.access(identity)[1]
        ceiling = bot_builder.access_ceiling(identity, profile, rights)
    config = get_config_for_profile_home(get_hermes_home_for_profile(profile))
    profile_groups = set(_resolve_cli_toolsets(config))
    groups = set(chat_mode_toolsets(session.enabled_toolsets or profile_groups, session.chat_mode))
    if source == "mcp":
        return mcp_rows(config, groups, access, ceiling)
    if source == "cli":
        tools = {tool for group in groups if allowed(access, "toolsets", group) for tool in resolve_toolset(group)}
        return cli_rows(config, tools, access, ceiling, policy)
    return api_rows(config, profile_groups | groups, groups, access)
