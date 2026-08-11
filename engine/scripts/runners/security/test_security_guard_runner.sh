#!/usr/bin/env bash
# The security-guard runner's own regression, fully self-contained: it drives the
# runner over both fixtures and requires the correctly-labeled corpus to pass
# (exit 0, every hostile input blocked and every benign input allowed) and the
# holed corpus to fail (exit 1, the metadata endpoint that slips through an
# allowlist hole caught as a SECURITY BYPASS). Standard library only, so a
# reviewer reruns it with no setup. The same control logic is also unit-tested in
# scripts/selftest.py, which is the check the every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/security_guard_runner.py" "$here/fixtures/pass.security.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "correct corpus: exit 0 (correct - every input matched its label)"; else echo "correct corpus: FAIL (expected 0)"; fail=1; fi

python3 "$here/security_guard_runner.py" "$here/fixtures/fail.security.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "holed corpus: exit 1 (correct - bypass caught)"; else echo "holed corpus: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "security guard runner self-test: pass"; else echo "security guard runner self-test: FAIL"; fi
exit $fail
