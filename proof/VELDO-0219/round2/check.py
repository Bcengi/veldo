"""Round two ticket regressions. All state and test locks live in scratch directories."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True

def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def handoff(gate=None):
    schedule = load(ROOT/'scripts/gate_schedule.py')
    with tempfile.TemporaryDirectory(prefix='v219-channel-') as tmp:
        top = Path(tmp)
        graph = json.loads((ROOT/'scripts/gate_graph.json').read_text())
        graph['nodes'] = {'mutation': graph['nodes']['mutation']}
        (top/'graph.json').write_text(json.dumps(graph))
        # Real subprocesses and the production inherited channel; only kernel
        # cgroup creation is replaced so this also runs inside confinement.
        child = top/'child.py'
        child.write_text('''import importlib.util,json,sys,time,subprocess
from pathlib import Path
s=importlib.util.spec_from_file_location('gate',sys.argv[1]);g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
g.ROOT=Path(sys.argv[2])
a=g.Admission.authority()
pool=g.SuiteResources(dict(resource_capacities={'systemd_user_manager':16},suites=[dict(file='x.py',resources={'systemd_user_manager':1})]))
job=dict(case=dict(suite='x.py'),claim=dict(cpu=1,memory=1048576,source='default'))
assert a.acquire('one',job,pool)
p=subprocess.Popen([sys.executable,'-c','print("worker ran")'],stdout=subprocess.PIPE,text=True)
out,_=p.communicate(timeout=10)
assert p.returncode==0 and 'worker ran' in out
assert a.acquire('two',job,pool)
a.release('one');a.release('two')
Path(sys.argv[3]).write_text(json.dumps(a.events))
a.close()
''')
        class Meter:
            def command(self, argv): return argv
            def sample(self): return dict(cpu_seconds=.01,peak_anon_bytes=1024)
            def finish(self): return self.sample()
        target = Path(gate.__file__) if gate else ROOT/'scripts/check_gate_mutations.py'
        with patch.object(schedule,'command_for',lambda *a:[sys.executable,'-B',str(child),str(target),str(ROOT),str(top/'events.json')]), contextlib.redirect_stdout(io.StringIO()):
            result = schedule.run({'mutation':'fixture'},top,top/'logs',top/'legs',top/'receipt',
                graph_path=top/'graph.json',declaration_path=top/'absent',
                capacity=dict(cpu=20,memory=15*2**30,manager=16),measurement_store=top/'times',
                meter_factory=lambda n:Meter(),guard_factory=lambda r:lambda:True)
        ok = result['stages']['mutation']=='pass'
        events=json.loads((top/'events.json').read_text()) if ok else []
        transfers=[e for e in result['ledger'] if e['action']=='handoff']
        return ok and len(transfers)==1 and transfers[0]['granted']['manager']==0 and len(events)==2

def fixed_cap(gate):
    with patch.object(gate,'worker_count',lambda *a:40), patch.object(gate,'PARALLEL',40):
        return gate.Workers(time.monotonic()+60).parallel==16 and gate.Workers(time.monotonic()+60,admission=object()).parallel==40

def per_run(gate):
    return gate.resource_claim([dict(cpu_seconds=8,elapsed=10,peak_anon_bytes=1),dict(cpu_seconds=12,elapsed=20,peak_anon_bytes=2)])==dict(cpu=.8,memory=2)

def blocking_resource(gate):
    class Client:
        last_reply = {}
        def acquire(self, *args): return self.last_reply['granted']
    client=Client()
    a=gate.Admission(client,dict(cpu=20,memory=15*2**30),dict(cpu=10,memory=8*2**30))
    pool=gate.SuiteResources(dict(resource_capacities={'systemd_user_manager':16},suites=[dict(file='x.py')]))
    job=dict(case=dict(suite='x.py'),claim=dict(cpu=1,memory=1024,source='this_key'))
    for resource in ('cpu','memory','manager'):
        client.last_reply=dict(granted=False,resource=resource,totals=dict(cpu=9,memory=4096,manager=16))
        if a.acquire('waiter',job,pool): return False
    client.last_reply=dict(granted=True,resource=None,totals=dict(cpu=10,memory=5120,manager=1))
    return a.acquire('waiter',job,pool) and a.events[-1]['resource']==['cpu','manager','memory'] and a.events[-1]['granted']==client.last_reply['totals']

def main():
    gate=load(ROOT/'scripts/check_gate_mutations.py')
    checks={}
    for name,check in [('handoff',lambda:handoff(gate)),('fixed-cap',lambda:fixed_cap(gate)),('cpu-per-run',lambda:per_run(gate)),('blocking-resource',lambda:blocking_resource(gate))]:
        try: checks[name]=bool(check())
        except Exception as e: checks[name]=str(e)
    print(json.dumps(checks,indent=2))
    return int(any(v is not True for v in checks.values()))
if __name__=='__main__': raise SystemExit(main())
