---
schema: veldo.spec/v1
id: VELDO-0073
title: Per-channel live ingress activation and real sandbox qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W58
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0067, VELDO-0072]
placement: [tracker, engine, contracts, distribution]
protected_paths: [.veldo/policy.yaml]
footprint:
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/tracker_mirror_runner.py"
  - ".veldo/tracker_mirror_runner.py"
  - "packs/*/.veldo/tracker_mirror_runner.py"
  - "engine/.veldo/control_channel_ingress*.py"
  - ".veldo/control_channel_ingress*.py"
  - "packs/*/.veldo/control_channel_ingress*.py"
  - "engine/.veldo/control_channel_activation*.py"
  - ".veldo/control_channel_activation*.py"
  - "packs/*/.veldo/control_channel_activation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/policy.yaml"
  - "engine/.veldo/policy.yaml"
  - "packs/*/.veldo/policy.yaml"
  - "scripts/suites/*_veldo_0073_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0073-channel-ingress-activation.md"
  - "specs/index.md"
  - "proof/VELDO-0073/*"
behavior_bearing: true
observability:
  logs: >
    Activation receipts identify channel, enrollment/key/delegation versions, installed adapter
    and sandbox-proof digests, permitted transport, activation authority, and rollback profile.
  metrics: >
    Expose inactive/session-start/live channel modes, last canonical cursor, reconnect backlog,
    blocked activation reasons, and actual sandbox test coverage.
  traces: >
    Join a separately authorized activation command to sandbox publication, canonical answer
    acquisition, restricted signing, one settlement, and recovered delivery observations.
  error_taxonomy: >
    Distinguish absent sandbox proof, unsafe signer, unestablished attribution, transport
    mismatch, stale activation inputs, ingress unavailable, and unauthorized live mutation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Live ingress and external decision mutations remain disabled per channel until a
      separate authorized activation binds current enrollment and real sandbox proof. Set:
      request_doorbell.TelegramSink.send, request_projection.project_from_repo,
      request_reconcile.reconcile_from_repo, tracker_mirror_runner.build_live_adapter, and
      proposed channel activation entry points. Completeness: Enumerate every outward mutation and
      ingress start from the installed inventory across Telegram chat, Jira, signed CLI and email
      when enrolled. Invoke direct APIs before activation and after source landing alone, remove
      or stale each proof/enrollment/key binding, and submit altered activation parameters under
      an old signature. Require refusal before external writes/listeners and no global enable flag
      that activates other channels. Falsifier: Allow TelegramSink.send to perform a
      decision-channel write merely because a token resolves; ingress/no-implicit-activation must
      detect the unauthorized send.
    falsified_by: >
      Allow TelegramSink.send to perform a decision-channel write merely because a token resolves;
      ingress/no-implicit-activation must detect the unauthorized send.
  - id: AC2
    text: >
      Claim: Every channel claimed live has real sandbox proof of presentation, canonical
      attribution, restricted signing, and one authoritative settlement with recovery. Set: The
      actual enrolled Telegram, Jira, signed CLI and email adapters entering request_projection,
      request_reconcile and B authority, including PLAN-0016 live tracker compatibility.
      Completeness: Freeze the enrolled channel matrix and map each to real sandbox or isolated
      signed-CLI processes and genuine platform accounts where applicable. Publish and retrieve
      presentations, answer as authorized and unauthorized actors, verify message/sender/time from
      platform or the CLI source signature, attempt edge-key escalation and stale presentation,
      then interrupt delivery/settlement and reconnect. Require attributable single settlement and
      exact external correlation. Missing email or chat evidence leaves that channel disabled;
      FakeTracker/FakeSink and C approval fixtures cannot certify it. Falsifier: Accept a
      FakeTracker-only report as Jira sandbox qualification; ingress/real-sandbox-required must
      detect activation without actual canonical platform evidence.
    falsified_by: >
      Accept a FakeTracker-only report as Jira sandbox qualification;
      ingress/real-sandbox-required must detect activation without actual canonical platform
      evidence.
  - id: AC3
    text: >
      Claim: Qualified notification/doorbell transport wakes canonical-history reconciliation with
      durable cursors, while compatibility pull remains honestly labeled until activated. Set:
      request_doorbell.notice_key/ring/TelegramSink.send, request_reconcile.reconcile_from_repo,
      and each control_channel_ingress adapter using B wake-up/cursor APIs. Completeness:
      Enumerate each installed transport capability and execute real disconnect, duplicate
      notification, out-of-order delivery, expired platform retention, and reconnect cases.
      Persist Telegram response identifiers rather than discarding response bytes. Treat a
      doorbell as a wake-up, never an assertion, and pull canonical evidence before acceptance;
      unprovable gaps block. Measure replay and finite reconnect bounds, no database polling for
      rare changes, and session-start-only display when the old tracker trigger is used.
      Falsifier: Settle directly from a notification payload without canonical acquisition;
      ingress/doorbell-is-not-answer must detect the unsupported assertion.
    falsified_by: >
      Settle directly from a notification payload without canonical acquisition;
      ingress/doorbell-is-not-answer must detect the unsupported assertion.
  - id: AC4
    text: >
      Claim: Revocation, configuration drift, or failed qualification stops only affected channel
      authority and preserves unsettled requests for another independently qualified channel. Set:
      control_channel_activation and authorization consumed by
      request_reconcile.reconcile_requests and request_projection.project_requests, across edge
      revocation, adapter upgrade, operations stop and restart. Completeness: Race each change
      with answer acceptance, kill ingress after stop commit, and restart against the durable
      activation record. Verify no implicit reactivation, retained original
      request/nonces/presentations, current authority rechecks, and explicit rollback to a
      compatible qualified profile. Record protected policy changes with exact commit/proof
      approval; no workflow permissions are widened to pass a sandbox test. Falsifier:
      Automatically reactivate a channel on restart after its explicit operations stop;
      ingress/stopped-stays-stopped must detect renewed answer acceptance.
    falsified_by: >
      Automatically reactivate a channel on restart after its explicit operations stop;
      ingress/stopped-stays-stopped must detect renewed answer acceptance.
required_evidence: [unit, integration]
rollback: >
  Record an authorized stop for the affected edge, revoke its fresh assertion permission, retain
  cursors and unresolved deliveries, and restore only a compatible qualified inactive profile.
---

## Intent

Activate each decision channel only after its actual installed edge proves safe in its own real sandbox.

## Context

Package E, W58 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R28, R36-R41, R50 and R60 separate source landing, enrollment and activation. The current live entry points can construct credentialed adapters, and TelegramSink discards the platform response; neither establishes qualified ingress. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Unreviewed board redesign, blanket activation of every channel, provider-worker qualification, and automatic membership enrollment are excluded.

## Notes

D1/D2 block authority and published settlement; D3 blocks activated service/transport supervision and D4 remains inherited through C. Before ready, record each permitted transport, sandbox access, enrolled test principal, finite retention/reconnect bounds, and exact proof commands. Source-only channel names are not enrollment. No missing additional authority is invented, and email remains unavailable until its own attribution and presentation proof exists. This spec includes protected .veldo/policy.yaml only for concrete version-bound activation policy, with corresponding engine/pack policy copies if the shared contract changes; source landing still cannot enable a running edge. Canonicalize repository-only adapters and inventory new ingress/configuration assets through W30. Retain each applied mutation, failed row and real sandbox receipts; redacted evidence must retain verifiable provenance.
