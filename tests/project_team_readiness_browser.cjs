// Real DOM and the complete production projects.js; every API boundary is synthetic.
// The virtual HTTPS page is fulfilled in process. No server or live user state is used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const origin = 'https://synthpulse-project-qa.invalid';
const screenshotDir = process.env.PROJECT_QA_SCREENSHOT_DIR;
const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SynthPulse isolated project readiness</title>
<style>body{font:16px sans-serif;background:#101928;color:#e8eef8;margin:20px;overflow-wrap:anywhere}
button,input{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}button{margin:5px}
.proj-card{padding:15px;margin:10px 0;border:1px solid #71859d}.proj-team-grid{display:flex;flex-wrap:wrap;gap:24px}
.proj-choice,.proj-field{display:block;margin:8px 0}.proj-field input{display:block}.proj-actions{display:flex;flex-wrap:wrap}
#projectsPanelList{display:none}#feedback{white-space:pre-wrap}</style>
<h1>Project readiness fixture</h1><p>Synthetic data. No provider or account connection.</p>
<div id="projectsPanelList"></div><div id="projDetailEmpty"></div><div id="projDetailBody">
<div id="projSummary"></div><div id="projSections"></div></div><div id="feedback" role="status"></div>`;

function project(id = 'alpha', overrides = {}) {
  return {project_id: id, name: 'Project ' + id, collaboration: true,
    owner_email: 'owner@example.test', members: ['member@example.test'],
    bot_participants: ['writer'], unavailable_bots: [], can_manage: true, revision: 1,
    ...overrides};
}

async function scene(browser, width) {
  const context = await browser.newContext({viewport: {width, height: 1000}, serviceWorkers: 'block'});
  const unexpected = [], pageErrors = [];
  await context.route('**/*', route => {
    if (route.request().url() === origin + '/') {
      return route.fulfill({status: 200, contentType: 'text/html', body: html});
    }
    unexpected.push(route.request().url());
    return route.abort('blockedbyclient');
  });
  if (context.routeWebSocket) await context.routeWebSocket('**/*', socket => {
    unexpected.push(socket.url()); socket.close({code: 1008, reason: 'Isolated fixture'});
  });
  const page = await context.newPage();
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto(origin + '/');
  await page.evaluate(() => {
    window.$ = id => document.getElementById(id);
    window.t = key => key;
    window.botDisplayName = bot => bot.name;
    window.__qa = {calls: [], loads: [], switches: [], projects: {}, batch: '', holdCreate: false};
    window._loadSessionGeneration = 0;
    window._currentPanel = 'projects';
    window.showToast = text => { $('feedback').textContent = text; };
    window.refreshSessionList = async () => {};
    window.loadSession = async id => { _loadSessionGeneration++; __qa.loads.push(id); };
    window.switchPanel = panel => { _currentPanel = panel; __qa.switches.push(panel); };
    window.api = (url, options = {}) => {
      const body = options.body ? JSON.parse(options.body) : null;
      const call = {url, body, batch: __qa.batch, pending: false};
      __qa.calls.push(call);
      if (url.startsWith('/api/projects/hub/detail?')) {
        const id = new URL(url, location.origin).searchParams.get('project_id');
        return Promise.resolve({project: structuredClone(__qa.projects[id])});
      }
      if (url === '/api/projects/chat') {
        const result = {session: {session_id: 'created-' + body.project_id, project_shared: true}};
        if (!__qa.holdCreate) return Promise.resolve(result);
        call.pending = true;
        return new Promise(resolve => { call.finish = () => { call.pending = false; resolve(result); }; });
      }
      if (url === '/api/projects/team') return Promise.resolve({ok: true});
      if (url === '/api/people') call.kind = 'people';
      else if (url === '/api/profiles?fast=1') call.kind = 'profiles';
      else if (url.startsWith('/api/projects/files?')) call.kind = 'files';
      else return Promise.reject(new Error('Unexpected fixture API: ' + url));
      call.pending = true;
      return new Promise((resolve, reject) => {
        call.finish = (value, error) => {
          call.pending = false;
          if (error) reject(new Error(error)); else resolve(value);
        };
      });
    };
  });
  await page.addScriptTag({path: path.resolve('static/projects.js')});
  return {page, context, unexpected, pageErrors};
}

async function openProject(page, value, batch, reuseHost = false) {
  await page.evaluate(async ({value, batch, reuseHost}) => {
    __qa.batch = batch;
    __qa.projects[value.project_id] = structuredClone(value);
    if (reuseHost) {
      __qa.reusedHost = $('projTeamControls');
      _projSelectedId = value.project_id;
      _projDetail = {project: structuredClone(value)};
      void _projLoadTeamControls(_projDetail.project);
    } else {
      await _projOpen(value.project_id);
    }
  }, {value, batch, reuseHost});
}

async function settle(page, batch, {errors = [], member = 'member@example.test', bot = 'writer', file = 'current.txt', responses = {}} = {}) {
  await page.evaluate(({batch, errors, member, bot, file, responses}) => {
    const values = {
      people: {people: [{email: 'owner@example.test', display_name: 'Owner'}, {email: member, display_name: member}], me: 'owner@example.test'},
      profiles: {profiles: [{name: bot}]}, files: {files: [{name: file}]}, ...responses
    };
    for (const call of __qa.calls.filter(call => call.batch === batch && call.kind && call.pending)) {
      call.finish(values[call.kind], errors.includes(call.kind) ? 'Synthetic ' + call.kind + ' unavailable' : null);
    }
  }, {batch, errors, member, bot, file, responses});
  // An event-loop/render boundary flushes settled promises without a timing race.
  await page.evaluate(() => new Promise(requestAnimationFrame));
}

async function snapshot(page, width, name, stage) {
  if (!screenshotDir) return;
  fs.mkdirSync(screenshotDir, {recursive: true});
  await page.screenshot({path: path.join(screenshotDir, `${width}-${name}-${stage}.png`), fullPage: true});
}

async function unavailableSave(page) {
  assert.equal(await page.locator('#projSaveTeam:not(:disabled)').count(), 0,
    'Incomplete or read-only metadata must not enable team updates');
  assert.equal(await page.evaluate(() => __qa.calls.filter(call => call.url === '/api/projects/team').length), 0);
}

async function start(page, id = 'alpha', finish = true) {
  assert.equal(await page.locator('#projStartChat').count(), 1, 'Actual project start button must render independently of metadata');
  assert.equal(await page.locator('#projStartChat').isEnabled(), true);
  await page.locator('#projStartChat').click();
  await page.waitForFunction(() => __qa.calls.some(call => call.url === '/api/projects/chat'));
  const posts = await page.evaluate(() => __qa.calls.filter(call => call.url === '/api/projects/chat').map(call => call.body));
  assert.equal(posts.length, 1);
  assert.equal(posts[0].project_id, id);
  assert.deepEqual(posts[0].bot_participants, ['writer']);
  assert.match(posts[0].request_id, /^[A-Za-z0-9_-]{16,80}$/);
  if (finish) {
    await page.evaluate(() => { for (const call of __qa.calls) if (call.url === '/api/projects/chat' && call.pending) call.finish(); });
    await page.waitForFunction(() => __qa.loads.length === 1);
    assert.deepEqual(await page.evaluate(() => __qa.loads), ['created-' + id]);
  }
}

const scenarios = [
  ['metadata-pending', async (page, width) => {
    await openProject(page, project(), 'pending');
    await snapshot(page, width, 'metadata-pending', 'before');
    assert.equal(await page.evaluate(() => __qa.calls.filter(call => call.kind && call.pending).length), 3);
    await unavailableSave(page);
    await start(page);
  }],
  ...['people', 'profiles'].map(kind => [kind + '-rejected', async page => {
    await openProject(page, project(), 'failed');
    await settle(page, 'failed', {errors: [kind]});
    await unavailableSave(page);
    await start(page);
  }]),
  ...['people', 'profiles'].flatMap(kind => [
    ['null', null], ['missing-list', {}], ['non-array-list', {[kind]: 'not a list'}]
  ].map(([shape, payload]) => [kind + '-' + shape, async page => {
    await openProject(page, project(), 'malformed');
    await settle(page, 'malformed', {responses: {[kind]: payload}});
    await unavailableSave(page);
    await start(page);
  }])),
  ['files-rejected', async page => {
    await openProject(page, project(), 'files');
    await settle(page, 'files', {errors: ['files']});
    assert.equal(await page.locator('#projSaveTeam').isEnabled(), true, 'Files failure must not disable complete team editing');
    await page.locator('#projSaveTeam').click();
    const update = await page.evaluate(() => __qa.calls.find(call => call.url === '/api/projects/team').body);
    assert.equal(update.project_id, 'alpha');
    assert.equal(update.revision, 1);
    assert.deepEqual(update.members, ['member@example.test']);
    assert.deepEqual(update.bot_participants, ['writer']);
    await start(page);
  }],
  ['metadata-during-create', async page => {
    await page.evaluate(() => { __qa.holdCreate = true; });
    await openProject(page, project(), 'busy');
    await start(page, 'alpha', false);
    await page.evaluate(() => { __qa.busyButton = $('projStartChat'); });
    await settle(page, 'busy');
    assert.equal(await page.evaluate(() => __qa.busyButton === $('projStartChat')), true, 'Metadata must not replace the active start button');
    assert.equal(await page.locator('#projStartChat').isDisabled(), true);
    assert.equal(await page.locator('#projStartChat').getAttribute('aria-busy'), 'true');
    await page.locator('#projStartChat').dispatchEvent('click');
    assert.equal(await page.evaluate(() => __qa.calls.filter(call => call.url === '/api/projects/chat').length), 1);
    await page.evaluate(() => __qa.calls.find(call => call.url === '/api/projects/chat').finish());
    await page.waitForFunction(() => __qa.loads.length === 1);
  }],
  ...['success', 'error'].map(outcome => ['a-b-a-old-' + outcome, async page => {
    await openProject(page, project('alpha', {name: 'Old Alpha', revision: 1}), 'a1');
    await openProject(page, project('beta', {name: 'Old Beta'}), 'b');
    await openProject(page, project('alpha', {name: 'Current Alpha', can_manage: false, revision: 3}), 'a2');
    await settle(page, 'a2');
    await settle(page, 'a1', {errors: outcome === 'error' ? ['people'] : [], member: 'stale-alpha@example.test', file: 'stale-alpha.txt'});
    await settle(page, 'b', {errors: outcome === 'error' ? ['people'] : [], member: 'stale-beta@example.test', file: 'stale-beta.txt'});
    assert.match(await page.locator('#projSummary').textContent(), /Current Alpha/);
    assert.doesNotMatch(await page.locator('#projTeamControls').textContent(), /stale-alpha|stale-beta|Synthetic/);
    assert.match(await page.locator('#projTeamControls').textContent(), /member@example.test/);
    await unavailableSave(page);
    await start(page);
  }]),
  ['same-host-reload', async page => {
    await openProject(page, project('alpha', {revision: 1}), 'old');
    await openProject(page, project('alpha', {revision: 9, members: ['latest@example.test'], bot_participants: ['latest-bot']}), 'new', true);
    assert.equal(await page.evaluate(() => __qa.reusedHost === $('projTeamControls')), true, 'Fixture must reuse the actual host');
    await settle(page, 'new', {member: 'latest@example.test', bot: 'latest-bot', file: 'latest.txt'});
    await settle(page, 'old', {member: 'stale@example.test', file: 'stale.txt'});
    assert.doesNotMatch(await page.locator('#projTeamControls').textContent(), /stale@example.test|stale.txt/);
    assert.deepEqual(await page.locator('#projHumanChoices input:checked').evaluateAll(nodes => nodes.map(node => node.value)), ['latest@example.test']);
    assert.deepEqual(await page.locator('#projBotChoices input:checked').evaluateAll(nodes => nodes.map(node => node.value)), ['latest-bot']);
    await page.locator('#projSaveTeam').click();
    const update = await page.evaluate(() => __qa.calls.find(call => call.url === '/api/projects/team').body);
    assert.equal(update.revision, 9);
    assert.deepEqual(update.members, ['latest@example.test']);
    assert.deepEqual(update.bot_participants, ['latest-bot']);
  }]
];

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  let failures = 0;
  try {
    for (const width of [1360, 390]) for (const [name, exercise] of scenarios) {
      const {page, context, unexpected, pageErrors} = await scene(browser, width);
      page.setDefaultTimeout(5000);
      try {
        await exercise(page, width);
        assert.deepEqual(unexpected, [], 'No unfulfilled browser network requests');
        assert.deepEqual(pageErrors, [], 'No uncaught browser errors');
        await snapshot(page, width, name, 'passed');
        console.log(`PASS ${width} ${name}`);
      } catch (error) {
        failures++;
        await snapshot(page, width, name, 'failed');
        console.error(`FAIL ${width} ${name}: ${error.stack || error}`);
      } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log(JSON.stringify({scenarios: scenarios.length * 2, failures, live_api_calls: 0}));
  process.exitCode = failures ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; });
