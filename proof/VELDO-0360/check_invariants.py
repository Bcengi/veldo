#!/usr/bin/env python3
"""Read-only final invariants: exact mutation anchors and unchanged protected declarations."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
teeth, review = module('check_teeth_mutations'), module('check_review_mutations')
cases = teeth.cases() + review.cases()
stale = []
for case in cases:
    path = ROOT / ('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')) / case['module']
    try:
        teeth.mutate(path.read_bytes(), case)
    except (OSError, RuntimeError) as error:
        stale.append((case['name'], str(error)))
print('stale-mutant scan: %d of %d' % (len(stale), len(cases)), stale)
assert not stale
for name in ('gate_unconfined.json', 'verify.sh'):
    path = 'scripts/' + name
    assert (ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', '40301b937:' + path], cwd=ROOT)
    print(path + ': unchanged')
assert (ROOT / 'scripts/gate_schedule.py').read_bytes() == (ROOT / 'engine/scripts/gate_schedule.py').read_bytes()
print('scheduler mirror: identical')
print('scheduler sha256:', hashlib.sha256((ROOT / 'scripts/gate_schedule.py').read_bytes()).hexdigest())
