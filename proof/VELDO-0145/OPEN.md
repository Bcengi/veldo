# VELDO-0145: questions for the owner

Each item below needs an owner decision. Work continued around each one; nothing here is hidden in the
implementation.

## 1. PrimeVue and the "no free and paid tiers" rule (PLAN-0019 C16, VELDO-0131 AC4)

The owner named PrimeVue 4 (Telegram 37228). The registry's latest PrimeVue is 5.0.4, which is under
PrimeTek's commercial "PrimeUI License" (a free community tier and a paid tier) and pulls in
`@primeui/license-manager`. PrimeVue 4.5.5 is MIT, so the build pins 4.5.5. PrimeTek also sells paid
products around version 4 (templates, PrimeBlocks, a theme designer). C16 says "no library with free
and paid tiers"; the dependency policy denies PrimeVue 5 and the license manager and records PrimeVue 4
under an owner decision (`engine/ui/dependency-policy.json`, `owner_decisions`).

Decide: keep PrimeVue 4.5.5 (and stay on 4.x), or drop PrimeVue for native controls styled by Veldo.
Only five PrimeVue components are used (Button, InputText, Textarea, RadioButton, ToggleSwitch), all
unstyled, so either is a small change.

## 2. Monaco and PrimeVue under the API's content security policy

VELDO-0171's policy has no `style-src`, so inline `<style>` elements and `style="..."` markup are
refused. Monaco writes both, and PrimeVue writes a base sheet even unstyled. Rather than relax the
policy, the build replaces those two internal modules with Veldo's own (CSS object model), and moves
Monaco's style attributes into `element.style` (`engine/ui/src/ui/`). The browser tests assert zero
policy violations on every screen, and Monaco renders correctly. The cost: two internal module paths
(`@primevue/core/usestyle`, Monaco's `base/browser/domStylesheets.js`) are named in `vite.config.ts`,
so a PrimeVue or Monaco upgrade must re-run the e2e tests.

Decide: keep this (the policy stays exactly VELDO-0171's), or amend the policy with
`style-src 'self' 'unsafe-inline'` and drop the shims. Recommendation: keep it.

## 3. How the built UI reaches an installed host

The API serves the page from `control_api_ui.directory()`: the configuration's `ui` key, else `ui/`
beside the installed module, else `engine/ui/dist` beside the engine. The build output (`dist/`, about
3.6 MB, most of it Monaco) is not committed, and neither `veldo factory setup` (VELDO-0171) nor the
scaffold lays a built UI down yet, so on a host the API currently answers
`missing_evidence:ui_not_built` until someone runs `npm ci && npm run build` in `engine/ui` and points
the configuration's `ui` at `dist`. `control_client_api.py` and the setup modules are outside this
spec's footprint.

Decide: commit `dist/` (reproducible build, no Node on the host) or build at setup time; and which spec
teaches `veldo factory setup` to lay the UI down and write `ui` into the API configuration.

## 4. The phone leg over the tailnet (AC1)

AC1 says the lead runs the phone enrollment and sign-in leg over the tailnet once with the owner and
records it. That needs the owner's phone and the host's Tailscale Serve name, and item 3 resolved on the
host. Everything up to that is proven in Chrome with a virtual authenticator against a real factory
harness (real WebAuthn ceremonies verified by OpenSSL, real steward enrollment). To record: open
`https://<host tailnet name>/sign-in` on the phone, Add a passkey, compare its fingerprint with
`veldo factory passkey`, approve, sign in, open a run and a decision, sign out.

## 5. "Answer as a member outside the project's scope" (AC3)

The API has no distinct refusal for answering outside a project's scope. A member whose scope does not
cover the request never sees it (the read model filters it; a direct link shows
`missing_evidence:not_pending_or_out_of_scope` and no answer action). A member who can see it but is not
the presented owner is refused `unauthorized:not_owner` beside the action (tested). The owner whose
scope no longer covers it is refused `stale_version:stale_presentation` (VELDO-0068). Decide whether
that is the intended behavior or the API should name `unauthorized:out_of_scope` for answers too
(a VELDO-0130 or VELDO-0068 change, outside this footprint).

## 6. The stack named by PLAN-0019 C16 and VELDO-0131

This spec was amended to Vue (Telegram 37226, 37228). PLAN-0019 C16 and VELDO-0131 (screen contract and
AC4's allowed list: React, shadcn/ui, TanStack Table, React Flow, Chart.js) still name the React stack,
and VELDO-0179's AC1 says "the React shell of VELDO-0145". Those documents are outside this footprint.
Decide the Vue equivalents for 0131's remaining screens (tables, the workflow canvas, charts) when that
plan is revised.

## 7. Package origins

Vue, Vite, Vitest, vue-router and Pinia are maintained by the Vue and Vite teams (the Vue project was
started by Evan You; Vite and Vitest are now stewarded by VoidZero). The owner chose Vue explicitly; the
policy records each direct package's origin. No package from the deny list (Element Plus, Ant Design
Vue, Naive UI, Vant, Arco, TDesign, ECharts and others) is installed.
