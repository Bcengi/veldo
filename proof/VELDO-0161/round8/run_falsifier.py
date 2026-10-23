#!/usr/bin/env python3
"""VELDO-0161 round 8: drive_debt.py over the modules as they are, with the round-8 fix reverted, and with
finding 161's upgrade161-adoption-restart-not-owed applied; drive_driver.py over suite 86 as it is and as it was
at 6b2805e6; record all of them.

    python3 proof/VELDO-0161/round8/run_falsifier.py [<output.json>]

The revert removes the adoption_signers branch from control_factory_setup_upgrade.recovery (the round-8 fix);
the registered mutant is made by scripts/check_teeth_mutations.py's own materialize from its anchor. Under
either, a run killed after the last adoption_signers point owes no restart and the next run restarts nothing:
drive_debt is red there. Suite 86's kill driver at 6b2805e6 wraps `point` once per fetch of the upgrade module:
drive_driver is red on it. The registered row is suite 86's restart/adoption-signer-kill, on the host.
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
CASE = 'upgrade161-adoption-restart-not-owed'
MODULE = 'control_factory_setup_upgrade.py'
FIX = ("        elif name == 'adoption_signers':\n"
       "            # VELDO-0161: the service reads its enrollment signers only at its start, so signers laid down owe a\n"
       "            # restart until a restart outcome or done clears it, whichever run makes it.\n"
       "            held['due'] = True\n")
BEFORE = '6b2805e6'


def drive(script, *args):
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name(script))] + [str(a) for a in args],
                          capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    try:
        report = json.loads(done.stdout)
    except ValueError:
        report = {'error': done.stderr[-600:]}
    return dict(exit=done.returncode, failed=[label for label, ok in report.get('checks', []) if not ok],
                passed=report.get('passed'), error=report.get('error'))


def main(argv):
    spec = importlib.util.spec_from_file_location('r8_teeth', str(ROOT / 'scripts/check_teeth_mutations.py'))
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    case = next(c for c in teeth.cases() if c['name'] == CASE)
    scratch = Path(tempfile.mkdtemp(prefix='r8-falsifier-', dir=os.environ.get('TMPDIR')))
    try:
        def copy(name, module_text):
            mods = scratch / name
            shutil.copytree(str(ROOT / 'engine' / '.veldo'), str(mods), ignore=shutil.ignore_patterns('__pycache__'))
            (mods / MODULE).write_text(module_text)
            return mods
        source = (ROOT / 'engine' / '.veldo' / MODULE).read_text()
        fix_count = source.count(FIX)
        reverted = copy('reverted', source.replace(FIX, ''))
        made = teeth.materialize(case, 'mutant', scratch / 'mutant')
        mutant = copy('mutant-veldo', Path(made['mutant']).read_text())
        before = scratch / 'suite-86-before.py'
        before.write_bytes(subprocess.run(['git', 'show', BEFORE + ':scripts/suites/86_veldo_0189_engine_upgrade.py'],
                                          cwd=str(ROOT), capture_output=True, check=True).stdout)
        runs = {'debt_baseline': drive('drive_debt.py', ROOT / 'engine' / '.veldo'),
                'debt_fix_reverted': drive('drive_debt.py', reverted),
                'debt_registered_mutant': drive('drive_debt.py', mutant),
                'driver_now': drive('drive_driver.py'),
                'driver_at_' + BEFORE: drive('drive_driver.py', before)}
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)

    def red_on_kill(run):
        return run['exit'] == 1 and any('owes the restart' in f for f in run['failed']) \
            and any(f.startswith('killed at 4 (adoption_signers): the next run restarts') for f in run['failed'])
    killed = {
        'baseline_green': all(runs[k]['exit'] == 0 and not runs[k]['failed'] for k in ('debt_baseline', 'driver_now')),
        'fix_reverted_red_on_the_kill_after_the_signers': fix_count == 1 and red_on_kill(runs['debt_fix_reverted']),
        'registered_mutant_red_on_the_kill_after_the_signers': (made['replacement_count'] == 1
                                                                and red_on_kill(runs['debt_registered_mutant'])),
        'driver_at_%s_red_on_the_count' % BEFORE: (runs['driver_at_' + BEFORE]['exit'] == 1 and any(
            f.startswith('one count per step-log line') for f in runs['driver_at_' + BEFORE]['failed'])),
    }
    report = {'schema': 'veldo.falsifier-run/v1', 'spec_id': 'VELDO-0161', 'round': 8, 'case': CASE,
              'registered_rows': case['rows'], 'registered_suite': case['suite'],
              'replacement_count': made['replacement_count'], 'old_digest': made['old_digest'],
              'new_digest': made['new_digest'], 'fix_anchor_count': fix_count, 'runs': runs,
              'verdicts': killed, 'killed_here': all(killed.values()),
              'note': 'suite 86 needs the host\'s user manager and local sockets; these drivers are the sandbox '
                      'falsifiers of the restart debt and of the kill driver\'s count'}
    text = json.dumps(report, indent=1) + '\n'
    if argv:
        Path(argv[0]).write_text(text)
    print(text, end='')
    return 0 if report['killed_here'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
