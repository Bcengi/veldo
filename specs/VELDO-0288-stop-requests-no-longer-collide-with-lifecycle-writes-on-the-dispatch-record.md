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
      A lifecycle write (accept, run, exit, unknown) and stop_result that the store refuses stale_version
      re-read the dispatch record and commit again only when the re-read differs from the record the write
      first read in nothing but stop_request and history: the same state, contract digest and every
      lifecycle field the transition judges. Each retry recomputes its expected versions from the re-read
      and is a new command only because the re-read showed a stop write; a delivery retry of the same
      observation still replays its first result. Attempts are bounded by a small fixed number named in
      the code. Any other change between the read and the commit is refused exactly as today, and so is a
      stop-only conflict that outlasts the bound.
    falsified_by: >
      Suite 62 row dispatch/stop-write-commutes: with the record's version moved by a request_stop and by
      a stop_result between the receiver's read and its commit, accept, run and exit each commit on retry
      and the record holds the new state. The sibling dispatch/lifecycle-write-still-stale: a state change
      (another receiver's exit) in the same window is refused stale_version with no retry. Mutation
      stop288-no-retry (the retry removed) reds the first row; stop288-retry-any-change (the re-read check
      removed) reds the second; stop288-unbounded (no bound, with a hook that writes stop metadata on
      every attempt) reds a row that expects the refusal after the bound.
  - id: AC2
    text: >
      honor_stops asks the receiver first and records the result afterwards, so stop_request.result.asked
      is what Launch.stop returned: true only when the stop bytes reached a receiver of that dispatch. A
      runner that crashes between the ask and the record leaves the request pending (result null), which
      is true, and the next sweep asks again. A receiver that ended before it could be asked is recorded
      asked false. The round 9 order (record, then ask) and its tooth launch131-stop-recorded-unasked are
      replaced by this order and the teeth of AC3. The alternative the review allows, a record of intent
      before the ask and a second commit of delivery after it with an explicit delivery-unknown state
      after a crash, adds a field to the stored dispatch record; a build that takes it amends this spec
      first with risk_areas [schema] and the approval that area computes.
    falsified_by: >
      Suite 62 row dispatch/owner-stop-asked-is-delivered: when Launch.stop returns False (the receiver's
      stdin closed after can_stop), the record carries asked false, and when it raises, asked false; when
      it returns True, asked true. Row dispatch/owner-stop-crash-before-record: a runner stopped by an
      injected hook after the ask and before stop_result leaves result null, and a second runner's sweep
      records it. Mutation stop288-record-before-ask (the round 9 order restored) reds both.
  - id: AC3
    text: >
      Suite 62 forces the interleavings with an injected hook in the receiver's write path, not a sleep or
      a load. The hook holds the receiver after it has read the record's version and before it commits,
      runs honor_stops (and with it stop_result) in that window, and then releases it. Three rows use it:
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
      retry or the order leaves every row green. Each row passes 20 of 20 consecutive runs on an idle
      host, recorded in the proof with the command, commit and host.
  - id: AC4
    text: >
      The honor_stops docstring states what is guaranteed and nothing more: the receiver is asked before
      the ask is recorded; asked true means the bytes reached the receiver; a lifecycle write that meets a
      stop write retries within the bound and is otherwise refused as before; a crash before the record
      leaves the request pending for the next sweep. It does not say the receiver's end "never races" the
      runner's record. The .veldo and engine/.veldo copies of both files stay byte identical.
    falsified_by: >
      The reviewer reads the docstring against AC1 to AC3 and the code, and the claim "never races" (or
      any claim with the same meaning) is absent. The gate's template-sync check reds on any difference
      between the two copies of either file.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. honor_stops returns to the round 9 order (record, then ask) and lifecycle writes stop
  retrying, which is the interim landing-c shipped with. No stored record gains a field, so records
  written under this change read the same after the revert.
---

## Intent

Landing-c fix round 9 (commit 7c8bcb5d) made the gate's dispatch/owner-stop noop control green by
moving honor_stops to record the ask before making it. The review of that commit
(~/projects/myday/research/claude-runs/landing-c-fix9-review-2026-11-09.md) found the reorder sound as an
interim and wrong as the fix of record, for two reasons.

The race it closed is one case of a wider one. A stop request and a stop result write stop_request and a
history entry on the dispatch record. Neither changes the record's state, but both bump its version. The
receiver's lifecycle writes (accept and run in Launch.launch, exit and unknown in Launch._finish) expect
the version they read, so any stop write between the read and the commit refuses them stale. The receiver
then emits failed and exits 0, and the run is settled outcome_unknown with its unit held. The reorder
only removes this for an end the stop itself caused. Accept and run under a pending stop, and a natural
end, deadline or heartbeat loss that coincides with a sweep, still hit it. stop_result has the same
problem in the other direction: refused stale by a receiver write, it now skips the ask entirely.

The reorder also made the durable record false. A runner that dies between stop_result and the write to
the receiver's stdin, or a Launch.stop that fails, leaves asked true for a receiver that was never asked.
The request is consumed, a new one is refused stop_requested, and the worker runs to its deadline while
the record and the UI say it was asked.

The fix goes to the root: a write that changed no state should not refuse a lifecycle write. With that in
place the original order, ask then record, is safe again and the record says what happened.

## Design

Optimistic concurrency stays. On stale_version, Dispatches._run and stop_result re-read the record and
compare it with the record the write first read, excluding stop_request and history. Equal means the
conflict was a stop write, which commutes with every lifecycle transition, so the write recomputes its
expected versions and commits again. Unequal means someone changed state, and the refusal stands. The
retry count is bounded so a stream of stop writes cannot spin a receiver.

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

## What the reviewer judges

- The re-read comparison covers every field a lifecycle transition judges, so a retry can never commit
  over a real state change.
- asked true cannot be recorded for a receiver the runner did not reach.
- Each new row is deterministic and fails when the retry or the order is removed.

## History

2026-11-09: drafted from the landing-c fix round 9 review (verdict NOT SOUND as the fix of record, fix
brief A to D).
