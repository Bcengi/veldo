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
    Measure checkpoint transaction duration, domain-write latency, busy refusals, denied
    cross-namespace attempts, and quarantine counts.
  traces: >
    Join trusted checkpoint requests to permitted table effects and independent before/after
    domain-history digests.
  error_taxonomy: >
    Distinguish cross-namespace write, indirect write, forbidden database attachment, lock-budget
    exhaustion, logical checkpoint damage, and physical database damage.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A trusted checkpoint boundary restricts adapter writes to its own tables in
      control.sqlite3 and gives model processes no database path, handle, or filesystem access.
      Set: Real adapter, boundary, and model child processes attempting direct SQL plus trigger,
      view, foreign-key, ATTACH, PRAGMA, extension, and schema-mediated writes. Completeness:
      Derive permitted operations from the checkpoint API and SQLite connection configuration;
      execute each prohibited route against the actual shared file, including inherited file
      descriptors and filesystem attempts by the model child. Compare domain table and journal
      digests before and after every attack. Falsifier: Allow a checkpoint trigger to update a
      domain entity during a legitimate checkpoint insert; checkpoints/indirect-write must detect
      and refuse the domain mutation.
    falsified_by: >
      Allow a checkpoint trigger to update a domain entity during a legitimate checkpoint insert;
      checkpoints/indirect-write must detect and refuse the domain mutation.
  - id: AC2
    text: >
      Claim: Checkpoint activity cannot hold domain transactions beyond the declared contention
      budget and cannot change their outcomes. Set: Concurrent real domain writers and checkpoint
      processes under the supported SQLite journal and busy-timeout configuration. Completeness:
      Set a finite documented contention bound before qualification; hold an adapter transaction
      open, SIGSTOP its process, and race signed domain commands. Observe bounded cancellation or
      refusal and deterministic command results, with no silent retry allocating fresh command
      IDs. Falsifier: Leave a stalled checkpoint write transaction without a bounded timeout and
      SIGSTOP its owner; checkpoints/contention-deadline must detect the blocked domain writer.
    falsified_by: >
      Leave a stalled checkpoint write transaction without a bounded timeout and SIGSTOP its
      owner; checkpoints/contention-deadline must detect the blocked domain writer.
  - id: AC3
    text: >
      Claim: Logical checkpoint corruption may be quarantined only after domain integrity is
      proven; deleting all checkpoint data leaves authoritative history and effect identity
      intact. Set: Real shared SQLite files with malformed checkpoint content, deleted checkpoint
      tables, and physical file-page corruption in disposable copies. Completeness: Corrupt each
      damage class, restart the boundary, and compare signed replay with materialized domain
      state. Domain-intact checkpoint loss restarts the graph using committed results; unproven
      physical integrity stops dispatch and preserves damaged bytes. Falsifier: Classify a
      physically damaged shared database as checkpoint-only and resume dispatch without verified
      replay; checkpoints/physical-corruption must refuse startup.
    falsified_by: >
      Classify a physically damaged shared database as checkpoint-only and resume dispatch without
      verified replay; checkpoints/physical-corruption must refuse startup.
required_evidence: [unit, integration]
rollback: >
  Disable checkpoint writes, preserve suspect database material, prove domain integrity, and
  quarantine only proven logical checkpoint damage before using the replacement adapter.
---

## Intent

Confine checkpoint writes inside the one authority database without exposing domain tables or unbounded contention.

## Context

Package B, W29 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R21, R27, R34-R35, R57. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Replica restoration is W33; dependency packaging is W30; no second domain database is introduced.

## Notes

D1 directly blocks the shared SQLite placement until Dmitry rules. An adapter-owned namespace in a shared file is not enforced by table naming conventions alone; qualify the actual authorizer or broker restrictions against indirect writes. A trusted broker process may hold the connection, but model processes must not. State the finite contention budget in accepted configuration before ready.

