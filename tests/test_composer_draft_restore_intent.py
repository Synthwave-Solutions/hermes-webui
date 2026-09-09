"""Run the real restore function against delayed draft/user-edit orderings."""
import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("mode", ["clear", "untouched", "cross-session", "superseded-session"])
def test_restore_respects_observable_input_and_current_session_ownership(mode):
    source = (Path(__file__).resolve().parents[1] / "static/sessions.js").read_text()
    restore = source[source.index("function _restoreComposerDraft("):source.index("// Clear the saved draft")]
    script = r"""
const assert=require('node:assert/strict');
const mode=JSON.parse(process.argv[1]);
const ta={value:mode==='cross-session'?'Previous conversation draft':''};
const $=()=>ta, saved=[];
const S={session:{session_id:mode==='superseded-session'?'newer':'target'},pendingFiles:[]};
let _loadingSessionId=null, _composerDraftInputGeneration=2;
const _composerDraftHasPayload=(text,files)=>!!(text||files.length);
const _isComposerDraftRestoreSuppressed=()=>false, _clearComposerDraftRestoreSuppression=()=>{};
const _saveComposerDraftNow=(...args)=>saved.push(args);
const autoResize=()=>{},updateSendBtn=()=>{};
""" + restore + r"""
_restoreComposerDraft({text:'Older server draft',files:[]},'target',{
 preserveActiveInput:mode!=='cross-session',inputGeneration:mode==='untouched'?2:0
});
if(mode==='clear'){
 assert.equal(ta.value,'','the intentional empty value must survive a late server reply');
 assert.deepEqual(saved,[['target','',[]]],'persist that newer empty draft in the matching current session');
}else if(mode==='superseded-session'){
 assert.equal(ta.value,'');assert.deepEqual(saved,[],'never persist into a session that lost ownership');
}else{
 assert.equal(ta.value,'Older server draft','untouched boot and ordinary cross-session restores must still work');
 assert.deepEqual(saved,[]);
}
"""
    result = subprocess.run(["node", "-e", script, json.dumps(mode)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
