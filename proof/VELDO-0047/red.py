#!/usr/bin/env python3
"""Run the CURRENT suite 66 over the pre-change code and print every VELDO-0047 row.

    python3 -B proof/VELDO-0047/red.py b738c79

This is how each row was recorded red by assertion before the change. At b738c79 there is no
authority service, no unit template and no installer: the client names no service unit or start
procedure when the authority is absent, and the scaffolder installs neither. The suite's four
production anchors are pointed at: b738c79's own control_client.py and init_scaffold.py, and the
stand-ins prefix/control_service.py (the module that does not exist there: it installs, starts and
refuses nothing) and prefix/veldo-authority.service. Every other installed module is checked
byte-identical to the commit's copy and reported, so the stand-ins are the only substitution. A row
that fails reports its observation, never a crash: each region reds its rows on a raise, and a `ran/`
row says whether it did.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/66_veldo_0047_authority.py'
HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _load('red_git_process', ROOT / '.veldo' / 'git_process.py')


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    substituted = {'control_client.py', 'init_scaffold.py', 'control_service.py'}
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - substituted
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    rows = []
    with tempfile.TemporaryDirectory(prefix='v47-red-') as directory:
        anchors = {'ROOT / ".veldo" / "control_service.py"': HERE / 'prefix' / 'control_service.py',
                   'ROOT / ".veldo" / "services/veldo-authority.service"': HERE / 'prefix' / 'veldo-authority.service'}
        for name in ('control_client.py', 'init_scaffold.py'):
            path = Path(directory) / name
            path.write_bytes(git('show', '%s:.veldo/%s' % (commit, name)))
            anchors['ROOT / ".veldo" / "%s"' % name] = path
        for text, path in anchors.items():
            assert source.count(text) == 1, 'anchor moved: ' + text
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(path))
        shared = ROOT / 'scripts/suites/shared.py'
        ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
        tree = ast.parse(shared.read_text(), str(shared))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'expect':
                node.body = ast.parse('__observe__(name, condition)').body
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
            ns['__suite_file__'] = str(SUITE)
            before = len(rows)
            exec(compile(source, str(SUITE), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0047')]
    observed = ns.get('_V47_OBSERVED') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'control_client.py': '%s:.veldo/control_client.py' % commit,
                        'init_scaffold.py': '%s:.veldo/init_scaffold.py' % commit,
                        'control_service.py': 'proof/VELDO-0047/prefix/control_service.py',
                        'services/veldo-authority.service': 'proof/VELDO-0047/prefix/veldo-authority.service'},
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('placement', 'install', 'receiver', 'lock', 'mutation', 'refusals',
                                                   'absent', 'exit', 'observations')},
    }, indent=1, sort_keys=True, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'b738c79')
