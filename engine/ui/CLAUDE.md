# Veldo factory UI

The owner's control center for a Veldo factory: watch every worker run live, answer the decisions
waiting on you, and sign in with a passkey, on a phone or a desktop. It is a Vue single page served by
the authenticated factory API (`.veldo/control_api.py`) on loopback behind Tailscale Serve, and it
reads and acts only through that API's published routes.

Read this file and the relevant page under `docs/` before changing anything here. After a change,
update the page it touches in the same commit. These rules bind every UI ticket (VELDO-0145, 0159,
0163, 0131, 0179 and later).

## Commands

Run from `engine/ui/`.

| Command | What it does |
|---|---|
| `npm ci` | Install exactly the locked dependency set |
| `npm run dev` | Vite dev server; proxies `/api` to `VELDO_API` (default `http://127.0.0.1:8765`) |
| `npm run typecheck` | `vue-tsc --noEmit` over `src/` and tests |
| `npm run build` | Type-check, then build to `dist/` (what the API serves). The proof and the falsifiers use this script |
| `npm test` | Unit and component tests once (Vitest, jsdom) |
| `npm run e2e` | Browser tests against a real factory harness (Playwright, system Chrome) |
| `npm run e2e e2e/decisions.spec.ts` | One browser test file |
| `npm run falsify <case>` | Apply one registered falsifier, run its check, expect red, restore |

To lay the build where an installed factory serves it, run the repository's install path after the build,
asking for the UI: `python3 .veldo/init_scaffold.py --ui <factory repository>` lays `dist/` as
`<repository>/.veldo/ui`, beside the API module (replaced whole when the build changed), with a `.gitignore`
that keeps it out of that repository. A plain scaffold (no `--ui`) never lays the UI. A composed pack carries
no UI source, so the UI is always built and laid from a Veldo source checkout. `VELDO_ORGANS=<repository>/.veldo VELDO_UI_INSTALLED=1
npm run e2e e2e/signin.spec.ts` runs the browser checks against that installed copy.

On the shared host, any run beyond a single test file goes inside
`flock /home/dmitry/.local/state/core-gates/.gate.lock <command>`. Never leave a dev server running:
the e2e runner starts and stops its own harness.

## Stack

Every package is public open source, pinned in `package-lock.json`, and listed with its origin,
license and tier in `dependency-policy.json`. Adding one means adding it there first; the
dependency-policy suite fails on anything unlisted. See [docs/patterns/dependencies.md](docs/patterns/dependencies.md).

- Vue 3 with `<script setup lang="ts">` and the Composition API only
- TypeScript 6, strict (vue-tsc does not run on TypeScript 7 yet)
- Vite
- No component library: Veldo's own controls on native elements (`src/components/V*.vue`); PrimeVue was
  dropped (free and paid tiers, PLAN-0019 C16) and the policy denies it
- Tailwind CSS 4 for layout utilities; design tokens are CSS custom properties (`src/styles/tokens.css`)
- Pinia (setup stores) and vue-router
- monaco-editor for diffs only, read-only, loaded lazily
- Fonts self-hosted from Fontsource packages: IBM Plex Sans (everything) and IBM Plex Mono (the record
  and copied ids)

## Hard rules

1. **The API is the only source of state and the only way to act.** No store, file or provider is
   reached any other way. Every request goes through `src/api/client.ts` and names a route of
   `src/api/routes.ts`, which mirrors the API's published `ROUTES` table; a test compares the two.
2. **No inline script and no inline style.** The API serves a same-origin content security policy
   (`default-src 'self'`, no `style-src`). Nothing may need `unsafe-inline`: no library that writes
   style elements, no `v-html`, no `<style>` element or `style="..."` markup created at run time. Vue `:style` bindings
   are allowed (they use the CSS object model). Libraries that write styles are routed through
   `src/ui/sheets.ts` and `src/ui/style-attributes.ts`; the browser tests fail on any policy violation.
3. **Text from the factory is text.** Record lines, questions and rationales render through text
   interpolation, never `v-html` or markdown rendering.
4. **Never show optimism.** A decision is answered only when the API says so; a refusal is shown beside
   the action it concerns with its name, never as success and never as a generic failure.
5. **The anti-forgery token lives in memory only** (the session store), never in storage, the URL or
   the DOM.
6. **No placeholder styling.** Every screen ships loading, empty, error (named refusal) and populated
   states, at 360, 390, 1280 and 1440 pixels, in light and dark.
7. **Accessible by construction.** 44 px primary touch targets, visible focus, a name on every control,
   reduced motion respected. See [docs/patterns/accessibility.md](docs/patterns/accessibility.md).
8. **ASCII in source and docs**: no em dash, en dash or double hyphen in prose.

## Layout of the code

```
src/
  main.ts            app bootstrap: Pinia, router, fonts, styles
  App.vue            the shell switch: sign-in screen or AppShell
  api/               the only code that calls fetch or EventSource
  stores/            Pinia setup stores (session, decisions, runs)
  router/            routes and the session guard
  app/               navigation registry and shell chrome
  features/<area>/   pure logic and the components of one area (overview, run, decisions, signin)
  components/        shared components, each documented in docs/ui/
  composables/       shared composables (theme, media, async state)
  views/             one per route; orchestrates, holds no fetch logic
  styles/            tokens.css, base.css, components.css
  ui/                CSS object model shims for Monaco (sheets, style attributes)
e2e/                 Playwright specs and the factory harness they drive
docs/                these guidelines
```

Names: components `PascalCase.vue`; composables `useThing.ts`; stores `useThingStore` in `thing.ts`;
pure modules `kebab-case.ts`; tests `*.spec.ts` beside their subject, browser tests in `e2e/`.

## Documentation map

```
docs/
  design/     direction, colors, typography, layout and motion
  patterns/   api layer and state, testing, interactivity, accessibility, dependencies
  ui/         one page per shared component (index: docs/ui/README.md)
  views/      one page per screen: routes, reads, states and refusals
```

Before creating a component, check [docs/ui/README.md](docs/ui/README.md); it may exist already or
take one more prop. A new shared component gets its page in `docs/ui/` in the same commit. A new
screen gets its page in `docs/views/`. A rule that appears in two places becomes a pattern page.
