"""Workspace membership is independent of broad role/path grants and live sessions."""
import io
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from api import routes, workspace, personal_file_guard
from api.governance import enforce, loader, resource_access


@pytest.fixture
def scope(tmp_path, monkeypatch):
    root = tmp_path / 'shared'; root.mkdir()
    private = root / 'private'; private.mkdir()
    (private / 'private.txt').write_text('PRIVATE_WORKSPACE_MARKER')
    state = tmp_path / 'workspaces.json'
    rows = [{'name': 'Shared', 'path': str(root)},
            {'name': 'Private', 'path': str(private), 'owner_email': 'owner@example.test', 'members': []}]
    state.write_text(json.dumps(rows))
    monkeypatch.setattr(workspace, '_workspaces_file', lambda: state)
    identity = {'email': 'member@example.test', 'groups': [], 'method': 'qa'}
    monkeypatch.setattr(enforce, '_request_identity', lambda _: identity)
    policy = loader.parse_governance_policy({'mode': 'report_only', 'users': {identity['email']: {
        'grants': {'workspaces': ['*'], 'file_read_roots': ['*'], 'file_write_roots': ['*']}}}})
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    monkeypatch.setattr(routes, 'load_workspaces', lambda: json.loads(state.read_text()))
    session = SimpleNamespace(workspace=str(private), worktree_repo_root=None)
    monkeypatch.setattr(routes, 'get_session_for_file_ops', lambda _: session)
    monkeypatch.setattr(routes, '_get_or_materialize_session', lambda _: session)
    monkeypatch.setattr(routes, '_check_csrf', lambda _: True)
    monkeypatch.setattr(routes, '_guard_request_session_visibility', lambda *a, **k: True)
    monkeypatch.setattr('api.bot_builder.guard_profile_request', lambda *a: True)
    monkeypatch.setattr(routes.governance_api, 'handle_governance_api', lambda *a: False)
    monkeypatch.setattr(routes, '_handle_extension_sidecar_proxy', lambda *a, **k: False)
    monkeypatch.setattr(routes, 'resolve_trusted_workspace', lambda p: p)
    monkeypatch.setattr(routes, 'get_last_workspace', lambda: str(private))
    return SimpleNamespace(root=root, private=private, state=state, rows=rows, session=session, identity=identity)


def request(path, body=None):
    handler = SimpleNamespace(path=path, command='POST' if body is not None else 'GET', headers={},
                              wfile=io.BytesIO(), status=None)
    raw = json.dumps(body).encode() if body is not None else b''
    handler.rfile = io.BytesIO(raw); handler.headers['Content-Length'] = str(len(raw))
    handler.send_response = lambda status: setattr(handler, 'status', status)
    handler.send_header = lambda *a: None; handler.end_headers = lambda: None
    (routes.handle_post if body is not None else routes.handle_get)(handler, urlsplit(path))
    return handler


def test_name_or_wildcard_grant_never_replaces_membership(scope):
    assert [r['name'] for r in routes._workspaces_response_list(scope.rows, SimpleNamespace())] == ['Shared']


@pytest.mark.parametrize('body', [{'workspace': 'PRIVATE'}, {}])
def test_explicit_and_last_workspace_session_creation_denied_before_side_effect(scope, monkeypatch, body):
    body = {'workspace': str(scope.private)} if body else body
    monkeypatch.setattr(routes, 'new_session', lambda **_: pytest.fail('unauthorized session creation'))
    assert request('/api/session/new', body).status == 403


def test_workspace_switch_denied_before_session_mutation(scope, monkeypatch):
    scope.session.workspace = str(scope.root)
    monkeypatch.setattr(routes, '_get_session_agent_lock', lambda _: pytest.fail('unauthorized session mutation'))
    assert request('/api/session/update', {'session_id': 'qa', 'workspace': str(scope.private)}).status == 403
    assert scope.session.workspace == str(scope.root)


@pytest.mark.parametrize('route,values', [('/api/file', {'path': 'private.txt'}),
    ('/api/list', {'path': '.'}), ('/api/file/save', {'path': 'private.txt', 'content': 'FORBIDDEN'}),
    ('/api/folder/download', {'path': '.'})])
def test_retained_session_file_requests_check_current_membership(scope, route, values):
    scope.rows[1]['members'] = ['member@example.test']; scope.state.write_text(json.dumps(scope.rows))
    personal_file_guard.guard_request(SimpleNamespace(), route, {'session_id': 'qa', **values})
    scope.rows[1]['members'] = []; scope.state.write_text(json.dumps(scope.rows))
    with pytest.raises(PermissionError):
        personal_file_guard.guard_request(SimpleNamespace(), route, {'session_id': 'qa', **values})
    assert (scope.private / 'private.txt').read_text() == 'PRIVATE_WORKSPACE_MARKER'


def test_shared_parent_does_not_expose_private_child_or_symlink(scope):
    link = scope.root / 'alias'; link.symlink_to(scope.private, target_is_directory=True)
    for path in [scope.private / 'private.txt', link / 'private.txt']:
        assert resource_access.file_allowed(scope.identity, path) is False
    assert resource_access.filter_file_entries(scope.identity, scope.root,
        [{'path': 'private'}, {'path': 'alias'}, {'path': 'public.txt'}]) == [{'path': 'public.txt'}]


def test_owner_member_and_unowned_keep_access(scope):
    scope.identity['email'] = ' OWNER@example.test '
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt')
    scope.identity['email'] = 'member@example.test'
    scope.rows[1]['members'] = [' MEMBER@example.test ']; scope.state.write_text(json.dumps(scope.rows))
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt')
    scope.rows[1].pop('owner_email'); scope.rows[1]['members'] = []; scope.state.write_text(json.dumps(scope.rows))
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt')


def test_unreadable_acl_fails_closed_without_hiding_admin_recovery(scope, monkeypatch):
    scope.state.write_text('{ invalid json')
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt') is False
    monkeypatch.setattr('api.ownership.identity_is_admin', lambda _: True)
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt') is True


@pytest.mark.parametrize('route', ['/api/chat/start', '/api/chat', '/api/chat/steer',
    '/api/terminal/start', '/api/terminal/input', '/api/terminal/resize', '/api/git/status'])
def test_retained_workspace_execution_routes_deny_before_dispatch(scope, route):
    response = request(route + '?session_id=qa') if route.endswith('/status') else request(route, {'session_id': 'qa'})
    assert response.status == 403


def test_workspace_catalog_hides_private_last_path(scope, monkeypatch):
    monkeypatch.setattr(routes, '_terminal_remote_backend_enabled', lambda: False)
    response = request('/api/workspaces')
    body = json.loads(response.wfile.getvalue())
    assert response.status == 200
    assert body['last'] == str(scope.root)
    assert str(scope.private) not in json.dumps(body)


def test_invalid_registry_catalog_is_not_treated_as_shared_default(scope):
    scope.state.write_text('{ invalid')
    assert request('/api/workspaces').status == 403


def test_unowned_child_cannot_clear_ancestor_membership(scope):
    child = scope.private / 'nested'
    scope.rows.append({'name': 'Unowned child', 'path': str(child)})
    scope.state.write_text(json.dumps(scope.rows))
    assert resource_access.file_allowed(scope.identity, child / 'secret.txt') is False


def test_member_only_acl_is_not_legacy_unowned(scope):
    scope.rows[1].pop('owner_email'); scope.rows[1]['members'] = ['someone@example.test']
    scope.state.write_text(json.dumps(scope.rows))
    assert resource_access.file_allowed(scope.identity, scope.private / 'private.txt') is False


def test_worktree_source_membership_still_required(scope):
    scope.session.workspace = str(scope.root / 'outside-worktree')
    scope.session.worktree_repo_root = str(scope.private)
    with pytest.raises(PermissionError):
        personal_file_guard.guard_request(SimpleNamespace(), '/api/file', {'session_id': 'qa', 'path': 'file.txt'})


@pytest.mark.parametrize('parent_session', [False, True])
def test_workspace_upload_blocks_revoked_session_and_private_child(scope, monkeypatch, parent_session):
    from api import upload
    if parent_session:
        scope.session.workspace = str(scope.root)
    monkeypatch.setattr(upload, 'get_session', lambda _: scope.session)
    monkeypatch.setattr(upload, '_reject_invisible_session', lambda *a: False)
    monkeypatch.setattr(upload, 'resolve_trusted_workspace', lambda p: scope.root if parent_session else scope.private)
    monkeypatch.setattr(upload, 'parse_multipart', lambda *a: (
        {'session_id': 'qa', 'path': 'private' if parent_session else ''}, {'file': ('upload.txt', b'FORBIDDEN')}))
    handler = SimpleNamespace(headers={}, rfile=io.BytesIO(), wfile=io.BytesIO(), status=None)
    handler.send_response = lambda status: setattr(handler, 'status', status)
    handler.send_header = lambda *a: None; handler.end_headers = lambda: None
    upload.handle_workspace_upload(handler)
    assert handler.status == 403
    assert not (scope.private / 'upload.txt').exists()


@pytest.mark.parametrize('grants,denied,allow', [(['Private'], [], True), (['Elsewhere'], [], False),
    (['*'], ['Private'], False), (['PATH'], [], True), (['*'], ['PATH'], False)])
def test_workspace_resource_grants_and_denies_remain_additional_ceiling(scope, monkeypatch, grants, denied, allow):
    from api.workspace_access import ensure_workspace_selection
    scope.rows[1]['members'] = ['member@example.test']; scope.state.write_text(json.dumps(scope.rows))
    replace = lambda values: [str(scope.private) if value == 'PATH' else value for value in values]
    policy = loader.parse_governance_policy({'mode': 'enforce', 'users': {scope.identity['email']: {
        'grants': {'workspaces': replace(grants)}, 'deny': {'workspaces': replace(denied)}}}})
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    if allow:
        ensure_workspace_selection(SimpleNamespace(), scope.private)
    else:
        with pytest.raises(PermissionError):
            ensure_workspace_selection(SimpleNamespace(), scope.private)


def test_runtime_callback_captures_principal_and_root_checks_live_acl_and_restores_tls(scope, monkeypatch):
    import os
    from api import profiles
    from api.workspace_access import runtime_workspace_scope
    scope.session.profile = 'qa-private-profile'
    scope.rows[1]['members'] = ['member@example.test']; scope.state.write_text(json.dumps(scope.rows))
    seen = []
    monkeypatch.setattr(workspace, '_workspaces_file', lambda: (seen.append(profiles.get_active_profile_name()) or scope.state))
    profiles.set_request_profile('prior-profile')
    previous_env = dict(os.environ)
    try:
        root, check = runtime_workspace_scope(scope.session, scope.identity)
        assert root == str(scope.private)
        assert check(scope.root / 'outside.txt') is True
        assert profiles.get_active_profile_name() == 'prior-profile'
        scope.identity['email'] = 'owner@example.test'  # Captured principal cannot be substituted.
        scope.rows[1]['members'] = []; scope.state.write_text(json.dumps(scope.rows))
        with pytest.raises(PermissionError):
            check(scope.root / 'outside.txt')
        assert profiles.get_active_profile_name() == 'prior-profile'
        assert seen and set(seen) == {'qa-private-profile'}
        assert dict(os.environ) == previous_env
    finally:
        profiles.clear_request_profile()


def test_runtime_callback_checks_actual_nested_target_and_resolved_workspace_override(scope):
    from api.workspace_access import runtime_workspace_scope
    root, check = runtime_workspace_scope(scope.session, scope.identity, workspace=str(scope.root))
    assert root == str(scope.root)
    assert check(scope.root / 'public.txt') is True
    with pytest.raises(PermissionError):
        check(scope.private / 'private.txt')


@pytest.mark.parametrize('change', ['revoke', 'blacklist'])
def test_retained_member_runtime_and_http_recheck_live_workspace_policy(scope, monkeypatch, change):
    from api.workspace_access import runtime_workspace_scope
    scope.rows[1]['members'] = ['member@example.test']; scope.state.write_text(json.dumps(scope.rows))
    raw = {'mode': 'enforce', 'users': {scope.identity['email']: {'grants': {'workspaces': ['Private']}}}}
    monkeypatch.setattr(loader, 'get_policy', lambda: loader.parse_governance_policy(raw))
    _, check = runtime_workspace_scope(scope.session, scope.identity)
    assert check(scope.private / 'private.txt') is True
    if change == 'revoke':
        raw['users'][scope.identity['email']]['grants']['workspaces'] = ['Elsewhere']
    else:
        raw['users'][scope.identity['email']]['deny'] = {'workspaces': ['Private']}
    with pytest.raises(PermissionError):
        check(scope.private / 'private.txt')
    assert request('/api/terminal/start', {'session_id': 'qa'}).status == 403
    with pytest.raises(PermissionError):
        personal_file_guard.guard_request(SimpleNamespace(), '/api/file', {'session_id': 'qa', 'path': 'private.txt'})
