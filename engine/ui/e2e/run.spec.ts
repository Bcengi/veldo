import type { Page } from '@playwright/test'
import { expect, guard, signIn, test, type Factory } from './fixtures'

/**
 * VELDO-0145 AC2: the run screen is a live terminal of the run's execution record, every line in the order
 * the engine produced it, never a summary.
 */

interface KeptLine {
  seq: number
  stream: string
  payload: string
  redacted: string[]
}

async function recordOf(factory: Factory, key: string) {
  return (await factory.control<{ lines: KeptLine[]; total: number }>('/record/read', { key })).lines
}

/** The lines the terminal shows, as sequences, in screen order. */
const shownSeqs = (page: Page) =>
  page.locator('[data-testid="lines"] > li').evaluateAll((els) => els.map((e) => Number((e as HTMLElement).dataset.seq)))

/** Compare the terminal with the record line by line: same sequences in order, and in raw view each line's
 * payload exactly as kept. */
async function compareLineByLine(page: Page, record: KeptLine[]) {
  expect(await shownSeqs(page)).toEqual(record.map((l) => l.seq))
  await page.getByText('Raw', { exact: true }).click()
  const payloads = await page.locator('[data-testid="lines"] > li [data-testid="payload"]').allTextContents()
  expect(payloads).toEqual(record.map((l) => l.payload))
  const streams = await page.locator('[data-testid="lines"] > li').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.stream))
  expect(streams).toEqual(record.map((l) => l.stream))
  await page.getByText('Raw', { exact: true }).click()
}

test('full detail: an ended run shows every kept line, tool calls, output, edits and errors', async ({ page, factory }) => {
  const state = await factory.state()
  const watch = await guard(page)
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + state.dispatches.done)
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  const record = await recordOf(factory, 'done')
  expect(record.length).toBeGreaterThan(8)
  await compareLineByLine(page, record)

  // Every engine line's content is on screen in full: the tool and its command, its output, the edit.
  for (const line of record) {
    const row = page.locator(`[data-testid="lines"] > li[data-seq="${line.seq}"]`)
    if (line.stream !== 'engine') {
      await expect(row).toContainText(line.payload)
      continue
    }
    const event = JSON.parse(line.payload)
    for (const part of event.message?.content ?? []) {
      if (part.type === 'text') await expect(row).toContainText(part.text)
      if (part.type === 'tool_use' && part.name === 'Bash') {
        await expect(row.locator('.tb-tool')).toHaveText('Bash')
        await expect(row.locator('.tb-summary')).toHaveText(part.input.command)
      }
      if (part.type === 'tool_use' && part.name === 'Edit') {
        await expect(row.locator('.tb-summary')).toHaveText(part.input.file_path)
        await row.scrollIntoViewIfNeeded()
        // The edit is a Monaco diff of exactly the old and new text.
        await expect(row.locator('.monaco-diff-editor')).toBeVisible()
        const shown = await row.locator('[data-testid="diff-text"]').textContent()
        expect(shown).toContain(part.input.old_string)
        expect(shown).toContain(part.input.new_string)
      }
      if (part.type === 'tool_result') {
        await expect(row.locator('.tb-output')).toHaveText(part.content)
        // Command output is monospace.
        const family = await row.locator('.tb-output').evaluate((e) => getComputedStyle(e).fontFamily)
        expect(family).toContain('IBM Plex Mono')
        if (part.is_error) await expect(row).toHaveAttribute('data-error', 'true')
        else await expect(row).not.toHaveAttribute('data-error', 'true')
      }
    }
    if (event.type === 'result') await expect(row).toContainText(event.result)
  }

  // Search finds exactly the lines whose payload holds the text, and steps through them.
  const holding = record.filter((l) => l.payload.toLowerCase().includes('pytest')).map((l) => l.seq)
  await page.getByTestId('search').fill('pytest')
  await expect(page.getByTestId('search-hits')).toHaveText(`1 of ${holding.length}`)
  expect(await page.locator('.tline.is-match').evaluateAll((els) => els.map((e) => Number((e as HTMLElement).dataset.seq)))).toEqual(holding)
  await page.getByTestId('search').press('Enter')
  await expect(page.getByTestId('search-hits')).toHaveText(`2 of ${holding.length}`)
  await expect(page.locator('.tline.is-current-match')).toHaveAttribute('data-seq', String(holding[1]))
  expect(await watch.violations()).toEqual([])
})

test('live: lines appear as the worker prints them, and a dropped connection resumes from its cursor', async ({ page, factory }) => {
  const made = await factory.control<{ key: string; dispatch: string }>('/dispatch/new', { unit: 'VELDO-9170', count: 4 })
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + made.dispatch)
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'live')
  await expect(page.getByTestId('line-count')).toHaveText('4 lines')
  // Following: new lines arrive without a reload, in order, and the view stays at the end.
  await factory.control('/record/append', { key: made.key, start: 1, count: 3 })
  await expect(page.getByTestId('line-count')).toHaveText('10 lines')
  expect(await shownSeqs(page)).toEqual(Array.from({ length: 10 }, (_, i) => i + 1))
  // The connection drops mid-run while lines are being written; the browser reconnects from the last
  // frame it received and the API resumes after it.
  await factory.control('/record/drop', { key: made.key })
  await factory.control('/record/append', { key: made.key, start: 4, count: 2 })
  await factory.control('/record/append', { key: made.key, start: 6, count: 2 })
  await expect(page.locator('.terminal-reconnects')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('line-count')).toHaveText('18 lines', { timeout: 15_000 })
  const record = await recordOf(factory, made.key)
  expect(record.length).toBe(18)
  await compareLineByLine(page, record)
  // The run ends: the terminal says so, with the committed count.
  await factory.control('/record/end', { key: made.key })
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  await expect(page.locator('.terminal-committed')).toContainText('18 lines committed')
  await compareLineByLine(page, await recordOf(factory, made.key))
})

test('follow mode: scrolling up stops following; jumping to the latest resumes it', async ({ page, factory }) => {
  const made = await factory.control<{ key: string; dispatch: string }>('/dispatch/new', { unit: 'VELDO-9171', count: 4 })
  await factory.control('/record/append', { key: made.key, start: 1, count: 20 })
  await page.setViewportSize({ width: 1280, height: 720 })
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + made.dispatch)
  await expect(page.getByTestId('line-count')).toHaveText('44 lines')
  const body = page.locator('.terminal-body')
  const atEnd = () => body.evaluate((e) => e.scrollHeight - e.scrollTop - e.clientHeight < 30)
  await expect.poll(atEnd).toBe(true)
  await body.evaluate((e) => e.scrollTo({ top: 0 }))
  await expect(page.locator('#follow')).not.toBeChecked()
  await factory.control('/record/append', { key: made.key, start: 21, count: 1 })
  await expect(page.getByTestId('jump')).toHaveText('Jump to latest (2 new)')
  await page.getByTestId('jump').click()
  await expect(page.locator('#follow')).toBeChecked()
  await expect.poll(atEnd).toBe(true)
})

test('station strip: the unit is lit at its station beside the record', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + state.dispatches.live)
  const strip = page.getByTestId('station-strip')
  await expect(strip).toHaveAttribute('data-unit-state', 'RUNNING')
  await expect(strip.locator('[aria-current="step"]')).toContainText('Build')
  await expect(strip.locator('[aria-current="step"] .lamp')).toHaveClass(/lamp-live/)
  await expect(page.getByTestId('run-station')).toContainText('build')
  await page.goto(factory.origin + '/runs/' + state.dispatches.quiet)
  await expect(strip.locator('[aria-current="step"]')).toContainText('Review')
  await expect(page.getByTestId('terminal-empty')).toBeVisible()
})

test('run header: the run\'s state, elapsed time, engine and model, host and station, with the dispatch id as a copyable detail', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + state.dispatches.done)
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('VELDO-9145')
  await expect(page.getByTestId('run-status')).toContainText('Done')
  await expect(page.getByTestId('elapsed')).toHaveText(/^\d+ (s|min \d\d s)$/)
  const headline = page.getByTestId('run-headline')
  await expect(headline).toContainText('Claude Code')
  await expect(page.getByTestId('run-model')).toContainText('claude-opus-5-5')
  await expect(headline).toContainText('veldo-linux-1')
  await expect(page.getByTestId('run-station')).toContainText('build')
  // The dispatch id is not the headline: it waits behind a disclosure, in full, with a copy action.
  await expect(page.getByTestId('dispatch-id')).toBeHidden()
  await page.getByText('Dispatch id', { exact: true }).click()
  await expect(page.getByTestId('dispatch-id')).toHaveText(state.dispatches.done!)
  await expect(page.getByRole('button', { name: 'Copy dispatch id' })).toBeVisible()
  // A running run's elapsed time keeps counting.
  await page.goto(factory.origin + '/runs/' + state.dispatches.live)
  await expect(page.getByTestId('run-status')).toContainText('Running')
  const first = await page.getByTestId('elapsed').textContent()
  await expect.poll(() => page.getByTestId('elapsed').textContent(), { timeout: 5000 }).not.toBe(first)
})

test('compact gutter: each line\'s sequence, its time since the first line and an inline kind tag on the content\'s row', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + state.dispatches.done)
  await expect(page.getByTestId('terminal')).toHaveAttribute('data-state', 'ended')
  const times = await page.locator('.tline-time').allTextContents()
  expect(times[0]).toBe('+0.0 s')
  expect(new Set(times).size).toBeGreaterThan(5)
  for (const t of times) expect(t).toMatch(/^\+(\d+\.\d s|\d+ s|\d+:\d\d)$/)
  // The tag and the content share a row: the tag's top is level with the content's first line.
  const row = page.locator('[data-testid="lines"] > li[data-seq="4"]')
  await expect(row.locator('.tline-kind')).toHaveText('tool')
  const tag = (await row.locator('.tline-kind').boundingBox())!
  const content = (await row.locator('.tb-call-head').boundingBox())!
  expect(Math.abs(tag.y - content.y)).toBeLessThan(8)
  await expect(page.locator('[data-testid="lines"] > li[data-seq="5"] .tline-kind')).toHaveText('error')
})
