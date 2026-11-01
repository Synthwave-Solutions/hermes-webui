"""Native plugin installation remains curated, administrator-only and scoped."""
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from api import plugin_catalog_ui


@pytest.fixture
def route(monkeypatch):
    monkeypatch.setattr('api.routes.j', lambda handler, payload, status=200: (status, payload))
    monkeypatch.setattr('api.profiles.profile_env_for_active_request', lambda reason: nullcontext())
    monkeypatch.setattr('api.ownership.request_is_admin', lambda handler: True)
    return lambda action, body: plugin_catalog_ui.handle(object(), action, body)


def test_member_cannot_install_or_toggle(route, monkeypatch):
    monkeypatch.setattr('api.ownership.request_is_admin', lambda handler: False)
    install = Mock()
    monkeypatch.setattr('hermes_cli.plugins_cmd.dashboard_install_plugin', install)
    assert route('install', {'name': 'calendar'})[0] == 403
    assert route('toggle', {'name': 'calendar', 'enabled': True})[0] == 403
    install.assert_not_called()


@pytest.mark.parametrize('name', ['https://example.test/unreviewed.git', '../escape', 'foo;whoami'])
def test_arbitrary_source_or_invalid_name_cannot_reach_installer(route, monkeypatch, name):
    install = Mock()
    monkeypatch.setattr('hermes_cli.plugins_cmd.dashboard_install_plugin', install)
    assert route('install', {'name': name})[0] == 400
    install.assert_not_called()


def test_install_uses_native_catalog_name_without_force_and_hides_internal_error(route, monkeypatch):
    install = Mock(return_value={'ok': True})
    monkeypatch.setattr('hermes_cli.plugins_cmd.dashboard_install_plugin', install)
    assert route('install', {'name': 'calendar'}) == (200, {'ok': True, 'restart_required': True})
    install.assert_called_once_with('', catalog_name='calendar', enable=True, force=False)
    install.return_value = {'error': 'secret-token and private-path'}
    code, result = route('install', {'name': 'calendar'})
    assert code == 409
    assert 'secret-token' not in str(result)
