---
schema: veldo.spec/v1
id: VELDO-0229
title: The web UI is built on Nuxt UI
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0145, VELDO-0159, VELDO-0163, VELDO-0131]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - ".veldo/shape_gate.py"
  - "engine/.veldo/shape_gate.py"
  - "scripts/suites/07_warp_1103_completion_mandatory.py"
  - "engine/.veldo/control_api_ui.py"
  - ".veldo/control_api_ui.py"
  - "scripts/suites/113_*"
  - "scripts/suites/118_*"
  - "scripts/suites/119_*"
  - "scripts/suites/120_*"
  - "engine/ui/e2e/layout.spec.ts"
  - "engine/ui/e2e/fixtures.ts"
  - "engine/ui/e2e/harness.py"
  - "specs/VELDO-0131-factory-phone-desktop-ui.md"
  - "specs/VELDO-0145-ui-shell-run-terminal-decisions.md"
  - "specs/VELDO-0229-the-web-ui-is-built-on-nuxt-ui.md"
  - "specs/index.md"
  - "proof/VELDO-0229/**"
behavior_bearing: true
observability:
  logs: >
    Unchanged: the UI records nothing new; the API keeps its own logs of every route the screens call.
  metrics: >
    Unchanged: none added by moving the controls.
  traces: >
    Unchanged: every request still goes through src/api/client.ts and names a published route.
  error_taxonomy: >
    Unchanged: every named refusal is shown beside the action it concerns, as before the move.
acceptance_criteria:
  - id: AC1
    text: >
      Nuxt UI 4.12.0 (exact pin, MIT, NuxtLabs) runs in the existing Vue 3, TypeScript, Vite, Tailwind CSS,
      Pinia and Vue Router app through its Vite plugin and Vue plugin (no Nuxt framework, no SSR), with UApp at
      the root (Telegram 38234 and 38235, sections 1 and 4). The shared buttons, cards, status badges and the
      account avatar are Nuxt UI components (UButton, UCard, UBadge, UAvatar). VButton keeps its interface and
      is adapted internally onto UButton: label, pending label, pending, disabled, variant, size, block, button
      type, passed attributes and the emitted click event are preserved. There is one theme preference:
      useTheme() drives both Veldo's data-theme attribute and Nuxt UI's dark and light classes; the sidebar
      carries a clearly labeled appearance switch and the account screen keeps its control, both on that one
      preference. Every new direct package is pinned exactly and recorded in dependency-policy.json; @vueuse/*
      is no longer denied (the VELDO-0131 and VELDO-0145 amendments, owner's dependency rule Telegram 28929);
      suite 120's stack lists Nuxt UI; the UI's CLAUDE.md and docs describe the stack, the theme and the
      wrappers.
    falsified_by: >
      @nuxt/ui missing from the lockfile or not exactly pinned (suite 113 ui/dependency-policy and suite 120
      ac4/dependency-policy and ac4/stack fail); a VButton component test that finds no Nuxt UI button, a lost
      pending label, disabled state, type, attribute or click event; a useTheme unit test where setting the
      preference leaves data-theme and the dark class disagreeing, or the sidebar switch and the account
      switch showing different preferences.
  - id: AC2
    text: >
      The look of Telegram 38255, which supersedes the look of 38234 and 38235 (the owner's chosen dashboard
      template, its gallery as visual reference only, no code, text or assets copied): neutral surfaces, white
      page and panels in light and a near-black page with panels barely lighter in dark, no colored
      backgrounds, shadows or gradients; thin 1px neutral borders and about 8px corners on every panel, 20 to
      24px inner padding and 16 to 20px between panels; a narrow icon rail sidebar (about 50px, icons only,
      grouped by subtle separators, the account avatar at the bottom) that a panel toggle in the top bar
      expands to a labeled sidebar of about 240px keeping the factory identity, host activity and account
      footer of 38234; a slim top bar per screen (about 50px: the panel toggle, the page title, actions at the
      right, a bottom border); segmented tabs in a bordered strip with the selected one a solid inverted pill;
      neutral buttons and selection (solid inverted for the main action, bordered neutral for the rest) in
      place of 38234's blue primary; compact KPI panels with a secondary label and a large semibold value;
      tables with a plain secondary header row, thin row dividers, monospace identifiers and small tinted
      status badges. Status keeps the meanings of 38234: green running, amber waiting, red failures or urgent
      attention, every status color with its text. IBM Plex Sans for the interface and IBM Plex Mono for logs,
      code and ids (38234). Behavior and content follow 38234 and 38235 (sections 2 and 3): the sidebar has
      navigation, factory identity, host activity and an account footer. Overview: the four real signals (running, blocked, failed, waiting on me) in one
      joined summary panel with large counts; beneath it the oldest waiting decision (question, waiting and
      deadline, a prominent answer action) and the host roster; then the ranked inbox and the current runs.
      Runs: active runs separated from stopped runs, unit, project, host, pipeline position and status easy
      to scan, and a header summary of runs, distinct projects and distinct hosts computed from the displayed
      rows. Run detail: the complete record (tool calls, output, errors, Monaco diffs), live updates, reconnect,
      follow, search, raw view and the station pipeline kept, the record taking most of the screen height.
      Decisions: on desktop the ranked inbox beside the open decision, each scrolling on its own, with the
      question, risk, choices, rationale and answer action clearly organized; on phones the single-pane flow
      and its accessible answer controls. Sign-in, account preferences, empty, loading and error states carry
      the same type, theme and controls. No metric is shown that the existing API responses do not support.
    falsified_by: >
      A unit test of the runs summary whose run, project or host count differs from the rows shown; the
      VELDO-0145 layout spec (decisions panes scrolling independently, the record's share of the height, the
      phone single-pane flow) or suites 113 and 120 failing; a section 7 screenshot that does not show the
      described layout or the neutral template look of Telegram 38255 (a colored primary action, a colored
      page or panel background, panel corners well above 8px, or a sidebar that cannot collapse to an icon
      rail).
  - id: AC3
    text: >
      Security and behavior are preserved (Telegram 38234 and 38235, section 5): every read and action still
      goes through the existing API layer; passkey sign-in, sessions, authorization, decision-version binding,
      pending states, named refusals and the API's actual outcome are unchanged; factory content renders as
      text. The strict content security policy stays intact: fonts, icons, scripts and styles are served from
      the build; Nuxt UI's runtime color injector (which writes a style element) is replaced by a narrowly
      scoped, documented adapter and the theme variables come from compiled CSS; icons, including loading
      indicators, are bundled from a local collection so nothing requests the Iconify API; the Monaco
      integration is unchanged. The primary button meets contrast in its normal and hover states in both
      themes, and keyboard focus stays visible on Nuxt UI controls.
    falsified_by: >
      Any content security policy violation or response from another origin in the browser tests (the layout
      spec's policy check, suite 120 ac2/api-only, suite 113's served-assets row); a built asset naming the
      Iconify API host; an axe color-contrast violation; a browser check that finds no visible focus outline
      on a focused Nuxt UI button or a primary button below 4.5:1 in its normal or hover state.
  - id: AC4
    text: >
      Verified as section 6 of Telegram 38234 and 38235 asks: the typecheck, the production build, the unit and
      component tests, and the browser tests (suites 113, 117, 118, 119 and 120 and the VELDO-0145 layout spec)
      pass; both themes are exercised at 360, 390, 1280 and 1440 pixels with no page overflow or overlapping
      controls, readable contrast, visible focus, accessible names that include the visible labels, usable
      phone touch targets, the theme kept across navigation and reload, working sign-in, live run viewing and
      decision submission, and no policy violation or unexpected external request. Tests that selected a native
      element now rendered by Nuxt UI select it by role or label, keeping their row names and intent.
    falsified_by: >
      Any failing row of suites 113, 117, 118, 119 or 120, any failing test of the layout spec (including its
      theme persistence test), a failing typecheck, build or unit test.
  - id: AC5
    text: >
      Screenshots (Telegram 38234 and 38235, section 7): full-resolution PNGs captured from the production
      build with the factory harness of engine/ui/e2e/, labeled as seeded demonstration data, at least
      Overview dark, Overview light, Run detail dark with a code diff, Decisions light and one phone screen, in
      proof/VELDO-0229/screens/ with an index.md naming each and saying the data is seeded.
    falsified_by: >
      One of the five named screens without its PNG or its line in the index, or an index that does not say
      the data is seeded demonstration data.
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change: the UI returns to Veldo's own controls on native elements; the API, its routes and
  every stored record are untouched by this specification.
---

## Intent

The owner wants Veldo's web UI built on a real component library rather than Veldo's own controls:
"for veldo, let's do nuxt ui" (Telegram 38228), with screenshots once it is integrated (Telegram 38229).
The full requirements followed in Telegram 38234 and 38235: integrate Nuxt UI into the existing
application and give it a polished, spacious infrastructure and AI operations dashboard design with
deliberate dark and light themes, verify the existing workflows, and show browser screenshots. They
supersede the shorter brief and the first acceptance criteria.

## Context

VELDO-0145 built the shell, run terminal and decisions on Vue 3 + Vite with Veldo's own controls on
native elements after PrimeVue was dropped; VELDO-0159, VELDO-0163 and VELDO-0131 added the server form,
the role and team forms and the factory screens on the same controls. Nuxt UI runs in a plain Vue + Vite
app through its Vite plugin, so the stack keeps Vue, Vite, Tailwind 4, Pinia, vue-router, Monaco,
Chart.js and TanStack Table, and the controls move onto Nuxt UI. Its dependencies include @vueuse/*,
which VELDO-0131 had rejected; the owner's dependency rule (Telegram 28929) approves the dependencies of
software he picks, so the amendments of VELDO-0131 and VELDO-0145 on this date lift that rejection. The
owner's selection of Nuxt UI supersedes the older instruction to use no component library (Telegram
38234); the security, dependency and testing requirements stay. Wrappers whose interface protects
behavior (VButton) stay and are adapted internally.

## Out of scope

New screens, new routes, new behavior and any change to the API; the Nuxt framework and SSR; Nuxt UI's
editor, chat and content components the screens do not need; metrics the existing API responses do not
support; production deployment (Telegram 38235).

## What the reviewer judges

- Normal use: every screen has the neutral template look of Telegram 38255 (IBM Plex, dark and light) and
  behaves exactly as before on phone and desktop.
- Threat model: a control library that loads icons or fonts from the network, writes inline styles the
  content security policy refuses, or changes what a screen sends to the API.
- Out of review scope (filed, not blocking): the visual taste of individual screens beyond the look of
  Telegram 38255.

## Notes

Nuxt UI is MIT, from NuxtLabs. Its icons are rendered from a local Iconify JSON collection registered at
start, so no request reaches the Iconify API; the IBM Plex faces stay on the Fontsource packages.

## History

2026-11-02: footprint extended by the lead (.veldo/shape_gate.py, its synced copy and suite 07's row). The
first gate of this branch failed suite 08's WARP-1012 AC6 row: shape_gate.run, given a named change set,
still read the branch's own git diff to choose the governing spec, so on any branch carrying exactly one
footprinted spec's proof the named set was judged against that spec. A named change set now supplies its
own evidence; the gate's own call, which names none, still reads git. Suite 07 proves both.

2026-11-01: AC2's visual criterion restated to the owner's newer style direction (Telegram 38255, 23:24Z): the
look of the nuxt-dashboard template's gallery (neutral surfaces, an icon rail sidebar that expands, a slim top
bar, segmented tabs, neutral buttons, 8px panels) replaces 38234's blue primary, palette and 14px corners. 38255
wins on look only; behavior, security, content, wrappers, the one theme preference, verification and the
screenshots stay as 38234 and 38235 ask. Nuxt UI's dashboard layout components were weighed for the shell and
not used: UDashboardGroup fixes the frame (fixed, overflow hidden) and UDashboardSidebar hides below 1024px and
replaces the phone's bottom bar with a slide-over, which would change the scrolling and the phone flow this
specification keeps; the rail is Veldo's shell restyled, its toggle a Nuxt UI button.

2026-11-01: footprint extended by the dependency check (engine/.veldo/control_api_ui.py, its synced copy and
suite 113's row): two Nuxt UI dependencies needed it. tslib is 0BSD (added to the allowed licenses), and
vaul-vue 0.4.1 publishes no license field although its repository is MIT; the check now admits a package
without a declared license only through a policy record of its exact version, an allowed license and the
evidence, and suite 113 proves an unrecorded one is still refused.

2026-11-01: acceptance criteria rewritten to the owner's full requirements (Telegram 38234 and 38235), which
supersede the first four; the reference screenshots the owner mentions did not reach the repository, so the
written visual direction governs.

2026-11-01: written and marked ready on the owner's decision (Telegram 38228 and 38229). The brief asked for
risk medium; the repository's tiers are low, standard, high and critical, and the footprint spans the
loop and distribution areas, which raises the tier to at least high (nothing may lower it), so it is
recorded as high.
