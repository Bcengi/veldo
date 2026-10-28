---
schema: veldo.spec/v1
id: VELDO-0216
title: Gate stages run concurrently on a declared graph under one gate-wide resource ledger
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0214, VELDO-0215, VELDO-0220]
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
  logs: Each node prints its start, its end, its verdict and its wall time; each stage block is printed whole, in catalog order, from the node's own log; every ledger grant and refusal names the claimant and the resource.
  metrics: Per node wall seconds, CPU seconds and peak anonymous memory; the ledger's peak granted CPU, memory and manager slots against its capacities; the gate's critical path and total wall time.
  traces: The graph's digest enters the stamp, the gate event and the authority identity, so a result names the graph it ran under.
  error_taxonomy: An invalid graph, a catalog stage missing from it or a cycle runs nothing and is RED; a node that writes the candidate tree is RED by name; a claim no capacity can satisfy is RED as invalid_resource_requirement.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the gate runs its required stages as nodes of one declared graph, read from the
      authority (scripts/gate_graph.json, protected), and starts a node as soon as every node it
      depends on has finished and the ledger grants its claim. Set: every required catalog item of
      verify.sh (lint, unit and integration with their confined and unconfined legs, security,
      generated, docs, packaging, extra, mutation), a graph with a cycle, a graph missing a
      required stage, a graph naming an unknown stage and an invalid file. Completeness: the node
      set is compared with verify.sh's catalog on every run, so a stage left out of the graph is a
      refusal, never a stage that silently did not run; rows concurrent-stages/graph-complete and
      concurrent-stages/graph-refusals drive each case through the real scheduler.
    falsified_by: >
      Let the scheduler skip a required stage the graph omits instead of refusing. Registered
      mutant concurrent216-missing-stage-runs-nothing must fail concurrent-stages/graph-complete.
  - id: AC2
    text: >
      Claim: running concurrently changes no verdict and no evidence. Each leg runs through the
      runner it uses today (scripts/gate_candidate.py for a confined leg, directly for an
      unconfined leg) with the same leg variables and its own log; the stamp, the gate event, the
      leg record and the mutation receipt carry the same verdict fields as a serial run of the same
      tree; and the candidate tree is unchanged from before the first node to after the last
      (the mutation stage's inputs_unchanged comparison). Set: a fixture where all stages pass,
      where a confined leg fails, where an unconfined leg fails, where the mutation stage fails,
      each run serially and concurrently, and a node that writes a file into the candidate.
      Completeness: row concurrent-stages/same-verdicts compares the runs field by field (per stage
      pass or FAIL, catalog counts, reused, force_fresh, unconfined); row
      concurrent-stages/tree-unchanged requires the writing node to be RED by name.
    falsified_by: >
      Drop the unconfined leg's line from the leg record when two legs finish together. Registered
      mutant concurrent216-lost-leg-record must fail concurrent-stages/same-verdicts.
  - id: AC3
    text: >
      Claim: one gate-wide ledger, owned by the scheduler, holds the gate's CPU, anonymous memory
      and systemd user manager capacities, and every claimant draws from it: each node, each shard
      of VELDO-0221 and each mutation worker of VELDO-0219, the latter two over an inherited channel
      to the ledger. A claim is its claimant's measured need (peak anonymous memory and CPU rate
      from the stores of VELDO-0215, VELDO-0219 and VELDO-0221; for a sharded leg the sum over its
      running shards, never the serial leg's peak) and its manager use (none, shared or exclusive).
      The ledger grants a claim only when the sum of granted CPU and of granted memory, each plus
      the claim, stays within capacity, and never grants an exclusive manager claim beside any
      other manager claim; fixed TCP ports are exclusive claims too (a scan of the repository on
      2026-10-25 found none). Set: claims that together exceed CPU, claims that together exceed
      memory, an exclusive manager claim while mutation workers hold manager slots, and two claims
      on one port. Completeness: row concurrent-stages/ledger-sums records every grant and release
      and requires, at every instant, the summed granted peaks within each capacity and every
      oversubscribing claim refused until it fits.
    falsified_by: >
      Grant claims by count of claimants instead of by summed measured need. Registered mutant
      concurrent216-count-not-sum must fail concurrent-stages/ledger-sums.
  - id: AC4
    text: >
      Claim: on the qualification host (20 cores, 31 GiB, the 16 GiB gate scope of VELDO-0220) a
      full fresh gate with this change and without VELDO-0219 and VELDO-0221 finishes in at most
      6,000 seconds against the measured 10,719, because its critical path becomes the mutation
      stage (5,207 s measured) instead of the sum of every stage. Set: one force-fresh canonical
      gate at the landing candidate. Completeness: the receipt records every node's start, end,
      CPU seconds and peak memory; the proof states the critical path and compares each node with
      the serial baseline in proof/VELDO-0216/serial-baseline.json, taken from the 2026-10-25
      canonical receipts.
    falsified_by: >
      Serialize every node (a CPU capacity of one claimant). The measured canonical run exceeds
      6,000 seconds and the proof's critical path check fails.
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

The memory column is cgroup memory, which includes reclaimable page cache; the ledger uses
anonymous memory, measured per claimant. None of the pre-mutation legs needs another's result. The
integration stage runs in a throwaway copy, and its budget input from VELDO-0214 already accepts
the unit leg's measurement from an earlier gate run. The mutation stage freezes its own snapshot and
runs its own controls. So the gate can run these as independent nodes, and the wall time becomes
the longest chain rather than the sum.

## Design

A new authority script, scripts/gate_schedule.py, takes the place of verify.sh's loop over the
required catalog items. verify.sh still declares the catalog exactly as today and still prints,
counts and stamps exactly as today; it hands the required items to the scheduler and reads back one
result per stage in catalog order.

The graph is scripts/gate_graph.json, an authority file like scripts/gate_unconfined.json: read
beside the scheduler, never from the candidate, protected, and part of the authority identity
(reuse_evidence.AUTHORITY_FILES). Each node is one stage, or one leg of a stage the unconfined list
declares. A node names the nodes it depends on (none today, stated explicitly), whether it writes
the candidate tree (none may), its manager use and its fixed ports.

The ledger is the one place resources are counted. Its capacities come from the gate's delegated
scope (VELDO-0220): CPU is the CPUs the gate may use, bounded by the scope's quota; memory is the
scope's memory.max less a stated reserve; manager slots are the manifest's systemd_user_manager
capacity. Claims are measured, not typed: a node's claim is read from its per-node record (the
VELDO-0214 leg-time store, extended with CPU seconds and peak anonymous memory), a shard's from
VELDO-0221's per-suite record, a mutation worker's from VELDO-0219's per-case record. The shard
dispatcher of a leg and the mutation coordinator each hold a channel to the ledger and claim per
shard or per worker, so a sharded leg's memory is the sum of what its running shards hold, never a
figure measured when the leg ran serially. Admission rules inside the mutation stage (slots,
exclusive holds, new_project_fixture) stay where they are and add to, never replace, the ledger's
rule. The graph also states a floor of CPU and memory reserved for the mutation stage, which no
other claimant may take; VELDO-0219 computes its guaranteed worker count against that floor.

The two unconfined legs each run suites that need the manager undisturbed
(63_veldo_0040_containment and 66_veldo_0047_authority declare it exclusive), so those shards hold
an exclusive manager claim while they run; VELDO-0221 confines that hold to the two shards.

Output stays readable and deterministic. Each node writes to its own log in the gate's private
directory; when a node ends, its block is printed whole with its stage header, and the summary lines
are printed in catalog order at the end. The leg record and the reuse receipt are each written by
one node, or by single-line appends that are whole under concurrency.

Expected time with this change alone: the critical path is the mutation stage at 5,207 s measured,
with the pre-mutation legs (the longest 1,913 s) running beside it on the cores it leaves idle (it
averaged 10.8 of 20). Allowing for contention and the manager's exclusive holds, the full gate
should take about 5,300 to 5,600 seconds, a saving of about 5,100 to 5,400 seconds.

## Out of scope

The suites, their assertions and their confinement; which suites run unconfined; how mutation
workers are admitted (VELDO-0219); how a leg runs its suites (VELDO-0221); host load from other
jobs (VELDO-0220, VELDO-0223); reuse.

## What the reviewer judges

Normal use: the owner or the lander runs scripts/verify.sh on a checkout or in candidate mode, on
the qualification host. Threat model: the same as VELDO-0208. The candidate cannot choose the graph,
the order or the capacities, because all three are the authority's; claims are read from the
authority's stores. Out of review scope: a host with less memory than one claimant's need (the gate
refuses by name), and resource exhaustion by the owner's own account.

## Notes

The integration legs receive the unit leg's last recorded measurement (VELDO-0214 AC3, the
earlier-run path) because the unit legs now run beside them; with no measurement the floor of 1800
seconds applies, as today.

Expected times of the whole set, with the owner's decisions D1 (an isolation check in every gate,
VELDO-0221) and D2 (reuse only when every input is traced or mechanically refused, VELDO-0217 and
VELDO-0222) applied. The 30-minute target holds for a typical landing only when VELDO-0222's private
managers qualify most unconfined cases and most cases pass VELDO-0226's sensitivity proof. Estimates from the 2026-10-25 receipts; each is to be replaced by the
measured figure in its spec's proof.

| Run | Estimate | Basis |
|---|---|---|
| Full fresh gate (force fresh) | about 58 min; floor 52 | CPU bound: 61,247 CPU s measured plus about 1,500 for shard closures and interpreter starts (VELDO-0221), over about 18 of 20 cores; 52 min at full packing on 20 |
| Typical landing, a few suites changed, private managers qualify the unconfined cases (VELDO-0222) | about 15 to 20 min | every suite shard (about 5,500 CPU s) plus 3 to 7 percent of 2,689 cases and the audit sample (about 10,000 to 15,000 CPU s) at measured admission |
| Typical landing, unconfined cases stay fresh | about 38 to 45 min | the above plus all 982 unconfined cases and their controls (38,472 worker s measured), bounded by the manager's 16 slots |
| Any landing before VELDO-0226's sensitivity proofs exist (libfaketime is not yet installed) | about 55 min | nothing qualifies for reuse, so the mutation stage runs fresh at measured admission beside the shards |
| Share of cases passing the sensitivity proof | unmeasured | two fresh runs on 2026-10-25 differed in non-target observations for 4 of 2,566 cases, which would fail; clock-offset and hash-order sensitivity is unknown until the first proof pass. Each typical-landing figure above scales with this share |
| Landing that changes a shared engine module (14 of 37 recent landings) | about 40 to 45 min | about 73 percent of cases re-run because their fixtures copy all 233 engine modules |
| The same, if VELDO-0225's replay shows copies are mostly unread | about 15 to 25 min | re-runs fall toward the 3 to 20 percent of suite-only landings; unmeasured until that replay |

This spec is written to apply after the pending stack (agent/claude/cand-veldo-stack, tip
3ab6e90d) lands: its manifest adds the new_project_fixture resource, which stays a mutation-stage
resource and is not a ledger capacity.
