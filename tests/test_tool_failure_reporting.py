"""A completed invocation may have failed; never present its effect as success."""
import json
import re
import subprocess
from pathlib import Path

import pytest

from api.streaming import _tool_result_is_error, _extract_tool_calls_from_messages

CASES = [
    ({"error": "Action blocked by governance: workspace_access_revoked"}, True),
    ({"error": {"message": "denied"}}, True),
    ({"success": False}, True),
    ({"is_error": True}, True),
    ({"isError": True}, True),
    ({"success": True, "error": None}, False),
    ({"error": ""}, False),
    ({"content": '{"error":"workspace_access_revoked"}', "path": "/qa/read.txt"}, False),
    ({"output": "Action blocked by governance: workspace_access_revoked"}, False),
    ("Action blocked by governance: workspace_access_revoked", False),
    ([], False),
    (None, False),
]


@pytest.mark.parametrize("value,expected", CASES)
def test_backend_error_envelope_is_not_file_content(value, expected):
    assert _tool_result_is_error(value) is expected
    assert _tool_result_is_error(json.dumps(value)) is expected


def test_persisted_completed_tool_keeps_failure_flag():
    messages = [{"role": "assistant", "tool_calls": [{"id": "call1", "function": {
        "name": "write_file", "arguments": '{"path":"/qa/blocked.txt"}'}}]},
        {"role": "tool", "tool_call_id": "call1", "content": json.dumps(CASES[0][0])}]
    card = _extract_tool_calls_from_messages(messages)[0]
    assert card["is_error"] is True
    assert "workspace_access_revoked" in card["snippet"]


def test_actual_frontend_envelopes_and_group_summaries():
    source = (Path(__file__).parents[1] / "static/ui.js").read_text()
    names = ['_toolResultIsError', '_toolResultErrorsByTid', '_toolDisplayName',
             '_toolActionKind', '_toolTargetLabel', '_toolVisibleTargetLabel',
             '_decodeToolLabelEntities', '_redactToolTargetLabel', '_toolI18n',
             '_toolActionLabelText', '_toolWorklogActionParts', '_toolWorklogSummaryLine',
             '_toolWorklogJoin', '_toolWorklogSummary', '_anchorSceneToolCallFromRow', '_messageRenderCacheSignature']
    functions = [re.search(rf'(?ms)^function {name}\(.*?^\}}', source).group(0) for name in names]
    script = "const assert=require('node:assert/strict'); const window={}; const S={messages:[],toolCalls:[]}; function msgContent(m){return m.content||'';} function _messageHasReasoningPayload(){return false;}\n" + '\n'.join(functions)
    script += '\nconst cases=' + json.dumps(CASES) + ';'
    script += r'''
for(const [raw,expected] of cases)assert.equal(_toolResultIsError(raw),expected);
const failed={name:'write_file',done:true,is_error:true};
const success={name:'write_file',done:true,is_error:false};
assert.match(_toolWorklogSummary([failed]),/^Failed/);
assert.doesNotMatch(_toolWorklogSummary([failed]),/Updated/);
assert.equal(_toolWorklogSummary([success]),'Updated a file');
assert.equal(_toolWorklogSummary([failed,success]),'Updated a file, 1 failed');
assert.equal(_toolWorklogSummary([failed,failed]),'2 failed');
assert.deepEqual(_toolResultErrorsByTid([
 {role:'tool',tool_call_id:'one',content:JSON.stringify({error:'denied'})},
 {role:'tool',tool_call_id:'two',content:JSON.stringify({content:'{"error":"denied"}'})},
 {role:'user',content:[{type:'tool_result',tool_use_id:'three',is_error:true,content:'blocked'}]}
]),{one:true,two:false,three:true});
S.messages=[{role:'assistant',_partial_tool_calls:[{tid:'failed-call',name:'write_file',snippet:'same result',is_error:false}]}];
const before=_messageRenderCacheSignature();
S.messages[0]._partial_tool_calls[0].is_error=true;
assert.notEqual(_messageRenderCacheSignature(),before);
const settled=_anchorSceneToolCallFromRow({tool:{id:'failed-call',name:'write_file',is_error:false},payload:{},status:'completed'},{settled:true});
assert.equal(settled.is_error,true);
assert.equal(_anchorSceneToolCallFromRow({tool:{id:'other-call',name:'write_file',is_error:false},payload:{},status:'completed'},{settled:true}).is_error,false);
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
