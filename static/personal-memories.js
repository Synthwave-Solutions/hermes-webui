/* Person-owned memories. All untrusted content goes through textContent/value. */
window.PersonalMemories = (() => {
  let generation = 0;
  function render(body, options) {
    const context = options.context();
    const company = options.section === 'company';
    const section = company ? 'company' : 'mnemosyne';
    const gen = ++generation;
    let request = 0, offset = 0, query = '';
    const root = document.createElement('div');
    root.className = 'main-view-content personal-memories';
    body.replaceChildren(root);
    const live = () => gen === generation && context === options.context() && options.active() && root.parentNode === body;
    const make = (tag, text, parent = root) => {
      const element = document.createElement(tag);
      if (text) element.textContent = text;
      parent.appendChild(element);
      return element;
    };
    make('p', company ? 'All agents can use this company knowledge. Only admins can manage it. Automatic consolidation preserves your edits and keeps deleted topics suppressed.' : 'Only you can view and edit these memories. Private chats share your personal memory. Memories from a shared chat are used only in that chat.');
    const form = make('form');
    form.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px';
    const search = make('input', '', form);
    search.type = 'search'; search.placeholder = 'Search memories'; search.setAttribute('aria-label', 'Search memories');
    search.style.cssText = 'flex:1;min-width:120px';
    const submit = make('button', 'Search', form); submit.className = 'btn-secondary';
    const status = make('p'); status.setAttribute('role', 'status');
    const list = make('div');
    const pages = make('div'); pages.style.cssText = 'display:flex;gap:8px;margin-top:12px';
    const prev = make('button', 'Previous', pages), next = make('button', 'Next', pages);
    prev.className = next.className = 'btn-secondary';
    prev.onclick = () => { offset = Math.max(0, offset - 50); load(); };
    next.onclick = () => { offset += 50; load(); };
    form.onsubmit = e => { e.preventDefault(); query = search.value; offset = 0; load(); };
    async function load() {
      const seq = ++request;
      status.textContent = 'Loading memories…'; list.replaceChildren(); prev.disabled = next.disabled = true;
      try {
        const params = new URLSearchParams({section, q:query, offset:String(offset), session_id:options.sessionId});
        const data = await options.api('/api/memory?' + params);
        if (!live() || seq !== request) return;
        status.textContent = data.total ? `${data.total} saved memories` : 'No saved memories yet. New completed chats will add memories here.';
        if (company) {
          const state = data.consolidation || {};
          status.textContent = `${data.total} company memories · ${state.pending || 0} sources pending`;
          if (state.last_success) status.textContent += ' · Last consolidated: ' + new Date(state.last_success).toLocaleString();
          if (state.last_error) status.textContent += ' · Consolidation will retry (' + state.last_error + ')';
        }
        for (const item of data.items) card(item);
        prev.disabled = offset === 0; next.disabled = offset + data.limit >= data.total;
      } catch (err) {
        if (live() && seq === request) status.textContent = 'Could not load memories: ' + err.message;
      }
    }
    function card(item) {
      const article = make('article', '', list); article.className = 'notes-source-card';
      const meta = make('p', '', article); meta.className = 'memory-detail-mtime';
      meta.textContent = company ? `${item.category} · ${item.sources} sources · ${item.manual ? 'Admin correction protected' : 'Automatically consolidated'}` : `${item.scope === 'private' ? 'Private chats' : 'Shared chat only'} · ${new Date(item.timestamp).toLocaleString()}`;
      const content = make('p', item.content, article); content.style.cssText = 'white-space:pre-wrap;overflow-wrap:anywhere';
      const controls = make('div', '', article); controls.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap';
      const edit = make('button', 'Edit', controls), del = make('button', 'Delete', controls);
      edit.className = del.className = 'btn-secondary';
      const error = make('p', '', article); error.setAttribute('role', 'alert');
      async function write(operation, value) {
        if (!live()) return false;
        try {
          await options.api('/api/memory/write', {method:'POST', body:JSON.stringify({
            section, session_id:options.sessionId, bank:item.bank, id:item.id,
            revision:item.revision, operation, ...(operation === 'edit' ? {content:value} : {})
          })});
          if (live()) await load();
          return true;
        } catch (err) { if (live()) error.textContent = err.message; return false; }
      }
      del.onclick = async () => {
        if (!await options.confirm() || !live()) return;
        del.disabled = edit.disabled = true;
        if (!await write('delete')) del.disabled = edit.disabled = false;
      };
      edit.onclick = () => {
        content.hidden = controls.hidden = true;
        const editor = make('form', '', article);
        const input = make('textarea', '', editor); input.value = item.content; input.maxLength = 16000;
        input.setAttribute('aria-label', 'Memory content'); input.rows = 6;
        input.style.cssText = 'width:100%;box-sizing:border-box;margin-bottom:8px';
        const save = make('button', 'Save', editor); save.className = 'btn-primary';
        const cancel = make('button', 'Cancel', editor); cancel.type = 'button'; cancel.className = 'btn-secondary';
        cancel.onclick = () => { editor.remove(); content.hidden = controls.hidden = false; edit.focus(); };
        editor.onsubmit = async e => {
          e.preventDefault(); if (!input.value.trim()) { error.textContent = 'Enter a memory first.'; return; }
          save.disabled = cancel.disabled = true;
          if (!await write('edit', input.value)) save.disabled = cancel.disabled = false;
        };
        input.focus();
      };
    }
    load();
  }
  return {render};
})();
