#!/usr/bin/env python3
"""Record the recorded-numbers rows RED against f84f2d2's production modules; verification is the full gate.

Runs this tree's suite with the three modules the fix changes (control_alias.py, control_store.py,
control_readset.py) taken from commit f84f2d2 (the round 4 code, in which the builder's lost-commit
probe found the floor skipping an accepted commit the bound repository no longer holds) and every
other module from this tree, and writes red-at-f84f2d2.json: every row, which rows failed, and the
suite's own observations of each. A row counts as recorded RED only when the suite ran to
completion, so the row failed its assertion rather than raising.

NO SHIMS. Both rows call only entry points f84f2d2 already has (attach_revisions, accept,
enable_kind, allocate, current). Row 14 is listed because the lead's decision changed what it
expects of a revision that records no numbers and whose commit is gone: a named refusal, not a skip.
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
REVIEWED = 'f84f2d2'
MODULES = ('control_alias.py', 'control_store.py', 'control_readset.py')
DEFECT_ROWS = ('aliases/floor-from-recorded-numbers', 'aliases/revision-in-enrolled-repository')


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
              'defect_observations': {key: defects.get(key) for key in ('recorded-numbers', 'enrolled-repository')},
              'verification': 'Diagnostic record; only bash scripts/verify.sh verifies the change.'}
    (OUT / 'red-at-f84f2d2.json').write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + '\n')
    print(json.dumps({'failed_rows': failed, 'all_defect_rows_red': all(record['defect_rows_red'].values())}))
    return 0 if set(failed) == set(DEFECT_ROWS) else 1


if __name__ == '__main__':
    sys.exit(main())
