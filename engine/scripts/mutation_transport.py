#!/usr/bin/env python3
"""Protected SSH transport and host supervisor for VELDO-0366.

Only authorities own the SSH stream and ephemeral MAC key. Candidate workers inherit
neither. The receiver owns one host lock, one delegated scope and one resource ledger.
"""
import contextlib
import ctypes
import fcntl
import errno
import platform
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
PROCESS_HANG_SECONDS = 3600


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Read exactly the header and bundle; no buffered read may steal the service's next packet.
# This bootstrap has no candidate-controlled paths or archive extraction.
BOOTSTRAP = r'''
import json, os, pathlib, signal, subprocess, sys, tempfile
sys.dont_write_bytecode = True
line = bytearray()
while not line.endswith(b'\n'):
    part = os.read(0, 1)
    if not part: raise RuntimeError('missing bundle header')
    line.extend(part)
header = json.loads(line)
with tempfile.TemporaryDirectory(prefix='vs-', dir='/tmp') as directory:
    top = pathlib.Path(directory)
    bundle = top / 'source.bundle'
    remaining = header['size']
    if type(remaining) is not int or remaining <= 0: raise RuntimeError('invalid bundle size')
    with bundle.open('wb') as target:
        while remaining:
            part = os.read(0, min(1048576, remaining))
            if not part: raise RuntimeError('truncated bundle')
            target.write(part)
            remaining -= len(part)
    root = top / 'tree'
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '-q', '--no-checkout', str(bundle), str(root)], check=True, stdout=2)
    subprocess.run(['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', 'checkout', '-q', '--detach', header['head']], check=True, stdout=2)
    process = subprocess.Popen(['/usr/bin/python3', '-I', '-S', str(root / 'scripts/mutation_transport.py'), '--serve'])
    def stop(signum, frame):
        process.terminate()
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM): signal.signal(sig, stop)
    try:
        code = process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
sys.exit(code)
'''


def send(stream, value):
    stream.write(json.dumps(value, sort_keys=True).encode() + b'\n')
    stream.flush()


def receive(stream):
    line = stream.readline()
    if not line:
        raise RuntimeError('shard disconnected or returned no receipt')
    return json.loads(line)


def terminate(process):
    if process is None:
        return b''
    if process.poll() is None:
        process.terminate()
    # Cancellation can produce a large partial receipt. Drain it while waiting;
    # waiting first would deadlock a child writing more than the pipe can hold.
    if process.stdout is not None and not process.stdout.closed:
        if process.stdin is not None and process.stdin.closed:
            process.stdin = None
        output, _ = process.communicate()
        return output
    process.wait()
    return b''


class SSHNode:
    def __init__(self, root, entry, request, key):
        self.process = None
        self.closed = False
        self.root, self.request, self.key = root, request, key
        self.entry = entry
        # SSH's encrypted channel and mandatory known-host check bind the remote authority.
        target = entry['ssh']
        if not isinstance(target, str) or not target or target.startswith('-'):
            raise RuntimeError('invalid SSH target')
        try:
            with tempfile.TemporaryDirectory(prefix='veldo-bundle-') as temp:
                bundle = Path(temp) / 'source.bundle'
                subprocess.run(['git', '-C', str(root), 'bundle', 'create', str(bundle), 'HEAD'],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self.process = subprocess.Popen(['ssh', '-T', '-o', 'BatchMode=yes',
                    '-o', 'StrictHostKeyChecking=yes', '-o', 'ClearAllForwardings=yes',
                    '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', target,
                    shlex.join(['/usr/bin/python3', '-I', '-S', '-c', BOOTSTRAP])],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                send(self.process.stdin, dict(head=request['head'], size=bundle.stat().st_size))
                with bundle.open('rb') as source:
                    while chunk := source.read(1024 * 1024):
                        self.process.stdin.write(chunk)
                send(self.process.stdin, dict(request=request, host=entry['name'], key=key.hex()))
        except BaseException:
            self.close()
            raise

    def qualify(self):
        return receive(self.process.stdout)

    def dispatch(self, task, qualified):
        send(self.process.stdin, dict(task=task, qualified=qualified))

    def result(self):
        envelope = receive(self.process.stdout)
        # Service exits only after its scope and shard scratch have been removed.
        if self.process.wait() != 0:
            raise RuntimeError('shard transport failed')
        return envelope

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process is not None:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()  # EOF is cancellation, never successful coverage.
            terminate(self.process)
            self.process.stdout.close()


class LocalNode:
    def __init__(self, root, request, key):
        self.root, self.request, self.key = root, request, key
        self.process, self.closed = None, False

    def dispatch(self, task, qualified):
        self.task, self.qualified = task, qualified
        scheduler = load('gate_schedule')
        boundary = load('agent_sandbox')
        self.process = subprocess.Popen([sys.executable, '-I', '-S', __file__, '--local', str(self.root)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                pass_fds=(int(os.environ[scheduler.CHANNEL]), *boundary.launcher_fds()))
        send(self.process.stdin, dict(task=task, qualified=qualified))

    def result(self):
        stage = receive(self.process.stdout)
        if self.process.wait() != 0:
            raise RuntimeError('local shard failed')
        shards = load('mutation_shards')
        return shards.seal(self.key, shards.result_body(self.task, self.qualified, stage, True))

    def close(self):
        if not self.closed:
            self.closed = True
            self.partial = terminate(self.process)
            if self.process:
                if self.process.stdin is not None:
                    self.process.stdin.close()
                self.process.stdout.close()


def completed(nodes):
    with selectors.DefaultSelector() as selector:
        for name, node in nodes.items():
            selector.register(node.process.stdout, selectors.EVENT_READ, name)
        while selector.get_map():
            for key, _ in selector.select():
                selector.unregister(key.fileobj)
                try:
                    result = nodes[key.data].result()
                except Exception as error:
                    result = dict(transport_error=str(error))
                yield key.data, result


def cancellation(signum, frame):
    # Exception, not an immediate exit: run_stage's finally drains all worker ownership.
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, signal.SIG_IGN)
    raise RuntimeError('shard cancelled')


def install_signals():
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, cancellation)



def network_program():
    # x86-64 only, matching the existing gate seccomp ABI. Deny every socket family
    # except AF_UNIX; scratch Unix IPC remains governed by the existing broker.
    deny = 0x50000 | errno.EPERM
    code = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, deny)]
    for syscall in (41, 53):
        code += [(0x15, 0, 3, syscall), (0x20, 0, 0, 16),
                 (0x15, 1, 0, 1), (0x06, 0, 0, deny), (0x20, 0, 0, 0)]
    return code + [(0x06, 0, 0, 0x7fff0000)]


def deny_network(boundary):
    # Called only after namespace setup and descriptor closure, before candidate imports.
    # Installing no_new_privs before the namespace helper would break native setup.
    if platform.machine() != 'x86_64':
        raise RuntimeError('no-network worker requires qualified x86-64 seccomp')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'cannot seal no-network worker')
    boundary.install_filter(libc, network_program())


def execute(gate, root, task, qualified, admission=None, remote=False, scratch_parent='/tmp'):
    shards = load('mutation_shards')
    common = gate.common_directory(root)
    shards.validate_assignment(gate, root, common, task, qualified)
    leg = load('gate_legs').mutation_leg()
    if remote:
        os.environ['VELDO_GATE_COLLECT_ALL'] = '1' if task['request'].get('collect_all') else '0'
        config = json.loads((ROOT / 'scripts/mutation_hosts.json').read_text())
        if any(gate.in_leg(leg, c) or c['suite'] not in config['remote_suites'] for c in task['cases']):
            raise shards.Refused('remote native or confinement requirement undeclared')
    with tempfile.TemporaryDirectory(prefix='vm-', dir=scratch_parent) as scratch:
        previous = tempfile.tempdir
        try:
            tempfile.tempdir = scratch
            result = gate.run_stage(root, common, identities=[c['identity'] for c in task['cases']],
                    admission=admission, admit=not remote, parallel=gate.worker_count(),
                    leg=leg, measure=True, force_fresh=True, no_network=remote)
        finally:
            tempfile.tempdir = previous
    if Path(scratch).exists():
        raise shards.Refused('shard scratch survived')
    if any(task['request'][k] != v for k, v in shards.binding(gate, root, common).items()):
        raise shards.Refused('shard inputs changed')
    return result


def node(state_path, lock_fd):
    """Child owns execution; a keeper outside its scope retains the host lock on death."""
    install_signals()
    host, scheduler, shards = load('gate_host'), load('gate_schedule'), load('mutation_shards')
    hello = receive(sys.stdin.buffer)
    channel = None
    try:
        channel, state = host.start_keeper(host.load(), lock_fd)
        state_path.write_text(json.dumps(state))
        scope = state['cgroup']
        os.environ[host.SCOPE_ENV] = scope
        graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
        capacity = scheduler.capacities(graph, scope, ROOT / 'scripts/suites/manifest.json')
        ledger = scheduler.Ledger(capacity, graph['mutation_floor'])
        aggregate_claim, _ = scheduler.node_claim(graph['nodes']['mutation'], None, capacity)
        if not ledger.acquire('mutation', aggregate_claim, mutation=True):
            raise shards.Refused('host reservation refused')
        ledger.handoff('mutation', graph['nodes']['mutation']['coordinator'])
        os.environ['VELDO_GATE_COLLECT_ALL'] = '1' if hello['request'].get('collect_all') else '0'
        qualification_module = load('qualify_mutation_host')
        checks = qualification_module.qualify(scope)
        checks['namespaces']['no_network'] = False
        if qualification_module.qualified(checks):
            probe = subprocess.run([sys.executable, '-I', '-S', __file__, '--network-probe'],
                                   capture_output=True, text=True)
            checks['namespaces']['no_network'] = probe.returncode == 0
            if probe.returncode:
                checks['namespaces'].update(passed=False, error=probe.stderr)
        qualified = shards.qualification(hello['request'], hello['host'], capacity, checks)
        send(PROTOCOL, qualified)
        shards.admit(hello['request'], hello['host'], qualified)
        message = receive(sys.stdin.buffer)
        if message['qualified'] != qualified:
            raise shards.Refused('qualification changed before dispatch')
        gate = load('check_gate_mutations')
        ownership = load('mutation_ownership')
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
        floor = {r: ledger.floor[r] - graph['nodes']['mutation']['coordinator'][r] for r in ('cpu', 'memory')}
        admission = gate.Admission(Client(), capacity, floor, lambda n: ownership.WorkerMeter(scope, n))
        stage = execute(gate, ROOT, message['task'], qualified, admission, remote=True, scratch_parent=state_path.parent)
        if not shards.runtime_matches(qualified, qualification_module.toolchain()):
            stage.update(status='failed', error='runtime_changed', detail='qualified runtime changed during shard')
        ledger.release('mutation')
        if ledger.held:
            raise shards.Refused('host ledger retained grants')
        stage['host_ledger'] = dict(capacity=capacity, peak=ledger.peak, held=ledger.held)
        send(PROTOCOL, stage)
    finally:
        if channel is not None:
            channel.close()


def serve():
    """Outside-scope supervisor: sign only trusted child output after mandatory teardown."""
    install_signals()
    shards, host = load('mutation_shards'), load('gate_host')
    hello = receive(sys.stdin.buffer)
    key = bytes.fromhex(hello.pop('key'))
    if len(key) != 32:
        raise shards.Refused('invalid session key')
    lock_path = Path(host.load()['lock'])
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    process = None
    stage = qualified = task = None
    with lock_path.open('a') as lock, tempfile.TemporaryDirectory(prefix='va-', dir=ROOT.parent) as temp:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = Path(temp) / 'scope.json'
        try:
            parent = os.getpid()
            def parent_death():
                ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL)
                if os.getppid() != parent:
                    os.kill(os.getpid(), signal.SIGKILL)
            process = subprocess.Popen([sys.executable, '-I', '-S', __file__, '--node', str(state_path), str(lock.fileno())],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, pass_fds=(lock.fileno(),), preexec_fn=parent_death)
            send(process.stdin, hello)
            with selectors.DefaultSelector() as selector:
                selector.register(sys.stdin.buffer, selectors.EVENT_READ, 'upstream')
                selector.register(process.stdout, selectors.EVENT_READ, 'child')
                while stage is None:
                    for event, _ in selector.select():
                        message = receive(event.fileobj)  # EOF always refuses, including mid-run.
                        if event.data == 'upstream':
                            if qualified is None or task is not None:
                                raise shards.Refused('unexpected assignment')
                            task = message['task']
                            send(process.stdin, message)
                        elif qualified is None:
                            qualified = message
                            send(PROTOCOL, shards.seal(key, qualified))
                        else:
                            stage = message
                            break
            if process.wait() != 0:
                raise shards.Refused('shard child failed')
        finally:
            terminate(process)
            if state_path.exists():
                host.stop_scope(json.loads(state_path.read_text()))
            if process:
                if process.stdin is not None:
                    process.stdin.close()
                process.stdout.close()
    send(PROTOCOL, shards.seal(key, shards.result_body(task, qualified, stage, not Path(temp).exists())))


def main():
    # Worker logs can never become protocol packets.
    with contextlib.redirect_stdout(sys.stderr):
        if sys.argv[1:] == ['--serve']:
            serve()
        elif sys.argv[1:2] == ['--node']:
            node(Path(sys.argv[2]), int(sys.argv[3]))
        elif sys.argv[1:2] == ['--local']:
            install_signals()
            message = receive(sys.stdin.buffer)
            send(PROTOCOL, execute(load('check_gate_mutations'), Path(sys.argv[2]),
                                   message['task'], message['qualified']))
        elif sys.argv[1:] == ['--network-probe']:
            import socket
            deny_network(load('agent_sandbox'))
            for family in (socket.AF_INET, socket.AF_INET6):
                try:
                    sock = socket.socket(family, socket.SOCK_STREAM)
                except PermissionError:
                    pass
                else:
                    sock.close()
                    raise RuntimeError('network socket creation was allowed')
            left, right = socket.socketpair()
            left.close()
            right.close()
        else:
            raise RuntimeError('internal transport mode required')
    return 0


if __name__ == '__main__':
    PROTOCOL = sys.stdout.buffer
    sys.exit(main())
