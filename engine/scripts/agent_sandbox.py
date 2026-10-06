#!/usr/bin/env python3
"""Start one implementing process tree in an inherited, unprivileged domain.

Invoke with python3 -I -S from a reviewed authority checkout, never the candidate.
No daemon, alternate uid, root helper, or unsandboxed fallback is used.
"""
import argparse
import ctypes
import errno
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import stat
import sys
import tempfile

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


def landlock(grants):
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

    # Handle device ioctl too; only ordinary files and selected safe devices get grants.
    rules = Ruleset(READ | WRITE | (1 << 15), 0, 3)
    fd = call(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
    try:
        for path, access in grants:
            if not path.is_dir():
                access &= FILE
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
    spec = importlib.util.spec_from_file_location('mutation_sandbox',
                                                  Path(__file__).with_name('mutation_sandbox.py'))
    boundary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boundary)
    boundary.network_filter(libc)
    ipc_filter(libc)


def ipc_filter(libc):
    """Block pathname Unix service escapes too (Landlock ABI 6 scopes abstract ones).

    Do not expose inherited sockets or io_uring as alternate syscall dispatch.
    The common network filter also denies TCP/TLS and inherited socket dispatch.
    """
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                    ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]

    deny = 0x50000 | errno.EPERM
    code = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, deny)]
    # socket(AF_UNIX, ...) refused; socketpair is local to this process tree.
    code += [(0x15, 0, 3, 41), (0x20, 0, 0, 16), (0x15, 0, 1, 1), (0x06, 0, 0, deny),
             (0x20, 0, 0, 0)]
    # Standard descriptors can be terminals opened before confinement. Do not
    # let a child inject input into the orchestrator's terminal through them.
    code += [(0x15, 0, 5, 16), (0x20, 0, 0, 24), (0x15, 0, 1, 0x5412),
             (0x06, 0, 0, deny), (0x15, 0, 1, 0x541c), (0x06, 0, 0, deny),
             (0x20, 0, 0, 0)]
    # Close IPC, namespace, mount, ptrace and asynchronous syscall alternatives.
    # chmod is intentionally available for normal build/Git use: it cannot grant
    # file-content access denied by Landlock. Metadata secrecy is not claimed.
    for number in (101, 133, 165, 166, 246, 272, 298,
                   303, 304, 308, 310, 311, 313, 321, 323, 425, 426, 427, 428, 429,
                   430, 431, 432, 433, 438, 442, 452):
        code += [(0x15, 0, 1, number), (0x06, 0, 0, deny)]
    code += [(0x06, 0, 0, 0x7fff0000)]
    filters = (Filter * len(code))(*(Filter(*item) for item in code))
    program = Program(len(code), filters)
    if libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), 'agent sandbox IPC filter unavailable')


def git_grants(worktree, protected):
    """Grant linked-worktree persistence without writing common config or hooks."""
    marker = worktree / '.git'
    if not marker.is_file():
        return []
    if marker.is_symlink():
        raise ValueError('worktree Git marker must not be a symlink')
    line = marker.read_text().strip()
    if not line.startswith('gitdir: '):
        raise ValueError('invalid worktree Git marker')
    gitdir = (worktree / line[8:]).resolve(strict=True)
    common = (gitdir / (gitdir / 'commondir').read_text().strip()).resolve(strict=True)
    if (gitdir.parent != common / 'worktrees'
            or Path((gitdir / 'gitdir').read_text().strip()).resolve() != marker):
        raise ValueError('Git directory does not belong to this worktree')
    head = (gitdir / 'HEAD').read_text().strip()
    if not head.startswith('ref: refs/heads/'):
        raise ValueError('agent worktree needs a branch')
    reference = head[5:]
    if any(part in ('', '.', '..') for part in reference.split('/')) or '\n' in reference:
        raise ValueError('invalid worktree branch')
    # Git locks require creating a sibling .lock and renaming it over the branch.
    # Landlock grants directories, so sibling loose refs in these two directories
    # share this write grant. Use a dedicated branch namespace to minimize it.
    grants = [(gitdir, READ | WRITE), (common / 'objects', READ | WRITE)]
    for relative in (reference, 'logs/' + reference):
        target = common / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        grants.append((target.parent, READ | WRITE))
    for path, _ in grants:
        if (path.resolve() != path or path.is_symlink()
                or any(beneath(path, p) or beneath(p, path) for p in protected)):
            raise ValueError('Git write grant overlaps protected path: ' + str(path))
    return grants


def grants_for(config, authority, worktree, scratch):
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

    for path in config['read_roots']:
        read(expand(path))
    grants += [(p, READ | WRITE) for p in writes]
    # Git persistence is the sole exception beneath the authority's .git.
    # Its working files, config, hooks and other worktree gitdirs stay read-only.
    if '{worktree}' in config['write_roots']:
        grants += git_grants(worktree, [store, *(p for p in protected if p != authority)])
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)),
               (Path('/dev/urandom'), 1 << 2), (Path('/dev/random'), 1 << 2)]
    return grants, [store, *protected]


def close_descriptors(protected):
    for fd in (0, 1, 2):
        try:
            info = os.fstat(fd)
        except OSError:
            continue
        if stat.S_ISSOCK(info.st_mode):
            raise ValueError('standard descriptors may not be service sockets')
        if stat.S_ISREG(info.st_mode):
            target = Path(os.readlink('/proc/self/fd/' + str(fd))).resolve()
            if any(beneath(target, p) for p in protected):
                raise ValueError('standard descriptor exposes a protected path')
    # Close the actual open set, including descriptors above a lowered rlimit.
    for name in os.listdir('/proc/self/fd'):
        if int(name) >= 3:
            try:
                os.close(int(name))
            except OSError:
                pass


def launch(config_path, worktree, command, profile="agent"):
    policy = policy_module()
    config_path, config = policy.configuration(config_path)
    authority = Path(__file__).resolve().parents[1]
    worktree = Path(worktree).resolve(strict=True)
    store = Path(config['store'])
    store.mkdir(mode=0o700, parents=True, exist_ok=True)
    policy.private(store, directory=True)
    scratch = Path(tempfile.mkdtemp(prefix='veldo-agent-'))
    # Scratch persists for this process tree; the owner removes it after the run.
    # There is no unconfined supervisor waiting on agent-controlled cleanup code.
    if profile == 'gate':
        config = dict(config, write_roots=['{scratch}'])
    grants, protected = grants_for(config, authority, worktree, scratch)
    grants += [(worktree, READ), (authority, READ), (scratch, READ | WRITE)]
    protected += [config_path, Path(policy.__file__).resolve()]
    if profile == "agent" and any(beneath(p, worktree) for p in protected):
        raise ValueError('launcher, configuration and authority must be outside the worktree')
    for source, relative in config.get('seed_files', {}).items():
        destination = scratch / relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('invalid private state seed')
        source = Path(source).expanduser()
        if source.is_file():
            if beneath(source.resolve(strict=True), store):
                raise ValueError('private state seed exposes the reuse store')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            destination.chmod(0o600)
    for name in ('.codex', '.claude', 'tmp'):
        (scratch / name).mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(scratch), CODEX_HOME=str(scratch / '.codex'),
               CLAUDE_CONFIG_DIR=str(scratch / '.claude'), TMPDIR=str(scratch / 'tmp'),
               VELDO_AGENT_CONFIG=str(config_path),
               XDG_CACHE_HOME=str(scratch / '.cache'), XDG_CONFIG_HOME=str(scratch / '.config'),
               XDG_STATE_HOME=str(scratch / '.local/state'), XDG_DATA_HOME=str(scratch / '.local/share'))
    for name in ('PYTHONPATH', 'PYTHONHOME', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
                 'BASH_ENV', 'ENV', 'DBUS_SESSION_BUS_ADDRESS', 'SSH_AUTH_SOCK'):
        env.pop(name, None)
    close_descriptors(protected)
    landlock(grants)
    print('agent sandbox: private state ' + str(scratch), file=sys.stderr, flush=True)
    os.chdir(worktree)
    os.execvpe(command[0], command, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--profile', choices=('agent', 'gate'), default='agent')
    parser.add_argument('--worktree', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        if not command:
            raise ValueError('an agent command is required after --')
        launch(args.config, args.worktree, command, args.profile)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print('agent sandbox refused to start: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
