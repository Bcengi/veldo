"""Compare fresh pc2 evidence with gate 15 and completed gate 18 workers."""
import gzip
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE1 = HERE.parents[1] / 'VELDO-0365'
spec = importlib.util.spec_from_file_location('phase1_compare', PHASE1 / 'compare.py')
phase1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase1)
expected = json.loads((PHASE1 / 'expected.json').read_text())
batch = json.loads(gzip.decompress((HERE / 'pc2-batch.json.gz').read_bytes()))
gate18 = json.loads(gzip.decompress((HERE / 'gate18-workers.json.gz').read_bytes()))
actual = {r['case']['name']: r for r in batch['results']}
rows = []
for old in expected:
    case = old['case']
    now = actual[case['name']]
    strict = phase1.verdict(now)
    row = dict(name=case['name'], gate15=dict(
        exact_verdict=strict == old,
        named_verdict=now['kills'] == old['kills'] and now['kill_by'] == old['kill_by'],
        full_observations=strict['observations'] == old['observations'],
        differing_fields=[k for k in old if strict[k] != old[k]]))
    group = case['suite'] + ':' + case['module'] + ':' + str(case.get('fixture') is True)
    if case.get('confined_only'):
        group += ':confined'
    keys = dict(baseline=group + ':baseline', noop=group + ':noop', mutant=case['identity'])
    missing = [name for name in keys.values() if name not in gate18]
    if missing:
        row['gate18'] = dict(status='pending gate worker', missing=missing)
    else:
        workers = {mode: gate18[name]['output'] for mode, name in keys.items()}
        observations = {mode: value['observation']['observations'] for mode, value in workers.items()}
        mutant = workers['mutant']
        target_kills = sorted(name for name, state in observations['mutant']
                              if name.split()[-1] in case['rows'] and state is False)
        row['gate18'] = dict(status='compared completed workers',
            mutation_identity=all(mutant[k] == now[k]
                for k in ('old_digest', 'new_digest', 'replacement_count')),
            controls_green=all(state is True for mode in ('baseline', 'noop')
                               for _, state in observations[mode]),
            named_verdict=target_kills == sorted(k['row'] for k in now['kills']),
            full_observations=observations == strict['observations'],
            differing_modes=[mode for mode in observations if observations[mode] != strict['observations'][mode]])
    rows.append(row)
result = dict(gate15=phase1.compare(expected, batch),
    gate18=dict(compared=sum(r['gate18']['status'] == 'compared completed workers' for r in rows),
        pending=[r['name'] for r in rows if r['gate18']['status'] != 'compared completed workers']),
    cases=rows)
(HERE / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
for row in rows:
    if not row['gate15']['exact_verdict'] or any(v is False for v in row['gate18'].values()):
        print(json.dumps(row))
