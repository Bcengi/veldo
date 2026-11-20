"""Ticket-local owner-conflict document check; never modifies specifications."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
paths = [next((ROOT / 'specs').glob('VELDO-' + n + '-*.md')) for n in ('0111','0113','0114','0122')]
doc = HERE.parent / 'spec-conflict.md'
text = doc.read_text() if doc.exists() else ''
passed = all(n in text for n in ('VELDO-0111','VELDO-0113','VELDO-0114','VELDO-0122')) and all(
    phrase in text for phrase in ('Proposed amendment', 'when they land', 'Owner decision pending'))
report = dict(passed=passed, spec_digests={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(HERE / ('spec-' + sys.argv[1] + '.json')).write_text(json.dumps(report, indent=2) + '\n')
assert passed == (sys.argv[1] == 'green'), report
print(sys.argv[1], passed)
