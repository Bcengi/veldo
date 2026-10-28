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

## The factory harness

`e2e/harness.py` builds a real factory in a temporary directory: a real SQLite store and membership
(owner with full scope, a member scoped to another project, a steward), the real API authority and
settlement, a real execution record written through the launch receiver's `Recorder`, and the real
`control_api.listen` serving `dist/` with the real content security policy. Passkeys are real: the
e2e tests add a Chrome virtual authenticator, so registration and sign-in are real WebAuthn
ceremonies verified by OpenSSL. A second loopback port takes test controls (approve a pending
registration at the host, append record lines, end a run, answer from Telegram, revise a
presentation, drop record connections). The browser never sees that port.

## Falsifiers

Every acceptance criterion's check names a falsifier: a small change to production code that must
turn the check red. They are registered in `e2e/falsifiers.json` (UI side) and in
`scripts/check_teeth_mutations.py` (API side). `npm run falsify -- <case>` applies one to a copy,
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
