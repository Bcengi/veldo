#!/usr/bin/env python3
"""Record the incremental-record row RED against 7bd70d2's production modules; verification is the full gate.

Runs this tree's suite with the three modules the fix changes (control_alias.py, control_store.py,
control_readset.py) taken from commit 7bd70d2 (the first recorded-numbers code, whose record held
the whole history of every accepted commit, and whose enabling still read the named revision's
commit from Git) and every other module from this tree, and writes red-at-7bd70d2.json: every row, which rows failed, and the
suite's own observations of each. A row counts as recorded RED only when the suite ran to
completion, so the row failed its assertion rather than raising.

NO SHIMS. The row calls only entry points 7bd70d2 already has (attach_revisions, accept, attach,
enable_kind, current, accepted_maximum) and finds each record by its kind and commit, not its id.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'proof/VELDO-0037'
REVIEWED = '7bd70d2'
MODULES = ('control_alias.py', 'control_store.py', 'control_readset.py')
DEFECT_ROWS = ('aliases/records-hold-only-what-a-commit-adds',)


def main():
    suite = ROOT / 'scripts/suites/59_veldo_0037_aliases.py'
    source = suite.read_text()
    digests = {}
    with tempfile.TemporaryDirectory(prefix='veldo-0037-red-') as directory:
        for name in MODULES:
            body = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:.veldo/%s' % (REVIEWED, name)],
                                  capture_output=True, check=True).stdout
            digests[name] = hashlib.sha256(body).hexdigest()
            (Path(directory) / name).write_bytes(body)
            anchor = 'ROOT / ".veldo" / "%s"' % name
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + anchor)
            source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(Path(directory) / name))
        rows = []
        namespace = {'ROOT': ROOT, '__file__': str(suite), 'expect': lambda name, ok: rows.append([name, bool(ok)])}
        exec(compile(source, str(suite), 'exec'), namespace)   # an exception here records nothing
    failed = [name for name, ok in rows if not ok]
    defects = namespace['_s37_observations']['defects']
    record = {'reviewed_commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', REVIEWED], capture_output=True,
                                                text=True, check=True).stdout.strip(),
              'module_sha256': digests, 'shims': {}, 'suite_sha256': hashlib.sha256(suite.read_bytes()).hexdigest(),
              'completed': True, 'rows': rows, 'failed_rows': failed,
              'defect_rows_red': {row: row in failed for row in DEFECT_ROWS},
              'defect_observations': {key: defects.get(key) for key in ('incremental-records',)},
              'veldo_history_record_paths': namespace['_s37_observations'].get('veldo-history-record-paths'),
              'veldo_history_floors': namespace['_s37_observations'].get('veldo-history-floors'),
              'verification': 'Diagnostic record; only bash scripts/verify.sh verifies the change.'}
    (OUT / 'red-at-7bd70d2.json').write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + '\n')
    print(json.dumps({'failed_rows': failed, 'all_defect_rows_red': all(record['defect_rows_red'].values())}))
    return 0 if set(failed) == set(DEFECT_ROWS) else 1


if __name__ == '__main__':
    sys.exit(main())
