---
schema: veldo.spec/v1
id: VELDO-0313
title: "The CLI's space verb and the run wrapper"
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
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0313_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0313-the-clis-space-verb-and-the-run-wrapper.md"
  - "specs/index.md"
  - "proof/VELDO-0313/**"
behavior_bearing: true
observability:
  logs: >
    space run prints the numbers when the run would wait, and records the run's items, census and outcomes
    as a receiver does.
  error_taxonomy: >
    space run exits with the command's own status. In act mode with too little space it exits 75 with the
    numbers and does not start the command. record and event refuse an unknown kind or event type, a path
    outside every known root and a path on the protect list, each by name. With no central installation
    each verb says so and space run runs the command unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      space run declares the run with its station, scratch root, label and compose project name, starts
      the command in its own containment group, and after the command and the group end runs the census,
      run finished and release before it exits
    falsified_by: >
      Skip the census; the build folder the command made has no item, stays, and the row fails
  - id: AC2
    text: >
      space run exits with the command's own status. In act mode with too little space it exits 75 with
      the numbers and does not start the command; in report mode it prints the numbers and starts it
    falsified_by: >
      Start the command anyway in act mode; the row finds the command's marker file and fails
  - id: AC3
    text: >
      record and event refuse an unknown kind or event type, a path outside every known root and a path on
      the protect list, each by name; the event types are ref changed, session started, session ended and
      released
    falsified_by: >
      Accept any path; the row that records a folder outside the roots gets an item and fails
  - id: AC4
    text: >
      With no central installation each verb says so, and space run runs the command unchanged
    falsified_by: >
      Refuse to run; the row's command never starts and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Commands started from a shell run unwrapped, with no admission and no removal at
  their end.
---

## Intent

A builder or a gate started from a shell is outside the receiver. The CLI's space run wraps such a
command: it asks admission, declares the run with its station, scratch root, label and compose project
name, starts the command in its own containment group, and afterwards runs the census, run finished and
the release. The record and event verbs let a host script report what it made and what it gave up.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (the run wrapper rows), 6.3
(what a run is given), 6.7 (admission) and 3 (the CLI's verb space). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: CLI.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
