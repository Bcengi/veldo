#!/usr/bin/env bash
# VELDO-0278 pending runs: run from the worktree root under the shared gate lock.
# The lock was held by a core gate for the whole of the build's 20-minute allowance.
# Each line is one run; record exit code and the final summary line of each.
set -u

# AC1, AC2, AC3 rows (new suite; it also runs the parked set and a fixture gate)
python3 scripts/selftest.py --suite 129_veldo_0278_parked_estimation

# AC1 parked command on its own (expected: exit 2, "verify stamp: refused", 0 failed)
python3 scripts/selftest.py --parked estimation

# Suites this ticket edited (AC3 fixtures)
python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse
python3 scripts/selftest.py --suite 113_veldo_0220_gate_host
python3 scripts/selftest.py --suite 114_veldo_0220_gate_scope

# Suites that read the changed graph, list, catalog, dispatcher, manifest or case registry
python3 scripts/selftest.py --suite 114_veldo_0216_concurrent_stages
python3 scripts/selftest.py --suite 14_warp_0717_subset_runner
python3 scripts/selftest.py --suite 100_veldo_0207_case_reuse
python3 scripts/selftest.py --suite 104_veldo_0210_mutation_workers
python3 scripts/selftest.py --suite 112_veldo_0215_case_deadlines
python3 scripts/selftest.py --suite 115_veldo_0219_measured_admission
python3 scripts/selftest.py --suite 53_veldo_0123_mutations
python3 scripts/selftest.py --suite 66_veldo_0051_events
python3 scripts/selftest.py --suite 125_veldo_0230_engine_census
python3 scripts/selftest.py --suite 69_veldo_0058_gate_output
python3 scripts/selftest.py --suite 70_veldo_0057_landing
python3 scripts/selftest.py --suite 07_warp_1103_completion_mandatory
python3 scripts/selftest.py --suite 13_warp_0623_codified_live
python3 scripts/selftest.py --suite 23_veldo_0006_budget_state
python3 scripts/selftest.py --suite 29_veldo_0016_policy_boundaries
python3 scripts/selftest.py --suite 99_veldo_0205_reuse

# Falsifier drives: the three registered cases of finding 278, from a green baseline
# (expected: mutations: passed, registered=3 executed=3, each mutant reddens its target row)
python3 scripts/check_teeth_mutations.py --finding 278
