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
import importlib.util
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import subprocess
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


def landlock(grants, profile="agent"):
    spec = importlib.util.spec_from_file_location('mutation_sandbox',
                                                  Path(__file__).with_name('mutation_sandbox.py'))
    boundary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boundary)
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
    if profile == 'worker':
        boundary.network_filter(libc)
    ipc_filter(libc)


def ipc_filter(libc):
    """Block pathname Unix service escapes too (Landlock ABI 6 scopes abstract ones).

    Do not expose inherited sockets or io_uring as alternate syscall dispatch.
    Agent TCP/TLS is allowed; only workers install the full network filter.
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


def close_descriptors(protected, keep=()):
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
        if int(name) >= 3 and int(name) not in keep:
            try:
                os.close(int(name))
            except OSError:
                pass


def launch(config_path, worktree, command, profile="agent"):
    with tempfile.TemporaryDirectory(prefix='veldo-agent-') as temporary:
        return prepared_launch(config_path, worktree, command, profile, Path(temporary))


def prepared_launch(config_path, worktree, command, profile, scratch):
    policy = policy_module()
    config_path, config = policy.configuration(config_path)
    authority = Path(__file__).resolve().parents[1]
    worktree = Path(worktree).resolve(strict=True)
    store = Path(config['store'])
    store.mkdir(mode=0o700, parents=True, exist_ok=True)
    policy.private(store, directory=True)
    if profile == 'gate':
        config = dict(config, write_roots=['{scratch}'], seed_files={})
    grants, protected = grants_for(config, authority, worktree, scratch)

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
    pid = os.fork()
    if pid:
        try:
            _, status = os.waitpid(pid, 0)
        finally:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return os.waitstatus_to_exitcode(status) if os.WIFEXITED(status) else 1
    # Only this child executes candidate/agent code. The parent only waits and
    # removes its own scratch using symlink-safe stdlib cleanup.
    try:
        os.setsid()
        close_descriptors(protected)
        landlock(grants)
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
    parser.add_argument('--worktree', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        if not command:
            raise ValueError('an agent command is required after --')
        return launch(args.config, args.worktree, command, args.profile)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print('agent sandbox refused to start: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
