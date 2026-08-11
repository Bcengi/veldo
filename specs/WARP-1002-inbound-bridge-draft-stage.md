---
schema: veldo.spec/v1
id: WARP-1002
title: The inbound bridge, draft stage - draft a spec from an Agent ticket and post it back for validation
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W2
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A non-LLM inbound bridge reconciles the tracker into spec drafts. Over the
      WARP-0603 adapter seam it lists candidate tickets (assigned to the single Agent
      user with a resolvable repo tag), and for each candidate that has no existing
      VELDO spec yet, it runs the shipped intake (draft_spec_from_item) to produce a
      veldo.spec/v1 DRAFT (status: draft) bound to the resolved repo, written under
      that repo's specs/. It reuses is_eligible/routing and the intake logic; it adds
      no second parser and no LLM call.
  - id: AC2
    text: >
      The bridge is a RECONCILER, idempotent with no processed-offset ledger: a
      ticket that already has a spec (linked by its intake_source) is skipped, not
      redrafted, so re-running the bridge over the same tickets creates no duplicate
      spec and leaves state byte-identical. Determining "already drafted" is by the
      durable intake_source link, not by a side store.
  - id: AC3
    text: >
      Two-stage validation (PLAN-0010 D1, resolved to 2-stage): after drafting, the
      bridge posts the drafted spec back onto the ticket as a KEYED comment (so it
      posts at most once under re-run), so the human reviews the actual spec VELDO
      will build before approving it. The draft is NOT promoted to ready here (that
      is the human's Jira action, wired in WARP-1003); a draft is not claimable, so
      nothing builds yet.
  - id: AC4
    text: >
      The bridge is pure control logic over the injected adapter seam and the shipped
      intake, driving the offline FakeTracker in the gate with teeth: a candidate
      (Agent + resolvable repo, no existing draft) is drafted and its spec is posted
      to the ticket exactly once; and non-candidates are left alone, proven with
      single-leg negatives - a non-Agent or unassigned ticket, a ticket with no
      resolvable repo, and an already-drafted ticket each produce no draft and no
      comment. No live network in the gate; the live Jira query path is the same
      reference adapter used elsewhere.
  - id: AC5
    text: >
      capabilities.yaml gains an honest entry for the bridge (mechanical, its shipped
      home) in both byte-identical copies; every edited ENGINE_GLOBS file is re-synced
      byte-identical across engine and all seven packs (template-sync and
      pack-drift pass). The full gate is GREEN, RULE #1 is clean, no protected path is
      touched, and the change lands in the canonical two-commit shape.
required_evidence: [unit]
rollback: >
  Revert the commit. The bridge is additive and nothing runs it automatically yet
  (its unattended runner and the promote gate are later items); removing it leaves
  the tracker and fleet exactly as before.
---

## Intent

This is the inbound half of making Jira the work queue: turn a ticket the founder
has pointed at the fleet into a VELDO spec draft, and surface that draft on the
ticket so a human can validate the machine's interpretation before any build. It
is the first stage of the 2-stage gate - draft and show, then (WARP-1003) the human
approves in Jira. It is deterministic non-LLM Python so it can run unattended later
without an agent in the loop.

## Context

- Reuse the shipped pieces: is_eligible and resolve_repo (WARP-1001 / WARP-0601) in
  .veldo/tracker.py, and draft_spec_from_item in .veldo/tracker_intake.py (which
  already binds the draft to the repo and records intake_source). The adapter seam
  (.veldo/tracker_adapter.py) provides list_intake_items/read_item and comment.
- The draft trigger is Agent + resolvable repo (an Agent-destined, routable ticket),
  independent of the ready status - drafting happens before approval so the human
  can review. The ready-status gate (Approved-for-dev) is the PROMOTE trigger in
  WARP-1003, not here.
- Idempotency is by the durable intake_source link on the drafted spec, matching the
  mirror's reconciler pattern (no offset ledger, no second store).
- Non-LLM: the bridge only calls the adapter seam and the mechanical intake; it never
  invokes an agent. Tracker content stays untrusted input (the intake already
  sanitizes front matter).

## Out of scope

- No promotion to ready (WARP-1003), no unattended runner/poller (the bridge is a
  callable reconciler here; the live service is WARP-1005-style), no reassignment or
  status mirror (WARP-1004), no plan generation (WARP-1007).
- No live Jira in the gate; the FakeTracker drives all assertions.

## Notes

- Keep the bridge a pure function over an injected adapter + a repo-root resolver so
  the gate drives it with a FakeTracker and a temp repo, no network. Fail closed: a
  ticket that does not cleanly resolve is skipped, never drafted to a default.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Match the existing tracker selftest conventions.
