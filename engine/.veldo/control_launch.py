#!/usr/bin/env python3
"""The runner that prepares a dispatch and the trusted receiver that launches it (PLAN-0019 W24,
VELDO-0039, R31, R33).

THE RUNNER (Runner.submit, in the scheduler's process). For one admitted unit at one station it
takes the station decision from VELDO-0052's shared eligibility Gate for the holder, reads that no
dispatch holds the unit and station, makes the dispatch identity, reserves that identity's
VELDO-0036 worker slot, resolves the source commit and tree from a real Git repository, and then
PREPARES: control_dispatch commits the COMPLETE contract. Only after that commit is the receiver
invoked. A preparation the authority refuses retires the slot it reserved (nothing was spawned).

THE RECEIVER (`python3 control_launch.py <config>`, a separate trusted process the runner owns; its
config, journal key and this executable are installed outside worker clones, and a worker can select
none of them). It is handed the prepared contract, rechecks the station decision with the
preparation's decision as its ticket (admission and claim are rechecked at the accepting boundary,
not only at selection) and records its ACCEPTANCE, its durable launch record, under the original
dispatch identity. The acceptance transition itself requires the prepared record and the handed
contract's digest to match it, so the receiver launches only what the authority committed. Then,
and only then, it spawns the worker with the adapter's configured argv and exactly the recorded
configuration (never reduced), in the owner's environment plus the adapter's configured one, reads
the spawned process's OS identity and records it (`running`). It reaps the worker, killing its
session at the contract deadline, and records the termination under the same dispatch and process.
A worker's output is hashed and counted, never believed.

LAUNCH RESULTS, always read from the RECORD, never from a reply alone. accepted: the record says
running, with the OS identity stored. refused: nothing ran, by name (a receiver check failed before
acceptance, or the spawn itself failed). unknown: the receiver accepted and no conclusive launch
evidence followed (its answer was lost: it ended or overran its bound). When the receiver ends
without recording, the runner records it: a record still prepared is refused (the receiver spawns
only after its acceptance commits, and it has ended), an accepted one is unknown. An unknown dispatch
keeps its unit and station and is never launched again; a receiver asked to launch a dispatch that is
not prepared refuses and records nothing.

PROCESS IDENTITY. Linux: /proc/<pid>/stat start time (clock ticks since boot) with the boot id.
macOS: `ps -o lstart=` with kern.boottime. A local adapter's identity is read from the spawned pid.
An adapter launched through a transport to another host (the Mac, over SSH, since the authority
and its store stay on this Linux host) sets `identity: reported` and runs the trusted wrapper
(`control_launch.py exec <argv>`) there: the wrapper's first output line names its own identity
before it becomes the engine by exec, so the recorded pid and start time are the engine's. The
receiver, on the authority's host, records it.

CONTAINMENT (VELDO-0040, R43, R44). A local adapter's worker is contained by the host's worker
profile (the config's `profile`, control_containment.py): the receiver qualifies it before its
acceptance, refusing an absent, invalid or unenforceable profile by name, and the one spawn starts the
trusted wrapper (`control_launch.py exec --contained ...`) inside the dispatch's own systemd scope with
every declared cap installed, checks the wrapper is in that group with those controls, and only then
releases it to exec the engine. The reap sleeps until an OS notification (output, the worker's pidfd,
the group's populated event, a stop request from the runner on the receiver's stdin, or the next stop
timer); the worker's exit ends the dispatch, anything left in its group is stopped, and the exit is
recorded only once the group is empty. A group that cannot be emptied is recorded unknown
(`containment_not_empty`), holding its unit. The runner returns the worker slot only on its own kernel
observation that the process is gone and the group empty. Another host's worker (identity reported)
is contained by that host's profile (VELDO-0124).

HEARTBEAT AND RETIREMENT (VELDO-0041, R44). A contained worker's wrapper starts its own heartbeat
(control_heartbeat.py) just before it becomes the engine, on a channel the receiver passes it, so
liveness never waits for a model call. The receiver sleeps on that channel too: each heartbeat renews
the claim the contract binds, and a worker with no heartbeat for the profile's window has uncertain
liveness and is stopped (`heartbeat_missing`). Every stop escalates on the monotonic clock and the
supervision the receiver reports carries its steps on both clocks, its graces and the heartbeat's
account. The runner returns a worker slot through control_retirement.py, which keeps each open
obligation (termination, the outcome, the clone files and the accounting) until it is completed and
releases the slot once. A refused retirement stays pending and is retried when an obligation it waits
on is completed: at once when the retirement service observes the completion (its own clone teardown,
a final accounting report the reservation service accepts), and on the runner's sweep before each
preparation and after each wait, so none is stranded.

SUBSCRIPTION LOGIN AND USAGE (VELDO-0062). An adapter that declares an `engine` (`claude_code` or
`codex`) runs a logged-in subscription CLI. Before acceptance the receiver reads the account the
accepted contract records (its reservation's account) from the store's account records
(control_accounts): an unregistered, paused or disabled account, one of another provider, or one with
no profile on this host is refused by name, as is an adapter whose configured environment names a
login (control_accounts.refused). The engine's environment is the inherited one with every provider's
profile variable and every other login variable removed (by family, and every name the installed
binaries' lists make a login or a setting of the owner's shell, control_accounts.strips), then the
adapter's configured one as configured, and that account's own profile set (CLAUDE_CONFIG_DIR or
CODEX_HOME), never a profile the caller's environment names. After
acceptance, and before anything is spawned, the invocation (initial, retry or follow-on,
control_reservation_runtime.boundary) is checked and reserved against every applicable cap and the
account's reported rate-limit windows through VELDO-0036's InvocationGuard, bounded by the contract
deadline; a refusal is recorded by name and launches nothing. While the worker runs, the usage and
rate-limit windows the CLI's own stream reports (control_engine_claude, control_engine_codex) are
reported as they arrive, their raw lines kept as receipts in a private file and their digests in the
ledger; a cap reached stops the worker. At its end one final report settles the invocation: its count,
the wall time it took and the CLI's conclusive totals, or, when the CLI reported none, the token and
message units stay unknown and their reservation is retained. Timeout, cancellation or a missing
report never release it.

THE ENGINE PROTOCOL (VELDO-0060, VELDO-0061). Every subscription engine module (ENGINES) implements
ENGINE_PROTOCOL with the same signatures, and the receiver drives each through the one path here:
- `bind(adapter, state_root)`, before acceptance: the pinned executable the adapter runs, checked
  against the engine's installed qualification record, or `Refused` by name, so nothing is accepted,
  reserved or spawned. Claude Code's adapter names a qualified version whose pinned copy lies under the
  factory state root (the config's `state_root`); Codex's names the vendor binary inside its package.
- `command(binding, adapter)`: the engine argv. Claude Code's is the adapter's prefix (its clone
  entrance, or a transport's trusted wrapper) followed by the pinned path and the qualified flags;
  Codex's is the adapter's own argv, exactly. The receiver then checks, for every engine, that the argv
  binds what runs (`pinned_argv_problem`): what the trusted wrapper execs (a local adapter's whole argv, a
  reported adapter's argv after its transport's `control_launch.py exec`) is the pinned path itself, or
  the clone entrance (`<python> -B control_clone.py enter <clones> --`, for a local adapter the installed
  one beside this receiver, run by this receiver's own Python) and then the pinned path, followed by its
  qualified flags; anything else, a shell or a package manager's link first among them, is refused by
  name. The engine's environment names the pinned path and digest (VELDO_ENGINE_PATH,
  VELDO_ENGINE_SHA256), and whichever trusted program execs the engine (this wrapper, or the clone
  entrance) re-hashes the file immediately before the exec and refuses a changed one (exit 70, the
  engine never runs). The wrapper compares resolved paths, and passes the two names on to the clone
  entrance only: the engine inherits neither.
- `environment(binding)`: the settings the engine always runs with (DISABLE_AUTOUPDATER), set last in
  its environment; an adapter configuring one of them otherwise is refused by name.
- `Terminal()`: the terminal output decoder, fed what the meter is fed. At the end its document (one
  shape for every engine: schema, engine, verdict, complete, then the engine's own decoded fields,
  bound to the dispatch, invocation, account and pinned executable) is kept in a private file (0600 in
  a 0700 directory, beside the store unless the config names `artifacts`), and its report {path, digest,
  verdict, complete} is sent to the runner before the end. The invocation and the worker slot are
  `completed` only when the document is complete, so a zero exit without a terminal record is never a
  completion: the exit record binds the report's verdict, completeness and digest, and the runner's slot
  and the build and review floor read completion from that record through control_dispatch.completed.
- `Meter` (VELDO-0062), with PROVIDER, CREDENTIALS, SETTINGS and REGISTRATION (the lifecycle operations).
An engine module that does not implement the protocol is refused by name before acceptance.

WHAT IT IS NOT. No recovery of an unknown dispatch, leadership fencing or crash-safe retirement
(Release 2), and no model API. Standard library only.
"""
import contextlib
import errno
import hashlib
import math
import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('launch_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = _organ('control_dispatch')
S = D.S
C = _organ('control_containment')
HB = _organ('control_heartbeat')
RT = _organ('control_retirement')
# VELDO-0062: the account records (the instance the reservations module reads windows through), the
# invocation seam and each subscription engine's login and usage reports.
ACC = D.RES.ACC
RTM = _organ('control_reservation_runtime')
ENGINES = {'claude_code': _organ('control_engine_claude'), 'codex': _organ('control_engine_codex')}
# Every name either binary's lists make a login: none reaches any engine, whichever it is, and an
# adapter configuring one is refused. STRIPPED adds each binary's settings of the owner's shell, which
# the inherited environment loses and an adapter may configure.
CREDENTIALS = frozenset().union(*(engine.CREDENTIALS for engine in ENGINES.values()))
STRIPPED = CREDENTIALS.union(*(engine.SETTINGS for engine in ENGINES.values()))
# What every engine module implements, with the same signatures (THE ENGINE PROTOCOL above).
ENGINE_PROTOCOL = ('PROVIDER', 'CREDENTIALS', 'SETTINGS', 'REGISTRATION', 'Meter', 'Refused', 'bind', 'command',
                   'environment', 'Terminal')
RECEIPTS_SCHEMA = 'veldo.usage_receipts/v1'
ARTIFACT_REPORT = ('path', 'digest', 'verdict', 'complete')
RECEIVER = str(Path(__file__).resolve())
JOURNAL_NAMESPACE = 'veldo-journal'
ACCEPT_SECONDS = 30
WRAPPER_SCHEMA = 'veldo.launch_identity/v1'


# OS process identity.

def process_identity(pid):
    """{platform, host, boot_id, pid, start}: what identifies one process across pid reuse."""
    host = socket.gethostname()
    if sys.platform.startswith('linux'):
        stat = Path('/proc/%d/stat' % pid).read_text()
        # Field 22 is the start time; fields after the parenthesized command name start at 3.
        start = stat[stat.rindex(')') + 2:].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return {'platform': 'linux', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    if sys.platform == 'darwin':
        env = {'PATH': '/bin:/usr/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'}
        start = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True,
                               timeout=5, env=env).stdout.strip()
        boot = subprocess.run(['sysctl', '-n', 'kern.boottime'], capture_output=True, text=True,
                              timeout=5, env=env).stdout.strip()
        if not start or not boot:
            raise ValueError('process identity unreadable')
        return {'platform': 'darwin', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    raise ValueError('no process identity reader for ' + sys.platform)


# THE ENGINE PROTOCOL's argv check and exec-time re-hash, the same for every engine.

ENTRANCE_MODULE, WRAPPER_MODULE = 'control_clone.py', 'control_launch.py'
ENGINE_PATH, ENGINE_DIGEST = 'VELDO_ENGINE_PATH', 'VELDO_ENGINE_SHA256'
WRAPPER_REFUSED = 70


def engine_argv(argv, reported):
    """What the trusted wrapper execs: a local adapter's whole argv (the receiver starts the wrapper around
    it), a reported adapter's argv after its transport's wrapper (`control_launch.py exec`); None when a
    reported argv names no wrapper."""
    if not reported:
        return list(argv)
    for at in range(len(argv) - 2, -1, -1):
        if Path(argv[at]).name == WRAPPER_MODULE and argv[at + 1] == 'exec':
            return list(argv[at + 2:])
    return None


def entrance(engine):
    """Whether an engine argv is the clone entrance's shape: `<python> -B control_clone.py enter <clones> --`
    and then what it execs."""
    return (len(engine) > 6 and engine[1] == '-B' and Path(engine[2]).name == ENTRANCE_MODULE and engine[3] == 'enter'
            and engine[5] == '--')


def pinned_argv_problem(argv, bound, reported=False):
    """None when the argv binds what runs: the engine argv (engine_argv) is the bound pinned path, or the
    clone entrance and then the pinned path, followed by its qualified flags; else the named refusal. A
    local adapter's entrance is the installed one beside this receiver, run by this receiver's own Python."""
    path, flags = bound.get('path'), list(bound.get('flags') or [])
    engine = engine_argv(argv, reported)
    if not isinstance(path, str) or not engine:
        return 'invalid_input:engine_executable'
    at = 0
    if entrance(engine):
        if not reported and Path(engine[2]).resolve() != Path(__file__).resolve().with_name(ENTRANCE_MODULE):
            return 'invalid_input:engine_entrance'
        if not reported and os.path.realpath(engine[0]) != os.path.realpath(sys.executable):
            return 'invalid_input:engine_interpreter'
        at = 6
    if engine[at] != path:
        return 'invalid_input:engine_executable'
    if engine[at + 1:at + 1 + len(flags)] != flags:
        return 'invalid_input:engine_flags'
    return None


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


# The runner: decide, reserve, prepare the complete contract, then invoke the receiver.

def resolve_source(repository_path, revision):
    """The commit and tree `revision` names in a real Git repository."""
    _git_process = _organ('git_process')
    commit = _git_process.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{commit}'],
                              capture_output=True, text=True, timeout=20)
    tree = _git_process.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{tree}'],
                            capture_output=True, text=True, timeout=20)
    if commit.returncode or tree.returncode:
        raise D.Refused('invalid_input:source', 'the source revision does not resolve')
    return {'commit': commit.stdout.strip(), 'tree': tree.stdout.strip()}


class Runner:
    """The scheduler's side of every dispatch. `gate` is VELDO-0052's eligibility Gate, `reservations`
    VELDO-0036's service, `dispatches` a control_dispatch.Dispatches writing as the runner,
    `receiver(contract)` invokes the trusted receiver and returns its Launch, and `clones` is
    VELDO-0042's clone provisioner when dispatches use clones (its teardown retires their files).
    Every slot is returned through `retirements` (VELDO-0041): a refused retirement is kept pending
    and retried when what it waits on is completed, and `sweep()` retries every pending one that is
    due, before each preparation and after each wait."""

    def __init__(self, gate, reservations, dispatches, receiver, *, account, clock=None, clones=None):
        self.gate, self.reservations, self.dispatches = gate, reservations, dispatches
        self.receiver, self.account = receiver, account
        self.clock = clock or time.time
        self.observations = []
        self.launches = {}
        self.retirements = RT.Retirements(reservations, dispatches, clones=clones, clock=self.clock,
                                          observations=self.observations)

    def _slot(self, dispatch_id):
        entity = RES_ENTITY(self.dispatches.domain, dispatch_id)
        row = self.dispatches.conn.execute('SELECT version, digest FROM entities WHERE id=?', (entity,)).fetchone()
        if row is None:
            raise D.Refused('missing_reservation', entity)
        return entity, row[0], row[1]

    def _retire(self, dispatch_id, outcome, basis):
        """Return an ended dispatch's worker slot through the retirement service (VELDO-0041), which
        keeps the dispatch, its reported containment group and every obligation still open until the
        slot is released once. The observation is the runner's own, read from the kernel now (VELDO-0040):
        a live worker or a populated group is refused (worker_alive, cleanup_incomplete) and keeps the
        slot, pending, until an obligation it waits on is completed and the retirement is retried. A
        dispatch the runner asked to stop is accounted as cancelled."""
        launch = self.launches.pop(dispatch_id, None)
        if launch is not None:
            self.retirements.track(dispatch_id, group=getattr(launch, 'group', None),
                                   stop_requested=getattr(launch, 'stop_requested', False),
                                   supervision=getattr(launch, 'supervision', None))
        return self.retirements.retire(dispatch_id, outcome, basis)

    def sweep(self):
        """Retry every pending retirement whose obligations have changed since its last attempt, or whose
        clone can now be removed (VELDO-0041); the dispatches whose slots it released. Each preparation
        and each wait makes one, and a scheduler may make one at any time."""
        return self.retirements.sweep()

    def prepare(self, unit, station, *, holder, source, revision, payload, adapter, configuration,
                deadline, context=None):
        """Decide, reserve and record the complete contract; nothing is invoked. Returns the contract."""
        # Pending retirements first: a slot whose obligations have since completed is released before
        # this preparation reserves another.
        self.sweep()
        now = self.clock()
        decided = dict(context or {}, holder=holder)
        decision = self.gate.require(station, unit, context=decided)
        held = self.dispatches.active(unit, station)
        if held:
            code = 'dispatch_outcome_unknown:' if held['state'] == 'unknown' else 'active_dispatch:'
            raise D.Refused(code + held['dispatch_id'], 'one active dispatch per unit and station')
        record = self.gate.unit_record(unit) or {}
        project = record.get('project')
        if not D._text(project):
            raise D.Refused('missing_authority:project', 'the unit has no accepted project')
        claim = None
        if station in D.CLAIMED_STATIONS:
            entity = D.CLM.claim_id(self.dispatches.repository, unit)
            row = self.dispatches.conn.execute('SELECT data FROM entities WHERE id=?', (entity,)).fetchone()
            data = json.loads(row[0]) if row else {}
            claim = {'entity': entity, 'holder': data.get('holder'), 'generation': data.get('generation')}
        dispatch_id = 'dispatch/%s/%s' % (unit, uuid.uuid4().hex)
        self.reservations.reserve_worker('worker/' + dispatch_id, dispatch_id, self.account, project, unit, now=now)
        try:
            entity, version, slot_digest = self._slot(dispatch_id)
            contract = {
                'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': self.dispatches.domain,
                'repository': self.dispatches.repository, 'unit': unit, 'station': station,
                'attempt': self.dispatches.attempts(unit, station) + 1,
                'source': dict(resolve_source(source, revision), repository_uuid=self.dispatches.repository),
                'input': {'decision': {k: decision[k] for k in ('decision_id', 'station', 'unit', 'domain_uuid',
                                                                'watermark', 'inputs')},
                          'context': decided, 'payload': payload, 'payload_digest': D.digest(payload)},
                'capability': {'adapter': adapter, 'configuration': configuration,
                               'configuration_digest': D.digest(configuration)},
                'reservation': {'entity': entity, 'version': version, 'digest': slot_digest,
                                'account': self.account, 'project': project},
                'claim': claim, 'deadline': deadline, 'authority_generation': self.dispatches.generation,
            }
            self.dispatches.prepare(contract, now=now)
        except BaseException:
            self._retire(dispatch_id, 'cancelled', 'never_spawned')
            raise
        return contract

    def submit(self, unit, station, **kwargs):
        """Prepare the complete contract, then invoke the receiver: the one launch path."""
        contract = self.prepare(unit, station, **kwargs)
        launch = self.receiver(contract)
        self.launches[contract['dispatch_id']] = launch
        if launch.owned and (launch.record or {}).get('state') == 'refused':
            self._retire(contract['dispatch_id'], 'cancelled', 'never_spawned')
        return launch

    def wait(self, launch, timeout=None):
        """Wait for the launched dispatch's terminal record; a conclusive end returns its slot."""
        record = launch.wait(timeout)
        if record and record['state'] == 'exited':
            # The one completion gate (control_dispatch.completed): the exit record's clean exit and, for an
            # engine, the complete artifact it binds (THE ENGINE PROTOCOL).
            clean = D.completed(record)
            self._retire(record['dispatch_id'], 'completed' if clean else 'failed', 'worker_reaped')
        elif record and record['state'] == 'unknown':
            # Its outcome is an open obligation: the retirement keeps it, and the slot, until it is known.
            self._retire(record['dispatch_id'], 'unknown', 'outcome_unknown')
        self.launches.pop(launch.dispatch_id, None)
        # This dispatch's end may have completed another's obligation (a group the kernel emptied).
        self.sweep()
        return record


def RES_ENTITY(domain, dispatch_id):
    return D.RES.entity('worker', [domain, dispatch_id])


# The runner-side end of the receiver's pipe.

class Launch:
    """One invocation of the receiver. `result` is accepted, refused or unknown, read from the record.
    `owned` is False when the receiver refused to launch a dispatch that was not prepared: that
    invocation launched nothing, owns nothing and never writes the record. `group` is the containment
    group the receiver reported (unit, slice and cgroup), `supervision` its account of how the worker
    and its group ended, `heartbeat` the interval and window it watches the worker's heartbeat with
    (VELDO-0041), and `stop()` asks it to stop the dispatch."""

    def __init__(self, child, contract, dispatches, clock):
        self.child, self.contract, self.dispatches, self.clock = child, contract, dispatches, clock
        self.dispatch_id = contract['dispatch_id']
        self.pending = b''
        self.messages = []
        self.result = None
        self.refusal = None
        self.owned = True
        self.record = None
        self.group = None
        self.supervision = None
        self.stop_requested = False
        self.ends_by = None
        self.heartbeat = None
        self.artifact = None

    def stop(self, reason='requested'):
        """Ask the receiver to stop this dispatch: R44's cooperative stop, then the group's escalation.
        False when there is no receiver of this dispatch to ask."""
        if not self.owned or self.child is None or self.child.stdin is None:
            return False
        try:
            self.child.stdin.write((json.dumps({'stop': reason}) + '\n').encode())
            self.child.stdin.flush()
        except (OSError, ValueError):
            return False
        self.stop_requested = True
        return True

    def _message(self, deadline):
        if self.child is None:
            return None
        while b'\n' not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.child.stdout], [], [], remaining)[0]:
                return None
            chunk = os.read(self.child.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.pending += chunk
        line, _, self.pending = self.pending.partition(b'\n')
        try:
            message = json.loads(line)
        except ValueError:
            return {}
        self.messages.append(message)
        if not isinstance(message, dict):
            return {}
        if isinstance(message.get('group'), dict):
            self.group = message['group']
        if message.get('supervision') is not None:
            self.supervision = message['supervision']
        if isinstance(message.get('ends_by'), (int, float)):
            self.ends_by = message['ends_by']
        if isinstance(message.get('heartbeat'), dict):
            self.heartbeat = message['heartbeat']
        if message.get('event') == 'artifact' and isinstance(message.get('artifact'), dict):
            # The engine's artifact report {path, digest, verdict, complete} (THE ENGINE PROTOCOL).
            self.artifact = message['artifact']
        return message

    def _end_receiver(self):
        """Make the receiver's silence conclusive: it is stopped and reaped, so it writes no more."""
        if self.child is None:
            return
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=10)
        with contextlib.suppress(OSError, ValueError):
            if self.child.stdin is not None:
                self.child.stdin.close()

    def _settle(self, lost):
        """The launch result from the record. When the receiver ended without a conclusive record it
        is settled here: still prepared is refused (the receiver spawns only after its acceptance
        commits, and it has ended), accepted is unknown (a stop owed, never a second launch)."""
        record = self.dispatches.record(self.dispatch_id)
        state = (record or {}).get('state')
        digest = (record or {}).get('contract_digest')
        if lost and state == 'prepared':
            record = self.dispatches.refuse(self.dispatch_id, digest, 'receiver_unavailable', now=self.clock(),
                                            expected_state='prepared')
        elif lost and state == 'accepted':
            record = self.dispatches.unknown(self.dispatch_id, digest, 'launch_evidence_missing', now=self.clock(),
                                             expected_state='accepted')
        state = (record or {}).get('state')
        self.record = record
        self.result = {'running': 'accepted', 'exited': 'accepted', 'refused': 'refused'}.get(state, 'unknown')
        self.refusal = (record or {}).get('refusal') if state == 'refused' else None

    def start(self, accept_seconds):
        deadline = time.monotonic() + accept_seconds
        while True:
            message = self._message(deadline)
            if message is None:
                self._end_receiver()
                self._settle(lost=True)
                return self
            refusal = message.get('refusal') if message.get('event') == 'refused' else None
            if isinstance(refusal, str) and refusal.startswith('not_prepared:'):
                # This invocation launched nothing and owns nothing; the record is not its to write.
                self._end_receiver()
                self.owned, self.result, self.refusal = False, 'refused', refusal
                self.record = self.dispatches.record(self.dispatch_id)
                return self
            if message.get('event') in ('running', 'refused', 'unknown', 'exited'):
                self._settle(lost=False)
                if self.result != 'accepted':
                    self._end_receiver()
                return self

    def wait(self, timeout=None):
        """The dispatch's record once the receiver has recorded its end, or unknown if it cannot."""
        if not self.owned:
            return self.dispatches.record(self.dispatch_id)
        # By default the receiver has until the contract deadline, or the later end it announced for a
        # contained worker's stop, and ACCEPT_SECONDS more.
        ends_by = max(self.contract['deadline'], self.ends_by or 0)
        deadline = time.monotonic() + (timeout if timeout is not None else
                                       max(1.0, ends_by - time.time() + ACCEPT_SECONDS))
        if self.result == 'accepted' and (self.record or {}).get('state') == 'running':
            while True:
                message = self._message(deadline)
                if message is None or message.get('event') in ('exited', 'unknown'):
                    break
        self._end_receiver()
        record = self.dispatches.record(self.dispatch_id)
        if record and record['state'] == 'running':
            # The receiver that owned the worker has ended without recording its end.
            record = self.dispatches.unknown(self.dispatch_id, record['contract_digest'], 'outcome_unknown',
                                             now=self.clock(), expected_state='running')
        self.record = record
        return record


def invoke(config_path, contract, dispatches, *, accept_seconds=ACCEPT_SECONDS, environment=None, clock=None):
    """Hand the prepared contract to the trusted receiver process named by the installed config."""
    try:
        child = subprocess.Popen([sys.executable, '-B', RECEIVER, str(config_path)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment)
    except OSError:
        # No receiver ran, so nothing was launched: a conclusive refusal, never a held unit.
        launch = Launch(None, contract, dispatches, clock or time.time)
        launch._settle(lost=True)
        return launch
    launch = Launch(child, contract, dispatches, clock or time.time)
    try:
        # The receiver's stdin stays open as its control channel: Launch.stop writes a stop request on it.
        child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
        child.stdin.flush()
    except OSError:
        pass
    return launch.start(accept_seconds)


# The receiver process.

class Receiver:
    """The trusted launch receiver over the installed configuration: {store, journal_key, principal,
    domain, repository, authority_generation, workspace, profile, adapters: {name: {argv, environment?,
    identity?}}}. `profile` is this host's worker profile (control_containment); `control` is the
    runner's channel after its request line (fd, what was already read of it), where it asks for a stop."""

    def __init__(self, config, emit, control=None):
        self.config, self.emit = config, emit
        self.profile = config.get('profile')
        self.qualification = None
        self.supervision = None
        self.control = control
        self.conn = S.open_store(config['store'])
        key = config['journal_key']
        signer = _organ('control_signer')
        self.dispatches = D.Dispatches(S, self.conn, domain=config['domain'], repository=config['repository'],
                                       principal=config['principal'], signer=config['principal'],
                                       sign=lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE),
                                       generation=config.get('authority_generation', 1))
        self.renewals = HB.Renewals(self.dispatches, D)
        self.sign = lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE)
        self.host = config.get('host') or socket.gethostname()
        self.login = None
        self.metering = None
        self.binding = None

    def close(self):
        self.conn.close()

    def _recheck(self, contract):
        """The preparation's station decision, rechecked at this accepting boundary as its ticket."""
        EL = _organ('control_eligibility')
        reader = S.open_store(self.config['store'], mode='r')
        try:
            # The workspace whose architecture the decision judges (VELDO-0053) is the receiver's configured
            # repository checkout; without one the Gate is store-only and refuses.
            gate = EL.Gate(S, reader, domain_uuid=self.config['domain'], repository_uuid=self.config['repository'],
                           authority_generation=self.config.get('authority_generation', 1),
                           workspace=self.config.get('workspace'))
            context = dict(contract['input']['context'])
            if contract['claim']:
                context['generation'] = contract['claim']['generation']
            decision = gate.decide(contract['station'], contract['unit'], context=context,
                                   ticket=contract['input']['decision'])
        finally:
            reader.close()
        return None if decision['eligible'] else '; '.join(decision['refusals'])

    def _qualify(self, adapter):
        """This host's worker profile, qualified before acceptance for a local adapter: an absent, invalid
        or unenforceable profile is refused by name and nothing is spawned. Another host's worker
        (identity reported) is contained by that host's profile (VELDO-0124)."""
        if adapter.get('identity', 'local') == 'reported':
            return None
        self.qualification = C.qualify(self.profile)
        return self.qualification['refusal']

    def launch(self, contract):
        dispatch_id = contract['dispatch_id']
        record = self.dispatches.record(dispatch_id)
        if record is None or record['state'] != 'prepared':
            # Not this receiver's to launch: another attempt of it was accepted, refused, ended or is
            # unknown. Nothing is recorded and nothing is spawned.
            self.emit({'event': 'refused', 'refusal': 'not_prepared:%s' % (record or {}).get('state', 'missing')})
            return
        contract_digest = D.digest(contract)
        adapter = self.config.get('adapters', {}).get(contract['capability']['adapter'])
        refusal = None
        if contract_digest != record['contract_digest']:
            refusal = 'binding_mismatch:contract_digest'
        elif not isinstance(adapter, dict) or not adapter.get('argv'):
            refusal = 'unregistered_adapter:' + str(contract['capability']['adapter'])
        else:
            refusal = self._recheck(contract)
        if not refusal:
            refusal = self._qualify(adapter)
        if not refusal:
            refusal = self._login(contract, adapter)
        if not refusal:
            refusal = self._bind(adapter)
        if refusal:
            self.dispatches.refuse(dispatch_id, record['contract_digest'], refusal, now=time.time(),
                                   expected_state='prepared')
            self.emit({'event': 'refused', 'refusal': refusal})
            return
        me = dict(process_identity(os.getpid()), principal=self.config['principal'])
        try:
            self.dispatches.accept(dispatch_id, contract_digest, me, now=time.time())
        except D.Refused as error:
            current = (self.dispatches.record(dispatch_id) or {}).get('state')
            if current != 'prepared':
                # Another invocation moved it on: not this receiver's to refuse or launch.
                self.emit({'event': 'refused', 'refusal': 'not_prepared:%s' % current})
                return
            self.dispatches.refuse(dispatch_id, record['contract_digest'], error.code, now=time.time(),
                                   expected_state='prepared')
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        acceptance = self.dispatches.receipt(dispatch_id, 'accept')
        self.emit({'event': 'accepted', 'acceptance': acceptance})
        try:
            worker = self._invoke(contract, acceptance, adapter)
        except Unfunded as error:
            # Checked and refused before anything was spawned: nothing ran, nothing was reserved.
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        except C.Refused as error:
            if error.settled:
                self._not_executed()
            self._uncontained(dispatch_id, contract_digest, error)
            return
        except OSError as error:
            self._not_executed()
            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)
            self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(), expected_state='accepted')
            self.emit({'event': 'refused', 'refusal': refusal})
            return
        carry = b''
        remote = adapter.get('identity', 'local') == 'reported'
        try:
            if remote:
                process, refusal, carry = self._reported(worker, contract)
                if refusal:
                    worker.wait()
                    self._not_executed()
                    self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time(),
                                           expected_state='accepted')
                    self.emit({'event': 'refused', 'refusal': refusal})
                    return
            else:
                process = process_identity(worker.pid)
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            self._stop(worker)
            self.dispatches.unknown(dispatch_id, contract_digest, 'process_identity_unreadable', now=time.time(),
                                    expected_state='accepted')
            self.emit({'event': 'unknown'})
            return
        try:
            self.dispatches.run(dispatch_id, contract_digest, process, now=time.time())
        except BaseException:
            # The worker ran with no running record: stop it; the runner records the outcome unknown.
            self._stop(worker)
            raise
        group = getattr(worker, 'group', None)
        watch = getattr(worker, 'heartbeat', None)
        # When this receiver will have recorded the end at the latest: a stop begun at the deadline, its
        # graces and the settling of the group.
        ends_by = contract['deadline'] + (sum(self._graces()) + C.SETTLE_SECONDS if group else 0)
        beat = {'interval_seconds': watch.interval, 'window_seconds': watch.window} if watch else None
        graces = dict(zip(('stop_grace_seconds', 'kill_grace_seconds'), self._graces())) if group else None
        self.emit({'event': 'running', 'process': process, 'ends_by': ends_by, 'heartbeat': beat, 'graces': graces,
                   'group': group.report() if group else None})
        termination = self._reap(worker, contract, carry, process=process, contract_digest=contract_digest)
        if self.metering is not None:
            # The invocation settles before its end is recorded, so the slot's accounting is complete.
            self.metering.settle(termination, (self.supervision or {}).get('cause'))
            if self.metering.report is not None:
                self.emit({'event': 'artifact', 'artifact': self.metering.report})
        if remote and termination['deadline_stop']:
            # Stopping the local transport at the deadline does not show the remote engine ended: its
            # outcome is unknown, and the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running')
            self.emit({'event': 'unknown'})
            return
        supervision = self.supervision
        if remote and supervision['cause'] in ('requested', 'usage_cap'):
            # Nor does stopping it on request or at its usage cap: the unit and station stay held.
            self.dispatches.unknown(dispatch_id, contract_digest, 'remote_stop_unconfirmed', now=time.time(),
                                    expected_state='running')
            self.emit({'event': 'unknown', 'supervision': supervision})
            return
        if supervision['empty'] is False:
            # Something of the worker's group is still running: never recorded as ended.
            self.dispatches.unknown(dispatch_id, contract_digest, 'containment_not_empty', now=time.time(),
                                    expected_state='running')
            self.emit({'event': 'unknown', 'supervision': supervision})
            return
        report = self.metering.report if self.metering is not None else None
        artifact = {k: report[k] for k in ('verdict', 'complete', 'digest')} if report is not None else None
        self.dispatches.exit(dispatch_id, contract_digest, process, termination, now=time.time(), artifact=artifact)
        self.emit({'event': 'exited', 'termination': termination, 'supervision': supervision})

    def _login(self, contract, adapter):
        """VELDO-0062: the subscription login of an engine adapter, read before acceptance from the
        account the accepted contract records. None when it may run; else the named refusal."""
        self.login = None
        engine = adapter.get('engine')
        if engine is None:
            return None
        module = ENGINES.get(engine)
        if module is None:
            return 'unregistered_adapter:engine:' + str(engine)
        missing = [name for name in ENGINE_PROTOCOL if not hasattr(module, name)]
        if missing:
            return 'unregistered_adapter:engine_protocol:%s:%s' % (engine, missing[0])
        # What the adapter configures reaches the engine as configured; a login in it is refused by name.
        configured = ACC.refused(adapter.get('environment') or {}, CREDENTIALS)
        if configured:
            return 'invalid_input:adapter_environment:' + configured[0]
        account = contract['reservation']['account']
        record = ACC.read(self.conn, account)
        if record is not None and record.get('provider') != module.PROVIDER:
            return 'invalid_input:account_provider:%s:%s' % (record.get('provider'), module.PROVIDER)
        try:
            ACC.profile(record, self.host)
        except ACC.Refused as error:
            return error.code
        # The engine's local time zone, for a CLI that states a reset in local time (Codex).
        zone = (adapter.get('environment') or {}).get('TZ', os.environ.get('TZ'))
        self.login = {'engine': module, 'account': account, 'record': record, 'zone': zone}
        return None

    def _bind(self, adapter):
        """THE ENGINE PROTOCOL's one binding path (VELDO-0060, VELDO-0061): the engine's pinned executable,
        its argv and its settings, bound before acceptance. None when it may run; else the named refusal,
        with nothing accepted, reserved or spawned."""
        self.binding = None
        module = (self.login or {}).get('engine')
        if module is None:
            return None
        try:
            bound = module.bind(adapter, self.config.get('state_root'))
            argv = module.command(bound, adapter)
            settings = module.environment(bound)
        except module.Refused as error:
            return error.code
        refusal = pinned_argv_problem(argv, bound, adapter.get('identity', 'local') == 'reported')
        if refusal:
            return refusal
        configured = adapter.get('environment') or {}
        for name in sorted(settings):
            if name in configured and configured[name] != settings[name]:
                return 'invalid_input:adapter_environment:' + name
        self.binding = dict(bound, argv=argv, environment=settings)
        return None

    def _invoke(self, contract, acceptance, adapter):
        """Spawn the worker. For a subscription engine the invocation is first checked and reserved
        against every applicable cap and the account's reported windows (VELDO-0036's InvocationGuard,
        whose launch is this spawn), so a refusal launches nothing."""
        dispatch_id = contract['dispatch_id']
        if self.login is None:
            return self._spawn(dispatch_id, acceptance, adapter)
        reservations = D.RES.Reservations(S, self.conn, domain=self.config['domain'],
                                          repository=self.config['repository'], principal=self.config['principal'],
                                          authorize=D.RES.service_authority, signer=self.config['principal'],
                                          sign=self.sign, generation=self.config.get('authority_generation', 1))
        accounts = ACC.Accounts(S, self.conn, principal=self.config['principal'], signer=self.config['principal'],
                                sign=self.sign, generation=self.config.get('authority_generation', 1))
        spawned = []

        def launch(invocation, configuration):
            # Reserved: from here a spawn that fails is attested not executed, one that starts is metered.
            self.metering = metering
            spawned.append(self._spawn(dispatch_id, acceptance, adapter))
            metering.started()
        metering = Metering(self, contract, reservations, accounts, launch)
        try:
            metering.guard.invoke('call/' + dispatch_id, dispatch_id, metering.invocation, metering.boundary,
                                  max(0.001, contract['deadline'] - time.time()),
                                  contract['capability']['configuration'], now=time.time())
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            raise Unfunded('missing_authority:allowance:' + error.code)
        if not spawned:
            raise Unfunded('stale_subject:invocation_replayed')
        return spawned[0]

    def _not_executed(self):
        """A reserved invocation whose engine never started: the receiver attests it (VELDO-0036)."""
        metering, self.metering = self.metering, None
        if metering is not None:
            metering.settle(None, None)

    def _uncontained(self, dispatch_id, contract_digest, error):
        """A worker that could not be contained as declared was never released to its engine: refused
        by name, or unknown when its group could not be emptied."""
        if error.settled:
            self.dispatches.refuse(dispatch_id, contract_digest, error.code, now=time.time(), expected_state='accepted')
            self.emit({'event': 'refused', 'refusal': error.code, 'group': error.group})
        else:
            self.dispatches.unknown(dispatch_id, contract_digest, 'containment_not_empty', now=time.time(),
                                    expected_state='accepted')
            self.emit({'event': 'unknown', 'group': error.group})

    def _spawn(self, dispatch_id, acceptance, adapter):
        """THE ONE SPAWN: the adapter's configured argv in its own session, its own pipes (it never
        shares this receiver's reply channel) and an environment naming its dispatch and the journal
        digest of the acceptance it launches under. That digest exists only once the acceptance has
        committed, so a worker's birth environment is evidence the acceptance, and the contract it
        accepted, were recorded before the worker existed. A local adapter's worker is started inside
        its dispatch's own containment group (VELDO-0040); a transport to another host is started as
        configured, and that host's profile contains the engine there."""
        environment = dict(os.environ)
        if self.login is not None:
            # VELDO-0062: the recorded account's own profile, no other profile and no other login in what
            # the engine inherits; what the adapter configures, as configured.
            environment = ACC.login_environment(environment, self.login['record'], self.host, STRIPPED,
                                                adapter.get('environment') or {}, CREDENTIALS)
            environment['VELDO_ACCOUNT'] = self.login['account']
        else:
            environment.update(adapter.get('environment') or {})
        argv = list(adapter['argv'])
        if self.binding is not None:
            # THE ENGINE PROTOCOL: the bound engine argv and the engine's own settings, last.
            argv = list(self.binding['argv'])
            environment.update(self.binding['environment'])
            # What the trusted program that execs the engine re-hashes immediately before the exec.
            environment[ENGINE_PATH], environment[ENGINE_DIGEST] = self.binding['path'], self.binding['sha256']
        environment['VELDO_DISPATCH_ID'] = dispatch_id
        environment['VELDO_DISPATCH_ACCEPTANCE'] = acceptance or ''
        if adapter.get('identity', 'local') != 'reported':
            return self._contained(dispatch_id, argv, environment)
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=environment, start_new_session=True, close_fds=True)

    def _contained(self, dispatch_id, argv, environment):
        """Start the trusted wrapper inside the dispatch's own containment group with every declared cap
        installed, check it is in that group with those controls, and only then release it to become the
        engine (the same pid). The group is created under the profile's concurrency admission. A worker
        that is not contained as declared is discarded before any engine code runs and refused by name."""
        if self.qualification is None:
            self.qualification = C.qualify(self.profile)
        if not self.qualification['qualified']:
            raise C.Refused(self.qualification['refusal'])
        group = C.Group(self.profile, self.qualification, dispatch_id, environment)
        interval, window = self._heartbeat()
        # The heartbeat channel (VELDO-0041): the wrapper's heartbeat writes it, this receiver reads it.
        channel, beat = os.pipe()
        wrapper = [sys.executable, '-B', RECEIVER, 'exec', '--contained', json.dumps(group.held()),
                   '--heartbeat', str(beat), repr(float(interval))] + argv
        try:
            with group.admission():
                try:
                    worker = subprocess.Popen(group.command(wrapper), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL, env=group.environment, start_new_session=True,
                                              close_fds=True, pass_fds=(beat,))
                finally:
                    os.close(beat)
                worker.group = group
                try:
                    reported, refusal, _ = self._reported(worker, {'deadline': time.time() + ACCEPT_SECONDS})
                    problems = [refusal] if refusal else group.attach(worker.pid)
                    if not problems and reported.get('pid') != worker.pid:
                        problems = ['spawn_failed:containment:identity']
                    if not problems:
                        HB.make_group(group.cgroup)
                except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
                    problems = ['spawn_failed:containment:unavailable']
                if problems:
                    settled = group.discard(worker)
                    if problems[0] == 'spawn_failed:ENOENT' and settled:
                        raise FileNotFoundError(errno.ENOENT, 'no engine: ' + str(argv[0]))
                    raise C.Refused(problems[0], settled=settled, group=group.report())
            try:
                worker.stdin.write(b'go\n')
                worker.stdin.flush()
            except OSError:
                settled = group.discard(worker)
                raise C.Refused('spawn_failed:containment:release', settled=settled, group=group.report())
        except BaseException:
            os.close(channel)
            raise
        worker.heartbeat = HB.Watch(channel, interval, window, time.monotonic())
        return worker

    @staticmethod
    def _reported(worker, contract):
        """(process, refusal, carry) from an adapter launched through the trusted wrapper (a remote
        host reached over the configured transport): the wrapper's FIRST line, written before it
        became the engine, names the OS identity of the process the engine now is, or the named
        refusal of an engine that could not be run. Anything after that line is the worker's output
        (`carry`). A missing, late or malformed line is unreadable, never a guess."""
        pending, end = b'', min(contract['deadline'], time.time() + ACCEPT_SECONDS)
        while b'\n' not in pending:
            remaining = end - time.time()
            if remaining <= 0 or not select.select([worker.stdout], [], [], remaining)[0]:
                raise ValueError('no identity line')
            chunk = os.read(worker.stdout.fileno(), 65536)
            if not chunk:
                raise ValueError('no identity line')
            pending += chunk
        line, _, carry = pending.partition(b'\n')
        message = json.loads(line)
        if not isinstance(message, dict) or message.get('schema') != WRAPPER_SCHEMA:
            raise ValueError('not an identity line')
        if D._text(message.get('refused')) and message['refused'].startswith('spawn_failed:'):
            return None, message['refused'], carry
        if D._identity_problems(message.get('process')):
            raise ValueError('malformed identity')
        return message['process'], None, carry

    @staticmethod
    def _stop(worker):
        """Kill a worker at once: its whole containment group when it has one, and its session."""
        group = getattr(worker, 'group', None)
        if group is not None:
            group.kill()
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except OSError:
            pass
        worker.wait()

    def _settings(self, *names):
        settings = (self.qualification or {}).get('settings') or {}
        return tuple((settings.get(name) or {}).get('value', C.SETTINGS[name]['default']) for name in names)

    def _graces(self):
        return self._settings('stop_grace_seconds', 'kill_grace_seconds')

    def _heartbeat(self):
        """The profile's heartbeat interval and missed-heartbeat window (VELDO-0041)."""
        return self._settings('heartbeat_seconds', 'heartbeat_window_seconds')

    def _renew(self, watch, contract, contract_digest, process, beat):
        """Renew the claim the contract binds on one heartbeat; a refusal is recorded by name."""
        renewed, refusal = self.renewals.renew(contract, contract_digest, process, beat['seq'], time.time())
        beat['renewed'] = renewed
        if renewed:
            watch.renewals['renewed'] += 1
        elif refusal:
            watch.renewals['refused'] = (watch.renewals['refused'] + [{'seq': beat['seq'], 'refusal': refusal}])[-HB.KEEP:]

    def _stop_asked(self, poller=None):
        """Whether the runner asked for a stop in what it has written on the control channel; with a
        poller, what is readable now is read first (end of the channel unregisters it)."""
        if self.control is None:
            return False
        fd, pending = self.control
        if poller is not None:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b''
            if not chunk:
                poller.unregister(fd)
            pending += chunk
        asked = False
        while b'\n' in pending:
            line, _, rest = bytes(pending).partition(b'\n')
            pending[:] = rest
            with contextlib.suppress(ValueError):
                message = json.loads(line)
                asked = asked or (isinstance(message, dict) and bool(message.get('stop')))
        return asked

    def _reap(self, worker, contract, carry=b'', process=None, contract_digest=None):
        """Feed the worker its packet, hash what it prints, and reap it and its group by the contract
        deadline. The loop sleeps in poll until an OS notification or the next timer: the worker's
        output, its pidfd (its exit), its group's populated event, a heartbeat, a stop request on the
        control channel, the deadline, the missed-heartbeat deadline or the next escalation step; nothing
        is polled for liveness. Closing its output does not end a worker: it is still held to the
        contract deadline. Its exit ends the dispatch: whatever is left in its group is stopped (the
        wrapper's own heartbeat, which ends on the worker's exit, is given SETTLE_SECONDS first), and the
        reap ends once the group is empty (or, SETTLE_SECONDS after the kill, declared not empty in the
        supervision). Every stop it begins escalates on the monotonic clock."""
        packet = {'dispatch_id': contract['dispatch_id'], 'unit': contract['unit'], 'station': contract['station'],
                  'source': contract['source'], 'payload': contract['input']['payload'],
                  'configuration': contract['capability']['configuration']}

        def feed():
            try:
                worker.stdin.write(json.dumps(packet).encode())
                worker.stdin.close()
            except OSError:
                pass
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        group, watch = getattr(worker, 'group', None), getattr(worker, 'heartbeat', None)
        stop = C.Stop(group, worker.pid, *self._graces()) if group is not None else None
        hasher, size, stopped, cause, code, empty = hashlib.sha256(carry), len(carry), False, None, None, None
        settle, emptied = None, (None, None)
        output, pidfd = worker.stdout.fileno(), os.pidfd_open(worker.pid)
        poller = select.poll()
        poller.register(output, select.POLLIN)
        poller.register(pidfd, select.POLLIN)
        if group is not None:
            poller.register(group.events, select.POLLPRI | select.POLLERR)
        if watch is not None:
            poller.register(watch.fd, select.POLLIN)
        if self.control is not None:
            poller.register(self.control[0], select.POLLIN)

        def begin(reason):
            nonlocal cause, stopped, code
            if cause is not None or code is not None:
                return
            cause, stopped = reason, reason == 'deadline'
            if stop is not None:
                stop.begin(reason, time.monotonic(), True)
            else:
                self._stop(worker)
                code = worker.returncode
        metering = self.metering
        if metering is not None and metering.feed(carry):
            begin('usage_cap')
        try:
            if self._stop_asked():
                begin('requested')
            while True:
                if code is not None and (group is None or not group.populated()):
                    empty, emptied = True, (time.time(), time.monotonic())
                    break
                if stop is not None and stop.stage == 'abandoned':
                    empty = False
                    break
                live = cause is None and code is None
                waits = [contract['deadline'] - time.time()] if live else []
                waits += [due - time.monotonic() for due in (stop.due if stop is not None else math.inf,
                                                             watch.due() if watch is not None and live else math.inf,
                                                             settle if settle is not None else math.inf)
                          if due != math.inf]
                timeout = max(0, math.ceil(min(waits) * 1000)) if waits else None
                for fd, _ in poller.poll(timeout):
                    if fd == output:
                        chunk = os.read(output, 65536)
                        if not chunk:
                            poller.unregister(output)
                        size += len(chunk)
                        hasher.update(chunk)
                        if metering is not None and metering.feed(chunk):
                            # VELDO-0062: a cap the CLI's own report reached stops the worker.
                            begin('usage_cap')
                    elif fd == pidfd:
                        poller.unregister(pidfd)
                        code = worker.wait()
                        if stop is not None and group.populated():
                            if group.members() or watch is None:
                                stop.adapter_exited(time.monotonic())
                            else:
                                # Only the wrapper's heartbeat is left, and it ends on the worker's exit.
                                settle = time.monotonic() + HB.SETTLE_SECONDS
                    elif group is not None and fd == group.events:
                        group.populated()
                    elif watch is not None and fd == watch.fd:
                        for beat in watch.read(time.monotonic()):
                            self._renew(watch, contract, contract_digest, process, beat)
                        if not watch.open:
                            poller.unregister(watch.fd)
                    elif self.control is not None and fd == self.control[0] and self._stop_asked(poller):
                        begin('requested')
                now = time.monotonic()
                if cause is None and code is None and time.time() >= contract['deadline']:
                    begin('deadline')
                elif cause is None and code is None and watch is not None and watch.expired(now):
                    # No heartbeat for the window with the worker still running: its liveness is
                    # uncertain, and it is stopped (the supervision records when and why).
                    watch.lapse(now)
                    begin('heartbeat_missing')
                elif stop is not None:
                    if settle is not None and now >= settle:
                        settle = None
                        stop.adapter_exited(now)
                    stop.advance(now)
        finally:
            os.close(pidfd)
            if watch is not None:
                os.close(watch.fd)
        # What is left in the pipe, without waiting on a writer that is no longer in the group.
        os.set_blocking(output, False)
        with contextlib.suppress(OSError):
            for chunk in iter(lambda: os.read(output, 65536), b''):
                size += len(chunk)
                hasher.update(chunk)
                if metering is not None:
                    metering.feed(chunk)
        code = worker.poll() if code is None else code
        result = group.conclude() if group is not None and empty else None
        if cause is None and result in ('timeout', 'oom-kill'):
            # systemd stopped the group at a cap: the runtime cap is a deadline, the memory cap is not.
            cause = {'timeout': 'runtime_cap', 'oom-kill': 'memory_cap'}[result]
            stopped = cause == 'runtime_cap'
        self.supervision = {'cause': cause or (stop.cause if stop is not None else None),
                            'steps': stop.steps if stop is not None else [], 'empty': empty,
                            'graces': ({'stop_grace_seconds': stop.grace['cooperative'],
                                        'kill_grace_seconds': stop.grace['terminate']} if stop is not None else None),
                            'empty_at': emptied[0], 'empty_monotonic': emptied[1], 'result': result,
                            'group': group.report() if group is not None else None,
                            'heartbeat': watch.summary() if watch is not None else None}
        if group is not None and empty:
            group.close()
        feeder.join(timeout=5)
        worker.stdout.close()
        return {'returncode': code if code is not None and code >= 0 else None,
                'signal': -code if code is not None and code < 0 else None,
                'output_digest': 'sha256:' + hasher.hexdigest(), 'output_bytes': size, 'deadline_stop': stopped}


class Unfunded(Exception):
    """An invocation checked and refused before launch (VELDO-0062); `code` names why."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class Metering:
    """One subscription invocation's usage, from its reservation to its settlement (VELDO-0062).

    The account is the one the accepted contract records. Each line the CLI prints that reports usage
    or a rate-limit window is kept, raw, in the invocation's receipt file (mode 0600 in a 0700
    directory, beside the store unless the config names `receipts`), after a header naming the
    dispatch, invocation, account, project, unit, provider and boundary; the ledger carries each
    line's digest. Usage goes to VELDO-0036 in sequence, and a report that reaches a cap, or that
    cannot be recorded, stops the worker. A window goes to the account record."""

    def __init__(self, receiver, contract, reservations, accounts, launch):
        self.receiver, self.contract = receiver, contract
        self.reservations, self.accounts = reservations, accounts
        self.dispatch_id = contract['dispatch_id']
        self.account = contract['reservation']['account']
        self.engine = receiver.login['engine']
        # A follow-on resumes a CLI session whose earlier turns the CLI may carry into this invocation's
        # report: the meter is given the session's running total the ledger settled last (None when no
        # invocation settled it, or settled it without one), so only the difference is charged, and only
        # when the CLI reports that same session (the meter decides; another session is charged whole).
        payload = (contract.get('input') or {}).get('payload')
        self.resumes = str(payload['resume']) if isinstance(payload, dict) and payload.get('resume') else None
        settled = reservations.session(self.engine.PROVIDER, self.resumes) if self.resumes else None
        self.meter = self.engine.Meter(zone=receiver.login.get('zone'), resumes=self.resumes,
                                       prior=(settled or {}).get('tokens'))
        self.invocation = 'invocation/' + self.dispatch_id
        self.boundary = RTM.boundary(contract)
        self.guard = RTM.InvocationGuard(reservations, self.engine.PROVIDER, launch, self._stop)
        self.sequence = 0
        self.stop = False
        self.errors = []
        self.receipts = []
        self.start = None
        self.settled = False
        self.file = None
        # THE ENGINE PROTOCOL: the engine's terminal output, decoded from the same stream, and its report.
        self.terminal = self.engine.Terminal()
        self.report = None

    def _stop(self, dispatch_id):
        self.stop = True

    def started(self):
        """The engine exists: open its receipt file and start its clock."""
        self.start = time.monotonic()
        directory = Path(self.receiver.config.get('receipts') or Path(self.receiver.config['store']).parent / 'receipts')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.jsonl')
        self.file = os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')
        header = {'schema': RECEIPTS_SCHEMA, 'dispatch_id': self.dispatch_id, 'invocation': self.invocation,
                  'account': self.account, 'project': self.contract['reservation']['project'],
                  'unit': self.contract['unit'], 'provider': self.engine.PROVIDER, 'boundary': self.boundary}
        self.file.write((json.dumps(header, sort_keys=True) + '\n').encode())
        self.file.flush()

    def feed(self, chunk):
        """Whether the worker must stop, after the observations in `chunk`."""
        self.terminal.feed(chunk)
        for observation in self.meter.feed(chunk):
            self._observe(observation)
        return self.stop

    def _keep(self, line):
        if self.file is not None:
            self.file.write(line + b'\n')
            self.file.flush()

    def _observe(self, observation):
        self._keep(observation['line'])
        self.receipts.append(observation['receipt'])
        now = time.time()
        try:
            if observation['kind'] == 'window':
                self.accounts.observe('window/%s/%s/%s' % (self.dispatch_id, observation['receipt'][7:23],
                                                           observation['window_id']),
                                      self.account, observation['window_id'], status=observation['status'],
                                      reset_at=observation['reset_at'], utilization=observation['utilization'],
                                      source_dispatch=self.dispatch_id, now=now)
                return
            self.sequence += 1
            result = self.guard.observe('usage/%s/%d' % (self.dispatch_id, self.sequence), self.invocation,
                                        self.sequence, observation['usage'], now=now,
                                        receipts=[observation['receipt']])
            self.stop = self.stop or bool(result.get('stop_required'))
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            # A report that cannot be recorded fails closed: the worker stops.
            self.errors.append(error.code)
            self.stop = True

    def _artifact(self, termination, cause):
        """The invocation's artifact (THE ENGINE PROTOCOL): the engine's decoded document, bound to its
        dispatch, invocation, account and pinned executable, kept in its private file; its report {path,
        digest, verdict, complete}. A document that cannot be kept is reported with no path: never complete."""
        self.terminal.close()
        executable = self.receiver.binding or {}
        document = dict(self.terminal.document(termination, cause), dispatch_id=self.dispatch_id,
                        invocation=self.invocation, account=self.account,
                        executable={k: executable.get(k) for k in ('engine', 'version', 'path', 'sha256')})
        data = (json.dumps(document, sort_keys=True) + '\n').encode()
        directory = Path(self.receiver.config.get('artifacts') or Path(self.receiver.config['store']).parent / 'artifacts')
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            path = directory / (hashlib.sha256(self.invocation.encode()).hexdigest() + '.json')
            with os.fdopen(os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
                handle.write(data)
        except OSError as error:
            self.errors.append('artifact:' + type(error).__name__)
            path = None
        verdict = document['verdict'] if path is not None else 'artifact_unkept'
        return {'path': str(path) if path else None, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                'verdict': verdict, 'complete': verdict == 'complete' and document['complete'] is True}

    def settle(self, termination, cause):
        """The one final report. `termination` None: the engine never started (not executed)."""
        if self.settled:
            return
        self.settled = True
        now = time.time()
        if termination is None:
            usage, outcome = {}, 'not_executed'
        else:
            for observation in self.meter.close():
                self._observe(observation)
            usage = dict(self.meter.final(), invocations=1,
                         wall_seconds=round(time.monotonic() - (self.start or time.monotonic()), 6))
            if termination.get('deadline_stop'):
                outcome = 'timeout'
            elif cause in ('requested', 'usage_cap', 'heartbeat_missing'):
                outcome = 'cancelled'
            else:
                outcome = 'completed' if termination.get('returncode') == 0 else 'failed'
            self.report = self._artifact(termination, cause)
            if outcome == 'completed' and not self.report['complete']:
                outcome = 'failed'  # a zero exit is a completion only with its terminal record (THE ENGINE PROTOCOL)
        self.sequence += 1
        session = self.meter.session() if termination is not None else None
        try:
            self.guard.observe('usage/%s/%d' % (self.dispatch_id, self.sequence), self.invocation, self.sequence,
                               usage, now=now, final=True, outcome=outcome, receipts=self.receipts, session=session)
        except (D.RES.Refused, ACC.Refused, S.StoreRefused) as error:
            self.errors.append(error.code)
        finally:
            if self.file is not None:
                self.file.close()


def wrap(argv):
    """THE TRUSTED WRAPPER (`control_launch.py exec [--contained <limits>] [--heartbeat <fd> <seconds>]
    <argv>`). Through a transport it is what runs on the far host (the Mac over SSH, for one); on this
    host it is what the dispatch's containment group is created around (VELDO-0040). It writes the OS
    identity of this very process on its first output line and then becomes the engine by exec, so the
    pid and start time it named are the engine's. Contained, it first applies the profile's per-process
    limits, which every descendant inherits, and after its identity line waits for the receiver's
    release: the receiver checks the group and its controls in between, so no engine code runs
    uncontained. Released, it starts its heartbeat on the channel the receiver passed (VELDO-0041,
    control_heartbeat.start) and closes the channel before the exec. An engine that cannot be found is
    refused by name before anything runs. It opens no store: the receiver records what it reports."""
    held, beat = None, None
    if argv[:1] == ['--contained'] and len(argv) > 2:
        held, argv = json.loads(argv[1]), argv[2:]
    if argv[:1] == ['--heartbeat'] and len(argv) > 3:
        # VELDO-0041: the channel the receiver passed and the profile's heartbeat interval.
        beat, argv = (int(argv[1]), float(argv[2])), argv[3:]
    path = shutil.which(argv[0]) if argv else None
    if not path:
        sys.stdout.write(json.dumps({'schema': WRAPPER_SCHEMA, 'refused': 'spawn_failed:ENOENT'}) + '\n')
        sys.stdout.flush()
        os._exit(127)
    if held is not None:
        C.hold(held)
    sys.stdout.write(json.dumps({'schema': WRAPPER_SCHEMA, 'process': process_identity(os.getpid())}) + '\n')
    sys.stdout.flush()
    if held is not None and not C.released(0):
        os._exit(125)
    if beat is not None:
        # Released: the heartbeat starts now, in a process of its own, and this process closes the
        # channel before it becomes the engine, so liveness never waits on anything the engine does.
        HB.start(*beat)
    # The engine starts with the default dispositions of the signals Python ignores, as subprocess does.
    for number in (signal.SIGPIPE, signal.SIGXFSZ):
        signal.signal(number, signal.SIG_DFL)
    environment = dict(os.environ)
    # THE ENGINE PROTOCOL: the names of the exec-time re-hash reach the clone entrance only, never an engine.
    pinned, expected = environment.pop(ENGINE_PATH, None), environment.pop(ENGINE_DIGEST, None)
    if pinned is not None and entrance(argv):
        environment[ENGINE_PATH], environment[ENGINE_DIGEST] = pinned, expected
    elif pinned is not None and os.path.realpath(path) == os.path.realpath(pinned):
        # This wrapper execs the pinned engine itself (however its path is spelled), so it re-hashes the
        # file now, immediately before the exec; a changed one never runs.
        try:
            unchanged = file_digest(path) == expected
        except OSError:
            unchanged = False
        if not unchanged:
            sys.stderr.write('wrapper refused: binding_mismatch:engine_digest\n')
            sys.stderr.flush()
            os._exit(WRAPPER_REFUSED)
    try:
        os.execve(path, argv, environment)
    except OSError:
        os._exit(126)


def _request(fd, seconds):
    """The runner's request, the first line on the receiver's stdin, and what it has written after it
    (the start of the control channel), read from the descriptor itself so nothing is buffered away."""
    pending, end = b'', time.monotonic() + seconds
    while b'\n' not in pending and len(pending) < 1 << 22:
        remaining = end - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise ValueError('no request')
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        pending += chunk
    line, _, rest = pending.partition(b'\n')
    return json.loads(line), bytearray(rest)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'exec':
        wrap(sys.argv[2:])
        return

    def emit(message):
        sys.stdout.write(json.dumps(message) + '\n')
        sys.stdout.flush()
    receiver = None
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        request, pending = _request(0, 10)
        receiver = Receiver(config, emit, control=(0, pending))
        receiver.launch(request['contract'])
    except (OSError, ValueError, TypeError, KeyError, D.Refused, S.StoreRefused, C.Refused) as error:
        # Nothing conclusive is claimed: the runner reads the record and settles it.
        emit({'event': 'failed', 'error': type(error).__name__})
    finally:
        if receiver is not None:
            receiver.close()


if __name__ == '__main__':
    main()
