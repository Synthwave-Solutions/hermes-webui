// Bot teamwork copy in static/tool-friendly.js: the handoff line, the helper
// credit and the names. Runs the real module in Node with a stub catalog.
const assert=require('node:assert/strict');
const ft=require('../static/tool-friendly.js');

const catalog={
  'sanne-sales':{known:true,title:'Sanne',avatar_url:'/api/profile/avatar?profile=sanne-sales'},
  'linus-research':{known:true,title:'Linus',avatar_url:''},
};
globalThis.groupRouting={botInfo:id=>catalog[id]||null,workingState:()=>null};
globalThis.S={
  session:{session_id:'s1',profile:'sanne-sales'},
  messages:[
    {role:'user',content:'Zoek dit uit'},
    {role:'assistant',content:'',bot_profile:'sanne-sales',bot_name:'Sanne'},
  ],
};

const call=(args,extra)=>({name:'delegate_to_bot',args,assistant_msg_idx:1,done:true,...extra});
const queued=call({action:'delegate',bot:'linus-research',task:'Check the three supplier quotes   and list the cheapest'},
  {snippet:JSON.stringify({status:'queued',mode:'background',bot:'linus-research',session_id:'abcdef123456'})});

ft.setLanguage('nl');
assert.equal(ft.family(queued),'handoff');
let d=ft.describe(queued);
assert.equal(d.family,'handoff');
assert.equal(d.title,'Sanne heeft Linus gevraagd');
assert.equal(d.target,'Check the three supplier quotes and list the cheapest');
assert.equal(d.detailsLabel,'Bekijk de opdracht');
assert.equal(d.state,'done');
assert.match(d.iconHtml,/sp-handoff-avatars/);
// Sanne has a photo; Linus is known without one, so no request is made for him.
assert.match(d.iconHtml,/src="\/api\/profile\/avatar\?profile=sanne-sales"/);
assert.ok(!d.iconHtml.includes('profile=linus-research'));
assert.match(d.iconHtml,/sp-bot-avatar-initial">L</);

const running=call({action:'delegate',bot:'linus-research',task:'x'},{done:false});
assert.equal(ft.describe(running).title,'Sanne geeft dit door aan Linus…');
assert.equal(ft.describe(running).state,'running');
assert.equal(ft.describe(call({action:'delegate',mode:'handoff',bot:'linus-research',task:'Neem over'},
  {snippet:'{"status":"queued","bot":"linus-research"}'})).title,'Linus neemt het hierna over in dit gesprek');
assert.equal(ft.describe(call({action:'list'},{snippet:'{"bots":["linus-research"]}'})).title,'Sanne keek wie kan helpen');
const denied=ft.describe(call({action:'delegate',bot:'linus-research',task:'x'},
  {snippet:'{"error": "Choose another authorized bot from action=list"}'}));
assert.equal(denied.title,'Niet doorgegeven: Linus is niet beschikbaar voor jou');
assert.equal(denied.state,'failed');
assert.equal(ft.describe(call({action:'delegate',bot:'linus-research',task:'x'},
  {snippet:'{"error": "This chain has reached four handoffs. Report back to the user"}'})).title,
  'Maximaal vier keer doorgeven bereikt');
// A shortened result still yields the plain error.
assert.equal(ft.describe(call({action:'delegate',bot:'linus-research',task:'x'},
  {snippet:'{"error": "Choose another authorized bot from action=list and then some text that was cut'})).state,'failed');

// The visible line: one sentence, both avatars, the task behind a disclosure.
const line=ft.bots.handoffLineHtml(queued);
assert.match(line,/^<details class="sp-handoff-line" data-kind="queued"/);
assert.match(line,/Sanne heeft Linus gevraagd: Check the three supplier quotes and list the cheapest/);
assert.match(line,/<span class="sp-handoff-more">Bekijk de opdracht<\/span>/);
const visible=line.replace(/<[^>]+>/g,' ').replace(/title="[^"]*"/g,'');
assert.ok(!/sanne-sales|linus-research/.test(visible.replace(/\s+/g,' ').split('Bekijk de opdracht')[0].replace(/@\S+/g,'')),visible);
// Profile names only in the tooltip (as @handles) and image URL, never as text.
const textOnly=line.replace(/<[^>]*>/g,'');
assert.ok(!textOnly.includes('sanne-sales')&&!textOnly.includes('linus-research'),textOnly);
assert.ok(!/🤖/.test(line));
// Hostile task text is escaped.
const hostile=ft.bots.handoffLineHtml(call({action:'delegate',bot:'linus-research',task:'<img src=x onerror=alert(1)>'},{snippet:'{"status":"queued"}'}));
assert.ok(!hostile.includes('<img src=x'));
assert.match(hostile,/&lt;img src=x onerror=alert\(1\)&gt;/);

// Names: catalog title, then the stamped bot name, then a readable form.
assert.equal(ft.bots.name('sanne-sales'),'Sanne');
assert.equal(ft.bots.name('grace-ops'),'Grace ops');
S.messages.push({role:'assistant',content:'hoi',bot_profile:'grace-ops',bot_name:'Grace'});
assert.equal(ft.bots.name('grace-ops'),'Grace');
assert.equal(ft.bots.name(''),'een andere bot');
assert.equal(ft.bots.joinNames(['Linus']),'Linus');
assert.equal(ft.bots.joinNames(['Linus','Grace']),'Linus en Grace');
assert.equal(ft.bots.joinNames(['Linus','Grace','Ada']),'Linus, Grace en Ada');
// Unknown ids that are not plain profile names never become an avatar URL.
assert.ok(!ft.bots.avatarHtml('../etc/passwd','X').includes('<img'));

// Helper credit: only the bot_delegation results directly before the reply.
const transcript=[
  {role:'user',content:'Vraag'},
  {role:'assistant',content:'Ik vraag Linus',bot_profile:'sanne-sales'},
  {role:'user',_source:'process_wakeup',bot_delegation:{from:'linus-research',to:'sanne-sales',result:true}},
  {role:'user',_source:'process_wakeup',bot_delegation:{from:'grace-ops',to:'sanne-sales',result:true}},
  {role:'assistant',content:'Linus zegt: met hulp van Ada', bot_profile:'sanne-sales'},
  {role:'user',content:'Linus is klaar, toch?'},
  {role:'assistant',content:'Ja'},
];
assert.deepEqual(ft.bots.assistedBy(transcript,4),['linus-research','grace-ops']);
assert.deepEqual(ft.bots.assistedBy(transcript,6),[],'text that mentions a bot is never a credit');
assert.deepEqual(ft.bots.assistedBy(transcript,1),[]);
assert.deepEqual(ft.bots.assistedBy([{role:'user',bot_delegation:{from:'x',to:'y'}},{role:'assistant'}],1),[],
  'a task handed to a bot is not a result');

ft.setLanguage('en');
assert.equal(ft.describe(queued).title,'Sanne asked Linus');
assert.equal(ft.describe(running).title,'Sanne is handing this to Linus…');
assert.equal(ft.bots.joinNames(['Linus','Grace']),'Linus and Grace');
assert.equal(ft.text('subagents_title'),'Teamwork');
ft.setLanguage('nl');
assert.equal(ft.text('subagents_title'),'Teamwerk');
assert.equal(ft.emojiFor('subagent'),'👥');
assert.match(ft.groupSummary([ft.describe(queued)]).text,/↪ 1/);

// Every new string exists in both languages, without long dashes.
const src=require('node:fs').readFileSync(require.resolve('../static/tool-friendly.js'),'utf8');
assert.ok(!new RegExp('[\\u2013\\u2014]').test(src));
for(const key of ['handoff_running','handoff_asked','handoff_takeover','handoff_list','handoff_not_available','handoff_limit',
  'handoff_view_task','team_status_queued','team_status_queued_handoff','team_status_running','team_status_done',
  'team_status_failed','team_status_stopped','team_count_running','team_count_done','open_work']){
  ft.setLanguage('nl'); const nl=ft.text(key);
  ft.setLanguage('en'); const en=ft.text(key);
  assert.ok(nl&&en&&nl!==key&&en!==key&&nl!==en,key);
}
console.log('ok');
