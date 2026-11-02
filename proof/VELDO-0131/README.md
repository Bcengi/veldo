# VELDO-0131: the Veldo factory UI on phone and desktop

Status after fix round 3 (owner approval, Telegram 38184): see the round 3 section below and [OPEN.md](OPEN.md).
Round 2's three waiting controls work: backlog priority save, worker stop and the run cap are authority
commands reached only through the authenticated API. Round 2's status (REMAINING on those three) is in git
history at 6727193e.

## Spec amendment (2026-11-01)

The amendment covers two changes, recorded in the spec's "Amendment 2026-11-01" section. (a) The stack in AC4,
the Notes, Allowed dependencies and the spend and editor rows moves from React to the owner's Vue stack. Vue Flow
was not admitted (it requires @vueuse/core, of Chinese origin), so the canvas is Veldo's own Vue control.
(b) The backlog row gains desktop drag-and-drop reorder, and keyboard and touch reorder stay. No other
acceptance text changed.

## Fix round 3 (owner, Telegram 38184)

The owner widened the footprint to the engine files OPEN.md lists, for exactly three commands. Each is the engine's
own writer, reached only through the authenticated API (`work` route family), with the existing commands' edge
signing, refusal classes, journal record (the session's member is the journal actor) and observations.

| Control | Route | Command | Accepted | Stale | Unauthorized |
|---|---|---|---|---|---|
| Save priority order (backlog) | `backlog.reprioritize` {item, item_version, rank} | control_backlog's reprioritize, the api edge's signature verified there again (`_api_edge`) | new rank, item at its next version, record names channel api and the assertion digest | `stale_version`, beside Save | `unauthorized:not_owner:project`, `:not_authorized:role`, beside Save |
| Stop (workers) | `workers.stop` {dispatch, dispatch_version} | control_dispatch's `request_stop`, then the runner's `honor_stops` asks the receiver (Launch.stop) and records `stop_result` | request on the dispatch, state unchanged; the card shows it from the record | `stale_version`, beside the card | `unauthorized:not_authorized:role` or `:scope`, beside the card |
| Save cap (workers, Run caps by account) | `workers.cap` {account, account_version, concurrency} | control_accounts' `cap` | concurrency at the record's next version, change kept in `concurrency_history` | `stale_version`, beside the control | `unauthorized:missing_authority:scope` or `missing_authority` |

Falsifiers: 19 of 19 proven ([falsifiers.json](falsifiers.json), [round3-falsifiers-red.log](round3-falsifiers-red.log)):
baselines and restored runs of suites 120, 73, 62, 71 and 75 green, each of the 19 mutants red on its target row.
The driver now runs a baseline and a restored run per suite (falsifiers.py). The runs span commits f42dafee to
981db41f, which differ only in proof files. Round 2's receipt is kept as round2-falsifiers.json.

Neighbors run this round (logs `round3-suite-<name>.log`), green: 113 (7), 118 (7), 119 (10), 104, 82_0144, 94, 93,
85_0158, 82_0141, 85_0171, 117, 76, 113_0112 (its client inventory now drives the two new dispatch entrypoints),
67_0041, 78_0160, 83_0154, 65, 82_0129, 83_0166, 92_0088, 105. Red: 86_0127 on its two live-capture rows only,
because they bind control_launch.py's digest (OPEN.md, REMAINING 3). VELDO-0145's layout spec: 10 of 10
([round3-layout145-e2e.log](round3-layout145-e2e.log)).

Rows (all green on this tree, logs `round3-*`):

| Suite | New rows | Result |
|---|---|---|
| 71 (API) | work/backlog-reprioritize, work/worker-stop, work/worker-cap; route family and AC4 contract now name the routes | 45 rows green ([log](round3-suite-71_veldo_0130_api.log)) |
| 73 (backlog) | priority/owner-reprioritize (own signature accepted, stale, not the owner; edge packets of another operation, another command, an unenrolled edge refused unauthenticated) | 21 rows green |
| 62 (dispatch) | dispatch/owner-stop (a real receiver and worker: request refused stale, outside scope and without the role; accepted; the runner's sweep asks the receiver, the worker ends, the result is journaled; an ended run is not stopped again) | 23 rows green |
| 75 (accounts) | accounts/owner-cap | 24 rows green |
| 120 (UI) | ac2/priority-save, ac2/worker-stop, ac2/worker-cap (each: unauthorized, stale with the page's stream held, accepted), replacing ac2/pending-actions | 26 rows green ([log](round3-suite120-green.log)) |

## What was built, by screen row

| Row | Route | Built |
|---|---|---|
| Objectives and projects | `/projects`, `/projects/<p>` | Searchable list, objective evidence and status, project detail, and the message box beside it (to `messages.send`). Phone: cards, a full-width detail, a persistent Message button and a chat sheet |
| Backlog and nested units | `/backlog` | TanStack Table (`@tanstack/vue-table`) item-to-unit hierarchy with priority and blockers. Desktop drag and drop, plus Move up / Move down by keyboard (Enter, Alt+Up/Down) and touch. Detail panel on desktop, sheet on phone. Save maps the order to ranks and sends each through `backlog.reprioritize` at the version read; a refusal is named beside Save (round 3) |
| Workers per machine | `/workers` | Linux and Mac groups, host labels, worker cards with capability, activity and account; Stop with an inline confirmation sent to `workers.stop`, the stop shown from the dispatch record; Run caps by account with Save cap sent to `workers.cap` (round 3; a machine's own cap waits on VELDO-0125, OPEN) |
| Live agent run | `/runs/<dispatch>` | VELDO-0145's terminal, checked at all four widths (ac1) and fed live (ac2/live) |
| Pending decisions | `/decisions/<request>` | VELDO-0145's inline answer, checked at all four widths (ac1, carries the AC1 falsifier), with settlement and refusals (ac2) |
| Gate and review | `/proof` | Check table (cards on phone), findings, proof links, and Monaco manifest and gate-output panes with old/new/changes selection and a wrap switch |
| Usage over time | `/usage` | Chart.js time series by unit, with unknown amounts never shown as zero. Breakdown by provider, account, project and run; each account's provider, label and status from its record; windows, reset times, active runs and "No account until". Touch, click or keyboard selection of hours |
| Team and configuration | `/configuration` | Role table of every stored capability configuration (named by a team or not) with revision history and exact tools, servers and skills; every stored skill. Teams with version and pending proposal. Opens VELDO-0163's forms |
| MCP servers and credentials | `/catalog` | Table of the whole catalog (`mcp.list`) with revision history, transport, hosts, read-only tools and each credential's label, set at and set by from its record; a Credentials section of every record. No value is served or shown. Opens VELDO-0159's form |
| Repositories and identities | `/repositories` | Read-only (`repositories.read`): Git identities (label, author, remote owner, projects root, default visibility) and repositories (identity, path, remote, origin, state with its named reason). Tables on desktop, cards on phone. No credential reference is served |
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
| AC1 (round 2) | ac1/repositories | `ui131-identities-dropped`: the identities are not listed | ac1/repositories (and unit/factory, ac2/metadata-only) |
| AC1 (round 2) | ac1/every-configuration | `ui131-configurations-team-named-only`: stored configurations are not listed | ac1/every-configuration (and unit/factory) |
| AC1 (round 2) | ac1/whole-catalog | `ui131-catalog-first-server-only`: the catalog lists one server | ac1/whole-catalog (and unit/factory) |
| AC1 (round 2) | ac1/whole-catalog | `ui131-credential-metadata-dropped`: credential records are not listed | ac1/whole-catalog (and unit/factory, ac2/metadata-only) |
| AC1 (round 2) | ac1/usage-provider | `ui131-provider-unread`: the account records are not read | ac1/usage-provider (and unit/factory) |
| AC1 (round 2) | ac1/worker-capability | `ui131-capability-dropped`: a worker's capability is not shown | ac1/worker-capability |
| AC2 (round 2, retargeted in round 3) | ac2/worker-stop | `ui131-stop-shown-unsent`: Stop reports a stop it never sent | ac2/worker-stop (and unit/factory) |
| AC2 (round 2, retargeted in round 3) | ac2/priority-save | `ui131-priority-shown-unsent`: Save reports ranks it never sent | ac2/priority-save (and unit/factory) |
| AC1/AC2 (round 3) | ac2/worker-cap | `ui131-cap-shown-unsent`: Save cap reports a cap it never sent | ac2/worker-cap (and unit/factory) |
| AC2 (round 3) | 73 priority/owner-reprioritize | `backlog131-edge-command-underived` (control_backlog.py): the edge's signature stands for a command the assertion does not derive | priority/owner-reprioritize |
| AC2 (round 3) | 62 dispatch/owner-stop | `dispatch131-stop-any-scope` (control_dispatch.py): a stop from an owner outside the run's project | dispatch/owner-stop |
| AC2 (round 3) | 62 dispatch/owner-stop | `launch131-stop-recorded-unasked` (control_launch.py): the ask recorded, the receiver never asked | dispatch/owner-stop (and service-principals-only) |
| AC2 (round 3) | 71 work/worker-stop | `api131-stop-asked-before-record` (control_api_authority.py): the receiver asked before the request is recorded | work/worker-stop |
| AC2 (round 3) | 75 accounts/owner-cap | `accounts131-cap-any-scope` (control_accounts.py): a one-repository owner caps a factory account | accounts/owner-cap |
| AC2 (round 2) | ac2/metadata-only | `api131-identity-credentials-served` (control_api_models.py): an identity's credential references served | ac2/metadata-only |

Round 2: suite 120 has 24 rows, all green ([round2-suite120-green.log](round2-suite120-green.log)). The whole UI
has 118 Vitest tests in 28 files, all green; there are 20 Playwright browser tests in factory.spec.ts.

Falsifiers: [falsifiers.json](falsifiers.json) and [round2-falsifiers-red.log](round2-falsifiers-red.log), all at
commit 9281411c. The baseline is green, each of the 13 mutants is red on its target row, and the restored run is
green: 13 of 13 proven. (Round 1's 4 of 4 are in [falsifiers-red.log](falsifiers-red.log).) They were driven by
the teeth driver's own worker outside the confinement ([falsifiers.py](falsifiers.py)), because the
coordinator's confined leg cannot install the UI's dependencies or run Chrome
([coordinator-confined-baseline-refused.log](coordinator-confined-baseline-refused.log)). The proposed
unconfined entry is in OPEN.md A.

Round 2 neighbors (logs `round2-suite-<name>.log`), all green: the API suites whose files changed, 71 (42 rows),
104 (19), 82_0144 (29), 94 (26), 93 (24), 85_0158 (23), 82_0141 (40), 85_0171 (18), 117 (7); suites 113 (7), 118
(7) and 119 (10); VELDO-0145's layout spec, 10 of 10 ([round2-layout145-e2e.log](round2-layout145-e2e.log)).

Round 1 neighbors: suites 113 (7 rows), 118 (7) and 119 (10) are green
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
