# VELDO-0289 proof

Workers.finish keeps the worker's first error and detail when ownership cleanup, meter close,
or the final meter sample fails. Cleanup failures are stored in cleanup_error. When both cleanup
steps fail, the ownership failure comes first. A final sample failure is stored in measurement_error
when finish was handed an error. Cleanup failure keeps both grants until the existing stage abort
releases admission grants.

Suite 98 checks the receipt, the raised error, both cleanup steps, combined failures, and grant
retention. It also checks cancellation, bad exits, trace failures, and workers without an earlier
error. Its release-failed-cleanup mutation uses the new hold condition.

Suite 115's meter samples succeed in the run loop. The last sample fails after check_worker reports
the deadline. The row checks the raised error's identity and the outcome's detail. A second case
checks a sample failure without a handed error.

The new suite 101 row starts an unmetered worker in the fixture's unconfined leg. The worker makes a
directory in /dev/shm and exceeds its two-second deadline. The row checks that the ledger names the
directory, the worker was killed, the timeout remains the first error, and cleanup refuses the
directory. The fixture then removes its empty directory.

The proof runner executes only that new suite 101 function. It does not execute suite 101's other
functions, which invoke fixture gates. It uses the registered cleanup289-replaces-first-error
mutation for the integration red, and also checks the coordinator from 852f133b. The registered
teeth run the full suites 98 and 115.

The ownership guard and its engine copy are unchanged from 852f133b. The coordinator copies are byte
identical. The specification and its footprint were not edited after the ready spec merge.

All repeated checks and teeth use the shared lock through host_heavy.sh. One preliminary run of each
offline suite used a systemd user scope with MemoryMax=10G. These are selected checks, not a complete
repository verification. The gate, verify.sh, and policy_check.py were not run.

Built through 160c338e4e7f9bada7a273d0540c23388985b3cb. The combined proof run completed under
host_heavy.sh with exit 0. Run it with:

```
bash /home/dmitry/projects/myday/scripts/host_heavy.sh python3 proof/VELDO-0289/check.py all
```

- Suite 98 receipts/deadline-then-cleanup-failure is red under cleanup289-replaces-first-error.
  Its baseline and no-op controls are green.
- Suite 115 admission/deadline-then-sample-failure is red under measure289-replaces-first-error.
  Its baseline and no-op controls are green.
- Suite 101 ownership/timeout-then-cleanup-failure is red on 852f133b and under
  cleanup289-replaces-first-error. It is green on the current coordinator.

The teeth summary reports two registered, two executed, two rejected, zero reused, and six worker
invocations. Its result array was discarded after hashing. Unit evidence for AC1 comes from those
controls and named mutation detections. The selected selftest runs are diagnostics: suite 98 had
46 passing rows, suite 115 had 31, and neither had failures. Both returned the expected partial-run
exit 2. The suite 98 release-failed-cleanup checks passed for both entry points.

The integration summary shows worker_cleanup_error on 852f133b and under the cleanup mutation.
The current coordinator raises mutation_budget_exceeded with the detail "late: worker deadline
(2s)" and stores the guard's refusal in cleanup_error. Every case recorded its directory in the
ledger, was killed with SIGKILL, retained its resource slot, and left the directory intact for the
fixture to remove.
