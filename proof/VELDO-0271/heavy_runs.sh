#!/usr/bin/env bash
# VELDO-0271: the heavy runs behind this bundle, in one pass. Run from the worktree root, already
# inside the shared host lock and a memory-limited scope:
#   bash <host lock wrapper> bash proof/VELDO-0271/heavy_runs.sh <scratch dir> <baseline checkout> unit
#   bash <host lock wrapper> bash proof/VELDO-0271/heavy_runs.sh <scratch dir> <baseline checkout> rest
# "unit" is step 1. The table (removed.json, rows.json) is built from its record, and "rest" (steps 2 to 4)
# runs after the table is in place, because one registered mutation and one row read the table.
# <scratch dir> receives every log and raw record (nothing raw goes into the repository).
# <baseline checkout> is a clean checkout of 24c9f5b4, whose row record (rows-before.json) is already
# in <scratch dir>, made by: python3 proof/VELDO-0271/record_rows.py record <baseline checkout> ...
# Each step appends one line to <scratch dir>/results.txt.
set -u
OUT="$1"; BASE="$2"; PART="$3"
ROOT=$(pwd -P)
RESULTS="$OUT/results-$PART.txt"
: > "$RESULTS"
own_cgroup() { echo "/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)"; }
usage_usec() { awk '$1 == "usage_usec" {print $2}' "$(own_cgroup)/cpu.stat"; }

if [ "$PART" = unit ]; then
# 1. The whole unit suite of this tree, once, with every row name recorded. Wall seconds, CPU seconds
#    and the scope's peak memory are the measured run behind the unit node's estimate.
cpu0=$(usage_usec); t0=$(date +%s.%N)
python3 proof/VELDO-0271/record_rows.py record "$ROOT" "$OUT/rows-after.json" > "$OUT/unit.log" 2>&1
code=$?
t1=$(date +%s.%N); cpu1=$(usage_usec)
peak=$(cat "$(own_cgroup)/memory.peak" 2>/dev/null || echo unknown)
failing=$(grep -E '^ *SELFTEST FAIL: ' "$OUT/unit.log" | sed -E 's/^ *SELFTEST FAIL: //' | cut -c1-120 | paste -sd ';' -)
echo "unit exit $code wall $(echo "$t1 - $t0" | bc) cpu $(echo "($cpu1 - $cpu0) / 1000000" | bc -l | cut -c1-10) peak_bytes $peak load $(cut -d' ' -f1-3 /proc/loadavg) :: $(grep -E '^selftest: ' "$OUT/unit.log" | tail -1) :: failing: ${failing:-none}" >> "$RESULTS"
cat "$RESULTS"
exit 0
fi

# 2. The registered mutations of this spec, and the cases whose anchors this change moved.
python3 scripts/check_teeth_mutations.py --finding 271 --summary "$OUT/teeth-271.summary.json" > "$OUT/teeth-271.log" 2>&1
echo "teeth-271 exit $? $(grep -E '^mutations: ' "$OUT/teeth-271.log" | tail -1)" >> "$RESULTS"
python3 scripts/check_teeth_mutations.py --case deadline215-no-prune --case deadline215-key-omits-sources \
  --case deadline215-key-omits-definition --case deadline215-candidate-authority-not-recorded \
  --case scope272-gate-legs-added-back --summary "$OUT/teeth-moved.summary.json" > "$OUT/teeth-moved.log" 2>&1
echo "teeth-moved exit $? $(grep -E '^mutations: ' "$OUT/teeth-moved.log" | tail -1)" >> "$RESULTS"

# 3. AC3's falsifier: the suite 62 cases of VELDO-0261 through the driver's own entry.
python3 scripts/check_teeth_mutations.py --case dispatch261-stop-message-ignored \
  --case dispatch261-stop-leaves-record-running --summary "$OUT/teeth-261.summary.json" > "$OUT/teeth-261.log" 2>&1
echo "teeth-261 exit $? $(grep -E '^mutations: ' "$OUT/teeth-261.log" | tail -1)" >> "$RESULTS"

# 4. Red on the code before this change: suite 141 and its registration laid over a copy of 24c9f5b4.
RED="$OUT/red"
rm -rf "$RED"
cp -a "$BASE" "$RED"
cp scripts/suites/141_veldo_0271_gate_without_sandbox.py "$RED/scripts/suites/"
mkdir -p "$RED/proof/VELDO-0271"
cp proof/VELDO-0271/removed.json proof/VELDO-0271/rows.json "$RED/proof/VELDO-0271/" 2>/dev/null
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
cat "$RESULTS"
