"""Execute the WebUI stream worker through its native route/cache boundary.

Provider I/O and the engine constructor are captured; WebUI custom-provider
normalization, constructor introspection and cache selection execute unchanged.
"""
from collections import OrderedDict
import queue
import sys
import types

import pytest


MODEL = "codex/gpt-6-astra"
URL = "http://127.0.0.1:20128/v1"


@pytest.fixture
def stream_fixture(monkeypatch, tmp_path):
    from api import config, oauth, profiles, streaming, personal_context
    from api import project_collaboration, workspace_access
    from agent import model_metadata

    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text("{}\n")
    personal = tmp_path / "personal"
    personal.mkdir()
    cfg = {
        "agent": {"reasoning_effort": "high"},
        "custom_providers": [
            {"name": name, "base_url": URL, "api_key": "fixture-only"}
            for name in ("omniroute", "local")
        ],
    }
    state = types.SimpleNamespace(
        route="custom:omniroute", constructed=[], runs=[], legacy=False,
        activate_fallback=False,
    )

    class Session:
        def __init__(self):
            self.session_id = "fixture-requested-provider"
            self.title = "Synthetic provider identity test"
            self.workspace = str(tmp_path)
            self.model = MODEL
            self.model_provider = None
            self.profile = None
            self.personality = None
            self.messages = []
            self.context_messages = []
            self.tool_calls = []
            self.input_tokens = self.output_tokens = 0
            self.context_length = self.threshold_tokens = self.last_prompt_tokens = 0
            self.estimated_cost = None
            self.active_stream_id = self.pending_user_message = self.pending_started_at = None
            self.pending_attachments = []
            self.llm_title_generated = True

        def save(self, *args, **kwargs):
            pass

        def compact(self):
            return {
                "session_id": self.session_id, "title": self.title,
                "workspace": self.workspace, "model": self.model,
                "created_at": 0, "updated_at": 0, "pinned": False,
                "archived": False, "project_id": None, "profile": None,
                "input_tokens": 0, "output_tokens": 0,
                "estimated_cost": None, "personality": None,
            }

    session = Session()

    class Agent:
        def __init__(self, requested_provider=None, reasoning_config=None, **kwargs):
            self.requested_provider = requested_provider
            self.reasoning_config = reasoning_config
            self.model = kwargs.get("model")
            self.provider = kwargs.get("provider")
            self.base_url = kwargs.get("base_url")
            self.api_key = kwargs.get("api_key")
            self.session_id = kwargs.get("session_id")
            self.context_compressor = None
            self.session_prompt_tokens = self.session_completion_tokens = 0
            self.session_estimated_cost_usd = self.ephemeral_system_prompt = None
            self._last_error = None
            self._fallback_activated = False
            state.constructed.append(self)

        def run_conversation(self, **kwargs):
            state.runs.append(self)
            if state.activate_fallback:
                self.provider = "ollama"
                self.requested_provider = "ollama"
                self._fallback_activated = True
                state.activate_fallback = False
            return {"messages": list(kwargs.get("conversation_history") or []) + [
                {"role": "user", "content": kwargs.get("persist_user_message", "")},
                {"role": "assistant", "content": "Synthetic result"},
            ]}

        def interrupt(self, *_args):
            pass

        def clear_interrupt(self):
            return True

        def commit_memory_session(self):
            pass

        def shutdown_memory_provider(self, *_args):
            pass

    class LegacyAgent(Agent):
        def __init__(self, **kwargs):
            assert "requested_provider" not in kwargs
            super().__init__(**kwargs)

    runtime_module = types.ModuleType("hermes_cli.runtime_provider")
    runtime_module.resolve_runtime_provider = lambda **kwargs: {
        "provider": "custom", "requested_provider": kwargs.get("requested"),
        "base_url": URL, "api_key": "fixture-only",
    }
    monkeypatch.setitem(sys.modules, "hermes_cli.runtime_provider", runtime_module)
    memory_module = types.ModuleType("tools.memory_tool")
    memory_module.bind_personal_memory_dir = lambda *args, **kwargs: None
    memory_module.reset_personal_memory_dir = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "tools.memory_tool", memory_module)
    monkeypatch.setattr(oauth, "resolve_runtime_provider_with_anthropic_env_lock", lambda resolver, **kwargs: resolver(**kwargs))
    monkeypatch.setattr(streaming, "get_session", lambda _sid: session)
    monkeypatch.setattr(streaming, "_get_ai_agent", lambda: LegacyAgent if state.legacy else Agent)
    monkeypatch.setattr(streaming, "resolve_model_provider", lambda *args, **kwargs: (MODEL, state.route, URL))
    monkeypatch.setattr(streaming, "_build_session_db_for_stream", lambda *args: None)
    monkeypatch.setattr(model_metadata, "get_model_context_length", lambda *args, **kwargs: 256000)
    monkeypatch.setattr(streaming, "_maybe_schedule_title_refresh", lambda *args, **kwargs: None)
    monkeypatch.setattr(streaming, "bind_governed_agent_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile", lambda _profile: home)
    monkeypatch.setattr(profiles, "get_profile_runtime_env", lambda _home: {})
    monkeypatch.setattr(config, "get_config", lambda: cfg)
    monkeypatch.setattr(config, "get_config_for_profile_home", lambda _home: cfg)
    monkeypatch.setattr(config, "_resolve_cli_toolsets", lambda _cfg: [])
    monkeypatch.setattr(config, "load_settings", lambda: {})
    monkeypatch.setattr(config, "SESSION_AGENT_CACHE", OrderedDict())
    monkeypatch.setattr(personal_context, "ensure_home", lambda *_args: personal)
    monkeypatch.setattr(personal_context, "shared_conversation", lambda *_args: False)
    monkeypatch.setattr(personal_context, "prompt_overlay", lambda *_args: "")
    monkeypatch.setattr(personal_context, "shared_project_context", lambda *_args: {"content": ""})
    monkeypatch.setattr(project_collaboration, "runtime_file_scope", lambda *_args: (None, None))
    monkeypatch.setattr(workspace_access, "runtime_workspace_scope", lambda *args, **kwargs: (None, None))

    ids = []

    def turn(route="custom:omniroute", *, ephemeral=False):
        state.route = route
        sid = "fixture-identity-stream-" + str(len(ids))
        ids.append(sid)
        session.model_provider = route
        session.active_stream_id = sid
        channel = queue.Queue()
        streaming.STREAMS[sid] = channel
        streaming._run_agent_streaming(
            session_id=session.session_id, msg_text="Synthetic QA",
            model=MODEL, model_provider=route, workspace=str(tmp_path),
            stream_id=sid, ephemeral=ephemeral,
        )
        events = list(channel.queue)
        assert not [item for item in events if item[0] == "apperror"], events
        assert any(item[0] == "done" for item in events), events
        return state.runs[-1]

    state.turn = turn
    yield state
    from api.session_lifecycle import unregister_agent
    unregister_agent(session.session_id)
    with config.SESSION_AGENT_CACHE_LOCK:
        config.SESSION_AGENT_CACHE.clear()
    for stream_id in ids:
        for mapping in (streaming.STREAMS, streaming.CANCEL_FLAGS, streaming.AGENT_INSTANCES,
                        streaming.STREAM_PARTIAL_TEXT, streaming.STREAM_REASONING_TEXT,
                        streaming.STREAM_LIVE_TOOL_CALLS):
            mapping.pop(stream_id, None)


@pytest.mark.parametrize("ephemeral", [False, True])
def test_named_identity_reaches_constructor_without_changing_runtime(stream_fixture, ephemeral):
    agent = stream_fixture.turn(ephemeral=ephemeral)
    assert agent.requested_provider == "custom:omniroute"
    assert (agent.provider, agent.model, agent.base_url, agent.api_key) == ("custom", MODEL, URL, "fixture-only")
    assert agent.reasoning_config["effort"] == "high"


def test_same_named_route_reuses_agent(stream_fixture):
    first = stream_fixture.turn()
    second = stream_fixture.turn()
    assert first is second
    assert len(stream_fixture.constructed) == 1
    assert second.requested_provider == "custom:omniroute"


def test_same_endpoint_different_named_route_rebuilds_agent(stream_fixture):
    first = stream_fixture.turn()
    second = stream_fixture.turn("custom:local")
    assert first is not second
    assert len(stream_fixture.constructed) == 2
    assert second.requested_provider == "custom:local"
    assert (first.model, first.base_url, first.api_key) == (second.model, second.base_url, second.api_key)


def test_active_fallback_is_rebuilt_without_relabeling_its_runtime(stream_fixture):
    stream_fixture.activate_fallback = True
    first = stream_fixture.turn()
    assert (first.provider, first.requested_provider) == ("ollama", "ollama")
    second = stream_fixture.turn()
    assert first is not second
    assert (first.provider, first.requested_provider) == ("ollama", "ollama")
    assert (second.provider, second.requested_provider) == ("custom", "custom:omniroute")


def test_older_agent_without_explicit_parameter_remains_supported(stream_fixture):
    stream_fixture.legacy = True
    stream_fixture.turn()
    assert len(stream_fixture.constructed) == 1
