import type { Page } from '@playwright/test';
import { test, expect, open, api, capture } from './fixtures';

// All mutations below are real UI actions. Read-only API calls verify the
// resulting persisted records independently of the browser's rendered cache.
async function cron(page: Page, id: string) {
  const result = await api(page, '/api/crons');
  expect(result.status).toBe(200);
  return result.body.jobs.find((job: any) => job.id === id);
}

async function task(page: Page, id: string) {
  const result = await api(page, '/api/kanban/tasks/' + encodeURIComponent(id));
  expect(result.status).toBe(200);
  return result.body;
}

async function saveNewCron(page: Page) {
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/crons/create' && r.request().method() === 'POST');
  await page.locator('#btnSaveTaskDetail').click();
  const result = await response;
  expect(result.ok()).toBeTruthy();
  const body = await result.json();
  const id = body.id || body.job?.id;
  expect(id).toBeTruthy();
  return id as string;
}

async function deleteCron(page: Page, id: string) {
  await page.locator('#btnDeleteTaskDetail').click();
  await expect(page.locator('#appDialog')).toBeVisible();
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/crons/delete' && r.request().method() === 'POST');
  await page.locator('#appDialogConfirm').click();
  expect((await response).ok()).toBeTruthy();
  await expect.poll(() => cron(page, id)).toBeUndefined();
}

test('US-SP-LIFECYCLE-CRON edit, cancel, duplicate, run locally, pause, resume and delete persist', async ({ page }, info) => {
  test.setTimeout(120_000);
  const name = 'QA Cron lifecycle ' + Date.now();
  const renamed = name + ' edited';
  const prompt = 'Return a short synthetic status. QA_CRON_LIFECYCLE';
  await open(page, 'tasks');
  await page.getByRole('button', { name: 'New job', exact: true }).click();
  await page.locator('#cronFormName').fill(name);
  await page.locator('#cronFormPrompt').fill(prompt);
  await page.locator('#cronFormSchedulePreset').selectOption('daily');
  await page.locator('#cronFormScheduleTime').fill('09:30');
  await page.locator('#cronFormProfile').selectOption('qa-research');
  await page.locator('#cronFormDeliver').selectOption('local');
  const id = await saveNewCron(page);
  await expect(page.locator('#taskDetailTitle')).toHaveText(name);
  expect(await cron(page, id)).toMatchObject({ name, prompt, profile: 'qa-research', deliver: 'local' });

  await page.locator('#btnEditTaskDetail').click();
  await page.locator('#cronFormName').fill('Discarded cron edit');
  await page.locator('#cronFormPrompt').fill('This must not be saved');
  await page.locator('#btnCancelTaskDetail').click();
  await expect(page.locator('#taskDetailTitle')).toHaveText(name);
  expect(await cron(page, id)).toMatchObject({ name, prompt });

  await page.locator('#btnEditTaskDetail').click();
  await page.locator('#cronFormName').fill(renamed);
  await page.locator('#cronFormScheduleTime').fill('10:45');
  await page.locator('#cronFormToastNotifications').uncheck();
  await page.locator('#btnSaveTaskDetail').click();
  await expect(page.locator('#taskDetailTitle')).toHaveText(renamed);
  expect(await cron(page, id)).toMatchObject({ name: renamed, prompt, toast_notifications: false });
  await page.reload();
  await page.locator('.rail-btn[data-panel="tasks"]').click();
  await page.locator('.cron-item').filter({ hasText: renamed }).click();
  await page.locator('#btnEditTaskDetail').click();
  await expect(page.locator('#cronFormScheduleTime')).toHaveValue('10:45');
  await expect(page.locator('#cronFormPrompt')).toHaveValue(prompt);
  await expect(page.locator('#cronFormToastNotifications')).not.toBeChecked();
  await page.locator('#btnCancelTaskDetail').click();

  await page.locator('#btnDuplicateTaskDetail').click();
  const copyName = renamed + ' (copy)';
  await expect(page.locator('#cronFormName')).toHaveValue(copyName);
  await expect(page.locator('#cronFormPrompt')).toHaveValue(prompt);
  await expect(page.locator('#cronFormProfile')).toHaveValue('qa-research');
  const copyId = await saveNewCron(page);
  expect(copyId).not.toBe(id);
  await expect(page.locator('#taskDetailTitle')).toHaveText(copyName);
  await expect(page.locator('#btnResumeTaskDetail')).toBeVisible();
  expect(await cron(page, copyId)).toMatchObject({ name: copyName, enabled: false, prompt, profile: 'qa-research', deliver: 'local' });
  expect((await cron(page, id)).name).toBe(renamed);
  await deleteCron(page, copyId);

  await page.locator('.cron-item').filter({ hasText: renamed }).click();
  await page.locator('#btnPauseTaskDetail').click();
  await expect(page.locator('#btnResumeTaskDetail')).toBeVisible();
  expect((await cron(page, id)).enabled).toBe(false);
  await page.locator('#btnResumeTaskDetail').click();
  await expect(page.locator('#btnPauseTaskDetail')).toBeVisible();
  expect((await cron(page, id)).enabled).toBe(true);

  // The runner clears inherited provider credentials and binds the configured
  // deterministic model to loopback. Local delivery cannot message outsiders.
  await page.locator('#btnRunTaskDetail').click();
  await expect.poll(async () => (await api(page, '/api/crons/history?job_id=' + id)).body.total, { timeout: 60_000 }).toBeGreaterThan(0);
  await expect(page.locator('#cronDetailRuns .detail-run-item')).toHaveCount(1, { timeout: 15_000 });
  await page.locator('#cronDetailRuns .detail-run-head').click();
  await expect(page.locator('#cronDetailRuns .cron-run-pre')).toContainText('QA_REPLY: QA_CRON_LIFECYCLE');
  const history = await api(page, '/api/crons/history?job_id=' + id);
  const filename = history.body.runs[0].filename;
  const output = await api(page, '/api/crons/run?job_id=' + id + '&filename=' + encodeURIComponent(filename));
  expect(output.status).toBe(200);
  expect(output.body.content).toContain('QA_REPLY: QA_CRON_LIFECYCLE');
  await info.attach('persisted-cron-run', { body: JSON.stringify({ job: await cron(page, id), history: history.body, output: output.body }), contentType: 'application/json' });
  await capture(page, 'cron-run-output', info);

  await page.locator('#btnDeleteTaskDetail').click();
  await page.locator('#appDialogCancel').click();
  expect((await cron(page, id)).name).toBe(renamed);
  await deleteCron(page, id);
  await page.reload();
  await page.locator('.rail-btn[data-panel="tasks"]').click();
  await expect(page.locator('.cron-item').filter({ hasText: name })).toHaveCount(0);
});

test('US-SP-LIFECYCLE-KAN edit, comment, complete, archive and restore survive reload', async ({ page }, info) => {
  test.setTimeout(90_000);
  const name = 'QA Kanban lifecycle ' + Date.now();
  const renamed = name + ' edited';
  const body = 'Synthetic lifecycle task. Deliberately unassigned so no dispatcher runs.';
  await open(page, 'kanban');
  await page.locator('#kanbanNewTaskBtn').click();
  await page.locator('#kanbanTaskModalSubmit').click();
  await expect(page.locator('#kanbanTaskModalError')).toContainText('Title is required');
  await page.locator('#kanbanTaskModalTitleInput').fill(name);
  await page.locator('#kanbanTaskModalBody').fill(body);
  await page.locator('#kanbanTaskModalStatus').selectOption('triage');
  await page.locator('#kanbanTaskModalAssignee').selectOption('');
  const created = page.waitForResponse(r => new URL(r.url()).pathname === '/api/kanban/tasks' && r.request().method() === 'POST');
  await page.locator('#kanbanTaskModalSubmit').click();
  const response = await created;
  expect(response.ok()).toBeTruthy();
  const id = (await response.json()).task.id;
  const preview = page.locator('#kanbanTaskPreview');
  const card = page.locator(`.kanban-card[data-kanban-task-id="${id}"]`);
  await expect(preview.locator('.kanban-task-preview-title')).toHaveText(name);
  expect((await task(page, id)).task).toMatchObject({ title: name, body, status: 'triage', assignee: null });

  await preview.locator('.kanban-edit-btn').click();
  await page.locator('#kanbanTaskModalTitleInput').fill(renamed);
  await page.locator('#kanbanTaskModalBody').fill(body + ' Edited through the browser.');
  await page.locator('#kanbanTaskModalStatus').selectOption('todo');
  await page.locator('#kanbanTaskModalPriority').fill('2');
  await page.locator('#kanbanTaskModalSubmit').click();
  await expect(preview.locator('.kanban-task-preview-title')).toHaveText(renamed);
  expect((await task(page, id)).task).toMatchObject({ title: renamed, status: 'todo', priority: 2, assignee: null });
  await expect(page.locator('.kanban-column[data-status="todo"]').locator(card)).toBeVisible();

  const comment = 'QA lifecycle comment persisted ' + Date.now();
  await page.locator('#kanbanCommentInput').fill(comment);
  await preview.getByRole('button', { name: 'Add comment', exact: true }).click();
  await expect(preview.locator('.kanban-detail-comments')).toContainText(comment);
  expect((await task(page, id)).comments.some((item: any) => item.body === comment)).toBe(true);
  // The engine's completion contract starts at Ready. No assignee is set,
  // so this transition cannot dispatch a worker in the isolated fixture.
  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Ready', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('ready');
  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Done', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('done');

  // Editing an already-completed task must preserve its real state even
  // though the modal only offers Triage, Todo and Ready in its status select.
  await preview.locator('.kanban-edit-btn').click();
  await expect(page.locator('#kanbanTaskModalStatusOriginalHint')).toContainText('Done');
  await page.locator('#kanbanTaskModalBody').fill(body + ' Completed task edited without resetting status.');
  await page.locator('#kanbanTaskModalSubmit').click();
  await expect(preview.locator('.kanban-task-preview-body')).toContainText('Completed task edited');
  expect((await task(page, id)).task.status).toBe('done');

  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Archived', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('archived');
  await preview.locator('.kanban-back-btn').click();
  await expect(card).toHaveCount(0);
  await page.reload();
  await page.locator('.rail-btn[data-panel="kanban"]').click();
  await expect(card).toHaveCount(0);
  await page.locator('#kanbanIncludeArchived').check();
  await expect(page.locator('.kanban-column[data-status="archived"]').locator(card)).toBeVisible();
  await card.click();
  await expect(preview.locator('.kanban-detail-comments')).toContainText(comment);
  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Todo', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('todo');
  await preview.locator('.kanban-back-btn').click();
  await page.locator('#kanbanIncludeArchived').uncheck();
  await expect(page.locator('.kanban-column[data-status="todo"]').locator(card)).toBeVisible();
  await page.reload();
  await page.locator('.rail-btn[data-panel="kanban"]').click();
  await expect(page.locator('.kanban-column[data-status="todo"]').locator(card)).toBeVisible();
  const persisted = await task(page, id);
  expect(persisted.task).toMatchObject({ title: renamed, status: 'todo', priority: 2, assignee: null });
  expect(persisted.comments.some((item: any) => item.body === comment)).toBe(true);
  await info.attach('persisted-kanban-lifecycle', { body: JSON.stringify(persisted), contentType: 'application/json' });
  await capture(page, 'restored-kanban-task', info);

  // Also exercise card shortcuts, ending archived so full-suite runs leave no
  // actionable fixture task behind. Kanban intentionally exposes no hard delete.
  await card.click();
  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Ready', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('ready');
  await preview.locator('.kanban-back-btn').click();
  await card.getByRole('button', { name: 'complete', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('done');
  await preview.locator('.kanban-back-btn').click();
  await card.getByRole('button', { name: 'archive', exact: true }).click();
  await expect.poll(async () => (await task(page, id)).task.status).toBe('archived');
});

test('US-SP-LIFECYCLE-KAN-DEFECT visible Done action must complete an existing Todo task', async ({ page }, info) => {
  // Known existing frontend/engine contract mismatch: the UI offers Done for
  // Todo, but the real engine accepts completion only from Ready or later.
  // Keep this acceptance check failing until that product decision is fixed;
  // a mocked Kanban database would incorrectly make this interaction pass.
  await open(page, 'kanban');
  await page.locator('#kanbanNewTaskBtn').click();
  const name = 'QA Kanban completion defect ' + Date.now();
  await page.locator('#kanbanTaskModalTitleInput').fill(name);
  await page.locator('#kanbanTaskModalBody').fill('Unassigned synthetic task; no worker execution.');
  await page.locator('#kanbanTaskModalStatus').selectOption('todo');
  await page.locator('#kanbanTaskModalAssignee').selectOption('');
  const created = page.waitForResponse(r => new URL(r.url()).pathname === '/api/kanban/tasks' && r.request().method() === 'POST');
  await page.locator('#kanbanTaskModalSubmit').click();
  const id = (await (await created).json()).task.id;
  const preview = page.locator('#kanbanTaskPreview');
  await expect(preview.locator('.kanban-task-preview-title')).toHaveText(name);
  expect((await task(page, id)).task.status).toBe('todo');
  const changed = page.waitForResponse(r => new URL(r.url()).pathname === '/api/kanban/tasks/' + id && r.request().method() === 'PATCH');
  await preview.locator('.kanban-status-actions').getByRole('button', { name: 'Done', exact: true }).click();
  const response = await changed;
  await info.attach('todo-completion-response', { body: JSON.stringify({ status: response.status(), response: await response.json(), persisted: await task(page, id) }), contentType: 'application/json' });
  expect(response.status(), 'A visible Done action must accept this existing task or be unavailable before the click').toBe(200);
  expect((await task(page, id)).task.status).toBe('done');
});
