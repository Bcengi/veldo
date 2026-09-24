#!/usr/bin/env python3
"""Keep protected key directories out of every worker tool's reach (VELDO-0067 AC3, PLAN-0019 W52).

WHY THIS EXISTS. VELDO-0027 keeps signing keys out of reach by location and interface: the private
key lives in the authority's key directory outside every repository, only the installed signer's
fixed configuration names it, a request that names a key path is refused, and nothing the signer
returns carries key bytes. That stops a worker from ASKING for the key. It does not stop a worker
tool from opening the file, because workers run under the owner's account, and the owner ruled out
a second operating-system account (VELDO-0027, Telegram 28578/28580). So nothing protected a key
from a worker process. This module is the narrowest seam that does: a trusted wrapper that confines
the worker it starts, with the Linux kernel's Landlock sandbox, so that no process of that worker
can read a file beneath a protected directory, and then becomes the worker by exec.

    python3 control_keys_custody.py confine <protected-dir> [<protected-dir> ...] -- <worker argv>

It is used exactly as control_launch's own `exec` wrapper is: an adapter whose workers must not reach
the keys has its configured argv start with this wrapper (`confined()` builds that argv). Choosing the
adapters and the installed key location is installation (W32), not this module.

WHAT THE WORKER LOSES, AND ONLY THAT. The sandbox handles two access rights and no others: reading
a file's content, and linking or renaming a file into another directory. Every file and directory
that exists when the worker starts stays readable, writable and executable as before, except
beneath the protected directories, which the worker can list but not read, link out of or move
away. Landlock grants by directory hierarchy and cannot deny a single path, so the grant is built
from the protected directories' ancestor chains: every entry beside the chain at every level is
granted as a whole hierarchy, and the ancestors themselves are not. Two consequences follow and are
stated rather than hidden: a file the worker creates directly in an ancestor directory after it
starts is not readable by that worker, and a file moved directly into or out of an ancestor
directory needs a copy. The protected directory therefore belongs where workers never write
directly into its ancestors (outside the home and temporary directories); that placement is W32's.
Landlock also requires no_new_privs, so a confined worker cannot gain privilege through a setuid
program (which would otherwise read anything).

WHAT IT IS NOT. Not the worker containment group of VELDO-0040, and not a defense against a worker
reaching an unconfined process of the owner's account that reads for it (the user's service
manager, a login shell's startup files, ssh to this host). Writing or deleting the protected files
is not restricted: the threat model is reading them. It refuses to start the worker at all when the
kernel does not provide Landlock ABI 2 or later (for example on macOS, where workers do not share
the authority's key directory): a worker is never started unconfined by this wrapper. Standard
library only (ctypes for the three Landlock system calls).
"""
import ctypes
import os
from pathlib import Path
import platform
import sys

# Landlock system calls: the generic syscall table numbers, the same on x86_64 and aarch64.
SYSCALLS = {'x86_64': (444, 445, 446), 'aarch64': (444, 445, 446)}
CREATE_RULESET_VERSION = 1
RULE_PATH_BENEATH = 1
READ_FILE = 1 << 2
REFER = 1 << 13
# The rights the sandbox handles: reading content, and reparenting (a link or rename across
# directories), which Landlock ABI 2 treats as handled by every ruleset anyway.
HANDLED = READ_FILE | REFER
# The rights a rule on a non-directory may carry (a file, a device, a socket).
FILE_RIGHTS = READ_FILE
MINIMUM_ABI = 2
PR_SET_NO_NEW_PRIVS = 38
O_PATH = getattr(os, 'O_PATH', 0o10000000)
EXIT_REFUSED = 70
REFUSALS = {'custody-unavailable': 'unavailable_service', 'invalid-protected-directory': 'invalid_input',
            'usage': 'invalid_input'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class _RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def _libc():
    if sys.platform != 'linux' or platform.machine() not in SYSCALLS:
        raise Refused('custody-unavailable', 'Landlock is a Linux kernel sandbox; this host has none')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc, SYSCALLS[platform.machine()]


def abi():
    """The kernel's Landlock ABI version, or 0 when it has none (not built, or disabled at boot)."""
    try:
        libc, (create, _, _) = _libc()
    except Refused:
        return 0
    version = libc.syscall(ctypes.c_long(create), None, ctypes.c_size_t(0), ctypes.c_uint32(CREATE_RULESET_VERSION))
    return version if version > 0 else 0


def protected_paths(directories):
    """The protected directories as resolved absolute paths; each must exist and be a directory."""
    resolved = []
    for directory in directories:
        path = Path(directory).resolve()
        if not path.is_dir() or path == Path(path.anchor):
            raise Refused('invalid-protected-directory', 'a protected directory exists and is not the root')
        resolved.append(path)
    if not resolved:
        raise Refused('invalid-protected-directory', 'at least one protected directory is named')
    return resolved


def grants(directories):
    """[(path, is_directory)] to grant: every entry beside the protected directories' ancestor
    chains, at every level of every chain. A path is on a chain when it is a protected directory or
    one of its ancestors; nothing on a chain is granted, so nothing beneath a protected directory
    is covered by any grant. Symbolic links are not granted: their targets are granted, or not, at
    their own place in the tree."""
    protected = protected_paths(directories)
    chain = set(protected)
    for path in protected:
        chain.update(path.parents)
    found = []
    for ancestor in sorted(p for p in chain if not any(p == q or p.is_relative_to(q) for q in protected)):
        try:
            entries = list(os.scandir(ancestor))
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if path in chain:
                continue
            try:
                if entry.is_symlink():
                    continue
                found.append((path, entry.is_dir(follow_symlinks=False)))
            except OSError:
                continue
    return sorted(set(found))


def confine(directories):
    """Confine this process and everything it starts: no file beneath `directories` can be read.
    Irrevocable. Refuses, confining nothing, when the kernel's Landlock ABI is below 2."""
    libc, (create, add_rule, restrict_self) = _libc()
    version = abi()
    if version < MINIMUM_ABI:
        raise Refused('custody-unavailable', 'Landlock ABI %d is below %d' % (version, MINIMUM_ABI))
    rules = grants(directories)
    attr = _RulesetAttr(HANDLED)
    ruleset = libc.syscall(ctypes.c_long(create), ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)),
                           ctypes.c_uint32(0))
    if ruleset < 0:
        raise Refused('custody-unavailable', 'landlock_create_ruleset failed (errno %d)' % ctypes.get_errno())
    try:
        for path, is_directory in rules:
            try:
                fd = os.open(path, O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
            except OSError:
                continue
            try:
                rule = _PathBeneathAttr(HANDLED if is_directory else FILE_RIGHTS, fd)
                if libc.syscall(ctypes.c_long(add_rule), ctypes.c_int(ruleset), ctypes.c_int(RULE_PATH_BENEATH),
                                ctypes.byref(rule), ctypes.c_uint32(0)) < 0:
                    raise Refused('custody-unavailable', 'landlock_add_rule failed (errno %d)' % ctypes.get_errno())
            finally:
                os.close(fd)
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise Refused('custody-unavailable', 'no_new_privs could not be set (errno %d)' % ctypes.get_errno())
        if libc.syscall(ctypes.c_long(restrict_self), ctypes.c_int(ruleset), ctypes.c_uint32(0)) < 0:
            raise Refused('custody-unavailable', 'landlock_restrict_self failed (errno %d)' % ctypes.get_errno())
    finally:
        os.close(ruleset)
    return len(rules)


def confined(argv, directories, python=None):
    """The argv an adapter configures so its worker starts confined: this wrapper, then the worker."""
    return [python or sys.executable, '-B', str(Path(__file__).resolve()), 'confine',
            *[str(Path(d).resolve()) for d in directories], '--', *argv]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(argv) < 4 or argv[0] != 'confine' or '--' not in argv[2:] or argv.index('--') == len(argv) - 1:
            raise Refused('usage', 'confine <protected-dir> [...] -- <worker argv>')
        split = argv.index('--')
        confine(argv[1:split])
        worker = argv[split + 1:]
    except Refused as error:
        # Refused names only: no path, no argument, nothing the worker would have seen.
        sys.stderr.write('custody refused: %s\n' % error.code)
        return EXIT_REFUSED
    os.execvp(worker[0], worker)


if __name__ == '__main__':
    sys.exit(main())
