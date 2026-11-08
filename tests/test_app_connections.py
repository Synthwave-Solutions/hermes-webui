"""app_connections resolver: own connections only, org rows for admins, safe proxy paths."""
import json
from contextvars import copy_context

import pytest

from api import app_connections, integrations, personal_credentials
from tools.app_connections_tool import app_connections as tool, app_connections_bound

ROWS = [
    {"connection_id": "a1", "provider_config_key": "lemlist", "errors": [], "end_user": {"id": "u-alice-example-test"}},
    {"connection_id": "b1", "provider_config_key": "lemlist", "errors": [], "end_user": {"id": "u-bob-example-test"}},
    {"connection_id": "org", "provider_config_key": "productive", "errors": [], "end_user": None},
]


@pytest.fixture(autouse=True)
def fake_nango(monkeypatch, tmp_path):
    from api import config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "host"))

    def list_connections(owner_email, *, is_admin=False):
        if is_admin:
            return [dict(r) for r in ROWS]
        own = integrations.end_user_id(owner_email)
        return [dict(r) for r in ROWS if r["end_user"] and r["end_user"]["id"] == own]

    monkeypatch.setattr(integrations, "list_connections", list_connections)
    monkeypatch.setattr(integrations, "_list_integrations", lambda: [
        {"unique_key": "lemlist", "provider": "lemlist"}, {"unique_key": "productive", "provider": "productive"}])
    monkeypatch.setattr(integrations, "load_provider_entries", lambda: {
        "lemlist": {"auth_mode": "BASIC", "proxy": {"base_url": "https://api.lemlist.com"}},
        "productive": {"auth_mode": "API_KEY", "proxy": {"base_url": "https://api.productive.io"}}})


def _resolver(email, admin):
    r = app_connections.Resolver({"email": email})
    r._admin = admin
    return r


def test_member_sees_only_own_connections():
    rows = _resolver("alice@example.test", False).list()
    assert [(r["connection_id"], r["scope"]) for r in rows] == [("a1", "personal")]


def test_admin_gets_org_rows_but_never_someone_elses_personal_connection():
    rows = _resolver("alice@example.test", True).list()
    assert {(r["connection_id"], r["scope"]) for r in rows} == {("a1", "personal"), ("org", "organization")}
    with pytest.raises(LookupError):
        _resolver("alice@example.test", True)._pick("lemlist", "b1")


def test_member_cannot_use_org_connection():
    with pytest.raises(LookupError):
        _resolver("alice@example.test", False)._pick("productive", None)


@pytest.mark.parametrize("path", ["@evil.test/x", "//evil.test/x", "https://evil.test/x", "x/y", "/a b", "/a\\b"])
def test_paths_that_could_change_the_host_are_refused(path):
    with pytest.raises(ValueError):
        app_connections._validate_path(path)


def test_tool_fails_closed_without_identity_and_binds_per_turn(monkeypatch):
    assert "error" in json.loads(tool({"action": "list"}))
    monkeypatch.setattr(app_connections.Resolver, "_is_admin", lambda self: False)
    with personal_credentials.scope({"email": "alice@example.test"}):
        assert app_connections_bound()
        delegated = copy_context()
        out = json.loads(tool({"action": "list"}))
        assert [c["connection_id"] for c in out["connections"]] == ["a1"]
        assert delegated.run(app_connections_bound)
    assert not app_connections_bound()


def test_mcp_endpoint_derivation():
    assert app_connections._mcp_url({"authorization_params": {"resource": "https://mcp.granola.ai/"}}) == "https://mcp.granola.ai/mcp"
    assert app_connections._mcp_url({"authorization_params": {"resource": "https://mcp.attio.com/mcp"}}) == "https://mcp.attio.com/mcp"
    with pytest.raises(LookupError):
        app_connections._mcp_url({"proxy": {"base_url": "http://insecure.test"}})
