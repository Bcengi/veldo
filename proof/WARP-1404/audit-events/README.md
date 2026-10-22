# WARP-1404 AC5 audit event coverage

Scope: test suite and its embedded audit driver only, based on `f3e204c0`.
The reviewed bytecode suppression remains enabled before the audit hook is installed.
No product code or earlier proof file is changed.

## Event names

Every original WRITES and SPAWN entry and each requested addition was checked
against the [official CPython 3.12 audit events table](https://docs.python.org/3.12/library/audit_events.html).
The per-name results are in `name-check.txt`.

The only original entries absent from that table are `os.replace` and
`socket.socket`. Replace the latter with `socket.__new__`; the former operation
already emits the monitored `os.rename` event. The requested `os.lchown` is also
not an event: that operation emits the already monitored `os.chown` event.
The [OS documentation](https://docs.python.org/3.12/library/os.html) confirms
both aliases, recorded in `operation-aliases.txt`. Do not add a nonexistent
`os.lchown` event name. Keep `os.truncate` and exercise it explicitly.

Add these nine real event names: `os.utime`, `os.chflags`, `os.setxattr`,
`os.removexattr`, `shutil.make_archive`, `shutil.unpack_archive`,
`socket.__new__`, `socket.sendto`, and `socket.sendmsg`.

## Falsifier design

The new rows reuse `_w1404_auditroot`, injecting code at module scope in its
copied `estimate.py`. The `toe_analogy.py` import and named-call allowlists
therefore remain satisfied. Every row requires a successful driver process,
all eight drives, the CLI report, more than 100 real corpus records, the expected
predictions and the existing read-only git spawn allowance. Its own event must
appear in the PURE or strict repository write bucket. The dependency loads lazily
during the PURE window, so module-scope effects are recorded there. A fresh process
after each source restoration must satisfy those same checks with both buckets empty.

The timestamp, ownership, xattr, archive, replacement and truncation calls target
scratch files only. Archive creation and extraction use a real one-member ZIP.
The socket creation row creates and closes an unconnected socket. The send rows
close their socket before attempting a send, so no packet can be transmitted;
the attempted operations must still emit their named events. OS errors are
caught, but a missing event or an incomplete report fails the row.

This Linux CPython 3.12.3 runtime has no `os.chflags` function. That row explicitly
uses `sys.audit` with the documented event and arguments, and labels the report
synthetic. On a platform providing the function the row calls it directly.
This proves the hook handles that event here, not that a native chflags syscall
ran. All other new operation rows use real APIs.

The prior cold read-only cache, import writer and import spawn rows remain.
Additional controls drive a cold writable cache and a cache warmed by importing
both scratch modules in a separate process with bytecode enabled. Both controls
require empty audit buckets; the warm control also requires actual compiled
analogy and estimate cache files.

## Execution evidence

The initial run used the original event tuple with the new regression rows
(source matching `39a1e84c`). It completed with 54 selected-suite passes;
including shared setup, 80 passed and 13 failed, exit 1. All nine new event
assertions failed. Three auxiliary rows (`os.lchown`, `os.replace`, `os.truncate`)
also failed because the first helper incorrectly required an empty PURE bucket
even during injection. The warm control failed because its warmup omitted the
lazy estimate dependency. The raw reports preserve those observations in
`before-reports.jsonl`; failure and summary lines are in `before.txt`.
The initial reports' `complete` field includes that overly strict PURE check;
it does not mean those driver processes crashed or skipped their eight drives.

The event tuple fix is `cca2d214`. The helper correction is `2c9daf3f`, and the
explicit dependency warmup is `2df1e691`. The final run at `2df1e691` passed
all 67 selected-suite assertions. Including shared setup, it reported
93 passed, 0 failed in 224.51 seconds. Exit 2 is the dispatcher's intentional
successful partial-run status. See `after.txt`.

All 12 injections made AC5 red with their own expected event recorded, and
all 12 restorations were green with both strict buckets empty. This includes
the nine added events plus the lchown, replace and truncate operation controls.
Cold writable, warm and cold read-only cache rows all passed, as did the prior
import writer and import spawn falsifiers. The complete 26 driver reports
(two cache baselines plus 12 injection/restoration pairs) are retained in
`after-reports.jsonl`. Per-operation event lists are in `event-results.txt`.
The final tuple names, all present in the official table, are in `final-names.json`.

In the final reports, `complete` means all structural drive checks passed;
`ac5_green` additionally requires both strict audit buckets to be empty. This
keeps a correctly rejected injection distinct from a broken or incomplete drive.

Only `15_warp_1404_historical_analogy` is run. The full gate and mutation runners
are reserved for the reviewer. These observations are scoped test evidence,
not an aggregate verification stamp or a landing approval.
