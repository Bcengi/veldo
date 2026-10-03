#!/usr/bin/env python3
"""Run current VELDO-0088 assertions against an unchanged git archive of the red commit.
Uses generated fixture keys and loopback presentation; no model or real credentials.
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '92_veldo_0088_pm_cycles.py'
PREFIX = 'VELDO-0088 '
FINDING = 88
MODULES = ('control_workflow_cycle_pm.py', 'control_graph_pm.py', 'control_dispatch.py', 'control_eligibility.py', 'control_service.py', 'control_launch.py', 'control_team.py', 'authority_contract.py', 'init_scaffold.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v88_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def one(paths, root):
    """Run the shared preamble of `root` and the current suite once, in this interpreter."""
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
                raise RuntimeError('suite production-copy anchor moved: ' + module)
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(path) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    details = [line.strip() for line in out.getvalue().split('\n') if PREFIX.strip() in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]], 'details': details,
            'preamble_rows': len(rows) - len(mine)}


def run(paths=None, root=None):
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one', json.dumps(paths or {}), str(root or ROOT)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _raised(observed):
    return any('did not run to its end' in d for d in observed['details'])


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v88-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        observed = run({}, tree)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0088', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite file run against it' % resolved, modules=modules,
                  by_assertion=not _raised(observed), **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    if not report['by_assertion'] or not observed['rows'] or any(ok for _, ok in observed['rows']):
        raise SystemExit('Red record must fail every behavior row by assertion.')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'by_assertion': report['by_assertion'],
                      'written': name}))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
        return
    raise SystemExit('Use the red option; mutation execution belongs to the reviewer.')


if __name__ == '__main__':
    main()
