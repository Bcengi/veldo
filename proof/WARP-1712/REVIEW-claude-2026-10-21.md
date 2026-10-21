VERDICT: HAS DEFECTS (R1 high, R2 medium, R3 medium, R4 low, R5 low)

# WARP-1712 independent review, 2026-10-21

Reviewer: Claude (fresh context, did not write this change). Subject: commit 5b2a5a95
(the tip of agent/codex/warp-integration-evidence), compared with base d49581b4. Read: the
spec, proof README, core-blast-radius.md, the debt register, engine/.veldo/validate.py,
engine/.veldo/evidence_debt.py, the policy_check range resolver, the lander's sync step, the
suite 106 matrix and the falsifier driver. Both validator copies and both evidence_debt
copies are byte-identical (cmp).

## Findings

### R1 (high): a touched historical pair leaves the register without passing evidence by breaking its pairing

Where: engine/.veldo/evidence_debt.py:101-106 (the touch refusal walks only the pairs that
fail now) with engine/.veldo/validate.py:726 (a pair exists only while the manifest's
spec_id matches a spec in specs/ and the spec declares required_evidence).

Scenario, run in a scratch clone of 5b2a5a95 with origin/main at the clone's root commit.
Each push touches registered historical pair VELDO-0016, regenerates the register with
`validate.py evidence-debt`, and commits:

- the manifest's spec_id is edited to `VELDO-0016-retired`: `validate.py all` exit 0;
- proof/VELDO-0016/manifest.json is deleted: exit 0;
- the spec's `required_evidence` is changed to `[]`: exit 0.

In each case the pair no longer exists, or no longer fails, so it has no row, the touch check
never sees it, and its register line disappears as an allowed shrink. The owner's rule is
that debt shrinks only through real passing evidence, and that a touched historical pair is
refused. Here debt is paid off by unlinking or relabeling, the shortcut that rule forbids. The lander uses the same code, so a landing gate does not
catch it. (Changing the spec's own id was caught, but only by an unrelated plan-binding
check, so a spec bound to no plan would pass too.)

Fix: also walk the push-base register. For each base entry whose spec or proof directory is
touched, or which is missing from the new register, require at HEAD that the same spec path
and proof path still exist, still pair by spec_id, declare at least the base's required
kinds, and pass the strict check. Otherwise refuse with the cause. Add CLI controls for
the three scenarios above, with falsifiers.

### R2 (medium): the register bound and touched set follow the branch's own upstream, not trunk

Where: engine/.veldo/evidence_debt.py:60 (the first readable range from
`policy._range_specs()`, which tries `@{upstream}..HEAD` first).

Scenario, run: on branch t, commit 1 adds a new failing pair VELDO-9001 (integration
required, only a generic `test` entry), touches historical VELDO-0016, and regenerates the
register (VELDO-9001 is now listed). Point refs/remotes/origin/t at commit 1 and make
it t's upstream (an earlier push of the feature branch, which no gate required). Commit 2
changes one unrelated file. `validate.py all` exit 0: the range is origin/t..HEAD, so
neither pair counts as touched, and the "previous" register is read at origin/t, so the new
debt counts as preexisting. The same tree measured against origin/main exits 1 with
"new required-evidence debt forbidden" and both touch refusals. The gate's green on a
tracked feature branch therefore does not mean what the ratchet promises, which matters
wherever that green is relied on (the push guard checks for a green gate on HEAD).
From reading lander.py:529-536 (not executed), the lander's detached workspace has no
upstream and points origin/HEAD at the watermark, so a lander gate would catch this.
policy_check.BASE (the VELDO-0058 hardening) is never passed through to the ratchet either.

Fix: read the base register, and compute the touched set, against trunk: policy BASE when
set, otherwise the merge base with origin/HEAD or origin/main. Never use @{upstream} alone
for this bound. If upstream semantics are wanted for other checks, use the union of the
upstream and trunk touched sets and take the register bound from trunk.

### R3 (medium): wrong path spellings under a vendored VELDO root

Where: engine/.veldo/evidence_debt.py:61, :75 and :103. `git diff` names paths relative to
the repository top level; the rows name paths relative to the VELDO root.
`git show base:.veldo/...` is also read at the top level, while the `ls-tree` before it is
read at the current directory. verdict_corpus.py resolves the root prefix explicitly
(`rev-parse` with show-prefix) because vendored roots are a supported layout.

Scenario, run: the tree vendored at vendor/v inside a host repository. (a) With the register
committed at base and nothing touched: exit 1, "cannot read push-base debt register", so the
adopter is permanently red. (b) Adoption: the base has no register, and the push edits
VELDO-0016's spec and a proof file and adopts the register: exit 0, because
`vendor/v/specs/...` never equals `specs/...`. A touched pair is swallowed.

Fix: compute the prefix once (as verdict_corpus does), strip it from diff output (or use
git diff's relative mode run from the root), and read `base:<prefix>.veldo/required-evidence-debt.jsonl`.
Add a vendored-root CLI control.

### R4 (low): two-point diff against a trunk that has moved on refuses pairs the push never touched

Where: engine/.veldo/evidence_debt.py:61. `git diff A..B` compares two trees, so any file
trunk changed after the fork point appears as changed.

Scenario, run: trunk adds proof/VELDO-0017/mainnote.txt after the fork. The branch changes
one unrelated file. Result: exit 1, "touched pair requires passing evidence" for VELDO-0017.
This fails closed (rebasing clears it) but is a false refusal and is not "what this push
touches". policy_check's changed_files has the same shape.

Fix: take the changed set from the merge base to HEAD (three-dot semantics), and read the
previous register at that merge base.

### R5 (low): a check that records passed together with a nonzero exit code still counts

Where: engine/.veldo/validate.py:158. Only `status` and `result` are read. The checks
schema in use also carries `exit_code` (61 records in this corpus) and `expected_exit`.

Scenario, reasoned and not run: `{"name": "integration", "status": "passed",
"exit_code": 1}` satisfies integration. The spec says a record is rejected when "any
supplied outcome field disagrees". No current record in this corpus has that contradiction
(scanned: zero records with status passed and a nonzero exit_code), so this does not
affect today's verdicts.

Fix: when `exit_code` is present, require it to equal `expected_exit` if given, else 0.
Add the refusal case and its falsifier.

## What holds

Question 1, strict rule. Integration is satisfied only by evidence `type: integration`
or a check named `integration`, and the entry itself must record `status: passed` or
`result: pass`/`passed`. All supplied fields must agree. Unhashable, null, boolean, case
variants and prose fail. A criterion's status is never inherited. `test` and `unit`
(evidence or check) do not satisfy integration. Failed, pending, not-run and result-less
entries fail, and so does a bare check name. Apart from R5, I found no route by which a
unit test, a non-passing or result-less entry, or a check name alone satisfies
integration. Residual risk outside the spec's scope: the kind label is self-declared, so
an entry labeled integration that actually ran unit tests is not detectable without
inspecting the artifact.

Question 2, ratchet. Run in a scratch clone, each case exit 1 with the expected diagnostic:
touching only a proof file, only the spec, a touch in an earlier commit of a multi-commit
push, renaming the spec plus regenerating, moving the proof directory plus regenerating, a
new failing pair regenerated into the register, a new failing pair left unlisted, a dropped
entry, and a hand-added entry. The untouched clone exits 0. Renames cannot hide because of
the no-renames diff plus pair keys. A missing range grants no exemption. Deleting an
adopted register is refused. Pairs outside specs/*.md and proof/ are not checked at all,
which is true of every contract check before this change too. The defects are R1 to R4.

Question 3, tests and falsifiers: real. `drive.py base` exits 1 with 41 compatibility
controls passing and 69 refusal assertions failing on the old validator, and the driver
asserts that per-case relationship. All 11 mutants exit 1 with exactly the recorded counts:
integration-alias 2, evidence-outcome 40, check-outcome 16, conflicting-outcome 4,
design-existence 7, ratchet-touch 5, ratchet-global 3, ratchet-register 6, ratchet-growth 2,
ratchet-range 2, ratchet-reset 1. None of the controls covers R1 to R5.

## Commands run here (exit statuses read directly)

- `python3 proof/WARP-1712/drive.py current`: exit 0, 234 passed, 0 failed.
- `python3 proof/WARP-1712/drive.py base`: exit 1 (expected), 41 passed, 69 failed.
- the 11 mutant modes of drive.py: each exit 1, counts as above.
- `python3 .veldo/validate.py all`: exit 0 (range fell back to HEAD~20; no remote here).
- `scripts/check_template_sync.sh`: exit 0, 285 pairs. `scripts/check_lint.sh`: exit 0.
  `scripts/check_generated.sh`: exit 0.
- `python3 scripts/selftest.py` (full unit): exit 1 after 64 s, aborted in suite
  12_warp_1210_hardening_four on `PermissionError` creating an AF_UNIX socket. This
  environment forbids AF_UNIX sockets even outside the tool sandbox (a bare
  `socket.socket(AF_UNIX)` fails the same way). So this is not a product result. No full
  unit result is claimed.
- `selftest.py` with the suite option on 106, 14, 18_veldo_0012, 27_veldo_0010 and 43_veldo_0104: exit 1,
  409 passed, 1 failed. The one failure is the VELDO-0010 AC5 negative control (version
  stamp). Suite 27 run alone on an archive of base d49581b4 fails the same assertion
  (51 passed, 1 failed, exit 1), so it predates WARP-1712 and depends on the environment.
- `python3 proof/WARP-1712/confirm.py`: exit 1, permission denied reading
  /home/dmitry/projects/core. The core measurement (107 strict failures, 214 refusals,
  five parser errors) was not reproduced and is not confirmed by this review.
- Canonical `./scripts/verify.sh`: not run (it needs the socket-using unit stage). The
  author's record that no complete final-tree gate exists stands. That alone blocks landing.

Scratch repositories were made from `git archive` of the commit under review, outside this
worktree. No file other than this review was changed.
