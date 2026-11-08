// SynthPulse Artifacts in the chat.
//
// After `artifact_publish` the reply carries a fenced block
//   ```artifact
//   {"id":"<uuid>","title":"...","kind":"html"}
//   ```
// renderMd (static/ui.js) turns it into an .iui-block placeholder through
// interactiveUiFenceAccepts (static/interactive_ui.js), and renderBlocks hands
// it to synthpulseArtifactRender, which draws an artifact card: title, a live
// preview in a sandboxed iframe, full screen, download and an explicit share.
//
// The preview comes from GET /api/artifacts/<id>/frame (api/artifacts.py): the
// artifact service renders it, the WebUI serves it with `sandbox allow-scripts`
// (opaque origin, no network), so artifact code never reaches this document,
// its cookies or the API. Only the person who made it (and the library admin)
// can open it; anyone else sees a quiet "not available" card.
//
// Globals: synthpulseArtifactAccepts, synthpulseArtifactRender.

const _spa=(function(){
  const ID_RE=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const HEIGHT={html:540,markdown:460,svg:400,png:400,webp:400};
  const TEXT={
    nl:{kind:{html:'Webpagina',markdown:'Document',svg:'Tekening',png:'Afbeelding',webp:'Afbeelding'},
      noun:'Artifact',open:'Openen',close:'Sluiten',download:'Downloaden',share:'Delen',
      shareLead:'Maak een link waarmee iemand anders alleen dit artifact kan bekijken.',
      shareNet:'De link werkt binnen het Synthwave-netwerk.',
      days:{1:'1 dag',7:'7 dagen',30:'30 dagen'},validFor:'Geldig',make:'Link maken',making:'Bezig',
      copy:'Kopiëren',copied:'Gekopieerd',linkReady:'Link gemaakt. Je ziet hem alleen nu; bewaar hem als je hem later nodig hebt.',
      unavailable:'Dit artifact is niet beschikbaar.',ownerOnly:'Alleen de maker kan dit artifact openen.',
      offline:'De artifact-service is nu niet bereikbaar.',failed:'Er ging iets mis. Probeer het opnieuw.',
      loading:'Wordt geladen'},
    en:{kind:{html:'Web page',markdown:'Document',svg:'Drawing',png:'Image',webp:'Image'},
      noun:'Artifact',open:'Open',close:'Close',download:'Download',share:'Share',
      shareLead:'Create a link that lets someone else view only this artifact.',
      shareNet:'The link works inside the Synthwave network.',
      days:{1:'1 day',7:'7 days',30:'30 days'},validFor:'Valid for',make:'Create link',making:'Working',
      copy:'Copy',copied:'Copied',linkReady:'Link created. It is shown only now; keep it if you need it later.',
      unavailable:'This artifact is not available.',ownerOnly:'Only the person who made it can open this artifact.',
      offline:'The artifact service cannot be reached right now.',failed:'Something went wrong. Please try again.',
      loading:'Loading'},
  };
  function lang(){
    const l=String((typeof _currentLang!=='undefined'&&_currentLang)||document.documentElement.lang||navigator.language||'en').toLowerCase();
    return l.startsWith('nl')?'nl':'en';
  }
  function t(key){return (TEXT[lang()]||TEXT.en)[key];}
  const SVG_NS='http://www.w3.org/2000/svg';
  const ICON={
    page:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    code:'<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
    image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>',
    pen:'<path d="M4 20l4-1 11-11-3-3L5 16z"/>',
    expand:'<path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/>',
    download:'<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    link:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    close:'<path d="M6 6l12 12M18 6L6 18"/>',
  };
  function icon(name){
    const s=document.createElementNS(SVG_NS,'svg');
    s.setAttribute('viewBox','0 0 24 24');s.setAttribute('class','iui-ico');s.setAttribute('aria-hidden','true');
    s.innerHTML=ICON[name]||ICON.page;  // fixed strings only
    return s;
  }
  function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
  function button(cls,ico,label,withText){
    const b=el('button','iui-btn'+(withText?' iui-btn--text':'')+(cls?' '+cls:''));
    b.type='button';b.title=label;b.setAttribute('aria-label',label);
    if(ico)b.appendChild(icon(ico));
    if(withText)b.appendChild(el('span','iui-btn-label',label));
    return b;
  }
  function kindIcon(kind){return kind==='html'?'code':kind==='svg'?'pen':(kind==='png'||kind==='webp')?'image':'page';}
  function theme(){
    const r=document.documentElement;
    if(r.classList.contains('dark')) return 'dark';
    if(r.classList.contains('light')||r.dataset.theme==='light') return 'light';
    try{
      const m=getComputedStyle(document.body).backgroundColor.match(/\d+(\.\d+)?/g);
      if(m&&m.length>=3){const [R,G,B]=m.map(Number);return (0.2126*R+0.7152*G+0.0722*B)/255<0.45?'dark':'light';}
    }catch(_){}
    return 'light';
  }
  function frameUrl(id){return 'api/artifacts/'+id+'/frame?theme='+theme();}
  function toast(msg){try{if(typeof showToast==='function')showToast(msg,2600);}catch(_){}}

  function parse(code){
    let spec;
    try{spec=JSON.parse(String(code||'').trim());}catch(_){return null;}
    if(!spec||typeof spec!=='object'||Array.isArray(spec)) return null;
    const id=String(spec.id||spec.artifact_id||'').trim();
    if(!ID_RE.test(id)) return null;
    const kind=['html','markdown','svg','png','webp'].includes(spec.kind)?spec.kind:'';
    const title=String(spec.title||'').replace(/[\u0000-\u001f]+/g,' ').trim().slice(0,200);
    return {id:id.toLowerCase(),kind,title};
  }
  function accepts(code){return !!parse(code);}

  function makeFrame(id,title){
    const f=document.createElement('iframe');
    f.className='spa-frame';
    f.setAttribute('sandbox','allow-scripts');
    f.setAttribute('referrerpolicy','no-referrer');
    f.setAttribute('loading','lazy');
    f.setAttribute('title',title||t('noun'));
    f.src=frameUrl(id);
    return f;
  }

  let fullOpen=null;
  function openFull(spec){
    closeFull();
    const wrap=el('div','spa-full');wrap.setAttribute('role','dialog');wrap.setAttribute('aria-modal','true');
    wrap.setAttribute('aria-label',spec.title||t('noun'));
    const bar=el('div','spa-full-bar');
    const badge=el('span','iui-badge');badge.appendChild(icon(kindIcon(spec.kind)));
    bar.appendChild(badge);
    bar.appendChild(el('span','iui-title',spec.title||t('noun')));
    const actions=el('div','iui-actions');
    const dl=button('', 'download', t('download'), false);dl.addEventListener('click',()=>download(spec));
    const close=button('spa-full-close','close',t('close'),true);close.addEventListener('click',closeFull);
    actions.appendChild(dl);actions.appendChild(close);bar.appendChild(actions);
    wrap.appendChild(bar);
    const stage=el('div','spa-full-stage');wrap.dataset.artifactId=spec.id;stage.appendChild(makeFrame(spec.id,spec.title));wrap.appendChild(stage);
    const onKey=ev=>{if(ev.key==='Escape'){ev.preventDefault();closeFull();}};
    document.addEventListener('keydown',onKey,true);
    const prevFocus=document.activeElement;
    fullOpen={wrap,onKey,prevFocus};
    document.body.appendChild(wrap);
    document.documentElement.classList.add('spa-full-open');
    close.focus();
  }
  function closeFull(){
    if(!fullOpen) return;
    document.removeEventListener('keydown',fullOpen.onKey,true);
    fullOpen.wrap.remove();
    document.documentElement.classList.remove('spa-full-open');
    try{if(fullOpen.prevFocus&&fullOpen.prevFocus.focus)fullOpen.prevFocus.focus();}catch(_){}
    fullOpen=null;
  }
  function download(spec){
    const a=document.createElement('a');
    a.href='api/artifacts/'+spec.id+'/download';a.rel='noopener noreferrer';a.download='';
    document.body.appendChild(a);a.click();a.remove();
  }

  function sharePanel(card,spec){
    let panel=card.querySelector('.spa-share');
    if(panel){panel.hidden=!panel.hidden;return;}
    panel=el('div','spa-share');
    panel.appendChild(el('p','spa-share-lead',t('shareLead')+' '+t('shareNet')));
    const row=el('div','spa-share-row');
    const label=el('label','spa-share-label',t('validFor'));
    const sel=document.createElement('select');sel.className='spa-share-select';
    const days=t('days');
    [1,7,30].forEach(d=>{const o=document.createElement('option');o.value=String(d*24);o.textContent=days[d];if(d===7)o.selected=true;sel.appendChild(o);});
    label.appendChild(sel);row.appendChild(label);
    const make=el('button','spa-share-make',t('make'));make.type='button';row.appendChild(make);
    panel.appendChild(row);
    const out=el('div','spa-share-out');out.hidden=true;panel.appendChild(out);
    make.addEventListener('click',async ev=>{
      if(!ev.isTrusted) return;
      make.disabled=true;make.textContent=t('making');
      try{
        const res=await api('/api/artifacts/'+spec.id+'/share',{method:'POST',body:JSON.stringify({expires_in_hours:Number(sel.value)}),retries:0,timeoutToast:false});
        if(!res||!res.url) throw new Error('no url');
        out.textContent='';out.hidden=false;
        const input=document.createElement('input');input.className='spa-share-url';input.readOnly=true;input.value=String(res.url);
        input.addEventListener('focus',()=>input.select());
        const copy=el('button','spa-share-copy',t('copy'));copy.type='button';
        copy.addEventListener('click',async()=>{
          try{await navigator.clipboard.writeText(input.value);copy.textContent=t('copied');setTimeout(()=>{copy.textContent=t('copy');},1600);}
          catch(_){input.focus();input.select();}
        });
        const line=el('div','spa-share-row');line.appendChild(input);line.appendChild(copy);
        out.appendChild(line);out.appendChild(el('p','spa-share-note',t('linkReady')));
        row.hidden=true;
      }catch(_){
        toast(t('failed'));
      }finally{make.disabled=false;make.textContent=t('make');}
    });
    card.appendChild(panel);
  }

  function unavailable(card,stage,status){
    card.dataset.state='unavailable';
    stage.textContent='';
    stage.classList.add('spa-stage--note');
    stage.appendChild(el('p','spa-note',status===404?t('ownerOnly'):status===503?t('offline'):t('unavailable')));
    card.querySelectorAll('.spa-act').forEach(b=>{b.disabled=true;});
  }

  function render(block){
    const spec=parse(block.textContent||'');
    const inAssistant=block.closest('.assistant-turn,.msg-row[data-role="assistant"],#liveAssistantTurn');
    if(!spec||!inAssistant){
      const pre=document.createElement('pre');const c=document.createElement('code');c.textContent=block.textContent||'';pre.appendChild(c);block.replaceWith(pre);
      return;
    }
    block.textContent='';
    const card=el('div','iui-card spa-card');card.dataset.artifactId=spec.id;
    const head=el('div','iui-head spa-head');
    const badge=el('span','iui-badge');badge.appendChild(icon(kindIcon(spec.kind)));head.appendChild(badge);
    const titles=el('div','spa-titles');
    const title=el('span','iui-title',spec.title||t('noun'));
    const sub=el('span','spa-sub',t('noun')+(spec.kind?' · '+t('kind')[spec.kind]:''));
    titles.appendChild(title);titles.appendChild(sub);head.appendChild(titles);
    const actions=el('div','iui-actions');
    const open=button('spa-act','expand',t('open'),true);
    const dl=button('spa-act','download',t('download'),false);
    const sh=button('spa-act','link',t('share'),false);
    actions.appendChild(sh);actions.appendChild(dl);actions.appendChild(open);head.appendChild(actions);
    card.appendChild(head);
    const stage=el('div','iui-stage spa-stage');
    stage.style.height=(HEIGHT[spec.kind]||460)+'px';
    card.appendChild(stage);
    block.appendChild(card);

    open.addEventListener('click',()=>openFull(spec));
    dl.addEventListener('click',()=>download(spec));
    sh.addEventListener('click',()=>sharePanel(card,spec));

    // The server is the source of truth for title, kind and access.
    fetch('api/artifacts/'+spec.id,{credentials:'include',cache:'no-store'}).then(async res=>{
      if(!res.ok){unavailable(card,stage,res.status);return;}
      const data=await res.json();
      const a=data&&data.artifact||{};
      if(a.title){spec.title=String(a.title).slice(0,200);title.textContent=spec.title;}
      if(a.kind&&TEXT.en.kind[a.kind]){spec.kind=a.kind;sub.textContent=t('noun')+' · '+t('kind')[a.kind];badge.textContent='';badge.appendChild(icon(kindIcon(a.kind)));
        stage.style.height=(HEIGHT[a.kind]||460)+'px';}
      stage.appendChild(makeFrame(spec.id,spec.title));
    }).catch(()=>unavailable(card,stage,503));
  }

  // Theme changes reload previews so light and dark stay readable.
  if(typeof MutationObserver==='function'){
    let last=null;
    new MutationObserver(()=>{
      const now=theme();if(now===last) return;last=now;
      document.querySelectorAll('.spa-frame').forEach(f=>{
        const card=f.closest('[data-artifact-id]');const id=card?card.dataset.artifactId:'';
        if(id&&ID_RE.test(id)) f.src=frameUrl(id);
      });
    }).observe(document.documentElement,{attributes:true,attributeFilter:['class','data-theme']});
    last=theme();
  }

  return {accepts,render,parse,closeFull};
})();

function synthpulseArtifactAccepts(code){return _spa.accepts(code);}
function synthpulseArtifactRender(block){_spa.render(block);}
