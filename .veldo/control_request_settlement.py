"""Atomic request settlement and conjunctive authority (VELDO-0068, PLAN-0019 W53, R40, R72).

WHAT THIS MODULE IS. The one settlement service of a repository's control store. A request is a
VELDO-0064 inbox assignment at one request version, presented on Telegram by VELDO-0065. An
owner's answer reaches it as accepted evidence from either enrolled input surface: a signed
Telegram assertion the VELDO-0065 presenter accepted (a `presentation_answer`, attributed by
VELDO-0066 and signed by the VELDO-0067 edge), or an answer from the authenticated API edge, which
this service accepts itself under the same presentation rules. `settle` then decides the request
version once and commits, in ONE store transaction, the settlement (the offered choice the owner
picked, its ruling and the owner's own reasoning, with the signed assertion), the settlement's
nonce, the typed effect its touchpoint gives that ruling, the terminal request state (the
assignment moves to SATISFIED carrying the answer and the settlement reference) and the receipt.
The control store is the only authority: a second store, a file, a tracker status or a request
record in the repository is never read as settlement state, and no other store can be attached.

THE TOUCHPOINTS. JOURNEY is the configuration of the running journey's enabled request touchpoints
(grooming, admission, priority, finding disposition, decision disposition): the assignment kind
each is presented as, its policy predicates (the roles an answering principal must hold, the count
of distinct principals and the independence required) and the typed effect each ruling produces.
A request names its touchpoint through signed terms: the requester records `settlement_terms`
(touchpoint, target, proposal, the request's own `required_roles` and `quorum`) and opens the
assignment with the terms as its subject, so the presentation binds the terms digest.

AUTHORITY IS CONJUNCTIVE. The effective requirement is the journey policy AND the request's terms:
the union of the roles, the larger count and the larger independence. It is decided through the
authority contract's `authorize` at the decision_settlement boundary, by distinct principal (one
person on two channels is one principal), for every scope of the request. Independence is also
separation: a counted principal is never the requester, nor in the requester's independence group.
Release 1 presents a request to one owner, so a count above one or an independence above one is an
UNSUPPORTED quorum policy: it blocks the request by name and is never weakened to what can be met.

ONE WINNER. The settlement key is the request and its version, as the entity id, the command id and
the nonce. Every accepted answer of the version is read in acceptance order; the earliest one that
still binds the current presentation and request wins, and every other answer that read returned is
listed on the settlement as conflicting or duplicate, never counted twice and never settled. An
answer accepted on another connection after that read and before the settlement commits is NOT
listed: the transaction pins the answers it read, not the absence of others. That answer takes no
effect, is never counted, and settling again refuses as already_settled; listing it is Release 2.
A second settlement of the same version, from any surface, is refused and writes nothing;
concurrent settlements commit once.

THE GOVERNING BINDING (VELDO-0069). A request whose terms target a governing decision (target kind
GOVERNING_TARGET, settled through the decision_disposition touchpoint) names the exact question the
owner is asked: the governing record, its decision id and revision, and the digests of its framing,
its subject (kind, id, digest) and its scope, with the digest of that question. Settling it writes, in
the SAME transaction as the settlement, effect, receipt and terminal request state, the governing
binding: a `decision_settlement` record keyed by the decision and the revision ruled on, carrying the
chosen option, the decider, the time and a body signed by the configured decision signer under the
VELDO-0054 settlement namespace. The body binds what the owner was shown, never what the record says
at settlement time, so a stale framing, another subject or an older revision is bound faithfully and
every VELDO-0054 consumer names it (unbound_decision:<id>/framing, /subject, /revision) instead of
unblocking. A question at a revision ABOVE the record's current one, as read and pinned by the settling
transaction, is refused as future_revision with nothing written: that revision was never shown to anyone,
and a binding written for it would clear the work the moment the record reached it. A governed subject kind this release does not bind (anything but spec or plan), an absent
governing record or no configured decision signer stops the settlement by name: nothing is written, so
a receipt is never committed without its binding. A later revision's binding supersedes an earlier
one, since the consumers read only the binding of the record's current revision; one revision is
bound once.

PUBLISHED STATE. `publish` records the settled requests as statuses of a VELDO-0035 accepted revision
(`.veldo/settlements/<alias>.json` the settlement, `<alias>.request.json` the terminal request) and
materializes an accepted snapshot; readers take request state from those statuses only.

WHAT IT IS NOT. Not crash, replica or restart recovery, not the exhaustive channel matrix and not a
quorum of several people (Release 2 and 3). Observations carry identities, versions, outcomes and
named refusals, never rationale text, signatures or keys. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time

SCHEMA = 'veldo.request_settlement/v1'
TERMS_SCHEMA = 'veldo.settlement_terms/v1'
EFFECT_SCHEMA = 'veldo.settlement_effect/v1'
RECEIPT_SCHEMA = 'veldo.settlement_receipt/v1'
API_SCHEMA = 'veldo.settlement_api_answer/v1'
SETTLEMENT_KIND, EFFECT_KIND, RECEIPT_KIND = 'request_settlement', 'settlement_effect', 'settlement_receipt'
# VELDO-0069: the governing binding a settlement of a governing decision question writes, the target kind
# that names such a question, the touchpoint it is settled through and the fields the owner rules on.
DECISION_SETTLEMENT_KIND, GOVERNING_RECORD_KIND = 'decision_settlement', 'decision'
GOVERNING_TARGET, GOVERNING_TOUCHPOINT = 'governing_decision', 'decision_disposition'
GOVERNING_FIELDS = ('decision_id', 'revision', 'framing_digest', 'subject', 'scope_digest')
TERMS_KIND, API_KIND = 'settlement_terms', 'settlement_api_answer'
SETTLE, TERMS, API = 'request_settle', 'settlement_terms_record', 'settlement_api_answer'
OWNER = 'VELDO-0068 request settlement'
WRITES = ('entities', 'journal', 'commands', 'nonces')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
# The assignment subject kind that names a request's settlement terms.
SUBJECT_KIND = 'settlement_terms'
TELEGRAM, API_CHANNEL = 'telegram_chat', 'api'
TERMINAL_STATE = 'SATISFIED'
# The R18 edges from each pending state to the terminal state, with the predicates settlement establishes.
TERMINAL_PATH = ('OFFERED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED', TERMINAL_STATE)
TERMINAL_EVIDENCE = {'actor_predicate_satisfied': True, 'work_started': True, 'artifact_submitted': True,
                     'receipt_verified': True}

# THE JOURNEY CONFIGURATION: every enabled request touchpoint. Roles are the R37 scoped roles: the
# project owner grooms and disposes of decisions, the admission and priority authorities admit and
# prioritize (admission_contract.CLASS_POLICY for ordinary work), the technical authority disposes of
# findings. One distinct principal, independent of the requester, answers each.
JOURNEY = {
    'grooming': {'assignment_kind': 'decision', 'roles': ('project_owner',),
                 'quorum': {'count': 1, 'min_independence': 1},
                 'effects': {'approve': 'backlog_item_groomed', 'reject': 'backlog_item_rejected',
                             'return_for_elaboration': 'backlog_item_returned'}},
    'admission': {'assignment_kind': 'decision', 'roles': ('admission_authority',),
                  'quorum': {'count': 1, 'min_independence': 1},
                  'effects': {'approve': 'work_admitted', 'reject': 'admission_refused',
                              'return_for_elaboration': 'admission_returned'}},
    'priority': {'assignment_kind': 'decision', 'roles': ('priority_authority',),
                 'quorum': {'count': 1, 'min_independence': 1},
                 'effects': {'approve': 'priority_assigned', 'reject': 'priority_refused',
                             'return_for_elaboration': 'priority_returned'}},
    'finding_disposition': {'assignment_kind': 'review_disposition', 'roles': ('technical_authority',),
                            'quorum': {'count': 1, 'min_independence': 1},
                            'effects': {'approve': 'finding_accepted', 'reject': 'finding_rejected',
                                        'return_for_elaboration': 'finding_returned'}},
    'decision_disposition': {'assignment_kind': 'decision', 'roles': ('project_owner',),
                             'quorum': {'count': 1, 'min_independence': 1},
                             'effects': {'approve': 'decision_approved', 'reject': 'decision_rejected',
                                         'return_for_elaboration': 'decision_returned'}},
}
QUORUM_FIELDS = ('count', 'min_independence')
# What Release 1 settles: one presented owner, at most separation from the requester.
SUPPORTED = {'count': (1,), 'min_independence': (0, 1)}
TERMS_FIELDS = ('operation', 'terms', 'principal', 'command_id', 'nonce', 'touchpoint', 'target', 'proposal',
                'required_roles', 'quorum') + COORDINATES
API_FIELDS = ('schema', 'edge', 'answer_id', 'principal', 'request_id', 'request_version', 'presentation_id',
              'presentation_digest', 'presentation_version', 'choice', 'rationale') + COORDINATES
# Every named refusal and its error class; an unknown code is an unknown outcome, never success.
TAXONOMY = {'invalid_input': 'invalid_input', 'unmatched_choice': 'invalid_input', 'missing_rationale': 'invalid_input',
            'not_authorized': 'missing_authority', 'not_owner': 'missing_authority', 'owner_not_current': 'missing_authority',
            'role_not_satisfied': 'missing_authority', 'independence_not_met': 'missing_authority',
            'quorum_not_met': 'missing_authority', 'unsupported_quorum': 'missing_authority',
            'stale_presentation': 'stale_subject', 'stale_terms': 'stale_subject', 'already_settled': 'stale_subject',
            'request_closed': 'stale_subject', 'stale_subject': 'stale_subject', 'already_answered': 'stale_subject',
            'future_revision': 'stale_subject',
            'missing_terms': 'missing_evidence', 'unsupported_touchpoint': 'missing_evidence',
            'no_answer': 'missing_evidence', 'missing_evidence': 'missing_evidence',
            'missing_decision': 'missing_evidence', 'unsupported_subject': 'invalid_input',
            'unavailable_service': 'unavailable_service'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def settlement_id(request, version):
    """THE settlement key: one per request version, whatever surface the answer came from."""
    return 'request-settlement:%s:%d' % (request, version)


def effect_id(request, version):
    return 'settlement-effect:%s:%d' % (request, version)


def receipt_id(request, version):
    return 'settlement-receipt:%s:%d' % (request, version)


def binding_id(decision, revision):
    """THE governing binding key (VELDO-0069): one per governing record and revision ruled on."""
    return 'decision-settlement:%s:%d' % (decision, revision)


def terms_id(repository_uuid, name):
    return 'settlement-terms:%s:%s' % (repository_uuid, name)


def api_answer_id(request, version, edge, answer):
    return 'settlement-api-answer:%s:%d:%s:%s' % (request, version, edge, answer)


def status_paths(alias):
    """The published paths of one settled request: its settlement and its terminal request state."""
    return '.veldo/settlements/%s.json' % alias, '.veldo/settlements/%s.request.json' % alias


def quorum_problem(quorum):
    """Why a quorum mapping is not one this release settles, or None."""
    if not isinstance(quorum, dict) or set(quorum) - set(QUORUM_FIELDS):
        return 'a quorum is {count, min_independence}'
    for field in QUORUM_FIELDS:
        value = quorum.get(field)
        if value is not None and (type(value) is not int or value < 0):
            return '%s must be a non-negative integer' % field
    return None


def requirement(touchpoint, terms):
    """The effective requirement: the journey policy AND the request's own terms. Raises Refused
    unsupported_quorum when the conjunction is not a policy this release can settle."""
    policy = JOURNEY[touchpoint]
    wanted = terms.get('quorum') or {}
    for quorum in (policy['quorum'], wanted):
        problem = quorum_problem(quorum)
        if problem:
            raise Refused('unsupported_quorum', problem)
    roles = sorted(set(policy['roles']) | set(terms.get('required_roles') or []))
    count = max(policy['quorum'].get('count') or 1, wanted.get('count') or 1)
    independence = max(policy['quorum'].get('min_independence') or 0, wanted.get('min_independence') or 0)
    if count not in SUPPORTED['count'] or independence not in SUPPORTED['min_independence']:
        raise Refused('unsupported_quorum', 'count %d and independence %d are not settled in this release'
                      % (count, independence))
    return {'roles': roles, 'count': count, 'min_independence': independence}


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DD = _sibling('settlement_decision_dependency', 'control_decision_dependency.py')


def governing_question(target):
    """The exact question a governing target asks the owner to rule on."""
    return {k: target.get(k) for k in GOVERNING_FIELDS}


def governing_target(decision, record):
    """The terms target a requester opens a governing decision question with: the record's entity id and
    the decision, revision, framing, subject and scope it asks about, with the digest of that question."""
    record = record if isinstance(record, dict) else {}
    question = {'decision_id': record.get('decision_id'), 'revision': record.get('revision'),
                'framing_digest': record.get('framing_digest'), 'subject': dict(record.get('subject') or {}),
                'scope_digest': DD.scope_digest(record.get('scope'))}
    return dict(question, kind=GOVERNING_TARGET, ref=decision, digest=digest(question))


def governing_problem(target):
    """Why a governing target is not a question this release binds, as (code, detail), or None."""
    q = governing_question(target)
    subject = q['subject']
    if not (_is_str(q['decision_id']) and type(q['revision']) is int and q['revision'] >= 1
            and _is_str(q['framing_digest']) and _is_str(q['scope_digest']) and isinstance(subject, dict)
            and set(subject) == {'kind', 'id', 'digest'} and all(_is_str(subject[k]) for k in subject)):
        return 'invalid_input', 'a governing target names its decision, revision, framing, subject and scope'
    if target.get('digest') != digest(q):
        return 'invalid_input', 'the governing target digest is not the digest of the question it names'
    if subject['kind'] not in DD.SUBJECT_KINDS:
        return 'unsupported_subject', 'subject kind %r is not bound in this release' % subject['kind']
    return None


class Settlement:
    """The settlement service on one control store connection.

    `store`, `membership`, `assignment` and `presentation` are the control_store, control_membership,
    control_assignment and control_channel_presentation modules; `inbox` and `presenter` are the
    VELDO-0064 Inbox and VELDO-0065 Presenter on the same connection. `api_edge` names the
    authenticated API edge's service principal. `sign(bytes) -> text` signs journal records as
    `journal_signer`. `decision_signer` is (principal, sign) for governing bindings (VELDO-0069): `sign`
    signs a binding body under the VELDO-0054 settlement namespace as `principal`, a signer the hosts
    that read eligibility trust. Without it a governing decision question is never settled."""

    def __init__(self, store, membership, inbox, presenter, conn, journal_signer, sign, *, assignment, presentation,
                 api_edge=None, authority_generation=1, clock=time.time, decision_signer=None):
        if not hasattr(conn, 'command_registry') or inbox.conn is not conn or presenter.conn is not conn:
            raise Refused('invalid_input', 'settlement has one authority: the control store connection the inbox '
                                           'and the presenter use')
        if decision_signer is not None and not (isinstance(decision_signer, tuple) and len(decision_signer) == 2
                                                and _is_str(decision_signer[0]) and callable(decision_signer[1])):
            raise Refused('invalid_input', 'a decision signer is (principal, sign)')
        self.decision_signer = decision_signer
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.inbox, self.presenter, self.I, self.V = inbox, presenter, assignment, presentation
        self.conn, self.ids = conn, dict(inbox.ids)
        self.journal_signer, self.sign = journal_signer, sign
        self.api_edge, self.authority_generation, self.clock = api_edge, authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[SETTLE] = {'transition': self._settle_transition, 'writes': WRITES}
        conn.command_registry[TERMS] = {'transition': self._new_transition, 'writes': WRITES}
        conn.command_registry[API] = {'transition': self._new_transition, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={SETTLEMENT_KIND: (SETTLE,), EFFECT_KIND: (SETTLE,),
                                                 RECEIPT_KIND: (SETTLE,), TERMS_KIND: (TERMS,), API_KIND: (API,),
                                                 DECISION_SETTLEMENT_KIND: (SETTLE,)},
                             module=__file__)

    # reading

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def _data(self, eid, kind):
        e = self._entity(eid)
        return None if e is None or e['kind'] != kind else e['data']

    def settlement(self, request, version):
        return self._data(settlement_id(request, version), SETTLEMENT_KIND)

    def settlements(self):
        return [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id',
                                                           (SETTLEMENT_KIND,))]

    def answers(self, request, version):
        """Every accepted answer of one request version, from both surfaces, in acceptance order:
        (evidence id, entity version, channel, answer)."""
        found = []
        for kind, channel in ((self.V.ANSWER_KIND, TELEGRAM), (API_KIND, API_CHANNEL)):
            for eid, ver, text in self.conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id',
                                                    (kind,)):
                data = json.loads(text)
                if data.get('request_id') == request and data.get('request_version') == version:
                    found.append((eid, ver, channel, data))
        return sorted(found, key=lambda a: (a[3].get('accepted_at') or 0, a[0]))

    def _observe(self, operation, request, versions, outcome, reason, **extra):
        accepted = outcome in ('settled', 'recorded')
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.ids, operation=operation, request_id=request, accepted_versions=versions,
                                      outcome=outcome, reason=reason,
                                      error_class=None if accepted else taxonomy(reason), **extra))
        result = dict({'request_id': request, 'outcome': outcome}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    def _commit(self, operation, command_id, params, expected, principal=None):
        command = dict(command_id=command_id, principal=principal or self.journal_signer, operation=operation,
                       parameters=params, expected_versions=expected, artifact_digests=[], nonce=command_id)
        return self.store.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)

    def _verified(self, principal, body, signature, types):
        """The member entry of `principal` when `signature` is its active key's over `body` and it is an
        active member of one of `types`; Refused not_authorized otherwise."""
        now = self.clock()
        state = self.membership.authority_state(self.store, self.conn)
        entry = self.AC.membership_entry(state['membership'], principal)
        if not self.AC.active_member(entry, now)[0] or entry.get('principal_type') not in types:
            raise Refused('not_authorized', 'not an active member who may act here')
        key = self.AC.active_key(state['keyring'], principal, now)
        if key is None or not isinstance(signature, str) or not signature.isascii():
            raise Refused('not_authorized', 'no active verification key or no signature')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(body), signature,
                                                self.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'the signature does not verify')
        return entry, key

    # transitions

    def _new_transition(self, params, before):
        eid, kind, data = params.get('entity_id'), params.get('kind'), params.get('data')
        if not isinstance(eid, str) or kind not in (TERMS_KIND, API_KIND) or not isinstance(data, dict) or eid in before:
            raise self.store.StoreRefused('invalid_input', '%r exists already or is malformed' % (eid,))
        return {eid: {'kind': kind, 'data': data}}

    def _settle_transition(self, params, before):
        """THE terminal transaction: settlement, typed effect, receipt and terminal request state
        together, against the versions the decision read."""
        refused = self.store.StoreRefused
        request, version = params['request_id'], params['request_version']
        sid, eid, rid = settlement_id(request, version), effect_id(request, version), receipt_id(request, version)
        if any(x in before for x in (sid, eid, rid)):
            raise refused('stale_subject', 'this request version is settled')
        current = before.get(request) or {}
        data = current.get('data') or {}
        if (current.get('kind') != self.I.ENTITY_KIND or data.get('request_version') != version
                or data.get('state') not in self.I.PENDING):
            raise refused('stale_subject', 'the request is no longer pending at this version')
        if not all(a in before for a in params['answers']):
            raise refused('stale_subject', 'an answer this settlement counts is not recorded')
        state = data['state']
        for source, destination in zip(TERMINAL_PATH, TERMINAL_PATH[1:]):
            if TERMINAL_PATH.index(source) < TERMINAL_PATH.index(state):
                continue
            ok, why = self.inbox.contract.transition('assignment', source, destination, TERMINAL_EVIDENCE)
            if not ok:
                raise refused('transition_refused', why)
        terminal = dict(data, state=TERMINAL_STATE, answer=params['answer'], settlement=params['reference'])
        # The four writes keep the VELDO-0068 layout (its registered mutation anchors on these lines).
        changes = {sid: {'kind': SETTLEMENT_KIND, 'data': params['settlement']},
                eid: {'kind': EFFECT_KIND, 'data': params['effect']},
                rid: {'kind': RECEIPT_KIND, 'data': params['receipt']},
                request: {'kind': self.I.ENTITY_KIND, 'data': terminal}}
        binding = params.get('binding')
        if binding is not None:
            # VELDO-0069: the governing binding commits with the receipt or not at all.
            if binding['binding_id'] in before:
                raise refused('stale_subject', 'this decision revision is settled')
            if (before.get(binding['decision']) or {}).get('kind') != GOVERNING_RECORD_KIND:
                raise refused('stale_subject', 'the governing decision is not recorded')
            changes[binding['binding_id']] = {'kind': DECISION_SETTLEMENT_KIND, 'data': binding}
        return changes

    # terms: what a request settles and what it requires

    def terms(self, packet):
        """Record one requester-signed terms command: the touchpoint, its target and proposal, and
        the request's own required roles and quorum. Terms are immutable."""
        c = packet.get('command') if isinstance(packet, dict) else None
        c = c if isinstance(c, dict) else {}
        try:
            if (not isinstance(packet, dict) or set(c) != set(TERMS_FIELDS) or c['operation'] != 'terms'
                    or any(c[k] != v for k, v in self.ids.items())
                    or not all(_is_str(c[k]) for k in ('terms', 'principal', 'command_id', 'nonce'))):
                raise Refused('invalid_input', 'a terms command carries exactly the terms fields for this authority')
            if c['touchpoint'] not in JOURNEY:
                raise Refused('unsupported_touchpoint', 'the touchpoint is not enabled in the journey')
            target = c['target']
            if not isinstance(target, dict) or not all(_is_str(target.get(k)) for k in ('kind', 'ref', 'digest')):
                raise Refused('invalid_input', 'the target names its kind, ref and digest')
            if target['kind'] == GOVERNING_TARGET:
                if c['touchpoint'] != GOVERNING_TOUCHPOINT:
                    raise Refused('unsupported_touchpoint', 'a governing decision is settled through decision disposition')
                problem = governing_problem(target)
                if problem:
                    raise Refused(*problem)
            roles = c['required_roles']
            if not isinstance(roles, list) or not all(r in self.AC.ROLES for r in roles):
                raise Refused('invalid_input', 'required_roles lists authority roles')
            if c['quorum'] is not None and not isinstance(c['quorum'], dict):
                raise Refused('invalid_input', 'quorum is a mapping or null')
            if c['proposal'] is not None and not isinstance(c['proposal'], dict):
                raise Refused('invalid_input', 'proposal is a mapping or null')
            self._verified(c['principal'], c, packet.get('signature'), self.AC.BOUNDARIES['proposal_commit'])
            tid = terms_id(self.ids['repository_uuid'], c['terms'])
            data = {'schema': TERMS_SCHEMA, 'terms_id': tid, 'touchpoint': c['touchpoint'], 'target': dict(target),
                    'proposal': c['proposal'], 'required_roles': sorted(set(roles)), 'quorum': c['quorum'],
                    'requested_by': c['principal'], 'command_id': c['command_id'],
                    'domain_uuid': self.ids['domain_uuid'], 'repository_uuid': self.ids['repository_uuid']}
            self._commit(TERMS, c['command_id'], dict(entity_id=tid, kind=TERMS_KIND, data=data), {tid: 0},
                         principal=c['principal'])
        except Refused as exc:
            return self._observe('terms', None, {}, 'refused', exc.code)
        except self.store.StoreRefused as exc:
            return self._observe('terms', None, {}, 'refused', 'invalid_input' if exc.code != 'stale_version' else 'stale_subject')
        except sqlite3.Error:
            return self._observe('terms', None, {}, 'refused', 'unavailable_service')
        return self._observe('terms', None, {tid: 1}, 'recorded', None, terms_id=tid,
                             subject={'kind': SUBJECT_KIND, 'ref': tid, 'digest': digest(data)})

    def _terms(self, data):
        subject = data.get('subject') or {}
        if subject.get('kind') != SUBJECT_KIND:
            raise Refused('missing_terms', 'the request names no settlement terms')
        found = self._entity(subject.get('ref')) if isinstance(subject.get('ref'), str) else None
        if found is None or found['kind'] != TERMS_KIND:
            raise Refused('missing_terms', 'the named terms are not recorded')
        terms = found['data']
        if digest(terms) != subject.get('digest'):
            raise Refused('stale_terms', 'the request binds other terms than the recorded ones')
        if terms.get('requested_by') != data.get('requested_by'):
            raise Refused('missing_terms', 'the terms are another requester\'s')
        touchpoint = terms.get('touchpoint')
        if touchpoint not in JOURNEY or JOURNEY[touchpoint]['assignment_kind'] != data.get('kind'):
            raise Refused('unsupported_touchpoint', 'the request is not a touchpoint of this journey')
        return touchpoint, terms, found['version']

    # answers from the authenticated API

    def api_answer(self, packet):
        """Accept one answer from the authenticated API edge under the presentation rules, then settle."""
        a = packet.get('answer') if isinstance(packet, dict) else None
        a = a if isinstance(a, dict) else {}
        request = a.get('request_id')
        try:
            if (not isinstance(packet, dict) or set(a) != set(API_FIELDS) or a['schema'] != API_SCHEMA
                    or any(a[k] != v for k, v in self.ids.items()) or not _is_str(a['answer_id'])
                    or a['edge'] != self.api_edge or self.api_edge is None):
                raise Refused('invalid_input', 'not an answer from this authority\'s API edge')
            self._verified(a['edge'], a, packet.get('signature'), ('service',))
            item = self.inbox.read(request) if isinstance(request, str) else None
            if item is None or item['data'] is None:
                raise Refused('missing_evidence', 'no valid request')
            if item['data']['state'] not in self.I.PENDING:
                raise Refused('request_closed', 'the request is no longer pending')
            receipt = self.presenter.receipt(a['presentation_id']) if isinstance(a['presentation_id'], str) else None
            if receipt is None or receipt.get('outcome') != 'published' or any(a[k] != receipt[f] for k, f in (
                    ('presentation_digest', 'brief_digest'), ('presentation_version', 'presentation_version'),
                    ('request_id', 'request_id'), ('request_version', 'request_version'))):
                raise Refused('stale_presentation', 'no published presentation is the one this answer names')
            if a['principal'] != receipt['owner']:
                raise Refused('not_owner', 'the principal is not the owner the presentation was shown to')
            self._verified_person(a['principal'])
            head = self.presenter.head(request)
            refusal, current, versions = self.presenter.bindings(request)
            if (head is None or head.get('current') != receipt['presentation_id'] or refusal
                    or self.V.binding_mismatches(receipt, current) or a['request_version'] != item['data']['request_version']):
                raise Refused('stale_presentation', 'the named presentation no longer binds the current request')
            if a['choice'] not in receipt['choices'] or self.V.ruling_of(a['choice']) is None:
                raise Refused('unmatched_choice', 'the answer names no offered choice')
            if not _is_str(a['rationale']):
                raise Refused('missing_rationale', 'an answer records its reasoning')
            eid = api_answer_id(request, a['request_version'], a['edge'], a['answer_id'])
            data = {'schema': API_SCHEMA, 'channel': API_CHANNEL, 'request_id': request,
                    'request_version': a['request_version'], 'presentation_id': a['presentation_id'],
                    'presentation_digest': a['presentation_digest'], 'presentation_version': a['presentation_version'],
                    'principal': a['principal'], 'choice': a['choice'], 'ruling': self.V.ruling_of(a['choice']),
                    'rationale': a['rationale'], 'edge_principal': a['edge'], 'answer_id': a['answer_id'],
                    'assertion': dict(a), 'signature': packet['signature'], 'accepted_at': self.clock()}
            expected = {eid: 0, request: item['version'], a['presentation_id']: receipt['entity_version']}
            self._commit(API, eid, dict(entity_id=eid, kind=API_KIND, data=data), expected, principal=a['edge'])
        except Refused as exc:
            return self._observe('api_answer', request, {}, 'refused', exc.code)
        except self.store.StoreRefused as exc:
            reason = {'stale_version': 'stale_subject', 'nonce_consumed': 'already_answered',
                      'command_content_conflict': 'already_answered'}.get(exc.code, 'invalid_input')
            return self._observe('api_answer', request, {}, 'refused', reason)
        except sqlite3.Error:
            return self._observe('api_answer', request, {}, 'refused', 'unavailable_service')
        self._observe('api_answer', request, expected, 'recorded', None, answer=eid)
        return dict(self.settle(request), answer=eid)

    def _verified_person(self, principal):
        entry = self.AC.membership_entry(self.membership.authority_state(self.store, self.conn)['membership'], principal)
        if not self.AC.active_member(entry, self.clock())[0] or entry.get('principal_type') != 'person':
            raise Refused('not_authorized', 'the answering principal is not an active person member')

    # settlement

    def run(self):
        """Settle every pending request that has an accepted answer at its current version."""
        results = []
        for entry in self.inbox.index()['entries']:
            if entry.get('category') == 'pending' and self.answers(entry['id'], entry['request_version']):
                results.append(self.settle(entry['id']))
        return results

    def settle(self, request):
        try:
            return self._settle(request)
        except Refused as exc:
            return self._observe('settle', request, {}, 'refused', exc.code)
        except self.store.StoreRefused as exc:
            # Another settlement of this version committed first, or an input changed: nothing written.
            reason = {'stale_version': 'stale_subject', 'nonce_consumed': 'already_settled',
                      'command_content_conflict': 'already_settled'}.get(exc.code, 'stale_subject')
            return self._observe('settle', request, {}, 'refused', reason)
        except sqlite3.Error:
            return self._observe('settle', request, {}, 'refused', 'unavailable_service')

    def _answer_problem(self, answer, data, current, head):
        """Why one accepted answer does not count now, or None."""
        if answer.get('principal') != data['owner']:
            return 'not_owner'
        receipt = self.presenter.receipt(answer.get('presentation_id')) if isinstance(answer.get('presentation_id'), str) else None
        if (receipt is None or receipt.get('outcome') != 'published' or head is None
                or head.get('current') != receipt['presentation_id'] or receipt['request_version'] != data['request_version']
                or answer.get('presentation_digest') != receipt['brief_digest']
                or self.V.binding_mismatches(receipt, current)):
            return 'stale_presentation'
        if answer.get('choice') not in receipt['choices'] or answer.get('ruling') != self.V.ruling_of(answer.get('choice')):
            return 'unmatched_choice'
        if not _is_str(answer.get('rationale')) or not isinstance(answer.get('assertion'), dict) \
                or not _is_str(answer.get('signature')):
            return 'missing_rationale'
        return None

    def _authority_problems(self, need, principals, data, state, now):
        codes = []
        for scope in data['scope']:
            ok, why = self.AC.authorize('decision_settlement', {'roles': need['roles'], 'quorum': need['count'],
                                                                'min_independence': need['min_independence'],
                                                                'scope': scope},
                                        [{'principal': p} for p in principals], state['membership'], now)
            codes.extend(r.split(':', 1)[0] for r in why)
        if need['min_independence'] >= 1:
            requester = self.AC.membership_entry(state['membership'], data['requested_by']) or {}
            group = requester.get('independence_group')
            for p in principals:
                entry = self.AC.membership_entry(state['membership'], p) or {}
                if p == data['requested_by'] or (group and entry.get('independence_group') == group):
                    codes.append('independence_not_met')
        names = {'role_not_satisfied': 'role_not_satisfied', 'independence_not_met': 'independence_not_met',
                 'quorum_not_met': 'quorum_not_met'}
        return [names.get(c, 'not_authorized') for c in codes]

    def _settle(self, request):
        item = self.inbox.read(request) if isinstance(request, str) else None
        if item is None or item['data'] is None:
            raise Refused('missing_evidence', 'no valid request')
        data = item['data']
        version = data['request_version']
        sid = settlement_id(request, version)
        if data['state'] not in self.I.PENDING:
            raise Refused('already_settled' if self._entity(sid) is not None else 'request_closed',
                          'the request is not pending')
        touchpoint, terms, terms_version = self._terms(data)
        need = requirement(touchpoint, terms)
        refusal, current, versions = self.presenter.bindings(request)
        if refusal:
            raise Refused('owner_not_current' if refusal == 'missing_authority' else 'stale_presentation', refusal)
        # The answers read here are the ones listed or counted; one accepted after this read commits
        # beside the settlement unlisted and takes no effect (see ONE WINNER).
        answers = self.answers(request, version)
        if not answers:
            raise Refused('no_answer', 'no accepted answer at this request version')
        head = self.presenter.head(request)
        valid, listed = [], []
        for eid, ver, channel, answer in answers:
            why = self._answer_problem(answer, data, current, head)
            if why is None:
                valid.append((eid, ver, channel, answer))
            else:
                listed.append({'answer_id': eid, 'channel': channel, 'principal': answer.get('principal'), 'reason': why})
        if not valid:
            raise Refused(listed[0]['reason'], 'no accepted answer binds the current presentation')
        winner_id, _, channel, winner = valid[0]
        for eid, _ver, other_channel, answer in valid[1:]:
            listed.append({'answer_id': eid, 'channel': other_channel, 'principal': answer.get('principal'),
                           'reason': 'duplicate_principal' if answer.get('choice') == winner.get('choice')
                           else 'conflicting_ruling'})
        principals = sorted({answer['principal'] for _e, _v, _c, answer in valid})
        now = self.clock()
        state = self.membership.authority_state(self.store, self.conn)
        problems = self._authority_problems(need, principals, data, state, now)
        if problems:
            raise Refused(problems[0], ';'.join(problems))
        receipt = self.presenter.receipt(winner['presentation_id'])
        eff, rec = effect_id(request, version), receipt_id(request, version)
        ruling, choice = winner['ruling'], winner['choice']
        bound = (self._binding(terms, request, version, principals, winner, now)
                 if terms['target'].get('kind') == GOVERNING_TARGET else None)
        settlement = {'schema': SCHEMA, 'settlement_id': sid, 'request_id': request, 'request_version': version,
                      'request_digest': receipt['request_digest'], 'touchpoint': touchpoint,
                      'terms_id': terms['terms_id'], 'terms_digest': digest(terms), 'requirement': need,
                      'choice': choice, 'ruling': ruling, 'rationale': winner['rationale'], 'principals': principals,
                      'originating_channel': channel, 'answer_id': winner_id, 'assertion': winner['assertion'],
                      'signature': winner['signature'], 'edge_principal': winner.get('edge_principal'),
                      'presentation_id': receipt['presentation_id'], 'presentation_digest': receipt['brief_digest'],
                      'presentation_version': receipt['presentation_version'], 'not_counted': listed,
                      'effect_id': eff, 'receipt_id': rec, 'nonce': sid, 'settled_at': now}
        if bound is not None:
            settlement['binding_id'] = bound['data']['binding_id']
        effect = {'schema': EFFECT_SCHEMA, 'effect_id': eff, 'type': JOURNEY[touchpoint]['effects'][ruling],
                  'touchpoint': touchpoint, 'target': terms['target'],
                  'proposal': terms['proposal'] if ruling == 'approve' else None, 'choice': choice, 'ruling': ruling,
                  'rationale': winner['rationale'], 'principals': principals, 'request_id': request,
                  'request_version': version, 'settlement_id': sid, 'state': 'obligated'}
        receipt_data = {'schema': RECEIPT_SCHEMA, 'receipt_id': rec, 'settlement_id': sid,
                        'settlement_digest': digest(settlement), 'effect_ids': [eff], 'request_id': request,
                        'request_version': version, 'terminal_state': TERMINAL_STATE, 'nonce': sid,
                        'originating_channel': channel, 'settled_at': now}
        if bound is not None:
            receipt_data['binding_id'] = bound['data']['binding_id']
        answer = {'principal': winner['principal'], 'ruling': choice, 'request_version': version,
                  'command_id': winner_id, 'command': winner['assertion'], 'signature': winner['signature'],
                  'key_id': winner.get('edge_key_id') or winner.get('edge_principal'), 'accepted_at': winner['accepted_at']}
        reference = {'settlement_id': sid, 'receipt_id': rec, 'effect_id': eff, 'request_version': version,
                     'ruling': ruling, 'choice': choice}
        expected = dict(versions)
        expected.update({sid: 0, eff: 0, rec: 0, terms['terms_id']: terms_version, request: item['version'],
                         receipt['presentation_id']: receipt['entity_version'],
                         self.V.head_id(request): head['entity_version']})
        expected.update({eid: ver for eid, ver, _c, _a in answers})
        params = dict(request_id=request, request_version=version, settlement=settlement, effect=effect,
                      receipt=receipt_data, answer=answer, reference=reference, answers=[e for e, _v, _c, _a in answers])
        extra = {}
        if bound is not None:
            params['binding'] = bound['data']
            expected.update(bound['expected'])
            extra = dict(binding_id=bound['data']['binding_id'], decision=bound['data']['decision'],
                         binding_current=not bound['currency'], binding_refusals=bound['currency'])
        self._commit(SETTLE, sid, params, expected)
        return self._observe('settle', request, expected, 'settled', None, settlement_id=sid, receipt_id=rec,
                             effect_id=eff, touchpoint=touchpoint, ruling=ruling, originating_channel=channel,
                             not_counted=len(listed), **extra)

    def _binding(self, terms, request, version, principals, winner, now):
        """VELDO-0069: the governing binding of a settled governing decision question, signed, with the
        versions it pins and the named blockers the consumers will raise against it now (empty when it is
        the record's current exact binding). The body is the question the owner was shown, never the
        record as it stands at settlement. Refused by name, before anything is written, when the question
        or record is not one this release binds or no decision signer is configured."""
        target = terms['target']
        problem = governing_problem(target)
        if problem:
            raise Refused(*problem)
        if self.decision_signer is None:
            raise Refused('unavailable_service', 'no decision signer is configured: a governing decision is never '
                                                 'settled without its binding')
        rid, question = target['ref'], governing_question(target)
        found = self._entity(rid)
        record = found['data'] if found is not None and found['kind'] == GOVERNING_RECORD_KIND else None
        if not isinstance(record, dict) or record.get('schema') != DD.GOVERNING_SCHEMA or DD.record_invalid(rid, record):
            raise Refused('missing_decision', 'the request names no recorded governing decision')
        kind = record['subject']['kind']
        if kind not in DD.SUBJECT_KINDS:
            raise Refused('unsupported_subject', 'the governed subject kind %r is not bound in this release' % kind)
        if question['revision'] > record['revision']:
            # The record read here is pinned at its version in the settling transaction (expected below).
            raise Refused('future_revision', 'the question names revision %d; the record is at revision %d'
                          % (question['revision'], record['revision']))
        bid = binding_id(rid, question['revision'])
        if self._entity(bid) is not None:
            raise Refused('already_settled', 'this decision revision is settled')
        at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))
        body = {'schema': DD.SETTLEMENT_SCHEMA, 'domain_uuid': self.ids['domain_uuid'],
                'decision_id': question['decision_id'], 'decision_revision': question['revision'],
                'framing_digest': question['framing_digest'], 'subject': dict(question['subject']),
                'scope_digest': question['scope_digest'], 'ruling': winner['ruling'], 'request_id': request,
                'request_version': version, 'principals': list(principals), 'settled_at': at}
        principal, sign = self.decision_signer
        signature = sign(DD.settlement_bytes(body))
        if not _is_str(signature):
            raise Refused('unavailable_service', 'the decision signer returned no signature')
        data = {'schema': DD.SETTLEMENT_SCHEMA, 'binding_id': bid, 'decision': rid, 'settlement': body,
                'signer': principal, 'signature': signature, 'choice': winner['choice'],
                'decided_by': list(principals), 'decided_at': at, 'settlement_id': settlement_id(request, version),
                'receipt_id': receipt_id(request, version), 'terms_id': terms['terms_id']}
        if question['revision'] != record['revision']:
            currency = ['unbound_decision:%s/revision' % rid]
        else:
            subject = self._entity(DD.subject_entity(record['subject']))
            current = DD.subject_digest(kind, subject['data'] if subject is not None else None)
            currency = DD.binding_problems(rid, record, body, current, self.ids['domain_uuid'])
        return {'data': data, 'expected': {bid: 0, rid: found['version']}, 'currency': currency}

    # the published state

    def statuses(self):
        """The accepted revision statuses of every settled request: {path: entity id}."""
        found = {}
        for s in self.settlements():
            request = self._data(s['request_id'], self.I.ENTITY_KIND) or {}
            if request.get('settlement', {}).get('settlement_id') == s['settlement_id']:
                settled, state = status_paths(request['alias'])
                found[settled] = s['settlement_id']
                found[state] = s['request_id']
        return found

    def publish(self, revisions, reader, revision_id, commit, documents, snapshot_id, destination, principal):
        """Accept a VELDO-0035 revision whose statuses are the settled requests, accept its snapshot and
        materialize it at `destination`; returns the manifest. `revisions` and `reader` are the VELDO-0035
        services attached to a publication connection of this same store, never this service's own, so
        the read set they register governs publication only."""
        if reader.conn is self.conn or revisions.conn is not reader.conn:
            raise Refused('invalid_input', 'publication runs on its own connection to this store')
        SN = _sibling('settlement_snapshot', 'control_snapshot.py')
        signing = dict(signer=self.journal_signer, sign=self.sign, authority_generation=self.authority_generation)
        revisions.accept(revision_id, self.ids['repository_uuid'], commit, principal, documents, self.statuses(), **signing)
        if 'record_receipt' not in reader.registrations:
            reader.enable('record_receipt', {'revision': '$revision', 'entities': {},
                                             'collections': {'settlements': {'kind': SETTLEMENT_KIND, 'where': {}}}})
        reader.execute({'command_id': 'settlement-snapshot:' + snapshot_id, 'principal': principal,
                        'operation': 'accept_snapshot', 'artifact_digests': [], 'nonce': 'settlement-snapshot:' + snapshot_id,
                        'parameters': {'snapshot_id': snapshot_id, 'operation': 'record_receipt',
                                       'arguments': {'revision': revision_id}},
                        'expected_versions': {snapshot_id: 0}}, **signing)
        snapshot = SN.load(self.store, reader.conn, snapshot_id, self.ids['domain_uuid'], self.ids['repository_uuid'])
        return SN.materialize(snapshot, reader.repo, destination)

    def metrics(self):
        """Accepted and refused operations, settled request versions, and the pending work: pending
        requests with an accepted answer that has not settled, by the refusal settling them names."""
        pending, blocked = 0, {}
        last = {}
        for o in self.observations:
            if o['operation'] == 'settle':
                last[o['request_id']] = o.get('reason')
        for entry in self.inbox.index()['entries']:
            if entry.get('category') == 'pending' and self.answers(entry['id'], entry['request_version']):
                pending += 1
                reason = last.get(entry['id']) or 'not_attempted'
                blocked[reason] = blocked.get(reason, 0) + 1
        bound = self.conn.execute('SELECT count(*) FROM entities WHERE kind=?', (DECISION_SETTLEMENT_KIND,)).fetchone()[0]
        return dict(self.counts, settled=len(self.settlements()), bound=bound, pending=pending, pending_by_reason=blocked)


def published_state(members, alias):
    """A request's state as a published snapshot holds it: from the settlement statuses only. `members`
    are the bytes read_materialized returned. A request without them is not settled in that snapshot."""
    settled, state = status_paths(alias)
    if settled not in members or state not in members:
        return {'settled': False}
    s, r = json.loads(members[settled]), json.loads(members[state])
    sdata, rdata = s.get('data') or {}, r.get('data') or {}
    return {'settled': s.get('kind') == SETTLEMENT_KIND and rdata.get('settlement', {}).get('settlement_id') == sdata.get('settlement_id'),
            'state': rdata.get('state'), 'request_version': rdata.get('request_version'),
            'settlement_id': sdata.get('settlement_id'), 'receipt_id': sdata.get('receipt_id'),
            'settlement_version': s.get('version'), 'ruling': sdata.get('ruling'), 'choice': sdata.get('choice')}
