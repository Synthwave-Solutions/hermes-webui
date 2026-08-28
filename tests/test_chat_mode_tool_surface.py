"""The tool surface really shrinks in normal mode, and never grows.

Companion to tests/test_chat_mode_toggle.py: that file proves the resolver is a
subset filter on paper, this one runs the real hermes-agent assembly
(``model_tools.get_tool_definitions``, the same call agent/agent_init.py makes)
and measures the drop end to end.
"""
from __future__ import annotations

import json
import sys

import pytest

# Importing api.config performs the supported Hermes Agent source discovery.
# Ensure that checkout is importable before probing for agent-only modules.
from api.config import (  # noqa: E402
    NORMAL_CHAT_TOOLSETS,
    _AGENT_DIR,
    _resolve_cli_toolsets,
    chat_mode_toolsets,
    get_config,
)

if _AGENT_DIR is not None and str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

pytest.importorskip("hermes_constants", reason="hermes-agent not installed")

SKILLS_TOOLS = {"skills_list", "skill_view", "skill_manage"}
# The tool_search progressive-disclosure bridge agent-side assembly adds once the
# deferrable surface grows past its threshold.
TOOL_SEARCH_BRIDGE = {"tool_search", "tool_describe", "tool_call"}


def _tool_names(defs) -> set[str]:
    names = set()
    for definition in defs:
        name = definition.get("name") or definition.get("function", {}).get("name")
        if name:
            names.add(name)
    return names


@pytest.fixture(scope="module")
def surfaces():
    # Some larger test combinations reload config under an isolated HERMES_HOME
    # and remove its previously discovered source path. Re-resolve at execution
    # time so this integration test remains independent of collection order.
    from api.config import _discover_agent_dir

    agent_dir = _discover_agent_dir()
    if agent_dir is None:
        pytest.skip("hermes-agent not installed")
    if str(agent_dir) not in sys.path:
        sys.path.append(str(agent_dir))
    import model_tools

    toolsets = _resolve_cli_toolsets(get_config())
    super_defs = model_tools.get_tool_definitions(
        enabled_toolsets=chat_mode_toolsets(toolsets, "super"), quiet_mode=True
    )
    normal_defs = model_tools.get_tool_definitions(
        enabled_toolsets=chat_mode_toolsets(toolsets, "normal"), quiet_mode=True
    )
    return toolsets, super_defs, normal_defs


def test_every_normal_mode_toolset_exists_in_the_live_resolution(surfaces):
    """NORMAL_CHAT_TOOLSETS is a hardcoded allowlist of agent toolset names.

    An upstream rename would narrow normal mode silently, so pin the five names
    against what the resolver actually returns.
    """
    toolsets, _, _ = surfaces
    assert NORMAL_CHAT_TOOLSETS <= set(toolsets)


def test_normal_mode_loads_fewer_tools(surfaces):
    _, super_defs, normal_defs = surfaces
    assert len(normal_defs) < len(super_defs)


def test_normal_mode_tools_are_a_strict_subset(surfaces):
    """Narrowing, not substitution: the mode may only take tools away."""
    _, super_defs, normal_defs = surfaces
    assert _tool_names(normal_defs) < _tool_names(super_defs)


def test_the_schema_payload_at_least_halves(surfaces):
    """A ratio floor, not an absolute count, so the assertion survives profile
    drift while still failing loudly if the set quietly re-widens."""
    _, super_defs, normal_defs = surfaces
    super_bytes = len(json.dumps(super_defs))
    normal_bytes = len(json.dumps(normal_defs))
    assert normal_bytes * 2 < super_bytes


def test_no_mcp_server_tool_survives_normal_mode(surfaces):
    """MCP servers ride the toolset list under their bare server names."""
    from hermes_cli.tools_config import enabled_mcp_server_names

    toolsets, _, _ = surfaces
    servers = enabled_mcp_server_names(get_config())
    narrowed = set(chat_mode_toolsets(toolsets, "normal"))
    assert narrowed & set(servers) == set()

    import model_tools

    registry = model_tools.registry
    _, _, normal_defs = surfaces
    for tool_name in _tool_names(normal_defs):
        toolset = registry.get_toolset_for_tool(tool_name)
        assert toolset not in servers, f"{tool_name} came from MCP server {toolset}"


def test_the_skills_index_disappears_in_normal_mode(surfaces):
    """agent/system_prompt.py gates the whole skills index on these tool names.

    Dropping the skills toolset therefore removes the index from the prompt for
    free, which is the single biggest saving of the mode.
    """
    _, super_defs, normal_defs = surfaces
    assert SKILLS_TOOLS & _tool_names(super_defs)
    assert SKILLS_TOOLS & _tool_names(normal_defs) == set()

    from agent.prompt_builder import build_skills_system_prompt
    import model_tools

    registry = model_tools.registry

    def _emitted_index(defs):
        """Reproduce the has_skills_tools gate from agent/system_prompt.py."""
        names = _tool_names(defs)
        if not any(name in names for name in SKILLS_TOOLS):
            return ""
        toolsets = {registry.get_toolset_for_tool(name) for name in names}
        return build_skills_system_prompt(
            available_tools=names,
            available_toolsets={t for t in toolsets if t},
        )

    assert _emitted_index(normal_defs) == ""
    # Sanity floor on what normal mode is dropping: the index this profile emits
    # in super mode is tens of thousands of characters of prompt.
    assert len(_emitted_index(super_defs)) > 50_000


def test_the_tool_search_bridge_is_absent_in_normal_mode(surfaces):
    """Normal mode stays under the deferrable-surface threshold, so an ordinary
    chat turn does not pay a discovery round-trip."""
    _, _, normal_defs = surfaces
    assert TOOL_SEARCH_BRIDGE & _tool_names(normal_defs) == set()


def test_the_mode_composes_with_governance_instead_of_racing_it(surfaces):
    """Under an enforce-mode context the mode can still only ever subtract.

    _filter_tools_by_governance runs downstream of toolset resolution on every
    tool, so switching back to super must never return a tool the context
    denies.
    """
    import model_tools
    from hermes_cli.dashboard_governance.context import (
        DashboardGovernanceContext,
        governance_context,
    )
    from hermes_cli.dashboard_governance.models import (
        EffectiveAccess,
        GovernanceSubject,
        GrantSet,
    )

    toolsets, _, _ = surfaces
    subject = GovernanceSubject(email="governed@example.test")
    access = EffectiveAccess(
        subject=subject,
        mode="enforce",
        grants=GrantSet(toolsets=frozenset({"file", "todo"})),
    )
    ctx = DashboardGovernanceContext(subject=subject, access=access)

    with governance_context(ctx):
        model_tools._clear_tool_defs_cache()
        governed_super = _tool_names(
            model_tools.get_tool_definitions(
                enabled_toolsets=chat_mode_toolsets(toolsets, "super"), quiet_mode=True
            )
        )
        governed_normal = _tool_names(
            model_tools.get_tool_definitions(
                enabled_toolsets=chat_mode_toolsets(toolsets, "normal"), quiet_mode=True
            )
        )
    model_tools._clear_tool_defs_cache()

    # Not vacuous: the granted toolsets still produce a working surface.
    assert governed_super
    assert governed_normal <= governed_super
    # Denied under this context, and denied in BOTH modes: the wide mode cannot
    # hand back what governance withheld from the narrow one.
    ungranted = {"terminal", "execute_code", "browser_exec", "delegate_task", "memory"}
    assert governed_super & ungranted == set()
    assert governed_normal & ungranted == set()
