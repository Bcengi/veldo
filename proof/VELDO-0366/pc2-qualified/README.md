# Fresh pc2 qualification and bounded batch, 2026-11-25

Authority: speed-pc2 `925f162e81ae647c74d5e10b020778b655b8d60b`.
Every workload used the exclusive pc2 target of the personal remote runner and
explicit `/usr/bin/python3 -I -S`. No pc1 workload was started.

Fresh six-probe qualification: **all passed**.

| Probe | Result |
| --- | --- |
| delegation | Passed: cpu/memory/pids controllers, actual worker membership and accounting, cgroup removed |
| landlock | Passed: allowed read/write, refused ungranted read/write, confined child interpreter started |
| namespaces | Passed: namespace helper self-test |
| ptrace | Passed: actual child file read observed |
| pidfds | Passed: live child and exit readiness |
| toolchain | Passed: all eight required worker-visible tools, runtime identity recorded |

The unchanged phase-1 selection executed 100 cases, rejected all 100, reused zero,
and left zero invalid results or surviving workers. All 136 workers cleaned up;
peak concurrency seven; ledger empty; private batch scratch removed. Stage time
283.222689748 seconds. Scope peak memory 1,375,424,512 bytes; OOM and throttling
counters zero. Both the standalone and batch qualification receipts are retained.

**Gate 15 comparison: exact 100/100.** The existing strict comparator passes all
checks, including complete case definitions, mutation digests, replacement counts,
named verdicts and every baseline/no-op/mutant observation. This includes the
previously discrepant signing case. Gate 15 itself was not a green full gate;
its completed selected records are the comparison baseline.

**Gate 18 comparison: not fully green.** At the read-only snapshot, 98 selected
mutants and all 36 controls had completed. Their mutation identities, green
controls and named target-row kills agree. Full observations agree for 97/98.
`signing-truncated-clock` differs at `VELDO-0027 signing/rotation-race`: gate 18
reported true and this pc2 run reported false. Its named transition-clock kill
agrees. No observation was normalized or waived. The two review-driver cases
`14` and `17` had not launched, so no gate-18 comparison exists for them.
The gate-18 signing fixture differs from this authority; this evidence records
the difference without claiming an independently established cause.

Gate 18 is still running. Its final stage receipt was empty, so this comparison
uses completed raw worker outputs bound to the running gate's commit and the
zero-based launch order in its ledger log. Each selected mutant's old/new digest
and replacement count independently matches. These are partial worker evidence,
not a finished or authenticated gate-18 stage receipt. Source paths, snapshot
hashes, grant order, raw outputs and the exact signing difference are retained.

`compare.py` reproduces both comparisons. `comparison.json` records each case.
Logs record exact remote invocations and successful wrapper cleanup. This
six-probe qualification is not the session-specific distributed qualification
and does not establish wider-catalog readiness or full-gate acceptance.
