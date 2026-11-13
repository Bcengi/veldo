---
schema: veldo.spec/v1
id: VELDO-0340
title: "Unique work in review worktrees: one request per day"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0318, VELDO-0327, VELDO-0336]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0340_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0340-unique-work-in-review-worktrees-one-request-per-day.md"
  - "specs/index.md"
  - "proof/VELDO-0340/**"
behavior_bearing: true
observability:
  logs: >
    One review group record per scope, day and sequence number, with its members, each member's file list,
    and the current request with its version.
  error_taxonomy: >
    An answer bound to an earlier presentation settles nothing. On a group's Discard a member whose file
    list changed is deferred again.
acceptance_criteria:
  - id: AC1
    text: >
      Two review worktrees with tracked edits deferred on one day raise one request; a third on the next
      day raises a second, and the first day's request is unchanged
    falsified_by: >
      Raise one request per worktree; the row counts two on day 1 and fails
  - id: AC2
    text: >
      A later deferral of the same day publishes a new version of the day's request, and an answer bound
      to the earlier presentation settles nothing. The clock opens and sends nothing: with the fixture
      clock moved a day and no deferral there is no new request
    falsified_by: >
      Add the worktree without a new version; the row's answer to the old presentation settles the group,
      the worktree the owner never saw included, and the row fails
  - id: AC3
    text: >
      A group pick applies to every member still in the group and closes the group. Save commits each
      worktree's changes on a kept branch named space-saved and the review run's label and removes it
      without force; Keep sets each to kept; Discard removes each member whose file list equals the list
      shown and defers a changed one again, into a new group (VELDO-0342 AC3)
    falsified_by: >
      Skip the comparison per worktree; the row adds a file to one member after the request was shown,
      loses it and fails
  - id: AC4
    text: >
      Only a review run's worktree is treated this way: a detached worktree owned by a run of another
      station keeps its untracked file at run finished and raises a request of its own
    falsified_by: >
      Treat every run-owned worktree as a review worktree; the builder's untracked file is deleted and the
      row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A review worktree with tracked edits raises a request of its own, as any worktree a
  run owns does.
---

## Intent

Reviews run many times a day, and a request for every review worktree would bury the owner. Review
worktrees deferred for tracked edits share one request per scope and day. The day is a key of the deferral
event; the clock opens and sends nothing. A group pick applies to every member still in the group.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (review worktrees, items 1 to 6)
and 4.9 (review group record). Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (the review group record), Signal, Removers (discard). Depends on 0318, 0327 and 0336.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
