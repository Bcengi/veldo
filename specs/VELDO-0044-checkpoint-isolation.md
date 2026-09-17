---
schema: veldo.spec/v1
id: VELDO-0044
title: Checkpoint namespace isolation and bounded contention
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W29
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0043]
placement: [contracts, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_checkpoint*.py"
  - ".veldo/control_checkpoint*.py"
  - "packs/*/.veldo/control_checkpoint*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0044_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0044-checkpoint-isolation.md"
  - "specs/index.md"
  - "proof/VELDO-0044/*"
behavior_bearing: true
observability:
  logs: >
    Checkpoint diagnostics identify adapter operation, allowed namespace, rejected SQL capability,
    and contention deadline.
  metrics: >
    Measure checkpoint transaction duration, domain-write latency, busy refusals, holder
    cancellation latency, denied cross-namespace attempts, and quarantine counts.
  traces: >
    Join trusted checkpoint requests to permitted table effects and independent before/after
    domain-history digests.
  error_taxonomy: >
    Distinguish cross-namespace read, cross-namespace write, indirect write, forbidden database
    attachment, lock-budget exhaustion, holder cancellation failure, logical checkpoint damage,
    and physical database damage.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A trusted checkpoint boundary restricts adapter reads and writes to its own tables
      in control.sqlite3, refuses domain reads, and gives model processes no database path,
      handle, or filesystem access. Set: Real adapter, boundary, and model child processes
      attempting direct SELECT, INSERT ... SELECT, views and triggers reading domain tables,
      ATTACH of the same file under another schema name, and direct SQL plus trigger, view,
      foreign-key, ATTACH, PRAGMA, extension, and schema-mediated writes. Completeness:
      Derive permitted operations from the checkpoint API and SQLite connection configuration;
      execute each prohibited route against the actual shared file, including inherited file
      descriptors and filesystem attempts by the model child. Enumerate every domain table from
      the domain schema, including membership, decision, and reservation tables, seed domain
      rows, and require a refused read for each table through every applicable read route.
      Compare domain table and journal digests before and after every attack; unchanged digests
      do not prove read isolation. Falsifier: Allow a successful INSERT ... SELECT of a domain
      row into a checkpoint table; checkpoints/cross-namespace-read must detect the copied row.
    falsified_by: >
      Allow a successful INSERT ... SELECT of a domain row into a checkpoint table;
      checkpoints/cross-namespace-read must detect the copied row.
  - id: AC2
    text: >
      Claim: The trusted checkpoint boundary owns the adapter connection and independently
      cancels the lock holder within the declared contention budget so domain writes recover;
      checkpoint activity cannot change domain command outcomes. Cancellation uses sqlite3
      interrupt on the owning connection with transaction rollback or termination of the owning
      process, and must release the lock without cooperation from the stalled adapter.
      Set: Concurrent real domain writers issuing signed commands, including a revocation, and
      checkpoint writers SIGSTOPped while holding a write transaction under every supported
      SQLite journal and busy-timeout configuration. Completeness: Declare finite contention
      and domain-command completion bounds before qualification; confirm the checkpoint write
      lock, SIGSTOP its owner, and issue the signed commands. Measure from first contention to
      holder cancellation and lock release, require both within the contention budget, then
      require the revocation and subsequent domain writes to commit within the command bound.
      Verify deterministic command results with no silent retry allocating fresh command IDs;
      bounded refusal of a waiter alone is insufficient. Falsifier: Rely on busy timeout alone
      and SIGSTOP the holder; checkpoints/holder-cancellation must detect that the revocation
      never commits.
    falsified_by: >
      Rely on busy timeout alone and SIGSTOP the holder; checkpoints/holder-cancellation must
      detect that the revocation never commits.
  - id: AC3
    text: >
      Claim: Logical checkpoint corruption may be quarantined only after domain integrity is
      proven; deleting all checkpoint data leaves authoritative history and effect identity
      intact. Set: Real shared SQLite files with malformed checkpoint content, deleted checkpoint
      tables, and physical file-page corruption in disposable copies. Completeness: Corrupt each
      damage class, restart the boundary, and compare signed replay with materialized domain
      state. Domain-intact checkpoint loss restarts the graph using committed results; unproven
      physical integrity stops dispatch and preserves damaged bytes. Falsifier: Quarantine
      malformed checkpoint payloads without domain replay after also corrupting a domain entity
      version in a readable SQLite file; checkpoints/mixed-corruption must refuse startup.
    falsified_by: >
      Quarantine malformed checkpoint payloads without domain replay after also corrupting a
      domain entity version in a readable SQLite file; checkpoints/mixed-corruption must refuse
      startup.
required_evidence: [unit, integration]
rollback: >
  Disable checkpoint writes, preserve suspect database material, prove domain integrity, and
  quarantine only proven logical checkpoint damage before using the replacement adapter.
---

## Intent

Confine checkpoint reads and writes inside the one authority database without exposing domain tables or unbounded contention.

## Context

Package B, W29 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R21, R27, R34-R35, R44, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Checkpoint SQL or shared-file corruption could alter authoritative history or prevent enforcement from progressing. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Replica restoration is W33; dependency packaging is W30; no second domain database is introduced.

## Notes

D1 directly blocks the shared SQLite placement until Dmitry rules. An adapter-owned namespace in a shared file is not enforced by table naming conventions alone; qualify the actual authorizer or broker restrictions against direct and indirect reads and writes. The trusted checkpoint boundary owns the connection and must cancel a stalled lock holder independently; model processes must not hold it. State finite contention and domain-command completion bounds in accepted configuration before ready.
