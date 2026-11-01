/* Searchable static feature documentation. Search terms never leave the browser. */
(function () {
  'use strict';
  const W = window.SynthPulseFeatureCatalog, M = window.SynthPulseMspFeatureCatalog;
  if (!W || W.schema_version !== 1) return;
  const mspNames={access:['Access','Toegang'],channels:['Channels','Kanalen'],clients:['Clients','Klanten'],commercial:['Commercial modules','Commerciële modules'],credentials:['Credentials','Inloggegevens'],identity:['Identity','Identiteit'],jobs:['Jobs','Taken'],modules:['Modules','Modules'],operations:['Operations','Beheer'],providers:['Providers','Providers'],review:['Review','Controle'],security:['Security','Beveiliging'],service:['Service desk','Servicedesk'],support:['Support','Ondersteuning'],target:['Deployment target','Installatiebestemming'],team:['Team','Team']};
  const C={areas:{...W.areas},features:W.features.map(f=>({...f,product:'webui'}))};
  if(M&&M.schema_version===1){
    for(const f of M.features){const area='msp_'+f.area,names=mspNames[f.area]||[f.area,f.area];C.areas[area]={en:'MSP · '+names[0],nl:'MSP · '+names[1]};C.features.push({...f,area,product:'msp'});}
  }
  const features = C.features, byId = new Map(features.map(f => [f.id, f]));
  const copy = {
    en: {title:'Feature guide',intro:'Find a control, learn when to use it and check its limits.',search:'Search features',placeholder:'For example: mute, memory, model',area:'Area',all:'All areas',status:'Availability',allStatus:'All statuses',available:'Implemented',conditional:'Requires configuration or permissions',planned:'Planned',legend:'Availability describes the software, not your current access. Conditional features may be disabled. Planned features are not available yet.',product:'Product',allProducts:'All products',language:'Guide language',close:'Close guide',results:'results',empty:'No matching features. Try another term or clear the filters.',clear:'Clear search and filters',purpose:'What it does',when:'When to use it',steps:'How to use it',permissions:'Access required',limits:'Limits and cautions',example:'Example',related:'Related features',download:'Download bilingual catalogs',link:'Copy feature link',copied:'Feature link copied.',copyFailed:'Could not copy the link. Copy it from the field below.',context:'Features on this page',guide:'Browse all features',privacy:'Search uses this static catalog only. It does not send your query or read your conversations.',unknown:'This feature link was not found. Search the guide to find a current topic.',count:'features',back:'Back to results',tourFailed:'The interactive guide could not start. The complete explanation remains available below.',tour:'Start interactive guide',tourResults:'Guide through these results',show:'Show control',notVisible:'This control is not visible on the current page. This guide does not open restricted sections or change settings.'},
    nl: {title:'Functiegids',intro:'Vind een bediening, lees wanneer je die gebruikt en controleer de grenzen.',search:'Functies zoeken',placeholder:'Bijvoorbeeld: dempen, geheugen, model',area:'Onderdeel',all:'Alle onderdelen',status:'Beschikbaarheid',allStatus:'Alle statussen',available:'Geïmplementeerd',conditional:'Vereist configuratie of rechten',planned:'Gepland',legend:'Beschikbaarheid beschrijft de software, niet je huidige toegang. Voorwaardelijke functies kunnen uitstaan. Geplande functies zijn nog niet beschikbaar.',product:'Product',allProducts:'Alle producten',language:'Taal van de gids',close:'Gids sluiten',results:'resultaten',empty:'Geen passende functies. Probeer een ander zoekwoord of wis de filters.',clear:'Zoekopdracht en filters wissen',purpose:'Wat het doet',when:'Wanneer je dit gebruikt',steps:'Hoe je dit gebruikt',permissions:'Benodigde toegang',limits:'Grenzen en aandachtspunten',example:'Voorbeeld',related:'Verwante functies',download:'Tweetalige catalogi downloaden',link:'Functielink kopiëren',copied:'Functielink gekopieerd.',copyFailed:'De link kon niet worden gekopieerd. Kopieer deze uit het veld hieronder.',context:'Functies op deze pagina',guide:'Alle functies bekijken',privacy:'Zoeken gebruikt alleen deze statische catalogus. Je zoekopdracht wordt niet verstuurd en je gesprekken worden niet gelezen.',unknown:'Deze functielink is niet gevonden. Zoek in de gids naar een actueel onderwerp.',count:'functies',back:'Terug naar resultaten',tourFailed:'De interactieve gids kon niet starten. De volledige uitleg blijft hieronder beschikbaar.',tour:'Interactieve uitleg starten',tourResults:'Rondleiding langs deze resultaten',show:'Bediening aanwijzen',notVisible:'Deze bediening is niet zichtbaar op de huidige pagina. De gids opent geen afgeschermde onderdelen en wijzigt geen instellingen.'}
  };
  const pageAreas = {group_chat:'chat',voice_mode:'voice',realtime_voice:'voice',profiles:'bots',bot_builder:'bots',profile_switching:'bots',kanban:'boards',todos:'boards',workspaces:'files',workspace_files:'files',integrations:'connections',insights:'operations',approvals:'governance',logs:'operations',plugins:'operations',modules:'modules',apps:'apps'};
  let locale = '', dialog = null, trigger = null, selected = '', query = '', area = '', status = '', product = '';
  let refs = {};
  let view = 'results', filtersOpen = false;
  const extraCopy = {
    en: {filters:'Filters',about:'About this guide',details:'Access and limitations',intro:'What would you like to do? Find a short explanation and follow the steps.'},
    nl: {filters:'Filters',about:'Over deze gids',details:'Toegang en aandachtspunten',intro:'Wat wil je doen? Vind een korte uitleg en volg de stappen.'},
  };
  function lang() {
    if (locale) return locale;
    try { const stored=localStorage.getItem('sp-feature-guide-language'); if(stored==='nl'||stored==='en')return stored; } catch (_) {}
    try { if (typeof _localeCode==='string'&&_localeCode.toLowerCase().startsWith('nl')) return 'nl';
      if(localStorage.getItem('hermes-lang')==='en')return 'en'; } catch (_) {}
    return String(navigator.language||'').toLowerCase().startsWith('nl')?'nl':'en';
  }
  function text(key) {return extraCopy[locale||lang()][key] || copy[locale||lang()][key];}
  function node(tag, cls, value) {const n=document.createElement(tag);if(cls)n.className=cls;if(value)n.textContent=value;return n;}
  function button(label,fn,cls) {const n=node('button',cls||'sp-guide-button',label);n.type='button';n.addEventListener('click',fn);return n;}
  function labelFor(label,control) {const n=node('label','sp-guide-field');n.append(node('span','',label),control);return n;}
  function option(value,label) {const n=node('option','',label);n.value=value;return n;}
  function normalize(s) {return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();}
  const searchIndex=new Map(features.map(f=>[f.id,normalize([f.id,f.area,...['en','nl'].flatMap(l=>Object.values(f.locales[l]).flat())].join(' '))]));
  function matches(f) {return (!product||f.product===product)&&(!area||f.area===area)&&(!status||f.status===status)&&normalize(query).trim().split(/\s+/).every(word=>searchIndex.get(f.id).includes(word));}
  function close() {if(dialog&&dialog.open)dialog.close();}
  function announce(value) {refs.notice.textContent=value;}
  function showDetail() {
    view='detail';dialog.dataset.view=view;refs.detail.scrollTop=0;
    refs.detail.querySelector('h2')?.focus({preventScroll:true});
  }
  function showResults() {
    view='results';dialog.dataset.view=view;
    (refs.results.querySelector('[aria-current="true"]')||refs.search).focus({preventScroll:true});
  }
  function showControl(f) {
    for(const anchor of f.anchors||[]) {
      if(!/^#[A-Za-z][\w-]*$/.test(anchor))continue;
      const target=document.getElementById(anchor.slice(1));
      if(!target||target.disabled||target.type==='hidden'||target.closest('[hidden],[inert]')||!target.getClientRects().length||getComputedStyle(target).visibility==='hidden')continue;
      trigger=target;close();target.scrollIntoView({block:'center',behavior:'instant'});target.focus({preventScroll:true});return;
    }
    announce(text('notVisible'));
  }
  function renderDetail() {
    const f=byId.get(selected),d=refs.detail;d.replaceChildren();
    if(!f)return;
    const item=f.locales[locale];d.lang=locale;
    const back=button('← '+text('back'),showResults,'sp-guide-back');back.dataset.guideBack='';d.append(back);
    const title=node('h2','',item.title);title.id='spGuideFeatureTitle';title.tabIndex=-1;
    d.append(node('p','sp-guide-eyebrow',C.areas[f.area][locale]),title,node('span','sp-guide-badge sp-guide-'+f.status,text(f.status)));
    const detail=node('details','sp-guide-access');detail.append(node('summary','',text('details')));
    for(const key of ['purpose','steps','when','example','permissions','limits']) {
      const section=node('section','sp-guide-section');section.append(node('h3','',text(key)));
      if(key==='steps'){const list=node('ol');item.steps.forEach(step=>list.append(node('li','',step)));section.append(list);}
      else section.append(node('p','',item[key]));
      if(key==='permissions'||key==='limits')detail.append(section);
      else d.append(section);
      if(key==='purpose')d.append(button(text('tour'),()=>startInteractive([f.id]),'sp-guide-primary'));
    }
    d.append(detail);
    const actions=node('div','sp-guide-actions');
    actions.append(button(text('link'),async()=>{
      const url=new URL(location.href);url.searchParams.set('help_feature',f.id);
      try {await navigator.clipboard.writeText(url.href);announce(text('copied'));}
      catch(_){announce(text('copyFailed'));const field=node('input','sp-guide-link-copy');field.value=url.href;field.readOnly=true;field.setAttribute('aria-label',text('link'));refs.notice.append(field);field.focus();field.select();}
    }));
    if(f.anchors.some(a=>a.startsWith('#')))actions.append(button(text('show'),()=>showControl(f)));
    d.append(actions);
    if(f.related.length){const section=node('section','sp-guide-section');section.append(node('h3','',text('related')));
      for(const id of f.related){const other=byId.get(id);if(other)section.append(button(other.locales[locale].title,()=>{selected=id;area='';status='';query='';product='';refs.product.value='';refs.search.value='';refs.area.value='';refs.status.value='';renderResults();showDetail();},'sp-guide-related'));}d.append(section);}
  }
  function renderResults() {
    const filtered=features.filter(matches);refs.results.replaceChildren();
    refs.count.textContent=filtered.length+' '+text('results');
    if(!filtered.some(f=>f.id===selected))selected=filtered[0]?.id||'';
    if(!selected){view='results';dialog.dataset.view=view;}
    if(refs.tour)refs.tour.disabled=!filtered.length;
    if(!filtered.length)refs.results.append(node('p','sp-guide-empty',text('empty')));
    for(const f of filtered){const b=button('',()=>{selected=f.id;renderResults();showDetail();},'sp-guide-result');
      b.dataset.feature=f.id;b.setAttribute('aria-current',String(selected===f.id));b.append(node('span','',f.locales[locale].title),node('small','',C.areas[f.area][locale]+' · '+text(f.status)));refs.results.append(b);}
    renderDetail();
  }
  function build() {
    dialog.replaceChildren();dialog.lang=locale;dialog.dataset.view=view;dialog.setAttribute('aria-labelledby','spGuideTitle');
    const header=node('header','sp-guide-header');const heading=node('div');const title=node('h1','',text('title'));title.id='spGuideTitle';heading.append(title,node('p','',text('intro')));
    const language=node('select');language.id='spGuideLanguage';language.setAttribute('aria-label',text('language'));language.append(option('en','English'),option('nl','Nederlands'));language.value=locale;
    language.addEventListener('change',()=>{locale=language.value;try{localStorage.setItem('sp-feature-guide-language',locale);}catch(_){}build();document.getElementById('spGuideLanguage').focus();refreshEntry();});
    header.append(heading,labelFor(text('language'),language),button(text('close'),close,'sp-guide-close'));dialog.append(header);
    const tools=node('div','sp-guide-tools');refs.search=node('input');refs.search.type='search';refs.search.id='spGuideSearch';refs.search.placeholder=text('placeholder');refs.search.autocomplete='off';refs.search.value=query;
    refs.search.addEventListener('input',()=>{query=refs.search.value;renderResults();});
    refs.product=node('select');refs.product.id='spGuideProduct';refs.product.append(option('',text('allProducts')),option('webui','WebUI'),option('msp','MSP'));refs.product.value=product;refs.product.addEventListener('change',()=>{product=refs.product.value;area='';refs.area.value='';renderResults();});
    refs.area=node('select');refs.area.id='spGuideArea';refs.area.append(option('',text('all')));for(const [id,labels] of Object.entries(C.areas))refs.area.append(option(id,labels[locale]));refs.area.value=area;refs.area.addEventListener('change',()=>{area=refs.area.value;renderResults();});
    refs.status=node('select');refs.status.id='spGuideStatus';refs.status.append(option('',text('allStatus')),...['available','conditional','planned'].map(s=>option(s,text(s))));refs.status.value=status;refs.status.addEventListener('change',()=>{status=refs.status.value;renderResults();});
    tools.append(labelFor(text('search'),refs.search));
    const filters=node('details','sp-guide-filters');filters.open=filtersOpen;
    filters.append(node('summary','',text('filters')));
    const fields=node('div','sp-guide-filter-fields');fields.append(labelFor(text('product'),refs.product),labelFor(text('area'),refs.area),labelFor(text('status'),refs.status));filters.append(fields);
    filters.addEventListener('toggle',()=>{filtersOpen=filters.open;});tools.append(filters);dialog.append(tools);
    const meta=node('div','sp-guide-meta');refs.count=node('span');refs.count.id='spGuideCount';refs.count.setAttribute('role','status');refs.tour=button(text('tourResults'),()=>startInteractive(features.filter(matches).map(f=>f.id)));meta.append(refs.count,refs.tour,button(text('clear'),()=>{query='';area='';status='';product='';refs.product.value='';refs.search.value='';refs.area.value='';refs.status.value='';renderResults();refs.search.focus();}));dialog.append(meta);
    const body=node('div','sp-guide-body');refs.results=node('nav','sp-guide-results');refs.results.setAttribute('aria-label',text('results'));refs.detail=node('article','sp-guide-detail');body.append(refs.results,refs.detail);dialog.append(body);
    const footer=node('footer','sp-guide-footer');refs.notice=node('p','sp-guide-notice');refs.notice.setAttribute('role','status');
    const about=node('details');about.append(node('summary','',text('about')),node('p','',text('legend')),node('p','',text('privacy')));
    footer.append(refs.notice,about,button(text('download'),download));dialog.append(footer);renderResults();
  }
  function download() {
    const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:1,catalogs:[W,...(M?[M]:[])]},null,2)+'\n'],{type:'application/json'}));const a=node('a');a.href=url;a.download='synthpulse-feature-catalog.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function open(opts) {
    opts=opts||{};const wasOpen=dialog?.open;const requested=String(opts.feature||'');
    if(!wasOpen)trigger=opts.trigger||document.activeElement;
    if(window.SynthPulseHelp)window.SynthPulseHelp.closeAll();
    locale=opts.locale==='nl'||opts.locale==='en'?opts.locale:lang();
    const context=pageAreas[opts.area]||opts.area;area=C.areas[context]?context:'';product='webui';status='';query='';selected=byId.has(requested)?requested:'';
    view=selected?'detail':'results';filtersOpen=window.innerWidth>640;
    if(selected){area=byId.get(selected).area;product=byId.get(selected).product;}
    if(!dialog){dialog=node('dialog','sp-feature-guide');dialog.id='spFeatureGuide';dialog.addEventListener('keydown',event=>{event.stopPropagation();if(event.key==='Escape'&&!event.isComposing){event.preventDefault();close();}});dialog.addEventListener('close',()=>{const old=trigger;trigger=null;const target=old?.isConnected?old:document.getElementById('btnPageHelp');target?.focus({preventScroll:true});});document.body.append(dialog);}
    build();if(!dialog.open)dialog.showModal();
    if(view==='detail'&&window.innerWidth<=640)showDetail();else refs.search.focus();
    if(requested&&!byId.has(requested))announce(text('unknown'));return true;
  }
  async function startInteractive(ids) {
    if(!window.SynthPulseHelp?.startFeatureTour)return false;
    close();
    // The modal close event must finish restoring focus before the tour opens.
    await new Promise(resolve=>setTimeout(resolve,0));
    const started=window.SynthPulseHelp.startFeatureTour(ids,{locale:locale||lang(),trigger:document.getElementById('btnPageHelp')});
    if(!started){open({feature:ids[0],locale});announce(text('tourFailed'));}
    return started;
  }
  function featuresForPage(page) {
    const map=window.SynthPulseFeatureTargets||{};
    const special={group_chat:'chat',voice_mode:'voice',realtime_voice:'voice',bot_builder:'bots',profile_switching:'bots',workspace_files:'files'};
    if(special[page])return features.filter(f=>f.product==='webui'&&f.area===special[page]);
    const sections=new Set(['conversation','appearance','access','preferences','providers','plugins','extensions','system','help']);
    if(sections.has(page))return features.filter(f=>f.product==='webui'&&map[f.id]?.panel==='settings'&&map[f.id]?.section===page);
    const panel={bots:'profiles',boards:'kanban',connections:'integrations',files:'workspaces'}[page]||page;
    return features.filter(f=>f.product==='webui'&&(map[f.id]?.panel===panel||(!map[f.id]&&f.area===(pageAreas[page]||page))));
  }
  function refreshEntry() {const b=document.getElementById('helpCardGuide');if(b)b.textContent=copy[lang()].guide;}
  document.addEventListener('click',event=>{const b=event.target.closest?.('[data-help-guide]');if(b){event.preventDefault();open({area:b.dataset.helpGuide,trigger:b});}});
  function init(){refreshEntry();const id=new URL(location.href).searchParams.get('help_feature');if(id)open({feature:id});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  window.SynthPulseFeatureGuide=Object.freeze({open,close,download,contextLabel:()=>copy[lang()].context,featureCount:features.length,getFeature:id=>byId.get(id)||null,featuresForPage,featureIds:()=>features.map(f=>f.id),language:lang,setLanguage:value=>{if(value==='nl'||value==='en')locale=value;},startInteractive});
})();
