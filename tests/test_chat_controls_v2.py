"""Exercise the actual mode controller in Node, including navigation races."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_segments_send_modes_and_ignore_other_session_reply():
    source = (ROOT / 'static/ui.js').read_text()
    controller = source[source.index("let _currentChatMode = 'super';"):source.index('// ── Group conversations:')]
    script = r'''
const assert=require('node:assert/strict');
const elements={chatModeNormal:{setAttribute(k,v){this[k]=v}},chatModeSuper:{setAttribute(k,v){this[k]=v}}};
const $=id=>elements[id], t=x=>x,showToast=()=>{};
let S={session:null},calls=[],resolve;
const api=(url,opt)=>{calls.push({url,body:JSON.parse(opt.body)});return new Promise(r=>resolve=r)};
''' + controller + r'''
(async()=>{
setChatMode('normal');assert.equal(S._pendingChatMode,'normal');assert.equal(elements.chatModeNormal['aria-pressed'],'true');
S.session={session_id:'one',chat_mode:'normal'};
setChatMode('super');assert.deepEqual(calls[0].body,{session_id:'one',mode:'super'});
resolve({ok:true,chat_mode:'super'});await Promise.resolve();assert.equal(S.session.chat_mode,'super');
setChatMode('normal');assert.deepEqual(calls[1].body,{session_id:'one',mode:'normal'});
S.session={session_id:'two',chat_mode:'super'};resolve({ok:true,chat_mode:'normal'});await Promise.resolve();assert.equal(S.session.chat_mode,'super');
})();
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
