"""Governance usage tests: caps, hashed subject keys, atomic state file.

Mirrors the reference dashboard_governance usage tests with the context
object replaced by the duck-typed shape the webui port accepts.
Isolated via HERMES_HOME=tmp_path.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance.models import EffectiveAccess, GovernanceSubject, GrantSet  # noqa: E402
from api.governance.usage import check_usage_caps, read_usage_state, record_tool_usage  # noqa: E402


def _access(caps: dict, mode: str = "enforce") -> EffectiveAccess:
    return EffectiveAccess(
        subject=GovernanceSubject(email="operator@example.test"),
        mode=mode,
        grants=GrantSet(usage_caps=caps),
    )


def _ctx(caps: dict) -> SimpleNamespace:
    access = _access(caps)
    return SimpleNamespace(subject=access.subject, access=access)


def test_monthly_tool_call_cap_blocks_after_recorded_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    ctx = _ctx({"monthly_tool_calls": 1})

    assert check_usage_caps(ctx, "web_search").allowed is True
    record_tool_usage(ctx, "web_search")

    decision = check_usage_caps(ctx, "web_search")
    assert decision.allowed is False
    assert decision.reason == "monthly_tool_calls_exceeded"


def test_mcp_call_cap_counts_mcp_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    ctx = _ctx({"daily_mcp_calls": 1})

    assert check_usage_caps(ctx, "mcp_github_list_issues").allowed is True
    record_tool_usage(ctx, "mcp_github_list_issues")

    decision = check_usage_caps(ctx, "mcp_github_get_issue")
    assert decision.allowed is False
    assert decision.reason == "daily_mcp_calls_exceeded"


def test_bare_effective_access_is_accepted_as_context(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    access = _access({"daily_tool_calls": 1})

    assert check_usage_caps(access, "web_search").allowed is True
    record_tool_usage(access, "web_search")

    decision = check_usage_caps(access, "web_search")
    assert decision.allowed is False
    assert decision.reason == "daily_tool_calls_exceeded"


def test_inactive_modes_skip_caps(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    assert check_usage_caps(None, "web_search").reason == "governance_inactive"
    report_only = SimpleNamespace(access=_access({"daily_tool_calls": 0}, mode="report_only"))
    assert check_usage_caps(report_only, "web_search").reason == "governance_inactive"
    no_caps = _ctx({})
    assert check_usage_caps(no_caps, "web_search").reason == "usage_caps_inactive"
    record_tool_usage(no_caps, "web_search")
    assert read_usage_state() == {}


def test_usage_state_uses_hashed_subject_and_atomic_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    ctx = _ctx({"daily_tool_calls": 10})

    record_tool_usage(ctx, "web_search")
    state = read_usage_state()

    assert "operator@example.test" not in str(state)
    day_bucket = next(iter(state["days"].values()))
    subject_key = next(iter(day_bucket))
    assert len(subject_key) == 24
    counters = day_bucket[subject_key]
    assert counters["tool_calls"] == 1
    # atomic write leaves no temp residue
    assert [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []
