import fs from 'node:fs';
import path from 'node:path';
import {test, expect, open, auth, api, capture} from './fixtures';

// Registry/archive HTTP is an explicit loopback fixture. Installation, hashing,
// extraction, official extension injection, browser storage and proxy are real.
const local = 'qa-local-extension', peer = 'qa-peer-extension';
const extensionRoot = path.join(path.dirname(auth.workspace), 'state', 'extensions');
const state = path.dirname(extensionRoot);
const fixture = auth.extension_fixture;
const defaults = {enabled:false,label:'initial',ratio:1.5,count:2,mode:'compact'};
const changed = {enabled:true,label:'QA <b>literal</b> "quoted"',ratio:2.75,count:7,mode:'full'};
function activate() { fs.writeFileSync(fixture.activation_file, 'synthetic extension transport only\n'); }
async function extensions(page:any, tab='gallery') {
  await open(page, 'settings');
  await page.locator('[data-settings-section="extensions"]').click();
  await page.locator(`[data-extensions-tab="${tab}"]`).click();
}
function row(page:any,id=local) { return page.locator(`#extensionsInstalled [data-extension-id="${id}"]`); }
function runtime(page:any,id=local) { return page.locator(`#${id}-runtime`); }
async function runtimeRead(page:any,id:string,caption:string) {
  await runtime(page,id).getByRole('button',{name:caption,exact:true}).click();
  return JSON.parse(await page.locator(`#${id}-result`).innerText());
}
async function mutation(page:any,url:string,locator:any,status=200) {
  const response=page.waitForResponse((r:any)=>r.url().endsWith(url)&&r.request().method()==='POST');
  await locator.click(); const r=await response; expect(r.status(),await r.text()).toBe(status); return r;
}
async function install(page:any,id:string) {
  await mutation(page,'/api/extensions/install',page.locator(`[data-ext-install-id="${id}"]`));
  await expect(page.locator(`[data-ext-uninstall-id="${id}"]`)).toBeVisible();
  const data=(await api(page,'/api/extensions/status')).body;
  expect(Object.keys(data.gallery_installed)).toContain(id);
  expect(fs.existsSync(path.join(extensionRoot,id,'app.js'))).toBe(true);
}
async function uninstall(page:any,id:string) {
  await extensions(page);
  await mutation(page,'/api/extensions/uninstall',page.locator(`[data-ext-uninstall-id="${id}"]`));
  await expect(page.locator(`[data-ext-install-id="${id}"]`)).toBeVisible();
  expect(fs.existsSync(path.join(extensionRoot,id))).toBe(false);
}
async function cleanup(page:any,context:any) {
  await context.addCookies([{name:auth.cookie_name,value:auth.cookies.admin,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
  await extensions(page);
  const installed=Object.keys((await api(page,'/api/extensions/status')).body.gallery_installed);
  for(const id of [local,peer]) if(installed.includes(id)) await uninstall(page,id);
  fs.rmSync(fixture.activation_file,{force:true});
  // Deactivation clears only the fixture catalog transport cache.
  await api(page,'/api/extensions/registry');
}

test('SUPPLEMENT EXTENSION local archive install verifies checksum and rejects nonadmin lifecycle mutations without state changes', async({page,context},info)=>{
  test.setTimeout(90000); activate();
  try {
    await extensions(page);
    await mutation(page,'/api/extensions/install',page.locator('[data-ext-install-id="qa-bad-checksum"]'),400);
    await expect(page.locator('#toast')).toContainText('SHA-256 mismatch');
    expect(fs.existsSync(path.join(extensionRoot,'qa-bad-checksum'))).toBe(false);
    await expect(page.locator('[data-ext-install-id="qa-bad-checksum"]')).toBeEnabled();
    await install(page,local);
    const before=fs.readFileSync(path.join(state,'extension-install-manifest.json'),'utf8');
    await context.addCookies([{name:auth.cookie_name,value:auth.cookies.alice,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
    await open(page,'settings'); await expect(page.locator('[data-settings-section="extensions"]')).toBeHidden();
    const requests:[string,any?][]=[['/api/extensions/status'],['/api/extensions/registry'],
      ['/api/extensions/toggle',{id:local,enabled:false}],
      ['/api/extensions/sidecar-proxy-consent',{id:local,approved:true}],
      ['/api/extensions/uninstall',{id:local}],
      ['/api/extensions/install',{id:'qa-forbidden',download_url:'https://hermes-webui.github.io/qa/qa-local-extension.zip',sha256:'0'.repeat(64)}],
      [`/api/extensions/${local}/sidecar/probe`]];
    for(const [url,data] of requests) expect((await api(page,url,data)).status,url).toBe(403);
    expect(fs.readFileSync(path.join(state,'extension-install-manifest.json'),'utf8')).toBe(before);
    expect(fs.existsSync(path.join(extensionRoot,local,'app.js'))).toBe(true);
    expect(fs.existsSync(path.join(extensionRoot,'qa-forbidden'))).toBe(false);
    expect(JSON.parse(fs.readFileSync(path.join(fixture.artifacts,'sidecar-calls.json'),'utf8'))).toEqual([]);
    await capture(page,'extension-member-denials',info);
  } finally { await cleanup(page,context); }
});

test('SUPPLEMENT EXTENSION loaded local settings reset storage isolation sidecar consent revoke disable enable and uninstall persist through reload', async({page,context},info)=>{
  test.setTimeout(150000); activate();
  try {
    await extensions(page); await install(page,local); await install(page,peer);
    await expect(runtime(page)).toHaveCount(0); // Install requests a real reload.
    await extensions(page,'installed'); await expect(runtime(page)).toBeVisible();
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(defaults);
    const current=row(page);
    await current.locator('[data-extension-setting-input="enabled"]').check();
    await current.locator('[data-extension-setting-input="label"]').fill(changed.label);
    await current.locator('[data-extension-setting-input="ratio"]').fill(String(changed.ratio));
    await current.locator('[data-extension-setting-input="count"]').fill(String(changed.count));
    await current.locator('[data-extension-setting-input="mode"]').selectOption(changed.mode);
    await current.getByRole('button',{name:'Save settings',exact:true}).click();
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(changed);
    await extensions(page,'installed');
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(changed);
    await expect(row(page).locator('[data-extension-setting-input="label"]')).toHaveValue(changed.label);
    await row(page).locator('[data-extension-setting-input="count"]').fill('');
    await row(page).getByRole('button',{name:'Save settings',exact:true}).click();
    await expect(page.locator('#toast')).toContainText('invalid values');
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(changed);
    for(const id of [local,peer]) await runtime(page,id).getByRole('button',{name:'Store QA data',exact:true}).click();
    await row(page).getByRole('button',{name:'Reset settings',exact:true}).click();
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(defaults);
    expect(await runtimeRead(page,local,'Read QA data')).toEqual({record:'QA_OWNED_'+local});
    await row(page).getByRole('button',{name:'Clear extension storage',exact:true}).click();
    expect(await runtimeRead(page,local,'Read QA data')).toEqual({});
    expect(await runtimeRead(page,peer,'Read QA data')).toEqual({record:'QA_OWNED_'+peer});
    await extensions(page,'installed');
    expect(await runtimeRead(page,local,'Read QA settings')).toEqual(defaults);
    expect(await runtimeRead(page,local,'Read QA data')).toEqual({});
    expect(await runtimeRead(page,peer,'Read QA data')).toEqual({record:'QA_OWNED_'+peer});
    // This browser's settings were never written to the server settings file.
    expect(fs.readFileSync(path.join(state,'settings.json'),'utf8')).not.toContain('QA <b>literal');
    await runtime(page).getByRole('button',{name:'Call QA sidecar',exact:true}).click();
    await expect(page.locator(`#${local}-result`)).toContainText('"status":403');
    expect(JSON.parse(fs.readFileSync(path.join(fixture.artifacts,'sidecar-calls.json'),'utf8'))).toEqual([]);
    await page.locator('[data-extensions-tab="diagnostics"]').click();
    await expect(page.locator('.extension-sidecar-status-healthy')).toHaveText('healthy');
    await mutation(page,'/api/extensions/sidecar-proxy-consent',page.locator(`[data-extension-sidecar-proxy-id="${local}"]`));
    await runtime(page).getByRole('button',{name:'Call QA sidecar',exact:true}).click();
    await expect(page.locator(`#${local}-result`)).toContainText('"status":200');
    // The real extension intentionally supplied a forged mixed-case token.
    // A valid sidecar token proves the proxy replaced it with its own secret.
    const calls=JSON.parse(fs.readFileSync(path.join(fixture.artifacts,'sidecar-calls.json'),'utf8'));
    expect(calls).toEqual([{token_valid:true,cookie_forwarded:false,authorization_forwarded:false}]);
    const token=path.join(state,'sidecar-auth',local+'.token'); expect(fs.statSync(token).mode&0o777).toBe(0o600);
    await extensions(page,'diagnostics');
    await expect(page.locator(`[data-extension-sidecar-proxy-id="${local}"]`)).toHaveText('Revoke proxy consent');
    await mutation(page,'/api/extensions/sidecar-proxy-consent',page.locator(`[data-extension-sidecar-proxy-id="${local}"]`));
    await runtime(page).getByRole('button',{name:'Call QA sidecar',exact:true}).click();
    await expect(page.locator(`#${local}-result`)).toContainText('"status":403');
    expect(JSON.parse(fs.readFileSync(path.join(fixture.artifacts,'sidecar-calls.json'),'utf8'))).toEqual(calls);
    await mutation(page,'/api/extensions/toggle',page.locator(`#extensionsDiagnostics [data-extension-toggle-id="${local}"]`));
    await extensions(page,'diagnostics'); await expect(runtime(page)).toHaveCount(0); await expect(runtime(page,peer)).toBeVisible();
    await expect(page.locator(`#extensionsDiagnostics [data-extension-toggle-id="${local}"]`)).toHaveText('Enable');
    await mutation(page,'/api/extensions/toggle',page.locator(`#extensionsDiagnostics [data-extension-toggle-id="${local}"]`));
    await extensions(page,'installed'); await expect(runtime(page)).toBeVisible();
    expect(await runtimeRead(page,peer,'Read QA data')).toEqual({record:'QA_OWNED_'+peer});
    await capture(page,'extension-reloaded-lifecycle',info);
    await uninstall(page,local); await uninstall(page,peer); await extensions(page);
    await expect(runtime(page)).toHaveCount(0); await expect(runtime(page,peer)).toHaveCount(0);
    for(const id of [local,peer]) expect((await page.request.get(`/extensions/${id}/app.js`)).status()).toBe(404);
    const installState=JSON.parse(fs.readFileSync(path.join(state,'extension-install-manifest.json'),'utf8'));
    expect(installState.installed).toEqual({});
  } finally { await cleanup(page,context); }
});
