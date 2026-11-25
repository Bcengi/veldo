"""Direct ticket assertions, separate from canonical selftest evidence."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
rows = []

def expect(name, passed):
    rows.append(dict(name=name, passed=bool(passed)))

source = root / 'scripts/suites/162_veldo_0364_host_relative.py'
exec(compile(source.read_bytes(), str(source), 'exec'), dict(ROOT=root, expect=expect))
print(json.dumps(dict(passed=len(rows) == 9 and all(r['passed'] for r in rows), rows=rows), indent=2))
sys.exit(not (len(rows) == 9 and all(r['passed'] for r in rows)))
