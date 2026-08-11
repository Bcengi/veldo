---
schema: veldo.spec/v1
id: WARP-1006
title: Live epic and child creation - project a plan onto real Jira epics and child issues
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W6
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The live JiraCloud adapter completes create_or_update_epic and
      create_or_update_child (today both raise "later increment WARP-1006") against
      Jira Cloud REST: an epic issue keyed by a stable marker (the plan id) is created
      once and updated in place thereafter, and each child issue keyed by its work item
      id is created once and updated in place and linked to its epic (the parent/epic
      link). Auth is the token_ref (a secret reference, fail closed when none resolves),
      the same keep-tokens edge as the other live writes.
  - id: AC2
    text: >
      The live writes are UPSERTS by stable key, honoring the same contract the
      FakeTracker documents and the epic mirror relies on: find the existing epic/child
      by its marker first and update it, else create it, so a re-run NEVER forks a second
      epic or a duplicate child. A write to a tracker object that cannot be resolved
      still fails loud rather than silently no-op.
  - id: AC3
    text: >
      With this in place the live edge is complete: the WARP-1005 mirror runner, driven
      over a real Jira, can project a plan's work graph onto a real epic and its child
      issues (mirror_plan_events), in addition to the spec status/links/reassign already
      wired. This live path remains a REFERENCE implementation wired per repo to a live
      instance and is NOT run in the gate (the FakeTracker path is what the gate runs),
      matching the honesty of the other live adapters.
  - id: AC4
    text: >
      The FakeTracker epic/child upsert semantics (one epic per plan id, one child per
      work item, idempotent re-run) that the gate already exercises still hold, and the
      capability manifest is updated so the JiraCloud adapter no longer claims epic/child
      creation is deferred. Teeth: the offline epic-mirror conformance (a plan builds its
      epic + children, a replay forks nothing) stays green and non-tautological.
  - id: AC5
    text: >
      capabilities.yaml is updated honestly (the JiraCloud adapter now wires epic/child
      as reference; the offline epic-mirror logic stays mechanical) in both byte-identical
      copies; every edited ENGINE_GLOBS file is re-synced byte-identical across
      engine and all seven packs (template-sync and pack-drift pass). The full
      gate is GREEN, RULE #1 is clean, no protected path is touched, and the change lands
      in the canonical two-commit shape.
required_evidence: [operational]
rollback: >
  Revert the commit. The epic/child live writes are reference (never gate-run) and the
  offline mirror is unchanged, so removing this returns the JiraCloud adapter to raising
  "later increment" for epic/child, with no migration and nothing to unwind on any
  instance.
---

## Intent

This finishes the live tracker edge so a requirements document can become a whole
plan of epics and child tickets on a real Jira (the last piece before the
document-to-plan generator in WARP-1007). The offline epic mirror (PLAN-0006) already
projects a plan onto an epic and children against the fake tracker; here the live
JiraCloud adapter learns to create and upsert those issues for real.

## Context

- Complete .veldo/tracker_intake.py JiraCloudAdapter._create_or_update_epic and
  _create_or_update_child (they currently raise, now naming WARP-1006). Model them on
  the FakeTracker upsert semantics in .veldo/tracker_adapter.py (keyed by plan id / work
  item id; find-then-update else create; never fork a second object).
- The epic mirror that drives them, mirror_plan_events in .veldo/tracker_mirror.py, is
  already shipped and gate-tested against the FakeTracker; this change only makes its
  live target real. The WARP-1005 runner already drives mirror_plan_events.
- Jira REST: create an Epic and Story/Task issues, set the epic link / parent, and use a
  stable marker (a veldo key on a field or label) to find an existing issue for the
  upsert. Auth by token_ref, fail closed. Live only, reference, not gate-run.
- capabilities.yaml must stop claiming epic/child is deferred once it is wired.

## Out of scope

- No live Jira in the gate; the FakeTracker drives every assertion. No change to the
  runner, the bridge, the promote gate, or the reassign/links.
- The document-to-plan generator is WARP-1007.

## Notes

- Honor the upsert contract exactly: a re-run must update in place and never fork. Fail
  loud on an unresolvable object. Fail closed on a missing token.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Today is 2026-07-21; regenerating specs/index.md restamps its date header,
  which keeps the generated check green.
