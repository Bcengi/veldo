---
schema: veldo.spec/v1
id: VELDO-0301
title: "Signal: an event removes what is due, in the calling process"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0297, VELDO-0298, VELDO-0299, VELDO-0300]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "scripts/suites/*_veldo_0301_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0301-signal-an-event-removes-what-is-due-in-the-calling-process.md"
  - "specs/index.md"
  - "proof/VELDO-0301/**"
behavior_bearing: true
observability:
  logs: >
    One journal record per item made due and one per outcome: removed with the event, the method, the size
    and the free space before and after; deferred with the rule's name and the retry event; or gone.
  metrics: >
    Items removed, deferred by reason and marked gone, per event.
  traces: >
    An outcome joins the item to the event and to the process that called Signal.
  error_taxonomy: >
    A refusal is a deferral, never an error. An unknown event is refused by name. With the installation's
    switch off, and for an unconfirmed item of a project in report mode, Signal writes due and removes
    nothing.
acceptance_criteria:
  - id: AC1
    text: >
      A call with an event makes the matching items due, carries each out through rules and remover, and
      writes each outcome before it returns
    falsified_by: >
      Return after marking due and remove on a later call; the row that reads the disk as the call returns
      finds the folder and fails
  - id: AC2
    text: >
      A refused item is deferred with the rule's name and is carried out by the next event for it; an item
      whose thing is already missing is marked gone
    falsified_by: >
      Drop a refused item back to present; the next event's row finds no deferral record and fails
  - id: AC3
    text: >
      With the installation's switch off a call writes due and removes nothing. For a project in report
      mode it removes only items that carry the owner's confirmation
    falsified_by: >
      Ignore the mode; the report-mode row finds the unconfirmed folder gone and fails
  - id: AC4
    text: >
      No clock is read to decide a removal: with the fixture clock moved 30 days and no event, nothing
      changes
    falsified_by: >
      Add an age rule for scratch; the clock row finds scratch removed and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. No event removes anything, and items stay as recorded.
---

## Intent

Signal is the one entry point a process calls with an event. It marks the matching items due, carries each
out through the rules and its remover, and writes each outcome before it returns. A refused item waits for
its next event. No clock decides a removal.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 3 (the component view), 6.1 (signal
and outcome), 7 (the safety rules) and 8.6 (a deferral and its retry). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Signal. Depends on 0297, 0298, 0299, 0300.

Build order. It is built after 0298, 0299, 0330 and 0300, and before the creators and the event sources.
depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
