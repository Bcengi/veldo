# VELDO-0022 proof

Implementation commit: 111da90. Gate GREEN there (selftest 5291 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/admission_contract.py`, a pure contract organ: the seven governed work classes with the
class-specific authority, lane, request and priority each needs (R07, R08, R09); the R66 predicates that
let a policy defect be admitted automatically and where an item goes when they fail; the quarantine,
standing-maintenance and break-glass bounds (R67, R68); and the machine-comparable scope whose material
change invalidates admission, with the admission-debt report (R69). It runs no scanner and enrolls nobody.

## Driven

`drive.py` records one run of suite 34 as `driven.json`: 20 rows, 20 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0022 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.
