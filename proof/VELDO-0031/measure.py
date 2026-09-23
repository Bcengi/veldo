"""Measure this suite's gate workload with the real mutation-stage runner.

The in-memory inventory selector is for measurement only. The canonical gate is
always run separately with its full unchanged inventory. Includes a fresh frozen
input copy and the runner's baseline/no-op/mutant workers, not a sum of estimates.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mutation_stage', ROOT / 'scripts/check_gate_mutations.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
inventory = stage.inventory
stage.inventory = lambda root: [c for c in inventory(root) if c['driver'] == 'check_teeth_mutations.py' and c['finding'] == 31]
started = time.monotonic()
receipt = stage.run_stage(ROOT)
mutation_seconds = time.monotonic() - started
if receipt['status'] != 'passed':
    raise RuntimeError(receipt)
unit_seconds = []
for _ in range(2):  # unit and first-use integration each run the suite once
    start = time.monotonic()
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/selftest.py'),
                             '--suite', '58_veldo_0031_claims', '--suite', '59_veldo_0031_review'], cwd=ROOT, capture_output=True, text=True)
    if '35 passed, 0 failed' not in result.stdout:
        raise RuntimeError(result.stdout + result.stderr)
    unit_seconds.append(time.monotonic() - start)
print(json.dumps({'suite_runs_seconds': unit_seconds, 'mutation_stage_seconds': mutation_seconds,
                  'gate_added_workload_seconds': sum(unit_seconds) + mutation_seconds,
                  'mutations': receipt['executed'], 'workers': receipt['worker_invocations'],
                  'measurement': 'isolated added workload including snapshot overhead; full gate remains unfiltered'}, indent=2))
if sum(unit_seconds) + mutation_seconds > 60:
    raise SystemExit('STOP: added workload exceeds 60 seconds')
