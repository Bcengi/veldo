"""VELDO-0111 live event checks. No unrelated suites or host lock operations.

The four named rows check the collector against independently acknowledged
effects. They are not a declaration of full kernel qualification. That separate
result remains INCOMPLETE when any reachable path is unqualified.
Direct execution emits JSON; the standard suite dispatcher consumes ROOT/expect.
"""

import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


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

INVENTORY_PROBE = r'''
import ctypes,json,os,socket
libc=ctypes.CDLL(None,use_errno=True)
def ack(value):
    os.write(1,(json.dumps(value)+'\n').encode())
# AF_MAX 46, Linux UAPI through AF_MCTP. Higher families cannot be certified
# by this inventory. Protocol zero is only a discovery probe, not exhaustion.
for family in range(46):
    for kind in (1,2,3,4,5,6,10):
        fd=libc.socket(family,kind|socket.SOCK_NONBLOCK|socket.SOCK_CLOEXEC,0)
        ack(dict(kind='combination',family=family,type=kind,protocol=0,
                 available=fd>=0,errno=ctypes.get_errno() if fd<0 else 0))
        if fd>=0:
            os.close(fd)
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
    hanging, _ = run('deadline', 'import time; time.sleep(10)', deadline=.05)
    results.append(hanging['status'] == 'INCOMPLETE' and hanging['capture_status'] == 'INCOMPLETE')
    for value in (None, {}, {'status': 'COMPLETE'}, dict(empty, status='COMPLETE'),
                  dict(empty, status='COMPLETE', failures=[], qualification=None),
                  dict(empty, status='COMPLETE', failures=[], qualification={
                      'status':'COMPLETE', 'gaps':[], 'inventory':{'exhaustive':True}}, barriers=None)):
        results.extend(all(row['status'] == 'STANDS DOWN' for row in census.consumer_rows(value,c))
                       for c in expected_names)
    emit('census/incomplete-is-not-empty', all(results))

    inventory, combinations = run('inventory', INVENTORY_PROBE)
    evidence['capabilities'] = dict(combinations=combinations, status='INCOMPLETE',
        reason='Protocol-zero discovery is not exhaustive family/protocol/operation qualification',
        supported=[c for c in combinations if c.get('available')],
        unsupported=[c for c in combinations if not c.get('available')])
    emit('census/qualification-does-not-overclaim', len(combinations) == 323
         and all(c.get('available') or c.get('errno', 0) > 0 for c in combinations)
         and inventory['status'] == 'INCOMPLETE'
         and all(row['status'] == 'STANDS DOWN' for rows in inventory['consumer_rows'].values() for row in rows))
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
    escape_results = []
    for nr in (56,435):
        escaped, acks = run('escape_' + str(nr), ESCAPE_PROBE, nr)
        escape_results.append(escaped['capture_status'] == 'INCOMPLETE' and not acks
            and any(f['capability'] == 'trace_inheritance' and f['category'] == 'lifecycle_violation'
                    and f['state'] == 'collecting' for f in escaped['failures']))
    emit('census/clone-untraced', all(escape_results))
    return evidence


if __name__ == '__main__':
    rows = []
    evidence = run_checks(Path(__file__).resolve().parents[2], lambda name, ok: rows.append([name, bool(ok)]))
    print(json.dumps(dict(rows=rows, evidence=evidence)))
    raise SystemExit(0 if all(ok for _, ok in rows) else 1)
elif 'ROOT' in globals():
    _v111_evidence = run_checks(ROOT, lambda name, ok: expect('VELDO-0111 ' + name, ok))
