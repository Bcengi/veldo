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


def worker(case, mutant=None):
    """Capture every assertion, including the shared preamble, with exact row identities."""
    shared = ROOT / 'scripts/suites/shared.py'
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
        ns['__suite_file__'] = str(suite)
        exec(compile(source, str(suite), 'exec'), ns)
        if waits is not None:
            waits.run_ended()
    faulthandler.cancel_dump_traceback_later()
    auditing[0] = False
    return {'opened_files': sorted(opened),
            'failure_kinds': {name: 'terminal' if name in terminal_rows else 'assertion'
                              for name, ok in rows if not ok},
            'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'failed_details': details,
            'targets': {label: [ok for name, ok in rows if name.split()[-1] == label]
                        for label in case['rows']}}
