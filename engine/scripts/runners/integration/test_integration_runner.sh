#!/usr/bin/env bash
# The integration runner's own regression, fully self-contained: it stands up
# the stdlib mock server (fixtures/mock_server.py) on a free port, drives the
# runner against it, and requires the passing fixture to pass (exit 0, the
# response conforms) and the deliberately-failing fixture to fail (exit 1, the
# contract violation caught). Standard library only, so a reviewer reruns it
# with no setup. The same control logic is also unit-tested in
# scripts/selftest.py against an in-process server, which is the check the
# every-commit gate runs.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
port="${PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')}"
base="http://127.0.0.1:${port}"

python3 "$here/fixtures/mock_server.py" "$port" >/dev/null 2>&1 &
srv=$!
trap 'kill "$srv" 2>/dev/null' EXIT

# wait for the server to accept connections
if ! python3 - "$port" <<'PY'
import socket, sys, time
port = int(sys.argv[1])
for _ in range(50):
    s = socket.socket(); s.settimeout(0.2)
    if s.connect_ex(("127.0.0.1", port)) == 0:
        s.close(); sys.exit(0)
    s.close(); time.sleep(0.1)
sys.exit(1)
PY
then
  echo "integration runner self-test: FAIL (mock server did not come up)"; exit 1
fi

fail=0
python3 "$here/veldo_integration_runner.py" "$here/fixtures/pass.journey.json" "$base" >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass journey: exit 0 (correct - the response conforms)"; else echo "pass journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_integration_runner.py" "$here/fixtures/fail.journey.json" "$base" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail journey: exit 1 (correct - the contract violation caught)"; else echo "fail journey: FAIL (expected 1; a rubber-stamp runner is worse than none)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "integration runner self-test: pass"; else echo "integration runner self-test: FAIL"; fi
exit $fail
