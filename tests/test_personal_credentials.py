"""The shared turn boundary isolates credentials and restores nested contexts."""
from contextvars import copy_context

import pytest

from api import config, hosted_connectors, personal_context, personal_credentials
from agent.vault_scope import personal_vault_bound, vault_home
from tools.connectors.identity import personal_connector_token

ALICE = {'email': 'alice@example.test'}
BOB = {'email': 'bob@example.test'}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'STATE_DIR', tmp_path / 'webui')
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'host'))
    monkeypatch.setattr(hosted_connectors, '_PERSONAL_CATALOGS', {})


def test_nested_turn_and_delegate_keep_actor_and_restore_after_failure(monkeypatch):
    monkeypatch.setattr(hosted_connectors, 'personal_token', lambda identity: identity['email'])
    with personal_credentials.scope(ALICE):
        delegated = copy_context()
        with pytest.raises(RuntimeError, match='turn failed'):
            with personal_credentials.scope(BOB):
                assert personal_connector_token() == (True, BOB['email'])
                assert vault_home() == personal_context.home(BOB)
                assert delegated.run(personal_connector_token) == (True, ALICE['email'])
                assert delegated.run(vault_home) == personal_context.home(ALICE)
                raise RuntimeError('turn failed')
        assert personal_connector_token() == (True, ALICE['email'])
        assert vault_home() == personal_context.home(ALICE)
    assert not personal_vault_bound()
    assert personal_connector_token() == (False, None)


def test_bound_user_without_account_never_inherits_host_credentials():
    with personal_credentials.scope(ALICE):
        assert personal_connector_token() == (True, None)


def test_private_catalog_cache_never_crosses_users_and_tracks_credential_changes(monkeypatch):
    calls = []
    def worker(identity, action):
        calls.append((identity['email'], action))
        return {'connectors': [{'slug': identity['email'], 'version': len(calls)}]}
    monkeypatch.setattr(hosted_connectors, '_worker', worker)
    monkeypatch.setattr(hosted_connectors, 'catalog', lambda: [{'slug': 'public'}])
    assert hosted_connectors.catalog_for(ALICE) == [{'slug': 'public'}]
    assert calls == []
    for identity in (ALICE, BOB):
        root = hosted_connectors._account_home(identity)
        root.mkdir(parents=True)
        (root / 'auth.json').write_text('{}')
    alice = hosted_connectors.catalog_for(ALICE)
    bob = hosted_connectors.catalog_for(BOB)
    assert alice[0]['slug'] == ALICE['email']
    assert bob[0]['slug'] == BOB['email']
    assert hosted_connectors.catalog_for(ALICE) == alice
    assert len(calls) == 2
    path = hosted_connectors._account_home(ALICE) / 'auth.json'
    import os
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert hosted_connectors.catalog_for(ALICE) != alice
    path.unlink()
    assert hosted_connectors.catalog_for(ALICE) == [{'slug': 'public'}]
