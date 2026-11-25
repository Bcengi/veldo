"""Single-case baseline/no-op/mutant controls with fake coordinator children only."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'scripts/check_gate_mutations.py'
original = SOURCE.read_text()
support = runpy.run_path(str(ROOT / 'scripts/suites/support/v363_early.py'))


def module(source):
    obj = types.ModuleType('guard_gate')
    obj.__file__ = str(SOURCE)
    exec(compile(source, str(SOURCE), 'exec'), obj.__dict__)
    return obj


def observe(source, suite):
    rows = []
    def expect(name, ok):
        # The dispatcher's label ends at the colon; retain the assertion name.
        rows.append([name.split(': ', 1)[0], bool(ok)])
    if suite.startswith('98_'):
        support['checks'](module(source), expect)
    else:
        read = Path.read_text
        def patched(path, *a, **kw):
            return source if path == SOURCE else read(path, *a, **kw)
        path = ROOT / 'scripts/suites' / suite
        with patch.object(Path, 'read_text', patched):
            exec(compile(read(path), str(path), 'exec'),
                 dict(ROOT=ROOT, leg_runs=lambda *a: True, expect=expect))
    return dict(observations=rows, count=len(rows), row_names=[n for n, _ in rows],
                failed_rows=[n for n, ok in rows if not ok])


def main():
    spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    selected = [c for c in teeth.cases() if c['finding'] == 363]
    if len(sys.argv) > 1:
        selected = [c for c in selected if c['name'] in sys.argv[1:]]
    validator = module(original)
    results = []
    (HERE / 'mutations').mkdir(exist_ok=True)
    for c in selected:
        case = dict(c, driver=validator.DRIVERS[0], identity=validator.DRIVERS[0] + ':' + c['name'])
        broken = teeth.mutate(original, c)
        (HERE / 'mutations' / (c['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
            original.splitlines(True), broken.splitlines(True), n=0,
            fromfile='a/scripts/check_gate_mutations.py', tofile='b/scripts/check_gate_mutations.py')))
        entry = dict(name=c['name'], rows=c['rows'])
        try:
            record = dict(schema=validator.SCHEMA, fixture_version=validator.FIXTURE_VERSION,
                          case=case, replacement_count=1,
                          old_digest=hashlib.sha256(original.encode()).hexdigest(),
                          new_digest=hashlib.sha256(broken.encode()).hexdigest(),
                          baseline=observe(original, c['suite']), noop=observe(original, c['suite']),
                          mutant=observe(broken, c['suite']))
            validator.validate_result(record, case, baseline={'entries': []})
            entry.update(status='killed', kills=record['kills'],
                         baseline_rows=record['baseline']['count'], noop_agrees=True)
        except Exception as error:
            entry.update(status='invalid', detail=str(error))
        results.append(entry)
        print(c['name'], entry['status'], entry.get('detail', ''), flush=True)
    report = dict(kind='unit single-case controls; not a native gate receipt',
                  source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  registered=len(selected), killed=sum(r['status'] == 'killed' for r in results), results=results)
    (HERE / ('guards.json' if len(sys.argv) == 1 else 'guards-selected.json')).write_text(
        json.dumps(report, indent=2) + '\n')
    return int(report['killed'] != report['registered'])


if __name__ == '__main__':
    sys.exit(main())
