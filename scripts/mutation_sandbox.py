"""Linux Landlock filesystem boundary inherited by every mutation descendant.

The coordinator is trusted. Workers can read the frozen tree and runtime, and
write only their private scratch directory. No /proc or caller home is exposed.
Unsupported kernels fail closed; there is no unsandboxed fallback.
"""
import ctypes
import os
from pathlib import Path

RUNTIME = ('/usr', '/lib', '/lib64', '/etc')
READ = (1 << 0) | (1 << 2) | (1 << 3)
WRITE = sum(1 << n for n in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))


def restrict(root, scratch, runtime=RUNTIME, *, legacy=True):
    libc = ctypes.CDLL(None, use_errno=True)
    def call(number, *args):
        result = libc.syscall(number, *args)
        if result < 0:
            raise OSError(ctypes.get_errno(), 'mutation sandbox unavailable')
        return result
    abi = call(444, 0, 0, 1)
    if abi < 3:
        raise RuntimeError('mutation sandbox needs Landlock ABI 3')
    class Ruleset(ctypes.Structure):
        _fields_ = [('access', ctypes.c_uint64)]
    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('access', ctypes.c_uint64), ('parent', ctypes.c_int32)]
    rules = Ruleset(READ | WRITE)
    fd = call(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
    try:
        compatibility = [('/proc/mounts', READ), ('/sys', READ),
                         ('/dev/shm', READ | WRITE),
                         ('/run/user/' + str(os.getuid()), READ | WRITE)] if legacy else []
        for path, access in [(root, READ), (scratch, READ | WRITE), *compatibility,
                             *((p, READ) for p in runtime),
                             ('/dev/null', (1 << 1) | (1 << 2)),
                             ('/dev/urandom', 1 << 2)]:
            path = Path(path)
            if not path.exists():
                continue
            if not path.is_dir():
                access &= (1 << 0) | (1 << 1) | (1 << 2) | (1 << 14)
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(access, parent)
                call(445, fd, 1, ctypes.byref(rule), 0)
            finally:
                os.close(parent)
        if libc.prctl(38, 1, 0, 0, 0):
            raise OSError(ctypes.get_errno(), 'cannot set no_new_privs')
        call(446, fd, 0)
    finally:
        os.close(fd)
