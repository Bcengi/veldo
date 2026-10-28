import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base, expect, type BrowserContext, type Page } from '@playwright/test'

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
}

/** Start the real factory harness; it serves until its stdin closes. */
async function startFactory(): Promise<{ factory: Factory; child: ChildProcessWithoutNullStreams }> {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error(`build the UI first: no ${dist}/index.html`)
  const args = ['-B', path.join(here, 'harness.py'), '--dist', dist]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const ready = await new Promise<{ origin: string; control: string; domain: string }>((resolve, reject) => {
    let out = ''
    const timer = setTimeout(() => reject(new Error(`harness did not start: ${errors}`)), 60_000)
    child.stdout.on('data', (chunk) => {
      out += String(chunk)
      const line = out.split('\n')[0]
      if (out.includes('\n') && line) {
        clearTimeout(timer)
        resolve(JSON.parse(line))
      }
    })
    child.on('exit', (code) => reject(new Error(`harness exited ${code}: ${errors}`)))
  })
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
  }
  return { factory, child }
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

type Fixtures = { guarded: Guard }
type WorkerFixtures = { factory: Factory }

export const test = base.extend<Fixtures, WorkerFixtures>({
  factory: [
    async ({}, use) => {
      const { factory, child } = await startFactory()
      await use(factory)
      child.stdin.end()
      await new Promise((resolve) => {
        const timer = setTimeout(() => {
          child.kill('SIGTERM')
          resolve(null)
        }, 10_000)
        child.on('exit', () => {
          clearTimeout(timer)
          resolve(null)
        })
      })
    },
    { scope: 'worker' },
  ],
  guarded: async ({ page }, use) => {
    await use(await guard(page))
  },
})

export { expect }
