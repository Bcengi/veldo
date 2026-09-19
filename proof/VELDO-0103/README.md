# VELDO-0103 proof

Implementation commit: 1276da5. Gate GREEN there (selftest 5414 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/fix_assessor.py`: the second reader of a fix. The brief is assembled from an allowlist (the
reviewed and fixed commits, the findings, the capsule results, the diff) and refuses anything else,
so the author's conclusions have no field to travel in. The harness is a separate headless process
of the logged-in Claude Code subscription (claude -p, JSON output constrained to the verdict schema,
no session persistence, read-only tools, every API key variable stripped), never a paid API. The
verdict is parsed per finding into closed, not_closed or new_defect; a finding the verdict omits is
not_closed; unparseable output closes nothing; a run without provenance (harness, model, wall time,
tokens) closes nothing.

## Driven

`drive.py` records one run of suite 41 as `driven.json`: 7 rows, 7 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. Every row drives the organ with a fake harness, a child process of
the same interpreter, so no model call is made and nothing is spent.

## Approval

VELDO-0103 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Author-tested under the Codex-out rule (Dmitry, 2026-09-14, restated 2026-09-19): Codex was out of quota until 2026-09-21,
so the author drove suite 41 with every declared falsifier and ran the canonical gate; Dmitry approved the landing
(approval-dmitry.json). Codex reviews this item in its batch of 2026-09-22; that review, its findings and any fixes
are recorded in this section when they land.
