---
schema: veldo.spec/v1
id: VELDO-0288
title: Stop requests no longer collide with lifecycle writes on the dispatch record, and the record says whether the receiver was actually asked
status: draft
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0039, VELDO-0131]
placement: [loop]
protected_paths: []
footprint:
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - "scripts/suites/62_veldo_0039_dispatch.py"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0288-stop-requests-no-longer-collide-with-lifecycle-writes-on-the-dispatch-record.md"
  - "specs/index.md"
  - "proof/VELDO-0288/**"
  - "proof/VELDO-0127/claude-live.json"
  - "proof/VELDO-0127/codex-live.json"
  - "proof/VELDO-0127/resources-*.json"
behavior_bearing: true
observability:
  logs: >
    None new. A lifecycle write or stop_result that is refused keeps its existing refused observation.
  metrics: >
    None.
  traces: >
    Each retried commit is observed as its own attempt, with the same operation and dispatch, the refusal
    stale_version on the attempt that lost, and the attempt number, so a reader can count how often a stop
    write displaced a lifecycle write.
  error_taxonomy: >
    No new refusal names. stale_version keeps its meaning; what changes is that a stale_version caused
    only by stop metadata is retried instead of returned.
acceptance_criteria:
  - id: AC1
    text: >
      Every command Dispatches._run commits after prepare (accept, run, exit, refuse, unknown) can meet a
      stop write and be refused stale_version. _run reads the dispatch record's data and the versions of
      both entities it expects, in one read, just before it executes. On stale_version it reads them again
      and recommits only when the index entity's version is unchanged and the dispatch record is equal
      except for stop_request and history entries appended whose action is request_stop or stop_result.
      The retry reuses the command_id and nonce of the refused attempt, which wrote nothing, and
      recomputes its expected versions. A delivery retry of a committed observation still replays its
      first result through the journal's before_versions. A lifecycle write retries at most twice,
      because a dispatch takes at most two stop writes (one request_stop, one stop_result). stop_result
      refused stale_version re-reads the record and commits again while the re-read still shows the same
      stop request with result null; any other re-read is refused as today. stop_result retries at most
      three times, once for each lifecycle write that can follow a request (accept, run, end). Any other
      change between the read and the commit is refused exactly as today.
    falsified_by: >
      Suite 62 row dispatch/stop-write-commutes: with the record's version moved by a request_stop and by
      a stop_result between the receiver's read and its commit, accept, run and exit each commit on retry
      and the record holds the new state; the observations show the refused attempt with refusal
      stale_version and attempt 1, and the committed attempt with attempt 2. The sibling
      dispatch/lifecycle-write-still-stale: a state change (another receiver's exit) in the same window is
      refused stale_version with no retry. Row dispatch/stop-result-after-exit: the runner is held after
      stop_result's version read, the receiver's exit commits, and the record ends exited with
      stop_request.result.asked true. Mutation stop288-no-retry (the retry removed) reds the first row;
      stop288-retry-any-change (the re-read check removed) reds the second; stop288-result-no-retry (the
      stop_result retry removed) reds the third.
  - id: AC2
    text: >
      honor_stops asks the receiver first and records the result afterwards, so stop_request.result.asked
      is what Launch.stop returned: true only when the stop bytes reached a receiver of that dispatch. A
      runner that crashes between the ask and the record leaves the request pending (result null). A
      runner that doesn't hold the dispatch leaves it waiting while the dispatch runs and records asked
      false once it has ended. A receiver that ended before it could be asked is recorded asked false.
      The round 9 order (record, then ask) is replaced by this order. Tooth
      launch131-stop-recorded-unasked is re-anchored on the new ask line (the defect records asked true
      without calling Launch.stop) and still reds dispatch/owner-stop and
      dispatch/owner-stop-other-runner. The comment at check_teeth_mutations.py:12410 is updated to match.
    falsified_by: >
      Suite 62 row dispatch/owner-stop-asked-is-delivered: when Launch.stop returns False (the receiver's
      stdin closed after can_stop), the record carries asked false, and when it raises, asked false; when
      it returns True, asked true. Row dispatch/owner-stop-crash-before-record: a runner stopped by the
      honor_stops hook point of AC3 after the ask and before stop_result leaves result null. A second
      runner's sweep before the dispatch has ended leaves the request waiting. Its sweep after the
      dispatch has ended records asked false. Mutation stop288-record-before-ask (the round 9 order
      restored) reds both rows.
  - id: AC3
    text: >
      Suite 62 forces the interleavings with a hook in the receiver's write path, not a sleep or a load.
      Dispatches._run calls a named hook point between its version read and store.execute. It is active
      only when VELDO_CONTROL_TEST_HARNESS=1, the same gate as control_store._kill_point
      (control_store.py:550). Under the harness it blocks until the suite releases it through a file whose
      path is given in an environment variable. honor_stops has a second hook point between Launch.stop
      and stop_result, which the AC2 crash row uses to raise. Without the harness variable both points do
      nothing. The suite holds the receiver at the first point, runs honor_stops (and with it
      stop_result) in that window, and then releases it. Three rows use it:
      the stop causes the end, and the record reaches exited with cause requested and asked true; the
      worker ends on its own (natural end) while the stop lands, and the record reaches exited with the
      natural cause and the stop result recorded; and accept and run are each held while a stop request
      is pending and its result is recorded, and each commits, after which the stop is honored and the
      record ends with cause requested. No row ends with the record still running, a failed receiver
      event, or outcome_unknown.
    falsified_by: >
      Rows dispatch/stop-during-exit, dispatch/stop-during-natural-end and dispatch/stop-during-accept-run
      each fail under mutation stop288-no-retry. With the retry in place both orders reach exited, so the
      order is held by AC2's rows, which stop288-record-before-ask reds; together no single removal of the
      retry or the order leaves every row green. Each row passes 20 of 20 consecutive runs under the
      host's load during a full gate run, recorded in the proof with the command, commit, host and load
      average.
  - id: AC4
    text: >
      The honor_stops docstring states what is guaranteed and nothing more: the receiver is asked before
      the ask is recorded; asked true means the bytes reached the receiver; a lifecycle write that meets a
      stop write retries within the bound and is otherwise refused as before; a crash before the record
      leaves the request pending for the next sweep. It does not say the receiver's end "never races" the
      runner's record. The .veldo and engine/.veldo copies of both files stay byte identical.
    falsified_by: >
      Suite 62 row dispatch/honor-stops-docstring fails when Runner.honor_stops.__doc__ contains "never
      race" or still says the ask is recorded before it is made. The gate's template-sync check reds on
      any difference between the two copies of either file.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. honor_stops returns to the round 9 order (record, then ask) and lifecycle writes stop
  retrying, which is the interim landing-c shipped with. No stored record gains a field, so records
  written under this change read the same after the revert. A revert changes control_launch.py again, so
  the captures are retaken with the revert.
---

## Intent

Landing-c fix round 9 (commit 7c8bcb5d) made the gate's dispatch/owner-stop noop control green by
moving honor_stops to record the ask before making it. The review of that commit
(~/projects/myday/research/claude-runs/landing-c-fix9-review-2026-11-09.md) found the reorder sound as an
interim and wrong as the fix of record, for two reasons.

The race it closed is one case of a wider one. A stop request and a stop result write stop_request and a
history entry on the dispatch record. Neither changes the record's state, but both bump its version. The
receiver's lifecycle writes, in Receiver.launch (accept and run) and Receiver._finish (exit and unknown),
expect the version they read, so any stop write between the read and the commit refuses them stale. The
receiver then emits failed and exits 0, and the run is settled outcome_unknown with its unit held. The
reorder only removes this for an end the stop itself caused. Accept and run under a pending stop, and a
natural end, deadline or heartbeat loss that coincides with a sweep, still hit it. stop_result has the
same problem in the other direction: refused stale by a receiver write, it now skips the ask entirely.

The reorder also made the durable record false. A runner that dies between stop_result and the write to
the receiver's stdin, or a Launch.stop that fails, leaves asked true for a receiver that was never asked.
The request is consumed, a new one is refused stop_requested, and the worker runs to its deadline while
the record and the UI say it was asked.

The fix goes to the root: a write that changed no state should not refuse a lifecycle write. With that in
place the original order, ask then record, is safe again and the record says what happened.

## Design

Optimistic concurrency stays. _run reads the dispatch record's data and the versions of both entities it
expects, in one read, just before it executes. On stale_version it reads them again and recommits only
when the index entity's version is unchanged and the dispatch record is equal except for stop_request and
history entries appended whose action is request_stop or stop_result. That conflict was a stop write,
which changes no state. Any other difference means someone changed state, and the refusal stands.

stop_result has its own condition, because the write that refuses it is a receiver write and that always
changes state. stop_result refused stale_version re-reads the record and commits again while the re-read
still shows the same stop request with result null; any other re-read is refused as today.

A lifecycle write retries at most twice, because a dispatch takes at most two stop writes (one
request_stop, one stop_result). stop_result retries at most three times, once for each lifecycle write
that can follow a request (accept, run, end).

Moving stop_request into its own entity (record_id + '/stop') would have the same effect with no retry,
but it changes the record's data shape, which the suite and the API authority read. It is not this
spec's choice.

The ordering is guarded by rows, not by a comment. The rows hold the receiver at a named hook between its
read and its commit, so the interleaving is the same on every run and does not depend on host load,
which is how the original race survived until gate 7.

## Out of scope

The API authority's stop path (control_api_authority.py), which runs with stop=None in the product; the
receiver's control channel and what EOF on it means; suites 83, 124 and 71 beyond staying green; any
change to the stored record's shape.

## VELDO-0127 captures

The change to .veldo/control_launch.py makes the VELDO-0127 live captures and resource records stale.
Retaking them is part of this ticket: .veldo/qualify.py for the four resource records,
proof/VELDO-0127/live.py run once for codex and once for claude for the two captures. The lead takes the
Claude capture from outside a run, because a run holds the login lease. Suite 86 0127 passes 28 of 28
before review.

## What the reviewer judges

- The re-read comparison covers every field a lifecycle transition judges, so a retry can never commit
  over a real state change.
- asked true cannot be recorded for a receiver the runner did not reach.
- Each new row is deterministic and fails when the retry or the order is removed.

## History

2026-11-09: drafted from the landing-c fix round 9 review (verdict NOT SOUND as the fix of record, fix
brief A to D).

2026-11-10: revision 1. Applied findings 1 to 14 of the spec review
(~/projects/myday/research/claude-runs/spec-veldo-0288-review-2026-11-10.md).
