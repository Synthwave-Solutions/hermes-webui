"""Implicit remembered workspaces recover without granting explicit access."""
import io
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from api import config, routes, workspace, workspace_access
from api.governance import enforce, loader


@pytest.fixture
def state(tmp_path, monkeypatch):
    safe = tmp_path / 'safe'; safe.mkdir()
    private = tmp_path / 'private'; private.mkdir()
    home = tmp_path / 'home'; home.mkdir()
    registry = tmp_path / 'workspaces.json'
    rows = [{'name': 'Safe', 'path': str(safe)},
            {'name': 'Private', 'path': str(private), 'owner_email': 'owner@example.test', 'members': []}]
    registry.write_text(json.dumps(rows))
    remembered = tmp_path / 'last_workspace.txt'; remembered.write_text(str(private))
    identity = {'email': 'reader@example.test', 'groups': [], 'method': 'qa'}
    raw = {'mode': 'enforce', 'roles': {'member': {'grants': {'workspaces': ['*']}}},
           'users': {identity['email']: {'roles': ['member'], 'access_mode': 'blacklist', 'access_level': 'user'}}}
    monkeypatch.setattr(loader, 'get_policy', lambda: loader.parse_governance_policy(raw))
    monkeypatch.setattr(enforce, '_request_identity', lambda _: identity)
    monkeypatch.setattr(workspace, '_workspaces_file', lambda: registry)
    monkeypatch.setattr(workspace, '_last_workspace_file', lambda: remembered)
    monkeypatch.setattr(workspace, '_profile_default_workspace', lambda: str(safe))
    monkeypatch.setattr(workspace, '_remote_terminal_cwd', lambda: None)
    monkeypatch.setattr(workspace, '_remote_terminal_workspace_candidate', lambda _: None)
    monkeypatch.setattr(workspace, '_home_path', lambda: home)
    monkeypatch.setattr(workspace, '_BOOT_DEFAULT_WORKSPACE', safe)
    monkeypatch.setattr(config, 'DEFAULT_WORKSPACE', safe)
    monkeypatch.setattr(routes, '_check_csrf', lambda _: True)
    monkeypatch.setattr(routes, '_guard_request_session_visibility', lambda *a, **k: True)
    monkeypatch.setattr('api.bot_builder.guard_profile_request', lambda *a: True)
    monkeypatch.setattr(routes.governance_api, 'handle_governance_api', lambda *a: False)
    monkeypatch.setattr(routes, '_handle_extension_sidecar_proxy', lambda *a, **k: False)
    created = []

    def create(**values):
        created.append(values)
        return SimpleNamespace(session_id='new-qa', profile='default', messages=[], save=lambda: None,
                               compact=lambda: {'session_id': 'new-qa', 'workspace': values['workspace']})

    monkeypatch.setattr(routes, 'new_session', create)
    return SimpleNamespace(safe=safe, private=private, registry=registry, rows=rows,
                           remembered=remembered, raw=raw, identity=identity, created=created)


def request(path, body=None):
    handler = SimpleNamespace(path=path, command='POST' if body is not None else 'GET', headers={},
                              wfile=io.BytesIO(), status=None)
    raw = json.dumps(body).encode() if body is not None else b''
    handler.rfile = io.BytesIO(raw); handler.headers['Content-Length'] = str(len(raw))
    handler.send_response = lambda status: setattr(handler, 'status', status)
    handler.send_header = lambda *a: None; handler.end_headers = lambda: None
    (routes.handle_post if body is not None else routes.handle_get)(handler, urlsplit(path))
    return handler.status, json.loads(handler.wfile.getvalue())


def test_boot_and_implicit_creation_use_authorized_fallback_without_state_mutation(state):
    before = state.registry.read_bytes(), state.remembered.read_bytes()
    assert request('/api/profile/active')[1]['default_workspace'] == str(state.safe)
    status, body = request('/api/session/new', {})
    assert status == 200
    assert body['session']['workspace'] == str(state.safe)
    assert state.created[0]['workspace'] == str(state.safe)
    assert (state.registry.read_bytes(), state.remembered.read_bytes()) == before
    assert request('/api/session/new', {'workspace': str(state.private)})[0] == 403
    assert len(state.created) == 1


def test_membership_revocation_changes_only_actor_projection(state):
    state.rows[1]['members'] = [state.identity['email']]
    state.registry.write_text(json.dumps(state.rows))
    assert request('/api/profile/active')[1]['default_workspace'] == str(state.private)
    state.rows[1]['members'] = []
    state.registry.write_text(json.dumps(state.rows))
    assert request('/api/profile/active')[1]['default_workspace'] == str(state.safe)
    assert state.remembered.read_text() == str(state.private)


def test_existing_but_unregistered_remembered_directory_is_not_trusted(state):
    state.rows.pop(); state.registry.write_text(json.dumps(state.rows))
    assert state.private.is_dir()
    assert request('/api/profile/active')[1]['default_workspace'] == str(state.safe)
    assert request('/api/session/new', {})[1]['session']['workspace'] == str(state.safe)
    assert request('/api/session/new', {'workspace': str(state.private)})[0] == 400
    assert state.remembered.read_text() == str(state.private)


def test_governance_workspace_denial_applies_to_fallback_candidates(state):
    state.raw['users'][state.identity['email']]['deny'] = {'workspaces': ['Safe']}
    assert request('/api/profile/active')[1]['default_workspace'] is None
    assert request('/api/session/new', {})[0] == 403
    assert state.created == []


def test_saved_authorized_candidate_recovers_when_configured_default_is_denied(state):
    state.rows[1]['members'] = [state.identity['email']]
    state.registry.write_text(json.dumps(state.rows))
    state.raw['users'][state.identity['email']]['deny'] = {'workspaces': ['Safe']}
    assert workspace_access.resolve_implicit_workspace(SimpleNamespace(), preferred=str(state.safe)) == str(state.private)


def test_corrupt_acl_does_not_fall_back_to_shared_default(state):
    state.registry.write_text('{ invalid')
    assert request('/api/profile/active')[1]['default_workspace'] is None
    assert request('/api/session/new', {})[0] == 403
    assert state.created == []


@pytest.mark.parametrize('previous_profile', [None, 'original'])
@pytest.mark.parametrize('available', [True, False])
def test_switch_resolves_target_registry_and_restores_request_scope(
        state, tmp_path, monkeypatch, previous_profile, available):
    from api import profiles

    target_safe = tmp_path / 'target-safe'; target_safe.mkdir()
    target_registry = tmp_path / 'target-workspaces.json'
    target_registry.write_text(json.dumps([
        {'name': 'Target safe', 'path': str(target_safe)}, state.rows[1]]))
    monkeypatch.setattr(profiles, '_active_profile', 'process-default')
    monkeypatch.setattr(profiles._tls, 'profile', previous_profile)
    monkeypatch.setattr(workspace, '_workspaces_file', lambda:
                        target_registry if getattr(profiles._tls, 'profile', None) == 'target'
                        else state.registry)
    monkeypatch.setattr(workspace, '_profile_default_workspace', lambda:
                        str(target_safe) if getattr(profiles._tls, 'profile', None) == 'target'
                        else str(state.safe))
    switches = []

    def switch(name, *, process_wide):
        switches.append((name, process_wide, getattr(profiles._tls, 'profile', None)))
        return {'active': name, 'default_workspace': str(state.private)}

    monkeypatch.setattr(profiles, 'switch_profile', switch)
    monkeypatch.setattr(config, 'invalidate_models_cache', lambda: None)
    monkeypatch.setattr('api.gateway_watcher.restart_watcher_for_profile', lambda _: None)
    monkeypatch.setattr('api.helpers.build_profile_cookie', lambda *a: 'qa-profile=target')
    state.raw['roles']['member']['grants']['profiles'] = ['*']
    if not available:
        state.raw['users'][state.identity['email']]['deny'] = {'workspaces': ['*']}
    before = (state.registry.read_bytes(), target_registry.read_bytes(),
              state.remembered.read_bytes())

    status, payload = request('/api/profile/switch', {'name': 'target'})

    assert status == 200
    assert payload['active'] == 'target'
    assert payload['default_workspace'] == (str(target_safe) if available else None)
    assert switches == [('target', False, previous_profile)]
    assert getattr(profiles._tls, 'profile', None) == previous_profile
    assert profiles._active_profile == 'process-default'
    assert (state.registry.read_bytes(), target_registry.read_bytes(),
            state.remembered.read_bytes()) == before
    # Projection must never turn an explicitly requested foreign directory into
    # an authorized session, even when a safe implicit fallback was available.
    assert request('/api/session/new', {'workspace': str(state.private)})[0] == 403
    assert state.created == []
