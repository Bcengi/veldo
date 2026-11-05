#!/usr/bin/env python3
"""The owner's batch command in the running factory (VELDO-0239): the starter every production intake hands
`/batch <project>` to, and the line that runs the requested batch through control_batch.

THE STARTER (Starter). control_intake reads `/batch <project>`, from Telegram or from the UI's project view
(the same text through the authenticated API), and calls the starter with the project, the principal the
intake attributed the message to and its source. The starter reads the project's record from the authority
store and refuses anyone but the project's owner (missing_authority:batch/owner) and an unknown project
(invalid_input:batch/project). It takes the project's eligible units from the store (control_batch.Authority:
each unit whose floor record is handed off, bound to its reviewed commit, and that has not landed) and
records the owner's request, kind `batch_request`, one per source, so a repeated message starts nothing
again. Nothing is proposed: the message is the command, never work. A request with no eligible unit is
recorded `empty` and runs nothing.

THE LINE (BatchLine). The factory line of the project's repository (control_service Line, with its `land`
configuration) runs each request on its pass: `requested` is assembled, gated once and, when green, asked
of the owner as one inbox question (VELDO-0064; his signed answer is the VELDO-0068 settlement the batch
reads back); red returns each named unit to its fix round, recorded in the store (control_batch.Authority);
`awaiting_approval` lands once the owner's settled grant for exactly the batch's subject is in the store,
with a receipt per unit written to the store; a trunk moved after the watermark re-lands (re-merge, hook,
gate, ask again). The request record carries the batch's state, tip, inventory, refusal and receipts.

Standard library only; the store connection, coordinates, the land configuration and the signers are
arguments."""

import hashlib
import importlib.util
import json
from pathlib import Path
import time


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, str(Path(__file__).resolve().with_name(name)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BT = _sibling('veldo_batch_service_batch', 'control_batch.py')
REQUEST_KIND = 'batch_request'
REQUEST_SCHEMA = 'veldo.batch_request/v1'
REQUESTED, AWAITING, OPEN = 'requested', 'awaiting_approval', ('requested', 'awaiting_approval')
NOT_OWNER = 'missing_authority:batch/owner'
NO_PROJECT = 'invalid_input:batch/project'


def request_id(source):
    return 'batch-request:' + hashlib.sha256(str(source).encode()).hexdigest()[:24]


def _row(conn, identity):
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
    return {'id': identity, 'kind': row[0], 'version': row[1], 'data': json.loads(row[2])} if row else None


def _upsert(store, conn, signer, sign, generation, identity, kind, data):
    current = _row(conn, identity)
    if current is not None and current['data'] == data:
        return current
    command_id = 'batch-request/%s' % BT.digest([identity, data])[len('sha256:'):][:32]
    store.execute(conn, {'command_id': command_id, 'principal': signer, 'operation': 'upsert_entity',
                         'parameters': {'entity_id': identity, 'kind': kind, 'data': data},
                         'expected_versions': {identity: current['version'] if current else 0},
                         'artifact_digests': [], 'nonce': command_id + '/nonce'}, signer, sign, generation)
    return _row(conn, identity)


class Starter:
    """The batch starter an Intake is built with (`batches=`): called (project, principal, source)."""

    def __init__(self, store, conn, *, domain, signer, sign, generation=1, clock=time.time, observe=None):
        self.store, self.conn, self.domain = store, conn, domain
        self.signer, self.sign, self.generation, self.clock = signer, sign, generation, clock
        self.observe = observe or (lambda event: None)

    def _answer(self, outcome, project, principal, source, refusal=None, **fields):
        event = dict({'schema': REQUEST_SCHEMA, 'operation': 'batch_start', 'domain': self.domain,
                      'project': project, 'principal': principal, 'source': source, 'outcome': outcome}, **fields)
        if refusal is not None:
            event.update(refusal=refusal, taxonomy=BT.taxonomy(refusal))
        self.observe(event)
        return dict({'outcome': outcome, 'reason': refusal} if refusal else {'outcome': outcome}, **fields)

    def __call__(self, *, project, principal, source):
        record = _row(self.conn, 'project:' + str(project))
        data = record['data'] if record and record['kind'] == 'project' else None
        if data is None or not BT._text(data.get('execution_repository')):
            return self._answer('refused', project, principal, source, NO_PROJECT)
        if not BT._text(principal) or principal != data.get('owner'):
            return self._answer('refused', project, principal, source, NOT_OWNER)
        rid = request_id(source)
        existing = _row(self.conn, rid)
        if existing is not None:
            return self._answer(existing['data'].get('state'), project, principal, source, batch_request=rid,
                                repeated=True)
        repository = data['execution_repository']
        authority = BT.Authority(self.store, self.conn, domain=self.domain, repository=repository,
                                 signer=self.signer, sign=self.sign, generation=self.generation)
        units = [{'unit': u['unit'], 'commit': u['commit']} for u in BT.eligible(authority, authority.units_of(project))]
        state = REQUESTED if units else 'empty'
        _upsert(self.store, self.conn, self.signer, self.sign, self.generation, rid, REQUEST_KIND, {
            'schema': REQUEST_SCHEMA, 'project': project, 'repository': repository, 'principal': principal,
            'source': source, 'units': units, 'state': state, 'requested_at': self.clock(), 'batch': None})
        return self._answer(state, project, principal, source, batch_request=rid, units=[u['unit'] for u in units])


def starter(store, conn, *, domain, signer, sign, generation=1, clock=time.time, observe=None):
    """The production batch starter of an intake on `conn`."""
    return Starter(store, conn, domain=domain, signer=signer, sign=sign, generation=generation, clock=clock,
                   observe=observe)


class BatchLine:
    """The batches of one repository's line. `land` is the line's land configuration (repository, trunk,
    remote, installation, workspace_root); `inbox()` the repository's inbox, made for each use;
    `command_sign` the service principal's inbox-command signature; `identity` the (name, email) the batch
    commits under and `push_identity` the identity record a push runs under (VELDO-0142, VELDO-0153)."""

    def __init__(self, store, conn, *, domain, repository, land, signer, sign, command_sign, inbox, identity,
                 push_identity=None, generation=1, store_uuid=None, hook=None, observe=None, clock=time.time,
                 gate_timeout=None):
        self.store, self.conn, self.domain, self.repository, self.land = store, conn, domain, repository, land
        self.signer, self.sign, self.command_sign, self.inbox = signer, sign, command_sign, inbox
        self.identity, self.push_identity, self.generation = identity, push_identity, generation
        self.store_uuid, self.hook, self.clock, self.gate_timeout = store_uuid, hook, clock, gate_timeout
        self.observe = observe or (lambda event: None)
        self.held = {}

    def authority(self):
        return BT.Authority(self.store, self.conn, self.inbox(), domain=self.domain, repository=self.repository,
                            signer=self.signer, sign=self.sign, command_sign=self.command_sign,
                            generation=self.generation, store_uuid=self.store_uuid, clock=self.clock)

    def requests(self):
        return [{'id': i, 'data': json.loads(t)} for i, t in self.conn.execute(
            'SELECT id, data FROM entities WHERE kind=? ORDER BY id', (REQUEST_KIND,))
            if json.loads(t).get('repository') == self.repository]

    def _batch(self, request):
        if self.identity is None:
            # VELDO-0142: a batch commits only under the repository's own identity record.
            raise BT.Refused('missing_authority:repository_identity')
        record = _row(self.conn, 'project:' + request['project'])
        destination = BT._organ('control_project').landing_destination((record or {}).get('data') or {})
        return BT.Batch(self.land['repository'], project=request['project'], identity=self.identity,
                        authority=self.authority(), trunk=self.land['trunk'], remote=self.land['remote'],
                        destination=destination, hook=self.hook, push_identity=self.push_identity,
                        installation=self.land.get('installation'), workspace_root=self.land.get('workspace_root'),
                        observe=self.observe, clock=self.clock, gate_timeout=self.gate_timeout)

    def _end(self, rid, request, batch, state, refusal=None):
        record = batch.snapshot() if batch is not None else {}
        data = dict(request, state=state, refusal=refusal, batch=(record or {}).get('id'),
                    tip=(record or {}).get('tip'), watermark=(record or {}).get('watermark'),
                    left_out=(record or {}).get('left_out'), inventory=(record or {}).get('inventory'),
                    receipts=[r['unit'] for r in (record or {}).get('receipts') or []], updated_at=self.clock())
        _upsert(self.store, self.conn, self.signer, self.sign, self.generation, rid, REQUEST_KIND, data)
        return {'batch_request': rid, 'project': request['project'], 'state': state, 'refusal': refusal,
                'batch': data['batch']}

    def pass_once(self):
        """Every open request of this repository moved one step. Returns what each did."""
        done = []
        for entry in self.requests():
            rid, request = entry['id'], entry['data']
            if request.get('state') not in OPEN:
                continue
            try:
                done.append(self._step(rid, request))
            except (BT.Refused, self.store.StoreRefused) as error:
                code = getattr(error, 'code', 'unknown_outcome')
                batch = self.held.pop(rid, None)
                done.append(self._end(rid, request, batch, 'refused', code))
                if batch is not None:
                    batch.discard()
        return done

    def _step(self, rid, request):
        batch = self.held.get(rid)
        if request['state'] == AWAITING and batch is None:
            # The process that assembled it is gone: the batch is assembled and gated again, and asked again.
            request = dict(request, state=REQUESTED)
        if request['state'] == REQUESTED:
            batch = self._batch(request)
            outcome = BT.run(batch, request.get('units') or [])['outcome']
            if outcome == 'not_started':
                batch.discard()
                return {'batch_request': rid, 'project': request['project'], 'state': REQUESTED, 'refusal': None}
            if outcome != 'green':
                batch.discard()
                return self._end(rid, request, batch, outcome, (batch.record or {}).get('refusal'))
            self.held[rid] = batch
            return self._end(rid, request, batch, AWAITING)
        landed = batch.land()
        if landed.get('ok'):
            self.held.pop(rid, None)
            ended = self._end(rid, request, batch, 'landed')
            batch.discard()
            return ended
        if landed.get('outcome') == 'trunk_moved':
            again = batch.reland()
            if not again.get('ok'):
                self.held.pop(rid, None)
                state = (batch.record or {}).get('state') or 'refused'
                ended = self._end(rid, request, batch, state, (batch.record or {}).get('refusal'))
                batch.discard()
                return ended
            return self._end(rid, request, batch, AWAITING)
        if landed.get('refusal') == BT.STOPPED:
            self.held.pop(rid, None)
            ended = self._end(rid, request, batch, 'stopped', BT.STOPPED)
            batch.discard()
            return ended
        if landed.get('refusal') in (BT.MISSING_APPROVAL, BT.STALE):
            return self._end(rid, request, batch, AWAITING, landed['refusal'])
        return self._end(rid, request, batch, AWAITING, landed.get('refusal'))
