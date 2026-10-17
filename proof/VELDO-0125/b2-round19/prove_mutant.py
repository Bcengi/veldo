"""Run one explicitly named suite, optionally applying one registered mutant.

No mutation driver is executed. Original production bytes are restored in finally.
Every invocation creates new immutable logs, file snapshots and a run receipt.
"""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from audit_anchors import definitions, ROOT, HERE

NAMES = {'retire-no-sweep-on-wait', 'loop154-periodic-pass'}
name, mode = sys.argv[1:]
assert name in NAMES and mode in ('mutant', 'baseline')
registry = definitions('check_teeth_mutations.py')
case = next(c for c in registry['cases']() if c['name'] == name)
source = ROOT / '.veldo' / case['module']
before = source.read_bytes()
assert before == subprocess.check_output(['git', 'show', 'HEAD:' + str(source.relative_to(ROOT))], cwd=ROOT)
mutated = registry['mutate'](before, case)
assert mutated != before
compile(mutated, str(source), 'exec')
folder = HERE / name / mode
folder.mkdir(parents=True, exist_ok=False)
applied = mutated if mode == 'mutant' else before
(folder / 'materialized.txt').write_bytes(applied)
(folder / 'mutation.patch').write_text(''.join(difflib.unified_diff(
    before.decode().splitlines(keepends=True), applied.decode().splitlines(keepends=True),
    fromfile=str(source.relative_to(ROOT)), tofile=str(source.relative_to(ROOT)))))
command = ['python3', 'scripts/selftest.py', '--suite', case['suite'].removesuffix('.py')]
receipt = dict(name=name, mode=mode, command=command, target_rows=case['rows'],
               head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               source=str(source.relative_to(ROOT)),
               original_sha256=hashlib.sha256(before).hexdigest(),
               applied_sha256=hashlib.sha256(applied).hexdigest())
started = time.time()
try:
    source.write_bytes(applied)
    assert source.read_bytes() == (folder / 'materialized.txt').read_bytes()
    with (folder / 'suite.log').open('x') as log:
        receipt['returncode'] = subprocess.run(command, cwd=ROOT, stdout=log,
                                              stderr=subprocess.STDOUT).returncode
finally:
    source.write_bytes(before)
    receipt['restored'] = source.read_bytes() == before
    receipt['elapsed_seconds'] = time.time() - started
    receipt['log_sha256'] = hashlib.sha256((folder / 'suite.log').read_bytes()).hexdigest()
    (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
