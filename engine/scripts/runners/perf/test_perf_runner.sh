#!/usr/bin/env bash
# The performance/load runner's own regression, fully self-contained: it drives
# the runner over both fixtures and requires the passing fixture to pass (exit 0,
# budgets hold) and the deliberately-failing fixture to fail (exit 1, the zero
# error budget breached). The outcomes are deterministic by construction: the
# passing fixture pairs a fast workload with generous budgets, and the failing
# fixture breaches a zero error budget with an index-chosen failure fraction, so
# neither depends on wall-clock timing. Standard library only. The same control
# logic is also unit-tested in scripts/selftest.py, which the gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/veldo_perf_runner.py" "$here/fixtures/pass.journey.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass load: exit 0 (correct - budgets hold)"; else echo "pass load: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_perf_runner.py" "$here/fixtures/fail.journey.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail load: exit 1 (correct - error budget breached under load)"; else echo "fail load: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "perf runner self-test: pass"; else echo "perf runner self-test: FAIL"; fi
exit $fail
