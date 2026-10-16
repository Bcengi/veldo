"""Apple command boundary for VELDO-0124. Tool errors mean unknown, never empty.

launchctl loads one non restarting LaunchAgent in the user/<uid> bootstrap domain.
That domain exists without a console login and on macOS 26 refuses (EIO) any job
not limited to the Background session type; gui/<uid> takes only Aqua jobs.
launchd gives each job its own resource coalition, and every descendant stays in it
across setsid, setpgid and reparenting to launchd (observed on macOS 26.5.1; kqueue
NOTE_TRACK is ENOTSUP there). libproc coalition membership is the job's process tree.
kqueue NOTE_EXIT observes the held wrapper before release. Helpers that launchd
spawns as separate jobs for a descendant (XPC services, the Simulator) are in their
own coalitions; that escape matrix and PID reuse are Release 2.
"""
import ctypes
import os
from pathlib import Path
import plistlib
import select
import signal
import socket
import subprocess
import sys
import time
import threading

ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C', 'TZ': 'UTC'}


def command(argv):
    result = subprocess.run(argv, env=ENV, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=5)
    if result.returncode:
        raise OSError('macos_tool_failed:' + Path(argv[0]).name)
    return result.stdout.strip()


def identity(pid):
    start = command(['/bin/ps', '-o', 'lstart=', '-p', str(pid)])
    if not start:
        raise OSError('process_identity_unreadable')
    return dict(platform='darwin', host=socket.gethostname(), pid=pid, start=start,
                boot_id=command(['/usr/sbin/sysctl', '-n', 'kern.boottime']))


PROC_PIDTBSDINFO, PROC_PIDCOALITIONINFO, SZOMB = 3, 20, 5
BSDINFO_BYTES, COALITION_BYTES = 136, 40


def _libproc():
    return ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)


def coalition(pid, library=None):
    """Resource coalition id of pid; struct proc_pidcoalitioninfo starts with it."""
    library = library or _libproc()
    info = (ctypes.c_uint64 * (COALITION_BYTES // 8))()
    if library.proc_pidinfo(pid, PROC_PIDCOALITIONINFO, ctypes.c_uint64(0), info, COALITION_BYTES) != COALITION_BYTES:
        raise OSError('coalition_unreadable')
    return int(info[0])


def live_members(entries, wanted):
    """entries: (pid, coalition, status). Zombies have exited and cannot write files."""
    return sorted(pid for pid, group, status in entries if group == wanted and status != SZOMB)


def coalition_members(wanted):
    library = _libproc()
    count = library.proc_listallpids(None, 0)
    if count <= 0:
        raise OSError('process_table_unreadable')
    pids = (ctypes.c_int * (count + 256))()
    count = library.proc_listallpids(pids, ctypes.sizeof(pids))
    if count <= 0:
        raise OSError('process_table_unreadable')
    entries = []
    for pid in pids[:count]:
        try:
            group = coalition(pid, library)
        except OSError:
            continue  # exited between listing and lookup
        info = (ctypes.c_uint32 * (BSDINFO_BYTES // 4))()
        status = SZOMB if library.proc_pidinfo(pid, PROC_PIDTBSDINFO, ctypes.c_uint64(0), info,
                                               BSDINFO_BYTES) != BSDINFO_BYTES else info[1]
        entries.append((pid, group, status))
    return live_members(entries, wanted)


def wait_file(path, seconds):
    """Watch the parent before checking the file, closing the rename/wait race."""
    deadline = time.monotonic() + max(0, seconds)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        with select.kqueue() as queue:
            queue.control([select.kevent(descriptor, filter=select.KQ_FILTER_VNODE,
                flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                fflags=select.KQ_NOTE_WRITE)], 0, 0)
            while not path.exists():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                events = queue.control(None, 1, remaining)
                if any(event.flags & select.KQ_EV_ERROR for event in events):
                    raise OSError('file_notification_failed')
            return True
    finally:
        os.close(descriptor)


def wait_members(pids, seconds):
    """Wait for an observed descendant exit or the next shutdown deadline."""
    with select.kqueue() as queue:
        for pid in pids:
            try:
                queue.control([select.kevent(pid, filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                    fflags=select.KQ_NOTE_EXIT)], 0, 0)
            except ProcessLookupError:
                return  # Exit raced registration; rescan the coalition.
        events = queue.control(None, 1, max(0, seconds))
        if any(event.flags & select.KQ_EV_ERROR for event in events):
            raise OSError('exit_notification_failed')


class ExitWatch:
    """A process exit plus a pipe wake, using Python 3.11's kqueue filters."""
    def __init__(self, pid):
        self.lock = threading.Lock()
        self.closed = False
        self.reader = self.writer = -1
        self.queue = select.kqueue()
        try:
            self.reader, self.writer = os.pipe()
            os.set_blocking(self.reader, False)
            os.set_blocking(self.writer, False)
            self.queue.control([
                select.kevent(pid, filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT, fflags=select.KQ_NOTE_EXIT),
                select.kevent(self.reader, filter=select.KQ_FILTER_READ,
                    flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR)], 0, 0)
        except BaseException:
            self.close()
            raise

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            try:
                self.queue.close()
            finally:
                for descriptor in (self.reader, self.writer):
                    if descriptor >= 0:
                        os.close(descriptor)

    def wake(self):
        # The lifetime lock covers the write, so close cannot recycle its fd.
        with self.lock:
            if self.closed:
                return
            try:
                os.write(self.writer, b'x')
            except BlockingIOError:
                pass  # An unread wake already exists.


class Native:
    wait_file = staticmethod(wait_file)
    monotonic = staticmethod(time.monotonic)
    wall = staticmethod(time.time)
    sleep = staticmethod(time.sleep)

    def facts(self):
        return dict(platform=sys.platform, host=socket.gethostname(),
                    os_version=command(['/usr/bin/sw_vers', '-productVersion']) if sys.platform == 'darwin' else '',
                    boot_id=command(['/usr/sbin/sysctl', '-n', 'kern.boottime']) if sys.platform == 'darwin' else '',
                    tools=sys.platform == 'darwin' and hasattr(select, 'kqueue') and all(
                        os.access(p, os.X_OK) for p in ('/bin/launchctl', '/usr/bin/sandbox-exec', '/bin/ps')))

    def bootstrap(self, label, argv, directory, grace):
        path = directory / (label + '.plist')
        data = dict(Label=label, ProgramArguments=argv, RunAtLoad=True, KeepAlive=False,
                    LimitLoadToSessionType='Background',
                    AbandonProcessGroup=False, ExitTimeOut=max(1, int(grace + 0.999)),
                    WorkingDirectory=str(directory), EnvironmentVariables=ENV,
                    StandardOutPath=str(directory / 'wrapper.out'), StandardErrorPath=str(directory / 'wrapper.err'))
        path.write_bytes(plistlib.dumps(data))
        command(['/bin/launchctl', 'bootstrap', 'user/%d' % os.getuid(), str(path)])

    def bootout(self, label):
        command(['/bin/launchctl', 'bootout', 'user/%d/%s' % (os.getuid(), label)])

    def user_temp(self):
        # _CS_DARWIN_USER_TEMP_DIR from <unistd.h>; Python has no name for it.
        return os.confstr(65537)

    def interpreter(self, path):
        """(major, minor) of the pinned interpreter, or None if it cannot run."""
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return None
        try:
            text = command([path, '-I', '-c', 'import sys; print("%d %d" % sys.version_info[:2])'])
            return tuple(int(v) for v in text.split())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None

    def coalition(self, pid):
        return coalition(pid)

    def members(self, group):
        return coalition_members(group)

    def alive(self, process):
        try:
            return identity(process['pid']) == process
        except OSError:
            return False

    def watch(self, process):
        if identity(process['pid']) != process:
            raise OSError('process_identity_changed')
        return ExitWatch(process['pid'])

    def wake(self, watch):
        # Pipe readiness interrupts a blocking wait when stop shortens its deadline.
        watch.wake()

    def exited(self, watch, seconds):
        events = watch.queue.control(None, 2, max(0, seconds))
        if any(e.flags & select.KQ_EV_ERROR for e in events):
            raise OSError('exit_notification_failed')
        if any(e.filter == select.KQ_FILTER_READ for e in events):
            try:
                os.read(watch.reader, 65536)
            except BlockingIOError:
                pass
        return any(e.filter == select.KQ_FILTER_PROC and e.fflags & select.KQ_NOTE_EXIT for e in events)

    def send(self, pid, number, *, group=False):
        try:
            (os.killpg if group else os.kill)(pid, number)
        except ProcessLookupError:
            pass

    def check_clone(self, clone, source):
        for kind in ('commit', 'tree'):
            observed = command(['/usr/bin/git', '-C', clone, 'rev-parse', 'HEAD^{%s}' % kind])
            if observed != source[kind]:
                raise ValueError('binding_mismatch:clone_' + kind)
        if command(['/usr/bin/git', '-C', clone, 'status', '--porcelain', '--untracked-files=all']):
            raise ValueError('binding_mismatch:clone_dirty')
