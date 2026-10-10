"""Reserved permission namespaces (plan 3.6 and 3.11, package W3a).

org:, billing:, departments:, support:, a2a: and screen: are control-plane
names. A wildcard never reaches them, neither in EffectiveAccess.allows nor
in the resolver's level ceiling nor through a whitelist intersection, so an
elevated blacklist account holding the operational "*" (the wildcard-leak
regression subject power.user@acme.example in the shared org_acme fixture)
gets none of them. Inside a namespace a glob still works ("a2a:call:*"),
except screen:, which only an entry naming the permission exactly grants.
"""
import copy
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import resolver  # noqa: E402
from api.governance.catalog import RouteRule  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.governance.models import GrantSet, GovernanceSubject, intersect_grants  # noqa: E402
from api.governance.resolver import resolve_effective_access  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "managed_service" / "org_acme.yaml"

RESERVED = (
    "org:read",
    "org:members:write",
    "billing:read",
    "departments:read",
    "departments:sales:write",
    "support:tickets",
    "a2a:call:acme-inst_a/sales-bot",
    "a2a:serve:sales-bot",
    "screen:watch",
    "screen:takeover",
    "screen:admin",
)
SCREEN = ("screen:watch", "screen:takeover", "screen:admin")


def _fixture_policy() -> dict:
    return copy.deepcopy(yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["policy"])


def _access(raw: dict, email: str):
    return resolve_effective_access(parse_governance_policy(raw), GovernanceSubject(email=email))


def _with_user(raw: dict, email: str, entry: dict) -> dict:
    raw = copy.deepcopy(raw)
    raw["users"][email] = entry
    return raw


# ── The wildcard-leak regression ─────────────────────────────────────────────

def test_elevated_blacklist_user_with_wildcard_gets_no_reserved_permission():
    access = _access(_fixture_policy(), "power.user@acme.example")
    assert "*" in access.permissions, "the regression subject must hold the operational wildcard"
    for name in RESERVED:
        assert not access.has_permission(name), name
    # Ordinary permissions still follow the wildcard.
    assert access.has_permission("chat:use")
    assert access.has_permission("files:read")


def test_bootstrap_and_admin_level_wildcards_do_not_reach_reserved_names():
    raw = _fixture_policy()
    for email in ("ops@synthwave.example", "it.admin@acme.example"):
        access = _access(raw, email)
        assert "*" in access.permissions, email
        for name in RESERVED:
            assert not access.has_permission(name), (email, name)
        assert access.has_permission("governance:write"), email


def test_explicit_grant_still_works_outside_the_screen_namespace():
    raw = _with_user(_fixture_policy(), "support.lead@acme.example", {
        "roles": ["operator"],
        "grants": {"permissions": ["org:*", "a2a:call:*", "support:tickets"]},
    })
    access = _access(raw, "support.lead@acme.example")
    assert access.has_permission("org:read")
    assert access.has_permission("org:members:write")
    assert access.has_permission("a2a:call:acme-inst_a/sales-bot")
    assert access.has_permission("support:tickets")
    assert not access.has_permission("support:admin")
    assert not access.has_permission("billing:read")
    assert not access.has_permission("a2a:serve:sales-bot")


# ── screen: is exact-name only ───────────────────────────────────────────────

def test_screen_glob_grants_nothing():
    raw = _with_user(_fixture_policy(), "screen.glob@acme.example", {
        "roles": ["operator"],
        "grants": {"permissions": ["screen:*", "screen:?atch", "scr*"]},
    })
    access = _access(raw, "screen.glob@acme.example")
    for name in SCREEN:
        assert not access.has_permission(name), name


def test_exact_screen_grant_gives_exactly_that_one():
    raw = _with_user(_fixture_policy(), "watcher@acme.example", {
        "roles": ["operator"],
        "grants": {"permissions": ["screen:watch"]},
    })
    access = _access(raw, "watcher@acme.example")
    assert access.has_permission("screen:watch")
    assert not access.has_permission("screen:takeover")
    assert not access.has_permission("screen:admin")


def test_blacklist_user_with_an_exact_screen_grant_gets_only_that_one():
    raw = _fixture_policy()
    raw["users"]["power.user@acme.example"]["grants"] = {"permissions": ["screen:takeover"]}
    access = _access(raw, "power.user@acme.example")
    assert access.has_permission("screen:takeover")
    assert not access.has_permission("screen:watch")
    assert not access.has_permission("screen:admin")


# ── Denies stay broad ────────────────────────────────────────────────────────

def test_a_deny_still_removes_an_explicit_reserved_grant():
    raw = _with_user(_fixture_policy(), "denied@acme.example", {
        "access_level": "elevated",
        "access_mode": "blacklist",
        "roles": ["operator"],
        "grants": {"permissions": ["screen:watch", "org:read"]},
        "deny": {"permissions": ["screen:*", "org:read"]},
    })
    access = _access(raw, "denied@acme.example")
    assert not access.has_permission("screen:watch")
    assert not access.has_permission("org:read")


# ── Defence in depth: level ceiling and whitelist intersection ───────────────

def test_level_ceiling_never_pulls_a_reserved_catalog_permission_through_a_wildcard(monkeypatch):
    from api.governance import catalog

    extra = (
        RouteRule("/api/test-screen", "screen:watch"),
        RouteRule("/api/test-org", "org:read"),
        RouteRule("/api/test-files", "files:read"),
    )
    monkeypatch.setattr(catalog, "ROUTE_CATALOG", tuple(catalog.ROUTE_CATALOG) + extra)
    ceiling = resolver._level_ceiling(GrantSet(permissions=frozenset({"*"})), "elevated")
    assert "files:read" in ceiling.permissions
    assert "screen:watch" not in ceiling.permissions
    assert "org:read" not in ceiling.permissions
    explicit = resolver._level_ceiling(GrantSet(permissions=frozenset({"*", "screen:watch", "org:*"})), "elevated")
    assert "screen:watch" in explicit.permissions
    assert "org:read" in explicit.permissions


def test_whitelist_wildcard_does_not_admit_a_reserved_role_grant():
    raw = _fixture_policy()
    raw["roles"]["org_reader"] = {"grants": {"permissions": ["chat:use", "org:read", "screen:watch"]}}
    raw = _with_user(raw, "listed@acme.example", {
        "access_level": "elevated",
        "access_mode": "whitelist",
        "roles": ["org_reader"],
        "grants": {"permissions": ["*"]},
    })
    access = _access(raw, "listed@acme.example")
    assert access.has_permission("chat:use")
    assert not access.has_permission("org:read")
    assert not access.has_permission("screen:watch")


def test_intersection_keeps_a_reserved_name_both_sides_grant():
    left = GrantSet(permissions=frozenset({"org:read", "chat:use"}))
    right = GrantSet(permissions=frozenset({"org:*", "*"}))
    assert intersect_grants(left, right).permissions == frozenset({"org:read", "chat:use"})
    assert intersect_grants(GrantSet(permissions=frozenset({"*"})), GrantSet(
        permissions=frozenset({"org:read", "chat:use"}))).permissions == frozenset({"chat:use"})


# ── The matcher itself ───────────────────────────────────────────────────────

@pytest.mark.parametrize("name", RESERVED)
def test_reserved_names_are_recognised(name):
    from api.governance.models import permission_matches, reserved_namespace

    assert reserved_namespace(name)
    assert not permission_matches({"*"}, name)
    assert not permission_matches({"*:*", "?*", "[a-z]*"}, name)


def test_reserved_detection_ignores_case_so_a_wildcard_cannot_reach_a_cased_name():
    from api.governance.models import permission_matches, reserved_namespace

    for name in ("ORG:read", "Screen:Watch", "A2A:call:x"):
        assert reserved_namespace(name)
        assert not permission_matches({"*"}, name)


def test_ordinary_names_keep_the_existing_matcher():
    from api.governance.models import permission_matches, reserved_namespace

    assert permission_matches({"*"}, "chat:use")
    assert permission_matches({"files:*"}, "files:read")
    assert not permission_matches({"files:*"}, "chat:use")
    # A name that merely contains a reserved word is not reserved.
    assert not reserved_namespace("reports:org:read")
    assert permission_matches({"*"}, "reports:org:read")
