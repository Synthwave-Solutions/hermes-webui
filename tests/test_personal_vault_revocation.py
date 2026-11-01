"""Deterministic interleavings for personal vault disable, unlock and lock."""
from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace

import pytest

from api import config, vault
from agent.vault_backends import bitwarden, unlock
from agent.vault_store import get_vault_store

ALICE = {'email': 'alice@example.test'}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'STATE_DIR', tmp_path / 'state')
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'host'))
    monkeypatch.setattr('agent.vault_backends.base.is_installed', lambda name: True)
    monkeypatch.setattr(bitwarden.BitwardenLoginBackend, '_bw', lambda self: tmp_path / 'bw')
    with vault.vault_scope(ALICE):
        get_vault_store().update_source_settings('bitwarden', {'enabled': True, 'connected': True})
    yield
    with vault.vault_scope(ALICE):
        unlock.lock()


def action(name, body):
    with vault.vault_scope(ALICE):
        return vault._action(name, body)


def test_disable_cannot_slip_between_manager_selection_and_unlock(monkeypatch):
    selected = threading.Event()
    continue_unlock = threading.Event()
    real_manager = vault._manager
    real_configure = vault._configure_locked

    class OrderedLock:
        def __init__(self):
            self.lock = threading.Lock()

        def __enter__(self):
            if not self.lock.acquire(blocking=False):
                continue_unlock.set()
                assert self.lock.acquire(timeout=5)
            return self

        def __exit__(self, *args):
            self.lock.release()

    def paused_manager(name):
        backend = real_manager(name)
        selected.set()
        assert continue_unlock.wait(timeout=5)
        return backend

    def configure_then_resume(name, body):
        try:
            return real_configure(name, body)
        finally:
            continue_unlock.set()

    monkeypatch.setattr(vault, '_SOURCE_LOCKS', (OrderedLock(),))
    monkeypatch.setattr(vault, '_manager', paused_manager)
    monkeypatch.setattr(vault, '_configure_locked', configure_then_resume)
    monkeypatch.setattr(bitwarden, 'run_with_secret_env', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout='fixture-session', stderr=''))
    with ThreadPoolExecutor(max_workers=2) as pool:
        opening = pool.submit(action, 'unlock', {'name': 'bitwarden', 'password': 'fixture-password'})
        assert selected.wait(timeout=5)
        disabling = pool.submit(action, 'configure', {'name': 'bitwarden', 'enabled': False})
        assert opening.result(timeout=5) == {'ok': True}
        assert disabling.result(timeout=5) == {'ok': True}
    with vault.vault_scope(ALICE):
        assert get_vault_store().read_source_settings()['bitwarden']['enabled'] is False
        assert unlock.get_session_token('bitwarden') is None


def test_explicit_lock_still_invalidates_an_inflight_unlock(monkeypatch):
    started, finish = threading.Event(), threading.Event()

    def cli(*args, **kwargs):
        started.set()
        assert finish.wait(timeout=5)
        return SimpleNamespace(returncode=0, stdout='late-fixture-session', stderr='')

    monkeypatch.setattr(bitwarden, 'run_with_secret_env', cli)
    with ThreadPoolExecutor(max_workers=1) as pool:
        opening = pool.submit(action, 'unlock', {'name': 'bitwarden', 'password': 'fixture-password'})
        assert started.wait(timeout=5)
        try:
            assert action('lock', {'name': 'bitwarden'}) == {'ok': True}
        finally:
            finish.set()
        with pytest.raises(ValueError, match='Unlock failed'):
            opening.result(timeout=5)
    with vault.vault_scope(ALICE):
        assert unlock.get_session_token('bitwarden') is None


def test_onepassword_lock_cannot_claim_to_revoke_a_service_account():
    with vault.vault_scope(ALICE):
        get_vault_store().update_source_settings('onepassword', {
            'enabled': True, 'connected': True, 'service_account_token': 'fixture-service-token',
        })
        with pytest.raises(ValueError, match='Disable or disconnect'):
            vault._action('lock', {'name': 'onepassword'})
        assert vault.status()['sources'][2]['unlocked'] is True


@pytest.mark.parametrize('failure', ['logout_error', 'missing_cli'])
def test_failed_bitwarden_logout_still_revokes_local_access(monkeypatch, failure):
    def failed_cli(*args, **kwargs):
        raise ValueError('logout failed')

    monkeypatch.setattr(vault, '_cli', failed_cli)
    if failure == 'missing_cli':
        monkeypatch.setattr(bitwarden.BitwardenLoginBackend, '_bw', failed_cli)
    result = action('disconnect', {'name': 'bitwarden'})
    assert result['ok'] is True
    assert result['remote_logout'] is False
    assert 'retry' in result['message'].lower()
    with vault.vault_scope(ALICE):
        section = get_vault_store().read_source_settings()['bitwarden']
        assert section['enabled'] is False and section['connected'] is False
        assert unlock.get_session_token('bitwarden') is None
