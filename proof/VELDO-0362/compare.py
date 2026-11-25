"""Check two complete bounded receipts; no result is inferred from a resource hint."""
import hashlib
import json
from pathlib import Path
import sys


def compare(directory):
    directory = Path(directory)
    receipts = {mode: json.loads((directory / (mode + '.json')).read_text())
                for mode in ('default', 'calibrated')}
    names = json.loads((directory / 'selection.json').read_text())
    checks = {}
    metrics = {}
    verdicts = {}
    for mode, result in receipts.items():
        host = result['bounded_host']
        checks[mode + '/coverage'] = (result['scope'] == 'selected' and result['status'] == 'passed'
            and result['registered'] == result['executed'] == result['rejected'] == len(names) == 150
            and result['reused'] == 0 and not result['invalid_results'] and result['surviving_workers'] == 0
            and {r['identity'].split(':', 1)[1] for r in result['case_receipts']} == set(names))
        checks[mode + '/memory-cap'] = host['memory_peak'] <= host['memory_max'] == 16 * 2**30
        checks[mode + '/worker-anon-cap'] = result['peak_anon_bytes'] <= host['memory_max']
        events = dict(line.split() for line in host['memory_events'].splitlines())
        cpu = dict(line.split() for line in host['cpu_stat'].splitlines())
        checks[mode + '/no-quota-or-memory-high-throttling'] = all(int(events[k]) == 0 for k in ('high', 'oom', 'oom_kill')) and int(cpu['nr_throttled']) == 0
        checks[mode + '/no-timeouts'] = all(not o.get('error') for o in result['worker_outcomes'])
        checks[mode + '/one-generator'] = result['resources']['peak_slots']['load_generator'] == 1
        verdicts[mode] = {r['identity']: dict(validated=r['validated'], source=r['source'],
            kill_by=r.get('kill_by'), kills=sorted((k['row'].split()[-1], k['kill_by'])
                for k in r.get('kills', []))) for r in result['case_receipts']}
        metrics[mode] = dict(wall_seconds=result['elapsed'], workers=result['worker_invocations'],
            peak_workers=result['peak_workers'], mean_busy_cores=result['mean_busy_cores'],
            peak_worker_anon_bytes=result['peak_anon_bytes'], scope_peak_memory_bytes=host['memory_peak'],
            host_memory_cap=host['memory_max'], cpu_throttled_usec=int(cpu['throttled_usec']),
            memory_events=events, input_digest=result['input_digest'],
            implementation_digest=result['implementation_digest'],
            receipt_sha256=hashlib.sha256((directory / (mode + '.json')).read_bytes()).hexdigest())
    checks['same-verdicts'] = verdicts['default'] == verdicts['calibrated']
    checks['same-inputs'] = receipts['default']['input_digest'] == receipts['calibrated']['input_digest']
    checks['default-claims'] = all(c['source'] == 'default' and c['cpu'] == 1 and c['memory'] == 2**30
                                  for c in receipts['default']['case_claims'].values())
    checks['calibrated-claims'] = all(c['source'] == 'this_key' for c in receipts['calibrated']['case_claims'].values())
    return dict(passed=all(checks.values()), checks=checks, metrics=metrics,
                seconds_saved=metrics['default']['wall_seconds'] - metrics['calibrated']['wall_seconds'],
                verdicts=verdicts['default'])


if __name__ == '__main__':
    result = compare(sys.argv[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result['passed'] else 1)
