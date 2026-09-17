# VELDO-0020 proof

Implementation commit: 271735d. Gate GREEN there (selftest 5271 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/authority_contract.py`, a contract organ with one seam to the installed OpenSSH: distinct
principal types and scoped membership with conjunctive requirements at every R39 boundary (R36, R37);
the OpenSSH-envelope Ed25519 command signature binding the complete request and the active delegation,
verified by recomputing the canonical command digest and never trusting transport (R36, R38); the
restricted edge key and platform attribution every enrolled channel needs (R38, R60, R72); and one
settlement per request version with originating-channel attribution and a quorum by distinct principal
(R40, R41, R72). It holds no key material and enrolls nobody.

## Driven

`drive.py` records one run of suite 33 as `driven.json`: 25 rows, 25 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0020 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 07662db and found seven reproducible problems (settlement never ran
authorize() so any active member settled, a member scoped to one project holding roles everywhere
and delegations with an empty or non-covering authority scope, a revoked delegation still signing,
rejections counted toward the approval quorum, a signed CLI attribution taking any non-empty string as
verified, an assertion at a stale request version settling the current one, and an acknowledgement
settling and consuming the nonce). Each is fixed and pinned with the reviewer's reproduction in
suite 33. The fixes carry no second Codex pass (one review per landing until 2026-09-22).
