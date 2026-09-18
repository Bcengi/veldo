---
schema: veldo.spec/v1
id: VELDO-0026
title: Revocation and authorization rechecks
status: shipped
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W11
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_revocation*.py"
  - ".veldo/control_revocation*.py"
  - "packs/*/.veldo/control_revocation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/architecture.yaml"
  - "scripts/suites/*_veldo_0026_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0026-authorization-rechecks.md"
  - "specs/index.md"
  - "proof/VELDO-0026/*"
behavior_bearing: true
observability:
  logs: >
    Revocation records name principal, scope, revision, boundary, outstanding operation, and
    closure reason.
  metrics: >
    Count rejected stale capabilities, queued invalidations, stop obligations, and unresolved
    accepted effects.
  traces: >
    Join the revocation journal sequence to each acceptance decision, stop request, and final
    reconciliation receipt.
  error_taxonomy: >
    Distinguish revoked membership, stale policy or scope, invalid decision or dependency,
    in-flight effect, and denial-record failure.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Current authorization is checked at every accepting boundary, including indirectly
      referenced revisions. Set: Command acceptance, proposal commit, assignment acceptance,
      claim, dispatch acceptance, privileged-tool use, result acceptance, decision settlement, and
      landing publication. Completeness: Match these nine R39 boundaries to callable service
      registrations. Separate processes change membership, policy, scope, decision, and dependency
      records in real SQLite after a snapshot but before boundary acceptance; each applicable pair
      must refuse with its named reason. Falsifier: Skip the indirect dependency revision check at
      effect acceptance while another process withdraws that prerequisite;
      revocation/indirect-dependency must observe refusal.
    falsified_by: >
      Skip the indirect dependency revision check at effect acceptance while another process
      withdraws that prerequisite; revocation/indirect-dependency must observe refusal.
  - id: AC2
    text: >
      Claim: Revocation and protected effect acceptance share one serialized order, invalidate
      queued capabilities, and request stop for affected running work. Set: Both race orders
      between stored revocation and a real receiver process accepting an effect, with queued and
      already accepted operations. Completeness: Use process barriers at the transaction boundary
      and SIGKILL after revocation commit before notification. Replay must restore stop
      obligations; a receiver accepted first remains in-flight until evidence resolves it, while
      revocation first allows zero new effects. Falsifier: Report effective closure immediately
      after revocation even when the receiver accepted first and is still running;
      revocation/in-flight-closure must fail.
    falsified_by: >
      Report effective closure immediately after revocation even when the receiver accepted first
      and is still running; revocation/in-flight-closure must fail.
  - id: AC3
    text: >
      Claim: Revoked outputs remain evidence without satisfying obligations, and a denial that
      cannot be durably recorded stays denied and stops dispatch. Set: Result acceptance and every
      registered denial-writing boundary against the real store, including disk-write failure and
      restart. Completeness: Submit real artifact bytes before and after revocation and fault the
      denial transaction at its SQLite commit. Compare artifact retention, obligation state,
      dispatch permission, and durable reason records; fresh authorization must be explicitly
      version-bound. Falsifier: Allow dispatch after injecting a denial-journal write failure;
      revocation/denial-storage-failure must require stand-down.
    falsified_by: >
      Allow dispatch after injecting a denial-journal write failure;
      revocation/denial-storage-failure must require stand-down.
required_evidence: [unit, integration]
rollback: >
  Fail affected authorization closed, preserve revocation and output evidence, and keep unresolved
  operations stopped until authorized reconciliation.
---

## Intent

Order revocation with effect acceptance and remove affected permissions at every accepting boundary.

## Context

Package B, W11 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R14, R39, R50, R57, R69-R70. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

A missed revocation could allow work to execute or publish after its permission was withdrawn. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Live provider qualification and retroactive cancellation guarantees are excluded.

## Notes

D1 is inherited through membership and journal dependencies. This item implements reusable acceptance guards and durable stop obligations; later floor and channel consumers must invoke them, and their end-to-end proof remains C and E. A real local receiver can prove serialized acceptance without pretending that revocation can undo an external effect.

