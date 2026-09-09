"""A capability decision cannot override managed role/resource ceilings."""
from .models import GovernanceSubject
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
        return False  # managed secret exceptions require an explicit policy edit
    dim = dimensions.get(kind)
    if dim is None:
        return False
    return access.allows(dim, value, path=kind in {"file_read", "file_write", "workdir"})
