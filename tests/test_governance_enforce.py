"""Pure evaluate_request decision tests with an injected policy loader.

No server, no auth, no real ~/.hermes files: the policy is injected via
api.governance.loader.set_policy_loader and reset after every test.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import loader  # noqa: E402
from api.governance.enforce import evaluate_request, subject_from_identity  # noqa: E402
from api.governance.loader import GovernancePolicyError, parse_governance_policy  # noqa: E402

BOOTSTRAP = "michael@example.test"

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "owner": {
            "grants": {"permissions": ["*"], "profiles": ["*"], "routes": ["*"]},
        },
        "admin": {
            "grants": {
                "permissions": [
                    "governance:read", "governance:write", "governance:preview",
                    "governance:audit:read", "governance:usage:read",
                    "sessions:read", "sessions:write", "chat:use",
                    "files:read", "files:write", "git:read", "git:write",
                    "config:read", "config:write", "model:read", "model:write",
                    "profiles:read", "profiles:admin", "skills:read", "skills:write",
                    "mcp:read", "mcp:write", "plugins:read", "plugins:write",
                    "cron:read", "cron:write", "cron:run", "gateway:read",
                    "logs:read", "analytics:read", "memory:read", "memory:write",
                    "status:read", "system:read",
                ],
                "profiles": ["*"],
                "routes": ["*"],
            },
        },
        "operator": {
            "grants": {
                "permissions": [
                    "chat:use", "sessions:read", "sessions:write",
                    "files:read", "files:write", "git:read", "model:read",
                    "profiles:read", "status:read", "memory:read",
                ],
                "profiles": ["default"],
                "routes": [
                    "/api/session*", "/api/sessions*", "/api/chat*",
                    "/api/file*", "/api/list", "/api/git*", "/api/models*",
                    "/api/profiles*", "/api/health*", "/api/memory",
                    "/api/governance/me",
                ],
            },
        },
        "viewer": {
            "grants": {
                "permissions": ["sessions:read", "files:read", "status:read", "model:read", "profiles:read"],
                "profiles": ["default"],
                "routes": [
                    "/api/session*", "/api/sessions*", "/api/file*",
                    "/api/models*", "/api/profiles*", "/api/health*",
                ],
            },
        },
    },
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "operator@example.test": {"roles": ["operator"]},
        "viewer@example.test": {"roles": ["viewer"]},
    },
}


def _identity(email, groups=None, method="oidc"):
    return {"email": email, "groups": list(groups or []), "claims_subset": {}, "method": method}


@pytest.fixture
def inject_policy():
    def _set(data):
        policy = parse_governance_policy(data)
        loader.set_policy_loader(lambda: policy)
        return policy
    yield _set
    loader.set_policy_loader(None)


@pytest.fixture
def enforce_policy(inject_policy):
    return inject_policy(POLICY)


def test_mode_off_allows_everything(inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})

    decision = evaluate_request(None, "POST", "/api/session/delete")
    assert decision.allow is True
    assert decision.reason == "governance_off"
    assert decision.mode == "off"


def test_non_api_paths_pass_through(enforce_policy):
    for path in ("/", "/static/app.js", "/session/abc", "/login"):
        decision = evaluate_request(None, "GET", path)
        assert decision.allow is True, path
        assert decision.reason == "non_api"


def test_bootstrap_admin_is_never_denied(enforce_policy):
    identity = _identity(BOOTSTRAP.upper())

    # unknown route: everyone else fails closed, bootstrap passes
    decision = evaluate_request(identity, "POST", "/api/not-in-the-catalog")
    assert decision.allow is True
    assert decision.reason == "bootstrap_admin"

    # known route
    decision = evaluate_request(identity, "POST", "/api/gateway/restart")
    assert decision.allow is True
    assert decision.reason == "bootstrap_admin"
    assert decision.resource == "gateway:restart"

    # disallowed profile target does not stop the bootstrap admin either
    decision = evaluate_request(identity, "GET", "/api/session?profile=finance")
    assert decision.allow is True


def test_anonymous_identity_is_unauthenticated(enforce_policy):
    decision = evaluate_request(None, "GET", "/api/session")
    assert decision.allow is False
    assert decision.reason == "unauthenticated"

    # a session dict without email or sub is anonymous too
    decision = evaluate_request({"email": "", "groups": [], "claims_subset": {}, "method": "local"}, "GET", "/api/session")
    assert decision.allow is False
    assert decision.reason == "unauthenticated"


def test_unknown_user_hits_route_whitelist_first(enforce_policy):
    decision = evaluate_request(_identity("stranger@example.test"), "GET", "/api/session")
    assert decision.allow is False
    assert decision.reason == "route_not_allowed"


def test_route_not_allowed_for_operator_outside_whitelist(enforce_policy):
    decision = evaluate_request(_identity("operator@example.test"), "GET", "/api/settings")
    assert decision.allow is False
    assert decision.reason == "route_not_allowed"


def test_permission_not_allowed_for_viewer_write(enforce_policy):
    decision = evaluate_request(_identity("viewer@example.test"), "POST", "/api/file/save")
    assert decision.allow is False
    assert decision.reason == "permission_not_allowed"
    assert decision.resource == "files:write"


def test_unknown_route_fails_closed_even_with_wildcard_routes(enforce_policy):
    decision = evaluate_request(_identity("admin@example.test"), "GET", "/api/not-in-the-catalog")
    assert decision.allow is False
    assert decision.reason == "unknown_route"


def test_profile_query_target_check(enforce_policy):
    operator = _identity("operator@example.test")

    denied = evaluate_request(operator, "GET", "/api/session?profile=finance")
    assert denied.allow is False
    assert denied.reason == "profile_not_allowed"

    assert evaluate_request(operator, "GET", "/api/session?profile=default").allow is True
    # the sticky-active pseudo profile is exempt
    assert evaluate_request(operator, "GET", "/api/session?profile=active").allow is True
    # unrelated query params are ignored
    assert evaluate_request(operator, "GET", "/api/session?limit=5").allow is True


def test_self_route_needs_only_authentication(enforce_policy):
    decision = evaluate_request(_identity("viewer@example.test"), "GET", "/api/governance/me")
    assert decision.allow is False  # viewer routes do not whitelist it
    assert decision.reason == "route_not_allowed"

    decision = evaluate_request(_identity("operator@example.test"), "GET", "/api/governance/me")
    assert decision.allow is True
    assert decision.reason == "allowed"
    assert decision.resource == ""


def test_role_decision_matrix(enforce_policy):
    matrix = [
        # (email, method, path, allowed, reason)
        ("admin@example.test", "GET", "/api/session", True, "allowed"),
        ("admin@example.test", "POST", "/api/session/delete", True, "allowed"),
        ("admin@example.test", "POST", "/api/chat/start", True, "allowed"),
        ("admin@example.test", "POST", "/api/settings", True, "allowed"),
        ("admin@example.test", "POST", "/api/governance/policy", True, "allowed"),
        ("admin@example.test", "POST", "/api/gateway/restart", False, "permission_not_allowed"),
        ("admin@example.test", "POST", "/api/shutdown", False, "permission_not_allowed"),
        ("operator@example.test", "GET", "/api/session", True, "allowed"),
        ("operator@example.test", "POST", "/api/session/delete", True, "allowed"),
        ("operator@example.test", "POST", "/api/chat/start", True, "allowed"),
        ("operator@example.test", "POST", "/api/file/save", True, "allowed"),
        ("operator@example.test", "POST", "/api/git/commit", False, "permission_not_allowed"),
        ("operator@example.test", "POST", "/api/settings", False, "route_not_allowed"),
        ("viewer@example.test", "GET", "/api/session", True, "allowed"),
        ("viewer@example.test", "GET", "/api/file", True, "allowed"),
        ("viewer@example.test", "POST", "/api/session/delete", False, "permission_not_allowed"),
        ("viewer@example.test", "POST", "/api/chat/start", False, "route_not_allowed"),
    ]
    for email, method, path, allowed, reason in matrix:
        decision = evaluate_request(_identity(email), method, path)
        assert decision.allow is allowed, (email, method, path, decision)
        assert decision.reason == reason, (email, method, path, decision)


def test_policy_error_fails_closed():
    def _boom():
        raise GovernancePolicyError("bad policy")

    loader.set_policy_loader(_boom)
    try:
        decision = evaluate_request(_identity(BOOTSTRAP), "GET", "/api/session")
        assert decision.allow is False
        assert decision.reason == "policy_error"
        assert decision.mode == "enforce"
    finally:
        loader.set_policy_loader(None)


def test_subject_from_identity_mapping():
    subject = subject_from_identity(
        {
            "email": "User@Example.Test",
            "groups": ["sw-engineering", ""],
            "claims_subset": {"sub": "abc123", "name": "User Name"},
            "method": "oidc",
        }
    )
    assert subject.email == "user@example.test"
    assert subject.normalized_email == "user@example.test"
    assert subject.user_id == "abc123"
    assert subject.display_name == "User Name"
    assert subject.provider == "oidc"
    assert subject.groups == ("sw-engineering",)

    assert subject_from_identity(None).email == ""
    assert subject_from_identity({}).normalized_email == ""
