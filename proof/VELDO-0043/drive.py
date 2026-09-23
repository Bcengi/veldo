#!/usr/bin/env python3
"""Reproduce proof/VELDO-0043/mutations.json and observations.json.

  python3 -B proof/VELDO-0043/drive.py

For the unmutated suite and for each registered finding-43 mutation, run suite 59 in this
process the way scripts/check_teeth_mutations.py does (the production anchor replaced by a
temporary mutated copy) and record the rows that went red and the observation that explains why.
Needs the locked LangGraph runtime installed (python3 .veldo/control_graph_install.py).
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)


def run(case=None, mutant=None):
    rows = []
    ns = {'__file__': str(ROOT / 'scripts/suites/shared.py')}
    source = (ROOT / 'scripts/suites/59_veldo_0043_graph.py').read_text()
    if mutant:
        source = source.replace('ROOT / ".veldo" / "' + case['module'] + '"',
                                '__import__("pathlib").Path(' + repr(str(mutant)) + ')')
    with contextlib.redirect_stdout(io.StringIO()):
        exec((ROOT / 'scripts/suites/shared.py').read_text(), ns)
        ns['expect'] = lambda name, condition: rows.append((name.split(':', 1)[0], bool(condition)))
        exec(source, ns)
    return [name for name, ok in rows if not ok], ns['_s43_observations']


def why(observed):
    runtime = observed.get('runtime', {})
    return {
        'isolation_failed_entries': [
            {k: e.get(k) for k in ('entry', 'static_violations', 'refused_imports', 'exception', 'exit')}
            for e in observed['isolated']['verdict'].get('entries', []) if e['status'] != 'pass'],
        'start_without_runtime': observed['unavailable'],
        'foreign_object_answers': [f.get('failure', f) for f in runtime.get('foreign', [])],
        'store_unchanged_by_graph': runtime.get('store_unchanged_by_graph'),
        'store_probe_notes': (runtime.get('probe') or {}).get('notes'),
        'assertion_answers': {k: v.get('failure', v) for k, v in runtime.get('assertions', {}).items()},
        'untyped_proposal_answer': runtime.get('untyped'),
        'first_runner_audit': (runtime.get('audits') or [None])[0],
        'suspend_and_cancel_graphs_invoked': [(a or {}).get('invoked') for a in (runtime.get('audits') or [])[1:5:3]],
        'stub_label_as_evidence': runtime.get('stub_evidence'),
        'deep_answer': observed.get('deep_answer'),
        'closed_request': observed.get('closed_request'),
        'closed_response': observed.get('closed_response'),
        'proc_limit': runtime.get('proc_limit'),
        'stage_in_repository': runtime.get('stage_in_repository'),
    }


honest_red, honest = run()
assert not honest_red, honest_red
results = []
for case in [c for c in teeth.cases() if c['finding'] == 43]:
    with tempfile.TemporaryDirectory(prefix='drive-43-') as temporary:
        mutant = teeth.materialize(case, 'mutant', Path(temporary) / case['name'])['mutant']
        red, observed = run(case, mutant)
    results.append({'mutation': case['name'], 'module': case['module'], 'target_rows': case['rows'],
                    'red_rows': red, 'target_red': all(row in red for row in case['rows']),
                    'why': why(observed)})
(HERE / 'mutations.json').write_text(json.dumps(results, indent=1, sort_keys=True) + '\n')
(HERE / 'observations.json').write_text(json.dumps(honest, indent=1, sort_keys=True, default=list) + '\n')
print(json.dumps({'mutations': len(results), 'all_target_rows_red': all(r['target_red'] for r in results)}))
