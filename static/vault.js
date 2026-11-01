// Secrets only travel through the authenticated settings API. No chat, storage,
// toast payloads or console logging; forms are cleared before the request starts.
let _vaultEpoch = 0;
let _vaultSources = [];
let _vaultItems = [];
const _vaultT = (key, fallback) => _hubText('vault_' + key, fallback);

async function loadVault() {
  const epoch = ++_vaultEpoch;
  _hubBusy('vaultStatus');
  try {
    const data = await api('/api/vault/status', {timeoutMs:15000, timeoutToast:false});
    if (epoch !== _vaultEpoch || _integrationTab !== 'vault') return;
    _vaultSources = data.sources || []; _vaultItems = data.items || [];
    renderVault(); _hubStatus('vaultStatus', '');
  } catch (_) { if (epoch === _vaultEpoch) _hubStatus('vaultStatus', _vaultT('load_error', 'Could not load your vault. Refresh to retry.')); }
}

function renderVault() {
  const fragment = document.createDocumentFragment();
  for (const source of _vaultSources) {
    const card = _hubNode('article', 'intg-hub-card');
    const state = !source.installed ? _vaultT('not_installed', 'Server setup required')
      : source.name === 'local' ? _vaultT('active', 'Ready to use')
      : !source.configured ? _vaultT('not_connected', 'Not connected')
      : !source.enabled ? _vaultT('disabled', 'Disabled')
      : source.unlocked ? _vaultT('unlocked', 'Available') : _vaultT('locked', 'Locked');
    card.append(_hubNode('h3', '', source.display_name), _hubNode('span', 'intg-badge', state),
      _hubNode('p', 'intg-muted', source.name === 'local' ? _vaultT('local_hint', 'Built-in encrypted vault. Always available for your account.')
        : source.name === 'onepassword' ? _vaultT('op_hint', 'Connect selected vaults using a 1Password service account.')
        : _vaultT('bw_hint', 'Connect your personal account. Unlock with your master password when needed.')));
    const actions = _hubNode('div', 'intg-hub-actions');
    if (source.name === 'local') actions.append(_hubButton(_vaultT('add', 'Add login'), openVaultLogin));
    else if (!source.configured) {
      const button = _hubButton(_vaultT('connect', 'Connect'), () => openVaultManager(source));
      button.disabled = !source.installed; actions.append(button);
    } else {
      if (source.enabled && source.name === 'bitwarden') actions.append(_hubButton(
        source.unlocked ? _vaultT('lock', 'Lock') : _vaultT('unlock', 'Unlock'), event => source.unlocked
          ? vaultAction('lock', {name:source.name}, event.currentTarget) : openVaultUnlock()));
      if (source.enabled && source.unlocked) actions.append(_hubButton(_vaultT('view_logins', 'View logins'), event => vaultListManager(source, event.currentTarget)));
      actions.append(_hubButton(source.enabled ? _vaultT('disable', 'Disable') : _vaultT('enable', 'Enable'), event =>
        vaultAction('configure', {name:source.name, enabled:!source.enabled}, event.currentTarget)));
      actions.append(_hubButton(_vaultT('disconnect', 'Disconnect'), event => {
        if (confirm(_vaultT('disconnect_confirm', 'Disconnect this password manager from your account?'))) vaultAction('disconnect', {name:source.name}, event.currentTarget);
      }));
    }
    card.append(actions); fragment.append(card);
  }
  $('vaultSources').replaceChildren(fragment);
  renderVaultItems(_vaultItems, true);
}

function renderVaultItems(items, local) {
  const fragment = document.createDocumentFragment();
  if (!items.length) fragment.append(_hubNode('p', 'intg-muted', _vaultT('empty', 'No saved logins yet.')));
  for (const item of items) {
    const row = _hubNode('article', 'vault-login');
    const info = _hubNode('div', '');
    info.append(_hubNode('strong', '', item.label), _hubNode('p', 'intg-muted', [item.origin, item.identifier].filter(Boolean).join(' · ')));
    if (item.has_otp) info.append(_hubNode('span', 'intg-badge', _vaultT('totp_badge', 'Automatic 2FA')));
    row.append(info);
    if (local) row.append(_hubButton(_vaultT('remove', 'Remove'), event => {
      if (confirm(_vaultT('remove_confirm', 'Remove this saved login?'))) vaultAction('remove', {id:item.id}, event.currentTarget);
    }));
    fragment.append(row);
  }
  $('vaultItems').replaceChildren(fragment);
}

async function vaultAction(action, body, button) {
  if (button) button.disabled = true;
  _hubBusy('vaultStatus');
  try {
    const result = await api('/api/vault/' + action, {method:'POST', body:JSON.stringify(body), timeoutMs:100000, timeoutToast:false});
    await loadVault();
    _hubStatus('vaultStatus', result.remote_logout === false
      ? _vaultT('logout_incomplete', 'Access is disabled here. Bitwarden could not finish signing out; retry disconnecting to clear its local session.')
      : _vaultT('saved', 'Saved.'));
    return true;
  } catch (_) {
    _hubStatus('vaultStatus', _vaultT('action_error', 'Could not complete this action. Check your details and try again.'));
    return false;
  } finally { if (button) button.disabled = false; }
}

async function vaultListManager(source, button) {
  const epoch = _vaultEpoch;
  button.disabled = true; _hubBusy('vaultStatus');
  try {
    const data = await api('/api/vault/items', {method:'POST', body:JSON.stringify({name:source.name}), timeoutMs:45000, timeoutToast:false});
    if (epoch !== _vaultEpoch || _integrationTab !== 'vault') return;
    renderVaultItems(data.items || [], false);
    _hubStatus('vaultStatus', source.display_name);
  } catch (_) { _hubStatus('vaultStatus', _vaultT('load_error', 'Could not load your vault. Refresh to retry.')); }
  finally { button.disabled = false; }
}

function _vaultDialog(title, description, fields, submit) {
  document.getElementById('vaultDialog')?.close();
  const dialog = _hubNode('dialog', 'vault-dialog'); dialog.id = 'vaultDialog';
  dialog.setAttribute('aria-labelledby', 'vaultDialogTitle');
  dialog.setAttribute('aria-describedby', 'vaultDialogHint');
  const heading = _hubNode('h2', '', title); heading.id = 'vaultDialogTitle';
  const hint = _hubNode('p', 'intg-muted', description); hint.id = 'vaultDialogHint';
  const form = _hubNode('form', ''); form.autocomplete = 'off';
  dialog.append(heading, hint, form);
  for (const field of fields) {
    const label = _hubNode('label', 'vault-field', field.label);
    const input = _hubNode(field.options ? 'select' : 'input', '');
    input.name = field.name; input.required = !field.optional;
    if (field.options) for (const [value, text] of field.options) {
      const option = _hubNode('option', '', text); option.value = value; input.append(option);
    } else {
      input.type = field.type || 'text'; input.autocomplete = input.type === 'password' ? 'new-password' : 'off';
      input.maxLength = field.maxLength || 4096; input.spellcheck = false;
      if (field.placeholder) input.placeholder = field.placeholder;
    }
    label.append(input); form.append(label);
  }
  const message = _hubNode('p', '', ''); message.setAttribute('role', 'status');
  const actions = _hubNode('div', 'intg-hub-actions');
  const save = _hubNode('button', 'sm-btn primary', _vaultT('save', 'Save')); save.type = 'submit';
  actions.append(_hubButton(_vaultT('close', 'Close'), () => dialog.close()), save);
  form.append(message, actions);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    form.reset(); save.disabled = true;
    message.textContent = _hubText('loading', 'Loading…');
    const ok = await submit(values);
    // Drop references to secrets promptly; never retain them to refill a form.
    for (const key of Object.keys(values)) values[key] = '';
    if (ok) dialog.close();
    else { save.disabled = false; message.textContent = _vaultT('action_error', 'Could not complete this action. Check your details and try again.'); }
  });
  dialog.addEventListener('close', () => { form.reset(); dialog.remove(); }, {once:true});
  document.body.append(dialog); dialog.showModal();
}

function openVaultLogin() {
  _vaultDialog(_vaultT('add', 'Add login'), _vaultT('add_hint', 'The password can only be filled on this exact website.'), [
    {name:'label', label:_vaultT('label', 'Name'), maxLength:200},
    {name:'origin', label:_vaultT('website', 'Website'), type:'url', placeholder:'https://example.com'},
    {name:'identifier', label:_vaultT('username', 'Email or username'), maxLength:320},
    {name:'password', label:_vaultT('password', 'Password'), type:'password'},
    {name:'otp_secret', label:_vaultT('totp', 'Authenticator setup key (optional)'), type:'password', optional:true}
  ], values => vaultAction('add', {label:values.label, origin:values.origin,
    secret:{identifier_type:'username', identifier:values.identifier, password:values.password, ...(values.otp_secret ? {otp_secret:values.otp_secret} : {})}}));
}

function openVaultManager(source) {
  const op = source.name === 'onepassword';
  _vaultDialog(_vaultT('connect', 'Connect') + ' ' + source.display_name,
    op ? _vaultT('op_setup', 'Create a service account in 1Password with access to the vaults you want to use. Paste its token here. It is stored encrypted for your account.')
      : _vaultT('bw_setup', 'Find your personal API key under Settings → Security → Keys in Bitwarden. After connecting, unlock with your master password. It is never saved.'),
    op ? [{name:'service_account_token', label:_vaultT('op_token', 'Service account token'), type:'password', maxLength:8192}] : [
      {name:'server', label:_vaultT('region', 'Region'), options:[['https://vault.bitwarden.eu','EU'], ['https://vault.bitwarden.com','US']]},
      {name:'client_id', label:_vaultT('bw_id', 'Client ID'), placeholder:'user.…', maxLength:120},
      {name:'client_secret', label:_vaultT('bw_secret', 'Client secret'), type:'password'}
    ], values => vaultAction('configure', {name:source.name, ...values}));
}

function openVaultUnlock() {
  _vaultDialog(_vaultT('unlock', 'Unlock') + ' Bitwarden', _vaultT('unlock_hint', 'Unlocks for this account until you lock it, the service restarts, or it is idle for 30 minutes.'), [
    {name:'password', label:_vaultT('master_password', 'Master password'), type:'password'}
  ], values => vaultAction('unlock', {name:'bitwarden', password:values.password}));
}
