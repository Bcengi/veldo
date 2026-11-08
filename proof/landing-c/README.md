# landing-c: merge record

Branch landing-c, started at main 918e7c0e. Every merge is `git merge --no-edit`; no rebase, no
cherry-pick, no force. Line numbers are in the tree of the merge commit named.

The gate lock (/home/dmitry/.local/state/core-gates/.gate.lock) was held when each merge commit was
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
