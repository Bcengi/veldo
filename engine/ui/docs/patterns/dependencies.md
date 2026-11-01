# Dependencies

Veldo's UI uses only public open-source packages from the npm registry, and writes all of its own
code. Nothing is copied or adapted from another company's product.

## Admitting a package

1. Take the version from the registry on the day: `npm view <package> version`, and its license:
   `npm view <package> license` (read the license file when the field says "SEE LICENSE").
2. Check the origin: the publisher and where it is developed. No Chinese-origin UI library.
3. Check the tier: a package whose vendor sells a paid tier of the same library is not admitted
   without a recorded owner decision.
4. Add the package to `dependency-policy.json` with `version`, `license`, `origin`, `tier` and
   `why`. Direct packages are listed by name; transitive packages are covered by the license allow
   list and the origin and tier deny lists, which the dependency-policy suite applies to every entry
   of `package-lock.json`.
5. Install with `npm install --save-exact`, so the lockfile and `package.json` agree exactly.

## The policy check

The VELDO-0145 Python suite (`scripts/suites/113_veldo_0145_ui.py`, row `ui/dependency-policy`) applies
`control_api_ui.dependency_problems` to `package-lock.json`, `package.json` and `dependency-policy.json`,
and fails when:

- a package in the lockfile has a license outside the allow list,
- a package matches the deny list (Chinese-origin UI libraries, packages with free and paid tiers),
  unless an owner decision names it,
- a direct dependency is missing from the policy or its version differs,
- (in the browser test `served assets`) a response comes from another origin or an asset is not a file
  of the build.

## Notes on choices

- **No component library.** PrimeVue was dropped (owner decision, VELDO-0145 round 2): only five of
  its components were used, unstyled, and its vendor runs free and paid tiers (version 5 under the
  commercial PrimeUI License, paid add-ons around version 4), which PLAN-0019 C16 forbids. The deny
  list now refuses `primevue` and `@primevue/*` at every version. The five controls are Veldo's own
  (`VButton`, `VTextField`, `VTextArea`, `VRadio`, `VSwitch`, see `docs/ui/`), built on native
  elements.
- **IBM Plex Sans and Mono** (Fontsource packages 5.3.0, OFL-1.1, IBM, United States) replace Big
  Shoulders and Atkinson Hyperlegible (owner, Telegram 37382 and 37384).
- **monaco-editor** is loaded only on the run screen, only when an edit is on screen, and with only
  its base editor worker. Its pinned `dompurify` is overridden to the fixed 3.4.17.
- **TypeScript 6.0.3, not 7.0.2.** The registry's latest is 7.0.2, the native port, which vue-tsc
  3.3.13 cannot load (it has no `lib/tsc` export); 6.0.3 is the latest release vue-tsc runs on.
- **One internal module replaced at build time** (`vite.config.ts`): Monaco's `domStylesheets`, by
  Veldo's own module with the same call shapes that writes CSS through the CSS object model. It is
  Veldo's code, not a copy of the original.
- **@tanstack/vue-table 9.3.1 and chart.js 4.6.1** (VELDO-0131, registry and origin checked 2026-11-01; evidence
  in proof/VELDO-0131/dependencies.md). Chart.js is used directly, without a wrapper.
- **Vue Flow is not admitted** (VELDO-0131): it cannot be installed without `@vueuse/core`, whose creator and
  leading maintainers are of Chinese origin; the deny list refuses `@vue-flow/*` and `@vueuse/*`, and the
  workflow canvas is Veldo's own SVG control. `shadcn`, `shadcn-vue` and `recharts` are denied by name.
