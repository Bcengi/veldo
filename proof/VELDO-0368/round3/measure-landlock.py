"""Focused pc1 experiment. This script cannot issue a dependency certificate."""
import ctypes
import faulthandler
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path.cwd()
OUT = ROOT / '.local/0368/round3'

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

B = load('agent_sandbox')
M = load('mutation_sandbox')

class Rules(ctypes.Structure):
    _fields_ = [('access', ctypes.c_uint64)]

class Beneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('access', ctypes.c_uint64), ('parent', ctypes.c_int32)]

def read_layer(paths):
    libc = ctypes.CDLL(None, use_errno=True)
    def call(n, *args):
        result = libc.syscall(n, *args)
        if result < 0:
            raise OSError(ctypes.get_errno(), 'Landlock measurement')
        return result
    assert libc.prctl(38, 1, 0, 0, 0) == 0
    rules = Rules(B.READ)
    fd = call(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
    try:
        for p in paths:
            access = B.READ if p.is_dir() else B.READ & B.FILE
            parent = os.open(p, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(access, parent)
                call(445, fd, 1, ctypes.byref(rule), 0)
            finally:
                os.close(parent)
        call(446, fd, 0)
    finally:
        os.close(fd)

def attempt(fn):
    try:
        value = fn()
        return dict(ok=True, value=value)
    except OSError as e:
        return dict(ok=False, errno=e.errno)

def child(mode, scratch):
    applied = []
    original = B.landlock
    def capture(grants, **kwargs):
        grants = list(grants)
        applied.extend([str(p), a] for p, a in grants)
        return original(grants, **kwargs)
    B.landlock = capture
    M.confine_in_tree(ROOT, ROOT, scratch, boundary=B)
    unrelated = ROOT / 'specs/VELDO-0217-every-confined-case-has-a-reviewed-input-declaration.md'
    allowed = ROOT / 'scripts/agent_sandbox.json'
    inherited = os.open(unrelated, os.O_RDONLY)
    if mode == 'narrow':
        read_layer([allowed, scratch, Path('/usr'), Path('/etc'), Path('/proc'), Path('/dev/null'), Path('/dev/urandom')])
    result = dict(mode=mode, applied_grants=applied, namespace=B.nested_namespace() is not None,
        tracer=next(x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('TracerPid:')),
        allowed=attempt(lambda: len(allowed.read_bytes())),
        unrelated_read=attempt(lambda: len(unrelated.read_bytes())),
        unrelated_stat=attempt(lambda: unrelated.stat().st_size),
        unrelated_access=attempt(lambda: os.access(unrelated, os.R_OK)),
        repo_listing=attempt(lambda: len(os.listdir(ROOT))),
        repo_write=attempt(lambda: (ROOT / '.local/forbidden-round3').write_text('forbidden')),
        system_read=attempt(lambda: len(Path('/etc/os-release').read_bytes())))
    result['preopened_read'] = attempt(lambda: len(os.read(inherited, 32)))
    os.close(inherited)
    native = subprocess.run(['/usr/bin/cat', str(unrelated)], capture_output=True, text=True)
    result['native_read'] = dict(exit=native.returncode, stdout_bytes=len(native.stdout), stderr=native.stderr)
    result['threads_before'] = len(os.listdir('/proc/self/task'))
    faulthandler.dump_traceback_later(300, exit=True)
    result['threads_after'] = len(os.listdir('/proc/self/task'))
    result['read_after_watchdog'] = attempt(lambda: len(unrelated.read_bytes()))
    faulthandler.cancel_dump_traceback_later()
    print('SCOPE ' + json.dumps(result), flush=True)
    assert result['allowed']['ok'] and result['namespace'] and result['repo_write'].get('errno') == 13
    assert result['unrelated_read']['ok'] == (mode == 'broad')
    assert result['unrelated_stat']['ok'] and result['threads_after'] > result['threads_before']

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        child(sys.argv[1], Path(sys.argv[2]))
        return
    scratch = OUT / 'scratch'
    scratch.mkdir(exist_ok=True)
    grants = M.worker_grants(B, ROOT, ROOT, scratch)
    result = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        host=platform.node(), kernel=platform.release(), python=sys.version,
        landlock_abi=ctypes.CDLL(None).syscall(444, 0, 0, 1),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        worker_grants=[[str(p), a] for p, a in grants],
        implicit_grants=[[str(B.PROC), B.READ], [str(B.PTMX), (1 << 1) | (1 << 2) | B.DEVICE_IOCTL]],
        scope=[], samples=[])
    for mode in ('broad', 'narrow'):
        log = OUT / (mode + '.log')
        # Run the actual namespace launcher, IPC broker and worker Landlock entry.
        code = "import importlib.util,os,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('b','scripts/agent_sandbox.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b);sys.exit(b.worker_tree([sys.executable,'-B',sys.argv[1],sys.argv[2],sys.argv[3]],dict(os.environ),Path.cwd(),Path(sys.argv[3])))"
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(Path(__file__).resolve()), mode, str(scratch)], text=True, capture_output=True, timeout=90)
        log.write_text(proc.stdout + proc.stderr)
        print(mode, proc.returncode, proc.stdout, proc.stderr, flush=True)
        assert proc.returncode == 0
        result['scope'].append(json.loads(next(x[6:] for x in proc.stdout.splitlines() if x.startswith('SCOPE '))))
    files = [ROOT / p for p in subprocess.check_output(['git', 'ls-files', '*.py'], text=True).splitlines() if (ROOT / p).is_file()][:1024]
    assert len(files) == 1024
    runtime = [p for p, a in grants if p != ROOT and a & B.READ]
    # All inputs are warm; a fresh child installs every measured domain once.
    for rep in range(25):
        shapes = [0, 32, 128, 512, 1024]
        if rep % 2:
            shapes.reverse()
        for count in shapes:
            paths = [ROOT] if count == 0 else files[:count]
            for kind in ('full_existing_function', 'read_layer_only'):
                rd, wr = os.pipe()
                pid = os.fork()
                if pid == 0:
                    os.close(rd)
                    if kind == 'read_layer_only':
                        B.landlock(grants, profile='worker')
                    start, cpu = time.perf_counter_ns(), time.process_time_ns()
                    if kind == 'full_existing_function':
                        B.landlock([(p, a) for p, a in grants if p != ROOT] + [(p, B.READ) for p in paths], profile='worker')
                    else:
                        read_layer(runtime + paths)
                    row = dict(rep=rep, repository_rules=len(paths), shape=count, kind=kind,
                        wall_ns=time.perf_counter_ns()-start, cpu_ns=time.process_time_ns()-cpu)
                    os.write(wr, json.dumps(row).encode())
                    os._exit(0)
                os.close(wr)
                data = os.read(rd, 65536)
                os.close(rd)
                _, status = os.waitpid(pid, 0)
                assert status == 0 and data
                result['samples'].append(json.loads(data))
    result['summary'] = []
    for kind in ('full_existing_function', 'read_layer_only'):
        for count in (0, 32, 128, 512, 1024):
            rows = [r for r in result['samples'] if r['kind'] == kind and r['shape'] == count]
            result['summary'].append(dict(kind=kind, shape=count, n=len(rows),
                median_wall_us=statistics.median(r['wall_ns'] for r in rows)/1000,
                median_cpu_us=statistics.median(r['cpu_ns'] for r in rows)/1000,
                p95_wall_us=sorted(r['wall_ns'] for r in rows)[23]/1000))
    (OUT / 'landlock.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2), flush=True)

if __name__ == '__main__':
    main()
