"""Real engine review-thread routing with synthetic homes; no skill writes."""
import threading
import queue
from types import SimpleNamespace

import pytest


@pytest.fixture
def engine(monkeypatch, tmp_path):
    from api import profiles
    import hermes_constants as constants
    from run_agent import AIAgent
    from agent import background_review
    from tools import skills_tool, skill_manager_tool, thread_context

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "launch"))
    monkeypatch.setattr(profiles, "_hermes_home_override_available", None)
    monkeypatch.setattr(background_review, "load_background_review_settings", lambda: (True, {}))
    # The real context propagation remains in use; terminal UI callbacks are
    # irrelevant to the read-only worker and must never invoke user interaction.
    monkeypatch.setattr(thread_context, "_callback_api", lambda: (
        lambda: None, lambda: None, lambda value: None, lambda value: None))
    for module in (skills_tool, skill_manager_tool):
        monkeypatch.setattr(module, "SKILLS_DIR", module._SKILLS_DIR_AT_IMPORT)
        monkeypatch.setattr(module, "HERMES_HOME", module._SKILLS_DIR_AT_IMPORT.parent)
    return profiles, constants, AIAgent, background_review, skills_tool, skill_manager_tool


def test_real_background_review_keeps_original_skill_roots_after_other_profile_patch(engine, monkeypatch, tmp_path):
    profiles, constants, Agent, review, skills, manager = engine
    first, second = tmp_path / "actor-a", tmp_path / "actor-b"
    entered, release, done = threading.Event(), threading.Event(), threading.Event()
    captured = {}
    from tools import memory_tool
    from hermes_cli.dashboard_governance import context as governance
    actor_scope = SimpleNamespace(subject="actor-a")
    personal_dir = tmp_path / "personal-a"

    def target():
        entered.set()
        try:
            if not release.wait(5):
                captured["error"] = "release timed out"
                return
            captured.update(home=constants.get_hermes_home(), skills=skills._skills_dir(),
                            manager=manager._skills_dir(), actor=governance.current_governance_context(),
                            personal_memory=memory_tool.get_memory_dir())
        finally:
            done.set()

    monkeypatch.setattr(review, "spawn_background_review_thread", lambda *a, **kw: (target, ""))
    actor_token = governance.bind_governance_context(actor_scope)
    memory_token = memory_tool.bind_personal_memory_dir(personal_dir)
    home_token = constants.set_hermes_home_override(first)
    try:
        profiles.patch_skill_home_modules(first)
        Agent._spawn_background_review(SimpleNamespace(), [], review_skills=True)
        assert entered.wait(5)
    finally:
        constants.reset_hermes_home_override(home_token)
        governance.reset_governance_context(actor_token)
        memory_tool.reset_personal_memory_dir(memory_token)
    second_token = constants.set_hermes_home_override(second)
    try:
        profiles.patch_skill_home_modules(second)
        release.set()
        assert done.wait(5)
        assert captured == {"home": first, "skills": first / "skills",
                            "manager": first / "skills", "actor": actor_scope,
                            "personal_memory": personal_dir}
        assert constants.get_hermes_home() == second
    finally:
        release.set()
        constants.reset_hermes_home_override(second_token)


@pytest.mark.parametrize("raises", [False, True])
def test_streaming_home_scope_restores_nested_context_on_every_exit(engine, tmp_path, raises):
    profiles, constants, *_ = engine
    outer, inner = tmp_path / "outer", tmp_path / "inner"
    token = constants.set_hermes_home_override(outer)
    try:
        try:
            with profiles.agent_profile_home_context(inner):
                assert constants.get_hermes_home() == inner
                if raises:
                    raise RuntimeError("fixture failure")
        except RuntimeError:
            assert raises
        assert constants.get_hermes_home() == outer
    finally:
        constants.reset_hermes_home_override(token)


def test_actual_streaming_worker_binds_before_config_and_cleans_up_on_failure(engine, monkeypatch, tmp_path):
    profiles, constants, *_ = engine
    from api import streaming, personal_context, project_collaboration, workspace_access
    from api import approval_resume, background_process
    home, workspace = tmp_path / "profile", tmp_path / "workspace"
    session = SimpleNamespace(session_id="fixture-profile-scope", owner_email=None,
        profile="fixture", workspace=str(workspace), model="fixture", model_provider=None,
        active_stream_id="fixture-scope-run", pending_user_message=None, messages=[])
    captured = []

    def read_config(selected_home):
        captured.append((selected_home, constants.get_hermes_home()))
        raise RuntimeError("Stop before provider setup")

    monkeypatch.setattr(streaming, "STREAMS", {session.active_stream_id: queue.Queue()})
    monkeypatch.setattr(streaming, "get_session", lambda *a, **kw: session)
    monkeypatch.setattr(streaming, "RunJournalWriter", lambda *a: None)
    monkeypatch.setattr(streaming, "append_turn_journal_event_for_stream", lambda *a, **kw: None)
    monkeypatch.setattr(streaming, "_report_capacity_incident", lambda *a, **kw: None)
    monkeypatch.setattr(streaming, "bind_governed_agent_turn", lambda *a, **kw: None)
    monkeypatch.setattr(personal_context, "ensure_home", lambda *a: tmp_path / "personal")
    monkeypatch.setattr(personal_context, "shared_conversation", lambda *a: False)
    monkeypatch.setattr(personal_context, "prompt_overlay", lambda *a: "")
    monkeypatch.setattr(personal_context, "shared_project_context", lambda *a: {"content": ""})
    monkeypatch.setattr(project_collaboration, "runtime_file_scope", lambda *a: ("", None))
    monkeypatch.setattr(workspace_access, "runtime_workspace_scope", lambda *a, **kw: ("", None))
    monkeypatch.setattr(approval_resume, "make_waiter", lambda *a, **kw: None)
    monkeypatch.setattr(background_process, "drain_deferred_wakeups_for_session", lambda *a: None)
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile", lambda *a: home)
    monkeypatch.setattr(profiles, "get_profile_runtime_env", read_config)
    outer = constants.set_hermes_home_override(tmp_path / "outer")
    try:
        streaming._run_agent_streaming(session.session_id, "Synthetic scope check", "fixture",
                                       str(workspace), session.active_stream_id, ephemeral=True)
        assert captured == [(home, home)]
        assert constants.get_hermes_home() == tmp_path / "outer"
        assert session.active_stream_id not in streaming.STREAMS
    finally:
        constants.reset_hermes_home_override(outer)
