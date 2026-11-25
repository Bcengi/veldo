# VELDO-0347 superseded fixture retirement

Old source: `150_veldo_0347_unseen_work.py.txt` in this folder, preserved for audit. Its APIs belong to the old stack; it is not an executable joined-tree suite.
Replacement: `scripts/suites/161_veldo_0347_space_work.py`. Baseline implementation evidence: candidate 95851131e; see assembly-v1.md for the specific implementation commits.

Rows below identify current row families, not equivalence of every historical predicate. The clause-level recheck in proof/VELDO-0319/distinct-assertion-audit.json is authoritative and records partial coverage explicitly. Rows saying SUPERSEDED describe incompatible old contracts, not removed safety guarantees. Dynamic subrows remain in the archived source and are covered by their parent family. `setup` is fixture infrastructure, replaced with the current fixtures. Runtime results are recorded separately; this mapping alone is not a green receipt.

| Old row | Current assertion / disposition |
| --- | --- |
| `ac1/build-output-is-not-work` | ac1/build-output-passes |
| `ac1/loose-ignored-file` | ac1/loose-ignored-file |
| `ac1/personal-rule` | ac1/personal-rule |
| `ac1/untraced-rule` | ac1/untraced-rule |
| `ac2/build-output` | ac2/build-output |
| `ac2/clean-clone-goes` | ac2/clean-clone-reading |
| `ac2/hand-written-ref` | ac2/forged-remote-ref |
| `ac2/last-look` | ac2/clean-clone-reading; remover suite 138 final descriptor guard |
| `ac2/log-only-commit` | ac2/reset-log |
| `ac2/unpushed-commit` | ac2/unpushed-in-session-scratch |
| `ac2/unreadable-holds` | ac2/unreadable (candidate sandbox exception retained) |
| `ac2/work-tree-and-stash` | ac2/clean-clone-reading |
| `ac3/changed-after-snapshot` | ac3/compare-before-delete |
| `ac3/clone-request` | ac3/unique-work-request |
| `ac3/creators-declare-the-form` | ac3/kind-and-form |
| `ac3/keep-first` | ac3/commit-kept |
| `ac3/ledger-keep-only` | ac3/ledger-keep-only: settled Save and Discard refused unchanged; worktree Discard accepted |
| `ac3/not-shown` | SUPERSEDED: candidate 7808cb3da declares form in the signed ledger, not a second worker-manifest authority. ac3/kind-and-form; snapshot and comparison remain mandatory |
| `ac3/renamed-back` | ac3/put-back-at-stop |
| `ac3/table-1-clone` | ac3/table-1-keeps-its-handling |
| `ac3/table-2-clone` | ac3/worker-snapshot |
| `ac3/worker-clone-saved` | ac3/worker-snapshot |
| `ac4/changed-after-measure` | ac4/digest-at-removal |
| `ac4/held-files-go` | ac4/digest-at-removal |
| `ac4/trunk-never-guessed` | ac4/declared-trunk |
| `ac4/unreadable-is-no-copy` | ac4/no-copy-unread |
| `ac5/no-form` | ac5/clone-row |
| `ac5/own-folder-holds` | ac5/own-folder |
| `ac5/registry-row` | ac5/clone-row |
| `unseen/canon` | canon |

Old attempt-decrement, equal-attempt ordering, duplicate Requests API and composite ends_on representations are retired. The candidate uses monotonically distinct attempts, space_failure, current prepare and forms/FORM_ROWS. Candidate signed andon clearing and bounded waiter writes remain.

Historical home-directory strings in JSON receipts are redacted as `<historical-home>`; original bytes remain available at the pinned incoming Git revisions. Historical receipts never certify this joined tree.
