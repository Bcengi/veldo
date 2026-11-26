#!/usr/bin/env python3
"""VELDO-0220: the gate takes the owner's host lock and runs in a delegated scope of its own.

scripts/gate_host.json is the authority's host configuration, read beside this file, never from a
candidate: the lock path every heavy run on the host serializes on, the scope's memory limit and
out-of-memory score, and the load the gate needs. With no file verify.sh never calls this helper, so
a gate without one (every adopter's) takes no lock and makes no scope, exactly as before.

verify.sh, before its first check, asks `--inside`. That answers yes (exit 0, the stamp's host field
on stdout) only when this process already runs under a gate that holds the host: inside a gate scope
the kernel places it in (its /proc/self/cgroup beneath the scope verify.sh's holder named), or below
a live holder process when its descriptor record names that holder, or a process above it, as holding the
configured lock. An environment variable alone never answers yes. Otherwise verify.sh execs
`--enter`, which becomes the gate's holder:

  1. prints the load the gate needs;
  2. takes the lock with an exclusive flock on its own open descriptor (close-on-exec, so no
     candidate inherits it; a keeper retains custody until all scope processes have stopped). A lock held by
     one of the gate's own ancestors (a caller that runs `flock -x <lock> verify.sh`, as the owner's
     core runner does) is the caller's hold for this gate and is used as it is. A lock held by anyone
     else is NOT STARTED: the holder recorded beside the lock is printed, then
     `GATE: NOT STARTED (...)`, and the exit is 75 (EX_TEMPFAIL) with no stamp and no event, unless
     VELDO_GATE_HOST_WAIT names the seconds to wait for it;
  3. records its process id, commit and start time in <lock>.holder;
  4. when the configuration states a scope, asks the user manager for a transient scope holding its
     own process id with Delegate=yes and the stated MemoryMax, moves itself into the scope's leaf
     `gate/`, enables the cpu, memory and pids controllers for the scope's children (so per-worker
     and per-node cgroups can be made beside the leaf), and sets its oom_score_adj to the stated
     score, which every gate process inherits. A scope that cannot be made is RED by name;
  5. runs verify.sh again as a child, with the scope and the host record in the environment,
     exits on SIGTERM, SIGINT and SIGHUP or with the child status. A keeper outside the scope
     detects holder death, kills the scope and waits for it to empty before releasing the lock.

Standard library only; Linux (flock, /proc, cgroup v2, the systemd user manager through busctl).
"""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import select
import socket
import subprocess
import sys
import time

SCHEMA = 'veldo.gate-host/v1'
HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'gate_host.json'
NOT_STARTED = 75
WAIT = 'VELDO_GATE_HOST_WAIT'
# What the holder hands its child: the scope's cgroup, the holder's pid and the stamp's host field.
SCOPE_ENV = 'VELDO_GATE_SCOPE'
HOLDER_ENV = 'VELDO_GATE_HOST_HOLDER'
RECORD_ENV = 'VELDO_GATE_HOST'
CGROUP_ROOT = Path('/sys/fs/cgroup')
LEAF = 'gate'
SCOPE_NAME = re.compile(r'veldo-gate-[0-9]+-[0-9a-f]+\.scope')
CONTROLLERS = ('cpu', 'memory', 'pids')
SIZE = re.compile(r'([0-9]+)([KMGT]?)')
UNITS = {'': 1, 'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4}


class Refused(Exception):
    pass


def size(value, what):
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    found = SIZE.fullmatch(value) if isinstance(value, str) else None
    if not found or int(found.group(1)) <= 0:
        raise Refused('%s must be a positive byte count or a size like 16G' % what)
    return int(found.group(1)) * UNITS[found.group(2)]


def load(path=CONFIG):
    """The validated configuration: {lock, scope (None or {memory_max, oom_score_adj}), load}."""
    try:
        document = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise Refused('%s is unreadable: %s' % (path, error))
    if not isinstance(document, dict) or document.get('schema') != SCHEMA:
        raise Refused('%s is not %s' % (path, SCHEMA))
    lock = document.get('lock')
    if not isinstance(lock, str) or not lock:
        raise Refused('lock must name a path')
    if lock.startswith('~/'):
        lock = str(Path(pwd.getpwuid(os.getuid()).pw_dir) / lock[2:])
    if not os.path.isabs(lock) or '..' in Path(lock).parts:
        raise Refused('lock must be an absolute path')
    needs = document.get('load')
    if (not isinstance(needs, dict) or not isinstance(needs.get('cores'), (int, float))
            or isinstance(needs.get('cores'), bool) or needs['cores'] <= 0
            or not isinstance(needs.get('source'), str)):
        raise Refused('load must state cores, memory and their source')
    needs = dict(needs, memory=size(needs.get('memory'), 'load.memory'))
    scope = document.get('scope')
    if scope is not None:
        if not isinstance(scope, dict):
            raise Refused('scope must be an object')
        score = scope.get('oom_score_adj')
        if not isinstance(score, int) or isinstance(score, bool) or not -1000 <= score <= 1000:
            raise Refused('scope.oom_score_adj must be an integer from -1000 to 1000')
        scope = {'memory_max': size(scope.get('memory_max'), 'scope.memory_max'), 'oom_score_adj': score}
    return {'lock': lock, 'scope': scope, 'load': needs}


def gib(value):
    return '%g GiB' % round(value / 1024 ** 3, 2)


# Who holds the lock: descriptor-local lock records, matched by device and inode.

def ppid(pid):
    try:
        stat = Path('/proc/%d/stat' % pid).read_text()
    except OSError:
        return None
    return int(stat.rsplit(')', 1)[1].split()[1])


def ancestors(pid=None):
    found, pid = [], ppid(pid or os.getpid())
    while pid and pid not in found:
        found.append(pid)
        pid = ppid(pid)
    return found


def holders(lock, proc_root=Path('/proc')):
    """Read descriptor-local flock records; an open descriptor alone proves no hold.

    Deduplicate inherited descriptors by the lock owner's PID, not the descriptor
    holder's PID. Disappearing processes/descriptors are normal during this scan.
    """
    try:
        info = os.stat(lock)
        processes = list(Path(proc_root).iterdir())
    except OSError:
        return []
    device = (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
    owners = set()
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            descriptors = list((process / 'fdinfo').iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                lines = descriptor.read_text().splitlines()
            except OSError:
                continue
            for line in lines:
                fields = line.split()
                if (len(fields) < 7 or fields[0] != 'lock:' or fields[2] != 'FLOCK'
                        or fields[4] != 'WRITE'):
                    continue
                try:
                    major, minor, inode = fields[6].split(':')
                    identity = (int(major, 16), int(minor, 16), int(inode))
                    owner = int(fields[5])
                except ValueError:
                    continue
                if identity == device and owner > 0:
                    owners.add(owner)
    return sorted(owners)


def holder_file(lock):
    return Path(lock + '.holder')


def describe(lock):
    """The holder as recorded beside the lock, when the kernel agrees it holds the lock."""
    live = holders(lock)
    try:
        record = json.loads(holder_file(lock).read_text())
    except (OSError, ValueError):
        record = None
    if isinstance(record, dict) and record.get('pid') in live:
        return 'pid %s (commit %s, root %s, since %s)' % (
            record['pid'], record.get('commit') or 'unknown', record.get('root') or 'unknown',
            record.get('started') or 'unknown')
    if live:
        return 'pid %d (no holder recorded)' % live[0]
    return 'a holder not recorded'


def inside(config):
    """The stamp's host field when this process already runs under a gate holding the host, else None."""
    try:
        record = json.loads(os.environ.get(RECORD_ENV) or 'null')
    except ValueError:
        record = None
    if not isinstance(record, dict):
        record = {'lock': None, 'held': 'not recorded'}
    scope = os.environ.get(SCOPE_ENV, '')
    if scope and SCOPE_NAME.fullmatch(Path(scope).name):
        try:
            own = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
        except (OSError, IndexError):
            own = ''
        if own == scope or own.startswith(scope + '/'):
            return record
    holder = os.environ.get(HOLDER_ENV, '')
    mine = ancestors()
    if holder.isdigit() and int(holder) in mine and is_holder(int(holder)):
        # The lock is the holder's own, or its caller's above it.
        above = set(mine[mine.index(int(holder)):])
        if any(pid in above for pid in holders(config['lock'])):
            return record
    return None


def is_holder(pid):
    try:
        argv = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
    except OSError:
        return False
    return b'--enter' in argv and any(Path(os.fsdecode(a)).name == 'gate_host.py' for a in argv)


# The holder.

def take(lock, wait):
    """(descriptor or None, 'taken' or 'caller', seconds waited), or (None, None, seconds) when held."""
    Path(lock).parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o664)
    started = time.monotonic()
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd, 'taken', time.monotonic() - started
        except BlockingIOError:
            pass
        mine = set(ancestors())
        caller = [pid for pid in holders(lock) if pid in mine]
        if caller:
            os.close(fd)
            return None, 'caller pid %d' % caller[0], time.monotonic() - started
        if time.monotonic() - started >= wait:
            os.close(fd)
            return None, None, time.monotonic() - started
        time.sleep(min(0.2, max(0.0, wait - (time.monotonic() - started))))


def commit_of(root):
    guard = HERE.parent / '.veldo/candidate_git.py'
    if not root or not guard.is_file():
        return None
    try:
        run = subprocess.run([sys.executable, '-I', '-S', str(guard), '--root', root, '--', 'rev-parse',
                              '--verify', 'HEAD'], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    value = run.stdout.strip()
    return value if run.returncode == 0 and re.fullmatch('[0-9a-f]{40,64}', value) else None


def record_holder(lock, root):
    body = {'pid': os.getpid(), 'commit': commit_of(root), 'root': root,
            'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    path = holder_file(lock)
    temporary = path.with_name(path.name + '.%d' % os.getpid())
    temporary.write_text(json.dumps(body, sort_keys=True) + '\n')
    os.replace(temporary, path)


def forget_holder(lock, pid=None):
    try:
        if json.loads(holder_file(lock).read_text()).get('pid') == (pid or os.getpid()):
            holder_file(lock).unlink()
    except (OSError, ValueError, AttributeError):
        pass


def own_cgroup(pid=None):
    return Path('/proc/%s/cgroup' % (pid or 'self')).read_text().split('::', 1)[1].strip()


def make_scope(scope, pid=None, state=None):
    """Put pid in a delegated user scope and its leaf; retain cleanup state on partial failure."""
    pid = pid or os.getpid()
    state = state if state is not None else {}
    name = 'veldo-gate-%d-%s.scope' % (pid, secrets.token_hex(4))
    state['name'] = name
    properties = [('PIDs', 'au', '1', str(pid)), ('Delegate', 'b', 'true'),
                  ('MemoryMax', 't', str(scope['memory_max'])), ('CPUAccounting', 'b', 'true'),
                  ('MemoryAccounting', 'b', 'true'), ('TasksAccounting', 'b', 'true'),
                  ('CollectMode', 's', 'inactive-or-failed'),
                  ('Description', 's', 'Veldo gate (VELDO-0220)')]
    command = ['busctl', '--user', 'call', 'org.freedesktop.systemd1', '/org/freedesktop/systemd1',
               'org.freedesktop.systemd1.Manager', 'StartTransientUnit', 'ssa(sv)a(sa(sv))', name, 'fail',
               str(len(properties))] + [part for prop in properties for part in prop] + ['0']
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        raise Refused('the user manager could not be asked: %s' % error)
    if run.returncode:
        state.clear()  # A rejected StartTransientUnit created no scope.
        raise Refused('the user manager refused %s: %s' % (name, (run.stderr or run.stdout).strip()))
    deadline = time.monotonic() + 30
    while not own_cgroup(pid).endswith('/' + name):
        if time.monotonic() > deadline:
            raise Refused('the user manager did not move the gate into %s' % name)
        time.sleep(0.05)
    cgroup = own_cgroup(pid)
    state['cgroup'] = cgroup
    base = CGROUP_ROOT / cgroup.lstrip('/')
    try:
        (base / LEAF).mkdir()
        (base / LEAF / 'cgroup.procs').write_text(str(pid))
        available = (base / 'cgroup.controllers').read_text().split()
        wanted = [c for c in CONTROLLERS if c in available]
        if 'memory' not in wanted:
            raise Refused('the scope %s has no memory controller to delegate' % name)
        (base / 'cgroup.subtree_control').write_text(' '.join('+' + c for c in wanted))
        limit = (base / 'memory.max').read_text().strip()
        Path('/proc/%d/oom_score_adj' % pid).write_text(str(scope['oom_score_adj']))
    except OSError as error:
        raise Refused('the scope %s could not be delegated: %s' % (name, error))
    if limit != str(scope['memory_max']):
        raise Refused('the scope %s has memory.max %s, not %d' % (name, limit, scope['memory_max']))
    return name, cgroup


def stop_scope(state):
    """Kill through the cgroup, then keep custody until no process in any child is live."""
    cgroup = state.get('cgroup')
    if not cgroup and state.get('name'):
        # Creation may have moved the holder just before it died or delegation failed.
        run = subprocess.run(['systemctl', '--user', 'show', state['name'],
                              '--property=ControlGroup', '--value'],
                             capture_output=True, text=True, timeout=60)
        if run.returncode:
            raise Refused('cannot inspect scope ' + state['name'])
        cgroup = run.stdout.strip()
    if not cgroup:
        return
    base = CGROUP_ROOT / cgroup.lstrip('/')
    while True:
        try:
            if 'populated 1' not in (base / 'cgroup.events').read_text():
                return
            (base / 'cgroup.kill').write_text('1')
        except FileNotFoundError:
            return
        time.sleep(0.02)


def group_live(pgid):
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                return True
        except (OSError, ValueError, IndexError):
            pass
    return False


def keep_lock(channel, parent, config):
    """EOF plus parent exit starts mandatory teardown; the keeper exits as soon as it completes.

    Forked before the scope exists, this keeper retains the close-on-exec lock descriptor
    outside it. No stage inherits the descriptor. Even SIGKILL of the holder leaves custody
    here until cgroup.kill has emptied the scope. A pidfd avoids PID reuse and startup races.
    """
    state, pgid = {}, None
    parent_fd = os.pidfd_open(parent)
    try:
        try:
            if config['scope'] is not None:
                name, cgroup = make_scope(config['scope'], parent, state)
                channel.send(json.dumps({'name': name, 'cgroup': cgroup}).encode())
            else:
                channel.send(b'{}')
        except (OSError, Refused, subprocess.SubprocessError) as error:
            channel.send(json.dumps({'error': str(error)}).encode())
        while True:
            message = channel.recv(4096)
            if not message:
                break
            pgid = json.loads(message)['pgid']
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        channel.close()
        # The holder itself lives in the scope. Wait for its exit before killing the scope
        # so normal green and red statuses reach the caller intact.
        select.select([parent_fd], [], [])
        os.close(parent_fd)
        while True:
            try:
                if config['scope'] is not None:
                    stop_scope(state)
                elif pgid is not None:
                    # Lock-only installations have no cgroup: the command's private group
                    # is registered before exec, including on a parent-death startup race.
                    while group_live(pgid):
                        os.killpg(pgid, signal.SIGKILL)
                        time.sleep(0.02)
                break
            except ProcessLookupError:
                break
            except (OSError, Refused, subprocess.SubprocessError) as error:
                # A teardown error must never release the lock over live work.
                print('gate host: waiting for scope cleanup: %s' % error, file=sys.stderr, flush=True)
                time.sleep(0.2)
        forget_holder(config['lock'], parent)


def start_keeper(config, fd):
    parent = os.getpid()
    channel, keeper_channel = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    pid = os.fork()
    if pid == 0:
        # A terminal or caller process-group signal must not kill custody along with the gate.
        os.setpgid(0, 0)
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(number, signal.SIG_IGN)
        channel.close()
        try:
            keep_lock(keeper_channel, parent, config)
        finally:
            os._exit(0)
    keeper_channel.close()
    ready = json.loads(channel.recv(4096))
    if 'error' in ready:
        channel.close()
        raise Refused(ready['error'])
    return channel, ready


def prepare_child(channel, parent):
    os.setsid()
    channel.send(json.dumps({'pgid': os.getpid()}).encode())
    channel.close()
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG
    if os.getppid() != parent:
        os.kill(os.getpid(), signal.SIGKILL)


def enter(argv, root):
    holder = os.environ.get(HOLDER_ENV, '')
    if holder.isdigit() and int(holder) == os.getppid() and is_holder(int(holder)):
        # The gate this holder started did not find itself inside it: never start another holder.
        print('GATE: RED (the gate does not run inside the lock and scope its holder pid %s made)' % holder,
              flush=True)
        return 1
    try:
        config = load()
    except Refused as error:
        print('GATE: RED (gate host configuration invalid: %s)' % error, flush=True)
        return 1
    needs, lock = config['load'], config['lock']
    print('== gate host: this gate needs %g cores and %s of memory (%s)'
          % (needs['cores'], gib(needs['memory']), needs['source']), flush=True)
    wait = os.environ.get(WAIT, '0') or '0'
    try:
        wait = float(wait)
        if not 0 <= wait < float('inf'):
            raise ValueError(wait)
    except ValueError:
        print('GATE: RED (%s must be a number of seconds, not %r)' % (WAIT, os.environ.get(WAIT)), flush=True)
        return 1
    try:
        fd, held, waited = take(lock, wait)
    except OSError as error:
        print('GATE: RED (host lock %s cannot be opened: %s)' % (lock, error), flush=True)
        return 1
    if held is None:
        holder = describe(lock)
        print('== gate host: lock %s is held by %s; waited %.1fs of %gs' % (lock, holder, waited, wait), flush=True)
        print('GATE: NOT STARTED (host lock %s held by %s)' % (lock, holder), flush=True)
        return NOT_STARTED
    if fd is None:
        print('== gate host: lock %s is held for this gate by its %s' % (lock, held), flush=True)
    else:
        print('== gate host: took lock %s after %.1fs' % (lock, waited), flush=True)
    channel = None
    try:
        if fd is not None:
            record_holder(lock, root)
        env = dict(os.environ)
        for name in (SCOPE_ENV, HOLDER_ENV, RECORD_ENV):
            env.pop(name, None)
        record = {'lock': lock, 'held': 'taken' if fd is not None else 'caller',
                  'waited_seconds': round(waited, 1), 'scope': None}
        try:
            channel, ready = start_keeper(config, fd)
        except Refused as error:
            print('GATE: RED (gate scope could not be created: %s)' % error, flush=True)
            return 1
        if config['scope'] is not None:
            name, cgroup = ready['name'], ready['cgroup']
            print('== gate host: running in scope %s (memory.max %s, oom_score_adj %d); gate processes in %s/%s'
                  % (name, gib(config['scope']['memory_max']), config['scope']['oom_score_adj'], name, LEAF),
                  flush=True)
            env[SCOPE_ENV] = cgroup
            record.update(scope=name, memory_max=config['scope']['memory_max'],
                          oom_score_adj=config['scope']['oom_score_adj'])
        env[HOLDER_ENV] = str(os.getpid())
        env[RECORD_ENV] = json.dumps(record, sort_keys=True, separators=(',', ':'))
        # Descriptors the caller handed the gate (a launcher marker) stay open; the lock does not.
        parent = os.getpid()
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(number, lambda signum, frame: sys.exit(128 + signum))
        child = subprocess.Popen(['bash', *argv], env=env, close_fds=False,
                                 preexec_fn=lambda: prepare_child(channel, parent))
        code = child.wait()
        return 128 - code if code < 0 else code
    finally:
        if channel is not None:
            channel.close()
        if fd is not None:
            os.close(fd)


# Weekly admission is separate from the legacy entry: no existing launcher changes
# behavior until its host is explicitly enrolled and the common gate switch enables it.
def weekly_occupancy(config, own_pids=(), proc_root=Path('/proc')):
    """All-user process census. Unknown visibility is occupied, regardless of CPU use.

    Allowed services are exact executable/cgroup pairs, not process-name patterns.
    Containers, remote-run slots and agents have processes outside those pairs.
    Enrollment also requires every launcher to participate in the reservation protocol.
    """
    if config.get('enrolled') is not True:
        return 'host is not enrolled'
    if config.get('launchers_enrolled') is not True:
        return 'launchers are not enrolled'
    allowed = config.get('allowed_system_services', [])
    try:
        processes = list(Path(proc_root).iterdir())
        for process in processes:
            if not process.name.isdigit() or int(process.name) in own_pids:
                continue
            try:
                stat = (process / 'stat').read_text().rsplit(')', 1)[1].split()
                if stat[0] == 'Z':
                    continue
                # PF_KTHREAD, set by the kernel, cannot be supplied by a user task.
                if int(stat[6]) & 0x00200000:
                    continue
                executable = os.readlink(process / 'exe')
                group = (process / 'cgroup').read_text().split('::', 1)[1].strip()
            except FileNotFoundError:
                if not process.exists():
                    continue
                return 'unobservable process ' + process.name
            if dict(executable=executable, cgroup=group) not in allowed:
                return 'busy process ' + process.name
    except (OSError, ValueError, IndexError):
        return 'unobservable all-user occupancy'
    return None


class WeeklyCustody:
    """Reserve -> drain -> exclusive lock -> recheck, keeping both locks until cleanup.

    The caller retries acquire on occupancy/lock events, or cancels with close().
    Enrolled launchers use weekly_workload; they never start beside this reservation.
    The keeper owns the locks through crash cleanup and durable red settlement.
    """
    def __init__(self, lock, host, observe):
        self.lock, self.host, self.observe = str(lock), host, observe
        self.reservation = self.fd = self.channel = self.keeper = None
        self.reason = 'exclusive idle-host admission'

    @staticmethod
    def _take(path, mode):
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(fd, mode | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return None
        return fd

    def acquire(self):
        if self.reservation is None:
            self.reservation = self._take(self.lock + '.weekly', fcntl.LOCK_EX)
        if self.reservation is None:
            self.reason = 'another weekly caller holds the reservation'
            return False
        self.reason = self.observe()
        if self.reason:
            return False
        if self.fd is None:
            self.fd = self._take(self.lock, fcntl.LOCK_EX)
        if self.fd is None:
            self.reason = 'existing work is draining'
            return False
        # Work may have appeared between the census and the exclusive lock.
        return self.admitted(self.host)

    def admitted(self, host):
        if self.reservation is None or self.fd is None or host != self.host:
            self.reason = 'exclusive custody missing or wrong host'
            return False
        self.reason = self.observe()
        return self.reason is None

    def guard(self, cleanup, recover):
        """Fork before starting work. Cleanup names only this run's scope/descendants.

        recover durably settles an interrupted running record, including its outbox.
        A cleanup/persistence failure retains custody for operator repair.
        """
        if not self.admitted(self.host) or self.keeper is not None:
            raise Refused('weekly guard requires exclusive idle custody')
        channel, keeper_channel = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        pid = os.fork()
        if pid == 0:
            os.setpgid(0, 0)
            for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                signal.signal(number, signal.SIG_IGN)
            channel.close()
            groups = []
            try:
                while True:
                    message = keeper_channel.recv(4096)
                    if not message:
                        break
                    groups.append(json.loads(message)['pgid'])
                cleanup(groups)
                recover()
            except BaseException as error:
                print('weekly: custody retained (cleanup/receipt failure: %s)' % error,
                      file=sys.stderr, flush=True)
                while True:
                    signal.pause()
            finally:
                keeper_channel.close()
            os._exit(0)
        keeper_channel.close()
        self.channel, self.keeper = channel, pid

    def launch(self, argv, **kwargs):
        if self.channel is None:
            raise Refused('weekly keeper required before descendants')
        parent = os.getpid()
        return subprocess.Popen(argv, close_fds=True,
                                preexec_fn=lambda: prepare_child(self.channel, parent), **kwargs)

    def close(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.keeper is not None:
            os.waitpid(self.keeper, 0)
            self.keeper = None
        for name in ('fd', 'reservation'):
            fd = getattr(self, name)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)


def weekly_stop_groups(groups):
    """Fixture/lock-only descendant cleanup. Enrolled production uses stop_scope.

    Wait on kernel process exits, never on a timing guess; only this run's private
    process groups are signaled. A cgroup is required for workloads that can setsid.
    """
    for group in groups:
        while group_live(group):
            descriptors = []
            try:
                for path in Path('/proc').glob('[0-9]*/stat'):
                    try:
                        fields = path.read_text().rsplit(')', 1)[1].split()
                        if int(fields[2]) == group and fields[0] != 'Z':
                            descriptors.append(os.pidfd_open(int(path.parent.name)))
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    break
                if descriptors:
                    select.select(descriptors, [], [])
            finally:
                for descriptor in descriptors:
                    os.close(descriptor)


def weekly_workload(lock):
    """Launcher admission: a shared workload lock or None (wait/go elsewhere).

    Reservation and workload acquisition overlap, closing the admission race.
    Keep the returned descriptor until the workload's descendants have stopped.
    """
    reservation = WeeklyCustody._take(str(lock) + '.weekly', fcntl.LOCK_SH)
    if reservation is None:
        return None
    try:
        return WeeklyCustody._take(str(lock), fcntl.LOCK_SH)
    finally:
        os.close(reservation)


def main(argv):
    if argv[:1] == ['--inside']:
        try:
            config = load()
        except Refused:
            return 1
        record = inside(config)
        if record is None:
            return 1
        print(json.dumps(record, sort_keys=True, separators=(',', ':')))
        return 0
    if argv[:1] == ['--enter'] and len(argv) >= 5 and argv[1] == '--root' and argv[3] == '--':
        return enter(argv[4:], argv[2])
    print('usage: gate_host.py --inside | --enter --root <root> -- <verify.sh> [arguments]', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
