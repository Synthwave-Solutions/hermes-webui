const assert=require('node:assert/strict');
const {test,afterEach}=require('node:test');
const {SynPulseVoice}=require('../static/realtime_voice.js');
const cleanups=[];
afterEach(()=>{for(const v of cleanups.splice(0))v.stop();});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(overrides={}){
  const state={sid:'parent',outbound:[],tracks:[],peers:[],ended:[],transcripts:[],tasks:[],errors:[],approved:[],submitted:[]};
  const deps={
    current:()=>state.sid,status:()=>{},audio:()=>{},silence:()=>{},release:()=>{},
    error:e=>state.errors.push(e),transcript:entries=>state.transcripts=entries,tasks:entries=>state.tasks=entries,
    media:async()=>{const track={enabled:true,stopped:false,stop(){this.stopped=true;}};state.tracks.push(track);return {getTracks:()=>[track]};},
    peer:()=>{const dc={readyState:'open',send:value=>state.outbound.push(JSON.parse(value)),close(){this.closed=true;}};
      const pc={dc,addTrack(){},createDataChannel:()=>dc,createOffer:async()=>({sdp:'v=0'}),setLocalDescription:async()=>{},setRemoteDescription:async()=>{},close(){this.closed=true;}};
      state.peers.push(pc);return pc;},
    connect:async()=>({sdp:'v=0',voice_id:'voice-'+state.peers.length}),
    end:async id=>{state.ended.push(id);},
    approve:async body=>{state.approved.push(body);return {ok:true};},
    submit:body=>state.submitted.push(body),
    ...overrides,
  };
  const voice=new SynPulseVoice(deps);cleanups.push(voice);return {voice,state,deps};
}
test('native input/output captions dedupe without acknowledgement, chat submit or tool dispatch',async()=>{
  const {voice:v,state:s}=fixture();await v.start('parent');
  v.event({type:'conversation.item.input_audio_transcription.completed',item_id:'u1',transcript:'Hello'});
  v.event({type:'conversation.item.input_audio_transcription.completed',item_id:'u1',transcript:'Hello'});
  v.event({type:'response.output_audio_transcript.done',item_id:'a1',transcript:'Hello, how can I help?'});
  v.applySnapshot({transcript:[{id:'user:u1',role:'user',text:'Hello'},{id:'assistant:a1',role:'assistant',text:'Hello, how can I help?'}]});
  v.event({type:'response.function_call_arguments.done',call_id:'call1',name:'write_file',arguments:'{}'});
  v.event({type:'response.function_call_arguments.done',call_id:'call1',name:'write_file',arguments:'{}'});
  assert.deepEqual(s.transcripts.map(t=>[t.role,t.text]),[['user','Hello'],['assistant','Hello, how can I help?']]);
  assert.equal(s.submitted.length,0);assert.equal(s.outbound.length,0);assert.equal(s.approved.length,0);
});
test('generation completion never falsely declares buffered audio finished',async()=>{
  const {voice:v}=fixture();await v.start('parent');
  v.event({type:'response.created'});assert.equal(v.state,'thinking');
  v.event({type:'output_audio_buffer.started'});assert.equal(v.state,'speaking');
  v.event({type:'response.output_audio.done'});assert.equal(v.state,'speaking');
  v.event({type:'response.done',response:{status:'completed'}});assert.equal(v.state,'speaking');
  v.event({type:'output_audio_buffer.stopped'});assert.equal(v.state,'muted');
});
test('explicit microphone and interruption change tracks and audio without cancelling jobs',async()=>{
  const {voice:v,state:s}=fixture();await v.start('parent');assert.equal(s.tracks[0].enabled,false);
  v.applySnapshot({tasks:[{task_id:'job1',session_id:'child',status:'running'}]});
  v.mic(true);assert.equal(s.tracks[0].enabled,true);assert.equal(v.state,'listening');
  v.event({type:'input_audio_buffer.speech_started'});v.event({type:'input_audio_buffer.speech_stopped'});
  v.mic(false);assert.equal(s.tracks[0].enabled,false);
  v.interrupt();assert.deepEqual(s.outbound.slice(-2).map(e=>e.type),['response.cancel','output_audio_buffer.clear']);
  assert.equal(s.tasks[0].status,'running');assert.equal(s.ended.length,0);
});
test('background results and server transcript snapshots cannot inject extra speech',async()=>{
  const {voice:v,state:s}=fixture();await v.start('parent');
  v.event({type:'output_audio_buffer.started'});
  v.applySnapshot({transcript:[{id:'u1',role:'user',text:'Continue talking'}],tasks:[{task_id:'job',session_id:'child',status:'completed',result:'Task finished'}]});
  assert.equal(v.state,'speaking');assert.equal(s.outbound.length,0);assert.equal(s.tasks[0].result,'Task finished');assert.equal(s.peers[0].closed,undefined);
});
test('manual approval binds one request in child session and dedupes concurrent clicks',async()=>{
  let resolve;const {voice:v,state:s,deps:d}=fixture();d.approve=body=>{s.approved.push(body);return new Promise(r=>resolve=r);};
  await v.start('parent');v.applySnapshot({tasks:[{task_id:'job',session_id:'child',status:'approval',approval:{approval_id:'approval1',request_id:'request1'}}]});
  assert.equal(await v.approveTask('job','approval1','always'),false);
  assert.equal(await v.approveTask('job','old-approval','once'),false);
  const pending=v.approveTask('job','approval1','once');
  assert.equal(await v.approveTask('job','approval1','deny'),false);
  assert.deepEqual(s.approved,[{session_id:'child',approval_id:'approval1',request_id:'request1',choice:'once'}]);
  resolve({ok:true});assert.equal(await pending,true);
  assert.equal(await v.approveTask('job','approval1','once'),false);assert.equal(v.sid,'parent');assert.equal(s.peers[0].closed,undefined);
});
test('failed approval remains retryable and leaves voice available',async()=>{
  const {voice:v,state:s,deps:d}=fixture();d.approve=async()=>{throw Error('Denied by current policy');};
  await v.start('parent');v.applySnapshot({tasks:[{task_id:'job',session_id:'child',approval:{approval_id:'approval1'}}]});
  assert.equal(await v.approveTask('job','approval1','deny'),false);assert.equal(v.pendingApprovals.size,0);assert.equal(v.resolvedApprovals.size,0);
  assert.equal(s.errors.at(-1),'Denied by current policy');assert.equal(v.sid,'parent');
});
test('ending voice closes only its voice ID and releases peer and microphone once',async()=>{
  const {voice:v,state:s}=fixture();await v.start('parent');
  v.stop();v.stop();await tick();
  assert.deepEqual(s.ended,['voice-1']);assert.equal(s.peers[0].closed,true);assert.equal(s.tracks[0].stopped,true);
  assert.equal(v.state,'off');assert.equal(s.approved.length,0);
});
test('late allocated call after navigation is explicitly ended',async()=>{
  let resolve;const {voice:v,state:s,deps:d}=fixture();d.connect=()=>new Promise(r=>resolve=r);
  const pending=v.start('parent');await tick();s.sid='other';v.stop();
  resolve({sdp:'v=0',voice_id:'late-voice'});await pending;await tick();
  assert.deepEqual(s.ended,['late-voice']);assert.equal(s.tracks[0].stopped,true);assert.equal(v.state,'off');
});
test('late microphone permission completion stops acquired track after cancellation',async()=>{
  let resolve;const {voice:v,state:s,deps:d}=fixture();d.media=()=>new Promise(r=>resolve=r);
  const pending=v.start('parent');v.stop();
  const track={enabled:true,stopped:false,stop(){this.stopped=true;}};resolve({getTracks:()=>[track]});await pending;
  assert.equal(track.stopped,true);assert.equal(v.state,'off');assert.equal(s.peers.length,0);
});
test('old peer callbacks and status snapshots cannot contaminate a replacement call',async()=>{
  const {voice:v,state:s,deps:d}=fixture();let resolve;d.snapshot=()=>new Promise(r=>resolve=r);
  await v.start('parent');const old=s.peers[0],message=old.dc.onmessage,resolveOld=resolve;
  s.sid='new';await v.start('new');
  message({data:JSON.stringify({type:'conversation.item.input_audio_transcription.completed',item_id:'private-old',transcript:'Old private text'})});
  resolveOld({voice_id:'voice-1',session_id:'parent',tasks:[{task_id:'old',status:'running'}]});await tick();
  assert.equal(v.sid,'new');assert.deepEqual(s.transcripts,[]);assert.deepEqual(s.tasks,[]);
});
test('missing managed voice ID fails closed and transport failure releases resources',async()=>{
  const {voice:v,state:s,deps:d}=fixture();d.connect=async()=>({sdp:'v=0'});await v.start('parent');
  assert.equal(v.state,'off');assert.match(s.errors.at(-1),/managed conversation/);assert.equal(s.tracks[0].stopped,true);
  d.connect=async()=>({sdp:'v=0',voice_id:'managed'});await v.start('parent');const pc=s.peers.at(-1);
  pc.connectionState='failed';pc.onconnectionstatechange();await tick();
  assert.equal(v.state,'off');assert.deepEqual(s.ended,['managed']);assert.match(s.errors.at(-1),/connection lost/i);
});
for(const status of [401,403,404])test('status '+status+' stops capture immediately after authority ends',async()=>{
  const {voice:v,state:s,deps:d}=fixture();d.snapshot=async()=>{throw Object.assign(Error('Unavailable'),{status});};
  await v.start('parent');await tick();
  assert.equal(v.state,'off');assert.equal(s.tracks[0].stopped,true);assert.deepEqual(s.ended,[]);
  assert.match(s.errors.at(-1),/access ended or was revoked/);assert.equal(v.pollTimer,null);
});
for(const data of [{voice_id:'other'},{session_id:'other'}])test('mismatched status cannot keep recording or populate another conversation',async()=>{
  const {voice:v,state:s,deps:d}=fixture();d.snapshot=async()=>({...data,transcript:[{id:'foreign',role:'user',text:'Foreign private caption'}]});
  await v.start('parent');await tick();assert.equal(v.state,'off');assert.equal(s.tracks[0].stopped,true);
  assert.deepEqual(s.transcripts,[]);assert.match(s.errors.at(-1),/another conversation/);
});
test('a transient status failure warns without losing a healthy native conversation',async()=>{
  const warnings=[];const {voice:v,state:s,deps:d}=fixture({connectionWarning:value=>warnings.push(value)});
  d.snapshot=async()=>{throw Object.assign(Error('Temporary upstream failure'),{status:502});};
  await v.start('parent');await tick();assert.equal(v.state,'muted');assert.equal(s.tracks[0].stopped,false);
  assert.equal(warnings.length,1);assert.ok(v.pollTimer);
});
