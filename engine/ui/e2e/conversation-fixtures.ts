import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base, type Browser, type Page } from '@playwright/test'
import { expect, signIn, type Factory } from './fixtures'

export { expect, guard, routeOf, signIn, type Factory } from './fixtures'

/** VELDO-0179's browser tests run against e2e/conversation_harness.py: VELDO-0131's factory harness with the real
 * conversation authority on, a fake engine running every turn and a fake Telegram edge. */
const here = path.dirname(fileURLToPath(import.meta.url))
const UI = path.resolve(here, '..')

export interface RecordLine {
  seq: number
  at: number
  stream: string
  redacted: string[]
  payload: string
}

export interface ConversationFactory extends Factory {
  replies(replies: string[]): Promise<void>
  hold(conversation: string, on: boolean): Promise<void>
  pause(on: boolean): Promise<void>
  pace(seconds: number): Promise<void>
  telegram(conversation: string, text: string): Promise<Record<string, any>>
  roleElsewhere(conversation: string, role: string): Promise<Record<string, any>>
  stored(conversation: string): Promise<{ conversation: Record<string, any>; turns: Record<string, any>[] }>
  record(conversation: string, sequence: number): Promise<{ lines: RecordLine[]; total: number; committed: { lines: number; digest: string } | null; dispatch: string | null }>
}

async function start() {
  const dist = process.env.VELDO_UI_DIST ?? path.join(UI, 'dist')
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error(`build the UI first: no ${dist}/index.html`)
  const args = ['-B', path.join(here, 'conversation_harness.py'), '--dist', dist]
  if (process.env.VELDO_ORGANS) args.push('--organs', process.env.VELDO_ORGANS)
  const child = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] })
  let errors = ''
  child.stderr.on('data', (chunk) => (errors += String(chunk)))
  const ready = await new Promise<{ origin: string; control: string; domain: string }>((resolve, reject) => {
    let out = ''
    const timer = setTimeout(() => reject(new Error(`conversation harness did not start: ${errors}`)), 120_000)
    child.stdout.on('data', (chunk) => {
      out += String(chunk)
      const line = out.split('\n')[0]
      if (out.includes('\n') && line) {
        clearTimeout(timer)
        resolve(JSON.parse(line))
      }
    })
    child.on('exit', (code) => reject(new Error(`conversation harness exited ${code}: ${errors}`)))
  })
  const control = async <T,>(route: string, body: Record<string, unknown> = {}) => {
    const response = await fetch(ready.control + route, { method: 'POST', body: JSON.stringify(body) })
    const value = (await response.json()) as T & { error?: string }
    if (!response.ok) throw new Error(`control ${route}: ${value.error}`)
    return value as T
  }
  const factory: ConversationFactory = {
    origin: ready.origin,
    domain: ready.domain,
    control,
    state: () => control('/state'),
    replies: async (replies) => void (await control('/conversation/replies', { replies })),
    hold: async (conversation, on) => void (await control('/conversation/hold', { conversation, on })),
    pause: async (on) => void (await control('/conversation/pause', { on })),
    pace: async (seconds) => void (await control('/conversation/pace', { seconds })),
    telegram: (conversation, text) => control('/conversation/telegram', { conversation, text }),
    roleElsewhere: (conversation, role) => control('/conversation/role', { conversation, role }),
    stored: (conversation) => control('/conversation/read', { conversation }),
    record: (conversation, sequence) => control('/conversation/record', { conversation, sequence }),
  }
  return { factory, child }
}

export const test = base.extend<object, { factory: ConversationFactory }>({
  factory: [
    async ({}, use) => {
      const { factory, child } = await start()
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
})

export const isPhone = (page: Page) => (page.viewportSize()?.width ?? 1280) < 768

export async function pageAs(browser: Browser, factory: Factory, who: string, viewport: { width: number; height: number }) {
  const phone = viewport.width < 768
  const context = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone })
  const page = await context.newPage()
  await signIn(page, factory, who)
  return page
}

/** The conversation id of the screen the page shows. */
export function conversationOf(page: Page): string {
  const match = /\/conversations\/([^/?#]+)/.exec(new URL(page.url()).pathname)
  if (!match) throw new Error(`not a conversation screen: ${page.url()}`)
  return decodeURIComponent(match[1]!)
}

/** Open a new conversation from the list screen with New conversation; returns its id. */
export async function newConversation(page: Page, factory: Factory): Promise<string> {
  await page.goto(factory.origin + '/conversations')
  await page.getByTestId('conversation-new').click()
  await expect(page.getByTestId('conversation-screen')).toBeVisible()
  await expect(page.getByTestId('conversation-state')).toHaveText('Open')
  return conversationOf(page)
}

/** Send a message from the conversation screen's message box. */
export async function send(page: Page, text: string) {
  await page.getByTestId('message-text').fill(text)
  await page.getByTestId('message-send').click()
  await expect(page.getByTestId('message-text')).toHaveValue('')
}
