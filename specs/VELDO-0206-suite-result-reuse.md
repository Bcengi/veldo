---
schema: veldo.spec/v1
id: VELDO-0206
title: Exact input suite result reuse in the canonical gate
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0205]
placement: [enforcement]
protected_paths: ["scripts/verify.sh"]
footprint:
  - "scripts/verify.sh"
  - "scripts/selftest.py"
  - "scripts/run_scope.py"
  - "scripts/gate_reuse.py"
  - "scripts/suites/*_veldo_0206_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0206-suite-result-reuse.md"
  - "specs/index.md"
  - "proof/VELDO-0206/*"
behavior_bearing: true
observability:
  logs: Emit suite identity, exact closure key and fresh or reused source for every suite result.
  metrics: Exact per-stage fresh and reused counts with complete suite coverage.
  traces: Bind suite results to interpreter, tools, closure and dispatcher identities.
  error_taxonomy: Unknown closure, corrupt record and missing state are misses; failing suites stay failures.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A suite hit requires an exact complete input and execution-state closure. Set: every
      manifest suite and prerequisite, including the shared namespace and side effects. Completeness:
      explicitly qualify each reusable suite, include prior suite state or isolate it equivalently,
      and prove every changed input misses and an untouched qualified suite hits in suite-reuse/closure.
    falsified_by: Drop prerequisite state from the key; suite-reuse/closure must turn false.
  - id: AC2
    text: >
      Claim: Only authenticated passing observations can replace a fresh suite. Set: failed,
      timed-out, partial, corrupt and passing runs. Completeness: drive each through the VELDO-0205
      store and the real dispatcher in suite-reuse/pass-only; a cached selector run cannot verify.
    falsified_by: Accept a partial run as a full passing suite; suite-reuse/pass-only must turn false.
  - id: AC3
    text: >
      Claim: Every gate receipt has exact suite keys and fresh/reused counts, preserving full
      manifest coverage and force-fresh landing policy. Set: cold, warm, mixed and force-fresh runs.
      Completeness: drive all cases and planted stale records in suite-reuse/receipts, with a fresh
      failure remaining red even when other suites hit.
    falsified_by: Ignore a fresh failure after a cache hit; suite-reuse/receipts must turn false.
required_evidence: [unit, integration]
rollback: Revert suite reuse and keep mutation reuse and its authenticated store independently usable.
---

## Intent and status

Ready, intentionally unimplemented. Second concern split from VELDO-0205 under the owner's
2026-10-06 Telegram 31900 approval of the design in Telegram 31622. Suite execution currently shares
a mutable Python namespace, so dependency names alone cannot justify reuse. Preserve every current
assertion and partial-run refusal. Do not pretend the mutation closure proves suite isolation.

## What the reviewer judges

Normal use is the complete repository gate and its current suite dispatcher. Stale inputs, changed
prerequisites, corrupted records, false counts and lost side effects are in scope. Reuse of the
private store follows VELDO-0205's threat boundary. Unknown closures always execute fresh.

## Protected path

scripts/verify.sh requires high-risk review and exact commit/proof-bound owner approval under
.veldo/policy.yaml before landing. The design approval is not that final approval. Canonical release
and landing gates retain VELDO_GATE_FORCE_FRESH=1.
