---
schema: veldo.spec/v1
id: WARP-0606
title: Plan-creates-structure epic mirror - project a plan's work DAG onto a tracker epic and children
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W6
plan_revision: 1
depends_on: [WARP-0605]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: Planning-layer events (plan.created, plan.approved, plan.revised, work.pulled) drive a
      one-way projection of a plan's structure onto its tracker EPIC and CHILD issues. The epic is
      upserted keyed by the plan id (one plan to one epic, never forked) with the plan's target repo
      recorded on it; each work item in the plan's work DAG becomes a child issue keyed by the work
      item (one work item to one child), so the whole structure exists even for not-yet-started
      items. It writes only epic and child status/fields, never a plan or spec definition, and never
      mutates its input plan index - the repository stays the single source of truth.
  - id: AC2
    text: Per-repo routing is enforced on the epic - the plan's tracker_repo must resolve to a known
      tracker via the reused WARP-0601 resolver (tracker_for_repo) before anything is written, and a
      plan with no tracker_repo, no config, or an unroutable repo is SKIPPED by name in the result,
      not mirrored. The epic records the routing target (a real adapter maps it onto the config's
      routing mechanism when writing the live tracker).
  - id: AC3
    text: The mirror reflects the burn-down. The epic's status is a rollup mapped through the per-org
      status_map (shipped once every work item's spec is shipped, otherwise open/ready); each child's
      status is its work item's current spec status mapped through the SAME status_map (shipped,
      blocked, ready). Transitions stay inside the mapped set (NG4) - an unmapped epic status is a
      keyed comment, never an invented transition, and an early-lifecycle spec (draft/unstarted)
      leaves its child status untouched rather than guessing.
  - id: AC4
    text: The mirror is a RECONCILER (like update_index.py and the spec mirror) - any planning event
      for a plan rebuilds the epic and children from the plan's CURRENT definition, so it is
      idempotent under at-least-once delivery with no processed-offset ledger and no second store -
      replaying the same events, or the same event twice, records no duplicate epic or child
      transition and leaves the tracker state byte-identical - and it reuses the WARP-0603 seam
      (create_or_update_epic, create_or_update_child, set_status) with no reimplementation.
  - id: AC5
    text: A selftest drives the epic mirror over the deterministic FakeTracker offline (no network) -
      a plan event creates the epic (keyed by plan id, routing target recorded) and one child per
      work item, sets each child and the epic to the mapped burn-down status, an all-shipped plan
      makes the epic shipped, a full replay records no new transition and leaves state identical, an
      unroutable plan is skipped by name, and the plan index is never mutated (the one-way guard) -
      and it is non-tautological (removing the events leaves the tracker empty; wiring them builds
      the structure; neutering the reconcile turns the assertions red).
required_evidence: [unit]
rollback: git revert; additive - new functions in .veldo/tracker_mirror.py (mirror_plan_events,
  build_plan_index, helpers), one capability entry (both capabilities.yaml copies), a selftest
  block, and this spec; no protected path; pure stdlib, read-only over the repo, no network.
---

## Intent

O3 wants the tracker to reflect live status with nobody updating it by hand, and PLAN-0006's
founder-approved shape is "the plan creates the structure": one plan stands up its epic and the
child issues for its work items, mirroring the burn-down. This is that projection for the planning
layer, the sibling of the spec mirror (WARP-0605): the spec mirror keeps one spec's child live from
its lifecycle events; this builds and maintains the whole epic-and-children structure from the
plan's work DAG. Both are one-way and derived; neither lets the tracker define work.

## Context

W6 of PLAN-0006, depends on the spec mirror (W5). It lives in the same module (.veldo/tracker_mirror.py)
because it is the same feature (F3, the one-way mirror) at a different granularity, reusing the spec
mirror's status_map resolution, routing reuse, reconciler shape, and NG4 discipline - no parallel
machinery (C3). It consumes the planning-layer events the loop already emits (plan.created,
plan.approved, plan.revised, work.pulled) and drives the WARP-0603 seam's epic/child upserts. Jira
is not here: the FakeTracker is what runs in the gate, so the projection is proven offline.

## Notes

The epic and each child are UPSERTS keyed by stable identities (the plan id for the epic, the work
item for a child), so any planning event simply reconciles the structure to the plan's current
definition and a re-run never forks a second epic or child - the same reconcile-not-replay shape as
update_index.py, which is why replay is idempotent with no offset ledger. The epic status is a
coarse rollup (open until every work item ships, then shipped); the children carry the per-item
burn-down (each child's status is its spec's current status through the same status_map). Child
status is set only when the spec status maps to a VELDO status in the status_map; an early-lifecycle
spec (draft/unstarted) leaves the child status alone rather than inventing one.

The epic records its routing target in the vendor-neutral seam's fields (veldo_repo = the plan's
tracker_repo); a real adapter (WARP-0604 onward) translates that onto the config's actual routing
mechanism (a label, a component, or a custom field) when it writes the live tracker. VELDO always
knows its own epic's repo (the plan declares it), so the resolver is reused here only to ENFORCE
that the declared repo is known before writing - a plan that cannot be routed is skipped, not guessed.

A child's status is co-owned with the spec mirror (WARP-0605), by design: this epic mirror is a
RECONCILE-TO-TRUTH pass (each child's status is its spec's front-matter status, the source of truth,
so the burn-down is correct regardless of event history), and the spec mirror is a LIVE OVERLAY (it
tracks a spec's in-flight lifecycle from the event stream). Both address the identical child object
(keyed by plan + work item) so STRUCTURE never forks, and both project the same underlying spec
status, so they CONVERGE at every persistent state (ready, blocked, shipped). The only divergence is
a transient event-only status the front matter has no equivalent for - in_review (from
verdict.recorded) and merged - which the overlay may show briefly before the next reconcile settles
it. A stock status_map leaves in_review/merged unmapped (the overlay annotates rather than
transitions), so there is no visible flap; an org that maps them accepts a brief, self-healing
transient. The convergence guarantee is therefore precise: structure never forks, and status agrees
at every persistent state, with event-only statuses owned by the live overlay between reconciles.
