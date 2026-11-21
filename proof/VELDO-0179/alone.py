"""Run one registered mutation case alone, unconfined: the driver's own materialize() for the no-op and the mutant,
and its own worker entry (check_teeth_mutations.py --worker NAME [--mutant PATH]) for baseline, no-op and mutant."""
import importlib.util, json, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path.cwd()
name = sys.argv[1]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
case = next(c for c in T.cases() if c['name'] == name)
print('case:', name, '| suite:', case['suite'], '| module:', case.get('dir'), case['module'], '| rows:', case['rows'])
head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
print('at:', head)
verdict = {}
with tempfile.TemporaryDirectory(prefix='v179-alone-') as d:
    for mode in ('baseline', 'noop', 'mutant'):
        made = T.materialize(case, mode, Path(d) / mode)
        args = [sys.executable, 'scripts/check_teeth_mutations.py', '--worker', name]
        if made['mutant'] is not None:
            args += ['--mutant', str(made['mutant'])]
        started = time.monotonic()
        done = subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        try:
            out = json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:
            print(mode, 'worker did not answer', done.returncode, done.stderr[-2000:]); verdict[mode] = None; continue
        targets = {row: all(oks) and bool(oks) for row, oks in out['targets'].items()}
        print('%s: exit %d, %.0fs, module sha256 %s, %d rows observed, failed rows %s, target rows green %s'
              % (mode, done.returncode, time.monotonic() - started, made['new_digest'][:16], out['count'],
                 out['failed_rows'], targets))
        for row, detail in out['failed_details']:
            print('   %s detail: %s' % (row, detail[:600]))
        verdict[mode] = (out['failed_rows'], targets)
ok = (verdict.get('baseline') and not verdict['baseline'][0] and verdict.get('noop') and not verdict['noop'][0]
      and verdict.get('mutant') and not any(verdict['mutant'][1].values()))
print('verdict:', 'KILLED (baseline and no-op green, every target row red under the mutant)' if ok else 'NOT CLEAN')
