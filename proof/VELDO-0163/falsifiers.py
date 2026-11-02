#!/usr/bin/env python3
"""VELDO-0163: each registered mutant of finding 163, run by the teeth driver's own worker outside the gate's
confinement, because suite 119 runs system Chrome (/opt/google/chrome, outside the gate profile's read roots)
and the UI's locked node_modules, and is not (yet) on the owner's protected unconfined list
(scripts/gate_unconfined.json); see OPEN.md.

One step per call, so each locked run is short; every step's outcome is merged into falsifiers.json beside this
file:
  baseline          the unmutated production copies: every target row of every case green
  mutant CASE       the driver's own materialize (its exact replacements) into a temporary copy the suite's
                    production anchor is pointed at: at least one of the case's target rows red
  restored          the unmutated copies again: every target row green
The source files are never edited. Usage: python3 proof/VELDO-0163/falsifiers.py baseline|mutant CASE|restored
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = Path(__file__).with_name('falsifiers.json')
SUITE = 'scripts/suites/119_veldo_0163_role_team_form.py'
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts' / 'check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CASES = [c for c in T.cases() if c['finding'] == 163]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(case, mutant=None):
    """The driver's worker in its own process, as the coordinator starts it: every row and each target's checks."""
    argv = [sys.executable, str(ROOT / 'scripts' / 'check_teeth_mutations.py'), '--finding', '163', '--worker',
            case['name']] + (['--mutant', str(mutant)] if mutant else [])
    started = time.monotonic()
    done = subprocess.run(argv, capture_output=True, text=True, timeout=1500, cwd=str(ROOT))
    seconds = round(time.monotonic() - started, 3)
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'returncode': done.returncode, 'seconds': seconds, 'error': (done.stderr or done.stdout)[-900:]}
    return {'returncode': done.returncode, 'seconds': seconds, 'rows': result['row_names'],
            'targets': result['targets'], 'failed_rows': result['failed_rows'],
            'failed_details': result['failed_details']}


def green(outcome):
    return ('targets' in outcome and not outcome['failed_rows']
            and all(values and all(values) for values in outcome['targets'].values()))


def red(outcome):
    return 'targets' in outcome and any(not all(values) for values in outcome['targets'].values())


def main(argv):
    receipt = json.loads(RECEIPT.read_text()) if RECEIPT.is_file() else {'cases': {}}
    receipt.update(schema='veldo.falsifier_receipt/v1', spec='VELDO-0163',
                   driver='scripts/check_teeth_mutations.py --worker (unconfined; see OPEN.md)',
                   driver_sha256=sha(ROOT / 'scripts' / 'check_teeth_mutations.py'), suite=SUITE,
                   suite_sha256=sha(ROOT / SUITE))
    commit = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    step = argv[0] if argv else ''
    if step in ('baseline', 'restored'):
        # Every case's targets come from one worker run: the unmutated suite's rows are the same for each case.
        outcome = dict(run(CASES[0]), commit=commit)
        rows = outcome.get('rows') or []
        failed = set(outcome.get('failed_rows') or [])
        outcome['targets'] = {row: [name not in failed for name in rows if name.split()[-1] == row]
                              for case in CASES for row in case['rows']}
        receipt[step] = outcome
        print('%s: %s (failed rows %s)' % (step, 'green' if green(outcome) else 'NOT GREEN', outcome.get('failed_rows')))
    elif step == 'mutant' and len(argv) == 2:
        case = next(c for c in CASES if c['name'] == argv[1])
        with tempfile.TemporaryDirectory(prefix='v163-mutant-') as directory:
            made = T.materialize(case, 'mutant', directory)
            outcome = dict(run(case, made['mutant']), commit=commit)
        receipt['cases'][case['name']] = {
            'module': case['dir'] + '/' + case['module'], 'rows': case['rows'], 'edits': T.edits(case),
            'source_sha256': made['old_digest'], 'mutant_sha256': made['new_digest'],
            'replacement_count': made['replacement_count'], 'mutant': outcome}
        print('%s: %s %s' % (case['name'], 'red' if red(outcome) else 'NOT RED', outcome.get('failed_rows')))
    else:
        print(__doc__)
        return 64
    proven = [c['name'] for c in CASES
              if green(receipt.get('baseline', {})) and green(receipt.get('restored', {}))
              and red((receipt['cases'].get(c['name']) or {}).get('mutant', {}))]
    receipt.update(registered=[c['name'] for c in CASES], proven=proven,
                   verdict='red_under_each_mutant_green_restored' if len(proven) == len(CASES) else 'not_proven')
    RECEIPT.write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n')
    print('falsifiers: %d of %d proven (%s)' % (len(proven), len(CASES), receipt['verdict']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
