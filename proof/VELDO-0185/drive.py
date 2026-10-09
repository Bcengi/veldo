#!/usr/bin/env python3
"""Execute VELDO-0185's registered falsifiers, and replay suite 106 against the tree before this change.

Run: python3 proof/VELDO-0185/drive.py --mutations
     python3 proof/VELDO-0185/drive.py --red <pre-change commit>

--mutations runs scripts/check_teeth_mutations.py's own worker for every finding-185 case: once on the
unchanged production modules (the baseline every VELDO-0185 row must pass), then once per case on a copy of
its module with the case's exact replacement (materialize), recording which rows went false. The worker runs
as an ordinary process of this host, not inside the mutation stage's confined domain: suite 106 qualifies
the worker profile through the host's user manager, which that domain does not reach (the stage refuses
setup there with unavailable_service:profile:user_manager, as it does for suite 87's setup baselines).

--red replays the current suite against an unchanged `git archive` of the named commit, as VELDO-0186's
driver does, and records that every behavior row is false there by assertion.
"""
import ast
import contextlib
import difflib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '106_veldo_0185_dispatch_setup.py'
PREFIX = 'VELDO-0185 '


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(name, mutant=None):
    """The teeth driver's own worker for case `name`, as a separate process: its JSON answer."""
    command = [sys.executable, '-B', str(ROOT / 'scripts/check_teeth_mutations.py'), '--finding', '185',
               '--worker', name] + (['--mutant', str(mutant)] if mutant else [])
    started = time.monotonic()
    done = subprocess.run(command, capture_output=True, text=True, timeout=1800, cwd=str(ROOT))
    lines = [line for line in done.stdout.splitlines() if line.startswith('{"count"')]
    answer = json.loads(lines[-1]) if lines else {'error': done.stderr[-600:]}
    answer['seconds'] = round(time.monotonic() - started, 3)
    return answer


def mine(answer):
    return {name: ok for name, ok in answer.get('observations', []) if name.startswith(PREFIX)}


def mutations():
    teeth = load('v185_teeth', ROOT / 'scripts/check_teeth_mutations.py')
    cases = [case for case in teeth.cases() if case['finding'] == 185]
    baseline = worker(cases[0]['name'])
    rows = mine(baseline)
    report = {'schema': 'veldo.mutation-registration/v1', 'spec_id': 'VELDO-0185',
              'status': 'registered; executed by proof/VELDO-0185/drive.py outside the confined stage',
              'suite': 'scripts/suites/' + SUITE,
              'baseline': {'rows': len(rows), 'all_passed': bool(rows) and all(rows.values()),
                           'seconds': baseline['seconds']},
              'mutations': []}
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='v185-mutant-') as directory:
            made = teeth.materialize(case, 'mutant', directory)
            source = Path(made['source']).read_text()
            mutated = Path(made['mutant']).read_text()
            answer = worker(case['name'], made['mutant'])
        diff = ''.join(difflib.unified_diff(source.splitlines(True), mutated.splitlines(True),
                                            '.veldo/' + case['module'], '.veldo/' + case['module']))
        (HERE / (case['name'] + '.diff')).write_text(diff)
        observed = mine(answer)
        false = sorted(name[len(PREFIX):] for name, ok in observed.items() if not ok)
        details = {row: text for row, text in answer.get('failed_details', []) if row.startswith(PREFIX)}
        report['mutations'].append({
            'name': case['name'], 'module': '.veldo/' + case['module'], 'named_rows': case['rows'],
            'diff': 'proof/VELDO-0185/' + case['name'] + '.diff', 'source_sha256': made['old_digest'],
            'mutant_sha256': made['new_digest'], 'executed': True, 'seconds': answer['seconds'],
            'detected': bool(observed) and all(row in false for row in case['rows']),
            'false_rows': false,
            'named_row_details': {row: details.get(PREFIX + row) for row in case['rows']}})
        print(json.dumps({k: report['mutations'][-1][k] for k in ('name', 'detected', 'false_rows')}), flush=True)
    report['all_detected'] = report['baseline']['all_passed'] and all(m['detected'] for m in report['mutations'])
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    return 0 if report['all_detected'] else 1


def one(root):
    shared = root / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared), '__suite_file__': str(ROOT / 'scripts/suites' / SUITE),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition),
                                                               name.split(':', 1)[1].strip() if ':' in name else ''])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        exec(compile(source, SUITE, 'exec'), ns)
    found = [row for row in rows if row[0].startswith(PREFIX)]
    return {'rows': [[name, ok] for name, ok, _ in found], 'failed_rows': [name for name, ok, _ in found if not ok],
            'details': {name: detail for name, ok, detail in found if not ok},
            'by_assertion': not any('raised' in detail for _name, _ok, detail in found)}


def red(commit):
    git = load('v185_git', ROOT / '.veldo/git_process.py')
    resolved = git.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                       capture_output=True, text=True, check=True).stdout.strip()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='v185-red-') as directory:
        tree = Path(directory)
        archive = git.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True, capture_output=True)
        done = subprocess.run([sys.executable, '-B', __file__, '--one', str(tree)], capture_output=True, text=True,
                              timeout=1800, check=True, cwd=str(tree))
        observed = json.loads(done.stdout.strip().splitlines()[-1])
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0185', commit=resolved, suite='scripts/suites/' + SUITE,
                  tree='unchanged git archive of the pre-change commit', seconds=round(time.monotonic() - started, 3),
                  **observed)
    suite_tree = ast.parse((ROOT / 'scripts/suites' / SUITE).read_text())
    expected = next(ast.literal_eval(node.value) for node in ast.walk(suite_tree)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROWS' for t in node.targets))
    behavior = [name for name in expected if name != 'format/fake-lines']
    report['behavior_rows'] = behavior
    report['all_behavior_rows_red'] = all(PREFIX + name in report['failed_rows'] for name in behavior)
    (HERE / ('red-at-' + commit + '.json')).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ('commit', 'failed_rows', 'by_assertion', 'all_behavior_rows_red')}))
    return 0 if report['by_assertion'] and report['all_behavior_rows_red'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--one':
        print(json.dumps(one(Path(sys.argv[2]))))
    elif len(sys.argv) == 3 and sys.argv[1] == '--red':
        raise SystemExit(red(sys.argv[2]))
    elif sys.argv[1:] == ['--mutations']:
        raise SystemExit(mutations())
    else:
        raise SystemExit('name --mutations, or --red with the pre-change commit')
