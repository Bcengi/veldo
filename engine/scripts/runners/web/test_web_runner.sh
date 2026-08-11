#!/usr/bin/env bash
# The web runner's own regression: the passing journey must pass (exit 0) and
# the deliberately-broken journey must fail (exit 1) with the failure caught.
# Run on demand and as the runner's proof; NOT wired into the every-commit
# gate, because launching a real browser on every commit is heavy and this
# repository ships the runner as a reference for repos that DO have a UI.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

"$here/run.sh" "$here/fixtures/pass.journey.json" /tmp/veldo-web-pass >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass journey: exit 0 (correct)"; else echo "pass journey: FAIL (expected 0)"; fail=1; fi

"$here/run.sh" "$here/fixtures/fail.journey.json" /tmp/veldo-web-fail >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail journey: exit 1 (correct - failure caught)"; else echo "fail journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "web runner self-test: pass"; else echo "web runner self-test: FAIL"; fi
exit $fail
