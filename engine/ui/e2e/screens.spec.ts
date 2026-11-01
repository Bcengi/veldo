import { mkdirSync } from 'node:fs'
import path from 'node:path'
import type { Page } from '@playwright/test'
import { ROOT, expect, guard, signIn, test } from './fixtures'

/**
 * VELDO-0229 AC5 (Telegram 38234 and 38235, section 7): screenshots of the production build against the factory
 * harness, which serves the build under the API's content security policy over its seeded demonstration factory.
 * Run alone, on a fresh harness: VELDO_SCREENS_0229=1 npx playwright test e2e/screens.spec.ts. Each image carries
 * a label saying the data is seeded demonstration data; the label is drawn by this test, not by the UI.
 */
const OUT = path.join(ROOT, 'proof', 'VELDO-0229', 'screens')
test.skip(!process.env.VELDO_SCREENS_0229, 'screenshots are taken on request (VELDO_SCREENS_0229=1)')

async function label(page: Page) {
  await page.evaluate(() => {
    const tag = document.createElement('div')
    tag.textContent = 'Seeded demonstration data (Veldo test harness)'
    // CSS object model only: the policy refuses style markup, not style properties.
    Object.assign(tag.style, {
      position: 'fixed', right: '12px', bottom: '12px', zIndex: '9999', padding: '4px 10px', borderRadius: '999px',
      font: '600 12px "IBM Plex Sans Variable", sans-serif', background: '#f2a900', color: '#1b263c', pointerEvents: 'none',
    })
    document.body.appendChild(tag)
  })
}

async function shoot(page: Page, name: string, theme: 'light' | 'dark') {
  await page.evaluate((t) => localStorage.setItem('veldo.theme', t), theme)
  await page.reload()
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(400)
  await label(page)
  await page.screenshot({ path: path.join(OUT, `${name}.png`), type: 'png', fullPage: false })
}

test('section 7 screenshots from the production build, seeded demonstration data', async ({ browser, factory }) => {
  test.setTimeout(240_000)
  mkdirSync(OUT, { recursive: true })
  const ids = await factory.state()
  const desk = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const page = await desk.newPage()
  const watch = await guard(page)
  await signIn(page, factory)

  await page.goto(factory.origin + '/')
  await expect(page.getByTestId('oldest')).toBeVisible()
  await expect(page.getByTestId('inbox')).toBeVisible()
  await shoot(page, '1-overview-dark-1440', 'dark')
  await expect(page.getByTestId('andon')).toBeVisible()
  await shoot(page, '2-overview-light-1440', 'light')
  await expect(page.getByTestId('andon')).toBeVisible()

  await page.goto(factory.origin + '/runs/' + ids.dispatches.done)
  await page.evaluate(() => localStorage.setItem('veldo.theme', 'dark'))
  await page.reload()
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  // The record opens at its edit, so the Monaco diff is on screen.
  await page.locator('[data-seq="7"]').evaluate((e) => e.scrollIntoView({ block: 'start' }))
  await expect(page.locator('[data-seq="7"] .monaco-diff-editor')).toBeVisible()
  await page.waitForTimeout(600)
  await label(page)
  await page.screenshot({ path: path.join(OUT, '3-run-detail-diff-dark-1440.png'), type: 'png' })

  await page.goto(factory.origin + '/decisions')
  await expect(page.getByTestId('decision')).toBeVisible()
  await shoot(page, '4-decisions-light-1440', 'light')
  await expect(page.getByTestId('decision')).toBeVisible()

  await page.goto(factory.origin + '/runs')
  await expect(page.getByTestId('runs')).toBeVisible()
  await shoot(page, '6-runs-dark-1440', 'dark')
  await expect(page.getByTestId('runs')).toBeVisible()
  expect(await watch.violations()).toEqual([])
  await desk.close()

  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, hasTouch: true, isMobile: true })
  const small = await phone.newPage()
  const watchPhone = await guard(small)
  await signIn(small, factory)
  await small.goto(factory.origin + '/')
  await expect(small.getByTestId('andon')).toBeVisible()
  await shoot(small, '5-overview-phone-dark-390', 'dark')
  await expect(small.getByTestId('andon')).toBeVisible()
  await small.goto(factory.origin + '/decisions/' + ids.requests.de5)
  await expect(small.getByTestId('decision')).toBeVisible()
  await shoot(small, '7-decision-phone-light-390', 'light')
  await expect(small.getByTestId('decision')).toBeVisible()
  expect(await watchPhone.violations()).toEqual([])
  await phone.close()

  const out = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const signin = await out.newPage()
  await signin.goto(factory.origin + '/sign-in')
  await expect(signin.getByTestId('sign-in')).toBeVisible()
  await shoot(signin, '8-sign-in-dark-1440', 'dark')
  await out.close()
})
