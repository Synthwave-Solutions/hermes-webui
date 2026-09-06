import base64
import io
import json
from types import SimpleNamespace
from urllib.parse import urlparse
import pytest

OWNER='michael@example.test'
MEMBER='member@example.test'
OUTSIDER='outsider@example.test'
ADMIN='admin@example.test'
RESTRICTED='restricted@example.test'

@pytest.fixture
def client(tmp_path,monkeypatch):
    from api import routes,auth,models,profiles
    from api.governance import loader
    policy=loader.parse_governance_policy({'version':1,'mode':'enforce','bootstrap_admins':[ADMIN],'roles':{'member':{'grants':{
        'permissions':['sessions:read','sessions:write','files:read','files:write','chat:use'],
        'routes':['/api/*'],'profiles':['writer'],'tools':{'builtins':['read_file','write_file']},'files':{'read_roots':[str(tmp_path/'personal')],'write_roots':[str(tmp_path/'personal')],'denied_globs':['**/.env']}}},'restricted':{'grants':{'permissions':['sessions:read','sessions:write'],'routes':['/api/*'],'profiles':[]}}},'users':{**{x:{'roles':['member']} for x in [OWNER,MEMBER,OUTSIDER]},RESTRICTED:{'roles':['restricted']}}})
    loader.set_policy_loader(lambda:policy)
    monkeypatch.setattr(loader,'load_governance_policy',lambda *a,**kw:policy)
    monkeypatch.setattr(auth,'is_auth_enabled',lambda:True)
    monkeypatch.setattr(auth,'parse_cookie',lambda h:h.headers.get('Cookie'))
    monkeypatch.setattr(auth,'get_session_identity',lambda cookie:{'email':cookie,'groups':[]})
    monkeypatch.setattr(routes,'_check_csrf',lambda h:True)
    monkeypatch.setattr(models,'PROJECTS_FILE',tmp_path/'projects.json')
    monkeypatch.setattr(models,'SESSION_DIR',tmp_path)
    monkeypatch.setattr(models,'SESSION_INDEX_FILE',tmp_path/'index.json')
    bot=tmp_path/'writer';bot.mkdir();(bot/'config.yaml').write_text('model:\n  provider: custom:test\n  default: test\n')
    monkeypatch.setattr(profiles,'get_hermes_home_for_profile',lambda name:bot)
    responses=[]
    monkeypatch.setattr(routes,'j',lambda h,payload,**kw:responses.append((kw.get('status',200),payload)) or True)
    monkeypatch.setattr(routes,'bad',lambda h,error,status=400:responses.append((status,{'error':error})) or True)
    def request(actor,path,body=None):
        raw=json.dumps(body or {}).encode();responses.clear()
        handler=SimpleNamespace(headers={'Content-Length':str(len(raw)),'Cookie':actor},rfile=io.BytesIO(raw),command='GET' if body is None else 'POST')
        if body is None:routes.handle_get(handler,urlparse(path))
        else:routes.handle_post(handler,urlparse(path))
        assert responses,'dispatcher produced no response'
        return responses[-1]
    request.tmp=tmp_path
    yield request
    loader.set_policy_loader(None)


def create(client):
    status,result=client(OWNER,'/api/projects/team',{'name':'Shared project','members':[MEMBER],'bot_participants':['writer']})
    assert status==200,result
    return result['project']


def test_full_dispatch_project_files_roster_chat_and_revocation(client):
    from api import routes,models
    from api.project_collaboration import session_access
    p=create(client);pid=p['project_id']
    assert client(MEMBER,'/api/projects/files?project_id='+pid)==(200,{'files':[]})
    assert client(OUTSIDER,'/api/projects/files?project_id='+pid)[0]==404
    content=base64.b64encode(b'project document').decode()
    assert client(MEMBER,'/api/projects/files',{'project_id':pid,'name':'plan.txt','content_base64':content})[0]==200
    assert client(OWNER,'/api/projects/files?project_id='+pid+'&name=plan.txt')[1]['content_base64']==content
    status,result=client(MEMBER,'/api/projects/chat',{'project_id':pid,'bot_participants':['writer']})
    assert status==200,result
    session=models.get_session(result['session']['session_id'])
    assert session.project_shared and session.project_id==pid
    assert session_access(session,OWNER) and session_access(session,MEMBER)
    assert not session_access(session,OUTSIDER)
    assert client(MEMBER,'/api/session/status?session_id='+session.session_id)[0]==200
    assert client(OUTSIDER,'/api/session/status?session_id='+session.session_id)[0]==404
    assert client(MEMBER,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'members':[]})[0]==403
    status,result=client(OWNER,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'members':[]})
    assert status==200,result
    assert not session_access(session,MEMBER)
    assert client(MEMBER,'/api/session/status?session_id='+session.session_id)[0]==404
    assert client(MEMBER,'/api/chat/start',{'session_id':session.session_id,'message':'@writer hello'})[0] in (403,404)
    assert client(MEMBER,'/api/projects/files?project_id='+pid)[0]==404
    assert client(MEMBER,'/api/projects/chat',{'project_id':pid,'bot_participants':['writer']})[0]==404
    from api.group_chat import require_turn_membership
    with pytest.raises(PermissionError):require_turn_membership(session,MEMBER)
    assert client(OWNER,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'members':[MEMBER]})[0]==409


def test_files_reject_traversal_symlinks_overwrite_and_unknown_bot(client):
    p=create(client);pid=p['project_id'];content=base64.b64encode(b'test').decode()
    for name in ['../outside','.env','folder/file']:
        assert client(OWNER,'/api/projects/files',{'project_id':pid,'name':name,'content_base64':content})[0]==400
    outside=client.tmp/'outside.txt';outside.write_text('private')
    from pathlib import Path
    (Path(p['workspace'])/'link.txt').symlink_to(outside)
    assert client(MEMBER,'/api/projects/files?project_id='+pid+'&name=link.txt')[0]==400
    assert client(OWNER,'/api/projects/chat',{'project_id':pid,'bot_participants':['admin']})[0]==400
    assert client(OUTSIDER,'/api/projects/chat',{'project_id':pid,'bot_participants':['writer']})[0]==404


def test_project_deletion_retains_revocation_tombstone(client):
    p=create(client);pid=p['project_id']
    result=client(OWNER,'/api/projects/chat',{'project_id':pid})[1]
    from api import models
    from api.project_collaboration import session_access
    session=models.get_session(result['session']['session_id'])
    status,result=client(OWNER,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'deleted':True})
    assert status==200,result
    assert not session_access(session,OWNER)
    assert client(OWNER,'/api/projects/files?project_id='+pid)[0]==404


def test_project_membership_does_not_grant_bot_or_file_capability(client):
    p=create(client)
    status,result=client(OWNER,'/api/projects/team',{'project_id':p['project_id'],'revision':p['revision'],'members':[MEMBER,RESTRICTED]})
    assert status==200,result
    assert client(RESTRICTED,'/api/projects/files?project_id='+p['project_id'])[0]==403
    status,result=client(RESTRICTED,'/api/projects/chat',{'project_id':p['project_id'],'bot_participants':['writer']})
    assert status==400 and 'not allowed' in result['error']


def test_existing_create_entrypoint_uses_shared_model_and_legacy_adoption_keeps_old_chats_private(client):
    from api import models
    from api.project_collaboration import session_access
    status,result=client(OWNER,'/api/projects/create',{'name':'Sidebar project'})
    assert status==200,result
    assert result['project']['collaboration']
    legacy={'project_id':'legacy','name':'Old project','owner_email':OWNER,'profile':'default'}
    models.save_projects(models.load_projects(_migrate=False)+[legacy])
    old_session=SimpleNamespace(project_id='legacy',project_shared=False,owner_email=OWNER,participants=[])
    status,result=client(OWNER,'/api/projects/team',{'project_id':'legacy','revision':0,'members':[MEMBER],'bot_participants':['writer']})
    assert status==200,result
    assert result['project']['collaboration']
    assert session_access(old_session,MEMBER) is None
    assert client(MEMBER,'/api/projects/chat',{'project_id':'legacy','bot_participants':['writer']})[0]==200


def test_ephemeral_project_file_scope_uses_actual_engine_decisions_and_revokes(client,monkeypatch):
    from api import models
    from api.project_collaboration import runtime_file_scope
    from api.governance.agent_context import bind_governed_agent_turn, reset_governed_agent_turn
    from hermes_cli.dashboard_governance.context import current_governance_context
    from hermes_cli.dashboard_governance.tool_policy import tool_arguments_allowed_for_context
    p=create(client);pid=p['project_id']
    status,result=client(MEMBER,'/api/projects/chat',{'project_id':pid})
    assert status==200,result
    session=models.get_session(result['session']['session_id'])
    root,check=runtime_file_scope(session,MEMBER,'writer')
    token=bind_governed_agent_turn(MEMBER,active_profile='writer',session_id=session.session_id,
        project_workspace=root,project_access_check=check)
    try:
        ctx=current_governance_context()
        assert ctx is not None
        from pathlib import Path
        inside=Path(root)/'plan.txt';inside.write_text('project evidence')
        outside=client.tmp/'private.txt';outside.write_text('private')
        assert tool_arguments_allowed_for_context(ctx,'read_file',{'path':str(inside)}).allowed
        monkeypatch.setenv('TERMINAL_CWD',root)
        monkeypatch.setenv('TERMINAL_ENV','local')
        from model_tools import handle_function_call
        reply=handle_function_call('read_file',{'path':'plan.txt'},task_id='project-runtime-fixture')
        assert 'project evidence' in str(reply), reply
        written=handle_function_call('write_file',{'path':'draft.txt','content':'member output'},task_id='project-runtime-fixture')
        assert (Path(root)/'draft.txt').read_text()=='member output',written
        private_reply=handle_function_call('read_file',{'path':str(outside)},task_id='project-runtime-fixture')
        assert 'private' not in str(private_reply).lower() or 'blocked' in str(private_reply).lower()


        assert tool_arguments_allowed_for_context(ctx,'write_file',{'path':str(Path(root)/'new.txt')}).allowed
        assert not tool_arguments_allowed_for_context(ctx,'read_file',{'path':str(outside)}).allowed
        (Path(root)/'escape.txt').symlink_to(outside)
        assert not tool_arguments_allowed_for_context(ctx,'read_file',{'path':str(Path(root)/'escape.txt')}).allowed
        status,result=client(OWNER,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'members':[]})
        assert status==200,result
        assert not tool_arguments_allowed_for_context(ctx,'read_file',{'path':str(inside)}).allowed
        denied=handle_function_call('read_file',{'path':'plan.txt'},task_id='project-runtime-fixture')
        assert 'project evidence' not in str(denied), denied
        handle_function_call('write_file',{'path':'draft.txt','content':'after revoke'},task_id='project-runtime-fixture')
        assert (Path(root)/'draft.txt').read_text()=='member output'

    finally:reset_governed_agent_turn(token)


def test_new_group_roster_is_persisted_before_first_turn(client):
    from api import models
    status,result=client(OWNER,'/api/session/new',{'participants':[MEMBER],'bot_participants':['writer']})
    assert status==200,result
    disk=models.Session.load(result['session']['session_id'])
    assert disk.owner_email==OWNER
    assert disk.participants==[MEMBER]
    assert disk.bot_participants==['writer']


def test_governance_admin_can_read_manage_but_not_deleted_project(client):
    p=create(client);pid=p['project_id']
    assert client(ADMIN,'/api/projects/files?project_id='+pid)[0]==200
    status,result=client(ADMIN,'/api/projects/team',{'project_id':pid,'revision':p['revision'],'members':[OUTSIDER]})
    assert status==200,result
    assert result['project']['owner_email']==OWNER
    assert client(MEMBER,'/api/projects/files?project_id='+pid)[0]==404
    assert client(OUTSIDER,'/api/projects/files?project_id='+pid)[0]==200
    status,result=client(ADMIN,'/api/projects/team',{'project_id':pid,'revision':result['project']['revision'],'deleted':True})
    assert status==200,result
    assert client(ADMIN,'/api/projects/files?project_id='+pid)[0]==404


def test_legacy_project_writer_holds_shared_transaction_lock(client,monkeypatch):
    from api import models,routes
    from threading import Thread
    p=create(client)
    models.save_projects(models.load_projects(_migrate=False)+[{'project_id':'personal','name':'Old','owner_email':OWNER,'profile':'default'}])
    original=routes.save_projects
    attempted=[]
    def saved(rows):
        def competing_writer():
            acquired=models.PROJECTS_LOCK.acquire(blocking=False)
            attempted.append(acquired)
            if acquired:models.PROJECTS_LOCK.release()
        thread=Thread(target=competing_writer);thread.start();thread.join(timeout=3)
        assert not thread.is_alive()
        original(rows)
    monkeypatch.setattr(routes,'save_projects',saved)
    assert client(OWNER,'/api/projects/rename',{'project_id':'personal','name':'Renamed'})[0]==200
    assert attempted==[False]
    assert client(OWNER,'/api/projects/team',{'project_id':p['project_id'],'revision':p['revision'],'members':[]})[0]==200
    assert models.load_projects(_migrate=False)[0]['name']=='Renamed'
    assert client(MEMBER,'/api/projects/files?project_id='+p['project_id'])[0]==404


def test_replay_stops_when_project_membership_changes(client, monkeypatch):
    from api import routes
    p=create(client)
    status,result=client(MEMBER,'/api/projects/chat',{'project_id':p['project_id'],'bot_participants':['writer']})
    sid=result['session']['session_id']
    handler=SimpleNamespace(headers={'Cookie':MEMBER})
    monkeypatch.setattr(routes,'_stream_id_owner_session_id',lambda stream:sid)
    monkeypatch.setattr(routes,'find_run_summary',lambda stream:{'session_id':sid,'terminal':True})
    monkeypatch.setattr(routes,'read_run_events',lambda *a,**kw:{'events':[{'event':'token','payload':'first'},{'event':'token','payload':'secret after revocation'}]})
    emitted=[]
    def emit(handler,event,payload,event_id):
        emitted.append(payload)
        assert client(OWNER,'/api/projects/team',{'project_id':p['project_id'],'revision':p['revision'],'members':[]})[0]==200
    monkeypatch.setattr(routes,'_sse_with_id',emit)
    routes._replay_run_journal(handler,'run-project',None)
    assert emitted==['first']


def test_runtime_file_scope_keeps_authenticated_group_claims(client, monkeypatch):
    from api import auth, models
    from api.governance import loader
    from api.project_collaboration import runtime_file_scope
    p=create(client)
    status,result=client(MEMBER,'/api/projects/chat',{'project_id':p['project_id'],'bot_participants':['writer']})
    session=models.get_session(result['session']['session_id'])
    policy=loader.parse_governance_policy({'version':1,'mode':'enforce','roles':{'sso_role':{'grants':{'permissions':['files:read','sessions:read'],'profiles':['writer']}}},'groups':{'sso-team':{'roles':['sso_role']}}})
    loader.set_policy_loader(lambda:policy)
    identity={'email':MEMBER,'groups':['sso-team']}
    root,check=runtime_file_scope(session,identity,'writer')
    assert check(root+'/plan.txt')
    assert not check(root+'/plan.txt',True)
    _,without=runtime_file_scope(session,{'email':MEMBER},'writer')
    assert not without(root+'/plan.txt')
