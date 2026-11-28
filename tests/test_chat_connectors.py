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
        assert [row["provider_config_key"] for row in resolver._rows()] == ["calendar"]
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
