#!/usr/bin/env bash
# The LLM/eval runner's own regression, fully self-contained: it drives the
# runner over both fixtures with the deterministic fake provider and requires the
# passing fixture to pass (exit 0, new prompt holds) and the deliberately-failing
# fixture to fail (exit 1, the prompt-change regression caught). Standard library
# only, so a reviewer reruns it with no setup. The same control logic is also
# unit-tested in scripts/selftest.py, which is the check the every-commit gate
# runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/veldo_llm_runner.py" "$here/fixtures/pass.journey.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass eval: exit 0 (correct - new prompt holds)"; else echo "pass eval: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_llm_runner.py" "$here/fixtures/fail.journey.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail eval: exit 1 (correct - prompt-change regression caught)"; else echo "fail eval: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "llm runner self-test: pass"; else echo "llm runner self-test: FAIL"; fi
exit $fail
