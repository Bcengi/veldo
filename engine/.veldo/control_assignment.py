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
commit. `waiting_resources` reports any claim still held on a pending assignment's unit, and
`parked_units` every parked unit with the assignment it waits for and why it is still parked,
listed (and counted in `metrics`) so it is never invisible.

WHAT BECOMES OF WORK THAT STOPPED (VELDO-0133). A unit whose assignment ends without admitting
the blocked work (declined, canceled, expired, or answered without admitting) is never parked for
good: Veldo asks what becomes of it. The question is an ordinary person assignment of kind
`disposition` in this same inbox, offering exactly `close`, `backlog` and `other`, naming the
source assignment, its request version and the blocked unit, so the index, brief, projection and
admission apply to it unchanged. It is addressed to the person who declined or canceled; when no
person ended the assignment (a cancel by an agent run or a service, an EXPIRED record, an answer
that no longer admits) it goes to the one project owner resolved from the unit's own ownership
chain (unit, backlog item, objective, project), and when that is not exactly one active person the
question is not opened and the refusal is `no_project_owner`: ownership is never guessed. A
decline or cancel opens it in its own store transaction; an EXPIRED record, an answer that no
longer admits, and work routed to intake (asked again) are opened by `ask`. A disposition
question can only be answered: declining, canceling or revising it is refused. The answer is the
addressee's own signed answer; `other` carries its non-empty instruction inside the signed command,
with the evidence of where the answer arrived: the id of the kept VELDO-0066 Telegram evidence, or the
request packet the API edge signed. `dispose`
applies an admitted answer, like `resume`, in one store transaction that binds every input
admission read: `close` walks the declared `disposition_recorded` edges of the unit and its backlog
item (the backlog item is left as it is while it owns other open units), `backlog` clears the park
through the claim organ's `unpark` so an ordinary claim succeeds, and `other` submits the signed
instruction verbatim through the VELDO-0126 intake's public attested submission, which authenticates
that evidence itself and requires it to be the answering person's own, and changes no
unit, backlog item, claim or priority; the unit stays parked as `routed_to_intake`. Each applied
disposition is one `assignment_disposition` record, so applying it again is refused (or, for
`other`, returns the same proposal). Nothing is inferred from the free text.

VIEWS ARE NOT AUTHORITY. `index` and `brief` describe the current stored version and show an
invalid record as visibly invalid, never skipped and never presented as content. `admit` is the
only answer to "may the blocked work proceed": it requires a valid record in an answered state
whose current version was written by the owner's own answer command in the journal, and an owner
who is still an active person member covering the assignment's scope. The record keeps the
owner's signed answer command and its signature; admission checks that the command answers
exactly this assignment, request version and ruling, and verifies the signature against the
owner's key as it stood when the answer was accepted (VELDO-0027's historical verification
rule): the key version the answer's own journal record pinned, read back from the journal. A
later rotation, retirement or in-place replacement of that key strands nothing; a revocation
dated at or before the acceptance refuses it. The journal's principal column is copied from
whatever command the store was given, so it identifies no one on its own. A displayed status, an
assignee field or any other text on the record grants nothing.

INJECTED ORGANS. The store, membership, claim and entity-contract modules are passed in, so the
module loads from any path and shares the caller's store module instance with the claim organ.
Standard library only.

WHAT IT IS NOT. Not settlement or quorum (VELDO-0068), presentation receipts (VELDO-0065),
channel attribution (VELDO-0066), edge signing (VELDO-0067), deadline expiry sweeping, concurrent
reassignment or lost-acknowledgement recovery (Release 2). EXPIRED is displayed when present but
no Release 1 command produces it. SATISFIED is displayed as answered; admitting from it needs the
settlement receipt its later consumer defines, so it refuses here as missing evidence. A request
whose subject is settlement terms (VELDO-0068) is answered only through the settlement service:
the `answer` command here refuses it as `settlement_required`, so it never reaches SUBMITTED
without its settlement, typed effect and receipt. A request without terms is answered here.
"""
import hashlib
import json
import math
import re
import sqlite3
import time
from datetime import datetime

SCHEMA = 'veldo.assignment/v1'
ENTITY_KIND = 'assignment'
OPERATION = 'assignment_operation'
OPERATIONS = ('open', 'revise', 'answer', 'decline', 'cancel', 'resume', 'ask', 'dispose')
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
# Why a parked unit is still parked. `ready_to_resume` has its way back (`resume`) and
# `awaiting_answer` waits for the owner. A unit parked for one of DISPOSITION_REASONS has no way
# back of its own, so a disposition question asks what becomes of it (VELDO-0133): the unit then
# reads `awaiting_disposition` while the question waits, `ready_to_dispose` once its answer admits,
# and `routed_to_intake` after `other`; `close` and `backlog` take it out of the listing. It reads
# under its original reason only while no question is open (`no_project_owner`).
PARKED_REASONS = ('awaiting_answer', 'ready_to_resume', 'answer_not_admitted', 'declined', 'canceled', 'expired',
                  'invalid_assignment', 'missing_assignment', 'awaiting_disposition', 'ready_to_dispose',
                  'routed_to_intake')
DISPOSITION_REASONS = ('answer_not_admitted', 'declined', 'canceled', 'expired')
# The reasons no Release 1 event hangs a question on, so `ask` opens it; `routed_to_intake` asks again.
ASKABLE_REASONS = ('answer_not_admitted', 'expired', 'routed_to_intake')
DISPOSITION_KIND = 'disposition'
DISPOSITION_CHOICES = ('close', 'backlog', 'other')
DISPOSITION_ALIAS_PREFIX = 'disposition-'
DISPOSITION_RECORD_KIND = 'assignment_disposition'
DISPOSITION_RECORD_SCHEMA = 'veldo.assignment_disposition/v1'
# Why the addressee of a disposition question was chosen.
ADDRESSED_AS = ('decliner', 'canceler', 'project_owner')
# Where an answer arrived: exactly VELDO-0126's two intake source kinds (control_intake.SOURCE_KINDS).
ARRIVAL_KINDS = ('telegram_message', 'api_request')
# An intake refusal of an `other` instruction, by the class of its code, as this inbox names it.
INTAKE_REFUSALS = {'unauthorized': 'not_authorized', 'unauthenticated': 'not_authorized',
                   'unavailable_service': 'unavailable_service', 'unknown_outcome': 'unknown_outcome',
                   'missing_evidence': 'missing_evidence', 'identity_conflict': 'stale_subject',
                   'stale_version': 'stale_subject'}
REFUSALS = ('invalid_input', 'not_authorized', 'missing_authority', 'stale_subject', 'not_owner',
            'unavailable_service', 'missing_evidence', 'invalid_record', 'not_answered', 'unknown_outcome',
            'settlement_required', 'no_project_owner')
# The subject kind of a request that carries settlement terms (VELDO-0068): only the settlement
# service answers it.
SETTLEMENT_SUBJECT_KIND = 'settlement_terms'
_ALIAS = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _is_int(v, low):
    return type(v) is int and v >= low


def assignment_id(repository_uuid, alias):
    return 'assignment:%s:%s' % (repository_uuid, alias)


def disposition_alias(source, request_version, round_):
    """The alias of the `round_`th disposition question about the work `source` blocked at
    `request_version`: derived, so two questions of one round cannot both be opened."""
    digest = hashlib.sha256(json.dumps([source, request_version, round_]).encode()).hexdigest()
    return DISPOSITION_ALIAS_PREFIX + digest[:24]


def disposition_record_id(question):
    return 'assignment-disposition:' + question


def arrival_problem(arrived):
    """Why `arrived_on` does not carry the evidence of one Telegram message or one authenticated API
    request: the id of kept VELDO-0066 evidence, or the {request, signature} packet the API edge
    signed. Only the shape is read here; the intake authenticates the evidence itself at dispose, and
    no chat, sender or request id the answer names counts."""
    if not isinstance(arrived, dict) or arrived.get('source_kind') not in ARRIVAL_KINDS:
        return 'arrived_on names a telegram_message or an api_request'
    if arrived['source_kind'] == 'telegram_message':
        evidence = arrived.get('evidence_id')
        if set(arrived) != {'source_kind', 'evidence_id'} or not _is_str(evidence) or not evidence.isascii() \
                or not evidence.isprintable() or len(evidence) > 128:
            return 'a Telegram arrival names its kept evidence'
        return None
    if set(arrived) != {'source_kind', 'request', 'signature'} or not isinstance(arrived['request'], dict) \
            or not _is_str(arrived['signature']):
        return 'an API arrival carries the request packet the API edge signed'
    return None


def disposition_answer_problem(command):
    """Why a signed answer to a disposition question does not carry what its ruling needs: `other`
    carries non-empty instruction text and where it arrived, inside the signed command itself."""
    if command.get('ruling') == 'other':
        text = command.get('instruction')
        if not isinstance(text, str) or not text.strip():
            return 'other carries a non-empty instruction inside the signed command'
        return arrival_problem(command.get('arrived_on'))
    if 'instruction' in command:
        return 'only other carries an instruction'
    return arrival_problem(command['arrived_on']) if 'arrived_on' in command else None


def disposition_problems(data):
    """The problems of a disposition question beyond those of every assignment record."""
    problems = []
    if list(data.get('choices') or []) != list(DISPOSITION_CHOICES):
        problems.append('a disposition question offers exactly close, backlog and other')
    of = data.get('disposition_of')
    if (not isinstance(of, dict) or not _is_str(of.get('assignment_id')) or not _is_int(of.get('request_version'), 1)
            or of.get('unit_id') != data.get('unit_id') or not _is_str(of.get('unit_id'))
            or of.get('ended_as') not in DISPOSITION_REASONS or of.get('addressed_as') not in ADDRESSED_AS
            or not _is_int(of.get('round'), 1) or of.get('opened_by') not in ('decline', 'cancel', 'ask')):
        problems.append('a disposition question names the source assignment, its request version, the blocked unit, '
                        'how it ended and why its addressee was chosen')
    elif (data.get('subject') or {}).get('kind') != DISPOSITION_KIND or (data.get('subject') or {}).get('ref') != of['assignment_id']:
        problems.append('a disposition question\'s subject is the source assignment')
    answer = data.get('answer')
    if isinstance(answer, dict) and isinstance(answer.get('command'), dict) \
            and disposition_answer_problem(answer['command']):
        problems.append('a disposition answer carries what its ruling needs inside the signed command')
    return problems


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
    if content.get('kind') not in KINDS and content.get('kind') != DISPOSITION_KIND:
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
                or not _is_str(answer.get('command_id')) or not isinstance(answer.get('command'), dict)
                or not _is_str(answer.get('signature'))):
            problems.append('an answered record carries the owner ruling, request version, and the signed command')
    elif answer is not None:
        problems.append('only an answered record carries an answer')
    disposition = data.get('disposition')
    if state in ('DECLINED', 'CANCELED'):
        if not isinstance(disposition, dict) or not _is_str(disposition.get('principal')) \
                or not _is_str(disposition.get('command_id')):
            problems.append('a declined or canceled record names who disposed of it and the command')
    elif disposition is not None:
        problems.append('only a declined or canceled record carries a disposition')
    if data.get('kind') == DISPOSITION_KIND:
        problems.extend(disposition_problems(data))
    elif data.get('disposition_of') is not None:
        problems.append('only a disposition question names the work it disposes of')
    return problems


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class Inbox:
    """One repository's inbox on the configured real store connection.

    `store`, `membership`, `claims` and `contract` are the control_store, control_membership,
    control_claim and entity_contract modules; pass the store module the claim organ uses.
    `sign(bytes) -> text` signs journal records as `journal_signer`. `intake` is the VELDO-0126
    Intake on the same connection that `dispose` submits an `other` instruction to; without it
    `other` is refused as unavailable_service. Observations record identity, accepted versions and
    outcome, never brief text, signatures, answers or instructions.
    """

    def __init__(self, store, membership, claims, contract, conn, coordinates, journal_signer, sign,
                 authority_generation=1, clock=time.time, *, intake=None):
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
        self.intake = intake
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
            if content['kind'] == DISPOSITION_KIND:
                raise Refused('invalid_input', 'a disposition question is opened by the decline, cancel or ask it follows')
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
            question = data['kind'] == DISPOSITION_KIND
            if question and op not in ('answer', 'dispose'):
                # Declining or canceling it would open another question about the same unit; `other`
                # is how a person says "not me" or "give it to someone else".
                raise Refused('invalid_input', 'a disposition question can only be answered')
            if op == 'dispose' and not question:
                raise Refused('invalid_input', 'dispose applies the answer to a disposition question')
            if op in ('answer', 'decline'):
                if (data.get('subject') or {}).get('kind') == SETTLEMENT_SUBJECT_KIND:
                    # A request with settlement terms is answered, or rejected, only through the settlement
                    # service, whose rejection is a ruling with the owner's reasoning. The record's version is
                    # pinned below, so a revision of the subject is stale.
                    raise Refused('settlement_required', 'a request with settlement terms is answered or declined '
                                  'through the settlement service')
                self._active(state, principal, now, ('person',), data['scope'])
                params['ruling'] = command.get('ruling')
                if question:
                    problem = disposition_answer_problem(command)
                    if problem:
                        raise Refused('invalid_input', problem)
                if op == 'answer':
                    params['signed'] = {'command': command, 'signature': packet['signature']}
                    # The key that verified it, and when: admission verifies against this key as the
                    # answer's own journal record pinned it, so a later rotation strands nothing.
                    params['verified_by'] = {'key_id': key['key_id'], 'accepted_at': now}
            elif op == 'resume':
                touched.update(self._resume(state, entities, current, principal, now, command, params))
            elif op == 'ask':
                touched.update(self._ask(state, entities, aid, data, principal, now, params, observation))
            elif op == 'dispose':
                inputs, repeated = self._dispose(state, entities, current, principal, now, command, params, observation)
                if repeated is not None:
                    return repeated
                touched.update(inputs)
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
            if op in ('decline', 'cancel'):
                touched.update(self._question_on_end(state, entities, aid, data, op, principal, now, params, observation))
            touched.add(data['owner'])
        versions = {eid: entities.get(eid, {}).get('version', 0) for eid in touched}
        observation['accepted_versions'] = versions
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION,
                      parameters=params, expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        record = self.store.materialized_state(self.conn)['entities'][aid]['data']
        result = {'ok': True, 'reason': op, 'assignment_id': aid, 'assignment': record, 'receipt': receipt,
                  'released_claim': released, 'stop_requester': op == 'open'}
        if 'question' in params or 'question_refusal' in params:
            result.update(question_id=(params.get('question') or {}).get('id'),
                          question_refusal=params.get('question_refusal'))
        if op == 'dispose':
            plan = params['dispose']
            result.update(ruling=plan['ruling'], proposal_id=plan['record'].get('proposal_id'),
                          disposition_id=plan['record_id'], repeated=False)
        return result

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
        if params['action'] == 'dispose' and params['dispose']['ruling'] == 'close':
            # The backlog item's open units are re-read here, so a unit added between the read and the
            # commit is not canceled with it: closing one unit never cancels sibling work.
            plan = params['dispose']
            if self._siblings(conn, plan['unit_id'], plan['backlog_item_uuid']) != plan['siblings']:
                raise self.store.StoreRefused('stale_subject', 'the backlog item\'s units changed while the unit was closed')
        return self._transition(params, before)

    def _siblings(self, conn, unit, backlog):
        """The other units of `backlog` that are not terminal, read on `conn`."""
        terminal = self.contract.LIFECYCLES['execution_unit']['terminal']
        found = []
        for eid, text in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', ('execution_unit',)):
            data = json.loads(text)
            if eid != unit and isinstance(data, dict) and data.get('backlog_item_uuid') == backlog \
                    and data.get('state') not in terminal:
                found.append(eid)
        return found

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

    # What becomes of work that stopped (VELDO-0133).

    def _question_on_end(self, state, entities, aid, data, op, principal, now, params, observation):
        """The disposition question a decline or cancel opens in its own transaction, when the
        assignment blocks a unit parked on it; otherwise nothing. When no project owner resolves
        the end is still accepted, no question is opened and the refusal is named."""
        unit = data.get('unit_id')
        if not _is_str(unit):
            return set()
        cid = self.claims.claim_id(self.ids['repository_uuid'], unit)
        claim = entities.get(cid, {}).get('data') or {}
        if claim.get('state') != 'released' or claim.get('parked_on') != params['assignment_id']:
            return {cid}
        ended_as = 'declined' if op == 'decline' else 'canceled'
        inputs, refusal = self._prepare_question(state, entities, aid, data, op, ended_as, principal, principal, now,
                                                 params, observation)
        if refusal:
            params['question_refusal'] = refusal
        return inputs

    def _ask(self, state, entities, aid, data, principal, now, params, observation):
        """`ask`: open the question for a parked unit no event opened one for (an EXPIRED record, an
        answer that no longer admits) or ask again after `other` routed it to intake."""
        self._active(state, principal, now, self.AC.BOUNDARIES['proposal_commit'], data['scope'])
        parked = next((p for p in self.parked_units() if p['assignment_id'] == aid), None)
        if parked is None or parked['unit_id'] != data.get('unit_id'):
            raise Refused('invalid_input', 'the assignment blocks no parked unit')
        reason = parked['reason']
        if reason in ('awaiting_disposition', 'ready_to_dispose'):
            raise Refused('stale_subject', 'a disposition question about this unit is open')
        if reason not in ASKABLE_REASONS:
            raise Refused('invalid_input', 'ask opens a question for expired work, an answer that no longer admits, '
                                           'or work routed to intake')
        ended_as = parked.get('ended_as') or reason
        ended_by = (data.get('disposition') or {}).get('principal')
        inputs, refusal = self._prepare_question(state, entities, aid, data, 'ask', ended_as, ended_by, principal, now,
                                                 params, observation)
        if refusal:
            raise Refused(refusal, 'the unit\'s ownership chain resolves to no single project owner')
        return inputs

    def _prepare_question(self, state, entities, aid, data, opened_by, ended_as, ended_by, asker, now, params,
                          observation):
        """(inputs, refusal): the question about the unit `aid` blocks, put in params['question'],
        with every entity id its addressee and round were read from."""
        repository = self.ids['repository_uuid']
        unit = data['unit_id']
        u = entities.get(unit, {})
        if u.get('kind') != 'execution_unit' or (u.get('data') or {}).get('repository_uuid') != repository:
            raise Refused('invalid_input', 'the assignment blocks no execution unit of this repository')
        cid = self.claims.claim_id(repository, unit)
        inputs = {unit, cid}
        if _is_str(u['data'].get('backlog_item_uuid')):
            inputs.add(u['data']['backlog_item_uuid'])
        questions = self._questions(aid)
        prior = questions[-1] if questions else None
        if prior is not None:
            inputs.update((prior['id'], disposition_record_id(prior['id'])))
        addressee, why, read = self._addressee(state, entities, ended_as, ended_by, unit, data['scope'], now, prior)
        inputs.update(read)
        info = dict(source_assignment=aid, unit_id=unit, addressee=addressee, addressed_as=why, operation=opened_by)
        observation['disposition'] = info
        if addressee is None:
            info['refusal'] = 'no_project_owner'
            return inputs, 'no_project_owner'
        self._active(state, addressee, now, ('person',), data['scope'])
        inputs.add(addressee)
        round_ = len(questions) + 1
        alias = disposition_alias(aid, data['request_version'], round_)
        qid = assignment_id(repository, alias)
        inputs.add(qid)
        how = {'declined': 'was declined by %s' % ended_by, 'canceled': 'was canceled by %s' % ended_by,
               'expired': 'expired', 'answer_not_admitted': 'was answered, but the answer no longer admits'}[ended_as]
        brief = ('What becomes of unit %s? It waits for assignment %s at request version %d, which %s. Answer close '
                 'to cancel the unit, backlog to return it to the backlog for an ordinary claim, or other with your '
                 'instruction for the project manager.' % (unit, aid, data['request_version'], how))
        question = dict(kind=DISPOSITION_KIND, owner=addressee, scope=list(data['scope']), deadline=data['deadline'],
                        budget=dict(data['budget']), brief=brief, choices=list(DISPOSITION_CHOICES),
                        subject={'kind': DISPOSITION_KIND, 'ref': aid, 'digest': self.store.digest_of(data)},
                        unit_id=unit, schema=SCHEMA, alias=alias, actor_kind='person', state='OFFERED',
                        requested_by=asker, request_version=1, answer=None, disposition=None,
                        domain_uuid=self.ids['domain_uuid'], repository_uuid=repository,
                        disposition_of=dict(assignment_id=aid, request_version=data['request_version'], unit_id=unit,
                                            ended_as=ended_as, ended_by=ended_by, addressed_as=why, round=round_,
                                            opened_by=opened_by))
        params['question'] = dict(id=qid, source=aid, claim_id=cid, data=question)
        info['question_id'] = qid
        return inputs, None

    def _addressee(self, state, entities, ended_as, ended_by, unit, scope, now, prior):
        """(principal or None, why, ids read): who is asked. A decline is by the owning person, who
        is asked; a cancel by a person asks that person; otherwise the one project owner. Asking
        again asks the person the earlier question asked, or the project owner resolved again."""
        if prior is not None and prior['data']['disposition_of']['addressed_as'] != 'project_owner':
            return prior['data']['owner'], prior['data']['disposition_of']['addressed_as'], set()
        if ended_as == 'declined':
            return ended_by, 'decliner', set()
        if ended_as == 'canceled':
            entry = self.AC.membership_entry(state['membership'], ended_by)
            if entry is not None and entry.get('principal_type') == 'person':
                return ended_by, 'canceler', {ended_by}
        owner, read = self._project_owner(state, entities, unit, scope, now)
        return owner, 'project_owner', read

    def _project(self, entities, unit, read):
        """The project entity at the end of the unit's ownership chain (unit, backlog item, objective,
        project), or None; every id on the way is added to `read`."""
        step = entities.get(unit) or {}
        for field, kind in (('backlog_item_uuid', 'backlog_item'), ('objective_uuid', 'objective'),
                            ('project_uuid', 'project')):
            ref = (step.get('data') or {}).get(field)
            if not _is_str(ref):
                return None
            read.add(ref)
            step = entities.get(ref) or {}
            if step.get('kind') != kind or not isinstance(step.get('data'), dict):
                return None
        return step if _is_str(step['data'].get('name')) else None

    def _project_owner(self, state, entities, unit, scope, now):
        """(principal or None, ids read): the one active person member holding project_owner whose
        scope covers the unit's project and the assignment's scope. Anything but exactly one is
        None: ownership is never guessed."""
        read = {unit}
        project = self._project(entities, unit, read)
        if project is None:
            return None, read
        owners = []
        for member in state['membership']:
            read.add(member['principal'])
            if (self.AC.active_member(member, now)[0] and member.get('principal_type') == 'person'
                    and 'project_owner' in (member.get('roles') or [])
                    and self.membership.scope_covers(member.get('scope'), [project['data']['name']])
                    and self.membership.scope_covers(member.get('scope'), scope)):
                owners.append(member['principal'])
        return (owners[0] if len(owners) == 1 else None), read

    def _questions(self, source):
        """The valid disposition questions about the work `source` blocks, oldest round first."""
        prefix = assignment_id(self.ids['repository_uuid'], DISPOSITION_ALIAS_PREFIX)
        rows, _ = self._rows(None, 'substr(id, 1, ?) = ? AND kind = ?', (len(prefix), prefix, ENTITY_KIND))
        found = [item for item in (self._item(row) for row in rows)
                 if item['data'] is not None and item['data'].get('kind') == DISPOSITION_KIND
                 and item['data']['disposition_of']['assignment_id'] == source]
        return sorted(found, key=lambda item: item['data']['disposition_of']['round'])

    def _record(self, question):
        row = self.conn.execute('SELECT data FROM entities WHERE id=? AND kind=?',
                                (disposition_record_id(question), DISPOSITION_RECORD_KIND)).fetchone()
        return None if row is None else json.loads(row[0])

    def _disposition_state(self, source, ended_as):
        """(reason or None, fields) of a unit parked for one of DISPOSITION_REASONS: its original
        reason while no question was opened, `awaiting_disposition` while the latest question waits
        (or its answer does not admit), `ready_to_dispose` once it admits, `routed_to_intake` after
        `other`, and None once close or backlog was applied (the unit is no longer parked work)."""
        questions = self._questions(source)
        if not questions:
            return ended_as, {}
        latest = questions[-1]
        fields = {'ended_as': ended_as, 'question_id': latest['id']}
        if CATEGORIES[latest['data']['state']] == 'pending':
            return 'awaiting_disposition', fields
        record = self._record(latest['id'])
        if record is not None:
            if record.get('ruling') == 'other':
                return 'routed_to_intake', dict(fields, proposal_id=record.get('proposal_id'))
            return None, fields
        fields['question_admission'] = self._admission(latest)[0]
        return ('ready_to_dispose' if fields['question_admission'] == 'admitted' else 'awaiting_disposition'), fields

    def _dispose(self, state, entities, current, principal, now, command, params, observation):
        """(inputs, repeated result or None): the inputs a dispose binds, and its plan in
        params['dispose']. Like resume, it is accepted only while the question's answer admits, and
        the decision is the answer's, never the disposer's."""
        repository = self.ids['repository_uuid']
        qid, data = params['assignment_id'], current['data']
        self._active(state, principal, now, self.AC.BOUNDARIES['proposal_commit'], data['scope'])
        of = data['disposition_of']
        source, unit = of['assignment_id'], of['unit_id']
        observation['disposition'] = dict(question_id=qid, source_assignment=source, unit_id=unit, addressee=data['owner'],
                                          addressed_as=of['addressed_as'], operation='dispose',
                                          ruling=(data.get('answer') or {}).get('ruling'))
        item = self.read(qid)
        if item is None or item['version'] != current['version']:
            raise Refused('stale_subject', 'the question changed while it was read')
        reason, inputs = self._admission(item)
        if reason != 'admitted':
            raise Refused(reason, 'the question\'s answer does not admit')
        answer = item['data']['answer']
        ruling, signed = answer['ruling'], answer['command']
        u = entities.get(unit, {})
        backlog = (u.get('data') or {}).get('backlog_item_uuid')
        if (u.get('kind') != 'execution_unit' or u['data'].get('repository_uuid') != repository
                or entities.get(backlog, {}).get('kind') != 'backlog_item'):
            raise Refused('invalid_input', 'the question blocks no execution unit of this repository')
        cid, rid = self.claims.claim_id(repository, unit), disposition_record_id(qid)
        inputs = set(inputs) | {source, unit, backlog, cid, rid}
        existing = entities.get(rid)
        if existing is not None and ruling != 'other':
            raise Refused('stale_subject', 'the disposition is already applied')
        claim = entities.get(cid, {}).get('data') or {}
        if existing is None and (claim.get('state') != 'released' or claim.get('parked_on') != source):
            raise Refused('stale_subject', 'the unit is no longer parked on the source assignment')
        record = dict(schema=DISPOSITION_RECORD_SCHEMA, question_id=qid, question_version=item['version'],
                      source_assignment=source, source_request_version=of['request_version'], unit_id=unit,
                      backlog_item_uuid=backlog, ruling=ruling, answered_by=answer['principal'],
                      answer_command_id=answer['command_id'], disposed_by=principal,
                      dispose_command_id=command['command_id'], domain_uuid=self.ids['domain_uuid'],
                      repository_uuid=repository)
        plan = dict(ruling=ruling, question_id=qid, question_version=item['version'], record_id=rid, record=record,
                    source=source, unit_id=unit, backlog_item_uuid=backlog, claim_id=cid, siblings=[])
        if ruling == 'other':
            proposal, arrived, read = self._to_intake(entities, item, unit)
            inputs |= read
            if existing is not None:
                kept = existing.get('data') or {}
                if existing.get('kind') != DISPOSITION_RECORD_KIND or kept.get('proposal_id') != proposal:
                    raise Refused('unknown_outcome', 'the recorded disposition names another proposal')
                return inputs, {'ok': True, 'reason': 'dispose', 'assignment_id': qid, 'ruling': ruling,
                                'proposal_id': proposal, 'disposition_id': rid, 'repeated': True}
            record.update(instruction=signed['instruction'], proposal_id=proposal, intake_source=arrived)
        elif ruling == 'close':
            plan['siblings'] = self._siblings(self.conn, unit, backlog)
            inputs |= set(plan['siblings'])
            record.update(backlog_item_left=bool(plan['siblings']), open_siblings=list(plan['siblings']))
        else:
            plan['unpark'] = dict(action='unpark', unit_id=unit, backlog_item_uuid=backlog, claim_id=cid, holder=None,
                                  generation=0, capabilities=[], repository_uuid=repository, parked_on=source)
        params['dispose'] = plan
        return inputs, None

    def _to_intake(self, entities, item, unit):
        """(proposal id, arrival, ids read): the signed instruction, exactly as signed, submitted
        through the VELDO-0126 intake's public attested submission with the evidence the answer
        carries, the answering person and the project from the unit's chain. The intake authenticates
        the evidence itself and takes the source identity from it; this inbox names no source. The
        same answer again is the same source request, so the intake returns the same proposal and
        writes nothing."""
        if self.intake is None:
            raise Refused('unavailable_service', 'no intake is configured to take the instruction')
        answer = item['data']['answer']
        signed, of = answer['command'], item['data']['disposition_of']
        arrived = signed['arrived_on']
        read = {unit}
        project = self._project(entities, unit, read)
        evidence = (arrived['evidence_id'] if arrived['source_kind'] == 'telegram_message'
                    else {'request': arrived['request'], 'signature': arrived['signature']})
        # The signed answer's command identity beside the source: the evidence that makes it an
        # owner instruction.
        disposition = dict(question_id=item['id'], answer_command_id=answer['command_id'],
                           source_assignment=of['assignment_id'], unit_id=unit)
        result = self.intake.submit_attested(arrived['source_kind'], evidence, principal=answer['principal'],
                                             text=signed['instruction'],
                                             project=project['data']['name'] if project else None,
                                             provenance={'disposition': disposition})
        if result.get('outcome') not in ('proposed', 'inbox') or not _is_str(result.get('proposal_id')):
            code = str(result.get('reason') or 'unknown_outcome').split(':', 1)[0]
            raise Refused(INTAKE_REFUSALS.get(code, 'invalid_input'), 'the intake did not take the instruction')
        taken = result.get('command') or {}
        return result['proposal_id'], {'source_kind': taken.get('source_kind'), 'source_id': taken.get('source_id')}, read

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
        if op == 'ask':
            if data['request_version'] != params['request_version']:
                raise refused('stale_subject', 'the assignment changed while the question was opened')
            return self._question_changes(params, before)
        if op == 'dispose':
            return self._dispose_changes(params, before)
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
                                                       command_id=params['command_id'],
                                                       command=params['signed']['command'],
                                                       signature=params['signed']['signature'],
                                                       key_id=params['verified_by']['key_id'],
                                                       accepted_at=params['verified_by']['accepted_at']))
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
        changes = {aid: {'kind': ENTITY_KIND, 'data': data}}
        if 'question' in params:
            # The decline or cancel and the question about the work it stopped commit together, so
            # there is no moment when the unit is parked with no question.
            changes.update(self._question_changes(params, before))
        return changes

    def _question_changes(self, params, before):
        """The disposition question an end or an ask opens, re-checked inside the transaction: it
        does not exist yet and the unit is still parked on the source assignment."""
        refused = self.store.StoreRefused
        question = params['question']
        claim = before.get(question['claim_id'], {}).get('data') or {}
        if question['id'] in before:
            raise refused('stale_subject', 'a disposition question of this round exists')
        if claim.get('state') != 'released' or claim.get('parked_on') != question['source']:
            raise refused('stale_subject', 'the unit is no longer parked on the source assignment')
        return {question['id']: {'kind': ENTITY_KIND, 'data': question['data']}}

    def _dispose_changes(self, params, before):
        """The registered dispose: the record of the applied disposition, and for `close` the declared
        disposition_recorded edges of the unit and (with no open sibling) its backlog item, for
        `backlog` the claim organ's unpark. Each precondition is re-checked on the pinned versions."""
        refused = self.store.StoreRefused
        plan = params['dispose']
        question = before.get(plan['question_id'], {})
        claim = before.get(plan['claim_id'], {}).get('data') or {}
        if (question.get('version') != plan['question_version'] or (question.get('data') or {}).get('state') != 'SUBMITTED'
                or plan['record_id'] in before):
            raise refused('stale_subject', 'the question changed or its disposition is already applied')
        if claim.get('state') != 'released' or claim.get('parked_on') != plan['source']:
            raise refused('stale_subject', 'the unit is no longer parked on the source assignment')
        record = plan['record']
        changes = {plan['record_id']: {'kind': DISPOSITION_RECORD_KIND, 'data': record}}
        mark = dict(question=plan['question_id'], ruling=plan['ruling'], principal=record['answered_by'],
                    answer_command_id=record['answer_command_id'], dispose_command_id=record['dispose_command_id'])
        if plan['ruling'] == 'close':
            targets = [(plan['unit_id'], 'execution_unit')]
            if not plan['siblings']:
                targets.append((plan['backlog_item_uuid'], 'backlog_item'))
            for eid, kind in targets:
                current = dict(before[eid]['data'])
                ok, why = self.contract.transition(kind, current.get('state'), 'CANCELED', {'disposition_recorded': True})
                if not ok:
                    raise refused('transition_refused', why)
                changes[eid] = {'kind': kind, 'data': dict(current, state='CANCELED', disposition=mark)}
        if 'unpark' in plan:
            changes.update(self.claims.transition(plan['unpark'], before))
        return changes

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
        if data['kind'] == DISPOSITION_KIND:
            content['disposition_of'] = dict(data['disposition_of'])
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
        now = self.clock()
        inputs.add(data['owner'])
        owner = self.AC.membership_entry(state['membership'], data['owner'])
        active, _ = self.AC.active_member(owner, now)
        if not active or owner['principal_type'] != 'person' \
                or not self.membership.scope_covers(owner.get('scope'), data['scope']):
            return 'missing_authority', inputs
        # The owner's own signed answer: it answers this assignment at this request version with
        # this ruling, was written by that answer's journal record, and its signature verifies
        # against the owner's key as that record pinned it.
        answer, signed = data['answer'], data['answer']['command']
        binds = (signed.get('operation') == 'answer' and signed.get('alias') == data['alias']
                 and signed.get('principal') == data['owner'] and signed.get('ruling') == answer['ruling']
                 and signed.get('request_version') == data['request_version']
                 and signed.get('command_id') == answer['command_id']
                 and all(signed.get(k) == v for k, v in self.ids.items()))
        if not binds:
            return 'missing_authority', inputs
        row = self.conn.execute('SELECT principal, transition, seq, before_versions FROM journal WHERE command_id=?',
                                (data['answer']['command_id'],)).fetchone()
        written = json.loads(row[1]).get(item['id'], {}) if row else {}
        if row is None or row[0] != data['owner'] or written.get('version') != item['version'] \
                or written.get('digest') != item['digest']:
            return 'missing_authority', inputs
        key = self._answer_key(state, data, row, inputs)
        verified = False
        if key:
            verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(signed), answer['signature'],
                                                    self.AC.allowed_signers_line(data['owner'], key['public_key']),
                                                    data['owner'])
        if not verified:
            return 'missing_authority', inputs
        return 'admitted', inputs

    def _answer_key(self, state, data, row, inputs):
        """The owner's verification key as it stood when the answer was accepted, or None.

        VELDO-0027's historical rule: a signature is verified against the key that was active when
        it was signed, never against whatever key is active now, so a later rotation, retirement or
        in-place replacement does not strand an accepted answer. The key is the one the answer's
        own journal record pinned (its before-version), read from the journal record that wrote
        that version and checked against its committed digest; it must name the owner and have been
        active at the acceptance time. A revocation reaches back: a current keyring entry with the
        same public key revoked at or before the acceptance verifies nothing. """
        answer = data['answer']
        kid, at = answer.get('key_id'), answer.get('accepted_at')
        if not _is_str(kid) or type(at) not in (int, float) or not math.isfinite(at):
            return None
        pinned = json.loads(row[3]).get(kid) if row[3] else None
        if not _is_int(pinned, 1):
            return None
        stored = None
        for (transition,) in self.conn.execute('SELECT transition FROM journal WHERE seq < ? AND instr(transition, ?) > 0 '
                                               'ORDER BY seq DESC', (row[2], json.dumps(kid))):
            stored = json.loads(transition).get(kid)
            if stored is not None:
                break
        if (not isinstance(stored, dict) or stored.get('version') != pinned or stored.get('kind') != 'verification_key'
                or not isinstance(stored.get('data'), dict)
                or self.store.digest_of({'kind': stored['kind'], 'data': stored['data'], 'version': pinned}) != stored.get('digest')):
            return None
        key = dict(stored['data'], key_id=kid)
        if not _is_str(key.get('public_key')) or self.AC.active_key([key], data['owner'], at) is None:
            return None
        inputs.add(kid)
        words = key['public_key'].split()[:2]
        for current in state['keyring']:
            if current.get('principal') != data['owner'] or not _is_str(current.get('public_key')) \
                    or current['public_key'].split()[:2] != words:
                continue
            inputs.add(current['key_id'])
            if current.get('revoked_at') is not None and current['revoked_at'] <= at:
                return None
        return key

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

    def parked_units(self):
        """Every unit of this repository parked on a person assignment: its unit, claim and the
        assignment it waits for, and why it is still parked (PARKED_REASONS). A unit whose
        assignment was declined, canceled or answered without admitting stays parked, because no
        Release 1 command decides what becomes of it; it is listed here so it is never invisible.
        `admission` is the admission answer of an answered assignment, otherwise None."""
        prefix = self.claims.claim_id(self.ids['repository_uuid'], '')
        parked = []
        for cid, e in sorted(self.store.materialized_state(self.conn)['entities'].items()):
            claim = e.get('data')
            if (e.get('kind') != 'claim' or not cid.startswith(prefix) or not isinstance(claim, dict)
                    or claim.get('state') != 'released' or not claim.get('parked_on')):
                continue
            aid, admission = claim['parked_on'], None
            item = self.read(aid) if _is_str(aid) else None
            if item is None:
                reason = 'missing_assignment'
            elif item['problems']:
                reason = 'invalid_assignment'
            else:
                category = CATEGORIES[item['data']['state']]
                if category == 'pending':
                    reason = 'awaiting_answer'
                elif category == 'answered':
                    admission = self._admission(item)[0]
                    reason = 'ready_to_resume' if admission == 'admitted' else 'answer_not_admitted'
                else:
                    reason = category
            fields = {}
            if reason in DISPOSITION_REASONS:
                reason, fields = self._disposition_state(aid, reason)
                if reason is None:
                    continue  # closed or returned to the backlog: no longer parked work
            parked.append({'unit_id': claim.get('unit_id'), 'claim_id': cid, 'assignment_id': aid,
                           'reason': reason, 'admission': admission, **fields})
        return parked

    def metrics(self):
        pending = sum(1 for e in self.index()['entries'] if e['category'] == 'pending')
        parked = self.parked_units()
        by_reason = {}
        for unit in parked:
            by_reason[unit['reason']] = by_reason.get(unit['reason'], 0) + 1
        # Accepted and refused disposition operations by the outcome they apply (VELDO-0133).
        dispositions = {'accepted': {}, 'refused': {}}
        for o in self.observations:
            if o.get('operation') == 'dispose':
                ruling = (o.get('disposition') or {}).get('ruling') or 'unknown'
                dispositions[o['outcome']][ruling] = dispositions[o['outcome']].get(ruling, 0) + 1
        return dict(self.counts, pending=pending, parked=len(parked), parked_by_reason=by_reason,
                    dispositions=dispositions)
