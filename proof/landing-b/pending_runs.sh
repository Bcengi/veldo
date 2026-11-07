#!/bin/bash
# landing-b gate fix round 6: suites 99 and 100 (controlled workers implement retarget), suite 115
# (stage row injects 240 s deadlines through case_deadlines), and the 8 admission219 mutation cases.
# Run from the landing-b worktree root, under the host gate lock held by the caller (no flock here).
cd "$(dirname "$0")/../.." || exit 1

n=0
for suite in 99_veldo_0205_reuse 100_veldo_0207_case_reuse 115_veldo_0219_measured_admission; do
    n=$((n + 1))
    s=$(date +%s)
    python3 scripts/selftest.py --suite "$suite" > "/tmp/lb6-$suite.log" 2>&1
    rc=$?
    echo "step$n $suite rc=$rc wall=$(( $(date +%s) - s ))s fails=$(grep -c 'SELFTEST FAIL' "/tmp/lb6-$suite.log") last: $(tail -1 "/tmp/lb6-$suite.log" | cut -c1-160); log /tmp/lb6-$suite.log"
done

cases=""
for c in channel-ignored fixed-sixteen graph-without-channel optimistic-m short-unit-unaccounted \
         slowest-rate unowned-lifecycle-register worker-before-handoff; do
    cases="$cases --case admission219-$c"
done
s=$(date +%s)
# shellcheck disable=SC2086
python3 scripts/check_gate_mutations.py $cases --receipt /tmp/lb6-mut.json > /tmp/lb6-mut.log 2>&1
rc=$?
echo "step4 mutation admission219 x8 rc=$rc wall=$(( $(date +%s) - s ))s $(grep -m1 '^mutations:' /tmp/lb6-mut.log) $(python3 -c "
import json
r = json.load(open('/tmp/lb6-mut.json'))
print('budget=%s error=%s' % (r.get('budget_seconds'), r.get('error')))
" 2>&1 | cut -c1-300); log /tmp/lb6-mut.log"
