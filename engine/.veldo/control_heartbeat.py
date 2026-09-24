#!/usr/bin/env python3
"""The trusted wrapper's heartbeat and the receiver's watch of it: liveness that does not depend on a
blocking model call, the claim renewed on each heartbeat, and the missed-heartbeat deadline
(PLAN-0019 W26, VELDO-0041, R44).

THE HEARTBEAT (`start`, in the trusted wrapper). A contained worker's wrapper (control_launch.py
`exec --contained`) is released by the receiver and then becomes the engine by exec, so the engine
keeps the pid the receiver recorded. Just before that exec the wrapper starts its heartbeat: a process
of its own, forked twice so it is no child the engine could wait for, in a session and process group
of its own (taken between the two forks, before the engine exists), so an engine that signals its own
process group leaves it beating. It writes one line
(veldo.heartbeat/v1: a sequence number, its monotonic time and its pid) on the heartbeat channel at
once and then every `heartbeat_seconds` of the worker profile, on a fixed monotonic schedule. It reads
nothing the engine writes and waits on nothing the engine does, so a model call that blocks for an
hour leaves it beating. It ends when the engine's process ends (a pidfd the wrapper opened on itself
before the exec becomes readable), when its channel is closed, or with the group. The channel is a
pipe the receiver made and passed through systemd-run by descriptor number; the wrapper closes its own
copy before the exec, so neither the engine nor its descendants hold it.

THE HEARTBEAT'S GROUP. The heartbeat runs in a child group of the dispatch's containment group
(`<scope cgroup>/veldo-wrapper`, created by the receiver before it releases the wrapper). It is
charged to the scope's caps and killed with the scope (cgroup.kill covers the subtree, and the scope's
populated state includes it), while the scope's own cgroup.procs stays exactly the worker's processes.
So the receiver tells the wrapper's heartbeat from a leftover descendant by construction: after the
worker's exit, a group whose own processes are gone while its heartbeat child is still populated is the
heartbeat ending by itself, which the receiver gives SETTLE_SECONDS before it stops what is left.

THE WATCH (`Watch`, in the receiver). The receiver sleeps in poll on the heartbeat channel beside its
other notifications. Each well-formed heartbeat (this schema, a sequence number above the last) is
taken at the receiver's own monotonic time; the missed-heartbeat deadline is the last one taken (the
release, before the first) plus `heartbeat_window_seconds`. When it passes with the worker still
running, liveness is uncertain: the receiver records it and stops the worker (cause
`heartbeat_missing`) through VELDO-0040's escalation. A heartbeat proves the wrapper is responsive,
never that an effect succeeded.

CLAIM RENEWAL (`Renewals`, in the receiver). A dispatch whose contract binds a claim (the build
station, VELDO-0031) has that claim renewed on every heartbeat taken, so renewal never waits for the
engine. The receiver renews it as the dispatch authority, not as the holder: one registered store
command (`dispatch_heartbeat`) that requires, inside its transaction, the receiver's current service
membership over the repository (control_dispatch's own authorization) and the dispatch record running
under the same contract digest and process identity, and then applies VELDO-0031's own `renew`
transition to the claim the contract binds, with that holder and generation. It changes the claim's
heartbeat time and nothing else. A claim that holder no longer owns at that generation is refused by
that transition's own names; the refusal is recorded and the worker is not stopped for it.

WHAT IT IS NOT. No leadership fencing or timing, recovery of a stopped receiver or orchestrator, or
closing of effect permissions at the deadline (Release 2); the Mac's heartbeat is its own profile's
(VELDO-0124). Standard library only.
"""
import contextlib
import json
import math
import os
from pathlib import Path
import select
import signal
import time

SCHEMA = 'veldo.heartbeat/v1'
OPERATION = 'dispatch_heartbeat'
GROUP = 'veldo-wrapper'
CGROUP = Path('/sys/fs/cgroup')
SETTLE_SECONDS = 1.0
LINE_BYTES = 512
KEEP = 64


def group_path(cgroup):
    """The heartbeat's own child group inside a dispatch's containment group `cgroup`."""
    return CGROUP / str(cgroup).lstrip('/') / GROUP


def make_group(cgroup):
    """In the receiver, before the release: create the heartbeat's child group. Raises OSError."""
    path = group_path(cgroup)
    path.mkdir(exist_ok=True)
    if not (path / 'cgroup.procs').is_file():
        raise OSError('the heartbeat group is not a cgroup')
    return path


# The trusted wrapper's side.

def start(fd, seconds):
    """In the trusted wrapper, after its release and just before it becomes the engine by exec: start
    the heartbeat on channel `fd` every `seconds`, then close the channel here so the engine never
    holds it."""
    engine = os.pidfd_open(os.getpid())
    try:
        first = os.fork()
        if first == 0:
            try:
                # Its own session and process group, taken before the second fork and so before the
                # engine exists: a signal the engine sends to its own group never reaches the heartbeat.
                os.setsid()
                if os.fork() == 0:
                    _beat(fd, seconds, engine)
            finally:
                os._exit(0)
        os.waitpid(first, 0)
    finally:
        os.close(engine)
        os.close(fd)


def _beat(fd, seconds, engine):
    """The heartbeat process. It keeps only its channel and the engine's pidfd, moves itself into the
    heartbeat group and beats until the engine ends or the channel is closed. Never returns."""
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        null = os.open(os.devnull, os.O_RDWR)
        for target in (0, 1, 2):
            os.dup2(null, target)
        keep = {0, 1, 2, fd, engine}
        for name in os.listdir('/proc/self/fd'):
            if int(name) not in keep:
                with contextlib.suppress(OSError):
                    os.close(int(name))
        own = next(line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
        (group_path(own) / 'cgroup.procs').write_text(str(os.getpid()))
        poller = select.poll()
        poller.register(engine, select.POLLIN)
        started, seq = time.monotonic(), 0
        while True:
            seq += 1
            os.write(fd, (json.dumps({'schema': SCHEMA, 'seq': seq, 'monotonic': time.monotonic(),
                                      'pid': os.getpid()}) + '\n').encode())
            # The next slot of the fixed schedule after now: a heartbeat held up is never sent twice.
            due = started + (math.floor((time.monotonic() - started) / seconds) + 1) * seconds
            while time.monotonic() < due:
                if poller.poll(max(1, math.ceil((due - time.monotonic()) * 1000))):
                    os._exit(0)  # the engine has ended
    except BaseException:  # noqa: BLE001 - the heartbeat ends; the receiver's deadline judges it
        pass
    os._exit(0)


# The receiver's side.

class Watch:
    """The receiver's watch of one worker's heartbeat on channel `fd`: the configured interval and
    window, and `released`, the receiver's monotonic time of the release (the deadline's start before
    the first heartbeat)."""

    def __init__(self, fd, interval, window, released):
        self.fd, self.interval, self.window, self.released = fd, interval, window, released
        self.pending, self.open = b'', True
        self.seq, self.count, self.first, self.last, self.max_gap = 0, 0, None, None, None
        self.recent, self.pid = [], None
        self.liveness, self.uncertain_at = 'live', None
        self.renewals = {'renewed': 0, 'refused': []}

    def due(self):
        """The missed-heartbeat deadline on the monotonic clock."""
        return (self.last if self.last is not None else self.released) + self.window

    def expired(self, now):
        return now >= self.due()

    def read(self, now):
        """The heartbeats readable now, each taken at `now`. End of file closes the channel."""
        try:
            chunk = os.read(self.fd, 65536)
        except BlockingIOError:
            return []
        except OSError:
            chunk = b''
        if not chunk:
            self.open = False
            return []
        self.pending += chunk
        taken = []
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            beat = self._parse(line)
            if beat is None:
                continue
            if self.last is not None and (self.max_gap is None or now - self.last > self.max_gap):
                self.max_gap = now - self.last
            self.seq, self.count, self.last = beat['seq'], self.count + 1, now
            self.first = now if self.first is None else self.first
            entry = {'seq': beat['seq'], 'sent': beat['monotonic'], 'taken': now}
            self.recent = (self.recent + [entry])[-KEEP:]
            taken.append(entry)
        if len(self.pending) > LINE_BYTES:
            self.pending = b''  # not a heartbeat line
        return taken

    def _parse(self, line):
        try:
            message = json.loads(line)
        except ValueError:
            return None
        if (not isinstance(message, dict) or message.get('schema') != SCHEMA or type(message.get('seq')) is not int
                or message['seq'] <= self.seq or isinstance(message.get('monotonic'), bool)
                or not isinstance(message.get('monotonic'), (int, float))):
            return None
        if type(message.get('pid')) is int:
            self.pid = message['pid']
        return message

    def lapse(self, now):
        """Liveness is uncertain from `now`: the deadline passed with the worker running."""
        self.liveness, self.uncertain_at = 'uncertain', now

    def summary(self):
        return {'interval_seconds': self.interval, 'window_seconds': self.window, 'released': self.released,
                'beats': self.count, 'first': self.first, 'last': self.last, 'max_gap': self.max_gap,
                'recent': list(self.recent), 'pid': self.pid, 'channel_open': self.open,
                'liveness': self.liveness, 'uncertain_at': self.uncertain_at,
                'renewed': self.renewals['renewed'], 'renewal_refusals': list(self.renewals['refused'])}


class Renewals:
    """Claim renewal on each heartbeat, as the dispatch authority. `dispatches` is the receiver's
    control_dispatch.Dispatches and `dispatch` the control_dispatch module it was made from, whose
    authorization, record reads and claim transition are used, never spelled here a second time."""

    def __init__(self, dispatches, dispatch):
        self.dispatches, self.D = dispatches, dispatch
        self.observations, self.counts = [], {'accepted': 0, 'refused': 0}
        dispatches.conn.command_registry[OPERATION] = {'transaction_transition': self._transition,
                                                       'writes': ('entities', 'journal', 'commands', 'nonces')}

    def _transition(self, conn, params, before):
        D = self.D
        if (params.get('action') != 'renew' or not D._number(params.get('now'))
                or not D._text(params.get('dispatch_id'))):
            raise D.Refused('invalid_input', 'a renewal names its dispatch and time')
        D._authorize(conn, params.get('principal'), params.get('repository'), params['now'])
        current = before.get(D.record_id(params['dispatch_id']))
        if not current or current['kind'] != D.RECORD_KIND:
            raise D.Refused('missing_dispatch', params['dispatch_id'])
        record = current['data']
        if record['state'] != 'running':
            raise D.Refused('transition_refused:%s:renew' % record['state'])
        if params.get('contract_digest') != record['contract_digest']:
            raise D.Refused('binding_mismatch:contract_digest', 'this heartbeat belongs to another dispatch')
        if params.get('process') != record['process']:
            raise D.Refused('binding_mismatch:process', 'this heartbeat belongs to another process')
        contract, binding = record['contract'], record['contract']['claim']
        if binding is None:
            raise D.Refused('invalid_input:claim', 'this dispatch binds no claim')
        backlog = ((before.get(contract['unit']) or {}).get('data') or {}).get('backlog_item_uuid')
        if contract['unit'] not in before or backlog not in before:
            raise D.Refused('missing_authority:claim', binding['entity'])
        return D.CLM.transition(dict(action='renew', unit_id=contract['unit'], backlog_item_uuid=backlog,
                                     claim_id=binding['entity'], holder=binding['holder'],
                                     generation=binding['generation'], capabilities=[],
                                     repository_uuid=contract['repository']), before)

    def renew(self, contract, contract_digest, process, seq, now):
        """Renew the claim `contract` binds for heartbeat `seq`: (True, None), (False, refusal), or
        (None, None) when the contract binds no claim."""
        D, conn, service = self.D, self.dispatches.conn, self.dispatches
        binding = contract.get('claim')
        if binding is None:
            return None, None
        unit = D._entity(conn, contract['unit']) or {}
        backlog = (unit.get('data') or {}).get('backlog_item_uuid')
        ids = [D.record_id(contract['dispatch_id']), contract['unit'], backlog, binding['entity']]
        expected = {}
        for identity in ids:
            if D._text(identity):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
                expected[identity] = row[0] if row else 0
        params = dict(action='renew', dispatch_id=contract['dispatch_id'], contract_digest=contract_digest,
                      process=process, seq=seq, now=now, principal=service.principal, domain=service.domain,
                      repository=service.repository)
        command_id = 'heartbeat/%s/%d' % (contract['dispatch_id'], seq)
        command = dict(command_id=command_id, principal=service.principal, operation=OPERATION, parameters=params,
                       expected_versions=expected, artifact_digests=[], nonce='heartbeat/' + command_id)
        event = {'schema': SCHEMA, 'operation': 'renew', 'domain': service.domain, 'repository': service.repository,
                 'unit': contract['unit'], 'dispatch_id': contract['dispatch_id'], 'request': command_id,
                 'claim': binding['entity'], 'accepted_versions': dict(expected)}
        try:
            result = service.store.execute(conn, command, service.signer, service.sign, service.generation)
        except Exception as error:  # noqa: BLE001 - a refused renewal is recorded, never a crashed receiver
            code = getattr(error, 'code', None) or type(error).__name__
            self.counts['refused'] += 1
            self.observations.append(dict(event, outcome='refused', refusal=code, taxonomy=D.taxonomy(code)))
            return False, code
        self.counts['accepted'] += 1
        self.observations.append(dict(event, outcome='accepted', watermark=result.get('seq')))
        return True, None
