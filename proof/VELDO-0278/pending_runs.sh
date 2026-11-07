#!/usr/bin/env bash
# VELDO-0278 pending runs, fix round 1. Run from the worktree root by the lead, already inside the
# shared gate lock (this script takes no lock itself). The fix round waited 1190 s on the lock
# (flock -w 540, 420, 230) and never got it, so none of these ran.
# Each step appends one line to proof/VELDO-0278/pending-summary.txt: the step, its exit code, its
# summary line, the failing row names (or "none"), and TRACEBACK if the run raised. Logs go to /tmp.
set -u
cd "$(dirname "$0")/../.."
LOGS=/tmp/veldo-0278-fix1-pending
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

# F1, F2, F3: the suites the fix round touched or turned green (01 carries the WARP-0733 AC4 row
# F2 restores; 14's --upto row runs suite 01; 08 holds the F3 row and its TEETH row; 101 holds F1).
# Expected: each exit=2 (PARTIAL), 0 failed.
step 01_warp_0101_reviewer_notes python3 scripts/selftest.py --suite 01_warp_0101_reviewer_notes
step 08_restoration_spec_generation_veldo python3 scripts/selftest.py --suite 08_restoration_spec_generation_veldo
step 14_warp_0717_subset_runner python3 scripts/selftest.py --suite 14_warp_0717_subset_runner
step 101_veldo_0208_landing_reuse python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse

# F4, AC1 proof evidence, run once (never at the gate; about 10 minutes, 15_warp_1404 alone ~540 s).
# Expected: exit 1, "verify stamp: refused", each of the eight estimation suites 0 failed; the one
# red row is parked suite 111's handoff-present row (the VELDO-0214 handoff left with AC3).
# Besides the step line, the per-suite lines (suite, passed, failed, seconds) go to the summary.
step parked_estimation python3 scripts/selftest.py --parked estimation
grep -E '^  [0-9]+_[a-z0-9_]+ +[0-9]+ passed +[0-9]+ failed' "$LOGS/parked_estimation.log" \
  | sed -E 's/^ +/parked: /; s/ +/ /g' >> "$SUMMARY"
