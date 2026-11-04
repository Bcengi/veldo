"""The decisions a conversation raises, and the authority a turn's output never carries (VELDO-0181).

THE DECISIONS GO THROUGH THE EXISTING FLOW. A conversation gets no decision path of its own. A question the factory
asks about one of its turns (the re-run-or-ask of a turn stopped at its account limit, VELDO-0160 AC3 over VELDO-0154
AC3, and the wait-or-move question when every account of its engine is at its limit, VELDO-0176 AC2) is one ordinary
VELDO-0068 request: `open_question` records its requester-signed settlement terms (touchpoint decision_disposition,
the target the question is about), opens the VELDO-0064 request at the conversation's decision coordinate
(`conversation:<identity>`) with those terms as its subject, and records the requester's signed framing, so the
VELDO-0065 presenter can present it and VELDO-0068 can settle it. The presenter publishes every pending conversation
request beside its own inbox's (control_channel_presentation.publish), on the owner's enrolled private chat, the chat he
wrote from; settlement settles each once, from his Telegram reply to that presentation or from his inline answer in the
UI (control_request_settlement.run and api_answer), and the turn it concerns waits until it settles (the service reads
only the settled answer).

THE UNCLEAR ROUTE QUESTION (VELDO-0175 AC2) is the same kind of request. When the factory PM routes a Telegram message
unclear, intake opens its question through `open_question` at the message's own decision coordinate
(`conversation:route:<proposal>`, `route_identity`), the choices `route_choices` offers (each a pick: a project, a
new project, a new conversation, one of his open conversations), and presents it at once; its reply is settlement's,
never intake's and never a turn (a reply that is exactly one choice's short form, `route_short`, answers it with no
reason typed, as he answered it before; one two choices share is refused ambiguous_choice), and intake applies the settled choice (`ruling`) to the proposal as his reply answer
was applied before: a project resolves it, anything else clarifies it for the PM (control_intake.route_answers).

A PRESENTATION IN A CONVERSATION IS NOT ONE OF ITS TURNS. Once a conversation request is published, `presented` keeps
each of its Telegram messages as a message the factory sent in that conversation (VELDO-0175's record, kind
`decision`, never a turn's reply) and notes the presentation on the turn's question: the trace from the decision to
its turn, its presentation receipt and, once settled, the answer. VELDO-0066 attributes a reply to it as an answer to
that presentation before intake ever reads it, so it settles the decision and is never the conversation's next turn;
a message that replies to no presentation gets VELDO-0136's reply-to-the-request hint.

NOTHING A TURN PRODUCES CARRIES AUTHORITY. `authority_documents` reads a turn's execution record (its reply, its tool
results and every protocol message) for documents shaped as authority: an answer to a request (a presentation or API
answer, an inbox answer, anything naming a request and a choice or ruling), an approval (an objective acceptance or any
approve/accept operation), a role save, and a route or reading document. Each is refused by name
(invalid_input:turn_output:authority), recorded on the turn by its kind, where it was found and its digest, never its
text, and the reply is kept as text: no settlement, acceptance, admission or role save reads it.

OBSERVABILITY. `metrics` counts conversation decisions by kind and settlement and turn outputs refused as authority from
the store itself; `trace` joins one decision to its turn, presentation receipt and settling answer; `event` is the one
log line of a decision (kind, request, presentation, settlement) or of a refused output (its rule), never message
text. Standard library only.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('conversation_decisions_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMA = 'veldo.conversation_decision/v1'
PREFIX = 'conversation:'
REQUEST_PREFIX = 'assignment:' + PREFIX
TOUCHPOINT = 'decision_disposition'
# The decisions a conversation raises, by the kind of what they are about (the terms target's kind).
RERUN, ENGINE_LIMIT, ROUTE, PROJECT = 'account_limit_rerun', 'conversation_engine_limit', 'unclear_route', 'new_project'
KINDS = (RERUN, ENGINE_LIMIT)
# What open_question opens: a turn's two questions and the unclear route question of a message on its way in.
OPENED = KINDS + (ROUTE,)
RISK = {
    RERUN: 'A re-run may repeat what the stopped run already wrote outside its clone; stopping ends the turn.',
    ENGINE_LIMIT: 'Moving changes the conversation to your assistant role on the other engine; waiting changes '
                  'nothing until the reset.',
    ROUTE: 'Your choice routes this message: a project makes it that project\'s proposal; anything else is read '
           'again by the factory PM with your answer.',
}
# The unclear route question's decision coordinate is the message's own, beside the conversations'.
ROUTE_PREFIX = 'route:'
OWNER_REFUSAL = 'missing_authority:conversation_owner'
OUTPUT_REFUSAL = 'invalid_input:turn_output:authority'
SENT_KIND = 'decision'
# What a turn's output may imitate: an answer, an approval, a role save, a route. Read from JSON objects only.
ANSWER_SCHEMAS = ('veldo.presentation_answer/v1', 'veldo.settlement_api_answer/v1')
ROUTE_SCHEMAS = ('veldo.intake_route/v1', 'veldo.conversation_reading/v1')
APPROVAL_OPERATIONS = ('accept', 'accept_message', 'accept_decided', 'approve', 'admit', 'settle', 'terms', 'frame',
                       'open')
ROLE_OPERATIONS = ('save_capability_configuration', 'save_default_team', 'propose_team', 'save_role',
                   'set_conversation_role')
DOCUMENT_KINDS = ('answer', 'approval', 'role', 'route')
SCAN_LIMIT = 200000


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code + (': ' + detail if detail else ''))
        self.code, self.detail = code, detail


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


# the conversation's decision coordinate

def coordinate(identity):
    return PREFIX + str(identity)


def route_identity(proposal_id):
    """The decision coordinate identity of the unclear route question of one inbox proposal."""
    return ROUTE_PREFIX + hashlib.sha256(str(proposal_id).encode()).hexdigest()[:24]


def route_choices(projects, conversations):
    """{choice: option} the unclear route question offers, in order: each project (`accept project <name>`), a new
    project, a new conversation and each of his open conversations (`accept conversation <id>`). Each choice is a pick
    (control_channel_presentation), so its ruling is approve; the option is what the settled choice routes to.
    `conversations` are open_conversations' entries."""
    found = {}
    for name in projects:
        found['accept project ' + name] = {'route': 'project', 'project': name, 'label': name}
    found['accept new project'] = {'route': 'new_project', 'label': 'a new project'}
    found['accept new conversation'] = {'route': 'new_conversation', 'label': 'a new conversation'}
    for entry in conversations:
        found['accept conversation ' + entry['id']] = {
            'route': 'open_conversation', 'conversation': entry['id'],
            'label': 'conversation %s%s' % (entry['id'], ' (%s)' % entry['opening'] if entry.get('opening') else '')}
    return found


def route_short(choice):
    """The short form of one unclear route choice, as he answered the question before it was a request: a project's
    bare name, `new project`, `new conversation`, or a conversation's id."""
    for lead in ('accept project ', 'accept conversation ', 'accept '):
        if isinstance(choice, str) and choice.startswith(lead):
            return choice[len(lead):]
    return None


def route_shorts(typed, choices, fold):
    """The offered unclear route choices whose short form `typed` is, folded as the presenter folds a choice (`fold`):
    one is his answer, two or more are ambiguous."""
    return [c for c in choices if route_short(c) is not None and fold(route_short(c)) == fold(typed)]


def is_request(request):
    """Whether `request` is a question a conversation raised (a request at a conversation's decision coordinate)."""
    return isinstance(request, str) and request.startswith(REQUEST_PREFIX) and ':' in request[len(REQUEST_PREFIX):]


def coordinate_of(request):
    """The coordinate a conversation request was opened at, or None for any other request."""
    return 'conversation:' + request[len(REQUEST_PREFIX):].rsplit(':', 1)[0] if is_request(request) else None


def identity_of(request):
    return request[len(REQUEST_PREFIX):].rsplit(':', 1)[0] if is_request(request) else None


def pending(conn, inbox):
    """The pending conversation requests of the store, in id order, each read by its own coordinate's inbox."""
    found = []
    for (rid,) in conn.execute("SELECT id FROM entities WHERE kind='assignment' AND substr(id, 1, ?) = ? ORDER BY id",
                               (len(REQUEST_PREFIX), REQUEST_PREFIX)):
        if is_request(rid) and inbox_for(inbox, rid).brief(rid).get('category') == 'pending':
            found.append(rid)
    return found


def inbox_for(inbox, request):
    """The inbox that reads `request`: `inbox` itself, or for a question a conversation raised the same inbox at that
    conversation's decision coordinate (an inbox reads only its own coordinate's requests). Made once per coordinate,
    leaving the connection's registered transitions as they were."""
    where = coordinate_of(request)
    if where is None or inbox.ids.get('repository_uuid') == where:
        return inbox
    kept = inbox.__dict__.setdefault('_conversation_inboxes', {})
    if where not in kept:
        with registry_kept(inbox.conn):
            kept[where] = type(inbox)(inbox.store, inbox.membership, inbox.claims, inbox.contract, inbox.conn,
                                      dict(inbox.ids, repository_uuid=where), inbox.journal_signer, inbox.sign,
                                      inbox.authority_generation, inbox.clock)
    return kept[where]


class registry_kept:
    """Constructing an inbox, presenter or settlement registers its transitions on the connection; a sibling built for a
    conversation coordinate leaves the connection's registry as it found it."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.saved = dict(self.conn.command_registry)
        return self

    def __exit__(self, *exc):
        self.conn.command_registry.clear()
        self.conn.command_registry.update(self.saved)
        return False


# opening a conversation question as an ordinary request

def open_question(store, membership, claims, contract, assignment, conn, *, domain, store_uuid, identity, alias,
                  content, principal, journal_sign, command_sign, generation=1, clock=time.time):
    """Open one question about a conversation's turn as an ordinary VELDO-0068 request at the conversation's decision
    coordinate: the requester-signed settlement terms (decision_disposition, the target `content['subject']` names),
    the VELDO-0064 request with those terms as its subject and the requester's signed framing. `command_sign(bytes)`
    signs as `principal` under the command namespace. Opened once per alias: a retry finds each step committed and
    completes the rest. Returns ({ok, reason}, request id)."""
    V, ST = _organ('control_channel_presentation'), _organ('control_request_settlement')
    P = _organ('control_channel_projection')
    where = coordinate(identity)
    ids = {'domain_uuid': domain, 'repository_uuid': where, 'store_uuid': store_uuid}
    request = assignment.assignment_id(where, alias)
    subject = content.get('subject') or {}
    kind = subject.get('kind')
    if kind not in OPENED or not all(_text(subject.get(k)) for k in ('ref', 'digest')):
        return {'ok': False, 'reason': 'invalid_input:conversation_question'}, request

    def signed(**fields):
        command = dict(ids, principal=principal, **fields)
        return {'command': command, 'signature': command_sign(store.canonical_bytes(command))}

    with registry_kept(conn):
        inbox = assignment.Inbox(store, membership, claims, contract, conn, ids, principal, journal_sign, generation)
        presenter = V.Presenter(store, membership, P, inbox, None, conn, principal, journal_sign, generation, clock,
                                assignment=assignment)
        settlement = ST.Settlement(store, membership, inbox, presenter, conn, principal, journal_sign,
                                   assignment=assignment, presentation=V, authority_generation=generation, clock=clock)
        terms_id = ST.terms_id(where, alias)
        recorded = (presenter._entity(terms_id) or {}).get('data')
        if recorded is None:
            terms = settlement.terms(signed(operation='terms', terms=alias, command_id=alias + '-terms',
                                            nonce=alias + '-terms', touchpoint=TOUCHPOINT,
                                            target={k: subject[k] for k in ('kind', 'ref', 'digest')},
                                            proposal=None, required_roles=[], quorum=None))
            if terms.get('outcome') != 'recorded':
                return {'ok': False, 'reason': 'unavailable_service:terms:' + str(terms.get('reason'))}, request
            terms_subject = terms['subject']
        else:
            terms_subject = {'kind': ST.SUBJECT_KIND, 'ref': terms_id, 'digest': ST.digest(recorded)}
        opened = {'ok': True, 'reason': 'exists'}
        if inbox.read(request) is None:
            opened = inbox.apply(signed(operation='open', alias=alias, command_id=alias, nonce=alias,
                                        assignment=dict(content, subject=terms_subject)))
            if not opened.get('ok'):
                return opened, request
        item = inbox.read(request) or {}
        version = (item.get('data') or {}).get('request_version', 1)
        if presenter._entity(V.framing_id(request)) is None:
            framed = presenter.frame(signed(operation='frame', alias=alias, request_version=version,
                                            risk_statement=RISK[kind], command_id=alias + '-frame',
                                            nonce=alias + '-frame'))
            if framed.get('outcome') != 'accepted':
                return {'ok': False, 'reason': 'unavailable_service:framing:' + str(framed.get('reason'))}, request
    return opened, request


def open_presented(presenter, *, identity, alias, content, principal, command_sign):
    """open_question with the parts of the presenter that will present it (its inbox's store, membership, claims and
    contract, its assignment module and connection)."""
    inbox = presenter.inbox
    return open_question(inbox.store, inbox.membership, inbox.claims, inbox.contract, presenter.assignment,
                         presenter.conn, domain=inbox.ids['domain_uuid'], store_uuid=inbox.ids['store_uuid'],
                         identity=identity, alias=alias, content=content, principal=principal,
                         journal_sign=presenter.sign, command_sign=command_sign,
                         generation=presenter.authority_generation)


def ruling(conn, request):
    """The owner's settled choice on a question a conversation raised, judged from its VELDO-0068 evidence: the request
    terminal with its settlement reference, the settlement of this request version settled by the request's owner alone
    through decision_disposition with one of the offered choices, and the effect that ruling gives. None while it waits
    and whenever that evidence does not hold, so nothing a turn wrote and no other record stands in for his answer."""
    ST, V = _organ('control_request_settlement'), _organ('control_channel_presentation')
    item = _row(conn, request)
    data = (item or {}).get('data') or {}
    if not is_request(request) or (item or {}).get('kind') != 'assignment' or data.get('state') != ST.TERMINAL_STATE:
        return None
    version = data.get('request_version')
    sid, eid = ST.settlement_id(request, version), ST.effect_id(request, version)
    reference = data.get('settlement') if isinstance(data.get('settlement'), dict) else {}
    settled = (_row(conn, sid) or {}).get('data') or {}
    effect = (_row(conn, eid) or {}).get('data') or {}
    choice = settled.get('choice')
    if (reference.get('settlement_id') != sid or settled.get('request_id') != request
            or settled.get('request_version') != version or settled.get('touchpoint') != TOUCHPOINT
            or settled.get('principals') != [data.get('owner')] or choice not in (data.get('choices') or [])
            or settled.get('ruling') != V.ruling_of(choice) or (data.get('answer') or {}).get('ruling') != choice
            or effect.get('settlement_id') != sid
            or effect.get('type') != ST.JOURNEY[TOUCHPOINT]['effects'].get(settled.get('ruling'))):
        return None
    return choice


def kind_of(conn, request):
    """What a conversation request is about: its terms target's kind (None when it names no recorded terms)."""
    row = conn.execute('SELECT data FROM entities WHERE id=?', (request,)).fetchone()
    subject = (json.loads(row[0]).get('subject') or {}) if row else {}
    terms = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(subject.get('ref')),)).fetchone()
    if not terms or terms[0] != 'settlement_terms':
        return None
    return (json.loads(terms[1]).get('target') or {}).get('kind')


# the presentation kept in the conversation

def _row(conn, eid):
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


def turn_of(conn, request):
    """(conversation, turn record) of the turn whose question `request` is, or (identity, None)."""
    identity = identity_of(request)
    for (raw,) in conn.execute('SELECT data FROM entities WHERE kind=?', ('conversation_turn',)):
        turn = json.loads(raw)
        if turn.get('conversation') == identity and any(q.get('ref') == request for q in turn.get('questions') or []):
            return identity, turn
        limited = turn.get('limited') if isinstance(turn.get('limited'), dict) else {}
        if turn.get('conversation') == identity and limited.get('question') == request:
            return identity, turn
    return identity, None


def wrote_from(conn, turn):
    """(bot, chat) of the Telegram message the turn was made from, or (None, None) for any other turn."""
    source = _row(conn, str((turn or {}).get('intake_command')))
    command = ((source or {}).get('data') or {}).get('command') or {}
    if not source or source['kind'] != 'intake_source' or command.get('source_kind') != 'telegram_message':
        return None, None
    where = command.get('provenance') or {}
    return where.get('bot_id'), where.get('chat_id')


def presented(presenter, request, observe=None):
    """Keep the published presentation of a conversation request in its conversation: each of its Telegram messages
    as a message the factory sent there (kind `decision`, bound to the conversation and the request) and, on the turn's
    question, the presentation receipt and where it was shown. Done once per presentation. Returns the trace event, or
    None when nothing was due."""
    CV = _organ('control_conversation')
    conn = presenter.conn
    receipt = presenter.current(request)
    if receipt is None or receipt.get('outcome') != 'published':
        return None
    identity, turn = turn_of(conn, request)
    if turn is None:
        return None
    bot, chat = wrote_from(conn, turn)
    question = next((q for q in turn.get('questions') or [] if q.get('ref') == request), None)
    shown = (question or {}).get('presentation') or {}
    if shown.get('presentation_id') == receipt['presentation_id']:
        return None
    conn.command_registry[CV.OPERATION] = {'transaction_transition': CV.transition,
                                           'writes': ('entities', 'journal', 'commands', 'nonces')}

    def run(params, ids, cid):
        command = {'command_id': cid, 'principal': presenter.journal_signer, 'operation': CV.OPERATION,
                   'parameters': dict(params, principal=presenter.journal_signer),
                   'expected_versions': {eid: (_row(conn, eid) or {}).get('version', 0) for eid in ids},
                   'artifact_digests': [], 'nonce': cid}
        presenter.store.execute(conn, command, presenter.journal_signer, presenter.sign,
                                presenter.authority_generation)

    if type(bot) is int and receipt.get('chat_id') == chat:
        for number, message in enumerate(receipt.get('message_ids') or [], 1):
            mid = CV.sent_id(bot, chat, message)
            if _row(conn, mid) is not None:
                continue
            run({'operation': CV.SENT, 'kind': SENT_KIND, 'conversation': identity, 'sequence': turn['sequence'],
                 'part': number, 'parts': len(receipt['message_ids']), 'ref': request, 'bot_id': bot, 'chat_id': chat,
                 'message_id': message, 'date': receipt.get('published_at') or 0, 'reply_to': None, 'answers': None},
                [CV.conversation_id(identity), mid], 'conversation-decision/%s/%s/%s' % (bot, chat, message))
    note = dict(question or {'kind': 'question', 'ref': request, 'about': kind_of(conn, request), 'answer': None})
    note['presentation'] = {'presentation_id': receipt['presentation_id'], 'chat_id': receipt.get('chat_id'),
                            'message_ids': list(receipt.get('message_ids') or []),
                            'wrote_from': chat, 'same_chat': receipt.get('chat_id') == chat}
    run({'operation': CV.NOTE, 'conversation': identity, 'domain': presenter.ids.get('domain_uuid'),
         'sequence': turn['sequence'], 'note': note},
        [CV.conversation_id(identity), CV.turn_id(identity, turn['sequence'])],
        'conversation-decision-note/%s/%s' % (request, receipt['presentation_id']))
    found = event(conn, request, 'presented')
    if observe:
        observe(found)
    return found


# observability

def trace(conn, request):
    """One conversation decision joined to its turn, its presentation receipt and the answer that settled it."""
    identity, turn = turn_of(conn, request)
    head = _row(conn, 'presentation-head:telegram_chat:' + request)
    receipt = (_row(conn, str(head['data'].get('current'))) or {}).get('data') if head else None
    item = (_row(conn, request) or {}).get('data') or {}
    settled = item.get('settlement') if isinstance(item.get('settlement'), dict) else None
    settlement = (_row(conn, settled['settlement_id']) or {}).get('data') if settled else None
    if isinstance(identity, str) and identity.startswith(ROUTE_PREFIX):
        identity = None  # the unclear route question is a message's, before any conversation
    return {'schema': SCHEMA, 'request': request, 'kind': kind_of(conn, request), 'conversation': identity,
            'turn': (turn or {}).get('sequence'), 'state': item.get('state'),
            'presentation': (receipt or {}).get('presentation_id'),
            'presented_on': (receipt or {}).get('chat_id'), 'settlement': (settlement or {}).get('settlement_id'),
            'answer': (settlement or {}).get('answer_id'), 'choice': (settlement or {}).get('choice'),
            'channel': (settlement or {}).get('originating_channel')}


def event(conn, request, outcome, **extra):
    """The log line of one conversation decision: kind, request, presentation and settlement; never message text."""
    found = trace(conn, request)
    return dict({'schema': SCHEMA, 'operation': 'conversation_decision', 'outcome': outcome},
                **{k: found[k] for k in ('request', 'kind', 'conversation', 'turn', 'presentation', 'settlement',
                                         'answer', 'choice', 'channel')}, **extra)


def metrics(conn):
    """Conversation decisions by kind and settlement (the chosen answer, or pending/closed) and turn outputs refused
    as authority by document kind, from the store."""
    decisions = {}
    for (rid,) in conn.execute("SELECT id FROM entities WHERE kind='assignment' AND substr(id, 1, ?) = ?",
                               (len(REQUEST_PREFIX), REQUEST_PREFIX)):
        found = trace(conn, rid)
        key = '%s/%s' % (found['kind'], found['choice'] or ('pending' if found['settlement'] is None
                                                            and found['state'] not in ('SATISFIED', 'CANCELLED',
                                                                                       'EXPIRED') else 'closed'))
        decisions[key] = decisions.get(key, 0) + 1
    refused = {}
    for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='conversation_turn'"):
        for item in json.loads(raw).get('refused_outputs') or []:
            refused[item.get('document')] = refused.get(item.get('document'), 0) + 1
    return {'decisions': decisions, 'turn_outputs_refused': refused}


# a turn's output carries no authority

def _objects(text):
    """Every JSON object written in `text` (bare or fenced), outermost first, at most SCAN_LIMIT characters read."""
    decoder, found, at = json.JSONDecoder(), [], 0
    text = text[:SCAN_LIMIT]
    while True:
        at = text.find('{', at)
        if at < 0:
            return found
        try:
            value, end = decoder.raw_decode(text, at)
        except ValueError:
            at += 1
            continue
        if isinstance(value, dict):
            found.append(value)
            at = end
        else:
            at += 1


def document_kind(value):
    """The kind of authority a JSON object is shaped as (answer, approval, role, route), or None."""
    if not isinstance(value, dict):
        return None
    schema, operation = value.get('schema'), value.get('operation')
    if (schema in ANSWER_SCHEMAS or operation == 'answer'
            or ('request_id' in value and ('choice' in value or 'ruling' in value))):
        return 'answer'
    if schema in ROUTE_SCHEMAS or ('route' in value and ('proposal_id' in value or 'project' in value)):
        return 'route'
    if operation in ROLE_OPERATIONS or (isinstance(value.get('role'), str) and 'revision' in value
                                        and ('engine' in value or 'tools' in value)):
        return 'role'
    if operation in APPROVAL_OPERATIONS or value.get('decision') in ('approve', 'accept', 'accepted') \
            or value.get('state') == 'ACCEPTED':
        return 'approval'
    return None


def _strings(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, path + (str(k),))
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, path)


def _where(event, path):
    kind = event.get('type')
    if kind == 'result' or (kind == 'item.completed' and (event.get('item') or {}).get('type') == 'agent_message'):
        return 'reply'
    if 'tool_result' in json.dumps(event)[:4096] or (kind == 'item.completed' and (event.get('item') or {}).get(
            'type') in ('command_execution', 'mcp_tool_call', 'web_search', 'file_change')):
        return 'tool_result'
    return 'protocol'


def authority_documents(lines, reply=None):
    """Every authority-shaped document a turn's output holds: its reply, its tool results and its protocol messages
    (the engine lines of its execution record). One entry per distinct document: {document, where, digest, refusal}."""
    found = {}

    def take(value, where):
        for obj in _objects(value):
            kind = document_kind(obj)
            nested = [o for k, v in obj.items() for o in ([v] if isinstance(v, dict) else [])]
            if kind is None:
                for inner in nested:
                    take(json.dumps(inner), where)
                continue
            key = _digest(obj)
            entry = found.setdefault(key, {'document': kind, 'where': [], 'digest': key, 'refusal': OUTPUT_REFUSAL})
            if where not in entry['where']:
                entry['where'].append(where)

    for line in lines or []:
        if line.get('stream') != 'engine':
            continue
        try:
            payload = json.loads(line.get('payload') or 'null')
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        where = _where(payload, ())
        for _path, value in _strings(payload):
            if '{' in value:
                take(value, where)
    if isinstance(reply, str) and '{' in reply:
        take(reply, 'reply')
    return sorted(found.values(), key=lambda e: (DOCUMENT_KINDS.index(e['document']), e['digest']))


def refused_event(identity, sequence, dispatch_id, entry):
    """The log line of one turn output refused as authority: the rule, the document kind and where it was found."""
    return {'schema': SCHEMA, 'operation': 'turn_output', 'conversation': identity, 'sequence': sequence,
            'dispatch_id': dispatch_id, 'outcome': 'refused', 'refusal': entry['refusal'],
            'document': entry['document'], 'where': list(entry['where']), 'digest': entry['digest']}


def copy_entries(entries):
    return [copy.deepcopy(e) for e in entries]
