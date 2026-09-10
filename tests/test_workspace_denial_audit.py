"""Denied owned-session execution has useful, bounded, non-content diagnostics."""
import hashlib
import io
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from api import auth, ownership, routes, workspace, workspace_access
from api.governance import audit


@pytest.fixture
def denied(tmp_path, monkeypatch):
    actor = 'member@example.test'
    registry = tmp_path / 'workspaces.json'
    private = tmp_path / 'private-customer-path-canary'
    private.mkdir()
    registry.write_text(json.dumps([{'path': str(private),
                                    'owner_email': 'other@example.test', 'members': []}]))
    log = tmp_path / 'audit.jsonl'
    monkeypatch.setattr(workspace, '_workspaces_file', lambda: registry)
    monkeypatch.setattr(audit, '_audit_file', lambda: log)
    monkeypatch.setattr(ownership, 'request_owner_scope', lambda _: actor)
    monkeypatch.setattr(auth, 'is_auth_enabled', lambda: True)
    monkeypatch.setattr(auth, 'parse_cookie', lambda _: 'synthetic-cookie-canary')
    monkeypatch.setattr(auth, 'get_session_identity', lambda _: {
        'email': ' MEMBER@example.test ',
        'method': 'sso', 'claims_subset': {'sub': 'synthetic-subject-canary'}})
    session = SimpleNamespace(session_id='current-owned-session', profile='steve',
                              owner_email=actor, workspace=str(private), worktree_repo_root=None)
    monkeypatch.setattr(routes, 'get_session_for_file_ops', lambda _: session)
    handler = SimpleNamespace(wfile=io.BytesIO(), status=None, command='POST')
    handler.send_response = lambda value: setattr(handler, 'status', value)
    handler.send_header = lambda *args: None
    handler.end_headers = lambda: None
    return SimpleNamespace(handler=handler, session=session, registry=registry, log=log)


def request(fixture, body=None, path='/api/chat/start?secret=query-canary'):
    return workspace_access.guard_session_request(fixture.handler, urlsplit(path),
        body or {'session_id': 'request-alias-canary', 'message': 'private-prompt-canary',
                 'tool_args': {'token': 'credential-canary'}})


@pytest.mark.parametrize('malformed', [False, True])
def test_real_acl_denial_audits_current_owned_session_without_request_contents(denied, malformed):
    if malformed:
        denied.registry.write_text('{ invalid')
    assert request(denied) is False
    assert denied.handler.status == 403
    reason = 'unavailable' if malformed else 'required'
    assert json.loads(denied.handler.wfile.getvalue()) == {'error': 'Workspace membership ' + reason}
    raw = denied.log.read_text()
    row = json.loads(raw)
    assert row['event'] == 'deny' and row['mode'] == 'enforce'
    assert row['path'] == '/api/chat/start' and row['method'] == 'POST'
    assert row['reason'] == 'workspace_membership_' + reason
    assert row['subject_email_hash'] == hashlib.sha256(b'member@example.test').hexdigest()[:24]
    assert row['subject_user_id_hash'] == hashlib.sha256(b'synthetic-subject-canary').hexdigest()[:24]
    assert row['extra'] == {'session_id': 'current-owned-session', 'profile': 'steve'}
    for private in ['member@example.test', 'other@example.test', 'private-customer-path-canary',
                    'synthetic-cookie-canary', 'synthetic-subject-canary', 'request-alias-canary',
                    'query-canary', 'private-prompt-canary', 'credential-canary', 'tool_args']:
        assert private not in raw


@pytest.mark.parametrize('owner', ['other@example.test', '', None])
def test_foreign_or_unowned_session_is_not_added_to_actor_audit(denied, owner):
    denied.session.owner_email = owner
    assert request(denied) is False
    assert denied.handler.status == 403
    assert not denied.log.exists()


def test_missing_session_defers_to_endpoint_validation_without_audit(denied, monkeypatch):
    def missing(_):
        raise KeyError('unknown-session')
    monkeypatch.setattr(routes, 'get_session_for_file_ops', missing)
    assert request(denied) is True
    assert denied.handler.status is None
    assert not denied.log.exists()


def test_audit_failure_cannot_allow_execution_or_change_http_denial(denied, monkeypatch):
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(kwargs)
        raise OSError('private-audit-path-canary')
    monkeypatch.setattr(audit, 'append_audit_event', unavailable)
    dispatched = []
    if request(denied):
        dispatched.append('execution')
    assert len(calls) == 1 and dispatched == []
    assert denied.handler.status == 403
    assert json.loads(denied.handler.wfile.getvalue()) == {'error': 'Workspace membership required'}


@pytest.mark.parametrize(('message', 'reason'), [
    ('Workspace explicitly denied by governance', 'workspace_explicitly_denied'),
    ("Workspace is outside the user's governed scope", 'workspace_outside_governed_scope'),
    ('Workspace governance unavailable', 'workspace_governance_unavailable'),
    ('sensitive-unrecognized-reason-canary', 'workspace_access_denied'),
])
def test_other_reasons_are_static_and_never_copy_arbitrary_exception_details(denied, monkeypatch, message, reason):
    def refusal(*_):
        raise PermissionError(message)
    monkeypatch.setattr(workspace_access, 'ensure_session_workspace_access', refusal)
    assert request(denied) is False
    row = json.loads(denied.log.read_text())
    assert row['reason'] == reason
    assert 'sensitive-unrecognized-reason-canary' not in denied.log.read_text()
    assert json.loads(denied.handler.wfile.getvalue()) == {'error': message}


def test_allowed_session_does_not_emit_a_denial(denied, monkeypatch):
    monkeypatch.setattr(workspace_access, 'ensure_session_workspace_access', lambda *_: None)
    assert request(denied) is True
    assert denied.handler.status is None
    assert not denied.log.exists()
