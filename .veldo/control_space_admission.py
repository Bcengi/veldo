#!/usr/bin/env python3
"""Admission: the answer a run gets for the space it asked to hold (design 4.3 and 6.7, VELDO-0331).

Runner admission and need selection (VELDO-0316), waiting holds (VELDO-0334),
and full-pool receiver ends (VELDO-0317).

THE RULE, per pool, the same for every scope: free now, minus what other runs still hold, must be at
least the need plus the pool's floor. What a run still holds is its need minus the size of its own items
at its last measurement, never below zero.

AN ADVISED HOLD STILL COUNTS AS HELD. Held is read from the holds in state admitted and in state advised.
An advised run was started, so the space it was promised is spoken for, and a run of another project on
the same pool is judged against it.

THE MODE DECIDES ONLY THE ANSWER. When the rule holds on every pool the hold is admitted, in either mode.
When a pool is short, admit asks for the mode of the scope the run belongs to:

  act      waiting, with the reason as numbers: the run does not start
  report   advised, with the same numbers: the run would have waited and is started anyway

The scope is the hold's own, never the caller's: the ledger recorded it when the hold was placed (the
project of the unit or of the gated repository, and for a wrapped run the project or plain repository its
working folder is inside, else no project; design 6.7). The ledger checks the answer against that scope
again when it writes it, and refuses advised for a hold of a scope in act mode. Two projects on one pool
can be in different modes; the numbers are the same for both.

Waiting holds keep their recorded answer until a freeing write marks them (VELDO-0334). The service submits initial admission to its serial space worker; its pipe completion
wakes the factory. No free-space reader, project file read or lock wait runs on the service loop.

A HOLD NO RUN ANSWERS FOR IS RELEASED BY THE WORKER (reconcile): at service start, and when an offer
leaves the backlog, a dispatch hold that is admitted or advised, that no dispatch record carries and
that has no live offer is released. The snapshot is the caller's; there is no timer.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path


SCHEMA = 'veldo.control_space_admission/v1'


class NoSpaceOutput:
    """Search both output streams incrementally, retaining only a token-sized tail."""
    tokens = (b'no space left on device', b'enospc')

    def __init__(self):
        self.tails, self.found = {}, False

    def feed(self, stream, chunk):
        data = self.tails.get(stream, b'') + chunk.lower()
        self.found = self.found or any(token in data for token in self.tokens)
        self.tails[stream] = data[-max(map(len, self.tokens)):]


def classify_end(space, termination, found, worktree=None, incomplete=False):
    """Receiver-only snapshot, before census or Signal. Unread is never confirmed full."""
    if not enabled(space) or not found or (termination.get('returncode') == 0
            and termination.get('signal') is None and not termination.get('deadline_stop') and not incomplete):
        return None
    pools = []
    for name in sorted(space['ledger'].config['pools']):
        pool = space['ledger'].pool(name)
        try:
            free = space['free'](pool)
            if type(free) is not int or free < 0:
                raise ValueError('free space unread')
            pools.append({'pool': name, 'free': free, 'floor': pool['floor']})
        except Exception as error:
            pools.append({'pool': name, 'free': None, 'floor': (pool or {}).get('floor'),
                          'unread': type(error).__name__})
    full = any(p['free'] is not None and p['free'] < p['floor'] for p in pools)
    return {'classification': 'environment_failure:no_space' if full else 'unknown_outcome:no_space_unconfirmed',
            'class': 'unavailable_service' if full else 'unknown_outcome',
            'pools': pools, 'worktree': worktree}


def ends(conn, contract):
    """Committed terminal history of this unit, across stations, in store write order."""
    found = []
    # Only the records that name this unit are parsed: the store writes a string as JSON writes it,
    # so the quoted unit is in every record of the unit. The exact test stays the one below.
    for seq, raw in conn.execute("SELECT rowid, data FROM entities WHERE kind='dispatch' AND instr(data, ?)",
                                 (json.dumps(contract.get('unit')),)):
        record = json.loads(raw)
        other = record.get('contract') or {}
        if (all(other.get(k) == contract.get(k) for k in ('domain', 'repository', 'unit'))
                and record.get('state') in ('exited', 'refused', 'unknown')
                and record.get('dispatch_id') != contract.get('dispatch_id')):
            found.append((record.get('end_sequence', 0), record['history'][-1]['at'], seq, record))
    return [row[-1] for row in sorted(found, key=lambda row: row[:-1], reverse=True)]


def settle_end(conn, contract, outcome):
    """Called inside the exit transaction; replay cannot charge or repeat an end twice."""
    if outcome is None:
        return None
    result = dict(outcome)
    prior = ends(conn, contract)
    previous = (prior[0].get('space_end') or {}) if prior else {}
    confirmed = result['classification'] == 'environment_failure:no_space'
    streak = previous.get('consecutive', 0) + 1 if confirmed else 0
    repeated = previous.get('classification') == 'unknown_outcome:no_space_unconfirmed'
    result.update(consecutive=streak, retry=confirmed or not repeated, andon=streak >= 2)
    if result['andon']:
        result['retry'] = False
    return result


def recovery_payload(conn, contract, payload, completed):
    """The kept work the next run is told to recover: the worktrees of the unit's no-space ends since
    its last successful end (`completed`, the dispatch completion gate). A run that ended well after
    them had this brief, so later runs are not told again. The worktrees themselves stay pinned by
    rule 5; releasing that pin is the disposition touchpoint's (VELDO-0327)."""
    trees = []
    for record in ends(conn, contract):
        if completed(record):
            break
        path = (record.get('space_end') or {}).get('worktree')
        if path and path not in trees:
            trees.append(path)
    if not trees:
        return payload
    return dict(payload, space_recovery={'worktrees': trees,
        'brief': 'The previous run ended with a no-space error. These worktrees are kept with their '
                 'uncommitted changes. Recover the work before continuing: ' + ', '.join(trees)})

# The holds whose promise is counted: a run that was started, admitted or advised.
COUNTED = ('admitted', 'advised')


def still_held(hold, pool):
    """What one hold still holds on a pool: its need minus what its own items already use."""
    return max(0, hold['needs'].get(pool, 0) - (hold.get('used') or {}).get(pool, 0))


def held(ledger, pool, but=None):
    """The bytes other runs still hold on a pool: every admitted and every advised hold but `but`."""
    return sum(still_held(hold, pool) for identity, hold in ledger.holds().items()
               if identity != but and hold['state'] in COUNTED and pool in hold['needs'])


def judge(ledger, identity, free):
    """The reason the hold would wait, as numbers (pool, need, free, held, floor), for the first pool
    by name that is short; None when the rule holds on every pool. Reads, and writes nothing."""
    hold = ledger.hold(identity)
    for pool in sorted(hold['needs']):
        record = ledger.pool(pool)
        need, free_now, others = hold['needs'][pool], free(record), held(ledger, pool, identity)
        if free_now - others < need + record['floor']:
            return {'pool': pool, 'need': need, 'free': free_now, 'held': others, 'floor': record['floor']}
    return None


def _admit(ledger, identity, free, principal=None, command_id=None, given=None):
    """One request per hold; only a freeing write permits another judgment.

    Every judgment writes against the version read before its free-space read. A freeing
    write during that read cannot be erased: a stale write retries from the new snapshot.
    """
    versioned = 'expected_version' in inspect.signature(ledger.admit).parameters
    while True:
        version, hold = ledger.hold_snapshot(identity) if hasattr(ledger, 'hold_snapshot') else (None, ledger.hold(identity))
        if hold is None:
            return ledger.admit(identity, 'admitted', principal=principal, command_id=command_id)
        scope = hold.get('scope')
        if hold['state'] != 'waiting' or (hold.get('reason') is not None and not hold.get('freed')):
            return {'ok': True, 'answer': hold['state'], 'reason': hold.get('reason')}
        reason = judge(ledger, identity, free)
        if given is not None and reason is not None and not hold.get('retry_asked'):
            # Claim this hold's one request before entering Signal, in one write with the answer its
            # scope's mode gives now. A crash cannot send it twice, and a report-mode hold is advised
            # already: nothing Signal does, and no lost worker, can leave it waiting (design 6.7).
            claim = answer_of(ledger, scope, reason)
            claimed = ledger.admit(identity, claim, reason, retry_asked=True,
                principal=principal, expected_version=version)
            if claimed.get('reason') == 'stale_version':
                continue
            if not claimed.get('ok'):
                return claimed
            signal = _organ('control_space_signal').signal
            # A refused Signal frees nothing and changes no answer: the judgment below still stands.
            signal(ledger, 'admission_requested', {'pool': reason['pool']},
                   emitter={'hold': identity}, **(given or {}))
            version, hold = ledger.hold_snapshot(identity)
            if hold['state'] != 'waiting':
                return dict(claimed, answer=hold['state'], reason=hold.get('reason'))
            if hold.get('freed'):
                reason = judge(ledger, identity, free)
        answer = answer_of(ledger, scope, reason)
        options = {'expected_version': version} if versioned and version is not None else {}
        result = ledger.admit(identity, answer, reason, principal=principal, command_id=command_id, **options)
        if result.get('reason') == 'stale_version':
            continue
        return dict(result, answer=answer, reason=reason) if result['ok'] else result


def answer_of(ledger, scope, reason):
    """The one place the mode decides: admitted when no pool is short, else waiting in act mode and
    advised in report mode."""
    return 'admitted' if reason is None else 'waiting' if ledger.acts(scope) else 'advised'


def admit(ledger, identity, free, principal=None, command_id=None, **given):
    # Gate and wrapped-run callers share the dispatch admission lock. Their existing
    # read/write adapters have no Signal context and are not queued factory units.
    # Dispatch prepare supplies that context on the worker below.
    with lock(ledger) if getattr(ledger, 'state_root', None) else contextlib.nullcontext():
        return _admit(ledger, identity, free, principal, command_id, given or None)


class Refused(Exception):
    def __init__(self, code, numbers=None):
        super().__init__(code)
        self.code, self.numbers = code, numbers


def accepted(result):
    if not result.get('ok'):
        raise Refused(str(result.get('reason') or 'space_admission_failed'))
    return result


def enabled(space):
    return space is not None and space['ledger'].config.get('enabled') is True


def _organ(name):
    spec = importlib.util.spec_from_file_location('space_admission_' + name,
                                                 Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finished(ledger, project, station):
    """Last five finished dispatches, newest first, including runs without measurements.

    An unmeasured run cannot silently count as zero. Failed exits are finished; a refusal,
    an unknown outcome and a running dispatch are not finished runs.
    """
    found = []
    for (raw,) in ledger.conn.execute("SELECT data FROM entities WHERE kind='dispatch'"):
        record = json.loads(raw)
        contract = record.get('contract') or {}
        if (record.get('state') == 'exited' and contract.get('station') == station
                and not (record.get('space_end') or {}).get('retry')
                and not (record.get('space_end') or {}).get('andon')
                and (contract.get('reservation') or {}).get('project') == project):
            hold = ledger.hold((contract.get('space') or {}).get('hold')) or {}
            at = (record.get('history') or [{}])[-1].get('at', 0)
            found.append((at, contract.get('dispatch_id', ''), hold.get('used') or {}))
    return [row[2] for row in sorted(found, key=lambda row: row[:2], reverse=True)[:5]]


def needs_of(ledger, project, station):
    declaration = next((p for p in ledger.projects if p['project'] == project), None)
    if declaration is None:
        raise Refused('space_project_unknown:' + project)
    # Read the project's current file in the worker, not the startup copy.
    config, yaml = _organ('control_space_config'), _organ('yamlish')
    current = config.read_project(declaration['repository'], yaml.read, config=ledger.config)
    declared = (current.get('needs') or {}).get(station) or {}
    recent = finished(ledger, project, station)
    needs, sources = {}, {}
    for name, pool in sorted(ledger.config['pools'].items()):
        if ledger.pool(name) is None:
            raise Refused('space_pool_unread:' + name)
        if name in declared:
            needs[name], sources[name] = declared[name], 'declared'
        elif len(recent) == 5 and all(type(run.get(name)) is int for run in recent):
            needs[name], sources[name] = max(run[name] for run in recent), 'measured'
        else:
            default = pool['needs'].get(station)
            if default is None:
                raise Refused('space_default_missing:' + station)
            needs[name], sources[name] = default, 'default'
    if not needs:
        raise Refused('space_no_pools')
    return needs, sources


@contextlib.contextmanager
def lock(ledger):
    """Serialize dispatch readers through the admitted write, including separate runners."""
    path = os.path.join(ledger.state_root, 'space-admission.lock')
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def identity_of(repository, unit, station, attempt):
    key = json.dumps([repository, unit, station, attempt], separators=(',', ':')).encode()
    return 'dispatch/' + hashlib.sha256(key).hexdigest()


def carried(ledger, identity):
    """Whether a dispatch record names this hold. The store writes entity data as JSON with its
    strings quoted, and an identity is a digest, so the quoted identity is found in no other field."""
    return ledger.conn.execute("SELECT 1 FROM entities WHERE kind='dispatch' AND instr(data, ?) LIMIT 1",
                               ('"' + identity + '"',)).fetchone() is not None


def prepare(space, *, repository, project, unit, station, attempt):
    """Place and judge before reserving anything, on the caller or space worker."""
    if not enabled(space):
        return {'ok': True, 'space': None}
    ledger = space['ledger']
    try:
        with lock(ledger):
            base = identity_of(repository, unit, station, attempt)
            identity, retry = base, 0
            hold = ledger.hold(identity)
            # A preparation that failed after admission released its promise. A fresh preparation
            # gets a fresh hold, while a waiting preparation keeps its identity and its answer.
            # VELDO-0317: a refunded attempt asks again under the number of the run that ended. The
            # hold a dispatch record carries is that dispatch's own, live until its receiver releases
            # it, so it is passed over here as reconcile passes over it, and this run is judged anew.
            while hold and (hold['state'] == 'released' or carried(ledger, identity)):
                retry += 1
                identity = base + '/' + str(retry)
                hold = ledger.hold(identity)
            if hold is None:
                needs, sources = needs_of(ledger, project, station)
                accepted(ledger.place_hold(identity, needs, sources, scope={'type': 'project', 'id': project}))
                hold = ledger.hold(identity)
            if hold['state'] == 'waiting':
                def free(pool):
                    value = space['free'](pool)
                    if type(value) is not int or value < 0:
                        raise Refused('space_free_unread:' + pool['name'])
                    return value
                accepted(_admit(ledger, identity, free, given={key: value for key, value in space.items()
                    if key != 'ledger'}))
                hold = ledger.hold(identity)
            answer = {'ok': True, 'space': {'hold': identity, 'needs': hold['needs']},
                      'answer': hold['state'], 'reason': hold.get('reason'), 'source': hold['source']}
            if hold['state'] == 'waiting':
                answer.update(ok=False, code='space_wait:' + hold['reason']['pool'])
            return answer
    except Exception as error:  # an unread pool or declaration grants no promise
        return {'ok': False, 'code': getattr(error, 'code', 'space_admission_unread'),
                'detail': str(error)[:300]}


def reconcile(space, left=None):
    """Release the dispatch holds no run will ever answer for: admitted or advised, carried by no
    dispatch record, and with no live offer. `left` is the snapshot the caller took: None at service
    start, when no offer is live yet, so every such hold; else the offers (repository, unit,
    station, attempt) that left the backlog, and only their holds. Runs in the space worker, under
    the admission lock. A hold a dispatch record carries is released by that dispatch's own end."""
    if not enabled(space):
        return {'ok': True, 'released': []}
    ledger = space['ledger']
    try:
        with lock(ledger):
            bases = None if left is None else {identity_of(*key) for key in left}
            carried = set()
            for (raw,) in ledger.conn.execute("SELECT data FROM entities WHERE kind='dispatch'"):
                carried.add(((json.loads(raw).get('contract') or {}).get('space') or {}).get('hold'))
            released = []
            for identity, hold in sorted(ledger.holds().items()):
                if (not identity.startswith('dispatch/') or hold['state'] not in COUNTED
                        or identity in carried
                        or bases is not None and '/'.join(identity.split('/')[:2]) not in bases):
                    continue
                accepted(ledger.release(identity))
                released.append(identity)
            return {'ok': True, 'released': released}
    except Exception as error:  # named, and tried again at the next start or leaving
        return {'ok': False, 'code': getattr(error, 'code', 'space_admission_unread'),
                'detail': str(error)[:300]}


class Requests:
    """Judgments on the existing consumer, coalesced by dispatch attempt.

    Completed answers that carry a hold are retained: unrelated factory passes do no work for
    them. A waiting answer is invalidated by its hold's committed freed mark (VELDO-0334). An
    answer with no hold (a failed read, a lost worker) is reported by name once and then dropped:
    its completion wakes the factory, and the pass after the one that reports it submits the
    judgment again, so a freed mark that outlived a failed judgment is looked at again.
    """
    def __init__(self, service, loop):
        self.service, self.loop, self.answers = service, loop, {}
        # The offers asked since the last pass ended, and the count of leavings sent to the worker.
        self.asked, self.leavings = set(), 0

    def passed(self):
        """The end of one factory pass of this line. An answered offer the pass did not ask again
        has left the backlog: its answer is dropped here, and the worker releases its hold when no
        dispatch record carries it (reconcile). Nothing is read or written on the service loop."""
        left = sorted(set(self.answers) - self.asked)
        self.asked = set()
        for key in left:
            del self.answers[key]
        space, consumer = self.service.space, self.service.space_consumer
        if left and consumer is not None and enabled(space):
            self.leavings += 1
            consumer.submit(('admission_left', id(self), self.leavings), lambda: reconcile(space, left))
        return left

    def taken(self, contract):
        """A dispatch record now carries this offer's hold: its answer is spent. A refunded attempt
        (VELDO-0317) asks under the same number, and must be judged again, never answered from here."""
        self.answers.pop(tuple(contract[name] for name in ('repository', 'unit', 'station', 'attempt')), None)

    def prepare(self, **given):
        space = self.service.space
        if not enabled(space):
            return {'ok': True, 'space': None}
        key = tuple(given[name] for name in ('repository', 'unit', 'station', 'attempt'))
        self.asked.add(key)
        answer = self.answers.get(key)
        if answer is not None:
            # Only an answer that carries a hold is kept: waiting, admitted or advised. Any other
            # answer (an unread pool, a lost worker) is returned once, and the next pass asks again.
            # A waiting answer whose hold a freeing write marked is dropped and judged again.
            bound = answer.get('space')
            hold = space['ledger'].hold(bound['hold']) if bound else None
            del self.answers[key]
            if hold is None:
                if not bound:
                    return answer
            elif hold['state'] != 'released' and not (hold['state'] == 'waiting' and hold.get('freed')):
                self.answers[key] = answer
                return answer
        consumer = self.service.space_consumer
        if consumer is None:
            return {'ok': False, 'code': 'space_worker_unavailable'}

        def complete(result):
            self.answers[key] = result
            self.loop.wake('space_admission', key)

        consumer.submit(('admission',) + key, lambda: prepare(space, **given), complete)
        return {'ok': False, 'code': 'space_pending'}


def metrics(ledger, free):
    """An explicit per-pool read and counts; callers choose when to request this snapshot."""
    holds = ledger.holds()
    return {'pools': {name: {'free': free(ledger.pool(name)), 'floor': ledger.pool(name)['floor'],
                            'held': held(ledger, name)} for name in sorted(ledger.config['pools'])},
            'holds': {state: sum(record['state'] == state for record in holds.values())
                      for state in ('admitted', 'waiting', 'advised')}}
