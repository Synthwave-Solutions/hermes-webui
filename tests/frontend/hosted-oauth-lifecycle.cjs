const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
  const nodes = new Map(), timers = new Map();
  const state = {calls: [], popups: [], nextTimer: 1, response: null};
  const node = () => ({textContent: '', children: [], setAttribute() {},
    replaceChildren() { this.children = []; }, append(child) { this.children.push(child); }});
  const ctx = {
    console,
    document: {hidden: false, addEventListener() {}, createElement: node},
    window: {open() {
      const popup = {closed: false, location: {}, close() { this.closed = true; }};
      state.popups.push(popup); return popup;
    }},
    $(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); },
    _intgT: (_key, fallback) => fallback,
    _intgSafeDocsUrl: url => url,
    _intgRenderConnections() {}, _intgRenderGrid() {},
    _intgLoadCatalog: async () => {}, _intgRefreshConnections: async () => {},
    _intgRefreshRequests: async () => {}, chLoadChannels: async () => {}, chLoadMine: async () => {},
    setTimeout(callback) { const id = state.nextTimer++; timers.set(id, callback); return id; },
    clearTimeout(id) { timers.delete(id); },
    async api(url) {
      state.calls.push(url);
      if (state.response) return state.response(url);
      return url.endsWith('/connect')
        ? {status: 'initiated', connect_url: 'https://auth.example.test/start'}
        : {accounts: [{connector: 'gmail', status: 'active'}]};
    },
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('static/integration-hub.js', 'utf8'), ctx);
  return {ctx, state, timers, nodes, run: value => vm.runInContext(value, ctx),
    async tick() {
      assert.equal(timers.size, 1, 'one bounded poll must remain scheduled');
      const [id, callback] = timers.entries().next().value;
      timers.delete(id); await callback();
    }};
}

(async () => {
  const hidden = harness();
  await hidden.run('_connectHosted({slug:"gmail"}, {disabled:false})');
  hidden.ctx.document.hidden = true;
  await hidden.tick();
  assert.equal(hidden.state.calls.filter(url => url.endsWith('/accounts')).length, 0);
  assert.equal(hidden.timers.size, 1, 'switching to OAuth must not permanently stop account polling');
  hidden.ctx.document.hidden = false;
  hidden.state.popups[0].close();
  await hidden.tick();
  assert.equal(hidden.state.calls.filter(url => url.endsWith('/accounts')).length, 1);
  assert.equal(hidden.run('_hostedAccounts[0].status'), 'active');
  assert.equal(hidden.timers.size, 0, 'closed OAuth window gets one final refresh');

  for (const reject of [false, true]) {
    const stale = harness();
    let settle;
    stale.state.response = () => new Promise((resolve, fail) => { settle = reject ? fail : resolve; });
    const connect = stale.run('_connectHosted({slug:"gmail"}, {disabled:false})');
    await stale.run('switchIntegrationTab("channels")');
    stale.ctx.$('hostedActionStatus').textContent = 'current tab status';
    settle(reject ? new Error('old failure') : {connect_url: 'https://auth.example.test/old'});
    await connect;
    assert.equal(stale.ctx.$('hostedActionStatus').textContent, 'current tab status');
    assert.equal(stale.ctx.$('hostedActionStatus').children.length, 0);
    assert.equal(stale.timers.size, 0);
    assert.equal(stale.state.popups[0].closed, true);
  }

  const inflight = harness();
  await inflight.run('_connectHosted({slug:"gmail"}, {disabled:false})');
  let finish;
  inflight.state.response = () => new Promise(resolve => { finish = resolve; });
  const polling = inflight.tick();
  await inflight.run('switchIntegrationTab("channels")');
  finish({accounts: [{connector: 'gmail', status: 'active'}]});
  await polling;
  assert.equal(inflight.run('_hostedAccounts.length'), 0);
  assert.equal(inflight.timers.size, 0, 'stale poll must not rearm after navigation');
})().catch(error => { console.error(error); process.exitCode = 1; });
