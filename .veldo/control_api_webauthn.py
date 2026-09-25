#!/usr/bin/env python3
"""Passkey (WebAuthn Level 2) ceremony checks with the standard library and OpenSSL (VELDO-0130).

WHAT THIS MODULE IS. The verifier the authenticated API and the api_credential enrollment command
share. A credential is its id, its public key as DER SubjectPublicKeyInfo, its COSE algorithm (ES256,
-7, or Ed25519, -8; nothing else is accepted) and a random 16-byte user handle. The public key comes from
the browser's getPublicKey() and getPublicKeyAlgorithm() at registration, so no CBOR is parsed; the
possession proof (`possession_problems`) binds that key.

AN ASSERTION (`assertion_problems`) is accepted only when every check holds, each refusing by name:
clientDataJSON parses to an object whose type is "webauthn.get", whose challenge is the expected one,
whose origin equals the configured origin exactly and whose crossOrigin is absent or false; the first
32 bytes of authenticatorData are SHA-256 of the configured relying-party id and its flags byte has
user present (bit 0) and user verified (bit 2) set; the userHandle is the credential's; and the
signature verifies over authenticatorData followed by SHA-256 of clientDataJSON. The signature counter
is not read, because synced passkeys report zero.

THE SIGNATURE is checked by the openssl command line as a subprocess (`openssl_verifies`): "openssl
dgst -sha256 -verify" with the DER key for ES256 (a WebAuthn ES256 signature is already DER ECDSA) and
"openssl pkeyutl -verify -pubin -rawin" for Ed25519. The argument vector is fixed, there is no shell,
the key and signature go in files in a fresh 0700 directory under the caller's state directory, the
environment is empty, the timeout is 10 seconds, and only the exit status is read. ES256 reads the
signed bytes on standard input. OpenSSL 3.0's pkeyutl cannot size a pipe for a one-shot Ed25519
verification ("unable to determine file size for oneshot operation", measured on this host with
OpenSSL 3.0.13), so for Ed25519 the signed bytes are one more file in the same private directory.

A REGISTRATION (`registration_problems`) checks clientDataJSON's type "webauthn.create", its challenge
and its origin, and the offered key's shape. The possession proof is a sign-in ceremony made at once
with the new credential whose challenge is SHA-256 of the canonical registration binding
(`binding_challenge`), verified as any assertion.

WHAT IT IS NOT. Not attestation or signature-counter clone detection (Release 2), not a session, not
key storage. Standard library and the openssl executable only (OpenSSL 3.0 or later, Apache-2.0).
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import tempfile

ES256, ED25519 = -7, -8
ALGORITHMS = (ES256, ED25519)
BINDING_SCHEMA = 'veldo.api_registration_binding/v1'
BINDING_FIELDS = ('schema', 'rp_id', 'origin', 'credential_id', 'public_key', 'algorithm', 'label', 'user_handle',
                  'nonce', 'expires_at')
USER_PRESENT, USER_VERIFIED = 0x01, 0x04
CREDENTIAL_ID_BYTES = 1023  # the WebAuthn Level 2 maximum
USER_HANDLE_BYTES = 16
TIMEOUT = 10
# The DER SubjectPublicKeyInfo prefixes of the two accepted key types, byte for byte: an uncompressed
# P-256 point (RFC 5480) and a raw Ed25519 key (RFC 8410). A key with any other prefix or length is refused.
SPKI_PREFIX = {ES256: bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d03010703420004'),
               ED25519: bytes.fromhex('302a300506032b6570032100')}
SPKI_LENGTH = {ES256: 91, ED25519: 44}


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def unb64url(text):
    """Bytes of unpadded base64url text, or None when it is not that."""
    if not isinstance(text, str) or not text or len(text) > 8192 or '=' in text:
        return None
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in text):
        return None
    try:
        return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))
    except ValueError:
        return None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def new_user_handle():
    return b64url(secrets.token_bytes(USER_HANDLE_BYTES))


def fingerprint(public_key):
    """What the enrollment tool shows the steward: SHA-256 of the DER key, grouped for reading."""
    der = unb64url(public_key) or b''
    text = hashlib.sha256(der).hexdigest()[:32]
    return 'SHA256:' + ':'.join(text[i:i + 4] for i in range(0, len(text), 4))


def key_problem(public_key, algorithm):
    """Why a (base64url DER SubjectPublicKeyInfo, COSE algorithm) is not an accepted key, or None."""
    if type(algorithm) is not int or algorithm not in ALGORITHMS:
        return 'unsupported_algorithm'
    der = unb64url(public_key)
    if der is None or len(der) != SPKI_LENGTH[algorithm] or not der.startswith(SPKI_PREFIX[algorithm]):
        return 'invalid_key'
    return None


def credential_id_problem(credential_id):
    raw = unb64url(credential_id)
    return None if raw is not None and 1 <= len(raw) <= CREDENTIAL_ID_BYTES else 'invalid_credential_id'


def binding_challenge(binding):
    """The possession ceremony's challenge: SHA-256 of the canonical registration binding."""
    return b64url(hashlib.sha256(canonical(binding)).digest())


def _client_data(client_data_json):
    raw = unb64url(client_data_json)
    if raw is None:
        return None, None
    try:
        data = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return raw, None
    return raw, data if isinstance(data, dict) else None


def _client_data_problem(data, kind, challenge, origin):
    if data is None:
        return 'invalid_client_data'
    if data.get('type') != kind:
        return 'wrong_ceremony'
    if not isinstance(challenge, str) or not challenge or data.get('challenge') != challenge:
        return 'wrong_challenge'
    if data.get('origin') != origin:
        return 'wrong_origin'
    if 'crossOrigin' in data and data['crossOrigin'] is not False:
        return 'cross_origin'
    return None


def registration_problems(client_data_json, challenge, origin, credential_id, public_key, algorithm):
    """Why a registration ceremony's result is refused, by name; [] when it is accepted."""
    _raw, data = _client_data(client_data_json)
    problem = _client_data_problem(data, 'webauthn.create', challenge, origin)
    return [p for p in (problem, credential_id_problem(credential_id), key_problem(public_key, algorithm)) if p]


def assertion_problems(credential, assertion, challenge, origin, rp_id, state_dir):
    """Why a sign-in assertion is refused, by name; [] when it is accepted. `credential` has
    credential_id, public_key (base64url DER), algorithm and user_handle; `assertion` has
    credential_id, client_data_json, authenticator_data, signature and user_handle, each base64url."""
    if not isinstance(credential, dict) or not isinstance(assertion, dict):
        return ['invalid_assertion']
    if assertion.get('credential_id') != credential.get('credential_id'):
        return ['wrong_credential']
    raw, data = _client_data(assertion.get('client_data_json'))
    problem = _client_data_problem(data, 'webauthn.get', challenge, origin)
    if problem:
        return [problem]
    auth = unb64url(assertion.get('authenticator_data'))
    if auth is None or len(auth) < 37:
        return ['invalid_authenticator_data']
    if auth[:32] != hashlib.sha256(rp_id.encode('ascii')).digest():
        return ['wrong_relying_party']
    flags = struct.unpack('>B', auth[32:33])[0]
    if not flags & USER_PRESENT:
        return ['user_not_present']
    if not flags & USER_VERIFIED:
        return ['user_not_verified']
    if assertion.get('user_handle') != credential.get('user_handle'):
        return ['wrong_user_handle']
    signature = unb64url(assertion.get('signature'))
    if signature is None or key_problem(credential.get('public_key'), credential.get('algorithm')):
        return ['signature_invalid']
    message = auth + hashlib.sha256(raw).digest()
    if not openssl_verifies(credential['algorithm'], unb64url(credential['public_key']), message, signature, state_dir):
        return ['signature_invalid']
    return []


def possession_problems(binding, proof, origin, rp_id, state_dir):
    """Why a registration's possession proof is refused: the binding is the canonical registration
    binding, and the proof is an assertion by that credential over a challenge that is its digest."""
    if not isinstance(binding, dict) or set(binding) != set(BINDING_FIELDS) or binding.get('schema') != BINDING_SCHEMA:
        return ['invalid_binding']
    if binding['origin'] != origin or binding['rp_id'] != rp_id:
        return ['wrong_origin']
    credential = {k: binding[k] for k in ('credential_id', 'public_key', 'algorithm', 'user_handle')}
    problems = [p for p in (credential_id_problem(binding['credential_id']),
                            key_problem(binding['public_key'], binding['algorithm'])) if p]
    if problems:
        return problems
    assertion = dict(proof, credential_id=binding['credential_id']) if isinstance(proof, dict) else None
    return assertion_problems(credential, assertion, binding_challenge(binding), origin, rp_id, state_dir)


def openssl_path():
    """The openssl executable on this process's PATH, or None."""
    return shutil.which('openssl')


def openssl_verifies(algorithm, spki_der, message, signature, state_dir):
    """Whether openssl verifies `signature` over `message` with the DER SubjectPublicKeyInfo key.
    Only the exit status is read; any failure to run is a signature that does not verify."""
    program = openssl_path()
    if program is None or not isinstance(spki_der, bytes) or algorithm not in ALGORITHMS:
        return False
    base = Path(state_dir) / 'verify'
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(base, 0o700)
    with tempfile.TemporaryDirectory(prefix='v-', dir=base) as directory:
        os.chmod(directory, 0o700)
        key, sig, data = Path(directory) / 'key.der', Path(directory) / 'signature', Path(directory) / 'message'
        for path, content in ((key, spki_der), (sig, signature)):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as handle:
                handle.write(content)
        if algorithm == ES256:
            argv = [program, 'dgst', '-sha256', '-verify', str(key), '-keyform', 'DER', '-signature', str(sig)]
            feed = message
        else:
            fd = os.open(data, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as handle:
                handle.write(message)
            argv = [program, 'pkeyutl', '-verify', '-pubin', '-inkey', str(key), '-keyform', 'DER', '-rawin',
                    '-in', str(data), '-sigfile', str(sig)]
            feed = b''
        try:
            done = subprocess.run(argv, input=feed, capture_output=True, timeout=TIMEOUT, env={}, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0
