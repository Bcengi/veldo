#!/usr/bin/env python3
"""A real authority for VELDO-0073: signed store, membership, the owner's chat enrollment, the VELDO-0067
edge key, the host configuration the activated ingress is constructed from, and a loopback Bot API
stand-in in the platform's documented shapes. Used by the suite and by the live qualification runner
(proof/VELDO-0073/qualify_live.py). Every key is generated here with ssh-keygen and stays under `base`;
no private key byte, signature or token is printed."""
import copy
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _private(path, text):
    """Write `text` to a new 0600 file."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    return Path(path)


# --- the loopback Bot API stand-in -----------------------------------------------------------------

def _message(st, bot, sender, chat, text, reply_to=None):
    with st['lock']:
        bot['next'] += 1
        st['tick'] += 1
        message = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
                   'text': text}
        if reply_to is not None:
            held = bot['messages'][(chat['id'], reply_to)]
            message['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
        bot['messages'][(chat['id'], message['message_id'])] = message
        return message


class _BotApi(http.server.BaseHTTPRequestHandler):
    """getMe, getUpdates and sendMessage in the Bot API's shapes, per bot token name."""
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
        st['calls'].append(method)
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
            return self._answer(200, {'ok': True, 'result': _message(st, bot, bot['user'], chat, body['text'], reply)})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def stand_in(bots):
    """Start a loopback Bot API. `bots` maps a token name to the bot's User. Returns (url, state, stop)."""
    api = {'tick': 0, 'bots': {}, 'chats': {}, 'calls': [], 'lock': threading.Lock()}
    for name, user in bots.items():
        api['bots'][name] = {'user': dict(user), 'next': 9000, 'update_next': 730000000, 'messages': {}, 'updates': []}
    handler = type('V73Handler', (_BotApi,), {'state': api})
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop():
        server.shutdown()
        server.server_close()
    return 'http://127.0.0.1:%d' % server.server_address[1], api, stop


def deliver(api, name, sender, text, reply_to=None, chat=None):
    """The platform receiving a message from `sender` in `chat` (the sender's own private chat by
    default): the update getUpdates will return."""
    bot = api['bots'][name]
    chat = chat or api['chats'].setdefault(sender['id'], {'id': sender['id'], 'type': 'private',
                                                         'first_name': sender.get('first_name')})
    with api['lock']:
        bot['update_next'] += 1
        update_id = bot['update_next']
    update = {'update_id': update_id, 'message': _message(api, bot, sender, chat, text, reply_to)}
    bot['updates'].append(update)
    return update


# --- the authority ---------------------------------------------------------------------------------

def build(base, organs, owner_chat, origin, token, scope='project-a', token_path=None):
    """The authority under `base`, its organs loaded from `organs`, with the owner's chat enrollment at
    `owner_chat`, and the ingress host configuration naming `origin` and a 0600 token file holding
    `token`. Returns a namespace of modules, keys, paths and helpers."""
    base, organs = Path(base), Path(organs)
    base.mkdir(mode=0o700, exist_ok=True)
    claims = load('v73_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = load('v73_keys', organs / 'control_keys.py')
    E = load('v73_enrollment', organs / 'control_channel_enrollment.py')
    keys, protected, edge_dir, host = base / 'keys', base / 'protected', base / 'edge', base / 'host'
    for directory in (keys, protected, edge_dir, host):
        directory.mkdir(mode=0o700)
    keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'pm', 'api-edge', 'settler')}
    keyfile['edge'] = protected / 'edge-telegram'
    keyfile['edge-auth'] = edge_dir / 'edge-auth'
    public = {}
    for who, path in keyfile.items():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v73-' + who, '-f', str(path)],
                       check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

    def sign_as(who, message, namespace='veldo-command'):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                              capture_output=True, check=True, timeout=10).stdout.decode()

    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return '%s-%d' % (prefix, serial[0])

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    ids = dict(domain_uuid='activation-domain', repository_uuid='activation-repository', store_uuid='activation-store')
    (base / 'authority').mkdir()
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    CM.attach(S)
    K.attach(S)
    repository = base / 'repository'
    repository.mkdir()
    subprocess.run(['git', 'init', '-q', str(repository)], check=True, capture_output=True, timeout=30)
    projection = repository / '.veldo' / 'keys' / 'allowed_signers'
    signer_config = base / 'authority' / 'signer.json'
    signer_config.write_text(json.dumps({'store': str(db), 'repository': str(repository), 'allowed_signers': str(projection),
                                         'key_directory': str(protected), 'authority_ids': ids}))

    def state():
        return CM.authority_state(S, conn)

    def envelope(command, principal):
        now = state()
        return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                    request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                    membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                    command_digest=AC.canonical_command_digest(command))

    def admin(principal, operation, params, enrollee=None):
        command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, principal)
        signature = sign_as(principal, AC.canonical_envelope_bytes(env))
        cosigned = sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal']))) if enrollee else None
        result = CM.admit(S, conn, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                          journal_signer=('authority', journal_sign))
        K.publish(S, conn, projection)
        return result

    admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                          'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                          'independence_group': 'steward', 'scope': '*'})
    for who, kind, roles in (('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority',
                                                  'technical_authority']),
                             ('pm', 'service', []), ('api-edge', 'service', [])):
        admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                              'public_key': public[who], 'independence_group': who, 'scope': [scope]},
              enrollee=who)

    def fixture(eid, kind, data):
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

    def enroll_chat(chat):
        """The owner's VELDO-0064 chat enrollment: his own private chat with the bot."""
        return fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                       dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=chat,
                            revoked_at=None))

    enroll_chat(owner_chat)
    enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)

    def edge_command(operation, params):
        command = {'command_id': next_id('edge'), 'operation': operation, 'target': 'channel:telegram_chat',
                   'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, 'steward')
        possession = sign_as('edge', AC.canonical_envelope_bytes(env), 'veldo-edge-possession') if operation == 'enroll_channel_edge' else None
        return enrollment.admit(env, command, sign_as('steward', AC.canonical_envelope_bytes(env)), possession)

    edge_command('enroll_channel_edge', {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge',
                                         'edge_key_id': 'edge-telegram', 'public_key': public['edge'],
                                         'connection_public_key': public['edge-auth'], 'scope': [scope]})

    def delegate(request_version=1, presentation_version=1):
        admin('owner', 'grant_delegation', {'id': next_id('delegation-owner'), 'principal': 'owner', 'channel': 'telegram_chat',
                                            'assertion_kinds': ['decision_answer', 'review_disposition'],
                                            'authority_scope': [scope], 'request_version': request_version,
                                            'presentation_version': presentation_version,
                                            'expires_at': time.time() + 1800, 'edge_key_id': 'edge-telegram'})
    delegate()

    # The host configuration the activated ingress is constructed from (control_channel_ingress.open_ingress).
    # A live run names the account's own 0600 token file, so no copy of the token is ever written; a
    # suite or rehearsal lays a private file holding its stand-in name.
    token_file = Path(token_path) if token_path else _private(host / 'bot-token', token + '\n')
    settlement_signers = _private(host / 'settlement_signers',
                                  'settler namespaces="veldo-decision-settlement" %s\n' % public['settler'])
    enrollment_signers = _private(host / 'enrollment_signers', 'steward namespaces="veldo-enrollment" %s\n' % public['steward'])
    host_trust = _private(host / 'host_trust.json', json.dumps({'schema': 'veldo.host_trust/v1', 'host_identity': 'v73-host',
                                                                 'enrollment_signers': str(enrollment_signers),
                                                                 'settlement_signers': str(settlement_signers)}))
    config = {'schema': 'veldo.telegram_ingress/v1', 'channel': 'telegram_chat', 'store_path': str(db),
              'authority_ids': ids, 'authority_generation': 1,
              'journal': {'principal': 'authority', 'key': str(keyfile['authority'])},
              'workspace': str(repository), 'host_trust': str(host_trust),
              'signer': {'config': str(signer_config), 'edge_key_id': 'edge-telegram', 'connection_key': str(keyfile['edge-auth'])},
              'edge_principal': 'telegram-edge', 'api_edge': 'api-edge',
              'bot_api': {'origin': origin, 'token_file': str(token_file)},
              'decision_signer': {'principal': 'settler', 'key': str(keyfile['settler'])}}
    config_path = _private(host / 'ingress.json', json.dumps(config))

    def signed_command(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    def authorize(activations, action, who='owner', **params):
        """One activation command signed by `who` (the owner by default)."""
        values = {'channel': 'telegram_chat', 'action': action, 'owner': 'owner', 'origin': origin,
                  'edge_key_id': 'edge-telegram'}
        if action == 'qualify':
            values['expires_at'] = time.time() + 900
        values.update(params)
        command = {'command_id': next_id('activation'), 'operation': 'channel_activation_authorize',
                   'target': 'channel:telegram_chat', 'parameters': values, 'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, who)
        return activations.authorize(env, command, sign_as(who, AC.canonical_envelope_bytes(env)))

    def open_request(ingress, alias, choices=('accept', 'return_for_elaboration', 'reject')):
        """Signed terms, the inbox request, its framing and its presentation: (request id, receipt)."""
        settlement, presenter = ingress.settlement, ingress.presenter
        target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % alias,
                  'digest': 'sha256:' + hashlib.sha256(alias.encode()).hexdigest()}
        body = dict(ids, operation='terms', terms=alias, principal='pm', command_id=next_id('terms'),
                    nonce=next_id('terms-nonce'), touchpoint='grooming', target=target, proposal=None,
                    required_roles=[], quorum=None)
        subject = settlement.terms(signed_command('pm', body)).get('subject')
        ingress.inbox.apply(signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm',
                                                      command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                          kind='decision', owner='owner', scope=[scope],
                                                          deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                          brief='VELDO-0073 qualification: groom %s.' % alias,
                                                          choices=list(choices), subject=subject))))
        rid = assignment_id(alias)
        presenter.frame(signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a qualification request with no effect beyond its record.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
        presenter.present(rid)
        return rid, presenter.current(rid) or ([{}] + list(presenter.receipts(rid) or []))[-1]

    I = load('v73_inbox', organs / 'control_assignment.py')

    def assignment_id(alias):
        return I.assignment_id(ids['repository_uuid'], alias)

    return SimpleNamespace(S=S, CM=CM, AC=AC, K=K, E=E, I=I, claims=claims, conn=conn, ids=ids, db=db, keyfile=keyfile,
                           public=public, sign_as=sign_as, journal_sign=journal_sign, next_id=next_id, envelope=envelope,
                           admin=admin, fixture=fixture, enroll_chat=enroll_chat, edge_command=edge_command,
                           delegate=delegate, config=config, config_path=config_path, token_file=token_file,
                           signer_config=signer_config, authorize=authorize, open_request=open_request,
                           assignment_id=assignment_id, signed_command=signed_command, projection=projection,
                           settlement_signers=settlement_signers, host=host)
