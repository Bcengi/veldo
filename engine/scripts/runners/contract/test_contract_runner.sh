#!/usr/bin/env bash
# The contract/schema drift runner's own regression, fully self-contained: it
# drives the runner over both fixtures and requires the conforming payload to
# pass (exit 0, no breaking drift against golden v1) and the drifted payload to
# fail (exit 1, a removed field, a type change, and a strict addition all named).
# Standard library only, so a reviewer reruns it with no setup. The same control
# logic is also unit-tested in scripts/selftest.py, which is the check the
# every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/veldo_contract_runner.py" "$here/fixtures/pass.contract.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "conforming payload: exit 0 (correct - no breaking drift)"; else echo "conforming payload: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_contract_runner.py" "$here/fixtures/fail.contract.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "drifted payload: exit 1 (correct - drift caught)"; else echo "drifted payload: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "contract runner self-test: pass"; else echo "contract runner self-test: FAIL"; fi
exit $fail
