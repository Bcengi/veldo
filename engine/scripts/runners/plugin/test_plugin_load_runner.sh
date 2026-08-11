#!/usr/bin/env bash
# The plugin-load runner's own regression, fully self-contained: it drives the
# runner over both fixtures and requires the safe-loader corpus to pass (exit 0,
# a well-formed archive loads and every malicious archive is rejected with
# nothing escaping) and the naive-loader corpus to fail (exit 1, the naive loader
# lets a ../ entry escape the target directory and the runner catches it as a
# PLUGIN ESCAPE). No network and no ports: every archive is built into a real zip
# in a throwaway temp directory. Standard library only, so a reviewer reruns it
# with no setup. The same control logic is also unit-tested in scripts/selftest.py,
# which is the check the every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/plugin_load_runner.py" "$here/fixtures/pass.plugin.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "safe corpus: exit 0 (correct - good archive loads, malicious archives rejected, nothing escaped)"; else echo "safe corpus: FAIL (expected 0)"; fail=1; fi

out="$(python3 "$here/plugin_load_runner.py" "$here/fixtures/fail.plugin.json" 2>&1)"
rc=$?
if [ "$rc" -eq 1 ]; then echo "naive corpus: exit 1 (correct - escape caught)"; else echo "naive corpus: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi
if echo "$out" | grep -q "PLUGIN ESCAPE"; then echo "naive corpus: PLUGIN ESCAPE named (correct)"; else echo "naive corpus: FAIL (expected a PLUGIN ESCAPE line naming the escaped path)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "plugin load runner self-test: pass"; else echo "plugin load runner self-test: FAIL"; fi
exit $fail
