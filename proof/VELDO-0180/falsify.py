"""VELDO-0180: apply each registered case's exact edits (scripts/check_teeth_mutations.py, finding 180) to the
checkout's .veldo module, run suite 136 alone, and restore the module byte for byte.

Run from the repository root: python3 proof/VELDO-0180/falsify.py [case ...]
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SUITE = '136_veldo_0180_conversation_projects'

spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:1] + sys.argv[1:]
spec.loader.exec_module(teeth)
cases = [c for c in teeth.cases() if c['finding'] == 180]
wanted = sys.argv[1:] or [c['name'] for c in cases]
for case in [c for c in cases if c['name'] in wanted]:
    path = ROOT / '.veldo' / case['module']
    original = path.read_bytes()
    text = original.decode()
    for old, new in teeth.edits(case):
        assert text.count(old) == 1, (case['name'], old)
        text = text.replace(old, new)
    path.write_text(text)
    try:
        run = subprocess.run(['python3', 'scripts/selftest.py', '--suite', SUITE], cwd=ROOT, capture_output=True,
                             text=True, timeout=600)
    finally:
        path.write_bytes(original)
    output = run.stdout + run.stderr
    failed = sorted(set(re.findall(r'SELFTEST FAIL: (VELDO-0180 \S+)', output)))
    details = [line for line in output.splitlines() if 'VELDO-0180 detail' in line or 'Traceback' in line
               or line.startswith('  File') or 'Error' in line][:40]
    print('case:', case['name'], '(%s)' % case['module'])
    print('  target rows:', case['rows'])
    print('  failed rows:', failed)
    print('  killed at its target:', all('VELDO-0180 ' + r in failed for r in case['rows']))
    for line in details:
        print('   ', line[:400])
    print('  restored:', hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(original).hexdigest())
