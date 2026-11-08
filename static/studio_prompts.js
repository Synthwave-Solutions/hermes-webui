/* Studio: shared prompts and the organisation profile (8 Nov 2026).

   Prompts: personal prompts stay in /api/prompts (the composer's saved
   prompts). Shared prompts live in /api/studio/prompts and are visible to a
   team, a department or the whole organisation, grouped by category or by
   where they are shared. "Use in chat" counts the use and puts the prompt in
   a new conversation.

   Organisation profile: one profile per installation that the Super Agent
   reads as context in every QuickScan, design and build plan. Organisation
   admins fill it in, or let the agent research the website first; the
   research only proposes, nothing is saved until Save. */
(function(){
  'use strict';
  const NL = {
    pr_intro: 'Prompts die je team, afdeling of de hele organisatie deelt, plus je eigen opgeslagen prompts. Gebruik ze in de chat met één klik.',
    new_prompt: 'Nieuwe prompt', search: 'Zoek in prompts', group_by: 'Groeperen', g_category: 'Categorie', g_where: 'Gedeeld met',
    mine: 'Mijn prompts', mine_note: 'Alleen voor jou; ook te kiezen in het chatveld.', team: 'Team', department: 'Afdeling', org: 'Hele organisatie',
    no_category: 'Zonder categorie', use: 'Gebruik in chat', copy: 'Kopiëren', copied: 'Gekopieerd', edit: 'Bewerken', remove: 'Verwijderen',
    share: 'Delen', uses: 'keer gebruikt', label: 'Naam', text: 'Prompt', category: 'Categorie', share_with: 'Delen met', only_me: 'Alleen ik',
    save: 'Opslaan', cancel: 'Annuleren', saved: 'Prompt opgeslagen', removed: 'Prompt verwijderd', confirm_remove: 'Deze prompt verwijderen voor iedereen die hem ziet?',
    empty: 'Nog geen prompts. Bewaar er een uit het chatveld, uit een Playbook-stap, of maak er hier een.', none_found: 'Geen prompts gevonden.',
    pf_intro: 'Wie jullie zijn, wat jullie willen bereiken en met welke systemen jullie werken. De Super Agent leest dit mee bij elke QuickScan, elk ontwerp en elk bouwplan.',
    pf_name: 'Naam van de organisatie', pf_website: 'Website', pf_sector: 'Sector', pf_size: 'Omvang', pf_description: 'Wat jullie doen',
    pf_products: 'Producten en diensten (één per regel)', pf_customers: 'Klanten', pf_goals: 'Doelen (één per regel)',
    pf_systems: 'Systemen in gebruik (gescheiden door komma’s)', pf_policy: 'Beleid voor AI en data', research: 'Onderzoek de website',
    researching: 'De agent leest de website…', proposal: 'Voorstel van de agent', proposal_note: 'Alleen wat op de website staat. Niets is opgeslagen tot je Opslaan kiest.',
    take_empty: 'Vul lege velden', take_all: 'Neem alles over', sources: 'Bronnen', context_title: 'Zo leest de agent het profiel',
    pf_readonly: 'Alleen organisatiebeheerders wijzigen het profiel.', pf_empty: 'Nog geen organisatieprofiel. Een beheerder vult het in, of laat de agent de website onderzoeken.',
    pf_hint: 'Vul het organisatieprofiel in: dan sluiten de voorstellen van de QuickScan aan op jullie doelen en systemen.', open_profile: 'Organisatieprofiel invullen',
    updated: 'Bijgewerkt', r_private: 'Alleen openbare websites kunnen worden onderzocht.', r_unreachable: 'De website was niet bereikbaar. Probeer het adres opnieuw of vul het profiel zelf in.', r_no_site: 'Vul eerst de website in.', pf_saved: 'Organisatieprofiel opgeslagen'
  };
  const EN = {
    pr_intro: 'Prompts your team, department or the whole organisation shares, plus your own saved prompts. Use them in chat with one click.',
    new_prompt: 'New prompt', search: 'Search prompts', group_by: 'Group by', g_category: 'Category', g_where: 'Shared with',
    mine: 'My prompts', mine_note: 'Only for you; also available in the chat box.', team: 'Team', department: 'Department', org: 'Whole organisation',
    no_category: 'No category', use: 'Use in chat', copy: 'Copy', copied: 'Copied', edit: 'Edit', remove: 'Remove',
    share: 'Share', uses: 'uses', label: 'Name', text: 'Prompt', category: 'Category', share_with: 'Share with', only_me: 'Only me',
    save: 'Save', cancel: 'Cancel', saved: 'Prompt saved', removed: 'Prompt removed', confirm_remove: 'Remove this prompt for everyone who sees it?',
    empty: 'No prompts yet. Save one from the chat box or a Playbook step, or create one here.', none_found: 'No prompts found.',
    pf_intro: 'Who you are, what you want to achieve and which systems you use. The Super Agent reads this in every QuickScan, design and build plan.',
    pf_name: 'Organisation name', pf_website: 'Website', pf_sector: 'Sector', pf_size: 'Size', pf_description: 'What you do',
    pf_products: 'Products and services (one per line)', pf_customers: 'Customers', pf_goals: 'Goals (one per line)',
    pf_systems: 'Systems in use (comma separated)', pf_policy: 'Policy for AI and data', research: 'Research the website',
    researching: 'The agent is reading the website…', proposal: 'Proposal from the agent', proposal_note: 'Only what the website says. Nothing is saved until you choose Save.',
    take_empty: 'Fill empty fields', take_all: 'Take all', sources: 'Sources', context_title: 'How the agent reads the profile',
    pf_readonly: 'Only organisation admins change the profile.', pf_empty: 'No organisation profile yet. An admin fills it in, or lets the agent research the website.',
    pf_hint: 'Fill in the organisation profile so QuickScan proposals match your goals and systems.', open_profile: 'Fill in the organisation profile',
    updated: 'Updated', r_private: 'Only public websites can be researched.', r_unreachable: 'The website could not be reached. Try the address again or fill in the profile yourself.', r_no_site: 'Fill in the website first.', pf_saved: 'Organisation profile saved'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = k => (lang() === 'en' ? EN : NL)[k] || NL[k] || k;
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? ''));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const errMsg = e => (e && e.message) || String(e);

  const P = { body: null, data: null, mine: [], q: '', group: (() => { try { return localStorage.getItem('sp-pr-group') || 'category'; } catch (_e) { return 'category'; } })(),
              form: null, profile: null, proposal: null, busy: false };

  // ── Prompts ────────────────────────────────────────────────────────────────
  async function loadPrompts(){
    const [shared, mine] = await Promise.all([call('/api/studio/prompts').catch(e => { toast(errMsg(e)); return { prompts: [], teams: [], departments: [] }; }),
                                              call('/api/prompts').catch(() => ({ prompts: [] }))]);
    P.data = shared; P.mine = (mine && mine.prompts) || [];
  }
  const teamName = k => ((P.data.teams || []).find(t => t.key === k) || {}).name || k;
  const deptName = k => ((P.data.departments || []).find(d => d.key === k) || {}).name || k;
  function whereLabel(p){
    return p.scope === 'team' ? w('team') + ' ' + teamName(p.team) : p.scope === 'department' ? w('department') + ' ' + deptName(p.department) : w('org');
  }
  function card(p, personal){
    const id = personal ? 'me:' + p.id : p.id;
    return `<div class="pr-card" data-pr="${H(id)}">
      <div class="pr-head"><strong>${H(p.label || p.text.slice(0, 60))}</strong>${p.uses ? `<span class="om-small om-muted">${H(p.uses)} ${H(w('uses'))}</span>` : ''}</div>
      <p class="pr-text">${H(p.text)}</p>
      <div class="pr-foot"><span class="om-chips">${personal ? `<span class="om-chip">${H(w('only_me'))}</span>` : `<span class="om-chip">${H(whereLabel(p))}</span>${p.category && P.group !== 'category' ? `<span class="om-chip">${H(p.category)}</span>` : ''}`}</span>
        <span class="pr-actions"><button type="button" class="sm-btn primary" data-pr-use>${H(w('use'))}</button><button type="button" class="sm-btn" data-pr-copy>${H(w('copy'))}</button>
        ${personal ? `<button type="button" class="sm-btn" data-pr-share>${H(w('share'))}</button><button type="button" class="sm-btn pr-quiet" data-pr-remove>${H(w('remove'))}</button>`
          : p.editable ? `<button type="button" class="sm-btn" data-pr-edit>${H(w('edit'))}</button><button type="button" class="sm-btn pr-quiet" data-pr-remove>${H(w('remove'))}</button>` : ''}</span></div>
    </div>`;
  }
  function formHtml(){
    const f = P.form; if (!f) return '';
    const d = P.data || {};
    const opts = [`<option value="me" ${f.scope === 'me' ? 'selected' : ''}>${H(w('only_me'))}</option>`]
      .concat((d.teams || []).filter(t => (d.my_teams || []).includes(t.key) || d.is_admin).map(t => `<option value="team:${H(t.key)}" ${f.scope === 'team' && f.team === t.key ? 'selected' : ''}>${H(w('team'))} ${H(t.name)}</option>`))
      .concat((d.departments || []).filter(x => (d.my_departments || []).includes(x.key) || d.is_admin).map(x => `<option value="department:${H(x.key)}" ${f.scope === 'department' && f.department === x.key ? 'selected' : ''}>${H(w('department'))} ${H(x.name)}</option>`))
      .concat([`<option value="org" ${f.scope === 'org' ? 'selected' : ''}>${H(w('org'))}</option>`]);
    return `<form class="om-card pr-form" data-pr-form>
      <label class="om-field">${H(w('label'))}<input name="label" maxlength="120" value="${H(f.label || '')}"></label>
      <label class="om-field">${H(w('text'))}<textarea name="text" rows="5" required maxlength="8000">${H(f.text || '')}</textarea></label>
      <div class="pr-form-row"><label class="om-field">${H(w('category'))}<input name="category" maxlength="60" list="prCategories" value="${H(f.category || '')}"><datalist id="prCategories">${(d.categories || []).map(c => `<option value="${H(c)}">`).join('')}</datalist></label>
        <label class="om-field">${H(w('share_with'))}<select name="scope">${opts.join('')}</select></label></div>
      <div class="om-value-actions"><button type="submit" class="sm-btn primary">${H(w('save'))}</button><button type="button" class="sm-btn" data-pr-cancel>${H(w('cancel'))}</button></div>
    </form>`;
  }
  function paintPrompts(){
    const d = P.data || { prompts: [] };
    const q = P.q.toLowerCase();
    const hit = p => !q || (String(p.label || '') + ' ' + p.text + ' ' + (p.category || '')).toLowerCase().includes(q);
    const mine = P.mine.filter(hit);
    const shared = (d.prompts || []).filter(hit);
    const groups = new Map();
    for (const p of shared) { const k = P.group === 'category' ? (p.category || w('no_category')) : whereLabel(p); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(p); }
    let open = {}; try { open = JSON.parse(localStorage.getItem('sp-pr-open') || '{}') || {}; } catch (_e) {}
    const ordered = [...groups.entries()].sort((a, b) => (a[0] === w('no_category')) - (b[0] === w('no_category')) || a[0].localeCompare(b[0]));
    P.body.innerHTML = `<p class="om-intro">${H(w('pr_intro'))}</p>
      <div class="bl-filters"><input class="om-select pb-search" type="search" data-pr-q value="${H(P.q)}" placeholder="${H(w('search'))}" aria-label="${H(w('search'))}">
        <div class="om-seg" role="group" aria-label="${H(w('group_by'))}">${[['category', 'g_category'], ['where', 'g_where']].map(([g, l]) => `<button type="button" aria-pressed="${P.group === g}" data-pr-group="${g}">${H(w(l))}</button>`).join('')}</div>
        <button type="button" class="sm-btn primary" data-pr-new data-tour="studio-prompt-new" style="margin-left:auto">${H(w('new_prompt'))}</button></div>
      ${formHtml()}
      ${!mine.length && !shared.length ? `<div class="om-empty"><p>${H(w(q ? 'none_found' : 'empty'))}</p></div>` : ''}
      <div class="pb-groups" data-tour="studio-prompts">
        ${mine.length ? `<details class="pb-group" data-pr-gopen="me" ${open.me === false ? '' : 'open'}><summary><span class="om-chev" aria-hidden="true"></span><strong>${H(w('mine'))}</strong><span class="om-side-count">${mine.length}</span><span class="om-small om-muted pr-group-note">${H(w('mine_note'))}</span></summary><div class="pr-grid">${mine.map(p => card(p, true)).join('')}</div></details>` : ''}
        ${ordered.map(([k, list]) => { const id = P.group + ':' + k; return `<details class="pb-group" data-pr-gopen="${H(id)}" ${open[id] === false ? '' : 'open'}><summary><span class="om-chev" aria-hidden="true"></span><strong>${H(k)}</strong><span class="om-side-count">${list.length}</span></summary><div class="pr-grid">${list.map(p => card(p, false)).join('')}</div></details>`; }).join('')}
      </div>`;
  }
  function find(id){
    if (id.startsWith('me:')) return { personal: true, p: P.mine.find(x => x.id === id.slice(3)) };
    return { personal: false, p: ((P.data || {}).prompts || []).find(x => x.id === id) };
  }
  async function useInChat(text){
    if (typeof switchPanel === 'function') await switchPanel('chat');
    if (typeof newSession === 'function') await newSession(false);
    if (typeof insertSavedPromptIntoComposer === 'function') insertSavedPromptIntoComposer(text);
    else { const box = document.getElementById('msg'); if (box) { box.value = text; box.focus(); } }
  }
  async function submitForm(form){
    const f = P.form; const fd = new FormData(form);
    const scopeVal = String(fd.get('scope') || 'me');
    const [scope, key] = scopeVal.includes(':') ? scopeVal.split(':') : [scopeVal, ''];
    const text = String(fd.get('text') || '').trim(); const label = String(fd.get('label') || '').trim();
    if (!text) return;
    try {
      if (scope === 'me') {
        await call('/api/prompts', { method: 'POST', body: JSON.stringify({ text, label }) });
        if (f.fromMine && f.id) { /* unchanged personal copy stays */ }
      } else {
        const body = { text, label, category: String(fd.get('category') || '').trim(), scope, source: f.source || '' };
        if (scope === 'team') body.team = key;
        if (scope === 'department') body.department = key;
        if (f.id && !f.fromMine) body.id = f.id;
        await post('/api/studio/prompts', body);
      }
      toast(w('saved')); P.form = null; await loadPrompts(); paintPrompts();
    } catch (e) { toast(errMsg(e)); }
  }

  // ── Organisation profile ──────────────────────────────────────────────────
  const FIELDS = [['name', 'input'], ['website', 'input'], ['sector', 'input'], ['size', 'input'], ['description', 'textarea'],
                  ['products', 'list'], ['customers', 'input'], ['goals', 'list'], ['systems', 'csv'], ['policy', 'textarea']];
  const fieldVal = (p, k, kind) => kind === 'list' ? (p[k] || []).join('\n') : kind === 'csv' ? (p[k] || []).join(', ') : (p[k] || '');
  function paintProfile(){
    const p = P.profile || {};
    const empty = !FIELDS.some(([k]) => (Array.isArray(p[k]) ? p[k].length : p[k]));
    if (!p.editable) {
      P.body.innerHTML = `<p class="om-intro">${H(w('pf_intro'))}</p>${empty ? `<div class="om-empty"><p>${H(w('pf_empty'))}</p></div>` : `<div class="om-card pf-read" data-tour="studio-profile">${FIELDS.filter(([k]) => Array.isArray(p[k]) ? p[k].length : p[k]).map(([k, kind]) => `<div class="pf-row"><span class="om-small om-muted">${H(w('pf_' + k))}</span><span>${kind === 'list' || kind === 'csv' ? (p[k] || []).map(x => `<span class="om-chip">${H(x)}</span>`).join(' ') : H(p[k])}</span></div>`).join('')}</div>`}
        <p class="om-small om-muted" style="margin-top:14px">${H(w('pf_readonly'))}</p>`;
      return;
    }
    const pr = P.proposal;
    P.body.innerHTML = `<p class="om-intro">${H(w('pf_intro'))}</p>
      <form class="om-card pf-form" data-pf-form data-tour="studio-profile">
        <div class="pf-grid">${FIELDS.map(([k, kind]) => `<label class="om-field ${kind === 'textarea' || kind === 'list' ? 'wide' : ''}">${H(w('pf_' + k))}${kind === 'textarea' || kind === 'list'
          ? `<textarea name="${k}" rows="${kind === 'list' ? 3 : 3}">${H(fieldVal(p, k, kind))}</textarea>` : `<input name="${k}" value="${H(fieldVal(p, k, kind))}" ${k === 'website' ? 'inputmode="url" placeholder="https://"' : ''}>`}</label>`).join('')}</div>
        <div class="om-value-actions"><button type="submit" class="sm-btn primary">${H(w('save'))}</button>
          <button type="button" class="sm-btn" data-pf-research data-tour="studio-profile-research" ${P.busy ? 'disabled' : ''}>${H(P.busy ? w('researching') : w('research'))}</button>
          ${p.updated_at ? `<span class="om-small om-muted">${H(w('updated'))}: ${H(new Date(p.updated_at * 1000).toLocaleString(lang() === 'en' ? 'en-GB' : 'nl-NL', { dateStyle: 'medium', timeStyle: 'short' }))}</span>` : ''}</div>
      </form>
      ${pr ? `<section class="om-card pf-proposal"><h3>${H(w('proposal'))}</h3><p class="om-small om-muted">${H(pr.summary || '')} ${H(w('proposal_note'))}</p>
        <div class="pf-read">${FIELDS.filter(([k]) => Array.isArray(pr.proposal[k]) ? pr.proposal[k].length : pr.proposal[k]).map(([k, kind]) => `<div class="pf-row"><span class="om-small om-muted">${H(w('pf_' + k))}</span><span>${kind === 'list' || kind === 'csv' ? pr.proposal[k].map(x => `<span class="om-chip">${H(x)}</span>`).join(' ') : H(pr.proposal[k])}</span></div>`).join('')}</div>
        <p class="om-small om-muted">${H(w('sources'))}: ${(pr.sources || []).map(s => H(s)).join(', ')}</p>
        <div class="om-value-actions"><button type="button" class="sm-btn primary" data-pf-take="empty">${H(w('take_empty'))}</button><button type="button" class="sm-btn" data-pf-take="all">${H(w('take_all'))}</button></div></section>` : ''}
      ${p.context ? `<details class="pf-context"><summary>${H(w('context_title'))}</summary><pre>${H(p.context)}</pre></details>` : ''}`;
  }
  function formToProfile(form){
    const fd = new FormData(form); const out = {};
    for (const [k, kind] of FIELDS) {
      const v = String(fd.get(k) || '');
      out[k] = kind === 'list' ? v.split('\n').map(x => x.trim()).filter(Boolean) : kind === 'csv' ? v.split(',').map(x => x.trim()).filter(Boolean) : v.trim();
    }
    return out;
  }

  // ── Wiring ─────────────────────────────────────────────────────────────────
  function bind(root){
    if (!root || root.dataset.prBound) return;
    root.dataset.prBound = '1';
    root.addEventListener('input', ev => {
      if (!ev.target.hasAttribute('data-pr-q')) return;
      P.q = ev.target.value; const pos = ev.target.selectionStart; paintPrompts();
      const q = P.body.querySelector('[data-pr-q]'); if (q) { q.focus(); q.setSelectionRange(pos, pos); }
    });
    root.addEventListener('toggle', ev => {
      const d = ev.target; if (!d || !d.dataset || !d.dataset.prGopen) return;
      let open = {}; try { open = JSON.parse(localStorage.getItem('sp-pr-open') || '{}') || {}; } catch (_e) {}
      open[d.dataset.prGopen] = d.open; try { localStorage.setItem('sp-pr-open', JSON.stringify(open)); } catch (_e) {}
    }, true);
    root.addEventListener('submit', async ev => {
      if (ev.target.hasAttribute('data-pr-form')) { ev.preventDefault(); await submitForm(ev.target); }
      else if (ev.target.hasAttribute('data-pf-form')) {
        ev.preventDefault();
        try { P.profile = await post('/api/studio/profile', formToProfile(ev.target)); P.profile.context = (await call('/api/studio/profile')).context; P.proposal = null; toast(w('pf_saved')); paintProfile(); if (window.SPStudio && window.SPStudio.refreshCounts) await window.SPStudio.refreshCounts(); }
        catch (e) { toast(errMsg(e)); }
      }
    });
    root.addEventListener('click', async ev => {
      const b = ev.target.closest('button'); if (!b || !P.body || !P.body.contains(b)) return;
      if (b.dataset.prGroup) { P.group = b.dataset.prGroup; try { localStorage.setItem('sp-pr-group', P.group); } catch (_e) {} paintPrompts(); return; }
      if (b.hasAttribute('data-pr-new')) { P.form = { scope: (P.data.my_teams || [])[0] ? 'team' : 'org', team: (P.data.my_teams || [])[0] || '' }; paintPrompts(); const t = P.body.querySelector('[data-pr-form] textarea'); if (t) t.focus(); return; }
      if (b.hasAttribute('data-pr-cancel')) { P.form = null; paintPrompts(); return; }
      if (b.hasAttribute('data-pf-research')) {
        const site = (P.body.querySelector('[data-pf-form] [name="website"]') || {}).value || '';
        P.busy = true; paintProfile();
        try { P.proposal = await post('/api/studio/profile', { op: 'research', url: site }); }
        catch (e) { const m = errMsg(e); toast(/public/i.test(m) ? w('r_private') : /reached|answered/i.test(m) ? w('r_unreachable') : /website first/i.test(m) ? w('r_no_site') : m); }
        P.busy = false; paintProfile(); return;
      }
      if (b.dataset.pfTake && P.proposal) {
        const form = P.body.querySelector('[data-pf-form]'); const cur = formToProfile(form); const pr = P.proposal.proposal;
        for (const [k] of FIELDS) { const has = Array.isArray(cur[k]) ? cur[k].length : cur[k]; const offer = Array.isArray(pr[k]) ? pr[k].length : pr[k]; if (offer && (b.dataset.pfTake === 'all' || !has)) cur[k] = pr[k]; }
        P.profile = Object.assign({}, P.profile, cur); paintProfile(); return;
      }
      const cardEl = b.closest('[data-pr]'); if (!cardEl) return;
      const { personal, p } = find(cardEl.dataset.pr); if (!p) return;
      if (b.hasAttribute('data-pr-use')) { if (!personal) post('/api/studio/prompts', { op: 'use', id: p.id }).catch(() => {}); await useInChat(p.text); return; }
      if (b.hasAttribute('data-pr-copy')) { try { await navigator.clipboard.writeText(p.text); toast(w('copied')); } catch (_e) { toast(p.text.slice(0, 80)); } return; }
      if (b.hasAttribute('data-pr-share')) { P.form = { label: p.label, text: p.text, scope: (P.data.my_teams || [])[0] ? 'team' : 'org', team: (P.data.my_teams || [])[0] || '', fromMine: true }; paintPrompts(); P.body.querySelector('[data-pr-form]').scrollIntoView({ block: 'nearest' }); return; }
      if (b.hasAttribute('data-pr-edit')) { P.form = Object.assign({}, p); paintPrompts(); P.body.querySelector('[data-pr-form]').scrollIntoView({ block: 'nearest' }); return; }
      if (b.hasAttribute('data-pr-remove')) {
        if (!confirm(w('confirm_remove'))) return;
        try { if (personal) await call('/api/prompts', { method: 'DELETE', body: JSON.stringify({ id: p.id }) }); else await post('/api/studio/prompts', { op: 'delete', id: p.id }); toast(w('removed')); }
        catch (e) { toast(errMsg(e)); }
        await loadPrompts(); paintPrompts();
      }
    });
  }
  async function render(body, tab){
    P.body = body; bind(body.closest('#mainStudio'));
    if (tab === 'profile') {
      body.innerHTML = '<div class="om-skeleton"></div>';
      try { P.profile = await call('/api/studio/profile'); } catch (e) { P.profile = {}; toast(errMsg(e)); }
      paintProfile(); return;
    }
    body.innerHTML = '<div class="om-skeleton"></div><div class="om-skeleton"></div>';
    await loadPrompts(); paintPrompts();
  }
  // Save a playbook step's prompt as a shared prompt of the playbook's team (or the organisation).
  async function saveFromStep(pb, step){
    const body = { label: step.title || '', text: step.prompt || '', category: pb.category || '', source: 'playbook:' + pb.id,
                   scope: pb.team ? 'team' : 'org' };
    if (pb.team) body.team = pb.team;
    return post('/api/studio/prompts', body);
  }
  window.SPPrompts = { render, saveFromStep, pfHint: () => w('pf_hint'), pfOpen: () => w('open_profile') };
})();
