#!/usr/bin/env python3
"""Drive every finding-189 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run is a
fresh interpreter executing the shared preamble and the VELDO-0189 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant. Rows
and the suite's own failure detail lines are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0189/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0189/drive.py

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT, a local
clone checked out at COMMIT in a temporary directory, and writes
proof/VELDO-0189/red-at-COMMIT.json. Nothing in that tree is changed. At the commit before VELDO-0189 it
has no engine upgrade module (.veldo/control_factory_setup_upgrade.py) and its installer has no layout, so
every row fails by its own assertion; at the commit before the review fix the rows that fix added fail by
their own assertions (the suite records that against each row rather than raising).

    python3 -B proof/VELDO-0189/drive.py --red <pre-change commit>
    python3 -B proof/VELDO-0189/drive.py --cache <directory> [--budget <seconds>]   (resumable)
"""
# Add --runtime to --red COMMIT to assert the runtime budget against the original suite.
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
SUITE = '86_veldo_0189_engine_upgrade.py'
PREFIX = 'VELDO-0189 '
FINDING = 189
MODULES = ('control_factory_setup.py', 'control_factory_setup_upgrade.py', 'control_factory_setup_api.py',
           'control_service.py', 'control_store.py', 'init_scaffold.py', 'control_factory_setup_engines.py')
# With `--cache DIR` each run's result is kept in DIR under the digest of the suite, the tree and every
# substituted file, so a drive longer than one sitting is finished by running it again.
CACHE = None
# With `--budget SECONDS` beside it, no run starts after that many seconds; the drive stops and says so.
BUDGET = None
BEGAN = time.monotonic()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v189_drive_git_process', ROOT / '.veldo' / 'git_process.py')


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
          '__setup_support__': str(ROOT / 'scripts/suites/support/setup_runtime.py'),
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
    key = None
    if CACHE is not None:
        key = hashlib.sha256(json.dumps([_sha(ROOT / 'scripts/suites' / SUITE), str(root or ROOT),
                                         sorted((m, _sha(p)) for m, p in (paths or {}).items())]).encode()).hexdigest()
        if (CACHE / (key + '.json')).is_file():
            return json.loads((CACHE / (key + '.json')).read_text())
        if BUDGET is not None and time.monotonic() - BEGAN > BUDGET:
            raise SystemExit('drive: the budget is spent; the finished runs are kept in %s, run it again' % CACHE)
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one', json.dumps(paths or {}), str(root or ROOT)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    result = dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))
    if key is not None:
        (CACHE / (key + '.json')).write_text(json.dumps(result))
    return result


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _raised(observed):
    return any('ran to its end' in d for d in observed['details'])


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, in a local clone checked out at it."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v189-red-') as directory:
        # A local clone checked out at COMMIT, so the suite finds the older engines and the history its census
        # reads (a bare archive has no repository, and the rows over the older hosts would raise instead).
        tree = Path(directory) / 'tree'
        _git_process.run(['git', 'clone', '-q', '--no-checkout', str(ROOT), str(tree)], capture_output=True, check=True)
        _git_process.run(['git', '-C', str(tree), 'checkout', '-q', '--detach', resolved], capture_output=True,
                         check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        observed = run({}, tree)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0189', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='a local clone checked out at %s, unchanged; the current suite file run against it' % resolved, modules=modules,
                  by_assertion=not _raised(observed), **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'by_assertion': report['by_assertion'],
                      'written': name}))


def main():
    global CACHE, BUDGET
    if len(sys.argv) >= 3 and sys.argv[1] == '--cache':
        CACHE = Path(sys.argv[2])
        CACHE.mkdir(parents=True, exist_ok=True)
        del sys.argv[1:3]
        if len(sys.argv) >= 3 and sys.argv[1] == '--budget':
            BUDGET = float(sys.argv[2])
            del sys.argv[1:3]
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        if '--runtime' in sys.argv[3:]:
            support = _load('setup_runtime', ROOT / 'scripts/suites/support/setup_runtime.py')
            support.runtime_red(ROOT, HERE, SUITE, sys.argv[2], 60, _git_process)
        else:
            red(sys.argv[2])
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0189', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'baseline': run(), 'noop': None,
              'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v189-drive-') as directory:
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
                                          diff='proof/VELDO-0189/%s.diff' % case['name'],
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in case['rows']),
                                          by_assertion=not _raised(observed), **observed))
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
                      'all_by_assertion': report['all_by_assertion'],
                      'controls_green': report['controls_green'], 'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
