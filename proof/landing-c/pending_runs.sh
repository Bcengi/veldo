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
