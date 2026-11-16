#!/usr/bin/env python3
"""Admission: the answer a run gets for the space it asked to hold (design 4.3 and 6.7, VELDO-0331).

Runner admission and need selection (VELDO-0316).

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

Waiting holds keep their recorded answer. The freeing-event retry and Signal request belong to
VELDO-0334. The service submits initial admission to its serial space worker; its pipe completion
wakes the factory. No free-space reader, project file read or lock wait runs on the service loop.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path


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
        need, free_now, others = hold['needs'][pool], free(record), held(ledger, pool, identity)
        if free_now - others < need + record['floor']:
            return {'pool': pool, 'need': need, 'free': free_now, 'held': others, 'floor': record['floor']}
    return None


def _admit(ledger, identity, free, principal=None, command_id=None):
    """Judge a waiting hold and write the answer: admitted, or with the reason waiting for a run of a
    scope in act mode and advised for a run of a scope in report mode. The scope is the one the hold
    records. Returns the ledger's answer with the answer and the reason added."""
    hold = ledger.hold(identity)
    if hold is None:
        return ledger.admit(identity, 'admitted', principal=principal, command_id=command_id)
    scope = hold.get('scope')
    reason = judge(ledger, identity, free)
    answer = 'admitted' if reason is None else 'waiting' if ledger.acts(scope) else 'advised'
    result = ledger.admit(identity, answer, reason, principal=principal, command_id=command_id)
    return dict(result, answer=answer, reason=reason) if result['ok'] else result


def admit(ledger, identity, free, principal=None, command_id=None):
    # Gate and wrapped-run callers share the dispatch admission lock. Readers without a
    # store (test doubles) keep the original pure ledger interface.
    with lock(ledger) if getattr(ledger, 'state_root', None) else contextlib.nullcontext():
        return _admit(ledger, identity, free, principal, command_id)


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


def prepare(space, *, repository, project, unit, station, attempt):
    """Place and judge before reserving anything. No removals or retry scheduling here."""
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
            while hold and hold['state'] == 'released':
                retry += 1
                identity = base + '/' + str(retry)
                hold = ledger.hold(identity)
            if hold is None:
                needs, sources = needs_of(ledger, project, station)
                accepted(ledger.place_hold(identity, needs, sources, scope={'type': 'project', 'id': project}))
                hold = ledger.hold(identity)
            if hold['state'] == 'waiting' and hold.get('reason') is None:
                def free(pool):
                    value = space['free'](pool)
                    if type(value) is not int or value < 0:
                        raise Refused('space_free_unread:' + pool['name'])
                    return value
                accepted(_admit(ledger, identity, free))
                hold = ledger.hold(identity)
            answer = {'ok': True, 'space': {'hold': identity, 'needs': hold['needs']},
                      'answer': hold['state'], 'reason': hold.get('reason'), 'source': hold['source']}
            if hold['state'] == 'waiting':
                answer.update(ok=False, code='space_wait:' + hold['reason']['pool'])
            return answer
    except Exception as error:  # an unread pool or declaration grants no promise
        return {'ok': False, 'code': getattr(error, 'code', 'space_admission_unread'),
                'detail': str(error)[:300]}


class Requests:
    """Initial judgments on the existing consumer, coalesced by dispatch attempt.

    Completed answers that carry a hold are retained: unrelated factory passes do no work for
    them. A later ticket supplies the freeing-event retry. An answer with no hold (a failed
    read, a lost worker) is reported by name once and then dropped: its completion wakes the
    factory, and the pass after the one that reports it submits the judgment again.
    """
    def __init__(self, service, loop):
        self.service, self.loop, self.answers = service, loop, {}

    def prepare(self, **given):
        space = self.service.space
        if not enabled(space):
            return {'ok': True, 'space': None}
        key = tuple(given[name] for name in ('repository', 'unit', 'station', 'attempt'))
        answer = self.answers.get(key)
        if answer is not None:
            # Only an answer that carries a hold is kept: waiting, admitted or advised. Any other
            # answer (an unread pool, a lost worker) is returned once, and the next pass asks again.
            bound = answer.get('space')
            hold = space['ledger'].hold(bound['hold']) if bound else None
            del self.answers[key]
            if hold is None:
                if not bound:
                    return answer
            elif hold['state'] != 'released':
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
