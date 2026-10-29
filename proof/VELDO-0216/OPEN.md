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

VELDO-0219 and VELDO-0221 are not implemented. The three aggregate manager users
still conflict for real reasons. The production-ledger duration replay projects
6932.501 seconds before overhead, versus AC4's 6000 seconds. See spec-conflict.md
for the numbers, reproducible evidence and a proposed owner amendment. The spec
has not been edited, and AC4 remains unmet.

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
