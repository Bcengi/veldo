---
schema: veldo.spec/v1
id: VELDO-0043
title: Replaceable LangGraph execution adapter
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W28
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0035]
placement: [loop, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0043_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0043-replaceable-langgraph-adapter.md"
  - "specs/index.md"
  - "proof/VELDO-0043/*"
behavior_bearing: true
observability:
  logs: >
    Adapter records identify cycle, snapshot watermark, node operation identity, supplied
    committed result, and proposal or failure.
  metrics: >
    Count starts, advances, suspensions, cancellations, repeated nodes, quarantined checkpoints,
    and refused proposal commits.
  traces: >
    Join graph execution and deterministic replacement execution to identical authorized command
    IDs and journal transitions.
  error_taxonomy: >
    Distinguish stale snapshot, checkpoint ahead or behind, conflicting checkpoint, repeated
    operation, and unavailable execution runtime.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Start, advance, suspend, cancel, and proposal/failure operations exchange plain
      versioned data with the domain and produce equivalent transitions under a deterministic
      replacement. Set: Real LangGraph adapter and replacement processes consuming the same
      accepted snapshots and supplied results against control.sqlite3. Completeness: Enumerate
      public adapter operations from the interface and execute each path, including cancel during
      a real child wait. Compare committed domain transitions and proposal digests for identical
      authorized inputs; domain modules must import neither LangGraph nor worker engines.
      Falsifier: Let the LangGraph path allocate a different command identity on advance after
      suspension; graph/adapter-equivalence must detect divergent journal transitions.
    falsified_by: >
      Let the LangGraph path allocate a different command identity on advance after suspension;
      graph/adapter-equivalence must detect divergent journal transitions.
  - id: AC2
    text: >
      Claim: Replayed nodes reuse Veldo command IDs, and checkpoint loss or apparent progress
      cannot repeat effects or establish admission, priority, assignment, authorization, dispatch,
      or completion. Set: Real SQLite checkpoint records ahead of, behind, absent from, and
      conflicting with signed domain history. Completeness: Kill the graph process after command
      commit before checkpoint persistence, delete checkpoints, and restart. Compare real receiver
      invocation counts and domain facts to the original committed results; repeat with forged
      checkpoint progress and require replay or quarantine. Falsifier: Allocate a fresh command ID
      after deleting the post-commit checkpoint; graph/checkpoint-loss must catch the repeated
      receiver effect.
    falsified_by: >
      Allocate a fresh command ID after deleting the post-commit checkpoint; graph/checkpoint-loss
      must catch the repeated receiver effect.
  - id: AC3
    text: >
      Claim: The execution adapter can be removed while stdlib validators, authorization, journal
      replay, and recovery continue to operate on unchanged domain history. Set: Fresh enforcement
      and recovery processes with the isolated execution environment unavailable and actual signed
      SQLite history present. Completeness: Run each registered enforcement entry, validate a real
      signature, replay the journal, and apply a permitted recovery command after hiding the
      runtime. Compare domain state before and after checkpoint removal and require unavailable
      graph execution to refuse explicitly without blocking independent recovery. Falsifier:
      Import LangGraph from journal replay and remove the runtime environment;
      graph/stdlib-recovery must fail its real replay command.
    falsified_by: >
      Import LangGraph from journal replay and remove the runtime environment;
      graph/stdlib-recovery must fail its real replay command.
required_evidence: [unit, integration]
rollback: >
  Suspend graph execution, preserve accepted domain results and operation identities, quarantine
  checkpoint state, and select the tested replacement through versioned configuration.
---

## Intent

Run LangGraph as a replaceable adapter over Veldo snapshots and command identities without granting checkpoints domain authority.

## Context

Package B, W28 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R21, R29-R30, R34-R35, R53, R57, R62. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The high risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Project-manager graphs, live engine adapters, and checkpoint SQL isolation implementation belong to G, D, and W29.

## Notes

D1 is inherited from store and snapshot implementation. Use actual LangGraph execution with only model responses faked; a hand-written replacement alone cannot prove the adopted adapter. W29 supplies the restricted checkpoint boundary and W30 packages its qualified versions. No server or hosted control plane is introduced. Keep graph lifecycle distinct from project-manager policy and completion facts.

