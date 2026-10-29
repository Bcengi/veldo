import { defineConfig } from '@playwright/test'

/** Browser tests run against a real factory harness (e2e/harness.py) in system Chrome, one worker, so the
 * shared host is not loaded beyond one browser. */
export default defineConfig({
  testDir: 'e2e',
  testMatch: /.*\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['json', { outputFile: process.env.VELDO_E2E_REPORT ?? 'test-results/e2e.json' }]],
  use: {
    channel: 'chrome',
    headless: true,
    trace: 'off',
    screenshot: 'off',
    actionTimeout: 10_000,
  },
})
