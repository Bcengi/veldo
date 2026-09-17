---
schema: veldo.spec/v1
id: VELDO-0097
title: Operational recovery under scope change, revocation, and lost effect acknowledgement
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W82
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095, VELDO-0096]
placement: [distribution, contracts, fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "engine/.veldo/version.py"
  - ".veldo/version.py"
  - "packs/*/.veldo/version.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_recovery_journey*.py"
  - ".veldo/control_recovery_journey*.py"
  - "packs/*/.veldo/control_recovery_journey*.py"
  - "engine/.veldo/control_restore*.py"
  - ".veldo/control_restore*.py"
  - "packs/*/.veldo/control_restore*.py"
  - "engine/.veldo/control_integrity*.py"
  - ".veldo/control_integrity*.py"
  - "packs/*/.veldo/control_integrity*.py"
  - "engine/.veldo/control_effect*.py"
  - ".veldo/control_effect*.py"
  - "packs/*/.veldo/control_effect*.py"
  - "scripts/check_install_and_run.py"
  - "scripts/suites/*_veldo_0097_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0097-operational-recovery-scope-revocation-lost-ack.md"
  - "specs/index.md"
  - "proof/VELDO-0097/*"
behavior_bearing: true
observability:
  logs: >
    Recovery records identify installed profile, scope/revocation sequence, dispatch/effect
    identity, fault barrier, trusted observations and recovery finding.
  metrics: >
    Report restored acknowledged commands, repeated effects, unsupported completion attempts,
    preserved corruption and unreconciled exposure.
  traces: >
    Join running work through lost effect acknowledgment and conflicting observations to verified
    replica recovery or a named authority stop.
  error_taxonomy: >
    Distinguish not dispatched, running, effect committed, acknowledgment lost, outcome unknown,
    journal corruption and incompatible restoration.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The decisive combined journey never repeats an effect or asserts unsupported
      completion after scope change or revocation. Set: Installed control_recovery_journey driving
      F invalidation/E settlement, frontier.claimable and B effect recovery for each qualified
      effect adapter. Completeness: Register RJ10; enumerate adapters and actual effect/ack
      barriers from installed instrumentation. While real work runs, change accepted scope or
      revoke authority, then crash after an external effect before its acknowledgment. Restart
      with conflicting checkpoint, local status, receiver and remote observations. For both
      scope/revocation variants require trusted target reconciliation, original dispatch identity,
      removed publication permission, no repeated effect and no completion from status/exit/nonce
      alone; unresolved cases remain AWAITING_AUTHORITY. Falsifier: Redispatch after checkpoint
      loss despite target evidence of the original effect; recovery/combined-lost-ack must detect
      the second effect.
    falsified_by: >
      Redispatch after checkpoint loss despite target evidence of the original effect;
      recovery/combined-lost-ack must detect the second effect.
  - id: AC2
    text: >
      Claim: Simulated host loss preserves every acknowledged command and retains uncertainty
      where target evidence is inconclusive. Set: Installed control_restore and control_effect
      recovery across R32 five findings, measured with version.installed_version and
      pack.engine_drift. Completeness: Run actual authority/receiver/replica processes, record
      acknowledged command watermarks, then make the original host database/workspaces/checkpoints
      inaccessible. Restore on a separate disposable host boundary from only verified off-host
      material. Require operations-proven old-host isolation, credential revocation and removal of
      publication authority before replacement; network silence alone is insufficient. Require
      acknowledged-history inclusion, explicit uncertainty for unpublished tails, new generation
      fencing and target-specific outcome queries. Process absence, lease expiry and consumed
      nonce cannot establish nonexecution; retry/compensation needs its own current signed
      contract and no uncertainty erasure. Falsifier: Classify absent worker process as proof of
      nonexecution after host loss; recovery/unknown-is-not-unstarted must detect an unsupported
      automatic retry.
    falsified_by: >
      Classify absent worker process as proof of nonexecution after host loss;
      recovery/unknown-is-not-unstarted must detect an unsupported automatic retry.
  - id: AC3
    text: >
      Claim: Corruption is preserved and blocks dispatch; only verified history can rebuild
      derived state. Set: Installed control_integrity/control_restore paths for journal sequence,
      signatures, snapshot, derived tables and isolated checkpoint data. Completeness: Enumerate
      persisted artifacts from B/W79 inventories. Corrupt each kind, including valid-looking
      altered history and a missing middle journal record, then restart. Require no truncation or
      implicit downgrade, signed operations reconciliation against verified replica, and
      replay-derived tables only from intact history. Checkpoint-only quarantine requires
      affirmative domain integrity proof; unavailable execution runtime does not prevent stdlib
      verification. Falsifier: Truncate an unexplained bad journal tail and resume dispatch;
      recovery/preserve-corruption must detect lost history and unauthorized recovery.
    falsified_by: >
      Truncate an unexplained bad journal tail and resume dispatch; recovery/preserve-corruption
      must detect lost history and unauthorized recovery.
  - id: AC4
    text: >
      Claim: Running revocation and resource exhaustion retain effect fencing and accounting
      through recovery. Set: Installed D runner profiles and B reservation/supervision boundaries
      consumed by control_recovery_journey. Completeness: Derive engine/host and memory/descendant
      CPU/storage bytes/inodes matrices from D qualification. Revoke a principal or exhaust each
      hard limit during real work, interrupt acknowledgment/accounting and restart. Require
      independent stop, empty-containment proof before slot reuse, retained unknown provider
      exposure and authority/other-project survival. Every retry/follow-on request still reserves
      its enforceable maximum charge before reaching the provider. Falsifier: Release outstanding
      provider exposure when a revoked worker exits without usage; recovery/revoked-unknown-spend
      must detect reuse of unbounded exposure.
    falsified_by: >
      Release outstanding provider exposure when a revoked worker exits without usage;
      recovery/revoked-unknown-spend must detect reuse of unbounded exposure.
required_evidence: [unit, integration, journeys]
rollback: >
  Keep affected dispatches stopped, preserve corrupt bytes and outstanding effects, and restore
  only verified history under explicit current operations authority.
---

## Intent

Qualify installed recovery under combined authority changes, external uncertainty, host loss and corrupted state.

## Context

Package H, W82 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R27, R32/R33, R43/R45 as reviewed, R63 and R74 require observed recovery with explicit uncertainty. Repair that invents nonexecution or loses history is critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Automatic failover, arbitrary target retries and certification from model assertions or source-tree recovery are excluded.

## Notes

D1/D2 block the verified authority/off-host recovery proof, D3 independent containment and D4 replacement worker clones. Dmitry must enroll the operations/resuming authority and rule on any accepted-risk disposition; a fixture signature cannot decide a real unknown effect. Drive tests only in disposable installed environments and retain target effect counts from outside the killed authority. Map control_recovery_journey and confirm B effect-module paths before ready; inventory all fault assets through W30. RJ10 must execute its combined sequence, not substitute separate green scope and crash tests.
