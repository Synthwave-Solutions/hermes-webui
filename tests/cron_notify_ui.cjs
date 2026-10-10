// Behaviour harness for the scheduled task notification UI (plan 3.1, W2).
// Pure JavaScript: the production functions are cut out of static/panels.js
// and run in a vm context with a stubbed api() and a minimal fake DOM, so no
// browser, server or engine is involved. Run: node tests/cron_notify_ui.cjs
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const SRC = fs.readFileSync(path.join(ROOT, 'static/panels.js'), 'utf8');
const EN = fs.readFileSync(path.join(ROOT, 'static/i18n/en.js'), 'utf8');

function block(start, end) {
  const from = SRC.indexOf(start);
  if (from < 0) throw new Error('missing ' + start);
  const to = SRC.indexOf(end, from);
  if (to < 0) throw new Error('missing ' + end);
  return SRC.slice(from, to);
}
function fn(name) {
  const marker = new RegExp('(async\\s+)?function\\s+' + name + '\\s*\\(');
  const match = marker.exec(SRC);
  if (!match) throw new Error('missing function ' + name);
  let i = SRC.indexOf('{', SRC.indexOf(')', match.index));
  let depth = 0;
  for (; i < SRC.length; i++) {
    if (SRC[i] === '{') depth++;
    else if (SRC[i] === '}' && --depth === 0) return SRC.slice(match.index, i + 1);
  }
  throw new Error('unterminated ' + name);
}

// English values of the keys the UI uses, read from the locale file so the
// assertions see what a person sees.
function english(key) {
  const m = new RegExp('\\n\\s*' + key + ":\\s*'((?:[^'\\\\]|\\\\.)*)'").exec(EN);
  if (!m) throw new Error('missing i18n key ' + key);
  return m[1].replace(/\\'/g, "'");
}
const KEYS = ['cron_notify_legend', 'cron_notify_me_label', 'cron_notify_me_all', 'cron_notify_me_failures',
  'cron_notify_me_never', 'cron_notify_me_off_admin', 'cron_notify_delivery_failures_only',
  'cron_notify_delivery_off_notice', 'cron_notify_hint', 'cron_notify_hint_managed',
  'cron_notify_delivery_off_warning', 'cron_notify_chip_change', 'cron_notify_mute_for_me',
  'cron_notify_unmute_for_me', 'cron_notify_muted', 'cron_notify_saved', 'cron_notify_conflict',
  'cancel', 'save', 'error_prefix'];
const STRINGS = Object.fromEntries([...KEYS, 'status_failed', 'status_completed'].map(k => [k, english(k)]));

class FakeEl {
  constructor(id, props = {}) {
    Object.assign(this, { id, value: '', checked: false, disabled: false, hidden: false, innerHTML: '',
      textContent: '', dataset: {}, style: {}, listeners: {}, children: [], className: '' }, props);
  }
  addEventListener(type, cb) { (this.listeners[type] = this.listeners[type] || []).push(cb); }
  removeEventListener() {}
  fire(type) { (this.listeners[type] || []).forEach(cb => cb({ target: this })); }
  closest(selector) { return this.parents ? this.parents[selector] || null : null; }
  focus() {}
  remove() { this.removed = true; }
  appendChild(child) { this.children.push(child); return child; }
  prepend(child) { this.children.unshift(child); }
  querySelector(selector) {
    const m = /option\[value="([^"]*)"\]/.exec(selector);
    if (m) return this.children.find(c => c.value === m[1]) || null;
    if (selector.startsWith('#') && this.byId) return this.byId[selector.slice(1)] || null;
    return null;
  }
  querySelectorAll() { return []; }
}

function scene(opts = {}) {
  const els = {};
  const calls = { api: [], toasts: [], desktop: [], badge: 0, marks: [], loads: 0, details: [], skills: 0 };
  const ctx = {
    console, Promise, Set, Map, JSON, Object, Array, String, Number, Math, RegExp, Error, Date, setTimeout,
    CSS: { escape: v => String(v) },
    window: { __GOV_ME__: opts.me },
    document: { hidden: false, body: new FakeEl('body'), addEventListener() {}, removeEventListener() {},
      createElement: tag => new FakeEl(tag), activeElement: null },
    els, calls,
    $: id => els[id] || null,
    esc: s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])),
    t: (key, ...args) => (key === 'cron_completion_status' ? `Cron "${args[0]}" ${args[1]}` : (STRINGS[key] || key)),
    showToast: (...args) => calls.toasts.push(args),
    sendBrowserNotification: (...args) => calls.desktop.push(args),
    updateCronBadge: () => { calls.badge++; },
    _markSessionCompletionUnreadIfBackground: (...args) => calls.marks.push(args),
    loadCrons: async () => { calls.loads++; },
    openCronDetail: job => calls.details.push(job),
    _modelStateForSelect: (_el, value) => ({ model: value, model_provider: null }),
    _canUseFeature: permission => !!(opts.features || {})[permission],
    _renderCronSkillTags: () => {},
    _bindCronSkillPicker: () => { calls.skills++; },
    setInterval: cb => { ctx.__tick = cb; return 1; },
    S: { activeProfile: 'default' },
  };
  ctx.api = async (url, options) => {
    const body = options && options.body ? JSON.parse(options.body) : null;
    calls.api.push({ url, method: (options && options.method) || 'GET', body });
    const handler = (opts.routes || {})[url];
    if (typeof handler === 'function') return handler(body, options);
    if (handler !== undefined) return JSON.parse(JSON.stringify(handler));
    return { ok: true };
  };
  vm.createContext(ctx);
  vm.runInContext(`
    var _cronList = null, _currentCronDetail = null, _cronMode = 'empty', _cronIsDuplicate = false;
    var _editingCronId = null, _cronPreFormDetail = null, _cronSelectedSkills = [], _cronSkillsCache = null;
    var _cronNotifySupported = false, _cronNotifyRevision = null, _cronNotifyMine = {};
    var _cronFormNotifyBase = null, _cronNotifyOverlay = null;
    var _cronPollSince = 10, _cronPollTimer = null, _cronUnreadCount = 0, _cronPollGeneration = 0;
    var _cronNewJobIds = new Set();
    var _cronDeliveryOptionsCache = null;
  `, ctx);
  vm.runInContext(block('// ── Scheduled task notifications (plan 3.1)', '// ── End of scheduled task notifications'), ctx);
  for (const name of ['_cronIsCronAdmin', '_cronCanEdit', '_cronCanCreate', '_cronModelBareName', 'saveCronForm', 'startCronPolling', '_setCronHeaderButtons',
    '_populateCronDeliverOptions', 'duplicateCurrentCron', '_cronEditableSchedule']) {
    vm.runInContext(fn(name), ctx);
  }
  ctx.run = code => vm.runInContext(code, ctx);
  return ctx;
}

const OWNER = 'owner@example.com';
const SHAREE = 'sharee@example.com';
const governed = email => ({ email, mode: 'enforce', method: 'oidc', permissions: ['cron:read', 'cron:write'], feature_permissions: { 'cron:write': true } });

const tests = [];
const test = (name, body) => tests.push([name, body]);

test('levels resolve like the notify policy, legacy jobs unchanged', () => {
  const x = scene();
  assert.deepEqual({ ...x._cronNotifyOf({}) }, { in_app: 'all', delivery: 'all', source: 'legacy' });
  assert.deepEqual({ ...x._cronNotifyOf({ toast_notifications: false }) }, { in_app: 'quiet', delivery: 'all', source: 'legacy' });
  assert.deepEqual({ ...x._cronNotifyOf({ notify: { in_app: 'failures', delivery: 'failures' }, notify_source: 'explicit' }) },
    { in_app: 'failures', delivery: 'failures', source: 'explicit' });
  assert.deepEqual({ ...x._cronNotifyOf({ notify: { in_app: 'loud', delivery: 'never' }, toast_notifications: false }) },
    { in_app: 'quiet', delivery: 'all', source: 'explicit' });
  assert.equal(x._cronNotifyOf({ notify: { in_app: 'off', delivery: 'off' } }).in_app, 'off');
  assert.deepEqual({ ...x._cronDefaultNotify('Monitoring') }, { in_app: 'failures', delivery: 'all' });
  assert.deepEqual({ ...x._cronDefaultNotify('Finance') }, { in_app: 'all', delivery: 'all' });
  assert.equal(x._cronLegacyToast('all'), true);
  assert.equal(x._cronLegacyToast('failures'), true);
  assert.equal(x._cronLegacyToast('quiet'), false);
  assert.equal(x._cronLegacyToast('off'), false);
});

test('a personal level only lowers the task level', () => {
  const x = scene();
  assert.equal(x._cronEffectiveInApp({ notify: { in_app: 'all', delivery: 'all' }, my_notify: 'quiet' }), 'quiet');
  assert.equal(x._cronEffectiveInApp({ notify: { in_app: 'quiet', delivery: 'all' }, my_notify: 'all' }), 'quiet');
  assert.equal(x._cronEffectiveInApp({ notify: { in_app: 'failures', delivery: 'all' }, my_notify: { in_app: 'quiet' } }), 'quiet');
  assert.equal(x._cronEffectiveInApp({ id: 'j', notify: { in_app: 'all', delivery: 'all' } }), 'all');
  x._cronNotifyMine = { j: 'quiet' };
  assert.equal(x._cronEffectiveInApp({ id: 'j', notify: { in_app: 'all', delivery: 'all' } }), 'quiet');
  assert.equal(x._cronNotifyMutedForMe({ id: 'j' }), true);
  // The per-request my_notify wins over the separately loaded map.
  assert.equal(x._cronNotifyMutedForMe({ id: 'j', my_notify: null }), false);
  assert.deepEqual({ ...x._cronNotifyMineFromPayload({ a: 'quiet', b: { in_app: 'failures' }, c: 'bogus' }) }, { a: 'quiet', b: 'failures' });
  assert.deepEqual({ ...x._cronNotifyMineFromPayload([{ job_id: 'a', in_app: 'quiet' }, { id: 'b', in_app: 'all' }]) }, { a: 'quiet', b: 'all' });
});

test('who may change a task: the server flag, the owner, cron admins, never a sharee', () => {
  const job = { id: 'j', owner_email: OWNER, origin: { platform: 'webui', user_id: OWNER } };
  assert.equal(scene()._cronCanEdit(job), true, 'without an identity the server stays the gate');
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit(job), true);
  assert.equal(scene({ me: governed(SHAREE) })._cronCanEdit({ ...job, shared_with: [SHAREE] }), false);
  assert.equal(scene({ me: governed(SHAREE) })._cronCanEdit({ ...job, can_edit: true }), true, 'server flag wins');
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ ...job, can_edit: false }), false, 'server flag wins');
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ ...job, read_only: true }), false);
  assert.equal(scene({ me: { ...governed(SHAREE), feature_permissions: { 'cron:admin': true } } })._cronCanEdit(job), true);
  assert.equal(scene({ me: { ...governed(SHAREE), feature_permissions: {}, permissions: ['*'] } })._cronCanEdit(job), true);
  assert.equal(scene({ me: { ...governed(SHAREE), mode: 'report_only' } })._cronCanEdit(job), true);
  assert.equal(scene({ me: { ...governed(SHAREE), mode: 'off' } })._cronCanEdit(job), true);
  assert.equal(scene({ me: { email: '', method: 'auth_disabled' } })._cronCanEdit(job), true);
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ id: 'x', origin: { platform: 'webui', user_id: OWNER } }), true);
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ id: 'x', origin: { platform: 'webui', chat_id: 'c1' } }), true, 'conversation owner is checked by the server');
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ id: 'x', origin: { platform: 'telegram' } }), false);
  assert.equal(scene({ me: governed(OWNER) })._cronCanEdit({ id: 'x', owner_email: SHAREE, origin: { platform: 'webui', user_id: OWNER } }), false, 'owner_email decides alone');
});

test('a sharee sees no Run, Pause, Resume, Edit, Share or Delete, but may duplicate', () => {
  const buttons = ['btnRunTaskDetail', 'btnPauseTaskDetail', 'btnResumeTaskDetail', 'btnEditTaskDetail', 'btnShareTaskDetail',
    'btnDuplicateTaskDetail', 'btnDeleteTaskDetail', 'btnCancelTaskDetail', 'btnSaveTaskDetail'];
  const render = (me, job) => {
    const x = scene({ me, features: { 'cron:write': true } });
    for (const id of buttons) x.els[id] = new FakeEl(id, { style: { display: 'none' } });
    x.els.mainTasks = new FakeEl('mainTasks', { querySelector: () => new FakeEl('header') });
    x.run('function _cronStatusMeta(){ return { state: "active" }; }');
    x._setCronHeaderButtons('read', job);
    return Object.fromEntries(buttons.map(id => [id.replace(/^btn|TaskDetail$/g, ''), x.els[id].style.display !== 'none']));
  };
  const job = { id: 'j', owner_email: OWNER, state: 'scheduled' };
  assert.deepEqual(render(governed(SHAREE), job), { Run: false, Pause: false, Resume: false, Edit: false, Share: false, Duplicate: true, Delete: false, Cancel: false, Save: false });
  assert.deepEqual(render(governed(OWNER), job), { Run: true, Pause: true, Resume: false, Edit: true, Share: true, Duplicate: true, Delete: true, Cancel: false, Save: false });
});

test('form controls: Notify me, Off (admin setting), Only send when it fails and the warning', () => {
  const x = scene();
  let html = x._cronNotifyInAppSelectHtml({ in_app: 'all', delivery: 'all' }, 'cronFormNotifyInApp');
  assert.match(html, /<label for="cronFormNotifyInApp">Notify me<\/label>/);
  assert.deepEqual([...html.matchAll(/<option value="(\w+)"[^>]*>([^<]*)</g)].map(m => [m[1], m[2]]), [['all', 'Every run'], ['quiet', 'Never']],
    'before the backend serves notify only the two legacy levels are offered');
  x._cronNotifySupported = true;
  html = x._cronNotifyInAppSelectHtml({ in_app: 'failures', delivery: 'all' }, 'cronFormNotifyInApp');
  assert.deepEqual([...html.matchAll(/<option value="(\w+)"[^>]*>([^<]*)</g)].map(m => [m[1], m[2]]), [['all', 'Every run'], ['failures', 'Only failures'], ['quiet', 'Never']]);
  assert.match(html, /<option value="failures" selected>/);
  html = x._cronNotifyInAppSelectHtml({ in_app: 'off', delivery: 'all' }, 'cronFormNotifyInApp');
  assert.match(html, /<select id="cronFormNotifyInApp" disabled data-level="off"><option value="off" selected>Off \(admin setting\)<\/option><\/select>/);

  html = x._cronNotifyDeliveryHtml({ in_app: 'all', delivery: 'failures' }, 'box', 'telegram');
  assert.match(html, /<input type="checkbox" id="box" checked><span>Only send when it fails<\/span>/);
  assert.doesNotMatch(html, / hidden/);
  assert.match(x._cronNotifyDeliveryHtml({ in_app: 'all', delivery: 'all' }, 'box', 'local'), /for="box" hidden>/);
  html = x._cronNotifyDeliveryHtml({ in_app: 'all', delivery: 'off' }, 'box', 'telegram');
  assert.ok(html.includes('Delivery is off for this task.'));
  assert.ok(html.includes('The messages of this task are its output. With delivery off, nobody receives them.'));
  assert.doesNotMatch(html, /checkbox/);
  x._cronNotifySupported = false;
  assert.equal(x._cronNotifyDeliveryHtml({ in_app: 'all', delivery: 'failures' }, 'box', 'telegram'), '');

  html = x._cronNotifyFieldsetHtml({ in_app: 'all', delivery: 'all' }, true);
  assert.match(html, /<fieldset class="detail-form-row cron-notify-fieldset" data-tour="tasks-notify">/);
  assert.match(html, /<legend>Notifications<\/legend>/);
  assert.ok(html.includes('Output is always saved in Scheduled tasks.'));
  assert.ok(html.includes('Synthwave support is notified when this fails.'));
  assert.ok(!x._cronNotifyFieldsetHtml({ in_app: 'all', delivery: 'all' }, false).includes('Synthwave support'));
});

test('detail row, bell chip and muted bell', () => {
  const x = scene({ me: governed(SHAREE) });
  x._cronNotifySupported = true;
  const owned = { id: 'j', owner_email: SHAREE, deliver: 'telegram', notify: { in_app: 'failures', delivery: 'failures' }, support_notified: true };
  let row = x._cronNotifyDetailRowHtml(owned);
  assert.ok(row.includes('>Notifications<') && row.includes('>Only failures<') && row.includes('>Only send when it fails<'));
  assert.ok(row.includes('Synthwave support is notified when this fails.'));
  row = x._cronNotifyDetailRowHtml({ id: 'k', notify: { in_app: 'off', delivery: 'off' }, my_notify: 'quiet' });
  assert.ok(row.includes('>Off (admin setting)<') && row.includes('Delivery is off for this task.') && row.includes('Muted'));
  assert.ok(!row.includes('Synthwave support'));

  let chip = x._cronNotifyMetaHtml(owned);
  assert.match(chip, /data-tour="tasks-notify"/);
  assert.match(chip, /onclick="openCronNotifyPopover\('j'\)">Change<\/button>/);
  const shared = { id: 's', owner_email: OWNER, shared_with: [SHAREE], notify: { in_app: 'all', delivery: 'all' } };
  chip = x._cronNotifyMetaHtml(shared);
  assert.match(chip, /onclick="toggleCronNotifyMute\('s'\)">Mute for me<\/button>/);
  assert.doesNotMatch(chip, /openCronNotifyPopover/);
  chip = x._cronNotifyMetaHtml({ ...shared, my_notify: 'quiet' });
  assert.match(chip, />Unmute for me<\/button>/);
  assert.match(chip, /is-muted/);
  assert.doesNotMatch(x._cronNotifyMetaHtml({ ...shared, read_only: true }), /<button/);
  x._cronNotifySupported = false;
  assert.doesNotMatch(x._cronNotifyMetaHtml(shared), /<button/, 'no personal mute before the backend serves it');

  assert.equal(x._cronNotifyListIconHtml({ id: 'a', notify: { in_app: 'all', delivery: 'all' } }), '');
  assert.match(x._cronNotifyListIconHtml({ id: 'a', notify: { in_app: 'all', delivery: 'all' }, my_notify: 'quiet' }), /cron-notify-muted-icon" title="Muted"/);
  assert.match(x._cronNotifyListIconHtml({ id: 'b', toast_notifications: false }), /cron-notify-muted-icon/);
});

function formScene(opts) {
  const x = scene(opts);
  const el = (id, props) => { x.els[id] = new FakeEl(id, props); return x.els[id]; };
  el('cronFormName', { value: 'Morning report' });
  el('cronFormSchedule', { value: '0 9 * * *' });
  el('cronFormPrompt', { value: 'Summarise the inbox' });
  el('cronFormDeliver', { value: 'telegram' });
  el('cronFormProfile', { value: '' });
  el('cronFormDiagram', { value: '' });
  el('cronFormEmoji', { value: '' });
  el('cronFormCategory', { value: '' });
  el('cronFormError', { style: {} });
  el('cronFormModel', { value: '', dataset: { loaded: '1' } });
  el('cronFormNotifyInApp', { value: 'all' });
  el('cronFormNotifyDeliveryFailures', { checked: false });
  return x;
}

test('saveCronForm: a new task sends notify and toast_notifications', async () => {
  const x = formScene({ routes: { '/api/crons/create': { id: 'new' } } });
  x._cronNotifySupported = true;
  x._cronFormNotifyBase = { in_app: 'all', delivery: 'all' };
  x.els.cronFormNotifyInApp.value = 'failures';
  x.els.cronFormNotifyDeliveryFailures.checked = true;
  await x.saveCronForm();
  const post = x.calls.api.find(c => c.url === '/api/crons/create');
  assert.deepEqual(post.body.notify, { in_app: 'failures', delivery: 'failures' });
  assert.equal(post.body.toast_notifications, true);

  const legacy = formScene({ routes: { '/api/crons/create': { id: 'new' } } });
  legacy._cronFormNotifyBase = { in_app: 'all', delivery: 'all' };
  legacy.els.cronFormNotifyInApp.value = 'quiet';
  delete legacy.els.cronFormNotifyDeliveryFailures;
  await legacy.saveCronForm();
  const legacyPost = legacy.calls.api.find(c => c.url === '/api/crons/create');
  assert.equal('notify' in legacyPost.body, false, 'a backend without notify never receives it');
  assert.equal(legacyPost.body.toast_notifications, false);
});

test('saveCronForm: an edit writes notify only when a level changed', async () => {
  const x = formScene();
  x._cronNotifySupported = true;
  x._editingCronId = 'job1';
  x._cronFormNotifyBase = { in_app: 'quiet', delivery: 'all' };
  x.els.cronFormNotifyInApp.value = 'quiet';
  await x.saveCronForm();
  let post = x.calls.api.find(c => c.url === '/api/crons/update');
  assert.equal('notify' in post.body, false, 'an untouched task keeps its stored notify');
  assert.equal(post.body.toast_notifications, false);

  const y = formScene();
  y._cronNotifySupported = true;
  y._editingCronId = 'job1';
  y._cronFormNotifyBase = { in_app: 'all', delivery: 'off' };
  y.els.cronFormNotifyInApp.value = 'failures';
  y.els.cronFormNotifyDeliveryFailures.checked = true;
  await y.saveCronForm();
  post = y.calls.api.find(c => c.url === '/api/crons/update');
  assert.deepEqual(post.body.notify, { in_app: 'failures', delivery: 'off' }, 'delivery off is an admin setting the form never changes');
  assert.equal(post.body.toast_notifications, true);

  const z = formScene();
  z._cronNotifySupported = true;
  z._editingCronId = 'job1';
  z._cronFormNotifyBase = { in_app: 'off', delivery: 'all' };
  z.els.cronFormNotifyInApp = new FakeEl('cronFormNotifyInApp', { value: 'off', disabled: true });
  z.els.cronFormNotifyDeliveryFailures.checked = true;
  await z.saveCronForm();
  post = z.calls.api.find(c => c.url === '/api/crons/update');
  assert.deepEqual(post.body.notify, { in_app: 'off', delivery: 'failures' });
  assert.equal(post.body.toast_notifications, false);
});

test('popover save and the personal mute', async () => {
  const job = { id: 'j', owner_email: OWNER, deliver: 'telegram', notify: { in_app: 'all', delivery: 'all' } };
  const x = scene({ me: governed(OWNER) });
  x._cronNotifySupported = true;
  x._cronList = [job];
  x.els.cronPopNotifyInApp = new FakeEl('cronPopNotifyInApp', { value: 'all' });
  x.els.cronPopNotifyDeliveryFailures = new FakeEl('cronPopNotifyDeliveryFailures', { checked: false });
  await x._saveCronNotify('j');
  assert.equal(x.calls.api.length, 0, 'nothing changed, nothing sent');
  x.els.cronPopNotifyDeliveryFailures.checked = true;
  await x._saveCronNotify('j');
  assert.deepEqual(x.calls.api[0], { url: '/api/crons/update', method: 'POST', body: { job_id: 'j', toast_notifications: true, notify: { in_app: 'all', delivery: 'failures' } } });
  assert.deepEqual(x.calls.toasts.at(-1), ['Notification setting saved']);
  assert.equal(x.calls.loads, 1);

  const shared = { id: 's', owner_email: OWNER, shared_with: [SHAREE], notify: { in_app: 'all', delivery: 'all' } };
  const y = scene({ me: governed(SHAREE), routes: {
    '/api/crons/notifications': (body) => (body ? { ok: true, revision: 8 } : { revision: 7, jobs: {} }),
  } });
  y._cronNotifySupported = true;
  y._cronList = [shared];
  await y.toggleCronNotifyMute('s');
  assert.deepEqual(y.calls.api.map(c => [c.method, c.url]), [['GET', '/api/crons/notifications'], ['POST', '/api/crons/notifications']]);
  assert.deepEqual(y.calls.api[1].body, { job_id: 's', in_app: 'quiet', revision: 7 });
  assert.equal(y._cronNotifyRevision, 8);
  assert.equal(shared.my_notify, 'quiet');
  assert.equal(y._cronNotifyMine.s, 'quiet');
  await y.toggleCronNotifyMute('s');
  assert.deepEqual(y.calls.api.at(-1).body, { job_id: 's', in_app: null, revision: 8 });
  assert.equal(shared.my_notify, null);
  assert.equal('s' in y._cronNotifyMine, false);

  const z = scene({ me: governed(SHAREE), routes: {
    '/api/crons/notifications': (body) => { if (body) throw Object.assign(new Error('stale'), { status: 409 }); return { revision: 9, jobs: { s: 'quiet' } }; },
  } });
  z._cronNotifySupported = true;
  z._cronNotifyRevision = 3;
  z._cronList = [{ ...shared }];
  await z.toggleCronNotifyMute('s');
  assert.deepEqual(z.calls.toasts.at(-1), ['This setting changed elsewhere. Reload and try again.', 5000, 'error']);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(z._cronNotifyRevision, 9, 'the conflict reloads the revision');
  assert.equal(z.calls.loads, 0);
});

test('duplicate: admin-only levels, custom targets and denied skills are dropped for non-admins', async () => {
  const x = scene({ me: governed(OWNER) });
  assert.deepEqual({ ...x._cronDuplicateNotify({ notify: { in_app: 'off', delivery: 'off' }, category: 'Monitoring' }, false) }, { in_app: 'failures', delivery: 'all' });
  assert.deepEqual({ ...x._cronDuplicateNotify({ notify: { in_app: 'off', delivery: 'off' } }, true) }, { in_app: 'off', delivery: 'off' });
  assert.deepEqual({ ...x._cronDuplicateNotify({ notify: { in_app: 'quiet', delivery: 'failures' } }, false) }, { in_app: 'quiet', delivery: 'failures' });

  const options = keepCustom => {
    const y = scene({ routes: { '/api/crons/delivery-options': { platforms: [{ value: 'local', label: 'Local' }, { value: 'telegram', label: 'Telegram' }] } } });
    const sel = y.els.cronFormDeliver = new FakeEl('cronFormDeliver');
    y.document.createElement = tag => new FakeEl(tag);
    Object.defineProperty(sel, 'innerHTML', { set() { sel.children = []; }, get() { return ''; } });
    return y._populateCronDeliverOptions('telegram:12345', keepCustom).then(() => sel.children.map(o => [o.value, !!o.selected]));
  };
  assert.deepEqual(await options(false), [['local', true], ['telegram', false]]);
  assert.deepEqual(await options(true), [['telegram:12345', true], ['local', false], ['telegram', false]]);

  const z = scene({ me: governed(OWNER), routes: { '/api/skills': { skills: [{ name: 'granted-skill' }] } } });
  let rendered = null;
  z._renderCronForm = args => { rendered = args; };
  z.run('function switchPanel(){}; var _currentPanel = "tasks";');
  z._currentCronDetail = { id: 'j', name: 'Report', skills: ['granted-skill', 'secret-skill'], deliver: 'telegram:12345', notify: { in_app: 'off', delivery: 'failures' }, schedule: { kind: 'cron', expr: '0 9 * * *' } };
  z.duplicateCurrentCron();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual({ ...rendered.notify }, { in_app: 'all', delivery: 'failures' });
  assert.equal(rendered.deliver, 'telegram:12345', 'the select drops it when the options load');
  assert.deepEqual([...z._cronSelectedSkills], ['granted-skill']);
  assert.equal(z.calls.skills, 1);
});

test('every string the notification UI shows is an Appendix G key', () => {
  const code = block('// ── Scheduled task notifications (plan 3.1)', '// ── End of scheduled task notifications');
  const keys = new Set([...code.matchAll(/\bt\('([a-z0-9_]+)'/g)].map(m => m[1]));
  for (const key of Object.values({ all: 'cron_notify_me_all', failures: 'cron_notify_me_failures', quiet: 'cron_notify_me_never', off: 'cron_notify_me_off_admin' })) keys.add(key);
  const allowed = new Set(KEYS);
  for (const key of keys) assert.ok(allowed.has(key), 'unexpected i18n key ' + key);
  assert.doesNotMatch(code, /\|\|\s*'[A-Z]/, 'no hard-coded fallback copy');
  assert.doesNotMatch(code, new RegExp('[\\u2013\\u2014]'), 'no en or em dash');
});

// Completion alerts: the poller and its flags.
test('completion flags from the server, with the toast_notifications fallback', () => {
  const x = scene();
  const flags = c => ({ ...x._cronCompletionFlags(c) });
  assert.deepEqual(flags({ toast: true, badge: true, desktop: false, silent: false }), { toast: true, badge: true, desktop: false, silent: false });
  assert.deepEqual(flags({ toast: false, badge: true, desktop: false, silent: false }), { toast: false, badge: true, desktop: false, silent: false });
  assert.deepEqual(flags({ toast: true, badge: true, desktop: true, silent: true }), { toast: false, badge: false, desktop: false, silent: true });
  assert.deepEqual(flags({ toast_notifications: false }), { toast: false, badge: true, desktop: false, silent: false });
  assert.deepEqual(flags({ toast_notifications: true }), { toast: true, badge: true, desktop: false, silent: false });
  assert.deepEqual(flags({}), { toast: true, badge: true, desktop: false, silent: false });
});

test('the poller follows toast, badge, desktop and silent (stubbed /api/crons/recent)', async () => {
  const completions = [
    { job_id: 'every', name: 'Every run', status: 'ok', completed_at: 20, session_id: 's-every', message_count: 2, toast: true, badge: true, desktop: false, silent: false },
    { job_id: 'failures-ok', name: 'Only failures, ok', status: 'ok', completed_at: 21, session_id: 's-f', toast: false, badge: false, desktop: false, silent: false },
    { job_id: 'failures-err', name: 'Only failures, failed', status: 'error', completed_at: 22, session_id: 's-e', toast: true, badge: true, desktop: true, silent: false },
    { job_id: 'never', name: 'Never', status: 'ok', completed_at: 23, session_id: 's-n', toast: false, badge: true, desktop: false, silent: false },
    { job_id: 'silent', name: 'Silent monitor', status: 'ok', completed_at: 24, session_id: 's-s', toast: true, badge: true, desktop: false, silent: true },
    { job_id: 'legacy', name: 'Legacy muted', status: 'ok', completed_at: 25, session_id: 's-l', toast_notifications: false },
  ];
  const x = scene({ routes: { '/api/crons/recent?since=10': { completions } } });
  x.startCronPolling();
  await x.__tick();
  assert.deepEqual(x.calls.toasts.map(a => a[0]), ['Cron "Every run" completed', 'Cron "Only failures, failed" failed']);
  assert.deepEqual(x.calls.desktop.map(a => [a[0], a[1], a[2].sid]), [['Only failures, failed', 'Cron "Only failures, failed" failed', 's-e']]);
  assert.deepEqual([...x._cronNewJobIds], ['every', 'failures-err', 'never', 'legacy']);
  assert.deepEqual(x.calls.marks.map(a => a[0]), ['s-every', 's-e', 's-n', 's-l']);
  assert.equal(x._cronPollSince, 25);
  assert.equal(x.calls.badge, 1);
});

test('a hidden tab polls only for the desktop notifications the viewer turned on', async () => {
  const x = scene({ routes: { '/api/crons/recent?since=10': { completions: [] } } });
  x.document.hidden = true;
  x.startCronPolling();
  await x.__tick();
  assert.equal(x.calls.api.length, 0);
  x.window._notificationsEnabled = true;
  await x.__tick();
  assert.deepEqual(x.calls.api.map(c => c.url), ['/api/crons/recent?since=10']);
});

(async () => {
  let passed = 0;
  for (const [name, body] of tests) {
    try { await body(); passed++; }
    catch (error) { console.error('FAIL ' + name); throw error; }
  }
  console.log(passed + ' cron notification UI scenarios passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
