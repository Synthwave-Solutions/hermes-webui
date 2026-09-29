"""Real catalog handler serialization stays within each request's MCP scope."""
from copy import deepcopy
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from api import routes
from api.governance import enforce, loader


@pytest.fixture
def catalog(monkeypatch):
    identity = {"email": "reader@example.test", "method": "qa"}
    state = {"raw": {}}
    source = {
        "public": {"connected": True, "tools": [
            {"name": "mcp__public__read", "description": "PUBLIC", "inputSchema": {}},
            {"name": "mcp__public__secret", "description": "PRIVATE_TOOL", "inputSchema": {}}]},
        "private": {"connected": False, "tools": [{"name": "mcp__private__read", "description": "PRIVATE_SERVER"}]},
        "other-profile": {"connected": True, "tools": [{"name": "mcp__other_profile__read", "description": "OTHER_PROFILE"}]},
    }
    config = {"mcp_servers": {name: {"command": "qa-only", "enabled": True}
                              for name in ("public", "private", "joplin")},
              "webui_external_notes_sources": True}
    monkeypatch.setattr(routes, "get_config", lambda: deepcopy(config))
    monkeypatch.setattr(routes, "_mcp_runtime_status_by_name", lambda: source)
    monkeypatch.setattr(routes, "_mcp_tools_from_registry", lambda _: [])
    monkeypatch.setattr("api.mcp_requests.sync_approved_quietly", lambda **_: None)
    monkeypatch.setattr(enforce, "_request_identity", lambda _: identity)
    monkeypatch.setattr(loader, "get_policy", lambda: loader.parse_governance_policy(deepcopy(state["raw"])))
    monkeypatch.setattr(routes, "j", lambda _, body, status=200, **__: (status, body))
    monkeypatch.setattr(routes, "bad", lambda _, message, status=400: (status, {"error": message}))

    def policy(*, deny=None, access_mode="blacklist", grants=None, role_grants=None, mode="enforce"):
        state["raw"] = {"mode": mode, "bootstrap_admins": ["owner@example.test"],
            "roles": {"member": {"grants": role_grants or {
                "mcp": {"servers": ["*"], "tools": {"*": ["*"]}}}}},
            "users": {"reader@example.test": {"roles": ["member"],
                "access_level": "elevated", "access_mode": access_mode,
                "grants": grants or {}, "deny": deny or {}}}}
    policy(deny={"mcp": {"servers": ["private", "joplin"]}})
    return SimpleNamespace(identity=identity, policy=policy, state=state, source=source,
                           handler=SimpleNamespace(path="/api/mcp/tools", command="GET"))


def test_server_deny_filters_catalog_runtime_and_unavailable_names_without_mutating_cache(catalog):
    before = deepcopy(catalog.source)
    status, result = routes._handle_mcp_tools_list(catalog.handler)
    assert status == 200
    assert result["total"] == 2
    assert {row["server"] for row in result["tools"]} == {"public"}
    assert result["unavailable_servers"] == []
    assert "PRIVATE_SERVER" not in str(result)
    assert "OTHER_PROFILE" not in str(result)
    assert catalog.source == before
    status, result = routes._handle_mcp_servers_list(catalog.handler)
    assert status == 200
    assert [row["name"] for row in result["servers"]] == ["public"]
    assert result["servers"][0]["tool_count"] == 2


def test_two_readers_and_revocation_filter_shared_inventory_on_every_request(catalog):
    catalog.identity["email"] = "owner@example.test"
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["total"] == 3
    catalog.identity["email"] = "reader@example.test"
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["total"] == 2
    catalog.policy(deny={"mcp": {"servers": ["*"]}})
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["tools"] == []
    catalog.identity["email"] = "owner@example.test"
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["total"] == 3


@pytest.mark.parametrize("denial", [
    {"mcp": {"tools": {"public": ["secret"]}}},
    {"mcp": {"tools": {"*": ["mcp__public__secret"]}}},
    {"tools": {"builtins": ["mcp__public__secret"]}},
])
def test_tool_denial_survives_wildcard_server_and_tool_grants(catalog, denial):
    catalog.policy(deny=denial)
    _, result = routes._handle_mcp_tools_list(catalog.handler)
    assert "PRIVATE_TOOL" not in str(result)
    assert any(row["name"] == "mcp__public__read" for row in result["tools"])


def test_empty_whitelist_catalog_is_empty_even_with_wildcard_role(catalog):
    catalog.policy(access_mode="whitelist")
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["tools"] == []
    assert routes._handle_mcp_servers_list(catalog.handler)[1]["servers"] == []


def test_whitelist_grant_does_not_exceed_assigned_mcp_role(catalog):
    catalog.policy(access_mode="whitelist",
        grants={"mcp": {"servers": ["*"], "tools": {"*": ["*"]}}},
        role_grants={"mcp": {"servers": ["public"], "tools": {"public": ["mcp__public__read"]}}})
    _, result = routes._handle_mcp_tools_list(catalog.handler)
    assert [row["name"] for row in result["tools"]] == ["mcp__public__read"]


@pytest.mark.parametrize("mode", ["off", "report_only"])
def test_inactive_governance_retains_catalog_behavior_but_not_other_profile_cache(catalog, mode):
    catalog.policy(mode=mode, deny={"mcp": {"servers": ["*"]}})
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["total"] == 3


def test_legacy_omitted_resource_dimension_keeps_route_level_read_behavior(catalog):
    catalog.state["raw"] = {"mode": "enforce", "users": {"reader@example.test": {}}}
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["total"] == 3


def test_policy_error_never_returns_cached_inventory(catalog, monkeypatch):
    monkeypatch.setattr(loader, "get_policy", lambda: (_ for _ in ()).throw(ValueError("invalid policy")))
    assert routes._handle_mcp_tools_list(catalog.handler)[0] == 403
    assert routes._handle_mcp_servers_list(catalog.handler)[0] == 403


def test_denied_notes_source_cannot_reach_search_detail_or_recent_note_reader(catalog, monkeypatch):
    monkeypatch.setattr(routes, "_joplin_search_notes", lambda *_a, **_k: pytest.fail("denied source searched"))
    monkeypatch.setattr(routes, "_joplin_get_note", lambda *_a, **_k: pytest.fail("denied source read"))
    monkeypatch.setattr(routes, "_joplin_recent_ai_notes", lambda *_a, **_k: pytest.fail("denied recent notes read"))
    assert routes._handle_notes_search(catalog.handler, urlparse("/api/notes/search?source=joplin&q=private"))[0] == 403
    assert routes._handle_notes_item(catalog.handler, urlparse("/api/notes/item?source=joplin&id=" + "a" * 32))[0] == 403
    status, result = routes._handle_notes_sources_list(catalog.handler)
    assert status == 200
    assert result["recent_ai_notes"] == []
    assert "joplin" not in str(result)


def test_registry_fallback_is_filtered_and_does_not_reintroduce_denied_or_other_profile_rows(catalog, monkeypatch):
    monkeypatch.setattr(routes, "_mcp_runtime_status_by_name", lambda: {})
    source = [{"name": "mcp__" + name.replace("-", "_") + "__read", "server": name}
              for name in ("public", "private", "other-profile")]
    monkeypatch.setattr(routes, "_mcp_tools_from_registry", lambda _: source)
    assert routes._handle_mcp_tools_list(catalog.handler)[1]["tools"] == [source[0]]
    assert len(source) == 3


@pytest.fixture
def notes_readers(monkeypatch):
    calls = []

    def search(query, *, limit):
        calls.append(("search", query))
        return [{"id": "a" * 32, "title": "QA_ALLOWED_SEARCH"}]

    def item(note_id):
        calls.append(("item", note_id))
        return {"id": note_id, "body": "QA_ALLOWED_NOTE"}

    def recent(*, limit):
        calls.append(("recent", limit))
        return [{"id": "a" * 32, "title": "QA_ALLOWED_RECENT"}]

    monkeypatch.setattr(routes, "_joplin_search_notes", search)
    monkeypatch.setattr(routes, "_joplin_get_note", item)
    monkeypatch.setattr(routes, "_joplin_recent_ai_notes", recent)
    return calls


def _notes_search(catalog):
    return routes._handle_notes_search(catalog.handler, urlparse("/api/notes/search?source=joplin&q=QA"))


def _notes_item(catalog):
    return routes._handle_notes_item(catalog.handler, urlparse("/api/notes/item?source=joplin&id=" + "a" * 32))


def _joplin_hints(catalog):
    status, payload = routes._handle_notes_sources_list(catalog.handler)
    assert status == 200
    row = next(row for row in payload["sources"] if row["name"] == "joplin")
    return [tool["name"] for tool in row["tools"]], payload["recent_ai_notes"]


@pytest.mark.parametrize("denial", [
    {"mcp": {"tools": {"joplin": ["*"]}}},
    {"mcp": {"tools": {"*": ["mcp__joplin__*"]}}},
    {"tools": {"builtins": ["mcp__joplin__*"]}},
    {"tools": {"toolsets": ["mcp-joplin"]}},
])
def test_notes_tool_deny_blocks_search_item_recent_and_inferred_hints(catalog, notes_readers, denial):
    catalog.policy(deny=denial)
    assert _notes_search(catalog)[0] == 403
    assert _notes_item(catalog)[0] == 403
    hints, recent = _joplin_hints(catalog)
    assert hints == []
    assert recent == []
    assert notes_readers == []


@pytest.mark.parametrize("tool", ["search_notes", "mcp__joplin__search_notes"])
def test_notes_search_deny_preserves_permitted_item_and_recent_reads(catalog, notes_readers, tool):
    catalog.policy(deny={"mcp": {"tools": {"joplin": [tool]}}})
    assert _notes_search(catalog)[0] == 403
    assert _notes_item(catalog) == (200, {"source": "joplin", "note": {"id": "a" * 32, "body": "QA_ALLOWED_NOTE"}})
    hints, recent = _joplin_hints(catalog)
    assert hints == ["list_notes", "get_note"]
    assert recent[0]["title"] == "QA_ALLOWED_RECENT"
    assert [call[0] for call in notes_readers] == ["item", "recent"]


@pytest.mark.parametrize("tool", ["get_note", "mcp__joplin__get_note"])
def test_notes_item_deny_blocks_recent_reads_without_blocking_search(catalog, notes_readers, tool):
    catalog.policy(deny={"mcp": {"tools": {"joplin": [tool]}}})
    assert _notes_item(catalog)[0] == 403
    assert _notes_search(catalog)[1]["results"][0]["title"] == "QA_ALLOWED_SEARCH"
    hints, recent = _joplin_hints(catalog)
    assert hints == ["search_notes", "list_notes"]
    assert recent == []
    assert [call[0] for call in notes_readers] == ["search"]


def test_notes_whitelist_search_only_cannot_read_items_or_recent_notes(catalog, notes_readers):
    catalog.policy(access_mode="whitelist", grants={"mcp": {"servers": ["joplin"], "tools": {"joplin": ["search_notes"]}}})
    assert _notes_search(catalog)[0] == 200
    assert _notes_item(catalog)[0] == 403
    assert _joplin_hints(catalog) == (["search_notes"], [])
    assert [call[0] for call in notes_readers] == ["search"]


def test_notes_tool_revocation_is_checked_on_next_request(catalog, notes_readers):
    catalog.policy()
    assert _notes_search(catalog)[0] == 200
    assert _notes_item(catalog)[0] == 200
    assert _joplin_hints(catalog)[0] == ["search_notes", "list_notes", "get_note"]
    notes_readers.clear()
    catalog.policy(deny={"mcp": {"tools": {"joplin": ["*"]}}})
    assert _notes_search(catalog)[0] == 403
    assert _notes_item(catalog)[0] == 403
    assert _joplin_hints(catalog) == ([], [])
    assert notes_readers == []
