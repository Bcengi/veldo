# VELDO-0018 proof

Implementation commit: 2575b87. Gate GREEN there (selftest 5221 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/release_floor_contract.py`, a pure contract organ: the release membership forest and its
unique ownership (R65), release execution acceptance over exact member revisions with observed
regression receipts (R65), behavior-floor eligibility over applicable floor revisions and affected
pins (R65), the cancellation dispositions (R05, R06, R11, R65) and the boundary that release
acceptance never authorizes deployment. It reuses release_contract's forest rules,
entity_contract's release execution lifecycle and behavior_floor's ruling vocabulary, and never
loads release.py.

## Driven

`drive.py` records one run of suite 31 as `driven.json`: 23 rows, 23 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0018 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 7e831aa and found five reproducible problems (any signer accepted as an
authority, evidence transferable between releases at the same revision number, an unvalidated snapshot
accepting with no receipts, missing floor bindings comparing equal, settlement scope bounded by the floor
instead of the affected pins). Each is fixed and pinned with the reviewer's reproduction in suite 31. The
fixes carry no second Codex pass (one review per landing until 2026-09-22).
