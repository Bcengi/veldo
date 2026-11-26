"""Authority-owned materialization and observation, with no candidate driver imports."""
import ast
import contextlib
import hashlib
import io
import ctypes
import faulthandler
import json
import os
import select
import signal
import subprocess
import resource
import runpy
import sys
import time
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
# Loaded before the worker enters confinement; authority paths are then unreadable.
FIXTURES = runpy.run_path(str(Path(__file__).with_name('gate_fixtures.py')))

# Brief A supplies these from suites/support/waits.py after integration. The
# authority observer also ships without the repository-only suites directory.
WAIT_HANG_SECONDS = 600
PROCESS_HANG_SECONDS = 3600


class Progress:
    """Only a completed progress event moves the hang bound; elapsed total is data."""
    def __init__(self, seconds=PROCESS_HANG_SECONDS, clock=None):
        self.clock = clock or time.monotonic
        self.seconds = seconds
        self.last = self.clock()
        self.event = 'started'

    def touch(self, event):
        self.last = self.clock()
        self.event = event

    def remaining(self):
        return max(0, self.seconds - (self.clock() - self.last))

    def expired(self):
        return self.remaining() == 0


def wait_readable(fds, seconds):
    """pidfds and pipes remain waitable above select's fixed descriptor ceiling."""
    poller = select.poll()
    for fd in fds:
        poller.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    return {fd for fd, events in poller.poll(seconds * 1000)}


class Events:
    """Kernel notifications for worker exits and appended output. No periodic wake."""
    def __init__(self):
        libc = ctypes.CDLL(None, use_errno=True)
        self.libc = libc
        self.fd = libc.inotify_init1(os.O_CLOEXEC | os.O_NONBLOCK)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), 'inotify_init1')
        self.pidfds = {}
        self.watches = {}
        self.notifications = {}

    def add(self, name, proc, streams, notifications=()):
        self.pidfds[name] = os.pidfd_open(proc.pid)
        self.notifications[name] = notifications
        self.watches[name] = []
        for stream in streams:
            wd = self.libc.inotify_add_watch(self.fd, os.fsencode(stream.name), 0x2 | 0x8)
            if wd < 0:
                raise OSError(ctypes.get_errno(), 'inotify_add_watch')
            self.watches[name].append(wd)

    def remove(self, name):
        self.notifications.pop(name, None)
        fd = self.pidfds.pop(name, None)
        if fd is not None:
            os.close(fd)
        for wd in self.watches.pop(name, []):
            self.libc.inotify_rm_watch(self.fd, wd)

    def wait(self, remaining):
        wait_readable([self.fd, *self.pidfds.values(),
                       *(fd for fds in self.notifications.values() for fd in fds)], remaining)
        try:
            while os.read(self.fd, 65536):
                pass
        except BlockingIOError:
            pass

    def close(self):
        for name in list(self.pidfds):
            self.remove(name)
        os.close(self.fd)


def wait_empty(path, seconds=WAIT_HANG_SECONDS):
    """Reap an owned cgroup by its populated transition, not a five-second guess."""
    try:
        fd = os.open(Path(path) / 'cgroup.events', os.O_RDONLY | os.O_CLOEXEC)
    except FileNotFoundError:
        return
    progress = Progress(seconds)
    poller = select.poll()
    poller.register(fd, select.POLLPRI | select.POLLERR)
    try:
        while True:
            values = dict(line.split() for line in os.pread(fd, 4096, 0).decode().splitlines())
            if values.get('populated') == '0':
                return
            if not poller.poll(progress.remaining() * 1000):
                raise TimeoutError('hung: cgroup remains populated: ' + str(path))
    finally:
        os.close(fd)


def run_heavy(argv, *, cwd, env, pass_fds=(), seconds=PROCESS_HANG_SECONDS, clock=None, on_line=None):
    """Capture output, rearming on complete lines. Python children dump all stacks on abort."""
    env = dict(env, PYTHONFAULTHANDLER='1', PYTHONUNBUFFERED='1')
    proc = subprocess.Popen(argv, cwd=cwd, env=env, pass_fds=pass_fds,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    progress = Progress(seconds, clock)
    stdout_fd, stderr_fd = proc.stdout.fileno(), proc.stderr.fileno()
    buffers = {stdout_fd: bytearray(), stderr_fd: bytearray()}
    fragments = {fd: bytearray() for fd in buffers}
    open_fds = set(buffers)
    pidfd = os.pidfd_open(proc.pid)
    try:
        while open_fds or pidfd >= 0:
            remaining = progress.remaining()
            # A supplied logical clock must not impose a short real-time deadline.
            wait_seconds = max(WAIT_HANG_SECONDS, remaining) if clock is not None and remaining else remaining
            ready = wait_readable([*([pidfd] if pidfd >= 0 else []), *open_fds], wait_seconds)
            if not ready:
                if not progress.expired():
                    continue
                os.killpg(proc.pid, signal.SIGABRT)
                out, err = proc.communicate()
                raise TimeoutError('hung after ' + progress.event + '\n' +
                                   (bytes(buffers[stderr_fd]) + err).decode(errors='replace'))
            for fd in open_fds.intersection(ready):
                data = os.read(fd, 65536)
                if not data:
                    open_fds.remove(fd)
                else:
                    buffers[fd].extend(data)
                    fragments[fd].extend(data)
                    while b'\n' in fragments[fd]:
                        line, _, rest = fragments[fd].partition(b'\n')
                        fragments[fd] = bytearray(rest)
                        if on_line is not None:
                            on_line(bytes(line))
                        progress.touch(line.decode(errors='replace')[-400:])
            if pidfd in ready:
                proc.wait()
                os.close(pidfd)
                pidfd = -1
        return subprocess.CompletedProcess(argv, proc.wait(),
            bytes(buffers[stdout_fd]).decode(errors='replace'),
            bytes(buffers[stderr_fd]).decode(errors='replace'))
    finally:
        if pidfd >= 0:
            os.close(pidfd)
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        proc.stdout.close()
        proc.stderr.close()


def run_python(script):
    """Expose selftest row events to its heavy-child parent without changing the dispatcher.

    A profile callback observes entry/return of the real shared expect function,
    including its dynamically named rows. Output stays on stderr, away from the
    suite summary and the mutation worker's JSON protocol.
    """
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    faulthandler.enable()
    def profile(frame, event, arg):
        if (event in ('call', 'return') and frame.f_code.co_name == 'expect'
                and frame.f_code.co_filename.endswith('/scripts/suites/shared.py')):
            name = str(frame.f_locals.get('name', 'row')).split(':', 1)[0]
            faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)
            os.write(2, ('SELFTEST PROGRESS ' + event + ' ' + name + '\n').encode())
    previous = sys.getprofile()
    sys.argv = [script]
    sys.setprofile(profile)
    faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)
    try:
        runpy.run_path(script, run_name='__main__')
    finally:
        sys.setprofile(previous)
        faulthandler.cancel_dump_traceback_later()


def edits(case):
    return [(case['old'], case['new'])] + [tuple(pair) for pair in case.get('also', ())]


def mutate(text, case):
    """Apply every replacement of `case` to `text` (str or bytes); each anchor must occur exactly
    once in the text it is applied to."""
    for old, new in edits(case):
        if isinstance(text, bytes):
            old, new = old.encode(), new.encode()
        if text.count(old) != 1:
            raise RuntimeError((case['name'], 'mutation anchor moved', text.count(old)))
        text = text.replace(old, new)
    return text


def materialize(case, mode, directory, root=ROOT):
    """Own case paths, exact replacement and file/directory copies for every driver.

    Digests describe the actual module bytes, even when the suite receives a directory.
    Baselines use the original input; no-op and mutant copies never edit that input.
    """
    if mode not in ('baseline', 'noop', 'mutant'):
        raise ValueError('unknown mutation mode: ' + mode)
    fixture = case.get('fixture') is True
    # `dir`: the directory a production module lives in, relative to the root (.veldo by default;
    # VELDO-0058's gate script lives in scripts).
    base = root / 'scripts/fixtures' if fixture else root / case.get('dir', '.veldo')
    source = base / case['module']
    before = source.read_bytes()
    old = case['old'].encode()
    count = before.count(old)
    if count != 1:
        raise RuntimeError((case['name'], 'mutation anchor moved', count))
    mutated = mutate(before, case)
    mutant = None
    after = before
    if mode != 'baseline':
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        mutant = destination / ('fixtures' if fixture else case['module'])
        if fixture:
            shutil.copytree(base, mutant, ignore=shutil.ignore_patterns('__pycache__'))
        elif case.get('dir', '.veldo') == '.veldo' or case.get('siblings') is True:
            # Baseline modules live in a complete tree. Give every production copy the
            # same siblings, including dependencies loaded only on first use. A sparse
            # companion list can make an identity replacement fail before its target.
            shutil.copytree(base, destination / 'veldo', ignore=shutil.ignore_patterns('__pycache__'))
            mutant = destination / 'veldo' / case['module']
            # Frozen inputs are read-only. The old sparse layout created writable
            # files for the selected module and companions; restore only those
            # write sites, leaving the complete tree's other modes untouched.
            for name in (case['module'], *case.get('companions', ())):
                copied = destination / 'veldo' / name
                copied.chmod(copied.stat().st_mode | 0o200)
        target = mutant / case['module'] if fixture else mutant
        target.parent.mkdir(parents=True, exist_ok=True)
        for name in case.get('companions', ()):
            # A module that loads a named sibling by its own path runs beside an unchanged copy of it.
            shutil.copyfile(base / name, target.parent / name)
        target.write_bytes(before if mode == 'noop' else mutated)
        after = target.read_bytes()
    return dict(source=source, mutant=mutant, replacement_count=count,
                old_digest=hashlib.sha256(before).hexdigest(),
                new_digest=hashlib.sha256(after).hexdigest())


@contextlib.contextmanager
def suite_imports():
    """The isolated observer gives suite imports their repository, after interpreter paths."""
    previous = sys.path[:]
    sys.path.append(str(ROOT / 'scripts'))
    try:
        yield
    finally:
        sys.path[:] = previous


@contextlib.contextmanager
def private_runtime():
    """A single-case worker owns its runtime, just as a dispatcher shard does.

    Never inherit the login session's write directory. Keep the socket path short
    enough that run-query cannot fall back out of this allocation. Only the user
    manager's sockets and unit directory are linked into it.
    """
    with FIXTURES['directory']() as runtime:
        FIXTURES['socket_paths']({'run query': runtime / ('vq-' + '0' * 32) / 'query.sock'})
        real = Path('/run/user/%d' % os.getuid())
        for relative in ('bus', 'systemd/private', 'systemd/user'):
            source = real / relative
            if source.is_dir() if relative == 'systemd/user' else source.is_socket():
                target = runtime / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.symlink_to(source)
        names = ('XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS')
        previous = {name: os.environ.get(name) for name in names}
        os.environ['XDG_RUNTIME_DIR'] = str(runtime)
        os.environ.pop('DBUS_SESSION_BUS_ADDRESS', None)
        if (runtime / 'bus').is_socket():
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=%s/bus' % runtime
        try:
            yield runtime
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


def worker(case, mutant=None, *, isolate_runtime=True, selected_rows=None):
    """Capture every assertion, including the shared preamble, with exact row identities."""
    shared = ROOT / 'scripts/suites/shared.py'
    dependency = DependencyReads(ROOT, discover_git=False).start()
    rows = []
    opened = set()
    auditing = [True]
    terminal_rows = set()
    def audit(event, args):
        if not auditing[0] or event != "open" or not args or not isinstance(args[0], (str, bytes)):
            return
        path = Path(os.path.abspath(os.fsdecode(args[0])))
        if mutant:
            copy = Path(mutant)
            base = ROOT / ('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo'))
            if case.get('fixture') and (path == copy or copy in path.parents):
                path = base / path.relative_to(copy)
            elif path == copy:
                path = base / case['module']
            elif (case.get('siblings') or case.get('companions')) and copy.parent in path.parents:
                path = base / path.relative_to(copy.parent)
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            return
        if relative.startswith(("scripts/", "proof/")):
            opened.add(relative)
    sys.addaudithook(audit)
    details = []  # a false row's own words after its colon: what the check saw, kept beside the row

    def observe(name, condition):
        faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)
        os.write(2, ('SELFTEST PROGRESS ' + name.split(':', 1)[0] + '\n').encode())
        if ns.get('WAITS') is not None:
            ns['WAITS'].row_event(name)
        rows.append([name.split(':', 1)[0], bool(condition)])
        if not condition and ':' in name:
            details.append([rows[-1][0], name.split(':', 1)[1].strip()])
    ns = {'__file__': str(shared), '__observe__': observe}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    faulthandler.enable()
    faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)
    with suite_imports(), contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        waits = ns.get('WAITS')
        if waits is not None:
            # Match selftest's process ownership: an outer scheduler is a subreaper,
            # but cannot wait for a whole stage to end before collecting our orphans.
            # The keeper wakes on SIGCHLD and reaps them while this suite is running.
            # Shared-preamble rows may have armed a watchdog; the keeper must not
            # inherit that timer, since only its child will report further progress.
            faulthandler.cancel_dump_traceback_later()
            waits.keep_the_tree()
            original_wait = waits.wait
            def observed_wait(*args, **kwargs):
                result = original_wait(*args, **kwargs)
                if result.outcome == 'impossible':
                    terminal_rows.add(waits.next_row(sys._getframe(1), result.name))
                return result
            waits.wait = observed_wait
        faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)
        suite = ROOT / 'scripts/suites' / case['suite']
        source = suite.read_text()
        if case.get('fixture'):
            if mutant:
                source = source.replace('ROOT / "scripts" / "fixtures"',
                                        '__import__("pathlib").Path(' + repr(mutant) + ')')
        elif mutant and case.get('dir') == 'scripts/suites' and case['module'] == case['suite']:
            # The mutated module is the suite itself (a fake engine it embeds): its copy is what runs.
            source = Path(mutant).read_text()
        elif mutant:
            anchor = 'ROOT / "' + case.get('dir', '.veldo') + '" / "' + case['module'] + '"'
            if not source.count(anchor):
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(mutant) + ')')
        if selected_rows is not None:
            source = dependency_module('gate_changes')['row_source'](source, selected_rows)
            if any(ok is not True for _, ok in rows):
                raise RuntimeError('selected row setup failed')
            rows.clear()  # setup ran, but selected observations belong to the requested rows
            details.clear()
        ns['__suite_file__'] = str(suite)
        # Declared workers have only their keyed scratch grant and cannot reach the
        # host runtime. Fresh workers, including direct single-case drives, own a
        # fixture allocation and must never inherit the login session's directory.
        with private_runtime() if isolate_runtime else contextlib.nullcontext():
            exec(compile(source, str(suite), 'exec'), ns)
        if waits is not None:
            waits.run_ended()
    faulthandler.cancel_dump_traceback_later()
    auditing[0] = False
    dependency.stop()
    dependency.read(ROOT / case.get('dir', '.veldo') / case['module'])
    for definition in ('mutation_observer.py', 'reuse_worker.py', 'gate_changes.py', 'gate_fixtures.py'):
        # These authority modules were loaded before confinement. Recording their
        # names must not probe absent counterparts in a declared input snapshot.
        dependency.paths.add('scripts/' + definition)
    commit = os.environ.get('VELDO_DEPENDENCY_COMMIT', '0' * 40)
    if commit == '0' * 40:
        dependency.unknown('observed commit unavailable')
    changes = dependency_module('gate_changes')
    item_id = changes['identity']('case', 'mutation', os.environ.get('VELDO_DEPENDENCY_LEG', 'confined'),
                                  case['suite'], case.get('driver', ''), case['name'])
    return {'dependency': dependency.record(item_id, commit), 'opened_files': sorted(opened),
            'failure_kinds': {name: 'terminal' if name in terminal_rows else 'assertion'
                              for name, ok in rows if not ok},
            'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'failed_details': details,
            'targets': {label: [ok for name, ok in rows if name.split()[-1] == label]
                        for label in (case['rows'] if selected_rows is None else
                                      [name.split()[-1] for name in selected_rows])}}

# VELDO-0367: observations never authorize selection. Python audit events are
# useful attribution, but are NOT a complete filesystem trace (notably stat and
# native children). Only a closed syscall trace can remove that unknown reason.
DEPENDENCY_MODULES = {}


def dependency_module(name):
    if name not in DEPENDENCY_MODULES:
        DEPENDENCY_MODULES[name] = runpy.run_path(str(Path(__file__).with_name(name + '.py')))
    return DEPENDENCY_MODULES[name]


class DependencyReads:
    """One executing item's reads, including failed probes and discovery inputs."""
    def __init__(self, root, environment=None, *, discover_git=True, private_scratch=()):
        self.root = Path(root).resolve()
        self.paths, self.directories, self.absent_paths = set(), set(), set()
        self.reasons = {'observation coverage unavailable'}
        values = os.environ if environment is None else environment
        # Execution paths and descriptors are per-run allocations, not runtime identity.
        self.runtime = {'environment': {k: values[k] for k in
            ('LANG', 'LC_ALL', 'LC_CTYPE', 'TZ', 'PYTHONHASHSEED', 'PYTHONUTF8') if k in values}}
        self.scratch = tuple(Path(values[k]).resolve() for k in
                             ('TMPDIR', 'TEMP', 'TMP', 'VELDO_FIXTURE_PARENT', 'XDG_RUNTIME_DIR')
                             if values.get(k))
        self.private_scratch = tuple(Path(path).resolve() for path in private_scratch)
        self.authority = Path(__file__).resolve().parents[1]
        self.git_directories = {self.root / '.git'}
        try:
            marker = self.root / '.git'
            if discover_git and marker.is_file():
                text = marker.read_text().strip()
                if text.startswith('gitdir: '):
                    gitdir = (self.root / text[8:]).resolve()
                    self.git_directories.add(gitdir)
                    common = gitdir / 'commondir'
                    if common.is_file():
                        self.git_directories.add((gitdir / common.read_text().strip()).resolve())
        except OSError:
            self.unknown('git directory unavailable')
        self.active, self.busy = False, False

    def unknown(self, reason):
        self.reasons.add(reason)

    def read(self, path, kind='content', success=True):
        if not isinstance(path, (str, bytes, os.PathLike)):
            self.unknown('unresolved descriptor or path')
            return
        if '..' in Path(os.fsdecode(path)).parts:
            self.unknown('ambiguous parent traversal')
        path = Path(os.path.abspath(os.fsdecode(path)))
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            self.unknown('unresolved symlink')
            return
        for candidate in {path, resolved}:
            if any(candidate == directory or directory in candidate.parents for directory in self.git_directories):
                self.unknown('git metadata read')
                continue
            try:
                relative = candidate.relative_to(self.root).as_posix()
            except ValueError:
                # Only the authority may designate its newly allocated private worker home.
                # Its job and materialized outputs derive from the recorded case definition/reads.
                if any(candidate == directory or directory in candidate.parents for directory in self.private_scratch):
                    continue
                if any(candidate == directory or directory in candidate.parents for directory in self.scratch):
                    self.unknown('unrecordable external scratch input')
                    continue
                if candidate == Path('/dev/null'):
                    continue
                # External inputs are represented by their bytes or directory
                # entries, not merely by the interpreter's version string.
                try:
                    if str(candidate).startswith(('/proc/', '/sys/', '/dev/', '/run/')):
                        raise ValueError('volatile runtime')
                    if not success and not candidate.exists():
                        value = ['absent']
                    elif candidate.is_file():
                        value = ['file', hashlib.sha256(candidate.read_bytes()).hexdigest(),
                                 candidate.stat().st_mode]
                    elif candidate.is_dir():
                        value = ['directory', sorted(os.listdir(candidate))]
                    else:
                        raise ValueError('external input')
                    key = ('authority:' + candidate.relative_to(self.authority).as_posix()
                           if self.authority in candidate.parents else str(candidate))
                    self.runtime[key] = value
                except (OSError, ValueError):
                    self.unknown('unrecordable external input: ' + str(candidate))
                continue
            if candidate.parent.name == '__pycache__' and '.cpython-' in candidate.name and candidate.suffix == '.pyc':
                source = candidate.parent.parent / (candidate.name.split('.cpython-', 1)[0] + '.py')
                self.paths.add(source.relative_to(self.root).as_posix())
            if kind == 'listing':
                self.directories.add(relative)
            elif relative != '.':
                self.paths.add(relative)
            if not success and relative != '.':
                self.absent_paths.add(relative)
        # A symlink in an intermediate component also affects the lookup.
        for parent in path.parents:
            if parent == self.root:
                break
            if self.root in parent.parents and parent.is_symlink():
                self.paths.add(parent.relative_to(self.root).as_posix())

    def audit(self, event, args):
        if not self.active or self.busy:
            return
        self.busy = True
        try:
            if event == 'open':
                self.read(args[0], success=os.path.exists(args[0]) if isinstance(args[0], (str, bytes)) else True)
            elif event == 'import' and args[1]:
                self.read(args[1])
            elif event in ('os.listdir', 'os.scandir'):
                self.read(args[0] if args and args[0] is not None else os.getcwd(), 'listing')
            elif event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn', 'os.exec'):
                self.unknown('native child coverage unavailable')
            elif event.startswith(('socket.', 'ctypes.')):
                self.unknown('unrecordable external input: ' + event)
        except (OSError, ValueError, TypeError):
            self.unknown('unresolved audit event')
        finally:
            self.busy = False

    def start(self):
        self.unknown('Python audit lacks complete syscall coverage')
        sys.addaudithook(self.audit)
        self.active = True
        return self

    def stop(self):
        self.active = False
        return self

    def trace(self, trace, *, dropped=False, launched_argv=()):
        """Read an authority-owned -f trace after all traced processes ended.

        A truncated, detached, malformed or namespace-changing trace stays unknown.
        launched_argv is taken from the authority's completed process.args, never
        from a worker claim. A legacy filtered trace cannot establish completeness. This does not start
        ptrace in worker trees: their existing prohibition stands.
        """
        tracer = dependency_module('case_trace')
        try:
            lines = Path(trace).read_text().splitlines()
            seen, ended = set(), set()
            for line in lines:
                if not line.strip():
                    continue
                pid = line.split(None, 1)[0]
                if not pid.isdigit():
                    raise ValueError('lost events or tracer diagnostic')
                seen.add(pid)
                if tracer['ENDED'].match(line):
                    ended.add(pid)
                elif not (tracer['CALL'].search(line) or '<unfinished ...>' in line
                          or ' resumed>' in line or '--- SIG' in line):
                    raise ValueError('unrecognized trace event')
                if any(token in line for token in ('unshare(', 'setns(', 'chroot(', 'pivot_root(',
                        'mount(', 'io_uring_', 'ptrace(', 'bpf(', 'CLONE_FS', 'CLONE_NEW')):
                    raise ValueError('ambiguous process filesystem')
                if '...' in line and '<unfinished ...>' not in line and '<... ' not in line:
                    raise ValueError('truncated trace event')
            # syscall_lines joins unfinished/resumed clone calls before finding children.
            for line in tracer['syscall_lines'](trace):
                call = tracer['CALL'].search(line)
                if call and call[1] in ('clone', 'clone3', 'fork', 'vfork'):
                    child = call[3].split()[0]
                    if child.isdigit() and child != '0':
                        seen.add(child)
            if dropped or not seen or seen != ended:
                raise ValueError('lost events or incomplete child coverage')
            for path, kind, success in tracer['accesses'](trace, cwd=self.root):
                self.read(path, kind, success)
            # Descriptor inputs (including mmap and inherited descriptors) need
            # their kernel-resolved path too; path-only traces cannot see these.
            import re
            for line in tracer['syscall_lines'](trace):
                call = tracer['CALL'].search(line)
                if call and call[1] in ('read', 'pread64', 'readv', 'preadv', 'preadv2',
                                       'mmap', 'mmap2', 'sendfile', 'copy_file_range'):
                    for name in re.findall(r'<(/[^<>]*)>', call[2]):
                        self.read(name)
                    if not re.search(r'<[^<>]+>', call[2]) and 'MAP_ANONYMOUS' not in call[2]:
                        self.unknown('unresolved inherited descriptor')
            if tracer['full_command'](launched_argv, trace):
                self.reasons.discard('observation coverage unavailable')
            if tracer['non_file_inputs'](trace):
                self.unknown('unrecordable external inputs in trace')
        except (OSError, ValueError, SyntaxError) as error:
            self.unknown('incomplete trace: ' + str(error))
        return self

    def record(self, item_id, commit):
        changes = dependency_module('gate_changes')
        value = changes['sealed'](changes['DEPENDENCY'], item_id=item_id, observed_commit=commit,
            paths=sorted(self.paths), directories=sorted(self.directories), absent_paths=sorted(self.absent_paths),
            runtime_digest=changes['digest'](self.runtime), complete=not self.reasons,
            unknown_reason='; '.join(sorted(self.reasons)) or None)
        return changes['validate_dependency'](value)


def combine_dependencies(records, item_id, commit, *, prior=None, rows=False):
    """Controls/mutants and prerequisite groups use their union. Rows never shrink it."""
    changes = dependency_module('gate_changes')
    records = list(records)
    if rows and prior is not None:
        records.append(prior)
    for record in records:
        changes['validate_dependency'](record)
    reasons = {r['unknown_reason'] for r in records if not r['complete']}
    if not records or rows and prior is None:
        reasons.add('missing complete suite observation')
    if any(r['observed_commit'] != commit for r in records if r is not prior):
        reasons.add('mixed observed commits')
    return changes['sealed'](changes['DEPENDENCY'], item_id=item_id, observed_commit=commit,
        **{field: sorted({p for r in records for p in r[field]})
           for field in ('paths', 'directories', 'absent_paths')},
        runtime_digest=changes['digest'](sorted({r['runtime_digest'] for r in records})),
        complete=not reasons, unknown_reason='; '.join(sorted(reasons)) or None)


def publish_dependencies(store, dependency, result):
    """One authenticated atomic publication contains BOTH result and dependencies.

    Interruption cannot expose an envelope with half of its evidence. No green gate/index is published here.
    """
    changes = dependency_module('gate_changes')
    changes['validate_dependency'](dependency)
    envelope = changes['sealed']('veldo.change-observation/v1', dependency=dependency, result=result)
    if not store.change_put(envelope):
        raise OSError('dependency/result publication failed')
    return envelope


def clean_commit(root):
    """Only an immutable clean checkout can name its HEAD as observation source."""
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    before = git('rev-parse', 'HEAD')
    status = git('status', '--porcelain', '--untracked-files=all')
    after = git('rev-parse', 'HEAD')
    if (before.returncode or status.returncode or status.stdout or after.returncode
            or before.stdout != after.stdout or len(after.stdout.strip()) not in (40, 64)):
        return '0' * 40
    return after.stdout.strip()


def native_dependency(native, claim):
    """Python adds attribution, but only the authority trace certifies coverage."""
    changes = dependency_module('gate_changes')
    changes['validate_dependency'](claim)
    if native is None:
        return claim
    changes['validate_dependency'](native)
    if native['observed_commit'] != claim['observed_commit']:
        raise ValueError('native dependency commit differs from worker claim')
    return changes['sealed'](changes['DEPENDENCY'], item_id=claim['item_id'],
        observed_commit=claim['observed_commit'],
        **{field: sorted(set(native[field]) | set(claim[field]))
           for field in ('paths', 'directories', 'absent_paths')},
        runtime_digest=native['runtime_digest'], complete=native['complete'],
        unknown_reason=native['unknown_reason'])
