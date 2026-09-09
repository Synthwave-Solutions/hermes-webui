"""Per-user access semantics, including wildcard and privilege boundaries."""
from copy import deepcopy

import pytest

from api.governance.loader import GovernancePolicyError, parse_governance_policy
from api.governance.models import GovernanceSubject
from api.governance.resolver import resolve_effective_access


BASE = {
    "mode": "enforce",
    "roles": {"member": {"grants": {
        "permissions": ["chat:use", "files:read", "terminal:use", "governance:write"],
        "routes": ["*"], "profiles": ["alice"],
        "tools": {"builtins": ["*"]},
        "skills": {"load": ["*"]},
    }}},
    "users": {"alice@example.test": {"roles": ["member"]}},
}


def access(**entry):
    raw = deepcopy(BASE)
    raw["users"]["alice@example.test"].update(entry)
    return resolve_effective_access(parse_governance_policy(raw), GovernanceSubject(email="alice@example.test"))


def test_explicit_empty_whitelist_has_no_inherited_work_permissions():
    a = access(access_level="user", access_mode="whitelist")
    assert not a.has_permission("chat:use")
    assert not a.is_tool_allowed("web_search")
    assert not a.is_profile_allowed("alice")


def test_blacklist_inherits_role_envelope_and_concrete_deny_beats_wildcard():
    a = access(access_level="elevated", access_mode="blacklist",
               deny={"tools": {"builtins": ["terminal"]}, "routes": ["/api/file*"]})
    assert a.has_permission("chat:use")
    assert not a.has_permission("governance:write")
    assert a.is_tool_allowed("web_search")
    assert not a.is_tool_allowed("terminal")
    assert not a.is_route_allowed("/api/file")
    assert not a.is_profile_allowed("bob")


def test_user_level_cannot_acquire_elevated_or_administrative_permission():
    a = access(access_level="user", access_mode="blacklist")
    assert not a.has_permission("terminal:use")
    assert not a.has_permission("governance:write")


def test_whitelist_must_explicitly_allow_and_stays_within_role_resources():
    a = access(access_level="user", access_mode="whitelist", grants={
        "permissions": ["chat:use", "governance:write"], "routes": ["*"],
        "profiles": ["alice", "bob"], "tools": {"builtins": ["web_search"]},
    })
    assert a.has_permission("chat:use")
    assert a.is_profile_allowed("alice")
    assert not a.is_profile_allowed("bob")
    assert not a.has_permission("governance:write")
    assert a.is_tool_allowed("web_search")
    assert not a.is_tool_allowed("terminal")


def test_legacy_role_union_compatible_but_deny_is_authoritative():
    a = access(deny={"tools": {"builtins": ["terminal"]}})
    assert a.has_permission("chat:use")
    assert not a.is_tool_allowed("terminal")


def test_changing_only_level_retains_existing_resource_union():
    a = access(access_level="elevated", grants={"profiles": ["direct-profile"]})
    assert a.has_permission("chat:use")
    assert a.has_permission("terminal:use")
    assert not a.has_permission("governance:write")
    assert a.is_profile_allowed("alice")
    assert a.is_profile_allowed("direct-profile")
    assert a.access_mode == ""
    assert a.approval_configured is False


def test_level_ceiling_cannot_retain_patterns_that_reenable_admin_permissions():
    a = access(access_level="user", grants={"permissions": ["*:*", "system:*", "profiles:*"]})
    assert a.has_permission("chat:use")
    assert not a.has_permission("system:ops")
    assert not a.has_permission("gateway:restart")
    assert not a.has_permission("profiles:admin")
    assert not a.has_permission("governance:write")


@pytest.mark.parametrize("denial", [{"files": {"read_roots": ["/private/restricted"]}}, {"env": {"vars": ["PRIVATE_TOKEN"]}}])
def test_direct_terminal_api_is_denied_when_host_execution_cannot_preserve_resources(monkeypatch, denial):
    from api.governance import loader
    from api.governance.enforce import evaluate_request
    raw = deepcopy(BASE)
    raw["users"]["alice@example.test"].update(access_level="elevated", access_mode="blacklist", deny=denial)
    monkeypatch.setattr(loader, "get_policy", lambda: parse_governance_policy(raw))
    for route in ("/api/terminal/start", "/api/terminal/input", "/api/commands/exec"):
        assert not evaluate_request({"email": "alice@example.test"}, "POST", route).allow


@pytest.mark.parametrize("entry", [
    {"access_level": "root"}, {"access_mode": "allow_all"},
    {"approval": {"mode": "sometimes"}},
    {"approval": {"mode": "automatic", "prompt": ""}},
    {"approval": {"mode": "automatic", "prompt": ["allow"]}},
    {"approval": {"mode": "automatic", "prompt": "a" * 8001}},
])
def test_invalid_per_user_configuration_fails_closed(entry):
    with pytest.raises(GovernancePolicyError):
        access(**entry)
