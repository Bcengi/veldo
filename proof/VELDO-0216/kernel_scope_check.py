#!/usr/bin/env python3
"""Ticket-only live node-cgroup check, run inside the owner's outer flock.

Creates only this process's scope via the unchanged VELDO-0220 helper. It does
not call gate_host.enter/take, read its host config, or manipulate any host lock.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name):
    path = ROOT/'scripts'/(name+'.py')
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    evidence = {'spec':'VELDO-0216','check':'live-node-cgroup','passed':False,
                'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'scheduler_sha256':hashlib.sha256((ROOT/'scripts/gate_schedule.py').read_bytes()).hexdigest()}
    process, meter = None, None
    try:
        host, scheduler = load('gate_host'), load('gate_schedule')
        name, scope = host.make_scope({'memory_max':512*2**20,'oom_score_adj':900})
        capacity = scheduler.capacities({'reserve':{'cpu':0,'memory':32*2**20}},scope,ROOT/'scripts/suites/manifest.json')
        assert capacity['memory']==480*2**20 and capacity['cpu']<=len(os.sched_getaffinity(0))
        meter = scheduler.Meter(scope,'probe')
        payload = 'import time; b=bytearray(32*1024*1024); end=time.monotonic()+.3\nwhile time.monotonic()<end: pass\ntime.sleep(.15)'
        process = subprocess.Popen(meter.command([sys.executable,'-c',payload]))
        while process.poll() is None:
            meter.sample()
            time.sleep(.02)
        metrics = meter.finish()
        assert process.returncode==0 and metrics['cpu_seconds']>=.2 and metrics['peak_anon_bytes']>=32*2**20
        assert metrics['live_descendants'] is False and not meter.path.exists()
        evidence.update(passed=True,scope=name,capacity=capacity,metrics=metrics)
    except Exception as error:
        evidence['error'] = str(error)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        if meter is not None and meter.path.exists():
            meter.finish()
        Path(__file__).with_name('kernel-scope.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence),flush=True)
    return int(not evidence['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
