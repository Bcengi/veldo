"""VELDO-0344: the process reader.

Run: python3 scripts/selftest.py --suite 141_veldo_0344_process_reader

Only shared ROOT and expect are consumed. The probe, the declarations reader and Signal are loaded by
path. The reader is built from its source with /usr/bin/cc and run for real, without its capability:
a suite has no root, so it cannot install the file capability. What a row cannot have without root it
gives the probe through the probe's seam, SEAM['reader']: the file's owner, group and mode, the folders'
owners, the capability attribute and the capability lines of the writer's status. Everything else is
real: the processes (python children, each ending when its input closes; "undumpable" ones call
prctl(PR_SET_DUMPABLE, 0), which is what makes a process of the owner's unreadable to the probe), their
threads with a file system state or a descriptor table of their own (tasks a small C program the suite
builds starts with clone(2), sharing the address space and the thread group but not that one thing; no
unshare call, which the gate's confinement refuses), a unix socket the suite
listens on the way the socket unit does (one program started per connection, the connection its
standard output), the kernel's SO_PASSCRED and SO_PASSPIDFD records of who wrote each part, and the
pidfd looks.

THE STAND-IN is a program the suite writes: it speaks the reader's protocol and prints the table the
row composed from the real numbers of the row's own files (os.stat). It is what a row uses wherever
the real reader would need its capability. "A table that shows the process elsewhere" is such a table
with a whole block for the row's process and facts outside the item: a table with no block for it
would leave the process unread and counted by the bound, so it could never make an item read free.

WHAT COUNTS. Rows on the host's own process table read one process's part of the answer, because other
processes of the host are judged too: `counted` is user when the answer names the process as a user,
bound when it lists it unread with a reach, and None when it does not count. Rows on a fixture process
table (AC3) read the whole answer, in_use.

AC1 rows: ac1/absent, ac1/not-regular, ac1/owner, ac1/mode, ac1/folder, ac1/capability,
ac1/capability-exact (cap_dac_read_search added), ac1/capability-root-id (version 3 with another root
id), ac1/no-pin, ac1/digest (a program that prints a table showing the process elsewhere, in the
reader's place), ac1/no-socket, ac1/writer (the writer check left real: a stand-in that holds no
capability and is not locked), ac1/writer-gone (the stand-in ends after its end line and the row
answers the status read as a locked reader's: the pidfd refuses it), ac1/bytes-before-the-byte (a
wrapper writes a table and then executes the built reader with its output on a socket pair; a stand-in
that sends its table without waiting), ac1/second-writer, ac1/header-cap (a header that says cap=0, from
the stand-in and from the built reader served on the socket), ac1/reader-locks-first (the built reader:
its status shows NoNewPrivs 1 and Seccomp 2 when its header arrives, and nothing follows the header
until the byte is sent), ac1/used.

AC2 rows: ac2/cwd, ac2/open-file-only, ac2/directory-descriptor, ac2/mapped-only,
ac2/second-thread-cwd, ac2/second-thread-descriptor, ac2/inode-alone, ac2/outside-not-counted, and on
the built reader's own output for a process it may read: reader/facts-of-every-thread, reader/maps.

The run label (the change of 2026-11-14: the reader reads the label too). reader/label, on the built
reader's own output for processes it may read: a process started with the run label variable has an
l line with its value, in hexadecimal, for each of its tasks, and nothing else of its environment is
anywhere in the output, neither a secret the row planted nor two variables whose names only begin or
end like the label's; a process with no such variable has l -; an empty value is read as empty; a
value of 64 bytes is read and one of 65 is not printed, in part or whole, and leaves the label unread;
the name in the source is the one the Docker adapter and the CLI give a run, and the source names no
other variable. label/table, on the probe's reading of a table: the label of a block is the values
its tasks carry, each once; an empty list only when the environment was read and holds none; not read
(None) for a block with an x env line, with no l line, closed with g, or opened twice; an x env line
leaves the block whole, so rule 4 still reads its files; an l line in no task or outside the format
makes the whole table unused.

A whole read (the fix of 2026-11-15, the review's finding 1). reader/whole-read, on the built reader's
own output for three real processes of a small static program the row builds: one that carries the
run label and executes itself again without end, read 150 times, never has l - and has its label
whenever its environment was read; one whose environment ends in memory it has unmapped, the label in
that part, has x env 11 and no l line; and one started with an environment of no bytes has x env 11
and no l line. Not read is what the probe makes of each. The source takes the task's stat and exe
before the read and after it, and reads the environment twice at most.

The same program before and after (the review of the fix, finding 1). reader/same-program: a task of
the row's helper that shares its parent's memory waits on a fifo and then executes the helper with the
run label as its whole environment; the built reader runs under strace, which holds its read of that
one environ entry back, and the row lets the task execute when strace shows the open. The kernel then
returns the parent's environment, which has no label and is as long as the ends taken before are
apart; the reader does not take it for the task's, reads once more and writes the task's own label.
The row is added only where strace is on /usr/bin:/bin; elsewhere a SELFTEST SKIP line says so.

A rewritten environment (the limit VELDO-0313 records). reader/rewritten-environment: a process started
with the run label that writes over its environment area, as a program that sets its process title
does, with its working directory in the item and a file of the item open: the reader writes l - (the
label is lost) and its block is whole and names the working directory and the open file by inode.

AC3 rows: ac3/root-login (in the item, and elsewhere), ac3/unread-fact, ac3/no-block-or-start,
ac3/unlistable-folder.

AC4 rows: ac4/no-argument, ac4/format, ac4/entries (the entries the source opens), ac4/filter (patched
copies of the reader that make one forbidden call after the filter is in place, each ended by the
kernel; one that makes an allowed call exits normally), ac4/unread-without-capability.

AC5 rows: ac5/cut (a table cut before a block), ac5/not-whole (no end line, another count, a line
outside the format, bytes after the end line, a line in no block), ac5/exit-status, ac5/failed-write
(the built reader on a standard output that refuses a large write), ac5/waits-after-end (the built
reader, read to its end line, is still alive until the row shuts down its side).

AC6 rows: ac6/units, ac6/reads-through-the-socket, ac6/executes-the-checked-descriptor,
ac6/refused-executes-nothing, ac6/reader-units, and ac6/installed, which runs only where the reader is
installed at its fixed path (the owner's host after docs/veldo-procread-setup.txt) and requires the
check's six PASS lines, the fifth being a whole block for process 1, root's and closed to the probe
itself, and the sixth the run label of a process whose environment the probe may not read: elsewhere it prints a SELFTEST SKIP line that says which condition skipped it (no reader, or a
reader and no systemd-run) and adds no row.

AC7 rows: ac7/reproducible, ac7/recorded-digest, ac7/compiler-not-from-path, ac7/setcap-after-digest,
ac7/no-replace-objects, ac7/digest-from-the-review-record.

AC8 rows: ac8/second-thread-cwd, ac8/second-thread-descriptor, ac8/unreadable-task.

Others: config/process-reader (the installation's key), signal/deferral-names-the-reader, reader/canon.
"""


def _v344_process_reader_suite():
    import hashlib
    import importlib.util
    import os
    import re
    import shutil
    import signal
    import socket
    import stat
    import struct
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
        'control_space_config.py': ROOT / ".veldo" / "control_space_config.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'veldo_procread.c': ROOT / "scripts" / "veldo_procread.c",
        'veldo-procread-setup.txt': ROOT / "docs" / "veldo-procread-setup.txt",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/absent', 'ac1/not-regular', 'ac1/owner', 'ac1/mode', 'ac1/folder', 'ac1/capability',
            'ac1/capability-exact', 'ac1/capability-root-id', 'ac1/no-pin', 'ac1/digest', 'ac1/no-socket',
            'ac1/writer', 'ac1/writer-gone', 'ac1/bytes-before-the-byte', 'ac1/second-writer', 'ac1/header-cap',
            'ac1/reader-locks-first', 'ac1/used',
            'ac2/cwd', 'ac2/open-file-only', 'ac2/directory-descriptor', 'ac2/mapped-only',
            'ac2/second-thread-cwd', 'ac2/second-thread-descriptor', 'ac2/inode-alone', 'ac2/outside-not-counted',
            'reader/facts-of-every-thread', 'reader/maps', 'reader/label', 'reader/whole-read', 'reader/rewritten-environment',
            'label/table',
            'ac3/root-login', 'ac3/unread-fact', 'ac3/no-block-or-start', 'ac3/unlistable-folder',
            'ac4/no-argument', 'ac4/format', 'ac4/entries', 'ac4/filter', 'ac4/unread-without-capability',
            'ac5/cut', 'ac5/not-whole', 'ac5/exit-status', 'ac5/failed-write', 'ac5/waits-after-end',
            'ac6/units', 'ac6/reads-through-the-socket', 'ac6/executes-the-checked-descriptor',
            'ac6/refused-executes-nothing', 'ac6/reader-units',
            'ac7/reproducible', 'ac7/recorded-digest', 'ac7/compiler-not-from-path', 'ac7/setcap-after-digest',
            'ac7/no-replace-objects', 'ac7/digest-from-the-review-record',
            'ac8/second-thread-cwd', 'ac8/second-thread-descriptor', 'ac8/unreadable-task',
            'config/process-reader', 'signal/deferral-names-the-reader', 'reader/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    ME = os.geteuid()
    PTRACE = 1 << 19
    CAP_V2 = struct.pack('<5I', 0x02000001, PTRACE, 0, 0, 0)
    BUILD = ['/usr/bin/cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static']

    # A live process: python that holds what its row asks for, says ready with the ids of the threads it
    # started, and ends when its input closes.
    CHILD = r'''
import ctypes, mmap, os, sys
libc = ctypes.CDLL(None, use_errno=True)
spec = dict(pair.split('=', 1) for pair in sys.argv[1:])
keep = []
if 'open' in spec:
    keep.append(open(spec['open'], 'rb'))
if 'dirfd' in spec:
    keep.append(os.open(spec['dirfd'], os.O_RDONLY | os.O_DIRECTORY))
if 'map' in spec:
    with open(spec['map'], 'rb') as mapped:
        keep.append(mmap.mmap(mapped.fileno(), 0, prot=mmap.PROT_READ))
if spec.get('dumpable') == '0':
    libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE: the probe may not read this process any more
print('ready', flush=True)
sys.stdin.read()
'''

    # The same live process with threads, as a C program: each thread is a task started with clone(2) in
    # the same address space and thread group (CLONE_VM, CLONE_SIGHAND, CLONE_THREAD), which leaves out
    # CLONE_FS (thread_cwd: a file system state of its own, where it changes directory) or CLONE_FILES
    # (thread_open: a descriptor table of its own, where it opens the file). The kernel gives such a task
    # its own copy at its start, so nothing calls unshare, which the gate's confinement refuses. A thread
    # that cannot do its part ends the program before it says ready. The order is the python child's: the
    # map (its descriptor kept open, as python keeps one), the threads, then undumpable.
    THREADS = r'''
#define _GNU_SOURCE
#include <fcntl.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

struct task { const char *path; int own_files; volatile int said; };

static int run(void *given)
{
    struct task *task = given;
    int failed = task->own_files ? open(task->path, O_RDONLY) < 0 : chdir(task->path) != 0;
    task->said = failed ? -1 : (int)syscall(SYS_gettid);
    for (;;)
        pause();
    return 0;
}

static int start(const char *path, int own_files)
{
    static struct task tasks[2];
    static int count;
    struct task *task = &tasks[count++];
    const size_t size = 1 << 20;
    const struct timespec nap = {0, 1000000};
    char *stack = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_STACK, -1, 0);
    int waited = 0;
    if (stack == MAP_FAILED)
        return -1;
    task->path = path;
    task->own_files = own_files;
    task->said = 0;
    if (clone(run, stack + size, CLONE_VM | CLONE_SIGHAND | CLONE_THREAD | (own_files ? CLONE_FS : CLONE_FILES),
              task) < 0)
        return -1;
    while (task->said == 0 && waited++ < 20000)
        nanosleep(&nap, NULL);
    return task->said > 0 ? task->said : -1;
}

int main(int argc, char **argv)
{
    const char *thread_cwd = NULL, *thread_open = NULL, *map = NULL;
    int undumpable = 0, tids[2], count = 0, at;
    char byte;
    for (at = 1; at < argc; at++) {
        if (!strncmp(argv[at], "thread_cwd=", 11))
            thread_cwd = argv[at] + 11;
        else if (!strncmp(argv[at], "thread_open=", 12))
            thread_open = argv[at] + 12;
        else if (!strncmp(argv[at], "map=", 4))
            map = argv[at] + 4;
        else if (!strcmp(argv[at], "dumpable=0"))
            undumpable = 1;
        else
            return 2;
    }
    if (map) {
        struct stat found;
        int descriptor = open(map, O_RDONLY);
        if (descriptor < 0 || fstat(descriptor, &found) != 0
            || mmap(NULL, (size_t)found.st_size, PROT_READ, MAP_SHARED, descriptor, 0) == MAP_FAILED)
            return 3;
    }
    if (thread_cwd && (tids[count++] = start(thread_cwd, 0)) < 0)
        return 4;
    if (thread_open && (tids[count++] = start(thread_open, 1)) < 0)
        return 5;
    if (undumpable && prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0)
        return 6;
    printf("ready");
    for (at = 0; at < count; at++)
        printf(" %d", tids[at]);
    printf("\n");
    fflush(stdout);
    while (read(0, &byte, 1) > 0)
        ;
    return 0;
}
'''

    # The stand-in: the reader's protocol, with the table the row wrote to a file.
    STANDIN = r'''
import os, socket, sys
mode = sys.argv[1]
with open(sys.argv[2], 'rb') as given:
    table = given.read()
header = b'veldo-procread 1 cap=0\n' if mode == 'cap0' else b'veldo-procread 1 cap=1\n'
def out(data):
    while data:
        data = data[os.write(1, data):]
if mode == 'direct':
    out(header + table)
    sys.exit(0)
if mode == 'early-one-write':
    out(header + table)
elif mode == 'early':
    out(header)
    out(table)
else:
    out(header)
try:
    os.read(1, 1)
except OSError:
    pass
if mode == 'second-writer':
    if os.fork() == 0:
        out(table)
        os._exit(0)
    os.wait()
elif mode not in ('early', 'early-one-write'):
    out(table)
if mode == 'exit-after-table':
    os._exit(0)
if mode == 'cut':
    socket.socket(fileno=os.dup(1)).shutdown(socket.SHUT_WR)  # the output ends; the writer stays
try:
    while os.read(1, 4096):
        pass
except OSError:
    pass
if mode == 'trailing':
    out(b'p 1 1\n')
'''

    # The wrapper of ac1/bytes-before-the-byte: it writes a header and a table to the connection, moves
    # its standard output to a socket pair and executes the real reader in its own place. A helper it
    # forked keeps the connection open and closes it when the probe shuts down its side.
    WRAPPER = r'''
import os, socket, sys
with open(sys.argv[2], 'rb') as given:
    os.write(1, b'veldo-procread 1 cap=1\n' + given.read())
mine, other = socket.socketpair()
if os.fork() == 0:
    mine.close()
    other.close()
    try:
        while os.read(1, 4096):
            pass
    except OSError:
        pass
    os._exit(0)
os.dup2(mine.fileno(), 1)
os.set_inheritable(other.fileno(), True)  # the other end stays open, so the reader waits on its read
os.execv(sys.argv[1], ['veldo-procread'])
'''

    # The driver of the unit's entry: the probe's reader_exec under a seam, in a process of its own.
    DRIVER = r'''
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location('v344_exec_probe', sys.argv[1])
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
path, other, pin, attribute, act = sys.argv[2:7]
def swap():
    os.replace(other, path)
P.SEAM['reader'] = {'path': path, 'pin': pin, 'file': lambda found: (0, os.getgid(), 0o750),
                    'folder': lambda where, found: (0, 0o755), 'capability': lambda descriptor: bytes.fromhex(attribute),
                    'before_exec': swap if act == 'swap' else None}
sys.exit(P.reader_exec())
'''

    children, spawned, threads_program = [], [], []

    def child(cwd, environ=None, **spec):
        """(the process, the ids of the threads it started). `environ`, when given, is its whole
        environment. A process with threads is the C program, built at its first use; any other is python."""
        program = [sys.executable, '-c', CHILD]
        if any(name.startswith('thread_') for name in spec):
            if not threads_program:
                folder = Path(tempfile.mkdtemp(prefix='threads-', dir=str(temporary)))
                (folder / 'threads.c').write_text(THREADS)
                built = subprocess.run(BUILD + ['-o', 'threads', 'threads.c'], cwd=str(folder),
                                       env={'PATH': '/usr/bin:/bin', 'TMPDIR': str(folder)}, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
                if built.returncode:
                    raise RuntimeError('the threads program was not built: ' + built.stderr.decode()[-400:])
                threads_program.append(str(folder / 'threads'))
            program = threads_program[:]
        process = subprocess.Popen(program + ['%s=%s' % pair for pair in spec.items()],
                                   cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=environ)
        children.append(process)
        said = process.stdout.readline().split()
        if said[:1] != [b'ready']:
            raise RuntimeError('the child did not start')
        return process, [int(tid) for tid in said[1:]]

    def stop(process):
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()

    def numbers(path):
        found = os.stat(path)
        return '%d:%d' % (os.major(found.st_dev), os.minor(found.st_dev)), found.st_ino

    temporary = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0344-')))
    listener = None
    closed = []
    try:
        P = load('v344_control_space_probe', PRODUCTION['control_space_probe.py'])
        P.READER_SECONDS = 20
        source = PRODUCTION['veldo_procread.c'].read_text()
        setup = PRODUCTION['veldo-procread-setup.txt'].read_text()

        def build(text, flags=()):
            folder = Path(tempfile.mkdtemp(prefix='build-', dir=str(temporary)))
            (folder / 'veldo_procread.c').write_text(text)
            done = subprocess.run(BUILD + list(flags) + ['-ffile-prefix-map=%s=.' % folder, '-o', 'veldo-procread',
                                                         'veldo_procread.c'],
                                  cwd=str(folder), env={'PATH': '/usr/bin:/bin', 'TMPDIR': str(folder)}, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if done.returncode:
                raise RuntimeError('the build failed: ' + done.stderr.decode()[-400:])
            return folder / 'veldo-procread'

        def digest(path):
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()

        reader = build(source)

        def run_reader(binary=None, argv=()):
            return subprocess.run([str(binary or reader)] + list(argv), stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}, timeout=300)

        elsewhere = temporary / 'elsewhere'
        elsewhere.mkdir()
        item = temporary / 'item'
        (item / 'inner').mkdir(parents=True)
        (item / 'inner' / 'held.txt').write_text('held\n')
        (item / 'inner' / 'mapped.bin').write_bytes(b'm' * 8192)
        other_item = temporary / 'other-item'
        other_item.mkdir()

        # The socket, served the way the socket unit serves it: one program per connection, the
        # connection its standard output.
        standin = temporary / 'standin.py'
        standin.write_text(STANDIN)
        wrapper = temporary / 'wrapper.py'
        wrapper.write_text(WRAPPER)
        table_file = temporary / 'table'
        socket_path = str(temporary / 'reader.sock')
        served = {'argv': None, 'mode': 'honest', 'last': None}
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(socket_path)
        listener.listen(8)

        def serve():
            while True:
                try:
                    connection, _ = listener.accept()
                except OSError:
                    return
                argv = served['argv'] or [sys.executable, '-I', str(standin), served['mode'], str(table_file)]
                try:
                    started = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=connection.fileno(),
                                               stderr=subprocess.DEVNULL)
                    spawned.append(started)
                    served['last'] = started
                    threading.Thread(target=started.wait, daemon=True).start()
                finally:
                    connection.close()

        threading.Thread(target=serve, daemon=True).start()

        def as_locked(pid, text):
            """The writer's status with the capability a suite cannot install: exactly cap_sys_ptrace,
            and the locks the stand-in does not set."""
            kept = [row for row in text.split('\n')
                    if row.split(':')[0] not in ('CapPrm', 'CapEff', 'NoNewPrivs', 'Seccomp')]
            return '\n'.join(kept + ['CapPrm:\t%016x' % PTRACE, 'CapEff:\t%016x' % PTRACE, 'NoNewPrivs:\t1',
                                     'Seccomp:\t2'])

        def capability_only(pid, text):
            """The capability lines alone: NoNewPrivs and Seccomp stay what the kernel says. It waits,
            for a moment, for a writer that is about to become the reader."""
            for _ in range(200):
                if 'Seccomp:\t2' in text:
                    break
                time.sleep(0.02)
                try:
                    text = Path('/proc/%d/status' % pid).read_text()
                except OSError:
                    break
            kept = [row for row in text.split('\n') if row.split(':')[0] not in ('CapPrm', 'CapEff')]
            return '\n'.join(kept + ['CapPrm:\t%016x' % PTRACE, 'CapEff:\t%016x' % PTRACE])

        installed = temporary / 'installed' / 'veldo-procread'
        installed.parent.mkdir()
        shutil.copyfile(str(reader), str(installed))

        def seam(**over):
            given = {'path': str(installed), 'socket': socket_path, 'pin': digest(installed),
                     'file': lambda found: (0, os.getgid(), 0o750), 'folder': lambda where, found: (0, 0o755),
                     'capability': lambda descriptor: CAP_V2, 'status': as_locked}
            given.update(over)
            P.SEAM['reader'] = {key: value for key, value in given.items() if value is not None}

        def block(pid, tasks, maps=(), start=None, extra=(), proc=None):
            """The lines of one block: tasks are (tid, working directory, files held open)."""
            seen = P.process(pid, proc) if proc else P.process(pid)
            lines = ['p %d %d' % (pid, seen['start'] if start is None else start)]
            for tid, cwd, held in tasks:
                lines += ['t %d' % tid, 'c %s %d' % numbers(cwd)]
                lines += ['f %d 30 %s %d' % ((number,) + numbers(path)) for number, path in enumerate(held, 3)]
            lines += ['m %s %d' % numbers(path) for path in maps]
            return lines + list(extra)

        def table(*blocks, end=None):
            lines = [line for one in blocks for line in one]
            return ('\n'.join(lines + ['end %d' % (len(blocks) if end is None else end)]) + '\n').encode()

        def ask(path, data=None, mode='honest', argv=None, **given):
            if data is not None:
                table_file.write_bytes(data)
            served.update(mode=mode, argv=argv)
            return P.in_use(str(path), **given)

        def counted(facts, pid):
            if any(user['pid'] == pid for user in facts['processes']):
                return 'user'
            if any(entry['pid'] == pid and entry['reach'] for entry in facts['unread']['processes']):
                return 'bound'
            return None

        def named(facts, pid):
            return [(use['how'], use['tid'], use['inode']) for user in facts['processes']
                    if user['pid'] == pid and user.get('by') == 'reader' for use in user['uses']]

        def state(facts):
            return facts['reader']['state']

        # The owner's own process that is not dumpable, in the item: the probe cannot read it.
        sealed, _ = child(item, dumpable=0)
        shown_elsewhere = table(block(sealed.pid, [(sealed.pid, elsewhere, [])]))
        shown_in_item = table(block(sealed.pid, [(sealed.pid, item, [])]))

        def refused(row, expected, label, **over):
            """One check that fails: the reader is not used, the process is judged by the bound as
            before, and the answer names the state."""
            seam(**over)
            facts = ask(item, shown_elsewhere)
            check(row, '%s: the state is %s [%s: %s]' % (label, expected, state(facts), facts['reader']['said']),
                  state(facts) == expected)
            check(row, '%s: the process in the item is judged by the bound, as before [%s]'
                  % (label, counted(facts, sealed.pid)),
                  counted(facts, sealed.pid) == 'bound' and facts['in_use'] is True)
            return facts

        # ---- AC1 ------------------------------------------------------------------------------------
        P.SEAM['reader'] = None
        before = P.in_use(str(item))
        check('ac1/absent', 'the reader\'s path and its socket\'s path are fixed in the probe, and every answer '
              'names the reader\'s state [%s]' % state(before),
              P.READER == '/usr/local/lib/veldo/veldo-procread'
              and P.READER_SOCKET == '/run/user/{uid}/veldo-procread.sock'
              and (state(before) == 'absent' or os.path.lexists(P.READER)))
        refused('ac1/absent', 'absent', 'no file at the path', path=str(temporary / 'installed' / 'none'))
        refused('ac1/absent', 'absent', 'no folder at the path', path=str(temporary / 'none' / 'veldo-procread'))
        check('ac1/absent', 'the undumpable process in the item was counted by the bound before any reader [%s]'
              % counted(before, sealed.pid), counted(before, sealed.pid) == 'bound')

        link = temporary / 'installed' / 'link'
        link.symlink_to(installed)
        refused('ac1/not-regular', 'refused:not_regular', 'a link to the reader', path=str(link))
        (temporary / 'installed' / 'folder').mkdir()
        refused('ac1/not-regular', 'refused:not_regular', 'a folder', path=str(temporary / 'installed' / 'folder'))

        refused('ac1/owner', 'refused:owner', 'the owner is not root', file=lambda found: (ME or 1, os.getgid(), 0o750))
        refused('ac1/owner', 'refused:owner', 'the file as it really is, owned by this user', file=None)
        refused('ac1/mode', 'refused:mode', 'another group', file=lambda found: (0, os.getgid() + 1, 0o750))
        refused('ac1/mode', 'refused:mode', 'mode 0755', file=lambda found: (0, os.getgid(), 0o755))
        refused('ac1/mode', 'refused:mode', 'mode 4750', file=lambda found: (0, os.getgid(), 0o4750))

        last = str(installed.parent)
        refused('ac1/folder', 'refused:folder', 'the folder that holds it belongs to this user',
                folder=lambda where, found: ((0, 0o755) if where != last
                                             else (found.st_uid, stat.S_IMODE(found.st_mode))))
        refused('ac1/folder', 'refused:folder', 'a folder on the way that others may write',
                folder=lambda where, found: (0, 0o775 if where == str(temporary) else 0o755))
        refused('ac1/folder', 'refused:folder', 'the folders as they really are', folder=None)
        way = temporary / 'way'
        way.symlink_to(installed.parent)
        refused('ac1/folder', 'refused:folder', 'a link on the way', path=str(way / 'veldo-procread'))

        def attribute(magic, permitted, inheritable=0, high=0, root=None):
            value = struct.pack('<5I', magic, permitted, inheritable, high, 0)
            return value + (struct.pack('<I', root) if root is not None else b'')

        def no_attribute(descriptor):
            raise OSError(61, 'No data available')

        refused('ac1/capability', 'refused:capability', 'no capability attribute', capability=no_attribute)
        refused('ac1/capability', 'refused:capability', 'the file as it really is, with no attribute',
                capability=None)
        refused('ac1/capability', 'refused:capability', 'permitted and not effective',
                capability=lambda descriptor: attribute(0x02000000, PTRACE))
        refused('ac1/capability', 'refused:capability', 'an inheritable capability',
                capability=lambda descriptor: attribute(0x02000001, PTRACE, PTRACE))
        refused('ac1/capability', 'refused:capability', 'version 1',
                capability=lambda descriptor: struct.pack('<3I', 0x01000001, PTRACE, 0))
        refused('ac1/capability', 'refused:capability', 'another capability and not cap_sys_ptrace',
                capability=lambda descriptor: attribute(0x02000001, 1 << 2))
        refused('ac1/capability-exact', 'refused:capability', 'cap_dac_read_search added',
                capability=lambda descriptor: attribute(0x02000001, PTRACE | 1 << 2))
        refused('ac1/capability-exact', 'refused:capability', 'a capability of the upper word added',
                capability=lambda descriptor: attribute(0x02000001, PTRACE, 0, 1))
        refused('ac1/capability-root-id', 'refused:capability', 'version 3 with root id 100000',
                capability=lambda descriptor: attribute(0x03000001, PTRACE, root=100000))
        seam(capability=lambda descriptor: attribute(0x03000001, PTRACE, root=0))
        facts = ask(item, shown_in_item)
        check('ac1/capability-root-id', 'version 3 with root id 0 is used [%s]' % state(facts), state(facts) == 'used')

        refused('ac1/no-pin', 'refused:no_pin', 'the word none', pin='none')
        refused('ac1/no-pin', 'refused:no_pin', 'no digest at all', pin=False)
        refused('ac1/no-pin', 'refused:no_pin', 'a digest of another form', pin=digest(installed).upper())

        # A program that prints a table showing the process elsewhere, in the reader's place.
        impostor = temporary / 'installed' / 'impostor'
        impostor.write_text('#!%s\n' % sys.executable + STANDIN)
        refused('ac1/digest', 'refused:digest', 'another program at the path', path=str(impostor))

        refused('ac1/no-socket', 'refused:no_socket', 'no socket at the path', socket=str(temporary / 'none.sock'))
        (temporary / 'file.sock').write_text('')
        refused('ac1/no-socket', 'refused:no_socket', 'a file that is no socket', socket=str(temporary / 'file.sock'))

        # The writer check left real: the stand-in answers on the socket, holds no capability and is
        # not locked, and the kernel says so.
        refused('ac1/writer', 'refused:writer', 'a stand-in on the socket, by its real status', status=None)
        refused('ac1/writer', 'refused:writer', 'a writer of another uid',
                status=lambda pid, text: as_locked(pid, text).replace('Uid:\t%d' % ME, 'Uid:\t%d' % (ME + 1)))
        refused('ac1/writer', 'refused:writer', 'a writer with cap_dac_read_search too',
                status=lambda pid, text: as_locked(pid, text).replace('%016x' % PTRACE, '%016x' % (PTRACE | 4)))
        refused('ac1/writer', 'refused:writer', 'a writer with NoNewPrivs 0',
                status=lambda pid, text: as_locked(pid, text).replace('NoNewPrivs:\t1', 'NoNewPrivs:\t0'))
        refused('ac1/writer', 'refused:writer', 'a writer with no filter',
                status=lambda pid, text: as_locked(pid, text).replace('Seccomp:\t2', 'Seccomp:\t0'))

        # The stand-in writes its table and ends. The row answers the status read for its number as a
        # locked reader's, after the process is gone: only the pidfd says that it is.
        looks = []

        def after_it_ended(pid, text):
            looks.append(pid)
            if len(looks) > 1:
                served['last'].wait(timeout=30)
                return 'Uid:\t%d\t%d\t%d\t%d\nCapPrm:\t%016x\nCapEff:\t%016x\nNoNewPrivs:\t1\nSeccomp:\t2\n' % (
                    ME, ME, ME, ME, PTRACE, PTRACE)
            return as_locked(pid, text)

        seam(status=after_it_ended)
        facts = ask(item, shown_elsewhere, mode='exit-after-table')
        check('ac1/writer-gone', 'a writer that ended before the last look is refused [%s: %s; looks %d]'
              % (state(facts), facts['reader']['said'], len(looks)),
              state(facts) == 'refused:writer' and counted(facts, sealed.pid) == 'bound')

        # A wrapper writes a header and a table, then executes the built reader in its own place with
        # its output on a socket pair. The process the kernel names is then the locked reader.
        seam(status=capability_only)
        facts = ask(item, shown_elsewhere, argv=[sys.executable, '-I', str(wrapper), str(reader), str(table_file)])
        became = served['last']
        try:
            status = Path('/proc/%d/status' % became.pid).read_text()
        except OSError:
            status = ''
        check('ac1/bytes-before-the-byte', 'the wrapper became the locked reader, by the kernel\'s own status [%s]'
              % [row for row in status.split('\n') if row.startswith(('NoNewPrivs', 'Seccomp:'))],
              'NoNewPrivs:\t1' in status and 'Seccomp:\t2' in status)
        check('ac1/bytes-before-the-byte', 'its table, written before it was locked, is refused [%s: %s]'
              % (state(facts), facts['reader']['said']),
              state(facts) == 'refused:writer' and counted(facts, sealed.pid) == 'bound')
        became.kill()
        seam()
        facts = ask(item, shown_elsewhere, mode='early-one-write')
        check('ac1/bytes-before-the-byte', 'a table in the header\'s own write is refused [%s]' % state(facts),
              state(facts) == 'refused:writer' and counted(facts, sealed.pid) == 'bound')
        seam(status=lambda pid, text: (time.sleep(0.3), as_locked(pid, text))[1])
        facts = ask(item, shown_elsewhere, mode='early')
        check('ac1/bytes-before-the-byte', 'a table sent before the probe\'s byte is refused [%s]' % state(facts),
              state(facts) == 'refused:writer' and counted(facts, sealed.pid) == 'bound')

        seam()
        facts = ask(item, shown_elsewhere, mode='second-writer')
        check('ac1/second-writer', 'a table written by another process than the header\'s is refused [%s: %s]'
              % (state(facts), facts['reader']['said']),
              state(facts) == 'refused:writer' and counted(facts, sealed.pid) == 'bound')

        seam()
        facts = ask(item, shown_elsewhere, mode='cap0')
        check('ac1/header-cap', 'a header that says cap=0 is refused [%s]' % state(facts),
              state(facts) == 'refused:no_capability' and counted(facts, sealed.pid) == 'bound')
        seam(status=capability_only)
        facts = ask(item, argv=[str(reader)])
        check('ac1/header-cap', 'the built reader, served on the socket with no capability, says cap=0 and is '
              'refused; its own status showed it locked [%s: %s]' % (state(facts), facts['reader']['said']),
              state(facts) == 'refused:no_capability' and counted(facts, sealed.pid) == 'bound')

        # The built reader itself: locked when its header arrives, and silent until the byte.
        mine, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        started = subprocess.Popen([str(reader)], stdin=subprocess.DEVNULL, stdout=theirs.fileno(), env={})
        spawned.append(started)
        theirs.close()
        mine.settimeout(20)
        header = mine.recv(4096)
        status = Path('/proc/%d/status' % started.pid).read_text()
        check('ac1/reader-locks-first', 'the header is the one line [%r]' % header, header == b'veldo-procread 1 cap=0\n')
        check('ac1/reader-locks-first', 'when it arrives the reader shows NoNewPrivs 1 and Seccomp 2',
              'NoNewPrivs:\t1' in status and 'Seccomp:\t2' in status)
        mine.settimeout(0.5)
        try:
            early = mine.recv(4096)
        except socket.timeout:
            early = None
        check('ac1/reader-locks-first', 'nothing follows the header before the byte is sent [%r]' % (early,),
              early is None and started.poll() is None)
        mine.settimeout(20)
        mine.sendall(b'\n')
        body = bytearray()
        while not re.search(rb'(?:\A|\n)end \d+\n\Z', bytes(body[-64:])):
            part = mine.recv(1 << 16)
            if not part:
                break
            body += part
        check('ac1/reader-locks-first', 'the table follows the byte, to its end line [%d bytes]' % len(body),
              P.reader_table(bytes(body))[1] is None)
        # AC5: after its end line the reader waits until this side is shut down.
        time.sleep(0.4)
        check('ac5/waits-after-end', 'the reader has written its end line and is still alive [%s]' % started.poll(),
              P.reader_table(bytes(body))[1] is None and started.poll() is None
              and os.path.exists('/proc/%d/status' % started.pid))
        mine.shutdown(socket.SHUT_WR)
        rest = mine.recv(4096)
        check('ac5/waits-after-end', 'it exits 0 once this side is shut down, and sends nothing more [%r %s]'
              % (rest, started.wait(timeout=20)), rest == b'' and started.returncode == 0)
        mine.close()

        seam()
        facts = ask(item, shown_in_item)
        check('ac1/used', 'with every check held the state is used, and the answer names the writer and the digest '
              '[%s]' % facts['reader'],
              state(facts) == 'used' and facts['reader']['writer']['uid'] == ME
              and facts['reader']['digest'] == digest(installed) and facts['reader']['read'] >= 1
              and facts['reader']['said'] is None)

        # ---- AC2 ------------------------------------------------------------------------------------
        held_file, mapped_file = item / 'inner' / 'held.txt', item / 'inner' / 'mapped.bin'
        check('ac2/cwd', 'the process in the item is named by process id, task and fact, with the device and inode '
              'number read [%s]' % [user for user in facts['processes'] if user['pid'] == sealed.pid],
              named(facts, sealed.pid) == [('cwd', sealed.pid, numbers(item)[1])]
              and [(user['uid'], use['device']) for user in facts['processes'] if user['pid'] == sealed.pid
                   for use in user['uses']] == [(ME, numbers(item)[0])]
              and counted(facts, sealed.pid) == 'user' and facts['in_use'] is True)
        facts = ask(other_item, shown_in_item)
        check('ac2/outside-not-counted', 'for another item the same process does not count any more [%s %s]'
              % (state(facts), counted(facts, sealed.pid)),
              state(facts) == 'used' and counted(facts, sealed.pid) is None
              and counted(before, sealed.pid) == 'bound')
        seam(path=str(temporary / 'installed' / 'none'))
        check('ac2/outside-not-counted', 'and with no reader it counts for that item, by the bound',
              counted(ask(other_item), sealed.pid) == 'bound')
        seam()

        opener, _ = child(elsewhere, open=held_file, dumpable=0)
        facts = ask(item, table(block(opener.pid, [(opener.pid, elsewhere, [held_file])])))
        check('ac2/open-file-only', 'a process that holds nothing but an open file beneath the item holds it [%s]'
              % named(facts, opener.pid), named(facts, opener.pid) == [('fd', opener.pid, numbers(held_file)[1])])
        stop(opener)
        director, _ = child(elsewhere, dirfd=item, dumpable=0)
        facts = ask(item, table(block(director.pid, [(director.pid, elsewhere, [item])])))
        check('ac2/directory-descriptor', 'a process that holds only a directory descriptor on the item holds it '
              '[%s]' % named(facts, director.pid), named(facts, director.pid) == [('fd', director.pid, numbers(item)[1])])
        stop(director)
        mapper, _ = child(elsewhere, map=mapped_file, dumpable=0)
        facts = ask(item, table(block(mapper.pid, [(mapper.pid, elsewhere, [])], maps=[mapped_file])))
        check('ac2/mapped-only', 'a process that only maps a file of the item holds it [%s]' % named(facts, mapper.pid),
              named(facts, mapper.pid) == [('maps', None, numbers(mapped_file)[1])])
        stop(mapper)
        walker, tids = child(elsewhere, thread_cwd=item / 'inner', dumpable=0)
        facts = ask(item, table(block(walker.pid, [(walker.pid, elsewhere, []), (tids[0], item / 'inner', [])])))
        check('ac2/second-thread-cwd', 'a process whose second thread sits in the item holds it, named by that thread '
              '[%s]' % named(facts, walker.pid),
              named(facts, walker.pid) == [('cwd', tids[0], numbers(item / 'inner')[1])])
        stop(walker)
        holder, tids = child(elsewhere, thread_open=held_file, dumpable=0)
        facts = ask(item, table(block(holder.pid, [(holder.pid, elsewhere, []), (tids[0], elsewhere, [held_file])])))
        check('ac2/second-thread-descriptor', 'a process whose second thread holds a file of the item in a table of '
              'its own holds it, named by that thread [%s]' % named(facts, holder.pid),
              named(facts, holder.pid) == [('fd', tids[0], numbers(held_file)[1])])
        inode = numbers(held_file)[1]
        for device in ('0:99', '-'):
            lines = block(holder.pid, [(holder.pid, elsewhere, [])]) + ['f 9 31 %s %d' % (device, inode)]
            facts = ask(item, table(lines))
            check('ac2/inode-alone', 'a descriptor printed with the device %s and an inode number of the item holds it '
                  '[%s]' % (device, [user for user in facts['processes'] if user['pid'] == holder.pid]),
                  named(facts, holder.pid) == [('fd', holder.pid, inode)]
                  and [use['device'] for user in facts['processes'] if user['pid'] == holder.pid
                       for use in user['uses']] == [device])
        stop(holder)

        # The built reader's own output, for a process it may read without its capability: one whose
        # second thread sits in the item, whose third holds a file of it in a table of its own, and
        # which maps a file of it.
        open_one, tids = child(elsewhere, thread_cwd=item / 'inner', thread_open=held_file, map=mapped_file)
        done = run_reader()
        printed = done.stdout.split(b'\n', 1)
        blocks, why = P.reader_table(printed[1] if len(printed) > 1 else b'')
        mine_block = (blocks or {}).get(open_one.pid) or {'facts': [], 'whole': None, 'start': None}
        seen = [(how, tid, inode) for how, tid, device, inode in mine_block['facts']]
        check('reader/facts-of-every-thread', 'the table is whole and the block is whole, with the start time the '
              'probe reads [%s %s]' % (why, mine_block['whole']),
              why is None and mine_block['whole'] is True
              and mine_block['start'] == P.process(open_one.pid)['start'])
        check('reader/facts-of-every-thread', 'the first thread is elsewhere, the second sits in the item',
              ('cwd', open_one.pid, numbers(elsewhere)[1]) in seen
              and ('cwd', tids[0], numbers(item / 'inner')[1]) in seen
              and ('cwd', open_one.pid, numbers(item / 'inner')[1]) not in seen)
        check('reader/facts-of-every-thread', 'the file is held by the third thread, in its own table, and by no other',
              [tid for how, tid, number in seen if how == 'fd' and number == numbers(held_file)[1]] == [tids[1]])
        check('reader/facts-of-every-thread', 'the device of the working directory is the one stat gives',
              ('cwd', tids[0], numbers(item / 'inner')[0], numbers(item / 'inner')[1]) in mine_block['facts'])
        text = done.stdout.decode('ascii', 'replace')
        own = text.split('\np %d ' % open_one.pid, 1)[-1].split('\np ', 1)[0].split('\n')
        check('reader/facts-of-every-thread', 'every task has its t line and an equal line is written once [%d lines]'
              % len(own),
              all('t %d' % tid in own for tid in [open_one.pid] + tids)
              and len([line for line in own if line[:2] in ('c ', 'f ')])
              == len(set(line for line in own if line[:2] in ('c ', 'f '))))
        check('reader/maps', 'the mapped file is in the block [%s]'
              % [fact for fact in seen if fact[0] == 'maps'][:3],
              ('maps', None, numbers(mapped_file)[1]) in seen)
        # The same table through the probe's own matching: every fact that is the item's, by its task.
        inodes, said = P._inodes(str(item))
        uses, stays = P._by_reader({'blocks': blocks or {}}, open_one.pid, P.PROC, inodes)
        check('reader/facts-of-every-thread', 'matched against the item, the reader\'s facts name the second thread\'s '
              'working directory, the third thread\'s file, the map and the descriptor python keeps for the map '
              '[%s %s]' % (stays, uses),
              stays is None and said is None
              and sorted(((use['how'], use['tid']) for use in uses or ()), key=str)
              == sorted([('cwd', tids[0]), ('fd', tids[1]), ('maps', None), ('fd', open_one.pid)], key=str))

        # ---- the run label ------------------------------------------------------------------------
        DK = load('v344_control_space_docker', ROOT / '.veldo' / 'control_space_docker.py')
        NAME = DK.LABEL_VARIABLE
        plain_environment = {key: value for key, value in os.environ.items() if key != NAME}
        secret, decoy_a, decoy_b = os.urandom(12).hex(), 'decoy-' + os.urandom(6).hex(), 'decoy-' + os.urandom(6).hex()
        run_label = 'row:run-' + os.urandom(4).hex()
        carrier, carrier_tids = child(elsewhere, thread_cwd=item / 'inner', environ=dict(
            plain_environment, **{NAME: run_label, 'SECRET_OF_THE_ROW': secret, NAME + '_OTHER': decoy_a,
                                  'X' + NAME: decoy_b}))
        bare, _ = child(elsewhere, environ=dict(plain_environment, SECRET_OF_THE_ROW=secret))
        empty, _ = child(elsewhere, environ=dict(plain_environment, **{NAME: ''}))
        longest, too_long = 'L' * 64, 'M' * 65
        fits, _ = child(elsewhere, environ=dict(plain_environment, **{NAME: longest}))
        over, _ = child(elsewhere, environ=dict(plain_environment, **{NAME: too_long}))
        labelled = run_reader()
        label_text = labelled.stdout.decode('ascii', 'replace')
        label_blocks, label_why = P.reader_table(labelled.stdout.split(b'\n', 1)[-1])

        def lines_of(pid):
            return label_text.split('\np %d ' % pid, 1)[-1].split('\np ', 1)[0].split('\n')

        def label_of(pid):
            return ((label_blocks or {}).get(pid) or {}).get('label', 'no block')
        check('reader/label', 'a process started with the run label variable has, for each of its tasks, one l line '
              'with the value in hexadecimal, and the probe reads that value as its label [%s %s %s]'
              % (label_why, label_of(carrier.pid), [line for line in lines_of(carrier.pid) if line[:1] in 'lx'][:4]),
              labelled.returncode == 0 and label_why is None and label_of(carrier.pid) == [run_label.encode()]
              and lines_of(carrier.pid).count('l =' + run_label.encode().hex()) == 1 + len(carrier_tids) == 2
              and not any(line.startswith('l ') and line != 'l =' + run_label.encode().hex()
                          for line in lines_of(carrier.pid)))
        leaked = [name for name, value in (('the secret', secret), ('the first decoy', decoy_a),
                                           ('the second decoy', decoy_b), ('the secret\'s name', 'SECRET_OF_THE_ROW'),
                                           ('the label\'s name', NAME))
                  if value in label_text or value.encode().hex() in label_text]
        check('reader/label', 'nothing else of an environment is anywhere in the output, as it is or in hexadecimal: '
              'not the secret the row planted, not its name, not the label\'s name, and not the values of two '
              'variables whose names only begin or end like the label\'s %s' % (leaked,), leaked == [])
        check('reader/label', 'a process with no such variable has l - and its label is read as none; an empty '
              'value is read as empty [%s %s]' % (label_of(bare.pid), label_of(empty.pid)),
              label_of(bare.pid) == [] and 'l -' in lines_of(bare.pid) and label_of(empty.pid) == [b'']
              and 'l =' in lines_of(empty.pid))
        check('reader/label', 'a value of 64 bytes is read; one of 65 is not printed, in part or whole, and leaves '
              'the label unread, with the block still whole [%s %s]'
              % (label_of(fits.pid), [line for line in lines_of(over.pid) if line[:1] in 'lx']),
              label_of(fits.pid) == [longest.encode()] and label_of(over.pid) is None
              and 'x env 7' in lines_of(over.pid) and not any(line.startswith('l ') for line in lines_of(over.pid))
              and 'M'.encode().hex() * 8 not in label_text
              and ((label_blocks or {}).get(over.pid) or {}).get('whole') is True)
        cli_text = (ROOT / 'bin' / 'veldo').read_text()
        check('reader/label', 'the one name in the source is the variable the Docker adapter and the CLI give a run, '
              'compared with its equals sign, and the probe names the same one [%s]'
              % (re.findall(r'"([A-Za-z_][A-Za-z0-9_]*=)"', source),),
              re.findall(r'"([A-Za-z_][A-Za-z0-9_]*=)"', source) == [NAME + '=']
              and 'static const char label_name[] = "%s=";' % NAME in source and P.RUN_LABEL_VARIABLE == NAME
              and 'SPACE_LABEL_VARIABLE = "%s"' % NAME in cli_text)
        for one in (carrier, bare, empty, fits, over):
            stop(one)

        # ---- a whole read of the environment ---------------------------------------------------------
        # One static program, three ways: spin executes itself again at once, with the environment it
        # has; cut unmaps the memory from the entry that begins with its second argument to the end
        # of the environment, says ready and waits; anything else says ready and waits.
        HELPER = r'''
#define _GNU_SOURCE
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
extern char **environ;
static char stack[1 << 16];
static char **shared;
/* A task that shares its parent's memory: it waits for a byte on the fifo, then executes this
 * program with an environment of its own, the one entry it was given. */
static int sharer(void *unused)
{
    char byte, *argv[] = {"helper", NULL}, *env[] = {shared[3], NULL};
    int fifo = open(shared[2], O_RDONLY);
    (void)unused;
    if (fifo < 0 || read(fifo, &byte, 1) != 1)
        _exit(1);
    execve("/proc/self/exe", argv, env);
    _exit(1);
}
int main(int argc, char **argv)
{
    char byte;
    if (argc > 3 && !strcmp(argv[1], "share")) {
        int pid;
        shared = argv;
        pid = clone(sharer, stack + sizeof stack, CLONE_VM | SIGCHLD, NULL);
        if (pid < 0 || dprintf(1, "ready\n%d\n", pid) < 0)
            return 1;
        while (read(0, &byte, 1) > 0)
            ;
        return 0;
    }
    if (argc > 3 && !strcmp(argv[1], "title")) {
        /* What a program that sets its process title does: it writes over its environment area. */
        char **entry, *first = NULL, *last = NULL;
        for (entry = environ; *entry; entry++) {
            char *end = *entry + strlen(*entry) + 1;
            if (!first || *entry < first)
                first = *entry;
            if (end > last)
                last = end;
        }
        if (!first || chdir(argv[2]) != 0 || open(argv[3], O_RDONLY) < 0)
            return 1;
        memset(first, 0, (size_t)(last - first));
        memcpy(first, "title", 5);
    }
    if (argc > 1 && !strcmp(argv[1], "spin")) {
        execve("/proc/self/exe", argv, environ);
        return 1;
    }
    if (argc > 2 && !strcmp(argv[1], "cut")) {
        uintptr_t page = (uintptr_t)sysconf(_SC_PAGESIZE), first = 0, last = 0;
        char **entry;
        for (entry = environ; *entry; entry++) {
            uintptr_t end = (uintptr_t)*entry + strlen(*entry) + 1;
            if (!strncmp(*entry, argv[2], strlen(argv[2])))
                first = (uintptr_t)*entry;
            if (end > last)
                last = end;
        }
        if (!first)
            return 1;
        first &= ~(page - 1);
        last = (last + page - 1) & ~(page - 1);
        if (munmap((void *)first, last - first) != 0)
            return 1;
    }
    if (write(1, "ready\n", 6) != 6)
        return 1;
    while (read(0, &byte, 1) > 0)
        ;
    return 0;
}
'''
        helper_folder = temporary / 'helper'
        helper_folder.mkdir()
        (helper_folder / 'helper.c').write_text(HELPER)
        built = subprocess.run(['/usr/bin/cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-o',
                                'helper', 'helper.c'], cwd=str(helper_folder), env={'PATH': '/usr/bin:/bin', 'TMPDIR': str(helper_folder)},
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if built.returncode:
            raise RuntimeError('the helper\'s build failed: ' + built.stderr.decode()[-400:])
        helper = str(helper_folder / 'helper')

        def helped(environ, *argv):
            process = subprocess.Popen([helper] + list(argv), cwd=str(elsewhere), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, env=environ)
            children.append(process)
            if argv[:1] != ('spin',) and process.stdout.readline() != b'ready\n':
                raise RuntimeError('the helper did not start')
            return process

        def label_lines(text, pid):
            return [line for line in text.split('\np %d ' % pid, 1)[-1].split('\np ', 1)[0].split('\n')[1:]
                    if line[:1] in 'lxg' and not line.startswith(('x cwd', 'x fd', 'x maps', 'x mnt', 'x task'))]

        spin_label = 'spin:run-' + os.urandom(4).hex()
        spin_line = 'l =' + spin_label.encode().hex()
        spinner = helped({NAME: spin_label, 'OTHER': 'value'}, 'spin')
        READS = 150
        seen_reads, wrong = {}, []
        for _ in range(READS):
            read = run_reader()
            read_text = read.stdout.decode('ascii', 'replace')
            if '\np %d ' % spinner.pid not in read_text:
                kind = 'no block'
            else:
                got = label_lines(read_text, spinner.pid)
                kind = ' | '.join(got) or 'no line'
                read_blocks = P.reader_table(read.stdout.split(b'\n', 1)[-1])[0] or {}
                carried = (read_blocks.get(spinner.pid) or {}).get('label')
                if 'l -' in got or carried == [] or (carried is not None and carried != [spin_label.encode()]) \
                        or read.returncode != 0:
                    wrong.append(kind)
            seen_reads[kind] = seen_reads.get(kind, 0) + 1
        alive = spinner.poll() is None
        spinner.kill()
        spinner.wait()
        spinner.stdin.close()
        spinner.stdout.close()
        check('reader/whole-read', 'a process that carries the run label and executes itself again without end, read '
              '%d times while it does: never l -, never a label of none, and its own label whenever its '
              'environment was read whole [%s wrong %s alive %s]' % (READS, seen_reads, wrong[:3], alive),
              alive and wrong == [] and sum(seen_reads.values()) == READS and seen_reads.get(spin_line, 0) >= 1
              and all(kind in (spin_line, 'no block', 'no line') or re.fullmatch(r'x env \d+', kind)
                      for kind in seen_reads))
        cut_label = 'cut:run-' + os.urandom(4).hex()
        severed = helped({'FILLER': 'f' * 100000, NAME: cut_label}, 'cut', NAME + '=')
        nothing = helped({})
        whole_read = run_reader()
        whole_text = whole_read.stdout.decode('ascii', 'replace')
        whole_blocks = P.reader_table(whole_read.stdout.split(b'\n', 1)[-1])[0] or {}

        def bounds_of(pid):
            fields = Path('/proc/%d/stat' % pid).read_bytes().rsplit(b')', 1)[1].split()
            return int(fields[48]) - int(fields[47])
        check('reader/whole-read', 'an environment that ends in memory the process has unmapped, the label in that '
              'part, is not read: x env 11, no l line, the label not read and the block still whole [%s %s of %s '
              'bytes]' % (label_lines(whole_text, severed.pid), (whole_blocks.get(severed.pid) or {}).get('label', '?'),
                          bounds_of(severed.pid)),
              whole_read.returncode == 0 and label_lines(whole_text, severed.pid) == ['x env 11']
              and severed.pid in whole_blocks and whole_blocks[severed.pid]['label'] is None
              and whole_blocks[severed.pid]['whole'] is True and bounds_of(severed.pid) > 100000
              and cut_label.encode().hex() not in whole_text)
        check('reader/whole-read', 'an environment of no bytes is not read either, since that is what the kernel '
              'returns for a task that is executing: x env 11, no l line, the label not read [%s %s of %s bytes]'
              % (label_lines(whole_text, nothing.pid), (whole_blocks.get(nothing.pid) or {}).get('label', '?'),
                 bounds_of(nothing.pid)),
              label_lines(whole_text, nothing.pid) == ['x env 11'] and nothing.pid in whole_blocks
              and whole_blocks[nothing.pid]['label'] is None and bounds_of(nothing.pid) == 0)
        for one in (severed, nothing):
            stop(one)
        check('reader/whole-read', 'the source takes what the task is before the read and after it, and reads an '
              'environment twice at most; the buffers an environment passed through are cleared by a call the '
              'compiler may not drop',
              source.count('identify(proc, pid, tid, &before)') == 1
              and source.count('identify(proc, pid, tid, &after)') == 1
              and 'for (attempt = 0; attempt < 2; attempt++) {' in source
              and 'explicit_bzero(in.bytes, sizeof in.bytes);' in source
              and 'explicit_bzero(value, sizeof value);' in source and 'explicit_bzero(kept, sizeof kept);' in source
              and 'memset(value' not in source and 'memset(in.bytes' not in source)

        # The same program before and after (the review of the fix, finding 1). A task that shares
        # its parent's memory until it executes: the kernel reads environ from the memory the task
        # had when the entry was opened, which the parent keeps alive, so a read that falls across
        # the execution returns the parent's whole environment, as many bytes as the ends taken
        # before it are apart. Only what the task is, before and after, tells that read from the
        # task's own. The reader's read of that one entry is held back by strace until the task has
        # executed.
        strace = shutil.which('strace', path='/usr/bin:/bin')
        if strace:
            HELD = 2.0  # how long the reader's read of that entry is held back
            share_label = 'share:run-' + os.urandom(4).hex()
            go = temporary / 'share.fifo'
            os.mkfifo(str(go))
            parent = helped({'OTHER': 'value'}, 'share', str(go), '%s=%s' % (NAME, share_label))
            shared_pid = int(parent.stdout.readline())
            program = os.stat(helper)

            def executed():
                try:
                    found = os.stat('/proc/%d/exe' % shared_pid)
                    carried = Path('/proc/%d/environ' % shared_pid).read_bytes()
                except OSError:
                    return False
                return (found.st_dev, found.st_ino) == (program.st_dev, program.st_ino) \
                    and carried == ('%s=%s' % (NAME, share_label)).encode() + b'\0'
            before_bytes = Path('/proc/%d/environ' % shared_pid).read_bytes()
            traced = subprocess.Popen(
                [strace, '-qq', '-P', '%d/task/%d/environ' % (shared_pid, shared_pid), '-e', 'trace=openat,read',
                 '-e', 'inject=read:delay_enter=%d' % int(HELD * 1000000), str(reader)],
                cwd='/proc', stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={})
            spawned.append(traced)
            table_read = []
            pump = threading.Thread(target=lambda: table_read.append(traced.stdout.read()), daemon=True)
            pump.start()
            opened_at = executed_at = None
            for line in traced.stderr:
                if opened_at is None and line.startswith(b'openat(') and b'environ' in line:
                    opened_at = time.monotonic()
                    with open(str(go), 'wb') as word:
                        word.write(b'x')
                    while time.monotonic() - opened_at < HELD and not executed():
                        time.sleep(0.005)
                    executed_at = time.monotonic() if executed() else None
            traced.wait(timeout=120)
            pump.join(timeout=120)
            share_text = (table_read or [b''])[0].decode('ascii', 'replace')
            share_blocks = P.reader_table((table_read or [b''])[0].split(b'\n', 1)[-1])[0] or {}
            share_lines = label_lines(share_text, shared_pid) if '\np %d ' % shared_pid in share_text else ['no block']
            in_time = opened_at is not None and executed_at is not None and executed_at - opened_at < HELD / 2
            rows['reader/same-program'] = [(
                'a task that shares its parent\'s memory and carries no label of its own until it executes a '
                'program with the run label, which it does between the reader\'s open of its environ entry and '
                'the read: the parent\'s environment, which holds no label, is not taken for the task\'s; the '
                'reader reads once more and writes the task\'s own label [%s label %s; the parent carried %d bytes '
                'and no label %s; executed in time %s; reader exit %s]'
                % (share_lines, (share_blocks.get(shared_pid) or {}).get('label', '?'), len(before_bytes),
                   NAME.encode() not in before_bytes, in_time, traced.returncode),
                in_time and len(before_bytes) > 0 and NAME.encode() not in before_bytes and traced.returncode == 0
                and share_lines == ['l =' + share_label.encode().hex()]
                and (share_blocks.get(shared_pid) or {}).get('label') == [share_label.encode()])]
            stop(parent)
        else:
            print('  SELFTEST SKIP: VELDO-0344 reader/same-program: strace is not on the path /usr/bin:/bin, and the '
                  'row needs it to hold the reader\'s read of one environ entry back until the task has executed')

        # A process that writes over its environment area (programs that set their process title that
        # way). Its label is gone for any reader; what it holds is not, and needs no label.
        title_label = 'title:run-' + os.urandom(4).hex()
        titled = helped({'FILLER': 'f' * 200, NAME: title_label}, 'title', str(item / 'inner'),
                        str(item / 'inner' / 'held.txt'))
        title_read = run_reader()
        title_text = title_read.stdout.decode('ascii', 'replace')
        title_blocks = P.reader_table(title_read.stdout.split(b'\n', 1)[-1])[0] or {}
        title_block = title_blocks.get(titled.pid) or {}
        title_uses, title_why = P._by_reader({'state': 'used', 'blocks': title_blocks}, titled.pid, '/proc',
                                             P._inodes(os.path.realpath(str(item)))[0])
        title_hows = sorted(set(use['how'] for use in title_uses or ()))
        title_inodes = set(use['inode'] for use in title_uses or ())
        check('reader/rewritten-environment', 'a process started with the run label that then writes over its '
              'environment area, with its working directory in the item and a file of the item open: the reader '
              'reads an environment with no label (l -, a label of none), and its block is whole and names the '
              'working directory and the open file by inode, so the item is in use by it [%s label %s whole %s; '
              'uses %s %s]' % (label_lines(title_text, titled.pid), title_block.get('label', '?'),
                               title_block.get('whole'), title_hows, title_why),
              title_read.returncode == 0 and label_lines(title_text, titled.pid) == ['l -']
              and title_block.get('label') == [] and title_block.get('whole') is True and title_why is None
              and title_hows == ['cwd', 'fd'] and title_label.encode().hex() not in title_text
              and os.stat(str(item / 'inner')).st_ino in title_inodes
              and os.stat(str(item / 'inner' / 'held.txt')).st_ino in title_inodes)
        stop(titled)

        def label_read(*lines):
            got = P.reader_table(table(['p 7 1'] + list(lines)))
            return (got[0][7]['label'], got[0][7]['whole']) if got[0] else got[1][0]
        check('label/table', 'the label of a block is what its tasks carry: none when the environment was read and '
              'holds none, a value once however many tasks carry it, two values in the order read [%s %s %s]'
              % (label_read('t 7', 'l -'), label_read('t 7', 'l =6162', 't 8', 'l =6162'),
                 label_read('t 7', 'l =6162', 't 8', 'l =63', 'l =')),
              label_read('t 7', 'c 1:2 3', 'l -') == ([], True)
              and label_read('t 7', 'l =6162', 't 8', 'l =6162') == ([b'ab'], True)
              and label_read('t 7', 'l =6162', 't 8', 'l =63', 'l =') == ([b'ab', b'c', b''], True)
              and label_read('t 7', 'l -', 't 8', 'l =6162') == ([b'ab'], True))
        check('label/table', 'an environment that was not read is not a label of none: an x env line leaves the '
              'label unread, before or after another task\'s l line, and leaves the block whole [%s %s]'
              % (label_read('t 7', 'x env 13'), label_read('t 7', 'l =6162', 't 8', 'x env 13')),
              label_read('t 7', 'x env 13') == (None, True)
              and label_read('t 7', 'l =6162', 't 8', 'x env 13') == (None, True)
              and label_read('t 7', 'x env 13', 't 8', 'l -') == (None, True))
        twice = P.reader_table(table(['p 7 1', 't 7', 'l -'], ['p 7 1', 't 7', 'l -']))[0]
        check('label/table', 'a block with no l line, one closed with g and a process id that opens two blocks have '
              'no label read [%s %s %s]' % (label_read('t 7', 'c 1:2 3'), label_read('t 7', 'l -', 'g'),
                                           twice and twice[7]['label']),
              label_read('t 7', 'c 1:2 3') == (None, True) and label_read('t 7', 'l -', 'g') == (None, False)
              and label_read() == (None, True) and twice is not None and twice[7]['label'] is None)
        check('label/table', 'an l line in no task, and one outside the format, make the whole table unused [%s]'
              % ([label_read(*lines) for lines in (('l -',), ('t 7', 'l =6'), ('t 7', 'l =6G'), ('t 7', 'l =AB'),
                                                   ('t 7', 'l'), ('t 7', 'l abc'), ('x env 13',))],),
              all(label_read(*lines) == 'refused:output'
                  for lines in (('l -',), ('t 7', 'l =6'), ('t 7', 'l =6G'), ('t 7', 'l =AB'), ('t 7', 'l'),
                                ('t 7', 'l abc'), ('t 7', 'l - '), ('x env 13',))))
        seam()
        shown = block(sealed.pid, [(sealed.pid, elsewhere, [])])
        facts = ask(item, table(shown[:2] + ['x env 13'] + shown[2:]))
        again = ask(item, table(block(sealed.pid, [(sealed.pid, item, [])]) + ['x env 13']))
        check('label/table', 'rule 4 still reads the files of a block whose label was not read: elsewhere the '
              'process does not count, in the item it holds it [%s %s %s]'
              % (state(facts), counted(facts, sealed.pid), counted(again, sealed.pid)),
              state(facts) == 'used' and counted(facts, sealed.pid) is None and counted(again, sealed.pid) == 'user')
        P.SEAM['reader'] = None

        # ---- AC4 ------------------------------------------------------------------------------------
        check('ac4/format', 'run directly it exits 0 and writes nothing to standard error [%s %r]'
              % (done.returncode, done.stderr[:80]), done.returncode == 0 and done.stderr == b'')
        check('ac4/format', 'the first line is the header and every other line is in the format of design 7.1',
              printed[0] == b'veldo-procread 1 cap=0' and why is None)
        check('ac4/format', 'it prints numbers only, and a run label in hexadecimal: no letter but the line\'s own '
              'first word and the digits of a label, no path',
              re.fullmatch(rb'(?:(?:(?:[ptcfmg]|x (?:cwd|fd|stat|mnt|maps|task|env)|end)(?: [0-9:]+| -)*'
                           rb'|l (?:-|=(?:[0-9a-f]{2})*))\n)+',
                           printed[1] if len(printed) > 1 else b'') is not None)
        check('ac4/format', 'the table holds this suite\'s own process and the end line counts the blocks',
              os.getpid() in (blocks or {}) and text.rstrip('\n').rsplit('\n', 1)[-1] == 'end %d' % len(blocks or {}))
        sealed_block = (blocks or {}).get(sealed.pid)
        sealed_lines = text.split('\np %d ' % sealed.pid, 1)[-1].split('\np ', 1)[0].split('\n')
        check('ac4/unread-without-capability', 'for a process it may not read it prints x lines, and the block is not '
              'whole [%s]' % sealed_lines[:6],
              sealed_block is not None and sealed_block['whole'] is False
              and 'x cwd 13' in sealed_lines and 'x fd 13' in sealed_lines and 'x maps 13' in sealed_lines)
        check('ac4/unread-without-capability', 'its environment is closed too: x env, no l line, and its label is not '
              'read [%s]' % (sealed_block and sealed_block['label'],),
              sealed_block is not None and sealed_block['label'] is None and 'x env 13' in sealed_lines
              and not any(line.startswith('l ') for line in sealed_lines))
        uses, stays = P._by_reader({'blocks': blocks or {}}, sealed.pid, P.PROC, inodes)
        check('ac4/unread-without-capability', 'and the probe leaves that process unread [%s]' % stays,
              uses is None and stays == 'unread_fact')
        stop(open_one)

        argued = run_reader(argv=['anything'])
        check('ac4/no-argument', 'with an argument it prints nothing and exits 2 [%s %r %r]'
              % (argued.returncode, argued.stdout[:40], argued.stderr[:40]),
              argued.returncode == 2 and argued.stdout == b'' and argued.stderr == b'')

        opened = sorted(set(re.findall(r'path_(?:start|task)\([^"]*"([^"]*)"', source)))
        check('ac4/entries', 'the entries the source opens are stat, mountinfo, maps and the task folder of a process, '
              'and cwd, environ, exe, stat and fdinfo of a task [%s %s]'
              % (opened, sorted(re.findall(r'path_task\([^"]*"([^"]*)"', source))),
              opened == ['/cwd', '/environ', '/exe', '/fdinfo', '/fdinfo/', '/maps', '/mountinfo', '/stat', '/task',
                         '/task/']
              and sorted(re.findall(r'path_task\([^"]*"([^"]*)"', source))
              == ['/cwd', '/environ', '/exe', '/fdinfo', '/fdinfo/', '/stat', '/task/'])
        check('ac4/entries', 'it opens /proc, and every other open is beneath that one descriptor',
              source.count('SYS_openat') == 2 and 'syscall(SYS_openat, AT_FDCWD, "/proc",' in source
              and 'syscall(SYS_openat, proc, path, O_RDONLY' in source and 'SYS_open,' not in source
              and source.count('SYS_newfstatat') == 1 and 'SYS_newfstatat, proc, path' in source)
        check('ac4/entries', 'it reads no environment of its own and takes no input: no getenv, no third argument of '
              'main, no read of descriptor 0; the one environment entry it opens is a task\'s, in one place',
              'getenv' not in source and 'envp' not in source and 'char **environ' not in source
              and source.count('"/environ"') == 1 and source.count('read_label(') == 2
              and 'int main(int argc, char **argv)\n' in source and 'SYS_read, 0' not in source
              and 'if (argc > 1)\n        return 2;' in source)

        # Patched copies: one forbidden call after the filter is in place, then a normal exit.
        ANCHOR = '    lock_in();\n'
        CALLS = (
            ('kill', 'syscall(SYS_getpid)', 'syscall(SYS_kill, before, 0)'),
            ('pidfd_getfd', 'syscall(SYS_pidfd_open, syscall(SYS_getpid), 0)', 'syscall(SYS_pidfd_getfd, before, 0, 0)'),
            ('process_vm_readv', 'syscall(SYS_getpid)', 'syscall(SYS_process_vm_readv, before, NULL, 0, NULL, 0, 0)'),
            ('open-for-writing', '0', 'syscall(SYS_openat, AT_FDCWD, "/dev/null", O_WRONLY)'),
            ('open-read-write', '0', 'syscall(SYS_openat, AT_FDCWD, "/dev/null", O_RDWR)'),
            ('open-create', '0', 'syscall(SYS_openat, AT_FDCWD, "/nonexistent-veldo-0344", O_RDONLY | O_CREAT, 0600)'),
            ('open-truncate', '0', 'syscall(SYS_openat, AT_FDCWD, "/dev/null", O_RDONLY | O_TRUNC)'),
            ('ptrace', 'syscall(SYS_getpid)', 'syscall(SYS_ptrace, 16, before, 0, 0)'),
            ('process_vm_writev', 'syscall(SYS_getpid)', 'syscall(SYS_process_vm_writev, before, NULL, 0, NULL, 0, 0)'),
            ('pidfd_open', 'syscall(SYS_getpid)', 'syscall(SYS_pidfd_open, before, 0)'),
            ('kcmp', 'syscall(SYS_getpid)', 'syscall(SYS_kcmp, before, before, 0, 0, 0)'),
            ('tkill', 'syscall(SYS_gettid)', 'syscall(SYS_tkill, before, 0)'),
            ('tgkill', 'syscall(SYS_getpid)', 'syscall(SYS_tgkill, before, before, 0)'),
            ('rt_sigqueueinfo', 'syscall(SYS_getpid)', 'syscall(SYS_rt_sigqueueinfo, before, 0, NULL)'),
            ('pidfd_send_signal', 'syscall(SYS_pidfd_open, syscall(SYS_getpid), 0)',
             'syscall(SYS_pidfd_send_signal, before, 0, NULL, 0)'),
            ('write-to-2', '0', 'syscall(SYS_write, 2, "x", 1)'),
            ('execve', '0', 'syscall(SYS_execve, "/bin/true", NULL, NULL)'),
            ('mmap', '0', 'syscall(SYS_mmap, NULL, 4096, 3, 0x22, -1, 0)'),
        )
        check('ac4/filter', 'the source locks itself in one place', source.count(ANCHOR) == 1)

        def patched(pre, call):
            return build(source.replace(ANCHOR, '    long before = %s;\n    lock_in();\n    %s;\n    (void)before;\n'
                                                '    leave(0);\n' % (pre, call)))

        allowed = run_reader(patched('0', 'syscall(SYS_read, -1, &byte, 0)'))
        check('ac4/filter', 'a patched copy that makes an allowed call after the filter exits normally [%s]'
              % allowed.returncode, allowed.returncode == 0 and allowed.stdout == b'')
        for name, pre, call in CALLS:
            ended = run_reader(patched(pre, call))
            check('ac4/filter', 'a patched copy that calls %s after the filter is ended by the kernel [%s]'
                  % (name, ended.returncode), ended.returncode == -signal.SIGSYS and ended.stdout == b'')

        # ---- AC5 ------------------------------------------------------------------------------------
        other, _ = child(elsewhere, dumpable=0)
        seam()
        whole = block(other.pid, [(other.pid, elsewhere, [])]) + block(sealed.pid, [(sealed.pid, elsewhere, [])])
        cut = ('\n'.join(block(other.pid, [(other.pid, elsewhere, [])])) + '\n').encode()
        facts = ask(item, cut, mode='cut')
        check('ac5/cut', 'an output cut before the block of the process in the item is refused [%s: %s]'
              % (state(facts), facts['reader']['said']), state(facts) == 'refused:output')
        check('ac5/cut', 'and nothing of it is used: the process whose block came before the cut is judged by the '
              'bound, as is the one in the item [%s %s]' % (counted(facts, other.pid), counted(facts, sealed.pid)),
              counted(facts, other.pid) == 'bound' and counted(facts, sealed.pid) == 'bound')
        facts = ask(item, cut, mode='exit-after-table')
        check('ac5/cut', 'a connection that ends with no end line is refused [%s]' % state(facts),
              state(facts) in ('refused:output', 'refused:writer') and counted(facts, other.pid) == 'bound')
        stop(other)

        def socketed(data, mode='honest'):
            facts = ask(item, data, mode=mode)
            return state(facts), counted(facts, sealed.pid)

        mine_lines = block(sealed.pid, [(sealed.pid, elsewhere, [])])
        check('ac5/not-whole', 'the whole table is used [%s]' % (socketed(table(mine_lines)),),
              socketed(table(mine_lines)) == ('used', None))
        for label, data in (('an end count other than the number of blocks', table(mine_lines, end=2)),
                            ('a line outside the format', table(mine_lines + ['c 1:2 /a/path'])),
                            ('a letter where a number belongs', table(mine_lines + ['m 8:1 0x10'])),
                            ('a line in no block', table(['t 5'], end=0)),
                            ('a fact in no task', table(['p 5 5', 'c 1:2 3'])),
                            ('two end lines', table(mine_lines) + b'end 1\n'),
                            ('a block after the end line', table(mine_lines) + b'p 1 1\n'),
                            ('a last line with no line feed', table(mine_lines)[:-1])):
            got = P.reader_table(data)
            check('ac5/not-whole', '%s: the table is not used [%s]' % (label, got[1]),
                  got[0] is None and got[1][0] == 'refused:output')
        check('ac5/not-whole', 'over the socket an end count that is wrong is refused and the process is judged by '
              'the bound [%s]' % (socketed(table(mine_lines, end=2)),),
              socketed(table(mine_lines, end=2)) == ('refused:output', 'bound'))
        check('ac5/not-whole', 'over the socket bytes after the end line are refused [%s]'
              % (socketed(table(mine_lines), 'trailing'),),
              socketed(table(mine_lines), 'trailing') == ('refused:output', 'bound'))
        check('ac5/not-whole', 'a process id that opens two blocks is whole in neither',
              [one['whole'] for one in P.reader_table(table(['p 7 1', 't 7', 'c 1:2 3'], ['p 7 1', 't 7', 'c 1:2 4']))[0]
               .values()] == [False])
        check('ac5/not-whole', 'a g line closes its block and leaves it not whole',
              P.reader_table(table(['p 7 1', 't 7', 'g']))[0][7]['whole'] is False
              and P.reader_table(table(['p 7 1', 'g', 't 7']))[0] is None)
        got = P.reader_table(table(mine_lines), status=3)
        check('ac5/exit-status', 'a reader run directly that ended with status 3 is not used at all [%s]' % (got[1],),
              got[0] is None and got[1][0] == 'refused:failed')
        check('ac5/exit-status', 'with status 0 the same output is used',
              P.reader_table(table(mine_lines), status=0)[1] is None
              and P.reader_table(b'veldo-procread 1 cap=1\n' + table(mine_lines), status=0, header=True)[1] is None
              and P.reader_table(b'veldo-procread 1 cap=0\n' + table(mine_lines), status=0, header=True)[1][0]
              == 'refused:no_capability')

        # A standard output that takes no more bytes: a packet socket refuses a write larger than its
        # buffer and takes a small one. Many open descriptors make the table larger than that.
        crowd = [child(elsewhere, **{'open': held_file}) for _ in range(2)]
        many = []
        try:
            for _ in range(900):
                many.append(os.open(str(held_file), os.O_RDONLY))
        except OSError:
            pass
        mine, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        theirs.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        started = subprocess.Popen([str(reader)], stdin=subprocess.DEVNULL, stdout=theirs.fileno(), env={})
        spawned.append(started)
        theirs.close()
        for descriptor in many:
            os.close(descriptor)
        mine.settimeout(30)
        packets = [mine.recv(1 << 16)]
        mine.sendall(b'\n')
        try:
            while True:
                packet = mine.recv(1 << 16)
                if not packet:
                    break
                packets.append(packet)
                if packet.startswith(b'end '):
                    break
        except (socket.timeout, OSError):
            pass
        mine.close()
        ended = started.wait(timeout=30)
        check('ac5/failed-write', 'the header was written and the table is larger than one write takes [%d packets]'
              % len(packets), packets[0] == b'veldo-procread 1 cap=0\n')
        check('ac5/failed-write', 'the reader ended with status 3 at the write that failed [%s]' % ended, ended == 3)
        check('ac5/failed-write', 'no end line follows the gap [%r]' % [packet[:12] for packet in packets[1:]],
              not any(packet.startswith(b'end ') for packet in packets))
        for process, _ in crowd:
            stop(process)

        # ---- AC3: a fixture process table, read whole ---------------------------------------------------
        fixture = temporary / 'fixture'
        fixture.mkdir()
        ROOT_LOGIN, START = 70, 100

        def entry(pid, uid, login, start=START):
            base = fixture / str(pid)
            (base / 'fd').mkdir(parents=True)
            (base / 'comm').write_text('holder\n')
            (base / 'maps').write_text('')
            (base / 'cwd').write_text('')  # no link: the probe cannot read where the process is
            (base / 'status').write_text('Name:\tholder\nPPid:\t0\nUid:\t%d\t%d\t%d\t%d\nGid:\t%d\t%d\t%d\t%d\n'
                                         'Groups:\t\nCapEff:\t%016x\n' % ((uid,) * 8 + (0x1ffffffffff if uid == 0 else 0,)))
            (base / 'loginuid').write_text(str(login))
            (base / 'cgroup').write_text('0::/system.slice/holder.service\n')
            (base / 'stat').write_text('%d (holder) S 0 %d %d 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 %d 0 0\n'
                                       % (pid, pid, pid, start))

        entry(ROOT_LOGIN, 0, ME)
        closed_item = temporary / 'closed-item'
        (closed_item / 'shut').mkdir(parents=True)
        (closed_item / 'shut' / 'held.txt').write_text('held\n')

        def fixed(path, lines, **given):
            return ask(path, table(lines) if lines is not None else None, proc=str(fixture), **given)

        seam(path=str(temporary / 'installed' / 'none'))
        facts = fixed(item, None)
        check('ac3/root-login', 'with no reader a root-owned process a login started makes the item in use, by the '
              'bound [%s]' % facts['unread']['processes'],
              facts['in_use'] is True and [entry['reach'] for entry in facts['unread']['processes']] == ['privileged_login'])
        seam()
        facts = fixed(item, ['p %d %d' % (ROOT_LOGIN, START), 't %d' % ROOT_LOGIN, 'c %s %d' % numbers(item)])
        check('ac3/root-login', 'with the reader, in the item it holds it, named with its uid [%s]' % facts['processes'],
              facts['in_use'] is True and named(facts, ROOT_LOGIN) == [('cwd', ROOT_LOGIN, numbers(item)[1])]
              and facts['processes'][0]['uid'] == 0 and facts['unread']['processes'] == [])
        facts = fixed(item, ['p %d %d' % (ROOT_LOGIN, START), 't %d' % ROOT_LOGIN, 'c %s %d' % numbers(elsewhere)])
        check('ac3/root-login', 'and elsewhere it does not count: the item is not in use [%s %s]'
              % (facts['in_use'], facts['reader']['read']),
              facts['in_use'] is False and facts['processes'] == [] and facts['unread']['processes'] == []
              and facts['reader']['read'] == 1)

        inside = ['p %d %d' % (ROOT_LOGIN, START), 't %d' % ROOT_LOGIN, 'c %s %d' % numbers(elsewhere)]
        facts = fixed(item, inside + ['x fd 13'])
        check('ac3/unread-fact', 'a block with an x line leaves the process unread, judged by the bound: in use [%s]'
              % facts['unread']['processes'],
              facts['in_use'] is True and [(entry['reader'], entry['reach']) for entry in facts['unread']['processes']]
              == [('unread_fact', 'privileged_login')])
        facts = fixed(item, inside + ['g'])
        check('ac3/unread-fact', 'so does a block the reader closed with g',
              facts['in_use'] is True and [entry['reader'] for entry in facts['unread']['processes']] == ['unread_fact'])
        facts = fixed(item, ['p 71 %d' % START, 't 71', 'c %s %d' % numbers(elsewhere)])
        check('ac3/no-block-or-start', 'a process with no block stays unread: in use [%s]' % facts['unread']['processes'],
              facts['in_use'] is True and [entry['reader'] for entry in facts['unread']['processes']] == ['no_block'])
        facts = fixed(item, ['p %d %d' % (ROOT_LOGIN, START + 1), 't %d' % ROOT_LOGIN, 'c %s %d' % numbers(elsewhere)])
        check('ac3/no-block-or-start', 'a block with another start time than the probe reads stays unread: in use',
              facts['in_use'] is True and [entry['reader'] for entry in facts['unread']['processes']] == ['start_time'])

        hidden = numbers(closed_item / 'shut' / 'held.txt')
        holds_hidden = ['p %d %d' % (ROOT_LOGIN, START), 't %d' % ROOT_LOGIN, 'c %s %d' % numbers(elsewhere),
                        'f 3 30 %s %d' % hidden]
        facts = fixed(closed_item, holds_hidden)
        check('ac3/unlistable-folder', 'while every folder can be listed the file inside is matched [%s]'
              % named(facts, ROOT_LOGIN), named(facts, ROOT_LOGIN) == [('fd', ROOT_LOGIN, hidden[1])])
        os.chmod(str(closed_item / 'shut'), 0)
        closed.append(closed_item / 'shut')
        facts = fixed(closed_item, holds_hidden)
        if ME == 0:
            print('  SELFTEST SKIP: VELDO-0344 ac3/unlistable-folder: root lists a folder of mode 000')
        else:
            check('ac3/unlistable-folder', 'a folder of the item that cannot be listed makes the item in use [%s %s]'
                  % (facts['in_use'], facts['unread']['folders']),
                  facts['in_use'] is True and facts['unknown'] is True and named(facts, ROOT_LOGIN) == []
                  and 'shut' in str(facts['unread']['folders']))
        os.chmod(str(closed_item / 'shut'), 0o755)

        # ---- AC8: the probe's own reading covers every thread -------------------------------------------
        P.SEAM['reader'] = None

        def paths(facts, pid, how):
            return [use['path'] for user in facts['users'] if user['pid'] == pid for use in user['uses']
                    if use['how'] == how]

        walker, tids = child(elsewhere, thread_cwd=item / 'inner')
        facts = P.processes(str(item))
        check('ac8/second-thread-cwd', 'a readable process whose second thread sits in the path, with a file system '
              'state of its own, uses it [%s]' % paths(facts, walker.pid, 'cwd'),
              paths(facts, walker.pid, 'cwd') == [str(item / 'inner')]
              and os.readlink('/proc/%d/cwd' % walker.pid) == str(elsewhere))
        stop(walker)
        holder, tids = child(elsewhere, thread_open=held_file)
        facts = P.processes(str(item))
        check('ac8/second-thread-descriptor', 'a readable process whose second thread holds a file of the path in a '
              'table of its own uses it [%s]' % paths(facts, holder.pid, 'open'),
              paths(facts, holder.pid, 'open') == [str(held_file)]
              and str(held_file) not in [os.readlink('/proc/%d/fd/%s' % (holder.pid, name))
                                         for name in os.listdir('/proc/%d/fd' % holder.pid)])
        stop(holder)
        tasked = fixture / '80'
        for tid, readable in ((80, True), (81, False)):
            (tasked / 'task' / str(tid) / 'fd').mkdir(parents=True)
            if readable:
                (tasked / 'task' / str(tid) / 'cwd').symlink_to(elsewhere)
            else:
                (tasked / 'task' / str(tid) / 'cwd').write_text('')
        (tasked / 'comm').write_text('threads\n')
        (tasked / 'maps').write_text('')
        (tasked / 'status').write_text('Name:\tthreads\nPPid:\t0\nUid:\t%d\t%d\t%d\t%d\nGid:\t%d\t%d\t%d\t%d\n'
                                       'Groups:\t\nCapEff:\t%016x\n' % ((ME,) * 8 + (0,)))
        (tasked / 'cgroup').write_text('0::/system.slice/holder.service\n')
        facts = P.processes(str(item), proc=str(fixture))
        check('ac8/unreadable-task', 'a process with a task the probe cannot read is unread [%s]'
              % [(entry['pid'], entry['reach']) for entry in facts['unread']],
              (80, 'same_uid') in [(entry['pid'], entry['reach']) for entry in facts['unread']])
        (tasked / 'task' / '81' / 'cwd').unlink()
        (tasked / 'task' / '81' / 'cwd').symlink_to(item)
        facts = P.processes(str(item), proc=str(fixture))
        check('ac8/unreadable-task', 'and once that task can be read, its working directory in the path is use',
              paths(facts, 80, 'cwd') == [str(item)] and 80 not in [entry['pid'] for entry in facts['unread']])

        # ---- AC6 ------------------------------------------------------------------------------------
        services = PRODUCTION['control_space_probe.py'].parent / 'services'
        socket_unit = (services / 'veldo-procread.socket').read_text()
        service_unit = (services / 'veldo-procread@.service').read_text()

        def settings(text, section):
            body = text.split('[%s]\n' % section, 1)[1].split('\n[', 1)[0]
            return [line for line in body.split('\n') if line and not line.startswith('#')]

        check('ac6/units', 'the socket unit listens in the runtime folder, for the owner alone, one instance per '
              'connection [%s]' % settings(socket_unit, 'Socket'),
              settings(socket_unit, 'Socket') == ['ListenStream=%t/veldo-procread.sock', 'SocketMode=0600',
                                                  'Accept=yes', 'MaxConnections=4']
              and settings(socket_unit, 'Install') == ['WantedBy=sockets.target'])
        check('ac6/units', 'the service unit has the entry, the connection as standard output and a time limit, and '
              'no NoNewPrivileges and no sandboxing setting [%s]' % settings(service_unit, 'Service'),
              settings(service_unit, 'Service') == ['ExecStart=@PYTHON@ -I -B @EXECUTABLE@ reader-exec',
                                                    'StandardInput=null', 'StandardOutput=socket',
                                                    'StandardError=null', 'RuntimeMaxSec=60']
              and not [line for line in service_unit.split('\n')
                       if line and not line.startswith(('#', '[')) and line not in settings(service_unit, 'Service')
                       and line != 'Description=Veldo process reader (one read)'])
        authority = (services / 'veldo-authority.service').read_text()
        check('ac6/units', 'the authority unit keeps NoNewPrivileges=yes',
              'NoNewPrivileges=yes' in settings(authority, 'Service'))

        # No probe executes the reader: with a program at the path that would answer when run, and no
        # socket, the reader is refused and the process is judged by the bound.
        direct = temporary / 'installed' / 'direct'
        direct.write_text('#!/bin/sh\nexec %s -I %s direct %s\n' % (sys.executable, standin, table_file))
        direct.chmod(0o755)
        seam(path=str(direct), pin=digest(direct), socket=str(temporary / 'none.sock'))
        facts = ask(item, shown_elsewhere)
        ran = subprocess.run([str(direct)], stdout=subprocess.PIPE, timeout=60)
        check('ac6/reads-through-the-socket', 'run by hand, the program at the path answers with a whole table',
              ran.returncode == 0 and P.reader_table(ran.stdout, header=True)[1] is None)
        check('ac6/reads-through-the-socket', 'the probe does not run it: with no socket the reader is refused and the '
              'process is judged by the bound [%s %s]' % (state(facts), counted(facts, sealed.pid)),
              state(facts) == 'refused:no_socket' and counted(facts, sealed.pid) == 'bound')

        # The unit's entry executes the descriptor it checked, also when the file is swapped between.
        stub = '#include <stdio.h>\nint main(int argc, char **argv, char **envp)\n{\n    int count = 0;\n' \
               '    (void)argc;\n    while (envp[count])\n        count++;\n' \
               '    printf("%s %%d %%s\\n", count, argv[0]);\n    return 0;\n}\n'
        programs = {}
        for name in ('checked', 'other'):
            folder = Path(tempfile.mkdtemp(prefix='stub-', dir=str(temporary)))
            (folder / 'stub.c').write_text(stub % name)
            subprocess.run(BUILD + ['-o', name, 'stub.c'], cwd=str(folder),
                           env={'PATH': '/usr/bin:/bin', 'TMPDIR': str(folder)},
                           check=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=300)
            programs[name] = folder / name
        driver = temporary / 'driver.py'
        driver.write_text(DRIVER)

        def entry_run(act, pin=None):
            target = temporary / 'installed' / 'entry'
            shutil.copy(str(programs['checked']), str(target))
            swapped = temporary / 'installed' / 'entry-other'
            shutil.copy(str(programs['other']), str(swapped))
            done = subprocess.run([sys.executable, '-I', str(driver), str(PRODUCTION['control_space_probe.py']),
                                   str(target), str(swapped), pin or digest(programs['checked']), CAP_V2.hex(), act],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env={'PATH': '/usr/bin:/bin', 'VELDO_0344_MARK': 'set'}, timeout=120)
            return done, digest(target)

        done, _ = entry_run('plain')
        check('ac6/executes-the-checked-descriptor', 'the entry executes the reader with an empty environment and the '
              'name veldo-procread [%r %r]' % (done.stdout, done.stderr[-200:]),
              done.stdout == b'checked 0 veldo-procread\n' and done.returncode == 0)
        done, now = entry_run('swap')
        check('ac6/executes-the-checked-descriptor', 'with the file swapped between the check and the execution, the '
              'program that was checked is the one that ran [%r; the path now holds the other: %s]'
              % (done.stdout, now == digest(programs['other'])),
              done.stdout == b'checked 0 veldo-procread\n' and now == digest(programs['other']))
        done, _ = entry_run('plain', pin=digest(programs['other']))
        check('ac6/refused-executes-nothing', 'with a digest that is not the pinned one the entry executes nothing '
              '[%s %r]' % (done.returncode, done.stdout), done.returncode == 1 and done.stdout == b'')

        units = temporary / 'units'
        laid = subprocess.run([sys.executable, '-I', str(PRODUCTION['control_space_probe.py']), 'reader-units',
                               str(units)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=120)
        written = {name: (units / name).read_text() if (units / name).is_file() else '' for name in P.READER_UNITS}
        check('ac6/reader-units', 'reader-units writes the two units with the interpreter and the entry filled in '
              '[%s %r]' % (laid.returncode, laid.stderr[-200:]),
              laid.returncode == 0 and written['veldo-procread.socket'] == socket_unit
              and 'ExecStart=%s -I -B %s reader-exec\n' % (os.path.realpath(sys.executable),
                                                         PRODUCTION['control_space_probe.py'].resolve())
              in written['veldo-procread@.service'] and '@' not in written['veldo-procread@.service'].split('[Unit]')[1])
        usage = subprocess.run([sys.executable, '-I', str(PRODUCTION['control_space_probe.py']), 'reader-exec', 'x'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        check('ac6/reader-units', 'an unknown command line is refused with status 2', usage.returncode == 2)

        # The installed row: only where the owner has installed the reader.
        present, runner = os.path.lexists(P.READER), shutil.which('systemd-run')
        if present and runner:
            ran = subprocess.run(['systemd-run', '--user', '--wait', '--pipe', '--quiet', '-p', 'NoNewPrivileges=yes',
                                  '-p', 'UMask=0077', '-p', 'KillMode=mixed', os.path.realpath(sys.executable), '-I',
                                  str(PRODUCTION['control_space_probe.py'].resolve()), 'reader'],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            said = ran.stdout.decode('utf-8', 'replace')
            print('  VELDO-0344 ac6/installed: ' + said.split('\n')[0])
            rows['ac6/installed'] = [('under the authority unit\'s properties the reader check reports the state used '
                                      'with cap=1, reads the undumpable process and its second thread, and finds a '
                                      'whole block for process 1, which is root\'s and closed to the probe itself, '
                                      'and reads the run label of the undumpable process and of process 1: '
                                      'six PASS lines [%s %s]' % (ran.returncode, said[-500:]),
                                      ran.returncode == 0 and 'state used cap=1' in said and 'FAIL' not in said
                                      and said.count('PASS: ') == 6
                                      and 'PASS: process 1, root-owned and closed to the probe itself, has a whole '
                                          'block with its start time' in said
                                      and 'PASS: the run label of the undumpable process, whose environment is '
                                          'closed to the probe itself, is read' in said)]
        elif present:
            print('  SELFTEST SKIP: VELDO-0344 ac6/installed: the process reader is installed at %s, but systemd-run is '
                  'not on the path of this run, so the row cannot start the check under the authority unit\'s '
                  'properties' % P.READER)
        else:
            print('  SELFTEST SKIP: VELDO-0344 ac6/installed: the process reader is not installed at %s on this host; '
                  'the row runs after the owner\'s setup (docs/veldo-procread-setup.txt)' % P.READER)

        # ---- AC7 ------------------------------------------------------------------------------------
        lines = setup.split('\n')
        first = [line for line in lines if line.startswith('d=$(mktemp -d)')]
        second = [line for line in lines if line.startswith('sudo sh -c')]
        ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        ENVIRONMENT.update(GIT_TERMINAL_PROMPT='0', LC_ALL='C', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')

        def git(where, *argv):
            done = subprocess.run(['/usr/bin/git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                   '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-C', str(where)]
                                  + list(argv), env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=120)
            if done.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
            return done.stdout.decode().strip()

        checkout = temporary / 'checkout'
        (checkout / 'scripts').mkdir(parents=True)
        git(checkout, 'init', '-q', '-b', 'main')
        (checkout / 'scripts' / 'veldo_procread.c').write_text(source)
        git(checkout, 'add', 'scripts/veldo_procread.c')
        git(checkout, 'commit', '-q', '-m', 'the reader')
        approved = git(checkout, 'rev-parse', 'HEAD')
        scratch = temporary / 'tmp'
        scratch.mkdir()

        def first_line(path='/usr/bin:/bin'):
            """Run the setup text's first line in the fixture checkout: (the digest it prints, the
            folder it built in)."""
            if len(first) != 1 or ' C:scripts/veldo_procread.c' not in first[0]:
                return None, None
            # The line's env -i drops TMPDIR, so cc would put its intermediate files in /tmp, which the
            # gate's confinement does not grant; run here, they go to the line's own folder "$d". Only
            # where cc keeps its intermediates changes; the program it writes does not.
            line = first[0].replace(' C:scripts/', ' %s:scripts/' % approved)
            if line.count('env -i PATH=/usr/bin:/bin ') != 1:
                return 'failed: the line has not exactly one env -i PATH=/usr/bin:/bin', None
            line = line.replace('env -i PATH=/usr/bin:/bin ', 'env -i PATH=/usr/bin:/bin TMPDIR="$d" ')
            done = subprocess.run(['/bin/bash', '-c', line],
                                  cwd=str(checkout), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=300,
                                  env={'PATH': path, 'TMPDIR': str(scratch), 'HOME': str(temporary),
                                       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
            said = done.stdout.decode().split()
            return (said[0], os.path.dirname(said[1])) if done.returncode == 0 and len(said) == 2 else (
                'failed: ' + done.stderr.decode()[-200:], None)

        one, two = first_line(), first_line()
        check('ac7/reproducible', 'the setup text\'s first line, run twice, builds in two folders and prints one digest '
              '[%s %s]' % (one[0], two[0]),
              one[0] == two[0] and one[1] != two[1] and one[1] is not None and re.fullmatch('[0-9a-f]{64}', one[0] or ''))
        again = build(source)
        check('ac7/reproducible', 'the suite\'s own two builds of the source, in two folders, have that digest too',
              digest(reader) == digest(again) == one[0] and reader.parent != again.parent)
        check('ac7/reproducible', 'the build line is the house line: static, with the prefix map of its folder',
              len(first) == 1 and ' -std=c11 -O2 -Wall -Wextra -Werror -static -ffile-prefix-map="$d"=. -o '
              in first[0] and '(cd "$d" && ' in first[0])
        image = Path(reader).read_bytes()
        offset, size, count = struct.unpack_from('<Q', image, 0x20)[0], *struct.unpack_from('<HH', image, 0x36)
        check('ac7/reproducible', 'the build is static: the program has no interpreter segment [%d segments]' % count,
              image[:5] == b'\x7fELF\x02' and count > 0
              and 3 not in [struct.unpack_from('<I', image, offset + index * size)[0] for index in range(count)])

        record = ROOT / 'proof' / 'VELDO-0344' / 'reader.sha256'
        recorded = record.read_text().split('\n') if record.is_file() else ['']
        compiler = subprocess.run(['/usr/bin/cc', '--version'], stdout=subprocess.PIPE, env={'PATH': '/usr/bin:/bin'},
                                  timeout=60).stdout.decode().split('\n')[0]
        library = subprocess.run(['/usr/bin/ldd', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 env={'PATH': '/usr/bin:/bin'}, timeout=60).stdout.decode().split('\n')[0]
        versions = dict(line.split(': ', 1) for line in recorded[1:] if ': ' in line)
        check('ac7/recorded-digest', 'the proof bundle records a digest with the versions of the compiler and the C '
              'library [%s]' % recorded[:3],
              re.fullmatch('[0-9a-f]{64}  veldo-procread', recorded[0]) is not None
              and versions.get('cc') and versions.get('libc'))
        if versions.get('cc') == compiler and versions.get('libc') == library:
            check('ac7/recorded-digest', 'on the recorded compiler and C library the build has the recorded digest '
                  '[%s]' % digest(reader), recorded[0].split()[0] == digest(reader))
        else:
            print('  SELFTEST SKIP: VELDO-0344 ac7/recorded-digest equality: this host builds with %r and %r, the '
                  'record with %r and %r' % (compiler, library, versions.get('cc'), versions.get('libc')))

        stand_in = temporary / 'stand-in-compiler'
        stand_in.mkdir()
        (stand_in / 'cc').write_text('#!/bin/sh\nwhile [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done\n'
                                     'echo stand-in > "$out"\n')
        (stand_in / 'cc').chmod(0o755)
        shutil.copy(str(stand_in / 'cc'), str(stand_in / 'gcc'))
        got = first_line('%s:/usr/bin:/bin' % stand_in)
        check('ac7/compiler-not-from-path', 'with a stand-in cc first in the path the line still builds with '
              '/usr/bin/cc [%s]' % got[0], got[0] == one[0])
        check('ac7/compiler-not-from-path', 'the line names the compiler by its path, under an empty environment',
              len(first) == 1 and 'env -i PATH=/usr/bin:/bin /usr/bin/cc ' in first[0])

        # The sudo line (review of VELDO-0344, finding 1): root copies its standard input into a
        # temporary file of its own, compares that copy with the digest, and only then sets the owner,
        # the mode and the capability and moves the file into place. A failure removes the copy.
        order = [second[0].find(step) if len(second) == 1 else -1
                 for step in ('sudo sh -c "umask 077 && ',
                              't=\\$(mktemp /usr/local/lib/veldo/.veldo-procread.XXXXXX) && ',
                              'if cat > \\"\\$t\\" && ',
                              'echo \'H  \'\\"\\$t\\" | sha256sum -c - >/dev/null; then ',
                              'chown root:\'$g\' \\"\\$t\\" && ',
                              'chmod 0750 \\"\\$t\\" && ',
                              'setcap cap_sys_ptrace=ep \\"\\$t\\" && ',
                              'mv -f \\"\\$t\\" /usr/local/lib/veldo/veldo-procread || ',
                              '; else rm -f \\"\\$t\\"; ',
                              'exit 1; fi" < "$d/veldo-procread" && rm -r "$d"')]
        check('ac7/setcap-after-digest', 'root copies its input into a temporary file of its own under umask 077, '
              'compares that copy with the digest written into the line, and only then sets the owner, the mode and '
              'the capability and moves the file into place [%s]' % order,
              -1 not in order and order == sorted(order)
              and all(second[0].count(word) == 1 for word in ('setcap', 'sha256sum', 'chown', 'mktemp', 'mv ', 'cat ')))
        script = second[0].split(' < "$d/veldo-procread" && rm -r "$d"')[0] if len(second) == 1 else '$d'
        check('ac7/setcap-after-digest', 'root is given no path of the owner\'s: the build reaches it as the standard '
              'input the owner\'s shell opened, and the line ends with that redirection',
              len(second) == 1 and '$d' not in script and second[0].count('$d') == 2
              and second[0].endswith('fi" < "$d/veldo-procread" && rm -r "$d"')
              and "install -D" not in second[0])
        check('ac7/setcap-after-digest', 'a comparison that fails and a step after it that fails both remove the copy '
              'and end with status 1; the folder is given mode 0755 only when the line made it',
              len(second) == 1
              and '|| { rm -f \\"\\$t\\"; echo \'the install failed: nothing installed\' >&2; exit 1; }; else '
                  'rm -f \\"\\$t\\"; echo \'digest differs: nothing installed\' >&2; exit 1; fi"' in second[0]
              and '{ [ -d /usr/local/lib/veldo ] || { mkdir -p /usr/local/lib/veldo && chmod 0755 '
                  '/usr/local/lib/veldo; }; } && t=' in second[0]
              and second[0].count('chmod 0755') == 1)

        blob = git(checkout, 'rev-parse', approved + ':scripts/veldo_procread.c')
        (temporary / 'other.c').write_text('int main(void)\n{\n    return 7;\n}\n')
        replacement = git(checkout, 'hash-object', '-w', str(temporary / 'other.c'))
        git(checkout, 'replace', blob, replacement)
        shown = git(checkout, 'show', approved + ':scripts/veldo_procread.c')
        got = first_line()
        check('ac7/no-replace-objects', 'in a checkout with a replace ref for the blob, git show gives the other source',
              shown.startswith('int main(void)') and 'veldo-procread' not in shown)
        check('ac7/no-replace-objects', 'and the first line still builds the source of the commit [%s]' % got[0],
              got[0] == one[0])
        check('ac7/no-replace-objects', 'the line reads the blob of a commit with cat-file under --no-replace-objects',
              len(first) == 1 and '/usr/bin/git --no-replace-objects cat-file blob C:scripts/veldo_procread.c > '
              in first[0] and 'git show' not in first[0])

        words = ' '.join(setup.split())
        check('ac7/digest-from-the-review-record', 'the setup text says the commit is named by its full hash',
              'the commit you approved, written as its full hash. Not a branch name and not a short form.' in words)
        check('ac7/digest-from-the-review-record', 'and that the digest is copied from the review record the owner '
              'approved and is not read back from the checkout',
              'Copy H from the review record you approved for C. Do not read it back from the checkout' in words
              and 'not from proof/VELDO-0344/reader.sha256 as the checkout shows it' in words)
        check('ac7/digest-from-the-review-record', 'the text carries the unit and the check lines of the design',
              'python3 -I .veldo/control_space_probe.py reader-units && systemctl --user daemon-reload && systemctl '
              '--user enable --now veldo-procread.socket' in words
              and '\npython3 -I .veldo/control_space_probe.py reader\n' in setup
              and 'sudo setcap -r /usr/local/lib/veldo/veldo-procread' in setup)

        # ---- The installation's key, Signal's deferral, the canon -------------------------------------
        C = load('v344_control_space_config', PRODUCTION['control_space_config.py'])
        section = {'enabled': True, 'time_zone': 'UTC', 'pools': {'host': {'floor': 1, 'needs': {
            'build': 1, 'review': 1, 'gate': 1}}}, 'engines': ['default'],
            'scratch_roots': {'roots': ['/tmp/veldo-scratch'], 'session_pattern': '{session_id}'},
            'build_roots': [], 'plain_repositories': [], 'client_accounts': [],
            'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [], 'networks': [],
                        'compose_projects': []}}

        def read_key(*value):
            given = dict(section, **({'process_reader': value[0]} if value else {}))
            try:
                return C.check(given)['process_reader']
            except Exception as error:
                return 'refused: %s %s' % (getattr(error, 'reason', type(error).__name__), getattr(error, 'key', ''))

        pin = 'a' * 64
        check('config/process-reader', 'a section without the key reads none, the word none reads none and a digest '
              'reads itself [%s %s %s]' % (read_key(), read_key('none'), read_key(pin)),
              read_key() == 'none' and read_key('none') == 'none' and read_key(pin) == pin)
        check('config/process-reader', 'anything else is refused as malformed, by the key\'s name [%s]'
              % [read_key(value) for value in (pin.upper(), pin[:63], 12, True, 'yes')],
              all(read_key(value) == 'refused: malformed space.process_reader'
                  for value in (pin.upper(), pin[:63], 12, True, 'yes', ['x'])))
        check('config/process-reader', 'the nine required keys are unchanged, and the key is no mode',
              len(C.KEYS) == 9 and 'process_reader' not in C.KEYS and C.OPTIONAL_KEYS == ('process_reader',))

        S = load('v344_control_space_signal', PRODUCTION['control_space_signal.py'])
        seam()
        table_file.write_bytes(shown_in_item)
        served.update(mode='honest', argv=None)
        record_of = {'kind': 'scratch', 'locator': {'path': str(item)}}
        ledger = types.SimpleNamespace(engines=())
        found = S._rule_process_use(ledger, P, 'item', record_of, {'run': None, 'proc': None, 'borrow_root': None})
        check('signal/deferral-names-the-reader', 'rule 4\'s refusal carries the reader\'s state and names the process '
              'by process id, task, uid and fact, with the device and inode number [%s]'
              % ((found or {}).get('reader'),),
              found is not None and found['reader']['state'] == 'used'
              and [(user['pid'], user['uid'], use['how'], use['tid'], use['device'], use['inode'])
                   for user in found['processes'] if user['pid'] == sealed.pid for use in user['uses']]
              == [(sealed.pid, ME, 'cwd', sealed.pid) + numbers(item)]
              and not any('path' in use for user in found['processes'] if user.get('by') == 'reader'
                          for use in user['uses']))
        seam(pin='none')
        found = S._rule_process_use(ledger, P, 'item', record_of, {'run': None, 'proc': None, 'borrow_root': None})
        check('signal/deferral-names-the-reader', 'with the reader refused the refusal says which check failed, and the '
              'process is named with the reason it stayed unread counted [%s]' % ((found or {}).get('reader'),),
              found is not None and found['reader']['state'] == 'refused:no_pin'
              and sealed.pid in [entry['pid'] for entry in found['unread']['processes']])
        P.SEAM['reader'] = None

        pairs = [('engine/scripts/veldo_procread.c', 'scripts/veldo_procread.c'),
                 ('engine/.veldo/services/veldo-procread.socket', '.veldo/services/veldo-procread.socket'),
                 ('engine/.veldo/services/veldo-procread@.service', '.veldo/services/veldo-procread@.service'),
                 ('engine/.veldo/control_space_probe.py', '.veldo/control_space_probe.py'),
                 ('engine/.veldo/control_space_config.py', '.veldo/control_space_config.py'),
                 ('engine/.veldo/control_space_signal.py', '.veldo/control_space_signal.py')]
        check('reader/canon', 'the engine canon equals this repository\'s copies',
              all((ROOT / canon).is_file() and (ROOT / canon).read_bytes() == (ROOT / copy).read_bytes()
                  for canon, copy in pairs))
        check('reader/canon', 'the source and the setup text are ASCII with no tab',
              all(ord(letter) < 128 and letter != '\t' for letter in source + setup))
        stop(sealed)
    except Exception as error:
        import traceback
        check('reader/canon', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)
    finally:
        try:
            P.SEAM['reader'] = None
        except Exception:
            pass
        if listener is not None:
            listener.close()
        for process in children + spawned:
            if process.poll() is None:
                process.kill()
                process.wait()
        for folder in closed:
            try:
                os.chmod(str(folder), 0o755)
            except OSError:
                pass
        shutil.rmtree(temporary, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0344 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v344_process_reader_suite()
