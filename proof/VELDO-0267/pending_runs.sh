#!/usr/bin/env bash
# VELDO-0267 fix round 1: the runs that need the host gate lock, which was not free within the
# 20 minute budget. The lead runs this file already inside the lock: it takes no lock itself.
# Each step appends one line to proof/VELDO-0267/pending-summary.txt; full logs stay under /tmp.
set -u
cd "$(dirname "$0")/../.." || exit 1
SUMMARY=proof/VELDO-0267/pending-summary.txt
LOGS=$(mktemp -d /tmp/veldo-0267-pending.XXXXXX) || exit 1

step() {
  name=$1
  shift
  started=$(date +%s)
  "$@" > "$LOGS/$name.log" 2>&1
  status=$?
  last=$(grep -v '^[[:space:]]*$' "$LOGS/$name.log" | tail -n 1 | cut -c1-220)
  failed=$(grep -c 'FAIL' "$LOGS/$name.log")
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $name head=$(git rev-parse --short HEAD) exit=$status seconds=$(( $(date +%s) - started )) fail_lines=$failed last=[$last] log=$LOGS/$name.log" >> "$SUMMARY"
}

# Suite 140 already ran green inside the lock at 3d886d3f (48 passed, 0 failed); see README.
# The 13 registered falsifiers of this ticket through the mutation stage: baseline green, no-op equal,
# mutant red on the targeted row, each anchor applied once.
step teeth267 python3 scripts/check_teeth_mutations.py --finding 267
