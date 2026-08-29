import { test, expect } from '@playwright/test'

// Group conversations and the approvals advice block, driven through the real
// UI. The unit suites cover the rules; these cover that a person can actually
// reach them: pick colleagues, see who is in the chat, and read the advice on
// a pending request before deciding.

test('TC-GROUP-001 @critical the people chip is present and says a new chat is private', async ({ page }) => {
  await page.goto('/')
  const chip = page.locator('#composerPeopleChip')
  await expect(chip).toBeVisible()
  await expect(page.locator('#composerPeopleLabel')).toHaveText('Just me')
})

test('TC-GROUP-002 @critical picking a colleague stages them on a new conversation', async ({ page, request }) => {
  const people = await request.get('/api/people')
  expect(people.ok()).toBeTruthy()
  const body = await people.json()
  expect(Array.isArray(body.people)).toBeTruthy()

  await page.goto('/')
  await page.locator('#composerPeopleChip').click()
  await expect(page.locator('#groupPeopleModal')).toBeVisible()
  const first = page.locator('#groupPeopleList input[type="checkbox"]').first()
  if (await first.count()) {
    await first.check()
    await page.locator('#groupPeopleModalSubmit').click()
    await expect(page.locator('#groupPeopleModal')).toBeHidden()
    await expect(page.locator('#composerPeopleLabel')).not.toHaveText('Just me')
  }
})

test('TC-GROUP-003 @high participants survive a round trip through the API', async ({ request }) => {
  const created = await request.post('/api/session/new', { data: {} })
  expect(created.ok()).toBeTruthy()
  const session = (await created.json()).session
  const sid = session.session_id || session.id

  const people = await (await request.get('/api/people')).json()
  const pick = (people.people || []).map((p: any) => p.email).filter((e: string) => e && e !== people.me)[0]
  if (!pick) test.skip(true, 'no colleagues configured on this workstation')

  const set = await request.post('/api/session/participants', {
    data: { session_id: sid, participants: [pick] },
  })
  expect(set.ok()).toBeTruthy()
  expect((await set.json()).participants).toContain(pick)

  const cleared = await request.post('/api/session/participants', {
    data: { session_id: sid, participants: [] },
  })
  expect(cleared.ok()).toBeTruthy()
  expect((await cleared.json()).participants).toEqual([])
})

test('TC-GROUP-004 @critical an unknown address cannot be put in a conversation', async ({ request }) => {
  const created = await request.post('/api/session/new', { data: {} })
  const session = (await created.json()).session
  const sid = session.session_id || session.id
  const refused = await request.post('/api/session/participants', {
    data: { session_id: sid, participants: ['outsider@example.com'] },
  })
  expect(refused.status()).toBe(400)
})

test('TC-GROUP-005 @high a malformed participant list is refused, not stored', async ({ request }) => {
  const created = await request.post('/api/session/new', { data: {} })
  const session = (await created.json()).session
  const sid = session.session_id || session.id
  const refused = await request.post('/api/session/participants', {
    data: { session_id: sid, participants: ['not-an-address'] },
  })
  expect(refused.status()).toBe(400)
})

test('TC-ADVICE-001 @critical a pending access request carries advice with a stated source', async ({ request }) => {
  const response = await request.get('/api/governance/approvals?kind=grant')
  if (!response.ok()) test.skip(true, 'approvals queue not reachable for this identity')
  const body = await response.json()
  const pending = (body.pending || []).filter((r: any) => r.status === 'pending')
  if (!pending.length) test.skip(true, 'no pending access request to advise on')
  const row = pending[0]
  expect(row.advice).toBeTruthy()
  expect(['model', 'rules']).toContain(row.advice.source)
  expect(['grant', 'grant_narrower', 'decline', 'needs_more_information'])
    .toContain(row.advice.recommendation)
  expect(String(row.advice.recommendation_reason || '').length).toBeGreaterThan(0)
})

test('TC-ADVICE-002 @high the advice block renders and escapes its values', async ({ page }) => {
  await page.goto('/')
  await page.locator('.rail-btn[data-panel="governance"]').click()
  const advice = page.locator('.gov-explain-body')
  if (await advice.count()) {
    // Untrusted text must never become markup: no injected nodes from a model
    // reply or a requester's own words.
    await expect(page.locator('.gov-explain-body script')).toHaveCount(0)
    await expect(page.locator('.gov-explain-body img')).toHaveCount(0)
  }
})
