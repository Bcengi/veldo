#!/usr/bin/env python3
"""Validate a future canonical capture. Never starts a gate."""
import argparse
import json
import math
from pathlib import Path


def check(capture):
    errors, comparisons = [], []
    def require(condition, detail):
        if not condition:
            errors.append(detail)
    def positive(value):
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    try:
        stage, stamp, event, host = (capture[k] for k in ('mutation', 'stamp', 'event', 'host'))
        require(len(capture['head']) == 40 and stamp['commit'] == event['commit'] == capture['head'],
                'capture must bind the candidate commit')
        require(stamp['status'] == 'green' and event['type'] == 'gate.passed', 'canonical gate must pass')
        require(stamp['force_fresh'] is True and event['force_fresh'] is True and stage['force_fresh'] is True,
                'force fresh required')
        require(stamp['reused'] == event['reused'] == {'unit': 0, 'mutation': 0}, 'canonical reuse is nonzero')
        require(host['cores'] == 20 and 30*2**30 <= host['memory_bytes'] <= 32*2**30
                and host['scope_memory_max'] == 16*2**30, 'wrong qualification capacities')
        require(host['lock'] == '/home/dmitry/.local/state/core-gates/.gate.lock'
                and host['held'] in ('taken', 'caller') and host['quiet'] is True,
                'missing quiet host lock evidence')
        require(stage['scope'] == 'full' and stage['status'] == 'passed' and stage['reused'] == 0
                and stage['registered'] == stage['executed'] == stage['rejected'] > 0,
                'incomplete fresh mutation inventory')
        require(positive(stage['elapsed']) and stage['elapsed'] <= 4000, 'mutation stage exceeds 4000 seconds')
        require(stage['surviving_workers'] == 0 and not stage['invalid_results'], 'invalid or surviving workers')
        require(positive(stage['peak_workers']) and positive(stage['mean_busy_cores'])
                and positive(stage['peak_anon_bytes']), 'missing stage resource measurements')
        rows = stage['worker_outcomes']
        require(len(rows) == stage['worker_invocations'] and len(rows) > stage['registered'],
                'missing control or mutant worker measurements')
        names = [o['name'] for o in rows]
        require(len(names) == len(set(names)), 'duplicate worker outcome')
        require(set(capture['quiet_measurements']) == set(names), 'quiet measurements differ from workers')
        for outcome in rows:
            name = outcome['name']
            require('error' not in outcome and outcome['returncode'] == 0, 'worker failed: ' + name)
            require(positive(outcome['elapsed']) and outcome['elapsed'] < outcome['budget_seconds'],
                    'worker deadline expired: ' + name)
            require(positive(outcome['measurement']['cpu_seconds'])
                    and positive(outcome['measurement']['peak_anon_bytes']), 'worker unmeasured: ' + name)
            quiet = capture['quiet_measurements'][name]
            require(positive(quiet), 'missing quiet measurement: ' + name)
            comparisons.append(dict(name=name, elapsed=outcome['elapsed'], deadline=outcome['budget_seconds'],
                                    quiet_seconds=quiet, slowdown=outcome['elapsed']/quiet))
        require(all(stage['peak_granted'][r] <= stage['ledger_capacities'][r] for r in ('cpu','memory')),
                'ledger capacity exceeded')
        return dict(passed=not errors, errors=errors, elapsed=stage['elapsed'],
                    baseline_seconds=5207, peak_workers=stage['peak_workers'],
                    mean_busy_cores=stage['mean_busy_cores'], peak_anon_bytes=stage['peak_anon_bytes'],
                    comparisons=comparisons)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        return dict(passed=False, errors=errors + ['incomplete capture: ' + str(error)])


def fixture():
    """Synthetic input solely for checker tests, never qualification evidence."""
    rows = [dict(name=n, elapsed=10, budget_seconds=120, returncode=0,
                 measurement=dict(cpu_seconds=5, peak_anon_bytes=2**28)) for n in ('baseline','noop','mutant')]
    head = 'a'*40
    return dict(head=head, stamp=dict(commit=head,status='green',force_fresh=True,reused={'unit':0,'mutation':0}),
        event=dict(commit=head,type='gate.passed',force_fresh=True,reused={'unit':0,'mutation':0}),
        host=dict(cores=20,memory_bytes=31*2**30,scope_memory_max=16*2**30,
                  lock='/home/dmitry/.local/state/core-gates/.gate.lock',held='taken',quiet=True),
        mutation=dict(scope='full',status='passed',force_fresh=True,reused=0,registered=1,executed=1,rejected=1,
            elapsed=3300,surviving_workers=0,invalid_results=[],peak_workers=26,mean_busy_cores=17,
            peak_anon_bytes=13*2**30,worker_invocations=3,worker_outcomes=rows,
            peak_granted={'cpu':18,'memory':13*2**30},ledger_capacities={'cpu':20,'memory':15*2**30}),
        quiet_measurements={o['name']:10 for o in rows})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.capture.read_text()))
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(int(not result['passed']))
