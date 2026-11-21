"""Event-ordered outside-writer ABA on bind, socketpair and recvmsg memory.

An unmeasured ancestor rewrites tracee memory with real process_vm_writev
calls, scheduled only by acknowledgements from an instrumented copy of the
collector (scheduling hooks; no decision logic changes). Each scenario makes
the tracee memory disagree with the kernel effect:

* bind: the sockaddr says 127.0.0.1 at both stops; the kernel bound 127.0.0.2;
* socketpair: the result array is rewritten to name an older, genuine pair;
* recvmsg: the received SCM_RIGHTS control is erased after the kernel filled it.

The collector must report each from kernel state (getsockname on a duplicate,
the descriptor-table diff) with its named failure. No sleep decides anything.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading

from socket_destruction import SOURCE, load

ROW = 'census/memory-aba-uses-kernel-state'
HOOK = '''    def witness(self, pid, nr, phase, args):
        plan = json.loads(os.environ['VELDO_0111_WITNESS_PLAN'])
        if nr not in plan.get(phase, []):
            return
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.connect('\\0' + plan['socket'])
            channel.sendall((json.dumps(dict(phase=phase, nr=nr, pid=pid, args=list(args))) + '\\n').encode())
            assert channel.recv(1) == b'A'

'''

BIND = r'''
import ctypes, json, os, socket, struct
libc = ctypes.CDLL(None, use_errno=True)
s = socket.socket()
address = ctypes.create_string_buffer(struct.pack('<HH4s8x', socket.AF_INET, 0, socket.inet_aton('127.0.0.1')))
assert libc.bind(s.fileno(), address, 16) == 0
s.listen(1)
print(json.dumps(dict(inode=os.readlink('/proc/self/fd/' + str(s.fileno())),
                      kernel=s.getsockname(), memory=socket.inet_ntoa(address.raw[4:8]))))
s.close()
'''

PAIR = r'''
import ctypes, json, os, socket
libc = ctypes.CDLL(None, use_errno=True)
older = socket.socketpair()
before = {n for n in os.listdir('/proc/self/fd') if os.path.exists('/proc/self/fd/' + n)}
sv = (ctypes.c_int * 2)()
assert libc.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0, sv) == 0
installed = sorted(int(n) for n in set(os.listdir('/proc/self/fd')) - before
                   if os.path.exists('/proc/self/fd/' + n))  # drop listdir's own fd
link = lambda fd: os.readlink('/proc/self/fd/' + str(fd))
print(json.dumps(dict(memory=list(sv), older=[s.fileno() for s in older], installed=installed,
                      installed_inodes=[link(fd) for fd in installed],
                      older_inodes=[link(s.fileno()) for s in older])))
for fd in installed: os.close(fd)
for s in older: s.close()
'''

RECEIVE = r'''
import json, os, socket, sys
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
    channel.connect('\0' + sys.argv[1])
    before = {n for n in os.listdir('/proc/self/fd') if os.path.exists('/proc/self/fd/' + n)}
    data, controls, flags, _ = channel.recvmsg(1, socket.CMSG_SPACE(4))
    installed = sorted(int(n) for n in set(os.listdir('/proc/self/fd')) - before
                       if os.path.exists('/proc/self/fd/' + n))  # drop listdir's own fd
    print(json.dumps(dict(data=data.decode(), controls=len(controls), installed=installed,
                          inodes=[os.readlink('/proc/self/fd/' + str(fd)) for fd in installed])))
    for fd in installed: os.close(fd)
'''


def instrument(original):
    source = original.replace('    def syscall(self, pid):\n', HOOK + '    def syscall(self, pid):\n')
    source = source.replace('            self.pending[pid] = entry\n',
        "            self.pending[pid] = entry\n            self.witness(pid, nr, 'entry', args)\n")
    source = source.replace('        nr, a = entry["nr"], entry["args"]\n',
        '        nr, a = entry["nr"], entry["args"]\n' +
        "        self.witness(pid, nr, 'exit', a)\n")
    assert source.count('self.witness(') == 2
    return source


def write(pid, address, data):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.process_vm_writev.restype = ctypes.c_ssize_t
    class Iovec(ctypes.Structure):
        _fields_ = [('base', ctypes.c_void_p), ('length', ctypes.c_size_t)]
    value = ctypes.create_string_buffer(data, len(data))
    local, remote = Iovec(ctypes.addressof(value), len(data)), Iovec(address, len(data))
    written = libc.process_vm_writev(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    assert written == len(data), ('process_vm_writev', written, ctypes.get_errno())
    return written


def memory(pid, address, length):
    with open(f'/proc/{pid}/mem', 'rb') as handle:
        handle.seek(address)
        return handle.read(length)


def scenario(census_module_path, name, plan, events, probe, act, args=(), courier=None):
    """Run one instrumented census; act(event) performs the outside writes."""
    records, errors = [], []
    channel = 'v111-maba-' + str(os.getpid()) + '-' + name
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as scheduler:
        scheduler.bind('\0' + channel); scheduler.listen(4); scheduler.settimeout(120)
        def serve():
            try:
                for _ in range(events):  # Exact hook count per probe.
                    connection, _ = scheduler.accept()
                    with connection:
                        connection.settimeout(120)
                        data = b''
                        while not data.endswith(b'\n'):
                            chunk = connection.recv(4096)
                            assert chunk
                            data += chunk
                        event = json.loads(data)
                        records.append(dict(event, writes=act(event)))
                        connection.sendall(b'A')
            except BaseException as exc:
                errors.append(repr(exc))
        worker = threading.Thread(target=serve)
        worker.start()
        helper = None
        if courier:
            helper = threading.Thread(target=courier)
            helper.start()
        old = os.environ.get('VELDO_0111_WITNESS_PLAN')
        os.environ['VELDO_0111_WITNESS_PLAN'] = json.dumps(dict(plan, socket=channel))
        try:
            census = load(census_module_path)
            r = census.census([sys.executable, '-B', '-c', probe, *args],
                              identity='VELDO-0111/memory-aba/' + name)
        finally:
            if old is None:
                os.environ.pop('VELDO_0111_WITNESS_PLAN', None)
            else:
                os.environ['VELDO_0111_WITNESS_PLAN'] = old
        worker.join(120)
        if helper:
            helper.join(120)
        assert not worker.is_alive() and not errors, errors
        assert r.get('root_status') == 0 and r['lost_events'] == 0, (r.get('root_status'), r['stderr'][-800:], r['failures'])
        ack, = [json.loads(line) for line in r['stdout'].splitlines()]
        return r, ack, records


def named(r, reason, capability='shared_socket_memory'):
    return any(f['capability'] == capability and f['reason'] == reason for f in r['failures'])


def stands_down(r):
    return r['capture_status'] == 'INCOMPLETE' and all(
        row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
        for rows in r['consumer_rows'].values() for row in rows)


def run(source=SOURCE):
    original = source.read_text()
    instrumented = instrument(original)
    cases = []
    with tempfile.TemporaryDirectory(prefix='v111-maba-') as temporary:
        path = Path(temporary) / 'lifecycle_census.py'
        path.write_text(instrumented)

        # bind: change the requested IPv4 address only while the syscall runs.
        def bind_act(event):
            target = event['args'][1] + 4
            return write(event['pid'], target, socket.inet_aton(
                '127.0.0.2' if event['phase'] == 'entry' else '127.0.0.1'))
        r, ack, records = scenario(path, 'bind', dict(entry=[49], exit=[49]), 2, BIND, bind_act)
        obj, = [o for o in r['sockets'] if o['inode'] == ack['inode']]
        kernel = bytes.fromhex(obj['kernel_sockaddr_hex'])
        effect = (ack['kernel'][0] == '127.0.0.2' and ack['memory'] == '127.0.0.1'
                  and socket.inet_ntoa(kernel[4:8]) == '127.0.0.2'
                  and bytes.fromhex(obj['address'])[4:8] == socket.inet_aton('127.0.0.1'))
        assert effect, (ack, obj)  # Otherwise the ABA did not happen: invalid drive.
        cases.append(dict(scenario='bind', acknowledgement=ack, writes=records,
            kernel_sockaddr_hex=obj['kernel_sockaddr_hex'], sampled_sockaddr_hex=obj['address'],
            passed=named(r, 'kernel-bound address differs from the sampled sockaddr') and stands_down(r),
            failures=r['failures']))

        # socketpair: at exit, rewrite the result array to name the older pair.
        state = {}
        def pair_act(event):
            state['count'] = state.get('count', 0) + 1
            if state['count'] != 2:
                return 0
            pid, pointer = event['pid'], event['args'][3]
            fds = list(struct.unpack('<2i', memory(pid, pointer, 8)))
            older = sorted(int(n) for n in os.listdir(f'/proc/{pid}/fd')
                           if os.readlink(f'/proc/{pid}/fd/{n}').startswith('socket:[')
                           and int(n) not in fds)
            assert len(older) == 2, older
            return write(pid, pointer, struct.pack('<2i', *older))
        r, ack, records = scenario(path, 'socketpair', dict(exit=[53]), 2, PAIR, pair_act)
        assert ack['memory'] == ack['older'] and ack['installed'] != ack['older'], ack
        registered = {o['inode']: o for o in r['sockets']}
        cases.append(dict(scenario='socketpair', acknowledgement=ack, writes=records,
            passed=named(r, 'socketpair result memory differs from installed descriptors')
                and all(i in registered and (registered[i]['closed'] or {}).get('released')
                        for i in ack['installed_inodes'] + ack['older_inodes'])
                and registered[ack['installed_inodes'][0]].get('pair_peer') == ack['installed_inodes'][1]
                and stands_down(r),
            failures=r['failures']))

        # recvmsg: an outside sender passes a socket; erase the control at exit.
        name = 'v111-maba-courier-' + str(os.getpid())
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind('\0' + name); listener.listen(1); listener.settimeout(120)
        outside = socket.socket()
        outside.bind(('127.0.0.1', 0)); outside.listen(1)
        sent = []
        def courier():
            connection, _ = listener.accept()
            with connection:
                sent.append(connection.sendmsg([b'R'], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                    struct.pack('<i', outside.fileno()))]))
        def receive_act(event):
            pid, header = event['pid'], event['args'][1]
            control, length = struct.unpack('<QQ', memory(pid, header + 32, 16))
            # Make it read as an empty, valid credentials-free control.
            return write(pid, control, bytes(length)) + write(pid, header + 40, bytes(8))
        try:
            r, ack, records = scenario(path, 'recvmsg', dict(exit=[47]), 1, RECEIVE, receive_act,
                                       (name,), courier)
            outside_inode = os.readlink('/proc/self/fd/' + str(outside.fileno()))
        finally:
            listener.close()
            outside.close()
        assert sent == [1] and ack['controls'] == 0 and ack['inodes'] == [outside_inode], ack
        cases.append(dict(scenario='recvmsg', acknowledgement=ack, writes=records,
            passed=named(r, 'received out-of-scope socket', 'descriptor_transfer') and any(
                e['kind'] == 'descriptor_transfer' and e['inode'] == outside_inode for e in r['events'])
                and stands_down(r),
            failures=r['failures']))
    return dict(row=ROW, passed=all(c['passed'] for c in cases), cases=cases,
                source_digest=hashlib.sha256(original.encode()).hexdigest(),
                instrumented_digest=hashlib.sha256(instrumented.encode()).hexdigest(),
                scheduling_only_instrumentation=True, external_writer_is_ancestor=True)


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
