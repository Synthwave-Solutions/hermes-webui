from unittest.mock import patch


def test_personal_selection_is_scoped_and_survives_reopening(tmp_path, monkeypatch):
    from api import chat_connectors as chat
    monkeypatch.setattr("api.config.STATE_DIR", tmp_path)
    person = {"email": "tester@example.org"}
    other = {"email": "colleague@example.org"}
    chat.set_enabled(person, "one", "hosted", "calendar", False)
    chat.set_enabled(person, "one", "nango", "calendar", False)
    assert chat.disabled(person, "one") == {"hosted:calendar", "nango:calendar"}
    assert chat.disabled(other, "one") == chat.disabled(person, "two") == set()
    chat.set_enabled(person, "one", "hosted", "calendar", True)
    assert chat.disabled(person, "one") == {"nango:calendar"}


def test_chat_disable_filters_connection_lookup_and_personal_cli_credentials():
    from api.app_connections import Resolver
    resolver = Resolver({"email": "tester@example.org"}, disabled={"github"})
    rows = [{"provider_config_key": key, "connection_id": key} for key in ("github", "calendar")]
    with patch("api.integrations.list_connections", return_value=rows), patch.object(resolver, "_is_admin", return_value=False):
        assert [row["provider_config_key"] for row in resolver.visible_connections()] == ["calendar"]
        with patch.object(resolver, "_integrations", return_value={}), patch("api.integrations._nango_request") as provider:
            assert resolver.cli_env() == {}
            provider.assert_not_called()


def test_sources_obey_chat_mode_and_grants(monkeypatch):
    from types import SimpleNamespace
    from api import chat_connectors as chat
    from api.governance.catalog import route_permission
    from api.governance import resource_scope
    monkeypatch.setattr(resource_scope, "access_for", lambda h: None)
    session = SimpleNamespace(profile="default", chat_mode="super", enabled_toolsets=["connections"])
    assert chat.available_in_chat(None, session, "hosted")
    assert not chat.available_in_chat(None, session, "nango")
    session.chat_mode = "normal"
    assert not chat.available_in_chat(None, session, "hosted")
    session.chat_mode = "super"
    monkeypatch.setattr(resource_scope, "allowed", lambda *args: False)
    assert not chat.available_in_chat(None, session, "hosted")
    for method in ("GET", "POST"):
        assert route_permission("/api/session/connectors", method) == route_permission("/api/integrations/catalog", method)


def test_nonmember_cannot_read_catalog_or_change_selection(monkeypatch):
    from api import chat_connectors as chat
    from types import SimpleNamespace
    actor = {"email": "other@example.test"}
    conversation = SimpleNamespace(owner_email="owner@example.test", participants=[])
    monkeypatch.setattr("api.ownership._request_identity", lambda handler: actor)
    monkeypatch.setattr("api.models.get_session", lambda sid: conversation)
    monkeypatch.setattr("api.project_collaboration.session_access", lambda *_: None)
    monkeypatch.setattr("api.routes.j", lambda handler, body, status=200: status)
    for write in (False, True):
        assert chat.handle(None, {"session_id": "one", "source": "hosted", "key": "calendar", "enabled": False}, write=write) == 403


def test_native_mcp_inventory_uses_chat_profile_and_only_public_metadata():
    from api import chat_connection_inventory as inv
    cfg = {"mcp_servers": {"notion": {"url": "https://private.test/resource", "headers": {"Authorization":"private"}},
                           "docs": {"command":"hidden-command", "enabled":False}, "invalid": {}}}
    rows = inv.mcp_rows(cfg, {"notion"}, None, None)
    assert {r["key"]: r["status"] for r in rows} == {"notion":"configured", "docs":"disabled", "invalid":"invalid"}
    assert "private" not in repr(rows) and "hidden-command" not in repr(rows)
    assert all(r["kinds"] == ["mcp"] for r in rows)


def test_provider_supports_multiple_interfaces_without_an_extra_account_row():
    from api.chat_connectors import source_rows
    providers = [{"unique_key":"crm","display_name":"CRM","configured":True,"auth_mode":"API_KEY","cli_env":["CRM_TOKEN"]},
                 {"unique_key":"notes","display_name":"Notes","configured":True,"auth_mode":"MCP_OAUTH2"}]
    with patch("api.integrations.get_catalog", return_value={"providers":providers,"nango":{"available":True}}), \
         patch("api.integrations.list_connections",return_value=[]), patch("api.ownership.identity_is_admin",return_value=False):
        rows = source_rows({"email":"me@example.test"}, "nango")
    assert [(r["key"],r["kinds"]) for r in rows] == [("crm",["api","cli"]),("notes",["mcp"])]
    assert "CRM_TOKEN" not in repr(rows)


def test_shared_connections_are_visible_only_through_agent_ownership_rules():
    from api.chat_connectors import source_rows
    provider = {"unique_key":"crm","display_name":"CRM","configured":True}
    def connections(email, *, is_admin):
        if not is_admin:
            return []
        return [{"provider_config_key":"crm","connection_id":"shared-id","end_user":None},
                {"provider_config_key":"crm","connection_id":"another-person","end_user":{"id":"other"}}]
    with patch("api.integrations.get_catalog",return_value={"providers":[provider],"nango":{"available":True}}), \
         patch("api.integrations.list_connections",side_effect=connections):
        for admin in (True,False):
            with patch("api.ownership.identity_is_admin",return_value=admin):
                row = source_rows({"email":"me@example.test"}, "nango")[0]
                assert row["organization"] == row["connected"] == admin
                assert row["accounts"] == []


def test_cli_inventory_filters_declared_commands_and_does_not_probe_remote(monkeypatch):
    from types import SimpleNamespace
    from api import chat_connection_inventory as inv
    def policy_entry(names):
        return SimpleNamespace(grants=SimpleNamespace(cli_commands=set(names),cli_denied_commands=set()))
    grant = policy_entry(["gh","gws","*"])
    grant.allows = lambda dimension, name: dimension == "tools" or name == "gh"
    policy = SimpleNamespace(roles={"member":policy_entry(["gh","gws","*"])},users={},groups={})
    with patch.object(inv,"_installed_cli_names",side_effect=AssertionError), patch.object(inv.shutil,"which",side_effect=AssertionError):
        rows = inv.cli_rows({"terminal":{"backend":"docker"}},set(),grant,None,policy)
    assert [(r["key"],r["status"],r["available"]) for r in rows] == [("gh","declared",False)]


def test_model_api_returns_friendly_name_without_connection_details():
    from api import chat_connection_inventory as inv
    config = {"custom_providers":[{"name":"Demo AI","base_url":"https://private.test","api_key":"private-token"}]}
    rows = inv.api_rows(config,set(),set(),None)
    assert [(r["name"],r["kinds"],r["origin"]) for r in rows] == [("Demo AI",["api"],"model")]
    assert "private" not in repr(rows)



def test_mcp_inventory_respects_catalog_permission_and_bot_ceiling():
    from unittest.mock import Mock
    from api import chat_connection_inventory as inv
    cfg = {"mcp_servers":{"notes":{"command":"notes"},"crm":{"url":"https://example.test"}}}
    denied = Mock()
    denied.has_permission.return_value = False
    assert inv.mcp_rows(cfg, {"notes"}, denied, None) == []
    ceiling = Mock()
    ceiling.allows.side_effect = lambda dim, name: name == "notes"
    rows = inv.mcp_rows(cfg, set(), None, ceiling)
    assert [(row["name"],row["available"]) for row in rows] == [("notes", False)]
