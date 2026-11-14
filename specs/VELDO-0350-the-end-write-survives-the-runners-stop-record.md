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
    The launch that started the receiver keeps that status (Launch.returncode). A receiver that failed
    writes one line on its standard error, with the error's class, its refusal code and the status; the
    launch sends the receiver's standard error to a file beside the run's execution record
    (Launch.receiver_log, the record's name with .receiver.log), of the owner alone.
  error_taxonomy: >
    No new refusal. An end write that could not be recorded after its retries is refused stale_version
    (stale_subject), as before. The receiver's exit status END_UNRECORDED (3) means it failed and the
    dispatch's record shows no end; 0 after a failed event means the end is on the record. When the
    runner records unknown for a receiver that exited END_UNRECORDED with its dispatch still running, the
    record's reason is outcome_unknown:end_unrecorded (unknown_outcome, as outcome_unknown is); for a
    receiver that was killed, vanished or ended with any other status it is outcome_unknown, as before.
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
      when it failed after the end was recorded, and when it ended cleanly. The launch that started the
      receiver reads the status: when it records unknown for a receiver that left its dispatch running
      and exited with that status, the record's reason says so (outcome_unknown:end_unrecorded), apart
      from a receiver that was killed or ended any other way (outcome_unknown), and the receiver's
      standard error is kept in a file beside the run's execution record
    falsified_by: >
      Each of these turns a row of its own red. Exit 0 after every failure, as it was: the row's
      receiver, whose end write was refused, exits 0 with the record still running. Exit non-zero after
      every failure: the row's receiver, which failed after its end was recorded, exits non-zero. Drop
      the status in the launch: the row's dispatch, whose receiver exited with it, is recorded
      outcome_unknown. Send the receiver's standard error to /dev/null, as it was: the row's log holds
      nothing of the real receiver that failed
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
read raises), it exits END_UNRECORDED (3). The failed event is written as before.

Who reads the status (the fix after the review, finding F1). Launch._end_receiver keeps the reaped
receiver's status in Launch.returncode. Launch.wait still settles from the record; when the record
says running and the receiver is gone it records unknown as before, and the reason it writes is
outcome_unknown:end_unrecorded when the status is END_UNRECORDED and outcome_unknown otherwise. The
part before the colon is the code every reader already has (the service writes
outcome_unknown:service_restart the same way), so nothing that holds or frees a unit changes. A receiver
whose output has reached its end of file is given RECEIVER_EXIT_SECONDS (2) to exit before the kill, so
the kill does not replace the status of a receiver that is ending by itself; one that is silent and
alive is killed at once, as before. invoke opens a file beside the run's execution record
(receiver_log: the record's path with .receiver.log, mode 0600 in the 0700 records directory) and
gives it to the receiver as its standard error, which was /dev/null. main() writes one line there
when it fails: the error's class, its refusal code (never the error's text) and the status. The file
is no part of the execution record and of no digest. A log that cannot be opened refuses no launch:
the receiver then gets /dev/null as before.

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
- 2026-11-14: fix, after the independent review of 66b943b2 (review-veldo-0350-and-suites.md, part A,
  verdict FIX: one finding; the retry sound). AC3 says more than it did: who reads the status. No other
  criterion changed.
  - F1: the new status reached nobody. invoke sent the receiver's standard error to /dev/null,
    Launch._end_receiver threw the status away, and the runner recorded outcome_unknown for a receiver
    whose end write was refused exactly as for one that died. Now the launch keeps the status, the
    unknown record's reason is outcome_unknown:end_unrecorded for a receiver that exited END_UNRECORDED,
    and the receiver's standard error is a file beside the run's execution record (the Design's "Who
    reads the status"). control_launch.py only, canon and copy.
  - Suite 150 is 10 rows, 36 passed. f1/launch-records-the-status: through the real Launch, a receiver
    whose end write was refused after its retries (the launch module's own main()) leaves status 3 on the
    launch, one end on the record, the runner's, with the reason outcome_unknown:end_unrecorded, and its
    line in the log; a silent receiver the runner killed and one that exited 1 are outcome_unknown; a
    receiver whose output ended 0.6 seconds before it exited keeps its own status; a receiver that
    recorded its end is not written over. f1/receiver-errors-in-the-log: the real invoke starts the real
    receiver, which cannot launch with the row's configuration; its line is in the log, a file of mode
    0600, the status is on the launch and in the record; a log that cannot be opened gives no descriptor.
  - One fixture change: the stand-in store that moves the record names its commands per dispatch, since
    two receivers now use it on one store.
  - Five falsifiers added under finding 350 (11 now), each applied once and red on its row, its no-op
    copy green: end350-launch-drops-the-status, end350-every-silent-receiver-recorded-unrecorded,
    end350-ending-receiver-killed-for-its-status, end350-receiver-errors-discarded,
    end350-receiver-says-nothing-of-its-failure. Two cases of finding 141 (record141e-config-read-after-
    spawn and its spawn anchor) are re-anchored, unchanged in meaning, because the lines they name gained
    the log; applied once, red on their rows.
  - Not done here, from the review's notes: N1 (two guards of the retry that no row holds), N2 (the
    runner's stop_result is not retried), N3. Each is for a ticket or a later round.
