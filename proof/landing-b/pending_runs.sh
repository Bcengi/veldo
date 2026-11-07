#!/bin/bash
# landing-b gate fix round 5: mutation case qualify230-claude-record-unwritten now targets suite 125's row
# qualify/claude-record-written (qualify.py's main on recorded readings, no binary runs; target baseline under 40 s).
# Run from the landing-b worktree root, under the host gate lock held by the caller (no flock here).
cd "$(dirname "$0")/../.." || exit 1

s=$(date +%s)
python3 scripts/selftest.py --suite 125_veldo_0230_engine_census > /tmp/lb5-suite125.log 2>&1
rc=$?
echo "step1 suite125 rc=$rc wall=$(( $(date +%s) - s ))s load=$(cut -d' ' -f1 /proc/loadavg) last: $(tail -1 /tmp/lb5-suite125.log | cut -c1-160); log /tmp/lb5-suite125.log"

s=$(date +%s)
python3 scripts/selftest.py --suite 126_veldo_0230_qualify_reproduces > /tmp/lb5-suite126.log 2>&1
rc=$?
echo "step2 suite126 rc=$rc wall=$(( $(date +%s) - s ))s load=$(cut -d' ' -f1 /proc/loadavg) last: $(tail -1 /tmp/lb5-suite126.log | cut -c1-160); log /tmp/lb5-suite126.log"

s=$(date +%s)
python3 scripts/check_gate_mutations.py --case qualify230-claude-record-unwritten \
    --receipt /tmp/lb5-mut.json > /tmp/lb5-mut.log 2>&1
rc=$?
echo "step3 mutation case qualify230-claude-record-unwritten rc=$rc wall=$(( $(date +%s) - s ))s $(grep -m1 '^mutations:' /tmp/lb5-mut.log) $(python3 -c "
import json
r = json.load(open('/tmp/lb5-mut.json'))
print('budget=%s' % r.get('budget_seconds'), ' '.join('%s=%.1fs%s' % (o['name'].rsplit(':', 1)[-1] if ':' in o['name'] else 'mutant',
      o.get('elapsed', 0), '(' + o['error'] + ')' if 'error' in o else '') for o in r.get('worker_outcomes', [])))
" 2>&1); log /tmp/lb5-mut.log"
