# VELDO-0131: dependency provenance (taken 2026-11-01)

Every package this ticket adds to engine/ui, checked on 2026-11-01 from the npm registry (`npm view`), the
maintainer's GitHub account or organization (`gh api users/<owner>`) and the project's own site for tiers. The
raw answers are in [dependencies.json](dependencies.json). The UI's `dependency-policy.json` records each direct
package with its version, license, origin, tier and why, and suite 120 (rows ac4/dependency-policy and
ac4/stack) applies VELDO-0145's `control_api_ui.dependency_problems` to the lockfile.

## Admitted

| Package | Locked | Registry latest | License | Origin | Tier |
|---|---|---|---|---|---|
| @tanstack/vue-table (direct) | 9.3.1 | 9.3.1 | MIT | TanStack organization (github.com/TanStack/table), created and led by Tanner Linsley, Utah, United States | None. tanstack.com's tenets page states "paid tiers none"; TanStack sells private consulting and support, not a tier of the library |
| @tanstack/table-core | 9.3.1 | 9.3.1 | MIT | TanStack, as above | None |
| @tanstack/store | 0.11.2 | 0.11.2 | MIT | TanStack, as above | None |
| chart.js (direct) | 4.6.1 | 4.6.1 | MIT | Chart.js organization (github.com/chartjs/Chart.js), community maintained | None; the site offers no paid product |
| @kurkle/color | 0.3.4 | 0.6.5 | MIT | Jukka Kurkela (github kurkle, Finland), a Chart.js maintainer | None |

`@kurkle/color` is locked at 0.3.4, not the registry's 0.6.5, because chart.js 4.6.1 asks for `^0.3.0`.

## Considered and not admitted

| Package | Why |
|---|---|
| @vue-flow/core 1.48.2 (MIT, Burak Cakmakoglu, Hamburg, Germany) | Its dependencies include `@vueuse/core` (`^10.5.0`); it cannot be installed without it. The site also asks visitors to support Webkid by subscribing to React Flow Pro (a paid product of the React library's company). The workflow canvas is Veldo's own Vue SVG control instead (`src/features/workflow/FlowCanvas.vue`), as the owner's rule for a failing library allows. |
| @vueuse/core 15.0.0 (MIT, vueuse organization) | Chinese origin: created and led by Anthony Fu (1706 commits), with the next leading contributors okxiaoliang4 and webfansplz (Chinese developers); see dependencies.json. Denied in the policy as `@vueuse/*`. |
| vue-chartjs 5.3.4 (MIT, Jakub Juszczak, account apertureless) | Not needed: Chart.js is used directly by one small component (`src/features/usage/UsageChart.vue`), which is smaller than adding a wrapper package. |
| recharts, shadcn, shadcn-vue | Explicitly rejected by AC4; denied by name in the policy. |

## Unchanged from VELDO-0145

Vue 3.5.44, vue-router 5.4.0, Pinia 4.1.0, Vite 8.3.5, TypeScript 6.0.3, Tailwind CSS 4.3.3, monaco-editor 0.57.0
and the IBM Plex fonts keep VELDO-0145's recorded evidence (its dependency-policy.json entries).

## Check today

```
$ python3 -I -c "...control_api_ui.dependency_problems(lock, policy, package)"
[]
```
(suite 120 row ac4/dependency-policy, green in suite120-green.log; red under the falsifier
ui131-tiered-dependency-locked, which puts ag-grid-enterprise, a library with free and paid tiers, in the
lockfile; see falsifiers-red.log.)
