#!/usr/bin/env python3
"""Native ticket check inside the owner's outer flock, without any lock API.

Creates only its own delegated scope and one uniquely named fixture service.
Never invokes verify.sh or reads gate_host.json.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name):
    path = ROOT / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    evidence = dict(spec='VELDO-0219', check='native-cgroup-children', passed=False, runs=[],
                    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                             ('scripts/mutation_ownership.py','scripts/reuse_worker.py')})
    meters, processes, unit = [], [], None
    try:
        host, owner = load('gate_host'), load('mutation_ownership')
        scope_name, scope = host.make_scope(dict(memory_max=2**30, oom_score_adj=900))
        evidence['scope'] = scope_name
        with tempfile.TemporaryDirectory(prefix='v219-kernel-') as temporary:
            home = Path(temporary)
            ledger = home / 'ownership.jsonl'
            ledger.write_text('')
            # The child reports process CPU, independent of the coordinator's
            # kernel counters. 256 MiB leaves interpreter overhead below 10%.
            payload = """import json,sys,time
b=bytearray(256*1024*1024)
start=time.process_time()
while time.process_time()-start < 1.0: pass
time.sleep(float(sys.argv[1]))
print(json.dumps(dict(cpu_seconds=time.process_time(),memory=256*1024*1024)),flush=True)
"""
            for index, delay in enumerate((.1,.6)):
                meter = owner.WorkerMeter(scope, str(index))
                meters.append(meter)
                join = meter.open_join()
                boot = """import importlib.util,os,subprocess,sys
s=importlib.util.spec_from_file_location('boot',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.join_worker_cgroup()
p=subprocess.run([sys.executable,'-c',sys.argv[2],sys.argv[3]],check=True)
"""
                start = time.monotonic()
                process = subprocess.Popen([sys.executable,'-I','-B','-c',boot,
                    str(ROOT/'scripts/reuse_worker.py'),payload,str(delay)],
                    env=dict(os.environ,VELDO_MUTATION_CGROUP_FD=str(join)),pass_fds=(join,),
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                processes.append(process)
                os.close(join)
                while process.poll() is None:
                    metrics = meter.sample(home,ledger)
                    time.sleep(.01)
                out,err = process.communicate()
                assert process.returncode == 0, err
                actual = json.loads(out)
                metrics = meter.sample(home,ledger)
                elapsed = time.monotonic()-start
                cpu_error = abs(metrics['cpu_seconds']/actual['cpu_seconds']-1)
                memory_error = abs(metrics['peak_anon_bytes']/actual['memory']-1)
                assert cpu_error <= .1 and memory_error <= .1, (metrics,actual,cpu_error,memory_error)
                evidence['runs'].append(dict(metrics=metrics,elapsed=elapsed,known=actual,
                                              cpu_relative_error=cpu_error,memory_relative_error=memory_error))
                meter.close()
            # A real user unit is owned in the same ledger used by cleanup. A
            # foreground systemd-run client waits for this one service only.
            unit = 'veldo-authority-' + secrets.token_hex(12) + '.service'
            service_file = owner.unit_directory()/unit
            ledger.write_text(json.dumps(['service',str(service_file)])+'\n')
            meter = owner.WorkerMeter(scope,'unit')
            meters.append(meter)
            process = subprocess.Popen(['systemd-run','--user','--wait','--pipe','--quiet',
                '--unit='+unit,sys.executable,'-I','-B','-c',payload,'.4'],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            processes.append(process)
            while process.poll() is None:
                meter.sample(home,ledger)
                time.sleep(.01)
            out,err = process.communicate()
            assert process.returncode == 0, err
            actual = json.loads(out)
            metrics = meter.sample(home,ledger)
            cpu_error = abs(metrics['cpu_seconds']/actual['cpu_seconds']-1)
            memory_error = abs(metrics['peak_anon_bytes']/actual['memory']-1)
            assert cpu_error <= .1 and memory_error <= .1, (metrics,actual,cpu_error,memory_error)
            assert any(unit in path for path in metrics['cgroups'])
            evidence['runs'].append(dict(unit=unit,metrics=metrics,known=actual,
                cpu_relative_error=cpu_error,memory_relative_error=memory_error))
            owner.cleanup(home,ledger)
            meter.close()
            unit = None
        evidence['passed'] = True
    except Exception as error:
        evidence['error'] = repr(error)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait()
        if unit:
            subprocess.run(['systemctl','--user','stop',unit],capture_output=True)
            subprocess.run(['systemctl','--user','reset-failed',unit],capture_output=True)
        for meter in meters:
            if meter.path.exists():
                meter.close()
        Path(__file__).with_name('kernel.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence),flush=True)
    return int(not evidence['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
