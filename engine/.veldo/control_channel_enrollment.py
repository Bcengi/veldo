#!/usr/bin/env python3
"""One restricted channel edge key, enrolled under current authority (VELDO-0067 AC1, PLAN-0019 W52, R38).

WHAT THIS MODULE IS. The administrative commands that enroll the restricted signing key of one channel
edge and retire it. An enrollment is an OpenSSH-envelope Ed25519 signed command (the authority
contract's envelope, never a second spelling): its canonical digest is recomputed from the operation,
target and complete parameters to be executed, so the edge's public key, its connection key, the
channel, the edge principal and the scope are all bound, and the envelope binds this authority's
domain, repository and store, the current membership and delegation versions, a nonce and an expiry.
The signer must be a current person member holding membership_steward whose scope covers the edge's.
The edge proves that it holds the private key being enrolled: a possession proof is the edge key's own
signature over the very envelope, in a namespace of its own, so a proof made for one enrollment proves
nothing about another and is never a command signature.

WHAT IS WRITTEN. One committed transition writes, together: a service membership for the edge
principal (no roles, the enrolled scope) and the channel's edge key as a verification key at the id
the authority contract names for the channel (`authority_contract.CHANNELS[channel]['edge_key_id']`),
which is where the VELDO-0065 answer acceptance reads the edge's current key. The key record carries
the channel, the connection public key the protected signer authenticates the edge by, the effective
time sampled inside the serialized transition, and the possession proof with the envelope it signs,
so the record verifies on its own. Retirement is a signed command of the same kind that records the
retirement time; nothing else ends an enrolled key in Release 1 (rotation, restart and failover are
Release 2). After each committed change the public allowed_signers projection is republished when a
path is given, as the VELDO-0027 key lifecycle expects.

WHAT IS REFUSED, BY NAME, WITH NOTHING WRITTEN. A substituted public key or any other parameter changed
after signing, and an envelope for another domain, repository or store, a stale version, a consumed
nonce or an expired envelope (envelope_refused); a signature that does not verify (signature_invalid);
a signer who is not a current member (not_current_member), not a person (not_a_person), not a steward
(policy_refused) or whose scope does not cover the edge's (scope_refused); a self-grant: the signer
enrolled as the edge, or the signer's own key as the edge's signing or connection key
(self_grant_refused); a key another principal or channel already holds (key_in_use); an edge principal
that is already a member (principal_exists); a channel with an enrolled edge key (already_enrolled);
parameters outside the channel schema (invalid_enrollment); and a missing or wrong possession proof
(key_possession_unproven).

WHAT IT IS NOT. Enrollment activates no ingress (VELDO-0073 requires separate live Telegram proof and
an authorized activation). Release 1 enrolls the Telegram chat edge and, for VELDO-0130, the
authenticated API's own edge (channel "api"); more channels are Release 4 and Jira enrollment is dropped. Key custody is the installer's and control_keys_custody's: the private
key stays in the protected key directory the signer's fixed configuration names. Standard library only;
the authority contract, membership, key lifecycle and store are loaded as sibling organs by path.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('edge_enrollment_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


K = organ('control_keys')
CM, AC = K.CM, K.AC
SCHEMA = 'veldo.channel_edge_key/v1'
ENROLL = 'enroll_channel_edge'
RETIRE = 'retire_channel_edge'
OPERATIONS = (ENROLL, RETIRE)
# Release 1 enrolls one answer channel edge, the Telegram chat edge; more channels are Release 4.
CHANNELS = ('telegram_chat',)
# VELDO-0130: the authenticated API's own edge (authority_contract.EDGE_CHANNELS), enrolled by the same
# command. It is not an answer channel, so the pending work of `metrics` stays the Telegram edge's.
API_CHANNELS = ('api',)
ENROLLABLE = CHANNELS + API_CHANNELS
# The signed parameters of each command, exactly: nothing more is executed than was signed.
ENROLLMENT_FIELDS = ('channel', 'edge_principal', 'edge_key_id', 'public_key', 'connection_public_key', 'scope')
RETIREMENT_FIELDS = ('channel', 'edge_key_id')
# The enrolled key record and the edge's membership record, field for field.
KEY_FIELDS = ('schema', 'channel', 'principal', 'public_key', 'connection_public_key', 'scope', 'effective_at',
              'retired_at', 'revoked_at', 'enrolled_by', 'retired_by', 'enrollment_command_id', 'possession')
MEMBER_FIELDS = ('principal_type', 'roles', 'independence_group', 'scope', 'revoked_at', 'expires_at', 'enrolled_by',
                 'channel_edge')
# The possession proof's own namespace: never the command namespace, so it is never a command signature.
POSSESSION_NAMESPACE = 'veldo-edge-possession'
REFUSALS = {'forbidden_command': 'invalid_input', 'envelope_refused': 'invalid_input',
            'signature_invalid': 'missing_authority', 'journal_signer_required': 'unavailable_service',
            'not_current_member': 'missing_authority', 'not_a_person': 'missing_authority',
            'policy_refused': 'missing_authority', 'scope_refused': 'missing_authority',
            'self_grant_refused': 'missing_authority', 'key_in_use': 'invalid_input',
            'principal_exists': 'invalid_input', 'already_enrolled': 'stale_subject',
            'not_enrolled': 'stale_subject', 'invalid_enrollment': 'invalid_input',
            'key_possession_unproven': 'missing_evidence', 'store_refused': 'unavailable_service'}


class Refused(Exception):
    def __init__(self, code, detail='', versions=None):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail, self.versions = code, detail, dict(versions or {})


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def _key_text(value):
    """The OpenSSH public key as type and base64, or None when it is not one Ed25519 public key."""
    words = value.split() if isinstance(value, str) else []
    return ' '.join(words[:2]) if len(words) in (2, 3) and words[0] == 'ssh-ed25519' else None


def _path_free(value):
    return _text(value) and value.replace('-', '').replace('_', '').isalnum()


def target(channel):
    """The command target of a channel edge command: the channel it enrolls or retires."""
    return 'channel:%s' % channel


def edge_key_id(channel):
    """The id the authority contract gives a channel's restricted edge key."""
    return AC.edge_channel(channel).get('edge_key_id')


def edge_record(state, key_id):
    """The enrolled channel edge key at `key_id` in an authority state, with its id and version, or None."""
    entity = state['entities'].get(key_id) if isinstance(key_id, str) else None
    data = (entity or {}).get('data')
    if not entity or entity.get('kind') != 'verification_key' or not isinstance(data, dict) or data.get('schema') != SCHEMA:
        return None
    return dict(data, key_id=key_id, entity_version=entity.get('version'))


def active(record, at):
    """Whether an enrolled edge key signs and is accepted at `at`: effective, not retired, not revoked."""
    return record is not None and K.active(record, at)


def parameter_problems(operation, params):
    """Why command parameters are not the channel schema of `operation`, by name; [] when they are."""
    fields = ENROLLMENT_FIELDS if operation == ENROLL else RETIREMENT_FIELDS
    if not isinstance(params, dict) or set(params) != set(fields):
        return ['the parameters are exactly %s' % ', '.join(fields)]
    problems = []
    channel = params['channel']
    if channel not in ENROLLABLE or not AC.edge_channel(channel).get('enrolled'):
        problems.append('channel %r is not enrollable in this release' % (channel,))
    elif params['edge_key_id'] != edge_key_id(channel):
        problems.append('the edge key id of %s is %r' % (channel, edge_key_id(channel)))
    if operation == ENROLL:
        signing, connection = _key_text(params['public_key']), _key_text(params['connection_public_key'])
        if signing is None or connection is None:
            problems.append('the signing and connection keys are Ed25519 public keys')
        elif signing == connection:
            problems.append('the connection key is not the signing key: the edge process never holds the signing key')
        if not _path_free(params['edge_principal']):
            problems.append('the edge principal is a plain identifier')
        scope = params['scope']
        if not (isinstance(scope, list) and scope and all(_text(s) for s in scope)):
            problems.append('the scope is a non-empty list of named scopes')
    return problems


def _keys_in_use(state):
    """{public key text: holder} of every key an enrolled principal, signing key or edge holds."""
    held = {}
    for key in state['keyring']:
        text = _key_text(key.get('public_key'))
        if text:
            held.setdefault(text, key.get('principal'))
        text = _key_text(key.get('connection_public_key'))
        if text:
            held.setdefault(text, key.get('principal'))
    for kid, entity in state['entities'].items():
        if entity.get('kind') == 'signing_key':
            for field in ('public_key', 'connection_public_key'):
                text = _key_text((entity.get('data') or {}).get(field))
                if text:
                    held.setdefault(text, kid)
    return held


def _enroll_transition(params, before, refused):
    signed = {f: params.get(f) for f in ENROLLMENT_FIELDS}
    if parameter_problems(ENROLL, signed) or not _text(params.get('enrolled_by')) or not isinstance(params.get('possession'), dict):
        raise refused('transition_refused', 'an edge enrollment carries the channel schema, its signer and its possession proof')
    kid, edge = signed['edge_key_id'], signed['edge_principal']
    if kid in before or edge in before:
        raise refused('transition_refused', 'the channel edge key and its principal are new')
    # Sampled inside the serialized transition, after the store lock: effective time follows every
    # signature committed before it.
    at = time.time()
    member = {'principal_type': 'service', 'roles': [], 'independence_group': None, 'scope': list(signed['scope']),
              'revoked_at': None, 'expires_at': None, 'enrolled_by': params['enrolled_by'], 'channel_edge': signed['channel']}
    key = {'schema': SCHEMA, 'channel': signed['channel'], 'principal': edge, 'public_key': _key_text(signed['public_key']),
           'connection_public_key': _key_text(signed['connection_public_key']), 'scope': list(signed['scope']),
           'effective_at': at, 'retired_at': None, 'revoked_at': None, 'enrolled_by': params['enrolled_by'],
           'retired_by': None, 'enrollment_command_id': params.get('command_id'), 'possession': params['possession']}
    return {edge: {'kind': 'membership', 'data': member}, kid: {'kind': 'verification_key', 'data': key},
            CM.VERSIONS_ENTITY: CM._bump(before, 'membership_version')}


def _retire_transition(params, before, refused):
    kid = params.get('edge_key_id')
    old = before.get(kid) if isinstance(kid, str) else None
    data = (old or {}).get('data') or {}
    if not old or old.get('kind') != 'verification_key' or data.get('schema') != SCHEMA or data.get('channel') != params.get('channel'):
        raise refused('transition_refused', 'retire_channel_edge names an enrolled channel edge key')
    if data.get('retired_at') is not None or not _text(params.get('retired_by')):
        raise refused('transition_refused', 'the edge key is retired once, by its signer')
    at = time.time()
    if at < data['effective_at']:
        raise refused('transition_refused', 'retirement does not precede enrollment')
    return {kid: {'kind': 'verification_key', 'data': dict(data, retired_at=at, retired_by=params['retired_by'])},
            CM.VERSIONS_ENTITY: CM._bump(before, 'membership_version')}


class Enrollment:
    """Admits channel edge enrollment and retirement commands on one store connection.

    `store` is the control_store module; `conn` its connection; `authority_ids` this authority's
    domain_uuid, repository_uuid and store_uuid; `sign(bytes) -> text` signs journal records as
    `journal_signer`; `projection` is the allowed_signers path republished after each commit.
    Observations record the operation, authority, channel, key id, signer, accepted versions, outcome
    and named refusal with its error class, never a key, a signature or a proof."""

    def __init__(self, store, conn, authority_ids, journal_signer, sign, projection=None, authority_generation=1,
                 clock=time.time):
        self.S, self.conn = store, conn
        self.ids = {f: authority_ids.get(f) for f in ('domain_uuid', 'repository_uuid', 'store_uuid')}
        self.journal_signer, self.sign = journal_signer, sign
        self.projection, self.authority_generation, self.clock = projection, authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        writes = ('entities', 'journal', 'commands', 'nonces')
        conn.command_registry[ENROLL] = {'transition': lambda p, b: _enroll_transition(p, b, store.StoreRefused),
                                         'writes': writes}
        conn.command_registry[RETIRE] = {'transition': lambda p, b: _retire_transition(p, b, store.StoreRefused),
                                         'writes': writes}

    def state(self):
        return CM.authority_state(self.S, self.conn)

    def edge(self, channel):
        """The channel's enrolled edge key record, current or not, or None."""
        return edge_record(self.state(), edge_key_id(channel))

    def admit(self, envelope, command, signature, possession=None):
        """Admit one signed enroll_channel_edge or retire_channel_edge command, or refuse it by name
        with nothing written. Returns the observation of the outcome."""
        command = command if isinstance(command, dict) else {}
        params = command.get('parameters') if isinstance(command.get('parameters'), dict) else {}
        about = {'operation': command.get('operation'), 'command_id': command.get('command_id'),
                 'channel': params.get('channel'), 'edge_key_id': params.get('edge_key_id'),
                 'principal': envelope.get('principal') if isinstance(envelope, dict) else None}
        try:
            committed, versions = self._admit(envelope, command, signature, possession, params)
        except Refused as exc:
            return self._observe(about, 'refused', exc.code, exc.versions)
        return self._observe(about, 'accepted', None, versions, seq=committed.get('seq'))

    def _admit(self, envelope, command, signature, possession, params):
        operation = command.get('operation')
        if operation not in OPERATIONS:
            raise Refused('forbidden_command', 'only channel edge enrollment and retirement are admitted here')
        if not isinstance(envelope, dict) or envelope.get('command_id') != command.get('command_id') or not _text(command.get('command_id')):
            raise Refused('envelope_refused', 'the executed command is the signed command')
        if not _text(self.journal_signer) or not callable(self.sign):
            raise Refused('journal_signer_required', 'the authority signs every journal record')
        now = self.clock()
        state = self.state()
        versions = {CM.VERSIONS_ENTITY: state['versions_entity_version']}
        signer = envelope.get('principal')
        entry = AC.membership_entry(state['membership'], signer)
        if not AC.active_member(entry, now)[0]:
            raise Refused('not_current_member', 'the signer is not a current member', versions)
        authority = dict(self.ids, membership_version=state['membership_version'],
                         delegation_version=state['delegation_version'])
        seen = set(self.S.materialized_state(self.conn)['nonces'])
        problems = AC.envelope_problems(envelope, command, authority, now, seen, state['keyring'], state['membership'])
        if problems:
            raise Refused('envelope_refused', '; '.join(problems), versions)
        key = AC.active_key(state['keyring'], signer, now)
        ok, _ = AC.ssh_keygen_verify(AC.canonical_envelope_bytes(envelope), signature if isinstance(signature, str) else '',
                                     AC.allowed_signers_line(signer, key['public_key']), signer)
        if not ok:
            raise Refused('signature_invalid', 'the signature does not verify with the signer\'s active key', versions)
        if entry.get('principal_type') != 'person':
            raise Refused('not_a_person', 'a service, policy or agent run enrolls no edge', versions)
        if CM.STEWARD_ROLE not in (entry.get('roles') or []):
            raise Refused('policy_refused', 'edge enrollment is a membership change: the signer holds %s' % CM.STEWARD_ROLE, versions)
        problems = parameter_problems(operation, params)
        if problems or command.get('target') != target(params.get('channel')):
            raise Refused('invalid_enrollment', '; '.join(problems) or 'the target is the channel', versions)
        kid = params['edge_key_id']
        record = edge_record(state, kid)
        versions[kid] = state['entities'].get(kid, {}).get('version', 0)
        if operation == RETIRE and (record is None or record.get('retired_at') is not None):
            raise Refused('not_enrolled', 'no current enrolled edge key to retire', versions)
        scope = record['scope'] if operation == RETIRE else params['scope']
        if not CM.scope_covers(entry.get('scope'), scope):
            raise Refused('scope_refused', 'the signer\'s scope does not cover the edge scope', versions)
        if operation == RETIRE:
            stored = dict(params, retired_by=signer)
        else:
            own = _key_text((key or {}).get('public_key'))
            if params['edge_principal'] == signer or own in (_key_text(params['public_key']), _key_text(params['connection_public_key'])):
                raise Refused('self_grant_refused', 'a signer never enrolls itself or its own key as an edge', versions)
            if kid in state['entities']:
                raise Refused('already_enrolled', 'the channel has an enrolled edge key; rotation is Release 2', versions)
            edge = params['edge_principal']
            versions[edge] = state['entities'].get(edge, {}).get('version', 0)
            if edge in state['entities']:
                raise Refused('principal_exists', 'the edge principal is a new service principal', versions)
            held = _keys_in_use(state)
            if any(_key_text(params[f]) in held for f in ('public_key', 'connection_public_key')):
                raise Refused('key_in_use', 'the edge keys are new keys', versions)
            ok, _ = AC.ssh_keygen_verify(AC.canonical_envelope_bytes(envelope), possession if isinstance(possession, str) else '',
                                         AC.allowed_signers_line(edge, params['public_key'], POSSESSION_NAMESPACE), edge,
                                         POSSESSION_NAMESPACE)
            if not ok:
                raise Refused('key_possession_unproven', 'the edge key\'s own signature over this envelope does not verify', versions)
            stored = dict(params, enrolled_by=signer, command_id=command['command_id'],
                          possession={'namespace': POSSESSION_NAMESPACE, 'envelope': dict(envelope), 'signature': possession})
        committed = dict(command, principal=signer, nonce=envelope['nonce'], parameters=stored,
                         expected_versions=dict(versions), artifact_digests=[])
        try:
            result = self.S.execute(self.conn, committed, self.journal_signer, self.sign, self.authority_generation, committed_at=now)
        except self.S.StoreRefused as exc:
            raise Refused('store_refused', exc.code, versions)
        if self.projection is not None:
            K.publish(self.S, self.conn, self.projection)
        return result, versions

    def _observe(self, about, outcome, refusal, versions, **extra):
        self.counts['accepted' if outcome == 'accepted' else 'refused'] += 1
        observation = dict(self.ids, **about, accepted_versions=dict(versions or {}), outcome=outcome, refusal=refusal,
                           error_class=None if refusal is None else REFUSALS.get(refusal, 'unknown_outcome'), **extra)
        self.observations.append(observation)
        return observation

    def metrics(self):
        """Accepted and refused commands, and per Release 1 channel whether its edge key is enrolled and
        current; the pending work of this specification is every channel without a current edge key."""
        state, now = self.state(), self.clock()
        current = {c: active(edge_record(state, edge_key_id(c)), now) for c in CHANNELS}
        return dict(self.counts, enrolled=sorted(c for c, ok in current.items() if ok),
                    retired=sorted(c for c in CHANNELS if (edge_record(state, edge_key_id(c)) or {}).get('retired_at') is not None),
                    pending=sorted(c for c, ok in current.items() if not ok))


def possession_digest(record):
    """The digest of an enrolled key's possession proof as recorded (for observations and proof, which
    never carry the signature itself)."""
    proof = (record or {}).get('possession') or {}
    return 'sha256:' + hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
