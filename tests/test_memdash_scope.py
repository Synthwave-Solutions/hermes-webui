"""Who may see which memory stores: the Wave 1 viewer kind (addendum 6.6.6).

Platform is exactly PLAN 3.6: a bootstrap admin or ``access_level: admin``.
Never ``auth_disabled``, never ``*`` or any other permission, never a role
name alone; ``org_admin`` is always false until A9. Only a policy that says
``installation.kind: hq`` is HQ; elsewhere the platform path needs a live
staff guest grant (X11), refused until X11 wires its checker.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))

import memdash_harness as H  # noqa: E402
from api import memdash_scope as scope  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402

HQ = {"kind": "hq"}
CFG = scope.Config(enabled=True, admin_view=True)


@pytest.fixture(autouse=True)
def _policy():
    yield
    loader.set_policy_loader(None)
    scope.set_staff_guest_checker(None)


def _use(policy: dict):
    parsed = parse_governance_policy(policy)
    loader.set_policy_loader(lambda: parsed)


def _kind(email, *, method="oidc", config=CFG):
    return scope.resolve_viewer(H.identity(email, method=method), config).kind


def test_bootstrap_admin_and_access_level_admin_are_platform_admins_at_hq():
    _use(H.hq_policy(installation=HQ))
    assert _kind(H.MICHAEL) == scope.PLATFORM_ADMIN
    assert _kind(H.YASER) == scope.PLATFORM_ADMIN
    assert _kind(H.ODIS) == scope.PLATFORM_ADMIN
    viewer = scope.resolve_viewer(H.identity(H.YASER), CFG)
    assert viewer.is_hq and viewer.org_id == "" and viewer.mem_admin_claim == "platform" and not viewer.guest


@pytest.mark.parametrize("email", [
    H.HRISHIKESH,   # elevated blacklist account holding "*"
    H.DELIVERY,     # admin_delivery role
    H.OWNERLESS,    # an owner role without an access level
    H.ADA,          # a member
    "stranger@example.test",
])
def test_wildcards_roles_and_members_are_members(email):
    _use(H.hq_policy(installation=HQ))
    assert _kind(email) == scope.MEMBER


def test_auth_disabled_identity_is_a_member_even_for_the_bootstrap_email():
    _use(H.hq_policy(installation=HQ))
    assert _kind(H.MICHAEL, method="auth_disabled") == scope.MEMBER


def test_org_admin_is_never_given_in_wave_1():
    policy = H.hq_policy(installation={"kind": "client"}, organization={"id": "org_acme", "name": "Acme"})
    policy["organization"]["admins"] = [H.ADA]
    _use(policy)
    for email in (H.ADA, H.BOB, H.YASER):
        assert _kind(email) != scope.ORG_ADMIN


def test_a_policy_load_error_raises_scope_unavailable():
    def broken():
        raise RuntimeError("unreadable")
    loader.set_policy_loader(broken)
    with pytest.raises(scope.ScopeUnavailable):
        scope.resolve_viewer(H.identity(H.MICHAEL), CFG)


@pytest.mark.parametrize("installation", [None, {"kind": "client"}, {"kind": "HQ"}, {"kind": ""}, {"name": "hq"}, "hq"])
def test_only_installation_kind_hq_is_hq(installation):
    policy = H.hq_policy()
    if installation is not None:
        policy["installation"] = installation
    try:
        _use(policy)
    except loader.GovernancePolicyError:
        # The integrated organization parser rejects malformed installation blocks.
        return
    viewer = scope.resolve_viewer(H.identity(H.MICHAEL), CFG)
    assert not viewer.is_hq
    # A client installation: the platform path needs a live staff guest grant.
    assert viewer.kind == scope.MEMBER


def test_client_installation_platform_admin_needs_a_live_staff_guest_grant():
    _use(H.hq_policy(installation={"kind": "client"}, organization={"id": "org_acme", "name": "Acme"}))
    assert _kind(H.YASER) == scope.MEMBER
    scope.set_staff_guest_checker(lambda identity: identity.get("email") == H.YASER)
    viewer = scope.resolve_viewer(H.identity(H.YASER), CFG)
    assert viewer.kind == scope.PLATFORM_ADMIN and viewer.guest and viewer.org_id == "org_acme"
    # A grant never makes a non-platform user an admin.
    scope.set_staff_guest_checker(lambda identity: True)
    assert _kind(H.ADA) == scope.MEMBER
    # A failing checker refuses.
    def broken(identity):
        raise RuntimeError("down")
    scope.set_staff_guest_checker(broken)
    assert _kind(H.YASER) == scope.MEMBER


def test_platform_admins_view_switch_off_gives_member():
    _use(H.hq_policy(installation=HQ))
    config = scope.Config(enabled=True, admin_view=True, view_platform_admins=False)
    assert _kind(H.MICHAEL, config=config) == scope.MEMBER


def test_config_defaults_and_overrides(monkeypatch):
    import api.config as api_config

    monkeypatch.setattr(api_config, "load_settings", lambda: {})
    monkeypatch.delenv("HERMES_WEBUI_MEMDASH", raising=False)
    monkeypatch.delenv("HERMES_WEBUI_MNEMO_ADMIN_VIEW", raising=False)
    config = scope.load_config()
    assert config == scope.Config()
    assert not config.enabled and not config.admin_view and not config.edit_personal
    assert config.mask_secrets and config.view_org_admins and config.view_platform_admins
    assert config.retention_days == 730
    monkeypatch.setattr(api_config, "load_settings", lambda: {
        "memdash_enabled": True, "memory_admin_edit_personal": True, "memory_admin_mask_secrets": False,
        "memory_access_log_retention_days": 5})
    config = scope.load_config()
    assert config.enabled and config.edit_personal and not config.mask_secrets and config.retention_days == 30
    monkeypatch.setenv("HERMES_WEBUI_MEMDASH", "0")
    monkeypatch.setenv("HERMES_WEBUI_MNEMO_ADMIN_VIEW", "1")
    config = scope.load_config()
    assert not config.enabled and config.admin_view
    monkeypatch.setenv("HERMES_WEBUI_MNEMO_ADMIN_VIEW", "true")
    assert not scope.load_config().admin_view  # only the exact value 1 switches it on

    def broken():
        raise OSError("unreadable")
    monkeypatch.setattr(api_config, "load_settings", broken)
    monkeypatch.delenv("HERMES_WEBUI_MEMDASH", raising=False)
    assert not scope.load_config().enabled
