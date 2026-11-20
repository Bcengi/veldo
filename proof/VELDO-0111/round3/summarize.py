"""Separate local green regressions from the still-open AC2 acceptance claim."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
result = json.load(gzip.open(HERE / 'suite-green.json.gz', 'rt'))
rows = dict(result['rows'])
focused = {'census/family-qualification-boundary', 'census/unix-binding-is-real', 'census/fault-state-coverage'}
(HERE / 'regressions-green.json').write_text(json.dumps(dict(
    derived_from='suite-green.json.gz', rows=[r for r in result['rows'] if r[0] in focused],
    source_digest=result['source_digest'], suite_digest=result['suite_digest']), indent=2) + '\n')
r = result['evidence']['inventory']
report = dict(
    status='REMAINING',
    acceptance=dict(AC1=rows['census/process-lifetimes'],
        AC2=r['qualification']['status'] == 'COMPLETE' and r['status'] == 'COMPLETE',
        AC3=rows['census/observer-is-outside'],
        AC4=rows['census/incomplete-is-not-empty'] and rows['census/fault-state-coverage']),
    regression_rows=result['rows'],
    qualification_status=r['qualification']['status'],
    capture_status=r['capture_status'],
    qualification_gaps=r['qualification']['gaps'],
    observed_outside_families=sorted({o['family'] for o in r['sockets'] if o.get('not_qualified')}),
    source_digest=result['source_digest'], suite_digest=result['suite_digest'],
    spec_digest=hashlib.sha256((ROOT / 'specs/VELDO-0111-process-and-listener-census.md').read_bytes()).hexdigest())
assert all(rows.values()) and report['acceptance'] == dict(AC1=True, AC2=False, AC3=True, AC4=True)
(HERE / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
