"""Guided bot configuration with explicit access and actor-limited capabilities."""
import copy
from dataclasses import replace
import fnmatch
import os
from pathlib import Path
import shutil
import tempfile
import threading
import yaml

_LOCK = threading.RLock()
_KEY = "synpulse_builder"


def _identity(identity):
    from api.personal_context import actor_email
    return actor_email(identity)


def _home(name):
    from api.profiles import _DEFAULT_HERMES_HOME, _validate_profile_name
    if name != "default":
        _validate_profile_name(name)
    path = _DEFAULT_HERMES_HOME if name == "default" else _DEFAULT_HERMES_HOME / "profiles" / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise PermissionError("Bot directory cannot use symlinks")
    return path


def _yaml(path):
    if path.is_symlink():
        raise PermissionError("Bot configuration cannot use symlinks")
    if not path.exists():
        return {}
    result = yaml.safe_load(path.read_text()) or {}
    if not isinstance(result, dict):
        raise ValueError("Invalid bot configuration")
    return result


def managed(name):
    data = _yaml(_home(name) / "profile.yaml").get(_KEY)
    if data is None:
        return None
    if isinstance(data, dict) and data.get("updating"):
        raise PermissionError("Bot update in progress; retry shortly")
    if not isinstance(data, dict) or not data.get("owner_email"):
        raise PermissionError("Invalid bot access configuration")
    return data


def access(identity):
    from api.governance.loader import get_policy
    from api.governance.enforce import subject_from_identity
    from api.governance.resolver import resolve_effective_access
    policy = get_policy()
    return policy, resolve_effective_access(policy, subject_from_identity(identity))


def allowed(identity, name):
    """None for legacy profiles; managed bots have their own explicit ACL."""
    data = managed(name)
    if data is None:
        return None
    email = _identity(identity)
    if email == data["owner_email"] or email in data.get("allowed_users", []):
        return True
    _, rights = access(identity)
    return bool(set(data.get("allowed_groups", [])) & set(rights.groups))


def require_edit(identity, name=None):
    policy, rights = access(identity)
    if not policy.enabled:
        raise PermissionError("Guided bots require active governance")
    if not rights.has_permission("profiles:admin"):
        raise PermissionError("Bot configuration requires profiles:admin")
    if name:
        data = managed(name)
        if data and _identity(identity) != data["owner_email"]:
            raise PermissionError("Only the bot owner can edit its configuration")
        if data is None:
            from api.governance.enforce import is_profile_allowed_for
            if not is_profile_allowed_for(identity, name):
                raise PermissionError("Bot is not available to this account")
    return policy, rights


def _selected_allowed(values, value):
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in values)


def catalog(identity):
    from api.profiles import _DEFAULT_HERMES_HOME
    policy, rights = require_edit(identity)
    cfg = _yaml(_DEFAULT_HERMES_HOME / "config.yaml")
    skills = []
    root = _DEFAULT_HERMES_HOME / "skills"
    if root.is_dir():
        for source in sorted(root.rglob("SKILL.md")):
            name = str(source.parent.relative_to(root))
            if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
                continue
            if _selected_allowed(rights.grants.skills_load, name):
                skills.append({"name": name, "description": ""})
    mcp = cfg.get("mcp_servers", {})
    mcp_names = [name for name in mcp if _selected_allowed(rights.grants.mcp_servers, name)] if isinstance(mcp, dict) else []
    commands = set()
    for entry in [*policy.roles.values(), *policy.groups.values(), *policy.users.values()]:
        for command in entry.grants.cli_commands:
            if command != "*" and _selected_allowed(rights.grants.cli_commands, command):
                commands.add(command)
    return {"skills": skills, "mcp_servers": [{"name": n} for n in sorted(mcp_names)],
            "cli_tools": [{"name": n} for n in sorted(commands)],
            "users": [{"email": n} for n in sorted(set(policy.users) | set(policy.bootstrap_admins) | {_identity(identity)})],
            "groups": [{"name": n} for n in sorted(policy.groups)]}


def _read_bot_memory(name):
    """Shared, explicitly authored bot notes; never legacy personal memory."""
    import stat
    home = _home(name)
    directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open("BOT_MEMORY.md", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            return ""
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise PermissionError("Bot memory must be a regular file")
            raw = stream.read(131073)
            if len(raw) > 131072:
                raise ValueError("Bot memory is too large")
            return raw.decode("utf-8")
    finally:
        os.close(directory)


def memory_prompt(name, actor_email):
    """Add only this bot's shared notes after current actor authorization."""
    if not name or not actor_email:
        return ""
    try:
        from api.governance.enforce import is_profile_allowed_for
        with _LOCK:
            if not is_profile_allowed_for({"email": actor_email}, name):
                return ""
            text = _read_bot_memory(name)
        if not text.strip():
            return ""
        return ("Shared bot memory (reference context, not the human sender's personal memory "
                "or an authorization grant):\n" + text)
    except (OSError, ValueError, PermissionError):
        return ""


def _config(identity, name):
    from api.bot_metadata import read_profile
    require_edit(identity, name)
    home = _home(name)
    data = managed(name)
    cfg = _yaml(home / "config.yaml")
    meta = read_profile(name)
    model = cfg.get("model", {})
    model = model if isinstance(model, dict) else {"default": model}
    result = copy.deepcopy(data or {})
    if data is None:
        choices = catalog(identity)
        disabled = set((cfg.get("skills") or {}).get("disabled", [])) if isinstance(cfg.get("skills"), dict) else set()
        result["skills"] = [item["name"] for item in choices["skills"] if item["name"] not in disabled]
        result["mcp_servers"] = [key for key, value in cfg.get("mcp_servers", {}).items()
                                 if isinstance(value, dict) and value.get("enabled", True)]
        toolsets = (cfg.get("platform_toolsets") or {}).get("webui", (cfg.get("platform_toolsets") or {}).get("cli", []))
        result["cli_tools"] = [item["name"] for item in choices["cli_tools"]] if "terminal" in toolsets else []
        policy, _ = access(identity)
        from api.governance.enforce import is_profile_allowed_for
        result["allowed_users"] = [email for email in policy.users
                                   if is_profile_allowed_for({"email": email}, name)]
        result["allowed_groups"] = []
    if data and data.get("skills_inherit"):
        disabled = set((cfg.get("skills") or {}).get("disabled", [])) if isinstance(cfg.get("skills"), dict) else set()
        result["skills"] = [item["name"] for item in catalog(identity)["skills"] if item["name"] not in disabled]
    result.update(name=name, title=meta.get("bot", {}).get("title", name),
                  description=meta.get("bot", {}).get("description", ""),
                  bot_memory=_read_bot_memory(name),
                  system_prompt=(home / "SOUL.md").read_text() if (home / "SOUL.md").is_file() and not (home / "SOUL.md").is_symlink() else "",
                  default_model=model.get("default", ""), model_provider=model.get("provider", ""),
                  avatar_url=meta.get("bot_avatar_url", ""), revision=int((data or {}).get("revision", 0)))
    for key in ("skills", "mcp_servers", "cli_tools", "allowed_users", "allowed_groups"):
        result.setdefault(key, [])
    result.pop("owner_email", None)
    result.pop("skills_inherit", None)
    return result


def get(identity, name=None):
    choices = catalog(identity)
    if name:
        config = _config(identity, name)
    else:
        from api.profiles import _DEFAULT_HERMES_HOME
        model = _yaml(_DEFAULT_HERMES_HOME / "config.yaml").get("model", {})
        model = model if isinstance(model, dict) else {}
        config = {"name": "", "title": "", "description": "", "system_prompt": "",
                  "skills": [], "mcp_servers": [], "cli_tools": [], "allowed_users": [],
                  "allowed_groups": [], "default_model": model.get("default", ""),
                  "model_provider": model.get("provider", ""), "avatar_url": ""}
    return {"catalog": choices, "config": config, "can_edit": True}


def _validate(identity, body):
    if not isinstance(body, dict):
        raise ValueError("Invalid bot configuration")
    permitted = {"name", "title", "description", "system_prompt", "skills", "mcp_servers",
                 "cli_tools", "allowed_users", "allowed_groups", "default_model",
                 "model_provider", "revision", "avatar", "bot_memory"}
    if set(body) - permitted:
        raise ValueError("Unknown bot configuration fields")
    name = body.get("name", "")
    target = _home(name)
    if not isinstance(body.get("system_prompt"), str) or not body["system_prompt"].strip():
        raise ValueError("Bot instructions are required")
    for key, maximum in (("title", 80), ("description", 400), ("system_prompt", 32768),
                         ("default_model", 200), ("model_provider", 200)):
        value = body.get(key, "")
        if not isinstance(value, str) or len(value) > maximum:
            raise ValueError("Invalid " + key)
    choices = catalog(identity)
    clean = {key: body.get(key, "") for key in ("title", "description", "system_prompt", "default_model", "model_provider")}
    for key in ("skills", "mcp_servers", "cli_tools", "allowed_users", "allowed_groups"):
        values = body.get(key, [])
        if not isinstance(values, list) or len(values) > 10000 or any(not isinstance(v, str) for v in values):
            raise ValueError("Invalid " + key)
        known = {entry.get("email", entry.get("name")) for entry in choices[{"allowed_users":"users", "allowed_groups":"groups"}.get(key, key)]}
        if set(values) - known:
            raise PermissionError("Unavailable selection in " + key)
        clean[key] = sorted(set(values))
    if "bot_memory" in body:
        if not isinstance(body["bot_memory"], str) or len(body["bot_memory"]) > 32768:
            raise ValueError("Bot memory must be at most 32768 characters")
        clean["bot_memory"] = body["bot_memory"]
    from api.profiles import _validate_profile_model_selection
    existing = _config(identity, name) if target.exists() else None
    unchanged_model = existing is not None and all(
        clean[key] == existing[key] for key in ("default_model", "model_provider"))
    # Editing instructions/photo must not depend on live provider discovery
    # for the exact model already configured on this bot. Grants below remain
    # authoritative, and any new selection still uses strict validation.
    if not unchanged_model:
        _validate_profile_model_selection(clean["default_model"], clean["model_provider"])
    _, rights = access(identity)
    for field, value in ((rights.grants.models, clean["default_model"]),
                         (rights.grants.model_providers, clean["model_provider"])):
        if value and not _selected_allowed(field, value):
            raise PermissionError("Model selection is not allowed")
    return name, target, clean


def save(identity, body):
    from api import profiles, bot_metadata
    from utils import atomic_yaml_write
    # Validate every field before a profile directory becomes discoverable.
    name, target, clean = _validate(identity, body)
    with _LOCK, bot_metadata._LOCK:
        exists = target.exists()
        require_edit(identity, name if exists else None)
        previous = managed(name) if exists else None
        if exists and any((target / child).is_symlink() for child in ("skills", "assets")):
            raise PermissionError("Bot assets or skills cannot use symlinks")
        actual_revision = int((previous or {}).get("revision", 0))
        if exists and ("revision" not in body or body["revision"] != actual_revision):
            raise RuntimeError("Bot changed or already exists. Reload before saving.")
        if not exists and "revision" in body:
            raise RuntimeError("Bot no longer exists. Reload before saving.")
        unchanged_skills = exists and set(clean["skills"]) == set(_config(identity, name)["skills"])
        if "bot_memory" not in clean:
            clean["bot_memory"] = _read_bot_memory(name) if exists else ""
        owner = (previous or {}).get("owner_email") or _identity(identity)
        data = {**clean, "owner_email": owner, "revision": actual_revision + 1}
        data.pop("bot_memory", None)  # BOT_MEMORY.md is the authoritative source.
        if unchanged_skills and (previous is None or previous.get("skills_inherit")):
            data["skills_inherit"] = True
        data["allowed_users"] = sorted(set(data["allowed_users"]) | {owner})
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".bot-stage-", dir=parent))
        backup = None
        try:
            if exists:
                # Copy only this bot's existing configuration; never another
                # person's profile, mailbox credentials, history or memories.
                for filename in ("config.yaml", "profile.yaml", ".env", "SOUL.md", "BOT_MEMORY.md"):
                    source = target / filename
                    if source.is_symlink():
                        raise PermissionError("Bot configuration cannot use symlinks")
                    if source.is_file():
                        shutil.copy2(source, stage / filename)
                if (target / "assets").is_dir() and not (target / "assets").is_symlink():
                    if any(item.is_symlink() for item in (target / "assets").rglob("*")):
                        raise PermissionError("Avatar assets cannot contain symlinks")
                    shutil.copytree(target / "assets", stage / "assets")
            cfg = _yaml(stage / "config.yaml")
            global_cfg = _yaml(profiles._DEFAULT_HERMES_HOME / "config.yaml")
            cfg["model"] = {**(cfg.get("model") if isinstance(cfg.get("model"), dict) else {}),
                            "default": clean["default_model"], "provider": clean["model_provider"]}
            # Routing definitions contain no personal profile copy. Shared
            # connection definitions stay server-side; APIs never return them.
            if not exists:
                cfg["custom_providers"] = copy.deepcopy(global_cfg.get("custom_providers", []))
            cfg["mcp_servers"] = {key: copy.deepcopy(global_cfg.get("mcp_servers", {})[key])
                                  for key in clean["mcp_servers"]}
            for value in cfg["mcp_servers"].values():
                if isinstance(value, dict):
                    value["enabled"] = True
            platforms = copy.deepcopy(cfg.get("platform_toolsets") or global_cfg.get("platform_toolsets") or {})
            if not isinstance(platforms, dict):
                platforms = {}
            for surface in ("webui", "cli"):
                baseline = platforms.get(surface, platforms.get("cli", ["file", "web", "memory", "delegation", "skills"]))
                baseline = baseline if isinstance(baseline, list) else []
                selected = [tool for tool in baseline if isinstance(tool, str) and not tool.startswith("mcp-") and tool != "terminal"]
                selected += ["skills"] + ["mcp-" + n for n in clean["mcp_servers"]]
                if clean["cli_tools"]:
                    selected.append("terminal")
                platforms[surface] = list(dict.fromkeys(selected))
            cfg["platform_toolsets"] = platforms
            atomic_yaml_write(stage / "config.yaml", cfg, sort_keys=False)
            (stage / "SOUL.md").write_text(clean["system_prompt"])
            (stage / "BOT_MEMORY.md").write_text(clean["bot_memory"], encoding="utf-8")
            metadata = _yaml(stage / "profile.yaml")
            metadata[_KEY] = data
            metadata.setdefault("ui_meta", {}).setdefault("hermes-bots", {}).update(
                title=clean["title"], description=clean["description"], custom=True)
            atomic_yaml_write(stage / "profile.yaml", metadata, sort_keys=False)
            if not unchanged_skills:
                (stage / "skills").mkdir(exist_ok=True)
            skills_root = profiles._DEFAULT_HERMES_HOME / "skills"
            for skill in ([] if unchanged_skills else clean["skills"]):
                source = skills_root / skill
                if not source.resolve().is_relative_to(skills_root.resolve()) or source.is_symlink():
                    raise PermissionError("Invalid skill source")
                if any(item.is_symlink() for item in source.rglob("*")):
                    raise PermissionError("Skill source cannot contain symlinks")
                shutil.copytree(source, stage / "skills" / skill, symlinks=False)
            if body.get("avatar"):
                blob = _avatar_bytes(body["avatar"])
                (stage / "assets").mkdir(exist_ok=True)
                (stage / "assets/avatar.png").write_bytes(blob)
            if exists:
                # Publish a deny-all transaction marker before new private
                # instructions/config can be observed under the old ACL.
                names = ("config.yaml", "SOUL.md", "BOT_MEMORY.md", "assets/avatar.png", "profile.yaml")
                had_skills = (target / "skills").exists()
                originals = {filename: ((target / filename).read_bytes() if (target / filename).is_file() else None)
                             for filename in names}
                old_metadata = _yaml(target / "profile.yaml")
                marker = copy.deepcopy(old_metadata)
                marker[_KEY] = {"owner_email": owner, "updating": True}
                atomic_yaml_write(target / "profile.yaml", marker, sort_keys=False)
                try:
                    for filename in ("config.yaml", "SOUL.md", "BOT_MEMORY.md"):
                        os.replace(stage / filename, target / filename)
                    old = target / "skills"
                    if (stage / "skills").exists():
                        if old.exists():
                            backup = target / (".skills-before-" + next(tempfile._get_candidate_names()))
                            os.replace(old, backup)
                        os.replace(stage / "skills", old)
                    if (stage / "assets/avatar.png").exists():
                        (target / "assets").mkdir(exist_ok=True)
                        os.replace(stage / "assets/avatar.png", target / "assets/avatar.png")
                    os.replace(stage / "profile.yaml", target / "profile.yaml")
                except BaseException:
                    # Restore content before restoring access/revision.
                    if backup and backup.exists():
                        if (target / "skills").exists():
                            shutil.rmtree(target / "skills")
                        os.replace(backup, target / "skills")
                        backup = None
                    if not had_skills and (target / "skills").exists():
                        shutil.rmtree(target / "skills")
                    for filename in names:
                        destination = target / filename
                        original = originals[filename]
                        if original is None:
                            destination.unlink(missing_ok=True)
                        else:
                            destination.parent.mkdir(exist_ok=True)
                            fd, temporary = tempfile.mkstemp(dir=destination.parent)
                            with os.fdopen(fd, "wb") as stream:
                                stream.write(original)
                            os.replace(temporary, destination)
                    raise
            else:
                os.replace(stage, target)
            profiles._invalidate_list_profiles_cache()
            profiles._invalidate_root_profile_cache()
            if backup:
                shutil.rmtree(backup)
            return {"ok": True, "config": _config(identity, name)}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def constrain_access(identity, name, rights):
    data = managed(name)
    if data is None:
        return rights
    if not allowed(identity, name):
        raise PermissionError("Bot access was revoked")
    grants = rights.grants
    def subset(existing, selected):
        return frozenset(v for v in selected if _selected_allowed(existing, v))
    return replace(rights, profiles=rights.profiles | {name}, grants=replace(
        grants, skills_load=subset(grants.skills_load, data["skills"]),
        skills_view=subset(grants.skills_view, data["skills"]),
        mcp_servers=subset(grants.mcp_servers, data["mcp_servers"]),
        cli_commands=subset(grants.cli_commands, data["cli_tools"])))


def _avatar_bytes(value):
    import base64
    import io
    import re
    from PIL import Image
    if not isinstance(value, str) or len(value) > 2800000:
        raise ValueError("Avatar is too large")
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", value)
    if not match:
        raise ValueError("Use a PNG, JPEG or WebP avatar")
    raw = base64.b64decode(match.group(2), validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        if image.width * image.height > 16000000:
            raise ValueError("Avatar dimensions too large")
        image.load()
        image.thumbnail((512, 512))
        result = io.BytesIO()
        image.convert("RGBA").save(result, format="PNG")
        return result.getvalue()


def access_ceiling(identity, name, rights):
    data = managed(name)
    if data is None:
        return None
    if not allowed(identity, name):
        raise PermissionError("Bot access was revoked")
    from api.governance.resolver import _wildcard_grants
    return replace(rights, mode="enforce", permissions=frozenset({"*"}),
                   profiles=frozenset({name}), grants=replace(
        _wildcard_grants(), skills_load=frozenset({"*"}) if data.get("skills_inherit") else frozenset(data["skills"]),
        skills_view=frozenset({"*"}) if data.get("skills_inherit") else frozenset(data["skills"]), skills_manage=frozenset(),
        mcp_servers=frozenset(data["mcp_servers"]),
        cli_commands=frozenset(data["cli_tools"])))


def guard_profile_request(handler, parsed, method):
    """Revalidate managed signed-cookie scopes at profile-dependent sinks."""
    path = parsed.path
    prefixes = ("/api/config", "/api/skills", "/api/skill/", "/api/mcp",
                "/api/models", "/api/model/", "/api/providers", "/api/personalities",
                "/api/personality/", "/api/reasoning", "/api/commands",
                "/api/plugins", "/api/toolsets", "/api/tools",
                "/api/profile/active", "/api/profile/bot", "/api/profile/avatar")
    # Default-deny a revoked active scope, including future profile-bound
    # APIs. Recovery and independently session/actor-scoped APIs are explicit.
    recovery = ("/api/auth/", "/api/governance/", "/api/chat", "/api/sessions", "/api/session/",
                "/api/projects", "/api/stream", "/api/events", "/api/health")
    if (not path.startswith("/api/") or path.startswith(recovery)
            or path in ("/api/profiles", "/api/profile/switch", "/api/memory",
                        "/api/memory/write", "/api/bots/builder", "/api/bots/knowledge", "/api/bots/knowledge/upload", "/api/version")):
        return True
    from urllib.parse import parse_qs
    from api.profiles import get_active_profile_name
    from api.governance.enforce import _request_identity
    from api.helpers import bad
    # Most sinks resolve their path from the signed active cookie, not
    # ?profile=. A harmless query target must never mask a revoked active bot.
    name = get_active_profile_name()
    if path == "/api/profile/avatar" and method in ("GET", "HEAD"):
        name = (parse_qs(parsed.query).get("profile") or [name])[0]
    if path in ("/api/profile/bot", "/api/profile/avatar") and method == "POST":
        return True  # Exact body target receives its own owner guard in routes.
    try:
        data = managed(name)
        if data is None:
            return True
        identity = _request_identity(handler)
        if allowed(identity, name) is not True:
            raise PermissionError("This bot is no longer available. Select another bot.")
        if method not in ("GET", "HEAD") and path.startswith(prefixes) and path != "/api/personality/set":
            require_edit(identity, name)
        return True
    except (PermissionError, ValueError, OSError):
        if method not in ("GET", "HEAD"):
            # The route may reject before consuming the request body.
            # Do not parse leftover JSON as a subsequent keep-alive request.
            try:
                handler.close_connection = True
            except AttributeError:
                pass
        bad(handler, "Bot access is restricted. Select an available bot.", 403)
        return False
