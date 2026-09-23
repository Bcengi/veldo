import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

root = Path.cwd()
spec = importlib.util.spec_from_file_location('teeth', root / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
cases = [case for case in teeth.cases() if case['finding'] == 46]
results = []
start = time.monotonic()
with tempfile.TemporaryDirectory(prefix='v46-measure-') as temp:
    # Two normal executions for unit + first-use integration, then the gate's
    # shared baseline/noop controls and each registered mutant (serial upper bound).
    jobs = [(label, cases[0], 'baseline') for label in ('unit', 'first-use-integration', 'mutation-baseline')]
    jobs.append(('mutation-noop', cases[0], 'noop'))
    jobs.extend((case['name'], case, 'mutant') for case in cases)
    for label, case, mode in jobs:
        began = time.monotonic()
        prepared = teeth.materialize(case, mode, Path(temp) / label)
        command = [sys.executable, '-B', str(root / 'scripts/check_teeth_mutations.py'), '--worker', case['name']]
        if prepared['mutant']:
            command += ['--mutant', str(prepared['mutant'])]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=15)
        assert proc.returncode == 0, proc.stderr
        obs = json.loads(proc.stdout)
        if mode != 'mutant':
            assert not obs['failed_rows'], obs
        else:
            assert all(obs['targets'][row] == [False] for row in case['rows']), obs
        results.append(dict(label=label, mode=mode, seconds=time.monotonic() - began,
                            old_digest=prepared['old_digest'], new_digest=prepared['new_digest'],
                            observations=[row for row in obs['observations'] if row[0].startswith('VELDO-0046')],
                            targets=obs['targets']))
value = dict(description='Measured serial cost of unit, first-use integration, shared baseline/noop and six mutants; includes child startup and shared preamble.',
             total_seconds=time.monotonic() - start, results=results)
Path('/tmp/veldo-0046-measure.json').write_text(json.dumps(value, indent=2) + '\n')
print('Added suite and mutation work, serial seconds: %.3f' % value['total_seconds'])
assert value['total_seconds'] <= 60
