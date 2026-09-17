---
schema: veldo.spec/v1
id: VELDO-0039
title: Durable dispatch acceptance and launch records
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W24
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0031, VELDO-0035, VELDO-0036, VELDO-0038]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_dispatch*.py"
  - ".veldo/control_dispatch*.py"
  - "packs/*/.veldo/control_dispatch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0039_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0039-durable-dispatch-acceptance.md"
  - "specs/index.md"
  - "proof/VELDO-0039/*"
behavior_bearing: true
observability:
  logs: >
    Dispatch diagnostics identify unit, station, attempt, contract, reservation, both generations,
    and receiver launch-record state.
  metrics: >
    Count logical dispatches, delivery retries, launch intents, published acceptances, and
    uncertain launch windows.
  traces: >
    Join precondition snapshot to prepared export, receiver acceptance, pre-spawn intent,
    invocation identity, and RUNNING acknowledgement.
  error_taxonomy: >
    Distinguish active-dispatch conflict, unpublished preparation, stale acceptance, launch
    uncertain, and acknowledgement pending.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Preparation stores and publishes the full dispatch contract before invocation, with
      at most one active logical dispatch per unit and station. Set: Real store clients racing
      dispatch preparation over unit, station, attempt, read set, contract digest, idempotency
      key, generations, and reservation. Completeness: Compare persisted fields to the R31 schema,
      race two proposals, and reject the bare remote export in turn. A separate receiver process
      must see no delivery before acknowledgement, and the unit stays DISPATCHING without a second
      active logical dispatch. Falsifier: Invoke the receiver before the preparation export is
      acknowledged while the remote rejects it; dispatch/unpublished-launch must detect the
      forbidden call.
    falsified_by: >
      Invoke the receiver before the preparation export is acknowledged while the remote rejects
      it; dispatch/unpublished-launch must detect the forbidden call.
  - id: AC2
    text: >
      Claim: The receiver durably accepts the original dispatch identity and records launch intent
      before spawning; repeated delivery queries that record rather than starting another engine.
      Set: Real receiver and child processes across acceptance commit, intent commit, process
      creation, and conclusive launch-record windows. Completeness: SIGKILL the receiver at every
      boundary and deliver the same dispatch from two clients after restart. Observe child
      identities and launch records; an intent without conclusive evidence remains stopped for W23
      reconciliation, never blindly relaunched. Falsifier: Treat a pre-spawn intent as safe to
      relaunch after killing the receiver just after child creation; dispatch/ambiguous-spawn must
      catch the second child.
    falsified_by: >
      Treat a pre-spawn intent as safe to relaunch after killing the receiver just after child
      creation; dispatch/ambiguous-spawn must catch the second child.
  - id: AC3
    text: >
      Claim: RUNNING requires committed and published receiver acceptance, and acceptance rechecks
      current admission, claim, authority, read set, and reservation. Set: Acknowledgement
      ingestion and repeated delivery against real SQLite, a real Git replica, and a durable
      receiver with revoked or stale inputs. Completeness: Race each precondition change against
      acceptance, kill after receipt commit before export, and retry acknowledgement by original
      identity. Compare lifecycle and receiver counts; a new attempt requires a reconciled
      terminal predecessor and fresh applicable retry authorization. Falsifier: Advance to RUNNING
      on a local acceptance commit while its replica export fails; dispatch/running-before-replica
      must detect the premature transition.
    falsified_by: >
      Advance to RUNNING on a local acceptance commit while its replica export fails;
      dispatch/running-before-replica must detect the premature transition.
required_evidence: [unit, integration]
rollback: >
  Stop new delivery, preserve prepared dispatches and launch records, and use W23 evidence-driven
  reconciliation before any retry.
---

## Intent

Record and replicate dispatch preparation and acceptance so delivery retries cannot launch a second worker.

## Context

Package B, W24 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R23, R31-R33, R39, R57. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Containment and heartbeat implementation are W25 and W26; production engine output is D.

## Notes

D2 directly blocks external dispatch and acceptance-success semantics until Dmitry ratifies off-host acknowledgement. D1 is inherited through storage and replication; D3 blocks production runner activation in W25. Launch records must be durable trusted receiver metadata, not a second coordination database or a model checkpoint. Temporary file write, fsync, and rename barriers need explicit crash coverage if used for receiver metadata.

