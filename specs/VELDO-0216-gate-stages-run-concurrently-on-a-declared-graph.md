---
schema: veldo.spec/v1
id: VELDO-0216
title: Gate stages run concurrently on a declared dependency graph
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0214]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", ".veldo/policy.yaml", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py", "scripts/gate_schedule.py", "engine/scripts/gate_schedule.py", "scripts/gate_graph.json"]
footprint:
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/gate_graph.json
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - .veldo/policy.yaml
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0216_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0216-gate-stages-run-concurrently-on-a-declared-graph.md
  - specs/index.md
  - proof/VELDO-0216/*
behavior_bearing: true
observability:
  logs: Each node prints its start, its end, its verdict and its wall time; each stage block is printed whole, in catalog order, from the node's own log.
  metrics: Per node wall seconds, CPU seconds and peak anonymous memory, recorded beside the VELDO-0214 leg times; the gate's critical path and its total wall time.
  traces: The graph's digest enters the stamp, the gate event and the authority identity, so a result names the graph it ran under.
  error_taxonomy: An invalid graph, a catalog stage missing from it or a cycle runs nothing and is RED; a node that writes the candidate tree is RED by name; a resource request no budget can satisfy is RED as invalid_resource_requirement.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the gate runs its required stages as nodes of one declared graph, read from the
      authority (scripts/gate_graph.json, protected), and starts a node as soon as every node it
      depends on has finished and its declared resources fit. Set: every required catalog item
      of verify.sh (lint, unit and integration with their confined and unconfined legs, security,
      generated, docs, packaging, extra, mutation), a graph with a cycle, a graph missing a
      required stage, a graph naming an unknown stage and an invalid file. Completeness: the node
      set is compared with verify.sh's catalog on every run, so a stage left out of the graph is
      a refusal, never a stage that silently did not run; rows concurrent-stages/graph-complete
      and concurrent-stages/graph-refusals drive each case through the real scheduler.
    falsified_by: >
      Let the scheduler skip a required stage the graph omits instead of refusing. Registered
      mutant concurrent216-missing-stage-runs-nothing must fail concurrent-stages/graph-complete.
  - id: AC2
    text: >
      Claim: running concurrently changes no verdict and no evidence. Each leg runs through the
      runner it uses today (scripts/gate_candidate.py for a confined leg, directly for an
      unconfined leg) with the same leg variables, writes its output to its own log, and the
      stamp, the gate event, the leg record and the mutation receipt carry the same verdict
      fields as a serial run of the same tree. Set: a fixture authority and candidate where all
      stages pass, where one confined leg fails, where an unconfined leg fails and where the
      mutation stage fails, each run serially and concurrently. Completeness: row
      concurrent-stages/same-verdicts compares the two runs field by field (per stage pass or
      FAIL, catalog counts, reused, force_fresh, unconfined) and requires them equal; a leg
      record line written by two legs at once is whole.
    falsified_by: >
      Drop the unconfined leg's line from the leg record when two legs finish together.
      Registered mutant concurrent216-lost-leg-record must fail concurrent-stages/same-verdicts.
  - id: AC3
    text: >
      Claim: no two nodes share a host resource beyond its declared capacity. Each node declares
      its memory (its measured peak anonymous memory from the last 30 days, a stated default when
      none is recorded), its systemd user manager use (none, shared or exclusive) and any fixed
      TCP port; the scheduler admits a node only when the sum of admitted declarations fits the
      gate's memory allowance, never runs an exclusive manager user beside any other manager user
      (the mutation stage's manager slots included, through one gate-wide ledger the coordinator
      reads on an inherited channel), and never runs two nodes on one fixed port. No node may
      write the candidate tree. Set: an exclusive manager node beside mutation manager workers, two
      nodes that together exceed the memory allowance, two nodes on one fixed port and a node
      that writes a file into the candidate. Completeness: rows concurrent-stages/manager-exclusive,
      concurrent-stages/memory-admission and concurrent-stages/tree-unchanged; the tree identity is
      the mutation stage's own inputs_unchanged comparison, taken before the first node and after
      the last.
    falsified_by: >
      Admit an exclusive manager node while mutation workers hold manager slots. Registered
      mutant concurrent216-manager-overlap must fail concurrent-stages/manager-exclusive.
  - id: AC4
    text: >
      Claim: on the qualification host (20 cores, 31 GiB, the owner's 16 GiB gate scope) a full
      fresh gate with this change alone finishes in at most 6,000 seconds against the measured
      10,719, because its critical path becomes the mutation stage (5,207 s measured) instead of
      the sum of every stage. Set: one force-fresh canonical gate at the landing candidate.
      Completeness: the receipt records every node's start, end, CPU seconds and peak memory; the
      proof states the critical path and compares each node's time with the serial baseline in
      proof/VELDO-0216/serial-baseline.json, taken from the 2026-10-25 canonical receipts.
    falsified_by: >
      Serialize every node (one node at a time). The measured canonical run exceeds 6,000 seconds
      and the proof's critical path check fails.
required_evidence: [unit, integration]
rollback: Remove scripts/gate_graph.json; verify.sh then runs every stage one after another, exactly as before this change.
---

## Intent

The last green canonical gate (2026-10-25, stack head 797b28fa, receipts in
/tmp/veldo-mutation-throughput-20261025) took 10,719 seconds. The stages before mutation took
5,502 seconds of wall time and used 5,069 CPU seconds: 0.92 of 20 cores on average, because
verify.sh runs every stage and every leg one after another. Measured per stage from the gate log
and the five-second resource samples:

| Stage | Wall s | CPU s | Average cores | Peak memory GiB |
|---|---:|---:|---:|---:|
| lint | 2 | | | |
| unit, confined leg | 1,913 | 1,900 | 0.99 | 2.52 |
| unit, unconfined leg | 892 | 661 | 0.75 | 1.87 |
| integration, confined leg | 1,795 | 1,796 | 1.00 | 2.89 |
| integration, unconfined leg | 834 | 629 | 0.76 | 2.27 |
| security | about 55 | 51 | 1.0 | 1.56 |
| generated, docs, packaging, extra | about 15 | 10 | 1.0 | 0.46 |
| mutation | 5,207 | 56,170 | 10.79 | 8.25 |
| contracts, shape gate, review events | about 6 | | | |

None of the pre-mutation legs needs another's result. The integration stage runs in a throwaway
copy, and its budget input from VELDO-0214 already accepts the unit leg's measurement from an
earlier gate run. The mutation stage freezes its own snapshot and runs its own controls. So the
gate can run these as independent nodes, and the wall time becomes the longest chain rather than
the sum.

## Design

A new authority script, scripts/gate_schedule.py, takes the place of verify.sh's loop over the
required catalog items. verify.sh still declares the catalog exactly as today and still prints,
counts and stamps exactly as today; it hands the required items to the scheduler and reads back one
result per stage in catalog order.

The graph is scripts/gate_graph.json, an authority file like scripts/gate_unconfined.json: read
beside the scheduler, never from the candidate, protected, and part of the authority identity
(reuse_evidence.AUTHORITY_FILES). Each node is one stage, or one leg of a stage the unconfined
list declares. A node names the nodes it depends on (none today, which the graph states
explicitly), whether it writes the candidate tree (none may), its manager use and its fixed ports.
Memory is not typed by hand: the scheduler reads each node's measured peak from the leg-time store
of VELDO-0214, extended with CPU seconds and peak anonymous memory per node, and uses a stated
default for a node with no measurement. Page cache is not counted, because the cgroup peaks in the
table above include reclaimable cache and overstate the need.

The gate's memory allowance is the memory.max of the cgroup the gate runs in, less a stated reserve;
with no limit it is the host's available memory less the reserve. The mutation stage is one node
whose worker admission draws from the same allowance and the same manager slots: the scheduler
hands the coordinator an inherited channel carrying its current allowance, and raises it as other
nodes finish. The coordinator never admits a new worker beyond the latest allowance.

Ordering that matters is kept. The unconfined legs of unit and integration each run suites that
need the manager undisturbed (63_veldo_0040_containment and 66_veldo_0047_authority declare it
exclusive in the manifest), so while either leg runs, no other manager user runs; they serialize
with each other and with the mutation stage's manager slots. VELDO-0221 shortens that window by
running each leg's suites in parallel.

Output stays readable and deterministic. Each node writes to its own log in the gate's private
directory; when a node ends, its block is printed whole with its stage header, and the summary
lines are printed in catalog order at the end. The leg record and the reuse receipt are each
written by one node, or by single-line appends that are whole under concurrency.

The candidate tree must not change while nodes run. No stage writes it today (VELDO-0208 moved the
generated check to a private temporary file). The scheduler compares the tree identity before the
first node and after the last with the mutation stage's inputs_unchanged; a change is RED.

Expected time with this change alone: the critical path is the mutation stage at 5,207 s measured,
with the pre-mutation legs (the longest 1,913 s) running beside it on the cores it leaves idle
(it averaged 10.8 of 20). Allowing for contention and for the manager serialization above, the
full gate should finish in about 5,300 to 5,600 seconds, a saving of about 5,100 to 5,400 seconds.
AC4 holds it to at most 6,000.

## Out of scope

The suites, their assertions and their confinement; which suites run unconfined (scripts/
gate_unconfined.json is unchanged); how many mutation workers run (VELDO-0219); running a leg's
suites in parallel (VELDO-0221); host load from other jobs (VELDO-0220); reuse.

## What the reviewer judges

Normal use: the owner or the lander runs scripts/verify.sh on a checkout or in candidate mode, on
the qualification host. Threat model: the same as VELDO-0208. The candidate cannot choose the
graph, the order or the resources, because all three are the authority's; unconfined legs keep the
residuals VELDO-0208 accepted. Out of review scope: a host with less memory than one node's
declared need (the gate refuses by name), and resource exhaustion by the owner's own account.

## Notes

The integration legs receive the unit leg's last recorded measurement (VELDO-0214 AC3, the
earlier-run path) because the unit legs now run beside them; with no measurement the floor of
1800 seconds applies, as today. The unit leg's time is still recorded when it passes.

Combined effect of the set VELDO-0216 to VELDO-0222, as estimates from the same receipts. A full
fresh gate (force fresh, nothing reused) becomes CPU bound: the measured 61,247 CPU seconds plus
about 5,000 for the ordered legs VELDO-0221 keeps in force-fresh gates, over about 18 usable cores,
is about 3,700 seconds (62 minutes); perfect packing on 20 cores would be about 3,300 (55 minutes).
A landing that changes a few suites re-runs every suite shard and about 3 to 7 percent of the
mutation cases plus the audit sample: about 15,000 to 20,000 CPU seconds, about 15 to 20 minutes.
A landing that changes a shared engine module under .veldo/ re-runs about 73 percent of the cases
(VELDO-0217 explains why) and takes about 40 to 45 minutes.

This spec is written to apply after the pending stack (agent/claude/cand-veldo-stack, tip
3ab6e90d) lands: its manifest adds the new_project_fixture resource, which stays a mutation-stage
resource and is not a gate node resource.
