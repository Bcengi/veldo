# VELDO-0121 implementation and qualification

Owner go: Telegram 37209 and 37212, explicitly requested on 2026-10-28. Work starts
from main 59b119a1 on agent/codex/veldo-0121. This is the standalone Release 2 relay
qualification in PLAN-0019, using the existing VELDO-0108 transport. The direct and
transitive dependency specifications, plan and owner's remaining-inventory note
were read. No outside project code or package was used; all new code uses Python's
standard library.

The two byte-identical relay copies set one monotonic deadline before connect and
use its remaining time for each 64 KiB chunked sendall, write-half shutdown and
receive. A sendall that makes no progress times out within the budget and refuses. The final EOF and assembled
response must still fit the budget. Response bytes stay buffered until successful
completion, so errors, timeouts and size violations cannot leak partial output.

Final qualification is bound to input commit
`3b1a6f55` and the implementation and fixture digests in
`receipt-validation.json`. All four declared falsifiers turned their own row red,
then their restored controls returned green. Every drive was valid and complete.
The final suite passed all four ticket rows over 3304 cells. Real stalled and
trickle exchanges returned exit 3 with zero stdout in 30.043 and 30.014 seconds,
respectively, with zero surviving helpers. `check_receipts.py` independently
validated the committed source bindings, applied diffs, schedule identity equality,
expected/executed counts and red-then-green ordering. No protected path was touched.

## Checks and falsifiers

| AC | Named row under `relay/` | Qualification | Applied falsifier |
| :--- | :--- | :--- | :--- |
| AC1 | transport-errors-have-zero-stdout | 3180 generated error schedules and 11 actual kernel close/reset controls | Flush each received chunk before the next recv, then observe leaked bytes on a later reset |
| AC2 | eof-and-size-decisions-match-model | 96 normal EOF, empty echo, binary and size boundary schedules | Raise an endpoint error on clean EOF, refusing the successful empty response |
| AC3 | exchange-deadline-is-total | 15 accelerated stall/late-return/trickle schedules and two real 30-second CLI exchanges | Renew the deadline after each response chunk, allowing the trickle to succeed |
| AC4 | failure-does-not-replay | Independent connection and complete request counts for all 3180 error schedules and 11 native controls | Reconnect and resend after a receive error, observing two complete requests |

[MODEL.md](MODEL.md) defines the exact finite domain and the outcomes classified as
endpoint_error, endpoint_timeout, orderly_eof, request_too_large and
response_too_large. The fixture reconciles the production socket call set and fails
on an omitted applicable fault. The model does not claim all possible network
schedules, application-level truncation detection, SSH authentication, downstream
stdout failures or a general listener/process census.

The changed suite is registered with itself as its only suite prerequisite.
`suite.log` records the selected suite and dispatcher result. This partial selector
intentionally exits 2 even when its rows pass; that is not a full gate result.
The dispatcher's shared setup also prints its existing negative fixture diagnostics.
`suite-initial.log` retains an exploratory failure in the native EOF oracle: a close
at request offset 3 correctly returned zero response bytes, while the first oracle
incorrectly expected three response bytes. The oracle was corrected to use the
response prefix only at receive barriers; production was already correct.

`drive.py` runs only this ticket's four checks. For each AC it applies its specified
source mutation in memory, executes the entire criterion, requires the named row
false with a concrete behavioral witness, then discards the mutation and executes
the original source requiring the same row true. Crashes, watchdog expirations,
missing rows and incomplete schedules invalidate the drive. Mutations never modify
the working production files. The driver verifies committed inputs before testing
and refuses if the implementation or fixture changes during the run. `results/AC*.diff` retains the exact applied diffs;
`results/summary.json` retains each verdict and its first falsifier witness.
The full receipts are lossless gzip JSON in `results/AC*-red.json.gz` and
`results/AC*-green.json.gz`, readable with Python's `gzip` and `json` modules.
Each binds its input commit, implementation SHA-256, fixture SHA-256 and version.
Every cell includes its schedule digest, input identity, phase and byte offsets,
injected or actual OS outcomes, exact compressed stdout, exact stderr, exit,
latency, connection count and complete request identities. Expected and executed
counts and incomplete schedules are explicit.

## Reproduction and scope

Run the suite using Python 3 and `scripts/selftest.py` with the `suite` selector for
`113_veldo_0121_relay_exchange` (the selector takes two leading minus characters).
Run the falsifiers with:

```
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 proof/VELDO-0121/drive.py
```

The lock is blocking without a timeout. Only the caller takes this real lock; the
fixture itself has no host-lock operations. Single-file suite checks use the owner's
single-file exception. No broader suite, full gate, push or merge was run. All
endpoint helpers are joined and relay CLI children reaped. [OPEN.md](OPEN.md) records
no owner decision or spec contradiction. No protected path was touched.

Independent review, the later batch gate and landing are still separate steps.
These ticket observations make no claim that those steps ran.

The `earlier-attempt/` directory retains the first mutation run, excluded from final
qualification because it began on ba3bc5f5 while the final peer-byte guard was being
added. Receipt validation caught that stale fixture. The final run uses frozen
committed inputs and adds explicit input-stability checks.
