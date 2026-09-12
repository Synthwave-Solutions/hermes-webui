"""Execute the shipped polling/DOM renderer with deterministic async boundaries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest

DRIVER = r'''
const vm=require('node:vm'),fs=require('node:fs');
const spec=JSON.parse(fs.readFileSync(0,'utf8'));
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.parentElement=null;this._text='';this.listeners={};}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set textContent(v){this._text=String(v);this.children=[];}
 append(...values){for(const v of values){v.parentElement=this;this.children.push(v);}}
 insertBefore(v,before){v.parentElement=this;this.children.splice(this.children.indexOf(before),0,v);}
 remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);}
 querySelectorAll(sel){let found=[];for(const c of this.children){if(sel==='[data-skill-learning-notice]'&&c.dataset.skillLearningNotice||sel==='[data-msg-idx]'&&c.dataset.msgIdx!==undefined)found.push(c);found.push(...c.querySelectorAll(sel));}return found;}
 addEventListener(event,fn){this.listeners[event]=fn;}
}
const clone=v=>JSON.parse(JSON.stringify(v));
const host=new Element('main'),requests=[],timers=new Map();let n=0,now=1000000,payload=spec.payload,deferred=null,hold=false;
const S={session:{session_id:'chat-a'},messages:[{timestamp:800},{timestamp:1100}]};
const document={hidden:false,getElementById:()=>host,querySelectorAll:s=>host.querySelectorAll(s),createElement:t=>new Element(t),createTextNode:v=>{const e=new Element('#text');e.textContent=v;return e},addEventListener(){}};
const context={S,document,_currentPanel:'chat',_loadingSessionId:null,AbortController,queueMicrotask,console,
 Date:class extends Date{static now(){return now;}},
 setTimeout:fn=>{timers.set(++n,fn);return n;},clearTimeout:id=>timers.delete(id),
 api:async(url)=>{requests.push(url);if(hold){hold=false;return new Promise(r=>deferred=r);}return url.includes('session_id=chat-a')?clone(payload):{events:[]};},
 addEventListener(){}};context.window=context;
vm.createContext(context);vm.runInContext(spec.source,context);
function render(sid='chat-a'){S.session={session_id:sid};host.children=[];S.messages.forEach((m,i)=>{const e=new Element('article');e.dataset.msgIdx=String(i);e.textContent='Message '+i;host.append(e)});context.SynthPulseSkillActivity.sync(true);}
const settle=()=>new Promise(setImmediate);
const notices=()=>host.querySelectorAll('[data-skill-learning-notice]').map(n=>n.textContent);
(async()=>{
 render();await settle();const first=notices();
 if(spec.action==='poll'){payload=spec.next;now+=11000;const callbacks=[...timers.values()];timers.clear();callbacks.forEach(f=>f());await settle();}
 if(spec.action==='stale'){render('chat-b');await settle();hold=true;render('chat-a');await settle();render('chat-b');deferred(clone(spec.payload));await settle();}
 process.stdout.write(JSON.stringify({first,notices:notices(),requests,messages:S.messages,order:host.children.map(x=>x.textContent)}));
})().catch(e=>{console.error(e);process.exitCode=1});
'''

def execute(payload, **kw):
    node=shutil.which('node')
    if not node: pytest.skip('Node required for frontend behavior')
    root=Path(os.environ.get('SKILL_NOTICE_SOURCE_ROOT',Path(__file__).parents[1]))
    spec={'source':(root/'static/skill_learning_activity.js').read_text(),'payload':payload,**kw}
    r=subprocess.run([node,'-e',DRIVER],input=json.dumps(spec),text=True,capture_output=True,timeout=10,check=True)
    return json.loads(r.stdout)

def event(skills=None):
    row={'id':'a'*64,'created_at':900,'counts':{'created':1,'patched':2,'updated':0}}
    if skills is not None: row['skills']=skills
    return {'events':[row]}

NAMED=[{'name':'build-workflow','kind':'created','count':1},{'name':'cloud-check','kind':'patched','count':2}]

def test_named_updates_render_inline_and_poll_without_manual_refresh():
    result=execute({'events':[]},action='poll',next=event(NAMED))
    assert result['first']==[]
    assert len(result['notices'])==1
    assert 'Skill automatically created: build-workflow' in result['notices'][0]
    assert 'Skill automatically patched: cloud-check × 2' in result['notices'][0]
    assert 'build-workflow' in result['order'][1]
    assert result['messages']==[{'timestamp':800},{'timestamp':1100}]
    assert all(url.startswith('/api/session/skill-updates?session_id=') for url in result['requests'])
    # A fresh JS runtime models reload: API/store identity is independent of DOM.
    assert 'cloud-check' in execute(event(NAMED))['notices'][0]


def test_legacy_event_is_explicit_about_missing_name():
    result=execute(event())
    assert 'Skill name was not recorded' in result['notices'][0]
    assert 'build-workflow' not in result['notices'][0]


def test_late_named_response_cannot_cross_chat_navigation():
    assert execute(event(NAMED),action='stale')['notices']==[]


@pytest.mark.parametrize('skills',[
    [{'name':'<img src=x onerror=alert(1)>','kind':'created','count':1}],
    [{'name':'/private/key','kind':'created','count':1}],
    [{'name':'safe','kind':'created','count':2}],
])
def test_invalid_name_metadata_is_not_rendered_as_content(skills):
    result=execute(event(skills))
    assert result['notices']==['Skill update notices are unavailable.Retry']
