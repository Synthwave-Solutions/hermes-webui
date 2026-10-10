"""Governance policy loading, validation and atomic persistence.

Vendored from the hermes-agent dashboard_governance loader with the
hermes_cli.config dependency removed. Both apps read the same canonical
policy file (~/.hermes/dashboard-governance.yaml) so the schema and the
validation results must stay identical to the reference implementation.

One deliberate exception (plan 2.5 and 3.6): the managed-service sections
``installation``, ``organization`` and ``departments`` and the ``delegable``
and ``external`` flags are validated here only. The engine's parser ignores
them, so a policy it accepts can still fail closed in the WebUI.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from .models import (
    INSTALLATION_KINDS,
    GrantSet,
    GovernanceDepartment,
    GovernanceGroup,
    GovernanceOrganization,
    GovernancePolicy,
    GovernanceRole,
    GovernanceUser,
    _ALLOWED_MODES,
    _norm_email,
    _string_set,
    reserved_namespace,
)


class GovernancePolicyError(ValueError):
    """Raised when a dashboard governance policy is invalid."""


class PolicyImmutableFieldError(GovernancePolicyError):
    """A write would change ``organization.id`` or ``installation.kind``.

    Both are stamped by the installation render (plan 2.5, 3.6); no path in
    this app may add, change or remove them.
    """

    def __init__(self, field_name: str):
        self.field = field_name
        super().__init__(f"{field_name} is set by the installation setup and cannot be changed here")


def resolve_policy_path(
    path: str | Path | None = None,
    hermes_home: str | Path | None = None,
) -> Path:
    """Resolve the canonical policy file path.

    Resolution order: explicit ``path`` arg, env ``HERMES_WEBUI_GOVERNANCE_POLICY``,
    explicit ``hermes_home`` arg, env ``HERMES_HOME``, then the default
    ``~/.hermes/dashboard-governance.yaml`` shared with hermes-agent.
    """
    if path is not None:
        return Path(path).expanduser()
    env_path = os.getenv("HERMES_WEBUI_GOVERNANCE_POLICY", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    if hermes_home is not None:
        return Path(hermes_home).expanduser() / "dashboard-governance.yaml"
    env_home = os.getenv("HERMES_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser() / "dashboard-governance.yaml"
    return Path.home() / ".hermes" / "dashboard-governance.yaml"


def _flag(data: Mapping[str, Any], key: str, owner: str) -> bool:
    """An optional boolean flag; anything but a real boolean is refused.

    ``delegable: "yes"`` must not be read as true (it widens what delegated
    admins may hand out) nor silently as false (the author meant something).
    """
    if key not in data or data.get(key) is None:
        return False
    value = data.get(key)
    if not isinstance(value, bool):
        raise GovernancePolicyError(f"{owner} {key} must be true or false")
    return value


def _parse_role(name: str, raw: Any) -> GovernanceRole:
    data = raw if isinstance(raw, Mapping) else {}
    return GovernanceRole(
        name=name,
        description=str(data.get("description") or ""),
        grants=GrantSet.from_mapping(data.get("grants") if isinstance(data.get("grants"), Mapping) else data),
        delegable=_flag(data, "delegable", f"role {name}"),
    )


def _parse_group(name: str, raw: Any) -> GovernanceGroup:
    data = raw if isinstance(raw, Mapping) else {}
    return GovernanceGroup(
        name=name,
        description=str(data.get("description") or ""),
        roles=tuple(str(v) for v in (data.get("roles") or []) if str(v).strip()),
        sso_groups=_string_set(data.get("sso_groups")),
        grants=GrantSet.from_mapping(data.get("grants")),
        delegable=_flag(data, "delegable", f"group {name}"),
        external=_flag(data, "external", f"group {name}"),
    )


def _parse_user(email: str, raw: Any) -> GovernanceUser:
    data = raw if isinstance(raw, Mapping) else {}
    from .models import ACCESS_LEVELS, ACCESS_MODES, APPROVAL_MODES
    level = data.get("access_level", "")
    access_mode = data.get("access_mode", "")
    for name, value, allowed in (("access_level", level, ACCESS_LEVELS), ("access_mode", access_mode, ACCESS_MODES)):
        if name in data and (not isinstance(value, str) or value not in allowed):
            raise GovernancePolicyError(f"invalid user {name}: expected one of {', '.join(sorted(allowed))}")
    approval = data.get("approval", {})
    if not isinstance(approval, Mapping) or set(approval) - {"mode", "prompt"}:
        raise GovernancePolicyError("user approval must contain mode and prompt only")
    approval_mode = approval.get("mode", "manual")
    prompt = approval.get("prompt", "")
    if not isinstance(approval_mode, str) or approval_mode not in APPROVAL_MODES:
        raise GovernancePolicyError("invalid user approval mode")
    if not isinstance(prompt, str) or len(prompt) > 8000:
        raise GovernancePolicyError("user approval prompt must be a string of at most 8000 characters")
    if approval_mode == "automatic" and not prompt.strip():
        raise GovernancePolicyError("automatic approval requires an administrator-authored prompt")
    return GovernanceUser(
        email=_norm_email(email),
        roles=tuple(str(v) for v in (data.get("roles") or []) if str(v).strip()),
        groups=tuple(str(v) for v in (data.get("groups") or []) if str(v).strip()),
        grants=GrantSet.from_mapping(data.get("grants")),
        deny=GrantSet.from_mapping(data.get("deny")),
        access_level=level,
        access_mode=access_mode,
        approval_mode=approval_mode,
        approval_prompt=prompt.strip(),
        approval_configured="approval" in data,
    )


# ── Managed-service sections (plan 2.5 and 3.6) ─────────────────────────────
#
# installation, organization and departments are rendered from client.yaml by
# the installation render. They are validated here so a policy that would let
# a delegated admin hand out more than a platform admin allowed never loads:
# like any other invalid policy, it fails closed (policy_error on /api).

# organization.id and department keys travel in headers, audit rows and
# memory bank names, so both are plain lowercase slugs. The department key
# rule is the narrowest one any consumer applies (plan addendum 2.1).
_ORG_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_DEPARTMENT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
_EMAIL_RE = re.compile(r"^[^@\s,;:<>()\[\]\"'\\]+@[^@\s,;:<>()\[\]\"'\\]+\.[^@\s,;:<>()\[\]\"'\\]+$")

# Permissions a department group may never carry: whoever manages the
# group's membership (a department admin, from Wave 2) would hand them out.
# The user-level rule of the resolver's level ceiling, plus governance and
# reserved names.
_PRIVILEGED_PERMISSIONS = frozenset({
    "terminal:use", "config:write", "system:write", "system:ops", "gateway:restart",
    "model:write", "mcp:write", "plugins:write",
})


def _email_list(value: Any, owner: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise GovernancePolicyError(f"{owner} must be a list of e-mail addresses")
    emails: list[str] = []
    for item in value:
        email = _norm_email(item) if isinstance(item, str) else ""
        if not email or not _EMAIL_RE.match(email):
            raise GovernancePolicyError(f"{owner} must be a list of e-mail addresses")
        if email not in emails:
            emails.append(email)
    return tuple(sorted(emails))


def _name_list(value: Any, owner: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) and v.strip() for v in value):
        raise GovernancePolicyError(f"{owner} must be a list of names")
    return tuple(dict.fromkeys(v.strip() for v in value))


def _optional_text(data: Mapping[str, Any], key: str, owner: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise GovernancePolicyError(f"{owner} {key} must be text")
    return value.strip()


def _parse_installation(raw: Any) -> str:
    """The installation kind: "client", "hq", or "" when the block is absent."""
    if raw is None:
        return ""
    if not isinstance(raw, Mapping):
        raise GovernancePolicyError("installation must be a mapping")
    kind = raw.get("kind")
    kind = kind.strip().lower() if isinstance(kind, str) else ""
    if kind not in INSTALLATION_KINDS:
        raise GovernancePolicyError("installation kind must be client or hq")
    return kind


def _parse_organization(raw: Any) -> GovernanceOrganization | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise GovernancePolicyError("organization must be a mapping")
    org_id = raw.get("id")
    if not isinstance(org_id, str) or not _ORG_ID_RE.match(org_id.strip()):
        raise GovernancePolicyError("organization id must be a lowercase identifier")
    return GovernanceOrganization(
        id=org_id.strip(),
        name=_optional_text(raw, "name", "organization"),
        admins=_email_list(raw.get("admins"), "organization admins"),
        billing_admins=_email_list(raw.get("billing_admins"), "organization billing_admins"),
    )


def _parse_departments(raw: Any) -> dict[str, GovernanceDepartment]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise GovernancePolicyError("departments must be a mapping")
    departments: dict[str, GovernanceDepartment] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not _DEPARTMENT_KEY_RE.match(key):
            raise GovernancePolicyError("department keys must be lowercase identifiers")
        if not isinstance(value, Mapping):
            raise GovernancePolicyError(f"department {key} must be a mapping")
        group = value.get("group")
        if not isinstance(group, str) or not group.strip():
            raise GovernancePolicyError(f"department {key} needs a group")
        departments[key] = GovernanceDepartment(
            key=key,
            name=_optional_text(value, "name", f"department {key}") or key,
            group=group.strip(),
            admins=_email_list(value.get("admins"), f"department {key} admins"),
            assignable_roles=_name_list(value.get("assignable_roles"), f"department {key} assignable_roles"),
            assignable_groups=_name_list(value.get("assignable_groups"), f"department {key} assignable_groups"),
        )
    return departments


def _privileged_permission(permission: str) -> bool:
    value = str(permission)
    return (
        any(char in value for char in "*?[")
        or value.startswith("governance:")
        or value.endswith(":admin")
        or value in _PRIVILEGED_PERMISSIONS
        or bool(reserved_namespace(value))
    )


def _privileged_grants(grants: GrantSet) -> bool:
    """Grants a department admin must never be able to hand out by membership.

    Any permission above the user level, any wildcard in another dimension,
    and every capability whose requests stay platform-only (CLI commands, MCP
    servers, skill management, environment variables; plan 3.6).
    """
    if any(_privileged_permission(p) for p in grants.permissions):
        return True
    if grants.cli_commands or grants.mcp_servers or grants.mcp_tools or grants.skills_manage or grants.env_vars:
        return True
    for name in ("profiles", "routes", "settings_read", "settings_write", "toolsets", "tools",
                 "skills_view", "skills_load", "model_providers", "models", "file_read_roots",
                 "file_write_roots", "file_allow_globs", "cli_workdir_roots", "workspaces"):
        if any(_total_wildcard(value) for value in getattr(grants, name)):
            return True
    return False


def _total_wildcard(value: Any) -> bool:
    """"*", "**", "/**" and the like: a grant of everything in its dimension."""
    text = str(value).strip()
    return "*" in text and text.replace("*", "").strip("/") == ""


def group_is_privileged(policy_roles: Mapping[str, GovernanceRole], group: GovernanceGroup) -> bool:
    """True when membership of ``group`` confers more than a delegated admin may give.

    A role the group names that is unknown or not flagged delegable counts,
    and so do privileged grants on the group itself or on any of its roles.
    Unknown is treated as privileged (fail closed).
    """
    for role_name in group.roles:
        role = policy_roles.get(role_name)
        if role is None or not role.delegable or _privileged_grants(role.grants):
            return True
    return _privileged_grants(group.grants)


def _validate_managed_sections(
    *,
    installation_kind: str,
    organization: GovernanceOrganization | None,
    departments: Mapping[str, GovernanceDepartment],
    roles: Mapping[str, GovernanceRole],
    groups: Mapping[str, GovernanceGroup],
) -> None:
    if organization is not None:
        if installation_kind == "hq":
            raise GovernancePolicyError("an hq installation has no organization block")
        external = sorted(name for name, group in groups.items() if group.external)
        if external:
            raise GovernancePolicyError("an organization block cannot sit next to external groups")
    if departments and organization is None:
        raise GovernancePolicyError("departments need an organization block")
    seen_groups: dict[str, str] = {}
    for key, department in departments.items():
        group = groups.get(department.group)
        if group is None:
            raise GovernancePolicyError(f"department {key} names an unknown group")
        if department.group in seen_groups:
            raise GovernancePolicyError(f"department {key} shares its group with department {seen_groups[department.group]}")
        seen_groups[department.group] = key
        if department.group.lower().startswith("hd:") or group.sso_groups:
            raise GovernancePolicyError(f"department {key} group must not be synced from the identity provider")
        if group.external or group_is_privileged(roles, group):
            raise GovernancePolicyError(f"department {key} group must not be privileged")
        for role_name in department.assignable_roles:
            role = roles.get(role_name)
            if role is None or not role.delegable:
                raise GovernancePolicyError(f"department {key} may only assign roles marked delegable")
        for group_name in department.assignable_groups:
            assignable = groups.get(group_name)
            if assignable is None or not assignable.delegable:
                raise GovernancePolicyError(f"department {key} may only assign groups marked delegable")


def parse_governance_policy(data: Mapping[str, Any] | None) -> GovernancePolicy:
    raw = dict(data or {})
    mode = str(raw.get("mode") or "off").strip().lower()
    if mode not in _ALLOWED_MODES:
        raise GovernancePolicyError(f"invalid dashboard governance mode: {mode}")
    default_effect = str(raw.get("default_effect") or "deny").strip().lower()
    if default_effect != "deny":
        raise GovernancePolicyError("dashboard governance v1 only supports default_effect: deny")
    roles_raw = raw.get("roles") if isinstance(raw.get("roles"), Mapping) else {}
    groups_raw = raw.get("groups") if isinstance(raw.get("groups"), Mapping) else {}
    users_raw = raw.get("users") if isinstance(raw.get("users"), Mapping) else {}
    roles = {str(name): _parse_role(str(name), value) for name, value in roles_raw.items()}
    groups = {str(name): _parse_group(str(name), value) for name, value in groups_raw.items()}
    users = {_norm_email(str(email)): _parse_user(str(email), value) for email, value in users_raw.items()}
    installation_kind = _parse_installation(raw.get("installation"))
    organization = _parse_organization(raw.get("organization"))
    departments = _parse_departments(raw.get("departments"))
    _validate_managed_sections(
        installation_kind=installation_kind,
        organization=organization,
        departments=departments,
        roles=roles,
        groups=groups,
    )
    return GovernancePolicy(
        version=int(raw.get("version") or 1),
        mode=mode,
        default_effect=default_effect,
        bootstrap_admins=tuple(sorted(_norm_email(v) for v in raw.get("bootstrap_admins") or [] if _norm_email(v))),
        roles=roles,
        groups=groups,
        users=users,
        raw=raw,
        installation_kind=installation_kind,
        organization=organization,
        departments=departments,
    )


# ── Render-stamped fields (plan 2.5, 3.6, 3.7) ──────────────────────────────

IMMUTABLE_POLICY_FIELDS = ("organization.id", "installation.kind")


def _stamped_values(raw: Any) -> dict[str, str]:
    data = raw if isinstance(raw, Mapping) else {}
    organization = data.get("organization")
    installation = data.get("installation")
    org_id = organization.get("id") if isinstance(organization, Mapping) else None
    kind = installation.get("kind") if isinstance(installation, Mapping) else None
    return {
        "organization.id": str(org_id).strip() if org_id is not None else "",
        "installation.kind": str(kind).strip().lower() if kind is not None else "",
    }


def immutable_field_changes(before: Any, after: Any) -> list[str]:
    """The render-stamped fields that differ between two raw policy documents.

    Adding, changing and removing all count: ``organization.id`` is stamped
    once by the render, and ``installation.kind`` decides whether delegated
    administration exists at all, so neither may be written from this app.
    """
    old, new = _stamped_values(before), _stamped_values(after)
    return [name for name in IMMUTABLE_POLICY_FIELDS if old[name] != new[name]]


def _stored_raw_policy(policy_path: Path) -> Mapping[str, Any]:
    """The raw document currently on disk ({} when there is none).

    An unreadable file refuses the write: the stamped fields cannot be
    compared, and every API path already refuses to write over a broken
    policy (it cannot load it).
    """
    try:
        text = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise GovernancePolicyError("the stored governance policy cannot be read") from exc
    try:
        loaded = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise GovernancePolicyError("the stored governance policy is not valid YAML") from exc
    if not isinstance(loaded, Mapping):
        raise GovernancePolicyError("the stored governance policy must be a mapping")
    return loaded


def load_governance_policy(
    *,
    path: str | Path | None = None,
    hermes_home: str | Path | None = None,
) -> GovernancePolicy:
    policy_path = Path(path).expanduser() if path is not None else resolve_policy_path(hermes_home=hermes_home)
    if not policy_path.exists():
        return GovernancePolicy(mode="off", default_effect="deny")
    try:
        loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise GovernancePolicyError(f"invalid YAML in dashboard governance policy: {exc}") from exc
    if not isinstance(loaded, Mapping):
        raise GovernancePolicyError("dashboard governance policy must be a mapping")
    return parse_governance_policy(loaded)


def save_governance_policy(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    hermes_home: str | Path | None = None,
) -> Path:
    """Validate and atomically write dashboard governance policy YAML.

    Refuses (PolicyImmutableFieldError) any write that adds, changes or
    removes ``organization.id`` or ``installation.kind`` compared with the
    stored file: the installation render owns both (plan 2.5, 3.6). Every
    writer in this app goes through here, so this is the last line behind
    the explicit checks in the governance API.
    """
    if not isinstance(data, Mapping):
        raise GovernancePolicyError("dashboard governance policy must be a mapping")
    parse_governance_policy(data)
    policy_path = Path(path).expanduser() if path is not None else resolve_policy_path(hermes_home=hermes_home)
    changed = immutable_field_changes(_stored_raw_policy(policy_path), data)
    if changed:
        raise PolicyImmutableFieldError(changed[0])
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    # Unique temp name per writer: with a fixed ``<policy>.yaml.tmp`` two
    # concurrent writers (the webui and the hermes-agent dashboard, or the
    # ``hermes governance`` CLI) truncate the SAME temp file mid-write and can
    # publish interleaved content. mkstemp gives each writer its own file, so
    # concurrent saves degrade to last-write-wins of complete snapshots.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(policy_path.parent),
        prefix=f".{policy_path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(dict(data), handle, sort_keys=False, default_flow_style=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, policy_path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    _clear_policy_cache()
    return policy_path


def policy_etag(raw: Any) -> str:
    """Stable content hash of a raw policy mapping (optimistic concurrency)."""
    payload = raw if isinstance(raw, dict) else {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Process-wide mutation lock: the webui is a threaded http.server, so every
# admin-API read-check-save cycle must serialize through this lock.
_POLICY_MUTATION_LOCK = threading.Lock()


def policy_mutation_lock() -> threading.Lock:
    return _POLICY_MUTATION_LOCK


# Injectable policy accessor: tests swap the loader without touching the
# enforcement hook or the admin API. The production accessor is cached because
# governance runs before every API handler.
_policy_loader: Callable[[], GovernancePolicy] | None = None
_POLICY_CACHE_LOCK = threading.Lock()
_POLICY_CACHE_PATH: Path | None = None
_POLICY_CACHE_SIGNATURE: tuple[bool, int, int, int] | None = None
_POLICY_CACHE_VALUE: GovernancePolicy | None = None


def _policy_file_signature(path: Path) -> tuple[bool, int, int, int]:
    """Return a cheap identity for hot-path policy cache invalidation."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (False, 0, 0, 0)
    return (True, stat.st_mtime_ns, stat.st_size, getattr(stat, "st_ino", 0))


def _clear_policy_cache() -> None:
    global _POLICY_CACHE_PATH, _POLICY_CACHE_SIGNATURE, _POLICY_CACHE_VALUE
    with _POLICY_CACHE_LOCK:
        _POLICY_CACHE_PATH = None
        _POLICY_CACHE_SIGNATURE = None
        _POLICY_CACHE_VALUE = None


def _get_cached_policy() -> GovernancePolicy:
    """Load once per file version while preserving hot policy reloads.

    Path + inode + nanosecond mtime + size keep the common path to one stat
    call, while atomic replacements and in-place edits are observed on the next
    request. The final signature avoids pinning a stale version if a replacement
    races the read.
    """
    global _POLICY_CACHE_PATH, _POLICY_CACHE_SIGNATURE, _POLICY_CACHE_VALUE
    path = resolve_policy_path()
    signature = _policy_file_signature(path)
    with _POLICY_CACHE_LOCK:
        if (
            _POLICY_CACHE_VALUE is not None
            and _POLICY_CACHE_PATH == path
            and _POLICY_CACHE_SIGNATURE == signature
        ):
            return _POLICY_CACHE_VALUE
        policy = load_governance_policy(path=path)
        _POLICY_CACHE_PATH = path
        _POLICY_CACHE_SIGNATURE = _policy_file_signature(path)
        _POLICY_CACHE_VALUE = policy
        return policy


def set_policy_loader(fn: Callable[[], GovernancePolicy] | None) -> None:
    global _policy_loader
    _policy_loader = fn
    _clear_policy_cache()


def get_policy() -> GovernancePolicy:
    loader = _policy_loader or _get_cached_policy
    return loader()
