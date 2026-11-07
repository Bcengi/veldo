#!/usr/bin/env bash
# VELDO-0272 runs, each under the shared gate lock (scripts/gate_host.json). Run from the worktree root.
# Logs go to proof/VELDO-0272/runs/<name>.log; the last line of each log is the command's exit code.
set -u
cd "$(git rev-parse --show-toplevel)"
LOCK="$HOME/.local/state/core-gates/.gate.lock"
OUT=proof/VELDO-0272/runs
mkdir -p "$OUT"

run() {
  local name="$1"; shift
  echo "== $name: $*"
  flock -x "$LOCK" "$@" > "$OUT/$name.log" 2>&1
  local code=$?
  echo "exit $code" >> "$OUT/$name.log"
  echo "   exit $code"
}

# The new suite and its falsifiers with the gate's mutation driver.
run suite-129 python3 scripts/selftest.py --suite 129_veldo_0272_approval_scope
run teeth-272 python3 scripts/check_teeth_mutations.py --finding 272

# Suites that read init_scaffold's asset list as a whole (not only "rel in scaffold._FILES") or load the
# reporter that now loads landed_summary.py beside it.
for s in 01_warp_0101_reviewer_notes 26_veldo_0009_install_stamp 66_veldo_0047_authority \
         72_veldo_0128_reports 86_veldo_0168_text 86_veldo_0189_engine_upgrade 101_veldo_0208_landing_reuse \
         110_veldo_0143_new_project; do
  run "suite-$s" python3 scripts/selftest.py --suite "$s"
done

# Landing and candidate suites named in the README as possibly affected by landing_without_review.
for s in 67_veldo_0056_candidates 69_veldo_0058_gate_output 70_veldo_0057_landing 86_veldo_0148_re_land; do
  run "suite-$s" python3 scripts/selftest.py --suite "$s"
done
