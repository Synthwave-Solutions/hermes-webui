import fs from 'node:fs';
import path from 'node:path';
import type {Browser, Page, TestInfo} from '@playwright/test';
import {test, expect, open, session, api, auth, capture} from './fixtures';

const memberEmail = 'bob@example.test';
const unique = (prefix: string) => `${prefix}-${Date.now()}`;

// A retained second signed-in browser exercises live policy changes. It uses
// the same loopback-only rules and eager error collection as the main fixture.
async function memberBrowser(browser: Browser) {
  const context = await browser.newContext({baseURL: auth.base_url, viewport: {width: 1440, height: 1000}});
  await context.route('**/*', route =>
    ['127.0.0.1', 'localhost', '[::1]'].includes(new URL(route.request().url()).hostname)
      ? route.continue() : route.abort('blockedbyclient'));
  await context.routeWebSocket('**/*', socket => {
    if (['127.0.0.1', 'localhost', '[::1]'].includes(new URL(socket.url()).hostname)) socket.connectToServer();
    else socket.close({code: 1008, reason: 'QA requires loopback networking'});
  });
  await context.addCookies([{name: auth.cookie_name, value: auth.cookies.bob, url: auth.base_url, httpOnly: true, sameSite: 'Lax'}]);
  const actions: any[] = [];
  await context.exposeBinding('__qaRecordMemberAction', (_source, action) => actions.push(action));
  await context.addInitScript(() => {
    const w = window as any;
    w.__qaActions = [];
    for (const event of ['click', 'dblclick', 'change', 'input', 'keydown']) document.addEventListener(event, ev => {
      const el = ev.composedPath().find(node => node instanceof Element && node.matches('button,input,select,textarea,a,[onclick],[role="button"]')) as Element | undefined;
      if (!el) return;
      const action = {event, tag: el.tagName, id: el.id, text: (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim().slice(0, 90), onclick: el.getAttribute('onclick'), panel: el.getAttribute('data-panel'), scope: document.querySelector('.panel-view.active')?.id || 'app', selection: el.getAttribute('data-selection'), value: null};
      w.__qaActions.push(action);
      w.__qaRecordMemberAction(action).catch(() => {});
    }, true);
  });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await open(page);
  return {context, page, errors, actions};
}

async function policy(page: Page) {
  const result = await api(page, '/api/governance/users');
  expect(result.status).toBe(200);
  return result.body.users[memberEmail];
}

async function denyInEditor(page: Page, field: string, value: string, advanced = false) {
  await open(page, 'governance');
  await page.locator('[data-gov-tab="users"]').click();
  await page.locator('#govPaneUsers tr').filter({hasText: memberEmail}).getByRole('button', {name: 'Edit', exact: true}).click();
  await expect(page.locator('#govUserEmail')).toHaveValue(memberEmail);
  if (advanced) await page.locator('details.gov-access-details').nth(1).locator('summary').click();
  const input = page.locator(`#govUserDeny${field}Input`);
  await input.fill(value);
  await input.press('Enter');
  await input.press('Escape');
  const saved = page.waitForResponse(r => r.url().endsWith('/api/governance/users/update') && r.request().method() === 'POST');
  await page.locator('#govUserSave').click();
  expect((await saved).status()).toBe(200);
  await expect(page.locator('#govUserEmail')).toHaveValue('');
}

async function restorePolicy(page: Page, entry: any) {
  const state = await api(page, '/api/governance/users');
  const status = await page.evaluate(async ({entry, etag, email}) => {
    const response = await fetch('/api/governance/users/update', {method: 'POST', headers: {'Content-Type': 'application/json', 'If-Match': etag}, body: JSON.stringify({email, entry})});
    return response.status;
  }, {entry, etag: state.body.etag, email: memberEmail});
  expect(status, 'restore the exact original member policy').toBe(200);
  expect(await policy(page)).toEqual(entry);
}

async function closeMember(member: Awaited<ReturnType<typeof memberBrowser>>, info: TestInfo) {
  await capture(member.page, 'retained-member-final', info);
  await info.attach('retained-member-screen', {body: await member.page.screenshot(), contentType: 'image/png'});
  await info.attach('retained-member-navigation-controls', {body: JSON.stringify({actions: member.actions, controls: []}), contentType: 'application/json'});
  await info.attach('retained-member-browser-errors', {body: JSON.stringify(member.errors), contentType: 'application/json'});
  await member.context.close();
  expect(member.errors, 'retained member uncaught errors').toEqual([]);
}

test('US-SP-AFFORDANCE-FILE-CANCEL Escape discards edited text and exact original bytes survive reopening and reload', async ({page}) => {
  const name = unique('qa-editor-cancel') + '.txt';
  const target = path.join(auth.workspace, name);
  const original = 'Original file stays byte-for-byte.\nUTF-8 café and two final newlines.\n\n';
  fs.writeFileSync(target, original);
  await open(page);
  const sid = await session(page);
  await page.locator('#btnWorkspacePanelToggle').click();
  const row = page.locator('#fileTree .file-item').filter({hasText: name});
  await row.click();
  await expect(page.locator('#previewCode')).toHaveText(original);
  let saves = 0;
  page.on('request', r => { if (r.url().endsWith('/api/file/save') && r.method() === 'POST') saves++; });
  await page.locator('#btnEditFile').click();
  await expect(page.locator('#previewEditArea')).toHaveValue(original);
  await page.locator('#previewEditArea').fill('QA_CANCELLED_CONTENT must never persist.');
  await expect(page.locator('#btnEditFile')).toContainText('Save*');
  await page.locator('#previewEditArea').press('Escape');
  await expect(page.locator('#previewEditArea')).toBeHidden();
  await expect(page.locator('#previewCode')).toHaveText(original);
  await expect(page.locator('#btnEditFile')).toContainText('Edit');
  expect(saves).toBe(0);
  expect(fs.readFileSync(target, 'utf8')).toBe(original);
  const read = await api(page, `/api/file?session_id=${sid}&path=${encodeURIComponent(name)}`);
  expect(read.status).toBe(200);
  expect(read.body.content).toBe(original);
  await page.locator('#btnClearPreview').click();
  await row.click();
  await page.locator('#btnEditFile').click();
  await expect(page.locator('#previewEditArea')).toHaveValue(original);
  await page.locator('#previewEditArea').press('Escape');
  await page.reload();
  await expect(page.locator('#msg')).toBeVisible();
  if (!(await page.locator('#fileTree').isVisible())) await page.locator('#btnWorkspacePanelToggle').click();
  await page.locator('#fileTree .file-item').filter({hasText: name}).click();
  await expect(page.locator('#previewCode')).toHaveText(original);
  expect(fs.readFileSync(target, 'utf8')).toBe(original);
  expect(saves).toBe(0);
});

test('US-SP-AFFORDANCE-SKILL-LINKS linked markdown and Back work while traversal and live revoked access return no new file content', async ({page, browser}, info) => {
  const name = unique('qa-linked-skill');
  await open(page, 'skills');
  const originalPolicy = await policy(page);
  await page.getByRole('button', {name: 'New skill', exact: true}).click();
  await page.locator('#skillFormName').fill(name);
  await page.locator('#skillFormContent').fill(`---\nname: ${name}\ndescription: Linked-file QA\n---\nQA_SKILL_ROOT_ONLY\n`);
  await page.locator('#btnSaveSkillDetail').click();
  await expect(page.locator('#skillDetailTitle')).toHaveText(name);
  const created = await api(page, '/api/skills/content?name=' + encodeURIComponent(name));
  expect(created.status).toBe(200);
  const skillDir = created.body.skill_dir;
  expect(typeof skillDir).toBe('string');
  const references = path.join(skillDir, 'references');
  fs.mkdirSync(references);
  const linkedPath = path.join(references, 'notes.md');
  fs.writeFileSync(linkedPath, '# Linked QA document\n\nQA_LINKED_INITIAL\n');
  const outsidePath = path.join(path.dirname(skillDir), name + '-outside.md');
  fs.writeFileSync(outsidePath, 'QA_OUTSIDE_SKILL_MUST_NOT_LEAK');
  fs.symlinkSync(outsidePath, path.join(references, 'escape.md'));
  const member = await memberBrowser(browser);
  try {
    await member.page.locator('.rail-btn[data-panel="skills"]').click();
    await member.page.locator('.skill-item').filter({has: member.page.locator('.skill-name', {hasText: name})}).click();
    const link = member.page.locator('.skill-linked-file[data-skill-file="references/notes.md"]');
    await expect(link).toBeVisible();
    const linkedRead = member.page.waitForResponse(r => new URL(r.url()).searchParams.get('file') === 'references/notes.md');
    await link.click();
    expect((await linkedRead).status()).toBe(200);
    await expect(member.page.locator('.skill-file-path')).toHaveText('references/notes.md');
    await expect(member.page.locator('#skillDetailBody')).toContainText('QA_LINKED_INITIAL');
    await member.page.locator('.skill-file-back').click();
    await expect(member.page.locator('#skillDetailBody')).toContainText('QA_SKILL_ROOT_ONLY');
    await expect(member.page.locator('.skill-file-path')).toHaveCount(0);
    const escaped = member.page.waitForResponse(r => new URL(r.url()).searchParams.get('file') === 'references/escape.md');
    await member.page.locator('.skill-linked-file[data-skill-file="references/escape.md"]').click();
    const escapedResponse = await escaped;
    expect(escapedResponse.status()).toBe(400);
    expect(await escapedResponse.text()).not.toContain('QA_OUTSIDE_SKILL_MUST_NOT_LEAK');
    await expect(member.page.locator('#skillDetailBody')).not.toContainText('QA_OUTSIDE_SKILL_MUST_NOT_LEAK');
    const traversal = await api(member.page, `/api/skills/content?name=${encodeURIComponent(name)}&file=${encodeURIComponent('../' + path.basename(outsidePath))}`);
    expect(traversal.status).toBe(400);
    expect(JSON.stringify(traversal.body)).not.toContain('QA_OUTSIDE_SKILL_MUST_NOT_LEAK');
    await denyInEditor(page, 'Skills', name);
    expect((await policy(page)).deny.skills.view).toContain(name);
    fs.writeFileSync(linkedPath, '# Changed after authorization was revoked\n\nQA_LINKED_NEW_SECRET\n');
    const denied = member.page.waitForResponse(r => new URL(r.url()).searchParams.get('file') === 'references/notes.md');
    await link.click();
    const deniedResponse = await denied;
    expect(deniedResponse.status()).toBe(403);
    expect(await deniedResponse.text()).not.toContain('QA_LINKED_NEW_SECRET');
    await expect(member.page.locator('#skillDetailBody')).not.toContainText('QA_LINKED_NEW_SECRET');
    expect((await api(member.page, `/api/skills/content?name=${encodeURIComponent(name)}&file=references%2Fnotes.md`)).status).toBe(403);
    await member.page.reload();
    await member.page.locator('.rail-btn[data-panel="skills"]').click();
    await expect(member.page.locator('.skill-name').filter({hasText: name})).toHaveCount(0);
    expect((await api(page, `/api/skills/content?name=${encodeURIComponent(name)}&file=references%2Fnotes.md`)).body.content).toContain('QA_LINKED_NEW_SECRET');
  } finally {
    await restorePolicy(page, originalPolicy);
    await closeMember(member, info);
  }
});

test('US-SP-AFFORDANCE-HIDDEN-FILES persisted hidden-file toggle reveals permitted system files without bypassing a file denial', async ({page, browser}, info) => {
  const name = unique('._qa-visible') + '.txt';
  const protectedName = unique('._qa-protected') + '.txt';
  const protectedPath = path.join(auth.workspace, protectedName);
  fs.writeFileSync(path.join(auth.workspace, name), 'QA_HIDDEN_ALLOWED\n');
  fs.writeFileSync(protectedPath, 'QA_HIDDEN_PROTECTED_SECRET\n');
  await open(page);
  const originalPolicy = await policy(page);
  const member = await memberBrowser(browser);
  try {
    await denyInEditor(page, 'FilesRead', protectedPath, true);
    expect((await policy(page)).deny.files.read_roots).toContain(protectedPath);
    const sid = await session(member.page);
    await member.page.locator('#btnWorkspacePanelToggle').click();
    await member.page.locator('.rightpanel').evaluate(async panel => {
      await Promise.all(panel.getAnimations().map(animation => animation.finished));
    });
    const allowedRow = member.page.locator('#fileTree .file-item').filter({hasText: name});
    const protectedRow = member.page.locator('#fileTree .file-item').filter({hasText: protectedName});
    await expect(member.page.locator('#fileTree')).toContainText('qa-evidence.txt');
    await expect(allowedRow).toHaveCount(0);
    await expect(protectedRow).toHaveCount(0);
    await member.page.locator('#btnWorkspacePrefs').click();
    await expect(member.page.locator('#workspaceShowHiddenFiles')).not.toBeChecked();
    await member.page.locator('#workspaceShowHiddenFiles').check();
    await member.page.keyboard.press('Escape');
    await expect(allowedRow).toBeVisible();
    await expect(protectedRow).toHaveCount(0);
    // The default 300px panel intentionally uses the kebab dot; the text
    // indicator appears only when the panel is wider than 420px.
    await expect(member.page.locator('#workspacePrefsDot')).toBeVisible();
    await allowedRow.click();
    await expect(member.page.locator('#previewCode')).toContainText('QA_HIDDEN_ALLOWED');
    const denied = await api(member.page, `/api/file?session_id=${sid}&path=${encodeURIComponent(protectedName)}`);
    expect(denied.status).toBe(403);
    expect(JSON.stringify(denied.body)).not.toContain('QA_HIDDEN_PROTECTED_SECRET');
    await member.page.locator('#btnClearPreview').click();
    await member.page.reload();
    await expect(member.page.locator('#msg')).toBeVisible();
    if (!(await member.page.locator('#fileTree').isVisible())) await member.page.locator('#btnWorkspacePanelToggle').click();
    await member.page.locator('.rightpanel').evaluate(async panel => {
      await Promise.all(panel.getAnimations().map(animation => animation.finished));
    });
    await expect(allowedRow).toBeVisible();
    await expect(protectedRow).toHaveCount(0);
    await member.page.locator('#btnWorkspacePrefs').click();
    await expect(member.page.locator('#workspaceShowHiddenFiles')).toBeChecked();
    await member.page.locator('#workspaceShowHiddenFiles').uncheck();
    await member.page.keyboard.press('Escape');
    await expect(allowedRow).toHaveCount(0);
    await expect(protectedRow).toHaveCount(0);
    await expect(member.page.locator('#workspacePrefsDot')).toBeHidden();
    expect((await api(member.page, `/api/file?session_id=${sid}&path=${encodeURIComponent(protectedName)}`)).status).toBe(403);
    expect(fs.readFileSync(protectedPath, 'utf8')).toBe('QA_HIDDEN_PROTECTED_SECRET\n');
  } finally {
    await restorePolicy(page, originalPolicy);
    await closeMember(member, info);
  }
});

test('US-SP-AFFORDANCE-MESSAGE-FORK selected message creates an exact persistent prefix and child continuation leaves the private parent unchanged', async ({page}, info) => {
  await open(page);
  const parentId = await session(page);
  const read = async (sid: string) => (await api(page, '/api/session?session_id=' + sid)).body.session;
  const transcript = (messages: any[]) => messages.map(m => ({role: m.role, content: m.content}));
  const acceptedStreams = new Set<string>();
  const sendAccepted = async (sid: string, prompt: string) => {
    await page.locator('#msg').fill(prompt);
    const actionAt = Date.now();
    const readiness: any = {session_id: sid, prompt, action_at_utc: new Date(actionAt).toISOString(), accepted_at_utc: null, action_to_accept_ms: null};
    const started = page.waitForResponse(response => {
      if (new URL(response.url()).pathname !== '/api/chat/start' || response.request().method() !== 'POST') return false;
      const request = response.request().postDataJSON();
      if (request.session_id !== sid || request.message !== prompt) return false;
      const acceptedAt = Date.now();
      readiness.accepted_at_utc = new Date(acceptedAt).toISOString();
      readiness.action_to_accept_ms = acceptedAt - actionAt;
      readiness.status = response.status();
      return true;
    });
    try {
      await page.locator('#btnSend').click();
      const response = await started;
      expect(response.status()).toBe(200);
      const accepted = await response.json();
      readiness.returned_session_id = accepted.session_id;
      readiness.stream_id = accepted.stream_id;
      expect(accepted.session_id).toBe(sid);
      expect(accepted.stream_id).toMatch(/^[0-9a-f]{32}$/);
      expect(acceptedStreams.has(accepted.stream_id)).toBe(false);
      acceptedStreams.add(accepted.stream_id);
    } finally {
      await info.attach('fork-chat-start-readiness-' + prompt, {body: JSON.stringify(readiness), contentType: 'application/json'});
    }
    // The unchanged reply budget starts at accepted dispatch, not a click SLO.
    await expect.poll(() => page.locator('#messages').innerText(), {intervals: [100], timeout: 10000}).toContain('QA_REPLY: ' + prompt);
    await expect(page.locator('#btnSend')).not.toHaveAttribute('aria-label', 'Stop generation');
  };
  for (const prompt of ['QA_FORK_FIRST', 'QA_FORK_LATER']) {
    await sendAccepted(parentId, prompt);
  }
  const parent = await read(parentId);
  const original = transcript(parent.messages);
  expect(original).toEqual([
    {role: 'user', content: 'QA_FORK_FIRST'},
    {role: 'assistant', content: 'DEFAULT QA_REPLY: QA_FORK_FIRST'},
    {role: 'user', content: 'QA_FORK_LATER'},
    {role: 'assistant', content: 'DEFAULT QA_REPLY: QA_FORK_LATER'},
  ]);
  const fork = page.locator('[onclick="forkFromMessage(2)"]');
  await fork.locator('xpath=ancestor::*[contains(@class,"msg-row")][1]').hover();
  const branched = page.waitForResponse(r => r.url().endsWith('/api/session/branch') && r.request().method() === 'POST');
  await fork.click();
  const response = await branched;
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON()).toEqual({session_id: parentId, keep_count: 2});
  const childId = (await response.json()).session_id;
  expect(childId).not.toBe(parentId);
  await expect(page).toHaveURL(new RegExp('/session/' + childId));
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_FORK_FIRST');
  await expect(page.locator('#messages')).not.toContainText('QA_FORK_LATER');
  const child = await read(childId);
  expect(transcript(child.messages)).toEqual(original.slice(0, 2));
  expect(child.workspace).toBe(parent.workspace);
  expect(child.profile).toBe(parent.profile);
  expect(transcript((await read(parentId)).messages)).toEqual(original);
  await page.reload();
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_FORK_FIRST');
  await expect(page.locator('#messages')).not.toContainText('QA_FORK_LATER');
  await sendAccepted(childId, 'QA_FORK_CHILD_ONLY');
  expect(transcript((await read(childId)).messages)).toEqual([
    ...original.slice(0, 2), {role: 'user', content: 'QA_FORK_CHILD_ONLY'}, {role: 'assistant', content: 'DEFAULT QA_REPLY: QA_FORK_CHILD_ONLY'},
  ]);
  expect(transcript((await read(parentId)).messages)).toEqual(original);
  for (const sid of [parentId, childId]) {
    const deniedRead = await page.request.get('/api/session?session_id=' + sid, {headers: {Cookie: auth.cookie_name + '=' + auth.cookies.bob}});
    expect(deniedRead.status()).toBe(404);
    expect(await deniedRead.text()).not.toContain('QA_FORK_');
    const deniedFork = await page.request.post('/api/session/branch', {headers: {Cookie: auth.cookie_name + '=' + auth.cookies.bob}, data: {session_id: sid, keep_count: 2}});
    expect(deniedFork.status()).toBe(404);
    expect(await deniedFork.text()).not.toContain('QA_FORK_');
  }
});
