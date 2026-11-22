"""Portable B1 falsifier reproduction using the registered driver's worker API.

No confinement or process-manager claim. Each fresh process runs the complete
fixture suite. Exceptions, missing rows, and timeouts are errors, never kills.
Run from the checkout: python3 -B proof/VELDO-0359/b1-mutation-controls.py
"""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'scripts/check_teeth_mutations.py'
spec = importlib.util.spec_from_file_location('b1_registry', DRIVER)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)
cases = [c for c in registry.cases() if c['finding'] == 359 and c['suite'] == '157_veldo_0359_run_query.py']
assert len(cases) == 16


def run(case, mode, directory):
    prepared = registry.materialize(case, mode, directory, root=ROOT)
    argv = [sys.executable, '-B', str(DRIVER), '--worker', case['name']]
    if prepared['mutant'] is not None:
        argv += ['--mutant', str(prepared['mutant'])]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError('%s/%s worker error: %s' % (case['name'], mode, result.stderr[-3000:]))
    observed = json.loads(result.stdout)
    target = observed['targets']
    present = all(target.get(row) for row in case['rows'])
    if mode == 'mutant':
        passed = present and all(not all(target[row]) for row in case['rows'])
    else:
        passed = present and not observed['failed_rows']
    return dict(case=case['name'], mode=mode, passed=passed, targets=target,
                failed_rows=observed['failed_rows'], failed_details=observed['failed_details'],
                source_sha256=prepared['old_digest'], tested_sha256=prepared['new_digest'])


with tempfile.TemporaryDirectory(prefix='b1-controls-') as scratch:
    directory = Path(scratch)
    # One whole-suite baseline; one no-op per production module, then each defect.
    results = [run(cases[0], 'baseline', directory / 'baseline')]
    modules = {}
    for case in cases:
        modules.setdefault(case['module'], case)
    jobs = [(case, 'noop') for case in modules.values()] + [(case, 'mutant') for case in cases]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run, case, mode, directory / (mode + '-' + case['name'])) for case, mode in jobs]
        for future in futures:
            results.append(future.result())
    report = dict(schema='veldo.b1_query_controls/v1',
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  suite_sha256=hashlib.sha256((ROOT / 'scripts/suites/157_veldo_0359_run_query.py').read_bytes()).hexdigest(),
                  results=results, passed=all(r['passed'] for r in results))
    output = json.dumps(report, sort_keys=True, indent=2) + '\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output)
    print(output)
    sys.exit(0 if report['passed'] else 1)
