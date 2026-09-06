import pytest
import yaml
from api import bot_builder as builder
from api.governance.loader import parse_governance_policy

ADMIN = {"email":"alice@example.test"}
BOB = {"email":"bob@example.test"}
OUT = {"email":"outside@example.test"}

@pytest.fixture
def setup(tmp_path, monkeypatch):
    from api import profiles
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", tmp_path)
    monkeypatch.setattr(profiles, "_validate_profile_model_selection", lambda *a: None)
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({
        "model":{"default":"codex/gpt-6-astra", "provider":"custom:omniroute"},
        "mcp_servers":{"allowed":{"command":"example", "enabled":False}},
    }))
    skill = tmp_path / "skills" / "research"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Research")
    policy = parse_governance_policy({"version":1,"mode":"enforce",
        "bootstrap_admins":["alice@example.test"],
        "roles":{"worker":{"grants":{"permissions":["chat:use", "profiles:admin"], "profiles":["default"],
            "cli":{"commands":["git"]}, "skills":{"load":["research"],"view":["research"]},
            "mcp":{"servers":["allowed"]}}}},
        "groups":{"team":{"roles":["worker"]}},
        "users":{"alice@example.test":{}, "bob@example.test":{"groups":["team"]},
                 "outside@example.test":{"roles":["worker"]}}})
    monkeypatch.setattr("api.governance.loader.get_policy", lambda: policy)
    return tmp_path


def payload():
    return {"name":"research-bot", "title":"Research", "description":"Focused research",
        "system_prompt":"You are a research bot.", "skills":["research"],
        "mcp_servers":["allowed"], "cli_tools":["git"],
        "allowed_users":[], "allowed_groups":[],
        "default_model":"codex/gpt-6-astra", "model_provider":"custom:omniroute"}


def test_create_private_and_no_actor_secrets_copied(setup):
    result = builder.save(ADMIN, payload())
    assert result["config"]["revision"] == 1
    assert builder.allowed(ADMIN, "research-bot")
    assert builder.allowed(BOB, "research-bot") is False
    assert builder.allowed(OUT, "research-bot") is False
    assert not (setup / "profiles/research-bot/.env").exists()
    assert (setup / "profiles/research-bot/SOUL.md").read_text() == payload()["system_prompt"]
    cfg = yaml.safe_load((setup / "profiles/research-bot/config.yaml").read_text())
    assert cfg["model"]["provider"] == "custom:omniroute"
    assert cfg["mcp_servers"]["allowed"]["enabled"] is True


def test_validation_failure_never_publishes_profile(setup):
    body = payload()
    body["mcp_servers"] = ["unknown"]
    with pytest.raises(PermissionError):
        builder.save(ADMIN, body)
    assert not (setup / "profiles/research-bot").exists()
    body = payload()
    body["avatar"] = "data:image/png;base64,AAAA"
    with pytest.raises((ValueError, OSError)):
        builder.save(ADMIN, body)
    assert not (setup / "profiles/research-bot").exists()


def test_duplicate_and_stale_edit_fail_closed(setup):
    builder.save(ADMIN, payload())
    with pytest.raises(RuntimeError):
        builder.save(ADMIN, payload())
    body = {**payload(), "revision":0}
    with pytest.raises(RuntimeError):
        builder.save(ADMIN, body)
    assert builder.get(ADMIN, "research-bot")["config"]["revision"] == 1


def test_share_group_and_revoke_used_by_profile_and_worker_policy(setup):
    from api.governance.enforce import is_profile_allowed_for
    from api.group_chat import bot_allowed
    result = builder.save(ADMIN, {**payload(), "allowed_groups":["team"]})
    assert is_profile_allowed_for(BOB, "research-bot")
    assert bot_allowed(BOB, "research-bot")
    _, rights = builder.access(BOB)
    scoped = builder.constrain_access(BOB, "research-bot", rights)
    assert scoped.is_profile_allowed("research-bot")
    assert scoped.grants.cli_commands == frozenset({"git"})
    assert not scoped.is_tool_allowed("unauthorized_tool")
    builder.save(ADMIN, {**payload(), "revision":result["config"]["revision"]})
    assert not is_profile_allowed_for(BOB, "research-bot")
    assert not bot_allowed(BOB, "research-bot")
    with pytest.raises(PermissionError):
        builder.constrain_access(BOB, "research-bot", rights)


def test_granted_viewer_cannot_edit_or_expand_actor_capabilities(setup):
    builder.save(ADMIN, {**payload(), "allowed_users":[BOB["email"]]})
    with pytest.raises(PermissionError):
        builder.save(BOB, {**payload(), "revision":1})
    _, rights = builder.access(OUT)
    with pytest.raises(PermissionError):
        builder.constrain_access(OUT, "research-bot", rights)


def test_symlink_skill_or_profile_rejected(setup):
    (setup / "skills/research/secret").symlink_to(setup / "config.yaml")
    with pytest.raises(PermissionError):
        builder.save(ADMIN, payload())
    assert not (setup / "profiles/research-bot").exists()


def test_real_engine_binding_preserves_actor_and_bot_ceiling(setup):
    from api.governance.agent_context import bind_governed_agent_turn, reset_governed_agent_turn
    from hermes_cli.dashboard_governance.context import current_governance_context
    from hermes_cli.dashboard_governance.tool_policy import tool_arguments_allowed_for_context
    builder.save(ADMIN, {**payload(), "allowed_users":[BOB["email"]]})
    token = bind_governed_agent_turn(BOB, active_profile="research-bot", session_id="s", request_id="r")
    try:
        ctx = current_governance_context()
        assert ctx.subject.email == BOB["email"]
        assert ctx.bot_access_ceiling.grants.cli_commands == frozenset({"git"})
        assert not tool_arguments_allowed_for_context(ctx, "terminal", {"command":"python script.py"}).allowed
        assert tool_arguments_allowed_for_context(ctx, "terminal", {"command":"git status"}).allowed
        builder.save(ADMIN, {**payload(), "revision":1})
        assert not tool_arguments_allowed_for_context(ctx, "terminal", {"command":"git status"}).allowed
    finally:
        reset_governed_agent_turn(token)


def test_failed_edit_rolls_back_content_and_acl_revision(setup, monkeypatch):
    import os
    builder.save(ADMIN, {**payload(), "allowed_users":[BOB["email"]]})
    original_replace = os.replace
    failed = False
    def fail_final_publish(source, destination):
        nonlocal failed
        from pathlib import Path
        source, destination = Path(source), Path(destination)
        if not failed and source.name == "profile.yaml" and source.parent.name.startswith(".bot-stage-"):
            failed = True
            with pytest.raises(PermissionError):
                builder.allowed(BOB, "research-bot")
            raise OSError("simulated publish failure")
        return original_replace(source, destination)
    monkeypatch.setattr(os, "replace", fail_final_publish)
    with pytest.raises(OSError):
        builder.save(ADMIN, {**payload(), "revision":1, "system_prompt":"NEW_PRIVATE"})
    restored = builder.get(ADMIN, "research-bot")["config"]
    assert restored["revision"] == 1
    assert restored["system_prompt"] == payload()["system_prompt"]
    assert builder.allowed(BOB, "research-bot")


@pytest.mark.parametrize("route,body", [
    ("/api/profile/delete", {"name":"research-bot"}),
    ("/api/profile/create", {"name":"copied-bot", "clone_from":"research-bot", "clone_config":True}),
])
def test_legacy_body_dispatch_cannot_delete_or_clone_private_bot(setup, monkeypatch, route, body):
    from api import routes, profiles
    from types import SimpleNamespace
    from urllib.parse import urlparse
    builder.save(ADMIN, payload())
    monkeypatch.setattr(routes, "_check_csrf", lambda h: True)
    monkeypatch.setattr(routes.governance_api, "handle_governance_api", lambda *a: False)
    monkeypatch.setattr(routes, "_handle_extension_sidecar_proxy", lambda *a, **k: False)
    monkeypatch.setattr(routes, "read_body", lambda h: body)
    monkeypatch.setattr(routes, "_guard_request_session_visibility", lambda *a, **k: True)
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h: BOB)
    response = {}
    monkeypatch.setattr(routes, "bad", lambda h, message, status=400: response.update(status=status))
    monkeypatch.setattr(profiles, "delete_profile_api", lambda *a: pytest.fail("delete reached"))
    monkeypatch.setattr(profiles, "create_profile_api", lambda *a, **k: pytest.fail("clone reached"))
    routes.handle_post(SimpleNamespace(headers={}), urlparse(route))
    assert response["status"] == 403
    assert builder.allowed(ADMIN, "research-bot")


@pytest.mark.parametrize("path,method", [
    ("/api/profile/active","GET"), ("/api/skills/content","GET"),
    ("/api/future-profile-api","GET"),
    ("/api/config","GET"), ("/api/skills/toggle","POST"),
    ("/api/reasoning","POST"), ("/api/commands/exec","POST"), ("/api/personality/set","POST"),
    ("/api/model/set","POST"), ("/api/providers","POST"),
    ("/api/mcp/servers/test","PATCH"), ("/api/mcp/servers/test","DELETE"),
])
def test_revoked_active_cookie_cannot_read_or_mutate_profile(setup, monkeypatch, path, method):
    from urllib.parse import urlparse
    builder.save(ADMIN, payload())
    monkeypatch.setattr("api.profiles.get_active_profile_name", lambda:"research-bot")
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h:BOB)
    statuses = []
    monkeypatch.setattr("api.helpers.bad", lambda h, message, status:statuses.append(status))
    assert builder.guard_profile_request(object(), urlparse(path + "?profile=default"), method) is False
    assert statuses == [403]


def test_shared_viewer_cannot_mutate_bot_but_can_switch_and_use_personal_memory(setup, monkeypatch):
    from urllib.parse import urlparse
    builder.save(ADMIN, {**payload(), "allowed_users":[BOB["email"]]})
    monkeypatch.setattr("api.profiles.get_active_profile_name", lambda:"research-bot")
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h:BOB)
    monkeypatch.setattr("api.helpers.bad", lambda *a:None)
    assert builder.guard_profile_request(object(), urlparse("/api/profile/active"), "GET")
    assert not builder.guard_profile_request(object(), urlparse("/api/skills/toggle"), "POST")
    assert builder.guard_profile_request(object(), urlparse("/api/profile/switch"), "POST")
    assert builder.guard_profile_request(object(), urlparse("/api/memory"), "GET")


def test_revoked_bot_is_rejected_before_chat_enqueue(setup):
    from api import routes
    from types import SimpleNamespace
    builder.save(ADMIN, payload())
    session = SimpleNamespace(profile="research-bot", owner_email=BOB["email"],
                              participants=[], bot_participants=[])
    result = routes._start_chat_stream_for_session(session, msg="hello", workspace=str(setup),
        model="codex/gpt-6-astra", sender_identity=BOB)
    assert result["_status"] == 403


def test_legacy_large_skills_unchanged_preserve_tree_and_wildcard(setup):
    for i in range(102):
        path = setup / "skills" / ("skill" + str(i))
        path.mkdir()
        (path / "SKILL.md").write_text("# skill")
    (setup / "SOUL.md").write_text("Legacy bot")
    existing = builder.get(ADMIN, "default")["config"]
    assert len(existing["skills"]) > 100
    existing.pop("avatar_url")
    existing["system_prompt"] = "Updated instructions"
    before = (setup / "skills/research/SKILL.md").stat().st_ino
    result = builder.save(ADMIN, existing)
    assert result["config"]["system_prompt"] == "Updated instructions"
    assert (setup / "skills/research/SKILL.md").stat().st_ino == before
    _, rights = builder.access(ADMIN)
    assert builder.access_ceiling(ADMIN, "default", rights).grants.skills_load == frozenset({"*"})


def test_recovery_session_routes_remain_available_with_revoked_cookie(setup, monkeypatch):
    from urllib.parse import urlparse
    builder.save(ADMIN, payload())
    monkeypatch.setattr("api.profiles.get_active_profile_name", lambda:"research-bot")
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h:BOB)
    assert builder.guard_profile_request(object(), urlparse("/api/session/load?session_id=own"), "GET")
