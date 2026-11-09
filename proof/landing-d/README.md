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

## Local runs (landing-d2)

Run after landing-c gate 7 recorded its end (runner.log: "69f3a-landing-c-gate7 rc=1 end 2026-11-09T18:17:45Z").
Commit 167454a3, tree 36815f22, host dmitry-pc, Python 3.12.3, systemd 255. Each command ran on its own in
`systemd-run --user --scope -p MemoryMax=10G`, one after another. These are partial local runs, not gate evidence.
selftest exits 2 on every partial run by design; the tallies decide.

`python3 scripts/selftest.py --suite NAME` (suite rows, then the selftest total with the prerequisite closure):

- 130_veldo_0262_step_runner: 14 passed; 40 passed, 0 failed (9.6 s)
- 130_veldo_0275_approved_engine: 3 passed; 29 passed, 0 failed (0.1 s)
- 131_veldo_0275_stream_probe: 4 passed; 30 passed, 0 failed (0.2 s)
- 86_veldo_0186_setup_assets: 11 passed; 37 passed, 0 failed (19.1 s)
- 78_veldo_0060_claude_adapter (merged on both sides): 35 passed; 61 passed, 0 failed (24.4 s)
- 83_veldo_0154_factory_loop (merged on both sides): 14 passed; 40 passed, 0 failed (25.5 s)
- 91_veldo_0167_setup_records (loads the merged review_rows.py): 9 passed; 35 passed, 0 failed (31.7 s)

Teeth, `python3 scripts/check_teeth_mutations.py --finding N --summary FILE`, exit 0:

- 262: registered 12, executed 12, rejected 12, status passed, 697.6 s (host load 48.27 at the end).
  Summary: landing-d2-teeth-262.summary.json.
- 275: registered 8, executed 8, rejected 8, status passed, 160.7 s (host load 11.42 at the end).
  Summary: landing-d2-teeth-275.summary.json.

Nothing failed, so nothing was rerun or fixed. The raw logs were discarded:

- suite-130_veldo_0262_step_runner.log 9485 bytes sha256 c0ee553a8c5e81a10970c3d0968e959d97d69a885f215a81c1c7e3c3ceed85c8
- suite-130_veldo_0275_approved_engine.log 9489 bytes sha256 a2f5a7958bbe78d7bede61a88562f2ba2c583526e41677959ed9d264388380d3
- suite-131_veldo_0275_stream_probe.log 9687 bytes sha256 8b59549ff651f0dcdfeee4d14efb7275f6dea7597719b1c55bb5852bc1c5ed6f
- suite-78_veldo_0060_claude_adapter.log 10357 bytes sha256 f9b1ba8ec9c7c85fc75f02669a658ef98751b796ac10f3b1b288d4bb6c71772a
- suite-83_veldo_0154_factory_loop.log 10796 bytes sha256 ce81d5d36d77a4476a0e8aaa7c29c25ef1db7ba918f709bec0c986a3820be5f1
- suite-86_veldo_0186_setup_assets.log 9666 bytes sha256 41f3f04bd9791d59d09ad3665bd0b7e2fccafa1ba7456112d5986a2cd2b7f527
- suite-91_veldo_0167_setup_records.log 12134 bytes sha256 a0242c5c0948c5234f62d53aa3d86de803ba16cbacfead3c195e7e01a5a6017c
- teeth-262.log 149400 bytes sha256 5726389059802e4605b3d9f4460dce95456415daa3704b944860f7f137c5922c
- teeth-275.log 86715 bytes sha256 024ae977c50ad008e9fca65def222b6b8cd942f6bd71e12d76a72b410e2cca72
