# Selective first use working notes

This is a partial validation record, not gate evidence or a landing approval.

The implementation records syscalls during the existing unit invocation, using the unique
current gate receipt and its leg to scope observations. It follows child processes, observes
metadata and directory reads, and binds the result to the source contents. First use compares
pristine and mutated inventories, selects observed readers, and adds their prerequisite closure.
Because fragments share mutable Python state, potential influence also propagates to later
fragments. This conservative propagation may limit or eliminate savings on this tree.

Missing observations, unavailable tracing and inventory failures use the existing full nested
run. Individual incomplete observations, namespace changes, shared filesystem threads and gate
inputs select reruns. Baseline attribution stays lazy. Every failing row remains named.

## Focused checks

The suites ran sequentially. Counts include 26 shared harness assertions where a summary exists.

| Suite | Result | Elapsed |
| :--- | :--- | :--- |
| 103, first use reads | 57 passed, 0 failed; 31 belong to the new suite | 0.16 s |
| 98, mutation receipts | 71 passed, 0 failed | 0.49 s |
| 99, reuse | 54 passed, 1 failed | 1.72 s |
| 101, landing reuse | Aborted before summary; 1 failing row printed | No complete timing |
| 102, agent profile runtime | Aborted before summary; 16 failing rows printed | No complete timing |

Suite 99 failed the worker and child store access row because the sandbox broker was unavailable.
Suite 101 printed the planted suite publication failure and then aborted on a denied pseudo
terminal operation. Suite 102 reported confinement and launcher failures, then aborted when the
host denied a Unix socket. These suites were not edited to accommodate the environment.

The host refused ptrace. Live syscall fixtures could not execute; recorded syscall parsing,
selection, child attribution, directory listings, metadata, resumed syscalls, alias descriptor
resolution, missing and stale observations, incomplete traces, full fallback and the original
spend emptiness regression were exercised. The real sanctioned writer regression was driven in
an isolated miniature repository through the check's copy, writer, verdict and lazy baseline
flow. Its assertion newly failed after spend was recorded, and the check returned failure.

## Timing and selection limits

The owner supplied the earlier gate 0210d integration measurement: approximately 1165 seconds
confined plus 754 seconds unconfined, totaling 1919 seconds. That measurement was not rerun here.

There is no new end to end timing or observed real suite selection from this sandbox. Tracing is
unavailable, so this host must rerun all suites through the fallback. The owner forbids a full
selftest, including the nested full run needed in that condition. Clarification was requested;
no authorization to run it was received. No speedup is claimed.

The reviewer still needs a real gate run on a host that permits observation, the named rerun and
kept suite report from that run, comparison of wall times including observation overhead, and the
checks that require host capabilities absent here. The prerequisite closure behavior remains the
existing dispatcher's contract; this work does not establish a new equivalence proof for those
closures. The branch is for owner review, with no push or merge.
