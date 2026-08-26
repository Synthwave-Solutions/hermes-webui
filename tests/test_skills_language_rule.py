"""Skills language regression (ticket skills-language, reported 2026-08-26).

Many bundled skills are Dutch-authored, and governed users (like Stephen)
can be English-speaking. The governed system prompt must therefore carry a
language rule: respond in the user's language, an explicit user preference
wins, and a skill's own writing language (Dutch or English) never overrides
the user's. The single authoritative source is render_governance_block in
~/.hermes/scripts/governance_profile_sync.py, which writes the governance
block into every governed profile's SOUL.md between markers. These tests
pin the rule at that source so a template refactor cannot silently drop it.
"""
import importlib.util
import pathlib
import sys
from types import SimpleNamespace

import pytest

SYNC_SCRIPT = pathlib.Path.home() / ".hermes" / "scripts" / "governance_profile_sync.py"


def _load_sync_module():
    if not SYNC_SCRIPT.is_file():
        pytest.skip("governance_profile_sync.py not installed on this host")
    spec = importlib.util.spec_from_file_location("governance_profile_sync_under_test", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:  # hermes_cli lives in ~/.hermes/hermes-agent
        pytest.skip(f"sync script dependencies unavailable: {exc}")
    return module


def _fake_access(skills=("client-facing-contact",)):
    grants = SimpleNamespace(
        skills_load=frozenset(skills),
        cli_commands=frozenset(),
        mcp_servers=frozenset(),
        permissions=frozenset(),
        file_write_roots=(),
        cli_workdir_roots=(),
        workdir_roots=(),
        toolsets=(),
    )
    return SimpleNamespace(grants=grants, roles=frozenset(), groups=frozenset())


@pytest.fixture(scope="module")
def rendered_block():
    module = _load_sync_module()
    return module.render_governance_block(
        "stephen@synthwave.solutions", "Steve", _fake_access()
    )


def test_block_answers_in_the_users_language(rendered_block):
    # English input gets an English response by default: the rule binds the
    # response language to the language the user writes in.
    assert "always respond in the language the user writes in" in rendered_block


def test_block_lets_explicit_preference_override_skill_default(rendered_block):
    assert "explicit language preference from the user overrides" in rendered_block


def test_block_covers_dutch_and_english_skill_documents(rendered_block):
    # Skill-based workflows: skills may be authored in Dutch or English and
    # their language must never override the user's.
    assert "Dutch" in rendered_block and "English" in rendered_block
    assert "never let the language a skill is written in override" in rendered_block


def test_block_allows_fixed_language_only_when_task_requires(rendered_block):
    assert "only when the task itself" in rendered_block


def test_language_rule_is_a_hard_rule_inside_managed_markers(rendered_block):
    module = _load_sync_module()
    hard_rules = rendered_block.split("Hard rules:", 1)[1]
    assert "Language:" in hard_rules.split("Granted to this user", 1)[0]
    assert rendered_block.startswith(module.GOV_BEGIN)
    assert rendered_block.rstrip().endswith(module.GOV_END)


def test_block_has_no_em_or_en_dashes(rendered_block):
    # House style: the governed prompt itself must respect the dash rule.
    assert "\u2014" not in rendered_block and "\u2013" not in rendered_block
