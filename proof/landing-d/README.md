# landing-d

A landing candidate built on landing-c 9ea10fdf (landing-c lands first). Two reviewed branches, merged in order:

1. agent/claude/veldo-0262 (VELDO-0262, the step runner replaces LangGraph), merge commit 1727d623. Conflicts were
   generated lists only: scripts/check_teeth_mutations.py (every case from both sides kept),
   scripts/suites/manifest.json (every suite kept; 0262 and 0275 each add a different suite numbered 130),
   scripts/suites/requires.json (regenerated with scripts/run_scope.py --emit-requires) and specs/index.md
   (regenerated with scripts/update_index.py).
2. agent/claude/veldo-0275 (VELDO-0275, approved engine pinned by digest, qualification summaries, stream probe),
   merge commit 84b5889a. Eleven conflicted files, resolved keeping both tickets' behaviour: .veldo/init_scaffold.py
   and its engine copy keep 0262's leftover_runtime refusal and CLI default home and 0275's installation of the
   qualification tables and summaries; proof/VELDO-0127/factory.py keeps 0275's engines record install and landing-c's
   VELDO-0274 slice ownership; suites 86_veldo_0186 and 88_veldo_0127 keep both sides' rows (86_0186's expected
   runtime assets gained 0275's two installed summaries after the merge review, which found that row red); check_teeth_mutations.py
   and mutation_case_inputs.json keep every case and entry; specs/VELDO-0275 takes the 0275 branch's revised spec;
   requires.json and index.md regenerated. Checks before the commit: py_compile on changed files, engine copies
   byte-identical, template sync, and all 2941 registered mutation anchors occur exactly once.

The merge resolutions are reviewed separately (research/claude-runs/landing-d-merge-review-2026-11-08.md in the
lead's workspace). The full gate runs on this candidate after landing-c lands.

Protected paths against landing-c, judged by landing-c's policy (policy_check.protected_patterns, fnmatch over
git diff --name-only landing-c...HEAD): 145 files changed, none protected. VELDO-0272 (in landing-c) removed the
test machinery these tickets touch (scripts/mutation_case_inputs.json, scripts/agent_sandbox.json) from the
protected list.

## Merge record (landing-d2)

landing-d 05ba978f was merged again with --no-ff onto landing-c 39ddd9e5, the commit in landing-c's gate run, as
merge commit 98dad1db (branch landing-d2). The merge base is 9ea10fdf; landing-c adds 33 commits past it and
landing-d 52. Git reported no conflicts. Five files changed on both sides and merged automatically. Each was
checked by reading both diffs:

- proof/VELDO-0167/review_rows.py: landing-c changed older_engine (VELDO-0270, the archive is read from git by its
  summary), landing-d changed restart (VELDO-0275 record names). Different functions; both kept as written.
- scripts/check_teeth_mutations.py: landing-c's VELDO-0287 cases, the fix round 8 proof270-hook-bare-payload case,
  the selection267 factory, the worker's row details and the mutation leg; landing-d's VELDO-0262 and 0275 cases
  and retargeted graph rows. All kept. All 2948 registered anchors occur exactly once in the merged tree
  (materialize in baseline mode over every case).
- scripts/suites/78_veldo_0060_claude_adapter.py: landing-c's atomic children marker write sits in the fake's
  script loop, landing-d's changes are elsewhere in the file. Both kept.
- scripts/suites/83_veldo_0154_factory_loop.py: landing-c's limit step chosen at print time and its stop-request
  wait; landing-d's --ephemeral stream probe in the fake and the codex-tables.json name. Both kept.
- specs/index.md: landing-c's VELDO-0287 row and landing-d's VELDO-0262, 0275 and 0275b rows. The merged file is
  byte-identical to scripts/update_index.py --output on the merged tree.

landing-c's own files (VELDO-0287, the per-ref pre-push hooks, approval_scope.from_commit bd8a4bc5 in
.veldo/policy.yaml, the manifests) are untouched by landing-d, so they carry over byte for byte. No landing-c file
names anything landing-d removed (LangGraph, control_graph_langgraph.py, control_graph_install.py,
control_graph_lock.py, the *-qualification.json records) except review_rows.py's restart, which is landing-d's
own change. The engine copies of validate.py and policy_check.py stay identical to .veldo/.

## Protected paths (landing-d2)

The union of the protected_paths in .veldo/policy.yaml at landing-c 39ddd9e5 (52 patterns) and at main 918e7c0e
(58 patterns), 99 distinct, matched as policy_check.glob_covers matches them (fnmatch on the pattern, and on the
pattern with its trailing stars widened to one) over git diff --name-only 39ddd9e5...HEAD (146 files). Three files
are protected, all by main's patterns only; landing-c's policy alone protects none of the 146:

- engine/scripts/agent_sandbox.json (main: engine/scripts/agent_sandbox.json)
- scripts/agent_sandbox.json (main: scripts/agent_sandbox.json)
- scripts/mutation_case_inputs.json (main: scripts/mutation_case_inputs.json)
