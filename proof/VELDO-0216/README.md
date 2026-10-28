# VELDO-0216 local implementation evidence

This is ticket evidence, not a canonical gate or landing approval. Implementation
starts at df758f80, the supplied VELDO-0220 branch head. Owner go: Telegram 37209 and
37212. No push, merge, other worktree edit or Bcengi source was used.

## Acceptance checks

All checks live in scripts/suites/114_veldo_0216_concurrent_stages.py. The suite
runs only its own prerequisites and reports PARTIAL, with exit 2 on success by the
existing selftest contract. No invocation of scripts/verify.sh was made. Shell
catalog and stamp fragments are exercised independently over fixture authorities.

| AC | Implementation and check | Registered falsifier | Qualification |
| :--- | :--- | :--- | :--- |
| AC1 | Authority graph has all eleven required nodes. Exact catalog comparison, cycle and invalid-file refusal precede all launches. graph-complete, graph-refusals, dependency-start, ordered-logs, shell-catalog | concurrent216-missing-stage-runs-nothing | Local checks |
| AC2 | Actual confined launcher and unconfined leg runner; one private log per node; atomic leg append; serialized unit timing-store transaction; prior-run integration budgets; original mutation input comparison spans the whole graph. same-verdicts compares stage verdicts, mutation receipt, leg record, actual stamp/event fields and catalog counts in serial and concurrent fixtures. tree-unchanged rejects a real unconfined writer by name. measurement-record-race checks simultaneous store writers. | concurrent216-lost-leg-record | Local checks |
| AC3 | Scheduler-owned summed CPU, anonymous-memory, manager and fixed-port ledger; inherited socket protocol for trusted coordinators. ledger-sums, inherited-ledger, mutation-floor, scope-capacities, anonymous-metrics, measured-claims, cold-measurements | concurrent216-count-not-sum | Local ledger checks; downstream dispatchers remain for 0219 and 0221 |
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
cache-inclusive figures are never used as anonymous-memory claims.

Production capacities come from the gate scope and every ancestor quota/memory
limit, minus the graph reserve, and the authority manifest's manager slots. Each
node has its own delegated cgroup. Anonymous peaks are sampled at the scheduler's
nominal 50 ms polling interval; process startup and input comparisons add overhead
between polls. CPU seconds are the kernel cumulative counter. A remaining descendant
reddens its node and is killed in that node's cgroup before release. Scratch tests
substitute a meter, so they do not qualify real delegated node cgroups.

A cold node reserves full CPU and memory capacity. Only passing authority cgroup
measurements enter its per-node store. Files bind authority location, graph, catalog,
leg declaration and runner sources; samples expire after 30 days. A changed authority
or new temporary authority starts cold. This deliberately does not invent missing
measurements, but makes the first cold graph serial. Subsequent measured graphs can
run concurrently. Current mutation coordination holds an aggregate exclusive manager
claim, so the two unconfined legs cannot overlap it. The measured baseline lower bound
for those three intervals alone is 6932.501 seconds. The spec's 6000 second promise
therefore needs the decision recorded in OPEN.md.

The inherited Client API is for authority coordinators. It returns refusal until a
claim fits, retains the coordinator's claim, namespaces claims per node, rejects
foreign releases and marks leaked child claims red. Candidate children receive
neither its descriptor nor its environment variable through either leg runner.
The 0219 and 0221 dispatchers must supply measured worker/shard claims and use
coordinator-only node measurements when they are built. They do not exist in this
base and are not represented as integrated here.

Tree changes conservatively redden all nodes in the graph. The actual writer is
therefore red by name, without claiming exclusive attribution among overlapping
unconfined processes. As with mutation's original before/after comparison, a write
restored before comparison is not detected.

The graph is optional and repository-specific, like the unconfined declaration.
Its absence preserves the serial catalog loop. The scheduler ships to adopters;
the repository graph does not. Both scheduler and graph enter authority identity,
with an absent graph represented explicitly. Graph digest is in the stamp, gate
event, scheduler receipt and scheduled mutation receipt.

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
