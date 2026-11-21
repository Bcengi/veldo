"""VELDO-0111 live event checks. No unrelated suites or host lock operations.

The four named rows check the collector against independently acknowledged
effects. They are not a declaration of full kernel qualification. That separate
result remains INCOMPLETE when any reachable path is unqualified.
Direct execution emits JSON; the standard suite dispatcher consumes ROOT/expect.
"""

import array
import ctypes
import importlib.util
import inspect
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading


PROCESS_PROBE = r'''
import ctypes, json, os, signal, subprocess, sys, threading, time
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
def ack(kind):
    os.write(1, (json.dumps(dict(kind=kind, pid=os.getpid(), tid=threading.get_native_id(),
                               parent=os.getppid())) + '\n').encode())
ack('root')
root_pid = os.getpid()
child = os.fork()
if child == 0:
    ack('immediate')
    os._exit(0)
os.waitpid(child, 0)
child = libc.syscall(56, signal.SIGCHLD, 0, 0, 0, 0)
if child == 0:
    ack('clone')
    os._exit(0)
assert child > 0
os.waitpid(child, 0)
args = (ctypes.c_ulonglong * 11)()
args[4] = signal.SIGCHLD
child = libc.syscall(435, ctypes.byref(args), ctypes.sizeof(args))
if child == 0:
    ack('clone3')
    os._exit(0)
if child > 0:
    os.waitpid(child, 0)
else:
    os.write(1, (json.dumps(dict(kind='unsupported', operation='clone3', errno=ctypes.get_errno()))+'\n').encode())
t = threading.Thread(target=lambda: ack('thread'))
t.start(); t.join()
code = "import os,json; os.write(1,(json.dumps(dict(kind='vfork_exec',pid=os.getpid(),tid=os.getpid(),parent=os.getppid()))+'\\n').encode())"
child = os.posix_spawn(sys.executable, [sys.executable, '-B', '-c', code], os.environ)
os.waitpid(child, 0)
child = os.fork()
if child == 0:
    ack('daemon_parent')
    os.setsid()
    child = os.fork()
    if child == 0:
        ack('reparented')
        # This probe waits for the collector to reap the root, so host load
        # cannot turn an arbitrary sleep into an exit-before-return case.
        # The observer itself never derives births or exits from this query.
        while libc.kill(root_pid, 0) == 0:
            time.sleep(.001)
        os._exit(0)
    os._exit(0)
os.waitpid(child, 0)
'''

THREAD_EXEC_PROBE = r'''
import json, os, sys, threading
def child():
    os.write(1,(json.dumps(dict(kind='thread_exec',tid=threading.get_native_id()))+'\n').encode())
    os.execv(sys.executable,[sys.executable,'-B','-c','pass'])
t=threading.Thread(target=child)
t.start(); t.join()
'''

SOCKET_PROBE = r'''
import array, ctypes, errno, json, os, socket, sys
def ack(**values):
    os.write(1, (json.dumps(values)+'\n').encode())
def service(s, address, name):
    s.bind(address)
    if s.type & 15 in (1,5):
        s.listen(1)
        op='listen'
    else:
        op='bind'
    ack(kind='service',family=s.family,type=s.type & 15,op=op,name=name,
        inode=os.readlink('/proc/self/fd/'+str(s.fileno())))
    s.close()
for family, address in ((socket.AF_INET,('127.0.0.1',0)),(socket.AF_INET6,('::1',0))):
    for kind in (socket.SOCK_STREAM,socket.SOCK_DGRAM):
        service(socket.socket(family,kind),address,f'{family}:{kind}')
for kind in (socket.SOCK_STREAM,socket.SOCK_DGRAM,socket.SOCK_SEQPACKET):
    for abstract in (False,True):
        address=('\0v111-'+str(os.getpid())+'-'+str(kind)) if abstract else os.path.join(sys.argv[1],str(kind))
        service(socket.socket(socket.AF_UNIX,kind),address,f'unix:{kind}:{abstract}')
s=socket.socket()
alias=socket.socket(fileno=os.dup(s.fileno()))
s.close()
service(alias,('127.0.0.1',0),'dup')
s=socket.socket()
child=os.fork()
if child==0:
    service(s,('127.0.0.1',0),'inherited')
    os._exit(0)
os.waitpid(child,0)
s.close()
a,b=socket.socketpair()
s=socket.socket()
a.sendmsg([b'x'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[s.fileno()]))])
_, ancillary, _, _=b.recvmsg(1,socket.CMSG_SPACE(4))
fd=array.array('i'); fd.frombytes(ancillary[0][2][:4])
received=socket.socket(fileno=fd[0])
s.close()
service(received,('127.0.0.1',0),'transferred')
a.close(); b.close()
try:
    service(socket.socket(socket.AF_NETLINK,socket.SOCK_RAW,2),(0,0),'netlink')
except OSError as exc:
    ack(kind='unsupported',family=socket.AF_NETLINK,type=socket.SOCK_RAW,errno=exc.errno)
'''

RING_HELPER = r'''
import ctypes,json,os,sys
libc=ctypes.CDLL(None,use_errno=True)
params=ctypes.create_string_buffer(120)
fd=libc.syscall(425,2,ctypes.byref(params))
libc.prctl(0x59616d61,ctypes.c_ulong(-1),0,0,0)  # PR_SET_PTRACER_ANY for pidfd_getfd
print(json.dumps(dict(pid=os.getpid(),fd=fd)),flush=True)
sys.stdin.read()
'''
RING_TAKER = r'''
import ctypes,json,os,sys
libc=ctypes.CDLL(None,use_errno=True)
pid,fd=int(sys.argv[1]),int(sys.argv[2])
pidfd=os.pidfd_open(pid)
taken=libc.syscall(438,pidfd,fd,0)
value=dict(fd=taken,link=os.readlink('/proc/self/fd/%d'%taken) if taken>=0 else None,reopened=None)
try:
    value['reopened']=os.open('/proc/%d/fd/%d'%(pid,fd),os.O_RDONLY)
except OSError as exc:
    value['reopen_errno']=exc.errno
print(json.dumps(value))
'''
SCTP_BINDX_PROBE = r'''
import socket,struct
s=socket.socket(socket.AF_INET,socket.SOCK_SEQPACKET,132)
s.bind(('127.0.0.1',0))
s.setsockopt(132,100,struct.pack('<H',2)+struct.pack('!H',s.getsockname()[1])+socket.inet_aton('127.0.0.2')+bytes(8))
s.close()
'''
INVENTORY_PROBE = r'''
import ctypes,json,os,socket,struct
libc=ctypes.CDLL(None,use_errno=True)
def ack(value):
    os.write(1,(json.dumps(value)+'\n').encode())
for family in range(46):
    bounds={1:16,2:1024,10:1024,16:64}
    protocols=range(bounds[family]) if family in bounds else (0,)
    for kind in (1,2,3,4,5,6,10):
        for protocol in protocols:
            fd=libc.socket(family,kind|socket.SOCK_NONBLOCK|socket.SOCK_CLOEXEC,protocol)
            ack(dict(kind='combination',family=family,type=kind,protocol=protocol,
                     available=fd>=0,errno=ctypes.get_errno() if fd<0 else 0))
            if fd<0:
                continue
            if family not in (1,2,10,16):
                os.close(fd)
                continue
            with socket.socket(family,kind,protocol,fileno=fd) as s:
                if family==1:
                    address='\0v111-generated-'+str(os.getpid())
                elif family==2:
                    address=('127.0.0.1',0)
                elif family==10:
                    address=('::1',0)
                elif family==16:
                    address=(0,0)
                conn=None
                if protocol==115 and family in (2,10):
                    # L2TP/IP binds a connection id with its own sockaddr layout.
                    conn=0x3330000+os.getpid()%65536
                    address=(struct.pack('<HH4sI4x',2,0,socket.inet_pton(2,'127.0.0.1'),conn) if family==2
                             else struct.pack('<HHI16sII',10,0,0,socket.inet_pton(10,'::1'),0,conn))
                for operation in ('bind','listen') if kind in (1,5,6) else ('bind',):
                    try:
                        if operation=='listen':
                            s.listen(1)
                        elif conn is not None:
                            raw=ctypes.create_string_buffer(address,len(address))
                            if libc.bind(fd,raw,len(address))!=0:
                                raise OSError(ctypes.get_errno(),'bind')
                        else:
                            s.bind(address)
                        ack(dict(kind='operation',family=family,type=kind,protocol=protocol,
                                 operation=operation,result=0,address=repr(s.getsockname()),conn_id=conn,
                                 inode=os.readlink('/proc/self/fd/'+str(fd))))
                    except OSError as exc:
                        ack(dict(kind='operation',family=family,type=kind,protocol=protocol,
                                 operation=operation,result=-1,errno=exc.errno))
params=ctypes.create_string_buffer(256)
fd=libc.syscall(425,1,ctypes.byref(params))
ack(dict(kind='io_uring_setup',available=fd>=0,errno=ctypes.get_errno() if fd<0 else 0))
if fd>=0:
    os.close(fd)
'''


EXTENDED_SOCKET_PROBE = r'''
import ctypes, json, mmap, os, socket, struct
libc=ctypes.CDLL(None,use_errno=True)
libc.syscall.restype=ctypes.c_long
def ack(**v):
    os.write(1,(json.dumps(v)+'\n').encode())
for nr in (43,288):
    listener=socket.socket()
    listener.bind(('127.0.0.1',0)); listener.listen(1)
    client=socket.socket(); client.connect(listener.getsockname())
    fd=libc.syscall(nr,listener.fileno(),0,0,0)
    assert fd>=0
    accepted=socket.socket(fileno=fd)
    client.send(b'x'); assert accepted.recv(1)==b'x'
    ack(kind='accept',syscall=nr,inode=os.readlink('/proc/self/fd/'+str(fd)),address=accepted.getsockname())
    accepted.close(); client.close(); listener.close()
for family,address in ((socket.AF_INET,('127.0.0.1',0)),(socket.AF_INET6,('::1',0))):
    target=socket.socket(family,socket.SOCK_DGRAM); target.bind(address)
    sender=socket.socket(family,socket.SOCK_DGRAM)
    sender.sendto(b'x',target.getsockname())
    ack(kind='implicit',family=family,inode=os.readlink('/proc/self/fd/'+str(sender.fileno())),address=sender.getsockname())
    sender.sendto(b'y',target.getsockname())
    sender.close(); target.close()
# An int 0x80 socketcall with low-address argument memory exercises the actual
# compat ABI without a compiler, a 32-bit loader, or an installed executable.
code=mmap.mmap(-1,4096,prot=7)
code.write(bytes.fromhex('53 b866000000 89fb 89f1 cd80 4898 5b c3'))
call=ctypes.CFUNCTYPE(ctypes.c_long,ctypes.c_int,ctypes.c_void_p)(ctypes.addressof(ctypes.c_char.from_buffer(code)))
low=mmap.mmap(-1,4096,flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS|0x40,prot=3)
base=ctypes.addressof(ctypes.c_char.from_buffer(low))
assert base < 2**32
args=(ctypes.c_uint32*6).from_buffer(low)
args[:3]=[socket.AF_INET,socket.SOCK_STREAM,0]
fd=call(1,base)
if fd<0:
    ack(kind='socketcall_unavailable',errno=-fd)
else:
    low[64:80]=struct.pack('=H',socket.AF_INET)+b'\0\0'+socket.inet_aton('127.0.0.1')+b'\0'*8
    args[:3]=[fd,base+64,16]; assert call(2,base)==0
    args[:2]=[fd,1]; assert call(4,base)==0
    ack(kind='socketcall',inode=os.readlink('/proc/self/fd/'+str(fd)))
    os.close(fd)
'''

ESCAPE_PROBE = r'''
import ctypes, json, os, signal, sys
libc=ctypes.CDLL(None,use_errno=True)
libc.syscall.restype=ctypes.c_long
nr=int(sys.argv[1])
# Invalid CLONE_THREAD combination prevents an escaped child even in the mutant.
flags=0x800000|0x10000|signal.SIGCHLD
if nr==56:
    result=libc.syscall(nr,flags,0,0,0,0)
else:
    args=(ctypes.c_ulonglong*11)(); args[0]=flags
    result=libc.syscall(nr,ctypes.byref(args),ctypes.sizeof(args))
assert result<0
os.write(1,(json.dumps(dict(returned=True,errno=ctypes.get_errno()))+'\n').encode())
'''


def run_round3_checks(census, emit, groups=('families', 'unix', 'states')):
    """Focused ticket regressions, also called by the complete ticket suite."""
    evidence = {}
    if 'families' in groups:
        expected_families = {1: 'Unix', 2: 'IPv4', 10: 'IPv6', 16: 'netlink'}
        probes = []
        for family in (*range(46), 65535):
            collector = census.Collector(dict(identity='family-boundary', argv=['probe']))
            collector.r['state'] = 'collecting'
            collector.birth(os.getpid())
            # Unit exercise of the registration guard for unavailable and future
            # families. Live discovery below separately witnesses real sockets.
            collector.socket_at = lambda pid, fd: 'socket:[111]'
            obj = collector.register_socket(os.getpid(), 9, family, 2, 0)
            failures = [f for f in collector.r['failures'] if f['capability'] == 'family_not_qualified']
            probes.append(dict(family=family, failures=failures,
                               capture_status=collector.r['capture_status']))
            if family in expected_families:
                probes[-1]['passed'] = not failures
            else:
                probes[-1]['passed'] = (bool(obj) and len(failures) == 1
                    and str(family) in failures[0]['reason']
                    and collector.r['capture_status'] == 'INCOMPLETE')
        inventory = census.host_inventory()
        excluded = inventory.get('not_qualified_families', [])
        live = census.census([sys.executable, '-B', '-c', r'''
import ctypes,json,os,socket
libc=ctypes.CDLL(None,use_errno=True)
for family in range(46):
    if family in (1,2,10,16):
        continue
    for kind in (1,2,3,4,5,6,10):
        fd=libc.socket(family,kind|socket.SOCK_NONBLOCK|socket.SOCK_CLOEXEC,0)
        if fd>=0:
            print(json.dumps(dict(family=family,inode=os.readlink('/proc/self/fd/'+str(fd)))))
            os.close(fd)
'''], identity='VELDO-0111/other-families')
        acks = [json.loads(line) for line in live['stdout'].splitlines()]
        live_ok = live.get('root_status') == 0 and (not acks or (
            live['capture_status'] == 'INCOMPLETE'
            and all(any(f['capability'] == 'family_not_qualified'
                        and str(a['family']) in f['reason'] for f in live['failures']) for a in acks)))
        # The qualifier must preserve the obligations inside the chosen universe.
        minimal = dict(inventory, exhaustive=True, operation_probes=[], io_uring={'available':False})
        fake = census.receipt(dict(identity='synthetic-qualifier', argv=['probe']))
        fake['capture_status'] = 'COMPLETE'
        fake['sockets'] = [dict(identity='synthetic', closed=dict(exact=False))]
        census.qualify(fake, minimal)
        # A socket without an observed final release keeps its named gap.
        preserved = {'socket_destruction'} <= {
            r['capability'] for r in fake['qualification']['reasons']}
        evidence['family_boundary'] = dict(probes=probes, inventory=inventory, live=live,
                                          retained_obligations=fake)
        emit('census/family-qualification-boundary',
             getattr(census, 'QUALIFICATION_FAMILIES', None) == expected_families
             and all(p['passed'] for p in probes) and live_ok and preserved
             and inventory.get('qualification_families') == list(expected_families)
             and {r['family'] for r in excluded} == set(range(46)) - set(expected_families)
             and all(r['capability'] == 'family_not_qualified' and r['reason'] for r in excluded)
             and all(p['family'] in expected_families for p in inventory['operation_probes']))
    if 'unix' in groups:
        results = []
        for passcred in (False, True):
            r = census.census([sys.executable, '-B', '-c', r'''
import json,os,socket,sys
receiver=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
receiver.bind('\0v111-round3-'+str(os.getpid()))
sender=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
if sys.argv[1]=='True':
    sender.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
before=sender.getsockname()
for i in range(2):
    sender.sendto(b'x',receiver.getsockname())
    assert receiver.recv(1)==b'x'
name=sender.getsockname()
print(json.dumps(dict(before=bool(before),bound=bool(name),
                     name_hex=os.fsencode(name).hex(),
                     inode=os.readlink('/proc/self/fd/'+str(sender.fileno())))))
''', str(passcred)], identity='VELDO-0111/unix-binding-' + str(passcred))
            acks = [json.loads(line) for line in r['stdout'].splitlines()]
            sender = [o for o in r['sockets'] if acks and o['inode'] == acks[0]['inode']]
            events = [e for e in r['events'] if e['kind'] == 'service'
                      and sender and e['socket'] == sender[0]['identity']]
            result = (r.get('root_status') == 0 and len(acks) == 1 and len(sender) == 1
                      and not acks[0]['before'] and acks[0]['bound'] == passcred
                      and r['capture_status'] == 'COMPLETE'
                      and not any(f['capability'] == 'implicit_address' for f in r['failures']))
            if passcred:
                result = result and len(events) == 1 and events[0]['operation'] == 'implicit_receive_binding' and (
                    isinstance(events[0]['address'], dict)
                    and events[0]['address'].get('unix_name_hex') == acks[0]['name_hex'])
            else:
                result = result and not events
            results.append(bool(result))
            evidence['unix_' + str(passcred)] = r
        # A successful syscall does not establish a local binding for a family
        # whose implicit address we cannot decode. It must fail without an event.
        collector = census.Collector(dict(identity='implicit-other', argv=['probe']))
        collector.r['state'] = 'collecting'
        collector.birth(os.getpid())
        collector.socket_at = lambda pid, fd: 'socket:[222]'
        collector.register_socket(os.getpid(), 9, 16, 2, 0)
        collector.syscall_exit(os.getpid(), dict(nr=44, args=[9,0,0,0,0,0], inode='socket:[222]'), 1)
        results.append(not any(e['kind'] == 'service' for e in collector.r['events'])
                       and any(f['capability'] == 'implicit_address' for f in collector.r['failures']))
        evidence['implicit_other'] = collector.r
        emit('census/unix-binding-is-real', all(results))
    if 'states' in groups:
        import ast
        tree = ast.parse(Path(census.__file__).read_text())
        states = set()
        dynamic = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                            and target.slice.value == 'state'):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            states.add(node.value.value)
                        else:
                            dynamic.append(node.lineno)
            if isinstance(node, ast.keyword) and node.arg == 'state' and isinstance(node.value, ast.Constant):
                states.add(node.value.value)
        faults = {case[0] for case in census.FAULTS.values()}
        evidence['fault_states'] = dict(assigned=sorted(states), covered=sorted(faults), dynamic=dynamic)
        emit('census/fault-state-coverage', bool(states) and not dynamic and states == faults)
    return evidence


def finish_rows(census, r):
    return [census.consumer_rows(r, c) for c in census.CONSUMERS]


def run_checks(root, emit, module_path=None):
    spec = importlib.util.spec_from_file_location('lifecycle111', module_path or root / 'scripts/fixtures/lifecycle_census.py')
    census = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(census)
    evidence = {}

    def run(label, code, *args, **kwargs):
        r = census.census([sys.executable, '-B', '-c', code, *map(str, args)],
                          identity='VELDO-0111/' + label, **kwargs)
        evidence[label] = r
        return r, [json.loads(line) for line in r['stdout'].splitlines()]

    def complete_capture(r):
        return r['capture_status'] == 'COMPLETE' and r.get('root_status') == 0 and r['lost_events'] == 0

    r, acknowledgements = run('processes', PROCESS_PROBE)
    births = [a for a in acknowledgements if a['kind'] not in ('unsupported', 'root')]
    actual = [p for p in r['processes'] if not p['root']]
    birth_events = [e for e in r['events'] if e['kind'] == 'birth']
    barriers = {b['name']: b for b in r['barriers']}
    ok = (complete_capture(r) and len(births) >= 6 and len(actual) == len(births)
          and {p['pid'] for p in actual} == {a['tid'] for a in births}
          and {e['identity'] for e in birth_events} == {p['identity'] for p in actual}
          and len({p['identity'] for p in r['processes']}) == len(r['processes'])
          and all(p['terminal'] and p['terminal'] > p['birth'] for p in r['processes'])
          and all(p['parent'] in {q['identity'] for q in r['processes']} for p in actual)
          and any(p['terminal'] < barriers['call_returned']['sequence'] for p in actual)
          and any(p['terminal'] > barriers['call_returned']['sequence'] for p in actual)
          and barriers['armed_before_exec']['sequence'] < min(e['sequence'] for e in r['events'] if e['kind'] == 'exec')
          and any(p['operation'] == 'vfork' for p in actual))
    thread, acks = run('thread_exec', THREAD_EXEC_PROBE)
    former = acks[0]['tid'] if acks else None
    ok = ok and complete_capture(thread) and any(
        e['kind'] == 'exec' and e['former_tid'] == former and e['pid'] != former for e in thread['events'])
    emit('census/process-lifetimes', bool(ok))

    with tempfile.TemporaryDirectory(prefix='v111-outside-') as outside:
        r, acknowledgements = run('listeners', SOCKET_PROBE, outside)
    expected = [a for a in acknowledgements if a['kind'] == 'service']
    actual = [e for e in r['events'] if e['kind'] == 'service']
    objects = {obj['identity']: obj for obj in r['sockets']}
    expected_keys = sorted((a['inode'], a['family'], a['type'], a['op']) for a in expected)
    actual_keys = sorted((objects[e['socket']]['inode'], e['family'], e['type'], e['operation']) for e in actual)
    emit('census/listener-lifetimes', complete_capture(r) and len(expected) >= 13
         and any(a['family'] == socket.AF_INET6 for a in expected)
         and expected_keys == actual_keys
         and all(isinstance(e['address'],dict) and e['address']['port'] > 0 for e in actual
                 if e['family'] in (socket.AF_INET,socket.AF_INET6))
         and any(e['kind'] == 'descriptor_transfer' for e in r['events'])
         and all(objects[e['socket']]['created'] < e['sequence'] for e in actual)
         and all(any(close['sequence'] > e['sequence'] and close.get('inode') == objects[e['socket']]['inode']
                     for close in r['events'] if close['kind'] == 'close') for e in actual))

    empty, _ = run('empty', 'pass')
    same, acks = run('same_names', r'''
import ctypes,json,os
libc=ctypes.CDLL(None)
observer=__import__('sys').argv[1]
for name in (observer,'pgrep'):
    child=os.fork()
    if child==0:
        libc.prctl(15,name.encode(),0,0,0)
        os.write(1,(json.dumps(dict(pid=os.getpid(),name=name))+'\n').encode())
        os._exit(0)
    os.waitpid(child,0)
''', empty['observer']['comm'])
    scope = {p['pid'] for p in same['processes'] if not p['root']}
    emit('census/observer-is-outside', complete_capture(empty) and complete_capture(same)
         and len(empty['processes']) == 1 and len(acks) == 2 and scope == {a['pid'] for a in acks}
         and all(r['observer']['collector'] not in {p['pid'] for p in r['processes']}
                 and r['observer']['supervisor'] not in {p['pid'] for p in r['processes']}
                 for r in (same, empty)))

    expected_names = {
        'VELDO-0113': ['unavailable/no-client-starts-the-authority', 'unavailable/no-client-hosts-a-listener',
                       'unavailable/no-auto-start-needs-census'],
        'VELDO-0114': ['relay/one-endpoint-one-judgement', 'relay/no-listener-during-call',
                       'relay/no-second-process', 'relay/listener-proof-needs-census'],
        'VELDO-0122': ['filesystem/transient-and-escaped-writes-are-seen', 'unavailable/no-transient-write',
                       'unavailable/no-out-of-directory-write', 'unavailable/no-write-needs-complete-observation']}
    results = []
    for fault, (state, category, capability) in census.FAULTS.items():
        code = 'import os; p=os.fork(); os._exit(0)' if fault in ('loss', 'collector_death', 'drain') else 'pass'
        r, _ = run('fault_' + fault, code, fault=fault)
        results.append(r['status'] == 'INCOMPLETE' and r['capture_status'] == 'INCOMPLETE'
                       and any(f['capability'] == capability and f['category'] == category
                               and f['state'] == state and bool(f['reason']) for f in r['failures']))
        if category == 'event_loss':
            results.append(r['lost_events'] > 0)
        for consumer, names in expected_names.items():
            rows = census.consumer_rows(r, consumer)
            results.append([row['name'] for row in rows] == names and all(
                row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete' for row in rows))
        if fault == 'collector_death':
            results.append(r['supervision']['collector_status'] == 9 and
                           len(r['supervision']['adopted_terminal_waits']) >= 2)
    # The root never returns on its own, so expiry does not depend on how fast this host is.
    hanging, _ = run('deadline', 'import signal\nwhile True: signal.pause()', deadline=.05)
    results.append(hanging['status'] == 'INCOMPLETE' and hanging['capture_status'] == 'INCOMPLETE')
    for value in (None, {}, {'status': 'COMPLETE'}, dict(empty, status='COMPLETE'),
                  dict(empty, status='COMPLETE', failures=[], qualification=None),
                  dict(empty, status='COMPLETE', failures=[], qualification={
                      'status':'COMPLETE', 'gaps':[], 'inventory':{'exhaustive':True}}, barriers=None)):
        results.extend(all(row['status'] == 'STANDS DOWN' for row in census.consumer_rows(value,c))
                       for c in expected_names)
    emit('census/incomplete-is-not-empty', all(results))

    inventory, combinations = run('inventory', INVENTORY_PROBE, deadline=600)
    cells = [c for c in combinations if c['kind'] == 'combination']
    operations = [c for c in combinations if c['kind'] == 'operation']
    expected = sorted((c['inode'], c['family'], c['type'], c['operation']) for c in operations
        if c['result'] == 0 and (c['operation'] == 'listen' or c['type'] in (2,3,10)))
    objects = {o['identity']: o for o in inventory['sockets']}
    observed = sorted((objects[e['socket']]['inode'], e['family'], e['type'], e['operation'])
        for e in inventory['events'] if e['kind'] == 'service')
    evidence['capabilities'] = dict(combinations=cells, operations=operations,
        expected_services=len(expected), observed_services=len(observed),
        status=inventory['qualification']['status'])
    emit('census/qualification-does-not-overclaim', len(cells) == 15190
         and len({(c['family'],c['type'],c['protocol']) for c in cells}) == len(cells)
         and all(c['available'] or c['errno'] > 0 for c in cells)
         and inventory.get('root_status') == 0 and expected == observed
         and inventory['status'] == 'INCOMPLETE'
         and all(row['status'] == 'STANDS DOWN' for rows in inventory['consumer_rows'].values() for row in rows))
    capabilities = inventory['qualification']['inventory']
    # The inventory is exhaustive only when the registry reconciles; that host
    # claim is proved separately by census/protocol-inventory-covers-kernel.
    wanted = set() if capabilities['exhaustive'] else {'protocol_inventory_bounds'}
    # socket_destruction is named only for a socket whose final release was not
    # observed; this capture must instead see every one of its sockets released.
    released = bool(inventory['sockets']) and all(
        (o.get('closed') or {}).get('released') is True for o in inventory['sockets'])
    wanted.update(p['gap'] for p in capabilities['operation_probes'] if p.get('gap'))
    if capabilities['io_uring']['available'] and capabilities['io_uring'].get('refused_in_scope') is not True:
        wanted.add('io_uring_socket_effects')
    reasons = inventory['qualification']['reasons']
    qualified = dict(inventory, qualification=dict(inventory['qualification']),
                     failures=[], sockets=[], capture_status='COMPLETE')
    # Synthetic positive branch tests the qualifier only. It is not a host receipt.
    census.qualify(qualified, dict(capabilities, exhaustive=True, operation_probes=[],
                                  io_uring={'available':False}))
    emit('census/named-qualification-reasons', wanted == {f['capability'] for f in reasons}
         and all(f.get('evidence') and f['reason'] for f in reasons)
         and wanted <= {f['capability'] for f in inventory['failures']}
         and not any(f['capability'] == 'qualification' for f in inventory['failures'])
         and released
         and qualified['status'] == 'COMPLETE' and qualified['qualification']['gaps'] == [])

    # Independent of the fixture's bounds: every (family, type, protocol) this
    # kernel accepts, over a wider range and extreme values, must be a discovered
    # cell. A synthetic registry checks that unknown entries fail closed.
    known = {(c['family'], c['type'], c['protocol']) for c in capabilities['combinations'] if c['available']}
    triples = {tuple(c['kernel']) for c in capabilities['combinations'] if c.get('kernel')}
    outside, accepted = [], 0
    extremes = (-1, -2**31, 2**31 - 1, 65535, 65536)
    for family, bound in ((1, 1024), (2, 4096), (10, 4096), (16, 1024)):
        for kind in (1, 2, 3, 4, 5, 6, 10):
            for protocol in (*range(bound), *extremes):
                try:
                    probe = socket.socket(family, kind | socket.SOCK_CLOEXEC, protocol)
                except OSError:
                    continue
                with probe:
                    accepted += 1
                    triple = tuple(probe.getsockopt(socket.SOL_SOCKET, o)
                                   for o in (socket.SO_DOMAIN, socket.SO_TYPE, socket.SO_PROTOCOL))
                if (family, kind, protocol) not in known or triple not in triples:
                    outside.append([family, kind, protocol, list(triple)])
    synthetic = census.reconcile_registry(
        'protocol  size sockets\nFUTUREPROTO 1 0\nTCP 1 0\nPACKET 1 0\nINET_SMC 1 0\n',
        'alias net-pf-2-proto-4000 future\nalias net-pf-10-proto-256-type-1 smc\nalias net-pf-17 other\n')
    unexplained = sorted(str(u.get('name') or u.get('alias')) for u in synthetic['unexplained'])
    smc = any(c['available'] and c['protocol'] == 256 for c in capabilities['combinations'])
    evidence['protocol_inventory'] = dict(accepted=accepted, outside=outside, smc_available=smc,
        registry=capabilities.get('registry'), synthetic=synthetic)
    emit('census/protocol-inventory-covers-kernel', capabilities['exhaustive'] is True
         and capabilities['registry']['unexplained'] == [] and accepted > 0 and not outside
         and unexplained == ['FUTUREPROTO', 'net-pf-2-proto-4000']
         and 'protocol_inventory_bounds' not in inventory['qualification']['gaps'])
    # Explicit refusal: the live receipt's sockets carry kernel triples; with one
    # triple removed from the inventory exactly its sockets are refused.
    measured = [o for o in inventory['sockets'] if o.get('family') in (1, 2, 10, 16)]
    target = (2, 1, 256) if smc else (1, 1, 0)
    named = sorted(o['identity'] for o in measured if tuple(o.get('kernel_triple') or ()) == target)
    narrowed = dict(capabilities, exhaustive=True, operation_probes=[], io_uring={'available': False},
        combinations=[c for c in capabilities['combinations'] if tuple(c.get('kernel') or ()) != target])
    refused = dict(inventory, qualification=dict(inventory['qualification']), failures=[],
                   capture_status='COMPLETE')
    census.qualify(refused, narrowed)
    refusals = [f for f in refused['qualification']['reasons'] if f['capability'] == 'protocol_inventory_bounds']
    emit('census/undiscovered-protocol-refused', bool(named)
         and all(o.get('kernel_triple') for o in measured)
         and len(refusals) == 1 and sorted(x['identity'] for x in refusals[0]['evidence']['sockets']) == named
         and refused['status'] == 'INCOMPLETE'
         and all(row['status'] == 'STANDS DOWN' for rows in finish_rows(census, refused) for row in rows))

    # operation_configuration: every available operation of the four families is
    # qualified with its own address fixture, decoded from the kernel's sockaddr;
    # L2TP/IP connection ids are exact; SCTP bindx/connectx/peeloff fail closed.
    l2tp = [c for c in operations if c['protocol'] == 115 and c['result'] == 0]
    l2tp_services = {objects[e['socket']]['inode']: e['address'] for e in inventory['events']
                     if e['kind'] == 'service' and objects[e['socket']]['protocol'] == 115}
    fixture = lambda conn: census.fixture_address(2, 115, conn)
    sctp = any(c['available'] and c['protocol'] == 132 for c in capabilities['combinations'])
    bindx = run('sctp_bindx', SCTP_BINDX_PROBE)[0] if sctp else None
    evidence['operation_configuration'] = dict(l2tp=l2tp, l2tp_services=l2tp_services,
        bindx_failures=bindx and bindx['failures'])
    emit('census/protocol-specific-operations',
         not any(p.get('gap') for p in capabilities['operation_probes'])
         and all(o.get('decoded') for p in capabilities['operation_probes'] if p['family'] in (2, 10)
                 for o in p['operations'])
         and not any(f['capability'] in ('socket_address', 'operation_configuration') for f in inventory['failures'])
         and {c['family'] for c in l2tp} == {f for f in (2, 10) if any(
             c['available'] and c['family'] == f and c['protocol'] == 115 for c in capabilities['combinations'])}
         and all(l2tp_services.get(c['inode'], {}).get('conn_id') == c['conn_id'] for c in l2tp)
         and census.sampled_matches(2, fixture(7), fixture(7), 115)
         and not census.sampled_matches(2, fixture(7), fixture(8), 115)
         and (bindx is None or (bindx.get('root_status') == 0 and bindx['capture_status'] == 'INCOMPLETE'
              and [f['reason'] for f in bindx['failures'] if f['capability'] == 'operation_configuration']
              == ['SCTP bindx add binds, connects or installs outside observed operations'])))

    extended, acks = run('socket_extensions', EXTENDED_SOCKET_PROBE)
    accepted = [a for a in acks if a['kind'] == 'accept']
    implicit = [a for a in acks if a['kind'] == 'implicit']
    services = [e for e in extended['events'] if e['kind'] == 'service']
    objects = {o['identity']: o for o in extended['sockets']}
    emit('census/accepted-and-implicit', complete_capture(extended)
         and {a['syscall'] for a in accepted} == {43,288}
         and all(any(o['inode'] == a['inode'] and o.get('accepted_from')
                     for o in objects.values()) for a in accepted)
         and len(implicit) == 2
         and all(sum(objects[e['socket']]['inode'] == a['inode']
                     and e['operation'] == 'implicit_receive_binding'
                     and e['address']['port'] == a['address'][1] for e in services) == 1
                 for a in implicit)
         and any(a['kind'] == 'socketcall' for a in acks)
         and any(e.get('abi') == 'i386_socketcall' for e in services))
    unix, acks = run('implicit_unix', r"""
import json,os,socket
receiver=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
receiver.bind('\0v111-implicit-'+str(os.getpid()))
sender=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
sender.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
sender.sendto(b'x',receiver.getsockname())
os.write(1,(json.dumps(dict(address=repr(sender.getsockname())))+'\n').encode())
""")
    # The compat entry decoder stops before dereferencing the unsupported msghdr.
    compat_code = EXTENDED_SOCKET_PROBE[EXTENDED_SOCKET_PROBE.index('code=mmap.mmap'):]
    compat_code = 'import ctypes,json,mmap,os,socket,struct\n' + compat_code
    compat_code = compat_code.replace('    os.close(fd)', '    args[:3]=[fd,0,0]; call(16,base)\n    os.close(fd)')
    compat, _ = run('compat_message', compat_code.replace("    ack(kind='socketcall',inode=os.readlink('/proc/self/fd/'+str(fd)))", '    pass'))
    emit('census/unsupported-address-and-compat', unix['capture_status'] == 'COMPLETE'
         and bool(acks) and not any(f['capability'] == 'implicit_address' for f in unix['failures'])
         and compat['capture_status'] == 'INCOMPLETE'
         and any(f['capability'] == 'compat_socketcall_message' for f in compat['failures']))
    async_code = ('import ctypes,json,os,socket,struct\n'
                  'LIBC=ctypes.CDLL(None,use_errno=True)\n' + inspect.getsource(census.io_uring_probe)
                  + '\nprint(json.dumps(io_uring_probe()))\n')
    asynchronous, acks = run('async_effect', async_code)
    effect = acks[0] if acks else {}
    emit('census/async-effects-stand-down', bool(effect)
         and (not effect.get('available') or (
             effect['socket_effect'].get('completion_result', -1) >= 0
             and asynchronous['capture_status'] == 'INCOMPLETE'
             and any(f['capability'] == 'io_uring' for f in asynchronous['failures']))))
    # io_uring_socket_effects: no ring may exist in measured scope. An outside
    # helper owns a ring and permits pidfd_getfd; taking it (or reopening it via
    # /proc) must fail the capture. A task's first stop refuses inherited rings.
    helper = subprocess.Popen([sys.executable, '-B', '-c', RING_HELPER], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True)
    try:
        held = json.loads(helper.stdout.readline())
        taken, ring_acks = run('ring_pidfd_getfd', RING_TAKER, held['pid'], held['fd'])
    finally:
        helper.stdin.close()
        helper.wait(timeout=120)
    ring_reasons = sorted(f['reason'] for f in taken['failures'] if f['capability'] == 'io_uring')
    took = ring_acks[0] if ring_acks else {}
    expected_reasons = ['measured task holds an io_uring instance (syscall 438 installed descriptor %d)'
                        % took.get('fd', -1)]
    if took.get('reopened') is not None:
        expected_reasons.append('measured task holds an io_uring instance (syscall 257 installed descriptor %d)'
                                % took['reopened'])
    unit = census.Collector(dict(identity='inherited-ring', argv=['probe']))
    unit.r['state'] = 'collecting'
    unit.birth(os.getpid())
    unit.fd_table = lambda pid: {7: 'anon_inode:[io_uring]'}
    entry = bytearray(88)
    entry[0] = 1
    struct.pack_into('<I9Q', entry, 4, 0xc000003e, 0, 0, 39, 0, 0, 0, 0, 0, 0)  # getpid entry
    real_ptrace = census.ptrace
    census.ptrace = lambda request, pid, address=0, data=0: (
        ctypes.memmove(data, bytes(entry), 88), 88)[1]
    try:
        unit.syscall(os.getpid())
    finally:
        census.ptrace = real_ptrace
    evidence['io_uring_refusal'] = dict(helper=held, acks=ring_acks, reasons=ring_reasons,
                                        inherited=unit.r['failures'])
    emit('census/io-uring-refused-in-scope', held.get('fd', -1) >= 0
         and took.get('link') == 'anon_inode:[io_uring]' and taken.get('root_status') == 0
         and ring_reasons == sorted(expected_reasons) and taken['capture_status'] == 'INCOMPLETE'
         and all(row['status'] == 'STANDS DOWN' for rows in taken['consumer_rows'].values() for row in rows)
         and [f['reason'] for f in unit.r['failures']] == [
             'measured task holds an io_uring instance (inherited descriptor 7)']
         and capabilities['io_uring'].get('refused_in_scope') is True)
    escape_results = []
    for nr in (56,435):
        escaped, acks = run('escape_' + str(nr), ESCAPE_PROBE, nr)
        escape_results.append(escaped['capture_status'] == 'INCOMPLETE' and not acks
            and any(f['capability'] == 'trace_inheritance' and f['category'] == 'lifecycle_violation'
                    and f['state'] == 'collecting' for f in escaped['failures']))
    emit('census/clone-untraced', all(escape_results))
    # One completed send exports all four service families and an ordinary fd.
    # A failed send must not be reported as an actual descriptor escape.
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
        name = 'v111-rights-suite-' + str(os.getpid())
        receiver.bind('\0' + name)
        receiver.settimeout(census.HANG_SECONDS)
        escaped, acks = run('escaped_references', r'''
import array, errno, json, os, socket, sys
services=[]
for family, address in ((1,'\0v111-rights-service-'+str(os.getpid())),
                        (2,('127.0.0.1',0)),(10,('::1',0)),(16,(0,0))):
    s=socket.socket(family,3 if family==16 else 1,2 if family==16 else 0)
    s.bind(address)
    if family!=16: s.listen(1)
    services.append(s)
    print(json.dumps(dict(family=family,inode=os.readlink('/proc/self/fd/'+str(s.fileno())))))
with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as transport:
    transport.connect('\0'+sys.argv[1])
    try:
        transport.sendmsg([b'X'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[-1]))])
        raise AssertionError('invalid fd accepted')
    except OSError as exc:
        assert exc.errno==errno.EBADF
    ordinary=os.open(os.devnull,os.O_RDONLY)
    descriptors=[s.fileno() for s in services]+[ordinary]
    assert transport.sendmsg([b'R'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',descriptors))])==1
    os.close(ordinary)
for s in services: s.close()
''', name)
        if escaped.get('root_status') == 0:
            data, controls, flags, _ = receiver.recvmsg(1, socket.CMSG_SPACE(20))
            held = array.array('i')
            assert len(controls) == 1 and controls[0][:2] == (socket.SOL_SOCKET, socket.SCM_RIGHTS)
            held.frombytes(controls[0][2])
            try:
                observed = [os.readlink('/proc/self/fd/' + str(fd)) for fd in held]
            finally:
                for fd in held:
                    os.close(fd)
            sends = [e for e in escaped['events'] if e['kind'] == 'descriptor_send']
            passed = (data == b'R' and not flags & socket.MSG_CTRUNC and len(held) == 5
                and len(acks) == 4 and {a['family'] for a in acks} == {1,2,10,16}
                and observed[:4] == [a['inode'] for a in acks]
                and len(sends) == 1 and len(sends[0]['descriptors']) == 5
                and escaped['capture_status'] == 'INCOMPLETE'
                and any(f['capability'] == 'escaped_reference' and f['category'] == 'lifecycle_violation'
                        and f['reason'] == 'SCM_RIGHTS send %d has no exclusively measured receiver'
                        % sends[0]['sequence'] for f in escaped['failures'])
                and all(p['terminal'] for p in escaped['processes'])
                and all(row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
                        for rows in escaped['consumer_rows'].values() for row in rows))
        else:
            passed = False
        emit('census/escaped-reference', passed)
    # Destruction at drain: every socket without an outside reference must be
    # seen released by the epoll observer. An outside ancestor that takes a
    # reference with pidfd_getfd (no SCM_RIGHTS, no send) must still be caught.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as rendezvous:
        name = 'v111-grab-suite-' + str(os.getpid())
        rendezvous.bind('\0' + name)
        rendezvous.listen(1)
        rendezvous.settimeout(census.HANG_SECONDS)  # Hang detector only.
        grabbed, failures = [], []
        def grab():
            try:
                connection, _ = rendezvous.accept()
                with connection:
                    connection.settimeout(census.HANG_SECONDS)
                    data = b''
                    while not data.endswith(b'\n'):
                        chunk = connection.recv(4096)
                        assert chunk
                        data += chunk
                    target = json.loads(data)
                    pidfd = os.pidfd_open(target['pid'])
                    try:
                        grabbed.append(census.LIBC.syscall(438, pidfd, target['fd'], 0))
                    finally:
                        os.close(pidfd)
                    assert grabbed[-1] >= 0
                    connection.sendall(b'G')
            except BaseException as exc:
                failures.append(repr(exc))
        worker = threading.Thread(target=grab)
        worker.start()
        lifetime, acks = run('destruction_at_drain', r'''
import json, os, socket, sys
released=[]
for family, address in ((1,'\0v111-release-'+str(os.getpid())),(2,('127.0.0.1',0)),(10,('::1',0)),(16,(0,0))):
    s=socket.socket(family,3 if family==16 else 1,2 if family==16 else 0)
    s.bind(address)
    if family!=16: s.listen(1)
    released.append(os.readlink('/proc/self/fd/'+str(s.fileno())))
    s.close()
held=socket.socket(); held.bind(('127.0.0.1',0)); held.listen(1)
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
    channel.connect('\0'+sys.argv[1])
    channel.sendall((json.dumps(dict(pid=os.getpid(),fd=held.fileno()))+'\n').encode())
    assert channel.recv(1)==b'G'
print(json.dumps(dict(released=released,held=os.readlink('/proc/self/fd/'+str(held.fileno())),
                      address=held.getsockname())))
held.close()
''', name)
        worker.join(census.HANG_SECONDS)
        ok = not worker.is_alive() and not failures and len(grabbed) == 1
        try:
            if ok and lifetime.get('root_status') == 0:
                ack, = acks
                with socket.socket(fileno=grabbed[0]) as outside:
                    ok = (os.readlink('/proc/self/fd/' + str(outside.fileno())) == ack['held']
                          and outside.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) == 1
                          and outside.getsockname() == tuple(ack['address']))
                grabbed.clear()
                by_inode = {o['inode']: o for o in lifetime['sockets']}
                held_obj = by_inode.get(ack['held'])
                ok = (ok and held_obj is not None and len(ack['released']) == 4
                    and all((by_inode.get(i) or {}).get('closed', {}) and by_inode[i]['closed'].get('released') is True
                            for i in ack['released'])
                    and all(o['closed'] and o['closed']['released'] for o in lifetime['sockets']
                            if o['inode'] != ack['held'])
                    and held_obj['closed'] is None and held_obj.get('referenced_after_drain') is True
                    and not any(e['kind'] == 'descriptor_send' for e in lifetime['events'])
                    and [f for f in lifetime['failures'] if f['capability'] == 'escaped_reference'] == [dict(
                        capability='escaped_reference', category='lifecycle_violation', state='drained',
                        reason=held_obj['identity'] + ' file is still referenced after descendant drain')]
                    and lifetime['capture_status'] == 'INCOMPLETE'
                    and 'socket_destruction' not in lifetime['qualification']['gaps']
                    and all(row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
                            for rows in lifetime['consumer_rows'].values() for row in rows))
            else:
                ok = False
        finally:
            for fd in grabbed:
                os.close(fd)
        emit('census/destruction-at-drain', ok)
    # A task sharing the descriptor table or memory could swap a descriptor or
    # sockaddr between stops; so could a seccomp listener. Both fail closed.
    shared_probe = r'''
import ctypes, os, socket, struct, sys, threading
libc = ctypes.CDLL(None, use_errno=True)
mode = sys.argv[1]
if mode == 'seccomp':
    assert libc.prctl(38, 1, 0, 0, 0) == 0  # PR_SET_NO_NEW_PRIVS
    allow = ctypes.create_string_buffer(struct.pack('<HBBI', 6, 0, 0, 0x7fff0000))
    program = ctypes.create_string_buffer(struct.pack('<H6xQ', 1, ctypes.addressof(allow)))
    listener = libc.syscall(317, 1, 8, ctypes.byref(program))  # NEW_LISTENER
    assert listener >= 0, ctypes.get_errno()
if mode == 'thread':
    rd, wr = os.pipe()
    t = threading.Thread(target=os.read, args=(rd, 1)); t.start()
s = socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1); s.close()
if mode == 'thread':
    os.write(wr, b'x'); t.join()
'''
    # Netlink autobind on send is decoded from the kernel's sockaddr: exactly
    # one implicit receive binding with the port id the tracee itself reports.
    netlink, acks = run('netlink_implicit', r'''
import json, os, socket, struct
s = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 0)
before = s.getsockname()
assert s.sendto(struct.pack('<IHHII', 16, 1, 0, 1, 0), (0, 0)) == 16  # NLMSG_NOOP to the kernel
print(json.dumps(dict(before=list(before), after=list(s.getsockname()),
                      inode=os.readlink('/proc/self/fd/' + str(s.fileno())))))
s.close()
''')
    objects = [o for o in netlink['sockets'] if acks and o['inode'] == acks[0]['inode']]
    services = [e for e in netlink['events'] if e['kind'] == 'service']
    emit('census/netlink-implicit-binding', complete_capture(netlink) and len(acks) == 1
         and acks[0]['before'][0] == 0 and acks[0]['after'][0] != 0 and len(objects) == 1
         and len(services) == 1 and services[0]['socket'] == objects[0]['identity']
         and services[0]['operation'] == 'implicit_receive_binding'
         and services[0]['address']['nl_pid'] == acks[0]['after'][0]
         and services[0]['address']['nl_groups'] == acks[0]['after'][1]
         and not any(f['capability'] in ('implicit_address', 'socket_address') for f in netlink['failures']))
    shared = {mode: run('shared_' + mode, shared_probe, mode)[0] for mode in ('alone', 'thread', 'seccomp')}
    reasons = {mode: {f['reason'] for f in r['failures'] if f['capability'] == 'shared_socket_memory'}
               for mode, r in shared.items()}
    emit('census/shared-descriptor-table-fails-closed',
         all(r.get('root_status') == 0 and r['lost_events'] == 0 for r in shared.values())
         and complete_capture(shared['alone']) and not reasons['alone']
         and {'syscall %d ran while another live task shared its descriptor table or memory' % nr
              for nr in (41, 49, 50)} <= reasons['thread']
         and reasons['seccomp'] == {'seccomp user notification can install descriptors from outside scope'}
         and all(r['capture_status'] == 'INCOMPLETE' and all(
             row['status'] == 'STANDS DOWN' and row['reason'] == 'census_incomplete'
             for rows in r['consumer_rows'].values() for row in rows)
             for r in (shared['thread'], shared['seccomp'])))
    evidence.update(run_round3_checks(census, emit))
    return evidence


if __name__ == '__main__':
    rows = []
    evidence = run_checks(Path(__file__).resolve().parents[2], lambda name, ok: rows.append([name, bool(ok)]))
    print(json.dumps(dict(rows=rows, evidence=evidence)))
    raise SystemExit(0 if all(ok for _, ok in rows) else 1)
elif 'ROOT' in globals():
    _v111_evidence = run_checks(ROOT, lambda name, ok: expect('VELDO-0111 ' + name, ok))
