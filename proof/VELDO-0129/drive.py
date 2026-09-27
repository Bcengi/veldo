"""Reproduce the base red record and exact finding 129 mutations in temporary trees.

Use the red option with a commit, or no options for mutation evidence. Each suite
runs in a fresh interpreter. No branch, worktree or production file is rewritten.
"""
import ast
import contextlib
import hashlib
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
SUITE = '82_veldo_0129_worker_wiring.py'
PREFIX = 'VELDO-0129 '
OPT = '-' * 2
MODULES = ('control_launch_work.py', 'control_launch.py', 'control_engine_claude.py', 'executor.py',
           'dispatch.py', 'init_scaffold.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(paths, root):
    shared = Path(root) / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared), '__suite_file__': str(ROOT / 'scripts/suites' / SUITE),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        for module, path in paths.items():
            anchor = 'ROOT / ".veldo" / "' + module + '"'
            if source.count(anchor) != 1:
                raise RuntimeError('production-copy anchor moved: ' + module)
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(path) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    details = [line.strip() for line in out.getvalue().splitlines() if 'detail:' in line and PREFIX in line]
    return dict(rows=mine, failed_rows=[name for name, ok in mine if not ok], details=details,
                by_assertion=not any('fixture setup did not complete' in d for d in details),
                one_report_per_row=len(mine) == len({name for name, _ in mine}))


def run(paths=None, root=ROOT):
    started = time.monotonic()
    proc = subprocess.run([sys.executable, '-B', __file__, OPT + 'one', json.dumps(paths or {}), str(root)],
                          capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def red(commit):
    GP = load('red_git', ROOT / '.veldo/git_process.py')
    resolved = GP.run(['git', 'rev-parse', OPT + 'verify', commit + '^{commit}'],
                      capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v129-red-') as directory:
        tree = Path(directory)
        archive = GP.run(['git', 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        observed = run(root=tree)
        digests = {name: hashlib.sha256((tree / '.veldo' / name).read_bytes()).hexdigest()
                   if (tree / '.veldo' / name).is_file() else None for name in MODULES}
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0129', commit=resolved,
                  tree='unchanged git archive; current suite against base production', modules=digests, **observed)
    (HERE / ('red-at-' + commit + '.json')).write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report))


def mutations():
    driver = load('teeth', ROOT / 'scripts/check_teeth_mutations.py')
    cases = [c for c in driver.cases() if c['finding'] == 129]
    report = dict(schema='veldo.proof-mutations/v1', spec_id='VELDO-0129', baseline=run(), mutants=[])
    with tempfile.TemporaryDirectory(prefix='v129-mutants-') as directory:
        for case in cases:
            material = driver.materialize(case, 'mutant', Path(directory) / case['name'])
            observed = run({case['module']: str(material['mutant'])})
            report['mutants'].append(dict(name=case['name'], module=case['module'],
                source_sha256=material['old_digest'], mutant_sha256=material['new_digest'],
                edits=[{'old': old, 'new': new} for old, new in driver.edits(case)], named_rows=case['rows'],
                named_rows_red=all(PREFIX + row in observed['failed_rows'] for row in case['rows']), **observed))
    report['all_rejected'] = all(m['named_rows_red'] and m['by_assertion'] for m in report['mutants'])
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({'mutants': len(cases), 'all_rejected': report['all_rejected']}))


if __name__ == '__main__':
    if sys.argv[1:2] == [OPT + 'one']:
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
    elif sys.argv[1:2] == [OPT + 'red']:
        red(sys.argv[2])
    else:
        mutations()
