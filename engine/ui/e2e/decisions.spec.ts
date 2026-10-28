import type { Page } from '@playwright/test'
import { expect, signIn, test, type Factory } from './fixtures'

/**
 * VELDO-0145 AC3: each pending decision exactly as presented, answered inline through the API bound to the
 * presentation version shown, settling once with Telegram; each refusal named beside the action.
 */

let serial = 0
async function freshRequest(factory: Factory) {
  serial += 1
  const alias = `dx${Date.now() % 100000}${serial}`
  const { request } = await factory.control<{ request: string }>('/request/open', { alias })
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
  await expect(page.locator('.answer-binding')).toContainText(`presentation version ${receipt.presentation_version} of request version ${receipt.request_version}`)
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
  await expect(page.locator('.answer-binding')).toContainText('presentation version 1')
  await factory.control('/request/revise', { alias })
  await answer(page, 'accept', 'Answering what the screen showed.')
  const refusal = page.getByTestId('answer-bar').getByTestId('refusal')
  await expect(refusal).toHaveAttribute('data-refusal', 'stale_version:stale_presentation')
  await expect(refusal).toContainText('The question changed after you opened it')
  await expect(page.getByTestId('answer-result')).toHaveCount(0)
  expect(await settlements(factory, alias)).toHaveLength(0)
  // Reloading shows the current presentation, which can then be answered.
  await page.reload()
  await expect(page.locator('.answer-binding')).toContainText('presentation version 2')
  await answer(page, 'accept', 'Answering the revised question.')
  await expect(page.getByTestId('answer-result')).toBeVisible()
  const found = await settlements(factory, alias)
  expect(found).toHaveLength(1)
  expect(found[0]!.presentation_version).toBe(2)
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
