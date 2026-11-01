const {test}=require('node:test');const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
const builder=fs.readFileSync('static/bot-builder.js','utf8');
const panels=fs.readFileSync('static/panels.js','utf8');
const mount=builder.slice(builder.indexOf('  async function mountAutomation(){'),builder.indexOf('  async function assignScheduledTaskToBot'));
function harness(admin=true,step=6){
 const box={innerHTML:''},nodes={builderAutomation:box,builderAssignTask:{},builderCreateTask:{}};
 const calls=[],p={name:'reviewer',scout_manageable:admin,bot:{scout:{topics:['Planning']}}};
 const context={esc:value=>String(value),tr:(key,fallback)=>fallback,state:{edit:true,step,config:{name:'reviewer',system_prompt:'unsaved instructions'}},input:id=>nodes[id],_currentProfileDetail:null,_botScoutTopics:[],
  api:async(url,opts)=>{calls.push([url,opts]);return url.includes('/profiles')?{profiles:[p]}:{people:[{email:'colleague@example.test',enabled:false}]};},
  _botScoutCardHtml:profile=>{assert.equal(profile,p);return JSON.stringify(profile.scout_people_options||[]);},_paintBotScoutTopics(){},
  _loadProfileBotJobs:async profile=>calls.push(['jobs',profile.name]),assignScheduledTaskToBot:profile=>calls.push(['assign',profile.name]),
  collect(){},openCronCreate:name=>calls.push(['create',name])};
 vm.createContext(context);vm.runInContext(mount,context);
 return {context,calls,p,box,nodes};
}
test('admin Scout tab loads eligible people automatically and preserves bot draft',async()=>{
 const h=harness();await h.context.mountAutomation();
 assert.equal(h.calls.length,2);assert.deepEqual(JSON.parse(h.calls[1][1].body),{name:'reviewer',action:'people'});
 assert.match(h.box.innerHTML,/colleague@example.test/);assert.equal(h.context.state.config.system_prompt,'unsaved instructions');
});
test('directory failure still renders the personal Scout form for retry',async()=>{
 const h=harness();const api=h.context.api;
 h.context.api=(url,options)=>url.includes('/api/bots/scout')?Promise.reject(new Error('offline')):api(url,options);
 await h.context.mountAutomation();
 assert.equal(h.p.scout_people_error,true);assert.equal(h.box.innerHTML,'[]');
});
test('non-manager does not request another user directory',async()=>{
 const h=harness(false);await h.context.mountAutomation();assert.equal(h.calls.length,1);
});
test('late bot response cannot overwrite a newly selected editor tab',async()=>{
 const h=harness();let finish;h.context.api=()=>new Promise(resolve=>{finish=resolve;});
 const pending=h.context.mountAutomation();h.context.state={step:0,config:{name:'different'}};
 finish({profiles:[h.p]});await pending;assert.equal(h.box.innerHTML,'');
});
test('tasks tab reuses assignment and create with the edited bot, not active chat bot',async()=>{
 const h=harness(true,7);await h.context.mountAutomation();h.nodes.builderAssignTask.onclick();h.nodes.builderCreateTask.onclick();
 assert.deepEqual(h.calls.slice(1),[['jobs','reviewer'],['assign','reviewer'],['create','reviewer']]);
});
test('Scout save updates its revision in place and keeps other drafts',async()=>{
 const src=panels.slice(panels.indexOf('async function _postBotScout('),panels.indexOf('// Explicit save/activate/pause:'));
 const calls=[],p={name:'reviewer',bot_revision:4};
 const view={busy:false,drafts:new Map([['colleague@example.test',{prompt:'saved'}],['other@example.test',{prompt:'keep'}]])};
 const card={isConnected:true,setAttribute(){}},nodes={botScoutControls:{},botScoutError:{},botScoutStatus:{},botScoutSave:{focus(){}}};
 const context={document:{querySelector:()=>card},$:id=>nodes[id],t:x=>x,_currentProfileDetail:p,_botScoutState:()=>view,
  api:async(url,opts)=>{calls.push(JSON.parse(opts.body));return {bot_revision:5};},_profileDropdownClearStoredCache(){},CustomEvent:class{},
  window:{dispatchEvent(){}},_refreshBotScoutCard:()=>calls.push('refresh')};
 vm.createContext(context);vm.runInContext(src,context);
 await context._postBotScout(p,{person:'colleague@example.test',enabled:true},'Saved');
 assert.equal(calls[0].person,'colleague@example.test');assert.equal(calls[0].revision,4);
 assert.equal(p.bot_revision,5);assert.equal(calls[1],'refresh');assert.equal(view.busy,false);
 assert.equal(view.drafts.has('colleague@example.test'),false);assert.equal(view.drafts.get('other@example.test').prompt,'keep');
});

test('editor labels remain readable when an older locale returns missing keys',()=>{
 const start=builder.indexOf('  const tr=');const end=builder.indexOf('\n',start);
 const context={t:key=>key};vm.createContext(context);
 vm.runInContext(builder.slice(start,end)+"\nresult=tr('bot_editor_assign_title','Assign scheduled task');",context);
 assert.equal(context.result,'Assign scheduled task');
});
