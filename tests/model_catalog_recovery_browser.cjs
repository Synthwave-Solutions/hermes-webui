// Real Chromium DOM and complete production ui.js; every HTTP boundary is synthetic.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = 'https://catalog-fixture.invalid';
const routeId = '@custom:omniroute:codex/gpt-6-astra';
const provisional = {active_provider: 'openai-api', default_model: 'default-model', refresh_pending: true,
  groups: [{provider: 'OpenAI', provider_id: 'openai-api', models: [{id: 'default-model', label: 'Default'}, {id: 'other', label: 'Other'}]}]};
const complete = {...provisional, refresh_pending: false, groups: [...provisional.groups,
  {provider: 'OmniRoute', provider_id: 'custom:omniroute', models: [{id: routeId, label: 'GPT-6 Astra'}, {id: '@custom:omniroute:codex/other', label: 'Other routed model'}]}]};
async function scene(browser, width) {
  const context = await browser.newContext({viewport: {width, height: 800}, serviceWorkers: 'block'});
  const network = [], errors = [];
  await context.route('**/*', r => {
    if(r.request().url() === origin + '/') return r.fulfill({contentType: 'text/html', body: `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic catalog fixture</title><label>Model<select id="modelSelect"><option value="other">Other</option></select></label><label>Message<textarea id="msgInput">Unsaved synthetic draft</textarea></label><select id="reasoningEffort"><option>High</option></select><div id="composerModelDropdown"></div>`});
    network.push(r.request().url()); return r.abort('blockedbyclient');
  });
  if(context.routeWebSocket) await context.routeWebSocket('**/*', s => { network.push(s.url()); s.close(); });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(origin + '/');
  await page.evaluate(() => {
    window.t = k => k;
    window._profileSwitchGeneration = 0;
    window.__catalog = {calls: [], queue: [], live: []};
    window.fetch = (url, options = {}) => {
      const call = {url: String(url), aborted: false}; __catalog.calls.push(call);
      const response = __catalog.queue.shift();
      if(!response) return Promise.reject(new Error('Unexpected synthetic request ' + url));
      const finish = () => ({ok: (response.status || 200) < 400, status: response.status || 200, json: async () => response.body || response});
      if(!response.hold) return Promise.resolve(finish());
      return new Promise((resolve, reject) => {
        call.finish = () => resolve(finish());
        options.signal?.addEventListener('abort', () => { call.aborted = true; if(!response.ignoreAbort) reject(new DOMException('Aborted', 'AbortError')); });
      });
    };
  });
  await page.addScriptTag({path: path.resolve('static/ui.js')});
  await page.evaluate(() => {
    // Unrelated presentation/transport boundaries; selection and catalog code stay native.
    syncModelChip = () => {};
    window.__nativeFetchLiveModels = _fetchLiveModels;
    _fetchLiveModels = (...args) => __catalog.live.push(args[0]);
    _redirectIfUnauth = r => r.status === 401;
    S.activeProfile = 'default'; S.session = null;
  });
  return {context, page, network, errors};
}
async function finish(scene) {
  assert.deepEqual(scene.errors, []); assert.deepEqual(scene.network, []);
  await scene.context.close();
}
async function start(s, queue, options = {}) {
  await s.page.evaluate(({queue, options}) => { __catalog.queue.push(...queue); window.__started = populateModelDropdown(options); }, {queue, options});
  await s.page.evaluate(() => __started);
}
async function invariant(page) {
  assert.equal(await page.locator('#msgInput').inputValue(), 'Unsaved synthetic draft');
  assert.equal(await page.locator('#reasoningEffort').inputValue(), 'High');
  assert.equal(await page.locator('#msgInput').isEnabled(), true);
}
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  let passed = 0;
  try {
    for(const width of [1280, 390]) {
      const s = await scene(browser, width);
      try {
        await start(s, [provisional, complete]);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
        await s.page.waitForFunction(id => [...document.querySelector('#modelSelect').options].some(o => o.value === id), routeId, {timeout: 3500});
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
        await s.page.locator('#modelSelect').selectOption(routeId);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), routeId);
        await invariant(s.page);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 2);
        assert.deepEqual(await s.page.evaluate(() => __catalog.live), ['openai-api']);
        passed++;
      } finally { await finish(s); }
    }
    for(const width of [1280, 390]) {
      const run = async (name, body) => {
        const s = await scene(browser, width);
        try { await body(s); await invariant(s.page); passed++; }
        catch(e) { e.message = name + ' (' + width + '): ' + e.message; throw e; }
        finally { await finish(s); }
      };
      await run('No recovery without authoritative marker', async s => {
        await s.page.clock.install();
        await start(s, [{...provisional, refresh_pending: 'true'}]);
        await s.page.clock.fastForward(5000);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 1);
      });
      await run('Repeated provisional results coalesce and stop at limit', async s => {
        await s.page.clock.install();
        await start(s, Array(6).fill(provisional));
        for(let i=0;i<6;i++) { await s.page.clock.fastForward(1200); await s.page.evaluate(() => Promise.resolve()); }
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 4);
        assert.equal(await s.page.evaluate(() => populateModelDropdown._cancelRecovery), null);
        assert.deepEqual(await s.page.evaluate(() => __catalog.live), []);
      });
      await run('Newer explicit refresh clears previous recovery timer', async s => {
        await s.page.clock.install();
        await start(s, [provisional]);
        await start(s, [complete]);
        await s.page.clock.fastForward(3000);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 2);
        assert.equal(await s.page.locator('option').filter({hasText:'GPT-6 Astra'}).count(), 1);
      });
      await run('Late active-provider enrichment cannot populate another profile', async s => {
        await s.page.evaluate(() => { _fetchLiveModels=__nativeFetchLiveModels; });
        await start(s, [complete, {body:{models:[{id:'stale-live',label:'Stale live'}]},hold:true}]);
        await s.page.evaluate(() => { S.activeProfile='beta'; _profileSwitchGeneration++; __catalog.calls[1].finish(); });
        await s.page.evaluate(() => Promise.resolve());
        assert.equal(await s.page.locator('option').filter({hasText:'Stale live'}).count(), 0);
        assert.equal(await s.page.evaluate(() => _liveModelCache['openai-api']), undefined);
      });
      await run('Profile A to B to A cancels scheduled recovery', async s => {
        await s.page.clock.install();
        await start(s, [provisional, complete]);
        await s.page.evaluate(() => { S.activeProfile='beta'; _profileSwitchGeneration++; S.activeProfile='default'; _profileSwitchGeneration++; });
        await s.page.clock.fastForward(1200);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 1);
        assert.equal(await s.page.evaluate(() => populateModelDropdown._cancelRecovery), null);
      });
      await run('Removed picker cancels scheduled recovery', async s => {
        await s.page.clock.install();
        await start(s, [provisional, complete]);
        await s.page.locator('#modelSelect').evaluate(el => el.remove());
        await s.page.clock.fastForward(1200);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 1);
        assert.equal(await s.page.evaluate(() => populateModelDropdown._cancelRecovery), null);
      });
      await run('External cancellation stops scheduled recovery', async s => {
        await s.page.clock.install();
        await s.page.evaluate(p => { __catalog.queue.push(p); window.__cancel=new AbortController(); window.__started=populateModelDropdown({signal:__cancel.signal}); }, provisional);
        await s.page.evaluate(() => __started);
        await s.page.evaluate(() => __cancel.abort());
        await s.page.clock.fastForward(1200);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 1);
      });
      await run('Superseded slow response never restores older catalog', async s => {
        await s.page.evaluate(p => { __catalog.queue.push({body:p,hold:true,ignoreAbort:true}); void populateModelDropdown(); }, provisional);
        await start(s, [complete]);
        await s.page.evaluate(() => __catalog.calls[0].finish());
        await s.page.evaluate(() => Promise.resolve());
        assert.equal(await s.page.evaluate(() => __catalog.calls[0].aborted), true);
        assert.equal(await s.page.locator('option').filter({hasText:'GPT-6 Astra'}).count(), 1);
        assert.equal(await s.page.evaluate(() => __catalog.calls.length), 2);
      });
      await run('Profile switch invalidates in-flight response before new request', async s => {
        await s.page.evaluate(p => { __catalog.queue.push({body:p,hold:true}); window.__started=populateModelDropdown(); }, complete);
        await s.page.evaluate(() => { S.activeProfile='beta'; _profileSwitchGeneration++; __catalog.calls[0].finish(); });
        await s.page.evaluate(() => __started);
        assert.equal(await s.page.locator('#modelSelect option').count(), 1);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
      });
      await run('Fresh boot recovery preserves subsequent deliberate choice', async s => {
        await start(s, [provisional, complete], {preferProfileDefaultOnFreshBoot:true});
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'default-model');
        await s.page.locator('#modelSelect').selectOption('other');
        await s.page.waitForFunction(() => __catalog.calls.length === 2);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
      });
      await run('Session replacement preserves new session route', async s => {
        await start(s, [provisional, complete]);
        await s.page.evaluate(id => { S.session={session_id:'new-qa',model:id,model_provider:'custom:omniroute'}; }, routeId);
        await s.page.waitForFunction(() => __catalog.calls.length === 2);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), routeId);
        assert.equal(await s.page.evaluate(() => _modelStateForSelect($('modelSelect'),$('modelSelect').value).model_provider), 'custom:omniroute');
      });
      await run('Unauthorized continuation stops without another request', async s => {
        await start(s, [provisional, {status:401,body:{}}]);
        await s.page.waitForFunction(() => __catalog.calls.length === 2);
        assert.equal(await s.page.evaluate(() => populateModelDropdown._cancelRecovery), null);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
      });
      await run('A hanging continuation is aborted by total deadline', async s => {
        await s.page.clock.install();
        await start(s, [provisional, {body:complete,hold:true}]);
        await s.page.clock.fastForward(1200);
        await s.page.waitForFunction(() => __catalog.calls.length === 2);
        await s.page.clock.fastForward(20000);
        assert.equal(await s.page.evaluate(() => __catalog.calls[1].aborted), true);
        assert.equal(await s.page.evaluate(() => populateModelDropdown._cancelRecovery), null);
        assert.equal(await s.page.locator('#modelSelect').inputValue(), 'other');
      });
    }
    process.stdout.write(JSON.stringify({status: 'PASS', journeys: passed, real_browser: true, synthetic_http: true}) + '\n');
  } finally { await browser.close(); }
})().catch(e => {console.error(e); process.exitCode = 1;});
