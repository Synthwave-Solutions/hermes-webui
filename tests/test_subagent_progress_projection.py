import pytest
from api.subagent_progress import normalize, remember
from api.gateway_chat import _gateway_tool_progress_event

def test_gateway_and_local_share_safe_payload():
    pytest.importorskip("tools.delegation_progress", reason="requires optional upgraded engine; exercised by engine integration QA")
    payload={"subagent_id":"child-1","goal":"Review token=abcdef repository changes",
             "task_index":0,"task_count":2,"args":{"password":"private"},
             "reasoning":"hidden"}
    local=normalize("subagent.start",payload)
    assert local and local["status"]=="running"
    assert "abcdef" not in str(local) and "private" not in str(local) and "hidden" not in str(local)
    assert _gateway_tool_progress_event({"event":"subagent",**local})==("subagent",local)
    assert normalize("subagent.thinking",payload) is None
    assert normalize("subagent.text",payload) is None

def test_ui_fallback_is_deduplicated_and_terminal():
    rows=[]
    data={"id":"c","status":"running","summary":"Check files","task_index":0,"task_count":1,"tool_count":0}
    remember(rows,data)
    remember(rows,data)
    completed={**data,"status":"completed"}
    remember(rows,completed);remember(rows,data)
    assert len(rows)==1 and rows[0]["done"] is True
    assert rows[0]["name"]=="subagent_progress" and rows[0]["tid"]=="subagent:c"
    assert "tool_call_id" not in rows[0]


def test_older_engine_without_progress_capability_is_optional(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,"tools.delegation_progress",None)
    assert normalize("subagent.start",{"id":"worker"}) is None
