---
schema: veldo.spec/v1
id: VELDO-0067
title: Per-channel restricted edge signing and enrollment
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W52
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0027, VELDO-0066]
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
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One restricted Telegram edge key is explicitly enrolled under current authority. Set
      and completeness: Compare actual enrollment fields and possession proof with the channel
      schema; submit real signed enrollment and altered public-key/authority parameters, and reject
      self-grant or absent current membership. Falsifier: Exclude the public key from the enrollment
      command digest; substituted-key acceptance must fail the check.
    falsified_by: >
      Exclude the public key from the enrollment command digest; substituted-key acceptance must
      fail the check.
  - id: AC2
    text: >
      Claim: The protected signer enforces purpose, channel, actor, request, presentation, scope and
      expiry. Set and completeness: For the Telegram edge mutate each delegation dimension
      independently through the actual signer and try arbitrary-byte or membership-command signing;
      require no signature for a forbidden request or missing canonical evidence. Falsifier: Permit
      the edge to sign a membership command; the purpose-refusal check must fail.
    falsified_by: >
      Permit the edge to sign a membership command; the purpose-refusal check must fail.
  - id: AC3
    text: >
      Claim: Current edge and actor authorization is required at answer acceptance. Set and
      completeness: Accept one valid current Telegram assertion, then use a retired edge or revoked
      actor and attempt a real private-key read from a worker tool; observe acceptance refusal and
      protected key custody. Falsifier: Accept an answer with a retired edge key; the current-
      authorization check must fail.
    falsified_by: >
      Accept an answer with a retired edge key; the current-authorization check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Per-channel restricted edge signing and enrollment. Deliver the normal function needed by the running factory journey.

## Context

W52 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: a current member enrolls one restricted Telegram edge key with a signed enrollment
  command whose digest binds the public key and the authority parameters, plus proof that the edge
  holds the private key. The edge then signs only answer assertions, through the protected signer, for
  its own purpose, channel, actor, request, presentation, scope and expiry, and only with the canonical
  evidence VELDO-0066 produces. When an answer is accepted, both the edge and the actor must still be
  current. The private edge key never reaches a worker or a proof bundle.
- Threat model: a substituted public key or altered authority parameters in an enrollment; a
  self-grant, or an enrollment by someone who is not a current member; the edge asked to sign outside
  its purpose (a membership command, arbitrary bytes) or for another channel, actor, request,
  presentation or scope, or after expiry; an answer signed by a retired edge or for a revoked actor;
  and a worker process trying to read the private edge key. The owner's account outside workers, the
  protected signing and membership services, and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); key
  rotation, restart and failover (Release 2); more than one channel (Release 4); Jira enrollment
  (dropped by the owner); activating ingress (VELDO-0073); forged rows in our own store and files
  planted in the installed directory.

## Notes

Use protected signing and membership services already present. Enrollment does not activate
ingress; 0073 requires separate actual Telegram proof and authorized activation. Keep private
edge keys outside worker access and proof. API sessions later use their own authenticated
actor path.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
rotation/restart/failover moved to Release 2; AC1/AC2 plural-channel coverage moved to Release
4. Jira-specific enrollment is dropped. Restricted Telegram edge and current authorization
remain. The criteria, declared evidence universe, Context and Notes above now carry only the
retained function. No specification status or historical proof was changed.
