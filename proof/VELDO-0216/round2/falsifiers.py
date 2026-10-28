"""Run only this ticket's registered falsifiers and suite under the caller's flock."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
s = importlib.util.spec_from_file_location('teeth', ROOT/'scripts/check_teeth_mutations.py')
t = importlib.util.module_from_spec(s); s.loader.exec_module(t)
paths = ['scripts/gate_schedule.py','engine/scripts/gate_schedule.py','scripts/gate_graph.json',
         'scripts/gate_legs.py','engine/scripts/gate_legs.py','scripts/verify.sh','engine/scripts/verify.sh',
         'scripts/suites/114_veldo_0216_concurrent_stages.py','scripts/check_teeth_mutations.py']
identity = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
result = dict(head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
              source_sha256=identity, canonical_gate='NOT RUN: owner rule 37191', runs=[])
cases = [c for c in t.cases() if c['finding']==216]
assert len(cases)==4
for case in cases:
    for mode in ('mutant','baseline'):
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='v216-round2-') as directory:
            made = t.materialize(case,mode,directory,ROOT)
            rows = t.worker(case,str(made['mutant']) if made['mutant'] else None)
        observed = {n.split()[-1]:ok for n,ok in rows['observations'] if n.startswith('VELDO-0216 ')}
        record = dict(case=case['name'],mode=mode,rows=observed,
            target_rows=case['rows'],failed_rows=[n for n,ok in observed.items() if not ok],
            old_digest=made['old_digest'],new_digest=made['new_digest'],seconds=time.monotonic()-start)
        result['runs'].append(record)
        Path(__file__).with_name('falsifiers.json').write_text(json.dumps(result,indent=2)+'\n')
        print(case['name'],mode,record['failed_rows'],flush=True)
        assert all(observed.get(n) is False for n in case['rows']) if mode=='mutant' else all(observed.values())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in identity.items())
command = [sys.executable,'-I','-S','scripts/gate_candidate.py','--root',str(ROOT),'--',
           sys.executable,'scripts/selftest.py','--suite','114_veldo_0216_concurrent_stages']
p = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
Path(__file__).with_name('confined-suite.log').write_text(p.stdout+p.stderr)
assert p.returncode==2 and '48 passed, 0 failed' in p.stdout,p.stdout[-6000:]+p.stderr[-2000:]
result['confined_suite'] = dict(command=command,exit=p.returncode,ticket_rows=22,shared_preamble_rows=26,failed=0)
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in identity.items())
Path(__file__).with_name('falsifiers.json').write_text(json.dumps(result,indent=2)+'\n')
print('Four red then green falsifiers; confined suite 22 ticket rows green',flush=True)
