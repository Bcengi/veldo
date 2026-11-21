#!/usr/bin/env bash
# VELDO-0187 fix round 3: the heavy runs behind the proof, in one script.
#
# The lead queues this through the gate lock. It takes no lock of its own and starts no gate.
# Run it from anywhere inside the checkout that holds the built change:
#
#   bash proof/VELDO-0187/heavy_runs.sh
#
# Each registered finding 187 mutation case is run alone through scripts/check_gate_mutations.py
# with its case option, in its own memory-capped scope, honouring the committed
# scripts/gate_unconfined.json (suites 138 and 128 are on it, so their cases run in the unconfined
# leg; check_teeth_mutations.py run directly confines suite 138 and gives invalid_baseline).
#
# The three cases of the build are retaken at this head, because their committed receipts were
# taken at b6849b26 with a temporary uncommitted unconfined entry (review of 2026-11-11, F6):
#   feed187-any-version       proof/VELDO-0187/mutation-feed187-any-version.txt       AC1/unqualified
#   feed187-held-session      proof/VELDO-0187/mutation-feed187-held-session.txt      AC2/redaction
#   feed187-dropped           proof/VELDO-0187/mutation-feed187-dropped.txt           AC3/pending
# The five cases fix round 3 added have no receipt yet (F2, F3 and F5):
#   feed187-refusal-pending   proof/VELDO-0187/mutation-feed187-refusal-pending.txt   AC3/worker-refusal
#   feed187-version-unasked   proof/VELDO-0187/mutation-feed187-version-unasked.txt   AC1/running-version
#   attach187-check-ignored   proof/VELDO-0187/mutation-attach187-check-ignored.txt   AC3/project-check (suite 128)
#   point187-check-ignored    proof/VELDO-0187/mutation-point187-check-ignored.txt    AC1/project-check (suite 136)
#   point187-existing-as-new  proof/VELDO-0187/mutation-point187-existing-as-new.txt  AC1/project-check (suite 136)
# Each file keeps the case, the commit, the exit code and the run's output. A case passes when the
# run exits 0: baseline and no-op green, the mutant killed at its row.
# A case that fails does not stop the others. The exit code is 0 only when all eight pass.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root" || exit 2

scoped() {
    systemd-run --user --scope --quiet -p MemoryMax=10G "$@"
}

head_commit="$(git rev-parse --short=8 HEAD)"
status=0
for name in feed187-any-version feed187-held-session feed187-dropped \
            feed187-refusal-pending feed187-version-unasked \
            attach187-check-ignored point187-check-ignored point187-existing-as-new; do
    out="proof/VELDO-0187/mutation-$name.txt"
    raw="$(scoped python3 scripts/check_gate_mutations.py --case "$name" 2>&1)"
    code=$?
    {
        echo "case: $name"
        echo "run: python3 scripts/check_gate_mutations.py with the case option naming $name, alone, at $head_commit, in a transient user scope with MemoryMax=10G, honouring the committed scripts/gate_unconfined.json; exit $code"
        printf '%s\n' "$raw" | tail -n 40
    } > "$out"
    echo "$name: exit $code"
    [ "$code" -eq 0 ] || status=1
done

if [ "$status" -eq 0 ]; then
    echo "VELDO-0187 heavy runs: all eight mutation cases pass"
else
    echo "VELDO-0187 heavy runs: at least one case did not pass; read proof/VELDO-0187/mutation-*.txt"
fi
exit "$status"
