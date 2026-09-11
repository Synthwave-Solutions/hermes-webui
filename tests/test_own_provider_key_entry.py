"""Own key entry is permitted without exposing it to another profile or response."""
import json
import os

import pytest

from api import profiles, providers
from api import streaming  # noqa: F401 - Complete startup before seeding the test environment.
from api.governance import enforce, loader
from api.governance.nav import feature_permissions
from api.governance.resolver import resolve_effective_access


@pytest.fixture
def homes(tmp_path, monkeypatch):
    base = tmp_path / '.hermes'
    own = base / 'profiles' / 'alice'
    other = base / 'profiles' / 'bob'
    own.mkdir(parents=True)
    other.mkdir()
    (base / '.env').write_text('OPENAI_API_KEY=synthetic-root-key\n')
    (other / '.env').write_text('OPENAI_API_KEY=synthetic-other-key\n')
    monkeypatch.setattr(profiles, '_DEFAULT_HERMES_HOME', base)
    monkeypatch.setenv('HERMES_BASE_HOME', str(base))
    monkeypatch.setenv('HERMES_HOME', str(base))
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-process-key')
    monkeypatch.setattr(providers, 'invalidate_models_cache', lambda: None)
    monkeypatch.setattr(providers, 'invalidate_account_usage_status_cache', lambda *_: None)
    monkeypatch.setattr(providers, '_provider_is_oauth', lambda _: False)
    profiles.set_request_profile('alice')
    try:
        yield base, own, other
    finally:
        profiles.clear_request_profile()


@pytest.mark.parametrize('key', ['synthetic-own-new-key', 'synthetic-own-replacement-key', None])
def test_named_profile_key_save_replace_remove_never_changes_shared_environment(homes, key, caplog):
    base, own, other = homes
    (own / '.env').write_text('# personal\nOPENAI_API_KEY=synthetic-own-old-key\nUNCHANGED=retained\n')
    protected = {p: (p / '.env').read_bytes() for p in (base, other)}
    result = providers.set_provider_key('openai', key)
    assert result['ok'] is True
    assert os.environ['OPENAI_API_KEY'] == 'synthetic-process-key'
    assert all((p / '.env').read_bytes() == raw for p, raw in protected.items())
    actual = providers._load_env_file(own / '.env')
    assert actual.get('OPENAI_API_KEY') == key
    assert actual['UNCHANGED'] == 'retained'
    assert (own / '.env').stat().st_mode & 0o777 == 0o600
    assert profiles.get_profile_runtime_env(own).get('OPENAI_API_KEY') == key
    if key:
        assert key not in json.dumps(result) + caplog.text


def test_default_profile_key_keeps_single_user_process_environment_behavior(homes):
    base, _, other = homes
    other_before = (other / '.env').read_bytes()
    profiles.set_request_profile('default')
    assert providers.set_provider_key('openai', 'synthetic-default-replacement')['ok']
    assert os.environ['OPENAI_API_KEY'] == 'synthetic-default-replacement'
    assert providers._load_env_file(base / '.env')['OPENAI_API_KEY'] == 'synthetic-default-replacement'
    assert providers.set_provider_key('openai', None)['ok']
    assert 'OPENAI_API_KEY' not in os.environ
    assert (other / '.env').read_bytes() == other_before


def test_rejected_key_does_not_change_files_or_environment(homes):
    base, own, other = homes
    result = providers.set_provider_key('openai', 'synthetic-key\nEXTRA=not-allowed')
    assert result['ok'] is False
    assert not (own / '.env').exists()
    assert os.environ['OPENAI_API_KEY'] == 'synthetic-process-key'
    assert 'EXTRA' not in json.dumps(result)


@pytest.mark.parametrize('denied, expected', [(['env:*', 'governance:*'], True), (['config:write'], False)])
def test_native_own_key_route_needs_config_write_but_not_raw_secret_read(monkeypatch, denied, expected):
    policy = loader.parse_governance_policy({'version': 1, 'mode': 'enforce', 'users': {
        'alice@example.test': {'roles': [], 'access_level': 'elevated', 'access_mode': 'blacklist',
                               'approval': {'mode': 'automatic', 'prompt': 'Routine authorized technical work.'},
                               'deny': {'permissions': denied}}}})
    monkeypatch.setattr(loader, 'get_policy', lambda: policy)
    identity = {'email': 'alice@example.test'}
    decision = enforce.evaluate_request(identity, 'POST', '/api/providers')
    assert decision.allow is expected
    assert decision.resource == 'config:write'
    access = resolve_effective_access(policy, enforce.subject_from_identity(identity))
    assert feature_permissions(access)['config:write'] is expected
    if expected:
        assert not access.has_permission('env:read')
        assert not access.has_permission('governance:write')
