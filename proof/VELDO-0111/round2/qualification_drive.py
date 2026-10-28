"""Qualification regression and named-gap checks for this ticket only."""
import gzip, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'scripts/fixtures/lifecycle_census.py'
SUITE=ROOT/'scripts/suites/113_veldo_0111_census.py'
phase=sys.argv[1]
spec=importlib.util.spec_from_file_location('suite',SUITE)
suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
rows=[]
evidence=suite.run_checks(ROOT,lambda name,ok:rows.append([name,bool(ok)]))
r=evidence['inventory']; inventory=r['qualification']['inventory']
checks=dict(no_blanket_failure=all(f['capability']!='qualification' for f in r['failures']),
    operations_probed=bool(inventory.get('operation_probes')),
    nonzero_protocols=any(c['protocol']>0 for c in inventory['combinations']),
    async_effect_tested=bool(inventory.get('io_uring',{}).get('socket_effect')),
    named_reasons=bool(r['qualification'].get('reasons')))
with gzip.open(HERE/('qualification-'+phase+'.json.gz'),'wt') as out:
    json.dump(dict(rows=rows,evidence=evidence,checks=checks),out)
(HERE/('qualification-'+phase+'.json')).write_text(json.dumps(dict(checks=checks,rows=rows,
    source_digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    suite_digest=hashlib.sha256(SUITE.read_bytes()).hexdigest()),indent=2)+'\n')
print(phase,checks,rows,flush=True)
assert all(checks.values())==(phase=='green')
assert all(ok for _,ok in rows)
