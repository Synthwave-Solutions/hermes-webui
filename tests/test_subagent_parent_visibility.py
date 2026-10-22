import sqlite3
from types import SimpleNamespace
from api import routes, models


def test_child_access_uses_persisted_parent_and_current_permissions(tmp_path, monkeypatch):
    db=tmp_path/'state.db'
    with sqlite3.connect(db) as c:
        c.execute('create table sessions(id text,source text,parent_session_id text)')
        c.executemany('insert into sessions values(?,?,?)',[('child','subagent','parent'),('other','cli','parent'),('orphan','subagent','missing')])
    monkeypatch.setattr(models,'_active_state_db_path',lambda:db)
    parent=SimpleNamespace(session_id='parent')
    def get(sid):
        if sid=='parent':return parent
        raise KeyError(sid)
    monkeypatch.setattr(routes,'get_session',get)
    allowed=object()
    monkeypatch.setattr(routes,'_session_visible_to_request',lambda s,h:s is parent and h is allowed)
    assert routes._subagent_parent_visible_to_request('child',allowed)
    assert not routes._subagent_parent_visible_to_request('child',object())
    assert not routes._subagent_parent_visible_to_request('other',allowed)
    assert not routes._subagent_parent_visible_to_request('orphan',allowed)
    assert not routes._subagent_parent_visible_to_request('../bad',allowed)
