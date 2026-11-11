#!/usr/bin/env python3
"""VELDO-0117: the runs behind the proof, each kept as one small summary.

Run by proof/VELDO-0117/heavy_runs.sh from the repository root, under the gate lock:

  python3 proof/VELDO-0117/heavy_summary.py red-before --scratch <dir> [--base f6b8ae41]
  python3 proof/VELDO-0117/heavy_summary.py green-after --scratch <dir> [--runs 3]
  python3 proof/VELDO-0117/heavy_summary.py teeth --scratch <dir> [--jobs 3]

red-before  The suite as built, run in a scratch checkout of this commit whose three product
            modules are the base commit's. Every row must be red on the checks named below, and
            no row may be red because its section raised.
green-after The suite as built, run in this checkout.
teeth       The registered mutants of finding 117 through scripts/check_teeth_mutations.py. The
            summary quotes, for every mutant, the false labels its target row printed.

Each step writes proof/VELDO-0117/<step>.summary.json (veldo.proof-summary/v1). Every raw file it
produced is named there with its size and sha256, and is left in <dir> for the caller to delete.
The exit code is 0 only when the step's verdict is pass.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SUITE = '113_veldo_0117_domain_store'
SUITE_COMMAND = ['python3', 'scripts/selftest.py', '--suite', SUITE]
MODULES = ('.veldo/control_store.py', '.veldo/control_client.py', '.veldo/control_enrollment.py')
RAISED = 'the section ran to its end (it raised'
ROWS = {'AC1': 'enrollment/authority-refuses-domain-store-conflict',
        'AC2': 'enrollment/one-domain-one-winner',
        'AC3': 'enrollment/domain-binding-survives-restart'}
SCHEDULES = ['%s, %s first' % (kind, clone) for kind in ('one after the other', 'overlapped') for clone in 'ab']
# The checks that must be false on the base code, by the words their labels begin with.
NAMED = {
    'AC1': ['domain equal, uuid %s, location %s is conflict' % cell
            for cell in (('equal', 'unequal'), ('unequal', 'equal'), ('unequal', 'unequal'))],
    'AC2': ['%s: the first store is registered and the second is told domain_store_conflict' % schedule
            for schedule in SCHEDULES],
    'AC3': ['%s, restarted %s first, the conflicting store: it is told domain_store_conflict again'
            % (schedule, order) for schedule in SCHEDULES for order in ('matching', 'conflicting')],
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_suite(cwd, log, report):
    with open(log, 'wb') as out:
        done = subprocess.run(SUITE_COMMAND, cwd=str(cwd), stdout=out, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=dict(os.environ, VELDO_0117_REPORT=str(report)))
    return done.returncode


def read_run(log, report):
    """What one suite run printed and reported: its counts, its false rows and each one's false labels."""
    text = Path(log).read_text(errors='replace')
    found = {'passed': None, 'seconds': None, 'red': {}, 'report': {}}
    for line in text.splitlines():
        line = line.strip()
        match = re.match(r'SELFTEST FAIL: (VELDO-\d+) (\S+?)(?::\s.*)?$', line)
        if match:
            found['red'].setdefault(match.group(2), [])
            continue
        match = re.match(r'VELDO-\d+ (\S+) detail: (.*)$', line)
        if match:
            found['red'].setdefault(match.group(1), []).append(match.group(2))
            continue
        match = re.match(re.escape(SUITE) + r'\s+(\d+) passed\s+([\d.]+)s$', line)
        if match:
            found['passed'], found['seconds'] = int(match.group(1)), float(match.group(2))
    try:
        found['report'] = json.loads(Path(report).read_text())
    except (OSError, ValueError):
        pass
    return found


def raw(paths, scratch):
    return [(str(Path(p).relative_to(scratch)), Path(p).read_bytes()) for p in paths if Path(p).is_file()]


def write(V, name, command, deciding, discarded):
    path = HERE / (name + '.summary.json')
    V.write_proof_summary(path, command, deciding, discarded=discarded, root=ROOT, timing=True)
    print('VELDO-0117 %s: %s -> %s' % (name, deciding['verdict'], path.relative_to(ROOT)))
    return 0 if deciding['verdict'] == 'pass' else 1


def red_before(V, args):
    git = load('v117_git_process', ROOT / '.veldo/git_process.py')
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    tree = scratch / 'tree'

    def run(*command):
        return git.run(list(command), capture_output=True, text=True, check=True).stdout.strip()
    base = run('git', '-C', str(ROOT), 'rev-parse', args.base + '^{commit}')
    built = run('git', '-C', str(ROOT), 'rev-parse', 'HEAD')
    run('git', 'clone', '-q', '--no-checkout', str(ROOT), str(tree))
    run('git', '-C', str(tree), 'checkout', '-q', '--detach', built)
    run('git', '-C', str(tree), 'checkout', '-q', base, '--', *MODULES)
    log, report = scratch / 'red-before.log', scratch / 'red-before-report.json'
    code = run_suite(tree, log, report)
    seen = read_run(log, report)
    rows = []
    for criterion in sorted(ROWS):
        row = ROWS[criterion]
        labels = seen['red'].get(row)
        named = [mark for mark in NAMED[criterion] if any(label.startswith(mark) for label in labels or [])]
        raised = any(RAISED in label for label in labels or [])
        rows.append({
            'criterion': criterion, 'row': row, 'row_red': labels is not None, 'row_raised': raised,
            'false_checks': len(labels or []), 'named_checks_required': NAMED[criterion],
            'named_checks_false': named, 'false_labels': [label[:400] for label in (labels or [])[:4]],
            'verdict': 'red-before' if labels is not None and not raised and named == NAMED[criterion]
                       else 'not red-before',
        })
    deciding = {
        'base': base, 'built': built,
        'bound': 'for every criterion: its row is red, every check named for it is among the row\'s false labels, '
                 'and no false label of the row says its section raised',
        'what_ran': 'the suite as built, in a scratch checkout of the built commit whose three product modules '
                    'are the base commit\'s',
        'base_module_sha256': {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in MODULES},
        'authority_module_sha256': seen['report'].get('module_sha256'),
        'fixture_version': seen['report'].get('fixture_version'),
        'returncode': code, 'suite_passed': seen['passed'], 'suite_seconds': seen['seconds'],
        'other_red_rows': sorted(name for name in seen['red'] if name not in ROWS.values()),
        'rows': rows,
        'verdict': 'pass' if all(one['verdict'] == 'red-before' for one in rows) else 'fail',
    }
    command = ('systemd-run --user --scope -p MemoryMax=10G python3 proof/VELDO-0117/heavy_summary.py red-before '
               '--base %s; in the scratch checkout: VELDO_0117_REPORT=<scratch file> %s'
               % (args.base, ' '.join(SUITE_COMMAND)))
    return write(V, 'red-before', command, deciding, raw([log, report], scratch))


def green_after(V, args):
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    runs, files = [], []
    for number in range(1, args.runs + 1):
        log, report = scratch / ('green-%02d.log' % number), scratch / ('green-%02d-report.json' % number)
        code = run_suite(ROOT, log, report)
        files += [log, report]
        seen = read_run(log, report)
        told = seen['report']
        rows = told.get('rows') or {}
        runs.append({
            'run': number, 'returncode': code, 'suite_passed': seen['passed'], 'suite_seconds': seen['seconds'],
            'red_rows': sorted(seen['red']), 'rows': rows, 'checks_made_and_true': told.get('checks'),
            'authority_module_sha256': told.get('module_sha256'), 'fixture_version': told.get('fixture_version'),
            'cases': {row: len(found) for row, found in (told.get('records') or {}).items()},
            'verdict': 'green' if (seen['passed'] and not seen['red'] and sorted(rows) == sorted(ROWS.values())
                                   and all(rows.values())) else 'not green',
        })
    deciding = {
        'bound': 'every run: the suite reports no failed row and its report shows each of the three rows true, '
                 'with the number of checks each made. selftest --suite exits 2 by design (a partial run)',
        'runs': runs, 'verdict': 'pass' if runs and all(one['verdict'] == 'green' for one in runs) else 'fail',
    }
    command = ('systemd-run --user --scope -p MemoryMax=10G python3 proof/VELDO-0117/heavy_summary.py green-after '
               '--runs %d --name %s; per run: VELDO_0117_REPORT=<scratch file> %s'
               % (args.runs, args.name, ' '.join(SUITE_COMMAND)))
    return write(V, args.name, command, deciding, raw(files, scratch))


def teeth(V, args):
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    driver = load('v117_teeth', ROOT / 'scripts/check_teeth_mutations.py')
    registered = {c['name']: c for c in driver.cases() if c['finding'] == 117}
    log, workers, diffs = scratch / 'teeth.log', scratch / 'workers', scratch / 'diffs'
    driver_summary = scratch / 'driver.summary.json'
    command = ['python3', 'scripts/check_teeth_mutations.py', '--finding', '117', '--jobs', str(args.jobs)]
    with open(log, 'wb') as out:
        done = subprocess.run(command + ['--worker-log-dir', str(workers), '--diff-dir', str(diffs),
                                         '--summary', str(driver_summary)],
                              cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    receipt = {}
    for line in reversed(log.read_text(errors='replace').splitlines()):
        if line.startswith('{'):
            try:
                receipt = json.loads(line)
            except ValueError:
                continue
            if isinstance(receipt, dict) and 'results' in receipt:
                break
            receipt = {}
    cases = []
    for result in receipt.get('results') or []:
        case, mutant = result.get('case') or {}, result.get('mutant') or {}
        targets = case.get('rows') or []
        quoted = [words[:500] for name, words in mutant.get('failed_details') or []
                  if name.split()[-1] in targets][:3]
        cases.append({'case': case.get('name'), 'module': case.get('module'), 'target_rows': targets,
                      'expected': 'killed', 'observed': 'killed', 'source': result.get('source'),
                      'replacement_count': result.get('replacement_count'),
                      'baseline_rows': (result.get('baseline') or {}).get('count'),
                      'baseline_red_rows': (result.get('baseline') or {}).get('failed_rows'),
                      'mutant_red_rows': sorted(name.split()[-1] for name in mutant.get('failed_rows') or []),
                      # A row red because its section raised is a failed drive, not a detected falsifier.
                      'target_row_raised': any(RAISED in words for name, words in mutant.get('failed_details') or []
                                               if name.split()[-1] in targets),
                      'target_row_false_labels': quoted})
    for result in receipt.get('invalid_results') or []:
        case = result.get('case') or {}
        cases.append({'case': case.get('name'), 'target_rows': case.get('rows'), 'expected': 'killed',
                      'observed': result.get('error') or 'invalid', 'red': str(result.get('detail'))[:1200]})
    cases.sort(key=lambda one: str(one['case']))
    killed = sorted(one['case'] for one in cases if one['observed'] == 'killed')
    deciding = {
        'bound': 'the stage passed, every mutant registered under finding 117 was run and killed on its target '
                 'row, each kill quotes a false label of that row, and no target row was red because its '
                 'section raised',
        'registered': sorted(registered), 'returncode': done.returncode,
        'counts': {key: receipt.get(key) for key in ('status', 'registered', 'executed', 'reused', 'rejected',
                                                      'worker_invocations', 'elapsed', 'error') if key in receipt},
        'diff_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(diffs.iterdir())} if diffs.is_dir() else {},
        'cases': cases,
        'verdict': 'pass' if (done.returncode == 0 and receipt.get('status') == 'passed'
                              and killed == sorted(registered)
                              and all(one.get('target_row_false_labels') and not one.get('target_row_raised')
                                      for one in cases)) else 'fail',
    }
    # The run's own output: the stage log, the driver's summary, each worker's output streams and ledger, and
    # each applied diff. A worker's home below the log directory holds copies of the tree and is not output.
    files = [log, driver_summary] + sorted(p for d in (workers, diffs) if d.is_dir() for p in d.iterdir()
                                           if p.is_file() and not p.is_symlink())
    return write(V, 'teeth', 'systemd-run --user --scope -p MemoryMax=10G ' + ' '.join(command)
                 + ' --worker-log-dir <scratch> --diff-dir <scratch> --summary <scratch file>', deciding,
                 raw(files, scratch))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=('red-before', 'green-after', 'teeth'))
    parser.add_argument('--scratch', required=True, help='a directory that does not exist yet, for the raw output')
    parser.add_argument('--base', default='f6b8ae41')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--name', default='green-after', choices=('green-after', 'offline-suite'),
                        help='green-after only: the summary to write (offline-suite is the builder\'s one quick run)')
    parser.add_argument('--jobs', type=int, default=3)
    args = parser.parse_args()
    V = load('v117_validate', ROOT / '.veldo/validate.py')
    return {'red-before': red_before, 'green-after': green_after, 'teeth': teeth}[args.step](V, args)


if __name__ == '__main__':
    sys.exit(main())
