#!/usr/bin/env python3
"""Run the CURRENT suite 66 over the pre-change code and print every VELDO-0051 row.

    python3 -B proof/VELDO-0051/red.py 8231708 > proof/VELDO-0051/red-8231708.json

This is how each row was recorded red by assertion before the change. At 8231708 the emitter holds
31 event types and the validator its own 21, the writer admits a type substituted through an extra
field, spec.shipped is an ordinary hand-emittable type, and nothing projects the control journal.
The suite's three existing production anchors (events.py, validate.py, init_scaffold.py) are pointed
at the commit's own bytes; the two modules the commit does not have are pointed at prefix/, marked
stand-ins (the registry the suite enumerates, which nothing at the commit loads, and a projection
that derives nothing). Every other installed module is written from `git show 8231708:<path>`, and
so is the engine template tree the scaffolder lays from, so the stand-ins are the only substitution.
A row that fails reports its observation, never a crash: each region reds its rows on a raise, and a
`ran/` row says whether it did.
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
SUITE = ROOT / 'scripts/suites/66_veldo_0051_events.py'
HERE = Path(__file__).resolve().parent
NEW = ('control_event_vocabulary.py', 'control_event_projection.py')
_spec = importlib.util.spec_from_file_location('red_git', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', '-r', commit, '.veldo/', 'engine/').decode().splitlines()]
    installed = sorted(p for p in listed if p.startswith('.veldo/') and p.count('/') == 1
                       and (p.endswith('.py') or p == '.veldo/policy.yaml'))
    engine = sorted(p for p in listed if p.startswith('engine/'))
    present = [name for name in NEW if '.veldo/' + name in installed]
    with tempfile.TemporaryDirectory(prefix='v51-red-') as directory:
        base = Path(directory)
        for path in installed + engine:
            target = base / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git('show', '%s:%s' % (commit, path)))
        source = SUITE.read_text()
        anchors = {'ROOT / ".veldo" / "%s"' % name: base / '.veldo' / name
                   for name in ('events.py', 'validate.py', 'init_scaffold.py')}
        anchors.update({'ROOT / ".veldo" / "%s"' % name: HERE / 'prefix' / name for name in NEW})
        anchors.update({"ROOT / '.veldo'": base / '.veldo', "ROOT / 'engine'": base / 'engine'})
        for text, path in anchors.items():
            assert source.count(text) == 1, 'anchor moved: ' + text
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(path))
        rows = []
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0051')]
    observed = ns.get('_V51_OBSERVED') or {}
    vocabulary = observed.get('vocabulary') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {name: 'proof/VELDO-0051/prefix/%s (absent at %s)' % (name, commit) for name in NEW},
        'new_modules_present_at_commit': present,
        'installed_from_commit': len(installed), 'engine_templates_from_commit': len(engine),
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {
            'validator_over_the_owners_events': vocabulary.get('validator'),
            'journey_at_commit': vocabulary.get('journey'),
            'substitution_at_the_writer': (observed.get('refusals') or {}).get('writer', {}).get('substituted'),
            'substitution_in_process': (observed.get('refusals') or {}).get('substituted'),
            'direct_spec_shipped_after_build_only': (observed.get('build_only') or {}).get('direct'),
            'direct_log_unchanged': (observed.get('build_only') or {}).get('log_unchanged'),
            'projection': {k: (observed.get('projection') or {}).get(k) for k in ('first', 'second')},
            'installed': observed.get('installed'),
            'observations': observed.get('observations'),
        },
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '8231708')
