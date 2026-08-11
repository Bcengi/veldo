#!/usr/bin/env bash
# The sandbox isolation runner's own regression, fully self-contained: it drives
# the runner over both fixtures with the in-process FakeContainerDriver
# (VELDO_SANDBOX_DRIVER=fake, so no container runtime is required on this host)
# and requires the confined journey to pass (exit 0, every escape attempt
# denied) and the breached journey to fail (exit 1, the over-broad root mount
# that lets a host secret leak caught as a CONFINEMENT BREACH). Standard library
# only, so a reviewer reruns it with no setup. The same control logic is also
# unit-tested in scripts/selftest.py, which is the check the every-commit gate
# runs. A live run against a real container needs docker or podman on PATH; this
# reference regression proves the runner's confinement grading without one.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
export VELDO_SANDBOX_DRIVER=fake

fail=0
python3 "$here/sandbox_isolation_runner.py" "$here/fixtures/pass.sandbox.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "confined journey: exit 0 (correct - every escape attempt denied)"; else echo "confined journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/sandbox_isolation_runner.py" "$here/fixtures/fail.sandbox.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "breached journey: exit 1 (correct - confinement breach caught)"; else echo "breached journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "sandbox isolation runner self-test: pass"; else echo "sandbox isolation runner self-test: FAIL"; fi
exit $fail
