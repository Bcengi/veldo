VERDICT: HAS DEFECTS (D1 medium)

# WARP-1712 round 3 fix check, 2026-10-21

Reviewer: Claude (fresh context, did not write this change). Subject: 4c230340, fixes in
90290e15, judged against _inputs/REVIEW.md (R1 to R5 on 5b2a5a95). Read: the round 3 diff of
engine/.veldo/evidence_debt.py and engine/.veldo/validate.py, the suite 106 review cases
(_w1712_review), drive.py, the spec's round 3 text, proof README, policy_check BASE,
control_verification._policy_main, lander sync_main, verify.sh stage order, the gate
sandbox write roots. The engine and .veldo copies of both files are byte-identical (cmp).

## Findings R1 to R5

R1 (high): CLOSED. engine/.veldo/evidence_debt.py:122-130 now walks every base-register row
and sends each row absent from the current failures to payoff() (:93-107). payoff refuses
when the spec or proof at the original path is missing (:97-98), when the base spec id, the
current spec id and the manifest spec_id are not all equal (:102-104), when any base-required
kind was dropped (:105-106), and otherwise requires the strict check to pass (:107). The base
spec is read at the merge base (:82-86), so a same-push edit cannot fake the old kinds. Rows
that still fail stay subject to the touch refusal (:134-139). My own scratch runs: manifest
deleted, spec deleted, spec renamed plus register regenerated: exit 1 with "historical pair
requires passing evidence at its original paths". The suite covers relabel, both ids
relabeled, requirements emptied and reduced, proof moved, real payoff.
Falsifier on round 2 code: `drive.py review-round2` exit 1; the six R1 refusal cases fail and
the three R1 controls pass. My delete manifest and delete spec cases exit 0 on 5b2a5a95.

R2 (medium): CLOSED for the upstream scenario, NOT CLOSED for the BASE pass-through it also
named. evidence_debt.py:64-69 no longer consults @{upstream} or HEAD~20; the bound is
merge-base(origin/HEAD or origin/main, HEAD), and with no trunk ref it fails closed (:90;
this worktree has no remote refs, so `validate.py all` here exits 1 with "cannot resolve trunk
range", as intended). Falsifier: "R2 feature upstream touch" and "growth" fail on round 2
code. But the review also said policy_check.BASE is never passed to the ratchet, and that is
still true: the only caller, engine/.veldo/validate.py:731, passes no policy, so
push_context loads a fresh policy_check module (:50-54) whose BASE is always None. The
"R2 explicit policy base" control works only by rewriting `BASE = None` in policy_check.py
source, a path no gate uses. See D1.

R3 (medium): CLOSED. The prefix is taken once with rev-parse show-prefix (:60-63), stripped
from top-level diff names (:87-88), and prepended to every historical object read (:78, :83).
ls-tree (:73) is cwd-relative, so it is right without the prefix. Scratch runs at vendor/v:
untouched exit 0; touching a proof file exit 1 (touched pair); new debt exit 1 (new debt
forbidden). Falsifier: the three R3 cases fail on round 2 code.

R4 (low): CLOSED. Changed paths and the prior register both come from the merge base
(:66-81). Scratch run: trunk moves with an unrelated commit, the branch touches the fixture
pair WARP-1712 and merges trunk back in: exit 1 for the touch, as it should. Suite: trunk-only
proof change and trunk payoff do not redden an untouched branch. Falsifier: both R4 cases
fail on round 2 code.

R5 (low): CLOSED, and stricter than the review's proposal. engine/.veldo/validate.py:160-162:
a present exit_code must be an int (bool excluded by `type(...) is int`) equal to 0, in
addition to an explicit passing outcome. expected_exit cannot bless a nonzero exit; the spec
(round 3 text, lines 154-155) and README say this is the owner's choice, so it is not a defect.
My scratch case exit_code true: exit 1 now, exit 0 on round 2. Suite falsifiers: three R5
cases fail on round 2 code, two controls pass.

## New finding

### D1 (medium): the ratchet's trunk bound is read from refs the candidate can move

Where: engine/.veldo/validate.py:731 (no policy argument), engine/.veldo/evidence_debt.py:50-54
and :64 (BASE always None, so the bound is origin/HEAD or origin/main of the candidate's own
repository). Context: control_verification.py:610-627 hands the installed policy check the
lander's watermark precisely because "its code could move its own origin refs to HEAD,
emptying a range read from them" (VELDO-0058 AC3). The lander workspace is a fresh git init
whose .git lies inside the worktree (lander.py:509-535), the gate sandbox write roots include
{worktree} (scripts/agent_sandbox.json), and verify.sh runs the unit stage, whose suite
files are deliberately unprotected (policy.yaml:60-63), before the contracts stage
(verify.sh:190 then :233).

Concrete sequence on a feature branch:
1. Commit A: edit specs/VELDO-0016-policy-boundaries.md (a registered historical pair), add a
   new pair with a spec that requires integration and a proof without it, run
   `validate.py evidence-debt` and commit the regenerated register.
2. Commit B: in any existing suite under scripts/suites/, add one line that runs
   `git update-ref refs/remotes/origin/main HEAD` (origin/HEAD is a symbolic ref to it in
   the lander workspace).
3. Land. The unit stage moves the ref; the contracts stage resolves merge-base(origin/HEAD,
   HEAD) = HEAD, so the touched set is empty and the "previous" register is HEAD's own
   regenerated one. No touch refusal, no new-debt refusal, no payoff check. The installed
   policy check is unaffected because it alone receives BASE.

Run here in a scratch fixture with the shipped CLI (step 3 simulated by moving the ref
directly): control without the move exit 1 (new debt forbidden plus touched pair); after
`update-ref refs/remotes/origin/main HEAD` exit 0; pointing origin/HEAD at a ref on HEAD
also exit 0. Not run through the real lander and sandbox. A candidate can also simply edit
the unprotected evidence_debt.py, so this is a review-tier bypass, not a privilege escape;
it is medium because it needs no change to the ratchet's own code, the spec promises "an
explicit policy BASE when provided" and the README says "the policy object can be supplied
to the ratchet", yet no gate provides one, and the shipped control for that path proves
only a source edit.

Fix: give the ratchet the same authority base as the policy check. For example, have the
lander/control_verification pass the watermark to the contracts stage through the authority
(an installed entry that loads evidence_debt with a policy whose BASE is the watermark, as
_policy_main does), and refuse in a gate context when no BASE is supplied. Add a falsifier:
a candidate stage moves origin/main and origin/HEAD to HEAD before the contracts stage, and
the gate stays red with the touch and growth refusals.

## Other dodges tried, all refused or harmless

- Rename the spec or move the proof directory, register regenerated: exit 1 (payoff paths
  missing plus new debt forbidden).
- Edit only the spec, or only a proof file: exit 1 (touched pair).
- Delete either half: exit 1 (spec or proof missing).
- Regenerate the register in the same push: the bound is read at the merge base, so no effect.
- Add a duplicate kind to required_evidence: still failing, touched, exit 1.
- Relabel the manifest in one commit and restore it in the next: exit 0, but the net diff is
  empty and the pair is unchanged in the register, so nothing is paid off. Not a dodge.
- Vendored root, trunk that moved, branch merging trunk: correct, as above.
- Uncommitted working tree edit to a historical spec: local `validate.py all` exit 0,
  because the touched set is commit-based while the rows are computed from the working tree.
  The lander gates committed trees and verify.sh stamps the tree as dirty, and round 2 had
  the same shape, so I record it as an observation, not a finding.

## Commands run here (exit statuses read directly)

- `python3 proof/WARP-1712/drive.py current`: exit 0, 257 passed, 0 failed.
- `drive.py base`: exit 1 (expected), 41 passed, 69 failed.
- `drive.py review-current`: exit 0, 23 passed. `drive.py review-round2`: exit 1 (expected),
  7 passed, 16 failed; the driver asserts the per-case relationship and that each of R1 to R5
  has a failing case.
- The 11 mutant modes: each exit 1. integration-alias 2, evidence-outcome 40, check-outcome
  16, conflicting-outcome 4, design-existence 7, ratchet-touch 5, ratchet-global 3,
  ratchet-register 6, ratchet-growth 2, ratchet-range 3, ratchet-reset 1.
- `scripts/selftest.py` with the suite option on 106_warp_1712_required_evidence: exit 2
  (the partial-run status), 283 passed, 0 failed.
- `scripts/check_template_sync.sh`: exit 0.
- `python3 .veldo/validate.py all` in this worktree: exit 1, the single problem being the
  fail-closed "cannot resolve trunk range" (no remote refs here). Not a product defect.
- Canonical `./scripts/verify.sh`: not run here. The author's round 3 gate record was not
  re-executed by this review.

Scratch fixtures were built in temporary directories outside this worktree. No file other
than this one was changed.
