import {test, expect, open, api} from './fixtures';

test('SUPPLEMENT KANBAN EDIT FOCUS delayed initial focus cannot redirect priority typing into the saved title', async ({page}, info) => {
  await page.addInitScript(() => {
    const w = window as any;
    const original = window.setTimeout.bind(window);
    w.__qaTaskFocusTimers = [];
    w.__qaTaskFocusSchedulers = [];
    window.setTimeout = ((callback: TimerHandler, delay?: number, ...args: any[]) => {
      const stack = new Error().stack || '';
      if (typeof callback === 'function' && delay === 50 && /at openKanbanEdit\b/.test(stack)) {
        w.__qaTaskFocusTimers.push(() => callback(...args));
        w.__qaTaskFocusSchedulers.push(stack);
        return original(() => {}, delay);
      }
      return original(callback, delay, ...args);
    }) as typeof window.setTimeout;
    w.__qaReleaseTaskFocus = () => {
      const pending = w.__qaTaskFocusTimers.splice(0);
      for (const callback of pending) callback();
      return pending.length;
    };
  });
  await open(page);
  const board = 'qa-edit-focus-' + Date.now();
  const title = 'Exact task title ' + Date.now();
  expect((await api(page, '/api/kanban/boards', {slug:board, name:board, switch:true})).status).toBe(200);
  const seeded = await api(page, '/api/kanban/tasks?board=' + board, {title, body:'Original body', status:'todo', assignee:null});
  expect(seeded.status).toBe(200);
  const id = seeded.body.task.id;
  try {
    await page.reload();
    await page.locator('.rail-btn[data-panel="kanban"]').click();
    await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(board);
    await page.locator(`.kanban-card[data-kanban-task-id="${id}"]`).click();
    await page.locator('#kanbanTaskPreview .kanban-edit-btn').click();
    await expect(page.locator('#kanbanTaskModal')).toBeVisible();
    const renamed = title + ' edited';
    const body = 'Exact body typed before priority.';
    await page.locator('#kanbanTaskModalTitleInput').fill(renamed);
    await page.locator('#kanbanTaskModalBody').fill(body);
    await page.locator('#kanbanTaskModalPriority').fill('');
    await expect(page.locator('#kanbanTaskModalPriority')).toBeFocused();
    const released = await page.evaluate(() => (window as any).__qaReleaseTaskFocus());
    // Native typing must stay in the field selected by the user. Old source's
    // captured50ms callback selects the title instead; fixed source has no timer.
    await page.keyboard.insertText('2');
    const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/kanban/tasks/' + id && r.request().method() === 'PATCH');
    await page.locator('#kanbanTaskModalSubmit').click();
    const response = await saved;
    expect(response.status()).toBe(200);
    const persisted = await api(page, '/api/kanban/tasks/' + id + '?board=' + board);
    expect(persisted.status).toBe(200);
    await info.attach('task-edit-focus-readback', {body:JSON.stringify({released, schedulers:await page.evaluate(() => (window as any).__qaTaskFocusSchedulers), patch:response.request().postDataJSON(), persisted:persisted.body.task}), contentType:'application/json'});
    expect(response.request().postDataJSON()).toMatchObject({title:renamed, body, priority:2});
    expect(persisted.body.task).toMatchObject({title:renamed, body, priority:2, status:'todo', assignee:null});
    await expect(page.locator('#kanbanTaskPreview .kanban-task-preview-title')).toHaveText(renamed);
    await page.reload();
    await page.locator('.rail-btn[data-panel="kanban"]').click();
    await page.locator(`.kanban-card[data-kanban-task-id="${id}"]`).click();
    await page.locator('#kanbanTaskPreview .kanban-edit-btn').click();
    await expect(page.locator('#kanbanTaskModalTitleInput')).toHaveValue(renamed);
    await expect(page.locator('#kanbanTaskModalPriority')).toHaveValue('2');
  } finally {
    expect((await api(page, '/api/kanban/boards/default/switch', {})).status).toBe(200);
  }
});
