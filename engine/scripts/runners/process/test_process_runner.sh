#!/usr/bin/env bash
# The process lifecycle runner's own regression, fully self-contained: it drives
# the runner over both fixtures and requires the well-behaved sleeper to pass
# (exit 0, spawn + graceful SIGTERM exit + fresh respawn pid + clean kill-tree)
# and the misbehaving target to fail (exit 1, SIGTERM ignored and a setsid-escaped
# child left orphaned). Both fixtures drive python3, so a reviewer reruns it with
# nothing to install. The same control logic is also unit-tested in
# scripts/selftest.py over real short-lived subprocesses, which is the check the
# every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

python3 "$here/process_runner.py" "$here/fixtures/pass.lifecycle.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "well-behaved target: exit 0 (correct - spawn, signal, respawn, kill-tree hold)"; else echo "well-behaved target: FAIL (expected 0)"; fail=1; fi

python3 "$here/process_runner.py" "$here/fixtures/fail.lifecycle.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "misbehaving target: exit 1 (correct - ignored SIGTERM and leaked child caught)"; else echo "misbehaving target: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "process runner self-test: pass"; else echo "process runner self-test: FAIL"; fi
exit $fail
