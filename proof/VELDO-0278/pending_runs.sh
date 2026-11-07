#!/usr/bin/env bash
# VELDO-0278 pending runs: run from the worktree root under the shared gate lock
# (~/.local/state/core-gates/.gate.lock). The lock was held by another gate for the build's
# 20-minute allowance in the second and the third start. Each line is one run; record the exit
# code and the final summary line of each.
set -u

# AC1, AC2, AC3 rows (suite 129; seconds: a fixture parked set and a fixture gate, never the real
# eight). Already run without the lock in the third start: 6 passed, 0 failed in 0.39s.
python3 scripts/selftest.py --suite 129_veldo_0278_parked_estimation

# AC1 proof evidence, run ONCE (never at the gate; about 10 minutes, 15_warp_1404 alone ~540 s).
# Expected: exit 1, "verify stamp: refused", each of the eight suites 0 failed; the one red row
# is 111's "handoff-present" (the VELDO-0214 handoff it tests left with the integration stage).
python3 scripts/selftest.py --parked estimation

# Suites this ticket edited (AC3 fixtures and the handoff rows)
python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse
python3 scripts/selftest.py --suite 113_veldo_0220_gate_host
python3 scripts/selftest.py --suite 114_veldo_0220_gate_scope
python3 scripts/selftest.py --suite 114_veldo_0216_concurrent_stages

# Suites that read the changed gate_legs.py, gate_schedule.py, verify.sh (both), graph, list,
# catalog, dispatcher, manifest or case registry
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
python3 scripts/selftest.py --suite 01_warp_0101_reviewer_notes
python3 scripts/selftest.py --suite 03_plugin_extension_loading_runner
python3 scripts/selftest.py --suite 08_restoration_spec_generation_veldo
python3 scripts/selftest.py --suite 128_veldo_0235_land_locally
python3 scripts/selftest.py --suite 24_veldo_0007_install_and_run
python3 scripts/selftest.py --suite 63_veldo_0049_floor
python3 scripts/selftest.py --suite 64_veldo_0050_proof
python3 scripts/selftest.py --suite 67_veldo_0056_candidates
python3 scripts/selftest.py --suite 67_veldo_0135_offers
python3 scripts/selftest.py --suite 72_veldo_0128_reports
python3 scripts/selftest.py --suite 82_veldo_0129_worker_wiring
python3 scripts/selftest.py --suite 86_veldo_0148_re_land

# Falsifier drives: the three registered cases of finding 278, from a green baseline
# (expected: mutations: passed, registered=3 executed=3, each mutant reddens its target row;
# parked278-stamp-allowed now reddens parked/no-gate-pass through the fixture parked set alone)
python3 scripts/check_teeth_mutations.py --finding 278
