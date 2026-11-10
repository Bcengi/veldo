"""Run the requested suites sequentially in user scopes and retain small summaries."""

from collections import deque
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[2]
proof = Path(__file__).resolve().parent
marker = next((line for line in Path('/home/dmitry/projects/myday/research/lock-queue/runner.log')
               .read_text().splitlines() if line.startswith('78a-landing-c-gate9 rc=')), None)
if marker is None:
    raise SystemExit('Gate 9 completion marker is absent; run wait_for_gate.py first')

names = (
    '128_veldo_0254_confined_runner',
    '127_veldo_0254_secret_scan',
    '102_veldo_0210_agent_profile_runtime',
    '47_veldo_0107_ipc',
    '86_veldo_0189_engine_upgrade',
)
with (proof / 'suite-results.txt').open('x') as summary:
    def record(line):
        summary.write(line + '\n')
        summary.flush()
        print(line, flush=True)

    record(marker)
    for name in names:
        for mode in ('single', 'repeat'):
            argv = (['python3', 'scripts/selftest.py', '--suite', name] if mode == 'single' else
                    ['python3', str(proof / 'repeat_suite.py'), name])
            command = ['systemd-run', '--user', '--scope', '-p', 'MemoryMax=10G', *argv]
            record('Running %s %s in a user scope with MemoryMax=10G' % (name, mode))
            tail = deque(maxlen=25)
            completed = False
            with subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True) as process:
                for line in process.stdout:
                    line = line.rstrip()[:1500]
                    tail.append(line)
                    if line.startswith('selftest (PARTIAL,') and ', 0 failed in ' in line:
                        completed = True
                    if (name in line and 'passed' in line or line.startswith(('selftest (PARTIAL,',
                            'Round 10 repeat:', 'Remaining thread:', 'Running scope as unit:'))
                            or 'FAIL' in line or 'Traceback' in line):
                        record(line)
                status = process.wait()
            record('%s %s rc=%d' % (name, mode, status))
            if status != 2 or not completed:
                record('Stopped after an unexpected result. Last output:')
                for line in tail:
                    record(line)
                sys.exit(status or 1)
