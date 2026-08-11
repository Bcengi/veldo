#!/usr/bin/env bash
# The config-schema runner's own regression: the passing fixture must pass
# (exit 0, every sample's verdict matches its label) and the deliberately
# mislabeled fixture must fail (exit 1, the valid-labeled sample that violates
# the schema caught). Run on demand and as the runner's proof. The runner's
# CONTROL LOGIC is also unit-tested over these same fixtures in
# scripts/selftest.py, so this script is not wired into the every-commit gate;
# it is here for a reviewer to rerun end to end. Standard library only, so no
# setup is needed.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

python3 "$here/config_runner.py" "$here/fixtures/pass.schema.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass fixture: exit 0 (correct - every verdict matched its label)"; else echo "pass fixture: FAIL (expected 0)"; fail=1; fi

python3 "$here/config_runner.py" "$here/fixtures/fail.schema.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail fixture: exit 1 (correct - mislabeled sample caught)"; else echo "fail fixture: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "config runner self-test: pass"; else echo "config runner self-test: FAIL"; fi
exit $fail
