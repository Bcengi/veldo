---
schema: veldo.spec/v1
id: VELDO-0038
title: Effect-specific reconciliation and recovery commands
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W23
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0028, VELDO-0030, VELDO-0031, VELDO-0035, VELDO-0036]
placement: [fleet, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_recovery*.py"
  - ".veldo/control_recovery*.py"
  - "packs/*/.veldo/control_recovery*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0038_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0038-effect-recovery-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0038/*"
behavior_bearing: true
observability:
  logs: >
    Recovery records name original dispatch, receiver, evidence digests, finding, outstanding
    effects, and resolving authority.
  metrics: >
    Count the five recovery findings separately, unresolved obligations, bounded retries,
    compensation attempts, and contradictory evidence.
  traces: >
    Join receiver outcome query to signed ruling, original nonce and attempt, fencing receipt, and
    any separately authorized retry or compensation.
  error_taxonomy: >
    Distinguish conclusive nonexecution, running, effect committed, acknowledgement lost, outcome
    unknown, evidence conflict, and unauthorized resolution.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each autonomously available effect declares a receiver, idempotency scope, acceptance
      evidence, outcome query, success predicate, retry conditions, compensation, and resolving
      authority. Set: Registered Git publication, worker launch, and any enabled tracker
      correlation adapters, exercised with actual receiver processes and target state.
      Completeness: Compare the effect registry to R74 required fields; remove each field and
      attempt dispatch through the real store. Query real bare-remote commit ancestry and durable
      local receiver records; unqualified tracker adapters stay disabled until their real target
      proof in E. Falsifier: Enable a receiver without an uncertain-outcome query or stopping
      procedure and kill after send; recovery/unqualified-effect must have refused dispatch before
      uncertainty arose.
    falsified_by: >
      Enable a receiver without an uncertain-outcome query or stopping procedure and kill after
      send; recovery/unqualified-effect must have refused dispatch before uncertainty arose.
  - id: AC2
    text: >
      Claim: Recovery commands distinguish all five R32 findings from trusted evidence and never
      equate absent processes, lost checkpoints, expired leases, or consumed nonces with
      nonexecution. Set: Attach-evidence, import-acknowledgement, certify-nonexecution, fence, and
      retain-stop commands against real control.sqlite3 and effect receivers. Completeness: Create
      each finding with actual barriers and SIGKILL after receiver acceptance or commit but before
      authority acknowledgement; invoke signed recovery commands and compare persisted evidence
      and target operation counts. Feed contradictory local observations and require outcome
      unknown with AWAITING_AUTHORITY. Falsifier: Certify nonexecution from a consumed nonce and
      absent PID after a real target commit; recovery/false-nonexecution must reject the ruling.
    falsified_by: >
      Certify nonexecution from a consumed nonce and absent PID after a real target commit;
      recovery/false-nonexecution must reject the ruling.
  - id: AC3
    text: >
      Claim: Retry and compensation require current authorization, fencing, recorded duplicate
      risk, and separate identities while preserving unknown historical effects. Set: Concurrent
      signed bounded-retry, compensation, and retain-stop commands for one unresolved dispatch.
      Completeness: Race opposing resolutions at one expected version, kill after resolution
      commit before reply, and retry by original command ID. Require one accepted decision, a new
      contracted compensation effect with its own receipt, retained exposure, and no rewriting of
      the original finding into certainty. Falsifier: Reuse original effect permission for
      compensation after a competing revocation commits; recovery/compensation-authority must
      observe zero compensation calls.
    falsified_by: >
      Reuse original effect permission for compensation after a competing revocation commits;
      recovery/compensation-authority must observe zero compensation calls.
required_evidence: [unit, integration]
rollback: >
  Keep unresolved effects stopped, preserve receiver evidence and signed rulings, and disable new
  retries or compensation until a compatible recovery reader is available.
---

## Intent

Give operations explicit evidence-driven recovery commands before crash handling can authorize another attempt.

## Context

Package B, W23 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R26-R27, R32-R33, R41, R57, R74. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

No automatic host failover, universal exactly-once claim, or live tracker activation is supplied.

## Notes

D1 and D2 are inherited through journal and replication; D3 and D4 remain barriers for recovery of production runner and clone profiles. Recovery commands must exist before dependent launch crash tests. Accepted rulings may originate on any enrolled qualified channel, with one authoritative settlement; retained tracker-only wording does not impose a tracker prerequisite. An explicit accepted-risk disposition closes an operational obligation without inventing historical certainty.

