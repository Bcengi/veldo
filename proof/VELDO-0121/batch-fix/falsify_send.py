"""Batch fix red/green: the fixture pin refuses the chunked conn.send relay.

Red is the relay at d6fd78b9 (chunked conn.send, the source the VELDO-0168 send
inventory rejected); green is the committed sendall relay. Both run the complete
AC1 criterion on the same fixture, so the only difference is the relay source.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / 'scripts/fixtures/relay_exchange.py'
spec = importlib.util.spec_from_file_location('relay_exchange121_batch', path)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
red_source = subprocess.check_output(['git', 'show', 'd6fd78b9:.veldo/control_relay.py'], cwd=ROOT, text=True)
green_source = (ROOT / '.veldo/control_relay.py').read_text()
assert green_source == (ROOT / 'engine/.veldo/control_relay.py').read_text()
row = fixture.ROWS['AC1']
summary = []
for color, source in (('red', red_source), ('green', green_source)):
    result = fixture.qualify(source, 'AC1')
    entry = dict(color=color, implementation_sha256=result['implementation_sha256'],
                 fixture_sha256=result['fixture_sha256'], reconciliation=result['reconciliation'],
                 valid=result['valid'], incomplete=result['incomplete'], executed=result['executed'],
                 row=row, observed=result['rows'][row])
    summary.append(entry)
    print(color, 'calls=' + ','.join(sorted(set(entry['reconciliation']['calls']))),
          'valid=' + str(entry['valid']), 'row=' + str(entry['observed']), flush=True)
ok = (summary[0]['observed'] is False and not summary[0]['reconciliation']['matches']
      and summary[1]['observed'] is True and all(e['valid'] and not e['incomplete'] for e in summary))
Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'proof/VELDO-0121/batch-fix/falsify_send.json').write_text(
    json.dumps(dict(ok=ok, results=summary), indent=2) + '\n')
sys.exit(0 if ok else 1)
