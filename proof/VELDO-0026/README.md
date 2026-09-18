# VELDO-0026 proof

Implementation commit: 8a7c049. Gate GREEN there (selftest 5386 passed, 0 failed) in the plan-0019 branch
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

`drive.py` records one run of suite 39 as `driven.json`: 10 rows, 10 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The crash matrix and the races run real writer processes
against real SQLite files with real Ed25519 keys through the installed ssh-keygen under a temporary directory.

## Approval

VELDO-0026 is a critical-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.
