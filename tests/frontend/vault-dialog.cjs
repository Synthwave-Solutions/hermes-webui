// Real vault renderer + styles; synthetic accounts only, with all network blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(process.env.VAULT_SOURCE || path.join(__dirname, '../..'));
const output = process.env.SYNTHPULSE_QA_OUTPUT;

// Compute rendered text contrast, including translucent ancestor backgrounds.
async function contrast(locator, pseudo = null) {
  return locator.evaluate((node, pseudo) => {
    const rgb = color => color.match(/[\d.]+/g).map(Number);
    const over = (fg, bg) => fg.slice(0, 3).map((v, i) => v * (fg[3] ?? 1) + bg[i] * (1 - (fg[3] ?? 1)));
    let bg = [255, 255, 255];
    const ancestors = [];
    for (let el = node; el; el = el.parentElement) ancestors.unshift(el);
    for (const el of ancestors) bg = over(rgb(getComputedStyle(el).backgroundColor), bg);
    const fg = over(rgb(getComputedStyle(node, pseudo).color), bg);
    const luminance = color => color.map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const [a, b] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
    return (a + .05) / (b + .05);
  }, pseudo);
}

(async () => {
  if (output) fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    page.setDefaultTimeout(5000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => route.abort());
    await page.setContent('<!doctype html><html><body><main style="padding:32px"><h1>Connections</h1><p>App connectors · Plugins · Password vault</p><button id="opener" type="button">Add login</button></main><div id="vaultStatus"></div><div id="vaultSources"></div><div id="vaultItems"></div></body></html>');
    for (const file of ['style.css', 'workspace-clarity.css']) await page.addStyleTag({path: path.join(root, 'static', file)});
    await page.evaluate(() => {
      window.$ = id => document.getElementById(id);
      window._intgT = (_, fallback) => fallback;
      window.calls = [];
      window.api = async (url, options = {}) => {
        if (options.method !== 'POST') return {sources: [], items: []};
        calls.push({url, body: JSON.parse(options.body)});
        // The renderer must empty secret inputs before any request leaves it.
        if ([...document.querySelectorAll('#vaultDialog input')].some(input => input.value)) throw Error('Form was not cleared');
        return new Promise(resolve => { window.completeRequest = resolve; });
      };
    });
    for (const file of ['integration-hub.js', 'vault.js']) await page.addScriptTag({path: path.join(root, 'static', file)});
    await page.evaluate(() => document.getElementById('opener').addEventListener('click', openVaultLogin));
    const modes = ['light', 'dark'];
    let lowestContrast = Infinity;
    for (const mode of modes) {
      await page.evaluate(mode => document.documentElement.classList.toggle('dark', mode === 'dark'), mode);
      for (const [width, height] of [[1440, 900], [900, 720], [390, 844], [320, 568], [390, 360]]) {
        await page.setViewportSize({width, height});
        await page.locator('#opener').click();
        const dialog = page.getByRole('dialog');
        if (output && height !== 360) await page.screenshot({path: path.join(output, `${mode}-${width}.png`)});
        const text = dialog.locator('h2, p, label, input, select, button');
        for (const node of await text.all()) {
          if (!(await node.isVisible())) continue;
          const ratio = await contrast(node);
          lowestContrast = Math.min(lowestContrast, ratio);
          assert.ok(ratio >= 4.5, `${mode}: ${await node.evaluate(el => el.tagName)} contrast ${ratio.toFixed(2)}:1`);
        }
        assert.ok(await contrast(dialog.locator('[name="origin"]'), '::placeholder') >= 4.5);
        const box = await dialog.boundingBox();
        assert.ok(Math.abs(box.x + box.width / 2 - width / 2) < 2, 'dialog is horizontally centered');
        assert.ok(Math.abs(box.y + box.height / 2 - height / 2) < 2, 'dialog is vertically centered');
        assert.ok(box.x >= 15 && box.y >= 15 && box.y + box.height <= height - 15, 'dialog fits viewport');
        assert.ok(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth), 'no horizontal overflow');
        for (const button of await dialog.getByRole('button').all()) {
          const size = await button.boundingBox();
          assert.ok(size.width >= 44 && size.height >= 44, 'buttons are usable touch targets');
        }
        const close = await dialog.getByRole('button', {name: 'Close', exact: true}).boundingBox();
        const save = await dialog.getByRole('button', {name: 'Save', exact: true}).boundingBox();
        assert.ok(save.x - close.x - close.width >= 8, 'actions have a visible gap');
        assert.equal(await dialog.locator('[name="password"]').getAttribute('type'), 'password');
        assert.equal(await dialog.locator('[name="otp_secret"]').getAttribute('type'), 'password');
        await dialog.getByRole('button', {name: 'Close', exact: true}).click();
        await dialog.waitFor({state: 'detached'});
      }
      await page.setViewportSize({width: 390, height: 844});
      for (const kind of ['bitwarden', 'onepassword', 'unlock']) {
        await page.evaluate(kind => kind === 'unlock' ? openVaultUnlock() : openVaultManager({name: kind, display_name: kind === 'bitwarden' ? 'Bitwarden' : '1Password'}), kind);
        const dialog = page.getByRole('dialog');
        for (const node of await dialog.locator('h2, p, label, input, select, button').all()) {
          if (await node.isVisible()) assert.ok(await contrast(node) >= 4.5, `${mode} ${kind} text contrast`);
        }
        await page.keyboard.press('Escape');
        await dialog.waitFor({state: 'detached'});
      }
    }
    assert.deepEqual(await page.evaluate(() => calls), [], 'open/cancel/Escape never save');
    await page.locator('#opener').click();
    const dialog = page.getByRole('dialog', {name: 'Add login'});
    assert.ok(await dialog.evaluate(el => !!document.getElementById(el.getAttribute('aria-describedby'))?.textContent), 'hint describes the dialog');
    assert.ok(await dialog.locator('[name="label"]').evaluate(el => el === document.activeElement), 'first field receives focus');
    await dialog.getByRole('button', {name: 'Save', exact: true}).click();
    assert.equal(await page.evaluate(() => calls.length), 0, 'required fields block empty saves');
    const fillLogin = async () => {
      for (const [name, value] of Object.entries({label: 'Example', origin: 'https://example.test', identifier: 'alex@example.test', password: 'test-only-password'})) {
        await dialog.locator(`[name="${name}"]`).fill(value);
      }
    };
    await fillLogin();
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => calls.length === 1);
    assert.ok(await dialog.getByRole('button', {name: 'Save', exact: true}).isDisabled());
    assert.equal(await dialog.locator('[name="password"]').inputValue(), '', 'password cleared during save');
    await page.evaluate(() => { completeRequest({ok: true}); });
    await dialog.waitFor({state: 'detached'});
    assert.ok(await page.locator('#opener').evaluate(el => el === document.activeElement), 'focus returns to the opener');
    assert.deepEqual(errors, [], 'no browser errors');
    console.log(JSON.stringify({status: 'passed', modes, viewports: 5, dialogs: 4, minimumTextContrast: Number(lowestContrast.toFixed(2))}));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
