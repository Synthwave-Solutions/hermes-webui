"""Keep an explicitly selected custom gateway when its model ID contains a slash."""
import copy

import pytest

from api import config


@pytest.fixture
def gateway_config(monkeypatch):
    settings = {
        "model": {
            "provider": "openai-codex",
            "default": "gpt-6-astra",
            "base_url": "https://chatgpt.com/backend-api/codex",
        },
        "providers": {},
        "custom_providers": [
            {"name": "Other Gateway", "base_url": "http://127.0.0.1:9911/v1"},
            {
                "name": "OmniRoute",
                "base_url": "http://127.0.0.1:9922/v1",
                # The live regression uses a list catalog, not a models mapping.
                "models": [{"id": "codex/gpt-6-astra"}, {"id": "codex/gpt-5.6-luna"}],
            },
        ],
    }
    monkeypatch.setattr(config, "cfg", settings)
    monkeypatch.setattr(config, "get_config", lambda: settings)
    return settings


@pytest.mark.parametrize("model", ["codex/gpt-6-astra", "codex/gpt-5.6-luna", "vendor/model:free"])
def test_selected_named_custom_slash_model_reaches_its_gateway(gateway_config, model):
    before = copy.deepcopy(gateway_config)
    wrapped = config.model_with_provider_context(model, "custom:omniroute")
    resolved_model, provider, base_url = config.resolve_model_provider(wrapped)
    assert wrapped == f"@custom:omniroute:{model}"
    assert (resolved_model, provider) == (model, "custom:omniroute")
    assert base_url is None  # The existing named-provider runtime resolves the endpoint next.
    _, gateway_url = config.resolve_custom_provider_connection(provider)
    assert gateway_url == "http://127.0.0.1:9922/v1"
    assert gateway_config == before


def test_normalized_custom_name_and_second_gateway_stay_separate(gateway_config):
    wrapped = config.model_with_provider_context("vendor/model", " CUSTOM:OTHER-GATEWAY ")
    assert wrapped == "@custom:other-gateway:vendor/model"
    model, provider, _ = config.resolve_model_provider(wrapped)
    assert (model, provider) == ("vendor/model", "custom:other-gateway")
    assert config.resolve_custom_provider_connection(provider)[1] == "http://127.0.0.1:9911/v1"


def test_native_selection_and_existing_qualified_selection_are_preserved(gateway_config):
    assert config.model_with_provider_context("gpt-6-astra", "openai-codex") == "gpt-6-astra"
    assert config.resolve_model_provider("gpt-6-astra")[1] == "openai-codex"
    selected = "@custom:omniroute:codex/gpt-6-astra"
    assert config.model_with_provider_context(selected, "openai-codex") == selected


def test_portal_and_unconfigured_custom_slash_semantics_are_preserved(gateway_config):
    assert config.model_with_provider_context("anthropic/claude-test", "nous") == "anthropic/claude-test"
    assert config.model_with_provider_context("vendor/model", "custom:missing") == "vendor/model"
    assert config.model_with_provider_context("vendor/model", "default") == "vendor/model"


def test_active_custom_gateway_keeps_existing_bare_model_semantics(gateway_config):
    gateway_config["model"] = {
        "provider": "custom:omniroute", "default": "vendor/default",
        "base_url": "http://127.0.0.1:9922/v1",
    }
    model = "codex/gpt-6-astra"
    assert config.model_with_provider_context(model, "custom:omniroute") == model
    assert config.resolve_model_provider(model) == (model, "custom:omniroute", "http://127.0.0.1:9922/v1")


@pytest.mark.parametrize("entries", [None, {}, [None, {}, {"name": ""}]])
def test_malformed_custom_catalog_does_not_create_provider_authority(gateway_config, entries):
    gateway_config["custom_providers"] = entries
    assert config.model_with_provider_context("vendor/model", "custom:omniroute") == "vendor/model"
