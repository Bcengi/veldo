"""VELDO-0067: the restricted Telegram edge key enrolled under current authority, the protected signer's
answer purpose, and current edge and actor authorization at answer acceptance, over a real signed store.

Run: python3 scripts/selftest.py --suite 65_veldo_0067_edges

Every administrative command is a real OpenSSH-envelope Ed25519 signed command, through the membership
organ or the enrollment organ, and every journal record is signed. Every answer signature is made by the
actual protected signer process from the protected key directory, asked by the actual VELDO-0066
Acquirer over a loopback Bot API (real HTTP in the platform's documented shapes; not the Telegram
service, no network, no real token), and every acceptance is the actual VELDO-0065 presenter. The worker
read is a real process under the custody wrapper. Mutation workers replace the production copies named
in PRODUCTION below, never assertions or fixtures. Where a module is absent (the pre-change tree, for
the red record) the rows drive the path that tree has: the VELDO-0027 signing-key registration and
retirement, the protected signer as it stood, and a worker started without a wrapper, so every row
fails by its own assertions rather than by an exception. No private key byte, public key blob or
signature is printed or retained.
"""
import copy as _v67_copy
import errno as _v67_errno
import http.server as _v67_http
import importlib.util as _v67_import
import json as _v67_json
import os as _v67_os
from pathlib import Path as _v67_Path
import shutil as _v67_shutil
import subprocess as _v67_sp
import sys as _v67_sys
import tempfile as _v67_temp
import threading as _v67_threading
import time as _v67_time

_V67_ROWS = ('install/assets', 'enrollment/schema-and-possession', 'enrollment/binds-key-and-authority',
             'enrollment/current-member-only', 'signer/purpose-refusal', 'signer/delegation-dimensions',
             'signer/canonical-evidence', 'acceptance/current-edge-and-actor', 'custody/worker-cannot-read-key')


def _v67_load(name, path):
    spec = _v67_import.spec_from_file_location(name, path)
    module = _v67_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v67_message(st, bot, sender, chat, text, reply_to=None):
    """One message as the platform keeps and delivers it: its id numbered per bot, the platform's date,
    the sender's User, the chat, the text and, for a reply, the replied message as the platform holds it."""
    bot['next'] += 1
    st['tick'] += 1
    message = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
               'text': text}
    if reply_to is not None:
        held = bot['messages'][(chat['id'], reply_to)]
        message['reply_to_message'] = _v67_copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
    bot['messages'][(chat['id'], message['message_id'])] = message
    return message


class _V67BotApi(_v67_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes, per bot name."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = _v67_json.loads(raw) if raw else {}
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
            return self._answer(200, {'ok': True, 'result': _v67_message(st, bot, bot['user'], chat, body['text'], reply)})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = _v67_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _v67_checks(base):
    rows = {name: [] for name in _V67_ROWS}

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
                    check(name, 'the section ran to its end (it raised %s)' % kind.__name__, False)
            return True

    IA, SP, BK, MO = _V67_ROWS[:4]
    PR, DD, CE, AA, KC = _V67_ROWS[4:]
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {
        'control_channel_enrollment.py': ROOT / ".veldo" / "control_channel_enrollment.py",
        'control_signer_answers.py': ROOT / ".veldo" / "control_signer_answers.py",
        'control_signer.py': ROOT / ".veldo" / "control_signer.py",
        'control_keys_custody.py': ROOT / ".veldo" / "control_keys_custody.py",
        'authority_contract.py': ROOT / ".veldo" / "authority_contract.py",
        'control_channel_presentation.py': ROOT / ".veldo" / "control_channel_presentation.py",
    }
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    organs = base / 'installed'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v67_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        if _v67_Path(source).is_file():
            _v67_shutil.copyfile(source, organs / name)
    here = {name: (organs / name).is_file() for name in PRODUCTION}

    with section(IA):
        scaffold = _v67_load('v67_scaffold', scaffold_path)
        for rel in ('.veldo/control_channel_enrollment.py', '.veldo/control_signer_answers.py',
                    '.veldo/control_keys_custody.py'):
            both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
            check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
            check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
            check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
            if both:
                scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
            check(IA, rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                  and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())
        check(IA, '.veldo/control_signer.py engine copy identical',
              (ROOT / 'engine/.veldo/control_signer.py').read_bytes() == (ROOT / '.veldo/control_signer.py').read_bytes())

    claims = _v67_load('v67_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = _v67_load('v67_keys', organs / 'control_keys.py')
    I = _v67_load('v67_inbox', organs / 'control_assignment.py')
    P = _v67_load('v67_projection', organs / 'control_channel_projection.py')
    V = _v67_load('v67_presentation', organs / 'control_channel_presentation.py')
    EV = _v67_load('v67_attribution', organs / 'control_channel_attribution.py')
    SG = _v67_load('v67_signer', organs / 'control_signer.py')
    contract = _v67_load('v67_contract', organs / 'entity_contract.py')
    E = _v67_load('v67_enrollment', organs / 'control_channel_enrollment.py') if here['control_channel_enrollment.py'] else None
    A = _v67_load('v67_answers', organs / 'control_signer_answers.py') if here['control_signer_answers.py'] else None
    C = _v67_load('v67_custody', organs / 'control_keys_custody.py') if here['control_keys_custody.py'] else None

    keys, protected, edge_dir, work = base / 'keys', base / 'protected', base / 'edge', base / 'work'
    for directory in (keys, protected, edge_dir, work):
        directory.mkdir()
    keyfile = {who: keys / who for who in ('authority', 'steward', 'steward2', 'owner', 'owner2', 'member', 'pm', 'ghost',
                                           'intruder', 'intruder-auth', 'edge-next', 'edge-next-auth')}
    # The installer's layout: the edge signing key in the protected key directory the signer's fixed
    # configuration names (file name = the channel's edge key id); the connection key in the edge's custody.
    keyfile['edge'] = protected / 'edge-telegram'
    keyfile['edge-auth'] = edge_dir / 'edge-auth'
    public = {}
    for who, path in keyfile.items():
        _v67_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v67-' + who, '-f', str(path)],
                    check=True, capture_output=True, timeout=10)
        public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
    private_edge = keyfile['edge'].read_bytes()

    def sign_as(who, message, namespace='veldo-command'):
        return _v67_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                           capture_output=True, check=True, timeout=10).stdout.decode()

    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return '%s-%d' % (prefix, serial[0])

    def verifies(principal, public_key, message, signature, namespace):
        """An independent ssh-keygen verification, in a fresh directory of its own."""
        place = base / next_id('verify')
        place.mkdir()
        (place / 'allowed').write_text('%s namespaces="%s" %s\n' % (principal, namespace, public_key))
        (place / 'signature').write_text(signature if isinstance(signature, str) else '')
        done = _v67_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(place / 'allowed'), '-I', principal, '-n', namespace,
                            '-s', str(place / 'signature')], input=message, capture_output=True, timeout=10)
        return done.returncode == 0

    def canonical(value):
        return _v67_json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    ids = dict(domain_uuid='edges-domain', repository_uuid='edges-repository', store_uuid='edges-store')
    (base / 'authority').mkdir()
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    CM.attach(S)
    K.attach(S)
    repository = base / 'repository'
    repository.mkdir()
    projection = repository / '.veldo' / 'keys' / 'allowed_signers'
    config_path = base / 'authority' / 'signer.json'
    config_path.write_text(_v67_json.dumps({'store': str(db), 'repository': str(repository),
                                            'allowed_signers': str(projection), 'key_directory': str(protected),
                                            'authority_ids': ids}))

    def state():
        return CM.authority_state(S, conn)

    def envelope(command, principal, **over):
        now = state()
        found = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                     request_revision=1, nonce='nonce-' + command['command_id'], expires_at=_v67_time.time() + 600,
                     membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                     command_digest=AC.canonical_command_digest(command))
        found.update(over)
        return found

    def admin(principal, operation, params, enrollee=None):
        """One membership organ command, signed by `principal` (and co-signed by an enrollee)."""
        command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, principal)
        signature = sign_as(principal, AC.canonical_envelope_bytes(env))
        cosigned = sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal']))) if enrollee else None
        result = CM.admit(S, conn, env, command, signature, ids, _v67_time.time(), enrollee_signature=cosigned,
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
    enroll_member('owner', 'person', ['project_owner'], ['project-a', 'project-b'])
    enroll_member('owner2', 'person', ['project_owner'], ['project-a'])
    enroll_member('member', 'person', [], ['project-a'])
    enroll_member('steward2', 'person', ['membership_steward'], '*')
    enroll_member('pm', 'service', [], ['project-a'])
    admin('steward', 'revoke_membership', {'principal': 'steward2', 'revoked_at': _v67_time.time()})

    def fixture(eid, kind, data):
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

    chats = {'owner': 5560001, 'owner2': 5560002, 'member': 5560003}
    # VELDO-0064 chat enrollments, spelled here: each person's own private chat with the bot.
    for who, chat in chats.items():
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))

    # The edge enrollment path: the enrollment organ, or on the pre-change tree the VELDO-0027 key lifecycle.
    POSSESSION = 'veldo-edge-possession'
    enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection) if E is not None else None
    valid = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
             'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['project-a']}

    def edge_command(operation, params):
        params = dict(params)
        if E is None:
            legacy = {'enroll_channel_edge': 'register_signing_key', 'retire_channel_edge': 'retire_signing_key'}[operation]
            keep = ('channel', 'public_key', 'connection_public_key') if legacy == 'register_signing_key' else ()
            params = dict({f: params[f] for f in keep if f in params}, key_id=params.get('edge_key_id'))
            operation = legacy
        return {'command_id': next_id('edge'), 'operation': operation,
                'target': 'channel:%s' % params.get('channel', 'telegram_chat'), 'parameters': params,
                'artifact_digests': [], 'expected_versions': {}}

    def written():
        return conn.execute('SELECT count(*) FROM journal').fetchone()[0]

    def admit_edge(env, command, signature, proof):
        if enrollment is not None:
            got = enrollment.admit(env, command, signature, proof)
            return {'outcome': got['outcome'], 'refusal': got['refusal']}
        try:
            K.admit(S, conn, env, command, signature, ids, ('authority', journal_sign), projection)
            K.publish(S, conn, projection)
            return {'outcome': 'accepted', 'refusal': None}
        except Exception as exc:  # noqa: BLE001 - the pre-change path's refusal, by its own name
            return {'outcome': 'refused', 'refusal': getattr(exc, 'code', type(exc).__name__)}

    def submit(signer, params, operation='enroll_channel_edge', possession='edge', proof_over=None,
               namespace=POSSESSION, over=None, tamper=None, signer_key=None):
        """Sign one edge command as `signer` (with `signer_key`'s key), prove possession with
        `possession`'s key over the envelope (or `proof_over`), change it after signing with `tamper`."""
        command = edge_command(operation, params)
        env = envelope(command, signer, **(over or {}))
        signature = sign_as(signer_key or signer, AC.canonical_envelope_bytes(env))
        proof = sign_as(possession, AC.canonical_envelope_bytes(proof_over or env), namespace) if possession else None
        if tamper is not None:
            tamper(command, env)
        before = written()
        result = admit_edge(env, command, signature, proof)
        return dict(result, wrote=written() - before, env=env, command=command, signature=signature, proof=proof)

    def refused(result, name):
        return result.get('outcome') == 'refused' and result.get('refusal') == name and result.get('wrote') == 0

    def observed(result):
        """What happened instead, for a failing check's label: the outcome, the refusal and what was written."""
        return ' [observed: %s, %s, %s record(s) written]' % (result.get('outcome'), result.get('refusal'), result.get('wrote'))

    def expect_refused(row, label, result, name):
        ok = refused(result, name) and unwritten()
        check(row, 'refused with nothing written: %s (%s)' % (label, name) + ('' if ok else observed(result)), ok)

    def unwritten():
        entities = S.materialized_state(conn)['entities']
        return 'edge-telegram' not in entities and 'telegram-edge' not in entities

    def swap(field, value):
        def change(command, env):
            command['parameters'][field] = value
        return change

    def move(field):
        def change(command, env):
            env[field] = 'another-' + field
        return change

    api = {'tick': 0, 'bots': {}, 'chats': {}}
    handler = type('V67Handler', (_V67BotApi,), {'state': api})
    server = _v67_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v67_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:%d' % server.server_address[1]
    api['bots']['bot67'] = {'user': {'id': 8000000067, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_edges_bot'},
                            'next': 9000, 'update_next': 700000000, 'messages': {}, 'updates': []}
    bot = api['bots']['bot67']
    people = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize()} for who, chat in chats.items()}
    for person in people.values():
        api['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}
    signer_results = []

    try:
        # AC1: every refused enrollment, before the one valid enrollment that is the control of all three rows.
        with section(SP):
            other = envelope(edge_command('enroll_channel_edge', valid), 'steward')
            for label, result, name in (
                    ('no possession proof', submit('steward', valid, possession=None), 'key_possession_unproven'),
                    ('a possession proof by the steward\'s key', submit('steward', valid, possession='steward'),
                     'key_possession_unproven'),
                    ('the edge key\'s proof over another envelope', submit('steward', valid, proof_over=other),
                     'key_possession_unproven'),
                    ('the edge key\'s proof in the command namespace', submit('steward', valid, namespace='veldo-command'),
                     'key_possession_unproven'),
                    ('a parameter outside the schema (roles)', submit('steward', dict(valid, roles=['membership_steward'])),
                     'invalid_enrollment'),
                    ('no connection key', submit('steward', {k: v for k, v in valid.items() if k != 'connection_public_key'}),
                     'invalid_enrollment'),
                    ('another edge key id than the channel\'s', submit('steward', dict(valid, edge_key_id='edge-other')),
                     'invalid_enrollment'),
                    ('a channel outside this release (jira)', submit('steward', dict(valid, channel='jira', edge_key_id='edge-jira')),
                     'invalid_enrollment'),
                    ('the connection key equal to the signing key',
                     submit('steward', dict(valid, connection_public_key=public['edge'])), 'invalid_enrollment'),
                    ('a key that is not Ed25519', submit('steward', dict(valid, public_key='ssh-rsa AAAAB3NzaC1yc2E')),
                     'invalid_enrollment')):
                expect_refused(SP, label, result, name)
        with section(BK):
            for label, result, name in (
                    ('the public key substituted after signing, with its own possession proof',
                     submit('steward', valid, possession='intruder', tamper=swap('public_key', public['intruder'])),
                     'envelope_refused'),
                    ('the connection key substituted after signing',
                     submit('steward', valid, tamper=swap('connection_public_key', public['intruder-auth'])), 'envelope_refused'),
                    ('the scope widened after signing', submit('steward', valid, tamper=swap('scope', ['*'])), 'envelope_refused'),
                    ('the edge principal changed after signing', submit('steward', valid, tamper=swap('edge_principal', 'other-edge')),
                     'envelope_refused'),
                    ('the envelope moved to another domain after signing', submit('steward', valid, tamper=move('domain_uuid')),
                     'envelope_refused'),
                    ('the envelope moved to another repository after signing',
                     submit('steward', valid, tamper=move('repository_uuid')), 'envelope_refused'),
                    ('the envelope moved to another store after signing', submit('steward', valid, tamper=move('store_uuid')),
                     'envelope_refused'),
                    ('an envelope signed for another store', submit('steward', valid, over={'store_uuid': 'another-store'}),
                     'envelope_refused'),
                    ('an envelope signed against a stale membership version',
                     submit('steward', valid, over={'membership_version': state()['membership_version'] - 1}), 'envelope_refused'),
                    ('an expired envelope', submit('steward', valid, over={'expires_at': _v67_time.time() - 1}), 'envelope_refused'),
                    ('the steward\'s envelope signed by another member\'s key', submit('steward', valid, signer_key='member'),
                     'signature_invalid')):
                expect_refused(BK, label, result, name)
        with section(MO):
            for label, result, name in (
                    ('a revoked steward', submit('steward2', valid), 'not_current_member'),
                    ('a principal never enrolled', submit('ghost', valid), 'not_current_member'),
                    ('a current member who is not a steward', submit('member', valid), 'policy_refused'),
                    ('a service', submit('pm', valid), 'not_a_person'),
                    ('the steward enrolled as the edge', submit('steward', dict(valid, edge_principal='steward')),
                     'self_grant_refused'),
                    ('the steward\'s own key as the edge key',
                     submit('steward', dict(valid, public_key=public['steward']), possession='steward'), 'self_grant_refused'),
                    ('the steward\'s own key as the connection key',
                     submit('steward', dict(valid, connection_public_key=public['steward'])), 'self_grant_refused'),
                    ('another member\'s key as the edge key',
                     submit('steward', dict(valid, public_key=public['owner']), possession='owner'), 'key_in_use'),
                    ('an existing member as the edge principal', submit('steward', dict(valid, edge_principal='owner')),
                     'principal_exists')):
                expect_refused(MO, label, result, name)

        with section(SP, BK, MO):
            pending_before = enrollment.metrics() if enrollment is not None else {}
            enrolled = submit('steward', valid)
            accepted = enrolled['outcome'] == 'accepted' and enrolled['wrote'] == 1
            for row in (SP, BK, MO):
                check(row, 'control: the steward\'s signed enrollment with the edge key\'s own proof is accepted', accepted)
        with section(SP):
            entities = S.materialized_state(conn)['entities']
            record = entities.get('edge-telegram') or {}
            data = record.get('data') or {}
            member = (entities.get('telegram-edge') or {}).get('data') or {}
            check(SP, 'the edge key is a verification key at the id the authority contract gives the Telegram channel',
                  record.get('kind') == 'verification_key' and AC.CHANNELS['telegram_chat']['edge_key_id'] == 'edge-telegram')
            check(SP, 'the enrolled record has exactly the channel schema\'s fields',
                  set(data) == {'schema', 'channel', 'principal', 'public_key', 'connection_public_key', 'scope',
                                'effective_at', 'retired_at', 'revoked_at', 'enrolled_by', 'retired_by',
                                'enrollment_command_id', 'possession'})
            check(SP, 'the enrolled values are the signed ones: channel, edge principal, both keys, scope, signer, command',
                  data.get('schema') == 'veldo.channel_edge_key/v1' and data.get('channel') == 'telegram_chat'
                  and data.get('principal') == 'telegram-edge' and data.get('public_key') == public['edge']
                  and data.get('connection_public_key') == public['edge-auth'] and data.get('scope') == ['project-a']
                  and isinstance(data.get('effective_at'), float) and data.get('effective_at') <= _v67_time.time()
                  and data.get('retired_at') is None and data.get('revoked_at') is None and data.get('retired_by') is None
                  and data.get('enrolled_by') == 'steward'
                  and data.get('enrollment_command_id') == enrolled['command']['command_id'])
            check(SP, 'the edge principal is a new service member with no roles, the enrolled scope and its channel',
                  (entities.get('telegram-edge') or {}).get('kind') == 'membership' and member.get('principal_type') == 'service'
                  and member.get('roles') == [] and member.get('scope') == ['project-a'] and member.get('revoked_at') is None
                  and member.get('channel_edge') == 'telegram_chat' and member.get('enrolled_by') == 'steward')
            proof = data.get('possession') or {}
            proved = proof.get('envelope') or {}
            check(SP, 'the recorded possession proof is the edge key\'s own signature over the recorded envelope, in its namespace',
                  set(proof) == {'namespace', 'envelope', 'signature'} and proof.get('namespace') == POSSESSION
                  and proved == enrolled['env']
                  and verifies('telegram-edge', public['edge'], AC.canonical_envelope_bytes(proved), proof.get('signature'), POSSESSION)
                  and not verifies('telegram-edge', public['edge'], AC.canonical_envelope_bytes(proved), proof.get('signature'),
                                   'veldo-command'))
            signed = {'operation': 'enroll_channel_edge', 'target': 'channel:telegram_chat',
                      'parameters': {'channel': data.get('channel'), 'edge_principal': data.get('principal'),
                                     'edge_key_id': 'edge-telegram', 'public_key': data.get('public_key'),
                                     'connection_public_key': data.get('connection_public_key'), 'scope': data.get('scope')}}
            check(SP, 'the recorded envelope\'s digest is the digest of the command with the recorded key and parameters',
                  proved.get('command_digest') == AC.canonical_command_digest(signed))
            now = _v67_time.time()
            current = AC.active_key([k for k in state()['keyring'] if k.get('key_id') == 'edge-telegram'], 'telegram-edge', now)
            check(SP, 'the committed keyring resolves the channel\'s edge key to the enrolled key, as answer acceptance reads it',
                  current is not None and current.get('public_key') == public['edge'])
            check(SP, 'the published allowed_signers file is the accepted projection and names the edge key',
                  projection.read_text() == K.projection(state())
                  and ('telegram-edge namespaces="veldo-command" ' + public['edge']) in projection.read_text().splitlines())
            observed = enrollment.observations if enrollment is not None else []
            text = _v67_json.dumps(observed)
            classes = {'invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence',
                       'unknown_outcome'}
            check(SP, 'each admission is observed: operation, authority, channel, key id, signer, versions, outcome, named refusal',
                  len(observed) == 31 and all(o.get('repository_uuid') == ids['repository_uuid'] and 'accepted_versions' in o
                                              and o.get('edge_key_id') is not None and o.get('channel') for o in observed)
                  and observed[-1].get('outcome') == 'accepted' and observed[-1].get('principal') == 'steward'
                  and all(o['error_class'] in classes for o in observed if o['outcome'] == 'refused')
                  and 'BEGIN' not in text and 'SSH SIGNATURE' not in text)
            after = enrollment.metrics() if enrollment is not None else {}
            check(SP, 'metrics: the unenrolled channel is the pending work, and after enrollment it is enrolled',
                  pending_before.get('pending') == ['telegram_chat'] and pending_before.get('enrolled') == []
                  and after.get('pending') == [] and after.get('enrolled') == ['telegram_chat']
                  and after.get('accepted') == 1 and after.get('refused') == 30)
        with section(BK):
            state_text = _v67_json.dumps(S.materialized_state(conn)['entities'])
            check(BK, 'the committed key is exactly the signed key and connection key; no substituted key is anywhere',
                  data.get('public_key') == public['edge'] and data.get('connection_public_key') == public['edge-auth']
                  and public['intruder'] not in state_text and public['intruder-auth'] not in state_text)
            before = written()
            replay = admit_edge(enrolled['env'], enrolled['command'], enrolled['signature'], enrolled['proof'])
            check(BK, 'the accepted enrollment replayed is refused (its nonce is consumed) and writes nothing',
                  replay == {'outcome': 'refused', 'refusal': 'envelope_refused'} and written() == before)
        with section(MO):
            second = submit('steward', dict(valid, public_key=public['edge-next'], connection_public_key=public['edge-next-auth']),
                            possession='edge-next')
            check(MO, 'a second enrollment of the channel is refused (rotation is Release 2) and writes nothing',
                  refused(second, 'already_enrolled'))

        # The answer journey: delegations, presentations, the owner's replies through the Acquirer.
        with section(PR, DD, CE, AA, KC):
            now = _v67_time.time()
            grant = {'principal': 'owner', 'channel': 'telegram_chat', 'assertion_kinds': ['decision_answer'],
                     'authority_scope': ['project-a'], 'request_version': 1, 'presentation_version': 1,
                     'expires_at': now + 900, 'edge_key_id': 'edge-telegram'}

            def delegate(did, who='owner', **changes):
                admin(who, 'grant_delegation', dict(grant, id=did, **changes))

            delegate('d1')
            delegate('d2', who='owner2', principal='owner2')
            delegate('d-channel', channel='jira')
            delegate('d-edge', edge_key_id='edge-other')
            delegate('d-kinds', assertion_kinds=['acknowledgement'])
            delegate('d-request', request_version=2)
            delegate('d-presentation', presentation_version=2)
            delegate('d-scope', authority_scope=['project-b'])
            delegate('d-expired', expires_at=now - 60)
            delegate('d-revoked')
            admin('owner', 'revoke_delegation', {'id': 'd-revoked', 'revoked_at': _v67_time.time()})
            delegate('d-old')
            admin('owner', 'supersede_delegation', dict(grant, id='d-new', supersedes='d-old', presentation_version=9))
            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot67'), conn, 'authority',
                                    journal_sign, assignment=I)

            def signed_command(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            def open_framed(alias, owner):
                inbox.apply(signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                                      nonce=next_id('n'), assignment=dict(
                                                          kind='decision', owner=owner, scope=['project-a'],
                                                          deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                          brief='Choose how the example specification proceeds.',
                                                          choices=['accept', 'reject'],
                                                          subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md',
                                                                   'digest': 'sha256:' + '1' * 64}))))
                presenter.frame(signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                          risk_statement='Low: a wrong choice costs one review cycle.',
                                                          command_id=next_id('f'), nonce=next_id('fn'))))
                rid = I.assignment_id(ids['repository_uuid'], alias)
                presenter.present(rid)
                return presenter.current(rid) or {}

            r1, r2, r3, r4 = (open_framed('EDGE-%d' % n, who) for n, who in ((1, 'owner'), (2, 'owner'), (3, 'owner2'),
                                                                              (4, 'owner')))

            def reply(receipt, text, who='owner'):
                sender = people[who]
                chat = api['chats'][sender['id']]
                bot['update_next'] += 1
                update = {'update_id': bot['update_next'],
                          'message': _v67_message(api, bot, sender, chat, text, (receipt.get('message_ids') or [None])[-1])}
                bot['updates'].append(update)
                return update

            def call(request, key='edge-auth', identity='edge-telegram'):
                result = SG.call(config_path, request, identity, keyfile[key] if key else None)
                signer_results.append(result)
                return result

            def spelled(assertion, delegation, version=None):
                """A sign_answer request spelled here, not built by the module under test."""
                return {'operation': 'sign_answer', 'channel': 'telegram_chat', 'edge_key_id': 'edge-telegram',
                        'delegation_id': delegation,
                        'delegation_version': state()['delegation_version'] if version is None else version,
                        'assertion': assertion}

            adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth']) if A is not None else None
            before_hooks, after_hooks, hook_failures = {}, {}, []

            def edge_sign(message):
                """The edge's signing seam as the Acquirer calls it, with the suite's probes around it."""
                a = _v67_json.loads(message)
                for hook in before_hooks.pop(a.get('request_id'), []):
                    try:
                        hook(a)
                    except Exception as exc:  # noqa: BLE001 - a probe that raised is a failed probe, never silence
                        hook_failures.append(type(exc).__name__)
                if adapter is not None:
                    signature = adapter(message)
                else:
                    got = call(spelled(a, {'owner': 'd1', 'owner2': 'd2'}.get(a.get('principal'))))
                    if not got.get('accepted'):
                        raise RuntimeError(got.get('refusal'))
                    signature = got['signature']
                for hook in after_hooks.pop(a.get('request_id'), []):
                    try:
                        hook(a, signature)
                    except Exception as exc:  # noqa: BLE001 - as above
                        hook_failures.append(type(exc).__name__)
                return signature

            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot67'), conn, 'authority',
                                   journal_sign, 'telegram-edge', edge_sign)

            def acquire():
                return {r['update_id']: (r.get('outcome'), r.get('reason')) for r in acquirer.acquire()
                        if r.get('update_id') is not None}

            def answered(receipt):
                for (text,) in conn.execute("SELECT data FROM entities WHERE kind='presentation_answer'"):
                    found = _v67_json.loads(text)
                    if found.get('request_id') == receipt.get('request_id'):
                        return found
                return None

        # AC2: every probe runs through the actual signer inside the edge's own signing of the first answer,
        # while that answer's evidence is kept and not yet decided.
        with section(PR, DD, CE, AA):
            probes = {}
            membership = {'command_id': 'edge-self-grant', 'operation': 'enroll_principal', 'target': 'authority',
                          'parameters': {'principal': 'telegram-edge', 'principal_type': 'person',
                                         'roles': ['membership_steward'], 'public_key': public['edge'],
                                         'independence_group': 'edge', 'scope': '*'}}
            attribution_fields = ('platform_message_id', 'sender_id', 'platform_timestamp', 'chat_id', 'reply_to_message_id',
                                  'update_id', 'evidence_id', 'evidence_digest', 'bot_id', 'chat_type', 'sender_type')

            def altered(value):
                return value + 1 if isinstance(value, int) else str(value) + '-altered'

            def probe_all(a):
                probes['valid'] = a
                req = spelled(a, 'd1')
                probes['control'] = call(req)
                purpose = {
                    'arbitrary bytes': (dict({k: v for k, v in req.items() if k != 'assertion'}, operation='sign_bytes',
                                             bytes='arbitrary'), 'forbidden-purpose'),
                    'a membership operation': (dict(req, operation='enroll_principal'), 'forbidden-purpose'),
                    'a membership command as the assertion': (dict(req, assertion=membership), 'forbidden-purpose'),
                    'a membership command envelope as the assertion':
                        (dict(req, assertion=envelope(membership, 'telegram-edge')), 'forbidden-purpose'),
                    'an answer carrying a command field': (dict(req, assertion=dict(a, operation='enroll_principal')),
                                                           'forbidden-purpose'),
                    'a request field outside the answer purpose': (dict(req, bytes='arbitrary'), 'forbidden-purpose'),
                    'the evidence receipt purpose': (dict(req, operation='sign_receipt', source_id='x'), 'forbidden-purpose'),
                    'an assertion kind the delegation does not permit':
                        (dict(req, assertion=dict(a, assertion_kind='acknowledgement')), 'forbidden-purpose'),
                    'a key path': (dict(req, key_path=str(keyfile['edge'])), 'key-path')}
                probes['purpose'] = {label: (call(request), name) for label, (request, name) in purpose.items()}
                probes['unauthenticated'] = call(req, key='intruder-auth')
                other = presenter.receipt(r2.get('presentation_id') or '') or {}
                dimensions = {
                    'another principal\'s delegation': (spelled(a, 'd2'), 'actor-mismatch'),
                    'a delegation for another channel': (spelled(a, 'd-channel'), 'channel-mismatch'),
                    'a delegation binding another edge key': (spelled(a, 'd-edge'), 'edge-mismatch'),
                    'a delegation for another assertion kind': (spelled(a, 'd-kinds'), 'forbidden-purpose'),
                    'a delegation for another request version': (spelled(a, 'd-request'), 'request-mismatch'),
                    'a delegation for another presentation version': (spelled(a, 'd-presentation'), 'presentation-mismatch'),
                    'a delegation for another scope': (spelled(a, 'd-scope'), 'scope-refused'),
                    'an expired delegation': (spelled(a, 'd-expired'), 'delegation-expired'),
                    'a revoked delegation': (spelled(a, 'd-revoked'), 'delegation-refused'),
                    'a superseded delegation': (spelled(a, 'd-old'), 'stale-delegation'),
                    'a stale delegation version': (spelled(a, 'd1', state()['delegation_version'] - 1), 'stale-delegation'),
                    'no delegation': (spelled(a, None), 'delegation-refused'),
                    'another actor, under that actor\'s delegation': (spelled(dict(a, principal='owner2'), 'd2'), 'actor-mismatch'),
                    'another enrolled person as the actor': (spelled(dict(a, principal='member'), 'd1'), 'actor-mismatch'),
                    'another request': (spelled(dict(a, request_id=r2.get('request_id')), 'd1'), 'request-mismatch'),
                    'another request version': (spelled(dict(a, request_version=2), 'd1'), 'request-mismatch'),
                    'another presentation version': (spelled(dict(a, presentation_version=2), 'd1'), 'presentation-mismatch'),
                    'another presentation digest': (spelled(dict(a, presentation_digest='sha256:' + '0' * 64), 'd1'),
                                                    'presentation-mismatch'),
                    'another published presentation, named consistently':
                        (spelled(dict(a, presentation_id=other.get('presentation_id'), presentation_digest=other.get('brief_digest'),
                                      request_id=other.get('request_id')), 'd1'), 'presentation-mismatch'),
                    'another scope': (spelled(dict(a, authority_scope=['project-b']), 'd1'), 'scope-refused'),
                    'another channel': (dict(spelled(dict(a, channel='jira'), 'd1'), channel='jira'), 'channel-mismatch'),
                    'another edge key': (spelled(dict(a, edge_key_id='edge-jira'), 'd1'), 'edge-mismatch'),
                    'another edge principal': (spelled(dict(a, edge_principal='other-edge'), 'd1'), 'edge-mismatch'),
                    'another authority': (spelled(dict(a, domain_uuid='another-domain'), 'd1'), 'wrong-authority')}
                probes['dimensions'] = {label: (call(request), name) for label, (request, name) in dimensions.items()}
                evidence = {'no evidence id': {k: v for k, v in a['attribution'].items() if k != 'evidence_id'},
                            'an unknown evidence id': dict(a['attribution'], evidence_id='channel-evidence:telegram_chat:1:1'),
                            'text only, no platform evidence': {}}
                for field in attribution_fields:
                    evidence['the attribution\'s %s altered' % field] = dict(a['attribution'], **{field: altered(a['attribution'][field])})
                probes['evidence'] = {label: (call(spelled(dict(a, attribution=value), 'd1')), 'missing-evidence')
                                      for label, value in evidence.items()}

            before_hooks[r1.get('request_id')] = [probe_all]
            u1 = reply(r1, 'accept: fits the plan')
            first = acquire()
            probes['decided'] = call(spelled(probes['valid'], 'd1')) if 'valid' in probes else {}

        def no_signature(result, name):
            return not result.get('accepted') and 'signature' not in result and result.get('refusal') == name

        def expect_unsigned(row, label, result, name):
            ok = no_signature(result, name)
            seen = ' [observed: %s, %s]' % ('signed' if 'signature' in result else 'unsigned', result.get('refusal'))
            check(row, 'no signature for %s (%s)' % (label, name) + ('' if ok else seen), ok)

        with section(PR):
            control = probes.get('control') or {}
            a = probes.get('valid') or {}
            check(PR, 'the probes ran inside the edge\'s own signing, with nothing raised', 'valid' in probes and not hook_failures)
            check(PR, 'control: the actual signer signs the canonical answer, and the signature verifies with the enrolled key',
                  control.get('accepted') is True
                  and verifies('telegram-edge', public['edge'], canonical(a), control.get('signature'), 'veldo-command'))
            for label, (result, name) in sorted((probes.get('purpose') or {}).items()):
                expect_unsigned(PR, label, result, name)
            check(PR, 'the probes covered every forbidden purpose', len(probes.get('purpose') or {}) == 9)
            unauthenticated = probes.get('unauthenticated') or {}
            check(PR, 'no signature, and nothing stored revealed, for a caller without the edge\'s connection key',
                  no_signature(unauthenticated, 'unauthenticated-channel')
                  and unauthenticated.get('diagnostic') == {'key_id': None, 'principal': None, 'assertion_kind': None,
                                                            'delegation_revision': None, 'refusal': 'unauthenticated-channel'})
            diagnostic = control.get('diagnostic') or {}
            check(PR, 'the signer\'s diagnostic names operation, channel, edge, actor, request, presentation, evidence, '
                      'delegation and versions, never text or a signature',
                  diagnostic.get('operation') == 'sign_answer' and diagnostic.get('channel') == 'telegram_chat'
                  and diagnostic.get('edge_key_id') == 'edge-telegram' and diagnostic.get('principal') == 'owner'
                  and diagnostic.get('request_id') == r1.get('request_id') and diagnostic.get('delegation_id') == 'd1'
                  and diagnostic.get('evidence_id') == (a.get('attribution') or {}).get('evidence_id')
                  and diagnostic.get('presentation_id') == r1.get('presentation_id') and diagnostic.get('outcome') == 'accepted'
                  and {'membership_version', 'delegation_version'} <= set(diagnostic.get('accepted_versions') or {})
                  and 'fits the plan' not in _v67_json.dumps(diagnostic) and 'SSH SIGNATURE' not in _v67_json.dumps(diagnostic)
                  and all((r[0].get('diagnostic') or {}).get('error_class') in
                          ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence')
                          for r in (probes.get('purpose') or {}).values()))
        with section(DD):
            check(DD, 'control: the valid answer under its own current delegation is signed', (probes.get('control') or {}).get('accepted'))
            for label, (result, name) in sorted((probes.get('dimensions') or {}).items()):
                expect_unsigned(DD, label, result, name)
            check(DD, 'every delegation dimension and every assertion dimension was mutated', len(probes.get('dimensions') or {}) == 24)
        with section(CE):
            check(CE, 'control: the answer bound to its undecided canonical evidence is signed', (probes.get('control') or {}).get('accepted'))
            for label, (result, name) in sorted((probes.get('evidence') or {}).items()):
                expect_unsigned(CE, label, result, name)
            check(CE, 'every attribution field was altered', len(probes.get('evidence') or {}) == 14)
            check(CE, 'no signature for the same answer once its evidence is decided (missing-evidence)',
                  no_signature(probes.get('decided') or {}, 'missing-evidence'))

        # AC3: current edge and actor authorization at answer acceptance.
        with section(AA):
            record1 = answered(r1) or {}
            check(AA, 'a valid current Telegram answer is signed by the protected signer and accepted by the presenter',
                  first.get(u1['update_id']) == ('answered', None) and record1.get('principal') == 'owner'
                  and record1.get('edge_key_id') == 'edge-telegram' and record1.get('edge_principal') == 'telegram-edge'
                  and verifies('telegram-edge', public['edge'], canonical(record1.get('assertion')), record1.get('signature'),
                               'veldo-command'))
            results = adapter.results if adapter is not None else []
            check(AA, 'the edge asked the signer through its adapter under the owner\'s one current delegation, '
                      'in a signer process of its own',
                  bool(results) and results[-1].get('accepted') is True
                  and (results[-1].get('diagnostic') or {}).get('delegation_id') == 'd1'
                  and results[-1].get('signer_pid') not in (None, _v67_os.getpid()))

            def revoke_owner2(a, signature):
                admin('steward', 'revoke_membership', {'principal': 'owner2', 'revoked_at': _v67_time.time()})
                probes['after-revocation'] = call(spelled(a, 'd2'))

            after_hooks[r3.get('request_id')] = [revoke_owner2]
            u3 = reply(r3, 'accept: fine by me', who='owner2')
            third = acquire()
            check(AA, 'an answer the edge signed before its actor was revoked is refused at acceptance (owner_not_current)',
                  third.get(u3['update_id']) == ('refused', 'owner_not_current') and answered(r3) is None
                  and bool(results) and results[-1].get('accepted') is True)
            check(AA, 'the signer signs nothing more for the revoked actor (actor-not-current)',
                  no_signature(probes.get('after-revocation') or {}, 'actor-not-current'))

            def retire_edge(a, signature):
                probes['retirement'] = submit('steward', {'channel': 'telegram_chat', 'edge_key_id': 'edge-telegram'},
                                              operation='retire_channel_edge', possession=None)
                probes['after-retirement'] = call(spelled(a, 'd1'))

            after_hooks[r4.get('request_id')] = [retire_edge]
            u4 = reply(r4, 'accept: go ahead')
            fourth = acquire()
            retirement = probes.get('retirement') or {}
            check(AA, 'the steward\'s signed retirement of the edge key is accepted',
                  retirement.get('outcome') == 'accepted' and retirement.get('wrote') == 1)
            check(AA, 'an answer the edge signed before its key was retired is refused at acceptance (not_authorized)',
                  fourth.get(u4['update_id']) == ('refused', 'not_authorized') and answered(r4) is None)
            check(AA, 'the signer signs nothing more with the retired key (revoked-key)',
                  no_signature(probes.get('after-retirement') or {}, 'revoked-key'))
            u2 = reply(r2, 'accept: later')
            second_answer = acquire()
            check(AA, 'a new reply after retirement is not signed, so it is not accepted',
                  second_answer.get(u2['update_id']) == ('refused', 'unavailable_service') and answered(r2) is None
                  and bool(results) and results[-1].get('refusal') == 'revoked-key')
            kept = (S.materialized_state(conn)['entities'].get('edge-telegram') or {}).get('data') or {}
            check(AA, 'the retired key keeps its enrollment and records when and by whom it was retired',
                  kept.get('public_key') == public['edge'] and isinstance(kept.get('retired_at'), float)
                  and kept['retired_at'] >= kept.get('effective_at', 0) and kept.get('retired_by') == 'steward'
                  and (answered(r1) or {}).get('principal') == 'owner')
            metrics = enrollment.metrics() if enrollment is not None else {}
            check(AA, 'metrics: the retired channel is pending work again', metrics.get('retired') == ['telegram_chat']
                  and metrics.get('pending') == ['telegram_chat'] and metrics.get('enrolled') == [])
            check(AA, 'no probe around the edge\'s signing raised', not hook_failures)

        # AC3: a worker tool cannot read the private edge key.
        with section(KC):
            # The worker tool prints only what it could do, never a byte it read. The unconfined control
            # only reads, so no copy or link of the key is ever made outside its custody.
            code = ('import errno, json, os, sys\n'
                    'key, sibling, directory, work, mode = sys.argv[1:6]\n'
                    'out = {}\n'
                    'def attempt(name, action):\n'
                    '    try:\n'
                    '        action()\n'
                    '        out[name] = "done"\n'
                    '    except OSError as exc:\n'
                    '        out[name] = "denied:" + errno.errorcode.get(exc.errno, str(exc.errno))\n'
                    'attempt("read-key", lambda: open(key, "rb").read())\n'
                    'if mode == "read-only":\n'
                    '    print(json.dumps(out))\n'
                    '    sys.exit(0)\n'
                    'attempt("read-key-public", lambda: open(key + ".pub", "rb").read())\n'
                    'attempt("read-sibling", lambda: open(sibling, "rb").read())\n'
                    'attempt("list-directory", lambda: os.listdir(directory))\n'
                    'attempt("link-out", lambda: os.link(key, os.path.join(work, "taken")))\n'
                    'attempt("write-work", lambda: open(os.path.join(work, "note"), "w").write("x"))\n'
                    'attempt("read-work", lambda: open(os.path.join(work, "note")).read())\n'
                    'print(json.dumps(out))\n')
            confined_work, open_work = work / 'confined', work / 'open'
            confined_work.mkdir()
            open_work.mkdir()
            tool = [_v67_sys.executable, '-B', '-c', code, str(keyfile['edge']), str(keyfile['edge-auth']) + '.pub',
                    str(protected)]
            worker = tool + [str(confined_work), 'all']
            argv = C.confined(worker, [protected]) if C is not None else worker
            confined = _v67_sp.run(argv, capture_output=True, timeout=30)
            opened = _v67_sp.run(tool + [str(open_work), 'read-only'], capture_output=True, timeout=30)
            seen = _v67_json.loads(confined.stdout or b'{}') if confined.returncode == 0 else {}
            control = _v67_json.loads(opened.stdout or b'{}') if opened.returncode == 0 else {}
            check(KC, 'control: the same worker tool, unconfined, reads the private edge key (the denial is not file modes)',
                  control.get('read-key') == 'done')
            check(KC, 'the confined worker tool\'s read of the private edge key is denied by the kernel (EACCES)',
                  seen.get('read-key') == 'denied:EACCES' and seen.get('read-key-public') == 'denied:EACCES')
            check(KC, 'the confined worker cannot link the key out of the protected directory',
                  seen.get('link-out') in ('denied:EXDEV', 'denied:EACCES') and not (confined_work / 'taken').exists())
            check(KC, 'the confined worker keeps everything else: it reads beside the key, lists the directory and writes its work',
                  seen.get('read-sibling') == 'done' and seen.get('list-directory') == 'done'
                  and seen.get('write-work') == 'done' and seen.get('read-work') == 'done')
            marker = work / 'never-started'
            refusal = _v67_sp.run(C.confined([_v67_sys.executable, '-c', 'open(%r, "w")' % str(marker)], [base / 'absent'])
                                  if C is not None else [_v67_sys.executable, '-c', 'open(%r, "w")' % str(marker)],
                                  capture_output=True, timeout=30)
            check(KC, 'a wrapper that cannot confine starts no worker and names its refusal without a path',
                  refusal.returncode == 70 and not marker.exists()
                  and refusal.stderr.decode() == 'custody refused: invalid-protected-directory\n')
            outputs = [confined.stdout, confined.stderr, opened.stdout, opened.stderr, refusal.stderr,
                       _v67_json.dumps(signer_results).encode(),
                       _v67_json.dumps(adapter.results if adapter is not None else []).encode(),
                       _v67_json.dumps(enrollment.observations if enrollment is not None else []).encode(),
                       _v67_json.dumps(acquirer.observations).encode(), _v67_json.dumps(presenter.observations).encode()]
            laid = [p for p in base.rglob('*') if p.is_file() and not any(p.is_relative_to(d) for d in (protected, keys, edge_dir))]
            check(KC, 'the private edge key reaches no output, observation, store or file outside its custody',
                  bool(laid) and all(private_edge not in blob for blob in outputs)
                  and all(private_edge not in p.read_bytes() for p in laid))
    finally:
        server.shutdown()
        server.server_close()
        conn.close()
    return rows


_v67_started = _v67_time.monotonic()
# The store and keys live in memory-backed /dev/shm when it exists and is writable (Linux), as the
# other store suites do; elsewhere the platform's temporary directory is used.
_v67_fast = '/dev/shm' if _v67_os.path.isdir('/dev/shm') and _v67_os.access('/dev/shm', _v67_os.W_OK) else None
with _v67_temp.TemporaryDirectory(prefix='v67-', dir=_v67_fast) as _v67_dir:
    _v67_rows = _v67_checks(_v67_Path(_v67_dir))
for _v67_name, _v67_observed in _v67_rows.items():
    _v67_ok = bool(_v67_observed) and all(ok for _, ok in _v67_observed)
    if not _v67_ok:
        for _v67_label, _v67_one in _v67_observed:
            if not _v67_one:
                print('  VELDO-0067 %s detail: %s' % (_v67_name, _v67_label))
    expect('VELDO-0067 ' + _v67_name, _v67_ok)
print('VELDO-0067 suite seconds: %.3f' % (_v67_time.monotonic() - _v67_started))
