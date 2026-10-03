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
| followup/initial-fault | An injected RuntimeError from starting a real project's next cycle reaches the pass_once caller unchanged. |
| followup/pending-fault | A real owner answer changes input during a dispatched cycle; after completion, an injected follow-up start fault reaches the caller unchanged. |

The original fixture remains for the earlier rows. The setup row uses generated
owner keys, a fresh store, inert installation engine bytes, scratch install paths
and a local manager stand-in. No model or external channel is contacted.
Three additional finding-88 mutations remove setup enrollment or broaden each
scheduler catch. The existing budget-refusal mutation now targets except Refused.
Mutation execution remains reviewer-owned.
