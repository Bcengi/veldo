#!/usr/bin/env python3
"""Drive every finding-148 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run is a
fresh interpreter executing the shared preamble and the VELDO-0148 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant. Rows
and the suite's own failure detail lines are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0148/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0148/drive.py

With `--report-mutants` it applies only the three report-handshake mutations in
a disposable archive and runs suite 86 serially through its selftest selector.
This mode reads registrations as syntax and never executes the mutation checker.

With `--wake-only` it applies just the wake no-op by hand to a temporary module
copy and asserts that only reland/end-wakes-pass is red. This mode never imports
the mutation checker.

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT,
extracted read-only with `git archive` into a temporary directory, and writes
proof/VELDO-0148/red-at-COMMIT.json. Nothing in that tree is changed. Against the original base all behavior rows fail by assertion;
against f59b3136 the four re-check rows expose mixed requests, repeated grants and revoked approvals.

    python3 -B proof/VELDO-0148/drive.py --red <pre-change commit>
"""
import ast
import concurrent.futures
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
SUITE = '86_veldo_0148_re_land.py'
PREFIX = 'VELDO-0148 '
FINDING = 148
MODULES = ('control_service.py', 'control_landing_station.py', 'control_landing.py', 'control_effect_executor.py',
           'lander.py', 'control_launch.py', 'control_containment.py', 'control_heartbeat.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v148_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    proc = subprocess.run(command, capture_output=True, text=True, timeout=1500)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _raised(observed):
    return any('ran to its end' in d for d in observed['details'])


def regression_runs(root):
    """Run the original receiver regression suites serially through the normal selector.

    The caller supplies the gate environment. No mutation driver is loaded.
    """
    reports = []
    for suite in ('67_veldo_0041_heartbeat', '80_veldo_0155_claude_baseline', '81_veldo_0156_codex_baseline'):
        proc = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite],
                              cwd=root, capture_output=True, text=True, timeout=600)
        lines = (proc.stdout + proc.stderr).splitlines()
        failed = [line.split('SELFTEST FAIL: ', 1)[1] for line in lines if 'SELFTEST FAIL: ' in line]
        summary = next((line for line in lines if line.startswith('selftest (PARTIAL')), None)
        reports.append(dict(suite=suite, exit=proc.returncode, summary=summary, failed_rows=failed,
                            by_assertion=summary is not None and not any(
                                'raised' in line or 'Traceback' in line for line in lines),
                            details=[line for line in lines if 'detail:' in line]))
    return reports


def red(commit, regressions=False):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v148-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        observed = run({}, tree)
        previous = regression_runs(tree) if regressions else []
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0148', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite file run against it' % resolved, modules=modules,
                  by_assertion=not _raised(observed), receiver_regressions=previous, **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'by_assertion': report['by_assertion'],
                      'written': name}))


def wake_only():
    """Apply only the wake no-op by hand to a temporary copy; never load the mutation checker."""
    source = ROOT / '.veldo/control_service.py'
    old = "            self.loop.wake('run_end', record['dispatch_id'])\n"
    new = "            pass  # defect: a land's end wakes no pass\n"
    body = source.read_text()
    assert body.count(old) == 1
    with tempfile.TemporaryDirectory(prefix='v148-wake-') as directory:
        target = Path(directory) / 'control_service.py'
        target.write_text(body.replace(old, new))
        observed = run({'control_service.py': str(target)})
        report = dict(schema='veldo.manual-mutation/v1', spec_id='VELDO-0148',
                      name='reland148-end-wakes-nothing', source_sha256=_sha(source),
                      mutant_sha256=_sha(target), suite_sha256=_sha(ROOT / 'scripts/suites' / SUITE),
                      old=old, new=new, by_assertion=not _raised(observed),
                      named_rows=['reland/end-wakes-pass'], **observed)
    report['only_named_row_red'] = observed['failed_rows'] == [PREFIX + 'reland/end-wakes-pass']
    assert source.read_text() == body
    (HERE / 'manual-wake.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(report))
    assert report['by_assertion'] and report['only_named_row_red']


def report_mutants():
    """Run only the three report regressions' mutants, serially via suite 86.

    Read registrations as syntax, never execute the mutation checker. Each edit
    lives in a disposable archive of HEAD, never another branch or worktree.
    """
    names = {'receiver148-report-wait-unbounded', 'receiver148-late-wrapper-execs',
             'receiver148-wrapper-eof-is-timeout'}
    registry = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    cases = [tuple(ast.literal_eval(arg) for arg in node.args) for node in ast.walk(registry)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'reland148' and ast.literal_eval(node.args[0]) in names]
    assert len(cases) == len(names)
    commit = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, check=True).stdout.strip()
    records = []
    with tempfile.TemporaryDirectory(prefix='v148-report-mutants-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', commit],
                                   capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        for name, module, old, new, rows in cases:
            target = tree / '.veldo' / module
            source = target.read_text()
            assert source == (ROOT / '.veldo' / module).read_text()
            assert source.count(old) == 1
            target.write_text(source.replace(old, new))
            log = Path(directory) / (name + '.log')
            try:
                with log.open('w') as output:
                    proc = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', SUITE[:-3]],
                                          cwd=tree, stdout=output, stderr=subprocess.STDOUT, timeout=600)
                lines = log.read_text().splitlines()
                failed = [line.split('SELFTEST FAIL: ', 1)[1] for line in lines if 'SELFTEST FAIL: ' in line]
                summary = next((line for line in lines if line.startswith('selftest (PARTIAL')), None)
                record = dict(name=name, named_rows=list(rows), failed_rows=failed, summary=summary,
                              exit=proc.returncode, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                              mutant_sha256=_sha(target), by_assertion=summary is not None and not any(
                                  'ran to its end' in line or 'Traceback' in line for line in lines),
                              only_named_rows_red=failed == [PREFIX + row for row in rows],
                              details=[line.strip() for line in lines if ' detail:' in line])
                records.append(record)
                print(name, summary, flush=True)
            finally:
                target.write_text(source)
    report = dict(schema='veldo.manual-mutation/v1', spec_id='VELDO-0148', commit=commit,
                  suite='scripts/suites/' + SUITE, suite_sha256=_sha(ROOT / 'scripts/suites' / SUITE),
                  mutants=records, checker_executed=False)
    (HERE / 'manual-report-mutants.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    assert all(r['by_assertion'] and r['only_named_rows_red'] for r in records)


def main():
    if sys.argv[1:] == ['--report-mutants']:
        report_mutants()
        return
    if sys.argv[1:] == ['--wake-only']:
        wake_only()
        return
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2], '--receiver-regressions' in sys.argv)
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0148', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'baseline': run(), 'noop': None,
              'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v148-drive-') as directory, concurrent.futures.ThreadPoolExecutor(
            max_workers=2) as pool:
        report['noop'] = {}
        for module in sorted({c['module'] for c in cases}):
            case = next(c for c in cases if c['module'] == module)
            noop = ctm.materialize(case, 'noop', Path(directory) / ('noop-' + module))
            report['noop'][module] = dict(pending=pool.submit(run, {module: str(noop['mutant'])}),
                                          source_sha256=noop['old_digest'], copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            source = prepared['source'].read_text()
            (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), ctm.mutate(source, case).splitlines(keepends=True),
                n=0, fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module'])))
            pending = pool.submit(run, {case['module']: str(prepared['mutant'])})
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                                          diff='proof/VELDO-0148/%s.diff' % case['name'],
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          pending=pending))
        for result in report['noop'].values():
            result.update(result.pop('pending').result())
        for result in report['mutants']:
            observed = result.pop('pending').result()
            result.update(observed, by_assertion=not _raised(observed),
                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in result['named_rows']))
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
