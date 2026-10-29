# VELDO-0216 open qualification

AC4 requires a force-fresh canonical gate at the landing candidate and a serialized
canonical falsifier. Owner rule 37191 limits this build to ticket checks and forbids
scripts/verify.sh. Both canonical measurements remain for the batch gate. No fixture
or estimate is evidence that the 6000 second qualification passed.

Round two replaces full-capacity cold claims with explicit authority startup
estimates derived from serial-baseline.json. Historical cache-inclusive peaks
remain labelled estimates, never anonymous-memory measurements. Fresh source-bound
anonymous measurements still take precedence. The ledger accounts separately for
CPU, memory, shared inherited host-lock use, manager slots and ports.

The approved amendment at 18e375b0 measures AC4 with VELDO-0219 and without
VELDO-0221. This branch now includes VELDO-0219's per-case handoff: the mutation
root releases aggregate manager exclusion when measured admission takes ownership.
The earlier 6932.501 second replay describes VELDO-0216 alone. It is not a timing
result for the combined implementation. The exact joint batch requirements,
including the 6,000 second full-gate target, fixed-sixteen mutation control and
serialized gate control, are in ../VELDO-0219/OPEN.md. Both AC4s remain deferred.

VELDO-0220 already records that suite 113 needs a userbus entry in
scripts/gate_unconfined.json. That protected file is outside this ticket's named paths.
It is unchanged here and remains a batch-gate blocker.

PLAN-0019 retains standalone enforcement work outside its release work graph. The
2026-10-28 inventory orders this gate-speed ticket after 0220 and before 0219 and 0221.

Owner decision requested: the earlier implementation added .gitignore to the
footprint of the ready, human_approval: required VELDO-0216 specification. No cited
owner approval for that footprint edit exists. The addition remains necessary to
ignore generated graph receipts. Please approve or revise that footprint explicitly;
this round does not change the specification or claim that approval was given.
