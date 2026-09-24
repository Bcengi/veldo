---
schema: veldo.spec/v1
id: VELDO-0041
title: Independent heartbeat, bounded stopping, and safe capacity retirement
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W26
plan_revision: 3
depends_on: [VELDO-0036, VELDO-0039, VELDO-0040]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/control_heartbeat*.py"
  - ".veldo/control_heartbeat*.py"
  - "packs/*/.veldo/control_heartbeat*.py"
  - "engine/.veldo/control_retirement*.py"
  - ".veldo/control_retirement*.py"
  - "packs/*/.veldo/control_retirement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "packs/*/.veldo/control_launch.py"
  - "engine/.veldo/control_containment.py"
  - ".veldo/control_containment.py"
  - "packs/*/.veldo/control_containment.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/*_veldo_0041_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0041-heartbeat-and-retirement.md"
  - "specs/index.md"
  - "proof/VELDO-0041/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The wrapper reports liveness independently of a blocking model response. Set and
      completeness: Run a real wrapper and blocked model child on Linux; observe ten-second
      heartbeats and claim renewal, then missing-heartbeat stop after the configured thirty-second
      window. Record actual monotonic timings. Falsifier: Emit heartbeats only after model return;
      the blocked-call liveness check must fail.
    falsified_by: >
      Emit heartbeats only after model return; the blocked-call liveness check must fail.
  - id: AC2
    text: >
      Claim: An accepted stop escalates to termination after ten seconds and killing remaining
      descendants after five more seconds. Set and completeness: Exercise a cooperative child and a
      signal-ignoring descendant under the real Linux group; observe the requested stop, signals and
      OS exit with declared measurement tolerance. Falsifier: Send termination only to the parent;
      the bounded group-exit check must fail.
    falsified_by: >
      Send termination only to the parent; the bounded group-exit check must fail.
  - id: AC3
    text: >
      Claim: Retirement follows actual termination and retains unresolved outcome/accounting/cleanup
      obligations. Set and completeness: Attempt retirement with a live descendant, missing
      accounting or remaining clone files, then complete each obligation and inspect the single
      capacity release. Falsifier: Release the slot before descendant termination; the retirement
      observation must fail.
    falsified_by: >
      Release the slot before descendant termination; the retirement observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Independent heartbeat, bounded stopping, and safe capacity retirement. Deliver the normal function needed by the running factory journey.

## Context

W26 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the trusted wrapper around a worker sends a heartbeat every ten seconds and renews the
  claim while the model call is still blocked, and a worker whose heartbeats stop for the configured
  thirty seconds is stopped. An accepted stop asks the worker to stop, terminates its whole VELDO-0040
  group after ten seconds and kills whatever remains five seconds later. Retirement happens only after
  the group has really ended, keeps each open obligation (unknown outcome, accounting, clone files)
  until it is completed, and releases the capacity slot exactly once.
- Threat model: a wrapper that reports liveness only when the model returns; a descendant that ignores
  signals; a stop sent only to the parent; and a retirement that releases the slot while a descendant is
  alive, with accounting missing or with clone files left. The owner's account, the user service manager
  and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); leadership
  fencing and timing, a stopped orchestrator and crash-safe retirement (Release 2, see History); other
  host kinds (Release 4; the Mac is VELDO-0124); a worker that deliberately escapes its group (Release 2,
  filed by VELDO-0040's review); forged rows in our own store, files planted in the installed directory
  and resource exhaustion by our own account.

## Notes

A heartbeat proves wrapper responsiveness, never effect success. Linux qualification is here;
the Mac must meet the same normal liveness/retirement semantics through its own profile.
Release 1 does not recover a stopped or failed orchestrator.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 leadership
fencing/timing, AC2 all-profile/stopped-orchestrator matrix and AC3 crash-safe retirement
moved to Release 2; broader hosts moved to Release 4. Normal liveness/stop/exit/retirement
remain. The criteria, declared evidence universe, Context and Notes above now carry only the
retained function. No specification status or historical proof was changed.

2026-09-24, footprint (branch build-veldo-0041): the footprint names `.veldo/control_launch.py`, where
the trusted wrapper emits the heartbeat and the VELDO-0039 receiver watches it, renews the claim and
stops a worker whose heartbeats stop; `.veldo/control_containment.py`, where the worker profile
declares the heartbeat interval and window beside VELDO-0040's stop graces and the stop escalation is
timed on the monotonic clock; and `scripts/check_teeth_mutations.py`, where this specification's
mutations are registered as finding 41.
