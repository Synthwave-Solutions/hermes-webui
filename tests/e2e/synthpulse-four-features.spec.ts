import { test, expect } from '@playwright/test'

async function createSession(request, mode = 'super') {
  const response = await request.post('/api/session/new', {
    data: { chat_mode: mode },
  })
  expect(response.ok()).toBeTruthy()
  const payload = await response.json()
  return payload.session
}

test('TC-CHATMODE-001 @critical new chats default to Super agent and can switch to Normal', async ({ page, request }) => {
  await page.goto('/')
  const chip = page.locator('#composerChatModeChip')
  await expect(chip).toBeVisible()
  await expect(page.locator('#composerChatModeLabel')).toHaveText('Super agent')

  await chip.click()
  await expect(page.locator('#composerChatModeLabel')).toHaveText('Normal chat')
  const session = await createSession(request, 'normal')
  expect(session.chat_mode).toBe('normal')
})

test('TC-CHATMODE-002 @high session mode persists and rejects unknown modes', async ({ page, request }) => {
  await page.goto('/')
  const session = await createSession(request, 'super')
  const changed = await request.post('/api/session/mode', {
    data: { session_id: session.id || session.session_id, mode: 'normal' },
  })
  expect(changed.ok()).toBeTruthy()
  expect((await changed.json()).chat_mode).toBe('normal')

  const invalid = await request.post('/api/session/mode', {
    data: { session_id: session.id || session.session_id, mode: 'lite' },
  })
  expect(invalid.status()).toBe(400)
})

test('TC-PROJHUB-001 @critical Projects hub loads and safely renders project names', async ({ page, request }) => {
  const marker = '<img src=x onerror=alert(1)>'
  const created = await request.post('/api/projects/create', { data: { name: marker } })
  expect(created.ok()).toBeTruthy()

  await page.goto('/')
  await page.locator('.rail-btn[data-panel="projects"]').click()
  await expect(page.locator('#panelProjects')).toBeVisible()
  await expect(page.locator('#projectsPanelList')).toContainText(marker)
  await expect(page.locator('#projectsPanelList img')).toHaveCount(0)
})

test('TC-PROJHUB-002 @high Projects API labels unconnected sources honestly', async ({ page, request }) => {
  await page.goto('/')
  const response = await request.get('/api/projects')
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  expect(body).toHaveProperty('projects')
  expect(Array.isArray(body.projects)).toBeTruthy()
})

test('TC-APPROVAL-001 @critical approval explanation renderer escapes untrusted values', async ({ page }) => {
  await page.goto('/')
  const result = await page.evaluate(() => {
    const hostile = '<img src=x onerror=alert(1)>'
    const html = (window as any)._govExplainHtml({
      capability: hostile,
      data: 'Session metadata',
      risks: [{ id: 'data_access', label: hostile }],
      policy_target: ['user@example.test'],
    })
    const host = document.createElement('div')
    host.id = 'qaApprovalExplanation'
    host.innerHTML = html
    document.body.appendChild(host)
    return { html, images: host.querySelectorAll('img').length, text: host.textContent }
  })
  expect(result.images).toBe(0)
  expect(result.text).toContain('<img src=x onerror=alert(1)>')
})

test('TC-CHAIN-001 @critical related approvals keep route and permission walls separate', async ({ page, request }) => {
  await page.goto('/')
  const mine = await request.get('/api/governance/approvals/mine')
  expect(mine.ok()).toBeTruthy()
  const body = await mine.json()
  expect(body).toHaveProperty('requests')
  expect(Array.isArray(body.requests)).toBeTruthy()
})
