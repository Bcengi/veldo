import { conversationOf, expect, guard, newConversation, pageAs, routeOf, send, test, type ConversationFactory } from './conversation-fixtures'
import type { Page } from '@playwright/test'

/**
 * VELDO-0179 AC1 and AC2: the conversation screens against the real API (e2e/conversation_harness.py), every turn run
 * by a fake engine. Each test's title begins with its row name; scripts/suites/134_veldo_0179_conversation_screens.py
 * reads the rows from the JSON report.
 *
 * ac1/journey: open a conversation with New conversation, send two messages and see both replies, the owner writes on
 *   Telegram and the turn and its reply appear without a reload, change the role, attach the fixture project, close.
 * ac1/as-written: a message and a reply holding markup are shown exactly as the API serves them, never as markup.
 * ac1/stale-version: a role change sent on an older version is refused stale_version, named beside the role control,
 *   and nothing is written.
 * ac1/list: the list shows open conversations first, then closed, each with its opening words, role and last activity.
 * ac1/api-only: every request is a published route of this origin; the client log keeps route, outcome and latency and
 *   never a message's text, and the metrics and traces count and join what the screen sent.
 * ac2/terminal: a running turn's terminal opens from the conversation screen in one tap and follows the turn live
 *   (its tool call, the command's output with its redaction mark and its error line, while the turn runs), then shows
 *   the whole record with its line count and digest; every line on screen matches the record in sequence, stream,
 *   receive time and redaction marks.
 */

const DESKTOP = { width: 1280, height: 860 }

const turn = (page: Page, sequence: number) => page.getByTestId(`turn-${sequence}`)

async function replied(page: Page, sequence: number, reply: string) {
  await expect(turn(page, sequence).getByTestId('turn-reply')).toHaveText(reply, { timeout: 30_000 })
}

test('ac1/journey: open, two messages and their replies, a Telegram turn live, role, project and close', async ({ browser, factory }) => {
  test.setTimeout(240_000)
  await factory.pace(0.1)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  let loads = 0
  const id = await newConversation(page, factory)
  page.on('load', () => (loads += 1))
  await expect(page.getByTestId('turns-empty')).toBeVisible()
  const replies = ['The deploy step failed at migrate: the schema lock timed out.', 'It runs again at 14:00 with a longer lock timeout.']
  await factory.replies(replies)
  await send(page, 'Why did the deploy step fail this morning?')
  await expect(turn(page, 1).getByTestId('turn-message')).toHaveText('Why did the deploy step fail this morning?')
  await replied(page, 1, replies[0]!)
  await expect(turn(page, 1).getByTestId('turn-outcome')).toHaveText('completed')
  await send(page, 'When does it run again?')
  await replied(page, 2, replies[1]!)
  // The owner continues the same conversation from Telegram: the turn and its reply appear without a reload.
  await factory.replies(['Yesterday the same step passed in four minutes.'])
  const routed = await factory.telegram(id, 'And what happened yesterday?')
  expect(routed.routed?.outcome, JSON.stringify(routed)).toBe('applied')
  await expect(turn(page, 3).getByTestId('turn-message')).toHaveText('And what happened yesterday?', { timeout: 30_000 })
  await replied(page, 3, 'Yesterday the same step passed in four minutes.')
  expect(loads, 'no reload happened').toBe(0)
  // The role control lists the default team's roles with the current one marked and sends set_role on the version.
  const options = await page.getByTestId('role-select').locator('option').allTextContents()
  expect(options).toContain('assistant (current)')
  expect(options).toContain('assistant_codex')
  await page.getByTestId('role-select').selectOption('assistant_codex')
  await page.getByTestId('role-change').click()
  await expect(page.getByTestId('conversation-current-role')).toHaveText('Role assistant_codex')
  expect((await factory.stored(id)).conversation.role).toBe('assistant_codex')
  // The project control lists the projects in his scope and sends attach_project on the version.
  expect(await page.getByTestId('project-select').locator('option').allTextContents()).toContain('veldo')
  await page.getByTestId('project-select').selectOption('veldo')
  await page.getByTestId('project-attach').click()
  await expect(page.getByTestId('conversation-project')).toHaveText('Project veldo')
  const attached = (await factory.stored(id)).conversation
  expect(attached.project).toBe('veldo')
  expect(attached.attachments?.length).toBe(1)
  // Close through conversations.close; the message box says so and takes nothing.
  await page.getByTestId('conversation-close').click()
  await expect(page.getByTestId('conversation-state')).toHaveText('Closed')
  expect((await factory.stored(id)).conversation.status).toBe('closed')
  await expect(page.getByTestId('message-text')).toBeDisabled()
  expect((await factory.stored(id)).turns.map((t) => t.sequence)).toEqual([1, 2, 3])
  await page.context().close()
})

test('ac1/as-written: a message and a reply holding markup are shown as written, never rendered', async ({ browser, factory }) => {
  test.setTimeout(120_000)
  await factory.pace(0.1)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  await newConversation(page, factory)
  const reply = 'Fixed in <b>migrate</b> & <i>seed</i>; see <a href="https://example.invalid">this</a> <img src=x onerror="window.__ran=1">.'
  await factory.replies([reply])
  const message = 'Is <b>this</b> bold?'
  await send(page, message)
  await replied(page, 1, reply)
  const shown = turn(page, 1)
  expect(await shown.getByTestId('turn-reply').evaluate((el) => el.textContent)).toBe(reply)
  expect(await shown.getByTestId('turn-message').evaluate((el) => el.textContent)).toBe(message)
  for (const part of ['turn-reply', 'turn-message'])
    expect(await shown.getByTestId(part).locator('*').count(), `no element inside ${part}`).toBe(0)
  expect(await page.evaluate(() => (window as unknown as { __ran?: number }).__ran ?? 0)).toBe(0)
  await page.context().close()
})

test('ac1/stale-version: a role change on an older version is refused stale_version beside the role control', async ({ browser, factory }) => {
  test.setTimeout(120_000)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  const id = await newConversation(page, factory)
  // The screen stops hearing the journal (the stream is held open with nothing sent), so it keeps the version it read
  // while the owner changes the role elsewhere: the screen's version is now an older one.
  await page.route(/\/events\/stream/, () => undefined)
  await page.reload()
  await expect(page.getByTestId('conversation-current-role')).toHaveText('Role assistant')
  const before = await factory.roleElsewhere(id, 'assistant_codex')
  expect(before.conversation?.version).toBe(2)
  await page.getByTestId('role-select').selectOption('assistant_codex')
  await page.getByTestId('role-change').click()
  const refusal = page.getByTestId('conversation-controls').locator('[data-refusal]')
  await expect(refusal).toBeVisible()
  await expect(refusal).toHaveAttribute('data-refusal', /^stale_version/)
  await expect(page.getByTestId('conversation-controls')).toContainText('stale_version')
  const stored = (await factory.stored(id)).conversation
  expect([stored.version, stored.role]).toEqual([2, 'assistant_codex'])
  await page.context().close()
})

test('ac1/list: open conversations first, then closed, each with its opening words, role and last activity', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  await factory.pace(0.05)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  const words: Record<string, string> = {}
  for (const opening of ['List one: why is the importer slow on large files today', 'List two: plan the release notes', 'List three: check the gate timing']) {
    const id = await newConversation(page, factory)
    await send(page, opening)
    await expect(turn(page, 1).getByTestId('turn-reply')).toBeVisible({ timeout: 30_000 })
    words[id] = opening
  }
  const first = Object.keys(words)[0]!
  await page.goto(`${factory.origin}/conversations/${encodeURIComponent(first)}`)
  await page.getByTestId('conversation-close').click()
  await expect(page.getByTestId('conversation-state')).toHaveText('Closed')
  await page.goto(factory.origin + '/conversations')
  const cards = page.locator('[data-testid="conversations"] li[data-conversation]')
  await expect(cards.first()).toBeVisible()
  const statuses = await cards.evaluateAll((li) => li.map((x) => x.getAttribute('data-status')))
  const firstClosed = statuses.indexOf('closed')
  expect(firstClosed, `open first: ${statuses}`).toBeGreaterThan(0)
  expect(statuses.slice(firstClosed).every((s) => s === 'closed'), `closed after every open: ${statuses}`).toBe(true)
  for (const [id, opening] of Object.entries(words)) {
    const card = page.locator(`li[data-conversation="${id}"]`)
    const expected = opening.split(/\s+/).slice(0, 12).join(' ') + (opening.split(/\s+/).length > 12 ? ' ...' : '')
    await expect(card.getByTestId('conversation-opening')).toHaveText(expected)
    await expect(card.getByTestId('conversation-role')).toHaveText('Role assistant')
    await expect(card.getByTestId('conversation-activity')).toContainText(/Last activity \d\d:\d\d/)
  }
  await expect(page.locator(`li[data-conversation="${first}"]`)).toHaveAttribute('data-status', 'closed')
  await page.context().close()
})

test('ac1/api-only: every request is a published route; the client log keeps no text; metrics and traces join', async ({ browser, factory }) => {
  test.setTimeout(150_000)
  await factory.pace(0.1)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  const watch = await guard(page)
  const id = await newConversation(page, factory)
  const message = 'Secret words of the owner: lantern seventeen.'
  const reply = 'Reply words: harbor ninety.'
  await factory.replies([reply])
  await send(page, message)
  await replied(page, 1, reply)
  await turn(page, 1).getByTestId('turn-terminal').click()
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  const outside = watch.requests.filter((r) => new URL(r.url).origin !== factory.origin)
  const unrouted = watch.requests.filter((r) => new URL(r.url).pathname.startsWith('/api/') && !routeOf(r.method, r.url, factory.domain))
  expect(outside.map((r) => r.url)).toEqual([])
  expect(unrouted.map((r) => `${r.method} ${r.url}`)).toEqual([])
  expect(await watch.violations()).toEqual([])
  const telemetry = await page.evaluate(() => JSON.parse(JSON.stringify((window as unknown as { __veldoConversations: unknown }).__veldoConversations)))
  const text = JSON.stringify(telemetry)
  expect(text).not.toContain('lantern')
  expect(text).not.toContain('harbor')
  expect(text).not.toMatch(/__Host-veldo-session|cookie/i)
  const routes = new Set((telemetry.log as { route: string; outcome: string; ms: number }[]).map((e) => e.route))
  for (const route of ['conversations.open', 'conversations.read', 'messages.send']) expect(routes.has(route), route).toBe(true)
  for (const entry of telemetry.log) expect(Object.keys(entry).sort()).toEqual(['at', 'ms', 'outcome', 'route'])
  expect(telemetry.metrics.messages_sent).toBe(1)
  expect(telemetry.metrics.conversations_opened).toBe(1)
  const stored = await factory.stored(id)
  const trace = (telemetry.traces as { conversation: string; sequence: number; dispatch: string; api_request_id: string }[]).find((t) => t.conversation === id)
  expect(trace?.api_request_id).toMatch(/^api-/)
  expect([trace?.sequence, trace?.dispatch]).toEqual([1, stored.turns[0]!.dispatch_id])
  const kept = await page.evaluate(() => [JSON.stringify(localStorage), JSON.stringify(sessionStorage), location.href])
  expect(kept.join(' ')).not.toMatch(/lantern|harbor|token|csrf/i)
  await page.context().close()
})

async function screenLines(page: Page) {
  return page.locator('[data-testid="lines"] li.tline').evaluateAll((items) =>
    items.map((li) => ({
      seq: Number(li.getAttribute('data-seq')),
      stream: li.getAttribute('data-stream'),
      at: li.querySelector('time')?.getAttribute('datetime') ?? null,
      redacted: Array.from(li.querySelectorAll('.tline-redacted')).map((x) => (x.textContent ?? '').replace(/^redacted /, '')),
      text: li.textContent ?? '',
    })),
  )
}

async function matchesRecord(page: Page, factory: ConversationFactory, id: string, sequence: number) {
  const record = await factory.record(id, sequence)
  const shown = await screenLines(page)
  expect(shown.map((l) => l.seq)).toEqual(record.lines.map((l) => l.seq))
  expect(shown.map((l) => l.stream)).toEqual(record.lines.map((l) => l.stream))
  expect(shown.map((l) => l.at)).toEqual(record.lines.map((l) => new Date(l.at * 1000).toISOString()))
  expect(shown.map((l) => l.redacted)).toEqual(record.lines.map((l) => l.redacted))
  return record
}

test('ac2/terminal: the running turn\'s terminal opens in one tap and follows the record live, then complete', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  await factory.pace(0.6)
  const page = await pageAs(browser, factory, 'owner', DESKTOP)
  const id = await newConversation(page, factory)
  await factory.hold(id, true)
  await send(page, 'Run the deploy step and tell me what fails.')
  const marker = turn(page, 1).getByTestId('turn-marker')
  await expect(marker).toHaveAttribute('data-marker', 'running', { timeout: 30_000 })
  // One tap from the conversation screen.
  await turn(page, 1).getByTestId('turn-watch').click()
  await expect(page.getByTestId('turn-screen')).toBeVisible()
  expect(conversationOf(page)).toBe(id)
  const terminal = page.getByTestId('terminal')
  await expect(terminal).toHaveAttribute('data-state', 'live')
  const lines = page.locator('[data-testid="lines"] li.tline')
  // The slow fake engine's lines arrive while the turn runs: the tool call, the command output, the error line.
  await expect(lines.filter({ hasText: 'cat deploy.env' })).toHaveCount(1, { timeout: 30_000 })
  await expect(lines.filter({ hasText: 'DEPLOY_STEP=migrate' })).toHaveCount(1, { timeout: 30_000 })
  await expect(lines.filter({ hasText: 'fake engine error: the deploy step of turn 1 failed' })).toHaveCount(1, { timeout: 30_000 })
  await expect(page.getByTestId('turn-status')).toHaveAttribute('data-marker', 'running')
  await expect(terminal).toHaveAttribute('data-state', 'live')
  const secret = (await factory.control<{ secret: string }>('/conversation/secret')).secret
  expect(await terminal.textContent()).not.toContain(secret)
  const running = await matchesRecord(page, factory, id, 1)
  expect(running.committed).toBeNull()
  expect(running.lines.some((l) => l.redacted.length > 0)).toBe(true)
  expect(running.lines.some((l) => l.stream === 'stderr')).toBe(true)
  // The turn ends: the terminal completes with the record's line count and digest.
  await factory.hold(id, false)
  await expect(terminal).toHaveAttribute('data-state', 'ended', { timeout: 30_000 })
  await expect(page.getByTestId('turn-status')).toHaveAttribute('data-marker', 'ended', { timeout: 30_000 })
  const ended = await matchesRecord(page, factory, id, 1)
  expect(ended.committed?.lines).toBe(ended.lines.length)
  await expect(page.getByTestId('line-count')).toHaveText(`${ended.lines.length} lines`)
  await expect(terminal).toContainText(`${ended.committed!.lines} lines committed`)
  await expect(terminal).toContainText(ended.committed!.digest)
  await page.context().close()
})
