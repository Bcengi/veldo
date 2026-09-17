---
schema: veldo.spec/v1
id: VELDO-0068
title: Atomic cross-channel settlement and principal-based quorum enforcement
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W53
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0065, VELDO-0066, VELDO-0067]
placement: [contracts, tracker, engine, distribution]
protected_paths: [.veldo/settlements/*]
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_request_settlement*.py"
  - ".veldo/control_request_settlement*.py"
  - "packs/*/.veldo/control_request_settlement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/settlements/*.json"
  - "scripts/suites/*_veldo_0068_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0068-atomic-cross-channel-settlement.md"
  - "specs/index.md"
  - "proof/VELDO-0068/*"
behavior_bearing: true
observability:
  logs: >
    Settlement records identify request/version, accepted assertion and presentation digests,
    canonical principal/channel, actual ruling/rationale, terminal state, and journal sequence.
  metrics: >
    Count one-winner conflicts, pending quorum, principal deduplications, rejected stale answers,
    partial-commit detections, and pending settlement exports.
  traces: >
    Join canonical answer evidence through authorization to the single transaction containing
    ruling, request state, nonce, domain effects, receipt, and outbound obligations.
  error_taxonomy: >
    Distinguish missing ruling, choice conflict, stale request, request-level role refusal,
    insufficient independent principals, terminal conflict, and publication pending.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The actual offered ruling and actor-authored reasoning survive canonical answer
      ingestion and become the settlement, rather than a generic accepted status. Set:
      request_reconcile._terminal_decision/_build_attestation/_settlement_record/_reconcile_one
      for every request.TOUCHPOINTS member on Telegram chat, Jira, signed CLI, and email when
      enrolled. Completeness: Derive touchpoint/ruling coverage from A schemas and offered
      choices. Submit distinct choices, rejection, elaboration and finding dispositions using
      authenticated source evidence, real signed assertions and authority commands. Compare source
      ruling/rationale to stored assertion, settlement and typed effect; reject absent,
      unsupported, or contradictory choices and never copy one request-level rationale onto
      several actors. Falsifier: Retain _settlement_record converting every accepted decision
      choice to decided without the chosen option; settlement/ruling-carried must detect loss of
      the actual ruling.
    falsified_by: >
      Retain _settlement_record converting every accepted decision choice to decided without the
      chosen option; settlement/ruling-carried must detect loss of the actual ruling.
  - id: AC2
    text: >
      Claim: One request version receives at most one terminal settlement, and all settlement
      components commit atomically through B authority. Set: SettlementStore.settle,
      FilesystemSettlementStore._has_receipt/_apply and the enrolled control_request_settlement
      replacement, with accepted assertions, ruling, terminal request state, consumed nonce,
      domain transitions, signed receipt, and delivery obligations. Completeness: Race separate
      real client processes within and across all enrolled channel pairs, including different
      changelog/message IDs, same-ID altered payloads, and opposite rulings. SIGKILL at each write
      and commit/reply boundary in real SQLite, reopen and replay the signed journal, and inspect
      every affected table. Require complete old or new state, one winner keyed by
      domain/request/version, and pending success until B off-host acknowledgment. Falsifier: Move
      receipt insertion outside the domain transaction and kill after ruling/state commit;
      settlement/atomic-crash must detect partial settlement on restart.
    falsified_by: >
      Move receipt insertion outside the domain transaction and kill after ruling/state commit;
      settlement/atomic-crash must detect partial settlement on restart.
  - id: AC3
    text: >
      Claim: Terminal request state and settlement reference are authoritative and materialize
      coherently so reconciliation cannot repeatedly reopen or reapply a completed request. Set:
      request_reconcile._is_open_status/_repo_records/reconcile_from_repo,
      FilesystemSettlementStore._apply, and request.validate_record/_check_settlement_path using
      accepted, rejected, and superseded requests. Completeness: Settle each terminal outcome
      through actual authority transactions; kill before and after B snapshot materialization,
      then read from another process/clone. Assert terminal status, exact receipt reference and
      version in one published snapshot, zero reopening from stale request YAML, and no second
      settlement after another external answer ID. Preserve historical records without fabricating
      new signatures. Falsifier: Leave the request status open after committing its settlement as
      the baseline _apply does; settlement/terminal-request-state must detect the stale inbox and
      renewed settlement attempt.
    falsified_by: >
      Leave the request status open after committing its settlement as the baseline _apply does;
      settlement/terminal-request-state must detect the stale inbox and renewed settlement
      attempt.
  - id: AC4
    text: >
      Claim: Policy and request requirements apply conjunctively, and assertions accumulate quorum
      by distinct authenticated principals rather than channels or files. Set:
      authorization.required_roles/quorum/_attestation_ok/_tally/_decide/is_authorized and
      request_reconcile._reconcile_one for every enrolled channel, actor kind, named-authority
      restriction, role, quorum, independence, expiry and impact predicate. Completeness:
      Enumerate effective predicate combinations from A; use real signatures and stored
      memberships to test stronger request roles/counts, insufficient or duplicate principals
      across channels, proposer-as-decider, revoked membership/edge, expired and stale
      presentations, and conflicting choices. Exercise both acceptance and rejection without the
      legacy rejection shortcut. Preserve PLAN-0016 owner-plus-independent-machine two-key
      consumption for applicable impacts; it cannot satisfy a quorum requiring two people.
      Falsifier: Ignore request.required_roles when policy roles are satisfied;
      settlement/stronger-request-role must detect unauthorized settlement.
    falsified_by: >
      Ignore request.required_roles when policy roles are satisfied;
      settlement/stronger-request-role must detect unauthorized settlement.
required_evidence: [unit, integration]
rollback: >
  Stop affected settlement acceptance, preserve assertions/nonces/history, and reconcile pending
  exports and projections through the original command identity.
---

## Intent

Settle a request exactly once with its actual ruling, attributable assertions, and complete durable consequences.

## Context

Package E, W53 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R22-R23, R37-R40, R60, and R72 govern settlement. The existing store checks only request/changelog pairs before sequential file writes; it neither carries an offered ruling nor updates the request status. Its rejection path also bypasses authorization checks. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

New signing primitives, live ingress activation, source approval policy changes, and reinterpreting historical records as new authority are excluded.

## Notes

D1/D2 block transactional settlement and acknowledgment until Dmitry rules; D3/D4 remain inherited C prerequisites. AC1 owns ruling-not-carried, AC2 non-atomic settlement, and AC3 request-status-never-updated. W50 AC2 owns answer/presentation binding and W57 AC1 the stale comment key. Preserve historical veldo.approval/v1, veldo.decision/v1 and veldo.verdict/v1 compatibility through typed materialization and actual reader validation; a new receipt is not a valid legacy record merely because it copies its schema name. Enrolled writes must retire FilesystemSettlementStore authority, retaining it only for explicit historical compatibility; use B journal, nonce and delivery transactions without a second ledger. The protected settlements glob covers accepted projections, not permission to author approvals. Map/inventory new engine copies and narrow settlement modules before ready. Retain complete crash-table observations, applied mutation diffs and failed rows.
