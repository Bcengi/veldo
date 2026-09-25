#!/usr/bin/env python3
"""Passkey credentials of person members, enrolled and revoked under current authority (VELDO-0130).

WHAT THIS MODULE IS. The owner of the store kind `api_credential` and of its two commands,
`enroll_api_credential` and `revoke_api_credential`. A passkey belongs to exactly one current person
member of this membership authority. Both commands are OpenSSH-envelope signed commands (the authority
contract's envelope, never a second spelling, as VELDO-0067 enrolls an edge key): the canonical digest
is recomputed from the operation, target and complete parameters, and the envelope binds this
authority's domain, repository and store, the current membership and delegation versions, a nonce and
an expiry.

ENROLLMENT HAS TWO HALVES. On the new device the API runs a registration ceremony and at once a
sign-in ceremony with the new credential whose challenge is SHA-256 of the canonical registration
binding (relying-party id, origin, credential id, public key, algorithm, label, user handle, a fresh
nonce and the pending registration's expiry): that assertion is the possession proof, and the API
keeps the pending registration in a 0600 file, granting nothing. On the host a current person member
holding membership_steward whose scope covers the principal's signs enroll_api_credential naming the
principal, the binding and the proof. Before commit the proof is verified again with OpenSSL
(control_api_webauthn), so the record verifies on its own. Refused by name with nothing written: an
envelope for another authority, a stale version, a consumed nonce or an expired envelope
(envelope_refused); a signature that does not verify (signature_invalid); a signer who is not a current
member (not_current_member), not a person (not_a_person), not a steward (policy_refused) or whose scope
does not cover the principal's (scope_refused); a principal who is not a current person member
(principal_not_member); parameters outside the schema (invalid_credential); an expired pending
registration (registration_expired); a credential id or key any record holds (credential_in_use); and a
proof that does not verify (possession_unproven). The owner enrolls his own passkeys this way: a
credential grants no role, so it is not a self-grant.

REVOCATION is revoke_api_credential, signed by a steward at the host (`admit`) or sent by a steward's
own API session as an edge assertion the authority has verified (`revoke_as_member`, VELDO-0130's
control_api_authority). A credential is CURRENT (`current`) only while it is effective, not revoked, and
its principal is a current person member, so revoke_membership ends every credential of the member with
it, read at every use, with no second write.

WHAT IT IS NOT. An API session can never enroll a credential: nothing here accepts an edge assertion
for enrollment. Not rotation policy or attestation (Release 2 and 3). Observations carry identities,
versions and the named refusal, never a key, a signature or a proof. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('api_credentials_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


K = organ('control_keys')
CM, AC = K.CM, K.AC
W = organ('control_api_webauthn')
SCHEMA = 'veldo.api_credential/v1'
KIND = 'api_credential'
ENROLL, REVOKE = 'enroll_api_credential', 'revoke_api_credential'
OPERATIONS = (ENROLL, REVOKE)
OWNER = 'VELDO-0130 api credentials'
WRITES = ('entities', 'journal', 'commands', 'nonces')
ENROLL_FIELDS = ('principal', 'binding', 'proof')
REVOKE_FIELDS = ('credential_id',)
PROOF_FIELDS = ('client_data_json', 'authenticator_data', 'signature', 'user_handle')
RECORD_FIELDS = ('schema', 'principal', 'credential_id', 'public_key', 'algorithm', 'user_handle', 'rp_id', 'origin',
                 'label', 'effective_at', 'revoked_at', 'revoked_by', 'enrolled_by', 'proof', 'envelope', 'command_id')
LABEL_LIMIT = 64
REFUSALS = {'forbidden_command': 'invalid_input', 'envelope_refused': 'invalid_input',
            'signature_invalid': 'unauthenticated', 'journal_signer_required': 'unavailable_service',
            'not_current_member': 'unauthorized', 'not_a_person': 'unauthorized', 'policy_refused': 'unauthorized',
            'scope_refused': 'unauthorized', 'principal_not_member': 'unauthorized',
            'invalid_credential': 'invalid_input', 'registration_expired': 'stale_version',
            'credential_in_use': 'invalid_input', 'possession_unproven': 'missing_evidence',
            'not_enrolled': 'stale_version', 'store_refused': 'unavailable_service'}


class Refused(Exception):
    def __init__(self, code, detail='', versions=None):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail, self.versions = code, detail, dict(versions or {})


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def entity_id(credential_id):
    """The store id of a credential: its id digested, so no browser-chosen text becomes a store key."""
    return 'api-credential:' + hashlib.sha256(str(credential_id).encode('utf-8')).hexdigest()[:32]


def target(credential_id):
    return 'api_credential:' + entity_id(credential_id).split(':', 1)[1]


def record(entities, credential_id):
    """The api_credential record of `credential_id` in committed entities, current or not, or None."""
    entity = entities.get(entity_id(credential_id)) if isinstance(credential_id, str) else None
    data = (entity or {}).get('data')
    if not entity or entity.get('kind') != KIND or not isinstance(data, dict) or data.get('credential_id') != credential_id:
        return None
    return dict(data, entity_version=entity.get('version'))


def current(state, credential_id, now, principal=None):
    """(record, None) when the credential is current at `now` (effective, not revoked, its principal a
    current person member, and `principal` when named), else (record or None, the named reason)."""
    found = record(state['entities'], credential_id)
    if found is None:
        return None, 'unknown_credential'
    if found.get('effective_at') is None or found['effective_at'] > now:
        return found, 'credential_not_effective'
    if found.get('revoked_at') is not None and found['revoked_at'] <= now:
        return found, 'credential_revoked'
    if principal is not None and found.get('principal') != principal:
        return found, 'credential_of_another_principal'
    member = AC.membership_entry(state['membership'], found.get('principal'))
    if not AC.active_member(member, now)[0]:
        return found, 'principal_not_member'
    if member.get('principal_type') != 'person':
        return found, 'principal_not_person'
    return found, None


def parameter_problems(operation, params):
    """Why command parameters are not the schema of `operation`, by name; [] when they are."""
    fields = ENROLL_FIELDS if operation == ENROLL else REVOKE_FIELDS
    if not isinstance(params, dict) or set(params) != set(fields):
        return ['the parameters are exactly %s' % ', '.join(fields)]
    if operation == REVOKE:
        return [] if _text(params['credential_id']) else ['the credential id is named']
    problems = []
    binding, proof = params['binding'], params['proof']
    if not _text(params['principal']):
        problems.append('the principal is named')
    if not isinstance(binding, dict) or set(binding) != set(W.BINDING_FIELDS) or binding.get('schema') != W.BINDING_SCHEMA:
        return problems + ['the binding is the canonical registration binding']
    if not isinstance(proof, dict) or set(proof) != set(PROOF_FIELDS):
        problems.append('the proof is one assertion')
    for check in (W.credential_id_problem(binding['credential_id']), W.key_problem(binding['public_key'], binding['algorithm'])):
        if check:
            problems.append(check)
    handle = W.unb64url(binding['user_handle'])
    if handle is None or len(handle) != W.USER_HANDLE_BYTES:
        problems.append('the user handle is 16 random bytes')
    label = binding['label']
    if not _text(label) or len(label) > LABEL_LIMIT or not label.isprintable():
        problems.append('the label is printable text of at most %d characters' % LABEL_LIMIT)
    if type(binding['expires_at']) not in (int, float) or not _text(binding['nonce']):
        problems.append('the binding names its nonce and expiry')
    return problems


def _held(entities):
    """{credential id or public key: principal} of every api_credential record, revoked ones included."""
    held = {}
    for entity in entities.values():
        data = entity.get('data') if entity.get('kind') == KIND else None
        if isinstance(data, dict):
            for field in ('credential_id', 'public_key'):
                if _text(data.get(field)):
                    held.setdefault(data[field], data.get('principal'))
    return held


def _transition(params, before, refused):
    operation = params.get('operation')
    eid = params.get('entity_id')
    old = before.get(eid) if isinstance(eid, str) else None
    if operation == ENROLL:
        data = params.get('record')
        if old is not None or not isinstance(data, dict) or set(data) != set(RECORD_FIELDS):
            raise refused('transition_refused', 'an api credential is enrolled once, as a complete record')
        # Sampled inside the serialized transition: effective after every command committed before it.
        return {eid: {'kind': KIND, 'data': dict(data, effective_at=time.time())}}
    data = (old or {}).get('data') or {}
    if not old or old.get('kind') != KIND or data.get('revoked_at') is not None or not _text(params.get('revoked_by')):
        raise refused('transition_refused', 'revoke_api_credential names a current api credential, once')
    return {eid: {'kind': KIND, 'data': dict(data, revoked_at=max(time.time(), data['effective_at']),
                                             revoked_by=params['revoked_by'])}}


class Credentials:
    """Admits api_credential enrollment and revocation on one authority store connection.

    `store` is the control_store module; `conn` its connection; `authority_ids` this authority's
    domain_uuid, repository_uuid and store_uuid; `sign(bytes) -> text` signs journal records as
    `journal_signer`; `rp_id` and `origin` are the configured relying party and origin; `state_dir`
    holds the private directories OpenSSL verifies in."""

    def __init__(self, store, conn, authority_ids, journal_signer, sign, *, rp_id, origin, state_dir,
                 authority_generation=1, clock=time.time):
        self.S, self.conn = store, conn
        self.ids = {f: authority_ids.get(f) for f in ('domain_uuid', 'repository_uuid', 'store_uuid')}
        self.journal_signer, self.sign, self.generation, self.clock = journal_signer, sign, authority_generation, clock
        self.rp_id, self.origin, self.state_dir = rp_id, origin, state_dir
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        for operation in OPERATIONS:
            conn.command_registry[operation] = {'transition': lambda p, b: _transition(p, b, store.StoreRefused),
                                                'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: OPERATIONS}, module=__file__)

    def state(self):
        return CM.authority_state(self.S, self.conn)

    def credential(self, credential_id):
        return record(self.state()['entities'], credential_id)

    def admit(self, envelope, command, signature):
        """Admit one steward-signed enroll_api_credential or revoke_api_credential command, or refuse it
        by name with nothing written. Returns the observation."""
        command = command if isinstance(command, dict) else {}
        params = command.get('parameters') if isinstance(command.get('parameters'), dict) else {}
        binding = params.get('binding') if isinstance(params.get('binding'), dict) else {}
        about = {'operation': command.get('operation'), 'command_id': command.get('command_id'),
                 'credential_id': params.get('credential_id') or binding.get('credential_id'),
                 'principal': params.get('principal'),
                 'signer': envelope.get('principal') if isinstance(envelope, dict) else None}
        try:
            committed, versions = self._admit(envelope, command, signature, params)
        except Refused as exc:
            return self._observe(about, 'refused', exc.code, exc.versions)
        return self._observe(about, 'accepted', None, versions, seq=committed.get('seq'))

    def _admit(self, envelope, command, signature, params):
        operation = command.get('operation')
        if operation not in OPERATIONS:
            raise Refused('forbidden_command', 'only api credential enrollment and revocation are admitted here')
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
        problems = parameter_problems(operation, params)
        credential_id = params.get('credential_id') if operation == REVOKE else (params.get('binding') or {}).get('credential_id')
        if problems or command.get('target') != target(credential_id):
            raise Refused('invalid_credential', '; '.join(problems) or 'the target is the credential', versions)
        return self._commit(operation, params, signer, entry, state, now, versions, dict(envelope), command)

    def revoke_as_member(self, member, credential_id, provenance):
        """revoke_api_credential sent by a steward's own API session: `member` is the session's principal
        as the authority verified the edge assertion that carries it (control_api_authority), and
        `provenance` names the channel, edge, request id, credential and assertion digest."""
        about = {'operation': REVOKE, 'command_id': None, 'credential_id': credential_id, 'principal': None, 'signer': member}
        try:
            now, state = self.clock(), self.state()
            versions = {CM.VERSIONS_ENTITY: state['versions_entity_version']}
            entry = AC.membership_entry(state['membership'], member)
            if not AC.active_member(entry, now)[0]:
                raise Refused('not_current_member', 'the member is not current', versions)
            if not _text(credential_id):
                raise Refused('invalid_credential', 'the credential id is named', versions)
            command = {'command_id': 'api-revoke:' + str(provenance.get('request_id')), 'operation': REVOKE,
                       'target': target(credential_id), 'parameters': {'credential_id': credential_id}}
            committed, versions = self._commit(REVOKE, command['parameters'], member, entry, state, now, versions,
                                               {'provenance': dict(provenance)}, command)
        except Refused as exc:
            return self._observe(about, 'refused', exc.code, exc.versions)
        return self._observe(about, 'accepted', None, versions, seq=committed.get('seq'))

    def _commit(self, operation, params, signer, entry, state, now, versions, envelope, command):
        if entry.get('principal_type') != 'person':
            raise Refused('not_a_person', 'a service, policy or agent run enrolls no credential', versions)
        if CM.STEWARD_ROLE not in (entry.get('roles') or []):
            raise Refused('policy_refused', 'a credential is a membership change: the signer holds %s' % CM.STEWARD_ROLE, versions)
        entities = state['entities']
        if operation == REVOKE:
            found = record(entities, params['credential_id'])
            eid = entity_id(params['credential_id'])
            versions[eid] = entities.get(eid, {}).get('version', 0)
            if found is None or found.get('revoked_at') is not None:
                raise Refused('not_enrolled', 'no unrevoked api credential to revoke', versions)
            principal = found['principal']
        else:
            principal, binding = params['principal'], params['binding']
            eid = entity_id(binding['credential_id'])
            versions[eid] = entities.get(eid, {}).get('version', 0)
        member = AC.membership_entry(state['membership'], principal)
        versions[principal] = entities.get(principal, {}).get('version', 0) if isinstance(principal, str) else 0
        if operation == ENROLL and (not AC.active_member(member, now)[0] or member.get('principal_type') != 'person'):
            raise Refused('principal_not_member', 'a passkey belongs to a current person member', versions)
        if not CM.scope_covers(entry.get('scope'), (member or {}).get('scope')):
            raise Refused('scope_refused', 'the signer\'s scope does not cover the principal\'s', versions)
        if operation == ENROLL:
            if binding['expires_at'] <= now:
                raise Refused('registration_expired', 'the pending registration expired', versions)
            held = _held(entities)
            if binding['credential_id'] in held or binding['public_key'] in held:
                raise Refused('credential_in_use', 'the credential id and key are new', versions)
            if W.possession_problems(binding, params['proof'], self.origin, self.rp_id, self.state_dir):
                raise Refused('possession_unproven', 'the possession assertion does not verify', versions)
            data = {'schema': SCHEMA, 'principal': principal, 'credential_id': binding['credential_id'],
                    'public_key': binding['public_key'], 'algorithm': binding['algorithm'],
                    'user_handle': binding['user_handle'], 'rp_id': binding['rp_id'], 'origin': binding['origin'],
                    'label': binding['label'], 'effective_at': None, 'revoked_at': None, 'revoked_by': None,
                    'enrolled_by': signer, 'proof': {'binding': dict(binding), 'assertion': dict(params['proof'])},
                    'envelope': envelope, 'command_id': command['command_id']}
            stored = {'operation': ENROLL, 'entity_id': eid, 'record': data}
        else:
            stored = {'operation': REVOKE, 'entity_id': eid, 'revoked_by': signer, 'envelope': envelope}
        nonce = envelope.get('nonce') or command['command_id']
        committed = dict(command_id=command['command_id'], principal=signer, operation=operation, parameters=stored,
                         expected_versions=dict(versions), artifact_digests=[], nonce=nonce)
        try:
            result = self.S.execute(self.conn, committed, self.journal_signer, self.sign, self.generation, committed_at=now)
        except self.S.StoreRefused as exc:
            raise Refused('store_refused', exc.code, versions)
        return result, versions

    def _observe(self, about, outcome, refusal, versions, **extra):
        self.counts['accepted' if outcome == 'accepted' else 'refused'] += 1
        observation = dict(self.ids, **about, accepted_versions=dict(versions or {}), outcome=outcome, refusal=refusal,
                           error_class=None if refusal is None else REFUSALS.get(refusal, 'unknown_outcome'), **extra)
        self.observations.append(observation)
        return observation

    def metrics(self):
        """Accepted and refused commands and the credentials by state (current, revoked)."""
        state, now = self.state(), self.clock()
        records = [e['data'] for e in state['entities'].values() if e.get('kind') == KIND]
        live = sum(1 for r in records if current(state, r.get('credential_id'), now)[1] is None)
        return dict(self.counts, current=live, revoked=sum(1 for r in records if r.get('revoked_at') is not None))


def describe(pending):
    """What the enrollment tool shows the steward before signing: the label and the key's fingerprint."""
    binding = (pending or {}).get('binding') or {}
    return {'label': binding.get('label'), 'fingerprint': W.fingerprint(binding.get('public_key')),
            'expires_at': binding.get('expires_at'), 'origin': binding.get('origin')}


def enrollment_command(pending, principal, command_id):
    """The command the steward signs for one pending registration and the principal it belongs to."""
    binding = pending['binding']
    return {'command_id': command_id, 'operation': ENROLL, 'target': target(binding['credential_id']),
            'parameters': {'principal': principal, 'binding': dict(binding), 'proof': dict(pending['proof'])},
            'artifact_digests': [], 'expected_versions': {}}


def main(argv):
    """`show <pending file>`: print what a steward checks before signing the enrollment."""
    if len(argv) != 3 or argv[1] != 'show':
        print('usage: control_api_credentials.py show <pending registration file>', file=sys.stderr)
        return 64
    print(json.dumps(describe(json.loads(Path(argv[2]).read_text())), indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
