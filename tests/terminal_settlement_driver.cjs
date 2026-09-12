// Provider-free lifecycle driver: real registry -> settlement -> native tool card.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(__dirname, '..');
const messagesSource = fs.readFileSync(path.join(root, 'static/messages.js'), 'utf8');
const uiSource = fs.readFileSync(path.join(root, 'static/ui.js'), 'utf8');
function extract(source, name) {
  const start = source.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('Missing function: ' + name);
  let at = source.indexOf('(', start), depth = 1;
  for (at++; depth && at < source.length; at++) {
    if (source[at] === '(') depth++;
    if (source[at] === ')') depth--;
  }
  at = source.indexOf('{', at); depth = 1;
  for (at++; depth && at < source.length; at++) {
    if (source[at] === '{') depth++;
    if (source[at] === '}') depth--;
  }
  return source.slice(start, at);
}
global.window = {chatActivityMode: () => 'transparent_stream'};
global.activeSid = 'fixture-session';
global.streamId = 'fixture-stream';
global.S = {toolCalls: [], session: {}};
vm.runInThisContext(fs.readFileSync(path.join(root, 'static/assistant_turn_anchors.js'), 'utf8'));
// This contiguous closure section contains the actual per-message builders,
// deduplication helpers and final settlement. No replacement merger is stubbed.
vm.runInThisContext(messagesSource.slice(
  messagesSource.indexOf('  function _anchorSceneMessageRef('),
  messagesSource.indexOf('  let _persistAnchorSceneWarned=')));
for (const name of ['_anchorSceneActiveMode', '_anchorSceneRowDisplayHintForMode']) {
  vm.runInThisContext(extract(messagesSource, name));
}
for (const name of ['_anchorSceneToolCallFromRow', '_toolResultIsError', '_toolResultErrorsByTid', 'buildToolCard']) {
  vm.runInThisContext(extract(uiSource, name));
}
// Cosmetic helpers are outside this regression. The actual card builder owns
// result presence, truncation, escaping calls and data-full output below.
global.esc = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
global.document = {createElement: () => ({dataset: {}, setAttribute() {}, removeAttribute() {}})};
for (const name of ['li', 'toolIcon', '_toolCardPreviewText', '_formatToolArgPreview']) global[name] = () => '';
for (const name of ['_isMemorySave', '_isSkillUpdate', '_snippetLooksLikeDiff']) global[name] = () => false;
global._toolActionKind = () => 'shell';
global._toolDisplayName = tc => tc.name;
global._toolActionLabelText = tc => tc.name;
global._toolDetailLeadText = (_kind, tc) => tc.args?.command || '';
global._toolDetailLeadLabel = () => 'Shell';
global._toolCardAllowsDetail = () => true;
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const p = JSON.parse(input);
  const api = window.HermesAssistantTurnAnchors;
  const registry = api.createAssistantTurnAnchorRegistry({session_id:activeSid, turn_id:'fixture-turn'});
  if (p.wire) {
    // Exact live callback normalization, including preview -> snippet and
    // explicit tid matching. Only DOM scheduling / localStorage writes skip.
    Object.assign(global, {_anchorRegistry:registry, _anchorApi:api, INFLIGHT:{},
      uploaded:[], assistantRow:null, _assistantSegmentSeq:1, _currentLiveSegmentSeq:1,
      _currentActivityBurstId:1, _renderAnchorLiveScene:()=>false,
      persistInflightState:()=>{}});
    S.messages = [];
    vm.runInThisContext(messagesSource.slice(messagesSource.indexOf('  function _stableStringify('),
      messagesSource.indexOf('  let _lastRenderMs=')));
    vm.runInThisContext(extract(messagesSource, '_applyToAnchor'));
    p.events.forEach((event, i) => {
      const {source_event_type:kind, ...payload} = event;
      const tc = kind === 'tool' || kind === 'tool_complete'
        ? upsertLiveToolCall(payload, kind === 'tool_complete' ? 'complete' : 'start') : {};
      _applyToAnchor(kind, {...payload, ...tc}, {lastEventId:`fixture-stream:${i+1}`});
    });
  } else {
    api.applyAssistantTurnAnchorSourceEvents(registry, p.events, {session_id:activeSid, stream_id:streamId});
  }
  let projected = api.projectAssistantTurnAnchorActivityScene(registry, {mode:p.mode || 'transparent_stream'});
  if (p.extraRows) projected = {...projected, activity_rows:[...projected.activity_rows, ...p.extraRows]};
  S.toolCalls = p.liveTools || [];
  const messages = p.messages || [{role:'user', content:'Run fixture'}, {role:'assistant', content:'Final answer'}];
  const before = JSON.stringify(projected);
  const scene = _completeSettledAnchorSceneForTurn(messages, messages.length - 1, projected);
  const cards = scene.activity_rows.filter(row => row.role === 'tool').map(row => {
    const tc = _anchorSceneToolCallFromRow(row, {settled:true});
    const card = buildToolCard(tc);
    return {row, tc, html:card.innerHTML};
  });
  process.stdout.write(JSON.stringify({projected, scene, cards, projectionUnchanged:JSON.stringify(projected) === before}));
});
