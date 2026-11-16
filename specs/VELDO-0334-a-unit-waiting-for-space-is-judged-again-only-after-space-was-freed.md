---
schema: veldo.spec/v1
id: VELDO-0334
title: "A unit waiting for space is judged again only after space was freed"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0316]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_admission.py"
  - ".veldo/control_space_admission.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/*_veldo_0334_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0334-a-unit-waiting-for-space-is-judged-again-only-after-space-was-freed.md"
  - "specs/index.md"
  - "proof/VELDO-0334/**"
behavior_bearing: true
observability:
  logs: >
    A hold records that its one admission requested event was sent, and each time its freed mark is set
    and cleared.
  error_taxonomy: >
    None new. A waiting hold answers space_wait:<pool> with the recorded numbers until it is judged again.
acceptance_criteria:
  - id: AC1
    text: >
      Admission requested is sent once, when a hold first would wait: a waiting unit offered on three more
      passes, one of them woken by the account-reset timer, causes one Signal call in all
    falsified_by: >
      Retry the deferred items on every admit call; the row counts four Signal calls and fails
  - id: AC2
    text: >
      A waiting hold is judged again only when its freed mark is set. On a pass woken by any other source
      admit returns the recorded answer and reads no free space: with space freed by hand on the fixture
      pool and a pass woken by the account-reset timer, the unit is still waiting
    falsified_by: >
      Read free space on every admit call; the row's unit is admitted on the timer-woken pass and fails
  - id: AC3
    text: >
      A removal outcome with freed bytes on the pool, a released hold on the pool and a reconcile each set
      the mark and raise the wake source space; with the fixture clock stopped, a unit waiting on the pool
      is prepared after a removal frees enough, with no other action
    falsified_by: >
      Set the mark and leave out the wake; with the clock stopped no pass runs, the unit stays waiting and
      the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Nothing sets the freed mark or raises the space wake, and a waiting unit is judged as
  VELDO-0316 alone leaves it.
---

## Intent

A unit waiting for space is offered on every pass of the factory loop, and most passes have nothing to do
with space. This ticket makes a waiting hold cost nothing on those passes: it is judged again only after a
ledger write that freed space on its pool, and that write also wakes the loop.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.7 (what judges a waiting hold
again) and 4.3 (the hold's retry asked and freed fields). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Admission, Ledger, Authority service (the wake source space). Depends on 0316.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.

- 2026-11-16: footprint includes Signal and its synced copy. Admission requested retries a pool
  through the existing ending event, rules, keep step and removers. No acceptance criterion changed.
