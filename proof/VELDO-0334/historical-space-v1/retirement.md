# VELDO-0334 superseded fixture retirement

Old source: `150_veldo_0334_space_wait.py.txt` in this folder, preserved for audit. Its APIs belong to the old stack; it is not an executable joined-tree suite.
Replacement: `scripts/suites/158_veldo_0334_space_freed.py`. Baseline implementation evidence: candidate 95851131e; see assembly-v1.md for the specific implementation commits.

Rows below preserve the required assertion through the named current row(s). Rows saying SUPERSEDED describe incompatible old contracts, not removed safety guarantees. Dynamic subrows remain in the archived source and are covered by their parent family. `setup` is fixture infrastructure, replaced with the current fixtures. Runtime results are recorded separately; this mapping alone is not a green receipt.

| Old row | Current assertion / disposition |
| --- | --- |
| `ac1/one-signal` | ac1/one-signal |
| `ac1/signal-can-admit` | ac1/retry-removes |
| `ac2/manual-free-timer` | ac2/timer-still-waits |
| `ac2/no-read-or-write` | ac2/no-read-write |
| `ac2/public-admit` | ac2/no-read-write |
| `ac3/backing-pool` | ac3/pool-only |
| `ac3/completion-race` | ac3/completion-race (157) |
| `ac3/free-during-judgment` | race/freeing-during-judgment |
| `ac3/nonfreeing` | ac3/nonfreeing-no-mark |
| `ac3/pool-isolation` | ac3/pool-only |
| `ac3/refusal-atomic` | race/own-version-refused |
| `ac3/release-replay` | replay/own-hold |
| `ac3/stopped-clock` | ac3/release-wakes |
| `ac3/waiting-set-race` | race/release-resent; race/resend-bounded |
| `compat/one-shot-adapter` | ac1/retry-removes |
| `fix1/act-refused-signal` | act/signal-refused-waits |
| `fix1/report-refused-signal` | report/signal-refused-advised |
| `fix2/release-marks-per-pool` | fix2/release-marks-per-pool |
| `fix2/waiting-release-no-mark` | fix2/waiting-release-no-mark |
| `fix3/requests-unrelated-passes` | fix3/requests-unrelated-passes (157) |
| `fix4/failed-read-rejudges` | fix1/failed-judgment (157) |
| `setup` | Current fixture setup, no behavioral assertion retired |

Old attempt-decrement, equal-attempt ordering, duplicate Requests API and composite ends_on representations are retired. The candidate uses monotonically distinct attempts, space_failure, current prepare and forms/FORM_ROWS. Candidate signed andon clearing and bounded waiter writes remain.

Historical home-directory strings in JSON receipts are redacted as `<historical-home>`; original bytes remain available at the pinned incoming Git revisions. Historical receipts never certify this joined tree.
