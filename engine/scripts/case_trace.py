"""Coordinator-owned file and metadata evidence, including unsuccessful probes."""
import ast
import os
from pathlib import Path
import re

QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')
CALL = re.compile(r'\b([a-zA-Z0-9_]+)\((.*)\)\s+=\s+(.*)')
PATH_READS = {'open', 'openat', 'openat2', 'stat', 'lstat', 'statx', 'newfstatat',
              'access', 'faccessat', 'faccessat2', 'readlink', 'readlinkat',
              'statfs', 'getxattr', 'lgetxattr', 'listxattr', 'llistxattr',
              'execve', 'execveat', 'chdir', 'symlink', 'symlinkat'}
FD_READS = {'fstat', 'fstatfs', 'getdents', 'getdents64', 'fchdir'}
# -q, not -qq: strace prints each traced thread's own end, so a call that never resumed is known to
# belong to a thread that ended. Only an exit, or a call strace could not name, may end that way.
ENDED = re.compile(r'^\d+ \+\+\+ (?:exited with -?\d+|killed by SIG[A-Z0-9]+(?: \(core dumped\))?) \+\+\+$')
STATUS = re.compile(r'^\d+ \+\+\+ .* \+\+\+$')
ENDING_CALLS = {'exit', 'exit_group', '???'}
RESUMED = re.compile(r'^\d+ <\.\.\. (?:[a-zA-Z0-9_]+|\?\?\?) resumed>')
UNFINISHED = ' <unfinished ...>'
# Calls whose quoted arguments are file or socket data, never names: their buffers may hold any text,
# including strace's own markers, and -s may truncate them (VELDO-0367 N1).
DATA_CALLS = {'read', 'pread64', 'readv', 'preadv', 'preadv2', 'write', 'pwrite64', 'writev',
              'pwritev', 'pwritev2', 'recvfrom', 'recvmsg', 'recvmmsg', 'sendto', 'sendmsg', 'sendmmsg'}
# A network call an ended thread was still waiting in (a server thread in accept, a reader in recv)
# reads no file: the file-read evidence is whole. It is yielded with result '?', so the non-file
# classifier still judges it: a pending connect or send is an attempt, a pending accept on a socket
# the traced tree did not listen on is an input (VELDO-0217 F2).
NETWORK_WAITS = {'accept', 'accept4', 'recvfrom', 'recvmsg', 'recvmmsg',
                 'connect', 'sendto', 'sendmsg', 'sendmmsg'}
PENDING_CALL = re.compile(r'^\d+ ([a-zA-Z0-9_]+|\?\?\?)\(')


class UndeclaredInput(ValueError):
    """A trace found an input outside the declaration: rerun the case fresh."""


class IncompleteTrace(ValueError):
    """A traced thread ended inside a call that may have read a file: lost evidence. The gate keeps
    such a run's case from publishing rather than failing its stage (VELDO-0217 F6)."""


def command(trace, argv):
    # file includes metadata probes, even failed ones. getdents is not in file. network carries
    # every bind, connect and send, the evidence of a non-file input (VELDO-0217 AC4).
    return ['/usr/bin/strace', '-f', '-q', '-yy', '-v', '-s', '65535',
            '-e', 'trace=all',
            '-o', str(trace), *argv]


def full_command(argv, trace):
    """Check the tracer prefix actually launched by the authority, before its command."""
    if not isinstance(argv, (list, tuple)):
        return False
    prefix = command(trace, [])
    return list(argv[:len(prefix)]) == prefix and len(argv) > len(prefix)


def compatible(authority, suites):
    """A second tracer or a worker-tree launch must retain its existing boundary.

    Use the authority's unchanged leg declarations; unknown requirements do not
    license an observer that can change the workload's behavior.
    """
    if not suites:
        return True
    import json
    try:
        entries = json.loads((Path(authority) / 'scripts/gate_unconfined.json').read_text())['suites']
        names = {name.split(':', 1)[0].removesuffix('.py') for name in suites}
        relevant = [entry for entry in entries if entry['suite'] in names]
        return len(relevant) == len(names) and not any(
            word in entry['reason'].lower() for entry in relevant
            for word in ('ptrace', 'strace', 'namespace', 'confinement'))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def syscall_lines(trace):
    pending = {}
    for line in Path(trace).read_text(errors='replace').splitlines():
        pid = line.split(None, 1)[0]
        if ENDED.match(line):
            # A thread torn down by its group's exit never resumes its last call. Accept that
            # call only when it is an exit or a network wait; any other call of an ended thread is
            # lost evidence.
            call = pending.pop(pid, None)
            name = PENDING_CALL.match(call) if call is not None else None
            if call is not None and name is not None and name[1] in NETWORK_WAITS:
                yield call.rstrip().rstrip(',') + ') = ? <thread ended>'
                continue
            if call is not None and (name is None or name[1] not in ENDING_CALLS):
                raise IncompleteTrace('incomplete file-read trace')
            continue
        if STATUS.match(line):
            continue
        # Anchor both markers: a read or write buffer may hold either text (VELDO-0367 N1).
        resumed = RESUMED.match(line)
        if resumed and line[resumed.end():].startswith(' <unfinished ...>'):
            # strace's teardown of a pending call ("<... accept4 resumed> <unfinished ...>) = ?"):
            # the call never completed; its thread's end judges the call it started.
            if pid not in pending:
                raise ValueError('unmatched resumed syscall')
            continue
        if not resumed and line.endswith(UNFINISHED):
            pending[pid] = line[:-len(UNFINISHED)]
            continue
        if resumed:
            if pid not in pending:
                raise ValueError('unmatched resumed syscall')
            line = pending.pop(pid) + line[resumed.end():]
        yield line
    if pending:
        raise IncompleteTrace('incomplete file-read trace')


def accesses(trace, *, cwd=None, after_confinement=False):
    """Yield (absolute path, content/metadata/listing, success) for every probe.

    FD annotations resolve *at calls and getdents. Track cwd for older path syscalls
    and inherit it across fork/clone. Undecodable evidence is a failure, never a skip.
    """
    initial = Path(cwd or Path.cwd()).absolute()
    directories = {}
    confined = not after_confinement
    for line in syscall_lines(trace):
        match = CALL.search(line)
        if not match:
            continue
        pid = line.split(None, 1)[0]
        call, arguments, result = match.groups()
        if not confined:
            # Only authority bootstrap runs before this boundary. Never skip
            # candidate accesses or a later, candidate-installed ruleset.
            if call == 'landlock_restrict_self' and result.strip() == '0':
                confined = True
            continue
        current = directories.setdefault(pid, initial)
        success = not result.startswith('-1 ')
        if call in ('fork', 'vfork', 'clone', 'clone3') and success:
            child = result.split()[0]
            if child.isdigit():
                directories[child] = current
            continue
        if call not in PATH_READS | FD_READS:
            continue
        kind = 'metadata'
        if call in FD_READS:
            fd = arguments.split(',', 1)[0]
            annotated = re.search(r'<(/[^<>]*)', fd)
            if not annotated:
                # Pipes, sockets and anonymous descriptors carry no file input.
                if '<' in fd or result.startswith('-1 EBADF'):
                    continue
                raise ValueError('unresolved syscall descriptor: ' + line[:200])
            name = annotated[1]
            if call.startswith('getdents'):
                kind = 'listing'
        else:
            quoted = QUOTED.search(arguments)
            if not quoted:
                if arguments.startswith('NULL,') and not success:
                    continue
                raise ValueError('undecodable syscall path: ' + line[:200])
            try:
                name = ast.literal_eval(quoted[0])
            except (ValueError, SyntaxError):
                raise ValueError('undecodable syscall path')
            if call in ('symlink', 'symlinkat'):
                # Treat aliases as input capabilities at creation, even if later deleted.
                destination = list(QUOTED.finditer(arguments))
                if len(destination) < 2:
                    raise ValueError('undecodable symlink destination')
                link = ast.literal_eval(destination[1][0])
                annotation = re.search(r'<(/[^<>]*)', arguments[quoted.end():destination[1].start()])
                linkbase = Path(annotation[1]) if annotation else current
                targetbase = (linkbase / link).parent
                if not name.startswith('/'):
                    name = str(targetbase / name)
                kind = 'content'
            if not name.startswith('/'):
                prefix = arguments[:quoted.start()]
                directory = re.search(r'<(/[^<>]*)', prefix)
                if directory:
                    base = Path(directory[1])
                elif not prefix or 'AT_FDCWD' in prefix:
                    base = current
                else:
                    raise ValueError('unresolved syscall directory: ' + line[:200])
                name = str(base / name)
            if call.startswith('open'):
                if 'O_DIRECTORY' in arguments:
                    kind = 'listing'
                elif 'O_WRONLY' not in arguments and 'O_PATH' not in arguments:
                    kind = 'content'
            elif call.startswith('execve'):
                kind = 'content'
        # Normalization must not erase a probe of an undeclared traversal component.
        parts = Path(name).parts
        for index, part in enumerate(parts):
            if part == '..' and index:
                yield Path(os.path.normpath(str(Path(*parts[:index])))), 'metadata', success
        path = Path(os.path.normpath(name))
        if call in ('chdir', 'fchdir') and success:
            directories[pid] = path
        yield path, kind, success
    if not confined:
        raise ValueError('missing authority worker confinement boundary')


def opened_paths(trace, *, successful=False, cwd=None):
    # Compatibility name: now includes every file and metadata input, not just opens.
    for path, kind, success in accesses(trace, cwd=cwd):
        if not successful or success:
            yield path, kind == 'listing'


def reads(trace, root):
    root = Path(root).absolute()
    for path, directory in opened_paths(trace, cwd=root):
        if path == root or root in path.parents:
            yield str(path.relative_to(root)), directory


def check(trace, root, declared, absent=(), *, runtime=(), scratch=None, directories=(), runtime_absent=(), after_confinement=False):
    root = Path(root).absolute()
    allowed = set(declared) | set(absent)
    parents = {'.'}
    for name in allowed | set(directories):
        parents.update(str(p) for p in Path(name).parents)
    grants = [root, *(Path(p).resolve() for p in runtime)]
    if scratch is not None:
        grants.append(Path(scratch).resolve())
    devices = {Path('/dev/null'), Path('/dev/urandom'), Path('/dev/ptmx')}  # ptmx: a fresh pair, no input
    for path, kind, success in accesses(trace, cwd=root, after_confinement=after_confinement):
        resolved = path.resolve()
        if resolved == root or root in resolved.parents:
            path = resolved
        if path == root or root in path.parents:
            name = str(path.relative_to(root))
            if kind == 'listing':
                permitted = name in directories
            else:
                permitted = name in allowed or (kind == 'metadata' and name in parents)
            if not permitted:
                raise UndeclaredInput('undeclared input read: ' + name + ' (' + kind + ')')
        elif scratch is not None:
            if not success and str(path) in runtime_absent:
                continue
            # Include failed external probes: an absent dependency still affects execution.
            resolved = path.resolve()
            if resolved in devices or any(resolved == p or p in resolved.parents for p in grants):
                continue
            if kind == 'metadata' and any(resolved in p.parents for p in grants):
                continue
            raise UndeclaredInput('undeclared runtime read: ' + str(path) + ' (' + kind + ')')


# VELDO-0217 AC4: non-file inputs, refused mechanically from the trace. A connection or datagram to
# an address no process of the traced tree bound (loopback and abstract Unix names included), a Unix
# socket outside the case's own private roots, a session or user bus, and a process started outside
# the traced tree each name a class; a case whose trace shows one is never reused.
NON_FILE_CLASSES = ('network_peer', 'unbound_loopback', 'user_bus', 'host_socket', 'outside_process')
# Programs whose purpose is to have another process run the work: a service manager, a bus, a
# scheduler, a remote shell or a container engine. The traced tree ends at their request.
LAUNCHERS = {'systemd-run', 'systemctl', 'busctl', 'dbus-send', 'dbus-launch', 'gdbus', 'at', 'batch',
             'ssh', 'docker', 'podman', 'loginctl', 'machinectl', 'flatpak-spawn', 'pkexec', 'sudo'}
SENDS = {'connect', 'sendto', 'sendmsg', 'sendmmsg'}
FAMILY = re.compile(r'\{sa_family=(AF_[A-Z0-9]+)(.*?)\}')
INET = re.compile(r'sin_port=htons\((\d+)\), sin_addr=inet_addr\("([^"]*)"\)')
INET6 = re.compile(r'sin6_port=htons\((\d+)\).*?inet_pton\(AF_INET6, "([^"]*)"')
UNIX = re.compile(r'sun_path=(@?)("(?:[^"\\]|\\.)*")')
# A socket descriptor's local endpoint as -yy prints it: TCP:[127.0.0.1:4000] or
# TCPv6:[[::1]:4000->[::1]:5000], UNIX-STREAM:[123,@"name"] or UNIX-STREAM:[123,"/path"].
LOCAL_INET = re.compile(r'<(?:TCP|UDP|UDPLITE|SCTP)(?:v6)?:\[(\[[^\]]*\]|[0-9.]+):(\d+)(?:->|\])')
LOCAL_UNIX = re.compile(r'<UNIX(?:-[A-Z]+)?:\[\d+,(@?)("(?:[^"\\]|\\.)*")\]')
WILDCARD = {'0.0.0.0', '::'}
# The socket a call's first argument names, as -yy prints it: 3<TCP:[127.0.0.1:4000]> gives
# TCP:[127.0.0.1:4000]; a listening socket keeps the same text in every later accept on it.
SOCKET = re.compile(r'^\s*\d+<((?:TCP|UDP|UDPLITE|SCTP|UNIX)[^<>]*)>')
ACCEPTS = {'accept', 'accept4'}


def _loopback(address):
    return address.startswith('127.') or address in ('::1', 'localhost') or address.startswith('::ffff:127.')


def _endpoint(arguments):
    """(family, address) of the first socket address in a call's arguments, or None. An Internet
    address is (host, port); a Unix one is ('@', name) when abstract, else ('/', path)."""
    match = FAMILY.search(arguments)
    if match is None:
        return None
    family, rest = match.groups()
    if family == 'AF_INET':
        inet = INET.search(rest)
        return (family, (inet[2], int(inet[1]))) if inet else (family, None)
    if family == 'AF_INET6':
        inet = INET6.search(rest)
        return (family, (inet[2], int(inet[1]))) if inet else (family, None)
    if family == 'AF_UNIX':
        unix = UNIX.search(rest)
        if unix is None:
            return (family, None)  # an unnamed or autobound address
        return (family, ('@' if unix[1] else '/', ast.literal_eval(unix[2])))
    return (family, rest)


def _bus(name):
    path = Path(name)
    return ('dbus' in name or path.name == 'bus' and str(path.parent).startswith('/run/user/')
            or str(path).startswith('/run/dbus/'))


OPENED = re.compile(r'^(\d+)<(/[^<>]*)>')
DESCRIPTOR_PATH = re.compile(r'^/proc/(?:self|thread-self|\d+)/fd/(\d+)$')
ABSENT = ('-1 ENOENT', '-1 ENOTDIR')


def _network(trace, private, after_confinement):
    """(classes {class: [evidence]}, absent socket paths) of one trace; see non_file_inputs."""
    private = [Path(p).resolve() for p in private]
    bound_inet, bound_unix, attempts, found, absent = set(), set(), [], {}, set()
    listening, accepted = set(), []
    descriptors = {}
    confined = not after_confinement
    for line in syscall_lines(trace):
        match = CALL.search(line)
        if not match:
            continue
        pid = line.split(None, 1)[0]
        call, arguments, result = match.groups()
        if not confined:
            if call == 'landlock_restrict_self' and result.strip() == '0':
                confined = True
            continue
        own = descriptors.setdefault(pid, {})
        opened = OPENED.match(result.strip())
        if opened:
            own[opened[1]] = opened[2]
        if call in ('fork', 'vfork', 'clone', 'clone3') and result.split()[0].isdigit():
            descriptors[result.split()[0]] = dict(own)
        # Every endpoint the traced tree holds is one it bound (an explicit bind, a listener, or the
        # kernel's choice for its own outgoing socket).
        scan = QUOTED.sub('""', line) if call in DATA_CALLS else line
        for host, port in LOCAL_INET.findall(scan):
            bound_inet.add((host.strip('[]'), int(port)))
        for abstract, name in LOCAL_UNIX.findall(scan):
            bound_unix.add(('@' if abstract else '/', ast.literal_eval(name)))
        if call == 'bind' and not result.startswith('-1 '):
            endpoint = _endpoint(arguments)
            if endpoint and endpoint[0] in ('AF_INET', 'AF_INET6') and endpoint[1]:
                bound_inet.add(endpoint[1])
            elif endpoint and endpoint[0] == 'AF_UNIX' and endpoint[1]:
                bound_unix.add(endpoint[1])
        if call == 'listen' and not result.startswith('-1 '):
            socket = SOCKET.match(arguments)
            if socket:
                listening.add(socket[1])
        if call in ACCEPTS:
            # Waiting for, or taking, a connection on a socket: the case's own only when the traced
            # tree listened on it. A socket handed in from outside is a door another process opened.
            socket = SOCKET.match(arguments)
            accepted.append((socket[1] if socket else None, line))
            continue
        if call in SENDS:
            endpoint = _endpoint(arguments)
            if endpoint is not None and endpoint[0] == 'AF_UNIX' and endpoint[1] and endpoint[1][0] == '/':
                # A socket reached through a descriptor path (/proc/self/fd/N) is the file that
                # descriptor holds in this process, when the trace shows it opened.
                held = DESCRIPTOR_PATH.match(endpoint[1][1])
                if held:
                    endpoint = ('AF_UNIX', ('/', own.get(held[1], endpoint[1][1])))
                # No socket file there: a probe of an absent path, which is keyed as an absent
                # runtime input (the toolchain's absent list), not a peer that answered.
                if result.startswith(ABSENT):
                    absent.add(endpoint[1][1])
                    continue
            if endpoint is not None:
                attempts.append((endpoint, line))
        elif call in ('execve', 'execveat'):
            quoted = QUOTED.search(arguments)
            if quoted and Path(ast.literal_eval(quoted[0])).name in LAUNCHERS:
                found.setdefault('outside_process', []).append(line[:300])
    for socket, line in accepted:
        if socket in listening:
            continue
        if socket is None or not socket.startswith('UNIX'):
            local = LOCAL_INET.search('<' + socket + '>') if socket else None
            kind = 'unbound_loopback' if local and _loopback(local[1].strip('[]')) else 'network_peer'
        else:
            kind = 'host_socket'
        found.setdefault(kind, []).append(line[:300])
    for (family, address), line in attempts:
        if family in ('AF_INET', 'AF_INET6'):
            if address is None:
                kind = 'network_peer'
            else:
                host, port = address
                ours = (host, port) in bound_inet or (_loopback(host) and any(
                    (w, port) in bound_inet for w in WILDCARD))
                kind = None if ours else ('unbound_loopback' if _loopback(host) else 'network_peer')
        elif family == 'AF_UNIX':
            if address is None:
                kind = None if 'sendto' in line or 'sendmsg' in line else 'host_socket'
            elif _bus(address[1]):
                kind = 'user_bus'
            elif address[0] == '@':
                kind = None if address in bound_unix else 'unbound_loopback'
            else:
                path = Path(os.path.normpath(address[1]))
                kind = None if any(path == root or root in path.parents for root in private) else 'host_socket'
        elif family == 'AF_UNSPEC':
            kind = None  # a disconnect, no peer
        else:
            kind = 'network_peer'  # netlink, packet, vsock and any other family reach outside the tree
        if kind is not None:
            found.setdefault(kind, []).append(line[:300])
    if not confined:
        raise ValueError('missing authority worker confinement boundary')
    return found, sorted(absent - {str(p) for p in private})


def non_file_inputs(trace, private=(), *, after_confinement=False):
    """{class: [evidence, ...]} for every non-file input the trace shows; {} when it shows none.
    `private` are the case's own roots (its scratch and its snapshot): a Unix socket path inside them
    is the case's own. Every attempt counts, answered or refused: a refused connection still told
    the case whether something listened. Only a Unix path with no socket file at all is not a peer:
    absent_sockets names it, to be keyed as an absent runtime input."""
    return _network(trace, private, after_confinement)[0]


def absent_sockets(trace, private=(), *, after_confinement=False):
    """Unix socket paths the trace tried that did not exist outside the private roots."""
    found, absent = _network(trace, private, after_confinement)
    return [p for p in absent if not any(Path(p) == Path(r).resolve() or Path(r).resolve() in Path(p).parents
                                         for r in private)]
