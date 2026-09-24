#!/usr/bin/env python3
"""Record the review-defect rows RED against adfb89a's production modules; verification is the full gate.

Runs this tree's suite with control_alias.py and control_document.py taken from commit adfb89a
(the reviewed implementation) and every other module from this tree, and writes
red-at-adfb89a.json: every row, which rows failed, and the suite's own observations of each defect.
A row counts as recorded RED only when the suite ran to completion, so the row failed its
assertion rather than raising.
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
REVIEWED = 'adfb89a'
MODULES = ('control_alias.py', 'control_document.py')
DEFECT_ROWS = ('publication/no-symlink-escape', 'aliases/one-path-per-kind', 'aliases/historical-floor',
               'publication/recorded-only-by-publisher', 'aliases/generic-writes-refused',
               'publication/bound-to-repository', 'aliases/case-insensitive-names', 'aliases/reserved-directories')


def main():
    suite = ROOT / 'scripts/suites/59_veldo_0037_aliases.py'
    source = suite.read_text()
    digests = {}
    with tempfile.TemporaryDirectory(prefix='veldo-0037-red-') as directory:
        for name in MODULES:
            body = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:.veldo/%s' % (REVIEWED, name)],
                                  capture_output=True, check=True).stdout
            (Path(directory) / name).write_bytes(body)
            digests[name] = hashlib.sha256(body).hexdigest()
            anchor = 'ROOT / ".veldo" / "%s"' % name
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + anchor)
            source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(Path(directory) / name))
        rows = []
        namespace = {'ROOT': ROOT, '__file__': str(suite), 'expect': lambda name, ok: rows.append([name, bool(ok)])}
        exec(compile(source, str(suite), 'exec'), namespace)   # an exception here records nothing
    failed = [name for name, ok in rows if not ok]
    record = {'reviewed_commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', REVIEWED], capture_output=True,
                                                text=True, check=True).stdout.strip(),
              'module_sha256': digests, 'suite_sha256': hashlib.sha256(suite.read_bytes()).hexdigest(),
              'completed': True, 'rows': rows, 'failed_rows': failed,
              'defect_rows_red': {row: row in failed for row in DEFECT_ROWS},
              'defect_observations': namespace['_s37_observations']['defects'],
              'verification': 'Diagnostic record; only bash scripts/verify.sh verifies the change.'}
    (OUT / 'red-at-adfb89a.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'failed_rows': failed, 'all_defect_rows_red': all(record['defect_rows_red'].values())}))
    return 0 if set(failed) == set(DEFECT_ROWS) else 1


if __name__ == '__main__':
    sys.exit(main())
