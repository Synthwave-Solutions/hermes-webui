import json
import sys
import types

import pytest
from api import integrations, cron_webui_delivery


def test_catalog_preserves_multiple_configurations(monkeypatch):
    monkeypatch.setattr(integrations, 'load_provider_entries', lambda: {'notion': {'display_name': 'Notion', 'auth_mode': 'OAUTH2'}})
    monkeypatch.setattr(integrations, '_list_integrations', lambda: [
        {'provider': 'notion', 'unique_key': 'notion-personal'},
        {'provider': 'notion', 'unique_key': 'notion-work'},
    ])
    monkeypatch.setattr(integrations, '_approval_entries', lambda: {})
    rows = integrations.get_catalog(is_admin=True)['providers']
    assert {row['unique_key'] for row in rows} == {'notion-personal', 'notion-work'}
    assert all(row['key'] == 'notion' for row in rows)


def test_catalog_exposes_credential_fields(monkeypatch):
    row = integrations._catalog_item('notion', {'auth_mode': 'OAUTH2'})
    assert row['credential_fields'] == ['client_id', 'client_secret']
    assert integrations._catalog_item('mcp', {'auth_mode': 'MCP_OAUTH2'})['credential_fields'] == []


@pytest.mark.parametrize('response, expected', [
    ({'success': True}, True), ({'success': False, 'error': 'unavailable'}, False),
    ({'success': 'false'}, False), ({}, False), ('invalid-json', False),
])
def test_external_notice_uses_installed_transport(monkeypatch, response, expected):
    calls = []
    def send(args):
        calls.append(args)
        return json.dumps(response) if isinstance(response, dict) else response
    monkeypatch.setitem(sys.modules, 'tools.send_message_tool', types.SimpleNamespace(send_message_tool=send))
    ok, error = cron_webui_delivery.deliver_external_notice('telegram:123', 'Capacity unavailable')
    assert calls == [{'action': 'send', 'target': 'telegram:123', 'message': 'Capacity unavailable'}]
    assert ok is expected
    assert (error is None) is expected
