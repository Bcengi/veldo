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
