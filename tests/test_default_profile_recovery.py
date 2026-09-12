"""Scoped default/own bot roundtrip; all profiles, identities and chats are synthetic."""
import io
import json
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest


@pytest.fixture
def profile_client(tmp_path, monkeypatch):
    from api import auth, config, gateway_watcher, helpers, models, profiles, routes
    from api.governance import enforce, loader

    actor = "developer@example.test"
    root = tmp_path / "hermes"
    own = root / "profiles" / "own-bot"
    other = root / "profiles" / "other-bot"
    own.mkdir(parents=True)
    other.mkdir()
    for home in (root, own, other):
        (home / "config.yaml").write_text("model:\n  default: synthetic-model\n  provider: synthetic\n")
    (own / "profile.yaml").write_text("synpulse_builder:\n  owner_email: developer@example.test\n")
    (other / "profile.yaml").write_text("synpulse_builder:\n  owner_email: other@example.test\n")
    rows = [{"name": name, "is_default": name == "default", "visible": True,
             "path": str(home), "model": "synthetic-model"}
            for name, home in (("default", root), ("own-bot", own), ("other-bot", other))]
    state = SimpleNamespace(actor=actor, profile="own-bot", scan_unavailable=False, list_calls=[])

    def catalog(*, fast=False, include_skill_counts=True):
        state.list_calls.append((fast, include_skill_counts))
        if state.scan_unavailable and not fast:
            raise RuntimeError("Unrelated profile skill scan unavailable")
        return [dict(row) for row in rows]

    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", root)
    monkeypatch.setattr(profiles, "_active_profile", "default")
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(profiles, "list_profiles_api", catalog)
    monkeypatch.setattr(profiles, "_root_profile_name_cache", {"default"})
    monkeypatch.setattr(profiles, "_root_profile_name_cache_loaded", True)
    monkeypatch.setattr(config, "invalidate_models_cache", lambda: None)
    monkeypatch.setattr(gateway_watcher, "restart_watcher_for_profile", lambda name: None)
    monkeypatch.setattr("api.workspace_access.resolve_implicit_workspace", lambda *a, **kw: None)
    monkeypatch.setattr(helpers, "build_profile_cookie", lambda name, handler: "fixture-profile=" + name)
    monkeypatch.setattr(routes, "_check_csrf", lambda handler: True)
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "parse_cookie", lambda handler: state.actor)
    monkeypatch.setattr(auth, "get_session_identity", lambda cookie: {"email": cookie, "groups": []})
    policy = loader.parse_governance_policy({"version": 1, "mode": "enforce",
        "users": {actor: {"grants": {"permissions": ["profiles:read", "chat:use", "sessions:read"],
            "routes": ["/api/*"], "profiles": ["own-bot"]}}}})
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    monkeypatch.setenv("HERMES_WEBUI_USER_ISOLATION", "1")
    monkeypatch.setattr(models, "PROJECTS_FILE", tmp_path / "projects.json")
    chats = [models.Session(session_id=sid, profile=profile, owner_email=owner,
               messages=[{"role": "user", "content": content}], title=content)
             for sid, profile, owner, content in (
                 ("my-morning", "default", actor, "Morning conversation"),
                 ("my-bot-chat", "own-bot", actor, "Own bot conversation"),
                 ("foreign-morning", "default", "other@example.test", "Other person private"),
                 ("legacy-unowned", "default", None, "Unclaimed private history"))]
    monkeypatch.setattr(routes, "all_sessions", lambda **kw: [s.compact() for s in chats])
    monkeypatch.setattr(routes, "_reconcile_stale_stream_state_for_session_rows", lambda rows: False)
    monkeypatch.setattr(routes, "_prune_orphaned_webui_zero_message_sessions", lambda rows, **kw: rows)

    def request(path, body=None):
        raw = json.dumps(body or {}).encode()
        handler = SimpleNamespace(headers={"Content-Length": str(len(raw))},
                                  rfile=io.BytesIO(raw), command="GET" if body is None else "POST")
        captured = {}
        monkeypatch.setattr(routes, "j", lambda h, data, **kw: captured.update(
            status=kw.get("status", 200), data=data, headers=kw.get("extra_headers", {})) or True)
        monkeypatch.setattr(routes, "bad", lambda h, error, status=400: captured.update(
            status=status, data={"error": error}, headers={}) or True)
        decision = enforce.evaluate_request({"email": state.actor}, handler.command, path)
        assert decision.allow, decision
        profiles.set_request_profile(state.profile)
        try:
            if body is None:
                routes.handle_get(handler, urlparse(path))
            else:
                routes.handle_post(handler, urlparse(path))
            if captured["status"] == 200 and path == "/api/profile/switch":
                assert captured["headers"]["Set-Cookie"] == "fixture-profile=" + body["name"]
                state.profile = captured["data"]["active"]
            return captured["status"], captured["data"]
        finally:
            profiles.clear_request_profile()

    def visible():
        payload = routes._build_session_list_cache_payload(state.profile, False, False, False, False,
                                                          owner_scope=state.actor)
        return {row["session_id"] for row in payload["sessions"]}

    state.request, state.visible, state.chats, state.own_home = request, visible, chats, own
    yield state
    profiles.clear_request_profile()


def test_scoped_developer_roundtrip_recovers_only_own_default_history(profile_client):
    client = profile_client
    status, payload = client.request("/api/profiles?fast=1")
    assert status == 200
    assert {p["name"] for p in payload["profiles"]} == {"default", "own-bot"}
    assert client.visible() == {"my-bot-chat"}
    before = [(s.session_id, s.profile, s.owner_email, list(s.messages)) for s in client.chats]
    assert client.request("/api/profile/switch", {"name": "default"})[0] == 200
    assert client.visible() == {"my-morning"}
    assert client.request("/api/profile/switch", {"name": "own-bot"})[0] == 200
    assert client.visible() == {"my-bot-chat"}
    assert before == [(s.session_id, s.profile, s.owner_email, list(s.messages)) for s in client.chats]
    assert client.request("/api/profile/switch", {"name": "other-bot"})[0] == 403
    assert client.profile == "own-bot"


def test_switch_response_does_not_disclose_unavailable_profiles(profile_client):
    status, payload = profile_client.request("/api/profile/switch", {"name": "default"})
    assert status == 200
    assert {p["name"] for p in payload["profiles"]} == {"default", "own-bot"}


def test_default_recovery_does_not_wait_for_unrelated_skill_scan(profile_client):
    profile_client.scan_unavailable = True
    status, payload = profile_client.request("/api/profile/switch", {"name": "default"})
    assert status == 200, payload
    assert profile_client.profile == "default"
    assert profile_client.visible() == {"my-morning"}
    assert all(fast for fast, _ in profile_client.list_calls)


def test_revoked_bot_stays_unavailable_while_default_recovery_remains_possible(profile_client):
    client = profile_client
    client.own_home.joinpath("profile.yaml").write_text("synpulse_builder:\n  owner_email: other@example.test\n")
    status, payload = client.request("/api/profile/switch", {"name": "default"})
    assert status == 200
    assert [p["name"] for p in payload["profiles"]] == ["default"]
    assert client.visible() == {"my-morning"}
    assert client.request("/api/profile/switch", {"name": "own-bot"})[0] == 403
    assert client.profile == "default"
