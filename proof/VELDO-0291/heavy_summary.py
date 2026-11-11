#!/usr/bin/env python3
"""VELDO-0291: the heavy runs behind the proof, each kept as one small summary.

Run by proof/VELDO-0291/heavy_runs.sh from the repository root, under the gate lock:

  python3 proof/VELDO-0291/heavy_summary.py red-before --scratch <dir> [--base 646ff7c8]
  python3 proof/VELDO-0291/heavy_summary.py green-after --scratch <dir> [--runs 3]
  python3 proof/VELDO-0291/heavy_summary.py teeth --scratch <dir> [--jobs 3]

red-before  Suite 86 as built, run in a scratch checkout of the base commit with one criterion's
            behavior put back as it is there, once per criterion. The criterion's row must be red on
            the checks the criterion names. A row red because its section raised does not count.
green-after Suite 86 as built, run in this checkout.
teeth       The registered mutants of finding 291 through scripts/check_teeth_mutations.py. The summary
            quotes, for every mutant, the false labels its target row printed.

Each step writes proof/VELDO-0291/<step>.summary.json (veldo.proof-summary/v1). Every raw file it
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
SUITE = '86_veldo_0189_engine_upgrade'
SUITE_FILE = 'scripts/suites/%s.py' % SUITE
SUPPORT_FILE = 'scripts/suites/support/v171_tailscale.py'
SUITE_COMMAND = ['python3', 'scripts/selftest.py', '--suite', SUITE]
RAISED = 'the section ran to its end (it raised'
ROWS = {'AC1': 'port/held-for-the-run', 'AC2': 'start/failure-recorded',
        'AC3': 'restart/adoption-start-checked'}
# The checks each criterion names for its red-before, by the words their labels begin with.
NAMED = {
    'AC1': ['the socket the suite holds is open',
            'while the child holds its socket, a plain bind of its port without SO_REUSEADDR fails'],
    'AC2': ["refused bind: the API unit's start is recorded once",
            "late start: the fixture unit's start is recorded once"],
    'AC3': ['the last check the row recorded is the start check'],
}
PUT_BACK = {
    'AC1': 'reserved_port() returns the port free_port() gives and a closed socket',
    'AC2': 'Manager.start is the text of the base commit: no records, the unit log never read',
    'AC3': 'without_signer makes no check of its start (the edit of mutant start291-signer-start-unchecked)',
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def swap(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit('VELDO-0291 %s: the text to replace occurs %d times, not once' % (what, text.count(old)))
    return text.replace(old, new)


def between(text, first, last, what):
    """The part of `text` from the line `first` up to the line `last`, each occurring once."""
    for mark in (first, last):
        if text.count(mark) != 1:
            raise SystemExit('VELDO-0291 %s: marker %r occurs %d times, not once' % (what, mark, text.count(mark)))
    return text[text.index(first):text.index(last)]


def run_suite(cwd, log, env=None):
    with open(log, 'wb') as out:
        done = subprocess.run(SUITE_COMMAND, cwd=str(cwd), stdout=out, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=env)
    return done.returncode


def read_run(log):
    """What one suite run printed: the suite's counts, its false rows and each one's false labels."""
    text = Path(log).read_text(errors='replace')
    found = {'passed': None, 'failed': None, 'seconds': None, 'red': {}}
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
    # selftest prints a suite's passed count only; its failed rows are the SELFTEST FAIL lines.
    found['failed'] = len(found['red'])
    return found


def raw(paths, scratch):
    return [(str(Path(p).relative_to(scratch)), Path(p).read_bytes()) for p in paths if Path(p).is_file()]


def write(V, name, command, deciding, discarded):
    path = HERE / (name + '.summary.json')
    V.write_proof_summary(path, command, deciding, discarded=discarded, root=ROOT, timing=True)
    print('VELDO-0291 %s: %s -> %s' % (name, deciding['verdict'], path.relative_to(ROOT)))
    return 0 if deciding['verdict'] == 'pass' else 1


def red_before(V, args):
    git = load('v291_git_process', ROOT / '.veldo/git_process.py')
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    tree = scratch / 'tree'
    base = git.run(['git', '-C', str(ROOT), 'rev-parse', args.base + '^{commit}'], capture_output=True, text=True,
                   check=True).stdout.strip()
    git.run(['git', 'clone', '-q', '--no-checkout', str(ROOT), str(tree)], capture_output=True, check=True)
    git.run(['git', '-C', str(tree), 'checkout', '-q', '--detach', base], capture_output=True, check=True)
    variants = put_back((tree / SUITE_FILE).read_text())
    results, logs = [], []
    for criterion in sorted(variants):
        suite_text, support_text = variants[criterion]
        (tree / SUITE_FILE).write_text(suite_text)
        (tree / SUPPORT_FILE).write_text(support_text)
        log = scratch / ('red-before-%s.log' % criterion)
        code = run_suite(tree, log)
        logs.append(log)
        seen, row = read_run(log), ROWS[criterion]
        labels = seen['red'].get(row)
        named = [mark for mark in NAMED[criterion] if any(label.startswith(mark) for label in labels or [])]
        raised = any(RAISED in label for label in labels or [])
        results.append({
            'criterion': criterion, 'row': row, 'put_back': PUT_BACK[criterion],
            'suite_sha256': hashlib.sha256(suite_text.encode()).hexdigest(),
            'support_sha256': hashlib.sha256(support_text.encode()).hexdigest(),
            'returncode': code, 'suite_passed': seen['passed'], 'suite_failed': seen['failed'],
            'row_red': labels is not None, 'row_raised': raised,
            'named_checks_false': named, 'named_checks_required': NAMED[criterion],
            'false_labels': [label[:400] for label in (labels or [])[:6]],
            'other_red_rows': sorted(name for name in seen['red'] if name != row),
            'verdict': 'red-before' if labels is not None and not raised and named == NAMED[criterion]
                       else 'not red-before',
        })
    deciding = {
        'base': base, 'bound': 'for every criterion: its row is red, every check the criterion names is among the '
                               'row\'s false labels, and no false label of the row says its section raised',
        'what_ran': 'suite 86 and its support file as built, in a scratch checkout of the base commit, with the '
                    'one criterion\'s behavior put back as it is at the base commit',
        'variants': results,
        'verdict': 'pass' if all(one['verdict'] == 'red-before' for one in results) else 'fail',
    }
    command = ('systemd-run --user --scope -p MemoryMax=10G python3 proof/VELDO-0291/heavy_summary.py red-before '
               '--base %s; per criterion, in the scratch checkout: %s' % (args.base, ' '.join(SUITE_COMMAND)))
    return write(V, 'red-before', command, deciding, raw(logs, scratch))


def put_back(base_suite):
    """{criterion: (suite text, support text)}: the built suite and support file with that one criterion's
    behavior as it is at the base commit, whose suite text is `base_suite`."""
    built_suite, built_support = (ROOT / SUITE_FILE).read_text(), (ROOT / SUPPORT_FILE).read_text()
    stop = '        def stop(self, unit):\n'
    driver = load('v291_teeth', ROOT / 'scripts/check_teeth_mutations.py')
    unchecked = next(c for c in driver.cases() if c['name'] == 'start291-signer-start-unchecked')
    return {
        'AC1': (built_suite, swap(
            built_support,
            "    held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    held.bind(('127.0.0.1', 0))\n"
            "    held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
            "    return held.getsockname()[1], held\n",
            "    port = free_port()\n"
            "    held = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    held.close()\n"
            "    return port, held\n", 'AC1 put-back')),
        'AC2': (swap(
            built_suite,
            between(built_suite, '        def record(self, unit, code, error, began, proc=None, offset=0):\n', stop,
                    'AC2 put-back, the built suite'),
            between(base_suite, '        def start(self, unit):\n', stop, 'AC2 put-back, the base suite'),
            'AC2 put-back'), built_support),
        'AC3': (driver.mutate(built_suite, unchecked), built_support),
    }


def green_after(V, args):
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    runs, files = [], []
    for number in range(1, args.runs + 1):
        log, timing = scratch / ('green-%02d.log' % number), scratch / ('green-%02d-rows.json' % number)
        code = run_suite(ROOT, log, env=dict(os.environ, VELDO_ROW_TIMINGS=str(timing)))
        files += [log, timing]
        seen = read_run(log)
        try:
            measured = json.loads(timing.read_text())
        except (OSError, ValueError):
            measured = {}
        adoption = measured.get('adoption') or {}
        starts = adoption.get('starts') or []
        row_seconds = {row: (measured.get('rows') or {}).get(row) for row in sorted(ROWS.values())}
        runs.append({
            'run': number, 'returncode': code, 'suite_passed': seen['passed'], 'suite_failed': seen['failed'],
            'red_rows': sorted(seen['red']), 'suite_seconds': measured.get('seconds'),
            'row_seconds': row_seconds, 'api_port': adoption.get('api_port'),
            'adoption_starts': len(starts), 'adoption_failed_starts': sum(1 for one in starts if one.get('code')),
            'verdict': 'green' if seen['failed'] == 0 and seen['passed'] and not seen['red']
                       and all(isinstance(v, float) and v > 0 for v in row_seconds.values()) else 'not green',
        })
    deciding = {
        'bound': 'every run: suite 86 reports no failed row, and each of the three VELDO-0291 rows took time in '
                 'the row timings file, so it ran. selftest --suite exits 2 by design (a partial run)',
        'runs': runs, 'verdict': 'pass' if runs and all(one['verdict'] == 'green' for one in runs) else 'fail',
    }
    command = ('systemd-run --user --scope -p MemoryMax=10G python3 proof/VELDO-0291/heavy_summary.py green-after '
               '--runs %d --name %s; per run: VELDO_ROW_TIMINGS=<scratch file> %s'
               % (args.runs, args.name, ' '.join(SUITE_COMMAND)))
    return write(V, args.name, command, deciding, raw(files, scratch))


def teeth(V, args):
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True)
    driver = load('v291_teeth', ROOT / 'scripts/check_teeth_mutations.py')
    registered = {c['name']: c for c in driver.cases() if c['finding'] == 291}
    log, workers, diffs = scratch / 'teeth.log', scratch / 'workers', scratch / 'diffs'
    driver_summary = scratch / 'driver.summary.json'
    command = ['python3', 'scripts/check_teeth_mutations.py', '--finding', '291', '--jobs', str(args.jobs)]
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
        quoted = [words[:600] for name, words in mutant.get('failed_details') or []
                  if name.split()[-1] in targets][:4]
        cases.append({'case': case.get('name'), 'target_rows': targets, 'expected': 'killed', 'observed': 'killed',
                      'source': result.get('source'), 'replacement_count': result.get('replacement_count'),
                      'baseline_rows': (result.get('baseline') or {}).get('count'),
                      'baseline_red_rows': (result.get('baseline') or {}).get('failed_rows'),
                      'mutant_red_rows': len(mutant.get('failed_rows') or []),
                      'target_row_false_labels': quoted})
    for result in receipt.get('invalid_results') or []:
        case = result.get('case') or {}
        cases.append({'case': case.get('name'), 'target_rows': case.get('rows'), 'expected': 'killed',
                      'observed': result.get('error') or 'invalid', 'red': str(result.get('detail'))[:1200]})
    cases.sort(key=lambda one: str(one['case']))
    killed = sorted(one['case'] for one in cases if one['observed'] == 'killed')
    deciding = {
        'bound': 'the stage passed, every mutant registered under finding 291 was run and killed on its target '
                 'row, and each kill quotes a false label of that row',
        'registered': sorted(registered), 'returncode': done.returncode,
        'counts': {key: receipt.get(key) for key in ('status', 'registered', 'executed', 'reused', 'rejected',
                                                      'worker_invocations', 'elapsed', 'error') if key in receipt},
        'cases': cases,
        'verdict': 'pass' if (done.returncode == 0 and receipt.get('status') == 'passed'
                              and killed == sorted(registered)
                              and all(one.get('target_row_false_labels') for one in cases)) else 'fail',
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
    parser.add_argument('--base', default='646ff7c8')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--name', default='green-after', choices=('green-after', 'offline-suite'),
                        help='green-after only: the summary to write (offline-suite is the builder\'s one quick run)')
    parser.add_argument('--jobs', type=int, default=3)
    args = parser.parse_args()
    V = load('v291_validate', ROOT / '.veldo/validate.py')
    return {'red-before': red_before, 'green-after': green_after, 'teeth': teeth}[args.step](V, args)


if __name__ == '__main__':
    sys.exit(main())
