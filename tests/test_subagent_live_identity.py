import subprocess
from pathlib import Path


def test_distinct_workers_never_merge_by_tool_name():
    source=Path("static/messages.js").read_text()
    start=source.index("  function _stableStringify(")
    end=source.index("  let _lastRenderMs=0;",start)
    script="""
const assert=require('node:assert/strict');
const activeSid='session',INFLIGHT={},uploaded=[];
const S={messages:[]};const assistantRow=null;
const _assistantSegmentSeq=1,_currentLiveSegmentSeq=1,_currentActivityBurstId=1;
function persistInflightState(){}
"""+source[start:end]+"""
const a={name:'subagent_progress',tid:'subagent:a',args:{status:'queued',task:'A'}};
const b={name:'subagent_progress',tid:'subagent:b',args:{status:'queued',task:'B'}};
upsertLiveToolCall(a,'start');upsertLiveToolCall(b,'start');
assert.equal(S.toolCalls.length,2,'distinct explicit worker IDs must not merge by name');
for(const item of [a,b])upsertLiveToolCall({...item,args:{...item.args,status:'running'}},'start');
for(const item of [a,b])upsertLiveToolCall({...item,args:{...item.args,status:'completed'}},'complete');
assert.equal(S.toolCalls.length,2);
assert.deepEqual(S.toolCalls.map(t=>[t.tid,t.args.status]),[['subagent:a','completed'],['subagent:b','completed']]);
"""
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True)
    assert result.returncode==0,result.stderr


def test_settled_worker_state_advances_without_fabricating_success():
    source=Path("static/messages.js").read_text()
    start=source.index("  function _mergeSubagentActivityRow(")
    end=source.index("  function _completeSettledAnchorSceneForTurn(",start)
    script="const assert=require('node:assert/strict');\n"+source[start:end]+"""
const row=(status,id='subagent:a')=>({row_id:'first',order_index:1,status:'completed',tool:{id,name:'subagent_progress',args:{status,task:'A'}},payload:{args:{status,task:'A'}}});
let state=row('queued');state=_mergeSubagentActivityRow(state,row('running'));
assert.equal(state.tool.args.status,'running');
state=_mergeSubagentActivityRow(state,row('completed'));
assert.equal(state.tool.args.status,'completed');assert.equal(state.payload.args.status,'completed');
assert.equal(_mergeSubagentActivityRow(state,row('queued')).tool.args.status,'completed');
assert.equal(_mergeSubagentActivityRow(row('running'),row('failed')).tool.args.status,'failed');
assert.equal(_mergeSubagentActivityRow(row('queued'),row('completed','subagent:b')).tool.args.status,'queued');
assert.equal(_mergeSubagentActivityRow(row('running'),row('running')).tool.args.status,'running');
"""
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
