#!/usr/bin/env python3
"""Run the CURRENT suite 68_veldo_0134 over every .veldo module of an earlier commit and print every row.

    python3 -B proof/VELDO-0134/red.py 8dcdd34     (the pre-change commit: main as this build started)

The suite's ROOT is pointed at an export of that commit's .veldo directory and of this specification, so
every module the suite installs (its production-copy anchors and the rest of the engine it copies beside
them) is that commit's. No line of the suite is substituted: where the commit has no writer the suite's
own drive answers no_writer, so each criterion row fails its assertion, and each region's `ran/` row says
it completed.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/68_veldo_0134_acceptance.py'
_spec = importlib.util.spec_from_file_location('red_git_process', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)


def main(commit):
    rows = []
    with tempfile.TemporaryDirectory(prefix='v134-red-') as directory:
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', commit, '.veldo', 'specs'], check=True,
                                   capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(directory, filter='data')
        shared = ROOT / 'scripts/suites/shared.py'
        ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
        stree = ast.parse(shared.read_text(), str(shared))
        for node in stree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'expect':
                node.body = ast.parse('__observe__(name, condition)').body
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.fix_missing_locations(stree), str(shared), 'exec'), ns)
            ns['ROOT'] = Path(directory)
            ns['__suite_file__'] = str(SUITE)
            before = len(rows)
            exec(compile(SUITE.read_text(), str(SUITE), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0134')]
    observed = ns.get('_V134_OBSERVED') or {}
    print(json.dumps({'production_at': commit, 'modules': '.veldo/*.py of ' + commit,
                      'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
                      'observed': {k: observed.get(k) for k in ('first', 'signers', 'schema_oracle', 'generic_write',
                                                                'raised')}},
                     indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'HEAD')
