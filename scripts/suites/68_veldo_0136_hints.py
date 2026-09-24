"""The owner told to reply to the request message, over a real signed store and a loopback Bot API (VELDO-0136).

An owner who answers without pressing Reply, or replies to a bot message that is not a presentation,
is told once how to answer while a request of his waits. His messages reach the edge the way Telegram
delivers them: a loopback Bot API endpoint over real HTTP answers getMe, getUpdates and sendMessage in
the platform's documented shapes (Update, Message, User, Chat), keeps the messages the bot published
and the updates it holds, and confirms updates by offset. Presentations are VELDO-0065's, acquisition
and attribution VELDO-0066's, both run through their production entry points (Presenter.present,
Acquirer.acquire). Every journal record and edge assertion carries a real OpenSSH signature. This is
not the Telegram service: no network or real token is used. Mutation workers replace the production
module copies below, never assertions or fixtures. On a tree without hints the rows still run through
the same entry points, so they fail by their own assertions rather than by an exception.
"""
import http.server as _v136_http
import importlib.util as _v136_import
import json as _v136_json
import os as _v136_os
from pathlib import Path as _v136_Path
import shutil as _v136_shutil
import subprocess as _v136_sp
import tempfile as _v136_temp
import threading as _v136_threading
import time as _v136_time


def _v136_load(name, path):
    spec = _v136_import.spec_from_file_location(name, path)
    module = _v136_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _V136BotApi(_v136_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes for one bot."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = _v136_json.loads(raw) if raw else {}
        _, _, rest = self.path.partition('/bot')
        token, _, method = rest.partition('/')
        if token != st['token']:
            return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
        if method == 'getMe':
            return self._answer(200, {'ok': True, 'result': dict(st['bot'], can_join_groups=True,
                                                                 can_read_all_group_messages=False,
                                                                 supports_inline_queries=False)})
        if method == 'getUpdates':
            offset = body.get('offset') or 0
            if offset:
                st['updates'] = [u for u in st['updates'] if u['update_id'] >= offset]  # earlier ones are confirmed
            return self._answer(200, {'ok': True, 'result': st['updates'][:body.get('limit') or 100]})
        if method == 'sendMessage':
            if len(body.get('text', '').encode('utf-16-le')) // 2 > 4096:
                return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: message is too long'})
            chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
            reply = (body.get('reply_parameters') or {}).get('message_id')
            if reply is not None and (chat['id'], reply) not in st['messages']:
                reply = None  # allow_sending_without_reply: sent as an ordinary message, as Telegram does
            message = _v136_message(st, st['bot'], chat, body['text'], reply)
            st['sent'].append(message)
            return self._answer(200, {'ok': True, 'result': message})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = _v136_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _v136_message(st, sender, chat, text, reply_to=None, **extra):
    """One message as the platform keeps and delivers it: its id, the platform's date, the sender's
    User, the chat, the text and, for a reply, the replied message as the platform holds it."""
    st['next'] += 1
    message = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1790000000 + st['next'],
               'text': text}
    if reply_to is not None:
        held = st['messages'][(chat['id'], reply_to)]
        message['reply_to_message'] = _v136_json.loads(_v136_json.dumps(
            {k: v for k, v in held.items() if k != 'reply_to_message'}))
    message.update(extra)
    st['messages'][(chat['id'], message['message_id'])] = message
    return message


def _v136_checks(base):
    rows = {name: [] for name in ('hint/tells-owner-to-reply', 'hint/owner-only-never-an-answer',
                                  'hint/once-per-pending-request')}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    contract = _v136_load('v136_contract', ROOT / '.veldo' / 'entity_contract.py')
    organs = base / 'organs'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v136_shutil.copyfile(source, organs / source.name)
    claims = _v136_load('v136_claims', organs / 'control_claim.py')
    S, CM, AUTHC = claims.S, claims.CM, claims.AC
    I = _v136_load('v136_inbox', organs / 'control_assignment.py')
    P = _v136_load('v136_projection', organs / 'control_channel_projection.py')
    # The production copies under test; mutation workers replace exactly these paths.
    V = _v136_load('v136_presentation', ROOT / ".veldo" / "control_channel_presentation.py")
    A = _v136_load('v136_attribution', ROOT / ".veldo" / "control_channel_attribution.py")

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'pm', 'telegram-edge'):
        _v136_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v136-' + who, '-f', str(keys / who)],
                     check=True, capture_output=True, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()

    def sign_as(who, message, namespace=AUTHC.SIGNATURE_NAMESPACE):
        return _v136_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                            capture_output=True, check=True, timeout=10).stdout.decode()

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    def edge_sign(message):
        return sign_as('telegram-edge', message)

    ids = dict(domain_uuid='hint-domain', repository_uuid='hint-repository', store_uuid='hint-store')
    conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
    serial = [0]

    def fixture(eid, kind, data):
        serial[0] += 1
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    person = dict(principal_type='person', roles=[], scope=['project-a'])
    members = {'owner': dict(principal_type='person', roles=['project_owner'], scope=['project-a']),
               'owner3': dict(person), 'stranger': dict(person),
               'pm': dict(principal_type='service', roles=[], scope=['project-a']),
               'telegram-edge': dict(principal_type='service', roles=[], scope=['project-a'])}
    for who, data in members.items():
        fixture(who, 'membership', dict(data, revoked_at=None, expires_at=None))
    fixture('key-pm', 'verification_key', dict(principal='pm', public_key=public['pm'], effective_at=0))
    fixture(AUTHC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
            dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
    owner_chat, owner3_chat, stranger_chat, nobody_chat = 5560001, 5560002, 5560003, 5560099
    for who, chat in (('owner', owner_chat), ('owner3', owner3_chat), ('stranger', stranger_chat)):
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))

    def user(uid, first, is_bot=False):
        return {'id': uid, 'is_bot': is_bot, 'first_name': first, 'language_code': 'en'}

    def private(person_user):
        """The private Chat of a person with the bot: Telegram gives it the person's own user id."""
        return {'id': person_user['id'], 'type': 'private', 'first_name': person_user['first_name']}

    owner_user, owner3_user = user(owner_chat, 'Owner'), user(owner3_chat, 'Third')
    stranger_user, nobody_user = user(stranger_chat, 'Stranger'), user(nobody_chat, 'Nobody')
    bot_account = user(8300000001, 'Owner', is_bot=True)
    inline = {'id': 8200000001, 'is_bot': True, 'first_name': 'Inline helper', 'username': 'inline_helper_bot'}
    api = {'token': 'sandbox-bot', 'bot': {'id': 8000000001, 'is_bot': True, 'first_name': 'Veldo',
                                           'username': 'veldo_example_bot'},
           'next': 9000, 'update_next': 600000000, 'messages': {}, 'updates': [], 'sent': [], 'chats': {}}
    for someone in (owner_user, owner3_user, stranger_user, nobody_user, bot_account):
        api['chats'][someone['id']] = private(someone)
    handler = type('V136Handler', (_V136BotApi,), {'state': api})
    server = _v136_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v136_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:%d' % server.server_address[1]
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'sandbox-bot'), conn, 'authority',
                            journal_sign, assignment=I)
    acquirer = A.Acquirer(S, CM, P, V, presenter, A.TelegramAcquisitionEdge(P, url, 'sandbox-bot'), conn,
                          'authority', journal_sign, 'telegram-edge', edge_sign)
    counter = [0]

    def signed(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    def open_framed(alias, owner='owner'):
        counter[0] += 1
        inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id='c-%d' % counter[0],
                                      nonce='n-%d' % counter[0], assignment=dict(
                                          kind='decision', owner=owner, scope=['project-a'],
                                          deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                          brief='Choose how the example specification proceeds.',
                                          choices=['accept', 'reject'],
                                          subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md',
                                                   'digest': 'sha256:' + '1' * 64}))))
        presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                          risk_statement='Low: a wrong choice costs one review cycle.',
                                          command_id='f-%d' % counter[0], nonce='fn-%d' % counter[0])))
        rid = I.assignment_id(ids['repository_uuid'], alias)
        presenter.present(rid)
        return rid, presenter.current(rid) or {}

    def say(sender, text, reply_to=None, chat=None, **extra):
        """A message a Telegram account sends to the bot, held by the platform as an Update."""
        message = _v136_message(api, sender, chat or private(sender), text, reply_to, **extra)
        api['update_next'] += 1
        update = {'update_id': api['update_next'], 'message': message}
        api['updates'].append(update)
        return update

    def acquire():
        return {r['update_id']: (r.get('outcome'), r.get('reason')) for r in acquirer.acquire()
                if r.get('update_id') is not None}

    def entity(eid):
        row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': _v136_json.loads(row[2])}

    def kind_count(kind):
        return conn.execute('SELECT count(*) FROM entities WHERE kind=?', (kind,)).fetchone()[0]

    def answered(rid):
        """The answer record of a request at version 1, read from the store itself."""
        for (text,) in conn.execute("SELECT data FROM entities WHERE kind='presentation_answer'"):
            data = _v136_json.loads(text)
            if data.get('request_id') == rid and data.get('request_version') == 1:
                return data
        return None

    def evidence_of(update):
        found = entity('channel-evidence:telegram_chat:%d:%d' % (api['bot']['id'], update['update_id']))
        return (found or {}).get('data') or {}

    def hint_of(update):
        """The hint kept for one inbound message, at the id spelled here: its chat and message id."""
        m = update['message']
        found = entity('presentation-hint:telegram_chat:%d:%d' % (m['chat']['id'], m['message_id']))
        return found if found is not None and found['kind'] == 'presentation_hint' else None

    def sent_since(mark):
        return api['sent'][mark:]

    def request_line(rid):
        return 'Request: %s (version 1)' % rid

    def is_hint(message, update, rids):
        """A bot message in the sender's chat, replying to his message, telling him to reply to the
        request message and naming exactly the given requests."""
        text = message.get('text') or ''
        return (message['chat']['id'] == update['message']['chat']['id']
                and (message.get('reply_to_message') or {}).get('message_id') == update['message']['message_id']
                and 'press Reply on the request message' in text
                and sorted(line.split(' (version')[0][len('Request: '):] for line in text.split('\n')
                           if line.startswith('Request: ')) == sorted(rids))

    def answer_all(receipts, row):
        """The owner answers each request by replying to its presentation, as the control."""
        mark = len(api['sent'])
        replies = [say(owner_user, 'accept: fits the plan', reply_to=r.get('message_id')) for r in receipts]
        got = acquire()
        check(row, 'control: replying to each presentation records each answer and sends nothing back',
              all(got.get(u['update_id']) == ('answered', None) for u in replies)
              and all(answered(r.get('request_id')) is not None for r in receipts) and sent_since(mark) == [])

    class section:
        """One criterion section: an exception is recorded as that row's failure and the run goes on,
        so every row reports even against code whose interface differs."""

        def __init__(self, row):
            self.row = row

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                check(self.row, 'the section ran to its end (it raised %s)' % kind.__name__, False)
            return True

    try:
        # AC1: a message that replies to no presentation, while requests of his wait, is answered once
        # with how to answer: reply to the request message, naming each waiting request.
        tell = 'hint/tells-owner-to-reply'
        with section(tell):
            hinted_updates = []
            for count in (1, 2):
                for how in ('a plain message', 'a reply to the bot\'s help message', 'a reply to another bot message'):
                    opened = [open_framed('AC1-%d-%s-%d' % (count, how.split()[-2], n)) for n in range(count)]
                    rids, receipts = [o[0] for o in opened], [o[1] for o in opened]
                    if how == 'a plain message':
                        cause, u = 'missing_reply_reference', say(owner_user, 'accept: fits the plan')
                    elif how == 'a reply to another bot message':
                        welcome = _v136_message(api, api['bot'], private(owner_user), 'Welcome to Veldo.')
                        cause, u = 'unknown_presentation', say(owner_user, 'accept: fits the plan',
                                                               reply_to=welcome['message_id'])
                    else:
                        # The bot's help message: what the presenter says to a reply naming no offered choice.
                        wrong = say(owner_user, 'maybe: later', reply_to=receipts[0].get('message_id'))
                        mark = len(api['sent'])
                        helped = acquire()
                        help_message = next(iter(sent_since(mark)), {})
                        check(tell, 'precondition: a reply naming no choice gets the help message with the choices',
                              helped.get(wrong['update_id']) == ('refused', 'unmatched_choice')
                              and 'accept | reject' in help_message.get('text', ''))
                        cause, u = 'unknown_presentation', say(owner_user, 'accept: fits the plan',
                                                               reply_to=help_message.get('message_id'))
                    mark = len(api['sent'])
                    got = acquire()
                    out = sent_since(mark)
                    label = '%s with %d waiting request%s' % (how, count, 's' if count > 1 else '')
                    check(tell, '%s is refused as %s' % (label, cause), got.get(u['update_id']) == ('refused', cause))
                    check(tell, '%s gets exactly one message back: a reply to it saying to reply to the request message, '
                                'naming every waiting request' % label,
                          len(out) == 1 and is_hint(out[0], u, rids))
                    kept = hint_of(u) or {'data': {}}
                    check(tell, '%s: the hint is kept with the platform\'s answer, joined by identity to the message, its '
                                'evidence and the presentations it names' % label,
                          kept['data'].get('outcome') == 'sent' and len(out) == 1
                          and (kept['data'].get('platform') or {}).get('message_id') == out[0]['message_id']
                          and kept['data'].get('evidence_id') == evidence_of(u).get('evidence_id') is not None
                          and kept['data'].get('update_id') == u['update_id'] and kept['data'].get('cause') == cause
                          and sorted(r.get('presentation_id') for r in kept['data'].get('requests') or [])
                          == sorted(r.get('presentation_id') for r in receipts))
                    hinted_updates.append((u, cause))
                    answer_all(receipts, tell)
            observed = [o for o in presenter.observations if o.get('operation') == 'hint_owner']
            text = _v136_json.dumps(observed)
            check(tell, 'each hinted message is observed with its cause, evidence, update, hint and named requests, never text',
                  [(o.get('update_id'), o.get('cause'), o.get('outcome')) for o in observed]
                  == [(u['update_id'], cause, 'sent') for u, cause in hinted_updates]
                  and all(o.get('evidence_id') and o.get('hint_id') and o.get('request_ids') and o.get('presentation_ids')
                          and o.get('hint_message_id') for o in observed)
                  and not any(s in text for s in ('fits the plan', 'press Reply', 'Owner', 'sandbox-bot')))
            check(tell, 'metrics count the hints sent and the owner messages refused as not a reply',
                  presenter.metrics().get('hints_sent') == 6 and acquirer.metrics().get('not_a_reply') == 6)

        # AC2: a hint never records an answer and never reaches anyone but the current enrolled owner.
        only = 'hint/owner-only-never-an-answer'
        with section(only):
            h, rh = open_framed('AC2-H')
            h3, rh3 = open_framed('AC2-H3', owner='owner3')
            fixture('owner3', 'membership', dict(members['owner3'], revoked_at=_v136_time.time() - 1, expires_at=None))
            answers_before = kind_count('presentation_answer')
            mark = len(api['sent'])
            u_owner = say(owner_user, 'accept: this names a choice but replies to nothing')
            u_stranger = say(stranger_user, 'accept: go')
            u_nobody = say(nobody_user, 'accept: go')
            u_revoked = say(owner3_user, 'accept: go')
            u_bot = say(bot_account, 'accept: go')
            u_inline = say(owner_user, 'accept: go', via_bot=inline)
            try:
                got = acquire()
            finally:
                fixture('owner3', 'membership', dict(members['owner3'], revoked_at=None, expires_at=None))
            out = sent_since(mark)
            check(only, 'the owner\'s plain message is refused as not a reply and gets its one hint naming his request',
                  got.get(u_owner['update_id']) == ('refused', 'missing_reply_reference')
                  and [m for m in out if m['chat']['id'] == owner_chat] != [] and all(
                      is_hint(m, u_owner, [h]) for m in out if m['chat']['id'] == owner_chat))
            check(only, 'a stranger (a member with nothing waiting), an unknown account, a revoked owner and bot senders '
                        'get nothing, and nothing goes anywhere for them',
                  [got.get(u['update_id']) for u in (u_stranger, u_nobody, u_revoked, u_bot, u_inline)]
                  == [('refused', 'missing_reply_reference'), ('refused', 'unknown_sender'), ('refused', 'not_current_member'),
                      ('refused', 'automation_sender'), ('refused', 'automation_sender')]
                  and len(out) == 1 and hint_of(u_inline) is None
                  and all(hint_of(u) is None for u in (u_stranger, u_nobody, u_revoked, u_bot)))
            ev = evidence_of(u_owner)
            check(only, 'the hint records no answer: no answer record, the refusal kept as decided, the request still pending',
                  kind_count('presentation_answer') == answers_before and answered(h) is None and answered(h3) is None
                  and ev.get('outcome') == 'refused' and ev.get('reason') == 'missing_reply_reference'
                  and ev.get('answer_id') is None and inbox.brief(h).get('category') == 'pending'
                  and presenter.current(h).get('presentation_id') == rh.get('presentation_id'))
            mark = len(api['sent'])
            u_back = say(owner3_user, 'accept: go')
            got = acquire()
            check(only, 'control: the same owner, a current member again, gets his hint',
                  got.get(u_back['update_id']) == ('refused', 'missing_reply_reference')
                  and len(sent_since(mark)) == 1 and is_hint(sent_since(mark)[0], u_back, [h3]))
            mark = len(api['sent'])
            u_answer = say(owner_user, 'reject: not now', reply_to=rh.get('message_id'))
            got = acquire()
            record = answered(h) or {}
            check(only, 'control: the owner\'s reply to the request message is his answer, from that reply alone',
                  got.get(u_answer['update_id']) == ('answered', None) and record.get('ruling') == 'reject'
                  and (record.get('attribution') or {}).get('platform_message_id') == u_answer['message']['message_id']
                  and sent_since(mark) == [])

        # AC3: repeated messages do not flood the owner: one hint per waiting request until he answers it.
        once = 'hint/once-per-pending-request'
        with section(once):
            q, rq = open_framed('AC3-Q')
            mark = len(api['sent'])
            first, second = say(owner_user, 'hello'), say(owner_user, 'accept: fits the plan')
            got = acquire()
            third = say(owner_user, 'are you there?')
            got.update(acquire())
            out = sent_since(mark)
            check(once, 'three plain messages for one waiting request get one hint, to the first',
                  [got.get(u['update_id']) for u in (first, second, third)] == [('refused', 'missing_reply_reference')] * 3
                  and len(out) == 1 and is_hint(out[0], first, [q]))
            mark_entity = entity('presentation-hinted:%s:1:owner' % q) or {'data': {}}
            first_id = 'presentation-hint:telegram_chat:%d:%d' % (owner_chat, first['message']['message_id'])
            check(once, 'the waiting request version is marked hinted by that one hint, and the later messages are not hinted',
                  mark_entity.get('kind') == 'presentation_hinted' and hint_of(first) is not None
                  and mark_entity['data'].get('hint_id') == first_id
                  and hint_of(second) is None and hint_of(third) is None)
            check(once, 'the later messages are observed as already hinted, naming the request',
                  [(o.get('outcome'), o.get('request_ids')) for o in presenter.observations
                   if o.get('operation') == 'hint_owner' and o.get('update_id') in (second['update_id'], third['update_id'])]
                  == [('already_hinted', [q])] * 2)
            q2, rq2 = open_framed('AC3-Q2')
            mark = len(api['sent'])
            fourth = say(owner_user, 'hello again')
            got = acquire()
            out = sent_since(mark)
            check(once, 'a newly waiting request gets its own one hint, which does not name the request already hinted',
                  got.get(fourth['update_id']) == ('refused', 'missing_reply_reference')
                  and len(out) == 1 and is_hint(out[0], fourth, [q2]))
            answer_all([rq, rq2], once)
            mark = len(api['sent'])
            fifth = say(owner_user, 'anything else?')
            got = acquire()
            check(once, 'once he has answered, nothing waits and nothing is sent',
                  got.get(fifth['update_id']) == ('refused', 'missing_reply_reference') and sent_since(mark) == [])
    finally:
        server.shutdown()
        server.server_close()
        conn.close()
    return rows


_v136_started = _v136_time.monotonic()
# The store and keys live in memory-backed /dev/shm when it exists and is writable (Linux), as the
# other store suites do; elsewhere (the Mac) the platform's temporary directory is used.
_v136_fast = '/dev/shm' if _v136_os.path.isdir('/dev/shm') and _v136_os.access('/dev/shm', _v136_os.W_OK) else None
with _v136_temp.TemporaryDirectory(prefix='v136-', dir=_v136_fast) as _v136_dir:
    _v136_rows = _v136_checks(_v136_Path(_v136_dir))
for _v136_name, _v136_observed in _v136_rows.items():
    _v136_ok = bool(_v136_observed) and all(ok for _, ok in _v136_observed)
    if not _v136_ok:
        for _v136_label, _v136_one in _v136_observed:
            if not _v136_one:
                print('  VELDO-0136 %s detail: %s' % (_v136_name, _v136_label))
    expect('VELDO-0136 ' + _v136_name, _v136_ok)
print('VELDO-0136 suite seconds: %.3f' % (_v136_time.monotonic() - _v136_started))
