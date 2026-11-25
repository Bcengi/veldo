#!/usr/bin/env bash
set -u
evidence=$(mktemp -d)
# Keep diagnostic outputs outside the candidate while its input census runs.
trap 'cp "$evidence"/* .; rm -r "$evidence"' EXIT
python3 -B proof/VELDO-0364/targeted.py > "$evidence/targeted.json" 2>&1
unit_rc=$?
python3 -B scripts/check_wallclock.py > "$evidence/census.log" 2>&1
census_rc=$?
python3 -B scripts/check_personal_setup.py --base 0f2e081f0 > "$evidence/personal.log" 2>&1
personal_rc=$?
python3 -B proof/VELDO-0364/check_static.py > "$evidence/stale.json"
stale_rc=$?
printf 'checks unit=%s census=%s personal=%s stale=%s\n' "$unit_rc" "$census_rc" "$personal_rc" "$stale_rc"
if [ "$unit_rc$census_rc$personal_rc$stale_rc" != 0000 ]; then
  tail -n 35 "$evidence/targeted.json" "$evidence/census.log" "$evidence/personal.log" "$evidence/stale.json"
  exit 1
fi
/usr/bin/python3 -I -S scripts/qualify_mutation_host.py --receipt "$evidence/qualification.json" --cases proof/VELDO-0364/selection.json --batch-receipt "$evidence/batch.json" > "$evidence/batch.log" 2>&1
batch_rc=$?
if [ -f "$evidence/batch.json" ]; then
  python3 proof/VELDO-0364/compare.py proof/VELDO-0364/expected.json "$evidence/batch.json" > "$evidence/comparison.json"
  comparison_rc=$?
  gzip -n "$evidence/batch.json"
else
  comparison_rc=1
fi
tail -n 12 "$evidence/batch.log"
printf 'batch=%s comparison=%s\n' "$batch_rc" "$comparison_rc"
test "$batch_rc$comparison_rc" = 00
