"""Bounded real-worker comparison; no full gate or leg. Run from an immutable scratch snapshot."""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


def load(root, name):
    path = root / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial(root, output, mode):
    gate = load(root, 'check_gate_mutations')
    host = load(root, 'gate_host')
    scheduler = load(root, 'gate_schedule')
    ownership = load(root, 'mutation_ownership')
    config = host.load()
    # Use the existing cap and delegation implementation, never a higher host limit.
    name, scope = host.make_scope(config['scope'])
    os.environ[host.SCOPE_ENV] = scope
    cg = Path('/sys/fs/cgroup') / scope.lstrip('/')
    graph = json.loads((root / 'scripts/gate_graph.json').read_text())
    capacity = scheduler.capacities(graph, scope, root / 'scripts/suites/manifest.json')
    ledger = scheduler.Ledger(capacity, graph['mutation_floor'])
    overhead = graph['nodes']['mutation']['coordinator']
    ledger.acquire('coordinator', overhead, mutation=True)
    floor = {r: graph['mutation_floor'][r] - overhead[r] for r in ('cpu', 'memory')}
    class Client:
        last_reply = {}
        def acquire(self, name, cpu, memory, manager='none'):
            granted = ledger.acquire(name, dict(cpu=cpu,memory=memory,manager=manager,ports=[]),mutation=True)
            self.last_reply = dict(totals=ledger.totals(),resource=ledger.blocking_resource)
            return granted
        def release(self, name):
            ledger.release(name)
        def close(self):
            pass
    admission = gate.Admission(Client(),capacity,floor,lambda n:ownership.WorkerMeter(scope,n))
    real_claims, real_times, real_resources = gate.CaseClaims, gate.record_case_times, gate.record_case_resources
    real_deadlines = gate.case_deadlines
    real_pool = gate.SuiteResources.from_root
    def pool(*args):
        resources = real_pool(*args)
        resources.capacity['load_generator'] = 1
        resources.used['load_generator'] = resources.peak['load_generator'] = 0
        resources.requirements['160_veldo_0358_load_leg.py']['load_generator'] = 1
        return resources
    names = json.loads((output / 'selection.json').read_text())
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(gate,'CaseClaims',lambda:real_claims(output / ('empty' if mode=='default' else 'resources'))))
        stack.enter_context(patch.object(gate,'case_deadlines',lambda keys:real_deadlines(keys,output/'estimate-empty')))
        stack.enter_context(patch.object(gate,'record_case_times',lambda r,s,authority=False:real_times(r,s,output/'elapsed',authority=authority)))
        stack.enter_context(patch.object(gate,'record_case_resources',lambda c,k,o,g,authority=False:real_resources(c,k,o,g,output/'resources',authority=authority)))
        stack.enter_context(patch.object(gate.SuiteResources,'from_root',pool))
        result = gate.run_stage(root,gate.common_directory(root),names=names,admission=admission,
                    parallel=gate.worker_count(),leg=load(root,'gate_legs').mutation_leg(),measure=True,
                    force_fresh=True,log_dir=output/(mode+'-workers'))
    result['bounded_host'] = dict(scope=scope,memory_max=int((cg/'memory.max').read_text()),
        memory_peak=int((cg/'memory.peak').read_text()), memory_events=(cg/'memory.events').read_text(),
        cpu_stat=(cg/'cpu.stat').read_text(), ledger_peak=ledger.peak)
    (output/(mode+'.json')).write_text(json.dumps(result,sort_keys=True))
    print(json.dumps({k:result.get(k) for k in ('status','error','detail','registered','executed','rejected','elapsed','peak_workers','resource_sample_error','bounded_host')}),flush=True)
    return 0


def main():
    root,output = Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()
    if len(sys.argv)>3:
        return trial(root,output,sys.argv[3])
    host=load(root,'gate_host')
    config=host.load()
    output.mkdir(parents=True,exist_ok=True)
    with open(config['lock'],'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        if host.holders(config['lock']):
            raise RuntimeError('gate lock held exclusively')
        for mode in ('default','calibrated'):
            with (output/(mode+'.log')).open('w') as log:
                subprocess.run([sys.executable,'-B',__file__,str(root),str(output),mode],
                               stdout=log,stderr=subprocess.STDOUT,check=True)
    return 0


if __name__=='__main__':
    sys.exit(main())
