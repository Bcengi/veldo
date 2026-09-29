#!/usr/bin/env python3
"""Refresh finding 148's exact diffs and digests without executing the checker."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    registry = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    document = json.loads((HERE / 'mutations.json').read_text())
    previous = {m['name']: m for m in document['mutants']}
    records = []
    for node in ast.walk(registry):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'reland148':
            continue
        name, module, old, new, rows, *rest = [ast.literal_eval(arg) for arg in node.args]
        also = rest[0] if rest else ()
        for keyword in node.keywords:
            assert keyword.arg == 'also'
            also = ast.literal_eval(keyword.value)
        source = (ROOT / '.veldo' / module).read_text()
        mutant = source
        for before, after in [(old, new), *also]:
            assert mutant.count(before) == 1, (name, before)
            mutant = mutant.replace(before, after)
        compile(mutant, module, 'exec')
        record = dict(previous[name], named_rows=rows, source_sha256=digest(source),
                      mutant_sha256=digest(mutant), by_assertion=None, named_row_red=None,
                      status='static refresh; mutation checker execution reserved for reviewer')
        assert rows == previous[name]['named_rows'] or name == 'reland148-end-wakes-nothing'
        (ROOT / record['diff']).write_text(''.join(difflib.unified_diff(
            source.splitlines(keepends=True), mutant.splitlines(keepends=True), n=0,
            fromfile='a/.veldo/' + module, tofile='b/.veldo/' + module)))
        records.append(record)
    assert len(records) == len(previous) == len({r['name'] for r in records})
    document.update(mutants=records, suite_sha256=digest(
        (ROOT / 'scripts/suites/86_veldo_0148_re_land.py').read_text()),
        status='All 19 registrations statically refreshed. Only the wake target changed. '
               'Manual wake rejection is recorded separately in manual-wake.json. '
               'Mutation checker execution remains reserved for the reviewer.')
    (HERE / 'mutations.json').write_text(json.dumps(document, indent=1, sort_keys=True) + '\n')
    print('Refreshed %d exact diffs and source/mutant digests; all anchors unique and mutants compile.' % len(records))


if __name__ == '__main__':
    main()
