#!/usr/bin/env python3
"""Write proof/VELDO-0204/mutations.json and one diff per finding-204 mutation, from the registry itself.
Nothing is executed: the reviewer runs `python3 scripts/check_teeth_mutations.py --finding 204`."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('v204_teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
entries = []
for case in teeth.cases():
    if case['finding'] != 204:
        continue
    path = ROOT / '.veldo' / case['module']
    source = path.read_text()
    mutant = teeth.mutate(source, case)
    diff = ''.join(difflib.unified_diff(source.splitlines(True), mutant.splitlines(True),
                                        'a/.veldo/' + case['module'], 'b/.veldo/' + case['module'], n=0))
    (HERE / (case['name'] + '.diff')).write_text(diff)
    entries.append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                        diff='proof/VELDO-0204/%s.diff' % case['name'],
                        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest(), executed=False))
(HERE / 'mutations.json').write_text(json.dumps(dict(schema='veldo.mutation-registration/v1', spec_id='VELDO-0204',
                                                     status='registered; reviewer execution required',
                                                     mutations=entries), indent=1) + '\n')
print(len(entries), 'mutations registered')
