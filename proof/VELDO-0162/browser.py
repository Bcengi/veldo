"""Generated passkey stand-in, copied from the VELDO-0130 ceremony fixture."""
import base64
import hashlib
import json
import os
import subprocess

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

class Browser:
    """A local passkey stand-in: an openssl key, and ceremony results assembled as WebAuthn lays them out.
    authenticatorData is SHA-256(rp id), one flags byte and a zero signature counter; clientDataJSON is
    the JSON a browser serializes; the signature is openssl's over authenticatorData || SHA-256(clientDataJSON)."""

    def __init__(self, directory, name, algorithm):
        directory.mkdir(exist_ok=True)
        self.key, self.algorithm, self.directory = directory / (name + '.pem'), algorithm, directory
        spec = ['-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256'] if algorithm == -7 else ['-algorithm', 'ED25519']
        subprocess.run(['openssl', 'genpkey'] + spec + ['-out', str(self.key)], check=True, capture_output=True, timeout=10)
        self.der = subprocess.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'], check=True,
                                capture_output=True, timeout=10).stdout
        self.credential_id = b64url(os.urandom(32))
        self.user_handle = None

    def public_key(self):
        return b64url(self.der)

    def sign(self, message):
        if self.algorithm == -7:
            return subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)], input=message, check=True,
                                capture_output=True, timeout=10).stdout
        data = self.directory / (self.key.stem + '.message')
        data.write_bytes(message)
        return subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', str(self.key), '-rawin', '-in', str(data)],
                            check=True, capture_output=True, timeout=10).stdout

    @staticmethod
    def client_data(kind, challenge, origin, cross_origin=False):
        value = {'type': kind, 'challenge': challenge, 'origin': origin}
        if cross_origin is not None:
            value['crossOrigin'] = cross_origin
        return json.dumps(value, separators=(',', ':')).encode()

    def create(self, challenge, origin):
        return {'credential_id': self.credential_id, 'public_key': self.public_key(), 'algorithm': self.algorithm,
                'client_data_json': b64url(self.client_data('webauthn.create', challenge, origin))}

    def get(self, challenge, origin, rp_id, flags=0x05, kind='webauthn.get', cross_origin=False, user_handle=None,
            signer=None, after=None):
        """One assertion; `signer` signs instead of this key, `after` changes it once it is signed."""
        client = self.client_data(kind, challenge, origin, cross_origin)
        auth = hashlib.sha256(rp_id.encode()).digest() + bytes([flags]) + b'\x00\x00\x00\x00'
        signature = (signer or self).sign(auth + hashlib.sha256(client).digest())
        value = {'credential_id': self.credential_id, 'client_data_json': b64url(client),
                 'authenticator_data': b64url(auth), 'signature': b64url(signature),
                 'user_handle': user_handle if user_handle is not None else self.user_handle}
        if after is not None:
            after(value)
        return value
