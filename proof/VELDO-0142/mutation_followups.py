"""Run one review follow-up with the gate's worker, controls and result validator.

This is scoped evidence, not a gate result. Workers run serially in this checkout;
no stage inventory, snapshot, cache or other mutation case is executed.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[2]
NAMES = ('repository-binding-unchecked', 'account-cap-stop-ignored')


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=NAMES)
    parser.add_argument('--leg', required=True, choices=('confined', 'direct'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    gate = load('check_gate_mutations')
    driver = load('check_teeth_mutations')
    case = next(c for c in driver.cases() if c['name'] == args.case)
    case = dict(case, driver='check_teeth_mutations.py',
                identity='check_teeth_mutations.py:' + args.case)
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    workers = gate.Workers(time.monotonic() + 3 * gate.WORKER_BUDGET + 30, parallel=1)
    if args.leg == 'direct':
        workers.leg = {'suites': [case['suite'][:-3]], 'entries': [case['suite'][:-3]]}
    results = {}
    try:
        for mode in ('baseline', 'noop', 'mutant'):
            completed = workers.run({mode: {'case': case, 'mode': mode}}, directory, ROOT)[mode]
            results[mode] = completed['result']
            print(json.dumps({'mode': mode, 'elapsed': completed['elapsed'],
                              'failed_rows': results[mode]['observation']['failed_rows'],
                              'targets': results[mode]['observation']['targets']}), flush=True)
        prepared = results['mutant']
        record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=case,
                      **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')},
                      **{mode: results[mode]['observation'] for mode in results})
        gate.validate_result(record, case)
        (directory / 'validated.json').write_text(json.dumps(record, indent=2) + '\n')
        print('PASS: %s (%s): green baseline/noop, named assertion killed mutant' % (args.case, args.leg))
    finally:
        (directory / 'workers.json').write_text(json.dumps(workers.outcomes, indent=2) + '\n')


if __name__ == '__main__':
    main()
