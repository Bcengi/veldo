import { createHash } from 'node:crypto'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import type { Page, Request } from '@playwright/test'
import { ROOT, expect, routeOf, signIn, test, type Factory } from './fixtures'

/**
 * VELDO-0159: the owner defines an MCP server in the UI, each save a new catalog revision through the API's catalog
 * route (AC1), and sets its credential through a write-only field (AC2). Each test title carries the suite row it
 * proves in brackets; scripts/suites/118_veldo_0159_mcp_credential_form.py reads them from the JSON report.
 * Screens are written to proof/VELDO-0159/screens only when VELDO_0159_SCREENS is set.
 */

const PHONE = { width: 360, height: 780 }
const DESKTOP = { width: 1280, height: 900 }
const sha = (text: string) => createHash('sha256').update(text).digest('hex')

interface McpState {
  servers: Record<string, Record<string, Record<string, unknown>>>
  heads: Record<string, number>
  credentials: Record<string, { id: string; label: string; set_at: number; set_by: string; reference: string; deleted?: boolean; version: number }>
  keystore: Record<string, string>
}
const mcp = (factory: Factory) => factory.control<McpState>('/mcp/state')

async function screen(page: Page, name: string) {
  if (!process.env.VELDO_0159_SCREENS) return
  const dir = path.join(ROOT, 'proof', 'VELDO-0159', 'screens')
  mkdirSync(dir, { recursive: true })
  await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: true })
}

/** Every request the page makes, with its body, and every response body, for the no-value-kept row. */
function wiretap(page: Page) {
  const sent: { method: string; url: string; body: string; route: string | null }[] = []
  const answers: string[] = []
  page.on('request', (r: Request) => sent.push({ method: r.method(), url: r.url(), body: r.postData() ?? '', route: null }))
  page.on('response', async (r) => {
    try {
      answers.push(`${r.url()} ${await r.text()}`)
    } catch {
      answers.push(r.url())
    }
  })
  return { sent, answers }
}

async function credential(page: Page, id: string) {
  const box = page.locator(`[data-testid="credential"][data-credential="${id}"]`)
  if (!(await box.count())) {
    await page.getByTestId('credential-new').fill(id)
    await page.getByTestId('credential-add').click()
  }
  await expect(box).toBeVisible()
  return box
}

async function setValue(page: Page, id: string, label: string, value: string, action: 'Set value' | 'Replace value') {
  const box = await credential(page, id)
  await box.getByTestId('credential-label-input').fill(label)
  await box.getByTestId('credential-value').fill(value)
  const button = box.getByTestId('credential-set')
  await expect(button).toHaveText(action)
  await button.click()
  await expect(box.getByTestId('credential-label')).toHaveText(label)
  await expect(box.getByTestId('credential-set')).toHaveText('Replace value')
  return box
}

interface Server {
  id: string
  label: string
  transport: 'stdio' | 'http'
  command: string | null
  arguments: string[]
  url: string | null
  environment: Record<string, { literal: string } | { reference: string }>
  headers: Record<string, { reference: string }>
  hosts: string[]
  read_only_tools: string[]
}

/** Fill the form with `server`; a reference is picked from the credential select by the credential's id. */
async function fill(page: Page, server: Server, credentialIds: Record<string, string>) {
  const id = page.getByTestId('server-id')
  if (await id.isEnabled()) await id.fill(server.id)
  await page.getByTestId('server-label').fill(server.label)
  await page.getByTestId('server-transport').selectOption(server.transport)
  if (server.transport === 'stdio') {
    await page.getByTestId('server-command').fill(server.command ?? '')
    await page.getByTestId('server-arguments').fill(server.arguments.join('\n'))
  } else {
    await page.getByTestId('server-url').fill(server.url ?? '')
  }
  await page.getByTestId('server-hosts').fill(server.hosts.join('\n'))
  await page.getByTestId('server-tools').fill(server.read_only_tools.join('\n'))
  const rows = async (testid: string, add: string, entries: [string, { literal: string } | { reference: string }][], header: boolean) => {
    while ((await page.getByTestId(testid).count()) < entries.length) await page.getByTestId(add).click()
    for (const [i, [name, binding]] of entries.entries()) {
      const row = page.getByTestId(testid).nth(i)
      await row.getByTestId('binding-name').fill(name)
      if (!header) await row.getByTestId('binding-kind').selectOption('literal' in binding ? 'literal' : 'reference')
      if ('literal' in binding) await row.getByTestId('binding-value').fill(binding.literal)
      else {
        const select = row.getByTestId('binding-reference')
        const option = select.locator('option', { hasText: `${credentialIds[binding.reference]} (` })
        await select.selectOption({ label: (await option.textContent()) ?? '' })
      }
    }
  }
  await rows('environment-row', 'environment-add', Object.entries(server.environment), false)
  if (server.transport === 'http') await rows('header-row', 'header-add', Object.entries(server.headers), true)
}

/** The definition with each `ref:<credential id>` placeholder replaced by the reference the route answered. */
function resolve(server: Server, references: Record<string, string>): Server {
  const map = <T extends { literal: string } | { reference: string }>(values: Record<string, T>) =>
    Object.fromEntries(Object.entries(values).map(([k, v]) => [k, 'reference' in v ? { reference: references[v.reference]! } : v])) as Record<string, { literal: string } | { reference: string }>
  return { ...server, environment: map(server.environment), headers: map(server.headers) as Server['headers'] }
}

async function save(page: Page, revision: number) {
  await page.getByTestId('server-save').click()
  await expect(page.getByTestId('server-saved')).toHaveText(`Saved as revision ${revision}`)
  await expect(page.getByTestId('server-form')).toHaveAttribute('data-edited-from', String(revision))
}

/** A primary action is not clipped: inside the viewport's width, and the topmost element at its center. */
async function unclipped(page: Page, testid: string, width: number) {
  const target = page.getByTestId(testid).first()
  await target.scrollIntoViewIfNeeded()
  const box = await target.boundingBox()
  expect(box, `${testid} has a box`).not.toBeNull()
  expect(box!.x, `${testid} starts inside the viewport`).toBeGreaterThanOrEqual(0)
  expect(box!.x + box!.width, `${testid} ends inside the viewport`).toBeLessThanOrEqual(width + 0.5)
  expect(box!.height, `${testid} is a 44px touch target`).toBeGreaterThanOrEqual(44)
  const topmost = await target.evaluate((el) => {
    const r = el.getBoundingClientRect()
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
    return !!hit && (hit === el || el.contains(hit))
  })
  expect(topmost, `${testid} is not covered`).toBe(true)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow, 'no page-wide horizontal overflow').toBeLessThanOrEqual(0)
}

async function define(page: Page, factory: Factory, suffix: string, viewport: { width: number; height: number }) {
  await page.setViewportSize(viewport)
  const sent = wiretap(page).sent
  await signIn(page, factory)
  await page.goto(factory.origin + '/servers')
  await expect(page.getByTestId('server-form')).toBeVisible()
  const github = `github-token${suffix}`
  const atlassianToken = `atlassian-token${suffix}`
  await setValue(page, github, 'GitHub read token', `ghp_e2e${suffix}value000000000000000000000`, 'Set value')
  await setValue(page, atlassianToken, 'Atlassian API token', `Basic ZTJlLWF0bGFzc2lhbg${suffix}`, 'Set value')
  const state = await mcp(factory)
  const references = { [github]: state.credentials[github]!.reference, [atlassianToken]: state.credentials[atlassianToken]!.reference }
  const ids = { [github]: github, [atlassianToken]: atlassianToken }
  const stdio: Server = {
    id: `filesystem${suffix}`,
    label: 'Project files',
    transport: 'stdio',
    command: 'npx',
    arguments: ['-y', '@modelcontextprotocol/server-filesystem', '/srv/projects'],
    url: null,
    environment: { LOG_LEVEL: { literal: 'info' }, GITHUB_TOKEN: { reference: github } },
    headers: {},
    hosts: ['veldo-linux-1'],
    read_only_tools: ['read_file', 'list_directory'],
  }
  const http: Server = {
    id: `atlassian${suffix}`,
    label: 'Atlassian',
    transport: 'http',
    command: null,
    arguments: [],
    url: 'https://mcp.atlassian.com/v1/sse',
    environment: {},
    headers: { Authorization: { reference: atlassianToken } },
    hosts: ['veldo-linux-1', 'veldo-mac-1'],
    read_only_tools: ['getJiraIssue', 'searchJiraIssuesUsingJql'],
  }
  // Both servers are entered in one visit (the credentials written above are this page's memory), then each is
  // reopened from the catalog route, edited and saved again.
  for (const [i, server] of [stdio, http].entries()) {
    if (i > 0) await page.getByRole('link', { name: 'New server' }).click()
    await expect(page.getByTestId('server-form')).toHaveAttribute('data-edited-from', '0')
    await fill(page, server, ids)
    await save(page, 1)
    await expect(page).toHaveURL(new RegExp(`/servers/${server.id}$`))
    await screen(page, `define-${server.transport}-${viewport.width}`)
  }
  for (const server of [stdio, http]) {
    const edited: Server = { ...server, label: `${server.label} (edited)`, read_only_tools: [...server.read_only_tools, 'whoami'] }
    await page.goto(`${factory.origin}/servers/${server.id}`)
    // The reopened form reads the revision through the catalog route; the edit changes the label and adds a tool.
    await expect(page.getByTestId('server-form')).toHaveAttribute('data-edited-from', '1')
    await expect(page.getByTestId('server-label')).toHaveValue(server.label)
    await expect(page.getByTestId('server-tools')).toHaveValue(server.read_only_tools.join('\n'))
    await page.getByTestId('server-label').fill(edited.label)
    await page.getByTestId('server-tools').fill(edited.read_only_tools.join('\n'))
    await save(page, 2)
    const stored = await mcp(factory)
    expect(stored.heads[server.id]).toBe(2)
    expect(stored.servers[server.id]!['1']).toEqual({ ...resolve(server, references), revision: 1 })
    expect(stored.servers[server.id]!['2']).toEqual({ ...resolve(edited, references), revision: 2 })
  }
  // Every field the form sent is what the catalog route stored, and every save went to that route.
  const saves = sent.filter((r) => routeOf(r.method, r.url, factory.domain) === 'mcp.save')
  expect(saves).toHaveLength(4)
  const stored = await mcp(factory)
  const bodies = saves.map((r) => JSON.parse(r.body) as { definition: Server; base: number })
  expect(bodies.map((b) => [b.definition.id, b.base])).toEqual([[stdio.id, 0], [http.id, 0], [stdio.id, 1], [http.id, 1]])
  for (const [i, b] of bodies.entries()) {
    const { revision, ...fields } = stored.servers[b.definition.id]![String(b.base + 1)] as Record<string, unknown>
    expect(revision).toBe(b.base + 1)
    expect(fields, `save ${i} sent exactly what was stored`).toEqual(b.definition)
  }
  for (const r of sent) {
    if (new URL(r.url).pathname.startsWith('/api/')) expect(routeOf(r.method, r.url, factory.domain), `${r.method} ${r.url}`).not.toBeNull()
  }
}

test.describe('MCP server form (VELDO-0159)', () => {
  test('[mcp/define-desktop] at 1280px the owner defines a stdio server and the Atlassian http server; each save and edit is a new catalog revision holding every field the form sent', async ({ page, factory }) => {
    await define(page, factory, '', DESKTOP)
  })

  test('[mcp/define-phone] at 360px the owner defines a stdio server and an http server; each save and edit is a new catalog revision holding every field the form sent', async ({ page, factory }) => {
    await define(page, factory, '-phone', PHONE)
  })

  test('[mcp/stale-save] a save edited from an older revision shows the stale refusal beside the save action and stores nothing', async ({ page, factory }) => {
    await page.setViewportSize(DESKTOP)
    const sent = wiretap(page).sent
    await signIn(page, factory)
    await page.goto(factory.origin + '/servers')
    const server: Server = {
      id: 'stale-check', label: 'Stale check', transport: 'stdio', command: 'mcp-stale', arguments: [], url: null,
      environment: { MODE: { literal: 'one' } }, headers: {}, hosts: ['veldo-linux-1'], read_only_tools: [],
    }
    await fill(page, server, {})
    await save(page, 1)
    // Another session saves revision 2 while this form still shows revision 1.
    const other = await factory.control<{ status: number; answer: { revision?: number } }>('/mcp/save', {
      definition: { ...server, label: 'Saved elsewhere' }, base: 1,
    })
    expect(other.status, JSON.stringify(other.answer)).toBe(200)
    expect(other.answer.revision).toBe(2)
    await page.getByTestId('server-label').fill('Edited from revision 1')
    await page.getByTestId('server-save').click()
    const refusal = page.locator('.server-save [data-testid="refusal"]')
    // The store refuses the save's expected head version by name before the catalog transition runs.
    await expect(refusal).toHaveAttribute('data-refusal', /^stale_version(:|$)/)
    await expect(refusal).toHaveAttribute('data-action', 'save')
    await expect(page.getByTestId('server-saved')).toHaveCount(0)
    const last = sent.filter((r) => routeOf(r.method, r.url, factory.domain) === 'mcp.save').at(-1)!
    expect(JSON.parse(last.body).base, 'the refused save carried the revision it was edited from').toBe(1)
    const stored = await mcp(factory)
    expect(stored.heads[server.id], 'nothing was stored').toBe(2)
    expect(Object.keys(stored.servers[server.id]!).sort()).toEqual(['1', '2'])
    expect(stored.servers[server.id]!['2']!.label).toBe('Saved elsewhere')
    await screen(page, 'stale-save-1280')
    // Loading the current revision edits from it.
    await page.getByTestId('server-reload').click()
    await expect(page.getByTestId('server-form')).toHaveAttribute('data-edited-from', '2')
    await expect(page.getByTestId('server-label')).toHaveValue('Saved elsewhere')
  })

  test('[mcp/phone-actions] at 360px no primary action of the server form or the credential field is clipped', async ({ page, factory }) => {
    await page.setViewportSize(PHONE)
    await signIn(page, factory)
    await page.goto(factory.origin + '/you')
    await page.getByTestId('you-servers').click()
    await expect(page.getByTestId('server-form')).toBeVisible()
    await page.getByTestId('server-transport').selectOption('http')
    await page.getByTestId('header-add').click()
    await page.getByTestId('environment-add').click()
    await credential(page, 'phone-layout')
    for (const testid of ['server-save', 'credential-set', 'credential-add', 'header-add', 'environment-add', 'server-open-go']) {
      await unclipped(page, testid, PHONE.width)
    }
    await setValue(page, 'phone-layout', 'Phone layout', 'phone-layout-value-1', 'Set value')
    for (const testid of ['credential-set', 'credential-delete']) await unclipped(page, testid, PHONE.width)
    await screen(page, 'form-360')
  })

  test('[cred/metadata-only] the Atlassian credential is set, replaced and deleted through the field; after each the form shows only its label, set at and set by', async ({ page, factory }) => {
    await page.setViewportSize(DESKTOP)
    await signIn(page, factory)
    await page.goto(factory.origin + '/servers')
    const id = 'atlassian-api'
    const check = async (label: string, value: string | null, outcome: 'set' | 'deleted') => {
      const box = page.locator(`[data-testid="credential"][data-credential="${id}"]`)
      const stored = (await mcp(factory)).credentials[id]!
      const meta = box.getByTestId('credential-meta')
      await expect(meta.locator('dt')).toHaveText(outcome === 'deleted' ? ['Label', 'Deleted at', 'Deleted by'] : ['Label', 'Set at', 'Set by'])
      await expect(box.getByTestId('credential-label')).toHaveText(stored.label)
      await expect(box.getByTestId('credential-set-by')).toHaveText(stored.set_by)
      // Set at is the stored record's set at, exactly: never the browser's clock, which on a phone may be off.
      const shown = box.getByTestId('credential-set-at')
      expect(Number(await shown.getAttribute('data-set-at')), 'set at is the stored record\'s set at').toBe(stored.set_at)
      const recordText = await page.evaluate((at) => new Date(at * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' }), stored.set_at)
      await expect(shown, 'the shown set at is the stored record\'s set at').toHaveText(recordText)
      expect(stored.label).toBe(label)
      expect(stored.set_by).toBe('owner')
      const name = stored.reference.split(':')[1]!
      if (value === null) expect(stored.deleted).toBe(true)
      expect((await mcp(factory)).keystore[name], 'the keystore holds the value written').toBe(value === null ? undefined : sha(value))
      // Only the label, set at and set by: no value and no other field of the record is on the page.
      const text = await box.innerText()
      for (const hidden of [stored.reference, name]) expect(text).not.toContain(hidden)
      await expect(box.getByTestId('credential-value')).toHaveValue('')
    }
    await setValue(page, id, 'Atlassian API token', 'atlassian-first-value-7d1f', 'Set value')
    await check('Atlassian API token', 'atlassian-first-value-7d1f', 'set')
    await screen(page, 'credential-set-1280')
    await setValue(page, id, 'Atlassian API token (rotated)', 'atlassian-second-value-9c2e', 'Replace value')
    await check('Atlassian API token (rotated)', 'atlassian-second-value-9c2e', 'set')
    const box = page.locator(`[data-testid="credential"][data-credential="${id}"]`)
    await box.getByTestId('credential-delete').click()
    await expect(box.getByTestId('credential-set')).toHaveText('Set value')
    await check('Atlassian API token (rotated)', null, 'deleted')
    await screen(page, 'credential-deleted-1280')
  })

  test('[cred/no-value-kept] a typed value appears only in the body of the one request to the credential route, and nowhere after it is sent; reopening shows an empty field', async ({ page, factory }) => {
    await page.setViewportSize(DESKTOP)
    const { sent, answers } = wiretap(page)
    const urls: string[] = []
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) urls.push(frame.url())
    })
    await signIn(page, factory)
    await page.goto(factory.origin + '/servers')
    const id = 'kept-check'
    const cdp = await page.context().newCDPSession(page)

    /** Everywhere a value could stay in the browser after it was sent. */
    const nowhere = async (value: string) => {
      const found = await page.evaluate(async (needle) => {
        const where: string[] = []
        const has = (text: string | null | undefined) => typeof text === 'string' && text.includes(needle)
        if (has(document.documentElement.outerHTML)) where.push('rendered page')
        for (const el of Array.from(document.querySelectorAll('input, textarea, select'))) {
          if (has((el as HTMLInputElement).value)) where.push(`field ${el.id}`)
        }
        for (const store of [localStorage, sessionStorage]) {
          for (let i = 0; i < store.length; i++) {
            const key = store.key(i)!
            if (has(key) || has(store.getItem(key))) where.push(store === localStorage ? 'local storage' : 'session storage')
          }
        }
        if (has(location.href)) where.push('URL')
        if (has(JSON.stringify(history.state))) where.push('history state')
        const dbs = (await indexedDB.databases?.()) ?? []
        for (const info of dbs) {
          const db = await new Promise<IDBDatabase>((ok, fail) => {
            const open = indexedDB.open(info.name!)
            open.onsuccess = () => ok(open.result)
            open.onerror = () => fail(open.error)
          })
          for (const name of Array.from(db.objectStoreNames)) {
            const all = await new Promise<unknown[]>((ok) => {
              const req = db.transaction(name).objectStore(name).getAll()
              req.onsuccess = () => ok(req.result)
            })
            if (has(JSON.stringify(all))) where.push(`IndexedDB ${info.name}/${name}`)
          }
          db.close()
        }
        return where
      }, value)
      const tree = await cdp.send('Accessibility.getFullAXTree')
      if (JSON.stringify(tree).includes(value)) found.push('accessibility tree')
      if ((await page.locator('body').ariaSnapshot()).includes(value)) found.push('aria snapshot')
      for (const url of urls) if (url.includes(value)) found.push(`history entry ${url}`)
      return found
    }

    const once = async (value: string, before: number) => {
      const carrying = sent.slice(before).filter((r) => r.url.includes(value) || r.body.includes(value))
      expect(carrying.map((r) => routeOf(r.method, r.url, factory.domain)), 'only the one credential route request carries it').toEqual(['mcp.credential_set'])
      expect(carrying[0]!.url, 'never in a URL').not.toContain(value)
      expect(JSON.parse(carrying[0]!.body).value).toBe(value)
      for (const answer of answers) expect(answer, 'no answer echoes it').not.toContain(value)
      expect(await nowhere(value), 'kept nowhere after it is sent').toEqual([])
    }

    const first = 'kept-check-value-4b8a-first'
    let before = sent.length
    await setValue(page, id, 'Kept check', first, 'Set value')
    await once(first, before)

    const second = 'kept-check-value-6e3c-second'
    before = sent.length
    await setValue(page, id, 'Kept check', second, 'Replace value')
    await once(second, before)

    // Reopening the form shows an empty field; nothing typed is kept for it.
    await page.getByRole('link', { name: 'You', exact: true }).first().click()
    await expect(page.getByTestId('you-servers')).toBeVisible()
    await page.getByTestId('you-servers').click()
    const reopened = page.locator(`[data-testid="credential"][data-credential="${id}"]`)
    await expect(reopened.getByTestId('credential-value')).toHaveValue('')
    await expect(reopened.getByTestId('credential-label')).toHaveText('Kept check')
    expect(await nowhere(first)).toEqual([])
    expect(await nowhere(second)).toEqual([])

    before = sent.length
    await reopened.getByTestId('credential-delete').click()
    await expect(reopened.getByTestId('credential-set')).toHaveText('Set value')
    expect(sent.slice(before).filter((r) => r.body.includes(first) || r.body.includes(second))).toEqual([])
    expect(await nowhere(second)).toEqual([])
    expect(sent.filter((r) => r.body.includes(first) || r.url.includes(first))).toHaveLength(1)
    expect(sent.filter((r) => r.body.includes(second) || r.url.includes(second))).toHaveLength(1)
  })
})
