# Open decisions and footprint widening, fix round 1

Review: proof/VELDO-0259/review-2026-11-05.md (NOT SOUND). Evidence of this round: proof/VELDO-0259/fix-round-1.txt.

## The lead's ruling on the home path in proof/ (footprint widened by the lead)

The built-in home_path rule stays as the spec requires. So that no builder or tool has to remember it, each
of Veldo's own evidence and log writers that records into proof/ writes the user's home directory as `~`
when it writes (home_as_tilde, both $HOME and the account's home from the password database). The writers:

- .veldo/fix_validation.py (and engine/.veldo/fix_validation.py): main, fix-validation.json
- .veldo/fix_assessor.py (and engine/.veldo/fix_assessor.py): main, assessment.json
- .veldo/fix_validation_record.py (and engine/.veldo/fix_validation_record.py): write_record, validation.json and validation/<commit>.json
- .veldo/qualify.py (and engine/.veldo/qualify.py): fixtures, the qualification fixtures under proof/
- scripts/drive.py: red and main, red-at-<commit>.json, <case>.diff and mutations.json
- scripts/parser_corpus_audit.py: main, corpus-before.json and corpus-before.md
- scripts/propose_case_inputs.py: main, its report file (default under proof/)
- scripts/suite_slice.py: main, its JSON measurement
- scripts/suite_extract.py: main, its report file

Test: scripts/suites/127_veldo_0259_installation.py row writers/home-as-tilde. Falsifier writers259-home-kept.

## Review F3 (AC1): the owner's identity and name, sites changed (fix round 1 item 3)

These files are outside the footprint the spec declared before this round; they were added to the spec's
footprint list with the writers above, for the History to record.

- scripts/migrate_to_veldo.py run_gate: committed the produced tree as a hard-coded name and personal
  email. Now commit_identity() reads git_identities.owner through .veldo/installation.py and refuses
  installation_missing:git_identities.owner when absent; the unused identity environment is gone.
- .veldo/naming.py CASE ruled_by: the owner's login, now the owner role id `owner`.
- .veldo/action_executor.py selfcheck: the executor credential id and confirmed_by named the owner, now
  `owner-executor` and `owner`.
- .veldo/incident_reconcile.py selfcheck validated_by: now `owner`.
- .veldo/tracker_intake.py selfcheck: the generated spec's owner, now the role id `owner`.
- The engine/.veldo copies of the four modules above, byte-identical.

Search scope: product code (.veldo, engine, scripts outside scripts/suites, bin, packs) for the owner's
names, logins and emails and for ambient identity reads. Owners elsewhere come from the authority store's
enrolled principals, not literals. Left for VELDO-0250 (records and live text it scrubs): comments and
recorded rulings in .veldo/*.py, .veldo/decisions/, .veldo/architecture.yaml approved_by,
.veldo/decision_reviews/, .veldo/events.jsonl, the spec frontmatter owner fields in specs/, and fixture
values in scripts/suites/.

## Review F1 and F2

- F1: the stage lists changed files with git diff names separated by NUL (the z option) and diffs each by literal pathspec, so a
  name Git quotes is judged. Rows ac2/quoted-names; falsifier personal259-quoted-names-skipped.
- F2: the base is the trunk the candidate declares, refs/remotes/origin/HEAD (a clone sets it; the lander
  points it at the trunk it gates against), or the base named on its command line. Nothing guesses main or master. With commits and no
  base the stage prints `personal setup: REFUSED personal_setup:no_base: ...` and exits 2. The migration's
  produced tree declares its one commit as its trunk. Rows ac2/declared-base; falsifiers
  personal259-base-guessed and personal259-no-base-silent.

## Open, not in this round's scope

- 50_git_environment fails git-boundary/no-private-git-invocations on .veldo/installation.py:222 and
  scripts/check_personal_setup.py `_git`, both direct subprocess git calls from the original build
  (present at 8dc8faf8). The review did not run that suite. Not fixed here (fix exactly the four items);
  the gate's unit stage will be red on it until it is.
- 101_veldo_0208_landing_reuse: two sandbox rows red, environmental, as the review recorded at the base.
- proof/VELDO-0259/manifest.json predates this round and does not list fix-round-1.txt or this file.
