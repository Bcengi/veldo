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
  - "engine/.veldo/control_signer.py"
  - ".veldo/control_signer.py"
  - "packs/*/.veldo/control_signer.py"
  - "engine/.veldo/control_keys.py"
  - ".veldo/control_keys.py"
  - "packs/*/.veldo/control_keys.py"
  - "engine/.veldo/architecture.yaml"
  - ".veldo/architecture.yaml"
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
      private keys to repository, sandbox, build, transcript, or model processes, and it holds no
      resident process: every signature is produced by a short-lived child that exits with the
      call. Set: Evidence and per-channel signing purposes, using real Ed25519 keys held outside a
      disposable repository, readable only by the signing account, invoked through one fixed
      command. Completeness: Drive each registered purpose through that command; a real worker
      process attempts key reads, arbitrary-byte signing, cross-channel signing, and
      membership-command signing with an edge key. Inspect output and artifact bytes for fixture
      key leakage and require exact purpose refusals. Count the signer processes alive before and
      after a signature and require the counts to be equal, and require no socket, no pid file and
      no listener to be created anywhere in the run. Falsifier: Remove the channel-purpose
      restriction and ask one edge key to sign another channel assertion; signing/cross-channel
      must fail.
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
  - id: AC4
    text: >
      Claim: Custody is the operating-system account, not the caller's good behaviour: the private
      key is unreadable by the repository account, and the signer is reached only through the one
      fixed command, which refuses a request that names a key path instead of a purpose. Set: The
      repository account, the signing account, a real key file with its real mode and owner, and
      requests naming a purpose and naming a path. Completeness: Read the key directly as the
      repository account and require the read to fail on permissions; run the fixed command as the
      repository account and require a signature for a registered purpose; ask the same command
      for an arbitrary path and require refusal. Do all three against the real filesystem, never a
      mock. Falsifier: Make the key world-readable; signing/custody-mode must fail.
    falsified_by: >
      Make the key world-readable; signing/custody-mode must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new signatures under the affected purpose, retain historical public keys and signed
  receipts, and rotate through accepted transitions before reactivation.
---

## Intent

Keep signing authority outside workers and make key transitions verifiable without allowing branch-local keys to grant authority.

## Context

Package B, W12 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R15, R36-R38, R50, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Unrestricted signing or compromised key custody could fabricate authority and trusted observations. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies, and register each new asset in the distribution inventory and scaffolder as applicable.

**Two modules, both in the engine area.** `.veldo/control_signer.py` decides: whether this principal, under this delegation, may sign this purpose for this channel, plus the canonical envelope and its verification. `.veldo/control_keys.py` holds the lifecycle: accepted rotation, retirement and revocation transitions, the `allowed_signers` projection, and verification of historical receipts by retired keys. They are safety-core decision organs in the same sense as `.veldo/authorization.py` and `.veldo/control_membership*.py`, which is where the engine area already puts that work, so this item adds both globs to that area's includes. That is the amendment precedent this contract already set for VELDO-0011, VELDO-0023 and VELDO-0025: one entry inside an ordinary item, contract version unchanged.

**The signer is a short-lived child, not a resident process.** Dmitry decided this on 2026-09-21 over Telegram (message 28437, answering the ask 28435), choosing it over a signer daemon under its own account with an authenticated socket. The custody requirement is that private keys never enter a repository, a sandbox, a model context, a transcript or a build, and an account boundary plus one fixed command buys exactly that; a resident process earns its keep only across several machines and several authorities, which is not where this is. It also leaves the `no_detached_processes` invariant standing as written: that rule has one scoped exception, for the project runner, and the daemon would have needed a second.

Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Back to draft, 2026-09-21: what an adversarial read found before the build

This spec was moved to ready and approved, and an independent review then found three things that
make it unbuildable as written. It is draft again and the build has not started. None of this is a
wording problem.

**"Purpose" is not a word the accepted contract has.** AC1 drives "each registered purpose", AC4
refuses a request naming a path "instead of a purpose", and the metrics and the taxonomy both count
purpose mismatches. The word appears nowhere in the design document, nowhere in VELDO-0020, and
nowhere in `.veldo/authority_contract.py`, whose actual dimensions are channel, assertion kind and
authority scope. Either purpose is another name for assertion kind, and this spec must say so, or it
is new contract vocabulary being introduced by an implementation item, which Package A forbids.
Nobody can enumerate "each registered purpose" until that is settled.

**AC4 claims a deployment property that its own footprint cannot produce.** It says the key is
unreadable by the repository account and the signer is reached only through one fixed command. The
footprint ships two Python modules, a public key file, the scaffolder and the suites. There is no
command, no installer, no account, nothing that sets a file mode. A builder handed this footprint
can only write a test that asserts facts about its own fixture. Its falsifier makes the key
world-readable, which mutates the fixture rather than the implementation, so deleting every line of
custody logic leaves the row green.

**The light design has a consequence this spec does not follow through.** With no resident process,
the caller composes the whole request: principal, channel, delegation, attribution. R38 requires that
the signer independently checks those and that an edge cannot impersonate another channel, but the
channel is decided by an `edge_key_id` the calling account writes. Where the child gets committed
membership, delegation and revocation versions from is not stated either, and the two possible
answers, from the caller or from a store the caller owns, are both weaker than the clause. This is a
design question about the option that was chosen, and it is the owner's to settle, not mine.

Until those three are answered the ready transition is premature whatever the validator says.

## Out of scope

No production private keys or live channel credentials are created, and channel enrollment remains E.

## Notes

D1 is inherited through the accepted membership store. The signer core and real custody boundary ship here; E qualifies live channel evidence acquisition and per-channel activation. Fixture attribution cannot certify a platform. Public allowed_signers is a projection of accepted key transitions, never independent worker-controlled authority. The keys glob names public verification artifacts only.

