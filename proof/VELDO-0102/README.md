# VELDO-0102 proof

Implementation commit: 7614c8b. Gate GREEN there (selftest 5414 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude), who also tested it under Dmitry's Codex-out rule; Codex validates it in the batch of 2026-09-22.

## What landed

`.veldo/fix_validation.py`: the capsule runner. For each finding of a review it produces four results,
each in a fresh copy of a commit made with `git archive` under a run directory that must lie outside
the worktree: the reviewer's capsule reproduces the defect on the reviewed commit (capsule_reviewed),
the same capsule does not reproduce it on the fixed commit (capsule_fixed), the author's pinned suite
row fails on the fixed commit with the declared mutant applied (row_mutant_red), and passes on a fresh
unmutated copy (row_fresh_green). A finding is closed only when all four hold. A result that could not
be produced is missing, never passed. A declared mutant whose anchor does not match exactly once is
INVALID_MUTATION naming the file, the anchor and the count, and no other anchor is searched for. Every
run is one child process started as a process-group leader with a deadline; on the deadline the whole
group is killed and the result is deadline. The worktree's digest is taken before and after and
recorded as worktree_unchanged.

## Driven

`drive.py` records one run of suite 42 as `driven.json`: 6 rows, 6 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The rows build a real two-commit git repository with the suite
layout under a temporary directory and produce the four results there as child processes with deadlines,
one of them a capsule that outlives its deadline with a helper process.

## Approval

VELDO-0102 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Author-tested under the Codex-out rule (Dmitry, 2026-09-14, restated 2026-09-19): Codex was out of quota until 2026-09-21,
so the author drove suite 42 with every declared falsifier and ran the canonical gate; Dmitry approved the landing
(approval-dmitry.json). Codex reviews this item in its batch of 2026-09-22; that review, its findings and any fixes
are recorded in this section when they land.
