"""Event-ordered external memory ABA across ptrace entry/exit stops.

Instrumentation changes scheduling only. An unmeasured ancestor uses the real
process_vm_writev syscall to change a private anonymous control buffer after
entry sampling and restore it before exit sampling. The kernel's received fd
is the independent oracle; no sleep or duration establishes correctness.

The send decoder is blind here by construction: both samples show credentials.
The row requires the escape to be caught anyway, by the epoll file-release
observer after descendant drain, as a named escaped_reference violation.
"""
import array
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

from socket_destruction import ROOT, SOURCE, load

HERE = Path(__file__).resolve().parent
ROW = 'census/escape-detected-despite-control-aba'
PROBE = r'''
import ctypes, json, os, socket, struct, sys
s = socket.socket()
s.bind(('127.0.0.1', 0)); s.listen(1)
transport = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
transport.connect('\0' + sys.argv[1])
payload = ctypes.create_string_buffer(b'R')
vector = ctypes.create_string_buffer(struct.pack('<QQ', ctypes.addressof(payload), 1))
# Entry and exit expose credentials; the external writer supplies SCM_RIGHTS
# only while the actual syscall runs, replacing valid credentials with three
# copies of this tracee's service fd. Both ancillary messages are valid.
assert s.fileno() == 3
control = ctypes.create_string_buffer(struct.pack('<Qiiiii4x', 28, socket.SOL_SOCKET, socket.SCM_CREDENTIALS, os.getpid(), os.getuid(), os.getgid()))
message = ctypes.create_string_buffer(struct.pack('<QI4xQQQQI4x', 0, 0, ctypes.addressof(vector), 1,
    ctypes.addressof(control), 32, 0))
libc = ctypes.CDLL(None, use_errno=True)
assert libc.syscall(46, transport.fileno(), ctypes.byref(message), 0) == 1
print(json.dumps(dict(inode=os.readlink('/proc/self/fd/' + str(s.fileno())), address=s.getsockname())))
s.close(); transport.close()
'''
HOOK = '''    def witness_phase(self, pid, entry, phase):
        message = self.memory(pid, entry['args'][1], 56)
        pointer, length = struct.unpack_from('<QQ', message, 32)
        before = self.memory(pid, pointer, length).hex()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.connect('\\0' + os.environ['VELDO_0111_WITNESS_SOCKET'])
            channel.sendall((json.dumps(dict(phase=phase, pid=pid, pointer=pointer, before=before)) + '\\n').encode())
            assert channel.recv(1) == b'A'
        sample = before if phase == 'entry' else self.memory(pid, pointer, length).hex()
        self.event('witness_sample', phase=phase, sample=sample,
                   entry_descriptors=entry.get('sent_controls'))

'''


def instrument(original):
    source = original.replace('    def syscall(self, pid):\n', HOOK + '    def syscall(self, pid):\n')
    source = source.replace('            self.pending[pid] = entry\n',
        "            self.pending[pid] = entry\n            if nr == 46:\n                self.witness_phase(pid, entry, 'entry')\n")
    source = source.replace('        nr, a = entry["nr"], entry["args"]\n',
        '        nr, a = entry["nr"], entry["args"]\n' +
        "        if nr == 46 and result >= 0:\n            self.witness_phase(pid, entry, 'exit')\n")
    return source


def run(source=SOURCE):
    original = source.read_text()
    instrumented = instrument(original)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.process_vm_writev.restype = ctypes.c_ssize_t
    class Iovec(ctypes.Structure):
        _fields_ = [('base', ctypes.c_void_p), ('length', ctypes.c_size_t)]
    records, errors = [], []
    name = 'v111-aba-' + str(os.getpid())
    with tempfile.TemporaryDirectory(prefix='v111-aba-') as temporary, \
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as scheduler, \
            socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
        scheduler.bind('\0' + name); scheduler.listen(2); scheduler.settimeout(120)
        receiver.bind('\0' + name + '-receiver'); receiver.settimeout(120)
        control_module = load(source)
        control_receipt = control_module.census(
            [sys.executable, '-B', '-c', PROBE, name + '-receiver'],
            identity='VELDO-0111/shared-control-benign')
        assert control_receipt.get('root_status') == 0 and control_receipt['capture_status'] == 'COMPLETE'
        benign_data, benign_controls, benign_flags, _ = receiver.recvmsg(1, socket.CMSG_SPACE(32))
        assert benign_data == b'R' and not benign_flags & socket.MSG_CTRUNC
        assert not any((level, kind) == (socket.SOL_SOCKET, socket.SCM_RIGHTS)
                       for level, kind, _ in benign_controls)
        path = Path(temporary) / 'lifecycle_census.py'
        path.write_text(instrumented)
        def mutate_memory():
            try:
                for phase, kind in (('entry', socket.SCM_RIGHTS), ('exit', socket.SCM_CREDENTIALS)):
                    connection, _ = scheduler.accept()
                    with connection:
                        connection.settimeout(120)
                        data = b''
                        while not data.endswith(b'\n'):
                            chunk = connection.recv(4096)
                            assert chunk
                            data += chunk
                        event = json.loads(data)
                        assert event['phase'] == phase
                        if phase == 'entry':
                            original_fields = bytes.fromhex(event['before'])[12:28]
                            value = ctypes.create_string_buffer(struct.pack('<4i', kind, 3, 3, 3))
                        else:
                            value = ctypes.create_string_buffer(original_fields)
                        local = Iovec(ctypes.addressof(value), 16)
                        remote = Iovec(event['pointer'] + 12, 16)
                        written = libc.process_vm_writev(event['pid'], ctypes.byref(local), 1,
                                                        ctypes.byref(remote), 1, 0)
                        assert written == 16, ('process_vm_writev', written, ctypes.get_errno())
                        records.append(dict(phase=phase, bytes_written=written, kind=kind))
                        connection.sendall(b'A')
            except BaseException as exc:
                errors.append(str(exc))
        worker = threading.Thread(target=mutate_memory)
        worker.start()
        old = os.environ.get('VELDO_0111_WITNESS_SOCKET')
        os.environ['VELDO_0111_WITNESS_SOCKET'] = name
        try:
            census = load(path)
            r = census.census([sys.executable, '-B', '-c', PROBE, name + '-receiver'],
                              identity='VELDO-0111/shared-control-aba')
        finally:
            if old is None:
                os.environ.pop('VELDO_0111_WITNESS_SOCKET', None)
            else:
                os.environ['VELDO_0111_WITNESS_SOCKET'] = old
        worker.join(120)
        assert not worker.is_alive() and not errors, errors
        assert r.get('root_status') == 0 and r['lost_events'] == 0, r['failures']
        ack, = [json.loads(line) for line in r['stdout'].splitlines()]
        data, ancillary, flags, _ = receiver.recvmsg(1, socket.CMSG_SPACE(12))
        assert data == b'R' and not flags & socket.MSG_CTRUNC
        level, kind, raw = ancillary[0]
        assert (level, kind) == (socket.SOL_SOCKET, socket.SCM_RIGHTS)
        descriptors = array.array('i'); descriptors.frombytes(raw)
        assert len(descriptors) == 3
        for fd in descriptors[1:]:
            assert os.readlink('/proc/self/fd/' + str(fd)) == ack['inode']
            os.close(fd)
        with socket.socket(fileno=descriptors[0]) as held:
            assert os.readlink('/proc/self/fd/' + str(held.fileno())) == ack['inode']
            assert held.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) == 1
            assert held.getsockname() == tuple(ack['address'])
        samples = [e for e in r['events'] if e['kind'] == 'witness_sample']
        assert len(samples) == 2 and samples[0]['sample'] == samples[1]['sample']
        assert all(e['entry_descriptors'] == [[]] for e in samples)
        assert all(p['terminal'] for p in r['processes'])
        service, = [o for o in r['sockets'] if o['inode'] == ack['inode']]
        escapes = [f for f in r['failures'] if f['capability'] == 'escaped_reference']
        # The decoder saw credentials only; any send attribution would mean the
        # ABA did not happen and the drive is invalid, not a detection.
        assert not any(f['reason'].startswith('SCM_RIGHTS send ') for f in escapes)
        assert all(not e['descriptors'] for e in r['events'] if e['kind'] == 'descriptor_send')
        detected = [f for f in escapes if f['category'] == 'lifecycle_violation' and
                    f['reason'] == service['identity'] + ' file is still referenced after descendant drain']
        passed = bool(detected) and r['capture_status'] == 'INCOMPLETE' and r['status'] == 'INCOMPLETE' \
            and service['closed'] is None and all(
            row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
            for rows in r['consumer_rows'].values() for row in rows)
        return dict(row=ROW, passed=passed, source_digest=hashlib.sha256(original.encode()).hexdigest(),
            instrumented_digest=hashlib.sha256(instrumented.encode()).hexdigest(),
            scheduling_only_instrumentation=True, external_writer_is_ancestor=True,
            unmodified_credentials_control=dict(root_status=control_receipt['root_status'],
                capture_status=control_receipt['capture_status'], no_received_rights=True),
            actual_fd_received_after_drain=True, send_decoder_attributed=False,
            escaped_reference_detected=bool(detected),
            identical_entry_exit_samples=True, samples=samples, mutations=records,
            acknowledgement=ack, receipt={k:r[k] for k in ('status','capture_status','state',
                'barriers','processes','failures','consumer_rows')})


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
