#!/usr/bin/env bash
# VELDO-0291: every heavy run behind the proof, in one script.
#
# The lead queues this through the gate lock. It takes no lock of its own and starts no gate.
# Run it from anywhere inside the checkout that holds the built change:
#
#   bash proof/VELDO-0291/heavy_runs.sh
#
# Steps, each in its own memory-capped scope, each writing one small summary:
#   1. red-before   proof/VELDO-0291/red-before.summary.json
#      Suite 86 as built, in a scratch checkout of 646ff7c8, three runs: one per criterion, with
#      that criterion's behavior put back as it is at 646ff7c8. About 80 s a run.
#   2. green-after  proof/VELDO-0291/green-after.summary.json
#      Suite 86 as built, in this checkout, VELDO_0291_RUNS times (3). About 80 s a run.
#   3. teeth        proof/VELDO-0291/teeth.summary.json
#      The eight mutants of finding 291, VELDO_0291_JOBS workers at a time (3).
#
# The raw output goes to a scratch directory under ${TMPDIR:-/tmp}. Each summary names every raw
# file with its size and sha256, and the directory is deleted at the end.
# A step that fails does not stop the ones after it. The exit code is 0 only when all three pass.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root" || exit 2

scratch="$(mktemp -d "${TMPDIR:-/tmp}/veldo-0291.XXXXXXXX")" || exit 2
trap 'chmod -R u+w "$scratch" 2>/dev/null; rm -rf "$scratch"' EXIT

scoped() {
    systemd-run --user --scope --quiet -p MemoryMax=10G "$@"
}

status=0
scoped python3 proof/VELDO-0291/heavy_summary.py red-before --scratch "$scratch/red-before" --base 646ff7c8 || status=1
scoped python3 proof/VELDO-0291/heavy_summary.py green-after --scratch "$scratch/green-after" --runs "${VELDO_0291_RUNS:-3}" || status=1
scoped python3 proof/VELDO-0291/heavy_summary.py teeth --scratch "$scratch/teeth" --jobs "${VELDO_0291_JOBS:-3}" || status=1

if [ "$status" -eq 0 ]; then
    echo "VELDO-0291 heavy runs: all three steps pass"
else
    echo "VELDO-0291 heavy runs: at least one step did not pass; read the summaries under proof/VELDO-0291/"
fi
exit "$status"
