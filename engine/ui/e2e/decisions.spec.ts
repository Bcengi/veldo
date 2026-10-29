import type { Page } from '@playwright/test'
import { expect, signIn, test, type Factory } from './fixtures'

/**
 * VELDO-0145 AC3: each pending decision exactly as presented, answered inline through the API bound to the
 * presentation version shown, settling once with Telegram; each refusal named beside the action.
 */

let serial = 0
async function freshRequest(factory: Factory, owner = 'owner') {
  serial += 1
  const alias = `dx${Date.now() % 100000}${serial}`
  const { request } = await factory.control<{ request: string }>('/request/open', { alias, owner })
  return { alias, request }
}

async function settlements(factory: Factory, alias: string) {
  return (await factory.control<{ settlements: { originating_channel: string; presentation_version: number }[] }>(
    '/request/settlements',
    { alias },
  )).settlements
}

async function openDecision(page: Page, factory: Factory, request: string) {
  await page.goto(factory.origin + '/decisions/' + request)
  await expect(page.getByTestId('decision')).toHaveAttribute('data-request', request)
}

async function answer(page: Page, choice: string, rationale: string) {
  await page.locator(`[data-choice="${choice}"]`).click()
  await page.getByTestId('rationale').fill(rationale)
  await page.getByTestId('send-answer').click()
}

test('inbox and exact presentation: the question, choices and rationale as the receipt holds them', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/decisions')
  const rows = page.locator('[data-testid="inbox"] [data-request]')
  for (const request of Object.values(state.requests)) await expect(page.locator(`[data-testid="inbox"] [data-request="${request}"]`)).toHaveCount(1)
  expect(await rows.count()).toBeGreaterThanOrEqual(1)

  const read = await (await page.request.get(`${factory.origin}/api/v1/domains/${factory.domain}/decisions`)).json()
  const receipt = read.items.channel_presentation
    .map((i: { data: Record<string, unknown> }) => i.data)
    .filter((d: Record<string, unknown>) => d.request_id === state.requests.de2 && d.outcome === 'published')
    .sort((a: { presentation_version: number }, b: { presentation_version: number }) => b.presentation_version - a.presentation_version)[0]
  await openDecision(page, factory, state.requests.de2!)
  await expect(page.getByTestId('question')).toHaveText(receipt.request.brief)
  await expect(page.getByTestId('risk')).toHaveText(receipt.risk_statement)
  expect(await page.locator('[data-choice]').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.choice))).toEqual(receipt.choices)
  await page.getByText(/As it was presented in/).click()
  expect(await page.getByTestId('rendered').allTextContents()).toEqual(receipt.rendered)
  const shown = page.getByTestId('decision')
  await expect(shown).toHaveAttribute('data-presentation-version', String(receipt.presentation_version))
  await expect(shown).toHaveAttribute('data-request-version', String(receipt.request_version))
  await expect(page.getByTestId('answer-binding')).toContainText(`Answering version ${receipt.presentation_version} of this question`)
})

test('ranked inbox: most urgent deadline first, then risk, with how soon each is due and an urgency lamp', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/decisions')
  await expect(page.getByTestId('inbox')).toBeVisible()
  const order = await page.locator('[data-testid="inbox"] [data-request]').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.request))
  const seeded = ['de3', 'de5', 'de1', 'de2', 'de4'].map((a) => state.requests[a]!)
  // The seeded decisions: de3 due in 5 h (high risk), then within three days de5 (high), de1 (medium) and de2
  // (low), then de4 in six days. Other tests' decisions may sit between them, never out of this order.
  expect(order.filter((r) => seeded.includes(r!))).toEqual(seeded)
  const row = (alias: string) => page.locator(`.inbox-row[data-request="${state.requests[alias]}"]`)
  await expect(row('de3')).toHaveAttribute('data-urgency', 'today')
  await expect(row('de3').getByTestId('due')).toHaveText(/^due in [45] h$/)
  await expect(row('de3').locator('.lamp')).toHaveClass(/lamp-stop/)
  await expect(row('de5')).toHaveAttribute('data-urgency', 'soon')
  await expect(row('de5').locator('.lamp')).toHaveClass(/lamp-waiting/)
  await expect(row('de4')).toHaveAttribute('data-urgency', 'later')
  await expect(row('de4').getByTestId('due')).toHaveText(/^due in [56] d$/)
  await expect(row('de3')).toContainText('High risk')
})

test('inline answer: bound to the presentation shown, settled once, and Telegram after it settles nothing', async ({ page, factory }) => {
  const { alias, request } = await freshRequest(factory)
  await signIn(page, factory)
  await openDecision(page, factory, request)
  const sent = page.waitForRequest((r) => r.url().endsWith('/decisions/answer') && r.method() === 'POST')
  await answer(page, 'accept', 'The search index is the next thing the owner needs.')
  const body = JSON.parse((await sent).postData() ?? '{}')
  expect(body).toMatchObject({ request_id: request, request_version: 1, presentation_version: 1, choice: 'accept' })
  expect(Object.keys(body).sort()).toEqual(
    ['choice', 'presentation_digest', 'presentation_id', 'presentation_version', 'rationale', 'request_id', 'request_version'],
  )
  await expect(page.getByTestId('answer-result')).toContainText('Answer sent')
  let found = await settlements(factory, alias)
  expect(found).toHaveLength(1)
  expect(found[0]).toMatchObject({ originating_channel: 'api', presentation_version: 1 })
  // The same request answered from Telegram afterwards: still exactly one settlement.
  await factory.control('/request/telegram', { alias, text: 'reject: answered later in Telegram' })
  found = await settlements(factory, alias)
  expect(found).toHaveLength(1)
  // The inbox no longer lists it, read again from the API.
  await page.goto(factory.origin + '/decisions')
  await expect(page.locator(`[data-testid="inbox"] [data-request="${request}"]`)).toHaveCount(0)
})

test('answered in Telegram first: the UI answer is refused as already settled, beside the action', async ({ page, factory }) => {
  const { alias, request } = await freshRequest(factory)
  await signIn(page, factory)
  await openDecision(page, factory, request)
  await factory.control('/request/telegram', { alias, text: 'accept: answered first in Telegram' })
  expect(await settlements(factory, alias)).toHaveLength(1)
  await answer(page, 'reject', 'Answering from the phone after Telegram.')
  const refusal = page.getByTestId('answer-bar').getByTestId('refusal')
  await expect(refusal).toHaveAttribute('data-refusal', /^stale_version:(request_closed|already_answered|already_settled)$/)
  await expect(refusal).toContainText(/Already/)
  await expect(page.getByTestId('answer-result')).toHaveCount(0)
  const found = await settlements(factory, alias)
  expect(found).toHaveLength(1)
  expect(found[0]!.originating_channel).toBe('telegram_chat')
})

test('stale answer: the presentation changed after it was shown, and the answer is refused beside the action', async ({ page, factory }) => {
  const { alias, request } = await freshRequest(factory)
  await signIn(page, factory)
  await openDecision(page, factory, request)
  await expect(page.getByTestId('decision')).toHaveAttribute('data-presentation-version', '1')
  await factory.control('/request/revise', { alias })
  await answer(page, 'accept', 'Answering what the screen showed.')
  const refusal = page.getByTestId('answer-bar').getByTestId('refusal')
  await expect(refusal).toHaveAttribute('data-refusal', 'stale_version:stale_presentation')
  await expect(refusal).toContainText('The question changed after you opened it')
  await expect(page.getByTestId('answer-result')).toHaveCount(0)
  expect(await settlements(factory, alias)).toHaveLength(0)
  // The refused action is replaced: no Send answer over a version that is gone, and the choice is cleared.
  await expect(page.getByTestId('send-answer')).toHaveCount(0)
  await expect(page.locator('[data-choice] input:checked')).toHaveCount(0)
  // Load the current version shows it, and that one can be answered.
  await page.getByTestId('load-current').click()
  await expect(page.getByTestId('decision')).toHaveAttribute('data-presentation-version', '2')
  await expect(page.getByTestId('question')).toContainText('Revised:')
  await answer(page, 'accept', 'Answering the revised question.')
  await expect(page.getByTestId('answer-result')).toBeVisible()
  const found = await settlements(factory, alias)
  expect(found).toHaveLength(1)
  expect(found[0]!.presentation_version).toBe(2)
})

test('snapshot binding: a refresh that brings a new version never changes what is being answered', async ({ page, factory }) => {
  const { alias, request } = await freshRequest(factory)
  await signIn(page, factory)
  await openDecision(page, factory, request)
  await page.locator('[data-choice="reject"]').click()
  await page.getByTestId('rationale').fill('Picked on the version shown.')
  const before = await page.getByTestId('question').textContent()
  await factory.control('/request/revise', { alias })
  let sent = 0
  page.on('request', (r) => {
    if (r.url().endsWith('/decisions/answer')) sent += 1
  })
  await page.getByRole('button', { name: 'Refresh' }).click()
  // The screen still shows version 1, says the question changed, clears the choice and sends nothing.
  await expect(page.getByTestId('question-changed')).toBeVisible()
  await expect(page.getByTestId('question')).toHaveText(before!)
  await expect(page.getByTestId('decision')).toHaveAttribute('data-presentation-version', '1')
  await expect(page.locator('[data-choice] input:checked')).toHaveCount(0)
  await expect(page.getByTestId('send-answer')).toHaveCount(0)
  expect(sent).toBe(0)
  await page.getByTestId('load-current').click()
  await expect(page.getByTestId('decision')).toHaveAttribute('data-presentation-version', '2')
  const posted = page.waitForRequest((r) => r.url().endsWith('/decisions/answer') && r.method() === 'POST')
  await answer(page, 'reject', 'Answering the version now shown.')
  expect(JSON.parse((await posted).postData() ?? '{}')).toMatchObject({ request_id: request, presentation_version: 2 })
  await expect(page.getByTestId('answer-result')).toBeVisible()
  expect((await settlements(factory, alias))[0]!.presentation_version).toBe(2)
})

test('answer as a member outside the project\'s scope: refused as out of scope beside the action', async ({ page, factory }) => {
  // A project owner of project-a opens a decision presented to them; then a steward narrows their scope to
  // project-b. Their answer is refused by name as outside their scope, and nothing settles.
  const { alias, request } = await freshRequest(factory, 'mover')
  await signIn(page, factory, 'mover')
  try {
    await openDecision(page, factory, request)
    await factory.control('/member/scope', { principal: 'mover', scope: ['project-b'] })
    await answer(page, 'accept', 'Answering after my scope moved.')
    const refusal = page.getByTestId('answer-bar').getByTestId('refusal')
    await expect(refusal).toHaveAttribute('data-refusal', 'unauthorized:out_of_scope')
    await expect(refusal).toContainText('Outside your scope')
    await expect(page.getByTestId('answer-result')).toHaveCount(0)
    expect(await settlements(factory, alias)).toHaveLength(0)
  } finally {
    await factory.control('/member/scope', { principal: 'mover', scope: ['project-a'] })
  }
})

test('a member the request was not presented to: the answer is refused by name beside the action', async ({ page, factory }) => {
  const { alias, request } = await freshRequest(factory)
  await signIn(page, factory, 'owner2')
  await openDecision(page, factory, request)
  await answer(page, 'accept', 'Answering as another member.')
  const refusal = page.getByTestId('answer-bar').getByTestId('refusal')
  await expect(refusal).toHaveAttribute('data-refusal', /^unauthorized:/)
  await expect(page.getByTestId('answer-result')).toHaveCount(0)
  expect(await settlements(factory, alias)).toHaveLength(0)
})

test('the answer needs a choice and a rationale before anything is sent', async ({ page, factory }) => {
  const { request } = await freshRequest(factory)
  await signIn(page, factory)
  await openDecision(page, factory, request)
  let sent = 0
  page.on('request', (r) => {
    if (r.url().endsWith('/decisions/answer')) sent += 1
  })
  await page.getByTestId('send-answer').click()
  await expect(page.locator('.answer-problem')).toHaveText('Pick one of the choices first.')
  await page.locator('[data-choice="reject"]').click()
  await page.getByTestId('send-answer').click()
  await expect(page.locator('.answer-problem')).toHaveText('Add a rationale: say briefly why.')
  expect(sent).toBe(0)
})
