"""Execute actual navigation functions with a deliberately delayed create reply."""
import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("reselect_current", [False, True])
def test_new_chat_retires_old_load_but_honors_a_later_sidebar_choice(reselect_current):
    source = (Path(__file__).resolve().parents[1] / "static/sessions.js").read_text()
    new_chat = source[source.index("async function newSession("):source.index("/**\n * Self-heal:")]
    load = source[source.index("async function loadSession(sid)"):source.index("// ── Handoff hint logic")]
    script = r"""
const assert=require('node:assert/strict');
const reselect=JSON.parse(process.argv[1]);
let resolveCreate, calls=0, pending=false, savedSid='old', urlSid='old', renders=0;
const response=new Promise(resolve=>resolveCreate=resolve);
const original={session_id:'old',messages:[{role:'user',content:'Original transcript'}]};
const S={session:original,messages:original.messages,toolCalls:[],activeProfile:'default'};
const window=globalThis;
const localStorage={setItem(_key,value){savedSid=value;}};
const $=()=>null;
let _newSessionInFlight=null, _loadSessionGeneration=10, _loadingSessionId='obsolete';
let _messagesTruncated=false, _oldestIdx=0, _activeProject=null, _sessionSourceFilter='webui';
const _setNewSessionPending=value=>pending=value;
const updateQueueBadge=()=>{}, clearLiveToolCards=()=>{}, _rememberNewChatDraftSession=()=>{};
const _setSessionViewedCount=()=>{}, updateSendBtn=()=>{}, setStatus=()=>{}, setComposerStatus=()=>{};
const syncTopbar=()=>{}, renderMessages=()=>renders++, _deferWorkspaceRefreshForSession=()=>{};
const _setActiveSessionUrl=sid=>urlSid=sid;
const _rearmActiveSessionStream=()=>{}, _sessionVisitHasUnreadState=()=>false;
const api=async(url)=>{assert.equal(url,'/api/session/new');calls++;return await response;};
""" + new_chat + load + r"""
(async()=>{
 const first=newSession();
 assert.equal(calls,1);assert.equal(pending,true);
 assert.equal(_loadSessionGeneration,11,'New Chat must retire an older load before awaiting the server');
 assert.equal(_loadingSessionId,null);
 const duplicate=newSession();
 assert.equal(calls,1,'concurrent New Chat requests still deduplicate');
 if(reselect){
   await loadSession('old');
   assert.equal(_loadSessionGeneration,12,'even reselecting the current sidebar row is a newer choice');
 }
 resolveCreate({session:{session_id:'created',messages:[],last_usage:{}}});
 await Promise.all([first,duplicate]);
 assert.equal(pending,false);assert.equal(_newSessionInFlight,null);
 assert.equal(S.session.session_id,reselect?'old':'created');
 assert.equal(savedSid,reselect?'old':'created');assert.equal(urlSid,savedSid);
 assert.equal(renders,reselect?0:1);
 if(reselect) assert.deepEqual(S.messages,original.messages);
})().catch(error=>{console.error(error);process.exit(1);});
"""
    result = subprocess.run(["node", "-e", script, json.dumps(reselect_current)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
