#!/usr/bin/env python3
"""Worker containment: host worker profiles, one containment group per dispatch, the profile's caps
installed before the worker runs, a stop of the whole group and exit detection from operating system
notifications (PLAN-0019 W25, VELDO-0040, R43, R44).

THE PROVIDER-NEUTRAL SHAPE. A host's worker profile (schema veldo.worker_profile/v1) names its
provider (`kind`) and declares its settings. The provider qualifies the profile on the host it runs on
(`qualify`), makes the dispatch's containment group around the trusted wrapper (`Group.command`,
under `Group.admission` for the concurrency cap), reads back the controls actually installed
(`Group.attach`), stops the whole group (`Stop`) and reports its emptiness through a kernel event
(`Group.events`). The receiver in control_launch.py is the one spawn point and calls these; nothing
here launches a worker on its own. This Linux box's provider is `linux-systemd`; the Mac's profile
(VELDO-0124) is another provider of the same shape.

LINUX (`linux-systemd`). Each dispatch's worker runs in its own transient systemd scope under the
owner's user manager (`systemd-run --user --scope`), named from the dispatch identity
(veldo-dispatch-<digest>.scope) in the profile's slice. systemd-run creates the scope with every
declared cap installed, moves itself into it and then becomes the trusted wrapper by exec, so the pid
the receiver spawned is contained before any engine code runs, and every descendant (a fork, a new
session or process group, a double fork) is in the same cgroup v2 group because membership is
inherited and none of those leaves it. The wrapper applies the per-process limit (RLIMIT_FSIZE),
reports its identity and waits; the receiver checks the pid is in the dispatch's own group and every
declared control is installed, and only then releases the wrapper to exec the engine.

THE SETTINGS and the mechanism that bounds each are SETTINGS below; `qualify` returns them with the
host facts, the worker identity and what this profile does not bound (UNBOUNDED). A required setting
that is absent, a setting whose value is invalid, an unknown setting and a host that cannot enforce
the profile are refused by name before anything is spawned.

STOP (R44). A stop asks the adapter to end (SIGTERM to the worker's own process), after
stop_grace_seconds sends SIGTERM to every process in the group, after kill_grace_seconds kills the
group with cgroup.kill (atomic against forks), and then waits for the group to be empty, every grace
timed on the monotonic clock. The profile also declares the trusted wrapper's heartbeat interval and
the receiver's missed-heartbeat window (VELDO-0041, control_heartbeat.py). The worker's own exit
ends its dispatch: anything left in its group is terminated and killed the same way. A group that is
still populated SETTLE_SECONDS after the kill is reported not empty, never as ended.

EXIT DETECTION. The worker's exit is a pidfd becoming readable and the group's emptiness is the
cgroup.events `populated 0` change (poll POLLPRI); the receiver sleeps in poll until one of those, its
output, a stop request or the next stop timer. Nothing polls for liveness.

RETIREMENT. `retirement` is the runner's observation for returning the worker slot (VELDO-0036's
lifecycle observer): read from the kernel at that moment, the worker's process is gone and its group
is empty (the cgroup directory is removed, which the kernel allows only when empty, or reports
populated 0). A populated group keeps the slot.

WHAT IT IS NOT. The worker runs as the owner's account, so it could write its own group's control
files or ask the same user manager for another unit; distinct worker identities through a privileged
runner helper, escape and aggregate exhaustion qualification and recovery after the receiver ends are
Release 2 (R43). Standard library only.
"""
import contextlib
import fcntl
import hashlib
import math
import os
from pathlib import Path
import re
import resource
import select
import shutil
import signal
import subprocess
import sys
import time

SCHEMA = 'veldo.worker_profile/v1'
QUALIFICATION = 'veldo.worker_qualification/v1'
LINUX = 'linux-systemd'
CGROUP = Path('/sys/fs/cgroup')
UNIT_PREFIX = 'veldo-dispatch-'
DEFAULT_SLICE = 'veldo-workers.slice'
SETTLE_SECONDS = 5.0
TOOL_SECONDS = 20
HELPER = 'systemd user manager (no OS privileges)'

# Every setting a profile may declare: whether it is required, its kind, the kernel or systemd
# controls it installs and the mechanism that bounds it on this profile.
SETTINGS = {
    'concurrency': dict(required=True, kind='count', controls=['live dispatch groups in the slice'],
                        mechanism='the receiver counts the populated dispatch groups of the profile slice and '
                                  'creates its own under one exclusive lock (flock), refusing at the cap'),
    'runtime_seconds': dict(required=True, kind='seconds', controls=['RuntimeMaxUSec'],
                            mechanism='systemd RuntimeMaxSec on the dispatch scope: the user manager stops the '
                                      'whole group at the cap whether or not the receiver runs; TimeoutStopSec '
                                      'then escalates to SIGKILL'),
    'memory_bytes': dict(required=True, kind='bytes', controls=['memory.max', 'memory.swap.max', 'OOMPolicy'],
                         mechanism='cgroup v2 memory.max (MemoryMax) with memory.swap.max 0 (MemorySwapMax), '
                                   'charged across every descendant; OOMPolicy=stop ends the group on a breach'),
    'cpu_percent': dict(required=True, kind='percent', controls=['cpu.max'],
                        mechanism='cgroup v2 cpu.max (CPUQuota) across every descendant; with the runtime cap it '
                                  'bounds cumulative CPU time to runtime_seconds x cpu_percent / 100'),
    'file_bytes': dict(required=True, kind='bytes', controls=['Max file size'],
                       mechanism='RLIMIT_FSIZE, soft and hard, set by the trusted wrapper before the engine runs '
                                 'and inherited by every descendant, which cannot raise it'),
    'tasks_max': dict(required=False, kind='count', controls=['pids.max'],
                      mechanism='cgroup v2 pids.max (TasksMax) across every descendant'),
    'stop_grace_seconds': dict(required=False, kind='seconds', default=10, controls=[],
                               mechanism='the receiver: after a cooperative stop it sends SIGTERM to every '
                                         'process in the group this long later'),
    'kill_grace_seconds': dict(required=False, kind='seconds', default=5, controls=['TimeoutStopUSec', 'KillMode'],
                               mechanism='the receiver kills the group with cgroup.kill this long after it '
                                         'terminates it; systemd TimeoutStopSec for the stops systemd makes'),
    # VELDO-0041: the trusted wrapper's heartbeat and the receiver's missed-heartbeat deadline.
    'heartbeat_seconds': dict(required=False, kind='seconds', default=10, controls=[],
                              mechanism='the trusted wrapper: its own heartbeat process, which waits on nothing '
                                        'the engine does, writes a heartbeat to the receiver this often '
                                        '(control_heartbeat)'),
    'heartbeat_window_seconds': dict(required=False, kind='seconds', default=30, controls=[],
                                     mechanism='the receiver: a worker with no heartbeat for this long has uncertain '
                                               'liveness and is stopped with the escalation above; each heartbeat '
                                               'renews the claim its contract binds'),
}
FIELDS = ('kind', 'slice', 'lock', 'systemd_run', 'systemctl')
CONTROLLERS = {'memory_bytes': 'memory', 'cpu_percent': 'cpu', 'tasks_max': 'pids'}
UNBOUNDED = {
    'storage_total': 'aggregate writable bytes and inodes across all files: no unprivileged mechanism on this '
                     'profile (a per-dispatch filesystem from the runner helper, Release 2)',
    'controls_owner': 'the group and its controls belong to the owner account the worker runs as (a distinct '
                      'worker identity through the runner helper, Release 2)',
}
_SPAN = {'us': 1, 'ms': 10 ** 3, 's': 10 ** 6, 'min': 60 * 10 ** 6, 'h': 3600 * 10 ** 6, 'd': 86400 * 10 ** 6,
         'w': 604800 * 10 ** 6, 'month': 2629800 * 10 ** 6, 'y': 31557600 * 10 ** 6}


class Refused(Exception):
    """A named refusal of a containment step. `settled` is True when nothing of the dispatch is left
    running (its group is empty or was never made); False leaves the outcome unknown."""

    def __init__(self, code, detail='', settled=True, group=None):
        self.code, self.detail, self.settled, self.group = code, detail, settled, group
        super().__init__(code + (': ' + detail if detail else ''))


def unit_name(dispatch_id):
    """The one scope a dispatch's worker runs in, derived from its dispatch identity."""
    return UNIT_PREFIX + hashlib.sha256(str(dispatch_id).encode()).hexdigest()[:32] + '.scope'


def _valid(kind, value):
    if isinstance(value, bool):
        return False
    if kind == 'count':
        return type(value) is int and 1 <= value <= 1 << 22
    if kind == 'seconds':
        return isinstance(value, (int, float)) and math.isfinite(value) and 0 < value <= 366 * 86400
    if kind == 'bytes':
        return type(value) is int and 4096 <= value <= 1 << 62
    if kind == 'percent':
        return type(value) is int and 1 <= value <= 100 * (os.cpu_count() or 1)
    return False


def setting_problems(profile):
    """The named problems of a profile, in a fixed order; [] when it is complete and valid."""
    if not isinstance(profile, dict):
        return ['invalid_input:profile:absent']
    problems = ['invalid_input:profile:unknown:' + str(name) for name in profile
                if name not in SETTINGS and name not in FIELDS]
    if not isinstance(profile.get('kind'), str) or not profile['kind']:
        problems.append('invalid_input:profile:kind:absent')
    for name, rule in SETTINGS.items():
        if name not in profile:
            if rule['required']:
                problems.append('invalid_input:profile:%s:absent' % name)
        elif not _valid(rule['kind'], profile[name]):
            problems.append('invalid_input:profile:%s:invalid' % name)
    # A window no longer than the heartbeat interval would stop every worker between two heartbeats.
    beat, window = (profile.get(name, SETTINGS[name]['default'])
                    for name in ('heartbeat_seconds', 'heartbeat_window_seconds'))
    if _valid('seconds', beat) and _valid('seconds', window) and window <= beat:
        problems.append('invalid_input:profile:heartbeat_window_seconds:invalid')
    slice_name = profile.get('slice', DEFAULT_SLICE)
    if not isinstance(slice_name, str) or not re.fullmatch(r'[A-Za-z0-9_]+(-[A-Za-z0-9_]+)*\.slice', slice_name):
        problems.append('invalid_input:profile:slice:invalid')
    for name in ('lock', 'systemd_run', 'systemctl'):
        if name in profile and not (isinstance(profile[name], str) and os.path.isabs(profile[name])):
            problems.append('invalid_input:profile:%s:invalid' % name)
    return problems


def runtime_dir(environment=None):
    """The owner's runtime directory, where the user manager listens: the environment's, or the
    standard /run/user/<uid> when it is this account's own."""
    given = (environment if environment is not None else os.environ).get('XDG_RUNTIME_DIR')
    if given:
        return given
    path = '/run/user/%d' % os.getuid()
    with contextlib.suppress(OSError):
        if os.stat(path).st_uid == os.getuid():
            return path
    return None


def tool_environment(environment=None):
    """The environment systemd's tools run with: the given one, naming the owner's runtime directory."""
    env = dict(environment if environment is not None else os.environ)
    found = runtime_dir(env)
    if found:
        env['XDG_RUNTIME_DIR'] = found
    return env


def _tool(profile, name, env):
    configured = profile.get(name.replace('-', '_'))
    path = configured or shutil.which(name, path=env.get('PATH', os.defpath))
    return path if path and os.path.isfile(path) and os.access(path, os.X_OK) else None


def _show(systemctl, env, unit, names):
    """Properties of a unit (or of the manager itself when unit is None) from the user manager."""
    command = [systemctl, '--user', 'show'] + [a for n in names for a in ('-p', n)] + ([unit] if unit else [])
    result = subprocess.run(command, capture_output=True, text=True, timeout=TOOL_SECONDS, env=env,
                            stdin=subprocess.DEVNULL)
    if result.returncode:
        raise OSError('systemctl show failed')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def span_us(text):
    """Microseconds in a time span as systemctl prints it ('1.500000s', '500ms', '1min 30s'); None for
    'infinity' or anything else."""
    total = 0.0
    for token in (text or '').split() or ['infinity']:
        match = re.fullmatch(r'(\d+(?:\.\d+)?)(us|ms|s|min|h|d|w|month|y)', token)
        if not match:
            return None
        total += float(match.group(1)) * _SPAN[match.group(2)]
    return round(total)


def _usec(seconds):
    return '%dus' % round(seconds * 10 ** 6)


def qualify(profile, environment=None):
    """Qualify `profile` on this host before anything is spawned. Returns the qualification: whether it
    is qualified, the first named refusal, every setting's value and mechanism, the host facts, the
    worker identity and what the profile does not bound."""
    env = tool_environment(environment)
    problems = setting_problems(profile)
    profile = profile if isinstance(profile, dict) else {}
    host = {'platform': sys.platform, 'runtime_dir': runtime_dir(env)}
    if not problems and profile['kind'] != LINUX:
        problems.append('unavailable_service:profile:kind')
    if not problems and not sys.platform.startswith('linux'):
        problems.append('unavailable_service:profile:platform')
    if not problems:
        problems.extend(_host_problems(profile, env, host))
    settings = {}
    for name, rule in SETTINGS.items():
        if name in profile or 'default' in rule:
            settings[name] = {'value': profile.get(name, rule.get('default')), 'mechanism': rule['mechanism'],
                              'controls': list(rule['controls'])}
    return {'schema': QUALIFICATION, 'provider': profile.get('kind'), 'qualified': not problems,
            'refusal': problems[0] if problems else None, 'problems': problems, 'settings': settings,
            'unbounded': dict(UNBOUNDED), 'host': host,
            'identity': {'worker_uid': os.getuid(), 'worker_gid': os.getgid(), 'helper': HELPER,
                         'privileged_helper': False}}


def _host_problems(profile, env, host):
    for name in ('systemd-run', 'systemctl'):
        host[name.replace('-', '_')] = _tool(profile, name, env)
        if not host[name.replace('-', '_')]:
            return ['unavailable_service:profile:' + name.replace('-', '_')]
    if not (CGROUP / 'cgroup.controllers').is_file():
        return ['unavailable_service:profile:cgroup_v2']
    try:
        manager = _show(host['systemctl'], env, None, ('Version', 'ControlGroup'))
    except (OSError, subprocess.SubprocessError, ValueError):
        return ['unavailable_service:profile:user_manager']
    if not manager.get('ControlGroup', '').startswith('/'):
        return ['unavailable_service:profile:user_manager']
    host.update(systemd=manager.get('Version'), manager_cgroup=manager['ControlGroup'])
    try:
        delegated = (CGROUP / manager['ControlGroup'].lstrip('/') / 'cgroup.subtree_control').read_text().split()
    except OSError:
        return ['unavailable_service:profile:controllers']
    host['controllers'] = sorted(delegated)
    for name, controller in CONTROLLERS.items():
        if name in profile and controller not in delegated:
            return ['unavailable_service:profile:controller:' + controller]
    return []


def _read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def cgroup_of(pid):
    """The cgroup v2 path a process is in, from /proc; None when it cannot be read."""
    text = _read('/proc/%d/cgroup' % pid) or ''
    return next((line[3:] for line in text.splitlines() if line.startswith('0::')), None)


def file_limit(pid):
    """(soft, hard) of a process's RLIMIT_FSIZE as /proc/<pid>/limits states it."""
    for line in (_read('/proc/%d/limits' % pid) or '').splitlines():
        if line.startswith('Max file size'):
            return tuple(re.split(r'\s{2,}', line.strip())[1:3])
    return None


def populated(path):
    """True or False from a group's cgroup.events; None when the group directory is gone."""
    text = _read(Path(path) / 'cgroup.events')
    if text is None:
        return None
    return 'populated 1' in text.splitlines()


def alive(process):
    """Whether the process a recorded identity names is still running on this boot."""
    if not isinstance(process, dict) or not isinstance(process.get('pid'), int):
        return False
    stat = _read('/proc/%d/stat' % process['pid'])
    boot = _read('/proc/sys/kernel/random/boot_id')
    if not stat or boot != process.get('boot_id'):
        return False
    return stat[stat.rindex(')') + 2:].split()[19] == process.get('start')


def reap(worker, seconds):
    """Wait for a spawned child by its pidfd (a kernel notification), at most `seconds`; its exit code
    or None."""
    if worker.returncode is not None:
        return worker.returncode
    fd = os.pidfd_open(worker.pid)
    try:
        poller = select.poll()
        poller.register(fd, select.POLLIN)
        if poller.poll(max(0.0, seconds) * 1000):
            return worker.wait()
    finally:
        os.close(fd)
    return None


class Group:
    """One dispatch's containment group on the linux-systemd profile. `qualification` is `qualify`'s
    answer for the same profile; `environment` is the worker's, which systemd-run carries in."""

    def __init__(self, profile, qualification, dispatch_id, environment=None):
        self.profile, self.qualification, self.dispatch_id = profile, qualification, dispatch_id
        self.unit = unit_name(dispatch_id)
        self.slice = profile.get('slice', DEFAULT_SLICE)
        self.environment = tool_environment(environment)
        self.systemctl = qualification['host']['systemctl']
        self.settings = {name: entry['value'] for name, entry in qualification['settings'].items()}
        self.cgroup, self.events, self.installed = None, None, {}

    def report(self):
        return {'unit': self.unit, 'slice': self.slice, 'cgroup': self.cgroup}

    def properties(self):
        """The declared caps as the scope's systemd properties, installed when the scope is created."""
        s = self.settings
        props = [('MemoryMax', str(s['memory_bytes'])), ('MemorySwapMax', '0'), ('CPUQuota', '%d%%' % s['cpu_percent']),
                 ('RuntimeMaxSec', _usec(s['runtime_seconds'])), ('TimeoutStopSec', _usec(s['kill_grace_seconds'])),
                 ('OOMPolicy', 'stop'), ('KillMode', 'control-group')]
        if 'tasks_max' in s:
            props.append(('TasksMax', str(s['tasks_max'])))
        return props

    def held(self):
        """What the trusted wrapper applies to itself before the engine runs; every descendant inherits it."""
        return {'file_bytes': self.settings['file_bytes']}

    def command(self, argv):
        """systemd-run creates this dispatch's scope with every cap installed, moves itself into it and
        then becomes `argv` (the trusted wrapper) by exec: the same pid, already contained."""
        head = [self.qualification['host']['systemd_run'], '--user', '--scope', '--quiet', '--unit=' + self.unit,
                '--slice=' + self.slice, '--description=Veldo dispatch ' + str(self.dispatch_id)]
        for name, value in self.properties():
            head += ['-p', '%s=%s' % (name, value)]
        return head + ['--'] + list(argv)

    def _show(self, unit, names):
        return _show(self.systemctl, self.environment, unit, names)

    def live(self):
        """The populated dispatch groups in this profile's slice, read from the kernel."""
        base = self._show(self.slice, ('ControlGroup',)).get('ControlGroup')
        if not base:
            return []
        found = []
        with contextlib.suppress(FileNotFoundError, NotADirectoryError):
            for entry in os.scandir(CGROUP / base.lstrip('/')):
                if entry.name.startswith(UNIT_PREFIX) and entry.name.endswith('.scope') and populated(entry.path):
                    found.append(entry.name)
        return sorted(found)

    @contextlib.contextmanager
    def admission(self):
        """The concurrency cap: the slice's live dispatch groups are counted and this group is created
        under one exclusive lock, so two receivers cannot both take the last place. The caller creates
        the group and sees its wrapper arrive before leaving the block."""
        path = self.profile.get('lock') or os.path.join(self.qualification['host']['runtime_dir'] or '/tmp',
                                                         'veldo', self.slice + '.lock')
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            live = self.live()
            if len(live) >= self.settings['concurrency']:
                raise Refused('unavailable_service:concurrency',
                              '%d of %d dispatch groups are live' % (len(live), self.settings['concurrency']))
            self.installed['concurrency'] = {'live_before': len(live), 'cap': self.settings['concurrency']}
            yield live
        finally:
            os.close(fd)

    def _expected(self):
        s, page = self.settings, resource.getpagesize()
        expected = {
            'memory_bytes': {'memory.max': str(s['memory_bytes'] // page * page), 'memory.swap.max': '0',
                             'OOMPolicy': 'stop'},
            'cpu_percent': {'cpu.max': '%d 100000' % (s['cpu_percent'] * 1000)},
            'runtime_seconds': {'RuntimeMaxUSec': round(s['runtime_seconds'] * 10 ** 6)},
            'kill_grace_seconds': {'TimeoutStopUSec': round(s['kill_grace_seconds'] * 10 ** 6),
                                   'KillMode': 'control-group'},
            'file_bytes': {'Max file size': (str(s['file_bytes']), str(s['file_bytes']))},
        }
        if 'tasks_max' in s:
            expected['tasks_max'] = {'pids.max': str(s['tasks_max'])}
        return expected

    def attach(self, pid):
        """Check the wrapper `pid` is in this dispatch's own group, in the profile slice, and that every
        declared control is installed, from the kernel's files and the manager's unit; then open the
        group's populated events. Returns the named problems, [] when contained as declared."""
        shown = self._show(self.unit, ('ControlGroup', 'Slice', 'RuntimeMaxUSec', 'TimeoutStopUSec', 'OOMPolicy',
                                       'KillMode'))
        cgroup = shown.get('ControlGroup') or ''
        if (not cgroup or cgroup_of(pid) != cgroup or cgroup.rsplit('/', 1)[-1] != self.unit
                or shown.get('Slice') != self.slice):
            return ['spawn_failed:containment:group']
        self.cgroup = cgroup
        path = CGROUP / cgroup.lstrip('/')
        read = {'memory.max': _read(path / 'memory.max'), 'memory.swap.max': _read(path / 'memory.swap.max'),
                'cpu.max': _read(path / 'cpu.max'), 'pids.max': _read(path / 'pids.max'),
                'RuntimeMaxUSec': span_us(shown.get('RuntimeMaxUSec')),
                'TimeoutStopUSec': span_us(shown.get('TimeoutStopUSec')),
                'OOMPolicy': shown.get('OOMPolicy'), 'KillMode': shown.get('KillMode'), 'Max file size': file_limit(pid)}
        problems = []
        for name, controls in self._expected().items():
            self.installed[name] = {control: read[control] for control in controls}
            if self.installed[name] != controls:
                problems.append('spawn_failed:containment:' + name)
        self.events = os.open(path / 'cgroup.events', os.O_RDONLY | os.O_CLOEXEC)
        return problems

    def members(self):
        text = _read(CGROUP / self.cgroup.lstrip('/') / 'cgroup.procs') if self.cgroup else None
        return [int(line) for line in (text or '').split()]

    def populated(self):
        """Whether any process is left in the group (read from its cgroup.events, which also consumes
        the pending event); False once the group directory is gone."""
        if self.events is not None:
            try:
                return b'populated 1' in os.pread(self.events, 4096, 0).splitlines()
            except OSError:
                return False
        return bool(self.cgroup and populated(CGROUP / self.cgroup.lstrip('/')))

    def terminate(self):
        """SIGTERM to every process in the group."""
        for pid in self.members():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGTERM)

    def kill(self):
        """Kill every process in the group and its descendants at once (cgroup.kill)."""
        if self.cgroup:
            with contextlib.suppress(OSError):
                (CGROUP / self.cgroup.lstrip('/') / 'cgroup.kill').write_text('1')

    def wait_empty(self, seconds):
        """Wait for the group's populated 0 event, at most `seconds`. True once empty."""
        end = time.monotonic() + seconds
        if self.events is None and self.cgroup:
            with contextlib.suppress(OSError):
                self.events = os.open(CGROUP / self.cgroup.lstrip('/') / 'cgroup.events', os.O_RDONLY | os.O_CLOEXEC)
        if self.events is None:
            return not self.populated()
        poller = select.poll()
        poller.register(self.events, select.POLLPRI | select.POLLERR)
        while self.populated():
            remaining = end - time.monotonic()
            if remaining <= 0:
                return False
            poller.poll(remaining * 1000)
        return True

    def conclude(self):
        """After the group is empty: the scope's result as systemd recorded it (`timeout` for the
        runtime cap, `oom-kill` for the memory cap), clearing a failed scope so it is not left loaded."""
        try:
            shown = self._show(self.unit, ('Result', 'ActiveState'))
            if shown.get('ActiveState') == 'failed':
                subprocess.run([self.systemctl, '--user', 'reset-failed', self.unit], capture_output=True,
                               timeout=TOOL_SECONDS, env=self.environment, stdin=subprocess.DEVNULL)
            return shown.get('Result')
        except (OSError, subprocess.SubprocessError):
            return None

    def close(self):
        if self.events is not None:
            os.close(self.events)
            self.events = None

    def discard(self, worker):
        """End a group whose engine was never released: kill everything in it (only the trusted wrapper
        can be there) and wait for it to be empty. True once it is."""
        if self.cgroup is None:
            with contextlib.suppress(OSError, subprocess.SubprocessError):
                cgroup = self._show(self.unit, ('ControlGroup',)).get('ControlGroup')
                self.cgroup = cgroup or None
        self.kill()
        with contextlib.suppress(OSError):
            os.killpg(worker.pid, signal.SIGKILL)
        reap(worker, SETTLE_SECONDS)
        empty = self.wait_empty(SETTLE_SECONDS)
        self.conclude()
        self.close()
        return empty


class Stop:
    """R44's stop of one group: cooperative (SIGTERM to the adapter's own process), SIGTERM to every
    process in the group after stop_grace, cgroup.kill after kill_grace, then SETTLE_SECONDS for the
    group to empty before it is declared not empty (`abandoned`). Every `now` is the monotonic clock
    (VELDO-0041), so a step of the wall clock neither shortens nor stretches a grace; `due` is when the
    next step falls on it, and each step records both clocks."""

    def __init__(self, group, pid, stop_grace, kill_grace):
        self.group, self.pid, self.grace = group, pid, {'cooperative': stop_grace, 'terminate': kill_grace,
                                                        'kill': SETTLE_SECONDS}
        self.cause, self.stage, self.due, self.steps = None, None, math.inf, []

    def begin(self, cause, now, adapter_alive):
        """Start stopping for `cause`; when the adapter has already exited, its group is terminated at once."""
        if self.cause is None:
            self.cause = cause
        if self.stage is None:
            self._step('cooperative' if adapter_alive else 'terminate', now)

    def adapter_exited(self, now):
        """The adapter ended while its group is not empty: what is left is terminated now."""
        if self.stage in (None, 'cooperative'):
            if self.cause is None:
                self.cause = 'exit'
            self._step('terminate', now)

    def advance(self, now):
        """Take the step that is due, if any."""
        if now < self.due:
            return
        following = {'cooperative': 'terminate', 'terminate': 'kill', 'kill': 'abandoned'}.get(self.stage)
        if following:
            self._step(following, now)

    def _step(self, stage, now):
        self.stage = stage
        self.steps.append({'step': stage, 'at': time.time(), 'monotonic': now})
        self.due = now + self.grace[stage] if stage in self.grace else math.inf
        if stage == 'cooperative':
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(self.pid, signal.SIGTERM)
        elif stage == 'terminate':
            self.group.terminate()
        elif stage == 'kill':
            self.group.kill()


def hold(held):
    """In the trusted wrapper, before the engine exists: the per-process limits every descendant inherits."""
    size = held['file_bytes']
    resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))


def released(fd=0):
    """In the trusted wrapper: wait for the receiver's release line on `fd`, read byte by byte so the
    engine's packet after it stays unread. True for `go`."""
    line = b''
    while not line.endswith(b'\n') and len(line) < 64:
        chunk = os.read(fd, 1)
        if not chunk:
            return False
        line += chunk
    return line == b'go\n'


def retirement(group, process):
    """The runner's observation for returning a dispatch's worker slot, read from the kernel now: the
    worker process has ended and its group is empty (the cgroup directory is gone, which the kernel
    allows only once it is empty, or it reports populated 0). No group means nothing was contained on
    this host (never spawned here, or another host's worker)."""
    observed = 'none'
    if isinstance(group, dict) and group.get('cgroup'):
        state = populated(CGROUP / group['cgroup'].lstrip('/'))
        observed = 'absent' if state is None else ('populated' if state else 'unpopulated')
    return {'terminated': process is None or not alive(process), 'cleaned': observed != 'populated',
            'group': dict(group or {}, observed=observed), 'observed_at': time.time()}


def status(profile, environment=None):
    """Pending work of one profile: its live dispatch groups (unit and description), from the manager."""
    qualification = qualify(profile, environment)
    if not qualification['qualified']:
        return {'qualified': False, 'refusal': qualification['refusal'], 'groups': []}
    group = Group(profile, qualification, 'status', environment)
    groups = []
    for unit in group.live():
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            groups.append({'unit': unit, 'description': group._show(unit, ('Description',)).get('Description')})
    return {'qualified': True, 'refusal': None, 'groups': groups}
