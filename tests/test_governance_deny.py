"""Per-user deny (off-toggle) tests: loader parse, resolver subtraction,
bootstrap-admin exemption and admin API acceptance/validation.

The deny GrantSet is subtracted from the merged role/group/user union AFTER
the union, so an explicit off-toggle wins from any allow source. Mirrors the
vendored hermes-agent dashboard_governance implementation.
"""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import governance_api  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.governance.models import GrantSet, GovernanceSubject  # noqa: E402
from api.governance.resolver import resolve_effective_access  # noqa: E402


# ── Loader ──────────────────────────────────────────────────────────────────

def test_loader_parses_user_deny():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "users": {
                "user@example.test": {
                    "deny": {
                        "skills": {"load": ["alpha"]},
                        "cli": {"commands": ["ls"]},
                        "mcp": {"servers": ["srv"]},
                    }
                }
            },
        }
    )
    user = policy.users["user@example.test"]
    assert user.deny.skills_load == frozenset({"alpha"})
    assert user.deny.cli_commands == frozenset({"ls"})
    assert user.deny.mcp_servers == frozenset({"srv"})
    assert not user.deny.is_empty()


def test_loader_missing_deny_is_empty():
    policy = parse_governance_policy(
        {"version": 1, "mode": "enforce", "users": {"user@example.test": {"roles": ["viewer"]}}}
    )
    assert policy.users["user@example.test"].deny.is_empty()


# ── GrantSet.subtract ───────────────────────────────────────────────────────

def test_subtract_wildcard_deny_empties_category():
    base = GrantSet.from_mapping({"skills": {"load": ["a", "b"], "view": ["a", "b"]}})
    deny = GrantSet.from_mapping({"skills": {"load": ["*"]}})
    out = base.subtract(deny)
    assert out.skills_load == frozenset()
    assert out.skills_view == frozenset({"a", "b"})


def test_subtract_specific_deny_cannot_narrow_wildcard_allow():
    # Documented limitation: "*" stays "*" under a specific deny; the admin
    # API warns when a deny targets a wildcard-granted category.
    base = GrantSet.from_mapping({"skills": {"load": ["*"]}})
    deny = GrantSet.from_mapping({"skills": {"load": ["a"]}})
    assert base.subtract(deny).skills_load == frozenset({"*"})


def test_subtract_mcp_tools_follow_server_deny():
    base = GrantSet.from_mapping(
        {"mcp": {"servers": ["s1", "s2"], "tools": {"s1": ["t1", "t2"], "s2": ["t3"]}}}
    )
    deny = GrantSet.from_mapping({"mcp": {"servers": ["s2"], "tools": {"s1": ["t2"]}}})
    out = base.subtract(deny)
    assert out.mcp_servers == frozenset({"s1"})
    assert out.mcp_tools == {"s1": frozenset({"t1"})}


def test_subtract_never_touches_denied_globs_or_caps():
    base = GrantSet.from_mapping(
        {"files": {"denied_globs": ["**/.env"]}, "usage_caps": {"daily_tokens": 5}}
    )
    deny = GrantSet.from_mapping(
        {"files": {"denied_globs": ["**/.env"]}, "usage_caps": {"daily_tokens": 99}}
    )
    out = base.subtract(deny)
    assert out.file_denied_globs == frozenset({"**/.env"})
    assert out.usage_caps == {"daily_tokens": 5}


# ── Resolver ────────────────────────────────────────────────────────────────

DENY_POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["owner@example.test"],
    "roles": {
        "maker": {
            "grants": {
                "permissions": ["sessions:read", "chat:use"],
                "skills": {"view": ["a", "b", "c"], "load": ["a", "b", "c"]},
                "cli": {"commands": ["git", "ls"]},
                "mcp": {"servers": ["s1", "s2"], "tools": {"s1": ["t1", "t2"]}},
            }
        }
    },
    "groups": {"crew": {"grants": {"skills": {"load": ["d"]}}}},
    "users": {
        "user@example.test": {
            "roles": ["maker"],
            "groups": ["crew"],
            "deny": {
                "permissions": ["chat:use"],
                "skills": {"load": ["b", "d"]},
                "cli": {"commands": ["ls"]},
                "mcp": {"servers": ["s2"], "tools": {"s1": ["t2"]}},
            },
        },
        "owner@example.test": {"deny": {"skills": {"load": ["*"]}}},
    },
}


def test_resolver_subtracts_deny_after_union():
    policy = parse_governance_policy(DENY_POLICY)
    access = resolve_effective_access(policy, GovernanceSubject(email="user@example.test"))

    # deny wins over role AND group grants
    assert access.grants.skills_load == frozenset({"a", "c"})
    assert access.grants.skills_view == frozenset({"a", "b", "c"})
    assert access.grants.cli_commands == frozenset({"git"})
    assert access.grants.mcp_servers == frozenset({"s1"})
    assert access.grants.mcp_tools == {"s1": frozenset({"t1"})}
    assert not access.has_permission("chat:use")
    assert access.has_permission("sessions:read")
    assert "deny:user:user@example.test" in access.grant_sources
    assert "chat:use" not in access.permission_sources


def test_resolver_bootstrap_admin_exempt_from_deny():
    policy = parse_governance_policy(DENY_POLICY)
    access = resolve_effective_access(policy, GovernanceSubject(email="owner@example.test"))
    # a stray deny: "*" must not brick the owner
    assert "*" in access.grants.skills_load
    assert "deny:user:owner@example.test" not in access.grant_sources


def test_resolver_empty_deny_leaves_sources_untouched():
    policy = parse_governance_policy(
        {
            "version": 1,
            "mode": "enforce",
            "users": {"user@example.test": {"grants": {"permissions": ["sessions:read"]}}},
        }
    )
    access = resolve_effective_access(policy, GovernanceSubject(email="user@example.test"))
    assert not any(source.startswith("deny:") for source in access.grant_sources)


# ── Admin API ───────────────────────────────────────────────────────────────

BOOTSTRAP = "michael@example.test"

API_POLICY = {
    "version": 1,
    "mode": "report_only",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "admin": {
            "grants": {
                "permissions": ["governance:read", "governance:write", "governance:preview"],
                "profiles": ["*"],
                "routes": ["*"],
            }
        },
        "viewer": {"grants": {"permissions": ["sessions:read"], "skills": {"load": ["a", "b"]}}},
    },
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "viewer@example.test": {"roles": ["viewer"]},
        BOOTSTRAP: {"roles": ["admin"]},
    },
}


class FakeHandler:
    def __init__(self, body=None, headers=None):
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = dict(headers or {})
        if raw:
            self.headers.setdefault("Content-Length", str(len(raw)))
        self.rfile = io.BytesIO(raw)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = {}
        self.close_connection = False

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    loader.set_policy_loader(None)
    yield tmp_path
    loader.set_policy_loader(None)


@pytest.fixture
def policy_file(isolated_home):
    def _write(data=API_POLICY):
        path = isolated_home / "dashboard-governance.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path
    return _write


@pytest.fixture
def as_user(monkeypatch):
    def _set(email, groups=None):
        identity = {"email": email, "groups": list(groups or []), "claims_subset": {}, "method": "oidc"}
        monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: identity)
    return _set


def _call(path, method="GET", body=None, headers=None, query=""):
    handler = FakeHandler(body=body, headers=headers)
    handled = governance_api.handle_governance_api(handler, SimpleNamespace(path=path, query=query), method)
    return handled, handler


def _etag():
    return loader.policy_etag(dict(loader.get_policy().raw))


def test_api_user_update_accepts_deny_and_resolver_applies_it(policy_file, as_user):
    policy_file()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/users/update", "POST",
        body={
            "email": "viewer@example.test",
            "entry": {"roles": ["viewer"], "deny": {"skills": {"load": ["b"]}}},
        },
        headers={"If-Match": _etag()},
    )
    assert handler.status == 200
    saved = loader.get_policy().raw["users"]["viewer@example.test"]
    assert saved["deny"] == {"skills": {"load": ["b"]}}
    access = resolve_effective_access(loader.get_policy(), GovernanceSubject(email="viewer@example.test"))
    assert access.grants.skills_load == frozenset({"a"})


def test_api_user_create_accepts_deny(policy_file, as_user):
    policy_file()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/users", "POST",
        body={
            "email": "new@example.test",
            "entry": {"roles": ["viewer"], "deny": {"cli": {"commands": ["rm"]}}},
        },
        headers={"If-Match": _etag()},
    )
    assert handler.status == 200
    assert loader.get_policy().raw["users"]["new@example.test"]["deny"] == {"cli": {"commands": ["rm"]}}


def test_api_deny_on_bootstrap_admin_refused(policy_file, as_user):
    policy_file()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/users/update", "POST",
        body={"email": BOOTSTRAP, "entry": {"roles": ["admin"], "deny": {"skills": {"load": ["*"]}}}},
        headers={"If-Match": _etag()},
    )
    assert handler.status == 400
    assert "bootstrap admin" in handler.body["message"]
    assert "deny" not in loader.get_policy().raw["users"][BOOTSTRAP]


def test_api_preview_returns_post_deny_grant_detail(policy_file, as_user):
    policy = dict(API_POLICY)
    policy["users"] = dict(API_POLICY["users"])
    policy["users"]["viewer@example.test"] = {
        "roles": ["viewer"],
        "deny": {"skills": {"load": ["b"]}},
    }
    policy_file(policy)
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/preview", "POST", body={"email": "viewer@example.test"},
    )
    assert handler.status == 200
    grants = handler.body["effective_access"]["grants"]
    assert grants["skills"]["load"] == ["a"]
    assert grants["mcp"] == {"servers": []}
    assert grants["cli"] == {"commands": [], "approval_commands": []}


def test_api_deny_must_be_mapping(policy_file, as_user):
    policy_file()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/users/update", "POST",
        body={"email": "viewer@example.test", "entry": {"deny": ["skills"]}},
        headers={"If-Match": _etag()},
    )
    assert handler.status == 400
