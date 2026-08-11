#!/usr/bin/env bash
# The streaming runner's own regression, fully self-contained: it drives the
# runner over both fixtures and requires the well-formed stream to pass (exit 0,
# framing + contiguous sequence + terminal all hold) and the malformed stream to
# fail (exit 1, the dropped chunk caught as a sequence gap). Standard library
# only, so a reviewer reruns it with no setup. The same control logic is also
# unit-tested in scripts/selftest.py, which is the check the every-commit gate
# runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/veldo_streaming_runner.py" "$here/fixtures/pass.stream.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "well-formed stream: exit 0 (correct - framing, sequence, terminal hold)"; else echo "well-formed stream: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_streaming_runner.py" "$here/fixtures/fail.stream.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "malformed stream: exit 1 (correct - dropped chunk caught)"; else echo "malformed stream: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "streaming runner self-test: pass"; else echo "streaming runner self-test: FAIL"; fi
exit $fail
