"""One ticket file: a unit exits completely between authority discovery polls."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode=True

def load(path):
    spec=importlib.util.spec_from_file_location('ownership',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def check(owner):
    if not hasattr(owner.WorkerMeter,'prepare_unit'):
        return dict(passed=False,error='no lifecycle accounting before units start')
    unit='veldo219'+secrets.token_hex(6)+'.slice'
    processes=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'scope').mkdir()
        meter=owner.WorkerMeter('/scope','fixture',root)
        # Only the worker cgroup is fake; the separate unit and its parent use
        # the real user manager and real kernel counters.
        (meter.path/'cpu.stat').write_text('usage_usec 0\n')
        (meter.path/'memory.stat').write_text('anon 0\n')
        meter.root=Path('/sys/fs/cgroup')
        measured=[]
        try:
            meter.prepare_unit('slice',unit)
            for cycle in range(2):
                if cycle:
                    owner.RetainedSlice.ctl('start',unit)
                    meter.retained[unit].sample(final=True)
                name='veldo-authority-'+secrets.token_hex(6)+'.service'
                code='import time,json; memory=bytearray(32*1024*1024); start=time.process_time()\nwhile time.process_time()-start<.04: pass\nprint(json.dumps(time.process_time()))'
                p=subprocess.Popen(['systemd-run','--user','--wait','--pipe','--quiet','--unit='+name,'--slice='+unit,
                                    sys.executable,'-I','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                processes.append(p)
                out,err=p.communicate(timeout=20)
                assert p.returncode==0,err
                known=json.loads(out)
                # No discovery or sample happened while this short unit lived.
                value=meter.sample()
                assert value['peak_memory_bytes'] >= 32*1024*1024,value
                expected=sum(r['known'] for r in measured)+known
                assert abs(value['cpu_seconds']/expected-1)<=.1,(expected,value)
                owner.RetainedSlice.ctl('stop',unit)
                final=meter.retained[unit].sample(final=True)
                measured.append(dict(known=known,measurement=value,final=final))
            assert measured[1]['measurement']['cpu_seconds'] >= .9*sum(r['known'] for r in measured), measured
            return dict(passed=True,cycles=measured)
        finally:
            for p in processes:
                if p.poll() is None:p.kill()
                p.wait()
            subprocess.run(['systemctl','--user','stop',unit],capture_output=True,timeout=10)
            for retained in meter.retained.values():retained.close()

def service_check(owner):
    with tempfile.TemporaryDirectory() as tmp:
        top=Path(tmp);(top/'scope').mkdir();home=top/'home';home.mkdir()
        ledger=top/'ownership';ledger.write_text('')
        meter=owner.WorkerMeter('/scope','service',top)
        (meter.path/'cpu.stat').write_text('usage_usec 0\n')
        (meter.path/'memory.stat').write_text('anon 0\n')
        meter.root=Path('/sys/fs/cgroup')
        unit='veldo-authority-'+secrets.token_hex(10)+'.service'
        unitfile=owner.unit_directory()/unit
        worker=top/'worker.py'
        worker.write_text('''import importlib.util,os,subprocess,sys,json
from pathlib import Path
s=importlib.util.spec_from_file_location('owner',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
home=Path(sys.argv[2]);unit=Path(sys.argv[3]);tracker=m.Tracker(home,int(sys.argv[4]),int(sys.argv[5])).install()
payload=home/'payload.py'
payload.write_text("import time,json\\nfrom pathlib import Path\\nmemory=bytearray(32*1024*1024)\\nstart=time.process_time()\\nwhile time.process_time()-start<.04: pass\\nPath("+repr(str(home/'known'))+").write_text(str(time.process_time()))\\n")
try:
    unit.write_text('[Unit]\\nDescription=VELDO-0219 short unit\\n[Service]\\nType=oneshot\\nExecStart='+sys.executable+' -I -B '+str(payload)+'\\n')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','start',unit.name],check=True)
    subprocess.run(['systemctl','--user','stop',unit.name],check=True)
finally:
    unit.unlink(missing_ok=True)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    tracker.close()
''')
        fd=meter.open_lifecycle();log=os.open(ledger,os.O_WRONLY|os.O_APPEND)
        p=None
        try:
            p=subprocess.Popen([sys.executable,'-B',str(worker),owner.__file__,str(home),str(unitfile),str(log),str(fd)],
                pass_fds=(log,fd),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            os.close(log);meter.launched()
            end=time.monotonic()+30
            while p.poll() is None:
                assert time.monotonic()<end,'lifecycle deadlock'
                meter.sample(home,ledger)
                time.sleep(.005)
            out,err=p.communicate()
            assert p.returncode==0,err
            value=meter.sample(home,ledger)
            known=float((home/'known').read_text())
            assert abs(value['cpu_seconds']/known-1)<=.1,(known,value)
            assert value['peak_memory_bytes']>=32*1024*1024,value
            return dict(passed=True,known=known,measurement=value)
        finally:
            if p is not None:
                if p.poll() is None:p.kill()
                p.wait()
            subprocess.run(['systemctl','--user','stop',unit],capture_output=True,timeout=10)
            unitfile.unlink(missing_ok=True)
            for target in meter.dropins:
                target.unlink(missing_ok=True);target.parent.rmdir()
            if meter.accounting_slice in meter.retained:
                owner.RetainedSlice.ctl('stop',meter.accounting_slice)
            for r in meter.retained.values():r.close()
            for sock in (meter.peer,meter.lifecycle):
                if sock is not None:sock.close()
            subprocess.run(['systemctl','--user','daemon-reload'],capture_output=True,timeout=10)

if __name__=='__main__':
    owner=load(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'scripts/mutation_ownership.py')
    try:
        result=check(owner)
        if result['passed']:result['service']=service_check(owner)
    except Exception as e:result=dict(passed=False,error=repr(e))
    print(json.dumps(result,indent=2))
    raise SystemExit(not result['passed'])
