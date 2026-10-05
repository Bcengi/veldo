#!/usr/bin/env python3
"""Drive every finding-205 mutation and record what each one turned red, and why.

Uses the registry and the mutation of scripts/check_teeth_mutations.py unchanged. Each run is a fresh
interpreter executing the shared preamble of a whole tree and the current VELDO-0205 suite against it:
the tree is HEAD extracted read-only with `git archive`, unchanged (the baseline), with the module a
mutation names copied unchanged (its no-op control), or with that mutation applied. The suite reads its
production modules from the tree's .veldo, and its fixtures from this repository's proof directory.
Rows and the suite's own failure detail lines are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0205/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0205/drive.py

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT, extracted
read-only with `git archive` into a temporary directory, and writes proof/VELDO-0205/red-at-COMMIT.json.
Nothing in that tree is changed; where the code before VELDO-0205 takes none of the keywords it adds
(served repositories, the authority lock), the suite calls it without them, so the rows fail by their
own checks.

    python3 -B proof/VELDO-0205/drive.py --red <pre-change commit>
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
SUITE = '95_veldo_0205_multirepo.py'
PREFIX = 'VELDO-0205 '
FINDING = 205
MODULES = ('control_alias.py', 'control_readset.py', 'control_team.py', 'control_team_routes.py', 'control_assignment.py',
           'control_claim.py', 'control_backlog.py', 'control_decomposition.py', 'control_grooming.py', 'control_intake.py',
           'control_intake_routes.py', 'control_workflow_cycle_pm.py', 'control_channel_ingress.py',
           'control_channel_presentation.py', 'control_channel_attribution.py', 'control_request_settlement.py',
           'control_signer_answers.py', 'control_service_channel.py', 'control_service.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v205_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(root):
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
        exec(compile((ROOT / 'scripts/suites' / SUITE).read_text(), SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    details = [line.strip() for line in out.getvalue().split('\n') if PREFIX.strip() in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]], 'details': details,
            'preamble_rows': len(rows) - len(mine)}


def run(root):
    started = time.monotonic()
    proc = subprocess.run([sys.executable, '-B', __file__, '--one', str(root)], capture_output=True, text=True,
                          timeout=1200)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _raised(observed):
    """Whether a fixture part did not run to its end (a row's guard records what it raised)."""
    return any('did not run to its end' in d or 'the row ran to its end (' in d for d in observed['details'])


def _tree(commit, directory):
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    tree = Path(directory)
    tree.mkdir(parents=True)
    archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
    return resolved, tree


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive."""
    with tempfile.TemporaryDirectory(prefix='v205-red-') as directory:
        resolved, tree = _tree(commit, Path(directory) / 'tree')
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        observed = run(tree)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0205', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite file run against it' % resolved, modules=modules,
                  by_assertion=not _raised(observed), **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'by_assertion': report['by_assertion'],
                      'written': name}))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    if len(sys.argv) >= 3 and sys.argv[1] == '--one':
        print(json.dumps(one(sys.argv[2])))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    head = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', 'HEAD^{commit}'],
                            capture_output=True, text=True, check=True).stdout.strip()
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0205', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'commit': head, 'mutants': []}

    def measured(case=None, module=None):
        """One run over a fresh tree of HEAD: unchanged, with `module` copied unchanged, or with `case`
        applied; the tree is removed after its run, so at most two exist at once."""
        with tempfile.TemporaryDirectory(prefix='v205-drive-') as directory:
            _, tree = _tree(head, Path(directory) / 'tree')
            extra = {}
            if case is not None:
                path = tree / '.veldo' / case['module']
                source = path.read_text()
                mutant = ctm.mutate(source, case)
                path.write_text(mutant)
                (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                    source.splitlines(keepends=True), mutant.splitlines(keepends=True),
                    n=0, fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module'])))
                extra = dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                             mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest())
            elif module is not None:
                path = tree / '.veldo' / module
                path.write_bytes(path.read_bytes())
                extra = dict(source_sha256=_sha(path), copy_sha256=_sha(path))
            return dict(run(tree), **extra)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        baseline = pool.submit(measured)
        noop = {module: pool.submit(measured, module=module) for module in sorted({c['module'] for c in cases})}
        pending = [(case, pool.submit(measured, case=case)) for case in cases]
        report['baseline'] = baseline.result()
        report['noop'] = {module: future.result() for module, future in noop.items()}
        for case, future in pending:
            observed = future.result()
            report['mutants'].append(dict(observed, name=case['name'], module='.veldo/' + case['module'],
                                          named_rows=case['rows'], diff='proof/VELDO-0205/%s.diff' % case['name'],
                                          by_assertion=not _raised(observed),
                                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in case['rows'])))
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
