---
schema: veldo.spec/v1
id: VELDO-0027
title: Protected signing and key lifecycle
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W12
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
placement: [engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_signer*.py"
  - ".veldo/control_signer*.py"
  - "packs/*/.veldo/control_signer*.py"
  - "engine/.veldo/control_keys*.py"
  - ".veldo/control_keys*.py"
  - "packs/*/.veldo/control_keys*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/keys/allowed_signers"
  - "engine/.veldo/keys/allowed_signers"
  - "packs/*/.veldo/keys/allowed_signers"
  - "scripts/suites/*_veldo_0027_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0027-protected-signing.md"
  - "specs/index.md"
  - "proof/VELDO-0027/*"
behavior_bearing: true
observability:
  logs: >
    Signer diagnostics record key ID, purpose, principal, delegation revision, and refusal without
    private material.
  metrics: >
    Count purpose and channel mismatches, revoked signing attempts, custody violations, and
    retained historical verification keys.
  traces: >
    Bind receipt bytes to observed subject, signing purpose, accepted key transition, and
    effective signing time.
  error_taxonomy: >
    Distinguish unknown purpose, forbidden arbitrary signing, revoked key, stale delegation,
    missing attribution, and inaccessible protected custody.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A protected signer independently validates purpose and delegation and never exposes
      private keys to repository, sandbox, build, transcript, or model processes. Set: Evidence
      and per-channel signing purposes, using real Ed25519 keys outside a disposable repository
      and an OS-separated signer process. Completeness: Drive each registered purpose through its
      authenticated IPC path; a real worker process attempts key reads, arbitrary-byte signing,
      cross-channel signing, and membership-command signing with an edge key. Inspect output and
      artifact bytes for fixture key leakage and require exact purpose refusals. Falsifier: Remove
      the channel-purpose restriction and ask one edge key to sign another channel assertion;
      signing/cross-channel must fail.
    falsified_by: >
      Remove the channel-purpose restriction and ask one edge key to sign another channel
      assertion; signing/cross-channel must fail.
  - id: AC2
    text: >
      Claim: Rotation, retirement, and revocation are durable accepted transitions; retained keys
      verify historical receipts without authorizing fresh commands. Set: Accepted key lifecycle
      states and verification paths, including .veldo/keys/allowed_signers and a conflicting
      worker-branch copy. Completeness: Sign real receipts before and after each transition, race
      rotation and signing processes, and SIGKILL after transition commit. On restart, compare
      effective, retirement, and revocation times and reject branch-added keys and revoked fresh
      signatures while verifying legitimate history. Falsifier: Load a worker branch added key as
      active authority after restart; signing/branch-key must refuse its fresh administrative
      command.
    falsified_by: >
      Load a worker branch added key as active authority after restart; signing/branch-key must
      refuse its fresh administrative command.
  - id: AC3
    text: >
      Claim: Evidence signatures attest captured observations with contract and actor provenance
      and preserve agent statements as assertions; edge signatures retain source evidence and
      presentation binding. Set: Real child exit, output bytes, and tool invocation receipts plus
      stored restricted-edge requests with the VELDO-0020 assertion fields. Completeness: Capture
      a real subprocess observation and verify its signature in another process. Corrupt each
      bound digest or actor field and remove chat platform message ID, sender ID, timestamp, or
      CLI personal signature in turn; a signer must refuse incomplete edge inputs and never
      relabel assertions as observations. Falsifier: Accept an edge request containing only chat
      text after removing canonical message identity; signing/text-only must refuse to issue a
      signature.
    falsified_by: >
      Accept an edge request containing only chat text after removing canonical message identity;
      signing/text-only must refuse to issue a signature.
required_evidence: [unit, integration]
rollback: >
  Disable new signatures under the affected purpose, retain historical public keys and signed
  receipts, and rotate through accepted transitions before reactivation.
---

## Intent

Keep signing authority outside workers and make key transitions verifiable without allowing branch-local keys to grant authority.

## Context

Package B, W12 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R15, R36-R38, R50, R57. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

No production private keys or live channel credentials are created, and channel enrollment remains E.

## Notes

D1 is inherited through the accepted membership store. The signer core and real custody boundary ship here; E qualifies live channel evidence acquisition and per-channel activation. Fixture attribution cannot certify a platform. Public allowed_signers is a projection of accepted key transitions, never independent worker-controlled authority. The keys glob names public verification artifacts only.

