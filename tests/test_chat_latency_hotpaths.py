"""Execute production browser hot paths; delays/counters are deterministic."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = (ROOT / 'static/messages.js').read_text()
UI = (ROOT / 'static/ui.js').read_text()


def function(source, name):
    start = source.index('function ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for i in range(brace, len(source)):
        depth += (source[i] == '{') - (source[i] == '}')
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError(name)


def node(script):
    result = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def test_first_send_never_waits_for_sidebar_network():
    # Execute each actual session-creation gate in send, with an unresolved
    # sidebar response. Session creation itself must still finish first.
    gates = re.findall(r'if\(!S.session\)\{await newSession\(\);[^}]*\}', MESSAGES)
    assert gates
    result = node('''
      const gates=GATES;
      (async()=>{const results=[];for(const gate of gates){
        const S={session:null};let created=false,refreshes=0;
        const newSession=async()=>{await Promise.resolve();S.session={session_id:'new'};created=true;};
        const renderSessionList=()=>{refreshes++;return new Promise(()=>{});};
        const send=new Function('S','newSession','renderSessionList','return (async()=>{'+gate+';return !!S.session})()');
        const ready=await Promise.race([send(S,newSession,renderSessionList),new Promise(r=>setTimeout(()=>r(false),20))]);
        results.push({ready,created,refreshes});
      }console.log(JSON.stringify(results));})();
    '''.replace('GATES', json.dumps(gates)))
    assert all(r['ready'] and r['created'] and r['refreshes'] == 0 for r in result), result


def test_unchanged_thinking_preserves_text_node():
    result = node(function(UI, '_renderThinkingInto') + '''
      let writes=0;const pre={_text:'reasoning',get textContent(){return this._text},set textContent(v){writes++;this._text=v;}};
      const row={querySelector:()=>pre};
      function _sanitizeThinkingDisplayText(t){return t.trim();}
      for(let i=0;i<120;i++) _renderThinkingInto(row,'reasoning');
      const unchanged=writes;
      _renderThinkingInto(row,'new reasoning');
      console.log(JSON.stringify({unchanged,writes,text:pre.textContent}));
    ''')
    assert result == {'unchanged': 0, 'writes': 1, 'text': 'new reasoning'}


def test_animation_frames_reuse_parse_until_content_or_reasoning_changes():
    result = node('''
      let assistantText='answer',liveReasoningText='reason',_cachedParsed=null,_cachedParsedText='',_cachedParsedReasoning='';
      let _renderPending=false,_streamFinalized=false,_lastRenderMs=0,_pendingRafHandle=null;
      let parses=0,frames=[],segmentStart=0,assistantBody=null;
      const window={};const performance={now:()=>10000};
      const requestAnimationFrame=fn=>{frames.push(fn);return frames.length};
      const setTimeout=fn=>{frames.push(fn);return frames.length};
      function _shouldUseLiveProseFade(){return true;}
      function _parseStreamState(){parses++;return {displayText:assistantText,thinkingText:liveReasoningText};}
      function _renderLiveThinking(){} function _upsertAnchorProcessProse(){}
      function scrollIfPinned(){} function _throttledSnapshotLiveTurn(){}
      FUNCTION
      function frame(){_scheduleRender();while(frames.length)frames.shift()();}
      for(let i=0;i<100;i++)frame();const repeated=parses;
      assistantText+=' next';frame();const afterText=parses;
      liveReasoningText+=' next';frame();const afterReason=parses;
      assistantText='replacement';frame();const afterReplace=parses;
      _streamFinalized=true;frame();
      console.log(JSON.stringify({repeated,afterText,afterReason,afterReplace,final:parses}));
    '''.replace('FUNCTION', function(MESSAGES, '_scheduleRender')))
    assert result == {'repeated': 1, 'afterText': 2, 'afterReason': 3, 'afterReplace': 4, 'final': 4}


def test_display_filter_preserves_plain_text_and_strips_tool_xml():
    result = node(function(UI, '_stripXmlToolCallsDisplay') + '''
      console.log(JSON.stringify([
        _stripXmlToolCallsDisplay('Plain TEXT with spaces  '),
        _stripXmlToolCallsDisplay('Before <FUNCTION_CALLS>secret</FUNCTION_CALLS> after'),
        _stripXmlToolCallsDisplay('Before <function_calls>unfinished'),
        _stripXmlToolCallsDisplay('Before <｜DSML｜function_calls>secret</｜DSML｜function_calls> after'),
        _stripXmlToolCallsDisplay('A function_calls label is ordinary text')
      ]));
    ''')
    assert result == ['Plain TEXT with spaces  ', 'Before  after', 'Before', 'Before  after', 'A function_calls label is ordinary text']
