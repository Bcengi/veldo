#!/usr/bin/env python3
"""VELDO-0271: the row and mutation case inventory of a checkout, and the two files built from it.

  record_rows.py record <checkout root> <out.json>
      Runs <root>/scripts/selftest.py whole, in that checkout, and records for every suite the name of
      every row it asserts (the label before its first colon, the identity the mutation observer uses),
      and the identity of every registered mutation case. The dispatcher is the checkout's own and is
      not changed: the shared namespace's expect is wrapped as it is loaded. The run's aggregate line
      and exit status are recorded too.

  record_rows.py merge <before.json> <after.json> <removed.json> <rows.json> <summary.json>
      Writes rows.json, what the suite row removed/table-lists-every-removed-row reads: the row names of
      every suite whose rows differ between the two records (or that only one of them has), the suites a
      table entry names as still covering a removed row, and the case identities only one record has.
      Writes the proof summary beside it, with the size and sha256 of the two full records, which are
      then discarded.

Standard library only. Nothing is written outside the two paths named on the command line.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def record(root, out):
    root = Path(root).resolve()
    rows, said = {}, []
    original = importlib.machinery.SourceFileLoader.exec_module

    def exec_module(self, module):
        original(self, module)
        if module.__name__ == 'shared' and callable(getattr(module, 'expect', None)):
            inner = module.expect

            def expect(name, condition):
                suite = Path(module.__dict__.get('__suite_file__', 'shared')).stem
                rows.setdefault(suite, set()).add(str(name).split(':', 1)[0])
                return inner(name, condition)
            module.expect = expect

            inner_report = module.report

            def report():
                said.append(module.SCOPE.aggregate_line(module.PASS, module.FAIL))
                return inner_report()
            module.report = report

    importlib.machinery.SourceFileLoader.exec_module = exec_module
    os.chdir(root)
    sys.argv = [str(root / 'scripts/selftest.py')]
    sys.path[0] = str(root / 'scripts')
    try:
        runpy.run_path(str(root / 'scripts/selftest.py'), run_name='__main__')
        code = 0
    except SystemExit as exit_:
        code = exit_.code
    finally:
        importlib.machinery.SourceFileLoader.exec_module = original
    cases = []
    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
        spec = importlib.util.spec_from_file_location('record_' + driver[:-3], root / 'scripts' / driver)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases += ['%s:%s' % (driver, case['name']) for case in module.cases()]
    commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, text=True).stdout
    document = {'commit': commit, 'dirty_paths': len(dirty.splitlines()), 'exit': code,
                'aggregate': said[-1] if said else None,
                'rows': {suite: sorted(names) for suite, names in sorted(rows.items())}, 'cases': sorted(cases)}
    Path(out).write_text(json.dumps(document, indent=1, sort_keys=True) + '\n')
    print('recorded %d suites, %d rows, %d cases, exit %s: %s'
          % (len(rows), sum(len(v) for v in rows.values()), len(cases), code, document['aggregate']))
    return 0


def merge(before_path, after_path, removed_path, rows_path, summary_path):
    raw = {name: Path(path).read_bytes() for name, path in (('before', before_path), ('after', after_path))}
    before, after = json.loads(raw['before']), json.loads(raw['after'])
    table = json.loads(Path(removed_path).read_text())
    still = {entry['now'] for entry in table['removed'] if entry['now'] != 'confinement only'}
    suites = set(before['rows']) | set(after['rows'])
    differ = {s for s in suites if before['rows'].get(s) != after['rows'].get(s)}
    covering = {s for s, names in after['rows'].items() if still & set(names)}

    def part(record, keep):
        return {'commit': record['commit'], 'aggregate': record['aggregate'], 'exit': record['exit'],
                'suites': len(record['rows']), 'rows_total': sum(len(v) for v in record['rows'].values()),
                'cases_total': len(record['cases']),
                'rows': {s: record['rows'][s] for s in sorted(keep) if s in record['rows']}}
    document = {'schema': 'veldo.removed-rows/v1',
                'note': 'Row names per suite, for the suites whose rows differ between the two records and '
                        'the suites the table names as still covering a removed row; case identities that '
                        'only one record has. Built by proof/VELDO-0271/record_rows.py merge.',
                'at_24c9f5b4': dict(part(before, differ), cases=sorted(set(before['cases']) - set(after['cases']))),
                'after': dict(part(after, differ | covering), cases=sorted(set(after['cases']) - set(before['cases'])))}
    Path(rows_path).write_text(json.dumps(document, indent=1, sort_keys=True) + '\n')
    removed_rows = sum(len(set(before['rows'][s]) - set(after['rows'].get(s, []))) for s in before['rows'])
    added_rows = sum(len(set(after['rows'][s]) - set(before['rows'].get(s, []))) for s in after['rows'])
    spec = importlib.util.spec_from_file_location('record_validate', ROOT / '.veldo/validate.py')
    validate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate)
    deciding = {
        'before': {k: document['at_24c9f5b4'][k] for k in ('commit', 'aggregate', 'exit', 'suites', 'rows_total', 'cases_total')},
        'after': {k: document['after'][k] for k in ('commit', 'aggregate', 'exit', 'suites', 'rows_total', 'cases_total')},
        'suites_removed': sorted(set(before['rows']) - set(after['rows'])),
        'suites_added': sorted(set(after['rows']) - set(before['rows'])),
        'suites_with_different_rows': len(differ), 'row_names_removed': removed_rows, 'row_names_added': added_rows,
        'cases_removed': document['at_24c9f5b4']['cases'], 'cases_added': document['after']['cases'],
        'table_entries': len(table['removed']),
        'verdict': 'the suite row removed/table-lists-every-removed-row compares rows.json with removed.json'}
    validate.write_proof_summary(summary_path, 'python3 proof/VELDO-0271/record_rows.py ' + ' '.join(sys.argv[1:]), deciding,
                                 discarded=[('rows-at-24c9f5b4.json', raw['before']), ('rows-after.json', raw['after'])],
                                 timing=False)
    print('rows.json: %d suites differ, %d row names removed, %d added, %d cases removed, %d added'
          % (len(differ), removed_rows, added_rows, len(document['at_24c9f5b4']['cases']), len(document['after']['cases'])))
    return 0


def main(argv):
    if len(argv) == 3 and argv[0] == 'record':
        return record(argv[1], argv[2])
    if len(argv) == 6 and argv[0] == 'merge':
        return merge(*argv[1:])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
