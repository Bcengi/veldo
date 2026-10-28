# VELDO-0216 open qualification

AC4 requires a force-fresh canonical gate at the landing candidate and a serialized
canonical falsifier. Owner rule 37191 limits this build to ticket checks and forbids
scripts/verify.sh. Both canonical measurements remain for the batch gate. No fixture
or estimate is evidence that the 6000 second qualification passed.

The baseline receipts contain cgroup memory including cache, not per-node anonymous
memory. VELDO-0214 and VELDO-0215 stores on main contain duration only. Cold nodes
must reserve capacity conservatively until authority measurements exist; the historical
memory figures must not be represented as anonymous-memory measurements.

VELDO-0219 and VELDO-0221 depend on this ticket and are not implemented. This ticket
provides the inherited ledger protocol. Their dispatchers must use it with measured
per-worker and per-shard needs when built. Until then mutation is an aggregate claim;
its manager use excludes the two exclusive unconfined legs. This can make the stated
AC4 bound unattainable without those follow-ups, requiring an owner specification decision
or measurement demonstrating otherwise. No manager exclusion is weakened for speed.

VELDO-0220 already records that suite 113 needs a userbus entry in
scripts/gate_unconfined.json. That protected file is outside this ticket's named paths.
It is unchanged here and remains a batch-gate blocker.

PLAN-0019 retains standalone enforcement work outside its release work graph. The
2026-10-28 inventory orders this gate-speed ticket after 0220 and before 0219 and 0221.
