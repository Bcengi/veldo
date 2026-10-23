"""VELDO-0214 round 2: unregistered falsifiers for the new rows of suite 111 (review F1, F3, F4),
through the teeth driver's own materialize and worker. Each case must fail its target row. Prints
JSON; exit 0 only when every case is killed."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec); spec.loader.exec_module(teeth)
S = '111_veldo_0214_first_use_budget.py'
cases = [
 ('main-drops-budget-mutated-site-only', 'check_first_use.py',
  '            _, failed, names = _run_suite(tree, "mutated(%s)" % mut["family"], budget)\n',
  '            _, failed, names = _run_suite(tree, "mutated(%s)" % mut["family"])\n', 'measured-budget-used'),
 ('main-drops-budget-baseline-site-only', 'check_first_use.py',
  '                baseline = _run_suite(pristine, "baseline", budget)[2]\n',
  '                baseline = _run_suite(pristine, "baseline")[2]\n', 'measured-budget-used'),
 ('ceiling-removed', 'check_first_use.py',
  '    budget = min(max(RUN_TIMEOUT_S, derived), BUDGET_CEILING_S)\n',
  '    budget = max(RUN_TIMEOUT_S, derived)\n', 'ceiling-caps-the-budget'),
 ('cap-not-printed', 'check_first_use.py',
  '    if derived > BUDGET_CEILING_S:\n', '    if False:\n', 'ceiling-caps-the-budget'),
 ('non-finite-accepted', 'check_first_use.py',
  '    if not math.isfinite(derived):\n', '    if False:\n', 'non-finite-budget-refused'),
 ('store-never-pruned', 'gate_legs.py',
  '    prune_times(times, keep=target)\n', '', 'leg-time-store-pruned'),
 ('prune-ignores-gone-authority', 'gate_legs.py',
  "                stale = isinstance(authority, str) and authority != '' and not Path(authority).exists()\n",
  '                stale = False\n', 'leg-time-store-pruned'),
 ('owner-store-guard-removed', 'gate_legs.py',
  '            refusal = owner_store_refusal(times, path)\n', '            refusal = None\n',
  'suites-stay-out-of-the-owner-store'),
 ('temporary-authority-allowed', 'gate_legs.py',
  '    if authority == temporary or temporary in authority.parents:\n', '    if False:\n',
  'suites-stay-out-of-the-owner-store'),
]
out = []
for name, module, old, new, row in cases:
    case = dict(finding=214, name=name, suite=S, module=module, old=old, new=new, rows=[row], dir='scripts')
    with tempfile.TemporaryDirectory(prefix='v214b-hand-') as d:
        made = teeth.materialize(case, 'mutant', d, ROOT)
        result = teeth.worker(case, str(made['mutant']))
    ok = ('VELDO-0214 first-use-budget/' + row) in result['failed_rows']
    out.append({'case': name, 'module': module, 'replacement_count': made['replacement_count'],
                'target': row, 'failed_rows': result['failed_rows'], 'killed': ok})
print(json.dumps({'scope': 'unregistered hand falsifiers through check_teeth_mutations.materialize and worker', 'cases': out}, indent=1))
sys.exit(0 if all(o['killed'] for o in out) else 1)
