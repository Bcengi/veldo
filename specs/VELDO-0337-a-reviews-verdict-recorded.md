---
schema: veldo.spec/v1
id: VELDO-0337
title: "A review's verdict recorded"
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
  - "engine/.veldo/control_launch_work.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/control_launch_work.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "docs/design/VELDO-0295-design.md"
  - "scripts/suites/*_veldo_0337_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0337-a-reviews-verdict-recorded.md"
  - "specs/index.md"
  - "proof/VELDO-0337/**"
behavior_bearing: true
observability:
  logs: >
    The event follows the review's verdict record, and each outcome follows the event.
  error_taxonomy: >
    None new. A review with no verdict in the store sends no verdict recorded.
acceptance_criteria:
  - id: AC1
    text: >
      A review's receiver sends verdict recorded when the review's verdict is recorded, and never before
    falsified_by: >
      Send it at the review's start; the row finds the review's build folder gone before the verdict and
      fails
  - id: AC2
    text: >
      At a review's verdict recorded its build output and scratch are removed and its evidence folder
      stays, with the caches the project declares dropped
    falsified_by: >
      Remove the evidence folder with the scratch; the row finds no evidence and fails
  - id: AC3
    text: >
      A review that ends with no verdict sends run finished and no verdict recorded
    falsified_by: >
      Send verdict recorded at every end of a review; the row that kills the review finds a verdict
      recorded event with no verdict in the store and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A review's items end at run finished only.
---

## Intent

A review's build output and scratch go when its verdict is recorded, and its evidence stays. The review's
receiver sends verdict recorded at that moment and never before. A review that ends with no verdict sends
run finished only.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (verdict recorded) and 8.1 (a
build run through the factory). Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver (the review station).

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-15: fix round after the review (review-veldo-0337.md, verdict FIX), by three lead decisions. No
  acceptance criterion changed.
  Finding 1, lead decision: AC1 wins over the design's table. An item's own declared end events govern
  its removal. A review run's scratch folder and build root are declared at creation to end at verdict
  recorded and the events after it, without run finished (control_launch.space_ends, called by
  space_run_folders); run finished neither names nor matches them, and they go when the writer of the
  verdict sends verdict recorded. The design's section 5 carries the dated note. Footprint: the end
  events of an item are written by the ledger alone, from its kind, so the declaration needs the
  ledger: control_space.py and its synced copy are added (declare takes `ends`, some of the kind's own
  events, never another; an item is kept longer by it and never removed sooner), and the design
  document for the note. Neither is a protected path. The lead's fix brief names "fix the declaration"
  and does not name this file: the extension is recorded here for the lead to confirm.
  What the decision leaves as it was: the run directory of a review ends at run finished; the build
  output the census declares inside a review's worktree goes at run finished before its worktree, as
  the review worktree row has it (declared at the run's end, not at creation; held back, it would hold
  the worktree with no event of the run left to end it). Known effect: a review that ends with no
  verdict (AC3) sends run finished only, so its scratch folder and build root stay until a later event
  of theirs (landed or contained, ticket ended, project ended, worktree abandoned). No work is in them
  that is lost by staying; the cost is space.
  Finding 2: rows for the reviewer's survivors. ac2/second-attempt: a second review of a unit names
  only its own dispatch's items. ac2/error-after-commit: Signal raising after the commit is observed,
  Dispatcher._review_floor returns, the verdict stays stored and nothing is removed.
  ac2/ends-on-the-event: a worktree of the review present at the verdict is not named. Each survivor
  is a registered mutation of finding 337.
  Finding 3, lead decision: a verdict recorded lost between the commit and the send is recovered at
  start. FloorAuthority.reconcile_verdicts reads the committed verdicts and sends the event once for
  the items it has not reached; it reads no clock and polls nothing. Lead decision: the footprint may
  include the reconcile module VELDO-0315 built. It was not needed and is not touched: VELDO-0315's
  reconcile at start is not on this branch (no commit, suite or proof of it; control_space_reconcile.py
  holds the adoption rule of VELDO-0331 and VELDO-0307 only). The reconcile is therefore called where
  the floor is built, at the start of the worker's Runtime (control_launch_work.py), and VELDO-0315's
  reconcile can call the same function when it is built.

- 2026-11-15: lead decision, footprint extended to the recording path; the signal is emitted by the one writer of the verdict after its commit
  FloorAuthority.record_review is the emitter for both review callers. The
  receiver and the engine completion artifact emit no verdict event. This
  resolves the blocker recorded below without changing the three criteria.

- 2026-11-15: build blocked by the declared production footprint. Launch.wait
  reaps the receiver before Runtime.review validates and signs the review
  receipt. The verdict is recorded afterwards by control_launch_work.py or,
  for a supplied assignment, dispatch.py; both are outside this footprint.
  An engine completion artifact is not a stored review verdict. No production
  change or AC amendment made. The owner was asked to extend the footprint to
  the verdict-recording path and decide the emitter. Evidence and the read-only
  ordering reproduction are in proof/VELDO-0337/blocker.md and receiver_order.py.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
