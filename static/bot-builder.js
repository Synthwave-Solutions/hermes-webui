/* Guided bot setup: draft-only until the final atomic save. */
(function(){
  'use strict';
  let state=null, epoch=0;
  const tr=(key,fallback)=>{const value=typeof t==='function'?t(key):null;return value&&value!==key?value:fallback;};
  function input(id){return document.getElementById(id);}
  const tabLayout=window.matchMedia?.('(min-width:1100px)');
  function orientTabs(){
    const tabs=document.querySelector('.bot-builder-tabs');
    if(tabs)tabs.setAttribute('aria-orientation',tabLayout?.matches?'vertical':'horizontal');
  }
  tabLayout?.addEventListener('change',orientTabs);
  async function readAvatar(file){
    if(!file || !['image/png','image/jpeg','image/webp'].includes(file.type))
      throw new Error('Choose a PNG, JPEG or WebP image.');
    if(file.size>10*1024*1024)throw new Error('Choose an image smaller than 10 MB.');
    const url=URL.createObjectURL(file);
    try{
      const image=new Image();
      await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('This image could not be opened. Try another PNG or JPEG.'));image.src=url;});
      if(!image.naturalWidth||!image.naturalHeight||image.naturalWidth*image.naturalHeight>40000000)
        throw new Error('Choose an image smaller than 40 megapixels.');
      const ratio=Math.min(1,512/image.naturalWidth,512/image.naturalHeight);
      const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.naturalWidth*ratio));canvas.height=Math.max(1,Math.round(image.naturalHeight*ratio));
      canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
      return canvas.toDataURL('image/png');
    }finally{URL.revokeObjectURL(url);}
  }
  window.readBotAvatarFile=readAvatar;

  function field(label,id,value='',multi=false){
    return '<label class="bot-builder-field" for="'+id+'">'+esc(label)+(multi?
      '<textarea id="'+id+'" rows="8">'+esc(value)+'</textarea>':
      '<input id="'+id+'" value="'+esc(value)+'" autocomplete="off">')+'</label>';
  }
  function choices(label,key,rows){
    const chosen=state.config[key]||[];
    rows=[...(rows||[])];
    const available=new Set(rows.map(row=>row.name||row.email));
    for(const value of chosen)if(!available.has(value))rows.push({name:value,description:tr('bot_editor_unavailable_selection',"Previously selected; currently unavailable. Remove this selection to save.")});
    return '<fieldset class="bot-builder-options"><legend>'+esc(label)+'</legend>'+
      '<input type="search" data-filter="'+key+'" aria-label="Filter '+esc(label)+'" placeholder="Filter '+esc(label.toLowerCase())+'">'+
      '<div class="bot-builder-choice-list">'+(rows||[]).map(row=>{
        const value=row.name||row.email;
        return '<label data-choice="'+key+'"><input type="checkbox" data-selection="'+key+'" value="'+esc(value)+'" '+(chosen.includes(value)?'checked':'')+'><span>'+esc(value)+(row.description?'<small>'+esc(row.description)+'</small>':'')+'</span></label>';
      }).join('')+'</div>'+(!(rows||[]).length?'<p>No available options for your account.</p>':'')+'</fieldset>';
  }
  function collect(){
    if(!state)return;
    const c=state.config;
    for(const [id,key] of [['builderName','name'],['builderTitle','title'],['builderDescription','description'],['builderPrompt','system_prompt'],['builderMemory','bot_memory']]){
      if(input(id))c[key]=input(id).value;
    }
    for(const key of ['skills','mcp_servers','cli_tools','allowed_users','allowed_groups']){
      if(document.querySelector('[data-filter="'+key+'"]'))
        c[key]=[...document.querySelectorAll('[data-selection="'+key+'"]:checked')].map(el=>el.value);
    }
  }
  function validate(){
    collect();
    const c=state.config;
    if(state.edit||state.step===0){
      c.name=(c.name||'').trim().toLowerCase();
      if(!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(c.name))throw new Error('Use a bot ID with lowercase letters, numbers, hyphens or underscores.');
      if(!(c.title||'').trim())throw new Error('Give your bot a display name.');
    }
    if((state.edit||state.step===1)&&!(c.system_prompt||'').trim())throw new Error('Describe the bot’s role and instructions before continuing.');
  }
  function error(message){
    const el=input('builderError');if(el){el.textContent=message;el.hidden=false;}
  }
  function render(){
    const body=input('profileDetailBody');if(!body||!state)return;
    const {config:c,catalog:cat,step}=state;
    input('profileDetailTitle').textContent=state.edit?(c.title||c.name)+' · '+tr('bot_setup_edit','Edit bot'):tr('bot_setup_create','Create a bot');
    input('profileDetailEmpty').style.display='none';body.style.display='';
    _profileMode='create';_setProfileHeaderButtons('create');
    const headerSave=input('btnSaveProfileDetail');if(headerSave)headerSave.style.display='none';
    let content='';
    if(step===0){
      content=field(tr('bot_setup_id','Bot ID'),'builderName',c.name)+field(tr('bot_setup_name','Display name'),'builderTitle',c.title)+
        field(tr('bot_setup_description','What does this bot help with?'),'builderDescription',c.description,true)+
        '<label class="bot-builder-field">'+esc(tr('bot_setup_photo','Profile photo'))+'<input id="builderPhoto" type="file" accept="image/png,image/jpeg,image/webp"></label>'+
        '<p>'+esc(tr('bot_setup_photo_hint','PNG, JPEG or WebP up to 10 MB. Resized before saving.'))+'</p>'+
        ((state.avatar||c.avatar_url)?'<img class="bot-builder-photo" src="'+esc(state.avatar||c.avatar_url)+'" alt="'+esc(tr('bot_setup_photo_preview','Bot photo preview'))+'">':'');
    }else if(step===1){
      content=field(tr('bot_editor_instructions','Instructions'),'builderPrompt',c.system_prompt,true)+
        (state.edit?'':choices('Skills','skills',cat.skills));
    }else if(step===2){
      content=choices(tr('bot_setup_connections','Tool connections'),'mcp_servers',cat.mcp_servers)+choices(tr('bot_setup_cli','Command-line tools'),'cli_tools',cat.cli_tools)+
        '<p>Model: <strong>'+esc(c.default_model||tr('bot_setup_default','Configured default'))+'</strong> '+esc(c.model_provider||'')+'</p>';
    }else if(step===4){
      content=field(tr('bot_editor_memory',"Bot memory"),'builderMemory',c.bot_memory||'',true)+
        '<p>'+esc(tr('bot_editor_memory_hint',"Shared with the users of this bot. Separate from My Notes and your personal user profile."))+'</p>'+
        '<p>'+esc(tr('bot_editor_knowledge_hint',"File selections are saved separately using Save knowledge below."))+'</p><div id="builderKnowledge"></div>';
    }else if(state.edit&&(step===6||step===7)){
      content='<div id="builderAutomation" aria-live="polite">'+esc(tr('loading','Loading…'))+'</div>';
    }else if(step===5){
      content=choices('Skills','skills',cat.skills);
    }else{
      content=choices(tr('bot_setup_users','Allowed users'),'allowed_users',cat.users)+choices(tr('bot_setup_groups','Allowed groups'),'allowed_groups',cat.groups)+
        '<h3>'+esc(tr('bot_setup_review','Review before saving'))+'</h3><dl class="bot-builder-review">'+
        [['Bot',c.title+' (@'+c.name+')'],[tr('bot_editor_instructions','Instructions'),c.system_prompt],['Skills',(c.skills||[]).join(', ')||tr('bot_setup_none','None selected')],[tr('bot_setup_connections','Tool connections'),(c.mcp_servers||[]).join(', ')||tr('bot_setup_none','None selected')],[tr('bot_setup_cli','Command-line tools'),(c.cli_tools||[]).join(', ')||tr('bot_setup_none','None selected')]].map(([a,b])=>'<dt>'+esc(a)+'</dt><dd>'+esc(b)+'</dd>').join('')+'</dl>'+
        '<p>'+esc(tr('bot_setup_review_hint','The bot becomes available after its configuration and access have been checked.'))+'</p>';
    }
    const sections=[[0,tr('bot_editor_identity',"Identity & photo")],[1,tr('bot_editor_instructions',"Instructions")],[4,tr('bot_editor_memory_tab',"Memory & knowledge")],[5,tr('bot_editor_skills',"Skills")],[2,tr('bot_editor_connections',"Connections & tools")],[3,tr('bot_editor_access',"Access")],[6,tr('bot_scout',"Scout")],[7,tr('bot_editor_tasks','Scheduled tasks')]];
    const createSteps=[sections[0][1],tr('bot_setup_instructions_skills','Instructions & skills'),sections[4][1],tr('bot_setup_access_review','Access & review')];
    const navigation=state.edit?'<div class="bot-builder-tabs" role="tablist" aria-label="'+esc(tr('bot_editor_tabs','Bot configuration'))+'">'+sections.map(([i,label])=>'<button type="button" role="tab" id="builderTab'+i+'" aria-controls="builderTabPanel" aria-selected="'+(i===step)+'" tabindex="'+(i===step?0:-1)+'" data-builder-tab="'+i+'">'+esc(label)+'</button>').join('')+'</div>':'<ol class="bot-builder-steps">'+createSteps.map((s,i)=>'<li '+(i===step?'aria-current="step"':'')+'><span aria-hidden="true">'+(i+1)+'</span>'+esc(s)+'</li>').join('')+'</ol>';
    const title=state.edit?sections.find(([i])=>i===step)?.[1]:createSteps[step];
    const introduction='<header class="bot-builder-section-head"><h2>'+esc(title||'')+'</h2><p>'+esc(tr('bot_setup_hint_'+step,''))+'</p></header>';
    body.innerHTML='<div class="main-view-content bot-builder">'+navigation+'<section id="builderTabPanel" '+(state.edit?'role="tabpanel" aria-labelledby="builderTab'+step+'"':'')+'>'+introduction+content+'</section>'+
      '<p id="builderError" role="alert" hidden></p><div class="bot-builder-actions"><button type="button" class="sm-btn" id="builderBack" '+(step===0||state.edit?'disabled':'')+'>'+esc(tr('bot_setup_back','Back'))+'</button><button type="button" class="sm-btn primary" id="builderNext">'+esc(state.edit?tr('bot_setup_save','Save bot'):step===3?tr('bot_setup_create','Create a bot'):tr('bot_setup_next','Continue'))+'</button></div></div>';
    if(state.edit){
      orientTabs();
      input('builderBack').hidden=true;
      body.querySelectorAll('[data-builder-tab]').forEach(tab=>{
        tab.onclick=()=>{if(!state||state.saving)return;if(window.BotKnowledge&&window.BotKnowledge.isBusy&&window.BotKnowledge.isBusy(state.config.name)){error(tr('bot_editor_knowledge_busy',"Wait for the knowledge file operation to finish."));return;}collect();state.step=Number(tab.dataset.builderTab);render();input('builderTab'+state.step).focus();input('builderTab'+state.step).scrollIntoView({block:'nearest',inline:'nearest'});};
        tab.onkeydown=event=>{
          if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;
          event.preventDefault();const tabs=[...body.querySelectorAll('[data-builder-tab]')];let index=tabs.indexOf(tab);
          index=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1)+tabs.length)%tabs.length;
          tabs[index].click();
        };
      });
      if(step===4){
        if(window.BotKnowledge)window.BotKnowledge.mount(input('builderKnowledge'),c.name);
        else input('builderKnowledge').textContent=tr('bot_editor_knowledge_unavailable',"Knowledge files are unavailable. Reload the page.");
      }
    }
    if(state.edit&&(step===6||step===7)){input('builderNext').hidden=true;mountAutomation();}
    if(state.edit&&input('builderName'))input('builderName').readOnly=true;
    body.querySelectorAll('[data-filter]').forEach(el=>el.oninput=()=>{
      body.querySelectorAll('[data-choice="'+el.dataset.filter+'"]').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(el.value.toLowerCase()));
    });
    if(input('builderPhoto'))input('builderPhoto').onchange=async event=>{
      if(!event.target.files.length)return;
      const current=state,button=input('builderNext');button.disabled=true;
      try{const avatar=await readAvatar(event.target.files[0]);if(state!==current)return;collect();state.avatar=avatar;render();}
      catch(err){if(state===current)error(err.message);}
      finally{event.target.value='';if(state===current&&input('builderNext'))input('builderNext').disabled=false;}
    };
    input('builderBack').onclick=()=>{if(!state||state.saving)return;collect();state.step--;render();};
    input('builderNext').onclick=async()=>{
      try{if(!state||state.saving)return;validate();if(!state.edit&&state.step<3){state.step++;render();}else await save();}catch(err){error(err.message);}
    };
  }
  async function open(name,section){
    if(window.BotKnowledge&&window.BotKnowledge.forget)window.BotKnowledge.forget();
    const intent=++epoch;state=null;
    _profileMode='create';
    if(typeof switchPanel==='function' && await switchPanel('profiles')===false)return;
    if(epoch!==intent || (typeof _currentPanel!=='undefined' && _currentPanel!=='profiles'))return;
    const body=input('profileDetailBody');if(!body)return;
    body.style.display='';body.textContent='Loading bot configuration…';
    const data=await api('/api/bots/builder'+(name?'?profile='+encodeURIComponent(name):''),{timeoutToast:false}).catch(err=>{
      if(epoch===intent)body.textContent=err.message;return null;
    });
    if(epoch!==intent||!data)return;
    if(!data.can_edit){body.textContent='You do not have permission to configure this bot.';return;}
    const steps={identity:0,soul:1,memory:4,knowledge:4,skills:5,settings:2,access:3,scout:6,tasks:7};
    state={step:name?(steps[section]??0):0,edit:!!name,catalog:data.catalog||{},config:{name:'',title:'',description:'',system_prompt:'',skills:[],mcp_servers:[],cli_tools:[],allowed_users:[],allowed_groups:[],...data.config}};
    if(!name)delete state.config.revision;
    render();
  }
  async function mountAutomation(){
    const current=state,box=input('builderAutomation');if(!current||!box)return;
    try{
      const data=await api('/api/profiles?fast=1&counts=0',{timeoutToast:false});
      if(state!==current||input('builderAutomation')!==box)return;
      const p=(data.profiles||[]).find(row=>row.name===current.config.name);
      if(!p)throw new Error('This bot is no longer available.');
      _currentProfileDetail=p;
      if(current.step===6){
        _botScoutTopics=[...((p.bot&&p.bot.scout&&p.bot.scout.topics)||[])];
        if(p.scout_manageable||p.bot_editable){
          const people=await api('/api/bots/scout',{method:'POST',body:JSON.stringify({name:p.name,action:'people'})});
          if(state!==current||input('builderAutomation')!==box)return;
          p.scout_people_options=people.people||[];
        }
        box.innerHTML=_botScoutCardHtml(p);
        if(!box.innerHTML){box.textContent='Scout is available for bot profiles only.';return;}
        _paintBotScoutTopics();

      }else{
        box.innerHTML='<div class="bot-task-toolbar"><button type="button" class="sm-btn" id="builderAssignTask">'+esc(tr('bot_editor_assign_task','Assign existing task'))+'</button><button type="button" class="sm-btn primary" id="builderCreateTask">'+esc(tr('bot_editor_new_task','New scheduled task'))+'</button></div><section id="profileBotJobs"></section>';
        input('builderAssignTask').onclick=()=>assignScheduledTaskToBot(p);
        input('builderCreateTask').onclick=()=>{collect();openCronCreate(p.name);};
        await _loadProfileBotJobs(p);
      }
    }catch(err){if(state===current&&input('builderAutomation')===box)box.textContent=err.message;}
  }
  async function assignScheduledTaskToBot(p){
    const current=state;
    try{
      const jobs=(await _botJobsAll()).filter(job=>job.managed_by!=='scout'&&_cronCanChangeBot(job)&&_cronJobBotName(job)!==p.name);
      if(state!==current)return;
      const dialog=document.createElement('dialog');dialog.className='bot-task-dialog';
      dialog.innerHTML='<form method="dialog"><h3 id="builderTaskDialogTitle">'+esc(tr('bot_editor_assign_title','Assign scheduled task'))+'</h3><p>'+esc(p.bot?.title||p.name)+' · '+esc(tr('bot_editor_assign_hint','Select a task. Its owner and schedule stay unchanged.'))+'</p><label>'+esc(tr('task','Task'))+'<select id="builderTaskChoice">'+jobs.map((job,i)=>'<option value="'+i+'">'+esc(job.name||job.id)+' · '+esc(job.owner_email||_cronOwnerProfileName(job))+'</option>').join('')+'</select></label><p role="alert" class="builder-task-error"></p><div class="bot-task-dialog-actions"><button type="submit" value="cancel" class="sm-btn">'+esc(tr('cancel','Cancel'))+'</button> <button type="button" class="sm-btn primary builder-task-assign" '+(!jobs.length?'disabled':'')+'>'+esc(tr('bot_editor_assign_save','Assign task'))+'</button></div></form>';
      if(!jobs.length)dialog.querySelector('.builder-task-error').textContent=tr('bot_editor_no_tasks','No other editable scheduled tasks are available.');
      dialog.querySelector('.builder-task-assign').onclick=async event=>{
        const job=jobs[Number(dialog.querySelector('select').value)];if(!job)return;
        event.target.disabled=true;
        try{
          const store=_cronOwnerProfileName(job)||'default';
          await api('/api/crons/assign',{method:'POST',body:JSON.stringify({job_id:job.id,owner_profile:store,bot:p.name===store?'':p.name})});
          _botJobsCache=null;dialog.close();
          if(state===current)await mountAutomation();
        }catch(err){dialog.querySelector('.builder-task-error').textContent=err.message;event.target.disabled=false;}
      };
      dialog.setAttribute('aria-labelledby','builderTaskDialogTitle');
      dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.appendChild(dialog);dialog.showModal();
    }catch(err){error(err.message);}
  }
  async function save(){
    if(!state||(!state.edit&&state.step!==3)||state.saving)return;
    if(window.BotKnowledge&&window.BotKnowledge.isBusy&&window.BotKnowledge.isBusy(state.config.name)){
      error(tr('bot_editor_knowledge_busy',"Wait for the knowledge file operation to finish."));return;
    }
    if(window.BotKnowledge&&window.BotKnowledge.hasUnsaved&&window.BotKnowledge.hasUnsaved(state.config.name)){
      error(tr('bot_editor_knowledge_unsaved',"Save your knowledge file selection first, then save the bot."));return;
    }
    validate();const current=state,button=input('builderNext');
    state.saving=true;button.disabled=true;button.textContent=tr('bot_setup_saving','Saving…');
    input('builderBack').disabled=true;
    input('profileDetailBody').querySelectorAll('[data-builder-tab]').forEach(tab=>tab.disabled=true);
    const payload={...state.config};
    delete payload.avatar_url;
    if(state.avatar)payload.avatar=state.avatar;
    try{
      await api('/api/bots/builder',{method:'POST',body:JSON.stringify(payload)});
      if(state!==current)return;
      if(window.BotKnowledge&&window.BotKnowledge.forget)window.BotKnowledge.forget();
      state=null;epoch++;_profileMode='read';
      _profileDropdownClearStoredCache();
      window.dispatchEvent(new CustomEvent('synpulse:bot-updated',{detail:{name:payload.name}}));
      await loadProfilesPanel();openProfileDetail(payload.name);
      showToast('Bot saved');
    }catch(err){if(state===current){current.saving=false;input('profileDetailBody').querySelectorAll('[data-builder-tab]').forEach(tab=>tab.disabled=false);error(err.message);button.disabled=false;input('builderBack').disabled=false;button.textContent=current.edit?tr('bot_setup_save','Save bot'):tr('bot_setup_create','Create a bot');}}
  }
  function invalidate(){epoch++;state=null;if(window.BotKnowledge&&window.BotKnowledge.forget)window.BotKnowledge.forget();}
  window.BotBuilder={readAvatar,open,save,invalidate,isEditing:name=>!!state?.edit&&state.config.name===name,refreshAutomation:mountAutomation};

})();
