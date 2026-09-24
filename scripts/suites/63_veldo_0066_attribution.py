"""Canonical Telegram attribution over a real signed store and a loopback Bot API (VELDO-0066).

Criterion rows collect every observation, including negative requests. The owner's replies reach the
edge the way Telegram delivers them: a loopback Bot API endpoint over real HTTP answers getMe,
getUpdates and sendMessage in the platform's documented shapes (Update, Message, User, Chat), keeps
per bot the messages it published and the updates it holds, confirms updates by offset, applies
allowed_updates only to updates created after a request named it, and numbers each bot's messages on
its own, as two bots' chats with one person are numbered. Presentations are VELDO-0065's. Every
journal record and every edge assertion carries a real OpenSSH signature. This is not the Telegram
service: no network or real token is used. Mutation workers replace the production module copy
below, never assertions or fixtures. When the attribution module is absent (the pre-change tree, for
the red record) the rows drive the answer path as it stood there instead, so they fail by their own
assertions rather than by an exception.
"""
import copy as _v66_copy
import hashlib as _v66_hashlib
import http.server as _v66_http
import importlib.util as _v66_import
import json as _v66_json
import os as _v66_os
from pathlib import Path as _v66_Path
import shutil as _v66_shutil
import subprocess as _v66_sp
import tempfile as _v66_temp
import threading as _v66_threading
import time as _v66_time
import urllib.request as _v66_urlreq


def _v66_load(name, path):
    spec = _v66_import.spec_from_file_location(name, path)
    module = _v66_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v66_message(st, bot, sender, chat, text, reply_to=None, **extra):
    """One message as the platform keeps and delivers it: its id numbered per bot, the platform's date,
    the sender's User, the chat, the text and, for a reply, the replied message as the platform holds
    it, without that message's own reply (as the Bot API documents)."""
    bot['next'] += 1
    st['tick'] += 1
    message = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1790000000 + st['tick'],
               'text': text}
    if reply_to is not None:
        held = bot['messages'][(chat['id'], reply_to)]
        message['reply_to_message'] = _v66_copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
    message.update(extra)
    bot['messages'][(chat['id'], message['message_id'])] = message
    return message


def _v66_update(bot, kind, message):
    """One Update the platform holds for the bot until an offset past it confirms it."""
    bot['update_next'] += 1
    update = {'update_id': bot['update_next'], kind: message}
    bot['updates'].append(update)
    return update


class _V66BotApi(_v66_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes, per bot token."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = _v66_json.loads(raw) if raw else {}
        _, _, rest = self.path.partition('/bot')
        token, _, method = rest.partition('/')
        bot = st['bots'].get(token)
        if bot is None:
            return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
        st['calls'].append((token, method, body))
        if method == 'getMe':
            return self._answer(200, {'ok': True, 'result': dict(bot['user'], can_join_groups=True,
                                                                 can_read_all_group_messages=False,
                                                                 supports_inline_queries=False,
                                                                 can_connect_to_business=False, has_main_web_app=False)})
        if method == 'getUpdates':
            return self._updates(bot, body)
        if method == 'sendMessage':
            return self._send(st, bot, body)
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _updates(self, bot, body):
        mode = bot['mode']
        if mode == 'conflict':
            return self._answer(409, {'ok': False, 'error_code': 409, 'description': "Conflict: can't use getUpdates "
                                      'method while webhook is active; use deleteWebhook to delete the webhook first'})
        if mode == 'transcript':  # a pasted transcript, not the platform's answer
            return self._raw(200, 'text/plain; charset=utf-8', b'Owner Example: accept: fits the plan\n')
        if mode == 'gateway':
            return self._raw(502, 'text/html', b'<html><body><h1>502 Bad Gateway</h1></body></html>')
        offset = body.get('offset') or 0
        bot['offsets'].append(offset)
        if body.get('allowed_updates') is not None and body['allowed_updates'] != bot['allowed']:
            # The Bot API: the filter does not affect updates created before the call that set it.
            bot['allowed'], bot['allowed_from'] = list(body['allowed_updates']), bot['update_next'] + 1
        if offset:
            bot['updates'] = [u for u in bot['updates'] if u['update_id'] >= offset]  # earlier ones are confirmed
        wanted = bot['allowed'] or []
        out = [u for u in bot['updates'] if not wanted or u['update_id'] < bot['allowed_from'] or any(k in u for k in wanted)]
        payload = _v66_json.dumps({'ok': True, 'result': out[:body.get('limit') or 100]}).encode()
        bot['delivered'].append(payload)
        return self._raw(200, 'application/json', payload)

    def _send(self, st, bot, body):
        if len(body.get('text', '').encode('utf-16-le')) // 2 > 4096:  # the documented Bot API text limit
            return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: message is too long'})
        chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
        reply = (body.get('reply_parameters') or {}).get('message_id')
        if reply is not None and (chat['id'], reply) not in bot['messages']:
            if not (body.get('reply_parameters') or {}).get('allow_sending_without_reply'):
                return self._answer(400, {'ok': False, 'error_code': 400,
                                          'description': 'Bad Request: message to be replied not found'})
            reply = None  # sent as an ordinary message, as Telegram does
        message = _v66_message(st, bot, bot['user'], chat, body['text'], reply)
        self._answer(200, {'ok': True, 'result': message})

    def _answer(self, code, value):
        self._raw(code, 'application/json', _v66_json.dumps(value).encode())

    def _raw(self, code, kind, payload):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _v66_checks(base):
    rows = {name: [] for name in ('install/assets', 'acquisition/platform-fields-retained',
                                  'attribution/stable-sender-identity', 'attribution/binds-replied-presentation',
                                  'attribution/person-only-authority')}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    rel = '.veldo/control_channel_attribution.py'
    # The production copy under test; mutation workers replace exactly this path.
    module_path = ROOT / ".veldo" / "control_channel_attribution.py"
    scaffold = _v66_load('v66_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
    here = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
    check('install/assets', rel + ' installed by the scaffold', rel in scaffold._FILES)
    check('install/assets', rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
    check('install/assets', rel + ' engine copy identical', here and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
    if here:
        scaffold._lay(ROOT / 'engine' / rel, base / 'installed' / rel, rel, [], [])
    check('install/assets', rel + ' laid by the installer',
          here and (base / 'installed' / rel).is_file() and (base / 'installed' / rel).read_bytes() == (ROOT / rel).read_bytes())

    contract = _v66_load('v66_contract', ROOT / '.veldo' / 'entity_contract.py')
    organs = base / 'organs'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v66_shutil.copyfile(source, organs / source.name)
    claims = _v66_load('v66_claims', organs / 'control_claim.py')
    S, CM, AUTHC = claims.S, claims.CM, claims.AC
    I = _v66_load('v66_inbox', organs / 'control_assignment.py')
    P = _v66_load('v66_projection', organs / 'control_channel_projection.py')
    V = _v66_load('v66_presentation', organs / 'control_channel_presentation.py')
    V66 = _v66_load('v66_attribution', module_path) if module_path.is_file() else None

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'pm', 'owner', 'stranger', 'twin-a', 'twin-b', 'owner3', 'ops-relay', 'telegram-edge'):
        _v66_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v66-' + who, '-f', str(keys / who)],
                    check=True, capture_output=True, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()
    journal_signed = []
    sign_plan = []  # pending journal signatures: False makes that one store write fail unsigned

    def sign_as(who, message, namespace=AUTHC.SIGNATURE_NAMESPACE):
        return _v66_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                           capture_output=True, check=True, timeout=10).stdout.decode()

    def journal_sign(message):
        if sign_plan and not sign_plan.pop(0):
            return None
        signature = sign_as('authority', message, 'veldo-journal')
        journal_signed.append((message, signature))
        return signature

    def edge_sign(message):
        return sign_as('telegram-edge', message)

    ids = dict(domain_uuid='attribution-domain', repository_uuid='attribution-repository', store_uuid='attribution-store')
    conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
    serial = [0]

    def fixture(eid, kind, data):
        serial[0] += 1
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    person_member = dict(principal_type='person', roles=[], scope=['project-a'])
    members = {'owner': dict(principal_type='person', roles=['project_owner'], scope=['project-a']),
               'pm': dict(principal_type='service', roles=[], scope=['project-a']),
               'stranger': dict(person_member), 'twin-a': dict(person_member), 'twin-b': dict(person_member),
               'owner3': dict(person_member),
               'ops-relay': dict(principal_type='service', roles=[], scope=['project-a']),
               'telegram-edge': dict(principal_type='service', roles=[], scope=['project-a'])}
    for who, data in members.items():
        fixture(who, 'membership', dict(data, revoked_at=None, expires_at=None))
        if who != 'telegram-edge':
            fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
    fixture(AUTHC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
            dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
    owner_chat, stranger_chat, twin_chat, owner3_chat, relay_chat = 5550001, 5550002, 5550003, 5550004, 5550005
    lookalike_chat, nobody_chat = 5550099, 5550199
    # Enrollment ids are spelled here, not taken from a module under test. Both twins name one chat.
    for who, chat in (('owner', owner_chat), ('stranger', stranger_chat), ('twin-a', twin_chat), ('twin-b', twin_chat),
                      ('owner3', owner3_chat), ('ops-relay', relay_chat)):
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))

    def user(uid, first, last=None, username=None):
        """A Telegram User as the Bot API sends it for a person account."""
        found = {'id': uid, 'is_bot': False, 'first_name': first, 'language_code': 'en'}
        if last:
            found['last_name'] = last
        if username:
            found['username'] = username
        return found

    def private(person):
        """The private Chat of a person with the bot: Telegram gives it the person's own user id."""
        chat = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}
        chat.update({k: person[k] for k in ('last_name', 'username') if k in person})
        return chat

    owner_user = user(owner_chat, 'Owner', 'Example', 'owner_example')
    stranger_user = user(stranger_chat, 'Stranger', None, 'stranger_x')
    twin_user = user(twin_chat, 'Twin')
    owner3_user = user(owner3_chat, 'Third', 'Owner')
    api = {'tick': 0, 'calls': [], 'bots': {}, 'chats': {}}
    for person in (owner_user, stranger_user, twin_user, owner3_user):
        api['chats'][person['id']] = private(person)

    def add_bot(token, uid, username, next_message, next_update):
        api['bots'][token] = {'user': {'id': uid, 'is_bot': True, 'first_name': 'Veldo', 'username': username},
                              'next': next_message, 'update_next': next_update, 'messages': {}, 'updates': [],
                              'offsets': [], 'delivered': [], 'mode': 'ok', 'allowed': None, 'allowed_from': 0}
        return api['bots'][token]

    bot1 = add_bot('sandbox-bot', 8000000001, 'veldo_example_bot', 9000, 600000000)
    handler = type('V66Handler', (_V66BotApi,), {'state': api})
    server = _v66_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v66_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:%d' % server.server_address[1]
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'sandbox-bot'), conn, 'authority',
                            journal_sign, assignment=I)
    presenters = {'sandbox-bot': presenter}
    acquirers = {}
    counter = [0]

    def signed(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    def command(who, operation, alias, **fields):
        counter[0] += 1
        return inbox.apply(signed(who, dict(ids, operation=operation, alias=alias, principal=who,
                                            command_id='c-%d' % counter[0], nonce='n-%d' % counter[0], **fields)))

    def frame(who, alias, version, risk):
        counter[0] += 1
        return presenter.frame(signed(who, dict(ids, operation='frame', alias=alias, principal=who, request_version=version,
                                                risk_statement=risk, command_id='f-%d' % counter[0],
                                                nonce='fn-%d' % counter[0])))

    def content(owner='owner', choices=('accept', 'reject')):
        return dict(kind='decision', owner=owner, scope=['project-a'], deadline='2026-10-01T17:00:00Z',
                    budget={'owner_minutes': 15}, brief='Choose how the example specification proceeds.',
                    choices=list(choices),
                    subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md', 'digest': 'sha256:' + '1' * 64})

    def open_framed(alias, owner='owner'):
        command('pm', 'open', alias, assignment=content(owner=owner))
        frame('pm', alias, 1, 'Low: a wrong choice costs one review cycle.')
        return I.assignment_id(ids['repository_uuid'], alias)

    def presented(rid, via=None):
        via = via or presenter
        via.present(rid)
        return via.current(rid) or {}

    def say(sender, text, chat=None, reply_to=None, token='sandbox-bot', **extra):
        """A message a Telegram account sends to the bot, held by the platform as an Update."""
        bot = api['bots'][token]
        return _v66_update(bot, 'message', _v66_message(api, bot, sender, chat or private(sender), text, reply_to, **extra))

    def reply(receipt, text, sender=None, token='sandbox-bot', part=-1, chat=None, **extra):
        """A reply to one published part of a presentation, in the sender's own private chat."""
        sender = owner_user if sender is None else sender
        return say(sender, text, chat=chat or private(sender), reply_to=(receipt.get('message_ids') or [None])[part],
                   token=token, **extra)

    def bot_says(chat, text, token='sandbox-bot'):
        """A message the bot sent earlier in a chat (its own messages are never delivered to it)."""
        bot = api['bots'][token]
        return _v66_message(api, bot, bot['user'], chat, text)

    def edge_signed(assertion):
        return {'assertion': assertion, 'signature': edge_sign(S.canonical_bytes(assertion))}

    pre_offsets = {}

    def pre_change_acquire(token, via):
        """The answer path before VELDO-0066, used only when the attribution module is absent (the
        pre-change tree): nothing pulled updates or kept evidence, and VELDO-0065's edge seam was the
        Bot API message object handed to canonical_answer and signed by the edge. This drives that
        seam with each message the platform delivers, so the red record measures the pre-change code."""
        request = _v66_urlreq.Request('%s/bot%s/getUpdates' % (url, token), method='POST',
                                      data=_v66_json.dumps({'offset': pre_offsets.get(token, 0)}).encode(),
                                      headers={'Content-Type': 'application/json'})
        try:
            with _v66_urlreq.urlopen(request, timeout=10) as response:
                updates = _v66_json.loads(response.read()).get('result') or []
        except Exception:  # noqa: BLE001 - an unreadable answer acquires nothing
            return [{'outcome': 'refused', 'reason': 'unreadable'}]
        results = []
        for update in updates:
            pre_offsets[token] = max(pre_offsets.get(token, 0), update['update_id'] + 1)
            message = next((v for k, v in update.items() if k != 'update_id'), None)
            try:
                assertion = via.canonical_answer(message, 'telegram-edge')
            except V.Refused as exc:
                results.append({'update_id': update['update_id'], 'outcome': 'refused', 'reason': exc.code})
                continue
            except Exception as exc:  # noqa: BLE001 - reported as a result, never raised past the row
                results.append({'update_id': update['update_id'], 'outcome': 'refused', 'reason': type(exc).__name__})
                continue
            got = via.answer(edge_signed(assertion))
            results.append({'update_id': update['update_id'], 'reason': got.get('reason'),
                            'outcome': 'answered' if got.get('outcome') == 'accepted' else 'refused'})
        return results

    def acquirer(token='sandbox-bot'):
        if V66 is None:
            return None
        if token not in acquirers:
            acquirers[token] = V66.Acquirer(S, CM, P, V, presenters[token], V66.TelegramAcquisitionEdge(P, url, token), conn,
                                            'authority', journal_sign, 'telegram-edge', edge_sign)
        return acquirers[token]

    def acquire(token='sandbox-bot'):
        return pre_change_acquire(token, presenters[token]) if V66 is None else acquirer(token).acquire()

    def by_update(results):
        return {r['update_id']: (r.get('outcome'), r.get('reason')) for r in results if r.get('update_id') is not None}

    def entity(eid):
        row = conn.execute('SELECT version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'version': row[0], 'data': _v66_json.loads(row[1])}

    def evidence_of(update, token='sandbox-bot'):
        """The evidence record of one update, at the id spelled here: bot user id and update id."""
        found = entity('channel-evidence:telegram_chat:%d:%d' % (api['bots'][token]['user']['id'], update['update_id']))
        return None if found is None else dict(found['data'], entity_version=found['version'])

    def evidence_count():
        return conn.execute("SELECT count(*) FROM entities WHERE kind='channel_evidence'").fetchone()[0]

    def answered(rid, principal=None):
        """The answer record of a request at version 1, read from the store itself."""
        for (text,) in conn.execute("SELECT data FROM entities WHERE kind='presentation_answer'"):
            data = _v66_json.loads(text)
            if data.get('request_id') == rid and data.get('request_version') == 1 and principal in (None, data.get('principal')):
                return data
        return None

    def sends():
        return sum(1 for _, method, _ in api['calls'] if method == 'sendMessage')

    def digest_of(value):
        return 'sha256:' + _v66_hashlib.sha256(_v66_json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                                ensure_ascii=True).encode('utf-8')).hexdigest()

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
        # AC1: acquisition keeps the platform's own sender, message, time and chat for every update
        acq = 'acquisition/platform-fields-retained'
        with section(acq):
            customer = user(5559001, 'Customer')
            # Created before any getUpdates call named the wanted types, so the platform still delivers it.
            business = _v66_update(bot1, 'business_message', _v66_message(api, bot1, owner_user, private(customer),
                                                                          'accept: fits the plan', business_connection_id='bc-1'))
            a1 = open_framed('AQ-1')
            r1 = presented(a1)
            u1 = reply(r1, 'accept: fits the plan')
            before = len(api['calls'])
            got = by_update(acquire())
            asked = [(method, body) for token, method, body in api['calls'][before:] if token == 'sandbox-bot']
            check(acq, 'the run asks the platform who the bot is, then for updates from the start, naming the wanted types',
                  len(asked) >= 2 and [m for m, _ in asked[:2]] == ['getMe', 'getUpdates'] and asked[1][1].get('offset') == 0
                  and asked[1][1].get('allowed_updates') == ['message', 'edited_message'])
            body = bot1['delivered'][-1] if bot1['delivered'] else b'{}'
            served = next((u for u in _v66_json.loads(body).get('result') or [] if u.get('update_id') == u1['update_id']), None)
            ev = evidence_of(u1)
            check(acq, 'the owner\'s reply is kept as evidence exactly as the platform served it, with its own digest',
                  served is not None and ev is not None and ev.get('source') == served and ev.get('source_digest') == digest_of(served))
            check(acq, 'the evidence names the digest of the whole platform answer it arrived in',
                  ev is not None and ev.get('response_digest') == 'sha256:' + _v66_hashlib.sha256(body).hexdigest())
            m = (served or {}).get('message') or {}
            expected = {'update_id': u1['update_id'], 'update_kind': 'message', 'message_id': m.get('message_id'),
                        'date': m.get('date'), 'chat_id': (m.get('chat') or {}).get('id'), 'chat_type': 'private',
                        'sender_id': (m.get('from') or {}).get('id'), 'sender_is_bot': False,
                        'reply_to_message_id': (m.get('reply_to_message') or {}).get('message_id'),
                        'reply_chat_id': ((m.get('reply_to_message') or {}).get('chat') or {}).get('id'),
                        'reply_date': (m.get('reply_to_message') or {}).get('date')}
            check(acq, 'every canonical field is the platform\'s own value in that response (message, date, chat, sender, replied message)',
                  all(v is not None for v in expected.values()) and ev is not None and ev.get('fields') == expected
                  and expected['sender_id'] == owner_chat and expected['reply_to_message_id'] == r1.get('message_id'))
            record = answered(a1) or {}
            att = record.get('attribution') or {}
            check(acq, 'the recorded answer carries that message, sender, time, chat and replied message, and the evidence holding them',
                  ev is not None and record.get('principal') == 'owner' and att.get('platform_message_id') == expected['message_id']
                  and att.get('sender_id') == owner_chat and att.get('platform_timestamp') == expected['date']
                  and att.get('chat_id') == owner_chat and att.get('reply_to_message_id') == r1.get('message_id')
                  and att.get('update_id') == u1['update_id'] and att.get('evidence_id') == ev.get('evidence_id')
                  and att.get('evidence_digest') == ev.get('source_digest') and _v66_json.dumps(att).count('Owner') == 0)
            check(acq, 'the evidence records its one decision: answered by the owner through the presentation',
                  got.get(u1['update_id']) == ('answered', None) and ev is not None and ev.get('outcome') == 'answered'
                  and ev.get('principal') == 'owner' and ev.get('presentation_id') == r1.get('presentation_id'))
            business_ev = evidence_of(business)
            check(acq, 'an update of another type the platform still delivered is kept and refused, and records nothing',
                  got.get(business['update_id']) == ('refused', 'unsupported_update') and business_ev is not None
                  and business_ev.get('outcome') == 'refused')
            kept = evidence_count()
            again = acquire()
            check(acq, 'the next run asks from the update after the last one kept, so the platform confirms them, and decides nothing again',
                  bot1['offsets'][-1:] == [max(u1['update_id'], business['update_id']) + 1] and again == []
                  and evidence_count() == kept and not any(u['update_id'] <= u1['update_id'] for u in bot1['updates']))
            held = bot1['messages'][(owner_chat, u1['message']['message_id'])]
            edit = _v66_update(bot1, 'edited_message', dict(_v66_copy.deepcopy(held), text='reject: changed my mind',
                                                             edit_date=held['date'] + 60))
            got = by_update(acquire())
            check(acq, 'an edit of the answer is kept and refused as an edit, and the recorded answer is unchanged',
                  got.get(edit['update_id']) == ('refused', 'edited_message') and evidence_of(edit) is not None
                  and (answered(a1) or {}).get('ruling') == 'approve')
            for mode, named in (('transcript', 'invalid_platform_answer'), ('conflict', 'channel_refused'),
                                ('gateway', 'unavailable_service')):
                note = say(owner_user, 'hello')
                bot1['mode'] = mode
                try:
                    results = acquire()
                finally:
                    bot1['mode'] = 'ok'
                check(acq, 'a %s answer on the platform exchange acquires nothing and is refused as %s' % (mode, named),
                      [r.get('reason') for r in results] == [named] and evidence_of(note) is None)
                got = by_update(acquire())
                check(acq, 'the next readable answer keeps the update the %s answer did not' % mode,
                      evidence_of(note) is not None and got.get(note['update_id']) == ('refused', 'missing_reply_reference'))
            stray = V66.Acquirer(S, CM, P, V, presenter, V66.TelegramAcquisitionEdge(P, url, 'revoked-token'), conn,
                                 'authority', journal_sign, 'telegram-edge', edge_sign) if V66 is not None else None
            check(acq, 'a token the platform does not accept acquires nothing (channel_refused)',
                  stray is not None and [r.get('reason') for r in stray.acquire()] == ['channel_refused'])
            # A decision taken but not recorded (the journal write fails) stays pending work, decided next run.
            pending = say(owner_user, 'hello again')
            sign_plan[:] = [True, False]
            first = acquire()
            sign_plan[:] = []
            waiting = acquirer().metrics() if V66 is not None else {}
            later = by_update(acquire())
            check(acq, 'a decision whose record could not be written is reported unknown and stays pending until the next run decides it',
                  [(r.get('outcome'), r.get('reason')) for r in first] == [('unknown_outcome', 'incomplete_transaction')]
                  and waiting.get('pending') == 1 and later.get(pending['update_id']) == ('refused', 'missing_reply_reference')
                  and (acquirer().metrics() if V66 is not None else {}).get('pending') == 0)
            observed = acquirer().observations if V66 is not None else []
            text = _v66_json.dumps(observed)
            classes = {'invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence',
                       'unknown_outcome'}
            check(acq, 'observations name operation, update, outcome, named refusal and its error class, never text, names or the token',
                  bool(observed) and all(o.get('operation') in ('acquire', 'attribute') and 'outcome' in o and 'reason' in o
                                         and o.get('repository_uuid') == ids['repository_uuid'] for o in observed)
                  and all(o['error_class'] in classes for o in observed if o['outcome'] not in ('acquired', 'answered'))
                  and not any(s in text for s in ('fits the plan', 'changed my mind', 'hello', 'Example', 'owner_example',
                                                  'sandbox-bot', 'Customer')))
            metrics = acquirer().metrics() if V66 is not None else {}
            check(acq, 'metrics count accepted and refused operations, the pending work and refusals by reason',
                  metrics.get('accepted', 0) >= 1 and metrics.get('refused', 0) >= 1 and metrics.get('pending') == 0
                  and metrics.get('answered') == 1
                  and metrics.get('refused_by_reason') == {'unsupported_update': 1, 'edited_message': 1,
                                                           'missing_reply_reference': 4})

        # AC1: identity is the platform's stable sender id mapped to an enrollment, never a display name
        ident = 'attribution/stable-sender-identity'
        with section(ident):
            s1 = open_framed('ID-S1', owner='stranger')
            rs1 = presented(s1)
            o1, o2 = open_framed('ID-O1'), open_framed('ID-O2')
            ro1, ro2 = presented(o1), presented(o2)
            copycat = dict(stranger_user, first_name='Owner', last_name='Example')  # a username stays unique on Telegram
            lookalike = user(lookalike_chat, 'Owner', 'Example')
            api['chats'][lookalike_chat] = private(lookalike)
            greeting = bot_says(private(lookalike), 'Welcome. Nothing is waiting for you.')
            renamed = user(owner_chat, 'Dmitry', 'G.', 'dmitry_g')
            u_copy = say(copycat, 'accept: mine to answer', reply_to=rs1.get('message_id'))
            u_look = say(lookalike, 'accept: approved', reply_to=greeting['message_id'])
            u_paste = say(lookalike, 'Owner Example (owner): accept: approved')
            u_renamed = say(renamed, 'accept: fits', reply_to=ro1.get('message_id'))
            u_forward = say(owner_user, 'accept: fits', forward_origin={'type': 'user', 'sender_user': owner_user,
                                                                       'date': 1790000001})
            u_hidden = say(stranger_user, 'accept: fits', forward_origin={'type': 'hidden_user', 'date': 1790000001,
                                                                         'sender_user_name': 'Owner Example'})
            t1 = open_framed('ID-T1', owner='twin-a')
            rt1 = presented(t1)
            u_twin = say(twin_user, 'accept: fits', reply_to=rt1.get('message_id'))
            got = by_update(acquire())
            copy_ev, renamed_ev = evidence_of(u_copy), evidence_of(u_renamed)
            check(ident, 'a stranger who copies the owner\'s display name is attributed to its own stable id\'s principal, never the owner',
                  got.get(u_copy['update_id']) == ('answered', None) and copy_ev is not None
                  and copy_ev.get('principal') == 'stranger' and (answered(s1) or {}).get('principal') == 'stranger'
                  and (answered(s1) or {}).get('attribution', {}).get('sender_id') == stranger_chat
                  and entity('presentation-answer:%s:1:owner' % s1) is None)
            check(ident, 'an unenrolled account with the owner\'s display name is attributed to nobody, even pasting a transcript',
                  [got.get(u['update_id']) for u in (u_look, u_paste)] == [('refused', 'unknown_sender')] * 2
                  and all((evidence_of(u) or {'principal': 'x'}).get('principal') is None for u in (u_look, u_paste)))
            check(ident, 'the owner renamed (new first, last and user name) is still the owner, by the same stable id',
                  got.get(u_renamed['update_id']) == ('answered', None) and renamed_ev is not None
                  and renamed_ev.get('principal') == 'owner' and (answered(o1) or {}).get('principal') == 'owner')
            check(ident, 'a forward is a transcript of earlier words, the owner\'s own included, and is refused (forwarded_message)',
                  [got.get(u['update_id']) for u in (u_forward, u_hidden)] == [('refused', 'forwarded_message')] * 2)
            check(ident, 'two principals enrolled on one Telegram account are ambiguous, so neither is attributed',
                  got.get(u_twin['update_id']) == ('refused', 'ambiguous_sender') and answered(t1) is None
                  and (evidence_of(u_twin) or {'principal': 'x'}).get('principal') is None)
            names = ('Owner', 'Example', 'Dmitry', 'G.', 'dmitry_g', 'owner_example', 'Stranger', 'stranger_x')
            check(ident, 'no display name, username or text is a canonical field of the evidence',
                  copy_ev is not None and sorted(copy_ev.get('fields') or {}) == sorted(
                      ('update_id', 'update_kind', 'message_id', 'date', 'chat_id', 'chat_type', 'sender_id', 'sender_is_bot',
                       'reply_to_message_id', 'reply_chat_id', 'reply_date'))
                  and not any(v in names for v in (copy_ev.get('fields') or {}).values()))
            u_control = say(owner_user, 'accept: fits', reply_to=ro2.get('message_id'))
            got = by_update(acquire())
            check(ident, 'control: the owner\'s own reply to another request is attributed to the owner and recorded',
                  got.get(u_control['update_id']) == ('answered', None) and (answered(o2) or {}).get('principal') == 'owner')

        # AC2: the answer binds the exact presentation it replies to, in its own chat
        bind = 'attribution/binds-replied-presentation'
        with section(bind):
            ba, bb, bc = open_framed('BD-A'), open_framed('BD-B'), open_framed('BD-C')
            ra, rb, rc = presented(ba), presented(bb), presented(bc)
            ub = reply(rb, 'reject: not now')
            got = by_update(acquire())
            record_b, evidence_b = answered(bb), evidence_of(ub)
            check(bind, 'a reply to one presentation is recorded for that request through that presentation, with the offered ruling',
                  got.get(ub['update_id']) == ('answered', None) and record_b is not None
                  and record_b.get('presentation_id') == rb.get('presentation_id') and record_b.get('choice') == 'reject'
                  and record_b.get('ruling') == 'reject' and answered(ba) is None and answered(bc) is None)
            check(bind, 'the canonical-binding check holds for it: the answer is bound by its evidence to the presentation it names',
                  V66 is not None and evidence_b is not None and acquirer().answer_problems(record_b, evidence_b) == [])
            group = {'id': -1001234567001, 'type': 'supergroup', 'title': 'Project room'}
            api['chats'][group['id']] = group
            note = bot_says(group, 'Project room: decisions are answered in private.')
            u_group = say(owner_user, 'accept: from the room', chat=group, reply_to=note['message_id'])
            u_external = say(owner_user, 'accept: via another chat',
                             external_reply={'origin': {'type': 'chat', 'sender_chat': group, 'date': note['date']},
                                             'chat': group, 'message_id': note['message_id']})
            u_omitted = say(owner_user, 'accept: no reply used')
            u_unmatched = reply(ra, 'maybe: later')
            refused = by_update(acquire())
            told = next((msg for (chat, _), msg in bot1['messages'].items() if chat == owner_chat
                         and (msg.get('reply_to_message') or {}).get('message_id') == u_unmatched['message']['message_id']
                         and msg['from'].get('is_bot')), None)
            check(bind, 'a reply naming no offered choice is refused and the owner is told the valid choices',
                  refused.get(u_unmatched['update_id']) == ('refused', 'unmatched_choice') and told is not None
                  and 'accept | reject' in told.get('text', ''))
            u_to_tell = say(owner_user, 'accept: fine', reply_to=(told or {}).get('message_id'))
            # Bytes altered in delivery: the reference names C's message while the replied message is A's part.
            u_altered = reply(ra, 'accept: fits')
            u_altered['message']['reply_to_message']['message_id'] = rc.get('message_id')
            refused.update(by_update(acquire()))
            for u, named, label in ((u_group, 'not_private_chat', 'a reply in a group chat'),
                                    (u_external, 'reply_in_another_chat', 'a reply made in another chat'),
                                    (u_omitted, 'missing_reply_reference', 'a message that omits the reply reference'),
                                    (u_to_tell, 'unknown_presentation', 'a reply to the bot\'s message back, not a presentation'),
                                    (u_altered, 'presentation_mismatch',
                                     'a reply whose reference names another presentation than the part it carries')):
                check(bind, '%s is refused (%s)' % (label, named), refused.get(u['update_id']) == ('refused', named))
            check(bind, 'none of them recorded an answer to A or C', answered(ba) is None and answered(bc) is None)
            # The bot token replaced by another bot: its chat with the owner has the same chat id and numbers
            # its messages again, so its presentation of E holds the chat and message id of C's.
            add_bot('sandbox-bot-2', 8000000002, 'veldo_example2_bot', rc.get('message_id', 1) - 1, 700000000)
            presenters['sandbox-bot-2'] = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'sandbox-bot-2'), conn,
                                                      'authority', journal_sign, assignment=I)
            be = open_framed('BD-E')
            re_ = presented(be, via=presenters['sandbox-bot-2'])
            looked = presenter.receipt_for_message(owner_chat, rc.get('message_id'))
            check(bind, 'precondition: the second bot\'s presentation of E has C\'s chat and message id, and the lookup by them finds C',
                  re_.get('message_id') == rc.get('message_id') and re_.get('chat_id') == rc.get('chat_id') == owner_chat
                  and (looked or {}).get('presentation_id') == rc.get('presentation_id'))
            u_rotated = reply(re_, 'accept: rotated', token='sandbox-bot-2')
            got = by_update(acquire('sandbox-bot-2'))
            check(bind, 'a reply in the second bot\'s chat is never taken as an answer to the first bot\'s presentation with the same ids',
                  got.get(u_rotated['update_id']) == ('refused', 'presentation_mismatch') and answered(bc) is None
                  and answered(be) is None)
            if V66 is not None and evidence_b is not None and record_b is not None:
                for label, path, value in (('the text', ('message', 'text'), 'accept: sure'),
                                           ('the sender id', ('message', 'from', 'id'), stranger_chat),
                                           ('the replied message id', ('message', 'reply_to_message', 'message_id'),
                                            ra.get('message_id'))):
                    altered = _v66_copy.deepcopy(evidence_b)
                    target = altered['source']
                    for step in path[:-1]:
                        target = target[step]
                    target[path[-1]] = value
                    check(bind, 'evidence whose retained update was altered after acquisition (%s) is refused and binds no answer' % label,
                          V66.evidence_problems(altered) != [] and acquirer().attribute(altered)[0] == 'evidence_mismatch'
                          and acquirer().answer_problems(record_b, altered) != [])
            else:
                check(bind, 'evidence whose retained update was altered after acquisition is refused and binds no answer', False)
            ua, uc = reply(ra, 'accept: fits'), reply(rc, 'accept: ok')
            got = by_update(acquire())
            record_a, record_c = answered(ba) or {}, answered(bc) or {}
            check(bind, 'control: A and C are answered by their own replies, each bound by its evidence to its own presentation',
                  got.get(ua['update_id']) == ('answered', None) and got.get(uc['update_id']) == ('answered', None)
                  and record_a.get('presentation_id') == ra.get('presentation_id')
                  and record_c.get('presentation_id') == rc.get('presentation_id') and V66 is not None
                  and acquirer().answer_problems(record_a, evidence_of(ua)) == []
                  and acquirer().answer_problems(record_c, evidence_of(uc)) == [])

        # AC3: a person-required decision accepts only the current authorized enrolled person
        person = 'attribution/person-only-authority'
        with section(person):
            h = open_framed('PA-H')
            rh = presented(h)
            inline = {'id': 8200000001, 'is_bot': True, 'first_name': 'Inline helper', 'username': 'inline_helper_bot'}
            business_bot = {'id': 8200000002, 'is_bot': True, 'first_name': 'Business helper',
                            'username': 'business_helper_bot'}
            automated = [('an inline bot, from the owner\'s account', reply(rh, 'accept: go', via_bot=inline)),
                         ('a business bot, from the owner\'s account',
                          reply(rh, 'accept: go', sender_business_bot=business_bot, business_connection_id='bc-2')),
                         ('an away, greeting or scheduled message of the owner\'s account',
                          reply(rh, 'accept: go', is_from_offline=True))]
            group = {'id': -1001234567001, 'type': 'supergroup', 'title': 'Project room'}
            api['chats'][group['id']] = group
            note = bot_says(group, 'Project room note.')
            bot_account = {'id': 8300000001, 'is_bot': True, 'first_name': 'Owner', 'last_name': 'Example',
                           'username': 'owner_example_bot'}
            anonymous = {'id': 1087968824, 'is_bot': True, 'first_name': 'Group', 'username': 'GroupAnonymousBot'}
            automated += [('a bot account', say(bot_account, 'accept: go', chat=group, reply_to=note['message_id'])),
                          ('an anonymous administrator signed as the owner',
                           say(anonymous, 'accept: go', chat=group, reply_to=note['message_id'], sender_chat=group,
                               author_signature='Owner Example'))]
            sent = sends()
            got = by_update(acquire())
            for label, u in automated:
                check(person, 'a message sent by %s is refused as automation_sender' % label,
                      got.get(u['update_id']) == ('refused', 'automation_sender'))
            check(person, 'none of them recorded an answer or sent anything back', answered(h) is None and sends() == sent)
            relay_user = user(relay_chat, 'Ops relay')  # an ordinary account a script drives
            nobody = user(nobody_chat, 'Someone')
            api['chats'].update({relay_chat: private(relay_user), nobody_chat: private(nobody)})
            u_relay = say(relay_user, 'accept: go', reply_to=bot_says(private(relay_user), 'Welcome.')['message_id'])
            u_nobody = say(nobody, 'accept: go', reply_to=bot_says(private(nobody), 'Welcome.')['message_id'])
            h3 = open_framed('PA-3', owner='owner3')
            r3 = presented(h3)
            u_revoked = reply(r3, 'accept: go', sender=owner3_user)
            no_id = {'is_bot': False, 'first_name': 'Owner', 'last_name': 'Example', 'username': 'owner_example'}
            u_no_id = reply(rh, 'accept: go', sender=no_id, chat=private(owner_user), principal='owner', actor='owner')
            u_no_from = reply(rh, 'accept: go', principal='owner', author_signature='Owner Example')
            u_no_from['message'].pop('from')
            u_no_date = reply(rh, 'accept: go')
            u_no_date['message'].pop('date')
            s3 = open_framed('PA-S', owner='stranger')
            rs3 = presented(s3)
            u_label = reply(rs3, 'accept: go', sender=stranger_user, principal='owner', actor='owner',
                            author_signature='Owner Example')
            fixture('owner3', 'membership', dict(members['owner3'], revoked_at=_v66_time.time() - 1, expires_at=None))
            sent = sends()
            try:
                got = by_update(acquire())
            finally:
                fixture('owner3', 'membership', dict(members['owner3'], revoked_at=None, expires_at=None))
            check(person, 'an enrolled automation identity (a service member on an ordinary account) is refused (not_a_person)',
                  got.get(u_relay['update_id']) == ('refused', 'not_a_person'))
            check(person, 'an unrecognized sender is refused (unknown_sender)', got.get(u_nobody['update_id']) == ('refused', 'unknown_sender'))
            check(person, 'an owner no longer a current member is refused (not_current_member) and records nothing',
                  got.get(u_revoked['update_id']) == ('refused', 'not_current_member') and answered(h3) is None)
            check(person, 'a message missing the sender id, the sender or the date is refused (missing_canonical_field), labels or not',
                  [got.get(u['update_id']) for u in (u_no_id, u_no_from, u_no_date)] == [('refused', 'missing_canonical_field')] * 3
                  and answered(h) is None)
            label_ev = evidence_of(u_label)
            check(person, 'a sender\'s own labels naming the owner grant nothing: it is attributed by its stable id',
                  got.get(u_label['update_id']) == ('answered', None) and label_ev is not None
                  and label_ev.get('principal') == 'stranger' and (answered(s3) or {}).get('principal') == 'stranger'
                  and entity('presentation-answer:%s:1:owner' % s3) is None)
            check(person, 'nothing was sent back for any refused sender', sends() == sent)
            probe = _v66_message(api, bot1, owner_user, private(owner_user), 'accept: go', rh.get('message_id'))
            forged = presenter.canonical_answer(probe, 'telegram-edge')
            forged['attribution'] = dict(forged['attribution'], sender_id=stranger_chat)
            forged['principal'] = 'owner'
            check(person, 'an assertion that labels the owner as principal over another sender is refused by the presenter (not_owner)',
                  presenter.answer(edge_signed(forged)).get('reason') == 'not_owner' and answered(h) is None)
            u_ok = reply(rh, 'accept: go')
            got = by_update(acquire())
            record = answered(h) or {}
            check(person, 'control: the owner\'s own reply, in person, is the owner\'s answer',
                  got.get(u_ok['update_id']) == ('answered', None) and record.get('principal') == 'owner'
                  and record.get('attribution', {}).get('sender_id') == owner_chat
                  and record.get('attribution', {}).get('sender_type') == 'person')
    finally:
        server.shutdown()
        server.server_close()

    allowed = base / 'allowed_signers'
    allowed.write_text('authority ' + public['authority'] + '\n')
    for message, signature_text in journal_signed[-3:] + journal_signed[:2]:
        sig = base / 'journal.sig'
        sig.write_text(signature_text)
        verified = _v66_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'authority', '-n', 'veldo-journal',
                                '-s', str(sig)], input=message, capture_output=True, timeout=10)
        check('install/assets', 'journal record signature verifies', verified.returncode == 0)
    conn.close()
    return rows


_v66_started = _v66_time.monotonic()
# The store and keys live in memory-backed /dev/shm when it exists and is writable (Linux), as the
# other store suites do; elsewhere (the Mac) the platform's temporary directory is used.
_v66_fast = '/dev/shm' if _v66_os.path.isdir('/dev/shm') and _v66_os.access('/dev/shm', _v66_os.W_OK) else None
with _v66_temp.TemporaryDirectory(prefix='v66-', dir=_v66_fast) as _v66_dir:
    _v66_rows = _v66_checks(_v66_Path(_v66_dir))
for _v66_name, _v66_observed in _v66_rows.items():
    _v66_ok = bool(_v66_observed) and all(ok for _, ok in _v66_observed)
    if not _v66_ok:
        for _v66_label, _v66_one in _v66_observed:
            if not _v66_one:
                print('  VELDO-0066 %s detail: %s' % (_v66_name, _v66_label))
    expect('VELDO-0066 ' + _v66_name, _v66_ok)
print('VELDO-0066 suite seconds: %.3f' % (_v66_time.monotonic() - _v66_started))
