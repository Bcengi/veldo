"""VELDO-0231: apply each spec falsifier (the finding 231 mutation cases) to the checkout's .veldo copy, run suite
127, keep its rows, and restore the module byte for byte. Run from the repository root:

    python3 proof/VELDO-0231/falsify.py > proof/VELDO-0231/falsifiers.txt
"""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
for case in [c for c in teeth.cases() if c['finding'] == 231]:
    path = ROOT / '.veldo' / case['module']
    before = path.read_bytes()
    assert before.count(case['old'].encode()) == 1, case['name']
    print('== %s: %s, %r -> %r (rows %s)' % (case['name'], case['module'], case['old'].strip(), case['new'].strip(),
                                            ', '.join(case['rows'])), flush=True)
    try:
        path.write_bytes(before.replace(case['old'].encode(), case['new'].encode()))
        done = subprocess.run([sys.executable, 'scripts/selftest.py', '-' * 2 + 'suite', '127_veldo_0231_run_flags'],
                              cwd=ROOT, capture_output=True, text=True)
    finally:
        path.write_bytes(before)
    for line in done.stdout.splitlines():
        if 'VELDO-0231' in line or '127_veldo_0231_run_flags ' in line:
            print(line)
    print('restored: %s' % (path.read_bytes() == before), flush=True)
