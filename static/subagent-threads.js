/* Teamwerk: helpers and bots working for the open conversation.
 *
 * Delegated workers run in the background and usually outlive the turn that
 * started them, so their progress cannot live only inside that turn's event
 * stream. This dock shows every worker of the open conversation as a card
 * (bot photo, task, plain status, steps, duration), expandable to its own
 * steps. Handoffs to a bot in this same chat are listed too. It reads
 * GET /api/session/subagents, which the server keeps up to date even after the
 * parent stream has closed, and is nudged immediately by live `subagent` events.
 *
 * Cost: one cheap timer that only compares the open session id; network reads
 * happen on session change, after a live event, and every few seconds only
 * while a worker is still running. The dock re-renders only when its content
 * signature changes.
 *
 * decorate(container) also adds the handoff line ("Sanne heeft Linus
 * gevraagd") to settled turns, whose work steps are folded away.
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
  let lastRefresh=0;
  let open=new Set();
  let collapsed=false;
  let userToggled=false;
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
    if(w.queue_authoritative) return true;
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

  // A bot's own photo when the catalog knows it; otherwise its initial.
  function avatarHtml(w, who){
    const bots=FT()&&FT().bots;
    if(bots&&w.bot_profile) return bots.avatarHtml(w.bot_profile,who,'sp-subagent-avatar');
    const initial=(String(who||'').trim().charAt(0)||'?').toUpperCase();
    return `<span class="sp-bot-avatar sp-subagent-avatar" aria-hidden="true"><span class="sp-bot-avatar-initial">${esc(initial)}</span></span>`;
  }
  function statusWord(w, st){
    if(st==='queued'){
      if(w.kind==='handoff'){
        const bots=FT()&&FT().bots;
        const lead=bots?bots.name(w.from_profile,w.from_title):(w.from_title||'');
        if(lead) return tx('team_status_queued_handoff',{from:lead});
      }
      return tx('team_status_queued');
    }
    const key={running:'team_status_running',done:'team_status_done',failed:'team_status_failed',stopped:'team_status_stopped',last_seen:'team_status_last_seen'}[st];
    return key?tx(key):'';
  }

  function cardHtml(w){
    const ft=FT();
    const st=stateOf(w);
    const dur=durationOf(w);
    const chip=ft?ft.statusChipHtml({state:st,duration:dur}):'';
    const idx=Number(w.task_index)||0, cnt=Number(w.task_count)||0;
    const bots=ft&&ft.bots;
    const who=w.bot_profile&&bots?bots.name(w.bot_profile,w.bot_title)
      :(w.bot_title||(cnt>1?`${tx('subagent')} ${idx+1}/${cnt}`:tx('subagent')));
    const n=Number(w.tool_count)||0;
    const stepsLabel=n===1?tx('tools_one'):tx('tools_many',{n});
    const steps=Array.isArray(w.steps)?w.steps:[];
    const isOpen=open.has(w.id);
    const hidden=Math.max(0,n-steps.length);
    const body=steps.length
      ?`<ol class="sp-subagent-steps">${steps.map(stepHtml).join('')}</ol>${hidden&&w.steps_truncated?`<div class="sp-subagent-note">${esc(tx('step_more',{n:hidden}))}</div>`:''}`
      :`<div class="sp-subagent-note">${esc(n?stepsLabel:tx('subagents_empty'))}</div>`;
    const openLabel=w.bot_profile?tx('open_work',{name:who}):tx('open_thread');
    const openLink=w.child_session_id
      ?`<button type="button" class="sp-subagent-open" data-sp-subagent-open="${esc(w.child_session_id)}" data-sp-subagent-profile="${esc(w.bot_profile||'')}">${esc(openLabel)} <span aria-hidden="true">↗</span></button>`
      :'';
    const word=statusWord(w,st);
    const tip=w.bot_profile?` title="${esc('@'+w.bot_profile)}"`:'';
    return `<article class="sp-subagent-card" data-state="${esc(st)}" data-kind="${esc(w.kind||'worker')}" data-worker-id="${esc(w.id)}">
      <button type="button" class="sp-subagent-head" aria-expanded="${isOpen?'true':'false'}" data-sp-subagent-toggle="${esc(w.id)}"${tip}>
        ${avatarHtml(w,who)}
        <span class="sp-subagent-main"><span class="sp-subagent-who">${esc(who)}</span><span class="sp-subagent-task">${esc(w.task||'')}</span></span>
        <span class="sp-subagent-meta">${word?`<span class="sp-subagent-status">${esc(word)}</span>`:''}${chip}</span>
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
    const working=states.filter(s=>s==='running').length;
    const waiting=live-working;
    const done=states.filter(s=>s==='done').length;
    const failed=states.filter(s=>s==='failed').length;
    // Folded by default once everything has finished, unless the reader chose.
    const folded=userToggled?collapsed:!live;
    const tick=live?Math.floor(nowSec()/5):0; // refresh running durations every 5 s
    const signature=JSON.stringify([currentSid,folded,[...open],tick,workers.map(w=>[w.id,w.status,w.kind||'',w.tool_count,(w.steps||[]).length,w.duration_seconds,w.task,w.child_session_id||'',w.bot_title||'',w.bot_profile||'',w.from_profile||''])]);
    if(signature===lastSignature) return;
    lastSignature=signature;
    const parts=[];
    if(working) parts.push(`<span class="sp-chip sp-chip-running"><span class="sp-spin" aria-hidden="true"></span>${esc(tx('team_count_running',{n:working}))}</span>`);
    if(waiting) parts.push(`<span class="sp-chip sp-chip-queued">${esc(tx('team_count_queued',{n:waiting}))}</span>`);
    if(done) parts.push(`<span class="sp-chip sp-chip-done">${esc(tx('team_count_done',{n:done}))}</span>`);
    if(failed) parts.push(`<span class="sp-chip sp-chip-failed">${esc(tx('team_count_failed',{n:failed}))}</span>`);
    const ordered=workers.slice().reverse(); // newest first
    el.hidden=false;
    el.innerHTML=`<div class="sp-subagent-dock-inner">
      <button type="button" class="sp-subagent-dock-head" aria-expanded="${folded?'false':'true'}" data-sp-subagent-dock-toggle="1">
        <span class="sp-subagent-dock-title">${esc(tx('subagents_title'))} (${workers.length})</span>
        <span class="sp-subagent-dock-chips">${parts.join('<span class="sp-chip-sep" aria-hidden="true">·</span>')}</span><span class="sp-subagent-caret" aria-hidden="true">›</span>
      </button>
      <div class="sp-subagent-list"${folded?' hidden':''}>${ordered.map(cardHtml).join('')}</div>
    </div>`;
  }

  // Open the worker's own conversation (state.db child session, view-only) the
  // same way the sidebar opens nested subagent chats, so the same server-side
  // visibility checks apply.
  async function openThread(childSid,profile){
    if(!childSid) return;
    let row=null;
    try{ if(typeof _allSessions!=='undefined'&&Array.isArray(_allSessions)) row=_allSessions.find(s=>s&&s.session_id===childSid)||null; }catch(_){}
    const session=row||{session_id:childSid,...(profile?{profile}:{}),source_tag:'subagent',raw_source:'subagent',parent_session_id:currentSid,relationship_type:'child_session'};
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
    if(o){ ev.preventDefault(); openThread(o.getAttribute('data-sp-subagent-open'),o.getAttribute('data-sp-subagent-profile')); return; }
    const t=ev.target&&ev.target.closest?ev.target.closest('[data-sp-subagent-toggle],[data-sp-subagent-dock-toggle]'):null;
    if(!t) return;
    const id=t.getAttribute('data-sp-subagent-toggle');
    if(id){ if(open.has(id)) open.delete(id); else open.add(id); }
    else {
      const head=t.getAttribute('aria-expanded')==='true';
      collapsed=head; userToggled=true;
    }
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
    lastRefresh=Date.now();
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
    userToggled=false;
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

  // ── Handoff lines in settled turns ──
  // The work steps of a finished turn are folded away, so the moment a bot
  // asks another bot ("Sanne heeft Linus gevraagd") gets its own quiet line at
  // the end of that turn. Built only from the stored delegate_to_bot calls and
  // their results; idempotent, so repeated renders change nothing.
  function parseArgs(raw){
    if(raw&&typeof raw==='object') return raw;
    try{ const v=JSON.parse(String(raw||'')); return v&&typeof v==='object'?v:{}; }catch(_){ return {}; }
  }
  function resultText(value){
    if(typeof value==='string') return value;
    if(Array.isArray(value)) return value.map(p=>p&&(p.text||p.content)||'').join('');
    return value&&typeof value==='object'?JSON.stringify(value):'';
  }
  function turnHandoffs(messages, start){
    const calls=[], results=Object.create(null);
    for(let i=start;i<messages.length;i++){
      const m=messages[i];
      if(!m) continue;
      if(i>start&&m.role==='user') break;
      if(m.role==='tool'&&m.tool_call_id) results[m.tool_call_id]=resultText(m.content);
      if(m.role!=='assistant') continue;
      for(const c of (Array.isArray(m.tool_calls)?m.tool_calls:[])){
        const fn=c&&c.function||{};
        if((fn.name||c.name)==='delegate_to_bot') calls.push({id:String(c.id||''),args:parseArgs(fn.arguments!==undefined?fn.arguments:c.args),idx:i});
      }
      if(Array.isArray(m.content)){
        for(const part of m.content){
          if(part&&part.type==='tool_use'&&part.name==='delegate_to_bot') calls.push({id:String(part.id||''),args:parseArgs(part.input),idx:i});
          if(part&&part.type==='tool_result'&&part.tool_use_id) results[part.tool_use_id]=resultText(part.content);
        }
      }
    }
    return calls.map(c=>({name:'delegate_to_bot',args:c.args,assistant_msg_idx:c.idx,done:true,
      result:Object.prototype.hasOwnProperty.call(results,c.id)?results[c.id]:'',key:c.id||('i'+c.idx)}));
  }
  function decorate(container){
    const ft=FT();
    const bots=ft&&ft.bots;
    const doc=root.document;
    if(!bots||!doc) return;
    let st=null;
    try{ st=(typeof S!=='undefined')?S:root.S; }catch(_){ st=root.S; }
    const messages=st&&Array.isArray(st.messages)?st.messages:[];
    const scope=container&&container.querySelectorAll?container:doc.getElementById('msgInner');
    if(!scope||!messages.length) return;
    // Cheap exit for ordinary chats: no delegate_to_bot anywhere.
    if(!messages.some(m=>m&&m.role==='assistant'&&((Array.isArray(m.tool_calls)&&m.tool_calls.some(c=>c&&((c.function&&c.function.name)||c.name)==='delegate_to_bot'))
      ||(Array.isArray(m.content)&&m.content.some(p=>p&&p.type==='tool_use'&&p.name==='delegate_to_bot'))))){
      return;
    }
    for(const turn of scope.querySelectorAll('.assistant-turn')){
      if(turn.id==='liveAssistantTurn') continue;
      const start=Number(turn.dataset&&turn.dataset.recycleKey);
      const blocks=turn.querySelector('.assistant-turn-blocks');
      if(!Number.isInteger(start)||!blocks) continue;
      const wanted=turnHandoffs(messages,start).filter(tc=>{
        const h=bots.handoffInfo(tc);
        return h.kind!=='list';
      });
      const shown=new Set(Array.from(turn.querySelectorAll('.tool-card-row[data-tool-family="handoff"]'))
        .filter(row=>row.getClientRects().length>0)
        .map(row=>String(row.dataset.toolActionLabel||'')));
      const keep=new Set();
      for(const tc of wanted){
        const key=String(tc.key);
        const h=bots.handoffInfo(tc);
        if(shown.has(h.kind==='queued'&&h.task?h.sentence+': '+(FT().describe(tc).target||''):h.sentence)) continue;
        keep.add(key);
        const html=bots.handoffLineHtml(tc);
        let node=Array.from(blocks.querySelectorAll(':scope > .sp-handoff-line')).find(el=>el.dataset.handoffKey===key);
        if(node&&node._spHtml===html) continue;
        const wasOpen=!!(node&&node.open);
        const holder=doc.createElement('div');
        holder.innerHTML=html;
        const next=holder.firstElementChild;
        if(!next) continue;
        next.dataset.handoffKey=key;
        next._spHtml=html;
        if(wasOpen) next.open=true;
        if(node) node.replaceWith(next); else blocks.appendChild(next);
      }
      for(const el of blocks.querySelectorAll(':scope > .sp-handoff-line')){
        if(!keep.has(el.dataset.handoffKey)) el.remove();
      }
    }
  }

  // Turns are added, replaced and recycled as direct children of #msgInner
  // (the same signal static/chat-bots.js uses for its reply chips); decorate
  // once per frame after such a change, so ui.js needs no extra hook.
  let observed=null, decoratePending=false;
  function scheduleDecorate(){
    if(decoratePending) return;
    decoratePending=true;
    const run=()=>{ decoratePending=false; try{ decorate(null); }catch(_){} };
    if(typeof root.requestAnimationFrame==='function') root.requestAnimationFrame(run); else setTimeout(run,0);
  }
  function observe(){
    const inner=root.document&&root.document.getElementById('msgInner');
    if(!inner||inner===observed||typeof root.MutationObserver!=='function') return;
    observed=inner;
    new root.MutationObserver(scheduleDecorate).observe(inner,{childList:true});
    scheduleDecorate();
  }

  function start(){
    observe();
    root.document.addEventListener('click',event=>{
      const button=event.target?.closest?.('[data-sp-specialist-open]');
      if(!button)return;
      event.preventDefault();
      openThread(button.getAttribute('data-sp-specialist-open'),button.getAttribute('data-sp-specialist-profile'));
    });
    const el=dock();
    if(el&&!el._spBound){ el.addEventListener('click',onClick); el._spBound=true; }
    // Names arrive with the bot catalog. If a teamwork name was guessed before
    // it came in, repaint the conversation once (not while a reply streams);
    // otherwise only the lines and the dock.
    root.addEventListener('synpulse:bot-catalog',()=>{
      const bots=FT()&&FT().bots;
      let st=null;
      try{ st=(typeof S!=='undefined')?S:root.S; }catch(_){ st=root.S; }
      const guessed=!!(bots&&typeof bots.takePendingNames==='function'&&bots.takePendingNames());
      if(guessed&&!(st&&(st.activeStreamId||st.busy))&&typeof root.renderMessages==='function'){
        try{ root.renderMessages({preserveScroll:true}); }catch(_){}
      }else{
        try{ decorate(null); }catch(_){}
      }
      lastSignature=''; render();
    });
    setInterval(()=>{
      observe();
      const sid=activeSid();
      if(sid!==currentSid) switchTo(sid);
      else if(workers.some(isLive)) render(); // keeps running durations fresh
      // Discover queued bot jobs even when their parent stream has already ended.
      if(sid&&!inflight&&!pollTimer&&Date.now()-lastRefresh>15000) refresh();
    }, WATCH_MS);
    switchTo(activeSid());
  }

  const api={noteLive,decorate,refresh:()=>refresh(),_state:()=>({currentSid,workers,open:[...open]}),_render:render,_switchTo:switchTo,_turnHandoffs:turnHandoffs};
  root.SynPulseSubagentThreads=api;
  if(typeof module!=='undefined'&&module.exports){ module.exports=api; return; }
  if(root.document){
    if(root.document.readyState==='loading') root.document.addEventListener('DOMContentLoaded',start);
    else start();
  }
})(typeof window!=='undefined'?window:globalThis);
