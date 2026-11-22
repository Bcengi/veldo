"""The one place a suite may block, and the suite process's runtime (VELDO-0358, brief A).

A WAIT has a done condition, an optional terminal condition (the event that proves the done one can no
longer come) and the kernel event sources that can change either. It wakes only when one of those sources
fires and reads both conditions again. It has exactly three outcomes:

  done        the done condition holds
  impossible  the terminal condition holds; the row fails at once, on that evidence
  hung        WAIT_HANG_SECONDS passed since the wait began with neither. This is never returned and never
              read as false: the row is printed as hung (SELFTEST HUNG, with the wait's name and its source
              line), every thread's stack is written, every row not reached is printed as not run
              (SELFTEST NOT RUN), and the suite's process ends red.

The sources (C2): a process exit (Pidfd), a readable descriptor (Readable), a path appearing or being
replaced (PathAppears: inotify on its directory, or on the nearest existing ancestor and moved down on each
creation), a change of a store (Store: inotify on its write-ahead file, the writer's lock awaited, then the
condition re-read) and a cgroup becoming empty (CgroupEmpty: cgroup.events). While none fires, the waiting
thread is in one poll call whose only timeout is the wait hang bound.

The suite process's runtime (C5, C6, C7): the rows a suite emits through shared.expect are progress
events; the progress watchdog ends a process only after PROCESS_HANG_SECONDS with no row starting or
ending, and writes every thread's stack first; the residue reading names the threads, children and
listening sockets a suite left behind; the keeper (keep_the_tree) kills and reaps every process a run
that did not finish left behind, whoever its parent was by then.

The two constants below are the only durations a suite or the gate's tooling may name (design, section 6).
This module and its Stamp are the one place the census's rules R1 to R3 do not apply.
"""
import ast
import ctypes
import errno
import faulthandler
import fcntl
import os
import re
import select
import struct
import sys
import tempfile
import threading
import time

WAIT_HANG_SECONDS = 600
PROCESS_HANG_SECONDS = 3600

# The closed list of heavy children (design, section 6): a child that runs one of these may be given the
# process hang bound, measured from its last output line; every other child call is light and gets the wait
# hang bound. Decided by what the child runs, never by how long it is expected to take.
HEAVY_CHILDREN = ('suite', 'selftest', 'gate stage', 'browser run', 'package install', 'qualify')

HUNG_EXIT_STATUS = 1


# ----------------------------------------------------------------------------------------------- stamp


class Stamp:
    """A moment, for ordering and for a lower bound only. It has no subtraction, so an upper bound on a
    real duration cannot be written with it; iso() gives the wall time as data for a record."""

    __slots__ = ('_mono', '_wall')

    def __init__(self):
        self._mono = time.monotonic()
        self._wall = time.time()

    def __lt__(self, other):
        return self._mono < other._mono

    def __le__(self, other):
        return self._mono <= other._mono

    def __gt__(self, other):
        return self._mono > other._mono

    def __ge__(self, other):
        return self._mono >= other._mono

    def at_least(self, start, seconds):
        """True when this stamp is at least `seconds` after `start`: a lower bound, which load can only
        make truer."""
        return self._mono - start._mono >= seconds

    def iso(self):
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(self._wall)) + '.%06dZ' % int(
            (self._wall % 1) * 1e6)

    def __repr__(self):
        return 'Stamp(%s)' % self.iso()


def stamp():
    return Stamp()


# --------------------------------------------------------------------------------------------- inotify

_LIBC = ctypes.CDLL(None, use_errno=True)
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800
IN_ONLYDIR = 0x01000000
_IN_NONBLOCK = os.O_NONBLOCK
_IN_CLOEXEC = os.O_CLOEXEC
_EVENT = struct.Struct('iIII')

ENTRY_EVENTS = IN_CREATE | IN_MOVED_TO | IN_DELETE | IN_MOVED_FROM | IN_CLOSE_WRITE | IN_ATTRIB
SELF_EVENTS = IN_DELETE_SELF | IN_MOVE_SELF


class Inotify:
    """A non-blocking inotify descriptor, through the C library (the standard library has no binding)."""

    def __init__(self):
        fd = _LIBC.inotify_init1(_IN_NONBLOCK | _IN_CLOEXEC)
        if fd < 0:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
        self.fd = fd

    def add(self, path, mask):
        wd = _LIBC.inotify_add_watch(self.fd, os.fsencode(path), mask)
        if wd < 0:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e), path)
        return wd

    def remove(self, wd):
        _LIBC.inotify_rm_watch(self.fd, wd)

    def drain(self):
        """Every queued event, as (wd, mask, name); never blocks."""
        out = []
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return out
            at = 0
            while at < len(data):
                wd, mask, _cookie, size = _EVENT.unpack_from(data, at)
                name = data[at + _EVENT.size:at + _EVENT.size + size].rstrip(b'\0')
                out.append((wd, mask, os.fsdecode(name)))
                at += _EVENT.size + size

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


# --------------------------------------------------------------------------------------------- sources


class Source:
    """A kernel notification a wait wakes on. `fileno()` is polled for `events`; `fired()` consumes the
    notification and says whether the source stays watched. `interval` is None for every real source:
    nothing here wakes on a timer."""

    events = select.POLLIN
    interval = None

    def fileno(self):
        raise NotImplementedError

    def fired(self):
        return True

    def close(self):
        pass

    def describe(self):
        return type(self).__name__


class Pidfd(Source):
    """A process exit, on its pidfd. One shot: an exit happens once."""

    def __init__(self, process):
        self.pid = process if isinstance(process, int) else process.pid
        self.fd = os.pidfd_open(self.pid)

    def fileno(self):
        return self.fd

    def fired(self):
        return False

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def describe(self):
        return 'pidfd(%d)' % self.pid


class Readable(Source):
    """A readable descriptor (a pipe or a stream socket). With drain, each wake reads what is there into
    `data` (so a condition can read it) and end of file ends the watch; without, the first wake ends it and
    the condition reads the descriptor itself; with persistent as well, the watch stays and the condition
    must consume what it reads (else the descriptor stays readable and wakes it again at once)."""

    def __init__(self, fd, drain=True, persistent=False):
        self.fd = fd if isinstance(fd, int) else fd.fileno()
        self.drain = drain
        self.persistent = persistent
        self.data = bytearray()
        self.closed = False

    def fileno(self):
        return self.fd

    def fired(self):
        if not self.drain:
            return self.persistent
        chunk = os.read(self.fd, 65536)
        if not chunk:
            self.closed = True
            return False
        self.data += chunk
        return True

    def describe(self):
        return 'readable(%d)' % self.fd


class PathAppears(Source):
    """A path appearing, being replaced or going away: inotify on its directory. While the directory does
    not exist yet, the watch is on the nearest existing ancestor and is moved one level down on each
    creation, so a directory made two levels deep after the wait began is followed. With modify, the file
    itself is also watched for writes once it exists."""

    def __init__(self, path, modify=False):
        self.path = os.path.abspath(os.fspath(path))
        self.modify = modify
        self.ino = Inotify()
        self.dir_wd = None
        self.dir_at = None
        self.file_wd = None
        self.interval = None
        self._place()

    def _nearest(self):
        at = os.path.dirname(self.path)
        while not os.path.isdir(at):
            at = os.path.dirname(at)
        return at

    def _place(self):
        """Put the directory watch on the path's directory, or on its nearest existing ancestor, and the
        file watch on the file when it exists. Repeated until stable, because a level may be created
        between finding the ancestor and watching it (that creation's event went to the old watch)."""
        while True:
            at = self._nearest()
            if at == self.dir_at:
                break
            if self.dir_wd is not None:
                self.ino.remove(self.dir_wd)
                self.dir_wd = None
            try:
                self.dir_wd = self.ino.add(at, ENTRY_EVENTS | SELF_EVENTS | IN_ONLYDIR)
            except OSError as e:
                if e.errno in (errno.ENOENT, errno.ENOTDIR):
                    self.dir_at = None
                    continue
                raise
            self.dir_at = at
        if self.modify:
            if self.file_wd is None and os.path.exists(self.path):
                try:
                    self.file_wd = self.ino.add(self.path, IN_MODIFY | IN_CLOSE_WRITE | SELF_EVENTS)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            elif self.file_wd is not None and not os.path.exists(self.path):
                self.ino.remove(self.file_wd)
                self.file_wd = None

    def fileno(self):
        return self.ino.fd

    def fired(self):
        for wd, mask, _name in self.ino.drain():
            if wd == self.file_wd and mask & (SELF_EVENTS | 0x8000):
                self.file_wd = None
            if wd == self.dir_wd and mask & (SELF_EVENTS | 0x8000):
                self.dir_wd, self.dir_at = None, None
        self._place()
        return True

    def close(self):
        self.ino.close()

    def describe(self):
        return 'path(%s, watching %s)' % (self.path, self.dir_at)


_WAL_WRITE_LOCK_BYTE = 120  # SQLite's unix VFS: UNIX_SHM_BASE plus WAL_WRITE_LOCK, in the -shm file
_FLOCK = struct.Struct('hhxxxxqqixxxx')


class Store(PathAppears):
    """A change of an SQLite store in WAL mode: inotify on its write-ahead file. A commit is several writes
    and is visible only once the writer has updated the index and released its write lock, so on each wake
    the writer's lock is awaited (a blocking open-file-description read lock on SQLite's write-lock byte,
    released at once) before the condition is read again. Without that, the last write's wake could read the
    store before the commit is visible, and nothing would wake the wait again."""

    def __init__(self, database):
        self.database = os.path.abspath(os.fspath(database))
        super().__init__(self.database + '-wal', modify=True)

    def fired(self):
        self._writer_done()
        return super().fired()

    def _writer_done(self):
        try:
            fd = os.open(self.database + '-shm', os.O_RDONLY | os.O_CLOEXEC)
        except FileNotFoundError:
            return
        try:
            fcntl.fcntl(fd, fcntl.F_OFD_SETLKW, _FLOCK.pack(fcntl.F_RDLCK, os.SEEK_SET,
                                                            _WAL_WRITE_LOCK_BYTE, 1, 0))
            fcntl.fcntl(fd, fcntl.F_OFD_SETLK, _FLOCK.pack(fcntl.F_UNLCK, os.SEEK_SET,
                                                           _WAL_WRITE_LOCK_BYTE, 1, 0))
        finally:
            os.close(fd)

    def describe(self):
        return 'store(%s)' % self.database


def _cgroup_gone(error):
    """A cgroup that is no longer there: its files answer ENOENT once it is removed, and ENODEV when it is
    removed between the open and the read (the descriptor outlives the group). Both are the same fact."""
    return error.errno in (errno.ENOENT, errno.ENODEV)


def _cgroup_events(cgroup):
    """An open descriptor on the cgroup's cgroup.events."""
    return os.open(os.path.join(os.fspath(cgroup), 'cgroup.events'), os.O_RDONLY | os.O_CLOEXEC)


class CgroupEmpty(Source):
    """A cgroup becoming empty (or changing population): cgroup.events, which the kernel signals with
    POLLPRI and which is read again to re-arm it. A group already removed, at the open or at the first
    read, is a source that is `gone`: it is not polled, because nothing more will come from it, and the
    wait's conditions (cgroup_populated answers None for it) decide at their first reading."""

    events = select.POLLPRI | select.POLLERR

    def __init__(self, cgroup):
        self.cgroup = os.fspath(cgroup)
        self.fd = -1
        self.gone = False
        try:
            self.fd = _cgroup_events(self.cgroup)
            self._read()
        except OSError as error:
            self.close()
            if not _cgroup_gone(error):
                raise
            self.gone = True

    def _read(self):
        os.lseek(self.fd, 0, os.SEEK_SET)
        return os.read(self.fd, 4096)

    def fileno(self):
        return None if self.gone else self.fd

    def fired(self):
        try:
            self._read()
        except OSError as error:
            if not _cgroup_gone(error):
                raise
            self.gone = True
            return False  # the cgroup was removed: nothing more will come from it
        return True

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def describe(self):
        return 'cgroup(%s%s)' % (self.cgroup, ', gone' if self.gone else '')


def cgroup_populated(cgroup):
    """True, False, or None when the cgroup is gone (removed before the open, or between it and the read)."""
    try:
        fd = _cgroup_events(cgroup)
        try:
            text = os.read(fd, 4096).decode('ascii', 'replace')
        finally:
            os.close(fd)
    except OSError as error:
        if _cgroup_gone(error):
            return None
        raise
    for line in text.splitlines():
        key, _, value = line.partition(' ')
        if key == 'populated':
            return value.strip() == '1'
    return None


class LegacyInterval(Source):
    """NOT AN EVENT. Only for a caller of shared.wait_for that names no source yet: the condition is read
    again every interval. Each such caller is a site of the census in its own file and is converted (given
    its sources and a terminal condition) in its wave; no new caller may use this."""

    def __init__(self, seconds=0.02):
        self.interval = seconds

    def fileno(self):
        return None

    def describe(self):
        return 'legacy-interval(%gs)' % self.interval


# ------------------------------------------------------------------------------------------------ wait


class Result:
    """What a wait ended with: outcome 'done' or 'impossible', the last observation of each condition, and
    the report a row carries (what was waited for, the bound and its source, the last observations, the
    terminal condition and the sources)."""

    def __init__(self, outcome, name, source_line, done_obs, terminal_obs, sources, bound):
        self.outcome = outcome
        self.name = name
        self.source_line = source_line
        self.done_observation = done_obs
        self.terminal_observation = terminal_obs
        self.sources = sources
        self.bound = bound

    @property
    def done(self):
        return self.outcome == 'done'

    @property
    def impossible(self):
        return self.outcome == 'impossible'

    def report(self):
        return ('%s for %s (%s), bound %d s (waits.WAIT_HANG_SECONDS); last observed: done=%r, terminal=%r; '
                'sources: %s' % (self.outcome, self.name, self.source_line, self.bound, self.done_observation,
                                 self.terminal_observation, ', '.join(self.sources) or 'none'))

    def __bool__(self):
        return self.done

    def __repr__(self):
        return 'Result(%s)' % self.report()


def _reading(condition):
    """(holds, observation) from a condition that returns that pair or any value (its truth holds)."""
    value = condition()
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], bool):
        return value
    return bool(value), value


def _site(frame):
    return '%s:%d' % (frame.f_code.co_filename, frame.f_lineno)


def wait(name, done, terminal=None, sources=(), *, row=None, hang_bound_for_test=None, _depth=1):
    """Block until `done` holds (outcome done) or `terminal` holds (outcome impossible), waking only when
    one of `sources` fires. Past the wait hang bound the row is hung and the process ends (see the module's
    docstring). `hang_bound_for_test` replaces the bound for this module's own test; nothing else passes it.
    The sources are closed when the wait ends."""
    bound = WAIT_HANG_SECONDS if hang_bound_for_test is None else hang_bound_for_test
    caller = sys._getframe(_depth)
    where = _site(caller)
    sources = list(sources)
    if not sources:
        raise ValueError('wait %r names no event source: a wait with none could only wake on the clock'
                         % name)
    poller = select.poll()
    by_fd = {}
    timed = [s.interval for s in sources if s.interval is not None]
    for s in sources:
        fd = s.fileno()
        if fd is not None:
            poller.register(fd, s.events)
            by_fd[fd] = s
    began = time.monotonic()
    done_obs = terminal_obs = None
    try:
        while True:
            holds, done_obs = _reading(done)
            if holds:
                return Result('done', name, where, done_obs, terminal_obs, [s.describe() for s in sources],
                              bound)
            if terminal is not None:
                holds, terminal_obs = _reading(terminal)
                if holds:
                    return Result('impossible', name, where, done_obs, terminal_obs,
                                  [s.describe() for s in sources], bound)
            left = bound - (time.monotonic() - began)
            if left <= 0:
                hung(row if row is not None else next_row(caller, name), name, where,
                     'bound %d s since the wait began; last observed: done=%r, terminal=%r; sources: %s'
                     % (bound, done_obs, terminal_obs, ', '.join(s.describe() for s in sources)))
            if timed:
                left = min([left] + timed)
            for fd, _event in poller.poll(max(1, int(left * 1000) + 1)):
                s = by_fd.get(fd)
                if s is not None and not s.fired():
                    poller.unregister(fd)
                    del by_fd[fd]
    finally:
        for s in sources:
            s.close()


def wait_for(condition, bound, what, sources=None, terminal=None, _depth=2):
    """shared.wait_for's contract over wait(): None when the condition holds, else the report (when the
    terminal condition held). `bound` is the caller's former (seconds, source); it is kept in the report as
    data and bounds nothing: a wait is bounded by the wait hang bound only, and past it the row is hung."""
    seconds, origin = bound
    result = wait(what, condition, terminal,
                  sources if sources is not None else [LegacyInterval()], _depth=_depth)
    if result.done:
        return None
    return result.report() + ' (the caller once bounded this at %.1f s: %s)' % (seconds, origin)


# ------------------------------------------------------------------------------------------- the rows


def static_rows(path):
    """The row names a suite file states, in order, as (line, name): the first argument of every
    expect(...) call that is a string literal or an f-string (a formatted part reads as {}). A row's name is
    its label up to the first colon, as the mutation driver reads it."""
    try:
        with open(path, encoding='utf-8') as f:
            tree = ast.parse(f.read(), path)
    except (OSError, SyntaxError, ValueError):
        return []
    rows = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and node.args):
            continue
        func = node.func
        named = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if named != 'expect':
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            label = first.value
        elif isinstance(first, ast.JoinedStr):
            label = ''.join(v.value if isinstance(v, ast.Constant) else '{}' for v in first.values)
        else:
            continue
        rows.append((node.lineno, label.split(':', 1)[0]))
    rows.sort()
    return rows


def declared_rows(path):
    """The row names a suite file DECLARES when it emits its rows under names built at run time (most suites
    of a specification do: they collect each row's checks and state every row at their end, as
    expect(prefix + row ...)): the strings of the last assignment to the name ROWS that can be read from the
    source, where a value is a tuple or list of string literals, the name of an earlier one, or a sum of
    those. Such a row is reached when a row was stated whose last word is its name, which is how the mutation
    driver matches a row to a case's target."""
    try:
        with open(path, encoding='utf-8') as f:
            tree = ast.parse(f.read(), path)
    except (OSError, SyntaxError, ValueError):
        return []
    known = {}

    def value(node):
        if isinstance(node, (ast.Tuple, ast.List)):
            if all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
                return [e.value for e in node.elts]
            return None
        if isinstance(node, ast.Name):
            return known.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = value(node.left), value(node.right)
            return None if left is None or right is None else left + right
        return None

    assigned = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)]
    for node in sorted(assigned, key=lambda n: (n.lineno, n.col_offset)):
        found = value(node.value)
        if found is not None:
            known[node.targets[0].id] = found
        elif node.targets[0].id != 'ROWS':
            known.pop(node.targets[0].id, None)
    rows = []
    for name in known.get('ROWS') or []:
        if name not in rows:
            rows.append(name)
    return rows


def _undeclared(path, seen):
    """The declared rows of a suite file that no stated row has reached."""
    reached = {s.split()[-1] for s in seen if s.split()}
    return [name for name in declared_rows(path) if name not in reached]


def _pattern(name):
    return re.compile('^' + '.*'.join(re.escape(p) for p in name.split('{}')) + '$', re.S)


def _suite_frames(frame):
    """The frames of suite files on the stack, innermost first (not this module, not shared.py)."""
    out = []
    here = os.path.abspath(__file__)
    while frame is not None:
        f = os.path.abspath(frame.f_code.co_filename)
        if f != here and os.path.basename(f) != 'shared.py' and f.endswith('.py'):
            out.append(frame)
        frame = frame.f_back
    return out


def next_row(frame, fallback):
    """The row a blocked statement belongs to: walking outward from it, the first row stated after the
    statement inside the same function's lines. A wait inside a helper belongs to the row its caller
    asserts next."""
    for f in _suite_frames(frame):
        code = f.f_code
        lines = [ln for _, _, ln in code.co_lines() if ln is not None]
        last = max(lines) if lines else f.f_lineno
        for line, name in static_rows(code.co_filename):
            if f.f_lineno <= line <= last:
                return name
    return fallback


class _Runtime:
    """The running suite as the dispatcher states it. Active only inside scripts/selftest.py; elsewhere
    (a mutation worker execs a suite directly) the rows not reached are read from the suite file by line."""

    def __init__(self):
        self.active = False
        self.suite = None
        self.suite_file = None
        self.seen = set()
        self.later = []
        self.last_row = None
        self.watchdog = None
        self.before_exit = []  # called before a hung process ends (the opened-files record)
        self.ended_fd = None  # the keeper's pipe (keep_the_tree), in the suite process only
        self.ended_pid = None


RUNTIME = _Runtime()


def begin_suite(name, path, later=()):
    """A suite starts: a progress event. `later` is [(name, path)] of the suites after it in this run."""
    RUNTIME.active = True
    RUNTIME.suite, RUNTIME.suite_file = name, os.path.abspath(path)
    RUNTIME.seen = set()
    RUNTIME.later = list(later)
    progress('suite %s started' % name)


def row_event(label):
    """A row ended (shared.expect): a progress event, and the row is reached."""
    name = label.split(':', 1)[0] if isinstance(label, str) else repr(label)
    RUNTIME.seen.add(name)
    RUNTIME.last_row = name
    progress('row %s' % name)


def progress(what):
    if RUNTIME.watchdog is not None:
        RUNTIME.watchdog.progress(what)


def _not_run(frame):
    """Every row not reached, in order: the current suite's stated rows not yet seen and its declared rows
    (declared_rows) no stated row has reached, then every stated and declared row of each later suite."""
    out = []
    if RUNTIME.active and RUNTIME.suite_file:
        seen = RUNTIME.seen
        for _, name in static_rows(RUNTIME.suite_file):
            if '{}' in name:
                pattern = _pattern(name)
                reached = any(pattern.match(s) for s in seen)
            else:
                reached = name in seen
            if not reached and name not in out:
                out.append(name)
        out += [name for name in _undeclared(RUNTIME.suite_file, seen) if name not in out]
        for _, path in RUNTIME.later:
            for name in [n for _, n in static_rows(path)] + declared_rows(path):
                if name not in out:
                    out.append(name)
        return out
    frames = _suite_frames(frame)
    if frames:
        outer = frames[-1]
        for line, name in static_rows(outer.f_code.co_filename):
            if line > outer.f_lineno and name not in out:
                out.append(name)
        out += [name for name in _undeclared(outer.f_code.co_filename, RUNTIME.seen) if name not in out]
    return out


def _stack_file():
    directory = os.environ.get('VELDO_HANG_DIR') or tempfile.gettempdir()
    return os.path.join(directory, 'veldo-hang-%d.txt' % os.getpid())


def _write_stacks(path):
    with open(path, 'w') as f:
        faulthandler.dump_traceback(file=f, all_threads=True)
    try:
        faulthandler.dump_traceback(file=sys.__stderr__, all_threads=True)
    except (AttributeError, ValueError, OSError):
        pass


def hung(row, name, source_line, detail, frame=None):
    """A row is hung: print it, write every thread's stack, print every row not reached, end the process.
    Written straight to the process's own standard output, so a caller that redirected sys.stdout still
    shows it."""
    frame = frame or sys._getframe(1)
    path = _stack_file()
    lines = ['SELFTEST HUNG %s: wait %s at %s; %s; stacks: %s' % (row, name, source_line, detail, path)]
    try:
        _write_stacks(path)
    except OSError as e:
        lines[0] += ' (stack file not written: %s)' % e
    lines += ['SELFTEST NOT RUN %s' % r for r in _not_run(frame) if r != row]
    for hook in RUNTIME.before_exit:
        try:
            hook()
        except Exception as e:  # noqa: BLE001 - a record that cannot be written must not hide the hang
            lines.append('SELFTEST HUNG note: %r not completed: %s' % (hook, e))
    try:
        sys.stdout.flush()
    except (AttributeError, ValueError, OSError):
        pass
    os.write(1, ('\n'.join(lines) + '\n').encode('utf-8', 'replace'))
    os._exit(HUNG_EXIT_STATUS)


# ------------------------------------------------------------------------------------------ watchdog


class Watchdog:
    """The progress watchdog of a suite process (C6). It ends the process only after `bound` seconds with
    no progress event (a suite starting, a row ending), and writes every thread's stack first. It bounds
    the time between events, never the total.

    With the real clock a thread waits for the bound since the last event (it wakes once per bound, not per
    row), and the standard library's faulthandler timer, re-armed at each of that thread's wakes to one more
    bound past it, writes the stacks and exits even when the interpreter is stuck and the thread cannot run.
    With a supplied `clock` (this module's own test) there is no real timer: the time since the last event
    is judged at each event on that clock."""

    def __init__(self, bound=PROCESS_HANG_SECONDS, clock=None):
        self.bound = bound
        self.clock = clock
        self.last_what = 'start'
        self._supplied_last = clock() if clock is not None else None
        self._real_last = time.monotonic()
        self._stopped = False
        self._cond = threading.Condition()
        self._thread = None

    def start(self):
        if self.clock is None:
            faulthandler.dump_traceback_later(2 * self.bound, exit=True)
            self._thread = threading.Thread(target=self._run, name='veldo-progress-watchdog', daemon=True)
            self._thread.start()
        return self

    def progress(self, what):
        if self.clock is not None:
            now = self.clock()
            if now - self._supplied_last >= self.bound:
                self.fire(sys._getframe(1))
            self._supplied_last = now
        self._real_last = time.monotonic()
        self.last_what = what

    def _run(self):
        with self._cond:
            while not self._stopped:
                since = time.monotonic() - self._real_last
                if since >= self.bound:
                    main = sys._current_frames().get(threading.main_thread().ident)
                    self.fire(main)
                    return
                faulthandler.dump_traceback_later(2 * self.bound - since, exit=True)
                self._cond.wait(self.bound - since)

    def fire(self, frame):
        source = _site(frame) if frame is not None else 'unknown'
        row = next_row(frame, 'after %s' % (RUNTIME.last_row or 'the suite start')) if frame else 'unknown'
        hung(row, 'progress-watchdog', source,
             'no progress for %s s since %s' % (self.bound, self.last_what), frame=frame)

    def stop(self):
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
        if self.clock is None:
            faulthandler.cancel_dump_traceback_later()


def arm_watchdog(bound=PROCESS_HANG_SECONDS, clock=None):
    """Arm this process's progress watchdog, replacing any armed before. `bound` and `clock` other than the
    defaults are for this module's own test."""
    if RUNTIME.watchdog is not None:
        RUNTIME.watchdog.stop()
    RUNTIME.watchdog = Watchdog(bound, clock).start()
    return RUNTIME.watchdog


def disarm_watchdog():
    if RUNTIME.watchdog is not None:
        RUNTIME.watchdog.stop()
        RUNTIME.watchdog = None


class SuppliedClock:
    """A clock the test moves: for the watchdog's own test."""

    def __init__(self, at=0.0):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, seconds):
        self.at += seconds


# -------------------------------------------------------------------------------- the tree of a run

_PR_SET_PDEATHSIG = 1
_PR_SET_CHILD_SUBREAPER = 36
_PASSED_ON = ('SIGTERM', 'SIGHUP', 'SIGINT', 'SIGQUIT', 'SIGABRT', 'SIGUSR1', 'SIGUSR2')


def keep_the_tree():
    """Called once by the dispatcher, before it starts a thread or a suite. The calling process becomes the
    KEEPER of the run and this returns only in its child, which runs the suites.

    Why: a hung row ends its process at once (hung, or the watchdog's timer when the interpreter is stuck),
    so nothing the suite started is stopped by the suite. The keeper is what stops it. It is the child
    subreaper of the run, so a process whose parent ended (a worker whose receiver was killed, a daemon
    that forked twice, in a scope of its own or not) becomes the keeper's child and not the user manager's,
    and is reaped by it at once, as the manager would. When the suite process ends WITHOUT having said that
    it ran every suite to its end (run_ended), the keeper kills every descendant it has, reaps each one,
    names them (SELFTEST TREE), and only then ends with the suite process's own status. An orderly end
    kills nothing: what a suite leaves then is the residue row's to name.

    The keeper sleeps in sigwaitinfo: it wakes on a child's end and on a signal sent to it, which it
    passes on to the suite process. It reads no clock."""
    import signal
    sys.stdout.flush()
    sys.stderr.flush()
    told, tell = os.pipe()
    watched = {signal.SIGCHLD} | {getattr(signal, name) for name in _PASSED_ON}
    before = signal.pthread_sigmask(signal.SIG_BLOCK, watched)
    keeper = os.getpid()
    subreaper = _LIBC.prctl(_PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) == 0
    child = os.fork()
    if child == 0:
        os.close(told)
        signal.pthread_sigmask(signal.SIG_SETMASK, before)
        _LIBC.prctl(_PR_SET_PDEATHSIG, int(signal.SIGKILL), 0, 0, 0)
        if os.getppid() != keeper:  # the keeper died before that was in place
            os._exit(HUNG_EXIT_STATUS)
        RUNTIME.ended_fd, RUNTIME.ended_pid = tell, os.getpid()
        return
    os.close(tell)
    _keep(child, told, watched, subreaper)


def run_ended():
    """The dispatcher ran every suite to its end: said to the keeper, once, by the suite process only."""
    fd, RUNTIME.ended_fd = RUNTIME.ended_fd, None
    if fd is not None and RUNTIME.ended_pid == os.getpid():
        os.write(fd, b'.')
        os.close(fd)


def _reap(child=None):
    """Reap every child that has ended. (the status of `child` if it was among them, a child is left)."""
    status = None
    while True:
        try:
            pid, ended = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return status, False
        if pid == 0:
            return status, True
        if pid == child:
            status = ended


def _descendants(root):
    """[(pid, parent)] of every process whose parents lead to `root`, read from /proc."""
    parents = {}
    for name in os.listdir('/proc'):
        if name.isdigit():
            try:
                with open('/proc/%s/stat' % name) as f:
                    parents[int(name)] = int(f.read().rsplit(')', 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                continue
    below = {}
    for pid, parent in parents.items():
        below.setdefault(parent, []).append(pid)
    out, at = [], [root]
    while at:
        parent = at.pop()
        for pid in sorted(below.get(parent, ())):
            out.append((pid, parent))
            at.append(pid)
    return out


def _end_tree():
    """Kill and reap every descendant of this process: ({pid: what} ended, {pid: what} not this account's to
    signal). Each pass reaps what has ended, kills what /proc shows below this process and sleeps until a
    child ends; a process that was forked meanwhile, or whose parent was just killed, is this process's
    child by then (the subreaper) and is met by the next pass. It ends when no child is left."""
    import signal
    me = os.getpid()
    ended, refused = {}, {}
    while True:
        if not _reap()[1]:
            break
        own = False
        for pid, parent in _descendants(me):
            if pid in refused:
                continue
            what = ended.get(pid) or _describe_child(pid)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                continue
            except PermissionError:
                refused[pid] = what
                continue
            ended[pid] = what
            own = own or parent == me
        if not own:  # every child left is one this account may not signal: nothing more will end
            break
        signal.sigwaitinfo({signal.SIGCHLD})
    return ended, refused


def _keep(child, told, watched, subreaper):
    import signal
    status = None
    while status is None:
        got = signal.sigwaitinfo(watched)
        if got.si_signo == signal.SIGCHLD:
            status = _reap(child)[0]
        elif not (got.si_signo == signal.SIGINT and got.si_code > 0):  # the terminal's own reached it already
            try:
                os.kill(child, got.si_signo)
            except ProcessLookupError:
                pass
    os.set_blocking(told, False)
    try:
        orderly = os.read(told, 1) == b'.'
    except BlockingIOError:
        orderly = False
    if not orderly:
        ended, refused = _end_tree()
        lines = ['SELFTEST TREE ended and reaped: %s' % what for _, what in sorted(ended.items())]
        lines += ['SELFTEST TREE NOT ENDED (not this account\'s to signal): %s' % what
                  for _, what in sorted(refused.items())]
        if ended or refused:
            lines.append('SELFTEST TREE: the run ended without finishing; %d process(es) it left were killed '
                         'and reaped%s%s' % (len(ended), ', %d could not be' % len(refused) if refused else '',
                                             '' if subreaper else ' (no child subreaper here: a process '
                                             'whose parent had ended before was not this run\'s to find)'))
            os.write(1, ('\n'.join(lines) + '\n').encode('utf-8', 'replace'))
    if os.WIFSIGNALED(status):
        number = os.WTERMSIG(status)
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            signal.signal(number, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK, {number})
            os.kill(os.getpid(), number)
        except (OSError, ValueError):
            pass
        os._exit(128 + number)
    os._exit(os.WEXITSTATUS(status))


# ------------------------------------------------------------------------------------------- residue


def _children():
    out = set()
    try:
        tasks = os.listdir('/proc/self/task')
    except OSError:
        return out
    for tid in tasks:
        try:
            with open('/proc/self/task/%s/children' % tid) as f:
                out.update(int(p) for p in f.read().split())
        except OSError:
            continue
    return out


def _listening_inodes():
    found = {}
    for proto in ('tcp', 'tcp6'):
        try:
            with open('/proc/net/' + proto) as f:
                next(f)
                for line in f:
                    parts = line.split()
                    if len(parts) > 9 and parts[3] == '0A':
                        found[parts[9]] = '%s %s' % (proto, parts[1])
        except (OSError, StopIteration):
            continue
    try:
        with open('/proc/net/unix') as f:
            next(f)
            for line in f:
                parts = line.split()
                if len(parts) >= 7 and int(parts[3], 16) & 0x10000:
                    found[parts[6]] = 'unix %s' % (parts[7] if len(parts) > 7 else '(unnamed)')
    except (OSError, StopIteration):
        pass
    mine = {}
    for fd in os.listdir('/proc/self/fd'):
        try:
            target = os.readlink('/proc/self/fd/' + fd)
        except OSError:
            continue
        if target.startswith('socket:['):
            inode = target[8:-1]
            if inode in found:
                mine[inode] = found[inode]
    return mine


def residue_snapshot():
    """What exists before a suite starts, so that only what the suite left is named after it."""
    own = RUNTIME.watchdog._thread if RUNTIME.watchdog is not None else None
    return {'threads': {t.ident for t in threading.enumerate()} | ({own.ident} if own else set()),
            'children': _children(), 'listeners': set(_listening_inodes())}


def _describe_child(pid):
    try:
        with open('/proc/%d/stat' % pid) as f:
            state = f.read().rsplit(')', 1)[1].split()[0]
    except OSError:
        state = '?'
    try:
        with open('/proc/%d/cmdline' % pid, 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
    except OSError:
        cmd = ''
    return 'child %d (%s%s)' % (pid, 'not reaped' if state == 'Z' else 'running, state ' + state,
                                ': ' + ' '.join(cmd.split())[:120] if cmd else '')


def residue(before):
    """Every thread still alive, child process not reaped and listening socket still open that was not
    there in `before`, each named."""
    import subprocess
    cleanup = getattr(subprocess, '_cleanup', None)
    if cleanup is not None:
        cleanup()  # Popen objects already dropped are the interpreter's to reap; it does so now
    left = []
    own = RUNTIME.watchdog._thread if RUNTIME.watchdog is not None else None
    for t in threading.enumerate():
        if t.ident not in before['threads'] and t is not own and t.is_alive():
            left.append('thread %r alive (%s)' % (t.name, type(t).__name__))
    for pid in sorted(_children() - before['children']):
        left.append(_describe_child(pid))
    for inode, what in sorted(_listening_inodes().items()):
        if inode not in before['listeners']:
            left.append('listening socket %s' % what)
    return left


# -------------------------------------------------------------------------------------- heavy children


class HeavyResult:
    def __init__(self, returncode, stdout, stderr, hung):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.hung = hung


def run_heavy(cmd, kind, *, hang_bound_for_test=None, text=True, **popen):
    """Run a heavy child (one of HEAVY_CHILDREN) to its end, with no bound on its total time: it is ended
    only after the process hang bound passes with no output from it (each chunk it writes re-arms the
    bound). Ending it sends SIGABRT first, so a Python child run with -X faulthandler writes every thread's
    stack, and SIGKILL only if it is still there one wait hang bound later. The result says hung; the caller
    reports it red. `hang_bound_for_test` is for this module's own test."""
    import signal
    import subprocess
    if kind not in HEAVY_CHILDREN:
        raise ValueError('%r is not a heavy child (%s)' % (kind, ', '.join(HEAVY_CHILDREN)))
    bound = PROCESS_HANG_SECONDS if hang_bound_for_test is None else hang_bound_for_test
    popen.setdefault('stdin', subprocess.DEVNULL)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **popen)
    out_fd, err_fd = proc.stdout.fileno(), proc.stderr.fileno()
    chunks = {out_fd: [], err_fd: []}
    pidfd = os.pidfd_open(proc.pid)
    poller = select.poll()
    for fd in chunks:
        poller.register(fd, select.POLLIN)
    poller.register(pidfd, select.POLLIN)
    open_fds = set(chunks)
    exited = False
    hung_now = False
    last = time.monotonic()
    try:
        while open_fds or not exited:
            left = bound - (time.monotonic() - last)
            if left <= 0:
                if hung_now:
                    proc.kill()
                    break
                hung_now = True
                proc.send_signal(signal.SIGABRT)
                bound, last = WAIT_HANG_SECONDS, time.monotonic()
                continue
            for fd, _event in poller.poll(max(1, int(left * 1000) + 1)):
                if fd == pidfd:
                    exited = True
                    poller.unregister(pidfd)
                    continue
                data = os.read(fd, 65536)
                if data:
                    chunks[fd].append(data)
                    if not hung_now:
                        last = time.monotonic()
                else:
                    poller.unregister(fd)
                    open_fds.discard(fd)
    finally:
        os.close(pidfd)
        proc.stdout.close()
        proc.stderr.close()
    code = proc.wait()
    out, err = b''.join(chunks[out_fd]), b''.join(chunks[err_fd])
    if text:
        out, err = out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace')
    return HeavyResult(code, out, err, hung_now)
