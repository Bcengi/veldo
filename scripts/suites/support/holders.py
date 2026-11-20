"""Latch holders (VELDO-0358, C3): a fixture process that must stay alive, without a sleep.

A holder blocks reading a pipe whose only write end the test holds. It ends when the test releases it
(closes that end) and, because the kernel closes every descriptor of a process that dies, when the test's
process dies for any reason. Nothing in it counts time, so a busy machine cannot end it early or keep it
past its test.

    holder = Holder()              # alive until released or until this process dies
    holder.pid
    holder.release()
    holder.ended()                 # waits.Result: done on its exit (its pidfd)

A holder that would also see the write end can never see it closed. ended() treats that as its terminal
condition: the wait is impossible at once, with the holder's own descriptors as the evidence.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)
import waits  # noqa: E402

# The holder's program: read the latch until end of file, then exit. argv[1] is the latch's read end.
HOLDER_SOURCE = (
    "import os, sys\n"
    "fd = int(sys.argv[1])\n"
    "while os.read(fd, 4096):\n"
    "    pass\n"
)

# For a shell fixture: block on descriptor 3 until its writer closes it (pass the latch as fd 3).
SHELL_LATCH = 'read -r _ <&3'


def _write_ends(pid, inode):
    """The descriptors of `pid` that are a write end of the pipe `inode`."""
    found = []
    try:
        fds = os.listdir('/proc/%d/fd' % pid)
    except OSError:
        return found
    for fd in fds:
        try:
            if os.readlink('/proc/%d/fd/%s' % (pid, fd)) != 'pipe:[%d]' % inode:
                continue
            with open('/proc/%d/fdinfo/%s' % (pid, fd)) as f:
                flags = next(int(line.split()[1], 8) for line in f if line.startswith('flags:'))
        except (OSError, StopIteration):
            continue
        if (flags & os.O_ACCMODE) == os.O_WRONLY:
            found.append(int(fd))
    return found


class Holder:
    """A latch-held process: `argv` (default: the holder program above) is run with the latch's read end
    as its last argument, or as descriptor 3 when shell is True."""

    def __init__(self, argv=None, shell=False, **popen):
        # A holder writes nothing and reads nothing but its latch, so it inherits no stream of its test: a
        # holder that outlived its test must not keep the test runner's output pipe open as well.
        for stream in ('stdin', 'stdout', 'stderr'):
            popen.setdefault(stream, subprocess.DEVNULL)
        read, self._write = os.pipe()
        self.inode = os.fstat(read).st_ino
        if shell:
            command = argv if argv is not None else SHELL_LATCH
            self.proc = subprocess.Popen(['sh', '-c', 'exec 3<&%d; %s' % (read, command)],
                                         pass_fds=[read], **popen)
        else:
            base = list(argv) if argv is not None else [sys.executable, '-c', HOLDER_SOURCE]
            self.proc = subprocess.Popen(base + [str(read)], pass_fds=[read], **popen)
        os.close(read)
        self.pid = self.proc.pid

    def release(self):
        if self._write is not None:
            os.close(self._write)
            self._write = None

    def ended(self, name=None, **kw):
        """Wait for the holder's exit on its pidfd, and reap it."""
        def gone():
            code = self.proc.poll()
            return code is not None, {'exit': code}

        def blind():
            ends = _write_ends(self.pid, self.inode)
            return bool(ends), {'holder_write_ends': ends}
        result = waits.wait(name or 'holder %d to end' % self.pid, gone, blind,
                            [waits.Pidfd(self.proc)], _depth=2, **kw)
        return result

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait()
