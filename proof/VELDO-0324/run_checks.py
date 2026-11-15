"""Small targeted test receipts. The lead owns the full verification gate."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITES = ('103_veldo_0211_borrowed_login', '133_veldo_0326_space_principals',
          '138_veldo_0300_space_remove', '139_veldo_0301_space_signal',
          '140_veldo_0345_space_keep', '153_veldo_0302_space_creators', '154_veldo_0324_batch_sandbox')
FAST = (['python3', '.veldo/validate.py', 'all'], ['bash', 'scripts/check_docs.sh'],
        ['bash', 'scripts/check_template_sync.sh'], ['bash', 'scripts/check_lint.sh'],
        ['bash', 'scripts/check_generated.sh'], ['python3', 'scripts/check_git_boundary.py'])
mode = sys.argv[1]
commands = ([['python3', 'scripts/selftest.py', '--suite', suite] for suite in SUITES]
            if mode == 'tests' else FAST)
rows = []
for command in commands:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if mode == 'tests':
        summary = next((line for line in output.splitlines() if line.startswith('selftest (PARTIAL,')), '')
        passed = bool(re.search(r'\b0 failed\b', summary)) and result.returncode == 2
        detail = [] if passed else [line for line in output.splitlines() if 'FAIL' in line][-8:]
    else:
        passed = result.returncode == 0
        summary = '\n'.join(output.splitlines()[-5:])
        detail = [] if passed else output.splitlines()[-15:]
    row = {'command': ' '.join(command), 'exit': result.returncode, 'passed': passed,
           'summary': summary, 'detail': detail}
    rows.append(row)
    print(json.dumps(row), flush=True)
    (HERE / (mode + '.json')).write_text(json.dumps(rows, indent=1) + '\n')
assert all(row['passed'] for row in rows), 'one or more targeted checks failed'
