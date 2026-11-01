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
      Nuxt UI 4.12.0 (exact pin, MIT, NuxtLabs) is installed through its Vite plugin in the existing Vue 3
      + Vite app (no Nuxt framework, no SSR). Veldo's own form and display controls (engine/ui/src/components
      VButton, VTextField, VTextArea, VSwitch, VRadio, StatePanel and the like, plus tabs, modals, toasts,
      badges, menus and tables where the screens have them) are replaced by the Nuxt UI components. Nuxt
      UI's own dependencies are approved by the owner's dependency rule (Telegram 28929: dependencies of
      software we pick are approved automatically, pinned exactly and recorded). The origin, license and
      version evidence for Nuxt UI is in proof/VELDO-0229/.
    falsified_by: >
      A Veldo V* control left in a screen, or @nuxt/ui missing from the lockfile or not exactly pinned; the
      suite 120 ac4/stack row must fail.
  - id: AC2
    text: >
      Behavior is unchanged: the same routes, API calls, refusals, accessibility (the axe checks) and phone
      layouts. Every existing UI check passes: suites 113, 117, 118, 119 and 120, the VELDO-0145 layout
      spec and the unit tests.
    falsified_by: >
      Any row of suites 113, 117, 118, 119 or 120, any test of the VELDO-0145 layout spec, or any unit test
      failing on the moved UI.
  - id: AC3
    text: >
      The look keeps Veldo's identity on Nuxt UI's theme: Veldo's fonts (IBM Plex) and palette from
      engine/ui/src/styles/tokens.css mapped onto Nuxt UI's primary and neutral colors, dark and light
      both. The built UI makes no runtime request off the machine: icons are bundled from a local
      collection (no Iconify API) and fonts stay local (no font CDN, @nuxt/fonts off).
    falsified_by: >
      A built asset that names the Iconify API host or a font CDN, or a browser test that sees a response
      from another origin; the suite 120 ac2/api-only row must fail.
  - id: AC4
    text: >
      Screenshots: PNGs of these screens against the factory harness, dark and light, desktop 1440x900,
      plus Overview and Backlog on a 390x844 phone in dark: Sign in, Overview, Backlog, Workers, Decisions,
      Role, Team, Configuration, Usage. In proof/VELDO-0229/screens/ with an index.md naming each.
    falsified_by: >
      A named screen without its PNG in proof/VELDO-0229/screens/ or without its line in the index.
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change: the UI returns to Veldo's own controls on native elements; the API, its routes and
  every stored record are untouched by this specification.
---

## Intent

The owner wants Veldo's web UI built on a real component library rather than Veldo's own controls:
"for veldo, let's do nuxt ui" (Telegram 38228), with screenshots once it is integrated (Telegram 38229).

## Context

VELDO-0145 built the shell, run terminal and decisions on Vue 3 + Vite with Veldo's own controls on
native elements after PrimeVue was dropped; VELDO-0159, VELDO-0163 and VELDO-0131 added the server form,
the role and team forms and the factory screens on the same controls. Nuxt UI runs in a plain Vue + Vite
app through its Vite plugin, so the stack keeps Vue, Vite, Tailwind 4, Pinia, vue-router, Monaco,
Chart.js and TanStack Table, and the controls move onto Nuxt UI. Its dependencies include @vueuse/*,
which VELDO-0131 had rejected; the owner's dependency rule (Telegram 28929) approves the dependencies of
software he picks, so the amendments of VELDO-0131 and VELDO-0145 on this date lift that rejection.

## Out of scope

New screens, new routes, new behavior and any change to the API; the Nuxt framework and SSR; Nuxt UI's
editor, chat and content components the screens do not need.

## What the reviewer judges

- Normal use: every screen looks like Veldo (IBM Plex, the blue palette, dark and light) and behaves
  exactly as before on phone and desktop.
- Threat model: a control library that loads icons or fonts from the network, writes inline styles the
  content security policy refuses, or changes what a screen sends to the API.
- Out of review scope (filed, not blocking): the visual taste of individual screens beyond keeping
  Veldo's identity.

## Notes

Nuxt UI is MIT, from NuxtLabs. Its icons are rendered from a local Iconify JSON collection registered at
start, so no request reaches the Iconify API; the IBM Plex faces stay on the Fontsource packages.

## History

2026-11-01: written and marked ready on the owner's decision (Telegram 38228 and 38229). The brief asked for
risk medium; the repository's tiers are low, standard, high and critical, and the footprint spans the
loop and distribution areas, which raises the tier to at least high (nothing may lower it), so it is
recorded as high.
