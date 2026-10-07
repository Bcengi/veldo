#!/usr/bin/env python3
"""Start one implementing process tree in an inherited, unprivileged domain.

Invoke with python3 -I -S from a reviewed authority checkout, never the candidate.
No daemon, alternate uid, root helper, or unsandboxed fallback is used.

An agent's Git worktree belongs to the agent's own repository, never the shared one:
`prepare` creates it (private objects, the shared store a read-only alternate, a branch
under refs/heads/agent/<id>/), and `integrate` fetches that namespace into the shared
repository with transfer.fsckObjects, re-hashing every object.
"""
import argparse
import ctypes
import errno
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time

READ = (1 << 0) | (1 << 2) | (1 << 3)
WRITE = sum(1 << n for n in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))
FILE = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 14)


def policy_module():
    source = Path(__file__).resolve().parents[1] / '.veldo/reuse_evidence.py'
    spec = importlib.util.spec_from_file_location('reuse_evidence', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def beneath(path, root):
    return path == root or root in path.parents


def landlock(grants, profile="agent", broker=None):
    """Confine this process and every descendant before candidate code runs.

    broker is the child's Handoff from fork_gate_domain (gate and worker profiles). With it, the
    confined tree has Unix sockets and its own terminals, every operation that could reach
    outside the domain (connect, bind, addressed sends, TIOCGPTPEER) performed by the trusted
    parent's Broker. Without it the strict IPC filter refuses Unix sockets outright. The
    network rule is the same for every profile: nothing below depends on the profile for it.
    """
    libc = ctypes.CDLL(None, use_errno=True)

    def call(number, *args):
        result = libc.syscall(number, *args)
        if result < 0:
            raise OSError(ctypes.get_errno(), 'agent sandbox Landlock unavailable')
        return result

    if platform.machine() != 'x86_64':
        raise RuntimeError('agent sandbox supports reviewed x86_64 syscall numbers only')
    if call(444, 0, 0, 1) < 6:
        raise RuntimeError('agent sandbox needs Landlock ABI 6 (filesystem and IPC scope)')

    class Ruleset(ctypes.Structure):
        _fields_ = [('access', ctypes.c_uint64), ('net', ctypes.c_uint64), ('scoped', ctypes.c_uint64)]

    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('access', ctypes.c_uint64), ('parent', ctypes.c_int32)]

    if libc.prctl(38, 1, 0, 0, 0):
        raise OSError(ctypes.get_errno(), 'cannot set no_new_privs')
    # The IPC filter goes first: whether a broker serves this tree decides the terminal grant.
    mode = broker.install(libc) if broker is not None else install_filter(libc, ipc_program())
    grants = list(grants)
    # Every profile reads /proc: the suites and the control plane read mounts, process identity and
    # cgroups, and Claude's runtime aborts without it (VELDO-0210). Read only: Landlock's ptrace
    # scope still refuses another domain's environ, fd, root, cwd, mem and maps, so what is left is
    # what any account can read.
    grants.append((PROC, READ))
    if mode != 'strict':
        # A fresh terminal pair per open. Its peer comes only through the broker (TIOCGPTPEER),
        # and /dev/pts stays ungranted, so no other terminal on the host is reachable.
        grants.append((PTMX, (1 << 1) | (1 << 2) | DEVICE_IOCTL))
    # Handle device ioctl too; only ordinary files and selected safe devices get grants.
    rules = Ruleset(READ | WRITE | DEVICE_IOCTL, 0, 3)
    fd = call(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
    try:
        for path, access in grants:
            if not path.is_dir():
                access &= FILE | (DEVICE_IOCTL if stat.S_ISCHR(path.stat().st_mode) else 0)
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(access, parent)
                call(445, fd, 1, ctypes.byref(rule), 0)
            finally:
                os.close(parent)
        call(446, fd, 0)
    finally:
        os.close(fd)
    return mode


SECCOMP_NOTIFY, SECCOMP_ALLOW = 0x7fc00000, 0x7fff0000
TIOCGPTPEER = 0x5441
DEVICE_IOCTL = 1 << 15
PTMX = Path('/dev/ptmx')
PROC = Path('/proc')
RESOLVER = Path('/etc/resolv.conf')
RESOLVER_RUNTIME = Path('/run/systemd/resolve')
# Marks a tree a Broker serves, for suites that must know whether they already run inside one.
BROKERED = 'VELDO_SANDBOX_BROKERED'


def ipc_program(mediate=None):
    """Block pathname Unix service escapes too (Landlock ABI 6 scopes abstract ones).

    Do not expose inherited sockets or io_uring as alternate syscall dispatch.
    TCP/TLS is allowed in every profile (agent, gate and mutation worker).

    mediate None is the strict filter: socket(AF_UNIX) is refused. Otherwise (SECCOMP_NOTIFY) Unix
    sockets may be created and every call that names an address or a terminal peer (connect,
    bind, sendto with an address, sendmsg and TIOCGPTPEER) goes to this launcher's Broker.
    sendmmsg reports ENOSYS so libraries fall back to sendmsg.
    """
    deny = 0x50000 | errno.EPERM
    code = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, deny)]
    if mediate is None:
        # socket(AF_UNIX, ...) refused; socketpair is local to this process tree.
        code += [(0x15, 0, 3, 41), (0x20, 0, 0, 16), (0x15, 0, 1, 1), (0x06, 0, 0, deny),
                 (0x20, 0, 0, 0)]
        # Standard descriptors can be terminals opened before confinement. Do not
        # let a child inject input into the orchestrator's terminal through them.
        code += [(0x15, 0, 5, 16), (0x20, 0, 0, 24), (0x15, 0, 1, 0x5412),
                 (0x06, 0, 0, deny), (0x15, 0, 1, 0x541c), (0x06, 0, 0, deny),
                 (0x20, 0, 0, 0)]
    else:
        code += [(0x15, 0, 7, 16), (0x20, 0, 0, 24), (0x15, 0, 1, 0x5412),
                 (0x06, 0, 0, deny), (0x15, 0, 1, 0x541c), (0x06, 0, 0, deny),
                 (0x15, 0, 1, TIOCGPTPEER), (0x06, 0, 0, mediate), (0x20, 0, 0, 0)]
        for number in (42, 46, 49):  # connect, sendmsg, bind
            code += [(0x15, 0, 1, number), (0x06, 0, 0, mediate)]
        code += [(0x15, 0, 1, 307), (0x06, 0, 0, 0x50000 | errno.ENOSYS)]
        # sendto with a NULL destination is a send on a connected socket; any address is mediated.
        code += [(0x15, 0, 6, 44), (0x20, 0, 0, 48), (0x15, 0, 3, 0), (0x20, 0, 0, 52),
                 (0x15, 0, 1, 0), (0x06, 0, 0, SECCOMP_ALLOW), (0x06, 0, 0, mediate),
                 (0x20, 0, 0, 0)]
    # Close IPC, namespace, mount, ptrace and asynchronous syscall alternatives.
    # chmod is intentionally available for normal build/Git use: it cannot grant
    # file-content access denied by Landlock. Metadata secrecy is not claimed.
    for number in (101, 133, 165, 166, 246, 272, 298,
                   303, 304, 308, 310, 311, 313, 321, 323, 425, 426, 427, 428, 429,
                   430, 431, 432, 433, 438, 442, 452):
        code += [(0x15, 0, 1, number), (0x06, 0, 0, deny)]
    code += [(0x06, 0, 0, SECCOMP_ALLOW)]
    return code


def install_filter(libc, code, flags=0):
    """seccomp(SECCOMP_SET_MODE_FILTER). Returns 'strict' for a plain filter, or the listener
    descriptor when flags ask for one."""
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                    ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]

    filters = (Filter * len(code))(*(Filter(*item) for item in code))
    program = Program(len(code), filters)
    result = libc.syscall(ctypes.c_long(317), ctypes.c_long(1), ctypes.c_long(flags),
                          ctypes.byref(program))
    if result < 0:
        raise OSError(ctypes.get_errno(), 'agent sandbox IPC filter unavailable')
    return result if flags else 'strict'


def ipc_filter(libc):
    install_filter(libc, ipc_program())


class Handoff:
    """The confined child's half of fork_brokered: install the notifying filter and hand its
    listener to the trusted parent before any candidate code runs, then close it here, so
    nothing in the domain can answer its own requests."""

    def __init__(self, request, reply):
        self.request, self.reply, self.mode = request, reply, None

    def keep(self):
        return (self.request, self.reply)

    def install(self, libc):
        try:
            try:
                # NEW_LISTENER | WAIT_KILLABLE_RECV: once the broker holds a request, only a fatal
                # signal interrupts the caller, so a request is never performed twice.
                listener = install_filter(libc, ipc_program(SECCOMP_NOTIFY), (1 << 3) | (1 << 5))
            except OSError as error:
                if error.errno != errno.EBUSY:
                    raise
                # A listener is already above this process (this launcher nested in a brokered
                # domain). That broker answers for its own domain's roots, not this one's, so a
                # nested domain gets no Unix sockets at all rather than its parent's reach.
                self.mode = 'strict'
                install_filter(libc, ipc_program())
                os.write(self.request, b'-\n')
                return self.mode
            try:
                os.write(self.request, b'%d\n' % listener)
                if os.read(self.reply, 1) != b'1':
                    raise RuntimeError('agent sandbox broker unavailable')
            finally:
                os.close(listener)
            self.mode = 'broker'
            return self.mode
        finally:
            os.close(self.request)
            os.close(self.reply)


def fork_brokered(roots):
    """Fork a child that will confine itself with a Handoff. Returns (0, Handoff) in the child
    and (pid, Broker or None) in the parent once the child has installed its filter: a Broker
    serving its listener, or None when the child is strict or failed first."""
    request_r, request_w = os.pipe()
    reply_r, reply_w = os.pipe()
    pid = os.fork()
    if not pid:
        os.close(request_r)
        os.close(reply_w)
        return 0, Handoff(request_w, reply_r)
    os.close(request_w)
    os.close(reply_r)
    broker = None
    try:
        line = b''
        while not line.endswith(b'\n'):
            chunk = os.read(request_r, 32)
            if not chunk:
                break
            line += chunk
        if line.strip() not in (b'', b'-'):
            try:
                broker = Broker(roots)
                broker.attach(pid, int(line))
            except (OSError, ValueError):
                broker = None
            os.write(reply_w, b'1' if broker else b'0')
    except OSError:
        broker = None
    finally:
        os.close(request_r)
        os.close(reply_w)
    return pid, broker


def fork_gate_domain(roots):
    """fork_brokered with the gate profile's network rule. The gate launcher and
    mutation_sandbox.confine (every confined mutation worker and case-input proposal) start their
    domain here, so they have one network rule and it cannot drift (VELDO-0208,
    owner decision Telegram 32421): TCP/TLS pass the broker; a Unix address is performed only
    beneath `roots`; ipc_program refuses inherited service sockets and io_uring, and the Landlock
    scope abstract sockets, alike in both."""
    return fork_brokered(roots)


class Broker:
    """The trusted parent's side: performs each mediated call with its own copy of the arguments.

    A Unix address must be absolute and lie beneath one of `roots` (the domain's writable roots,
    where only the domain can create sockets), resolved with no symlink, magic link or mount
    crossing; an abstract address is refused, since this process is outside the Landlock scope
    that keeps abstract sockets inside the domain. connect and addressed sends go through an
    O_PATH descriptor of the resolved socket. bind runs in a helper confined (Landlock) to create
    socket files only beneath `roots`, so the bound name is the caller's own path. Other address
    families (TCP/TLS) pass through: the gate profile's network rule, the only one there is.
    TIOCGPTPEER is answered with the peer of a terminal master the caller itself holds.
    """
    LIMIT = 1 << 24

    def __init__(self, roots):
        self.libc = libc = ctypes.CDLL(None, use_errno=True)
        for call in (libc.connect, libc.bind):
            call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.sendto.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int,
                                ctypes.c_char_p, ctypes.c_uint32]
        libc.sendto.restype = libc.sendmsg.restype = ctypes.c_ssize_t
        libc.sendmsg.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        self.roots = []
        for root in roots:
            self.roots.append((os.fsencode(Path(root).resolve(strict=True)),
                               os.open(root, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)))
        self.listener = None
        self.binder, self.lock = self._binder(), __import__('threading').Lock()

    def _syscall(self, number, *args):
        result = self.libc.syscall(ctypes.c_long(number), *(ctypes.c_long(a) for a in args))
        if result < 0:
            raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
        return result

    def attach(self, pid, number):
        pidfd = self._syscall(434, pid, 0)
        try:
            self.listener = self._syscall(438, pidfd, number, 0)
        finally:
            os.close(pidfd)
        os.set_inheritable(self.listener, False)
        threading = __import__('threading')
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self):
        """Stop serving: the listener, the roots and the bind helper (which exits on EOF)."""
        for descriptor in [self.listener, *(fd for _, fd in self.roots)]:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        self.binder.close()
        try:
            os.waitpid(self.binder_pid, 0)
        except ChildProcessError:
            pass

    # ---- the confined bind helper ------------------------------------------------------------
    def _binder(self):
        import socket
        ours, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        pid = os.fork()
        if pid:
            theirs.close()
            self.binder_pid = pid
            return ours
        try:
            keep = theirs.fileno()
            os.closerange(3, keep)
            os.closerange(keep + 1, 0x7fffffff)
            libc = ctypes.CDLL(None, use_errno=True)
            libc.bind.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            confined = False
            while True:
                data, ancillary, _, _ = theirs.recvmsg(256, socket.CMSG_SPACE(4))
                if not data:
                    os._exit(0)
                if not confined:
                    # Confined on its first request, never earlier: the first request comes after
                    # the served tree confined itself, so a trace's confinement boundary (the first
                    # landlock_restrict_self it records) is still that tree's own.
                    self._confine_binder(libc)
                    confined = True
                fds = [int.from_bytes(d[:4], 'little') for level, kind, d in ancillary
                       if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS]
                code = errno.EBADF
                if len(fds) == 1:
                    code = 0 if libc.bind(fds[0], data, len(data)) == 0 else ctypes.get_errno()
                for fd in fds:
                    os.close(fd)
                os.write(theirs.fileno(), code.to_bytes(4, 'little'))
        except BaseException:
            os._exit(3)

    def _confine_binder(self, libc):
        """Landlock handling only socket creation, granted beneath the roots: a bind of a path whose
        components were swapped for links after the broker checked it still cannot create a
        socket anywhere else."""
        class Ruleset(ctypes.Structure):
            _fields_ = [('access', ctypes.c_uint64)]

        class Beneath(ctypes.Structure):
            _pack_ = 1
            _fields_ = [('access', ctypes.c_uint64), ('parent', ctypes.c_int32)]
        make_sock = 1 << 9
        rules = Ruleset(make_sock)
        ruleset = libc.syscall(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
        if ruleset < 0:
            os._exit(3)
        for root, _ in self.roots:
            parent = os.open(root, os.O_PATH | os.O_CLOEXEC)
            if libc.syscall(445, ruleset, 1, ctypes.byref(Beneath(make_sock, parent)), 0):
                os._exit(3)
            os.close(parent)
        if libc.prctl(38, 1, 0, 0, 0) or libc.syscall(446, ruleset, 0):
            os._exit(3)
        os.close(ruleset)

    def _bind_path(self, sock, address):
        import socket
        with self.lock:
            self.binder.sendmsg([address], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                             sock.to_bytes(4, 'little'))])
            reply = self.binder.recv(4)
        if len(reply) != 4:
            raise OSError(errno.EACCES, 'bind helper unavailable')
        code = int.from_bytes(reply, 'little')
        if code:
            raise OSError(code, os.strerror(code))

    # ---- request service ---------------------------------------------------------------------
    def _serve(self):
        import select
        import threading
        poller = select.poll()
        poller.register(self.listener, select.POLLIN)
        while True:
            try:
                events = poller.poll()
            except InterruptedError:
                continue
            except OSError:
                return
            if any(flags & (select.POLLHUP | select.POLLERR | select.POLLNVAL) and not flags & select.POLLIN
                   for _, flags in events):
                return
            notification = _Notification()
            if self.libc.ioctl(self.listener, ctypes.c_ulong(0xc0502100), ctypes.byref(notification)):
                if ctypes.get_errno() in (errno.ENOENT, errno.EINTR):
                    continue
                return
            threading.Thread(target=self._answer, args=(notification,), daemon=True).start()

    def _answer(self, notification):
        opened = []
        try:
            value = self._perform(notification, opened)
            if value is None:
                return
            error = 0
        except OSError as failure:
            value, error = 0, -(failure.errno or errno.EACCES)
        finally:
            for fd in opened:
                try:
                    os.close(fd)
                except OSError:
                    pass
        response = _Response(notification.id, value, error, 0)
        self.libc.ioctl(self.listener, ctypes.c_ulong(0xc0182101), ctypes.byref(response))

    def _valid(self, notification):
        """The caller is still blocked in this very request (no pid reuse, no completed call)."""
        ident = ctypes.c_uint64(notification.id)
        return self.libc.ioctl(self.listener, ctypes.c_ulong(0x40082102), ctypes.byref(ident)) == 0

    def _read(self, tid, address, length):
        if length == 0:
            return b''
        if length < 0 or length > self.LIMIT:
            raise OSError(errno.EMSGSIZE, 'request too large')
        buffer = ctypes.create_string_buffer(length)
        local, remote = _Iovec(ctypes.addressof(buffer), length), _Iovec(address, length)
        result = self.libc.syscall(ctypes.c_long(310), ctypes.c_long(tid), ctypes.byref(local),
                                   ctypes.c_long(1), ctypes.byref(remote), ctypes.c_long(1), ctypes.c_long(0))
        if result != length:
            raise OSError(errno.EFAULT, 'unreadable request')
        return buffer.raw

    def _descriptor(self, tid, number, opened):
        pidfd = self._syscall(434, tid, os.O_EXCL)  # PIDFD_THREAD
        try:
            fd = self._syscall(438, pidfd, number & 0xffffffff, 0)
        finally:
            os.close(pidfd)
        opened.append(fd)
        return fd

    def _resolve(self, path, opened, directory=False):
        """An O_PATH descriptor of `path` beneath a root, or OSError."""
        if not path.startswith(b'/'):
            raise OSError(errno.EACCES, 'only absolute Unix addresses are brokered')
        for root, rootfd in self.roots:
            if path == root or path.startswith(root + b'/'):
                relative = path[len(root) + 1:] or b'.'
                break
        else:
            raise OSError(errno.EACCES, 'Unix address outside the domain')
        how = struct.pack('QQQ', os.O_PATH | os.O_CLOEXEC | (os.O_DIRECTORY if directory else 0),
                          0, 0x01 | 0x02 | 0x04 | 0x08)  # NO_XDEV, NO_MAGICLINKS, NO_SYMLINKS, BENEATH
        fd = self.libc.syscall(ctypes.c_long(437), ctypes.c_long(rootfd), ctypes.c_char_p(relative),
                               ctypes.c_char_p(how), ctypes.c_long(len(how)))
        if fd < 0:
            code = ctypes.get_errno()
            raise OSError(errno.EACCES if code in (errno.ELOOP, errno.EXDEV) else code, 'unresolvable')
        opened.append(fd)
        return fd

    def _address(self, raw, opened, bind=False):
        """The address this process uses for the caller's raw sockaddr, or None for a bind it
        hands to the helper with the caller's own path (returned second)."""
        if len(raw) < 2:
            raise OSError(errno.EINVAL, 'short address')
        family = int.from_bytes(raw[:2], 'little')
        if family != 1:
            return raw, None
        path = raw[2:]
        if not path:
            if bind:
                return raw, None  # autobind: a kernel-chosen abstract name, nothing named
            raise OSError(errno.EINVAL, 'empty Unix address')
        if path[0] == 0:
            raise OSError(errno.EPERM, 'abstract Unix address')
        path = path.split(b'\0', 1)[0]
        if bind:
            parent, _, name = path.rpartition(b'/')
            if name in (b'', b'.', b'..'):
                raise OSError(errno.EINVAL, 'invalid socket name')
            self._resolve(parent or b'/', opened, directory=True)
            return None, raw[:2] + path + b'\0'
        target = self._resolve(path, opened)
        if not stat.S_ISSOCK(os.fstat(target).st_mode):
            raise OSError(errno.ECONNREFUSED, 'not a socket')
        return b'\x01\x00' + b'/proc/self/fd/%d\0' % target, None

    def _perform(self, notification, opened):
        tid, number, args = notification.pid, notification.data.nr, list(notification.data.args)
        libc = self.libc
        if number == 16:  # ioctl(fd, TIOCGPTPEER, flags)
            master = self._descriptor(tid, args[0], opened)
            info = os.fstat(master)
            if not stat.S_ISCHR(info.st_mode) or (os.major(info.st_rdev), os.minor(info.st_rdev)) != (5, 2):
                raise OSError(errno.ENOTTY, 'not a terminal master')
            flags = args[2] & 0xffffffff
            if not self._valid(notification):
                return None
            peer = libc.ioctl(master, ctypes.c_ulong(TIOCGPTPEER),
                              ctypes.c_ulong((flags | os.O_NOCTTY | os.O_CLOEXEC) & 0xffffffff))
            if peer < 0:
                raise OSError(ctypes.get_errno(), 'TIOCGPTPEER')
            opened.append(peer)
            addfd = _AddFd(notification.id, 1 << 1, peer, 0, os.O_CLOEXEC if flags & os.O_CLOEXEC else 0)
            if libc.ioctl(self.listener, ctypes.c_ulong(0x40182103), ctypes.byref(addfd)) < 0:
                if ctypes.get_errno() == errno.ENOENT:
                    return None  # the caller is gone
                raise OSError(ctypes.get_errno(), 'peer descriptor not delivered')
            return None  # SECCOMP_ADDFD_FLAG_SEND answered the request with the new descriptor
        if number in (42, 49):  # connect, bind
            length = args[2] & 0xffffffff
            if length > 128:
                raise OSError(errno.EINVAL, 'address too long')
            raw = self._read(tid, args[1], length)
            sock = self._descriptor(tid, args[0], opened)
            address, path = self._address(raw, opened, bind=number == 49)
            if not self._valid(notification):
                return None
            if path is not None:
                self._bind_path(sock, path)
                return 0
            call = libc.connect if number == 42 else libc.bind
            if call(sock, address, len(address)):
                raise OSError(ctypes.get_errno(), 'connect' if number == 42 else 'bind')
            return 0
        if number == 44:  # sendto(fd, buf, len, flags, addr, addrlen), addr not NULL
            length = args[5] & 0xffffffff
            if length > 128:
                raise OSError(errno.EINVAL, 'address too long')
            data = self._read(tid, args[1], args[2])
            raw = self._read(tid, args[4], length)
            sock = self._descriptor(tid, args[0], opened)
            address, _ = self._address(raw, opened)
            if not self._valid(notification):
                return None
            sent = libc.sendto(sock, data, len(data), args[3] & 0xffffffff, address, len(address))
            if sent < 0:
                raise OSError(ctypes.get_errno(), 'sendto')
            return sent
        if number == 46:  # sendmsg(fd, msg, flags)
            return self._sendmsg(notification, tid, args, opened)
        raise OSError(errno.ENOSYS, 'unmediated request')

    def _sendmsg(self, notification, tid, args, opened):
        name, namelen, iov, iovlen, control, controllen, _ = struct.unpack(
            '<QI4xQQQQi4x', self._read(tid, args[1], 56))
        if iovlen > 1024 or namelen > 128 or controllen > 65536:
            raise OSError(errno.EMSGSIZE if iovlen > 1024 else errno.EINVAL, 'sendmsg bounds')
        vectors = [struct.unpack_from('<QQ', self._read(tid, iov, 16 * iovlen), 16 * i)
                   for i in range(iovlen)] if iovlen else []
        if sum(length for _, length in vectors) > self.LIMIT:
            raise OSError(errno.EMSGSIZE, 'request too large')
        data = [self._read(tid, base, length) for base, length in vectors]
        raw = self._read(tid, name, namelen) if name and namelen else b''
        ancillary = self._read(tid, control, controllen) if control and controllen else b''
        sock = self._descriptor(tid, args[0], opened)
        address = self._address(raw, opened)[0] if raw else b''
        rebuilt, offset = b'', 0
        while offset + 16 <= len(ancillary):
            length, level, kind = struct.unpack_from('<Qii', ancillary, offset)
            if length < 16 or offset + length > len(ancillary):
                raise OSError(errno.EINVAL, 'malformed control message')
            body = ancillary[offset + 16:offset + length]
            if level == 1 and kind == 1:  # SCM_RIGHTS: the caller's descriptors, as ours
                body = b''.join(self._descriptor(tid, int.from_bytes(body[i:i + 4], 'little'), opened)
                                .to_bytes(4, 'little') for i in range(0, len(body) - len(body) % 4, 4))
            elif level == 1:
                raise OSError(errno.EPERM, 'only SCM_RIGHTS is brokered at socket level')
            entry = struct.pack('<Qii', 16 + len(body), level, kind) + body
            rebuilt += entry + b'\0' * (-len(entry) % 8)
            offset += length + (-length % 8)
        if not self._valid(notification):
            return None
        buffers = [ctypes.create_string_buffer(chunk, len(chunk)) for chunk in data]
        vector = (_Iovec * max(len(buffers), 1))(*(_Iovec(ctypes.addressof(b), len(b)) for b in buffers))
        name_buffer = ctypes.create_string_buffer(address, len(address)) if address else None
        control_buffer = ctypes.create_string_buffer(rebuilt, len(rebuilt)) if rebuilt else None
        header = _Msghdr(ctypes.addressof(name_buffer) if name_buffer else None, len(address),
                         ctypes.addressof(vector), len(buffers),
                         ctypes.addressof(control_buffer) if control_buffer else None, len(rebuilt), 0)
        sent = self.libc.sendmsg(sock, ctypes.byref(header), args[2] & 0xffffffff)
        if sent < 0:
            raise OSError(ctypes.get_errno(), 'sendmsg')
        return sent


class _Data(ctypes.Structure):
    _fields_ = [('nr', ctypes.c_int), ('arch', ctypes.c_uint32), ('ip', ctypes.c_uint64),
                ('args', ctypes.c_uint64 * 6)]


class _Notification(ctypes.Structure):
    _fields_ = [('id', ctypes.c_uint64), ('pid', ctypes.c_uint32), ('flags', ctypes.c_uint32),
                ('data', _Data)]


class _Response(ctypes.Structure):
    _fields_ = [('id', ctypes.c_uint64), ('val', ctypes.c_int64), ('error', ctypes.c_int32),
                ('flags', ctypes.c_uint32)]


class _AddFd(ctypes.Structure):
    _fields_ = [('id', ctypes.c_uint64), ('flags', ctypes.c_uint32), ('srcfd', ctypes.c_uint32),
                ('newfd', ctypes.c_uint32), ('newfd_flags', ctypes.c_uint32)]


class _Iovec(ctypes.Structure):
    _fields_ = [('base', ctypes.c_void_p), ('length', ctypes.c_size_t)]


class _Msghdr(ctypes.Structure):
    _fields_ = [('name', ctypes.c_void_p), ('namelen', ctypes.c_uint32), ('iov', ctypes.c_void_p),
                ('iovlen', ctypes.c_size_t), ('control', ctypes.c_void_p),
                ('controllen', ctypes.c_size_t), ('flags', ctypes.c_int)]


AGENT_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')


def candidate_git(authority=None):
    authority = authority or Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('candidate_git', authority / '.veldo/candidate_git.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard


def branch_parts(reference):
    """(agent id, branch name) of refs/heads/agent/<id>/<name>, or a ValueError."""
    parts = reference.split('/')
    if (len(parts) < 5 or parts[:3] != ['refs', 'heads', 'agent'] or not AGENT_ID.fullmatch(parts[3])
            or any(part in ('', '.', '..') or part.endswith('.lock') or part.startswith('.')
                   for part in parts[4:]) or any(c in reference for c in '\n\\ ~^:?*[')):
        raise ValueError('agent branch must be refs/heads/agent/<id>/<name>: ' + reference)
    return parts[3], '/'.join(parts[4:])


def git_grants(gitdir, private, shared, protected):
    """Commit persistence for a linked worktree of the agent's own repository.

    The agent writes its worktree gitdir, its private object store and its own ref namespace
    refs/heads/agent/<id>/ only. The shared repository, including its object store, is read-only
    (at most an alternate of the private store), and every other ref of the private repository
    (refs/heads/main among them), its config and its hooks stay read-only too. Agent work reaches
    the shared repository only through integrate(), a fetch that re-hashes every object.
    """
    if beneath(private, shared) or beneath(shared, private):
        raise ValueError('agent repository must not share the authority object store')
    head = (gitdir / 'HEAD').read_text().strip()
    if not head.startswith('ref: '):
        raise ValueError('agent worktree needs a branch')
    agent, _ = branch_parts(head[5:])
    objects = private / 'objects'
    alternates = objects / 'info/alternates'
    if alternates.is_symlink() or (objects / 'info').is_symlink():
        raise ValueError('agent object alternates must not be a link')
    for line in (alternates.read_text().splitlines() if alternates.exists() else []):
        line = line.strip()
        if line and not line.startswith('#') and (objects / line).resolve() != (shared / 'objects').resolve():
            raise ValueError('agent object alternates may name only the shared object store')
    namespace = 'refs/heads/agent/' + agent
    grants = [(gitdir, READ | WRITE), (objects, READ | WRITE)]
    for relative in (namespace, 'logs/' + namespace):
        target = private / relative
        target.mkdir(parents=True, exist_ok=True)
        grants.append((target, READ | WRITE))
    for path, _ in grants:
        if (path.resolve() != path or path.is_symlink() or beneath(path, shared)
                or any(beneath(path, p) or beneath(p, path) for p in protected)):
            raise ValueError('Git write grant overlaps protected path: ' + str(path))
    return grants


def git_run(argv):
    authority = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('git_process', authority / '.veldo/git_process.py')
    _git_process = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_git_process)
    result = _git_process.run(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                               *argv], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    if result.returncode:
        raise RuntimeError('git ' + ' '.join(argv[:4]) + ' failed: ' + result.stderr.strip()[-400:])
    return result.stdout.strip()


def prepare(shared, private, worktree, agent, name, start):
    """Create the agent's own bare repository (objects private, the shared store its read-only
    alternate) and a linked worktree on refs/heads/agent/<agent>/<name> at the shared `start`."""
    shared, private, worktree = Path(shared).resolve(strict=True), Path(private).absolute(), Path(worktree).absolute()
    branch_parts('refs/heads/agent/%s/%s' % (agent, name))
    if private.exists() or worktree.exists():
        raise ValueError('agent repository and worktree must be new paths')
    if beneath(private.resolve(), shared) or beneath(shared, private.resolve()):
        raise ValueError('agent repository must be outside the shared repository')
    commit = git_run(['--git-dir=' + str(shared), 'rev-parse', '--verify', '--end-of-options', start + '^{commit}'])
    git_run(['init', '-q', '--bare', str(private)])
    (private / 'objects/info/alternates').write_text(str(shared / 'objects') + '\n')
    git_run(['--git-dir=' + str(private), 'worktree', 'add', '-q', '-b', 'agent/%s/%s' % (agent, name),
             str(worktree), commit])
    return commit


def integrate(shared, private, agent):
    """Bring refs/heads/agent/<agent>/* of the agent repository into the shared one. The fetch runs
    with transfer.fsckObjects, so every object it receives is re-hashed and checked; the private
    store's bytes never enter the shared store any other way, and no other shared ref moves."""
    if not AGENT_ID.fullmatch(agent):
        raise ValueError('invalid agent id')
    namespace = 'refs/heads/agent/%s/*' % agent
    git_run(['--git-dir=' + str(Path(shared).resolve(strict=True)), '-c', 'transfer.fsckObjects=true',
             'fetch', '-q', '--no-tags', '--no-write-fetch-head', '--', str(Path(private).resolve(strict=True)),
             '+%s:%s' % (namespace, namespace)])


def grants_for(config, authority, worktree, scratch, config_path=None, extra_reads=()):
    def expand(value):
        return Path(value.format(authority=authority, worktree=worktree,
                                 scratch=scratch)).expanduser().resolve(strict=True)

    store = Path(config['store']).resolve(strict=True)
    protected = [expand(p) for p in config['deny_write']]
    protected += [authority, Path(__file__).resolve()]
    writes = [expand(p) for p in config['write_roots']]
    # No broad writable home/tmp grants, even if a mistaken config requests one.
    for path in writes:
        if (not any(beneath(path, p) for p in (worktree, scratch))
                or any(beneath(path, p) or beneath(p, path) for p in (store, *protected))):
            raise ValueError('unsafe writable path: ' + str(path))
    if not worktree.is_dir() or worktree == scratch:
        raise ValueError('worktree must be a separate existing directory')
    blocked = [store, Path('/proc'), Path('/run'), Path('/sys'), Path('/dev')]
    blocked += [Path(p).expanduser().resolve() for p in config.get('deny_read', [])]
    if any(beneath(store, p) for p in (authority, worktree, scratch)):
        raise ValueError('authority storage must be outside candidate and authority trees')
    grants = []

    def read(path):
        if any(beneath(path, p) for p in blocked):
            return
        if any(beneath(p, path) for p in blocked):
            # Landlock is an allowlist: never grant an ancestor of a denied path.
            # Skip aliases here; their resolved target must have its own grant.
            for child in path.iterdir():
                if not child.is_symlink():
                    read(child)
        else:
            grants.append((path, READ))

    for path in [*config['read_roots'], '{worktree}', '{authority}', '{scratch}']:
        read(expand(path))
    for value in config.get('optional_read_roots', []):
        path = Path(value).expanduser()
        if path.exists():
            read(path.resolve(strict=True))
    # The agent profile's own read-only additions (VELDO-0210): the reviewed project roots and the
    # selected client's plugin and skill directories, through the same filter as every read root.
    for path in extra_reads:
        read(path)
    # The configuration this launcher hands its tree as VELDO_AGENT_CONFIG, read only, so a launcher
    # the tree starts reads the file it is named. Under another authority (a nested copy of the tree,
    # an installed pack, a scaffold) that file lies outside every other grant of this domain.
    if config_path is not None:
        read(Path(config_path).resolve(strict=True))
    grants += [(p, READ | WRITE) for p in writes]
    # The shared repository is read-only in every profile. An agent worktree must be a linked
    # worktree of the agent's own repository, named by the orchestrator (VELDO_EXPECTED_GIT_COMMON),
    # never derived from the worktree's writable marker; only that repository takes its writes.
    marker = worktree / '.git'
    if marker.exists() or marker.is_symlink():
        guard = candidate_git(authority)
        shared = Path(config.get('git_common_dir') or guard.common_directory(authority)).resolve(strict=True)
        expected = os.environ.get('VELDO_EXPECTED_GIT_COMMON')
        if '{worktree}' in config['write_roots']:
            if not expected:
                raise ValueError('an agent worktree needs its private agent repository (VELDO_EXPECTED_GIT_COMMON)')
            gitdir, private = guard.validate(worktree, expected)
            if gitdir == private:
                raise ValueError('agent worktree must be a linked worktree of a private agent repository')
            if any(beneath(private, w) or beneath(w, private) for w in writes):
                raise ValueError('agent repository must be outside every writable root')
            commons = [private, shared]
        else:
            commons = [guard.validate(worktree, expected or shared)[1]]
        for common in commons:
            if beneath(store, common):
                raise ValueError('authority storage must be outside agent-readable gitdirs')
            read(common)
        if '{worktree}' in config['write_roots']:
            grants += git_grants(gitdir, private, shared, [store, *(p for p in protected if p != authority)])
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)),
               (Path('/dev/urandom'), 1 << 2), (Path('/dev/random'), 1 << 2)]
    return grants, [store, *protected]


def resolver_grants():
    """The DNS resolver configuration, read only, for the agent profile (VELDO-0210).
    /etc/resolv.conf lies under the /etc read root; when it links into /run/systemd/resolve, that
    directory is granted read only. Not the one file it names: systemd-resolved replaces
    stub-resolv.conf by rename on every network change, and a grant binds the inode it was made
    for. Nothing else under /run: the user bus, systemd's sockets and every other runtime file stay
    outside the domain, and the agent profile's filter refuses the Unix sockets in that directory."""
    runtime = RESOLVER_RUNTIME.resolve()
    target = RESOLVER.resolve()
    if target != RESOLVER and target != runtime and beneath(target, runtime) and runtime.is_dir():
        return [(runtime, READ)]
    return []


def installed_tools(config):
    """The installed tools and runtimes the configuration names (optional_read_roots: Node under
    ~/.nvm, Claude Code, the langgraph runtime), as a fresh mutation worker's read-only grants, the
    ones the gate profile gives the same suites. '~' is the account's home, never the HOME a worker
    runs with (its private scratch). A root that is absent, or that holds, is or lies beneath the
    reuse store or a denied path, is not granted; nothing here is ever writable."""
    home = Path(__import__('pwd').getpwuid(os.getuid()).pw_dir)

    def expand(value):
        return home / value[2:] if value.startswith('~/') else Path(value)
    blocked = [Path(config['store']).resolve()]
    blocked += [expand(p).resolve() for p in config.get('deny_read', [])]
    roots = []
    for value in config.get('optional_read_roots', []):
        path = expand(value)
        if not path.exists():
            continue
        path = path.resolve(strict=True)
        if path.is_dir() and not any(beneath(path, p) or beneath(p, path) for p in blocked):
            roots.append(path)
    return roots


def close_descriptors(protected, keep=()):
    for fd in (0, 1, 2):
        try:
            info = os.fstat(fd)
        except OSError:
            continue
        if stat.S_ISSOCK(info.st_mode):
            raise ValueError('standard descriptors may not be service sockets')
        if stat.S_ISREG(info.st_mode):
            # A launcher nested in another domain cannot read /proc; an unnamed file is refused.
            target = Path(os.readlink('/proc/self/fd/' + str(fd))).resolve()
            if any(beneath(target, p) for p in protected):
                raise ValueError('standard descriptor exposes a protected path')
    # Close the actual open set, including descriptors above a lowered rlimit: closerange is
    # close_range(2), which needs no /proc listing (a nested launcher has none).
    low = 3
    for fd in sorted(k for k in keep if k >= 3):
        os.closerange(low, fd)
        low = fd + 1
    os.closerange(low, 0x7fffffff)


CREDENTIAL_LIMIT = 1 << 20


def account_home():
    return Path(__import__('pwd').getpwuid(os.getuid()).pw_dir)


def client_files(config, name):
    """The files one client (claude, codex) receives, from the configuration's `clients`:
    {'credentials': [(source, relative)], 'seed_files': [...], 'read_links': [...],
    'state_dirs': [...], 'state_files': [...]}.

    A client's places are the directories its runner names in the environment (CLAUDE_CONFIG_DIR,
    CODEX_HOME: the account the runner chose), else their defaults under the account's home. Every
    destination lies under the client's own state directory (.claude, .codex), so one client's
    files never land where the other client looks for its own (VELDO-0210). Persistent state
    (state_dirs, state_files) must lie strictly beneath the client's `home` place: the runner's
    configuration directory for that client and account."""
    clients = config.get('clients', {})
    if name not in clients:
        raise ValueError('unknown agent client: ' + str(name))
    entry, home = clients[name], account_home()
    places = {}
    for place, (variable, default) in entry.get('places', {}).items():
        value = os.environ.get(variable) or default
        path = home / value[2:] if value.startswith('~/') else home if value == '~' else Path(value)
        if not path.is_absolute():
            raise ValueError('agent client place must be an absolute directory: ' + place)
        places[place] = path
    files = {}
    for kind in ('credentials', 'seed_files', 'read_links', 'state_dirs', 'state_files'):
        files[kind] = []
        for source, relative in entry.get(kind, {}).items():
            parts = Path(relative).parts
            if Path(relative).is_absolute() or '..' in parts or len(parts) < 2 or parts[0] != '.' + name:
                raise ValueError('agent client file must lie under .%s: %s' % (name, relative))
            source = source.format(**places)
            source = home / source[2:] if source.startswith('~/') else Path(source)
            if kind.startswith('state_') and ('home' not in places or '..' in source.parts
                                              or places['home'] not in source.parents):
                raise ValueError('agent client state must lie beneath its configuration directory: '
                                 + str(source))
            files[kind].append((source, relative))
    files['home'] = places.get('home')
    return files


def state_grants(files, refused):
    """The selected client's persistent state, read and write, as (resolved path, relative) pairs:
    its transcripts, sessions, history and memories, which outlive the scratch in the runner's
    configuration directory for that account (VELDO-0210). An absent entry is created (directory
    0700, file 0600); with no such configuration directory there is nothing to keep. An entry that
    is a link, is of the other kind, resolves outside that directory, or holds, is or lies beneath a
    refused path (the store, a protected path, a denied path, a credential source, the worktree)
    refuses the start."""
    granted, home = [], files.get('home')
    if home is None or not home.is_dir():
        return granted
    home = home.resolve(strict=True)
    for kind, directory in (('state_dirs', True), ('state_files', False)):
        for source, relative in files.get(kind, []):
            if directory:
                try:
                    os.mkdir(source, 0o700)
                except FileExistsError:
                    pass
            else:
                try:
                    os.close(os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                     0o600))
                except FileExistsError:
                    pass
            mode = os.lstat(source).st_mode
            real = source.resolve(strict=True)
            if (not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)) or home not in real.parents
                    or any(beneath(real, p) or beneath(p, real) for p in refused)):
                raise ValueError('agent client state refused: ' + str(source))
            granted.append((real, relative))
    return granted


def project_roots(config):
    """The reviewed project directories agents read today (project_read_roots: other projects a
    builder's tests read). '~' is the account's home; an absent root is skipped. Read only, agent
    profile only: they are never write roots, and the filter of grants_for still removes the store
    and every denied path beneath them."""
    home, roots = account_home(), []
    for value in config.get('project_read_roots', []):
        path = home / value[2:] if value.startswith('~/') else Path(value)
        if not path.is_absolute():
            raise ValueError('project read root must be absolute: ' + value)
        if path.exists():
            roots.append(path.resolve(strict=True))
    return roots


def credential_sources(config):
    """Every client's credential sources, as they resolve for this run: never readable in place."""
    sources = []
    for name in config.get('clients', {}):
        sources += [source for source, _ in client_files(config, name)['credentials']]
    return sources


def scratch_directory(scratch, parts):
    """A descriptor of the directory scratch/<parts>, each component opened (and created 0700 when
    absent) without following a link: a link anywhere on the path refuses, never redirects."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open(scratch, flags)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=directory)
            except FileExistsError:
                pass
            inner = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = inner
    except BaseException:
        os.close(directory)
        raise
    return directory


def overlapping_links(links, destinations):
    """Refuse a read link at, above or beneath a seed destination or another read link: every seed
    is written before any link exists, and no write or link of the launcher may pass through one."""
    for index, relative in enumerate(links):
        link = Path(relative)
        for other in [*destinations, *links[:index], *links[index + 1:]]:
            other = Path(other)
            if link == other or link in other.parents or other in link.parents:
                raise ValueError('agent client read link %s overlaps %s' % (relative, other))


def seed(scratch, source, relative, store, protected=None):
    """Copy one private state file into the scratch. Returns (resolved source, bytes copied), or
    None when the source is absent. A source in the store, or, for a credential that is written
    back, in a protected path, refuses the start. The destination is created component by component
    without following a link."""
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('invalid private state seed')
    if not source.is_file():
        return None
    real = source.resolve(strict=True)
    if beneath(real, store):
        raise ValueError('private state seed exposes the reuse store')
    if protected is not None and any(beneath(real, p) for p in protected):
        raise ValueError('credential source lies in a protected path: ' + str(real))
    data = real.read_bytes()
    parts = Path(relative).parts
    directory = scratch_directory(scratch, parts[:-1])
    try:
        descriptor = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(data)
    return real, data


def read_scratch_file(scratch, relative):
    """The bytes of scratch/relative, opened one component at a time without following any link:
    a link the confined tree planted anywhere on the path is refused, so only the file the launcher
    copied in can be read back. One link, a regular file, at most CREDENTIAL_LIMIT bytes."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open(scratch, flags | os.O_DIRECTORY)
    try:
        parts = Path(relative).parts
        for part in parts[:-1]:
            inner = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = inner
        descriptor = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > CREDENTIAL_LIMIT:
            raise ValueError('not a private regular file')
        data = b''
        while len(data) <= CREDENTIAL_LIMIT:
            chunk = os.read(descriptor, CREDENTIAL_LIMIT + 1 - len(data))
            if not chunk:
                return data
            data += chunk
        raise ValueError('larger than %d bytes' % CREDENTIAL_LIMIT)
    finally:
        os.close(descriptor)


class Superseded(Exception):
    """The source no longer holds the bytes copied in at the start: something else wrote it."""


def current_bytes(path):
    """The bytes of `path` now, without following a final link, or None when it is absent, not a
    regular file or larger than CREDENTIAL_LIMIT."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > CREDENTIAL_LIMIT:
            return None
        data = b''
        while len(data) <= CREDENTIAL_LIMIT:
            chunk = os.read(descriptor, CREDENTIAL_LIMIT + 1 - len(data))
            if not chunk:
                return data
            data += chunk
        return None
    finally:
        os.close(descriptor)


def replace_atomically(target, data, expected=None):
    """Replace `target` with `data`: a temporary file beside it, fsync, rename, fsync the directory.
    A reader sees the old file or the new one, never a partial write. The mode stays the source's
    owner bits (credentials are 0600). With `expected`, the target is read again just before the
    rename and is replaced only if it still holds exactly those bytes; otherwise Superseded is
    raised and the target is left as it is."""
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode) & 0o700 or 0o600
    except FileNotFoundError:
        mode = 0o600
    descriptor, temporary = tempfile.mkstemp(prefix='.' + target.name + '.', suffix='.veldo-tmp',
                                             dir=target.parent)
    try:
        try:
            os.fchmod(descriptor, mode)
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if expected is not None and current_bytes(target) != expected:
            raise Superseded('the source changed during the run')
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write_back(scratch, credentials):
    """After the run: each credential file the launcher copied in that the CLI changed (a token
    refresh) and that is still one JSON object replaces its source atomically, so a refresh during
    a run never logs the account out (VELDO-0210). Nothing else in the scratch is ever written back,
    and an unchanged, unreadable or invalid copy leaves the source as it is. So does a source that no
    longer holds the bytes copied in (a login or another run wrote it meanwhile): the newer file wins."""
    for real, relative, original in credentials:
        try:
            data = read_scratch_file(scratch, relative)
        except (OSError, ValueError) as error:
            print('agent sandbox: credential %s not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            continue
        if data == original:
            continue
        try:
            if not isinstance(json.loads(data.decode('utf-8')), dict):
                raise ValueError('not a JSON object')
        except Exception as error:  # ValueError, and RecursionError for a deeply nested document
            print('agent sandbox: credential %s changed but not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            continue
        try:
            replace_atomically(real, data, expected=original)
        except Superseded as error:
            print('agent sandbox: credential %s changed but not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            continue
        except OSError as error:
            print('agent sandbox: credential %s write-back to %s failed: %s' % (relative, real, error),
                  file=sys.stderr, flush=True)
            continue
        print('agent sandbox: credential %s refreshed during the run, written back to %s' % (relative, real),
              file=sys.stderr, flush=True)


SCRATCH_PREFIX = 'veldo-agent-'
STALE_SECONDS = 24 * 60 * 60
GRACE_SECONDS = 10
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


def remove_tree(path):
    """Remove a scratch tree the confined process may have shut (directories made unreadable or
    unwritable): every directory is opened up before it is entered, through descriptors and without
    following a link, then shutil.rmtree removes the tree without following a link either."""
    os.chmod(path, 0o700)
    for _, directories, _, descriptor in os.fwalk(path, follow_symlinks=False):
        for name in directories:
            try:
                # O_PATH opens a shut directory; O_NOFOLLOW makes sure it is one, not a link.
                inner = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=descriptor)
            except OSError:
                continue
            try:
                os.chmod('/proc/self/fd/%d' % inner, 0o700)
            except OSError:
                pass
            finally:
                os.close(inner)
    shutil.rmtree(path)


def remove_stale_scratch(parent):
    """Remove the scratch directories launchers killed outright left in `parent`: veldo-agent-*
    directories this uid owns, untouched for more than a day and held by no live launcher or agent
    (each launcher holds a shared lock on its own scratch until it removes it, and its confined
    command holds another on its own descriptor for as long as it runs). A link or any other kind of
    entry is never followed or removed."""
    try:
        entries = list(os.scandir(parent))
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith(SCRATCH_PREFIX):
            continue
        try:
            info = entry.stat(follow_symlinks=False)
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                    or time.time() - info.st_mtime < STALE_SECONDS):
                continue
            descriptor = os.open(entry.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except OSError:
            continue
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(descriptor)
            continue
        try:
            remove_tree(entry.path)
        except OSError as error:
            print('agent sandbox: stale scratch %s not removed: %s' % (entry.path, error),
                  file=sys.stderr, flush=True)
        finally:
            os.close(descriptor)


class Interrupted(Exception):
    pass


class Stop:
    """TERM, INT and HUP while a launch runs. Before the confined child exists, a signal ends the
    launch (the scratch is still removed). After, it is forwarded to the child's process group, and a
    group still alive GRACE_SECONDS later is killed; the launcher then writes back credentials,
    removes its scratch and exits 128 plus the signal number. A signal the launcher inherited as
    ignored stays ignored, for it and for the child."""

    def __init__(self):
        self.pid = self.number = None
        self.reaped = self.closing = False
        self.previous = {}

    def __enter__(self):
        threading = __import__('threading')
        if threading.current_thread() is threading.main_thread():
            for number in STOP_SIGNALS:
                if signal.getsignal(number) != signal.SIG_IGN:
                    self.previous[number] = signal.signal(number, self.stop)
            self.previous[signal.SIGALRM] = signal.signal(signal.SIGALRM, self.kill)
        return self

    def __exit__(self, *_):
        if self.previous:
            signal.alarm(0)
        for number, handler in self.previous.items():
            signal.signal(number, handler)

    def child(self, pid):
        self.pid = pid

    def in_child(self):
        """In the forked child, before anything else: the default action for what this caught."""
        for number in self.previous:
            signal.signal(number, signal.SIG_DFL)

    def signal_group(self, number):
        if self.reaped:
            return  # the child is reaped: its pid may name another process now
        try:
            os.killpg(self.pid, number)
        except ProcessLookupError:
            try:
                os.kill(self.pid, number)  # not yet in its own session
            except ProcessLookupError:
                pass

    def stop(self, number, _frame):
        if self.number is not None:
            # Asked again: stop the group now. Cleanup is already under way and is not interrupted.
            if self.pid is not None:
                self.signal_group(signal.SIGKILL)
            return
        self.number = number
        if self.pid is None and not self.closing:
            raise Interrupted(number)
        if self.pid is None:
            return
        self.signal_group(number)
        signal.alarm(GRACE_SECONDS)

    def kill(self, _number, _frame):
        if self.pid is not None:
            self.signal_group(signal.SIGKILL)


def launch(config_path, worktree, command, profile="agent", client=None):
    """Run `command` confined. The private scratch is created in the temporary directory, held
    with a shared lock and removed when the launcher returns, raises or is stopped by TERM, INT or
    HUP; one a launcher killed outright left behind is removed by the next start once it is a day
    old and no process holds its lock (VELDO-0210)."""
    parent = Path(tempfile.gettempdir())
    remove_stale_scratch(parent)
    scratch = lock = None
    # The handlers stay installed until the scratch is gone, so a signal cannot cut the removal short.
    with Stop() as stop:
        try:
            scratch = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX, dir=parent))
            lock = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            code = prepared_launch(config_path, worktree, command, profile, scratch, client, stop)
        except Interrupted:
            code = None
        finally:
            stop.closing = True
            if scratch is not None:
                try:
                    remove_tree(scratch)
                except OSError as error:
                    print('agent sandbox: scratch %s not removed: %s' % (scratch, error),
                          file=sys.stderr, flush=True)
            if lock is not None:
                os.close(lock)
    return 128 + stop.number if stop.number else code


def prepared_launch(config_path, worktree, command, profile, scratch, client=None, stop=None):
    policy = policy_module()
    config_path, config = policy.configuration(config_path)
    authority = Path(__file__).resolve().parents[1]
    worktree = Path(worktree).resolve(strict=True)
    store = Path(config['store'])
    store.mkdir(mode=0o700, parents=True, exist_ok=True)
    policy.private(store, directory=True)
    if profile == 'gate':
        if client is not None:
            raise ValueError('the gate profile takes no agent client')
        config = dict(config, write_roots=['{scratch}'], seed_files={})
    # Credentials are copied in, never read in place: every client's sources are denied for the run.
    config = dict(config, deny_read=[*config.get('deny_read', []), *map(str, credential_sources(config))])
    files = client_files(config, client) if client is not None else {}
    links = [(source.resolve(strict=True), relative) for source, relative in files.get('read_links', [])
             if source.exists()]
    extra = [*project_roots(config), *(target for target, _ in links)] if profile == 'agent' else []
    grants, protected = grants_for(config, authority, worktree, scratch, config_path, extra)
    if profile == 'agent':
        grants += resolver_grants()

    protected += [config_path, Path(policy.__file__).resolve()]
    if profile == "agent" and any(beneath(p, worktree) for p in protected):
        raise ValueError('launcher, configuration and authority must be outside the worktree')
    store = Path(config['store']).resolve()
    overlapping_links([relative for kind in ('read_links', 'state_dirs', 'state_files')
                       for _, relative in files.get(kind, [])],
                      [*config.get('seed_files', {}).values(),
                       *(relative for kind in ('seed_files', 'credentials') for _, relative in files.get(kind, []))])
    # Every file is copied in before any link exists.
    for source, relative in config.get('seed_files', {}).items():
        seed(scratch, Path(source).expanduser(), relative, store)
    for source, relative in files.get('seed_files', []):
        seed(scratch, source, relative, store)
    credentials = []
    for source, relative in files.get('credentials', []):
        copied = seed(scratch, source, relative, store, protected)
        if copied is not None:
            real, data = copied
            credentials.append((real, relative, data))
    # The client's persistent state: read and write where it is, linked where the CLI looks for it.
    state = state_grants(files, [store, worktree, authority, *protected, *credential_sources(config),
                                 *(Path(p).expanduser().resolve() for p in config.get('deny_read', []))])
    grants += [(real, READ | WRITE) for real, _ in state]
    for name in ('.codex', '.claude', 'tmp'):
        os.close(scratch_directory(scratch, [name]))
    # The client's installed plugins, marketplaces and skills (read only) and its persistent state
    # (read and write), where they are, linked where the CLI looks for them under its private state
    # directory.
    for target, relative in [*links, *state]:
        parts = Path(relative).parts
        directory = scratch_directory(scratch, parts[:-1])
        try:
            os.symlink(target, parts[-1], dir_fd=directory)
        finally:
            os.close(directory)
    env = dict(os.environ, HOME=str(scratch), CODEX_HOME=str(scratch / '.codex'),
               CLAUDE_CONFIG_DIR=str(scratch / '.claude'), TMPDIR=str(scratch / 'tmp'),
               VELDO_AGENT_CONFIG=str(config_path),
               XDG_CACHE_HOME=str(scratch / '.cache'), XDG_CONFIG_HOME=str(scratch / '.config'),
               XDG_STATE_HOME=str(scratch / '.local/state'), XDG_DATA_HOME=str(scratch / '.local/share'))
    # VELDO_EXPECTED_GIT_COMMON names the trusted repository to this launcher only. Handed on, it
    # would make a gate the confined command runs for another repository (a freshly scaffolded
    # one, a fixture) check that repository against this one's common directory.
    for name in ('PYTHONPATH', 'PYTHONHOME', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
                 'BASH_ENV', 'ENV', 'DBUS_SESSION_BUS_ADDRESS', 'SSH_AUTH_SOCK',
                 'VELDO_EXPECTED_GIT_COMMON'):
        env.pop(name, None)
    # TERM, INT and HUP stay blocked from before the fork until the parent has registered its child:
    # a stop in between would otherwise end the launch, remove the scratch and leave the child running.
    launcher = os.getpid()
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        if profile == 'gate':
            # Gate commands run this repository's own suites, which serve and dial Unix sockets and
            # drive terminals. The parent brokers those inside the domain's writable roots (scratch).
            roots = [p for p, access in grants if access & WRITE == WRITE and p.is_dir()]
            pid, side = fork_gate_domain(roots)
        else:
            pid, side = os.fork(), None
    except BaseException:
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        raise
    if pid:
        status = None
        try:
            if stop is not None:
                stop.child(pid)
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)  # a stop that came meanwhile is handled now
            _, status = os.waitpid(pid, 0)
        finally:
            if stop is not None and status is not None:
                stop.reaped = True
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if status is None:
                # Interrupted before the child was reaped (it may not have its own session yet).
                try:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass
            if side is not None:
                side.close()
            # The confined group is gone: a refreshed credential goes back to its account. Nothing
            # the write-back meets replaces the run's own exit status.
            try:
                write_back(scratch, credentials)
            except Exception as error:
                print('agent sandbox: credential write-back stopped: %r' % error, file=sys.stderr, flush=True)
        return os.waitstatus_to_exitcode(status) if os.WIFEXITED(status) else 1
    # Only this child executes candidate/agent code. The parent only waits (and, for the gate,
    # brokers) and removes its own scratch using symlink-safe stdlib cleanup.
    try:
        if stop is not None:
            stop.in_child()
        # A launcher killed outright takes its child with it (PR_SET_PDEATHSIG, kept across exec), so
        # no agent runs on unsupervised; a launcher already gone refuses the start.
        if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid() != launcher:
            raise RuntimeError('the launcher is gone')
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        os.setsid()
        # The confined command holds its own shared lock on the scratch for as long as it runs (and
        # every descendant that keeps the descriptor), so no sweep removes a scratch still in use.
        held = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fcntl.flock(held, fcntl.LOCK_SH | fcntl.LOCK_NB)
        os.set_inheritable(held, True)
        keep = [held, *(side.keep() if side else ())]
        close_descriptors(protected, keep=keep)
        mode = landlock(grants, profile, broker=side)
        env.pop(BROKERED, None)
        if mode != 'strict':
            env[BROKERED] = '1'
        os.chdir(worktree)
        os.execvpe(command[0], command, env)
    except BaseException as error:
        print('agent sandbox refused to start: ' + str(error), file=sys.stderr, flush=True)
        os._exit(2)


def repository_main(action, argv):
    parser = argparse.ArgumentParser(prog='agent_sandbox.py ' + action,
                                     description=(prepare if action == 'prepare' else integrate).__doc__)
    parser.add_argument('--shared', required=True, help='the shared (authority) Git common directory')
    parser.add_argument('--private', required=True, help="the agent's own bare repository")
    parser.add_argument('--agent', required=True)
    if action == 'prepare':
        parser.add_argument('--worktree', required=True)
        parser.add_argument('--branch', required=True, help='name under refs/heads/agent/<agent>/')
        parser.add_argument('--start', required=True, help='shared revision the branch starts at')
    args = parser.parse_args(argv)
    try:
        if action == 'prepare':
            print(prepare(args.shared, args.private, args.worktree, args.agent, args.branch, args.start))
        else:
            integrate(args.shared, args.private, args.agent)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print('agent repository refused: ' + str(error), file=sys.stderr)
        return 2


def main():
    if sys.argv[1:2] in (['prepare'], ['integrate']):
        return repository_main(sys.argv[1], sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--profile', choices=('agent', 'gate'), default='agent')
    parser.add_argument('--client', help='the agent CLI whose files the run receives (a key of '
                        'clients in the configuration: claude, codex); none without it')
    parser.add_argument('--worktree', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        if not command:
            raise ValueError('an agent command is required after --')
        return launch(args.config, args.worktree, command, args.profile, args.client)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print('agent sandbox refused to start: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
