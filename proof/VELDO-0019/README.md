# VELDO-0019 proof

Implementation commit: bcb408b. Gate GREEN there (selftest 5239 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/graph_contract.py`, a pure contract organ: the union of the five R14 edge families and its
acyclicity, independent of the release membership forest; dependency resolution to exact accepted
revisions or completion receipts, never a status string; the reverse-closure invalidation an amended
or withdrawn prerequisite causes (R14, R39); and the decision bindings, settlement and observation
freshness rules that decide whether a governing decision authorizes anything (R40, R71).

## Driven

`drive.py` records one run of suite 32 as `driven.json`: 18 rows, 18 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0019 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.
