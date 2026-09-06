"""Identity and sidebar enumeration must not synchronously count skill trees."""
import pytest


def test_metadata_rows_do_not_read_or_queue_skill_counts(monkeypatch, tmp_path):
    from api import profiles
    import hermes_cli.profiles as engine_profiles
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setattr(engine_profiles, '_get_default_hermes_home', lambda: home)
    monkeypatch.setattr(engine_profiles, '_get_profiles_root', lambda: home / 'profiles')
    monkeypatch.setattr(engine_profiles, '_check_gateway_running', lambda _: False)
    monkeypatch.setattr(profiles, '_is_isolated_profile_mode', lambda: False)
    monkeypatch.setattr(profiles, 'get_active_profile_name', lambda: 'default')
    monkeypatch.setattr(profiles, '_list_skill_stats', lambda *a: pytest.fail('deferred counts consulted'))
    monkeypatch.setattr(profiles, '_get_profile_skills_stats', lambda *a: pytest.fail('full counts consulted'))
    rows = profiles.list_profiles_api(fast=True, include_skill_counts=False)
    assert rows[0]['name'] == 'default'
    assert rows[0]['path'] == str(home)
    assert rows[0]['is_default'] is True
    assert rows[0]['skill_count'] is None


def test_root_alias_resolution_uses_metadata_only_and_remains_cached(monkeypatch):
    from api import profiles
    calls = []
    def rows(**kwargs):
        calls.append(kwargs)
        assert kwargs == {'fast': True, 'include_skill_counts': False}
        return [{'name': 'canonical-root', 'is_default': True},
                {'name': 'research', 'is_default': False}]
    monkeypatch.setattr(profiles, 'list_profiles_api', rows)
    profiles._invalidate_root_profile_cache()
    try:
        assert profiles._is_root_profile('default')
        assert profiles._is_root_profile('canonical-root')
        assert not profiles._is_root_profile('research')
        assert len(calls) == 1
    finally:
        profiles._invalidate_root_profile_cache()


def test_cli_profile_enumeration_uses_metadata_without_counts(monkeypatch, tmp_path):
    from api import models, profiles
    root = tmp_path / 'profiles'
    root.mkdir()
    monkeypatch.setattr(profiles, '_profiles_root', lambda: root)
    monkeypatch.setattr(profiles, 'get_active_profile_name', lambda: 'default')
    monkeypatch.setattr(profiles, 'get_hermes_home_for_profile', lambda name: tmp_path / name)
    def rows(**kwargs):
        assert kwargs == {'fast': True, 'include_skill_counts': False}
        return [{'name': 'default'}, {'name': 'research'}]
    monkeypatch.setattr(profiles, 'list_profiles_api', rows)
    contexts, _ = models._all_profiles_cli_contexts()
    assert {row[2] for row in contexts} == {'default', 'research'}
