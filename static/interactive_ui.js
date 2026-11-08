// Interactive answers in chat.
//
// An assistant reply may hold a fenced block with the info string
// `interactive-ui` (HTML, CSS and JavaScript). renderMd (static/ui.js) turns
// it into an escaped placeholder through the seam _interactiveUiFenceAccepts;
// postProcessRenderedMessages then calls renderInteractiveUiBlocks, which
// mounts a card with a sandboxed iframe. While a reply streams,
// interactiveUiStreamTick (called from static/messages.js) shows the same card
// live, with CSS and markup but no scripts yet.
//
// The iframe loads static/interactive-ui/frame.html, served by
// api/interactive_ui.py with its own CSP (`sandbox allow-scripts allow-forms
// allow-popups`, never allow-same-origin, network only to a few public CDNs).
// The widget source never touches this document's DOM: it is sent to the
// frame with postMessage, and every message back is checked against the
// iframe's own window before it is used.
//
// Globals: interactiveUiFenceAccepts, renderInteractiveUiBlocks,
// interactiveUiStreamTick, parseInteractiveUiSource. Internals in _iui.

const _iui=(function(){
  const FRAME_URL='static/interactive-ui/frame.html';
  const FENCE_LANGS=new Set(['interactive-ui','interactive','iui']);
  const CDN_ORIGINS=new Set(['https://cdn.jsdelivr.net','https://unpkg.com','https://cdnjs.cloudflare.com','https://esm.sh']);
  const MAX_SOURCE=200*1024;
  const MIN_H=80, DEFAULT_H=360, STREAM_THROTTLE_MS=220, PROMPT_GAP_MS=2500, INTERACT_WINDOW_MS=5000;
  const byWindow=new Map();     // contentWindow -> controller
  const controllers=new Set();  // every mounted controller (a moved iframe gets a new window)
  const heightCache=new Map();  // source fingerprint -> last height
  let seq=0, themeObserver=null, intersection=null;

  // ── Text ────────────────────────────────────────────────────────────────
  const TEXT={
    nl:{title:'Interactieve weergave',building:'Wordt opgebouwd',ready:'Interactief',loading:'Laden',error:'Fout in de weergave',
      reload:'Opnieuw laden',source:'Broncode',hideSource:'Verberg broncode',copySource:'Kopieer broncode',download:'Download als HTML',
      newTab:'Open in nieuw tabblad',full:'Volledig scherm',exitFull:'Sluit volledig scherm',repair:'Laat de agent dit herstellen',
      dismiss:'Verbergen',copied:'Gekopieerd',sent:'Vervolgvraag verstuurd',blocked:'Klik eerst in de weergave om een vervolgvraag te sturen',
      tooBig:'Deze weergave is te groot om te tonen',removed:'Niet toegestane bron overgeslagen',
      repairPrompt:(title,msg)=>`De interactieve weergave "${title}" gaf deze fout: ${msg}\nHerstel het en stuur het volledige interactive-ui-blok opnieuw.`,
      popupBlocked:'De browser blokkeerde het nieuwe tabblad',sandboxNote:'Draait afgeschermd: geen toegang tot je account of de chat'},
    en:{title:'Interactive view',building:'Building',ready:'Interactive',loading:'Loading',error:'Error in the view',
      reload:'Reload',source:'Source',hideSource:'Hide source',copySource:'Copy source',download:'Download as HTML',
      newTab:'Open in new tab',full:'Full screen',exitFull:'Exit full screen',repair:'Ask the agent to fix this',
      dismiss:'Dismiss',copied:'Copied',sent:'Follow-up sent',blocked:'Click inside the view first to send a follow-up',
      tooBig:'This view is too large to show',removed:'Skipped a source that is not allowed',
      repairPrompt:(title,msg)=>`The interactive view "${title}" failed with: ${msg}\nFix it and send the complete interactive-ui block again.`,
      popupBlocked:'The browser blocked the new tab',sandboxNote:'Runs isolated: no access to your account or the chat'},
  };
  function lang(){
    const l=String((typeof _currentLang!=='undefined'&&_currentLang)||document.documentElement.lang||navigator.language||'en').toLowerCase();
    return l.startsWith('nl')?'nl':'en';
  }
  function tx(key,...args){const v=(TEXT[lang()]||TEXT.en)[key];return typeof v==='function'?v(...args):(v||key);}
  function toast(msg){try{if(typeof showToast==='function')showToast(msg,2600);}catch(_){}}

  const ICON={
    spark:'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    reload:'<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
    code:'<path d="M16 18l6-6-6-6"/><path d="M8 6l-6 6 6 6"/>',
    download:'<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
    external:'<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
    expand:'<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    shrink:'<path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/>',
    copy:'<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    alert:'<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    wrench:'<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    close:'<path d="M18 6L6 18"/><path d="M6 6l12 12"/>',
  };
  function icon(name){return `<svg class="iui-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICON[name]||''}</svg>`;}

  // ── Source parsing ──────────────────────────────────────────────────────
  function hostOf(raw){try{return new URL(String(raw||'').trim(),'https://invalid.invalid/').host||String(raw||'').slice(0,60);}catch(_){return String(raw||'').slice(0,60);}}
  function allowedUrl(raw){
    try{const u=new URL(String(raw||'').trim(),'https://invalid.invalid/');return u.protocol==='https:'&&CDN_ORIGINS.has(u.origin)?u.href:null;}catch(_){return null;}
  }
  function attr(tag,name){
    const m=new RegExp('\\s'+name+'\\s*=\\s*("([^"]*)"|\'([^\']*)\'|([^\\s>]+))','i').exec(tag);
    return m?(m[2]!=null?m[2]:m[3]!=null?m[3]:m[4]):null;
  }
  function parse(source,opts){
    const final=!!(opts&&opts.final);
    let s=String(source||'');
    const out={title:'',height:0,css:'',html:'',scripts:[],warnings:[],bytes:s.length,tooBig:s.length>MAX_SOURCE};
    if(out.tooBig) return out;
    const meta=(key)=>{const m=new RegExp('<!--\\s*'+key+'\\s*:\\s*([\\s\\S]*?)\\s*-->','i').exec(s);return m?m[1].trim():'';};
    out.title=meta('title').slice(0,120);
    const h=parseInt(meta('height'),10);if(h>0)out.height=Math.max(MIN_H,Math.min(h,2000));
    s=s.replace(/<!--\s*(title|height)\s*:[\s\S]*?-->/gi,'');
    if(!out.title){const m=/<title[^>]*>([\s\S]*?)<\/title>/i.exec(s);if(m)out.title=m[1].replace(/<[^>]+>/g,'').trim().slice(0,120);}
    s=s.replace(/<title[^>]*>[\s\S]*?<\/title>/gi,'')
      .replace(/<!doctype[^>]*>/gi,'').replace(/<\/?(html|head|body)\b[^>]*>/gi,'')
      .replace(/<meta\b[^>]*>/gi,'').replace(/<base\b[^>]*>/gi,'');
    const imports=[], css=[];
    s=s.replace(/<link\b[^>]*>/gi,(tag)=>{
      if(/rel\s*=\s*["']?stylesheet/i.test(tag)){const u=allowedUrl(attr(tag,'href'));if(u)imports.push(`@import url("${u.replace(/"/g,'%22')}");`);else out.warnings.push(tx('removed')+': '+hostOf(attr(tag,'href')));}
      return '';
    });
    s=s.replace(/<style\b[^>]*>([\s\S]*?)<\/style>/gi,(_,body)=>{css.push(body);return '';});
    s=s.replace(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi,(_,attrs,body)=>{
      const tag='<script '+attrs+'>';
      const type=(attr(tag,'type')||'').toLowerCase();
      if(type&&type!=='module'&&type!=='text/javascript'&&type!=='application/javascript'){
        if(/json|template|text\//.test(type)) return `<script type="${type.replace(/"/g,'')}"${attr(tag,'id')?` id="${String(attr(tag,'id')).replace(/"/g,'')}"`:''}>${body}<\/script>`;
        return '';
      }
      const src=attr(tag,'src');
      if(src){const u=allowedUrl(src);if(u)out.scripts.push({src:u,type:type==='module'?'module':''});else out.warnings.push(tx('removed')+': '+hostOf(src));}
      else if(body.trim()) out.scripts.push({code:body,type:type==='module'?'module':''});
      return '';
    });
    if(!final){
      // Still streaming: an unfinished <style> already styles what is there,
      // an unfinished <script> and a half-written tag are left out.
      const openStyle=/<style\b[^>]*>([\s\S]*)$/i.exec(s);
      if(openStyle){css.push(openStyle[1]);s=s.slice(0,openStyle.index);}
      const openScript=/<script\b[\s\S]*$/i.exec(s);
      if(openScript) s=s.slice(0,openScript.index);
      s=s.replace(/<[^>]*$/,'');
    }
    out.css=imports.concat(css).join('\n');
    out.html=s.trim();
    return out;
  }

  // ── Theme ───────────────────────────────────────────────────────────────
  function cssVar(cs,name){return (cs.getPropertyValue(name)||'').trim();}
  function luminance(color){
    const m=/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i.exec(color||'');
    if(!m) return null;
    const c=[m[1],m[2],m[3]].map(v=>{v=Number(v)/255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
  }
  function themeMessage(){
    const cs=getComputedStyle(document.documentElement);
    const pick=(...names)=>{for(const n of names){const v=cssVar(cs,n);if(v)return v;}return '';};
    const vars={
      '--sw-bg':pick('--main-bg','--bg'),
      '--sw-surface':pick('--surface','--input-bg'),
      '--sw-surface-2':pick('--hover-bg','--surface-subtle','--code-bg'),
      '--sw-fg':pick('--text'),
      '--sw-strong':pick('--strong','--text'),
      '--sw-muted':pick('--muted'),
      '--sw-accent':pick('--accent'),
      '--sw-accent-fg':pick('--accent-text-on','--on-accent')||'#ffffff',
      '--sw-accent-soft':pick('--accent-bg'),
      '--sw-border':pick('--border'),
    };
    Object.keys(vars).forEach(k=>{if(!vars[k])delete vars[k];});
    // The chat marks dark mode with html.dark; fall back to the surface colour.
    const root=document.documentElement;
    let mode;
    if(root.classList.contains('dark')) mode='dark';
    else if(root.classList.contains('light')||root.dataset.theme==='light') mode='light';
    else{
      const probe=document.body?getComputedStyle(document.body).backgroundColor:'';
      const lum=luminance(probe);
      mode=lum==null||lum<0.45?'dark':'light';
    }
    if(!root.classList.contains('dark')&&typeof _resolvedThemeBaseDark!=='undefined') mode='light';
    return {type:'theme',vars,mode};
  }
  function broadcastTheme(){const msg=themeMessage();byWindow.forEach(ctrl=>postTo(ctrl,msg));}
  function watchTheme(){
    if(themeObserver||typeof MutationObserver!=='function') return;
    let pending=0;
    themeObserver=new MutationObserver(()=>{clearTimeout(pending);pending=setTimeout(broadcastTheme,60);});
    themeObserver.observe(document.documentElement,{attributes:true,attributeFilter:['class','data-theme','data-skin','style']});
    if(document.body) themeObserver.observe(document.body,{attributes:true,attributeFilter:['class','data-theme']});
  }

  // ── Frame messaging ─────────────────────────────────────────────────────
  function postTo(ctrl,msg){
    const w=ctrl&&ctrl.iframe&&ctrl.iframe.contentWindow;
    if(!w||!ctrl.ready) return;
    try{w.postMessage(Object.assign({iui:1},msg),'*');}catch(_){}
  }
  function pushRender(ctrl){
    if(!ctrl.ready||ctrl.sentFinal) return;
    const p=ctrl.parsed;
    if(!p||p.tooBig) return;
    postTo(ctrl,{type:'render',css:p.css,html:p.html,scripts:ctrl.final?p.scripts:[],final:ctrl.final});
    if(ctrl.final) ctrl.sentFinal=true;
  }
  function onMessage(e){
    const data=e&&e.data;
    if(!data||data.iui!==1||typeof data.type!=='string') return;
    let ctrl=byWindow.get(e.source);
    let popup=false;
    if(!ctrl) ctrl=adopt(e.source);
    if(!ctrl){
      // A widget opened in its own tab talks to us through window.opener.
      byWindow.forEach(c=>{if(c.popup&&c.popup===e.source){ctrl=c;popup=true;}});
      if(!ctrl) return;
    }
    if(popup){handlePopup(ctrl,e.source,data);return;}
    switch(data.type){
      case 'ready':
        ctrl.ready=true;ctrl.sentFinal=false;
        postTo(ctrl,themeMessage());
        pushRender(ctrl);
        break;
      case 'height':
        setHeight(ctrl,Number(data.height)||0);
        break;
      case 'rendered':
        setState(ctrl,ctrl.errors.length?'error':'ready');
        break;
      case 'error':
        addError(ctrl,String(data.message||''),String(data.detail||''));
        break;
      case 'interact':
        ctrl.lastInteract=Date.now();
        break;
      case 'prompt':
        followUp(ctrl,String(data.text||''),document.activeElement===ctrl.iframe);
        break;
      case 'copy':
        copyText(String(data.text||''));
        break;
      case 'open':
        openLink(String(data.url||''));
        break;
      case 'key':
        if(data.key==='Escape'&&ctrl.card.classList.contains('iui-full')) toggleFull(ctrl);
        break;
      case 'log':
        try{console.warn('[interactive-ui]',String(data.message||''));}catch(_){}
        break;
    }
  }
  // A frame that was moved in the DOM reloads with a new window; find its
  // controller by asking each iframe for its current window.
  function adopt(win){
    let found=null;
    controllers.forEach(c=>{
      if(!c.iframe){controllers.delete(c);return;}
      if(!c.card.isConnected&&Date.now()-c.mountedAt>60000){controllers.delete(c);return;}
      if(c.iframe.contentWindow===win){found=c;}
    });
    if(found){byWindow.set(win,found);found.ready=false;found.sentFinal=false;}
    return found;
  }
  function handlePopup(ctrl,win,data){
    if(data.type==='ready'){
      const p=ctrl.parsed;
      try{
        win.postMessage(Object.assign({iui:1},themeMessage()),'*');
        win.postMessage({iui:1,type:'render',css:p.css,html:p.html,scripts:p.scripts,final:true},'*');
      }catch(_){}
    } else if(data.type==='interact'){ctrl.popupInteract=Date.now();}
    else if(data.type==='prompt'){followUp(ctrl,String(data.text||''),Date.now()-(ctrl.popupInteract||0)<INTERACT_WINDOW_MS);}
    else if(data.type==='open'){openLink(String(data.url||''));}
  }
  function openLink(url){
    if(!/^https?:\/\//i.test(url)) return;
    try{window.open(url,'_blank','noopener,noreferrer');}catch(_){}
  }
  function copyText(text){
    if(!text) return;
    const done=()=>toast(tx('copied'));
    try{
      if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,()=>fallbackCopy(text,done));return;}
    }catch(_){}
    fallbackCopy(text,done);
  }
  function fallbackCopy(text,done){
    try{const ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();done();}catch(_){}
  }
  function followUp(ctrl,text,userActive){
    text=text.trim().slice(0,4000);
    if(!text) return;
    const now=Date.now();
    const recent=now-(ctrl.lastInteract||0)<INTERACT_WINDOW_MS;
    if(!(userActive||recent)){toast(tx('blocked'));return;}
    if(now-(ctrl.lastPrompt||0)<PROMPT_GAP_MS) return;
    ctrl.lastPrompt=now;
    sendPrompt(text);
  }
  function sendPrompt(text){
    const box=document.getElementById('msg');
    if(!box||typeof window.send!=='function') return;
    box.value=text;
    try{box.dispatchEvent(new Event('input',{bubbles:true}));}catch(_){}
    try{
      window.send();
      toast(tx('sent'));
    }catch(err){try{console.warn('[interactive-ui] follow-up failed',err);}catch(_){}}
  }

  // ── Card ────────────────────────────────────────────────────────────────
  function fingerprint(src){return String(src||'').slice(0,400);}
  function setHeight(ctrl,h){
    if(!(h>0)) return;
    ctrl.height=h;
    heightCache.set(ctrl.fp,h);
    if(ctrl.card.classList.contains('iui-full')) return;
    const max=Math.max(320,Math.round((window.innerHeight||900)*0.86));
    ctrl.stage.style.height=Math.max(MIN_H,Math.min(h,max))+'px';
    ctrl.stage.classList.toggle('iui-stage--scroll',h>max);
  }
  function setState(ctrl,state){
    ctrl.state=state;
    ctrl.card.dataset.state=state;
    const label=state==='building'?tx('building'):state==='error'?tx('error'):state==='ready'?tx('ready'):tx('loading');
    ctrl.status.textContent=label;
    if(state==='building'&&ctrl.parsed) ctrl.status.textContent=label+' · '+formatBytes(ctrl.parsed.bytes);
  }
  function formatBytes(n){return n<1024?n+' B':(n/1024).toFixed(1).replace('.',lang()==='nl'?',':'.')+' KB';}
  function addError(ctrl,message,detail){
    if(!message) return;
    if(ctrl.errors.some(e=>e.message===message)) return;
    ctrl.errors.push({message,detail});
    ctrl.errorText.textContent=ctrl.errors.slice(0,3).map(e=>e.message).join(' · ');
    ctrl.errorBar.hidden=false;
    setState(ctrl,'error');
  }
  function button(name,label,onClick,extra){
    const b=document.createElement('button');
    b.type='button';b.className='iui-btn'+(extra?' '+extra:'');
    b.title=label;b.setAttribute('aria-label',label);
    b.innerHTML=icon(name)+`<span class="iui-btn-label">${escHtml(label)}</span>`;
    b.addEventListener('click',ev=>{ev.preventDefault();ev.stopPropagation();onClick(b);});
    return b;
  }
  function escHtml(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  function createController(source,opts){
    const final=!!(opts&&opts.final);
    const card=document.createElement('div');
    card.className='iui-card';
    card.dataset.iuiCard=String(++seq);
    card.setAttribute('role','group');
    const head=document.createElement('div');head.className='iui-head';
    const badge=document.createElement('span');badge.className='iui-badge';badge.innerHTML=icon('spark');
    const titleEl=document.createElement('span');titleEl.className='iui-title';
    const status=document.createElement('span');status.className='iui-status';status.setAttribute('aria-live','polite');
    const actions=document.createElement('div');actions.className='iui-actions';
    head.append(badge,titleEl,status,actions);
    const stage=document.createElement('div');stage.className='iui-stage';
    const skeleton=document.createElement('div');skeleton.className='iui-skeleton';skeleton.innerHTML='<span></span><span></span><span></span>';
    stage.appendChild(skeleton);
    const errorBar=document.createElement('div');errorBar.className='iui-error';errorBar.hidden=true;
    const errorText=document.createElement('span');errorText.className='iui-error-text';
    errorBar.innerHTML=icon('alert');errorBar.appendChild(errorText);
    const sourceBox=document.createElement('div');sourceBox.className='iui-source';sourceBox.hidden=true;
    const pre=document.createElement('pre');const code=document.createElement('code');code.className='language-html';pre.appendChild(code);
    sourceBox.appendChild(pre);
    const foot=document.createElement('div');foot.className='iui-foot';foot.innerHTML=icon('lock')+`<span>${escHtml(tx('sandboxNote'))}</span>`;
    card.append(head,stage,errorBar,sourceBox,foot);

    const ctrl={card,head,titleEl,status,actions,stage,skeleton,errorBar,errorText,sourceBox,code,foot,
      iframe:null,ready:false,final,sentFinal:false,source:'',parsed:null,errors:[],state:'loading',
      fp:'',height:0,lastInteract:0,lastPrompt:0,popup:null,popupInteract:0,lastTick:0,tickTimer:0,mounted:false,mountedAt:0};

    const repair=button('wrench',tx('repair'),()=>{
      const msg=ctrl.errors.map(e=>e.message).join('; ');
      sendPrompt(tx('repairPrompt',ctrl.parsed&&ctrl.parsed.title||tx('title'),msg));
    },'iui-btn--text');
    const dismiss=button('close',tx('dismiss'),()=>{errorBar.hidden=true;},'iui-btn--icon');
    errorBar.append(repair,dismiss);

    const srcBtn=button('code',tx('source'),b=>{
      sourceBox.hidden=!sourceBox.hidden;
      b.classList.toggle('is-on',!sourceBox.hidden);
      b.setAttribute('aria-pressed',String(!sourceBox.hidden));
      if(!sourceBox.hidden){code.textContent=ctrl.source;try{if(typeof Prism!=='undefined'&&Prism.highlightElement)Prism.highlightElement(code);}catch(_){}}
    });
    const copyBtn=button('copy',tx('copySource'),()=>copyText(ctrl.source));
    const reloadBtn=button('reload',tx('reload'),()=>reload(ctrl));
    const dlBtn=button('download',tx('download'),()=>download(ctrl));
    const tabBtn=button('external',tx('newTab'),()=>openTab(ctrl));
    const fullBtn=button('expand',tx('full'),()=>toggleFull(ctrl));
    ctrl.fullBtn=fullBtn;
    actions.append(srcBtn,copyBtn,reloadBtn,dlBtn,tabBtn,fullBtn);
    ctrl.finalOnly=[copyBtn,reloadBtn,dlBtn,tabBtn];
    update(ctrl,source,final);
    return ctrl;
  }
  function update(ctrl,source,final){
    ctrl.source=String(source||'');
    ctrl.final=!!final;
    ctrl.parsed=parse(ctrl.source,{final:ctrl.final});
    if(!ctrl.fp||!ctrl.final) ctrl.fp=fingerprint(ctrl.source);
    const p=ctrl.parsed;
    const title=p.title||tx('title');
    ctrl.titleEl.textContent=title;
    ctrl.card.setAttribute('aria-label',title);
    ctrl.finalOnly.forEach(b=>{b.disabled=!ctrl.final;});
    if(!ctrl.sourceBox.hidden) ctrl.code.textContent=ctrl.source;
    if(p.tooBig){setState(ctrl,'error');addError(ctrl,tx('tooBig'),'');return;}
    p.warnings.forEach(w=>addError(ctrl,w,''));
    if(!ctrl.height){
      const cached=heightCache.get(ctrl.fp);
      ctrl.stage.style.height=(cached||p.height||DEFAULT_H)+'px';
    }
    setState(ctrl,ctrl.final?(ctrl.state==='ready'?'ready':'loading'):'building');
    if(ctrl.mounted) pushRender(ctrl);
  }
  function mount(ctrl){
    if(ctrl.mounted) return;
    ctrl.mounted=true;
    const iframe=document.createElement('iframe');
    iframe.className='iui-frame';
    iframe.setAttribute('sandbox','allow-scripts allow-forms allow-popups');
    iframe.setAttribute('referrerpolicy','no-referrer');
    iframe.setAttribute('title',ctrl.parsed&&ctrl.parsed.title||tx('title'));
    iframe.setAttribute('loading','eager');
    iframe.src=FRAME_URL+'?v='+encodeURIComponent(String((typeof WEBUI_VERSION!=='undefined'&&WEBUI_VERSION)||'1'));
    iframe.addEventListener('load',()=>{ctrl.skeleton.classList.add('is-gone');});
    ctrl.iframe=iframe;
    ctrl.mountedAt=Date.now();
    controllers.add(ctrl);
    ctrl.stage.appendChild(iframe);
    // contentWindow exists as soon as the iframe is in the document.
    if(iframe.contentWindow) byWindow.set(iframe.contentWindow,ctrl);
    watchTheme();
  }
  function lazyMount(ctrl){
    if(typeof IntersectionObserver!=='function'){mount(ctrl);return;}
    if(!intersection){
      intersection=new IntersectionObserver(entries=>{
        entries.forEach(en=>{
          if(!en.isIntersecting) return;
          const c=en.target.__iui;
          intersection.unobserve(en.target);
          if(c) mount(c);
        });
      },{rootMargin:'800px 0px'});
    }
    ctrl.card.__iui=ctrl;
    intersection.observe(ctrl.card);
  }
  function reload(ctrl){
    if(!ctrl.iframe) return;
    byWindow.delete(ctrl.iframe.contentWindow);
    ctrl.iframe.remove();
    ctrl.iframe=null;ctrl.mounted=false;ctrl.ready=false;ctrl.sentFinal=false;ctrl.errors=[];ctrl.errorBar.hidden=true;
    ctrl.skeleton.classList.remove('is-gone');
    setState(ctrl,'loading');
    mount(ctrl);
  }
  function toggleFull(ctrl){
    const on=!ctrl.card.classList.contains('iui-full');
    ctrl.card.classList.toggle('iui-full',on);
    document.documentElement.classList.toggle('iui-has-full',on);
    const b=ctrl.fullBtn;
    b.innerHTML=icon(on?'shrink':'expand')+`<span class="iui-btn-label">${escHtml(on?tx('exitFull'):tx('full'))}</span>`;
    b.title=on?tx('exitFull'):tx('full');b.setAttribute('aria-label',b.title);
    if(on){
      ctrl.stage.style.height='';
      ctrl._esc=ev=>{if(ev.key==='Escape'){ev.preventDefault();toggleFull(ctrl);}};
      document.addEventListener('keydown',ctrl._esc,true);
      b.focus();
    } else {
      if(ctrl._esc) document.removeEventListener('keydown',ctrl._esc,true);
      ctrl._esc=null;
      if(ctrl.height) setHeight(ctrl,ctrl.height);
    }
    setTimeout(()=>postTo(ctrl,{type:'measure'}),50);
  }
  function openTab(ctrl){
    if(!ctrl.final) return;
    const w=window.open(FRAME_URL,'_blank');
    if(!w){toast(tx('popupBlocked'));return;}
    ctrl.popup=w;
  }
  function standaloneHtml(ctrl,frameHtml){
    const p=ctrl.parsed, theme=themeMessage();
    const vars=Object.keys(theme.vars).map(k=>`${k}:${theme.vars[k]}`).join(';');
    const scripts=p.scripts.map(sc=>sc.src
      ?`<script${sc.type?' type="module"':''} src="${escHtml(sc.src)}"><\/script>`
      :`<script${sc.type?' type="module"':''}>${String(sc.code).replace(/<\/script/gi,'<\\/script')}<\/script>`).join('\n');
    const title=escHtml(p.title||tx('title'));
    let doc=String(frameHtml||'');
    if(!/id="iui-root"/.test(doc)){
      doc='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title></title><style id="iui-user-style"></style></head><body><div id="iui-root"></div></body></html>';
    }
    doc=doc.replace(/<title>[\s\S]*?<\/title>/i,`<title>${title}</title>`)
      .replace('<html lang="nl" data-theme="dark">',`<html lang="${lang()}" data-theme="${theme.mode}" style="${escHtml(vars)}">`)
      .replace('<style id="iui-user-style"></style>',()=>`<style id="iui-user-style">${p.css.replace(/<\/style/gi,'<\\/style')}</style>`)
      .replace('<div id="iui-root"></div>',()=>`<div id="iui-root">${p.html}</div>`)
      .replace(/<\/body>/i,()=>scripts+'\n</body>');
    return doc;
  }
  function download(ctrl){
    if(!ctrl.final) return;
    const finish=html=>{
      const blob=new Blob([standaloneHtml(ctrl,html)],{type:'text/html'});
      const a=document.createElement('a');
      const name=(ctrl.parsed.title||'interactieve-weergave').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'weergave';
      a.href=URL.createObjectURL(blob);a.download=name+'.html';
      document.body.appendChild(a);a.click();
      setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1500);
    };
    fetch(FRAME_URL,{credentials:'same-origin'}).then(r=>r.ok?r.text():'').then(finish,()=>finish(''));
  }

  // ── Settled render (after the reply is complete) ────────────────────────
  function renderBlocks(container){
    const root=container||document;
    if(!root.querySelectorAll) return;
    root.querySelectorAll('.iui-block:not([data-iui-mounted])').forEach(block=>{
      block.setAttribute('data-iui-mounted','1');
      const source=block.textContent||'';
      const ctrl=createController(source,{final:true});
      block.textContent='';
      block.appendChild(ctrl.card);
      lazyMount(ctrl);
    });
  }

  // ── Live render while a reply streams ───────────────────────────────────
  function streamTick(root){
    if(!root||!root.querySelectorAll) return;
    root.querySelectorAll('pre > code').forEach(code=>{
      const cls=' '+(code.className||'')+' ';
      if(!/ (language-)?(interactive-ui|interactive|iui) /.test(cls)) return;
      const pre=code.parentElement;
      let ctrl=pre.__iuiLive;
      if(!ctrl){
        ctrl=createController(code.textContent||'',{final:false});
        ctrl.card.classList.add('iui-live');
        pre.__iuiLive=ctrl;
        pre.classList.add('iui-raw-hidden');
        pre.parentNode.insertBefore(ctrl.card,pre);
        // Only frames that are actually on screen load: the chat keeps a hidden
        // copy of the streaming text, which must not run a second widget.
        lazyMount(ctrl);
        return;
      }
      const now=Date.now();
      const run=()=>{ctrl.lastTick=Date.now();ctrl.tickTimer=0;update(ctrl,code.textContent||'',false);};
      if(now-ctrl.lastTick>=STREAM_THROTTLE_MS) run();
      else if(!ctrl.tickTimer) ctrl.tickTimer=setTimeout(run,STREAM_THROTTLE_MS);
    });
  }

  window.addEventListener('message',onMessage);
  return {parse,renderBlocks,streamTick,allowedUrl,themeMessage,FENCE_LANGS,_byWindow:byWindow};
})();

function interactiveUiFenceAccepts(lang,code){
  return _iui.FENCE_LANGS.has(String(lang||'').toLowerCase())&&String(code||'').trim().length>0;
}
function renderInteractiveUiBlocks(container){_iui.renderBlocks(container);}
function interactiveUiStreamTick(root){_iui.streamTick(root);}
function parseInteractiveUiSource(source,opts){return _iui.parse(source,opts);}
