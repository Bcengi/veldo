---
schema: veldo.spec/v1
id: VELDO-0075
title: Andon delivery and authorized resumption through enrolled channels
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W60
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068]
placement: [tracker, engine, fleet, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_andon*.py"
  - ".veldo/control_andon*.py"
  - "packs/*/.veldo/control_andon*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0075_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0075-andon-delivery-resumption.md"
  - "specs/index.md"
  - "proof/VELDO-0075/*"
behavior_bearing: true
observability:
  logs: >
    Andon records identify requesting principal, interrupted station, stop reason, outstanding
    effects, designated resolving authority, and per-channel delivery obligation.
  metrics: >
    Measure durable stops, pending notification ages, uncertain send outcomes, unauthorized resume
    attempts, and units still awaiting current reconciliation.
  traces: >
    Join the original stop command through channel-specific presentation and canonical answer to
    one accepted ruling, recovery evidence and resumed station contract.
  error_taxonomy: >
    Distinguish authenticated stop request, delivery failure, absent resuming authority, stale
    presentation, unresolved effect, revoked permission, and obsolete resume contract.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Any authenticated agent or service can request AWAITING_AUTHORITY, and Veldo persists
      the stop even when its requester cannot resolve it. Set: request.validate_record and
      request_projection.project_requests with the proposed control_andon command path, B
      authorization and durable stop obligations. Completeness: Enumerate accepted requester kinds
      and interrupted stations from A; use real authenticated client processes to request stops
      with outstanding running/unknown effects. Revoke the requester ability to resume, kill after
      stop commit before notification, and restart. Require durable reason, interrupted station,
      resolving-authority predicate and queued/running permission closure; notification failure
      cannot erase the stop or release uncertain reservations. Falsifier: Reject an authenticated
      agent stop request solely because it lacks the resolving role;
      andon/request-without-resume-role must detect the missing durable stop.
    falsified_by: >
      Reject an authenticated agent stop request solely because it lacks the resolving role;
      andon/request-without-resume-role must detect the missing durable stop.
  - id: AC2
    text: >
      Claim: Andon delivery reaches enrolled decision surfaces with durable correlation and the
      current presentation, without requiring a tracker ticket or granting authority from a
      notice. Set: request_doorbell.notice_key/build_notice/ring/TelegramSink.send and
      request_projection._project_one for Telegram chat, Jira, signed CLI and email when enrolled.
      Completeness: Compare delivery registrations to enrolled channels and use qualified real
      sandbox sends. Change request version while status remains unchanged, lose send
      acknowledgment, disconnect a channel and restart the notifier. Require new version-bound
      notice identity, retained pending obligation and lookup of original message correlation or
      explicit uncertainty; show the originating channel answer path and never tell a chat
      participant that only Jira can decide. Falsifier: Keep notice_key as request ID plus status
      when a revised andon retains its status; andon/revised-notice must detect suppression of the
      current presentation.
    falsified_by: >
      Keep notice_key as request ID plus status when a revised andon retains its status;
      andon/revised-notice must detect suppression of the current presentation.
  - id: AC3
    text: >
      Claim: Only the designated authority or a signed applicable automatic recovery policy can
      resume the unit through one current settlement. Set:
      request_reconcile._reconcile_one/reconcile_requests and
      authorization.required_roles/is_authorized with control_andon resumption and B
      effect-recovery commands. Completeness: Enumerate resolving role, named principal, policy
      scope, expiry, and outstanding-effect predicates; exercise each on every enrolled surface
      with real signed assertions. Race concurrent resume answers, changed scope, revoked
      membership/edge and stale presentation against acceptance. Require current complete read
      sets, reconciled effects or explicit authorized retained-risk disposition, durable
      replicated ruling and a fresh station contract; neither a notice nor process absence
      establishes nonexecution. Falsifier: Resume after an arbitrary authenticated notifier
      acknowledgment without the designated resolving authority; andon/unauthorized-resume must
      detect renewed execution permission.
    falsified_by: >
      Resume after an arbitrary authenticated notifier acknowledgment without the designated
      resolving authority; andon/unauthorized-resume must detect renewed execution permission.
required_evidence: [unit, integration]
rollback: >
  Keep units stopped, preserve pending notices and unresolved effects, and require current
  designated authority to restore a qualified resumption path.
---

## Intent

Make authority-required stops durable, deliverable where decisions occur, and resumable only under the current resolving authority.

## Context

Package E, W60 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R13, R28, R32, R39-R41, R60 and R74 distinguish requesting a stop from authorizing resumption. The current doorbell requires a tracker URL and deduplicates only by request/status, so revised stops can disappear from view. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Automatic host failover, new emergency powers, arbitrary compensation, and channel activation policy are excluded.

## Notes

D1/D2 block authoritative stop and published resumption, D3 blocks independent running-work stop supervision, and D4 remains inherited through C. W49 owns the general inbox, W50 presentations, W53 one settlement; this item composes those for andon rather than inventing another approval path. W60 has no plan dependency on W58, so it may implement with real local transport fixtures after its declared prerequisites, but any live channel proof or activation still requires that channel W58 qualification. Missing sandbox access blocks live evidence, never permits credentials to bypass activation. Canonicalize the repository-only doorbell/projection/reconcile modules, map control_andon and inventory it through W30 before ready. Save stopped-state snapshots, send/lookup receipts and every mutation diff with its failed row. A signed risk disposition cannot rewrite an unknown historical effect into nonexecution.
