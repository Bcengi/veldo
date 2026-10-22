# WARP-1404 AC5 additional audit events

Scope: test suite and embedded audit driver only, based on `6720690e`.
Product code and earlier proof files are unchanged.

The WRITES tuple now includes `os.killpg`, `socket.sethostname`,
`ctypes.dlopen`, and `ctypes.call_function`. All four are listed in the
[CPython 3.12 audit events table](https://docs.python.org/3.12/library/audit_events.html).

Each new row injects code into the scratch copy of `.veldo/estimate.py`.
The `toe_analogy.py` AST allowlist remains satisfied, so the audit event must
detect the operation. Every injection requires its own named event and a
complete driver report. Every restoration runs in a fresh process and requires
both strict audit buckets to be empty. All existing rows are retained.

The signal row calls `os.killpg(os.getpgrp(), -1)`. The invalid signal cannot
be delivered. The hostname row supplies 65,536 bytes, exceeding the kernel
hostname limit. Both emit their real audit event before failing with OSError;
an unexpected success raises AssertionError. Neither relies on a synthetic
event or changes the machine.

The ctypes rows import ctypes from the audited dependency and call libc's
harmless `getpid`, checking the result against `os.getpid()`. The first uses
`ctypes.CDLL(None).getpid()`, exercising `ctypes.dlopen`. Ordinary CDLL
function calls need not emit `ctypes.call_function`, so the second calls
`_ctypes.call_function` with the real getpid function pointer and requires
that specific event even though loading the library also emits dlopen.
These rows demonstrate foreign calls without relying on an OS write event.

The same selected suite, `15_warp_1404_historical_analogy`, runs before and
after the tuple change on Linux CPython 3.12.3. Raw logs and exit statuses
are saved alongside this file. No full gate or other suite was run.

The baseline at `932e46b2` contains all four new falsifier pairs with the
original tuple. It reports 71 selected-suite passes and 4 failures, or
97 passed and 4 failed including shared setup, in 280.59 seconds, exit 1.
Exactly the four new event assertions fail. All four injected reports are
complete but incorrectly AC5 green, with no recorded strict event. Every
restoration, all existing rows and all three cache controls pass.

The tuple fix is committed as `8fc904e3`.

The final run at that commit reports 75 selected-suite passes, or 101 passed
and 0 failed including shared setup, in 281.20 seconds. Exit 2 is the
dispatcher's successful partial-run status, not an aggregate gate result.
All existing rows and all three cache controls pass: cold read-only,
cold writable, and warm. The prior import writer and import spawn rows pass.

The four new injection/restoration pairs have these measured results:

| Case | Events during injection | AC5 injected | AC5 restored |
| :--- | :--- | :--- | :--- |
| os.killpg | os.killpg | red | green |
| socket.sethostname | socket.sethostname | red | green |
| ctypes.dlopen | ctypes.dlopen twice | red | green |
| ctypes.call_function | ctypes.dlopen twice, ctypes.call_function | red | green |

Every restoration has empty strict event buckets. Both runs have 34 complete
driver reports: two cache baselines plus 16 injection/restoration pairs.
`event-results.json` extracts the case, phase, completeness, AC5 result and
strict event lists from both raw logs. The final evidence shows all 16
injections rejected and all 16 restorations green, with all eight drives,
the CLI path, the AST allowlist and the read-only git spawn allowance intact.

This is scoped regression evidence. The reviewer runs the full gate and
mutation runners separately and owns the final verification stamp.
