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
// frame with postMessage, and every message back is matched to the window of
// a known iframe. Nothing the widget sends can act for the user on its own:
// a follow-up question is shown in the card and only sent after a click on
// the host's own button.
//
// A questions form (```form, ```vraag, ```vragen, ```questions) is JSON too,
// but the chat draws it itself, outside any frame, with textContent only; the
// answers go out as the user's next message through the reply chips' path.
//
// Data blocks (```table, ```csv, ```chart, ```map, ```kpi, ```timeline and
// their Dutch names)
// hold JSON or CSV instead of code. The chat checks them with SWKit.build()
// (static/interactive-ui/kit-core.js) and sends only the cleaned spec to a
// second frame, static/interactive-ui/kit.html, which draws it with fixed
// renderers and never runs model code (`sandbox allow-scripts`, scripts by
// hash). Maps first get their coordinates from POST /api/map/resolve through
// static/interactive_ui_map.js. The card, menu, full screen, height cache and
// saved settings are the same for both kinds.
//
// Globals: interactiveUiFenceAccepts, renderInteractiveUiBlocks,
// interactiveUiStreamTick, parseInteractiveUiSource. Internals in _iui.

const _iui=(function(){
  const FRAME_URL='static/interactive-ui/frame.html';
  const KIT_URL='static/interactive-ui/kit.html';
  const KIT_STREAM_H={table:300,chart:380,map:460,kpi:150,timeline:340};
  const KIT_ICON={table:'table',chart:'chart',map:'pin',kpi:'gauge',timeline:'gantt'};
  // Kinds registered from static/interactive-ui/kinds/*.js bring their own height, icon and names.
  function kitExtra(kind){const K=kits();return K&&typeof K.extra==='function'?K.extra(kind):null;}
  function kitStreamH(kind){const x=kitExtra(kind);return KIT_STREAM_H[kind]||(x&&Number(x.streamHeight))||300;}
  function kitIcon(kind){const x=kitExtra(kind);return KIT_ICON[kind]||(x&&typeof x.icon==="string"&&ICON[x.icon]?x.icon:"spark");}
  const KIT_DATA_MAX=200*1024;
  function kits(){return typeof SWKit!=='undefined'&&SWKit&&typeof SWKit.build==='function'?SWKit:null;}
  function kitKindOf(lang){const K=kits();return K?K.kitKind(lang):'';}
  // The data fence named by a code element's classes ('' when there is none).
  function kitFenceOf(cls){return String(cls||'').split(/\s+/).map(t=>t.replace(/^language-/,'')).find(t=>t&&kitKindOf(t))||'';}
  const FENCE_LANGS=new Set(['interactive-ui','interactive','iui']);
  const CHIP_LANGS=new Set(['suggestions','replies']);
  const CDN_ORIGINS=new Set(['https://cdn.jsdelivr.net','https://unpkg.com','https://cdnjs.cloudflare.com','https://esm.sh']);
  const STYLE_ORIGINS=new Set([...CDN_ORIGINS,'https://fonts.googleapis.com']);
  const MAX_SOURCE=200*1024;
  const MIN_H=80, DEFAULT_H=360, STREAM_THROTTLE_MS=220, PROMPT_GAP_MS=1500, MAX_PENDING_PROMPTS=3;
  const byWindow=new Map();     // contentWindow -> controller
  const controllers=new Set();  // every mounted controller (a moved iframe gets a new window)
  const heightCache=new Map();  // hashed fingerprint -> last height (LRU, persisted per tab)
  const stateCache=new Map();   // source hash -> control values the user set
  const liveCards=new Map();    // first part of a streaming block -> its live card
  const STATE_PREFIX='iui-state:', H_KEY='iui-heights-v1', H_MAX=200;
  let seq=0, themeObserver=null, intersection=null, heightSaveTimer=0;

  function hashSource(src){
    let h=0x811c9dc5;const s=String(src||'');
    for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}
    return (h>>>0).toString(36)+'-'+s.length.toString(36);
  }
  try{const saved=JSON.parse(sessionStorage.getItem(H_KEY)||'{}');Object.keys(saved).forEach(k=>{if(saved[k]>0)heightCache.set(k,saved[k]);});}catch(_){}
  function rememberHeight(key,h){
    if(!key||!(h>0)) return;
    heightCache.delete(key);heightCache.set(key,h);
    while(heightCache.size>H_MAX) heightCache.delete(heightCache.keys().next().value);
    clearTimeout(heightSaveTimer);
    heightSaveTimer=setTimeout(()=>{try{sessionStorage.setItem(H_KEY,JSON.stringify(Object.fromEntries(heightCache)));}catch(_){}},500);
  }
  function loadState(key){
    if(!key) return null;
    if(stateCache.has(key)) return stateCache.get(key);
    try{const raw=sessionStorage.getItem(STATE_PREFIX+key);if(raw){const v=JSON.parse(raw);stateCache.set(key,v);return v;}}catch(_){}
    return null;
  }
  function saveState(key,values){
    if(!key||!values||typeof values!=='object') return;
    const json=JSON.stringify(values);
    if(json.length>20000) return;
    stateCache.set(key,values);
    try{sessionStorage.setItem(STATE_PREFIX+key,json);}catch(_){}
  }

  // ── Text ────────────────────────────────────────────────────────────────
  const TEXT={
    nl:{title:'Interactieve weergave',building:'Wordt gemaakt',
      restart:'Opnieuw starten',viewCode:'Code bekijken',hideCode:'Code verbergen',copyCode:'Code kopiëren',download:'Downloaden',
      devGroup:'Voor ontwikkelaars',full:'Volledig scherm',exitFull:'Sluiten',more:'Meer opties',repair:'Laat repareren',
      details:'Details',hideDetails:'Verberg details',dismiss:'Verbergen',copied:'Gekopieerd',sent:'Vraag verstuurd',
      errorLead:'Deze weergave werkt niet helemaal.',tooBig:'Deze weergave is te groot om te tonen.',
      removed:'Overgeslagen bron',ask:'Vraag uit deze weergave',send:'Versturen',cancel:'Annuleren',
      draftBusy:'Je concept staat nog in het invoerveld. Verstuur of wis dat eerst.',
      repairPrompt:title=>`Kun je "${title}" herstellen? Die werkt nog niet goed.`,
      sandboxNote:'Draait los van je account en de chat',chipsLabel:'Voorgestelde antwoorden',chipsBusy:'Even wachten tot het huidige antwoord klaar is.',
      kitNoun:{table:'tabel',chart:'grafiek',map:'kaart',kpi:'kerncijfers',timeline:'planning'},
      kitName:{table:'Tabel',chart:'Grafiek',map:'Kaart',kpi:'Kerncijfers',timeline:'Planning'},
      kitFail:noun=>noun==='kerncijfers'?'Deze kerncijfers konden niet worden gemaakt.':`Deze ${noun} kon niet worden gemaakt.`,downloadCsv:'Download als CSV',copyTable:'Kopieer als tabel',
      viewData:'Gegevens bekijken',hideData:'Gegevens verbergen',copyData:'Gegevens kopiëren',example:'Voorbeeld',
      kitRepairPrompt:(noun,title)=>noun==='kerncijfers'?`Kun je de kerncijfers "${title}" herstellen? Die kloppen nog niet.`:`Kun je de ${noun} "${title}" herstellen? Die klopt nog niet.`},
    en:{title:'Interactive view',building:'Building',
      restart:'Restart',viewCode:'View code',hideCode:'Hide code',copyCode:'Copy code',download:'Download',
      devGroup:'For developers',full:'Full screen',exitFull:'Close',more:'More options',repair:'Fix it',
      details:'Details',hideDetails:'Hide details',dismiss:'Dismiss',copied:'Copied',sent:'Question sent',
      errorLead:'This view is not fully working.',tooBig:'This view is too large to show.',
      removed:'Skipped source',ask:'Question from this view',send:'Send',cancel:'Cancel',
      draftBusy:'Your draft is still in the message box. Send or clear it first.',
      repairPrompt:title=>`Can you fix "${title}"? It is not working yet.`,
      sandboxNote:'Runs separately from your account and the chat',chipsLabel:'Suggested replies',chipsBusy:'Wait until the current reply is finished.',
      kitNoun:{table:'table',chart:'chart',map:'map',kpi:'key figures',timeline:'timeline'},
      kitName:{table:'Table',chart:'Chart',map:'Map',kpi:'Key figures',timeline:'Timeline'},
      kitFail:noun=>`This ${noun} could not be made.`,downloadCsv:'Download as CSV',copyTable:'Copy as table',
      viewData:'View data',hideData:'Hide data',copyData:'Copy data',example:'Example',
      kitRepairPrompt:(noun,title)=>`Can you fix the ${noun} "${title}"? It is not right yet.`},
  };
  function lang(){
    const l=String((typeof _currentLang!=='undefined'&&_currentLang)||document.documentElement.lang||navigator.language||'en').toLowerCase();
    return l.startsWith('nl')?'nl':'en';
  }
  function tx(key,...args){const v=(TEXT[lang()]||TEXT.en)[key];return typeof v==='function'?v(...args):(v||key);}
  function kitWord(field,kind){
    const m=(TEXT[lang()]||TEXT.en)[field];
    if(m&&m[kind]) return m[kind];
    const K=kits(), table=K&&(field==='kitNoun'?K.NOUN:field==='kitName'?K.NAME:null);
    const l=lang()==='nl'?'nl':'en';
    return (table&&table[l]&&table[l][kind])||kind;
  }
  function toast(msg){try{if(typeof showToast==='function')showToast(msg,2600);}catch(_){}}

  const ICON={
    flow:'<rect x="3" y="3" width="7" height="5" rx="1"/><rect x="14" y="16" width="7" height="5" rx="1"/><path d="M6.5 8v4.5h11V16"/>',
    compare:'<rect x="3" y="4" width="7.5" height="16" rx="1.5"/><rect x="13.5" y="4" width="7.5" height="16" rx="1.5"/><path d="M6 9h2M16.5 9h2M6 13h2M16.5 13h2"/>',
    funnel:'<path d="M3 4h18l-7 8v6l-4 2v-8z"/>',
    form:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    spark:'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    reload:'<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
    code:'<path d="M16 18l6-6-6-6"/><path d="M8 6l-6 6 6 6"/>',
    download:'<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
    expand:'<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    shrink:'<path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/>',
    copy:'<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    alert:'<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    wrench:'<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    close:'<path d="M18 6L6 18"/><path d="M6 6l12 12"/>',
    dots:'<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    send:'<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
    table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M9 10v10"/>',
    chart:'<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
    pin:'<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    gauge:'<rect x="3" y="5" width="8" height="6" rx="1.5"/><rect x="13" y="5" width="8" height="6" rx="1.5"/><rect x="3" y="13" width="8" height="6" rx="1.5"/><rect x="13" y="13" width="8" height="6" rx="1.5"/>',
    gantt:'<path d="M4 6h8"/><path d="M8 12h9"/><path d="M13 18h7"/><path d="M3 3v18"/>',
    check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    sheet:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/>',
  };
  function icon(name){return `<svg class="iui-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICON[name]||''}</svg>`;}
  function escHtml(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  // ── Source parsing ──────────────────────────────────────────────────────
  // Popular hosts models reach for, mapped to the same library on jsdelivr.
  const REWRITE=[
    [/^https:\/\/code\.jquery\.com\/jquery-(\d+\.\d+\.\d+)(?:\.min)?\.js$/i,m=>`https://cdn.jsdelivr.net/npm/jquery@${m[1]}/dist/jquery.min.js`],
    [/^https:\/\/cdn\.plot\.ly\/plotly-(\d+\.\d+\.\d+)(?:\.min)?\.js$/i,m=>`https://cdn.jsdelivr.net/npm/plotly.js-dist-min@${m[1]}/plotly.min.js`],
    [/^https:\/\/cdn\.plot\.ly\/plotly-latest(?:\.min)?\.js$/i,()=>'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2/plotly.min.js'],
    [/^https:\/\/cdn\.tailwindcss\.com\/?(?:\?.*)?$/i,()=>'https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'],
  ];
  function rewriteUrl(raw){const s=String(raw||'').trim();for(const [re,fn] of REWRITE){const m=re.exec(s);if(m)return fn(m);}return s;}
  function hostOf(raw){try{return new URL(String(raw||'').trim(),'https://invalid.invalid/').host||String(raw||'').slice(0,60);}catch(_){return String(raw||'').slice(0,60);}}
  function allowedUrl(raw,origins){
    try{const u=new URL(String(raw||'').trim(),'https://invalid.invalid/');return u.protocol==='https:'&&(origins||CDN_ORIGINS).has(u.origin)?u.href:null;}catch(_){return null;}
  }
  function attr(tag,name){
    const m=new RegExp('\\s'+name+'\\s*=\\s*("([^"]*)"|\'([^\']*)\'|([^\\s>]+))','i').exec(tag);
    return m?(m[2]!=null?m[2]:m[3]!=null?m[3]:m[4]):null;
  }
  function parse(source,opts){
    const final=!!(opts&&opts.final);
    let s=String(source||'').replace(/\u0000/g,'');
    const out={title:'',height:0,css:'',html:'',scripts:[],warnings:[],bytes:s.length,tooBig:s.length>MAX_SOURCE};
    if(out.tooBig) return out;
    const inert=[];
    // One left-to-right pass classifies comments and scripts first, so a
    // commented-out script never runs and tags inside script bodies are kept.
    s=s.replace(/<!--[\s\S]*?-->|<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi,(m,attrs,body)=>{
      if(attrs===undefined){
        const meta=/^<!--\s*(title|height)\s*:([\s\S]*?)-->$/i.exec(m);
        if(meta){
          const v=meta[2].trim();
          if(meta[1].toLowerCase()==='title'&&!out.title) out.title=v.slice(0,120);
          else if(meta[1].toLowerCase()==='height'){const h=parseInt(v,10);if(h>0)out.height=Math.max(MIN_H,Math.min(h,2000));}
        }
        return '';
      }
      const tag='<script '+attrs+'>';
      const type=(attr(tag,'type')||'').toLowerCase().trim();
      if(type&&type!=='module'&&type!=='text/javascript'&&type!=='application/javascript'){
        if(/json|template|text\//.test(type)){
          const id=attr(tag,'id');
          inert.push(`<script type="${type.replace(/[^a-z0-9/+.-]/g,'')}"${id?` id="${String(id).replace(/[^A-Za-z0-9_-]/g,'')}"`:''}>${body}<\/script>`);
          return '\u0000S'+(inert.length-1)+'\u0000';
        }
        return '';
      }
      const src=attr(tag,'src');
      if(src){const u=allowedUrl(rewriteUrl(src));if(u)out.scripts.push({src:u,type:type==='module'?'module':''});else out.warnings.push(tx('removed')+': '+hostOf(src));}
      else if(body.trim()) out.scripts.push({code:body,type:type==='module'?'module':''});
      return '';
    });
    if(!final){
      // Still streaming: whatever follows an unfinished script or comment waits.
      const cut=[s.search(/<script\b/i),s.search(/<!--/)].filter(i=>i>=0);
      if(cut.length) s=s.slice(0,Math.min(...cut));
    }
    // An SVG keeps its own <title>; only a document title names the card.
    const svgs=[];
    s=s.replace(/<svg\b[\s\S]*?<\/svg>/gi,m=>{svgs.push(m);return '\u0000V'+(svgs.length-1)+'\u0000';});
    if(!out.title){const m=/<title[^>]*>([\s\S]*?)<\/title>/i.exec(s);if(m)out.title=m[1].replace(/<[^>]+>/g,'').trim().slice(0,120);}
    s=s.replace(/<title[^>]*>[\s\S]*?<\/title>/gi,'')
      .replace(/<!doctype[^>]*>/gi,'').replace(/<\/?(html|head|body)\b[^>]*>/gi,'')
      .replace(/<meta\b[^>]*>/gi,'').replace(/<base\b[^>]*>/gi,'');
    const imports=[], css=[];
    s=s.replace(/<link\b[^>]*>/gi,(tag)=>{
      if(/rel\s*=\s*["']?stylesheet/i.test(tag)){
        const href=attr(tag,'href');
        const u=allowedUrl(rewriteUrl(href),STYLE_ORIGINS);
        if(u)imports.push(`@import url("${u.replace(/"/g,'%22')}");`);else out.warnings.push(tx('removed')+': '+hostOf(href));
      }
      return '';
    });
    s=s.replace(/<style\b[^>]*>([\s\S]*?)<\/style>/gi,(_,body)=>{css.push(body);return '';});
    if(!final){
      // An unfinished <style> already styles what is there; a half tag waits.
      const openStyle=/<style\b[^>]*>([\s\S]*)$/i.exec(s);
      if(openStyle){css.push(openStyle[1]);s=s.slice(0,openStyle.index);}
      s=s.replace(/<[^>]*$/,'');
      s=s.replace(/\u0000V\d*$/,'');
    }
    s=s.replace(/\u0000V(\d+)\u0000/g,(_,i)=>svgs[+i]||'').replace(/\u0000S(\d+)\u0000/g,(_,i)=>inert[+i]||'');
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
    else if(root.classList.contains('light')||root.dataset.theme==='light'||typeof _resolvedThemeBaseDark!=='undefined') mode='light';
    else{
      const lum=luminance(document.body?getComputedStyle(document.body).backgroundColor:'');
      mode=lum==null||lum<0.45?'dark':'light';
    }
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
    if(ctrl.kit){pushKit(ctrl);return;}
    if(!ctrl.ready||ctrl.sentFinal) return;
    const p=ctrl.parsed;
    if(!p||p.tooBig) return;
    const restore=ctrl.final?loadState(ctrl.stateKey):null;
    postTo(ctrl,{type:'render',css:p.css,html:p.html,scripts:ctrl.final?p.scripts:[],final:ctrl.final,restore});
    if(ctrl.final) ctrl.sentFinal=true;
  }
  // A data block gets its cleaned spec (and, for a map, the resolved places)
  // as a structured clone: nothing the model wrote becomes code or markup.
  function kitDataFor(ctrl){
    const data=ctrl.kitData;
    if(!data) return null;
    try{if(JSON.stringify(data).length<=KIT_DATA_MAX) return data;}catch(_){}
    return Object.assign({},data,{places:(data.places||[]).map(p=>Object.assign({},p,{photo:undefined}))});
  }
  // A data block follows the language of the conversation when it says so.
  function kitLang(ctrl){const l=ctrl&&ctrl.parsed&&ctrl.parsed.spec&&String(ctrl.parsed.spec.lang||'').toLowerCase();return l==='nl'||l==='en'?l:lang();}
  function pushKit(ctrl){
    if(!ctrl.ready||ctrl.sentFinal||!ctrl.final) return;
    const p=ctrl.parsed;
    if(!p||!p.spec) return;
    if(ctrl.kit==='map'&&!ctrl.kitData){ensureMapData(ctrl);if(!ctrl.kitData) return;}
    postTo(ctrl,{type:'kit',kit:ctrl.kit,spec:p.spec,data:kitDataFor(ctrl),final:true,restore:loadState(ctrl.stateKey),lang:kitLang(ctrl)});
    ctrl.sentFinal=true;
  }
  function ensureMapData(ctrl){
    const p=ctrl.parsed, K=kits();
    if(ctrl.kit!=='map'||!ctrl.final||!p||!p.spec||!K||ctrl.kitData||ctrl.resolving) return;
    if(typeof interactiveUiMapResolve!=='function'){ctrl.kitData=K.mapLocalData(p.spec);return;}
    ctrl.resolving=true;
    if(ctrl.state!=='error') setState(ctrl,'building');
    const apply=data=>{
      ctrl.kitData=data&&typeof data==='object'?data:K.mapLocalData(p.spec);
      ctrl.sentFinal=false;
      pushKit(ctrl);
    };
    let first=true;
    Promise.resolve().then(()=>interactiveUiMapResolve(p.spec,ctrl.stateKey,{lang:kitLang(ctrl),onUpdate:data=>{if(!first)apply(data);}}))
      .then(data=>{first=false;ctrl.resolving=false;if(ctrl.state==='building')setState(ctrl,ctrl.rendered?'ready':'loading');apply(data);},
        ()=>{first=false;ctrl.resolving=false;if(ctrl.state==='building')setState(ctrl,'loading');apply(K.mapLocalData(p.spec,'later'));
          // Busy or offline: try once more a little later.
          if(!ctrl.mapRetried){ctrl.mapRetried=true;setTimeout(()=>{if(ctrl.card.isConnected){ctrl.kitData=null;ensureMapData(ctrl);}},8000);}});
  }
  function onMessage(e){
    const data=e&&e.data;
    if(!data||data.iui!==1||typeof data.type!=='string') return;
    // Our frames always run in an opaque origin.
    if(e.origin!=='null') return;
    const ctrl=byWindow.get(e.source)||adopt(e.source);
    if(!ctrl) return;
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
        ctrl.rendered=true;
        setState(ctrl,ctrl.errors.length?'error':(ctrl.resolving?'building':'ready'));
        revealIfReady(ctrl);
        break;
      case 'error':
        addError(ctrl,String(data.message||''),String(data.detail||''));
        break;
      case 'state':
        if(ctrl.final&&ctrl.stateKey) saveState(ctrl.stateKey,data.values);
        break;
      case 'prompt':
        if(!ctrl.kit) offerPrompt(ctrl,String(data.text||''));
        break;
      case 'copy':
        copyFromWidget(String(data.text||''));
        break;
      case 'open':
        openLink(String(data.url||''));
        break;
      case 'key':
        if(data.key==='Escape'&&ctrl.card.classList.contains('iui-full')) toggleFull(ctrl,false);
        break;
      case 'log':
        try{console.warn('[interactive-ui]',String(data.message||'').slice(0,300));}catch(_){}
        break;
    }
  }
  // A frame that was moved in the DOM reloads with a new window; find its
  // controller by asking each live iframe for its current window.
  function adopt(win){
    prune();
    let found=null;
    controllers.forEach(c=>{if(c.iframe&&c.iframe.contentWindow===win)found=c;});
    if(found){byWindow.set(win,found);found.ready=false;found.sentFinal=false;}
    return found;
  }
  // Drop controllers whose card left the page a while ago.
  function prune(){
    const now=Date.now();
    controllers.forEach(c=>{
      if(c.card.isConnected){c.detachedAt=0;return;}
      if(!c.detachedAt){c.detachedAt=now;return;}
      if(now-c.detachedAt<30000) return;
      controllers.delete(c);
      byWindow.forEach((v,k)=>{if(v===c)byWindow.delete(k);});
      if(intersection) try{intersection.unobserve(c.card);}catch(_){}
      if(c.card.classList.contains('iui-full')) toggleFull(c,false);
    });
  }
  function openLink(url){
    if(!/^https?:\/\//i.test(url)) return;
    try{window.open(url,'_blank','noopener,noreferrer');}catch(_){}
  }
  function hostActive(){
    // A click inside the frame also activates this page (user activation
    // propagates to ancestors); a timer or load handler does not.
    try{return !navigator.userActivation||navigator.userActivation.isActive;}catch(_){return true;}
  }
  function copyText(text){
    if(!text) return;
    const done=()=>toast(tx('copied'));
    try{
      if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,()=>fallbackCopy(text,done));return;}
    }catch(_){}
    fallbackCopy(text,done);
  }
  function copyFromWidget(text){
    if(!text||!hostActive()) return;
    copyText(text.slice(0,20000));
  }
  function fallbackCopy(text,done){
    try{const ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();done();}catch(_){}
  }
  function cleanPrompt(text){
    return String(text||'').replace(/[\p{Cf}\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/gu,'')
      .replace(/^[\s/]+/,'').slice(0,4000).trim();
  }
  // A follow-up question from a widget is shown in the card; only a click on
  // the host's own Send button sends it.
  function offerPrompt(ctrl,text){
    text=cleanPrompt(text);
    if(!text||ctrl.rejectedPrompts>=MAX_PENDING_PROMPTS) return;
    if(ctrl.pendingPrompt) ctrl.rejectedPrompts=(ctrl.rejectedPrompts||0)+1;
    ctrl.pendingPrompt=text;
    ctrl.askText.textContent=text.length>300?text.slice(0,300)+'…':text;
    ctrl.askBar.hidden=false;
    if(hostActive()) try{ctrl.askSend.focus({preventScroll:true});}catch(_){}
  }
  function hideAsk(ctrl){ctrl.pendingPrompt='';ctrl.askBar.hidden=true;}
  function composerBusy(){
    const box=document.getElementById('msg');
    const files=(typeof S!=='undefined'&&S&&Array.isArray(S.pendingFiles))?S.pendingFiles.length:0;
    const sel=(typeof _pendingSelections!=='undefined'&&Array.isArray(_pendingSelections))?_pendingSelections.length:0;
    return !!((box&&box.value.trim())||files||sel);
  }
  function chatBusy(){
    try{return !!(typeof S!=='undefined'&&S&&(S.busy||S.activeStreamId));}catch(_){return false;}
  }
  // Returns false when it could not even try; onDone(ok) reports whether the
  // message really left (the composer was emptied by send()).
  function sendPrompt(text,onDone,opts){
    const box=document.getElementById('msg');
    if(!box||typeof window.send!=='function') return false;
    if(composerBusy()){toast(tx('draftBusy'));return false;}
    box.value=text;
    try{box.dispatchEvent(new Event('input',{bubbles:true}));}catch(_){}
    const settle=()=>{
      const ok=box.value.trim()!==String(text).trim();
      if(ok) toast(opts&&opts.sentToast||tx('sent'));
      else if(box.value.trim()===String(text).trim()){box.value='';try{box.dispatchEvent(new Event('input',{bubbles:true}));}catch(_){}}
      if(onDone) onDone(ok);
    };
    try{
      const r=window.send();
      if(r&&typeof r.then==='function') r.then(settle,()=>{if(onDone)onDone(false);});
      else settle();
    }catch(err){try{console.warn('[interactive-ui] follow-up failed',err);}catch(_){}if(onDone)onDone(false);}
    return true;
  }

  // ── Card ────────────────────────────────────────────────────────────────
  function fingerprint(src){return hashSource(String(src||'').slice(0,400));}
  function scroller(){return document.getElementById('messages');}
  function setHeight(ctrl,h){
    if(!(h>0)) return;
    ctrl.height=h;
    if(ctrl.card.classList.contains('iui-full')) return;
    if(ctrl.final) rememberHeight(ctrl.fp,h);
    const max=Math.max(320,Math.round((window.innerHeight||900)*0.86));
    const next=Math.max(MIN_H,Math.min(h,max));
    const prev=ctrl.stage.offsetHeight;
    const delta=next-prev;
    // Keep the reader's place when a card above the visible area resizes.
    const sc=scroller();
    const above=sc&&delta&&ctrl.card.isConnected&&ctrl.card.getBoundingClientRect().bottom<=sc.getBoundingClientRect().top+1;
    if(above){
      ctrl.stage.style.transition='none';
      ctrl.stage.style.height=next+'px';
      sc.scrollTop+=delta;
      requestAnimationFrame(()=>{ctrl.stage.style.transition='';});
    } else {
      ctrl.stage.style.height=next+'px';
    }
    ctrl.stage.classList.toggle('iui-stage--scroll',h>max);
  }
  function setState(ctrl,state){
    ctrl.state=state;
    ctrl.card.dataset.state=state;
    // The error bar explains problems; the header only says "building".
    const label=state==='building'?tx('building'):'';
    if(ctrl.status.textContent!==label) ctrl.status.textContent=label;
    ctrl.status.hidden=state!=='building';
  }
  function friendly(message){return String(message||'').replace(/^Uncaught\s+/,'').slice(0,240);}
  function addError(ctrl,message,detail){
    if(!message) return;
    if(ctrl.errors.some(e=>e.message===message)) return;
    ctrl.errors.push({message,detail});
    renderDetails(ctrl);
    ctrl.errorBar.hidden=false;
    setState(ctrl,'error');
  }
  // Skipped sources are not errors: they only show in the details.
  function renderDetails(ctrl){
    const lines=ctrl.errors.slice(0,5).map(e=>friendly(e.message)).concat((ctrl.parsed&&ctrl.parsed.warnings)||[]);
    ctrl.errorDetails.textContent=lines.join('\n');
  }
  function button(name,label,onClick,extra){
    const b=document.createElement('button');
    b.type='button';b.className='iui-btn'+(extra?' '+extra:'');
    b.title=label;b.setAttribute('aria-label',label);
    b.innerHTML=icon(name)+`<span class="iui-btn-label">${escHtml(label)}</span>`;
    b.addEventListener('click',ev=>{ev.preventDefault();ev.stopPropagation();onClick(b,ev);});
    return b;
  }
  function menuItem(name,label,onClick,extra){
    const b=document.createElement('button');
    b.type='button';b.className='iui-menu-item'+(extra?' '+extra:'');b.setAttribute('role','menuitem');b.tabIndex=-1;
    b.innerHTML=icon(name)+`<span>${escHtml(label)}</span>`;
    b.addEventListener('click',ev=>{ev.preventDefault();ev.stopPropagation();onClick(b);});
    return b;
  }
  let openMenu=null;
  function closeMenu(focusTrigger){
    if(!openMenu) return;
    const {menu,trigger}=openMenu;
    menu.hidden=true;trigger.setAttribute('aria-expanded','false');
    openMenu=null;
    window.removeEventListener('blur',onMenuBlur);
    window.removeEventListener('resize',onMenuBlur);
    if(focusTrigger) try{trigger.focus();}catch(_){}
  }
  function onMenuBlur(){closeMenu(false);}
  function openMenuFor(ctrl){
    if(openMenu&&openMenu.menu===ctrl.menu){closeMenu(true);return;}
    closeMenu(false);
    ctrl.codeItem.querySelector('span').textContent=ctrl.kit?(ctrl.sourceBox.hidden?tx('viewData'):tx('hideData')):(ctrl.sourceBox.hidden?tx('viewCode'):tx('hideCode'));
    ctrl.menu.hidden=false;
    ctrl.moreBtn.setAttribute('aria-expanded','true');
    openMenu={menu:ctrl.menu,trigger:ctrl.moreBtn};
    // A click inside a frame never reaches this document; the window blurs.
    window.addEventListener('blur',onMenuBlur);
    window.addEventListener('resize',onMenuBlur);
    const first=ctrl.menu.querySelector('.iui-menu-item');
    if(first) first.focus();
  }

  function createController(source,opts){
    const final=!!(opts&&opts.final);
    const kit=(opts&&opts.kit)||'', fence=(opts&&opts.fence)||kit;
    const card=document.createElement('div');
    card.className='iui-card'+(kit?' iui-kit iui-kit--'+kit:'');
    card.dataset.iuiCard=String(++seq);
    card.setAttribute('role','group');
    const head=document.createElement('div');head.className='iui-head';
    const badge=document.createElement('span');badge.className='iui-badge';badge.innerHTML=icon(kitIcon(kit));
    const titleEl=document.createElement('span');titleEl.className='iui-title';
    const pill=document.createElement('span');pill.className='iui-pill';pill.textContent=tx('example');pill.hidden=true;
    const status=document.createElement('span');status.className='iui-status';
    const actions=document.createElement('div');actions.className='iui-actions';
    head.append(badge,titleEl,pill,status,actions);
    const stage=document.createElement('div');stage.className='iui-stage';
    const skeleton=document.createElement('div');skeleton.className='iui-skeleton';skeleton.innerHTML='<span></span><span></span><span></span>';
    stage.appendChild(skeleton);
    // Follow-up question offered by the widget, sent only by the host button.
    const askBar=document.createElement('div');askBar.className='iui-ask';askBar.hidden=true;
    const askLabel=document.createElement('span');askLabel.className='iui-ask-label';askLabel.textContent=tx('ask');
    const askText=document.createElement('span');askText.className='iui-ask-text';
    const askBody=document.createElement('div');askBody.className='iui-ask-body';askBody.append(askLabel,askText);
    askBar.append(askBody);
    const errorBar=document.createElement('div');errorBar.className='iui-error';errorBar.hidden=true;
    errorBar.setAttribute('role','status');
    const errorLead=document.createElement('span');errorLead.className='iui-error-text';errorLead.textContent=tx('errorLead');
    const errorDetails=document.createElement('pre');errorDetails.className='iui-error-details';errorDetails.hidden=true;
    errorBar.innerHTML=icon('alert');errorBar.appendChild(errorLead);
    const sourceBox=document.createElement('div');sourceBox.className='iui-source';sourceBox.hidden=true;
    const pre=document.createElement('pre');const code=document.createElement('code');code.className='language-html';pre.appendChild(code);
    sourceBox.appendChild(pre);
    card.append(head,stage,askBar,errorBar,errorDetails,sourceBox);

    if(kit) code.className='language-'+(fence==='csv'?'csv':'json');
    const ctrl={card,head,titleEl,pill,status,actions,stage,skeleton,askBar,askText,errorBar,errorLead,errorDetails,sourceBox,code,
      iframe:null,ready:false,final,sentFinal:false,rendered:false,source:'',parsed:null,errors:[],state:'loading',
      fp:'',stateKey:'',height:0,lastPrompt:0,pendingPrompt:'',rejectedPrompts:0,lastTick:0,tickTimer:0,
      mounted:false,mountedAt:0,detachedAt:0,kit,fence,kitData:null,resolving:false};
    if(kit) errorLead.textContent=tx('kitFail',kitWord('kitNoun',kit));

    const askSend=button('send',tx('send'),(b,ev)=>{
      if(!ev||!ev.isTrusted) return;
      const now=Date.now();
      if(now-ctrl.lastPrompt<PROMPT_GAP_MS||!ctrl.pendingPrompt) return;
      if(chatBusy()){toast(tx('chipsBusy'));return;}
      if(sendPrompt(ctrl.pendingPrompt)){ctrl.lastPrompt=now;hideAsk(ctrl);}
    },'iui-btn--text iui-btn--primary');
    const askCancel=button('close',tx('cancel'),()=>{ctrl.rejectedPrompts=(ctrl.rejectedPrompts||0)+1;hideAsk(ctrl);},'iui-btn--text iui-btn--quiet');
    askBar.append(askSend,askCancel);
    ctrl.askSend=askSend;

    const repair=button('wrench',tx('repair'),(b,ev)=>{
      if(!ev||!ev.isTrusted) return;
      // While an answer runs the request would be queued or used to steer, where the
      // hidden report is not stripped; and one request per error is enough.
      if(chatBusy()){toast(tx('chipsBusy'));return;}
      if(b.dataset.sent==='1') return;
      b.dataset.sent='1';b.disabled=true;
      const first=ctrl.errors[0]?friendly(ctrl.errors[0].message).slice(0,240):'';
      // The user sees one plain sentence; the error and the block type go to the
      // agent in a report the chat hides from the bubble.
      const report=(fence,msg)=>`\n\n[View report]\nBlock: ${fence}\nProblem: ${String(msg||'unknown').replace(/\[\/?View report\]/g,'')}\nFix the cause and send the complete ${fence} block again.\n[/View report]`;
      if(ctrl.kit){
        const msg=first||((ctrl.parsed&&ctrl.parsed.warnings||[])[0]||'');
        if(!sendPrompt(tx('kitRepairPrompt',kitWord('kitNoun',ctrl.kit),ctrl.parsed&&ctrl.parsed.title||kitWord('kitName',ctrl.kit))+report(ctrl.fence||ctrl.kit,msg))){b.dataset.sent='';b.disabled=false;}
        return;
      }
      if(!sendPrompt(tx('repairPrompt',ctrl.parsed&&ctrl.parsed.title||tx('title'))+report('interactive-ui',first))){b.dataset.sent='';b.disabled=false;}
    },'iui-btn--text');
    const detailsBtn=button('code',tx('details'),b=>{
      errorDetails.hidden=!errorDetails.hidden;
      b.querySelector('.iui-btn-label').textContent=errorDetails.hidden?tx('details'):tx('hideDetails');
      b.setAttribute('aria-expanded',String(!errorDetails.hidden));
    },'iui-btn--text iui-btn--quiet');
    detailsBtn.setAttribute('aria-expanded','false');
    const dismiss=button('close',tx('dismiss'),()=>{errorBar.hidden=true;errorDetails.hidden=true;},'iui-btn--icon');
    errorBar.append(repair,detailsBtn,dismiss);

    // Header: full screen stays visible, everything else lives in one menu.
    const fullBtn=button('expand',tx('full'),()=>toggleFull(ctrl));
    const moreBtn=button('dots',tx('more'),()=>openMenuFor(ctrl));
    moreBtn.setAttribute('aria-haspopup','menu');moreBtn.setAttribute('aria-expanded','false');
    const menu=document.createElement('div');menu.className='iui-menu';menu.hidden=true;menu.setAttribute('role','menu');
    menu.setAttribute('aria-label',tx('more'));
    const pick=fn=>b=>{closeMenu(true);fn(b);};
    const dlItem=menuItem('download',tx('download'),pick(()=>download(ctrl)));
    const restartItem=menuItem('reload',tx('restart'),pick(()=>reload(ctrl)));
    const sep=document.createElement('div');sep.className='iui-menu-sep';sep.setAttribute('role','separator');
    const group=document.createElement('div');group.className='iui-menu-group';group.textContent=tx('devGroup');group.setAttribute('aria-hidden','true');
    const codeItem=menuItem('code',kit?tx('viewData'):tx('viewCode'),pick(()=>{
      sourceBox.hidden=!sourceBox.hidden;
      if(!sourceBox.hidden){code.textContent=ctrl.source;try{if(typeof Prism!=='undefined'&&Prism.highlightElement)Prism.highlightElement(code);}catch(_){}}
    }),'iui-menu-dev');
    const copyItem=menuItem('copy',kit?tx('copyData'):tx('copyCode'),pick(()=>copyText(ctrl.source)),'iui-menu-dev');
    if(kit){
      // Data blocks: exports first, no sandbox note (nothing of the model runs).
      const csvItem=menuItem('sheet',tx('downloadCsv'),pick(()=>downloadCsv(ctrl)));
      const tsvItem=menuItem('copy',tx('copyTable'),pick(()=>copyText(kitExport(ctrl,'tsv'))));
      menu.append(csvItem,tsvItem,dlItem,restartItem,sep,group,codeItem,copyItem);
    } else {
      const note=document.createElement('div');note.className='iui-menu-note';note.innerHTML=icon('lock')+`<span>${escHtml(tx('sandboxNote'))}</span>`;
      menu.append(dlItem,restartItem,sep,group,codeItem,copyItem,note);
    }
    menu.addEventListener('keydown',ev=>{
      const items=[...menu.querySelectorAll('.iui-menu-item')];
      const at=items.indexOf(document.activeElement);
      if(ev.key==='Escape'){ev.preventDefault();ev.stopPropagation();closeMenu(true);}
      else if(ev.key==='ArrowDown'){ev.preventDefault();(items[at+1]||items[0]).focus();}
      else if(ev.key==='ArrowUp'){ev.preventDefault();(items[at-1]||items[items.length-1]).focus();}
      else if(ev.key==='Home'){ev.preventDefault();items[0].focus();}
      else if(ev.key==='End'){ev.preventDefault();items[items.length-1].focus();}
      else if(ev.key==='Tab'){closeMenu(false);}
    });
    Object.assign(ctrl,{fullBtn,moreBtn,menu,codeItem});
    actions.append(moreBtn,fullBtn,menu);
    update(ctrl,source,final);
    return ctrl;
  }
  function kitParse(ctrl){
    const K=kits(), kind=ctrl.kit;
    const base={kit:kind,css:'',html:'',scripts:[],warnings:[],errors:[],spec:null,tooBig:false,title:'',height:kitStreamH(kind)};
    if(!K) return Object.assign(base,{errors:['kit unavailable']});
    if(!ctrl.final) return Object.assign(base,{title:K.streamingTitle(ctrl.source)});
    const r=K.build(kind,ctrl.source,{lang:lang(),fence:ctrl.fence});
    return Object.assign(base,{title:r.title,height:r.estHeight,spec:r.spec,errors:r.errors,warnings:r.warnings});
  }
  function update(ctrl,source,final){
    ctrl.source=String(source||'');
    ctrl.final=!!final;
    ctrl.parsed=ctrl.kit?kitParse(ctrl):parse(ctrl.source,{final:ctrl.final});
    if(!ctrl.fp||!ctrl.final) ctrl.fp=fingerprint(ctrl.source);
    ctrl.stateKey=ctrl.final?hashSource(ctrl.source.trim()):'';
    const p=ctrl.parsed;
    const title=p.title||(ctrl.kit?kitWord('kitName',ctrl.kit):tx('title'));
    ctrl.pill.hidden=!(p.spec&&p.spec.example);
    if(ctrl.kit) ctrl.pill.textContent=(TEXT[kitLang(ctrl)]||TEXT.en).example;
    if(ctrl.titleEl.textContent!==title){ctrl.titleEl.textContent=title;ctrl.titleEl.title=title;}
    ctrl.card.setAttribute('aria-label',title);
    ctrl.moreBtn.hidden=!ctrl.final;
    if(!ctrl.sourceBox.hidden) ctrl.code.textContent=ctrl.source;
    if(p.tooBig){addError(ctrl,tx('tooBig'),'');return;}
    if(ctrl.kit&&ctrl.final&&!p.spec){
      // Nothing can be drawn: one plain sentence and the repair button, no empty frame.
      ctrl.card.classList.add('iui-kit-fatal');
      addError(ctrl,p.errors[0]||tx('kitFail',kitWord('kitNoun',ctrl.kit)),'');
      return;
    }
    renderDetails(ctrl);
    if(!ctrl.height){
      const cached=heightCache.get(ctrl.fp);
      ctrl.stage.style.height=(cached||p.height||DEFAULT_H)+'px';
      if(cached) ctrl.skeleton.classList.add('is-quiet');
    }
    if(ctrl.state!=='error') setState(ctrl,ctrl.final?(ctrl.rendered?'ready':'loading'):'building');
    if(ctrl.kit==='map'&&ctrl.mounted) ensureMapData(ctrl);
    if(ctrl.mounted) pushRender(ctrl);
    revealIfReady(ctrl);
  }
  function mount(ctrl){
    if(ctrl.mounted) return;
    ctrl.mounted=true;
    const iframe=document.createElement('iframe');
    iframe.className='iui-frame';
    if(ctrl.kit) iframe.setAttribute('sandbox','allow-scripts');
    else iframe.setAttribute('sandbox','allow-scripts allow-forms allow-popups');
    iframe.setAttribute('referrerpolicy','no-referrer');
    iframe.setAttribute('title',ctrl.parsed&&ctrl.parsed.title||tx('title'));
    iframe.src=(ctrl.kit?KIT_URL:FRAME_URL)+'?v='+encodeURIComponent(String((typeof WEBUI_VERSION!=='undefined'&&WEBUI_VERSION)||'1'));
    iframe.addEventListener('load',()=>{ctrl.frameLoaded=true;revealIfReady(ctrl);});
    ctrl.iframe=iframe;
    ctrl.mountedAt=Date.now();
    controllers.add(ctrl);
    ctrl.stage.appendChild(iframe);
    if(iframe.contentWindow) byWindow.set(iframe.contentWindow,ctrl);
    watchTheme();
  }
  // Keep the placeholder until the app has something to show.
  function revealIfReady(ctrl){
    if(ctrl.kit){if(ctrl.rendered) ctrl.skeleton.classList.add('is-gone');return;}
    if(ctrl.frameLoaded&&(ctrl.final||(ctrl.parsed&&ctrl.parsed.html.trim()))) ctrl.skeleton.classList.add('is-gone');
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
    Object.assign(ctrl,{iframe:null,mounted:false,ready:false,sentFinal:false,rendered:false,frameLoaded:false,errors:ctrl.kit&&!ctrl.parsed.spec?ctrl.errors:[]});
    ctrl.errorBar.hidden=true;ctrl.errorDetails.hidden=true;hideAsk(ctrl);
    ctrl.skeleton.classList.remove('is-gone');
    setState(ctrl,'loading');
    renderDetails(ctrl);
    mount(ctrl);
  }
  // Full screen is an overlay of the card itself (the iframe never moves, so
  // it never reloads); the message row and list stop clipping it meanwhile.
  function toggleFull(ctrl,force){
    const on=force===undefined?!ctrl.card.classList.contains('iui-full'):!!force;
    if(on===ctrl.card.classList.contains('iui-full')) return;
    closeMenu(false);
    ctrl.card.classList.toggle('iui-full',on);
    document.documentElement.classList.toggle('iui-has-full',on);
    const row=ctrl.card.closest('.msg-row,.assistant-turn,.assistant-segment');
    const b=ctrl.fullBtn;
    b.innerHTML=icon(on?'close':'expand')+`<span class="iui-btn-label">${escHtml(on?tx('exitFull'):tx('full'))}</span>`;
    b.title=on?tx('exitFull'):tx('full');b.setAttribute('aria-label',b.title);
    b.classList.toggle('iui-btn--text',on);
    if(on){
      ctrl._fullRow=row;if(row)row.classList.add('iui-row-full');
      ctrl._returnFocus=document.activeElement;
      ctrl.card.setAttribute('role','dialog');ctrl.card.setAttribute('aria-modal','true');
      ctrl.stage.style.height='';
      ctrl._esc=ev=>{
        if(ev.key==='Escape'){ev.preventDefault();toggleFull(ctrl,false);}
        else if(ev.key==='Tab'){
          // Keep focus inside the card while it covers the chat.
          const f=[...ctrl.card.querySelectorAll('button:not([hidden]):not(:disabled),iframe')].filter(x=>x.offsetParent!==null);
          if(!f.length) return;
          const i=f.indexOf(document.activeElement);
          if(ev.shiftKey&&i<=0){ev.preventDefault();f[f.length-1].focus();}
          else if(!ev.shiftKey&&i===f.length-1){ev.preventDefault();f[0].focus();}
        }
      };
      document.addEventListener('keydown',ctrl._esc,true);
      b.focus();
    } else {
      if(ctrl._fullRow) ctrl._fullRow.classList.remove('iui-row-full');
      ctrl._fullRow=null;
      ctrl.card.setAttribute('role','group');ctrl.card.removeAttribute('aria-modal');
      if(ctrl._esc) document.removeEventListener('keydown',ctrl._esc,true);
      ctrl._esc=null;
      if(ctrl.height) setHeight(ctrl,ctrl.height);
      const back=ctrl._returnFocus;ctrl._returnFocus=null;
      try{(back&&back.isConnected?back:b).focus({preventScroll:true});}catch(_){}
    }
    setTimeout(()=>postTo(ctrl,{type:'measure',full:on}),50);
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
    // The download is a plain page: drop the chat shell, keep theme and widget.
    doc=doc.replace(/<script>\s*\(function\(\)\{[\s\S]*?<\/script>/,'')
      .replace(/<title>[\s\S]*?<\/title>/i,`<title>${title}</title>`)
      .replace('<html lang="nl" data-theme="dark">',`<html lang="${lang()}" data-theme="${theme.mode}" style="${escHtml(vars)}">`)
      .replace('<style id="iui-user-style"></style>',()=>`<style id="iui-user-style">${p.css.replace(/<\/style/gi,'<\\/style')}</style>`)
      .replace('<div id="iui-root"></div>',()=>`<div id="iui-root">${p.html}</div>`)
      .replace(/<\/body>/i,()=>`<script>window.synthwave={theme:{palette:['#f97316','#3b82f6','#22c55e','#a855f7','#eab308','#ec4899','#14b8a6','#94a3b8'],mode:${JSON.stringify(theme.mode)}},sendPrompt:function(){return false},copy:function(t){try{navigator.clipboard.writeText(String(t))}catch(e){}},onTheme:function(){},resize:function(){}};<\/script>\n`+scripts+'\n</body>');
    return doc;
  }
  function fileName(ctrl,fallback){
    return ((ctrl.parsed&&ctrl.parsed.title)||fallback).toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||fallback;
  }
  function saveBlob(blob,name){
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download=name;
    document.body.appendChild(a);a.click();
    setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1500);
  }
  // Exports follow what the user sees: the table's sort and search are kept.
  function kitExport(ctrl,format){
    const K=kits(), p=ctrl.parsed;
    if(!K||!p||!p.spec) return '';
    const view=ctrl.kit==='table'?Object.assign(K.initialView(p.spec),loadState(ctrl.stateKey)||{}):null;
    const table=K.kitTable(ctrl.kit,p.spec,view,ctrl.kitData);
    return format==='csv'?K.toCsv(table,{delimiter:';',decimalComma:true}):K.toTsv(table,{decimalComma:true});
  }
  function downloadCsv(ctrl){
    const text=kitExport(ctrl,'csv');
    if(!text) return;
    saveBlob(new Blob([text],{type:'text/csv;charset=utf-8'}),fileName(ctrl,kitWord('kitName',ctrl.kit).toLowerCase())+'.csv');
  }
  // A downloaded data block is the kit page itself with the spec built in;
  // the JSON is escaped so it cannot end the script element.
  function kitStandaloneHtml(ctrl,frameHtml){
    const p=ctrl.parsed, theme=themeMessage();
    let doc=String(frameHtml||'');
    const at=doc.indexOf('<script>');
    if(!/id="kit-root"/.test(doc)||at<0||!p.spec) return '';
    const vars=Object.keys(theme.vars).map(k=>`${k}:${theme.vars[k]}`).join(';');
    const payload={kit:ctrl.kit,spec:p.spec,data:kitDataFor(ctrl),final:true,restore:loadState(ctrl.stateKey)||{},lang:kitLang(ctrl),theme:theme.mode};
    const json=JSON.stringify(payload).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
    doc=doc.slice(0,at)+'<script>window.__SWKIT_DOC='+json+';<\/script>'+doc.slice(at);
    const open='<html lang="nl" data-theme="dark">', i=doc.indexOf(open);
    if(i>=0) doc=doc.slice(0,i)+`<html lang="${lang()}" data-theme="${theme.mode}" style="${escHtml(vars)}">`+doc.slice(i+open.length);
    const t=doc.indexOf('<title>Gegevens</title>');
    if(t>=0) doc=doc.slice(0,t)+`<title>${escHtml(p.title||kitWord('kitName',ctrl.kit))}</title>`+doc.slice(t+'<title>Gegevens</title>'.length);
    return doc;
  }
  function download(ctrl){
    if(!ctrl.final) return;
    if(ctrl.kit){
      const v=encodeURIComponent(String((typeof WEBUI_VERSION!=='undefined'&&WEBUI_VERSION)||'1'));
      fetch(KIT_URL+'?v='+v,{credentials:'same-origin'}).then(r=>r.ok?r.text():'').then(html=>{
        const doc=kitStandaloneHtml(ctrl,html);
        if(doc) saveBlob(new Blob([doc],{type:'application/octet-stream'}),fileName(ctrl,'gegevens')+'.html');
      },()=>{});
      return;
    }
    const finish=html=>{
      // An octet-stream blob is only ever saved, never shown in this origin.
      const blob=new Blob([standaloneHtml(ctrl,html)],{type:'application/octet-stream'});
      const a=document.createElement('a');
      const name=(ctrl.parsed.title||'weergave').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'weergave';
      a.href=URL.createObjectURL(blob);a.download=name+'.html';
      document.body.appendChild(a);a.click();
      setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1500);
    };
    fetch(FRAME_URL,{credentials:'same-origin'}).then(r=>r.ok?r.text():'').then(finish,()=>finish(''));
  }

  // ── Reply chips (suggested answers under the latest reply) ──────────────
  function chipTexts(source){
    return String(source||'').split(/\n/).map(l=>l.replace(/^\s*(?:[-*\u2022]|\d+[.)])\s*/,'').replace(/^["']|["']$/g,'').trim())
      .map(cleanPrompt).filter(Boolean).filter(t=>t.length<=140).slice(0,3);
  }
  function renderChips(block){
    const texts=chipTexts(block.textContent||'');
    block.textContent='';
    if(!texts.length){block.remove();return;}
    const wrap=document.createElement('div');wrap.className='iui-chips';wrap.setAttribute('role','group');wrap.setAttribute('aria-label',tx('chipsLabel'));
    texts.forEach(t=>{
      const b=document.createElement('button');b.type='button';b.className='iui-chip';b.textContent=t;
      b.addEventListener('click',ev=>{
        if(!ev.isTrusted||wrap.classList.contains('is-used')||wrap.classList.contains('is-pending')) return;
        if(chatBusy()){toast(tx('chipsBusy'));return;}
        wrap.classList.add('is-pending');
        const started=sendPrompt(t,ok=>{
          wrap.classList.remove('is-pending');
          if(!ok) return;
          wrap.classList.add('is-used');b.classList.add('is-chosen');
          wrap.querySelectorAll('.iui-chip').forEach(x=>{x.disabled=true;});
        });
        if(!started) wrap.classList.remove('is-pending');
      });
      wrap.appendChild(b);
    });
    block.classList.add('iui-chips-host');
    block.appendChild(wrap);
  }

  // ── Questions form (```form, ```vraag, ```vragen, ```questions) ─────────
  // The agent asks a structured question as JSON; the chat draws the controls
  // itself (textContent only, no frame), so a click is a real user click.
  // Versturen composes a plain message ("Mijn antwoorden:\n- Budget: € 5.000")
  // and sends it through the same path as the reply chips, never over a
  // draft. The card then locks and shows the answers; a form under an older
  // reply is shown answered (from this tab's memory or the next message).
  const FORM_LANGS=new Set(['form','vraag','vragen','questions']);
  const FORM_LIMITS={bytes:64*1024,fields:8,options:12,title:120,intro:300,label:80,option:60,placeholder:80,hint:160,text:500,submit:24,unit:20};
  const FORM_TYPES={choice:'choice',select:'choice',single:'choice',radio:'choice',keuze:'choice',dropdown:'choice',option:'choice',options:'choice',
    multi:'multi',multiple:'multi',checkbox:'multi',checkboxes:'multi',meerkeuze:'multi',multiselect:'multi','multi-select':'multi',
    text:'text',textarea:'text',string:'text',tekst:'text',open:'text',input:'text',email:'text',
    number:'number',getal:'number',amount:'number',bedrag:'number',integer:'number',int:'number',currency:'number',
    slider:'slider',range:'slider',schaal:'slider',scale:'slider',
    date:'date',datum:'date',
    yesno:'yesno','yes-no':'yesno',yes_no:'yesno',janee:'yesno','ja-nee':'yesno',boolean:'yesno',bool:'yesno',confirm:'yesno',toggle:'yesno'};
  const FORM_TEXT={
    nl:{title:'Een paar vragen',title1:'Een vraag',submit:'Versturen',yes:'Ja',no:'Nee',and:' en ',required:'verplicht',multiHint:'Kies er één of meer',
      head:n=>n===1?'Mijn antwoord:':'Mijn antwoorden:',missing:'Vul dit nog in.',pick:'Kies een antwoord.',slide:'Schuif om te kiezen',
      left:n=>n===1?'Nog 1 vraag in te vullen.':`Nog ${n} vragen in te vullen.`,empty:'Beantwoord minstens één vraag.',
      notNumber:'Vul een getal in, bijvoorbeeld 1.500.',between:(a,b)=>`Kies een getal van ${a} tot en met ${b}.`,atLeast:a=>`Kies ${a} of meer.`,atMost:b=>`Kies ${b} of minder.`,
      badDate:'Kies een datum, bijvoorbeeld 1-12-2026.',dateBetween:(a,b)=>`Kies een datum van ${a} tot en met ${b}.`,dateFrom:a=>`Kies ${a} of later.`,dateUntil:b=>`Kies ${b} of eerder.`,
      sent:'Verstuurd',answered:'Beantwoord',closed:'Het gesprek is verder gegaan.',waiting:'Vragen worden klaargezet',
      sentToast:n=>n===1?'Antwoord verstuurd':'Antwoorden verstuurd',datePh:'dd-mm-jjjj',calendar:'Kies in de kalender',
      fail:'Deze vragen konden niet worden getoond.',repairPrompt:'Kun je je vragen opnieuw stellen? Het formulier werkte niet.',
      json:line=>`De vragen zijn geen geldige JSON${line?` (regel ${line})`:''}.`,notObject:()=>'De vragen moeten één JSON-object zijn met een lijst "fields".',
      tooBig:()=>'Het formulier is te groot (meer dan 64 kB).',noFields:()=>'Er staan geen vragen in de lijst "fields".',
      noneUsable:()=>'Geen enkele vraag is bruikbaar: elke vraag heeft een "label" nodig.',
      manyFields:(n,max)=>`Er zijn ${n} vragen; alleen de eerste ${max} worden getoond.`,
      manyOptions:(l,n,max)=>`Vraag "${l}" heeft ${n} opties; alleen de eerste ${max} worden getoond.`,
      fieldNotObject:i=>`Vraag ${i} is geen object en is weggelaten.`,noLabel:i=>`Vraag ${i} heeft geen "label" en is weggelaten.`,
      badType:(l,t)=>`Vraag "${l}" heeft een onbekend type "${t}".`,fewOptions:l=>`Vraag "${l}" heeft minder dan twee opties en is een open vraag geworden.`,
      dupOption:l=>`Vraag "${l}" had een dubbele optie; die is weggelaten.`,badDefault:l=>`De standaardwaarde van "${l}" past niet en is weggelaten.`,
      sliderRange:l=>`Schuifregelaar "${l}" had geen min en max; 0 tot en met 10 gebruikt.`,swapped:l=>`Bij "${l}" waren min en max omgedraaid.`},
    en:{title:'A few questions',title1:'A question',submit:'Send',yes:'Yes',no:'No',and:' and ',required:'required',multiHint:'Choose one or more',
      head:n=>n===1?'My answer:':'My answers:',missing:'Please fill this in.',pick:'Choose an answer.',slide:'Slide to choose',
      left:n=>n===1?'1 question still to answer.':`${n} questions still to answer.`,empty:'Answer at least one question.',
      notNumber:'Enter a number, for example 1,500.',between:(a,b)=>`Choose a number from ${a} to ${b}.`,atLeast:a=>`Choose ${a} or more.`,atMost:b=>`Choose ${b} or less.`,
      badDate:'Choose a date, for example 1/12/2026.',dateBetween:(a,b)=>`Choose a date from ${a} to ${b}.`,dateFrom:a=>`Choose ${a} or later.`,dateUntil:b=>`Choose ${b} or earlier.`,
      sent:'Sent',answered:'Answered',closed:'The conversation has moved on.',waiting:'Preparing the questions',
      sentToast:n=>n===1?'Answer sent':'Answers sent',datePh:'dd/mm/yyyy',calendar:'Choose in the calendar',
      fail:'These questions could not be shown.',repairPrompt:'Can you ask your questions again? The form did not work.',
      json:line=>`The questions are not valid JSON${line?` (line ${line})`:''}.`,notObject:()=>'The questions must be one JSON object with a "fields" list.',
      tooBig:()=>'The form is too large (over 64 kB).',noFields:()=>'There are no questions in the "fields" list.',
      noneUsable:()=>'None of the questions can be used: every question needs a "label".',
      manyFields:(n,max)=>`There are ${n} questions; only the first ${max} are shown.`,
      manyOptions:(l,n,max)=>`Question "${l}" has ${n} options; only the first ${max} are shown.`,
      fieldNotObject:i=>`Question ${i} is not an object and was left out.`,noLabel:i=>`Question ${i} has no "label" and was left out.`,
      badType:(l,t)=>`Question "${l}" has an unknown type "${t}".`,fewOptions:l=>`Question "${l}" has fewer than two options and became an open question.`,
      dupOption:l=>`Question "${l}" had a duplicate option; it was left out.`,badDefault:l=>`The default of "${l}" does not fit and was left out.`,
      sliderRange:l=>`Slider "${l}" had no min and max; 0 to 10 was used.`,swapped:l=>`For "${l}" min and max were the wrong way round.`},
  };
  function formLangOf(v){const l=String(v||'').toLowerCase();return l==='nl'||l==='en'?l:'';}
  function formClean(v,max,multiline){
    if(v==null) return '';
    let s=typeof v==='string'?v:((typeof v==='number'&&Number.isFinite(v))||typeof v==='boolean')?String(v):'';
    s=s.replace(/[\p{Cf}\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/gu,'');
    s=multiline?s.replace(/\r\n?/g,'\n').replace(/[ \t]+/g,' ').replace(/\n{3,}/g,'\n\n').trim():s.replace(/\s+/g,' ').trim();
    if(max&&s.length>max) s=s.slice(0,max-1).trimEnd()+'…';
    return s;
  }
  // English answers use a comma for thousands and a dot for decimals
  // ("1,500.50"); a lone comma with one or two digits after it is a decimal
  // comma ("7,5"). Dutch answers (and the agent's spec) go through parseNumber.
  function formNumEn(v){
    let s=v.trim().replace(/[\u00a0\u202f\u2009 ]/g,'');
    let neg=false;
    if(/^[-\u2212]/.test(s)){neg=true;s=s.slice(1);}
    s=s.replace(/^(€|eur|\$|usd|£|gbp)/i,'').replace(/(€|eur|\$|usd|£|gbp)$/i,'');
    if(!neg&&/^[-\u2212]/.test(s)){neg=true;s=s.slice(1);}
    let norm='';
    if(/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) norm=s.replace(/,/g,'');
    else if(/^\d+(\.\d+)?$|^\.\d+$/.test(s)) norm=s;
    else if(/^\d+,\d{1,2}$/.test(s)) norm=s.replace(',','.');
    else return NaN;
    if(/^0\d/.test(norm)) return NaN;
    const n=Number(norm);
    return Number.isFinite(n)?(neg?-n:n):NaN;
  }
  function formNum(v,l){
    if(typeof v==='number') return Number.isFinite(v)?v:NaN;
    if(typeof v!=='string'||!v.trim()) return NaN;
    if(l==='en') return formNumEn(v);
    const K=kits();
    if(K&&typeof K.parseNumber==='function') return K.parseNumber(v).n;
    const n=Number(v.trim().replace(/\s/g,'').replace(',','.'));
    return Number.isFinite(n)?n:NaN;
  }
  function formIso(v){
    const s=String(v==null?'':v).trim();
    if(!/^\d{4}-\d{2}-\d{2}$/.test(s)) return '';
    const d=new Date(s+'T12:00:00Z');
    return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===s?s:'';
  }
  const FORM_MONTHS={jan:1,januari:1,january:1,feb:2,febr:2,februari:2,february:2,mrt:3,maa:3,maart:3,mar:3,march:3,apr:4,april:4,
    mei:5,may:5,jun:6,juni:6,june:6,jul:7,juli:7,july:7,aug:8,augustus:8,august:8,sep:9,sept:9,september:9,okt:10,oct:10,oktober:10,october:10,
    nov:11,november:11,dec:12,december:12};
  function formYmd(y,m,d){
    const iso=String(y).padStart(4,'0')+'-'+String(m).padStart(2,'0')+'-'+String(d).padStart(2,'0');
    return formIso(iso);
  }
  // A typed date, day first as in Dutch: "1-12-2026", "1/12", "1 december",
  // "1 dec 2026", "december 1" or 2026-12-01. Without a year: this year, or
  // next year when this year's date falls before the earliest allowed date.
  function formDateParse(v,opts){
    const s=String(v==null?'':v).trim().toLowerCase().replace(/\s+/g,' ');
    if(!s) return '';
    const iso=formIso(s);
    if(iso) return iso;
    const o=opts||{}, now=o.now||new Date();
    const thisYear=now.getFullYear();
    let d=0,m=0,y=0,hit;
    if((hit=/^(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2}|\d{4}))?$/.exec(s))){d=+hit[1];m=+hit[2];y=hit[3]?+hit[3]:0;}
    else if((hit=/^(\d{1,2})(?:e|ste|de|st|nd|rd|th)?\.? ([a-z]+)\.?,? ?(\d{4})?$/.exec(s))){d=+hit[1];m=FORM_MONTHS[hit[2]]||0;y=hit[3]?+hit[3]:0;}
    else if((hit=/^([a-z]+)\.? (\d{1,2})(?:st|nd|rd|th)?,? ?(\d{4})?$/.exec(s))){m=FORM_MONTHS[hit[1]]||0;d=+hit[2];y=hit[3]?+hit[3]:0;}
    if(!d||!m) return '';
    if(y&&y<100) y+=2000;
    if(y) return formYmd(y,m,d);
    let out=formYmd(thisYear,m,d);
    if(out&&o.min&&out<o.min){const next=formYmd(thisYear+1,m,d);if(next&&next>=o.min&&(!o.max||next<=o.max))out=next;}
    return out||formYmd(thisYear+1,m,d);
  }
  // How a date stands in the text box: 01-12-2026 (Dutch) or 01/12/2026.
  function formDateInput(iso,l){
    const [y,m,d]=String(iso).split('-');
    return l==='en'?`${d}/${m}/${y}`:`${d}-${m}-${y}`;
  }
  // The chosen date read back in words, so a mixed-up order shows before sending.
  function formDateEcho(iso,l){
    const dt=new Date(iso+'T12:00:00Z');
    return dt.toLocaleDateString(l==='nl'?'nl-NL':'en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  }
  function formBool(v){
    if(v===true||v===false) return v;
    const s=String(v==null?'':v).trim().toLowerCase();
    if(['ja','yes','true','y','j','1'].includes(s)) return true;
    if(['nee','no','false','n','0'].includes(s)) return false;
    return null;
  }
  function formDecimals(step){const s=String(step);return s.includes('.')?Math.min(4,s.split('.')[1].length):0;}
  // The unit splits into a euro sign in front and words behind: "€ per maand".
  function formUnit(unit){
    const u=formClean(unit,FORM_LIMITS.unit);
    const m=/^(?:€|eur(?:o|os)?(?![a-z]))\s*(.*)$/i.exec(u);
    if(m) return {pre:'€ ',post:m[1]?' '+m[1]:''};
    if(u==='%') return {pre:'',post:'%'};
    return {pre:'',post:u?' '+u:''};
  }
  // Decimals of the value itself (at most 4), so a typed 7.500,50 stays 7.500,50.
  function formValueDecimals(n){
    let d=0;
    while(d<4&&Math.abs(Math.round(n*Math.pow(10,d))-n*Math.pow(10,d))>1e-6) d++;
    return d;
  }
  function formNumberText(n,field,l){
    const u=formUnit(field.unit);
    const own=formValueDecimals(n);
    let dec=Math.max(field.step?formDecimals(field.step):0,own);
    // An amount in euros with cents always shows two: € 2,50, never € 2,5.
    const min=u.pre&&own>0?2:0;
    dec=Math.max(dec,min);
    const txt=new Intl.NumberFormat(l==='nl'?'nl-NL':'en-GB',{maximumFractionDigits:dec,minimumFractionDigits:min}).format(n);
    return u.pre+txt+u.post;
  }
  function formDateText(iso,l,nowYear){
    const d=new Date(iso+'T12:00:00Z');
    const year=nowYear||new Date().getFullYear();
    const o={day:'numeric',month:'long',timeZone:'UTC'};
    if(d.getUTCFullYear()!==year) o.year='numeric';
    return d.toLocaleDateString(l==='nl'?'nl-NL':'en-GB',o);
  }
  function formList(items,l){
    const L=FORM_TEXT[l]||FORM_TEXT.en;
    return items.length<2?items.join(''):items.slice(0,-1).join(', ')+L.and+items[items.length-1];
  }
  function formOptions(raw,label,warn){
    const list=Array.isArray(raw)?raw:(typeof raw==='string'&&raw.trim()?raw.split(/\s*[,;|]\s*/):[]);
    const out=[], seen=new Set();
    list.forEach(o=>{
      const t=formClean(o&&typeof o==='object'?(o.label!=null?o.label:(o.text!=null?o.text:(o.name!=null?o.name:o.value))):o,FORM_LIMITS.option);
      if(!t) return;
      const k=t.toLowerCase();
      if(seen.has(k)){warn('dupOption',label);return;}
      seen.add(k);out.push({label:t,value:o&&typeof o==='object'&&o.value!=null?formClean(o.value,FORM_LIMITS.option):''});
    });
    if(out.length>FORM_LIMITS.options){warn('manyOptions',label,out.length,FORM_LIMITS.options);out.length=FORM_LIMITS.options;}
    return out;
  }
  function formOptionFor(options,v){
    const s=formClean(v,FORM_LIMITS.option).toLowerCase();
    if(!s) return '';
    const hit=options.find(o=>o.label.toLowerCase()===s)||options.find(o=>o.value&&o.value.toLowerCase()===s);
    return hit?hit.label:'';
  }
  function formField(f,i,warn,ids,l){
    if(typeof f==='string') f={label:f,type:'text'};
    if(!f||typeof f!=='object'||Array.isArray(f)){warn('fieldNotObject',i+1);return null;}
    const label=formClean(f.label!=null?f.label:(f.question!=null?f.question:(f.title!=null?f.title:f.name)),FORM_LIMITS.label);
    if(!label){warn('noLabel',i+1);return null;}
    const rawType=formClean(f.type,30).toLowerCase();
    let type=FORM_TYPES[rawType]||'';
    let options=formOptions(f.options!=null?f.options:(f.choices!=null?f.choices:f.values),label,warn);
    if(!type){
      if(rawType) warn('badType',label,rawType);
      type=options.length>=2?'choice':(formBool(f.default)!==null&&typeof f.default==='boolean'?'yesno':(f.min!=null||f.max!=null)?'number':'text');
    }
    if(type==='choice'&&(f.multiple===true||f.multi===true)) type='multi';
    if((type==='choice'||type==='multi')&&options.length<2){warn('fewOptions',label);type='text';options=[];}
    let id=formClean(f.id!=null?f.id:f.key,60).toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40);
    if(!id) id=label.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40)||('vraag-'+(i+1));
    let uid=id, n=2;
    while(ids.has(uid)) uid=id+'-'+(n++);
    ids.add(uid);
    const req=f.required;
    const out={id:uid,label,type,required:req===true||req===1||/^(true|ja|yes)$/i.test(String(req==null?'':req))};
    const hint=formClean(f.hint!=null?f.hint:(f.help!=null?f.help:f.description),FORM_LIMITS.hint);
    if(hint) out.hint=hint;
    const dflt=f.default!=null?f.default:f.value;
    if(type==='choice'){
      out.options=options.map(o=>o.label);
      if(dflt!=null&&dflt!==''){const d=formOptionFor(options,dflt);if(d)out.default=d;else warn('badDefault',label);}
    } else if(type==='multi'){
      out.options=options.map(o=>o.label);
      if(dflt!=null&&dflt!==''){
        const want=(Array.isArray(dflt)?dflt:[dflt]).map(v=>formOptionFor(options,v));
        if(want.some(v=>!v)) warn('badDefault',label);
        const keep=out.options.filter(o=>want.includes(o));
        if(keep.length) out.default=keep;
      }
    } else if(type==='yesno'){
      if(dflt!=null&&dflt!==''){const b=formBool(dflt);if(b!==null)out.default=b;else warn('badDefault',label);}
    } else if(type==='text'){
      out.long=rawType==='textarea'||f.multiline===true||f.long===true||Number(f.rows)>1;
      const ph=formClean(f.placeholder,FORM_LIMITS.placeholder);if(ph)out.placeholder=ph;
      if(dflt!=null&&dflt!==''){const t=formClean(dflt,FORM_LIMITS.text,out.long);if(t)out.default=t;else warn('badDefault',label);}
    } else if(type==='date'){
      const mn=formIso(f.min), mx=formIso(f.max);
      if(mn) out.min=mn;
      if(mx) out.max=mx;
      if(mn&&mx&&mn>mx){out.min=mx;out.max=mn;warn('swapped',label);}
      if(dflt!=null&&dflt!==''){
        const d=formIso(dflt);
        if(d&&(!out.min||d>=out.min)&&(!out.max||d<=out.max)) out.default=d; else warn('badDefault',label);
      }
    } else {
      let mn=formNum(f.min,l), mx=formNum(f.max,l), step=formNum(f.step,l);
      if(type==='slider'){
        if(!Number.isFinite(mn)&&!Number.isFinite(mx)){warn('sliderRange',label);mn=0;mx=10;}
        else if(!Number.isFinite(mn)) mn=Math.min(0,mx-1);
        else if(!Number.isFinite(mx)) mx=mn+(mn>=0?Math.max(10,Math.abs(mn)):10);
      }
      if(Number.isFinite(mn)&&Number.isFinite(mx)&&mn>mx){[mn,mx]=[mx,mn];warn('swapped',label);}
      if(type==='slider'&&mn===mx) mx=mn+1;
      if(Number.isFinite(mn)) out.min=mn;
      if(Number.isFinite(mx)) out.max=mx;
      if(type==='slider'){
        const span=mx-mn;
        if(!(step>0)||span/step>1000){
          const raw=span/100, p=Math.pow(10,Math.floor(Math.log10(raw||1)));
          step=span<=20&&Number.isInteger(mn)&&Number.isInteger(mx)?1:[1,2,5,10].map(x=>x*p).find(x=>x>=raw)||p*10;
        }
      }
      if(step>0) out.step=step;
      const unit=formClean(f.unit,FORM_LIMITS.unit);
      if(unit) out.unit=unit;
      else if(rawType==='currency'||rawType==='bedrag') out.unit='€';
      if(type==='number'){const ph=formClean(f.placeholder,FORM_LIMITS.placeholder);if(ph)out.placeholder=ph;}
      if(dflt!=null&&dflt!==''){
        const d=formNum(dflt,l);
        if(Number.isFinite(d)&&(!Number.isFinite(mn)||d>=mn)&&(!Number.isFinite(mx)||d<=mx)) out.default=d;
        else if(Number.isFinite(d)&&type==='slider'){out.default=Math.max(mn,Math.min(mx,d));warn('badDefault',label);}
        else warn('badDefault',label);
      }
    }
    return out;
  }
  // formSpec(source, {lang}) -> {spec, errors, warnings}; errors means nothing can be drawn.
  function formSpec(source,opts){
    let l=formLangOf(opts&&opts.lang)||lang();
    const res={spec:null,errors:[],warnings:[]};
    const msg=(key,...a)=>{const v=(FORM_TEXT[l]||FORM_TEXT.en)[key];return typeof v==='function'?v(...a):String(v);};
    const src=String(source==null?'':source);
    if(src.length>FORM_LIMITS.bytes){res.errors.push(msg('tooBig'));return res;}
    let raw;
    const K=kits();
    if(K&&typeof K.parseKit==='function'){
      const p=K.parseKit(src);
      if(!p.ok){res.errors.push(msg('json',p.line));return res;}
      raw=p.value;
    } else {
      try{raw=JSON.parse(src);}catch(_){res.errors.push(msg('json',0));return res;}
    }
    if(Array.isArray(raw)) raw={fields:raw};
    if(!raw||typeof raw!=='object'){res.errors.push(msg('notObject'));return res;}
    l=formLangOf(raw.lang)||l;
    const warn=(key,...a)=>res.warnings.push(msg(key,...a));
    const listKey=['fields','questions','vragen','items'].find(k=>raw[k]!=null);
    let fields=listKey?raw[listKey]:null;
    // A map of questions ({"budget":{...}}) becomes a list with the keys as ids.
    if(fields&&typeof fields==='object'&&!Array.isArray(fields)){
      fields=Object.keys(fields).map(k=>{const f=fields[k];
        if(f&&typeof f==='object'&&!Array.isArray(f)) return Object.assign({id:k},f.label==null&&f.question==null&&f.title==null&&f.name==null?{label:k}:{},f);
        return typeof f==='string'?{id:k,label:f}:f;});
    }
    if(!Array.isArray(fields)) fields=null;
    if(!fields||!fields.length){
      // A single question written at the top level: a label, or a title or
      // name together with a known type or options.
      const typed=FORM_TYPES[formClean(raw.type,30).toLowerCase()]||raw.options!=null||raw.choices!=null;
      if(!listKey&&(raw.label||raw.question||((raw.title||raw.name)&&typed))) fields=[raw];
      else {res.errors.push(msg('noFields'));return res;}
    }
    if(fields.length>FORM_LIMITS.fields){warn('manyFields',fields.length,FORM_LIMITS.fields);fields=fields.slice(0,FORM_LIMITS.fields);}
    const ids=new Set();
    const out=fields.map((f,i)=>formField(f,i,warn,ids,l)).filter(Boolean);
    if(!out.length){res.errors.push(msg('noneUsable'));return res;}
    const L=FORM_TEXT[l]||FORM_TEXT.en;
    const single=fields===raw||fields[0]===raw;
    res.spec={lang:l,title:single?'':formClean(raw.title,FORM_LIMITS.title),intro:formClean(raw.intro!=null?raw.intro:(raw.description!=null?raw.description:raw.subtitle),FORM_LIMITS.intro),
      submit:formClean(raw.submit,FORM_LIMITS.submit)||L.submit,fields:out};
    if(!res.spec.title) res.spec.title=out.length===1?L.title1:L.title;
    return res;
  }
  function formHasValue(field,v){
    if(v==null) return false;
    if(field.type==='multi') return Array.isArray(v)&&v.length>0;
    if(field.type==='yesno') return v===true||v===false;
    if(field.type==='number'||field.type==='slider') return typeof v==='number'&&Number.isFinite(v);
    return String(v).trim()!=='';
  }
  function formValueText(field,v,l,nowYear){
    const L=FORM_TEXT[l]||FORM_TEXT.en;
    if(field.type==='multi') return formList(field.options.filter(o=>v.includes(o)),l);
    if(field.type==='yesno') return v?L.yes:L.no;
    if(field.type==='number'||field.type==='slider') return formNumberText(v,field,l);
    if(field.type==='date') return formDateText(v,l,nowYear);
    return formClean(v,FORM_LIMITS.text);
  }
  function formLine(label,value){return '- '+label+(/[?:]$/.test(label)?' ':': ')+value;}
  // The message that is sent as the user's reply, plus the shown answers per field.
  function formMessage(spec,answers,opts){
    const display={}, lines=[];
    spec.fields.forEach(f=>{
      const v=answers&&answers[f.id];
      if(!formHasValue(f,v)) return;
      const t=formValueText(f,v,spec.lang,opts&&opts.nowYear);
      if(!t) return;
      display[f.id]=t;lines.push(formLine(f.label,t));
    });
    const L=FORM_TEXT[spec.lang]||FORM_TEXT.en;
    return {text:lines.length?L.head(lines.length)+'\n'+lines.join('\n'):'',display};
  }
  // Answers read back from a sent message (a reload in another tab).
  function formAnswersFrom(spec,text){
    const display={};
    const lines=String(text||'').split(/\r?\n/);
    spec.fields.forEach(f=>{
      const lead='- '+f.label+(/[?:]$/.test(f.label)?' ':': ');
      const hit=lines.find(x=>x.startsWith(lead));
      if(hit){const v=hit.slice(lead.length).trim();if(v)display[f.id]=v;}
    });
    return display;
  }
  // Checks one field's control state; returns {value} or {error}.
  function formCheck(field,raw,l,opts){
    const L=FORM_TEXT[l]||FORM_TEXT.en;
    const empty=raw==null||(Array.isArray(raw)?!raw.length:String(raw).trim()==='');
    if(empty) return field.required?{error:field.type==='choice'||field.type==='multi'||field.type==='yesno'||field.type==='slider'?L.pick:L.missing}:{value:null};
    if(field.type==='number'){
      const n=typeof raw==='number'?raw:formNum(String(raw).replace(/€/g,'').trim(),l);
      if(!Number.isFinite(n)) return {error:L.notNumber};
      const has=k=>typeof field[k]==='number', fmt=x=>formNumberText(x,field,l);
      if(has('min')&&has('max')&&(n<field.min||n>field.max)) return {error:L.between(fmt(field.min),fmt(field.max))};
      if(has('min')&&n<field.min) return {error:L.atLeast(fmt(field.min))};
      if(has('max')&&n>field.max) return {error:L.atMost(fmt(field.max))};
      return {value:n};
    }
    if(field.type==='date'){
      const d=formDateParse(raw,{min:field.min,max:field.max,now:opts&&opts.now});
      if(!d) return {error:L.badDate};
      const fmt=x=>formDateText(x,l);
      if(field.min&&field.max&&(d<field.min||d>field.max)) return {error:L.dateBetween(fmt(field.min),fmt(field.max))};
      if(field.min&&d<field.min) return {error:L.dateFrom(fmt(field.min))};
      if(field.max&&d>field.max) return {error:L.dateUntil(fmt(field.max))};
      return {value:d};
    }
    if(field.type==='text') return {value:formClean(raw,FORM_LIMITS.text)};
    return {value:raw};
  }

  function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
  function iconEl(name){const s=el('span','iui-form-ico');s.setAttribute('aria-hidden','true');s.innerHTML=icon(name);return s;}
  // Where the form stands: locked once a newer message exists.
  function formTurnState(block){
    const turn=block.closest('.assistant-turn,.msg-row[data-role="assistant"]');
    if(!turn) return {locked:false,user:null};
    let n=turn.nextElementSibling, user=null, newer=false;
    while(n){
      if(n.matches&&n.matches('.msg-row:not(.msg-row-btw):not([data-btw])')){newer=true;if(!user&&n.matches('[data-role="user"]'))user=n;}
      n=n.nextElementSibling;
    }
    return {locked:newer,user};
  }
  // The chat redraws the turn after a send, so focus on the old card would fall
  // back to the page; for a short while a redrawn copy of that form takes it.
  let formFocus=null;
  function formShowLocked(card,spec,display,how){
    const L=FORM_TEXT[spec.lang]||FORM_TEXT.en;
    const hadFocus=!!(document.activeElement&&card.contains(document.activeElement));
    card.classList.add('is-locked');
    card.querySelectorAll('.iui-form-body,.iui-form-foot,.iui-form-summary,.iui-form-closed').forEach(n=>n.remove());
    // Focus would fall back to the page once the controls are gone.
    const keepFocus=()=>{
      const a=document.activeElement, lost=!a||a===document.body;
      const mine=formFocus&&formFocus.key===card.dataset.formKey&&Date.now()<formFocus.until;
      if(!hadFocus&&!(mine&&lost&&card.isConnected)) return;
      card.tabIndex=-1;try{card.focus({preventScroll:true});}catch(_){}
    };
    const pill=card.querySelector('.iui-form-done');
    const ids=Object.keys(display||{}).filter(k=>display[k]);
    if(!ids.length){
      card.appendChild(el('p','iui-form-closed',L.closed));
      if(pill) pill.hidden=true;
      keepFocus();
      return;
    }
    if(pill){pill.querySelector('.iui-form-done-text').textContent=how==='sent'?L.sent:L.answered;pill.hidden=false;}
    const dl=el('dl','iui-form-summary');
    spec.fields.forEach(f=>{
      if(!display[f.id]) return;
      const row=el('div','iui-form-sum-row');
      row.appendChild(el('dt','',f.label));row.appendChild(el('dd','',display[f.id]));
      dl.appendChild(row);
    });
    card.appendChild(dl);
    keepFocus();
  }
  function formError(block,errors,fence){
    const l=lang(), L=FORM_TEXT[l];
    const card=el('div','iui-form is-error');
    card.setAttribute('role','group');
    const row=el('div','iui-form-errline');
    row.appendChild(iconEl('alert'));
    row.appendChild(el('span','iui-form-errtext',L.fail));
    const b=el('button','iui-form-repair',tx('repair'));b.type='button';
    b.addEventListener('click',ev=>{
      if(!ev.isTrusted||b.dataset.sent) return;
      if(formTurnState(block).locked){b.remove();return;}
      if(chatBusy()){toast(tx('chipsBusy'));return;}
      b.dataset.sent='1';b.disabled=true;
      const report=`\n\n[View report]\nBlock: ${fence}\nProblem: ${String(errors[0]||'unknown').replace(/\[\/?View report\]/g,'')}\nFix the cause and send the complete ${fence} block again.\n[/View report]`;
      if(!sendPrompt(L.repairPrompt+report)){b.dataset.sent='';b.disabled=false;}
    });
    if(!formTurnState(block).locked) row.appendChild(b);
    card.appendChild(row);
    block.appendChild(card);
  }
  function renderForm(block){
    const source=block.textContent||'';
    const fence=block.getAttribute('data-iui-kind')||'form';
    block.textContent='';
    block.classList.add('iui-form-host');
    const parsed=formSpec(source,{});
    if(!parsed.spec){formError(block,parsed.errors,fence);return;}
    const spec=parsed.spec, L=FORM_TEXT[spec.lang]||FORM_TEXT.en, l=spec.lang;
    const key='form:'+hashSource(source);
    const uid='iuif'+(++seq);
    const card=el('div','iui-form');
    card.setAttribute('role','group');
    card.setAttribute('lang',l);
    card.dataset.formKey=key;
    const head=el('div','iui-form-head');
    const badge=el('span','iui-badge');badge.appendChild(iconEl('form'));head.appendChild(badge);
    const title=el('div','iui-form-title',spec.title);title.id=uid+'-t';head.appendChild(title);
    card.setAttribute('aria-labelledby',title.id);
    const done=el('span','iui-form-done');done.hidden=true;done.appendChild(iconEl('check'));done.appendChild(el('span','iui-form-done-text',''));head.appendChild(done);
    card.appendChild(head);
    if(spec.intro) card.appendChild(el('p','iui-form-intro',spec.intro));
    const wait=el('div','iui-form-wait',L.waiting);wait.setAttribute('aria-hidden','true');card.appendChild(wait);

    const state=formTurnState(block);
    if(state.locked){
      const saved=loadState(key);
      let display=saved&&saved.display&&typeof saved.display==='object'?saved.display:null;
      if(!display&&state.user){
        const u=state.user, bodyEl=u.querySelector('.msg-body')||u;
        const t=(u.dataset&&u.dataset.rawText)||[...bodyEl.querySelectorAll('li')].map(li=>'- '+(li.textContent||'').trim()).join('\n');
        const found=formAnswersFrom(spec,t);
        if(Object.keys(found).length) display=found;
      }
      block.appendChild(card);
      formShowLocked(card,spec,display||{},'answered');
      return;
    }

    const body=el('div','iui-form-body');
    const readers=[];  // per field: () => raw control value
    spec.fields.forEach((f,fi)=>{
      const wrap=el('div','iui-field');wrap.dataset.field=f.id;
      const lab=el('div','iui-field-label');lab.id=uid+'-l'+fi;
      lab.appendChild(document.createTextNode(f.label));
      if(f.required){const r=el('span','iui-field-req','*');r.setAttribute('aria-hidden','true');lab.appendChild(r);}
      wrap.appendChild(lab);
      const hintText=f.hint||(f.type==='multi'?L.multiHint:'');
      if(hintText){const h=el('div','iui-field-hint',hintText);h.id=uid+'-h'+fi;wrap.appendChild(h);}
      const err=el('div','iui-field-err');err.id=uid+'-e'+fi;err.setAttribute('aria-live','polite');
      const describe=n=>{n.setAttribute('aria-describedby',[hintText?uid+'-h'+fi:'',err.id].filter(Boolean).join(' '));};
      const clearErr=()=>{if(err.textContent){err.textContent='';wrap.classList.remove('is-invalid');}};
      if(f.type==='choice'||f.type==='yesno'||f.type==='multi'){
        const multi=f.type==='multi';
        const opts=f.type==='yesno'?[L.yes,L.no]:f.options;
        const group=el('div','iui-opts');
        group.setAttribute('role',multi?'group':'radiogroup');
        group.setAttribute('aria-labelledby',lab.id);
        if(f.required) group.setAttribute('aria-required','true');
        describe(group);
        let chosen=multi?new Set(f.default||[]):(f.type==='yesno'?(f.default===true?L.yes:f.default===false?L.no:''):(f.default||''));
        const buttons=[];
        const paint=()=>{
          buttons.forEach(b=>{
            const on=multi?chosen.has(b.__opt):chosen===b.__opt;
            b.setAttribute(multi?'aria-pressed':'aria-checked',on?'true':'false');
            if(!multi) b.tabIndex=(chosen?on:b===buttons[0])?0:-1;
          });
        };
        opts.forEach((o,oi)=>{
          const b=el('button','iui-opt');b.type='button';b.__opt=o;
          if(!multi) b.setAttribute('role','radio');
          if(multi) b.appendChild(iconEl('check'));
          b.appendChild(el('span','iui-opt-text',o));
          b.addEventListener('click',()=>{
            if(card.classList.contains('is-locked')) return;
            if(multi){if(chosen.has(o))chosen.delete(o);else chosen.add(o);}
            else chosen=chosen===o&&!f.required?'':o;
            paint();clearErr();
          });
          if(!multi) b.addEventListener('keydown',ev=>{
            const d={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[ev.key];
            if(!d) return;
            ev.preventDefault();
            const next=buttons[(oi+d+buttons.length)%buttons.length];
            chosen=next.__opt;paint();clearErr();next.focus();
          });
          buttons.push(b);group.appendChild(b);
        });
        paint();
        wrap.appendChild(group);
        readers.push(()=>{
          if(multi) return opts.filter(o=>chosen.has(o));
          if(f.type==='yesno') return chosen===L.yes?true:chosen===L.no?false:null;
          return chosen||null;
        });
        wrap.__focus=()=>{const b=buttons.find(x=>x.tabIndex===0)||buttons[0];if(b)b.focus();};
      } else if(f.type==='slider'){
        const row=el('div','iui-slider');
        const input=el('input','iui-range');input.type='range';
        input.min=String(f.min);input.max=String(f.max);input.step=String(f.step||1);
        input.setAttribute('aria-labelledby',lab.id);describe(input);
        let touched=f.default!=null;
        input.value=String(f.default!=null?f.default:(f.min+Math.round((f.max-f.min)/2/(f.step||1))*(f.step||1)));
        const out=el('output','iui-slider-val');out.setAttribute('aria-hidden','true');
        const show=()=>{
          const n=Number(input.value);
          input.style.setProperty('--p',((n-f.min)/(f.max-f.min)*100).toFixed(2)+'%');
          out.textContent=touched?formNumberText(n,f,l):L.slide;
          row.classList.toggle('is-untouched',!touched);
          input.setAttribute('aria-valuetext',touched?formNumberText(n,f,l):L.slide);
        };
        const touch=()=>{if(card.classList.contains('is-locked'))return;touched=true;show();clearErr();};
        input.addEventListener('input',touch);
        input.addEventListener('change',touch);
        // Clicking the thumb without moving it fires no input event.
        input.addEventListener('pointerup',touch);
        input.addEventListener('keydown',ev=>{if(/^(Arrow(Left|Right|Up|Down)|Home|End|PageUp|PageDown)$/.test(ev.key))touch();});
        show();
        const track=el('div','iui-slider-track');
        const ends=el('div','iui-slider-ends');ends.setAttribute('aria-hidden','true');
        ends.appendChild(el('span','',formNumberText(f.min,f,l)));ends.appendChild(el('span','',formNumberText(f.max,f,l)));
        track.appendChild(input);track.appendChild(ends);
        row.appendChild(track);row.appendChild(out);
        wrap.appendChild(row);
        readers.push(()=>touched?Number(input.value):null);
        wrap.__focus=()=>input.focus();
      } else {
        let input;
        if(f.type==='text'&&f.long){input=el('textarea','iui-input');input.rows=3;}
        else {input=el('input','iui-input');input.type='text';}
        input.setAttribute('aria-labelledby',lab.id);describe(input);
        if(f.required) input.setAttribute('aria-required','true');
        if(f.type==='text'){input.maxLength=FORM_LIMITS.text;input.autocomplete='off';}
        if(f.placeholder) input.placeholder=f.placeholder;
        let host=input, echo=null;
        if(f.type==='date'){
          // The browser's own date box follows the browser language (mm/dd/yyyy
          // under a Dutch label), so the box takes Dutch dates and says the
          // chosen day in words; the calendar button fills it in.
          input.autocomplete='off';input.maxLength=40;input.spellcheck=false;
          if(!f.placeholder) input.placeholder=L.datePh;
          host=el('div','iui-date');host.appendChild(input);
          const native=document.createElement('input');native.type='date';native.className='iui-date-native';
          native.tabIndex=-1;native.setAttribute('aria-hidden','true');
          if(f.min)native.min=f.min;if(f.max)native.max=f.max;
          const pick=el('button','iui-date-pick');pick.type='button';pick.setAttribute('aria-label',L.calendar);pick.title=L.calendar;
          pick.appendChild(iconEl('calendar'));
          host.appendChild(pick);host.appendChild(native);
          echo=el('div','iui-date-echo');echo.id=uid+'-d'+fi;
          const paintEcho=()=>{const iso=formDateParse(input.value,{min:f.min,max:f.max});echo.textContent=iso?formDateEcho(iso,l):'';};
          input.addEventListener('input',paintEcho);
          native.addEventListener('change',()=>{
            if(!native.value||card.classList.contains('is-locked')) return;
            input.value=formDateInput(native.value,l);paintEcho();clearErr();input.focus();
          });
          pick.addEventListener('click',()=>{
            if(card.classList.contains('is-locked')) return;
            native.value=formDateParse(input.value,{min:f.min,max:f.max})||'';
            try{if(typeof native.showPicker==='function'){native.showPicker();return;}}catch(_){}
            input.focus();
          });
          input.__paintEcho=paintEcho;
        }
        if(f.type==='number'){
          input.inputMode='decimal';input.autocomplete='off';input.maxLength=40;
          const u=formUnit(f.unit);
          host=el('div','iui-num');
          if(u.pre){const p=el('span','iui-num-unit',u.pre.trim());p.setAttribute('aria-hidden','true');host.appendChild(p);}
          host.appendChild(input);
          if(u.post){const p=el('span','iui-num-unit',u.post.trim());p.setAttribute('aria-hidden','true');host.appendChild(p);}
        }
        if(f.default!=null) input.value=f.type==='number'?new Intl.NumberFormat(l==='nl'?'nl-NL':'en-GB',{maximumFractionDigits:4,useGrouping:false}).format(f.default):f.type==='date'?formDateInput(f.default,l):String(f.default);
        if(input.__paintEcho) input.__paintEcho();
        input.addEventListener('input',clearErr);
        if(input.tagName==='INPUT') input.addEventListener('keydown',ev=>{if(ev.key==='Enter'&&!ev.isComposing){ev.preventDefault();submitForm(ev);}});
        wrap.appendChild(host);
        if(echo){wrap.appendChild(echo);input.setAttribute('aria-describedby',[echo.id,input.getAttribute('aria-describedby')||''].filter(Boolean).join(' '));}
        readers.push(()=>input.value);
        wrap.__focus=()=>input.focus();
      }
      wrap.appendChild(err);
      wrap.__err=err;
      body.appendChild(wrap);
    });
    card.appendChild(body);
    const foot=el('div','iui-form-foot');
    const hint=el('span','iui-form-hint');hint.setAttribute('aria-live','polite');
    const submit=el('button','iui-form-submit');submit.type='button';
    submit.appendChild(el('span','',spec.submit));
    foot.appendChild(hint);foot.appendChild(submit);
    card.appendChild(foot);
    body.addEventListener('click',()=>{hint.textContent='';});

    function submitForm(ev){
      if(!ev||!ev.isTrusted||card.classList.contains('is-locked')||card.classList.contains('is-pending')) return;
      if(formTurnState(block).locked){formShowLocked(card,spec,{},'answered');return;}
      if(chatBusy()){toast(tx('chipsBusy'));return;}
      const answers={};let firstBad=null, bad=0;
      const wraps=[...body.querySelectorAll('.iui-field')];
      spec.fields.forEach((f,i)=>{
        const r=formCheck(f,readers[i](),l), w=wraps[i];
        if(r.error){bad++;w.__err.textContent=r.error;w.classList.add('is-invalid');if(!firstBad)firstBad=w;}
        else{w.__err.textContent='';w.classList.remove('is-invalid');answers[f.id]=r.value;}
      });
      if(bad){hint.textContent=L.left(bad);if(firstBad&&firstBad.__focus)firstBad.__focus();return;}
      const out=formMessage(spec,answers);
      if(!out.text){hint.textContent=L.empty;return;}
      hint.textContent='';
      if(card.contains(document.activeElement)) formFocus={key,until:Date.now()+15000};
      card.classList.add('is-pending');submit.disabled=true;
      const started=sendPrompt(out.text,ok=>{
        card.classList.remove('is-pending');submit.disabled=false;
        if(!ok) return;
        saveState(key,{display:out.display});
        formShowLocked(card,spec,out.display,'sent');
      },{sentToast:L.sentToast(Object.keys(out.display).length)});
      if(!started){card.classList.remove('is-pending');submit.disabled=false;}
    }
    submit.addEventListener('click',submitForm);
    block.appendChild(card);
  }

  // A reply that names a bot by its technical id gets the display name instead
  // ("Chief Financial Bot (`synthwave-cfo`)" becomes "Chief Financial Bot").
  function humanizeBotIds(root){
    const gr=window.groupRouting;
    if(!root||!root.querySelectorAll||!gr||typeof gr.botInfo!=='function') return;
    const ID=/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
    root.querySelectorAll('.assistant-turn .msg-body code, .msg-row[data-role="assistant"] .msg-body code, .assistant-segment .msg-body code').forEach(code=>{
      if(code.closest('pre,.sp-handoff-task,.iui-card,.iui-block')) return;
      const id=(code.textContent||'').trim();
      if(!ID.test(id)) return;
      let info=null;try{info=gr.botInfo(id);}catch(_){}
      const title=info&&info.title?String(info.title).trim():'';
      if(!title) return;
      const prev=code.previousSibling,next=code.nextSibling;
      const before=prev&&prev.nodeType===3?prev.nodeValue:'';
      const m=before.match(/\s*\(\s*$/);
      const named=m&&before.slice(0,m.index).replace(/\s+$/,'').toLowerCase().endsWith(title.toLowerCase());
      if(named&&next&&next.nodeType===3&&/^\s*\)/.test(next.nodeValue)){
        prev.nodeValue=before.slice(0,m.index);next.nodeValue=next.nodeValue.replace(/^\s*\)/,'');code.remove();
      } else code.replaceWith(document.createTextNode(title));
    });
  }

  // ── Settled render (after the reply is complete) ────────────────────────
  function renderBlocks(container){
    const root=container||document;
    if(!root.querySelectorAll) return;
    prune();
    try{humanizeBotIds(root);}catch(_){}
    // Settled cards replace live ones; drop live cards left in hidden copies.
    liveCards.forEach((c,k)=>{if(!c.card.isConnected||c.card.offsetParent===null){if(c.card.isConnected&&!c.mounted)c.card.remove();liveCards.delete(k);}});
    root.querySelectorAll('.iui-block:not([data-iui-mounted])').forEach(block=>{
      block.setAttribute('data-iui-mounted','1');
      if(CHIP_LANGS.has(block.getAttribute('data-iui-kind')||'')){
        // Reply chips belong to the assistant; elsewhere the text stays plain.
        if(block.closest('.assistant-turn,.msg-row[data-role="assistant"],#liveAssistantTurn')) renderChips(block);
        else{const pre=document.createElement('pre');const c=document.createElement('code');c.textContent=block.textContent||'';pre.appendChild(c);block.replaceWith(pre);}
        return;
      }
      if(FORM_LANGS.has(block.getAttribute('data-iui-kind')||'')){
        // A questions form belongs to the assistant; elsewhere the text stays plain.
        if(block.closest('.assistant-turn,.msg-row[data-role="assistant"],#liveAssistantTurn')){
          try{renderForm(block);}
          catch(err){
            try{console.warn('[interactive-ui] form failed',err);}catch(_){}
            block.textContent='';
            formError(block,[String(err&&err.message||err||'render failed').slice(0,200)],block.getAttribute('data-iui-kind')||'form');
          }
        }
        else{const pre=document.createElement('pre');const c=document.createElement('code');c.textContent=block.textContent||'';pre.appendChild(c);block.replaceWith(pre);}
        return;
      }
      const source=block.textContent||'';
      const kindAttr=block.getAttribute('data-iui-kind')||'';
      const kit=kitKindOf(kindAttr);
      if(!kit&&!FENCE_LANGS.has(kindAttr)){
        // A data block whose helpers did not load stays readable text.
        const pre=document.createElement('pre');const c=document.createElement('code');c.textContent=source;pre.appendChild(c);block.replaceWith(pre);
        return;
      }
      const ctrl=createController(source,kit?{final:true,kit,fence:kindAttr}:{final:true});
      block.textContent='';
      block.appendChild(ctrl.card);
      if(kit&&!ctrl.parsed.spec) return;  // nothing to draw: the error bar says why
      lazyMount(ctrl);
    });
    // One chip row per reply: keep only the last.
    const turns=new Set();
    if(root.closest){const t=root.closest('.assistant-turn');if(t)turns.add(t);}
    root.querySelectorAll('.assistant-turn').forEach(t=>turns.add(t));
    turns.forEach(t=>{const hosts=t.querySelectorAll('.iui-chips-host');for(let i=0;i<hosts.length-1;i++)hosts[i].remove();});
  }

  // ── Live render while a reply streams ───────────────────────────────────
  function liveKey(text){const t=String(text||'').trim();return t.length>=24?hashSource(t.slice(0,160)):'';}
  function streamKit(code,cls){
    const fence=kitFenceOf(cls);
    if(!fence) return '';
    const pre=code.parentElement;
    if(pre.__iuiLive) return pre.__iuiLive.kit||'';
    if(pre.__iuiNotKit) return '';
    const text=code.textContent||'';
    if(!text.trim()) return '';
    // A ```chart with code in it stays a code block; only JSON (or CSV) is data.
    if(fence!=='csv'&&!/^\s*\{/.test(text)){pre.__iuiNotKit=true;return '';}
    return kitKindOf(fence);
  }
  // A questions form only appears once the reply is complete; until then a
  // quiet line stands in for it (never the raw JSON).
  function streamForm(code){
    const pre=code.parentElement;
    if(pre.__iuiForm||pre.__iuiNotForm) return;
    const text=code.textContent||'';
    if(!text.trim()) return;
    if(!/^\s*[\[{]/.test(text)){pre.__iuiNotForm=true;return;}
    pre.classList.add('iui-raw-hidden');
    const ph=document.createElement('div');ph.className='iui-form-wait iui-form-wait--live';
    ph.textContent=(FORM_TEXT[lang()]||FORM_TEXT.en).waiting;
    pre.__iuiForm=ph;
    pre.parentNode.insertBefore(ph,pre);
  }
  function streamTick(root){
    if(!root||!root.querySelectorAll) return;
    root.querySelectorAll('pre > code').forEach(code=>{
      const cls=' '+(code.className||'')+' ';
      if(/ (language-)?(suggestions|replies) /.test(cls)){code.parentElement.classList.add('iui-raw-hidden');return;}
      if(/ (language-)?(form|vraag|vragen|questions) /.test(cls)){streamForm(code);return;}
      const kit=streamKit(code,cls);
      if(!kit&&!/ (language-)?(interactive-ui|interactive|iui) /.test(cls)) return;
      const fence=kit?kitFenceOf(cls):'';
      const pre=code.parentElement;
      let ctrl=pre.__iuiLive;
      if(!ctrl){
        // The chat sometimes rebuilds the streaming text node; take over the
        // card that already shows this block instead of starting a new one.
        const text=code.textContent||'';
        const key=liveKey(text);
        const prev=key&&liveCards.get(key);
        if(prev&&!prev.card.isConnected&&!prev.final&&(prev.kit||'')===kit){
          ctrl=prev;
        } else {
          ctrl=createController(text,kit?{final:false,kit,fence}:{final:false});
          ctrl.card.classList.add('iui-live');
        }
        if(key) liveCards.set(key,ctrl);
        while(liveCards.size>20) liveCards.delete(liveCards.keys().next().value);
        pre.__iuiLive=ctrl;
        pre.classList.add('iui-raw-hidden');
        pre.parentNode.insertBefore(ctrl.card,pre);
        // A data block draws once it is complete; while it streams the card
        // only shows its title and a placeholder, without a frame.
        if(ctrl.mounted||ctrl.kit){update(ctrl,text,false);return;}
        // Only frames that are actually on screen load: the chat keeps a hidden
        // copy of the streaming text, which must not run a second widget.
        lazyMount(ctrl);
        return;
      }
      const run=()=>{ctrl.lastTick=Date.now();ctrl.tickTimer=0;if(code.isConnected)update(ctrl,code.textContent||'',false);};
      if(Date.now()-ctrl.lastTick>=STREAM_THROTTLE_MS) run();
      else if(!ctrl.tickTimer) ctrl.tickTimer=setTimeout(run,STREAM_THROTTLE_MS);
    });
  }

  window.addEventListener('message',onMessage);
  document.addEventListener('pointerdown',ev=>{
    if(!openMenu) return;
    if(ev.target&&ev.target.closest&&(ev.target.closest('.iui-menu')||ev.target.closest('.iui-actions')))return;
    closeMenu(false);
  },true);
  return {parse,renderBlocks,streamTick,allowedUrl,rewriteUrl,themeMessage,chipTexts,kitKindOf,FENCE_LANGS,CHIP_LANGS,FORM_LANGS,formSpec,formMessage,formAnswersFrom,formCheck,formNumberText,formDateParse,formDateInput,formDateEcho,formTurnState,_byWindow:byWindow,_controllers:controllers};
})();

// A reply that starts with the interactive block's title comment but has no
// fence around it is wrapped, so a model slip still shows the app.
function interactiveUiWrapBare(text){
  const s=String(text||'');
  // Already fenced: only pull title/height comments written above the fence inside it.
  if(/(^|\n)[ ]{0,3}```[ \t]*interactive-ui\b/i.test(s)){
    return s.replace(/^\s*((?:<!--[\s\S]*?-->\s*)+)([ ]{0,3}```[ \t]*interactive-ui[^\n]*\n)/i,(m,c,f)=>f+c.trim()+'\n');
  }
  const lead=s.match(/^\s*/)[0].length;
  if(!/^<!--\s*title\s*:/i.test(s.slice(lead,lead+40))) return s;
  if(!/<(style|script)\b/i.test(s)) return s;
  const ends=[/<\/script>/gi,/<\/style>/gi,/<\/div>/gi].map(re=>{let m,last=-1;while((m=re.exec(s)))last=m.index+m[0].length;return last;});
  const end=Math.max(...ends);
  if(end<=lead) return s;
  return '```interactive-ui\n'+s.slice(lead,end).trim()+'\n```\n'+s.slice(end);
}
// Copy of a reply without its suggestion buttons block.
function stripReplySuggestions(text){
  return String(text||'').replace(/(^|\n)[ ]{0,3}```[ \t]*(?:suggestions|replies)[ \t]*\n[\s\S]*?\n[ ]{0,3}```[ \t]*(?=\n|$)/gi,'$1').replace(/\s+$/,'');
}
function interactiveUiFenceAccepts(lang,code){
  const l=String(lang||'').toLowerCase();
  const c=String(code||'');
  if(!c.trim()) return false;
  if(_iui.FENCE_LANGS.has(l)||_iui.CHIP_LANGS.has(l)) return true;
  // A questions form is JSON only (an object, or a list of questions).
  if(_iui.FORM_LANGS.has(l)) return /^\s*[\[{]/.test(c);
  // Data blocks: JSON only (a ```chart with Chart.js code stays code); CSV always.
  if(_iui.kitKindOf(l)) return l==='csv'||/^\s*\{/.test(c);
  return false;
}
function renderInteractiveUiBlocks(container){_iui.renderBlocks(container);}
function interactiveUiStreamTick(root){_iui.streamTick(root);}
function parseInteractiveUiSource(source,opts){return _iui.parse(source,opts);}
