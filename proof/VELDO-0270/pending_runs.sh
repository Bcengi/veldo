#!/usr/bin/env bash
# VELDO-0270 pending runs, fix round 3 (suite 129 runs its modules from a temporary .veldo tree, d9f69562). The lead runs this from the worktree root, already inside
# the gate lock. Each step appends one line to proof/VELDO-0270/pending-summary.txt naming its
# failing rows; logs go under /tmp only.
set -u
cd "$(git rev-parse --show-toplevel)"
OUT=proof/VELDO-0270/pending-summary.txt
LOGS=$(mktemp -d /tmp/veldo-0270-pending-XXXXXX)
HEAD_ID=$(git rev-parse --short HEAD)

step () {
  # step NAME COMMAND...: run, record exit code, failing row names and the log path in one line.
  name=$1; shift
  log="$LOGS/$name.log"
  start=$(date +%s)
  "$@" > "$log" 2>&1
  rc=$?
  # Suite rows that failed, and for the teeth run the first failing case details from its JSON.
  failing=$( { grep -oE 'SELFTEST FAIL: .*' "$log" | sed 's/^SELFTEST FAIL: //'; grep -oE '"detail": "[^"]*"' "$log" | head -3; } | tr '\n' ';' | cut -c1-400)
  tailline=$(grep -E 'selftest \(|mutations: ' "$log" | tail -1 | tr -d '\n' | cut -c1-200)
  echo "round3 $name head=$HEAD_ID exit=$rc seconds=$(( $(date +%s) - start )) failing=\"$failing\" last=\"$tailline\" log=$log" >> "$OUT"
}

# AC1 to AC4 rows; exit 2 with 0 failed is the PARTIAL-run convention, not a red.
step suite-129 python3 scripts/selftest.py --suite 129_veldo_0270_small_proof

# Falsifiers: the five teeth mutations of finding 270, each must be killed (status passed). Round 2 of
# this run: driver_error, the noop control of proof_size.py could not load validate.py's sibling tracker.py.
step teeth-270 python3 scripts/check_teeth_mutations.py --finding 270 --worker-log-dir "$LOGS/teeth-270-workers"

echo "pending runs done; summary in $OUT, logs in $LOGS"
