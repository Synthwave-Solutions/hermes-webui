from types import SimpleNamespace
import pytest


@pytest.mark.parametrize("sidecar_first", [True, False])
def test_authoritative_bot_stamp_survives_database_reconcile(monkeypatch, sidecar_first):
    from api.streaming import _stamp_group_bot_author
    from api.models import merge_session_messages_append_only
    monkeypatch.setattr("api.bot_metadata.read_profile", lambda p:{"bot":{"title":"Research"}})
    rows=[{"role":"user","content":"@research Test","timestamp":1000.0},
          {"role":"assistant","content":"Answer","timestamp":1001.0}]
    session=SimpleNamespace(messages=[dict(r) for r in rows])
    _stamp_group_bot_author(session, "@research Test", "research")
    assert session.messages[-1]["bot_profile"]=="research"
    left,right=(session.messages,rows) if sidecar_first else (rows,session.messages)
    merged=merge_session_messages_append_only(left,right)
    assert len(merged)==2
    assert merged[-1]["bot_profile"]=="research"
    assert merged[-1]["bot_name"]=="Research"


def test_bot_author_boundary_normalizes_whitespace_without_guessing(monkeypatch):
    from api.streaming import _stamp_group_bot_author
    monkeypatch.setattr("api.bot_metadata.read_profile", lambda p:{"bot":{"title":"Research"}})
    prompt="@research @bob@example.test    QA_MENTIONS_GROUP"
    session=SimpleNamespace(messages=[
        {"role":"user","content":"unrelated"},
        {"role":"assistant","content":"Old answer"},
        {"role":"user","content":prompt},
        {"role":"assistant","content":"New answer"}])
    _stamp_group_bot_author(session,prompt,"research")
    assert "bot_profile" not in session.messages[1]
    assert session.messages[-1]["bot_profile"]=="research"
    other=SimpleNamespace(messages=[{"role":"user","content":"not matching"},
                                   {"role":"assistant","content":"Do not attribute"}])
    _stamp_group_bot_author(other,prompt,"research")
    assert "bot_profile" not in other.messages[-1]
