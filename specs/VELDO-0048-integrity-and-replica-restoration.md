---
schema: veldo.spec/v1
id: VELDO-0048
title: Integrity verification, replica restoration, and host-replacement fencing
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W33
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0038, VELDO-0047]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_integrity*.py"
  - ".veldo/control_integrity*.py"
  - "packs/*/.veldo/control_integrity*.py"
  - "engine/.veldo/control_restore*.py"
  - ".veldo/control_restore*.py"
  - "packs/*/.veldo/control_restore*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0048_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0048-integrity-and-replica-restoration.md"
  - "specs/index.md"
  - "proof/VELDO-0048/*"
behavior_bearing: true
observability:
  logs: >
    Startup and restore reports identify store, replica export, integrity stage, generation,
    old-host fencing evidence, and unresolved tail.
  metrics: >
    Count invalid signatures, sequence gaps, artifact mismatches, replay disagreements,
    quarantined stores, and unresolved restored effects.
  traces: >
    Join preserved damaged bytes to verified replica chain, operations ruling, host isolation and
    credential revocation, new generation, and outcome reconciliation.
  error_taxonomy: >
    Distinguish physical corruption, journal corruption, missing tail, derived-state mismatch,
    checkpoint-only damage, unfenced host, and incompatible schema reader.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Startup verifies database integrity, signatures, sequence and hash-chain continuity,
      artifact digests, and replay agreement before scheduling. Set: Real SQLite stores and signed
      exports with corruption in each authoritative component and separately damaged derived or
      checkpoint data. Completeness: Generate valid history, corrupt one component at a time, kill
      startup during verification, and restart. Assert zero dispatch for invalid authority,
      preserved original damage, and derived-table rebuild only from verified complete history;
      physical damage cannot be waved away as checkpoint-only. Falsifier: Truncate an unexplained
      journal record and continue startup; integrity/no-truncation must detect accepted dispatch
      from incomplete history.
    falsified_by: >
      Truncate an unexplained journal record and continue startup; integrity/no-truncation must
      detect accepted dispatch from incomplete history.
  - id: AC2
    text: >
      Claim: Restoration imports the verified signed Git replica and artifacts, retains
      acknowledged history, and records any missing unpublished tail as uncertainty. Set:
      Authority process or clone loss after local commit, export publication, and remote
      acknowledgement boundaries using real Git remotes and disposable stores. Completeness:
      SIGKILL the authority at each barrier, remove access to its clone, and restore on a
      replacement fixture from actual replica commits. Compare every acknowledged command and
      artifact with restored history, reconcile target effects through W23, and require pending
      unknown work to stay stopped without repeat delivery. Falsifier: Treat the absent
      unpublished tail as proof its accepted target effect never ran; restoration/missing-tail
      must detect the unsafe redispatch.
    falsified_by: >
      Treat the absent unpublished tail as proof its accepted target effect never ran;
      restoration/missing-tail must detect the unsafe redispatch.
  - id: AC3
    text: >
      Claim: Replacement authority activates only after the operations authority proves the old
      host cannot execute or publish, then commits a new generation and reconciles outstanding
      effects. Set: Two real fixture hosts or isolated host environments with separate
      credentials, receiver processes, and a protected Git remote. Completeness: Partition the old
      host while its worker remains live and require refusal based on silence alone. Apply
      evidenced host isolation, credential revocation, and publication-authority removal, restore
      the replica, then resume the old processes and attempt real receiver calls and Git ref
      updates; all stale authority must be rejected. Falsifier: Accept network silence as fencing
      while the old worker still reaches the bare remote; restoration/unfenced-host must detect
      its surviving publication ability.
    falsified_by: >
      Accept network silence as fencing while the old worker still reaches the bare remote;
      restoration/unfenced-host must detect its surviving publication ability.
  - id: AC4
    text: >
      Claim: A previous known-good release and compatible reader remain usable through
      qualification, and restore interruption never activates an empty or partially imported
      authority. Set: Versioned restore/import stages and supported previous/current reader
      combinations over real restored SQLite files. Completeness: Kill import before and after
      history verification and generation commit, restart with each compatible reader, and compare
      activation markers and state digests. An incompatible reader refuses without implicit schema
      downgrade; client clone replacement requires reenrollment and authority clone replacement
      requires this controlled path. Falsifier: Initialize an empty authority when restore import
      is interrupted before verification; restoration/partial-import must detect scheduling
      without imported history.
    falsified_by: >
      Initialize an empty authority when restore import is interrupted before verification;
      restoration/partial-import must detect scheduling without imported history.
required_evidence: [unit, integration]
rollback: >
  Keep the replacement stopped, preserve old and restored stores plus fencing evidence, and use
  the last compatible release only after verified history and unresolved-effect checks.
---

## Intent

Recover authority only from verified history with explicit old-host fencing and preserved uncertainty for unpublished work.

## Context

Package B, W33 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R23-R27, R32, R57, R63, R74-R75. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Automatic failover, production remote provisioning, and the full H combined operational qualification remain outside this foundation item.

## Notes

D1 directly blocks the authority and replica restoration design until Dmitry rules. D2 determines the acknowledged history guarantee, and D3 blocks replacement-service activation on an unqualified host. A local bare remote proves protocol recovery only; host-loss survival requires separately established off-host durability and actual old-host fencing evidence. Preserve damaged stores as evidence and use signed operations commands for reconciliation, never truncate until green.

