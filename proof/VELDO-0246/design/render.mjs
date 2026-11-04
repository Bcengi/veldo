// Renders the VELDO-0246 pilot screens at 2x with Playwright driving system Chrome (/opt/google/chrome).
// Run from this folder after python3 gen.py:  NODE_PATH=<engine/ui>/node_modules node render.mjs
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const here = path.dirname(fileURLToPath(import.meta.url))
const screens = [['a-canvas-social-post', 1440, 900], ['b-step-inspector', 1440, 900], ['c-run-on-canvas', 1440, 900], ['d-run-phone', 390, 844]]
const browser = await chromium.launch({ executablePath: '/opt/google/chrome/chrome' })
for (const [name, width, height] of screens) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 2 })
  await page.goto('file://' + path.join(here, name + '.html'))
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({ path: path.join(here, name + '.png') })
  await page.close()
}
await browser.close()
