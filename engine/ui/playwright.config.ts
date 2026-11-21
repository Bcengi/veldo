import { defineConfig } from '@playwright/test'
import { WAIT_HANG_MS } from './e2e/fixtures'

/** Browser tests run against a real factory harness (e2e/harness.py) in system Chrome, one worker, so the
 * shared host is not loaded beyond one browser.
 *
 * Durations (VELDO-0358): one wait (an expectation, an action, a navigation) is bounded by the wait hang bound and
 * by nothing shorter, so a busy machine cannot turn a slow answer into a red. No test has a limit on its total
 * time (timeout 0): the run is bounded by progress, by the Progress reporter of e2e/fixtures.ts, which ends it only
 * after the process hang bound has passed with no test or step beginning or ending. */
export default defineConfig({
  testDir: 'e2e',
  testMatch: /.*\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 0,
  expect: { timeout: WAIT_HANG_MS },
  reporter: [
    ['list'],
    ['json', { outputFile: process.env.VELDO_E2E_REPORT ?? 'test-results/e2e.json' }],
    ['./e2e/fixtures.ts'],
  ],
  use: {
    channel: 'chrome',
    headless: true,
    trace: 'off',
    screenshot: 'off',
    actionTimeout: WAIT_HANG_MS,
    navigationTimeout: WAIT_HANG_MS,
  },
})
