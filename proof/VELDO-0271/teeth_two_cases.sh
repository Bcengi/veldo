#!/usr/bin/env bash
# VELDO-0271: the two teeth cases job 89 left without a readable cause, one case per driver run, with
# every log kept. Run from the worktree root on a clean tree, inside the shared host lock:
#   bash <host lock wrapper> bash proof/VELDO-0271/teeth_two_cases.sh <log dir>
# <log dir> is outside the repository; the script refuses one inside it. Nothing is written into the
# repository. For each case <log dir> receives:
#   <case>.log            the driver's own output (the receipt and the "mutations:" line)
#   <case>.summary.json   the driver's proof summary
#   <case>.workers/       the worker logs (--worker-log-dir)
#   <case>.diffs/         the applied mutation diff (--diff-dir)
#   <case>.shm-before.txt and <case>.shm-after.txt   the b139- directories under /dev/shm around the run
# <log dir>/results.txt has one line per case and the name, size and sha256 of every kept file.
# What to read:
#   oneleg271-lease-never-taken: job 89 said "worker exit 1" against the suite 103 rows
#     refused-before-launch/live/claude/busy and refused-before-launch/live/codex/busy; the worker log
#     says why the worker left.
#   oneleg271-factory-setup-calls-sudo: job 89 said worker_cleanup_error, "ownership ledger names
#     resources outside this worker: directory /dev/shm/b139-..."; the worker log and the two shm
#     listings say whether suite 73 left its base behind when the mutant made it leave early.
set -u
if [ $# -ne 1 ]; then
  echo "usage: bash proof/VELDO-0271/teeth_two_cases.sh <log dir outside the repository>" >&2
  exit 2
fi
ROOT=$(pwd -P)
if [ ! -f "$ROOT/scripts/check_teeth_mutations.py" ]; then
  echo "refused: run from the worktree root" >&2
  exit 2
fi
mkdir -p "$1" || exit 2
OUT=$(cd "$1" && pwd -P)
case "$OUT/" in
  "$ROOT"/*)
    echo "refused: the log directory is inside the repository" >&2
    exit 2;;
esac
RESULTS="$OUT/results.txt"
{
  echo "commit $(git rev-parse HEAD) tree $(git rev-parse 'HEAD^{tree}') dirty paths $(git status --porcelain | wc -l)"
  echo "host $(uname -n) $(python3 --version 2>&1) load $(cut -d' ' -f1-3 /proc/loadavg)"
} > "$RESULTS"
shm_list() { ls -ld /dev/shm/b139-* 2>/dev/null || echo "none"; }
overall=0
for name in oneleg271-lease-never-taken oneleg271-factory-setup-calls-sudo; do
  rm -rf "$OUT/$name.workers" "$OUT/$name.diffs"
  mkdir -p "$OUT/$name.diffs"
  shm_list > "$OUT/$name.shm-before.txt"
  python3 scripts/check_teeth_mutations.py --case "$name" --worker-log-dir "$OUT/$name.workers" \
    --diff-dir "$OUT/$name.diffs" --summary "$OUT/$name.summary.json" > "$OUT/$name.log" 2>&1
  code=$?
  shm_list > "$OUT/$name.shm-after.txt"
  [ "$code" = 0 ] || overall=1
  echo "$name exit $code $(grep -E '^mutations: ' "$OUT/$name.log" | tail -1)" >> "$RESULTS"
done
echo "kept files (bytes sha256 name):" >> "$RESULTS"
(cd "$OUT" && find . -type f ! -name results.txt | LC_ALL=C sort | while IFS= read -r file; do
  echo "$(stat -c %s "$file") $(sha256sum "$file" | cut -d' ' -f1) ${file#./}"
done) >> "$RESULTS"
cat "$RESULTS"
exit "$overall"
