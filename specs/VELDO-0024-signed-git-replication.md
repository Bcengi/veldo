---
schema: veldo.spec/v1
id: VELDO-0024
title: Signed Git replication and off-host acknowledgement
status: shipped
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W9
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_replica*.py"
  - ".veldo/control_replica*.py"
  - "packs/*/.veldo/control_replica*.py"
  - "engine/.veldo/runstatus.py"
  - ".veldo/runstatus.py"
  - "packs/*/.veldo/runstatus.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_store*.py"
  - ".veldo/control_store*.py"
  - "scripts/suites/36_veldo_0023_journal.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/architecture.yaml"
  - "scripts/suites/*_veldo_0024_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0024-signed-git-replication.md"
  - "specs/index.md"
  - "proof/VELDO-0024/*"
behavior_bearing: true
observability:
  logs: >
    Publication diagnostics name export digest, protected ref, local sequence, acknowledged
    sequence, and pending command identity.
  metrics: >
    Expose last durable sequence, local committed sequence, pending count, oldest pending age, and
    PAUSED_PUBLICATION.
  traces: >
    Bind SQLite command result to export tree, Git commit, remote ref observation, and
    acknowledgment receipt.
  error_taxonomy: >
    Distinguish pending publication, remote refusal, export divergence, lost acknowledgment,
    invalid signature, and unqualified durability contract.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Signed immutable exports containing journal records and newly referenced artifacts
      publish in sequence to a dedicated protected Git ref before success, external dispatch, or
      dependent publication. Set: All command result and effect-release paths, driven by real
      SQLite, signing processes, and Git against a disposable bare remote. Completeness: Enumerate
      release paths from the command/effect registry; fail the receive hook or disconnect Git for
      each sequence and assert pending results and zero receiver calls until exact export
      acknowledgment. Observe ref ordering and artifact completeness across restart. Falsifier:
      Return success after SQLite commit while the remote receive hook rejects publication;
      replica/pending-success must fail.
    falsified_by: >
      Return success after SQLite commit while the remote receive hook rejects publication;
      replica/pending-success must fail.
  - id: AC2
    text: >
      Claim: A lost acknowledgment retries or reconciles the same export identity without
      generating another command or divergent replica history. Set: Export preparation, remote ref
      update, acknowledgment storage, and client reply crash windows. Completeness: SIGKILL the
      publisher at each barrier, including after the bare remote ref changes, then restart and
      query exact remote ref and export digest; compare command and export counts and the durable
      watermark. A mismatching remote export must stop. Falsifier: Allocate a fresh export
      identity after a kill following remote ref update; replica/lost-ack-identity must detect the
      second export.
    falsified_by: >
      Allocate a fresh export identity after a kill following remote ref update;
      replica/lost-ack-identity must detect the second export.
  - id: AC3
    text: >
      Claim: Unavailable or unqualified replication stays visibly pending and cannot be
      misreported as rejection or off-host durability. Set: Real status CLI reads of empty,
      caught-up, pending, oldest-pending, and divergent store states plus installation
      remote-contract checks. Completeness: Build states through actual commands and Git failures;
      compare displayed watermarks and ages to stored records. Kill before acknowledgment
      persistence and read status after restart. Require operations evidence of remote durability
      and protected-ref access before activation; a local bare remote qualifies protocol only.
      Falsifier: Render a committed pending command as rejected after publisher death;
      replica/status-pending must preserve its original command identity and pending status.
    falsified_by: >
      Render a committed pending command as rejected after publisher death; replica/status-pending
      must preserve its original command identity and pending status.
required_evidence: [unit, integration]
rollback: >
  Pause mutation acknowledgments and dependent effects; retain pending exports and resume with a
  compatible publisher using their original identities.
---

## Intent

Withhold success and dependent effects until each committed command has a verifiable durable replica acknowledgment.

## Context

Package B, W9 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R23, R26-R27, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Premature success could acknowledge history that cannot survive authority-host loss. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Source landing, live remote provisioning, and host restoration are separate concerns.

## Notes

D1 and D2 directly block implementation and activation of this publication contract until Dmitry rules. Protocol proof uses only throwaway Git remotes; it cannot claim survival of authority-host loss. The exporter owns the audit ref, while source publication remains the lander responsibility. Include referenced artifact bytes in recovery exports, not only locations in the authority clone.

