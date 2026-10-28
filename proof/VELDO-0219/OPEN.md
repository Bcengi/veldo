# VELDO-0219 batch qualification contract

Status: REMAINING for canonical qualification. Owner rule 37191 defers both
VELDO-0216 and VELDO-0219 AC4 to the batch gate. No canonical gate was run during
this round. The approved VELDO-0216 amendment at 18e375b0 measures its target with
VELDO-0219, without VELDO-0221. The landing candidate must contain both tickets.

The batch gate must retain commit-bound canonical receipts and demonstrate:

1. One full force-fresh canonical gate on the qualification host, with 20 usable
   cores, 31 GiB host memory and the 16 GiB delegated gate scope. The host is quiet
   and the blocking lock at /home/dmitry/.local/state/core-gates/.gate.lock stays
   held throughout. Both unit and mutation reuse counts are zero; stamp, event,
   graph digest, schedule and mutation receipt identify the same landing candidate.
2. The complete gate finishes in at most 6,000 seconds, against VELDO-0216's
   10,718.803 second serial baseline. Record every node's start, end, verdict,
   CPU seconds and peak anonymous memory, the measured critical path, manager
   waits, ledger capacities and peak granted totals. Compare every node with
   proof/VELDO-0216/serial-baseline.json, retaining interval bounds for short
   baseline stages and labelling its historical memory as cache-inclusive.
3. VELDO-0219's mutation stage separately meets its unchanged 4,000 second target
   against 5,207 seconds. Enumerate the current registry rather than assuming
   the historical 2,689 cases. Execute and account for every case and its required
   controls. Require zero worker deadline expiries, zero invalid baselines,
   zero survivors and unchanged verdicts. Record stage elapsed time, peak workers,
   mean busy cores, sampled anonymous peak and conservative final-accounting
   memory bounds. Record every case's elapsed time, enforced deadline, quiet
   measurement and slowdown, plus claim provenance, gate totals and the blocking
   resource for each wait. qualification.py checks this mutation capture.
4. A matched fixed-sixteen canonical falsifier at the same candidate, on the same
   quiet locked host, changes only the measured worker ceiling to 16. It must
   fail the mutation 4,000 second check while preserving verdicts and deadlines;
   the prior 5,207 seconds is a comparison, not substitute evidence. Retain the
   full receipts even if the full gate still happens to meet 6,000 seconds.
5. VELDO-0216's matched serialized canonical falsifier must exceed 6,000 seconds
   and fail the critical path check. Keep host capacity and worker admission
   otherwise identical. A simulation or synthetic checker result cannot qualify
   either timing claim or either canonical falsifier.

Round two closes the aggregate handoff, unmetered worker cap, cross-run CPU claim
and refusal-resource defects. The mutation root atomically shrinks to the graph's
coordinator overhead, using its fresh measured need when available, releases manager exclusion, and retains its floor and host
lock claim until children finish. Per-case replies supply actual capacities,
remaining floor, totals and refusal resource. See round2/ for red and green checks.

Unit registration now waits for authority retention before launch. Owned slices
remain loaded; owned services use a private accounting parent. Kernel parent CPU
counters survive short-lived child teardown, and final manager accounting is read
around explicit stops and restarts. Invocation changes accumulate distinct CPU
runs. Unit placement does not change candidate code or the unit's own limits.
Anonymous memory remains sampled. A separate kernel total-memory peak supplies a
conservative admission bound for brief allocations missed by those samples; it is
stored as peak_memory_bytes, never relabelled as measured anonymous memory.
The native short-unit and installed-service checks prove these lifecycle paths.

Inherited VELDO-0220's missing suite 113 userbus declaration remains owned by that
ticket. This round does not edit scripts/gate_unconfined.json. The batch candidate
must carry that resolution before running its canonical suite.

## Scope amendment, 2026-10-28, pending owner approval

Owner approval remains pending for the VELDO-0219 changes to VELDO-0216's
protected files. No owner approval is claimed or message id invented. The
VELDO-0219 spec now lists these three paths in both footprint and
protected_paths; listing them does not grant approval. The implementation
record's earlier word "authorized" was unsupported and has been removed.

The following inventory names every changed new-side hunk at 822b69e2 relative
to f5b06f94's parent, before the handoff changes. Round three does not change
these three files. Exact old and new lines are retained in
`round3/protected-paths.diff`.

Both `scripts/gate_schedule.py` and `engine/scripts/gate_schedule.py` have the
same changes at these lines:

| Lines | Why the protected code changed |
| --- | --- |
| 77; 85 to 90 | Accept and validate a coordinator claim only on the mutation node; disallow retained manager exclusion. |
| 103 to 105 | Refuse coordinator overhead that consumes the entire reserved mutation floor. |
| 138; 168; 179; 185; 190 | Track and report the actual resource refusing admission, including host lock and ports. |
| 201 to 213 | Atomically shrink the root claim before children exist, release manager exclusion, and preserve ports, host lock and floor lifetime. |
| 243; 250 to 253 | Preserve the ledger reply and expose the client handoff operation. |
| 288 to 289 | Reserve at least the graph's coordinator overhead at startup. |
| 451; 459 to 467 | Retain measured coordinator overhead when available and reject overhead that exhausts the floor. |
| 528 | Track whether each node has handed off its claim. |
| 552 to 561 | Accept one valid mutation handoff and refuse worker acquisition before it. |
| 571 to 575 | Return capacities, granted totals, refusal resource and the floor net of coordinator overhead. |

`scripts/gate_graph.json`, lines 145 to 151, adds the mutation coordinator
claim: 0.25 CPU, 268435456 bytes, no manager hold or ports, and a shared host
lock. The aggregate root can therefore transfer worker resources while
retaining explicit coordinator overhead. These changes originated in
f5b06f94, 6a469e3a and f13bc619, not in an approved VELDO-0216 revision.

The earlier ea60f2d7 edit to `proof/VELDO-0216/OPEN.md`, lines 14 to 20,
replaced a stale standalone timing statement with the joint batch qualification
contract and its deferred AC4 status. This path is now in VELDO-0219's
footprint. It is a proof cross-reference, not one of the three protected
implementation paths above. Approval of VELDO-0216's separate .gitignore
footprint also remains with its owner.

## Memory claim, 2026-10-28, AC1 difference

AC1 describes the memory claim as the largest measured anonymous peak in the
window. `scripts/check_gate_mutations.py`, lines 277 to 279, and its identical
engine copy instead select the maximum of `peak_anon_bytes` and
`peak_memory_bytes` across those runs. The latter is the retained units' kernel
total-memory peak and includes page cache. Anonymous memory remains separately
measured and labelled; the total-memory bound is not an anonymous measurement.

The reason for retaining this conservative difference is that polling can miss
a short-lived unit's anonymous allocation before teardown. Its final kernel
peak remains available and prevents admission from treating that missed
allocation as free memory. Changing the claim to sampled anonymous memory alone
would remove the short-unit protection tested by admission/final-memory-bound.
This explanation records the difference without changing AC1 or claiming its
literal memory wording is satisfied. Owner acceptance of a spec amendment, or
a revision that measures the required anonymous peak, is pending owner approval.
