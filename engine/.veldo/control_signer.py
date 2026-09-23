#!/usr/bin/env python3
"""One authenticated pipe exchange, one restricted receipt, then exit.

The installed caller fixes the authority config and executable. Request bytes cannot
choose either. Authentication is a fresh Ed25519 challenge proof under a separately
registered connection key; channel comes from that registration, never JSON claims.
This is a core API, not the W32 installer or live platform evidence acquisition (E).
The authority's accepted store contains captured evidence and edge source records.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('signer_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


K = organ('control_keys')
S = organ('control_store')
CM, AC = K.CM, K.AC
AUTH_NAMESPACE = 'veldo-signer-connection'
SCHEMA = 'veldo.protected_receipt/v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()


def sign_bytes(path, message, namespace):
    """Only internal canonical envelopes reach this helper; output never includes stderr."""
    result = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', namespace],
                            input=message, capture_output=True, timeout=10,
                            env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
    if result.returncode:
        raise K.Refused('signing-unavailable')
    return result.stdout.decode()


def authenticate(state, challenge, request, identity, signature, now):
    key = K.entries(state).get(identity)
    if not key:
        raise K.Refused('unauthenticated-channel')
    message = canonical({'challenge': challenge, 'request_digest': digest(request)})
    ok, _ = AC.ssh_keygen_verify(message, signature,
                               AC.allowed_signers_line(identity, key['connection_public_key'], AUTH_NAMESPACE),
                               identity, AUTH_NAMESPACE)
    if not ok:
        raise K.Refused('unauthenticated-channel')
    if not K.active(key, now):
        raise K.Refused('revoked-key')
    return key['channel']


def record(store, conn, identity, kind, data, journal_signer):
    """Authority-side capture storage. No untrusted sign request can call this path.

    The caller is the evidence/platform acquisition service under its accepted
    contract, not a worker. Live platform qualification remains E.
    """
    command = {'command_id': secrets.token_hex(16), 'principal': 'evidence-service',
               'operation': 'upsert_entity', 'nonce': secrets.token_hex(16),
               'parameters': {'entity_id': identity, 'kind': kind, 'data': data},
               'expected_versions': {identity: 0}, 'artifact_digests': [digest(data)]}
    return store.execute(conn, command, journal_signer[0], journal_signer[1], 1)


def capture(store, conn, identity, argv, provenance, journal_signer):
    """Observe a real tool child: argv, exit and output bytes are measured here.

    Actor/contract provenance is supplied by the trusted invoker. It never comes
    from the process's output. The process's interpretation remains an assertion.
    """
    executable = Path(shutil.which(argv[0]) or argv[0]).resolve()
    executable_digest = 'sha256:' + hashlib.sha256(executable.read_bytes()).hexdigest()
    child = subprocess.Popen([str(executable), *argv[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = child.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()
        raise K.Refused('capture-timeout')
    if executable_digest != 'sha256:' + hashlib.sha256(executable.read_bytes()).hexdigest():
        raise K.Refused('capture-input-changed')
    data = dict(provenance, type='observation', invocation=list(argv), pid=child.pid,
                executable_digest=executable_digest,
                exit_code=child.returncode, stdout_digest='sha256:' + hashlib.sha256(out).hexdigest(),
                stderr_digest='sha256:' + hashlib.sha256(err).hexdigest(),
                stdout_length=len(out), stderr_length=len(err))
    record(store, conn, identity, 'captured_evidence', data, journal_signer)
    return data, out, err


def _payload(state, request, channel, now):
    entry = state['entities'].get(request.get('source_id'))
    if not entry or entry['kind'] not in ('captured_evidence', 'agent_assertion', 'edge_source'):
        raise K.Refused('missing-attribution')
    payload = request.get('payload')
    if not isinstance(payload, dict):
        raise K.Refused('missing-attribution')
    stored = entry['data']
    if payload.get('type') != stored.get('type'):
        raise K.Refused('assertion-is-not-observation')
    if payload != stored:
        raise K.Refused('provenance-mismatch')
    for field in ('contract_digest', 'actor', 'actor_kind', 'source_digest', 'presentation_digest'):
        if not isinstance(payload.get(field), str) or not payload[field]:
            raise K.Refused('missing-attribution')
    if channel == 'evidence':
        if entry['kind'] == 'agent_assertion' and payload['type'] != 'assertion':
            raise K.Refused('assertion-is-not-observation')
        if entry['kind'] == 'captured_evidence' and payload['type'] != 'observation':
            raise K.Refused('assertion-is-not-observation')
        if entry['kind'] == 'edge_source':
            raise K.Refused('channel-mismatch')
        return payload
    if entry['kind'] != 'edge_source' or payload.get('type') != 'assertion':
        raise K.Refused('forbidden-arbitrary-signing')
    if payload.get('channel') != request.get('channel'):
        raise K.Refused('channel-mismatch')
    if payload.get('actor') != payload.get('principal') or payload.get('actor_kind') != 'person':
        raise K.Refused('provenance-mismatch')
    for field in ('authority_scope', 'presentation_id'):
        if not isinstance(payload.get(field), str) or not payload[field]:
            raise K.Refused('missing-attribution')
    if payload.get('assertion_kind') not in AC.ASSERTION_KINDS:
        raise K.Refused('unknown-assertion-kind')
    # Canonical source identity is independently required even when the accepted
    # source record exists. A text-only record never becomes platform evidence.
    attribution = payload.get('attribution', {})
    fields = AC.CHANNELS[payload['channel']]['attribution']
    if any(not attribution.get(field) for field in fields):
        raise K.Refused('missing-attribution')
    if any(field.endswith('_verified') and attribution.get(field) is not True for field in fields):
        raise K.Refused('missing-attribution')
    if payload['channel'] == 'signed_cli':
        source = payload.get('personal_command', {})
        key = AC.active_key(state['keyring'], payload['principal'], now)
        if not key or not source.get('signature'):
            raise K.Refused('missing-attribution')
        command, envelope = source.get('command', {}), source.get('envelope', {})
        if envelope.get('principal') != payload['principal'] or envelope.get('command_digest') != AC.canonical_command_digest(command):
            raise K.Refused('provenance-mismatch')
        parameters = command.get('parameters', {})
        if any(field not in parameters or field not in payload or parameters[field] != payload[field]
               for field in AC.DECISION_ASSERTION_FIELDS):
            raise K.Refused('provenance-mismatch')
        # Coordinates come from the authority-captured source, not new admission.
        # Recheck its envelope against current membership/delegation and time via
        # the contract. Reading evidence neither executes nor consumes its nonce.
        authority = dict(envelope, membership_version=state['membership_version'],
                         delegation_version=state['delegation_version'])
        problems = AC.envelope_problems(envelope, command, authority, now, set(),
                                        state['keyring'], state['membership'], state['delegations'])
        if problems:
            raise K.Refused('missing-attribution')
        ok, _ = AC.ssh_keygen_verify(AC.canonical_envelope_bytes(envelope), source['signature'],
                                   AC.allowed_signers_line(payload['principal'], key['public_key']), payload['principal'])
        if not ok:
            raise K.Refused('missing-attribution')
    if payload.get('edge_key_id') != request['edge_key_id']:
        raise K.Refused('delegation-refused')
    envelope = {'principal': payload.get('principal'), 'delegation_id': request.get('delegation_id'),
                'delegation_version': request.get('delegation_version')}
    requirement = {'scope': payload.get('authority_scope'), 'boundary': 'decision_settlement',
                   'subject_digest': payload['source_digest']}
    problems = CM.delegated_use_problems(state, envelope, payload, requirement, now)
    if problems:
        raise K.Refused('stale-delegation' if any(p.startswith('stale_delegation') for p in problems) else 'delegation-refused')
    return payload


def issue(config, request, challenge, identity, authentication):
    """Authenticate, validate and sign under the same lock as lifecycle transitions.

    The resulting receipt contains only public provenance and a signature. Diagnostics
    deliberately omit request text and exception detail, including private file paths.
    """
    conn = S.open_store(config['store'])
    key = None
    diagnostic = {'key_id': None, 'assertion_kind': None, 'principal': None, 'delegation_revision': None}
    try:
        conn.execute('BEGIN IMMEDIATE')
        now = time.time()
        state = CM.authority_state(S, conn)
        channel = authenticate(state, challenge, request, identity, authentication, now)
        diagnostic['delegation_revision'] = state['delegation_version']
        source = state['entities'].get(request.get('source_id'), {}).get('data', {})
        diagnostic.update(principal=source.get('principal', source.get('actor')),
                          assertion_kind=source.get('assertion_kind', source.get('type')))
        if any(f in request for f in ('key_path', 'private_key', 'path')):
            raise K.Refused('key-path')
        if request.get('operation') != 'sign_receipt':
            raise K.Refused('forbidden-arbitrary-signing')
        key = K.select(state, config['allowed_signers'], channel, now)
        diagnostic['key_id'] = key['key_id']
        if request.get('channel') != channel or request.get('edge_key_id') != key['key_id']:
            raise K.Refused('channel-mismatch')
        payload = _payload(state, request, channel, now)
        key_path = (Path(config['key_directory']) / key['key_id']).resolve()
        if key_path.is_relative_to(Path(config['repository']).resolve()):
            raise K.Refused('key-custody')
        envelope = {'schema': SCHEMA, 'channel': channel, 'key_id': key['key_id'],
                    'key_effective_at': key['effective_at'], 'key_revision': key['revision'], 'signed_at': now,
                    'source_id': request['source_id'], 'source_digest': digest(payload), 'payload': payload,
                    'delegation_id': request.get('delegation_id'), 'delegation_version': state['delegation_version']}
        signature = sign_bytes(key_path, canonical(envelope), K.NAMESPACE)
        return {'accepted': True, 'envelope': envelope, 'signature': signature,
                'diagnostic': {'key_id': key['key_id'], 'principal': payload.get('principal', payload['actor']),
                               'assertion_kind': payload.get('assertion_kind', payload['type']),
                               'delegation_revision': state['delegation_version'], 'refusal': None},
                'metrics': {'retained_historical_keys': sum(not K.active(k, now) for k in K.entries(state).values())}}
    except K.Refused as error:
        return {'accepted': False, 'refusal': error.code,
                'diagnostic': dict(diagnostic, refusal=error.code),
                'metrics': {error.code: 1}}
    finally:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        conn.close()


def call(config_path, request, identity, connection_key):
    """Client adapter: a new joined child per call, over anonymous pipes only."""
    process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(config_path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Bound the first read as well as completion, without a listener or daemon.
        import select
        if not select.select([process.stdout], [], [], 10)[0]:
            raise K.Refused('signing-unavailable')
        challenge = json.loads(process.stdout.readline())['challenge']
        message = canonical({'challenge': challenge, 'request_digest': digest(request)})
        authentication = sign_bytes(connection_key, message, AUTH_NAMESPACE) if connection_key else ''
        out, err = process.communicate(json.dumps({'request': request, 'identity': identity,
                                                  'authentication': authentication}) + '\n', timeout=15)
        if process.returncode:
            raise K.Refused('signing-unavailable')
        result = json.loads(out)
        result['signer_pid'] = process.pid
        return result
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def main():
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        challenge = secrets.token_hex(32)
        print(json.dumps({'challenge': challenge}), flush=True)
        import select
        if not select.select([sys.stdin], [], [], 10)[0]:
            raise K.Refused('unauthenticated-channel')
        packet = json.loads(sys.stdin.buffer.readline(1024 * 1024))
        result = issue(config, packet['request'], challenge, packet.get('identity'), packet.get('authentication', ''))
    except (K.Refused, ValueError, KeyError, OSError, TypeError, subprocess.TimeoutExpired):
        result = {'accepted': False, 'refusal': 'signing-unavailable'}
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
