/* Subagent threads under the chat.
 *
 * Delegated workers run in the background and usually outlive the turn that
 * started them, so their progress cannot live only inside that turn's event
 * stream. This dock shows every worker of the open conversation as a card
 * (🤖 task, status, steps, duration), expandable to its own steps. It reads
 * GET /api/session/subagents, which the server keeps up to date even after the
 * parent stream has closed, and is nudged immediately by live `subagent` events.
 *
 * Cost: one cheap timer that only compares the open session id; network reads
 * happen on session change, after a live event, and every few seconds only
 * while a worker is still running. The dock re-renders only when its content
 * signature changes.
 */
(function(root){
  'use strict';
  const POLL_ACTIVE_MS=3000;
  const WATCH_MS=1500;
  const STALE_SECONDS=20*60;
  let currentSid='';
  let workers=[];
  let serverSkew=0;
  let lastSignature='';
  let pollTimer=null;
  let inflight=false;
  let open=new Set();
  let collapsed=false;
  let generation=0;

  const FT=()=>root.SynPulseFriendlyTools||null;
  function tx(key, vars){ const ft=FT(); return ft?ft.text(key,vars):key; }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function nowSec(){ return Date.now()/1000+serverSkew; }
  function dock(){ return root.document&&root.document.getElementById('spSubagentDock'); }
  function activeSid(){
    try{ const st=(typeof S!=='undefined')?S:root.S; return (st&&st.session&&st.session.session_id)||''; }catch(_){ return ''; }
  }

  function isLive(w){
    if(!w||w.restored) return false;
    if(w.status!=='running'&&w.status!=='queued') return false;
    const seen=Number(w.updated_at)||0;
    return !seen||nowSec()-seen<STALE_SECONDS;
  }
  function stateOf(w){
    if(w.status==='completed') return 'done';
    if(w.status==='failed') return 'failed';
    if(w.status==='cancelled') return 'stopped';
    if(!isLive(w)) return 'last_seen';
    return w.status==='queued'?'queued':'running';
  }
  function durationOf(w){
    if(typeof w.duration_seconds==='number') return w.duration_seconds;
    const start=Number(w.started_at)||0;
    if(!start) return null;
    const end=isLive(w)?nowSec():(Number(w.updated_at)||start);
    return Math.max(0,end-start);
  }

  function stepHtml(step){
    const ft=FT();
    const info=ft?ft.describe({name:step.tool,args:{},done:true}):{emoji:'🔧',title:step.tool,target:''};
    const t=Number(step.at)||0;
    const time=t?new Date((t-serverSkew)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';
    return `<li class="sp-subagent-step"><span class="sp-subagent-step-emoji" aria-hidden="true">${info.emoji}</span><span class="sp-subagent-step-title">${esc(info.title)}</span>${info.target?`<span class="sp-subagent-step-target">${esc(info.target)}</span>`:''}<span class="sp-subagent-step-tool" title="${esc(step.tool)}">${esc(step.tool)}</span>${time?`<time class="sp-subagent-step-time">${esc(time)}</time>`:''}</li>`;
  }

  function cardHtml(w){
    const ft=FT();
    const st=stateOf(w);
    const dur=durationOf(w);
    const chip=ft?ft.statusChipHtml({state:st,duration:dur}):'';
    const idx=Number(w.task_index)||0, cnt=Number(w.task_count)||0;
    const who=cnt>1?`${tx('subagent')} ${idx+1}/${cnt}`:tx('subagent');
    const n=Number(w.tool_count)||0;
    const stepsLabel=n===1?tx('tools_one'):tx('tools_many',{n});
    const steps=Array.isArray(w.steps)?w.steps:[];
    const isOpen=open.has(w.id);
    const hidden=Math.max(0,n-steps.length);
    const body=steps.length
      ?`<ol class="sp-subagent-steps">${steps.map(stepHtml).join('')}</ol>${hidden&&w.steps_truncated?`<div class="sp-subagent-note">${esc(tx('step_more',{n:hidden}))}</div>`:''}`
      :`<div class="sp-subagent-note">${esc(n?stepsLabel:tx('subagents_empty'))}</div>`;
    const openLink=w.child_session_id
      ?`<button type="button" class="sp-subagent-open" data-sp-subagent-open="${esc(w.child_session_id)}">💬 ${esc(tx('open_thread'))} <span aria-hidden="true">↗</span></button>`
      :'';
    return `<article class="sp-subagent-card" data-state="${esc(st)}" data-worker-id="${esc(w.id)}">
      <button type="button" class="sp-subagent-head" aria-expanded="${isOpen?'true':'false'}" data-sp-subagent-toggle="${esc(w.id)}">
        <span class="sp-subagent-avatar" aria-hidden="true">🤖</span>
        <span class="sp-subagent-main"><span class="sp-subagent-who">${esc(who)}</span><span class="sp-subagent-task">${esc(w.task||'')}</span></span>
        <span class="sp-subagent-meta"><span class="sp-subagent-count" title="${esc(stepsLabel)}">🔧 ${n}</span>${chip}</span>
        <span class="sp-subagent-caret" aria-hidden="true">›</span>
      </button>
      <div class="sp-subagent-body"${isOpen?'':' hidden'}>${body}${openLink}</div>
    </article>`;
  }

  function render(){
    const el=dock();
    if(!el) return;
    if(!workers.length||!currentSid){
      if(!el.hidden){ el.hidden=true; el.innerHTML=''; }
      lastSignature='';
      return;
    }
    const states=workers.map(stateOf);
    const live=states.filter(s=>s==='running'||s==='queued').length;
    const done=states.filter(s=>s==='done').length;
    const failed=states.filter(s=>s==='failed').length;
    const tick=live?Math.floor(nowSec()/5):0; // refresh running durations every 5 s
    const signature=JSON.stringify([currentSid,collapsed,[...open],tick,workers.map(w=>[w.id,w.status,w.tool_count,(w.steps||[]).length,w.duration_seconds,w.task,w.child_session_id||''])]);
    if(signature===lastSignature) return;
    lastSignature=signature;
    const parts=[];
    if(live) parts.push(`<span class="sp-chip sp-chip-running"><span class="sp-spin" aria-hidden="true"></span>${live} ${esc(tx('running').toLowerCase())}</span>`);
    if(done) parts.push(`<span class="sp-chip sp-chip-done">✅ ${done} ${esc(tx('done').toLowerCase())}</span>`);
    if(failed) parts.push(`<span class="sp-chip sp-chip-failed">⚠️ ${failed} ${esc(tx('failed').toLowerCase())}</span>`);
    const ordered=workers.slice().reverse(); // newest first
    el.hidden=false;
    el.innerHTML=`<div class="sp-subagent-dock-inner">
      <button type="button" class="sp-subagent-dock-head" aria-expanded="${collapsed?'false':'true'}" data-sp-subagent-dock-toggle="1">
        <span aria-hidden="true">🤖</span><span class="sp-subagent-dock-title">${esc(tx('subagents_title'))} (${workers.length})</span>
        <span class="sp-subagent-dock-chips">${parts.join('')}</span><span class="sp-subagent-caret" aria-hidden="true">›</span>
      </button>
      <div class="sp-subagent-list"${collapsed?' hidden':''}>${ordered.map(cardHtml).join('')}</div>
    </div>`;
  }

  // Open the worker's own conversation (state.db child session, view-only) the
  // same way the sidebar opens nested subagent chats, so the same server-side
  // visibility checks apply.
  async function openThread(childSid){
    if(!childSid) return;
    let row=null;
    try{ if(typeof _allSessions!=='undefined'&&Array.isArray(_allSessions)) row=_allSessions.find(s=>s&&s.session_id===childSid)||null; }catch(_){}
    const session=row||{session_id:childSid,source_tag:'subagent',raw_source:'subagent',parent_session_id:currentSid,relationship_type:'child_session'};
    try{
      if(typeof _openSidebarSession==='function') await _openSidebarSession(session,{skipLineageResolve:true});
      else if(typeof loadSession==='function') await loadSession(childSid);
    }catch(_){
      if(typeof root.showToast==='function') root.showToast(lang()==='nl'?'Dit gesprek kon niet worden geopend.':'This conversation could not be opened.',3000,'error');
    }
  }
  function lang(){ const ft=FT(); return ft&&ft.lang?ft.lang():'en'; }

  function onClick(ev){
    const o=ev.target&&ev.target.closest?ev.target.closest('[data-sp-subagent-open]'):null;
    if(o){ ev.preventDefault(); openThread(o.getAttribute('data-sp-subagent-open')); return; }
    const t=ev.target&&ev.target.closest?ev.target.closest('[data-sp-subagent-toggle],[data-sp-subagent-dock-toggle]'):null;
    if(!t) return;
    const id=t.getAttribute('data-sp-subagent-toggle');
    if(id){ if(open.has(id)) open.delete(id); else open.add(id); }
    else collapsed=!collapsed;
    lastSignature='';
    render();
  }

  function schedule(){
    if(pollTimer){ clearTimeout(pollTimer); pollTimer=null; }
    if(!currentSid||!workers.some(isLive)) return;
    pollTimer=setTimeout(()=>{ pollTimer=null; refresh(); }, POLL_ACTIVE_MS);
  }

  async function refresh(){
    const sid=currentSid;
    if(!sid||inflight) return;
    if(root.document&&root.document.hidden){ schedule(); return; }
    inflight=true;
    const gen=generation;
    try{
      const fetcher=typeof root.api==='function'?root.api:null;
      const path='/api/session/subagents?session_id='+encodeURIComponent(sid);
      const data=fetcher
        ?await fetcher(path,{timeoutMs:8000,timeoutToast:false,retries:0,redirect401:false})
        :await (await fetch(path.slice(1),{cache:'no-store'})).json();
      if(gen!==generation||sid!==currentSid) return;
      if(data&&typeof data.server_time==='number') serverSkew=data.server_time-Date.now()/1000;
      workers=Array.isArray(data&&data.subagents)?data.subagents:[];
      render();
    }catch(_){
      // Display-only: keep the last known cards.
    }finally{
      inflight=false;
      if(gen===generation) schedule();
    }
  }

  function switchTo(sid){
    if(sid===currentSid) return;
    generation++;
    currentSid=sid;
    workers=[];
    open=new Set();
    lastSignature='';
    render();
    if(sid) refresh();
  }

  // Live `subagent` SSE event for the open conversation: merge it right away so
  // the card moves without waiting for the next poll, then confirm from the server.
  function noteLive(sid, data){
    if(!sid||sid!==currentSid||!data||typeof data!=='object') return;
    const id=String(data.id||'');
    if(!id) return;
    const rank={queued:0,running:1,completed:2,failed:2,cancelled:2};
    if(!Object.prototype.hasOwnProperty.call(rank,data.status)) return;
    let w=workers.find(x=>x.id===id);
    if(!w){ w={id,started_at:nowSec(),steps:[]}; workers.push(w); }
    else if(rank[w.status]===2||rank[w.status]>rank[data.status]) return;
    w.status=data.status;
    if(data.summary) w.task=String(data.summary).slice(0,120);
    for(const k of ['task_index','task_count']) if(Number.isInteger(data[k])) w[k]=data[k];
    if(Number.isInteger(data.tool_count)) w.tool_count=Math.max(w.tool_count||0,data.tool_count);
    if(typeof data.duration_seconds==='number') w.duration_seconds=data.duration_seconds;
    if(typeof data.child_session_id==='string'&&/^[A-Za-z0-9_.:-]{1,128}$/.test(data.child_session_id)) w.child_session_id=data.child_session_id;
    w.updated_at=nowSec();
    delete w.restored;
    render();
    if(!pollTimer&&!inflight) pollTimer=setTimeout(()=>{ pollTimer=null; refresh(); }, 800);
  }

  function start(){
    const el=dock();
    if(el&&!el._spBound){ el.addEventListener('click',onClick); el._spBound=true; }
    setInterval(()=>{
      const sid=activeSid();
      if(sid!==currentSid) switchTo(sid);
      else if(workers.some(isLive)) render(); // keeps running durations fresh
    }, WATCH_MS);
    switchTo(activeSid());
  }

  const api={noteLive,refresh:()=>refresh(),_state:()=>({currentSid,workers,open:[...open]}),_render:render,_switchTo:switchTo};
  root.SynPulseSubagentThreads=api;
  if(typeof module!=='undefined'&&module.exports){ module.exports=api; return; }
  if(root.document){
    if(root.document.readyState==='loading') root.document.addEventListener('DOMContentLoaded',start);
    else start();
  }
})(typeof window!=='undefined'?window:globalThis);
