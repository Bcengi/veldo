---
schema: veldo.spec/v1
id: WARP-1004
title: Outbound reassignment and artifact links - the ready-to-test handoff on the ticket
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W4
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The WARP-0603 TrackerAdapter seam gains an assign(obj_id, assignee) write with
      the same base-owned guarantees as the other writes: it is EXPLICIT (appended to
      the writes() audit), idempotent by TARGET (assigning the assignee an object
      already holds records no change and returns False; a real change returns True),
      input is validated by name (a blank obj_id or assignee is a TrackerAdapterError),
      and assigning an object the tracker does not hold FAILS LOUD (TrackerItemNotFound),
      never a silent no-op. FakeTracker implements it in-memory; the live JiraCloud
      adapter is wired in a later increment (WARP-1005) and is not exercised here.
  - id: AC2
    text: >
      The mirror projects ARTIFACT LINKS onto the ticket: at the build-complete point
      of a spec's lifecycle it posts a KEYED comment carrying the links that exist -
      the commit, and where present the pull request and the proof - so re-running the
      mirror posts them at most once. It writes only comments/fields, never a spec or
      plan definition (the repository stays the source of truth).
  - id: AC3
    text: >
      At the ready-to-test handoff (the spec entering review after a build), the mirror
      REASSIGNS the ticket away from the Agent user to the configured reviewer,
      defaulting to the ticket's reporter, using a per-repo reviewer setting in
      .veldo/trackers.json (PLAN-0010 C7). It reuses the new assign seam op, is
      idempotent (reassigning to the current assignee is a no-op), and reassigns only
      at that transition - an earlier lifecycle point leaves the assignee (Agent)
      untouched so the fleet keeps the ticket while it works.
  - id: AC4
    text: >
      Gate-tested over the FakeTracker with teeth: at the ready-to-test transition the
      ticket is reassigned to the reviewer (defaulting to the reporter) exactly once
      and the artifact links are posted once; a lifecycle point BEFORE ready-to-test
      does NOT reassign (Agent keeps it), proven non-tautologically; re-running posts
      no duplicate comment and performs no duplicate reassignment (idempotent by target
      and by comment key); and assign to a missing object fails loud.
  - id: AC5
    text: >
      capabilities.yaml gains honest entries for the assign seam op and the
      reassign/links mirror behavior (mechanical, their shipped homes) in both
      byte-identical copies; every edited ENGINE_GLOBS file is re-synced byte-identical
      across engine and all seven packs (template-sync and pack-drift pass).
      The full gate is GREEN, RULE #1 is clean, no protected path is touched, and the
      change lands in the canonical two-commit shape.
required_evidence: [unit]
rollback: >
  Revert the commit. The assign op and the reassign/links behavior are additive; the
  live adapter still raises for assign until WARP-1005, and the FakeTracker path is
  gate-only, so removing this leaves the mirror at its prior status-plus-comment
  behavior with no migration.
---

## Intent

This is the outbound handoff the founder described: when a worker finishes, the
ticket should show the work (links to the commit, the pull request, and the proof)
and change hands - reassigned away from the Agent to the person who tests it,
defaulting to whoever raised it. The human never hand-updates the ticket; the
mirror does it as the spec crosses into review.

## Context

- Extend, do not rebuild: the adapter seam is .veldo/tracker_adapter.py (add assign
  alongside comment/set_status/create_or_update_epic/create_or_update_child, with the
  same base-owned audit + idempotency-by-target + fail-loud guarantees; add it to
  FakeTracker). The mirror is .veldo/tracker_mirror.py (its EVENT_STATUS lifecycle
  mapping is where the ready-to-test point lives - reassign + links hang off that
  same transition).
- The reviewer is a per-repo setting in .veldo/trackers.json defaulting to the
  ticket's reporter (PLAN-0010 C7). The Agent user (WARP-1001 config) is who the
  ticket is reassigned AWAY from.
- Artifact links: the commit is always available at ship; the PR and proof links are
  posted when present, never fabricated. Keyed comment so it is idempotent.
- The live JiraCloud assign/transition is WARP-1005; here everything is proven offline
  against the FakeTracker.

## Out of scope

- No live Jira runner (WARP-1005), no live epic/child creation (WARP-1006). The assign
  op is added to the seam + fake here; the live adapter still raises until WARP-1005.
- No change to the inbound bridge or the promote gate.

## Notes

- Keep the mirror additions pure control logic over the seam so the gate drives them
  with the FakeTracker. Idempotent everywhere: reassign by target, links by comment
  key. Fail loud on an assign to a missing object.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Match the existing mirror/adapter selftest conventions and their teeth.
