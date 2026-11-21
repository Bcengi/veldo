import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { once } from 'node:events'
import { appendFileSync, existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'
import { test as base, expect, type BrowserContext, type Page } from '@playwright/test'
import type { FullConfig, Reporter, Suite, TestCase, TestResult, TestStep } from '@playwright/test/reporter'

/**
 * THE TWO DURATIONS OF THE BROWSER TESTS (VELDO-0358; the same two as scripts/suites/support/waits.py). No test,
 * fixture or configuration names another one, sleeps, or reads a clock.
 *
 * WAIT_HANG_MS bounds one wait from its start: an expectation, an action, a navigation, the harness's ready line,
 * the harness's exit. A wait that reaches it is hung, which is red and names itself; it is never read as "no".
 * PROCESS_HANG_MS bounds the run from its last progress (a test or a step beginning or ending), never as a total:
 * `Progress` below, the configuration's reporter, re-arms it at each of them.
 */
export const WAIT_HANG_MS = 600_000
export const PROCESS_HANG_MS = 3_600_000

const here = path.dirname(fileURLToPath(import.meta.url))
export const UI = path.resolve(here, '..')
export const ROOT = path.resolve(UI, '..', '..')
export const SCREENS = path.join(ROOT, 'proof', 'VELDO-0145', 'screens')
export const ROUTE_TABLE = JSON.parse(readFileSync(path.join(UI, 'src', 'api', 'routes.json'), 'utf8')) as {
  routes: Record<string, { method: string; path: string }>
}

export interface Factory {
  origin: string
  domain: string
  control<T = Record<string, unknown>>(route: string, body?: Record<string, unknown>): Promise<T>
  state(): Promise<{ dispatches: Record<string, string>; units: Record<string, string>; requests: Record<string, string> }>
  /** The factory's own clock, in seconds: the time a test writes into a record. A test reads no clock itself. */
  now(): Promise<number>
}

export interface Harness {
  factory: Factory
  child: ChildProcessWithoutNullStreams
  what: string
}

let serial = 0
/** A tag no other call of this worker returns: a harness lives as long as its worker, so an alias made from it is new. */
export function unique(): string {
  serial += 1
  return String(serial).padStart(5, '0')
}

/**
 * Start a factory harness (a script of this directory) and wait for the one thing that says it is up: its ready
 * line, or its exit, whichever comes first. Both are events; the wait hang bound is the only duration, and a
 * harness that reaches it is ended and reported as hung with what it wrote. It serves until its stdin closes.
 */
export async function startHarness(script: string, extra: string[], what: string): Promise<Harness> {
  const args = ['-B', path.join(here, script), ...extra]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const bound = AbortSignal.timeout(WAIT_HANG_MS)
  const decided = new AbortController()
  const signal = AbortSignal.any([bound, decided.signal])
  const lines = createInterface({ input: child.stdout })
  let first: { line: string } | { code: number | null }
  try {
    first = await Promise.race([
      once(lines, 'line', { signal }).then(([line]) => ({ line: String(line) })),
      once(child, 'exit', { signal }).then(([code]) => ({ code: code as number | null })),
    ])
  } catch (error) {
    child.kill('SIGKILL')
    if (!bound.aborted) throw error
    throw new Error(`hung: the ${what} printed no ready line and did not exit in ${WAIT_HANG_MS / 1000} s (the wait hang bound): ${errors}`)
  } finally {
    decided.abort()
  }
  if (!('line' in first)) throw new Error(`the ${what} exited ${first.code} before its ready line: ${errors}`)
  const ready = JSON.parse(first.line) as { origin: string; control: string; domain: string; timers?: unknown }
  // The product timers the harness runs under (VELDO-0358 AC15), for the suite that asked to see them.
  if (process.env.VELDO_E2E_TIMERS) appendFileSync(process.env.VELDO_E2E_TIMERS, JSON.stringify({ harness: script, timers: ready.timers ?? null }) + '\n')
  const control = async <T,>(route: string, body: Record<string, unknown> = {}) => {
    const response = await fetch(ready.control + route, { method: 'POST', body: JSON.stringify(body) })
    const value = (await response.json()) as T & { error?: string }
    if (!response.ok) throw new Error(`control ${route}: ${value.error}`)
    return value as T
  }
  const factory: Factory = {
    origin: ready.origin,
    domain: ready.domain,
    control,
    state: () => control('/state'),
    now: async () => (await control<{ now: number }>('/clock')).now,
  }
  return { factory, child, what }
}

/** Close the harness's input and wait for its exit (an event). One that has not gone at the wait hang bound is
 * ended and reported as hung: a harness left behind is never passed over in silence. */
export async function stopHarness({ child, what }: Harness) {
  if (child.exitCode !== null || child.signalCode !== null) return
  const gone = once(child, 'exit', { signal: AbortSignal.timeout(WAIT_HANG_MS) })
  child.stdin.end()
  try {
    await gone
  } catch {
    child.kill('SIGKILL')
    throw new Error(`hung: the ${what} did not exit in ${WAIT_HANG_MS / 1000} s (the wait hang bound) after its input closed`)
  }
}

/** Start the real factory harness. */
function startFactory(): Promise<Harness> {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  // VELDO_UI_INSTALLED: serve the UI the install laid beside the organs (VELDO_ORGANS/ui), not a build directory.
  const installed = !!process.env.VELDO_UI_INSTALLED
  const page = installed ? path.join(process.env.VELDO_ORGANS ?? '', 'ui') : dist
  if (!existsSync(path.join(page, 'index.html'))) throw new Error(`build the UI first: no ${page}/index.html`)
  return startHarness('harness.py', installed ? ['--installed-ui'] : ['--dist', dist], 'harness')
}

/**
 * THE PAGE SETTLED SIGNAL (VELDO-0358, C10), standing in every page of every test. The page itself counts the
 * requests it has sent whose answers it has not finished reading (its event streams are not requests: they never
 * end), and its panels say their own state (StatePanel: loading, then ready, empty or error). A page is settled
 * when no request is unanswered, no panel is loading and no finite animation or transition is running: what it
 * shows then is what the API said, drawn. A test that must act or read "after the page is done" waits for this,
 * never for an interval.
 */
function countRequests() {
  const w = window as unknown as { __unanswered?: number }
  if (typeof w.__unanswered === 'number') return
  const send = window.fetch.bind(window)
  w.__unanswered = 0
  const answered = () => void (w.__unanswered = (w.__unanswered ?? 1) - 1)
  window.fetch = (...args: Parameters<typeof fetch>) => {
    w.__unanswered = (w.__unanswered ?? 0) + 1
    return send(...args).then(
      (response) => {
        // Answered once its body has arrived: the page reads its own copy at the same moment.
        void response.clone().arrayBuffer().then(answered, answered)
        return response
      },
      (error) => {
        answered()
        throw error
      },
    )
  }
}

export async function settled(page: Page) {
  if (!(await page.evaluate(() => typeof (window as unknown as { __unanswered?: number }).__unanswered === 'number')))
    throw new Error('the page settled signal is not in this page: its context was not made by this test\'s browser fixture')
  await page.waitForFunction(() => {
    const finite = (a: Animation) => Number.isFinite(Number(a.effect?.getComputedTiming().endTime ?? 0))
    return (
      (window as unknown as { __unanswered: number }).__unanswered === 0 &&
      !document.querySelector('.state-loading') &&
      document.getAnimations().every((a) => a.playState !== 'running' || !finite(a))
    )
  })
}

export interface Guard {
  /** Content security policy violations the page reported. */
  violations(): Promise<string[]>
  /** Every request the page made, as method and URL. */
  requests: { method: string; url: string; status: number | null }[]
}

/** Watch a page: its policy violations and every request it makes. */
export async function guard(page: Page): Promise<Guard> {
  const requests: Guard['requests'] = []
  page.on('request', (request) => requests.push({ method: request.method(), url: request.url(), status: null }))
  page.on('response', (response) => {
    const found = [...requests].reverse().find((r) => r.url === response.url() && r.status === null)
    if (found) found.status = response.status()
  })
  await page.addInitScript(() => {
    const seen: string[] = []
    ;(window as unknown as { __violations: string[] }).__violations = seen
    document.addEventListener('securitypolicyviolation', (event) => {
      seen.push(`${event.violatedDirective} ${event.blockedURI} ${event.sourceFile}:${event.lineNumber} ${event.sample}`)
    })
  })
  return {
    requests,
    violations: () => page.evaluate(() => (window as unknown as { __violations?: string[] }).__violations ?? []),
  }
}

/** The published route a request names, or null when it names none. */
export function routeOf(method: string, url: string, domain: string): string | null {
  const { pathname } = new URL(url)
  for (const [name, spec] of Object.entries(ROUTE_TABLE.routes)) {
    if (spec.method === method && spec.path.replace('{domain}', domain) === pathname) return name
  }
  return null
}

/** Give the browser context a virtual platform authenticator (user verification on), empty. */
export async function authenticator(context: BrowserContext, page: Page) {
  const known = authenticators.get(page)
  if (known) return known
  const cdp = await context.newCDPSession(page)
  await cdp.send('WebAuthn.enable')
  const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
    options: {
      protocol: 'ctap2',
      transport: 'internal',
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  })
  authenticators.set(page, { cdp, authenticatorId })
  return { cdp, authenticatorId }
}

const std = (b64url: string) => b64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (b64url.length % 4)) % 4)

const authenticators = new WeakMap<Page, { cdp: import('@playwright/test').CDPSession; authenticatorId: string }>()

/** Sign `principal` in through the sign-in screen with a passkey the host enrolled for them. */
export async function signIn(page: Page, factory: Factory, principal = 'owner') {
  const key = await factory.control<{ credential_id: string; private_key: string; user_handle: string; rp_id: string }>(
    '/passkey',
    { principal },
  )
  const known = authenticators.get(page) ?? (await authenticator(page.context(), page))
  authenticators.set(page, known)
  const { cdp, authenticatorId } = known
  // One passkey on the device at a time, so the browser's choice of passkey is this principal's.
  await cdp.send('WebAuthn.clearCredentials', { authenticatorId })
  await cdp.send('WebAuthn.addCredential', {
    authenticatorId,
    credential: {
      credentialId: std(key.credential_id),
      isResidentCredential: true,
      rpId: key.rp_id,
      privateKey: key.private_key,
      userHandle: std(key.user_handle),
      signCount: 0,
    },
  })
  await page.goto(factory.origin + '/sign-in')
  await page.getByTestId('sign-in').click()
  await expect(page.getByRole('navigation', { name: 'Main' }).first()).toBeVisible()
}

/** Every context a test makes, by the page fixture or by browser.newContext, carries the request count. */
const standing = base.extend<object, { settledPages: void }>({
  settledPages: [
    async ({ browser }, use) => {
      const make = browser.newContext.bind(browser)
      browser.newContext = async (options) => {
        const context = await make(options)
        await context.addInitScript(countRequests)
        return context
      }
      await use()
      browser.newContext = make
    },
    { scope: 'worker', auto: true },
  ],
})

/** The test object of a harness: its factory lives as long as the worker, and its end is waited for. */
export function withHarness<F extends Factory>(start: () => Promise<Harness & { factory: F }>) {
  return standing.extend<object, { factory: F }>({
    factory: [
      async ({}, use) => {
        const harness = await start()
        await use(harness.factory)
        await stopHarness(harness)
      },
      { scope: 'worker' },
    ],
  })
}

type Fixtures = { guarded: Guard }

export const test = withHarness(startFactory).extend<Fixtures>({
  guarded: async ({ page }, use) => {
    await use(await guard(page))
  },
})

export { expect }

interface Timers {
  set(fire: () => void, ms: number): unknown
  clear(timer: unknown): void
}

/**
 * THE RUN'S HANG BOUND, BY PROGRESS (VELDO-0358 AC5; the configuration's reporter). No test has a limit on its
 * total time. The run is ended only when PROCESS_HANG_MS has passed with no progress at all: a test or a step
 * beginning or ending re-arms the bound, so a slow run of many steps is never "hung" and a stuck one is ended
 * where it is stuck. Before it ends the run it says what it last saw and every test and step still in flight,
 * each with its source line. With VELDO_E2E_PROGRESS set it also writes one line per progress, which is what the
 * process that started the run (a suite, as its heavy child) counts its own bound from.
 */
export default class Progress implements Reporter {
  private readonly bound: number
  private readonly timers: Timers
  private readonly end: (report: string) => void
  private readonly lines: boolean
  private timer: unknown = null
  private last = 'nothing yet'
  private readonly flying = new Map<TestCase | TestStep, string>()

  constructor(options: { boundMs?: number; timers?: Timers; end?: (report: string) => void; lines?: boolean } = {}) {
    this.bound = options.boundMs ?? PROCESS_HANG_MS
    this.timers = options.timers ?? {
      set: (fire, ms) => setTimeout(fire, ms).unref(),
      clear: (timer) => clearTimeout(timer as NodeJS.Timeout),
    }
    this.end = options.end ?? ((report) => {
      process.stderr.write(report + '\n')
      // The workers, their browsers and the harness end with this process: each watches its parent.
      process.exit(1)
    })
    this.lines = options.lines ?? !!process.env.VELDO_E2E_PROGRESS
  }

  printsToStdio() {
    return false
  }

  onBegin(_config: FullConfig, _suite: Suite) {
    this.progress('the run began')
  }

  onTestBegin(test: TestCase, _result: TestResult) {
    this.flying.set(test, `test "${test.title}" (${where(test.location)})`)
    this.progress(`began test "${test.title}"`)
  }

  onStepBegin(_test: TestCase, _result: TestResult, step: TestStep) {
    this.flying.set(step, `step "${step.title}" (${where(step.location)})`)
    this.progress(`began step "${step.title}"`)
  }

  onStepEnd(_test: TestCase, _result: TestResult, step: TestStep) {
    this.flying.delete(step)
    this.progress(`ended step "${step.title}" (${where(step.location)})`)
  }

  onTestEnd(test: TestCase, result: TestResult) {
    this.flying.delete(test)
    this.progress(`ended test "${test.title}" ${result.status}`)
  }

  onEnd() {
    this.timers.clear(this.timer)
    this.timer = null
  }

  private progress(what: string) {
    this.last = what
    if (this.lines) process.stderr.write(`e2e progress: ${what.replace(/\s+/g, ' ').slice(0, 200)}\n`)
    this.timers.clear(this.timer)
    this.timer = this.timers.set(() => this.hung(), this.bound)
  }

  private hung() {
    this.end(
      `E2E HUNG: no test or step began or ended for ${this.bound / 1000} s (the process hang bound, counted from the ` +
        `last progress, never from the run's start). Last progress: ${this.last}. In flight: ${[...this.flying.values()].join('; ') || 'nothing'}.`,
    )
  }
}

function where(location?: { file: string; line: number }) {
  return location ? `${path.basename(location.file)}:${location.line}` : 'no source line'
}
