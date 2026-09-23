"""The assignment inbox for person-required work (VELDO-0064, PLAN-0019 W49, design R18).

WHAT THIS MODULE IS. The one authoritative inbox of assignments that need a person's action,
kept as `assignment` entities in the control store and read back through one index, one brief
reader and one admission check. Every change is a signed command applied through `Inbox.apply`:
the signature is verified against the signer's active key in the store's committed keyring, the
stored membership decides whether that principal may act, and one registered store transaction
commits the change together with the versions of every authority input it read. Only the store
writes. Telegram and the later authenticated UI/API are projections of this inbox; they read it,
they never become a second record.

WAITING HOLDS NOTHING. Opening a person assignment stops its requester. The unit the assignment
blocks is derived from the requester's own claim in this repository, never from a field the
requester writes: a requester holding one claim names its generation and the SAME transaction
parks that claim
through the claim organ's own `park` transition (a release that records the assignment the unit
waits for), and the reply tells the requester to exit. The answer arrives later on its own, from
the owner, with no model process or claim lease waiting for it. A parked unit is not claimable:
the blocked work resumes only through `resume`, which takes the claim again through the claim
organ's `resume` transition in the same store transaction that binds the versions of every input
`admit` read, and only while `admit` admits. A requester holding several claims is refused, and
the transaction re-reads the requester's claims so none is taken between the read and the
commit. `waiting_resources` reports any claim still held on a pending assignment's unit.

VIEWS ARE NOT AUTHORITY. `index` and `brief` describe the current stored version and show an
invalid record as visibly invalid, never skipped and never presented as content. `admit` is the
only answer to "may the blocked work proceed": it requires a valid record in an answered state
whose current version was written by the owner's own answer command in the journal, and an owner
who is still an active person member covering the assignment's scope. A displayed status, an
assignee field or any other text on the record grants nothing.

INJECTED ORGANS. The store, membership, claim and entity-contract modules are passed in, so the
module loads from any path and shares the caller's store module instance with the claim organ.
Standard library only.

WHAT IT IS NOT. Not settlement or quorum (VELDO-0068), presentation receipts (VELDO-0065),
channel attribution (VELDO-0066), edge signing (VELDO-0067), deadline expiry sweeping, concurrent
reassignment or lost-acknowledgement recovery (Release 2). EXPIRED is displayed when present but
no Release 1 command produces it. SATISFIED is displayed as answered; admitting from it needs the
settlement receipt its later consumer defines, so it refuses here as missing evidence.
"""
import json
import math
import re
import sqlite3
import time
from datetime import datetime

SCHEMA = 'veldo.assignment/v1'
ENTITY_KIND = 'assignment'
OPERATION = 'assignment_operation'
OPERATIONS = ('open', 'revise', 'answer', 'decline', 'cancel', 'resume')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
# Enabled person-required assignment kinds and the assertion kind an answer to each carries
# (authority_contract.ASSERTION_KINDS).
KINDS = {'decision': 'decision_answer', 'review_disposition': 'review_disposition',
         'acknowledgement': 'acknowledgement'}
# Every lifecycle state of the R18 assignment schema maps to exactly one inbox category.
CATEGORIES = {'OFFERED': 'pending', 'ACCEPTED': 'pending', 'IN_PROGRESS': 'pending',
              'SUBMITTED': 'answered', 'SATISFIED': 'answered', 'DECLINED': 'declined',
              'CANCELED': 'canceled', 'EXPIRED': 'expired'}
# The categories Release 1 commands produce. Expiry is shown when present, never produced here.
ENABLED_CATEGORIES = ('pending', 'answered', 'declined', 'canceled')
PENDING = tuple(s for s, c in CATEGORIES.items() if c == 'pending')
ANSWERED = tuple(s for s, c in CATEGORIES.items() if c == 'answered')
# The declared R18 edges an owner's answer walks, with the predicates the answer establishes.
ANSWER_PATH = ('OFFERED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED')
ANSWER_EVIDENCE = {'actor_predicate_satisfied': True, 'work_started': True, 'artifact_submitted': True}
DEADLINE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
REFUSALS = ('invalid_input', 'not_authorized', 'missing_authority', 'stale_subject', 'not_owner',
            'unavailable_service', 'missing_evidence', 'invalid_record', 'not_answered', 'unknown_outcome')
_ALIAS = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _is_int(v, low):
    return type(v) is int and v >= low


def assignment_id(repository_uuid, alias):
    return 'assignment:%s:%s' % (repository_uuid, alias)


def deadline_problem(value):
    if not isinstance(value, str):
        return 'deadline must be a UTC time %s' % DEADLINE_FORMAT
    try:
        datetime.strptime(value, DEADLINE_FORMAT)
    except ValueError:
        return 'deadline must be a UTC time %s' % DEADLINE_FORMAT
    return None


def budget_problem(value):
    if not isinstance(value, dict) or not value:
        return 'budget must be a non-empty mapping of unit to a non-negative amount'
    for unit, amount in value.items():
        if (not _is_str(unit) or type(amount) not in (int, float) or not math.isfinite(amount)
                or amount < 0):
            return 'budget must be a non-empty mapping of unit to a non-negative amount'
    return None


def content_problems(content):
    """Problems of the accepted content an opener supplies or a revision changes."""
    problems = []
    if content.get('kind') not in KINDS:
        problems.append('kind must be one of %s' % ', '.join(sorted(KINDS)))
    if not _is_str(content.get('owner')):
        problems.append('owner must name the principal who must act')
    scope = content.get('scope')
    if not isinstance(scope, list) or not scope or not all(_is_str(s) for s in scope) or len(set(scope)) != len(scope):
        problems.append('scope must be a non-empty list of distinct scope names')
    for problem in (deadline_problem(content.get('deadline')), budget_problem(content.get('budget'))):
        if problem:
            problems.append(problem)
    if not _is_str(content.get('brief')):
        problems.append('brief must be non-empty text')
    choices = content.get('choices')
    if (not isinstance(choices, list) or not choices or not all(_is_str(c) for c in choices)
            or len(set(choices)) != len(choices)):
        problems.append('choices must be a non-empty list of distinct rulings')
    subject = content.get('subject')
    if not isinstance(subject, dict) or not all(_is_str(subject.get(k)) for k in ('kind', 'ref', 'digest')):
        problems.append('subject must carry kind, ref and digest')
    if content.get('unit_id') is not None and not _is_str(content.get('unit_id')):
        problems.append('unit_id, when present, names the execution unit the assignment blocks')
    return problems


def record_problems(data, states, repository_uuid):
    """Every structural problem of one stored assignment record, by name. Unknown extra fields
    are ignored here: they are text, and nothing reads authority from them."""
    if not isinstance(data, dict):
        return ['an assignment record is a mapping']
    problems = []
    if data.get('schema') != SCHEMA:
        problems.append('schema must be %s' % SCHEMA)
    if data.get('repository_uuid') != repository_uuid:
        problems.append('record belongs to another repository')
    if data.get('actor_kind') != 'person':
        problems.append('actor_kind must be person: the inbox holds person-required assignments')
    state = data.get('state')
    if state not in states:
        problems.append('state %r is not a state of the assignment schema' % (state,))
    if not _is_str(data.get('alias')) or not _ALIAS.match(data.get('alias')):
        problems.append('alias must be a short name')
    if not _is_str(data.get('requested_by')):
        problems.append('requested_by must name the requesting principal')
    if not _is_int(data.get('request_version'), 1):
        problems.append('request_version must be an integer >= 1')
    problems.extend(content_problems(data))
    answer = data.get('answer')
    if state in ANSWERED:
        if (not isinstance(answer, dict) or answer.get('principal') != data.get('owner')
                or answer.get('ruling') not in (data.get('choices') or [])
                or answer.get('request_version') != data.get('request_version')
                or not _is_str(answer.get('command_id'))):
            problems.append('an answered record carries the owner ruling, request version and command')
    elif answer is not None:
        problems.append('only an answered record carries an answer')
    disposition = data.get('disposition')
    if state in ('DECLINED', 'CANCELED'):
        if not isinstance(disposition, dict) or not _is_str(disposition.get('principal')) \
                or not _is_str(disposition.get('command_id')):
            problems.append('a declined or canceled record names who disposed of it and the command')
    elif disposition is not None:
        problems.append('only a declined or canceled record carries a disposition')
    return problems


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class Inbox:
    """One repository's inbox on the configured real store connection.

    `store`, `membership`, `claims` and `contract` are the control_store, control_membership,
    control_claim and entity_contract modules; pass the store module the claim organ uses.
    `sign(bytes) -> text` signs journal records as `journal_signer`. Observations record
    identity, accepted versions and outcome, never brief text, signatures or answers.
    """

    def __init__(self, store, membership, claims, contract, conn, coordinates, journal_signer, sign,
                 authority_generation=1, clock=time.time):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input', 'coordinates are domain, repository and store identities')
        if claims.S is not store:
            raise Refused('invalid_input', 'the claim organ must commit through this same store module')
        states = tuple(contract.LIFECYCLES['assignment']['states'])
        if set(states) != set(CATEGORIES):
            raise Refused('invalid_input', 'inbox categories do not cover the assignment schema')
        self.store, self.membership, self.claims, self.contract = store, membership, claims, contract
        self.AC = membership.AC
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation, self.clock = authority_generation, clock
        self.states = states
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction,
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}

    # -- commands --------------------------------------------------------------------------

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = dict(self.ids, operation=command.get('operation'), assignment_id=None,
                           command_id=command.get('command_id'), accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except (Refused, self.store.StoreRefused) as exc:
            result = {'ok': False, 'reason': exc.code}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service'}
        observation.update(outcome='accepted' if result['ok'] else 'refused', reason=result['reason'])
        self.counts[observation['outcome']] += 1
        self.observations.append(observation)
        return result

    def _active(self, state, principal, now, types, scope):
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            raise Refused('not_authorized', why or 'no membership')
        if entry['principal_type'] not in types:
            raise Refused('not_authorized', 'principal type may not act here')
        if not self.membership.scope_covers(entry.get('scope'), scope):
            raise Refused('not_authorized', 'membership scope does not cover the assignment')
        return entry

    def _apply(self, packet, command, observation):
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii()):
            raise Refused('invalid_input', 'command must be a mapping and signature ASCII text')
        required = {'operation', 'alias', 'principal', 'command_id', 'nonce', *COORDINATES}
        if (not required <= command.keys() or command['operation'] not in OPERATIONS
                or not all(_is_str(command[k]) for k in ('principal', 'command_id', 'nonce', 'alias'))
                or not _ALIAS.match(command['alias'])
                or any(command[k] != v for k, v in self.ids.items())):
            raise Refused('invalid_input', 'invalid inbox command or authority coordinates')
        op, principal = command['operation'], command['principal']
        aid = assignment_id(self.ids['repository_uuid'], command['alias'])
        observation['assignment_id'] = aid
        state = self.membership.authority_state(self.store, self.conn)
        now = self.clock()
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key:
            raise Refused('not_authorized', 'no active verification key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                self.AC.allowed_signers_line(principal, key['public_key']),
                                                principal)
        if not verified:
            raise Refused('not_authorized', 'command signature did not verify')
        entities = state['entities']
        current = entities.get(aid)
        touched = {aid, principal, key['key_id'], self.membership.VERSIONS_ENTITY}
        params = dict(action=op, assignment_id=aid, principal=principal, command_id=command['command_id'])
        released = None
        if op == 'open':
            if current is not None:
                raise Refused('invalid_input', 'an assignment with this alias exists')
            content = command.get('assignment')
            if not isinstance(content, dict) or content_problems(content):
                raise Refused('invalid_input', '; '.join(content_problems(content)) if isinstance(content, dict)
                              else 'open carries the assignment content')
            self._active(state, principal, now, self.AC.BOUNDARIES['proposal_commit'], content['scope'])
            self._active(state, content['owner'], now, ('person',), content['scope'])
            touched.add(content['owner'])
            params['content'] = {k: content.get(k) for k in
                                 ('kind', 'owner', 'scope', 'deadline', 'budget', 'brief', 'choices', 'subject', 'unit_id')}
            params['alias'] = command['alias']
            held = self._held_claims(entities, principal)
            if len(held) > 1:
                raise Refused('invalid_input', 'a requester that stops for a person holds at most one claim here')
            unit = held[0][1].get('unit_id') if held else None
            if content.get('unit_id') is not None and content['unit_id'] != unit:
                raise Refused('not_owner', 'the blocked unit is the requester\'s own claim')
            params['content']['unit_id'] = unit
            params['held_claims'] = [cid for cid, _ in held]
            if unit is not None:
                released = self._claim_to_park(entities, unit, principal, command.get('claim_generation'), params, aid)
                touched.update(params.pop('claim_inputs'))
        else:
            if current is None or current['kind'] != ENTITY_KIND:
                raise Refused('missing_authority', 'no such assignment')
            data = current['data']
            if record_problems(data, self.states, self.ids['repository_uuid']):
                raise Refused('invalid_record', 'the stored assignment is invalid')
            if command.get('request_version') != data['request_version']:
                raise Refused('stale_subject', 'command names another request version')
            params['request_version'] = data['request_version']
            if op in ('answer', 'decline'):
                self._active(state, principal, now, ('person',), data['scope'])
                params['ruling'] = command.get('ruling')
            elif op == 'resume':
                touched.update(self._resume(state, entities, current, principal, now, command, params))
            else:
                entry = self._active(state, principal, now, self.AC.BOUNDARIES['proposal_commit'], data['scope'])
                params['project_owner'] = 'project_owner' in (entry.get('roles') or [])
                if principal != data['requested_by'] and not params['project_owner']:
                    raise Refused('not_authorized', 'only the requester or a project owner disposes of a request')
                if op == 'revise':
                    changes = command.get('changes')
                    allowed = {'deadline', 'budget', 'brief', 'choices', 'subject'}
                    if not isinstance(changes, dict) or not changes or not set(changes) <= allowed:
                        raise Refused('invalid_input', 'revise changes deadline, budget, brief, choices or subject')
                    params['changes'] = changes
            touched.add(data['owner'])
        versions = {eid: entities.get(eid, {}).get('version', 0) for eid in touched}
        observation['accepted_versions'] = versions
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION,
                      parameters=params, expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        record = self.store.materialized_state(self.conn)['entities'][aid]['data']
        return {'ok': True, 'reason': op, 'assignment_id': aid, 'assignment': record, 'receipt': receipt,
                'released_claim': released, 'stop_requester': op == 'open'}

    def _held_claims(self, entities, principal):
        """The (claim id, data) of every claim `principal` holds in this repository."""
        prefix = self.claims.claim_id(self.ids['repository_uuid'], '')
        return [(eid, e['data']) for eid, e in sorted(entities.items())
                if e.get('kind') == 'claim' and eid.startswith(prefix) and isinstance(e.get('data'), dict)
                and e['data'].get('state') != 'released' and e['data'].get('holder') == principal
                and e['data'].get('repository_uuid') == self.ids['repository_uuid']]

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: an opener's claims are re-read, so the derived
        unit is the requester's claim at commit, then the registered transition runs."""
        if params['action'] == 'open':
            rows = conn.execute('SELECT id, kind, version, data FROM entities WHERE kind=?', ('claim',)).fetchall()
            entities = {r[0]: {'kind': r[1], 'version': r[2], 'data': json.loads(r[3])} for r in rows}
            if [cid for cid, _ in self._held_claims(entities, params['principal'])] != params['held_claims']:
                raise self.store.StoreRefused('stale_subject', 'the requester\'s claims changed while the request was opened')
        return self._transition(params, before)

    def _claim_to_park(self, entities, unit, principal, generation, params, aid):
        cid = self.claims.claim_id(self.ids['repository_uuid'], unit)
        claim = entities.get(cid, {}).get('data')
        u = entities.get(unit, {})
        if u.get('kind') != 'execution_unit' or u['data'].get('repository_uuid') != self.ids['repository_uuid']:
            raise Refused('invalid_input', 'unit_id must name an execution unit of this repository')
        backlog = u['data'].get('backlog_item_uuid')
        params['claim_inputs'] = [x for x in (unit, backlog, cid) if _is_str(x)]
        if not claim or claim.get('state') == 'released':
            return None
        if claim.get('holder') != principal:
            raise Refused('not_owner', 'the claim on this unit is held by another principal')
        if type(generation) is not int:
            raise Refused('invalid_input', 'releasing a claim names its generation')
        params['release'] = dict(action='park', unit_id=unit, backlog_item_uuid=backlog, claim_id=cid,
                                 holder=principal, generation=generation, capabilities=[],
                                 repository_uuid=self.ids['repository_uuid'], parked_on=aid)
        return cid

    def _resume(self, state, entities, current, principal, now, command, params):
        """The inputs a resume binds: the claim principal's eligibility, every input admission
        read, and the parked claim, unit and backlog. Admission is decided here and its inputs
        are pinned by version, so the transaction commits only against what was admitted."""
        repository = self.ids['repository_uuid']
        self._active(state, principal, now, self.AC.BOUNDARIES['claim'], repository)
        capabilities = command.get('capabilities', [])
        if not isinstance(capabilities, list) or not all(isinstance(c, str) for c in capabilities):
            raise Refused('invalid_input', 'capabilities is a list of names')
        item = self.read(params['assignment_id'])
        if item is None or item['version'] != current['version']:
            raise Refused('stale_subject', 'the assignment changed while it was read')
        reason, inputs = self._admission(item)
        if reason != 'admitted':
            raise Refused(reason, 'the assignment does not admit the blocked work')
        unit = item['data'].get('unit_id')
        u = entities.get(unit, {}) if unit else {}
        backlog = u.get('data', {}).get('backlog_item_uuid')
        if (u.get('kind') != 'execution_unit' or u['data'].get('repository_uuid') != repository
                or entities.get(backlog, {}).get('kind') != 'backlog_item'):
            raise Refused('invalid_input', 'the assignment blocks no execution unit of this repository')
        cid = self.claims.claim_id(repository, unit)
        params['resume'] = dict(action='resume', unit_id=unit, backlog_item_uuid=backlog, claim_id=cid,
                                holder=principal, generation=0, capabilities=capabilities,
                                repository_uuid=repository, parked_on=params['assignment_id'])
        return set(inputs) | {unit, backlog, cid}

    def _transition(self, params, before):
        """The registered transaction: re-checks every precondition against the versions the
        store holds inside the transaction, walks declared R18 edges, and commits the claim
        release with the assignment it parks."""
        refused = self.store.StoreRefused
        aid, op, principal = params['assignment_id'], params['action'], params['principal']
        if op == 'open':
            if aid in before:
                raise refused('invalid_input', 'assignment exists')
            content = params['content']
            data = dict(content, schema=SCHEMA, alias=params['alias'], actor_kind='person', state='OFFERED',
                        requested_by=principal, request_version=1, answer=None, disposition=None,
                        domain_uuid=self.ids['domain_uuid'], repository_uuid=self.ids['repository_uuid'])
            changes = {aid: {'kind': ENTITY_KIND, 'data': data}}
            if 'release' in params:
                changes.update(self.claims.transition(params['release'], before))
            return changes
        data = dict(before[aid]['data'])
        if op == 'resume':
            if data['request_version'] != params['request_version'] or data['state'] != 'SUBMITTED':
                raise refused('stale_subject', 'the assignment no longer admits at this request version')
            return self.claims.transition(params['resume'], before)
        if data['request_version'] != params['request_version'] or data['state'] not in PENDING:
            raise refused('stale_subject', 'the assignment is no longer pending at this request version')
        if op == 'answer':
            if principal != data['owner'] or params['ruling'] not in data['choices']:
                raise refused('not_authorized', 'only the owner answers, with an offered ruling')
            for source, destination in zip(ANSWER_PATH, ANSWER_PATH[1:]):
                if ANSWER_PATH.index(source) < ANSWER_PATH.index(data['state']):
                    continue
                ok, why = self.contract.transition('assignment', source, destination, ANSWER_EVIDENCE)
                if not ok:
                    raise refused('transition_refused', why)
            data.update(state='SUBMITTED', answer=dict(principal=principal, ruling=params['ruling'],
                                                       request_version=data['request_version'],
                                                       command_id=params['command_id']))
        elif op == 'decline':
            if principal != data['owner']:
                raise refused('not_authorized', 'only the owner declines')
            ok, why = self.contract.transition('assignment', data['state'], 'DECLINED', {'actor_declined': True})
            if not ok:
                raise refused('transition_refused', why)
            data.update(state='DECLINED', disposition=dict(principal=principal, command_id=params['command_id']))
        elif principal != data['requested_by'] and not params['project_owner']:
            raise refused('not_authorized', 'only the requester or a project owner disposes of a request')
        elif op == 'cancel':
            ok, why = self.contract.transition('assignment', data['state'], 'CANCELED', {'disposition_recorded': True})
            if not ok:
                raise refused('transition_refused', why)
            data.update(state='CANCELED', disposition=dict(principal=principal, command_id=params['command_id']))
        else:
            revised = dict(data, **params['changes'])
            if content_problems(revised):
                raise refused('invalid_input', '; '.join(content_problems(revised)))
            data = dict(revised, request_version=data['request_version'] + 1)
        return {aid: {'kind': ENTITY_KIND, 'data': data}}

    # -- readers ---------------------------------------------------------------------------

    def _rows(self, conn, where, args):
        conn = conn or self.conn
        started = not conn.in_transaction
        if started:
            conn.execute('BEGIN')
        try:
            rows = conn.execute('SELECT id, kind, version, digest, data FROM entities WHERE ' + where + ' ORDER BY id',
                                args).fetchall()
            seq = conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        finally:
            if started:
                conn.execute('COMMIT')
        return rows, seq

    def _item(self, row):
        identity, kind, version, digest, text = row
        problems = []
        try:
            raw = json.loads(text)
        except ValueError:
            raw = None
            problems.append('stored data is not readable')
        if raw is not None and self.store.digest_of({'kind': kind, 'data': raw, 'version': version}) != digest:
            problems.append('stored data does not match its committed digest')
        if kind != ENTITY_KIND:
            problems.append('entity is not an assignment')
        if raw is not None:
            problems.extend(record_problems(raw, self.states, self.ids['repository_uuid']))
        if raw is not None and isinstance(raw, dict) and _is_str(raw.get('alias')) \
                and identity != assignment_id(self.ids['repository_uuid'], raw['alias']):
            problems.append('entity id does not match the record alias')
        return {'id': identity, 'version': version, 'digest': digest, 'raw': raw if isinstance(raw, dict) else {},
                'problems': problems, 'data': None if problems else raw}

    def read(self, assignment, conn=None):
        rows, seq = self._rows(conn, 'id=?', (assignment,))
        if not rows:
            return None
        return dict(self._item(rows[0]), watermark=seq)

    def index(self, conn=None):
        """Every stored assignment at one watermark. Invalid records are listed as invalid."""
        # This repository's assignment ids whatever their kind, and assignment-kind entities
        # whose id is not an assignment id at all; another repository's inbox is not listed.
        prefix = assignment_id(self.ids['repository_uuid'], '')
        rows, seq = self._rows(conn, "substr(id, 1, ?) = ? OR (kind = ? AND substr(id, 1, 11) != 'assignment:')",
                               (len(prefix), prefix, ENTITY_KIND))
        entries = []
        for row in rows:
            item = self._item(row)
            entry = {'id': item['id'], 'version': item['version'], 'valid': not item['problems'],
                     'problems': item['problems']}
            if item['problems']:
                entry['category'] = 'invalid'
            else:
                data = item['data']
                entry.update(category=CATEGORIES[data['state']], state=data['state'], kind=data['kind'],
                             owner=data['owner'], scope=list(data['scope']), deadline=data['deadline'],
                             budget=dict(data['budget']), request_version=data['request_version'],
                             unit_id=data.get('unit_id'), requested_by=data['requested_by'],
                             ruling=(data['answer'] or {}).get('ruling'),
                             brief_digest=self.store.digest_of(data['brief']))
            entries.append(entry)
        return {'schema': SCHEMA, 'watermark': seq, 'entries': entries}

    def brief(self, assignment, conn=None):
        """The current accepted content of one assignment, or its visible invalid state."""
        item = self.read(assignment, conn)
        if item is None:
            return {'id': assignment, 'valid': False, 'category': 'missing', 'problems': ['no such assignment']}
        if item['problems']:
            return {'id': item['id'], 'version': item['version'], 'valid': False, 'category': 'invalid',
                    'problems': item['problems'], 'watermark': item['watermark']}
        data = item['data']
        content = {k: data.get(k) for k in ('kind', 'state', 'owner', 'scope', 'deadline', 'budget', 'brief',
                                            'choices', 'subject', 'unit_id', 'requested_by', 'request_version')}
        return {'id': item['id'], 'version': item['version'], 'valid': True, 'category': CATEGORIES[data['state']],
                'content': content, 'watermark': item['watermark']}

    def _admission(self, item):
        """(reason, inputs): the admission answer and the entity ids it read, so a command that
        acts on the answer can bind their versions."""
        inputs = {item['id'], self.membership.VERSIONS_ENTITY}
        if item['problems']:
            return 'invalid_record', inputs
        data = item['data']
        if data['state'] not in ANSWERED:
            return 'not_answered', inputs
        if data['state'] != 'SUBMITTED':
            return 'missing_evidence', inputs
        state = self.membership.authority_state(self.store, self.conn)
        inputs.add(data['owner'])
        owner = self.AC.membership_entry(state['membership'], data['owner'])
        active, _ = self.AC.active_member(owner, self.clock())
        if not active or owner['principal_type'] != 'person' \
                or not self.membership.scope_covers(owner.get('scope'), data['scope']):
            return 'missing_authority', inputs
        row = self.conn.execute('SELECT principal, transition FROM journal WHERE command_id=?',
                                (data['answer']['command_id'],)).fetchone()
        written = json.loads(row[1]).get(item['id'], {}) if row else {}
        if row is None or row[0] != data['owner'] or written.get('version') != item['version'] \
                or written.get('digest') != item['digest']:
            return 'missing_authority', inputs
        return 'admitted', inputs

    def admit(self, assignment):
        """Whether the work this assignment blocks may proceed, from current authority only."""
        item = self.read(assignment)
        if item is None:
            reason = 'missing_authority'
            item = {'id': assignment, 'version': 0}
        else:
            reason = self._admission(item)[0]
        admitted = reason == 'admitted'
        self.counts['accepted' if admitted else 'refused'] += 1
        self.observations.append(dict(self.ids, operation='admit', assignment_id=assignment,
                                      accepted_versions={assignment: item['version']},
                                      outcome='accepted' if admitted else 'refused', reason=reason))
        return {'admitted': admitted, 'reason': reason, 'assignment_id': assignment, 'version': item['version']}

    def waiting_resources(self):
        """Claims still held on units that pending person assignments block. Empty is correct.
        The blocked unit is the requester's claim at open, so this is every claim a stopped
        requester gave up for a pending assignment and still holds."""
        held = []
        entities = self.store.materialized_state(self.conn)['entities']
        for entry in self.index()['entries']:
            if entry['category'] != 'pending' or not entry.get('unit_id'):
                continue
            cid = self.claims.claim_id(self.ids['repository_uuid'], entry['unit_id'])
            claim = entities.get(cid, {}).get('data')
            if claim and claim.get('state') != 'released':
                held.append({'assignment_id': entry['id'], 'claim_id': cid, 'holder': claim.get('holder')})
        return held

    def metrics(self):
        pending = sum(1 for e in self.index()['entries'] if e['category'] == 'pending')
        return dict(self.counts, pending=pending)
