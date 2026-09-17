---
schema: veldo.spec/v1
id: VELDO-0031
title: Authority-backed claims and claim-generation fencing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W16
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0030]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/control_claim*.py"
  - ".veldo/control_claim*.py"
  - "packs/*/.veldo/control_claim*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0031_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0031-authority-backed-claims.md"
  - "specs/index.md"
  - "proof/VELDO-0031/*"
behavior_bearing: true
observability:
  logs: >
    Claim results identify owner, unit, claim and authority generations, expected version, and
    exact refusal reason.
  metrics: >
    Count contention winners, stale claim effects, uncertain leases, and reconciled versus blocked
    reclaims.
  traces: >
    Join claim.unit_id_problem, claim transaction, unit and backlog transition, and downstream
    permit validation.
  error_taxonomy: >
    Distinguish invalid unit ID, capability mismatch, already claimed, unanswerable clock, stale
    generation, and prior attempt unresolved.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The installed claim API routes enrolled ownership, unit transition, first-unit
      backlog activation, and increasing claim generation through one authority transaction. Set:
      Two real clone clients racing claim() for the same admitted unit through control.sqlite3,
      plus invalid unit aliases. Completeness: Enumerate claim API entry points and allowed unit
      transitions; race each ownership operation and SIGKILL after commit before response. Query
      exactly one owner and atomic lifecycle changes, prove no clone-local ledger writes, and
      invoke claim.unit_id_problem before artifacts. Falsifier: Commit ownership separately from
      the unit transition and kill between commits; claims/atomic-owner must detect partial
      ownership.
    falsified_by: >
      Commit ownership separately from the unit transition and kill between commits;
      claims/atomic-owner must detect partial ownership.
  - id: AC2
    text: >
      Claim: Every protected effect rejects old claim generations even after lease expiry or
      authority restart. Set: Claim renew, release, reclaim, and effect validation against the
      real store and accepting receiver process. Completeness: Hold an old worker at a barrier,
      reconcile and fence its attempt, issue a higher generation, then resume the old worker.
      Check every registered effect permit kind and ensure the old worker cannot release or
      overwrite its successor claim. Falsifier: Check only lease expiry when the old worker
      resumes after reclaim; claims/stale-generation must catch its accepted effect.
    falsified_by: >
      Check only lease expiry when the old worker resumes after reclaim; claims/stale-generation
      must catch its accepted effect.
  - id: AC3
    text: >
      Claim: Reclaim requires fencing and effect reconciliation, and clock disagreement preserves
      unanswerable without granting takeover. Set: Real claim records with fresh, expired,
      future-beyond-tolerance, and malformed timestamps and receiver states running, unknown, and
      reconciled. Completeness: Drive the liveness/receiver matrix using installed claim.liveness
      and a real second claimant; SIGKILL the former worker after target acceptance and require no
      reclaim from process absence alone. Record both clock readings and tolerance and retain the
      original holder on uncertainty. Falsifier: Treat _is_stale false as proof of liveness for a
      future heartbeat; claims/unanswerable must retain the named uncertainty and block affected
      dispatch.
    falsified_by: >
      Treat _is_stale false as proof of liveness for a future heartbeat; claims/unanswerable must
      retain the named uncertainty and block affected dispatch.
required_evidence: [unit, integration]
rollback: >
  Stop enrolled claims and effects, retain owners and generation counters, and reconcile attempts
  before any compatible implementation resumes.
---

## Intent

Preserve one claim API while making enrolled ownership and generation changes atomic across clones.

## Context

Package B, W16 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R10-R11, R24-R25, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Incorrect claim ownership or generation checks could permit concurrent work and stale publication. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

No second claim API, scheduler rewrite, or reporting UI is introduced.

## Notes

D1 is inherited through leadership and storage. VELDO-0015 already implements clock stand-down; preserve its canonical detector and boolean reclaim contract. W17 through W19 repair consumers, not clock arithmetic. Unenrolled compatibility must remain explicit and must never become a fallback for an enrolled repository.

