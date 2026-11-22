"""Developer diagnostic using the registered teeth materializer and worker.

This does not replace the confined gate mutation driver or produce gate evidence.
It can run on compute nodes whose Python has no pidfd support.
"""
import argparse
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
driver = ROOT / 'scripts/check_teeth_mutations.py'
registry = runpy.run_path(str(driver))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case', action='append', help='registered case name (default: finding 258)')
args = parser.parse_args()
selected = [case for case in registry['cases']()
            if case['name'] in args.case] if args.case else [case for case in registry['cases']() if case['finding'] == 258]
if args.case and {case['name'] for case in selected} != set(args.case):
    parser.error('unknown registered case')
failed = False
for case in selected:
    for mode in ('baseline', 'noop', 'mutant'):
        with tempfile.TemporaryDirectory(prefix='outside-teeth-') as directory:
            material = registry['materialize'](case, mode, directory, root=ROOT)
            argv = [sys.executable, '-B', str(driver), '--worker', case['name']]
            if material['mutant']:
                argv += ['--mutant', str(material['mutant'])]
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=1200)
            try:
                report = json.loads(result.stdout)
                targets = report['targets']
                observed = [entry for entries in targets.values() for entry in entries]
                valid = result.returncode == 0 and bool(observed) and all(targets.values())
                valid = valid and (not all(observed) if mode == 'mutant' else not report['failed_rows'])
                print(json.dumps(dict(case=case['name'], mode=mode, targets=targets,
                                      failed_rows=report['failed_rows'], matched=bool(valid))), flush=True)
            except (ValueError, KeyError):
                valid = False
                print(json.dumps(dict(case=case['name'], mode=mode, matched=False,
                                      error='worker_did_not_return_rows', exit=result.returncode)), flush=True)
                print(result.stderr, file=sys.stderr)
            failed |= not valid
raise SystemExit(1 if failed else 0)
