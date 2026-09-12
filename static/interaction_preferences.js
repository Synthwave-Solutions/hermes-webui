/* Personal clarification defaults and an explicit conversation override. */
let _interactionPreferenceState = null;
let _interactionPreferenceRequest = 0;

function _interactionSid() {
  return S.session && S.session.session_id || null;
}

function _interactionStatus(message) {
  $('interactionStatus').textContent = message;
}

function _interactionDisable(disabled) {
  $('interactionUserMode').disabled = disabled;
  $('interactionTaskMode').disabled = disabled || !_interactionPreferenceState || !_interactionPreferenceState.session_id;
  $('interactionSave').disabled = disabled;
}

function _interactionRender(data) {
  _interactionPreferenceState = data;
  $('interactionUserMode').value = data.user_mode;
  $('interactionTaskMode').value = data.task_mode || '';
  $('interactionScope').textContent = data.session_id
    ? 'The conversation choice applies only to you in the conversation selected when these preferences loaded. Choose “Use my default” to remove its override.'
    : 'Open a conversation to set a choice for that conversation.';
  _interactionDisable(false);
}

async function loadInteractionPreferences() {
  const request = ++_interactionPreferenceRequest;
  const sid = _interactionSid();
  _interactionPreferenceState = null;
  _interactionDisable(true);
  _interactionStatus('Loading clarification preferences…');
  try {
    const data = await api('/api/interaction/preferences' + (sid ? '?session_id=' + encodeURIComponent(sid) : ''));
    if (request !== _interactionPreferenceRequest) return;
    if (_interactionSid() !== sid) {
      _interactionStatus('The conversation changed. Reload preferences before editing.');
      return;
    }
    _interactionRender(data);
    _interactionStatus('Saved style: ' + (data.effective_mode === 'minimal' ? 'Fewer questions' : 'Balanced') + '. Changes apply from your next message.');
  } catch (error) {
    if (request !== _interactionPreferenceRequest) return;
    _interactionStatus(error.message || 'Preferences could not be loaded. Please retry.');
  }
}

async function saveInteractionPreferences() {
  const saved = _interactionPreferenceState;
  if (!saved) return;
  if (_interactionSid() !== saved.session_id) {
    _interactionDisable(true);
    _interactionStatus('The conversation changed. Reload preferences before saving.');
    return;
  }
  const request = ++_interactionPreferenceRequest;
  const body = {revision: saved.revision, user_mode: $('interactionUserMode').value,
    session_id: saved.session_id, task_mode: $('interactionTaskMode').value || null};
  _interactionDisable(true);
  _interactionStatus('Saving clarification preferences…');
  try {
    const data = await api('/api/interaction/preferences', {method: 'POST', body: JSON.stringify(body)});
    if (request !== _interactionPreferenceRequest) return;
    if (_interactionSid() !== saved.session_id) {
      _interactionPreferenceState = null;
      _interactionStatus('Saved for the previously selected conversation. Reload to edit this conversation.');
      return;
    }
    _interactionRender(data);
    _interactionStatus('Saved. Changes apply from your next message; start a new voice call to use them in voice.');
  } catch (error) {
    if (request !== _interactionPreferenceRequest) return;
    // A timeout may have committed on the server. Reload before another write.
    _interactionPreferenceState = null;
    _interactionStatus((error.message || 'Saving failed.') + ' Reload saved preferences before trying again.');
  }
}

$('interactionSave').addEventListener('click', saveInteractionPreferences);
$('interactionReload').addEventListener('click', loadInteractionPreferences);
