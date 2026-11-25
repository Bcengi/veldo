#!/usr/bin/env bash
set -u
python3 -B scripts/selftest.py --suite 162_veldo_0364_host_relative > targeted.log 2>&1
unit_rc=$?
python3 -B scripts/check_wallclock.py > census.log 2>&1
census_rc=$?
python3 -B scripts/check_personal_setup.py --base 0f2e081f0 > personal.log 2>&1
personal_rc=$?
python3 -B proof/VELDO-0364/check_static.py > stale.json
stale_rc=$?
printf 'checks unit=%s census=%s personal=%s stale=%s\n' "$unit_rc" "$census_rc" "$personal_rc" "$stale_rc"
if [ "$unit_rc$census_rc$personal_rc$stale_rc" != 0000 ]; then
  tail -35 targeted.log census.log personal.log stale.json
  exit 1
fi
python3 -I -S scripts/qualify_mutation_host.py --receipt qualification.json --cases proof/VELDO-0364/selection.json --batch-receipt batch.json > batch.log 2>&1
batch_rc=$?
if [ -f batch.json ]; then
  python3 proof/VELDO-0364/compare.py proof/VELDO-0364/expected.json batch.json > comparison.json
  comparison_rc=$?
  gzip -n batch.json
else
  comparison_rc=1
fi
tail -12 batch.log
printf 'batch=%s comparison=%s\n' "$batch_rc" "$comparison_rc"
test "$batch_rc$comparison_rc" = 00
