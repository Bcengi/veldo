# VELDO-0104 proof

Implementation commit: 0390fda. Gate GREEN there (selftest 5460 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude), who also tested it under Dmitry's Codex-out rule; Codex validates it in the batch of 2026-09-22.

## What landed

`.veldo/fix_validation_record.py`, a module of its own, holds the validation record, the rule and the
validator's whole call site; `.veldo/validate.py` reaches it in one line through the organ inventory
`.veldo/validate_checks.py` already keeps, so `validate.py proof` and `validate.py all` apply the rule
alike. It became its own module because the validator sat at exactly the thousand-line budget this
repository caps a governed module at, and the refusal pointed at something real: producing four
mechanical results and deciding a closure from them are different questions.

A bundle is subject to the rule when it carries the REVIEWER's own evidence, the saved reproduction
capsules under `capsules/<finding-id>/`, each verified against its own digests, or a recorded verdict,
taken at a commit earlier than the bundle's own and present in THIS repository. Applicability is never
read from a field the author writes, and a review taken in a history this repository does not have is
not applicable rather than an error, which is what keeps the flag usable over a landed corpus. Then the
bundle must carry `validation.json`, written by the organ from the runner's record and the assessor's,
naming both commits and this spec, covering every finding the reviewer's evidence names, and closing
each one only where the four mechanical results AND the reader's verdict agree. Fix rounds are the
commits between the review and the landing that change code or suites, never filtered by the spec's
footprint, which a fix commit could rewrite, and never fewer than the fix commits the bundle's own kept
records name, so a squash cannot reset the count. Above two rounds the item is parked with its open
findings listed, and a parked item that says shipped is refused by name. The requirement itself is one
owner flag, `fix_validation.required` in the protected `.veldo/policy.yaml`: off, every problem is a
warning and the state is printed anyway; on, every problem refuses.

## Driven

`drive.py` records one run of suite 43 as `driven.json`: 9 rows, 9 passed, 6 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The rows build a real git repository with a review commit
carrying saved capsules, fix commits, a gate stamp, a proof commit and a ship commit, squash it with
plumbing, and run the validator's proof mode twice as a child process on bundles they built.

## Approval

VELDO-0104 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Author-tested under the Codex-out rule (Dmitry, 2026-09-14, restated 2026-09-19): Codex was out of quota until 2026-09-21,
so the author drove suite 43 with every declared falsifier and ran the canonical gate; Dmitry approved the landing
(approval-dmitry.json). Codex reviews this item in its batch of 2026-09-22; that review, its findings and any fixes
are recorded in this section when they land.
