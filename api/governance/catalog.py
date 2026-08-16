"""Route catalog: maps hermes-webui API routes to governance permissions.

The RouteRule mechanism is vendored from the hermes-agent dashboard
route_catalog; the catalog CONTENT is rebuilt for the hermes-webui route
surface using ONLY permission names already granted in the canonical
~/.hermes/dashboard-governance.yaml, so the existing owner/admin/operator/
viewer roles work without any policy edit.
"""
from __future__ import annotations

from dataclasses import dataclass

_MUTATION_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Pre-auth public login surface: these /api/* endpoints are reached BEFORE a
# session identity exists, so governance must let them through under enforce
# and even under a broken policy, otherwise mode=enforce (or a policy-load
# error) would 403 every login attempt and brick the bootstrap admin too.
# Kept in sync with the login endpoints in api.auth.PUBLIC_PATHS; a coverage
# test asserts the two stay aligned so a new public login route cannot silently
# become un-exempt. Non-login public paths (pages, static, manifests) are not
# listed here because they are already handled by the non-/api passthrough.
# /api/csp-report is listed as defense in depth: browsers POST CSP violation
# reports without credentials, and today the endpoint bypasses the hook via a
# server.py dispatch special-case; the entry here keeps it reachable even if
# that special-case ever moves.
_ANON_ROUTES: frozenset[str] = frozenset({
    "/api/auth/login",
    "/api/auth/status",
    "/api/auth/oidc/start",
    "/api/auth/oidc/callback",
    "/api/auth/passkey/options",
    "/api/auth/passkey/login",
    "/api/csp-report",
})

# Authenticated session self-management: no permission required beyond a
# valid identity. route_permission returns None for these; enforcement
# exempts them from the unknown_route fail-closed rule.
_SELF_ROUTES: frozenset[str] = frozenset({
    "/api/auth/status",
    "/api/auth/logout",
    "/api/auth/passkeys",
    "/api/auth/passkey/register/options",
    "/api/auth/passkey/register",
    "/api/auth/passkey/delete",
    "/api/governance/me",
})


@dataclass(frozen=True)
class RouteRule:
    pattern: str
    read_permission: str | None
    write_permission: str | None = None
    match: str = "prefix"

    def matches(self, path: str) -> bool:
        if self.match == "exact":
            return path == self.pattern
        return path == self.pattern or path.startswith(self.pattern.rstrip("/") + "/")

    def permission_for(self, method: str) -> str | None:
        if method.upper() in _MUTATION_METHODS:
            return self.write_permission or self.read_permission
        return self.read_permission


# Ordered most-specific first. Unknown /api/* routes deliberately return None;
# enforcement treats that as unknown_route so new endpoints fail closed until
# classified here (tests/test_governance_catalog_coverage.py is the net).
ROUTE_CATALOG: tuple[RouteRule, ...] = (
    # governance admin (mirror reference)
    RouteRule("/api/governance/policy",   "governance:read",  "governance:write"),
    RouteRule("/api/governance/validate", "governance:read",  "governance:read"),
    RouteRule("/api/governance/preview",  "governance:preview", "governance:preview"),
    RouteRule("/api/governance/audit",    "governance:audit:read"),
    RouteRule("/api/governance/usage",    "governance:usage:read"),
    RouteRule("/api/governance/users",    "governance:read",  "governance:write"),
    RouteRule("/api/governance/groups",   "governance:read",  "governance:write"),
    RouteRule("/api/governance",          "governance:read",  "governance:write"),

    # profiles
    RouteRule("/api/profiles",            "profiles:read"),
    RouteRule("/api/profile/active",      "profiles:read", match="exact"),
    RouteRule("/api/profile",             "profiles:read", "profiles:admin"),

    # sessions, projects, background
    RouteRule("/api/session/yolo",        "sessions:read", "sessions:write", match="exact"),
    RouteRule("/api/session",             "sessions:read", "sessions:write"),
    RouteRule("/api/sessions",            "sessions:read", "sessions:write"),
    RouteRule("/api/projects",            "sessions:read", "sessions:write"),
    RouteRule("/api/background",          "sessions:read", "sessions:write"),
    RouteRule("/api/bg-task-complete-ack", "sessions:write", "sessions:write", match="exact"),
    RouteRule("/api/process-complete-ack", "sessions:write", "sessions:write", match="exact"),

    # chat execution (incl. SSE streams, approval/clarify, voice)
    RouteRule("/api/chat",                "chat:use", "chat:use"),
    RouteRule("/api/btw",                 "chat:use", "chat:use", match="exact"),
    RouteRule("/api/goal",                "chat:use", "chat:use", match="exact"),
    RouteRule("/api/approval",            "chat:use", "chat:use"),
    RouteRule("/api/clarify",             "chat:use", "chat:use"),
    RouteRule("/api/transcribe/capability", "model:read", match="exact"),
    RouteRule("/api/transcribe",          "chat:use", "chat:use", match="exact"),
    RouteRule("/api/tts",                 "chat:use", "chat:use", match="exact"),

    # terminal + commands (RCE-grade; deliberately split off chat:use so chat
    # access no longer implies shell access; grant terminal:use explicitly)
    RouteRule("/api/terminal",            "terminal:use", "terminal:use"),
    RouteRule("/api/commands/exec",       "terminal:use", "terminal:use", match="exact"),
    RouteRule("/api/commands",            "config:read", "config:read"),

    # files and workspace
    RouteRule("/api/escape",              "files:read", "files:write"),
    RouteRule("/api/list",                "files:read", match="exact"),
    RouteRule("/api/file",                "files:read", "files:write"),
    RouteRule("/api/media",               "files:read", match="exact"),
    RouteRule("/api/folder/download",     "files:read", match="exact"),
    RouteRule("/api/upload",              "files:write", "files:write"),
    RouteRule("/api/workspace/upload",    "files:write", "files:write", match="exact"),
    RouteRule("/api/workspaces",          "files:read", "files:write"),
    RouteRule("/api/rollback",            "files:read", "files:write"),
    RouteRule("/api/wiki",                "files:read"),
    RouteRule("/api/notes",               "files:read"),

    # git
    RouteRule("/api/git-info",            "git:read", match="exact"),
    RouteRule("/api/git",                 "git:read", "git:write"),

    # config, settings, models, providers
    RouteRule("/api/settings",            "config:read", "config:write", match="exact"),
    RouteRule("/api/reasoning",           "config:read", "config:write", match="exact"),
    RouteRule("/api/models",              "model:read", "model:read"),
    RouteRule("/api/model",               "model:read", "model:write"),
    RouteRule("/api/default-model",       "model:write", "model:write", match="exact"),
    RouteRule("/api/providers",           "config:read", "config:write"),
    RouteRule("/api/integrations",        "config:read", "config:write"),
    RouteRule("/api/provider",            "analytics:read"),
    RouteRule("/api/personalities",       "config:read", match="exact"),
    RouteRule("/api/personality",         "config:write", "config:write"),
    RouteRule("/api/prompts",             "config:read", "config:write", match="exact"),
    RouteRule("/api/memory/write",        "memory:write", "memory:write", match="exact"),
    RouteRule("/api/memory",              "memory:read", match="exact"),
    RouteRule("/api/admin",               "config:write", "config:write"),
    RouteRule("/api/dashboard",           "dashboard:read", "dashboard:write"),
    RouteRule("/api/insights",            "analytics:read"),
    RouteRule("/api/project-os",          "analytics:read"),
    RouteRule("/api/logs",                "logs:read", match="exact"),
    RouteRule("/api/client-events/log",   "status:read", "status:read", match="exact"),

    # skills, mcp, plugins, extensions
    RouteRule("/api/skills",              "skills:read", "skills:write"),
    RouteRule("/api/mcp",                 "mcp:read", "mcp:write"),
    RouteRule("/api/plugins",             "plugins:read", match="exact"),
    RouteRule("/api/extensions",          "plugins:read", "plugins:write"),  # incl. sidecar proxy wildcard

    # cron (route_permission special-cases POST .../run -> cron:run, as reference)
    RouteRule("/api/crons",               "cron:read", "cron:write"),

    # gateway
    RouteRule("/api/gateway/status",      "gateway:read", match="exact"),
    RouteRule("/api/gateway",             "gateway:read", "gateway:restart"),

    # kanban bridge (agent dispatch is chat-run grade)
    RouteRule("/api/kanban/dispatch",     "chat:use", "chat:use", match="exact"),
    RouteRule("/api/kanban",              "sessions:read", "sessions:write"),

    # system, health, updates, onboarding
    RouteRule("/api/health/restart",      "system:ops", "system:ops", match="exact"),
    RouteRule("/api/health",              "status:read"),
    RouteRule("/api/system",              "system:read"),
    RouteRule("/api/shutdown",            "system:ops", "system:ops", match="exact"),
    RouteRule("/api/updates/check",       "system:read", "system:read", match="exact"),
    RouteRule("/api/updates/summary",     "system:read", "system:read", match="exact"),
    RouteRule("/api/updates",             "system:read", "system:ops"),
    RouteRule("/api/onboarding",          "config:read", "config:write"),
)


def route_permission(path: str, method: str) -> str | None:
    if path in _SELF_ROUTES:
        return None
    for rule in ROUTE_CATALOG:
        if rule.matches(path):
            if method.upper() == "POST" and path.startswith("/api/crons") and path.rstrip("/").endswith("/run"):
                return "cron:run"
            return rule.permission_for(method)
    return None
