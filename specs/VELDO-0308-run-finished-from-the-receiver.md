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
