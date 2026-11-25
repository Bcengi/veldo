"""Light direct suite drive; no selftest dispatcher or gate fixtures."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
rows = []
def expect(name, passed):
    rows.append(dict(name=name, passed=bool(passed)))
source = root / 'scripts/suites/163_veldo_0366_shards.py'
exec(compile(source.read_bytes(), str(source), 'exec'), dict(ROOT=root, expect=expect))
print(json.dumps(dict(passed=bool(rows) and all(r['passed'] for r in rows), rows=rows), indent=2))
sys.exit(not rows or not all(r['passed'] for r in rows))
