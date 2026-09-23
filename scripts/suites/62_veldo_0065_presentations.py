"""Versioned Telegram presentation receipts and presentation-bound answers over a real signed store (VELDO-0065).

Criterion rows collect every observation, including negative requests. Presentations go over real
HTTP to a loopback Bot API endpoint that answers with the platform's sendMessage shape, keeps what
it published so bytes can be retrieved, links a reply the way Telegram does and refuses a reply to
a message it does not hold. The owner's answers are Bot API message objects the platform holds,
turned into canonical assertions and signed by the Telegram edge's restricted OpenSSH key. Every
journal record carries a real OpenSSH signature. Mutation workers replace the production module
copy below, never assertions or fixtures.
"""
import copy as _v65_copy
import hashlib as _v65_hashlib
import http.server as _v65_http
import importlib.util as _v65_import
import json as _v65_json
from pathlib import Path as _v65_Path
import shutil as _v65_shutil
import subprocess as _v65_sp
import tempfile as _v65_temp
import threading as _v65_threading
import time as _v65_time


def _v65_load(name, path):
    spec = _v65_import.spec_from_file_location(name, path)
    module = _v65_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _V65BotApi(_v65_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API sendMessage request, reply and answer shapes."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        body = _v65_json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path != '/bot%s/sendMessage' % st['token']:
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})
        if st['mode'] == 'refuse':
            return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: chat not found'})
        if st.get('flood_after') is not None:  # flood control: this many sends pass, then one 429
            if st['flood_after'] == 0:
                st['flood_after'] = None
                params = st.get('flood_params', {'retry_after': 3})
                if params == 'INF':  # a JSON number Python reads as infinity
                    raw = b'{"ok": false, "error_code": 429, "description": "Too Many Requests", "parameters": {"retry_after": Infinity}}'
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                body = {'ok': False, 'error_code': 429, 'description': 'Too Many Requests'}
                if params is not None:
                    body['parameters'] = params
                return self._answer(429, body)
            st['flood_after'] -= 1
        if len(body.get('text', '').encode('utf-16-le')) // 2 > 4096:  # the documented Bot API text limit
            return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: message is too long'})
        chat = body.get('chat_id')
        reply = (body.get('reply_parameters') or {}).get('message_id')
        if reply is not None and (chat, reply) not in st['messages']:
            if not (body.get('reply_parameters') or {}).get('allow_sending_without_reply'):
                return self._answer(400, {'ok': False, 'error_code': 400,
                                          'description': 'Bad Request: message to be replied not found'})
            reply = None  # sent as an ordinary message, as Telegram does
        st['requests'].append((chat, body.get('text'), reply))
        st['next'] += 1
        date = 1790000000 + st['next']
        st['messages'][(chat, st['next'])] = {'text': body['text'], 'date': date, 'reply_to': reply, 'from_bot': True}
        message = {'message_id': st['next'], 'date': date, 'chat': {'id': chat, 'type': 'private'}, 'text': body['text']}
        if reply is not None:
            message['reply_to_message'] = {'message_id': reply, 'chat': {'id': chat, 'type': 'private'},
                                           'text': st['messages'][(chat, reply)]['text']}
        if st['mode'] == 'drop':
            self.close_connection = True
            return  # published, but the answer never reaches the caller
        self._answer(200, {'ok': True, 'result': message})

    def _answer(self, code, value):
        payload = _v65_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _v65_checks(base):
    rows = {name: [] for name in ('install/assets', 'presentation/receipt-binds-shown-content',
                                  'presentation/revision-identity', 'answer/current-presentation-only',
                                  'answer/ruling-and-rationale', 'presentation/visible-supersession',
                                  'answer/unseen-refused', 'answer/settle-consumes-answer', 'framing/requester-only',
                                  'framing/stored-framing-reverified', 'answer/not-before-publication',
                                  'presentation/private-chat-only', 'presentation/replacement-without-reply-target',
                                  'presentation/reply-link-verified', 'presentation/long-brief-split',
                                  'projection/one-message-per-version', 'framing/key-by-store-order',
                                  'projection/notice-superseded', 'projection/silent-from-store',
                                  'presentation/refused-part-sent-again', 'answer/choice-matching-and-feedback',
                                  'presentation/notice-kind-fixed', 'framing/frame-and-presenter-agree',
                                  'presentation/retry-after-bounded', 'answer/choice-normalization',
                                  'answer/after-answered-reply', 'answer/tell-once-per-message',
                                  'projection/in-flight-notice-superseded')}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    rel = '.veldo/control_channel_presentation.py'
    scaffold = _v65_load('v65_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
    created, skipped = [], []
    check('install/assets', rel + ' installed by the scaffold', rel in scaffold._FILES)
    check('install/assets', rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
    check('install/assets', rel + ' engine copy identical', (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
    scaffold._lay(ROOT / 'engine' / rel, base / 'installed' / rel, rel, created, skipped)
    check('install/assets', rel + ' laid by the installer', (base / 'installed' / rel).read_bytes() == (ROOT / rel).read_bytes())

    contract = _v65_load('v65_contract', ROOT / '.veldo' / 'entity_contract.py')
    organs = base / 'organs'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v65_shutil.copyfile(source, organs / source.name)
    claims = _v65_load('v65_claims', organs / 'control_claim.py')
    S, CM, AUTHC = claims.S, claims.CM, claims.AC
    I = _v65_load('v65_inbox', organs / 'control_assignment.py')
    P = _v65_load('v65_projection', ROOT / ".veldo" / "control_channel_projection.py")
    V = _v65_load('v65_presentation', ROOT / ".veldo" / "control_channel_presentation.py")

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'owner', 'pm', 'pm2', 'pm3', 'pm4', 'pm5', 'pm6', 'grouped', 'stranger', 'telegram-edge',
                'telegram-edge-other'):
        _v65_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v65-' + who, '-f', str(keys / who)],
                    check=True, capture_output=True, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()
    journal_signed = []
    sign_plan = []  # pending journal signatures: False makes that one store write fail unsigned

    def sign_as(who, message, namespace=AUTHC.SIGNATURE_NAMESPACE):
        return _v65_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                           capture_output=True, check=True, timeout=10).stdout.decode()

    def journal_sign(message):
        if sign_plan and not sign_plan.pop(0):
            return None
        signature = sign_as('authority', message, 'veldo-journal')
        journal_signed.append((message, signature))
        return signature

    ids = dict(domain_uuid='present-domain', repository_uuid='present-repository', store_uuid='present-store')
    conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
    serial = [0]

    def fixture(eid, kind, data, command_id=None, principal='authority'):
        # A generic store write; a forger may choose its command id and principal.
        serial[0] += 1
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=command_id or 'fixture-%d' % serial[0], principal=principal,
                                    operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    members = {'owner': dict(principal_type='person', roles=['project_owner'], scope=['project-a']),
               'pm': dict(principal_type='service', roles=[], scope=['project-a']),
               'stranger': dict(principal_type='person', roles=[], scope=['project-a']),
               'pm2': dict(principal_type='service', roles=[], scope=['project-a']),
               'grouped': dict(principal_type='person', roles=[], scope=['project-a']),
               'pm3': dict(principal_type='service', roles=[], scope=['project-a']),
               'pm4': dict(principal_type='service', roles=[], scope=['project-a']),
               'pm5': dict(principal_type='service', roles=[], scope=['project-a']),
               'pm6': dict(principal_type='service', roles=[], scope=['project-a']),
               'telegram-edge': dict(principal_type='service', roles=[], scope=['project-a'])}
    for who, data in members.items():
        fixture(who, 'membership', dict(data, revoked_at=None, expires_at=None))
        if who != 'telegram-edge':
            fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
    # The edge's restricted key has the channel's key id; its second key is an ordinary key.
    edge_key = AUTHC.CHANNELS['telegram_chat']['edge_key_id']
    fixture(edge_key, 'verification_key', dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
    fixture('key-telegram-edge-other', 'verification_key',
            dict(principal='telegram-edge', public_key=public['telegram-edge-other'], effective_at=0))
    owner_chat, stranger_chat = 5550001, 5550002
    group_chat = -1001234567890
    for who, chat in (('owner', owner_chat), ('stranger', stranger_chat), ('grouped', group_chat)):
        # The enrollment id is spelled here, not taken from the module under test.
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))

    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    api = {'token': 'sandbox-bot', 'mode': 'ok', 'next': 9000, 'messages': {}, 'requests': []}
    handler = type('V65Handler', (_V65BotApi,), {'state': api})
    server = _v65_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v65_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    edge = V.TelegramPresentationEdge(P, 'http://127.0.0.1:%d' % server.server_address[1], api['token'])
    presenter = V.Presenter(S, CM, P, inbox, edge, conn, 'authority', journal_sign, assignment=I)
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

    def content(brief='Choose how the example specification proceeds.', choices=('accept', 'reject'), owner='owner'):
        return dict(kind='decision', owner=owner, scope=['project-a'], deadline='2026-10-01T17:00:00Z',
                    budget={'owner_minutes': 15}, brief=brief, choices=list(choices),
                    subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md', 'digest': 'sha256:' + '1' * 64})

    def opened(alias, risk='Low: a wrong choice costs one review cycle.', **kw):
        command('pm', 'open', alias, assignment=content(**kw))
        rid = I.assignment_id(ids['repository_uuid'], alias)
        frame('pm', alias, 1, risk)
        return rid

    def platform(chat, message):
        held = api['messages'].get((chat, message))
        return None if held is None else {'text': held['text'], 'date': held['date'], 'reply_to': held['reply_to']}

    def owner_reply(receipt, text, sender=owner_chat, chat=None, is_bot=False, reply_to=None):
        """A message the owner sends in reply, as the platform holds and delivers it."""
        chat = receipt.get('chat_id') if chat is None else chat
        reply_to = receipt.get('message_id') if reply_to is None else reply_to
        api['next'] += 1
        date = 1790000000 + api['next']
        api['messages'][(chat, api['next'])] = {'text': text, 'date': date, 'reply_to': reply_to, 'from_bot': is_bot}
        return {'message_id': api['next'], 'date': date, 'text': text,
                'from': {'id': sender, 'is_bot': is_bot, 'first_name': 'Owner'},
                'chat': {'id': chat, 'type': 'private'}, 'reply_to_message': {'message_id': reply_to}}

    def edge_signed(assertion, key='telegram-edge'):
        return {'assertion': assertion, 'signature': sign_as(key, S.canonical_bytes(assertion))}

    def answer(message, change=None, key='telegram-edge', drop=()):
        try:
            assertion = presenter.canonical_answer(message, 'telegram-edge')
        except V.Refused as exc:  # the edge turns nothing into an answer, which is itself a refusal
            return {'outcome': 'refused', 'reason': exc.code}
        assertion.update(change or {})
        for field in drop:
            assertion.pop(field, None)
        return presenter.answer(edge_signed(assertion, key))

    def hand_assertion(receipt, message_id, choice='accept', rationale='the plan fits'):
        """The assertion an edge would sign for a presentation it names directly, with platform evidence."""
        return dict(ids, schema=V.ANSWER_SCHEMA, channel='telegram_chat', assertion_kind='decision_answer',
                    edge_principal='telegram-edge', edge_key_id=edge_key, principal='owner',
                    request_id=receipt['request_id'], request_version=receipt['request_version'],
                    presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                    presentation_version=receipt['presentation_version'], choice=choice,
                    ruling=V.CHOICE_RULINGS.get(choice, choice) if hasattr(V, 'CHOICE_RULINGS') else choice,
                    authority_scope=list(receipt.get('request', {}).get('scope', [])), rationale=rationale,
                    attribution={'platform_message_id': message_id, 'sender_id': owner_chat,
                                 'platform_timestamp': 1790000000 + message_id, 'chat_id': owner_chat,
                                 'reply_to_message_id': receipt.get('message_id') or 0})

    def reason(result):
        return (result.get('outcome'), result.get('reason'))

    def entity(eid):
        row = conn.execute('SELECT version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'version': row[0], 'digest': row[1], 'data': _v65_json.loads(row[2])}

    def direct_frame(who, alias, version, risk, key=None, signer=None, committed_at=None):
        """A framing committed through the registered frame operation itself, bypassing frame()'s
        checks, as any holder of the store connection could."""
        counter[0] += 1
        rid = I.assignment_id(ids['repository_uuid'], alias)
        fid = 'presentation-framing:' + rid
        body = dict(ids, operation='frame', alias=alias, principal=who, request_version=version, risk_statement=risk,
                    command_id='direct-%d' % counter[0], nonce='direct-n-%d' % counter[0])
        current = S.materialized_state(conn)['entities']
        pinned = {fid: current.get(fid, {}).get('version', 0), rid: current[rid]['version']}
        framing = {'schema': V.FRAMING_SCHEMA, 'request_id': rid, 'request_version': version, 'risk_statement': risk,
                   'framed_by': who, 'command_id': body['command_id'], 'key_id': key or 'key-' + who,
                   'expected_versions': pinned,
                   'signed': {'command': body, 'signature': sign_as(signer or who, S.canonical_bytes(body))}}
        return S.execute(conn, dict(command_id=body['command_id'], principal=who, operation=V.FRAME_OPERATION,
                                    parameters=dict(framing_id=fid, request_id=rid, framing=framing),
                                    expected_versions=pinned, artifact_digests=[], nonce=body['nonce']),
                         'authority', journal_sign, 1, committed_at=committed_at)

    def enroll_other_and_project():
        """A second owner with a plain enrollment and no presentation: the inbox projection sends."""
        fixture('channel-enrollment:telegram_chat:stranger', 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='stranger',
                     chat_id=stranger_chat, revoked_at=None))
        command('pm', 'open', 'N-1', assignment=content(owner='stranger'))
        n1 = I.assignment_id(ids['repository_uuid'], 'N-1')
        start = len(api['requests'])
        results = {r['assignment_id']: r for r in P.Projection(S, inbox, P.TelegramEdge(
            'http://127.0.0.1:%d' % server.server_address[1], api['token']), conn, 'authority', journal_sign).project()}
        return results.get(n1, {}).get('outcome') == 'sent' and any(c == stranger_chat for c, _, _ in api['requests'][start:])

    def answered(rid, version):
        """The answer record of one request version, read from the store itself."""
        for (text,) in conn.execute("SELECT data FROM entities WHERE kind='presentation_answer'"):
            data = _v65_json.loads(text)
            if data.get('request_id') == rid and data.get('request_version') == version:
                return data
        return None

    def independent_request_digest(rid):
        # Spelled here: identity, version and every accepted field of the stored assignment.
        data = entity(rid)['data']
        body = {'request_id': rid, 'request_version': data['request_version']}
        body.update({k: data.get(k) for k in ('kind', 'owner', 'scope', 'deadline', 'budget', 'brief', 'choices',
                                              'subject', 'unit_id', 'requested_by')})
        text = _v65_json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        return 'sha256:' + _v65_hashlib.sha256(text).hexdigest()

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
        # AC1: the receipt binds exactly what Telegram showed the owner
        shown = 'presentation/receipt-binds-shown-content'
        with section(shown):
            command('pm', 'open', 'D-1', assignment=content())
            d1 = I.assignment_id(ids['repository_uuid'], 'D-1')
            unframed = presenter.present(d1)
            check(shown, 'an unframed request is not presented and nothing is sent',
                  reason(unframed) == ('refused', 'missing_framing') and api['requests'] == [])
            check(shown, 'a stranger does not frame a request',
                  reason(frame('stranger', 'D-1', 1, 'None.')) == ('refused', 'not_authorized'))
            risk = 'Medium: approving starts two builder runs on the example specification.'
            check(shown, 'the requester frames the request', reason(frame('pm', 'D-1', 1, risk)) == ('accepted', None))
            first = presenter.present(d1)
            r1 = presenter.current(d1) or {}
            held = api['messages'].get((r1.get('chat_id'), r1.get('message_id'))) or {}
            text = held.get('text', '')
            lines = text.split('\n')
            stored = entity(d1)['data']
            check(shown, 'the presentation was published once', reason(first) == ('published', None)
                  and len(api['requests']) == 1 and r1.get('outcome') == 'published')
            r1_row = entity(r1.get('presentation_id', '')) or {}
            # Every R72 field, compared with the source it binds and the bytes the platform holds.
            check(shown, 'R72 request ID and version are the inbox record',
                  r1.get('request_id') == d1 and r1.get('request_version') == stored['request_version'] == 1
                  and 'Request: %s' % d1 in lines and 'Request version: 1' in lines)
            check(shown, 'R72 full request digest covers identity, version and content',
                  r1.get('request_digest') == independent_request_digest(d1)
                  and 'Request digest: %s' % r1.get('request_digest') in lines)
            check(shown, 'R72 subject digests are the assignment subject',
                  r1.get('subject_digests') == [stored['subject']]
                  and 'Subject: specification specs/EXAMPLE.md %s' % stored['subject']['digest'] in lines)
            check(shown, 'R72 rendered brief bytes are the bytes the platform holds',
                  held.get('text') is not None and r1.get('rendered') == [text]
                  and r1.get('brief_digest') == 'sha256:' + _v65_hashlib.sha256(_v65_json.dumps(
                      [text], sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')).hexdigest()
                  and stored['brief'] in text)
            check(shown, 'R72 risk statement is the signed framing and is shown',
                  r1.get('risk_statement') == risk and 'Risk (stated by pm): ' + risk in lines
                  and (entity(V.framing_id(d1)) or {}).get('data', {}).get('framed_by') == 'pm')
            check(shown, 'R72 authority statement names the owner and is shown',
                  'Only owner answers this' in r1.get('authority_statement', '')
                  and 'Authority: ' + r1.get('authority_statement', '') in lines)
            check(shown, 'R72 offered choices are the inbox choices and are shown',
                  r1.get('choices') == stored['choices'] and 'Choices: accept | reject' in lines)
            check(shown, 'R72 channel, chat and message identity are what the platform returned',
                  r1.get('channel') == 'telegram_chat' and r1.get('chat_id') == owner_chat
                  and r1.get('message_id') == api['next'] and r1.get('external_id') == '%d:%d' % (owner_chat, api['next']))
            check(shown, 'R72 publication time is the platform date',
                  held.get('date') is not None and r1.get('published_at') == held.get('date'))
            check(shown, 'the three digests are distinct',
                  len({r1.get('request_digest'), r1.get('subject_digests', [{}])[0].get('digest'), r1.get('brief_digest')}) == 3)
            check(shown, 'the receipt carries every authority-contract presentation field',
                  AUTHC.presentation_problems(r1) == [])
            check(shown, 'control: the receipt verifies against the platform bytes',
                  V.receipt_problems(r1, platform(r1.get('chat_id'), r1.get('message_id'))) == [])
            bindings = {'request_id': d1 + 'x', 'request_version': 2, 'request_digest': 'sha256:' + '0' * 64,
                        'subject_digests': [dict(stored['subject'], digest='sha256:' + '2' * 64)],
                        'rendered': [text + ' '], 'risk_statement': 'None.', 'authority_statement': 'Anyone answers.',
                        'choices': ['accept'], 'channel': 'jira', 'chat_id': stranger_chat,
                        'message_id': (r1.get('message_id') or 0) + 1000, 'published_at': (r1.get('published_at') or 0) + 1,
                        'brief_digest': 'sha256:' + '3' * 64, 'presentation_id': 'presentation:telegram_chat:other'}
            for field, value in bindings.items():
                altered = _v65_copy.deepcopy(r1)
                altered[field] = value
                check(shown, 'a receipt with its %s changed does not verify' % field,
                      V.receipt_problems(altered, platform(altered.get('chat_id'), altered.get('message_id'))) != [])
            altered = _v65_copy.deepcopy(r1)
            altered.get('request', {})['brief'] = 'Another brief.'
            check(shown, 'a receipt with its request content changed does not verify',
                  V.receipt_problems(altered, platform(altered.get('chat_id'), altered.get('message_id'))) != [])
            # A framing the requester never signed frames nothing, whoever wrote it into the store.
            command('pm', 'open', 'F-1', assignment=content())
            f1 = I.assignment_id(ids['repository_uuid'], 'F-1')
            genuine = entity(V.framing_id(d1))['data']
            forged_body = dict(ids, operation='frame', alias='F-1', principal='pm', request_version=1,
                               risk_statement='None: nothing can go wrong.', command_id='forged-1', nonce='forged-1')
            forgeries = {'signed by another principal': dict(genuine, request_id=f1, command_id='forged-1',
                                                             risk_statement='None: nothing can go wrong.',
                                                             signed={'command': forged_body,
                                                                     'signature': sign_as('stranger', S.canonical_bytes(forged_body))}),
                         'carrying another request\'s signed framing': dict(genuine, request_id=f1,
                                                                            risk_statement='None: nothing can go wrong.')}
            for label, forged in forgeries.items():
                asked = len(api['requests'])
                fixture('presentation-framing:' + f1, 'presentation_framing', forged)
                check(shown, 'a framing %s is not presented' % label,
                      reason(presenter.present(f1)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            check(shown, 'control: the requester\'s own framing is presented',
                  reason(frame('pm', 'F-1', 1, 'Low: a wrong choice costs one review cycle.')) == ('accepted', None)
                  and reason(presenter.present(f1)) == ('published', None))
            check(shown, 'metrics show nothing left to present', presenter.metrics()['pending'] == 0)
            check(shown, 'the token is never recorded', api['token'] not in _v65_json.dumps(S.materialized_state(conn)['entities'])
                  and api['token'] not in _v65_json.dumps(presenter.observations))
            check(shown, 'observations carry identity and outcome, never shown text',
                  all(set(o) >= {'operation', 'request_id', 'outcome', 'reason', 'accepted_versions'}
                      and text not in _v65_json.dumps(o) for o in presenter.observations))

        # AC1: equal revisions are distinct requests
        ident = 'presentation/revision-identity'
        with section(ident):
            revised = command('pm', 'revise', 'D-1', request_version=1, changes={'deadline': '2026-10-01T17:00:00Z'})
            v2 = entity(d1)['data']
            check(ident, 'the revision is accepted with equal content',
                  revised.get('ok') is True and v2['request_version'] == 2
                  and {k: v for k, v in v2.items() if k != 'request_version'} == {k: v for k, v in stored.items() if k != 'request_version'})
            check(ident, 'equal revisions have distinct request digests',
                  V.request_digest(d1, 1, stored) != V.request_digest(d1, 2, v2))
            check(ident, 'the module\'s digest of the revision is the independent one',
                  V.request_digest(d1, 2, v2) == independent_request_digest(d1) != r1.get('request_digest'))
            check(ident, 'the revision needs its own framing', reason(presenter.present(d1)) == ('refused', 'missing_framing'))
            frame('pm', 'D-1', 2, risk)
            refusal, now_bound, _ = presenter.bindings(d1)
            mismatched = V.binding_mismatches(r1, now_bound or {})
            check(ident, 'the first presentation does not bind the equal revision',
                  refusal is None and {'request_version', 'request_digest'} <= set(mismatched))
            stale = answer(owner_reply(r1, 'accept: same content as before'))
            check(ident, 'an answer to the first presentation is refused as stale after the equal revision',
                  reason(stale) == ('refused', 'stale_presentation'))
            check(ident, 'the first presentation settles nothing after the equal revision', answered(d1, 1) is None)
            second = presenter.present(d1)
            r2 = presenter.current(d1) or {}
            check(ident, 'the revision is a new presentation with its own identity',
                  reason(second) == ('published', None) and r2.get('request_version') == 2
                  and r2.get('presentation_id') not in (None, r1.get('presentation_id'))
                  and r2.get('request_digest') != r1.get('request_digest'))
            check(ident, 'both receipts are retained', presenter.receipt(r1.get('presentation_id', '')) is not None
                  and sorted(r['request_version'] for r in presenter.receipts(d1)) == [1, 2])

        # AC3: a changed presentation visibly supersedes the previous one
        sup = 'presentation/visible-supersession'
        with section(sup):
            held2 = api['messages'].get((r2.get('chat_id'), r2.get('message_id'))) or {}
            head = presenter.head(d1) or {}
            check(sup, 'the replacement is sent as a reply to the superseded message',
                  held2.get('reply_to') == r1.get('message_id') and r2.get('reply_to_message_id') == r1.get('message_id'))
            check(sup, 'the replacement names what it supersedes in the shown bytes',
                  'Supersedes: presentation version 1, message %s. Only this message can be answered.' % r1.get('message_id')
                  in held2.get('text', '').split('\n') and 'Presentation version: 2' in held2.get('text', '').split('\n'))
            check(sup, 'the visible link is the current authority\'s supersession',
                  head.get('current') == r2.get('presentation_id')
                  and head.get('superseded') == {r1.get('presentation_id'): r2.get('presentation_id')}
                  and head.get('published') == [r1.get('presentation_id'), r2.get('presentation_id')]
                  and (r2.get('supersedes') or {}).get('presentation_id') == r1.get('presentation_id'))
            after = entity(r1.get('presentation_id', '')) or {}
            check(sup, 'the superseded receipt is unchanged', after.get('version') == r1_row.get('version')
                  and after.get('digest') == r1_row.get('digest'))
            check(sup, 'both immutable receipts still verify against the platform',
                  V.receipt_problems(presenter.receipt(r1.get('presentation_id', '')),
                                     platform(r1.get('chat_id'), r1.get('message_id'))) == []
                  and V.receipt_problems(r2, platform(r2.get('chat_id'), r2.get('message_id'))) == [])
            risk3 = 'High: approving also publishes the example release.'
            check(sup, 'a changed risk statement at the same request version is framed', reason(frame('pm', 'D-1', 2, risk3)) == ('accepted', None))
            asked = len(api['requests'])
            third = presenter.present(d1)
            r3 = presenter.current(d1) or {}
            check(sup, 'changed text at the same request version is a new presentation and message',
                  reason(third) == ('published', None) and len(api['requests']) == asked + 1
                  and r3.get('request_version') == 2 and r3.get('presentation_version') == 3
                  and r3.get('presentation_id') not in (r2.get('presentation_id'), None) and r3.get('risk_statement') == risk3)
            check(sup, 'the third presentation replies to the second',
                  r3.get('reply_to_message_id') == r2.get('message_id') and (presenter.head(d1) or {}).get('superseded', {}).get(
                      r2.get('presentation_id')) == r3.get('presentation_id'))
            asked = len(api['requests'])
            rerun = presenter.publish()
            check(sup, 'a re-run shows nothing twice', len(api['requests']) == asked
                  and all(r['outcome'] == 'already_presented' for r in rerun))
            old = answer(owner_reply(r1, 'accept: answering the first message'))
            check(sup, 'an answer to a superseded presentation is refused',
                  reason(old) == ('refused', 'superseded_presentation'))

        # AC3: content with no confirmed publication is never answerable
        unseen = 'answer/unseen-refused'
        with section(unseen):
            u1, u2, u3 = opened('U-1'), opened('U-2'), opened('U-3')
            api['mode'] = 'refuse'
            refused = presenter.present(u1)
            api['mode'] = 'drop'
            dropped = presenter.present(u2)
            api['mode'] = 'ok'
            sign_plan[:] = [True, False]  # the intent commits; the completion write is refused
            incomplete = presenter.present(u3)
            sign_plan[:] = []
            receipts = {u: next(iter(presenter.receipts(u)), {}) for u in (u1, u2, u3)}
            check(unseen, 'a refused, a lost and an unrecorded send leave no confirmed publication',
                  reason(refused) == ('refused', 'channel_refused') and reason(dropped) == ('unknown_outcome', 'unknown_outcome')
                  and reason(incomplete) == ('unknown_outcome', 'incomplete_transaction')
                  and [receipts[u].get('outcome') for u in (u1, u2, u3)] == ['refused', 'unknown_outcome', 'pending'])
            for u, label in ((u1, 'a refused'), (u2, 'a lost'), (u3, 'an unrecorded')):
                api['next'] += 1
                result = presenter.answer(edge_signed(hand_assertion(receipts[u], api['next'])))
                check(unseen, 'an answer to %s presentation is refused as unseen' % label,
                      reason(result) == ('refused', 'unseen_presentation'))
                check(unseen, '%s presentation settles nothing' % label, answered(u, 1) is None)
            check(unseen, 'unknown outcomes are visible in metrics', presenter.metrics()['unknown'] >= 2)
            asked = len(api['requests'])
            again = {u: presenter.present(u) for u in (u1, u2, u3)}
            check(unseen, 'only the refused presentation is attempted again',
                  len(api['requests']) == asked + 1 and reason(again[u1]) == ('published', None)
                  and again[u2]['outcome'] == again[u3]['outcome'] == 'unknown_outcome')
            seen = presenter.current(u1) or {}
            control = answer(owner_reply(seen, 'accept: now I have seen it'))
            check(unseen, 'control: once confirmed published, the same presentation settles',
                  reason(control) == ('accepted', None) and seen.get('attempt') == 2
                  and seen.get('presentation_id') == receipts[u1].get('presentation_id'))

        # AC2: only the current shown presentation may settle
        cur = 'answer/current-presentation-only'
        with section(cur):
            c1 = opened('C-1')
            c2 = opened('C-2')
            c3 = opened('C-3')
            for c in (c1, c2, c3):
                presenter.present(c)
            c1_r1, c2_r1, c3_r1 = (presenter.current(c) or {} for c in (c1, c2, c3))
            command('pm', 'revise', 'C-1', request_version=1, changes={'brief': 'Replace the brief: build only the parser.'})
            frame('pm', 'C-1', 2, 'Low: a wrong choice costs one review cycle.')
            check(cur, 'the brief was replaced under the same subject',
                  entity(c1)['data']['subject'] == c1_r1.get('request', {}).get('subject')
                  and entity(c1)['data']['brief'] != c1_r1.get('request', {}).get('brief'))
            replaced = answer(owner_reply(c1_r1, 'accept: approving the brief I saw'))
            check(cur, 'an answer to the presentation of the replaced brief is refused as stale',
                  reason(replaced) == ('refused', 'stale_presentation'))
            check(cur, 'the presentation of the replaced brief settles nothing', answered(c1, 1) is None)
            frame('pm', 'C-2', 1, 'High: the risk is now a production migration.')
            rerisked = answer(owner_reply(c2_r1, 'accept: approving the risk I saw'))
            check(cur, 'an answer to a presentation whose risk changed is refused',
                  reason(rerisked) == ('refused', 'stale_presentation') and answered(c2, 1) is None)
            command('pm', 'revise', 'C-3', request_version=1, changes={'choices': ['accept', 'reject', 'return_for_elaboration']})
            frame('pm', 'C-3', 2, 'Low: a wrong choice costs one review cycle.')
            rechosen = answer(owner_reply(c3_r1, 'accept: approving the choices I saw'))
            check(cur, 'an answer to a presentation whose choices changed is refused',
                  reason(rechosen) == ('refused', 'stale_presentation') and answered(c3, 1) is None)
            for c in (c1, c2, c3):
                presenter.present(c)
            c1_r2, c2_r2, c3_r2 = (presenter.current(c) or {} for c in (c1, c2, c3))
            superseded = answer(owner_reply(c1_r1, 'accept: approving the old message'))
            check(cur, 'after replacement the old presentation is refused as superseded',
                  reason(superseded) == ('refused', 'superseded_presentation'))
            unreferenced = answer(owner_reply(c1_r2, 'accept: no reference'), drop=V.REFERENCE_FIELDS)
            check(cur, 'an answer that names no presentation is refused',
                  reason(unreferenced) == ('refused', 'missing_presentation') and answered(c1, 2) is None)
            crossed = answer(owner_reply(c3_r2, 'accept: crossed'), change={
                'request_id': c2, 'request_version': c2_r2.get('request_version'), 'presentation_id': c2_r2.get('presentation_id'),
                'presentation_digest': c2_r2.get('brief_digest'), 'presentation_version': c2_r2.get('presentation_version')})
            check(cur, 'an answer naming one presentation while replying to another is refused',
                  reason(crossed) == ('refused', 'evidence_mismatch') and answered(c2, 1) is None)
            accepted = answer(owner_reply(c1_r2, 'accept: the parser-only brief is right'))
            check(cur, 'control: an answer to the current presentation settles',
                  reason(accepted) == ('accepted', None) and (answered(c1, 2) or {}).get('presentation_id')
                  == c1_r2.get('presentation_id'))
            twice = answer(owner_reply(c1_r2, 'reject: changed my mind'))
            check(cur, 'an answered request version refuses a second answer', reason(twice) == ('refused', 'already_answered')
                  and (answered(c1, 2) or {}).get('choice') == 'accept')
            check(cur, 'control: the other current presentations still settle',
                  reason(answer(owner_reply(c2_r2, 'reject: too risky'))) == ('accepted', None)
                  and reason(answer(owner_reply(c3_r2, 'return_for_elaboration: after the release'))) == ('accepted', None))

        # AC2: every answer records its own ruling and rationale
        rul = 'answer/ruling-and-rationale'
        with section(rul):
            record = answered(c1, 2) or {}
            reply_msg = api['messages'].get((owner_chat, record.get('attribution', {}).get('platform_message_id'))) or {}
            check(rul, 'the answer records its ruling, rationale and the presentation it names',
                  record.get('choice') == 'accept' and record.get('ruling') == 'approve'
                  and record.get('rationale') == 'the parser-only brief is right'
                  and record.get('presentation_id') == c1_r2.get('presentation_id')
                  and record.get('presentation_digest') == c1_r2.get('brief_digest')
                  and record.get('presentation_version') == c1_r2.get('presentation_version') and record.get('principal') == 'owner')
            check(rul, 'the answer keeps the platform\'s message, sender, time and reply identity',
                  reply_msg.get('reply_to') == c1_r2.get('message_id') == record.get('attribution', {}).get('reply_to_message_id')
                  and record.get('attribution', {}).get('sender_id') == owner_chat
                  and record.get('attribution', {}).get('platform_timestamp') == reply_msg.get('date'))
            edge_signers = base / 'edge_signers'
            edge_signers.write_text('telegram-edge namespaces="%s" %s\n' % (AUTHC.SIGNATURE_NAMESPACE, public['telegram-edge']))
            signature = base / 'answer.sig'
            signature.write_text(record.get('signature') or '')
            verified = _v65_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(edge_signers), '-I', 'telegram-edge', '-n',
                                    AUTHC.SIGNATURE_NAMESPACE, '-s', str(signature)],
                                   input=S.canonical_bytes(record.get('assertion') or {}), capture_output=True, timeout=10)
            check(rul, 'the recorded assertion verifies with the edge\'s restricted key and ssh-keygen alone',
                  verified.returncode == 0 and record.get('edge_key_id') == edge_key
                  and (record.get('assertion') or {}).get('rationale') == record.get('rationale'))
            c2_answer = answered(c2, 1) or {}
            check(rul, 'a rejection is an answer with its own ruling and rationale',
                  c2_answer.get('choice') == c2_answer.get('ruling') == 'reject' and c2_answer.get('rationale') == 'too risky')
            k1 = opened('K-1')
            presenter.present(k1)
            k1_r = presenter.current(k1) or {}
            for text, why, label in (('accept', 'missing_rationale', 'a ruling with no rationale'),
                                     ('accept:    ', 'missing_rationale', 'a blank rationale'),
                                     ('maybe: not sure', 'unmatched_choice', 'an unoffered ruling')):
                check(rul, '%s is refused' % label, reason(answer(owner_reply(k1_r, text))) == ('refused', why))
            message = owner_reply(k1_r, 'reject: tampered later')
            tampered = edge_signed(presenter.canonical_answer(message, 'telegram-edge'))
            tampered['assertion'] = dict(tampered['assertion'], choice='accept', ruling='approve')
            check(rul, 'an assertion changed after the edge signed it is refused',
                  reason(presenter.answer(tampered)) == ('refused', 'not_authorized'))
            check(rul, 'an assertion signed with the edge\'s ordinary key is refused',
                  reason(answer(owner_reply(k1_r, 'accept: ordinary key'), key='telegram-edge-other')) == ('refused', 'not_authorized'))
            check(rul, 'an assertion the owner signs as the edge is refused',
                  reason(answer(owner_reply(k1_r, 'accept: owner key'), key='owner')) == ('refused', 'not_authorized'))
            check(rul, 'an answer from another sender is refused',
                  reason(answer(owner_reply(k1_r, 'accept: not mine', sender=stranger_chat))) == ('refused', 'not_owner'))
            try:
                presenter.canonical_answer(owner_reply(k1_r, 'accept: automated', is_bot=True), 'telegram-edge')
                check(rul, 'automation is never turned into an answer', False)
            except V.Refused as exc:
                check(rul, 'automation is never turned into an answer', exc.code == 'not_owner')
            check(rul, 'no refused answer settled the request', answered(k1, 1) is None)
            check(rul, 'control: the owner\'s answer then settles',
                  reason(answer(owner_reply(k1_r, 'accept: fine as shown'))) == ('accepted', None)
                  and (answered(k1, 1) or {}).get('ruling') == 'approve')
            observed = presenter.observations
            check(rul, 'refusals are named with their error class, never labeled success',
                  all(o['reason'] in V.REFUSALS and o['error_class'] == V.REFUSALS[o['reason']] for o in observed if o['outcome'] == 'refused')
                  and all(o['error_class'] is None for o in observed if o['outcome'] in ('accepted', 'published')))
            check(rul, 'observations never carry a rationale or signature',
                  all('rationale' not in o and 'signature' not in o and 'fine as shown' not in _v65_json.dumps(o) for o in observed))
            m = presenter.metrics()
            check(rul, 'metrics count accepted and refused operations', m['accepted'] >= 8 and m['refused'] >= 15)

        # Review r7: the answer record is what the one settlement contract consumes
        consume = 'answer/settle-consumes-answer'
        with section(consume):
            state = CM.authority_state(S, conn)
            for rid, version, receipt, ruling in ((c1, 2, c1_r2, 'approve'), (c2, 1, c2_r2, 'reject')):
                record = answered(rid, version) or {}
                assertion = record.get('assertion') or {}
                delegation = dict(principal='owner', channel='telegram_chat', assertion_kinds=['decision_answer'],
                                  authority_scope=['project-a'], request_version=version,
                                  presentation_version=receipt.get('presentation_version'), expires_at=9e12,
                                  edge_key_id=edge_key)
                request = {'id': rid, 'version': version, 'scope': 'project-a', 'framing_digest': receipt.get('request_digest'),
                           'subject_digests': receipt.get('subject_digests'), 'roles': [], 'quorum': 1}
                settled = AUTHC.settle(request, [assertion], [delegation], [presenter.receipt(receipt.get('presentation_id', ''))],
                                       state['membership'], state['keyring'], _v65_time.time())
                check(consume, 'authority_contract.settle settles the recorded %s answer as it was recorded' % ruling,
                      settled['settled'] is True and (settled['settlement'] or {}).get('ruling') == ruling == record.get('ruling')
                      and (settled['settlement'] or {}).get('presentation_id') == receipt.get('presentation_id'))
            check(consume, 'recorded rulings are in the contract vocabulary',
                  all(d.get('ruling') in AUTHC.RULINGS for (t,) in conn.execute("SELECT data FROM entities WHERE kind='presentation_answer'")
                      for d in [_v65_json.loads(t)]))
            check(consume, 'no second settlement record exists',
                  conn.execute("SELECT COUNT(*) FROM entities WHERE kind='presentation_settlement'").fetchone()[0] == 0)
            command('pm', 'open', 'M-1', assignment=content(choices=('accept', 'maybe later')))
            frame('pm', 'M-1', 1, 'Low: a wrong choice costs one review cycle.')
            m1 = I.assignment_id(ids['repository_uuid'], 'M-1')
            asked = len(api['requests'])
            check(consume, 'a decision whose choices have no contract ruling is not presented',
                  reason(presenter.present(m1)) == ('refused', 'unmapped_choice') and len(api['requests']) == asked)

        # Review r1: only the requester frames, and what is shown names who did
        own = 'framing/requester-only'
        with section(own):
            q1 = opened('Q-1', risk='High: approving deploys to production.')
            presenter.present(q1)
            q1_r = presenter.current(q1) or {}
            held = api['messages'].get((q1_r.get('chat_id'), q1_r.get('message_id'))) or {}
            check(own, 'the shown bytes and the receipt name the requester as the one who stated the risk',
                  'Risk (stated by pm): High: approving deploys to production.' in held.get('text', '').split('\n')
                  and q1_r.get('framed_by') == 'pm')
            owner_frame = frame('owner', 'Q-1', 1, 'None: nothing can go wrong.')
            check(own, 'a project owner cannot replace the requester\'s risk statement',
                  reason(owner_frame) == ('refused', 'not_authorized')
                  and (entity('presentation-framing:' + q1) or {}).get('data', {}).get('framed_by') == 'pm')
            asked = len(api['requests'])
            direct_frame('owner', 'Q-1', 1, 'None: nothing can go wrong.')
            check(own, 'a framing by anyone but the requester frames nothing, however it was committed',
                  reason(presenter.present(q1)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            direct_frame('pm', 'Q-1', 1, 'High: approving deploys to production.')
            check(own, 'control: the requester\'s own framing is current again',
                  reason(presenter.present(q1)) == ('already_presented', None))

        # Review r2, r2b: a stored framing counts only when the frame operation accepted it
        stored = 'framing/stored-framing-reverified'
        with section(stored):
            for alias in ('P2-1', 'P2-2'):
                command('pm2', 'open', alias, assignment=content())
            p21, p22 = (I.assignment_id(ids['repository_uuid'], a) for a in ('P2-1', 'P2-2'))
            check(stored, 'control: the requester\'s framing through frame() is presented',
                  reason(frame('pm2', 'P2-1', 1, 'Low: a wrong choice costs one review cycle.')) == ('accepted', None)
                  and reason(presenter.present(p21)) == ('published', None))
            unsent = dict(ids, operation='frame', alias='P2-2', principal='pm2', request_version=1,
                          risk_statement='None: nothing can go wrong.', command_id='never-sent-1', nonce='never-sent-1')
            asked = len(api['requests'])
            for label, who, body in (('the requester signed but never submitted', 'pm2', unsent),
                                     ('a stranger signed', 'stranger', dict(unsent, principal='stranger', command_id='s-1', nonce='s-1'))):
                fixture('presentation-framing:' + p22, 'presentation_framing',
                        {'schema': V.FRAMING_SCHEMA, 'request_id': p22, 'request_version': 1,
                         'risk_statement': body['risk_statement'], 'framed_by': who, 'command_id': body['command_id'],
                         'key_id': 'key-' + who, 'framed_at': _v65_time.time() - 100,
                         'expected_versions': {'presentation-framing:' + p22: 0, p22: 1},
                         'signed': {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}},
                        command_id=body['command_id'], principal=who)
                check(stored, 'a framing %s, written by a generic store write, is not presented' % label,
                      reason(presenter.present(p22)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            fixture('key-pm2', 'verification_key', dict(principal='pm2', public_key=public['pm2'], effective_at=0,
                                                        revoked_at=_v65_time.time()))
            check(stored, 'control: a revocation after the framing was accepted strands nothing',
                  reason(presenter.present(p21)) == ('already_presented', None))
            check(stored, 'frame() refuses the revoked key',
                  reason(frame('pm2', 'P2-2', 1, 'None: nothing can go wrong.')) == ('refused', 'not_authorized'))
            direct_frame('pm2', 'P2-2', 1, 'None: nothing can go wrong.')
            check(stored, 'a framing the store accepted after the key was revoked is not presented',
                  reason(presenter.present(p22)) == ('refused', 'missing_framing') and len(api['requests']) == asked)

        # Review r5: an answer cannot predate what it answers
        order = 'answer/not-before-publication'
        with section(order):
            o1 = opened('O-1')
            presenter.present(o1)
            o1_r = presenter.current(o1) or {}
            api['next'] += 1
            early = hand_assertion(o1_r, api['next'])
            early['attribution']['platform_timestamp'] = (o1_r.get('published_at') or 0) - 3600
            check(order, 'an answer timestamped before the presentation was published is refused by name',
                  reason(presenter.answer(edge_signed(early))) == ('refused', 'answer_before_publication')
                  and answered(o1, 1) is None)
            api['next'] += 1
            same = hand_assertion(o1_r, api['next'])
            same['attribution']['platform_timestamp'] = o1_r.get('published_at')
            same_result = presenter.answer(edge_signed(same))
            check(order, 'control: an answer in the same second as the publication settles',
                  reason(same_result) == ('accepted', None) and answered(o1, 1) is not None)

        # Review r9: Release 1 presents a decision only in a person's private chat
        private = 'presentation/private-chat-only'
        with section(private):
            g1 = opened('G-1', owner='grouped')
            asked = len(api['requests'])
            check(private, 'a decision whose owner is enrolled in a group chat is refused by name and not sent',
                  reason(presenter.present(g1)) == ('refused', 'group_chat') and len(api['requests']) == asked
                  and not presenter.receipts(g1))
            check(private, 'the refusal is visible in the presentation metrics',
                  (presenter.metrics().get('unpresented_by_reason') or {}).get('group_chat') == 1)

        # Review r6: a replacement publishes even when the message it supersedes is gone
        gone = 'presentation/replacement-without-reply-target'
        with section(gone):
            x1 = opened('X-1')
            presenter.present(x1)
            x1_r1 = presenter.current(x1) or {}
            del api['messages'][(x1_r1.get('chat_id'), x1_r1.get('message_id'))]  # the owner deleted it
            command('pm', 'revise', 'X-1', request_version=1, changes={'brief': 'The revised brief the owner must see.'})
            frame('pm', 'X-1', 2, 'Low: a wrong choice costs one review cycle.')
            replaced = presenter.present(x1)
            x1_r2 = presenter.current(x1) or {}
            shown_text = (api['messages'].get((x1_r2.get('chat_id'), x1_r2.get('message_id'))) or {}).get('text', '')
            check(gone, 'the replacement is published without the missing reply target',
                  reason(replaced) == ('published', None) and x1_r2.get('request_version') == 2)
            check(gone, 'the replacement still names what it supersedes in the shown text',
                  'Supersedes: presentation version 1, message %s. Only this message can be answered.'
                  % x1_r1.get('message_id') in shown_text.split('\n'))
            check(gone, 'the receipt records that no reply link was made',
                  x1_r2.get('reply_linked') is False and x1_r2.get('reply_to_message_id') is None
                  and x1_r2.get('reply_to') == x1_r1.get('message_id'))
            check(gone, 'control: an ordinary replacement records its reply link',
                  (presenter.receipt(r2.get('presentation_id', '')) or {}).get('reply_linked') is True)

        # Review r8: receipt verification binds the reply link to what was sent and what the platform holds
        link = 'presentation/reply-link-verified'
        with section(link):
            linked = presenter.receipt(r2.get('presentation_id', '')) or {}
            held_link = platform(linked.get('chat_id'), linked.get('message_id'))
            check(link, 'control: a linked replacement verifies against the platform',
                  linked.get('reply_to') == r1.get('message_id') and V.receipt_problems(linked, held_link) == [])
            check(link, 'control: an unlinked replacement verifies against the platform',
                  V.receipt_problems(x1_r2, platform(x1_r2.get('chat_id'), x1_r2.get('message_id'))) == [])
            for field, value in (('reply_to', None), ('reply_to', (r1.get('message_id') or 0) + 1),
                                 ('reply_to_message_id', None), ('reply_linked', False)):
                altered = _v65_copy.deepcopy(linked)
                altered[field] = value
                check(link, 'a receipt with its %s changed to %r does not verify' % (field, value),
                      V.receipt_problems(altered, held_link) != [])
            check(link, 'a receipt whose platform message replies to another message does not verify',
                  V.receipt_problems(linked, dict(held_link or {}, reply_to=(r1.get('message_id') or 0) + 1)) != [])

        # Review r4: a presentation longer than one Telegram message is split, never truncated
        long_row = 'presentation/long-brief-split'
        with section(long_row):
            sentence = ('The specification \U0001F680 needs a decision on the parser \U0001F680 the store migration '
                        '\U0001F680 and the rollout order.')
            brief = ' '.join('%s (%d)' % (sentence, n) for n in range(110))
            l1 = opened('L-1', brief=brief)
            asked = len(api['requests'])
            published = presenter.present(l1)
            l1_r = presenter.current(l1) or {}
            ids_sent = list(l1_r.get('message_ids') or [])
            parts = [(api['messages'].get((owner_chat, m)) or {}).get('text', '') for m in ids_sent]
            check(long_row, 'a presentation longer than one message is published as consecutive messages',
                  reason(published) == ('published', None) and len(ids_sent) >= 3 and len(api['requests']) == asked + len(ids_sent)
                  and ids_sent == sorted(ids_sent) and l1_r.get('message_id') == ids_sent[-1])
            check(long_row, 'every part fits the platform limit',
                  parts and all(0 < len(p.encode('utf-16-le')) // 2 <= 4096 for p in parts))
            check(long_row, 'only the last part carries the choices and how to answer',
                  parts and all(('Choices: accept | reject' in p.split('\n')) == (i == len(parts) - 1)
                                and ('Answer by replying' in p) == (i == len(parts) - 1) for i, p in enumerate(parts)))
            body = ' '.join(' '.join(' '.join(p.split('\n')[1:]) for p in parts).split())
            check(long_row, 'the whole brief is shown in order, across the parts',
                  len(parts) > 1 and ' '.join(brief.split()) in body)
            check(long_row, 'no part links elsewhere', not any('http' in p for p in parts))
            check(long_row, 'the receipt binds every part\'s message and bytes',
                  l1_r.get('rendered') == parts and V.receipt_problems(l1_r, [platform(owner_chat, m) for m in ids_sent]) == [])
            altered = _v65_copy.deepcopy(l1_r)
            altered['message_ids'] = ids_sent[:1] + [(ids_sent[-1] if ids_sent else 0) + 1000] + ids_sent[2:]
            check(long_row, 'a receipt with one part\'s message changed does not verify',
                  V.receipt_problems(altered, [platform(owner_chat, m) for m in altered['message_ids']]) != [])
            first_part = dict(l1_r, message_id=ids_sent[0] if ids_sent else None)
            check(long_row, 'an answer to the first part names the same presentation and settles',
                  reason(answer(owner_reply(first_part, 'accept: read every part'))) == ('accepted', None)
                  and (answered(l1, 1) or {}).get('presentation_id') == l1_r.get('presentation_id'))
            check(long_row, 'control: a short presentation is one message',
                  (presenter.receipt(r1.get('presentation_id', '')) or {}).get('message_ids') == [r1.get('message_id')])

        # Review 2 n1: the store, not a constructor argument, decides whether the projection sends
        edge64 = P.TelegramEdge('http://127.0.0.1:%d' % server.server_address[1], api['token'])

        def about(request, start):
            return [(chat, text, reply) for chat, text, reply in api['requests'][start:]
                    if 'Request: %s' % request in text.split('\n') or 'Assignment: %s' % request in text.split('\n')]
        notice_row = 'projection/notice-superseded'
        with section(notice_row):
            command('pm', 'open', 'B-1', assignment=content())  # not yet framed: presentations not in use
            b1 = I.assignment_id(ids['repository_uuid'], 'B-1')
            start = len(api['requests'])
            notice_results = {r['assignment_id']: r for r in
                              P.Projection(S, inbox, edge64, conn, 'authority', journal_sign).project()}
            notice = conn.execute("SELECT id, data FROM entities WHERE kind='channel_projection' AND data LIKE ?",
                                  ('%"' + b1 + '"%',)).fetchone()
            notice_data = _v65_json.loads(notice[1]) if notice else {}
            check(notice_row, 'before presentations are enabled the inbox projection sends its notice',
                  notice_results.get(b1, {}).get('outcome') == 'sent' and len(about(b1, start)) == 1)
            frame('pm', 'B-1', 1, 'Low: a wrong choice costs one review cycle.')
            presenter.present(b1)
            b1_r = presenter.current(b1) or {}
            shown_b1 = (api['messages'].get((owner_chat, b1_r.get('message_id'))) or {})
            check(notice_row, 'the first presentation is a reply to that notice and names it',
                  shown_b1.get('reply_to') == notice_data.get('message_id') is not None
                  and 'Supersedes: the notice message %s. Only this message can be answered.' % notice_data.get('message_id')
                  in shown_b1.get('text', '').split('\n'))
            after_notice = _v65_json.loads(conn.execute('SELECT data FROM entities WHERE id=?', (notice[0],)).fetchone()[0]) if notice else {}
            check(notice_row, 'the notice\'s record is marked superseded by the presentation',
                  after_notice.get('superseded_by') == b1_r.get('presentation_id') is not None
                  and after_notice.get('message_id') == notice_data.get('message_id'))
            check(notice_row, 'the presentation\'s receipt verifies with its reply link to the notice',
                  V.receipt_problems(b1_r, platform(owner_chat, b1_r.get('message_id'))) == [] and b1_r.get('reply_linked') is True)

        silent = 'projection/silent-from-store'
        with section(silent):
            a1 = opened('A-1')
            presenter.present(a1)
            start = len(api['requests'])
            restarted = {r['assignment_id']: r for r in P.Projection(S, inbox, edge64, conn, 'authority', journal_sign).project()}
            check(silent, 'a projection built without the presenter sends nothing for a request that has a presentation',
                  about(a1, start) == [] and about(b1, start) == [] and restarted.get(a1, {}).get('outcome') == 'presented')
            a2 = opened('A-2')
            start = len(api['requests'])
            framed_only = {r['assignment_id']: r for r in P.Projection(S, inbox, edge64, conn, 'authority', journal_sign).project()}
            check(silent, 'a framed request is presentation-bound: nothing is sent before its presentation exists',
                  about(a2, start) == [] and framed_only.get(a2, {}).get('outcome') == 'awaiting_presentation')
            fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                    dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=owner_chat,
                         revoked_at=None, presentations='enabled'))
            command('pm', 'open', 'S-9', assignment=content())
            s9 = I.assignment_id(ids['repository_uuid'], 'S-9')
            start = len(api['requests'])
            quiet = {r['assignment_id']: r for r in P.Projection(S, inbox, edge64, conn, 'authority', journal_sign).project()}
            check(silent, 'with presentations enabled on the enrollment, nothing is sent even before a presentation exists',
                  about(s9, start) == [] and quiet.get(s9, {}).get('outcome') == 'awaiting_presentation')
            check(silent, 'control: an owner without the setting and without a presentation still gets the notice',
                  enroll_other_and_project())
            check(silent, 'the receipt and framing kinds the projection reads are the presentation organ\'s',
                  getattr(P, 'PRESENTATION_KIND', None) == V.RECEIPT_KIND and getattr(P, 'FRAMING_KIND', None) == V.FRAMING_KIND)

        # Review r3: with presentations enabled, one decision message per request version
        one = 'projection/one-message-per-version'
        with section(one):
            projector = P.Projection(S, inbox, P.TelegramEdge('http://127.0.0.1:%d' % server.server_address[1], api['token']),
                                     conn, 'authority', journal_sign, presenter=presenter)
            t1 = opened('T-1')

            def about(request, start):
                return [(chat, text, reply) for chat, text, reply in api['requests'][start:]
                        if 'Request: %s' % request in text.split('\n') or 'Assignment: %s' % request in text.split('\n')]
            start = len(api['requests'])
            projected = {r['assignment_id']: r for r in projector.project()}
            presenter.publish()
            first = about(t1, start)
            t1_r1 = presenter.current(t1) or {}
            check(one, 'one request version reaches the owner as exactly one message',
                  len(first) == 1 and t1_r1.get('message_ids') == [t1_r1.get('message_id')])
            check(one, 'that one message carries the choices and how to answer',
                  len(first) == 1 and 'Choices: accept | reject' in first[0][1].split('\n') and 'Answer by replying' in first[0][1])
            check(one, 'the inbox projection sends no notice of its own and says the presentation carries it',
                  projected.get(t1, {}).get('outcome') == 'awaiting_presentation'
                  and not conn.execute("SELECT COUNT(*) FROM entities WHERE kind='channel_projection' AND data LIKE ?",
                                       ('%' + t1 + '%',)).fetchone()[0])
            again = {r['assignment_id']: r for r in projector.project()}
            check(one, 'once presented, the projection reports the entry as presented',
                  again.get(t1, {}).get('outcome') == 'presented')
            command('pm', 'revise', 'T-1', request_version=1, changes={'brief': 'A revised brief.'})
            frame('pm', 'T-1', 2, 'Low: a wrong choice costs one review cycle.')
            start = len(api['requests'])
            projector.project()
            presenter.publish()
            second = about(t1, start)
            check(one, 'the revision is again exactly one message, a reply to the first',
                  len(second) == 1 and second[0][2] == t1_r1.get('message_id'))
            t1_r2 = presenter.current(t1) or {}
            check(one, 'the owner\'s reply to the one message settles the request version',
                  reason(answer(owner_reply(t1_r2, 'accept: the revised brief is right'))) == ('accepted', None)
                  and (answered(t1, 2) or {}).get('presentation_id') == t1_r2.get('presentation_id'))
            check(one, 'the projection\'s metrics show what could not be presented, by reason',
                  (projector.metrics().get('unpresented_by_reason') or {}).get('group_chat') == 1)

        # Review 2 n6: a framing key is judged by the store's journal order, never by a time a caller supplies
        order_row = 'framing/key-by-store-order'
        with section(order_row):
            for alias in ('K3-1', 'K3-2', 'K3-3'):
                command('pm3', 'open', alias, assignment=content())
            k31, k32, k33 = (I.assignment_id(ids['repository_uuid'], a) for a in ('K3-1', 'K3-2', 'K3-3'))
            now = _v65_time.time()
            direct_frame('pm3', 'K3-1', 1, 'Low: framed before the revocation.', committed_at=now + 10 ** 6)
            fixture('key-pm3', 'verification_key', dict(principal='pm3', public_key=public['pm3'], effective_at=0,
                                                        revoked_at=now - 1000))
            check(order_row, 'control: a framing the store took before the revocation counts, whatever times the records carry',
                  reason(presenter.present(k31)) == ('published', None))
            asked = len(api['requests'])
            direct_frame('pm3', 'K3-2', 1, 'None: back-dated before the revocation.', committed_at=now - 2000)
            check(order_row, 'a framing the store took after the revocation, with a back-dated time, is not presented',
                  reason(presenter.present(k32)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            direct_frame('pm3', 'K3-3', 1, 'None: at the store\'s own time.')
            check(order_row, 'the same framing at the store\'s own time is not presented either',
                  reason(presenter.present(k33)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            command('pm4', 'open', 'K4-1', assignment=content())
            k41 = I.assignment_id(ids['repository_uuid'], 'K4-1')
            fixture('authority:revocations', 'revocation_ledger',
                    {'revocation_version': 1, 'revoked': {'pm4': {'at': now + 10 ** 6, 'reason': 'test', 'by': 'authority'}}})
            direct_frame('pm4', 'K4-1', 1, 'None: framed by a revoked principal.')
            check(order_row, 'a framing by a principal the revocation ledger revoked earlier in the journal is not presented',
                  reason(presenter.present(k41)) == ('refused', 'missing_framing') and len(api['requests']) == asked)
            check(order_row, 'the ledger this reads is the revocation organ\'s',
                  getattr(V, 'REVOCATION_LEDGER', None) == _v65_load('v65_revocation', organs / 'control_revocation.py').LEDGER_ENTITY)

        # Review 2 n2: a part Telegram definitely refused is sent again, after its retry_after
        again_row = 'presentation/refused-part-sent-again'
        with section(again_row):
            flood_brief = ' '.join(['The specification needs a decision on the parser and the rollout order (%d).' % n
                                    for n in range(60)])
            f2 = opened('F-2', brief=flood_brief)
            api['flood_after'] = 1
            asked = len(api['requests'])
            first_try = presenter.present(f2)
            partial = (presenter.receipts(f2) or [{}])[0]
            check(again_row, 'a part the platform refused leaves the earlier parts and a named refusal',
                  reason(first_try) == ('partial', 'channel_refused') and len(partial.get('rendered') or []) >= 2
                  and len(partial.get('message_ids') or []) == 1 and len(api['requests']) == asked + 1)
            wait = presenter.present(f2)
            check(again_row, 'a run inside the platform\'s retry_after sends nothing',
                  reason(wait) == ('refused', 'retry_after') and len(api['requests']) == asked + 1)
            real_clock = presenter.clock
            presenter.clock = lambda: real_clock() + 5
            try:
                done = presenter.present(f2)
            finally:
                presenter.clock = real_clock
            f2_r = presenter.current(f2) or {}
            check(again_row, 'after retry_after only the missing parts are sent and the presentation completes',
                  reason(done) == ('published', None) and len(api['requests']) == asked + len(partial.get('rendered') or [])
                  and (f2_r.get('message_ids') or [None])[0] == (partial.get('message_ids') or [0])[0]
                  and len(f2_r.get('message_ids') or []) == len(f2_r.get('rendered') or []))
            check(again_row, 'the completed receipt verifies against every part the platform holds',
                  V.receipt_problems(f2_r, [platform(owner_chat, m) for m in f2_r.get('message_ids') or []]) == [])
            check(again_row, 'the owner\'s reply to the first part then settles',
                  reason(answer(owner_reply(dict(f2_r, message_id=(f2_r.get('message_ids') or [None])[0]),
                                            'accept: read both parts'))) == ('accepted', None))

        # Review 2 n5: choices match whatever the phone did to case and spacing; no reply meets silence
        match_row = 'answer/choice-matching-and-feedback'
        with section(match_row):
            for n, text in enumerate(('Accept: looks right', 'ACCEPT: looks right', 'accept : looks right',
                                      '  Accept   :  looks right')):
                mid = opened('CM-%d' % n)
                presenter.present(mid)
                result = answer(owner_reply(presenter.current(mid) or {}, text))
                recorded = answered(mid, 1) or {}
                check(match_row, '%r is the offered choice accept' % text,
                      reason(result) == ('accepted', None) and recorded.get('choice') == 'accept'
                      and recorded.get('ruling') == 'approve' and recorded.get('rationale') == 'looks right')
            wrong = opened('CM-W')
            presenter.present(wrong)
            wrong_r = presenter.current(wrong) or {}
            for text, why in (('accept - looks right', 'unmatched_choice'), ('maybe: not sure', 'unmatched_choice'),
                              ('accept', 'missing_rationale')):
                asked = len(api['requests'])
                message = owner_reply(wrong_r, text)
                result = answer(message)
                told = api['requests'][asked:]
                check(match_row, '%r is refused as %s and the owner is told the valid choices' % (text, why),
                      reason(result) == ('refused', why) and len(told) == 1 and told[0][0] == owner_chat
                      and told[0][2] == message['message_id'] and 'accept | reject' in told[0][1])
            check(match_row, 'control: the refused replies answered nothing, and a matching one then does',
                  answered(wrong, 1) is None and reason(answer(owner_reply(wrong_r, 'Reject: not now'))) == ('accepted', None))

        # Review 3 item 6: a presentation supersedes only its own request's notice, of the projection's own kind
        kind_row = 'presentation/notice-kind-fixed'
        with section(kind_row):
            b1_notice = notice[0] if notice else None
            decoy = 'decoy:' + I.assignment_id(ids['repository_uuid'], 'FG-0')
            fixture(decoy, 'decoy_record', {'assignment_id': I.assignment_id(ids['repository_uuid'], 'FG-0'),
                                            'outcome': 'sent', 'message_id': 424242})
            for n, (label, target, kind) in enumerate((('a record of another kind for the same request', decoy, 'decoy_record'),
                                                       ('another request\'s notice', b1_notice, 'channel_projection'))):
                fg = opened('FG-%d' % n)
                _, base_record, _ = presenter.compose(fg)
                held_before = entity(target) if target else None
                forged = dict(base_record, supersedes={'notice_id': target, 'notice_kind': kind, 'chat_id': owner_chat,
                                                       'message_id': 424242 + n}, reply_to=None)
                forged['rendered'] = V.render(forged)
                forged['brief_digest'] = 'sha256:' + _v65_hashlib.sha256(_v65_json.dumps(
                    forged['rendered'], sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')).hexdigest()
                forged['presentation_id'] = V.presentation_id(fg, 1, forged['brief_digest'])  # its own request
                fpid, fhid = forged['presentation_id'], V.head_id(fg)
                refused_code = None
                try:
                    S.execute(conn, dict(command_id='forge-intent-%d' % n, principal='authority', operation=V.RECORD_OPERATION,
                                         parameters=dict(phase='intent', presentation_id=fpid, head_id=fhid, record=forged),
                                         expected_versions={fpid: 0}, artifact_digests=[], nonce='forge-intent-%d' % n),
                              'authority', journal_sign, 1)
                    parts = [{'chat_id': owner_chat, 'message_id': 525252 + 10 * n + i, 'date': 1790000000, 'text': t,
                              'reply_to_message_id': None} for i, t in enumerate(forged['rendered'])]
                    S.execute(conn, dict(command_id='forge-complete-%d' % n, principal='authority', operation=V.RECORD_OPERATION,
                                         parameters=dict(phase='complete', presentation_id=fpid, head_id=fhid, attempt=1,
                                                         parts=parts, refusal=None),
                                         expected_versions={fpid: 1, fhid: (entity(fhid) or {}).get('version', 0),
                                                            target: (held_before or {}).get('version', 0)},
                                         artifact_digests=[], nonce='forge-complete-%d' % n), 'authority', journal_sign, 1)
                except S.StoreRefused as exc:
                    refused_code = exc.code
                check(kind_row, 'a presentation naming %s as the notice it supersedes is refused and leaves it unchanged' % label,
                      held_before is not None and refused_code is not None and entity(target) == held_before)

        # Review 3 item 4: frame() and the stored-framing check apply one key rule
        agree = 'framing/frame-and-presenter-agree'
        with section(agree):
            for alias in ('Z-1', 'Z-2', 'Z-3', 'Z-4', 'Z-5'):
                command('pm5', 'open', alias, assignment=content())
            later = _v65_time.time() + 3600
            for alias, field, label in (('Z-1', 'revoked_at', 'a revocation dated in the future'),
                                        ('Z-2', 'retired_at', 'a retirement dated in the future'),
                                        ('Z-3', 'effective_at', 'a key not yet effective')):
                key = dict(principal='pm5', public_key=public['pm5'], effective_at=0)
                key[field] = later
                fixture('key-pm5', 'verification_key', key)
                zid = I.assignment_id(ids['repository_uuid'], alias)
                check(agree, 'frame() refuses a key with %s' % label,
                      reason(frame('pm5', alias, 1, 'Low: a wrong choice costs one review cycle.')) == ('refused', 'not_authorized'))
                direct_frame('pm5', alias, 1, 'Low: a wrong choice costs one review cycle.')
                check(agree, 'the presenter refuses the same framing written directly, with %s' % label,
                      reason(presenter.present(zid)) == ('refused', 'missing_framing'))
            fixture('key-pm5', 'verification_key', dict(principal='pm5', public_key=public['pm5'], effective_at=0))
            z4 = I.assignment_id(ids['repository_uuid'], 'Z-4')
            check(agree, 'control: with a usable key frame() accepts and the presenter presents',
                  reason(frame('pm5', 'Z-4', 1, 'Low: a wrong choice costs one review cycle.')) == ('accepted', None)
                  and reason(presenter.present(z4)) == ('published', None))
            ledger_now = (entity('authority:revocations') or {}).get('data') or {'revocation_version': 0, 'revoked': {}}
            fixture('authority:revocations', 'revocation_ledger',
                    dict(ledger_now, revoked=dict(ledger_now.get('revoked') or {}, pm5={'at': later, 'reason': 'test', 'by': 'authority'})))
            check(agree, 'frame() refuses a principal the revocation ledger names, as the presenter does',
                  reason(frame('pm5', 'Z-5', 1, 'Low: a wrong choice costs one review cycle.')) == ('refused', 'not_authorized'))
            command('pm6', 'open', 'Z-6', assignment=content())
            z6 = I.assignment_id(ids['repository_uuid'], 'Z-6')

            class LedgerRace:
                """The store, with a ledger revocation of pm6 landing between frame()'s read and its commit."""
                fired = False

                def __getattr__(self, name):
                    return getattr(S, name)

                def execute(self, conn_, cmd, *a, **k):
                    if cmd.get('operation') == V.FRAME_OPERATION and not LedgerRace.fired:
                        LedgerRace.fired = True
                        held = (entity('authority:revocations') or {}).get('data') or {'revocation_version': 0, 'revoked': {}}
                        fixture('authority:revocations', 'revocation_ledger',
                                dict(held, revoked=dict(held.get('revoked') or {}, pm6={'at': later, 'reason': 'test', 'by': 'authority'})))
                    return S.execute(conn_, cmd, *a, **k)
            presenter.store = LedgerRace()
            try:
                raced_frame = frame('pm6', 'Z-6', 1, 'Low: a wrong choice costs one review cycle.')
            finally:
                presenter.store = S
            check(agree, 'a ledger revocation between frame()\'s read and its commit refuses the framing, as the presenter would',
                  raced_frame.get('outcome') == 'refused' and reason(presenter.present(z6)) == ('refused', 'missing_framing'))

        # Review 3 item 5: retry_after counts only as a bounded non-negative integer
        bounded = 'presentation/retry-after-bounded'
        with section(bounded):
            for n, (label, params) in enumerate((('a string', {'retry_after': '3'}), ('a fraction', {'retry_after': 1.5}),
                                                 ('a negative number', {'retry_after': -1}), ('a huge number', {'retry_after': 10 ** 12}),
                                                 ('a boolean', {'retry_after': True}), ('an omitted value', None),
                                                 ('infinity', 'INF'))):
                rb = opened('RB-%d' % n, brief=' '.join(['The rollout needs a decision on the parser (%d).' % k for k in range(90)]))
                api['flood_after'], api['flood_params'] = 1, params
                first_run = presenter.present(rb)
                api['flood_params'] = {'retry_after': 3}
                next_run = presenter.present(rb)
                check(bounded, 'retry_after as %s means the next run sends the rest' % label,
                      reason(first_run) == ('partial', 'channel_refused') and reason(next_run) == ('published', None))

        # Review 3 item 8: choices match under NFKC and case folding, with spaces, underscores and hyphens alike
        nfkc = 'answer/choice-normalization'
        with section(nfkc):
            for n, (choices, text, choice, rationale) in enumerate((
                    (('accept', 'reject'), '\uff21\uff23\uff23\uff25\uff30\uff34: full-width letters', 'accept', 'full-width letters'),
                    (('accept', 'reject'), 'accept\uff1a full-width colon', 'accept', 'full-width colon'),
                    (('accept', 'reject', 'return_for_elaboration'), 'return for elaboration: need more',
                     'return_for_elaboration', 'need more'),
                    (('accept', 'reject', 'return_for_elaboration'), 'Return-For-Elaboration: need more',
                     'return_for_elaboration', 'need more'))):
                nid = opened('NF-%d' % n, choices=choices)
                presenter.present(nid)
                result = answer(owner_reply(presenter.current(nid) or {}, text))
                recorded = answered(nid, 1) or {}
                check(nfkc, '%r is the offered choice %s' % (text, choice),
                      reason(result) == ('accepted', None) and recorded.get('choice') == choice
                      and recorded.get('rationale') == rationale)

        # Review 3 item 2: after a version is answered, a reply is told so, not told it matched nothing
        done_row = 'answer/after-answered-reply'
        with section(done_row):
            aa = opened('AA-1')
            presenter.present(aa)
            aa_r = presenter.current(aa) or {}
            check(done_row, 'control: the owner answers once', reason(answer(owner_reply(aa_r, 'accept: fine'))) == ('accepted', None))
            for text in ('thanks!', 'reject: changed my mind'):
                asked = len(api['requests'])
                message = owner_reply(aa_r, text)
                result = answer(message)
                told = api['requests'][asked:]
                check(done_row, 'after the answer, %r is refused as already answered and the owner is told the ruling' % text,
                      reason(result) == ('refused', 'already_answered') and len(told) == 1 and told[0][2] == message['message_id']
                      and 'already answered: approve' in told[0][1] and 'did not match' not in told[0][1])
            check(done_row, 'the recorded answer is unchanged', (answered(aa, 1) or {}).get('ruling') == 'approve')

        # Review 3 item 3: the message back is sent once per inbound message, never again on redelivery
        once = 'answer/tell-once-per-message'
        with section(once):
            to1 = opened('TO-1')
            presenter.present(to1)
            to1_r = presenter.current(to1) or {}
            first_msg = owner_reply(to1_r, 'hello')
            counts = []
            for message in (first_msg, first_msg, owner_reply(to1_r, 'hello')):
                asked = len(api['requests'])
                answer(message)
                counts.append(len(api['requests']) - asked)
            check(once, 'the first delivery of a non-answer is told once', counts[0] == 1)
            check(once, 'the same message delivered again is not told again', counts[1] == 0)
            check(once, 'control: another message with the same text is told', counts[2] == 1)
            check(once, 'the message told is recorded by its platform identity',
                  conn.execute("SELECT COUNT(*) FROM entities WHERE id=?",
                               ('presentation-tell:telegram_chat:%d:%d' % (owner_chat, first_msg['message_id']),)).fetchone()[0] == 1)

        # Review 3 item 1: a notice still in flight, or of unknown outcome, when the first presentation goes out
        flight = 'projection/in-flight-notice-superseded'
        with section(flight):
            def notice_of(rid):
                row = conn.execute("SELECT id, data FROM entities WHERE kind='channel_projection' AND data LIKE ?",
                                   ('%"' + rid + '"%',)).fetchone()
                return (row[0], _v65_json.loads(row[1])) if row else (None, {})

            class Racing:
                """The store, with one foreign command landing just before a chosen projection intent."""
                def __init__(self, before_intent_of, act):
                    self.target, self.act, self.fired = before_intent_of, act, False

                def __getattr__(self, name):
                    return getattr(S, name)

                def execute(self, conn_, cmd, *a, **k):
                    params = cmd.get('parameters') or {}
                    if (not self.fired and cmd.get('operation') == P.OPERATION and params.get('phase') == 'intent'
                            and (params.get('record') or {}).get('assignment_id') == self.target):
                        self.fired = True
                        self.act()
                    return S.execute(conn_, cmd, *a, **k)
            command('pm', 'open', 'IF-1', assignment=content(owner='stranger'))  # an owner without the presentations setting
            if1 = I.assignment_id(ids['repository_uuid'], 'IF-1')
            start = len(api['requests'])
            raced = {r['assignment_id']: r for r in P.Projection(Racing(if1, lambda: frame('pm', 'IF-1', 1, 'Low: one review.')),
                                                                 inbox, edge64, conn, 'authority', journal_sign).project()}
            presenter.present(if1)
            check(flight, 'a framing that lands after the projection decided refuses its notice intent: one message only',
                  (raced.get(if1) or {}).get('outcome') == 'refused' and len(about(if1, start)) == 1
                  and notice_of(if1)[0] is None)

            command('pm', 'open', 'IF-2', assignment=content(owner='stranger'))  # an owner without the presentations setting
            if2 = I.assignment_id(ids['repository_uuid'], 'IF-2')

            class InFlight:
                """The platform edge; while the notice for IF-2 is in flight, the framing and presentation land."""
                fired = False

                def send(self, chat, text):
                    if not self.fired and 'Assignment: %s' % if2 in text.split('\n'):
                        InFlight.fired = True
                        frame('pm', 'IF-2', 1, 'Low: one review.')
                        presenter.present(if2)
                    return edge64.send(chat, text)
            P.Projection(S, inbox, InFlight(), conn, 'authority', journal_sign).project()
            if2_r = presenter.current(if2) or {}
            nid2, n2 = notice_of(if2)
            check(flight, 'a presentation composed while the notice is in flight names that notice in its text',
                  any(line.startswith('Supersedes: an earlier notice of this request') for line in (if2_r.get('rendered') or [''])[0].split('\n'))
                  and (if2_r.get('supersedes') or {}).get('notice_id') == nid2 is not None)
            check(flight, 'once the notice\'s outcome is known, the next run marks it superseded',
                  n2.get('outcome') == 'sent' and not n2.get('superseded_by')
                  and reason(presenter.present(if2)) == ('already_presented', None)
                  and notice_of(if2)[1].get('superseded_by') == if2_r.get('presentation_id'))

            command('pm', 'open', 'IF-3', assignment=content(owner='stranger'))  # an owner without the presentations setting
            if3 = I.assignment_id(ids['repository_uuid'], 'IF-3')
            api['mode'] = 'drop'
            P.Projection(S, inbox, edge64, conn, 'authority', journal_sign).project()
            api['mode'] = 'ok'
            frame('pm', 'IF-3', 1, 'Low: one review.')
            presenter.present(if3)
            if3_r = presenter.current(if3) or {}
            nid3, n3 = notice_of(if3)
            check(flight, 'a notice of unknown outcome is named by the first presentation and marked superseded',
                  n3.get('outcome') == 'unknown_outcome' and n3.get('superseded_by') == if3_r.get('presentation_id') is not None
                  and any(line.startswith('Supersedes: an earlier notice of this request') for line in (if3_r.get('rendered') or [''])[0].split('\n')))
            check(flight, 'the ids the projection pins are the presentation organ\'s',
                  getattr(P, 'framing_entity_id', lambda r: None)(if1) == V.framing_id(if1))
    finally:
        server.shutdown()
        server.server_close()

    allowed = base / 'allowed_signers'
    allowed.write_text('authority ' + public['authority'] + '\n')
    for message, signature_text in journal_signed[-3:] + journal_signed[:2]:
        sig = base / 'journal.sig'
        sig.write_text(signature_text)
        verified = _v65_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'authority', '-n', 'veldo-journal',
                                '-s', str(sig)], input=message, capture_output=True, timeout=10)
        check('install/assets', 'journal record signature verifies', verified.returncode == 0)
    conn.close()
    return rows


_v65_started = _v65_time.monotonic()
with _v65_temp.TemporaryDirectory(prefix='v65-') as _v65_dir:
    _v65_rows = _v65_checks(_v65_Path(_v65_dir))
for _v65_name, _v65_observed in _v65_rows.items():
    _v65_ok = bool(_v65_observed) and all(ok for _, ok in _v65_observed)
    if not _v65_ok:
        for _v65_label, _v65_one in _v65_observed:
            if not _v65_one:
                print('  VELDO-0065 %s detail: %s' % (_v65_name, _v65_label))
    expect('VELDO-0065 ' + _v65_name, _v65_ok)
print('VELDO-0065 suite seconds: %.3f' % (_v65_time.monotonic() - _v65_started))
