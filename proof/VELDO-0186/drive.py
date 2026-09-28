#!/usr/bin/env python3
"""Replay the current VELDO-0186 behavior suite against an archived pre-change tree.

Only the red replay is run here. Mutation execution belongs to the reviewer.
"""
import ast
import contextlib
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
SUITE = '86_veldo_0186_setup_assets.py'
PREFIX = 'VELDO-0186 '


def one(root):
    shared = root / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared), '__suite_file__': str(ROOT / 'scripts/suites' / SUITE),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [row for row in rows if row[0].startswith(PREFIX)]
    details = [line.strip() for line in output.getvalue().splitlines() if PREFIX in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [name for name, ok in mine if not ok], 'details': details,
            'by_assertion': not any('section raised' in line for line in details)}


def red(commit):
    spec = importlib.util.spec_from_file_location('v186_git', ROOT / '.veldo/git_process.py')
    git = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(git)
    resolved = git.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                       capture_output=True, text=True, check=True).stdout.strip()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='v186-red-') as directory:
        tree = Path(directory)
        archive = git.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True, capture_output=True)
        done = subprocess.run([sys.executable, '-B', __file__, '--one', str(tree)],
                              capture_output=True, text=True, timeout=120, check=True)
        observed = json.loads(done.stdout)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0186', commit=resolved,
                  suite='scripts/suites/' + SUITE, tree='unchanged git archive of the pre-change commit',
                  seconds=round(time.monotonic() - started, 3), **observed)
    suite_tree = ast.parse((ROOT / 'scripts/suites' / SUITE).read_text())
    expected = next(ast.literal_eval(node.value) for node in ast.walk(suite_tree)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROWS' for t in node.targets))
    report['all_behavior_rows_red'] = ({name for name, _ok in report['rows']} == {PREFIX + name for name in expected}
                                       and len(report['rows']) == len(expected)
                                       and all(not ok for _, ok in report['rows']))
    (HERE / ('red-at-' + commit + '.json')).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ('commit', 'failed_rows', 'by_assertion', 'all_behavior_rows_red')}))
    return 0 if report['by_assertion'] and report['all_behavior_rows_red'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--one':
        print(json.dumps(one(Path(sys.argv[2]))))
    elif len(sys.argv) == 3 and sys.argv[1] == '--red':
        raise SystemExit(red(sys.argv[2]))
    else:
        raise SystemExit('name the pre-change commit with the red option')
