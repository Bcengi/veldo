# VELDO-0213 host verification

Implementation commit: d84c8e378eb6f4c8495a7eb14569802cc126d498.

The race was confirmed at the original control_launch.py lines 1861 to 1864:
write and flush preceded wrote_prompt. Terminal._line in
.veldo/control_engine_claude.py:1818 classified the concurrent one-turn result
as a probe while prompt_written was false. The helper now marks before write;
the input_failed handler and configuration_stop exit path remain intact.

Local evidence: `python3 proof/VELDO-0213/local_check.py` passed five baseline
assertions. The registered prompt213-mark-after-write replacement failed exactly
the completion assertion with missing_result. The registered
role127-probe-is-terminal replacement failed both probe assertions. The existing
probe and write-failure mutation anchors still match both production copies.
See local_checks.json. These are synchronous Python checks using the suite's
exact row function and production modules, with defective modules only in memory.
They are not full suite runs or mutation-stage results.

The spec validator, Python syntax checks, and equality of the two production
copies passed. No systemd suite, mutation dispatcher or repository gate ran here.
The sandbox cannot start the systemd user manager. AC2's full receiver failure
check and integration proof remain pending. No passing gate stamp is claimed.

Run the following block from this checkout on the host with its user manager
available. It runs suites one at a time, suite 106 ten times while sixteen Python
processes consume CPU, then the new mutation case and both existing guard cases.
Every command log stays in a file. Successful selected suites return 2, so each
run also requires the partial summary with zero failures. Mutations return 0.
The commands construct their option prefix in Python.

```bash
python3 - <<'PY' > proof/VELDO-0213/host-driver.log 2>&1
import json
from pathlib import Path
import re
import subprocess

out = Path('proof/VELDO-0213/host')
out.mkdir(exist_ok=True)
option = chr(45) * 2
results = []

def run(label, argv, expected, summary):
    path = out / (label + '.log')
    with path.open('w') as log:
        done = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT)
    text = path.read_text()
    ok = done.returncode == expected and re.search(summary, text) is not None
    results.append({'label': label, 'argv': argv, 'returncode': done.returncode,
                    'passed': ok, 'log': str(path)})
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')

def suite(label, name):
    run(label, ['python3', 'scripts/selftest.py', option + 'suite', name], 2,
        r'selftest \(PARTIAL, \d+ of \d+ suites\): [1-9]\d* passed, 0 failed in ')

suite('suite80', '80_veldo_0155_claude_baseline')
suite('suite86', '86_veldo_0127_agent_configuration')
busy = []
try:
    for index in range(16):
        busy.append(subprocess.Popen(['python3', '-c', 'while True: pass'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for number in range(1, 11):
        assert all(process.poll() is None for process in busy)
        suite('suite106-load-%02d' % number, '106_veldo_0185_dispatch_setup')
        assert all(process.poll() is None for process in busy)
finally:
    for process in busy:
        process.terminate()
    for process in busy:
        process.wait()

for name in ('prompt213-mark-after-write', 'role127-probe-is-terminal',
             'role127-prompt-write-failure-swallowed'):
    run(name, ['python3', 'scripts/check_teeth_mutations.py', option + 'case', name,
               option + 'jobs', '1', option + 'worker-log-dir', str(out / (name + '-workers')),
               option + 'diff-dir', str(out / (name + '-diffs'))], 0, r'mutations: passed ')
assert all(result['passed'] for result in results), 'See host/results.json and failed command logs'
print('All requested host checks passed; repository gate and independent review remain separate')
PY
tail -5 proof/VELDO-0213/host-driver.log
```

The reviewer runs the repository gate outside this agent run and records the
stamp from the checkout it verifies. The spec stays ready pending that proof
and independent review.
