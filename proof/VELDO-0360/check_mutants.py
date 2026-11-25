#!/usr/bin/env python3
"""Bounded falsifiers through the registry's materializer and observer; no gate or load."""
import difflib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
cases = [case for case in teeth.cases() if case['finding'] == 360]
source = ROOT / 'scripts/gate_schedule.py'
results = []
with tempfile.TemporaryDirectory(prefix='v360-mutants-') as temporary:
    top = Path(temporary)
    control = teeth.worker(cases[0])
    assert not control['failed_rows'], control
    print('baseline: %d rows, zero failures' % control['count'], flush=True)
    for case in cases:
        noop = teeth.materialize(case, 'noop', top / (case['name'] + '-noop'))
        observed = teeth.worker(case, str(noop['mutant']))
        assert not observed['failed_rows'], (case['name'], 'noop', observed)
        prepared = teeth.materialize(case, 'mutant', top / case['name'])
        mutated = prepared['mutant'].read_text()
        diff = ''.join(difflib.unified_diff(source.read_text().splitlines(True), mutated.splitlines(True),
                                         fromfile='scripts/gate_schedule.py', tofile=case['name']))
        assert diff and prepared['old_digest'] != prepared['new_digest']
        (Path(__file__).parent / (case['name'] + '.diff')).write_text(diff)
        observed = teeth.worker(case, str(prepared['mutant']))
        assert all(observed['targets'][r] and not all(observed['targets'][r]) for r in case['rows']), (
            case['name'], observed)
        results.append(dict(case=case['name'], rows=case['rows'], rejected=True,
                            original_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest']))
        print(case['name'] + ': noop green; named row red', flush=True)
(Path(__file__).parent / 'mutants.json').write_text(json.dumps(results, indent=2) + '\n')
print('%d/%d mutants rejected' % (len(results), len(cases)), flush=True)
