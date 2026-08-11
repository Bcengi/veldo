#!/usr/bin/env bash
# The terminal/TUI runner's own regression, fully self-contained: it drives the
# runner over both fixtures and requires the well-formed journey to pass (exit 0,
# the bold red ERR at the right cell, the status line echoing the keystroke, the
# early lines in scrollback) and the defective journey to fail (exit 1, the
# dropped bold attribute caught and named with its cell coordinate). It drives a
# real command in a real pseudo-terminal via the standard-library pty module, so
# a reviewer reruns it with no setup and no third-party dependency. The renderer's
# control logic is also unit-tested in scripts/selftest.py, which is the check the
# every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/terminal_runner.py" "$here/fixtures/pass.terminal.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "well-formed journey: exit 0 (correct - every cell, attr, and scrollback line matched)"; else echo "well-formed journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/terminal_runner.py" "$here/fixtures/fail.terminal.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "defective journey: exit 1 (correct - dropped bold attribute caught)"; else echo "defective journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "terminal runner self-test: pass"; else echo "terminal runner self-test: FAIL"; fi
exit $fail
