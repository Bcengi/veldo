#!/usr/bin/env bash
# VELDO-0272 fix round 1: the runs the gate lock did not allow (2026-11-07). The lead runs this script
# already inside the shared gate lock, so it takes no lock itself. Run from the worktree root.
# Each step logs to /tmp (never into the repository) and appends one line to
# proof/VELDO-0272/pending-summary.txt: name, exit code, and the failing row names (or "none").
set -u
cd "$(git rev-parse --show-toplevel)"
SUMMARY=proof/VELDO-0272/pending-summary.txt

step() {
  local name="$1"; shift
  local log="/tmp/v272-pending-$name.log"
  "$@" > "$log" 2>&1
  local code=$?
  local failing
  failing=$(grep -E '^ *SELFTEST FAIL: ' "$log" | sed -E 's/^ *SELFTEST FAIL: //' | paste -sd ';' -)
  echo "$name exit $code failing: ${failing:-none} (log $log)" >> "$SUMMARY"
}

# The four landing suites whose fixtures fix round 1 changed (F7). In 101 the two sandbox rows
# (sandbox/unavailable-refuses-before-exec, sandbox/old-abi-refuses-before-exec) are inherited reds on
# main and are expected to fail; every other row is expected to pass.
step suite-67_veldo_0056_candidates python3 scripts/selftest.py --suite 67_veldo_0056_candidates
step suite-69_veldo_0058_gate_output python3 scripts/selftest.py --suite 69_veldo_0058_gate_output
step suite-86_veldo_0148_re_land python3 scripts/selftest.py --suite 86_veldo_0148_re_land
step suite-101_veldo_0208_landing_reuse python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse

# Not asked for, added as a check: the landing suite that pushes through the policy check and passed
# before fix round 1, whose rule changed (review judged per spec, F5).
step suite-70_veldo_0057_landing python3 scripts/selftest.py --suite 70_veldo_0057_landing
