"""Reduce an existing gate-15 receipt, then replay only fake coordinator children."""
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('early_gate', ROOT / 'scripts/check_gate_mutations.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
support = runpy.run_path(str(ROOT / 'scripts/suites/support/v363_early.py'))


def extract(log):
    for line in Path(log).open():
        if line.startswith('{"admissions":'):
            receipt = json.loads(line)
            break
    registry = {}
    for driver in gate.DRIVERS:
        source = subprocess.run(['git', 'show', '993f66d91:scripts/' + driver],
                                cwd=ROOT, capture_output=True, text=True, check=True).stdout
        module = types.ModuleType('historical_registry')
        module.__file__ = str(ROOT / 'scripts' / driver)
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        registry.update({driver + ':' + c['name']: dict(c, identity=driver + ':' + c['name'])
                         for c in module.cases()})
    outcomes = {o['name']: o for o in receipt['worker_outcomes']}
    failed = {r['case']['identity'] for r in receipt['invalid_results'] if 'case' in r}
    groups = {}
    for r in receipt['case_receipts']:
        c = registry[r['identity']]
        group = gate.control_group(c)
        times = [outcomes[group + ':' + m]['elapsed'] for m in ('baseline', 'noop')]
        own = outcomes.get(c['identity'], {})
        item = groups.setdefault(group, dict(controls=times, mutants=[]))
        item['mutants'].append([own.get('elapsed'), c['identity'] in failed
                               or own.get('error') not in (None, 'worker_cancelled')])
    result = dict(source=Path(log).name, receipt_sha256=hashlib.sha256(line.encode()).hexdigest(),
                  registered=receipt['registered'], groups=groups)
    assert result['registered'] == 3978 and len(groups) == 734
    (HERE / 'gate15.json').write_text(json.dumps(result, separators=(',', ':')) + '\n')


def replay():
    data = json.loads((HERE / 'gate15.json').read_text())
    sizes = [len(g['mutants']) for g in data['groups'].values()]
    cases = support['cases_for'](gate, sizes)
    durations, history = {}, {}
    for g, item in enumerate(data['groups'].values()):
        for mode, seconds in zip(('baseline', 'noop'), item['controls']):
            durations['g%d.py:target.py:False:%s' % (g, mode)] = seconds
        for n, (seconds, failed) in enumerate(item['mutants']):
            identity = 'g%d-c%d' % (g, n)
            # Unexecuted mutants have no measured duration: use their measured
            # control maximum, explicitly a replay estimate, never a verdict.
            durations[identity] = seconds or max(item['controls'])
            history[identity] = dict(failed=failed, seconds=durations[identity])
    r, launches, finishes = support['drive'](gate, cases=cases, durations=durations,
                                           history=history, parallel=14)
    first = next(item for item in launches if item[1] == 'mutant')
    first_case = next(c for c in cases if c['identity'] == first[0])
    group = gate.control_group(first_case)
    controls = {n: at for n, mode, at, rc in finishes if mode != 'mutant' and rc == 0}
    own = [controls[group + ':' + m] for m in ('baseline', 'noop')]
    assert r['status'] == 'passed' and r['rejected'] == r['registered'] == 3978
    assert max(own) <= first[2] < max(controls.values())
    for name, mode, at in launches:
        if mode == 'mutant':
            g = name.split('-')[0] + '.py:target.py:False'
            assert all(controls[g + ':' + m] <= at for m in ('baseline', 'noop'))
    result = dict(status='passed', kind='fake event replay; no speedup claim', groups=len(sizes),
                  registered=r['registered'], rejected=r['rejected'], workers=r['worker_invocations'],
                  first_mutant=first, own_controls_completed=own,
                  last_control_completed=max(controls.values()), surviving_workers=r['surviving_workers'],
                  unmeasured_mutants=sum(v[0] is None for g in data['groups'].values() for v in g['mutants']))
    (HERE / 'replay.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        extract(sys.argv[1])
    replay()
