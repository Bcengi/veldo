"""Repository-only Linux lifecycle observer for VELDO-0111.

The supervisor and collector are outside the measured scope. Only the TRACEME
root and inherited ptrace children belong to it. No process-name exclusions.
Receipts distinguish event capture from full host qualification. In particular,
the current operation inventory is NOT an exhaustive Linux protocol inventory.
Until that gap is closed, absence consumers must stand down even on a healthy
capture. See proof/VELDO-0111/OPEN.md.

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


def host_inventory():
    """Bounded discovery with generated safe operations and exact kernel errors.

    No Linux API enumerates every socket protocol, including autoloadable ones.
    The bounds remain explicit and prevent a claim of host-wide exhaustion.
    """
    inventory, operations = [], []
    for family in range(46):
        protocols = range(256) if family in (2, 10) else range(32) if family == 16 else (0,)
        if family in (2, 10):
            protocols = (*protocols, 262)  # MPTCP is outside the 8-bit IP range.
        for kind in (1, 2, 3, 4, 5, 6, 10):
            for protocol in protocols:
                ctypes.set_errno(0)
                fd = LIBC.socket(family, kind | socket.SOCK_NONBLOCK | socket.SOCK_CLOEXEC, protocol)
                cell = dict(family=family, type=kind, protocol=protocol, available=fd >= 0,
                            errno=ctypes.get_errno() if fd < 0 else 0)
                inventory.append(cell)
                if fd < 0:
                    continue
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
                        for name in ('bind', 'listen') if kind in (1, 5, 6) else ('bind',):
                            try:
                                sock.bind(address) if name == 'bind' else sock.listen(1)
                                probe['operations'].append(dict(operation=name, result=0,
                                                                 address=repr(sock.getsockname())))
                            except OSError as exc:
                                probe['operations'].append(dict(operation=name, result=-1, errno=exc.errno))
                                probe['gap'] = 'operation_configuration'
                except OSError as exc:
                    probe['gap'] = 'operation_address_fixture'
                    probe['errno'] = exc.errno
                finally:
                    if fd >= 0:
                        os.close(fd)
    return dict(family_limit=46, qualification_families=list(QUALIFICATION_FAMILIES),
                not_qualified_families=[unqualified_family(f) for f in range(46)
                                        if f not in QUALIFICATION_FAMILIES],
                types=[1, 2, 3, 4, 5, 6, 10],
                protocol_scope={'inet': [0, 255, 262], 'netlink': [0, 31], 'other': [0]},
                exhaustive=False, combinations=inventory, operation_probes=operations,
                io_uring=io_uring_probe())


def qualify(r, inventory):
    """Compute named limitations from evidence; never append a blanket failure."""
    reasons = []
    def gap(capability, reason, evidence):
        reasons.append(dict(capability=capability, reason=reason, evidence=evidence))
    if not inventory['exhaustive']:
        gap('protocol_inventory_bounds', 'bounded protocol discovery does not fully qualify the four required families',
            dict(qualification_families=inventory['qualification_families'],
                 protocol_scope=inventory['protocol_scope']))
    for probe in inventory['operation_probes']:
        if probe.get('gap'):
            gap(probe['gap'], 'available socket needs a qualified address or operation configuration', probe)
    async_probe = inventory['io_uring']
    if async_probe['available']:
        gap('io_uring_socket_effects', 'shared ring completions are not correlated to traced socket identities',
            async_probe)
    # A descriptor close is not a kernel socket destruction notification. The
    # reference may be queued in SCM_RIGHTS or shared with another task.
    if r['sockets']:
        gap('socket_destruction', 'terminal drain bounds socket destruction but does not timestamp it',
            dict(identities=[o['identity'] for o in r['sockets'] if not (o.get('closed') or {}).get('exact')]))
        gap('shared_socket_memory', 'entry/exit inode checks cannot exclude ABA or shared sockaddr mutation',
            dict(identities=[o['identity'] for o in r['sockets']]))
    r['qualification'].update(inventory=inventory, reasons=reasons,
        gaps=sorted({item['capability'] for item in reasons}),
        status='INCOMPLETE' if reasons else 'COMPLETE')
    for item in reasons:
        failure(r, item['capability'], item['reason'])
    r['status'] = ('COMPLETE' if r['capture_status'] == 'COMPLETE' and not r['failures']
                   and not reasons else 'INCOMPLETE')


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

    def register_socket(self, pid, fd, family, kind, protocol):
        inode = self.socket_at(pid, fd)
        if inode is None:
            failure(self.r, "socket_identity", f"missing descriptor {pid}:{fd}")
            return
        # Live inode identities are assigned a separate birth sequence, like tasks.
        obj = dict(identity=f"{inode}:{len(self.r['sockets']) + 1}", inode=inode,
                   family=family, type=kind & 15, protocol=protocol, address=None,
                   created=self.event("socket", task=self.live[pid]["identity"], fd=fd,
                                      family=family, type=kind & 15, inode=inode),
                   closed=None, references=[])
        self.sockets[inode] = obj
        self.r["sockets"].append(obj)
        if family not in QUALIFICATION_FAMILIES:
            obj['not_qualified'] = unqualified_family(family)
            failure(self.r, 'family_not_qualified', obj['not_qualified']['reason'])
        return obj

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
        failure(self.r, 'socket_address', f'no enrichment for {obj["identity"]}')
        return obj['address']

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
            if nr in (49, 42):
                entry["address"] = self.memory(pid, args[1], args[2]).hex() if args[1] else None
            if nr in (3, 32, 33, 42, 43, 44, 45, 46, 47, 49, 50, 72, 288, 292, 299, 307):
                entry["inode"] = self.socket_at(pid, args[0])
            if nr == 47:
                entry["message"] = a_message = self.memory(pid, args[1], 56)
                entry["control"] = struct.unpack_from("<Q", a_message, 32)[0]
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
        if nr == 47 and entry.get("control"):
            message = self.memory(pid, a[1], 56)
            length = struct.unpack_from("<Q", message, 40)[0]
            control = self.memory(pid, entry["control"], length)
            offset = 0
            while offset + 16 <= length:
                size, level, kind = struct.unpack_from("<Qii", control, offset)
                if size < 16 or offset + size > length:
                    raise ValueError("corrupt ancillary descriptor message")
                if (level, kind) == (socket.SOL_SOCKET, socket.SCM_RIGHTS):
                    for start in range(offset + 16, offset + size, 4):
                        fd = struct.unpack_from("<i", control, start)[0]
                        inode = self.socket_at(pid, fd)
                        self.event("descriptor_transfer", task=self.live[pid]["identity"],
                                   fd=fd, inode=inode)
                        if inode and inode not in self.sockets:
                            failure(self.r, "descriptor_transfer", "received out-of-scope socket")
                offset += (size + 7) & ~7
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
                obj['accepted_from'] = parent['identity']
                obj['address'] = parent['address']
                obj['abi'] = entry.get('abi', 'x86_64')
                self.event('accept', task=self.live[pid]['identity'], socket=obj['identity'],
                           listener=parent['identity'], syscall=nr, address=self.address(pid, obj))
        elif nr == 53:
            for fd in struct.unpack("<2i", self.memory(pid, a[3], 8)):
                self.register_socket(pid, fd, *a[:3])
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
            if nr == 49:
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
            for obj in r["sockets"]:
                obj["closed"] = dict(barrier="descendants_drained", exact=False)
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
    deadline = time.monotonic() + request["deadline"] + 2
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


def census(argv, *, identity, cwd=None, deadline=10, fault=None):
    """Measure one argv call through descendant drain. Stdout is returned separately."""
    if fault is not None and fault not in FAULTS:
        raise ValueError("unknown lifecycle fault")
    if not argv or not identity or not 0 < deadline <= 60:
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
