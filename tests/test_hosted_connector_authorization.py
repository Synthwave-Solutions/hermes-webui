"""Hosted browser actions and native chat tools share the approval registry."""
import json
import subprocess
import sys

import pytest

from api import approvals, config, hosted_connectors, integrations
from api.governance import loader

MEMBER = {'email': 'member@example.test', 'method': 'oidc'}
ADMIN = {'email': 'admin@example.test', 'method': 'oidc'}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'agent'))
    monkeypatch.setenv('HOME', str(tmp_path / 'system-home'))
    monkeypatch.setattr(config, 'STATE_DIR', tmp_path / 'webui')
    policy = loader.parse_governance_policy({
        'version': 1, 'mode': 'enforce', 'default_effect': 'deny',
        'bootstrap_admins': [ADMIN['email']], 'roles': {}, 'groups': {}, 'users': {},
    })
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    monkeypatch.setattr(integrations, 'load_provider_entries', lambda: {})


def test_native_approval_records_pending_then_respects_decision_and_owner_scope():
    with pytest.raises(PermissionError, match='admin approval'):
        hosted_connectors.authorize_connection(MEMBER, ['gmail', 'notion'])
    for slug in ('gmail', 'notion'):
        row = approvals.get('integration', 'hosted-' + slug)
        assert row['owner_email'] == MEMBER['email']
        assert row['status'] == 'pending'
    hosted_connectors.authorize_connection(ADMIN, ['gmail', 'notion'])
    hosted_connectors.authorize_connection(MEMBER, ['gmail', 'notion'])
    assert approvals.get('integration', 'hosted-gmail')['decided_by'] == ADMIN['email']

    approvals.request('integration', 'hosted-slack', ADMIN['email'], payload={'scope': 'owner'})
    approvals.decide('integration', 'hosted-slack', 'approve', decided_by=ADMIN['email'])
    with pytest.raises(PermissionError):
        hosted_connectors.authorize_connection(MEMBER, ['slack'])
    assert approvals.get('integration', 'hosted-slack')['owner_email'] == ADMIN['email']


def test_browser_connect_uses_same_policy_and_never_mints_until_approved(monkeypatch):
    calls = []
    monkeypatch.setattr(hosted_connectors, 'catalog', lambda: [{'slug': 'gmail'}])

    def worker(identity, action, **values):
        calls.append((identity, action, values))
        return {'results': [{'connector': 'gmail', 'status': 'initiated',
                             'connect_url': 'https://auth.example.test/start'}]}

    monkeypatch.setattr(hosted_connectors, '_worker', worker)
    pending = hosted_connectors.connect(MEMBER, 'gmail')
    assert pending['status'] == 'pending_approval'
    assert calls == []
    assert hosted_connectors.connect(ADMIN, 'gmail')['status'] == 'initiated'
    assert hosted_connectors.connect(MEMBER, 'gmail')['status'] == 'initiated'
    assert [row[0]['email'] for row in calls] == [ADMIN['email'], MEMBER['email']]


def test_invalid_batch_or_missing_actor_cannot_create_approval_rows():
    for identity, slugs in ((None, ['gmail']), (MEMBER, ['gmail', '../bad']), (MEMBER, 'gmail')):
        with pytest.raises((PermissionError, ValueError)):
            hosted_connectors.authorize_connection(identity, slugs)
    assert approvals.list_all(kinds='integration') == []


def test_worker_native_auth_cannot_read_synthetic_installation_owner(tmp_path, monkeypatch):
    owner_home = tmp_path / 'owner'
    owner_auth = owner_home / '.hermes' / 'auth.json'
    owner_auth.parent.mkdir(parents=True)
    owner_auth.write_text(json.dumps({'version': 1, 'providers': {
        'nous': {'access_token': 'synthetic-owner-credential'},
    }}))
    monkeypatch.setattr(config, 'STATE_DIR', owner_auth.parent / 'webui')
    personal_root = hosted_connectors._account_home(MEMBER)
    personal_root.mkdir(parents=True)
    (personal_root / 'auth.json').write_text('{"providers": {}}')
    real_run = subprocess.run
    probes = []

    def probe_native_resolution(command, **kwargs):
        env = dict(kwargs['env'])
        # Model the OS account-home fallback with synthetic state. Without a
        # worker HOME, Path.home() would otherwise reach the real test runner.
        env.setdefault('HOME', str(owner_home))
        code = '''
import json
from hermes_constants import get_default_hermes_root
from hermes_cli.auth import _load_auth_store, _load_provider_state
from tools.managed_tool_gateway import read_nous_access_token
state = _load_provider_state(_load_auth_store(), 'nous')
print(json.dumps({'ok': True, 'result': {
    'root': str(get_default_hermes_root()), 'owner_visible': state is not None,
    'token': read_nous_access_token() if state is None else None,
}}))
'''
        result = real_run([sys.executable, '-c', code], env=env, cwd=kwargs['cwd'],
                          text=True, capture_output=True, timeout=25)
        assert result.returncode == 0, result.stderr
        probes.append(json.loads(result.stdout)['result'])
        return result

    monkeypatch.setattr(hosted_connectors.subprocess, 'run', probe_native_resolution)
    assert hosted_connectors._worker(MEMBER, 'token')['token'] is None
    assert probes == [{'root': str(personal_root), 'owner_visible': False, 'token': None}]
    assert json.loads(owner_auth.read_text())['providers']['nous']['access_token'] == 'synthetic-owner-credential'
