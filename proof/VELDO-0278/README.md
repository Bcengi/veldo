# VELDO-0278 build, second start: AC1 and AC2 built, AC3 built except the handoff removal (blocked)

Branch agent/claude/veldo-0278, built on be8a44ad without VELDO-0267 and VELDO-0271. The first start's
footprint report is superseded by this file (it is at 052a20a1).

## Blocker: AC3's handoff removal needs a suite outside the footprint

AC3 says gate_legs.py, gate_schedule.py and their engine copies drop the unit stage's measured-seconds
handoff (VELDO-0214). scripts/suites/114_veldo_0216_concurrent_stages.py tests that handoff and is NOT
in the footprint (the footprint names 114_veldo_0220_gate_scope.py, a different file). Its rows
integration-waits-for-unit-without-measurement and integration-beside-measured-unit assert the
"integration: <leg> leg budget input" lines and the wait on the unit leg; measurement-record-race and
timing-store-refusal call gate_legs.record_time and read_times (the handoff's store). Dropping the
handoff reddens them, so per the build instruction that part was stopped and NOT built:
gate_legs.py, gate_schedule.py and both engine copies are unchanged, and verify.sh still unsets
VELDO_GATE_UNIT_SECONDS. Needed: add scripts/suites/114_veldo_0216_concurrent_stages.py to the
footprint (its four rows above drop with the handoff). The rest of AC3 is built and does not depend on it.

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
- Rows (suite 129): parked/unit-list-excludes-estimation, parked/command-runs-the-eight-green,
  parked/no-gate-pass. Off-suite pre-check (shared namespace, parked run stubbed): the first green;
  the other two need the real parked run, PENDING.
- Falsifier: case parked278-stamp-allowed (selftest.py, the parked scope built with selector None).
  Driven by hand on a fixture tree: baseline exit 2 and "verify stamp: refused"; mutant exit 0 and
  "verify stamp: ALLOWED", which the no-gate-pass row rejects. Registered drive PENDING.
- Note: a full by-hand parked run started before the edits finished and overlapped them, so its one
  red row (1402 AC5, verify.sh still named the moved file at that instant) is not evidence; the
  condition re-evaluated on the committed tree is true. A clean parked run is PENDING.

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
  Registered drive PENDING.

## AC3: the integration stage leaves the gate (built except the handoff, see blocker)

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
- Falsifier: case parked278-integration-node-left (gate_graph.json regains integration.confined):
  read_graph refuses it as unknown and the graph row goes red. Registered drive PENDING.

## Pending (gate lock held by a core gate for the full 20 minutes)

Every suite run and the falsifier drive are in proof/VELDO-0278/pending_runs.sh. New suite
129_veldo_0278_parked_estimation is registered in scripts/suites/manifest.json and requires.json in
the committed tree.

## Inherited, not fixed

- specs/index.md is stale at HEAD before this build (lead commit b40b3123 set 0273, 0274, 0278,
  0279, 0280 ready without regenerating it), so scripts/check_generated.sh is red. Not touched here.
- Stage checks run without the lock: check_lint.sh pass, check_template_sync.sh pass,
  check_generated.sh red only on the index above.
