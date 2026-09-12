"""MCP registration is not performed by Nango's public create-integration API."""
import pytest
from api import integrations


@pytest.fixture
def mcp(monkeypatch):
    entries = {
        'attio-mcp': {'display_name': 'Attio (MCP)', 'auth_mode': 'MCP_OAUTH2',
                     'client_registration': 'dynamic',
                     'docs': 'https://nango.dev/docs/api-integrations/attio-mcp'},
        'granola-mcp': {'display_name': 'Granola (MCP)', 'auth_mode': 'MCP_OAUTH2',
                       'client_registration': 'dynamic',
                       'docs': 'https://nango.dev/docs/api-integrations/granola-mcp'},
        'lovable-mcp': {'display_name': 'Lovable (MCP)', 'auth_mode': 'MCP_OAUTH2',
                       'client_registration': 'cimd',
                       'docs': 'https://docs.lovable.dev/integrations/lovable-mcp-server'},
    }
    configured = []
    sent = []
    approved = []
    monkeypatch.setattr(integrations, 'load_provider_entries', lambda: entries)
    monkeypatch.setattr(integrations, '_list_integrations', lambda: configured)
    monkeypatch.setattr(integrations, '_approval_entries', lambda: {})
    monkeypatch.setattr(integrations, '_record_admin_approval', lambda *a: approved.append(a))
    def request(method, path, **kwargs):
        sent.append((method, path, kwargs))
        return {'data': {'token': 'fixture-session'}}
    monkeypatch.setattr(integrations, '_nango_request', request)
    return entries, configured, sent, approved


@pytest.mark.parametrize('key', ['attio-mcp', 'granola-mcp', 'lovable-mcp'])
def test_enable_does_not_create_unregistered_mcp_row(mcp, key):
    entries, configured, sent, approved = mcp
    with pytest.raises(ValueError, match='Nango') as exc:
        integrations.enable_integration('admin@example.test', key)
    assert 'SynthPulse' in str(exc.value)
    assert 'client secret' not in str(exc.value).lower()
    assert entries[key]['docs'] in str(exc.value)
    assert sent == [] and approved == []


def test_catalog_setup_is_per_configuration_and_not_a_connection_claim(mcp):
    _, configured, _, _ = mcp
    configured.extend([
        {'provider': 'attio-mcp', 'unique_key': 'attio-work'},
        {'provider': 'attio-mcp', 'unique_key': 'attio-personal'},
    ])
    rows = integrations.get_catalog(is_admin=True)['providers']
    attio = [r for r in rows if r['key'] == 'attio-mcp']
    assert {r['unique_key'] for r in attio} == {'attio-work', 'attio-personal'}
    assert all(r['setup_required'] is False for r in attio)
    assert all(r['setup_guide_url'] == 'https://nango.dev/docs/api-integrations/attio-mcp' for r in attio)
    for row in rows:
        assert row['credential_fields'] == []
        if row['key'] != 'attio-mcp':
            assert row['setup_required'] is True
            assert 'Nango' in row['setup_message']


def test_configured_mcp_enable_and_connect_remain_available_without_credential_probe(mcp):
    _, configured, sent, approved = mcp
    configured.append({'provider': 'granola-mcp', 'unique_key': 'granola-mcp'})
    assert integrations.enable_integration('admin@example.test', 'granola-mcp')['status'] == 'enabled'
    response = integrations.create_connect_session('admin@example.test', 'granola-mcp', is_admin=True)
    assert response['status'] == 'ready'
    assert len(approved) == 2
    assert [(method, path) for method, path, _ in sent] == [('POST', '/connect/sessions')]
    assert sent[0][2]['payload']['allowed_integrations'] == ['granola-mcp']
    assert sent[0][2]['payload']['end_user']['id'] == 'u-admin-example-test'


def test_setup_guide_never_uses_unsafe_uri(mcp):
    entries, _, _, _ = mcp
    entries['attio-mcp']['docs'] = 'javascript:alert(1)'
    row = integrations.get_catalog(is_admin=True)['providers'][0]
    assert row['setup_guide_url'] == ''
    with pytest.raises(ValueError) as exc:
        integrations.enable_integration('admin@example.test', 'attio-mcp')
    assert 'javascript:' not in str(exc.value)
