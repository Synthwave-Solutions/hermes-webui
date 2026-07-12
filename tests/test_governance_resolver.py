"""Governance resolver tests: default deny, bootstrap wildcard, grant union,
SSO group mapping and grant/permission sources (preview contract).

Mirrors the reference dashboard_governance resolver tests.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance.loader import parse_governance_policy  # noqa: E402
from api.governance.models import GovernanceSubject  # noqa: E402
from api.governance.resolver import resolve_effective_access  # noqa: E402


def test_unknown_user_denied_by_default():
    policy = parse_governance_policy({"version": 1, "mode": "enforce", "default_effect": "deny"})
    access = resolve_effective_access(
        policy,
        GovernanceSubject(email="unknown@example.test", display_name="Unknown", provider="oidc"),
    )

    assert not access.has_permission("sessions:read")
    assert not access.is_profile_allowed("default")
    assert not access.is_route_allowed("/api/session")
    assert access.permissions == frozenset()


def test_bootstrap_admin_gets_wildcard_access_and_owner_role():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "default_effect": "deny",
            "bootstrap_admins": ["owner@example.test"],
        }
    )
    access = resolve_effective_access(
        policy,
        GovernanceSubject(email="OWNER@example.test", display_name="Owner", provider="oidc"),
    )

    assert access.has_permission("anything:anywhere")
    assert access.is_profile_allowed("finance")
    assert access.is_route_allowed("/api/whatever")
    assert "owner" in access.roles
    assert "bootstrap_admin" in access.grant_sources


def test_user_group_role_grants_union():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "roles": {
                "viewer": {"grants": {"permissions": ["sessions:read"], "profiles": ["default"]}},
                "operator": {"grants": {"permissions": ["chat:use"], "profiles": ["ops"]}},
            },
            "groups": {
                "sw-ops": {"roles": ["operator"], "sso_groups": ["google-ops"], "grants": {"permissions": ["logs:read"]}}
            },
            "users": {
                "user@example.test": {"roles": ["viewer"], "groups": ["sw-ops"], "grants": {"permissions": ["mcp:read"], "profiles": ["custom"]}}
            },
        }
    )
    access = resolve_effective_access(
        policy,
        GovernanceSubject(email="user@example.test", display_name="User", provider="oidc"),
    )

    assert access.permissions == frozenset({"sessions:read", "chat:use", "logs:read", "mcp:read"})
    assert access.profiles == frozenset({"default", "ops", "custom"})
    assert access.has_permission("chat:use")
    assert access.is_profile_allowed("custom")
    # merge order: role grants (sorted) first, then group, then direct user grants
    assert access.grant_sources == ("role:operator", "role:viewer", "group:sw-ops", "user:user@example.test")


def test_sso_group_claim_maps_to_local_group():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "groups": {
                "sw-eng": {
                    "sso_groups": ["engineering"],
                    "grants": {"permissions": ["skills:read"], "profiles": ["eng-ops"]},
                }
            },
        }
    )
    access = resolve_effective_access(
        policy,
        GovernanceSubject(
            email="eng@example.test",
            display_name="Eng",
            provider="oidc",
            groups=("engineering",),
        ),
    )

    assert access.has_permission("skills:read")
    assert access.is_profile_allowed("eng-ops")
    assert "sw-eng" in access.groups
    assert "group:sw-eng" in access.grant_sources


def test_route_wildcards_in_grants():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "users": {
                "user@example.test": {"grants": {"permissions": ["sessions:read"], "routes": ["/api/session*"]}}
            },
        }
    )
    access = resolve_effective_access(policy, GovernanceSubject(email="user@example.test"))

    assert access.is_route_allowed("/api/session")
    assert access.is_route_allowed("/api/sessions")
    assert access.is_route_allowed("/api/session/abc/messages")
    assert not access.is_route_allowed("/api/chat")


def test_preview_explains_source_of_grant():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "roles": {"viewer": {"grants": {"permissions": ["sessions:read"]}}},
            "users": {"user@example.test": {"roles": ["viewer"]}},
        }
    )
    access = resolve_effective_access(
        policy,
        GovernanceSubject(email="user@example.test", display_name="User", provider="oidc"),
    )

    decision = access.explain_permission("sessions:read")
    assert decision.allowed is True
    assert decision.reason == "allowed"
    assert "role:viewer" in decision.sources
    assert access.permission_sources["sessions:read"] == ("role:viewer",)

    denied = access.explain_permission("governance:write")
    assert denied.allowed is False
    assert denied.reason == "not_whitelisted"
