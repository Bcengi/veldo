#!/usr/bin/env python3
"""veldo factory setup: lay a real factory down on this host from the owner's own signed commands (VELDO-0139).

WHAT THIS MODULE IS. The one owner-run command that assembles a running factory from the pieces that
already exist, in the order they depend on each other, checking each. It reimplements none of them:

  1. the control store under the given state root (control_store.open_store);
  2. the owner bootstrap (VELDO-0025): his own enroll_principal command, signed with the private key he
     names, admitted by control_membership.admit, whose bootstrap_problems accepts exactly this while no
     membership exists;
  3. the public key projection (control_keys.publish) the protected signer reads;
  4. the owner's Telegram chat enrollment (VELDO-0064/0065) from the chat id he gives;
  5. the VELDO-0067 Telegram edge key, generated in the protected key directory, enrolled by his signed
     enroll_channel_edge command with the edge key's possession proof (control_channel_enrollment);
  6. his STANDING delegation of decision answers to that edge (control_membership grant_delegation, his
     signature; it names no request or presentation version, VELDO-0140, and he renews it with
     `veldo channel delegate` before it expires);
     then the factory's qualification requester, a service member whose key is generated in the protected
     key directory, enrolled by his signed enroll_principal with the requester key's possession
     co-signature; setup republishes the key projection itself. The running service's channel
     (control_service_channel) opens the one qualification decision request as this requester when it
     accepts his qualify command, so the live qualification needs no other preparation;
  7. this host's trust (control_eligibility.host_trust_path, read by load_host_trust) naming this host's
     identity, the owner as enrollment signer and the settlement signer;
  8. the VELDO-0029 enrollment of the named workspace clone, signed by the owner (control_enrollment.enroll);
  9. the 0600 VELDO-0073 ingress configuration (control_channel_ingress.load_config and open_ingress read
     it), naming the account's own 0600 bot token file, never a copy of the token;
 10. the VELDO-0047 authority service, installed with that ingress (control_service.install). It starts
     nothing: the service is started by the owner's explicit start and its channel is inert
     (not_activated) until his VELDO-0138 qualify and activate.

WHAT IS REFUSED, BY NAME, WITH NOTHING WRITTEN. Every check runs before the first write: a state root that
is absent, a link, not a directory, not this account's, not 0700, on an unsupported filesystem or not
empty (a store, a trust or anything else already there); a host trust file that already exists; a
workspace that is not a Git clone, is already enrolled, or overlaps the state root; an owner key that is
not a readable private key that signs; a token file that is not this account's own 0600 file holding one
token, or lies inside the workspace; a chat id that is not a Telegram user id; a key directory a worker
could write; a worker profile this host does not qualify. Nothing is ever overwritten: every file is
created exclusively.

ROLLBACK. The setup never deletes. A step that fails after writing began is reported by name with the
step; the owner stops and uninstalls the service with VELDO-0047's lifecycle and removes by hand the
state root's contents, the host trust file and the workspace binding at
<clone>/.git/veldo/control/enrollment.json. A second setup over the same paths then succeeds.

Observations and output carry paths, identities and digests, never a private key byte, a signature or the
token. Standard library only; every organ is loaded as a sibling by path.
"""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import time
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location('factory_setup_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMA = 'veldo.factory_setup/v1'
TELEGRAM_ORIGIN = 'https://api.telegram.org'
CHANNEL = 'telegram_chat'
# The service principals of one factory, named here once.
JOURNAL_PRINCIPAL = 'authority'
EDGE_PRINCIPAL = 'telegram-edge'
API_EDGE = 'api-edge'
SETTLEMENT_PRINCIPAL = 'settlement'
# The qualification requester the running service's channel opens its one request as (VELDO-0139),
# named once, by the channel that signs as it.
_CHANNEL = organ('control_service_channel')
REQUESTER, REQUESTER_KEY, REQUESTER_SCOPE = _CHANNEL.REQUESTER, _CHANNEL.REQUESTER_KEY, _CHANNEL.REQUESTER_SCOPE
RESERVED = (JOURNAL_PRINCIPAL, EDGE_PRINCIPAL, API_EDGE, SETTLEMENT_PRINCIPAL, 'launch-receiver', REQUESTER)
# The owner's roles: the bootstrap's two (project_owner, membership_steward) and the authorities a factory
# owner decides with.
OWNER_ROLES = ['admission_authority', 'membership_steward', 'priority_authority', 'project_owner',
               'technical_authority']
# How long the owner's standing delegation of Telegram decision answers lasts before he renews it
# (veldo channel delegate, VELDO-0140).
DELEGATION_DAYS = 90
# The state root's layout.
STORE_DIR, KEYS_DIR, EDGE_DIR, HOST_DIR = 'authority', 'keys', 'edge', 'host'
STORE_NAME = 'control.sqlite3'
JOURNAL_KEY, SETTLEMENT_KEY, CONNECTION_KEY = 'journal', 'settlement', 'edge-auth'
PLAIN = re.compile(r'[a-z][a-z0-9._-]{0,62}')
EXIT_REFUSED, EXIT_USAGE = 1, 2


class Refused(Exception):
    def __init__(self, code, detail='', problems=None):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail, self.problems = code, detail, list(problems or [code])


def _quiet_env():
    """The environment every ssh-keygen call runs in: never through an agent."""
    return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}


def _within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root.rstrip('/') + '/')


def _private(path, text, mode=0o600):
    """A new file of exactly `mode`, never through a link and never over an existing one."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    os.chmod(str(path), mode)
    return str(path)


def _keygen(path, comment):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                   capture_output=True, timeout=30, stdin=subprocess.DEVNULL, env=_quiet_env())
    os.chmod(str(path), 0o600)
    return ' '.join(Path(str(path) + '.pub').read_text().split()[:2])


def public_key(private_key):
    """The OpenSSH public key of a private key file, derived from it (never read from a .pub beside it)."""
    done = subprocess.run(['ssh-keygen', '-y', '-f', str(private_key)], capture_output=True, text=True, timeout=30,
                          env=_quiet_env())
    if done.returncode or not done.stdout.strip():
        raise Refused('invalid_input:owner_key:unreadable', 'the owner key is not a readable OpenSSH private key')
    return ' '.join(done.stdout.split()[:2])


# ---------------------------------------------------------------------------------------------
# Every check, before anything is written
# ---------------------------------------------------------------------------------------------

def state_root_problems(root):
    """Why `root` may not receive a new factory, first the one to act on; [] when it may."""
    text = str(root)
    if not os.path.isabs(text):
        return ['invalid_input:state_root:relative']
    try:
        info = os.lstat(text)
    except FileNotFoundError:
        return ['missing_authority:state_root:absent']
    if stat.S_ISLNK(info.st_mode):
        return ['invalid_input:state_root:symlink']
    if not stat.S_ISDIR(info.st_mode):
        return ['invalid_input:state_root:not_a_directory']
    problems = []
    if info.st_uid != os.getuid():
        problems.append('invalid_input:state_root:owner')
    if stat.S_IMODE(info.st_mode) != 0o700:
        problems.append('invalid_input:state_root:mode')
    if problems:
        return problems
    held = holdings(text)
    if held:
        return ['invalid_input:state_root:holds_' + held[0]]
    return []


def holdings(root):
    """What an existing state root already holds, by name: a store, a trust, an empty directory of the
    setup's own layout (empty_host, a leftover of a removed factory), or anything else (other)."""
    names = sorted(os.listdir(root))
    found, rest = [], []
    for name in names:
        path = os.path.join(root, name)
        directory = os.path.isdir(path) and not os.path.islink(path)
        inside = sorted(os.listdir(path)) if directory else []
        if name.endswith('.sqlite3') or any(n.startswith(STORE_NAME) for n in inside):
            found.append('store')
        elif any(n in ('host_trust.json', 'enrollment_signers', 'settlement_signers') for n in inside):
            found.append('trust')
        elif directory and not inside and name in (STORE_DIR, KEYS_DIR, EDGE_DIR, HOST_DIR):
            rest.append('empty_' + name)
        else:
            rest.append('other')
    order = ('store', 'trust')
    return sorted(set(found), key=order.index) + sorted(set(rest))


def host_trust_directory_problem(directory):
    """Why an EXISTING directory may not receive this host's trust (it is this account's own 0700
    directory, never a link); None when it may, or when it is absent and setup creates it 0700."""
    try:
        found = os.lstat(directory)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(found.st_mode):
        return 'invalid_input:host_trust_directory:symlink'
    if not stat.S_ISDIR(found.st_mode):
        return 'invalid_input:host_trust_directory:not_a_directory'
    if found.st_uid != os.getuid():
        return 'invalid_input:host_trust_directory:owner'
    if stat.S_IMODE(found.st_mode) != 0o700:
        return 'invalid_input:host_trust_directory:mode'
    return None


def check(state_root, owner, owner_key, workspace, chat, token_file, *, host_trust, install_root, unit_dir,
          profile, writable, origin):
    """Every precondition, as a plan the setup then carries out, or Refused naming the first problem."""
    CS, E, IN, S = organ('control_service'), organ('control_enrollment'), organ('control_channel_ingress'), organ('control_store')
    problems = state_root_problems(state_root)
    if problems:
        raise Refused(problems[0], str(state_root), problems)
    root = os.path.realpath(str(state_root))
    if S.filesystem_problems(root):
        raise Refused('invalid_input:state_root:filesystem', root)
    if not isinstance(owner, str) or not PLAIN.fullmatch(owner) or owner in RESERVED:
        raise Refused('invalid_input:owner:name', 'the owner is a plain principal name, not a service principal')
    if type(chat) is not int or chat <= 0:
        raise Refused('invalid_input:chat:not_a_user_id', 'the chat is the owner\'s numeric Telegram user id')
    if os.path.lexists(host_trust):
        raise Refused('invalid_input:host_trust:exists', host_trust)
    if _within(host_trust, root):
        raise Refused('invalid_input:host_trust:inside_state_root', host_trust)
    problem = host_trust_directory_problem(os.path.dirname(os.path.abspath(str(host_trust))))
    if problem:
        raise Refused(problem, os.path.dirname(os.path.abspath(str(host_trust))))
    workspace = os.path.realpath(str(workspace))
    try:
        E.git_common_dir(workspace)
    except (E.EnrollmentRefused, OSError):
        raise Refused('invalid_input:workspace:not_a_clone', workspace) from None
    if E.read_binding(workspace) is not None or os.path.lexists(E.binding_path(workspace)):
        raise Refused('invalid_input:workspace:enrolled', workspace)
    if _within(workspace, root) or _within(root, workspace):
        raise Refused('invalid_input:workspace:overlaps_state_root', workspace)
    if _within(host_trust, workspace):
        raise Refused('invalid_input:host_trust:inside_workspace', host_trust)
    if not isinstance(token_file, str) or not os.path.isabs(token_file):
        raise Refused('invalid_input:token_file:relative', 'the token file is named by its absolute path')
    try:
        IN.read_token(token_file)
    except IN.Refused as exc:
        raise Refused('missing_authority:token_file:absent' if exc.code == 'missing_authority'
                      else 'invalid_input:token_file:unusable', token_file) from None
    if _within(token_file, workspace):
        raise Refused('invalid_input:token_file:inside_workspace', token_file)
    key = os.path.realpath(str(owner_key))
    if not os.path.isfile(key):
        raise Refused('invalid_input:owner_key:absent', 'the owner key is his OpenSSH private key file')
    owner_public = public_key(key)
    ACT, AC = organ('control_channel_activation'), organ('authority_contract')
    probe = b'veldo.factory_setup.owner_probe/v1'
    try:
        signed = ACT.ssh_signer(key)(probe)
    except ACT.Refused:
        signed = ''
    if not AC.ssh_keygen_verify(probe, signed, AC.allowed_signers_line(owner, owner_public), owner)[0]:
        raise Refused('invalid_input:owner_key:does_not_sign', 'the owner key does not sign as its public key')
    keys = os.path.join(root, KEYS_DIR)
    located = [p for p in CS.key_directory_problems(keys, CS.worker_writable() if writable is None else writable)
               if not p.endswith(':absent')]
    if located:
        raise Refused(located[0], keys)
    store = os.path.join(root, STORE_DIR, STORE_NAME)
    if len(os.fsencode(os.path.join(os.path.dirname(store), organ('control_client').SOCKET_NAME))) >= CS.SOCKET_PATH_LIMIT:
        raise Refused('invalid_input:socket:too_long', 'the state root path is too long for the service socket')
    install_root = os.path.realpath(str(install_root or CS.default_install_root()))
    if _within(install_root, workspace) or _within(workspace, install_root):
        raise Refused('invalid_input:install_root:inside_workspace', install_root)
    profile = CS.host_profile(install_root) if profile is None else profile
    qualification = CS.C.qualify(profile)
    if not qualification['qualified']:
        raise Refused(qualification['refusal'], 'the worker profile is not qualified on this host')
    if not isinstance(origin, str) or ACT.platform_of(origin) is None:
        raise Refused('invalid_input:origin', 'the Bot API origin is the Telegram service')
    host_identity = re.sub(r'[^A-Za-z0-9._-]', '-', platform.node() or '') or 'veldo-host'
    return dict(root=root, owner=owner, owner_key=key, owner_public=owner_public, workspace=workspace, chat=chat,
                token_file=token_file, host_trust=str(host_trust), install_root=install_root,
                unit_dir=unit_dir, profile=profile, writable=writable, origin=origin, host_identity=host_identity,
                keys=keys, store=store)


# ---------------------------------------------------------------------------------------------
# The setup
# ---------------------------------------------------------------------------------------------

class _Step:
    """Names the step a failure after the first write happened in; the setup never deletes."""

    def __init__(self, done):
        self.done, self.name = done, None

    def __call__(self, name):
        self.name = name
        return self

    def __enter__(self):
        return self

    def __exit__(self, kind, value, trace):
        if kind is None:
            self.done.append(self.name)
            return False
        if issubclass(kind, Refused):
            raise Refused('setup_incomplete:%s:%s' % (self.name, value.code), 'written so far: %s' % self.done) from value
        if issubclass(kind, Exception):
            raise Refused('setup_incomplete:%s:%s' % (self.name, getattr(value, 'code', kind.__name__)),
                          'written so far: %s' % self.done) from value
        return False


def setup(state_root, owner, owner_key, workspace, chat, token_file, *, host_trust=None, install_root=None,
          unit_dir=None, profile=None, writable=None, runner=None, origin=TELEGRAM_ORIGIN, clock=time.time):
    """Lay the factory down; returns what was laid down. Refused by name, writing nothing, when a check fails."""
    EL = organ('control_eligibility')
    plan = check(state_root, owner, owner_key, workspace, chat, token_file,
                 host_trust=host_trust or EL.host_trust_path(), install_root=install_root, unit_dir=unit_dir,
                 profile=profile, writable=writable, origin=origin)
    claims, K, E, CE = organ('control_claim'), organ('control_keys'), organ('control_channel_enrollment'), organ('control_enrollment')
    IN, CS, ACT = organ('control_channel_ingress'), organ('control_service'), organ('control_channel_activation')
    S, CM, AC = claims.S, claims.CM, claims.AC
    root, keys, owner, workspace = plan['root'], plan['keys'], plan['owner'], plan['workspace']
    owner_sign = ACT.ssh_signer(plan['owner_key'])
    owner_public = plan['owner_public']
    done = []
    step = _Step(done)
    ids = {'domain_uuid': str(uuid.uuid4()), 'repository_uuid': str(uuid.uuid4()), 'store_uuid': str(uuid.uuid4())}
    host = os.path.join(root, HOST_DIR)
    projection = os.path.join(host, 'allowed_signers')
    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return 'setup-%s-%s-%d' % (prefix, ids['store_uuid'][:8], serial[0])

    with step('directories'):
        for name in (STORE_DIR, KEYS_DIR, EDGE_DIR, HOST_DIR):
            os.mkdir(os.path.join(root, name), 0o700)
            os.chmod(os.path.join(root, name), 0o700)
    with step('keys'):
        public = {'journal': _keygen(os.path.join(keys, JOURNAL_KEY), 'veldo-journal'),
                  'edge': _keygen(os.path.join(keys, E.edge_key_id(CHANNEL)), 'veldo-edge-telegram'),
                  'settlement': _keygen(os.path.join(keys, SETTLEMENT_KEY), 'veldo-settlement'),
                  'connection': _keygen(os.path.join(root, EDGE_DIR, CONNECTION_KEY), 'veldo-edge-connection'),
                  'requester': _keygen(os.path.join(keys, REQUESTER_KEY), 'veldo-qualification-requester')}
        journal_principal, journal_sign = IN.journal_signer({'principal': JOURNAL_PRINCIPAL,
                                                             'key': os.path.join(keys, JOURNAL_KEY)})
    conn = None

    def envelope(command, principal):
        now = CM.authority_state(S, conn)
        return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                    request_revision=1, nonce='nonce-' + command['command_id'], expires_at=clock() + 600,
                    membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                    command_digest=AC.canonical_command_digest(command))

    def admin(operation, params, sign=owner_sign, enrollee=None):
        command = {'command_id': next_id(operation), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, owner)
        cosigned = None if enrollee is None else enrollee(AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
        return CM.admit(S, conn, env, command, sign(AC.canonical_envelope_bytes(env)), ids, clock(),
                        enrollee_signature=cosigned, journal_signer=(journal_principal, journal_sign))

    try:
        with step('store'):
            # The store file is created 0600 before SQLite opens it; its WAL and shared-memory files take
            # the same mode.
            os.close(os.open(plan['store'], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600))
            os.chmod(plan['store'], 0o600)
            conn = S.open_store(plan['store'])
            CM.attach(S)
            K.attach(S)
        with step('owner_bootstrap'):
            # The genesis: the owner enrolls himself, signed with the key being enrolled (R37).
            admit_owner = admin('enroll_principal', {'principal': owner, 'principal_type': 'person', 'roles': OWNER_ROLES,
                                                     'public_key': owner_public, 'independence_group': owner, 'scope': '*'})
            K.publish(S, conn, projection)
            os.chmod(projection, 0o600)
        with step('chat_enrollment'):
            eid = 'channel-enrollment:%s:%s' % (CHANNEL, owner)
            S.execute(conn, dict(command_id=next_id('chat'), principal=journal_principal, operation='upsert_entity',
                                 parameters=dict(entity_id=eid, kind='channel_enrollment',
                                                 data=dict(schema='veldo.channel_enrollment/v1', channel=CHANNEL,
                                                           principal=owner, chat_id=plan['chat'], revoked_at=None)),
                                 expected_versions={eid: 0}, artifact_digests=[], nonce=next_id('chat-nonce')),
                      journal_principal, journal_sign, 1)
        with step('edge_enrollment'):
            enrollment = E.Enrollment(S, conn, ids, journal_principal, journal_sign, projection=projection)
            command = {'command_id': next_id('edge'), 'operation': E.ENROLL, 'target': E.target(CHANNEL),
                       'parameters': {'channel': CHANNEL, 'edge_principal': EDGE_PRINCIPAL,
                                      'edge_key_id': E.edge_key_id(CHANNEL), 'public_key': public['edge'],
                                      'connection_public_key': public['connection'], 'scope': ['*']},
                       'artifact_digests': [], 'expected_versions': {}}
            env = envelope(command, owner)
            possession = ACT.ssh_signer(os.path.join(keys, E.edge_key_id(CHANNEL)), E.POSSESSION_NAMESPACE)(
                AC.canonical_envelope_bytes(env))
            observed = enrollment.admit(env, command, owner_sign(AC.canonical_envelope_bytes(env)), possession)
            if observed.get('outcome') != 'accepted':
                raise Refused('edge_enrollment_refused:%s' % observed.get('refusal'))
            os.chmod(projection, 0o600)
        with step('delegation'):
            admin('grant_delegation', {'id': next_id('delegation'), 'principal': owner, 'channel': CHANNEL,
                                       'assertion_kinds': ['decision_answer', 'review_disposition'],
                                       'authority_scope': ['*'], 'request_version': None, 'presentation_version': None,
                                       'expires_at': clock() + DELEGATION_DAYS * 86400,
                                       'edge_key_id': E.edge_key_id(CHANNEL)})
        with step('requester_enrollment'):
            # The factory's qualification requester, enrolled by his signed command with its key's
            # possession co-signature; the projection the protected signer reads is republished here.
            admin('enroll_principal', {'principal': REQUESTER, 'principal_type': 'service', 'roles': [],
                                       'public_key': public['requester'], 'independence_group': REQUESTER,
                                       'scope': [REQUESTER_SCOPE]},
                  enrollee=ACT.ssh_signer(os.path.join(keys, REQUESTER_KEY)))
            K.publish(S, conn, projection)
            os.chmod(projection, 0o600)
        with step('host_trust'):
            enrollment_signers = _private(os.path.join(host, 'enrollment_signers'), '%s namespaces="%s" %s\n'
                                          % (owner, organ('control_eligibility').ENROLLMENT_NAMESPACE, owner_public))
            settlement_signers = _private(os.path.join(host, 'settlement_signers'), '%s namespaces="%s" %s\n'
                                          % (SETTLEMENT_PRINCIPAL, organ('control_decision_dependency').SETTLEMENT_NAMESPACE,
                                             public['settlement']))
            os.makedirs(os.path.dirname(plan['host_trust']), mode=0o700, exist_ok=True)
            _private(plan['host_trust'], json.dumps({'schema': EL.HOST_TRUST_SCHEMA, 'host_identity': plan['host_identity'],
                                                     'enrollment_signers': enrollment_signers,
                                                     'settlement_signers': settlement_signers}, indent=1, sort_keys=True) + '\n')
        with step('workspace_enrollment'):
            binding = CE.enroll(workspace, ids['domain_uuid'], ids['store_uuid'], plan['store'], plan['host_identity'], 1,
                                ACT.ssh_signer(plan['owner_key'], EL.ENROLLMENT_NAMESPACE), owner, clock(),
                                repository_uuid=ids['repository_uuid'])
        with step('ingress_configuration'):
            signer_config = _private(os.path.join(host, 'signer.json'), json.dumps(
                {'store': plan['store'], 'repository': workspace, 'allowed_signers': projection, 'key_directory': keys,
                 'authority_ids': ids}, indent=1, sort_keys=True) + '\n')
            ingress = _private(os.path.join(host, 'ingress.json'), json.dumps(
                {'schema': IN.CONFIG_SCHEMA, 'channel': CHANNEL, 'store_path': plan['store'], 'authority_ids': ids,
                 'authority_generation': 1, 'journal': {'principal': JOURNAL_PRINCIPAL, 'key': os.path.join(keys, JOURNAL_KEY)},
                 'workspace': workspace, 'host_trust': plan['host_trust'],
                 'signer': {'config': signer_config, 'edge_key_id': E.edge_key_id(CHANNEL),
                            'connection_key': os.path.join(root, EDGE_DIR, CONNECTION_KEY)},
                 'edge_principal': EDGE_PRINCIPAL, 'api_edge': API_EDGE,
                 'bot_api': {'origin': plan['origin'], 'token_file': plan['token_file']},
                 'decision_signer': {'principal': SETTLEMENT_PRINCIPAL, 'key': os.path.join(keys, SETTLEMENT_KEY)}},
                indent=1, sort_keys=True) + '\n')
            # The configuration is the one the ingress is constructed from, read back as it reads it: its
            # fields, the token file, the journal key and the decision key the host trust names. The ingress
            # itself is never opened here: its organs bind the store's owned entities to the code that first
            # attaches them, which must be the installed service's.
            config = IN.load_config(ingress)
            IN.read_token(config['bot_api']['token_file'])
            IN.journal_signer(config['journal'])
            IN.decision_signer(config, EL.load_host_trust(plan['host_trust']).settlement_trust(workspace))
        with step('service_install'):
            installed = CS.install([workspace], host_trust=plan['host_trust'], key_directory=keys,
                                   install_root=plan['install_root'], unit_dir=plan['unit_dir'], profile=plan['profile'],
                                   writable=plan['writable'], runner=runner, channel_ingress=ingress)
        genesis = S.export_journal(conn)[0]
    finally:
        if conn is not None:
            conn.close()
    return {'schema': SCHEMA, 'outcome': 'set_up', 'state_root': root, 'store': plan['store'], 'authority_ids': ids,
            'owner': owner, 'owner_key_digest': 'sha256:' + __import__('hashlib').sha256(owner_public.encode()).hexdigest(),
            'genesis': {'command_id': genesis.get('command_id'), 'principal': genesis.get('principal'),
                        'seq': admit_owner.get('seq') if isinstance(admit_owner, dict) else None},
            'host_trust': plan['host_trust'], 'host_identity': plan['host_identity'],
            'workspace': workspace, 'binding_digest': binding.get('binding_digest'), 'chat_enrolled': True,
            'edge_key': os.path.join(keys, E.edge_key_id(CHANNEL)), 'ingress': ingress,
            'token_file': plan['token_file'], 'unit': installed['unit'], 'unit_path': installed['unit_path'],
            'home': installed['home'], 'started': False, 'steps': done, 'qualification_requester': REQUESTER,
            'next': 'start it explicitly: systemctl --user start %s, then veldo channel qualify' % installed['unit']}


def main(argv=None, **overrides):
    """veldo factory setup --state-root DIR --owner NAME --owner-key FILE --workspace CLONE --chat ID
    --token-file FILE. Prints one JSON answer; exit 0 set up, 1 refused by name, 2 usage."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(prog='veldo factory setup', description='Lay a real factory down on this host '
                                     'from the owner\'s own signed commands.')
    parser.add_argument('action', choices=('setup',))
    parser.add_argument('--state-root', required=True, help='an empty 0700 directory of this account')
    parser.add_argument('--owner', required=True, help='the owner\'s principal name')
    parser.add_argument('--owner-key', required=True, help='his OpenSSH private key file; it signs, it is never read here')
    parser.add_argument('--workspace', required=True, help='the Git clone the factory serves')
    parser.add_argument('--chat', required=True, type=int, help='his numeric Telegram user id')
    parser.add_argument('--token-file', required=True, help='this account\'s own 0600 bot token file; named, never copied')
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE

    def answer(value, code):
        print(json.dumps(value, sort_keys=True))
        return code
    try:
        report = setup(args.state_root, args.owner, args.owner_key, args.workspace, args.chat, args.token_file,
                       **overrides)
    except Refused as exc:
        return answer({'action': 'setup', 'outcome': 'refused', 'reason': exc.code, 'problems': exc.problems,
                       'detail': exc.detail}, EXIT_REFUSED)
    return answer(dict(report, action='setup'), 0)


if __name__ == '__main__':
    raise SystemExit(main())
