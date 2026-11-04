"""VELDO-0241 falsifier driver: each named case of scripts/check_teeth_mutations.py materialized and run by
that driver's own materialize and worker; one JSON line per case. Usage: python3 proof/VELDO-0241/falsify.py NAME..."""
import importlib.util, json, sys, tempfile
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('teeth', 'scripts/check_teeth_mutations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
names = sys.argv[1:]
out = []
for case in m.cases():
    if case['name'] not in names:
        continue
    with tempfile.TemporaryDirectory(prefix='v241-mutant-') as d:
        made = m.materialize(case, 'mutant', d)
        result = m.worker(case, str(made['mutant']))
    out.append({'case': case['name'], 'module': case['module'], 'rows': case['rows'], 'targets': result['targets'],
                'failed_rows': result['failed_rows'], 'count': result['count'],
                'old_digest': made['old_digest'], 'new_digest': made['new_digest'],
                'red': all(not any(v) or False in v for v in result['targets'].values()) and all(result['targets'].values())})
for line in out:
    print(json.dumps(line, sort_keys=True))
