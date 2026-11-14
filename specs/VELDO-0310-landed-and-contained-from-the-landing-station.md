---
schema: veldo.spec/v1
id: VELDO-0310
title: "Landed and contained, from the landing station"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_landing.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_landing_station.py"
  - "scripts/suites/*_veldo_0310_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0310-landed-and-contained-from-the-landing-station.md"
  - "specs/index.md"
  - "proof/VELDO-0310/**"
behavior_bearing: true
observability:
  logs: >
    Each landing records the items it removed and each branch it marked contained, joined to the unit's
    completion receipt.
  error_taxonomy: >
    A worktree git refuses to remove is deferred as space_deferred:remove_refused, and one with unique
    work as space_deferred:unique_work. A branch is never deleted.
acceptance_criteria:
  - id: AC1
    text: >
      Landed is sent after the completion receipt is recorded and never before
    falsified_by: >
      Send it when the landing starts; the row that fails the landing after that finds the worktree gone
      and fails
  - id: AC2
    text: >
      At landed the unit's worktree is removed after its build output, its branch is kept and marked
      contained, and its image tags go
    falsified_by: >
      Remove the branch with the worktree; the row finds no branch and fails
  - id: AC3
    text: >
      Every other recorded branch of the project that has moved past its start commit and that the new
      trunk tip contains is marked contained and its worktree removed; a branch still at its start commit
      is left
    falsified_by: >
      Drop the start commit test; the row's fresh worktree on a new branch is removed and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A landing removes nothing, and the worktrees of landed branches stay until another
  event ends them.
---

## Intent

When a unit lands, its worktree has done its work. After the completion receipt is recorded the landing
station sends landed: the unit's build output goes, then its worktree, its image tags go, and its branch
is kept and marked contained. Every other recorded branch the new trunk tip contains is treated the same,
unless it has not moved past its start commit.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (landed and contained, and the
start commit rule) and 8.3 (a landing by the landing station). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Landing.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  the criteria do not say it:
  - Where it is. In control_landing.py: Landing.landed, Landing.receipt and the two readers
    space_branches and space_reach. In control_landing_station.py: LandStation.landed and its call in
    land, for a land dispatch whose outcome is landed and for no other. Nothing in either deletes
    anything and no branch is deleted: every removal is Signal's, after the safety rules and the keep
    step, by the removers. The station is given its ledger as `space`, the mapping the receiver and
    the runner are given. Nothing in the engine builds `space` yet (control_service.py is outside this
    footprint), so an installation lands as before until that wiring lands. FOR THE LEAD.
  - When it is sent. After the land's answer is classified landed, which needs the receipt, and before
    the land dispatch's own record is ended, so that record ends with the space step under `space`,
    beside the receipt. The landing reads the receipt of exactly that unit and dispatch back from the
    store itself and sends nothing without it. It also reads the trunk at that moment (the local ref,
    or the remote's answer for a landing that pushes) and sends nothing unless the trunk is at the
    landing's candidate or contains it: a landing undone since is not a landing. For a landing that
    pushes, a trunk another factory has moved on to a commit the publication clone does not hold yet
    cannot be read as containing the candidate, and nothing is sent at that landing; the worktrees
    then end at a later event. FOR THE LEAD.
  - The ledger's signal names an owner, not an item. So landed is sent for the unit's project and
    ticket, and contained once for each owner of a contained branch, and before each the landing
    reads what the event would reach. Landed is sent only when every branch, and the branch of every
    worktree, of that ticket is in the landing: its tip in the new trunk tip, or the source commit or
    an ancestor of it. A unit whose branch was rebased or built on after the evidence commit is sent
    nothing (not_landed) and its worktree, build output and image tags stay until a later event.
    Contained is sent only when the owner's event would reach nothing that is not contained; an
    owner with a contained branch and one that is not is sent nothing, and the contained branch is
    named as left (not_alone). So design section 5's case of a worktree switched from a contained
    branch X to a branch Y under one ticket leaves X unmarked here, where the design marks X and
    leaves the worktree: that needs a signal that names items, which is the ledger's. FOR THE LEAD.
  - Moved past its start commit is read as: a start commit is recorded, the tip is not that commit,
    and the start commit is an ancestor of the tip. A branch put back behind its start commit is not
    contained. A worktree on a contained branch must itself have moved past its own start commit
    (the one written when it was switched to that branch), and a detached worktree is never contained.
  - Marked contained is the branch item's outcome kept with the action mark_contained, which Signal
    writes through the ledger; git is not called. The ledger's item holds no field for the mark
    (control_space.py is outside this footprint), so the landing's own record is where a branch is
    named marked, with its ref, its repository and the tip that was tested. A branch already kept,
    with nothing else for the event to reach, is not sent the event again at later landings.
  - A ref that moves after the check. The rules read every fact at the moment of the removal, so a
    worktree whose branch gained a commit is deferred by rule 5. After each event the landing reads
    the tip of every branch it counted again, and one that moved is named moved and not marked.
  - Rule 5 is given the landing's source commit and its new trunk tip, both read from the receipt,
    beside whatever the installation wired in as landed.
  - A landing that pushes. Every branch is read in the repository it is recorded in. After a landing
    that pushes, that repository does not hold the new trunk tip until it fetches, so git cannot say
    there that the tip contains a branch: such a branch is counted unread, never contained, and
    nothing is sent for it at that landing. The unit's own branch is still read as landed when its
    tip is the source commit or an ancestor of it. The other branches end when the fetch moves the
    trunk there, which is the ref hook's event (VELDO-0311). The suite's landings land locally
    (VELDO-0235), where the project's repository holds the new tip; the pushing path's read of the
    remote is not driven by a row. FOR THE LEAD.
