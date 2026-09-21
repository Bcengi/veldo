---
schema: veldo.spec/v1
id: VELDO-0027
title: Protected signing and key lifecycle
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W12
plan_revision: 2
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
placement: [engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_signer.py"
  - ".veldo/control_signer.py"
  - "engine/.veldo/control_keys.py"
  - ".veldo/control_keys.py"
  - "engine/.veldo/architecture.yaml"
  - ".veldo/architecture.yaml"
  - ".veldo/keys/allowed_signers"
  - "engine/.veldo/keys/allowed_signers"
  - "scripts/suites/*_veldo_0027_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0027-protected-signing.md"
  - "specs/index.md"
  - "proof/VELDO-0027/*"
behavior_bearing: true
observability:
  logs: >
    Signer diagnostics record the key id, the assertion kind, the principal, the delegation
    revision and the refusal, and never any private material.
  metrics: >
    Count assertion-kind and channel mismatches, revoked signing attempts, and retained historical
    verification keys.
  traces: >
    Bind receipt bytes to the observed subject, the assertion kind, the accepted key transition and
    the effective signing time.
  error_taxonomy: >
    Distinguish an unknown assertion kind, forbidden arbitrary signing, a revoked key, a stale
    delegation, missing attribution, a key named by path rather than by channel, and a channel whose
    key is not the one that signed.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The signer independently validates the assertion kind and the delegation, holds no
      resident process, and never puts private key bytes into its output or its artifacts: every
      signature is produced by a short-lived child that exits with the call. Set: Evidence and
      per-channel assertion kinds, using real Ed25519 keys held outside a disposable repository.
      Completeness: Drive each of the four registered assertion kinds; a real worker process
      attempts arbitrary-byte signing, cross-channel signing, and membership-command signing with
      an edge key. Inspect the output and the artifact bytes for fixture key material and require
      the exact refusal for each. Count the signer processes alive before and after a signature and
      require the counts equal, and require no socket, no pid file and no listener anywhere in the
      run. Falsifier: Remove the channel restriction and ask one edge key to sign another channel's
      assertion; signing/cross-channel must fail.
    falsified_by: >
      Remove the channel restriction and ask one edge key to sign another channel's assertion;
      signing/cross-channel must fail.
  - id: AC2
    text: >
      Claim: Rotation, retirement and revocation are durable accepted transitions; retained keys
      verify historical receipts without authorizing fresh commands. Set: Accepted key lifecycle
      states and verification paths, including .veldo/keys/allowed_signers and a conflicting
      worker-branch copy. Completeness: Sign real receipts before and after each transition, race
      rotation and signing processes, and SIGKILL after the transition commits. On restart, compare
      effective, retirement and revocation times and reject branch-added keys and revoked fresh
      signatures while verifying legitimate history. Falsifier: Load a worker-branch added key as
      active authority after restart; signing/branch-key must refuse its fresh administrative
      command.
    falsified_by: >
      Load a worker-branch added key as active authority after restart; signing/branch-key must
      refuse its fresh administrative command.
  - id: AC3
    text: >
      Claim: Evidence signatures attest captured observations with contract and actor provenance
      and preserve agent statements as assertions; edge signatures retain source evidence and
      presentation binding. Set: Real child exit, output bytes and tool invocation receipts, plus
      stored restricted-edge requests carrying the VELDO-0020 assertion fields. Completeness:
      Capture a real subprocess observation and verify its signature in another process. Corrupt
      each bound digest or actor field and remove the chat platform message id, the sender id, the
      timestamp or the CLI personal signature in turn; the signer must refuse incomplete edge
      inputs and never relabel an assertion as an observation. Falsifier: Accept an edge request
      containing only chat text after removing the canonical message identity; signing/text-only
      must refuse to issue a signature.
    falsified_by: >
      Accept an edge request containing only chat text after removing the canonical message
      identity; signing/text-only must refuse to issue a signature.
  - id: AC4
    text: >
      Claim: The key is chosen by the SIGNER from the authority's own key file, keyed by channel,
      and never by anything the caller writes. A request naming a key path is refused; a request
      naming a channel is signed only with that channel's registered key, so an edge cannot sign as
      another channel even when it says it is one. Set: The real allowed_signers projection, two
      enrolled channels with different keys, and requests naming a channel, naming a path, and
      naming one channel while carrying the other's key id. Completeness: The second channel's key
      really exists and really verifies its own assertions, so the row fails if the answer is right
      only because the alternative was absent; and the refusal for a path is distinguishable by name
      from the refusal for a channel mismatch. Falsifier: Take the signing key from the key id in
      the request; signing/key-comes-from-the-channel must fail.
    falsified_by: >
      Take the signing key from the key id in the request;
      signing/key-comes-from-the-channel must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new signatures for the affected assertion kind, retain historical public keys and signed
  receipts, and rotate through accepted transitions before reactivation.
---

## Intent

Keep signing authority outside workers and make key transitions verifiable, without letting a branch-local key or a caller's own claim grant authority.

## Context

Package B, W12 of PLAN-0019 revision 2. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R15, R36-R38, R50, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Unrestricted signing or a branch-added key could fabricate authority and trusted observations. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with a byte-identical repository copy. `scripts/publish.py` composes every pack from `engine/` at publication, so the footprint names two copies and not nine: seven copies in git would be seven things to drift.

**Two modules, both in the engine area.** `.veldo/control_signer.py` decides whether this principal, under this delegation, may sign this assertion kind for this channel, plus the canonical envelope and its verification. `.veldo/control_keys.py` holds the lifecycle: accepted rotation, retirement and revocation transitions, the `allowed_signers` projection, and verification of historical receipts by retired keys. They are safety-core decision organs in the same sense as `.veldo/authorization.py` and `.veldo/control_membership*.py`, which is where the engine area already puts that work, so this item adds both globs to that area's includes. That is the amendment precedent this contract already set for VELDO-0011, VELDO-0023 and VELDO-0025: one entry inside an ordinary item, contract version unchanged.

**The signer is a short-lived child, not a resident process.** Dmitry decided this on 2026-09-21 over Telegram (message 28437, answering the ask 28435), choosing it over a signer daemon under its own account with an authenticated socket. A resident process earns its keep only across several machines and several authorities, which is not where this is. It also leaves the `no_detached_processes` invariant standing as written: that rule has one scoped exception, for the project runner, and a daemon would have needed a second.

**The key comes from the key file, never from the request.** This is the answer to the impersonation question, and the repository already answers it the same way elsewhere: `authority_contract.verify_signed_command` does not use any key the caller names. It looks the key up from the keyring the authority holds, keyed by principal, and verifies against that. Applied to channels, a Telegram edge cannot sign as Jira because it does not hold Jira's private key, and nothing in the path trusts the caller's claim about which channel it is. The `edge_key_id` a request carries becomes a cross-check against the channel's registered id, never the source of the key. AC4 is that property.

**The key file has to be a protected path, and arming that is the owner's act.** The `allowed_signers` projection lives in the repository the calling account can write, so without protection an edge could add its own key as another channel's and the lookup above would faithfully find it. The repository already has exactly this mechanism, and it is what guards `.veldo/policy.yaml`: a protected path, where a change needs a commit-bound, path-scoped approval from the owner. Adding `.veldo/keys/allowed_signers` to `protected_paths` at the `high` floor is therefore part of landing this item, and it is an owner act with its own approval, in the same shape as the fix-validation flag was: this specification states the requirement and does not perform it.

Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files and Git operations are real.

## Out of scope

No production private keys or live channel credentials are created, and channel enrollment remains E.

**The operating-system custody boundary is not here, and that is a decision rather than an omission.** An earlier version of this specification claimed the private key is unreadable by the repository account and the signer is reached only through one fixed command. Dmitry ruled on 2026-09-21 (Telegram 28578 and 28580, answering the ask in 28577) that the claim comes out and installation is its own item. Two reasons, and the second is the stronger one. It is consistent with the standing ruling that this boundary stays simple, with no second operating-system account. And nothing this item ships could produce the property: the footprint is two Python modules, a public key projection, an architecture entry and the suites. There is no installer, no account and nothing that sets a file mode, so a builder handed this footprint could only assert facts about a fixture it created itself, and the old falsifier proved it by mutating that fixture rather than the implementation. Service installation belongs to W32.

What survives of that claim is the half this item can actually hold, and it is in AC1 and AC4: the signer never puts private key bytes into its output or its artifacts, and it refuses a request that names a key by path instead of by channel.

## What the adversarial read found, and how each one was settled

This specification was moved to ready and approved on 2026-09-21, and an independent review then found three things that made it unbuildable as written. It went back to draft the same day, before any build started. All three are now answered, and they are kept here rather than deleted because the next reader should see what the item used to claim.

**"Purpose" was not a word the accepted contract has.** AC1 drove "each registered purpose", AC4 refused a request naming a path "instead of a purpose", and the metrics and the taxonomy both counted purpose mismatches. The word appeared nowhere in the design document, nowhere in VELDO-0020, and nowhere in `.veldo/authority_contract.py`, whose dimensions are channel, assertion kind and authority scope. Settled by reading the contract: `ASSERTION_KINDS` is a closed set of four, `decision_answer`, `assignment_acceptance`, `review_disposition` and `acknowledgement`, and every use of "purpose" meant one of those. The specification now uses the contract's word, so "each registered assertion kind" is something a builder can enumerate.

**AC4 claimed a deployment property its own footprint could not produce.** Settled by the owner's ruling above: the claim is out and installation is W32.

**The light design left the caller composing the whole request.** With no resident process the caller writes the principal, the channel, the delegation and the attribution, and R38 requires the signer to check those independently and forbids an edge impersonating another channel. Settled by the two paragraphs in Context: the key is resolved by channel from the authority's key file rather than from anything the request carries, following the pattern `verify_signed_command` already uses for principals, and the key file becomes a protected path so the lookup cannot be poisoned by the account being gated.

## Notes

D1 is inherited through the accepted membership store. The signer core ships here; E qualifies live channel evidence acquisition and per-channel activation. Fixture attribution cannot certify a platform. Public `allowed_signers` is a projection of accepted key transitions, never independent worker-controlled authority. The keys glob names public verification artifacts only.
