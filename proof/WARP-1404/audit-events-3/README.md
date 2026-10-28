# WARP-1404 AC5 ctypes import audit gap

This is a test-only follow-up to `f21e2a00` on the assigned persistent branch
`agent/codex/fix-warp1404-ctypes-import`. Product code and earlier proof files
are unchanged. No other branch or worktree was changed.

The shared audit hook now records generic `import` events for `ctypes`,
`_ctypes`, and their dotted submodules. This rule applies to all four active
windows: import, pure, repo, and cli. Imports enter the strict event buckets
before the separate process allowance. Unrelated imports remain unaffected.

WRITES also includes `ctypes.dlsym`, `ctypes.dlsym/handle`, and `ctypes.cdata`.
Each spelling and its arguments were checked against the
[CPython 3.12 audit events table](https://docs.python.org/3.12/library/audit_events.html).
The checked entries are recorded in `event-name-check.json`.

Four new falsifier pairs append operations to the scratch copy of
`.veldo/estimate.py`, leaving the analogy module's AST allowlist satisfied:

| Case | Operation | Required strict event |
| :--- | :--- | :--- |
| Raw address call | Import only `_ctypes`, construct C scalar and function pointer types, call `_memmove_addr` with valid byte strings and zero length | `import _ctypes` |
| Symbol lookup | Resolve and call libc `getpid` through CDLL | `ctypes.dlsym` |
| Handle lookup | Resolve `getpid` through `_ctypes.dlsym`, build a function pointer, call it | `ctypes.dlsym/handle` |
| Raw memory view | Read a live owned integer through `c_int.from_address` | `ctypes.cdata` |

The raw call copies no bytes and requires every recorded strict event to be
`import _ctypes`; another ctypes event cannot make that row pass. Both getpid
rows check the actual process id, and the memory row checks the owned value.
Each injection requires a complete eight-drive report and its specific event.
Each restoration starts a fresh interpreter and requires both strict buckets
to be empty. Every existing row and all three cache controls are retained.

The falsifiers were committed first as `9fee6ad2`, before the hook fix.
`before.txt` records the selected suite on Linux CPython 3.12.3: 79 passed
and 4 failed in the selected suite, or 105 passed and 4 failed including
shared setup, in 337.46 seconds. Exit status was 1. Exactly the four new
event assertions failed. The raw-address injection completed with no strict
event and incorrectly green AC5. The other three injections already recorded
dlopen, but none recorded the newly required name. All restorations, existing
rows, and three cache controls passed.

The hook fix was committed as `172caf7f`. `after.txt` records 83 passed and
0 failed in the selected suite, or 109 passed and 0 failed including shared
setup, in 319.58 seconds. Exit status was 2, the dispatcher's successful
partial-run status. Every existing row and all three cache controls passed.

All four new injected rows now make AC5 red with their required event, then
green after restoration. The raw-address row records exactly two
`import _ctypes` events and no ctypes event. The other rows each record their
own new event, in addition to import and loader events. `import ctypes._endian`
is also observed, demonstrating the dotted-submodule match with a real import.
Every one of the 42 reports in each run is complete. The 20 restorations per
run all have empty strict buckets. `event-results.json` extracts the reports'
case, phase, completion, AC5 outcome, and strict events for comparison.

Only `15_warp_1404_historical_analogy` was selected for these runs. The full
gate and independent review remain the reviewer's responsibility under the
owner's instructions. These partial-run results make no aggregate gate claim.
