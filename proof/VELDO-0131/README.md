# VELDO-0131: the Veldo factory UI on phone and desktop

Status: REMAINING. Every acceptance criterion's check and falsifier is built and proven, and every screen row
is built except "Repositories and identities", which needs an API read model outside this footprint. The
API-side halves of backlog priority save and worker stop are also missing. See [OPEN.md](OPEN.md).

## Spec amendment (2026-11-01)

The amendment covers two changes, recorded in the spec's "Amendment 2026-11-01" section. (a) The stack in AC4,
the Notes, Allowed dependencies and the spend and editor rows moves from React to the owner's Vue stack. Vue Flow
was not admitted (it requires @vueuse/core, of Chinese origin), so the canvas is Veldo's own Vue control.
(b) The backlog row gains desktop drag-and-drop reorder, and keyboard and touch reorder stay. No other
acceptance text changed.

## What was built, by screen row

| Row | Route | Built |
|---|---|---|
| Objectives and projects | `/projects`, `/projects/<p>` | Searchable list, objective evidence and status, project detail, and the message box beside it (to `messages.send`). Phone: cards, a full-width detail, a persistent Message button and a chat sheet |
| Backlog and nested units | `/backlog` | TanStack Table (`@tanstack/vue-table`) item-to-unit hierarchy with priority and blockers. Desktop drag and drop, plus Move up / Move down by keyboard (Enter, Alt+Up/Down) and touch. Detail panel on desktop, sheet on phone. Save names the API gap (OPEN 2) |
| Workers per machine | `/workers` | Linux and Mac groups, host labels, worker cards with activity and account, and an inline stop confirmation with its result (the API gap, OPEN 3) |
| Live agent run | `/runs/<dispatch>` | VELDO-0145's terminal, checked at all four widths (ac1) and fed live (ac2/live) |
| Pending decisions | `/decisions/<request>` | VELDO-0145's inline answer, checked at all four widths (ac1, carries the AC1 falsifier), with settlement and refusals (ac2) |
| Gate and review | `/proof` | Check table (cards on phone), findings, proof links, and Monaco manifest and gate-output panes with old/new/changes selection and a wrap switch |
| Usage over time | `/usage` | Chart.js time series by unit, with unknown amounts never shown as zero. Breakdown by account, project and run; windows, reset times, active runs and "No account until". Touch, click or keyboard selection of hours |
| Team and configuration | `/configuration` | Role table with revision history and exact tools, servers and skills. Teams with version and pending proposal. Opens VELDO-0163's forms |
| MCP servers and credentials | `/catalog` | Catalog table with revision history, transport, hosts, read-only tools and credential references (label, set at and set by for this session's writes). Opens VELDO-0159's form |
| Repositories and identities | none | NOT BUILT: no API read model (OPEN, REMAINING 1) |
| Workflow editor | `/workflows/<w>` | Veldo's own SVG canvas (pan, zoom, drag, arrow keys), palette, property sheet, an ordered step and transition list (select, connect, reorder), and version and save state. Saves through `workflows.save` and runs nothing |

Every factory screen follows the journal through `events.stream` and re-reads its model (`useLiveRead`), showing
the read's journal sequence, freshness and time. Rail entries are added for desktop and a Factory section on the
You screen for phone.

## Acceptance criteria and their checks (suite 120)

| AC | Rows | Falsifier (mutant) | Red under it |
|---|---|---|---|
| AC1 | ac1/screens-360, -390, -1280, -1440: every screen in loading, empty, error and populated states, plus sheets, the live run and the decision. Checks page-wide overflow, overlaps, primary action visible, unclipped and uncovered, 44 px on phone, axe (wcag2a/aa, serious and critical) at 390 and 1280, and no CSP violation | `ui131-decision-action-hidden-360`: the decision's Send answer is hidden at 360 px | ac1/screens-360 |
| AC2 | ac2/live (assignment, step and tool call, stop, gate and review, completion, all live), ac2/completion-receipt, ac2/message-intake, ac2/decision-settlement, ac2/refusals (unauthorized:out_of_scope beside the action, a workflow outside scope), ac2/api-only | `ui131-completion-from-build-state`: completion shown from the unit's COMPLETED state before the landing receipt | ac2/completion-receipt (and ac2/live, unit/factory) |
| AC3 | ac3/keyboard-desktop, ac3/touch-phone, ac3/stale-save | `ui131-node-settings-hover-only`: a workflow step's settings shown only on hover | ac3/keyboard-desktop, ac3/touch-phone (and ac1 rows) |
| AC4 | ac4/dependency-policy, ac4/stack, ac4/served-assets, plus ac2/api-only for origins | `ui131-tiered-dependency-locked`: ag-grid-enterprise (free and paid tiers) in the lockfile | ac4/dependency-policy |

Suite 120 has 17 rows, all green ([suite120-green.log](suite120-green.log)). Its unit row runs 31 Vitest tests in
9 files; the whole UI has 109 tests in 26 files, all green. There are 13 Playwright browser tests.

Falsifiers: [falsifiers.json](falsifiers.json) and [falsifiers-red.log](falsifiers-red.log). The baseline is
green, each mutant is red on its target row, and the restored run is green: 4 of 4 proven. They were driven by
the teeth driver's own worker outside the confinement ([falsifiers.py](falsifiers.py)), because the
coordinator's confined leg cannot install the UI's dependencies or run Chrome
([coordinator-confined-baseline-refused.log](coordinator-confined-baseline-refused.log)). The proposed
unconfined entry is in OPEN.md A.

Neighbors on this tree: suites 113 (7 rows), 118 (7) and 119 (10) are green
([suite113-green.log](suite113-green.log), [suite118-green.log](suite118-green.log),
[suite119-green.log](suite119-green.log)). VELDO-0145's browser layout spec is green: 9 rows
([layout145-e2e.log](layout145-e2e.log)), plus served assets against `engine/ui/dist`
([layout145-served-assets-green.log](layout145-served-assets-green.log)). In the first log, the served-assets
failure was that run serving a build outside `engine/ui/dist`.

## Dependencies

[dependencies.md](dependencies.md) and [dependencies.json](dependencies.json): `@tanstack/vue-table` 9.3.1 and
`chart.js` 4.6.1 are admitted (MIT, TanStack in the United States, the Chart.js organization and a Finnish
maintainer, no paid tiers). `@vue-flow/core`, `@vueuse/*`, `vue-chartjs`, `recharts` and `shadcn` are not
admitted, with the reasons recorded.

## Screenshots

[screens/](screens/): `<width>-<screen>.png` at 360, 390, 1280 and 1440 px for every populated screen and
sheet, taken by the ac1 rows with `VELDO_0131_SCREENS` set.

## Run

```
python3 scripts/selftest.py --suite 120_veldo_0131_factory_ui
python3 proof/VELDO-0131/falsifiers.py baseline | mutant <case> | restored
```
On the shared host, run both under the gate lock (`flock <gate lock> systemd-run --user ... --wait --collect`).
