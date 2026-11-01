import type { Browser, Page } from '@playwright/test'
import { expect, signIn, test, type TeamFactory } from './team-fixtures'

/**
 * VELDO-0163: the owner writes a role's capability configuration (AC1) and a project's team roles and the
 * default team (AC2) in the VELDO-0145 shell, in a passkey session, at a 360px phone width and a 1280px
 * desktop width, through VELDO-0162's routes on a real factory (e2e/team_harness.py). Each test title starts
 * with the row name the suite (scripts/suites/119_veldo_0163_role_team_form.py) reports.
 */
test.describe.configure({ mode: 'serial' })

const PHONE = { width: 360, height: 640 }
const DESKTOP = { width: 1280, height: 860 }

type Sent = { route: string; body: Record<string, unknown>; answer: Record<string, unknown> | null }

/** A signed-in page at `viewport` that records every save it sends and the API's answer to it. */
async function open(browser: Browser, factory: TeamFactory, viewport: { width: number; height: number }, who = 'owner') {
  const phone = viewport.width < 768
  const context = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone })
  const page = await context.newPage()
  await signIn(page, factory, who)
  return { context, page, sent: watch(page) }
}

function watch(page: Page) {
  const sent: Sent[] = []
  page.on('response', async (response) => {
    const request = response.request()
    const found = /\/(configurations\/save|teams\/save|teams\/default\/save)$/.exec(new URL(request.url()).pathname)
    if (request.method() !== 'POST' || !found) return
    let answer: Record<string, unknown> | null = null
    try {
      answer = (await response.json()) as Record<string, unknown>
    } catch {
      answer = null
    }
    sent.push({ route: found[1]!, body: request.postDataJSON() as Record<string, unknown>, answer })
  })
  return sent
}

/** The action is on screen, inside the viewport, not covered by anything, and a 44px target on a phone. */
async function unclipped(page: Page, testid: string, phone: boolean) {
  const action = page.getByTestId(testid).first()
  await action.scrollIntoViewIfNeeded()
  await expect(action).toBeInViewport({ ratio: 1 })
  const box = (await action.boundingBox())!
  const width = page.viewportSize()!.width
  expect(box.x, `${testid} left edge`).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width, `${testid} right edge`).toBeLessThanOrEqual(width)
  if (phone) expect(Math.min(box.width, box.height), `${testid} target`).toBeGreaterThanOrEqual(44)
  const hit = await page.evaluate(
    ({ x, y, testid }) => document.elementFromPoint(x, y)?.closest(`[data-testid="${testid}"]`) !== null,
    { x: box.x + box.width / 2, y: box.y + box.height / 2, testid },
  )
  expect(hit, `${testid} is covered`).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), 'page-wide overflow').toBe(0)
}

async function openRole(page: Page, factory: TeamFactory, role: string) {
  await page.goto(factory.origin + '/roles')
  await page.getByTestId('role-name').fill(role)
  await page.getByTestId('role-open').click()
  await expect(page.getByTestId('role-form')).toBeVisible()
}

async function openTeam(page: Page, factory: TeamFactory, project: string) {
  await page.goto(factory.origin + '/teams')
  if (project === 'default') await page.getByTestId('team-open-default').click()
  else {
    await page.getByTestId('team-project').fill(project)
    await page.getByTestId('team-open').click()
  }
  await expect(page.getByTestId('team-current')).toBeVisible()
}

/** The value field of the engine setting named `key`, wherever the stored order put it. */
async function setting(page: Page, key: string) {
  const keys = await page.locator('[id^="setting-key-"]').evaluateAll((els) => els.map((e) => (e as HTMLInputElement).value))
  expect(keys).toContain(key)
  return page.locator(`#setting-value-${keys.indexOf(key)}`)
}

const stripped = (stored: Record<string, unknown> | null) => {
  if (!stored) return null
  const { revision: _r, digest: _d, previous: _p, assertion_digest: _a, ...rest } = stored
  return rest
}

test('role/revisions: a role with every field and load mode is saved, edited and saved again as new revisions', async ({ browser, factory }) => {
  const { context, page, sent } = await open(browser, factory, DESKTOP)
  await openRole(page, factory, 'builder_jira')
  await expect(page.getByTestId('role-base')).toHaveAttribute('data-base', '0')
  await page.locator('label[for="engine-claude_code"]').click()
  await page.getByTestId('add-native-tool').click()
  await page.locator('#tool-name-0').fill('Read')
  await page.locator('#tool-load-0').selectOption('always')
  await page.getByTestId('add-native-tool').click()
  await page.locator('#tool-name-1').fill('Edit')
  await page.locator('#tool-load-1').selectOption('when assigned')
  // The MCP selection is chosen from the catalog read (VELDO-0144): the Atlassian server with all its tools.
  await page.getByTestId('catalog-server').fill('atlassian')
  await page.getByTestId('catalog-read').click()
  await expect(page.getByTestId('catalog-entry')).toContainText('Atlassian (atlassian), revision 1')
  await expect(page.getByTestId('catalog-entry')).toContainText('jira_get_issue')
  await expect(page.getByTestId('catalog-all')).toBeChecked()
  await page.getByTestId('catalog-load').selectOption('always')
  await page.getByTestId('catalog-add').click()
  await expect(page.getByTestId('mcp-atlassian')).toContainText('atlassian revision 1')
  await page.getByTestId('add-skill').click()
  await page.locator('#skill-name-0').fill('coding')
  await page.locator('#skill-load-0').selectOption('when assigned')
  await page.getByTestId('add-instruction').click()
  await page.locator('#instruction-source-0').selectOption('project')
  await page.locator('#instruction-path-0').fill('README.md')
  await page.locator('#instruction-load-0').selectOption('always')
  await page.getByTestId('add-instruction').click()
  await page.locator('#instruction-source-1').selectOption('factory')
  await page.locator('#instruction-path-1').fill('instructions/build.md')
  await page.locator('#instruction-load-1').selectOption('when assigned')
  await page.getByTestId('add-setting').click()
  await page.locator('#setting-key-0').fill('model')
  await page.locator('#setting-value-0').fill('sonnet')
  await page.getByTestId('role-save').click()
  await expect(page.getByTestId('role-saved')).toHaveAttribute('data-revision', '1')
  await expect(page.getByTestId('role-base')).toHaveAttribute('data-base', '1')

  // Edit and save again: a list of the server's tools in place of all of them, a load mode and a setting.
  await page.locator('#mcp-all-0').uncheck()
  await page.locator('#mcp-tools-0').fill('jira_get_issue, jira_search')
  await page.locator('#mcp-tools-0').press('Tab')
  await page.locator('#tool-load-1').selectOption('always')
  await page.getByTestId('add-setting').click()
  await page.locator('#setting-key-1').fill('effort')
  await page.locator('#setting-value-1').fill('high')
  await page.getByTestId('role-save').click()
  await expect(page.getByTestId('role-saved')).toHaveAttribute('data-revision', '2')
  await expect(page.getByTestId('role-base')).toHaveAttribute('data-base', '2')

  const saves = sent.filter((s) => s.route === 'configurations/save')
  expect(saves.map((s) => s.body.base)).toEqual([0, 1])
  expect(saves[0]!.body.definition).toEqual({
    role: 'builder_jira',
    engine: 'claude_code',
    native_tools: [
      { name: 'Read', load: 'always' },
      { name: 'Edit', load: 'when assigned' },
    ],
    mcp: [{ server: 'atlassian', revision: 1, tools: 'all', load: 'always' }],
    skills: [{ skill: 'coding', revision: 1, load: 'when assigned' }],
    instructions: [
      { source: 'project', path: 'README.md', load: 'always' },
      { source: 'factory', path: 'instructions/build.md', load: 'when assigned' },
    ],
    settings: { model: 'sonnet' },
  })
  expect((saves[1]!.body.definition as { mcp: unknown }).mcp).toEqual([
    { server: 'atlassian', revision: 1, tools: ['jira_get_issue', 'jira_search'], load: 'always' },
  ])
  // Every field the form sent is the revision the configuration route stored.
  for (const [n, save] of saves.entries()) {
    const stored = await factory.configuration('builder_jira', n + 1)
    expect(stored?.revision).toBe(n + 1)
    expect(stripped(stored)).toEqual(save.body.definition)
  }
  await context.close()
})

test('role/stale-save: a save edited from an older revision is refused beside the save action and stores nothing', async ({ browser, factory }) => {
  const { context, page } = await open(browser, factory, DESKTOP)
  await openRole(page, factory, 'builder_jira')
  const edited = await page.getByTestId('role-base').getAttribute('data-base')
  // Another tab saves a newer revision while this one is still open on the older one.
  const other = await context.newPage()
  await openRole(other, factory, 'builder_jira')
  await (await setting(other, 'model')).fill('opus')
  await other.getByTestId('role-save').click()
  const newer = Number(edited) + 1
  await expect(other.getByTestId('role-saved')).toHaveAttribute('data-revision', String(newer))

  await (await setting(page, 'model')).fill('haiku')
  await page.getByTestId('role-save').click()
  const bar = page.getByTestId('role-save-bar')
  await expect(bar.getByTestId('refusal')).toHaveAttribute('data-refusal', /^stale_version/)
  await expect(bar.getByTestId('refusal')).toContainText('This changed since you opened it')
  await expect(page.getByTestId('role-saved')).toHaveCount(0)
  await expect(page.getByTestId('role-base')).toHaveAttribute('data-base', String(edited))
  expect(await factory.configuration('builder_jira', newer + 1)).toBeNull()
  expect((await factory.configuration('builder_jira', newer))?.settings).toEqual({ model: 'opus', effort: 'high' })
  await context.close()
})

test('role/widths: the role form opens from the shell at 360px and 1280px with no primary action clipped', async ({ browser, factory }) => {
  for (const viewport of [PHONE, DESKTOP]) {
    const phone = viewport.width < 768
    const { context, page } = await open(browser, factory, viewport)
    await page.goto(factory.origin + '/you')
    await page.getByTestId('you-roles').click()
    await expect(page).toHaveURL(/\/roles$/)
    await unclipped(page, 'role-open', phone)
    await page.getByTestId('role-name').fill('builder_jira')
    await page.getByTestId('role-open').click()
    await expect(page.getByTestId('role-form')).toBeVisible()
    await unclipped(page, 'catalog-read', phone)
    await unclipped(page, 'role-save', phone)
    await context.close()
  }
})

test('team/owner-save: the owner adds, changes and removes roles and his save is current once read back', async ({ browser, factory }) => {
  const { context, page, sent } = await open(browser, factory, DESKTOP)
  await openTeam(page, factory, 'project-a')
  const before = (await factory.team('project-a'))!
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', String(before.revision))
  await expect(page.getByTestId('team-edited-from')).toHaveAttribute('data-version', String(before.version))
  await page.getByTestId('new-role').fill('builder_jira')
  await page.getByTestId('add-role').click()
  await expect(page.getByTestId('kind-builder_jira')).toHaveValue('specialist')
  await page.getByTestId('config-role-builder_jira').fill('builder_jira')
  await page.getByTestId('config-revision-builder_jira').fill('1')
  await page.getByTestId('workers-builder_jira').fill('w-build')
  await page.getByTestId('responsibilities-builder_jira').fill('fetch_tickets, report')
  await page.getByTestId('expertise-builder_jira').fill('jira')
  await page.getByTestId('permissions-builder_jira').fill('finding')
  await page.getByTestId('capacity-builder_jira').fill('1')
  await page.getByTestId('invocations-builder_jira').fill('2')
  await page.getByTestId('wall-builder_jira').fill('100')
  await page.getByTestId('config-role-implementation').fill('builder_jira')
  await page.getByTestId('config-revision-implementation').fill('2')
  await page.getByTestId('remove-reporter').click()
  await page.getByTestId('team-save').click()
  await expect(page.getByTestId('team-outcome')).toHaveAttribute('data-outcome', 'saved')
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', String(Number(before.revision) + 1))

  const save = sent.find((s) => s.route === 'teams/save')!
  expect(save.body.project).toBe('project-a')
  expect(save.body.team_version).toBe(before.version)
  const team = save.body.team as { roles: Record<string, { kind: string; capability_configuration?: unknown }> }
  expect(team.roles.builder_jira!.kind).toBe('specialist')
  expect(team.roles.builder_jira!.capability_configuration).toEqual({ role: 'builder_jira', revision: 1 })
  expect(team.roles.implementation!.capability_configuration).toEqual({ role: 'builder_jira', revision: 2 })
  expect(team.roles.reporter).toBeUndefined()
  const after = (await factory.team('project-a'))!
  expect(after.revision).toBe(Number(before.revision) + 1)
  expect(after.team).toEqual(save.body.team)
  expect(after.proposal ?? null).toBeNull()
  await context.close()
})

test('team/authoritative: another member\'s proposal shows pending, appears in Decisions, and is current only after the owner answers', async ({ browser, factory }) => {
  const member = await open(browser, factory, DESKTOP, 'owner2')
  await openTeam(member.page, factory, 'project-a')
  const before = (await factory.team('project-a'))!
  const current = String(before.revision)
  await member.page.getByTestId('expertise-elaboration').fill('python, docs')
  await member.page.getByTestId('team-save').click()
  await expect(member.page.getByTestId('team-outcome')).toHaveAttribute('data-outcome', 'proposed')
  const proposed = String(Number(before.revision) + 1)
  await expect(member.page.getByTestId('team-pending')).toHaveAttribute('data-revision', proposed)
  await expect(member.page.getByTestId('team-current')).toHaveAttribute('data-revision', current)
  const request = member.sent.find((s) => s.route === 'teams/save')!.answer!.owner_request as string
  expect(request).toBeTruthy()
  // Read again before any answer: the proposal is still only pending.
  await member.page.getByTestId('team-reload').click()
  await expect(member.page.getByTestId('team-current')).toHaveAttribute('data-revision', current)
  await expect(member.page.getByTestId('team-pending')).toHaveAttribute('data-revision', proposed)

  const owner = await open(browser, factory, DESKTOP)
  await openTeam(owner.page, factory, 'project-a')
  await expect(owner.page.getByTestId('team-current')).toHaveAttribute('data-revision', current)
  await expect(owner.page.getByTestId('team-pending')).toHaveAttribute('data-revision', proposed)
  // The request is in the decisions screen (VELDO-0145 AC3), and the owner answers it there.
  await owner.page.goto(factory.origin + '/decisions')
  await expect(owner.page.locator(`[data-testid="inbox"] [data-request="${request}"]`)).toHaveCount(1)
  await owner.page.goto(factory.origin + '/decisions/' + request)
  await expect(owner.page.getByTestId('decision')).toHaveAttribute('data-request', request)
  expect((await factory.team('project-a'))!.revision).toBe(before.revision)
  await owner.page.locator('[data-choice="accept"]').click()
  await owner.page.getByTestId('rationale').fill('The elaboration role needs the docs expertise.')
  await owner.page.getByTestId('send-answer').click()
  await expect.poll(async () => (await factory.team('project-a'))!.revision).toBe(Number(proposed))

  await member.page.getByTestId('team-reload').click()
  await expect(member.page.getByTestId('team-current')).toHaveAttribute('data-revision', proposed)
  await expect(member.page.getByTestId('team-pending')).toHaveCount(0)
  await owner.page.goto(factory.origin + '/teams/project-a')
  await expect(owner.page.getByTestId('team-current')).toHaveAttribute('data-revision', proposed)
  await member.context.close()
  await owner.context.close()
})

test('team/refusals: no configuration, an incomplete roster and a stale team version are named beside the save at 360px', async ({ browser, factory }) => {
  const { context, page } = await open(browser, factory, PHONE)
  await openTeam(page, factory, 'project-a')
  const before = (await factory.team('project-a'))!
  const current = String(before.revision)
  const bar = page.getByTestId('team-save-bar')
  const refused = async (name: RegExp) => {
    await unclipped(page, 'team-save', true)
    await page.getByTestId('team-save').tap()
    await expect(bar.getByTestId('refusal')).toHaveAttribute('data-refusal', name)
    await expect(page.getByTestId('team-outcome')).toHaveCount(0)
    await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', current)
    const stored = (await factory.team('project-a'))!
    expect([stored.revision, stored.team, stored.proposal ?? null]).toEqual([before.revision, before.team, null])
    await page.getByTestId('team-reload').tap()
    await expect(bar.getByTestId('refusal')).toHaveCount(0)
  }
  await page.getByTestId('config-role-builder_jira').fill('')
  await page.getByTestId('config-revision-builder_jira').fill('')
  await refused(/missing_capability_configuration/)
  await page.getByTestId('remove-independent_review').tap()
  await refused(/incomplete_roster/)

  const other = await context.newPage()
  await openTeam(other, factory, 'project-a')
  await other.getByTestId('expertise-builder_jira').fill('jira, confluence')
  await other.getByTestId('team-save').tap()
  await expect(other.getByTestId('team-current')).toHaveAttribute('data-revision', String(Number(current) + 1))
  const newer = (await factory.team('project-a'))!
  await page.getByTestId('expertise-builder_jira').fill('jira, bitbucket')
  await page.getByTestId('team-save').tap()
  await expect(bar.getByTestId('refusal')).toHaveAttribute('data-refusal', /stale_subject/)
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', current)
  expect((await factory.team('project-a'))!).toEqual(newer)
  await context.close()
})

test('team/default-team: the same form saves the default team bound to the revision it was edited from', async ({ browser, factory }) => {
  const { context, page, sent } = await open(browser, factory, DESKTOP)
  await openTeam(page, factory, 'default')
  const head = (await factory.team('default'))!
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', String(head.revision))
  await expect(page.getByTestId('team-edited-from')).toHaveAttribute('data-version', String(head.revision))
  await page.getByTestId('config-role-implementation').fill('builder_jira')
  await page.getByTestId('config-revision-implementation').fill('2')
  await page.getByTestId('team-save').click()
  await expect(page.getByTestId('team-outcome')).toHaveAttribute('data-outcome', 'saved')
  const next = Number(head.revision) + 1
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', String(next))
  const save = sent.find((s) => s.route === 'teams/default/save')!
  expect(save.body.base).toBe(head.revision)
  expect((await factory.defaultRevision(next))?.team).toEqual(save.body.team)
  await context.close()
})

test('team/default-stale-save: a default team save edited from an older revision is refused and stores nothing', async ({ browser, factory }) => {
  const { context, page } = await open(browser, factory, DESKTOP)
  await openTeam(page, factory, 'default')
  const head = Number((await factory.team('default'))!.revision)
  const other = await context.newPage()
  await openTeam(other, factory, 'default')
  await other.getByTestId('expertise-elaboration').fill('python, docs')
  await other.getByTestId('team-save').click()
  await expect(other.getByTestId('team-current')).toHaveAttribute('data-revision', String(head + 1))

  await page.getByTestId('expertise-elaboration').fill('python, design')
  await page.getByTestId('team-save').click()
  const bar = page.getByTestId('team-save-bar')
  await expect(bar.getByTestId('refusal')).toHaveAttribute('data-refusal', /^stale_version:default_team$/)
  await expect(page.getByTestId('team-current')).toHaveAttribute('data-revision', String(head))
  expect(await factory.defaultRevision(head + 2)).toBeNull()
  expect(Number((await factory.team('default'))!.revision)).toBe(head + 1)
  await context.close()
})

test('team/widths: the team form and the default team open from the shell at 360px and 1280px with no primary action clipped', async ({ browser, factory }) => {
  for (const viewport of [PHONE, DESKTOP]) {
    const phone = viewport.width < 768
    const { context, page } = await open(browser, factory, viewport)
    await page.goto(factory.origin + '/you')
    await page.getByTestId('you-team').click()
    await expect(page).toHaveURL(/\/teams$/)
    await unclipped(page, 'team-open', phone)
    await page.getByTestId('team-project').fill('project-a')
    await page.getByTestId('team-open').click()
    await expect(page.getByTestId('team-current')).toBeVisible()
    await unclipped(page, 'add-role', phone)
    await unclipped(page, 'team-save', phone)
    await page.goto(factory.origin + '/teams')
    await page.getByTestId('team-open-default').click()
    await expect(page.getByTestId('team-current')).toBeVisible()
    await unclipped(page, 'team-save', phone)
    await context.close()
  }
})
