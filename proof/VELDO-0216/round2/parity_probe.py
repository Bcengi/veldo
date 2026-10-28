"""The same split-only defect must distinguish the no-graph serial reference."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
mutant = sys.argv[1] == 'mutant'
source = (ROOT/'scripts/suites/114_veldo_0216_concurrent_stages.py').read_text()
if mutant:
    anchor = "        shutil.copyfile(leg_source, scripts / 'gate_legs.py')"
    injection = "\n        copied = scripts / 'gate_legs.py'\n        copied.write_text(copied.read_text().replace('write_record(record, stage, digest, listed)\\n', \"write_record(record, stage, digest, listed + ['split-defect'] if leg else listed)\\n\"))"
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor+injection)
rows = {}
exec(compile(source, str(ROOT/'scripts/suites/114_veldo_0216_concurrent_stages.py'), 'exec'),
     dict(ROOT=ROOT, expect=lambda name, ok: rows.update({name:bool(ok)})))
print(json.dumps(dict(mode=sys.argv[1], rows=rows), indent=2))
assert rows['VELDO-0216 concurrent-stages/same-verdicts'] is (not mutant)
assert all(ok for name,ok in rows.items() if not name.endswith('/same-verdicts'))
