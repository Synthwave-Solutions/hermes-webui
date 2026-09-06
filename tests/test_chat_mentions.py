import threading
import uuid
from types import SimpleNamespace

import pytest


@pytest.fixture
def fixture(monkeypatch, tmp_path):
    from api import chat_mentions as mentions, routes, group_chat, config
    mentions._RECENT.clear()
    monkeypatch.setattr("api.governance.enforce.evaluate_request", lambda *a:SimpleNamespace(allow=True))
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h:{"email":h.email})
    actor = "alice@example.test"
    sessions = {}
    def make(**kw):
        sid = str(uuid.uuid4())
        s = SimpleNamespace(session_id=sid, owner_email=actor, participants=[], bot_participants=[],
            messages=[], context_messages=[], pending_attachments=None, project_id=None,
            active_stream_id=None, profile="default", **{k:v for k,v in kw.items() if k != "profile"})
        s.save = lambda: sessions.update({sid:s})
        s.compact = lambda: {"session_id":sid, "participants":s.participants, "bot_participants":s.bot_participants}
        return s
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr("api.ownership.request_owner_email", lambda h:h.email)
    monkeypatch.setattr("api.profiles.get_active_profile_name", lambda:"default")
    monkeypatch.setattr(group_chat, "known_emails", lambda: {actor,"bob@example.test","eve@example.test"})
    def bots(values, actor):
        if not isinstance(values,list) or any(b not in ["default","research"] for b in values):
            raise ValueError("Unavailable bot")
        return values
    monkeypatch.setattr(group_chat, "validate_bots", bots)
    monkeypatch.setattr(routes, "get_session", lambda sid:sessions[sid])
    monkeypatch.setattr(routes, "new_session", make)
    monkeypatch.setattr(routes, "_get_session_agent_lock", lambda sid:threading.RLock())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda s,h:True)
    monkeypatch.setattr(routes, "_session_is_subagent_view_only", lambda sid:False)
    monkeypatch.setattr(routes, "_group_participants_may_be_managed_by", lambda s,h:s.owner_email==h.email)
    monkeypatch.setattr(routes, "_audit_group_participants", lambda *a:None)
    monkeypatch.setattr(routes, "_on_session_list_changed", lambda *a:None)
    monkeypatch.setattr(routes, "publish_session_list_changed", lambda *a,**k:None)
    monkeypatch.setattr("api.project_collaboration.project_for", lambda p:None)
    monkeypatch.setattr("api.project_collaboration.session_access", lambda s,a:None)
    old=make(workspace="/private/source"); old.messages=[{"role":"user","content":"PRIVATE"}]
    old.model="codex/gpt-6-astra"; old.model_provider="custom:omniroute"; old.chat_mode="normal"
    old.context_messages=[{"content":"PRIVATE_CONTEXT"}]; old.pending_attachments=["PRIVATE_FILE"];old.save()
    return mentions,SimpleNamespace(email=actor),old,sessions


def body(old, **kw):
    return {"request_id":str(uuid.uuid4()),"session_id":old.session_id,
            "participants":["bob@example.test"],"bot_participants":["research"],**kw}


def test_private_mentions_create_empty_group_and_retry_same_group(fixture):
    m,h,old,sessions=fixture
    b=body(old)
    result=m.prepare(h,b); new=sessions[result["session"]["session_id"]]
    assert result["created"] and new.session_id != old.session_id
    assert new.messages==[] and new.context_messages==[] and new.pending_attachments is None
    assert new.workspace != old.workspace and new.project_id is None
    assert (new.model,new.model_provider,new.chat_mode)==(old.model,old.model_provider,"normal")
    assert old.messages[0]["content"]=="PRIVATE" and old.participants==[]
    assert m.prepare(h,b)["session"]["session_id"]==new.session_id
    assert len(sessions)==2
    with pytest.raises(RuntimeError):
        m.prepare(h,{**b,"participants":["eve@example.test"]})


def test_member_cannot_invite_or_access_outsider(fixture):
    m,h,old,sessions=fixture
    old.participants=["bob@example.test"];old.bot_participants=["research"]
    bob=SimpleNamespace(email="bob@example.test")
    with pytest.raises(PermissionError):
        m.prepare(bob,body(old,participants=["eve@example.test"]))
    with pytest.raises(PermissionError):
        m.prepare(SimpleNamespace(email="eve@example.test"),body(old))
    assert old.participants==["bob@example.test"]


def test_busy_unknown_recipient_and_bot_fail_before_creation(fixture):
    m,h,old,sessions=fixture
    with pytest.raises(ValueError):m.prepare(h,body(old,participants=["unknown@example.test"]))
    with pytest.raises(ValueError):m.prepare(h,body(old,bot_participants=["forbidden"]))
    with pytest.raises(ValueError):m.prepare(h,body(old,participants=[],bot_participants=[]))
    old.active_stream_id="busy"
    with pytest.raises(RuntimeError):m.prepare(h,body(old))
    assert len(sessions)==1


def test_existing_group_owner_adds_without_replacing_members(fixture):
    m,h,old,sessions=fixture
    old.participants=["bob@example.test"];old.bot_participants=["default"]
    result=m.prepare(h,body(old,participants=["eve@example.test"]))
    assert not result["created"]
    assert old.participants==["bob@example.test","eve@example.test"]
    assert old.bot_participants==["default","research"]


def test_route_authorization_requires_nonadmin_chat_permission(monkeypatch):
    from api.governance.enforce import evaluate_request
    from api.governance.loader import parse_governance_policy
    policy = parse_governance_policy({"version":1,"mode":"enforce",
        "users":{"alice@example.test":{"grants":{"routes":["*"],"permissions":["chat:use","sessions:write"]}},
                 "bob@example.test":{"grants":{"routes":["*"],"permissions":["sessions:write"]}},
                 "charlie@example.test":{"grants":{"routes":["*"],"permissions":["chat:use"]}}}})
    monkeypatch.setattr("api.governance.loader.get_policy", lambda:policy)
    assert evaluate_request({"email":"alice@example.test"}, "POST", "/api/chat/mentions/prepare").allow
    assert not evaluate_request({"email":"bob@example.test"}, "POST", "/api/chat/mentions/prepare").allow
    assert evaluate_request({"email":"charlie@example.test"}, "POST", "/api/chat/mentions/prepare").allow
    assert not evaluate_request({"email":"charlie@example.test"}, "POST", "/api/session/new").allow

def test_read_only_source_cannot_mutate_or_fork(fixture):
    m,h,old,sessions=fixture
    old.read_only=True
    with pytest.raises(PermissionError):m.prepare(h,body(old))
    assert len(sessions)==1 and old.participants==[]
