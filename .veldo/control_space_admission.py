#!/usr/bin/env python3
"""Admission: the answer a run gets for the space it asked to hold (design 4.3 and 6.7, VELDO-0331).

WHAT IS HERE. The part of admission that reads the mode, with the arithmetic that part needs.

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

Admission requested is sent once per hold. A recorded wait is read again only after a freeing
ledger write sets its mark (VELDO-0334). When the ledger refuses that one Signal, nothing was
removed and the hold is judged all the same, so a run of a scope in report mode is advised and
never left on the reserved wait; the answer then names the refusal as retry_refused.
Runner preparation and need selection are VELDO-0316.
`free(pool)` is given: it returns the free bytes of one
pool record at the moment of the call. No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

import importlib.util
import json
import os
import re
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('admission_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMA = 'veldo.control_space_admission/v1'

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
        free_now = free(record)
        if type(free_now) is not int or free_now < 0:
            raise organ('control_dispatch').Refused('space_free_unread:' + pool)
        need, others = hold['needs'][pool], held(ledger, pool, identity)
        if free_now - others < need + record['floor']:
            return {'pool': pool, 'need': need, 'free': free_now, 'held': others, 'floor': record['floor']}
    return None


def admit(ledger, identity, free, principal=None, command_id=None, **given):
    """Judge a waiting hold and write the answer: admitted, or with the reason waiting for a run of a
    scope in act mode and advised for a run of a scope in report mode. The scope is the one the hold
    records. Returns the ledger's answer with the answer and the reason added."""
    with ledger.item_lock('admission:' + ledger.host):
        return _admit(ledger, identity, free, principal, command_id, given)


def _admit(ledger, identity, free, principal, command_id, given):
    hold = ledger.hold(identity)
    if hold is None:
        return ledger.admit(identity, 'admitted', principal=principal, command_id=command_id)
    if hold['state'] != 'waiting':
        return ledger.admit(identity, 'admitted', principal=principal, command_id=command_id)
    if hold.get('reason') is not None and hold['retry_asked'] and not hold['freed']:
        return {'ok': True, 'state': 'waiting', 'answer': 'waiting', 'reason': hold['reason']}
    scope = hold.get('scope')
    version = ledger._row('space:hold:' + identity, 'space_hold')[0]
    reason = judge(ledger, identity, free)
    retry = None
    if reason is not None and not hold['retry_asked']:
        # Reserve this hold's one request before Signal can commit any removal outcomes.
        asked = ledger.admit(identity, 'waiting', reason, retry_asked=True, principal=principal,
                             expected_version=version)
        if not asked['ok']:
            return asked
        given.setdefault('probe', organ('control_space_probe'))
        given.setdefault('kinds', organ('control_space_kinds'))
        given.setdefault('remover', organ('control_space_remove'))
        sent = organ('control_space_signal').signal(
            ledger, 'admission_requested', {'pool': reason['pool']}, free=free, **given)
        # A refused retry removed nothing, and the hold is still judged: the reservation above left it
        # waiting, and a run of a scope in report mode is advised, never left waiting (fix round 1).
        retry = None if sent['ok'] else {'reason': sent['reason'], 'detail': sent.get('detail', '')}
        version = ledger._row('space:hold:' + identity, 'space_hold')[0]
        reason = judge(ledger, identity, free)
    answer = 'admitted' if reason is None else 'waiting' if ledger.acts(scope) else 'advised'
    result = ledger.admit(identity, answer, reason, principal=principal, command_id=command_id,
                          expected_version=version)
    if not result['ok']:
        return result
    result = dict(result, answer=answer, reason=reason)
    if retry is not None:
        result['retry_refused'] = retry
    return result


def measured(ledger, dispatch_id):
    """The last measured sizes of this run's own items, per pool; unknown is not zero."""
    items = [item for item in ledger.items().values()
             if ((item.get('owner') or {}).get('run') or {}).get('id') == dispatch_id]
    sizes = {}
    unknown = set()
    for item in items:
        pool, size = item.get('pool'), item.get('size')
        if not pool:
            continue
        if not isinstance(size, dict) or type(size.get('bytes')) is not int:
            unknown.add(pool)
        else:
            sizes[pool] = sizes.get(pool, 0) + size['bytes']
    return {pool: size for pool, size in sizes.items() if pool not in unknown}


def finished(ledger, dispatches, project, station):
    """Last five exited runs, in durable exit order, including failed runs, never refusals.

    A run with a space binding gives the measurements its release saved, never a promised need. A legacy
    run, exited without a binding (before admission existed, or while the ledger was disabled), gives
    the last measurements of its own items in the ledger. A run missing a pool's measurement keeps
    that pool on its default.
    """
    runs = []
    seen = set()
    for (raw,) in dispatches.conn.execute(
            "SELECT transition FROM journal WHERE command_id LIKE 'dispatch/exit/%' ORDER BY seq DESC"):
        for entry in json.loads(raw).values():
            record = entry.get('data') or {}
            contract = record.get('contract') or {}
            identity = record.get('dispatch_id')
            if (entry.get('kind') != 'dispatch' or record.get('state') != 'exited' or identity in seen
                    or contract.get('domain') != dispatches.domain
                    or contract.get('repository') != dispatches.repository
                    or (contract.get('reservation') or {}).get('project') != project
                    or contract.get('station') != station):
                continue
            seen.add(identity)
            hold = ledger.hold((contract.get('space') or {}).get('hold')) or {}
            sizes = hold.get('used', {}) if hold.get('state') == 'released' else {}
            if not contract.get('space'):
                sizes = measured(ledger, identity)
            runs.append(sizes)
            if len(runs) == 5:
                return runs
    return runs


def needs(ledger, dispatches, project, station, declarations):
    """Declared bytes, else the maximum of five finished runs, else installation defaults."""
    history = finished(ledger, dispatches, project, station)
    declared = (declarations.get('needs') or {}).get(station) or {}
    values, sources = {}, {}
    for pool, config in sorted(ledger.config['pools'].items()):
        if pool in declared:
            values[pool], sources[pool] = declared[pool], 'declared'
        elif len(history) == 5 and all(pool in run for run in history):
            values[pool], sources[pool] = max(run[pool] for run in history), 'measured'
        else:
            # Coordination is project work and uses the build default until it declares a station need.
            values[pool], sources[pool] = config['needs'].get(station, config['needs']['build']), 'default'
    return values, sources


def prepare(space, dispatches, unit, station, project, repository):
    """Place and judge a stable unit/station/attempt hold before any reservation.

    An already waiting hold keeps its identity and recorded answer until space is freed.
    Serialized across pools so two
    concurrent preparations cannot both promise the same free bytes.
    """
    if space is None or space['ledger'].config.get('enabled') is not True:
        return None
    ledger = space['ledger']
    D = organ('control_dispatch')
    declarations = next((p for p in ledger.projects
                         if os.path.realpath(p.get('repository', '')) == os.path.realpath(repository)), None)
    if declarations is None:
        raise D.Refused('space_unknown_scope', 'the repository has no space declaration')
    declarations = organ('control_space_config').read_project(
        repository, organ('yamlish').read, config=ledger.config, project=declarations['project'])
    scope = {'type': 'project', 'id': declarations['project']}
    base = json.dumps([dispatches.domain, dispatches.repository, unit, station,
                       dispatches.attempts(unit, station) + 1], separators=(',', ':'))
    with ledger.item_lock('admission:' + ledger.host):
        identity = base
        generation = 0
        while (ledger.hold(identity) or {}).get('state') == 'released':
            generation += 1
            identity = base + '/' + str(generation)
        hold = ledger.hold(identity)
        if hold is None:
            values, sources = needs(ledger, dispatches, project, station, declarations)
            placed = ledger.place_hold(identity, values, sources, scope=scope)
            if not placed['ok']:
                raise D.Refused(placed['reason'], placed.get('detail', ''))
            hold = ledger.hold(identity)
        if hold['state'] != 'waiting':
            raise D.Refused('space_hold_state:' + hold['state'], 'another preparation owns this hold')
        answer = admit(ledger, identity, space['free'],
                       **{key: value for key, value in space.items() if key not in ('ledger', 'free')})
        if not answer['ok']:
            raise D.Refused(answer['reason'], answer.get('detail', ''))
        if answer['answer'] == 'waiting':
            error = D.Refused('space_wait:' + answer['reason']['pool'])
            error.space = dict(answer['reason'])
            raise error
        return {'hold': identity, 'needs': dict(hold['needs'])}


def runner_hold(identity, dispatches):
    """Whether `identity` is a hold prepare() places for this domain and repository: the JSON list
    [domain, repository, unit, station, attempt], with a '/generation' suffix after a released one."""
    try:
        value, end = json.JSONDecoder().raw_decode(identity)
    except (TypeError, ValueError):
        return False
    rest = identity[end:]
    return (isinstance(value, list) and len(value) == 5 and value[:2] == [dispatches.domain, dispatches.repository]
            and (rest == '' or (rest[:1] == '/' and rest[1:].isdigit())))


def recover(space, dispatches):
    """Start recovery: release every admitted or advised hold of this domain and repository that no
    dispatch record binds.

    prepare() commits the answer before the Runner reserves a slot and writes the dispatch. A service
    that dies between the two leaves a counted hold that nothing else names: its unit is refused with
    space_hold_state on every later offer and its need stays held on every pool. Run at service start,
    before any offer, under the admission lock, it reads the dispatch records and releases each such
    orphan; the unit's next preparation places a fresh generation and is judged again. A waiting hold
    is never released here: it is the stable identity a waiting unit keeps (VELDO-0334). Returns
    [{hold, state, released, refusal}], one per orphan."""
    if space is None or space['ledger'].config.get('enabled') is not True:
        return []
    ledger = space['ledger']
    D = organ('control_dispatch')
    with ledger.item_lock('admission:' + ledger.host):
        bound = set()
        for (data,) in dispatches.conn.execute('SELECT data FROM entities WHERE kind=?', (D.RECORD_KIND,)):
            binding = (json.loads(data).get('contract') or {}).get('space')
            if isinstance(binding, dict) and isinstance(binding.get('hold'), str):
                bound.add(binding['hold'])
        out = []
        for identity, hold in sorted(ledger.holds().items()):
            if hold.get('state') not in COUNTED or identity in bound or not runner_hold(identity, dispatches):
                continue
            result = ledger.release(identity)
            out.append({'hold': identity, 'state': hold['state'], 'released': bool(result.get('ok')),
                        'refusal': None if result.get('ok') else str(result.get('reason'))})
        return out


def status(ledger, free):
    """Current per-pool free/floor/held bytes and counts by admission outcome."""
    holds = ledger.holds().values()
    return {'pools': {pool['name']: {'free': free(pool), 'floor': pool['floor'],
                                    'held': held(ledger, pool['name'])} for pool in ledger._pools()},
            'holds': {state: sum(h['state'] == state for h in holds)
                      for state in ('admitted', 'waiting', 'advised')}}


# VELDO-0317: observations are taken before census/Signal can free any bytes.
NO_SPACE = 'environment_failure:no_space'
UNCONFIRMED = 'unknown_outcome:no_space_unconfirmed'


class Output:
    """Bounded streaming search of both output pipes, including split error text."""
    pattern = re.compile(rb'no space left on device|\bENOSPC\b|\[Errno 28\]', re.I)

    def __init__(self):
        self.tails, self.found = {}, False

    def feed(self, stream, chunk):
        data = self.tails.get(stream, b'') + chunk
        self.found = self.found or self.pattern.search(data) is not None
        self.tails[stream] = data[-64:]


def last_end(slots, station=None):
    """The space state the latest end of this unit left on its index slots (dispatch.unit_slots): of every
    station, or of one. The exit transaction writes it, so no record and no journal row is read for it."""
    states = [slot['space'] for slot in slots if isinstance(slot.get('space'), dict)
              and (station is None or slot.get('station') == station)]
    return max(states, key=lambda state: state['seq'], default={})


def classify(space, contract, unsuccessful, found, worktree=None):
    """Text plus a measured short pool confirms an environment failure, in either mode."""
    if (space is None or space['ledger'].config.get('enabled') is not True
            or not unsuccessful or not found):
        return None
    ledger = space['ledger']
    pools = []
    for name in sorted((contract.get('space') or {}).get('needs') or ledger.config['pools']):
        pool = ledger.pool(name)
        try:
            free = space['free'](pool)
            if type(free) is not int or free < 0:
                free = None
        except (OSError, ValueError, TypeError, KeyError, StopIteration):
            free = None
        pools.append({'pool': name, 'free': free, 'floor': pool['floor'] if pool else None})
    return {'classification': classification(pools), 'pools': pools, 'worktree': worktree}


def classification(pools):
    short = any(p['free'] is not None and p['floor'] is not None and p['free'] < p['floor'] for p in pools)
    return NO_SPACE if short else UNCONFIRMED


def disposition(slots, contract, observation):
    """Derive the retry bounds from committed ends, never a process-local counter.

    Environment failures count in a row over the unit, whatever station ended and whoever started the run.
    An unconfirmed end is repeated once: the end after one that was given its repeat is that repeat and
    stands, and the end after a standing one is a new run with a repeat of its own.
    """
    classification = observation['classification']
    if classification == NO_SPACE:
        prior = last_end(slots)
        consecutive = prior.get('consecutive', 0) + 1 if prior.get('classification') == NO_SPACE else 1
    else:
        prior = last_end(slots, contract['station'])
        consecutive = 2 if prior.get('classification') == UNCONFIRMED and prior.get('retry') else 1
    return dict(observation, consecutive=consecutive, retry=consecutive < 2,
                andon=classification == NO_SPACE and consecutive >= 2,
                taxonomy='unavailable_service' if classification == NO_SPACE else 'unknown_outcome')


RETAINED = 8  # worktree paths a slot remembers; the brief names only those still live in the ledger
RETAINED_STATES = ('present', 'due', 'deferred', 'kept')


def ended(slots, contract, failure):
    """The space state an exited end leaves on its own index slot, or None when there is none to keep.

    A no-space end records its classification and count. Any other exited end is written only when it
    ends a chain (the unit's latest state, or this station's, still names a classification), so a unit
    that never met a full pool carries nothing.
    """
    own = last_end(slots, contract['station'])
    latest = last_end(slots)
    if not failure and not own.get('classification') and not latest.get('classification'):
        return None
    failure = failure or {}
    retained = list(own.get('retained') or [])
    path = failure.get('worktree')
    if failure.get('classification') == NO_SPACE and path:
        retained = ([kept for kept in retained if kept != path] + [path])[-RETAINED:]
    return {'seq': latest.get('seq', 0) + 1, 'classification': failure.get('classification'),
            'consecutive': failure.get('consecutive', 0), 'retry': bool(failure.get('retry')), 'retained': retained}


def brief(slots, ledger, payload):
    """Carry retained work into the next packet, including a later station of the ticket.

    Only the worktree of an environment_failure:no_space end is named, and only while the ledger still
    holds it as a live item: a worktree that was removed, or whose work landed, is no longer claimed.
    """
    if ledger is None:
        return payload
    retained = set()
    for slot in slots:
        for path in (slot.get('space') or {}).get('retained') or []:
            held = ledger._at('path:' + path)
            if held is not None and held[2].get('kind') == 'worktree' and held[2].get('state') in RETAINED_STATES:
                retained.add(path)
    if not retained:
        return payload
    return dict(payload if isinstance(payload, dict) else {'payload': payload}, retained_worktrees=sorted(retained),
                space_recovery='These worktrees were kept after a no-space end and hold uncommitted changes: '
                               + ', '.join(sorted(retained)))


class Requests:
    """Service admission on its serial space worker, using the current preparation API.

    The answer belongs to a unit/station/attempt. A counted hold survives account shortage;
    a failed read is reported once then retried. A waiting answer is invalidated only by
    its committed freed mark. The completion pipe wakes the factory without polling.
    """
    def __init__(self, service, loop, dispatches):
        self.service, self.loop, self.dispatches = service, loop, dispatches
        self.answers, self.asked, self.leavings = {}, set(), 0

    def _dispatches(self):
        import copy
        dispatches = copy.copy(self.dispatches)
        dispatches.conn = self.service.space['ledger'].conn
        return dispatches

    def prepare(self, space, dispatches, unit, station, project, repository):
        if space is None or space['ledger'].config.get('enabled') is not True:
            return None
        D = organ('control_dispatch')
        key = (unit, station, dispatches.attempts(unit, station) + 1)
        self.asked.add(key)
        answer = self.answers.get(key)
        if answer is not None:
            hold = space['ledger'].hold((answer.get('space') or {}).get('hold'))
            if not hold or hold['state'] == 'released' or hold['state'] == 'waiting' and hold.get('freed'):
                del self.answers[key]
                if answer.get('space'):
                    answer = None
            if answer is not None:
                if answer.get('ok'):
                    return answer.get('space')
                error = D.Refused(answer.get('code') or answer.get('reason') or 'space_worker_failed')
                error.space = answer.get('numbers') or {}
                raise error
        consumer = self.service.space_consumer
        if consumer is None:
            raise D.Refused('space_worker_unavailable')

        def judge():
            current = self._dispatches()
            try:
                bound = prepare(space, current, unit, station, project, repository)
                return {'ok': True, 'space': bound}
            except Exception as error:
                code = str(getattr(error, 'code', None) or type(error).__name__)
                bound = None
                if code.startswith('space_wait:'):
                    base = json.dumps([current.domain, current.repository, unit, station, key[2]], separators=(',', ':'))
                    identity, generation = base, 0
                    while (space['ledger'].hold(identity) or {}).get('state') == 'released':
                        generation += 1
                        identity = base + '/' + str(generation)
                    hold = space['ledger'].hold(identity)
                    if hold:
                        bound = {'hold': identity, 'needs': dict(hold['needs'])}
                return {'ok': False, 'code': code, 'space': bound, 'numbers': getattr(error, 'space', None)}

        def complete(answer):
            self.answers[key] = answer
            self.loop.wake('space_admission', key)

        consumer.submit(('admission', dispatches.repository) + key, judge, complete)
        raise D.Refused('space_pending')

    def taken(self, contract):
        self.answers.pop((contract['unit'], contract['station'], contract['attempt']), None)

    def passed(self):
        left = sorted(set(self.answers) - self.asked)
        self.asked.clear()
        holds = [(self.answers.pop(key).get('space') or {}).get('hold') for key in left]
        holds = [hold for hold in holds if hold]
        consumer, space = self.service.space_consumer, self.service.space
        if holds and consumer is not None and space is not None:
            self.leavings += 1
            def release():
                current = self._dispatches()
                bound = {((json.loads(raw).get('contract') or {}).get('space') or {}).get('hold')
                         for (raw,) in current.conn.execute("SELECT data FROM entities WHERE kind='dispatch'")}
                for identity in holds:
                    hold = space['ledger'].hold(identity)
                    if identity not in bound and hold and hold['state'] in COUNTED:
                        space['ledger'].release(identity)
                return {'ok': True}
            consumer.submit(('admission_left', self.dispatches.repository, self.leavings), release)
        return left
