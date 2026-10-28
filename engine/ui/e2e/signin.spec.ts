import { ROUTE_TABLE, authenticator, expect, guard, routeOf, signIn, test } from './fixtures'

/**
 * VELDO-0145 AC1: the passkey session, the enrollment and sign-in screen, and every screen reading and
 * acting only through the API, with factory data only in an authenticated session.
 */

const DATA_SCREENS = (state: { dispatches: Record<string, string>; requests: Record<string, string> }) => [
  '/runs',
  `/runs/${state.dispatches.done}`,
  '/decisions',
  `/decisions/${state.requests.de1}`,
  '/you',
]

test('enroll-then-sign-in: a fresh passkey signs in only after the host approves it', async ({ page, factory }) => {
  const watch = await guard(page)
  await authenticator(page.context(), page)
  await page.goto(factory.origin + '/runs')
  // Before sign-in: only the enrollment and sign-in controls, and the named refusal.
  await expect(page).toHaveURL(/\/sign-in/)
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthenticated:no_session')
  await expect(page.getByRole('navigation')).toHaveCount(0)
  const controls = await page.locator('button, a[href], input, textarea, select').evaluateAll((els) =>
    els.map((e) => (e as HTMLElement).dataset.testid ?? e.textContent?.trim() ?? ''),
  )
  expect(controls.sort()).toEqual(['enroll-start', 'sign-in'])

  await page.getByTestId('enroll-start').click()
  await page.getByTestId('passkey-label').fill('Pixel phone')
  await page.getByTestId('enroll-create').click()
  await expect(page.getByTestId('pending')).toBeVisible()

  // The screen shows the pending key's label and fingerprint exactly as the host shows them.
  const host = await factory.control<{ pending: { label: string; fingerprint: string }[] }>('/pending')
  const waiting = host.pending.find((p) => p.label === 'Pixel phone')
  expect(waiting, 'the host shows the pending registration').toBeTruthy()
  await expect(page.getByTestId('pending-label')).toHaveText(waiting!.label)
  await expect(page.getByTestId('fingerprint')).toHaveAttribute('aria-label', `Fingerprint ${waiting!.fingerprint}`)
  const shownGroups = await page.locator('.fingerprint-group').allTextContents()
  expect(shownGroups.join(':')).toBe(waiting!.fingerprint.split(':').slice(1).join(':'))

  // Signing in before the host approves is refused, and nothing of the shell appears.
  await page.getByTestId('pending-sign-in').click()
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', /unauthenticated:unknown_credential/)
  await expect(page.getByRole('navigation', { name: 'Main' })).toHaveCount(0)
  await expect(page).toHaveURL(/\/sign-in/)

  // The host compares the fingerprint and approves that one; now the same passkey signs in.
  const approved = await factory.control<{ fingerprint: string; refusal: string | null }>('/approve', {
    principal: 'owner',
    label: 'Pixel phone',
  })
  expect(approved.fingerprint).toBe(waiting!.fingerprint)
  expect(approved.refusal).toBeFalsy()
  await page.getByTestId('pending-sign-in').click()
  await expect(page.getByRole('navigation', { name: 'Main' }).first()).toBeVisible()
  await expect(page).toHaveURL(/\/runs$/)

  // The shell's navigation reaches the run screens and the decisions screen.
  await expect(page.getByTestId('runs')).toBeVisible()
  await page.locator('.run-row').first().click()
  await expect(page.getByTestId('terminal')).toBeVisible()
  await page.locator('.rail [data-nav="decisions"]').click()
  await expect(page.getByTestId('inbox')).toBeVisible()

  // Sign out: back to the sign-in screen, and no factory data is reachable.
  await page.locator('.rail [data-nav="you"]').click()
  await page.getByTestId('sign-out').click()
  await expect(page).toHaveURL(/\/sign-in/)
  const after = await page.request.get(`${factory.origin}/api/v1/domains/${factory.domain}/workers`)
  expect(after.status()).toBe(401)
  expect(await watch.violations()).toEqual([])
})

test('unauthenticated access: no screen shows factory data before a passkey session', async ({ page, factory }) => {
  const state = await factory.state()
  const watch = await guard(page)
  for (const screen of DATA_SCREENS(state)) {
    await page.goto(factory.origin + screen)
    await expect(page).toHaveURL(/\/sign-in\?next=/)
    await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthenticated:no_session')
    await expect(page.locator('[data-testid="runs"], [data-testid="lines"], [data-testid="inbox"], [data-testid="decision"]')).toHaveCount(0)
  }
  // Every factory data route refuses without a session, whatever the screen would have asked.
  for (const [name, spec] of Object.entries(ROUTE_TABLE.routes)) {
    if (name.startsWith('auth.')) continue
    const url = factory.origin + spec.path.replace('{domain}', factory.domain) + (name.startsWith('runs.') ? `?dispatch=${encodeURIComponent(state.dispatches.done!)}` : '')
    const response = spec.method === 'GET' ? await page.request.get(url) : await page.request.post(url, { data: {}, headers: { Origin: factory.origin } })
    expect(response.status(), `${name} without a session`).toBe(401)
  }
  // Every request the screens made answered no data: auth.session refused, data routes never answered 200.
  const data = watch.requests.filter((r) => new URL(r.url).pathname.startsWith('/api/') && routeOf(r.method, r.url, factory.domain) !== 'auth.session')
  expect(data.filter((r) => r.status === 200)).toEqual([])
  expect(await watch.violations()).toEqual([])
})

test('a session that ends while a screen is open shows the named refusal and drops the data', async ({ page, factory }) => {
  const state = await factory.state()
  await signIn(page, factory)
  await page.goto(factory.origin + '/runs/' + state.dispatches.live)
  await expect(page.getByTestId('lines')).toBeVisible()
  await factory.control('/sessions/end', { principal: 'owner' })
  await expect(page).toHaveURL(/\/sign-in/)
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', /unauthenticated:(signed_out|revoked|no_session)/)
  await expect(page.locator('[data-testid="lines"], [data-testid="runs"]')).toHaveCount(0)
  // And the expired session: idle past 30 minutes, the next read is refused by name.
  await signIn(page, factory)
  await page.goto(factory.origin + '/decisions')
  await expect(page.getByTestId('inbox')).toBeVisible()
  await factory.control('/sessions/expire')
  await page.getByRole('button', { name: 'Refresh' }).click()
  await expect(page).toHaveURL(/\/sign-in/)
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthenticated:session_expired')
  await expect(page.locator('[data-testid="inbox"]')).toHaveCount(0)
})

test('a member outside a project sees its named refusal and none of its data', async ({ page, factory }) => {
  const state = await factory.state()
  // A member of project-b: project-a's run is refused by name; project-b's own run is shown.
  await signIn(page, factory, 'bmember')
  await page.goto(factory.origin + '/runs/' + state.dispatches.done)
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', 'unauthorized:out_of_scope')
  await expect(page.getByTestId('lines')).toHaveCount(0)
  await page.goto(factory.origin + '/runs')
  await expect(page.locator(`[data-dispatch="${state.dispatches.other}"]`)).toBeVisible()
  await expect(page.locator(`[data-dispatch="${state.dispatches.done}"]`)).toHaveCount(0)
  await page.goto(factory.origin + '/runs/' + state.dispatches.other)
  await expect(page.getByTestId('lines')).toBeVisible()
  // A member whose scope covers no project of this factory: the API names that, and nothing is shown.
  await page.locator('.rail [data-nav="you"]').click()
  await page.getByTestId('sign-out').click()
  await signIn(page, factory, 'outsider')
  await page.goto(factory.origin + '/runs/' + state.dispatches.done)
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', /^unauthorized:(out_of_scope|no_project)$/)
  await expect(page.getByTestId('lines')).toHaveCount(0)
  await page.goto(factory.origin + '/runs')
  await expect(page.locator('[data-state="empty"], [data-state="error"]')).toBeVisible()
  await page.goto(factory.origin + '/decisions')
  await expect(page.getByTestId('refusal')).toHaveAttribute('data-refusal', /^unauthorized:(out_of_scope|no_project)$/)
  await expect(page.getByTestId('inbox')).toHaveCount(0)
  await page.goto(factory.origin + '/decisions/' + state.requests.de1)
  await expect(page.getByTestId('decision')).toHaveCount(0)
  await expect(page.getByTestId('refusal').first()).toBeVisible()
})

test('route trace: every request each screen makes is a published API route or a built asset', async ({ page, factory }) => {
  const state = await factory.state()
  const watch = await guard(page)
  await signIn(page, factory)
  for (const screen of DATA_SCREENS(state).concat([`/runs/${state.dispatches.live}`])) {
    await page.goto(factory.origin + screen)
    await page.waitForLoadState('networkidle')
  }
  const untraced = watch.requests.filter((r) => {
    const url = new URL(r.url)
    if (url.origin !== factory.origin) return true
    if (url.pathname.startsWith('/api/')) return routeOf(r.method, r.url, factory.domain) === null
    return !(r.method === 'GET' && (url.pathname.startsWith('/assets/') || url.pathname === '/favicon.svg' || !url.pathname.includes('.')))
  })
  expect(untraced).toEqual([])
  const used = new Set(watch.requests.map((r) => routeOf(r.method, r.url, factory.domain)).filter(Boolean))
  for (const route of ['auth.session', 'auth.challenge', 'auth.sign_in', 'reads.workers', 'reads.work', 'reads.decisions', 'runs.record', 'runs.record_stream'])
    expect(used, `screens use ${route}`).toContain(route)
  const response = await page.request.get(factory.origin + '/runs')
  expect(response.headers()['content-security-policy']).toBe(
    "default-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
  )
  expect(await response.text()).not.toMatch(/<script(?![^>]*\bsrc=)[^>]*>/)
  expect(await watch.violations()).toEqual([])
})
