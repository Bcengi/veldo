#!/usr/bin/env python3
"""Explicit native mutation-host qualification (VELDO-0365), never a full gate.

Run from a reviewed authority: --receipt FILE [--cases JSON --batch-receipt FILE].
JSON is a nonempty list of case names. All probes must pass before the existing
single-host coordinator runs. A receipt describes this invocation only; it is
not a cached authorization, a reuse qualification or a distributed shard token.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ('delegation', 'landlock', 'namespaces', 'ptrace', 'pidfds', 'toolchain')


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualified(checks):
    return set(checks) == set(REQUIRED) and all(checks[n].get('passed') is True for n in REQUIRED)


def command(argv):
    run = subprocess.run(argv, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if run.returncode:
        raise RuntimeError('%s exited %d: %s' % (argv[0], run.returncode, (run.stderr + run.stdout)[-6000:]))
    return run.stdout.strip()


def delegation(scope):
    ownership = load('mutation_ownership')
    base = Path('/sys/fs/cgroup') / scope.lstrip('/')
    enabled = (base / 'cgroup.subtree_control').read_text().split()
    if not {'cpu', 'memory', 'pids'} <= set(enabled):
        raise RuntimeError('scope must delegate cpu, memory and pids controllers')
    meter = ownership.WorkerMeter(scope, 'qualification')
    join = meter.open_join()
    process = None
    try:
        code = ('import os,sys\nos.write(int(sys.argv[1]),str(os.getpid()).encode())\n'
                'os.close(int(sys.argv[1]))\n'
                'data=bytearray(8*1024*1024)\nprint("ready",flush=True)\nsys.stdin.read()\n')
        process = subprocess.Popen([sys.executable, '-I', '-S', '-c', code, str(join)],
                                   pass_fds=(join,), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if process.stdout.readline() != b'ready\n':
            raise RuntimeError('worker did not join its cgroup')
        members = (meter.path / 'cgroup.procs').read_text().split()
        measured = meter.sample()
        if str(process.pid) not in members or measured['cpu_seconds'] <= 0 or measured['peak_anon_bytes'] < 8*2**20:
            raise RuntimeError('worker membership or real cgroup accounting missing')
    finally:
        os.close(join)
        if process is not None:
            process.communicate()
        meter.close()
    if meter.path.exists():
        raise RuntimeError('worker cgroup survived cleanup')
    return dict(controllers=enabled, measurement=measured, cleaned=True)


def pidfds():
    # A real live child, then its exit becoming observable through the retained fd.
    child = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import sys; sys.stdin.read()'],
                             stdin=subprocess.PIPE)
    fd = None
    try:
        fd = os.pidfd_open(child.pid)
        before = os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        child.stdin.close()
        after = os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOWAIT)
        child.wait()
        if before is not None or after.si_pid != child.pid or child.returncode:
            raise RuntimeError('pidfd did not track the child lifecycle')
        return dict(live_unreadable=True, exited_readable=True)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        if fd is not None:
            os.close(fd)


def landlock():
    with tempfile.TemporaryDirectory(prefix='veldo-qualify-') as temp:
        top = Path(temp)
        allowed, denied = top / 'allowed', top / 'denied'
        allowed.mkdir()
        denied.write_text('private')
        code = '''import importlib.util, pathlib, subprocess, sys
s=importlib.util.spec_from_file_location('boundary',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
a,d=map(pathlib.Path,sys.argv[2:])
s=importlib.util.spec_from_file_location('mutation_boundary',pathlib.Path(sys.argv[1]).with_name('mutation_sandbox.py')); b=importlib.util.module_from_spec(s); s.loader.exec_module(b)
root=pathlib.Path(sys.argv[1]).parent.parent
m.landlock(b.worker_grants(m,root,root,a,None),profile='worker')
subprocess.run([sys.executable,'-c','print("confined interpreter started")'],check=True)
(a/'ok').write_text('allowed'); assert (a/'ok').read_text()=='allowed'
try: d.read_text()
except PermissionError: pass
else: raise RuntimeError('Landlock allowed an ungranted read')
try: d.write_text('changed')
except PermissionError: pass
else: raise RuntimeError('Landlock allowed an ungranted write')
print('allow-read-write deny-read-write')
'''
        return command([sys.executable, '-I', '-S', '-c', code,
                        str(ROOT / 'scripts/agent_sandbox.py'), str(allowed), str(denied)])


def ptrace():
    with tempfile.TemporaryDirectory(prefix='veldo-trace-') as temp:
        trace = Path(temp) / 'trace'
        marker = Path(temp) / 'input'
        marker.write_text('traced')
        tracing = load('case_trace')
        command(tracing.command(trace, [sys.executable, '-I', '-S', '-c',
                'import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_text()=="traced"', str(marker)]))
        if marker not in {path for path, _ in tracing.opened_paths(trace, successful=True)}:
            raise RuntimeError('ptrace omitted the child read')
        return dict(observed_read=True, trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest())


def toolchain():
    reuse = load('mutation_reuse')
    paths = reuse.required_runtime(os.environ)
    tools, missing = {}, []
    # Match the UI suites' account nvm lookup plus the fresh worker's fixed PATH.
    # The remote supervisor's private tools on its PATH are not worker grants.
    boundary = load('agent_sandbox')
    nodes = sorted((boundary.account_home() / '.nvm/versions/node').glob('v*/bin'),
                   key=lambda p: [int(n) for n in re.findall(r'\d+', p.parent.name)])
    worker_path = os.pathsep.join([*(str(p) for p in nodes[-1:]), '/usr/bin', '/bin'])
    for name in ('git', 'sh', 'strace', 'busctl', 'systemctl', 'node', 'npm', 'ssh-keygen'):
        found = shutil.which(name, path=worker_path)
        if found is None:
            missing.append(name)
            continue
        path = Path(found).resolve()
        paths.append(path)
        tools[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    paths.append(load('agent_sandbox').NAMESPACE_HELPER)
    identity = reuse.runtime_identity(sorted(set(paths)), os.environ)
    identity['trees'] = {p: reuse.R.digest(tree) for p, tree in identity['trees'].items()}
    return dict(tools=tools, runtime=identity, missing=missing, worker_path=worker_path)


def qualify(scope):
    checks = {}
    probes = dict(delegation=lambda: delegation(scope), landlock=landlock,
                  namespaces=lambda: command([sys.executable, '-I', '-S',
                    str(ROOT / 'scripts/agent_sandbox.py'), 'namespace-selftest']),
                  ptrace=ptrace, pidfds=pidfds, toolchain=toolchain)
    for name in REQUIRED:
        try:
            evidence = probes[name]()
            checks[name] = dict(passed=not (name == 'toolchain' and evidence['missing']), evidence=evidence)
            if not checks[name]['passed']:
                checks[name]['error'] = 'required tools absent from worker runtime: ' + ', '.join(evidence['missing'])
        except Exception as error:
            checks[name] = dict(passed=False, error=str(error))
        print('qualification %s: %s' % (name, 'passed' if checks[name]['passed'] else checks[name]['error']), flush=True)
    return checks


def batch(names, scope, capacity, ledger, graph, destination):
    gate = load('check_gate_mutations')
    ownership = load('mutation_ownership')
    overhead = graph['nodes']['mutation']['coordinator']
    if not ledger.acquire('coordinator', overhead, mutation=True):
        raise RuntimeError('coordinator reservation refused')
    floor = {r: ledger.floor[r] - overhead[r] for r in ('cpu', 'memory')}
    if any(v <= 0 for v in floor.values()):
        raise RuntimeError('coordinator consumes the mutation reservation')
    class Client:
        last_reply = {}
        def acquire(self, name, cpu, memory, manager='none'):
            granted = ledger.acquire(name, dict(cpu=cpu, memory=memory, manager=manager, ports=[]), mutation=True)
            self.last_reply = dict(totals=ledger.totals(), resource=ledger.blocking_resource)
            return granted
        def release(self, name):
            ledger.release(name)
        def close(self):
            pass
    admission = gate.Admission(Client(), capacity, floor, lambda n: ownership.WorkerMeter(scope, n))
    result = gate.run_stage(ROOT, gate.common_directory(ROOT), names=names, admission=admission,
                           parallel=gate.worker_count(), leg=load('gate_legs').mutation_leg(),
                           measure=True, force_fresh=True)
    ledger.release('coordinator')
    result['qualification_ledger'] = dict(capacity=capacity, floor=ledger.floor, peak=ledger.peak, held=ledger.held)
    destination.write_text(json.dumps(result, sort_keys=True))
    return result['status'] == 'passed' and not ledger.held


def native(args):
    host, schedule = load('gate_host'), load('gate_schedule')
    receipt = dict(schema='veldo.mutation-host-qualification/v1', status='failed', checks={},
                   host=platform.node(), kernel=list(platform.uname()),
                   authority={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((ROOT / 'scripts').glob('*.py'))})
    try:
        state = {}
        try:
            _, scope = host.make_scope(host.load()['scope'], state=state)
        finally:
            args.state.write_text(json.dumps(state))
        os.environ[host.SCOPE_ENV] = scope
        graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
        capacity = schedule.capacities(graph, scope, ROOT / 'scripts/suites/manifest.json')
        ledger = schedule.Ledger(capacity, graph['mutation_floor'])
        claim, _ = schedule.node_claim(graph['nodes']['mutation'], None, capacity)
        ledger.demand(claim)
        receipt.update(capacity=capacity, configured_floor=graph['mutation_floor'], effective_floor=ledger.floor,
                       aggregate_claim=claim, scope=scope, checks=qualify(scope))
        if qualified(receipt['checks']):
            receipt['status'] = 'passed'
            if args.cases:
                names = json.loads(args.cases.read_text())
                if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
                    raise ValueError('cases must be distinct nonempty names')
                # Unix socket fixtures need a short physical scratch path. The remote
                # supervisor's run directory can already exceed sun_path's 107 bytes.
                # This private allocation is removed on every normal or exceptional exit.
                with tempfile.TemporaryDirectory(prefix='vq-', dir='/tmp') as scratch:
                    previous = tempfile.tempdir
                    try:
                        tempfile.tempdir = scratch
                        receipt['batch_passed'] = batch(names, scope, capacity, ledger, graph, args.batch_receipt)
                    finally:
                        tempfile.tempdir = previous
                receipt['batch_scratch_removed'] = not Path(scratch).exists()
        cg = Path('/sys/fs/cgroup') / scope.lstrip('/')
        receipt['scope_counters'] = {n: (cg / n).read_text() for n in ('memory.peak', 'memory.events', 'cpu.stat')}
    except Exception as error:
        receipt.update(status='failed', error=str(error))
    finally:
        args.receipt.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    return 0 if receipt['status'] == 'passed' and receipt.get('batch_passed', True) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--cases', type=Path)
    parser.add_argument('--batch-receipt', type=Path)
    parser.add_argument('--state', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if bool(args.cases) != bool(args.batch_receipt):
        parser.error('--cases and --batch-receipt must be supplied together')
    if args.state:
        return native(args)
    host = load('gate_host')
    lock = Path(host.load()['lock'])
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as handle, tempfile.TemporaryDirectory(prefix='veldo-qualification-') as temp:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = Path(temp) / 'scope.json'
        try:
            return subprocess.call([sys.executable, '-I', '-S', __file__, *sys.argv[1:], '--state', str(state)])
        finally:
            if state.exists():
                host.stop_scope(json.loads(state.read_text()))


if __name__ == '__main__':
    sys.exit(main())
