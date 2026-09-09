"""Async jobs retain their actual initiator and bounded authority after restart."""
from copy import deepcopy
from contextvars import copy_context
from types import SimpleNamespace
import json
import stat

import pytest

from api.governance import agent_context, continuation, loader

EMAIL = "initiator@example.test"
IDENTITY = {"email": EMAIL, "groups": ["sso-no-write"], "method": "oidc",
            "claims_subset": {"sub": "sso-subject", "name": "Initiator"},
            "access_token": "MUST_NOT_BE_PERSISTED"}
POLICY = {"version": 1, "mode": "enforce", "default_effect": "deny",
          "roles": {"member": {"grants": {
              "permissions": ["chat:use", "sessions:read", "sessions:write"], "routes": ["*"],
              "profiles": ["default"], "tools": {"builtins": ["read_file", "write_file"]},
              "models": {"providers": ["qa"], "models": ["qa-model"]}}}},
          "groups": {"sso-no-write": {"grants": {"files": {"denied_globs": ["/qa/protected/*"]}}}},
          "users": {EMAIL: {"roles": ["member"]}, "later@example.test": {"roles": ["member"]}}}


@pytest.fixture
def world(monkeypatch, tmp_path):
    from api import auth, bot_builder, project_collaboration
    module = agent_context._agent_governance_module()  # Real paired engine is required.
    monkeypatch.setattr(continuation, "_directory", lambda: tmp_path / "authority")
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(bot_builder, "managed", lambda *_: None)
    monkeypatch.setattr(bot_builder, "access_ceiling", lambda *_: None)
    monkeypatch.setattr(project_collaboration, "session_access", lambda *_: None)
    current = {"policy": loader.parse_governance_policy(deepcopy(POLICY))}
    monkeypatch.setattr(loader, "get_policy", lambda: current["policy"])
    session = SimpleNamespace(session_id="parent123", owner_email=EMAIL, profile="default",
                              participants=["later@example.test"], bot_participants=[])
    tokens = []
    def begin(identity=IDENTITY, reference=None, capture=True):
        token = agent_context.bind_governed_agent_turn(identity, active_profile="default", session_id=session.session_id)
        try:
            child = continuation.begin_turn(session, identity, active_profile="default", request_id="run123", reference=reference)
        except BaseException:
            agent_context.reset_governed_agent_turn(token)
            raise
        tokens.append((token, child))
        return continuation.current_ref() if capture else None
    def end():
        parent, child = tokens.pop()
        continuation.end_turn(child)
        agent_context.reset_governed_agent_turn(parent)
    yield SimpleNamespace(session=session, module=module, begin=begin, end=end, current=current, root=tmp_path)
    while tokens:
        end()


def test_private_record_contains_verified_groups_but_no_auth_credentials(world):
    ref = world.begin()
    path = world.root / "authority" / (ref + ".json")
    assert len(ref) == 32
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    data = json.loads(path.read_text())
    assert data["identity"]["groups"] == ["sso-no-write"]
    assert "MUST_NOT_BE_PERSISTED" not in path.read_text()
    assert "continuation" not in vars(world.session)
    world.end()
    assert continuation.current_ref() == ""
    assert continuation.resolve(ref, world.session)["identity"]["email"] == EMAIL


def test_ordinary_authenticated_turn_does_not_persist_unused_authority(world):
    world.begin(capture=False)
    world.end()
    assert not (world.root / "authority").exists()


def test_parallel_async_producers_capture_one_complete_private_record(world):
    from concurrent.futures import ThreadPoolExecutor
    world.begin(capture=False)
    contexts = [copy_context() for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs = list(pool.map(lambda context: context.run(continuation.current_ref), contexts))
    assert len(set(refs)) == 1
    assert len(list((world.root / "authority").glob("*.json"))) == 1
    assert continuation.resolve(refs[0], world.session)["identity"]["groups"] == ["sso-no-write"]


def test_storage_capacity_rejects_new_jobs_but_preserves_existing_delayed_ref(world, monkeypatch):
    monkeypatch.setattr(continuation, "MAX_AUTHORITY_RECORDS", 1)
    existing = world.begin(); world.end()
    assert json.loads((world.root / "authority" / (existing + ".json")).read_text())["created_at"] > 0
    world.begin(capture=False)
    with pytest.raises(PermissionError, match="storage is full"):
        continuation.current_ref()
    world.end()
    assert world.begin(reference=existing) == existing
    assert len(list((world.root / "authority").glob("*.json"))) == 1


@pytest.mark.parametrize("mode", ["enforce", "off"])
def test_real_binder_keeps_live_workspace_check_when_policy_is_disabled(world, mode):
    from hermes_cli.dashboard_governance.tool_policy import tool_allowed_for_context, tool_arguments_allowed_for_context
    policy = deepcopy(POLICY); policy["mode"] = mode
    world.current["policy"] = loader.parse_governance_policy(policy)
    state = {"allowed": True}
    checker = lambda path: state["allowed"] and path != "/qa/another-private/file.txt"
    token = agent_context.bind_governed_agent_turn(IDENTITY, active_profile="default", session_id="parent123",
                                                 workspace_path="/qa", workspace_access_check=checker)
    try:
        ctx = world.module.current_governance_context()
        assert ctx.workspace_path == "/qa"
        registry = SimpleNamespace(get=lambda *_: None)
        assert tool_allowed_for_context(ctx, "read_file", registry).allowed
        assert not tool_arguments_allowed_for_context(ctx, "read_file", {"path": "/qa/another-private/file.txt"}).allowed
        state["allowed"] = False
        assert not tool_allowed_for_context(ctx, "read_file", registry).allowed
    finally:
        agent_context.reset_governed_agent_turn(token)


def test_later_group_participant_cannot_replace_prior_jobs_identity(world):
    original = world.begin(); world.end()
    newer = world.begin({"email": "later@example.test", "groups": [], "method": "oidc"}); world.end()
    assert original != newer
    assert continuation.resolve(original, world.session)["identity"]["email"] == EMAIL
    assert continuation.resolve(newer, world.session)["identity"]["email"] == "later@example.test"
    resumed = world.begin(reference=original)
    assert resumed == original
    assert world.module.current_governance_context().subject.groups == ("sso-no-write",)


@pytest.mark.parametrize("field,value", [("session_id", "other"), ("owner_email", "later@example.test"), ("profile", "other")])
def test_foreign_session_owner_or_profile_cannot_reuse_authority(world, field, value):
    ref = world.begin(); world.end()
    setattr(world.session, field, value)
    with pytest.raises(PermissionError, match="does not match"):
        continuation.resolve(ref, world.session)


@pytest.mark.parametrize("ref", [None, "", "../authority", "a" * 32])
def test_missing_and_forged_refs_cannot_fall_back_to_owner(world, ref):
    with pytest.raises(PermissionError, match="unavailable"):
        continuation.resolve(ref, world.session)


def test_worker_rejects_email_only_identity_losing_authenticated_sso_groups(world):
    ref = world.begin(); world.end()
    with pytest.raises(PermissionError, match="actor or execution profile changed"):
        world.begin({"email": EMAIL, "groups": [], "method": "oidc"}, reference=ref)


def test_original_group_deny_survives_later_policy_expansion(world):
    from hermes_cli.dashboard_governance.tool_policy import tool_allowed_for_context, tool_arguments_allowed_for_context
    ref = world.begin(); world.end()
    expanded = deepcopy(POLICY)
    expanded["groups"] = {}
    expanded["roles"]["member"]["grants"]["tools"]["builtins"].append("terminal")
    world.current["policy"] = loader.parse_governance_policy(expanded)
    world.begin(reference=ref)
    ctx = world.module.current_governance_context()
    assert ctx.access.deny.is_empty()
    registry = SimpleNamespace(get=lambda *_: None)
    assert tool_allowed_for_context(ctx, "read_file", registry).allowed
    assert tool_arguments_allowed_for_context(ctx, "write_file", {"path": "/qa/allowed.txt"}).allowed
    assert not tool_arguments_allowed_for_context(ctx, "write_file", {"path": "/qa/protected/file.txt"}).allowed
    assert not tool_allowed_for_context(ctx, "terminal", registry).allowed


def test_fresh_policy_revocation_blocks_continuation(world):
    ref = world.begin(); world.end()
    revoked = deepcopy(POLICY)
    revoked["users"][EMAIL]["deny"] = {"permissions": ["chat:use"]}
    world.current["policy"] = loader.parse_governance_policy(revoked)
    with pytest.raises(PermissionError, match="access was revoked"):
        continuation.resolve(ref, world.session)


def test_removed_original_participant_cannot_continue_as_conversation_owner(world):
    world.session.owner_email = "later@example.test"
    world.session.participants = [EMAIL]
    ref = world.begin(); world.end()
    world.session.participants = []
    with pytest.raises(PermissionError, match="no longer a member"):
        continuation.resolve(ref, world.session)


def test_ref_is_context_local_and_cleanup_does_not_erase_inherited_child(world):
    ref = world.begin()
    child = copy_context()
    world.end()
    assert continuation.current_ref() == ""
    assert child.run(continuation.current_ref) == ref


def test_async_start_routes_exact_stored_identity_without_owner_fallback(world, monkeypatch):
    from api import routes
    ref = world.begin(); world.end()
    received = []
    monkeypatch.setattr(routes, "get_session", lambda *_: world.session)
    assert routes.start_session_turn("parent123", "completed", source="async_delegation")["_status"] == 403
    world.session.model = "qa-model"; world.session.model_provider = "qa"
    monkeypatch.setattr(routes, "_resolve_chat_workspace_with_recovery", lambda *_: "/qa")
    monkeypatch.setattr(routes, "_read_profile_model_config", lambda *_: ("qa", "qa-model", {}))
    monkeypatch.setattr(routes, "_resolve_compatible_session_model_state", lambda *_a, **_kw: ("qa-model", "qa", False))
    monkeypatch.setattr(routes, "_start_run", lambda _s, **kw: received.append(kw) or {"_status": 200, "stream_id": "started"})
    result = routes.start_session_turn("parent123", "completed", source="async_delegation", continuation_ref=ref)
    assert result["_status"] == 200
    assert received[0]["sender_identity"]["groups"] == ["sso-no-write"]
    assert received[0]["sender_email"] == EMAIL
    assert received[0]["continuation_ref"] == ref


def test_auth_disabled_ownerless_legacy_continuation_remains_compatible(world, monkeypatch):
    from api import auth, routes
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    world.session.owner_email = ""; world.session.participants = []
    world.session.model = "qa-model"; world.session.model_provider = "qa"
    received = []
    monkeypatch.setattr(routes, "get_session", lambda *_: world.session)
    monkeypatch.setattr(routes, "_resolve_chat_workspace_with_recovery", lambda *_: "/qa")
    monkeypatch.setattr(routes, "_read_profile_model_config", lambda *_: ("qa", "qa-model", {}))
    monkeypatch.setattr(routes, "_resolve_compatible_session_model_state", lambda *_a, **_kw: ("qa-model", "qa", False))
    monkeypatch.setattr(routes, "_start_run", lambda _s, **kw: received.append(kw) or {"_status": 200})
    assert routes.start_session_turn("parent123", "complete", source="async_delegation")["_status"] == 200
    assert "sender_identity" not in received[0] and "continuation_ref" not in received[0]
    assert routes.start_session_turn("parent123", "complete", source="async_delegation", continuation_ref="forged")["_status"] == 403
    world.session.owner_email = EMAIL
    assert routes.start_session_turn("parent123", "complete", source="async_delegation")["_status"] == 403
