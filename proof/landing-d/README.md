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
