import AxeBuilder from '@axe-core/playwright'
import type { Page, Route } from '@playwright/test'
import { expect, guard, isPhone, newConversation, pageAs, send, test, type ConversationFactory } from './conversation-fixtures'

/**
 * VELDO-0179 AC3: the conversation screens under VELDO-0131's phone, desktop and accessibility rules, as VELDO-0145
 * AC4 applies them. Each test's title begins with its row name; scripts/suites/135_veldo_0179_conversation_layout.py
 * reads the rows from the JSON report.
 *
 * ac3/screens-<width>: the list and the conversation screen at 360, 390, 1280 and 1440 px in their loading, empty,
 *   waiting, running, error and populated states (and a turn's terminal): no page-wide overflow, no overlapping
 *   controls, the primary action visible, unclipped, uncovered and a 44 px target on a phone, the message box's Send
 *   reachable above the phone keyboard, axe (wcag2a and wcag2aa, contrast included) on the real accessibility tree at
 *   390 and 1280, and no content security policy violation.
 * ac3/keyboard-desktop: the owner's path by keyboard only at 1280 px: New conversation, write and send, change the
 *   role, attach a project and close, each control reached with Tab and showing a visible focus.
 * ac3/touch-phone: the same path by touch at 390 px with 44 px primary targets, the running turn's terminal one tap
 *   away, and every control found by its name in the accessibility tree.
 */

const WIDTHS = [
  { width: 360, height: 760 },
  { width: 390, height: 844 },
  { width: 1280, height: 860 },
  { width: 1440, height: 900 },
]

interface Fixture {
  populated: string
  empty: string
  waiting: string
  running: string
}

/** The conversations the renders show, made through the screens themselves: one with two answered turns, one with no
 * turn, one whose turn is running (held after its error line) and one whose turn is waiting (no turn starts). */
async function prepare(page: Page, factory: ConversationFactory): Promise<Fixture> {
  await factory.pause(false)
  await factory.pace(0.05)
  const populated = await newConversation(page, factory)
  await factory.replies(['The importer reads the file twice; the second read is the slow one.', 'Yes: stream it once and keep the index.'])
  await send(page, 'Why is the importer slow on large files?')
  await expect(page.getByTestId('turn-1').getByTestId('turn-reply')).toBeVisible({ timeout: 30_000 })
  await send(page, 'Can it read the file once?')
  await expect(page.getByTestId('turn-2').getByTestId('turn-reply')).toBeVisible({ timeout: 30_000 })
  const running = await newConversation(page, factory)
  await factory.hold(running, true)
  await send(page, 'Run the deploy step and watch it.')
  await expect(page.getByTestId('turn-1').getByTestId('turn-marker')).toHaveAttribute('data-marker', 'running', { timeout: 30_000 })
  await factory.pause(true)
  const waiting = await newConversation(page, factory)
  await send(page, 'Queue this behind the others.')
  await expect(page.getByTestId('turn-1').getByTestId('turn-marker')).toHaveAttribute('data-marker', 'waiting')
  const empty = await newConversation(page, factory)
  return { populated, empty, waiting, running }
}

type Opened = { primary: string | null; axe?: boolean; keyboard?: boolean }
interface Render {
  name: string
  who?: string
  open(page: Page, factory: ConversationFactory, f: Fixture): Promise<Opened>
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

const at = (factory: ConversationFactory, id: string) => `${factory.origin}/conversations/${encodeURIComponent(id)}`

const RENDERS: Render[] = [
  {
    name: 'list-loading',
    async open(page, factory) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/conversations')
      await expect(page.locator('[data-state="loading"]').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = release
      return { primary: '[data-testid="conversation-new"]', axe: false }
    },
  },
  {
    name: 'list-error',
    async open(page, factory) {
      const undo = await dropData(page)
      await page.goto(factory.origin + '/conversations')
      await expect(page.locator('[data-state="error"]').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = undo
      return { primary: '[data-testid="conversation-new"]' }
    },
  },
  {
    name: 'list-empty',
    who: 'owner2',
    async open(page, factory) {
      await page.goto(factory.origin + '/conversations')
      await expect(page.locator('[data-state="empty"]').first()).toBeVisible()
      return { primary: '[data-testid="conversation-new"]' }
    },
  },
  {
    name: 'list',
    async open(page, factory) {
      await page.goto(factory.origin + '/conversations')
      await expect(page.getByTestId('conversations')).toBeVisible()
      return { primary: '[data-testid="conversation-new"]' }
    },
  },
  {
    name: 'conversation-loading',
    async open(page, factory, f) {
      const release = await holdData(page)
      await page.goto(at(factory, f.populated))
      await expect(page.locator('[data-state="loading"]').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = release
      return { primary: null, axe: false }
    },
  },
  {
    name: 'conversation-error',
    async open(page, factory, f) {
      const undo = await dropData(page)
      await page.goto(at(factory, f.populated))
      await expect(page.locator('[data-state="error"]').first()).toBeVisible()
      ;(page as unknown as { release?: () => Promise<void> }).release = undo
      return { primary: null }
    },
  },
  {
    name: 'conversation-empty',
    async open(page, factory, f) {
      await page.goto(at(factory, f.empty))
      await expect(page.getByTestId('turns-empty')).toBeVisible()
      return { primary: '[data-testid="message-send"]', keyboard: true }
    },
  },
  {
    name: 'conversation-waiting',
    async open(page, factory, f) {
      await page.goto(at(factory, f.waiting))
      await expect(page.locator('[data-marker="waiting"]')).toBeVisible()
      return { primary: '[data-testid="message-send"]', keyboard: true }
    },
  },
  {
    name: 'conversation-running',
    async open(page, factory, f) {
      await page.goto(at(factory, f.running))
      await expect(page.locator('[data-marker="running"]')).toBeVisible()
      return { primary: '[data-testid="turn-watch"]' }
    },
  },
  {
    name: 'conversation',
    async open(page, factory, f) {
      await page.goto(at(factory, f.populated))
      await expect(page.getByTestId('turn-2').getByTestId('turn-reply')).toBeVisible()
      return { primary: '[data-testid="message-send"]', keyboard: true }
    },
  },
  {
    name: 'turn-running',
    async open(page, factory, f) {
      await page.goto(`${at(factory, f.running)}/turns/1`)
      await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'live')
      return { primary: null }
    },
  },
  {
    name: 'turn-ended',
    async open(page, factory, f) {
      await page.goto(`${at(factory, f.populated)}/turns/1`)
      await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
      return { primary: null }
    },
  },
]

interface Problems {
  overflow: number
  overlaps: string[]
  primary: string | null
}

/** VELDO-0131's measure (factory.spec.ts): page-wide overflow, overlapping controls and the primary action judged where
 * the owner scrolls to it. */
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
      const controls = Array.from(document.querySelectorAll('button, a[href], input:not([type=hidden]), textarea, select, [role="radio"]'))
        .filter(visible)
        .filter((el) => !el.closest('.vswitch') || el.matches('.vswitch-input'))
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

/** The phone keyboard: with the message box focused, the visible height shrinks by a keyboard's height (the page
 * declares interactive-widget=resizes-content, so the layout viewport is what is left above the keyboard); Send must
 * still be on screen, unclipped and uncovered, without scrolling the page. */
async function keyboardProblem(page: Page): Promise<string | null> {
  const size = page.viewportSize()!
  await page.getByTestId('message-text').focus()
  await page.setViewportSize({ width: size.width, height: Math.round(size.height * 0.55) })
  await page.waitForTimeout(150)
  const problem = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="message-send"]')
    const box = document.querySelector('[data-testid="message-text"]')
    if (!el || !box) return 'no message box'
    const vh = window.innerHeight
    const r = el.getBoundingClientRect()
    const t = box.getBoundingClientRect()
    if (r.top < 0 || r.bottom > vh || t.bottom > vh) return `send at ${Math.round(r.top)}..${Math.round(r.bottom)} of ${vh}`
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
    if (!hit || !(el === hit || el.contains(hit))) return `send covered by ${hit?.className ?? 'nothing'}`
    if (r.height < 44 || r.width < 44) return `send ${Math.round(r.width)}x${Math.round(r.height)}`
    return null
  })
  await page.setViewportSize(size)
  return problem
}

for (const viewport of WIDTHS) {
  const phone = viewport.width < 768
  test(`ac3/screens-${viewport.width}: the list and the conversation screen in every state at ${viewport.width}px`, async ({ browser, factory }) => {
    test.setTimeout(600_000)
    const failures: string[] = []
    const pages = new Map<string, Page>()
    const setup = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
    const fixture = await prepare(setup, factory)
    await setup.context().close()
    try {
      for (const render of RENDERS) {
        const who = render.who ?? 'owner'
        if (!pages.has(who)) pages.set(who, await pageAs(browser, factory, who, viewport))
        const page = pages.get(who)!
        const watch = await guard(page)
        let opened: Opened
        try {
          opened = await render.open(page, factory, fixture)
        } catch (error) {
          failures.push(`${render.name}: did not open (${String(error).split('\n')[0]})`)
          continue
        }
        const problems = await measure(page, opened.primary, phone)
        if (problems.overflow > 1) failures.push(`${render.name}: page-wide overflow ${problems.overflow}px`)
        if (problems.overlaps.length) failures.push(`${render.name}: overlapping ${problems.overlaps.slice(0, 3).join('; ')}`)
        if (problems.primary) failures.push(`${render.name}: primary action ${opened.primary} ${problems.primary}`)
        if (opened.axe !== false && (viewport.width === 390 || viewport.width === 1280)) {
          const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
          for (const v of result.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical'))
            failures.push(`${render.name}: axe ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target}`)
        }
        if (phone && opened.keyboard) {
          const problem = await keyboardProblem(page)
          if (problem) failures.push(`${render.name}: above the keyboard ${problem}`)
        }
        const violations = await watch.violations()
        if (violations.length) failures.push(`${render.name}: content security policy ${violations[0]}`)
        const release = (page as unknown as { release?: () => Promise<void> }).release
        if (release) {
          await release()
          ;(page as unknown as { release?: unknown }).release = undefined
        }
      }
    } finally {
      for (const page of pages.values()) await page.context().close()
      await factory.pause(false)
      await factory.hold(fixture.running, false)
    }
    expect(failures, failures.join('\n')).toEqual([])
  })
}

async function tabTo(page: Page, testid: string, limit = 60) {
  for (let n = 0; n < limit; n += 1) {
    await page.keyboard.press('Tab')
    const at = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      return el?.closest('[data-testid]')?.getAttribute('data-testid') ?? el?.getAttribute('data-testid') ?? null
    })
    if (at === testid) {
      const outline = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement
        const s = getComputedStyle(el)
        return s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 ? 'outline' : s.boxShadow !== 'none' ? 'shadow' : 'none'
      })
      expect(outline, `${testid} shows a visible focus`).not.toBe('none')
      return
    }
  }
  throw new Error(`Tab never reached ${testid}`)
}

test('ac3/keyboard-desktop: the owner\'s conversation path by keyboard only', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  await factory.pause(false)
  await factory.pace(0.05)
  const page = await pageAs(browser, factory, 'owner', { width: 1280, height: 860 })
  await page.goto(factory.origin + '/conversations')
  await expect(page.getByTestId('conversations-screen')).toBeVisible()
  await tabTo(page, 'conversation-new')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('conversation-screen')).toBeVisible()
  await expect(page.getByTestId('turns-empty')).toBeVisible()
  await factory.replies(['Keyboard reply: done.'])
  await tabTo(page, 'message-text')
  await page.keyboard.type('Written by keyboard only.')
  await tabTo(page, 'message-send')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('turn-1').getByTestId('turn-reply')).toHaveText('Keyboard reply: done.', { timeout: 30_000 })
  await tabTo(page, 'role-select')
  await page.keyboard.press('ArrowDown')
  await expect(page.getByTestId('role-select')).toHaveValue('assistant_codex')
  await tabTo(page, 'role-change')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('conversation-current-role')).toHaveText('Role assistant_codex')
  await page.getByTestId('project-select').focus()
  await page.keyboard.press('End')
  const project = await page.getByTestId('project-select').inputValue()
  await tabTo(page, 'project-attach')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('conversation-project')).toHaveText(`Project ${project}`)
  await tabTo(page, 'conversation-close')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('conversation-state')).toHaveText('Closed')
  await page.context().close()
})

test('ac3/touch-phone: the owner\'s conversation path by touch on a phone, 44 px targets and named controls', async ({ browser, factory }) => {
  test.setTimeout(180_000)
  await factory.pause(false)
  await factory.pace(0.2)
  const page = await pageAs(browser, factory, 'owner', { width: 390, height: 844 })
  expect(isPhone(page)).toBe(true)
  const big = async (selector: string) => {
    const box = await page.locator(selector).first().boundingBox()
    expect(box && box.width >= 44 && box.height >= 44, `${selector} is a 44 px target (${JSON.stringify(box)})`).toBe(true)
  }
  // From the You screen, as the phone's bottom bar has no room for it.
  await page.goto(factory.origin + '/you')
  await big('[data-testid="you-conversations"]')
  await page.getByTestId('you-conversations').tap()
  await expect(page.getByTestId('conversations-screen')).toBeVisible()
  await big('[data-testid="conversation-new"]')
  await page.getByRole('button', { name: 'New conversation' }).tap()
  await expect(page.getByTestId('conversation-screen')).toBeVisible()
  const id = new URL(page.url()).pathname.split('/').pop()!
  await factory.hold(decodeURIComponent(id), true)
  await page.getByRole('textbox', { name: 'Message' }).tap()
  await page.getByRole('textbox', { name: 'Message' }).fill('Written on the phone.')
  await big('[data-testid="message-send"]')
  await page.getByRole('button', { name: 'Send' }).tap()
  await expect(page.locator('[data-marker="running"]')).toBeVisible({ timeout: 30_000 })
  await big('[data-testid="turn-watch"]')
  await page.getByRole('link', { name: 'Watch live' }).tap()
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'live')
  await expect(page.getByRole('log', { name: 'Execution record' })).toBeVisible()
  await factory.hold(decodeURIComponent(id), false)
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended', { timeout: 30_000 })
  await page.getByRole('link', { name: 'Conversation' }).tap()
  await expect(page.getByTestId('turn-1').getByTestId('turn-reply')).toBeVisible()
  await page.getByRole('combobox', { name: 'Role' }).selectOption('assistant_codex')
  await big('[data-testid="role-change"]')
  await page.getByRole('button', { name: 'Change role' }).tap()
  await expect(page.getByTestId('conversation-current-role')).toHaveText('Role assistant_codex')
  await page.getByRole('combobox', { name: 'Project' }).selectOption('veldo')
  await big('[data-testid="project-attach"]')
  await page.getByRole('button', { name: 'Attach project' }).tap()
  await expect(page.getByTestId('conversation-project')).toHaveText('Project veldo')
  await big('[data-testid="conversation-close"]')
  await page.getByRole('button', { name: 'Close conversation' }).tap()
  await expect(page.getByTestId('conversation-state')).toHaveText('Closed')
  await page.context().close()
})
