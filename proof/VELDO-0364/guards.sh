#!/usr/bin/env bash
set -u
evidence=$(mktemp -d)
trap 'cp "$evidence"/* .; rm -r "$evidence"' EXIT
python3 -B proof/VELDO-0364/compare_controls.py > "$evidence/comparator-controls.json"
compare_rc=$?
bash scripts/check_template_sync.sh > "$evidence/template-sync.log"
sync_rc=$?
python3 -B .veldo/validate.py spec specs/VELDO-0364-host-relative-mutation-qualification.md > "$evidence/spec.log" 2>&1
spec_rc=$?
/usr/bin/python3 -I -S scripts/qualify_mutation_host.py --receipt "$evidence/guard-qualification.json" --cases proof/VELDO-0364/guards.json --batch-receipt "$evidence/guards.json" > "$evidence/guards.log" 2>&1
guard_rc=$?
if [ -f "$evidence/guards.json" ]; then gzip -n "$evidence/guards.json"; fi
tail -n 12 "$evidence/guards.log"
printf 'checks comparator=%s sync=%s spec=%s guards=%s\n' "$compare_rc" "$sync_rc" "$spec_rc" "$guard_rc"
test "$compare_rc$sync_rc$spec_rc$guard_rc" = 0000
