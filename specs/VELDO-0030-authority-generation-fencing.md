---
schema: veldo.spec/v1
id: VELDO-0030
title: Exclusive leadership and authority-generation fencing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W15
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0029]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_leader*.py"
  - ".veldo/control_leader*.py"
  - "packs/*/.veldo/control_leader*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0030_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0030-authority-generation-fencing.md"
  - "specs/index.md"
  - "proof/VELDO-0030/*"
behavior_bearing: true
observability:
  logs: >
    Leadership events identify stable lock inode, host and boot identity, generation,
    control-channel state, and recovery barrier.
  metrics: >
    Measure leader contenders, stale-generation refusals, channel-loss-to-fence latency, and
    unresolved prior effects.
  traces: >
    Join OS lock acquisition and recovery completion to generation commit and every issued permit.
  error_taxonomy: >
    Distinguish lock held, recovery incomplete, generation stale, control channel lost, and
    conflicting effect unresolved.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A stable exclusive OS lock permits only one scheduling session and a new generation
      commits only after startup recovery checks. Set: Two real authority processes sharing
      control.sqlite3 and one stable store lock file, across start, death, and restart.
      Completeness: Race starts in both orders; record lock inode, generation rows, and accepted
      scheduling calls. SIGKILL the winner during recovery and after generation commit; the
      replacement must not delete the lock file or skip reconciliation. Falsifier: Delete and
      recreate the lock file to steal leadership while the first process holds its inode;
      leadership/two-inodes must detect concurrent sessions.
    falsified_by: >
      Delete and recreate the lock file to steal leadership while the first process holds its
      inode; leadership/two-inodes must detect concurrent sessions.
  - id: AC2
    text: >
      Claim: Independent runner and effect acceptance close within two seconds of leadership or
      supervisor control-channel loss, even when the orchestrator is suspended. Set: Launch,
      claim, publication, and worker-capability permits bound to authority generation, using real
      separate accepting processes. Completeness: SIGSTOP the leader, close its control socket,
      and inject lock loss at separate barriers; timestamp attempted acceptance with an
      independent monotonic observer. SIGCONT the old process after replacement and require
      stale-generation rejection on every registered permit kind. Falsifier: Use only a timer
      inside the orchestrator to detect control-channel loss, then SIGSTOP it;
      leadership/two-second-fence must catch continued receiver acceptance.
    falsified_by: >
      Use only a timer inside the orchestrator to detect control-channel loss, then SIGSTOP it;
      leadership/two-second-fence must catch continued receiver acceptance.
  - id: AC3
    text: >
      Claim: Replacement leadership cannot authorize conflicting work until accepted prior effects
      are reconciled or safely quarantined. Set: Real receiver effects accepted before authority
      death, with running, committed, and unknown observations and reserved exposure.
      Completeness: Kill the leader after receiver acceptance, restart it, and request conflicting
      and independent work. Compare durable recovery decisions and reservations; only demonstrably
      nonconflicting work within retained exposure may resume. Falsifier: Clear outstanding
      effects when the generation increments and request a conflicting dispatch;
      leadership/unresolved-effect must refuse it.
    falsified_by: >
      Clear outstanding effects when the generation increments and request a conflicting dispatch;
      leadership/unresolved-effect must refuse it.
required_evidence: [unit, integration]
rollback: >
  Close permit acceptance, stop scheduling, retain the stable lock file and generation history,
  and recover through the compatible leader startup path.
---

## Intent

Prevent an old or stalled authority from authorizing new dispatch or effects after leadership changes.

## Context

Package B, W15 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R24, R26, R39, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Split leadership could authorize conflicting dispatches and external effects. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Claim generation belongs to W16; automatic host failover is excluded.

## Notes

D1 is inherited through storage and D3 blocks production supervisor activation. This item owns the lock and generation acceptance protocol; W25 supplies the qualified containment implementation. Its tests use real independent receiver processes so a stopped orchestrator cannot forge liveness. Host replacement is never inferred from an unreachable old process and is qualified in W33.

