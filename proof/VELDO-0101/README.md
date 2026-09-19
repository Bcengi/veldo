# VELDO-0101 proof

Implementation commit: c4b485f. Gate GREEN there (selftest 5399 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/capsule.py`: the review brief that tells the reviewer to save every confirmed reproduction as
files under .veldo-review/capsules/<finding-id>/ with manifest.json (finding_id, reviewed_commit,
command, expected, observation) and that a finding without a capsule is reported as UNCONFIRMED; a
loader that digests every file in the capsule and refuses changed bytes, a missing file or an
undigested extra file; a runner that copies the named commit with git archive into a fresh
directory, mounts the capsule at .capsule/, runs the saved command with a deadline and the checkout
root on PYTHONPATH, judges the observation in a separate function, and raises if the reviewer's
files changed during the run. The review script in myday appends the brief from the worktree under
review and harvests the capsules beside the report.

## Driven

`drive.py` records one run of suite 40 as `driven.json`: 9 rows, 9 passed, 4 DRIVEN rows, the three
declared falsifiers among them plus the deadline-kills-the-group falsifier added by the fix commit, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The runner rows build a real two-commit git repository under a
temporary directory and run the saved command as a child process with a deadline.

## Approval

VELDO-0101 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Author-tested under the Codex-out rule (Dmitry, 2026-09-14, restated 2026-09-19): Codex was out of quota until 2026-09-21,
so the author drove suite 40 with every declared falsifier and ran the canonical gate; Dmitry approved the landing
(approval-dmitry.json). The author's own review after landing found one defect, fixed in the commit that adds the
row capsule/deadline-kills-the-group: the deadline killed only the command, not the process group it started, so a
reproduction that spawned a helper left it running. Codex reviews this item in its batch of 2026-09-22; that review,
its findings and any fixes are recorded here when they land.
