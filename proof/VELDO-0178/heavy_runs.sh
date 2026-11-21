#!/usr/bin/env bash
# VELDO-0178 fix round 2: the heavy runs behind the proof, in one script.
#
# The lead queues this through the gate lock. It takes no lock of its own and starts no gate.
# Run it from anywhere inside the checkout that holds the built change:
#
#   bash proof/VELDO-0178/heavy_runs.sh
#
# Each registered finding 178 mutation case is run alone through scripts/check_gate_mutations.py
# with its case option, in its own memory-capped scope, honouring the committed
# scripts/gate_unconfined.json (suite 133 is not in it, so each case runs in the confined leg).
# The new case of the re-review of 2026-11-11 (finding A) runs first; it has no receipt yet:
#   account178-window-source-served   proof/VELDO-0178/mutation-account178-window-source-served.txt
# The four earlier cases are retaken at this head, because their committed receipts were taken at
# 1b51fa3d, before the branch was rebased (re-review finding B):
#   read178-domain-membership         proof/VELDO-0178/mutation-read178-domain-membership.txt
#   record178-project-alone           proof/VELDO-0178/mutation-record178-project-alone.txt
#   feed178-conversation-by-scope     proof/VELDO-0178/mutation-feed178-conversation-by-scope.txt
#   index178-released-by-dispatch-id  proof/VELDO-0178/mutation-index178-released-by-dispatch-id.txt
# Each file keeps the case, the commit, the exit code and the run's output. A case passes when the
# run exits 0: baseline and no-op green, the mutant killed at its row (AC1/events for the new case).
# A case that fails does not stop the others. The exit code is 0 only when all five pass.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root" || exit 2

scoped() {
    systemd-run --user --scope --quiet -p MemoryMax=10G "$@"
}

head_commit="$(git rev-parse --short=8 HEAD)"
status=0
for name in account178-window-source-served read178-domain-membership record178-project-alone \
            feed178-conversation-by-scope index178-released-by-dispatch-id; do
    out="proof/VELDO-0178/mutation-$name.txt"
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
    echo "VELDO-0178 heavy runs: all five mutation cases pass"
else
    echo "VELDO-0178 heavy runs: at least one case did not pass; read proof/VELDO-0178/mutation-*.txt"
fi
exit "$status"
