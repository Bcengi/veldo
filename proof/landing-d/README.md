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

## Merge record (landing-d2 onto 8955553d)

landing-c 8955553d (fix rounds 9, 9b and 9c, eight commits past 39ddd9e5) was merged with --no-ff into
landing-d2 e26ede48 as merge commit d86aa51d. Git reported six conflicts, all in proof/VELDO-0127:
claude-live.json, codex-live.json and the four resources-*.json records.

Each of the six records the sha256 of five modules in .veldo. landing-c retook them in round 9c because round 9
changed control_launch.py. landing-d had retaken them for its own changes to all five modules. The merged
control_launch.py (sha256 267fc7d2) carries both changes, so neither side's records describe the merged tree.

Resolution: all six keep landing-d's version. It matches four of the five merged modules and was captured on the
0275 engine pin; landing-c's version matches none. The six are stale by the control_launch.py digest and have to
be retaken on the merged tree: the resource records with .veldo/qualify.py, the two live captures with
proof/VELDO-0127/live.py and a login. landing-c's versions of these six files do not survive the merge, and
cannot: they record a tree without VELDO-0262 and 0275.

Three files changed on both sides and merged automatically. Each was checked by reading both diffs:

- .veldo/control_launch.py and its engine copy: landing-c's Runner.honor_stops (the ask is recorded before it is
  made) and Launch.can_stop; landing-d's VELDO-0275 stream probe, accept wait and stop cause. Different functions.
  The two copies are byte-identical.
- scripts/check_teeth_mutations.py: landing-c re-anchored launch131-stop-recorded-unasked; landing-d's cases are
  elsewhere. All 2948 registered anchors occur exactly once in the merged tree (materialize in baseline mode).
- scripts/suites/86_veldo_0189_engine_upgrade.py: landing-c's Bridge.close shuts the listener down and joins its
  thread; landing-d's VELDO-0262 rows and the engine_not_approved refusal. Both kept.

Everything else landing-c changed (suite 66_veldo_0042, the six manifests of VELDO-0267, 0268, 0270, 0272, 0274
and 0278, proof/landing-c/README.md) is untouched by landing-d and is byte-identical to 8955553d.

## Protected paths (landing-d2 onto 8955553d)

This replaces the list above. The union of the protected_paths in .veldo/policy.yaml at landing-c 8955553d
(52 patterns) and at main 918e7c0e (58 patterns), 99 distinct, matched the way policy_check.glob_covers matches
(fnmatch on the pattern, and on the pattern with its trailing stars widened to one) over
git diff --name-only 8955553d...HEAD (148 files). Three files are protected, all by main's patterns only;
landing-c's policy alone protects none of the 148:

- engine/scripts/agent_sandbox.json (main: engine/scripts/agent_sandbox.json)
- scripts/agent_sandbox.json (main: scripts/agent_sandbox.json)
- scripts/mutation_case_inputs.json (main: scripts/mutation_case_inputs.json)

## Local runs (landing-d2 onto 8955553d)

Run after landing-c gate 9 recorded its end (runner.log: "78a-landing-c-gate9 rc=1 end 2026-11-10T04:57:30Z").
Host dmitry-pc, Python 3.12.3, systemd 255, 20 CPUs. Each command ran on its own in
`systemd-run --user --scope -p MemoryMax=10G`, one after another. Another queued job (79a-v3910-calibrate) used
the host from 04:57Z, so the load was between 10 and 36. These are partial local runs, not gate evidence.
selftest exits 2 on a partial run that passes and 1 on one with a failed row.

`python3 scripts/selftest.py --suite NAME` on commit 570d2c73 (tree f855e824), suite rows, then the selftest
total with the prerequisite closure:

- 130_veldo_0262_step_runner: 14 passed; 40 passed, 0 failed (8.8 s)
- 130_veldo_0275_approved_engine: 3 passed; 29 passed, 0 failed (0.1 s)
- 131_veldo_0275_stream_probe: 4 passed; 30 passed, 0 failed (0.2 s)
- 86_veldo_0186_setup_assets: 11 passed; 37 passed, 0 failed (18.0 s)
- 86_veldo_0189_engine_upgrade (merged on both sides): 36 passed; 62 passed, 0 failed (155.1 s)
- 66_veldo_0042_clones (landing-c round 9b): 20 passed; 46 passed, 0 failed (1.8 s)
- 62_veldo_0039_dispatch (reads the merged control_launch.py): 25 passed; 51 passed, 0 failed (9.7 s)
- 83_veldo_0154_factory_loop (calls honor_stops): 14 passed; 40 passed, 0 failed (37.0 s)
- 86_veldo_0127_agent_configuration (the conflicted records): 27 passed, 2 failed; 53 passed, 2 failed (42.5 s).
  live/claude and live/codex fail with "missing or stale live capture".
- 126_veldo_0230_qualify_reproduces (the conflicted records): 4 passed, 1 failed; 30 passed, 1 failed (196.9 s).
  qualify/reproduces fails: the four resources-*.json records differ from what qualify writes.

Both failures come from the merge: the six records carry landing-d's control_launch.py digest, and the merged
module has a new one.

Fixed here (commit 2ef85b80, tree 47eea581): `python3 -B .veldo/qualify.py --codex <the Codex binary
.veldo/runtime/engines.json names> --claude <the Claude Code 2.1.317 binary it names>`, exit 0. It changed the four
resource records by one line each, the control_launch.py digest. It also rewrote the four runtime summaries with
new check durations only; those were restored and not committed. On 2ef85b80:

- 126_veldo_0230_qualify_reproduces: 5 passed; 31 passed, 0 failed (977.7 s, load 31 to 36).
- 82_veldo_0129_worker_wiring (run to read the teeth failure below): 31 passed; 57 passed, 0 failed (79.4 s,
  load 10).

Not fixed: claude-live.json and codex-live.json. Retaking them needs proof/VELDO-0127/live.py with a Claude and a
Codex subscription login, which this run does not have. Suite 86_veldo_0127 stays at 27 passed, 2 failed until
the lead retakes both. It was not run again.

Teeth, `python3 scripts/check_teeth_mutations.py --finding N --summary FILE`, on 2ef85b80. The two summary files
were written over; the earlier section's teeth numbers are no longer in them.

- 262: registered 12, executed 12, rejected 12, status passed, exit 0, 353.2 s (load 11.06 at the end).
  Summary: landing-d2-teeth-262.summary.json.
- 275: registered 8, executed 8, rejected 7, status failed (invalid_baseline), exit 1, 1101.6 s (load 34.64 at
  the end). Summary: landing-d2-teeth-275.summary.json. Seven cases were killed as expected. The eighth,
  probe275-claude-hold-role-bound, never got to its mutant: its controls ran suite 82_veldo_0129_worker_wiring on
  unchanged code and failed, the baseline in outcome/malformed-review, outcome/missing-usage and
  build/gitdir-missing, the noop in other rows (review/independence-policy, outcome/nonzero and more). None of
  those rows is the tooth's own probe/every-launch. The same suite alone passed 31 of 31 afterwards at load 10.
  Unchanged code failing in different rows on each control, at load 35, looks like the host and not the merge,
  but that is a reading and not proven. The teeth were not run again.

The raw logs were discarded (name, bytes, sha256):

- suite-130_veldo_0262_step_runner.log 9595 deb72d951150bf00116c27bcbe8e89967d04b9b9cfbb5e054e767233dbf94376
- suite-130_veldo_0275_approved_engine.log 9599 3e61a52e6ab42258396de825b0a3d5dbbfd97e4ee94d27213584c98692936d52
- suite-131_veldo_0275_stream_probe.log 9797 1aefdb33f4312009b192dfff8ab42b916959880456f1e3c899bc2e67b0904b92
- suite-86_veldo_0186_setup_assets.log 9776 75177896501a8c931c94f540bc94cafe7bdee4b19b9d80cee550e38428343af2
- suite-86_veldo_0189_engine_upgrade.log 9601 90b1757b9cfd6e9b4a5c9e319a040e85f3633ab78d8c14e00a28aabcc45049ec
- suite-66_veldo_0042_clones.log 9557 7e63c7e74a5bf4cdd9d88aa56a7c36f3b8d1a935d872ae90ea4088f57881b214
- suite-62_veldo_0039_dispatch.log 9559 d6d1f5846385b93255ce0f64ef9e2785867a47b0d4e9081b43255e98dd799b08
- suite-83_veldo_0154_factory_loop.log 10906 005ae7dbe1aa3449cf46cb1247308d887c36cdf5eb85b9fac12e4f0c0cb043ec
- suite-86_veldo_0127_agent_configuration.log 10454 59c78090307dea7b58d1b0001ea604311fbdfb5ced74eadcca3f032008f4d200
- suite-126_veldo_0230_qualify_reproduces.log 9887 bc24d0a79e6bf72edae5b99c85fff7a3103d853b15b725b99995b4e7baed9e70
- suite-126_veldo_0230_qualify_reproduces.after-fix.log 9572 d6297029fd1e1a95da79b306aed30d87e7bd8b7dc7411a0141f5fc35c4135568
- suite-82_veldo_0129_worker_wiring.log 10250 100072f1e947fbb72e4ac446095b5332506e9b59aac6f4f0c7ad006cddd7945f
- qualify-out.log 32897 0e3213b8352f6f5be1ac77ad5381319bf287506bf11982356d2fc5151bf6772e
- teeth-262.log 149516 3eb81e920f6f566d243eeae5a0e7aed85ec3b76d76db77678282d0485b6814fe
- teeth-275.log 74156 2d614133bff828853631e158e0e77ca2542230dbfdb210c17a771c4b4b572955
