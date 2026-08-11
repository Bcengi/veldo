---
schema: veldo.spec/v1
id: WARP-0605
title: Event-driven one-way spec mirror - project spec lifecycle onto tracker status and comments
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0006
work: W5
plan_revision: 1
depends_on: [WARP-0602, WARP-0603]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A one-way projection consumes the spec lifecycle event stream (spec.ready, spec.blocked,
      verdict.recorded, spec.shipped, merge.completed) and writes ONLY tracker status and comments
      onto the spec's child issue - it has no code path that mutates a spec or plan definition, so
      the repository stays the single source of truth. It is driven by events, never by polling the
      tracker, and it reuses the existing event vocabulary and reader shape (no new stream).
  - id: AC2
    text: Each VELDO status maps onto the tracker project's own status via a per-org status_map in
      the config (a global map, optionally overridden per repo), and the mirror transitions the
      child ONLY within that mapped set. A VELDO status with no mapping is never invented as a
      transition (NG4); it is recorded as a keyed status comment so a human sees it and the child's
      tracker status is left untouched. An absent status_map means no transitions, comments only.
  - id: AC3
    text: The mirror is idempotent under at-least-once delivery - it reconciles the child to the
      desired state (the latest mapped event's status) and keys every comment, so replaying the same
      stream, or the same event twice, produces NO duplicate transition and NO duplicate comment and
      leaves the tracker state byte-identical; run over a growing stream it walks the child through
      its mapped statuses as events land. No processed-offset ledger and no second store, mirroring
      the update_index.py re-projection precedent.
  - id: AC4
    text: The mirror reuses WARP-0601 (tracker_for_repo confirms a spec's declared tracker_repo maps
      to a known tracker before any write) and the WARP-0603 seam (create_or_update_child, set_status,
      comment) - no reimplementation of routing or the adapter. A spec not wired for mirroring (no
      tracker_repo, no config, an unroutable repo, or no plan to place a child under) is SKIPPED by
      name in the result, not errored; a malformed status_map fails closed by name (MirrorError).
  - id: AC5
    text: A selftest drives the mirror over the deterministic FakeTracker offline (no network) -
      a growing stream moves the child ready to shipped through the mapped statuses and posts the
      closing comment; a full replay plus a duplicated event id records no new transition or comment
      and leaves state identical; an unmapped status is annotated not transitioned; a spec with no
      tracker_repo is skipped; the spec index is never mutated (the one-way guard) - and it is
      non-tautological (removing the events leaves the child untouched; wiring them moves it).
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/tracker_mirror.py, one capability entry (both
  capabilities.yaml copies), a status_map example added to the template trackers.json, a selftest
  block, and this spec; no protected path; pure stdlib, read-only over the repo, no network.
---

## Intent

The tracker must reflect live status with nobody updating it by hand (O3). This is the mirror for a
single spec: it turns the spec's lifecycle events into a tracker status and a closing comment on the
spec's child issue, one-directionally. The repository defines the work; the tracker only reflects it.
There is deliberately no path from the tracker back into a spec or plan - a mirror that could write a
definition would make the tracker a second source of truth, which C1 forbids.

## Context

W5 of PLAN-0006, on the frontier with W4 once routing (W2) and the adapter seam (W3) exist. It is a
new CONSUMER of the event stream .veldo/events.py already emits (C3: reuse, do not reinvent), reusing
the WARP-0601 resolver for which tracker serves a repo and the WARP-0603 seam for how a tracker is
written. Jira is not here: the mirror drives the vendor-neutral seam, and the FakeTracker is what
runs in the gate, so the whole projection is proven offline. The plan/epic mirror (W6) extends this
to the planning layer and depends on it.

## Notes

The mirror is a RECONCILER, the same shape as update_index.py: every run recomputes the desired
tracker state from the events and applies it idempotently, rather than tracking which events it has
already applied. That is why replay is safe without a processed-offset ledger (which would be the
"second store" C2/NG2 warn against) - set_status is a no-op when unchanged and comments are keyed.
Running over a growing stream (the real cadence, as each event lands) walks the child through its
statuses; running over the whole stream twice is a no-op.

A spec's child is addressed by the seam's key: the epic is the spec's plan id, the child key is the
spec's work item (spec id as the fallback). The mirror ENSURES the child exists with the seam's
idempotent upsert, so it is self-sufficient and does not require the epic/child mirror (W6) to have
run first; both key the same child deterministically and converge. Shipping the tracker integration
modules to adopting repos via engine/.veldo is a release/W8 concern - like tracker_adapter.py
(WARP-0603), tracker_mirror.py is not a validate.py/policy_check.py load dependency, so it needs no
template twin to keep an adopting repo's gate green, and check_template_sync is unchanged.

The status_map lives in .veldo/trackers.json alongside routing; the mirror validates its own section
(known VELDO status keys, non-empty status names) at use, which is not a second copy of the routing
validator (that stays in tracker.py) but validation of a distinct mirror-owned section. The template
trackers.json ships an example status_map so an adopting org has a starting point.
