#!/usr/bin/env python3
"""Ticket-only falsifiers, red then green. Run under the owner's blocking flock.

No canonical gate, no other suite, no host-lock operation inside a fixture.
The teeth driver materializes mutants exclusively in scratch directories.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def main():
    spec = importlib.util.spec_from_file_location('teeth', ROOT/'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    cases = [c for c in teeth.cases() if c['finding'] == 216]
    assert len(cases) == 4
    paths = ['scripts/gate_schedule.py', 'scripts/gate_legs.py', 'scripts/gate_graph.json',
             'scripts/verify.sh', 'engine/scripts/verify.sh', 'scripts/check_gate_mutations.py',
             'scripts/suites/114_veldo_0216_concurrent_stages.py', 'scripts/check_teeth_mutations.py',
             'proof/VELDO-0216/qualification.py', 'proof/VELDO-0216/serial-baseline.json']
    evidence = {'schema': 'veldo.local-checks/v1', 'spec': 'VELDO-0216',
                'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'source_sha256': {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                'canonical_qualification': 'NOT RUN: owner rule 37191; see OPEN.md', 'runs': []}
    target = Path(__file__).with_name('red-green.json')
    print('Starting VELDO-0216 red then green checks at ' + evidence['head'], flush=True)
    for case in cases:
        for mode in ('mutant','baseline'):
            started = time.monotonic()
            with tempfile.TemporaryDirectory(prefix='veldo-0216-falsifier-') as directory:
                made = teeth.materialize(case,mode,directory,ROOT)
                result = teeth.worker(case,str(made['mutant']) if made['mutant'] else None)
            rows = {name.split()[-1]:ok for name,ok in result['observations'] if name.startswith('VELDO-0216 ')}
            evidence['runs'].append({'case':case['name'],'mode':mode,'target_rows':case['rows'],
                'old_digest':made['old_digest'],'new_digest':made['new_digest'],
                'rows':rows,'failed_rows':[n for n,ok in rows.items() if not ok],
                'seconds':time.monotonic()-started})
            target.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
            print(case['name'],mode,evidence['runs'][-1]['failed_rows'],flush=True)
            if mode == 'mutant':
                assert all(rows.get(r) is False for r in case['rows']), result['targets']
            else:
                assert rows and all(rows.values()), rows
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h
               for p,h in evidence['source_sha256'].items()), 'sources changed during proof'
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
