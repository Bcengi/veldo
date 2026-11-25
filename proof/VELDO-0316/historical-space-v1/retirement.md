# VELDO-0316 superseded fixture retirement

Old source: `150_veldo_0316_admission.py.txt` in this folder, preserved for audit. Its APIs belong to the old stack; it is not an executable joined-tree suite.
Replacement: `scripts/suites/157_veldo_0316_space_admission.py`. Baseline implementation evidence: candidate 95851131e; see assembly-v1.md for the specific implementation commits.

Rows below preserve the required assertion through the named current row(s). Rows saying SUPERSEDED describe incompatible old contracts, not removed safety guarantees. Dynamic subrows remain in the archived source and are covered by their parent family. `setup` is fixture infrastructure, replaced with the current fixtures. Runtime results are recorded separately; this mapping alone is not a green receipt.

| Old row | Current assertion / disposition |
| --- | --- |
| `ac1/concurrent` | ac1/concurrent |
| `ac1/floor-boundaries` | ac1/boundaries |
| `ac1/metrics` | ac1/metrics |
| `ac1/other-holds` | ac3/advised-counts |
| `ac1/second-pool` | ac1/second-pool |
| `ac1/unread-pool` | ac1/unread-pool |
| `ac2/acceptance-rechecks` | accept/released-hold |
| `ac2/before-reservation` | ac2/pre-reservation |
| `ac2/cancel-releases` | release/cancelled |
| `ac2/completion-wakes` | ac2/completion-wakes |
| `ac2/factory-waiting` | ac2/waiting-pass |
| `ac2/racing-prepare` | ac2/racing-prepare |
| `ac2/recorded-wait` | ac2/stable-hold |
| `ac2/reservation-failure` | release/preparation-failed |
| `ac2/service-wiring` | ac2/worker-responsive |
| `ac2/worker-responsive` | ac2/worker-responsive |
| `ac3/report-starts` | ac3/started-advised |
| `ac4/contract-digest` | ac4/digest |
| `ac4/finished-measurement` | release/measurements |
| `ac4/last-five` | ac4/last-five |
| `ac4/off-and-legacy` | disabled/no-hold; ac4/legacy-history |
| `ac4/one-run-default` | ac4/five-before-measured |
| `ac4/project-file` | ac4/declared-first |
| `ac4/unmeasured-default` | ac4/five-before-measured |
| `ac4/unread-declaration` | ac4/project-station |
| `fix1/failed-judgment` | fix1/failed-judgment |
| `fix2/left-backlog` | fix2/left-backlog |
| `fix2/withdrawn-restart` | recovery/orphan-released; recovery/next-offer |
| `fix4/no-account-keeps-hold` | fix4/no-account-keeps-hold |
| `setup` | Current fixture setup, no behavioral assertion retired |

Old attempt-decrement, equal-attempt ordering, duplicate Requests API and composite ends_on representations are retired. The candidate uses monotonically distinct attempts, space_failure, current prepare and forms/FORM_ROWS. Candidate signed andon clearing and bounded waiter writes remain.

Historical home-directory strings in JSON receipts are redacted as `<historical-home>`; original bytes remain available at the pinned incoming Git revisions. Historical receipts never certify this joined tree.
