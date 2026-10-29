#!/usr/bin/env python3
"""Check a future batch capture. This command never starts a gate.

Input: {head, elapsed, host:{cores, memory_bytes, scope_memory_max}, stamp,
        event, schedule, without_0219_0221}. Schedule is gate-schedule.json.
The caller captures full-gate elapsed time independently, including builtins.
"""
import argparse
import json
from pathlib import Path


def check(capture, baseline):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    try:
        schedule, stamp, event, host = (capture[n] for n in ('schedule', 'stamp', 'event', 'host'))
        require(capture['without_0219_0221'] is True, 'qualification includes follow-up tickets')
        require(host['cores'] == 20 and 30 * 2**30 <= host['memory_bytes'] <= 32 * 2**30
                and host['scope_memory_max'] == 16 * 2**30, 'wrong qualification host or scope')
        require(stamp['commit'] == event['commit'] == capture['head'] and len(capture['head']) == 40,
                'capture does not bind the landing candidate')
        require(stamp['status'] == 'green' and event['type'] == 'gate.passed', 'canonical gate is not green')
        require(stamp['force_fresh'] is True and event['force_fresh'] is True
                and stamp['reused'] == event['reused'] == {'unit': 0, 'mutation': 0}, 'gate is not force fresh')
        require(stamp['graph'] == event['graph'] == schedule['graph'], 'graph identity mismatch')
        require(schedule['inputs_unchanged'] is True, 'candidate changed')
        require(0 < schedule['wall_seconds'] <= capture['elapsed'] <= 6000, 'canonical elapsed exceeds 6000s')
        require(0 < schedule['critical_path_seconds'] <= 6000, 'critical path exceeds 6000s')
        require(set(schedule['nodes']) == set(baseline['nodes']), 'node inventory differs from baseline')
        comparisons = {}
        for name, node in schedule['nodes'].items():
            require(node['verdict'] == 'pass' and node['end'] >= node['start'] >= 0
                    and node['wall_seconds'] > 0 and node['cpu_seconds'] >= 0
                    and node['peak_anon_bytes'] > 0 and node['metrics_source'] == 'cgroup-v2-anon-sampled-50ms',
                    'missing or failed node measurement: ' + name)
            comparisons[name] = {'serial_wall_seconds': baseline['nodes'][name]['wall_seconds'],
                                 'graph_wall_seconds': node['wall_seconds'],
                                 'cpu_seconds': node['cpu_seconds'], 'peak_anon_bytes': node['peak_anon_bytes']}
        require(all(schedule['peak_granted'][r] <= schedule['capacities'][r]
                    for r in ('cpu', 'memory', 'manager')), 'ledger peak exceeds capacity')
        return dict(passed=not errors, errors=errors, serial_elapsed=baseline['elapsed'],
                    elapsed=capture['elapsed'], critical_path_seconds=schedule['critical_path_seconds'],
                    critical_path_end=schedule['critical_path_end'], comparisons=comparisons)
    except (KeyError, TypeError, ValueError) as error:
        return dict(passed=False, errors=errors + ['incomplete canonical capture: ' + str(error)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.capture.read_text()), json.loads(Path(__file__).with_name('serial-baseline.json').read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
