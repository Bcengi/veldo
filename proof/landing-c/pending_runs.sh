#!/bin/bash
# landing-c: the suites whose files conflicted in the merges made so far (the gate lock was not free
# when each merge commit was checked). Merge 1 (VELDO-0267): scripts/check_gate_mutations.py and its
# engine copy conflicted, so suite 140 (the canary names) and suite 112 (VELDO-0285's planned
# deadlines, the landing-b side of the same lines). Merge 2 (VELDO-0268): scripts/check_teeth_mutations.py
# conflicted, so suite 141 (suite 140 above covers the VELDO-0267 half).
# Merge 3 (VELDO-0270): scripts/parser_corpus_audit.py and .veldo/policy.yaml conflicted, so suite
# 127_veldo_0259 (the home_as_tilde writer count) and suite 129_veldo_0270 (the proof size limit).
# Merge 4 (VELDO-0272): .veldo/policy_check.py (valid_approval_for), .veldo/policy.yaml (the protected
# list union), check_teeth_mutations.py and suite 101 conflicted, so suites 129_veldo_0272, 140 (its
# self-approval falsifier anchors on valid_approval_for), 141 (protected_refs stays in force), 01 and
# 10 (valid_approval_for rows), 101, and the teeth cases of findings 267 and 272.
# Merge 5 (VELDO-0274): check_teeth_mutations.py, the manifest and requires.json conflicted; 0274 changed
# suites 86, 88, 89 and 90 and scripts/gate_unconfined.json, so suites 129_veldo_0274, 86, 88, 89, 90, 101
# (expected red: the unconfined list now holds 49, see the README), the teeth cases of finding 274
# (confined: the slice rows stand down there) and check_gate_mutations.py --finding 274 (the unconfined leg
# VELDO-0274's own proof names as the only entry that runs its cases with a user manager).
# Merge 6 (VELDO-0278): .veldo/policy.yaml, suites 101, 113_veldo_0220 and 114_veldo_0220, the manifest,
# requires.json and specs/index.md conflicted; 0278 changed suites 08 and 114_veldo_0216, selftest.py and the
# teeth cases, and suite 129_veldo_0272's expected list gained the parked entry, so suites 129_veldo_0278, 08,
# 113_veldo_0220, 114_veldo_0220, 114_veldo_0216 (101 and 129_veldo_0272 are above) and the teeth cases of
# finding 278.
# Run from the landing-c worktree root, under the host gate lock held by the caller (no flock here).
# One summary line per step goes to proof/landing-c/pending-summary.txt; logs go under /tmp.
cd "$(dirname "$0")/../.." || exit 1
summary=proof/landing-c/pending-summary.txt
: > "$summary"

n=0
step() {
    local name=$1
    shift
    n=$((n + 1))
    local s
    s=$(date +%s)
    "$@" > "/tmp/lc-$name.log" 2>&1
    local rc=$?
    echo "step$n $name rc=$rc wall=$(( $(date +%s) - s ))s fails=$(grep -c 'SELFTEST FAIL' "/tmp/lc-$name.log") last: $(tail -1 "/tmp/lc-$name.log" | cut -c1-160); log /tmp/lc-$name.log" | tee -a "$summary"
}

for suite in 140_veldo_0267_mutation_selection 112_veldo_0215_case_deadlines 141_veldo_0268_protected_refs \
        127_veldo_0259_installation 129_veldo_0270_small_proof \
        129_veldo_0272_approval_scope 01_warp_0101_reviewer_notes 10_warp_0613_anti_vacuity \
        101_veldo_0208_landing_reuse \
        129_veldo_0274_factory_slices 86_veldo_0127_agent_configuration 88_veldo_0127_feature_defaults \
        89_veldo_0127_feature_listing 90_veldo_0127_feature_profile; do
    step "$suite" python3 scripts/selftest.py --suite "$suite"
done
# Every registered mutation of findings 267, 272 and 274 must be rejected ("mutations: " line in the log).
step teeth-267 python3 scripts/check_teeth_mutations.py --finding 267
step teeth-272 python3 scripts/check_teeth_mutations.py --finding 272
step teeth-274 python3 scripts/check_teeth_mutations.py --finding 274
step gate-mutations-274 python3 scripts/check_gate_mutations.py --finding 274

# Merge 6 (VELDO-0278).
for suite in 129_veldo_0278_parked_estimation 08_restoration_spec_generation_veldo 113_veldo_0220_gate_host \
        114_veldo_0220_gate_scope 114_veldo_0216_concurrent_stages; do
    step "$suite" python3 scripts/selftest.py --suite "$suite"
done
step teeth-278 python3 scripts/check_teeth_mutations.py --finding 278

# Fix round 1 (merge review findings 1 to 3, commit 00d2731e): the approval rule row and its falsifier,
# the push to refs/heads/release row, and the moved land-does-not-bind-refs anchor.
step round1-129_veldo_0272_approval_scope python3 scripts/selftest.py --suite 129_veldo_0272_approval_scope
step round1-129_veldo_0270_small_proof python3 scripts/selftest.py --suite 129_veldo_0270_small_proof
step round1-teeth-267 python3 scripts/check_teeth_mutations.py --finding 267
step round1-teeth-272 python3 scripts/check_teeth_mutations.py --finding 272

# Fix round 2: _nightly_reader loads through the declared external loader, so closure() resolves
# policy_check.py again (suite 58 is the mutation stage's baseline, suite 71 an unconfined-leg traceback).
step round2-58_veldo_0028_effects python3 scripts/selftest.py --suite 58_veldo_0028_effects
step round2-71_veldo_0138_channel_service python3 scripts/selftest.py --suite 71_veldo_0138_channel_service

# Fix round 3 (gate 54aa at 9ea10fdf, README "Fix round 3"). Every suite with a failing row, the two
# whose crash or baseline failure hid others (99, 113), and the owners of the changed modules (129_0272
# for policy_check.py, 140 for mutation_selection.py and check_gate_mutations.py). 05 and 14 are
# EXPECTED RED until the owner decides the intake draft question (README, cause E).
for suite in 05_tracker_routing_resolver_veldo 07_warp_1103_completion_mandatory 13_warp_0623_codified_live \
        14_warp_0717_subset_runner 18_veldo_0012_behaviour_floor_contract 27_veldo_0010_evidence_provenance \
        50_git_environment 53_veldo_0123_mutations 59_veldo_0043_graph 62_veldo_0045_runtime \
        64_veldo_0050_proof 91_veldo_0167_setup_records 99_veldo_0205_reuse 100_veldo_0207_case_reuse \
        113_veldo_0220_gate_host 129_veldo_0272_approval_scope 140_veldo_0267_mutation_selection; do
    step "round3-$suite" python3 scripts/selftest.py --suite "$suite"
done
step round3-teeth-267 python3 scripts/check_teeth_mutations.py --finding 267
step round3-teeth-272 python3 scripts/check_teeth_mutations.py --finding 272
# The confined unit leg stopped at suite 99's crash, so no suite after it ran there at 9ea10fdf:
# only a full gate shows them.
step round3-full-gate bash scripts/verify.sh

# Fix round 4 (README "Fix round 4"): the intake writer drafts human_approval required (cause E,
# lead decision), so suites 05 and 14 are expected green, no longer expected red.
for suite in 05_tracker_routing_resolver_veldo 14_warp_0717_subset_runner; do
    step "round4-$suite" python3 scripts/selftest.py --suite "$suite"
done

# Fix round 5 (README "Fix round 5"): the suites changed here ran green under the lock; the teeth of
# the findings whose suites changed and were not run here, then the full gate.
step round5-teeth-216 python3 scripts/check_teeth_mutations.py --finding 216
step round5-teeth-278 python3 scripts/check_teeth_mutations.py --finding 278
step round5-full-gate bash scripts/verify.sh

# Fix round 6 (README "Fix round 6"): the two suites whose controls failed unmutated at ee5d2a85, each
# ten times alone and ten times with every core busy (one busy loop per core), every run expected green;
# then the teeth of findings 47 and 154 (their 5 cases went unjudged) and the full gate.
for i in 1 2 3 4 5 6 7 8 9 10; do
    step "round6-66-alone-$i" python3 scripts/selftest.py --suite 66_veldo_0047_authority
    step "round6-83-alone-$i" python3 scripts/selftest.py --suite 83_veldo_0154_factory_loop
done
hogs=()
for _ in $(seq "$(nproc)"); do
    python3 -c 'while True: pass' &
    hogs+=($!)
done
for i in 1 2 3 4 5 6 7 8 9 10; do
    step "round6-66-loaded-$i" python3 scripts/selftest.py --suite 66_veldo_0047_authority
    step "round6-83-loaded-$i" python3 scripts/selftest.py --suite 83_veldo_0154_factory_loop
done
kill "${hogs[@]}"
step round6-teeth-47 python3 scripts/check_teeth_mutations.py --finding 47
step round6-teeth-154 python3 scripts/check_teeth_mutations.py --finding 154
step round6-full-gate bash scripts/verify.sh

# Fix round 7 (README "Fix round 7"): suite 78 (the fake's children file, gate 5's red baseline) and suite
# 83 (the stop result read after its pass), each ten times alone and ten times with every core busy, every
# run expected green; then the teeth of findings 60 (suite 78's cases, the red baseline's own, 16 workers so
# the controls share the user manager as in the gate), 47 and 154 (now in the unconfined leg standalone too,
# every case expected rejected), and the full gate.
for i in 1 2 3 4 5 6 7 8 9 10; do
    step "round7-78-alone-$i" python3 scripts/selftest.py --suite 78_veldo_0060_claude_adapter
    step "round7-83-alone-$i" python3 scripts/selftest.py --suite 83_veldo_0154_factory_loop
done
hogs=()
for _ in $(seq "$(nproc)"); do
    python3 -c 'while True: pass' &
    hogs+=($!)
done
for i in 1 2 3 4 5 6 7 8 9 10; do
    step "round7-78-loaded-$i" python3 scripts/selftest.py --suite 78_veldo_0060_claude_adapter
    step "round7-83-loaded-$i" python3 scripts/selftest.py --suite 83_veldo_0154_factory_loop
done
kill "${hogs[@]}"
step round7-teeth-60 python3 scripts/check_teeth_mutations.py --finding 60 --jobs 16
step round7-teeth-47 python3 scripts/check_teeth_mutations.py --finding 47
step round7-teeth-154 python3 scripts/check_teeth_mutations.py --finding 154
step round7-full-gate bash scripts/verify.sh
