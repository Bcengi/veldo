"""Measure only the added gate work; this never substitutes for the full gate."""
import json
from pathlib import Path
import subprocess
import sys
import time
from measure import load, ROOT

started = time.monotonic()
unit = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '57_veldo_0120_policygrammar'],
                      cwd=ROOT, capture_output=True, text=True)
unit_seconds = time.monotonic() - started
assert unit.returncode == 2 and '29 passed, 0 failed' in unit.stdout, unit.stdout + unit.stderr
stage = load('mutation_stage', ROOT / 'scripts/check_gate_mutations.py')
inventory = stage.inventory
stage.inventory = lambda root: [case for case in inventory(root) if case.get('finding') == 120]
receipt = stage.run_stage()
result = dict(unit_seconds=unit_seconds, added_mutation_stage=receipt,
              conservative_added_gate_seconds=2 * unit_seconds + receipt['elapsed'],
              method='two unit executions (unit and first-use integration), plus isolated added mutations including setup')
Path(sys.argv[1]).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'added_mutation_stage'}))
print(receipt['status'], receipt.get('detail', ''), receipt['registered'], receipt['rejected'])
raise SystemExit(0 if receipt['status'] == 'passed' and result['conservative_added_gate_seconds'] <= 60 else 1)
