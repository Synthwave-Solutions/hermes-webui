"""The WebUI visuals prompt block (plan addendum 4.1, 4.2 and 4.4, package A1).

Modelled on ``tests/test_webui_artifact_delivery_prompt.py``: this checks the
prompt assembly and where it reaches, not whether a model follows it.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import gateway_chat, realtime_voice, streaming, webui_visuals

REPO = Path(__file__).resolve().parents[1]
HEADER = "WebUI visuals:"
ON = {"webui_inline_svg": True}
LONG_DASHES = "[" + chr(0x2013) + chr(0x2014) + "]"


def _denylist():
    """PLAN 0.4 rule 7: the shared internal-name list (Appendix E.4.3)."""
    from api.modules import DISPLAY_DENYLIST
    return tuple(name.lower() for name in DISPLAY_DENYLIST)


@pytest.fixture(autouse=True)
def isolated_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv(webui_visuals.ENV_VAR, raising=False)
    monkeypatch.setattr(streaming, "get_config", lambda: {})
    from api import bot_builder, bot_knowledge, bot_metadata
    monkeypatch.setattr(bot_metadata, "knowledge_prompt", lambda *a: "")
    monkeypatch.setattr(bot_knowledge, "prompt", lambda *a: "")
    monkeypatch.setattr(bot_builder, "memory_prompt", lambda *a: "")
    realtime_voice._ATTEMPTS.clear()


def prompt(config=None, personality="Keep the selected tone."):
    return streaming._webui_ephemeral_system_prompt(personality, config_data=config)


def test_the_block_appears_exactly_once_when_the_switch_is_on():
    for _ in range(2):  # re-sent on every call
        text = prompt(ON)
        assert text.count(HEADER) == 1
        assert webui_visuals.WEBUI_VISUALS_PROMPT in text
        assert "Keep the selected tone." in text


def test_the_block_follows_artifact_delivery_and_precedes_the_interaction_guidance():
    text = prompt(ON)
    delivery = text.index("WebUI artifact delivery:")
    visuals = text.index(HEADER)
    assert delivery < visuals < text.index("SynthPulse interaction guidance:")
    # "delivered with MEDIA: as described above" refers to the delivery block.
    assert "as described above" in webui_visuals.WEBUI_VISUALS_PROMPT


@pytest.mark.parametrize("config", [None, {}, {"webui_inline_svg": False}, {"webui_inline_svg": "off"},
                                    {"webui_inline_svg": "banana"}, {"webui_inline_svg": None},
                                    "not a dict", {"webui": {"inline_svg": True}}])
def test_the_block_is_absent_by_default_and_when_off(config):
    text = prompt(config)
    assert HEADER not in text
    assert "```svg" not in text


def test_off_leaves_the_prompt_byte_identical_to_the_scaffold_stub(monkeypatch):
    before = prompt({"webui_inline_svg": False})
    monkeypatch.setattr(webui_visuals, "prompt_block", lambda config_data=None: "")
    assert prompt({"webui_inline_svg": False}) == before
    assert prompt(ON) == before
    assert webui_visuals.DEFAULT_ENABLED is False


@pytest.mark.parametrize("env,config,expected", [
    ("0", ON, False),
    ("1", {"webui_inline_svg": False}, True),
    ("1", None, True),
    (" TRUE ", {}, True),
    ("off", ON, False),
    ("maybe", ON, True),     # not a yes or no value: the config decides
    ("", {"webui_inline_svg": False}, False),
])
def test_the_environment_overrides_the_config(monkeypatch, env, config, expected):
    monkeypatch.setenv(webui_visuals.ENV_VAR, env)
    assert webui_visuals.visuals_enabled(config) is expected
    assert (HEADER in prompt(config)) is expected


@pytest.mark.parametrize("value,expected", [
    (True, True), (False, False), (1, True), (0, False), (2, False), ("yes", True), ("No", False),
    ("on", True), ("1", True), ("0", False), ("", False), ("sure", False), (None, False), ([], False),
])
def test_config_values(value, expected):
    assert webui_visuals.visuals_enabled({"webui_inline_svg": value}) is expected


def _exec_assignment(func, target_is_attribute, name, namespace):
    tree = ast.parse(inspect.getsource(func))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            hit = (isinstance(target, ast.Attribute) and target.attr == name) if target_is_attribute \
                else (isinstance(target, ast.Name) and target.id == name)
            if hit:
                exec(compile(ast.Module(body=[node], type_ignores=[]), f"<{name}>", "exec"), namespace)
                return namespace
    raise AssertionError(f"assignment to {name} not found")


def test_the_gateway_path_equals_the_browser_path():
    session = SimpleNamespace(profile="shared", workspace="/fixture", owner_email="ada@example.test")
    agent = SimpleNamespace()
    browser = _exec_assignment(streaming._run_agent_streaming, True, "ephemeral_system_prompt", {
        "agent": agent, "_webui_ephemeral_system_prompt": streaming._webui_ephemeral_system_prompt,
        "_personality_prompt": "", "_personal_overlay": "", "session_id": "fixture",
        "execution_profile": None, "s": session, "_cfg": dict(ON), "_turn_principal": "ada@example.test",
    })
    gateway = _exec_assignment(gateway_chat._run_gateway_chat_streaming, False, "_gateway_system_prompt", {
        "_webui_ephemeral_system_prompt": streaming._webui_ephemeral_system_prompt,
        "session_id": "fixture", "workspace": "/fixture", "cfg": dict(ON), "s": session,
        "sender_email": "ada@example.test",
    })
    browser_prompt = browser["agent"].ephemeral_system_prompt
    gateway_prompt = gateway["_gateway_system_prompt"]
    assert browser_prompt.count(HEADER) == 1
    assert gateway_prompt == browser_prompt


def test_voice_never_gets_the_block(monkeypatch):
    monkeypatch.setenv(webui_visuals.ENV_VAR, "1")
    assert HEADER in prompt(ON)
    instructions = realtime_voice.session_config("ada@example.test", "s1")["instructions"]
    assert HEADER not in instructions and "```svg" not in instructions


def test_only_the_webui_prompt_builder_reads_the_block():
    """Messaging gateways, voice and the API server never import the block."""
    users = sorted(p.name for p in (REPO / "api").rglob("*.py")
                   if "webui_visuals" in p.read_text(encoding="utf-8") and p.name != "webui_visuals.py")
    assert users == ["streaming.py"]
    builders = sorted(p.name for p in (REPO / "api").rglob("*.py")
                      if "_webui_ephemeral_system_prompt(" in p.read_text(encoding="utf-8"))
    assert builders == ["gateway_chat.py", "streaming.py"]


def test_an_exception_in_the_block_leaves_the_rest_of_the_prompt_intact(monkeypatch):
    expected = prompt({"webui_inline_svg": False})

    def broken(config_data=None):
        raise RuntimeError("visuals unavailable")

    monkeypatch.setattr(webui_visuals, "prompt_block", broken)
    assert prompt(ON) == expected
    assert "SynthPulse interaction guidance:" in prompt(ON)


def test_the_block_text_follows_the_copy_rules():
    text = webui_visuals.WEBUI_VISUALS_PROMPT
    assert not re.search(LONG_DASHES, text)
    assert len(text.split()) <= 230
    assert text.splitlines()[0] == HEADER
    assert len([line for line in text.splitlines() if line.startswith("- ")]) == 7
    denylist = _denylist()
    assert {"hermes", "n8n", "omniroute", "mnemosyne", "mnemo-hub"} <= set(denylist)
    for word in denylist:
        assert word not in text.lower(), word
    for phrase in ("```svg and ```mermaid", "at most one visual per reply", "W at most 720",
                   "no width or height attributes", "start with <title>", "url() other than #ids",
                   "var(--sp-fg,#1f2937)", "Never hardcode black or white text",
                   "one sentence that states the takeaway", "visual-explainer"):
        assert phrase in text, phrase
    assert "<svg" in text and "example" not in text.lower()  # no example SVG in the block


def test_the_module_text_has_no_long_dashes():
    source = Path(webui_visuals.__file__).read_text(encoding="utf-8")
    assert not re.search(LONG_DASHES, source)
