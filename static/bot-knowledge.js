/* Existing bot document picker. Explicit uploads never select themselves. */
(function(){
  'use strict';
  const tr=(key,fallback)=>typeof t==='function'?t(key):fallback;
  const drafts=new Map();
  const hasUnsaved=profile=>{const d=drafts.get(profile);return !!d && (d.busy || JSON.stringify([...d.selected].sort())!==JSON.stringify([...d.saved].sort()));};
  async function mount(container, profile){
    if(!container)return;
    const token={};container._knowledgeToken=token;
    const alive=()=>container.isConnected&&container._knowledgeToken===token;
    const node=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el;};
    container.replaceChildren(node('p',tr("bot_documents_loading","Loading bot documents\u2026")));
    let data, busy=false;
    const draft=drafts.get(profile)||{selected:new Set(),saved:new Set(),initialized:false,busy:false};drafts.set(profile,draft);
    const selected=draft.selected;
    const endpoint='/api/bots/knowledge';
    function render(){
      if(!alive())return;
      container.replaceChildren();
      container.append(node('h3',tr("bot_documents_title","Knowledge files")),node('p','Upload documents, then select the files this bot may use. Saved selections are shared with everyone who can use this bot.'));
      const uploadLabel=node('label',tr("bot_documents_upload","Upload documents from your computer"));uploadLabel.className='bot-builder-field';
      const upload=node('input');upload.type='file';upload.multiple=true;upload.accept='.md,.txt,.csv,.json,.pdf,.docx';upload.dataset.knowledgeUpload='';upload.disabled=busy;
      uploadLabel.append(upload);container.append(uploadLabel,node('p','PDF, DOCX, Markdown, text, CSV or JSON. Up to 10 MB per document. Uploading alone does not add a document to the bot’s selected knowledge.'));
      const search=node('input');search.type='search';search.placeholder=tr("bot_documents_find","Find a document");search.setAttribute('aria-label',tr("bot_documents_find","Find a document"));container.append(search);
      const list=node('fieldset');list.className='bot-builder-options';list.append(node('legend',tr("bot_documents_available","Available bot documents")));
      const rows=node('div');rows.className='bot-builder-choice-list';
      for(const file of data.files||[]){
        const label=node('label');label.dataset.knowledgeRow='';const check=node('input');check.type='checkbox';check.value=file.id;check.checked=selected.has(file.id);check.disabled=busy;check.dataset.knowledgeFile='';
        check.onchange=()=>{if(check.checked)selected.add(file.id);else selected.delete(file.id);status.textContent=tr("bot_documents_changed","Selection changed. Choose Save knowledge to apply it.");};
        label.append(check,node('span',file.name+' ('+Math.ceil(file.size/1024)+' KB)'));rows.append(label);
      }
      if(!(data.files||[]).length)rows.append(node('p','No documents uploaded yet. Choose files above to add them.'));
      list.append(rows);container.append(list);
      if((data.legacy_sources||[]).length){
        const legacy=node('details');legacy.append(node('summary','Previously configured workspace references'));
        legacy.append(node('p','These references are preserved and still depend on each chat’s workspace. Upload the documents above to make them available across this bot’s chats.'));
        for(const path of data.legacy_sources)legacy.append(node('p',path));container.append(legacy);
      }
      const save=node('button',tr("bot_documents_save","Save knowledge"));save.type='button';save.className='sm-btn primary';save.dataset.knowledgeSave='';save.disabled=busy;container.append(save);
      const status=node('p');status.setAttribute('role','status');status.dataset.knowledgeStatus='';container.append(status);
      search.oninput=()=>{for(const row of rows.querySelectorAll('[data-knowledge-row]'))row.hidden=!row.textContent.toLowerCase().includes(search.value.toLowerCase());};
      const setBusy=value=>{busy=value;draft.busy=value;upload.disabled=value;save.disabled=value;for(const check of rows.querySelectorAll('input'))check.disabled=value;};
      save.onclick=async()=>{
        if(busy)return;setBusy(true);status.textContent=tr("bot_documents_saving","Saving knowledge selection\u2026");
        try{const result=await api(endpoint,{method:'POST',body:JSON.stringify({profile,action:'select',selected:[...selected],revision:draft.revision})});if(!alive())return;data=result;draft.saved=new Set(result.selected||[]);draft.revision=result.revision;status.textContent=tr("bot_documents_saved","Knowledge selection saved.");window.dispatchEvent(new CustomEvent('synpulse:bot-updated',{detail:{name:profile}}));}
        catch(error){if(alive())status.textContent=error.message||'Could not save knowledge. Reload this tab and try again.';}
        finally{draft.busy=false;if(alive())setBusy(false);}
      };
      upload.onchange=async()=>{
        if(busy||!upload.files.length)return;const files=[...upload.files];setBusy(true);let count=0;
        try{
          for(const file of files){
            if(!alive())break;if(file.size>10*1024*1024)throw new Error(file.name+' is larger than 10 MB.');
            status.textContent='Uploading '+file.name+'…';
            const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Could not read '+file.name));reader.readAsDataURL(file);});
            if(!alive())break;
            const result=await api(endpoint,{method:'POST',body:JSON.stringify({profile,action:'upload',filename:file.name,data:encoded})});
            if(!alive())break;data=result;count++;
          }
          if(alive()){setBusy(false);render();container.querySelector('[data-knowledge-status]').textContent=count+' document(s) uploaded. Select documents and choose Save knowledge.';}
        }catch(error){if(alive()){setBusy(false);render();container.querySelector('[data-knowledge-status]').textContent=(count?count+' document(s) uploaded. ':'')+(error.message||'Upload failed. Try again.');}}finally{draft.busy=false;}
      };
    }
    try{data=await api(endpoint+'?profile='+encodeURIComponent(profile),{timeoutToast:false});if(!alive())return;if(!draft.initialized){for(const id of data.selected||[])selected.add(id);draft.saved=new Set(data.selected||[]);draft.revision=data.revision;draft.initialized=true;}render();}
    catch(error){if(alive()){container.replaceChildren(node('p',error.message||'Could not load bot documents.'));const retry=node('button',tr("bot_documents_retry","Retry"));retry.type='button';retry.className='sm-btn';retry.onclick=()=>mount(container,profile);container.append(retry);}}
  }
  window.BotKnowledge={mount,hasUnsaved,isBusy:profile=>!!drafts.get(profile)?.busy,forget:profile=>{if(profile)drafts.delete(profile);else drafts.clear();}};
})();
