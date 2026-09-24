#!/usr/bin/env python3
"""Run the CURRENT suite 64 over the pre-change executor and print every VELDO-0050 row.

    python3 -B proof/VELDO-0050/red.py 91fb549 > proof/VELDO-0050/red-91fb549.json

This is how each row was recorded red by assertion before the change. At 91fb549 the executor
assembles every proof with a default passed unit check, validates it with check_json alone over a
temporary file, stores nothing, reads the gate's last line as its whole observation and emits
verdict.recorded itself; there is no control_proof module. The suite's three production anchors are
pointed at prefix/executor.py (91fb549's executor.py byte for byte, followed by a marked stand-in
section that gives the names the suite calls their pre-change behaviour), prefix/control_proof.py
(a marked stand-in that stores, resolves and names nothing) and the commit's own init_scaffold.py.
Every other installed module is checked byte-identical to the commit's copy and reported, so the
stand-ins are the only substitution. A row that fails reports its observation, never a crash: each
region reds its rows on a raise, and a `ran/` row says whether it did.
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
SUITE = ROOT / 'scripts/suites/64_veldo_0050_proof.py'
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('red_git', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    new_here = {'executor.py', 'control_proof.py', 'init_scaffold.py'}
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - new_here
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    prefix = (HERE / 'prefix' / 'executor.py').read_bytes()
    original = git('show', '%s:.veldo/executor.py' % commit)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v50-red-') as directory:
        scaffold = Path(directory) / 'init_scaffold.py'
        scaffold.write_bytes(git('show', '%s:.veldo/init_scaffold.py' % commit))
        anchors = {
            'ROOT / ".veldo" / "executor.py"': HERE / 'prefix' / 'executor.py',
            'ROOT / ".veldo" / "control_proof.py"': HERE / 'prefix' / 'control_proof.py',
            'ROOT / ".veldo" / "init_scaffold.py"': scaffold,
        }
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0050')]
    observed = ns.get('_V50_OBSERVED') or {}
    contextual = observed.get('contextual') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'executor.py': 'proof/VELDO-0050/prefix/executor.py',
                        'control_proof.py': 'proof/VELDO-0050/prefix/control_proof.py (absent at %s)' % commit,
                        'init_scaffold.py': '%s:.veldo/init_scaffold.py' % commit},
        'prefix_begins_with_the_commit_bytes': prefix.startswith(original),
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {
            'accepted_before_offer': {k: (observed.get('accepted_before_offer') or {}).get(k)
                                      for k in ('dispatch', 'proof_step', 'seqs', 'again', 'forged')},
            'actual_checks': {k: (observed.get('actual_checks') or {}).get(k) for k in ('checks', 'exit', 'terminal')},
            'build_only': (observed.get('build_only') or {}).get('fresh'),
            'fresh_reviewer': (observed.get('fresh_reviewer') or {}).get('resolution'),
            'contextual_accepted_by_the_old_check': sorted(k for k, v in contextual.items() if v.get('ok')),
            'owning_services': {k: (observed.get('owning_services') or {}).get(k) for k in ('run', 'raised', 'events')},
            'no_default_success': {k: (observed.get('no_default_success') or {}).get(k)
                                   for k in ('assembled_checks', 'direct', 'altered', 'foreign')},
            'installed': observed.get('installed'),
            'observations': (observed.get('observations') or {}).get('status'),
        },
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '91fb549')
