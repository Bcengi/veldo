#!/usr/bin/env python3
"""Compare OFF legacy qualification and every original Session method with 68b1c4520."""
import ast
import copy
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '68b1c4520'


def qualification(source):
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'failed_condition')
    runs = next(n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'TRACED_RUNS' for t in n.targets))
    namespace = {'review_matches': lambda *args: True}
    exec(compile(ast.Module(body=[runs, function], type_ignores=[]), '<qualification>', 'exec'), namespace)
    session = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Session')
    methods = {n.name: ast.dump(n) for n in session.body if isinstance(n, ast.FunctionDef) and n.name != 'for_changes'}
    return namespace['failed_condition'], ast.dump(function), methods


def main():
    before = subprocess.check_output(['git', 'show', BASE + ':scripts/case_reuse.py'], cwd=ROOT, text=True)
    old, old_ast, old_methods = qualification(before)
    current, current_ast, current_methods = qualification((ROOT / 'scripts/case_reuse.py').read_text())
    assert old_ast == current_ast and old_methods == current_methods
    assert '\nSELECTION_ENABLED = False\n' in (ROOT / 'scripts/gate_changes.py').read_text()
    declaration = dict(non_file_inputs='none', rationale='fixture', proposal=dict(
        runs=[dict(mode=m, exit=0, reads='same', observation='seen', non_file=[])
              for m in ('baseline', 'baseline', 'noop', 'mutant')], gate_observation='seen', inputs='inputs',
        gate_receipt=dict(status='passed', input_digest='inputs')))
    edits = [
        ('valid', None, lambda p: None),
        ('unequal reads', 'baseline_reads_differ', lambda p: p['runs'][1].update(reads='other')),
        ('one baseline', 'trace_failed', lambda p: p['runs'].pop(0)),
        ('missing observation', 'observation_differs', lambda p: p.pop('gate_observation')),
        ('different observation', 'observation_differs', lambda p: p.update(gate_observation='other')),
        ('missing receipt', 'observation_not_current', lambda p: p.pop('gate_receipt')),
        ('wrong receipt inputs', 'observation_not_current', lambda p: p['gate_receipt'].update(input_digest='old')),
        ('failed receipt', 'observation_not_current', lambda p: p['gate_receipt'].update(status='failed')),
    ]
    for name, expected, edit in edits:
        value = copy.deepcopy(declaration)
        edit(value['proposal'])
        previous, now = old({}, 'fixture', value), current({}, 'fixture', value)
        assert previous == now == expected, (name, previous, now, expected)
        print(name + ': ' + str(now))
    print('OFF qualification and original Session methods match ' + BASE)


if __name__ == '__main__':
    main()
