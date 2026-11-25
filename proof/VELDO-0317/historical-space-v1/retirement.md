# VELDO-0317 superseded fixture retirement

Old source: `150_veldo_0317_full_pool.py.txt` in this folder, preserved for audit. Its APIs belong to the old stack; it is not an executable joined-tree suite.
Replacement: `scripts/suites/159_veldo_0317_no_space.py`. Baseline implementation evidence: candidate 95851131e; see assembly-v1.md for the specific implementation commits.

Rows below identify current row families, not equivalence of every historical predicate. The clause-level recheck in proof/VELDO-0319/distinct-assertion-audit.json is authoritative and records partial coverage explicitly. Rows saying SUPERSEDED describe incompatible old contracts, not removed safety guarantees. Dynamic subrows remain in the archived source and are covered by their parent family. `setup` is fixture infrastructure, replaced with the current fixtures. Runtime results are recorded separately; this mapping alone is not a green receipt.

| Old row | Current assertion / disposition |
| --- | --- |
| `ac1/behind-admission` | ac1/behind-admission |
| `ac1/order` | ac1/numbers-before-cleanup |
| `ac1/refunded` | ac1/not-charged (charged count zero; attempt IDs remain distinct) |
| `ac1/replayed-end` | ac1/replayed-end |
| `ac2/repeat-once` | ac2/repeated-once; ac2/repeat-red |
| `ac2/restart` | ac4/restart-stop |
| `ac3/next-brief` | ac3/next-brief |
| `ac3/reconnect` | ac3/reconnect |
| `ac3/work-retained` | ac3/edit-kept |
| `ac4/off-loop` | ac4/off-loop |
| `ac4/reset` | history/reset |
| `ac4/two-stop` | ac4/two-stop |
| `classification/incomplete` | artifact/no-verdict |
| `classification/floor` | classify/controls: equality with the floor is unconfirmed |
| `classification/success` | classify/controls: successful process is not classified as no-space |
| `classification/ordinary` | classify/controls: failure without a no-space token is not classified as no-space |
| `classification/streams` | classify/streams |
| `classification/unread` | classify/unread |
| `fix1/rerun-before-release` | ac1/behind-admission; accept/released-hold (157) |
| `fix1/spent-answer` | fix1/spent-answer (157) |
| `fix2/andon-redelivery` | fix2/andon-redelivery |
| `fix3/bounded-scan` | history/bounded-read |
| `fix3/brief-ends` | ac3/brief-no-space-only; history/reset |
| `setup` | Current fixture setup, no behavioral assertion retired |

Old attempt-decrement, equal-attempt ordering, duplicate Requests API and composite ends_on representations are retired. The candidate uses monotonically distinct attempts, space_failure, current prepare and forms/FORM_ROWS. Candidate signed andon clearing and bounded waiter writes remain.

Historical home-directory strings in JSON receipts are redacted as `<historical-home>`; original bytes remain available at the pinned incoming Git revisions. Historical receipts never certify this joined tree.
