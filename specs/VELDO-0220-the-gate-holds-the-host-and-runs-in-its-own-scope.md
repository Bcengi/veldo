---
schema: veldo.spec/v1
id: VELDO-0220
title: The gate takes the owner's host lock and runs in a delegated scope of its own
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", ".veldo/policy.yaml", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py", "scripts/gate_host.py", "engine/scripts/gate_host.py", "scripts/gate_host.json"]
footprint:
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_host.py
  - engine/scripts/gate_host.py
  - scripts/gate_host.json
  - .veldo/policy.yaml
  - .veldo/reuse_evidence.py
  - engine/.veldo/reuse_evidence.py
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - .veldo/executor.py
  - engine/.veldo/executor.py
  - .veldo/lander.py
  - engine/.veldo/lander.py
  - .veldo/control_proof.py
  - engine/.veldo/control_proof.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0220_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0220-the-gate-holds-the-host-and-runs-in-its-own-scope.md
  - specs/index.md
  - proof/VELDO-0220/*
behavior_bearing: true
observability:
  logs: The gate prints the load it needs, the lock it took or found held with the holder when recorded, and the scope it runs in with its memory limit.
  metrics: Seconds waited for the lock; the scope's CPU and memory counters, which VELDO-0216, VELDO-0219 and VELDO-0223 read.
  traces: The stamp names the lock path and the scope.
  error_taxonomy: A held lock is NOT STARTED (exit 75, no stamp, no event); a scope that cannot be created is RED by name; the executor, the lander and the proof store record NOT STARTED as not run, never as a failed gate.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: before any check runs, the gate takes the owner's host lock exclusively (the path in
      the authority's protected scripts/gate_host.json; on this host
      /home/dmitry/.local/state/core-gates/.gate.lock, which myday/scripts/gate_core_cand.sh
      already holds with an exclusive flock) and keeps it until it exits on every path; when the
      lock is held it does not start, prints GATE: NOT STARTED with the holder when one is recorded,
      exits 75 and writes no stamp and no event, unless the caller asked to wait a stated number of
      seconds. Set: a lock held by another process, held by a flock like the core gate's, free, and
      a gate killed midway. Completeness: rows host-lock/held-not-started and
      host-lock/released-on-exit drive the real verify.sh against a fixture configuration.
    falsified_by: >
      Run the checks when the lock cannot be taken. Registered mutant host220-ignores-lock must fail
      host-lock/held-not-started.
  - id: AC2
    text: >
      Claim: the gate runs in a delegated user scope of its own, created through the user manager
      with the memory limit and out-of-memory score the configuration states (today 16 GiB and 900,
      the limits the owner already runs gates under), with the gate's own processes in a leaf of it
      so per-worker and per-node cgroups can be made beneath; the scope's CPU, memory and memory
      pressure counters are the gate's own and nothing else's. Set: a fixture gate started outside
      any scope and one started inside a scope that already exists. Completeness: row
      host-scope/own-scope requires the stated limits on the scope, every gate process inside it,
      and a child cgroup creatable beneath it.
    falsified_by: >
      Leave the gate in the caller's cgroup. Registered mutant host220-no-scope must fail
      host-scope/own-scope.
  - id: AC3
    text: >
      Claim: NOT STARTED is never recorded or charged as a red: the executor treats exit 75 as a step
      that did not run, the lander records no failed attempt, and the proof store keeps no gate
      observation for it. Set: an executor run, a landing attempt and a proof capture each meeting a
      held lock. Completeness: row host-lock/not-started-not-red drives the three with a fixture gate
      that exits 75.
    falsified_by: >
      Let the lander count exit 75 as a failed gate. Registered mutant host220-not-started-is-red
      must fail host-lock/not-started-not-red.
required_evidence: [unit, integration]
rollback: Remove scripts/gate_host.json; the gate then takes no lock and makes no scope, as before.
---

## Intent

The owner already serializes heavy gates with an exclusive flock on
/home/dmitry/.local/state/core-gates/.gate.lock (myday/scripts/gate_core_cand.sh). The Veldo gate
does not take it, so a core gate and a Veldo gate can overlap and slow each other into false reds.
The gate also has no cgroup of its own unless its caller made one, so it cannot tell its own load
from anyone else's, and VELDO-0216 and VELDO-0219 have nothing to count claims against.

## Design

scripts/gate_host.json is the authority's host configuration, repository-owned like
scripts/gate_unconfined.json: read beside the authority, protected, not shipped to adopters. It names
the lock path, the scope's memory limit and out-of-memory score, and the load the gate needs (cores
and memory, from the measured runs VELDO-0216 and VELDO-0219 record), which the gate prints first.
With no file the gate takes no lock and makes no scope, so an adopter's gate is exactly as today.

A new authority helper, scripts/gate_host.py, takes the lock as an exclusive flock on an open
descriptor (released by the kernel when the gate exits on any path), writes the gate's process id,
commit and start time to a holder file beside the lock, and creates the scope through the user
manager: the authority runs outside every confinement, so the user bus is reachable to it. Callers
that wait set an environment variable naming the seconds to wait. Exit 75 is the conventional
temporary-failure status, so callers can retry without parsing text.

Expected time saved: none on a quiet host. It prevents overlap with the core gates, whose load made
two gates red on 2026-10-23 and 2026-10-24, each costing a three-hour rerun today.

## Out of scope

Judging a result under load (VELDO-0223); how the gate uses its scope (VELDO-0216, VELDO-0219); jobs
that ignore the lock.

## What the reviewer judges

Normal use: the owner's runners and the lander start verify.sh on this host. Threat model: as in
VELDO-0208. Out of review scope: lock files on network file systems, and a holder file someone edits
by hand (it only changes the name printed).
