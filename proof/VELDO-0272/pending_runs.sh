#!/usr/bin/env bash
# VELDO-0272 fix round 3: the runs the gate lock did not allow (2026-11-07). The lead runs this script
# already inside the shared gate lock, so it takes no lock itself. Run from the worktree root.
# Each step logs to /tmp (never into the repository) and appends one line to
# proof/VELDO-0272/pending-summary.txt: name, exit code, and the failing row names (or "none").
set -u
cd "$(git rev-parse --show-toplevel)"
SUMMARY=proof/VELDO-0272/pending-summary.txt

step() {
  local name="$1"; shift
  local log="/tmp/v272-r3-pending-$name.log"
  "$@" > "$log" 2>&1
  local code=$?
  local failing
  failing=$(grep -E '^ *SELFTEST FAIL: ' "$log" | sed -E 's/^ *SELFTEST FAIL: //' | paste -sd ';' -)
  echo "$name exit $code failing: ${failing:-none} (log $log)" >> "$SUMMARY"
}

# The mutation driver prints one receipt line; a failure names no rows, so the line itself is kept.
teeth() {
  local log=/tmp/v272-r3-pending-teeth-272.log
  python3 scripts/check_teeth_mutations.py --finding 272 > "$log" 2>&1
  local code=$?
  echo "teeth-272 exit $code $(grep -E '^mutations: ' "$log" | tail -1) (log $log)" >> "$SUMMARY"
}

# The suite of this ticket (row AC3 review/covered is N3) and suite 01, whose objection rows now push
# a reviewed spec. Exit 2 from selftest --suite is the partial-run exit; "failing: none" is green.
step suite-129_veldo_0272_approval_scope python3 scripts/selftest.py --suite 129_veldo_0272_approval_scope
step suite-01_warp_0101_reviewer_notes python3 scripts/selftest.py --suite 01_warp_0101_reviewer_notes
# Finding 272 with the N3 falsifier scope272-uncovered-code-lands: every mutation must be rejected.
teeth
# The landing suites whose fixtures push through the policy check. In 101 the two sandbox rows
# (sandbox/unavailable-refuses-before-exec, sandbox/old-abi-refuses-before-exec) are inherited reds on
# main and are expected to fail; every other row is expected to pass.
step suite-67_veldo_0056_candidates python3 scripts/selftest.py --suite 67_veldo_0056_candidates
step suite-69_veldo_0058_gate_output python3 scripts/selftest.py --suite 69_veldo_0058_gate_output
step suite-86_veldo_0148_re_land python3 scripts/selftest.py --suite 86_veldo_0148_re_land
step suite-101_veldo_0208_landing_reuse python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse
