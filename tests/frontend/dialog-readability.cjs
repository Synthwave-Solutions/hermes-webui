// Exercise shared dialog renderers with synthetic data; never touch real accounts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(process.env.DIALOG_SOURCE || path.join(__dirname, '../..'));
const read = file => fs.readFileSync(path.join(root, 'static', file), 'utf8');
const output = process.env.SYNTHPULSE_QA_OUTPUT;
const issues = [], results = [];

async function inspect(page, name, selector, mode, width, geometry = true) {
  const dialog = page.locator(selector);
  await dialog.waitFor({state: 'visible'});
  const measure = el => {
    const rgb = color => color.match(/[\d.]+/g).map(Number);
    const over = (fg, bg) => fg.slice(0, 3).map((v, i) => v * (fg[3] ?? 1) + bg[i] * (1 - (fg[3] ?? 1)));
    const lum = c => c.map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
      .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const contrast = node => {
      let backgrounds = [[255, 255, 255]];
      const ancestors = [];
      for (let n = node; n; n = n.parentElement) ancestors.unshift(n);
      for (const n of ancestors) {
        const css = getComputedStyle(n);
        backgrounds = backgrounds.map(bg => over(rgb(css.backgroundColor), bg));
        if (css.backgroundImage.startsWith('linear-gradient(')) {
          const stops = css.backgroundImage.match(/rgba?\([^)]+\)/g) || [];
          if (stops.length) backgrounds = backgrounds.flatMap(bg => stops.map(stop => over(rgb(stop), bg)));
        }
      }
      return Math.min(...backgrounds.map(bg => {
        const fg = over(rgb(getComputedStyle(node).color), bg);
        const [a, b] = [lum(fg), lum(bg)].sort((a, b) => b - a);
        return (a + .05) / (b + .05);
      }));
    };
    const visible = node => node.getClientRects().length && !node.disabled;
    const text = [...el.querySelectorAll('h2,h3,p,label,input,select,textarea,button,.app-dialog-title,.app-dialog-desc,.ch-hint,pre')]
      .filter(visible).map(node => ({tag: node.tagName, text: (node.textContent || node.placeholder || '').trim().slice(0, 42), ratio: contrast(node)}));
    const rect = el.getBoundingClientRect();
    return {centered: Math.abs(rect.x + rect.width / 2 - innerWidth / 2) < 2,
      fits: rect.x >= 8 && rect.y >= 8 && rect.right <= innerWidth - 8 && rect.bottom <= innerHeight - 8,
      overflow: el.scrollWidth > el.clientWidth, text};
  };
  const report = await dialog.evaluate(measure);
  const height = page.viewportSize().height;
  if (output) await dialog.screenshot({path: path.join(output, `${mode}-${width}x${height}-${name}.png`)});
  const prefix = `${mode}/${width}/${name}`;
  if (geometry && !report.centered) issues.push(prefix + ': not centered');
  if (geometry && (!report.fits || report.overflow)) issues.push(prefix + ': exceeds viewport');
  for (const item of report.text) if (item.ratio < 4.5) issues.push(`${prefix}: ${item.tag} ${item.text} contrast ${item.ratio.toFixed(2)}`);
  for (const button of await dialog.locator('button.primary,button.confirm,button.memdash-btn-primary,button.sp-guide-primary,button.sp-help-btn-primary,button.guida-next').all()) {
    if (!(await button.isVisible()) || await button.isDisabled()) continue;
    await button.hover();
    const hovered = await dialog.evaluate(measure);
    for (const item of hovered.text) if (item.ratio < 4.5) issues.push(`${prefix}: hover ${item.tag} ${item.text} contrast ${item.ratio.toFixed(2)}`);
  }
  results.push({name, mode, width, ...report});
}

(async () => {
  if (output) fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  try {
    for (const mode of ['light', 'dark']) for (const [width, height] of [[1440, 900], [900, 720], [390, 844], [390, 360]]) {
      const page = await browser.newPage({viewport: {width, height}});
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', route => route.abort());
      const index = read('index.html');
      const appDialog = index.slice(index.indexOf('<div class="app-dialog-overlay"'), index.indexOf('<div class="toast"'));
      const screen = read('bot-screens.html').match(/<dialog[\s\S]*?<\/dialog>/)[0];
      await page.setContent(`<!doctype html><html class="${mode === 'dark' ? 'dark' : ''}"><head><base href="https://example.test/"></head><body><button id="opener">Open</button><div id="projSections"></div><div id="profileDetailTitle"></div><div id="profileDetailEmpty"></div><div id="profileDetailBody"></div><button id="btnSaveProfileDetail"></button><div id="memoryFixture"></div>${appDialog}${screen}</body></html>`);
      for (const file of ['style.css', 'bot-builder.css', 'memory_dashboard.css', 'bot-screens.css', 'help-guide.css', 'help-tour.css', 'workspace-clarity.css']) await page.addStyleTag({path: path.join(root, 'static', file)});
      await page.addStyleTag({content: '*,*::before,*::after{transition:none!important;animation:none!important}'});
      await page.evaluate(() => {
        window.$ = id => document.getElementById(id);
        window.esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        window.__registerHermesLocale = (_, values) => { window.locale = values; };
        window.t = (key, ...args) => typeof locale?.[key] === 'function' ? locale[key](...args)
          : String(locale?.[key] || key).replace(/\{(\d+)\}/g, (_, n) => args[n] ?? '');
        window.posts = [];
        window.api = async (url, opts = {}) => {
          if (opts.method === 'POST') { posts.push({url, body: JSON.parse(opts.body)}); return {ok: true}; }
          if (url === '/api/projects/folders/config') return {enabled: true};
          if (url.startsWith('/api/projects/folders?')) return {can_manage: true, folders: []};
          if (url === '/api/workspaces') return {workspaces: [{name: 'Example project', path: '/example/project'}]};
          if (url.startsWith('/api/profiles?')) return {profiles: [{name: 'assistant', bot: {title: 'Assistant'}}]};
          if (url === '/api/me/sidebar-organization') return {revision: 1, sections: [], assignments: {}, task_categories: {}};
          if (url.startsWith('/api/rollback/diff')) return {total_changes: 1, files_changed: [{file: 'example.txt', status: 'modified'}], diff: '- Before\n+ After'};
          return {can_edit: true, catalog: {}, config: {name: 'assistant', revision: 1, bot: {title: 'Assistant'}}};
        };
        window.fetch = async () => new Response(JSON.stringify({enabled: true, available: true, me: 'own', stores: [{ref: 'own', own: true, owner: 'You'}, {ref: 'other', own: false, owner: 'Example colleague'}]}), {status: 200});
        window._profileMode = ''; window._currentProfileDetail = null; window._botJobsCache = null;
        window._setProfileHeaderButtons = () => {}; window.switchPanel = () => {};
        window._profileDropdownClearStoredCache = () => {}; window.loadProfilesPanel = async () => {};
        window.openProfileDetail = () => {}; window.showToast = () => {};
        window._loadProfileBotJobs = async () => {};
        window._botJobsAll = async () => [{id:'example-task', name:'Weekly summary', owner_email:'alex@example.test', bot:'other'}];
        window._cronCanChangeBot = () => true; window._cronJobBotName = j => j.bot; window._cronOwnerProfileName = () => 'default';
      });
      const helpers = read('i18n.js');
      await page.addScriptTag({content: helpers.slice(helpers.indexOf('function _i18nProcessedElapsed('), helpers.indexOf('window.__registerHermesLocale='))});
      await page.addScriptTag({path: path.join(root, 'static/i18n/en.js')});
      for (const file of ['integrations.js', 'sidebar-organization.js', 'projects-folders.js', 'bot-builder.js', 'memory_dashboard.js']) await page.addScriptTag({path: path.join(root, 'static', file)});
      const ui = read('ui.js');
      await page.addScriptTag({content: ui.slice(ui.indexOf('const APP_DIALOG='), ui.indexOf('function _copyText('))});
      const panels = read('panels.js');
      await page.addScriptTag({content: panels.slice(panels.indexOf('async function _viewCheckpointDiff('), panels.indexOf('async function _restoreCheckpoint('))});

      // Shared control families used by page forms, governance and guided help.
      await page.evaluate(() => {
        const samples = document.createElement('section'); samples.id = 'controlSamples'; samples.className = 'main-view-body';
        samples.innerHTML = '<button class="sm-btn primary">Save changes</button><button class="gov-btn primary">Approve</button><div class="sp-help-tooltip"><button class="guida-next">Next step</button></div><button class="sp-help-btn-primary">Start tour</button><div class="sp-feature-guide" style="width:auto;height:auto"><button class="sp-guide-primary">Show me how</button></div><p class="intg-error">Could not connect. Please try again.</p><p class="intg-banner">This connection needs attention.</p>';
        document.body.append(samples);
      });
      await inspect(page, 'controls', '#controlSamples', mode, width, false);
      if (width === 1440) for (const skin of ['graphite', 'charizard']) {
        await page.evaluate(skin => { document.documentElement.dataset.skin = skin; }, skin);
        // Audit filled actions separately from existing custom-skin feedback colors.
        await page.locator('#controlSamples p').evaluateAll(nodes => nodes.forEach(node => { node.hidden = true; }));
        await inspect(page, 'controls-' + skin, '#controlSamples', mode, width, false);
      }
      await page.evaluate(() => { document.documentElement.removeAttribute('data-skin'); });
      await page.locator('#controlSamples').evaluate(el => el.remove());

      await page.evaluate(() => { void _intgCredentialDialog({display_name: 'Connect app'}, ['client_id', 'client_secret'], {scopes: true}); });
      await inspect(page, 'connector', 'dialog.app-dialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(() => {
        _chState = {platforms: [{key: 'example', label: 'Connect channel', summary: 'Connect a messaging channel.', fields: [{key: 'token', label: 'Access token', secret: true, hint: 'Enter the token from your provider.'}]}]};
        chOpenConfigure('example');
      });
      await inspect(page, 'channel', 'dialog.ch-dialog', mode, width);
      await page.locator('dialog.ch-dialog .app-dialog-btn').first().click();
      await page.evaluate(() => SpProjectFolders.afterDetail({project_id: 'example'}));
      await page.locator('.sp-folder-add').click();
      await inspect(page, 'folder', 'dialog.sp-folder-dialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(() => SynthPulseSidebarOrg.moveChat({session_id: 'example-chat'}));
      await inspect(page, 'section', 'dialog.sidebar-org-dialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(() => BotBuilder.open('assistant', 'tasks'));
      await page.locator('#builderAssignTask').click();
      await inspect(page, 'task', 'dialog.bot-task-dialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(async () => { const provider = SynthPulseMemoryExtensions[0]; await provider.sections(); provider.render('memdash_explorer', {body: $('memoryFixture')}); });
      await page.locator('#memdashPicker').selectOption('other');
      await inspect(page, 'memory', 'dialog.memdash-dialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(() => { document.body.classList.add('screen-page'); $('confirmTitle').textContent = 'Control bot screen'; $('confirmText').textContent = 'Confirm that you want to take control.'; $('cancel').textContent = 'Cancel'; $('confirm').textContent = 'Confirm'; $('confirmDialog').showModal(); });
      await inspect(page, 'screen', '#confirmDialog', mode, width);
      await page.keyboard.press('Escape');
      await page.evaluate(() => { document.body.classList.remove('screen-page'); void showPromptDialog({title: 'Rename conversation', message: 'Choose a name you can recognize.', value: 'Example chat'}); });
      await inspect(page, 'prompt', '#appDialog', mode, width);
      await page.keyboard.press('Escape');
      try {
        await page.evaluate(() => _viewCheckpointDiff('/example/project', 'example-checkpoint'));
        await inspect(page, 'checkpoint', '#checkpointDiffModal > div', mode, width);
        assert.equal(await page.locator('#checkpointDiffModal pre').textContent(), '- Before\n+ After');
        await page.locator('#checkpointDiffModal button').click();
        await page.evaluate(() => _viewCheckpointDiff('/example/project', 'example-checkpoint'));
        assert.equal(await page.locator('#checkpointDiffModal').count(), 1, 'reopening reuses the dialog');
        assert.ok(await page.locator('#checkpointDiffModal').isVisible());
      } catch (error) { issues.push(`${mode}/${width}/checkpoint: ${error.message.split('\n')[0]}`); }
      assert.deepEqual(await page.evaluate(() => posts), [], 'opening and cancelling dialogs never mutates accounts/tasks/access');
      assert.deepEqual(errors, [], 'no uncaught browser errors');
      await page.close();
    }
    if (output) fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify({issues, results}, null, 2));
    console.log(JSON.stringify({cases: results.length, issues}, null, 2));
    assert.deepEqual(issues, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
