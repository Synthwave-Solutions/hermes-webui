"""Hidden live activity must not pay the full activity-scene projection cost."""
import json
import subprocess
from pathlib import Path

from tests.test_chat_latency_hotpaths import function

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / 'static/ui.js').read_text()


def test_hidden_mode_skips_projection_and_switching_back_replays_all_activity():
    script = '''
    const fs=require('fs');
    global.window=globalThis;
    eval(fs.readFileSync('static/assistant_turn_anchors.js','utf8'));
    const api=HermesAssistantTurnAnchors;
    const registry=api.createAssistantTurnAnchorRegistry({session_id:'session',stream_id:'stream'});
    window._liveAnchorRegistries=new Map([['stream',registry]]);
    let activeMode='hide_all_activity', projections=0, rendered=[];
    function chatActivityMode(){return activeMode;}
    PROJECT
    const originalProject=_projectLiveAnchorActivitySceneForStream;
    _projectLiveAnchorActivitySceneForStream=(...args)=>{projections++;return originalProject(...args);};
    function renderLiveAnchorActivityScene(stream,scene,opts){
      if(chatActivityMode()==='hide_all_activity')return false;
      rendered.push(scene);return true;
    }
    RENDER
    function add(type,payload,seq){
      api.applyAssistantTurnAnchorSourceEvent(registry,{
        source_event_type:type,payload,seq,session_id:'session',stream_id:'stream',event_id:'run:'+seq
      },{session_id:'session',stream_id:'stream'});
    }
    add('tool',{name:'search',args:{query:'synthetic'},tool_call_id:'tool-1'},1);
    for(let i=0;i<50;i++)_renderLiveAnchorActivitySceneForStream('stream','session',{mode:'compact_worklog'});
    const hiddenProjects=projections;
    add('tool_complete',{name:'search',result:'complete',tool_call_id:'tool-1'},2);
    add('token',{text:'The complete answer'},3);
    const expected=api.projectAssistantTurnAnchorActivityScene(registry,{mode:'compact_worklog'});
    activeMode='compact_worklog';
    _renderLiveAnchorActivitySceneForStream('stream','session');
    const allPreserved=JSON.stringify(expected)===JSON.stringify(rendered[0]);
    activeMode='transparent_stream';
    _renderLiveAnchorActivitySceneForStream('stream','session');
    activeMode='hide_all_activity';
    _renderLiveAnchorActivitySceneForStream('stream','session');
    console.log(JSON.stringify({hiddenProjects,projections,allPreserved,modes:rendered.map(s=>s.mode),events:registry.anchor.activity_events.length}));
    '''.replace('PROJECT', function(UI, '_projectLiveAnchorActivitySceneForStream')).replace('RENDER', function(UI, '_renderLiveAnchorActivitySceneForStream'))
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {
        'hiddenProjects': 0, 'projections': 2, 'allPreserved': True,
        'modes': ['compact_worklog', 'transparent_stream'], 'events': 3,
    }
