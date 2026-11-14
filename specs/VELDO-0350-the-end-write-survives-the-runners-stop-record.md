---
schema: veldo.spec/v1
id: VELDO-0350
title: "The end write survives the runner's stop record"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0039, VELDO-0131, VELDO-0261]
placement: [loop, contracts]
protected_paths: [".veldo/control_dispatch.py", "engine/.veldo/control_dispatch.py", ".veldo/control_launch.py", "engine/.veldo/control_launch.py"]
footprint:
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "scripts/suites/*_veldo_0350_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0350-the-end-write-survives-the-runners-stop-record.md"
  - "specs/index.md"
  - "proof/VELDO-0350/**"
behavior_bearing: true
observability:
  logs: >
    Each time an end write is sent again the dispatch service observes one record with the outcome
    retried, the refusal stale_version, the attempt number and the versions the refused command expected.
    The accepted or refused record that follows is as before. A receiver that failed still writes its
    failed event on standard output; its exit status now says whether the dispatch's record shows an end.
  error_taxonomy: >
    No new refusal. An end write that could not be recorded after its retries is refused stale_version
    (stale_subject), as before. The receiver's exit status END_UNRECORDED (3) means it failed and the
    dispatch's record shows no end; 0 after a failed event means the end is on the record.
acceptance_criteria:
  - id: AC1
    text: >
      A write that records a dispatch's end (exit, unknown, refuse) and is refused stale_version because
      the record moved between the write's read of its version and its command reads the record again
      and, while the record shows no end and is in a state the write moves a record from, sends the
      command again with the versions read then. With the runner's record of its stop ask committed
      between the receiver's read and its command, the end is recorded: the record ends in the state the
      write gives, with what the write carried, and the stop request keeps its result. A write that
      records no end is refused stale_version as before
    falsified_by: >
      Each of these turns a row of its own red. Refuse the end write stale_version with no second read,
      as it was: the row's exit, sent with the runner's stop record committed in between, is refused
      and the record still says running. Send every write again, not only one that records an end: the
      row's run of an accepted dispatch, sent the same way, is accepted
  - id: AC2
    text: >
      No dispatch ever has two ends. When the record read again shows an end, or any state the write
      does not move, nothing more is sent and the refusal stands. The same end delivered again after it
      committed writes nothing. The retry is bounded: a record that moves before every command is sent
      the write END_RETRIES times after the first and the write is then refused stale_version, with no
      end recorded
    falsified_by: >
      Each of these turns a row of its own red. Send the write again whatever the record shows: with
      another writer's end committed between the read and the command the row's receiver sends a second
      command. Retry without a bound: the row's write, against a record that moves before every command,
      is still being sent after END_RETRIES retries
  - id: AC3
    text: >
      The receiver's main() exits with a status other than 0 when it failed and the record of the
      dispatch it was asked to launch shows no end, also when that record cannot be read. It exits 0
      when it failed after the end was recorded, and when it ended cleanly
    falsified_by: >
      Each of these turns a row of its own red. Exit 0 after every failure, as it was: the row's
      receiver, whose end write was refused, exits 0 with the record still running. Exit non-zero after
      every failure: the row's receiver, which failed after its end was recorded, exits non-zero
required_evidence: [unit, integration]
rollback: >
  Revert the change. An end write refused stale_version is refused at once again, and a receiver that
  failed exits 0 again; the runner then records such a dispatch unknown, as before this ticket. No
  record and no stored field is changed by the revert.
---

## Intent

A worker the owner stopped ends, and its dispatch is recorded as ended. Today the receiver's write of
that end can be refused as stale, because the runner writes the record of its stop ask on the same
dispatch record in the same moment. The receiver then leaves with status 0 and no end on the record,
and the runner records the dispatch unknown: the unit and the station stay held for a stop nobody owes.

## Context

Found by the review of the item naming in space management (2026-11-14, finding F2), from two rows of
suite 62_veldo_0039_dispatch that failed under parallel load and passed alone. It is a product race
older than space management and outside its footprint, so it is its own ticket.

Where. Runner.honor_stops (control_launch.py) asks the receiver to stop and then writes stop_result on
the dispatch record, which moves the record's version and not its state. The receiver's end write goes
through Dispatches._run (control_dispatch.py), which reads the record's version and then sends its
command with that version. When stop_result commits between the two, the store refuses the command
stale_version. main() catches the refusal, writes a failed event and returns, so the process exits 0.
The runner finds a receiver that ended with the record still running and records the dispatch unknown.

The proof was deterministic, not a rerun. With a three second sleep after the version read (for the
exit only) and a one second sleep in the runner between the ask and its record, suite 62 fails
dispatch/owner-stop and dispatch/owner-stop-other-runner with exactly the logged signature ("ended
(exit 0) with the record still running", state unknown, asked True), and dispatch/observations lists
both as unknowns it did not expect. The rows' expectation is right; the suite is not changed.

## Design

The end write (AC1, AC2), in Dispatches._run. A stop request and the runner's record of its ask are the
only writes that move a running record's version without moving its state. For the three actions that
record an end (ENDS: exit, unknown, refuse), a stale_version refusal is followed by a second read. The
command is sent again, with the versions read then, only while all of these hold: a version did move,
the record's state is one the action moves a record from (so it shows no end), the command was not
committed before, and fewer than END_RETRIES (8) retries were made. Otherwise the refusal stands, as
before. The command keeps its id: a refused command writes nothing, no nonce and no command row, so the
same content with new expected versions is a first commit. Nothing about who may write, the binding or
the states changed: the transition judges them inside each command's transaction, and that is what
keeps two ends from ever being recorded. Every other action is refused stale_version at once, as
before; an owner's stop request at a stale version in particular, since the owner acts on the version
shown.

The bound. Two writes can land between a read and a command in practice (the request and the ask's
record). Eight retries is far above that and still ends: a record that moves before every command is
left with no end and the refusal the caller always got.

The receiver's exit status (AC3), in control_launch.py. After a failure main() reads the record of the
dispatch its request named (end_recorded). An end is one of exited, refused, unknown. With an end on
the record it exits 0, as a failure after the end was recorded changes nothing the runner must settle.
With none, or with a record it cannot read (no receiver was made, the request names no dispatch, the
read raises), it exits END_UNRECORDED (3). The failed event is written as before. The runner does not
read the status today; it reads the record and settles it, which is unchanged. The status is for the
log and for whoever reads why a receiver ended.

Not done here. The other fix the review named, keeping the stop bookkeeping off the dispatch record's
version, would change what the record of a stop is and who reads it (VELDO-0131). The retry closes the
race without moving a stored field.

Protected paths. control_dispatch.py and control_launch.py, canon and copy, as VELDO-0261 named them.
The owner's recorded approval is needed at landing.

## What the reviewer judges

- The retry is taken only for a write that records an end, only on stale_version, only while the record
  read again shows no end, and it is bounded.
- No path writes an end over an end: the transition is unchanged, and the row shows one end in the
  history in every case.
- Each falsifier is registered and reds its row from a green baseline.
- Suite 62 is unchanged and green, also with the review's two delays put back into the fixed code.

## History

- 2026-11-14: written, made ready and built on the lead's instruction of that day, which followed the
  review of the item naming (verdict FIX; finding F2, to be ticketed apart). The number follows
  VELDO-0349; nothing in specs, plans or proof of any worktree, and no commit message, held 0350. Three
  criteria.
  - Built in control_dispatch.py (ENDS, END_RETRIES, the retry in Dispatches._run) and control_launch.py
    (END_UNRECORDED, end_recorded, main's exit status), canon and copy.
  - Suite 150_veldo_0350_end_write, 8 rows, 34 passed. The case is made without a clock: the receiver's
    Dispatches is given a store whose execute lets the runner's own sweep (Runner.honor_stops, writing
    stop_result) run to its end before the receiver's command reaches the real store, which is after the
    receiver read the versions. ac1/exit-after-the-stop-record, ac1/unknown-and-refuse-after-the-stop-
    record, ac1/other-writes-refused-as-before, ac2/never-two-ends, ac2/retry-is-bounded,
    ac3/failed-without-an-end, ac3/zero-with-an-end (both through the launch module's own main() in a
    process of its own) and paths/canon.
  - Red before, green after. The suite run against the two modules as they were at commit e38d5dcd:
    ac1/exit-after-the-stop-record is red with the refusal stale_version and the record still running.
    The review's own case, on a scratch clone of e38d5dcd with its two delays put in: suite
    62_veldo_0039_dispatch fails dispatch/owner-stop, dispatch/owner-stop-other-runner and
    dispatch/observations with the review's signature; with the modules of this ticket and the same
    two delays it passes, 51 of 51.
  - Six falsifiers registered under finding 350, each applied once to the copy the suite loads and seen
    red on its rows, its no-op copy green: end350-stale-end-write-refused (AC1, declared),
    end350-every-write-sent-again, end350-sent-again-over-a-recorded-end (AC2, declared),
    end350-retry-without-a-bound, end350-failed-receiver-exits-zero (AC3, declared),
    end350-failed-receiver-never-exits-zero.
  - Stand-ins, named in the suite: the dispatch and member records are fixture records, since prepare,
    accept and run need the reservation and the claim; in the AC3 rows the Receiver class is a stand-in
    around the real Dispatches. The whole path with a real receiver, a real worker and the real runner
    is suite 62's dispatch/owner-stop, unchanged.
