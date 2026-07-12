"""Governance loader tests: policy parsing, path resolution, atomic save, etag.

Mirrors the reference dashboard_governance loader tests. All state is
isolated via tmp_path and env overrides; the real ~/.hermes files are
never touched.
"""
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance.loader import (  # noqa: E402
    GovernancePolicyError,
    load_governance_policy,
    parse_governance_policy,
    policy_etag,
    policy_mutation_lock,
    resolve_policy_path,
    save_governance_policy,
)


# Placeholder copy of the canonical ~/.hermes/dashboard-governance.yaml
# structure (same keys, placeholder values). The loader must accept the
# shared file as-is, so this shape parsing is the compatibility contract.
CANONICAL_SHAPE = {
    "version": 1,
    "mode": "report_only",
    "default_effect": "deny",
    "bootstrap_admins": ["owner@example.test"],
    "identity": {
        "provider": "google",
        "allowed_domains": ["example.test"],
        "claims": {"email": "email", "display_name": "name", "groups": "groups"},
        "group_sync": {"enabled": True, "strict": True, "jit_create_groups": False},
    },
    "roles": {
        "owner": {
            "description": "Full owner.",
            "grants": {
                "permissions": ["*"],
                "profiles": ["*"],
                "routes": ["*"],
                "settings": {"read": ["*"], "write": ["*"]},
                "tools": {"toolsets": ["*"], "builtins": ["*"]},
                "skills": {"view": ["*"], "load": ["*"], "manage": ["*"]},
                "mcp": {"servers": ["*"], "tools": {"*": ["*"]}},
                "models": {"providers": ["*"], "models": ["*"]},
                "files": {"read_roots": ["*"], "write_roots": ["*"]},
                "cli": {"commands": ["*"], "workdir_roots": ["*"]},
                "usage_caps": {},
            },
        },
        "admin": {
            "description": "Administrator.",
            "grants": {
                "permissions": ["governance:read", "governance:write", "sessions:read", "chat:use"],
                "profiles": ["*"],
                "routes": ["*"],
                "files": {
                    "read_roots": ["/home/placeholder"],
                    "write_roots": ["/home/placeholder"],
                    "denied_globs": ["**/.env", "**/*.pem"],
                },
            },
        },
        "operator": {
            "description": "Operator.",
            "grants": {
                "permissions": ["chat:use", "sessions:read", "sessions:write", "files:read"],
                "profiles": ["default"],
                "routes": ["/api/sessions", "/api/chat"],
                "settings": {"read": ["model.default"], "write": []},
                "usage_caps": {"daily_tool_calls": 100},
            },
        },
        "viewer": {
            "description": "Viewer.",
            "grants": {
                "permissions": ["sessions:read", "status:read"],
                "profiles": ["default"],
                "routes": ["/api/sessions"],
            },
        },
    },
    "groups": {
        "sw-admins": {"sso_groups": ["sw-admins@example.test"], "roles": ["admin"]},
        "sw-engineering": {"sso_groups": ["sw-engineering@example.test"], "roles": ["operator"]},
        "sw-freelancers": {"sso_groups": ["sw-freelancers@example.test"], "roles": ["operator"]},
        "sw-viewers": {"sso_groups": ["sw-viewers@example.test"], "roles": ["viewer"]},
    },
    "users": {
        "Owner@Example.test": {"roles": ["owner"]},
    },
}


def test_missing_policy_defaults_to_off(tmp_path):
    policy = load_governance_policy(path=tmp_path / "missing.yaml")

    assert policy.mode == "off"
    assert policy.default_effect == "deny"
    assert policy.enabled is False
    assert policy.roles == {}


def test_canonical_policy_shape_parses(tmp_path):
    path = tmp_path / "dashboard-governance.yaml"
    path.write_text(yaml.safe_dump(CANONICAL_SHAPE), encoding="utf-8")

    policy = load_governance_policy(path=path)

    assert policy.mode == "report_only"
    assert policy.enabled is True
    assert policy.enforce is False
    assert policy.bootstrap_admins == ("owner@example.test",)
    assert set(policy.roles) == {"owner", "admin", "operator", "viewer"}
    assert set(policy.groups) == {"sw-admins", "sw-engineering", "sw-freelancers", "sw-viewers"}
    assert policy.roles["owner"].grants.permissions == frozenset({"*"})
    assert policy.roles["operator"].grants.profiles == frozenset({"default"})
    assert policy.roles["operator"].grants.routes == frozenset({"/api/sessions", "/api/chat"})
    assert policy.roles["operator"].grants.usage_caps == {"daily_tool_calls": 100}
    assert policy.roles["admin"].grants.file_denied_globs == frozenset({"**/.env", "**/*.pem"})
    assert policy.groups["sw-admins"].sso_groups == frozenset({"sw-admins@example.test"})
    # user emails are normalized to lowercase
    assert "owner@example.test" in policy.users
    # unknown-to-the-parser sections (identity) survive in raw
    assert policy.raw["identity"]["provider"] == "google"


def test_invalid_mode_is_rejected(tmp_path):
    path = tmp_path / "dashboard-governance.yaml"
    path.write_text("version: 1\nmode: maybe\n", encoding="utf-8")

    with pytest.raises(GovernancePolicyError):
        load_governance_policy(path=path)


def test_non_deny_default_effect_is_rejected():
    with pytest.raises(GovernancePolicyError):
        parse_governance_policy({"version": 1, "mode": "enforce", "default_effect": "allow"})


def test_policy_path_resolution_order(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit.yaml"
    env_policy = tmp_path / "env-policy.yaml"
    env_home = tmp_path / "env-home"

    monkeypatch.setenv("HERMES_WEBUI_GOVERNANCE_POLICY", str(env_policy))
    monkeypatch.setenv("HERMES_HOME", str(env_home))

    assert resolve_policy_path(path=explicit) == explicit
    assert resolve_policy_path() == env_policy

    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY")
    assert resolve_policy_path() == env_home / "dashboard-governance.yaml"
    assert resolve_policy_path(hermes_home=tmp_path) == tmp_path / "dashboard-governance.yaml"

    monkeypatch.delenv("HERMES_HOME")
    assert resolve_policy_path() == Path.home() / ".hermes" / "dashboard-governance.yaml"


def test_save_policy_validates_and_writes_atomically(tmp_path):
    path = tmp_path / "nested" / "dashboard-governance.yaml"
    payload = {
        "version": 1,
        "mode": "enforce",
        "default_effect": "deny",
        "users": {
            "Owner@Example.test": {
                "grants": {
                    "permissions": ["governance:read"],
                    "profiles": ["default"],
                    "routes": ["/api/governance/policy"],
                }
            }
        },
    }

    saved = save_governance_policy(payload, path=path)

    assert saved == path
    assert [p for p in path.parent.iterdir() if p.name.endswith(".tmp")] == []
    policy = load_governance_policy(path=path)
    assert policy.mode == "enforce"
    assert "owner@example.test" in policy.users


def test_save_policy_rejects_invalid_policy_without_overwriting(tmp_path):
    path = tmp_path / "dashboard-governance.yaml"
    path.write_text("version: 1\nmode: enforce\ndefault_effect: deny\n", encoding="utf-8")

    with pytest.raises(GovernancePolicyError):
        save_governance_policy({"version": 1, "mode": "maybe"}, path=path)

    assert "mode: enforce" in path.read_text(encoding="utf-8")


def test_policy_etag_stable_across_key_order_and_changes_on_content():
    a = {"mode": "report_only", "version": 1, "bootstrap_admins": ["a@b.test"]}
    b = {"version": 1, "bootstrap_admins": ["a@b.test"], "mode": "report_only"}
    c = {"version": 1, "bootstrap_admins": ["a@b.test"], "mode": "enforce"}

    assert policy_etag(a) == policy_etag(b)
    assert policy_etag(a) != policy_etag(c)
    assert len(policy_etag(a)) == 64
    # non-dict payloads hash the empty document instead of raising
    assert policy_etag(None) == policy_etag({})


def test_policy_mutation_lock_is_a_shared_threading_lock():
    lock = policy_mutation_lock()
    assert lock is policy_mutation_lock()
    assert isinstance(lock, type(threading.Lock()))
    with lock:
        pass
