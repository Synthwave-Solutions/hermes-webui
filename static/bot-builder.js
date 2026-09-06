/* Guided bot setup: draft-only until the final atomic save. */
(function(){
  'use strict';
  let state=null, epoch=0;
  const copy = {
    steps:['Identity & photo','Instructions & skills','Connections & tools','Access & review'],
    next:'Continue',back:'Back',save:'Create bot',saving:'Saving…'
  };
  function input(id){return document.getElementById(id);}
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
    for(const [id,key] of [['builderName','name'],['builderTitle','title'],['builderDescription','description'],['builderPrompt','system_prompt']]){
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
    if(state.step===0){
      c.name=(c.name||'').trim().toLowerCase();
      if(!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(c.name))throw new Error('Use a bot ID with lowercase letters, numbers, hyphens or underscores.');
      if(!(c.title||'').trim())throw new Error('Give your bot a display name.');
    }
    if(state.step===1&&!(c.system_prompt||'').trim())throw new Error('Describe the bot’s role and instructions before continuing.');
  }
  function error(message){
    const el=input('builderError');if(el){el.textContent=message;el.hidden=false;}
  }
  function render(){
    const body=input('profileDetailBody');if(!body||!state)return;
    const {config:c,catalog:cat,step}=state;
    input('profileDetailTitle').textContent=state.edit?'Edit bot':'Create a bot';
    input('profileDetailEmpty').style.display='none';body.style.display='';
    _profileMode='create';_setProfileHeaderButtons('create');
    const headerSave=input('btnSaveProfileDetail');if(headerSave)headerSave.style.display='none';
    let content='';
    if(step===0){
      content=field('Bot ID','builderName',c.name)+field('Display name','builderTitle',c.title)+
        field('What does this bot help with?','builderDescription',c.description,true)+
        '<label class="bot-builder-field">Profile photo<input id="builderPhoto" type="file" accept="image/png,image/jpeg,image/webp"></label>'+
        '<p>PNG, JPEG or WebP up to 10 MB. Resized before saving.</p>'+
        ((state.avatar||c.avatar_url)?'<img class="bot-builder-photo" src="'+esc(state.avatar||c.avatar_url)+'" alt="Bot photo preview">':'');
    }else if(step===1){
      content=field('System instructions','builderPrompt',c.system_prompt,true)+
        '<p>Define the role, expected outputs and boundaries. These are the bot’s instructions, not your personal memory.</p>'+
        choices('Skills','skills',cat.skills);
    }else if(step===2){
      content='<p>Only connections and tools already available to your account can be selected. Credentials stay on the server.</p>'+
        choices('MCP connections','mcp_servers',cat.mcp_servers)+choices('CLI tools','cli_tools',cat.cli_tools)+
        '<p>Model: <strong>'+esc(c.default_model||'Configured default')+'</strong> '+esc(c.model_provider||'')+'</p>';
    }else{
      content='<p>Private to you by default. Add only the people or groups who should be able to use this bot.</p>'+
        choices('Allowed users','allowed_users',cat.users)+choices('Allowed groups','allowed_groups',cat.groups)+
        '<h3>Review before saving</h3><dl class="bot-builder-review">'+
        [['Bot',c.title+' (@'+c.name+')'],['Instructions',c.system_prompt],['Skills',(c.skills||[]).join(', ')||'None selected'],['MCP connections',(c.mcp_servers||[]).join(', ')||'None selected'],['CLI tools',(c.cli_tools||[]).join(', ')||'None selected']].map(([a,b])=>'<dt>'+esc(a)+'</dt><dd>'+esc(b)+'</dd>').join('')+'</dl>'+
        '<p>The bot becomes available only after all configuration and access checks succeed.</p>';
    }
    body.innerHTML='<div class="main-view-content bot-builder"><ol class="bot-builder-steps">'+copy.steps.map((s,i)=>'<li '+(i===step?'aria-current="step"':'')+'>'+esc(s)+'</li>').join('')+'</ol>'+content+
      '<p id="builderError" role="alert" hidden></p><div class="bot-builder-actions"><button type="button" class="sm-btn" id="builderBack" '+(step===0?'disabled':'')+'>Back</button><button type="button" class="sm-btn primary" id="builderNext">'+(step===3?(state.edit?'Save bot':'Create bot'):'Continue')+'</button></div></div>';
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
      try{if(!state||state.saving)return;validate();if(state.step<3){state.step++;render();}else await save();}catch(err){error(err.message);}
    };
  }
  async function open(name){
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
    state={step:0,edit:!!name,catalog:data.catalog||{},config:{name:'',title:'',description:'',system_prompt:'',skills:[],mcp_servers:[],cli_tools:[],allowed_users:[],allowed_groups:[],...data.config}};
    if(!name)delete state.config.revision;
    render();
  }
  async function save(){
    if(!state||state.step!==3||state.saving)return;
    collect();const current=state,button=input('builderNext');
    state.saving=true;button.disabled=true;button.textContent='Saving…';
    input('builderBack').disabled=true;
    const payload={...state.config};
    delete payload.avatar_url;
    if(state.avatar)payload.avatar=state.avatar;
    try{
      await api('/api/bots/builder',{method:'POST',body:JSON.stringify(payload)});
      if(state!==current)return;
      state=null;epoch++;_profileMode='read';
      _profileDropdownClearStoredCache();
      window.dispatchEvent(new CustomEvent('synpulse:bot-updated',{detail:{name:payload.name}}));
      await loadProfilesPanel();openProfileDetail(payload.name);
      showToast('Bot saved');
    }catch(err){if(state===current){current.saving=false;error(err.message);button.disabled=false;input('builderBack').disabled=false;button.textContent=current.edit?'Save bot':'Create bot';}}
  }
  function invalidate(){epoch++;state=null;}
  window.BotBuilder={readAvatar,open,save,invalidate};

})();
