#!/usr/bin/env bash
# VELDO-0278 pending runs, fix round 2. Run from the worktree root by the lead, already inside the
# shared gate lock (this script takes no lock itself). The fix round waited 910 s on the lock
# (flock -w 300, 330, 280) and never got it, so none of these ran under it.
# Each step appends one line to proof/VELDO-0278/pending-summary.txt: the step, its exit code, its
# summary line, the failing row names (or "none"), and TRACEBACK if the run raised. Logs go to /tmp.
set -u
cd "$(dirname "$0")/../.."
LOGS=/tmp/veldo-0278-fix2-pending
SUMMARY=proof/VELDO-0278/pending-summary.txt
mkdir -p "$LOGS"
: > "$SUMMARY"

step() {
  local name=$1; shift
  local log="$LOGS/$name.log"
  "$@" > "$log" 2>&1
  local code=$?
  local summary fails tb=""
  summary=$(grep -E '^selftest ' "$log" | tail -1)
  fails=$(grep -E '^ *SELFTEST FAIL: ' "$log" | sed -E 's/^ *SELFTEST FAIL: //; s/:.*//' | paste -sd ';' -)
  grep -q '^Traceback' "$log" && tb=" TRACEBACK"
  echo "$name exit=$code | $summary | failing: ${fails:-none}$tb" >> "$SUMMARY"
}

# Fix round 2: suite 101's leg-time row now reads 'authority-copy-records-no-leg-time'; suite 129
# reads the eight and the nine from the spec and gains row parked/spec-names-eight-fragments-and-nine-modules.
# Expected: 101 exit=1 with exactly the two inherited reds (sandbox/unavailable-refuses-before-exec,
# sandbox/old-abi-refuses-before-exec); 129 exit=2, 7 passed, 0 failed.
step 101_veldo_0208_landing_reuse python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse
step 129_veldo_0278_parked_estimation python3 scripts/selftest.py --suite 129_veldo_0278_parked_estimation

# AC1 proof evidence, run once (never at the gate; about 10 minutes, 15_warp_1404 alone ~540 s).
# Expected: exit 1, "verify stamp: refused", each of the eight estimation suites 0 failed (WARP-1409
# AC6 green again); the one red row is parked suite 111's handoff-present row, red by design (AC3).
# Besides the step line, the per-suite lines (suite, passed, failed, seconds) go to the summary.
step parked_estimation python3 scripts/selftest.py --parked estimation
grep -E '^  [0-9]+_[a-z0-9_]+ +[0-9]+ passed +[0-9]+ failed' "$LOGS/parked_estimation.log" \
  | sed -E 's/^ +/parked: /; s/ +/ /g' >> "$SUMMARY"
