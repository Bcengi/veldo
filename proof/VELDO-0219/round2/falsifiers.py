"""This ticket's registered controls only. Run under the owner's blocking flock."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True

def load(path):
    spec=importlib.util.spec_from_file_location(path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

teeth=load(ROOT/'scripts/check_teeth_mutations.py')
cases=[c for c in teeth.cases() if c['finding']==219]
assert len(cases)==4
paths=['scripts/'+n for n in ('gate_schedule.py','gate_graph.json','check_gate_mutations.py','mutation_ownership.py','reuse_worker.py','check_teeth_mutations.py','suites/115_veldo_0219_measured_admission.py')]
paths+=['engine/scripts/'+n for n in ('gate_schedule.py','check_gate_mutations.py','mutation_ownership.py','reuse_worker.py')]
paths+=['proof/VELDO-0219/round2/'+n for n in ('check.py','lifecycle_check.py','falsifiers.py')]
sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
evidence=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources=sources,runs=[],suites=[])
for case in cases:
    for mode in ('mutant','baseline','noop'):
        with tempfile.TemporaryDirectory(prefix='v219-r2-falsifier-') as tmp:
            made=teeth.materialize(case,mode,tmp,ROOT)
            result=teeth.worker(case,str(made['mutant']) if made['mutant'] else None)
        rows={name.split()[-1]:ok for name,ok in result['observations'] if name.startswith('VELDO-0219 ')}
        failed=[name for name,ok in rows.items() if not ok]
        evidence['runs'].append(dict(case=case['name'],mode=mode,rows=rows,failed=failed,
            old_digest=made['old_digest'],new_digest=made['new_digest']))
        (OUT/'falsifiers.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(case['name'],mode,failed,flush=True)
        assert rows and (all(rows.get(r) is False for r in case['rows']) if mode=='mutant' else not failed),result
for suite in ('115_veldo_0219_measured_admission',):
    result=subprocess.run([sys.executable,'-B','scripts/selftest.py','--suite',suite],cwd=ROOT,capture_output=True,text=True)
    (OUT/(suite+'.log')).write_text(result.stdout+result.stderr)
    summary=[line for line in result.stdout.splitlines() if line.startswith('selftest (PARTIAL')]
    evidence['suites'].append(dict(suite=suite,exit=result.returncode,summary=summary))
    (OUT/'falsifiers.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(suite,result.returncode,summary,flush=True)
    assert result.returncode==2 and summary and '0 failed' in summary[0]
native=subprocess.run([sys.executable,'-B',str(OUT/'lifecycle_check.py')],cwd=ROOT,capture_output=True,text=True)
(OUT/'lifecycle-final-green.json').write_text(native.stdout)
assert native.returncode==0,native.stdout+native.stderr
evidence['native_lifecycle']=json.loads(native.stdout)
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sources.items())
evidence['passed']=True
(OUT/'falsifiers.json').write_text(json.dumps(evidence,indent=2)+'\n')
