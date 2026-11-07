#!/usr/bin/env bash
# VELDO-0270 pending runs, fix round 2 (suite 129 already ran green at 4f4d04c4). The lead runs this from the worktree root, already inside
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
  failing=$(grep -oE 'SELFTEST FAIL: .*' "$log" | sed 's/^SELFTEST FAIL: //' | tr '\n' ';' | cut -c1-400)
  tailline=$(grep -E 'selftest \(|mutations: ' "$log" | tail -1 | tr -d '\n' | cut -c1-200)
  echo "round2 $name head=$HEAD_ID exit=$rc seconds=$(( $(date +%s) - start )) failing=\"$failing\" last=\"$tailline\" log=$log" >> "$OUT"
}

# AC1 to AC4 rows; exit 2 with 0 failed is the PARTIAL-run convention, not a red.
step suite-129 python3 scripts/selftest.py --suite 129_veldo_0270_small_proof

# Falsifiers: the five teeth mutations of finding 270, each must be killed (status passed).
step teeth-270 python3 scripts/check_teeth_mutations.py --finding 270 --worker-log-dir "$LOGS/teeth-270-workers"

# Red 2 of the lead's run: VELDO-0189 upgrade/census (fixed in a2f920d0).
step suite-86_veldo_0189_engine_upgrade python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade

# Red 3 of the lead's run: WARP-1309 AC6 validate.py file_lines budget (suite 01 holds the row).
# Fixed in round 2 (proof size rules moved to .veldo/proof_size.py; validate.py 871 lines).
step suite-01_warp_0101_reviewer_notes python3 scripts/selftest.py --suite 01_warp_0101_reviewer_notes

# The lead's 4 suite command that showed red 3.
step suite-06_capabilities_manifest_honesty_veldo python3 scripts/selftest.py --suite 06_capabilities_manifest_honesty_veldo

echo "pending runs done; summary in $OUT, logs in $LOGS"
