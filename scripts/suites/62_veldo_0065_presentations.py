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
                                  'presentation/reply-link-verified')}

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
    for who in ('authority', 'owner', 'pm', 'pm2', 'grouped', 'stranger', 'telegram-edge', 'telegram-edge-other'):
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
        chat = receipt['chat_id'] if chat is None else chat
        reply_to = receipt['message_id'] if reply_to is None else reply_to
        api['next'] += 1
        date = 1790000000 + api['next']
        api['messages'][(chat, api['next'])] = {'text': text, 'date': date, 'reply_to': reply_to, 'from_bot': is_bot}
        return {'message_id': api['next'], 'date': date, 'text': text,
                'from': {'id': sender, 'is_bot': is_bot, 'first_name': 'Owner'},
                'chat': {'id': chat, 'type': 'private'}, 'reply_to_message': {'message_id': reply_to}}

    def edge_signed(assertion, key='telegram-edge'):
        return {'assertion': assertion, 'signature': sign_as(key, S.canonical_bytes(assertion))}

    def answer(message, change=None, key='telegram-edge', drop=()):
        assertion = presenter.canonical_answer(message, 'telegram-edge')
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

    def direct_frame(who, alias, version, risk, key=None, signer=None):
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
                         'authority', journal_sign, 1)

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
                  held.get('text') is not None and r1.get('rendered', '').encode('utf-8') == text.encode('utf-8')
                  and r1.get('brief_digest') == 'sha256:' + _v65_hashlib.sha256(text.encode('utf-8')).hexdigest()
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
                        'rendered': text + ' ', 'risk_statement': 'None.', 'authority_statement': 'Anyone answers.',
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
                                     ('maybe: not sure', 'invalid_input', 'an unoffered ruling')):
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
