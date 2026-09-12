"""Named private inline notices use confirmed native results, never skill content."""
import json
from types import SimpleNamespace
import pytest
from tests.test_skill_learning_activity import messages

@pytest.fixture
def activity(monkeypatch, tmp_path):
    from api import skill_learning_activity as mod, config
    monkeypatch.setattr(config, 'STATE_DIR', tmp_path)
    return mod


def test_native_review_keeps_confirmed_names_actions_and_original_chat(activity, monkeypatch):
    from agent import background_review as native
    activity.install_adapter()
    def review(*args, **kwargs):
        native.summarize_background_review_actions(messages('create') + messages('patch', call_id='patch')
          + messages('patch', call_id='failed', success=False), [], notification_mode='off')
    monkeypatch.setattr(native, '_run_review_in_thread', review)
    with activity.turn_scope('a@example.test', 'run-a', 'profile-a', 'chat-a'):
        target, _ = native.spawn_background_review_thread(SimpleNamespace(), [], task_cfg={})
    with activity.turn_scope('b@example.test', 'run-b', 'profile-b', 'chat-b'):
        target()
    data = activity.read_activity('a@example.test', 'chat-a')
    assert data['events'][0]['skills'] == [
        {'name':'PRIVATE-SKILL','kind':'created','count':1},
        {'name':'PRIVATE-SKILL','kind':'patched','count':1}]
    assert 'PRIVATE-CONTENT' not in json.dumps(data)
    assert activity.read_activity('b@example.test', 'chat-a')['events'] == []
    assert activity.read_activity('a@example.test', 'chat-b')['events'] == []


def test_legacy_count_only_store_reads_without_invented_names(activity):
    assert activity.record(activity.ReviewScope('a@example.test','old','p','chat-a'), {'created':1,'patched':0,'updated':0})
    path, _ = activity._paths('a@example.test')
    legacy = json.loads(path.read_text()); legacy[0].pop('skills')
    path.write_text(json.dumps(legacy))
    row = activity.read_activity('a@example.test', 'chat-a')['events'][0]
    assert row['skills'] == []
    assert row['counts']['created'] == 1


@pytest.mark.parametrize('method', ['GET','HEAD'])
def test_session_notice_alias_keeps_exact_chat_permission(method):
    from api.governance.catalog import route_permission
    assert route_permission('/api/session/skill-updates', method) == 'chat:use'

@pytest.mark.parametrize('name,expected', [
    ('category/build-workflow','build-workflow'), ('/private/key',''),
    ('../secret',''), ('<script>alert(1)</script>',''), ('notes\nprivate',''), ('a'*65,''),
])
def test_display_metadata_never_exposes_paths_or_arbitrary_content(activity, name, expected):
    rows=messages(); args=json.loads(rows[0]['tool_calls'][0]['function']['arguments']); args['name']=name
    rows[0]['tool_calls'][0]['function']['arguments']=json.dumps(args)
    counts, skills=activity.successful_skill_changes(rows, [])
    assert counts['created']==1
    assert skills==([{'name':expected,'resource':name,'kind':'created','count':1}] if expected else [])


def test_atomic_batch_keeps_default_name_and_ignores_unconfirmed_results(activity):
    operations=[{'action':'patch','old_string':'a','new_string':'b'}, {'action':'create','name':'second'}]
    rows=messages(); rows[0]['tool_calls'][0]['function']['arguments']=json.dumps({'action':'batch','name':'first','operations':operations})
    result={'success':True,'operations_applied':2,'results':[{'action':'patch','name':'first','success':True},{'action':'create','name':'second','success':True}]}
    rows[1]['content']=json.dumps(result)
    assert activity.successful_skill_changes(rows,[])[1]==[{'name':'first','resource':'first','kind':'patched','count':1},{'name':'second','resource':'second','kind':'created','count':1}]
    result['results'][1]['staged']=True;rows[1]['content']=json.dumps(result)
    assert activity.successful_skill_changes(rows,[])[1]==[]


def test_name_metadata_store_remains_bounded_and_restart_safe(activity):
    skills=[{'name':f'skill-{i:02d}-'+'a'*50,'kind':'patched','count':1} for i in range(50)]
    counts={'created':0,'patched':50,'updated':0}
    for i in range(100):
        assert activity.record(activity.ReviewScope('a@example.test',str(i),'p','chat-a'),counts,skills=skills,now=1000+i)
    path,_=activity._paths('a@example.test')
    assert path.stat().st_size<=activity._MAX_BYTES
    rows=activity.read_activity('a@example.test','chat-a',now=1200)['events']
    assert 0<len(rows)<100
    assert rows[0]['skills']==skills
    assert rows[0]['created_at']==1099


@pytest.mark.parametrize('bad', [
    [{'name':'../secret','kind':'created','count':1}],
    [{'name':'safe','kind':'created','count':2}],
    [{'name':'safe','kind':'created','count':1,'content':'PRIVATE'}],
    [{'name':'safe','kind':'unknown','count':1}],
])
def test_invalid_name_metadata_cannot_poison_existing_store(activity, bad):
    scope=activity.ReviewScope('a@example.test','good','p','chat-a')
    counts={'created':1,'patched':0,'updated':0}
    assert activity.record(scope,counts)
    path,_=activity._paths('a@example.test'); before=path.read_bytes()
    assert not activity.record(activity.ReviewScope('a@example.test','bad','p','chat-a'),counts,skills=bad)
    assert path.read_bytes()==before


@pytest.mark.parametrize('route',['/api/session/skill-updates','/api/skills/learning-activity'])
@pytest.mark.parametrize('actor,query,status',[
    ('a@example.test','session_id=chat-a',200), ('b@example.test','session_id=chat-a',200),
    ('outsider@example.test','session_id=chat-a',404), ('','session_id=chat-a',401),
    ('a@example.test','session_id=missing',404), ('a@example.test','session_id=chat-a&actor=b@example.test',400),
])
def test_both_routes_use_same_actual_dispatch_and_membership(activity,monkeypatch,route,actor,query,status):
    from urllib.parse import urlparse
    from api import routes,ownership,models
    session=SimpleNamespace(owner_email='a@example.test', participants=['b@example.test'],project_shared=False)
    def get_session(sid):
        if sid!='chat-a': raise KeyError(sid)
        return session
    monkeypatch.setattr(models,'get_session',get_session)
    monkeypatch.setattr(ownership,'_request_identity',lambda h:{'email':h.email})
    monkeypatch.setattr(activity,'j',lambda h,data,**kw:(kw.get('status',200),data,kw))
    counts={'created':1,'patched':0,'updated':0}
    assert activity.record(activity.ReviewScope('a@example.test','r','p','chat-a'),counts,skills=[{'name':'private-a','kind':'created','count':1}])
    response=routes.handle_get(SimpleNamespace(email=actor,headers={},command='GET'),urlparse(route+'?'+query))
    assert response[0]==status
    assert response[2]['extra_headers']['Cache-Control']=='no-store'
    if status==200:
        assert len(response[1]['events'])==(1 if actor=='a@example.test' else 0)
        session.participants=[]
        if actor=='b@example.test':
            assert routes.handle_get(SimpleNamespace(email=actor,headers={},command='GET'),urlparse(route+'?'+query))[0]==404

@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_notice_alias_does_not_grant_mutation_permission(method):
    from api.governance.catalog import route_permission
    assert route_permission('/api/session/skill-updates',method)=='skills:write'


def test_notice_alias_permission_does_not_expand_session_namespace():
    from api.governance.catalog import route_permission
    assert route_permission('/api/session/skill-updates/export','GET')=='sessions:read'
    assert route_permission('/api/session','GET')=='sessions:read'

@pytest.mark.parametrize('route',['/api/session/skill-updates','/api/skills/learning-activity'])
def test_current_category_deny_and_revocation_hide_names_and_known_counts(activity,monkeypatch,route):
    from urllib.parse import urlparse
    from api import routes,ownership,models
    from api.governance import enforce,loader
    identity={'email':'a@example.test','groups':[]}
    monkeypatch.setattr(ownership,'_request_identity',lambda h:identity)
    monkeypatch.setattr(enforce,'_request_identity',lambda h:identity)
    monkeypatch.setattr(models,'get_session',lambda sid:SimpleNamespace(owner_email=identity['email'],participants=[],project_shared=False))
    monkeypatch.setattr(activity,'j',lambda h,data,**kw:(kw.get('status',200),data))
    def policy(deny=()):
        parsed=loader.parse_governance_policy({'mode':'enforce','roles':{'member':{'grants':{
            'permissions':['chat:use'],'skills':{'view':['*']}}}},'users':{identity['email']:{'roles':['member'],'deny':{'skills':{'view':list(deny)}}}}})
        monkeypatch.setattr(loader,'get_policy',lambda:parsed)
    counts={'created':0,'patched':3,'updated':0}
    skills=[{'name':'deploy','resource':'private/deploy','kind':'patched','count':2},
            {'name':'deploy','resource':'public/deploy','kind':'patched','count':1}]
    assert activity.record(activity.ReviewScope(identity['email'],'named','p','chat-a'),counts,skills=skills)
    # Genuine old unnamed metadata remains generic; it cannot be retroactively named.
    assert activity.record(activity.ReviewScope(identity['email'],'legacy','p','chat-a'),{'created':1,'patched':0,'updated':0})
    handler=SimpleNamespace(headers={},command='GET')
    read=lambda:routes.handle_get(handler,urlparse(route+'?session_id=chat-a'))
    policy();status,data=read();assert status==200
    assert next(r for r in data['events'] if r['skills'])['skills']==[{'name':'deploy','kind':'patched','count':3}]
    assert 'resource' not in json.dumps(data) and 'private/' not in json.dumps(data)
    policy(['private/*']);status,data=read();assert status==200
    row=next(r for r in data['events'] if r['skills'])
    assert row['counts']['patched']==1 and row['skills'][0]['count']==1
    policy(['*']);status,data=read();assert status==200
    assert len(data['events'])==1 and data['events'][0]['skills']==[]
    assert data['events'][0]['counts']=={'created':1,'patched':0,'updated':0}
    assert 'deploy' not in json.dumps(data)


def test_policy_failure_returns_unavailable_without_stored_names(activity,monkeypatch):
    from api import ownership,personal_context
    from api.governance import resource_scope
    monkeypatch.setattr(ownership,'_request_identity',lambda h:{'email':'a@example.test'})
    monkeypatch.setattr(personal_context,'session_for',lambda *args:SimpleNamespace())
    monkeypatch.setattr(activity,'j',lambda h,data,**kw:(kw.get('status',200),data))
    assert activity.record(activity.ReviewScope('a@example.test','r','p','chat-a'),{'created':1,'patched':0,'updated':0},skills=[{'name':'hidden','kind':'created','count':1}])
    def fail(*args):raise RuntimeError('PRIVATE policy text')
    monkeypatch.setattr(resource_scope,'access_for',fail)
    status,data=activity.handle_get(None,'session_id=chat-a')
    assert status==503 and 'hidden' not in json.dumps(data) and 'PRIVATE' not in json.dumps(data)
