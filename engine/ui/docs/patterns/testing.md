# Testing

Three layers, each with a job. A test proves a behavior a person or the API depends on; a test that
only executes lines is not written.

| Layer | Tool | Where | Proves |
|---|---|---|---|
| Unit | Vitest | `src/**/*.spec.ts` beside the module | Pure logic: record parsing, frame application, inbox reduction, refusal mapping, base64url and key encoding |
| Component | Vitest + @vue/test-utils + jsdom | `src/**/*.spec.ts` beside the component | What a component renders for given props and state, what it emits, which refusal it shows where, which API calls a view makes |
| End to end | Playwright with system Chrome | `e2e/*.spec.ts` | What a person sees and can do in a real browser against a real factory harness, at phone and desktop widths, in both themes |

The Python suite `scripts/suites/*_veldo_0145_*.py` covers the API side: the page and assets the API
serves, the security policy, refusal of every factory data route without a session, the UI's route
table against the API's, and the dependency policy.

## Conventions

- One `describe` per unit (function, store, component); `it` sentences say the behavior:
  `it('drops a line it already applied')`.
- Arrange, act, assert, in that order, without comment banners.
- Test data builders live in the spec file until three specs need them, then move to
  `src/test/builders.ts`.
- Mock at the boundary only: component tests stub `src/api/*` modules (never `fetch` deep inside a
  store); store tests stub the api module; e2e tests mock nothing.
- No snapshot tests of markup. Assert the text, roles and attributes a person or an assistive
  technology meets.

## What each kind of test must prove

**A view.** For each state (loading, empty, error, ready) it renders the right panel; the error
panel names the refusal; the API calls it makes are exactly the routes its page in `docs/views/`
lists.

**A component that acts.** The action is disabled while pending; the request carries exactly the
fields the route takes, with the versions shown on screen; success shows the API's outcome; each
refusal class shows its sentence and name beside the action; nothing changes before the API answers.

**A store.** It holds what the API said, drops answers older than the newest request, and resets on
session end.

**A pure module.** Its edge cases: empty input, unknown kinds, malformed payloads (a record line that
is not JSON is still a line), repeats and gaps.

**An e2e screen test.** At 360, 390, 1280 and 1440 px: no page-wide horizontal overflow, the primary
action visible and unclipped, no overlapping controls, primary targets at least 44 by 44 px on phone;
keyboard-only completion on desktop; axe finds no violation; no request leaves the route table; no
content security policy violation is reported.

**The theme, focus and origin checks (VELDO-0229).** `e2e/layout.spec.ts` also proves the one theme
preference (the sidebar's "Dark appearance" switch and the You screen's switch agree, and the choice
survives navigation and reload), the primary action's contrast at rest and on hover and its solid
keyboard focus outline in both themes, and that no request leaves the origin and no built asset names
the Iconify API or a font CDN. `e2e/screens.spec.ts` takes the proof's screenshots on request
(`VELDO_SCREENS_0229=1`), labeled as seeded demonstration data; it is skipped otherwise.

## Time in browser tests (VELDO-0358)

A browser test's verdict must be the same on an idle machine and on one several times slower, so no
test, fixture or configuration sleeps, reads a clock, or names a duration of its own.

- **Two durations only**, exported by `e2e/fixtures.ts`: `WAIT_HANG_MS` (600 s) bounds one wait from its
  start (an expectation, an action, a navigation, the harness's ready line or exit); `PROCESS_HANG_MS`
  (3600 s) bounds the run from its last progress. Never pass a `timeout` option, never call
  `test.setTimeout`, `page.waitForTimeout` or `Date.now`. The gate's census
  (`scripts/check_wallclock.py`) refuses each of them.
- **No test has a limit on its total time** (`timeout: 0` in `playwright.config.ts`). The `Progress`
  reporter (the default export of `e2e/fixtures.ts`) re-arms the process hang bound at every test and
  step event and ends the run only when none happened for that long, naming every test and step still
  in flight with its source line. A Python suite that runs the browser tests sets `VELDO_E2E_PROGRESS`,
  so each event is also a line on the run's output, which is what the suite counts its own bound from.
- **Wait for the page's own state, never for an interval.** An expectation waits on what the page
  shows. Where a test must act or read "after the page is done", it awaits `settled(page)`, the page
  settled signal that stands in every page of every test: no request unanswered (the page counts its
  own, to the end of each answer's body; its event streams are not requests), no `StatePanel` loading,
  no finite animation or transition running. A panel that does not say its state through `StatePanel`
  gets that first; the test does not get a timer.
- **The harness starts and stops on events.** `startHarness` waits for the ready line or the exit,
  whichever comes first; `stopHarness` closes its input and waits for its exit. Either one reaching the
  wait hang bound ends the harness and is reported as hung.
- **Data, not clocks.** A name that must be new is `unique()`. A time written into a record is the
  factory's own clock, `await factory.now()`. In `e2e/harness.py` the wall time handed to the product is
  the suites' support stamp (`wall()`).
- **Product timers.** The harness selects the timers profile in its organs' timers table before it
  loads them (every giving-up deadline at the wait hang bound) and reports the profile and the
  effective values in its ready line; the suites' row `timers/profile-applied` reads that report.

## The factory harness

`e2e/harness.py` builds a real factory in a temporary directory: a real SQLite store and membership
(owner with full scope, a member scoped to another project, a steward), the real API authority and
settlement, a real execution record written through the launch receiver's `Recorder`, and the real
`control_api.listen` serving `dist/` with the real content security policy. Passkeys are real: the
e2e tests add a Chrome virtual authenticator, so registration and sign-in are real WebAuthn
ceremonies verified by OpenSSL. A second loopback port takes test controls (approve a pending
registration at the host, append record lines, end a run, answer from Telegram, revise a
presentation, drop record connections). The browser never sees that port.

A Python test that builds a `Factory` in its own process (suite 113 of VELDO-0145) calls its `close()` when
done: it stops the fake Telegram bot server, joins its thread and closes its listener, and ends the
authority thread, so the suite leaves nothing running (the suite runtime's residue check, VELDO-0358).

## Falsifiers

Every acceptance criterion's check names a falsifier: a small change to production code that must
turn the check red. They are registered in `e2e/falsifiers.json` (UI side) and in
`scripts/check_teeth_mutations.py` (API side). `npm run falsify <case>` applies one to a copy,
runs its check, requires red, and restores. The red and green records go under `proof/<spec>/`.

## Running

`npm test` for unit and component tests, `npm run e2e` for browser tests; one file at a time while
working. On the shared host, wrap any multi-file run in the gate lock (see `../../CLAUDE.md`).

## When you change something

| You changed | Add or update |
|---|---|
| A pure module | Its unit spec, including the new edge case |
| A component's props, emits or states | Its component spec and its page in `docs/ui/` |
| A view's reads or actions | Its component spec, its e2e spec and its page in `docs/views/` |
| A route used | `api/routes.ts`; the Python suite checks it against the API |
| A dependency | `dependency-policy.json` and [dependencies.md](dependencies.md) |
