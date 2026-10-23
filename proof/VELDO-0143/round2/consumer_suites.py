"""VELDO-0143 round 2: focused suite runs on two trees, one after the other in the same sandbox, for the
evidence that a change leaves a suite as it was (or changes exactly the rows it names).

    python3 proof/VELDO-0143/round2/consumer_suites.py <base tree> <base label> <branch tree> <output.json> suite ...

passed is the selftest table count for the suite; failed_rows are its SELFTEST FAIL lines. Not a gate result.
"""
import json
from pathlib import Path
import re
import subprocess
import sys

base, label, branch, out, suites = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5:]


def run(tree, suite):
    done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite], cwd=tree, capture_output=True,
                          text=True, timeout=3600)
    text = done.stdout + done.stderr
    table = re.search(r'^\s+%s\s+(\d+) passed' % re.escape(suite), text, re.M)
    return {'passed': int(table.group(1)) if table else None,
            'failed_rows': sorted(line.strip()[len('SELFTEST FAIL: '):] for line in text.splitlines()
                                  if line.strip().startswith('SELFTEST FAIL: ')),
            'exit': done.returncode}


records = []
for suite in suites:
    before, after = run(base, suite), run(branch, suite)
    same = (before['passed'], before['failed_rows']) == (after['passed'], after['failed_rows'])
    records.append({'suite': suite, label: before, 'branch': after, 'same': same})
    print(suite, before['passed'], len(before['failed_rows']), after['passed'], len(after['failed_rows']),
          'same' if same else 'DIFFERENT', flush=True)
out.write_text(json.dumps({'base': label, 'suites': records}, indent=1, sort_keys=True) + '\n')
