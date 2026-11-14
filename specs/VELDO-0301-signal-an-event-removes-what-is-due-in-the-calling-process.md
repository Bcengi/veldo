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
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0301_*.py"
  - "scripts/suites/134_veldo_0331_space_mode.py"
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
  - id: AC5
    text: >
      When rule 7 refuses, the outcome is written with the remover's own deferral, one of remove_refused,
      in_use and keep_failed, and with remove_refused when the remover names none of the three. When the
      remover's answer holds left_at, the item's thing is under its marked name and not at its locator:
      the outcome keeps the item removing, records left_at, and never marks it gone. The rows are a
      worktree with an ignored file that is work, due at an event, deferred as keep_failed and still on
      disk, and a folder the remover could not put back, still removing with its marked name recorded
    falsified_by: >
      Each of these turns a row of its own red. Name every tool refusal remove_refused: the row finds the
      worktree deferred as remove_refused and fails. Write the outcome of an answer with left_at as any
      other deferral: the row finds the item no longer removing, or marked gone with its folder whole
      under the marked name, and fails
  - id: AC6
    text: >
      An item is marked gone only when os.lstat said not found (ENOENT) at its locator and at its marked
      name. Any other answer, a folder above it that may not be searched (EACCES), an input/output error
      (EIO) or any other error, is a path that could not be read: the item is deferred with what was said
      and is never gone. The row is a folder whose parent has mode 000, due at its event: it is deferred
      as not_in_ledger, its files are all there, and its next event removes it
    falsified_by: >
      Each of these turns the row red. Read the locator with os.path.lexists: the row finds the item not
      deferred by rule 1 with what the kernel said. Read the marked name with os.path.lexists: the row's
      folder, not found at its path and with an input/output error at its marked name, is marked gone
  - id: AC7
    text: >
      Nothing that raises stops the event. An exception outside the rules while one item is carried out
      (the second look at the locator, the look under the marked name, a write of the ledger) defers
      that item as remove_refused with what was raised, and every other item of the event is carried
      out. When the kind registry's due raises, every carried item is deferred as remove_refused with
      what was raised and none is handed to a remover. The call returns with one entry per item
    falsified_by: >
      Each of these turns the row red. Let an item's exception leave the loop: the row's call raises and
      the two folders after the failing item are still on disk. Let the registry's exception leave the
      call: the row's call raises and its two items are due with no outcome
  - id: AC8
    text: >
      Every outcome a call writes holds the carrier: the id and the start time of the process that
      carries the item out and the journal number of the call's signal record. It is on the removal
      record from the moment the item is written removing, before its remover runs. A call whose
      removing write the ledger refuses because another carrier made the item removing first calls no
      remover and writes nothing over that record
    falsified_by: >
      Each of these turns a row of its own red. Write no carrier: the row reads the item while its
      remover runs and finds no carrier on its removal record. Write the refusal as a deferral: the
      row's item, made removing by another carrier, is found deferred by this call
  - id: AC9
    text: >
      No caller carries out by a callable of its own. A call that gives carry_out is refused by name,
      space_carry_out_refused, before the ledger is asked anything: nothing is made due and the callable
      is never called. Every removal an event causes passes the rules and its remover
    falsified_by: >
      Do not refuse; the row's call with carry_out makes the item due, and the row finds it not present
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
- 2026-11-14: from the re-review of VELDO-0300 (review2-veldo-0300.md, finding D). The note above said
  no acceptance criterion changed while it asked for a row and a falsifier, and a History note that
  changes no criterion binds nobody. It is now AC5: the remover's own deferral (remove_refused, in_use,
  keep_failed) is passed through to the outcome, and an answer that holds left_at keeps the item
  removing, with the marked name recorded, and never gone. AC5 has two falsifiers. The ledger's part,
  accepting those three deferrals for a removing item, is VELDO-0345 AC6. Four criteria became five. AC5
  is not in section 12 of the design, whose text this change does not edit; the criteria of AC1 to AC4
  are still the design's word for word.
- 2026-11-14: built. No acceptance criterion changed. Three things the build decided, recorded here
  because the criteria do not say them:
  - The item stays due while its remover runs, and removing is written only for a thing left under its
    marked name (the remover's answer holds left_at, or the look control_space_remove.left finds it).
    The ledger as built refuses any deferral but remove_refused for a removing item (VELDO-0345 AC6 is
    not built), so an item written removing ahead of its remover could not be deferred as keep_failed
    or in_use, and would be left for reconcile to finish "to the end" with its folder back at its
    path. Written this way AC5 holds on today's ledger and no ledger code is changed. When VELDO-0345
    AC6 is built nothing here has to change. What this gives up: a process killed inside a remover
    leaves its item due, not removing, with the thing under its marked name; VELDO-0315 looks under
    the marked name for any item with nothing at its locator, so reconcile still finds it.
  - An item is marked gone only after two looks: rule 1 finds nothing at the locator, and
    control_space_remove.left finds nothing under the marked name. A Docker object is gone only when
    its engine was read and answered that it holds no such object; a volume the engine shows (it has
    no Id, which rule 1 reads as missing) is deferred, not gone.
  - The owner's confirmation is read from the item's record (confirmed). No ledger command writes it
    until VELDO-0320, so the suite reads the real ledger through a view that returns one item with
    it. A measure cell, a contained branch and an event with no cell for the item's row leave the item
    kept, with the action named: the measuring and the mark are their own tickets.
- 2026-11-14: fixed from the independent review of this ticket (review-veldo-0301.md, verdict FIX).
  Five criteria became nine: each fix is a criterion with a row and a falsifier, because a History note
  that changes no criterion binds nobody. AC1 to AC5 are unchanged. AC6 to AC9 are not in section 12 of
  the design, whose text this change does not edit.
  - Finding 1 (the MUST), AC6. os.path.lexists answers False for a path it could not read, so a folder
    under a parent of mode 000 was read as missing twice and its item marked gone with every file on
    disk. Now the probe's located reads the locator with os.lstat (control_space_probe.there): exists
    is False only for not found, and None with unread, what was said, for any other answer. Rule 1 says
    missing only for not found. The removers' left reads the marked name the same way and raises on any
    other answer. Signal marks gone only on not found at both. The probe and the removers are added to
    the footprint (both copies). Row ac2/unreadable-is-not-gone; falsifiers
    space301-lexists-at-the-locator and space301-lexists-under-the-marked-name. With lexists back at
    the locator alone the row's item is no longer gone, because the look under the marked name now
    raises for the same parent; it is red because rule 1 no longer names what could not be read.
  - Finding 2, AC7. Only the rules were under a handler. Now each item is carried out under one of its
    own and the registry's due under another. Row ac1/every-item-gets-an-outcome; falsifiers
    space301-an-item-that-raises-stops-the-event and space301-a-registry-that-raises-stops-the-event.
  - Finding 3, AC8. The carrier is {pid, started, seq}, read by the probe's carrier, written into
    every outcome's facts and so onto the removal record at the removing write. No ledger code changed:
    the ledger stores the facts it is given. The due record is not given a carrier, because an item
    left due by the switch or by report mode is held by nobody, and a live long-running emitter named
    on it would hold it for ever. The window between due and removing is closed another way: the
    ledger admits one removing write, and the call that loses it writes nothing (the second half of
    AC8). What reconcile does with the carrier is VELDO-0315 AC5, added with this fix. Rows
    carrier/recorded and carrier/one-remover; falsifiers space301-no-carrier-on-the-record and
    space301-writes-over-another-carrier.
  - Finding 5, AC9. carry_out is refused, not routed: a callable given a due item can do anything with
    it, and no production caller existed. The parameter keeps its place so that a positional fourth
    argument is refused and not read as the principal. VELDO-0331's suite (134) used it as its
    remover; it now gives Signal the real probes, registry and removers, which is why that suite is
    in this footprint. No check of that suite was removed. Row rules/carry-out-refused; falsifier
    space301-carry-out-not-refused.
  - Finding 4, no code here. An item left due is not matched by a later event, and Signal does not
    pick it up: a due item may be one another process is carrying. The tickets that carry such items
    are VELDO-0320 (AC1: Confirm removes the group's due items through all seven rules) and VELDO-0315
    (AC6, added with this fix: reconcile carries the due items that may now be carried out). The
    retry of a signal command refused as stale_version is not built and is not in a criterion.
  - Also in this change: the registered case space331-signal-reads-no-mode (VELDO-0331) had no anchor
    since this ticket rewrote the line it mutated. It is anchored again at the line that reads the
    mode, and is red on ac2/signal-by-scope (proof/VELDO-0301/mutations.txt).
