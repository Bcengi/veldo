---
schema: veldo.spec/v1
id: WARP-1008
title: Release tracker-driven autonomous fleet v1 (PLAN-0010 at 8/8) - plugin 3.6.0
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W8
plan_revision: 1
depends_on: [WARP-1002, WARP-1003, WARP-1004, WARP-1005, WARP-1006, WARP-1007]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The plugin version is bumped to 3.6.0 for the tracker-driven autonomous fleet v1
      milestone: packs/claude/.claude-plugin/plugin.json is 3.6.0, the marketplace entry
      (.claude-plugin/marketplace.json) is 3.6.0, and README.md reads 3.6.0. The method
      document is unchanged (this ships a capability, not a change to the generic method).
  - id: AC2
    text: >
      The docs are made TRUE for the autonomous loop: the tracker operator guide
      (docs/tracker-operator-guide.md), docs/plugin.md section 12, and the README tracker
      bullet describe the shipped end-to-end flow accurately - the single Agent user and
      the eligibility triple (assigned to Agent, Approved-for-dev, resolvable repo), the
      inbound bridge drafting a spec and posting it on the ticket, the human promote in
      Jira, the fleet building, the mirror writing status and artifact links and
      reassigning to the reviewer (default reporter) at ready-to-test, a requirements page
      becoming a plan then a live epic and child issues, and the opt-in off-by-default
      "veldo mirror" runner. Every command, config field, and behavior named exists in the
      shipped code; the live Jira edge is described as reference (token_ref, wired per
      repo), not turnkey.
  - id: AC3
    text: >
      capabilities.yaml is accurate for the whole PLAN-0010 surface (eligibility, inbound
      bridge, promote gate, assign op, ready-to-test handoff, mirror runner, live
      epic/child, doc-to-plan generator) in both byte-identical copies, with no capability
      claimed that an adopter's tree does not carry.
  - id: AC4
    text: >
      With W1 through W8 shipped, plan.py release-check PLAN-0010 reports releasable and
      PLAN-0010 status is set to released. At the impl commit W8 is ready; releasability is
      achieved when this spec flips to shipped and the plan to released in the reviewed
      release commit, verifiable independently by simulating WARP-1008 shipped and running
      release-check.
  - id: AC5
    text: >
      The full gate is GREEN (selftest, contracts, generated/docs/secret checks, the
      dash/genericity sweeps), RULE #1 is clean, and no protected path is touched. The
      change lands in the CANONICAL release two-commit shape: one reviewed commit carrying
      the version bump, this spec (status shipped), PLAN-0010 (status released), and the
      docs, with the verdict binding to it, then an evidence-only commit (proof/, .veldo/)
      on top. Do not split the plan flip into an evidence commit.
required_evidence: [operational]
rollback: >
  git revert the release commit and its evidence; the version bump withdraws, PLAN-0010
  returns to in_progress, and the shipped W1-W7 capabilities keep working unchanged (the
  release adds no behavior of its own).
---

## Intent

Release the tracker-driven autonomous fleet: Jira is the work queue, a ticket assigned
to the Agent user and moved to Approved-for-dev flows into the fleet through a
human-validated spec, and the fleet builds it and mirrors the ticket forward. All eight
work items are shipped; this item bumps the version, makes the documentation true for
the whole loop, and marks the plan released.

## Context

- The prior plan release (WARP-0810 / WARP-0908) is the canonical model for the shape:
  the reviewed release commit carries the version bump, the spec flipped to shipped, the
  PLAN flipped to released, and the docs; the evidence-only commit on top carries the
  proof and verdict. Doing it in that order the first time avoids the topology restructure
  that a plan flip in an evidence commit forces (evidence-only must touch only
  proof/.veldo/specs, never plans/).
- Current version is 3.5.0 (PLAN-0009). Bump to 3.6.0.
- Docs to make true: docs/tracker-operator-guide.md and docs/plugin.md section 12 (the
  WARP-0610/0611 tracker docs) plus the README tracker bullet - extend them from "capability
  exists" to "here is the autonomous loop", accurate to WARP-1001 through 1007.
- capabilities.yaml already carries the PLAN-0010 entries (added per item); confirm they
  are accurate and complete for the release.

## Out of scope

- No code change to any W1-W7 behavior. No live wiring against a real instance. No method
  document change.

## Notes

- Author the reviewed commit in the canonical release shape from the start. Verify
  release-check releasable by simulating WARP-1008 shipped before finalizing.
- Docs must be true, not aspirational: the live Jira edge is reference (token_ref), the
  runner is opt-in and off by default, the human validates the spec. Follow the
  byte-identical engine sync discipline for any engine file; today is 2026-07-21 so the
  index restamps.
