---
schema: veldo.spec/v1
id: WARP-0617
title: the outbound Decision projection - a one-way, idempotent, redacted mirror of a veldo.request/v1
  onto a VEL Decision issue (brief + explicit RISK + what-approving-vouches-for + options/dead-ends +
  the DISPLAYED bound digest + assignee + watchers), reusing the shipped mirror (W3 of the human-decision
  surface)
status: shipped
risk: standard - a repo-only projection module (a sibling of .veldo/tracker_mirror.py) that REUSES the
  shipped one-way mirror seam and the WARP-0613 snapshot pattern; the live writes go through the already-
  reference-wired fenced OAuthJiraCloudAdapter and are NEVER run in the gate (the FakeTracker path is). It
  touches NO protected path and nothing in the safety core, and it writes ONLY through the tracker seam
  (never a repo record, never a spec/plan/request definition), so it cannot become a second source of
  truth. Its IMPORTANCE is high (it is what a human actually reads to decide, and a leak here would put
  secrets/operating data onto a third-party surface), so it carries a rigorous independent review of the
  redaction and the one-way guarantee even though the mechanical footprint is standard-tier
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W3
plan_revision: 1
placement: [tracker]
footprint:
  - .veldo/request_projection.py
  - .veldo/tracker_adapter.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - .veldo/architecture.yaml
  - scripts/selftest.py
  - specs/WARP-0617-outbound-decision-projection.md
  - specs/index.md
  - proof/WARP-0617/**
protected_paths: []
behavior_bearing: true
observability:
  logs: the projection emits a structured report of exactly what reached the board (requests projected,
    created vs reused, status transitions made vs already-present, comments posted, watchers set, and any
    request skipped by reason), so a stranger can see what one pass did from the report alone.
  error_taxonomy: a request that is not wired for a tracker (no tracker config) is a clean no-op; a
    malformed request is already refused upstream by check_requests_dir; a status with no mapping is a
    keyed comment, never an invented transition (NG4). No secret or operating datum ever reaches a
    projected write - the redactor removes it before the write, and a redaction failure fails closed
    (the field is dropped, never emitted raw).
acceptance_criteria:
  - id: AC1
    text: A one-way projection (a sibling of tracker_mirror.mirror_events, in a new repo-only module
      .veldo/request_projection.py) reads the veldo.request/v1 records from .veldo/requests/ and upserts ONE
      VEL Decision issue per request, keyed by the request id (never forked), through the shipped WARP-0603
      seam (create_or_update_child/comment/set_status/assign) - reusing resolve_status_map and the NG4
      guarantee (an unmapped VELDO status is a keyed comment, never an invented transition). It writes ONLY
      through the seam, NEVER back into a request/spec/plan record or the requests index (verified: the
      index is byte-identical after a run), so the repository stays the single source of truth. It is
      IDEMPOTENT: a re-run forks no issue, records no duplicate transition or comment, and leaves the board
      byte-identical.
  - id: AC2
    text: The projected Decision issue carries the readable BRIEF in its body: a plain-language summary;
      an explicit RISK section (the tier and why, reversible|costly|irreversible, the impact flags
      data_mutating/money/external, fake-vs-live, residual trust); WHAT approving vouches for and what it
      does NOT; the options with their dead-ends (read from the bound veldo.decision/v1 when the touchpoint
      is decision_choice); and the bound_artifact DIGEST DISPLAYED (so the human and the future inbound
      edge share one binding). The issue is assigned to the responsible human approver and the configured
      watchers are set. It DISPLAYS bound_artifact.digest as the binding - it never presents request_hash
      as a verified value to a human (request_hash self-consistency is a W2 creation-time invariant, the
      repo-recompute is W5).
  - id: AC3
    text: A REDACTION step scrubs secrets and operating data (per RULE #3) from the brief, the RISK
      section, and every projected comment BEFORE the write leaves the repo - secret references
      (env:/keychain:) and any declared-sensitive field are removed or masked, and the redactor fails
      closed (on any doubt the field is dropped, never emitted raw). Inbound ticket content is treated as
      untrusted DATA, never instructions (the posture already in tracker_intake/tracker_bridge is
      reaffirmed, not re-implemented). A selftest asserts a request carrying a secret reference and an
      operating datum projects with them redacted and never in the clear.
  - id: AC4
    text: It is wired so the board bootstrap / a veldo jira command can run the projection (offline over
      the deterministic FakeTracker with no network for the gate; the live path builds the SAME fenced
      OAuthJiraCloudAdapter as the mirror and FAILS CLOSED with no token). The Decision issue uses the VEL
      Decision issue type; the request status maps onto the provisioned VEL states (Needs Decision, In
      Discussion, Awaiting Approval, Changes Requested, Decided/Approved/Rejected/Blocked/Superseded)
      through the per-org status_map. It creates no timer/daemon and spawns nothing detached (NG1).
  - id: AC5
    text: A selftest drives the WHOLE projection over the deterministic FakeTracker offline (no network)
      and is NON-TAUTOLOGICAL - a request of each touchpoint projects one Decision issue with the brief +
      RISK + displayed digest + assignee + watchers; a re-run is byte-identical (idempotent); the requests
      index is byte-unchanged (one-way); a secret/operating datum is redacted (never in the clear); an
      unmapped status is a keyed comment not a transition (NG4) - each with an in-memory source-mutation
      TOOTH that turns its assertion red while the on-disk module stays byte-unchanged (neutralizing the
      redactor emits the secret; neutralizing the keyed-upsert reuse forks on a re-run; neutralizing the
      NG4 guard invents a transition). None of the teeth is vacuous.
required_evidence: [unit]
rollback: git revert; additive - a new repo-only projection module reusing the shipped mirror seam, a
  read of the requests index, a redactor, one capability entry (all eight capabilities.yaml byte-
  identical), the module declared in the tracker area of architecture.yaml, a selftest block, and this
  spec; no protected path; the live edge is the already-shipped fenced adapter, never run in the gate;
  pure stdlib.
---

## Intent

A human decides by reading a ticket. This projects a veldo.request/v1 (the W2 envelope) onto a VEL Decision
issue that carries everything a person needs to decide well - a plain summary, an explicit RISK section,
what approving does and does not vouch for, the options and their dead-ends, and the exact bound digest -
assigned to the responsible human with watchers set. It is a one-way, idempotent mirror (the repository
stays the source of truth; the ticket is a projection), and it REDACTS secrets and operating data before
anything leaves the repo onto the third-party surface (RULE #3). It reuses the shipped one-way mirror and
the WARP-0613 snapshot pattern; it invents no new projection machinery and writes nothing authoritative
back.

## Context

W3 of the approved human-decision surface (VEL-1), composing on W2 (veldo.request/v1, WARP-0615), the shipped
mirror (tracker_mirror, WARP-0605/0606 + the WARP-0613 snapshot), the WARP-0603 seam + FakeTracker, and the
live fenced board + OAuth adapter (WARP-0612/0614). It reads the request; the inbound edge (W5) writes the
settlement + advances the status; this only projects outward. It DISPLAYS bound_artifact.digest as the
binding a human and the inbound edge share; request_hash stays an internal integrity value (self-consistent
at creation per W2, repo-recomputed at W5), never presented to a human as verified.
