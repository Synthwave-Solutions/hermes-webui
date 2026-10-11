/* Read-only directory. The server owns app visibility and trusted destinations. */
(function () {
  'use strict';
  let allowed=false, generation=0, rows=null, loading=false, failed=false, language='', query='', category='all';
  const $=id=>document.getElementById(id);
  const copy={
    nl:{intro:'Je apps op één plek. Open een app in een nieuw tabblad; sommige apps vragen om een eigen login.',search:'Zoek een app',category:'Categorie',all:'Alle apps',creative:'Ontwerp en video',craft:'Craft Studio',automation:'Automatisering',productivity:'Documenten en kennis',platform:'Beheer en platform',download:'Download desktopapp',open:'Open app',help:'Uitleg',admin:'Beheer',unconfigured:'Nog geen browseradres gekoppeld',loading:'Apps laden…',error:'Apps konden niet worden geladen.',retry:'Opnieuw proberen',empty:'Er zijn nog geen apps voor jouw account gekoppeld.',noResults:'Geen apps gevonden. Pas je zoekterm of categorie aan.',count:'apps',language:'Taal',guide:'Interactieve gids',sidebar:'Kies een categorie of zoek op naam. Je chat blijft bewaard.'},
    en:{download:'Download desktop app',intro:'Your apps in one place. Open an app in a new tab; some apps require their own login.',search:'Search apps',category:'Category',all:'All apps',creative:'Design and video',craft:'Craft Studio',automation:'Automation',productivity:'Documents and knowledge',platform:'Management and platform',open:'Open app',help:'Guide',admin:'Admin',unconfigured:'No browser address linked yet',loading:'Loading apps…',error:'Apps could not be loaded.',retry:'Try again',empty:'No apps have been linked for your account yet.',noResults:'No apps found. Change your search or category.',count:'apps',language:'Language',guide:'Interactive guide',sidebar:'Choose a category or search by name. Your chat is preserved.'}
  };
  function lang(){if(language)return language;try{const v=localStorage.getItem('sp-apps-language')||localStorage.getItem('sp-feature-guide-language');if(copy[v])return v;}catch(_){}return document.documentElement.lang.startsWith('nl')?'nl':'en';}
  function el(tag,text,cls){const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;}
  function btn(text,fn){const n=el('button',text,'app-button');n.type='button';n.addEventListener('click',fn);return n;}
  function localized(value){return typeof value==='string'?value:value?.[lang()]||value?.en||'';}
  function appId(row){return row.id||row.module;}
  function validUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&!u.search&&!u.hash?u.href:null;}catch(_){return null;}}
  function guide(id,trigger){const feature='webui.apps.'+id;const known=window.SynthPulseFeatureCatalog?.features?.some(f=>f.id===feature);window.SynthPulseHelp?.startFeatureTour([known?feature:'webui.modules.apps'],{locale:lang(),trigger});}
  const categories=['creative','craft','automation','productivity','platform'];
  function renderList(){
    const root=$('appsList'),count=$('appsCount');if(!root)return;root.replaceChildren();const c=copy[lang()];
    if(loading){root.append(el('p',c.loading));count.textContent='';return;}
    if(failed){root.append(el('p',c.error),btn(c.retry,load));count.textContent='';return;}
    const all=rows||[],term=query.trim().toLocaleLowerCase();
    const matches=all.filter(r=>(category==='all'||(r.category||'creative')===category)&&[appId(r),localized(r.name),localized(r.description),appId(r)==='omniroute'?'omnirouter':''].join(' ').toLocaleLowerCase().includes(term));
    count.textContent=matches.length+' / '+all.length+' '+c.count;
    if(!matches.length){root.append(el('p',all.length?c.noResults:c.empty));return;}
    for(const group of categories){
      const items=matches.filter(r=>(r.category||'creative')===group);if(!items.length)continue;
      const section=el('section',null,'apps-group');section.append(el('h2',c[group]));const grid=el('div',null,'apps-grid');section.append(grid);root.append(section);
      for(const r of items){
        const id=appId(r),name=localized(r.name),card=el('article',null,'app-card');card.dataset.appId=id;card.tabIndex=-1;
        const heading=el('div',null,'app-card-heading');heading.append(el('h3',name));if(r.access==='platform')heading.append(el('span',c.admin,'app-badge'));
        card.append(heading,el('p',localized(r.description)||c.intro,'app-description'));
        const actions=el('div',null,'app-actions'),url=validUrl(r.url);
        if(url){const action=r.launch_kind==='desktop_download'?c.download:c.open;const link=el('a',action+' ↗','app-button app-open');link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.setAttribute('aria-label',action+': '+name);actions.append(link);}
        else card.append(el('p',c.unconfigured,'app-unconfigured'));
        if(r.id){const help=btn(c.help,()=>guide(id,help));help.setAttribute('aria-label',c.help+': '+name);actions.append(help);}
        card.append(actions);grid.append(card);
      }
    }
  }
  function render(){
    const root=$('mainApps');if(!root)return;root.replaceChildren();if(!allowed)return;const c=copy[lang()];
    const head=el('div',null,'apps-heading');head.append(el('h1','Apps'));
    const locale=el('select');locale.id='appsLanguage';locale.setAttribute('aria-label',c.language);
    for(const [value,text] of [['nl','Nederlands'],['en','English']]){const o=el('option',text);o.value=value;locale.append(o);}locale.value=lang();locale.addEventListener('change',()=>{language=locale.value;try{localStorage.setItem('sp-apps-language',language);}catch(_){}render();$('appsLanguage')?.focus();});
    const guideButton=btn(c.guide,()=>guide('overview',guideButton));head.append(guideButton,locale);root.append(head,el('p',c.intro,'apps-intro'));
    const toolbar=el('div',null,'apps-toolbar'),searchLabel=el('label',c.search),search=el('input');search.id='appsSearch';search.type='search';search.placeholder=c.search;search.value=query;search.addEventListener('input',()=>{query=search.value;renderList();});searchLabel.append(search);
    const filterLabel=el('label',c.category),filter=el('select');filter.id='appsCategory';
    for(const key of ['all',...categories]){if(key!=='all'&&!(rows||[]).some(r=>(r.category||'creative')===key))continue;const option=el('option',c[key]);option.value=key;filter.append(option);}if(![...filter.options].some(o=>o.value===category))category='all';filter.value=category;filter.addEventListener('change',()=>{category=filter.value;renderList();});filterLabel.append(filter);toolbar.append(searchLabel,filterLabel);root.append(toolbar);
    const count=el('p',null,'apps-count');count.id='appsCount';count.setAttribute('role','status');const list=el('div');list.id='appsList';root.append(count,list);
    if($('appsSidebar'))$('appsSidebar').textContent=c.sidebar;
    renderList();
  }
  function applyVisible(value){allowed=value===true;generation++;rows=null;loading=false;failed=false;query='';category='all';if(!allowed){$('mainApps')?.replaceChildren();$('appsSidebar')?.replaceChildren();}}
  async function load(){
    if(!allowed)return false;const mine=++generation;loading=true;failed=false;render();
    try{const result=await api('/api/apps');if(mine!==generation||!allowed)return false;rows=Array.isArray(result.apps)?result.apps:[];loading=false;render();return true;}
    catch(_){if(mine===generation&&allowed){rows=null;loading=false;failed=true;render();}return false;}
  }
  function reveal(id){
    if(!allowed)return;const previous={query,category};const changed=query!==''||category!=='all';
    function filters(){if($('appsSearch'))$('appsSearch').value=query;if($('appsCategory'))$('appsCategory').value=category;renderList();}
    query='';category='all';if(changed)filters();
    const card=[...document.querySelectorAll('#mainApps [data-app-id]')].find(n=>n.dataset.appId===id);card?.scrollIntoView({block:'nearest'});
    return ()=>{if(allowed&&changed){query=previous.query;category=previous.category;filters();}};
  }
  window.SynthPulseApps={applyVisible,load,reveal};
})();
