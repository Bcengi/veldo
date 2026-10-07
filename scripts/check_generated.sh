#!/usr/bin/env bash
# Derived-file freshness: regeneration must be a no-op. Snapshot-based on
# purpose: red if and only if the generator changes the file, independent
# of whatever else is uncommitted in the working tree.
#
# EVERY DERIVED ARTIFACT BELONGS HERE, not in a hand-maintained guard. A generated
# file policed by re-deriving each of its figures against a hand-written copy is a
# check with teeth and an unbounded manual cost to satisfy, which is a trap:
# WARP-0716 published a hand-written report guarded that way and ordinary growth of
# the test suite made it unsatisfiable without a hand rewrite. The remedy a stage
# like this leaves is always the same one command, so the cost stays flat as the
# corpus grows.
#
# Each entry is a name, one derived path, and the command that regenerates it into "$out";
# the same command with the derived path in place of "$out" is the remedy. Every entry runs,
# so one stale file cannot hide another.
#
# THE STAGE NEVER WRITES THE TREE IT VERIFIES. Each generator writes into "$out", a private
# temporary file, and the committed file is compared with it. The gate runs this stage over a
# read-only candidate tree (VELDO-0208), where an in-place regeneration is refused outright,
# and a check that repaired what it was checking would hide the red it reports anyway.
#
# GENERATED_CHECK_ROOT and GENERATED_CHECK_ONLY exist so the suite can drive THIS
# script hermetically over a fixture tree, the way DOCS_CHECK_PATHS lets it drive
# check_docs.sh. A stage nobody can run over a planted-bad input is a stage nobody
# has tested.
set -u
cd "${GENERATED_CHECK_ROOT:-$(dirname "$0")/..}"

FAILED=0

check_one() {
  # $1 entry name, $2 the derived path, $3 the command that writes the regenerated file to "$out"
  local name="$1" path="$2" cmd="$3" out remedy
  if [ -n "${GENERATED_CHECK_ONLY:-}" ] && [ "$name" != "$GENERATED_CHECK_ONLY" ]; then
    return
  fi
  out=$(mktemp)
  if ! out="$out" bash -c "$cmd"; then
    echo "generated: FAIL (the generator for ${path} errored or refused)"
    rm -f "$out"; FAILED=1; return
  fi
  if diff -u "$path" "$out"; then
    echo "generated: pass (${path})"
  else
    remedy=${cmd//\"\$out\"/$path}
    echo "generated: FAIL (${path} was stale; the diff above is what regeneration produces."
    echo "                 Nothing was rewritten: run \`${remedy}\` and commit the result)"
    FAILED=1
  fi
  rm -f "$out"
}

check_one spec-index specs/index.md \
  'python3 scripts/update_index.py --output "$out" >/dev/null'
# The survey never writes, so the redirect lives here rather than in the tool.
check_one crossing-state proof/WARP-0716/crossing-state.md \
  'python3 scripts/suite_survey.py --emit-report >"$out"'

# WARP-0712's order-dependence report is derived from the COMMITTED measurement beside it,
# not from a fresh measurement: producing the measurement runs the suite once and then one
# subset per region, which is minutes, and it measures scripts/selftest.py, the one file every
# item edits. A freshness check that re-measured or pinned that digest would redden this gate
# on every single item with a minutes-long remedy, which is the trap WARP-0716's first version
# built. Regeneration here is a millisecond render of recorded data.
check_one order-dependence proof/WARP-0712/order-dependence.md \
  'python3 scripts/suite_slice.py --emit-report \
     --from proof/WARP-0712/order-dependence.json >"$out"'
# The split plan is DERIVED from the same measurement rather than drawn around topic names,
# which is what AC1 asks for: a boundary set taken from where data actually stops crossing.
check_one split-plan proof/WARP-0712/split-plan.md \
  'python3 scripts/suite_slice.py --emit-plan \
     --from proof/WARP-0712/order-dependence.json >"$out"'

# WARP-0717's prerequisite closure table, which `--suite NAME` runs. It is DERIVED from the
# same committed measurement, by the same argument as the two entries above: a millisecond
# render of recorded data, never a fresh measurement. It belongs here rather than in a
# hand-maintained table because a fragment added to the manifest without a matching closure
# entry has to be a RED with a one-command remedy, not a silently missing closure. The
# generator REFUSES rather than emit an empty closure for a fragment whose prerequisites are
# neither measured nor declared, so a stale file cannot be papered over by regenerating it.
check_one suite-requires scripts/suites/requires.json \
  'python3 scripts/run_scope.py --emit-requires --output "$out" >/dev/null'

if [ "$FAILED" -eq 0 ]; then
  echo "generated: pass"
  exit 0
fi
exit 1
