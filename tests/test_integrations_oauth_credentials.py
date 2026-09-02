"""Enabling an OAuth-family integration needs its client credentials.

Nango refuses POST /integrations for OAUTH1/OAUTH2/TBA/APP/CUSTOM without a
credentials object, so the enable call came back as the opaque upstream text
"Nango API error (400): Missing credentials" and there was no place in the
product to supply them (reported 01-09-2026, alongside "still not possible to
connect them" from the admin side). MCP_OAUTH2 providers register a client
dynamically and must keep enabling with no credentials at all.
"""
from __future__ import annotations

import pytest

from api import integrations


@pytest.fixture
def catalog(monkeypatch):
    entries = {
        "notion": {"display_name": "Notion", "auth_mode": "OAUTH2",
                   "docs": "https://nango.dev/docs/notion"},
        "slack-mcp": {"display_name": "Slack (MCP)", "auth_mode": "MCP_OAUTH2",
                      "setup_guide_url": "https://nango.dev/docs/slack-mcp/register"},
        "productive": {"display_name": "Productive", "auth_mode": "API_KEY"},
        "gh-app": {"display_name": "GitHub App", "auth_mode": "APP"},
    }
    monkeypatch.setattr(integrations, "load_provider_entries", lambda: entries)
    monkeypatch.setattr(integrations, "_list_integrations", lambda: [])
    monkeypatch.setattr(integrations, "_approval_entries", lambda: {})
    monkeypatch.setattr(integrations, "_record_admin_approval",
                        lambda *a, **k: None)
    return entries


@pytest.fixture
def sent(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    def fake(method, path, *, payload=None, query=None):
        calls.append((method, path, payload))
        return {"data": {}}

    monkeypatch.setattr(integrations, "_nango_request", fake)
    return calls


def _enable(key, credentials=None):
    return integrations.enable_integration("admin@example.test", key, credentials)


class TestOAuthCredentialsRequired:
    def test_oauth2_without_credentials_is_refused_before_calling_nango(self, catalog, sent):
        with pytest.raises(ValueError) as err:
            _enable("notion")
        message = str(err.value)
        assert "client_id" in message and "client_secret" in message
        assert "Notion" in message
        assert "https://nango.dev/docs/notion" in message
        assert sent == [], "no request should reach Nango when we already know it fails"

    def test_oauth2_with_credentials_sends_them(self, catalog, sent):
        _enable("notion", {"client_id": "abc", "client_secret": "shh"})
        assert len(sent) == 1
        _, path, payload = sent[0]
        assert path == "/integrations"
        assert payload["credentials"] == {
            "type": "OAUTH2", "client_id": "abc", "client_secret": "shh"}

    def test_optional_scopes_pass_through(self, catalog, sent):
        _enable("notion", {"client_id": "a", "client_secret": "b", "scopes": "read,write"})
        assert sent[0][2]["credentials"]["scopes"] == "read,write"

    def test_blank_values_count_as_missing(self, catalog, sent):
        with pytest.raises(ValueError) as err:
            _enable("notion", {"client_id": "abc", "client_secret": "   "})
        assert "client_secret" in str(err.value)
        assert sent == []

    def test_app_mode_names_its_own_three_fields(self, catalog, sent):
        with pytest.raises(ValueError) as err:
            _enable("gh-app", {"app_id": "1"})
        message = str(err.value)
        assert "app_link" in message and "private_key" in message
        assert "client_id" not in message


class TestProvidersThatNeedNoCredentials:
    def test_mcp_oauth2_enables_with_nothing(self, catalog, sent):
        result = _enable("slack-mcp")
        assert sent[0][2] == {"provider": "slack-mcp", "unique_key": "slack-mcp"}
        assert "credentials" not in sent[0][2]
        assert result["status"] == "enabled"

    def test_api_key_enables_with_nothing(self, catalog, sent):
        _enable("productive")
        assert "credentials" not in sent[0][2]

    def test_mcp_oauth2_does_not_claim_to_need_credentials(self, catalog, sent):
        assert _enable("slack-mcp")["needs_credentials"] is False
