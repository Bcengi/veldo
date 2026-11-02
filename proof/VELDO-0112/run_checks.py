"""Ticket checks and the three edited transport suites only; invoke under flock."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('v112_drive', HERE / 'drive.py')
drive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drive)

baseline = drive.run(ROOT)
(HERE / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
if not all(baseline['rows'].values()):
    raise SystemExit('baseline is red; no falsifiers run')
print('Baseline: all three criteria green', flush=True)
drive.main()
selected = ('47_veldo_0107_ipc', '48_veldo_0108_relay', '49_veldo_0109_unavailable',
            '113_veldo_0112_registered_clients')
argv = [sys.executable, '-B', str(ROOT / 'scripts/selftest.py')]
for suite in selected:
    argv += ['-' * 2 + 'suite', suite]
result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
(HERE / 'selected-suites.log').write_text(result.stdout + result.stderr)
match = re.search(r'selftest \(PARTIAL, 4 of \d+ suites\): (\d+) passed, (\d+) failed', result.stdout)
summary = dict(suites=selected, exit_code=result.returncode,
               passed=int(match[1]) if match else None, failed=int(match[2]) if match else None,
               full_gate_run=False)
(HERE / 'selected-suites.json').write_text(json.dumps(summary, indent=2) + '\n')
if not match or int(match[2]) or result.returncode != 2:
    raise SystemExit('selected suites failed; inspect selected-suites.log')
print('Selected suites: ' + match[1] + ' passed, zero failed; partial-run exit 2', flush=True)
