"""Read-only binding and completeness audit of this ticket's final red/green receipts."""
import difflib
import fnmatch
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / 'proof/VELDO-0121'
RESULTS = PROOF / 'results'
sha = lambda data: hashlib.sha256(data).hexdigest()
source = (ROOT / '.veldo/control_relay.py').read_bytes()
fixture_bytes = (ROOT / 'scripts/fixtures/relay_exchange.py').read_bytes()
spec = importlib.util.spec_from_file_location('relay121_audit', ROOT / 'scripts/fixtures/relay_exchange.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
summary = json.loads((RESULTS / 'summary.json').read_text())
assert summary['complete'] and len(summary['results']) == 8
assert source == (ROOT / 'engine/.veldo/control_relay.py').read_bytes()
for relative in ('.veldo/control_relay.py', 'engine/.veldo/control_relay.py',
                 'scripts/fixtures/relay_exchange.py', 'proof/VELDO-0121/drive.py',
                 'scripts/suites/113_veldo_0121_relay_exchange.py'):
    assert subprocess.check_output(['git', 'show', summary['input_commit'] + ':' + relative], cwd=ROOT) == (ROOT / relative).read_bytes(), relative
checks = []
for criterion, row in fixture.ROWS.items():
    reports = [json.loads(gzip.decompress((RESULTS / (criterion + '-' + color + '.json.gz')).read_bytes()))
               for color in ('red', 'green')]
    red, green = reports
    assert red['rows'] == {row: False} and green['rows'] == {row: True}
    assert all(r['valid'] and r['inputs_unchanged'] and not r['incomplete'] for r in reports)
    assert red['expected'] == red['executed'] == green['expected'] == green['executed']
    assert [r['schedule_sha256'] for r in red['records']] == [r['schedule_sha256'] for r in green['records']]
    assert all(r['input_commit'] == summary['input_commit'] and r['fixture_sha256'] == sha(fixture_bytes) for r in reports)
    assert green['implementation_sha256'] == sha(source)
    changed = fixture.mutate(source.decode(), criterion)
    assert red['implementation_sha256'] == sha(changed.encode())
    expected_diff = ''.join(difflib.unified_diff(source.decode().splitlines(True), changed.splitlines(True),
                                                fromfile='a/.veldo/control_relay.py', tofile='b/.veldo/control_relay.py'))
    assert (RESULTS / (criterion + '.diff')).read_text() == expected_diff
    entries = [e for e in summary['results'] if e['criterion'] == criterion]
    assert [e['color'] for e in entries] == ['red', 'green']
    assert all(e['valid'] and e['observed'] == e['expected'] for e in entries)
    assert entries[0]['falsifier_witness_records']
    realtime = [dict(mode='trickle' if r['case']['trickle'] else 'stalled', elapsed=r['elapsed_seconds'],
                     exit=r['exit'], surviving_helpers=r['surviving_helpers'])
                for r in green['records'] if r['case']['kind'] == 'realtime']
    checks.append(dict(criterion=criterion, row=row, red=False, green=True,
                       counts=green['executed'], real_time=realtime))
    print(criterion, 'red then green, bound and complete', green['executed'], realtime)
paths = subprocess.check_output(['git', 'diff', '--name-only', '59b119a1', 'HEAD'], cwd=ROOT, text=True).splitlines()
protected = re.findall(r'\{path:\s*"([^"]+)"', (ROOT / '.veldo/policy.yaml').read_text())
touched = [p for p in paths if any(fnmatch.fnmatchcase(p, pattern) for pattern in protected)]
assert not touched, touched
report = dict(input_commit=summary['input_commit'], implementation_sha256=sha(source),
              fixture_sha256=sha(fixture_bytes), checks=checks, all_receipts_valid=True,
              protected_paths_touched=touched)
(PROOF / 'receipt-validation.json').write_text(json.dumps(report, indent=2) + '\n')
