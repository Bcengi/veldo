"""One intake for owner messages from Telegram and the authenticated API (VELDO-0126, PLAN-0019 W89).

WHAT THIS MODULE IS. The common intake operation that turns an owner's message into a proposal. There
are exactly two source kinds, `telegram_message` and `api_request`, and each has one adapter. Both
adapters build the same normalized intake command (source kind and identity, the exact text, the
authenticated principal, the requested project and the proposal it clarifies, plus the source's own
provenance) and hand it to the one common service, `_submit`, whose store command `intake_record` is
the only writer of intake sources, proposals and questions (control_store.declare_owners). Nothing
else in this module writes to the store except `intake_question_asked`, which records where a
question was delivered.

ONE PUBLIC ATTESTED SUBMISSION (VELDO-0133). A person's signed answer elsewhere (a disposition
question's `other`) carries an instruction the person signed and names the source it arrived on.
`submit_attested` takes it only after this intake authenticates that source itself, exactly as its
adapters do: a `telegram_message` source is the id of kept VELDO-0066 evidence, attributed again by
the Acquirer, whose sender must resolve to the answering person in that person's own private chat;
an `api_request` source is the request packet the API edge signed, verified by the API adapter,
whose principal must be the answering person. Only then does the common service take the signed
instruction as the text, the caller's project, and the source's own provenance with the caller's
(the question and the answer command identities) beside it. The caller never supplies a source
identity, a chat or a sender, and nothing else reaches `_submit` from outside this module.

WHO IS SPEAKING. A Telegram message counts only as the VELDO-0066 Acquirer attributes it: kept
canonical evidence, a person account in person, in that person's own private chat, mapped by the
stable sender id to one enrolled, active person member. The attribution is re-derived from the kept
evidence each time, never read from a label, a display name or anything written in the text. Only an
ordinary message is intake: one that replies to nothing, or replies to a message that is not a
presentation (the owner's own earlier message, or a question this module asked). An answer to a
presentation belongs to settlement, never to intake. An API request counts only when it is signed by
the configured API edge principal (the authenticated API of VELDO-0130, a trusted channel edge) with
its active key in the store's keyring, and the principal it asserts is an active person member. Both
sources then pass the same person check, the Acquirer's, inside the store transaction. Authority
holds at both ends: a Telegram message whose sender was not a member at the message's platform date
stays refused after the sender is enrolled, read from the effective time of the key the enrollment
wrote (VELDO-0025 keeps none on the membership entity).

THE TEXT IS KEPT AS WRITTEN. No ticket identifier, command syntax or structure is required, and the
text is never trimmed or rewritten. A ticket link in the text is data an agent may fetch later with
its configured tools; intake fetches nothing and watches nothing.

PROJECT CONTEXT. The candidate projects are the configured projects the principal's membership scope
covers. The project is the one the API request names (it must be a candidate), else the one candidate
the text names as a word, else the principal's only candidate. When none of these decides, intake does
not choose: it keeps an inbox proposal and a question naming the candidates. A Telegram question is
sent back as a reply to the owner's message through the VELDO-0065 edge; an API question is the
response. A follow-up that clarifies a proposal (a Telegram reply to the original message or to the
question, or an API request naming the proposal) is kept with its own source. It resolves an inbox
proposal into a proposed objective when it names one of the question's candidates, and is otherwise
kept on the proposal it clarifies. A follow-up to an inbox proposal already resolved lands on the
objective it was resolved to, never on the retired inbox record.

ONE REPLY ABOUT WAITING REQUESTS (VELDO-0136). A Telegram message the Acquirer refused as replying
to no presentation (NOT_A_REPLY) gets its one decision here, after intake has seen it, and at most one
bot reply, through the presenter's `hint_owner`: a message intake takes as a clarification or as the
answer to its own question gets none; one taken as a new proposal while requests of the owner wait
gets one note that it was taken as new work, not as an answer, naming the waiting requests, merged
into the project question when intake asks one; the plain hint goes only to a message intake does not
take. Each waiting request version is named once, and a later pass never decides a message again.

INTAKE PROPOSES AND NOTHING ELSE. It writes only intake sources, proposals (state PROPOSED,
AWAITING_PROJECT or RESOLVED) and questions: never an execution unit, a backlog item, an admission, a
priority, a claim, a reservation or an effect. Admission and priority are later owner decisions.

ONE SOURCE REQUEST, ONE PROPOSAL. A source's identity (bot, chat and message id; or the API request
id) names one intake source record. The same request again with the same content returns the proposal
it produced and writes nothing; changed content under the same identity, a Telegram edit included, is
refused `identity_conflict` and the record is unchanged.

WHAT IT IS NOT. Not the API server (VELDO-0130), not Jira intake, polling or webhooks (dropped by the
owner), not elaboration, admission or priority, and not redelivery or outage recovery (Release 2).
Observations carry identities, versions and outcomes, never the token or key material. Standard
library only.
"""
import hashlib
import json
import sqlite3
import time

COMMAND_SCHEMA = 'veldo.intake_command/v1'
API_SCHEMA = 'veldo.intake_api_request/v1'
SOURCE_SCHEMA = 'veldo.intake_source/v1'
PROPOSAL_SCHEMA = 'veldo.intake_proposal/v1'
QUESTION_SCHEMA = 'veldo.intake_question/v1'
SOURCE_KINDS = ('telegram_message', 'api_request')
SOURCE_KIND, PROPOSAL_KIND, QUESTION_KIND = 'intake_source', 'intake_proposal', 'intake_question'
RECORD, ASKED = 'intake_record', 'intake_question_asked'
OWNER = 'VELDO-0126 intake'
WRITES = ('entities', 'journal', 'commands', 'nonces')
COMMAND_FIELDS = ('schema', 'source_kind', 'source_id', 'principal', 'text', 'project', 'clarifies', 'provenance')
API_FIELDS = ('schema', 'domain', 'request_id', 'edge', 'principal', 'text', 'project', 'clarifies')
PROPOSAL_STATES = ('PROPOSED', 'AWAITING_PROJECT', 'RESOLVED')
# The attribution's own reasons for a message it attributed to a person but that is no presentation
# answer: it replies to nothing, or to a message that is not a presentation.
ORDINARY = ('missing_reply_reference', 'unknown_presentation')
EVIDENCE_KIND = 'channel_evidence'  # VELDO-0066's kept Telegram evidence
TEXT_LIMIT = 16384
ID_LIMIT = 128
PUNCTUATION = ',.;:!?()[]{}"\'<>'
TAXONOMY = {'unauthenticated': 'unauthenticated', 'unauthorized': 'unauthorized', 'identity_conflict': 'stale_version',
            'stale_version': 'stale_version', 'unsupported_source': 'unsupported_configuration',
            'not_intake': 'unsupported_configuration', 'invalid_input': 'unsupported_configuration',
            'missing_evidence': 'missing_evidence', 'unavailable_service': 'unavailable_service',
            'unknown_outcome': 'unknown_outcome', 'channel_refused': 'unavailable_service'}


class Refused(Exception):
    """A named refusal; nothing was written."""

    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


class _Repeated(Exception):
    """The same source request with the same content: its recorded result, nothing written."""

    def __init__(self, record):
        self.record = record
        super().__init__('repeated')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()


def _hex(*parts):
    return hashlib.sha256(canonical(list(parts))).hexdigest()[:32]


def source_key(kind, source_id):
    return 'intake_source:' + _hex(kind, source_id)


def proposal_id(key):
    return 'intake_proposal:' + _hex('proposal', key)


def question_id(key):
    return 'intake_question:' + _hex('question', key)


def telegram_source_id(bot, chat, message):
    return '%d:%d:%d' % (bot, chat, message)


def content_digest(command):
    """The content under a source identity: everything the command asks for, without provenance."""
    return digest({k: command[k] for k in COMMAND_FIELDS if k != 'provenance'})


def named_projects(text, candidates):
    """The candidates the text names as a whole word, compared without case."""
    words = {w.strip(PUNCTUATION).casefold() for w in text.split()}
    return [p for p in candidates if p.casefold() in words]


def _identifier(value):
    return type(value) is str and 0 < len(value) <= ID_LIMIT and value.isascii() and value.isprintable()


def command_problem(command):
    """Why a normalized intake command is malformed, or None."""
    if not isinstance(command, dict) or set(command) != set(COMMAND_FIELDS) or command['schema'] != COMMAND_SCHEMA:
        return 'invalid_input:command'
    if command['source_kind'] not in SOURCE_KINDS:
        return 'unsupported_source'
    if not _identifier(command['source_id']) or not _identifier(command['principal']):
        return 'invalid_input:identity'
    text = command['text']
    if type(text) is not str or not text.strip() or len(text) > TEXT_LIMIT:
        return 'invalid_input:text'
    if command['project'] is not None and not _identifier(command['project']):
        return 'invalid_input:project'
    if command['clarifies'] is not None and not _identifier(command['clarifies']):
        return 'invalid_input:clarifies'
    if not isinstance(command['provenance'], dict):
        return 'invalid_input:provenance'
    return None


class Intake:
    """The intake of one domain over a real control store connection.

    `store`, `membership` and `contract` are the control_store, control_membership and
    authority_contract modules; `acquirer` is the VELDO-0066 Acquirer on the same connection (its
    evidence, attribution and person check are used as they are); `asker` is a VELDO-0065
    TelegramPresentationEdge for the bot the Acquirer serves, or None. `projects` are the projects
    this intake serves. `api_edge` is the service principal the authenticated API signs as. `sign`
    signs journal records as `journal_signer`."""

    def __init__(self, store, membership, contract, acquirer, conn, *, domain, projects, api_edge, journal_signer,
                 sign, asker=None, authority_generation=1, clock=time.time, observe=None):
        if not _identifier(domain) or not _identifier(api_edge) or not _identifier(journal_signer):
            raise Refused('invalid_input', 'domain, API edge and journal signer are named')
        if not projects or not all(_identifier(p) for p in projects) or len(set(projects)) != len(projects):
            raise Refused('invalid_input', 'the served projects are named once each')
        self.store, self.CM, self.AC, self.acquirer, self.conn = store, membership, contract, acquirer, conn
        self.domain, self.projects, self.api_edge = domain, tuple(projects), api_edge
        self.journal_signer, self.sign, self.generation = journal_signer, sign, authority_generation
        self.asker, self.clock = asker, clock
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._adapters = {'telegram_message': self._telegram, 'api_request': self._api}
        store.declare_owners(conn, OWNER, kinds={SOURCE_KIND: (RECORD,), PROPOSAL_KIND: (RECORD,),
                                                 QUESTION_KIND: (RECORD, ASKED)}, module=__file__)
        conn.command_registry[RECORD] = {'transaction_transition': self._record_transition, 'writes': WRITES}
        conn.command_registry[ASKED] = {'transaction_transition': self._asked_transition, 'writes': WRITES}

    # reading

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def _data(self, eid, kind):
        row = self._entity(eid) if type(eid) is str else None
        return row['data'] if row is not None and row['kind'] == kind else None

    def source(self, kind, source_id):
        return self._data(source_key(kind, source_id), SOURCE_KIND)

    def proposal(self, pid):
        return self._data(pid, PROPOSAL_KIND)

    def question(self, qid):
        return self._data(qid, QUESTION_KIND)

    def _all(self, kind):
        return [json.loads(t) for (t,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (kind,))]

    # observability

    def _event(self, operation, outcome, reason=None, **fields):
        accepted = reason is None
        self.counts['accepted' if accepted else 'refused'] += 1
        event = dict({'schema': SOURCE_SCHEMA, 'operation': operation, 'domain': self.domain, 'outcome': outcome,
                      'refusal': reason, 'taxonomy': None if accepted else taxonomy(reason)}, **fields)
        self.observations.append(event)
        self.observe(event)
        result = {'outcome': outcome}
        if reason is not None:
            result['reason'] = reason
        result.update({k: fields[k] for k in ('source', 'proposal_id', 'question_id', 'question', 'repeated',
                                              'command') if k in fields})
        return result

    def metrics(self):
        """Accepted and refused operations, refusals by reason, and the pending work: proposals
        awaiting their owner's grooming and open questions awaiting an answer."""
        refused = {}
        for e in self.observations:
            if e['refusal'] is not None:
                refused[e['refusal']] = refused.get(e['refusal'], 0) + 1
        proposals = self._all(PROPOSAL_KIND)
        return dict(self.counts, refused_by_reason=refused,
                    pending={'proposed': sum(1 for p in proposals if p.get('state') == 'PROPOSED'),
                             'awaiting_project': sum(1 for p in proposals if p.get('state') == 'AWAITING_PROJECT'),
                             'open_questions': sum(1 for q in self._all(QUESTION_KIND) if q.get('state') == 'open')})

    # the entry

    def receive(self, source_kind, payload):
        """Take one message from an allowed source: `telegram_message` with the id of kept VELDO-0066
        evidence, or `api_request` with {request, signature} from the authenticated API. Anything else
        is refused `unsupported_source`."""
        adapter = self._adapters.get(source_kind) if isinstance(source_kind, str) else None
        if adapter is None:
            return self._event('receive', 'refused', 'unsupported_source', source_kind=str(source_kind)[:64])
        try:
            command = adapter(payload)
        except Refused as error:
            result = self._event('receive', 'refused', error.code, source_kind=source_kind)
        else:
            result = self._submit(command)
        if source_kind == 'telegram_message' and type(payload) is str:
            result['evidence_id'] = payload
            # The one decision about what the owner is told, now that intake has seen the message: a
            # proposal gets the new-work note, a message intake did not take the plain hint; an inbox
            # proposal's note rides on its question (_ask); a clarification or a resolution gets none.
            if not result.get('repeated') and result.get('outcome') in ('proposed', 'refused'):
                self._hint(payload, 'proposed' if result['outcome'] == 'proposed' else None)
        return result

    def take_telegram(self):
        """Every kept Telegram update that is not a recorded presentation answer, in update order, each
        attributed again by the intake's own reading. A message already taken returns its recorded
        result; every other update is refused by name and nothing is written for it."""
        rows = [r for r in self._all(EVIDENCE_KIND) if r.get('outcome') in ('acquired', 'refused')]
        return [self.receive('telegram_message', r['evidence_id'])
                for r in sorted(rows, key=lambda r: (r.get('bot_id') or 0, r.get('update_id') or 0))]

    # the two adapters

    def _telegram(self, evidence):
        record = self.acquirer.evidence(evidence) if type(evidence) is str else None
        if record is None:
            raise Refused('missing_evidence', 'no kept Telegram evidence %r' % (evidence,))
        refusal, known = self.acquirer.attribute(record)
        if refusal == 'edited_message':
            raise Refused('identity_conflict:edited_message', 'an edit never changes a retained message')
        if refusal is None:
            raise Refused('not_intake:presentation_answer', 'an answer to a presentation is settlement\'s')
        if known['principal'] is None:
            raise Refused('unauthenticated:' + str(refusal), record['evidence_id'])
        if refusal in ('not_current_member', 'not_a_person'):
            raise Refused('unauthorized:' + refusal, record['evidence_id'])
        if refusal not in ORDINARY:
            raise Refused('not_intake:' + str(refusal), 'a reply bound for a presentation is settlement\'s')
        fields, message = record['fields'], record['source']['message']
        text = message.get('text')
        if type(text) is not str:
            raise Refused('invalid_input:text', 'the message carries no text')
        bot, chat = record['bot_id'], fields['chat_id']
        clarifies = None
        if fields.get('reply_to_message_id') is not None:
            clarifies = self._replied_proposal(bot, chat, fields['reply_to_message_id'])
        return {'schema': COMMAND_SCHEMA, 'source_kind': 'telegram_message',
                'source_id': telegram_source_id(bot, chat, fields['message_id']), 'principal': known['principal'],
                'text': text, 'project': None, 'clarifies': clarifies,
                'provenance': {'channel': 'telegram_chat', 'bot_id': bot, 'chat_id': chat, 'message_id': fields['message_id'],
                               'update_id': fields['update_id'], 'date': fields['date'],
                               'evidence_id': record['evidence_id'], 'evidence_digest': record['source_digest'],
                               'reply_to_message_id': fields.get('reply_to_message_id')}}

    def _replied_proposal(self, bot, chat, message):
        """The proposal a Telegram reply clarifies: the one its replied message was taken into, or the
        one whose question was delivered as that message; None for any other message."""
        taken = self.source('telegram_message', telegram_source_id(bot, chat, message))
        if taken is not None:
            return taken['proposal_id']
        for q in self._all(QUESTION_KIND):
            where = q.get('delivery') or {}
            if (where.get('channel') == 'telegram_chat' and where.get('bot_id') == bot and where.get('chat_id') == chat
                    and where.get('message_id') == message):
                return q['proposal_id']
        return None

    def _api(self, packet):
        request = packet.get('request') if isinstance(packet, dict) else None
        signature = packet.get('signature') if isinstance(packet, dict) else None
        if not isinstance(request, dict) or set(request) != set(API_FIELDS) or request['schema'] != API_SCHEMA:
            raise Refused('invalid_input:request', 'an API intake request carries exactly its fields')
        if request['domain'] != self.domain:
            raise Refused('unauthorized:domain', 'the request names another domain')
        if not isinstance(signature, str) or not signature.isascii() or not signature.strip():
            raise Refused('unauthenticated:signature', 'the request is not signed')
        if request['edge'] != self.api_edge:
            raise Refused('unauthenticated:edge', 'the request is not carried by the authenticated API')
        if not self._edge_verifies(request, signature):
            raise Refused('unauthenticated:signature', 'the signature is not the API edge\'s')
        if not _identifier(request['request_id']):
            raise Refused('invalid_input:request_id', 'a request id is printable ASCII, at most %d' % ID_LIMIT)
        return {'schema': COMMAND_SCHEMA, 'source_kind': 'api_request', 'source_id': request['request_id'],
                'principal': request['principal'], 'text': request['text'], 'project': request['project'],
                'clarifies': request['clarifies'],
                'provenance': {'channel': 'api', 'edge': request['edge'], 'request_id': request['request_id'],
                               'request_digest': digest(request)}}

    def _edge_verifies(self, request, signature):
        """The request is signed by the API edge's active key in the store's keyring, and the edge is
        an active service member."""
        AC, now = self.AC, self.clock()
        state = self.CM.authority_state(self.store, self.conn)
        entry = AC.membership_entry(state['membership'], self.api_edge)
        if not AC.active_member(entry, now)[0] or entry.get('principal_type') != 'service':
            return False
        key = AC.active_key(state['keyring'], self.api_edge, now)
        if key is None:
            return False
        verified, _detail = AC.ssh_keygen_verify(self.store.canonical_bytes(request), signature,
                                                 AC.allowed_signers_line(self.api_edge, key['public_key']), self.api_edge)
        return bool(verified)

    # the attested submission (VELDO-0133)

    def submit_attested(self, source_kind, evidence, *, principal, text, project, provenance):
        """Submit `text`, which `principal` signed in an answer elsewhere, under the source it arrived
        on, once this intake has authenticated that source itself: `evidence` is the id of kept
        VELDO-0066 evidence for `telegram_message`, or the {request, signature} packet the API edge
        signed for `api_request`. The source identity, the chat and the sender come only from that
        evidence, never from the caller. `provenance` (the caller's question and answer command
        identities) is kept beside the source's own. Anything else is refused by name and nothing is
        written; otherwise the common service's result is returned."""
        about = dict(source_kind=str(source_kind)[:64], principal=principal if _identifier(principal) else None)
        if not _identifier(principal) or not isinstance(provenance, dict):
            return self._event('attest', 'refused', 'invalid_input:attested', **about)
        try:
            if source_kind == 'telegram_message':
                source_id, trace = self._attest_telegram(evidence, principal)
            elif source_kind == 'api_request':
                source_id, trace = self._attest_api(evidence, principal)
            else:
                raise Refused('unsupported_source', str(source_kind)[:64])
        except Refused as error:
            return self._event('attest', 'refused', error.code, **about)
        return self._submit({'schema': COMMAND_SCHEMA, 'source_kind': source_kind, 'source_id': source_id,
                             'principal': principal, 'text': text, 'project': project, 'clarifies': None,
                             'provenance': dict(trace, attested=dict(provenance))})

    def _attest_telegram(self, evidence, principal):
        """(source id, provenance) of kept Telegram evidence the Acquirer attributes to `principal`:
        the sender resolves to that person in the person's own private chat, re-derived from the kept
        platform update. An answer to a presentation counts as well as an ordinary message: the source
        is the message, and the text is the signed instruction, not the message's."""
        record = self.acquirer.evidence(evidence) if type(evidence) is str else None
        if record is None:
            raise Refused('missing_evidence', 'no kept Telegram evidence %r' % (str(evidence)[:ID_LIMIT],))
        refusal, known = self.acquirer.attribute(record)
        if refusal == 'edited_message':
            raise Refused('identity_conflict:edited_message', 'an edit never changes a retained message')
        # The attribution names a principal only for a person's own private chat with the bot.
        if known['principal'] is None:
            raise Refused('unauthenticated:' + str(refusal), record['evidence_id'])
        if refusal in ('not_current_member', 'not_a_person'):
            raise Refused('unauthorized:' + refusal, record['evidence_id'])
        if known['principal'] != principal:
            raise Refused('unauthorized:not_the_answering_person', record['evidence_id'])
        fields, bot = record['fields'], record['bot_id']
        return telegram_source_id(bot, fields['chat_id'], fields['message_id']), {
            'channel': 'telegram_chat', 'bot_id': bot, 'chat_id': fields['chat_id'], 'message_id': fields['message_id'],
            'update_id': fields['update_id'], 'date': fields['date'], 'evidence_id': record['evidence_id'],
            'evidence_digest': record['source_digest'], 'reply_to_message_id': fields.get('reply_to_message_id')}

    def _attest_api(self, packet, principal):
        """(source id, provenance) of a request the API adapter verifies as the API edge's, whose
        principal is `principal`."""
        command = self._api(packet)
        if command['principal'] != principal:
            raise Refused('unauthorized:not_the_answering_person', command['source_id'])
        return command['source_id'], command['provenance']

    # the common service

    def _submit(self, command):
        """THE INTAKE: one normalized command from either adapter becomes a proposal, an inbox proposal
        and its question, or a clarification, in one store transaction."""
        problem = command_problem(command)
        about = dict(source_kind=command.get('source_kind') if isinstance(command, dict) else None,
                     source_id=command.get('source_id') if isinstance(command, dict) else None,
                     principal=command.get('principal') if isinstance(command, dict) else None)
        if problem:
            return self._event('submit', 'refused', problem, **about)
        key = source_key(command['source_kind'], command['source_id'])
        about.update(source=key, trace=dict(command['provenance']))
        try:
            changes, reads, result = self._plan(command, self._entity)
        except _Repeated as repeat:
            done = repeat.record['result']
            return self._event('submit', done['outcome'], None, repeated=True, command=repeat.record['command'],
                               **dict(about, **{k: done[k] for k in ('proposal_id', 'question_id', 'question') if k in done}))
        except Refused as error:
            return self._event('submit', 'refused', error.code, **about)
        expected = {eid: (self._entity(eid) or {}).get('version', 0) for eid in sorted(set(changes) | set(reads))}
        params = {'command': command, 'content_digest': content_digest(command)}
        cid = 'intake:' + _hex(key, params['content_digest'])
        try:
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation=RECORD,
                                               parameters=params, expected_versions=expected, artifact_digests=[],
                                               nonce=cid), self.journal_signer, self.sign, self.generation)
        except Refused as error:
            return self._event('submit', 'refused', error.code, accepted_versions=expected, **about)
        except self.store.StoreRefused as error:
            return self._event('submit', 'refused', error.code, accepted_versions=expected, **about)
        except sqlite3.Error:
            return self._event('submit', 'refused', 'unavailable_service', accepted_versions=expected, **about)
        done = self._event('submit', result['outcome'], None, accepted_versions=expected, project=result.get('project'),
                           command=command, **dict(about, **{k: result[k] for k in ('proposal_id', 'question_id', 'question')
                                                             if k in result}))
        if result['outcome'] == 'inbox' and command['source_kind'] == 'telegram_message':
            self._ask(result['question_id'], command)
        return done

    def _record_transition(self, conn, params, before):
        """intake_record: re-plan inside the transaction on its own connection; the plan's writes are
        the transaction's, and a plan that now differs from the one the command declared refuses."""
        command = params.get('command')
        if command_problem(command) or params.get('content_digest') != content_digest(command):
            raise Refused('invalid_input:command', 'the recorded command is not the normalized command')
        try:
            changes, _reads, _result = self._plan(command, self._entity)
        except _Repeated:
            raise Refused('stale_version', 'the source request was recorded meanwhile') from None
        return changes

    def _plan(self, command, read):
        """(changes, reads, result) for one normalized command, from what `read` returns now."""
        key = source_key(command['source_kind'], command['source_id'])
        principal, text = command['principal'], command['text']
        existing = read(key)
        if existing is not None:
            if existing['kind'] == SOURCE_KIND and existing['data'].get('content_digest') == content_digest(command):
                raise _Repeated(existing['data'])
            raise Refused('identity_conflict', key)
        why = self.acquirer._person(principal)
        if why:
            raise Refused('unauthorized:' + why, principal)
        # Authority holds both when the message was sent and now: a Telegram message sent before its
        # sender was a member stays refused after the sender is enrolled.
        # An API request carries no send time of its own; it is authorized as the edge delivers it.
        if command['source_kind'] == 'telegram_message':
            why = self._member_when_sent(principal, command['provenance'].get('date'))
            if why:
                raise Refused('unauthorized:' + why, principal)
        member = read(principal)
        scope = member['data'].get('scope') if member is not None and member['kind'] == 'membership' else None
        candidates = [p for p in self.projects if self.CM.scope_covers(scope, p)]
        if not candidates:
            raise Refused('unauthorized:no_project', principal)
        explicit = command['project']
        if explicit is not None and explicit not in candidates:
            raise Refused('unauthorized:project', explicit)
        named = named_projects(text, candidates)
        context = {'domain': self.domain, 'candidates': candidates, 'membership_version': member['version']}
        pid = proposal_id(key)
        source = {'schema': SOURCE_SCHEMA, 'source_id': key, 'source_kind': command['source_kind'],
                  'source_ref': command['source_id'], 'principal': principal, 'text': text,
                  'content_digest': content_digest(command), 'command': command, 'context': context}
        changes, reads = {}, [principal]
        clarifies = command['clarifies']
        if clarifies is not None:
            live, target = self._live_proposal(clarifies, principal, read, reads)
            data = dict(target['data'])
            data['clarifications'] = list(data.get('clarifications') or []) + [{'source': key, 'text': text}]
            question = read(data['question_id']) if data.get('question_id') else None
            options = [p for p in (question['data']['candidates'] if question else []) if p in candidates]
            said = named_projects(text, options)
            chosen = explicit if explicit in options else (said[0] if len(said) == 1 else None)
            if data['state'] == 'AWAITING_PROJECT' and question is not None and chosen is not None:
                resolved = {'schema': PROPOSAL_SCHEMA, 'proposal_id': pid, 'proposal': 'objective', 'state': 'PROPOSED',
                            'domain': self.domain, 'project': chosen, 'principal': principal, 'text': data['text'],
                            'sources': list(data['sources']) + [key], 'clarifications': data['clarifications'],
                            'question_id': None, 'resolves': live, 'resolved_to': None}
                data.update(state='RESOLVED', resolved_to=pid)
                changes[pid] = {'kind': PROPOSAL_KIND, 'data': resolved}
                changes[question['data']['question_id']] = {'kind': QUESTION_KIND, 'data': dict(
                    question['data'], state='answered', answered_by=key, project=chosen)}
                result = {'outcome': 'resolved', 'proposal_id': pid, 'project': chosen}
            else:
                result = {'outcome': 'clarification', 'proposal_id': live, 'project': data.get('project')}
            changes[live] = {'kind': PROPOSAL_KIND, 'data': data}
        else:
            project = explicit or (named[0] if len(named) == 1 else None) or (candidates[0] if len(candidates) == 1 else None)
            proposal = {'schema': PROPOSAL_SCHEMA, 'proposal_id': pid, 'proposal': 'objective' if project else 'inbox',
                        'state': 'PROPOSED' if project else 'AWAITING_PROJECT', 'domain': self.domain, 'project': project,
                        'principal': principal, 'text': text, 'sources': [key], 'clarifications': [],
                        'question_id': None, 'resolves': None, 'resolved_to': None}
            result = {'outcome': 'proposed' if project else 'inbox', 'proposal_id': pid, 'project': project}
            if project is None:
                qid = question_id(key)
                prompt = 'Which project is this for? Reply to this message with one of: %s.' % ', '.join(candidates)
                proposal['question_id'] = qid
                ask = {'schema': QUESTION_SCHEMA, 'question_id': qid, 'proposal_id': pid, 'principal': principal,
                       'asks': 'project', 'candidates': candidates, 'prompt': prompt, 'state': 'open',
                       'asked_on': command['source_kind'], 'answered_by': None, 'project': None,
                       'delivery': ({'channel': 'api', 'request_id': command['source_id']}
                                    if command['source_kind'] == 'api_request' else None)}
                changes[qid] = {'kind': QUESTION_KIND, 'data': ask}
                result.update(question_id=qid, question={'question_id': qid, 'prompt': prompt, 'candidates': candidates})
            changes[pid] = {'kind': PROPOSAL_KIND, 'data': proposal}
        source.update(proposal_id=result['proposal_id'], question_id=result.get('question_id'),
                      result={k: v for k, v in result.items() if k != 'project'})
        changes[key] = {'kind': SOURCE_KIND, 'data': source}
        return changes, reads, result

    def _live_proposal(self, clarifies, principal, read, reads):
        """(id, entity) of the live proposal a follow-up clarifies. A follow-up names the proposal it
        answers: for a Telegram reply the one its replied message or question belongs to, for an API
        request the id it carries. When that is an inbox proposal already RESOLVED, the owner's work
        now lives on the objective it was resolved to, so the follow-up lands there; each record on
        the way is the principal's own and is read, so a change to any of them refuses the commit."""
        pid, seen = clarifies, []
        while True:
            target = read(pid)
            if target is None or target['kind'] != PROPOSAL_KIND:
                raise Refused('missing_evidence:clarifies', str(pid))
            if target['data'].get('principal') != principal:
                raise Refused('unauthorized:clarifies', str(pid))
            seen.append(pid)
            reads.append(pid)
            onward = target['data'].get('resolved_to')
            if target['data'].get('state') != 'RESOLVED':
                return pid, target
            if not _identifier(onward) or onward in seen:
                raise Refused('missing_evidence:clarifies', 'a resolved proposal names no live proposal: ' + str(pid))
            pid = onward

    def _member_when_sent(self, principal, sent):
        """None when `principal` was a member when the message was sent, at `sent`, the platform date
        of the Telegram message: its membership was not revoked or expired then, and the key its
        enrollment wrote had taken effect. VELDO-0025 keeps no start time on the membership entity
        itself; every enrollment (control_membership enroll_principal, and the channel edge
        enrollment) writes the principal's key in the same transition with `effective_at` set to the
        time the enrollment took effect, and a re-enrollment revokes the earlier keys at that time."""
        if type(sent) not in (int, float) or type(sent) is bool:
            return 'not_member_when_sent'
        state = self.CM.authority_state(self.store, self.conn)
        entry = self.AC.membership_entry(state['membership'], principal)
        if not self.AC.active_member(entry, sent)[0] or self.AC.active_key(state['keyring'], principal, sent) is None:
            return 'not_member_when_sent'
        return None

    # telling the owner about waiting requests (VELDO-0136)

    def _hint(self, evidence_id, taken, lead=None):
        """The presenter's one decision about a Telegram message the Acquirer refused as replying to no
        presentation, from a person it attributed: its recorded decision, taken once when the message
        was acquired, never a reading made now. `taken` is what intake made of it (None: not taken).
        A message intake did not take is remembered even when nothing is sent, so a later pass never
        decides it again. Returns hint_owner's result, or {} when no decision is due."""
        record = self.acquirer.evidence(evidence_id) if type(evidence_id) is str else None
        presenter = getattr(self.acquirer, 'presenter', None)
        if record is None or presenter is None or not hasattr(presenter, 'hint_owner'):
            return {}
        fields = record.get('fields') or {}
        if (record.get('outcome') != 'refused' or record.get('reason') not in ORDINARY
                or record.get('principal') is None):
            return {}
        try:
            if presenter.hint_decided(fields.get('chat_id'), fields.get('message_id')):
                return {}
            return presenter.hint_owner(dict(cause=record['reason'], principal=record['principal'],
                                             chat_id=fields.get('chat_id'), sender_id=fields.get('sender_id'),
                                             message_id=fields.get('message_id'), evidence_id=record['evidence_id'],
                                             update_id=record.get('update_id')),
                                        taken=taken, lead=lead, remember=taken is None)
        except Exception:  # noqa: BLE001 - a hint never undoes or blocks what intake recorded
            return {}

    # asking on Telegram

    def _ask(self, qid, command):
        """Send an inbox proposal's question to the owner's chat as a reply to the message, and record
        where the platform put it. When requests of the owner wait, the note that his message was taken
        as new work is merged into the question and the one message goes through the presenter's hint
        (VELDO-0136). A failed send leaves the question open and undelivered, by name."""
        where, question = command['provenance'], self.question(qid)
        if self.asker is None:
            self._hint(where.get('evidence_id'), 'proposed')
            return self._event('ask', 'refused', 'unavailable_service', question_id=qid)
        hinted = self._hint(where.get('evidence_id'), 'inbox', lead=question['prompt'])
        if hinted.get('attempted'):
            sent = hinted.get('delivery')
            if not isinstance(sent, dict):
                return self._event('ask', 'refused', hinted.get('reason') or 'unknown_outcome', question_id=qid)
        else:
            try:
                sent = self.asker.send(where['chat_id'], question['prompt'], reply_to=where['message_id'])
            except Exception as error:  # noqa: BLE001 - a failed send is named, never raised past the intake
                return self._event('ask', 'refused', getattr(error, 'code', 'unknown_outcome'), question_id=qid)
        delivery = {'channel': 'telegram_chat', 'bot_id': where['bot_id'], 'chat_id': sent['chat_id'],
                    'message_id': sent['message_id'], 'date': sent['date']}
        row = self._entity(qid)
        cid = 'intake-asked:' + _hex(qid, delivery)
        try:
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation=ASKED,
                                               parameters={'question_id': qid, 'delivery': delivery},
                                               expected_versions={qid: row['version']}, artifact_digests=[], nonce=cid),
                               self.journal_signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused, sqlite3.Error):
            return self._event('ask', 'unknown_outcome', 'unknown_outcome', question_id=qid)
        return self._event('ask', 'asked', None, question_id=qid, delivery=delivery)

    def _asked_transition(self, conn, params, before):
        qid, delivery = params.get('question_id'), params.get('delivery')
        current = (before.get(qid) or {}).get('data')
        if (not isinstance(current, dict) or (before.get(qid) or {}).get('kind') != QUESTION_KIND
                or current.get('delivery') is not None or not isinstance(delivery, dict)):
            raise Refused('invalid_input:delivery', 'a question is delivered once')
        return {qid: {'kind': QUESTION_KIND, 'data': dict(current, delivery=delivery)}}
