// Isolated rendered-click regression. Requires an existing Playwright install:
// NODE_PATH=/path/to/node_modules node scripts/test-artifact-download-browser.cjs
// Optional: ARTIFACT_QA_OUTPUT=/path/to/evidence, ARTIFACT_QA_BROWSER=firefox|webkit
// Uses fixture bytes and a loopback HTTP server only; no real user state.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const crypto = require('node:crypto');
const {once} = require('node:events');

async function main() {
  const root = path.resolve(__dirname, '..');
  const output = process.env.ARTIFACT_QA_OUTPUT || await fs.mkdtemp(path.join(os.tmpdir(), 'synthpulse-download-qa-'));
  await fs.mkdir(output, {recursive: true});
  const source = await fs.readFile(process.env.ARTIFACT_QA_SOURCE || path.join(root, 'static/workspace.js'));
  const locale = await fs.readFile(path.join(root, 'static/i18n/en.js'), 'utf8');
  const messages = Object.fromEntries([...locale.matchAll(/(artifact_download_\w+): '([^']+)'/g)].map(m => [m[1], m[2]]));
  const artifacts = [
    {name: 'Interactive report é ✓.html', mime: 'text/html', bytes: Buffer.from('<!doctype html><title>Artifact fixture</title><p>Exact HTML bytes ✓</p>')},
    {name: 'Report é.pdf', mime: 'application/pdf', bytes: Buffer.from('%PDF-1.4\n% SynthPulse fixture\n%%EOF\n')},
    {name: 'Diagram é.png', mime: 'image/png', bytes: Buffer.from('89504e470d0a1a0a', 'hex')},
    {name: 'Source é.zip', mime: 'application/zip', bytes: Buffer.from('504b0506000000000000000000000000000000000000', 'hex')},
  ];
  let mode = 'ok';
  const requests = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/workspace.js') { res.setHeader('Content-Type', 'application/javascript'); return res.end(source); }
    if (url.pathname.startsWith('/api/')) {
      requests.push({path: url.pathname, download: url.searchParams.get('download'), inline: url.searchParams.get('inline'), authenticated: req.headers.cookie === 'fixture_auth=yes'});
      if (mode === 'network') return req.socket.destroy();
      if (mode === 'redirect') { res.writeHead(302, {Location: '/login'}); return res.end(); }
      if (!req.headers.cookie) { res.writeHead(401); return res.end('Authentication required'); }
      if (mode !== 'ok') {
        res.writeHead(mode === 'login200' ? 200 : Number(mode), {'Content-Type': 'text/html'});
        return res.end('<title>Unavailable/login fixture</title>');
      }
      const artifact = artifacts[Number(url.searchParams.get('item'))];
      assert.equal(url.searchParams.get('download'), '1');
      assert.equal(url.searchParams.has('inline'), false);
      res.writeHead(200, {'Content-Type': artifact.mime, 'Content-Disposition': `attachment; filename="fallback"; filename*=UTF-8''${encodeURIComponent(artifact.name)}`});
      return res.end(artifact.bytes);
    }
    if (url.pathname !== '/') { res.writeHead(404); return res.end(); }
    if (url.searchParams.has('mode')) mode = url.searchParams.get('mode');
    res.setHeader('Set-Cookie', url.searchParams.get('signedout') === '1' ? 'fixture_auth=; Max-Age=0; HttpOnly; SameSite=Lax' : 'fixture_auth=yes; HttpOnly; SameSite=Lax');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SynthPulse download QA fixture</title>
      <style>body{font:16px system-ui;background:#10151c;color:#eee;margin:24px}a,button{display:inline-block;padding:12px;margin:8px;color:#90caf9;background:#202a37;border:1px solid #607080;border-radius:6px}#toast{padding:16px;max-width:640px;overflow-wrap:anywhere}#toast[data-level="error"]{border:1px solid #ee5577}</style>
      <h1>SynthPulse artifact download QA</h1><p>Isolated fixture. No user data.</p>
      <nav>${['ok','404','403','500','login200','redirect','network'].map(value => `<a href="/?mode=${value}">${value} fixture</a>`).join('')}<a href="/?mode=ok&signedout=1">Signed out fixture</a></nav>
      ${artifacts.map((a,i) => `<a class="msg-media-link" href="/api/media?item=${i}&inline=1" download="Friendly caption">Download ${a.name}</a>`).join('')}
      <button id="raw" onclick="downloadArtifact('/api/file/raw?item=0&inline=1','Friendly caption')">Workspace download</button>
      <button id="escape" onclick="downloadArtifact('/api/escape/file/raw?item=0&inline=1','Friendly caption')">Authorized external download</button>
      <div id="toast" role="status"></div><script>
      const $=id=>document.getElementById(id);const S={session:{session_id:'fixture'}};
      const copy=${JSON.stringify(messages)};
      const t=(key,name)=>copy[key]||(key==='downloading'?'Downloading '+name:key);
      const showToast=(text,duration,level)=>{const el=$('toast');el.textContent=text;el.dataset.level=level||'info'};
      </script><script src="/workspace.js"></script>`);
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  if (process.argv.includes('--serve-only')) {
    console.log(JSON.stringify({status: 'FIXTURE_READY', url: base, output}));
    return;
  }
  const browsers = require('playwright');
  const browserName = process.env.ARTIFACT_QA_BROWSER || 'chromium';
  let browser;
  const evidence = {browser: browserName, source_sha256: crypto.createHash('sha256').update(source).digest('hex'), saves: [], errors: []};
  try {
    browser = await browsers[browserName].launch({headless: true});
    for (const width of [1440, 390]) {
      const context = await browser.newContext({viewport: {width, height: 900}, acceptDownloads: true});
      await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
      await context.addCookies([{name: 'fixture_auth', value: 'yes', url: base, httpOnly: true}]);
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base);
      let downloads = 0;
      page.on('download', () => downloads++);
      for (let i = 0; i < artifacts.length + 2; i++) {
        mode = 'ok';
        const artifact = artifacts[i < artifacts.length ? i : 0];
        const pending = page.waitForEvent('download');
        if (i < artifacts.length) await page.locator('a[download]').nth(i).click();
        else await page.locator(i === 4 ? '#raw' : '#escape').click();
        const download = await pending;
        assert.equal(download.suggestedFilename(), artifact.name);
        const saved = path.join(output, `${width}-${i}-${artifact.name}`);
        await download.saveAs(saved);
        assert.equal(await download.failure(), null);
        const bytes = await fs.readFile(saved);
        assert.deepEqual(bytes, artifact.bytes);
        evidence.saves.push({width, name: artifact.name, sha256: crypto.createHash('sha256').update(bytes).digest('hex')});
      }
      for (const failure of ['404', '403', '500', 'login200', 'redirect', 'network', 'signedout']) {
        mode = failure === 'signedout' ? 'ok' : failure;
        if (failure === 'signedout') await context.clearCookies();
        await page.locator('#toast').evaluate(el => { el.textContent = ''; delete el.dataset.level; });
        const count = downloads;
        await page.locator('a[download]').first().click();
        await page.locator('#toast[data-level="error"]').waitFor();
        assert.equal(downloads, count, `${failure} must not save a browser error page`);
        const message = await page.locator('#toast').innerText();
        if (failure === '404') assert.match(message, /regenerate and attach/);
        if (failure === 'login200') assert.match(message, /did not return a downloadable file/);
        evidence.errors.push({width, failure, message});
        if (failure === '404') await page.screenshot({path: path.join(output, `missing-${width}.png`), fullPage: true});
      }
      assert.deepEqual(errors, []);
      await context.close();
    }
    assert(requests.filter(r => r.authenticated).length >= 12);
    assert(requests.every(r => r.download === '1' && r.inline === null));
    evidence.status = 'PASS';
    await fs.writeFile(path.join(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify({status: evidence.status, browser: browserName, saved_files: evidence.saves.length, failed_downloads_blocked: evidence.errors.length, output}));
  } finally {
    if (browser) await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
