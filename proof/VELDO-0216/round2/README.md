# Round two evidence

Scope: this ticket's suite, four registered falsifiers, a split-only parity defect,
and a duration replay. No end-to-end verify.sh run, other ticket suite, detached
process, push or merge. Suite batches use the owner's blocking host flock; fixtures
use scratch authorities and do not acquire the real lock. The first standalone
single-suite parity check ran without the flock, within the single-file allowance.

| Review item | Red | Green |
| :--- | :--- | :--- |
| Cold claims and real resources | design-red.json; schedule-red.json replays 281fd07c | design-green.json; schedule-green.json; seeded-first-run and host-lock-ledger rows |
| Same verdicts against serial | parity-final-red.json injects split-only record corruption | falsifiers.json restored baseline same-verdicts; confined-suite.log |
| Refused graph stamps and events | refusal-red.log, graph-refusal-record | fixes-green.log and confined-suite.log, graph-refusal-record |
| Writer attribution | refusal-red.log, tree-unchanged | fixes-green.log and confined-suite.log, tree-unchanged |
| Footprint approval item | design-red.json, footprint-owner-item false | design-green.json; OPEN.md owner item |

The earlier parity-red.json also reproduced the refusal-record defect, so its
probe exited on that additional false row. parity-final-red.json is the final
isolated split-defect run. The green logs use selftest's intentional exit 2 for a
partial run; that status never means a canonical gate passed.

The writer fixture has an unconfined leg change input while independent readers
run. It requires only that named leg to fail, every innocent node to pass, and the
original input to remain unchanged. Each unconfined leg receives a private snapshot
of the mutation coordinator's exact input closure, checked at exit. Mutation already
freezes its own inputs; confined commands already have read-only candidate access.
An out-of-snapshot change fails the whole graph without falsely attributing it.
This does not detect a write restored before comparison or attribute arbitrary
absolute writes outside the owned input snapshot.

The refusal fixture seeds a stale green stamp, then exercises invalid graph,
impossible capacity, and meter exceptions through the actual shell catalog and
stamp fragments. It requires a red stamp, gate.failed event, zero completed stages,
no mutation receipt, and no node launch. It never executes verify.sh end to end.

AC4 is still unmet. The replay is 6932.501 s for graph execution, based on exact
recorded durations for the three manager users and recorded interval ceilings for
coalesced short stages. It uses the real ledger, mutation floor, graph order and
startup claims. It excludes contention, snapshot preparation and shell overhead.
See ../spec-conflict.md for the detailed arithmetic and proposed amendment. The
specification is unchanged in round two. Canonical qualification and the footprint
approval remain owner work.

The confined launcher also prints its standard publication-forbidden message for
selftest's partial-run exit 2. The observed result is 48 passed and zero failed,
including 22 ticket rows. It is intentionally not a green canonical gate.
