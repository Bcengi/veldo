"""Ticket-local inventory anchor scan and immutable selection verification; no worker runs."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gate', root / 'scripts/check_gate_mutations.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
observer = gate.load(root / 'scripts/mutation_observer.py')
cases = gate.inventory_local(root)
stale = []
for case in cases:
    path = root / ('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')) / case['module']
    try:
        observer.mutate(path.read_bytes(), case)
    except Exception as error:
        stale.append(dict(identity=case['identity'], error=str(error)))
expected = json.loads((root / 'proof/VELDO-0364/expected.json').read_text())
by_name = {c['name']: c for c in cases}
selection_ok = all(by_name.get(v['case']['name']) == v['case'] for v in expected)
result = dict(count=len(stale), stale=stale, inventory=len(cases), selection_unchanged=selection_ok)
print(json.dumps(result, indent=2))
sys.exit(bool(stale) or not selection_ok)
