"""Canonical Telegram attribution: the platform's own chat, message, sender and time (VELDO-0066, PLAN-0019 W51).

WHAT THIS MODULE IS. The inbound half of the Telegram edge. It acquires updates through the Bot API
getUpdates method, the authenticated platform exchange (the token names the bot; nothing a caller
pastes is read), keeps each update as one immutable canonical evidence record in the control store,
attributes its sender by the platform's stable user id alone, binds a reply to the exact presentation
it replies to, and hands the attributed answer to the VELDO-0065 presenter, whose answer check is the
one that records it.

EVIDENCE IS WHAT THE PLATFORM SENT. One `channel_evidence` record per update, keyed by the bot's own
user id (getMe) and the update id. It holds the update exactly as the platform delivered it, the
digest of that update, the digest of the whole platform answer it arrived in, and the canonical
fields read from it: update id and type, message id, chat id and type, sender id and whether the
platform says the sender is a bot, the platform date, and the replied-to message's id, chat and date.
The record and the acquisition cursor move in one store transaction, so an update is confirmed to the
platform (the next getUpdates offset) only once its evidence is kept. A record is decided once. A
pasted transcript, a display name, a username, an author signature or any label a caller adds is
never evidence of who answered.

IDENTITY IS THE STABLE SENDER ID. A message is attributed only when it is an ordinary new message
(`message`: never an edit or another update type), carries every canonical field in the platform's
documented types, was sent by a person account in person (not by a bot account, not on behalf of a
chat, not through an inline bot, not by a business bot, not by an implicit action such as an away,
greeting or scheduled message, not an automatic forward), is not a forward of anyone's earlier words,
and was sent in that person's own private chat with the bot (a private chat whose id is the sender's
user id, as Telegram makes it). The sender's user id is then mapped to the one valid VELDO-0064
channel enrollment whose chat it is; none is `unknown_sender` and more than one `ambiguous_sender`.
That principal must be a current active person member (VELDO-0020 membership) whom the revocation
ledger does not name. Display names change and repeat, so they are never read for identity.

THE ANSWER BINDS ITS PRESENTATION. The message must reply to a message in the same chat. That message
must be a published VELDO-0065 presentation part, and the replied-to message the platform delivered
must be that part as published: sent by this bot, with the part's exact bytes and the platform date
the receipt recorded. The attributed principal must be the presentation's
owner. The canonical assertion is then built by the presenter itself (`canonical_answer`) from the
platform message, must name the same presentation, carries the attributed principal and the evidence
identity and digest, is signed with the edge's restricted key from the caller's custody, and is
decided by `Presenter.answer`, which refuses by name everything its own checks refuse and tells the
owner, once per message, when a reply cannot count. Everything here that is not proven refuses by
name, and nothing is sent back for it here. A message from the attributed current person that
replies to no presentation (NOT_A_REPLY) stays refused; the VELDO-0126 intake pass then takes or
refuses it and makes the one decision about what he is told (the presenter's `hint_owner`, once per
request waiting for him, VELDO-0136).

WHAT IT IS NOT. Not live qualification against the Telegram service, not edge enrollment or delegation
(VELDO-0067), not settlement (VELDO-0068), and not outage or redelivery recovery (Release 2). The bot
token comes from the caller's custody and is never logged or stored. Standard library only.
"""
import hashlib
import http.client
import json
import sqlite3
import time
import urllib.error
import urllib.request

EVIDENCE_SCHEMA = 'veldo.channel_evidence/v1'
CURSOR_SCHEMA = 'veldo.channel_acquisition_cursor/v1'
EVIDENCE_KIND = 'channel_evidence'
CURSOR_KIND = 'channel_acquisition_cursor'
EVIDENCE_OPERATION = 'channel_evidence_record'
CHANNEL = 'telegram_chat'
# The update types acquisition asks for (getUpdates allowed_updates). The platform may still deliver
# another type created before a request named them; such an update is kept and refused.
UPDATE_KINDS = ('message', 'edited_message')
# The most updates one getUpdates call returns (the Bot API's own maximum).
UPDATE_LIMIT = 100
# The evidence of one update as kept; the decision fields are added once, when it is decided.
EVIDENCE_FIELDS = ('schema', 'channel', 'evidence_id', 'bot_id', 'update_id', 'source', 'source_digest',
                   'response_digest', 'fields')
DECISION_FIELDS = ('outcome', 'reason', 'principal', 'request_id', 'presentation_id', 'answer_id')
OUTCOMES = ('acquired', 'answered', 'refused')
# The canonical fields, each read from the platform's own field of its documented type.
CANONICAL_FIELDS = ('update_id', 'update_kind', 'message_id', 'date', 'chat_id', 'chat_type', 'sender_id',
                    'sender_is_bot', 'reply_to_message_id', 'reply_chat_id', 'reply_date')
# The fields no message is attributed without.
REQUIRED_FIELDS = ('update_id', 'message_id', 'date', 'chat_id', 'chat_type', 'sender_id', 'sender_is_bot')
# Message fields that make the text a copy of words sent before, by whoever sent them (Bot API
# forward_origin, and the older forward_* fields it replaced).
FORWARD_FIELDS = ('forward_origin', 'forward_from', 'forward_from_chat', 'forward_sender_name', 'forward_date')
# Every named refusal of this module and its error class; the presenter's own are in its REFUSALS.
REFUSALS = {'channel_refused': 'unavailable_service', 'unavailable_service': 'unavailable_service',
            'invalid_platform_answer': 'unavailable_service', 'incomplete_transaction': 'unavailable_service',
            'evidence_mismatch': 'missing_evidence', 'edited_message': 'invalid_input',
            'unsupported_update': 'invalid_input', 'missing_canonical_field': 'missing_evidence',
            'automation_sender': 'missing_authority', 'forwarded_message': 'missing_evidence',
            'not_private_chat': 'missing_evidence', 'unknown_sender': 'missing_authority',
            'ambiguous_sender': 'missing_authority', 'not_current_member': 'missing_authority',
            'not_a_person': 'missing_authority', 'missing_reply_reference': 'missing_evidence',
            'reply_in_another_chat': 'missing_evidence', 'unknown_presentation': 'missing_evidence',
            'presentation_mismatch': 'missing_evidence', 'not_owner': 'missing_authority'}
# The refusals of a message from the attributed, current person that replies to no presentation: no
# reply reference at all, or a reply to a message of this chat that is not a presentation part. The
# intake pass decides what he is told once it has seen the message (VELDO-0126, VELDO-0136).
NOT_A_REPLY = ('missing_reply_reference', 'unknown_presentation')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def bytes_digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def source_digest(update):
    """The digest of one update as the platform delivered it (its canonical JSON bytes)."""
    return bytes_digest(_canonical(update))


def evidence_id(bot, update):
    return 'channel-evidence:%s:%s:%s' % (CHANNEL, bot, update)


def cursor_id(bot):
    return 'channel-acquisition:%s:%s' % (CHANNEL, bot)


def _int(value):
    return value if type(value) is int else None


def _map(value):
    return value if isinstance(value, dict) else {}


def update_kind(update):
    """The one payload type of an update (the Bot API sends at most one beside update_id), or None."""
    kinds = [k for k in _map(update) if k != 'update_id']
    return kinds[0] if len(kinds) == 1 else None


def platform_fields(update):
    """The canonical fields of one update, read only from the platform's own fields: None wherever
    the platform gave no value of the documented type. No display name, username or text is here."""
    update = _map(update)
    kind = update_kind(update)
    message = _map(update.get(kind)) if kind else {}
    chat, sender = _map(message.get('chat')), _map(message.get('from'))
    reply = _map(message.get('reply_to_message'))
    return {'update_id': _int(update.get('update_id')), 'update_kind': kind,
            'message_id': _int(message.get('message_id')), 'date': _int(message.get('date')),
            'chat_id': _int(chat.get('id')), 'chat_type': chat.get('type') if isinstance(chat.get('type'), str) else None,
            'sender_id': _int(sender.get('id')),
            'sender_is_bot': sender.get('is_bot') if type(sender.get('is_bot')) is bool else None,
            'reply_to_message_id': _int(reply.get('message_id')), 'reply_chat_id': _int(_map(reply.get('chat')).get('id')),
            'reply_date': _int(reply.get('date'))}


def missing_fields(fields):
    """The required canonical fields the platform did not give. A message id of 0 is a message the
    platform scheduled and has not sent, which the Bot API says is unusable."""
    missing = [f for f in REQUIRED_FIELDS if fields.get(f) is None]
    if fields.get('message_id') is not None and fields['message_id'] <= 0:
        missing.append('message_id')
    return missing


def automation_reason(message):
    """Why the platform says a message was not sent by a person in person, or None: a bot account;
    a message sent on behalf of a chat (an anonymous administrator or a channel, whose `from` is a
    placeholder user); one sent through an inline bot or by a business bot; one sent by an implicit
    action (an away or greeting message, or a scheduled one); or a channel post forwarded
    automatically into a discussion group."""
    if _map(message.get('from')).get('is_bot') is not False:
        return 'the sender is a bot account'
    if message.get('sender_chat') is not None:
        return 'sent on behalf of a chat'
    if message.get('via_bot') is not None:
        return 'sent through an inline bot'
    if message.get('sender_business_bot') is not None:
        return 'sent by a business bot'
    if message.get('is_from_offline'):
        return 'sent by an implicit action'
    if message.get('is_automatic_forward'):
        return 'forwarded automatically'
    return None


def is_forward(message):
    """Whether the text is a forward, a copy of words someone sent before, the owner's own included."""
    return any(message.get(f) is not None for f in FORWARD_FIELDS)


def sender_principals(enrollments, sender):
    """The principals whose valid Telegram enrollment is this sender's own private chat, matched by
    the platform's stable user id alone: never a display name, a username or any caller's label."""
    return sorted(principal for principal, chat in enrollments.items() if chat == sender['id'])


def replied_problems(receipt, reply, bot):
    """Why the replied-to message the platform delivered is not the presentation part the receipt
    published at that message: it must be this bot's own message, carrying the part's exact bytes and
    the platform date the receipt recorded for that part. A chat and message id alone do not identify
    a presentation: another bot's chat with the same person has the same chat id and numbers its
    messages again. The caller has already looked the receipt up by the message's own chat."""
    ids = receipt.get('message_ids') if isinstance(receipt.get('message_ids'), list) else []
    parts = receipt.get('platform_parts') if isinstance(receipt.get('platform_parts'), list) else []
    if reply.get('message_id') not in ids or len(parts) != len(ids):
        return ['the replied message is not one of the receipt\'s published parts']
    part = _map(parts[ids.index(reply['message_id'])])
    problems = []
    if _map(reply.get('from')).get('id') != bot or _map(reply.get('from')).get('is_bot') is not True:
        problems.append('the replied message was not sent by this bot')
    if reply.get('text') != part.get('text') or reply.get('date') != part.get('date'):
        problems.append('the replied message is not the part as published (its bytes or its platform date)')
    return problems


def evidence_problems(record):
    """Why a kept record is not the evidence of the update it holds, by name: its source digest must
    be the digest of the retained update, its canonical fields the fields read from that update now,
    and its id the id of its bot and update."""
    if not isinstance(record, dict) or any(f not in record for f in EVIDENCE_FIELDS):
        return ['the record is not a channel evidence record']
    problems = []
    if record['schema'] != EVIDENCE_SCHEMA or record['channel'] != CHANNEL:
        problems.append('the record is not a %s %s record' % (EVIDENCE_SCHEMA, CHANNEL))
    if record['source_digest'] != source_digest(record['source']):
        problems.append('the source digest is not the digest of the retained update')
    fields = platform_fields(record['source'])
    if record['fields'] != fields:
        problems.append('the canonical fields are not the fields of the retained update')
    if (type(record['bot_id']) is not int or record['update_id'] != fields['update_id']
            or record['evidence_id'] != evidence_id(record['bot_id'], fields['update_id'])):
        problems.append('the record is not keyed by its bot and update')
    return problems


def _evidence_transition(params, before):
    """`acquire` keeps one update exactly once and moves the bot's cursor past it in the same
    transaction; `decide` records the one decision of a kept update. Nothing is written twice."""
    eid, phase = params.get('evidence_id'), params.get('phase')
    if not isinstance(eid, str) or phase not in ('acquire', 'decide'):
        raise ValueError('an evidence record names its id and phase')
    current = (before.get(eid) or {}).get('data')
    if phase == 'acquire':
        record, cid = params.get('record'), params.get('cursor_id')
        if (current is not None or not isinstance(record, dict) or set(record) != set(EVIDENCE_FIELDS)
                or record.get('evidence_id') != eid or evidence_problems(record) or cid != cursor_id(record['bot_id'])):
            raise ValueError('evidence is kept once, exactly as the platform sent it')
        cursor = (before.get(cid) or {}).get('data') or {}
        if record['update_id'] < cursor.get('next_offset', 0):
            raise ValueError('the update is already confirmed to the platform')
        return {eid: {'kind': EVIDENCE_KIND, 'data': dict(record, **dict(dict.fromkeys(DECISION_FIELDS), outcome='acquired'))},
                cid: {'kind': CURSOR_KIND, 'data': {'schema': CURSOR_SCHEMA, 'channel': CHANNEL, 'bot_id': record['bot_id'],
                                                    'next_offset': record['update_id'] + 1}}}
    if current is None or current.get('outcome') != 'acquired':
        raise ValueError('evidence is decided once')
    outcome, reason = params.get('outcome'), params.get('reason')
    if outcome not in ('answered', 'refused') or (outcome == 'refused') is not isinstance(reason, str):
        raise ValueError('a decision is answered, or refused with its named reason')
    decided = {k: params.get(k) for k in DECISION_FIELDS if k not in ('outcome', 'reason')}
    return {eid: {'kind': EVIDENCE_KIND, 'data': dict(current, outcome=outcome, reason=reason, **decided)}}


class TelegramAcquisitionEdge:
    """The Bot API calls acquisition makes: getMe (the bot's own identity) and getUpdates (the updates
    after the cursor). Only the Bot API's own successful JSON answer counts: a transcript, a proxy page
    or an unreadable body acquires nothing. `projection` is the VELDO-0064 module, whose error answer
    reader and refusal type are reused. `activation` is the VELDO-0073 gate every call asks
    (projection.gated_open); a getMe answer naming another bot than the activated one refuses."""

    def __init__(self, projection, base_url, token, *, timeout=10, activation=None):
        self.P = projection
        if not isinstance(base_url, str) or not base_url.startswith(('https://', 'http://127.0.0.1:')):
            raise projection.EdgeRefused('invalid_input', 'the Bot API origin is https, or a loopback test endpoint')
        if not isinstance(token, str) or not token:
            raise projection.EdgeRefused('invalid_input', 'a token is required')
        self.base_url, self._token, self.timeout = base_url.rstrip('/'), token, timeout
        self.activation = activation

    def _call(self, method, payload):
        EdgeRefused = self.P.EdgeRefused
        request = urllib.request.Request('%s/bot%s/%s' % (self.base_url, self._token, method),
                                         data=json.dumps(payload).encode(), method='POST',
                                         headers={'Content-Type': 'application/json'})
        try:
            with self.P.gated_open(self.activation, self.base_url, request, self.timeout, method) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and self.P.telegram_error_answer(exc, exc.code) is not None:
                raise EdgeRefused('channel_refused', 'HTTP %d' % exc.code) from None
            raise EdgeRefused('unavailable_service', 'HTTP %d without the Bot API error answer' % exc.code) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            raise EdgeRefused('unavailable_service', 'no readable platform answer (%s)' % type(exc).__name__) from None
        try:
            answer = json.loads(body)
        except ValueError:
            raise EdgeRefused('invalid_platform_answer', 'the answer is not the Bot API\'s JSON') from None
        if not isinstance(answer, dict) or answer.get('ok') is not True or 'result' not in answer:
            raise EdgeRefused('invalid_platform_answer', 'the answer is not a successful Bot API answer')
        return answer['result'], body

    def get_me(self):
        """The bot's own User: its stable id and that the platform says it is a bot."""
        result, _ = self._call('getMe', {})
        if not isinstance(result, dict) or type(result.get('id')) is not int or result.get('is_bot') is not True:
            raise self.P.EdgeRefused('invalid_platform_answer', 'getMe did not answer with this bot\'s User')
        self.P.gated_bot(self.activation, result['id'])
        return {'id': result['id'], 'is_bot': True, 'username': result.get('username')}

    def get_updates(self, offset):
        """The updates from `offset` on. Passing an offset confirms every earlier update to the
        platform, so the caller passes one only past updates it has kept."""
        result, body = self._call('getUpdates', {'offset': offset, 'limit': UPDATE_LIMIT, 'timeout': 0,
                                                 'allowed_updates': list(UPDATE_KINDS)})
        if not isinstance(result, list) or not all(isinstance(u, dict) and type(u.get('update_id')) is int for u in result):
            raise self.P.EdgeRefused('invalid_platform_answer', 'getUpdates did not answer with a list of updates')
        return {'updates': result, 'response_digest': bytes_digest(body)}


class Acquirer:
    """Acquires one bot's updates, keeps each as canonical evidence and decides each once.

    `store`, `membership`, `projection` and `presentation` are the control_store, control_membership,
    control_channel_projection and control_channel_presentation modules; `presenter` is the VELDO-0065
    Presenter on the same connection, whose receipts, canonical assertion and answer check are used as
    they are. `edge_principal` is the Telegram edge's service principal and `edge_sign(bytes) -> text`
    signs with its restricted key from the caller's custody. `sign(bytes) -> text` signs journal records
    as `journal_signer`. Observations record identity, accepted versions and outcome, never message
    text, display names, signatures or the token."""

    def __init__(self, store, membership, projection, presentation, presenter, edge, conn, journal_signer, sign,
                 edge_principal, edge_sign, authority_generation=1, clock=time.time):
        self.store, self.membership, self.P, self.V = store, membership, projection, presentation
        self.presenter, self.edge, self.conn = presenter, edge, conn
        self.AC = membership.AC
        self.ids = dict(presenter.ids)
        self.journal_signer, self.sign = journal_signer, sign
        self.edge_principal, self.edge_sign = edge_principal, edge_sign
        self.authority_generation, self.clock = authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}

        def transition(params, before):
            try:
                return _evidence_transition(params, before)
            except ValueError as exc:
                raise store.StoreRefused('invalid_input', str(exc))
        conn.command_registry[EVIDENCE_OPERATION] = {'transition': transition,
                                                     'writes': ('entities', 'journal', 'commands', 'nonces')}

    # reading

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def evidence(self, eid):
        e = self._entity(eid)
        return None if e is None or e['kind'] != EVIDENCE_KIND else dict(e['data'], entity_version=e['version'])

    def _undecided(self, bot):
        rows = []
        for version, text in self.conn.execute('SELECT version, data FROM entities WHERE kind=?', (EVIDENCE_KIND,)):
            data = json.loads(text)
            if data.get('bot_id') == bot and data.get('outcome') == 'acquired':
                rows.append(dict(data, entity_version=version))
        return sorted(rows, key=lambda r: r.get('update_id') or 0)

    def _enrollments(self):
        """{principal: enrolled chat} of every valid Telegram channel enrollment, each at its own
        principal's enrollment id."""
        found = {}
        for eid, text in self.conn.execute('SELECT id, data FROM entities WHERE kind=?', (self.P.ENROLLMENT_KIND,)):
            data = json.loads(text)
            principal = data.get('principal')
            if (isinstance(principal, str) and eid == self.P.enrollment_id(principal)
                    and not self.P.enrollment_problems(self.P.ENROLLMENT_KIND, data, principal)):
                found[principal] = data['chat_id']
        return found

    def _person(self, principal):
        """None when `principal` holds person authority now: an active member of principal type person
        whom the revocation ledger does not name (read exactly as the presenter reads it)."""
        state = self.membership.authority_state(self.store, self.conn)
        entry = self.AC.membership_entry(state['membership'], principal)
        if not self.AC.active_member(entry, self.clock())[0] or self.presenter._ledger_revokes(state, principal):
            return 'not_current_member'
        if entry.get('principal_type') != 'person':
            return 'not_a_person'
        return None

    # observability

    def _observe(self, operation, outcome, reason, versions=None, **extra):
        accepted = outcome in ('acquired', 'answered')
        self.counts['accepted' if accepted else 'refused'] += 1
        error = (None if accepted else 'unknown_outcome' if outcome == 'unknown_outcome'
                 else REFUSALS.get(reason) or self.V.REFUSALS.get(reason, 'unavailable_service'))
        self.observations.append(dict(self.ids, operation=operation, channel=CHANNEL, accepted_versions=dict(versions or {}),
                                      outcome=outcome, reason=reason, error_class=error, **extra))
        result = dict({'outcome': outcome}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    def metrics(self):
        """Accepted and refused operations, kept updates not yet decided (the pending work), answers
        accepted, refused updates by named reason, and of those the messages that replied to no
        presentation (each hinted by the presenter when a request waits for its sender)."""
        rows = [json.loads(t) for (t,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (EVIDENCE_KIND,))]
        refused = {}
        for r in rows:
            if r.get('outcome') == 'refused':
                refused[r.get('reason')] = refused.get(r.get('reason'), 0) + 1
        return dict(self.counts, pending=sum(1 for r in rows if r.get('outcome') == 'acquired'),
                    answered=sum(1 for r in rows if r.get('outcome') == 'answered'), refused_by_reason=refused,
                    not_a_reply=sum(n for reason, n in refused.items() if reason in NOT_A_REPLY))

    # acquisition

    def _commit(self, params, expected, command_id):
        command = dict(command_id=command_id, principal=self.journal_signer, operation=EVIDENCE_OPERATION,
                       parameters=params, expected_versions=expected, artifact_digests=[], nonce=command_id)
        return self.store.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)

    def _keep(self, bot, update, response_digest):
        """Keep one update as evidence and move the cursor past it, in one transaction."""
        eid, cid = evidence_id(bot, update['update_id']), cursor_id(bot)
        if self._entity(eid) is not None:
            return None
        cursor = self._entity(cid)
        record = {'schema': EVIDENCE_SCHEMA, 'channel': CHANNEL, 'evidence_id': eid, 'bot_id': bot,
                  'update_id': update['update_id'], 'source': update, 'source_digest': source_digest(update),
                  'response_digest': response_digest, 'fields': platform_fields(update)}
        versions = {eid: 0, cid: cursor['version'] if cursor else 0}
        try:
            self._commit(dict(phase='acquire', evidence_id=eid, cursor_id=cid, record=record), versions, eid + ':acquire')
        except self.store.StoreRefused as exc:
            return self._observe('acquire', 'refused', exc.code, versions, update_id=update['update_id'], bot_id=bot)
        except sqlite3.Error:
            return self._observe('acquire', 'refused', 'unavailable_service', versions, update_id=update['update_id'], bot_id=bot)
        self._observe('acquire', 'acquired', None, versions, update_id=update['update_id'], evidence_id=eid, bot_id=bot)
        return None

    def acquire(self):
        """One run over the platform exchange: ask the platform who this bot is, fetch the updates after
        the cursor, keep each as evidence (confirmed to the platform only once kept), then decide every
        kept update of this bot not yet decided, in update order. Returns one result per decided update
        and per refused platform call or store write."""
        try:
            bot = self.edge.get_me()['id']
        except self.P.EdgeRefused as exc:
            return [self._observe('acquire', 'refused', exc.code)]
        results = []
        cid = cursor_id(bot)
        cursor = self._entity(cid)
        offset = cursor['data'].get('next_offset', 0) if cursor is not None and cursor['kind'] == CURSOR_KIND else 0
        try:
            batch = self.edge.get_updates(offset)
        except self.P.EdgeRefused as exc:
            results.append(self._observe('acquire', 'refused', exc.code, {cid: cursor['version'] if cursor else 0}, bot_id=bot))
            batch = {'updates': [], 'response_digest': None}
        for update in sorted(batch['updates'], key=lambda u: u['update_id']):
            if update['update_id'] >= offset:
                kept = self._keep(bot, update, batch['response_digest'])
                if kept is not None:
                    results.append(kept)
        for record in self._undecided(bot):
            results.append(self._decide(record))
        return results

    # attribution

    def attribute(self, record):
        """(refusal, known): whether one kept update is an attributed answer to a presentation, and what
        was established on the way (principal, request and presentation, and the canonical assertion
        when nothing refuses). Every check reads the retained platform update; nothing a caller writes
        counts."""
        known = {'principal': None, 'request_id': None, 'presentation_id': None, 'assertion': None}
        if evidence_problems(record):
            return 'evidence_mismatch', known
        fields = record['fields']
        if fields['update_kind'] == 'edited_message':
            return 'edited_message', known
        if fields['update_kind'] != 'message':
            return 'unsupported_update', known
        if missing_fields(fields):
            return 'missing_canonical_field', known
        message = record['source']['message']
        if automation_reason(message):
            return 'automation_sender', known
        if is_forward(message):
            return 'forwarded_message', known
        if fields['chat_type'] != 'private' or fields['chat_id'] != fields['sender_id']:
            return 'not_private_chat', known
        principals = sender_principals(self._enrollments(), message['from'])
        if not principals:
            return 'unknown_sender', known
        if len(principals) > 1:
            return 'ambiguous_sender', known
        known['principal'] = principals[0]
        refusal = self._person(known['principal'])
        if refusal:
            return refusal, known
        reply = message.get('reply_to_message')
        if not isinstance(reply, dict):
            return ('reply_in_another_chat' if message.get('external_reply') is not None
                    else 'missing_reply_reference'), known
        if fields['reply_to_message_id'] is None or fields['reply_chat_id'] is None:
            return 'missing_reply_reference', known
        if fields['reply_chat_id'] != fields['chat_id']:
            return 'reply_in_another_chat', known
        receipt = self.presenter.receipt_for_message(fields['chat_id'], fields['reply_to_message_id'])
        if receipt is None:
            return 'unknown_presentation', known
        known.update(request_id=receipt['request_id'], presentation_id=receipt['presentation_id'])
        if replied_problems(receipt, reply, record['bot_id']):
            return 'presentation_mismatch', known
        if known['principal'] != receipt['owner']:
            return 'not_owner', known
        try:
            assertion = self.presenter.canonical_answer(message, self.edge_principal)
        except self.V.Refused as exc:
            return exc.code, known
        if assertion.get('presentation_id') != receipt['presentation_id']:
            return 'presentation_mismatch', known
        assertion['principal'] = known['principal']
        assertion['attribution'] = dict(assertion['attribution'], update_id=fields['update_id'],
                                        evidence_id=record['evidence_id'], evidence_digest=record['source_digest'],
                                        bot_id=record['bot_id'], chat_type=fields['chat_type'], sender_type='person')
        known['assertion'] = assertion
        return None, known

    def _edge_signature(self, assertion):
        try:
            signature = self.edge_sign(self.store.canonical_bytes(assertion))
        except Exception:  # noqa: BLE001 - a custody failure signs nothing and is named, never raised past the run
            return None
        return signature if isinstance(signature, str) and signature.isascii() and signature.strip() else None

    def _decide(self, record):
        eid, fields = record['evidence_id'], record.get('fields') or {}
        refusal, known = self.attribute(record)
        answer = None
        if refusal is None:
            signature = self._edge_signature(known['assertion'])
            if signature is None:
                refusal = 'unavailable_service'
            else:
                result = self.presenter.answer({'assertion': known['assertion'], 'signature': signature})
                if result.get('outcome') == 'accepted':
                    answer = result.get('answer_id')
                else:
                    refusal = result.get('reason') or 'unknown_outcome'
        outcome = 'answered' if refusal is None else 'refused'
        decided = dict(principal=known['principal'], request_id=known['request_id'],
                       presentation_id=known['presentation_id'], answer_id=answer)
        versions = {eid: record['entity_version']}
        about = dict(update_id=record.get('update_id'), evidence_id=eid, bot_id=record.get('bot_id'),
                     chat_id=fields.get('chat_id'), sender_id=fields.get('sender_id'), **decided)
        try:
            self._commit(dict(phase='decide', evidence_id=eid, outcome=outcome, reason=refusal, **decided), versions,
                         eid + ':decide')
        except (self.store.StoreRefused, sqlite3.Error):
            # The decision was taken but not recorded: its outcome is unknown, never reported as success.
            return self._observe('attribute', 'unknown_outcome', 'incomplete_transaction', versions, **about)
        # A message refused as NOT_A_REPLY is not hinted here: the VELDO-0126 intake pass, which sees
        # it next, makes the one decision about what the owner is told (VELDO-0136).
        return self._observe('attribute', outcome, refusal, versions, **about)

    # verification

    def answer_problems(self, answer, evidence):
        """Why an accepted answer record is not bound, by its canonical evidence, to the presentation it
        names; [] when it is. The evidence must bind its retained update; the answer's platform
        attribution must be the evidence's own fields and identity; its principal the one the evidence
        was attributed to; its presentation the published part the evidence replies to, as published;
        and its choice the offered choice the owner's text names, with that choice's ruling."""
        answer = answer if isinstance(answer, dict) else {}
        problems = evidence_problems(evidence)
        if problems:
            return problems
        f, ev = evidence['fields'], _map(answer.get('attribution'))
        wanted = {'platform_message_id': f['message_id'], 'sender_id': f['sender_id'], 'platform_timestamp': f['date'],
                  'chat_id': f['chat_id'], 'reply_to_message_id': f['reply_to_message_id'], 'update_id': f['update_id'],
                  'evidence_id': evidence['evidence_id'], 'evidence_digest': evidence['source_digest'],
                  'bot_id': evidence['bot_id']}
        problems += ['the answer\'s %s is not the evidence\'s' % k for k, v in wanted.items() if ev.get(k) != v]
        if answer.get('principal') is None or answer.get('principal') != evidence.get('principal'):
            problems.append('the answer\'s principal is not the principal the evidence was attributed to')
        receipt = self.presenter.receipt(answer.get('presentation_id') or '')
        message = _map(_map(evidence['source']).get('message'))
        if receipt is None or evidence.get('presentation_id') != receipt['presentation_id']:
            return problems + ['the answer names no presentation the evidence replies to']
        if replied_problems(receipt, _map(message.get('reply_to_message')), evidence['bot_id']):
            problems.append('the evidence does not reply to the named presentation as published')
        if (answer.get('request_id'), answer.get('request_version')) != (receipt['request_id'], receipt['request_version']):
            problems.append('the answer names another request version than its presentation')
        typed, _ = self.V.split_reply(message.get('text'))
        choice = self.V.offered_choice(typed, receipt['choices'])
        if choice is None or answer.get('choice') != choice or answer.get('ruling') != self.V.ruling_of(choice):
            problems.append('the answer\'s choice and ruling are not the offered choice the owner\'s text names')
        return problems
