"""MCP OAuth client setup.

Nango's public create-integration API skips the OAuth client registration that
the dashboard performs, leaving rows that fail at connect time with "missing
client ID, secret and/or scopes" (reported 20-09-2026 for Slack). With the
dashboard API available (basic auth on a self-hosted Nango) the WebUI runs
that registration itself; without it the old refusal stays.
"""
import pytest
from api import integrations

ENTRIES = {
    'attio-mcp': {'display_name': 'Attio (MCP)', 'auth_mode': 'MCP_OAUTH2',
                 'client_registration': 'dynamic',
                 'docs': 'https://nango.dev/docs/api-integrations/attio-mcp'},
    'granola-mcp': {'display_name': 'Granola (MCP)', 'auth_mode': 'MCP_OAUTH2',
                   'client_registration': 'dynamic', 'default_scopes': ['offline_access'],
                   'docs': 'https://nango.dev/docs/api-integrations/granola-mcp'},
    'lovable-mcp': {'display_name': 'Lovable (MCP)', 'auth_mode': 'MCP_OAUTH2',
                   'client_registration': 'cimd',
                   'docs': 'https://docs.lovable.dev/integrations/lovable-mcp-server'},
    'slack-mcp': {'display_name': 'Slack (MCP)', 'auth_mode': 'MCP_OAUTH2',
                  'client_registration': 'static',
                  'docs': 'https://nango.dev/docs/api-integrations/slack-mcp'},
}


@pytest.fixture
def mcp(monkeypatch):
    entries = {k: dict(v) for k, v in ENTRIES.items()}
    configured = []
    sent = []
    approved = []
    monkeypatch.setattr(integrations, 'load_provider_entries', lambda: entries)
    monkeypatch.setattr(integrations, '_list_integrations', lambda: configured)
    monkeypatch.setattr(integrations, '_approval_entries', lambda: {})
    monkeypatch.setattr(integrations, '_record_admin_approval', lambda *a: approved.append(a))
    monkeypatch.setattr(integrations, '_nango_dashboard_auth', lambda: None)

    def request(method, path, **kwargs):
        sent.append((method, path, kwargs))
        return {'data': {'token': 'fixture-session'}}
    monkeypatch.setattr(integrations, '_nango_request', request)
    return entries, configured, sent, approved


@pytest.fixture
def dashboard(monkeypatch, mcp):
    """Dashboard API on: v1 rows carry oauth_client_id, calls are recorded."""
    entries, configured, sent, approved = mcp
    rows = {}
    v1 = []
    monkeypatch.setattr(integrations, '_nango_dashboard_auth', lambda: ('michael', 'secret'))
    monkeypatch.setattr(integrations, 'nango_callback_url', lambda: 'https://nango.example.ts.net:3003/oauth/callback')

    def v1_request(method, path, payload=None):
        v1.append((method, path, payload))
        if method == 'GET' and path == '/integrations':
            return {'data': list(rows.values())}
        if method == 'POST':
            key = payload['integrationId']
            rows[key] = {'unique_key': key, 'provider': payload['provider'], 'oauth_client_id': 'registered', 'missing_fields': []}
            return {'data': rows[key]}
        if method == 'DELETE':
            rows.pop(path.rsplit('/', 1)[-1], None)
        if method == 'PATCH':
            row = rows[path.rsplit('/', 1)[-1]]
            row['oauth_client_id'] = payload.get('clientId')
        return {'data': {}}
    monkeypatch.setattr(integrations, '_nango_v1_request', v1_request)
    return entries, configured, sent, approved, rows, v1


# ── Without the dashboard API: refuse, never create an unusable row ──────────

@pytest.mark.parametrize('key', ['attio-mcp', 'granola-mcp', 'lovable-mcp'])
def test_enable_without_dashboard_refuses_and_points_at_nango(mcp, key):
    entries, configured, sent, approved = mcp
    with pytest.raises(ValueError, match='Nango') as exc:
        integrations.enable_integration('admin@example.test', key)
    assert 'client secret' not in str(exc.value).lower()
    assert entries[key]['docs'] in str(exc.value)
    assert sent == [] and approved == []


def test_catalog_without_dashboard_marks_mcp_as_setup_required_only_when_unconfigured(mcp):
    _, configured, _, _ = mcp
    configured.extend([
        {'provider': 'attio-mcp', 'unique_key': 'attio-work'},
        {'provider': 'attio-mcp', 'unique_key': 'attio-personal'},
    ])
    rows = integrations.get_catalog(is_admin=True)['providers']
    attio = [r for r in rows if r['key'] == 'attio-mcp']
    assert {r['unique_key'] for r in attio} == {'attio-work', 'attio-personal'}
    assert all(r['setup_required'] is False and r['needs_setup'] is False for r in attio)
    for row in rows:
        if row['key'] == 'slack-mcp':
            assert row['credential_fields'] == ['client_id', 'client_secret']
        else:
            assert row['credential_fields'] == []
        if row['key'] != 'attio-mcp':
            assert row['setup_required'] is True
            assert 'Nango' in row['setup_message']


def test_setup_guide_never_uses_unsafe_uri(mcp):
    entries, _, _, _ = mcp
    entries['attio-mcp']['docs'] = 'javascript:alert(1)'
    row = [r for r in integrations.get_catalog(is_admin=True)['providers'] if r['key'] == 'attio-mcp'][0]
    assert row['setup_guide_url'] == ''
    with pytest.raises(ValueError) as exc:
        integrations.enable_integration('admin@example.test', 'attio-mcp')
    assert 'javascript:' not in str(exc.value)


# ── With the dashboard API: register, detect, repair, guard ──────────────────

def test_enable_cimd_mcp_goes_through_the_dashboard_when_nango_is_public(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    result = integrations.enable_integration('admin@example.test', 'lovable-mcp')
    assert result['status'] == 'enabled'
    assert v1 == [('POST', '/integrations', {'provider': 'lovable-mcp', 'integrationId': 'lovable-mcp', 'useSharedCredentials': False})]


def test_enable_dynamic_mcp_registers_through_the_dashboard(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    result = integrations.enable_integration('admin@example.test', 'granola-mcp')
    assert result['status'] == 'enabled'
    assert sent == [], 'the public create API never sees an MCP provider'
    assert v1 == [('POST', '/integrations', {'provider': 'granola-mcp', 'integrationId': 'granola-mcp', 'useSharedCredentials': False})]
    assert len(approved) == 1


def test_enable_cimd_mcp_is_refused_on_a_private_host(dashboard, monkeypatch):
    entries, configured, sent, approved, rows, v1 = dashboard
    monkeypatch.setattr(integrations, 'nango_callback_url', lambda: 'http://nango.internal:3003/oauth/callback')
    with pytest.raises(ValueError, match='internet'):
        integrations.enable_integration('admin@example.test', 'lovable-mcp')
    assert v1 == [] and approved == []


def test_catalog_flags_configured_rows_without_a_client(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    configured.extend([{'provider': 'slack-mcp', 'unique_key': 'slack-mcp'},
                       {'provider': 'granola-mcp', 'unique_key': 'granola-mcp'}])
    rows['slack-mcp'] = {'unique_key': 'slack-mcp', 'provider': 'slack-mcp', 'oauth_client_id': None, 'missing_fields': []}
    rows['granola-mcp'] = {'unique_key': 'granola-mcp', 'provider': 'granola-mcp', 'oauth_client_id': 'client_x', 'missing_fields': []}
    catalog = integrations.get_catalog(is_admin=True)
    assert catalog['nango']['dashboard'] is True
    by_key = {r['unique_key']: r for r in catalog['providers'] if r['configured']}
    slack, granola = by_key['slack-mcp'], by_key['granola-mcp']
    assert slack['needs_setup'] is True and slack['setup_kind'] == 'static'
    assert 'https://nango.example.ts.net:3003/oauth/callback' in slack['setup_message']
    assert slack['callback_url'] == 'https://nango.example.ts.net:3003/oauth/callback'
    assert granola['needs_setup'] is False and granola['setup_kind'] == 'dynamic'
    assert granola['default_scopes'] == 'offline_access'


def test_connect_refuses_a_row_without_a_client_before_minting_a_session(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    configured.append({'provider': 'slack-mcp', 'unique_key': 'slack-mcp'})
    rows['slack-mcp'] = {'unique_key': 'slack-mcp', 'provider': 'slack-mcp', 'oauth_client_id': None, 'missing_fields': []}
    with pytest.raises(ValueError, match='OAuth app'):
        integrations.create_connect_session('admin@example.test', 'slack-mcp', is_admin=True)
    assert sent == []
    rows['slack-mcp']['oauth_client_id'] = 'now-registered'
    response = integrations.create_connect_session('admin@example.test', 'slack-mcp', is_admin=True)
    assert response['status'] == 'ready'
    assert [(m, p) for m, p, _ in sent] == [('POST', '/connect/sessions')]


def test_repair_dynamic_recreates_the_row_so_nango_registers_a_client(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    rows['granola-mcp'] = {'unique_key': 'granola-mcp', 'provider': 'granola-mcp', 'oauth_client_id': None, 'missing_fields': []}
    result = integrations.repair_integration('admin@example.test', 'granola-mcp')
    assert result['status'] == 'repaired' and result['needs_setup'] is False
    assert [(m, p) for m, p, _ in v1 if m != 'GET'] == [
        ('DELETE', '/integrations/granola-mcp'),
        ('POST', '/integrations'),
    ]
    assert sent[0][1] == '/connection', 'existing connections are checked before a recreate'


def test_repair_static_stores_the_admin_credentials(dashboard):
    entries, configured, sent, approved, rows, v1 = dashboard
    rows['slack-mcp'] = {'unique_key': 'slack-mcp', 'provider': 'slack-mcp', 'oauth_client_id': None, 'missing_fields': []}
    with pytest.raises(ValueError, match='client_id'):
        integrations.repair_integration('admin@example.test', 'slack-mcp')
    result = integrations.repair_integration('admin@example.test', 'slack-mcp',
                                             {'client_id': 'id', 'client_secret': 'sec', 'scopes': 'channels:read chat:write'})
    assert result['needs_setup'] is False
    patch = [call for call in v1 if call[0] == 'PATCH'][0]
    assert patch[1] == '/integrations/slack-mcp'
    assert patch[2] == {'authType': 'MCP_OAUTH2', 'clientId': 'id', 'clientSecret': 'sec', 'scopes': 'channels:read,chat:write'}
    assert sent == []
