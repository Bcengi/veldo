"""Selected registered-worker diagnostics, not a confined mutation-stage receipt.

This exercises the registry's materializer and worker entry point on a compute
node that cannot run the pidfd/sandbox coordinator. The coordinator still runs
separately on the host. No source file is edited, and scratch is retained.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    driver = root / 'scripts/check_teeth_mutations.py'
    spec = importlib.util.spec_from_file_location('registered_teeth', driver)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = [case for case in module.cases() if case['finding'] == 253]
    scratch = Path(tempfile.mkdtemp(prefix='v253-registered-workers-'))
    results = []
    for case in cases:
        result = {'case': case['name'], 'rows': case['rows'], 'modes': {}}
        for mode in ('baseline', 'noop', 'mutant'):
            material = module.materialize(case, mode, scratch / case['name'] / mode, root=root)
            command = [sys.executable, '-B', str(driver), '--finding', '253', '--worker', case['name']]
            if material['mutant'] is not None:
                command += ['--mutant', str(material['mutant'])]
            completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=1800, check=True)
            observation = json.loads(completed.stdout)
            result['modes'][mode] = {key: observation[key] for key in ('count', 'failed_rows', 'targets')}
            result['modes'][mode].update({key: material[key] for key in ('replacement_count', 'old_digest', 'new_digest')})
        result['expected_red_green'] = (not result['modes']['baseline']['failed_rows']
            and not result['modes']['noop']['failed_rows']
            and all(result['modes']['mutant']['targets'][row] == [False] for row in case['rows']))
        results.append(result)
    report = {'scope': 'registered worker diagnostics; not the confined coordinator or full gate',
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'results': results}
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if len(results) == 4 and all(result['expected_red_green'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
