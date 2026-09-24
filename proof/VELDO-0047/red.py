#!/usr/bin/env python3
"""Run the CURRENT suite 66 over the pre-change code and print every VELDO-0047 row.

    python3 -B proof/VELDO-0047/red.py b738c79      (before the service existed)
    python3 -B proof/VELDO-0047/red.py 7ed08fb      (before the review fixes)

This is how each row was recorded red by assertion before the change. The suite's four production
anchors (control_service.py, control_client.py, init_scaffold.py and the unit template) are pointed at
the commit's own copies. At b738c79 there is no authority service, no unit template and no installer:
the client names no service unit or start procedure when the authority is absent, and the scaffolder
installs neither, so the two it lacks are the stand-ins prefix/control_service.py (it installs, starts
and refuses nothing) and prefix/veldo-authority.service. At 7ed08fb all four are the commit's. Every
other installed module is checked byte-identical to the commit's copy and reported, so the anchors are
the only substitution. A row that fails reports its observation, never a crash: each region reds its
rows on a raise, and a `ran/` row says whether it did.
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


def at(commit, rel):
    """The commit's copy of `rel`, or None when the commit has none."""
    proc = _git_process.run(['git', '-C', str(ROOT), 'show', '%s:%s' % (commit, rel)], capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


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
        stand_ins = {'control_service.py': HERE / 'prefix' / 'control_service.py',
                     'services/veldo-authority.service': HERE / 'prefix' / 'veldo-authority.service'}
        anchors, used = {}, {}
        for name in ('control_service.py', 'control_client.py', 'init_scaffold.py', 'services/veldo-authority.service'):
            data = at(commit, '.veldo/' + name)
            if data is None:
                anchors['ROOT / ".veldo" / "%s"' % name] = stand_ins[name]
                used[name] = str(stand_ins[name].relative_to(ROOT))
                continue
            path = Path(directory) / name.replace('/', '_')
            path.write_bytes(data)
            anchors['ROOT / ".veldo" / "%s"' % name] = path
            used[name] = '%s:.veldo/%s' % (commit, name)
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
        'substituted': used,
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('placement', 'located', 'guided', 'relative', 'install', 'receiver',
                                                   'lock', 'mutation', 'refusals', 'absent', 'exit', 'observations',
                                                   'launch', 'assets')},
    }, indent=1, sort_keys=True, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'b738c79')
