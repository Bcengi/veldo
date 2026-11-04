"""Every conversation reply where the owner wrote, and every message the factory sends in a conversation recorded
(VELDO-0175).

WHAT IS SENT. A turn whose message came from Telegram (its intake source is a `telegram_message`) gets its reply,
the engine's final result text kept on the turn record (control_conversation `final_reply`), sent to the chat he
wrote from through the Telegram edge with VELDO-0168's text rules: every invisible character escaped and the ends
the platform would trim kept, split in order into parts that each fit one Telegram message (control_channel_presentation
`_chunks`, whitespace cuts first), the first a reply to his message. A turn that ends with no result text (failed,
`account_limit`, `outcome_unknown`, any outcome but `completed`) gets one status line naming the outcome and what
happens next in place of a reply, and so does each run of a turn stopped at its account's limit and returned to
waiting. A turn whose message came from the API sends nothing: its reply is on its record, the conversation's API
read.

WHAT IS RECORDED. Each part and line, once the platform confirmed it, by control_conversation's
`record_conversation_message`: its bot, chat and message id bound to the conversation and turn, so a reply to any
part continues the conversation (control_intake). A part already recorded is never sent again, so a later pass
sends only what is missing.

`answer` sends the one line intake answers an owner's message with (a command's change, a refusal) and records it
under that message, so a redelivered message is never answered twice; a command's answer is a conversation message
too. Observations carry ids, counts and outcomes, never text. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('conversation_channel_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CV = _organ('control_conversation')
V = _organ('control_channel_presentation')
TEXT = V.TEXT
SCHEMA = 'veldo.conversation_delivery/v1'
SOURCE_KIND = 'intake_source'
EDGE_ROOM = 256
NEXT = {
    'account_limit': 'It runs again on another account, or you are asked first.',
    'outcome_unknown': 'The conversation keeps its last capture; your next message continues it.',
}
DEFAULT_NEXT = 'Nothing more runs for this turn; reply to this message to continue the conversation.'


def parts(reply, stats=None):
    """VELDO-0175 AC3: the reply as the Telegram messages that show it, in order, each within the platform limit:
    VELDO-0168's text rules (invisible characters escaped, the trimmed ends kept), cut at whitespace when it can be,
    nothing dropped."""
    shown = TEXT.visible(TEXT.lines(reply), stats)
    if V.utf16_units(TEXT.edges(shown)) <= V.MESSAGE_LIMIT:
        return [TEXT.edges(shown, stats)]
    # A soft cut opens the next part with the whitespace run it was made at; that run is shown escaped (the platform
    # trims it), so each part leaves room for its escaped ends.
    room = V.MESSAGE_LIMIT - EDGE_ROOM
    pieces = [TEXT.edges(piece, stats) for piece in V._chunks(shown, room, stats)]
    if any(V.utf16_units(piece) > V.MESSAGE_LIMIT for piece in pieces):
        raise ValueError('reply_part_too_long')
    return pieces


def status_line(sequence, outcome, limited=False):
    """The one status line of a turn that ended, or stopped, with no result text: its outcome and what happens next."""
    if limited:
        return 'Turn %d stopped at an account limit (account_limit) with no reply yet. %s' % (sequence, NEXT['account_limit'])
    return 'Turn %d ended %s with no reply. %s' % (sequence, outcome, NEXT.get(outcome, DEFAULT_NEXT))


def telegram_source(conn, turn):
    """The Telegram provenance of a turn's message ({bot_id, chat_id, message_id}), or None for any other source."""
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(turn.get('intake_command')),)).fetchone()
    if row is None or row[0] != SOURCE_KIND:
        return None
    source = json.loads(row[1])
    where = (source.get('command') or {}).get('provenance') or {}
    if source.get('source_kind') != 'telegram_message' or not all(
            type(where.get(k)) is int for k in ('bot_id', 'chat_id', 'message_id')):
        return None
    return {k: where[k] for k in ('bot_id', 'chat_id', 'message_id')}


class Messages:
    """The recorder of conversation messages over one store connection, signed by `principal` (the journal signer)."""

    def __init__(self, store, conn, principal, sign, generation=1, observe=None):
        self.store, self.conn, self.principal, self.sign, self.generation = store, conn, principal, sign, generation
        self.observe = observe or (lambda event: None)
        conn.command_registry[CV.OPERATION] = {'transaction_transition': CV.transition,
                                               'writes': ('entities', 'journal', 'commands', 'nonces')}

    def _version(self, eid):
        row = self.conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
        return row[0] if row else 0

    def record(self, kind, sent, *, bot, conversation=None, sequence=None, part=None, parts=None, ref=None,
               answers=None):
        """Record one sent message (`sent`: the edge's confirmed {chat_id, message_id, date, reply_to_message_id})."""
        params = {'operation': CV.SENT, 'kind': kind, 'conversation': conversation, 'sequence': sequence,
                  'part': part, 'parts': parts, 'ref': ref, 'bot_id': bot, 'chat_id': sent['chat_id'],
                  'message_id': sent['message_id'], 'date': sent['date'],
                  'reply_to': sent.get('reply_to_message_id'), 'answers': answers, 'principal': self.principal}
        ids = []
        if kind != 'refusal':
            ids += [CV.conversation_id(conversation), CV.sent_id(bot, sent['chat_id'], sent['message_id'])]
        if kind in ('reply', 'status'):
            ids.append(CV.turn_id(conversation, sequence))
        if answers is not None:
            ids.append(CV.answer_id(bot, sent['chat_id'], answers))
        cid = 'conversation-message/%s/%s/%s' % (bot, sent['chat_id'], sent['message_id'])
        command = {'command_id': cid, 'principal': self.principal, 'operation': CV.OPERATION, 'parameters': params,
                   'expected_versions': {eid: self._version(eid) for eid in ids}, 'artifact_digests': [],
                   'nonce': cid}
        self.store.execute(self.conn, command, self.principal, self.sign, self.generation)
        self.observe({'schema': SCHEMA, 'operation': 'conversation_message', 'kind': kind,
                      'conversation': conversation, 'sequence': sequence, 'part': part, 'parts': parts,
                      'bot_id': bot, 'chat_id': sent['chat_id'], 'message_id': sent['message_id'],
                      'reply_to': sent.get('reply_to_message_id'), 'outcome': 'recorded'})

    def answered(self, bot, chat, message):
        return self.conn.execute('SELECT 1 FROM entities WHERE id=?', (CV.answer_id(bot, chat, message),)).fetchone() \
            is not None

    def answer(self, edge, where, text, *, kind='answer', conversation=None, sequence=None, ref=None):
        """Send `text` as the one line answering the owner's message at `where` ({bot_id, chat_id, message_id}) and
        record it; a message already answered is not answered again. Returns the outcome."""
        bot, chat, message = where['bot_id'], where['chat_id'], where['message_id']
        if self.answered(bot, chat, message):
            return {'outcome': 'already_answered'}
        try:
            sent = edge.send(chat, TEXT.message(text), reply_to=message)
        except Exception as error:  # noqa: BLE001 - a failed send is named, never raised past intake
            self.observe({'schema': SCHEMA, 'operation': 'conversation_answer', 'kind': kind, 'conversation': conversation,
                          'outcome': 'refused', 'refusal': getattr(error, 'code', type(error).__name__)})
            return {'outcome': 'refused', 'reason': getattr(error, 'code', 'unknown_outcome')}
        try:
            self.record(kind, sent, bot=bot, conversation=conversation, sequence=sequence, ref=ref, answers=message)
        except Exception as error:  # noqa: BLE001 - sent but not recorded: named
            return {'outcome': 'unknown_outcome', 'reason': getattr(error, 'code', type(error).__name__),
                    'message_id': sent['message_id']}
        return {'outcome': 'sent', 'message_id': sent['message_id']}


class Replies(Messages):
    """THE DELIVERY: every Telegram turn's reply parts or status line not yet sent, sent and recorded."""

    def __init__(self, store, conn, principal, sign, edge, generation=1, observe=None, clock=time.time):
        super().__init__(store, conn, principal, sign, generation, observe)
        self.edge, self.clock = edge, clock
        self.counts = {'parts_sent': 0, 'status_sent': 0, 'refused': 0}

    def _turns(self):
        turns = [json.loads(raw) for (raw,) in self.conn.execute('SELECT data FROM entities WHERE kind=?',
                                                                 (CV.TURN_KIND,))]
        return sorted(turns, key=lambda t: (t.get('arrival') or 0, str(t.get('conversation')), t.get('sequence') or 0))

    def due(self, turn):
        """What a turn still has to send: [(kind, ref, part, parts, text)] in order."""
        sent = {(s.get('kind'), s.get('ref'), s.get('part')) for s in turn.get('sent') or []}
        sequence, wanted = turn['sequence'], []
        for limit in turn.get('limits') or []:
            ref = 'limit:%s' % limit.get('dispatch_id')
            wanted.append(('status', ref, 1, 1, status_line(sequence, CV.LIMITED, limited=True)))
        if turn.get('state') == 'ended':
            reply = turn.get('reply') if 'reply' in turn else None
            ref = 'end:%s' % turn.get('dispatch_id')
            if turn.get('outcome') == 'completed' and isinstance(reply, str) and reply.strip():
                pieces = parts(reply)
                wanted += [('reply', ref, n, len(pieces), piece) for n, piece in enumerate(pieces, 1)]
            elif not (turn.get('outcome') == CV.LIMITED and any(
                    'limit:%s' % turn.get('dispatch_id') == w[1] for w in wanted)):
                wanted.append(('status', ref, 1, 1, status_line(sequence, turn.get('outcome'))))
        return [w for w in wanted if (w[0], w[1], w[2]) not in sent]

    def deliver(self):
        """Send what every Telegram turn still has to send, in order; a refused send stops that turn until the next
        pass. Returns one {conversation, sequence, kind, part, parts, outcome} per message tried."""
        results = []
        for turn in self._turns():
            if not (turn.get('state') == 'ended' or turn.get('limits')):
                continue
            where = telegram_source(self.conn, turn)
            if where is None:
                continue
            try:
                due = self.due(turn)
            except ValueError as error:  # a reply no part can hold is named, never raised past the pass
                results.append({'conversation': turn['conversation'], 'sequence': turn['sequence'], 'kind': 'reply',
                                'outcome': 'refused', 'reason': str(error)})
                continue
            for kind, ref, part, count, text in due:
                about = {'conversation': turn['conversation'], 'sequence': turn['sequence'], 'kind': kind,
                         'part': part, 'parts': count}
                reply_to = where['message_id'] if part == 1 else None
                try:
                    sent = self.edge.send(where['chat_id'], text, reply_to=reply_to)
                except Exception as error:  # noqa: BLE001 - the next pass sends what is missing
                    self.counts['refused'] += 1
                    results.append(dict(about, outcome='refused', reason=getattr(error, 'code', type(error).__name__)))
                    self.observe(dict(about, schema=SCHEMA, operation='conversation_reply', outcome='refused',
                                      refusal=results[-1]['reason']))
                    break
                try:
                    self.record(kind, sent, bot=where['bot_id'], conversation=turn['conversation'],
                                sequence=turn['sequence'], part=part, parts=count, ref=ref)
                except Exception as error:  # noqa: BLE001 - sent and not recorded: named, and the pass goes on
                    results.append(dict(about, outcome='unknown_outcome', message_id=sent['message_id'],
                                        reason=getattr(error, 'code', type(error).__name__)))
                    break
                self.counts['parts_sent' if kind == 'reply' else 'status_sent'] += 1
                results.append(dict(about, outcome='sent', message_id=sent['message_id'], chat_id=sent['chat_id']))
                self.observe(dict(about, schema=SCHEMA, operation='conversation_reply', outcome='sent',
                                  chat_id=sent['chat_id'], message_id=sent['message_id'],
                                  reply_to=sent.get('reply_to_message_id'), turn=CV.turn_id(turn['conversation'],
                                                                                            turn['sequence'])))
        return results

    def metrics(self):
        """Reply parts and status lines sent, refused sends, and recorded conversation messages by kind."""
        recorded = {}
        for (raw,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (CV.SENT_KIND,)):
            kind = json.loads(raw).get('kind')
            recorded[kind] = recorded.get(kind, 0) + 1
        return dict(self.counts, recorded=recorded)


def digest(text):
    return 'sha256:' + hashlib.sha256(text.encode()).hexdigest()
