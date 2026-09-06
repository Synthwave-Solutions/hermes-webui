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
        "roles":{"worker":{"grants":{"permissions":["chat:use"], "profiles":["default"],
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
