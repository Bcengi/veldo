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
import sys
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
          profile, writable, origin, rerun=False):
    """Every precondition, as a plan the setup then carries out, or Refused naming the first problem. With
    `rerun` the state root holds a store laid down before, and the host trust file and the workspace binding
    it wrote are expected (rerun() then compares them with this run's arguments)."""
    CS, E, IN, S = organ('control_service'), organ('control_enrollment'), organ('control_channel_ingress'), organ('control_store')
    problems = state_root_problems(state_root)
    if problems and not (rerun and problems == ['invalid_input:state_root:holds_store']):
        raise Refused(problems[0], str(state_root), problems)
    root = os.path.realpath(str(state_root))
    if S.filesystem_problems(root):
        raise Refused('invalid_input:state_root:filesystem', root)
    if not isinstance(owner, str) or not PLAIN.fullmatch(owner) or owner in RESERVED:
        raise Refused('invalid_input:owner:name', 'the owner is a plain principal name, not a service principal')
    if type(chat) is not int or chat <= 0:
        raise Refused('invalid_input:chat:not_a_user_id', 'the chat is the owner\'s numeric Telegram user id')
    if not rerun and os.path.lexists(host_trust):
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
    if not rerun and (E.read_binding(workspace) is not None or os.path.lexists(E.binding_path(workspace))):
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
# What the file steps write, built once for the first run and for every re-run's comparison
# ---------------------------------------------------------------------------------------------

def host_files(plan, settlement_public):
    """The host trust and the two signer files it names: {path: text}."""
    host = os.path.join(plan['root'], HOST_DIR)
    enrollment_signers, settlement_signers = os.path.join(host, 'enrollment_signers'), os.path.join(host, 'settlement_signers')
    return {enrollment_signers: '%s namespaces="%s" %s\n' % (plan['owner'], organ('control_eligibility').ENROLLMENT_NAMESPACE,
                                                             plan['owner_public']),
            settlement_signers: '%s namespaces="%s" %s\n' % (SETTLEMENT_PRINCIPAL,
                                                             organ('control_decision_dependency').SETTLEMENT_NAMESPACE,
                                                             settlement_public),
            plan['host_trust']: json.dumps({'schema': organ('control_eligibility').HOST_TRUST_SCHEMA,
                                            'host_identity': plan['host_identity'],
                                            'enrollment_signers': enrollment_signers,
                                            'settlement_signers': settlement_signers}, indent=1, sort_keys=True) + '\n'}


def ingress_files(plan, ids):
    """The protected signer's configuration and the VELDO-0073 ingress configuration: {path: text}."""
    E, IN = organ('control_channel_enrollment'), organ('control_channel_ingress')
    root, keys, workspace = plan['root'], plan['keys'], plan['workspace']
    host = os.path.join(root, HOST_DIR)
    projection, signer_config = os.path.join(host, 'allowed_signers'), os.path.join(host, 'signer.json')
    return {signer_config: json.dumps({'store': plan['store'], 'repository': workspace, 'allowed_signers': projection,
                                       'key_directory': keys, 'authority_ids': ids}, indent=1, sort_keys=True) + '\n',
            os.path.join(host, 'ingress.json'): json.dumps(
                {'schema': IN.CONFIG_SCHEMA, 'channel': CHANNEL, 'store_path': plan['store'], 'authority_ids': ids,
                 'authority_generation': 1, 'journal': {'principal': JOURNAL_PRINCIPAL, 'key': os.path.join(keys, JOURNAL_KEY)},
                 'workspace': workspace, 'host_trust': plan['host_trust'],
                 'signer': {'config': signer_config, 'edge_key_id': E.edge_key_id(CHANNEL),
                            'connection_key': os.path.join(root, EDGE_DIR, CONNECTION_KEY)},
                 'edge_principal': EDGE_PRINCIPAL, 'api_edge': API_EDGE,
                 'bot_api': {'origin': plan['origin'], 'token_file': plan['token_file']},
                 'decision_signer': {'principal': SETTLEMENT_PRINCIPAL, 'key': os.path.join(keys, SETTLEMENT_KEY)}},
                indent=1, sort_keys=True) + '\n'}


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
          unit_dir=None, profile=None, writable=None, runner=None, origin=TELEGRAM_ORIGIN, clock=time.time,
          tailscale=None, api_port=None):
    """Lay the factory down, or complete one laid down with these same arguments (rerun). Returns what
    was laid down; refused by name, writing nothing, when a check fails. `tailscale` is the list of
    system paths the Tailscale CLI is looked for at (TAILSCALE_PATHS), `api_port` the API's loopback port."""
    EL, API = organ('control_eligibility'), organ('control_factory_setup_api')
    options = dict(host_trust=host_trust or EL.host_trust_path(), install_root=install_root, unit_dir=unit_dir,
                   profile=profile, writable=writable, origin=origin)
    port = API.PORT if api_port is None else api_port
    runner = runner or organ('control_service').Systemctl()
    if state_root_problems(state_root) == ['invalid_input:state_root:holds_store']:
        return rerun(state_root, owner, owner_key, workspace, chat, token_file, runner=runner, clock=clock,
                     tailscale=tailscale, port=port, **options)
    plan = check(state_root, owner, owner_key, workspace, chat, token_file, **options)
    # Tailscale is read, with read-only commands, after every other check and before the first write.
    cli = _api(lambda: API.Tailscale(tailscale))
    transport = _api(lambda: API.transport(cli, port))
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
    conn, lock = None, None

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
            # Setup writes the store only while it holds the store's lock itself (AC1 of VELDO-0171).
            lock = take_lock(root)
            if lock is None:
                raise Refused('invalid_input:state_root:service_running:store', 'another process holds the store lock')
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
            texts = host_files(plan, public['settlement'])
            for path in (os.path.join(host, 'enrollment_signers'), os.path.join(host, 'settlement_signers')):
                _private(path, texts[path])
            os.makedirs(os.path.dirname(plan['host_trust']), mode=0o700, exist_ok=True)
            _private(plan['host_trust'], texts[plan['host_trust']])
        with step('workspace_enrollment'):
            binding = CE.enroll(workspace, ids['domain_uuid'], ids['store_uuid'], plan['store'], plan['host_identity'], 1,
                                ACT.ssh_signer(plan['owner_key'], EL.ENROLLMENT_NAMESPACE), owner, clock(),
                                repository_uuid=ids['repository_uuid'])
        with step('ingress_configuration'):
            texts = ingress_files(plan, ids)
            signer_config = _private(os.path.join(host, 'signer.json'), texts[os.path.join(host, 'signer.json')])
            ingress = _private(os.path.join(host, 'ingress.json'), texts[os.path.join(host, 'ingress.json')])
            # The configuration is the one the ingress is constructed from, read back as it reads it: its
            # fields, the token file, the journal key and the decision key the host trust names. The ingress
            # itself is never opened here: its organs bind the store's owned entities to the code that first
            # attaches them, which must be the installed service's.
            config = IN.load_config(ingress)
            IN.read_token(config['bot_api']['token_file'])
            IN.journal_signer(config['journal'])
            IN.decision_signer(config, EL.load_host_trust(plan['host_trust']).settlement_trust(workspace))
        api_files = paths(root, keys, None, plan['unit_dir'], None)
        with step('api_edge_key'):
            API.generate_keys(api_files['key'], api_files['connection_key'])
        with step('api_edge_enrollment'):
            enroll_api_edge(plan, ids, S, conn, (journal_principal, journal_sign), owner_sign, envelope, next_id, projection)
            os.chmod(projection, 0o600)
        with step('api_service_configuration'):
            api_service = _private(api_files['service_config'], api_service_text(plan, ids, transport['name']))
        with step('service_install'):
            installed = CS.install([workspace], host_trust=plan['host_trust'], key_directory=keys,
                                   install_root=plan['install_root'], unit_dir=plan['unit_dir'], profile=plan['profile'],
                                   writable=plan['writable'], runner=runner, channel_ingress=ingress,
                                   api_service=api_service)
        genesis = S.export_journal(conn)[0]
    finally:
        if conn is not None:
            conn.close()
        if lock is not None:
            os.close(lock)
    api_files = paths(root, keys, installed['home'], plan['unit_dir'], installed['unit'])
    python = json.loads(Path(installed['config']).read_text())['python']
    with step('api_process_configuration'):
        _private(api_files['process_config'], api_process_text(plan, ids, api_files, transport['name'], port))
    with step('api_unit'):
        install_api_unit(api_files, installed['unit'], python, runner)
    with step('tailscale_serve'):
        if transport['serve'] == 'free':
            _api(lambda: API.serve(cli, transport['name'], port))
    return {'schema': SCHEMA, 'outcome': 'set_up', 'state_root': root, 'store': plan['store'], 'authority_ids': ids,
            'owner': owner, 'owner_key_digest': 'sha256:' + __import__('hashlib').sha256(owner_public.encode()).hexdigest(),
            'genesis': {'command_id': genesis.get('command_id'), 'principal': genesis.get('principal'),
                        'seq': admit_owner.get('seq') if isinstance(admit_owner, dict) else None},
            'host_trust': plan['host_trust'], 'host_identity': plan['host_identity'],
            'workspace': workspace, 'binding_digest': binding.get('binding_digest'), 'chat_enrolled': True,
            'edge_key': os.path.join(keys, E.edge_key_id(CHANNEL)), 'ingress': ingress,
            'token_file': plan['token_file'], 'unit': installed['unit'], 'unit_path': installed['unit_path'],
            'home': installed['home'], 'started': False, 'qualification_requester': REQUESTER,
            'steps': [{'step': name, 'outcome': 'done'} for name in done]
            + [{'step': 'api_start', 'outcome': 'deferred'}],
            'api': api_report(transport['name'], port, api_files, through_service=False),
            'next': 'start it explicitly: systemctl --user start %s (the API unit %s starts with it), then veldo channel '
                    'qualify' % (installed['unit'], api_files['unit'])}


# ---------------------------------------------------------------------------------------------
# The API steps (VELDO-0171), shared by the first run and every re-run
# ---------------------------------------------------------------------------------------------

def _api(call):
    """Run one call into control_factory_setup_api, its refusal kept by name as this module's. (Each load of
    that module by path is a module of its own, so its Refused is recognized by name, not by identity.)"""
    try:
        return call()
    except Refused:
        raise
    except Exception as exc:
        if type(exc).__name__ == 'Refused' and isinstance(getattr(exc, 'code', None), str):
            raise Refused(exc.code, getattr(exc, 'detail', '')) from None
        raise


def _differs(path):
    return Refused('invalid_input:state_root:differs:' + str(path), 'an existing file this run would write differently')


def take_lock(root, create=True):
    """The store's lock (authority.lock beside it), held exclusively by this run: whoever holds it is the
    store's only writer. None when another process, the running authority service, holds it; with `create`
    False, -1 when there is no lock file (no service ever ran, so nobody holds it)."""
    import fcntl
    path = os.path.join(root, STORE_DIR, organ('control_service').LOCK_NAME)
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | (os.O_CREAT if create else 0), 0o600)
    except FileNotFoundError:
        return -1
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def paths(root, keys, home, unit_dir, unit):
    """Every path the API steps own. `home` and `unit` are the installation's (None before it exists)."""
    API, E = organ('control_factory_setup_api'), organ('control_channel_enrollment')
    found = {'key': os.path.join(keys, E.edge_key_id(API.CHANNEL)),
             'connection_key': os.path.join(root, EDGE_DIR, API.CONNECTION_KEY),
             'service_config': os.path.join(root, HOST_DIR, API.SERVICE_CONFIG),
             'state_dir': os.path.join(root, API.STATE_DIR)}
    if home is not None and unit is not None:
        name = API.UNIT_PREFIX + unit[len(organ('control_client').SERVICE_PREFIX):]
        found.update(installed_service_config=os.path.join(home, 'config', API.SERVICE_CONFIG),
                     process_config=os.path.join(home, 'config', API.PROCESS_CONFIG),
                     service_json=os.path.join(home, 'config', 'service.json'),
                     executable=os.path.join(home, 'bin', API.API_EXECUTABLE), unit=name,
                     unit_path=os.path.join(unit_dir, name), wants=os.path.join(unit_dir, unit + '.wants', name))
    return found


def api_service_text(plan, ids, name):
    API = organ('control_factory_setup_api')
    return API.text(API.service_config(plan['store'], ids, {'principal': JOURNAL_PRINCIPAL,
                                                            'key': os.path.join(plan['keys'], JOURNAL_KEY)},
                                       API_EDGE, plan['workspace'], name))


def api_process_text(plan, ids, api, name, port):
    API, E = organ('control_factory_setup_api'), organ('control_channel_enrollment')
    return API.text(API.process_config(ids, plan['workspace'], plan['host_trust'],
                                       os.path.join(plan['root'], HOST_DIR, 'signer.json'), E.edge_key_id(API.CHANNEL),
                                       api['connection_key'], API_EDGE, api['state_dir'], name, port))


def enroll_api_edge(plan, ids, S, conn, journal, owner_sign, envelope, next_id, projection):
    """The owner's enroll_channel_edge of the api edge with the key's possession co-signature, admitted on
    this run's own store connection (it holds the lock); the projection is republished by the admission."""
    API, E, ACT, AC = organ('control_factory_setup_api'), organ('control_channel_enrollment'), organ('control_channel_activation'), organ('authority_contract')
    api = paths(plan['root'], plan['keys'], None, None, None)
    command = API.enrollment_command(next_id('api-edge'), API_EDGE, E.edge_key_id(API.CHANNEL), API.derived(api['key']),
                                     API.derived(api['connection_key']))
    env = envelope(command, plan['owner'])
    possession = ACT.ssh_signer(api['key'], E.POSSESSION_NAMESPACE)(AC.canonical_envelope_bytes(env))
    observed = E.Enrollment(S, conn, ids, journal[0], journal[1], projection=projection).admit(
        env, command, owner_sign(AC.canonical_envelope_bytes(env)), possession)
    if observed.get('outcome') != 'accepted':
        raise Refused('edge_enrollment_refused:%s' % observed.get('refusal'))
    return observed


def enroll_api_edge_through_service(plan, owner_sign, clock, serial):
    """The same signed enrollment sent to the running authority service over its socket, as every client
    reaches it (it holds the lock). Returns the service's answer."""
    API, E, ACT, AC = organ('control_factory_setup_api'), organ('control_channel_enrollment'), organ('control_channel_activation'), organ('authority_contract')
    CC, CE, EL = organ('control_client'), organ('control_enrollment'), organ('control_eligibility')
    workspace = plan['workspace']
    trust, binding = EL.load_host_trust(plan['host_trust']), CE.read_binding(workspace)
    verify = trust.verifier(binding.get('enrolled_by'), workspace)

    def send(packet):
        try:
            answer = CC.send(workspace, packet, CE, verify, owner_sign, trust.host_identity, timeout=60)
        except CC.RoutingRefused as exc:
            raise Refused('unavailable_service:authority:' + exc.reason, 'the running service did not answer') from None
        if not answer.get('accepted'):
            raise Refused('edge_enrollment_refused:%s' % answer.get('reason'), 'the running service refused the request')
        return answer.get('result') or {}
    status = send({'operation': 'inspect', 'entity_ids': []}).get('channel') or {}
    if not status.get('available'):
        raise Refused('invalid_input:state_root:service_running:api_edge_enrollment',
                      'the running service reports no authority versions to sign against')
    api = paths(plan['root'], plan['keys'], None, None, None)
    ids = status.get('authority_ids') or {}
    command = API.enrollment_command('setup-api-edge-%s-%s' % (str(ids.get('store_uuid'))[:8], serial), API_EDGE,
                                     E.edge_key_id(API.CHANNEL), API.derived(api['key']), API.derived(api['connection_key']))
    env = dict({k: ids.get(k) for k in ('domain_uuid', 'repository_uuid', 'store_uuid')}, schema=AC.ENVELOPE_SCHEMA,
               command_id=command['command_id'], principal=plan['owner'], request_revision=1,
               nonce='nonce-' + command['command_id'], expires_at=clock() + 600,
               membership_version=status.get('membership_version'), delegation_version=status.get('delegation_version'),
               command_digest=AC.canonical_command_digest(command))
    possession = ACT.ssh_signer(api['key'], E.POSSESSION_NAMESPACE)(AC.canonical_envelope_bytes(env))
    result = send({'command': command, 'envelope': env, 'signature': owner_sign(AC.canonical_envelope_bytes(env)),
                   'possession': possession})
    if not result.get('ok'):
        raise Refused('edge_enrollment_refused:%s' % result.get('reason'), 'the running service refused the enrollment')
    return result


def install_api_unit(api, authority_unit, python, runner, states=None):
    """The API unit and the authority unit's want of it, each written only when absent; True when written."""
    API = organ('control_factory_setup_api')
    body = _api(lambda: API.unit_text(authority_unit, python, api['executable'], api['process_config']))
    wrote = False
    if states is None or states['unit'] == 'absent':
        API.write_new(api['unit_path'], body, 0o644)
        wrote = True
    if states is None or states['wants'] == 'absent':
        os.makedirs(os.path.dirname(api['wants']), mode=0o755, exist_ok=True)
        os.symlink(os.path.join('..', api['unit']), api['wants'])
        wrote = True
    if wrote:
        runner.run(['daemon-reload'])
    return wrote


def api_report(name, port, api, through_service):
    return {'tailnet_name': name, 'origin': 'https://' + name, 'listen': '%s:%d' % ('127.0.0.1', port), 'port': port,
            'unit': api.get('unit'), 'unit_path': api.get('unit_path'), 'service_config': api.get('service_config'),
            'process_config': api.get('process_config'), 'store_write_through_service': through_service}


# The steps VELDO-0139 laid down, in its order; a re-run reports each of them.
BASE_STEPS = ('directories', 'keys', 'store', 'owner_bootstrap', 'chat_enrollment', 'edge_enrollment', 'delegation',
              'requester_enrollment', 'host_trust', 'workspace_enrollment', 'ingress_configuration', 'service_install')


def rerun(state_root, owner, owner_key, workspace, chat, token_file, *, host_trust, install_root, unit_dir, profile,
          writable, origin, runner, clock, tailscale, port):
    """A run over a state root laid down before. Accepted only when EVERY argument equals what the store and
    the installation were laid down with (else invalid_input:state_root:holds_<argument>). Every check runs
    before the first write: an earlier step is reported already done, a missing one is run, and an existing
    file that would differ is refused by name and never overwritten. The store is written only while this
    run holds its lock; while the authority service holds it, the api edge enrollment goes to the service
    and any other store write is refused (invalid_input:state_root:service_running:<step>)."""
    API, CS, CC, CE, E = (organ('control_factory_setup_api'), organ('control_service'), organ('control_client'),
                          organ('control_enrollment'), organ('control_channel_enrollment'))
    claims, K = organ('control_claim'), organ('control_keys')
    S, CM, AC = claims.S, claims.CM, claims.AC
    plan = check(state_root, owner, owner_key, workspace, chat, token_file, host_trust=host_trust,
                 install_root=install_root, unit_dir=unit_dir, profile=profile, writable=writable, origin=origin,
                 rerun=True)
    root, keys, workspace = plan['root'], plan['keys'], plan['workspace']
    host = os.path.join(root, HOST_DIR)
    try:
        laid = json.loads(Path(os.path.join(host, 'ingress.json')).read_text())
        ids = {k: laid['authority_ids'][k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid')}
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused('invalid_input:state_root:holds_store', 'a store without the configuration setup lays down with it') from None

    def holds(name):
        raise Refused('invalid_input:state_root:holds_' + name, 'the state root was laid down with another ' + name)
    now = clock()
    reader = S.open_store(plan['store'], mode='r')
    try:
        reader.execute('BEGIN')
        state = CM.authority_state(S, reader)
        row = reader.execute('SELECT data FROM entities WHERE id=?', ('channel-enrollment:%s:%s' % (CHANNEL, owner),)).fetchone()
        reader.execute('ROLLBACK')
    finally:
        reader.close()
    member = AC.membership_entry(state['membership'], owner)
    if not member or member.get('principal_type') != 'person':
        holds('owner')
    active = AC.active_key(state['keyring'], owner, now)
    if not active or active.get('public_key') != plan['owner_public']:
        holds('owner_key')
    try:
        binding = CE.read_binding(workspace)
    except (CE.EnrollmentRefused, OSError, ValueError):
        binding = None
    if (os.path.realpath(str(laid.get('workspace'))) != workspace or not isinstance(binding, dict)
            or binding.get('store_uuid') != ids['store_uuid'] or binding.get('store_path') != plan['store']):
        holds('workspace')
    if (json.loads(row[0]) if row else {}).get('chat_id') != plan['chat']:
        holds('chat')
    if (laid.get('bot_api') or {}).get('token_file') != plan['token_file']:
        holds('token_file')
    if laid.get('host_trust') != plan['host_trust']:
        holds('host_trust')
    if (laid.get('bot_api') or {}).get('origin') != plan['origin']:
        holds('origin')
    authority_unit, home = CC.service_unit(binding), os.path.join(plan['install_root'], CC.service_id(binding))
    try:
        installed = json.loads(Path(home, 'config', 'service.json').read_text())
    except (OSError, ValueError):
        installed = {}
    if installed.get('store_uuid') != ids['store_uuid']:
        holds('install_root')
    unit_dir = os.path.realpath(str(plan['unit_dir'] or CS.default_unit_dir()))
    if not os.path.isfile(os.path.join(unit_dir, authority_unit)):
        holds('unit_dir')
    profiles = []
    for path in sorted(((installed.get('receiver') or {}).get('configs') or {}).values()):
        try:
            profiles.append(json.loads(Path(path).read_text()).get('profile'))
        except (OSError, ValueError):
            profiles.append(None)
    if not profiles or any(p != json.loads(json.dumps(plan['profile'])) for p in profiles):
        holds('profile')

    # What VELDO-0139 committed to the store, read, never rewritten.
    telegram = E.edge_record(state, E.edge_key_id(CHANNEL))
    missing = [name for name, present in (
        ('edge_enrollment', telegram is not None and E.active(telegram, now)
         and telegram.get('public_key') == organ('control_factory_setup_api').derived(os.path.join(keys, E.edge_key_id(CHANNEL)))),
        ('delegation', any(d.get('principal') == owner and d.get('channel') == CHANNEL for d in state['delegations'])),
        ('requester_enrollment', AC.membership_entry(state['membership'], REQUESTER) is not None)) if not present]
    for path in (os.path.join(keys, JOURNAL_KEY), os.path.join(keys, E.edge_key_id(CHANNEL)), os.path.join(keys, SETTLEMENT_KEY),
                 os.path.join(keys, REQUESTER_KEY), os.path.join(root, EDGE_DIR, CONNECTION_KEY)):
        if not os.path.isfile(path):
            raise _differs(path)
    # The files the earlier steps wrote: equal ones are left alone, absent ones written, none overwritten.
    base = dict(host_files(plan, API.derived(os.path.join(keys, SETTLEMENT_KEY))), **ingress_files(plan, ids))
    base_states = {path: API.file_state(path, data, 0o600, _differs) for path, data in base.items()}
    # Tailscale, read-only, after every argument check and before the first write.
    cli = _api(lambda: API.Tailscale(tailscale))
    transport = _api(lambda: API.transport(cli, port))
    name = transport['name']
    api = paths(root, keys, home, unit_dir, authority_unit)
    edge = API.edge_state(state, api['key'], api['connection_key'], now, _differs)
    service_text = api_service_text(plan, ids, name)
    unit_body = _api(lambda: API.unit_text(authority_unit, installed.get('python') or '', api['executable'],
                                           api['process_config']))
    # VELDO-0189: the installed engine against the current one, from the installation's record, read only
    # here; the upgrade is the first step this run writes.
    engine = inspect_engine(plan, installed, home, unit_dir, (api['unit_path'], unit_body)
                            if os.path.lexists(api['unit_path']) else None)
    states = {'service_config': API.file_state(api['service_config'], service_text, 0o600, _differs),
              'installed_service_config': API.file_state(api['installed_service_config'], service_text, 0o600, _differs),
              'process_config': API.file_state(api['process_config'], api_process_text(plan, ids, api, name, port), 0o600,
                                               _differs),
              # An API unit the upgrade renders again from the current template is judged as that rendering.
              'unit': ('equal' if engine['state'] != 'current' and os.path.lexists(api['unit_path'])
                       else API.file_state(api['unit_path'], unit_body, 0o644, _differs)),
              'wants': API.link_state(api['wants'], api['unit'], _differs)}
    named = installed.get('api_service')
    if named is not None and named != api['installed_service_config']:
        raise _differs(api['service_json'])
    if not os.path.isfile(api['executable']) and API.API_EXECUTABLE not in engine['current']:
        raise Refused('unavailable_service:api:not_installed', 'the installed engine has no API process (%s)'
                      % api['executable'])
    lock = take_lock(root, create=False)
    running = lock is None
    try:
        if missing:
            if running:
                raise Refused('invalid_input:state_root:service_running:' + missing[0],
                              'the running service takes no command for this store write')
            raise Refused('invalid_input:state_root:holds_store', 'a store setup did not complete (%s)' % missing[0])
        # VELDO-0189: an earlier engine is replaced by the current one before any other step writes.
        upgraded = upgrade_engine(plan, engine, runner, running)
        installed = json.loads(Path(api['service_json']).read_text())
        outcomes = [upgraded] + [{'step': step, 'outcome': 'already_done'} for step in BASE_STEPS[:8]]

        def mark(step, wrote, **extra):
            outcomes.append(dict({'step': step, 'outcome': 'done' if wrote else 'already_done'}, **extra))

        def files(step, chosen):
            wrote = False
            for path in chosen:
                if base_states[path] == 'absent':
                    API.write_new(path, base[path], 0o600)
                    wrote = True
            mark(step, wrote)
        files('host_trust', [p for p in base if p == plan['host_trust'] or os.path.basename(p).endswith('_signers')])
        mark('workspace_enrollment', False)
        files('ingress_configuration', [p for p in base if os.path.basename(p) in ('signer.json', 'ingress.json')])
        mark('service_install', False)
        if edge == 'absent':
            API.generate_keys(api['key'], api['connection_key'])
        mark('api_edge_key', edge == 'absent')
        through = False
        projection = os.path.join(host, 'allowed_signers')
        if edge != 'enrolled':
            if running:
                enroll_api_edge_through_service(plan, organ('control_channel_activation').ssh_signer(plan['owner_key']),
                                                clock, uuid.uuid4().hex[:12])
                API.republish(S, CM, K, plan['store'], projection)
                through = True
            else:
                if lock == -1:
                    lock = take_lock(root)
                    if lock is None:
                        raise Refused('invalid_input:state_root:service_running:api_edge_enrollment',
                                      'the authority service started during this run')
                writer = S.open_store(plan['store'])
                try:
                    CM.attach(S)
                    K.attach(S)
                    IN = organ('control_channel_ingress')
                    journal = IN.journal_signer({'principal': JOURNAL_PRINCIPAL, 'key': os.path.join(keys, JOURNAL_KEY)})
                    serial = [0]

                    def next_id(prefix):
                        serial[0] += 1
                        return 'setup-%s-%s-%s-%d' % (prefix, ids['store_uuid'][:8], uuid.uuid4().hex[:8], serial[0])

                    def envelope(command, principal):
                        current = CM.authority_state(S, writer)
                        return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                                    request_revision=1, nonce='nonce-' + command['command_id'], expires_at=clock() + 600,
                                    membership_version=current['membership_version'],
                                    delegation_version=current['delegation_version'],
                                    command_digest=AC.canonical_command_digest(command))
                    enroll_api_edge(plan, ids, S, writer, journal, organ('control_channel_activation').ssh_signer(plan['owner_key']),
                                    envelope, next_id, projection)
                    os.chmod(projection, 0o600)
                finally:
                    writer.close()
        mark('api_edge_enrollment', edge != 'enrolled', through_service=through)
        if states['service_config'] == 'absent':
            API.write_new(api['service_config'], service_text, 0o600)
        mark('api_service_configuration', states['service_config'] == 'absent')
        added = named is None
        if states['installed_service_config'] == 'absent':
            SA = organ('control_service_api')
            try:
                SA.installable(api['service_config'], binding, installed.get('principal'), installed.get('journal_key'),
                               installed.get('repositories') or {}, installed.get('channel_ingress'))
            except SA.Refused as exc:
                raise Refused(exc.code, exc.detail) from None
            API.write_new(api['installed_service_config'], service_text, 0o600)
        if added:
            # The one change to an existing file: the installation's service configuration gains the key
            # it holds as null, naming the API configuration.
            API.replace_file(api['service_json'], CS._json(dict(installed, api_service=api['installed_service_config'])),
                             0o600)
        mark('api_service_install', added or states['installed_service_config'] == 'absent')
        if states['process_config'] == 'absent':
            API.write_new(api['process_config'], api_process_text(plan, ids, api, name, port), 0o600)
        mark('api_process_configuration', states['process_config'] == 'absent')
        mark('api_unit', install_api_unit(api, authority_unit, installed.get('python') or '', runner, states))
        started, next_step = False, None
        if running and not added:
            # VELDO-0189: a service the upgrade could not restart (it runs outside its unit) still runs the
            # previous engine, so nothing is started beside it; the answer names the one command to run.
            stale = upgraded.get('restart') == 'not_through_unit'
            if not stale and not API.service_running(runner, api['unit']):
                code, _out, err = runner.run(['start', api['unit']])
                if code or not API.service_running(runner, api['unit']):
                    raise Refused('unavailable_service:api', 'the API unit did not start (%s)' % err.strip()[:200])
                started = True
            if stale:
                outcomes.append({'step': 'api_start', 'outcome': 'deferred'})
                next_step = upgraded.get('next')
            else:
                mark('api_start', started)
        elif running:
            outcomes.append({'step': 'api_start', 'outcome': 'deferred'})
            next_step = ('the running service reads the API configuration when it starts: systemctl --user restart %s '
                         '(the API unit %s starts with it)' % (authority_unit, api['unit']))
        else:
            outcomes.append({'step': 'api_start', 'outcome': 'deferred'})
            next_step = 'start it explicitly: systemctl --user start %s (the API unit %s starts with it)' % (
                authority_unit, api['unit'])
        if transport['serve'] == 'free':
            _api(lambda: API.serve(cli, name, port))
        mark('tailscale_serve', transport['serve'] == 'free')
    finally:
        if lock is not None and lock != -1:
            os.close(lock)
    wrote = any(o['outcome'] == 'done' for o in outcomes)
    return {'schema': SCHEMA, 'outcome': 'set_up' if wrote else 'already_set_up', 'state_root': root,
            'store': plan['store'], 'authority_ids': ids, 'owner': owner, 'host_trust': plan['host_trust'],
            'workspace': workspace, 'ingress': os.path.join(host, 'ingress.json'), 'token_file': plan['token_file'],
            'unit': authority_unit, 'unit_path': os.path.join(unit_dir, authority_unit), 'home': home,
            'started': started, 'service_running': running, 'steps': outcomes,
            'api': api_report(name, port, api, through), 'next': next_step or upgraded.get('next')}


# ---------------------------------------------------------------------------------------------
# The engine upgrade (VELDO-0189), the first step of a re-run
# ---------------------------------------------------------------------------------------------

def inspect_engine(plan, installed, home, unit_dir, api_unit):
    """What the installed engine needs, read only: the current installer's rendering for this installation's
    arguments (control_service.layout) compared with the installation's record (control_factory_setup_upgrade)."""
    CS, UP = organ('control_service'), organ('control_factory_setup_upgrade')
    try:
        laid = CS.layout([plan['workspace']], host_trust=plan['host_trust'], key_directory=plan['keys'],
                         install_root=plan['install_root'], unit_dir=unit_dir, profile=plan['profile'],
                         writable=plan['writable'], principal=installed.get('principal') or JOURNAL_PRINCIPAL,
                         python=installed.get('python'),
                         channel_ingress=os.path.join(plan['root'], HOST_DIR, 'ingress.json'), existing=True)
    except CS.Refused as exc:
        raise Refused(exc.code, exc.detail) from None
    if laid['home'] != home:
        raise Refused('invalid_input:state_root:holds_install_root', 'the installation is not where its record is')
    engine = _api(lambda: UP.inspect(laid, installed, os.path.join(home, 'config', 'service.json'), api_unit))
    engine['module'] = UP
    return engine


def service_answers(plan):
    """A check that the running authority service answers an inspect over its socket, signed by the owner."""
    CC, CE, EL, ACT = organ('control_client'), organ('control_enrollment'), organ('control_eligibility'), organ(
        'control_channel_activation')
    workspace, owner_sign = plan['workspace'], ACT.ssh_signer(plan['owner_key'])
    trust, binding = EL.load_host_trust(plan['host_trust']), CE.read_binding(workspace)
    verify = trust.verifier(binding.get('enrolled_by'), workspace)

    def answers():
        try:
            answer = CC.send(workspace, {'operation': 'inspect', 'entity_ids': []}, CE, verify, owner_sign,
                             trust.host_identity, timeout=10)
        except Exception:
            return False
        return bool(answer.get('accepted'))
    return answers


def upgrade_engine(plan, engine, runner, running):
    """Carry out the inspected upgrade; its step of setup's answer."""
    CS, API, UP = organ('control_service'), organ('control_factory_setup_api'), engine['module']
    return _api(lambda: UP.run(engine, runner=runner, running=running, answers=service_answers(plan),
                               modes=CS.fixed_mode, bin_mode=CS.BIN_MODE,
                               is_active=lambda unit: API.service_running(runner, unit), stream=sys.stderr))


def main(argv=None, **overrides):
    """veldo factory setup --state-root DIR --owner NAME --owner-key FILE --workspace CLONE --chat ID
    --token-file FILE. Prints one JSON answer; exit 0 set up, 1 refused by name, 2 usage."""
    import argparse
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['passkey']:
        # veldo factory passkey (VELDO-0171): the owner signs the one pending registration he names.
        return organ('control_factory_setup_api').passkey_main(argv[1:])
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
        args = parser.parse_args(argv)
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
