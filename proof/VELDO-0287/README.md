# VELDO-0287 evidence

A spec lands in a push only when it is new to main. Built on fix/veldo-0287 from landing-c bd8a4bc5
(implementation commits 9488790a and b6ee3841). The canonical gate was not run and the gate lock was not taken; the
lead records the manifest and the verdict after the gate.

## What changed

`.veldo/policy_check.py` (the engine copy is byte-identical):

- `landing_specs` skips every spec in `on_base`: a carried spec that is readable and not a draft at the
  push base (`push_range`, the protected ref's tip). Absent, draft or unreadable at the base, it is not on
  the base. New helper `_status_at` reads a spec's status at a revision.
- First build (b6ee3841): a spec ready on main with no proof bundle there, whose bundle the push creates,
  is not on the base and lands. The factory makes a spec ready on main before a worker builds it; without
  this, every row of suite 69_veldo_0058 that lands a build was refused as uncovered work (found by the
  first full selftest run, stopped there). A spec whose bundle is already on main stays a re-land.
- `built_specs`: the landing specs whose proof bundle the push changes (`bundle_touched`: any bundle file
  but an approval record). The objection override, the protected-path check and `approval_rule` take the
  producer from these, not from every landing spec.
- The per-spec loop judges `landing_specs` (was every carried spec). A landing spec with nothing built goes
  down the spec-only branch: the owner approval its flag requires, the push's committers standing in for
  its missing producer, no review.
- N3: in a push that is not spec-only, a spec file or bundle file (not an approval record) of a spec on
  the base is work, listed after the other uncovered files, and only a built landing spec covers work.
- `lowered_flags` drops a result whose id is absent at every push base and at HEAD.

Suite 129: four rows, and a `returned` variant in `AC3 lowered/honest-trunk-merge` (trunk retires a
required spec, the branch merges main, trunk adds it back, the branch merges main again). Without it the
new filter also passed the `retired` case, and falsifier `scope272-absent-filtered-first` survived.

Three VELDO-0272 fixtures pushed a verdict for a spec already on main, which the new rule counts as work no
landing spec covers. `AC3 lowered/flip` and the approved half of `AC3 lowered/rename` no longer write that
verdict (a flag change to a landed spec is a spec-only push); `AC3 lowered/old-base-merge` carries a new
reviewed spec, VELDO-9318, that covers the merged work. Their expected exits are unchanged.

`scripts/check_teeth_mutations.py`: finding 287 (five falsifiers, below). Three finding 272 anchors
follow the renamed calls (`scope272-protected-producer-from-head`,
`scope272-approval-rule-producer-from-head`, `scope272-uncovered-code-lands`).

## Acceptance criteria and rows

| AC | Rows (suite 129) | Falsifiers (finding 287) |
|---|---|---|
| AC1 new to main | landing/slimmed-bundle (reviewed ticket: 0), landing/re-land (re-land 1, first build 0) | land287-on-base-lands, land287-first-build-refused |
| AC2 files of specs on main are work | landing/slimmed-bundle (no ticket: 1, names proof/VELDO-9371/big.json), landing/re-land (names docs/guide.md) | land287-on-base-not-work |
| AC3 unbuilt ready spec | landing/ready-no-work: owner approval 0, none 1, committer 1, code beside only it 1 | land287-unbuilt-reviewed, land287-unbuilt-covers-work |
| AC4 renumbered draft | lowered/renumbered-draft: draft 0, spec on main 1 | land287-renumbered-lowered |

`landing/re-land` also checks that every 0272 lowered, review and approval row passed in the same run.

## Red and green

All runs in `systemd-run --user --scope -p MemoryMax=10G`, host dmitry-pc, Python 3.12.3, load average
7.3 to 20 during the runs.

- Green: `python3 scripts/selftest.py --suite 129_veldo_0272_approval_scope`: 37 rows, 63 passed, 0
  failed (exit 2, the partial-run exit). `--suite 69_veldo_0058_gate_output`: 42 passed, 0 failed.
- Red, change reverted (before the first-build commit; the bd8a4bc5 policy_check.py over the working
  file, then restored):
  57 passed, 6 failed. The failures: all four new rows (slimmed-bundle: landing_without_review
  VELDO-9371; ready-no-work: landing_without_review VELDO-9374; renumbered-draft: approval_flag_lowered
  specs/VELDO-9375-spec.md; re-land: exit 0), the updated old-base-merge fixture, and
  policy/engine-identical (the engine copy differed while swapped).
- `python3 scripts/check_teeth_mutations.py --finding 287`: registered 6, executed 6, rejected 6, exit 0.
- `python3 scripts/check_teeth_mutations.py --finding 272`: registered 34, executed 34, rejected 34,
  exit 0 (before the returned variant: 33 rejected, `scope272-absent-filtered-first` survived).
- `python3 scripts/selftest.py` (whole suite) at b6ee3841: 9048 passed, 5 failed, exit 1. Two are the
  inherited sandbox rows of 101_veldo_0208 (red on main, VELDO-0272 proof). The other three passed when
  rerun alone right after: 67_veldo_0056 (candidate/rejection-leaves-trunk, named-policy-refusals) 37
  passed 0 failed, 115_veldo_0219 (admission/stage-receipts-and-recording) 56 passed 0 failed. The host
  was shared with other jobs (load average up to 20). The first full run, before b6ee3841, was stopped
  after 69_veldo_0058 failed 8 rows on the first-build defect described above.

## landing-c under the new rule

At b6ee3841, `.veldo/policy_check.py` imported with `BASE=918e7c0eeae9a3c8d7a464858ead3ef76512a27c`
(174 commits, 179 changed files), each predicate main() runs called separately:

- landing_specs(changed_files()): VELDO-0267, 0268, 0270, 0272, 0273, 0274, 0278, 0279, 0280, 0287.
- Built (give the producer, need the review): 0267, 0268, 0270, 0272, 0274, 0278. Unbuilt: 0273, 0279,
  0280 and 0287 (0287 becomes built once this README is in the push).
- On the base, now work: VELDO-0110, 0121, 0123, 0127, 0167, 0189, 0215, 0230, 0239, 0254, 0256, 0257,
  0259, 0285, WARP-0716. N3: 149 work files, covered by built landing specs.
- approval_flag_lowered: none (VELDO-0271 no longer judged). Objections, ready boundary, stale proof,
  nightly sweep, emergency debt: pass.
- Protected paths: 14 touched, all refused only because the producer cannot be determined (none of the six
  built tickets has a manifest); with the producer test off, Dmitry's record accepts all 14.
- landing_without_review: each of the six built tickets (no manifest, no producer, no verdict).
- Owner approval missing: all ten landing specs are approval-required and none is named by an approval.
- main() exit 1, first refusal: protected path .veldo/control_verification.py, "the producer cannot be
  determined".

## Still open

- The approvals of the unbuilt 0273, 0279, 0280 and 0287 are judged against the push's committers
  (VELDO-0272's spec-only rule, unchanged). All 174 commits are committed as "Dmitry Grinberg
  <dmitry@bcengi.com>", so an approval naming either of those strings is refused; "dmitry", the approver
  of proof/landing-c/approval-dmitry-landing.json, is not.
- The first-build reading (AC1) goes beyond the literal wording of the owner's question on 40127; it is
  what keeps the factory's order (ready on main, built later) landing. The lead should confirm it.
