# VELDO-0216 local implementation evidence

Round two evidence is in round2/. See spec-conflict.md and OPEN.md for the
unmet AC4 criterion and the pending footprint approval. Earlier proof files are
retained as history.

This is ticket evidence, not a canonical gate or landing approval. Implementation
starts at df758f80, the supplied VELDO-0220 branch head. Owner go: Telegram 37209 and
37212. No push, merge, other worktree edit or Bcengi source was used.

## Acceptance checks

Gate behavior checks live in scripts/suites/114_veldo_0216_concurrent_stages.py. The suite
runs only its own prerequisites and reports PARTIAL, with exit 2 on success by the
existing selftest contract. No invocation of scripts/verify.sh was made. Shell
catalog and stamp fragments are exercised independently over fixture authorities.

| AC | Implementation and check | Registered falsifier | Qualification |
| :--- | :--- | :--- | :--- |
| AC1 | Authority graph has all eleven required nodes. Exact catalog comparison, cycle and invalid-file refusal precede all launches. graph-complete, graph-refusals, dependency-start, ordered-logs, shell-catalog | concurrent216-missing-stage-runs-nothing | Local checks |
| AC2 | Actual confined launcher and unconfined leg runner; one private log per node; atomic leg append; serialized unit timing-store transaction; prior-run integration budgets; original mutation input comparison spans the whole graph. same-verdicts compares stage verdicts, mutation receipt, leg record, actual stamp/event fields and catalog counts against the no-graph serial runner and concurrent fixtures. tree-unchanged rejects a real unconfined snapshot writer by name while innocent nodes pass. measurement-record-race checks simultaneous store writers. | concurrent216-lost-leg-record | Local checks |
| AC3 | Scheduler-owned summed CPU, anonymous-memory, manager and fixed-port ledger; inherited socket protocol for trusted coordinators. ledger-sums, inherited-ledger, mutation-floor, scope-capacities, anonymous-metrics, measured-claims, cold-measurements, seeded-first-run, host-lock-ledger | concurrent216-count-not-sum | Local ledger checks; bootstrap estimates and remaining downstream admission are documented in spec-conflict.md |
| AC4 | Node receipts include intervals, CPU seconds, observed anonymous peak, graph and admission dependencies, critical path and total graph wall time. critical-path-fixture uses real short processes; canonical-receipt-check exercises the batch receipt checker. | concurrent216-serialize-nodes | Canonical normal and serialized runs NOT RUN; see OPEN.md |

red-green.json records each actual registered mutant first, then its restored
baseline, including target rows and source digests. local_check.py uses the existing
teeth materializer and worker, confined to this ticket's four cases. It runs inside
the owner's blocking flock. Every fixture uses private scratch, and none acquires,
releases or substitutes for the real host lock.

## Measurement and integration limits

serial-baseline.json derives from the actual 2026-10-25 receipts and binds their
SHA-256 digests. Exact leg durations and mutation duration come from the log. CPU
and total cgroup memory are five-second samples. Short stages in one sample have
an interval and null wall time rather than an invented duration. These historical
cache-inclusive figures now seed explicitly labelled startup estimates, rounded
upward to GiB. They are never reported as anonymous-memory measurements.

Production capacities come from the gate scope and every ancestor quota/memory
limit, minus the graph reserve, and the authority manifest's manager slots. Each
node has its own delegated cgroup. Anonymous peaks are sampled at the scheduler's
nominal 50 ms polling interval; process startup and input comparisons add overhead
between polls. CPU seconds are the kernel cumulative counter. A remaining descendant
reddens its node and is killed in that node's cgroup before release. Scratch suite checks
substitute a meter. The separate kernel_scope_check.py probe uses the unchanged
VELDO-0220 scope creator, a real delegated node cgroup and a 32 MiB allocating CPU
child. kernel-scope.json records its passing capacity, CPU, anonymous-memory and
empty-cgroup cleanup checks. Its outer command holds the real host lock; the probe
itself never operates on that lock.

The protected graph carries recorded startup estimates for every repository node,
with provenance bound to serial-baseline.json. A cold run uses these CPU rates and
cache-inclusive memory estimates; an unknown node without an estimate still reserves
full capacity. Passing anonymous-memory measurements remain source-bound and expire
after 30 days. Fresh measurements take precedence over startup estimates. CPU,
memory, manager use, inherited host-lock use and ports are separate ledger claims.
All current nodes share the gate holder's host lock and never reacquire it. Both
unconfined legs and mutation still need exclusive manager use because they include
suites 63 and 66. The production-ledger replay projects 6932.501 seconds; independent
confined legs now overlap mutation on the first run. AC4's 6000-second limit remains
unmet. spec-conflict.md proposes an owner amendment without changing the spec.

The inherited Client API is for authority coordinators. It returns refusal until a
claim fits, retains the coordinator's claim and unused mutation floor until the
mutation node finishes, namespaces claims per node, rejects
foreign releases and marks leaked child claims red. Candidate children receive
neither its descriptor nor its environment variable through either leg runner.
The 0219 and 0221 dispatchers must supply measured worker/shard claims and use
coordinator-only node measurements when they are built. They do not exist in this
base and are not represented as integrated here.

Each unconfined leg now runs through the existing runner in its own input snapshot,
using the mutation coordinator's closure and Git snapshot functions. A byte, mode,
name or HEAD change in that snapshot fails its owning node. Concurrent innocent
nodes keep their verdicts. Confined commands retain their existing read-only
candidate boundary; mutation retains its own frozen inputs. The original checkout
also has a whole-run guard. A change outside the owned snapshots fails the graph
without guessing a writer. Restored-before-comparison writes are not detected, as
with the existing mutation guard. Snapshot preparation adds unmeasured overhead
to the replay projection. This is input isolation, not new host confinement for
unconfined suites; absolute writes outside a leg's snapshot are not attributed.

A refused graph, impossible capacity or scheduler exception reaches the common
red stamp and gate.failed event emission. Refusal runs no additional built-in
checks and records zero completed catalog stages. The stale green stamp is replaced.

The same-verdicts reference invokes the no-graph path's unsplit gate_legs CLI and
mutation CLI directly. It does not invoke the scheduler or its command builder.
The checks compare verdicts, counts, leg records, mutation receipts and actual shell
stamp/event fields, excluding only the intentionally absent graph identity. A
split-only record corruption falsifier turns this comparison red.

The graph is optional and repository-specific, like the unconfined declaration.
Its absence preserves the serial catalog loop. The scheduler ships to adopters;
the repository graph does not. Both scheduler and graph enter authority identity,
with an absent graph represented explicitly. Graph digest is in the stamp, gate
event, scheduler receipt and scheduled mutation receipt. The scheduler receipt is
published atomically, replacing a sink symlink without following it. The repository
ignores this generated receipt so it does not add a dirty input path to the stamp.

## Protected surface

Only the twelve protected paths named by this ticket changed:

- scripts/verify.sh and engine/scripts/verify.sh
- scripts/gate_legs.py and engine/scripts/gate_legs.py
- scripts/check_gate_mutations.py and engine/scripts/check_gate_mutations.py
- scripts/gate_schedule.py and engine/scripts/gate_schedule.py
- .veldo/reuse_evidence.py and engine/.veldo/reuse_evidence.py
- .veldo/policy.yaml
- scripts/gate_graph.json

VELDO-0220's host helper and configuration are unchanged. Its existing missing
unconfined-suite declaration remains outside this ticket's protected surface.

For the later batch, feed a full capture to qualification.py as documented in its
module header. That checker requires the qualification host, exact candidate, a
green force-fresh stamp/event, matching graph identities, all node measurements,
stable inputs, ledger peaks within capacities and full elapsed time at most 6000s.

Round one red-green.json and targeted-checks.json are historical. The current
source-bound registered falsifiers and confined suite are recorded in
round2/falsifiers.json and round2/confined-suite.log. Round two's README maps each
finding to its red and green evidence. No canonical qualification is claimed.
