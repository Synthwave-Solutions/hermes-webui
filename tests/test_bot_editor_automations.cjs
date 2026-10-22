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
test('Scout save refreshes inside editor without losing selected user',async()=>{
 const src=panels.slice(panels.indexOf('async function _postBotScout('),panels.indexOf('// The caller\'s own Scout:'));
 const calls=[];const selected={bot:'reviewer',person:'colleague@example.test'};
 const context={api:async(url,opts)=>calls.push(JSON.parse(opts.body)),_profileDropdownClearStoredCache(){},CustomEvent:class{},
  window:{dispatchEvent(){},BotBuilder:{isEditing:()=>true,refreshAutomation:async()=>calls.push('refresh')}},
  _botScoutSelected:selected,loadProfilesPanel(){throw Error('Editor must not close');},showToast(){}};
 vm.createContext(context);vm.runInContext(src,context);
 await context._postBotScout({name:'reviewer',bot_revision:4},{person:selected.person,enabled:true},'Saved');
 assert.equal(calls[0].person,selected.person);assert.equal(calls[1],'refresh');assert.equal(context._botScoutSelected,selected);
});


test('editor labels remain readable when an older locale returns missing keys',()=>{
 const start=builder.indexOf('  const tr=');const end=builder.indexOf('\n',start);
 const context={t:key=>key};vm.createContext(context);
 vm.runInContext(builder.slice(start,end)+"\nresult=tr('bot_editor_assign_title','Assign scheduled task');",context);
 assert.equal(context.result,'Assign scheduled task');
});
