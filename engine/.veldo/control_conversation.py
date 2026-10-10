"""Durable conversations and ordered turns beside project work (VELDO-0174).

A conversation is authority data, not a project.  It has no repository, backlog,
charter or trunk.  Owner commands create and close its versioned record and append
turns.  The installed service changes a waiting turn to dispatched only after a
VELDO-0039 conversation dispatch has been prepared.  The receiver then rechecks the
same record before accepting the launch.

Conversation worker reservations use the shared subscription-account records and
the same account-pool selection order.  Their context names the conversation as the
unit and deliberately carries no project or repository.  They are visible to the
ordinary pool's active-run count, but do not invent project or unit usage policies.
"""
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('conversation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _organ('control_store')
CM = _organ('control_membership')
AC = CM.AC
POOL = _organ('control_account_pool')
RES = _organ('control_reservations')
CFG = _organ('control_agent_config')

SCHEMA = 'veldo.conversation/v1'
TURN_SCHEMA = 'veldo.conversation_turn/v1'
OPERATION = 'conversation_command'
RESERVATION_OPERATION = 'conversation_reservation'
KIND = 'conversation'
TURN_KIND = 'conversation_turn'
OPEN = 'open_conversation'
CLOSE = 'close_conversation'
MESSAGE = 'send_conversation_message'
DISPATCH = 'dispatch_conversation_turn'
END = 'end_conversation_turn'
OPERATIONS = (OPEN, CLOSE, MESSAGE, DISPATCH, END)
STATUSES = ('open', 'closed')
TURN_STATES = ('waiting', 'dispatched', 'ended')
DEFAULT_ROLE = 'assistant'
HEAD = 'default-team:head'
DEFAULT_PREFIX = 'default-team:'
WORKER_KIND = 'subscription_reservation'


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def conversation_id(identity):
    return 'conversation:' + str(identity)


def turn_id(identity, sequence):
    return 'conversation-turn:%s:%d' % (identity, sequence)


def _row(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def _member(conn, principal, now, *, owner=False, service=False):
    row = _row(conn, principal) if _text(principal) else None
    entry = dict((row or {}).get('data') or {}, principal=principal)
    active, why = AC.active_member(entry if row and row['kind'] == 'membership' else None, now)
    if not active:
        raise Refused('missing_authority:conversation_owner' if owner else 'missing_authority:conversation_service',
                      why or 'inactive member')
    if owner and (entry.get('principal_type') != 'person' or 'project_owner' not in (entry.get('roles') or [])):
        raise Refused('missing_authority:conversation_owner')
    if service and (entry.get('principal_type') != 'service'
                    or 'reservation_service' not in (entry.get('roles') or [])):
        raise Refused('missing_authority:conversation_service')
    return entry


def _conversation(conn, identity):
    row = _row(conn, conversation_id(identity))
    return row if row and row['kind'] == KIND else None


def _turn(conn, identity, sequence):
    row = _row(conn, turn_id(identity, sequence))
    return row if row and row['kind'] == TURN_KIND else None


def default_team(conn):
    head = _row(conn, HEAD)
    revision = ((head or {}).get('data') or {}).get('revision')
    row = _row(conn, DEFAULT_PREFIX + str(revision)) if type(revision) is int else None
    if not row or row['kind'] != 'default_team_revision':
        raise Refused('missing_evidence:default_team')
    return row['data']


def role_at(conn, name):
    """The named role of the current accepted default team and its immutable capability revision."""
    saved = default_team(conn)
    role = (((saved.get('team') or {}).get('roles') or {}).get(name))
    if not isinstance(role, dict):
        raise Refused('invalid_input:conversation_role:' + str(name))
    reference = role.get('capability_configuration')
    if (not isinstance(reference, dict) or set(reference) != {'role', 'revision'}
            or reference.get('role') != name or type(reference.get('revision')) is not int):
        raise Refused('missing_evidence:conversation_role:' + str(name))
    candidates = []
    for (data,) in conn.execute('SELECT data FROM entities WHERE kind=?', (CFG.KINDS[0],)):
        value = json.loads(data)
        if value.get('role') == name and value.get('revision') == reference['revision']:
            candidates.append(value)
    if len(candidates) != 1:
        raise Refused('missing_evidence:conversation_role:' + str(name))
    revision = candidates[0]
    if CFG.digest({k: v for k, v in revision.items() if k != 'digest'}) != revision.get('digest'):
        raise Refused('missing_evidence:agent_digest')
    return copy.deepcopy(role), copy.deepcopy(revision), saved['revision']


def transition(conn, params, before):
    operation, now = params.get('operation'), params.get('now')
    identity, principal = params.get('conversation'), params.get('principal')
    if operation not in OPERATIONS or not _text(identity) or not _number(now):
        raise Refused('invalid_input:conversation')
    cid = conversation_id(identity)
    current = before.get(cid)
    record = copy.deepcopy((current or {}).get('data') or {})
    if operation == OPEN:
        _member(conn, principal, now, owner=True)
        if current is not None:
            raise Refused('stale_subject:conversation_exists')
        role = params.get('role') or DEFAULT_ROLE
        role_at(conn, role)
        directory = params.get('directory')
        if not _text(directory) or not os.path.isabs(directory):
            raise Refused('invalid_input:conversation_directory')
        data = {'schema': SCHEMA, 'id': identity, 'domain': params.get('domain'), 'owner': principal,
                'role': role, 'status': 'open', 'version': 1, 'intake_digest': params.get('intake_digest'),
                'directory': directory, 'opened_at': now, 'closed_at': None}
        if not _text(data['domain']) or not _text(data['intake_digest']):
            raise Refused('invalid_input:conversation')
        return {cid: {'kind': KIND, 'data': data}}
    if not current or current.get('kind') != KIND:
        raise Refused('invalid_input:conversation:unknown')
    if operation in (CLOSE, MESSAGE):
        _member(conn, principal, now, owner=True)
        if record.get('owner') != principal:
            raise Refused('missing_authority:conversation_owner')
    else:
        _member(conn, principal, now, service=True)
    if operation == CLOSE:
        if params.get('version') != record.get('version'):
            raise Refused('stale_version')
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        record.update(status='closed', version=record['version'] + 1, closed_at=now)
        return {cid: {'kind': KIND, 'data': record}}
    if operation == MESSAGE:
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        intake = params.get('intake_command')
        digest = params.get('intake_digest')
        if not _text(intake) or not _text(digest):
            raise Refused('invalid_input:conversation_message')
        sequences = [value.get('sequence', 0) for (raw,) in conn.execute(
            'SELECT data FROM entities WHERE kind=?', (TURN_KIND,))
            if (value := json.loads(raw)).get('conversation') == identity]
        sequence = max(sequences, default=0) + 1
        tid = turn_id(identity, sequence)
        if tid in before or _row(conn, tid):
            raise Refused('stale_subject:conversation_turn')
        journal_seq = conn.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM journal').fetchone()[0]
        turn = {'schema': TURN_SCHEMA, 'conversation': identity, 'sequence': sequence,
                'intake_command': intake, 'intake_digest': digest, 'state': 'waiting', 'created_at': now,
                'arrival': journal_seq, 'dispatch_id': None, 'role_revision': None, 'account': None,
                'receiver': None, 'outcome': None, 'ended_at': None}
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    sequence = params.get('sequence')
    if type(sequence) is not int or sequence < 1:
        raise Refused('invalid_input:conversation_turn')
    tid = turn_id(identity, sequence)
    current_turn = before.get(tid)
    turn = copy.deepcopy((current_turn or {}).get('data') or {})
    if not current_turn or current_turn.get('kind') != TURN_KIND:
        raise Refused('invalid_input:conversation_turn:unknown')
    if operation == DISPATCH:
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        if turn.get('state') != 'waiting':
            raise Refused('stale_subject:conversation_turn_active')
        active = conn.execute("SELECT data FROM entities WHERE kind=?", (TURN_KIND,)).fetchall()
        if any((value := json.loads(r[0])).get('conversation') == identity
               and value.get('state') == 'dispatched' for r in active):
            raise Refused('stale_subject:conversation_turn_active')
        dispatch_id = params.get('dispatch_id')
        role_revision = params.get('role_revision')
        if not _text(dispatch_id) or type(role_revision) is not int or role_revision < 1:
            raise Refused('invalid_input:conversation_dispatch')
        turn.update(state='dispatched', dispatch_id=dispatch_id, role_revision=role_revision,
                    account=params.get('account'), receiver=params.get('receiver'), dispatched_at=now)
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    if turn.get('state') != 'dispatched' or turn.get('dispatch_id') != params.get('dispatch_id'):
        raise Refused('stale_subject:conversation_turn')
    outcome = params.get('outcome')
    if not _text(outcome):
        raise Refused('invalid_input:conversation_outcome')
    turn.update(state='ended', outcome=outcome, ended_at=now)
    return {tid: {'kind': TURN_KIND, 'data': turn}}


def reservation_transition(conn, params, before):
    """Reserve or retire a conversation's account slot in the shared worker-record set."""
    action, now = params.get('action'), params.get('now')
    target = params.get('target')
    if action not in ('reserve', 'retire') or not _number(now) or not _text(target):
        raise Refused('invalid_input:conversation_reservation')
    current = before.get(target)
    if action == 'retire':
        if not current or current.get('kind') != WORKER_KIND or current['data'].get('subject_kind') != KIND:
            raise Refused('missing_reservation')
        value = copy.deepcopy(current['data'])
        if value.get('retired'):
            return {}
        value.update(retired=True, retirement={'outcome': params.get('outcome'), 'at': now})
        return {target: {'kind': WORKER_KIND, 'data': value}}
    if current is not None:
        raise Refused('duplicate_dispatch')
    records = {key: json.loads(data) for key, data in conn.execute(
        'SELECT id, data FROM entities WHERE kind=?', (WORKER_KIND,))}
    request = params.get('request')
    choice = POOL.choose(conn, records, request, now, lambda _account: None)
    if choice['account'] is None:
        error = Refused(POOL.refusal(choice))
        error.passed = choice['passed']
        raise error
    value = {'type': 'worker', 'dispatch': params['dispatch'], 'subject_kind': KIND,
             'context': {'domain': params['domain'], 'repository': None, 'account': choice['account'],
                         'project': None, 'unit': params['conversation']},
             'retired': False, 'selection': choice['trace'],
             'reserved_seq': conn.execute('SELECT COALESCE(MAX(seq),0)+1 FROM journal').fetchone()[0]}
    return {target: {'kind': WORKER_KIND, 'data': value}}


class Conversations:
    def __init__(self, store, conn, *, domain, principal, signer, sign, state_root, generation=1, observe=None):
        self.store, self.conn, self.domain, self.principal = store, conn, domain, principal
        self.signer, self.sign, self.state_root, self.generation = signer, sign, os.path.abspath(str(state_root)), generation
        self.observe = observe or (lambda event: None)
        conn.command_registry[OPERATION] = {'transaction_transition': transition,
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}

    def read(self, identity):
        row = _conversation(self.conn, identity)
        return copy.deepcopy(row['data']) if row else None

    def turns(self, identity):
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,)):
            value = json.loads(data)
            if value.get('conversation') == identity:
                found.append(value)
        return sorted(found, key=lambda value: value['sequence'])

    def waiting(self):
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,)):
            value = json.loads(data)
            conversation = self.read(value.get('conversation'))
            if value.get('state') == 'waiting' and conversation and conversation.get('status') == 'open':
                found.append(value)
        return sorted(found, key=lambda value: (value.get('arrival', 0), value['conversation'], value['sequence']))

    def _run(self, operation, identity, fields, *, principal=None, now=None):
        principal, now = principal or self.principal, time.time() if now is None else now
        cid = conversation_id(identity)
        ids = [cid]
        if operation == MESSAGE:
            ids.append(turn_id(identity, len(self.turns(identity)) + 1))
        if type(fields.get('sequence')) is int:
            ids.append(turn_id(identity, fields['sequence']))
        expected = {}
        for item in ids:
            row = _row(self.conn, item)
            expected[item] = row['version'] if row else 0
        params = dict(fields, operation=operation, conversation=identity, domain=self.domain,
                      principal=principal, now=now)
        command_id = fields.get('command_id') or ('conversation/%s/%s/%s' % (
            operation, identity, S.digest_of(params).split(':', 1)[-1][:24]))
        command = {'command_id': command_id, 'principal': principal, 'operation': OPERATION,
                   'parameters': params, 'expected_versions': expected, 'artifact_digests': [],
                   'nonce': 'conversation/' + command_id}
        event = {'schema': SCHEMA, 'operation': operation, 'conversation': identity, 'principal': principal,
                 'read_version': expected.get(cid), 'command_id': command_id}
        try:
            receipt = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            code = error.code
            self.observe(dict(event, outcome='refused', refusal=code))
            if isinstance(error, Refused):
                raise
            raise Refused(code, getattr(error, 'detail', '')) from None
        record = self.read(identity)
        self.observe(dict(event, outcome='accepted', written_version=(record or {}).get('version'),
                          watermark=receipt['seq']))
        return record, receipt

    def open(self, identity, *, owner, role=DEFAULT_ROLE, intake_digest, command_id=None, now=None):
        safe = hashlib.sha256(identity.encode()).hexdigest()
        directory = os.path.join(self.state_root, 'conversations', safe)
        record, _receipt = self._run(OPEN, identity, {'role': role, 'intake_digest': intake_digest,
            'directory': directory, 'command_id': command_id}, principal=owner, now=now)
        return record

    def close(self, identity, version, *, owner, command_id=None, now=None):
        record, _receipt = self._run(CLOSE, identity, {'version': version, 'command_id': command_id},
                                     principal=owner, now=now)
        return record

    def message(self, identity, intake_command, intake_digest, *, owner, command_id=None, now=None):
        before = len(self.turns(identity))
        self._run(MESSAGE, identity, {'intake_command': intake_command, 'intake_digest': intake_digest,
                                      'command_id': command_id}, principal=owner, now=now)
        return self.turns(identity)[before]

    def dispatched(self, identity, sequence, dispatch_id, role_revision, account, receiver, *, now=None):
        self._run(DISPATCH, identity, {'sequence': sequence, 'dispatch_id': dispatch_id,
                  'role_revision': role_revision, 'account': account, 'receiver': receiver}, now=now)
        return _turn(self.conn, identity, sequence)['data']

    def ended(self, identity, sequence, dispatch_id, outcome, *, now=None):
        self._run(END, identity, {'sequence': sequence, 'dispatch_id': dispatch_id, 'outcome': outcome}, now=now)
        return _turn(self.conn, identity, sequence)['data']

    def status(self):
        conversations = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            conversations.append(json.loads(data))
        turns = [json.loads(data) for (data,) in self.conn.execute(
            'SELECT data FROM entities WHERE kind=?', (TURN_KIND,))]
        outcomes = {}
        for turn in turns:
            if turn.get('outcome'):
                outcomes[turn['outcome']] = outcomes.get(turn['outcome'], 0) + 1
        return {'open': sum(c.get('status') == 'open' for c in conversations),
                'waiting': sum(t.get('state') == 'waiting' for t in turns), 'outcomes': outcomes}


class ConversationReservations:
    """The subset of the reservation interface a conversation Runner consumes."""
    def __init__(self, store, conn, *, domain, principal, signer, sign, generation=1, observe=None):
        self.store, self.conn, self.domain, self.principal = store, conn, domain, principal
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        conn.command_registry[RESERVATION_OPERATION] = {'transaction_transition': reservation_transition,
            'writes': ('entities', 'journal', 'commands', 'nonces')}

    def reserve(self, command_id, dispatch, conversation, request, *, now):
        target = RES.entity('worker', [self.domain, dispatch])
        params = {'action': 'reserve', 'target': target, 'dispatch': dispatch, 'conversation': conversation,
                  'request': request, 'domain': self.domain, 'now': now}
        self._run(command_id, target, params)
        return self.worker(dispatch)['context']['account']

    def retire_conversation(self, command_id, dispatch, outcome, *, now):
        target = RES.entity('worker', [self.domain, dispatch])
        params = {'action': 'retire', 'target': target, 'dispatch': dispatch, 'outcome': outcome,
                  'domain': self.domain, 'now': now}
        self._run(command_id, target, params)

    def _run(self, command_id, target, params):
        row = _row(self.conn, target)
        command = {'command_id': command_id, 'principal': self.principal, 'operation': RESERVATION_OPERATION,
                   'parameters': params, 'expected_versions': {target: row['version'] if row else 0},
                   'artifact_digests': [], 'nonce': 'conversation-reservation/' + command_id}
        try:
            return self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            if isinstance(error, Refused):
                raise
            raise Refused(error.code) from None

    def worker(self, dispatch):
        row = _row(self.conn, RES.entity('worker', [self.domain, dispatch]))
        return row['data'] if row and row['kind'] == WORKER_KIND else None


def receiver_check(conn, contract):
    """None when this prepared conversation turn may still launch, else its named refusal."""
    if contract.get('subject_kind') != KIND or contract.get('station') != 'turn':
        return 'binding_mismatch:conversation_receiver'
    subject = contract.get('unit')
    record = _conversation(conn, subject)
    if record is None:
        return 'invalid_input:conversation:unknown'
    if record['data'].get('status') != 'open':
        return 'stale_subject:conversation_closed'
    turn = _turn(conn, subject, (contract.get('source') or {}).get('turn'))
    if (turn is None or turn['data'].get('state') != 'dispatched'
            or turn['data'].get('dispatch_id') != contract.get('dispatch_id')):
        return 'stale_subject:conversation_turn_active'
    return None
