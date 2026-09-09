import fs from 'node:fs';
import path from 'node:path';
import {test, expect, open, api, auth, session} from './fixtures';
declare const S: any;

test.use({user: 'manualapprove'});

test('SUPPLEMENT WORKSPACE DEFAULT remembered foreign or removed workspace recovers on New chat without widening explicit access', async ({page, browser}, info) => {
  const admin = await browser.newContext({baseURL: auth.base_url});
  await admin.route('**/*', r => ['127.0.0.1', 'localhost', '[::1]'].includes(new URL(r.request().url()).hostname) ? r.continue() : r.abort('blockedbyclient'));
  await admin.addCookies([{name: auth.cookie_name, value: auth.cookies.admin, url: auth.base_url, httpOnly: true, sameSite: 'Lax'}]);
  const adminPage = await admin.newPage();
  const adminErrors: string[] = []; adminPage.on('pageerror', error => adminErrors.push(error.message));
  const directory = path.join(auth.workspace, 'qa-remembered-private-' + Date.now());
  const removedDirectory = path.join(path.dirname(auth.workspace), 'qa-removed-private-' + Date.now());
  fs.mkdirSync(directory);
  fs.mkdirSync(removedDirectory);
  const name = path.basename(directory);
  let registered = false;
  let removedRegistered = false;
  const sessions: string[] = [];
  await open(adminPage);
  try {
    expect((await api(adminPage, '/api/workspaces/add', {path: directory, name})).status).toBe(200); registered = true;
    expect((await api(adminPage, '/api/workspaces/assign', {path: directory, owner_email: 'admin@example.test', members: ['manualapprove@example.test']})).status).toBe(200);
    const remembered = await api(adminPage, '/api/session/new', {workspace: directory, worktree: false});
    expect(remembered.status).toBe(200); sessions.push(remembered.body.session.session_id);
    expect((await api(adminPage, '/api/session/update', {session_id: sessions[0], workspace: directory})).status).toBe(200);
    await open(page);
    await page.waitForFunction(expected => typeof S !== 'undefined' && S._profileDefaultWorkspace === expected, directory);
    expect((await api(page, '/api/profile/active')).body.default_workspace).toBe(directory);
    expect((await api(adminPage, '/api/workspaces/assign', {path: directory, owner_email: 'admin@example.test', members: []})).status).toBe(200);
    await open(page);
    await page.waitForFunction(expected => typeof S !== 'undefined' && S._profileDefaultWorkspace === expected, auth.workspace);
    const active = await api(page, '/api/profile/active');
    expect(active.status).toBe(200); expect(active.body.default_workspace).toBe(auth.workspace);
    expect(JSON.stringify(active.body)).not.toContain(directory);
    const switched = await api(page, '/api/profile/switch', {name: 'default'});
    expect(switched.status).toBe(200); expect(switched.body.default_workspace).toBe(auth.workspace);
    expect(JSON.stringify(switched.body)).not.toContain(directory);
    const pendingNew = page.waitForResponse(r => r.url().endsWith('/api/session/new') && r.request().method() === 'POST');
    sessions.push(await session(page));
    const newResponse = await pendingNew;
    expect(newResponse.status()).toBe(200); expect(newResponse.request().postDataJSON().workspace).toBe(auth.workspace);
    expect((await api(page, '/api/session?session_id=' + sessions[1])).body.session).toMatchObject({workspace: auth.workspace, owner_email: 'manualapprove@example.test'});
    const implicit = await api(page, '/api/session/new', {worktree: false});
    expect(implicit.status).toBe(200); expect(implicit.body.session.workspace).toBe(auth.workspace); sessions.push(implicit.body.session.session_id);
    expect((await api(page, '/api/session/new', {workspace: directory, worktree: false})).status).toBe(403);
    // Choosing a fallback must not overwrite the profile's shared remembered hint.
    expect((await api(adminPage, '/api/profile/active')).body.default_workspace).toBe(directory);
    expect((await api(adminPage, '/api/workspaces/add', {path: removedDirectory, name: path.basename(removedDirectory)})).status).toBe(200); removedRegistered = true;
    const stale = await api(adminPage, '/api/session/new', {workspace: removedDirectory, worktree: false});
    expect(stale.status).toBe(200); sessions.push(stale.body.session.session_id);
    expect((await api(adminPage, '/api/session/update', {session_id: stale.body.session.session_id, workspace: removedDirectory})).status).toBe(200);
    expect((await api(adminPage, '/api/workspaces/remove', {path: removedDirectory})).status).toBe(200); removedRegistered = false;
    expect(fs.existsSync(removedDirectory)).toBe(true);
    await open(adminPage);
    await adminPage.waitForFunction(expected => typeof S !== 'undefined' && S._profileDefaultWorkspace === expected, auth.workspace);
    sessions.push(await session(adminPage));
    expect((await api(adminPage, '/api/session?session_id=' + sessions.at(-1))).body.session.workspace).toBe(auth.workspace);
    expect((await api(adminPage, '/api/session/new', {workspace: removedDirectory, worktree: false})).status).toBe(400);
  } finally {
    const restored = await api(adminPage, '/api/session/new', {workspace: auth.workspace, worktree: false});
    expect(restored.status).toBe(200); sessions.push(restored.body.session.session_id);
    expect((await api(adminPage, '/api/session/update', {session_id: restored.body.session.session_id, workspace: auth.workspace})).status).toBe(200);
    if (registered) expect((await api(adminPage, '/api/workspaces/remove', {path: directory})).status).toBe(200);
    if (removedRegistered) expect((await api(adminPage, '/api/workspaces/remove', {path: removedDirectory})).status).toBe(200);
    for (const sid of sessions) expect((await api(adminPage, '/api/session/delete', {session_id: sid})).status).toBe(200);
    await info.attach('admin-uncaught-browser-errors', {body: JSON.stringify(adminErrors), contentType: 'application/json'});
    await admin.close(); expect(adminErrors).toEqual([]);
  }
});
