# VELDO-0088 partial implementation evidence

This branch is not ready to land as a completed VELDO-0088. These observations
cover the bounded coordination substrate and one-run publication and staging.
They do not establish the entire criterion set.

The suite uses real signed membership, project and team enrollment, accepted
source revisions and immutable snapshots, an installed LangGraph process,
Runner dispatch, launch receiver, execution records, reservation settlement,
loopback decision presentation and settlement, document publication, backlog
and grooming commands, and the team assignment writer. Its worker is a generic
protocol process emitting predetermined documents, not a Claude Code or Codex
fake and not live engine qualification. All fixture keys are generated locally.

## Criterion observations

| Criterion | Rows | Observed behavior |
| :--- | :--- | :--- |
| AC1 | cycle/runner, cycle/snapshot, cycle/no-action, cycle/failure | Team configuration and accepted input enter an ordinary coordination dispatch; immutable source survives working-tree edits; persisted receipts include the actual graph trace; owner refusal is named. |
| AC2 | proposal/unauthorized, proposal/stop-on-refusal | Closed proposal vocabulary rejects shell, SQL, priority and completion operations; owning command refusal stops subsequent commands. |
| AC3 | cycle/serialized, cycle/pending-follow-up, cycle/budget | Store rejects concurrent cycles; an owner answer during a held worker produces one newer-snapshot follow-up without a self-loop; finite invocation ceiling stops another dispatch. |
| AC4 | unit/one-run-staging | An admitted objective preserves the exact message `please do BCG-123`; one PM dispatch publishes its requirements, grooms and stages a unit with all four role references and independent builder/reviewer assignment; the same dispatch records elaboration done. |

Each name reports once. The suite has ten behavior rows in addition to the
shared preamble. Rows use actual owning writers wherever those writers exist.

## Missing observations and behavior

The staged-unit test invokes ProjectCycles directly. It does not yet drive that
journey from the factory loop, start the assigned builder and independent
reviewer, or observe a builder fetching BCG-123 from its role's catalog server.
The factory still enumerates builder claims; accepted team assignments need the
corresponding engineering-dispatch bridge. The graph visits build, prove and
gate, review and land as routing nodes, without executing those stations.

The unauthorized row tests document vocabulary, not shell, SQL or store access
attempts inside the graph process. Waiting-person resource release and combined
owner-answer plus engineering-completion coalescing need dedicated observations.
The scheduler observes engineering completions, but this suite only drives the
owner-answer half of that set. Receipts also need a complete field-by-field
comparison for every cycle class.

## Red record and mutations

`drive.py` follows the recent proof-driver pattern. `red-at-24c0c90b.json`
records ten behavior rows red by assertion against the unchanged archive of
that commit. The new cycle and graph modules are absent there.

Finding 88 registers seven uniquely named mutations and retains their diffs in
`mutations.json`. No mutation was executed in this builder run; rejection is
unverified and belongs to the reviewer. The missing Runner dispatch and allowed
priority-vocabulary controls are proxies: they do not execute the exact inline
reasoning and graph-process direct-priority-write falsifiers required by AC1
and AC2. Pending-input discard and an extra elaboration dispatch have dedicated
mutations. Additional controls cover continuation after refusal, budget bypass,
and omitted trace evidence.

## Checks and scope

`checks.json` records scoped suites in normal and clean gate environments.
Exit status 2 is the repository's deliberate successful-partial-run status.
There is no gate stamp, full selftest, mutation-run result or landing claim.
Engine copies must remain byte-identical to their installed counterparts.

The only change to the VELDO-0151 implementation is the team assignment reader:
it reads risk from the accepted, digest-bound specification document when the
unit has no inline risk. Real grooming units carry that document binding.
The authority role vocabulary now admits the reservation service grant that
the existing reservation writer already requires; its exact role-set test is
updated. Both necessary footprint additions are recorded in the spec History.
