#!/bin/bash
# landing-b gate fix round 4: suite 126 and its one mutation case (qualify230-claude-record-unwritten).
# Run from the landing-b worktree root, under the host gate lock held by the caller (no flock here).
# Step 2 is the authority mutation CLI narrowed to the case: on a pass it records the case's measured
# seconds (VELDO-0215), so the next gate's worker deadline is min(1800, max(120, 3 x max sample)).
cd /home/dmitry/projects/veldo-worktrees/landing-b || exit 1

s=$(date +%s)
python3 scripts/selftest.py --suite 126_veldo_0230_qualify_reproduces > /tmp/lb4-suite126.log 2>&1
rc=$?
echo "step1 suite126 rc=$rc wall=$(( $(date +%s) - s ))s load=$(cut -d' ' -f1 /proc/loadavg) last: $(tail -1 /tmp/lb4-suite126.log | cut -c1-160); log /tmp/lb4-suite126.log"

s=$(date +%s); export LB4_STEP2_START=$s
python3 scripts/check_gate_mutations.py --case qualify230-claude-record-unwritten \
    --receipt /tmp/lb4-mut126.json > /tmp/lb4-mut126.log 2>&1
rc=$?
echo "step2 mutation case qualify230-claude-record-unwritten rc=$rc wall=$(( $(date +%s) - s ))s load=$(cut -d' ' -f1 /proc/loadavg) $(grep -m1 '^mutations:' /tmp/lb4-mut126.log) $(python3 -c "
import json
r = json.load(open('/tmp/lb4-mut126.json'))
print('budget=%s' % r.get('budget_seconds'), ' '.join('%s=%.1fs%s' % (o['name'].rsplit(':', 1)[-1] if ':' in o['name'] else 'mutant',
      o.get('elapsed', 0), '(' + o['error'] + ')' if 'error' in o else '') for o in r.get('worker_outcomes', [])))
" 2>&1); log /tmp/lb4-mut126.log"

python3 - <<'EOF'
import json, os, pathlib
since = int(os.environ['LB4_STEP2_START'])
store = pathlib.Path.home() / '.cache/veldo/mutation-case-seconds'
root = '/home/dmitry/projects/veldo-worktrees/landing-b'
hits = []
for path in store.glob('*.json'):
    try:
        item = json.loads(path.read_text())
    except (OSError, ValueError):
        continue
    if item.get('authority') == root and path.stat().st_mtime >= since:
        hits.append(item['seconds'])
if hits:
    print('step3 recorded sample %.1fs -> next gate worker deadline %.0fs' % (max(hits), min(1800, max(120, 3 * max(hits)))))
else:
    print('step3 no sample recorded for landing-b (step 2 did not pass); the gate keeps the 120s floor')
EOF
