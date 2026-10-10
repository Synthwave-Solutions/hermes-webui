// Group chat routing and live bot identity in the browser (plan 5.2, W6).
// Part 1 runs static/chat-bots.js in a vm and checks the pure rules. Part 2
// drives the roster, the reason chip, the default bot toggle and the mention
// picker in Chromium through Playwright when it is installed (set
// PLAYWRIGHT_MODULE to its path; GROUP_ROUTING_REQUIRE_BROWSER=1 makes a
// missing browser a failure instead of a skip).
const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');

const DASHES = /[\u2013\u2014]/;
const EN = fs.readFileSync('static/i18n/en.js', 'utf8');
const KEYS = {};
for (const key of ['group_route_reason_mention', 'group_route_reason_only_bot', 'group_route_reason_sticky',
  'group_route_reason_default', 'group_route_working', 'group_route_set_default', 'group_route_clear_default',
  'group_route_default_badge', 'group_route_last_bot_unavailable']) {
  const match = new RegExp('\\b' + key + ":\\s*'([^']*)'").exec(EN);
  assert.ok(match, 'missing English value for ' + key);
  KEYS[key] = match[1];
}

// ── Part 1: pure rules ──────────────────────────────────────────────────────
const context = {window:{addEventListener(){}}, document:{readyState:'loading', getElementById(){ return null; }, addEventListener(){}}, S:{}};
vm.runInNewContext(fs.readFileSync('static/chat-bots.js', 'utf8'), context);
const rules = context.window.chatBotRecipientRules;
assert.equal(rules.handleFromText('Sales'), 'sales');
assert.equal(rules.handleFromText('Hermes Ops'), 'ops');
assert.equal(rules.handleFromText('My OmniRoute and n8n desk'), 'my-and-desk');
assert.equal(rules.botHandle('ops-omniroute', undefined), 'ops');
assert.equal(rules.botHandle('hermes', ''), 'bot');
for (const name of rules.HANDLE_DENYLIST) {
  const handle = rules.handleFromText('The ' + name + ' helper');
  assert.ok(!rules.HANDLE_DENYLIST.some(denied => handle.includes(denied.toLowerCase())), handle);
}
const handles = {'sales-bot-7':'sales', research:'research', legal:'legal'};
const handleOf = id => handles[id] || id;
const session = {bot_participants:['research', 'sales-bot-7'], default_bot:'research'};
const history = [{role:'user', content:'@sales price?'}, {role:'assistant', content:'10 euro', bot_profile:'sales-bot-7'}];
const route = (draft, usable, s = session, messages = history) => rules.predictRoute(s, messages, draft, usable, handleOf);
assert.deepEqual({...route('@research check')}, {bot:'research', reason:'mention'});
assert.deepEqual({...route('@sales check')}, {bot:'sales-bot-7', reason:'mention'});
assert.deepEqual({...route('@SALES-BOT-7 check')}, {bot:'sales-bot-7', reason:'mention'});
assert.equal(route('@nobody check'), null);
assert.deepEqual({...route('And for ten seats?')}, {bot:'sales-bot-7', reason:'sticky'});
assert.deepEqual({...route('Start', null, session, [])}, {bot:'research', reason:'default'});
assert.deepEqual({...route('Start', null, {bot_participants:['legal']}, [])}, {bot:'legal', reason:'only_bot'});
assert.equal(route('Start', null, {bot_participants:['research', 'legal']}, []), null);
// The sender may not use the last bot: the default answers, else the choose prompt.
assert.deepEqual({...route('More', bot => bot !== 'sales-bot-7')}, {bot:'research', reason:'default'});
assert.deepEqual({...route('More', bot => bot !== 'sales-bot-7', {bot_participants:['research', 'sales-bot-7']})}, {bot:null, reason:'last_unavailable'});
assert.equal(route('More', null, {bot_participants:[]}), null);
assert.equal(rules.resolveMention('Sales', ['sales-bot-7', 'sales-2'], id => 'sales'), null);
assert.equal(rules.reasonText('sticky', 'sales'), 'Continued with @sales (last to answer)');
assert.equal(rules.reasonText('mention', 'x'), 'Asked by name');
assert.equal(rules.reasonText('only_bot', 'x'), 'Only bot in this chat');
assert.equal(rules.reasonText('default', 'x'), 'Default bot of this chat');
assert.equal(rules.reasonText('guess', 'x'), '');
const directory = [{kind:'bot', id:'sales-bot-7', label:'Sales', handle:'sales'}, {kind:'bot', id:'ops-hermes', label:'Ops', handle:'ops'},
  {kind:'bot', id:'twin-a', label:'Twin', handle:null}, {kind:'user', id:'bob@example.test', label:'Bob'}];
assert.deepEqual(Array.from(rules.mentions('@sales and @ops ask @bob@example.test', directory), row => row.id), ['sales-bot-7', 'ops-hermes', 'bob@example.test']);
assert.equal(rules.normalizeBotAddress('Please @SALES quote', directory), '@sales Please  quote');
assert.equal(rules.normalizeBotAddress('@twin-a go', directory), '@twin-a go');
console.log('group routing vm checks passed');

// ── Part 2: the browser ─────────────────────────────────────────────────────
let playwright = null;
try { playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright'); } catch (_) { playwright = null; }
if (!playwright) {
  if (process.env.GROUP_ROUTING_REQUIRE_BROWSER === '1') { console.error('Playwright is required but not installed'); process.exit(1); }
  console.log('group routing browser checks skipped: Playwright is not installed');
  process.exit(0);
}

(async () => {
  const browser = await playwright.chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || undefined});
  try {
    const page = await browser.newPage({viewport:{width:1100, height:800}});
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    await page.setContent(`<div id="messages"><div id="msgInner">
        <div class="msg-row" data-role="user" data-msg-idx="0">@sales price?</div>
        <div class="msg-row assistant-turn" data-role="assistant" data-recycle-key="1"><div class="msg-role assistant"><span class="msg-role-name">Sales</span></div><div class="assistant-turn-blocks">10 euro</div></div>
      </div></div><div id="composerWrap"><textarea id="msg"></textarea></div>`);
    await page.addStyleTag({path:'static/chat-bots.css'});
    await page.addStyleTag({path:'static/group-routing.css'});
    await page.evaluate(keys => {
      window.__GOV_ME__ = {email:'alice@example.test', roles:[]};
      window.S = {_bootReady:true, activeProfile:'default', activeStreamId:null,
        session:{session_id:'g1', owner_email:'alice@example.test', participants:['bob@example.test'],
          bot_participants:['research', 'sales-bot-7'], default_bot:'research'},
        messages:[{role:'user', content:'@sales price?'}, {role:'assistant', content:'10 euro', bot_profile:'sales-bot-7', bot_name:'Sales'}]};
      window.t = (key, ...args) => keys[key] === undefined ? key : keys[key].replace(/\{(\d+)\}/g, (m, i) => args[i]);
      window.botAvatarHtml = () => ''; window.botDisplayName = p => (p.bot && p.bot.title) || p.name;
      window.toasts = []; window.showToast = text => toasts.push(text);
      window.calls = []; window.api = (url, options) => new Promise((resolve, reject) => calls.push({url, options, resolve, reject}));
      window.workingEvents = []; addEventListener('synpulse:group-working', e => workingEvents.push(e.detail));
      // about:blank is not a secure context, so randomUUID is missing there.
      if (typeof crypto.randomUUID !== 'function') crypto.randomUUID = () => 'request-' + Math.random().toString(16).slice(2);
    }, KEYS);
    await page.addScriptTag({path:'static/chat-bots.js'});
    const resolve = (index, value) => page.evaluate(({index, value}) => calls[index].resolve(value), {index, value});
    assert.deepEqual(await page.evaluate(() => calls.map(c => c.url)), ['/api/profiles?fast=1', '/api/people']);
    await resolve(0, {profiles:[
      {name:'research', bot:{title:'Research', description:'Finds and summarises sources for a question.'}},
      {name:'sales-bot-7', bot:{title:'Sales', description:'Quotes, pricing and offers for customers.'}},
      {name:'ops-hermes', visible:false, bot:{title:'Hermes Ops', description:'Hidden helper.'}},
      {name:'legal', bot:{title:'Legal'}}]});
    await resolve(1, {people:[{email:'bob@example.test', display_name:'Bob'}]});
    await page.locator('[data-bot="sales-bot-7"]').waitFor();

    // Roster: the chat's bots, the default badge, and who answers an unaddressed message.
    assert.deepEqual(await page.$$eval('#chatBotRosterItems [data-bot]', nodes => nodes.map(n => n.dataset.bot)), ['research', 'sales-bot-7']);
    assert.equal(await page.locator('[data-bot="research"] .group-route-default-badge').textContent(), 'Default');
    assert.equal(await page.locator('[data-bot="sales-bot-7"] .group-route-default-badge').count(), 0);
    assert.equal(await page.getAttribute('[data-bot="sales-bot-7"]', 'aria-pressed'), 'true');
    assert.equal(await page.getAttribute('[data-bot="sales-bot-7"]', 'title'), '@sales');
    assert.equal(await page.getAttribute('[data-default-bot="research"]', 'aria-pressed'), 'true');
    assert.equal(await page.getAttribute('[data-default-bot="research"]', 'aria-label'), 'Clear default: Research');
    assert.equal(await page.getAttribute('[data-default-bot="sales-bot-7"]', 'aria-label'), 'Set as default: Sales');
    await page.locator('#msg').fill('@research check this');
    assert.equal(await page.getAttribute('[data-bot="research"]', 'aria-pressed'), 'true');
    assert.equal(await page.getAttribute('[data-bot="sales-bot-7"]', 'aria-pressed'), 'false');
    await page.locator('#msg').fill('');
    // Clicking a roster bot addresses it by its handle.
    await page.click('[data-bot="sales-bot-7"]');
    assert.equal(await page.inputValue('#msg'), '@sales ');
    await page.locator('#msg').fill('');

    // Live turn: Working on the bot, the reason chip on the reply, then idle.
    await page.evaluate(() => {
      S.activeStreamId = 'st1';
      const turn = document.createElement('div'); turn.id = 'liveAssistantTurn'; turn.className = 'msg-row assistant-turn';
      turn.innerHTML = '<div class="msg-role assistant"><span class="msg-role-name">Sales</span></div>';
      document.getElementById('msgInner').insertAdjacentHTML('beforeend', '<div class="msg-row" data-role="user" data-msg-idx="2">And for ten seats?</div>');
      S.messages.push({role:'user', content:'And for ten seats?'});
      groupRouting.onTurnBot('g1', 'st1', {session_id:'g1', stream_id:'st1', bot:'sales-bot-7', reason:'sticky', handle:'sales', name:'Sales'});
      document.getElementById('msgInner').appendChild(turn);
    });
    assert.equal(await page.locator('[data-bot="sales-bot-7"] .group-route-working').textContent(), 'Working');
    assert.equal(await page.getAttribute('[data-bot="sales-bot-7"]', 'data-working'), 'true');
    assert.equal(await page.locator('[data-bot="research"] .group-route-working').count(), 0);
    assert.deepEqual(await page.evaluate(() => groupRouting.workingState('g1')).then(s => [s.bot, s.stream_id, s.reason]), ['sales-bot-7', 'st1', 'sticky']);
    assert.deepEqual(await page.evaluate(() => workingEvents.map(e => [e.bot, e.working])), [['sales-bot-7', true]]);
    await page.waitForFunction(() => document.querySelector('#liveAssistantTurn .group-route-chip'));
    assert.equal(await page.locator('#liveAssistantTurn .group-route-chip').textContent(), 'Continued with @sales (last to answer)');
    assert.equal(await page.locator('[data-recycle-key="1"] .group-route-chip').count(), 0);
    // The stream ends: Working goes away within a second.
    await page.evaluate(() => { S.activeStreamId = null; });
    await page.waitForFunction(() => !document.querySelector('[data-bot="sales-bot-7"] .group-route-working'), null, {timeout:3000});
    assert.equal(await page.evaluate(() => groupRouting.workingState('g1')), null);
    assert.deepEqual(await page.evaluate(() => workingEvents.map(e => [e.bot, e.working])), [['sales-bot-7', true], ['sales-bot-7', false]]);
    // The settled reply keeps its chip until the next message is written.
    await page.evaluate(() => {
      const live = document.getElementById('liveAssistantTurn'); live.remove();
      S.messages.push({role:'assistant', content:'90 euro', bot_profile:'sales-bot-7', bot_name:'Sales'});
      document.getElementById('msgInner').insertAdjacentHTML('beforeend', '<div class="msg-row assistant-turn" data-role="assistant" data-recycle-key="3"><div class="msg-role assistant"><span class="msg-role-name">Sales</span></div></div>');
    });
    await page.waitForFunction(() => document.querySelector('[data-recycle-key="3"] .group-route-chip'));
    await page.evaluate(() => {
      S.messages.push({role:'user', content:'Thanks'});
      document.getElementById('msgInner').insertAdjacentHTML('beforeend', '<div class="msg-row" data-role="user" data-msg-idx="4">Thanks</div>');
    });
    await page.waitForFunction(() => !document.querySelector('.group-route-chip'));
    // A reason stored on the message shows on reload.
    await page.evaluate(() => {
      S.messages.push({role:'user', content:'Hi'}, {role:'assistant', content:'Hello', bot_profile:'research', bot_name:'Research', route_reason:'default'});
      document.getElementById('msgInner').insertAdjacentHTML('beforeend', '<div class="msg-row assistant-turn" data-role="assistant" data-recycle-key="6"><div class="msg-role assistant"><span class="msg-role-name">Research</span></div></div>');
    });
    await page.waitForFunction(() => document.querySelector('[data-recycle-key="6"] .group-route-chip'));
    assert.equal(await page.locator('[data-recycle-key="6"] .group-route-chip').textContent(), 'Default bot of this chat');

    // Set and clear the default bot through the participants route.
    await page.click('[data-default-bot="sales-bot-7"]');
    let request = await page.evaluate(() => { const c = calls[calls.length - 1]; return {url:c.url, method:c.options.method, body:JSON.parse(c.options.body)}; });
    assert.deepEqual(request, {url:'/api/session/participants', method:'POST', body:{session_id:'g1', participants:['bob@example.test'],
      bot_participants:['research', 'sales-bot-7'], default_bot:'sales-bot-7'}});
    assert.equal(await page.locator('[data-default-bot="research"]').isDisabled(), true);
    await page.evaluate(() => calls[calls.length - 1].resolve({ok:true, participants:['bob@example.test'], bot_participants:['research', 'sales-bot-7']}));
    await page.waitForFunction(() => S.session.default_bot === 'sales-bot-7' && document.querySelector('[data-bot="sales-bot-7"] .group-route-default-badge'));
    await page.click('[data-default-bot="sales-bot-7"]');
    request = await page.evaluate(() => JSON.parse(calls[calls.length - 1].options.body));
    assert.equal(request.default_bot, null);
    await page.evaluate(() => calls[calls.length - 1].reject(new Error('Choose the default bot from the bots in this chat.')));
    await page.waitForFunction(() => toasts.length === 1);
    assert.equal(await page.evaluate(() => S.session.default_bot), 'sales-bot-7');
    await page.click('[data-default-bot="sales-bot-7"]');
    await page.evaluate(() => calls[calls.length - 1].resolve({ok:true, participants:['bob@example.test'], bot_participants:['research', 'sales-bot-7'], default_bot:null}));
    await page.waitForFunction(() => S.session.default_bot === null && !document.querySelector('.group-route-default-badge'));

    // Mention picker: handles and descriptions; hidden bots stay out but still resolve.
    await page.locator('#msg').focus();
    await page.keyboard.type('@');
    await page.locator('#chatMentionDropdown button').first().waitFor();
    const options = await page.$$eval('#chatMentionDropdown button', nodes => nodes.map(n => ({id:n.dataset.mentionId, text:n.textContent,
      detail:n.querySelector('small').textContent, description:(n.querySelector('.group-route-bot-description') || {}).textContent || ''})));
    assert.deepEqual(options.map(o => o.id), ['research', 'sales-bot-7', 'legal', 'bob@example.test']);
    assert.equal(options[1].detail, 'Bot · @sales');
    assert.equal(options[1].description, 'Quotes, pricing and offers for customers.');
    assert.equal(options[2].description, '');
    await page.keyboard.type('sal');
    await page.keyboard.press('Enter');
    assert.equal(await page.inputValue('#msg'), '@sales ');
    await page.locator('#msg').fill('@ops check the logs');
    const prepared = page.evaluate(() => prepareChatMentions());
    await page.waitForFunction(() => calls[calls.length - 1].url === '/api/chat/mentions/prepare');
    const body = await page.evaluate(() => JSON.parse(calls[calls.length - 1].options.body));
    assert.deepEqual(body.bot_participants, ['ops-hermes']);
    await page.evaluate(() => calls[calls.length - 1].resolve({session:{session_id:'g1', bot_participants:['research', 'sales-bot-7', 'ops-hermes']}}));
    assert.equal(await prepared, true);
    assert.equal(await page.inputValue('#msg'), '@ops check the logs');

    // A sender who may not use the last bot is asked to choose before sending.
    await page.evaluate(() => {
      S.session = {session_id:'g2', owner_email:'bob@example.test', participants:['alice@example.test'], bot_participants:['research', 'private-bot']};
      S.messages = [{role:'assistant', content:'Done', bot_profile:'private-bot'}];
      document.getElementById('msg').value = '';
      refreshChatBots();
    });
    const pending = await page.evaluate(() => calls.length);
    await resolve(pending - 2, {profiles:[{name:'research', bot:{title:'Research'}}]});
    await resolve(pending - 1, {people:[]});
    await page.waitForFunction(() => document.getElementById('chatMentionHint').dataset.routeWarning === 'true');
    assert.equal(await page.locator('#chatMentionHint').textContent(), 'The last bot is not available to you. Choose a bot to continue.');
    assert.equal(await page.locator('#chatMentionHint').isHidden(), false);
    // Not the owner: no default toggles.
    assert.equal(await page.locator('.group-route-default-toggle').count(), 0);

    // On a narrow screen the strip scrolls the working bot into view.
    await page.setViewportSize({width:360, height:740});
    await page.evaluate(() => {
      S.session = {...S.session, session_id:'g2', bot_participants:['research', 'private-bot', 'legal', 'wide-one', 'wide-two']};
      refreshChatBots();
    });
    const loaded = await page.evaluate(() => calls.length);
    await resolve(loaded - 2, {profiles:['research', 'legal', 'wide-one', 'wide-two'].map(name => ({name, bot:{title:name === 'research' ? 'Research' : 'A rather long bot title ' + name}}))});
    await resolve(loaded - 1, {people:[]});
    await page.locator('[data-bot="wide-two"]').waitFor();
    await page.evaluate(() => { S.activeStreamId = 'st8'; groupRouting.onTurnBot('g2', 'st8', {bot:'wide-two', reason:'default', handle:'wide-two'}); });
    const inView = await page.evaluate(() => {
      const strip = document.getElementById('chatBotRosterItems').getBoundingClientRect();
      const chip = document.querySelector('[data-bot="wide-two"]').getBoundingClientRect();
      return strip.width > 0 && chip.left >= strip.left - 1 && chip.right <= strip.right + 1;
    });
    assert.equal(inView, true);
    await page.evaluate(() => { S.activeStreamId = null; });
    await page.waitForFunction(() => !document.querySelector('.group-route-working'), null, {timeout:3000});
    await page.setViewportSize({width:1100, height:800});

    // Motion respects the reduced-motion preference.
    await page.evaluate(() => { S.activeStreamId = 'st9'; groupRouting.onTurnBot('g2', 'st9', {bot:'research', reason:'default', handle:'research'}); });
    const animated = await page.$eval('.group-route-working-dot', node => getComputedStyle(node).animationName);
    assert.equal(animated, 'group-route-working-pulse');
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.$eval('.group-route-working-dot', node => getComputedStyle(node).animationName), 'none');

    const copy = await page.evaluate(() => document.body.innerText + ' ' + Array.from(document.querySelectorAll('[aria-label],[title]'))
      .map(n => (n.getAttribute('aria-label') || '') + ' ' + (n.getAttribute('title') || '')).join(' '));
    assert.ok(!DASHES.test(copy), 'dash in rendered copy');
    assert.deepEqual(errors, []);
    console.log('group routing browser checks passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
