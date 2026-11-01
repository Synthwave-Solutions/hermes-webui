// Integration sources share navigation, but retain their own account ownership.
let _integrationTab = 'connectors';
let _hubEpoch = 0;
let _hostedRows = null;
let _hostedLimit = 60;
let _hostedQuery = '';
let _pluginInventory = null;
let _hostedPoll = null;
const _hubText = (key, fallback) => _intgT(key, fallback);

function _hubNode(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function _hubButton(label, action) {
  const button = _hubNode('button', 'sm-btn', label);
  button.type = 'button'; button.addEventListener('click', action);
  return button;
}
function _hubStatus(id, text) { const node = $(id); if (node) node.textContent = text; }
function _hubBusy(id) { _hubStatus(id, _hubText('loading', 'Loading…')); }

async function switchIntegrationTab(tab) {
  if (!['connectors', 'plugins', 'vault', 'channels'].includes(tab)) return;
  _integrationTab = tab;
  ++_hubEpoch;
  clearTimeout(_hostedPoll); _hostedPoll = null;
  for (const name of ['connectors', 'plugins', 'vault', 'channels']) {
    const suffix = name[0].toUpperCase() + name.slice(1);
    $('intgPane' + suffix).hidden = name !== tab;
    $('intgTab' + suffix).setAttribute('aria-selected', String(name === tab));
  }
  await loadIntegrationTab();
}

async function loadIntegrationTab() {
  const epoch = ++_hubEpoch;
  if (_integrationTab === 'connectors') {
    await Promise.allSettled([_intgLoadCatalog(), _intgRefreshConnections(), _intgRefreshRequests(),
      _loadHostedCatalog(epoch), _loadHostedAccounts(epoch)]);
  } else if (_integrationTab === 'vault') {
    await loadVault();
  } else if (_integrationTab === 'channels') {
    await Promise.allSettled([chLoadChannels(), chLoadMine()]);
  } else if (_integrationTab === 'plugins') {
    _hubBusy('pluginCatalogList');
    try {
      const data = await api('/api/plugins/catalog', {timeoutMs:45000, timeoutToast:false});
      if (epoch !== _hubEpoch) return;
      _pluginInventory = data;
      _hubStatus('pluginScope', _hubText('integrations_plugin_scope', 'Bot profile') + ': ' + data.profile);
      renderIntegrationPlugins();
    } catch (error) { if (epoch === _hubEpoch) _hubStatus('pluginCatalogList', error.message); }
  }
}

async function _loadHostedCatalog(epoch) {
  try {
    const data = await api('/api/integrations/hosted/catalog', {timeoutMs:45000, timeoutToast:false});
    if (epoch !== _hubEpoch) return;
    _hostedRows = Array.isArray(data.connectors) ? data.connectors : [];
    _intgRenderCategoryChips();
    _intgRenderGrid();
  } catch (error) { if (epoch === _hubEpoch) _hubStatus('hostedActionStatus', _hubText('integrations_catalog_partial', 'Some app connectors could not be loaded. Refresh to retry.')); }
}

function _intgAllProviders() {
  const existing = (_intgCatalog && _intgCatalog.providers) || [];
  const hosted = (_hostedRows || []).map(row => ({...row, _hosted:true, key:'hosted-' + row.slug,
    display_name:row.name, categories:row.category ? [row.category] : [], configured:true}));
  return existing.concat(hosted).sort((a,b) => String(a.display_name).localeCompare(String(b.display_name)));
}
function _intgVisibleProviders(rows) {
  const key = _intgSearch + '\0' + _intgCategory;
  if (key !== _hostedQuery) { _hostedQuery = key; _hostedLimit = 60; }
  _hubStatus('intgCount', rows.length + ' ' + _hubText('integrations_hosted_tab', 'app connectors'));
  if ($('intgMore')) $('intgMore').hidden = rows.length <= _hostedLimit;
  return rows.slice(0, _hostedLimit);
}
function _hostedCardHtml(row) {
  const connected = (_hostedAccounts || []).some(account => account.connector === row.slug && account.status === 'active' && !account.disabled);
  const pending = _intgPendingRequestKeys().has(row.key);
  const label = pending ? _hubText('integrations_waiting_approval', 'Waiting for approval')
    : _hubText('integrations_connect', 'Connect');
  return '<article class="intg-card configured"><div class="intg-card-head"><div class="intg-card-name">' + _intgEsc(row.name) + '</div></div>'
    + '<p class="intg-muted">' + _intgEsc(row.description || '') + '</p>'
    + (connected ? '<span class="intg-badge intg-badge-ok">' + _intgEsc(_hubText('integrations_connected', 'Connected')) + '</span>' : '')
    + '<div class="intg-card-actions"><button class="intg-btn primary" type="button" data-hosted-connect="' + _intgEsc(row.slug) + '"'
    + (pending ? ' disabled' : '') + '>' + _intgEsc(label) + '</button></div></article>';
}
function showMoreHosted() { _hostedLimit += 60; _intgRenderGrid(); }
let _hostedAccounts = [];

async function _loadHostedAccounts(epoch = _hubEpoch) {
  try {
    const data = await api('/api/integrations/hosted/accounts', {timeoutMs:60000, timeoutToast:false});
    if (epoch !== _hubEpoch) return;
    _hostedAccounts = data.accounts || [];
    _intgRenderConnections();
    _intgRenderGrid();
  } catch (error) { if (epoch === _hubEpoch) _hubStatus('hostedActionStatus', error.message); }
}

async function _connectHosted(row, button) {
  const epoch = _hubEpoch;
  const popup = window.open('about:blank', '_blank');
  if (popup) popup.opener = null;
  button.disabled = true;
  _hubStatus('hostedActionStatus', _hubText('integrations_connecting', 'Preparing your connection…'));
  try {
    const data = await api('/api/integrations/hosted/connect', {method:'POST', body:JSON.stringify({slug:row.slug}), timeoutMs:60000});
    if (epoch !== _hubEpoch) { if (popup) popup.close(); return; }
    if (data.connect_url && _intgSafeDocsUrl(data.connect_url).startsWith('https://')) {
      if (popup) popup.location.href = data.connect_url;
      const status = $('hostedActionStatus'); status.replaceChildren();
      const link = _hubNode('a', 'sm-btn', _hubText('integrations_finish_connect', 'Finish connecting your account'));
      link.href = data.connect_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; status.append(link);
      let polls = 0;
      const poll = async () => {
        if (epoch !== _hubEpoch) return;
        _hostedPoll = null;
        // OAuth normally moves focus to another tab; keep a timer until this
        // document is visible again without spending its refresh budget.
        if (document.hidden) { _hostedPoll = setTimeout(poll, 5000); return; }
        if (++polls > 24) return;
        await _loadHostedAccounts(epoch);
        if (epoch !== _hubEpoch || (popup && popup.closed)) return;
        _hostedPoll = setTimeout(poll, 5000);
      };
      clearTimeout(_hostedPoll); _hostedPoll = setTimeout(poll, 5000);
    } else {
      if (popup) popup.close();
      _hubStatus('hostedActionStatus', data.message || (data.status === 'active'
        ? _hubText('integrations_connected', 'Connected') : _hubText('integrations_pending', 'Waiting for administrator approval.')));
      await _loadHostedAccounts(epoch);
    }
  } catch (error) {
    if (popup) popup.close();
    if (epoch === _hubEpoch) _hubStatus('hostedActionStatus', error.message);
  } finally { button.disabled = false; }
}

function renderIntegrationPlugins() {
  if (!_pluginInventory) return;
  const query = $('pluginCatalogSearch').value.trim().toLowerCase();
  const installedView = $('pluginCatalogFilter').value === 'installed';
  const installed = _pluginInventory.installed || [];
  const rows = (installedView ? installed : _pluginInventory.catalog || []).filter(row =>
    [row.title, row.name, row.description, row.category].join(' ').toLowerCase().includes(query));
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const card = _hubNode('article', 'intg-hub-card');
    card.append(_hubNode('h3', '', row.title || row.name),
      _hubNode('span', 'intg-muted', installedView ? row.status : [row.tier, row.category].filter(Boolean).join(' · ')),
      _hubNode('p', '', row.description || ''));
    if (row.docs_url && _intgSafeDocsUrl(row.docs_url)) {
      const link = _hubNode('a', '', _hubText('integrations_plugin_details', 'Details'));
      link.href = row.docs_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link);
    }
    const exists = installed.some(item => item.name === row.name || item.key === row.name);
    if (_pluginInventory.can_manage && (installedView || !exists)) {
      const action = installedView ? 'toggle' : 'install';
      const label = installedView ? (row.enabled ? _hubText('disable', 'Disable') : _hubText('enable', 'Enable')) : _hubText('install', 'Install');
      card.append(_hubButton(label, event => _changeIntegrationPlugin(row, action, event.currentTarget)));
    } else if (!installedView && exists) card.append(_hubNode('span', 'intg-muted', _hubText('settings_extensions_installed_tab', 'Installed')));
    fragment.append(card);
  }
  $('pluginCatalogEmpty').hidden = rows.length > 0;
  $('pluginCatalogList').replaceChildren(fragment);
}

async function _changeIntegrationPlugin(row, action, button) {
  const label = row.title || row.name;
  if (action === 'install' && !confirm(_hubText('integrations_plugin_confirm', 'Install this plugin for the selected bot profile?') + '\n\n' + label + ' · ' + row.tier)) return;
  const epoch = _hubEpoch;
  button.disabled = true; _hubBusy('pluginActionStatus');
  try {
    await api('/api/plugins/' + action, {method:'POST', body:JSON.stringify({name:action === 'install' ? row.name : row.key, enabled:!row.enabled}), timeoutMs:180000});
    if (epoch !== _hubEpoch) return;
    _hubStatus('pluginActionStatus', _hubText('integrations_plugin_saved', 'Saved. Start a new conversation to load the changes; some plugins require a service restart.'));
    await loadIntegrationTab();
  } catch (error) { if (epoch === _hubEpoch) _hubStatus('pluginActionStatus', error.message); }
  finally { button.disabled = false; }
}

document.addEventListener('click', event => {
  const connect = event.target.closest('[data-hosted-connect]');
  if (connect) _connectHosted({slug:connect.dataset.hostedConnect}, connect);
  const disconnect = event.target.closest('[data-hosted-disconnect]');
  if (disconnect) _disconnectHosted(disconnect);
});
async function _disconnectHosted(button) {
  if (!confirm(_hubText('integrations_disconnect_confirm', 'Disconnect this account?'))) return;
  button.disabled = true;
  try {
    await api('/api/integrations/hosted/disconnect', {method:'POST', body:JSON.stringify({connection_id:button.dataset.hostedDisconnect}), timeoutMs:60000});
    await _loadHostedAccounts();
  } catch (error) { _hubStatus('hostedActionStatus', error.message); button.disabled = false; }
}

async function openIntegrationPlugins() {
  _integrationTab = 'plugins';
  await switchPanel('integrations');
  await switchIntegrationTab('plugins');
}
