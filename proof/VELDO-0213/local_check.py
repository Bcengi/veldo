#!/usr/bin/env python3
"""Run only the synchronous suite row and its falsifiers, without the host fixture."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/80_veldo_0155_claude_baseline.py'


def load(name, path, source=None):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if source is None:
        spec.loader.exec_module(module)
    else:
        exec(compile(source, str(path), 'exec'), module.__dict__)
    return module


def main():
    # Execute the exact function used by the named suite row, without running its
    # systemd fixture or the mutation dispatcher. Production modules load normally.
    tree = ast.parse(SUITE.read_text(), filename=str(SUITE))
    row = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_v213_prompt_write')
    namespace = {}
    exec(compile(ast.Module(body=[row], type_ignores=[]), str(SUITE), 'exec'), namespace)
    drive = namespace[row.name]
    case_tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    names = ('prompt213-mark-after-write', 'role127-probe-is-terminal',
             'role127-prompt-write-failure-swallowed')
    cases = {}
    for node in ast.walk(case_tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add'
                and len(node.args) >= 7 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in names):
            cases[node.args[1].value] = {key: ast.literal_eval(node.args[index])
                                       for key, index in (('module', 3), ('old', 4), ('new', 5), ('rows', 6))}
    if len(cases) != len(names):
        raise AssertionError('missing registered falsifier')
    for case in cases.values():
        for base in (ROOT / '.veldo', ROOT / 'engine/.veldo'):
            assert (base / case['module']).read_text().count(case['old']) == 1
    reports = []
    for name in ('baseline', 'prompt213-mark-after-write', 'role127-probe-is-terminal'):
        path = ROOT / '.veldo/control_launch.py'
        if name == 'prompt213-mark-after-write':
            case = cases[name]
            launch = load('prompt213_launch_mutant', path, path.read_text().replace(case['old'], case['new']))
        else:
            launch = load('prompt213_launch_' + name.replace('-', '_'), path)
        if name == 'role127-probe-is-terminal':
            case = cases[name]
            engine_path = ROOT / '.veldo' / case['module']
            launch.ENGINES['claude_code'] = load('prompt213_probe_mutant', engine_path,
                                               engine_path.read_text().replace(case['old'], case['new']))
        checks = []
        drive(lambda row, label, ok: checks.append({'row': row, 'label': label, 'passed': bool(ok)}), launch)
        assert len(checks) == 5
        failed = [check for check in checks if not check['passed']]
        if name == 'baseline':
            assert not failed, failed
        elif name == 'prompt213-mark-after-write':
            assert len(failed) == 1 and 'missing_result' in failed[0]['label'], failed
        else:
            assert len(failed) == 2, failed
        reports.append({'case': name, 'checks': checks, 'failed_checks': len(failed)})
    print(json.dumps({'scope': 'Python row only; no full suite or mutation dispatcher executed',
                      'registered_anchors': list(cases), 'runs': reports}, indent=2))


if __name__ == '__main__':
    main()
