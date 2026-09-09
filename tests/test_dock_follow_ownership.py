"""Exercise actual deferred dock layout callbacks against viewport ownership."""
import subprocess

import pytest


SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source={ui:fs.readFileSync('static/ui.js','utf8'),sessions:fs.readFileSync('static/sessions.js','utf8'),
 terminal:fs.readFileSync('static/terminal.js','utf8'),messages:fs.readFileSync('static/messages.js','utf8')};
function extract(text,name){const start=text.indexOf('function '+name+'(');assert.ok(start>=0,name);
 const end=text.indexOf('\n}',start);assert.ok(end>start);return text.slice(start,end+2);}
const helpers=[['_syncHandoffDockSpace','sessions','_handoffMessagesEl','_handoffIsMessagesNearBottom'],
 ['_syncTerminalTranscriptSpace','terminal','_terminalMessagesEl','_terminalIsMessagesNearBottom'],
 ['_syncApprovalTranscriptSpace','messages',null,'_approvalMessagesNearBottom'],
 ['_syncClarifyTranscriptSpace','messages',null,'_clarifyMessagesNearBottom']];
function setup(index){
 const [name,file,element,near]=helpers[index], frames=[],timers=[],writes=[];
 const style={values:{},setProperty(k,v){this.values[k]=v;},removeProperty(k){delete this.values[k];}};
 const messages={scrollHeight:1000,scrollTop:400,clientHeight:600,style,
  classList:{add(){},remove(){},toggle(){}}};
 const card={classList:{contains:key=>key==='visible'},getBoundingClientRect:()=>({height:100}),
  querySelector(){return this;}};
 const ctx={S:{session:{session_id:'one'}},_messageScrollInputGeneration:5,_messageUserUnpinned:false,_scrollPinned:true,
  console,document:{getElementById:()=>messages},$:id=>id==='messages'?messages:card,
  scrollToBottom:()=>writes.push('follow'),requestAnimationFrame:fn=>frames.push(fn),setTimeout:fn=>timers.push(fn),
  TERMINAL_UI:{open:true},_terminalEls:()=>({panel:card,inner:card,dock:card})};
 if(element)ctx[element]=()=>messages;
 vm.createContext(ctx);
 if(source.ui.includes('function _messageDockFollowCallback('))vm.runInContext(extract(source.ui,'_messageDockFollowCallback'),ctx);
 vm.runInContext(extract(source[file],near)+extract(source[file],name),ctx);
 return {ctx,messages,card,writes,frames,timers,invoke:open=>ctx[name](index<2?open:(open?card:null)),
  flush(){for(const fn of frames.splice(0))fn();for(const fn of timers.splice(0))fn();}};
}
'''


@pytest.mark.parametrize('dock', range(4), ids=['handoff', 'terminal', 'approval', 'clarify'])
def test_deferred_dock_follow_yields_to_newer_viewport_or_session(dock):
    body = r'''
for(const open of [false,true])for(const reason of ['start','session','unpin','pin-lost','element','later-end']){
 const f=setup(DOCK);f.invoke(open);
 if(reason==='start'){f.ctx._messageScrollInputGeneration++;f.messages.scrollTop=0;f.ctx._scrollPinned=false;f.ctx._messageUserUnpinned=true;}
 if(reason==='session')f.ctx.S.session={session_id:'two'};
 if(reason==='unpin')f.ctx._messageUserUnpinned=true;
 if(reason==='pin-lost')f.ctx._scrollPinned=false;
 if(reason==='element')f.ctx.$=id=>id==='messages'?{}:f.card;
 if(reason==='later-end'){f.ctx._messageScrollInputGeneration++;f.ctx.scrollToBottom();}
 f.flush();assert.equal(f.writes.length,reason==='later-end'?1:0,reason+' open='+open);
 if(open)assert.ok(Object.keys(f.messages.style.values).length,'geometry still measured');
}
'''.replace('DOCK', str(dock))
    result = subprocess.run(['node', '-e', SCRIPT + body], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('dock', range(4), ids=['handoff', 'terminal', 'approval', 'clarify'])
def test_current_dock_follow_preserves_tail_and_does_not_invent_reader_intent(dock):
    body = r'''
for(const open of [false,true]){
 const f=setup(DOCK);f.invoke(open);f.flush();assert.equal(f.writes.length,open?2:1);
 assert.equal(f.ctx._messageScrollInputGeneration,5);
 const away=setup(DOCK);away.messages.scrollTop=0;away.messages.scrollHeight=2000;
 away.invoke(open);away.flush();assert.equal(away.writes.length,0);
}
'''.replace('DOCK', str(dock))
    result = subprocess.run(['node', '-e', SCRIPT + body], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
