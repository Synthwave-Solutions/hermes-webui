/* Plain-language tool rows for the chat worklog.
 *
 * Turns a raw tool call ({name,args,done,is_error,duration,...}) into an emoji,
 * a short human title and a short human target ("💻 Opdracht uitgevoerd · Tests
 * gedraaid"). Raw commands, arguments and output stay behind the row's Details
 * toggle; nothing here ever returns a full command line or file path.
 *
 * Pure functions, no DOM work, so it is cheap to call per row and testable in
 * Node (tests/test_tool_friendly_ui.cjs).
 */
(function(root){
  'use strict';

  // ── Language: same order as the SynthPulse feature guide (help-guide.js) ──
  let forced=null;
  function lang(){
    if(forced) return forced;
    // The app language (static/i18n.js `_localeCode`, a script-global) wins.
    try{ if(typeof _localeCode==='string'&&_localeCode) return _localeCode.toLowerCase().startsWith('nl')?'nl':'en'; }catch(_){}
    try{ const s=root.localStorage&&root.localStorage.getItem('sp-feature-guide-language'); if(s==='nl'||s==='en') return s; }catch(_){}
    try{ const n=root.navigator&&(root.navigator.language||''); return String(n).toLowerCase().startsWith('nl')?'nl':'en'; }catch(_){}
    return 'en';
  }

  const COPY={
    nl:{
      steps:'Werkstappen', running:'Bezig', done:'Klaar', failed:'Mislukt', stopped:'Gestopt', details:'Details',
      last_seen:'Laatst gezien: bezig', queued:'In de wachtrij', subagent:'Subagent', subagents:'Subagents',
      tools_one:'1 stap', tools_many:'{n} stappen', subagents_title:'Subagents', subagents_empty:'Nog geen activiteit',
      subagents_more:'Toon alle stappen', step_more:'{n} eerdere stappen niet bewaard',
      processed:'Verwerkt', processed_in:'Verwerkt in {d}', working:'Bezig', now:'nu', open_thread:'Bekijk het volledige gesprek',
      error_title:'Er ging iets mis', error_hint:'Probeer het opnieuw. Blijft dit gebeuren, geef het dan door aan support.',
    },
    en:{
      steps:'Work steps', running:'Running', done:'Done', failed:'Failed', stopped:'Stopped', details:'Details',
      last_seen:'Last seen: running', queued:'Queued', subagent:'Subagent', subagents:'Subagents',
      tools_one:'1 step', tools_many:'{n} steps', subagents_title:'Subagents', subagents_empty:'No activity yet',
      subagents_more:'Show all steps', step_more:'{n} earlier steps not kept',
      processed:'Processed', processed_in:'Processed in {d}', working:'Working', now:'now', open_thread:'Open the full conversation',
      error_title:'Something went wrong', error_hint:'Please try again. If it keeps happening, let support know.',
    },
  };
  function text(key, vars){
    const table=COPY[lang()]||COPY.en;
    let out=table[key]!=null?table[key]:(COPY.en[key]||key);
    if(vars) Object.keys(vars).forEach(k=>{ out=out.replace('{'+k+'}',String(vars[k])); });
    return out;
  }

  // ── Families: emoji plus title per state, in Dutch and English ──
  // [emoji, nl running, nl done, nl failed, en running, en done, en failed]
  const F={
    shell:     ['💻','Opdracht wordt uitgevoerd','Opdracht uitgevoerd','Opdracht mislukt','Running a command','Ran a command','Command failed'],
    read:      ['📄','Bestand lezen','Bestand gelezen','Bestand lezen mislukt','Reading a file','Read a file','Could not read a file'],
    write:     ['✏️','Bestand aanpassen','Bestand aangepast','Aanpassen mislukt','Editing a file','Edited a file','Edit failed'],
    search:    ['🔍','Zoeken in bestanden','Gezocht in bestanden','Zoeken mislukt','Searching files','Searched files','Search failed'],
    list:      ['🗂️','Map bekijken','Map bekeken','Map bekijken mislukt','Listing files','Listed files','Listing failed'],
    web:       ['🌐','Op het web zoeken','Op het web gezocht','Webzoektocht mislukt','Searching the web','Searched the web','Web search failed'],
    browser:   ['🧭','Browser bezig','Browser gebruikt','Browserstap mislukt','Using the browser','Used the browser','Browser step failed'],
    delegate:  ['🤝','Subagents starten','Subagent(s) gestart','Subagent starten mislukt','Starting subagents','Started subagent(s)','Could not start subagents'],
    subagent:  ['🤖','Subagent werkt','Subagent klaar','Subagent mislukt','Subagent working','Subagent finished','Subagent failed'],
    opencode:  ['🧑‍💻','OpenCode-klus loopt','OpenCode-klus','OpenCode-klus mislukt','OpenCode job running','OpenCode job','OpenCode job failed'],
    mail:      ['✉️','Mail bezig','Mail afgehandeld','Mailactie mislukt','Working on mail','Mail handled','Mail action failed'],
    calendar:  ['📅','Agenda bekijken','Agenda bekeken','Agendaactie mislukt','Checking the calendar','Checked the calendar','Calendar action failed'],
    drive:     ['📁','Documenten openen','Documenten bekeken','Documentactie mislukt','Opening documents','Checked documents','Document action failed'],
    notion:    ['📝','Notion bekijken','Notion bijgewerkt','Notion-actie mislukt','Working in Notion','Used Notion','Notion action failed'],
    crm:       ['📇','CRM bekijken','CRM bekeken','CRM-actie mislukt','Checking the CRM','Checked the CRM','CRM action failed'],
    memory:    ['🧠','Geheugen bijwerken','Geheugen bijgewerkt','Geheugen bijwerken mislukt','Updating memory','Updated memory','Memory update failed'],
    skill:     ['🧩','Skill laden','Skill gebruikt','Skill laden mislukt','Loading a skill','Used a skill','Skill failed'],
    process:   ['⏱️','Achtergrondproces','Achtergrondproces bekeken','Procesactie mislukt','Background process','Checked a background process','Process action failed'],
    code:      ['🐍','Code uitvoeren','Code uitgevoerd','Code mislukt','Running code','Ran code','Code failed'],
    todo:      ['✅','Takenlijst bijwerken','Takenlijst bijgewerkt','Takenlijst mislukt','Updating the to-do list','Updated the to-do list','To-do update failed'],
    image:     ['🖼️','Afbeelding verwerken','Afbeelding verwerkt','Afbeelding mislukt','Working on an image','Image done','Image failed'],
    vision:    ['👁️','Afbeelding bekijken','Afbeelding bekeken','Afbeelding bekijken mislukt','Looking at an image','Looked at an image','Image check failed'],
    schedule:  ['⏰','Planning bijwerken','Planning bijgewerkt','Planning mislukt','Updating a schedule','Updated a schedule','Schedule failed'],
    message:   ['💬','Bericht versturen','Bericht verstuurd','Bericht mislukt','Sending a message','Sent a message','Message failed'],
    clarify:   ['❓','Vraag aan jou','Vraag gesteld','Vraag mislukt','Asking you','Asked you','Question failed'],
    voice:     ['🔊','Spraak maken','Spraak gemaakt','Spraak mislukt','Making speech','Made speech','Speech failed'],
    tools:     ['🧰','Tools bekijken','Tools bekeken','Tools bekijken mislukt','Looking up tools','Looked up tools','Tool lookup failed'],
    unknown:   ['🔧','Tool bezig','Tool gebruikt','Tool mislukt','Running a tool','Used a tool','Tool failed'],
  };

  function norm(name){ return String(name||'').toLowerCase(); }
  function mcpParts(name){
    const raw=String(name||'');
    if(raw.startsWith('mcp__')){ const p=raw.split('__').filter(Boolean); return {server:p[1]||'',tool:p.slice(2).join('_')}; }
    if(raw.startsWith('mcp.')){ const p=raw.split('.').filter(Boolean); return {server:p[1]||'',tool:p.slice(2).join('_')}; }
    return null;
  }

  function family(tc){
    const raw=norm(tc&&tc.name);
    const mcp=mcpParts(tc&&tc.name);
    const n=mcp?norm(mcp.server+'_'+mcp.tool):raw;
    if(raw==='subagent_progress') return 'subagent';
    if(raw==='delegate_task') return 'delegate';
    if(raw.includes('opencode')) return 'opencode';
    if(/gmail|(^|_)mail|email|outlook|inbox/.test(n)) return 'mail';
    if(/calendar|agenda|meet(ing)?s?\b/.test(n)) return 'calendar';
    if(/drive|docs|sheets|slides|onedrive|sharepoint|dropbox/.test(n)) return 'drive';
    if(/notion|obsidian/.test(n)) return 'notion';
    if(/attio|hubspot|crm|lemlist|productive|apollo/.test(n)) return 'crm';
    if(raw.startsWith('browser')||/(^|_)browser|playwright|chrome/.test(n)) return 'browser';
    if(raw==='execute_code'||/python|execute_code|run_code/.test(raw)) return 'code';
    if(raw==='process'||raw.startsWith('process_')) return 'process';
    if(raw==='todo'||raw.startsWith('todo')) return 'todo';
    if(raw.includes('memory')||/mnemo|memory/.test(n)) return 'memory';
    if(raw.includes('skill')) return 'skill';
    if(raw==='vision_analyze'||raw.includes('vision')) return 'vision';
    if(/image|photo|picture|gpt_image|krea/.test(n)) return 'image';
    if(raw==='cronjob'||raw.includes('cron')||raw.includes('schedule')) return 'schedule';
    if(raw==='send_message'||/whatsapp|chat_send|send_message|slack/.test(n)) return 'message';
    if(raw==='clarify') return 'clarify';
    if(raw==='text_to_speech'||raw.includes('tts')) return 'voice';
    if(raw==='tool_describe'||raw==='tool_call'||raw==='tool_search') return 'tools';
    if(raw==='terminal'||raw.includes('shell')||raw.includes('terminal')||raw==='bash') return 'shell';
    if(raw==='read_file'||raw==='view_file'||raw==='file_read') return 'read';
    if(raw==='write_file'||raw==='patch'||raw==='edit_file'||raw.includes('write')||raw.includes('patch')||raw.includes('edit')) return 'write';
    if(raw==='search_files'||raw.includes('grep')||raw==='find_files') return 'search';
    if(raw==='list_files'||raw==='list_directory'||raw==='ls') return 'list';
    if(/web_search|web_extract|fetch|search_web|websearch|scrape|crawl|firecrawl/.test(n)||raw.startsWith('web')) return 'web';
    if(raw.includes('search')) return 'search';
    if(raw.includes('read')||raw.includes('view')) return 'read';
    return 'unknown';
  }

  // ── Targets: short, human, never a full command or path ──
  function clip(value, max){
    const s=String(value||'').replace(/\s+/g,' ').trim();
    const m=max||64;
    return s.length>m?s.slice(0,m-1).trimEnd()+'…':s;
  }
  function basename(value){
    const s=String(value||'').trim().replace(/[\\/]+$/,'');
    if(!s) return '';
    return s.split(/[\\/]+/).pop()||s;
  }
  function host(value){
    const s=String(value||'').trim();
    try{ return new URL(s).hostname.replace(/^www\./,''); }catch(_){}
    const m=s.match(/^(?:[a-z]+:\/\/)?([^\/\s?#]+)/i);
    return m?m[1].replace(/^www\./,''):'';
  }
  function words(value){
    return String(value||'').replace(/^(mcp__|mcp\.)/,'').replace(/[_.\-]+/g,' ').replace(/\s+/g,' ').trim();
  }
  function args(tc){ return (tc&&tc.args&&typeof tc.args==='object')?tc.args:{}; }
  function firstString(a, keys){
    for(const k of keys){ const v=a[k]; if(typeof v==='string'&&v.trim()) return v; }
    return '';
  }

  // Plain-language summary of a shell command. Recognises the commands people
  // run every day; anything else is described by the program name only.
  const SHELL_RULES=[
    [/(^|\s)(pytest|python3? -m pytest|npm (run )?test|pnpm test|yarn test|go test|cargo test|jest|vitest)\b/i,{nl:'Tests gedraaid',en:'Ran tests'}],
    [/(^|\s)(eslint|ruff|flake8|npm run lint|pnpm lint|prettier)\b/i,{nl:'Code gecontroleerd',en:'Checked code style'}],
    [/(^|\s)git\s+(status|diff)\b/i,{nl:'Wijzigingen in Git bekeken',en:'Checked Git changes'}],
    [/(^|\s)git\s+log\b/i,{nl:'Git-geschiedenis bekeken',en:'Checked Git history'}],
    [/(^|\s)git\s+commit\b/i,{nl:'Wijzigingen vastgelegd in Git',en:'Committed changes'}],
    [/(^|\s)git\s+(push|pull|fetch|clone)\b/i,{nl:'Git gesynchroniseerd',en:'Synced with Git'}],
    [/(^|\s)git\b/i,{nl:'Git gebruikt',en:'Used Git'}],
    [/(^|\s)(npm|pnpm|yarn)\s+(install|ci|add)\b|(^|\s)pip3? install\b|(^|\s)uv (pip|add|sync)\b/i,{nl:'Pakketten geïnstalleerd',en:'Installed packages'}],
    [/(^|\s)(npm|pnpm|yarn)\s+run\s+build\b|(^|\s)make\b/i,{nl:'Project gebouwd',en:'Built the project'}],
    [/(^|\s)(curl|wget|http)\b/i,{nl:'Webadres opgevraagd',en:'Called a web address'}],
    [/(^|\s)(systemctl|service|journalctl)\b/i,{nl:'Service bekeken',en:'Checked a service'}],
    [/(^|\s)docker\b/i,{nl:'Docker gebruikt',en:'Used Docker'}],
    [/(^|\s)(ssh|scp|rsync)\b/i,{nl:'Op een andere machine gewerkt',en:'Worked on another machine'}],
    [/(^|\s)(ps|pgrep|top|htop|lsof|kill|pkill)\b/i,{nl:'Processen bekeken',en:'Checked processes'}],
    [/(^|\s)(ls|tree|find|du|df|stat)\b/i,{nl:'Mappen bekeken',en:'Looked at folders'}],
    [/(^|\s)(cat|head|tail|less|sed -n|wc)\b/i,{nl:'Bestand bekeken',en:'Looked at a file'}],
    [/(^|\s)(grep|rg|ag)\b/i,{nl:'Gezocht in bestanden',en:'Searched files'}],
    [/(^|\s)(mkdir|cp|mv|rm|touch|chmod|ln)\b/i,{nl:'Bestanden geordend',en:'Organised files'}],
    [/(^|\s)(python3?|node|deno|bun|ruby|php)\b/i,{nl:'Script gedraaid',en:'Ran a script'}],
    [/(^|\s)(sleep|wait)\b/i,{nl:'Even gewacht',en:'Waited a moment'}],
  ];
  function shellSummary(tc){
    const a=args(tc);
    const cmd=firstString(a,['command','cmd','script'])||String(tc&&tc.command||'');
    if(!cmd) return '';
    const worker=typeof root._delegatedWorkerName==='function'?root._delegatedWorkerName(tc):'';
    const l=lang();
    if(worker) return (l==='nl'?'Werk uitbesteed aan ':'Handed work to ')+worker;
    for(const [re,label] of SHELL_RULES){ if(re.test(cmd)) return label[l]||label.en; }
    const prog=basename(String(cmd).trim().replace(/^(sudo|env|time|nohup)\s+/,'').split(/\s+/)[0]||'');
    if(!prog||/[=$`"'(]/.test(prog)) return '';
    return (l==='nl'?'Met ':'With ')+clip(prog,24);
  }

  function target(tc, fam){
    const a=args(tc);
    const l=lang();
    switch(fam){
      case 'shell': return shellSummary(tc);
      case 'read': case 'write': {
        const p=firstString(a,['path','file_path','file','target','filename']);
        return p?clip(basename(p),48):'';
      }
      case 'search': {
        const q=firstString(a,['pattern','query','regex','name']);
        return q?'"'+clip(q,40)+'"':'';
      }
      case 'list': { const p=firstString(a,['path','dir','directory']); return p?clip(basename(p),40):''; }
      case 'web': {
        const u=firstString(a,['url','uri']);
        if(u) return host(u);
        if(Array.isArray(a.urls)&&a.urls.length) return host(a.urls[0])+(a.urls.length>1?' +'+(a.urls.length-1):'');
        const q=firstString(a,['query','q','search']);
        return q?'"'+clip(q,48)+'"':'';
      }
      case 'browser': {
        const u=firstString(a,['url']);
        if(u) return host(u);
        const action=String(tc&&tc.name||'').replace(/^browser_?/i,'');
        const map={navigate:['Pagina geopend','Opened a page'],click:['Geklikt','Clicked'],type:['Tekst getypt','Typed text'],snapshot:['Pagina bekeken','Looked at the page'],screenshot:['Schermafbeelding gemaakt','Took a screenshot'],scroll:['Gescrold','Scrolled'],back:['Terug gegaan','Went back'],press:['Toets ingedrukt','Pressed a key']};
        const hit=Object.keys(map).find(k=>action.toLowerCase().includes(k));
        return hit?map[hit][l==='nl'?0:1]:clip(words(action),32);
      }
      case 'delegate': {
        let n=0;
        if(Array.isArray(a.tasks)) n=a.tasks.length;
        else if(typeof a.tasks==='string'){ const m=a.tasks.match(/['"]goal['"]\s*:/g); n=m?m.length:0; }
        if(!n&&(a.goal||a.task)) n=1;
        if(a.action==='steer') return l==='nl'?'Bijsturing gestuurd':'Sent guidance';
        if(a.action==='stop') return l==='nl'?'Subagent gestopt':'Stopped a subagent';
        if(a.action==='list') return l==='nl'?'Subagents bekeken':'Checked subagents';
        return n?(n===1?(l==='nl'?'1 subagent':'1 subagent'):n+' subagents'):'';
      }
      case 'subagent': {
        const idx=Number(a.task_index)||0, cnt=Number(a.task_count)||0;
        const who=cnt>1?`${idx+1}/${cnt}`:'';
        const task=clip(a.task||tc.preview||'',72);
        return [who,task].filter(Boolean).join(': ');
      }
      case 'opencode': return clip(firstString(a,['title','task','goal','prompt']),56);
      case 'skill': return clip(firstString(a,['name','skill']),40);
      case 'memory': {
        const act=String(a.action||'').toLowerCase();
        if(act==='add'||act==='replace') return l==='nl'?'Opgeslagen':'Saved';
        if(act==='remove') return l==='nl'?'Verwijderd':'Removed';
        return '';
      }
      case 'process': return clip(words(a.action||''),24);
      case 'schedule': return clip(firstString(a,['name','schedule']),40);
      case 'mail': case 'calendar': case 'drive': case 'notion': case 'crm': case 'tools': case 'unknown': {
        const mcp=mcpParts(tc&&tc.name);
        if(mcp) return clip(words(mcp.tool||mcp.server),40);
        return fam==='unknown'?clip(words(tc&&tc.name),40):'';
      }
      default: return '';
    }
  }

  function state(tc){
    if(tc&&tc.is_error) return 'failed';
    if(tc&&tc.name==='subagent_progress'){
      const s=String(args(tc).status||'');
      if(s==='failed') return 'failed';
      if(s==='cancelled') return 'stopped';
      if(s==='completed') return 'done';
      if(tc.done===true) return 'last_seen';
      return s==='queued'?'queued':'running';
    }
    return tc&&tc.done===false?'running':'done';
  }

  function describe(tc){
    const fam=family(tc);
    const row=F[fam]||F.unknown;
    const st=state(tc);
    const nl=lang()==='nl';
    const titleIdx=st==='failed'?3:(st==='running'||st==='queued'||st==='last_seen'?1:2);
    let title=row[titleIdx+(nl?0:3)];
    if(fam==='subagent'&&st==='stopped') title=nl?'Subagent gestopt':'Subagent stopped';
    const mcp=mcpParts(tc&&tc.name);
    return {
      family:fam, emoji:row[0], title, target:target(tc,fam), state:st,
      duration:duration(tc), source:mcp?words(mcp.server):'',
    };
  }

  function duration(tc){
    if(!tc) return null;
    const d=Number(tc.duration);
    if(Number.isFinite(d)&&d>=0&&tc.duration!==null&&tc.duration!=='') return d;
    if(tc.name==='subagent_progress'){
      const x=Number(args(tc).duration_seconds);
      if(Number.isFinite(x)&&x>=0) return x;
    }
    return null;
  }

  function formatDuration(sec){
    const s=Number(sec);
    if(!Number.isFinite(s)||s<0) return '';
    if(s<1) return '<1s';
    if(s<60) return Math.round(s)+'s';
    const m=Math.floor(s/60), r=Math.round(s%60);
    if(m<60) return r?`${m}m ${r}s`:`${m}m`;
    const h=Math.floor(m/60);
    return `${h}${lang()==='nl'?'u':'h'} ${m%60}m`;
  }

  const STATE_ICON={running:'',queued:'⏳',done:'✅',failed:'⚠️',stopped:'⏹️',last_seen:'🕓'};
  function esc(s){ return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  // Small status chip: spinner while running, ✅ / ⚠️ when settled, plus duration.
  function statusChipHtml(info){
    const st=info&&info.state||'done';
    const label=text(st==='last_seen'?'last_seen':st);
    const dur=info&&info.duration!=null?formatDuration(info.duration):'';
    const mark=st==='running'?'<span class="sp-spin" aria-hidden="true"></span>':`<span aria-hidden="true">${STATE_ICON[st]||''}</span>`;
    return `<span class="sp-tool-status sp-tool-status-${esc(st)}" title="${esc(label)}">${mark}${dur?`<span class="sp-tool-dur">${esc(dur)}</span>`:''}<span class="sr-only">${esc(label)}</span></span>`;
  }

  // Outer worklog line: "⚙️ Verwerkt in 4s · 11 stappen" / "⚙️ Bezig · 12s · 3 stappen".
  function processedLine(opts){
    const o=opts||{};
    const n=Math.max(0,Number(o.steps)||0);
    const steps=n?(n===1?text('tools_one'):text('tools_many',{n})):'';
    const d=String(o.duration||'').trim();
    const head=o.live?text('working')+(d?' · '+d:''):(d?text('processed_in',{d}):text('processed'));
    return '⚙️ '+head+(steps?' · '+steps:'');
  }

  // One-line group summary: "🛠️ Werkstappen (12)" plus "💻 5 · 📄 3 · ⚠️ 1".
  const ORDER=['subagent','delegate','opencode','shell','read','write','search','list','web','browser','mail','calendar','drive','notion','crm','code','process','todo','memory','skill','image','vision','schedule','message','clarify','voice','tools','unknown'];
  function groupSummary(items){
    const list=Array.from(items||[]).filter(Boolean);
    const counts=Object.create(null);
    let failed=0, running=0, current=null;
    for(const it of list){
      const fam=it.family||family(it);
      const st=it.state||state(it);
      counts[fam]=(counts[fam]||0)+1;
      if(st==='failed') failed++;
      if(st==='running'||st==='queued'){ running++; current=it; }
    }
    const parts=ORDER.filter(f=>counts[f]).map(f=>`${(F[f]||F.unknown)[0]} ${counts[f]}`);
    if(failed) parts.push(`⚠️ ${failed}`);
    const head=`🛠️ ${text('steps')} (${list.length})`;
    const now=current&&current.title?`${text('now')}: ${(F[current.family]||F.unknown)[0]} ${current.title}${current.target?' '+current.target:''}`:'';
    return {
      title:`${text('steps')} (${list.length})`,
      parts, failed, running, count:list.length, current:now,
      text:now?`${head} · ${now}`:`${head}${parts.length?' · '+parts.join(' · '):''}`,
    };
  }

  // Plain-language card for assistant error replies ("**Label:** message").
  // Only known error labels qualify, so normal answers are never restyled.
  const ERRORS={
    'error':['⚠️','alert',['Er ging iets mis','Something went wrong'],['Probeer het opnieuw. Blijft dit gebeuren, geef het dan door aan support.','Please try again. If it keeps happening, let support know.']],
    'gateway request failed':['🔌','alert',['SynthPulse kon de AI niet bereiken','SynthPulse could not reach the AI'],['Probeer het zo opnieuw. Blijft dit gebeuren, geef het dan door aan support.','Try again in a moment. If it keeps happening, let support know.']],
    'gateway authentication failed':['🔑','alert',['De verbinding met de AI is niet goed ingesteld','The connection to the AI is not set up correctly'],['Dit moet een beheerder oplossen. Geef het door aan support.','An administrator needs to fix this. Please let support know.']],
    'service unavailable':['🌩️','alert',['De AI-dienst is even niet bereikbaar','The AI service is not available right now'],['Probeer het over een paar minuten opnieuw.','Please try again in a few minutes.']],
    'service busy':['🌩️','alert',['De AI-dienst is het even te druk','The AI service is busy right now'],['Probeer het over een minuut opnieuw.','Please try again in a minute.']],
    'no response from provider':['🌩️','alert',['De AI gaf geen antwoord','The AI did not answer'],['Probeer het opnieuw.','Please try again.']],
    'rate limit reached':['⏳','alert',['Even te veel verzoeken tegelijk','Too many requests at once'],['Wacht een minuut en probeer het opnieuw.','Wait a minute and try again.']],
    'out of credits':['💳','alert',['Het AI-tegoed is op','The AI credit has run out'],['Geef het door aan een beheerder.','Please let an administrator know.']],
    'model not found':['🧭','alert',['Dit AI-model is niet beschikbaar','This AI model is not available'],['Kies een ander model onder het tekstvak.','Pick another model below the message box.']],
    'provider mismatch':['🧭','alert',['Dit AI-model past niet bij de gekozen dienst','This AI model does not match the chosen service'],['Kies een ander model onder het tekstvak.','Pick another model below the message box.']],
    'context compression exhausted':['📚','alert',['Dit gesprek is te lang geworden','This conversation has become too long'],['Begin een nieuw gesprek en verwijs naar dit gesprek.','Start a new chat and refer back to this one.']],
    'tool iteration limit reached':['🛑','info',['Maximaal aantal werkstappen bereikt','Maximum number of work steps reached'],['Vraag de bot om verder te gaan.','Ask the bot to continue.']],
    'response interrupted':['⏸️','info',['Antwoord onderbroken','Reply interrupted'],['Stuur je bericht opnieuw om verder te gaan.','Send your message again to continue.']],
    'task cancelled':['⏹️','info',['Gestopt','Stopped'],['Je hebt deze taak gestopt.','You stopped this task.']],
  };
  function errorCard(label){
    const hit=ERRORS[String(label||'').trim().toLowerCase()];
    if(!hit) return null;
    const i=lang()==='nl'?0:1;
    return {emoji:hit[0],tone:hit[1],title:hit[2][i],hint:hit[3][i]};
  }

  const api={lang,errorCard,processedLine,setLanguage:v=>{forced=(v==='nl'||v==='en')?v:null;},text,family,describe,state,target,shellSummary,formatDuration,statusChipHtml,groupSummary,emojiFor:fam=>(F[fam]||F.unknown)[0],FAMILIES:Object.keys(F)};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.SynPulseFriendlyTools=api;
})(typeof window!=='undefined'?window:globalThis);
