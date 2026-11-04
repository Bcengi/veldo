"""VELDO-0177: apply each spec falsifier and guard (the finding 177 mutation cases) to the checkout's .veldo copy,
run its suite, keep the suite's rows, and restore the module byte for byte. Run from the repository root:

    python3 proof/VELDO-0177/falsify.py > proof/VELDO-0177/falsifiers.txt
"""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
for case in [c for c in teeth.cases() if c['finding'] == 177]:
    path = ROOT / '.veldo' / case['module']
    before = path.read_bytes()
    print('== %s: %s, %d edit(s) (rows %s)' % (case['name'], case['module'], len(teeth.edits(case)),
                                              ', '.join(case['rows'])), flush=True)
    for old, new in teeth.edits(case):
        print('   %r -> %r' % (old.strip(), new.strip()))
    try:
        path.write_bytes(teeth.mutate(before, case))
        done = subprocess.run([sys.executable, 'scripts/selftest.py', '-' * 2 + 'suite', case['suite'][:-3]],
                              cwd=ROOT, capture_output=True, text=True)
    finally:
        path.write_bytes(before)
    for line in done.stdout.splitlines():
        if 'VELDO-0177' in line or case['suite'][:-3] + ' ' in line:
            print(line)
    print('restored: %s' % (path.read_bytes() == before), flush=True)
