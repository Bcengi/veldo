---
schema: veldo.spec/v1
id: VELDO-0226
title: A key is reused only after a sensitivity proof shows its case ignores the clock and randomness
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0217, VELDO-0218, VELDO-0219, VELDO-0222, VELDO-0224]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/case_trace.py", "engine/scripts/case_trace.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", "scripts/mutation_reuse.py", "engine/scripts/mutation_reuse.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/mutation_reuse.py
  - engine/scripts/mutation_reuse.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0226_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0226-a-reused-key-carries-a-clock-and-randomness-sensitivity-proof.md
  - specs/index.md
  - proof/VELDO-0226/*
behavior_bearing: true
observability:
  logs: For each key proved, the stage names the case, both perturbed runs, whether the perturbation reached every process, and every field that differed.
  metrics: Keys proved, insensitive, sensitive and unperturbable per stage; the share of reviewed cases that pass; the proof runs' worker seconds.
  traces: Each proof record in the authority store binds the key, the three observation sets' digests, the perturbation parameters and the gate run.
  error_taxonomy: Any difference is clock_or_random_sensitive and the case stays fresh for that key; a process the perturbation did not reach is unperturbable and the case stays fresh; neither is red.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the first time a reviewed key is fresh in a gate, the coordinator runs its baseline,
      no-op and mutant twice more beside the original: once with the wall and monotonic clocks
      moved exactly 400 days forward and running at 1.5 times real speed (libfaketime preloaded
      into every process of the traced tree, the private user manager of VELDO-0222 and its units
      included), and once with different randomness (PYTHONHASHSEED 1 instead of the fixed worker
      environment's 0; getrandom itself unchanged). A reused record is never older than 30 days
      (an older one is not reused: the case runs fresh and publishes again), so the offset is
      larger than the age of any record the proof vouches for. The key
      may be reused only when the verdict, the named target rows and the full baseline, no-op and
      mutant observation arrays are identical across all three runs. Set: a fixture case that
      branches on the current time, one that prints a random value into an observation, one whose
      observations depend on neither, and one that sorts by hash order. Completeness: row
      sensitivity/three-runs requires the first, second and fourth to stay fresh as
      clock_or_random_sensitive and only the third to be marked insensitive.
    falsified_by: >
      Skip the clock-perturbed run. Registered mutant sensitivity226-no-clock-run must fail
      sensitivity/three-runs on the case that branches on the time.
  - id: AC2
    text: >
      Claim: the perturbation must reach every process of the case or the case stays fresh: from the
      trace, every executed program must be dynamically linked and must have the preloaded library
      mapped at load (the dynamic loader maps it before the program's own code runs), and the
      private manager must pass the preload and the offset to
      every unit it starts; a statically linked program, a set-id program or a unit without the
      preload makes the case unperturbable. The same holds when libfaketime is not installed on the
      host. Set: a fixture case that runs a statically linked helper, one whose unit drops the
      environment, and a host without the library. Completeness: row sensitivity/reaches-every-
      process requires all three fresh as unperturbable.
    falsified_by: >
      Accept the proof when one child process did not map the preloaded library. Registered mutant
      sensitivity226-partial-preload must fail sensitivity/reaches-every-process.
  - id: AC3
    text: >
      Claim: the proof belongs to the key: it is recorded in the authority store (never in the
      candidate tree) with the key, lookup reuses a record only when an insensitive proof for that
      exact key is present and the record is at most 30 days old, and any key change requires a new
      proof before reuse. The sample audit
      of VELDO-0218 still runs on top. Set: a proved key, the same case after an input edit, a
      record whose proof entry was removed, and a proved record 31 days old. Completeness: row
      sensitivity/bound-to-key requires the first reusable, the second fresh with a new proof
      attempt, and the third and fourth fresh.
    falsified_by: >
      Reuse a record whose key has no proof entry. Registered mutant sensitivity226-proof-optional
      must fail sensitivity/bound-to-key.
required_evidence: [unit, integration]
rollback: Revert the proof; case_reuse then qualifies nothing, as VELDO-0217 does while no proof exists.
---

## Intent

The clock (read through the vDSO, which strace never sees) and the values of random bytes cannot be
keyed. The owner's ruling (through the coordinator, 2026-10-25) settles them by a mechanical
sensitivity proof rather than by tracing or by the audit alone: a key is reused only after its case
has produced identical results with the clock moved and with randomness changed.

## Design

The proof runs as two extra fresh jobs per mode for a key that has none, scheduled through the
ledger like any worker. The clock run preloads libfaketime with the setting +400d x1.5, which moves
the wall and monotonic clocks 400 days forward and runs them at 1.5 times real speed, set by the authority's bootstrap for the worker tree and by the private manager's own
configuration for its units (VELDO-0222), so a confined and an unconfined case are perturbed alike.
libfaketime replaces the C library's time functions, which Python's clock calls go through. The
randomness run changes PYTHONHASHSEED from 0 to 1; getrandom
stays as it is, so a case whose observations show raw random bytes still differs between the
original and either run by chance and is refused.

libfaketime is not installed on the qualification host (Ubuntu offers 0.9.10, GPL-2.0, used as a
host tool and not redistributed). Installing it is a step for the owner; until then AC2 keeps every
case fresh.

Cost: three times the work for each key the first time it runs fresh, nothing after that until its
key changes. On a landing, only invalidated keys pay it, about 3 to 7 percent of cases.

Expected share passing: unmeasured. One signal from 2026-10-25: comparing two fresh runs of 2,566
cases, four differed in non-target observations (timing-sensitive), so at least those would fail
the proof; how many depend on the clock or hash order under a large offset is not known until the
first proof pass, and the proof records it.

## Out of scope

Tracing file inputs (VELDO-0217, VELDO-0222); the audit (VELDO-0218); changing a case to make it
insensitive.

## What the reviewer judges

Normal use: landing gates with reviewed declarations on the owner's host. Threat model: as in
VELDO-0208. Out of review scope: a case whose result depends on the clock only at offsets or rates
the proof did not try; the stated parameters are the accepted bound.
