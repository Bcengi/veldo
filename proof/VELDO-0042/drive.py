#!/usr/bin/env python3
"""Drive every finding-42 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run is a
fresh interpreter executing the shared preamble and the VELDO-0042 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant. Rows
and the suite's own region-completion rows are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0042/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0042/drive.py

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT, extracted
read-only with `git archive` into a temporary directory, and writes proof/VELDO-0042/red-at-COMMIT.json.
Nothing in that tree is changed. At 18ecd6f the isolated-clone provisioner did not exist, so the
suite's control_clone anchor is pointed at proof/VELDO-0042/prefix/control_clone.py, a stand-in that
refuses every provision; every other module is the commit's own, byte-identical. Each row then reds by
its own assertion (the capability is absent, and the commit's init_scaffold installs neither asset).

    python3 -B proof/VELDO-0042/drive.py --red 18ecd6f
"""
import ast
import contextlib
import difflib
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
SUITE = '66_veldo_0042_clones.py'
PREFIX = 'VELDO-0042 '
FINDING = 42
MODULES = ('control_clone.py', 'env_provision.py', 'init_scaffold.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v42_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(paths, root):
    """Run the shared preamble of `root` and the current suite once, in this interpreter."""
    shared = Path(root) / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        for module, path in paths.items():
            anchor = 'ROOT / ".veldo" / "' + module + '"'
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + module)
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(path)) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    ran = [r[0] for r in mine if r[0].startswith(PREFIX + 'ran/') and not r[1]]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]],
            'regions_that_raised': ran, 'preamble_rows': len(rows) - len(mine)}


def run(paths=None, root=None):
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one', json.dumps(paths or {}), str(root or ROOT)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive; the
    control_clone anchor points at the prefix stand-in only when the module is absent at COMMIT."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    prefix = HERE / 'prefix' / 'control_clone.py'
    with tempfile.TemporaryDirectory(prefix='v42-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        absent = not (tree / '.veldo' / 'control_clone.py').is_file()
        observed = run({'control_clone.py': str(prefix)} if absent else {}, tree)
    described = ('with control_clone absent (proof/VELDO-0042/prefix/control_clone.py stands in)' if absent
                 else 'with every module the commit\'s own')
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0042', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite run against it %s' % (resolved, described),
                  control_clone_at_commit='absent' if absent else 'present', modules=modules,
                  by_assertion=not observed['regions_that_raised'], **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'],
                      'by_assertion': report['by_assertion'], 'written': name}))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0042', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'baseline': run(), 'noop': None,
              'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v42-drive-') as directory:
        report['noop'] = {}
        for module in sorted({c['module'] for c in cases}):
            case = next(c for c in cases if c['module'] == module)
            noop = ctm.materialize(case, 'noop', Path(directory) / ('noop-' + module))
            report['noop'][module] = dict(run({module: str(noop['mutant'])}), source_sha256=noop['old_digest'],
                                          copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            source = prepared['source'].read_text()
            (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), ctm.mutate(source, case).splitlines(keepends=True),
                n=0, fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module'])))
            observed = run({case['module']: str(prepared['mutant'])})
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                                          diff='proof/VELDO-0042/%s.diff' % case['name'],
                                          edits=1 + len(case.get('also', ())),
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in case['rows']),
                                          by_assertion=not observed['regions_that_raised'], **observed))
    report['all_named_rows_red'] = all(m['named_row_red'] for m in report['mutants'])
    report['all_by_assertion'] = all(m['by_assertion'] for m in report['mutants'])
    report['controls_green'] = not report['baseline']['failed_rows'] and all(
        not n['failed_rows'] for n in report['noop'].values())
    per_row = {}
    for m in report['mutants']:
        for r in m['named_rows']:
            per_row.setdefault(r, []).append(m['name'])
    report['mutations_per_row'] = per_row
    report['serial_seconds'] = round(report['baseline']['seconds'] + sum(n['seconds'] for n in report['noop'].values())
                                     + sum(m['seconds'] for m in report['mutants']), 3)
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'mutants': len(report['mutants']), 'all_named_rows_red': report['all_named_rows_red'],
                      'all_by_assertion': report['all_by_assertion'], 'controls_green': report['controls_green'],
                      'mutations_per_row': {k: len(v) for k, v in per_row.items()},
                      'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
