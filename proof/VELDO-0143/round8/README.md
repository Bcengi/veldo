# VELDO-0143 round 8: the round 7 review's findings

Branch agent/claude/veldo-0143. The round 7 review is `../REVIEW-claude-r7-2026-10-23.md`, added unchanged from
faa7b50c in c263c7af. The code is bb5ffc0d, the rows and mutations c95472a3 and ef991d51, the spec and DECISIONS 31
to 33 6f1ea365, and this evidence the commit that adds it. The scratch commit 3f6e8b18 (below) is an object no branch
names. Nothing here is a gate result, a review verdict or an approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So suite
110 runs here through `../round2/sandbox_run.py --stage --agent`, as in rounds 4 to 7, and `scripts/verify.sh`
cannot run here. No timer and no polling was added anywhere.

## Each finding: change, row, mutation

| Finding | Change | Rows | Mutations (finding 143) |
| --- | --- | --- | --- |
| R7-1 (medium): his own message settles a public repository he never picked | `nothing_asked`: the reason `visibility_not_private` whenever the proposal's visibility is not private (replaces `visibility_not_default`, whatever the identity's default or the PM's document says), and `visibility_in_message` whenever his message holds a word of visibility (`says_visibility`) | proposal/own-message-doubt: a fixture identity outward with `default_visibility` public, its message silent on visibility, saying "keep it private" and saying "hidden please", and a private identity's message saying "make it public", each presented with the reason named; the outward proposal shows public and offers `accept outward private` | newproject143-own-message-visibility (re-targeted to the new reason; also kills provision/adoption-path), -own-message-visibility-word |
| R7-2 (medium): an adopted directory offers both visibilities, and the pick binds nothing | an adopt entry records `as_on_remote` (`AS_ON_REMOTE`): `offered_entry` and the kept adoption of a correction; `picks` offers it as `accept <identity>` alone, or nothing when it is the identity shown; the brief says "visibility as it is on GitHub"; `resolve` refuses a visibility for an adoption; `proposal_problems` refuses a resolved adoption recording anything else and a creation from `as_on_remote`; `correction_problems` refuses a correction renaming a shown adoption (`invalid_input:correction:mode`). The remote's visibility is not known when the entry is laid (prepare reads the origin and checks its owner only), so nothing reads it from GitHub | proposal/adoption-visibility (quay: the entry's visibility, its choice, the brief, "accept personal private" and "accept personal public" refused `unmatched_choice`, the pick adopting it as it is, `resolve` and the judge refusing a recorded visibility, `proposal_problems` on it; slipway: the renamed adoption failed by name, GitHub not asked); provision/adoption-path (his own message naming an adoption is presented, `visibility_not_private`, then answered) | newproject143-adoption-visibility-offered, -adoption-visibility-recorded, -adoption-visibility-shown, -adoption-renamed-created; -correction-mode-unbound re-targeted to the new line |
| R7-3 (low): ids that fold alike leave a decision presented to no one | `control_git_identity.validate` refuses ids equal under the presentation module's fold (`presentation_fold` loads `control_channel_presentation._fold`), `invalid_input:ambiguous_git_identity`, and `configure_identities` refuses the same for an id added later; `NewProjects._present` reads the presenter's outcome, and a refusal no retry changes (`NOT_PRESENTABLE`: ambiguous_choice, unmapped_choice, presentation_too_long) cancels the request and raises `NotPresented`, so `propose` and `resume` fail the decision `invalid_input:<refusal>` (`presenting` may now go to `failed`); control_telegram_report tells him in plain words with what to do | proposal/identities-fold-alike (work/Work, my-org/my_org, a.b/A.B refused; distinct ids accepted; Bcengi added beside bcengi refused, nothing added); proposal/not-presentable (a legacy Bcengi written into the table as it was stored: failed `invalid_input:ambiguous_choice`, nothing sent, request CANCELED, the report says why and what to do) | newproject143-identities-fold-alike, -identity-added-folding (control_git_identity.py, now at suite 110's PRODUCTION anchor), -not-presented-left-presented |
| R7-4 (low): the judge's choices check has no row | none in the code | proposal/choices: a request presented with `PP.choices` stood in to `['accept', 'reject']` (chine), answered `accept`, applied (settled), and the judge refuses it `no_settled_decision:choices`; then failed, so no pass provisions it | newproject143-judge-choices-unchecked |
| R7-5 (low): AC1 states an absolute the own-message path does not keep | AC1: "On a presented proposal, only the choice he picks binds the identity and the visibility ...; His own message settles unasked only as the nothing-asked rule allows: ... the repository is created private, never public and never an adoption"; and an adopted directory is offered by its identity alone. Claim and falsifier unchanged. History entry. The stale comment at the word edges (`_LEFT_EDGE`) now names what reads them; control_telegram_report's advice for `invalid_input:correction:mode` (CORRECTION_NEXT) says what a refused mode means and what to do, no longer PICKED_NEXT | (text) | (text) |

Finding 143 has 60 cases: 51, plus nine new, two re-targeted.

## Results here

- Suite 110 at ef991d51 (`110-head.json`): 90 passed, red only service/hand-off (AF_UNIX, the host's). At
  c95472a3 the same.
- Suite 110's round-8 rows on the round-7 engine (`110-round7-engine.json`): the tree is c95472a3 with
  control_project_proposal.py, control_git_identity.py and control_telegram_report.py (both copies) taken from
  a7db6774, run as the scratch commit 3f6e8b18. Red: proposal/own-message-doubt, provision/adoption-path,
  proposal/adoption-visibility, proposal/identities-fold-alike, proposal/not-presentable, and with them
  proposal/presentation-interrupted and service/pm-settled-due (they read the decision not-presentable leaves
  presented there), and service/hand-off. proposal/choices is green there: R7-4 adds a row for a check the round-7
  engine already had, and its mutation is what shows the part guards it.
- Suite 62 at c95472a3 (`62-head.json`): 42 passed, 0 failed.
- Round 7's `phrasings.py` on the round-8 module (`phrasings-round8.jsonl`): 90 phrasings, 0 not as claimed.
- Finding 143, `../run_falsifiers.py` in worker mode (`falsifiers-143-round8.json`): the 57 cases that target suite
  110, in four partitions in parallel on a `git archive` of c95472a3: 56 killed. newproject143-adoption-visibility-
  recorded survived, because the judge's equality check (`proposal != expected`) refused the forged decision before
  `proposal_problems` mattered; ef991d51 adds a part judging `proposal_problems` on a resolved adoption recording a
  visibility, and the four adoption cases rerun on ef991d51 are all killed. Each baseline is red only on
  service/hand-off and pm/new-project-run (worker mode stands in for nothing). The two suite-62 cases are unchanged
  from round 7 and suite 62 is unchanged; newproject143-scaffold-not-laid is the host's (suite 66).
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`) on `git archive` trees of a7db6774 and
  c95472a3, one after the other: round 7's 44 suites, plus 103_veldo_0142_git_identities, 58_veldo_0028_effects
  and 59_veldo_0037_aliases (further readers of control_git_identity), give the same result on both trees. That is
  evidence only for the suites that run here: 103, 58, 59, 107, 82_veldo_0141, 85_veldo_0158, 71_veldo_0130_api and
  71_veldo_0138_channel_service do not start here (AF_UNIX or no table), and several others are red on both trees
  (sandbox limits). Suite 103's two fixture identities (bcengi, personal) fold apart, so the new refusal does not
  meet them; the host run is still needed.
- `.veldo/validate.py all` exits 0. check_lint, check_template_sync and check_generated pass.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, service/hand-off included and
   the new proposal/adoption-visibility, identities-fold-alike and not-presentable.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/selftest.py --suite 62_veldo_0065_presentations`: every row green, answer/pick-choices included.
4. `python3 scripts/check_gate_mutations.py --finding 143`: 60 of 60 killed.
5. The consumer suites at this branch's head and at a7db6774: first 103_veldo_0142_git_identities,
   107_veldo_0153_identity_push, 108_veldo_0153_executor_profile, 109_veldo_0161_adoption, 58_veldo_0028_effects
   and 59_veldo_0037_aliases (readers of control_git_identity), 72_veldo_0128_reports and 93_veldo_0152_intake_routes
   (control_telegram_report), then the rest of round 7's list.
6. `bash scripts/verify.sh`.
