// Execute the production boot tail and workspace loader with controlled HTTP results.
const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const scenario=JSON.parse(process.argv[3]||'{}');
const boot=fs.readFileSync(path.join(root,'static/boot.js'),'utf8');
const panels=fs.readFileSync(path.join(root,'static/panels.js'),'utf8');
const sessions=fs.readFileSync(path.join(root,'static/sessions.js'),'utf8');
const terminal=fs.readFileSync(path.join(root,'static/terminal.js'),'utf8');
const commands=fs.readFileSync(path.join(root,'static/commands.js'),'utf8');
function block(source,start,end){const from=source.indexOf(start);if(from<0)throw Error(start);const to=source.indexOf(end,from);if(to<0)throw Error(end);return source.slice(from,to);}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
const requests=[],switches=[],onboarding=deferred(),session=deferred(),xterm=deferred();
const values=new Map(scenario.local?[['hermes-webui-session','saved']]:[]);
const state={workspaceApplies:0,backend:'',loads:[],newSessions:0,binds:[],draft:'typed draft',ready:0};
const toggle={disabled:false,title:'',classList:{toggle(){}},setAttribute(){}};
const elements={emptyState:{style:{}},sessionSearch:{value:'old search'},msg:{value:'typed draft'}};
Object.assign(globalThis,{window:globalThis,S:{activeProfile:'alpha',session:null,messages:[],busy:false,_bootReady:false},
 document:{getElementById:id=>elements[id]},$:id=>elements[id],
 localStorage:{getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)},
 _workspaceList:[],_workspaceViewerIsAdmin:false,_workspaceListRequestGeneration:0,_profileSwitchGeneration:0,
 _loadSessionGeneration:0,_bootRestoreGeneration:0,_bootDraftInputGeneration:4,
 _composerDraftInputGeneration:4,_loadingSessionId:null,
 _composerDraftHasPayload:(text,files)=>!!(text||files.length),_isComposerDraftRestoreSuppressed:()=>false,
 _clearComposerDraftRestoreSuppression:()=>{},_saveComposerDraftNow:()=>{},autoResize:()=>{},updateSendBtn:()=>{},
 _bootSettings:{onboarding_completed:scenario.onboarding?false:true},prefillIntent:scenario.prefill?{}:null,
 profileIntent:null,_profileSwitchCompleted:false,_profileSwitchChangedProfile:false,
 _newSessionInFlight:null,_workspacePanelMode:'closed',
 api:(url,opts)=>{const req=deferred();if(url==='/api/profile/switch'){switches.push({req,name:JSON.parse(opts.body).name});return req.promise;}if(url==='/api/terminal/start'){state.posts=(state.posts||0)+1;return Promise.resolve({});}if(url!=='/api/workspaces')throw Error('Unexpected API '+url);requests.push(req);return req.promise;},

 syncWorkspaceDisplays:()=>{state.workspaceApplies++;},
 TERMINAL_UI:{open:false,collapsed:false},_terminalEls:()=>({toggle}),_terminalSessionId:()=>S.session&&S.session.session_id,
 t:key=>key,showToast:text=>{state.toast=text;},_loadXterm:()=>{state.terminalStarts=(state.terminalStarts||0)+1;return scenario.terminalDelay?xterm.promise:Promise.resolve();},_ensureXterm:()=>scenario.terminalDelay?{}:null,
 _fitTerminal:()=>{},_terminalDimensions:()=>({rows:24,cols:80}),_connectTerminalOutput:()=>{},_resizeComposerTerminal:()=>{},
 toggleComposerTerminal:async()=>{state.toggles=(state.toggles||0)+1;},
 _clearSessionSceneCache:()=>{},_skillsData:null,_sessionListSkeletonActive:false,
 _profileSwitchOpeningExistingSession:true,closeProfileDropdown:()=>{},_profileSwitchPanelLoad:async()=>{},
 _refreshProfileSwitchBackground:()=>{loadWorkspaceList();},
 loadOnboardingWizard:()=>onboarding.promise,
 renderSessionList:async()=>{},_initResizePanels:()=>{},syncTopbar:()=>{},syncWorkspacePanelState:()=>{},
 dispatchEvent:event=>{if(event.type==='synpulse:boot-ready')state.ready++;},
 _sessionIdFromLocation:()=>scenario.fresh||scenario.local?null:'saved',
 _shouldStartFreshPwaChat:()=>!!scenario.pwa,
 _profileQueryBlocksSavedLocalRestore:()=>false,_savedSessionSidebarOnlyState:async()=>scenario.sidebarOnly?{sidebarOnly:true,archived:!!scenario.archived}:null,
 _rootPrefillNeedsFreshComposer:()=>!!scenario.prefill,_isRestoredPersonalScratchSession:()=>!!scenario.scratch,
 _isCompactWorkspaceViewport:()=>false,_primeRestoredSessionModelForBoot:()=>true,
 _startBootModelDropdown:async()=>{},_finalizeComposerPrefillOnBoot:async()=>{},checkInflightOnBoot:async()=>{},
 _maybeBindFreshDefaultWorkspaceSession:async()=>{state.binds.push(_workspaceList.map(x=>x.path));},
 newSession:async()=>{state.newSessions++;S.session={session_id:'new',workspace:''};},
 loadSession:async(sid,opts)=>{state.loads.push({sid,opts});const gen=++_loadSessionGeneration;const response=await session.promise;
   if(gen!==_loadSessionGeneration)return;
   if(response.status!==200)throw Error('Session access denied');
   S.session={session_id:sid,model:'codex/gpt-6-astra',model_provider:'custom:omniroute',message_count:scenario.scratch?0:2,workspace:'saved-root'};
   S.messages=['Authorized saved history'];
   _restoreComposerDraft({text:'Older server draft',files:[]},sid,{preserveActiveInput:opts.preserveActiveInput,inputGeneration:opts.draftInputGeneration});
 },
});
vm.runInThisContext(block(sessions,'function _restoreComposerDraft(','// Clear the saved draft'));
if(panels.includes('function _resetWorkspaceListState('))vm.runInThisContext(block(panels,'function _resetWorkspaceListState(','async function loadWorkspaceList(){'));
vm.runInThisContext(block(terminal,'function syncTerminalBackendState(','function focusComposerTerminalInput'));
vm.runInThisContext(block(terminal,'async function _startComposerTerminal(','async function toggleComposerTerminal'));
vm.runInThisContext(block(commands,'async function cmdTerminal(){','async function cmdNew(){'));
vm.runInThisContext(block(sessions,'async function _switchProfileForSessionLoad(','async function loadSession('));
vm.runInThisContext(block(panels,'async function switchToProfile(name)','function openProfileCreate'));
vm.runInThisContext(block(panels,'async function loadWorkspaceList(){','function _setWorkspaceDropdownOpenState'));
vm.runInThisContext(block(boot,'  async function _finishBootAfterNewerSessionActivation(){','  if(window.i18nReady)'));
const tail=block(boot,'  // Start independent boot fetches','})().catch(e=>{');
const flush=async()=>{for(let n=0;n<50;n++)await Promise.resolve();};
const snapshot=()=>({ready:S._bootReady,sid:S.session&&S.session.session_id,messages:[...S.messages],profile:S.activeProfile,
  workspaces:_workspaceList,backend:S.terminalRemoteBackend,backendKnown:S.terminalBackendKnown,admin:_workspaceViewerIsAdmin,terminalDisabled:toggle.disabled,defaultWorkspace:S._profileDefaultWorkspace,switchWorkspace:S._profileSwitchWorkspace,draft:elements.msg.value,calls:JSON.parse(JSON.stringify(state))});
const payload=id=>({workspaces:[{path:id}],last:id,terminal_remote_backend:id==='older',viewer_is_admin:id==='older'});
(async()=>{
 if(scenario.switchControlRace){
   const control=()=>{const classes=new Set();return {disabled:false,classList:{add:name=>classes.add(name),remove:name=>classes.delete(name),contains:name=>classes.has(name)}};};
   elements.profileChip=control();elements.titlebarProfileBtn=control();
   elements.profileChipLabel={textContent:'alpha'};elements.titlebarProfileLabel={textContent:'alpha'};
   globalThis.syncTopbar=()=>{elements.profileChipLabel.textContent=S.activeProfile;elements.titlebarProfileLabel.textContent=S.activeProfile;};
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};S.messages=['Authorized origin'];
   const old=switchToProfile('beta');await flush();
   if(scenario.autoFailure==='setup')globalThis.showSessionListSkeleton=()=>{throw Error('Skeleton unavailable');};
   const current=_switchProfileForSessionLoad('gamma');await flush();
   if(scenario.autoFailure==='setup'){}
   else if(scenario.autoFailure)switches[1].req.reject(Error('Newer switch denied'));
   else switches[1].req.resolve({active:'gamma',default_workspace:'gamma-root'});
   try{await current;}catch(_){};
   switches[0].req.resolve({active:'beta',default_workspace:'stale-root'});await old;
   const controls=Object.fromEntries(['profileChip','titlebarProfileBtn'].map(id=>[id,{disabled:elements[id].disabled,switching:elements[id].classList.contains('switching')}]));
   process.stdout.write(JSON.stringify({controls,label:elements.profileChipLabel.textContent,after:snapshot()}));return;
 }
 if(scenario.switchRenderRace){
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};S.messages=['Authorized origin'];
   const render=deferred();let firstRender=true;
   globalThis.renderSessionList=()=>{if(firstRender){firstRender=false;return render.promise;}return Promise.resolve();};
   const old=_switchProfileForSessionLoad('beta');await flush();
   switches[0].req.resolve({active:'beta',default_workspace:'beta-root'});await flush();
   const newer=switchToProfile(scenario.roundTrip?'alpha':'gamma');await flush();
   switches[1].req.resolve({active:scenario.roundTrip?'alpha':'gamma',default_workspace:'current-root'});await newer;
   render.resolve();const oldResult=await old;
   process.stdout.write(JSON.stringify({oldResult,after:snapshot()}));return;
 }
 if(scenario.switchRace){
   const classes=new Set();elements.profileChip={disabled:false,classList:{add:name=>classes.add(name),remove:name=>classes.delete(name)}};
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};S.messages=['Authorized origin'];
   const old=_switchProfileForSessionLoad('beta');await flush();
   const newer=switchToProfile('gamma');await flush();
   if(!scenario.newerPending){switches[1].req.resolve({active:'gamma',default_workspace:'gamma-root'});await newer;await flush();}
   if(scenario.oldFailure)switches[0].req.reject(Error('Old switch denied'));
   else switches[0].req.resolve({active:'beta',default_workspace:'private-beta'});
   const oldResult=await old;
   const beforeNewer={disabled:elements.profileChip.disabled,switching:classes.has('switching')};
   if(scenario.newerPending){switches[1].req.resolve({active:'gamma',default_workspace:'gamma-root'});await newer;}
   process.stdout.write(JSON.stringify({oldResult,beforeNewer,after:snapshot()}));return;
 }
 if(scenario.command){
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};
   S.terminalRemoteBackend=false;S.terminalBackendKnown=true;
   const call=cmdTerminal();await flush();
   if(scenario.profileChange){S.activeProfile='beta';_profileSwitchGeneration++;_resetWorkspaceListState({});}
   if(scenario.sessionChange)S.session={session_id:'different',workspace:'new'};
   if(scenario.workspaceFailure)requests[0].reject(Error('403'));
   else requests[0].resolve(payload(scenario.remote?'older':'current'));
   await call;await flush();process.stdout.write(JSON.stringify(snapshot()));return;
 }
 if(scenario.terminalDelay){
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};S.terminalBackendKnown=true;S.terminalRemoteBackend=false;
   const start=_startComposerTerminal();await flush();
   if(scenario.profileChange){S.activeProfile='beta';_profileSwitchGeneration++;}
   if(scenario.roundTrip){S.activeProfile='alpha';_profileSwitchGeneration++;}
   if(scenario.sessionChange)S.session={session_id:'different',workspace:'new'};
   if(scenario.workspaceFailure)S.terminalBackendKnown=false;
   xterm.resolve();await start;process.stdout.write(JSON.stringify(snapshot()));return;
 }
 if(scenario.switchPath){
   S.session={session_id:'origin',profile:'alpha',workspace:'authorized-origin'};
   S.messages=['Authorized origin'];
   S._profileDefaultWorkspace='alpha-default';S._profileSwitchWorkspace='alpha-default';
   _workspaceList=[{path:'alpha-private'}];_workspaceViewerIsAdmin=true;
   S.terminalRemoteBackend=false;S.terminalBackendKnown=true;
   const stale=loadWorkspaceList();
   // A prior successful snapshot may exist when profile POST begins.
   _workspaceList=[{path:'alpha-private'}];_workspaceViewerIsAdmin=true;S.terminalBackendKnown=true;
   const switchFn=scenario.switchPath==='automatic'?_switchProfileForSessionLoad:switchToProfile;
   const change=switchFn('beta');await flush();
   if(scenario.failedSwitch){switches[0].req.reject(Error('Switch denied'));try{await change;}catch(_){};const failed=snapshot();requests[0].resolve(payload('older'));await stale;process.stdout.write(JSON.stringify({failed}));return;}
   switches[0].req.resolve({active:'beta',default_workspace:scenario.newDefault?'beta-default':''});await change;await flush();
   await _startComposerTerminal();const pending=snapshot();
   if(scenario.roundTrip){const back=switchFn('alpha');await flush();switches[1].req.resolve({active:'alpha',default_workspace:''});await back;await flush();}
   requests[0].resolve(payload('older'));await stale;
   const afterStale=snapshot();
   const latest=requests.at(-1);
   if(scenario.workspaceFailure)latest.reject(Object.assign(Error('Workspace denied'),{status:scenario.workspaceFailure==='forbidden'?403:503}));
   else latest.resolve(payload('current'));
   await flush();await _startComposerTerminal();
   process.stdout.write(JSON.stringify({pending,afterStale,after:snapshot()}));return;
 }
 if(scenario.loaderOnly){
   const first=loadWorkspaceList();
   if(scenario.profileSwitch){S.activeProfile='beta';_profileSwitchGeneration++;}
   if(scenario.roundTrip){S.activeProfile='alpha';_profileSwitchGeneration++;}
   const second=scenario.second?loadWorkspaceList():null;
   if(second){requests[1].resolve(payload('newer'));await second;}
   const malformed={null:null,empty:{},array:{...payload('older'),workspaces:{}},backend:{...payload('older'),terminal_remote_backend:'false'},admin:{...payload('older'),viewer_is_admin:'false'}};
   requests[0].resolve(scenario.malformed?malformed[scenario.malformed]:payload('older'));await first;
   if(scenario.recover){const retry=loadWorkspaceList();requests.at(-1).resolve(payload('current'));await retry;}
   process.stdout.write(JSON.stringify(snapshot()));return;
 }
 const pending=vm.runInThisContext('(async()=>{'+tail+'})()');
 if(!scenario.editDuringLoad)session.resolve({status:scenario.denied?403:200});await flush();
 const before=snapshot();
 if(scenario.editDuringLoad){elements.msg.value=scenario.editDuringLoad==='clear'?'':'New text while restoring';_composerDraftInputGeneration++;session.resolve({status:200});await flush();}
 const afterSession=snapshot();
 if(scenario.navigate){_loadSessionGeneration++;S.session={session_id:'newer',message_count:0};S.messages=[];elements.msg.value='newer typed draft';}
 if(scenario.newPending){const next=deferred();_loadSessionGeneration++;_newSessionInFlight=next.promise;S.session={session_id:'newer'};next.resolve();}
 if(scenario.onboarding){onboarding.resolve(false);await flush();}
 const afterOnboarding=snapshot();
 if(scenario.failedWorkspace)requests[0].reject(Error('Temporary workspace failure'));
 else requests[0].resolve(payload('available-root'));
 await pending;await flush();
 process.stdout.write(JSON.stringify({before,afterSession,afterOnboarding,after:snapshot()}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
