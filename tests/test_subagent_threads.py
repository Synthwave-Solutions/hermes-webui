"""Conversation-scoped worker record that outlives a turn's event stream."""
import json
from pathlib import Path

import pytest

from api import subagent_progress as sp

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "_store_dir", lambda: tmp_path / "subagent_threads")
    sp._reset_for_tests()
    yield
    sp._reset_for_tests()


def _ev(status, **kw):
    return {"id": "sa-0-abc", "status": status, "summary": "Review the README", "task_index": 0,
            "task_count": 2, "tool_count": kw.pop("tool_count", 0), **kw}


def test_lifecycle_steps_and_terminal_state(tmp_path):
    assert sp.record("sess1", _ev("queued"), now=100)["status"] == "queued"
    sp.record("sess1", _ev("running", tool_count=1), tool_name="read_file", now=101)
    sp.record("sess1", _ev("running", tool_count=2), tool_name="terminal", now=102)
    done = sp.record("sess1", _ev("completed", tool_count=2, duration_seconds=7.5), now=108)
    assert done["status"] == "completed" and done["duration_seconds"] == 7.5
    assert [s["tool"] for s in done["steps"]] == ["read_file", "terminal"]
    # Late or replayed events never reopen a finished worker.
    assert sp.record("sess1", _ev("running", tool_count=9), tool_name="x", now=110) is None
    snap = sp.snapshot("sess1")
    assert len(snap) == 1 and snap[0]["tool_count"] == 2
    # Persisted for restarts; reload from disk gives the same record.
    sp._threads.clear()
    assert sp.snapshot("sess1")[0]["status"] == "completed"


def test_only_tool_names_are_kept_never_arguments():
    sp.record("sess2", _ev("running"), tool_name="terminal --password=hunter2", now=1)
    sp.record("sess2", _ev("running"), tool_name="_thinking", now=2)
    w = sp.snapshot("sess2")[0]
    assert w["steps"] == []
    assert "hunter2" not in json.dumps(w)


def test_invalid_ids_and_sessions_are_ignored():
    assert sp.record("../etc", _ev("running")) is None
    assert sp.record("sess3", {"id": "bad id!", "status": "running"}) is None
    assert sp.record("sess3", {"id": "ok", "status": "weird"}) is None
    assert sp.snapshot("../etc") == []


def test_seed_from_persisted_worklog_rows():
    rows = [
        {"created_at": 5.0, "tool": {"id": "subagent:sa-1", "name": "subagent_progress",
                                      "args": {"status": "running", "task": "Check links", "task_index": 1,
                                               "task_count": 2, "tool_count": 4}}},
        {"tool": {"id": "t1", "name": "terminal", "args": {"command": "ls"}}},
    ]
    seeded = sp.seed_from_rows(rows)
    assert len(seeded) == 1
    assert seeded[0]["id"] == "sa-1" and seeded[0]["restored"] is True and seeded[0]["tool_count"] == 4


def test_route_and_stream_hooks_are_wired():
    routes = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    assert '"/api/session/subagents"' in routes
    block = routes[routes.index('"/api/session/subagents"'):][:1500]
    assert "_session_visible_to_request" in block
    streaming = (ROOT / "api" / "streaming.py").read_text(encoding="utf-8")
    assert "record_subagent(" in streaming
    gateway = (ROOT / "api" / "gateway_chat.py").read_text(encoding="utf-8")
    assert gateway.count('record(session_id, event_payload') == 2


def test_child_session_id_is_kept_for_the_transcript_link():
    w = sp.record("sess4", _ev("running"), child_session_id="20261018_child", now=1)
    assert w["child_session_id"] == "20261018_child"
    assert sp.record("sess5", _ev("running"), child_session_id="../../etc", now=1).get("child_session_id") is None
    assert sp.record("sess6", _ev("running"), child_session_id="sess6", now=1).get("child_session_id") is None
