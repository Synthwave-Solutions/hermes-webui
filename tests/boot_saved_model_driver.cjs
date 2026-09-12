// Isolated execution of the real saved-session boot branch and model helpers.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(__dirname, '..');
const scenario = JSON.parse(process.argv[3] || '{}');
const boot = fs.readFileSync(path.join(root, 'static/boot.js'), 'utf8');
const ui = fs.readFileSync(path.join(root, 'static/ui.js'), 'utf8');
const messages = fs.readFileSync(path.join(root, 'static/messages.js'), 'utf8');
function block(source, start, end) { return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))); }
function fn(source, name) {
  const match = new RegExp('(?:async\\s+)?function\\s+' + name + '\\s*\\(').exec(source);
  if (!match) throw Error('Missing function ' + name);
  let at = source.indexOf('(', match.index), depth = 1;
  for (at++; depth; at++) { if (source[at] === '(') depth++; if (source[at] === ')') depth--; }
  at = source.indexOf('{', at); depth = 1;
  for (at++; depth; at++) { if (source[at] === '{') depth++; if (source[at] === '}') depth--; }
  return source.slice(match.index, at);
}
class Node {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.style = {}; this.textContent = ''; this.classList = {contains:()=>false}; }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  removeChild(child) { this.children=this.children.filter(node=>node!==child); child.parentElement=null; }
}
class Select extends Node {
  constructor() { super('select'); this.id = 'modelSelect'; this._value = ''; }
  get options() { return this.children.flatMap(c => c.tagName === 'OPTGROUP' ? c.children : [c]); }
  set value(value) { this._value = this.options.some(o=>o.value === value) ? value : ''; this.options.forEach(o=>o._selected = o.value === this._value); }
  get value() { return this._value; }
  get selectedIndex() { return this.options.findIndex(o=>o._selected); }
  get selectedOptions() { return this.options.filter(o=>o._selected).slice(0,1); }
  set innerHTML(_) { this.children = []; this._value = ''; }
  querySelector() { return this.options[0] || null; }
  querySelectorAll(selector) { return selector === 'optgroup' ? this.children.filter(c=>c.tagName==='OPTGROUP') : this.options; }
}
const select = new Select();
function createNode(tag) {
  const node = new Node(tag);
  if (tag.toLowerCase()==='option') Object.defineProperty(node, 'selected', {
    get:()=>!!node._selected,
    set:value=>{ if(value) { select.options.forEach(o=>o._selected=false); node._selected=true; select._value=node.value; } }
  });
  return node;
}
function addOption(value, provider) { const option=createNode('option'); option.value=value; option.dataset.provider=provider; option.textContent=value; select.appendChild(option); select.value=value; }
addOption('gpt-6-astra', 'openai-codex');
const storage = () => ({getItem:()=>null, setItem(){}, removeItem(){}});
const calls = {models:0, metadata:0, ready:0, mutation:0, explicitUpdates:0};
const visible = {transcript:'', label:'', botsDisabled:true};
const savedSession = {session_id:'saved', model:'codex/gpt-6-astra', model_provider:'custom:omniroute', message_count:2, ...scenario.session};
Object.assign(globalThis, {window:globalThis, S:{session:null, activeProfile:'default', _bootReady:false},
  document:{baseURI:'http://fixture/session/saved', createElement:createNode},
  location:{pathname:'/session/saved',search:''}, localStorage:storage(), sessionStorage:storage(),
  _loadSessionGeneration:0, _bootRestoreGeneration:0, _bootDraftInputGeneration:0,
  urlSession:'saved', savedLocal:null, prefillIntent:null,
  _profileSwitchCompleted:false, _profileSwitchChangedProfile:false,
  _dynamicModelLabels:{}, _defaultModel:'gpt-6-astra', _activeProvider:'openai-codex',
  _configuredModelBadges:{}, _modelDropdownRequestSeq:0, _modelCatalogFallbackRetried:false,
  _liveModelFetchPending:new Set(), _liveModelCache:{},
  _persistSessionModelCorrection:()=>{calls.mutation++;},
  api:async(url, opts)=>{ if(url!=='/api/session/update'||opts.method!=='POST') throw Error('Unexpected API'); calls.explicitUpdates++; return {}; },
  _applySessionContextMetadataUpdate:()=>{},
  $:id=>id==='modelSelect' ? (scenario.noSelect ? null : select) : null,
  getModelLabel:id=>id, _fetchLiveModels:()=>{}, syncReasoningChip:()=>{},
  syncWorkspacePanelState:()=>{}, renderSessionList:async()=>{},
  _finalizeComposerPrefillOnBoot:async()=>{}, checkInflightOnBoot:async()=>{},
  _rootPrefillNeedsFreshComposer:()=>false, _isRestoredPersonalScratchSession:()=>false,
  _isCompactWorkspaceViewport:()=>false, _redirectIfUnauth:()=>false,
  dispatchEvent:event=>{ if(event.type==='synpulse:boot-ready') { calls.ready++; visible.botsDisabled=false; } },
  syncModelChip:()=>{ visible.label=S._bootReady && select.selectedOptions[0] ? select.selectedOptions[0].textContent : ''; },
});
let releaseMetadata;
const metadata = new Promise(resolve=>releaseMetadata=resolve);
globalThis.loadSession = async () => {
  calls.metadata++; const generation=++_loadSessionGeneration;
  await metadata;
  if(generation!==_loadSessionGeneration) return;
  S.session={...savedSession,_modelResolutionDeferred:true}; visible.transcript='Saved conversation';
  syncTopbar();
};
const pendingModels = [];
globalThis.fetch = url => {
  if(!String(url).includes('/api/models')) { calls.mutation++; throw Error('Unexpected network write/read'); }
  calls.models++;
  return new Promise((resolve,reject)=>pendingModels.push({resolve,reject}));
};
for (const name of ['_getOptionProviderId','_providerFromModelValue','_modelStateForSelect',
  '_modelPickerOptionIdentity','_deduplicateModelPickerOptions','_modelProviderForSend',
  '_captureModelDropdownSelection','_findModelInDropdown','_refreshOpenModelDropdown',
  '_applyModelToDropdown','_ensureModelOptionInDropdown','_modelStateFromAppliedDropdown','_applySessionModelFallback',
  '_providerDefersMissingModelFallback','_reconcileModelDropdownSelection','populateModelDropdown']) {
  vm.runInThisContext(fn(ui, name));
}
for(const name of ['_chatPayloadModel','_chatPayloadModelProvider','_chatPayloadModelState']) vm.runInThisContext(fn(messages,name));
vm.runInThisContext(block(boot,"$('modelSelect').onchange=async()=>{","$('msg').addEventListener('input',()=>{"));
// Run the actual syncTopbar model reconciliation, including its initial fuzzy
// match against static HTML. Unrelated title/workspace DOM stays outside this fixture.
vm.runInThisContext('function syncTopbar(){'+block(ui,
  '  const modelOverride=S._pendingProfileModel;',
  '  if(typeof syncReasoningChip===\'function\') syncReasoningChip();')+'}');
vm.runInThisContext(fn(boot, '_finishBootAfterNewerSessionActivation'));
vm.runInThisContext(block(boot, '  const _bootActiveProfileUnauthRedirectBudget=(()=>{', '  // Fetch active profile'));
vm.runInThisContext(block(boot, '  const _redirectBootModelDropdownIfUnauth=(res)=>{', '  setTimeout(()=>{'));
const savedBranch=block(boot, '  const saved=urlSession||savedLocal;', '  // no saved session - show empty state');
const flush = async () => { for(let i=0;i<30;i++) await Promise.resolve(); };
function snapshot() { return {ready:S._bootReady, session:{...S.session}, selected:_modelStateForSelect(select,select.value), outgoing:_chatPayloadModelState(), value:select.value, visible:{...visible}, calls:{...calls}}; }
function response(provider='openai-codex') { return {status:200, json:async()=>({active_provider:provider, default_model:'gpt-6-astra',
  groups:[{provider:'Native',provider_id:'openai-codex',models:[{id:'gpt-6-astra',label:'Native Astra'}]},
          ...(scenario.omitCustom?[]:[{provider:'Gateway',provider_id:'custom:omniroute',models:[{id:scenario.catalogModel||'codex/gpt-6-astra',label:'Gateway Astra'}]}])]})}; }
(async()=>{
  _startBootModelDropdown().catch(()=>{});
  const restore=vm.runInThisContext('(async()=>{'+savedBranch+'})()');
  releaseMetadata(); await flush();
  const beforeCatalog=snapshot();
  if(scenario.navigate) {
    _loadSessionGeneration++;
    S.session={session_id:'newer', model:'another-model', model_provider:'custom:second', message_count:2};
    S.activeProfile=scenario.navigate;
  }
  if(scenario.pick){
    _ensureModelOptionInDropdown('chosen-model',select,'custom:chosen');
    await select.onchange();
  }
  if(scenario.failure) pendingModels[0].reject(Error('Catalog unavailable'));
  else pendingModels[0].resolve(response());
  await flush(); await restore; await flush();
  const afterCatalog=snapshot();
  process.stdout.write(JSON.stringify({beforeCatalog, afterCatalog}));
})().catch(err=>{console.error(err.stack);process.exitCode=1;});
