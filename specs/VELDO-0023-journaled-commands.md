---
schema: veldo.spec/v1
id: VELDO-0023
title: Atomic journaled commands and deterministic replay
status: shipped
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W8
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_store*.py"
  - ".veldo/control_store*.py"
  - "packs/*/.veldo/control_store*.py"
  - "engine/.veldo/control_replay*.py"
  - ".veldo/control_replay*.py"
  - "packs/*/.veldo/control_replay*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/architecture.yaml"
  - "scripts/suites/*_veldo_0023_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0023-journaled-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0023/*"
behavior_bearing: true
observability:
  logs: >
    Command records expose command digest, journal sequence, before and after versions, and local
    pending state.
  metrics: >
    Count committed commands, identical retries, content conflicts, replay discrepancies, and
    durability refusals.
  traces: >
    Join transaction barriers to the signed record, nonce and reservation rows, effect
    obligations, and replay digest.
  error_taxonomy: >
    Distinguish command-content conflict, stale version, foreign-key violation, unsupported
    filesystem, incomplete transaction, and invalid journal.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The store commits entity versions, signed journal, consumed nonces, reservation
      changes, and effect obligations atomically with foreign keys and full durability enabled.
      Set: Every registered mutating command executed by a real authority process against
      <git-common-dir>/veldo/control/control.sqlite3 on a qualified local filesystem.
      Completeness: Compare command registrations to the transaction test matrix; SIGKILL the
      writer before commit, during commit, and after commit before reply, then reopen SQLite and
      compare every affected table to either the complete old or complete new state. Unsupported
      network storage refuses opening for writes. Falsifier: Move journal insertion outside the
      domain transaction and SIGKILL after the entity commit; journal/atomic-kill must detect
      state without its journal record.
    falsified_by: >
      Move journal insertion outside the domain transaction and SIGKILL after the entity commit;
      journal/atomic-kill must detect state without its journal record.
  - id: AC2
    text: >
      Claim: Identical command retries return the original committed result, while different
      content under one command ID and competing expected versions refuse without extra effects.
      Set: Same-ID and same-entity races from separate client processes using the real store
      command API. Completeness: Drive both race orders for identical and altered payloads and
      equal and stale versions, restart between commit and retry, and compare row counts,
      versions, result digests, and effect obligations to a one-winner oracle. Falsifier: Disable
      the command-digest equality check and race changed payloads under one ID;
      journal/content-reuse must reject the altered retry.
    falsified_by: >
      Disable the command-digest equality check and race changed payloads under one ID;
      journal/content-reuse must reject the altered retry.
  - id: AC3
    text: >
      Claim: Replay reconstructs materialized domain state deterministically from verified
      versioned canonical records without execution-runtime imports. Set: Every journal transition
      kind, identity, schema encoding, before and after version, receipt reference, and artifact
      digest produced by the command registry. Completeness: Replay real signed history into an
      empty derived-state target with the execution environment removed; compare digests with live
      SQLite state. Corrupt each signed field and reorder, duplicate, or remove records in
      disposable copies; no invalid history may rebuild writable authority. Falsifier: Skip
      previous-record digest verification and re-sign one record with an incorrect predecessor
      digest while retaining sequence continuity; journal/replay-chain must refuse reconstruction.
    falsified_by: >
      Skip previous-record digest verification and re-sign one record with an incorrect
      predecessor digest while retaining sequence continuity; journal/replay-chain must refuse
      reconstruction.
required_evidence: [unit, integration]
rollback: >
  Stop command acceptance, preserve the database and journal, and retain a compatible reader;
  never roll back by deleting committed commands.
---

## Intent

Make a domain command one durable, replayable transition even when the authority dies during commit.

## Context

Package B, W8 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R21-R22, R53, R57, R70. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Partial command commits or incorrect replay could lose accepted authority history or repeat privileged effects. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Replication transport is W9; operational restoration is W33. This item neither enables a service nor implements project workflows.

## Notes

D1 directly blocks effective storage implementation until Dmitry ratifies SQLite authority and its signed Git replica. D2 governs the later success boundary in W9; a local commit here is explicitly pending, never externally acknowledged success. New control_store and control_replay modules are proposed paths under the contracts and fleet areas; Package A must register their architecture mapping before ready. Exercise real SQLite and OpenSSH signing, not an in-memory transition dictionary.

