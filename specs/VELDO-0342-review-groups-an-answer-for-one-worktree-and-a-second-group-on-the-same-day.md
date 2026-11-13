---
schema: veldo.spec/v1
id: VELDO-0342
title: "Review groups: an answer for one worktree, and a second group on the same day"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0340]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "scripts/suites/*_veldo_0342_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0342-review-groups-an-answer-for-one-worktree-and-a-second-group-on-the-same-day.md"
  - "specs/index.md"
  - "proof/VELDO-0342/**"
behavior_bearing: true
observability:
  logs: >
    The group record holds each member's index and answer, and each request raised for the members left.
  error_taxonomy: >
    request_closed for an answer to a settled request. When the picks do not fit one message part, the
    request offers those that fit and its text names the members without one.
acceptance_criteria:
  - id: AC1
    text: >
      A group's request offers the three group picks and, for each member, the three member picks with its
      index. In a group of three the answer accept discard w2 discards only member 2 and settles the
      request, and the Ledger raises a new request for members 1 and 3 on the same group record; an answer
      to the settled request is refused as request_closed
    falsified_by: >
      Apply a member pick to the whole group; the row finds member 1 discarded and fails
  - id: AC2
    text: >
      When the group picks and the member picks of every member do not fit one message part, the request
      offers the group picks and the member picks of the lowest indexes that fit, and its text names the
      members without a pick; after a member pick the next request offers picks to the members after them
    falsified_by: >
      Offer every member pick whatever the size; the presenter refuses to render and the row that waits
      for the presentation fails
  - id: AC3
    text: >
      A scope has at most one open group per day: while one is open a deferral joins it. After the day's
      group is closed by an answer, a deferral the same day opens a new group with the next sequence
      number and its own request
    falsified_by: >
      Reuse the day key; the row's command is refused as a duplicate entity and the worktree has no
      request
required_evidence: [unit, integration]
rollback: >
  Revert the change. A group's request offers the three group picks only, and a worktree deferred after
  the day's group was answered has no group to join.
---

## Intent

The owner can answer for one worktree of a review group and leave the rest open. A member pick settles the
request, and the Ledger raises a new one for the members left. After a day's group is closed by an answer,
a deferral the same day opens a new group with the next sequence number.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (review worktrees, items 2, 4 and
6), 4.9 (review group record) and 13 (the decision on one answer for a group with per-worktree
exceptions). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are
copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (the review group record), Signal. Depends on 0340.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
