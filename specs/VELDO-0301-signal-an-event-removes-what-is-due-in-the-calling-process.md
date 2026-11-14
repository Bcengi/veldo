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
- 2026-11-13: from the re-review of VELDO-0298 and VELDO-0330. The kind registry's due is free of I/O
  and trusts the look it is given: with no look every worktree and agent repository waits, and with a
  look that answers {} it returns them for removal. So this ticket's call of due must pass
  look=signal.inside (lambda identity, record: inside(ledger, probe, identity, record, run)), the same
  reading rule 6 makes, and no other look. It must have a row for it: an agent repository due at an
  event, with a kept worktree inside it, is not carried out and its files are still on disk when the
  call returns. Falsifier: pass a stub look that returns {}; the row finds the agent repository handed
  to the remover and fails. No acceptance criterion changed.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. Signal calls the removers and no tool itself, so the keep step of
  VELDO-0345, which is inside the removers, cannot be passed by. The ledger also refuses the outcome
  removed for a worktree or a private repository that has no keep record.
- 2026-11-14: from the independent review of VELDO-0300 (finding 6), recorded here because this spec did not
  say it and no code of Signal was changed for it. No acceptance criterion changed. The rules name every
  refusal of rule 7 remove_refused (control_space_signal.DEFERRAL), and the remover's own deferral
  survives only in found.said.deferral. The remover means three different things: remove_refused (the
  tool, or the remover by itself, refused), in_use (its second probe found a user under the marked
  name and the item was put back) and keep_failed (the keep step failed, or the last look found work
  it did not save or a tip it did not record). This ticket must pass the remover's own deferral
  through: when rule 7 refuses and said.deferral is one of remove_refused, in_use or keep_failed, the
  outcome is written with that deferral, and with remove_refused otherwise. The ledger's refusal of any
  deferral but remove_refused for a removing item has to accept those three (a ledger change, with
  VELDO-0345). Without it a keep_failed item is recorded as remove_refused, and reconcile's completion
  of a removing item "to the end" (design 4.1) would remove a folder that was put back because it was
  in use or held unsaved work. It must have a row: a worktree with an ignored file that is work, due at
  an event, is deferred keep_failed, not remove_refused, and is still on disk. Falsifier: name every
  tool refusal remove_refused; the row finds the wrong deferral and fails. Also from that review: when
  the remover's answer holds left_at, the item's thing is under its marked name and not at its locator;
  the outcome keeps the item removing and never gone (design 8.8), and
  control_space_remove.left(path, id) is the look.
