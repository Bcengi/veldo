#!/usr/bin/env python3
"""VELDO-0220: the gate takes the owner's host lock and runs in a delegated scope of its own.

scripts/gate_host.json is the authority's host configuration, read beside this file, never from a
candidate: the lock path every heavy run on the host serializes on, the scope's memory limit and
out-of-memory score, and the load the gate needs. With no file verify.sh never calls this helper, so
a gate without one (every adopter's) takes no lock and makes no scope, exactly as before.

verify.sh, before its first check, asks `--inside`. That answers yes (exit 0, the stamp's host field
on stdout) only when this process already runs under a gate that holds the host: inside a gate scope
the kernel places it in (its /proc/self/cgroup beneath the scope verify.sh's holder named), or below
a live holder process when /proc/locks names that holder, or a process above it, as holding the
configured lock. An environment variable alone never answers yes. Otherwise verify.sh execs `--enter`, which becomes the gate's holder:

  1. prints the load the gate needs;
  2. takes the lock with an exclusive flock on its own open descriptor (close-on-exec, so no
     candidate inherits it; the kernel releases it when the holder exits on any path). A lock held by
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
  5. runs verify.sh again as its only child, with the scope and the host record in the environment,
     forwards SIGTERM, SIGINT and SIGHUP to it, has the kernel kill it if the holder dies, and exits
     with its status.

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


# Who holds the lock: the kernel's table, read by inode.

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


def holders(lock):
    """The pids /proc/locks names as holding a flock on `lock` (blocked waiters excluded)."""
    try:
        info = os.stat(lock)
        table = Path('/proc/locks').read_text()
    except OSError:
        return []
    device = '%02x:%02x:%d' % (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
    pids = []
    for line in table.splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[1] == 'FLOCK' and fields[3] == 'WRITE' and fields[5] == device:
            pids.append(int(fields[4]))
    return pids


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


def forget_holder(lock):
    try:
        if json.loads(holder_file(lock).read_text()).get('pid') == os.getpid():
            holder_file(lock).unlink()
    except (OSError, ValueError, AttributeError):
        pass


def own_cgroup():
    return Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()


def make_scope(scope):
    """Put this process in a new delegated user scope, in its leaf, and return the scope's cgroup."""
    pid = os.getpid()
    name = 'veldo-gate-%d-%s.scope' % (pid, secrets.token_hex(4))
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
        raise Refused('the user manager refused %s: %s' % (name, (run.stderr or run.stdout).strip()))
    deadline = time.monotonic() + 30
    while not own_cgroup().endswith('/' + name):
        if time.monotonic() > deadline:
            raise Refused('the user manager did not move the gate into %s' % name)
        time.sleep(0.05)
    cgroup = own_cgroup()
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
        Path('/proc/self/oom_score_adj').write_text(str(scope['oom_score_adj']))
    except OSError as error:
        raise Refused('the scope %s could not be delegated: %s' % (name, error))
    if limit != str(scope['memory_max']):
        raise Refused('the scope %s has memory.max %s, not %d' % (name, limit, scope['memory_max']))
    return name, cgroup


def pdeathsig():
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG


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
    try:
        if fd is not None:
            record_holder(lock, root)
        env = dict(os.environ)
        for name in (SCOPE_ENV, HOLDER_ENV, RECORD_ENV):
            env.pop(name, None)
        record = {'lock': lock, 'held': 'taken' if fd is not None else 'caller',
                  'waited_seconds': round(waited, 1), 'scope': None}
        if config['scope'] is not None:
            try:
                name, cgroup = make_scope(config['scope'])
            except Refused as error:
                print('GATE: RED (gate scope could not be created: %s)' % error, flush=True)
                return 1
            print('== gate host: running in scope %s (memory.max %s, oom_score_adj %d); gate processes in %s/%s'
                  % (name, gib(config['scope']['memory_max']), config['scope']['oom_score_adj'], name, LEAF),
                  flush=True)
            env[SCOPE_ENV] = cgroup
            record.update(scope=name, memory_max=config['scope']['memory_max'],
                          oom_score_adj=config['scope']['oom_score_adj'])
        env[HOLDER_ENV] = str(os.getpid())
        env[RECORD_ENV] = json.dumps(record, sort_keys=True, separators=(',', ':'))
        # Descriptors the caller handed the gate (a launcher marker) stay open; the lock does not.
        child = subprocess.Popen(['bash', *argv], env=env, close_fds=False, preexec_fn=pdeathsig)
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(number, lambda signum, frame: child.send_signal(signum))
        code = child.wait()
        return 128 - code if code < 0 else code
    finally:
        if fd is not None:
            forget_holder(lock)


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
