#!/usr/bin/env bash
# The agent-loop runner's own regression, fully self-contained: it drives the
# runner over both fixtures with the deterministic fake step and requires the
# passing fixture to pass (exit 0, the right tools called in order with the right
# results) and the deliberately-failing fixture to fail (exit 1, a forbidden
# destructive tool invoked and the expected call sequence violated). Standard
# library only, so a reviewer reruns it with no setup. The same control logic is
# also unit-tested in scripts/selftest.py, which is the check the every-commit
# gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/veldo_agent_runner.py" "$here/fixtures/pass.journey.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass journey: exit 0 (correct - right tools, right order, right final)"; else echo "pass journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_agent_runner.py" "$here/fixtures/fail.journey.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail journey: exit 1 (correct - forbidden tool caught, sequence violated)"; else echo "fail journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "agent runner self-test: pass"; else echo "agent runner self-test: FAIL"; fi
exit $fail
