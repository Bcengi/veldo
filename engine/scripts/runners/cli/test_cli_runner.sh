#!/usr/bin/env bash
# The CLI runner's own regression: the passing fixture must pass (exit 0) and
# the deliberately-broken fixture must fail (exit 1) with the failure caught.
# Run on demand and as the runner's proof. The runner's CONTROL LOGIC is also
# unit-tested over these same fixtures in scripts/selftest.py, so this script
# is not wired into the every-commit gate; it is here for a reviewer to rerun
# end to end. Fixtures drive commands present on any POSIX system, so no tool
# needs installing.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

python3 "$here/cli_runner.py" "$here/fixtures/pass.cases.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass fixture: exit 0 (correct)"; else echo "pass fixture: FAIL (expected 0)"; fail=1; fi

python3 "$here/cli_runner.py" "$here/fixtures/fail.cases.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail fixture: exit 1 (correct - failure caught)"; else echo "fail fixture: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "cli runner self-test: pass"; else echo "cli runner self-test: FAIL"; fi
exit $fail
