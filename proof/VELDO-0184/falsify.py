#!/usr/bin/env python3
"""VELDO-0184: apply each spec falsifier to the checkout's .veldo copy, run suite 131, keep the row's own words, restore.

Run: python3 proof/VELDO-0184/falsify.py > proof/VELDO-0184/falsifiers.txt
The edits are the registered mutation cases memory184-directory-unset, memory184-no-writable-root and
memory184-no-index-digest (scripts/check_teeth_mutations.py). Each file is restored byte for byte after its run.
"""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
FALSIFIERS = (('AC1', 'memory184-directory-unset', 'AC1/memory-path'),
              ('AC2', 'memory184-no-writable-root', 'AC2/write'),
              ('AC3', 'memory184-no-index-digest', 'AC3/loaded-at-launch'))
cases = {c['name']: c for c in teeth.cases()}
for criterion, name, row in FALSIFIERS:
    case = cases[name]
    path = ROOT / '.veldo' / case['module']
    original = path.read_bytes()
    try:
        path.write_bytes(teeth.mutate(original, case))
        done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '131_veldo_0184_file_memory'],
                              cwd=ROOT, capture_output=True, text=True, timeout=600)
    finally:
        path.write_bytes(original)
    lines = done.stdout.splitlines() + done.stderr.splitlines()
    print('%s falsifier (%s): %s %r -> %r' % (criterion, name, case['module'], case['old'].strip(), case['new'].strip()))
    for line in lines:
        if 'VELDO-0184 detail: ' + row in line or 'SELFTEST FAIL: VELDO-0184 ' + row in line:
            print('  ' + line.strip())
    print('  failed rows: ' + ', '.join(l.split('VELDO-0184 ')[1] for l in lines if l.startswith('  SELFTEST FAIL: VELDO-0184')))
    print('  restored: %s' % (path.read_bytes() == original))
    print()
