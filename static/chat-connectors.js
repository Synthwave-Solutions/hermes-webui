/* The account connection and the current person's selection for this chat have separate owners. */
(() => {
  const dialog = document.getElementById('chatConnectorsDialog');
  const trigger = document.getElementById('chatConnectorsButton');
  const search = document.getElementById('chatConnectorsSearch');
  const list = document.getElementById('chatConnectorsList');
  const notice = document.getElementById('chatConnectorsStatus');
  const sources = ['nango', 'hosted'];
  let sessionId = '', generation = 0;
  const catalogs = new Map();
  const failures = new Set();
  const pending = new Set();
  const accountChoices = new Map();
  const current = () => dialog.open && sessionId === S.session?.session_id;
  const element = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function render() {
    if (!current()) return;
    const query = search.value.trim().toLocaleLowerCase();
    const rows = [];
    for (const [source, data] of catalogs)
      for (const row of data.connectors)
        if (row.name.toLocaleLowerCase().includes(query) || row.key.toLowerCase().includes(query))
          rows.push({...row, source, available:data.chat_available});
    rows.sort((a,b) => Number(b.connected)-Number(a.connected) || a.name.localeCompare(b.name));
    const fragment = document.createDocumentFragment();
    for (const row of rows.slice(0, 80)) {
      const item = element('li'), main = element('div'), name = element('strong', row.name);
      const key = row.source + ':' + row.key;
      const accounts = row.accounts || [];
      const meta = element('small', [row.source === 'hosted' ? t('chat_connect_hosted') : 'Nango',
        t(row.connected ? 'chat_connect_linked' : accounts.length ? 'chat_connect_expired' : 'chat_connect_unlinked')].join(' · '));
      main.append(name, meta); item.append(main);
      let accountSelect;
      if (accounts.length > 1) {
        accountSelect = element('select');
        accountSelect.setAttribute('aria-label', row.name+' · '+t('chat_connect_account'));
        for (const account of accounts) {
          const option = element('option', account.label || account.id);
          option.value = account.id;
          accountSelect.append(option);
        }
        const previous = accountChoices.get(key);
        if (accounts.some(account => account.id === previous)) accountSelect.value = previous;
        accountSelect.onchange = () => accountChoices.set(key, accountSelect.value);
        main.append(accountSelect);
      }
      const connect = element('button', t(row.connected || accounts.length ? 'chat_connect_reconnect' : 'integrations_connect'));
      connect.type='button'; connect.className='sm-btn'; connect.disabled=pending.has(key);
      connect.onclick = async () => {
        const g=generation; pending.add(key); connect.disabled=true;
        try {
          const accountId = accountSelect ? accountSelect.value : accounts[0]?.id;
          if (row.source === 'hosted') await _connectHosted({slug:row.key,connection_id:accountId}, connect, notice.id, () => g === generation && current());
          else await _intgConnect(row.key, accountId, message => {
            if (g === generation && current()) notice.textContent = message;
          });
          if (g===generation && current()) await loadSource(row.source,g);
        } finally { pending.delete(key); if (current()) render(); }
      };
      item.append(connect);
      const toggle=element('button', t(!row.available ? 'chat_connect_restricted' :
        !row.selected ? 'chat_connect_off' : row.connected ? 'chat_connect_on' : 'chat_connect_when_linked'));
      toggle.type='button'; toggle.className='sm-btn chat-connector-toggle';
      toggle.setAttribute('aria-label', row.name+' · '+row.source+' · '+t('chat_connect_selection'));
      toggle.setAttribute('aria-pressed',String(!!(row.available && row.selected)));
      toggle.disabled=!row.available || pending.has(key);
      toggle.onclick=async () => {
        const g=generation; pending.add(key); toggle.disabled=true; connect.disabled=true;
        try {
          await api('/api/session/connectors',{method:'POST',body:JSON.stringify({session_id:sessionId,source:row.source,key:row.key,enabled:!row.selected})});
          if (g!==generation || !current()) return;
          const stored=catalogs.get(row.source)?.connectors.find(entry=>entry.key===row.key);
          if (stored) stored.selected=!row.selected;
          notice.textContent=t('chat_connect_saved');
        } catch (_) { if (g===generation && current()) notice.textContent=t('chat_connect_failed'); }
        finally { pending.delete(key); if (g===generation && current()) {render(); list.querySelectorAll('button.chat-connector-toggle').forEach(b=>{if(b.getAttribute('aria-label')===toggle.getAttribute('aria-label'))b.focus();});} }
      };
      item.append(toggle); fragment.append(item);
    }
    if (rows.length>80) fragment.append(element('li',t('chat_connect_filter')));
    if (!rows.length && catalogs.size===sources.length) fragment.append(element('li',t('chat_connect_empty')));
    for (const source of failures) fragment.append(element('li',(source==='hosted'?t('chat_connect_hosted'):'Nango')+' · '+t('chat_connect_failed')));
    list.replaceChildren(fragment);
    list.setAttribute('aria-busy',String(catalogs.size+failures.size<sources.length));
  }

  async function loadSource(source,g) {
    try {
      const data=await api('/api/session/connectors?'+new URLSearchParams({source,session_id:sessionId}),{timeoutMs:75000,timeoutToast:false});
      if(g!==generation || !current())return;
      failures.delete(source); catalogs.set(source,data);
    } catch (_) {if(g!==generation || !current())return;catalogs.delete(source);failures.add(source);}
    render();
  }
  async function refresh() {
    const g=++generation;
    failures.clear();catalogs.clear();notice.textContent=t('loading');render();
    await Promise.all(sources.map(source=>loadSource(source,g)));
    if(g===generation && current() && notice.textContent===t('loading')) notice.textContent='';
  }
  trigger.onclick=async () => {
    if (!S.session?.session_id) {await newSession(false,{worktree:false});}
    if (!S.session?.session_id) return;
    sessionId=S.session.session_id;search.value=''; dialog.showModal();search.focus();refresh();
  };
  document.getElementById('chatConnectorsClose').onclick=()=>dialog.close();
  document.getElementById('chatConnectorsRefresh').onclick=refresh;
  search.oninput=render;
  dialog.addEventListener('close',()=>{generation++;sessionId='';catalogs.clear();failures.clear();accountChoices.clear();list.replaceChildren();notice.textContent='';});
  window.addEventListener('focus',()=>{if(current() && !pending.size)refresh();});
  window.syncChatConnectorSession=()=>{if(dialog.open && !current())dialog.close();};
})();
