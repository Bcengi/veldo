"""Run one registered falsifier with baseline/no-op controls in scratch copies.

Unit-level evidence only: no gate stage, host scope, load generator or benchmark.
"""
import difflib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    root = Path(__file__).resolve().parents[3]
    output = Path(__file__).resolve().parent
    driver = load(root / 'scripts/check_teeth_mutations.py')
    gate = load(root / 'scripts/check_gate_mutations.py')
    case = next(c for c in driver.cases() if c['name'] == sys.argv[1])
    assert case['finding'] == 362
    case = dict(case, driver='check_teeth_mutations.py',
                identity='check_teeth_mutations.py:' + case['name'])
    record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=case)
    with tempfile.TemporaryDirectory(prefix='veldo-0362-fix1-') as temporary:
        for mode in ('baseline', 'noop', 'mutant'):
            materialized = driver.materialize(case, mode, Path(temporary) / mode)
            record[mode] = driver.worker(case, str(materialized['mutant']) if materialized['mutant'] else None)
            print(case['name'], mode, record[mode]['failed_rows'], flush=True)
            if mode == 'mutant':
                record.update({k: materialized[k] for k in ('replacement_count', 'old_digest', 'new_digest')})
                before = materialized['source'].read_text()
                after = materialized['mutant'].read_text()
                (output / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                    before.splitlines(True), after.splitlines(True),
                    fromfile='a/scripts/' + case['module'], tofile='b/scripts/' + case['module'])))
    gate.validate_result(record, case)
    (output / (case['name'] + '.json')).write_text(json.dumps(record, indent=2) + '\n')
    print(case['name'], 'validated', record['kills'], flush=True)


if __name__ == '__main__':
    main()
