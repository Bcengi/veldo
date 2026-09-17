---
schema: veldo.spec/v1
id: VELDO-0067
title: Per-channel restricted edge signing and enrollment
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W52
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0066]
placement: [engine, tracker, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/control_signer*.py"
  - ".veldo/control_signer*.py"
  - "packs/*/.veldo/control_signer*.py"
  - "engine/.veldo/control_keys*.py"
  - ".veldo/control_keys*.py"
  - "packs/*/.veldo/control_keys*.py"
  - "engine/.veldo/control_channel_enrollment*.py"
  - ".veldo/control_channel_enrollment*.py"
  - "packs/*/.veldo/control_channel_enrollment*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0067_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0067-restricted-channel-edges.md"
  - "specs/index.md"
  - "proof/VELDO-0067/*"
behavior_bearing: true
observability:
  logs: >
    Edge enrollment and signing records name channel/service/key identities, delegated principal,
    allowed assertion kinds, scope, expiry, and rejected purpose.
  metrics: >
    Count active, retired and revoked edge keys, denied cross-channel assertions, arbitrary
    signing requests, and channels blocked from activation.
  traces: >
    Join the signed complete enrollment command and proof of key possession to delegation
    versions, canonical source evidence, presentation receipt, and protected signing decision.
  error_taxonomy: >
    Distinguish enrollment-key substitution, missing possession, revoked edge, purpose escalation,
    cross-channel impersonation, expired delegation, and unsafe signing custody.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each enrolled decision channel has its own restricted edge key and versioned
      enrollment bound to explicit authority and possession proof. Set:
      authorization.is_authorized and B protected key/signer APIs consumed by proposed
      control_channel_enrollment, for Telegram chat, Jira, signed CLI, and email when enrolled.
      Completeness: Derive required enrollment fields from A and compare all configured channel
      records. Execute real signed enrollment/rotation commands using protected Ed25519 keys;
      mutate the public key under an unchanged command envelope and race duplicate key/channel
      grants. Verify command-digest recomputation, active membership/delegation versions and
      possession before persistence, with no agent or service self-grant. Falsifier: Omit
      enrollment public key from executed-command digest verification;
      edges/enrollment-key-substitution must detect a substituted active edge key.
    falsified_by: >
      Omit enrollment public key from executed-command digest verification;
      edges/enrollment-key-substitution must detect a substituted active edge key.
  - id: AC2
    text: >
      Claim: The protected signer independently enforces channel, principal, assertion purpose,
      request and presentation versions, scope and expiry before issuing an assertion. Set: B
      control_signer interface, authorization._attestation_ok/is_authorized, and
      request_reconcile._build_attestation through every enrolled edge. Completeness: Enumerate
      R38/A delegation dimensions and exercise each through a separate real edge process. Attempt
      arbitrary-byte and membership-command signing, another channel identity, changed principal,
      altered ruling/evidence, stale presentation, missing canonical attribution and expired
      scope. Require named refusals and no signature; CLI assertions also retain their verified
      personal source signature. Falsifier: Allow a Telegram edge key to sign a Jira assertion by
      changing the channel parameter; edges/cross-channel-purpose must detect the issued forbidden
      signature.
    falsified_by: >
      Allow a Telegram edge key to sign a Jira assertion by changing the channel parameter;
      edges/cross-channel-purpose must detect the issued forbidden signature.
  - id: AC3
    text: >
      Claim: Revoked or unsafe edges cannot accept fresh answers, while historical signatures
      remain verifiable and another qualified channel can use the same request. Set:
      request_reconcile.reconcile_requests, authorization.is_authorized and B key lifecycle
      acceptance guards across channel rotation, retirement, revocation, custody failure and
      restart. Completeness: Race edge/membership/delegation revocation against signing and
      settlement, kill after revocation commit before notification, and retry from the old edge.
      Query durable ordering and verify no fresh acceptance after revocation; retain old public
      keys for historical evidence. Attempt real sandbox/tool reads of private key material and
      disable the affected channel on custody failure. Exercise a current presentation on an
      independently enrolled channel without creating a second request. Falsifier: Reload a
      retired edge key as active after authority restart; edges/revoked-restart must catch a newly
      signed or accepted assertion.
    falsified_by: >
      Reload a retired edge key as active after authority restart; edges/revoked-restart must
      catch a newly signed or accepted assertion.
required_evidence: [unit, integration]
rollback: >
  Revoke the affected edge delegation, stop its assertions, preserve historical public keys and
  receipts, and re-enroll only with current authority and possession proof.
---

## Intent

Constrain every channel edge to attributable decision assertions under its own explicit enrollment.

## Context

Package E, W52 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R36-R39, R60, and R72 make edge signing a delegated authority boundary. A shared or unrestricted key could manufacture assertions or change membership. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

No actual production channel is enrolled by this draft, and no membership quorum or policy exemption is introduced.

## Notes

D1/D2 block durable enrollment and published assertions, with D3/D4 inherited through C. This item consumes B signing custody and command verification rather than reimplementing cryptography. Channel enrollment is distinct from activation: even a valid restricted key cannot enable ingress before W58 sandbox proof and a separately recorded authorized act. Public keys are accepted authority projections, never worker-branch authority; private keys stay outside repositories and proof. Map narrow enrollment modules and establish engine copies for request_reconcile before ready, registering all assets through W30. Effective policy amendments belong to A/W58, not an unrecorded edit here. Preserve signed attack inputs and each negative-control diff and failed row.
