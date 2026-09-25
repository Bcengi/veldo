"""VELDO-0068: atomic request settlement and conjunctive authority over a real signed store.

Run: python3 scripts/selftest.py --suite 69_veldo_0068_settlement

Every answer is an owner's reply to a real VELDO-0065 presentation over a loopback Bot API (real HTTP
in the platform's documented shapes; not the Telegram service, no network, no real token), attributed
by the actual VELDO-0066 Acquirer, signed by the actual protected signer process through the VELDO-0067
edge and accepted by the actual presenter; or a signed answer from the authenticated API edge. Every
command, journal record and assertion is a real OpenSSH signature on a real SQLite store; publication
is a VELDO-0035 accepted revision and snapshot over a real Git repository, read back in another
process. Mutation workers replace the production copies named in PRODUCTION below, never assertions
or fixtures. Where the settlement module is absent (the pre-change tree, for the red record) every
row drives the path that tree has, the answers recorded by the presenter and nothing settling them,
so each row fails by its own assertions rather than by an exception. No private key byte, signature
or rationale is printed or retained.
"""
import copy as _v68_copy
import hashlib as _v68_hashlib
import http.server as _v68_http
import importlib.util as _v68_import
import json as _v68_json
import os as _v68_os
from pathlib import Path as _v68_Path
import shutil as _v68_shutil
import subprocess as _v68_sp
import sys as _v68_sys
import tempfile as _v68_temp
import threading as _v68_threading
import time as _v68_time

_V68_ROWS = ('install/assets', 'ruling/offered-choice-and-reasoning', 'settlement/one-winner',
             'settlement/one-transaction', 'terminal/materialized-settlement', 'authority/roles-and-independence',
             'authority/owner-and-presentation', 'authority/unsupported-quorum-blocks')
# The touchpoints the specification names; the suite checks the journey enables exactly these.
_V68_NAMED = ('grooming', 'admission', 'priority', 'finding_disposition', 'decision_disposition')
# The offered choices every touchpoint is answered with, and the contract ruling each one is.
_V68_CHOICES = {'accept': 'approve', 'return_for_elaboration': 'return_for_elaboration', 'reject': 'reject'}


def _v68_load(name, path):
    spec = _v68_import.spec_from_file_location(name, path)
    module = _v68_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v68_message(st, bot, sender, chat, text, reply_to=None):
    """One message as the platform keeps and delivers it: its id numbered per bot, the platform's date,
    the sender's User, the chat, the text and, for a reply, the replied message as the platform holds it."""
    with st['lock']:
        bot['next'] += 1
        st['tick'] += 1
        message = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
                   'text': text}
        if reply_to is not None:
            held = bot['messages'][(chat['id'], reply_to)]
            message['reply_to_message'] = _v68_copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
        bot['messages'][(chat['id'], message['message_id'])] = message
        return message


class _V68BotApi(_v68_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes, per bot name."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = _v68_json.loads(raw) if raw else {}
        _, _, rest = self.path.partition('/bot')
        name, _, method = rest.partition('/')
        bot = st['bots'].get(name)
        if bot is None:
            return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
        if method == 'getMe':
            return self._answer(200, {'ok': True, 'result': dict(bot['user'], can_join_groups=True)})
        if method == 'getUpdates':
            offset = body.get('offset') or 0
            if offset:
                bot['updates'] = [u for u in bot['updates'] if u['update_id'] >= offset]
            return self._answer(200, {'ok': True, 'result': bot['updates'][:body.get('limit') or 100]})
        if method == 'sendMessage':
            chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
            reply = (body.get('reply_parameters') or {}).get('message_id')
            if reply is not None and (chat['id'], reply) not in bot['messages']:
                reply = None
            return self._answer(200, {'ok': True, 'result': _v68_message(st, bot, bot['user'], chat, body['text'], reply)})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = _v68_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


# The child that reads the published snapshot: the installed store, snapshot and settlement modules,
# a read-only connection, and the materialized revision compared with the accepted store snapshot.
_V68_CHILD = '''import importlib.util, json, sys
from pathlib import Path
def load(name):
    s = importlib.util.spec_from_file_location(name, Path(sys.argv[1]) / (name + '.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st = load('control_store'); sn = load('control_snapshot')
if not (Path(sys.argv[1]) / 'control_request_settlement.py').is_file():
    print(json.dumps({'refusal': 'no_settlement_module'})); sys.exit(0)
rs = load('control_request_settlement')
c = st.open_store(sys.argv[2], mode='r')
try:
    s = sn.load(st, c, sys.argv[5], sys.argv[6], sys.argv[7])
    r = sn.read_materialized(s, sys.argv[3], sys.argv[4])
    out = {'requests': {a: rs.published_state(r['members'], a) for a in sys.argv[8:]},
           'documents': {p: b.decode() for p, b in r['members'].items() if p.startswith('.veldo/requests/')},
           'watermark': r['manifest']['watermark']}
except sn.Refused as e:
    out = {'refusal': e.code}
c.close()
print(json.dumps(out))
'''


def _v68_checks(base):
    rows = {name: [] for name in _V68_ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """Criterion sections: an exception is recorded as a failure of each named row and the run goes
        on, so every row reports even against code whose interface differs."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:200]), False)
            return True

    IA, RU, OW, OT, TM, RI, OP, UQ = _V68_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
        'control_assignment.py': ROOT / ".veldo" / "control_assignment.py",
    }
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    organs = base / 'installed'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v68_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        target = organs / name
        if target.exists():
            target.unlink()
        if _v68_Path(source).is_file():
            _v68_shutil.copyfile(source, target)
    here = (organs / 'control_request_settlement.py').is_file()

    with section(IA):
        scaffold = _v68_load('v68_scaffold', scaffold_path)
        rel = '.veldo/control_request_settlement.py'
        both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
        check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
        check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
        check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
        if both:
            scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
        check(IA, rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
              and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())

    claims = _v68_load('v68_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = _v68_load('v68_keys', organs / 'control_keys.py')
    I = _v68_load('v68_inbox', organs / 'control_assignment.py')
    P = _v68_load('v68_projection', organs / 'control_channel_projection.py')
    V = _v68_load('v68_presentation', organs / 'control_channel_presentation.py')
    EV = _v68_load('v68_attribution', organs / 'control_channel_attribution.py')
    E = _v68_load('v68_enrollment', organs / 'control_channel_enrollment.py')
    A = _v68_load('v68_answers', organs / 'control_signer_answers.py')
    RS = _v68_load('v68_readset', organs / 'control_readset.py')
    contract = _v68_load('v68_contract', organs / 'entity_contract.py')
    _git_process = _v68_load('v68_git', organs / 'git_process.py')
    ST = _v68_load('v68_settlement', organs / 'control_request_settlement.py') if here else None

    keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
    for directory in (keys, protected, edge_dir):
        directory.mkdir()
    keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'owner2', 'pm', 'api-edge')}
    keyfile['edge'] = protected / 'edge-telegram'
    keyfile['edge-auth'] = edge_dir / 'edge-auth'
    public = {}
    for who, path in keyfile.items():
        _v68_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v68-' + who, '-f', str(path)],
                    check=True, capture_output=True, timeout=10)
        public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

    def sign_as(who, message, namespace='veldo-command'):
        return _v68_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                           capture_output=True, check=True, timeout=10).stdout.decode()

    serial = [0]
    serial_lock = _v68_threading.Lock()

    def next_id(prefix):
        with serial_lock:
            serial[0] += 1
            return '%s-%d' % (prefix, serial[0])

    def verifies(principal, public_key, message, signature, namespace='veldo-command'):
        """An independent ssh-keygen verification, in a fresh directory of its own."""
        place = base / next_id('verify')
        place.mkdir()
        (place / 'allowed').write_text('%s namespaces="%s" %s\n' % (principal, namespace, public_key))
        (place / 'signature').write_text(signature if isinstance(signature, str) else '')
        done = _v68_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(place / 'allowed'), '-I', principal, '-n', namespace,
                            '-s', str(place / 'signature')], input=message, capture_output=True, timeout=10)
        return done.returncode == 0

    def canonical(value):
        return _v68_json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')

    def spelled_digest(value):
        return 'sha256:' + _v68_hashlib.sha256(canonical(value)).hexdigest()

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    ids = dict(domain_uuid='settle-domain', repository_uuid='settle-repository', store_uuid='settle-store')
    (base / 'authority').mkdir()
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    CM.attach(S)
    K.attach(S)
    repository = base / 'repository'
    repository.mkdir()
    projection = repository / '.veldo' / 'keys' / 'allowed_signers'
    config_path = base / 'authority' / 'signer.json'
    config_path.write_text(_v68_json.dumps({'store': str(db), 'repository': str(repository),
                                            'allowed_signers': str(projection), 'key_directory': str(protected),
                                            'authority_ids': ids}))

    def state():
        return CM.authority_state(S, conn)

    def envelope(command, principal):
        now = state()
        return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                    request_revision=1, nonce='nonce-' + command['command_id'], expires_at=_v68_time.time() + 600,
                    membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                    command_digest=AC.canonical_command_digest(command))

    def admin(principal, operation, params, enrollee=None):
        """One membership organ command, signed by `principal` (and co-signed by an enrollee)."""
        command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, principal)
        signature = sign_as(principal, AC.canonical_envelope_bytes(env))
        cosigned = sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal']))) if enrollee else None
        result = CM.admit(S, conn, env, command, signature, ids, _v68_time.time(), enrollee_signature=cosigned,
                          journal_signer=('authority', journal_sign))
        K.publish(S, conn, projection)
        return result

    def enroll_member(who, principal_type, roles, scope):
        admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                              'public_key': public[who], 'independence_group': who, 'scope': scope},
              enrollee=who)

    admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                          'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                          'independence_group': 'steward', 'scope': '*'})
    enroll_member('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority', 'technical_authority'],
                  ['project-a'])
    enroll_member('owner2', 'person', ['project_owner'], ['project-a'])
    enroll_member('pm', 'service', [], ['project-a'])
    enroll_member('api-edge', 'service', [], ['project-a'])

    def fixture(eid, kind, data):
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

    chats = {'owner': 5580001, 'owner2': 5580002}
    # VELDO-0064 chat enrollments, spelled here: each person's own private chat with the bot.
    for who, chat in chats.items():
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))
    # The VELDO-0067 edge: the steward's signed enrollment with the edge key's own possession proof.
    enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
    edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                   'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['project-a']}
    edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge', 'target': 'channel:telegram_chat',
                    'parameters': edge_params, 'artifact_digests': [], 'expected_versions': {}}
    edge_env = envelope(edge_command, 'steward')
    enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                     sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))
    now = _v68_time.time()
    for who in ('owner', 'owner2'):
        admin(who, 'grant_delegation', {'id': 'delegation-' + who, 'principal': who, 'channel': 'telegram_chat',
                                        'assertion_kinds': ['decision_answer', 'review_disposition'],
                                        'authority_scope': ['project-a'], 'request_version': 1, 'presentation_version': 1,
                                        'expires_at': now + 1800, 'edge_key_id': 'edge-telegram'})

    api = {'tick': 0, 'bots': {}, 'chats': {}, 'lock': _v68_threading.Lock()}
    handler = type('V68Handler', (_V68BotApi,), {'state': api})
    server = _v68_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v68_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:%d' % server.server_address[1]
    api['bots']['bot68'] = {'user': {'id': 8000000068, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_settle_bot'},
                            'next': 9000, 'update_next': 710000000, 'messages': {}, 'updates': []}
    bot = api['bots']['bot68']
    people = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize()} for who, chat in chats.items()}
    for person in people.values():
        api['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}

    def services(connection):
        """The inbox, presenter and settlement service of one connection to the authority store."""
        inbox_ = I.Inbox(S, CM, claims, contract, connection, ids, 'authority', journal_sign)
        presenter_ = V.Presenter(S, CM, P, inbox_, V.TelegramPresentationEdge(P, url, 'bot68'), connection, 'authority',
                                 journal_sign, assignment=I)
        service_ = (ST.Settlement(S, CM, inbox_, presenter_, connection, 'authority', journal_sign, assignment=I,
                                  presentation=V, api_edge='api-edge') if ST is not None else None)
        return inbox_, presenter_, service_

    inbox, presenter, service = services(conn)
    adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth'])
    acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot68'), conn, 'authority',
                           journal_sign, 'telegram-edge', adapter)
    missing = {'outcome': 'refused', 'reason': 'no_settlement_service'}

    def signed_command(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    def record_terms(name, touchpoint, required_roles=(), quorum=None, requester='pm', proposal=None):
        """The requester's signed terms: the subject the request is opened with."""
        target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % name, 'digest': spelled_digest(name)}
        body = dict(ids, operation='terms', terms=name, principal=requester, command_id=next_id('terms'),
                    nonce=next_id('terms-nonce'), touchpoint=touchpoint, target=target, proposal=proposal,
                    required_roles=list(required_roles), quorum=quorum)
        got = service.terms(signed_command(requester, body)) if service is not None else missing
        subject = got.get('subject') or {'kind': 'settlement_terms', 'ref': 'settlement-terms:%s:%s' % (
            ids['repository_uuid'], name), 'digest': spelled_digest(body)}
        return subject, target, got

    def open_request(alias, touchpoint, owner='owner', requester='pm', required_roles=(), quorum=None, proposal=None):
        """Terms, the inbox request, its framing and its presentation: (request id, receipt, target)."""
        subject, target, _ = record_terms(alias, touchpoint, required_roles, quorum, requester, proposal)
        kind = ST.JOURNEY[touchpoint]['assignment_kind'] if ST is not None else (
            'review_disposition' if touchpoint == 'finding_disposition' else 'decision')
        inbox.apply(signed_command(requester, dict(ids, operation='open', alias=alias, principal=requester,
                                                   command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                       kind=kind, owner=owner, scope=['project-a'],
                                                       deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                       brief='Settle %s for %s.' % (touchpoint, alias),
                                                       choices=list(_V68_CHOICES), subject=subject))))
        rid = I.assignment_id(ids['repository_uuid'], alias)
        frame(alias, requester, 1)
        presenter.present(rid)
        return rid, presenter.current(rid) or {}, target

    def frame(alias, requester, version):
        presenter.frame(signed_command(requester, dict(ids, operation='frame', alias=alias, principal=requester,
                                                       request_version=version,
                                                       risk_statement='Low: a wrong choice costs one review cycle.',
                                                       command_id=next_id('f'), nonce=next_id('fn'))))

    def revise(alias, requester='pm'):
        rid = I.assignment_id(ids['repository_uuid'], alias)
        inbox.apply(signed_command(requester, dict(ids, operation='revise', alias=alias, principal=requester,
                                                   command_id=next_id('c'), nonce=next_id('n'), request_version=1,
                                                   changes={'brief': 'Revised brief for %s.' % alias})))
        frame(alias, requester, 2)
        presenter.present(rid)
        return presenter.current(rid) or {}

    def reply(receipt, text, who='owner'):
        sender = people[who]
        chat = api['chats'][sender['id']]
        with api['lock']:
            bot['update_next'] += 1
            update_id = bot['update_next']
        update = {'update_id': update_id,
                  'message': _v68_message(api, bot, sender, chat, text, (receipt.get('message_ids') or [None])[-1])}
        bot['updates'].append(update)
        return update

    def acquire():
        return {r['update_id']: (r.get('outcome'), r.get('reason')) for r in acquirer.acquire()
                if r.get('update_id') is not None}

    def run_settlement():
        return service.run() if service is not None else []

    def settle(rid):
        return service.settle(rid) if service is not None else dict(missing, request_id=rid)

    def api_packet(receipt, choice, rationale, principal='owner', answer=None, signer='api-edge', version=None):
        body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=answer or next_id('api'),
                    principal=principal, request_id=receipt.get('request_id'),
                    request_version=receipt.get('request_version') if version is None else version,
                    presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                    presentation_version=receipt.get('presentation_version'), choice=choice, rationale=rationale)
        return {'answer': body, 'signature': sign_as(signer, S.canonical_bytes(body))}

    def api_answer(packet, on=None):
        on = on or service
        return on.api_answer(packet) if on is not None else missing

    def entity(eid):
        row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': _v68_json.loads(row[2])}

    def of_kind(kind, request=None):
        found = []
        for eid, text in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (kind,)):
            data = _v68_json.loads(text)
            if request is None or data.get('request_id') == request:
                found.append((eid, data))
        return found

    def settled(rid):
        """(settlements, effects, receipts) the store holds for one request."""
        return (of_kind('request_settlement', rid), of_kind('settlement_effect', rid), of_kind('settlement_receipt', rid))

    def request_data(rid):
        return (entity(rid) or {}).get('data') or {}

    def journal_count():
        return conn.execute('SELECT count(*) FROM journal').fetchone()[0]

    def unchanged(rid, before):
        """Nothing about the request's settlement changed: its settlements, effects, receipts, API
        evidence and its own record."""
        return snapshot_of(rid) == before

    def snapshot_of(rid):
        return (settled(rid), of_kind('settlement_api_answer', rid), entity(rid))

    def blocked(rid, reason, result):
        """Refused by name, the request still pending at its version, and nothing settled."""
        data = request_data(rid)
        s, e, r = settled(rid)
        return (result.get('outcome') == 'refused' and result.get('reason') == reason
                and data.get('state') in I.PENDING and not s and not e and not r)

    def seen(result):
        return ' [observed: %s, %s]' % (result.get('outcome'), result.get('reason'))

    def result_for(results, rid):
        return next((r for r in results if r.get('request_id') == rid), {})

    try:
        # The one authority: a settlement service on another connection than its inbox's is refused.
        with section(IA):
            other = S.open_store(str(db))
            try:
                refused_other = None
                if ST is not None:
                    try:
                        ST.Settlement(S, CM, inbox, presenter, other, 'authority', journal_sign, assignment=I,
                                      presentation=V, api_edge='api-edge')
                    except ST.Refused as exc:
                        refused_other = exc.code
                check(IA, 'a settlement service on a second connection, beside the inbox\'s, is refused (one authority)',
                      refused_other == 'invalid_input')
            finally:
                other.close()

        # AC1: every enabled touchpoint answered with every offered choice through real signed Telegram answers.
        with section(RU):
            journey = sorted(ST.JOURNEY) if ST is not None else []
            check(RU, 'the journey enables exactly the touchpoints the specification names', journey == sorted(_V68_NAMED))
            touchpoints = journey or list(_V68_NAMED)
            asked = {}
            for tp in touchpoints:
                for choice in _V68_CHOICES:
                    alias = 'T-%s-%s' % (tp, choice)
                    rid, receipt, target = open_request(alias, tp, proposal={'rank': 2} if tp == 'priority' else None)
                    reason = 'because %s should %s now' % (tp.replace('_', ' '), choice.replace('_', ' '))
                    update = reply(receipt, '%s: %s' % (choice.replace('_', ' ').upper() if tp == 'admission' else choice,
                                                        reason))
                    asked[(tp, choice)] = dict(rid=rid, receipt=receipt, target=target, reason=reason, update=update)
            acquired = acquire()
            results = run_settlement()
            for (tp, choice), a in sorted(asked.items()):
                label = '%s answered %s' % (tp, choice)
                ruling = _V68_CHOICES[choice]
                got = result_for(results, a['rid'])
                s, e, r = settled(a['rid'])
                sdata = s[0][1] if len(s) == 1 else {}
                edata = e[0][1] if len(e) == 1 else {}
                message = a['update']['message']
                answer = (entity(sdata.get('answer_id') or '') or {}).get('data') or {}
                source = answer.get('attribution') or {}
                check(RU, '%s: the presenter accepted the owner\'s signed Telegram reply' % label,
                      acquired.get(a['update']['update_id']) == ('answered', None))
                check(RU, '%s: settled once, from the Telegram answer' % label + ('' if got.get('outcome') == 'settled' else seen(got)),
                      got.get('outcome') == 'settled' and len(s) == 1 and sdata.get('originating_channel') == 'telegram_chat')
                check(RU, '%s: the settlement carries the offered choice, its ruling and the owner\'s own words' % label,
                      sdata.get('choice') == choice and sdata.get('ruling') == ruling and sdata.get('rationale') == a['reason']
                      and sdata.get('touchpoint') == tp and sdata.get('principals') == ['owner'])
                check(RU, '%s: the settlement is the platform message the owner sent: message, sender, chat, date and the '
                          'presentation it replies to' % label,
                      source.get('platform_message_id') == message['message_id'] and source.get('sender_id') == message['from']['id']
                      and source.get('chat_id') == message['chat']['id'] and source.get('platform_timestamp') == message['date']
                      and source.get('reply_to_message_id') in (a['receipt'].get('message_ids') or [])
                      and sdata.get('assertion', {}).get('attribution', {}).get('platform_message_id') == message['message_id']
                      and sdata.get('presentation_id') == a['receipt'].get('presentation_id')
                      and sdata.get('presentation_digest') == a['receipt'].get('brief_digest'))
                check(RU, '%s: the carried assertion is the edge\'s signed one' % label,
                      verifies('telegram-edge', public['edge'], canonical(sdata.get('assertion')), sdata.get('signature')))
                effects = (ST.JOURNEY.get(tp) or {}).get('effects', {}) if ST is not None else {}
                check(RU, '%s: one typed effect, the touchpoint\'s for that ruling, carrying the choice, ruling, reasoning, '
                          'target and (on approval only) the proposal' % label,
                      len(e) == 1 and edata.get('type') == effects.get(ruling) and edata.get('touchpoint') == tp
                      and edata.get('choice') == choice and edata.get('ruling') == ruling and edata.get('rationale') == a['reason']
                      and edata.get('target') == a['target'] and edata.get('settlement_id') == sdata.get('settlement_id')
                      and edata.get('proposal') == ({'rank': 2} if tp == 'priority' and ruling == 'approve' else None))
            types = {(tp, _V68_CHOICES[c]): (settled(a['rid'])[1] or [(None, {})])[0][1].get('type') for (tp, c), a in asked.items()}
            check(RU, 'every touchpoint and ruling has its own effect type', len(set(types.values())) == len(types) == 15
                  and None not in types.values())

        # AC2: two conflicting authenticated answers for one request version, sequential then concurrent.
        with section(OW, RI):
            c1, c1_receipt, _ = open_request('C1', 'grooming')
            u_c1 = reply(c1_receipt, 'accept: telegram answer first')
            first_c1 = acquire()
            got_c1 = api_answer(api_packet(c1_receipt, 'reject', 'api answer second', answer='c1-api'))
            s, e, r = settled(c1)
            sdata = s[0][1] if len(s) == 1 else {}
            listed = sdata.get('not_counted') or []
            api_id = 'settlement-api-answer:%s:1:api-edge:c1-api' % c1
        with section(OW):
            check(OW, 'both answers were accepted as evidence: the Telegram reply, then the API answer',
                  first_c1.get(u_c1['update_id']) == ('answered', None) and entity(api_id) is not None)
            check(OW, 'one settlement, one effect and one receipt for the request version' + seen(got_c1),
                  got_c1.get('outcome') == 'settled' and len(s) == 1 and len(e) == 1 and len(r) == 1)
            check(OW, 'the earliest answer wins: the Telegram accept, attributed to its channel, with an approving effect',
                  sdata.get('choice') == 'accept' and sdata.get('originating_channel') == 'telegram_chat'
                  and (e[0][1] if e else {}).get('ruling') == 'approve')
            check(OW, 'the conflicting API answer is listed, not counted and not settled',
                  [(x.get('answer_id'), x.get('reason')) for x in listed] == [(api_id, 'conflicting_ruling')])
            data = request_data(c1)
            check(OW, 'the terminal request state names this one settlement',
                  data.get('state') == 'SATISFIED' and data.get('settlement', {}).get('settlement_id') == sdata.get('settlement_id')
                  and data.get('settlement', {}).get('receipt_id') == (r[0][0] if r else None))
            before, count = snapshot_of(c1), journal_count()
            again = settle(c1)
            later = api_answer(api_packet(c1_receipt, 'reject', 'api answer third', answer='c1-api-late'))
            check(OW, 'settling the version again, and a later API answer, are refused by name and write nothing',
                  again.get('reason') == 'already_settled' and later.get('reason') == 'request_closed'
                  and unchanged(c1, before) and journal_count() == count)

            c2, c2_receipt, _ = open_request('C2', 'grooming')
            packets = {'race-a': api_packet(c2_receipt, 'accept', 'race answer a', answer='race-a'),
                       'race-b': api_packet(c2_receipt, 'reject', 'race answer b', answer='race-b')}
            barrier = _v68_threading.Barrier(2)
            outcomes, timings = {}, {}
            race_started = _v68_time.monotonic()

            def racer(name):
                connection = S.open_store(str(db))
                try:
                    _i, _p, own = services(connection)
                    timings[name] = ['ready %.3f' % (_v68_time.monotonic() - race_started)]
                    barrier.wait(timeout=30)
                    timings[name].append('go %.3f' % (_v68_time.monotonic() - race_started))
                    outcomes[name] = api_answer(packets[name], own) if own is not None else missing
                except Exception as exc:  # noqa: BLE001 - a racer that raised is recorded, never silent
                    outcomes[name] = {'outcome': 'raised', 'reason': '%s: %s' % (type(exc).__name__, str(exc)[:160])}
                finally:
                    timings.setdefault(name, []).append('done %.3f' % (_v68_time.monotonic() - race_started))
                    connection.close()

            racers = [_v68_threading.Thread(target=racer, args=(name,)) for name in packets]
            for t in racers:
                t.start()
            for t in racers:
                t.join(timeout=60)
            s, e, r = settled(c2)
            sdata = s[0][1] if len(s) == 1 else {}
            winners = [n for n, o in outcomes.items() if o.get('outcome') == 'settled']
            losers = [o for n, o in outcomes.items() if n not in winners]
            won = (entity(sdata.get('answer_id') or '') or {}).get('data') or {}
            data = request_data(c2)
            # What the race saw, carried on each race check so a false row names it (never a rationale
            # or a signature): each racer's outcome, reason and recorded answer, its timings, the
            # settlements, effects and receipts, the winning answer, the listed ones and the request state.
            race_seen = (' [observed: racers %s; timings %s; alive %s; settlements %s answering %s choice %s; '
                         'not_counted %s; effects %s receipts %s; api answers %s; request state %s version %s]') % (
                _v68_json.dumps({n: {k: o.get(k) for k in ('outcome', 'reason', 'answer')} for n, o in sorted(outcomes.items())}),
                _v68_json.dumps(timings, sort_keys=True), [t.is_alive() for t in racers], len(s), sdata.get('answer_id'),
                sdata.get('choice'), [(x.get('answer_id'), x.get('reason')) for x in sdata.get('not_counted') or []],
                len(e), len(r), [eid for eid, _d in of_kind('settlement_api_answer', c2)], data.get('state'),
                data.get('request_version'))
            check(OW, 'two concurrent API answers on two connections: exactly one settles%s' % race_seen,
                  len(winners) == 1 and len(s) == 1 and len(e) == 1 and len(r) == 1)
            check(OW, 'the other is refused by name and no second settlement exists%s' % race_seen,
                  len(losers) == 1 and losers[0].get('outcome') == 'refused'
                  and losers[0].get('reason') in ('already_settled', 'request_closed', 'stale_subject', 'unavailable_service'))
            # The call that commits the settlement is not always the answer that wins it: when both answers
            # are recorded before either settles, the settling call counts the EARLIEST accepted answer,
            # which may be the other racer's, and lists its own as not counted. Every id below is an
            # evidence entity id (the settlement's answer_id, the racers' recorded answers, not_counted).
            recorded = {eid: d for eid, d in of_kind('settlement_api_answer', c2)}
            race_answers = {o.get('answer') for o in outcomes.values() if o.get('answer')}
            winning = sdata.get('answer_id')
            own = (outcomes.get(winners[0]) or {}).get('answer') if len(winners) == 1 else None
            listed_ids = [x.get('answer_id') for x in sdata.get('not_counted') or []]
            order = lambda eid: ((recorded.get(eid) or {}).get('accepted_at') or 0, eid)
            check(OW, 'the winning answer is the earliest accepted race answer; every other one the settlement read '
                      'is listed once as not counted (conflicting_ruling), and the settling call\'s own answer, when '
                      'it did not win, is among them' + race_seen,
                  winning in race_answers and winning in recorded and winning not in listed_ids
                  and len(set(listed_ids)) == len(listed_ids) and set(listed_ids) <= race_answers
                  and all(x.get('reason') == 'conflicting_ruling' for x in sdata.get('not_counted') or [])
                  and all(order(winning) < order(x) for x in listed_ids)
                  and (own == winning or own in listed_ids))
            check(OW, 'the settlement is one consistent result: its winning answer, ruling, effect, receipt and '
                      'terminal state agree' + race_seen,
                  won.get('choice') == sdata.get('choice') and winning in race_answers
                  and (e[0][1] if e else {}).get('ruling') == sdata.get('ruling') == _V68_CHOICES.get(sdata.get('choice'))
                  and (r[0][1] if r else {}).get('settlement_id') == sdata.get('settlement_id')
                  and data.get('state') == 'SATISFIED' and data.get('answer', {}).get('ruling') == sdata.get('choice')
                  and data.get('settlement', {}).get('settlement_id') == sdata.get('settlement_id'))

        # AC2: the ruling, the nonce, the effect, the terminal state and the receipt in one transaction.
        with section(OT):
            # The VELDO-0064 answer command never settles a request with terms: it is refused by name and
            # writes nothing, and the owner's Telegram answer then settles it in the one transaction.
            direct, direct_receipt, _ = open_request('OT-direct', 'grooming')
            before_direct, journal_before = snapshot_of(direct), journal_count()
            bypass = inbox.apply(signed_command('owner', dict(ids, operation='answer', alias='OT-direct', principal='owner',
                                                              command_id=next_id('c'), nonce=next_id('n'),
                                                              request_version=1, ruling='accept')))
            check(OT, 'the VELDO-0064 answer command on a request with settlement terms is refused '
                      '(settlement_required) and writes nothing [observed: %s, %s]' % (bypass.get('ok'), bypass.get('reason')),
                  bypass.get('ok') is False and bypass.get('reason') == 'settlement_required'
                  and unchanged(direct, before_direct) and journal_count() == journal_before
                  and request_data(direct).get('state') in I.PENDING)
            before_decline, journal_before = snapshot_of(direct), journal_count()
            declined = inbox.apply(signed_command('owner', dict(ids, operation='decline', alias='OT-direct', principal='owner',
                                                                command_id=next_id('c'), nonce=next_id('n'),
                                                                request_version=1, ruling='decline')))
            check(OT, 'the VELDO-0064 decline command on a request with settlement terms is refused '
                      '(settlement_required) and writes nothing [observed: %s, %s]' % (declined.get('ok'), declined.get('reason')),
                  declined.get('ok') is False and declined.get('reason') == 'settlement_required'
                  and unchanged(direct, before_decline) and journal_count() == journal_before
                  and request_data(direct).get('state') in I.PENDING)
            reply(direct_receipt, 'accept: settled through the service once the direct answer was refused')
            acquire()
            got_direct = settle(direct)
            s_d, e_d, r_d = settled(direct)
            check(OT, 'the owner\'s Telegram answer then settles it: one settlement, effect and receipt, and the '
                      'request terminal' + seen(got_direct),
                  got_direct.get('outcome') == 'settled' and len(s_d) == len(e_d) == len(r_d) == 1
                  and request_data(direct).get('state') == 'SATISFIED')
            rows_ = [(seq, cid, nonce, _v68_json.loads(t)) for seq, cid, nonce, t in
                     conn.execute('SELECT seq, command_id, nonce, transition FROM journal ORDER BY seq')]
            nonces = dict(conn.execute('SELECT nonce, command_id FROM nonces').fetchall())
            everything = of_kind('request_settlement')
            check(OT, 'every settled request was observed (the touchpoints, both conflicts and the controls)', len(everything) >= 17)
            for sid, sdata in everything:
                rid = sdata.get('request_id')
                eid, rec = sdata.get('effect_id'), sdata.get('receipt_id')
                touching = [x for x in rows_ if set(x[3]) & {sid, eid, rec}]
                one = touching[0] if len(touching) == 1 else (None, None, None, {})
                transition = one[3]
                terminal = (transition.get(rid) or {}).get('data') or {}
                receipt = (entity(rec or '') or {}).get('data') or {}
                label = rid.split(':')[-1] if isinstance(rid, str) else '?'
                check(OT, '%s: one journal record wrote the settlement, the effect, the receipt and the terminal request '
                          'state together' % label,
                      len(touching) == 1 and {sid, eid, rec, rid} <= set(transition)
                      and terminal.get('state') == 'SATISFIED'
                      and terminal.get('settlement', {}).get('receipt_id') == rec)
                check(OT, '%s: that record consumed the settlement\'s own nonce (the request version)' % label,
                      one[2] == sid and nonces.get(sid) == one[1] and sid.endswith(':%s' % sdata.get('request_version')))
                check(OT, '%s: the receipt binds the settlement it was committed with and its one effect' % label,
                      receipt.get('settlement_digest') == spelled_digest(sdata) and receipt.get('effect_ids') == [eid]
                      and receipt.get('terminal_state') == 'SATISFIED' and receipt.get('nonce') == sid)
                answered = [x[0] for x in rows_ if sdata.get('answer_id') in x[3]]
                check(OT, '%s: the counted answer is evidence committed before the settlement' % label,
                      bool(answered) and max(answered) < (one[0] or 0))
                check(OT, '%s: no later record changed the terminal request state' % label,
                      one[0] is not None and all(rid not in x[3] for x in rows_ if x[0] > one[0]))

        # AC3: terminal request state, materialized with its exact settlement, and nothing reapplied.
        with section(TM):
            accepted_a = asked[('grooming', 'accept')]
            rejected_r = asked[('grooming', 'reject')]
            for label, a, ruling in (('accepted', accepted_a, 'approve'), ('rejected', rejected_r, 'reject')):
                data = request_data(a['rid'])
                s, e, r = settled(a['rid'])
                entry = next((x for x in inbox.index()['entries'] if x['id'] == a['rid']), {})
                check(TM, 'the %s request is terminal in the inbox with its exact settlement and receipt' % label,
                      entry.get('category') == 'answered' and entry.get('state') == 'SATISFIED'
                      and len(s) == 1 and data.get('settlement', {}).get('settlement_id') == s[0][0]
                      and data.get('settlement', {}).get('receipt_id') == (r[0][0] if r else None)
                      and data.get('settlement', {}).get('ruling') == ruling and data.get('request_version') == 1)
            published_repo = base / 'published-repo'
            (published_repo / '.veldo' / 'requests').mkdir(parents=True)
            documents = {}
            for a in (accepted_a, rejected_r):
                alias = a['rid'].split(':')[-1]
                path = '.veldo/requests/%s.yaml' % alias
                # The stale repository record: it still says open, as it did before the owner answered.
                body = ('schema: veldo.request/v1\nid: %s\nstatus: open\n' % alias).encode()
                (published_repo / path).write_bytes(body)
                documents[path] = 'sha256:' + _v68_hashlib.sha256(body).hexdigest()

            def git(*args):
                return _git_process.run(['git', '-C', str(published_repo), *args], check=True, capture_output=True,
                                        text=True, identity=('Owner', 'owner@example.invalid')).stdout.strip()

            _git_process.run(['git', 'init', '-q', str(published_repo)], check=True, capture_output=True)
            git('add', '-A')
            git('commit', '-q', '-m', 'Request records as the repository holds them')
            commit = git('rev-parse', 'HEAD')
            publication = S.open_store(str(db))
            destination = base / 'published'
            try:
                if service is not None:
                    revisions = RS.attach_revisions(S, publication, ids['domain_uuid'], {ids['repository_uuid']: str(published_repo)})
                    reader = RS.attach(S, publication, published_repo, ids['domain_uuid'], ids['repository_uuid'])
                    service.publish(revisions, reader, 'settlement-revision', commit, documents, 'settlement-snapshot-1',
                                    destination, 'authority')
            finally:
                publication.close()
            aliases = [a['rid'].split(':')[-1] for a in (accepted_a, rejected_r)]
            child = _v68_sp.run([_v68_sys.executable, '-B', '-c', _V68_CHILD, str(organs), str(db), str(published_repo),
                                 str(destination), 'settlement-snapshot-1', ids['domain_uuid'], ids['repository_uuid'],
                                 *aliases], capture_output=True, text=True, timeout=30)
            read = _v68_json.loads(child.stdout or '{}') if child.returncode == 0 else {}
            for label, a, ruling, alias in (('accepted', accepted_a, 'approve', aliases[0]),
                                            ('rejected', rejected_r, 'reject', aliases[1])):
                s, _e, r = settled(a['rid'])
                got = (read.get('requests') or {}).get(alias) or {}
                check(TM, 'another process reads the published snapshot: the %s request is terminal at version 1 with '
                          'its exact settlement, settlement version and receipt' % label,
                      got.get('settled') is True and got.get('state') == 'SATISFIED' and got.get('request_version') == 1
                      and got.get('settlement_id') == (s[0][0] if s else None) and got.get('settlement_version') == 1
                      and got.get('receipt_id') == (r[0][0] if r else None) and got.get('ruling') == ruling)
                check(TM, 'the %s request\'s stale repository record still says open and decides nothing' % label,
                      'status: open' in ((read.get('documents') or {}).get('.veldo/requests/%s.yaml' % alias) or ''))
            before = {a['rid']: snapshot_of(a['rid']) for a in (accepted_a, rejected_r)}
            u_late = reply(accepted_a['receipt'], 'reject: changed my mind')
            late = acquire()
            late_api = api_answer(api_packet(rejected_r['receipt'], 'accept', 'api after settlement', answer='late-api'))
            rerun = run_settlement()
            check(TM, 'another ordinary Telegram answer to the settled request is refused: its version is answered '
                      '(already_answered) %s' % (late.get(u_late['update_id']),),
                  late.get(u_late['update_id']) == ('refused', 'already_answered'))
            check(TM, 'an API answer to the settled request is refused as closed', late_api.get('reason') == 'request_closed')
            check(TM, 'nothing was reapplied: no settlement, effect, receipt or evidence changed, and settling again '
                      'touches neither request',
                  all(unchanged(rid, b) for rid, b in before.items())
                  and not [x for x in rerun if x.get('request_id') in before])

        # AC4: the journey's role and independence predicates and the request's own, conjunctively.
        with section(RI):
            blocked_cases = {}
            for alias, touchpoint, owner, requester, roles, text in (
                    ('R-strong-accept', 'grooming', 'owner', 'pm', ['security_authority'], 'accept: stronger role wanted'),
                    ('R-strong-reject', 'grooming', 'owner', 'pm', ['security_authority'], 'reject: stronger role wanted'),
                    ('R-policy', 'admission', 'owner2', 'pm', [], 'accept: admitted without the role'),
                    ('R-self', 'grooming', 'owner', 'owner', [], 'accept: my own request')):
                rid, receipt, _ = open_request(alias, touchpoint, owner=owner, requester=requester, required_roles=roles)
                blocked_cases[alias] = (rid, reply(receipt, text, who=owner))
            valid_cases = {}
            for alias, text in (('R-valid-accept', 'accept: role held'), ('R-valid-reject', 'reject: role held')):
                rid, receipt, _ = open_request(alias, 'grooming', required_roles=['technical_authority'])
                valid_cases[alias] = (rid, reply(receipt, text))
            dup, dup_receipt, _ = open_request('R-duplicate', 'grooming')
            reply(dup_receipt, 'accept: on telegram')
            acquired = acquire()
            # The owner's second answer, on the API, before the settlement pass: both are evidence at once.
            dup_result = api_answer(api_packet(dup_receipt, 'accept', 'and on the api', answer='dup-api'))
            results = run_settlement()
            for alias, reason in (('R-strong-accept', 'role_not_satisfied'), ('R-strong-reject', 'role_not_satisfied'),
                                  ('R-policy', 'role_not_satisfied'), ('R-self', 'independence_not_met')):
                rid, update = blocked_cases[alias]
                got = result_for(results, rid)
                check(RI, '%s: the answer is accepted evidence, and settlement blocks by name (%s)' % (alias, reason)
                      + ('' if blocked(rid, reason, got) else seen(got)),
                      acquired.get(update['update_id']) == ('answered', None) and blocked(rid, reason, got))
            for alias, ruling in (('R-valid-accept', 'approve'), ('R-valid-reject', 'reject')):
                rid, update = valid_cases[alias]
                s, _e, _r = settled(rid)
                got = result_for(results, rid)
                check(RI, '%s: policy and request roles both held, so it settles (%s)' % (alias, ruling) + seen(got),
                      got.get('outcome') == 'settled' and len(s) == 1 and s[0][1].get('ruling') == ruling
                      and s[0][1].get('requirement', {}).get('roles') == ['project_owner', 'technical_authority'])
            s, _e, _r = settled(dup)
            listed = (s[0][1] if s else {}).get('not_counted') or []
            check(RI, 'one principal on two surfaces is one principal: settled once, the second answer a duplicate'
                  + seen(dup_result),
                  dup_result.get('outcome') == 'settled' and len(s) == 1 and s[0][1].get('principals') == ['owner']
                  and [x.get('reason') for x in listed] == ['duplicate_principal'])
            requirement = (settled(c1)[0] or [(None, {})])[0][1].get('requirement') or {}
            check(RI, 'the counted requirement is the journey\'s own grooming predicate (role, count, independence)',
                  ST is not None and requirement == {'roles': sorted(ST.JOURNEY['grooming']['roles']),
                                                     'count': ST.JOURNEY['grooming']['quorum']['count'],
                                                     'min_independence': ST.JOURNEY['grooming']['quorum']['min_independence']})

        # AC4: the wrong owner, a forged API edge and a stale presentation settle nothing.
        with section(OP):
            o1, o1_receipt, _ = open_request('O-wrong', 'grooming')
            before = snapshot_of(o1)
            wrong = api_answer(api_packet(o1_receipt, 'accept', 'not my request', principal='owner2'))
            forged = api_answer(api_packet(o1_receipt, 'accept', 'forged edge', signer='owner2'))
            check(OP, 'an API answer by a current person who is not the owner is refused (not_owner) and writes nothing'
                  + seen(wrong), wrong.get('reason') == 'not_owner' and unchanged(o1, before))
            check(OP, 'an API answer not signed by the API edge\'s key is refused (not_authorized) and writes nothing'
                  + seen(forged), forged.get('reason') == 'not_authorized' and unchanged(o1, before))
            o2, o2_first, _ = open_request('O-stale', 'grooming')
            o2_second = revise('O-stale')
            before = snapshot_of(o2)
            stale = api_answer(api_packet(o2_first, 'accept', 'answering what I saw first'))
            stale_now = api_answer(api_packet(o2_first, 'accept', 'the old presentation at the new version', version=2))
            check(OP, 'an API answer to the superseded presentation is refused (stale_presentation) and writes nothing'
                  + seen(stale) + seen(stale_now),
                  o2_second.get('presentation_version') == 2 and stale.get('reason') == 'stale_presentation'
                  and stale_now.get('reason') == 'stale_presentation' and unchanged(o2, before))
            current = api_answer(api_packet(o2_second, 'accept', 'answering the current presentation'))
            s, _e, _r = settled(o2)
            check(OP, 'control: the owner\'s API answer to the current presentation settles version 2' + seen(current),
                  current.get('outcome') == 'settled' and len(s) == 1 and s[0][1].get('request_version') == 2
                  and s[0][1].get('originating_channel') == 'api' and s[0][1].get('presentation_id') == o2_second.get('presentation_id'))
            o3, o3_receipt, _ = open_request('O-revised', 'grooming')
            u3 = reply(o3_receipt, 'accept: answered version one')
            answered_v1 = acquire()
            revise('O-revised')
            rerun = run_settlement()
            again = settle(o3)
            s, _e, _r = settled(o3)
            check(OP, 'an answer accepted at version 1 settles nothing once the request is revised to version 2'
                  + seen(again),
                  answered_v1.get(u3['update_id']) == ('answered', None) and not s
                  and not [x for x in rerun if x.get('request_id') == o3] and again.get('reason') == 'no_answer'
                  and request_data(o3).get('request_version') == 2 and request_data(o3).get('state') in I.PENDING)

        # AC4: an unsupported quorum policy blocks; it is never weakened to what one owner can meet.
        with section(UQ):
            derived = {}
            if ST is not None:
                for tp, config in ST.JOURNEY.items():
                    try:
                        derived[tp] = ST.requirement(tp, {'required_roles': [], 'quorum': None})
                    except ST.Refused as exc:
                        derived[tp] = exc.code
            check(UQ, 'every touchpoint\'s own predicate is derived from the journey configuration and is settleable',
                  ST is not None and len(derived) == 5 and all(
                      derived[tp] == {'roles': sorted(c['roles']), 'count': c['quorum']['count'],
                                      'min_independence': c['quorum']['min_independence']} for tp, c in ST.JOURNEY.items()))
            quorum_cases = {}
            for alias, quorum in (('Q-two', {'count': 2, 'min_independence': 1}), ('Q-independence', {'count': 1, 'min_independence': 2}),
                                  ('Q-shape', {'count': 1, 'weight': 3}), ('Q-ok', {'count': 1, 'min_independence': 1})):
                rid, receipt, _ = open_request(alias, 'grooming', quorum=quorum)
                quorum_cases[alias] = (rid, reply(receipt, 'accept: quorum %s' % alias))
            acquired = acquire()
            results = run_settlement()
            for alias in ('Q-two', 'Q-independence', 'Q-shape'):
                rid, update = quorum_cases[alias]
                got = result_for(results, rid)
                check(UQ, '%s: the owner\'s answer is accepted and settlement blocks as unsupported_quorum' % alias + seen(got),
                      acquired.get(update['update_id']) == ('answered', None) and blocked(rid, 'unsupported_quorum', got))
            rid, _update = quorum_cases['Q-ok']
            got = result_for(results, rid)
            check(UQ, 'control: a request asking the journey\'s own quorum settles' + seen(got), got.get('outcome') == 'settled')
            metrics = service.metrics() if service is not None else {}
            check(UQ, 'metrics: accepted and refused counts, settled versions and the blocked pending work by reason',
                  metrics.get('pending_by_reason', {}).get('unsupported_quorum') == 3
                  and metrics.get('pending_by_reason', {}).get('role_not_satisfied') == 3
                  and metrics.get('pending_by_reason', {}).get('independence_not_met') == 1
                  and metrics.get('settled') == len(of_kind('request_settlement')) and metrics.get('accepted', 0) > 0
                  and metrics.get('refused', 0) > 0)
            observed = service.observations if service is not None else []
            text = _v68_json.dumps(observed)
            classes = {'invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence'}
            check(UQ, 'observations name operation, authority, request, versions, outcome and refusal class, never '
                      'reasoning or signatures',
                  bool(observed) and all(o.get('repository_uuid') == ids['repository_uuid'] and 'accepted_versions' in o
                                         and o.get('operation') for o in observed)
                  and all(o['error_class'] in classes for o in observed if o['outcome'] == 'refused')
                  and 'quorum Q-two' not in text and 'telegram answer first' not in text and 'SSH SIGNATURE' not in text)
    finally:
        server.shutdown()
        server.server_close()
        conn.close()
    return rows


_v68_started = _v68_time.monotonic()
# The store and keys live in memory-backed /dev/shm when it exists and is writable (Linux), as the
# other store suites do; elsewhere the platform's temporary directory is used.
_v68_fast = '/dev/shm' if _v68_os.path.isdir('/dev/shm') and _v68_os.access('/dev/shm', _v68_os.W_OK) else None
with _v68_temp.TemporaryDirectory(prefix='v68-', dir=_v68_fast) as _v68_dir:
    _v68_rows = _v68_checks(_v68_Path(_v68_dir))
for _v68_name, _v68_observed in _v68_rows.items():
    _v68_ok = bool(_v68_observed) and all(ok for _, ok in _v68_observed)
    # A false row carries its false checks after the colon, where the mutation worker keeps a false
    # row's detail (failed_details); a true row keeps its bare name.
    expect('VELDO-0068 ' + _v68_name + ('' if _v68_ok else ': ' + ('; '.join(
        label for label, one in _v68_observed if not one) or 'no check observed')), _v68_ok)
print('VELDO-0068 suite seconds: %.3f' % (_v68_time.monotonic() - _v68_started))
