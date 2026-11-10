#!/usr/bin/env bash
# VELDO-0271: the heavy runs behind this bundle, in one pass. Run from the worktree root on a clean
# tree, inside the shared host lock and a memory-limited scope of its own:
#   bash <host lock wrapper> bash proof/VELDO-0271/heavy_runs.sh <scratch dir> <baseline checkout>
# <scratch dir> receives every log and raw record; nothing raw goes into the repository.
# <baseline checkout> is a clean checkout of 24c9f5b4. Its row record is <scratch dir>/rows-before.json;
# when that file is absent, step 0 makes it (one whole unit suite of the baseline).
# Nothing in the repository is written until step 6, after the last run.
# Each step appends one line to <scratch dir>/results.txt, printed at the end.
set -u
OUT="$1"; BASE="$2"
ROOT=$(pwd -P)
mkdir -p "$OUT"
RESULTS="$OUT/results.txt"
: > "$RESULTS"
own_cgroup() { echo "/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)"; }
usage_usec() { awk '$1 == "usage_usec" {print $2}' "$(own_cgroup)/cpu.stat"; }
teeth_line() { grep -E '^mutations: ' "$1" | tail -1; }

# 0. The baseline's row record, only when it is not there yet. When it runs here it shares the scope
#    with step 1, so the scope's peak memory is no longer a measurement of this tree alone.
BASELINE_RAN=0
if [ ! -s "$OUT/rows-before.json" ]; then
  BASELINE_RAN=1
  python3 proof/VELDO-0271/record_rows.py record "$BASE" "$OUT/rows-before.json" > "$OUT/record-before.log" 2>&1
  echo "baseline-record exit $? $(grep -E '^recorded ' "$OUT/record-before.log" | tail -1)" >> "$RESULTS"
fi

# 1. The whole unit suite of this tree, once, with every row name recorded: AC1 to AC4's suite rows
#    (suite 141 and the rows of suites 73, 103, 114, 127 and 140 the spec names). Wall seconds, CPU
#    seconds and the scope's peak memory are the measured run behind the unit node's estimate in
#    scripts/gate_graph.json.
cpu0=$(usage_usec); t0=$(date +%s.%N)
python3 proof/VELDO-0271/record_rows.py record "$ROOT" "$OUT/rows-after.json" > "$OUT/unit.log" 2>&1
code=$?
t1=$(date +%s.%N); cpu1=$(usage_usec)
peak=$(cat "$(own_cgroup)/memory.peak" 2>/dev/null || echo unknown)
[ "$BASELINE_RAN" = 1 ] && peak=includes-baseline-run
wall=$(echo "$t1 - $t0" | bc); cpu=$(echo "($cpu1 - $cpu0) / 1000000" | bc -l | cut -c1-10)
failing=$(grep -E '^ *SELFTEST FAIL: ' "$OUT/unit.log" | sed -E 's/^ *SELFTEST FAIL: //' | cut -c1-120 | paste -sd ';' -)
echo "unit exit $code wall $wall cpu $cpu peak_bytes $peak load $(cut -d' ' -f1-3 /proc/loadavg) :: $(grep -E '^selftest: ' "$OUT/unit.log" | tail -1) :: failing: ${failing:-none}" >> "$RESULTS"
python3 - "$OUT" "$code" "$wall" "$cpu" "$peak" <<'EOF'
import importlib.util, json, sys
from pathlib import Path
out, code, wall, cpu, peak = sys.argv[1:6]
spec = importlib.util.spec_from_file_location('heavy_validate', '.veldo/validate.py')
validate = importlib.util.module_from_spec(spec); spec.loader.exec_module(validate)
log = (Path(out) / 'unit.log').read_bytes()
text = log.decode('utf-8', 'replace').splitlines()
record = json.loads((Path(out) / 'rows-after.json').read_text())
deciding = {'exit': int(code), 'bound': 'exit 0 and no failing row',
            'aggregate': next((l for l in reversed(text) if l.startswith('selftest: ')), None),
            'failing_rows': [l.split('SELFTEST FAIL: ', 1)[1][:200] for l in text if 'SELFTEST FAIL: ' in l],
            'suites': len(record['rows']), 'row_names': sum(len(v) for v in record['rows'].values()),
            'wall_seconds': float(wall), 'cpu_seconds': float(cpu),
            'peak_cgroup_memory_bytes': int(peak) if peak.isdigit() else None,
            'verdict': 'pass' if code == '0' else 'fail'}
if peak == 'includes-baseline-run':
    deciding['peak_cgroup_memory_note'] = ('not measured: step 0 ran the baseline unit suite in this pass and the same scope, '
                                           'so the scope peak includes the baseline run')
validate.write_proof_summary(Path(out) / 'unit.summary.json',
                             'python3 proof/VELDO-0271/record_rows.py record <worktree> <scratch dir>/rows-after.json',
                             deciding, discarded=[('unit.log', log)], timing=True)
EOF

# 2. The table's inventory from the whole run. The committed rows.json was assembled from one run
#    per changed suite; this one comes from the whole suite and replaces it in step 6.
python3 proof/VELDO-0271/record_rows.py merge "$OUT/rows-before.json" "$OUT/rows-after.json" \
  proof/VELDO-0271/removed.json "$OUT/rows.json" "$OUT/rows.summary.json" > "$OUT/merge.log" 2>&1
echo "table-inventory exit $? $(tail -1 "$OUT/merge.log") :: $(python3 - "$OUT/rows.json" <<'EOF'
import json, sys
new, old = json.load(open(sys.argv[1])), json.load(open('proof/VELDO-0271/rows.json'))
part = lambda d, k: (d[k]['rows'], d[k]['cases'])
same = part(new, 'at_24c9f5b4') == part(old, 'at_24c9f5b4') and part(new, 'after') == part(old, 'after')
print('row and case names equal to the committed rows.json' if same else 'ROW OR CASE NAMES DIFFER from the committed rows.json')
EOF
)" >> "$RESULTS"

# 3. The registered mutations of this spec, and the cases whose anchors this change moved.
python3 scripts/check_teeth_mutations.py --finding 271 --summary "$OUT/teeth-271.summary.json" > "$OUT/teeth-271.log" 2>&1
echo "teeth-271 exit $? $(teeth_line "$OUT/teeth-271.log")" >> "$RESULTS"
python3 scripts/check_teeth_mutations.py --case deadline215-no-prune --case deadline215-key-omits-sources \
  --case deadline215-key-omits-definition --case deadline215-candidate-authority-not-recorded \
  --case scope272-gate-legs-added-back --summary "$OUT/teeth-moved.summary.json" > "$OUT/teeth-moved.log" 2>&1
echo "teeth-moved exit $? $(teeth_line "$OUT/teeth-moved.log")" >> "$RESULTS"

# 4. AC3's falsifier: the suite 62 cases of VELDO-0261 through the driver's own entry, the entry
#    whose confined run gave invalid baselines.
python3 scripts/check_teeth_mutations.py --case dispatch261-stop-message-ignored \
  --case dispatch261-stop-leaves-record-running --summary "$OUT/teeth-261.summary.json" > "$OUT/teeth-261.log" 2>&1
echo "teeth-261 exit $? $(teeth_line "$OUT/teeth-261.log")" >> "$RESULTS"

# 5. Red on the code before this change: suite 141 and its registration laid over a copy of 24c9f5b4.
RED="$OUT/red"
rm -rf "$RED"
cp -a "$BASE" "$RED"
cp scripts/suites/141_veldo_0271_gate_without_sandbox.py "$RED/scripts/suites/"
mkdir -p "$RED/proof/VELDO-0271"
cp proof/VELDO-0271/removed.json proof/VELDO-0271/rows.json "$RED/proof/VELDO-0271/"
python3 - "$RED" <<'EOF'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
ours = json.loads(Path('scripts/suites/manifest.json').read_text())
entry = next(e for e in ours['suites'] if e['name'] == '141_veldo_0271_gate_without_sandbox')
path = root / 'scripts/suites/manifest.json'
manifest = json.loads(path.read_text())
manifest['suites'].append(entry)
path.write_text(json.dumps(manifest, indent=1) + '\n')
EOF
(cd "$RED" && python3 scripts/run_scope.py --emit-requires > /dev/null 2>&1
 python3 scripts/selftest.py --suite 141_veldo_0271_gate_without_sandbox > "$OUT/red.log" 2>&1
 echo "red-on-24c9f5b4 exit $? $(grep -cE '^ *SELFTEST FAIL: VELDO-0271 ' "$OUT/red.log") rows red: $(grep -E '^ *SELFTEST FAIL: VELDO-0271 ' "$OUT/red.log" | sed -E 's/^ *SELFTEST FAIL: VELDO-0271 ([^: ]+).*/\1/' | paste -sd ';' -) :: $(grep -E '141_veldo_0271_gate_without_sandbox +[0-9]+ passed' "$OUT/red.log" | tr -s ' ')" >> "$RESULTS")
python3 - "$OUT" <<'EOF'
import importlib.util, re, sys
from pathlib import Path
out = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('heavy_validate', '.veldo/validate.py')
validate = importlib.util.module_from_spec(spec); spec.loader.exec_module(validate)
log = (out / 'red.log').read_bytes()
red = sorted(set(re.findall(r'SELFTEST FAIL: VELDO-0271 ([^: \n]+)', log.decode('utf-8', 'replace'))))
required = ['removed/leftover-reported', 'removed/lease-only', 'removed/seven-names-gone']
missing = [name for name in required if name not in red]
validate.write_proof_summary(out / 'red.summary.json',
                             'python3 scripts/selftest.py --suite 141_veldo_0271_gate_without_sandbox, in a copy of 24c9f5b4 '
                             'with suite 141, its manifest entry and the table laid over it',
                             {'required_red': required, 'required_not_red': missing,
                              'other_rows_red': [name for name in red if name not in required],
                              'rows_red': red, 'rows_red_count': len(red),
                              'bound': 'removed/seven-names-gone, removed/lease-only and removed/leftover-reported '
                                       'all red on the old code',
                              'verdict': 'fail' if missing else 'pass'}, discarded=[('red.log', log)])
EOF

# 6. The summaries, and the inventory of the whole run, into the bundle. Raw logs stay in <scratch dir>.
for name in unit.summary.json rows.json rows.summary.json teeth-271.summary.json teeth-moved.summary.json \
            teeth-261.summary.json red.summary.json; do
  [ -s "$OUT/$name" ] && cp "$OUT/$name" "proof/VELDO-0271/$name"
done
cat "$RESULTS"
