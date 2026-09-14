"""A capability decision cannot override managed role/resource ceilings."""
import os

from .models import GovernanceSubject, grant_matches
from .resolver import resolve_effective_access


def grant_within_bounds(policy, payload):
    email = str(payload.get("email") or "").strip().lower()
    user = policy.users.get(email)
    if user is None:
        return False
    if not (user.access_mode or user.access_level):
        return True
    access = resolve_effective_access(policy, GovernanceSubject(email=email))
    kind, value = str(payload.get("gkind") or ""), str(payload.get("value") or "")
    dimensions = {
        "tool": "tools", "toolset": "toolsets", "mcp": "mcp_servers",
        "profile": "profiles", "workspace": "workspaces", "route": "routes",
        "permission": "permissions", "file_read": "file_read_roots", "file_write": "file_write_roots",
        "workdir": "cli_workdir_roots", "cli": "cli_commands",
    }
    if kind == "skill":
        return access.allows("skills_view", value) and access.allows("skills_load", value)
    if kind == "secret_glob":
        # 14-09-2026 (Michael: an administrator must be able to approve every
        # queue item): a secret-file exception lands on one person's
        # files.allow_globs for one exact path, the per-person exception the
        # policy already supports, so it is decided from the queue like any
        # other grant. Only an explicit per-person deny on that path stays out
        # of reach here; the engine keeps credential and financial denies closed
        # for blacklist users regardless (EffectiveAccess.configuration_denies_file).
        expanded = os.path.expanduser(value)
        candidates = {value, expanded, os.path.realpath(expanded)}
        return not any(grant_matches(access.deny.file_denied_globs, c) for c in candidates)
    dim = dimensions.get(kind)
    if dim is None:
        return False
    return access.allows(dim, value, path=kind in {"file_read", "file_write", "workdir"})
