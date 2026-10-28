#!/usr/bin/env python3
"""VELDO-0161 round 7: drive_points.py and drive_signer.py over the modules as they are, with the round-7 fix
reverted, and with finding 161's upgrade161-adoption-signer-not-laid applied; record all three.

    python3 proof/VELDO-0161/round7/run_falsifier.py [<output.json>]

The revert puts back round 6's second fetch of the upgrade module inside lay_adoption_signer (the call is
otherwise unchanged), so suite 86's kill driver wraps `point` twice from there on: drive_points goes red at
every kill point after the first adoption point, and drive_signer stays green (the signer is still laid). The
registered mutant is made by scripts/check_teeth_mutations.py's own materialize from its round-7 anchor (the
two-line call); under it both drivers' prepare checks go red. The registered rows are suite 86's, on the host.
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
FIXED = ("    a run killed at any of them is finished by the next: the key is generated beside its place and renamed into\n"
         "    it (its public half first), and each signers file is written whole to a new file renamed over it (UP.replace,\n"
         "    `UP` the upgrade module the caller's inspection loaded, never a second load of it). A second run finds\n"
         "    everything laid and writes nothing.\"\"\"\n")
REVERTED = FIXED + "    UP = organ('control_factory_setup_upgrade')\n"


def drive(script, mods):
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name(script)), str(mods)],
                          capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    try:
        report = json.loads(done.stdout)
    except ValueError:
        report = {'error': done.stderr[-600:]}
    return dict(exit=done.returncode, failed=[label for label, ok in report.get('checks', []) if not ok],
                passed=report.get('passed'), error=report.get('error'))


def both(mods):
    return {'drive_points': drive('drive_points.py', mods), 'drive_signer': drive('drive_signer.py', mods)}


def main(argv):
    spec = importlib.util.spec_from_file_location('r7_teeth', str(ROOT / 'scripts/check_teeth_mutations.py'))
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    case = next(c for c in teeth.cases() if c['name'] == CASE)
    scratch = Path(tempfile.mkdtemp(prefix='r7-falsifier-', dir=os.environ.get('TMPDIR')))
    try:
        def copy(name, module_text):
            mods = scratch / name
            shutil.copytree(str(ROOT / 'engine' / '.veldo'), str(mods), ignore=shutil.ignore_patterns('__pycache__'))
            (mods / 'control_factory_setup.py').write_text(module_text)
            return mods
        source = (ROOT / 'engine' / '.veldo' / 'control_factory_setup.py').read_text()
        reverted_count = source.count(FIXED)
        reverted = copy('reverted', source.replace(FIXED, REVERTED))
        made = teeth.materialize(case, 'mutant', scratch / 'mutant')
        mutant = copy('mutant-veldo', Path(made['mutant']).read_text())
        runs = {'baseline': both(ROOT / 'engine' / '.veldo'), 'fix_reverted': both(reverted),
                'registered_mutant': both(mutant)}
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    base, rev, mut = runs['baseline'], runs['fix_reverted'], runs['registered_mutant']
    killed = {
        'baseline_green': all(r['exit'] == 0 and not r['failed'] for r in base.values()),
        'fix_reverted_red_on_kill_points': (reverted_count == 1 and rev['drive_points']['exit'] == 1
                                            and any(f.startswith("suite 86's kill at") for f in rev['drive_points']['failed'])
                                            and rev['drive_signer']['exit'] == 0),
        'registered_mutant_red_on_prepare': (made['replacement_count'] == 1 and mut['drive_points']['exit'] == 1
                                             and mut['drive_signer']['exit'] == 1
                                             and any(f.startswith('prepare: the engine upgrade')
                                                     for f in mut['drive_signer']['failed'])),
    }
    report = {'schema': 'veldo.falsifier-run/v1', 'spec_id': 'VELDO-0161', 'round': 7, 'case': CASE,
              'registered_rows': case['rows'], 'registered_suite': case['suite'],
              'replacement_count': made['replacement_count'], 'old_digest': made['old_digest'],
              'new_digest': made['new_digest'], 'revert_anchor_count': reverted_count, 'runs': runs,
              'verdicts': killed, 'killed_here': all(killed.values()),
              'note': 'suite 86 needs the host\'s user manager and local sockets; these drivers are the sandbox '
                      'falsifiers of the kill-point count and of the prepare step'}
    text = json.dumps(report, indent=1) + '\n'
    if argv:
        Path(argv[0]).write_text(text)
    print(text, end='')
    return 0 if report['killed_here'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
