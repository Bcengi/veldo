# landing-c: merge record

Branch landing-c, started at main 918e7c0e. Every merge is `git merge --no-edit`; no rebase, no
cherry-pick, no force. Line numbers are in the tree of the merge commit named.

The gate lock (~/.local/state/core-gates/.gate.lock) was held when each merge commit was
checked, so no suite ran here: the suites whose files conflicted are listed in
[pending_runs.sh](pending_runs.sh) (summary lines go to pending-summary.txt, logs to /tmp/lc-*.log).
The full gate was not run (the lead runs it).

## Merge 1: agent/claude/veldo-0267-0268 (VELDO-0267), commit 4495906a

| File | Conflict | Resolution |
| --- | --- | --- |
| scripts/check_gate_mutations.py:1356-1360 | main (VELDO-0285, landing-b) passes `planned` to `control_jobs`; the branch adds the canary name loop before the same call, which still passed `deadlines` | Both: the branch's canary loop (1356-1359), then `control_jobs(fresh, group_for, prepared_cases, planned, claims)` (1360) |
| engine/scripts/check_gate_mutations.py:1356-1360 | the same | Copied from scripts/; the two copies are byte-identical (cmp) |
| scripts/suites/manifest.json:1845 | both sides appended suites at the end | Every suite kept: main's 200 in main's order, then the branch's 140_veldo_0267_mutation_selection; no suite was changed by both sides |
| scripts/suites/requires.json:668 | the same | Regenerated with `python3 scripts/run_scope.py --emit-requires`; the only change from main is the new suite's entry |

specs/index.md merged without a conflict but placed the VELDO-0267 and VELDO-0268 rows out of
order; it was regenerated with `python3 scripts/update_index.py` (rows now at specs/index.md:198-199).

Checks: `python3 -m py_compile` on every changed .py, `bash -n` on scripts/verify.sh and
proof/VELDO-0267/pending_runs.sh: all clean. Pending suites: 140_veldo_0267_mutation_selection,
112_veldo_0215_case_deadlines.

## Merge 2: agent/claude/veldo-0268 (VELDO-0268), commit 58133876

| File | Conflict | Resolution |
| --- | --- | --- |
| scripts/check_teeth_mutations.py:12490-12694 | VELDO-0267 (already on landing-c from merge 1) and VELDO-0268 each append their case block at the same place in `cases()` | Both blocks: VELDO-0267's (12490-12550), a blank line (12551), VELDO-0268's (12552-12694). Every one of the 49 cases of findings 267 and 268 has its anchor exactly once in its target module after the merge (static check, not a mutation run) |
| scripts/suites/manifest.json:1854 | both sides appended suites | Every suite kept; 141_veldo_0268_protected_refs appended after 140 |
| scripts/suites/requires.json:671 | the same | Regenerated with `run_scope.py --emit-requires` |

Not in the lead's trial list: check_teeth_mutations.py conflicts here only because merge 1 already
added VELDO-0267's block. specs/index.md regenerated: no change. .veldo/policy_check.py and its
engine copy, and the three veldo-guard.sh copies, auto-merged and stay byte-identical.

Checks: py_compile clean; `bash -n` clean on the three veldo-guard.sh copies and
proof/VELDO-0268/pending_runs.sh. Pending suite: 141_veldo_0268_protected_refs.

## Merge 3: agent/claude/veldo-small-proof (VELDO-0270), commit 14b5ecb5

An earlier attempt stopped on scripts/parser_corpus_audit.py (main's raw write through
`home_as_tilde`, VELDO-0259, against the branch's summary write, VELDO-0270). The lead chose a tilded
summary, and the merge was then made and committed.

| File | Conflict | Resolution |
| --- | --- | --- |
| scripts/parser_corpus_audit.py:178 | main writes the raw report through `home_as_tilde` (VELDO-0259); the branch replaces it with the summary `corpus-before.json.summary.json` (VELDO-0270) | Both: `main()` writes the summary, and writes it through `home_as_tilde`: `target.write_text(home_as_tilde(summary_text(report, target)))`. `main()` still has two `write_text` calls through `home_as_tilde` (178, and 200 for corpus-before.md), so suite 127_veldo_0259's writer count (scripts/suites/127_veldo_0259_installation.py:612, `{'main': 2}`, checked at 630-646) holds unchanged. `write_summary` (124-129) writes through it too |
| .veldo/policy.yaml:146-160 | main+0268 add `protected_refs:` (VELDO-0268); the branch adds `proof:` (VELDO-0270) at the same place | Both keys: `protected_refs` (146-152), then `proof:` with `max_file_bytes` and `proof.protected_refs` (153-160) |
| scripts/suites/manifest.json:1863 | both sides appended suites | Every suite kept (203); 129_veldo_0270_small_proof appended after 141 |
| scripts/suites/requires.json:674 | the same | Regenerated with `run_scope.py --emit-requires` |

Checks: py_compile clean. Pending suites: 127_veldo_0259_installation, 129_veldo_0270_small_proof.

## Merge 4: agent/claude/veldo-approval-scope (VELDO-0272)

Merge base afa292f0. Line numbers are in the tree of the merge 4 commit.

| File | Conflict | Resolution |
| --- | --- | --- |
| .veldo/policy_check.py:591-681 | main (VELDO-0267) adds `accept` to `valid_approval_for` and inlines its checks; the branch moves the checks into `approval_refusal` (603-650, stricter: an approver must name somebody, a producer that cannot be determined refuses every approval, identities normalized) and adds `spec_id` and `owner_approved` (591) | Both: the branch's `owner_approved` and `approval_refusal`; `valid_approval_for(commits, path=None, producer=None, spec_id=None, accept=None)` (653) judges through `approval_refusal`, then `accept`. The docstring keeps both notes. A self-approval refusal is tested last, on its own line `continue  # self-approval: the approver produced the work` (679), so the VELDO-0267 falsifier (suite 140 ac4-4-self-approval-accepted, teeth selection267-self-approval-accepted at scripts/check_teeth_mutations.py:12547) still finds its anchor and still makes a self-approval count; the result is the same as `approval_refusal(...) is None` and `accept`. protected_refs (VELDO-0268, 106-175) and `approval_rule` (999, VELDO-0267) are unchanged; `approval_rule` now passes through the stricter refusal (fail closed when its producer cannot be determined) |
| engine/.veldo/policy_check.py | the same | Copied; byte-identical (cmp) |
| .veldo/policy.yaml:16-93 | main's protected list (with VELDO-0267's five mutation_selection/mutation_nightly entries and VELDO-0268's packs/claude/scripts/veldo-guard.sh) against the branch's narrowed list | Lead decision: the union. The branch's narrowed list (16-80), then the six entries with a comment naming the decision (81-93). None of the six is in the spec's removed list |
| .veldo/policy.yaml:124-147 | main+0270 `protected_refs:` and `proof:` against the branch's `approval_scope:` | All three keys kept: `protected_refs` (124), `proof` (136), `approval_scope` (146) |
| specs/VELDO-0272-...md:13, :251 | follows from the union (lead) | protected_paths gains the six entries; one History line (251) |
| scripts/suites/129_veldo_0272_approval_scope.py:164-168 | follows from the union (lead) | `expected` gains the six entries, so the exact-match check holds on the union; nothing else in the suite changed. Static check: the policy list equals the expected set, no duplicates, none removed |
| scripts/suites/101_veldo_0208_landing_reuse.py:1311-1312 | main counts 48 listed unconfined suites (landing-b added 128_veldo_0254 and 129_veldo_0254) and checks the dispatcher in the installed list; the branch drops that installed-list check (the dispatcher left the list) and counts 46 | Both: the branch's check (dispatcher in VELDO-0208's own protected_paths only) and main's count 48 (scripts/gate_unconfined.json lists 48) |
| scripts/check_teeth_mutations.py:12490-12869 | VELDO-0267 and VELDO-0268 blocks against VELDO-0272's block at the same place in `cases()` | Both blocks: 0267 and 0268 (12490-12694), a blank line, 0272 (12696-). Static check: every case of findings 267, 268, 270 and 272 (87) has its anchor exactly once in its target module; no duplicate case names (2935) |
| scripts/suites/manifest.json:1872 | both sides appended suites | Every suite kept (204, union of main's 203 and the branch's 193); 129_veldo_0272_approval_scope after 129_veldo_0270; no suite changed by both sides |
| scripts/suites/requires.json:677 | the same | Regenerated with `run_scope.py --emit-requires` |
| specs/index.md:201 | both sides | Regenerated with `python3 scripts/update_index.py` (441 specs); the only change is the VELDO-0272 row |

Staged auto-merges checked against both parents: .veldo/validate.py and .veldo/init_scaffold.py (and
their engine copies, byte-identical) changed on both sides and equal a clean three-way merge (diff3);
every other staged file equals the branch's version and was not changed on main.

Checks: py_compile clean on every changed .py; `bash -n` clean on proof/VELDO-0272/pending_runs.sh
and proof/landing-c/pending_runs.sh. Pending: suites 129_veldo_0272, 140, 141, 01, 10, 101 and the
teeth cases of findings 267 and 272.

## Merge 5: agent/claude/veldo-0274 (VELDO-0274), commit f54075a8

Merge base afa292f0 (branch tip cf742f6a). Line numbers are in the tree of the merge 5 commit.

| File | Conflict | Resolution |
| --- | --- | --- |
| scripts/check_teeth_mutations.py:12490-12903 | VELDO-0267, 0268 and 0272 blocks (landing-c) against VELDO-0274's block at the same place in `cases()` | Both: landing-c's blocks (12490-12867), a blank line, VELDO-0274's four cases (12869-12903). The result less the 0274 block equals landing-c's side exactly; the branch's only change to the file is that block. Static check: no duplicate case name; each of the four 0274 anchors occurs exactly once in its target (proof/VELDO-0127/factory.py three, suite 86 one) |
| scripts/suites/manifest.json:1890 | both sides appended suites | Every suite kept (205: landing-c's 204 in its order, then 129_veldo_0274_factory_slices). No suite removed by either side, none changed by both; the branch's edits to 88, 89 and 90 and landing-c's to 125 are kept; every other key equals landing-c's |
| scripts/suites/requires.json:680 | the same | Regenerated with `run_scope.py --emit-requires`; the only change from landing-c is the 0274 entry |
| specs/index.md | auto-merged with VELDO-0273, 0274 and 0278 to 0280 in the draft section | Regenerated with `python3 scripts/update_index.py` (449 specs): the five ready rows move to the ready section |

Staged auto-merges checked against the base: scripts/gate_unconfined.json changed on both sides and
keeps both (landing-c's 128_veldo_0254 and 129_veldo_0254, the branch's 129_veldo_0274_factory_slices);
every other staged file (proof/VELDO-0127/factory.py, suites 86, 88, 89, 90, the new suite, proof and
specs) was not changed on landing-c since the base and equals the branch's version.

Open, for the lead (not changed here): suite 101 will go red. scripts/gate_unconfined.json now lists 49
suites, 47 whole. scripts/suites/101_veldo_0208_landing_reuse.py:1265-1269 (`control_plane`) does not
name 129_0274, so 1277 (`len(expected_whole) == 46 and whole == expected_whole`) fails, and 1312
(`len(listed_files) == 48`) fails. The branch alone was red the same way (its base counts 44 and 46
against 45 and 47 listed). Both changes hold if suite 101 gains '129_0274' and the counts 47 and 49.

Checks: py_compile clean on every changed .py; `bash -n` clean on proof/landing-c/pending_runs.sh.
Pending: suites 129_veldo_0274, 86, 88, 89, 90, 101, teeth finding 274 (confined) and
`check_gate_mutations.py --finding 274` (the unconfined leg VELDO-0274's proof names).

## Merge 6: agent/claude/veldo-0278 (VELDO-0278), commit 2959a002

Merge base b40b3123 (branch tip 4ceb78f5). Line numbers are in the tree of the merge 6 commit.

| File | Conflict | Resolution |
| --- | --- | --- |
| .veldo/policy.yaml:94-97 | landing-c's narrowed list (VELDO-0272) plus the six union entries against the branch, which keeps the pre-0272 list and moves `scripts/check_first_use.py` to `scripts/parked/estimation/check_first_use.py` | Lead rule from merge 4, the union: landing-c's list, then the parked entry with a comment (94-97). Every other entry only the branch side holds is in VELDO-0272's removed list (static check), and `scripts/check_first_use.py` itself stays off (0272 removed it; suite 129_veldo_0278:155-157 requires the parked line and the old path's absence). 52 entries, no duplicate |
| specs/VELDO-0272-...md:13, :253 | follows from the union (lead) | protected_paths gains the parked entry; one History line (253) |
| scripts/suites/129_veldo_0272_approval_scope.py:167-170 | follows from the union (lead) | `expected` gains the parked entry; nothing else changed. Static check: the policy list equals the expected set, none of the 29 removed paths present, counts 11, 17, 29 unchanged |
| scripts/suites/113_veldo_0220_gate_host.py:85-87 | landing-c adds the `check_personal_setup.py` stub (VELDO-0259); the branch drops the `check_first_use.py` stub | Both: no `check_first_use.py` stub, `check_personal_setup.py` kept (86) |
| scripts/suites/114_veldo_0220_gate_scope.py:114-116 | the same | The same (115). landing-b's round 8 fix to inside-a-scope is unchanged: unique unit per run (215), the 180 s ceiling (219), the lock-release wait (249 and after the case) |
| scripts/suites/101_veldo_0208_landing_reuse.py:1272, 1280, 1316 | landing-c counts 46 whole; the branch adds `declared_commands_na` (integration is na) and counts 44 | Both: the branch's `declared_commands_na` check with 47 whole (1280), `'129_0274'` added to `control_plane` (1272) and 49 listed (1316). Counted from scripts/gate_unconfined.json: 49 entries, 47 whole, two rowed (100, 101); 0278 adds none. Static check: `expected_whole` from the manifest equals the 47 whole entries |
| scripts/suites/manifest.json:1821 | the branch removes the nine parked suites (111_veldo_0214, 15_warp_1402 to 1409, 16_warp_1403, files moved to scripts/parked/estimation/) and appends 129_veldo_0278; landing-c appended its 13 suites | Three-way: landing-c's order, less the nine the branch parked, then 129_veldo_0278_parked_estimation (197 suites). No suite changed by both sides; every listed file exists and no suite file is unlisted |
| scripts/suites/requires.json:656 | the same | Regenerated with `run_scope.py --emit-requires` (196 suites): the nine parked entries leave, 129_veldo_0278 joins, nothing else changes |
| specs/index.md | both sides | Regenerated with `python3 scripts/update_index.py` (449 specs); equals landing-c's (VELDO-0278 at 204) |

Staged auto-merges: scripts/check_teeth_mutations.py, scripts/gate_graph.json, scripts/gate_unconfined.json,
scripts/verify.sh and suite 114_veldo_0216 changed on both sides and each equals a clean diff3 of base,
landing-c and branch; every other staged file was changed by the branch only. check_teeth_mutations.py:
every case of landing-c and of the branch is present (2873); the nine absent are the branch's own
removal under VELDO-0278 AC (spec lines 70-73: the seven VELDO-0214 cases of parked suite 111 and the
two judgment_load.py cases), not a merge drop; the three 0278 cases (11581-) each find their anchor
once. scripts/gate_legs.py and gate_schedule.py equal their engine copies.

Checks: py_compile clean on every changed .py; `bash -n` clean on proof/landing-c/pending_runs.sh.
Pending: suites 129_veldo_0278, 08, 113_veldo_0220, 114_veldo_0220, 114_veldo_0216, 101, 129_veldo_0272
and teeth finding 278.

## Protected paths landing-c touches against main

Read at commit 81564c7d. Patterns: `python3 -c 'import sys; sys.path.insert(0,".veldo"); import
policy_check as p; print(p.protected_patterns())'` (landing-c's policy, 52 patterns). Files:
`git diff --name-only main...HEAD` (156 paths, renames under their new name). Each file matched with
`fnmatch` against every pattern: 14 match.

| Path | Pattern | Protected on main too |
| --- | --- | --- |
| .veldo/control_verification.py | itself | yes |
| .veldo/policy.yaml | itself | yes |
| .veldo/policy_check.py | itself | yes |
| engine/.veldo/control_verification.py | itself | yes |
| engine/.veldo/policy_check.py | itself | yes |
| engine/scripts/mutation_nightly.py | itself | no (VELDO-0267) |
| engine/scripts/mutation_selection.py | itself | no (VELDO-0267) |
| engine/scripts/veldo-guard.sh | itself | yes |
| packs/claude/scripts/veldo-guard.sh | itself | no (VELDO-0268) |
| scripts/mutation_nightly.py | itself | no (VELDO-0267) |
| scripts/mutation_selection.json | itself | no (VELDO-0267) |
| scripts/mutation_selection.py | itself | no (VELDO-0267) |
| scripts/parked/estimation/check_first_use.py | itself | no (VELDO-0278) |
| scripts/veldo-guard.sh | itself | yes |

Not in the instructed listing, recorded because a landing is judged by the trunk's policy as well
(VELDO-0058): main's own list (`git show main:.veldo/policy.yaml`) also protects 12 more paths landing-c
changes, all test machinery VELDO-0272 removes: engine/scripts/check_gate_mutations.py,
engine/scripts/gate_legs.py, engine/scripts/gate_schedule.py, engine/scripts/verify.sh,
scripts/check_gate_mutations.py, scripts/gate_graph.json, scripts/gate_legs.py, scripts/gate_schedule.py,
scripts/gate_unconfined.json, scripts/mutation_case_inputs.json, scripts/selftest.py, scripts/verify.sh;
and the deleted scripts/check_first_use.py (renamed by VELDO-0278, `--no-renames --diff-filter=D`).

## Fix round 1

Source: the merge review landing-c-merge-review-2026-11-08.md (MERGES SOUND with findings). Findings 1,
2 and 3 fixed in commit 00d2731e; finding 4 is not a defect and is left as it stands.

1. scripts/check_teeth_mutations.py, case gate-output-land-does-not-bind-refs: the anchor now matches the
   current .veldo/lander.py call (old and new strings gain `, base=c["watermark"]`), so the mutation
   applies again. Checked by applying the mutation by hand: the refs-bound row went red; lander.py was
   restored.
2. .veldo/policy_check.py approval_rule (engine copy byte-identical, `cmp` clean): the producer is taken
   as main() does under 0272 N2: `files = changed_files(); producer = approval_producer(push_producer(
   landing_specs(files)), files, commits)`, no longer `producer_for(_head_spec_id())`. Suite
   129_veldo_0272_approval_scope gains rows `AC3 approval/rule-producer`: the HEAD verdict belongs to
   another spec (producer other) and the rule still refuses the landing spec producer's own approval
   (red before the fix); the owner's approval of the same push is found. Falsifier
   scope272-approval-rule-producer-from-head registered under finding 272.
3. .veldo/policy.yaml proof.protected_refs: set to 0268's protected_refs patterns (refs/heads/main,
   master, release, release/*, release-*, refs/tags/*); the smaller change than teaching proof_size.py a
   fallback. Suite 129_veldo_0270_small_proof gains `p270/guard/push-to-release-size-checked`: a push of
   a 2 MB proof file to refs/heads/release under this repository's own proof policy is refused with
   proof_file_over_limit (red before the fix).

Checks: py_compile clean on every changed .py; the two policy_check.py copies identical.
Pending (gate lock busy, in pending_runs.sh): suites 129_veldo_0272_approval_scope and
129_veldo_0270_small_proof, teeth findings 267 and 272.

## Fix round 2

Source: the full gate at 1cef8eb1 (lock job 52d, log landing-c-1cef8eb1-verify.log, 1563 lines), RED on
unit, generated, personal_setup, mutation and contracts.

1. unit (both legs) and mutation: one cause. closure() (.veldo/control_service.py:597-652) refused
   `invalid_input:closure:unresolved` at policy_check.py:993 (log 1047 confined, suite v28_install; 1131
   unconfined, suite v138_service); the mutation driver_error (log 337) is suite 58's baseline failing the
   same way. VELDO-0267's `_nightly_reader` called `spec_from_file_location` with a Path variable, which
   names no file for certain (_Loads, control_service.py:471-473). A literal 'mutation_selection.py'
   would resolve but then refuse as `closure:absent`, since .veldo holds no such module. closure() already
   has the exemption for this case: a module-level EXTERNAL_LOADERS tuple naming loader helpers that load
   a file from outside every installed directory by design (control_service.py:405-409, 444-449, 562-564;
   precedent control_verification.py:73, `_policy_main`). `_nightly_reader` now calls
   `_installation_module(alias, path)`, declared in `EXTERNAL_LOADERS = ("_installation_module",)` in
   policy_check.py; closure() is unchanged. Behaviour unchanged: reads scripts/mutation_selection.py
   beside the installation when present, returns None without it. Checked: closure() over engine/.veldo
   and .veldo returns 160 modules (policy_check.py in, mutation_selection.py not); `_nightly_reader()`
   loads the module here and returns None in a copy of .veldo with no scripts/ beside it; the two
   policy_check.py copies are identical (cmp); py_compile clean.
2. generated: another cause (log 1173). VELDO-0278 (merge 6) changed scripts/selftest.py (272 to 332
   lines) without regenerating proof/WARP-0716/crossing-state.md. Updated to the generator's output: the
   file now equals `python3 scripts/suite_survey.py --emit-report` (diff empty).
3. personal_setup: another cause (log 1262-1268). Seven home paths carried in by the merges and this
   README: proof/VELDO-0267/README.md:144, proof/VELDO-0268/README.md:95, proof/VELDO-0268/pending_runs.sh:6,
   proof/landing-c/README.md:6, specs/VELDO-0270-...md:171, specs/VELDO-0272-...md:150 and :236. Each
   now uses `~/` (prose) or `"$HOME/` (the script's cd); none of these files exists on main and none is
   bound by a manifest digest.
4. contracts: another cause (log 1309-1319, 11 problems), not fixed here. Five specs (VELDO-0239, 0254,
   0256, 0257, 0259) are critical with no risk_areas (critical_without_area), and six (VELDO-0273, 0274,
   0278, 0279, 0280, 0285) declare human_approval not_required where the VELDO-0272 rule computes required
   (approval_flag_below_rule). Both come from VELDO-0272's validator rule meeting specs merged from other
   branches. Fixing them sets a spec's approval flag or risk areas, which is the owner's call under
   VELDO-0272 (Existing specs), not a merge resolution; left for the lead.

Pending (gate lock busy, in pending_runs.sh): suites 58_veldo_0028_effects and
71_veldo_0138_channel_service.

## Fix round 3

Source: the full gate at 9ea10fdf (lock job 54aa, log landing-c-9ea10fdf-verify.log, 6023 lines), RED on
unit (both legs) and mutation; every other stage passed. The confined leg printed no count: it stopped at
suite 99's traceback (log 2045-2058), so no suite after 99 ran in that leg. The unconfined leg reported
`selftest: 1088 passed, 15 failed` (log 2422). The mutation stage stopped on one driver_error (log 5736).

### Failing rows

| Leg | Suite | Row(s) | Log | First failure line | Cause |
|---|---|---|---|---|---|
| confined | 05_tracker_routing_resolver_veldo | intake renders a VALID draft; injection-attempt draft still valid; requirement intake renders a VALID draft; bridge writes a VALID status:draft spec | 1168, 1171, 1174, 1177 | 1167: `WARP-9601-x.md: approval_flag_below_rule: ... basis: footprint absent` | E |
| confined | 07_warp_1103_completion_mandatory | AC6 no-corpus-sweep (ready and shipped placeless spec) | 1226, 1228 | 1225: `specs/S.md: approval_flag_below_rule: ... footprint absent` | D |
| confined | 13_warp_0623_codified_live | WARP-0724 AC1 plan lane; WARP-0724 AC5 depends_on typed | 1479, 1500 | 1478: `WARP-9729.md: approval_flag_below_rule: ... footprint absent` | D |
| confined | 14_warp_0717_subset_runner | AC1 `--suite NAME` runs exactly the closure | 1506 | the row runs suite 05 alone and expects exit 2 (partial, passed); 05 is red | E |
| confined | 18_veldo_0012_behaviour_floor_contract | AC6 floor pattern; AC6 committed-change boundary | 1515, 1516 | the rows assert .veldo/floors/* is protected | C |
| confined | 27_veldo_0010_evidence_provenance | AC5 stamp key set equals run_scope's payload | 1747 | the stamp carries `mutation`, the payload does not | F |
| confined | 50_git_environment | git-boundary/no-private-git-invocations | 1753 | check_git_boundary: 8 call sites (below) | G |
| confined | 53_veldo_0123_mutations | gate/both-mutation-drivers-are-required; gate/removed-teeth-redden-the-gate | 1754, 1755 | the fixture gate's mutation stage cannot load scripts/mutation_selection.py | H |
| confined | 59_veldo_0043_graph | graph/isolated-enforcement | 1765 | policy_check entry: refused_imports `['_wmi']` (reproduced here) | I |
| confined | 62_veldo_0045_runtime | enforcement/no-runtime | 1804 | same refused import in the policy_check entry (reproduced here) | I |
| confined | 99_veldo_0205_reuse | crash, whole suite | 2045-2058 | check_gate_mutations.py:1550 run_stage: `'ControlledWorkers' object has no attribute 'coverage'` | A |
| unconfined | 64_veldo_0050_proof | accepted-before-offer, actual-checks, build-only-no-landing, fresh-reviewer-resolves, contextual-refusals, owning-services, observations | 2106-2112 | executor.merge_ready computes required for the fixture units (no footprint) | D |
| unconfined | 91_veldo_0167_setup_records | installed-record, late-subscriber, older-host, older-engine-host, interrupted-record-write, hints-without-api, record-hint-counts, upgrade-restart-answer | 2289-2303 | 2288: `FileNotFoundError: .../proof/VELDO-0189/older/8bc34e94.tar.gz` | B |
| mutation | 113_veldo_0220_gate_host | baseline of case gate_host.py | 5736 | worker stderr: lander.py:797 gate `base=c["watermark"]`: `KeyError: 'watermark'` | J |

Suite 100_veldo_0207_case_reuse has the same fake worker as 99 (cause A) and is fixed with it.

### Causes

None is a red main 918e7c0e also has: every cause is code that exists only on landing-c (VELDO-0267,
0270 and 0272 came in through its merges). All are landing-c defects except E, which is a rule question.

- A (VELDO-0267 vs the fake workers): run_stage reads `workers.coverage` after every stage; the real
  Workers sets it to None, the hand-written ControlledWorkers of suites 99 and 100 did not. Fixed: both
  fakes set `self.coverage = None`, the real class's default.
- B (VELDO-0270 vs VELDO-0167): 0270 removed proof/VELDO-0189/older/8bc34e94.tar.gz; 0167's review rows
  still read it from the tree. Fixed: proof/VELDO-0167/review_rows.py reads it as suite 86's fixture()
  does, through its summary from the commit that keeps it (`git show readable_at:original_path`), matched
  against the summary's sha256 and digests.json; a failed read reddens that row only.
- C (VELDO-0272, lead decision): 0272 removed .veldo/floors/* from the protected list under the owner's
  narrowed approval scope (Telegram 39707, 39708). Suite 18's floor row now asserts the floor pattern is
  ABSENT here (re-adding it reds the row); the boundary row keeps its measurement with a tracked
  settlement as the additive control (tracked settlement enumerated and matched, untracked settlement
  matched and not enumerated, both floors matched by no pattern). The settlement row and the engine
  template's two entries are unchanged.
- D (VELDO-0272 footprint-absent rule vs fixtures): fixtures that must be gate-legal declared no
  footprint and not_required. Fixed per suite, the rule untouched: 13's `_d724_gatelegal` and the AC5
  shape head carry `footprint: [src/fixture.py]` (no protected list in that fixture; without it the bad
  shapes in AC5 were refused for the footprint, not their shape); 64's units carry `footprint: ["src/**"]`
  (the lead's fix for 67, 69 and 86, 7dc0055b); 07's two placeless specs declare `human_approval:
  required`, the computed flag, since with a contract present a footprint without a placement is
  refused. Checked: each fixture spec validates and the same spec without the change is refused
  `footprint absent`.
- E (VELDO-0272 rule vs a PRODUCTION writer): NOT FIXED, reported. Suite 05's drafts are written by
  .veldo/tracker_intake.py (:107 and :232), which renders `human_approval: not_required` with no
  footprint; an intake draft is a new file, so it is in scope and the rule refuses it. This is not a
  fixture: every intake and bridge draft in any repository fails check_spec. The choice is the owner's:
  the writer renders the computed flag (required) until a footprint is declared, or the rule exempts
  drafts. Suite 14 stays red with it (it runs 05 alone).
- F (VELDO-0267): this repository's gate stamps a `mutation` block when its mutation stage ran;
  run_scope.verify_stamp_payload, which suite 27 holds equal to the stamp, did not know it. Fixed:
  the payload takes `mutation_ran` and `mutation`, present exactly when the stage ran, as verify.sh
  writes it; suite 27 declares per gate that scripts/verify.sh stamps it and engine/scripts/verify.sh
  does not (a template that gains it reds the row until declared).
- G (VELDO-0267 and 0272 vs the Git boundary): eight call sites ran Git outside the form
  check_git_boundary accepts: scripts/mutation_selection.py:128 and mutation_nightly.py:158 (plain
  subprocess), .veldo/landed_summary.py:45 (`_G.run`), .veldo/validate.py:159 (`_git_process_module().run`),
  each with its engine copy. Fixed: all go through `_git_process.run`; the two scripts load
  .veldo/git_process.py beside them on first use. Checked: the boundary check passes; both scripts'
  Git calls return the expected commit.
- H (VELDO-0267): check_gate_mutations.py main loads the authority's scripts/mutation_selection.py
  unconditionally, but that file is neither in the authority identity nor in the scaffold, so a fixture
  authority (suite 53) or an installed repository crashes the stage. Fixed: without the module the stage
  runs the full sweep and says so (never fewer cases); with it, unchanged.
- I (VELDO-0272 fix 5, f4901ce3): policy_check's `_projection_paths` executed lander.py to read
  PROJECTIONS; lander loads claim.py, both import uuid, which imports platform, whose `_wmi` probe the
  isolated-enforcement finder refuses (not in this CPython 3.12.3's stdlib_module_names). Fixed:
  PROJECTIONS is read as a literal from lander.py's source (ast), never executed; the finder is
  unchanged. Checked: control_graph_isolation.py over this tree passes every entry; the runtime
  enforcement run passes the policy_check entry; `_projection_paths()` returns `{specs/index.md}`.
- J (VELDO-0267 vs suite 113): Lander.gate passes `c["watermark"]` as the gate's selection base; 113
  hand-builds a candidate without the watermark sync_main always sets. Fixed: the fixture candidate
  carries `watermark` (its one commit). The other hand-built candidate (suite 140) already does.

The 113 baseline is confirmed as this KeyError (the mutation receipt's stderr_tail for case
113_veldo_0220_gate_host.py:gate_host.py:False:baseline); that suite never ran in the unit legs.

Checks run here: py_compile on every changed file; `cmp` clean for every mirrored pair
(check_gate_mutations.py, mutation_selection.py, mutation_nightly.py, validate.py, landed_summary.py,
policy_check.py); no teeth mutation anchors on a changed line.

Pending (gate lock held by another repository's gate, in pending_runs.sh): every suite in the table,
129_veldo_0272_approval_scope, 140_veldo_0267_mutation_selection, teeth findings 267 and 272, and a full
gate (the confined leg never reached the suites after 99).

## Fix round 4

Cause E (round 3) decided by the lead: the VELDO-0272 rule stands and the writer follows it.

- .veldo/tracker_intake.py and its engine copy: draft_spec_from_item and draft_spec_from_requirements
  render `human_approval: required` (was not_required). An intake draft declares no footprint, and the
  rule computes required when the footprint is absent; once a footprint is added, the author or the
  rule's report sets the flag from it. The rule (validate.py check_approval_scope, policy_check
  approval_bases) is unchanged.
- Suites 05 and 14: no row asserted the old not_required default (their drafts reach the rule through
  check_spec, suite 05 at :629, :645, :708 and :854), so no expectation changed.

Checks run here: py_compile on both copies; `cmp` clean for the pair; no teeth or gate mutation names
tracker_intake.py.

Pending (gate lock busy, in pending_runs.sh): suites 05 and 14, now expected green.
