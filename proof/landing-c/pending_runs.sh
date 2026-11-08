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
        101_veldo_0208_landing_reuse; do
    step "$suite" python3 scripts/selftest.py --suite "$suite"
done
# Every registered mutation of findings 267 and 272 must be rejected ("mutations: " line in the log).
step teeth-267 python3 scripts/check_teeth_mutations.py --finding 267
step teeth-272 python3 scripts/check_teeth_mutations.py --finding 272
