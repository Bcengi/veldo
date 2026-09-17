---
schema: veldo.spec/v1
id: VELDO-0064
title: Assignment inbox and durable projections on enrolled input surfaces
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W49
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
placement: [contracts, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/tracker_adapter.py"
  - ".veldo/tracker_adapter.py"
  - "packs/*/.veldo/tracker_adapter.py"
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "packs/*/.veldo/control_assignment*.py"
  - "engine/.veldo/control_channel_projection*.py"
  - ".veldo/control_channel_projection*.py"
  - "packs/*/.veldo/control_channel_projection*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0064_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0064-assignment-inbox-projections.md"
  - "specs/index.md"
  - "proof/VELDO-0064/*"
behavior_bearing: true
observability:
  logs: >
    Inbox records identify assignment/request versions, required actor and scope, destination
    channel, durable correlation, external object ID, and pending delivery reason.
  metrics: >
    Expose offered, waiting, expired, and reassigned counts plus projection lag, unresolved
    creations, and worker/claim resources retained by waiting assignments.
  traces: >
    Join a committed assignment and delivery obligation to each enrolled channel object and its
    acknowledgment, keeping the authority watermark visible.
  error_taxonomy: >
    Distinguish missing enrollment, unsatisfied actor predicate, stale reassignment, delivery
    pending, uncertain external creation, and correlation conflict.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One authoritative assignment inbox exposes work requiring a person on every enrolled
      decision surface without reserving a worker or claim while awaiting the answer. Set:
      request_projection.build_request_index/project_requests and request.validate_record
      integrated with R18 assignment states for Telegram chat, Jira, signed CLI, and email when
      enrolled. Completeness: Derive all states and actor predicates from A assignment schemas and
      compare the enrolled channel registry to delivery rows. Drive offered, accepted,
      in-progress, submitted, satisfied, declined, expired, canceled, and reassigned cases through
      real authority commands and fresh readers. Require retained deadline/budget/actor
      predicates, visible pending delivery, and no model process or execution claim solely for
      waiting. Falsifier: Keep a worker claim for an assignment awaiting a person after inbox
      publication; inbox/waiting-resources must detect the retained claim.
    falsified_by: >
      Keep a worker claim for an assignment awaiting a person after inbox publication;
      inbox/waiting-resources must detect the retained claim.
  - id: AC2
    text: >
      Claim: Projection creation persists channel-specific external identifiers and correlation so
      lost acknowledgments trigger lookup rather than blind creation. Set:
      request_projection._project_one/project_from_repo,
      tracker_adapter.TrackerAdapter.create_or_update_child/find_child, and corresponding enrolled
      channel projection adapters backed by B delivery/effect records. Completeness: Enumerate
      create/send, remote acceptance, local correlation commit, and acknowledgment barriers for
      each channel; kill the projector at each using real local receiver/storage processes. Reopen
      authority state and look up the original correlation, requiring one object or explicit
      uncertainty when the target cannot prove its outcome. Live target qualification is required
      by W58 before activation. Falsifier: Retry create_or_update_child with a fresh correlation
      after remote creation but before local acknowledgment; inbox/lost-create-ack must detect
      duplicate external objects.
    falsified_by: >
      Retry create_or_update_child with a fresh correlation after remote creation but before local
      acknowledgment; inbox/lost-create-ack must detect duplicate external objects.
  - id: AC3
    text: >
      Claim: Channel views and reassignment cannot grant authority or change accepted assignment
      predicates. Set: request_projection.project_requests/build_brief and
      request_doorbell.build_notice/ring for all enrolled channels and authorized inbox readers.
      Completeness: Race two reassignment commands against one version in real SQLite, supersede
      an assignment before delivery, and remove Jira enrollment while another qualified channel
      remains. Compare published views with current authority and require exact scope and
      originating-channel links, no tracker-first requirement, no local lifecycle writes, and no
      admission from assignee or status alone. Falsifier: Require a tracker issue link before
      projecting an otherwise valid enrolled chat assignment; inbox/chat-without-jira must detect
      the missing chat projection.
    falsified_by: >
      Require a tracker issue link before projecting an otherwise valid enrolled chat assignment;
      inbox/chat-without-jira must detect the missing chat projection.
required_evidence: [unit, integration]
rollback: >
  Pause delivery and retain inbox versions, external correlations, and pending effects; recover
  existing objects before resuming projections.
---

## Intent

Make waiting assignments durable and reachable on the enrolled channel where the assigned person works.

## Context

Package E, W49 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R18, R28, R41, and R60 require channel projections of one inbox. Lost creation identity or a misleading assignment can strand decisions or misdirect scoped authority. The declared risk floor is high; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Presentation digest design, quorum settlement, new project workflow, and live ingress activation are separate concerns.

## Notes

D1/D2 block durable inbox and published delivery obligations. D3/D4 remain inherited prerequisites through C, with no new host or clone choice here. The baseline build_request_index silently skips unreadable files and _project_one does not persist returned issue correlation; enrolled reads must use B snapshots and surface invalid records. request_projection, request_doorbell, and tracker_adapter currently have repository-only implementations: establish canonical engine copies and explicit W30/scaffolder inventory before installed use. Map proposed assignment/channel modules to contracts/tracker before ready. W50 owns receipt content, W53 settlement, and W58 actual channel activation. Preserve per-channel create/lookup evidence and each applied mutation with its failed row, then revert it.
