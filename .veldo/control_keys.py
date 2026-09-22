#!/usr/bin/env python3
"""Accepted signing-key lifecycle, never authority from a worker's projection.

attach/admit extend the existing journaled control store. The operator supplies the
store and projection locations, never the request. Private keys are supplied only to
the installed signer, outside repositories. This module neither installs custody nor
enrolls a live channel. Projection repair is deterministic after a committed crash.
"""
import importlib.util
import json
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('signing_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CM = organ('control_membership')
AC = CM.AC
OPERATIONS = ('register_signing_key', 'rotate_signing_key', 'retire_signing_key', 'revoke_signing_key')
NAMESPACE = 'veldo-receipt'


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def entries(state):
    return {eid: dict(e['data'], key_id=eid, revision=e['version'])
            for eid, e in state['entities'].items() if e['kind'] == 'signing_key'}


def active(key, at):
    return (key['effective_at'] <= at and
            all(key.get(f) is None or at < key[f] for f in ('retired_at', 'revoked_at')))


def _transition(params, before, operation, refused):
    at, kid = params['accepted_at'], params['key_id']
    old = before.get(kid)
    if operation in ('retire_signing_key', 'revoke_signing_key'):
        if not old or old['kind'] != 'signing_key' or at < old['data']['effective_at']:
            raise refused('transition_refused', 'unknown key or backwards time')
        field = 'retired_at' if operation == 'retire_signing_key' else 'revoked_at'
        if old['data'].get(field) is not None:
            raise refused('transition_refused', 'transition already accepted')
        changes = {kid: {'kind': 'signing_key', 'data': dict(old['data'], **{field: at})}}
    else:
        if old or not isinstance(kid, str) or not kid.replace('-', '').isalnum():
            raise refused('transition_refused', 'key id must be new and path-free')
        channel = params.get('channel')
        if channel != 'evidence' and not AC.CHANNELS.get(channel, {}).get('enrolled'):
            raise refused('transition_refused', 'unknown channel')
        for field in ('public_key', 'connection_public_key'):
            words = str(params.get(field, '')).split()
            if len(words) != 2 or words[0] != 'ssh-ed25519':
                raise refused('transition_refused', 'Ed25519 public keys required')
        if any(e['kind'] == 'signing_key' and e['data']['channel'] != channel and
               e['data']['connection_public_key'] == params['connection_public_key'] for e in before.values()):
            raise refused('transition_refused', 'connection key belongs to another channel')
        prior = [(i, e) for i, e in before.items() if e['kind'] == 'signing_key'
                 and e['data']['channel'] == channel and active(e['data'], at)]
        if (operation == 'register_signing_key' and prior) or (operation == 'rotate_signing_key' and len(prior) != 1):
            raise refused('transition_refused', 'registration/rotation state mismatch')
        changes = {kid: {'kind': 'signing_key', 'data': {
            'channel': channel, 'public_key': params['public_key'],
            'connection_public_key': params['connection_public_key'],
            'effective_at': at, 'retired_at': None, 'revoked_at': None}}}
        for previous, entry in prior:
            changes[previous] = {'kind': 'signing_key', 'data': dict(entry['data'], retired_at=at)}
    changes[CM.VERSIONS_ENTITY] = CM._bump(before, 'membership_version')
    return changes


def attach(store):
    for operation in OPERATIONS:
        store.COMMAND_REGISTRY[operation] = {
            'transition': lambda p, b, op=operation: _transition(p, b, op, store.StoreRefused),
            'writes': ('entities', 'journal', 'commands', 'nonces')}


def admit(store, conn, envelope, command, signature, authority_ids, journal_signer, projection_path):
    """Person steward signature, current membership, replay protection and snapshot CAS.

    Times are the authority's clock at admission, never a caller's backdated value.
    Projection publication follows commit; readers fail closed until repaired.
    """
    now = time.time()
    state = CM.authority_state(store, conn)
    authority = dict(authority_ids, membership_version=state['membership_version'],
                     delegation_version=state['delegation_version'])
    if command.get('operation') not in OPERATIONS or envelope.get('command_id') != command.get('command_id'):
        raise Refused('forbidden-command')
    keyring = administrative_keyring(state, projection_path)
    ok, _ = AC.verify_signed_command(envelope, command, signature, authority, now,
                                    set(store.materialized_state(conn)['nonces']), keyring, state['membership'])
    if not ok:
        raise Refused('command-authentication')
    member = CM._member(state, envelope['principal'])
    if member['principal_type'] != 'person' or CM.STEWARD_ROLE not in member['roles'] or member['scope'] != '*':
        raise Refused('membership-steward-required')
    if not journal_signer:
        raise Refused('journal-signer-required')
    params = dict(command['parameters'], accepted_at=now)
    # Every signing key is in the snapshot: registration cannot miss a concurrent
    # rotation, and the common versions entity serializes all membership changes.
    ids = set(entries(state)) | {params['key_id'], CM.VERSIONS_ENTITY}
    stored = dict(command, principal=envelope['principal'], nonce=envelope['nonce'], parameters=params,
                  expected_versions={i: state['entities'].get(i, {}).get('version', 0) for i in ids})
    return store.execute(conn, stored, journal_signer[0], journal_signer[1],
                         authority_ids.get('authority_generation', 1), committed_at=now)


def projection(state):
    lines = ['# Accepted signing keys; historical keys are verification-only.']
    for kid, key in sorted(entries(state).items()):
        lines.append(AC.allowed_signers_line(key['channel'] + ':' + kid, key['public_key'], NAMESPACE))
    for key in state['keyring']:
        lines.append(AC.allowed_signers_line(key['principal'], key['public_key']))
    return '\n'.join(lines) + '\n'


def administrative_keyring(state, projection_path):
    """The file corroborates accepted authority; branch-added keys grant nothing."""
    body = Path(projection_path).read_text()
    if body != projection(state):
        raise Refused('projection-mismatch')
    return state['keyring']


def publish(store, conn, path):
    """Atomic, rebuildable public projection of the accepted store, including history."""
    import os
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn.execute('BEGIN IMMEDIATE')
    try:
        body = projection(CM.authority_state(store, conn))
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(body)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        conn.execute('ROLLBACK')


def select(state, path, channel, at):
    """Resolve the authenticated channel in the authority's OWN checked key file."""
    body = Path(path).read_text()
    if body != projection(state):
        raise Refused('projection-mismatch')
    candidates = [k for k in entries(state).values() if k['channel'] == channel and active(k, at)]
    if len(candidates) != 1:
        raise Refused('revoked-key')
    selected = candidates[0]
    line = AC.allowed_signers_line(channel + ':' + selected['key_id'], selected['public_key'], NAMESPACE)
    if line not in body.splitlines():
        raise Refused('projection-mismatch')
    return selected


def verify(state, receipt, fresh=False, now=None):
    """Historical verification uses the signed effective time; fresh use rechecks now.

    A receipt signature is NOT an administrative command signature (separate namespace).
    The accepted key transition revision and channel are also bound into the receipt.
    """
    envelope = receipt.get('envelope', {})
    key = entries(state).get(envelope.get('key_id'))
    at = envelope.get('signed_at')
    if not key or not isinstance(at, (float, int)) or not active(key, at):
        return False
    if envelope.get('channel') != key['channel'] or envelope.get('key_effective_at') != key['effective_at']:
        return False
    if fresh and not active(key, time.time() if now is None else now):
        return False
    message = json.dumps(envelope, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ok, _ = AC.ssh_keygen_verify(message, receipt.get('signature', ''),
                               AC.allowed_signers_line(key['channel'] + ':' + key['key_id'], key['public_key'], NAMESPACE),
                               key['channel'] + ':' + key['key_id'], NAMESPACE)
    return ok
