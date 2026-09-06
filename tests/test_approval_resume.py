import threading
import time
import pytest
from api import approval_resume as r, config, approvals

OWNER='user@example.test'
OP={'operation_id':'op1','actor_email':OWNER,'session_id':'session','request_id':'run','tool_call_id':'call','prompt_sha256':'a'*64,'gkind':'tool','value':'read','binding_status':'bound','freshness_status':'bound'}
ENTRY={'owner_email':OWNER,'key':OWNER+'|tool|read','payload':{'operations':{'op1':OP}}}

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'STATE_DIR',tmp_path)
    monkeypatch.setattr(approvals,'get',lambda *a: None)
    r._WAITERS.clear()
    r._RUNNING.clear()

def start(fresh=lambda:True,cancel=None,max_wait=2):
    r.set_consent(OWNER,'session',True)
    stop=cancel or threading.Event()
    fn=r.make_waiter(OWNER,'session','run','a'*64,stop,fresh=fresh,max_wait=max_wait)
    result=[]
    worker=threading.Thread(target=lambda:result.append(fn(dict(OP))))
    worker.start()
    limit=time.time()+2
    while time.time()<limit:
        if r.records(OWNER):break
        threading.Event().wait(.01)
    return worker,result

def test_disabled_by_default():
    assert r.make_waiter(OWNER,'session','run','a'*64,threading.Event()) is None

def test_exact_approval_releases_same_waiter_once_and_completion():
    worker,result=start()
    r.decide(ENTRY,'approve');worker.join(2)
    assert result==[True]
    assert r.records(OWNER)[0]['status']=='resumed'
    r.decide(ENTRY,'approve')
    r.finish_call('other-run','call',{})
    assert r.records(OWNER)[0]['status']=='resumed'
    r.finish_call('run','call',{'success':True})
    assert r.records(OWNER)[0]['status']=='completed'
    fn=r.make_waiter(OWNER,'session','run','a'*64,threading.Event())
    assert fn(dict(OP)) is False

def test_mismatching_operation_cannot_resume():
    worker,result=start()
    changed=dict(OP,tool_call_id='other')
    r.decide(dict(ENTRY,payload={'operations':{'op1':changed}}),'approve')
    worker.join(2)
    assert result==[False]
    assert r.records(OWNER)[0]['status']=='input-needed'

def test_cancel_owner_and_run_cancellation():
    stop=threading.Event();worker,result=start(cancel=stop)
    with pytest.raises(KeyError):r.cancel('attacker@example.test','op1')
    stop.set();worker.join(2)
    assert result==[False]
    assert r.records(OWNER)[0]['status']=='cancelled'

def test_freshness_change_blocks_approval():
    current=[True];worker,result=start(fresh=lambda:current[0])
    current[0]=False;r.decide(ENTRY,'approve');worker.join(2)
    assert result==[False]
    assert r.records(OWNER)[0]['status']=='input-needed'

def test_expiry_and_lost_waiter_do_not_replay():
    worker,result=start(max_wait=.1);worker.join(2)
    assert result==[False]
    assert r.records(OWNER)[0]['status']=='expired'
    with r._db() as db:db.execute("UPDATE intents SET status='queued',expires=?",(time.time()+60,))
    assert r.records(OWNER)[0]['status']=='input-needed'

def test_refusal_and_revoked_consent():
    worker,result=start();r.set_consent(OWNER,'session',False);worker.join(2)
    assert result==[False]
    assert r.records(OWNER)[0]['status']=='cancelled'

def test_unbound_prompt_never_waits():
    r.set_consent(OWNER,'session',True)
    fn=r.make_waiter(OWNER,'session','run','a'*64,threading.Event())
    assert fn(dict(OP,prompt_sha256='b'*64)) is False
    assert not r.records(OWNER)


def test_restart_after_release_never_retries_unknown_execution():
    worker,result=start();r.decide(ENTRY,'approve');worker.join(2)
    assert result==[True]
    r._RUNNING.clear()
    assert r.records(OWNER)[0]['status']=='input-needed'


def test_owner_only_endpoint(monkeypatch):
    from api import governance_api
    from api import routes
    from types import SimpleNamespace
    responses=[]
    monkeypatch.setattr(governance_api,'j',lambda handler,body,**kw:responses.append((body,kw)))
    monkeypatch.setattr(governance_api,'_read_json',lambda h:{'session_id':'session','enabled':True})
    monkeypatch.setattr(routes,'get_session',lambda sid:SimpleNamespace(owner_email='someone-else@example.test'))
    governance_api._handle_approval_resume(SimpleNamespace(command='POST'),None,None,SimpleNamespace(normalized_email=OWNER),None)
    assert responses[-1][1]['status']==404
    assert not r.consent_enabled(OWNER,'session')


def test_run_teardown_releases_unknown_outcome():
    worker,result=start();r.decide(ENTRY,'approve');worker.join(2)
    r.close_run('run')
    assert r.records(OWNER)[0]['status']=='input-needed'
    assert not r._RUNNING
