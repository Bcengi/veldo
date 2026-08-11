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
# Each entry is a name, one derived path, and the command that regenerates it in
# place. Every entry runs, so one stale file cannot hide another.
#
# GENERATED_CHECK_ROOT and GENERATED_CHECK_ONLY exist so the suite can drive THIS
# script hermetically over a fixture tree, the way DOCS_CHECK_PATHS lets it drive
# check_docs.sh. A stage nobody can run over a planted-bad input is a stage nobody
# has tested.
set -u
cd "${GENERATED_CHECK_ROOT:-$(dirname "$0")/..}"

FAILED=0

check_one() {
  # $1 entry name, $2 the derived path, $3 the regeneration command (writes $2 in place)
  local name="$1" path="$2" cmd="$3" before
  if [ -n "${GENERATED_CHECK_ONLY:-}" ] && [ "$name" != "$GENERATED_CHECK_ONLY" ]; then
    return
  fi
  before=$(mktemp)
  cp "$path" "$before"
  if ! bash -c "$cmd"; then
    echo "generated: FAIL (the generator for ${path} errored or refused)"
    rm -f "$before"; FAILED=1; return
  fi
  if diff -u "$before" "$path"; then
    echo "generated: pass (${path})"
  else
    echo "generated: FAIL (${path} was stale; regeneration changed it above and has already"
    echo "                 rewritten it - commit the regenerated file)"
    FAILED=1
  fi
  rm -f "$before"
}

check_one spec-index specs/index.md \
  'python3 scripts/update_index.py >/dev/null'
# The survey never writes, so the redirect lives here rather than in the tool. It
# emits to a temporary first: a generator that failed halfway through a redirect
# straight onto the artifact would leave a truncated document behind.
check_one crossing-state proof/WARP-0716/crossing-state.md \
  'tmp=$(mktemp) && python3 scripts/suite_survey.py --emit-report >"$tmp" \
     && cp "$tmp" proof/WARP-0716/crossing-state.md && rm -f "$tmp"'

# WARP-0712's order-dependence report is derived from the COMMITTED measurement beside it,
# not from a fresh measurement: producing the measurement runs the suite once and then one
# subset per region, which is minutes, and it measures scripts/selftest.py, the one file every
# item edits. A freshness check that re-measured or pinned that digest would redden this gate
# on every single item with a minutes-long remedy, which is the trap WARP-0716's first version
# built. Regeneration here is a millisecond render of recorded data.
check_one order-dependence proof/WARP-0712/order-dependence.md \
  'tmp=$(mktemp) && python3 scripts/suite_slice.py --emit-report \
     --from proof/WARP-0712/order-dependence.json >"$tmp" \
     && cp "$tmp" proof/WARP-0712/order-dependence.md && rm -f "$tmp"'
# The split plan is DERIVED from the same measurement rather than drawn around topic names,
# which is what AC1 asks for: a boundary set taken from where data actually stops crossing.
check_one split-plan proof/WARP-0712/split-plan.md \
  'tmp=$(mktemp) && python3 scripts/suite_slice.py --emit-plan \
     --from proof/WARP-0712/order-dependence.json >"$tmp" \
     && cp "$tmp" proof/WARP-0712/split-plan.md && rm -f "$tmp"'

# WARP-0717's prerequisite closure table, which `--suite NAME` runs. It is DERIVED from the
# same committed measurement, by the same argument as the two entries above: a millisecond
# render of recorded data, never a fresh measurement. It belongs here rather than in a
# hand-maintained table because a fragment added to the manifest without a matching closure
# entry has to be a RED with a one-command remedy, not a silently missing closure. The
# generator REFUSES rather than emit an empty closure for a fragment whose prerequisites are
# neither measured nor declared, so a stale file cannot be papered over by regenerating it.
check_one suite-requires scripts/suites/requires.json \
  'python3 scripts/run_scope.py --emit-requires >/dev/null'

if [ "$FAILED" -eq 0 ]; then
  echo "generated: pass"
  exit 0
fi
exit 1
