---
schema: veldo.spec/v1
id: VELDO-0066
title: Canonical channel attribution including platform-derived chat message, sender, and time
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W51
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0064]
placement: [tracker, engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/tracker_adapter.py"
  - ".veldo/tracker_adapter.py"
  - "packs/*/.veldo/tracker_adapter.py"
  - "engine/.veldo/tracker_jira_live.py"
  - ".veldo/tracker_jira_live.py"
  - "packs/*/.veldo/tracker_jira_live.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_channel_attribution*.py"
  - ".veldo/control_channel_attribution*.py"
  - "packs/*/.veldo/control_channel_attribution*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0066_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0066-canonical-channel-attribution.md"
  - "specs/index.md"
  - "proof/VELDO-0066/*"
behavior_bearing: true
observability:
  logs: >
    Attribution evidence records platform account/message/history identity, canonical timestamp,
    actor kind, source API or verified command signature, and mapped membership revision.
  metrics: >
    Count unestablished actors, display-name collisions, missing history pages, edited answers
    without lineage, and mismatched platform/presentation identities.
  traces: >
    Join authenticated platform retrieval or CLI signature verification to immutable evidence
    bytes, principal mapping, presentation reference, and the proposed assertion.
  error_taxonomy: >
    Distinguish unknown actor kind, automation actor, unbound sender, history gap, contradictory
    edit, unverifiable email source, and command digest mismatch.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Platform-derived stable identity and ordering reach reconciliation without
      display-name or timestamp-field substitution. Set:
      tracker_adapter.normalize_changelog/normalize_actor_kind, tracker_jira_live.fetch_changelog,
      request_reconcile._opening_actor/_entry_actors/_reconcile_one, and authorization.actor_kind
      for Jira and enrolled Telegram chat. Completeness: Enumerate normalized fields and
      actor-kind vocabularies and run authenticated retrieval in real channel sandboxes. For chat
      retain platform message ID, sender ID, timestamp and conversation identity pulled from the
      platform; for Jira retain account ID, history ID, created time and actor kind. Rename
      display names, collide them, omit actor kind, and inject text-only transcripts. Require
      stable enrolled principal mapping and reject automation or unknown identity for
      person-required decisions. Falsifier: Use displayName instead of account_id to map a Jira
      answer after two accounts share that name; attribution/display-name-collision must detect
      the false principal.
    falsified_by: >
      Use displayName instead of account_id to map a Jira answer after two accounts share that
      name; attribution/display-name-collision must detect the false principal.
  - id: AC2
    text: >
      Claim: Canonical history must prove the answer and its relation to a presentation before an
      edge may assert it. Set: tracker_jira_live.fetch_changelog,
      tracker_adapter.TrackerAdapter.read_changelog, request_reconcile._terminal_decision and
      enrolled chat/email attribution adapters. Completeness: Inventory pagination and edit/delete
      semantics for each qualified platform. Retrieve real multi-page history, interrupt
      retrieval, hit the page bound, remove an opening event, introduce contradictory terminal
      actions and edits with missing provenance. Require complete attributed lineage or named
      refusal; _opening_actor cannot fall back to the first available actor. Email remains
      unavailable without authenticated canonical sender/message/time and presentation evidence;
      claimed From text alone is insufficient. Falsifier: Return a partial history as complete
      when fetch_changelog exhausts its page cap; attribution/history-gap must reject the
      otherwise plausible answer.
    falsified_by: >
      Return a partial history as complete when fetch_changelog exhausts its page cap;
      attribution/history-gap must reject the otherwise plausible answer.
  - id: AC3
    text: >
      Claim: Signed CLI decisions retain the verified personal command signature inside their
      channel assertion and bind the actual executed command. Set:
      request_reconcile.reconcile_requests and authorization.is_authorized integrated with the
      enrolled CLI attribution adapter and B command verifier. Completeness: Use real OpenSSH
      Ed25519 signatures and processes; enumerate A envelope fields and mutate operation, target,
      every parameter, enrollment public key, request/presentation versions,
      domain/repository/store, nonce, expiry, and membership/delegation versions independently.
      Verify the canonical command digest from executed bytes, preserve source signature evidence,
      and reject unsigned terminal text or transport-only authentication. Falsifier: Skip
      canonical command-digest recomputation and substitute the ruling under a retained valid CLI
      signature; attribution/cli-ruling-substitution must detect the accepted altered command.
    falsified_by: >
      Skip canonical command-digest recomputation and substitute the ruling under a retained valid
      CLI signature; attribution/cli-ruling-substitution must detect the accepted altered command.
required_evidence: [unit, integration]
rollback: >
  Disable assertions from any channel with unprovable attribution, preserve raw evidence and
  membership history, and requalify acquisition before accepting new answers.
---

## Intent

Establish who answered and which platform action they made from canonical evidence on each enrolled channel.

## Context

Package E, W51 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R36, R38, R60, and R72 require canonical attribution. The current normalizer emits at/account_id/actor_kind, but reconciliation uses actor display strings and settlement reads ts, losing both identity and ordering evidence. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Quorum settlement, membership-policy changes, provider account identity, and live ingress activation are outside this attribution concern.

## Notes

D1/D2 block stored attribution assertions and acknowledgment; D3/D4 are inherited C prerequisites. Real sandbox access and separately enrolled test identities are required to prove each channel; fixtures cannot certify identity retrieval. No additional authority is invented: absent named enrollment blocks that assignment or quorum. W52 supplies restricted edge signing, and W58 gates live activation even when these acquisition tests pass. Repair the existing tracker normalizer and reconcile functions in canonical engine copies with W30 inventory; map control_channel_attribution before ready. Preserve canonical evidence with secret-safe proof references, mutation diffs, and named failures. An edge signature attests acquisition; it never pretends the platform action had a personal local signature.
