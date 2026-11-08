#!/bin/bash
# landing-c: the suites whose files conflicted in the merges made so far (the gate lock was not free
# when each merge commit was checked). Merge 1 (VELDO-0267): scripts/check_gate_mutations.py and its
# engine copy conflicted, so suite 140 (the canary names) and suite 112 (VELDO-0285's planned
# deadlines, the landing-b side of the same lines). Merge 2 (VELDO-0268): scripts/check_teeth_mutations.py
# conflicted, so suite 141 (suite 140 above covers the VELDO-0267 half).
# Run from the landing-c worktree root, under the host gate lock held by the caller (no flock here).
# One summary line per step goes to proof/landing-c/pending-summary.txt; logs go under /tmp.
cd "$(dirname "$0")/../.." || exit 1
summary=proof/landing-c/pending-summary.txt
: > "$summary"

n=0
for suite in 140_veldo_0267_mutation_selection 112_veldo_0215_case_deadlines 141_veldo_0268_protected_refs; do
    n=$((n + 1))
    s=$(date +%s)
    python3 scripts/selftest.py --suite "$suite" > "/tmp/lc-$suite.log" 2>&1
    rc=$?
    echo "step$n $suite rc=$rc wall=$(( $(date +%s) - s ))s fails=$(grep -c 'SELFTEST FAIL' "/tmp/lc-$suite.log") last: $(tail -1 "/tmp/lc-$suite.log" | cut -c1-160); log /tmp/lc-$suite.log" | tee -a "$summary"
done
