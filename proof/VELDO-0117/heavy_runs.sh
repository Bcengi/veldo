#!/usr/bin/env bash
# VELDO-0117: every heavy run behind the proof, in one script.
#
# The lead queues this through the gate lock. It takes no lock of its own and starts no gate.
# Run it from anywhere inside the checkout that holds the built change, with the change committed
# (the red-before step clones this checkout's HEAD):
#
#   bash proof/VELDO-0117/heavy_runs.sh
#
# Steps, each in its own memory-capped scope, each writing one small summary:
#   1. red-before   proof/VELDO-0117/red-before.summary.json
#      Suite 113_veldo_0117_domain_store as built, in a scratch checkout of HEAD whose three
#      product modules (.veldo/control_store.py, control_client.py, control_enrollment.py) are
#      those of f6b8ae41. One run, about half a minute. All three rows must be red on the
#      checks the summary names, and none because its section raised.
#   2. green-after  proof/VELDO-0117/green-after.summary.json
#      The same suite in this checkout, VELDO_0117_RUNS times (3). About 20 s a run.
#   3. teeth        proof/VELDO-0117/teeth.summary.json
#      The eight mutants of finding 117, VELDO_0117_JOBS workers at a time (3). The applied
#      diffs are named in the summary with their sha256.
#
# None of these has been run by the builder. The raw output goes to a scratch directory under
# ${TMPDIR:-/tmp}. Each summary names every raw file with its size and sha256, and the directory
# is deleted at the end.
# A step that fails does not stop the ones after it. The exit code is 0 only when all three pass.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root" || exit 2

scratch="$(mktemp -d "${TMPDIR:-/tmp}/veldo-0117.XXXXXXXX")" || exit 2
trap 'chmod -R u+w "$scratch" 2>/dev/null; rm -rf "$scratch"' EXIT

scoped() {
    systemd-run --user --scope --quiet -p MemoryMax=10G "$@"
}

status=0
scoped python3 proof/VELDO-0117/heavy_summary.py red-before --scratch "$scratch/red-before" --base f6b8ae41 || status=1
scoped python3 proof/VELDO-0117/heavy_summary.py green-after --scratch "$scratch/green-after" --runs "${VELDO_0117_RUNS:-3}" || status=1
scoped python3 proof/VELDO-0117/heavy_summary.py teeth --scratch "$scratch/teeth" --jobs "${VELDO_0117_JOBS:-3}" || status=1

if [ "$status" -eq 0 ]; then
    echo "VELDO-0117 heavy runs: all three steps pass"
else
    echo "VELDO-0117 heavy runs: at least one step did not pass; read the summaries under proof/VELDO-0117/"
fi
exit "$status"
