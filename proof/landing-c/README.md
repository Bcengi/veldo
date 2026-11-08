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

## Merge 3: agent/claude/veldo-small-proof (VELDO-0270): STOPPED, not committed

The merge was attempted and aborted (`git merge --abort`); landing-c is at merge 2. Merges 4 to 6
(veldo-approval-scope, veldo-0274, veldo-0278) were not attempted.

Conflicts:

1. .veldo/policy.yaml (not in the lead's trial list; it follows from merge 2): main+0268 adds the
   top level `protected_refs:` list (VELDO-0268); the branch adds `proof:` with `max_file_bytes`
   and its own `proof.protected_refs` (VELDO-0270), at the same place after `fix_validation`. These
   are different keys and both can be kept.
2. scripts/parser_corpus_audit.py: the two changes to the same lines cannot both hold.
   - main 918e7c0e (VELDO-0259 fix round 1, e509bce0): lines 75-89 add `home_as_tilde`, line 134-135
     write the raw report `proof/VELDO-0110/corpus-before.json` through `home_as_tilde`.
   - branch a3e9c00c (VELDO-0270, 4600fda7): lines 75-98 add `summarize` and `write_summary`, lines
     143-147 replace that raw write with `write_summary(report, target)` to
     `corpus-before.json.summary.json` (no raw bulk in proof).
   - main's scripts/suites/127_veldo_0259_installation.py:612 requires
     `'scripts/parser_corpus_audit.py': {'main': 2}`, and its check at :629-646 counts `write_text`
     calls in `main()` whose argument goes through `home_as_tilde`. With the branch's summary write
     `main()` has one such call (corpus-before.md, line 169 on the branch, tilded by main), so
     suite 127 goes red; keeping main's raw write instead defeats VELDO-0270. Holding both needs a
     choice (for example a tilded summary plus a changed count in suite 127), which is left to the lead.
