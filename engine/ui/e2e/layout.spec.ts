import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import type { Page, Route } from '@playwright/test'
import { SCREENS, UI, expect, guard, signIn, test, type Factory } from './fixtures'

/**
 * VELDO-0145 AC4: the shell, the enrollment and sign-in screen, the run screen and the decisions screen at
 * 360 and 390 px phone and 1280 and 1440 px desktop widths, in loading, empty, live, stopped or error and
 * populated states, light and dark: no clipped primary action, no overlapping controls, no page-wide
 * horizontal overflow, 44 px primary touch targets on phone, labeled controls, contrast and names from the
 * real accessibility tree (axe), and only this origin's built assets served.
 */

const PHONES = [
  { width: 360, height: 760 },
  { width: 390, height: 844 },
]
const DESKTOPS = [
  { width: 1280, height: 860 },
  { width: 1440, height: 900 },
]
type Theme = 'light' | 'dark'

interface Render {
  name: string
  who?: string | null
  /** Open the screen in this state; return the primary action's selector, if the state has one. */
  open(page: Page, factory: Factory, ids: Ids): Promise<string | null>
  /** Undo what the render changed in the factory, so later screenshots show the curated data only. */
  cleanup?(page: Page, factory: Factory): Promise<void>
}

const isPhone = (page: Page) => (page.viewportSize()?.width ?? 1280) < 768
type Ids = Awaited<ReturnType<Factory['state']>>

/** Hold every factory data request until released, so the loading state can be seen; nothing is mocked. */
async function holdData(page: Page) {
  const held: Route[] = []
  let open = false
  await page.route(/\/api\/v1\/domains\//, (route) => (open ? route.continue() : void held.push(route)))
  return async () => {
    open = true
    for (const route of held) await route.continue().catch(() => undefined)
    await page.unroute(/\/api\/v1\/domains\//)
  }
}

const RENDERS: Render[] = [
  {
    name: 'signin-start',
    who: null,
    async open(page, factory) {
      await page.goto(factory.origin + '/sign-in')
      await expect(page.getByTestId('sign-in')).toBeVisible()
      return '[data-testid="sign-in"]'
    },
  },
  {
    name: 'signin-refused',
    who: null,
    async open(page, factory) {
      await page.goto(factory.origin + '/runs')
      await expect(page.getByTestId('refusal')).toBeVisible()
      return '[data-testid="sign-in"]'
    },
  },
  {
    name: 'signin-enroll',
    who: null,
    async open(page, factory) {
      await page.goto(factory.origin + '/sign-in')
      await page.getByTestId('enroll-start').click()
      return '[data-testid="enroll-create"]'
    },
  },
  {
    name: 'overview-loading',
    async open(page, factory) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/')
      await expect(page.locator('[data-state="loading"]').first()).toBeVisible()
      ;(page as unknown as { release: () => Promise<void> }).release = release
      return null
    },
  },
  {
    name: 'overview-populated',
    async open(page, factory) {
      await page.goto(factory.origin + '/')
      await expect(page.getByTestId('andon')).toBeVisible()
      await expect(page.getByTestId('oldest')).toBeVisible()
      await expect(page.getByTestId('inbox')).toBeVisible()
      return '.oldest-open'
    },
  },
  {
    name: 'overview-empty',
    who: 'cmember',
    async open(page, factory) {
      await page.goto(factory.origin + '/')
      await expect(page.getByTestId('andon')).toBeVisible()
      await expect(page.locator('[data-state="empty"]').first()).toBeVisible()
      return null
    },
  },
  {
    name: 'overview-error',
    who: 'outsider',
    async open(page, factory) {
      await page.goto(factory.origin + '/')
      await expect(page.locator('[data-state="error"]')).toBeVisible()
      return null
    },
  },
  {
    name: 'runs-loading',
    async open(page, factory) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/runs')
      await expect(page.locator('[data-state="loading"]')).toBeVisible()
      ;(page as unknown as { release: () => Promise<void> }).release = release
      return null
    },
  },
  {
    name: 'runs-populated',
    async open(page, factory) {
      await page.goto(factory.origin + '/runs')
      await expect(page.getByTestId('runs')).toBeVisible()
      return '.run-row'
    },
  },
  {
    name: 'runs-empty',
    who: 'cmember',
    async open(page, factory) {
      await page.goto(factory.origin + '/runs')
      await expect(page.locator('[data-state="empty"]')).toBeVisible()
      return null
    },
  },
  {
    name: 'runs-error',
    who: 'outsider',
    async open(page, factory) {
      await page.goto(factory.origin + '/runs')
      await expect(page.locator('[data-state="error"]')).toBeVisible()
      return null
    },
  },
  {
    name: 'run-loading',
    async open(page, factory, ids) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/runs/' + ids.dispatches.done)
      await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'loading')
      ;(page as unknown as { release: () => Promise<void> }).release = release
      return null
    },
  },
  {
    name: 'run-live',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/runs/' + ids.dispatches.live)
      await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'live')
      return isPhone(page) ? '[data-testid="search-open"]' : '[data-testid="search"]'
    },
  },
  {
    name: 'run-ended',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/runs/' + ids.dispatches.done)
      await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
      await page.locator('[data-seq="7"]').scrollIntoViewIfNeeded()
      await expect(page.locator('[data-seq="7"] .monaco-diff-editor')).toBeVisible()
      return isPhone(page) ? '[data-testid="search-open"]' : '[data-testid="search"]'
    },
  },
  {
    name: 'run-empty',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/runs/' + ids.dispatches.quiet)
      await expect(page.getByTestId('terminal-empty')).toBeVisible()
      return null
    },
  },
  {
    name: 'run-error',
    who: 'bmember',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/runs/' + ids.dispatches.done)
      await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthorized:out_of_scope')
      // Nothing is shown, so no record control is either, and a named refusal offers no Try again.
      await expect(page.locator('#follow, [data-testid="search"], [data-testid="try-again"]')).toHaveCount(0)
      return null
    },
  },
  {
    name: 'decisions-loading',
    async open(page, factory) {
      const release = await holdData(page)
      await page.goto(factory.origin + '/decisions')
      await expect(page.locator('[data-state="loading"]')).toBeVisible()
      ;(page as unknown as { release: () => Promise<void> }).release = release
      return null
    },
  },
  {
    name: 'decisions-inbox',
    async open(page, factory) {
      await page.goto(factory.origin + '/decisions')
      await expect(page.getByTestId('inbox')).toBeVisible()
      return '.inbox-row'
    },
  },
  {
    name: 'decision-open',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/decisions/' + ids.requests.de3)
      await expect(page.getByTestId('decision')).toBeVisible()
      return '[data-testid="send-answer"]'
    },
  },
  {
    name: 'decision-picked',
    async open(page, factory, ids) {
      await page.goto(factory.origin + '/decisions/' + ids.requests.de5)
      await expect(page.getByTestId('decision')).toBeVisible()
      await page.locator('[data-choice="return_for_elaboration"]').click()
      await page.getByTestId('rationale').fill('Split the gate change from the policy change first.')
      return '[data-testid="send-answer"]'
    },
  },
  {
    name: 'decision-refused',
    async open(page, factory) {
      const alias = `dl${Date.now() % 100000}`
      const { request } = await factory.control<{ request: string }>('/request/open', {
        alias,
        brief: 'Admit VELDO-9156, the stale lock sweeper, into the backlog?',
        deadline_hours: 40,
        risk: 'Medium',
      })
      await page.goto(factory.origin + '/decisions/' + request)
      await expect(page.getByTestId('decision')).toBeVisible()
      await factory.control('/request/revise', { alias })
      await page.locator('[data-choice="accept"]').click()
      await page.getByTestId('rationale').fill('Answering what the screen showed.')
      await page.getByTestId('send-answer').click()
      await expect(page.getByTestId('answer-bar').getByTestId('refusal')).toBeVisible()
      return '[data-testid="load-current"]'
    },
    async cleanup(page) {
      // Answer the current version here, so the inbox of later screenshots holds the curated decisions only.
      await page.getByTestId('load-current').click()
      await expect(page.getByTestId('decision')).toHaveAttribute('data-presentation-version', '2')
      await page.locator('[data-choice="reject"]').click()
      await page.getByTestId('rationale').fill('Cleaning up after the screenshot.')
      await page.getByTestId('send-answer').click()
      await expect(page.getByTestId('answer-result')).toBeVisible()
    },
  },
  {
    name: 'decisions-empty',
    who: 'cmember',
    async open(page, factory) {
      await page.goto(factory.origin + '/decisions')
      await expect(page.locator('[data-state="empty"]')).toBeVisible()
      return null
    },
  },
  {
    name: 'decisions-error',
    who: 'outsider',
    async open(page, factory) {
      await page.goto(factory.origin + '/decisions')
      await expect(page.locator('[data-state="error"]')).toBeVisible()
      return null
    },
  },
  {
    name: 'you',
    async open(page, factory) {
      await page.goto(factory.origin + '/you')
      await expect(page.getByTestId('you-principal')).toBeVisible()
      return '[data-testid="sign-out"]'
    },
  },
]

interface Problems {
  overflow: number
  overlaps: string[]
  primary: string | null
  smallTargets: string[]
}

/** Measure the page as rendered: page-wide overflow, overlapping controls, the primary action and targets. */
async function measure(page: Page, primary: string | null, phone: boolean): Promise<Problems> {
  if (primary) await page.locator(primary).first().scrollIntoViewIfNeeded()
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
        .filter((el) => !el.closest('.monaco-editor, .vradio, .vswitch') || el.matches('.vradio-input, .vswitch-input'))
      const pinned = (el: Element): Element | null => {
        for (let n: Element | null = el; n; n = n.parentElement) {
          const position = getComputedStyle(n).position
          if (position === 'fixed' || position === 'sticky') return n
        }
        return null
      }
      const label = (el: Element) => (el as HTMLElement).dataset.testid ?? el.getAttribute('aria-label') ?? el.textContent?.trim().slice(0, 30) ?? el.tagName
      const overlaps: string[] = []
      for (let i = 0; i < controls.length; i += 1)
        for (let j = i + 1; j < controls.length; j += 1) {
          const a = controls[i]!
          const b = controls[j]!
          if (a.contains(b) || b.contains(a) || a.closest('label')?.contains(b) || b.closest('label')?.contains(a)) continue
          // Page content scrolls beneath pinned chrome (the bottom bar, the pinned answer bar) by design;
          // controls are compared within the same layer only.
          if (pinned(a) !== pinned(b)) continue
          const ra = a.getBoundingClientRect()
          const rb = b.getBoundingClientRect()
          const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left)
          const y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top)
          if (x > 1 && y > 1) overlaps.push(`${label(a)} / ${label(b)}`)
        }
      let primaryProblem: string | null = null
      if (primary) {
        const el = document.querySelector(primary)
        if (!el || !visible(el)) primaryProblem = 'not visible'
        else {
          const r = el.getBoundingClientRect()
          if (r.left < 0 || r.right > vw || r.top < 0 || r.bottom > vh) primaryProblem = `clipped at ${JSON.stringify(r)}`
          else {
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
            if (!hit || !(el === hit || el.contains(hit))) primaryProblem = `covered by ${hit?.className ?? 'nothing'}`
            else if (phone && (r.height < 44 || r.width < 44)) primaryProblem = `target ${r.width}x${r.height}`
          }
        }
      }
      const smallTargets: string[] = []
      if (phone)
        for (const el of document.querySelectorAll('.bottombar-link, .screen-back, .run-row, .inbox-row, .choice, .vbtn:not(.vbtn-small)')) {
          if (!visible(el)) continue
          const r = el.getBoundingClientRect()
          if (r.height < 44 || r.width < 44) smallTargets.push(`${label(el)} ${Math.round(r.width)}x${Math.round(r.height)}`)
        }
      return { overflow, overlaps, primary: primaryProblem, smallTargets }
    },
    { primary, phone },
  )
}

async function setTheme(page: Page, theme: Theme) {
  await page.evaluate((t) => {
    localStorage.setItem('veldo.theme', t)
    document.documentElement.setAttribute('data-theme', t)
  }, theme)
}

for (const viewport of [...PHONES, ...DESKTOPS]) {
  const phone = viewport.width < 768
  test(`every screen and state at ${viewport.width}px, light and dark`, async ({ browser, factory }) => {
    test.setTimeout(300_000)
    const ids = await factory.state()
    const failures: string[] = []
    const sessions = new Map<string, Page>()
    const pageFor = async (who: string | null) => {
      const key = who ?? 'nobody'
      let page = sessions.get(key)
      if (!page) {
        const context = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone, deviceScaleFactor: 1 })
        page = await context.newPage()
        if (who) await signIn(page, factory, who)
        sessions.set(key, page)
      }
      return page
    }
    for (const theme of ['light', 'dark'] as Theme[]) {
      for (const render of RENDERS) {
        const page = await pageFor(render.who === undefined ? 'owner' : render.who)
        const watch = await guard(page)
        await page.goto(factory.origin + '/sign-in')
        await setTheme(page, theme)
        const primary = await render.open(page, factory, ids)
        await page.evaluate(() => document.fonts.ready)
        const found = await measure(page, primary, phone)
        const where = `${render.name} ${viewport.width} ${theme}`
        if (found.overflow > 0) failures.push(`${where}: page overflows by ${found.overflow}px`)
        if (found.overlaps.length) failures.push(`${where}: overlapping ${found.overlaps.join('; ')}`)
        if (found.primary) failures.push(`${where}: primary action ${found.primary}`)
        if (found.smallTargets.length) failures.push(`${where}: small targets ${found.smallTargets.join('; ')}`)
        // The proof's screenshots come from a fresh harness running this file alone (VELDO_SCREENS=1), so they
        // show the curated factory, not what other tests left behind.
        if (process.env.VELDO_SCREENS)
          await page.screenshot({ path: path.join(SCREENS, `${render.name}-${viewport.width}-${theme}.jpg`), type: 'jpeg', quality: 70, fullPage: false })
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).exclude('.monaco-editor').analyze()
        for (const v of axe.violations) failures.push(`${where}: axe ${v.id} ${v.nodes.map((n) => n.target.join(' ')).join(', ').slice(0, 200)}`)
        const violations = await watch.violations()
        if (violations.length) failures.push(`${where}: policy violations ${violations.join('; ')}`)
        await render.cleanup?.(page, factory)
        const release = (page as unknown as { release?: () => Promise<void> }).release
        if (release) {
          await release()
          ;(page as unknown as { release?: unknown }).release = undefined
        }
      }
    }
    for (const page of sessions.values()) await page.context().close()
    expect(failures).toEqual([])
  })
}

test('phone decisions: the inline answer action is visible, unclipped and works at 360px', async ({ browser, factory }) => {
  const ids = await factory.state()
  const context = await browser.newContext({ viewport: { width: 360, height: 640 }, hasTouch: true, isMobile: true })
  const page = await context.newPage()
  await signIn(page, factory)
  await page.goto(factory.origin + '/decisions/' + ids.requests.de4)
  await expect(page.getByTestId('decision')).toBeVisible()
  // On arrival, without scrolling: the question and every choice are above the fold, none under a pinned bar.
  for (const choice of await page.locator('[data-choice]').all()) await expect(choice).toBeInViewport({ ratio: 1 })
  const bottombar = (await page.locator('.bottombar').boundingBox())!
  for (const choice of await page.locator('[data-choice]').all()) expect((await choice.boundingBox())!.y + 48).toBeLessThanOrEqual(bottombar.y)
  // Once a choice is picked, the answer action is pinned above the bottom bar.
  await page.locator('[data-choice="accept"]').tap()
  const found = await measure(page, null, true)
  expect(found.overflow).toBe(0)
  const send = page.getByTestId('send-answer')
  await expect(send).toBeInViewport({ ratio: 1 })
  const box = (await send.boundingBox())!
  expect(box.height).toBeGreaterThanOrEqual(44)
  expect(box.x).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width).toBeLessThanOrEqual(360)
  const hit = await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.closest('[data-testid="send-answer"]') !== null, {
    x: box.x + box.width / 2,
    y: box.y + box.height / 2,
  })
  expect(hit).toBe(true)
  // And a touch on it acts: with no rationale yet it names what is missing, beside it.
  await send.tap()
  await expect(page.locator('.answer-problem')).toHaveText('Add a rationale: say briefly why.')
  await context.close()
})

test('keyboard only on desktop: sign in, open a decision and answer it without a pointer', async ({ browser, factory }) => {
  const { request } = await factory.control<{ request: string }>('/request/open', { alias: `dk${Date.now() % 100000}` })
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 } })
  const page = await context.newPage()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs')
  await expect(page.getByTestId('runs')).toBeVisible()
  const focusTo = async (selector: string, limit = 40) => {
    for (let i = 0; i < limit; i += 1) {
      if (await page.evaluate((s) => document.activeElement?.matches(s) ?? false, selector)) return
      await page.keyboard.press('Tab')
    }
    throw new Error(`Tab never reached ${selector}`)
  }
  await focusTo('.rail [data-nav="decisions"]')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('inbox')).toBeVisible()
  await focusTo(`.inbox-row[data-request="${request}"]`, 80)
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('decision')).toHaveAttribute('data-request', request)
  await focusTo('#choice-0')
  await page.keyboard.press('Space')
  await expect(page.locator('[data-choice="accept"]')).toHaveClass(/is-picked/)
  await focusTo('#rationale')
  await page.keyboard.type('Answered with the keyboard only.')
  await focusTo('[data-testid="send-answer"]')
  const focusRing = await page.evaluate(() => getComputedStyle(document.activeElement!).outlineStyle)
  expect(focusRing).not.toBe('none')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('answer-result')).toContainText('Answer sent')
  await context.close()
})

test('touch on phone: open a run and a decision from the bottom bar and answer by tapping', async ({ browser, factory }) => {
  const ids = await factory.state()
  const { request } = await factory.control<{ request: string }>('/request/open', { alias: `dt${Date.now() % 100000}` })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
  const page = await context.newPage()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs')
  await page.locator(`[data-dispatch="${ids.dispatches.live}"]`).tap()
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'live')
  await page.locator('.bottombar [data-nav="decisions"]').tap()
  await expect(page.getByTestId('inbox')).toBeVisible()
  await page.locator(`.inbox-row[data-request="${request}"]`).tap()
  await page.locator('[data-choice="return_for_elaboration"]').tap()
  await page.getByTestId('rationale').tap()
  await page.keyboard.type('Needs a smaller first slice.')
  await page.getByTestId('send-answer').tap()
  await expect(page.getByTestId('answer-result')).toContainText('Answer sent')
  await page.getByRole('link', { name: 'Decisions' }).first().tap()
  await expect(page.locator(`.inbox-row[data-request="${request}"]`)).toHaveCount(0)
  await context.close()
})

test('served assets: every response is this origin and every asset is a file of the build', async ({ page, factory }) => {
  const ids = await factory.state()
  const responses: { url: string; type: string }[] = []
  page.on('response', (r) => responses.push({ url: r.url(), type: r.headers()['content-type'] ?? '' }))
  await signIn(page, factory)
  for (const screen of ['/runs', `/runs/${ids.dispatches.done}`, '/decisions', `/decisions/${ids.requests.de5}`, '/you']) {
    await page.goto(factory.origin + screen)
    await page.waitForLoadState('networkidle')
  }
  await page.locator('[data-seq="7"]').count()
  const built = new Set(readdirSync(path.join(UI, 'dist', 'assets')).map((f) => '/assets/' + f))
  const foreign = responses.filter((r) => new URL(r.url).origin !== factory.origin)
  expect(foreign).toEqual([])
  const assets = responses.map((r) => new URL(r.url).pathname).filter((p) => p.startsWith('/assets/'))
  expect(assets.filter((p) => !built.has(p))).toEqual([])
  const fonts = assets.filter((p) => p.endsWith('.woff2') || p.endsWith('.ttf'))
  for (const font of fonts) expect(font).toMatch(/^\/assets\/(ibm-plex-(sans|mono)|codicon)-/)
})

test('phone terminal: the record gets the screen, the headline unclipped, the strip on one line and the controls in one bar', async ({ browser, factory }) => {
  const ids = await factory.state()
  for (const viewport of PHONES) {
    const context = await browser.newContext({ viewport, hasTouch: true, isMobile: true })
    const page = await context.newPage()
    await signIn(page, factory)
    await page.goto(factory.origin + '/runs/' + ids.dispatches.done)
    await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
    // The headline wraps rather than clipping: the host is whole and inside the screen.
    const headline = page.getByTestId('run-headline')
    const host = headline.locator('li', { hasText: 'veldo-linux-1' })
    await expect(host).toHaveText('on veldo-linux-1')
    expect(await headline.evaluate((el) => el.scrollWidth <= el.clientWidth + 1), `headline clipped at ${viewport.width}`).toBe(true)
    const hostBox = (await host.boundingBox())!
    const lineBox = (await headline.boundingBox())!
    expect(hostBox.x + hostBox.width, `host inside the headline at ${viewport.width}`).toBeLessThanOrEqual(Math.min(viewport.width, lineBox.x + lineBox.width) + 1)
    const log = (await page.locator('.terminal-body').boundingBox())!
    expect(log.height / viewport.height, `log height at ${viewport.width}`).toBeGreaterThan(0.55)
    const strip = (await page.getByTestId('station-strip').boundingBox())!
    expect(strip.height).toBeLessThanOrEqual(44)
    const bar = (await page.locator('.terminal-bar').boundingBox())!
    expect(bar.height).toBeLessThanOrEqual(52)
    for (const control of ['#follow', '#raw', '[data-testid="search-open"]']) {
      const box = (await page.locator(control).boundingBox())!
      expect(box.y).toBeGreaterThanOrEqual(bar.y - 1)
      expect(box.y + box.height).toBeLessThanOrEqual(bar.y + bar.height + 1)
    }
    // Search opens in the same bar and finds lines.
    await page.getByTestId('search-open').tap()
    await page.getByTestId('search').fill('pytest')
    await expect(page.getByTestId('search-hits')).toHaveText(/^1 of \d+$/)
    await context.close()
  }
})

test('desktop decisions: the most urgent decision is open, and the list scrolls on its own', async ({ browser, factory }) => {
  const ids = await factory.state()
  for (let n = 0; n < 12; n += 1) await factory.control('/request/open', { alias: `dq${Date.now() % 100000}${n}`, deadline_hours: 200 + n })
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 } })
  const page = await context.newPage()
  await signIn(page, factory)
  await page.goto(factory.origin + '/decisions')
  await expect(page.getByTestId('decision')).toHaveAttribute('data-request', ids.requests.de3!)
  await expect(page.locator(`.inbox-row[data-request="${ids.requests.de3}"]`)).toHaveAttribute('aria-current', 'true')
  // The page itself does not scroll; the list does, and its header stays in view.
  expect(await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)).toBeLessThanOrEqual(1)
  const list = page.locator('.decisions-list')
  expect(await list.evaluate((e) => e.scrollHeight > e.clientHeight)).toBe(true)
  await list.evaluate((e) => e.scrollTo({ top: e.scrollHeight }))
  await expect(page.getByRole('heading', { level: 1, name: 'Decisions' })).toBeInViewport()
  await context.close()
})

// VELDO-0229 (Telegram 38234 and 38235, sections 4 to 6): the one theme preference, keyboard focus and the primary
// action's contrast on Nuxt UI's controls, and nothing requested from another origin (no Iconify, no font CDN).

test('theme: one preference across the sidebar and the account switch, navigation and reload', async ({ browser, factory }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 } })
  const page = await context.newPage()
  const watch = await guard(page)
  await signIn(page, factory)
  await page.evaluate(() => localStorage.setItem('veldo.theme', 'light'))
  await page.reload()
  const theme = () =>
    page.evaluate(() => ({ attr: document.documentElement.dataset.theme, dark: document.documentElement.classList.contains('dark') }))
  const appearance = page.getByRole('switch', { name: 'Dark appearance' })
  await expect(appearance).toHaveAttribute('aria-checked', 'false')
  expect(await theme()).toEqual({ attr: 'light', dark: false })
  await page.getByText('Dark appearance').click()
  await expect(appearance).toHaveAttribute('aria-checked', 'true')
  expect(await theme()).toEqual({ attr: 'dark', dark: true })
  // Navigation keeps it.
  await page.locator('.rail [data-nav="runs"]').click()
  await expect(page.getByRole('heading', { level: 1, name: 'Runs' })).toBeVisible()
  expect(await theme()).toEqual({ attr: 'dark', dark: true })
  // A reload keeps it.
  await page.reload()
  await expect(page.getByRole('heading', { level: 1, name: 'Runs' })).toBeVisible()
  expect(await theme()).toEqual({ attr: 'dark', dark: true })
  // The account screen's switch is the same preference, both ways.
  await page.locator('.rail [data-nav="you"]').click()
  const account = page.getByLabel('Dark theme')
  await expect(account).toBeChecked()
  await account.click()
  await expect(account).not.toBeChecked()
  expect(await theme()).toEqual({ attr: 'light', dark: false })
  await expect(appearance).toHaveAttribute('aria-checked', 'false')
  expect(await watch.violations()).toEqual([])
  await context.close()
})

/** WCAG contrast of two computed colors (rgb() or color(srgb ...)). */
function contrastOf(a: string, b: string): number {
  const parse = (c: string) => {
    const srgb = c.match(/color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)/)
    if (srgb) return [1, 2, 3].map((i) => Number(srgb[i]))
    const rgb = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
    if (!rgb) throw new Error(`unreadable color ${c}`)
    return [1, 2, 3].map((i) => Number(rgb[i]) / 255)
  }
  const lum = (c: string) => {
    const [r, g, b] = parse(c).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
    return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
  }
  const [x, y] = [lum(a), lum(b)]
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)
}

for (const theme of ['light', 'dark'] as Theme[]) {
  test(`primary action: contrast at rest and on hover, and a visible keyboard focus, ${theme}`, async ({ browser, factory }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 860 } })
    const page = await context.newPage()
    const watch = await guard(page)
    await page.goto(factory.origin + '/sign-in')
    await setTheme(page, theme)
    await page.reload()
    const button = page.getByTestId('sign-in')
    await expect(button).toBeVisible()
    expect(await button.getAttribute('data-slot'), 'the primary action is a Nuxt UI button').toBe('base')
    const colors = () => button.evaluate((e) => ({ fg: getComputedStyle(e).color, bg: getComputedStyle(e).backgroundColor }))
    const rest = await colors()
    expect(contrastOf(rest.fg, rest.bg), `at rest ${JSON.stringify(rest)}`).toBeGreaterThanOrEqual(4.5)
    await button.hover()
    await page.waitForTimeout(250)
    const hover = await colors()
    expect(hover.bg, 'hover changes the fill').not.toBe(rest.bg)
    expect(contrastOf(hover.fg, hover.bg), `on hover ${JSON.stringify(hover)}`).toBeGreaterThanOrEqual(4.5)
    // Keyboard focus: tab to the action; its outline is solid, at least 2px, and not transparent.
    await page.mouse.move(0, 0)
    await page.locator('h1').focus()
    for (let n = 0; n < 6 && !(await button.evaluate((e) => e === document.activeElement)); n += 1) await page.keyboard.press('Tab')
    expect(await button.evaluate((e) => e === document.activeElement && e.matches(':focus-visible'))).toBe(true)
    const ring = await button.evaluate((e) => {
      const s = getComputedStyle(e)
      return { style: s.outlineStyle, width: parseFloat(s.outlineWidth), color: s.outlineColor, page: getComputedStyle(document.body).backgroundColor }
    })
    expect(ring.style, JSON.stringify(ring)).toBe('solid')
    expect(ring.width).toBeGreaterThanOrEqual(2)
    expect(contrastOf(ring.color, ring.page), `focus ring against the page ${JSON.stringify(ring)}`).toBeGreaterThanOrEqual(3)
    expect(await watch.violations()).toEqual([])
    await context.close()
  })
}

test('no request leaves the origin and no built asset names the Iconify API or a font CDN', async ({ browser, factory }) => {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  const assets = readdirSync(path.join(dist, 'assets')).filter((f) => /\.(js|css)$/.test(f))
  const named = assets.filter((f) => /api\.iconify\.design|api\.simplesvg\.com|api\.unisvg\.com|fonts\.googleapis|fonts\.bunny|fonts\.gstatic/.test(readFileSync(path.join(dist, 'assets', f), 'utf8')))
  expect(named).toEqual([])
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 } })
  const page = await context.newPage()
  const watch = await guard(page)
  await signIn(page, factory)
  const ids = await factory.state()
  for (const where of ['/', '/runs', '/runs/' + ids.dispatches.done, '/decisions', '/you']) {
    await page.goto(factory.origin + where)
    await page.waitForLoadState('networkidle')
  }
  // Icons are drawn (the sidebar's), from the bundle.
  expect(await page.locator('.rail-icon').first().evaluate((e) => e.tagName.toLowerCase())).toBe('svg')
  const foreign = watch.requests.filter((r) => !r.url.startsWith(factory.origin) && !r.url.startsWith('data:'))
  expect(foreign).toEqual([])
  expect(await watch.violations()).toEqual([])
  await context.close()
})
