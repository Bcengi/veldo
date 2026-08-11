#!/usr/bin/env bash
# The MCP runner's own regression, fully self-contained: it drives the runner
# over both fixtures against the bundled fake MCP server (spawned as a real
# subprocess and spoken to as newline-delimited JSON-RPC 2.0 over stdio, the MCP
# stdio framing) and requires the passing journey to pass (exit 0: tool listing
# matches, valid and proxied tool calls return their expected results, and an
# unknown tool is correctly observed as a JSON-RPC error) and the deliberately
# failing journey to fail (exit 1: a step expects a result from a tool the server
# does not expose, caught and named). The transport is stdio (a subprocess over
# pipes), so no port is bound. Standard library only, so a reviewer reruns it with
# no setup. The same control logic is also unit-tested in scripts/selftest.py,
# which is the check the every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

fail=0
python3 "$here/mcp_runner.py" "$here/fixtures/pass.mcp.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "passing journey: exit 0 (correct - contract held over real stdio transport)"; else echo "passing journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/mcp_runner.py" "$here/fixtures/fail.mcp.json" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "failing journey: exit 1 (correct - bad tool call caught)"; else echo "failing journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "mcp runner self-test: pass"; else echo "mcp runner self-test: FAIL"; fi
exit $fail
