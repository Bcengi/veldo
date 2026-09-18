# VELDO-0026 proof

Implementation commit: ad8b1f5. Gate GREEN there (selftest 5392 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/control_revocation.py`: the reusable acceptance guard for the nine R39 boundaries, each a
callable registration judging one action against the current committed store: the actor's membership
through the authority contract, the revocation ledger, and every input in the caller's snapshot (a
dependency's prerequisites read indirectly), refusing by name whatever moved, was withdrawn or was
inserted since, and writing every refusal as a durable denial first (a denial that cannot be written
stands the boundary down). Revocation and effect acceptance are store commands sharing one ledger
entity as an expected version, so their order is the store's; an effect accepted first stays in
flight with a journaled stop obligation until evidence reconciles it; outputs from a revoked
principal stay evidence and satisfy nothing without a reauthorization bound to the ledger's current
version (R14, R39, R50, R69, R70). No receiver runs and no external effect is undone.

## Driven

`drive.py` records one run of suite 39 as `driven.json`: 16 rows, 16 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The crash matrix and the races run real writer processes
against real SQLite files with real Ed25519 keys through the installed ssh-keygen under a temporary directory.

## Approval

VELDO-0026 is a critical-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 40b22ce and found seven reproducible problems (an output submitted under the ledger's
id overwriting the revocation ledger, checked read-set versions dropped before commit, the guard trusting the
caller's cached membership, membership revocation not quarantining the member's outputs, real disk-full errors
escaping the denial handler, identical retries becoming content conflicts, and non-transitive snapshot expansion
rejecting valid dependency chains). Each is fixed and pinned with the reviewer's reproduction in suite 39. The
fixes carry no second Codex pass; they are verified in the Codex batch of 2026-09-22 (Dmitry's ruling).
