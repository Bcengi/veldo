#!/bin/sh
# VELDO-0274 fix round 5: the runs still owed, from the checkout root. The lead runs this already inside the
# gate lock, so there is no flock and no systemd-run here. Each step appends one line to
# proof/VELDO-0274/pending-summary.txt with its exit code, summary and failing row names; logs go under
# /tmp/v274-pending, never in the repository.
# The 274 mutation cases (now four: AC1, AC2 (two) and AC3's suite 86 without its ExitStack) run through the
# coordinator's own CLI (check_gate_mutations.py), the only entry that passes the unconfined leg from
# scripts/gate_unconfined.json; check_teeth_mutations.py runs them confined.
set -u
LOG=/tmp/v274-pending
SUM=proof/VELDO-0274/pending-summary.txt
mkdir -p "$LOG"
echo "head $(git rev-parse --short HEAD) $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SUM"

python3 scripts/check_gate_mutations.py --finding 274 > "$LOG/gate-mutations.log" 2>&1
code=$?
echo "check_gate_mutations.py --finding 274: exit=$code $(grep '^mutations:' "$LOG/gate-mutations.log" | tail -n 1) $(grep '^   mutation: unconfined leg' "$LOG/gate-mutations.log" | tail -n 1) refused: $(grep -oE '(invalid_baseline|missing_target|mutation_survived|driver_error)[^ ]*( [^ ]+)?' "$LOG/gate-mutations.log" | sort -u | tr '\n' ' ')" >> "$SUM"

python3 scripts/selftest.py --suite 129_veldo_0274_factory_slices > "$LOG/s129.log" 2>&1
code=$?
echo "suite 129 --suite: exit=$code $(grep -E 'passed|failed' "$LOG/s129.log" | tail -n 1) failing: $(grep 'SELFTEST FAIL' "$LOG/s129.log" | sed 's/^ *SELFTEST FAIL: //' | tr '\n' ' ')" >> "$SUM"

echo "veldo0127/veldo0274 units loaded after: $(systemctl --user list-units --all --no-legend 'veldo0127-*' 'veldo0274-*' | wc -l)" >> "$SUM"
