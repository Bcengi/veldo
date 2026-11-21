"""Repository-only Linux lifecycle observer for VELDO-0111.

The supervisor and collector are outside the measured scope. Only the TRACEME
root and inherited ptrace children belong to it. No process-name exclusions.
Receipts distinguish event capture from full host qualification. Protocol
discovery inside the four families is reconciled against the kernel's protocol
registry and module aliases, and a measured socket whose kernel protocol was
not discovered fails closed. Other retained gaps still make absence consumers
stand down. See proof/VELDO-0111/OPEN.md.

Linux UAPI: ptrace(2), PTRACE_GET_SYSCALL_INFO (Linux 5.3), x86_64 native ABI.
No privilege changes, compiler, packages, daemon or snapshot fallback.
"""

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time


VERSION = "veldo.lifecycle-census/1"
WALL = 0x40000000
OPTIONS = 1 | 2 | 4 | 8 | 16 | 64 | 0x100000
CONSUMERS = {
    "VELDO-0113": (
        "unavailable/no-client-starts-the-authority",
        "unavailable/no-client-hosts-a-listener",
        "unavailable/no-auto-start-needs-census"),
    "VELDO-0114": (
        "relay/one-endpoint-one-judgement", "relay/no-listener-during-call",
        "relay/no-second-process", "relay/listener-proof-needs-census"),
    "VELDO-0122": (
        "filesystem/transient-and-escaped-writes-are-seen",
        "unavailable/no-transient-write", "unavailable/no-out-of-directory-write",
        "unavailable/no-write-needs-complete-observation"),
}
QUALIFICATION_FAMILIES = {1: "Unix", 2: "IPv4", 10: "IPv6", 16: "netlink"}
# Native socket syscalls (socketcall is normalized to these numbers).
SOCKET_CALLS = frozenset((41, 42, 43, 44, 45, 46, 47, 49, 50, 53, 288, 299, 307))


FAULTS = {
    "facilities": ("preflight", "observer_unavailable", "linux_ptrace"),
    "denied": ("arming", "observer_unavailable", "PTRACE_TRACEME"),
    "abi": ("collecting", "observation_incomplete", "syscall_abi"),
    "corrupt": ("collecting", "event_loss", "collection"),
    "loss": ("collecting", "event_loss", "event_stream"),
    "collector_death": ("collecting", "observation_incomplete", "collector_death"),
    "drain": ("draining", "observation_incomplete", "collection"),
    "finalize": ("drained", "observation_incomplete", "receipt_finalization"),
}
LIBC = ctypes.CDLL(None, use_errno=True)
if hasattr(LIBC, "ptrace"):
    LIBC.ptrace.restype = ctypes.c_long
    LIBC.ptrace.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]


def comm(pid):
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return None


class ObservationFailure(Exception):
    def __init__(self, capability, reason, category="observation_incomplete"):
        super().__init__(reason)
        self.capability, self.category = capability, category


def ptrace(request, pid, address=0, data=0):
    if not hasattr(LIBC, "ptrace"):
        raise OSError(errno.ENOSYS, "ptrace unavailable")
    ctypes.set_errno(0)
    result = LIBC.ptrace(request, pid, address, data)
    error = ctypes.get_errno()
    if result == -1 and error:
        raise OSError(error, os.strerror(error))
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def receipt(request):
    return dict(schema=VERSION, input_identity=request["identity"],
                input_digest=digest(request), implementation_digest=hashlib.sha256(
                    Path(__file__).read_bytes()).hexdigest(), fixture_version=VERSION,
                host=dict(kernel=platform.release(), machine=platform.machine(),
                          python=platform.python_version(), system=platform.system()),
                status="INCOMPLETE", capture_status="INCOMPLETE", state="preflight",
                barriers=[], processes=[], events=[], sockets=[], failures=[],
                lost_events=0, observer=dict(supervisor=os.getppid(), collector=os.getpid(),
                    comm=comm('self')),
                qualification=dict(status="INCOMPLETE", qualified_abis=["x86_64"],
                    gaps=[], reasons=[]),
                metrics={})


def failure(r, capability, reason, category="observation_incomplete"):
    item = dict(capability=capability, reason=str(reason), category=category, state=r["state"])
    if item not in r["failures"]:
        r["failures"].append(item)
    r["status"] = "INCOMPLETE"


def consumer_rows(r, consumer):
    """A valid census permits evaluation, never establishes a consumer's claim."""
    try:
        valid = (isinstance(r, dict) and r.get("schema") == VERSION
                 and r.get("status") == "COMPLETE" and r.get("capture_status") == "COMPLETE"
                 and r.get("state") == "drained" and not r.get("failures")
                 and r.get("lost_events") == 0
                 and r.get("qualification", {}).get("status") == "COMPLETE"
                 and not r.get("qualification", {}).get("gaps")
                 and r["qualification"]["inventory"]["exhaustive"] is True
                 and [b["name"] for b in r["barriers"]] == [
                     "armed_before_exec", "call_returned", "descendants_drained"]
                 and all(isinstance(r[k], str) and len(r[k]) == 64
                         and all(c in '0123456789abcdef' for c in r[k])
                         for k in ("input_digest", "implementation_digest"))
                 and bool(r["input_identity"])
                 and sum(p["root"] is True for p in r["processes"]) == 1
                 and all(p["terminal"] is not None for p in r["processes"]))
    except (AttributeError, KeyError, TypeError, ValueError):
        valid = False
    return [dict(name=name, status="READY" if valid else "STANDS DOWN",
                 reason=None if valid else "census_incomplete") for name in CONSUMERS[consumer]]


def finish(r):
    r["metrics"] = dict(events=len(r["events"]), lost_events=r["lost_events"],
                        measured_tasks=len(r["processes"]),
                        births=sum(not p["root"] for p in r["processes"]),
                        service_events=sum(e["kind"] == "service" for e in r["events"]),
                        supported_families=r["qualification"].get("supported_families", []),
                        unsupported_combinations=len(r["qualification"].get("unsupported_combinations", [])))
    r["consumer_rows"] = {c: consumer_rows(r, c) for c in CONSUMERS}
    return r


def io_uring_probe():
    """Exercise one completed socket effect, not merely a ring submission."""
    import mmap
    params = ctypes.create_string_buffer(120)
    ctypes.set_errno(0)
    fd = LIBC.syscall(425, 2, ctypes.byref(params))
    report = dict(available=fd >= 0, errno=ctypes.get_errno() if fd < 0 else 0,
                  socket_effect=dict(attempted=False))
    if fd < 0:
        return report
    mappings = []
    try:
        probe = ctypes.create_string_buffer(16 + 255 * 8)
        result = LIBC.syscall(427, fd, 8, ctypes.byref(probe), 255)
        report['probe_errno'] = ctypes.get_errno() if result < 0 else 0
        report['supported_opcodes'] = [probe.raw[16 + i * 8] for i in range(probe.raw[1])
            if struct.unpack_from('<H', probe.raw, 18 + i * 8)[0] & 1] if result == 0 else []
        sq_entries, cq_entries = struct.unpack_from('<II', params.raw)
        features = struct.unpack_from('<I', params.raw, 20)[0]
        sq = struct.unpack_from('<7I', params.raw, 40)
        cq = struct.unpack_from('<6I', params.raw, 80)
        sq_size, cq_size = sq[6] + sq_entries * 4, cq[5] + cq_entries * 16
        ring = mmap.mmap(fd, max(sq_size, cq_size) if features & 1 else sq_size,
                         flags=mmap.MAP_SHARED, prot=3, offset=0)
        mappings.append(ring)
        if features & 1:
            completion = ring
        else:
            completion = mmap.mmap(fd, cq_size, flags=mmap.MAP_SHARED, prot=3, offset=0x8000000)
            mappings.append(completion)
        entries = mmap.mmap(fd, sq_entries * 64, flags=mmap.MAP_SHARED, prot=3, offset=0x10000000)
        mappings.append(entries)
        entries[0:64] = bytes(64)
        entries[0] = 45  # IORING_OP_SOCKET, Linux UAPI
        struct.pack_into('<i', entries, 4, socket.AF_INET)
        struct.pack_into('<Q', entries, 8, socket.SOCK_DGRAM)
        struct.pack_into('<I', ring, sq[6], 0)
        struct.pack_into('<I', ring, sq[1], 1)
        result = LIBC.syscall(426, fd, 1, 1, 1, 0, 0)
        report['socket_effect'] = dict(attempted=True, enter_result=result,
                                      errno=ctypes.get_errno() if result < 0 else 0)
        if result >= 0:
            head = struct.unpack_from('<I', completion, cq[0])[0]
            tail = struct.unpack_from('<I', completion, cq[1])[0]
            if head != tail:
                mask = struct.unpack_from('<I', completion, cq[2])[0]
                value = struct.unpack_from('<i', completion, cq[5] + (head & mask) * 16 + 8)[0]
                report['socket_effect']['completion_result'] = value
                if value >= 0:
                    report['socket_effect']['inode'] = os.readlink(f'/proc/self/fd/{value}')
                    os.close(value)
            else:
                report['socket_effect']['missing_completion'] = True
    except (OSError, ValueError, struct.error) as exc:
        report['error'] = str(exc)
    finally:
        for mapping in reversed(mappings):
            mapping.close()
        os.close(fd)
    return report


def unqualified_family(family):
    """A total boundary: unknown future families fail just like known others."""
    try:
        name = socket.AddressFamily(family).name
    except ValueError:
        name = f"AF_{family}"
    return dict(family=family, name=name, capability='family_not_qualified',
                reason=f'{name} ({family}) is outside the Unix, IPv4, IPv6 and netlink qualification universe')


# Discovery bounds per family. IP protocol numbers above 255 exist (MPTCP 262,
# SMC 256); the inet bound leaves headroom above every registered number.
PROTOCOL_BOUNDS = {1: 16, 2: 1024, 10: 1024, 16: 64}
# Kernel protocol registry names (/proc/net/protocols) inside the four families,
# with the protocol number each one is created by. None: the whole family range.
REGISTERED_PROTOCOLS = {
    'TCP': (2, 6), 'UDP': (2, 17), 'UDP-Lite': (2, 136), 'RAW': (2, None), 'PING': (2, 1),
    'MPTCP': (2, 262), 'INET_SMC': (2, 256), 'SCTP': (2, 132), 'L2TP/IP': (2, 115),
    'TCPv6': (10, 6), 'UDPv6': (10, 17), 'UDPLITEv6': (10, 136), 'RAWv6': (10, None),
    'PINGv6': (10, 58), 'MPTCPv6': (10, 262), 'INET6_SMC': (10, 256), 'SCTPv6': (10, 132),
    'L2TP/IPv6': (10, 115), 'UNIX': (1, 0), 'UNIX-STREAM': (1, 0), 'NETLINK': (16, None)}
# Registry names that belong to families outside the qualification universe.
# Their sockets fail as family_not_qualified. Any other name is unexplained.
OTHER_FAMILY_PROTOCOLS = frozenset((
    'SMC', 'SMC6', 'KCM', 'AF_VSOCK', 'NFC_LLCP', 'NFC_RAW', 'PHONET', 'RXRPC', 'LLC', 'PPPOE',
    'KEY', 'VCC', 'DDP', 'RFCOMM', 'QIPCRTR', 'ALG', 'BNEP', 'SCO', 'L2CAP', 'HCI', 'PACKET',
    'XDP', 'MCTP', 'PPTP', 'PPPOL2TP', 'TIPC', 'RDS', 'CAN_RAW', 'CAN_BCM', 'CAN_ISOTP',
    'CAN_J1939', 'X25', 'ROSE', 'NETROM', 'AX25', 'IEEE-802.15.4-RAW', 'IEEE-802.15.4-MAC',
    'IUCV', 'HIDP', 'CMTP', 'ISO', 'ATMPVC', 'ATMSVC', 'PNPIPE'))


def scanned_protocols(family):
    if family in PROTOCOL_BOUNDS:
        return range(PROTOCOL_BOUNDS[family])
    return (0,)


def reconcile_registry(protocols_text, aliases_text):
    """Every registered or autoloadable protocol of the four families must lie
    inside the discovered bounds. Unknown registry names fail closed."""
    unexplained, registered, aliases = [], [], []
    if protocols_text is None:
        unexplained.append(dict(source='/proc/net/protocols', reason='unreadable'))
    for line in (protocols_text or '').splitlines()[1:]:
        if not line.split():
            continue
        name = line.split()[0]
        if name in OTHER_FAMILY_PROTOCOLS:
            continue
        if name not in REGISTERED_PROTOCOLS:
            unexplained.append(dict(source='/proc/net/protocols', name=name,
                                    reason='registered protocol has no known family mapping'))
            continue
        family, protocol = REGISTERED_PROTOCOLS[name]
        registered.append(dict(name=name, family=family, protocol=protocol))
        if protocol is not None and protocol not in scanned_protocols(family):
            unexplained.append(dict(source='/proc/net/protocols', name=name, family=family,
                                    protocol=protocol, reason='outside the discovered bounds'))
    if aliases_text is None:
        unexplained.append(dict(source='modules.alias', reason='unreadable'))
    for line in (aliases_text or '').splitlines():
        words = line.split()
        if len(words) < 2 or words[0] != 'alias' or not words[1].startswith('net-pf-'):
            continue
        parts = words[1].split('-')
        try:
            family = int(parts[2])
            protocol = int(parts[4]) if len(parts) > 4 and parts[3] == 'proto' else None
        except (IndexError, ValueError):
            unexplained.append(dict(source='modules.alias', alias=words[1], reason='undecoded alias'))
            continue
        if family not in QUALIFICATION_FAMILIES:
            continue
        aliases.append(dict(alias=words[1], family=family, protocol=protocol))
        if protocol is not None and protocol not in scanned_protocols(family):
            unexplained.append(dict(source='modules.alias', alias=words[1], family=family,
                                    protocol=protocol, reason='outside the discovered bounds'))
    return dict(registered=registered, aliases=aliases, unexplained=unexplained)


def read_text(path):
    try:
        return Path(path).read_text()
    except OSError:
        return None


def kernel_triple(fd):
    """The kernel's (family, type, protocol) for a descriptor, not syscall arguments."""
    with socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        return [sock.getsockopt(socket.SOL_SOCKET, option)
                for option in (socket.SO_DOMAIN, socket.SO_TYPE, socket.SO_PROTOCOL)]


L2TP_IP = 115  # IPPROTO_L2TP: binds a connection id, not a port.
# setsockopt/getsockopt operations that bind, connect or install descriptors
# outside bind/listen/accept: SCTP bindx, connectx and peeloff (SOL_SCTP 132).
SCTP_UNQUALIFIED = {(54, 100): 'bindx add', (54, 101): 'bindx remove', (54, 107): 'connectx (old)',
                    (54, 110): 'connectx', (54, 111): 'connectx3', (55, 102): 'peeloff',
                    (55, 122): 'peeloff with flags'}


def decode_inet(family, protocol, raw):
    """The exact local endpoint from the kernel's own sockaddr, or None."""
    if len(raw) < 2 or struct.unpack_from('<H', raw)[0] != family:
        return None
    if family == socket.AF_INET and len(raw) >= 8:
        ip = socket.inet_ntop(family, raw[4:8])
        if protocol == L2TP_IP:
            return dict(ip=ip, conn_id=struct.unpack_from('<I', raw, 8)[0]) if len(raw) >= 12 else None
    elif family == socket.AF_INET6 and len(raw) >= 24:
        ip = socket.inet_ntop(family, raw[8:24])
        if protocol == L2TP_IP:
            return dict(ip=ip, conn_id=struct.unpack_from('<I', raw, 28)[0]) if len(raw) >= 32 else None
    else:
        return None
    return dict(ip=ip, port=struct.unpack_from('>H', raw, 2)[0])


def fixture_address(family, protocol, conn_id):
    """A protocol-specific bind address; None means the generic socket address."""
    if protocol != L2TP_IP:
        return None
    if family == socket.AF_INET:
        return struct.pack('<HH4sI4x', family, 0, socket.inet_pton(family, '127.0.0.1'), conn_id)
    return struct.pack('<HHI16sII', family, 0, 0, socket.inet_pton(family, '::1'), 0, conn_id)


def raw_name(call, fd, data=None):
    """bind with exact bytes, or getsockname returning exact bytes."""
    if data is not None:
        buffer = ctypes.create_string_buffer(data, len(data))
        ctypes.set_errno(0)
        if LIBC.bind(fd, buffer, len(data)) != 0:
            raise OSError(ctypes.get_errno(), 'bind')
        return data
    buffer, size = ctypes.create_string_buffer(128), ctypes.c_uint(128)
    ctypes.set_errno(0)
    if LIBC.getsockname(fd, buffer, ctypes.byref(size)) != 0:
        raise OSError(ctypes.get_errno(), 'getsockname')
    return buffer.raw[:min(size.value, 128)]


def host_inventory():
    """Bounded discovery with generated safe operations and exact kernel errors.

    No Linux API enumerates socket protocols directly. The bounds are therefore
    reconciled with the kernel's protocol registry and module aliases; the
    inventory is exhaustive only when nothing registered lies outside them.
    Measured sockets are also checked against the discovered kernel triples.
    """
    inventory, operations = [], []
    for family in range(46):
        protocols = scanned_protocols(family)
        for kind in (1, 2, 3, 4, 5, 6, 10):
            for protocol in protocols:
                ctypes.set_errno(0)
                fd = LIBC.socket(family, kind | socket.SOCK_NONBLOCK | socket.SOCK_CLOEXEC, protocol)
                cell = dict(family=family, type=kind, protocol=protocol, available=fd >= 0,
                            errno=ctypes.get_errno() if fd < 0 else 0)
                inventory.append(cell)
                if fd < 0:
                    continue
                try:
                    cell['kernel'] = kernel_triple(fd)
                except OSError as exc:
                    cell['kernel_errno'] = exc.errno
                if family not in QUALIFICATION_FAMILIES:
                    os.close(fd)
                    continue
                probe = dict(family=family, type=kind, protocol=protocol, operations=[])
                operations.append(probe)
                try:
                    with socket.socket(family, kind, protocol, fileno=fd) as sock:
                        fd = -1
                        if family == 1:
                            address = '\0v111-inventory-' + str(os.getpid())
                        elif family == 2:
                            address = ('127.0.0.1', 0)
                        elif family == 10:
                            address = ('::1', 0)
                        elif family == 16:
                            address = (0, 0)
                        kproto = cell.get('kernel', [0, 0, protocol])[2]
                        specific = fixture_address(family, kproto, 0x1110000 + os.getpid() % 0x10000)
                        if specific is not None:
                            probe['fixture'] = specific.hex()
                        for name in ('bind', 'listen') if kind in (1, 5, 6) else ('bind',):
                            try:
                                if name == 'listen':
                                    sock.listen(1)
                                elif specific is not None:
                                    raw_name('bind', sock.fileno(), specific)
                                else:
                                    sock.bind(address)
                                kernel = raw_name('getsockname', sock.fileno())
                                operation = dict(operation=name, result=0, address=kernel.hex())
                                probe['operations'].append(operation)
                                # Qualified only if the collector's decoder names the endpoint.
                                if family in (2, 10):
                                    operation['decoded'] = decode_inet(family, kproto, kernel)
                                    if operation['decoded'] is None or (specific is not None and (
                                            not sampled_matches(family, specific, kernel, kproto))):
                                        probe['gap'] = 'operation_configuration'
                            except OSError as exc:
                                probe['operations'].append(dict(operation=name, result=-1, errno=exc.errno))
                                probe['gap'] = 'operation_configuration'
                except OSError as exc:
                    probe['gap'] = 'operation_address_fixture'
                    probe['errno'] = exc.errno
                finally:
                    if fd >= 0:
                        os.close(fd)
    registry = reconcile_registry(read_text('/proc/net/protocols'),
                                  read_text(f'/lib/modules/{platform.release()}/modules.alias'))
    return dict(family_limit=46, qualification_families=list(QUALIFICATION_FAMILIES),
                not_qualified_families=[unqualified_family(f) for f in range(46)
                                        if f not in QUALIFICATION_FAMILIES],
                types=[1, 2, 3, 4, 5, 6, 10],
                protocol_scope={'unix': [0, PROTOCOL_BOUNDS[1] - 1], 'inet': [0, PROTOCOL_BOUNDS[2] - 1],
                                'netlink': [0, PROTOCOL_BOUNDS[16] - 1], 'other': [0]},
                registry=registry, exhaustive=not registry['unexplained'] and all(
                    'kernel' in c for c in inventory if c['available']
                    and c['family'] in QUALIFICATION_FAMILIES),
                combinations=inventory, operation_probes=operations,
                io_uring=dict(io_uring_probe(), refused_in_scope=True))


def qualify(r, inventory):
    """Compute named limitations from evidence; never append a blanket failure."""
    reasons = []
    def gap(capability, reason, evidence):
        reasons.append(dict(capability=capability, reason=reason, evidence=evidence))
    if not inventory['exhaustive']:
        gap('protocol_inventory_bounds', 'bounded protocol discovery does not fully qualify the four required families',
            dict(qualification_families=inventory['qualification_families'],
                 protocol_scope=inventory['protocol_scope'],
                 unexplained=(inventory.get('registry') or {}).get('unexplained')))
    # Refuse explicitly: a measured socket whose kernel triple was not discovered.
    discovered = {tuple(c['kernel']) for c in inventory.get('combinations', []) if c.get('kernel')}
    undiscovered = [dict(identity=o.get('identity'), kernel=o.get('kernel_triple'))
                    for o in r['sockets'] if o.get('family') in QUALIFICATION_FAMILIES
                    and tuple(o.get('kernel_triple') or ()) not in discovered]
    if undiscovered:
        gap('protocol_inventory_bounds', 'measured socket protocol is outside the discovered inventory',
            dict(sockets=undiscovered))
    for probe in inventory['operation_probes']:
        if probe.get('gap'):
            gap(probe['gap'], 'available socket needs a qualified address or operation configuration', probe)
    # io_uring is refused in measured scope (Collector.refuse_rings and the
    # setup/enter/register exit check), so completions need no correlation.
    async_probe = inventory['io_uring']
    if async_probe['available'] and async_probe.get('refused_in_scope') is not True:
        gap('io_uring_socket_effects', 'shared ring completions are not correlated to traced socket identities',
            async_probe)
    # Escapes fail capture separately. A socket is destroyed at drain only when
    # the release observer saw its last file reference go; anything else is a gap.
    unreleased = [o['identity'] for o in r['sockets'] if not (o.get('closed') or {}).get('released')
                  and not o.get('referenced_after_drain')]
    if unreleased:
        gap('socket_destruction', 'final file release was not observed at descendant drain',
            dict(identities=unreleased))
    r['qualification'].update(inventory=inventory, reasons=reasons,
        gaps=sorted({item['capability'] for item in reasons}),
        status='INCOMPLETE' if reasons else 'COMPLETE')
    for item in reasons:
        failure(r, item['capability'], item['reason'])
    r['status'] = ('COMPLETE' if r['capture_status'] == 'COMPLETE' and not r['failures']
                   and not reasons else 'INCOMPLETE')


def sampled_matches(family, sample, kernel, protocol=0):
    """Is the kernel's bound address one the sampled bind sockaddr requested?

    Port 0 (inet) and nl_pid 0 (netlink) ask the kernel to choose. An L2TP/IP
    connection id is never chosen by the kernel and must match exactly.
    """
    if protocol == L2TP_IP and family in (socket.AF_INET, socket.AF_INET6):
        span = (8, 12) if family == socket.AF_INET else (28, 32)
        if len(sample) < span[1] or len(kernel) < span[1] or sample[span[0]:span[1]] != kernel[span[0]:span[1]]:
            return False
    if len(sample) < 2 or len(kernel) < 2 or struct.unpack_from('<H', sample)[0] != family \
            or struct.unpack_from('<H', kernel)[0] != family:
        return False
    if family == socket.AF_UNIX:
        requested, bound = sample[2:], kernel[2:]
        if requested[:1] == b'\0':
            return requested == bound
        return requested.split(b'\0', 1)[0] == bound.split(b'\0', 1)[0]
    if family == socket.AF_INET:
        span = (4, 8)
    elif family == socket.AF_INET6:
        span = (8, 24)
    elif family == socket.AF_NETLINK:
        if len(sample) < 12 or len(kernel) < 12:
            return False
        port = sample[4:8]
        return (port == bytes(4) or port == kernel[4:8]) and sample[8:12] == kernel[8:12]
    else:
        return False
    if len(sample) < span[1] or len(kernel) < span[1]:
        return False
    port = sample[2:4]
    return sample[span[0]:span[1]] == kernel[span[0]:span[1]] and port in (bytes(2), kernel[2:4])


class Collector:
    def __init__(self, request):
        self.request = request
        self.r = receipt(request)
        self.live = {}
        self.pending = {}
        self.sockets = {}
        self.root = None
        self.early_stops = {}
        self.newborn = set()
        self.release = None
        self.ring_checked = set()

    def event(self, kind, **values):
        event = dict(sequence=len(self.r["events"]) + 1, time_ns=time.monotonic_ns(),
                     kind=kind, **values)
        self.r["events"].append(event)
        return event["sequence"]

    def barrier(self, name):
        self.r["barriers"].append(dict(name=name, time_ns=time.monotonic_ns(),
                                       sequence=len(self.r["events"])))

    def birth(self, pid, parent=None, operation="root"):
        identity = f"{pid}:{len(self.r['processes']) + 1}"
        task = dict(identity=identity, pid=pid, current_tid=pid, parent=parent,
                    root=parent is None, operation=operation, terminal=None,
                    birth=self.event("launch" if parent is None else "birth",
                                     identity=identity, parent=parent, pid=pid), execs=[])
        self.live[pid] = task
        if parent is not None:
            self.newborn.add(pid)
        self.r["processes"].append(task)
        return task

    def memory(self, pid, address, length):
        if length < 0 or length > 4096:
            raise ValueError("unbounded tracee structure")
        words = [ptrace(2, pid, address + offset) & ((1 << 64) - 1)
                 for offset in range(0, length, 8)]
        return b"".join(word.to_bytes(8, "little") for word in words)[:length]

    def socket_at(self, pid, fd):
        try:
            link = os.readlink(f"/proc/{pid}/fd/{fd}")
        except FileNotFoundError:
            return None
        if not link.startswith("socket:["):
            return None
        return link

    def fd_table(self, pid):
        """The kernel's descriptor table for a stopped task (no sharers allowed)."""
        table = {}
        for name in os.listdir(f'/proc/{pid}/fd'):
            try:
                table[int(name)] = os.readlink(f'/proc/{pid}/fd/{name}')
            except FileNotFoundError:
                pass
        return table

    def refuse_rings(self, pid, links, how):
        """No io_uring instance may exist in a measured task.

        Ring operations (including SQPOLL submissions, which need no syscall)
        run on an instance reached through a descriptor. The only ways a
        measured task holds one are setup/enter/register (refused on success),
        inheritance at its first stop, received rights, pidfd_getfd and /proc
        reopen; each is refused here, so no completion can create, bind or
        accept a socket without failing the capture. A ring owned and driven
        by an outside process is an outside process's effect.
        """
        for fd, link in links:
            if link == 'anon_inode:[io_uring]':
                failure(self.r, 'io_uring', f'measured task holds an io_uring instance ({how} descriptor {fd})')

    def installed(self, pid, entry):
        """Descriptors the syscall installed, from the kernel table, not memory."""
        before = entry['fds']
        return {fd: link for fd, link in self.fd_table(pid).items() if before.get(fd) != link}

    def register_socket(self, pid, fd, family, kind, protocol):
        inode = self.socket_at(pid, fd)
        if inode is None:
            failure(self.r, "socket_identity", f"missing descriptor {pid}:{fd}")
            return
        if inode in self.sockets:
            failure(self.r, 'shared_socket_memory', f'created socket {inode} was already known')
            return
        # Live inode identities are assigned a separate birth sequence, like tasks.
        obj = dict(identity=f"{inode}:{len(self.r['sockets']) + 1}", inode=inode,
                   family=family, type=kind & 15, protocol=protocol, address=None,
                   created=self.event("socket", task=self.live[pid]["identity"], fd=fd,
                                      family=family, type=kind & 15, inode=inode),
                   closed=None, references=[])
        self.sockets[inode] = obj
        self.r["sockets"].append(obj)
        self.watch(pid, fd, obj)
        if family not in QUALIFICATION_FAMILIES:
            obj['not_qualified'] = unqualified_family(family)
            failure(self.r, 'family_not_qualified', obj['not_qualified']['reason'])
        return obj

    def watch(self, pid, fd, obj):
        """Register the socket's open file with epoll without keeping a reference.

        An epoll item holds no file reference; the kernel removes it when the
        last reference is released (__fput -> eventpoll_release). The temporary
        duplicate exists only while the tracee is stopped and is closed first.
        A listed item after descendant drain is therefore a reference held
        outside the measured scope, whatever path carried it there.
        """
        try:
            if self.release is None:
                raise OSError(errno.EBADF, 'release observer not armed')
            dup = self.duplicate(pid, fd, obj['inode'])
            try:
                obj['kernel_triple'] = kernel_triple(dup)
                self.release.register(dup, 0)
            finally:
                os.close(dup)
            obj['release_observer'] = 'epoll_file_release'
        except OSError as exc:
            failure(self.r, 'socket_destruction', f'release observer unavailable: {exc}',
                    'observer_unavailable')

    def duplicate(self, pid, fd, inode):
        """A collector-owned duplicate of a stopped tracee's socket descriptor."""
        pidfd = os.pidfd_open(pid, 0x80)  # PIDFD_THREAD: pid is a stopped TID.
        try:
            ctypes.set_errno(0)
            dup = LIBC.syscall(438, pidfd, fd, 0)  # pidfd_getfd
            if dup < 0:
                raise OSError(ctypes.get_errno(), 'pidfd_getfd')
        finally:
            os.close(pidfd)
        if os.readlink(f'/proc/self/fd/{dup}') != inode:
            os.close(dup)
            raise OSError(errno.ESTALE, 'duplicated a different file')
        return dup

    def kernel_name(self, pid, fd, inode):
        """The kernel's own local address for the socket, not tracee memory."""
        dup = self.duplicate(pid, fd, inode)
        try:
            buffer, size = ctypes.create_string_buffer(128), ctypes.c_uint(128)
            ctypes.set_errno(0)
            if LIBC.getsockname(dup, buffer, ctypes.byref(size)) != 0:
                raise OSError(ctypes.get_errno(), 'getsockname')
            return buffer.raw[:min(size.value, 128)]
        finally:
            os.close(dup)

    def sharers(self, pid):
        """Live measured tasks sharing pid's descriptor table or address space.

        Only such a task (or a seccomp listener, refused separately) can swap a
        descriptor between entry and exit stops; kcmp compares kernel objects.
        """
        shared = []
        for other in self.live:
            if other == pid:
                continue
            for kind in (2, 1):  # KCMP_FILES, KCMP_VM
                ctypes.set_errno(0)
                value = LIBC.syscall(312, pid, other, kind, 0, 0)
                if value < 0:
                    raise ObservationFailure('shared_socket_memory', f'kcmp unavailable: errno {ctypes.get_errno()}')
                if value == 0:
                    shared.append(self.live[other]['identity'])
                    break
        return shared

    def unix_peer(self, inode):
        """Peer inode of a Unix socket from NETLINK_SOCK_DIAG (UDIAG_SHOW_PEER)."""
        number = int(inode[8:-1])
        request = struct.pack('<IHHII', 40, 20, 1, 1, 0) + struct.pack(
            '<BBHIIIII', socket.AF_UNIX, 0, 0, 0xffffffff, number, 4, 0xffffffff, 0xffffffff)
        with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4) as diag:
            diag.sendto(request, (0, 0))
            data = diag.recv(65536)
        length, kind = struct.unpack_from('<IH', data)
        if kind != 20 or length > len(data):
            raise ObservationFailure('shared_socket_memory', 'unix_diag did not answer for a socketpair member')
        offset = 16 + 16
        while offset + 4 <= length:
            size, attribute = struct.unpack_from('<HH', data, offset)
            if size < 4:
                break
            if attribute == 2:  # UNIX_DIAG_PEER
                return f'socket:[{struct.unpack_from("<I", data, offset + 4)[0]}]'
            offset += (size + 3) & ~3
        return None

    def referenced(self):
        """Socket inodes whose file is still open anywhere, read after drain."""
        alive = set()
        for line in Path(f'/proc/self/fdinfo/{self.release.fileno()}').read_text().splitlines():
            if line.startswith('tfd:'):
                inode = int(line.split('ino:')[1].split()[0], 16)
                alive.add(f'socket:[{inode}]')
        return alive

    def drained_references(self):
        alive = self.referenced()
        for obj in self.r['sockets']:
            if obj.get('release_observer') != 'epoll_file_release':
                obj['closed'] = None
            elif obj['inode'] in alive:
                obj['closed'] = None
                obj['referenced_after_drain'] = True
                failure(self.r, 'escaped_reference',
                        f'{obj["identity"]} file is still referenced after descendant drain',
                        'lifecycle_violation')
            else:
                obj['closed'] = dict(barrier='descendants_drained', released=True,
                                     observer='epoll_file_release', exact=False)

    def expose(self, pid, obj, operation, address):
        self.event("service", task=self.live[pid]["identity"], socket=obj["identity"],
                   family=obj["family"], type=obj["type"], operation=operation,
                   address=address, abi=obj.get("abi", "x86_64"))

    def unix_binding(self, pid, obj):
        """Read the stopped socket's name; an unnamed sender is not a service.

        /proc renders the kernel's autobind name as @ plus five hex digits.
        Other names cannot safely be decoded from this lossy text interface.
        Explicit binds retain the syscall sockaddr; unknown enrichment fails.
        """
        inode = obj['inode'][8:-1].encode()
        try:
            lines = Path(f'/proc/{pid}/net/unix').read_bytes().splitlines()[1:]
        except OSError as exc:
            failure(self.r, 'implicit_address', f'Unix name unavailable: {exc}')
            return None
        matches = [parts for line in lines if len(parts := line.split(None, 7)) >= 7
                   and parts[6] == inode]
        if len(matches) != 1:
            failure(self.r, 'implicit_address', 'Unix socket name missing or ambiguous')
            return None
        fields = matches[0]
        if len(fields) == 7:
            return None
        name = fields[7]
        if len(name) == 6 and name[:1] == b'@' and all(c in b'0123456789abcdef' for c in name[1:]):
            return dict(unix_name_hex=(b'\0' + name[1:]).hex(),
                        sockaddr_hex=(struct.pack('<H', socket.AF_UNIX) + b'\0' + name[1:]).hex())
        failure(self.r, 'implicit_address', 'Unix name exists but is not a decodable autobind name')
        return None

    def address(self, pid, obj):
        """Enrich an already witnessed successful operation, never infer an event."""
        family = obj['family']
        if family not in (socket.AF_INET, socket.AF_INET6):
            return obj['address']
        suffix = '6' if family == socket.AF_INET6 else ''
        inode = obj['inode'][8:-1]
        for protocol in ('tcp', 'udp', 'raw'):
            try:
                lines = Path(f'/proc/{pid}/net/{protocol}{suffix}').read_text().splitlines()[1:]
            except OSError:
                continue
            for line in lines:
                fields = line.split()
                if len(fields) < 10 or fields[9] != inode:
                    continue
                encoded, port = fields[1].split(':')
                data = bytes.fromhex(encoded)
                data = b''.join(data[i:i + 4][::-1] for i in range(0, len(data), 4))
                return dict(ip=socket.inet_ntop(family, data), port=int(port, 16),
                            sockaddr_hex=obj['address'] if isinstance(obj['address'], str) else None)
        # Protocols without a /proc table (SCTP, UDP-Lite, SMC, L2TP/IP): the
        # kernel's own sockaddr from the operation stop names the endpoint.
        kernel = obj.get('kernel_sockaddr_hex')
        decoded = kernel and decode_inet(family, (obj.get('kernel_triple') or [0, 0, obj['protocol']])[2],
                                         bytes.fromhex(kernel))
        if decoded:
            return dict(decoded, sockaddr_hex=obj['address'] if isinstance(obj['address'], str) else None,
                        source='getsockname')
        failure(self.r, 'socket_address', f'no enrichment for {obj["identity"]}')
        return obj['address']

    def message_memory(self, pid, address, length):
        """Reject known shared or file-backed control mappings before a send.

        This is a qualification failure, not support for shared control buffers.
        A second live task can also share the descriptor table or address space.
        File-backed private mappings can change before their first COW fault.
        Private anonymous memory still needs qualification against outside writers.
        """
        if self.sharers(pid):
            raise ObservationFailure('shared_socket_memory', 'a live task shares the send descriptors or control memory')
        if not length:
            return b''
        for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
            fields = line.split(None, 5)
            low, high = (int(value, 16) for value in fields[0].split('-'))
            if low <= address and address + length <= high:
                if fields[1][3] != 'p' or fields[4] != '0':
                    raise ObservationFailure('shared_socket_memory', 'send control uses shared or file-backed memory')
                return self.memory(pid, address, length)
        raise ObservationFailure('shared_socket_memory', 'send control mapping is not qualified')

    def sent_controls(self, pid, pointer, count):
        if count > 1024:
            raise ObservationFailure('message_layout', 'sendmmsg vector exceeds qualified kernel bound')
        messages = []
        for index in range(count):
            message = self.message_memory(pid, pointer + index * 64, 56)
            control_pointer, length = struct.unpack_from('<QQ', message, 32)
            control = self.message_memory(pid, control_pointer, length)
            descriptors, offset = [], 0
            while offset + 16 <= length:
                size, level, kind = struct.unpack_from('<Qii', control, offset)
                if size < 16 or offset + size > length:
                    raise ObservationFailure('message_layout', 'invalid send ancillary length')
                if (level, kind) == (socket.SOL_SOCKET, socket.SCM_RIGHTS):
                    if (size - 16) % 4:
                        raise ObservationFailure('message_layout', 'unaligned SCM_RIGHTS descriptors')
                    for start in range(offset + 16, offset + size, 4):
                        fd = struct.unpack_from('<i', control, start)[0]
                        descriptors.append(dict(fd=fd, inode=self.socket_at(pid, fd)))
                offset += (size + 7) & ~7
            messages.append(descriptors)
        return messages

    def sent_rights(self, pid, entry, result):
        count = 1 if entry['nr'] == 46 else result
        for descriptors in entry.get('sent_controls', [])[:count]:
            if not descriptors:
                continue
            transport = self.sockets.get(entry.get('inode'))
            peer = self.sockets.get(transport.get('pair_peer')) if transport else None
            # Only a private socketpair has a proven peer. A pathname, peer PID,
            # or a transport's creation inside the scope does not prove ownership.
            contained = bool(peer and not peer.get('exported') and not transport.get('exported'))
            sequence = self.event('descriptor_send', task=self.live[pid]['identity'],
                transport=entry.get('inode'), descriptors=descriptors, contained=contained)
            if not contained:
                failure(self.r, 'escaped_reference',
                        f'SCM_RIGHTS send {sequence} has no exclusively measured receiver',
                        'lifecycle_violation')
                for descriptor in descriptors:
                    obj = self.sockets.get(descriptor['inode'])
                    if obj:
                        obj['exported'] = True
                        obj.setdefault('escaped_references', []).append(sequence)

    def syscall(self, pid):
        buf = ctypes.create_string_buffer(88)
        size = ptrace(0x420e, pid, 88, ctypes.byref(buf))
        raw = buf.raw
        op, arch = raw[0], struct.unpack_from("<I", raw, 4)[0]
        if self.request.get("fault") == "abi":
            arch = 0
        elif self.request.get("fault") == "corrupt":
            op = 255
        if size < 24 or arch not in (0xc000003e, 0x40000003):
            raise ObservationFailure("syscall_abi", f"arch={arch:x} size={size}")
        if op == 1:
            if size < 80:
                raise ValueError("short syscall entry")
            nr, *args = struct.unpack_from("<7Q", raw, 24)
            if pid not in self.ring_checked:
                self.ring_checked.add(pid)
                self.refuse_rings(pid, self.fd_table(pid).items(), 'inherited')
            if nr & 0x40000000:
                raise ObservationFailure("syscall_abi", "x32")
            abi = 'x86_64'
            if arch == 0x40000003:
                if nr != 102:
                    raise ObservationFailure('compat_syscall', f'unqualified i386 syscall {nr}')
                # i386 socketcall arguments are unsigned 32-bit words. Normalize
                # to native socket operation numbers after decoding the ABI.
                operation, pointer = args[:2]
                calls = {1:(41,3), 2:(49,3), 3:(42,3), 4:(50,2), 5:(43,3),
                         6:(51,3), 7:(52,3), 8:(53,4), 9:(44,4), 10:(45,4),
                         11:(44,6), 12:(45,6), 13:(48,2), 14:(54,5), 15:(55,5),
                         18:(288,4)}
                if operation not in calls:
                    raise ObservationFailure('compat_socketcall_message',
                                             f'unqualified socketcall operation {operation}')
                nr, count = calls[operation]
                args = list(struct.unpack('<' + 'I' * count, self.memory(pid, pointer, count * 4)))
                args += [0] * (6 - count)
                abi = 'i386_socketcall'
            entry = dict(nr=nr, args=args, abi=abi)
            if nr in SOCKET_CALLS:
                entry['sharers'] = self.sharers(pid)
            if nr in (47, 53, 299):
                entry['fds'] = self.fd_table(pid)
            if nr in (49, 42):
                entry["address"] = self.memory(pid, args[1], args[2]).hex() if args[1] else None
            if nr in (3, 32, 33, 42, 43, 44, 45, 46, 47, 49, 50, 72, 288, 292, 299, 307):
                entry["inode"] = self.socket_at(pid, args[0])
            if nr in (46, 307):
                entry['sent_controls'] = self.sent_controls(pid, args[1], 1 if nr == 46 else args[2])
            self.pending[pid] = entry
            # A task can deliberately escape tracing with CLONE_UNTRACED.
            flags = args[0] if nr == 56 else 0
            if nr == 435 and args[1] >= 8:
                flags = int.from_bytes(self.memory(pid, args[0], 8), "little")
            if flags & 0x800000:
                raise ObservationFailure("trace_inheritance", "CLONE_UNTRACED would escape measured scope",
                                         "lifecycle_violation")
        elif op == 2:
            if size < 33:
                raise ValueError("short syscall exit")
            result = struct.unpack_from("<q", raw, 24)[0]
            entry = self.pending.pop(pid, None)
            # A newly inherited child starts at its creation syscall's exit.
            if entry is None:
                return
            self.syscall_exit(pid, entry, result)
        else:
            raise ValueError(f"unexpected syscall stop {op}")

    def syscall_exit(self, pid, entry, result):
        nr, a = entry["nr"], entry["args"]
        if result < 0:
            return
        if nr in SOCKET_CALLS and (entry.get('sharers') or self.sharers(pid)):
            failure(self.r, 'shared_socket_memory',
                    f'syscall {nr} ran while another live task shared its descriptor table or memory')
        if nr == 317 and a[0] == 1 and a[1] & 8:
            failure(self.r, 'shared_socket_memory',
                    'seccomp user notification can install descriptors from outside scope')
        if nr in (2, 257, 437, 438):  # open, openat, openat2, pidfd_getfd
            try:
                self.refuse_rings(pid, [(result, os.readlink(f'/proc/{pid}/fd/{result}'))],
                                  f'syscall {nr} installed')
            except OSError:
                pass
        if nr in (54, 55) and a[1] == 132 and (nr, a[2]) in SCTP_UNQUALIFIED:
            failure(self.r, 'operation_configuration',
                    f'SCTP {SCTP_UNQUALIFIED[nr, a[2]]} binds, connects or installs outside observed operations')
        # Decode sends even when the transport was received from outside scope.
        if nr in (46, 307):
            self.sent_rights(pid, entry, result)
        # Received descriptors come from the kernel table diff; tracee control
        # memory can be rewritten after the kernel fills it.
        if nr in (47, 299):
            for fd, link in sorted(self.installed(pid, entry).items()):
                inode = link if link.startswith('socket:[') else None
                self.event("descriptor_transfer", task=self.live[pid]["identity"], fd=fd, inode=inode)
                if inode and inode not in self.sockets:
                    failure(self.r, "descriptor_transfer", "received out-of-scope socket")
                if link == 'anon_inode:[io_uring]':
                    failure(self.r, 'io_uring', 'received an io_uring instance from outside scope')
        if nr == 41:
            obj = self.register_socket(pid, result, *a[:3])
            if obj:
                obj['abi'] = entry.get('abi', 'x86_64')
        elif nr in (43, 288):
            parent = self.sockets.get(entry.get('inode'))
            if parent is None or self.socket_at(pid, a[0]) != entry.get('inode'):
                failure(self.r, 'accept_identity', 'missing or changed listening descriptor')
                return
            obj = self.register_socket(pid, result, parent['family'], parent['type'], parent['protocol'])
            if obj:
                try:
                    obj['kernel_sockaddr_hex'] = self.kernel_name(pid, result, obj['inode']).hex()
                except OSError:
                    obj['kernel_sockaddr_hex'] = None
                obj['accepted_from'] = parent['identity']
                obj['address'] = parent['address']
                obj['abi'] = entry.get('abi', 'x86_64')
                self.event('accept', task=self.live[pid]['identity'], socket=obj['identity'],
                           listener=parent['identity'], syscall=nr, address=self.address(pid, obj))
        elif nr == 53:
            pair = []
            created = sorted(fd for fd, link in self.installed(pid, entry).items() if link.startswith('socket:['))
            if created != sorted(struct.unpack("<2i", self.memory(pid, a[3], 8))):
                failure(self.r, 'shared_socket_memory', 'socketpair result memory differs from installed descriptors')
            for fd in created:
                pair.append(self.register_socket(pid, fd, *a[:3]))
            if len(pair) != 2:
                failure(self.r, 'socket_identity', 'socketpair did not install two sockets')
                pair = [None]
            if all(pair):
                if (pair[0]['family'] != socket.AF_UNIX or self.unix_peer(pair[0]['inode']) != pair[1]['inode']
                        or self.unix_peer(pair[1]['inode']) != pair[0]['inode']):
                    failure(self.r, 'shared_socket_memory', 'socketpair result memory does not name kernel peers')
                else:
                    pair[0]['pair_peer'], pair[1]['pair_peer'] = pair[1]['inode'], pair[0]['inode']
        elif nr in (425, 426, 427):
            failure(self.r, "io_uring", "successful async interface is not decoded")
        elif nr in (49, 50, 42, 44, 45, 46, 47, 299, 307):
            inode = entry.get("inode")
            if inode is None:
                failure(self.r, "socket_identity", f"syscall {nr} has no socket identity")
                return
            obj = self.sockets.get(inode)
            if obj is None:
                failure(self.r, "descriptor_transfer", f"unknown socket {inode}")
                return
            if self.socket_at(pid, a[0]) != inode:
                failure(self.r, "descriptor_race", "socket changed during operation")
                return
            if nr in (49, 50) or (obj['type'] in (2, 3, 10) and obj['address'] is None):
                try:
                    obj['kernel_sockaddr_hex'] = self.kernel_name(pid, a[0], inode).hex()
                except OSError as exc:
                    obj['kernel_sockaddr_hex'] = None
                    failure(self.r, 'socket_address', f'kernel address unavailable: {exc}')
            if nr == 49:
                if obj['kernel_sockaddr_hex'] is not None and not sampled_matches(
                        obj['family'], bytes.fromhex(entry['address'] or ''),
                        bytes.fromhex(obj['kernel_sockaddr_hex']),
                        (obj.get('kernel_triple') or [0, 0, obj['protocol']])[2]):
                    failure(self.r, 'shared_socket_memory', 'kernel-bound address differs from the sampled sockaddr')
                obj["address"] = entry["address"]
                self.event("bind", task=self.live[pid]["identity"], socket=obj["identity"],
                           family=obj["family"], address=obj["address"])
                if obj["type"] in (2, 3, 10):
                    self.expose(pid, obj, "bind", self.address(pid, obj))
            elif nr == 50:
                self.expose(pid, obj, "listen", self.address(pid, obj))
            elif obj["type"] in (2, 3, 10) and obj["address"] is None:
                if obj['family'] == socket.AF_UNIX:
                    address = self.unix_binding(pid, obj)
                    bound = address is not None
                elif obj['family'] == socket.AF_NETLINK and obj.get('kernel_sockaddr_hex'):
                    # A successful netlink send autobinds; the kernel's own
                    # sockaddr names the assigned port id exactly.
                    kernel = bytes.fromhex(obj['kernel_sockaddr_hex'])
                    port, groups = struct.unpack_from('<II', kernel, 4)
                    address = dict(nl_pid=port, nl_groups=groups, sockaddr_hex=kernel.hex())
                    bound = port != 0
                    if port == 0:
                        failure(self.r, 'implicit_address', 'netlink operation left no kernel port id')
                else:
                    address = self.address(pid, obj)
                    bound = isinstance(address, dict) and address.get('port', 0) > 0
                    if not bound:
                        failure(self.r, "implicit_address", "successful operation has no decoded local binding")
                if bound:
                    obj['address'] = address
                    self.expose(pid, obj, "implicit_receive_binding", address)
        elif nr in (32, 33, 72, 292) and entry.get("inode"):
            self.event("descriptor_alias", task=self.live[pid]["identity"],
                       inode=entry["inode"], syscall=nr, result=result)
        elif nr == 3 and entry.get("inode"):
            obj = self.sockets.get(entry["inode"])
            closed = self.event("close", task=self.live[pid]["identity"], inode=entry["inode"],
                                socket=obj["identity"] if obj else None, fd=a[0])
            if obj:
                obj.setdefault('descriptor_closes', []).append(closed)
        elif nr in (436, 438):
            failure(self.r, "descriptor_operation", f"unqualified syscall {nr}")

    def run(self):
        r, req = self.r, self.request
        if platform.system() != "Linux" or platform.machine() != "x86_64" or req.get("fault") == "facilities":
            failure(r, "linux_ptrace", "required Linux native x86_64 facilities unavailable",
                    "observer_unavailable")
            return finish(r)
        collector_pid = os.getpid()
        root = os.fork()
        if root == 0:
            LIBC.prctl(1, signal.SIGKILL, 0, 0, 0)
            if os.getppid() != collector_pid:
                os._exit(125)
            try:
                # No inherited host lock, sockets or observer sink in the tracee.
                out = os.open(req["output"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                err = os.open(req["error"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                os.dup2(out, 1)
                os.dup2(err, 2)
                null = os.open(os.devnull, os.O_RDONLY)
                os.dup2(null, 0)
                os.closerange(3, 1048576)
                if req.get("fault") == "denied":
                    raise PermissionError(errno.EPERM, "injected ptrace denial")
                ptrace(0, 0)
                os.kill(os.getpid(), signal.SIGSTOP)
                os.chdir(req["cwd"])
                os.execvpe(req["argv"][0], req["argv"], dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            except BaseException as exc:
                os.write(2, str(exc).encode())
                os._exit(125)
        self.root = root
        r["state"] = "arming"
        # Created after the root fork, close-on-exec: never inherited by the scope.
        self.release = select.epoll()
        _, status = os.waitpid(root, WALL)
        if not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGSTOP:
            failure(r, "PTRACE_TRACEME", "root did not reach pre-exec stop", "observer_unavailable")
            return finish(r)
        self.birth(root)
        try:
            ptrace(0x4200, root, 0, OPTIONS)
            self.barrier("armed_before_exec")
            r["state"] = "collecting"
            ptrace(24, root)
            deadline = time.monotonic() + req["deadline"]
            while self.live:
                if time.monotonic() >= deadline:
                    raise TimeoutError("drain_deadline")
                pid, status = os.waitpid(-1, WALL | os.WNOHANG)
                if not pid:
                    time.sleep(0.0005)
                    continue
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    task = self.live.pop(pid, None)
                    if task is None:
                        raise ValueError("terminal wait for unknown birth")
                    task["terminal"] = self.event("exit", identity=task["identity"], status=status)
                    self.pending.pop(pid, None)
                    if pid == root:
                        self.barrier("call_returned")
                        r["root_status"] = status
                        r["state"] = "draining"
                        if req.get("fault") == "drain":
                            raise TimeoutError("injected drain deadline expiry")
                    continue
                if not os.WIFSTOPPED(status):
                    raise ValueError("unexpected wait status")
                event, sig = status >> 16, os.WSTOPSIG(status)
                if pid not in self.live and event != 4:
                    # Linux may deliver the child's initial stop before its parent's
                    # creation event. Do not run an as-yet unaccounted task.
                    if sig == signal.SIGSTOP and not event and pid not in self.early_stops:
                        self.early_stops[pid] = status
                        continue
                    raise ValueError("stop for unknown birth identity")
                if event in (1, 2, 3):
                    message = ctypes.c_ulong()
                    ptrace(0x4201, pid, 0, ctypes.byref(message))
                    self.birth(message.value, self.live[pid]["identity"],
                               {1: "fork", 2: "vfork", 3: "clone"}[event])
                    if req.get("fault") == "loss":
                        r["events"].pop()
                        raise ObservationFailure("event_stream", "missing acknowledged birth event", "event_loss")
                    if message.value in self.early_stops:
                        self.early_stops.pop(message.value)
                        self.newborn.remove(message.value)
                        ptrace(24, message.value)
                elif event == 4:
                    message = ctypes.c_ulong()
                    ptrace(0x4201, pid, 0, ctypes.byref(message))
                    former = message.value
                    if former != pid:
                        displaced = self.live.pop(pid, None)
                        task = self.live.pop(former)
                        if displaced is not None:
                            displaced["terminal"] = self.event("exec_replaced", identity=displaced["identity"])
                        task["current_tid"] = pid
                        self.live[pid] = task
                        self.pending.pop(former, None)
                    task = self.live[pid]
                    task["execs"].append(self.event("exec", identity=task["identity"], former_tid=former, pid=pid))
                    self.pending.pop(pid, None)
                elif event == 6:
                    self.live[pid]["comm"] = comm(pid)
                    self.event("exit_pending", identity=self.live[pid]["identity"])
                elif event:
                    raise ValueError(f"unrecognised ptrace event {event}")
                elif sig == signal.SIGTRAP | 0x80:
                    self.syscall(pid)
                elif sig == signal.SIGSTOP:
                    if pid not in self.newborn:
                        raise ValueError("unqualified tracee group stop")
                    self.newborn.remove(pid)
                else:
                    ptrace(24, pid, 0, sig)
                    continue
                if req.get("fault") == "collector_death" and event in (1, 2, 3):
                    os.kill(os.getpid(), signal.SIGKILL)
                ptrace(24, pid)
            self.barrier("descendants_drained")
            if self.early_stops:
                raise ValueError("unmatched child stops at drain")
            r["state"] = "drained"
            if req.get("fault") == "finalize":
                raise ObservationFailure("receipt_finalization", "injected receipt finalization failure")
            self.drained_references()
            if not r["failures"]:
                r["capture_status"] = "COMPLETE"
            r['status'] = 'COMPLETE' if r['capture_status'] == 'COMPLETE' else 'INCOMPLETE'
        except ObservationFailure as exc:
            failure(r, exc.capability, str(exc), exc.category)
            if exc.category == "event_loss":
                r["lost_events"] += 1
        except (OSError, ValueError, KeyError, TimeoutError) as exc:
            failure(r, "collection", str(exc), "event_loss" if isinstance(exc, (ValueError, KeyError))
                    else "observation_incomplete")
            if isinstance(exc, (ValueError, KeyError)):
                r["lost_events"] += 1
        finally:
            # Only identities created in this collector's ptrace scope are signalled.
            for pid in set(self.live) | set(self.early_stops):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            while self.live:
                try:
                    pid, status = os.waitpid(-1, WALL)
                except ChildProcessError:
                    break
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self.live.pop(pid, None)
                elif os.WIFSTOPPED(status):
                    try:
                        ptrace(7, pid, 0, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        return finish(r)


def supervise(request):
    """Separate subreaper owns the collector and its orphans, never caller children."""
    r = receipt(request)
    if platform.system() != "Linux" or not hasattr(LIBC, "prctl"):
        failure(r, "linux_ptrace", "required Linux facilities unavailable", "observer_unavailable")
        return finish(r)
    LIBC.prctl(1, signal.SIGKILL, 0, 0, 0)
    if os.getppid() != request["owner_pid"]:
        failure(r, "supervisor_parent", "caller exited before supervision armed")
        return finish(r)
    if LIBC.prctl(36, 1, 0, 0, 0) != 0:
        failure(r, "subreaper", os.strerror(ctypes.get_errno()), "observer_unavailable")
        return finish(r)
    capabilities = host_inventory()
    supervisor_pid = os.getpid()
    collector = os.fork()
    if collector == 0:
        LIBC.prctl(1, signal.SIGKILL, 0, 0, 0)
        if os.getppid() != supervisor_pid:
            os._exit(126)
        try:
            result = Collector(request).run()
            Path(request["receipt"]).write_text(json.dumps(result))
            os._exit(0)
        except BaseException:
            os._exit(126)
    # The collector reports its own drain expiry; this wait only detects a collector that hangs.
    deadline = time.monotonic() + request["deadline"] + HANG_SECONDS
    status = None
    while status is None:
        pid, value = os.waitpid(collector, os.WNOHANG)
        if pid:
            status = value
        elif time.monotonic() >= deadline:
            os.kill(collector, signal.SIGKILL)
            _, status = os.waitpid(collector, 0)
        else:
            time.sleep(0.005)
    # EXITKILL terminates tracees on collector death. Reap only our adopted children.
    reaped = []
    while True:
        try:
            pid, value = os.waitpid(-1, WALL)
            reaped.append(dict(pid=pid, status=value))
        except ChildProcessError:
            break
    if status == 0:
        try:
            r = json.loads(Path(request["receipt"]).read_text())
        except (OSError, ValueError):
            failure(r, "receipt", "collector did not deliver valid JSON", "event_loss")
    else:
        r["state"] = "collecting"
        failure(r, "collector_death", f"collector terminal status {status}")
    r["supervision"] = dict(collector_status=status, adopted_terminal_waits=reaped,
                            supervisor=os.getpid(), collector=collector)
    qualify(r, capabilities)
    r["qualification"]["supported_families"] = sorted({c["family"] for c in capabilities["combinations"] if c["available"]})
    r["qualification"]["unsupported_combinations"] = [c for c in capabilities["combinations"] if not c["available"]]
    return finish(r)


# A deadline here is a hang detector, never a measure of the host: 120 s or more (load rule).
HANG_SECONDS = 120


def census(argv, *, identity, cwd=None, deadline=HANG_SECONDS, fault=None):
    """Measure one argv call through descendant drain. Stdout is returned separately."""
    if fault is not None and fault not in FAULTS:
        raise ValueError("unknown lifecycle fault")
    if not argv or not identity or not 0 < deadline <= 10 * HANG_SECONDS:
        raise ValueError("argv, identity and a bounded deadline are required")
    with tempfile.TemporaryDirectory(prefix="veldo-census-") as scratch:
        request = dict(argv=list(argv), identity=identity, cwd=str(cwd or Path.cwd()),
                       owner_pid=os.getpid(), deadline=deadline, fault=fault, output=f"{scratch}/stdout",
                       error=f"{scratch}/stderr", receipt=f"{scratch}/receipt")
        child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "supervise"],
                               input=json.dumps(request), text=True, capture_output=True)
        try:
            r = json.loads(child.stdout) if child.returncode == 0 else None
            if not isinstance(r, dict):
                raise ValueError("supervisor failed")
        except ValueError as exc:
            r = receipt(request)
            failure(r, "supervisor", str(exc))
        r["stdout"] = Path(request["output"]).read_text(errors="replace") if Path(request["output"]).exists() else ""
        r["stderr"] = Path(request["error"]).read_text(errors="replace") if Path(request["error"]).exists() else ""
        return finish(r)


if __name__ == "__main__":
    if sys.argv[1:] != ["supervise"]:
        raise SystemExit("internal supervisor entry only")
    print(json.dumps(supervise(json.load(sys.stdin))))
