import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import sidebar_organization as org


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(org,'_path',lambda email:tmp_path/(email+'.json'))
    return tmp_path


def change(email='one', **body):
    return org.update(email,{'revision':org.read(email)['revision'],**body})


def test_nested_sections_move_cycles_and_non_destructive_delete(store):
    a=change(action='create',name='Clients')['sections'][0]['id']
    b=change(action='create',name='Acme',parent=a)['sections'][-1]['id']
    c=change(action='create',name='Planning',parent=b)['sections'][-1]['id']
    change(action='assign',session_id='chat1',section=b)
    with pytest.raises(ValueError,match='itself'):change(action='edit',id=a,name='Clients',parent=c)
    change(action='edit',id=c,name='Delivery',parent=a)
    result=change(action='delete',id=b)
    assert result['assignments']['chat1']==a
    assert {s['id']:s for s in result['sections']}[c]['parent']==a
    result=change(action='delete',id=a)
    assert result['assignments']=={}
    assert result['sections']==[dict(id=c,name='Delivery',parent=None)]


def test_personal_isolation_revision_and_restart_persistence(store):
    result=change(action='create',name='Private')
    assert org.read('two')['sections']==[]
    assert org.read('one')==result
    with pytest.raises(RuntimeError):org.update('one',{'revision':0,'action':'create','name':'Stale'})
    assert org.read('one')==result
    assert not list(store.glob('*.tmp'))


def test_no_fixed_nesting_depth_and_invalid_parent(store):
    parent=None
    for i in range(120):parent=change(action='create',name=str(i),parent=parent)['sections'][-1]['id']
    assert len(org.read('one')['sections'])==120
    with pytest.raises(ValueError):change(action='create',name='Bad',parent='missing')
    with pytest.raises(ValueError):change(action='assign',session_id='../outside',section=parent)
    with pytest.raises(ValueError):change(action='create',name='\ninvalid')


def test_task_preferences_do_not_modify_sections(store):
    change(action='grouping',value='bot')
    change(action='category',session_id='job1',category='Operations')
    data=org.read('one')
    assert data['task_grouping']=='bot' and data['task_categories']=={'job1':'Operations'}
    assert data['sections']==[]
    assert change(action='category',session_id='job1',category='')['task_categories']=={}


def test_route_rejects_other_users_chat_and_ignores_client_identity(store,monkeypatch):
    from api import ownership,routes
    monkeypatch.setattr(ownership,'request_owner_email',lambda h:'one')
    monkeypatch.setattr(routes,'get_session',lambda sid:SimpleNamespace(owner_email='two'))
    monkeypatch.setattr(routes,'_session_visible_to_request',lambda s,h:False)
    monkeypatch.setattr(routes,'bad',lambda h,msg,status=400:(status,msg))
    monkeypatch.setattr(routes,'j',lambda h,payload:payload)
    assert org.handle(object(),{'revision':0,'action':'assign','session_id':'private','section':None})[0]==404
    result=org.handle(object(),{'revision':0,'action':'create','name':'Mine','email':'two'})
    assert result['sections'][0]['name']=='Mine'
    assert org.read('two')['sections']==[]
    monkeypatch.setattr(ownership,'request_owner_email',lambda h:None)
    assert org.handle(object())[0]==401


def test_frontend_grouping_preserves_rows_nested_collapse_and_search():
    script=r'''
const assert=require('assert');global.window={};global.t=k=>k;
require(process.argv[1]);const org=window.SynthPulseSidebarOrg;
const state={sections:[{id:'a',name:'Clients',parent:null},{id:'b',name:'Acme',parent:'a'},{id:'c',name:'Research',parent:'b'}],assignments:{chat:'c'},task_categories:{},task_grouping:'category_bot'};
const chat={session_id:'chat',title:'Plan'},free={session_id:'free',title:'Free'};
const job={session_id:'job',title:'health check',profile:'ops',cron_job:{job_id:'j'}};
const scout={session_id:'scout',title:'Scout',cron_job:{job_id:'sc',kind:'scout'}};
const rows=[chat,free,job,scout], original=[{label:'Today',items:rows}];
let groups=org.groups(original,rows,'all','',{},state);
assert(groups.some(g=>g.key==='section:c'&&g.items[0]===chat));
assert(groups.some(g=>g.label==='Today'&&g.items.includes(scout)));
assert(!groups.some(g=>g.depth===1&&g.key.startsWith('tasks:')),'tasks collapsed initially');
groups=org.groups(original,rows,'all','',{'section:a':true},state);
assert(!groups.some(g=>g.key==='section:b'||g.key==='section:c'));
groups=org.groups(original,rows,'all','query',{'section:a':true},state);
assert(groups.some(g=>g.key==='section:c'&&g.forceExpanded));
const ids=groups.flatMap(g=>g.items).map(s=>s.session_id).sort();assert.deepStrictEqual(ids,['chat','free','job','scout']);
state.task_grouping='bot';assert(org.taskGroups([job],state)[0].items[0]===job);
for(let i=0;i<150;i++)state.sections.push({id:'deep'+i,name:'Level',parent:i?'deep'+(i-1):'c'});
assert.strictEqual(org.orderedSections(state).at(-1).depth,152);
'''
    source=Path(__file__).resolve().parents[1]/'static/sidebar-organization.js'
    run=subprocess.run(['node','-e',script,str(source)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr


def test_personal_organization_catalog_permissions():
    from api.governance.catalog import route_permission
    for method in ('GET','POST'):
        assert route_permission('/api/me/sidebar-organization',method)=='sessions:read'


def test_ui_section_dialog_and_move_action_submit_personal_changes():
    script=r'''
const assert=require('assert');
class El{
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.attrs={};this.style={};}
 appendChild(e){this.children.push(e);return e;} append(...es){this.children.push(...es);}
 insertBefore(e,b){this.children.splice(this.children.indexOf(b),0,e);}
 setAttribute(k,v){this.attrs[k]=v;}addEventListener(){}remove(){}showModal(){this.shown=true;}close(){this.closed=true;}focus(){}
 click(){return this.onclick?.({stopPropagation(){}});}
}
global.window={};global.document={body:new El('body'),createElement:t=>new El(t)};global.t=k=>k;global.renderSessionListFromCache=()=>{};global.showToast=e=>{throw Error(e);};
let data={revision:0,sections:[],assignments:{},task_categories:{},task_grouping:'category_bot'},posts=[];
global.api=async(url,opts)=>{assert.strictEqual(url,'/api/me/sidebar-organization');if(opts?.method==='POST'){let b=JSON.parse(opts.body);posts.push(b);assert.strictEqual(b.revision,data.revision);data.revision++;if(b.action==='create')data.sections.push({id:'new',name:b.name,parent:b.parent});if(b.action==='assign')data.assignments[b.session_id]=b.section;}return structuredClone(data);};
require(process.argv[1]);let org=window.SynthPulseSidebarOrg;
const all=(e)=>[e,...e.children.flatMap(all)];
(async()=>{
 await org.ensure();const list=new El('div');org.controls(list,'chats');
 await list.children[0].children[0].click();
 let d=document.body.children.at(-1);assert(d.shown);
 all(d).find(e=>e.tag==='input').value='My section';
 await all(d).find(e=>e.tag==='button'&&e.textContent==='sidebar_org_save').click();
 assert.strictEqual(posts[0].name,'My section');assert(d.closed);
 await org.moveChat({session_id:'chat'});d=document.body.children.at(-1);
 all(d).find(e=>e.tag==='select').value='new';
 await all(d).find(e=>e.tag==='button'&&e.textContent==='sidebar_org_save').click();
 assert.strictEqual(posts[1].section,'new');assert.strictEqual(posts[1].session_id,'chat');assert(d.closed);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    source=Path(__file__).resolve().parents[1]/'static/sidebar-organization.js'
    run=subprocess.run(['node','-e',script,str(source)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
