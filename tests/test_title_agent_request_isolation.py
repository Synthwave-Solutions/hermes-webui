"""A pending title request must not change the cached foreground agent."""
import copy
from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from api import streaming


class TitleAgent:
    """Only the provider call is gated; title orchestration runs unchanged."""
    provider = "custom"
    model = "fixture-model"
    base_url = "https://provider.invalid/v1"

    def __init__(self, api_mode="chat_completions", *, error=False):
        self.api_mode = api_mode
        self.reasoning_config = {"enabled": True, "effort": "high"}
        self.tools = [{"type": "function", "function": {"name": "foreground_tool"}}]
        self._transport_cache = {api_mode: SimpleNamespace(_last_wire_aliases={"wire": "foreground_tool"})}
        self._ephemeral_max_output_tokens = 777
        self.entered = threading.Event()
        self.release = threading.Event()
        self.requests = []
        self.error = error

    def _build_api_kwargs(self, messages, tools_for_api=None):
        # Match the canonical builder's scalar consumption and transport-local
        # alias reset, so neither can escape a request-only title view.
        self._ephemeral_max_output_tokens = None
        transport = self._transport_cache.setdefault(self.api_mode, SimpleNamespace())
        transport._last_wire_aliases = {}
        return {"messages": messages, "tools": self.tools if tools_for_api is None else tools_for_api,
                "reasoning": copy.deepcopy(self.reasoning_config)}

    def _request(self, kwargs):
        self.requests.append(kwargs)
        self.entered.set()
        self.release.wait()  # Every test releases this gate in finally.
        if self.error:
            raise RuntimeError("synthetic title failure")
        return {"choices": [{"message": {"content": "Synthetic title"}, "finish_reason": "stop"}]}

    def _ensure_primary_openai_client(self, **_kwargs):
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: self._request(kw))))

    def _run_codex_stream(self, kwargs):
        return self._request(kwargs)

    def _normalize_codex_response(self, response):
        return SimpleNamespace(content=response["choices"][0]["message"]["content"]), "stop"


@pytest.fixture(autouse=True)
def one_title_prompt(monkeypatch):
    # Eliminate title wording/budget retries from this state-lifetime test.
    monkeypatch.setattr(streaming, "_title_prompts", lambda *_: ("synthetic exchange", ["title prompt"]))


@pytest.mark.parametrize("api_mode", ["chat_completions", "codex_responses"])
def test_waiting_title_does_not_change_foreground_reasoning_or_builder_state(api_mode):
    agent = TitleAgent(api_mode)
    reasoning = agent.reasoning_config
    tools = copy.deepcopy(agent.tools)
    transport = agent._transport_cache[api_mode]
    with ThreadPoolExecutor(max_workers=1) as pool:
        title = pool.submit(streaming.generate_title_raw_via_agent, agent, "user", "assistant")
        try:
            assert agent.entered.wait(3), "title did not reach synthetic provider"
            assert agent.reasoning_config is reasoning
            assert agent.reasoning_config == {"enabled": True, "effort": "high"}
            assert agent._ephemeral_max_output_tokens == 777
            assert agent._transport_cache[api_mode] is transport
            assert transport._last_wire_aliases == {"wire": "foreground_tool"}
            assert agent.tools == tools
            assert agent.requests[0]["reasoning"] == {"enabled": False}
            assert "tools" not in agent.requests[0]
        finally:
            agent.release.set()
        assert title.result(timeout=3) == ("Synthetic title", "llm")
    assert agent.reasoning_config is reasoning
    assert agent._ephemeral_max_output_tokens == 777
    assert transport._last_wire_aliases == {"wire": "foreground_tool"}


@pytest.mark.parametrize("api_mode", ["chat_completions", "codex_responses"])
@pytest.mark.parametrize("error", [False, True])
def test_title_completion_never_overwrites_a_concurrent_foreground_setting(api_mode, error):
    agent = TitleAgent(api_mode, error=error)
    changed = {"enabled": True, "effort": "low"}
    with ThreadPoolExecutor(max_workers=1) as pool:
        title = pool.submit(streaming.generate_title_raw_via_agent, agent, "user", "assistant")
        try:
            assert agent.entered.wait(3), "title did not reach synthetic provider"
            agent.reasoning_config = changed
        finally:
            agent.release.set()
        result = title.result(timeout=3)
    assert result == ((None, "llm_error") if error else ("Synthetic title", "llm"))
    assert agent.reasoning_config is changed
    assert agent.requests[0]["reasoning"] == {"enabled": False}


def test_uncopyable_agent_uses_existing_failure_fallback_without_dispatch():
    class Uncopyable(TitleAgent):
        def __copy__(self):
            raise TypeError("synthetic noncopyable runtime")
    agent = Uncopyable()
    agent.release.set()
    original = agent.reasoning_config
    assert streaming.generate_title_raw_via_agent(agent, "user", "assistant") == (None, "llm_error")
    assert not agent.requests
    assert agent.reasoning_config is original


class NativeWireAgent(TitleAgent):
    """Real engine builder, transports and profiles; synthetic runtime metadata/API."""
    def __init__(self, provider, model, base_url, api_mode):
        super().__init__(api_mode)
        self.provider, self.model, self.base_url = provider, model, base_url
        self._base_url_lower = base_url.lower()
        self._base_url_hostname = urlparse(base_url).hostname
        self.max_tokens = 512
        self.request_overrides = {}
        self.session_id = "synthetic-title-wire"
        self._ollama_num_ctx = None
        self.openrouter_min_coding_score = None
        self.providers_allowed = self.providers_ignored = self.providers_order = []
        self.provider_sort = self.provider_data_collection = None
        self.provider_require_parameters = False
        from agent.transports import get_transport
        transport = get_transport(api_mode)
        transport._last_wire_aliases = {"wire": "foreground_tool"}
        self._transport_cache = {api_mode: transport}
        self.release.set()

    def _build_api_kwargs(self, messages, tools_for_api=None):
        from agent.chat_completion_helpers import build_api_kwargs
        return build_api_kwargs(self, messages, tools_for_api=tools_for_api)

    def _get_transport(self):
        from agent.transports import get_transport
        if self.api_mode not in self._transport_cache:
            self._transport_cache[self.api_mode] = get_transport(self.api_mode)
        return self._transport_cache[self.api_mode]

    def _is_qwen_portal(self):
        return False

    def _is_openrouter_url(self):
        return self.provider == "openrouter"

    def _supports_reasoning_extra_body(self):
        # Known fixture capability, avoiding an unrelated live model-catalog lookup.
        return self.provider in {"openrouter", "nous"}

    def _prepare_messages_for_non_vision_model(self, messages):
        return messages  # Title fixture contains text only.

    def _resolved_api_call_timeout(self):
        return 15.0

    def _max_tokens_param(self, value):
        return {"max_tokens": value}


@pytest.mark.parametrize("provider,model,base_url,api_mode,expected_reasoning", [
    ("custom", "codex/gpt-6-astra", "https://gateway.invalid/v1", "chat_completions", None),
    ("openai", "gpt-5.6", "https://api.openai.com/v1", "chat_completions", None),
    ("nous", "hermes-4-405b", "https://inference-api.nousresearch.com/v1", "chat_completions", None),
    ("openrouter", "deepseek/deepseek-r1", "https://openrouter.ai/api/v1", "chat_completions", {"enabled": False}),
    ("openrouter", "anthropic/claude-sonnet-4.6", "https://openrouter.ai/api/v1", "chat_completions", None),
    ("openai-codex", "gpt-5.6", "https://chatgpt.com/backend-api/codex", "codex_responses", None),
])
def test_title_preserves_native_provider_reasoning_wire_contract(provider, model, base_url, api_mode, expected_reasoning):
    agent = NativeWireAgent(provider, model, base_url, api_mode)
    original = agent.reasoning_config
    original_tools = copy.deepcopy(agent.tools)
    original_transport = agent._transport_cache[api_mode]
    result = streaming.generate_title_raw_via_agent(agent, "user", "assistant")
    assert result == ("Synthetic title", "llm")
    assert len(agent.requests) == 1
    kwargs = agent.requests[0]
    assert (kwargs.get("extra_body") or {}).get("reasoning") == expected_reasoning
    assert "tools" not in kwargs
    assert agent.reasoning_config is original
    assert agent._ephemeral_max_output_tokens == 777
    assert agent.tools == original_tools
    assert agent._transport_cache[api_mode] is original_transport
    assert original_transport._last_wire_aliases == {"wire": "foreground_tool"}


@pytest.mark.parametrize("error", [False, True])
def test_anthropic_explicit_request_reasoning_does_not_change_shared_agent(error):
    class AnthropicAgent(TitleAgent):
        model = "claude-sonnet-4-6"
        _is_anthropic_oauth = False

        def _anthropic_preserve_dots(self):
            return False

        def _anthropic_messages_create(self, kwargs):
            self._request(kwargs)
            # SDK-shaped provider response; no external SDK/client is required.
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Synthetic title")],
                stop_reason="end_turn")

    agent = AnthropicAgent("anthropic_messages", error=error)
    original = agent.reasoning_config
    changed = {"enabled": True, "effort": "low"}
    with ThreadPoolExecutor(max_workers=1) as pool:
        title = pool.submit(streaming.generate_title_raw_via_agent, agent, "user", "assistant")
        try:
            assert agent.entered.wait(3)
            assert agent.reasoning_config is original
            assert agent.requests[0].get("thinking", {}).get("type") != "enabled"
            assert "tools" not in agent.requests[0]
            agent.reasoning_config = changed
        finally:
            agent.release.set()
        expected = (None, "llm_error") if error else ("Synthetic title", "llm")
        assert title.result(timeout=3) == expected
    assert agent.reasoning_config is changed
    assert agent._ephemeral_max_output_tokens == 777
