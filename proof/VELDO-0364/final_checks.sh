#!/usr/bin/env bash
set -u
evidence=$(mktemp -d)
trap 'cp "$evidence"/* .; rm -r "$evidence"' EXIT
python3 -B proof/VELDO-0364/targeted.py > "$evidence/targeted.json"
unit_rc=$?
python3 -B proof/VELDO-0364/compare_controls.py > "$evidence/comparator-controls.json"
compare_rc=$?
python3 -B scripts/check_wallclock.py > "$evidence/census.log"
census_rc=$?
python3 -B scripts/check_personal_setup.py --base 0f2e081f0 > "$evidence/personal.log"
personal_rc=$?
python3 -B proof/VELDO-0364/check_static.py > "$evidence/stale.json"
stale_rc=$?
bash scripts/check_template_sync.sh > "$evidence/template-sync.log"
sync_rc=$?
python3 -B .veldo/validate.py spec specs/VELDO-0364-host-relative-mutation-qualification.md > "$evidence/spec.log" 2>&1
spec_rc=$?
/usr/bin/python3 -I -S scripts/qualify_mutation_host.py --receipt "$evidence/qualification.json" > "$evidence/qualification.log" 2>&1
qualification_rc=$?
cat "$evidence/qualification.log"
printf 'checks unit=%s comparator=%s census=%s personal=%s stale=%s sync=%s spec=%s qualification=%s\n' "$unit_rc" "$compare_rc" "$census_rc" "$personal_rc" "$stale_rc" "$sync_rc" "$spec_rc" "$qualification_rc"
test "$unit_rc$compare_rc$census_rc$personal_rc$stale_rc$sync_rc$spec_rc$qualification_rc" = 00000000
