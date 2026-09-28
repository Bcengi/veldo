#!/usr/bin/env python3
"""The API steps of veldo factory setup and the owner's `veldo factory passkey` (VELDO-0171).

WHAT THIS MODULE IS. The part of the owner's setup (control_factory_setup) that lays the VELDO-0130 API
down on the host and puts it behind Tailscale Serve, and the host command that signs the owner's first
passkey. Every step checks what is there before it writes: a file equal to what it would write is left
alone, an absent one is written, and an existing one that would differ is refused by name
(invalid_input:state_root:differs:<path>) and never overwritten. The steps, in order:

  api_edge_key          the api edge key (control_channel_enrollment.edge_key_id('api')) in the protected
                        key directory, and its connection key beside the Telegram edge's; kept when present;
  api_edge_enrollment   the owner's signed enroll_channel_edge for the ingress's api edge principal with the
                        key's possession co-signature, as setup enrolls the Telegram edge. Setup writes the
                        store only while it holds authority.lock itself; while the authority service holds
                        it, the command goes to the running service over its socket, and setup then
                        republishes the key projection from a read-only view of the store;
  api_service_configuration   host/api-service.json, veldo.api_service/v1, its rp_id the host's tailnet name
                        and its origin https://<that name>;
  api_service_install   the installation's copy (VELDO-0047's api_service option on a fresh host; on a host
                        laid down before, its config/api-service.json and service.json naming it);
  api_process_configuration   the 0600 veldo.api_process/v1 of the API process, listening on loopback only;
  api_unit              the systemd user unit rendered from services/veldo-api.service, which binds to the
                        authority unit, and the link that has the authority unit want it, so it starts and
                        stops with the authority service;
  api_start             the API unit started when the authority already runs with an installation that
                        already named the API configuration; otherwise nothing is restarted and the one
                        restart command is named;
  tailscale_serve       `tailscale serve --bg` mapping the tailnet name's HTTPS to the loopback port, never
                        Funnel, read back from the Serve status.

TAILSCALE. The CLI is resolved from a fixed list of system paths, never PATH. Before anything is written
setup reads, with read-only commands only: `status --json` (a running backend and this node's DNS name,
which is the tailnet name, and its certificate domains), `debug prefs` (OperatorUser: the account Serve
may be configured by without root), `serve --help` (whether it lists `--bg`, the background persistence)
and `serve status --json`. It refuses by name a missing or logged-out Tailscale (unavailable_service:tailscale),
no operator setting (unavailable_service:tailscale:operator), a tailnet name without an HTTPS certificate
domain (unavailable_service:tailscale:https), no `--bg` (unavailable_service:tailscale:persistence) and a
Serve mapping of the name's HTTPS that names another target or is funneled (invalid_input:tailscale_serve:occupied).

THE PASSKEY COMMAND. `veldo factory passkey --state-root DIR --owner NAME --owner-key FILE` lists the API's
pending registrations with each one's label, fingerprint and principal (control_api_credentials.describe);
with `--sign FINGERPRINT` it signs enroll_api_credential with the owner's key for the ONE pending
registration whose fingerprint that is, and sends it to the running authority service. An expired, unknown
or ambiguous fingerprint is refused by name and nothing is signed.

Observations carry paths, names, ports and fingerprints, never a key, a signature or a token. Standard
library only; every organ is loaded as a sibling by path.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('factory_setup_api_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The fixed system locations of the Tailscale CLI, in order; PATH is never searched.
TAILSCALE_PATHS = ('/usr/bin/tailscale', '/usr/sbin/tailscale', '/usr/local/bin/tailscale', '/bin/tailscale',
                   '/opt/homebrew/bin/tailscale', '/Applications/Tailscale.app/Contents/MacOS/Tailscale')
# The API process's loopback port, the one the Serve mapping names.
PORT = 8171
LOOPBACK = '127.0.0.1'
HTTPS_PORT = 443
CHANNEL = 'api'
CONNECTION_KEY = 'api-auth'
STATE_DIR = 'api'
SERVICE_CONFIG = 'api-service.json'
PROCESS_CONFIG = 'api-process.json'
UNIT_PREFIX = 'veldo-api-'
UNIT_SCHEMA = 'veldo.api_unit/v1'
TEMPLATE = Path(__file__).resolve().parent / 'services' / 'veldo-api.service'
API_EXECUTABLE = 'control_client_api.py'
# A tailnet name: a lower-case DNS name of at least two labels.
NAME = re.compile(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+')
UNIT_VALUE = re.compile(r'[A-Za-z0-9._/+-]+')
EXIT_REFUSED, EXIT_USAGE = 1, 2


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def _quiet_env():
    return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}


def _keygen(path, comment):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                   capture_output=True, timeout=30, stdin=subprocess.DEVNULL, env=_quiet_env())
    os.chmod(str(path), 0o600)


def derived(path):
    """The OpenSSH public key of a private key file, derived from it; None when it does not derive."""
    done = subprocess.run(['ssh-keygen', '-y', '-f', str(path)], capture_output=True, text=True, timeout=30,
                          stdin=subprocess.DEVNULL, env=_quiet_env())
    return ' '.join(done.stdout.split()[:2]) if done.returncode == 0 and done.stdout.strip() else None


def text(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


# ---------------------------------------------------------------------------------------------
# Tailscale: read-only checks before any write, then the one Serve mapping
# ---------------------------------------------------------------------------------------------

class Tailscale:
    """The Tailscale CLI at the first of `paths` that is an executable regular file; never PATH."""

    def __init__(self, paths=None):
        self.binary = None
        for path in (TAILSCALE_PATHS if paths is None else paths):
            if os.path.isabs(str(path)) and os.path.isfile(str(path)) and os.access(str(path), os.X_OK):
                self.binary = str(path)
                break
        if self.binary is None:
            raise Refused('unavailable_service:tailscale', 'no Tailscale CLI at the system locations')

    def run(self, args):
        try:
            done = subprocess.run([self.binary] + list(args), capture_output=True, text=True, timeout=60,
                                  stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            raise Refused('unavailable_service:tailscale', 'the Tailscale CLI did not answer') from None
        return done.returncode, done.stdout, done.stderr

    def json(self, args):
        code, out, _err = self.run(args)
        if code:
            raise Refused('unavailable_service:tailscale', 'tailscale %s exited %d' % (' '.join(args), code))
        try:
            return json.loads(out) if out.strip() else {}
        except ValueError:
            raise Refused('unavailable_service:tailscale', 'tailscale %s printed no JSON' % ' '.join(args)) from None


def target(port):
    return 'http://%s:%d' % (LOOPBACK, port)


def serve_state(served, name, port):
    """'ours' when the name's HTTPS already maps to the API's loopback port, 'free' when it maps nothing;
    any other mapping of it, or one Funnel publishes, is refused as occupied."""
    served = served if isinstance(served, dict) else {}
    key = '%s:%d' % (name, HTTPS_PORT)
    web = (served.get('Web') or {}).get(key)
    tcp = (served.get('TCP') or {}).get(str(HTTPS_PORT))
    funnel = bool((served.get('AllowFunnel') or {}).get(key))
    if web is None and tcp is None and not funnel:
        return 'free'
    if (not funnel and tcp == {'HTTPS': True}
            and web == {'Handlers': {'/': {'Proxy': target(port)}}}):
        return 'ours'
    raise Refused('invalid_input:tailscale_serve:occupied', 'the tailnet name\'s HTTPS already maps elsewhere')


def transport(cli, port):
    """Every Tailscale precondition, read-only: {'name', 'serve'} or Refused naming the first problem."""
    status = cli.json(['status', '--json'])
    own = status.get('Self') if isinstance(status.get('Self'), dict) else {}
    name = str(own.get('DNSName') or '').rstrip('.').lower()
    if status.get('BackendState') != 'Running' or not NAME.fullmatch(name):
        raise Refused('unavailable_service:tailscale', 'Tailscale is not running and logged in on this host')
    prefs = cli.json(['debug', 'prefs'])
    if os.getuid() != 0 and not (isinstance(prefs.get('OperatorUser'), str) and prefs['OperatorUser'].strip()):
        raise Refused('unavailable_service:tailscale:operator', 'no operator setting: this account cannot configure Serve')
    domains = [str(d).rstrip('.').lower() for d in status.get('CertDomains') or []]
    if name not in domains:
        raise Refused('unavailable_service:tailscale:https', 'the tailnet has no HTTPS certificate for this name')
    _code, out, err = cli.run(['serve', '--help'])
    if '--bg' not in (out + '\n' + err).replace('=', ' ').split():
        raise Refused('unavailable_service:tailscale:persistence', 'this Serve cannot keep a mapping in the background')
    return {'name': name, 'serve': serve_state(cli.json(['serve', 'status', '--json']), name, port)}


def serve(cli, name, port):
    """Map the name's HTTPS to the loopback port in the background, then read the mapping back."""
    code, _out, _err = cli.run(['serve', '--bg', '--https=%d' % HTTPS_PORT, target(port)])
    if code:
        raise Refused('unavailable_service:tailscale', 'tailscale serve --bg exited %d' % code)
    if serve_state(cli.json(['serve', 'status', '--json']), name, port) != 'ours':
        raise Refused('unavailable_service:tailscale', 'the Serve status does not show the mapping')


# ---------------------------------------------------------------------------------------------
# The files the API steps write, each checked before anything is written
# ---------------------------------------------------------------------------------------------

def file_state(path, data, mode, differs):
    """'absent', 'equal', or `differs(path)` raised: an existing file is never overwritten."""
    try:
        info = os.lstat(str(path))
    except FileNotFoundError:
        return 'absent'
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode
            or Path(path).read_text() != data):
        raise differs(str(path))
    return 'equal'


def write_new(path, data, mode):
    Path(path).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'w') as handle:
        handle.write(data)
    os.chmod(str(path), mode)


def replace_file(path, data, mode):
    """An atomic rewrite beside `path` (used only to add a step's own keys to a file that lacks them)."""
    temporary = '%s.%d.new' % (path, os.getpid())
    write_new(temporary, data, mode)
    os.replace(temporary, str(path))


def service_config(store, ids, journal, api_edge, workspace, root, name):
    """The veldo.api_service/v1 the authority service constructs the API's judge from."""
    return {'schema': 'veldo.api_service/v1', 'store_path': store, 'authority_ids': dict(ids),
            'authority_generation': 1, 'journal': dict(journal), 'api_edge': api_edge,
            'domain': ids['domain_uuid'], 'projects': [ids['repository_uuid']], 'rp_id': name,
            'origin': 'https://' + name, 'workflows_repository': workspace,
            'publication_root': os.path.join(root, 'authority', 'publication')}


def process_config(ids, workspace, host_trust, signer_config, key_id, connection_key, api_edge, state_dir, name, port):
    """The 0600 veldo.api_process/v1 the API process is constructed from (control_client_api.open_api)."""
    return {'schema': 'veldo.api_process/v1', 'workspace': workspace, 'host_trust': host_trust,
            'signer': {'config': signer_config, 'edge_key_id': key_id, 'connection_key': connection_key},
            'listen': {'host': LOOPBACK, 'port': port},
            'api': {'origin': 'https://' + name, 'rp_id': name, 'host': name, 'domain': ids['domain_uuid'],
                    'ids': dict(ids), 'edge': api_edge, 'state_dir': state_dir}}


def unit_text(authority_unit, python, executable, config):
    """The API unit from its template: bound to the authority unit, which wants it."""
    body = TEMPLATE.read_text()
    for field, value in (('AUTHORITY', authority_unit), ('PYTHON', python), ('EXECUTABLE', executable), ('CONFIG', config)):
        if not isinstance(value, str) or not UNIT_VALUE.fullmatch(value):
            raise Refused('invalid_input:unit_value:' + field.lower(), 'a value the unit cannot carry safely')
        body = body.replace('@%s@' % field, value)
    if re.search(r'@[A-Z_]+@', body) or UNIT_SCHEMA not in body:
        raise Refused('invalid_input:unit_template', 'the API unit template is not %s' % UNIT_SCHEMA)
    return body


def link_state(path, unit, differs):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return 'absent'
    if not stat.S_ISLNK(info.st_mode) or os.readlink(path) != os.path.join('..', unit):
        raise differs(path)
    return 'equal'


def enrollment_command(command_id, api_edge, key_id, public_key, connection_public_key):
    E = organ('control_channel_enrollment')
    return {'command_id': command_id, 'operation': E.ENROLL, 'target': E.target(CHANNEL),
            'parameters': {'channel': CHANNEL, 'edge_principal': api_edge, 'edge_key_id': key_id,
                           'public_key': public_key, 'connection_public_key': connection_public_key, 'scope': ['*']},
            'artifact_digests': [], 'expected_versions': {}}


def edge_state(state, key_path, connection_path, now, differs):
    """'absent' when no api edge is enrolled and its keys are absent, 'keys' when only the keys are there,
    'enrolled' when the enrolled edge is current and is exactly those keys; anything else differs."""
    E = organ('control_channel_enrollment')
    record = E.edge_record(state, E.edge_key_id(CHANNEL))
    held = [os.path.lexists(key_path), os.path.lexists(connection_path)]
    if held[0] != held[1]:
        raise differs(key_path if not held[0] else connection_path)
    if record is None:
        return 'keys' if held[0] else 'absent'
    if not held[0]:
        raise differs(key_path)
    if (not E.active(record, now) or record.get('public_key') != derived(key_path)
            or record.get('connection_public_key') != derived(connection_path)):
        raise differs(key_path)
    return 'enrolled'


def generate_keys(key_path, connection_path):
    _keygen(key_path, 'veldo-edge-api')
    _keygen(connection_path, 'veldo-edge-api-connection')


def republish(S, CM, K, store, projection):
    """The key projection from a read-only view of the committed store (setup never writes the store
    while the service holds its lock): an atomic 0600 file."""
    conn = S.open_store(store, mode='r')
    try:
        conn.execute('BEGIN')
        try:
            body = K.projection(CM.authority_state(S, conn))
        finally:
            conn.execute('ROLLBACK')
    finally:
        conn.close()
    if not os.path.isfile(projection) or Path(projection).read_text() != body:
        replace_file(projection, body, 0o600)


def service_running(runner, unit):
    rc, out, _err = runner.run(['show', '-p', 'ActiveState', unit])
    shown = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    return rc == 0 and shown.get('ActiveState') == 'active'


# ---------------------------------------------------------------------------------------------
# veldo factory passkey
# ---------------------------------------------------------------------------------------------

def pending(state_dir, now):
    """The API's pending registrations: [(path, record)], each unexpired and well formed."""
    found = []
    folder = Path(state_dir) / 'pending'
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            record = json.loads(path.read_text())
            binding = record['binding']
            expires = float(binding['expires_at'])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        found.append((path, record, expires > now))
    return found


def passkey(state_root, owner, owner_key, fingerprint=None, clock=time.time):
    """The pending registrations (fingerprint None), or the one the owner names signed and sent."""
    CC, CE, EL, CR = organ('control_client'), organ('control_enrollment'), organ('control_eligibility'), organ('control_api_credentials')
    ACT, AC = organ('control_channel_activation'), organ('authority_contract')
    root = os.path.realpath(str(state_root))
    try:
        ingress = json.loads((Path(root) / 'host' / 'ingress.json').read_text())
        workspace, trust_path = ingress['workspace'], ingress['host_trust']
        trust = EL.load_host_trust(trust_path)
        binding = CE.read_binding(workspace)
    except (OSError, ValueError, KeyError, TypeError, EL.Stopped, CE.EnrollmentRefused):
        raise Refused('missing_authority:state_root:not_set_up', root) from None
    if trust is None or not isinstance(binding, dict):
        raise Refused('missing_authority:state_root:not_set_up', root)
    now = clock()
    found = pending(os.path.join(root, STATE_DIR), now)
    listed = [dict(CR.describe(record), principal=owner, pending_id=path.stem, expired=not live)
              for path, record, live in found]
    if fingerprint is None:
        return {'outcome': 'listed', 'pending': [p for p in listed if not p['expired']]}
    named = [(path, record, live) for path, record, live in found
             if CR.describe(record).get('fingerprint') == fingerprint]
    if not named:
        raise Refused('invalid_input:passkey:unknown', 'no pending registration has that fingerprint')
    if len(named) > 1:
        raise Refused('invalid_input:passkey:ambiguous', 'more than one pending registration has that fingerprint')
    path, record, live = named[0]
    if not live:
        raise Refused('invalid_input:passkey:expired', 'that pending registration expired')
    verify = trust.verifier(binding.get('enrolled_by'), workspace)
    sign = ACT.ssh_signer(os.path.realpath(str(owner_key)))

    def send(packet):
        try:
            answer = CC.send(workspace, packet, CE, verify, sign, trust.host_identity, timeout=60)
        except CC.RoutingRefused as exc:
            raise Refused('unavailable_service:authority:' + exc.reason, 'the authority service did not answer') from None
        if not answer.get('accepted'):
            raise Refused(str(answer.get('reason') or 'unknown_outcome'), 'the authority refused the request')
        return answer.get('result') or {}
    status = send({'operation': 'inspect', 'entity_ids': []}).get('channel') or {}
    if not status.get('available'):
        raise Refused('unavailable_service:channel', 'the running service reports no authority versions')
    command = CR.enrollment_command(record, owner, 'passkey-%s-%s' % (owner, path.stem))
    ids = status.get('authority_ids') or {}
    envelope = dict({k: ids.get(k) for k in ('domain_uuid', 'repository_uuid', 'store_uuid')}, schema=AC.ENVELOPE_SCHEMA,
                    command_id=command['command_id'], principal=owner, request_revision=1,
                    nonce='nonce-' + command['command_id'], expires_at=now + 600,
                    membership_version=status.get('membership_version'),
                    delegation_version=status.get('delegation_version'),
                    command_digest=AC.canonical_command_digest(command))
    result = send({'command': command, 'envelope': envelope, 'signature': sign(AC.canonical_envelope_bytes(envelope))})
    shown = dict(CR.describe(record), principal=owner, pending_id=path.stem,
                 credential_id=record['binding'].get('credential_id'), command_id=command['command_id'])
    if not result.get('ok'):
        raise Refused(str(result.get('reason') or 'unknown_outcome'), 'the authority refused the enrollment')
    return {'outcome': 'enrolled', 'enrolled': shown}


def passkey_main(argv=None):
    """veldo factory passkey --state-root DIR --owner NAME --owner-key FILE [--sign FINGERPRINT]. Prints one
    JSON answer; exit 0 listed or enrolled, 1 refused by name, 2 usage."""
    import argparse
    parser = argparse.ArgumentParser(prog='veldo factory passkey', description='List the API\'s pending passkey '
                                     'registrations, or sign the one whose fingerprint your phone shows.')
    parser.add_argument('--state-root', required=True, help='the state root veldo factory setup laid down')
    parser.add_argument('--owner', required=True, help='the owner\'s principal name')
    parser.add_argument('--owner-key', required=True, help='his OpenSSH private key file; it signs, it is never read here')
    parser.add_argument('--sign', metavar='FINGERPRINT', help='the fingerprint of the ONE registration to enroll')
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    try:
        report = passkey(args.state_root, args.owner, args.owner_key, args.sign)
    except Refused as exc:
        print(json.dumps({'action': 'passkey', 'outcome': 'refused', 'reason': exc.code, 'detail': exc.detail},
                         sort_keys=True))
        return EXIT_REFUSED
    print(json.dumps(dict(report, action='passkey'), sort_keys=True))
    return 0
