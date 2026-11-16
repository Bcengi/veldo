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
- 2026-11-16: BLOCKER, recorded by the builder before any code was written. Status stays ready; nothing
  is built. Read on the base 73c7b832 (VELDO-0340 with its fix round 1). AC1 and AC2 need a group's
  request to offer member picks and to say in its text which members have none, and three files outside
  this ticket's footprint refuse or pin that:
  - engine/.veldo/control_request_settlement.py (and its synced copy). space_presentation returns the
    choices as the three group picks alone (:244, :257) and a fixed brief, and request_problem (:275-296)
    binds every open and revise of a space request, and every framing by the presenter, to exactly that
    brief and those choices. So no request with a member pick, and none whose text names the members
    without a pick, can be opened, revised or presented by the Ledger and Signal alone. The brief also
    numbers the worktrees by their place in the list (:256), not by the member's index: after member 2
    leaves, members 1 and 3 would be shown as Worktree 1 and Worktree 2 beside the picks w1 and w3,
    which is terms that differ from what is acted on.
  - engine/.veldo/control_space_remove.py (and its synced copy). _r_disposition refuses unless the
    settled choice equals accept and the action (:968), so the settled answer accept discard w2 removes
    nothing. The Ledger could hand the remover an effect with the index cut off, but that is a rewritten
    settled answer, a workaround, and it was not built.
  - scripts/suites/150_veldo_0340_review_groups.py. Row terms/group (:644) asserts that a group's
    choices are exactly the three group picks; it goes red the moment member picks are offered.
  Needed from the lead: the footprint widened by those three files and the two synced copies. The terms
  would carry each member's index and the indexes offered a pick, signed, so that space_presentation
  derives the member picks and the line naming the members without one from the signed terms alone;
  every single-worktree behavior of VELDO-0327 and VELDO-0318 stays as it is.
  engine/.veldo/control_service.py reads the settled choice at :1729 (anything but accept keep is
  authorized); the Ledger's authorize_disposition can refuse an accept keep w2 inside the footprint, so
  that file may not need to change, to be confirmed in the build.
  Not blocked: AC3. VELDO-0340 already built the sequence number (its History, "A join is taken by the
  day's first group that is open"); what is left for it here is the rows and the falsifier, and the
  close by the last member pick, which waits on AC1.
  The VELDO-0340 review's point (b), a group whose request is canceled or declined: no criterion of this
  ticket names it, and the design (4.9, section 7 item 4) gives a group two closures only, a group pick
  applied and the last member leaving by a member pick. So it is not built here without a lead decision
  that adds a criterion; the members stay deferred on disk and no work is lost meanwhile.
