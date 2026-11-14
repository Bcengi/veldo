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
- 2026-11-14: fix round, after the review of this ticket (verdict FIX, five findings) and the lead's
  decisions on them. No acceptance criterion changed and the footprint is as it was. What changed, and
  what it replaces in the entry above:
  - Finding 1, AC3 at the remote destination, which is the default. The entry above said a repository
    does not hold the new trunk tip after a landing to the remote, and that its branches are unread
    until a fetch. Now the landing brings the objects of the new trunk tip from its own clone into
    every repository a live branch of the project is recorded in and that does not hold them, before
    the reads: pack-objects in the clone, unpack-objects in the repository, the way VELDO-0235 copies
    a candidate. No ref is written, nothing is fetched and nothing is removed, and the pack leaves out
    what the repository's own refs already hold. A repository the objects could not be brought into
    (git cannot read it, it shares no commit with the clone, the transfer failed) is read as it is:
    its branches are unread, never contained. It is done after the trunk read, so a landing that was
    undone brings nothing. The record names each repository under `brought`.
  - What the rows found, FOR THE LEAD. In the suite the project's own repository already holds the
    candidate when the step begins, also at the remote destination: the lander's discard of its
    candidate workspace keeps the workspace's commits on a kept ref in the project's repository
    (VELDO-0303), and the candidate is one of them. So AC3 already held for a branch of the project's
    repository at the remote destination, and the review's finding (read from the code, not run) does
    not reproduce there. The transfer is what makes it hold where that kept ref is not: a branch
    recorded in another repository (an agent repository), and a workspace whose discard kept nothing.
    The row drives it with a branch recorded in a second repository that holds nothing of the
    landing.
  - The remote side of the trunk read is driven by a row now: the station's own step runs with the
    bare origin's trunk put back just before it, the remote's own answer is read, and nothing is sent.
  - Finding 2, rule 5 reads the trunk itself. The entry above said rule 5 is given the source commit
    and the new trunk tip. It is given the source commit only, beside whatever the installation wired
    in as landed. The trunk is rule 5's own read at each removal (design section 7: no fact is carried
    over), so a trunk put back between the landing's check and a removal holds nothing: a worktree
    whose commit only the old candidate held is deferred as unique_work.
  - Finding 3, a known gap, not closed here. The landing judges a snapshot of the ledger's items
    (space_reach) and the ledger matches again when the event is sent. An item declared for the same
    owner in between, for example a fresh worktree on a branch at its start commit, is reached by the
    event though the check never judged it, and a clean worktree at the trunk passes rule 5: it is
    removed, against the start commit rule. No work is lost: rule 5 holds any file that is in no
    commit, the keep step writes the worktree's commits to kept refs before the remove, and no branch
    is deleted. Closing it needs a signal that names the items it is sent for (or expected versions),
    which is the ledger's: the item-naming signal follow-up, the same one that lets contained be sent
    for one branch of an owner and leave the others (note A of the review, and design section 5's
    branch-switch case above). FOR THE LEAD.
  - Finding 4, three paths the entry above claimed and no row drove: a squash landing (the branch tip
    is the source commit and not in the trunk), a unit with one landed branch and one the landing
    does not hold (landed is not sent, and the record names that branch), and a detached worktree at
    landed (it counts as landed and is removed by the rules and the tool, after the keep step). Each
    has its row and a falsifier. The lander makes no squash, so that row's receipt is a stand-in.
  - Finding 5, the space step no longer runs inside the land dispatch's running window. The entry
    above said landed is sent before the land dispatch's own record is ended. Now the dispatch's
    record is ended first, landed, and the space step has a record of its own (kind
    land_dispatch_space, id land-space:<dispatch>), written by the station's one transition: opened
    running, which the store refuses unless the dispatch's record is ended landed with its receipt,
    and ended done with what was sent, or failed with what was raised. The dispatch's record holds no
    `space` field any more. A step that raises, or a process that dies or hangs in it, leaves the
    landing ended and landed; the stop is the space record's. A failed or interrupted step is not
    retried by the station: the worktrees end at a later event or by reconcile (VELDO-0315).
  - The ledger's state kept is one the signal reaches (the review's other note): when the owner's Keep
    (design 0.4) is built on that state, landed and contained will make an owner-kept item due. That
    is the ledger ticket's to settle, and this change inherits it.
  - Rows added to suite 147, each with a registered falsifier applied once to the copy the suite loads
    and seen red: f1/remote-trunk-put-back (space310-remote-trunk-not-read, on the remote side of
    _trunk_holds), f1/remote-unit-landed and f1/remote-branch-contained
    (space310-candidate-not-brought, and space310-transfer-writes-a-ref for the rule that the transfer
    writes no ref), f2/trunk-read-at-the-attempt (space310-candidate-given-to-rule-5),
    f4/squash-landing (space310-source-commit-not-counted), f4/one-landed-one-unlanded
    (space310-first-branch-judged-alone), f4/detached-worktree-at-landed
    (space310-detached-refused-at-landed) and f5/space-step-failed
    (space310-space-step-inside-the-running-window). The ten falsifiers of the build keep their
    anchors and were applied again: all red.
- 2026-11-14: second fix round, after the re-review of the fix round (verdict FIX; its notes 3 and 4
  are this ticket's). No acceptance criterion changed and no engine code changed.
  - A space step that hangs, or a process that dies before the step's record is opened, leaves no
    readable record (the re-review's note 4). Three cases, as the code stands:
    a step that hangs, or whose process dies inside it, leaves its record running for good, and the
    station never runs it again (the open is refused, the record exists);
    a process that dies after the dispatch's record is ended landed and before the step's record is
    opened leaves no space record at all;
    and nothing reads a space record that is running or failed: the station's status lists
    dispatch records only.
    So nothing in this ticket tells an owner, or a later run, that a landed dispatch's space step
    did not run to its end. No work is lost by it: the landing is a fact with its receipt, and the
    unit's worktree, its branch and every other branch stay as they were, on disk and in the
    ledger. It costs space. Where it is picked up: VELDO-0315 reconcile. A landed dispatch whose
    space record is missing, running or failed is reconcile's to find, and what it then ends goes
    through Signal, after the rules and the keep step, as every removal does. Until then the
    worktrees wait for a later event, as the entry above says of a failed step.
    Not built here, and left to the lead: the station's status naming running and failed space
    records, the space record opened in the same transition that ends the dispatch landed, and a
    stated deadline for a hung step.
  - The transfer into the project's own repository has a row (the re-review's note 3 and its
    case 3). Every row of the fix round had that repository answer held, through the kept ref the
    lander's workspace discard writes there, so the copied path was driven only for the agent
    repository. Row f1/project-repository-brought: a unit lands at the remote with the lander's
    workspace discard disabled (it is asked and does nothing, and the workspace stays on disk); when
    the step begins the project's repository does not hold the candidate, by a ref or by an
    alternate; the step copies the candidate's objects into it and the record names it copied; the
    refs of that repository at the first event are exactly those before, nothing is fetched, and
    after the step no ref of it holds the candidate; landed is sent for the unit and its worktree
    is removed after the keep step; and contained still holds for another branch of that
    repository, its worktree removed after the keep step and the branch kept and marked. Its
    falsifier, registered and applied once to the copy the suite loads, seen red on that row alone:
    space310-project-repository-left-to-the-discard (a repository that has kept refs is not brought
    to). space310-candidate-not-brought and space310-transfer-writes-a-ref were applied again and
    are red on this row and on f1/remote-branch-contained. Suite 147 is 30 rows, 56 passed.
