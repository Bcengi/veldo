"""An event-ordered counterexample to destruction at descendant drain.

The receiver is created outside the measured scope. The measured root queues
SCM_RIGHTS, closes every local descriptor and exits. Only after census returns
does the receiver exercise and receive the socket, then release it. No sleep
or elapsed-time assertion establishes any of those transitions.
"""

import array
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'scripts/fixtures/lifecycle_census.py'
ROW = 'census/external-reference-needs-destruction-observer'
PROBE = r'''
import array, json, os, socket, sys
family = int(sys.argv[1])
kind = socket.SOCK_RAW if family == socket.AF_NETLINK else socket.SOCK_STREAM
protocol = 2 if family == socket.AF_NETLINK else 0
s = socket.socket(family, kind, protocol)
address = {1: '\0v111-held-' + str(os.getpid()), 2: ('127.0.0.1', 0),
           10: ('::1', 0), 16: (0, 0)}[family]
s.bind(address)
if family != socket.AF_NETLINK:
    s.listen(1)
address = s.getsockname()
if isinstance(address, bytes):
    address = os.fsdecode(address)
inode = os.readlink('/proc/self/fd/' + str(s.fileno()))
with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as transport:
    transport.connect('\0' + sys.argv[2])
    assert transport.sendmsg([b'R'], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                      array.array('i', [s.fileno()]))]) == 1
s.close()
print(json.dumps(dict(family=family, address=address, inode=inode,
                     local_close_acknowledged=True)))
'''


def load(path):
    spec = importlib.util.spec_from_file_location('census111_external', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(source=SOURCE):
    census = load(source)
    results = []
    for family in (socket.AF_UNIX, socket.AF_INET, socket.AF_INET6, socket.AF_NETLINK):
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
            name = 'v111-external-' + str(os.getpid()) + '-' + str(int(family))
            receiver.bind('\0' + name)
            receiver.settimeout(census.HANG_SECONDS)  # Hang detector only.
            r = census.census([sys.executable, '-B', '-c', PROBE, str(int(family)), name],
                              identity='VELDO-0111/external-reference/' + str(int(family)))
            returned_ns = time.monotonic_ns()
            # Unavailable tracing is an invalid drive, never a detected falsifier.
            assert r['capture_status'] == 'COMPLETE' and r.get('root_status') == 0, r['failures']
            ack, = [json.loads(line) for line in r['stdout'].splitlines()]
            obj, = [o for o in r['sockets'] if o['inode'] == ack['inode']]
            events = [e for e in r['events'] if e.get('socket') == obj['identity']]
            assert sum(e['kind'] == 'service' for e in events) == 1
            assert obj['descriptor_closes'] and ack['local_close_acknowledged']
            assert all(p['terminal'] for p in r['processes'])
            assert os.getpid() not in {p['pid'] for p in r['processes']}
            drained = next(b for b in r['barriers'] if b['name'] == 'descendants_drained')
            address = ack['address'] if family == socket.AF_UNIX else tuple(ack['address'])
            kind = socket.SOCK_RAW if family == socket.AF_NETLINK else socket.SOCK_STREAM
            protocol = 2 if family == socket.AF_NETLINK else 0
            with socket.socket(family, kind, protocol) as client:
                client.settimeout(census.HANG_SECONDS)
                # The only reference to the service socket is still in the queue.
                if family == socket.AF_NETLINK:
                    assert client.sendto(b'queued-reference', address) == 16
                else:
                    client.connect(address)
                    client.sendall(b'queued-reference')
                queued_live_ns = time.monotonic_ns()
                data, ancillary, flags, _ = receiver.recvmsg(1, socket.CMSG_SPACE(4))
                assert data == b'R' and not flags & socket.MSG_CTRUNC
                level, control, raw = ancillary[0]
                assert (level, control) == (socket.SOL_SOCKET, socket.SCM_RIGHTS)
                descriptors = array.array('i')
                descriptors.frombytes(raw)
                assert len(descriptors) == 1
                with socket.socket(family, kind, protocol, fileno=descriptors[0]) as held:
                    held.settimeout(census.HANG_SECONDS)
                    assert os.readlink('/proc/self/fd/' + str(held.fileno())) == obj['inode']
                    actual_address = held.getsockname()
                    if isinstance(actual_address, bytes):
                        actual_address = os.fsdecode(actual_address)
                    assert actual_address == address
                    if family == socket.AF_NETLINK:
                        assert held.recv(128) == b'queued-reference'
                    else:
                        assert held.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) == 1
                        connection, _ = held.accept()
                        with connection:
                            connection.settimeout(census.HANG_SECONDS)
                            received = b''
                            while len(received) < 16:
                                chunk = connection.recv(16 - len(received))
                                assert chunk
                                received += chunk
                            assert received == b'queued-reference'
                    holder_live_ns = time.monotonic_ns()
                released_ns = time.monotonic_ns()
            assert drained['time_ns'] <= returned_ns <= queued_live_ns <= holder_live_ns <= released_ns
            # These timestamps order explicit acknowledgements; release is NOT
            # asserted to be the exact kernel destruction time either.
            reasons = [v for v in r['qualification']['reasons']
                       if v['capability'] == 'socket_destruction']
            passed = bool(reasons) and r['status'] == 'INCOMPLETE' and all(
                row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
                for rows in r['consumer_rows'].values() for row in rows)
            results.append(dict(family=int(family), passed=passed, acknowledgement=ack,
                receipt={k: r[k] for k in ('schema', 'input_identity', 'input_digest',
                    'implementation_digest', 'fixture_version', 'host', 'status',
                    'capture_status', 'state', 'barriers', 'processes', 'failures',
                    'lost_events', 'consumer_rows')},
                socket=obj, service_and_close_events=events, destruction_reasons=reasons,
                witness=dict(receiver_outside_scope=True, queued_socket_live_after_drain=True,
                    held_socket_live_after_drain=True, census_returned_ns=returned_ns,
                    queued_live_ns=queued_live_ns, holder_live_ns=holder_live_ns,
                    external_release_ack_ns=released_ns, exact_destruction_observed=False)))
    return dict(row=ROW, passed=all(r['passed'] for r in results), cases=results,
                source_digest=hashlib.sha256(source.read_bytes()).hexdigest())


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
