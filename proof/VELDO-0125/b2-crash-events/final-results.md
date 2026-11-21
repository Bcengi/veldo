# Final correction evidence

All seven requested corrections are implemented. The final selected routing suite
passed 141 rows and the relay suite passed 43 rows, with zero failures. These counts
include their prerequisite rows. Each selected suite exits 2 by design and declares
PARTIAL; neither result is a canonical gate or native macOS qualification claim.

All 23 distinct falsifiers were rejected with exit 1 and their intended failed row.
The supplemental set repeats the first two controls after the Python 3.11 pipe-wake
correction, then proves the native pipe and the preserved idle-timer assertion.
The complete mapping, source hashes and log paths are in verification.json.

The unchanged-code baselines are routing-consolidated.log and
relay-post-falsifiers.log. Earlier runs are retained, including protected temporary
path refusals and a synthetic fixture that initially omitted its live-index entry.
The fixture now writes the same index intent as production; its capacity assertions
were preserved. routing-corrected.log is an accidentally overlapping invocation
that was stopped on detection and is not used as passing evidence. Subsequent
suite and falsifier invocations were serial.

The lifecycle and event regression modules have new revisions so historical proof
records remain unchanged. Both now patch the worker-local sleep seam, and restoring
the global patch or an idle sleep causes the corresponding row to fail. The
0124 simulation fixture models blocking exit events. Its old heartbeat-loss row
still requires bounded termination, now at the runtime cap, as required by removal
of healthy-run heartbeat polling. Only the two owning 0125 suites were executed.

Engine and installed copies are identical. Commits use the configured Dmitry
Grinberg identity without trailers. The reviewer retains the full gate, merged-tree
stamp, independent review and native Mac/SSH qualification. No push was performed.
