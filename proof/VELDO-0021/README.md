# VELDO-0021 proof

Implementation commit: 3657544. Gate GREEN there (selftest 5326 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/completion_contract.py`, a pure contract organ: the four distinct completion facts and their
evidence, none implying the next (R70, R76); the authoritative snapshot every execution entry reads with
its named refusals and the provider charge reservation that must fit before a call (R45, R70); the proof,
review and outside-verification obligations of engineering completion (R46, R47, R50); and the publication
transition table with the R32 recovery findings, where uncertainty stays explicit (R32, R49, R76). It runs
no Git and lands nothing.

## Driven

`drive.py` records one run of suite 35 as `driven.json`: 26 rows, 26 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0021 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 814d6c2 and found six reproducible problems (a negative reconciled charge
manufacturing spending capacity, recovery returning to authorized without the authority recheck, a review
not bound to the implementation or proof it reviewed, a red gate satisfying completion, optional post-run
tree evidence, and verifier containment by unnormalized string prefix). Each is fixed and pinned with the
reviewer's reproduction in suite 35. The fixes carry no second Codex pass (one review per landing until
2026-09-22).
