from types import SimpleNamespace

import pytest

from api import ownership
from api.governance import loader
from api.governance.models import GovernancePolicy, GovernanceRole, GovernanceUser, GrantSet
from api.governance.nav import navigation_audience
from api.governance.resolver import resolve_effective_access
from api.governance.enforce import subject_from_identity


@pytest.fixture
def member_policy(monkeypatch):
    policy = GovernancePolicy(mode='enforce', users={
        'member@example.test': GovernanceUser(email='member@example.test',
            grants=GrantSet(permissions=frozenset({'sessions:read', 'profiles:read'}), routes=frozenset({'*'}))),
    })
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    ownership._ADMIN_CACHE.clear()
    return policy


def test_route_wildcard_does_not_expose_other_users_rows(member_policy, monkeypatch):
    identity = {'email': 'member@example.test', 'method': 'oidc'}
    monkeypatch.setattr(ownership, '_request_identity', lambda handler: identity)
    assert not ownership.identity_is_admin(identity)
    assert ownership.request_owner_scope(object()) == 'member@example.test'
    assert ownership.row_visible_to('member@example.test', object())
    assert not ownership.row_visible_to('owner@example.test', object())
    assert not ownership.row_visible_to(None, object())


def test_route_wildcard_cannot_open_private_group(member_policy, monkeypatch):
    from api import routes
    identity = {'email': 'member@example.test', 'method': 'oidc'}
    monkeypatch.setattr(ownership, '_request_identity', lambda handler: identity)
    monkeypatch.setattr(routes, '_session_visible_to_active_profile', lambda *args: True)
    session = SimpleNamespace(owner_email='owner@example.test', participants=['someone@example.test'], profile='default')
    assert not routes._session_visible_to_request(session, object())


@pytest.mark.parametrize('role', ['owner', 'admin'])
def test_explicit_administrative_roles_agree_in_ui_and_ownership(monkeypatch, role):
    policy = GovernancePolicy(mode='enforce', roles={role:GovernanceRole(name=role)},
        users={'admin@example.test':GovernanceUser(email='admin@example.test', roles=(role,))})
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    ownership._ADMIN_CACHE.clear()
    identity={'email':'admin@example.test', 'method':'oidc'}
    access=resolve_effective_access(policy, subject_from_identity(identity))
    assert ownership.identity_is_admin(identity)
    assert navigation_audience(access, policy)=='admin'
