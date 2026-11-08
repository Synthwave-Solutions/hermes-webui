// Teamwerk dock (static/subagent-threads.js) with the real friendly module:
// bot photos instead of a robot emoji, plain statuses, handoff rows, folding.
const assert=require('node:assert/strict');
const ft=require('../static/tool-friendly.js');
ft.setLanguage('nl');
const dock={hidden:true,innerHTML:''};
global.document={hidden:false,getElementById:()=>dock};
global.SynPulseFriendlyTools=ft;
global.groupRouting={botInfo:id=>({
  'linus-research':{known:true,title:'Linus',avatar_url:'/api/profile/avatar?profile=linus-research'},
  'sanne-sales':{known:true,title:'Sanne',avatar_url:''},
  'grace-ops':{known:true,title:'Grace',avatar_url:''},
})[id]||null};
let rows=[
  {id:'bot:1',kind:'specialist',bot_profile:'linus-research',bot_title:'linus-research',from_profile:'sanne-sales',task:'Check quotes',status:'running',child_session_id:'abcdef123456',queue_authoritative:true,steps:[],started_at:1,updated_at:2},
  {id:'handoff:2',kind:'handoff',bot_profile:'grace-ops',bot_title:'Grace',from_profile:'sanne-sales',from_title:'Sanne',task:'Take over the reply',status:'queued',child_session_id:'',queue_authoritative:true,steps:[],started_at:3,updated_at:3},
  {id:'bot:3',kind:'specialist',bot_profile:'grace-ops',bot_title:'Grace',task:'Old work',status:'completed',child_session_id:'123456abcdef',queue_authoritative:true,steps:[],started_at:0,updated_at:1,duration_seconds:12},
];
global.api=async()=>({subagents:rows});
const ui=require('../static/subagent-threads.js');
ui._switchTo('parent');
setImmediate(async()=>{
  const html=dock.innerHTML;
  assert.equal(dock.hidden,false);
  assert.ok(!html.includes('\u{1F916}'),'no robot emoji');
  assert.match(html,/sp-subagent-dock-title">Teamwerk \(3\)/);
  assert.match(html,/1 aan het werk/);
  assert.match(html,/1 klaar/);
  assert.match(html,/1 wacht/);
  assert.match(html,/<span class="sp-subagent-status">Aan het werk<\/span>/);
  assert.match(html,/<span class="sp-subagent-status">Neemt het over na Sanne<\/span>/);
  assert.match(html,/<span class="sp-subagent-status">Klaar<\/span>/);
  // Photo when the catalog has one, initial otherwise; the catalog title wins over an id-like title.
  assert.match(html,/src="\/api\/profile\/avatar\?profile=linus-research"/);
  assert.match(html,/sp-subagent-who">Linus</);
  assert.match(html,/sp-bot-avatar-initial">G</);
  assert.match(html,/Bekijk het werk van Linus/);
  const text=html.replace(/<[^>]*>/g,'');
  for(const id of ['linus-research','sanne-sales','grace-ops']) assert.ok(!text.includes(id),id);
  // Something is still running, so the list is open.
  assert.match(html,/<div class="sp-subagent-list">/);

  // Everything finished: the strip folds by itself.
  rows=rows.map(r=>({...r,status:'completed',duration_seconds:5}));
  await ui.refresh();
  assert.match(dock.innerHTML,/<div class="sp-subagent-list" hidden>/);
  assert.match(dock.innerHTML,/3 klaar/);
  assert.ok(!dock.innerHTML.includes('aan het werk'));

  // Handoff calls of a turn, read from stored messages (OpenAI and block form).
  const calls=ui._turnHandoffs([
    {role:'user',content:'Vraag'},
    {role:'assistant',bot_profile:'sanne-sales',tool_calls:[
      {id:'c1',function:{name:'delegate_to_bot',arguments:'{"action":"delegate","bot":"linus-research","task":"Check"}'}},
      {id:'c2',function:{name:'read_file',arguments:'{}'}}]},
    {role:'tool',tool_call_id:'c1',content:'{"status":"queued"}'},
    {role:'assistant',content:[{type:'tool_use',id:'c3',name:'delegate_to_bot',input:{action:'list'}}]},
    {role:'user',content:[{type:'tool_result',tool_use_id:'c3',content:'{"bots":[]}'}]},
    {role:'assistant',tool_calls:[{id:'c9',function:{name:'delegate_to_bot',arguments:'{}'}}]},
  ],1);
  assert.deepEqual(calls.map(c=>[c.key,c.args.action||'',c.result]),[['c1','delegate','{"status":"queued"}'],['c3','list','']]);
  console.log('ok');
});
