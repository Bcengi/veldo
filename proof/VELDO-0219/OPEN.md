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

AC1 lifecycle limit: polling reads known unit cgroups before coordinator cleanup,
and the native sustained-load fixture passes its 10 percent checks. A unit can,
however, be created and removed by candidate code between discovery polls; a
recreated cgroup at the same path can reset its counter. Full accounting requires
an authority lifecycle notification or other kernel accounting mechanism that
captures final counters before every unit teardown. The current implementation
must not be represented as proving this universal clause. Anonymous memory is
sampled, and disjoint per-unit peaks are added conservatively.

Observability also awaits the ledger protocol extension: its current reply is a
boolean grant only, without the resource of refusal or the gate-wide totals.
The dispatcher records its own granted sums, claim provenance and elapsed wait;
the scheduler separately records the actual gate totals and refusal resource.
A single admission record with the complete gate state requires that extension.

The lifecycle assumption conflicts with existing code on main: in
.veldo/control_containment.py, Group.conclude resets failed units and Group.close
releases its manager reference before the containing suite worker returns;
.veldo/control_service.py stop also stops a unit during the worker's lifetime.
Thus reading unit cgroups only when coordinator cleanup begins cannot recover
all final counters. This contradicts the spec's assumption that the coordinator can read every
unit's counters before its cleanup. These runtime modules are not policy-protected;
the open issue is the accounting contract, not a path approval requirement. A
lifecycle capture mechanism or an explicit sampled-accounting contract is needed
before the complete AC1 unit-accounting claim can be made.
