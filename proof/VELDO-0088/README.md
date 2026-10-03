# VELDO-0088 coordination and factory evidence

The continuation closes the four previously named integration gaps with real
production interfaces: factory dispatch from an accepted team assignment, a
builder fetching the referenced ticket, a distinct assigned review run,
graph-process capability attacks, and combined owner-answer plus engineering
completion input. Specification status remains ready, pending reviewer checks.

The fixture uses signed membership, project and team enrollment, accepted source
revisions and immutable snapshots, the installed LangGraph process, FactoryLoop
and Line, Runner, launch receiver, execution records, reservation settlement,
loopback owner presentation and settlement, document publication, backlog and
grooming commands, team assignment and MCP catalog writers. Fixture keys are
generated locally. FactoryLoop uses a constructed Service and Line; Line.run
builds from_line and all proposal owners. The protocol adapter mapping and account
selection are fixtures; the network authority daemon and account pool are not started.
The existing membership writer enrolls the service signing edge public key for
the PM and the separate factory service principal. PM proposals name the team
worker; journal and cycle receipts name the service. This requires that PM key
enrollment in an installation; changing the team roster does not grant a key.

Workers are generic protocol processes with predetermined output. They are not
Claude Code or Codex fakes and this is not live engine qualification. The builder
reads its accepted role's catalog selection, resolves the matching catalog record
exported by the real catalog writer, and invokes that fixture stdio server with a
tools/call request for BCG-123. The server records the request from that child.
The review is a separate assigned process using its own role configuration and
following the completed build. No live model, real credential or remote endpoint
was used, and no review verdict about this implementation is claimed.

## Criterion observations

| Criterion | Rows | Observed behavior |
| :--- | :--- | :--- |
| AC1 | cycle/runner, cycle/snapshot, cycle/no-action, cycle/failure, cycle/receipts | Ordinary coordination dispatch uses the PM role and immutable snapshot. Actual LangGraph traverses the default pipeline for proposal and empty outcomes; refusal is named. Every cycle receipt is compared with its store record, accepted source, snapshot inputs and watermark, workflow and dispatch reservation. |
| AC2 | proposal/unauthorized, proposal/stop-on-refusal, proposal/graph-process, cycle/waiting-release | Closed proposal handlers reject unauthorized operations and stop after owner refusal. Hostile nodes run in the LangGraph child: shell execution, SQL priority writes, store reads, invented roles and direct priority output are refused. The SQL target is a copy of the real writer-produced unit. A real owner request leaves an exited dispatch and retired worker reservation. |
| AC3 | cycle/serialized, cycle/pending-follow-up, cycle/combined-inputs, cycle/budget | One active cycle is enforced. A held PM run overlaps an accepted owner answer and a real reviewer completion; both change the input fingerprint, coalesce into one newer-snapshot follow-up, and cause no self-loop once consumed. The finite project cycle budget refuses another dispatch. |
| AC4 | unit/one-run-staging, unit/factory-builder-ticket, unit/independent-review | The factory starts the PM cycle for the admitted objective with exact text `please do BCG-123`. That coordination run publishes requirements, grooms and stages the unit with all four role references, marks elaboration done, and launches no extra elaboration run. The factory then dispatches the assigned builder, which fetches BCG-123, and one distinct assigned reviewer, with no idle PM rerun between them. The gate refuses a builder reviewing its own work. |

Twenty-one behavior names each report once. The shared suite preamble is separate.
The factory requires the existing account, project and unit spending policies;
fixtures configure them through the reservation service. Assignment consumption
does not confer unlimited spend or claim that an engineering exit proves landing.

## Authority and graph boundaries

Factory Line consumes accepted team assignments alongside the existing claim
path. Successful engineering completion that this line can advance itself does
not start another idle PM run; completion during an active PM run remains input
for its bounded follow-up. Accepted input members are retained in the receipt. Its build and review use the assignment's accepted role revisions and team
budgets. The gate binds the current assignment, team and active members; the
Runner carries that accepted authority and the dispatch writer rechecks it at
preparation and acceptance. Legacy claim dispatches retain their claim checks.
The footprint adds only the launch module and its engine copy to the prior scope.

The installed graph is trusted. Its node wrapper denies filesystem, process,
SQL and network audit events while a node executes, and the existing graph
response contract rejects invented authority outputs. This does not claim an
arbitrary Python-code sandbox against modification of the installed runtime.

## Red record and mutations

`red-at-24c0c90b.json` records all twenty-one current behavior rows red by assertion
against the unchanged archive before the original implementation. No row fails
by a fixture exception. The proof driver stays in this proof directory.

Finding 88 registers fifteen unique mutations with current diffs and hashes in
`mutations.json`. Controls cover inline coordinate reasoning through an in-process
model fixture instead of Runner dispatch, a graph node directly changing SQL
priority, discarded pending inputs, and an extra elaboration dispatch. Additional
controls cover allowed priority vocabulary, continuation after refusal, budget
bypass, omitted traces, ignored team assignments and a builder dispatched as its
own reviewer. No mutations were executed here; rejection results belong to the
reviewer. The inline control uses a deterministic model fixture, not a live model.

## Checks and scope

`checks.json` records normal and clean-environment scoped suites. Exit status 2
is the selftest command's successful partial-run status. The capability-configuration
suite reports two failures, live/claude and live/codex, because its live captures
are missing or stale. Its other rows pass. Refreshing those captures requires
the live model execution prohibited in this run. These results are not a
gate stamp or a completed proof manifest. The full selftest, gate, mutation runs,
live engine qualification and independent review of this implementation were
not performed. The owner reserved the first three checks for the reviewer and
prohibited live model execution in this run.

The required single-spec footprint checker compares against origin/main, so it
also reports the inherited VELDO-0151 changes in this branch. Those files were
not changed by this continuation. Checking the combined 0088 and 0151 footprints
reports none outside; checking changes since continuation head 925003f1 against
0088 alone also reports none outside. This discrepancy is recorded rather than
adding unrelated inherited files to the specification's footprint.

## Independent review follow-up

Five additional rows report once each in a fresh production fixture, whose
project budget is five cycles. This avoids expanding the retained snapshot
history merely to exercise another regression. The original sixteen rows keep
their original fixture and twelve-cycle budget.

| Row | Observation |
| :--- | :--- |
| review/pm-principal | Line.run constructs from_line, and the assignment writer records the team's PM as assigned_by while the service principal is distinct. |
| review/build-refusal | Missing adapters produce per-unit build refusals for both assigned units, without a factory fault; restoring the adapter launches both builders. |
| review/review-refusal | The same pass-level observation holds for independent review after real build completions. |
| review/pending-budget | A real accepted owner answer remains pending during the last allowed PM run; completion records the budget refusal without a factory fault or another cycle. |
| review/current-publication | A document publishing a new unit but naming the earlier READY assigned unit is refused without elaboration done; a matching subsequent publication succeeds. |

The five corrections have separate finding-88 mutations. Their replacements
have unique anchors; execution and rejection results remain reviewer-owned.
`red-at-1773b279.json` selects these five new regression rows against the unchanged
reviewed head. The full red record remains against the original implementation
base. `review-checks.json` records the current scoped checks and their limitations.

The current review checks supersede the earlier compatibility observations above
for the suites rerun here. All twelve direct service-consumer suites pass both
normally and in the requested fresh gate environment, run sequentially. The
collector's complete names, summaries and durations are in `review-checks.json`.
The 0088 suite has twenty-one behavior rows and twenty-six shared preamble rows.
Each scoped run exits with the intentional partial-run status, not a gate stamp.

Validation passes, the Git boundary passes, and the anchor check reports zero
bad anchors. `review-static-checks.json` records those results and the footprint
limitation: the supplied single-spec command compares against origin/main and
flags inherited 0151 files. The combined 0088 and 0151 footprint is clean, as is
the 0088-only review diff from 1773b279. No unrelated inherited file was changed
to satisfy that checker. No mutation execution, full selftest, gate, model,
remote service, push or independent approval was performed in this follow-up.

## Production setup follow-up

The default PM is enrolled during owner-run factory setup with the service journal
key, through the same signed membership command and possession co-signature used
for other service members. Setup republishes the verification-key projection.
The team writer remains unable to grant membership. The footprint adds setup and
its engine copy because enrollment belongs at that production boundary.

| Row | Observation |
| :--- | :--- |
| followup/setup-pm | Fresh production setup, then real project and team commands and Line.run accept an assignment signed as the default PM. This fixture branch never enrolls the PM itself. |
| followup/setup-pm-authority | The setup-enrolled PM is refused with missing_authority when recording a Runner reservation or reporting an account limit window; neither changes the protected state. The service principal succeeds with the same operations and valid inputs. |
| followup/initial-fault | An injected RuntimeError from starting a real project's next cycle reaches the pass_once caller unchanged. |
| followup/pending-fault | A real owner answer changes input during a dispatched cycle; after completion, an injected follow-up start fault reaches the caller unchanged. |

The original fixture remains for the earlier rows. The setup row uses generated
owner keys, a fresh store, inert installation engine bytes, scratch install paths
and a local manager stand-in. No model or external channel is contacted.
Three additional finding-88 mutations remove setup enrollment or broaden each
scheduler catch. The existing budget-refusal mutation now targets except Refused.
Mutation execution remains reviewer-owned.

`red-at-37dcd381.json` runs only these three follow-up rows against the unchanged
pre-fix archive; all three fail by assertion, with no fixture exception.
`followup-checks.json` records the sequential scoped runs in normal and clean
gate environments. Each successful scoped run has the required partial-run exit
status, not a gate stamp. `followup-static-checks.json` records the final validators.

The single-spec footprint checker still includes inherited VELDO-0151 changes
because its comparison starts at origin/main. The combined 0088/0151 check has
no outside paths, and `followup-scope.json` separately shows that this follow-up
from 37dcd381 stays entirely within 0088. No inherited footprint was expanded.

The completed follow-up checks pass for 0088, factory setup (0139), standing
delegation (0140), setup API (0171), setup assets (0186) and engine upgrade (0189)
in both environments. The text suite (0168), which inventories setup send sites,
passes its inventory row but fails intake/delivery in both environments. An
unchanged archive of 37dcd381 fails that identical assertion. This pre-existing
failure is recorded in followup-checks.json and was not changed under 0088.
Validation and the Git boundary pass; the final anchor check reports zero bad
anchors. All eighteen finding-88 mutation diffs are current, including the three
new follow-up mutations. No mutation rejection result is claimed without the
reviewer's run.


### PM enrollment role follow-up

Setup now enrolls the PM with `roles: []`, retaining the journal key and `scope: '*'`.
The PM can still author proposals and assignments, but cannot record Runner
reservations or report account limit windows. Suite preparation uses the service
principal for reservation policy configuration.

`role-checks.json` records the new `followup/setup-pm-authority` row failing with
the old role (50 passed, 1 failed), with `followup/setup-pm` still passing. After
the fix, suite 92 passes 51 checks and factory setup suite 73 passes 43 checks,
with no failures. The suites ran alone and sequentially; successful partial runs
return 2 by design. No gate stamp is claimed.

Finding 88 registers `v88-setup-pm-service-role`, restoring `reservation_service`
and targeting the new row. Its diff and digests are in `mutations.json`; the
existing setup-enrollment mutation digests are refreshed for the new source.
No mutation driver was run; mutation execution remains reviewer-owned.

### Bounded cycle-budget mutation fixture

The `cycle/budget` row now drives at most the remaining project allowance plus
one attempt. Its graph fixture returns a deterministic named refusal before any
external graph or worker launch. It still calls the production `ProjectCycles.start`
and signed receipt writers: admitted failed cycles consume the project budget,
and the next attempt must raise `budget_exceeded:coordination`. The row asserts
the exact final receipt count and that no worker was launched. With the budget
predicate bypassed, the finite drive records one excess cycle and the named row
fails by assertion. The other rows still exercise real graph and worker runs.

The review fixture retains its separate `review/pending-budget` assertion. If a
defect admits its follow-up, cleanup waits for that finite set of workers and
finishes their receipts without driving another scheduler pass. The redundant
budget probe whose row was not selected in review mode is removed.

`budget-checks.json` records the final scoped suites and a targeted injection of
the exact registered `v88-ignore-cycle-budget` replacement, obtained by parsing
the registry rather than executing its driver. The mutant completed in 75.45s
with 49 checks passing and exactly `cycle/budget` and `review/pending-budget`
failing by assertion; it neither timed out nor raised a fixture exception. The
temporary replacement was mirrored into the engine copy and both originals were
restored in `finally`. No production change, Runner timeout increase, mutation
registration change, or live capture change is included in this repair.

The suites use the owner's clean environment; the targeted mutation run also
sets `PYTHONUNBUFFERED=1` for progress output. Full finding-88 mutation execution
is still reserved for the reviewer by the owner's token rules. This proof does
not claim rejection results for the other registered mutants or a gate pass.

## Gate regression repair at e3325634 (2026-10-03)

Implementation commit: `e3325634f8147ae1a330f1ca05dfd75b337b748c`.
[gate-regressions.json](gate-regressions.json) records the clean environment,
serial wall-clock measurements, scoped summaries, failing rows, diagnostic
observations, implementation digests and validation results. This is diagnostic
subset evidence, not passed unit evidence, a green gate or a landing decision.
No timeout, mutation budget, heartbeat window or existing assertion was relaxed.

Causes below name lines at the failing `07008bc1` tree. Every fix is in
`e3325634`; the older architecture and decision assertions are unchanged.

| Failing row | Branch cause | Fix and observed evidence |
| :--- | :--- | :--- |
| architecture/snapshot-in-memory | `.veldo/control_eligibility.py:796` loaded the entire PM module on every read; `.veldo/control_workflow_cycle_pm.py:25-29` loaded its command-owner dependencies. | Move assignment reads/checks to `control_workflow_cycle_assignment.py`, load the parser-free helper at eligibility initialization, and continue reading current authority records on every decision. The baseline observed 882 disk module loads during the watched window; the unchanged row now proves zero loads, no scratch writes and correct held-byte digests. |
| architecture/identity-keyed-by-module | The same `Gate.read` import reached the parser outside the architecture snapshot. The fixture parser's relative module load then left empty validator records and the wrong decisions. | The same helper separation restores both named parser identities, role labels, durable observations and expected refusals, as asserted by the unchanged row. |
| decisions/minor-shapes | The repeated imports at `.veldo/control_eligibility.py:796` made the suite outlast the 90-second claim heartbeat window (`.veldo/claim.py:52`). | Remove that repeated work. Baseline diagnostics show `VELDO-9401` incorrectly held by `missing_authority:claim`; all malformed-record refusals were already correct. The unchanged row now passes without changing claim age or fixture timestamps. |
| decisions/deep-blocks-named | The same delay expired the healthy control unit's claim before this later region. | The same fix restores the healthy control unit; the 5000-deep malformed-block refusal and named unexpected-verifier error remain asserted and pass. |
| acceptance/signers | `.veldo/authority_contract.py:51` added `reservation_service`, while `scripts/suites/68_veldo_0134_acceptance.py:338-342` still enumerated seven roles. | Extend the exhaustive matrix with `reservation_service: False`; actually sign and submit that case and require the role refusal with unchanged store state. AC1 requires Runner dispatch (spec lines 85-89), and the spec's integration prerequisite at lines 242-246 explicitly requires enrolling this existing reservation role. No architecture-acceptance permission changes. |
| census/writers | `.veldo/control_workflow_cycle_pm.py:407` invoked `getattr(service, method)`, which the complete writer census could not resolve. | Explicit `service.publish(packet)` / `service.apply(packet)` calls preserve the closed handler registry and owner checks. The unchanged census and all planted-writer controls now pass. |

All `.veldo` changes have byte-identical `engine/.veldo` copies. The new helper is
registered in `init_scaffold.py` and in suite 92's production-file map; the team
reader delegates to that helper so assignment enumeration still has one source.
`.veldo/control_launch.py` and its engine copy are unchanged from `07008bc1`.

Serial wall times in seconds (including the shared preamble and dispatcher):

| Suite | Main 352df040 | Before 07008bc1 | After e3325634 | Suite rows after |
| :--- | ---: | ---: | ---: | ---: |
| 60_veldo_0053_architecture | 3.221 | 36.272 | 3.150 | 39 |
| 62_veldo_0054_decisions | 5.205 | 152.216 | 5.448 | 39 |
| 68_veldo_0134_acceptance | 1.942 | 1.887 | 1.988 | 27 |
| 84_veldo_0169_project_handouts | 12.803 | 13.134 | 12.817 | 27 |

Additional scoped checks: `92_veldo_0088_pm_cycles` has 25 passing rows in
69.857 seconds; `50_git_environment` has four in 2.309 seconds. Every after-run
has zero failed assertions and exits 2, the required PARTIAL refusal to claim a
gate pass. Main has no suite 92. Validation (`python3 .veldo/validate.py all`)
exits 0; engine sync exits 0 with 251 pairs compared, six declared per-repo and
131 engine-only files.

The first branch-62 reproduction took 148.085 seconds, matching the reviewer's
148-second report. An initial main-62 measurement was accidentally started
before that branch run finished; both measurements are excluded from the table.
Both were rerun serially. Temporary diagnostic prints on the baseline's existing
failure paths captured the causes; no assertions or production bytes changed.
Main and baseline comparisons used archive exports, never another worktree.

Suite 62 is now about 28 times faster and architecture about 12 times faster,
back near main's measurements. The common repeated-import path affected every
ordinary eligibility read, not just these rows. These observations explain a
substantial branch regression but do not establish a new full-gate duration.
The 1800-second first-use run and mutation baseline deadline remain for the
reviewer to verify. Neither full selftest nor either mutation checker nor
`scripts/verify.sh` was run here.
