#!/usr/bin/env python3
"""VELDO-0161 round 6: drive_signer.py once over the modules as they are and once with finding 161's
upgrade161-adoption-signer-not-laid applied, and record both.

    python3 proof/VELDO-0161/round6/run_falsifier.py [<output.json>]

The mutant is made by scripts/check_teeth_mutations.py's own materialize (the exact registered replacement, the
source never edited) into a copy of engine/.veldo. Unmutated, every check holds. Under the mutant, only the
prepare check fails: the upgrade's prepare step no longer lays the signer, while the two functions it calls
still work when called directly. The case's registered rows are suite 86's, which run on the host.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CASE = 'upgrade161-adoption-signer-not-laid'


def drive(mods):
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('drive_signer.py')), str(mods)],
                          capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    try:
        report = json.loads(done.stdout)
    except ValueError:
        report = {'error': done.stderr[-600:]}
    return dict(exit=done.returncode, failed=[label for label, ok in report.get('checks', []) if not ok],
                passed=report.get('passed'), error=report.get('error'))


def main(argv):
    spec = importlib.util.spec_from_file_location('r6_teeth', str(ROOT / 'scripts/check_teeth_mutations.py'))
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    case = next(c for c in teeth.cases() if c['name'] == CASE)
    scratch = Path(tempfile.mkdtemp(prefix='r6-falsifier-', dir=os.environ.get('TMPDIR')))
    try:
        made = teeth.materialize(case, 'mutant', scratch / 'mutant')
        mods = scratch / 'veldo'
        shutil.copytree(str(ROOT / 'engine' / '.veldo'), str(mods), ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(str(made['mutant']), str(mods / case['module']))
        baseline, mutant = drive(ROOT / 'engine' / '.veldo'), drive(mods)
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    killed = (baseline['exit'] == 0 and not baseline['failed'] and mutant['exit'] == 1
              and len(mutant['failed']) == 1 and mutant['failed'][0].startswith('prepare: the engine upgrade'))
    report = {'schema': 'veldo.falsifier-run/v1', 'spec_id': 'VELDO-0161', 'round': 6, 'case': CASE,
              'registered_rows': case['rows'], 'registered_suite': case['suite'],
              'replacement_count': made['replacement_count'], 'old_digest': made['old_digest'],
              'new_digest': made['new_digest'], 'baseline': baseline, 'mutant': mutant, 'killed_here': killed,
              'note': 'the registered rows are suite 86\'s, which need the host\'s user manager; this run is the sandbox '
                      'falsifier of the same replacement over the step it removes'}
    text = json.dumps(report, indent=1) + '\n'
    if argv:
        Path(argv[0]).write_text(text)
    print(text, end='')
    return 0 if killed else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
