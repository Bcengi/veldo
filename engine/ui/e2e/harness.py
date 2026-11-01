#!/usr/bin/env python3
"""A real Veldo factory for the UI's browser tests (VELDO-0145).

WHAT IT BUILDS, in a fresh temporary directory: a real SQLite authority store with real OpenSSH-signed
membership (a steward; the owner with every scope; owner2 scoped to project-a; bmember scoped to
project-b; cmember scoped to project-c, which has nothing yet; an outsider scoped to project-z; mover, a
project owner scoped to project-a whose scope a steward can narrow mid-test; and the pm service), the Telegram and API edges enrolled as VELDO-0067 lays them down, the real VELDO-0064
inbox, VELDO-0065 presenter (against a loopback Bot API stand-in), VELDO-0068 settlement and VELDO-0126
intake, the real control_api_authority over that store, the real protected signer process for the API
edge, real execution records written through control_execution_record.Recorder, and the real
control_api.ControlApi served by the real control_api.listen, which serves the built UI (dist/) from the
same origin under the API's own content security policy. Every module comes from the repository's
.veldo directory (or VELDO_ORGANS), copied once, never edited.

THE ORIGIN is http://localhost:<port> with relying-party id localhost: a browser treats localhost as a
secure context, so passkeys and the __Host- cookie work there exactly as on the tailnet name.

THE STORE CONNECTION belongs to one thread. Every authority call the API makes from its request threads
is carried to that thread and answered there (`OnThread`); a call made on that thread (a post-commit
notification) runs at once.

THE CONTROL PORT (a second loopback listener, never the page's origin) takes what happens at the host and
in the factory: approve a pending passkey as `veldo factory passkey` does (the steward's signed
enroll_api_credential), give a member a passkey for the browser's virtual authenticator, append lines to a
run's record and end it, drop a record stream's connection, open, revise and answer requests from Telegram,
and expire sessions. It prints one JSON line, {"origin", "control", "domain", ...}, when ready, and serves
until stdin closes or it is told to stop.

Run: python3 -B engine/ui/e2e/harness.py --dist engine/ui/dist
"""
import argparse
import base64
import concurrent.futures
import copy
import fcntl
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
CHOICES = ['accept', 'return_for_elaboration', 'reject']
DOMAIN = 'veldo-e2e'
PROJECTS = ('project-a', 'project-b', 'project-c')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class OnThread:
    """Every attribute call of `target` runs on one worker thread; a call from that thread runs at once."""

    def __init__(self, target, pool, ident):
        self._target, self._pool, self._ident = target, pool, ident

    def __getattr__(self, name):
        value = getattr(self._target, name)
        if not callable(value):
            return value

        def call(*args, **kwargs):
            if threading.get_ident() == self._ident[0]:
                return value(*args, **kwargs)
            return self._pool.submit(value, *args, **kwargs).result()
        return call


class Browser:
    """An openssl ES256 passkey for the browser's virtual authenticator: the harness registers it over the
    API exactly as the page would, and the test hands its private key to Chrome."""

    def __init__(self, directory, name):
        directory.mkdir(exist_ok=True)
        self.key = directory / (name + '.pem')
        subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out',
                        str(self.key)], check=True, capture_output=True, timeout=10)
        self.der = subprocess.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'], check=True,
                                  capture_output=True, timeout=10).stdout
        self.pkcs8 = subprocess.run(['openssl', 'pkcs8', '-topk8', '-nocrypt', '-in', str(self.key), '-outform', 'DER'],
                                    check=True, capture_output=True, timeout=10).stdout
        self.credential_id = b64url(os.urandom(32))
        self.user_handle = None

    def sign(self, message):
        return subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)], input=message, check=True,
                              capture_output=True, timeout=10).stdout

    def create(self, challenge, origin):
        client = json.dumps({'type': 'webauthn.create', 'challenge': challenge, 'origin': origin, 'crossOrigin': False},
                            separators=(',', ':')).encode()
        return {'credential_id': self.credential_id, 'public_key': b64url(self.der), 'algorithm': -7,
                'client_data_json': b64url(client)}

    def get(self, challenge, origin, rp_id):
        client = json.dumps({'type': 'webauthn.get', 'challenge': challenge, 'origin': origin, 'crossOrigin': False},
                            separators=(',', ':')).encode()
        auth = hashlib.sha256(rp_id.encode()).digest() + bytes([0x05]) + b'\x00\x00\x00\x00'
        return {'credential_id': self.credential_id, 'client_data_json': b64url(client), 'authenticator_data': b64url(auth),
                'signature': b64url(self.sign(auth + hashlib.sha256(client).digest())), 'user_handle': self.user_handle}


def record_lines(unit, station):
    """A worker run's engine and error lines in Claude Code's stream JSON shapes (VELDO-0141's formats), its
    wrapper line naming the run's own unit and station."""
    sid = 'session-' + secrets.token_hex(4)

    def assistant(*content):
        return {'type': 'assistant', 'parent_tool_use_id': None, 'session_id': sid,
                'message': {'id': 'msg_' + secrets.token_hex(6), 'role': 'assistant', 'content': list(content)}}

    def result(tool_id, text, error=False):
        return {'type': 'user', 'parent_tool_use_id': None, 'session_id': sid,
                'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'content': text,
                                                         'is_error': error}]}}
    return [
        ('wrapper', 'veldo-wrapper: engine claude-code, unit %s, station %s' % (unit, station)),
        ('engine', {'type': 'system', 'subtype': 'init', 'cwd': '/work/clone', 'session_id': sid,
                    'tools': ['Bash', 'Edit', 'Read', 'Write'], 'model': 'claude-opus-5-5', 'permissionMode': 'default'}),
        ('engine', assistant({'type': 'text', 'text': 'I will read the failing test first, then fix the parser.'})),
        ('engine', assistant({'type': 'tool_use', 'id': 'toolu_01', 'name': 'Bash',
                              'input': {'command': 'python3 -m pytest tests/test_parser.py -q', 'description': 'Run the parser tests'}})),
        ('engine', result('toolu_01', 'F.\nFAILED tests/test_parser.py::test_empty_line - AssertionError: expected [] got None\n1 failed, 1 passed in 0.04s', True)),
        ('stderr', 'warning: pytest cache directory is not writable, skipping'),
        ('engine', assistant({'type': 'tool_use', 'id': 'toolu_02', 'name': 'Edit', 'input': {
            'file_path': '/work/clone/src/parser.py',
            'old_string': 'def parse(line):\n    if not line:\n        return None\n    return line.split(",")',
            'new_string': 'def parse(line):\n    if not line:\n        return []\n    return [part.strip() for part in line.split(",")]'}})),
        ('engine', result('toolu_02', 'The file /work/clone/src/parser.py has been updated.')),
        ('engine', assistant({'type': 'tool_use', 'id': 'toolu_03', 'name': 'Bash',
                              'input': {'command': 'python3 -m pytest tests/test_parser.py -q'}})),
        ('engine', result('toolu_03', '..\n2 passed in 0.03s')),
        ('engine', {'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 4,
                    'result': 'The parser returns an empty list for an empty line; both tests pass.',
                    'stop_reason': 'end_turn', 'total_cost_usd': 0}),
    ]


RISKS = {
    'Low': 'Low: a wrong choice costs one review cycle, and the unit can be returned later.',
    'Medium': 'Medium: admitting it now delays two queued units by about a day.',
    'High': 'High: it changes what every project gates on; a wrong answer reaches every open run.',
}


class PacedClock:
    """A receiver clock for seeded lines: it starts at `start` and steps by a varied interval per reading, as a
    worker that thinks, runs a command and prints would. Once `done`, it is the real clock."""
    STEPS = (0.4, 2.1, 0.3, 6.8, 0.9, 1.6, 14.2, 0.5, 3.3, 0.7, 9.4, 0.2)

    def __init__(self, start):
        self.at, self.n, self.done = start, 0, False

    def __call__(self):
        if self.done:
            return time.time()
        self.at += self.STEPS[self.n % len(self.STEPS)]
        self.n += 1
        return self.at


def live_lines(start, count):
    """Lines a running worker prints while a test watches: alternating commands and their output."""
    out = []
    for n in range(start, start + count):
        out.append(('engine', {'type': 'assistant', 'parent_tool_use_id': None, 'session_id': 'live',
                               'message': {'id': 'msg_live_%d' % n, 'role': 'assistant', 'content': [
                                   {'type': 'tool_use', 'id': 'toolu_live_%d' % n, 'name': 'Bash',
                                    'input': {'command': 'echo step %d' % n}}]}}))
        out.append(('engine', {'type': 'user', 'parent_tool_use_id': None, 'session_id': 'live', 'message': {
            'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'toolu_live_%d' % n,
                                         'content': 'step %d' % n, 'is_error': False}]}}))
    return out


# VELDO-0159: the keystore stand-in run by control_credential_keystore.SecretService. Its argv is what that module
# passes (store with a label, clear or lookup, then the attribute pairs); a stored value arrives on standard input.
SECRET_TOOL = r'''#!/usr/bin/env python3
import json, os, sys
path, args = '@STORE@', sys.argv[1:]
items = json.load(open(path)) if os.path.exists(path) else {}
name = args[args.index('credential') + 1]
if args[0] == 'store':
    items[name] = sys.stdin.read()
elif args[0] == 'clear':
    items.pop(name, None)
elif args[0] == 'lookup':
    if name not in items:
        sys.exit(1)
    sys.stdout.write(items[name])
    sys.exit(0)
fd = os.open(path + '.tmp', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as handle:
    json.dump(items, handle)
os.replace(path + '.tmp', path)
'''


class Factory:
    def __init__(self, base, dist, organs_from):
        self.base = base
        self.lock = threading.Lock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='authority')
        self.ident = [None]
        self.pool.submit(lambda: self.ident.__setitem__(0, threading.get_ident())).result()
        self.port = free_port()
        self.host = 'localhost:%d' % self.port
        self.origin = 'http://' + self.host
        self.offset = [0.0]
        self.recorders = {}
        self.drops = set()
        self.requests = {}
        self.browsers = {}
        self.dist = dist
        self.organs_from = organs_from
        self.on_thread(self._build)

    def on_thread(self, fn, *args, **kwargs):
        if threading.get_ident() == self.ident[0]:
            return fn(*args, **kwargs)
        return self.pool.submit(fn, *args, **kwargs).result()

    def clock(self):
        return time.time() + self.offset[0]

    # the factory, built on the authority thread

    def _build(self):
        base = self.base
        organs = base / 'installed'
        organs.mkdir()
        for source in sorted(Path(self.organs_from).glob('*.py')):
            shutil.copyfile(source, organs / source.name)
        if self.dist is None:
            # Installed layout: the UI the repository's install path laid beside the modules (init_scaffold's
            # .veldo/ui) travels with them, and the API finds it there with no `ui` in its configuration.
            shutil.copytree(Path(self.organs_from) / 'ui', organs / 'ui')
        self.organs = organs
        claims = load('e2e_claims', organs / 'control_claim.py')
        S, CM, AC = claims.S, claims.CM, claims.AC
        self.S, self.CM, self.AC = S, CM, AC
        K = load('e2e_keys', organs / 'control_keys.py')
        I = load('e2e_inbox', organs / 'control_assignment.py')
        P = load('e2e_projection', organs / 'control_channel_projection.py')
        V = load('e2e_presentation', organs / 'control_channel_presentation.py')
        EV = load('e2e_attribution', organs / 'control_channel_attribution.py')
        E = load('e2e_enrollment', organs / 'control_channel_enrollment.py')
        A = load('e2e_answers', organs / 'control_signer_answers.py')
        IN = load('e2e_intake', organs / 'control_intake.py')
        ST = load('e2e_settlement', organs / 'control_request_settlement.py')
        contract = load('e2e_contract', organs / 'entity_contract.py')
        CR = load('e2e_credentials', organs / 'control_api_credentials.py')
        AUTH = load('e2e_authority', organs / 'control_api_authority.py')
        SG = load('e2e_api_signer', organs / 'control_api_signer.py')
        API = load('e2e_api', organs / 'control_api.py')
        ER = load('e2e_record', organs / 'control_execution_record.py')
        self.I, self.CR, self.API, self.ER = I, CR, API, ER

        keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
        for directory in (keys, protected, edge_dir):
            directory.mkdir()
        keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'owner2', 'outsider', 'bmember', 'cmember', 'mover',
                                                'pm')}
        keyfile['edge'] = protected / 'edge-telegram'
        keyfile['api-edge'] = protected / 'edge-api'
        keyfile['edge-auth'] = edge_dir / 'edge-auth'
        keyfile['api-auth'] = edge_dir / 'api-auth'
        public = {}
        for who, path in keyfile.items():
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'e2e-' + who, '-f', str(path)],
                           check=True, capture_output=True, timeout=10)
            public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
        self.keyfile = keyfile

        def sign_as(who, message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=10).stdout.decode()
        self.sign_as = sign_as
        serial = [0]

        def next_id(prefix):
            serial[0] += 1
            return '%s-%d-%s' % (prefix, serial[0], secrets.token_hex(3))
        self.next_id = next_id

        def journal_sign(message):
            return sign_as('authority', message, 'veldo-journal')
        self.journal_sign = journal_sign
        ids = dict(domain_uuid='e2e-domain', repository_uuid='e2e-repository', store_uuid='e2e-store')
        self.ids = ids
        (base / 'authority').mkdir()
        db = base / 'authority' / 'control.sqlite3'
        conn = S.open_store(str(db))
        self.conn = conn
        CM.attach(S)
        K.attach(S)
        repository = base / 'repository'
        repository.mkdir()
        projection = repository / '.veldo' / 'keys' / 'allowed_signers'
        config_path = base / 'authority' / 'signer.json'
        config_path.write_text(json.dumps({'store': str(db), 'repository': str(repository),
                                           'allowed_signers': str(projection), 'key_directory': str(protected),
                                           'authority_ids': ids}))

        def envelope(command, principal):
            now = CM.authority_state(S, conn)
            return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                        membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        self.envelope = envelope

        def admin(principal, operation, params, enrollee=None):
            command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority',
                       'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            env = envelope(command, principal)
            signature = sign_as(principal, AC.canonical_envelope_bytes(env))
            cosigned = (sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
                        if enrollee else None)
            result = CM.admit(S, conn, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                              journal_signer=('authority', journal_sign))
            K.publish(S, conn, projection)
            return result
        self.admin = admin

        def enroll_member(who, principal_type, roles, scope):
            admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                                  'public_key': public[who], 'independence_group': who, 'scope': scope},
                  enrollee=who)

        admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                              'roles': ['membership_steward', 'project_owner'],
                                              'public_key': public['steward'], 'independence_group': 'steward',
                                              'scope': '*'})
        enroll_member('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority',
                                          'technical_authority'], '*')
        enroll_member('owner2', 'person', ['project_owner'], ['project-a'])
        enroll_member('outsider', 'person', [], ['project-z'])
        enroll_member('bmember', 'person', [], ['project-b'])
        enroll_member('cmember', 'person', [], ['project-c'])
        enroll_member('mover', 'person', ['project_owner'], ['project-a'])
        enroll_member('pm', 'service', [], ['project-a'])

        def fixture(eid, kind, data):
            current = S.materialized_state(conn)['entities']
            return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                        parameters=dict(entity_id=eid, kind=kind, data=data),
                                        expected_versions={eid: current.get(eid, {}).get('version', 0)},
                                        artifact_digests=[], nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)
        self.fixture = fixture

        chats = {'owner': 5590001, 'owner2': 5590002, 'mover': 5590003}
        for who, chat in chats.items():
            fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                    dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                         revoked_at=None))
        enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)

        def enroll_edge(params, possession):
            command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                       'target': 'channel:' + params['channel'], 'parameters': params, 'artifact_digests': [],
                       'expected_versions': {}}
            env = envelope(command, 'steward')
            return enrollment.admit(env, command, sign_as('steward', AC.canonical_envelope_bytes(env)),
                                    sign_as(possession, AC.canonical_envelope_bytes(env), 'veldo-edge-possession'))

        enroll_edge({'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                     'public_key': public['edge'], 'connection_public_key': public['edge-auth'],
                     'scope': ['project-a']}, 'edge')
        enroll_edge({'channel': 'api', 'edge_principal': 'api-edge', 'edge_key_id': 'edge-api',
                     'public_key': public['api-edge'], 'connection_public_key': public['api-auth'],
                     'scope': ['project-a', 'project-b']}, 'api-edge')
        now = time.time()
        for who in ('owner', 'owner2', 'mover'):
            admin(who, 'grant_delegation', {'id': 'delegation-' + who, 'principal': who, 'channel': 'telegram_chat',
                                            'assertion_kinds': ['decision_answer', 'review_disposition'],
                                            'authority_scope': ['project-a'], 'request_version': 1,
                                            'presentation_version': 1, 'expires_at': now + 36000,
                                            'edge_key_id': 'edge-telegram'})

        bots = {'tick': 0, 'bots': {}, 'chats': {}, 'lock': threading.Lock()}
        self.bots = bots
        bot_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), type('Bot', (BotApi,), {'state': bots}))
        threading.Thread(target=bot_server.serve_forever, daemon=True).start()
        url = 'http://127.0.0.1:%d' % bot_server.server_address[1]
        bots['bots']['bot145'] = {'user': {'id': 8000000145, 'is_bot': True, 'first_name': 'Veldo',
                                           'username': 'veldo_e2e_bot'}, 'next': 9000, 'update_next': 720000000,
                                  'messages': {}, 'updates': []}
        self.bot = bots['bots']['bot145']
        self.people = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize()} for who, chat in chats.items()}
        for person in self.people.values():
            bots['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}

        inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
        presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot145'), conn, 'authority',
                                journal_sign, assignment=I)
        settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                   presentation=V, api_edge='api-edge')
        adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth'])
        acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot145'), conn, 'authority',
                               journal_sign, 'telegram-edge', adapter)
        intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=PROJECTS, api_edge='api-edge',
                           journal_signer='authority', sign=journal_sign)
        neighbors = ROOT / 'proof/VELDO-0152/neighbors.py'
        if neighbors.is_file():
            __import__('runpy').run_path(str(neighbors))['factory'](intake, ids, 'owner', sign_as)
        self.inbox, self.presenter, self.settlement, self.acquirer = inbox, presenter, settlement, acquirer
        self.credentials = CR.Credentials(S, conn, ids, 'authority', journal_sign, rp_id='localhost', origin=self.origin,
                                          state_dir=base / 'authority-state')
        self.records = base / 'records'
        self.records.mkdir(mode=0o700)
        lock = os.open(str(base / 'authority' / 'authority.lock'), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.api_box = []
        authority = AUTH.ApiAuthority(
            S, CM, conn, ids=ids, domain=DOMAIN, edge='api-edge', intake=intake, settlement=settlement,
            credentials=self.credentials, records=self.records, authority_lock=lock,
            notify=lambda hint: self.api_box[0].deliver(hint) if self.api_box else None)
        self.authority = authority
        self._mcp(AUTH)  # VELDO-0159
        signer = SG.ApiSigner(config_path, 'edge-api', keyfile['api-auth'])
        config = {'origin': self.origin, 'rp_id': 'localhost', 'host': self.host, 'domain': DOMAIN, 'ids': ids,
                  'edge': 'api-edge', 'state_dir': str(base / 'api-state'),
                  'ui': str(self.dist) if self.dist is not None else None}
        self.api = API.ControlApi(config, OnThread(authority, self.pool, self.ident), signer, clock=self.clock)
        self.api_box.append(self.api)
        self._seed()

    def _seed(self):
        """The runs and requests the screens show: curated, so a screenshot shows the product and not test
        residue. Two hosts; a unit waiting on authority (blocked) and one failed; five decisions whose deadlines
        and risks differ, so the inbox's ranking and urgency colors are visible. Seeded lines are paced as a
        worker prints them (PacedClock), so the gutter's times since the first line are real spans."""
        self.dispatch('done', 'VELDO-9145', 'project-a', 'build', 'COMPLETED', record_lines('VELDO-9145', 'build'), end=True,
                      paced=time.time() - 9 * 60)
        self.dispatch('live', 'VELDO-9146', 'project-a', 'build', 'RUNNING', record_lines('VELDO-9146', 'build')[:4], paced=time.time() - 140)
        self.dispatch('quiet', 'VELDO-9147', 'project-a', 'review', 'REVIEWING', [])
        self.dispatch('other', 'VELDO-9148', 'project-b', 'build', 'RUNNING', record_lines('VELDO-9148', 'build')[:3], host='veldo-linux-2',
                      paced=time.time() - 75)
        self.dispatch('blocked', 'VELDO-9149', 'project-a', 'review', 'AWAITING_AUTHORITY', record_lines('VELDO-9149', 'review')[:2], end=True,
                      host='veldo-linux-2', paced=time.time() - 50 * 60)
        self.dispatch('failed', 'VELDO-9144', 'project-a', 'build', 'FAILED', record_lines('VELDO-9144', 'build')[:5], end=True,
                      paced=time.time() - 3 * 3600)
        # Each presented some hours ago (the Bot stand-in's message date), oldest first, so "waited longest" is real.
        for alias, hours, risk, ago in (('de1', 30, 'Medium', 50), ('de2', 70, 'Low', 30), ('de3', 5, 'High', 20),
                                        ('de4', 140, 'Low', 8), ('de5', 52, 'High', 2)):
            self.bots['back'] = ago * 3600
            self.open_request(alias, deadline_hours=hours, risk=risk)
        self.bots['back'] = 0

    def dispatch(self, key, unit, project, station, unit_state, lines, end=False, host='veldo-linux-1', paced=None):
        dispatch_id = 'dispatch/%s/%s' % (unit, secrets.token_hex(16))
        digest = 'sha256:' + hashlib.sha256(dispatch_id.encode()).hexdigest()
        data = dict(schema='veldo.dispatch/v1', dispatch_id=dispatch_id, state='running', contract_digest=digest,
                    process={'platform': 'linux', 'host': host, 'boot_id': 'boot-e2e', 'pid': 4000 + len(self.recorders),
                             'start': 17},
                    contract={'unit': unit, 'station': station, 'attempt': 1,
                              'reservation': {'project': project, 'account': 'owner-plan'},
                              # VELDO-0131: control_launch's capability (the adapter and the configuration it runs).
                              'capability': {'adapter': 'claude_code',
                                             'configuration': {'role': 'general', 'revision': 2,
                                                               'native_tools': [{'name': 'Read', 'load': 'always'}],
                                                               'mcp': [{'server': 'atlassian', 'revision': 1}]}}})
        self.fixture('dispatch:' + dispatch_id, 'dispatch', data)
        self.fixture(unit, 'execution_unit', dict(state=unit_state, repository_uuid=self.ids['repository_uuid'],
                                                  revision=1, project=project))
        header = {'dispatch_id': dispatch_id, 'contract_digest': digest, 'unit': unit, 'station': station,
                  'project': project, 'account': 'owner-plan', 'host': host}
        clock = PacedClock(paced) if paced else time.time
        recorder = self.ER.Recorder(self.records, header, self.ER.Resolved(), clock=clock)
        self.recorders[key] = {'id': dispatch_id, 'recorder': recorder, 'data': data, 'unit': unit}
        self._append(key, lines)
        if end:
            self._end(key)
        if paced:
            clock.done = True
        return dispatch_id

    def _append(self, key, lines):
        entry = self.recorders[key]
        recorder = entry['recorder']
        for stream, payload in lines:
            text = payload if isinstance(payload, str) else json.dumps(payload, separators=(',', ':'))
            recorder.feed(stream, text.encode('utf-8') + b'\n')
        recorder.batch()
        if self.api_box:
            self.api.deliver_record({'dispatch_id': entry['id'], 'seq': recorder.sequence})
        return recorder.sequence

    def _end(self, key):
        entry = self.recorders[key]
        committed = entry['recorder'].close()
        entry['data'] = dict(entry['data'], state='exited', execution_record=committed)
        self.fixture('dispatch:' + entry['id'], 'dispatch', entry['data'])
        if self.api_box:
            self.api.deliver_record({'dispatch_id': entry['id'], 'seq': committed['lines']})
        return committed

    def signed_command(self, who, body):
        return {'command': body, 'signature': self.sign_as(who, self.S.canonical_bytes(body))}

    def open_request(self, alias, owner='owner', requester='pm', deadline_hours=None, risk=None, brief=None):
        target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % alias,
                  'digest': 'sha256:' + hashlib.sha256(json.dumps(alias).encode()).hexdigest()}
        body = dict(self.ids, operation='terms', terms=alias, principal=requester, command_id=self.next_id('terms'),
                    nonce=self.next_id('terms-nonce'), touchpoint='admission', target=target, proposal=None,
                    required_roles=[], quorum=None)
        subject = self.settlement.terms(self.signed_command(requester, body)).get('subject')
        due = time.time() + 3600 * (deadline_hours if deadline_hours is not None else 6 * 24)
        deadline = time.strftime('%Y-%m-%dT%H:%M:00Z', time.gmtime(due))
        briefs = {'de1': 'Admit VELDO-9150, the record search index, into the backlog?',
                  'de2': 'Admit VELDO-9151, retries for the Telegram edge, into the backlog?',
                  'de3': 'Admit VELDO-9152, the nightly proof digest, into the backlog?',
                  'de4': 'Admit VELDO-9153, the account pool rebalance, into the backlog?',
                  'de5': 'Admit VELDO-9154, the gate timing report, into the backlog?'}
        self.inbox.apply(self.signed_command(requester, dict(
            self.ids, operation='open', alias=alias, principal=requester, command_id=self.next_id('c'),
            nonce=self.next_id('n'), assignment=dict(kind='decision', owner=owner, scope=['project-a'],
                                                      deadline=deadline, budget={'owner_minutes': 15},
                                                      brief=brief or briefs.get(alias, 'Decide %s.' % alias), choices=list(CHOICES),
                                                      subject=subject))))
        rid = self.I.assignment_id(self.ids['repository_uuid'], alias)
        self.frame(alias, requester, 1, risk)
        self.presenter.present(rid)
        self.requests[alias] = rid
        return rid

    def frame(self, alias, requester, version, risk=None):
        self.presenter.frame(self.signed_command(requester, dict(
            self.ids, operation='frame', alias=alias, principal=requester, request_version=version,
            risk_statement=RISKS.get(risk, RISKS['Low']),
            command_id=self.next_id('f'), nonce=self.next_id('fn'))))

    def revise(self, alias, requester='pm'):
        rid = self.requests[alias]
        self.inbox.apply(self.signed_command(requester, dict(
            self.ids, operation='revise', alias=alias, principal=requester, command_id=self.next_id('c'),
            nonce=self.next_id('n'), request_version=1, changes={'brief': 'Revised: admit %s with a smaller scope?' % alias})))
        self.frame(alias, requester, 2)
        self.presenter.present(rid)
        return self.presenter.current(rid) or {}

    def telegram_reply(self, alias, text, who='owner'):
        receipt = self.presenter.current(self.requests[alias]) or {}
        sender = self.people[who]
        chat = self.bots['chats'][sender['id']]
        with self.bots['lock']:
            self.bot['update_next'] += 1
            update_id = self.bot['update_next']
        self.bot['updates'].append({'update_id': update_id, 'message': message(
            self.bots, self.bot, sender, chat, text, (receipt.get('message_ids') or [None])[-1])})
        self.acquirer.acquire()
        return self.settlement.run()

    def settlements(self, alias):
        rid = self.requests[alias]
        rows = self.conn.execute("SELECT data FROM entities WHERE kind='request_settlement'").fetchall()
        return [json.loads(r[0]) for r in rows if json.loads(r[0]).get('request_id') == rid]

    def call(self, method, path, body=None, cookie=None, token=None):
        headers = {'Host': self.host}
        if method == 'POST':
            headers.update({'Origin': self.origin, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json'})
        if cookie:
            headers['Cookie'] = '__Host-veldo-session=' + cookie
        if token:
            headers['X-Veldo-Token'] = token
        return self.api.handle(method, path, headers, json.dumps(body).encode() if body is not None else b'')

    def steward_enroll(self, pending, principal):
        CR = self.CR
        command = CR.enrollment_command(pending, principal, self.next_id('credential'))
        env = self.envelope(command, 'steward')
        return self.credentials.admit(env, command, self.sign_as('steward', self.AC.canonical_envelope_bytes(env)))

    def pending(self):
        found = []
        for path in sorted((self.base / 'api-state' / 'pending').glob('*.json')):
            data = json.loads(path.read_text())
            found.append(dict(self.CR.describe(data), pending_id=path.stem))
        return found

    def approve(self, principal, label=None):
        """What `veldo factory passkey` does at the host: show the waiting passkey, and the steward signs its
        enrollment for the principal."""
        for path in sorted((self.base / 'api-state' / 'pending').glob('*.json')):
            data = json.loads(path.read_text())
            if label is None or data['binding']['label'] == label:
                got = self.on_thread(self.steward_enroll, data, principal)
                return dict(self.CR.describe(data), outcome=got.get('outcome'), refusal=got.get('refusal'))
        return {'outcome': 'refused', 'refusal': 'no_pending_registration'}

    def passkey(self, principal):
        """A passkey for `principal`, registered over the API as the page does and enrolled at the host; its
        private key goes to the browser's virtual authenticator."""
        browser = Browser(self.base / 'browsers', principal + '-' + secrets.token_hex(3))
        status, _h, begun = self.call('POST', '/api/v1/auth/registration/begin', {'label': principal + ' e2e'})
        assert status == 200, begun
        browser.user_handle = begun['user_handle']
        made = browser.create(begun['challenge'], self.origin)
        status, _h, offered = self.call('POST', '/api/v1/auth/registration/credential',
                                        dict(made, registration_id=begun['registration_id']))
        assert status == 200, offered
        proof = browser.get(offered['possession_challenge'], self.origin, 'localhost')
        status, _h, shown = self.call('POST', '/api/v1/auth/registration/possession',
                                      dict({k: v for k, v in proof.items() if k != 'credential_id'},
                                           registration_id=begun['registration_id']))
        assert status == 200, shown
        pending = json.loads((self.base / 'api-state' / 'pending' / (begun['registration_id'] + '.json')).read_text())
        got = self.on_thread(self.steward_enroll, pending, principal)
        assert got.get('outcome') not in ('refused',), got
        self.browsers[principal] = browser
        return {'credential_id': browser.credential_id, 'private_key': base64.b64encode(browser.pkcs8).decode(),
                'user_handle': browser.user_handle, 'rp_id': 'localhost'}

    def session(self, principal):
        """A signed-in API session for `principal` without a browser (the gate's rows): its passkey registered and
        approved as `passkey` does, then the sign-in ceremony over the API. Returns (cookie, anti-forgery token)."""
        self.passkey(principal)
        browser = self.browsers[principal]
        status, _h, challenge = self.call('POST', '/api/v1/auth/challenge', {})
        assert status == 200, challenge
        status, headers, view = self.call('POST', '/api/v1/auth/sign-in',
                                          browser.get(challenge['challenge'], self.origin, 'localhost'))
        assert status == 200, view
        cookie = [v for k, v in headers if k == 'Set-Cookie'][0].split(';', 1)[0].split('=', 1)[1]
        return cookie, view['csrf_token']


    # VELDO-0159: the MCP catalog and the write-only credential commands, as control_service_api lays them

    def _mcp(self, AUTH):
        """The real catalog (VELDO-0144 AC1) and credential commands (AC2) on this store. The keystore is the real
        control_credential_keystore.SecretService running a stand-in `secret-tool` executable that keeps each value
        in a 0600 file of this temporary directory, so a value travels exactly as it does to the Secret Service: on
        the executable's standard input, never its command line."""
        self.keystore_file = self.base / 'keystore.json'
        tool = self.base / 'bin' / 'secret-tool'
        tool.parent.mkdir()
        tool.write_text(SECRET_TOOL.replace('@STORE@', str(self.keystore_file)))
        tool.chmod(0o700)
        common = dict(domain=self.ids['domain_uuid'], repository=self.ids['repository_uuid'], signer='authority',
                      sign=self.journal_sign, generation=1)
        self.authority.catalog = AUTH.MC.Catalog(self.S, self.conn, **common)
        keystore = AUTH.CV.KS.SecretService(str(tool))  # its refusals are the ones the commands catch
        self.authority.mcp_credentials = AUTH.CV.Credentials(self.S, self.conn, keystore=keystore, **common)
        self.mcp_session = None

    def mcp_state(self):
        """Every catalog revision and head and every credential record as the store holds them, and the keystore's
        items by name with the digest of each value (never the value)."""
        out = {'servers': {}, 'heads': {}, 'credentials': {}, 'keystore': {}}
        for kind, version, data in self.conn.execute(
                "SELECT kind, version, data FROM entities WHERE kind IN ('mcp_server', 'mcp_server_head', 'credential')"):
            data = json.loads(data)
            if kind == 'mcp_server':
                out['servers'].setdefault(data['id'], {})[str(data['revision'])] = data
            elif kind == 'mcp_server_head':
                out['heads'][data['id']] = data['revision']
            else:
                out['credentials'][data['id']] = dict(data, version=version)
        if self.keystore_file.is_file():
            for name, value in json.loads(self.keystore_file.read_text()).items():
                out['keystore'][name] = hashlib.sha256(value.encode()).hexdigest()
        return out

    def mcp_save(self, definition, base):
        """Another session of the owner saves a revision through the API's catalog route (the stale-save row)."""
        if self.mcp_session is None:
            self.mcp_session = self.session('owner')
        cookie, token = self.mcp_session
        status, _h, answer = self.call('POST', '/api/v1/domains/%s/mcp/catalog/save' % DOMAIN,
                                       {'definition': definition, 'base': base}, cookie=cookie, token=token)
        return {'status': status, 'answer': answer}


def message(st, bot, sender, chat, text, reply_to=None):
    with st['lock']:
        bot['next'] += 1
        st['tick'] += 1
        sent = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': int(time.time()) - st.get('back', 0) + st['tick'],
                'text': text}
        if reply_to is not None and (chat['id'], reply_to) in bot['messages']:
            held = bot['messages'][(chat['id'], reply_to)]
            sent['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
        bot['messages'][(chat['id'], sent['message_id'])] = sent
        return sent


class BotApi(http.server.BaseHTTPRequestHandler):
    """Loopback Bot API stand-in: getMe, getUpdates and sendMessage in the platform's shapes."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = json.loads(raw) if raw else {}
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
            return self._answer(200, {'ok': True, 'result': message(st, bot, bot['user'], chat, body['text'], reply)})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def control_server(factory, stop):
    """The host's and the factory's side, on its own loopback port."""

    class Control(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            try:
                value = self.route(self.path, body)
                status = 200
            except Exception as error:  # noqa: BLE001 - the test sees the failure by name
                value, status = {'error': '%s: %s' % (type(error).__name__, error)}, 500
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def route(self, path, body):
            f = factory
            if path == '/state':
                return {'origin': f.origin, 'domain': DOMAIN,
                        'dispatches': {k: v['id'] for k, v in f.recorders.items()},
                        'units': {k: v['unit'] for k, v in f.recorders.items()}, 'requests': dict(f.requests)}
            if path == '/pending':
                return {'pending': f.pending()}
            if path == '/approve':
                return f.approve(body['principal'], body.get('label'))
            if path == '/passkey':
                return f.passkey(body['principal'])
            if path == '/record/append':
                lines = body.get('lines') or live_lines(body.get('start', 1), body.get('count', 1))
                return {'seq': f.on_thread(f._append, body['key'], [(l[0], l[1]) for l in lines])}
            if path == '/record/end':
                return {'committed': f.on_thread(f._end, body['key'])}
            if path == '/record/read':
                rec = f.recorders[body['key']]
                lines = f.ER.read(f.records, rec['id'], 0, 100000, None)
                return {'lines': lines['lines'], 'total': lines['total']}
            if path == '/record/drop':
                f.drops.add(f.recorders[body['key']]['id'])
                return {'dropping': True}
            if path == '/dispatch/new':
                unit, station = body.get('unit', 'VELDO-9160'), body.get('station', 'build')
                lines = record_lines(unit, station) if body.get('lines', 'seed') == 'seed' else []
                key = body.get('key') or 'run-' + secrets.token_hex(3)
                f.on_thread(f.dispatch, key, unit, body.get('project', 'project-a'),
                            station, body.get('unit_state', 'RUNNING'), lines[:body.get('count', len(lines))])
                return {'key': key, 'dispatch': f.recorders[key]['id']}
            if path == '/request/open':
                return {'request': f.on_thread(f.open_request, body['alias'], body.get('owner', 'owner'), 'pm',
                                               body.get('deadline_hours'), body.get('risk'), body.get('brief'))}
            if path == '/member/scope':
                f.on_thread(f.admin, 'steward', 'change_roles', {'principal': body['principal'],
                                                                  'roles': body.get('roles', ['project_owner']),
                                                                  'scope': body['scope']})
                return {'scope': body['scope']}
            if path == '/request/revise':
                receipt = f.on_thread(f.revise, body['alias'])
                return {'presentation_version': receipt.get('presentation_version')}
            if path == '/request/telegram':
                return {'run': str(f.on_thread(f.telegram_reply, body['alias'], body['text'], body.get('who', 'owner')))}
            if path == '/request/settlements':
                return {'settlements': f.on_thread(f.settlements, body['alias'])}
            if path == '/sessions/expire':
                f.offset[0] += 31 * 60
                return {'offset': f.offset[0]}
            if path == '/sessions/end':
                ended = f.api.sessions.end_by_principal(body['principal'])
                f.api._reap('signed_out')
                return {'ended': ended}
            if path == '/observations':
                return {'observations': [dict(o) for o in f.api.observations]}
            if path == '/mcp/state':  # VELDO-0159
                return f.on_thread(f.mcp_state)
            if path == '/mcp/save':  # VELDO-0159
                return f.mcp_save(body['definition'], body['base'])
            if path == '/stop':
                stop.set()
                return {'stopping': True}
            raise KeyError(path)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Control)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dist', default=str(HERE.parents[1] / 'dist'))
    parser.add_argument('--installed-ui', action='store_true',
                        help='serve the UI laid beside the organs (<organs>/ui), as an installed factory does')
    parser.add_argument('--organs', default=os.environ.get('VELDO_ORGANS') or str(ROOT / '.veldo'))
    args = parser.parse_args()
    stop = threading.Event()
    with tempfile.TemporaryDirectory(prefix='veldo-ui-e2e-') as directory:
        factory = Factory(Path(directory), None if args.installed_ui else Path(args.dist).resolve(), args.organs)
        API = factory.API
        original = API.serve_stream

        def serve_stream(stream, write, idle=API.STREAM_IDLE_SECONDS):
            """The production stream writer, with the harness able to cut one record stream's connection
            mid-run (the next write fails as a dropped socket would), so the browser must resume."""
            def guarded(data):
                if stream.dispatch_id in factory.drops:
                    factory.drops.discard(stream.dispatch_id)
                    raise OSError('connection dropped by the harness')
                write(data)
            return original(stream, guarded, idle)
        API.serve_stream = serve_stream
        server = API.listen(factory.api, '127.0.0.1', factory.port)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        control = control_server(factory, stop)
        print(json.dumps({'origin': factory.origin, 'control': 'http://127.0.0.1:%d' % control.server_address[1],
                          'domain': DOMAIN}), flush=True)

        def watch_stdin():
            try:
                sys.stdin.read()
            finally:
                stop.set()
        threading.Thread(target=watch_stdin, daemon=True).start()
        stop.wait()
        server.shutdown()
        control.shutdown()
        factory.pool.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    main()
