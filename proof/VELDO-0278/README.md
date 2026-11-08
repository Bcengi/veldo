# VELDO-0278 build, third start: AC1, AC2 and AC3 built

Branch agent/claude/veldo-0278. The second start stopped on two points; the lead answered both in
8ce24d17 (spec History, 2026-11-07): AC1's gate row runs only a one-fragment fixture parked set and
the real eight run once as proof evidence, and suite 114_veldo_0216 joined the footprint so the
VELDO-0214 handoff could be removed. Both are built in this start (commit 046872cd).

## AC1: the estimation suites leave the gate (built)

- The eight fragments moved with git mv to scripts/parked/estimation/, with their manifest entries
  (closures included, each itself alone) in scripts/parked/estimation/manifest.json. Suite 111 moved
  with them (AC3). scripts/suites/manifest.json lost the nine entries; requires.json regenerated with
  `python3 scripts/run_scope.py --emit-requires` (no remaining closure names any of them).
- scripts/selftest.py gained `--parked SET`: runs the set's fragments in order in shared.py's
  namespace under a RunScope with a selector, so the aggregate line and the verify stamp refuse and
  the exit is 2 (pass) or 1 (fail), never 0. It refuses other selectors, an unknown set, and any run
  inside a gate leg. It prints its own lines, ending "selftest parked estimation: N passed, M failed
  in Xs (not a gate result)", and "verify stamp: refused (PARTIAL_RUN_CANNOT_VERIFY)".
- In the parked copies: 1409's "only fragment naming cost_to_change" row now globs scripts/suites and
  scripts/parked/estimation; 111 loads check_first_use.py from its parked path.
- Rows (suite 129): parked/unit-list-excludes-estimation and parked/no-gate-pass. The gate row runs
  `--parked estimation` only over a one-fragment fixture tree (a copy of selftest.py and run_scope.py
  with a fixture parked manifest): exit 2, "verify stamp: refused (PARTIAL_RUN_CANNOT_VERIFY)", no
  aggregate line, the parked summary line. The real-eight row (parked/command-runs-the-eight-green)
  is gone from the suite, so suite 129 runs in seconds: third start, without the lock,
  `python3 scripts/selftest.py --suite 129_veldo_0278_parked_estimation`: 6 passed, 0 failed in 0.39s.
- Proof evidence, run once by the lead inside the gate lock at 4c38dd1a (lock job 31, 2026-11-07): `python3 scripts/selftest.py --parked
  estimation`, each of the eight 0 failed. Expected exit 1, not 2: parked suite 111 tests only the
  VELDO-0214 handoff, which AC3 removed, so it now reports one red row
  ("VELDO-0214 first-use-budget/handoff-present ... removed by VELDO-0278") instead of raising and
  cutting off the summary. The eight are judged on their own per-suite lines.
- Falsifier: case parked278-stamp-allowed (selftest.py, the parked scope built with selector None).
  The fixture tree copies the scripts/selftest.py under test, so the mutant reddens
  parked/no-gate-pass through the fixture alone. Driven by hand in the second start on a fixture
  tree: baseline exit 2 and "verify stamp: refused"; mutant exit 0 and "verify stamp: ALLOWED".
  Registered drive: check_teeth_mutations.py --finding 278 passed 3/3 (lead, lock job 17 at 13b405ab).
- Earlier evidence (second start): an overlapped by-hand parked run finished at 513 passed, 2 failed
  in 595 s, both reds caused by edits landing mid-run; 15_warp_1404 alone took 539 s. Not evidence
  of green; the clean run above is.

## AC2: no mutation case on an estimation module or a parked suite (built)

Removed from scripts/check_teeth_mutations.py (9 cases; 2810 became 2801 before the 3 new ones):
judgment-spend-recorded-unkinded, judgment-historical-spend-unkinded (module judgment_load.py);
budget214-fixed-1800-restored, budget214-caller-value-kept, budget214-failed-leg-recorded,
budget214-stale-docstring, budget214-main-drops-the-budget, budget214-temporary-authority-refused,
budget214-keep-not-spared (suite 111, parked). No case named any of the other eight modules or the
eight suites. The spend.py and vocabulary cases of finding 51 stay. scripts/mutation_case_inputs.json
had no case on those modules or suites; its formats172-census-drops-conform declaration listed the
eight moved suite files as inputs, which would no longer exist, so they were dropped (185 to 177 files).
- Row: mutation/no-estimation-case. Pre-check: green.
- Falsifier: case parked278-judgment-case-restored (restores judgment-spend-recorded-unkinded);
  materialized by hand, its cases() lists the restored case on judgment_load.py, which the row names.
  Registered drive: check_teeth_mutations.py --finding 278 passed 3/3 (lead, lock job 17 at 13b405ab).

## AC3: the integration stage leaves the gate (built)

- verify.sh: CHECK_integration="na:estimation layer parked until a spend source exists, VELDO-0278";
  the catalog now prints every na item as "== <name>: na (<reason>)"; the INTEGRATION comment
  rewritten. engine/scripts/verify.sh already declared integration na and is unchanged.
- gate_graph.json: integration.confined and integration.unconfined nodes removed.
- gate_unconfined.json: the integration stage entry removed.
- check_first_use.py moved to scripts/parked/estimation/ (ROOT now parents[3]).
- .veldo/policy.yaml: protection moved to scripts/parked/estimation/check_first_use.py, floor high.
- Suite 101: dispatcher_files drops check_first_use.py; the shadow fixture no longer copies or runs it;
  _v208_first_use_nested_copy loads it from the parked path. Suites 113 and 114 (0220): fixture stub
  for scripts/check_first_use.py removed.
- Rows: integration/graph-nodes-are-required-catalog-items, integration/stage-is-na-and-parked,
  integration/fixture-gate-green-with-na-line (this repository's verify.sh over a stub authority:
  exit 0, GATE: GREEN, the na line with the reason, no integration stage line, stamp green with
  checks_na equal to the na items). Pre-check: all three green.
- The VELDO-0214 handoff (third start): gate_legs.py and engine/scripts/gate_legs.py drop
  UNIT_SECONDS, MEASURED_STAGE/BUDGETED_STAGE, read_times, record_time, _record_time_locked,
  _times_file, measurement, owner_store_refusal, the integration "leg budget input" line, run_stage's
  times and prior parameters and the --prior-times flag; the docstring's measured-budget sections
  become one paragraph on the measurement store, which still holds the scheduler's resource
  measurements (record_resources, read_resources, prune_times, LEG_TIMES unchanged).
  gate_schedule.py and its engine copy drop write_prior, prior-unit-times.json, the integration
  wait on the unit leg (awaits_unit), command_for's prior_times and UNIT_SECONDS from the node
  environment filter. scripts/verify.sh and engine/scripts/verify.sh no longer name
  VELDO_GATE_UNIT_SECONDS (the env -u list and its comment). Copies identical; check_template_sync
  pass, check_lint pass. Every registered mutation case on gate_legs.py, gate_schedule.py or
  verify.sh still finds its text exactly once.
- Suite 114_veldo_0216: rows integration-waits-for-unit-without-measurement,
  integration-beside-measured-unit, measurement-record-race and timing-store-refusal removed, with
  the fixture's record_time seeding and run()'s store parameter. No registered case targets them.
- Parked suite 111: one guard row (above) when gate_legs.py carries no handoff.
- Falsifier: case parked278-integration-node-left (gate_graph.json regains integration.confined):
  read_graph refuses it as unknown and the graph row goes red. Registered drive: check_teeth_mutations.py --finding 278 passed 3/3 (lead, lock job 17 at 13b405ab).

## Pending (gate lock ~/.local/state/core-gates/.gate.lock held by another gate)

Every suite run, the parked all-eight run and `check_teeth_mutations.py --finding 278` are in
proof/VELDO-0278/pending_runs.sh: the suites edited here, every suite that loads gate_legs.py or
gate_schedule.py, and every suite that reads or copies verify.sh. Third start: the lock
was not free in 1200 s of waiting (flock -w 420, 440, 340 on it), so none of these ran here.

## Fix round 1 (check of 2026-11-07, NOT SOUND: F1 to F4)

- F1: suite 101's row 'VELDO-0208 unconfined-leg/declared-list' read CHECK_integration as
  required: and crashed (re.search returned None). It now reads unit and mutation as required:,
  requires CHECK_integration to be na:, and compares gate_unconfined.json's stages with those two;
  what it proves is unchanged (the list's stages are the required catalog items it covers).
- F2: verify.sh's INTEGRATION comment no longer names the spend recorder's file, so suite 01's row
  'WARP-0733 AC4: no gate stage consults the spend recorder' holds again (row unchanged).
- F3: suite 08's row 'WARP-1203 AC2: governing_spec resolves a behavior by declared footprint match'
  runs on a fixed fixture corpus of two specs (WARP-9011 footprint fixture/governed/*.py, WARP-9012
  footprint fixture/other/*.sh); fixture/governed/evidence.py must resolve governed, to WARP-9011,
  matched_by footprint, candidates exactly [WARP-9011]. Falsifier, in the suite's own TEETH form:
  row 'WARP-1203 AC2 TEETH' replaces the corpus module's fnmatch with one that never matches and
  requires the same check to be false. Both evaluated by hand outside a suite run (the row's code
  over the fixture): row true, TEETH true (the broken matcher makes the check false).
- F4: the parked run's per-suite lines were not kept by the lead's run. It is rerun as the last
  step of pending_runs.sh, which writes each of the eight suites' lines (suite, passed, failed,
  seconds) to pending-summary.txt. The lead's run of it (fix round 1 pending_runs.sh, logs
  /tmp/veldo-0278-fix1-pending): 504 passed, 2 failed in 595.95s, exit 1, verify stamp refused.
  Per suite (passed, failed, seconds): 15_warp_1402_estimate_record 58 0 0.08;
  15_warp_1404_historical_analogy 83 0 539.68; 15_warp_1405_reconciliation 60 0 17.27;
  15_warp_1406_normalization 45 0 12.62; 15_warp_1407_judgment_load 84 0 6.86;
  15_warp_1408_budget_rollup 45 0 0.28; 15_warp_1409_cost_to_change_per_area 54 1 17.39;
  16_warp_1403_sizing_pass 49 0 1.77; 111_veldo_0214_first_use_budget 0 1 0.00. The 1409 red is
  fixed in round 2 (below). Rerun at 4c38dd1a (lock job 31): 15_warp_1402 58/0, 1404 83/0, 1405 60/0, 1406 45/0, 1407 84/0, 1408 45/0, 1409 55/0, 16_warp_1403 49/0 (all eight green), 111 0/1 by design; suites 01 637/0, 08 1966/0, 14 53/0, 129 33/0, 101 214/2 (only the two inherited VELDO-0208 sandbox rows). Fix check of 2026-11-07: SOUND (research/claude-runs/veldo-0278-fixcheck-2026-11-07.md).
- Runs: the gate lock was not free in 1190 s of waiting (flock -w 540, 420, 230), so suites 01,
  08, 14 and 101 and the parked run did not run here. They are in pending_runs.sh (no lock inside;
  each step appends one line to pending-summary.txt, logs under /tmp/veldo-0278-fix1-pending);
  bash -n pending_runs.sh: clean.

## Fix round 2 (lead's run of the round 1 pending_runs.sh)

Lead's results: suites 01 637/0, 08 1966/0, 14 53/0 green (F1 to F3 confirmed); 101 213/3; the
parked run 504/2.
- Suite 101, VELDO-0208 sandbox/unavailable-refuses-before-exec and sandbox/old-abi-refuses-before-exec:
  inherited (red on main afa292f0, on the lead's known list). Recorded, not fixed.
- Suite 101, VELDO-0208 unconfined-leg/authority-copy-records-under-its-scratch-home: CAUSED by this
  diff. It required the authority copy's gate_legs.py to record a passing unit leg's time in the
  scratch HOME's leg-time store (VELDO-0214 AC6); AC3 removes that recording with the handoff, so the
  store stayed empty ([], []). Fixed by stating the new behavior, not by dropping the row: renamed
  'VELDO-0208 unconfined-leg/authority-copy-records-no-leg-time', it requires the scratch store to
  hold no file after both drivers and that both drivers ran a passing unit leg (kept: code 0, stamp
  green; list-read: exit 0, "unit: unconfined leg: pass"), so an empty store from a driver that ran
  nothing cannot pass it. The scratch HOME stays, so a suite run never reaches the owner's store.
- Parked WARP-1409 AC6 ("no gate stage consumes this module's output"): CAUSED by this diff. Its
  bound requires its own fragment to be the only suite fragment naming cost_to_change; suite 129
  (new here) typed the module and 15_warp_1409's full name into its lists. The row is unchanged.
  Suite 129 now reads the eight fragments from AC1's text (by the spec's own prefixes, resolved to
  names in the parked manifest) and the nine modules from AC2's text, and a new row
  parked/spec-names-eight-fragments-and-nine-modules requires exactly 8 distinct prefixes, 9
  distinct modules and one parked fragment per prefix, so a parse that finds nothing is red.
  parked/unit-list-excludes-estimation also refuses any unit-manifest name, requires.json key or
  scripts/suites file starting with one of the eight prefixes. By hand: the 1409 glob now finds only
  15_warp_1409_cost_to_change_per_area.py; gate closure texts name it nowhere.
- Parked VELDO-0214 first-use-budget/handoff-present: red by design, not fixed. AC1 requires the
  eight named estimation fragments green; suite 111 is not one of the eight. AC3 parks 111 because it
  tests only the VELDO-0214 handoff, which AC3 removes. Its one row says that behavior is absent;
  making it green would need either the handoff back (against AC3) or a row that passes over
  removed behavior (a loosened check). So the parked run exits 1 by design and AC1 is judged on the
  eight's per-suite lines.
- Runs: suite 129 ran once without the lock by mistake (3 s): 7 passed, 0 failed. The lock was not
  free in 910 s (flock -w 300, 330, 280), so suites 101 and 129 and the parked all-eight run are in
  pending_runs.sh (fix round 2; no lock inside; logs /tmp/veldo-0278-fix2-pending; one line per
  step in pending-summary.txt); bash -n clean.

## Inherited, not fixed

- specs/index.md is stale at HEAD before this build (lead commit b40b3123 set 0273, 0274, 0278,
  0279, 0280 ready without regenerating it), so scripts/check_generated.sh is red. Not touched here.
- Stage checks run without the lock: check_lint.sh pass, check_template_sync.sh pass,
  check_generated.sh red only on the index above.
