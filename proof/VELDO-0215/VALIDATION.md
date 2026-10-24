# VELDO-0215 validation

Implementation commit: `45c714d2db159f139482da3f12aed02da334f3af`.

This is a validation record, not a human approval or independent review.

## Design

The worker allowance is `min(1800, max(120, 3 * seconds))`. Seconds are the maximum
coordinator-observed baseline, no-op and mutant duration for that case in the last passing
fresh, input-stable stage. Shared controls use the largest member allowance. The combined
budget is the larger of the previous inventory/worker-count cap and 120 seconds plus the
sum of the actual job allowances, covering resource admission that serializes jobs.
Inventory and Git setup subprocesses retain their separate 120-second bound; their expiry
is also reported as a timeout.

Only the authority CLI enables owner-store recording, including a candidate in another root.
Workers never record; library and fixture runs default to no owner-store writes. Atomic
files live in `~/.cache/veldo/mutation-case-seconds`. The SHA-256-derived key binds the
authority checkout, full case definition, suite, target, shared harness, execution helpers
and confinement declaration. HEAD and unrelated proof documents are not key inputs.
VELDO-0214 pruning removes files older than 30 days or belonging to a gone checkout,
including abandoned pending files, and preserves the current file and foreign names.

## Rows

| Row (case-deadlines/) | Assertion |
| --- | --- |
| bounds | Missing, malformed and extreme samples use the floor or hard ceiling. |
| key-binding | Changed definitions and direct execution inputs do not inherit samples. |
| shared-controls | Shared baseline/no-op jobs receive the largest member deadline. |
| combined-budget | The stage cap accommodates serialized job deadlines. |
| setup-timeout | An inventory subprocess timeout is mutation_budget_exceeded. |
| measured-worker | The selected 240-second allowance reaches actual worker admission/checking and the stage alarm. |
| slow-pass | A controlled 150-second worker passes beyond the 120-second floor. |
| hang-timeout | Hanging baseline, no-op and mutant jobs expire once, are cleaned up and report timeout. |
| baseline-details | Completed false control rows remain invalid_baseline and retain their own explanation. |
| authority-recording | Only passing, fresh authority runs write; failures, input races, reuse and fixture drives do not. |
| candidate-authority | The authority CLI records when the candidate has another root. |
| store-pruned | Gone and stale files are removed; current, live and foreign files remain. |
| real-hang-reaped | An actual sleeping OS process is killed and reaped at the worker deadline. |

## Registered mutations

All 16 were killed in the final affected-finding run.

| Mutation (deadline215-) | Required false rows |
| --- | --- |
| timeout-is-baseline | hang-timeout |
| no-authority-guard | authority-recording |
| key-omits-sources | key-binding |
| key-omits-definition | key-binding |
| no-prune | store-pruned |
| old-stage-cap | combined-budget |
| first-control | shared-controls |
| no-ceiling | bounds |
| lost-baseline-details | baseline-details |
| record-invalid | authority-recording |
| setup-timeout-is-driver-error | setup-timeout |
| candidate-authority-not-recorded | candidate-authority |
| stage-drops-authority | authority-recording |
| fixed-worker | measured-worker, slow-pass |
| drop-measurement | measured-worker, slow-pass |
| no-expiry | hang-timeout |

## Timeout investigation

At base `2eb9c2be`, `check_worker()` raises `mutation_budget_exceeded`. `Workers.run()` passes
it to `finish()`, which kills/reaps the process and raises that error. A timed-out control never
enters `control_results`, so it cannot reach `validate_result()` as a completed baseline.
`invalid_baseline` is emitted there only for completed false baseline rows or unequal no-op
observations. The historical report therefore was not a coordinator deadline relabeled as a
baseline failure. Its original detail did not identify the false rows, so their exact cause
cannot be reconstructed from that report alone. The new detail carries both controls' failed
rows and explanations. Uncaught inventory subprocess expiry also now has the timeout code.

Both reported cases passed in the final targeted run, without retry inside the coordinator:

| Case | Mutant seconds | Enforced seconds |
| --- | --- | --- |
| receiver148-setup-clock-before-release | 67.824 | 120.000 |
| claude-completion-gate-exit-only | 36.444 | 120.000 |

The targeted run recorded 67.824 seconds for the receiver case, selecting 203.471 seconds
for its next worker. The Claude case remains at the 120-second floor. A live store inspection
during the full unit stage found the same 330 records present after targeted validation,
all bound to this checkout: the count had not grown during the unit fixtures.

## Gate

GREEN at `45c714d2db159f139482da3f12aed02da334f3af` (exit 0).

Command:

```sh
systemd-run --user --wait --collect --pipe \
  --working-directory=/home/dmitry/projects/veldo-worktrees/mutation-case-deadlines \
  -p MemoryHigh=14G -p MemoryMax=16G -p OOMScoreAdjust=900 \
  bash scripts/verify.sh
```

The complete gate log and final targeted receipt are retained as gzip artifacts.
The targeted run used the same systemd limits and findings 60, 148, 215, 123, 204, 210 and 214;
106 cases executed and were killed, with no invalid results or surviving workers.

Standalone suite runs are diagnostics only (the dispatcher deliberately exits 2 for a
partial run). The six existing mutation/resource/reuse suites plus the new suite passed
230 rows before the final authority-entry refinement. The final standalone new suite passed
13 own rows plus 26 shared rows. The full gate above is the canonical result on the final code.


The full mutation stage executed and rejected all 2,569 registered cases with 16 workers,
zero reused results, zero invalid results and zero surviving workers. All 16 new mutants
were killed. It took 4,893.54 seconds; 32 case deadlines exceeded the floor. The receiver
case used its measured 203.471-second allowance and passed in 68.596 seconds; the Claude
case passed in 35.337 seconds with the 120-second floor. No real worker in this run exceeded
120 seconds; the controlled slow-pass row supplies that boundary proof.

The full unit legs passed 7,747 confined and 871 unconfined rows. Both integration legs and
all remaining gate checks passed. The service ran for 2h 50m 30.271s, with 13.6G peak memory.
There are no red full-gate failures to classify against the base.

The existing diagnostic suites were 53_veldo_0123_mutations, 97_veldo_0204_gate_resources,
98_veldo_0204_mutation_receipts, 99_veldo_0205_reuse, 100_veldo_0207_case_reuse and
104_veldo_0210_mutation_workers, together with the new 112_veldo_0215_case_deadlines.
A separate read-only anchor audit applied all 2,569 registered mutations without errors.


Protected paths touched: `scripts/check_gate_mutations.py` and its identical engine copy,
`engine/scripts/check_gate_mutations.py`. The spec requires human approval for landing; none
was authored. All commits use Dmitry Grinberg <dmitry@bcengi.com>, with no co-author trailer.
No branch was switched and nothing was pushed.
