"""Single suite 115 only: its registered mutants and controls, run sequentially."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
cases = [case for case in teeth.cases() if case['finding'] == 219]
assert len(cases) == 8
assert {case['suite'] for case in cases} == {'115_veldo_0219_measured_admission.py'}
paths = ['scripts/' + name for name in ('gate_schedule.py', 'gate_graph.json', 'check_gate_mutations.py',
    'mutation_ownership.py', 'reuse_worker.py', 'check_teeth_mutations.py',
    'suites/115_veldo_0219_measured_admission.py', 'suites/104_veldo_0210_mutation_workers.py')]
paths += ['engine/scripts/' + name for name in ('gate_schedule.py', 'check_gate_mutations.py',
    'mutation_ownership.py', 'reuse_worker.py')]
paths += ['proof/VELDO-0219/' + name for name in ('round2/check.py', 'round3/check.py', 'round3/falsifiers.py')]
sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
evidence = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                sources=sources, runs=[], passed=False)
for case in cases:
    for mode in ('mutant', 'baseline', 'noop'):
        with tempfile.TemporaryDirectory(prefix='v219-round3-falsifier-') as temporary:
            made = teeth.materialize(case, mode, temporary, ROOT)
            result = teeth.worker(case, str(made['mutant']) if made['mutant'] else None)
        rows = {name.split()[-1]: ok for name, ok in result['observations'] if name.startswith('VELDO-0219 ')}
        failed = [name for name, ok in rows.items() if not ok]
        evidence['runs'].append(dict(case=case['name'], mode=mode, rows=rows, failed=failed,
            old_digest=made['old_digest'], new_digest=made['new_digest']))
        (OUT / 'falsifiers.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(case['name'], mode, failed, flush=True)
        assert rows and (all(rows.get(row) is False for row in case['rows'])
                         if mode == 'mutant' else not failed), result
assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value for path, value in sources.items())
evidence['passed'] = True
(OUT / 'falsifiers.json').write_text(json.dumps(evidence, indent=2) + '\n')
