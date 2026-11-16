import { mkdirSync } from 'node:fs'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import type { Browser, Page, Route } from '@playwright/test'
import { expect, guard, routeOf, signIn, test, type SpaceFactory } from './space-fixtures'

/**
 * VELDO-0319: the console's Space screen. Each test's title begins with its row name; the Python suite
 * scripts/suites/150_veldo_0319_space_ui.py reads the rows from the JSON report.
 *
 * ac1/usage-table: the usage table's figure for every project, ticket and kind equals the sum of the harness's
 *   item records that are still there (a deferred item counts), with the plain repository and "No project" as
 *   rows of their own and the totals row; as a table at 1280 px and as a list at 390 px.
 * ac2/pending-removed: Pending removal lists every due and deferred item with its reason in words, its retry
 *   events and its open decision request, the review group's worktrees under their one request by index;
 *   Removed lists every removal with its event, size and free space before and after.
 * ac3/owner-commands: Reconcile and Abandon are sent as signed commands and their results are the API's; a member
 *   who is not the owner is refused each by name, beside the control, and nothing is written.
 * ac3/answer-path: an open request links to the decision it is answered through.
 * ac4/live-no-clock: with the page's clock stopped, a hold the ledger records reaches the Pools section, and a
 *   removal the Removed section, through the record stream, without a reload.
 * ac4/runs-list: a run that waits and a run that would have waited show need, free, held and floor on the runs list.
 * ui/states-<width>: the screen's loading, error, empty and populated states, its Abandon confirmation and the
 *   runs list at 360, 390, 1280 and 1440 px: no page-wide overflow, no overlapping controls, the primary action
 *   visible, unclipped, uncovered and 44 px on a phone, axe, and no content security policy violation.
 * ui/api-only: every request the screen makes is a published route of this origin.
 * VELDO_0319_SCREENS=<directory> also writes a screenshot of each populated state, in light and in dark.
 */

const WIDTHS = [
  { width: 360, height: 760 },
  { width: 390, height: 844 },
  { width: 1280, height: 860 },
  { width: 1440, height: 900 },
]
const SCREENS_DIR = process.env.VELDO_0319_SCREENS
const GIB = 1024 ** 3
const LIVE = new Set(['declared', 'present', 'due', 'deferred', 'removing', 'kept'])

async function pageAs(browser: Browser, factory: SpaceFactory, who: string, viewport: { width: number; height: number }) {
  const phone = viewport.width < 768
  const context = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone })
  const page = await context.newPage()
  // The first load of the build on a busy host can take longer than one action's wait: the sign-in screen is
  // awaited here with room, then signIn drives it.
  await page.goto(factory.origin + '/sign-in')
  await expect(page.getByTestId('sign-in')).toBeVisible({ timeout: 45_000 })
  await signIn(page, factory, who)
  return page
}

async function openSpace(page: Page, factory: SpaceFactory) {
  await page.goto(factory.origin + '/space')
  await expect(page.getByTestId('space')).toBeVisible()
  await expect(page.getByTestId('live-meta')).toHaveAttribute('data-live', 'live')
}

/** The sums of the harness's own item records, as the fixture holds them: by scope, by ticket and by kind. */
async function fixtureSums(factory: SpaceFactory) {
  const sums = new Map<string, { bytes: number; items: number }>()
  const add = (key: string, bytes: number) => {
    const cell = sums.get(key) ?? { bytes: 0, items: 0 }
    cell.bytes += bytes
    cell.items += 1
    sums.set(key, cell)
  }
  for (const item of await factory.kind('space_item')) {
    const d = item.data
    if (!LIVE.has(d.state)) continue
    const scope = `${d.owner.scope.type === 'no_project' ? 'no_project' : d.owner.scope.type}:${d.owner.scope.id ?? ''}`
    const bytes = d.size?.bytes ?? 0
    add('total', bytes)
    add(scope, bytes)
    add(`${scope}/${d.owner.ticket ?? ''}`, bytes)
    add(`${scope}/${d.owner.ticket ?? ''}/${d.kind}`, bytes)
  }
  return sums
}

for (const viewport of [{ width: 1280, height: 860 }, { width: 390, height: 844 }]) {
  test(`ac1/usage-table-${viewport.width}: the usage figures equal the sums of the item records at ${viewport.width}px`, async ({ browser, factory }) => {
    const page = await pageAs(browser, factory, 'owner', viewport)
    await openSpace(page, factory)
    const sums = await fixtureSums(factory)
    const usage = page.getByTestId('space-usage')
    const shown = await usage.locator('[data-usage]').evaluateAll((rows) =>
      rows.map((row) => {
        const bytes = row.querySelector('[data-bytes]') as HTMLElement
        const items = (row.querySelector('[data-items]') as HTMLElement) ?? bytes
        return { key: (row as HTMLElement).dataset.usage!, bytes: Number(bytes.dataset.bytes), items: Number(items.dataset.items), text: row.textContent ?? '' }
      }),
    )
    // Every sum of the fixture is a row, every row is a sum of the fixture, and the figures are equal.
    expect(shown.map((r) => r.key).sort()).toEqual([...sums.keys()].sort())
    for (const row of shown) expect({ key: row.key, bytes: row.bytes, items: row.items }).toEqual({ key: row.key, ...sums.get(row.key)! })
    // A deferred item is counted: the in-use build folder is 4.1 GiB of its ticket's build output.
    const busy = shown.find((r) => r.key === 'project:project-a/VELDO-9149/build_output')!
    expect(busy.bytes).toBe(4 * GIB + 100 * 1024 ** 2)
    expect(busy.text).toContain('4.1 GiB')
    // The plain repository and no project are rows of their own, beside the projects.
    const top = await usage.locator('[data-level="0"]').evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.usage))
    expect(top.filter((k) => k !== 'total')).toEqual(['project:project-a', 'project:project-b', 'plain_repository:/home/owner/tools', 'no_project:'])
    await expect(usage.locator('[data-usage="plain_repository:/home/owner/tools"]')).toContainText('Plain repository')
    await expect(usage.locator('[data-usage="no_project:"]')).toContainText('No project')
    await expect(usage.locator('[data-usage="total"]')).toContainText('Total')
    // A removed and a gone item are in no figure.
    expect(shown.some((r) => r.key.includes('VELDO-9143') || r.key.includes('VELDO-9142'))).toBe(false)
    await page.context().close()
  })
}

test('ac2/pending-removed: every due and deferred item with its reason, retry and request; every removal with its event, size and free space', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await openSpace(page, factory)
  const ids = await factory.ids()
  const items = await factory.kind('space_item')
  const pending = page.getByTestId('space-pending')
  const want = items.filter((i) => i.data.state === 'due' || i.data.state === 'deferred').map((i) => i.id).sort()
  const listed = await pending.locator('[data-item]').evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.item!))
  expect([...listed].sort()).toEqual(want)
  expect(want.length).toBe(6)
  // The in-use folder: its reason in words, the events that retry it, and that no request is open for it.
  const busy = pending.locator(`[data-item="${ids.busy}"]`)
  await expect(busy).toHaveAttribute('data-state', 'deferred')
  await expect(busy.getByTestId('pending-reason')).toHaveText('In use by process 4412')
  await expect(busy.getByTestId('pending-retry')).toHaveText('Retried at run finished, ticket ended, project ended')
  await expect(busy.getByTestId('pending-request')).toHaveText('No decision request is open for it')
  await expect(busy).toContainText('At run finished, 3 times')
  // The due item says so.
  await expect(pending.locator(`[data-item="${ids.due}"]`).getByTestId('pending-reason')).toHaveText('Due since ticket ended; the removal has not run yet')
  // A worktree with a request of its own.
  const solo = pending.locator(`[data-request="${ids.solo_alias}"]`)
  await expect(solo.locator(`[data-item="${ids.solo}"]`).getByTestId('pending-reason')).toHaveText('Uncommitted changes in 3 files')
  await expect(solo.getByTestId('space-not-yours')).toBeVisible()
  // The review group: three worktrees under their one request, each with its index and its own answers.
  const group = pending.locator(`[data-request="${ids.group_alias}"]`)
  expect(await group.locator('[data-item]').evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.index))).toEqual(['1', '2', '3'])
  await expect(group.locator(`[data-item="${ids.review2}"]`).getByTestId('pending-reason')).toHaveText('Uncommitted changes in 5 files')
  await expect(group.locator(`[data-item="${ids.review2}"]`).getByTestId('member-picks')).toHaveText('accept save w2, accept keep w2, accept discard w2')
  await expect(group.locator(`[data-item="${ids.review3}"]`).getByTestId('member-picks')).toContainText('None in this request')
  await expect(group.getByTestId('space-answer')).toBeVisible()

  // Removed: every removal, with its event, its size and the pool's free space before and after.
  const removed = page.getByTestId('space-removed')
  const gone = items.filter((i) => i.data.state === 'removed')
  expect(await removed.locator('[data-item]').count()).toBe(gone.length)
  for (const item of gone) {
    const row = removed.locator(`[data-item="${item.id}"]`)
    const r = item.data.removal
    await expect(row.getByTestId('removed-event')).toContainText(String(r.event).replace(/_/g, ' '))
    await expect(row.getByTestId('removed-size')).toHaveAttribute('data-bytes', String(r.bytes))
    await expect(row.getByTestId('removed-free')).toHaveAttribute('data-before', String(r.pool_free_before))
    await expect(row.getByTestId('removed-free')).toHaveAttribute('data-after', String(r.pool_free_after))
  }
  await expect(removed.locator(`[data-item="${ids['gone-build']}"]`).getByTestId('removed-free')).toContainText('30.0 GiB free before, 37.0 GiB after')
  await expect(removed.locator(`[data-item="${ids['gone-volume']}"]`)).toContainText('The host figure did not change (39.0 GiB free on main)')
  await expect(removed.locator(`[data-item="${ids['gone-tree']}"]`)).toContainText('2 refs kept, 1 snapshot saved')
  // No raw record text reaches the screen.
  expect(await page.getByTestId('space').innerText()).not.toMatch(/[{}]|\bnull\b|undefined|\[object/)
  await page.context().close()
})

test('ac3/owner-commands: Reconcile and Abandon are signed commands; a member who is not the owner is refused each', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  const ids = await factory.ids()
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  const watch = await guard(page)
  await openSpace(page, factory)
  // Reconcile, for one project: accepted, and what it adopted reaches the screen from the journal.
  const trees = page.getByTestId('space-worktrees')
  const before = await trees.locator('[data-worktree]').count()
  await page.getByTestId('space-reconcile-project').selectOption('project-b')
  await page.getByTestId('space-reconcile-run').click()
  const reconciled = page.getByTestId('space-reconcile-result')
  await expect(reconciled).toContainText('Reconcile ran for project-b (reconciled)')
  expect(await reconciled.getAttribute('data-refusal')).toBeNull()
  await expect(trees.locator('[data-worktree]')).toHaveCount(before + 1)
  // Abandon: confirmed inline, sent with the item and the version shown, and the row leaves when the record does.
  const kept = trees.locator(`[data-worktree="${ids.kept}"]`)
  await expect(kept).toContainText('Kept by you')
  const shown = Number(await kept.getAttribute('data-version'))
  await kept.getByTestId('space-abandon').click()
  await kept.getByTestId('space-abandon-confirm').click()
  await expect(trees.locator(`[data-worktree="${ids.kept}"]`)).toHaveCount(0)
  await expect(page.getByTestId('space-removed').locator(`[data-item="${ids.kept}"]`).getByTestId('removed-event')).toContainText('worktree abandoned')
  // Abandon of a worktree with unique work: it stays, and the answer says what stays for the owner's Discard.
  const solo = trees.locator(`[data-worktree="${ids.solo}"]`)
  await solo.getByTestId('space-abandon').click()
  await solo.getByTestId('space-abandon-confirm').click()
  await expect(solo.getByTestId('space-abandon-result')).toContainText('1 worktree stays until your Discard, which saves first')
  await expect(solo).toHaveAttribute('data-state', 'deferred')
  // Both were POSTs of published routes carrying exactly their fields.
  const sent = watch.requests.filter((r) => r.method === 'POST').map((r) => routeOf(r.method, r.url, factory.domain))
  expect(sent).toEqual(['space.reconcile', 'space.abandon', 'space.abandon'])
  expect((await factory.entity(ids.kept))!.version).toBe(shown + 1)
  await page.context().close()

  // A project owner whose scope is one project is not the owner of the space ledger: each command is refused by
  // name, beside its control, and nothing is written.
  const other = await pageAs(browser, factory, 'mover', { width: 1280, height: 860 })
  await openSpace(other, factory)
  const tree = other.getByTestId('space-worktrees').locator(`[data-worktree="${ids.tree}"]`)
  const version = (await factory.entity(ids.tree))!.version
  const adopted = (await factory.kind('space_reconcile')).length
  await other.getByTestId('space-reconcile-run').click()
  await expect(other.getByTestId('space-reconcile-result')).toHaveAttribute('data-refusal', 'unauthorized:not_owner')
  await expect(other.getByTestId('space-reconcile-result')).toContainText('Not run: unauthorized:not_owner')
  await tree.getByTestId('space-abandon').click()
  await tree.getByTestId('space-abandon-confirm').click()
  await expect(tree.getByTestId('space-abandon-result')).toHaveAttribute('data-refusal', 'unauthorized:not_owner')
  await expect(tree.getByTestId('space-abandon-result')).toContainText('Not abandoned: unauthorized:not_owner')
  expect((await factory.entity(ids.tree))!.version).toBe(version)
  expect((await factory.entity(ids.tree))!.data.state).toBe('present')
  expect((await factory.kind('space_reconcile')).length).toBe(adopted)
  await other.context().close()
})

test('ac3/answer-path: an open request links to the decision it is answered through', async ({ browser, factory }) => {
  const ids = await factory.ids()
  const page = await pageAs(browser, factory, 'owner', { width: 390, height: 844 })
  await openSpace(page, factory)
  await page.getByTestId('space-pending').locator(`[data-request="${ids.group_alias}"]`).getByTestId('space-answer').click()
  await expect(page.getByTestId('decision')).toHaveAttribute('data-request', ids.request)
  await expect(page.getByTestId('send-answer')).toBeVisible()
  await page.context().close()
})

test('ac4/live-no-clock: with the clock stopped, a hold and a removal reach the screen from the record stream', async ({ browser, factory }) => {
  test.setTimeout(120_000)
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.clock.install()
  await openSpace(page, factory)
  const meta = page.getByTestId('live-meta')
  const seq0 = Number(await meta.getAttribute('data-seq'))
  const navigations: string[] = []
  page.on('framenavigated', (frame) => frame === page.mainFrame() && navigations.push(frame.url()))
  // The fixture clock stops: no timer of the page fires from here on.
  await page.clock.pauseAt(new Date(Date.now() + 1000))
  const hold = 'space:hold:dispatch/' + 'c'.repeat(64)
  const reason = { pool: 'main', need: 9 * GIB, free: 33 * GIB, held: 14 * GIB, floor: 20 * GIB }
  await factory.upsert(hold, 'space_hold', { scope: { type: 'project', id: 'project-b' }, needs: { main: 9 * GIB }, source: { main: 'measured' },
    state: 'waiting', reason, used: {}, retry_asked: true, freed: false })
  const card = page.getByTestId('space-pools').locator(`[data-hold="${hold}"]`)
  await expect(card).toHaveAttribute('data-state', 'waiting')
  for (const [name, text] of [['need', '9.0 GiB'], ['free', '33.0 GiB'], ['held', '14.0 GiB'], ['floor', '20.0 GiB']])
    await expect(card.locator(`[data-number="${name}"] dd`)).toHaveText(text!)
  expect(Number(await meta.getAttribute('data-seq'))).toBeGreaterThan(seq0)
  // The run is started on advice (report mode): the same hold, advised, with the numbers kept.
  await factory.upsert(hold, 'space_hold', { scope: { type: 'project', id: 'project-b' }, needs: { main: 9 * GIB }, source: { main: 'measured' },
    state: 'advised', reason, used: {}, retry_asked: true, freed: false })
  await expect(card).toHaveAttribute('data-state', 'advised')
  await expect(page.getByTestId('space-pools').locator('[data-pool="main"] [data-holds="advised"]').locator(`[data-hold="${hold}"]`)).toBeVisible()
  // A removal the ledger records reaches Removed and leaves Pending removal.
  const ids = await factory.ids()
  const due = (await factory.entity(ids.due))!
  await factory.upsert(ids.due, 'space_item', { ...due.data, state: 'removed', removal: { event: 'ticket_ended', method: 'rmtree', bytes: 2 * GIB, pool: 'main',
    pool_free_before: 39 * GIB, pool_free_after: 41 * GIB, freed: 2 * GIB, host: null } })
  await expect(page.getByTestId('space-removed').locator(`[data-item="${ids.due}"]`).getByTestId('removed-free')).toContainText('39.0 GiB free before, 41.0 GiB after')
  await expect(page.getByTestId('space-pending').locator(`[data-item="${ids.due}"]`)).toHaveCount(0)
  expect(navigations).toEqual([])
  await page.context().close()
})

test('ac4/runs-list: a waiting run and a run that would have waited show need, free, held and floor on the runs list', async ({ browser, factory }) => {
  const ids = await factory.ids()
  const state = await factory.state()
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.goto(factory.origin + '/runs')
  await expect(page.getByTestId('runs')).toBeVisible()
  // Report mode: the live run was started on advice; its row says what it would have waited for.
  const advised = page.locator(`[data-dispatch="${state.dispatches.live}"]`).getByTestId('run-space')
  await expect(advised).toHaveAttribute('data-hold', 'advised')
  await expect(advised).toHaveText('Would have waited for space on main: need 6.0 GiB, free 38.0 GiB, held 14.0 GiB, floor 20.0 GiB')
  // A waiting run has no dispatch yet: it is a row of its own, with no run to open.
  const waiting = page.locator(`[data-hold="${ids.hold_waiting}"]`)
  await expect(waiting.getByTestId('run-space')).toHaveText('Waiting for space on main: need 12.0 GiB, free 41.3 GiB, held 14.0 GiB, floor 20.0 GiB')
  await expect(waiting).toContainText('Waiting for space')
  expect(await waiting.evaluate((el) => el.tagName)).toBe('DIV')
  // Every other run has no such line.
  expect(await page.getByTestId('run-space').count()).toBe(2)
  // The same numbers are on the Pools section.
  await openSpace(page, factory)
  const pool = page.getByTestId('space-pools').locator('[data-pool="main"]')
  await expect(pool.getByTestId('pool-floor')).toContainText('20.0 GiB')
  // Held is what the admitted and the advised holds still hold: each need less what the run's own items use.
  const held = (await factory.kind('space_hold'))
    .filter((h) => ['admitted', 'advised'].includes(h.data.state) && 'main' in h.data.needs)
    .reduce((sum, h) => sum + Math.max(0, h.data.needs.main - (h.data.used?.main ?? 0)), 0)
  expect(held).toBeGreaterThanOrEqual(14 * GIB)
  await expect(pool.getByTestId('pool-held')).toContainText(`${(held / GIB).toFixed(1)} GiB`)
  const card = pool.locator(`[data-hold="${ids.hold_advised}"]`)
  for (const [name, text] of [['need', '6.0 GiB'], ['free', '38.0 GiB'], ['held', '14.0 GiB'], ['floor', '20.0 GiB']])
    await expect(card.locator(`[data-number="${name}"] dd`)).toHaveText(text!)
  await expect(card.locator('a')).toContainText('VELDO-9146')
  await page.context().close()
})

test('ui/api-only: every request of the screen is a published route of this origin', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  const watch = await guard(page)
  await openSpace(page, factory)
  const api = watch.requests.filter((r) => new URL(r.url).pathname.startsWith('/api/'))
  expect(api.every((r) => new URL(r.url).origin === factory.origin)).toBe(true)
  const named = api.map((r) => routeOf(r.method, r.url.split('?')[0]!, factory.domain))
  expect(named.filter((n) => n === null)).toEqual([])
  for (const route of ['space.pools', 'space.usage', 'space.pending', 'space.removed', 'events.stream']) expect(named).toContain(route)
  expect(watch.requests.filter((r) => new URL(r.url).origin !== factory.origin)).toEqual([])
  expect(await watch.violations()).toEqual([])
  // A member scoped to another project sees that project's items and no plain repository or no-project row.
  const narrow = await pageAs(browser, factory, 'bmember', { width: 1280, height: 860 })
  await openSpace(narrow, factory)
  const top = await narrow.getByTestId('space-usage').locator('[data-level="0"]').evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.usage))
  expect(top).toEqual(['project:project-b'])
  await expect(narrow.getByTestId('space-pending-none')).toBeVisible()
  await narrow.context().close()
  await page.context().close()
})

// The states at four widths.

type Opened = { primary: string | null; axe?: boolean }
interface Render {
  name: string
  bare?: boolean
  open(page: Page, factory: SpaceFactory): Promise<Opened>
}

async function holdData(page: Page) {
  const held: Route[] = []
  await page.route(/\/api\/v1\/domains\//, (route) => void held.push(route))
  return async () => {
    await page.unroute(/\/api\/v1\/domains\//)
    for (const route of held) await route.continue().catch(() => undefined)
  }
}

async function dropData(page: Page) {
  await page.route(/\/api\/v1\/domains\/[^/]+\/(?!events)/, (route) => route.abort('connectionreset'))
  return () => page.unroute(/\/api\/v1\/domains\/[^/]+\/(?!events)/)
}

const RENDERS: Render[] = [
  {
    name: 'space-loading',
    async open(page, factory) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/space')
      await expect(page.locator('[data-state="loading"]').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = release
      return { primary: null, axe: false }
    },
  },
  {
    name: 'space-error',
    async open(page, factory) {
      const undo = await dropData(page)
      await page.goto(factory.origin + '/space')
      await expect(page.getByTestId('refusal').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = undo
      return { primary: null }
    },
  },
  {
    name: 'space-empty',
    bare: true,
    async open(page, factory) {
      await page.goto(factory.origin + '/space')
      await expect(page.locator('[data-state="empty"]').first()).toBeVisible()
      return { primary: '[data-testid="space-reconcile-run"]' }
    },
  },
  {
    name: 'space',
    async open(page, factory) {
      await openSpace(page, factory)
      return { primary: '[data-testid="space-reconcile-run"]' }
    },
  },
  {
    name: 'space-pending',
    async open(page, factory) {
      await openSpace(page, factory)
      await page.getByTestId('space-pending').scrollIntoViewIfNeeded()
      return { primary: '[data-testid="space-answer"]' }
    },
  },
  {
    name: 'space-abandon-confirm',
    async open(page, factory) {
      await openSpace(page, factory)
      await page.getByTestId('space-worktrees').getByTestId('space-abandon').first().click()
      return { primary: '[data-testid="space-abandon-confirm"]' }
    },
  },
  {
    name: 'space-reconcile-refused',
    async open(page, factory) {
      await openSpace(page, factory)
      // A dropped connection while the command is sent: the refusal is named beside the control.
      await page.route(/\/space\/reconcile$/, (route) => route.abort('connectionreset'))
      await page.getByTestId('space-reconcile-run').click()
      await expect(page.getByTestId('space-reconcile-result')).toHaveAttribute('data-refusal', /unavailable/)
      ;(page as unknown as { release?: () => Promise<void> }).release = () => page.unroute(/\/space\/reconcile$/)
      return { primary: '[data-testid="space-reconcile-run"]' }
    },
  },
  {
    name: 'runs-space',
    async open(page, factory) {
      await page.goto(factory.origin + '/runs')
      await expect(page.getByTestId('run-space').first()).toBeVisible()
      return { primary: null }
    },
  },
]

interface Problems {
  overflow: number
  overlaps: string[]
  primary: string | null
}

/** The page as rendered: page-wide overflow, overlapping controls and the primary action (VELDO-0131's measure). */
async function measure(page: Page, primary: string | null, phone: boolean): Promise<Problems> {
  if (primary) await page.locator(primary).first().evaluate((el) => el.scrollIntoView({ block: 'center' })).catch(() => undefined)
  return page.evaluate(
    ({ primary, phone }) => {
      const vw = window.innerWidth
      const vh = window.innerHeight
      const overflow = document.documentElement.scrollWidth - vw
      const visible = (el: Element) => {
        const r = el.getBoundingClientRect()
        const s = getComputedStyle(el)
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && r.bottom > 0 && r.top < vh
      }
      const controls = Array.from(document.querySelectorAll('button, a[href], input:not([type=hidden]), textarea, select')).filter(visible)
      const layer = (el: Element): Element | null => {
        for (let n: Element | null = el; n; n = n.parentElement) {
          const position = getComputedStyle(n).position
          if (position === 'fixed' || position === 'sticky' || position === 'absolute') return n
        }
        return null
      }
      const clippedBy = (el: Element) => {
        const r = el.getBoundingClientRect()
        for (let n = el.parentElement; n; n = n.parentElement) {
          const s = getComputedStyle(n)
          if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
            const p = n.getBoundingClientRect()
            if (r.right <= p.left || r.left >= p.right || r.bottom <= p.top || r.top >= p.bottom) return true
          }
        }
        return false
      }
      const label = (el: Element) => (el as HTMLElement).dataset.testid ?? el.getAttribute('aria-label') ?? el.textContent?.trim().slice(0, 30) ?? el.tagName
      const shown = controls.filter((el) => !clippedBy(el))
      const overlaps: string[] = []
      for (let i = 0; i < shown.length; i += 1)
        for (let j = i + 1; j < shown.length; j += 1) {
          const a = shown[i]!
          const b = shown[j]!
          if (a.contains(b) || b.contains(a) || a.closest('label')?.contains(b) || b.closest('label')?.contains(a)) continue
          if (layer(a) !== layer(b)) continue
          const ra = a.getBoundingClientRect()
          const rb = b.getBoundingClientRect()
          const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left)
          const y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top)
          if (x > 1 && y > 1) overlaps.push(`${label(a)} / ${label(b)}`)
        }
      // Text that runs out of its own box is broken layout too: a path or a number that does not wrap.
      const spilled = Array.from(document.querySelectorAll('[data-testid="space"] *, .runs *'))
        .filter((el) => visible(el) && el.children.length === 0 && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).display !== 'inline')
        .map((el) => `spills: ${(el.textContent ?? '').trim().slice(0, 30)}`)
      let problem: string | null = null
      if (primary) {
        const el = Array.from(document.querySelectorAll(primary)).find(visible) ?? document.querySelector(primary)
        if (!el || !visible(el)) problem = 'not visible'
        else {
          const r = el.getBoundingClientRect()
          if (r.left < 0 || r.right > vw || r.top < 0 || r.bottom > vh) problem = `clipped at ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}x${Math.round(r.height)}`
          else {
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
            if (!hit || !(el === hit || el.contains(hit))) problem = `covered by ${hit?.className ?? 'nothing'}`
            else if (phone && (r.height < 44 || r.width < 44)) problem = `target ${Math.round(r.width)}x${Math.round(r.height)}`
          }
        }
      }
      return { overflow, overlaps: overlaps.concat(spilled), primary: problem }
    },
    { primary, phone },
  )
}

async function shoot(page: Page, name: string) {
  if (!SCREENS_DIR) return
  mkdirSync(SCREENS_DIR, { recursive: true })
  // The theme as useTheme puts it on the document: Veldo's data-theme and Nuxt UI's dark and light classes.
  const put = (theme: string) =>
    page.evaluate((t) => {
      const root = document.documentElement
      root.setAttribute('data-theme', t)
      root.classList.toggle('dark', t === 'dark')
      root.classList.toggle('light', t === 'light')
    }, theme)
  const was = (await page.evaluate(() => document.documentElement.getAttribute('data-theme'))) ?? 'light'
  for (const theme of ['light', 'dark']) {
    await put(theme)
    await page.waitForTimeout(150)
    await page.screenshot({ path: path.join(SCREENS_DIR, `${name}-${theme}.png`), fullPage: true })
  }
  await put(was)
}

for (const viewport of WIDTHS) {
  const phone = viewport.width < 768
  test(`ui/states-${viewport.width}: the Space screen's states and the runs list at ${viewport.width}px`, async ({ browser, factory, bare }) => {
    test.setTimeout(300_000)
    const failures: string[] = []
    const seeded = await pageAs(browser, factory, 'owner', viewport)
    const empty = await pageAs(browser, bare, 'owner', viewport)
    for (const render of RENDERS) {
      const page = render.bare ? empty : seeded
      const watch = await guard(page)
      let opened: Opened
      try {
        opened = await render.open(page, render.bare ? bare : factory)
      } catch (error) {
        failures.push(`${render.name}: did not open (${String(error).split('\n')[0]})`)
        // A state that did not open must not leave its held or dropped requests on the page for the next one.
        await (page as unknown as { release?: () => Promise<void> }).release?.()
        ;(page as unknown as { release?: unknown }).release = undefined
        await page.unrouteAll({ behavior: 'ignoreErrors' })
        continue
      }
      const problems = await measure(page, opened.primary, phone)
      if (problems.overflow > 1) failures.push(`${render.name}: page-wide overflow ${problems.overflow}px`)
      if (problems.overlaps.length) failures.push(`${render.name}: ${problems.overlaps.slice(0, 3).join('; ')}`)
      if (problems.primary) failures.push(`${render.name}: primary action ${opened.primary} ${problems.primary}`)
      if (opened.axe !== false && (viewport.width === 390 || viewport.width === 1280)) {
        const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
        for (const v of result.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical'))
          failures.push(`${render.name}: axe ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target}`)
      }
      const violations = await watch.violations()
      if (violations.length) failures.push(`${render.name}: content security policy ${violations[0]}`)
      if (viewport.width === 390 || viewport.width === 1440) await shoot(page, `${viewport.width}-${render.name}`)
      const release = (page as unknown as { release?: () => Promise<void> }).release
      if (release) {
        await release()
        ;(page as unknown as { release?: unknown }).release = undefined
      }
    }
    await seeded.context().close()
    await empty.context().close()
    expect(failures, failures.join('\n')).toEqual([])
  })
}
