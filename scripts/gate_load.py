#!/usr/bin/env python3
"""The load generator of the gate's load-proof leg (VELDO-0358, AC12).

A gate's verdict must not depend on how busy the machine is. The leg proves it by running suites on
a machine that is deliberately far busier than any gate has been, and this module makes that load.
It builds the load BY CONSTRUCTION and proves it BY LIVENESS. It measures nothing to decide
anything: no reading of how slow the host is ever becomes a verdict.

THE LEVEL (the design's section 10.1).

  CPU     The leg's suites and three spinners per CPU are bound by CPU affinity to the same set of K
          CPUs, K being the leg's slots. A spinner never blocks, so a suite process on a CPU of the
          set shares it with three always-runnable tasks and gets at most a quarter of it. That is
          the scheduler's fair share between tasks of one cgroup, which is why the spinners run in
          the SAME cgroup as the suites: between two cgroups the kernel shares a CPU by group, and a
          lone suite process beside a group of spinners would get far more than a quarter.
  Memory  The leg's cgroup gets the memory.high it is handed: 60 percent of the peak the previous
          leg recorded for the same set at the same concurrency, or none on the first leg and where
          the gate has no delegated scope. memory.max is never lowered, so nothing is killed.
  Disk    One writer per four CPUs of the set writes, flushes and removes a 256 MiB file, turn by
          turn on each directory it is given (the file systems of the scratch root and of the
          checkout). The file has no name from the moment it exists, so it is gone on every path,
          a kill included. The writers run in a cgroup beside the leg's, so their page cache is
          not charged to the suites' memory.high.

THE PROOF. Every generator process is a child of the process that started the generator, held by a
pidfd from its fork. At the end each must still be alive (its pidfd not readable), each spinner must
have consumed CPU and each writer must have written bytes. Anything else is `load_not_applied`,
which is red: a defect of the leg, like any other failed check. The slowdown probe (one CPU-second
of work on a CPU of the set; the kernel's own account of the time it ran and the time it waited to
run), the memory.events high count and the canary's result are DATA in the record and judge nothing.

TEARDOWN ON EVERY PATH. stop() kills and reaps every generator and removes the cgroups; the context
manager calls it on any exception. A generator also asks the kernel to kill it when the process that
started it dies (PR_SET_PDEATHSIG), so a leg that is killed outright leaves none either.

THE CANARY (the design's section 10.3) is the test of the generator itself: a child does a tenth of
a CPU-second of work and writes a marker; the parent sleeps 0.2 seconds and reads it. Alone the work
takes a tenth of a second and the canary is green. At a quarter of a CPU it takes at least 0.4
seconds and the canary is red. A canary that is green under the generator means the leg is not
loading. Its sleep is the one sleep here, and it is the subject of the test, never a wait.

This module waits on events only: a readiness byte on a pipe, a child's exit, a cgroup's
cgroup.events. It reads no wall or monotonic clock.

  gate_load.py --slots N --write-dir DIR [--write-dir DIR] [--scope CGROUP] [--memory-high BYTES]
               -- command...      run one command under the load; `load: start` and `load: record`
                                  lines carry the records; exit 1 with load_not_applied
  gate_load.py --canary           the canary alone: exit 0 green, 1 red
  gate_load.py --enter SPEC -- command...   (internal) bind to the set, enter the cgroup, exec
"""
import argparse
import ctypes
import json
import mmap
import os
from pathlib import Path
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
import types

# The two hang bounds of the design's section 6, with the values scripts/suites/support/waits.py
# exports them at. This module runs from the authority as python3 -I -S and imports nothing of the
# candidate's, so it names them here, once, for the gate's own tooling; nothing else here is a duration.
HANG = types.SimpleNamespace(WAIT_HANG_SECONDS=600, PROCESS_HANG_SECONDS=3600)
WAIT_HANG_SECONDS, PROCESS_HANG_SECONDS = HANG.WAIT_HANG_SECONDS, HANG.PROCESS_HANG_SECONDS

SPINNERS_PER_CPU = 3
CPUS_PER_WRITER = 4
WRITER_BYTES = 256 * 1024 * 1024
WRITER_CHUNK = 1024 * 1024
MEMORY_HIGH_PERCENT = 60
PROBE_CPU_SECONDS = 1.0
CANARY_CPU_SECONDS = 0.1
CANARY_SLEEP_SECONDS = 0.2
NOT_APPLIED = 'load_not_applied'
CGROUP_ROOT = Path('/sys/fs/cgroup')
PR_SET_PDEATHSIG = 1
_COUNTER = struct.Struct('QQ')  # a writer's bytes written and files completed


class Refused(ValueError):
    pass


def _die_with(parent):
    """Ask the kernel to kill this process when the one that started it dies, however it dies."""
    ctypes.CDLL(None, use_errno=True).prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0)
    if os.getppid() != parent:  # it died before the request was in place
        os._exit(0)


def burn(cpu_seconds):
    """Consume this much CPU time, counted on the process's own CPU clock."""
    start = time.process_time()
    while time.process_time() - start < cpu_seconds:
        pass


def exited(pidfd):
    """Whether the process behind a pidfd has ended: its pidfd is readable from then on."""
    return bool(select.select([pidfd], [], [], 0)[0])


def anonymous_file(directory):
    """A file on the directory's file system that has no name, so no path leaves it behind."""
    try:
        return os.open(str(directory), os.O_TMPFILE | os.O_WRONLY, 0o600)
    except OSError:
        fd, path = tempfile.mkstemp(prefix='.veldo-load-', dir=str(directory))
        os.unlink(path)
        return fd


def canary():
    """True when green: the marker of a tenth of a CPU-second of work is there after 0.2 seconds."""
    directory = tempfile.mkdtemp(prefix='veldo-canary-')
    marker = os.path.join(directory, 'marker')
    try:
        child = os.fork()
        if child == 0:
            try:
                burn(CANARY_CPU_SECONDS)
                os.close(os.open(marker, os.O_CREAT | os.O_WRONLY, 0o600))
            finally:
                os._exit(0)
        time.sleep(CANARY_SLEEP_SECONDS)  # the canary's subject: a test synchronized by a sleep
        seen = os.path.exists(marker)
        os.waitpid(child, 0)
        return seen
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def scope_cgroup(scope):
    """The directory of a delegated cgroup scope this process is in or under, or Refused."""
    scope = str(scope)
    if not scope.startswith('/') or '..' in Path(scope).parts:
        raise Refused('invalid cgroup scope %r' % scope)
    own = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
    if not (own == scope or own.startswith(scope.rstrip('/') + '/')):
        raise Refused('the cgroup scope %s is not an ancestor of this process' % scope)
    return CGROUP_ROOT / scope.lstrip('/')


def _empty(cgroup):
    """Kill everything in a cgroup, wait on cgroup.events until it is empty, and remove it."""
    try:
        (cgroup / 'cgroup.kill').write_text('1')
        with open(cgroup / 'cgroup.events') as events:
            while True:
                events.seek(0)
                if 'populated 0' in events.read():
                    break
                # The kernel reports a change of cgroup.events as an exceptional condition on it.
                if not select.select([], [], [events], HANG.WAIT_HANG_SECONDS)[2]:
                    return 'cgroup %s still populated after the wait hang bound' % cgroup.name
        cgroup.rmdir()
    except OSError as error:
        return 'cgroup %s: %s' % (cgroup.name, error)
    return None


class Generator:
    """The load of one leg. start() returns the start record, stop() the load record; wrap() is the
    command that runs a leg's suite inside the load. Start it from the main thread: a generator is
    tied to the life of the thread that forked it."""

    def __init__(self, slots, write_dirs, scope=None, memory_high=None, cpus=None):
        available = sorted(os.sched_getaffinity(0))
        if not isinstance(slots, int) or slots < 1:
            raise Refused('slots must be a positive integer')
        # The set: as many CPUs as the leg has slots, the highest numbered this process may use.
        self.cpus = sorted(cpus) if cpus is not None else available[-min(slots, len(available)):]
        self.slots = slots
        self.write_dirs = [str(d) for d in write_dirs]
        if not self.write_dirs:
            raise Refused('a writer needs at least one directory')
        self.scope = scope_cgroup(scope) if scope else None
        self.memory_high = memory_high
        self.writers_wanted = max(1, -(-len(self.cpus) // CPUS_PER_WRITER))
        self.generators = []
        self.cgroup = self.writers_cgroup = None
        self.counters = None
        self.probe = None
        self.memory = {}
        self.start_record = None
        self.started = self.stopped = False
        self.record = None

    # ---- the generator processes -----------------------------------------------------------

    def _fork(self, kind, body, cgroup, cpus, **facts):
        """One generator: forked, tied to this process's life, in its cgroup, bound to its CPUs,
        and known to be running its body (a readiness byte) before this returns."""
        ready, tell = os.pipe()
        parent = os.getpid()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(ready)
                _die_with(parent)
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                if cgroup is not None:
                    (cgroup / 'cgroup.procs').write_text(str(os.getpid()))
                os.sched_setaffinity(0, cpus)
                os.write(tell, b'1')
                os.close(tell)
                body()
            finally:
                os._exit(1)
        os.close(tell)
        item = dict(kind=kind, pid=pid, pidfd=os.pidfd_open(pid), **facts)
        self.generators.append(item)
        told = os.read(ready, 1)
        os.close(ready)
        if told != b'1':
            raise Refused('a %s did not start' % kind)
        return item

    @staticmethod
    def _spin():
        while True:  # the load: always runnable, never blocks
            pass

    def _write(self, slot):
        chunk = b'\0' * WRITER_CHUNK
        written = files = 0
        while True:
            for directory in self.write_dirs:
                fd = anonymous_file(directory)
                for _ in range(WRITER_BYTES // WRITER_CHUNK):
                    written += os.write(fd, chunk)
                    _COUNTER.pack_into(self.counters, slot * _COUNTER.size, written, files)
                os.fsync(fd)
                os.close(fd)  # the file had no name: closing it removes it
                files += 1
                _COUNTER.pack_into(self.counters, slot * _COUNTER.size, written, files)

    @staticmethod
    def _measure(tell):
        """The slowdown probe: a fixed amount of CPU work, and the kernel's account of how long the
        process ran and how long it waited to run while doing it. Data, never a verdict."""
        burn(PROBE_CPU_SECONDS)
        try:
            ran, waited = (int(v) for v in Path('/proc/self/schedstat').read_text().split()[:2])
            reading = {'ran_ns': ran, 'waited_ns': waited, 'slowdown': round((ran + waited) / ran, 3)}
        except (OSError, ValueError, ZeroDivisionError) as error:
            reading = {'unavailable': str(error)}
        os.write(tell, json.dumps(reading).encode())
        os.close(tell)
        signal.pause()

    # ---- start ---------------------------------------------------------------------------------

    def start(self):
        if self.started:
            raise Refused('the generator was already started')
        if threading.current_thread() is not threading.main_thread():
            raise Refused('the generator is started from the main thread only')
        self.started = True
        try:
            self.start_record = self._start()
        except BaseException:
            self.stop()  # whatever was started is ended before the failure is reported
            raise
        return self.start_record

    def _start(self):
        memory = {'high': None, 'applied': 'none: no delegated scope'}
        if self.scope is not None:
            self.cgroup = self.scope / ('load-%d' % os.getpid())
            self.writers_cgroup = self.scope / ('load-%d-writers' % os.getpid())
            self.cgroup.mkdir()
            self.writers_cgroup.mkdir()
            memory['applied'] = 'none: no earlier leg recorded a peak for this set'
            if self.memory_high:
                (self.cgroup / 'memory.high').write_text(str(int(self.memory_high)))
                memory = {'high': int(self.memory_high),
                          'applied': '%d percent of the previous peak' % MEMORY_HIGH_PERCENT}
        self.memory = memory
        self.counters = mmap.mmap(-1, max(1, self.writers_wanted) * _COUNTER.size)
        for cpu in self.cpus:
            for _ in range(SPINNERS_PER_CPU):
                self._fork('spinner', self._spin, self.cgroup, {cpu}, cpu=cpu)
        for slot in range(self.writers_wanted):
            self._fork('writer', lambda slot=slot: self._write(slot), self.writers_cgroup, set(self.cpus),
                       slot=slot)
        result, tell = os.pipe()
        self.probe = self._fork('probe', lambda: self._measure(tell), self.cgroup, {self.cpus[0]}, result=result)
        self.generators.remove(self.probe)  # the probe is data; the load is the spinners and writers
        os.close(tell)
        return {'cpus': self.cpus, 'slots': self.slots,
                'spinners': [g['pid'] for g in self.generators if g['kind'] == 'spinner'],
                'writers': [g['pid'] for g in self.generators if g['kind'] == 'writer'],
                'probe': self.probe['pid'], 'memory': memory,
                'cgroup': str(self.cgroup) if self.cgroup else None}

    def wrap(self, argv):
        """The command that runs argv as a suite of the leg: bound to the set, in the leg's cgroup."""
        spec = json.dumps({'cpus': self.cpus, 'cgroup': str(self.cgroup) if self.cgroup else None})
        return [sys.executable, '-I', '-S', str(Path(__file__).resolve()), '--enter', spec, '--', *argv]

    # ---- stop ----------------------------------------------------------------------------------

    def _reap(self, item):
        try:
            os.kill(item['pid'], signal.SIGKILL)
        except ProcessLookupError:
            pass
        _, status, usage = os.wait4(item['pid'], 0)
        os.close(item['pidfd'])
        return status, round(usage.ru_utime + usage.ru_stime, 3)

    def stop(self):
        """Read the proof, end every generator and return the load record. Safe to call twice."""
        if self.stopped or not self.started:
            return self.record
        self.stopped = True
        spinners, writers, problems = [], [], []
        # The proof is read first: who is still alive at the leg's end, before anything is ended.
        for item in self.generators:
            item['alive'] = not exited(item['pidfd'])
        memory = dict(self.memory)
        if self.cgroup is not None:
            try:
                events = dict(line.split() for line in (self.cgroup / 'memory.events').read_text().splitlines())
                memory['high_events'] = int(events.get('high', 0))
                memory['peak'] = int((self.cgroup / 'memory.peak').read_text())
            except (OSError, ValueError) as error:
                memory['unreadable'] = str(error)
        for item in self.generators:
            _, cpu = self._reap(item)
            if item['kind'] == 'spinner':
                spinners.append({'pid': item['pid'], 'cpu': item['cpu'], 'alive': item['alive'], 'cpu_seconds': cpu})
                if not item['alive']:
                    problems.append('spinner %d on CPU %d was not alive at the end' % (item['pid'], item['cpu']))
                elif not cpu > 0:
                    problems.append('spinner %d on CPU %d consumed no CPU' % (item['pid'], item['cpu']))
            else:
                written, files = _COUNTER.unpack_from(self.counters, item['slot'] * _COUNTER.size)
                writers.append({'pid': item['pid'], 'alive': item['alive'], 'bytes': written, 'files': files,
                                'cpu_seconds': cpu})
                if not item['alive']:
                    problems.append('writer %d was not alive at the end' % item['pid'])
                elif not written > 0:
                    problems.append('writer %d wrote no bytes' % item['pid'])
        wanted = len(self.cpus) * SPINNERS_PER_CPU
        if len(spinners) != wanted or len(writers) != self.writers_wanted:
            problems.append('%d of %d spinners and %d of %d writers were started'
                            % (len(spinners), wanted, len(writers), self.writers_wanted))
        probe = {'unfinished': 'the leg ended before one CPU-second of probe work'}
        if self.probe is not None:
            if select.select([self.probe['result']], [], [], 0)[0]:
                try:
                    probe = json.loads(os.read(self.probe['result'], 4096).decode() or 'null') or probe
                except ValueError:
                    pass
            os.close(self.probe['result'])
            self._reap(self.probe)
        for cgroup in (self.cgroup, self.writers_cgroup):
            if cgroup is not None:
                left = _empty(cgroup)
                if left:
                    problems.append(left)
        self.record = {'schema': 'veldo.gate-load/v1', 'cpus': self.cpus, 'slots': self.slots,
                       'spinners_per_cpu': SPINNERS_PER_CPU, 'spinners': spinners, 'writers': writers,
                       'memory': memory, 'probe': probe, 'applied': not problems,
                       'error': NOT_APPLIED if problems else None, 'problems': problems}
        return self.record

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False


def summary(record):
    """The lines a leg prints about its load, all of it data except the last."""
    spinners, writers = record['spinners'], record['writers']
    lines = ['load: %d CPUs %s, %d spinners per CPU: %d of %d alive to the end, CPU consumed %.1fs (least %.3fs)'
             % (len(record['cpus']), record['cpus'], record['spinners_per_cpu'],
                sum(1 for s in spinners if s['alive']), len(spinners),
                sum(s['cpu_seconds'] for s in spinners), min([s['cpu_seconds'] for s in spinners] or [0])),
             'load: %d writers: %d alive to the end, bytes written %s'
             % (len(writers), sum(1 for w in writers if w['alive']), [w['bytes'] for w in writers]),
             'load: memory %s; probe %s (data, no verdict)'
             % (json.dumps(record['memory'], sort_keys=True), json.dumps(record['probe'], sort_keys=True))]
    if not record['applied']:
        lines.append('load: %s: %s' % (NOT_APPLIED, '; '.join(record['problems'])))
    return lines


def enter(spec, argv):
    """Become a suite of the leg: tied to the leg's life, in its cgroup, bound to its CPUs."""
    spec = json.loads(spec)
    _die_with(os.getppid())
    if spec.get('cgroup'):
        (Path(spec['cgroup']) / 'cgroup.procs').write_text(str(os.getpid()))
    os.sched_setaffinity(0, spec['cpus'])  # the same CPUs the spinners are on
    os.execvp(argv[0], argv)


def _terminated(signum, frame):
    raise SystemExit(128 + signum)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['--enter']:
        return enter(argv[1], argv[3:] if argv[2:3] == ['--'] else argv[2:])
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--canary', action='store_true')
    parser.add_argument('--slots', type=int)
    parser.add_argument('--write-dir', action='append', default=[])
    parser.add_argument('--scope')
    parser.add_argument('--memory-high', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.canary:
        green = canary()
        print('canary: %s' % ('green' if green else 'red'), flush=True)
        return 0 if green else 1
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not args.slots or not command:
        parser.error('--slots and a command are required')
    signal.signal(signal.SIGTERM, _terminated)
    try:
        generator = Generator(args.slots, args.write_dir or [tempfile.gettempdir()], scope=args.scope,
                              memory_high=args.memory_high)
        with generator:
            print('load: start %s' % json.dumps(generator.start_record, sort_keys=True), flush=True)
            code = subprocess.run(generator.wrap(command), stdin=subprocess.DEVNULL).returncode
    except Refused as error:
        print('load: %s: %s' % (NOT_APPLIED, error), flush=True)
        return 1
    record = generator.record
    print('load: record %s' % json.dumps(record, sort_keys=True), flush=True)
    for line in summary(record):
        print(line, flush=True)
    return code if record['applied'] else (code or 1)


if __name__ == '__main__':
    sys.exit(main())
