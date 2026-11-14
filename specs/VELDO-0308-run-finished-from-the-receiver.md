---
schema: veldo.spec/v1
id: VELDO-0308
title: "Run finished, from the receiver"
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
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_retirement.py"
  - ".veldo/control_retirement.py"
  - "scripts/suites/*_veldo_0308_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0308-run-finished-from-the-receiver.md"
  - "specs/index.md"
  - "proof/VELDO-0308/**"
behavior_bearing: true
observability:
  logs: >
    The receiver's end records the census, each removal outcome and the released hold, in that order.
  error_taxonomy: >
    A removal refused at run finished is a deferral. Run finished is not sent while the dispatch's
    containment group still has a process.
acceptance_criteria:
  - id: AC1
    text: >
      Run finished is sent only after the dispatch is conclusive and its group is empty, and the removal
      is complete before the receiver exits
    falsified_by: >
      Send it when the worker's own process exits; the row has a surviving child that keeps a file open
      under the scratch root (not its working directory), the scratch is judged while the child lives, and
      the row fails
  - id: AC2
    text: >
      At the run's end the receiver runs the census, then Signal, then releases the hold, in that order,
      and all three are written before it exits
    falsified_by: >
      Exit after Signal without releasing the hold; the row's waiting unit, which needs the released hold
      as well as the freed bytes, is still waiting after the receiver has gone, and the row fails
  - id: AC3
    text: >
      When a pending retirement's obligation completes and the retirement is carried out, the dispatch's
      deferred items are retried in that call; a sweep that finds the obligation unchanged retries nothing
    falsified_by: >
      Retry on every sweep call; the row counts retries over three sweeps with an unchanged obligation,
      finds three and fails
  - id: AC4
    text: >
      The clone obligation of a retirement closes when the clone's teardown has been handed to the
      ledger: when the teardown answers retired, and when it is refused as space_deferred, for the
      ledger then tracks the clone's items and retries them itself. The worker slot is released then. A
      teardown refused as clone_in_use keeps the obligation open and the slot held, unchanged. A sweep
      does not attempt a deferred teardown again. The clone's pins are released when the work tree's
      item is removed, whoever removes it and whenever, and not before
    falsified_by: >
      Each of these turns a row of its own red. Keep the obligation open on space_deferred: the row's
      dispatch, whose clone is left due in report mode, still holds its worker slot after the sweep,
      and the row fails. Attempt the teardown on every sweep: the row counts the run finished events
      sent for the same clone over three sweeps, finds three and fails. Release the pins at the
      teardown call only: the row has the owner's Confirm remove the work tree after the slot was
      released, finds the pin still held in the cache, and fails. Release them at hand-over: the row
      collects the cache while the work tree is deferred, finds its commit unreadable, and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The receiver sends no run finished, and the run's items stay present until another
  event ends them.
---

## Intent

A dispatch's scratch, run directory and Docker objects go when the run has finished: the dispatch is
conclusive and its containment group is empty. The receiver then runs the census, Signal and the release
of the hold, in that order, and all three are written before it exits. A pending retirement that completes
retries the dispatch's deferred items in the same call.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (run finished), 6.7 (release) and
8.1 (steps 6 to 10). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver, Retirement. A review's verdict recorded is VELDO-0337.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: AC4 added, from the review of VELDO-0303 (finding 4) and the lead's decision on it. Not
  built yet, here or in VELDO-0303. What the review found in control_retirement.py: the clone
  obligation is open while the clone is on disk or a pin is held (_observe), lifecycle refuses the
  release of the worker slot while clone is the first open obligation, _complete_clone turns every
  refused teardown into teardown refused, and _due answers true for it at every sweep. So once a
  ledger is wired into the clone provisioner, a clone that a rule defers, and in report mode every
  clone, would keep its dispatch's worker slot until the owner's Confirm, and every sweep would
  send run finished again for the same items, which is the falsifier of AC3. The decision: the slot
  is compute, and the clone's files are a deferred item the ledger tracks. So the obligation closes
  on hand-over to the ledger (retired, or a refusal whose code is space_deferred), the slot is
  released then, and a deferred teardown is recorded as deferred with the ledger's item and is not
  attempted again by a sweep. clone_in_use is live compute and keeps the obligation open. Two things
  follow and are part of AC4 and of this ticket's build. The pins: today the provisioner releases
  them only inside the teardown call (control_clone.Clones._through_space), and after the slot is
  released nothing calls the teardown again, so the release has to follow the work tree item's
  removal outcome wherever it is written (the next event, admission, reconcile, the owner's
  Confirm). AC3: its "a pending retirement's obligation completes" now includes the clone
  obligation closing at hand-over, and the design's Retry paragraph of section 7 and the Retirement
  row of the component table need the same wording when the design is next revised. This ticket
  must land before `space` is wired into the clone provisioner: VELDO-0303 threads `space` through
  to the three places that build one (control_launch.py twice, control_launch_work.py once), and
  nothing gives them a ledger yet.
