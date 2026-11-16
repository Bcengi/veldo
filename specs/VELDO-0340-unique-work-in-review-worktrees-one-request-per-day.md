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
  - "engine/.veldo/control_request_settlement.py"
  - ".veldo/control_request_settlement.py"
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
      without force; Keep sets each to kept; Discard saves each member's uncommitted state in the snapshot
      store first, removes each member whose file list equals the list shown and defers a changed one
      again, into a new group (VELDO-0342 AC3)
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
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC3: a group's Discard saves each member's uncommitted state on a kept ref before it removes that
  member. The falsifier is unchanged.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC3: a group's Discard saves each member's
  uncommitted state in the snapshot store, where it said on a kept ref. The falsifier is unchanged.
- 2026-11-16: BLOCKER, recorded by the builder before any code was written. Status stays ready; nothing
  is built. A group's request must name every member with its file list (design 7, VELDO-0327 AC2), and
  the only path to a space disposition request refuses that outside this ticket's footprint. In
  engine/.veldo/control_request_settlement.py, space_presentation refuses terms whose worktrees list
  does not hold exactly one entry (read on the base d0e2461a: two entries give invalid_input, "space
  terms name one worktree"), the terms command requires the target to be a space_item equal to that one
  entry's item, and request_problem binds the request's brief and choices to space_presentation of the
  signed proposal at every open and revise. So no request for two worktrees can be signed, opened or
  settled, and AC1, AC2 and AC3 cannot be met by the Ledger, Signal and the Removers alone. The one
  way inside the footprint is to write a group as one worktree entry, with the group's identity as its
  item and the members' files joined in its list: the owner would then be shown one path for several
  worktrees and a restore command that names no item, which is terms that differ from what is acted
  on, so it was not built. Needed from the lead: the footprint widened by
  engine/.veldo/control_request_settlement.py and its synced copy (space_presentation for one or more
  worktrees, and a target kind for a review group), with the VELDO-0327 suite if a row of it holds the
  one-entry refusal. engine/.veldo/control_service.py does not need to change: its disposition task
  can reach a group through the members' own records.
- 2026-11-16: LEAD DECISION on the blocker above: the footprint widening is accepted. This ticket may
  change engine/.veldo/control_request_settlement.py and its synced copy so the space terms carry one
  or more worktrees and a group target kind, every member listed with its own path, files, commits
  and restore command, and the target naming the group and every member item; and the VELDO-0327
  suite where a row asserts the one-entry refusal. Every single-worktree behavior of VELDO-0327 and
  VELDO-0318 stays as it is. A group is never written as one worktree entry.
  engine/.veldo/control_service.py does not change. The two settlement files are added to the
  footprint above. The VELDO-0327 suite was not changed: terms without a group still name exactly
  one worktree, so no row of it asserted anything that moved.
- 2026-11-16: built. What the build decided where the design leaves room:
  - Terms. Space terms with a `group` (the review group record's identity) list one or more
    worktrees and are targeted as space_group, with `members` naming every item in the order
    listed. Terms without a group are what they were, one worktree targeted as space_item.
  - The record (design 4.9): space:group:<scope>:<day>:<sequence>, with the day, the sequence, the
    members (index, review run, file list, kept branch, the commit read, the whole entry shown),
    the current request with its version, and the state. Each member's own disposition holds its
    own entry alone and names the group, so Save and Discard compare each worktree with what was
    shown for that worktree, through the same remover checks as a single request.
  - The day is read once, as the deferral is recorded, through the Ledger's clock in the
    installation's time zone. Signal still imports nothing and names no clock. Nothing is opened,
    closed or sent when the clock moves.
  - A new version is a new terms record (terms are immutable) and a revision of the one request,
    then its framing. The settlement refuses an answer bound to the earlier presentation as
    stale_presentation, before and after the new version is presented.
  - A join is taken by the day's first group that is open and whose request no answer has ended.
    So a deferral after the answer, and before it is applied, opens the next sequence number. The
    sequence number is built here because AC3 defers a changed member "into a new group"; the
    rest of VELDO-0342 (member picks, the size rule) is not built.
  - A group pick is one write: every member still in the group (deferred, its requested
    disposition naming the group) that the settled terms list gets the pick, and the group closes.
    A member that joined after the presentation the owner answered was never shown: the pick does
    not reach it, and it joins a new group at its next publish. Save and Discard are authorized by
    the service's disposition task as for one worktree and carried per member by Signal; Keep is
    the owner's signed space_disposition packet naming any member with the group's request, as
    VELDO-0318 AC4 has it for one worktree.
  - The owner's Save and Discard of a review worktree do not run the review scratch remover: Save
    has committed the untracked files and Discard removes exactly what its snapshot holds.
  - Not built, and why: member picks and the one-message size rule (VELDO-0342); a client that
    signs the owner's Keep packet (none exists in the repository, as VELDO-0318 found); a group
    whose request was canceled or declined keeps its members without a live request until their
    next deferral, which no criterion here names.
