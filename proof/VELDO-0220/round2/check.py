#!/usr/bin/env python3
"""Run only VELDO-0220 falsifiers, each executing the single ticket suite.

Every fixture uses a scratch lock. This driver never invokes the canonical gate.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
requested = sys.argv[1:]
cases = [c for c in teeth.cases() if c['finding'] == 220 and (not requested or c['name'] in requested)]
assert cases and (not requested or {c['name'] for c in cases} == set(requested))
for case in cases:
    for mode in ('mutant', 'baseline'):
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='v220-round2-') as directory:
            made = teeth.materialize(case, mode, directory, ROOT)
            result = teeth.worker(case, str(made['mutant']) if made['mutant'] else None)
        record = dict(case=case['name'], mode=mode, result=result,
                      old_digest=made['old_digest'], new_digest=made['new_digest'],
                      seconds=round(time.monotonic() - started, 2),
                      head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (ROOT / 'scripts/gate_host.py', ROOT / 'scripts/suites' / case['suite'],
                                         ROOT / 'scripts/check_teeth_mutations.py')})
        path = Path(__file__).parent / (case['name'] + '-' + mode + '.json')
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        print(case['name'], mode, result['targets'], flush=True)
        if mode == 'baseline':
            assert not result['failed_rows'], result['failed_details']
        else:
            assert all(result['targets'].values()) and all(
                values == [False] for values in result['targets'].values()), result
