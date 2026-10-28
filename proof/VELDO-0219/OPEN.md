# VELDO-0219 remaining qualification and dependency contract

AC4's force-fresh canonical gate and fixed-sixteen canonical falsifier are deferred
by owner rule 37191. No canonical gate is run during this build. The 4000 second
bound remains unqualified until the batch capture passes qualification.py.

The inherited VELDO-0216 scheduler holds an aggregate mutation claim, including an
exclusive manager claim, while its channel accepts only additional child claims
and releases of those children. There is no operation to replace the aggregate
claim with coordinator overhead. A cold mutation node reserves the whole capacity.
Consequently per-worker claims cannot fit, even when the actual host is idle.
The scheduler must hand off the aggregate claim, expose capacity, reserved floor
and current totals to its dispatcher, and retain a mutation root reservation until
all workers finish. Its mutation node must claim coordinator overhead only and
leave manager admission to workers. Required changes are in scripts/gate_schedule.py,
engine/scripts/gate_schedule.py and scripts/gate_graph.json, protected paths the
owner explicitly excluded from this ticket. They are untouched. Production
measured admission refuses this incompatible graph explicitly instead of hanging.

The inventory's 2689 case count is historical. Qualification must enumerate the
current registry and account for every case; tests retain a 2689 case scenario too.
PLAN-0019 places this work outside its release work graph as standalone gate
infrastructure, before 0217 and 0223 in the remaining inventory.

Inherited VELDO-0220 also records the missing suite 113 entry in the protected
scripts/gate_unconfined.json. This ticket does not edit that file.
