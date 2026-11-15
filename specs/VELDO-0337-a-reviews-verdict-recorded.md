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
