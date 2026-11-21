# Brief C restatements

Authorized by the lead's two scope decisions following cb0c3da3 and 76d4069b.
The contracts are unchanged. Historical row labels stay, even where their names
refer to a budget that is now only an admission estimate.

| File | Row or fixture | Why |
| --- | --- | --- |
| scripts/suites/53_veldo_0123_mutations.py | gate/mutation-stage-budget-is-enforced | Progress permits arbitrarily long work; three supplied seconds of inactivity refuse it. The real process termination and stack check is in suite 112. |
| scripts/suites/53_veldo_0123_mutations.py | gate/mutation-budget-scales-with-inventory | Inventory affects the estimate, while the worker deadline is absent and no stage alarm is armed. |
| scripts/suites/53_veldo_0123_mutations.py | gate/mutation-results-have-teeth | A nonzero no-op control exit is control_failed; it remains a stage error, never a kill. |
| scripts/suites/53_veldo_0123_mutations.py | gate/workers-follow-the-host | Pipe latches replace fixture pacing and sleeping holders; host affinity, quota and actual concurrency assertions stay. |
| scripts/suites/53_veldo_0123_mutations.py | hanging worker fixture | Pipe latches replace fixture pacing and sleeping holders; host affinity, quota and actual concurrency assertions stay. |
| scripts/suites/97_veldo_0204_gate_resources.py | gate/resources-workers | Supply completion events at the process boundary instead of a sleep poll; reservation, fairness, cleanup and failure assertions stay. |
| scripts/suites/97_veldo_0204_gate_resources.py | gate/resources-failure-cleanup | Supply completion events at the process boundary instead of a sleep poll; reservation, fairness, cleanup and failure assertions stay. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-None | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-empty | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-nonobject | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-exit | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-spawn | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-deadline | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-receipt-cleanup | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-None | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-empty | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-nonobject | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-exit | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-spawn | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-deadline | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-receipt-cleanup | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-siblings | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-completed-siblings | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-planted-discarded-sibling | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-siblings | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-completed-siblings | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-planted-discarded-sibling | Inactivity replaces a measured deadline; completed results and sibling cleanup still survive the failure. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/gate-planted-queued-deadline | The new launch-clock seam must exclude queued time from measured worker time. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/teeth-planted-queued-deadline | The new launch-clock seam must exclude queued time from measured worker time. |
| scripts/suites/98_veldo_0204_mutation_receipts.py | stall/killed-owner | Ready and release pipes replace a sleeping holder and a readiness poll; SIGKILL must still leave an actionable ownership ledger. |
| scripts/suites/99_veldo_0205_reuse.py | reuse/deadline-stays-red | There is no asynchronous stage alarm. A cached record that claims a hung kill must grant neither reuse nor publication. |
| scripts/suites/100_veldo_0207_case_reuse.py | case/sandbox-valid-worker | Compare the stored receipt after the validator adds the required kill evidence; confinement, read tracing and scratch cleanup checks stay. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use/watchdog-is-not-preexisting | Even a completed summary cannot make a later watchdog exit an ordinary differential failure. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/measured-budget-used | Each nested run uses the progress bound and has no total timeout, whatever measurement is handed in. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/ceiling-caps-the-budget | Each nested run uses the progress bound and has no total timeout, whatever measurement is handed in. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/non-finite-budget-refused | Each nested run uses the progress bound and has no total timeout, whatever measurement is handed in. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/candidate-set-value-ignored | First-use verdicts no longer consume measurements; the runner's provenance, stale-measurement and candidate-input checks remain. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/reused-stage-uses-last-fresh | First-use verdicts no longer consume measurements; the runner's provenance, stale-measurement and candidate-input checks remain. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/by-hand-uses-1800-and-says-so | First-use verdicts no longer consume measurements; the runner's provenance, stale-measurement and candidate-input checks remain. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/installed-authority-under-temp-is-measured | A supplied clock gives the fixture a nonzero rounded measurement without sleeping; measurement handoff checks remain. |
| scripts/suites/111_veldo_0214_first_use_budget.py | first-use-budget/stage-runner-hands-the-matching-leg | A supplied clock gives the fixture a nonzero rounded measurement without sleeping; measurement handoff checks remain. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/measured-worker | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/slow-pass | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/hang-timeout | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/unmeasured-slow-baseline | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/unmeasured-mutant-deadline | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/unmeasured-hang | Estimates cannot end or retrospectively fail a worker. Only absent progress can. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/setup-timeout | Setup hangs and failed controls use the new taxonomy; a real blocked child must dump its stack and be reaped. Readiness is emitted from inside the blocking call, so sampling its source line does not depend on scheduling. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/baseline-details | Setup hangs and failed controls use the new taxonomy; a real blocked child must dump its stack and be reaped. Readiness is emitted from inside the blocking call, so sampling its source line does not depend on scheduling. |
| scripts/suites/112_veldo_0215_case_deadlines.py | case-deadlines/real-hang-reaped | Setup hangs and failed controls use the new taxonomy; a real blocked child must dump its stack and be reaped. Readiness is emitted from inside the blocking call, so sampling its source line does not depend on scheduling. |
| scripts/suites/112_veldo_0215_case_deadlines.py | verdict/kill-by-evidence | New Brief C acceptance rows, including a stage beyond 21,600 supplied seconds and a ten-line heavy child under a three-second progress bound. A ready descriptor above fd_set is also awaited without refusal. |
| scripts/suites/112_veldo_0215_case_deadlines.py | verdict/slow-is-not-red | New Brief C acceptance rows, including a stage beyond 21,600 supplied seconds and a ten-line heavy child under a three-second progress bound. A ready descriptor above fd_set is also awaited without refusal. |
| scripts/suites/112_veldo_0215_case_deadlines.py | watchdog/progress-not-total | New Brief C acceptance rows, including a stage beyond 21,600 supplied seconds and a ten-line heavy child under a three-second progress bound. A ready descriptor above fd_set is also awaited without refusal. |
| scripts/suites/112_veldo_0215_case_deadlines.py | host/holders-from-descriptor | New Brief C acceptance rows, including a stage beyond 21,600 supplied seconds and a ten-line heavy child under a three-second progress bound. A ready descriptor above fd_set is also awaited without refusal. |
| scripts/suites/112_veldo_0215_case_deadlines.py | timers/table-profile | New Brief C acceptance rows, including a stage beyond 21,600 supplied seconds and a ten-line heavy child under a three-second progress bound. A ready descriptor above fd_set is also awaited without refusal. |
| scripts/suites/115_veldo_0219_measured_admission.py | admission/measured-per-case | Explicit completion events replace polling-only doubles. Receipts report estimates and control_failed; resource claims and measurement checks stay. |
| scripts/suites/115_veldo_0219_measured_admission.py | admission/same-verdicts | Explicit completion events replace polling-only doubles. Receipts report estimates and control_failed; resource claims and measurement checks stay. |
| scripts/suites/115_veldo_0219_measured_admission.py | admission/stage-receipts-and-recording | Explicit completion events replace polling-only doubles. Receipts report estimates and control_failed; resource claims and measurement checks stay. |
| scripts/suites/115_veldo_0219_measured_admission.py | coordinator process fixtures (exercise and stage_run) | Explicit completion events replace polling-only doubles. Receipts report estimates and control_failed; resource claims and measurement checks stay. |
| scripts/check_teeth_mutations.py | VELDO-0358 BRIEF C block | Contains this brief's registrations together, including preserved measurement and provenance falsifiers. |
| scripts/suites/115_veldo_0219_measured_admission.py | admission/qualification-capture | A stage beyond 21,600 supplied seconds and workers above their estimates pass; hung evidence, missing measurements and malformed captures remain refused. |
| proof/VELDO-0219/qualification.py | check and fixture | Remove the 4,000-second total cutoff and elapsed-versus-budget verdict; retain resource measurements, complete outcomes, commit binding, host custody and positive measurement checks. Report estimates as data. The existing host path is constructed from the home lookup instead of a committed personal literal. |
| proof/VELDO-0219/local_check.py | synthetic elapsed/worker comparison | Both complete synthetic captures pass regardless of elapsed time; historical recorded captures are unchanged. |

Retired registrations (their target code was removed):

- budget214-fixed-1800-restored: the measured nested-run budget expression is gone.
- budget214-main-drops-the-budget: neither nested call site accepts a budget.
- deadline215-fixed-worker: no worker compares elapsed runtime with a measured deadline.
- deadline215-no-expiry: the same removed comparison cannot be disabled.
- deadline215-timeout-is-baseline: the measured-deadline refusal no longer exists.
- deadline215-setup-timeout-is-driver-error: the old mutation_budget_exceeded mapping is gone.

Replacements exercise firstuse358-total-budget, verdict358-measured-time-kills,
wait358-child-watchdog-silent, wait358-child-watchdog-total-time and the new
verdict matrix. Registrations whose measurement or provenance targets still
exist are retained. deadline285-no-same-stage-derivation now targets the row
that observes the same-stage estimate rather than requiring an expiry verdict.
