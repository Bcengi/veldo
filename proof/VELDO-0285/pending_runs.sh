#!/bin/bash
# VELDO-0285 round 2: suite 112 (case deadlines, with the unmeasured rows) and the two registered
# falsifiers (finding 285). Run from anywhere; it finds the checkout from its own path. The caller
# holds the host gate lock (no flock here).
cd "$(dirname "$0")/../.." || exit 1

s=$(date +%s)
python3 scripts/selftest.py --suite 112_veldo_0215_case_deadlines > /tmp/v285-suite112.log 2>&1
rc=$?
echo "step1 suite112 rc=$rc wall=$(( $(date +%s) - s ))s load=$(cut -d' ' -f1 /proc/loadavg) $(grep -m1 '  112_veldo' /tmp/v285-suite112.log | tr -s ' ') last: $(tail -1 /tmp/v285-suite112.log | cut -c1-160); log /tmp/v285-suite112.log"

s=$(date +%s)
python3 scripts/check_gate_mutations.py --finding 285 --receipt /tmp/v285-mut.json > /tmp/v285-mut.log 2>&1
rc=$?
echo "step2 mutation finding 285 rc=$rc wall=$(( $(date +%s) - s ))s $(grep -m1 '^mutations:' /tmp/v285-mut.log) $(python3 -c "
import json
r = json.load(open('/tmp/v285-mut.json'))
print('budget=%s' % r.get('budget_seconds'), ' '.join('%s=%.1fs%s' % (o['name'].rsplit(':', 1)[-1],
      o.get('elapsed', 0), '(' + o['error'] + ')' if 'error' in o else '') for o in r.get('worker_outcomes', [])))
" 2>&1 | cut -c1-400); log /tmp/v285-mut.log"
