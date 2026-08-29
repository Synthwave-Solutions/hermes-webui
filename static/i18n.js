// ── i18n: demand-loaded locale bundles and public helpers ───────────────────
// Locale catalogs live in static/i18n/<locale>.js. English and the active
// locale are loaded at boot; additional locales are fetched only when selected.
const _I18N_LOCALE_META = {
  en:['English','en-US'],it:['Italiano','it-IT'],ja:['日本語','ja-JP'],
  ru:['Русский','ru-RU'],es:['Español','es-ES'],de:['Deutsch','de-DE'],
  zh:['简体中文','zh-CN'],'zh-Hant':['繁體中文','zh-TW'],pt:['Português','pt-PT'],
  ko:['한국어','ko-KR'],fr:['Français','fr-FR'],tr:['Türkçe','tr-TR'],
  pl:['Polski','pl-PL'],vi:['Tiếng Việt','vi-VN'],
};
const LOCALES = Object.fromEntries(Object.entries(_I18N_LOCALE_META).map(([code,meta])=>[
  code,{_lang:code,_label:meta[0],_speech:meta[1]},
]));
const _i18nLoads = new Map();
const _i18nVersion=(document.currentScript&&new URL(document.currentScript.src).searchParams.get('v'))||'__WEBUI_VERSION__';
let _locale = LOCALES.en;
let _localeCode = 'en';

function _i18nProcessedElapsed(prefix,duration){return duration?`${prefix} ${duration}`:prefix;}
function _i18nProcessedElapsedEn(duration){return _i18nProcessedElapsed('Processed',duration);}
function _i18nProcessedElapsedZh(duration){return _i18nProcessedElapsed('已处理',duration);}
function _i18nProcessedElapsedZhHant(duration){return _i18nProcessedElapsed('已處理',duration);}
function _i18nProcessedElapsedVi(duration){return _i18nProcessedElapsed('Đã xử lý',duration);}
function _i18nProcessedElapsedPl(duration){return _i18nProcessedElapsed('Przetworzono',duration);}
const _I18N_TOOL_ACTION_TEXT_EN={
  shell:{running:'Running',done:'Ran',fail:'run',fallback:'a command'},read:{running:'Reading',done:'Read',fail:'read',fallback:'a file'},list:{running:'Listing',done:'Listed',fail:'list',fallback:'files'},search:{running:'Searching',done:'Searched',fail:'search',fallback:'workspace'},web:{running:'Checking',done:'Checked',fail:'check',fallback:'web data'},write:{running:'Updating',done:'Updated',fail:'update',fallback:'a file'},skill:{running:'Loading',done:'Loaded',fail:'load',fallback:'a skill'},memory:{running:'Saving',done:'Saved',fail:'save',fallback:'memory'},delegate:{running:'Delegating',done:'Delegated',fail:'delegate',fallback:'a task'},unknown:{running:'Running',done:'Ran',fail:'run',fallback:'a tool'},
};
const _I18N_TOOL_SUMMARY_TEXT_EN={
  shell:{running:['Running a command','Running {n} commands'],done:['Ran a command','Ran {n} commands']},read:{running:['Reading a file','Reading {n} files'],done:['Read a file','Read {n} files']},list:{running:['Listing files','Listing {n} items'],done:['Listed files','Listed {n} files']},search:{running:['Searching workspace','Searching workspace {n} times'],done:['Searched workspace','Searched workspace {n} times']},web:{running:['Checking web','Checking web {n} times'],done:['Checked the web','Checked the web {n} times']},write:{running:['Updating a file','Updating {n} files'],done:['Updated a file','Updated {n} files']},skill:{running:['Loading a skill','Loading {n} skills'],done:['Loaded a skill','Loaded {n} skills']},memory:{running:['Saving memory','Saving {n} memory updates'],done:['Saved memory','Saved {n} memory updates']},delegate:{running:['Delegating a task','Delegating {n} tasks'],done:['Delegated a task','Delegated {n} tasks']},unknown:{running:['Running a tool','Running {n} tools'],done:['Ran a tool','Ran {n} tools']},
};
const _I18N_TOOL_ACTION_TEXT_ZH={..._I18N_TOOL_ACTION_TEXT_EN};
const _I18N_TOOL_SUMMARY_TEXT_ZH={..._I18N_TOOL_SUMMARY_TEXT_EN};
const _I18N_TOOL_ACTION_TEXT_ZH_HANT={..._I18N_TOOL_ACTION_TEXT_EN};
const _I18N_TOOL_SUMMARY_TEXT_ZH_HANT={..._I18N_TOOL_SUMMARY_TEXT_EN};
const _I18N_TOOL_ACTION_TEXT_VI={..._I18N_TOOL_ACTION_TEXT_EN};
const _I18N_TOOL_SUMMARY_TEXT_VI={..._I18N_TOOL_SUMMARY_TEXT_EN};
const _I18N_TOOL_ACTION_TEXT_PL={..._I18N_TOOL_ACTION_TEXT_EN};
const _I18N_TOOL_SUMMARY_TEXT_PL={..._I18N_TOOL_SUMMARY_TEXT_EN};
function _i18nToolActionLabelFromMap(map,kind,state,target,display,failed){const verbs=map[kind]||map.unknown||_I18N_TOOL_ACTION_TEXT_EN.unknown;const object=target||verbs.fallback||display||'tool';return failed?`Failed to ${verbs.fail||'run'} ${object}`:`${verbs[state]||verbs.running} ${object}`;}
function _i18nToolActionLabelEn(...args){return _i18nToolActionLabelFromMap(_I18N_TOOL_ACTION_TEXT_EN,...args);}
function _i18nToolActionLabelZh(...args){return _i18nToolActionLabelFromMap(_I18N_TOOL_ACTION_TEXT_ZH,...args);}
function _i18nToolActionLabelZhHant(...args){return _i18nToolActionLabelFromMap(_I18N_TOOL_ACTION_TEXT_ZH_HANT,...args);}
function _i18nToolActionLabelVi(...args){return _i18nToolActionLabelFromMap(_I18N_TOOL_ACTION_TEXT_VI,...args);}
function _i18nToolActionLabelPl(...args){return _i18nToolActionLabelFromMap(_I18N_TOOL_ACTION_TEXT_PL,...args);}
function _i18nToolWorklogSummaryFromMap(map,kind,state,count){const n=Math.max(1,Number(count)||1);const entry=map[kind]||map.unknown||_I18N_TOOL_SUMMARY_TEXT_EN.unknown;const form=entry[state]||entry.running;return (n===1?form[0]:form[1]).replace('{n}',String(n));}
function _i18nToolWorklogSummaryEn(...args){return _i18nToolWorklogSummaryFromMap(_I18N_TOOL_SUMMARY_TEXT_EN,...args);}
function _i18nToolWorklogSummaryZh(...args){return _i18nToolWorklogSummaryFromMap(_I18N_TOOL_SUMMARY_TEXT_ZH,...args);}
function _i18nToolWorklogSummaryZhHant(...args){return _i18nToolWorklogSummaryFromMap(_I18N_TOOL_SUMMARY_TEXT_ZH_HANT,...args);}
function _i18nToolWorklogSummaryVi(...args){return _i18nToolWorklogSummaryFromMap(_I18N_TOOL_SUMMARY_TEXT_VI,...args);}
function _i18nToolWorklogSummaryPl(...args){return _i18nToolWorklogSummaryFromMap(_I18N_TOOL_SUMMARY_TEXT_PL,...args);}
function _i18nToolSummaryJoinEn(parts){return Array.isArray(parts)?parts.filter(Boolean).join(', '):'';}
function _i18nToolSummaryJoinCjk(parts){const items=Array.isArray(parts)?parts.filter(Boolean):[];if(items.length<=1)return items[0]||'';if(items.length===2)return `${items[0]}和${items[1]}`;return `${items.slice(0,-1).join('、')}和${items.at(-1)}`;}
const _i18nToolSummaryJoinPl=_i18nToolSummaryJoinEn;
const _i18nToolSummaryJoinVi=_i18nToolSummaryJoinEn;

window.__registerHermesLocale=function(code,bundle){
  LOCALES[code]=bundle;
  if(code===_localeCode)_locale=bundle;
};
function resolveLocale(lang){
  if(typeof lang!=='string')return null;
  const lower=lang.trim().toLowerCase().replace(/_/g,'-');
  if(!lower)return null;
  const direct=Object.keys(LOCALES).find(k=>k.toLowerCase()===lower);
  if(direct)return direct;
  if(lower==='zh'||lower.startsWith('zh-cn')||lower.startsWith('zh-sg')||lower.startsWith('zh-hans'))return 'zh';
  if(lower.startsWith('zh-tw')||lower.startsWith('zh-hk')||lower.startsWith('zh-mo')||lower.startsWith('zh-hant'))return 'zh-Hant';
  return Object.keys(LOCALES).find(k=>k.toLowerCase()===lower.split('-')[0])||null;
}
function resolvePreferredLocale(primary,fallback){return resolveLocale(primary)||resolveLocale(fallback)||'en';}
function _localeBundleUrl(code){
  return new URL(`static/i18n/${encodeURIComponent(code)}.js?v=${encodeURIComponent(_i18nVersion)}`,document.baseURI||location.href).href;
}
function loadLocaleBundle(code){
  const resolved=resolveLocale(code)||'en';
  if(LOCALES[resolved]&&Object.keys(LOCALES[resolved]).length>3)return Promise.resolve(LOCALES[resolved]);
  if(_i18nLoads.has(resolved))return _i18nLoads.get(resolved);
  const promise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=_localeBundleUrl(resolved);s.async=true;s.onload=()=>resolve(LOCALES[resolved]);s.onerror=()=>reject(new Error(`Locale bundle failed to load: ${resolved}`));document.head.appendChild(s);});
  _i18nLoads.set(resolved,promise);
  return promise;
}
function t(key,...args){const val=_locale[key]??LOCALES.en[key];if(val===undefined)return key;if(typeof val==='function')return val(...args);return args.length?String(val).replace(/\{(\d+)\}/g,(m,i)=>Object.prototype.hasOwnProperty.call(args,i)?String(args[i]):m):val;}
function setLocale(lang){
  const resolved=resolveLocale(lang)||'en';
  _localeCode=resolved;
  if(LOCALES[resolved])_locale=LOCALES[resolved];
  try{localStorage.setItem('hermes-lang',resolved);}catch(_){}
  document.documentElement.lang=(_I18N_LOCALE_META[resolved]||[])[1]||resolved;
  return Promise.all([loadLocaleBundle('en'),loadLocaleBundle(resolved)]).then(()=>{_locale=LOCALES[resolved]||LOCALES.en;document.documentElement.lang=_locale._speech||resolved;if(typeof applyLocaleToDOM==='function')applyLocaleToDOM();return resolved;});
}
function loadLocale(){let stored=null;try{stored=localStorage.getItem('hermes-lang');}catch(_){}return setLocale(resolvePreferredLocale(null,stored));}
function applyLocaleToDOM(){
  document.querySelectorAll('[data-i18n]').forEach(el=>{const key=el.getAttribute('data-i18n'),val=t(key);if(val&&val!==key)el.textContent=val;});
  document.querySelectorAll('[data-i18n-title]').forEach(el=>{const key=el.getAttribute('data-i18n-title'),val=t(key);if(!val||val===key)return;if(el.hasAttribute('data-tooltip')){el.setAttribute('data-tooltip',val);el.removeAttribute('title');}else el.title=val;});
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el=>{const key=el.getAttribute('data-i18n-placeholder'),val=t(key);if(val&&val!==key)el.placeholder=val;});
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el=>{const key=el.getAttribute('data-i18n-aria-label'),val=t(key);if(val&&val!==key)el.setAttribute('aria-label',val);});
  if(typeof syncAppTitlebar==='function')syncAppTitlebar();
  // Chip labels that JS owns (their text depends on state, not on a fixed
  // data-i18n key) have to be re-rendered after a locale switch.
  if(typeof syncChatModeChip==='function')syncChatModeChip();
  if(typeof syncGroupPeopleChip==='function')syncGroupPeopleChip();
}
window.i18nReady=loadLocale().catch(err=>{console.warn('[i18n] using English metadata fallback',err);_locale=LOCALES.en;});
