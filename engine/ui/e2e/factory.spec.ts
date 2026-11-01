import { mkdirSync } from 'node:fs'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import type { Browser, Page, Route } from '@playwright/test'
import { expect, guard, routeOf, signIn, test, type FactoryUi } from './factory-fixtures'

/**
 * VELDO-0131: the factory screens on phone and desktop. Each test's title begins with its row name (the Python
 * suite scripts/suites/120_veldo_0131_factory_ui.py reads the rows from the JSON report).
 *
 * ac1/screens-<width>: every screen row at 360, 390, 1280 and 1440 px in its loading, empty, error and populated
 *   states (and the live run, the decision and the sheets): no page-wide overflow, no overlapping controls, the
 *   primary action visible, unclipped, uncovered and 44 px on a phone; axe on the real accessibility tree.
 * ac2/live: journal updates for assignment, step/tool call, stop, gate/review and completion reach the open
 *   screens without a reload, through events.stream and the API's re-read.
 * ac2/completion-receipt: a unit is shown landed only once its landing's completion receipt is in the proof read.
 * ac2/message-intake, ac2/decision-settlement, ac2/refusals: a message reaches the common intake; an inline
 *   answer settles once; a stale presentation and an unauthorized save are refused beside their action.
 * ac2/api-only: every request is a published route; nothing reaches storage, the URL or another origin.
 * ac3/keyboard-desktop and ac3/touch-phone: the owner's task path by keyboard only (1280 px) and by touch (390 px):
 *   backlog reorder, detail and sheet focus restoration, message, workflow step settings, add, connect, reorder
 *   and save, with 44 px touch targets and announced results.
 */

const WIDTHS = [
  { width: 360, height: 760 },
  { width: 390, height: 844 },
  { width: 1280, height: 860 },
  { width: 1440, height: 900 },
]
const SCREENS_DIR = process.env.VELDO_0131_SCREENS
const isPhone = (page: Page) => (page.viewportSize()?.width ?? 1280) < 768

type Opened = { primary: string | null; axe?: boolean }
interface Render {
  name: string
  who?: string
  open(page: Page, factory: FactoryUi): Promise<Opened>
}

/** Hold every factory data request until released, so the loading state is on screen; nothing is mocked. */
async function holdData(page: Page) {
  const held: Route[] = []
  await page.route(/\/api\/v1\/domains\//, (route) => void held.push(route))
  return async () => {
    await page.unroute(/\/api\/v1\/domains\//)
    for (const route of held) await route.continue().catch(() => undefined)
  }
}

/** Drop the screen's data connection, as a network does: the screen must show the named refusal. */
async function dropData(page: Page) {
  await page.route(/\/api\/v1\/domains\/[^/]+\/(?!events)/, (route) => route.abort('connectionreset'))
  return () => page.unroute(/\/api\/v1\/domains\/[^/]+\/(?!events)/)
}

const tree = (page: Page) => (isPhone(page) ? '.tree-cards' : '.tree-grid')

const SCREENS: { name: string; path: string; ready: string; primary: (page: Page) => string; empty?: string }[] = [
  { name: 'projects', path: '/projects', ready: '[data-testid="projects"], [data-testid="project-detail"]', primary: (p) => (isPhone(p) ? '[data-testid="message-open"]' : '[data-testid="message-send"]'), empty: 'cmember' },
  { name: 'backlog', path: '/backlog', ready: '[data-testid="backlog"]', primary: (p) => `${tree(p)} [data-row="backlog:131-encoding"] [data-testid="move-up"]`, empty: 'cmember' },
  { name: 'workers', path: '/workers', ready: '[data-testid="workers"]', primary: () => '[data-dispatch*="VELDO-9146"] [data-testid="worker-stop"]', empty: 'cmember' },
  { name: 'proof', path: '/proof', ready: '[data-testid="proof"]', primary: () => '[data-testid="pane-changes"]', empty: 'cmember' },
  { name: 'usage', path: '/usage', ready: '[data-testid="usage"]', primary: () => '[data-testid="usage-bucket"]', empty: 'cmember' },
  { name: 'configuration', path: '/configuration', ready: '[data-testid="roles-table"]', primary: () => '[data-testid="role-edit"]' },
  { name: 'catalog', path: '/catalog', ready: '[data-testid="catalog"]', primary: () => '[data-testid="server-edit"]' },
  { name: 'workflows', path: '/workflows/delivery', ready: '[data-testid="workflow-editor"]', primary: () => '[data-testid="add-grooming"]' },
]

function renders(): Render[] {
  const out: Render[] = []
  for (const s of SCREENS) {
    out.push({
      name: `${s.name}-loading`,
      async open(page, factory) {
        const release = await holdData(page)
        await page.goto(factory.origin + s.path)
        await expect(page.locator('[data-state="loading"]').first()).toBeVisible()
        ;(page as unknown as { release?: () => Promise<void> }).release = release
        return { primary: null, axe: false }
      },
    })
    out.push({
      name: `${s.name}-error`,
      async open(page, factory) {
        const undo = await dropData(page)
        await page.goto(factory.origin + s.path)
        await expect(page.getByTestId('refusal').first()).toBeVisible()
        ;(page as unknown as { release?: () => Promise<void> }).release = undo
        return { primary: null }
      },
    })
    if (s.empty)
      out.push({
        name: `${s.name}-empty`,
        who: s.empty,
        async open(page, factory) {
          await page.goto(factory.origin + s.path)
          await expect(page.locator('[data-state="empty"]').first()).toBeVisible()
          return { primary: null }
        },
      })
    out.push({
      name: s.name,
      async open(page, factory) {
        await page.goto(factory.origin + s.path)
        await expect(page.locator(s.ready).first()).toBeVisible()
        await expect(page.getByTestId('live-meta').first()).toHaveAttribute('data-live', /live|idle/)
        return { primary: s.primary(page) }
      },
    })
  }
  out.push(
    {
      name: 'project-detail',
      async open(page, factory) {
        await page.goto(factory.origin + '/projects/project-a')
        await expect(page.getByTestId('project-detail')).toBeVisible()
        return { primary: isPhone(page) ? '[data-testid="message-open"]' : '[data-testid="message-send"]' }
      },
    },
    {
      name: 'chat-sheet',
      async open(page, factory) {
        await page.goto(factory.origin + '/projects/project-a')
        if (!isPhone(page)) return { primary: '[data-testid="message-send"]' }
        await page.getByTestId('message-open').click()
        await expect(page.getByTestId('chat-sheet')).toBeVisible()
        return { primary: '[data-testid="message-send"]' }
      },
    },
    {
      name: 'backlog-detail',
      async open(page, factory) {
        await page.goto(factory.origin + '/backlog')
        await page.locator(`${tree(page)} [data-row="backlog:131-report"] [data-testid="backlog-details"]`).click()
        await expect(page.getByTestId(isPhone(page) ? 'backlog-sheet' : 'backlog-detail')).toBeVisible()
        return { primary: isPhone(page) ? '[data-testid="backlog-sheet"] button' : `${tree(page)} [data-row="backlog:131-report"] [data-testid="move-up"]` }
      },
    },
    {
      name: 'workers-confirm',
      async open(page, factory) {
        await page.goto(factory.origin + '/workers')
        await page.locator('[data-dispatch*="VELDO-9146"] [data-testid="worker-stop"]').click()
        return { primary: '[data-testid="worker-stop-confirm"]' }
      },
    },
    {
      name: 'workflow-step',
      async open(page, factory) {
        await page.goto(factory.origin + '/workflows/delivery')
        await page.locator('[data-step="wait"] [data-testid="step-select"]').click()
        await expect(page.getByTestId('node-settings')).toBeVisible()
        return { primary: '[data-testid="node-port-admit"]' }
      },
    },
    {
      name: 'run-live',
      async open(page, factory) {
        const ids = await factory.state()
        await page.goto(factory.origin + '/runs/' + ids.dispatches.live)
        await expect(page.getByTestId('terminal')).toBeVisible()
        return { primary: null }
      },
    },
    {
      name: 'decision-inline',
      async open(page, factory) {
        const ids = await factory.state()
        await page.goto(factory.origin + '/decisions/' + ids.requests.de3)
        await expect(page.getByTestId('decision')).toBeVisible()
        return { primary: '[data-testid="send-answer"]' }
      },
    },
  )
  return out
}

interface Problems {
  overflow: number
  overlaps: string[]
  primary: string | null
}

/** The page as rendered: page-wide overflow, overlapping controls and the primary action (VELDO-0145's measure,
 * with the factory screens' internal scrollers allowed: a table wrapper and the canvas scroll inside). */
async function measure(page: Page, primary: string | null, phone: boolean): Promise<Problems> {
  if (primary) await page.locator(primary).first().scrollIntoViewIfNeeded().catch(() => undefined)
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
      const controls = Array.from(document.querySelectorAll('button, a[href], input:not([type=hidden]), textarea, select, [role="radio"]'))
        .filter(visible)
        .filter((el) => !el.closest('.monaco-editor, .vradio, .vswitch, .flow-canvas svg') || el.matches('.vradio-input, .vswitch-input'))
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
      return { overflow, overlaps, primary: problem }
    },
    { primary, phone },
  )
}

async function pageAs(browser: Browser, factory: FactoryUi, who: string, viewport: { width: number; height: number }) {
  const phone = viewport.width < 768
  const context = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone })
  const page = await context.newPage()
  await signIn(page, factory, who)
  return page
}

for (const viewport of WIDTHS) {
  const phone = viewport.width < 768
  test(`ac1/screens-${viewport.width}: every screen row and state at ${viewport.width}px`, async ({ browser, factory }) => {
    test.setTimeout(600_000)
    const failures: string[] = []
    const pages = new Map<string, Page>()
    for (const render of renders()) {
      const who = render.who ?? 'owner'
      if (!pages.has(who)) pages.set(who, await pageAs(browser, factory, who, viewport))
      const page = pages.get(who)!
      const watch = await guard(page)
      let opened: Opened
      try {
        opened = await render.open(page, factory)
      } catch (error) {
        failures.push(`${render.name}: did not open (${String(error).split('\n')[0]})`)
        continue
      }
      const problems = await measure(page, opened.primary, phone)
      if (problems.overflow > 1) failures.push(`${render.name}: page-wide overflow ${problems.overflow}px`)
      if (problems.overlaps.length) failures.push(`${render.name}: overlapping ${problems.overlaps.slice(0, 3).join('; ')}`)
      if (problems.primary) failures.push(`${render.name}: primary action ${opened.primary} ${problems.primary}`)
      if (opened.axe !== false && (viewport.width === 390 || viewport.width === 1280)) {
        const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).exclude('.monaco-editor').analyze()
        for (const v of result.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical'))
          failures.push(`${render.name}: axe ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target}`)
      }
      const violations = await watch.violations()
      if (violations.length) failures.push(`${render.name}: content security policy ${violations[0]}`)
      if (SCREENS_DIR && !render.name.endsWith('-loading')) {
        mkdirSync(SCREENS_DIR, { recursive: true })
        await page.screenshot({ path: path.join(SCREENS_DIR, `${viewport.width}-${render.name}.png`), fullPage: true })
      }
      const release = (page as unknown as { release?: () => Promise<void> }).release
      if (release) {
        await release()
        ;(page as unknown as { release?: unknown }).release = undefined
      }
    }
    for (const page of pages.values()) await page.context().close()
    expect(failures, failures.join('\n')).toEqual([])
  })
}

test('ac2/live: assignment, step and tool call, stop, gate and review, and completion reach the open screens', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.goto(factory.origin + '/workers')
  await expect(page.getByTestId('workers')).toBeVisible()
  const meta = page.getByTestId('live-meta')
  await expect(meta).toHaveAttribute('data-live', 'live')
  const seq0 = Number(await meta.getAttribute('data-seq'))
  // Assignment: a unit dispatched to a worker appears on its machine, without a reload.
  const { key, dispatch } = await factory.control<{ key: string; dispatch: string }>('/dispatch/new', { unit: 'VELDO-9171', key: 'live131', count: 3 })
  await factory.deliver()
  const card = page.locator(`[data-dispatch="${dispatch}"]`)
  await expect(card).toHaveAttribute('data-state', 'running')
  expect(Number(await meta.getAttribute('data-seq'))).toBeGreaterThan(seq0)
  // Stop: the worker's run ends; its card shows the recorded state.
  await factory.control('/record/end', { key })
  await factory.deliver()
  await expect(card).toHaveAttribute('data-state', 'exited')
  // Step and tool call: a new line of the record reaches the live terminal.
  const ids = await factory.state()
  await page.goto(factory.origin + '/runs/' + ids.dispatches.live)
  await expect(page.getByTestId('terminal')).toBeVisible()
  await factory.control('/record/append', { key: 'live', start: 131, count: 1 })
  await expect(page.getByTestId('terminal').getByText('echo step 131').first()).toBeVisible()
  // Gate and review: a new gate observation reaches the gate and review screen.
  await page.goto(factory.origin + '/proof')
  await expect(page.getByTestId('gate-output')).toBeVisible()
  const options = page.getByTestId('gate-new').locator('option')
  const before = await options.count()
  const red = 'suite 120: ac1/screens-360 red\nGATE: RED (7a7a7a7)\n'
  await factory.upsert('gate-observation:131-live', 'gate_observation', {
    schema: 'veldo.gate_observation/v1', command: ['bash', 'scripts/verify.sh'], commit: '7a7a7a7'.repeat(5) + 'ab', exit: 1, stdout: red,
    stderr: '', terminal: 'GATE: RED (7a7a7a7)', green: false, started_at: Date.now() / 1000 - 60, finished_at: Date.now() / 1000, capture: 'e2e',
    domain: 'e2e-domain', repository: 'e2e-repository',
  })
  await expect(options).toHaveCount(before + 1)
  await expect(page.locator('[data-finding="gate-observation:131-live"]')).toBeVisible()
  // Completion: the landing's receipt turns the unit landed on the backlog, live.
  await page.goto(factory.origin + '/backlog')
  await page.locator('.tree-grid [data-row="backlog:131-parser"] [data-testid="backlog-details"]').click()
  const unit = page.locator('[data-testid="backlog-detail"] [data-unit="unit-131-tests"]')
  await expect(unit).toHaveAttribute('data-completion', 'not-complete')
  await factory.upsert('unit-131-tests', 'execution_unit', { ...(await factory.entity('unit-131-tests'))!.data, state: 'COMPLETED' })
  await expect(unit).toHaveAttribute('data-completion', 'built-unconfirmed')
  await factory.land('unit-131-tests')
  await expect(unit).toHaveAttribute('data-completion', 'landed')
  await page.context().close()
})

test('ac2/completion-receipt: a unit built but not landed is never shown complete', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.goto(factory.origin + '/backlog')
  await page.locator('.tree-grid [data-row="backlog:131-parser"] [data-testid="backlog-details"]').click()
  const built = page.locator('[data-testid="backlog-detail"] [data-unit="unit-131-built"]')
  const landed = page.locator('[data-testid="backlog-detail"] [data-unit="unit-131-parse"]')
  expect((await factory.entity('unit-131-built'))!.data.state).toBe('COMPLETED')
  expect((await factory.kind('completion_receipt')).some((r) => r.data.subject?.id === 'unit-131-built')).toBe(false)
  await expect(built).toHaveAttribute('data-completion', 'built-unconfirmed')
  await expect(built).toContainText('Built, landing not confirmed')
  await expect(built).not.toContainText('Landed')
  await expect(landed).toHaveAttribute('data-completion', 'landed')
  await page.goto(factory.origin + '/proof')
  await expect(page.locator('[data-bundle="proof-bundle:131-parse"] .factory-tag').first()).toHaveText('Landed')
  await page.context().close()
})

test('ac2/message-intake: a message from the projects screen reaches the common intake', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  const watch = await guard(page)
  await page.goto(factory.origin + '/projects/project-a')
  const text = `Export the import report as CSV ${Date.now()}`
  await page.getByTestId('message-text').first().fill(text)
  await page.getByTestId('message-send').first().click()
  await expect(page.getByTestId('message-answer')).toBeVisible()
  const sent = watch.requests.filter((r) => routeOf(r.method, r.url, factory.domain) === 'messages.send')
  expect(sent).toHaveLength(1)
  const proposals = await factory.kind('intake_proposal')
  expect(proposals.some((p) => p.data.text === text)).toBe(true)
  await expect(page.getByTestId('chat-log').getByText(text)).toBeVisible()
  await page.context().close()
})

test('ac2/decision-settlement: an inline answer settles once; a stale presentation is refused beside the action', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 390, height: 844 })
  const ids = await factory.state()
  await page.goto(factory.origin + '/decisions/' + ids.requests.de1)
  await page.locator('[data-choice="accept"]').click()
  await page.getByTestId('rationale').fill('Admit it; the index is needed.')
  await page.getByTestId('send-answer').click()
  await expect(page.getByTestId('send-answer')).toHaveCount(0)
  const settled = await factory.control<{ settlements: unknown[] }>('/request/settlements', { alias: 'de1' })
  expect(settled.settlements).toHaveLength(1)
  await page.goto(factory.origin + '/decisions/' + ids.requests.de4)
  await page.locator('[data-choice="reject"]').click()
  await page.getByTestId('rationale').fill('Not now.')
  await factory.control('/request/revise', { alias: 'de4' })
  await page.getByTestId('send-answer').click()
  await expect(page.locator('[data-refusal^="stale_version"]')).toBeVisible()
  const none = await factory.control<{ settlements: unknown[] }>('/request/settlements', { alias: 'de4' })
  expect(none.settlements).toHaveLength(0)
  await page.context().close()
})

test('ac2/refusals: an answer from a member outside the project\'s scope is refused beside the action; a workflow outside the scope shows none', async ({ browser, factory }) => {
  const alias = `rf${Date.now() % 100000}`
  const { request } = await factory.control<{ request: string }>('/request/open', { alias, owner: 'mover' })
  const page = await pageAs(browser, factory, 'mover', { width: 390, height: 844 })
  await page.goto(factory.origin + '/decisions/' + request)
  await expect(page.getByTestId('decision')).toBeVisible()
  await factory.control('/member/scope', { principal: 'mover', scope: ['project-b'] })
  await page.locator('[data-choice="accept"]').click()
  await page.getByTestId('rationale').fill('Answering after my scope moved.')
  await page.getByTestId('send-answer').click()
  await expect(page.getByTestId('answer-bar').getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthorized:out_of_scope')
  expect((await factory.control<{ settlements: unknown[] }>('/request/settlements', { alias })).settlements).toHaveLength(0)
  await page.context().close()
  const outside = await pageAs(browser, factory, 'bmember', { width: 1280, height: 860 })
  const before = (await factory.workflow()).version
  await outside.goto(factory.origin + '/workflows/delivery')
  await expect(outside.locator('[data-state="empty"]')).toBeVisible()
  await expect(outside.getByTestId('flow-save')).toHaveCount(0)
  expect((await factory.workflow()).version).toBe(before)
  await outside.context().close()
})

test('ac2/api-only: every request is a published route of this origin and nothing is kept in storage or the URL', async ({ browser, factory }) => {
  test.setTimeout(120_000)
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  const watch = await guard(page)
  for (const s of SCREENS) {
    await page.goto(factory.origin + s.path)
    await expect(page.locator(s.ready).first()).toBeVisible()
  }
  const outside = watch.requests.filter((r) => new URL(r.url).origin !== factory.origin)
  const unrouted = watch.requests.filter((r) => new URL(r.url).pathname.startsWith('/api/') && !routeOf(r.method, r.url, factory.domain))
  expect(outside.map((r) => r.url)).toEqual([])
  expect(unrouted.map((r) => `${r.method} ${r.url}`)).toEqual([])
  const kept = await page.evaluate(() => [JSON.stringify(localStorage), JSON.stringify(sessionStorage), location.href])
  expect(kept.join(' ')).not.toMatch(/token|csrf|credential_value|secret/i)
  expect(await watch.violations()).toEqual([])
  await page.context().close()
})

test('ac3/keyboard-desktop: the owner\'s task path by keyboard only', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  // Backlog: reorder from the keyboard (Enter on Move up, Alt+Down on a row's button), announced.
  await page.goto(factory.origin + '/backlog')
  const order = () => page.locator('.tree-grid tbody tr[data-depth="0"]').evaluateAll((rows) => rows.map((r) => r.getAttribute('data-row')))
  await expect(page.locator('.tree-grid tbody tr[data-depth="0"]')).toHaveCount(4)
  const first = await order()
  await page.locator('.tree-grid [data-row="backlog:131-report"] [data-testid="move-up"]').focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('backlog-announce')).toContainText('is now number')
  const moved = await order()
  expect(moved.indexOf('backlog:131-report')).toBe(first.indexOf('backlog:131-report') - 1)
  await page.locator('.tree-grid [data-row="backlog:131-report"] [data-testid="move-down"]').focus()
  await page.keyboard.press('Alt+ArrowDown')
  expect((await order()).indexOf('backlog:131-report')).toBe(first.indexOf('backlog:131-report'))
  await expect(page.getByTestId('priority-save')).toBeDisabled()
  // Nested units: expand a row from the keyboard.
  await page.locator('.tree-grid button[aria-label="Expand Empty lines parse to an empty list"]').focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('.tree-grid tr[data-row="unit-131-parse"]')).toBeVisible()
  // Workflow: select a step from the ordered list, reach its settings by Tab, connect a port, add a step, save.
  await page.goto(factory.origin + '/workflows/delivery')
  const version = (await factory.workflow()).version as number
  await page.locator('[data-step="wait"] [data-testid="step-select"]').focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('node-settings')).toBeVisible()
  let reached = false
  for (let i = 0; i < 40 && !reached; i += 1) {
    await page.keyboard.press('Tab')
    reached = await page.evaluate(() => document.activeElement?.getAttribute('data-testid') === 'node-port-admit')
  }
  expect(reached, 'the step setting is reachable by Tab').toBe(true)
  await page.getByTestId('node-port-admit').selectOption('groom')
  await expect(page.getByTestId('flow-state')).toHaveAttribute('data-state', 'edited')
  await page.getByTestId('add-result_handling').focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('flow-announce')).toContainText('Added result_handling_1')
  await page.locator('[data-step="wait"] [data-testid="step-select"]').focus()
  await page.keyboard.press('Enter')
  await page.getByTestId('node-port-admit').selectOption('result_handling_1')
  // The canvas: a focused step moves with the arrow keys.
  const node = page.locator('.flow-node[data-node="groom"]')
  const from = await node.getAttribute('transform')
  await node.focus()
  await page.keyboard.press('ArrowDown')
  await expect(node).not.toHaveAttribute('transform', from ?? '')
  await page.getByTestId('flow-save').focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('flow-state')).toContainText(`Saved as version ${version + 1}`)
  const stored = await factory.workflow()
  expect(stored.version).toBe(version + 1)
  expect(Object.keys(stored.definition.nodes)).toContain('result_handling_1')
  await page.context().close()
})

test('ac3/touch-phone: the owner\'s task path by touch on a phone', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  const page = await pageAs(browser, factory, 'owner', { width: 390, height: 844 })
  const big = async (selector: string) => {
    const box = await page.locator(selector).first().boundingBox()
    expect(box && box.width >= 44 && box.height >= 44, `${selector} is a 44 px target (${JSON.stringify(box)})`).toBe(true)
  }
  // Backlog: reorder by touch buttons, open the detail sheet, close it and get focus back.
  await page.goto(factory.origin + '/backlog')
  const up = '.tree-cards [data-row="backlog:131-report"] [data-testid="move-up"]'
  await big(up)
  await page.locator(up).tap()
  await expect(page.getByTestId('backlog-announce')).toContainText('is now number')
  const details = '.tree-cards [data-row="backlog:131-report"] [data-testid="backlog-details"]'
  await big(details)
  await page.locator(details).tap()
  await expect(page.getByTestId('backlog-sheet')).toBeVisible()
  await expect(page.getByTestId('backlog-sheet').getByTestId('blocker')).toBeVisible()
  await page.getByTestId('backlog-sheet').getByRole('button', { name: 'Close' }).tap()
  await expect(page.getByTestId('backlog-sheet')).toHaveCount(0)
  expect(await page.evaluate(() => document.activeElement?.getAttribute('data-testid'))).toBe('backlog-details')
  // Message: the persistent message action opens the chat sheet.
  await page.goto(factory.origin + '/projects/project-a')
  await big('[data-testid="message-open"]')
  await page.getByTestId('message-open').tap()
  await expect(page.getByTestId('chat-sheet')).toBeVisible()
  await page.getByTestId('chat-sheet').getByRole('button', { name: 'Close' }).tap()
  // Workflow: tap a step, its settings are in the sheet; connect, add, reorder and save by touch.
  await page.goto(factory.origin + '/workflows/delivery')
  const version = (await factory.workflow()).version as number
  await page.locator('[data-step="wait"] [data-testid="step-select"]').tap()
  const sheet = page.getByTestId('flow-sheet')
  await expect(sheet).toBeVisible()
  await expect(sheet.getByTestId('node-settings')).toBeVisible()
  await big('[data-testid="flow-sheet"] [data-testid="node-port-decline"]')
  await sheet.getByRole('button', { name: 'Close' }).tap()
  await page.getByTestId('add-grooming').tap()
  await expect(page.getByTestId('flow-sheet')).toBeVisible()
  await page.getByTestId('flow-sheet').getByTestId('node-port-groomed').selectOption('finish')
  await page.getByTestId('flow-sheet').getByRole('button', { name: 'Close' }).tap()
  await page.locator('[data-step="wait"] [data-testid="step-select"]').tap()
  await page.getByTestId('flow-sheet').getByTestId('node-port-decline').selectOption('grooming_1')
  await page.getByTestId('flow-sheet').getByRole('button', { name: 'Close' }).tap()
  await page.locator('[data-step="grooming_1"] button[aria-label="Move grooming_1 up"]').tap()
  await big('[data-testid="flow-save"]')
  await page.getByTestId('flow-save').tap()
  await expect(page.getByTestId('flow-state')).toContainText(`Saved as version ${version + 1}`)
  const stored = await factory.workflow()
  expect(stored.version).toBe(version + 1)
  expect(stored.definition.transitions.some((t: { from: string; port: string; to: string }) => t.from === 'wait' && t.port === 'decline' && t.to === 'grooming_1')).toBe(true)
  await page.context().close()
})

test('ac3/stale-save: a workflow save from an older version is refused beside Save and the current version loads', async ({ browser, factory }) => {
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.goto(factory.origin + '/workflows/delivery')
  await expect(page.getByTestId('workflow-editor')).toBeVisible()
  const stored = await factory.workflow()
  // Another save lands first, through the same API, from a second session.
  const other = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await other.goto(factory.origin + '/workflows/delivery')
  await other.getByTestId('workflow-editor').waitFor()
  await other.locator('.flow-node[data-node="groom"]').focus()
  await other.keyboard.press('ArrowDown')
  await other.getByTestId('flow-save').click()
  await expect(other.getByTestId('flow-state')).toContainText(`Saved as version ${stored.version + 1}`)
  await page.locator('.flow-node[data-node="groom"]').focus()
  await page.keyboard.press('ArrowRight')
  await page.getByTestId('flow-save').click()
  await expect(page.locator('[data-refusal^="stale_version"]')).toBeVisible()
  expect((await factory.workflow()).version).toBe(stored.version + 1)
  await page.getByTestId('flow-reload').click()
  await expect(page.getByTestId('flow-state')).toHaveAttribute('data-state', 'saved')
  await other.context().close()
  await page.context().close()
})
