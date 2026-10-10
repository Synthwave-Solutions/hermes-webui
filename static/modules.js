/* Read-only installation modules. The server is the permission boundary. */
(function () {
  'use strict';
  let language = '', generation = 0, modulesAllowed = false, moduleRows = null, apps = [];
  let popover = null, fetching = null;
  const byId = id => document.getElementById(id);
  function lang() {
    if (language) return language;
    try { const saved=localStorage.getItem('sp-modules-language')||localStorage.getItem('sp-feature-guide-language'); if(['nl','en'].includes(saved))return saved; } catch (_) {}
    return document.documentElement.lang.toLowerCase().startsWith('nl')?'nl':'en';
  }
  function content() { return window.SynthPulseModuleContent.locales[lang()] || window.SynthPulseModuleContent.locales.en; }
  function el(tag, text, cls) { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; }
  function button(text, fn) { const n=el('button',text,'module-button'); n.type='button'; n.addEventListener('click',fn); return n; }
  function languagePicker() {
    const label=el('label',content().ui.language+' ', 'module-language'); const select=el('select'); select.setAttribute('aria-label',content().ui.language);
    for(const [value,name] of [['nl','Nederlands'],['en','English']]) {const o=el('option',name);o.value=value;select.append(o);}
    select.value=lang(); select.addEventListener('change',()=>{const inApps=!!popover?.contains(select);language=select.value;try{localStorage.setItem('sp-modules-language',language);}catch(_){}render();if(popover)renderApps();(inApps?popover:byId('mainModules'))?.querySelector('select')?.focus();});label.append(select);return label;
  }
  function closeApps(focus=false) { if(popover){popover.remove();popover=null;} const b=byId('btnApps');if(b){b.setAttribute('aria-expanded','false');if(focus)b.focus();} }
  function hide() {
    modulesAllowed=false; moduleRows=null;apps=[];closeApps();
    document.querySelectorAll('[data-module-gated]').forEach(n=>{n.hidden=true;});
    window._moduleHiddenNav=['modules','knowledge','meetings'];
    const main=byId('mainModules');if(main)main.replaceChildren();
  }
  function apply(settings) {
    hide();
    const nav=settings && settings.module_nav;
    if(!nav || !Array.isArray(nav.hidden_panels) || !Array.isArray(settings.enabled_modules))return;
    modulesAllowed=nav.modules_visible===true;
    window._moduleHiddenNav=nav.hidden_panels.concat(modulesAllowed?[]:['modules']);
    document.querySelectorAll('[data-module-gated]').forEach(n=>{
      if(n.id==='btnApps')n.hidden=nav.apps_visible!==true;
      else if(n.dataset.panel==='modules')n.hidden=!modulesAllowed;
      else if(n.dataset.module)n.hidden=!settings.enabled_modules.includes(n.dataset.module);
      else if(n.dataset.panel)n.hidden=window._moduleHiddenNav.includes(n.dataset.panel);
    });
    for(const id of nav.hidden_composer_controls||[]){const n=byId(id);if(n)n.hidden=true;}
    for(const id of nav.hidden_settings_sections||[]){document.querySelectorAll('[data-settings-section]').forEach(n=>{if(n.dataset.settingsSection===id)n.hidden=true;});}
    if(typeof _applyTabVisibility==='function' && typeof _getHiddenTabs==='function')_applyTabVisibility(_getHiddenTabs());
  }
  async function refresh() {
    const mine=++generation;hide();
    try {const settings=await api('/api/settings');if(mine===generation)apply(settings);} catch(_){if(mine===generation)hide();}
  }
  function render() {
    const root=byId('mainModules');if(!root)return;root.replaceChildren();if(!modulesAllowed)return;
    const c=content(), ui=c.ui;const head=el('div',null,'modules-heading');head.append(el('h1',ui.title),languagePicker());root.append(head,el('p',ui.intro,'modules-intro'));
    if(!moduleRows){root.append(el('p',ui.error),button(ui.retry,load));return;}
    const list=el('div',null,'module-list');root.append(list);
    moduleRows.forEach(row=>{
      const text=c.modules[row.id];if(!text)return;
      const card=el('article',null,'module-card');card.dataset.moduleId=row.id;
      const top=el('div',null,'module-card-heading');top.append(el('h2',text.name),el('span',ui[row.status]||ui.unavailable,'module-status'));card.append(top,el('p',text.summary));
      if(row.reason)card.append(el('p',ui.reasons[row.reason]||ui.unavailable));
      card.append(el('p',ui.usage+': '+(ui[row.model_usage]||ui.none),'module-meta'));
      if(row.status==='active')card.append(el('p',ui.local,'module-meta'));
      if(row.tier==='advanced'){
        card.append(el('p',ui.price,'module-meta'));
        if(row.confirmed===false)card.append(el('p',ui.pilot,'module-meta'));
        const details=el('details');details.append(el('summary',ui.request),el('p',ui.contact));card.append(details);
      }
      const links=Array.isArray(row.works_with)?row.works_with:[];
      if(links.length){const details=el('details');details.append(el('summary',ui.works));const ul=el('ul');links.forEach(link=>{
        const li=el('li');const name=(link.name||{})[lang()]||(link.name||{}).en||'';
        const others=(link.other_modules||[]).filter(m=>c.modules[m]).map(m=>c.modules[m].name).join(', ');
        const status=link.status==='active'?ui.connected:link.status==='needs_module'?ui.needs+others:ui.off;
        li.append(el('strong',name),el('p',status));if((link.consent||[]).some(v=>v!=='none'))li.append(el('p',ui.consent,'module-meta'));ul.append(li);
      });details.append(ul);card.append(details);}
      list.append(card);
    });
  }
  async function load() {
    if(!modulesAllowed)return false;
    const mine=generation;
    try {const result=await api('/api/org/modules');if(mine!==generation||!modulesAllowed)return false;moduleRows=Array.isArray(result.modules)?result.modules:[];render();return true;}
    catch(_){if(mine===generation){moduleRows=null;render();}return false;}
  }
  function renderApps() {
    if(!popover)return;const c=content();popover.replaceChildren();const head=el('div',null,'modules-heading');head.append(el('h2',c.ui.apps),button(c.ui.close,()=>closeApps(true)));popover.append(head,languagePicker());
    const list=el('div',null,'app-links');
    apps.forEach(app=>{let u;try{u=new URL(app.url);}catch(_){return;}if(u.protocol!=='https:'||u.username||u.password)return;
      const a=el('a',(app.name||{})[lang()]||(app.name||{}).en||'');a.href=app.url;a.target='_blank';a.rel='noopener noreferrer';list.append(a);});
    popover.append(list.children.length?list:el('p',c.ui.empty));
  }
  async function openApps() {
    if(popover){closeApps(true);return;}if(fetching)return;
    const mine=generation;const b=byId('btnApps');if(!b||b.hidden)return;
    fetching=api('/api/apps');
    try {const result=await fetching;if(mine!==generation||b.hidden)return;apps=Array.isArray(result.apps)?result.apps:[];popover=el('div',null,'apps-popover');popover.id='appsPopover';popover.setAttribute('role','dialog');popover.setAttribute('aria-label',content().ui.apps);document.body.append(popover);renderApps();b.setAttribute('aria-expanded','true');popover.querySelector('button').focus();}
    catch(_){if(typeof toast==='function')toast(content().ui.error);}finally{fetching=null;}
  }
  document.addEventListener('keydown',e=>{if(!popover)return;if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();closeApps(true);}else if(e.key==='Tab'){const nodes=[...popover.querySelectorAll('a,button,select')];const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}},true);
  document.addEventListener('pointerdown',e=>{if(popover&&!popover.contains(e.target)&&!byId('btnApps').contains(e.target))closeApps();});
  window.SynthPulseModules={apply,refresh,load,canOpen:name=>!window._moduleHiddenNav?.includes(name),openApps};
  document.addEventListener('DOMContentLoaded',()=>{byId('btnApps')?.addEventListener('click',openApps);refresh();});
})();
