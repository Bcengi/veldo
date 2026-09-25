#!/usr/bin/env python3
"""Per-channel live ingress activation and real sandbox qualification (VELDO-0073, PLAN-0019 W58).

WHAT THIS MODULE IS. The one record that decides whether the Telegram edge may talk to the platform,
the gate every installed Telegram send and receive entry point asks before each exchange, and the
qualification evidence an activation is bound to. A bot token that resolves, an enrolled edge key or
the source having landed is never activation: an edge given no gate refuses every exchange with the
Bot API as not_activated before any byte leaves (control_channel_projection.gated_open). Only a local
stand-in Bot API on the loopback interface, which cannot carry a message to Telegram, is reached
without a gate, so the suites of VELDO-0064 to VELDO-0068 keep driving their stand-ins.

THE ENTRY POINTS. ENTRY_POINTS names every installed Telegram exchange: TelegramEdge.send (VELDO-0064),
TelegramPresentationEdge.send (VELDO-0065), TelegramAcquisitionEdge getMe and getUpdates (VELDO-0066)
and the doorbell's TelegramSink.send (WARP-0618). Each calls gated_open with the gate it was given.

THE ACTIVATION RECORD. One `channel_activation` entity per channel, written only by the
channel_activation_authorize command, which is the owner's own OpenSSH-signed envelope (the authority
contract's envelope, as VELDO-0067 enrollment uses it): a current person member holding project_owner,
signing for himself, over the exact action and parameters. Three actions, each a separate
authorization: `qualify` opens a bounded qualification run on one Bot API origin (at most
MAX_RUN_SECONDS), `activate` names one committed qualification record by id and digest, `stop` halts
the edge. Every record binds, as read in the authority's committed state when it is signed: the
origin, the owner, his VELDO-0064 chat enrollment (id, version, chat), the VELDO-0067 edge key (id,
version, key digest) and, when active, the qualification and the bot it proved. The store checks
those versions again when it commits.

THE GATE. Gate.admit re-reads the record at every exchange: none is not_activated, a stopped record is
edge_stopped, another origin is stale_configuration, a changed or retired edge key is stale_key, a
changed chat enrollment is stale_enrollment, an owner no longer a current person member is
owner_not_current, an expired run is qualification_expired, a send to any chat but the owner's
enrolled one is chat_not_enrolled, and an active record whose qualification is missing, altered or no
longer proves the platform refuses by that proof's own reason. A getMe answer naming another bot than
the one activated is stale_configuration. Stop halts send and answer acceptance at once; nothing about
a pending request changes, so it stays pending.

REAL EVIDENCE, AND HOW IT IS TOLD FROM A FIXTURE. The gate performs the exchange itself, through its
own opener: no proxy from the environment, and for https a TLS context that loads only the trust
store compiled into this host's OpenSSL (never SSL_CERT_FILE or SSL_CERT_DIR), requires a certificate
and checks the host name. For each exchange it records the origin, the host, the status, the digest of
the platform's answer bytes and the identities in it, and for TLS the verified peer's certificate
fingerprint, names, issuer and protocol. A qualification for the Telegram origin is real only when
every exchange of its presentation, answer and settlement legs was made with https://api.telegram.org
over a verified TLS session whose certificate names that host, and its evidence is the same bytes:
the owner's answer is the canonical VELDO-0066 evidence whose answer digest is the digest of a
recorded getUpdates answer. An exchange with a loopback stand-in carries no TLS peer, so evidence from
a fixture never qualifies the Telegram origin (fixture_only_evidence). An exchange the gate's transport
could not complete (a timeout, a refused connection, a name that did not resolve, a body cut off)
records the failure's class and no answer; a run holding one does not qualify either, and is named
unavailable_service, so the owner knows to run it again rather than look for a fixture. A stand-in origin can be
qualified and activated too, which is how the suites drive the gate, but that activation binds the
stand-in origin and cannot admit an exchange with any other. WHAT THIS CANNOT PROVE: Telegram does not
sign its answers, so a record in the store is trusted as the store is (the threat model trusts the
store, the signer and the token's custody). In a factory the witness beside the transport's record is
the owner's activation over the record's digest, signed with his enrolled key after he saw the message
on his own phone (VELDO-0138). A record copied out of the store into a file proves nothing by itself.

THE UNAUTHORIZED LEG. The owner has no second person (Telegram 29047), so the unauthorized actor is an
update from an unenrolled sender id, as in VELDO-0066; the record says whether that update came from
the platform or from a stand-in (`provenance`).

WHAT IT IS NOT. Not interrupted settlement, retention, reconnect, restart or rollback qualification
(Release 2), not other channels (Release 4). Observations carry identities, versions, outcomes and
named refusals, never the token, message text, rationale or a signature. Standard library only.
"""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request


def organ(name):
    spec = importlib.util.spec_from_file_location('activation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = organ('control_channel_projection')
E = organ('control_channel_enrollment')
CM, AC = E.CM, E.AC

CHANNEL = 'telegram_chat'
TELEGRAM_ORIGIN = 'https://api.telegram.org'
TELEGRAM_HOST = 'api.telegram.org'
STAND_IN_PREFIX = P.STAND_IN_ORIGIN
ACTIVATION_SCHEMA = 'veldo.channel_activation/v1'
QUALIFICATION_SCHEMA = 'veldo.channel_qualification/v1'
ACTIVATION_KIND, QUALIFICATION_KIND = 'channel_activation', 'channel_qualification'
AUTHORIZE, QUALIFY = 'channel_activation_authorize', 'channel_qualification_record'
OWNER = 'VELDO-0073 channel activation'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OWNER_ROLE = 'project_owner'
MAX_RUN_SECONDS = 3600
STATES = {'qualify': 'qualifying', 'activate': 'active', 'stop': 'stopped'}
PARAMETERS = {'qualify': ('channel', 'action', 'owner', 'origin', 'edge_key_id', 'expires_at'),
              'activate': ('channel', 'action', 'owner', 'origin', 'edge_key_id', 'qualification_id',
                           'qualification_digest'),
              'stop': ('channel', 'action', 'owner', 'origin', 'edge_key_id')}
# What an activation binds and the gate compares with current authority at every exchange.
BOUND = ('owner', 'enrollment_id', 'enrollment_version', 'enrolled_chat', 'edge_key_id', 'edge_version',
         'edge_key_digest')
SEND, RECEIVE = ('sendMessage',), ('getMe', 'getUpdates')
# Every installed Telegram send and receive entry point: (installed module, the call, the Bot API method).
ENTRY_POINTS = (('control_channel_projection.py', 'TelegramEdge.send', 'sendMessage'),
                ('control_channel_presentation.py', 'TelegramPresentationEdge.send', 'sendMessage'),
                ('control_channel_attribution.py', 'TelegramAcquisitionEdge.get_me', 'getMe'),
                ('control_channel_attribution.py', 'TelegramAcquisitionEdge.get_updates', 'getUpdates'),
                ('request_doorbell.py', 'TelegramSink.send', 'sendMessage'))
REFUSALS = {'not_activated': 'missing_authority', 'edge_stopped': 'missing_authority',
            'stale_configuration': 'stale_subject', 'stale_key': 'stale_subject', 'stale_enrollment': 'stale_subject',
            'owner_not_current': 'missing_authority', 'qualification_expired': 'stale_subject',
            'chat_not_enrolled': 'missing_authority', 'missing_qualification': 'missing_evidence',
            'fixture_only_evidence': 'missing_evidence', 'presentation_unproven': 'missing_evidence',
            'answer_unproven': 'missing_evidence', 'unauthorized_unproven': 'missing_evidence',
            'settlement_unproven': 'missing_evidence', 'invalid_input': 'invalid_input',
            'envelope_refused': 'invalid_input', 'signature_invalid': 'missing_authority',
            'not_current_member': 'missing_authority', 'not_a_person': 'missing_authority',
            'policy_refused': 'missing_authority', 'not_owner': 'missing_authority', 'already_active': 'stale_subject',
            'not_qualifying': 'stale_subject', 'store_refused': 'unavailable_service',
            'unavailable_service': 'unavailable_service'}
assert set(P.GATE_REFUSALS) <= set(REFUSALS)


class Refused(Exception):
    """A named refusal; nothing was written and, from the gate, nothing was sent."""

    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def bytes_digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def activation_id(channel=CHANNEL):
    return 'channel_activation:%s' % channel


def qualification_id(channel, run):
    return 'channel_qualification:%s:%s' % (channel, run)


def origin_of(url):
    """scheme://host[:port] of a URL, the way the gate compares origins."""
    scheme, _, rest = url.partition('://')
    return '%s://%s' % (scheme, rest.split('/', 1)[0])


def platform_of(origin):
    """'telegram' for the Bot API service, 'stand_in' for a loopback stand-in, None for anything else."""
    if origin == TELEGRAM_ORIGIN:
        return 'telegram'
    if isinstance(origin, str) and origin.startswith(STAND_IN_PREFIX) and origin[len(STAND_IN_PREFIX):].isdigit():
        return 'stand_in'
    return None


def _entity(conn, eid):
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


def bindings(store, conn, owner, edge_key_id, now):
    """(refusal, bound): what an activation of `owner`'s edge binds, read in committed state now."""
    state = CM.authority_state(store, conn)
    entry = AC.membership_entry(state['membership'], owner)
    if not AC.active_member(entry, now)[0] or entry.get('principal_type') != 'person':
        return 'owner_not_current', None
    edge = E.edge_record(state, edge_key_id)
    if edge is None or not E.active(edge, now) or edge.get('channel') != CHANNEL:
        return 'stale_key', None
    eid = P.enrollment_id(owner)
    enrollment = _entity(conn, eid)
    if (enrollment is None or enrollment['kind'] != P.ENROLLMENT_KIND
            or P.enrollment_problems(enrollment['kind'], enrollment['data'], owner)):
        return 'stale_enrollment', None
    return None, {'owner': owner, 'enrollment_id': eid, 'enrollment_version': enrollment['version'],
                  'enrolled_chat': enrollment['data']['chat_id'], 'edge_key_id': edge_key_id,
                  'edge_version': edge['entity_version'],
                  'edge_key_digest': digest([edge.get('public_key'), edge.get('connection_public_key')])}


def _names_cover(names, host):
    """Whether a certificate's DNS names cover `host` (one leftmost wildcard label at most)."""
    for name in names or ():
        name = str(name).lower()
        if name == host or (name.startswith('*.') and host.split('.', 1)[-1] == name[2:] and host.count('.') >= 2):
            return True
    return False


def failed_in_transport(exchange, origin):
    """Whether one recorded exchange with `origin` failed in transport: the gate's own transport raised
    before the platform's answer was read whole, and it recorded the failure's class."""
    return isinstance(exchange, dict) and exchange.get('origin') == origin and _text(exchange.get('transport_failure'))


def proven_exchange(exchange, origin):
    """Whether one recorded exchange is evidence of `origin`: for the Telegram origin, an https exchange
    with that host over a verified TLS session whose certificate names it; for a stand-in, its own origin.
    An exchange that failed in transport is evidence of nothing."""
    if not isinstance(exchange, dict) or exchange.get('origin') != origin or exchange.get('transport_failure'):
        return False
    if platform_of(origin) != 'telegram':
        return platform_of(origin) == 'stand_in' and exchange.get('tls') is None
    tls = exchange.get('tls')
    return (isinstance(tls, dict) and tls.get('verified') is True and tls.get('host') == TELEGRAM_HOST
            and _names_cover(tls.get('dns_names'), TELEGRAM_HOST)
            and isinstance(tls.get('peer_certificate'), str) and tls['peer_certificate'].startswith('sha256:')
            and exchange.get('host') == TELEGRAM_HOST)


def qualification_problems(record, origin):
    """The real-platform-proof check: why `record` does not qualify `origin`, by name; [] when it does.
    Fixture exchanges never qualify the Telegram origin."""
    if not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA:
        return ['missing_qualification']
    if record.get('origin') != origin or platform_of(origin) is None or record.get('platform') != platform_of(origin):
        return ['stale_configuration']
    exchanges = record.get('exchanges') if isinstance(record.get('exchanges'), list) else []
    unproven = [x for x in exchanges if not proven_exchange(x, origin)]
    if unproven and all(failed_in_transport(x, origin) for x in unproven):
        # The platform was not reached (a timeout, a refused connection, a name that did not resolve,
        # a body cut off): the run proves nothing, and the owner runs it again.
        return ['unavailable_service']
    if not exchanges or unproven:
        return ['fixture_only_evidence']
    chat = record.get('enrolled_chat')
    shown = record.get('presentation') or {}
    ids = shown.get('message_ids') or []
    sent = [x for x in exchanges if x.get('operation') == 'sendMessage' and x.get('status') == 200]
    bots = {(x.get('result') or {}).get('bot_id') for x in exchanges if x.get('operation') == 'getMe'}
    if (not ids or type(chat) is not int or shown.get('chat_id') != chat or bots != {record.get('bot_id')}
            or sorted((x.get('result') or {}).get('message_id') for x in sent if (x.get('result') or {}).get('chat_id') == chat
                      and (x.get('result') or {}).get('message_id') in ids) != sorted(ids)):
        return ['presentation_unproven']
    answer = record.get('owner_answer') or {}
    pulled = [x for x in exchanges if x.get('operation') == 'getUpdates' and x.get('status') == 200
              and x.get('response_digest') == answer.get('response_digest')
              and answer.get('update_id') in ((x.get('result') or {}).get('update_ids') or [])]
    if (not pulled or answer.get('outcome') != 'answered' or answer.get('sender_id') != chat
            or answer.get('chat_id') != chat or answer.get('reply_to_message_id') not in ids or not _text(answer.get('answer_id'))):
        return ['answer_unproven']
    other = record.get('unauthorized') or {}
    if (other.get('outcome') != 'refused' or other.get('reason') != 'unknown_sender' or type(other.get('sender_id')) is not int
            or other.get('sender_id') == chat or other.get('provenance') not in ('platform', 'stand_in')):
        return ['unauthorized_unproven']
    settled = record.get('settlement') or {}
    if (settled.get('answer_id') != answer.get('answer_id') or settled.get('originating_channel') != CHANNEL
            or settled.get('request_id') != record.get('request_id') or not _text(settled.get('settlement_id'))):
        return ['settlement_unproven']
    return []


# ---------------------------------------------------------------------------------------------
# The gate and its transport
# ---------------------------------------------------------------------------------------------

def _trust_context():
    """TLS that verifies against this host's compiled-in OpenSSL trust store only: the environment's
    SSL_CERT_FILE and SSL_CERT_DIR are never read, a certificate is required and the host name checked."""
    paths = ssl.get_default_verify_paths()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    loaded = False
    for cafile, capath in ((paths.openssl_cafile, None), (None, paths.openssl_capath)):
        try:
            context.load_verify_locations(cafile=cafile, capath=capath)
            loaded = True
        except (OSError, ssl.SSLError, TypeError):
            pass
    if not loaded:
        raise Refused('unavailable_service', 'this host has no OpenSSL trust store')
    return context


def _opener(peers):
    """The Bot API opener (no proxy, no redirect: projection.bot_opener) whose https connections record
    their verified peer."""
    class Connection(http.client.HTTPSConnection):
        def connect(self):
            super().connect()
            info = self.sock.getpeercert() or {}
            flat = lambda part: {k: v for rdn in info.get(part, ()) for k, v in rdn}
            peers.append({'verified': True, 'host': self.host, 'version': self.sock.version(),
                          'peer_certificate': bytes_digest(self.sock.getpeercert(True) or b''),
                          'dns_names': sorted(v for k, v in info.get('subjectAltName', ()) if k == 'DNS'),
                          'subject': flat('subject').get('commonName'), 'issuer': flat('issuer').get('organizationName'),
                          'not_after': info.get('notAfter')})

    class Handler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(Connection, req, context=_trust_context())

    return P.bot_opener(Handler())


def _result_fields(operation, body):
    """The identities in a Bot API answer that qualification binds, never its text."""
    try:
        answer = json.loads(body)
    except ValueError:
        return {}
    result = answer.get('result') if isinstance(answer, dict) and answer.get('ok') is True else None
    if operation == 'getMe' and isinstance(result, dict):
        return {'bot_id': result.get('id')}
    if operation == 'sendMessage' and isinstance(result, dict):
        return {'message_id': result.get('message_id'), 'chat_id': (result.get('chat') or {}).get('id'),
                'date': result.get('date')}
    if operation == 'getUpdates' and isinstance(result, list):
        return {'update_ids': [u.get('update_id') for u in result if isinstance(u, dict)]}
    return {}


class _Recorded:
    """The platform's answer as the edge reads it, digested into the exchange record as it is read."""

    def __init__(self, response, exchange):
        self._response, self._exchange, self._body = response, exchange, b''

    def read(self, *args):
        try:
            data = self._response.read(*args)
        except (http.client.HTTPException, OSError) as exc:
            self._exchange['transport_failure'] = type(exc).__name__
            raise
        self._body += data
        self._exchange['response_digest'] = bytes_digest(self._body)
        self._exchange['result'] = _result_fields(self._exchange['operation'], self._body)
        return data

    def close(self):
        self._response.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __getattr__(self, name):
        return getattr(self._response, name)


class Gate:
    """The activation gate of one channel on one control store connection. The edges call `open` for
    every exchange; `admit` alone answers whether one may happen now. `exchanges` keeps what each
    admitted exchange was, for the qualification record; `observations` every admission and refusal."""

    def __init__(self, store, conn, channel=CHANNEL, clock=time.time):
        self.store, self.conn, self.channel, self.clock = store, conn, channel, clock
        self.exchanges, self.observations = [], []
        self.counts = {'admitted': 0, 'refused': 0}

    def current(self):
        found = _entity(self.conn, activation_id(self.channel))
        data = found['data'] if found and found['kind'] == ACTIVATION_KIND else None
        return dict(data, entity_version=found['version']) if isinstance(data, dict) else None

    def _refuse(self, operation, code, detail=''):
        self.counts['refused'] += 1
        self.observations.append({'operation': operation, 'channel': self.channel, 'outcome': 'refused', 'reason': code,
                                  'error_class': REFUSALS.get(code, 'missing_authority')})
        raise Refused(code, detail)

    def admit(self, operation, origin, chat=None):
        """The current record when an exchange of `operation` with `origin` (to `chat`, for a send) may
        happen now; a named Refused otherwise."""
        record, now = self.current(), self.clock()
        if record is None or record.get('schema') != ACTIVATION_SCHEMA:
            self._refuse(operation, 'not_activated', 'no activation record: a token or a landed source is not one')
        if record.get('state') == 'stopped':
            self._refuse(operation, 'edge_stopped', 'the edge was stopped by an explicit record')
        if record.get('state') not in ('qualifying', 'active'):
            self._refuse(operation, 'not_activated')
        if not isinstance(origin, str) or origin.rstrip('/') != record.get('origin'):
            self._refuse(operation, 'stale_configuration', 'the edge names another Bot API origin than the activation')
        refusal, current = bindings(self.store, self.conn, record.get('owner'), record.get('edge_key_id'), now)
        if refusal:
            self._refuse(operation, refusal)
        for field in BOUND:
            if current[field] != record.get(field):
                self._refuse(operation, 'stale_key' if field.startswith('edge') else 'stale_enrollment',
                             '%s changed since the activation' % field)
        if record['state'] == 'qualifying' and not now < record.get('expires_at', 0):
            self._refuse(operation, 'qualification_expired')
        if record['state'] == 'active':
            found = _entity(self.conn, record.get('qualification_id') or '')
            proof = found['data'] if found and found['kind'] == QUALIFICATION_KIND else None
            if proof is None or digest(proof) != record.get('qualification_digest'):
                self._refuse(operation, 'missing_qualification')
            problems = qualification_problems(proof, record['origin'])
            if problems:
                self._refuse(operation, problems[0])
        if operation in SEND and chat != record.get('enrolled_chat'):
            self._refuse(operation, 'chat_not_enrolled', 'a send goes only to the enrolled owner\'s chat')
        if operation not in SEND + RECEIVE:
            self._refuse(operation, 'invalid_input', 'not a Telegram entry point method')
        self.counts['admitted'] += 1
        self.observations.append({'operation': operation, 'channel': self.channel, 'outcome': 'admitted', 'reason': None,
                                  'state': record['state'], 'accepted_versions': {activation_id(self.channel): record['entity_version']}})
        return record

    def bot(self, bot_id):
        """Refuse a getMe answer that names another bot than the one the active record proved."""
        record = self.current()
        if record is not None and record.get('state') == 'active' and record.get('bot_id') != bot_id:
            self._refuse('getMe', 'stale_configuration', 'the token names another bot than the activation')

    def open(self, request, timeout, operation, origin, chat=None):
        """Admit, then perform the exchange through the gate's own transport and record it."""
        record = self.admit(operation, origin, chat)
        if origin_of(request.full_url) != record['origin']:
            self._refuse(operation, 'stale_configuration')
        peers = []
        exchange = {'operation': operation, 'origin': record['origin'], 'host': request.host.split(':')[0],
                    'mode': record['state'], 'at': self.clock(), 'status': None, 'response_digest': None, 'result': {},
                    'tls': None}
        self.exchanges.append(exchange)
        try:
            response = _opener(peers).open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            exchange['status'] = exc.code
            exchange['tls'] = peers[-1] if peers else None
            raise
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            # No answer from the platform: recorded by the failure's class (never its text), so the
            # qualification names the run unavailable_service rather than fixture evidence.
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            exchange['transport_failure'] = type(reason if isinstance(reason, BaseException) else exc).__name__
            exchange['tls'] = peers[-1] if peers else None
            raise
        exchange['status'] = response.status
        exchange['tls'] = peers[-1] if peers else None
        return _Recorded(response, exchange)


# ---------------------------------------------------------------------------------------------
# The organ: owner-authorized records and the qualification record
# ---------------------------------------------------------------------------------------------

def _authorize_transition(params, before):
    record = params.get('record')
    aid = activation_id(params.get('channel'))
    if not isinstance(record, dict) or record.get('schema') != ACTIVATION_SCHEMA or record.get('state') not in STATES.values():
        raise ValueError('an activation record carries its schema and state')
    return {aid: {'kind': ACTIVATION_KIND, 'data': record}}


def _qualify_transition(params, before):
    record, qid = params.get('record'), params.get('qualification_id')
    if not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA or qid in before:
        raise ValueError('a qualification record is written once')
    return {qid: {'kind': QUALIFICATION_KIND, 'data': record}}


class Activations:
    """Admits the owner's signed activation commands and records qualification on one store connection.

    `store` is the control_store module, `conn` its connection, `authority_ids` this authority's
    domain, repository and store; `sign(bytes) -> text` signs journal records as `journal_signer`."""

    def __init__(self, store, conn, authority_ids, journal_signer, sign, authority_generation=1, clock=time.time):
        self.S, self.conn = store, conn
        self.ids = {f: authority_ids.get(f) for f in ('domain_uuid', 'repository_uuid', 'store_uuid')}
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation, self.clock = authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}

        def guarded(fn):
            def transition(params, before):
                try:
                    return fn(params, before)
                except ValueError as exc:
                    raise store.StoreRefused('invalid_input', str(exc))
            return transition
        conn.command_registry[AUTHORIZE] = {'transition': guarded(_authorize_transition), 'writes': WRITES}
        conn.command_registry[QUALIFY] = {'transition': guarded(_qualify_transition), 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={ACTIVATION_KIND: (AUTHORIZE,), QUALIFICATION_KIND: (QUALIFY,)},
                             module=__file__)

    def current(self, channel=CHANNEL):
        return Gate(self.S, self.conn, channel).current()

    def _observe(self, operation, outcome, reason, versions=None, **extra):
        self.counts['accepted' if outcome == 'accepted' else 'refused'] += 1
        observation = dict(self.ids, operation=operation, channel=CHANNEL, accepted_versions=dict(versions or {}),
                           outcome=outcome, reason=reason, error_class=None if reason is None else REFUSALS.get(reason, 'unknown_outcome'),
                           **extra)
        self.observations.append(observation)
        return observation

    def metrics(self):
        """Accepted and refused commands, the edge's state and the pending work: a channel not active."""
        record = self.current()
        state = record.get('state') if record else None
        return dict(self.counts, state=state, pending=[] if state == 'active' else [CHANNEL])

    def authorize(self, envelope, command, signature):
        """Admit one owner-signed channel_activation_authorize command (qualify, activate or stop), or
        refuse it by name with nothing written. Returns the observation."""
        command = command if isinstance(command, dict) else {}
        params = command.get('parameters') if isinstance(command.get('parameters'), dict) else {}
        about = {'action': params.get('action'), 'command_id': command.get('command_id'),
                 'principal': envelope.get('principal') if isinstance(envelope, dict) else None}
        versions = {}
        try:
            committed = self._authorize(envelope, command, signature, params, versions)
        except Refused as exc:
            return self._observe(AUTHORIZE, 'refused', exc.code, versions, **about)
        return self._observe(AUTHORIZE, 'accepted', None, versions, seq=committed.get('seq'), **about)

    def _authorize(self, envelope, command, signature, params, versions):
        action = params.get('action')
        if command.get('operation') != AUTHORIZE or action not in PARAMETERS or set(params) != set(PARAMETERS[action]):
            raise Refused('invalid_input', 'the parameters are exactly those of one action')
        if params['channel'] != CHANNEL or command.get('target') != E.target(CHANNEL) or platform_of(params['origin']) is None:
            raise Refused('invalid_input', 'the Telegram channel, its target and a Bot API origin')
        if not isinstance(envelope, dict) or envelope.get('command_id') != command.get('command_id') or not _text(command.get('command_id')):
            raise Refused('envelope_refused', 'the executed command is the signed command')
        now = self.clock()
        state = CM.authority_state(self.S, self.conn)
        signer = envelope.get('principal')
        entry = AC.membership_entry(state['membership'], signer)
        if not AC.active_member(entry, now)[0]:
            raise Refused('not_current_member')
        authority = dict(self.ids, membership_version=state['membership_version'], delegation_version=state['delegation_version'])
        seen = set(self.S.materialized_state(self.conn)['nonces'])
        problems = AC.envelope_problems(envelope, command, authority, now, seen, state['keyring'], state['membership'])
        if problems:
            raise Refused('envelope_refused', '; '.join(problems))
        key = AC.active_key(state['keyring'], signer, now)
        ok, _ = AC.ssh_keygen_verify(AC.canonical_envelope_bytes(envelope), signature if isinstance(signature, str) else '',
                                     AC.allowed_signers_line(signer, key['public_key']), signer)
        if not ok:
            raise Refused('signature_invalid')
        if entry.get('principal_type') != 'person':
            raise Refused('not_a_person')
        if OWNER_ROLE not in (entry.get('roles') or []):
            raise Refused('policy_refused', 'the owner authorizes the edge: the signer holds %s' % OWNER_ROLE)
        if signer != params['owner']:
            raise Refused('not_owner', 'the owner authorizes his own edge')
        aid = activation_id(CHANNEL)
        found = _entity(self.conn, aid)
        prior = found['data'] if found else None
        versions[aid] = found['version'] if found else 0
        if prior is not None and signer != prior.get('owner'):
            # An edge that has a record is its recorded owner's: every command over it (stop, qualify,
            # activate) is his own signature, never another project_owner naming himself as owner.
            raise Refused('not_owner', 'only the recorded owner commands an edge that has a record')
        refusal, bound = bindings(self.S, self.conn, params['owner'], params['edge_key_id'], now)
        if action == 'stop' and prior:
            # A stop never waits on current bindings: a retired key or a changed enrollment is exactly
            # when the owner must still be able to halt the edge. It keeps what the record bound.
            refusal, bound = None, {field: prior.get(field) for field in BOUND}
        if refusal:
            raise Refused(refusal)
        if action != 'stop':
            versions[bound['enrollment_id']] = bound['enrollment_version']
            versions[bound['edge_key_id']] = bound['edge_version']
        record = dict(bound, schema=ACTIVATION_SCHEMA, channel=CHANNEL, state=STATES[action], origin=params['origin'],
                      platform=platform_of(params['origin']), authorized_by=signer, command_id=command['command_id'],
                      authorized_at=now, expires_at=None, qualification_id=None, qualification_digest=None, bot_id=None)
        if action == 'qualify':
            if prior and prior.get('state') == 'active':
                raise Refused('already_active', 'stop the active edge before a new qualification run')
            expires = params['expires_at']
            if not isinstance(expires, (int, float)) or isinstance(expires, bool) or not now < expires <= now + MAX_RUN_SECONDS:
                raise Refused('invalid_input', 'a qualification run ends within %d seconds' % MAX_RUN_SECONDS)
            record['expires_at'] = expires
        elif action == 'activate':
            if not prior or prior.get('state') not in ('qualifying', 'stopped'):
                raise Refused('not_qualifying', 'activation follows a qualification run')
            qid = params['qualification_id']
            proof = _entity(self.conn, qid) if _text(qid) else None
            data = proof['data'] if proof and proof['kind'] == QUALIFICATION_KIND else None
            if data is None or digest(data) != params['qualification_digest']:
                raise Refused('missing_qualification', 'the named qualification is not the committed record')
            versions[qid] = proof['version']
            problems = qualification_problems(data, params['origin'])
            if problems:
                raise Refused(problems[0])
            for field in BOUND:
                if data.get(field) != bound[field]:
                    raise Refused('stale_key' if field.startswith('edge') else 'stale_enrollment',
                                  'the qualification bound another %s' % field)
            record.update(qualification_id=qid, qualification_digest=params['qualification_digest'], bot_id=data['bot_id'])
        else:
            if not prior:
                raise Refused('not_activated', 'there is no edge to stop')
            record.update({k: prior.get(k) for k in ('qualification_id', 'qualification_digest', 'bot_id')})
            record['stopped_from'] = prior.get('state')
        committed = dict(command, principal=signer, nonce=envelope['nonce'], parameters=dict(params, record=record),
                         expected_versions=dict(versions), artifact_digests=[])
        try:
            return self.S.execute(self.conn, committed, self.journal_signer, self.sign, self.authority_generation,
                                  committed_at=now)
        except self.S.StoreRefused as exc:
            raise Refused('store_refused', exc.code)

    def qualify(self, gate, presenter, acquirer, settlement, request_id, owner_evidence_id, unauthorized_evidence_id):
        """Record the qualification of the current run from what the store and the gate hold: the
        request's published presentation, the owner's canonical answer evidence and the unenrolled
        sender's, the settlement of that answer, and every exchange the gate made in this run. Refused
        by name, with nothing written, unless it proves the run's origin. Returns (id, digest, record)."""
        record = gate.current()
        if record is None or record.get('state') != 'qualifying':
            raise Refused('not_qualifying', 'qualification is recorded inside a qualification run')
        now = self.clock()
        refusal, bound = bindings(self.S, self.conn, record['owner'], record['edge_key_id'], now)
        if refusal:
            raise Refused(refusal)
        receipt = presenter.current(request_id) or {}
        owner = acquirer.evidence(owner_evidence_id) or {}
        other = acquirer.evidence(unauthorized_evidence_id) or {}
        settled = settlement.settlement(request_id, receipt.get('request_version')) if receipt else None
        exchanges = [dict(x) for x in gate.exchanges if x.get('mode') == 'qualifying' and x.get('origin') == record['origin']]
        pulled = {x.get('response_digest') for x in exchanges if x.get('operation') == 'getUpdates'}

        def answer(evidence):
            fields = evidence.get('fields') or {}
            return {'evidence_id': evidence.get('evidence_id'), 'update_id': evidence.get('update_id'),
                    'response_digest': evidence.get('response_digest'), 'source_digest': evidence.get('source_digest'),
                    'message_id': fields.get('message_id'), 'sender_id': fields.get('sender_id'),
                    'chat_id': fields.get('chat_id'), 'date': fields.get('date'),
                    'reply_to_message_id': fields.get('reply_to_message_id'), 'outcome': evidence.get('outcome'),
                    'reason': evidence.get('reason'), 'answer_id': evidence.get('answer_id')}
        qid = qualification_id(CHANNEL, record['command_id'])
        data = dict(bound, schema=QUALIFICATION_SCHEMA, channel=CHANNEL, qualification_id=qid, run=record['command_id'],
                    origin=record['origin'], platform=record['platform'], bot_id=owner.get('bot_id'), request_id=request_id,
                    request_version=receipt.get('request_version'),
                    presentation={'presentation_id': receipt.get('presentation_id'), 'digest': receipt.get('brief_digest'),
                                  'message_ids': list(receipt.get('message_ids') or []), 'chat_id': receipt.get('chat_id'),
                                  'published_at': receipt.get('published_at')},
                    exchanges=exchanges, owner_answer=answer(owner),
                    unauthorized=dict(answer(other), provenance='platform' if other.get('response_digest') in pulled else 'stand_in'),
                    settlement={'settlement_id': (settled or {}).get('settlement_id'), 'request_id': (settled or {}).get('request_id'),
                                'answer_id': (settled or {}).get('answer_id'), 'choice': (settled or {}).get('choice'),
                                'ruling': (settled or {}).get('ruling'),
                                'originating_channel': (settled or {}).get('originating_channel')},
                    recorded_at=now)
        problems = qualification_problems(data, record['origin'])
        if problems:
            self._observe(QUALIFY, 'refused', problems[0], qualification_id=qid)
            raise Refused(problems[0])
        command = dict(command_id=qid, principal=self.journal_signer, operation=QUALIFY,
                       parameters={'qualification_id': qid, 'record': data}, expected_versions={qid: 0},
                       artifact_digests=[], nonce=qid)
        try:
            committed = self.S.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)
        except self.S.StoreRefused as exc:
            self._observe(QUALIFY, 'refused', 'store_refused', qualification_id=qid)
            raise Refused('store_refused', exc.code)
        self._observe(QUALIFY, 'accepted', None, {qid: 0}, qualification_id=qid, seq=committed.get('seq'))
        return qid, digest(data), data


# ---------------------------------------------------------------------------------------------
# The owner's command surface (VELDO-0138): veldo channel status|qualify|activate|stop
# ---------------------------------------------------------------------------------------------
#
# The owner's own command path to the RUNNING authority service, which applies it to the gate every
# exchange of its ingress asks. bin/veldo routes `veldo channel` here and adds nothing. Each command
# reads the service's channel status (inspect, a signed request like every other), builds the one
# channel_activation_authorize command of the action from what the service reports (its configured
# origin and edge key, the authority coordinates and versions, and for activate the qualification the
# service recorded in the current run), signs the envelope with the owner's enrolled key and sends it
# through control_client to the authority of the named workspace. The service admits it only when it
# is the owner's own signature (Activations.authorize); nothing here decides that.

COMMAND_ACTIONS = ('status', 'qualify', 'activate', 'stop')
EXIT_REFUSED, EXIT_USAGE = 1, 2
DEFAULT_RUN_MINUTES = 15


def ssh_signer(key, namespace='veldo-command'):
    """sign(bytes) -> text with the private key file `key`, never through an agent."""
    import os
    import subprocess

    def sign(message):
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', namespace], input=message,
                              capture_output=True, timeout=30,
                              env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
        if done.returncode:
            raise Refused('unavailable_service', 'the key did not sign')
        return done.stdout.decode()
    return sign


def owner_command(action, status, principal, now, *, minutes=DEFAULT_RUN_MINUTES, qualification=None, serial=None):
    """(envelope, command) of one owner action over what the running service reports in `status` (its
    inspect answer's `channel`). Refused by name when the service reports no channel or, for activate,
    no qualification to name."""
    import uuid
    if not isinstance(status, dict) or not status.get('available'):
        raise Refused('unavailable_service', 'the authority runs no Telegram channel (%s)'
                      % ((status or {}).get('refusal') or 'not configured'))
    params = {'channel': CHANNEL, 'action': action, 'owner': principal, 'origin': status.get('origin'),
              'edge_key_id': status.get('edge_key_id')}
    if action == 'qualify':
        if type(minutes) is not int or not 1 <= minutes <= MAX_RUN_SECONDS // 60:
            raise Refused('invalid_input', 'a qualification run lasts 1 to %d minutes' % (MAX_RUN_SECONDS // 60))
        params['expires_at'] = now + 60 * minutes
    elif action == 'activate':
        named = qualification or status.get('qualification') or {}
        if not _text(named.get('id')) or not _text(named.get('digest')):
            raise Refused('missing_qualification', 'the running service has recorded no qualification for this run')
        params.update(qualification_id=named['id'], qualification_digest=named['digest'])
    elif action != 'stop':
        raise Refused('invalid_input', 'one of qualify, activate or stop')
    ids = status.get('authority_ids') or {}
    command_id = 'channel-%s-%s' % (action, serial or uuid.uuid4().hex)
    command = {'command_id': command_id, 'operation': AUTHORIZE, 'target': E.target(CHANNEL), 'parameters': params,
               'artifact_digests': [], 'expected_versions': {}}
    envelope = {'domain_uuid': ids.get('domain_uuid'), 'repository_uuid': ids.get('repository_uuid'),
                'store_uuid': ids.get('store_uuid'), 'schema': AC.ENVELOPE_SCHEMA, 'command_id': command_id,
                'principal': principal, 'request_revision': 1, 'nonce': 'nonce-' + command_id, 'expires_at': now + 600,
                'membership_version': status.get('membership_version'),
                'delegation_version': status.get('delegation_version'),
                'command_digest': AC.canonical_command_digest(command)}
    return envelope, command


def main(argv=None):
    """veldo channel status|qualify|activate|stop --principal <owner> --key <his enrolled private key>
    [--workspace <enrolled clone>] [--host-trust <file>] [--minutes N] [--qualification-id ID
    --qualification-digest DIGEST]. Prints one JSON answer; exit 0 accepted, 1 refused by name,
    2 usage or no route to the authority."""
    import argparse
    import os
    import sys
    parser = argparse.ArgumentParser(prog='veldo channel', description='The owner\'s Telegram edge commands, '
                                     'applied by the running authority service.')
    parser.add_argument('action', choices=COMMAND_ACTIONS)
    parser.add_argument('--workspace', default=os.getcwd(), help='an enrolled clone of this authority (default: here)')
    parser.add_argument('--principal', required=True, help='the owner, signing for himself')
    parser.add_argument('--key', required=True, help='his enrolled private key file')
    parser.add_argument('--host-trust', help='this host\'s trust file (default: the installed one)')
    parser.add_argument('--minutes', type=int, default=DEFAULT_RUN_MINUTES, help='a qualification run\'s length')
    parser.add_argument('--qualification-id')
    parser.add_argument('--qualification-digest')
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE

    def answer(value, code):
        print(json.dumps(value, sort_keys=True))
        return code

    CC, CE, EL = organ('control_client'), organ('control_enrollment'), organ('control_eligibility')
    workspace = os.path.realpath(args.workspace)
    try:
        trust = EL.load_host_trust(args.host_trust)
        binding = CE.read_binding(workspace)
    except (EL.Stopped, CE.EnrollmentRefused, OSError, ValueError) as exc:
        return answer({'action': args.action, 'outcome': 'refused', 'reason': 'unenrolled_workspace',
                       'detail': type(exc).__name__}, EXIT_USAGE)
    if trust is None or not isinstance(binding, dict):
        return answer({'action': args.action, 'outcome': 'refused', 'reason': 'unenrolled_workspace'}, EXIT_USAGE)
    verify = trust.verifier(binding.get('enrolled_by'), workspace)
    sign = ssh_signer(os.path.realpath(args.key))

    def send(packet):
        response = CC.send(workspace, packet, CE, verify, sign, trust.host_identity, timeout=60)
        if not response.get('accepted'):
            raise Refused(response.get('reason') or 'unknown_outcome', 'the authority refused the request')
        return response.get('result') or {}

    try:
        status = send({'operation': 'inspect', 'entity_ids': []}).get('channel') or {}
        if args.action == 'status':
            return answer({'action': 'status', 'outcome': 'accepted', 'channel': status}, 0)
        named = ({'id': args.qualification_id, 'digest': args.qualification_digest}
                 if args.qualification_id or args.qualification_digest else None)
        envelope, command = owner_command(args.action, status, args.principal, time.time(), minutes=args.minutes,
                                          qualification=named)
        result = send({'command': command, 'envelope': envelope,
                       'signature': sign(AC.canonical_envelope_bytes(envelope))})
    except CC.RoutingRefused as exc:
        return answer({'action': args.action, 'outcome': 'refused', 'reason': exc.reason}, EXIT_USAGE)
    except Refused as exc:
        return answer({'action': args.action, 'outcome': 'refused', 'reason': exc.code}, EXIT_REFUSED)
    shown = {'action': args.action, 'outcome': 'accepted' if result.get('ok') else 'refused',
             'reason': None if result.get('ok') else result.get('reason'), 'state': result.get('state'),
             'command_id': command['command_id']}
    if args.action == 'activate':
        shown['qualification'] = {'id': command['parameters']['qualification_id'],
                                  'digest': command['parameters']['qualification_digest']}
    return answer(shown, 0 if result.get('ok') else EXIT_REFUSED)


if __name__ == '__main__':
    raise SystemExit(main())
