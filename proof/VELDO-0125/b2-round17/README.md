# VELDO-0125 B2 round 17

This correction separates operational entry-read errors from invalid content and
makes deadline validity independent of wall-clock changes. It continues from
5d2943bf on agent/codex/veldo-0125-b2.

- An OSError opening or reading an entry is logged and returns no entry for
  that pass. The file stays in place for a later pass. Skipping the failed read
  also keeps receiver error handling from parking it as a recorder failure.
- Undecodable bytes, malformed JSON and values outside the entry contract still
  quarantine the original bytes before exposing fields. Other unexpected errors
  propagate instead of being classified as content corruption.
- Due is a non-negative finite int or float, excluding bool, bounded by
  sys.float_info.max. It has no wall-clock-relative upper bound. The existing
  drain sleep clamp of 1-300 seconds is unchanged.

`round17_checks.py`, registered in suite 106, adds thirteen rows: eight operational-read rows
(EIO, EMFILE, ENFILE and EACCES in both recovery and entries), receiver EIO, a four-second
writer-created retry read after a 600-second backward clock step, and three
far-future deadline rows (1e300, maximum float and its exact integer value).
Every retained valid entry is subsequently drained. The backward-clock row
observes sleeps of 300, 300 and 4 seconds. Far-future rows observe a 300-second
sleep before a simulated resync makes delivery due.

Round 16's former rejection of 1e300 and now+300.01 is superseded by the owner's
round 17 contract. Those invalid-content fixtures now use an integer one above
the maximum finite float, keeping all read-boundary coverage. Round 17 tests
finite future deadlines through real queue reads and the unchanged sleep clamp.
Round 13's unreadable-active fixture now requires retention and delivery after
permissions recover, while still requiring healthy-peer progress. The remaining
invalid-entry, corrupt-byte, writer-compatibility, ENOSPC recovery and defensive-
sleep rows are retained.

Logs and exit codes are recorded separately for baseline, regressions against
the original implementation, intermediate observations, the receiver negative
control, and the final fixed implementation. `results.json`
records commands, row counts, source digests and log digests. Selected-suite
success exits 2 by repository design; it is not a gate pass. The full gate,
mutation scripts, native qualification, independent approval, merge and push
were not run. These are scoped observations for the reviewer, not a passed
unit-evidence manifest or landing decision.
