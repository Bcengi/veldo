#!/usr/bin/env python3
"""The authority service's side of the authenticated API: every API command and read, run by the
running service, and the hint it sends the API after each commit (VELDO-0130 phase 3).

WHAT THIS MODULE IS. The part of the authority service (control_service.py) that runs the API's calls.
An installation that names an API service configuration (veldo.api_service/v1, this account's own 0600
file naming THIS authority's store, identities, generation, the service's own journal principal and key,
the api edge the Telegram ingress already names, the intake domain and projects, the relying party, the
workflow repository and the publication's destination) copies it into the protected configuration, and
`serve` constructs, with `open_api`, the VELDO-0130 ApiAuthority on the Telegram ingress's own store
connection (control_service_channel), sharing its VELDO-0066 acquirer and its VELDO-0068 settlement, so
one request still gets one ruling whichever channel answers. The API rides on that ingress: without one
the installation refuses by name. The judge holds the service's authority lock, so it runs here and
nowhere else (control_api_authority.authority_problem).

THE CALLS. An API request reaches the service over VELDO-0107 like any other, and control_client.Authority
judges the peer, the request signature and the workspace coordinate. Its command is one API call
(control_api_assertion.CALLS). The service verifies an API call's request signature against the enrolled
api edge's key alone, in control_api_assertion.REQUEST_NAMESPACE (`verifies`), so no member key speaks as
the API and the API's request signature stands in for no command. `call` then runs it on the judge:
`apply` (one edge-signed assertion packet, rechecked there), `inspect`, `read`, `workflow`, `events` and
`feed`, and `subscribe`.

HOST COMMITS REACH THE API. A steward's enroll_api_credential or revoke_api_credential, signed at the host
and sent to the service (`credential`), is admitted by control_api_credentials.Credentials on the same
connection. After every packet or channel pass that advanced the journal, whoever sent it, the service
sends the VELDO-0046 hint of the head record (identity only) to each subscribed API (`publish`): one
connection to the API's own socket, which must be this account's socket in a directory nobody else can
enter, its peer checked by the kernel's answer (SO_PEERCRED). The hint only wakes: the API reads the
committed records after its cursor through `feed`, ends the sessions a revocation ends and closes their
streams. Each hint names this service instance and its number for that subscriber. The subscribers are
remembered across a restart (a 0600 file in the service's state directory), and a new instance sends
each the head's hint once it serves (`announce`), so an API whose service restarted sees the new
instance on its hint socket and subscribes again and reconciles by itself. A subscriber whose socket is
gone or refuses is dropped and forgotten.

Observations carry identities, digests, counts and named refusals, never a signature, a key or a
credential. Standard library only.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import struct
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('service_api_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTH = _organ('control_api_authority')
AS, CR, WF = AUTH.AS, AUTH.CR, AUTH.WF
E, AC, CM = AUTH.E, AUTH.AC, AUTH.CM
IN = _organ('control_channel_ingress')
EVP = _organ('control_event_projection')

SCHEMA = 'veldo.api_service/v1'
FIELDS = ('schema', 'store_path', 'authority_ids', 'authority_generation', 'journal', 'api_edge', 'domain',
          'projects', 'rp_id', 'origin', 'workflows_repository', 'publication_root')
SUBSCRIBER_LIMIT = 8
SUBSCRIBERS_NAME = 'api-subscribers.json'
HINT_LIMIT = 64 * 1024
PUSH_SECONDS = 0.5
EVENT_LIMIT = 256


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def _code(exc):
    return getattr(exc, 'code', None) or type(exc).__name__


def load_config(path):
    """The API service configuration: this account's own 0600 regular file with exactly its fields."""
    try:
        text = Path(IN._private_file(str(path), 'the API service configuration')).read_text()
        config = json.loads(text)
    except ValueError:
        raise Refused('invalid_input', 'the API service configuration is not JSON') from None
    except Exception as exc:  # noqa: BLE001 - the ingress module names its own refusal
        raise Refused(_code(exc), str(path)) from None
    if not isinstance(config, dict) or config.get('schema') != SCHEMA or set(config) != set(FIELDS):
        raise Refused('invalid_input', 'the API service configuration has exactly the %s fields' % SCHEMA)
    return config


def installable(path, binding, principal, journal_key, repositories, channel_ingress):
    """The API service configuration an installation copies, refused by name unless it is THIS
    authority's: its store, identities, generation and a served repository, the service's own journal
    principal and key, and the api edge of the Telegram ingress it rides on (which must be installed too)."""
    try:
        config = load_config(path)
    except Refused as exc:
        raise Refused('invalid_input:api_service:' + exc.code, str(path)) from None
    if channel_ingress is None:
        raise Refused('invalid_input:api_service:no_channel', 'the API rides on the Telegram ingress; install it too')
    ingress = IN.load_config(channel_ingress)
    ids = config['authority_ids'] if isinstance(config['authority_ids'], dict) else {}
    journal = config['journal'] if isinstance(config['journal'], dict) else {}
    checks = (('store', str(config['store_path']) == binding['store_path']),
              ('domain', ids.get('domain_uuid') == binding['domain_uuid']),
              ('store_uuid', ids.get('store_uuid') == binding['store_uuid']),
              ('repository', ids.get('repository_uuid') in repositories),
              ('generation', config['authority_generation'] == binding['authority_generation']),
              ('journal', journal.get('principal') == principal and journal.get('key') == journal_key),
              ('api_edge', config['api_edge'] == ingress.get('api_edge')
               and ids == (ingress.get('authority_ids') or {})),
              ('publication_root', isinstance(config['publication_root'], str)
               and os.path.isabs(config['publication_root'])))
    for name, ok in checks:
        if not ok:
            raise Refused('invalid_input:api_service:' + name, 'the API service configuration is not this authority\'s')
    return Path(path).read_bytes()


def open_api(path, channel, lock, state_dir, clock=time.time):
    """(ServiceApi, None) for an installation's API configuration, (None, refusal) when it cannot be
    constructed, and (None, None) when the installation names none."""
    if not path:
        return None, None
    if channel is None:
        return None, 'no_channel'
    try:
        return ServiceApi(path, channel, lock, state_dir, clock), None
    except Exception as exc:  # noqa: BLE001 - the service keeps serving; the refusal is reported by name
        return None, _code(exc)


def peer_uid(conn):
    """The kernel's answer about who is on the other end of a local stream socket, or None."""
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    except (OSError, AttributeError):
        return None
    return struct.unpack('3i', raw)[1]


class ServiceApi:
    """The API calls of one running authority service, on the Telegram ingress's store connection."""

    def __init__(self, config_path, channel, lock, state_dir, clock=time.time):
        self.config = load_config(config_path)
        ingress = channel.ingress
        self.S, self.conn, self.clock = ingress.activations.S, ingress.conn, clock
        ids = dict(self.config['authority_ids'])
        generation = self.config['authority_generation']
        principal, sign = IN.journal_signer(self.config['journal'])
        credentials_dir = Path(state_dir) / 'api-credentials'
        credentials_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.credentials = CR.Credentials(self.S, self.conn, ids, principal, sign, rp_id=self.config['rp_id'],
                                          origin=self.config['origin'], state_dir=credentials_dir,
                                          authority_generation=generation, clock=clock)
        intake = AS.IN.Intake(self.S, CM, AC, ingress.acquirer, self.conn, domain=self.config['domain'],
                              projects=list(self.config['projects']), api_edge=self.config['api_edge'],
                              journal_signer=principal, sign=sign, authority_generation=generation, clock=clock)
        workflows = WF.Workflows(self.S, self.conn, domain=self.config['domain'],
                                 repository=self.config['workflows_repository'], signer=principal, sign=sign,
                                 generation=generation, clock=clock)
        publication = EVP.Projection(self.S, self.config['store_path'], domain=ids['domain_uuid'],
                                     repository=ids['repository_uuid'], root=self.config['publication_root'])
        self.edge = self.config['api_edge']
        self.authority = AUTH.ApiAuthority(self.S, CM, self.conn, ids=ids, domain=self.config['domain'], edge=self.edge,
                                           intake=intake, settlement=ingress.settlement, credentials=self.credentials,
                                           workflows=workflows, publication=publication, clock=clock,
                                           authority_lock=lock)
        self.instance = '%d-%s' % (os.getpid(), os.urandom(6).hex())
        # The subscribed APIs' hint sockets, remembered across a restart in this 0600 file of the service's
        # state directory, and each one's hint number from this instance.
        self.subscribers_file = Path(state_dir) / SUBSCRIBERS_NAME
        self.subscribers = self._remembered()
        self.sequence = {}
        self.counts = {'calls': 0, 'refused': 0, 'published': 0, 'dropped': 0}

    # -- the request signature -----------------------------------------------------------------

    def verifies(self, message, signature):
        """Whether an API call's request was signed by the enrolled api edge's current key, in the API's
        request namespace, the edge a current service member."""
        now = self.clock()
        state = CM.authority_state(self.S, self.conn)
        entry = E.edge_record(state, AC.edge_channel(AS.CHANNEL).get('edge_key_id'))
        member = AC.membership_entry(state['membership'], self.edge)
        if (entry is None or entry.get('channel') != AS.CHANNEL or entry.get('principal') != self.edge
                or not E.active(entry, now) or not AC.active_member(member, now)[0]
                or member.get('principal_type') != 'service'):
            return False
        return AC.ssh_keygen_verify(message, signature, AC.allowed_signers_line(self.edge, entry['public_key'],
                                                                                AS.REQUEST_NAMESPACE),
                                    self.edge, AS.REQUEST_NAMESPACE)[0]

    # -- the calls -----------------------------------------------------------------------------

    def call(self, command):
        """Run one API call on the judge. Returns its answer with this service instance named."""
        self.counts['calls'] += 1
        try:
            result = self._call(command)
        except Exception as exc:  # noqa: BLE001 - an organ's named refusal keeps its name
            code = getattr(exc, 'code', None)
            if not isinstance(code, str):
                raise
            result = {'ok': False, 'reason': code, 'taxonomy': AUTH.taxonomy(code)}
        if not result.get('ok'):
            self.counts['refused'] += 1
        return dict(result, instance=self.instance)

    def _call(self, command):
        problems = AS.call_problems(command)
        if problems:
            raise Refused('invalid_input:api_call', problems[0])
        a, name = command['arguments'], command['call']
        if name == 'apply':
            return self.authority.apply(a['packet'])
        if name == 'inspect':
            return self.authority.inspect(a['entity_ids'])
        if name == 'read':
            return self.authority.read(a['model'], a['principal'])
        if name == 'workflow':
            return self.authority.workflow(a['principal'], a['workflow'], a['version'])
        if name == 'subscribe':
            return self.subscribe(a['socket'])
        after, limit = a['after'], a['limit']
        if type(after) is not int or after < 0 or type(limit) is not int or not 0 < limit <= EVENT_LIMIT:
            raise Refused('invalid_input:api_call', 'after is a sequence and limit at most %d' % EVENT_LIMIT)
        if name == 'events':
            return self.authority.events(a['principal'], after, limit)
        return self.authority.feed(after, limit)

    def credential(self, packet):
        """A steward's enroll_api_credential or revoke_api_credential, signed at the host, admitted by
        control_api_credentials on this connection. Nothing is written unless it is accepted."""
        packet = packet if isinstance(packet, dict) else {}
        envelope, command, signature = packet.get('envelope'), packet.get('command'), packet.get('signature')
        seen = self.credentials.admit(envelope if isinstance(envelope, dict) else {}, command,
                                      signature if isinstance(signature, str) else '')
        if seen.get('outcome') != 'accepted':
            code = seen.get('refusal') or 'unknown_outcome'
            return {'ok': False, 'reason': '%s:api_credential:%s' % (seen.get('error_class') or 'unknown_outcome', code),
                    'accepted_versions': seen.get('accepted_versions') or {}}
        return {'ok': True, 'reason': (command or {}).get('operation'), 'credential_id': seen.get('credential_id'),
                'seq': seen.get('seq'), 'accepted_versions': seen.get('accepted_versions') or {}}

    # -- the subscribers -----------------------------------------------------------------------

    @staticmethod
    def _socket_problem(path):
        """Why `path` is not an API's own hint socket: this account's socket, in a directory of this
        account that nobody else can enter."""
        if not isinstance(path, str) or not os.path.isabs(path) or len(os.fsencode(path)) >= 108:
            return 'invalid_input:subscribe:path'
        try:
            here, parent = os.lstat(path), os.lstat(os.path.dirname(path))
        except OSError:
            return 'missing_evidence:subscribe:absent'
        if not stat.S_ISSOCK(here.st_mode) or here.st_uid != os.getuid():
            return 'invalid_input:subscribe:not_own_socket'
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
            return 'invalid_input:subscribe:directory'
        return None

    def _remembered(self):
        """The subscribers a previous instance remembered: this account's own 0600 file, a list of at most
        SUBSCRIBER_LIMIT absolute paths; anything else is no subscriber (each API subscribes again)."""
        try:
            info = os.lstat(str(self.subscribers_file))
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                return []
            listed = json.loads(self.subscribers_file.read_text())
        except (OSError, ValueError):
            return []
        if not isinstance(listed, list) or len(listed) > SUBSCRIBER_LIMIT:
            return []
        return [p for p in dict.fromkeys(listed) if isinstance(p, str) and os.path.isabs(p)]

    def _remember(self):
        """Write the subscriber list (0600, replaced whole), so the next instance can wake each API."""
        temporary = self.subscribers_file.with_name(self.subscribers_file.name + '.%d.tmp' % os.getpid())
        fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(json.dumps(self.subscribers))
        os.replace(str(temporary), str(self.subscribers_file))

    def subscribe(self, path):
        problem = self._socket_problem(path)
        if problem:
            raise Refused(problem, 'not an API hint socket of this account')
        if path not in self.subscribers:
            if len(self.subscribers) >= SUBSCRIBER_LIMIT:
                raise Refused('unavailable_service:subscribe:limit', 'at most %d subscribed APIs' % SUBSCRIBER_LIMIT)
            self.subscribers.append(path)
            self._remember()
        return dict(self.hint(), ok=True, reason='subscribed', subscribers=len(self.subscribers),
                    sequence=self.sequence.get(path, 0))

    def hint(self):
        """The VELDO-0046 hint of the journal head: identity only, never domain data."""
        return self.authority.hint()

    def publish(self):
        """Send the head record's hint to every subscribed API, naming this instance and the hint's number
        for that subscriber (counted whether or not it arrives, so a lost hint is a gap the API sees).
        Returns {sent, dropped}."""
        hint = dict(self.hint(), instance=self.instance)
        sent, dropped = 0, []
        for path in list(self.subscribers):
            self.sequence[path] = self.sequence.get(path, 0) + 1
            outcome = self._push(path, json.dumps(dict(hint, sequence=self.sequence[path]), sort_keys=True).encode())
            if outcome == 'sent':
                sent += 1
            elif outcome == 'gone':
                dropped.append(path)
        if dropped:
            self.subscribers = [p for p in self.subscribers if p not in dropped]
            self._remember()
        self.counts['published'] += sent
        self.counts['dropped'] += len(dropped)
        return {'sent': sent, 'dropped': len(dropped), 'watermark': hint.get('watermark')}

    def announce(self):
        """Once this instance serves: the head's hint to every subscriber a previous instance remembered,
        so each API sees the new instance and reconciles without waiting for a request of its own."""
        return self.publish() if self.subscribers else {'sent': 0, 'dropped': 0}

    def _push(self, path, body):
        if self._socket_problem(path):
            return 'gone'
        channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        channel.settimeout(PUSH_SECONDS)
        try:
            channel.connect(path)
            if peer_uid(channel) != os.getuid():
                return 'gone'
            channel.sendall(body)
            return 'sent'
        except (ConnectionRefusedError, FileNotFoundError):
            return 'gone'
        except OSError:
            return 'failed'
        finally:
            channel.close()

    def status(self):
        return {'available': True, 'instance': self.instance, 'edge': self.edge, 'subscribers': len(self.subscribers),
                'counts': dict(self.counts), 'metrics': self.authority.metrics()}
