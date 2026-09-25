"""VELDO-0130 phase 1: the authenticated API's passkey sign-in, sessions, edge and message and decision writes.

Run: python3 scripts/selftest.py --suite 71_veldo_0130_api

Every passkey assertion is made by a local browser stand-in: a real ES256 or Ed25519 key generated with
openssl in the fixture, a clientDataJSON and authenticatorData assembled here byte by byte as the
WebAuthn Level 2 specification lays them out, and a signature made by the openssl command line. The
verifier is also judged against an independent implementation: four W3C WebAuthn Level 3 test vectors
(section 16, W3C Software and Document License, copied below), whose keys, client data, authenticator
data and signatures were made by the W3C's generator, not by anything here. Every administrative command,
journal record, edge assertion and domain request is a real OpenSSH signature on a real SQLite store; the
API edge's signatures are made by the actual protected signer process from the protected key directory,
and every write is executed by the actual VELDO-0126 intake and VELDO-0068 settlement. Telegram answers
run against a loopback Bot API server (real HTTP in the platform's documented shapes, no network, no real
token). The API's request handler is driven directly for store-touching requests (the store connection
belongs to this thread) and over real loopback HTTP for the transport row. Mutation workers replace the
production copies named in PRODUCTION below, never assertions or fixtures. Where the API modules are
absent (the pre-change tree, for the red record) the API is what that tree has, nothing: every route
answers 404, no credential can be enrolled and no assertion verified, so each row fails by its own
assertions rather than by an exception. No private key byte, cookie, token or signature is printed.
"""
import base64 as _v130_b64
import copy as _v130_copy
import hashlib as _v130_hashlib
import http.client as _v130_client
import http.server as _v130_http
import importlib.util as _v130_import
import json as _v130_json
import os as _v130_os
from pathlib import Path as _v130_Path
import shutil as _v130_shutil
import stat as _v130_stat
import subprocess as _v130_sp
import tempfile as _v130_temp
import threading as _v130_threading
import time as _v130_time

_V130_ROWS = ('install/assets', 'webauthn/stand-in-browser', 'webauthn/independent-vectors',
              'enrollment/pending-grants-nothing', 'enrollment/steward-signed', 'session/cookie-and-expiry',
              'session/forgery-refused', 'session/revocation-ends', 'routes/every-family', 'routes/body-actor-refused',
              'edge/signer-api-purpose', 'edge/authority-recheck', 'messages/common-intake',
              'decisions/exact-settlement', 'decisions/one-ruling', 'transport/loopback-only')
_V130_CHOICES = {'accept': 'approve', 'return_for_elaboration': 'return_for_elaboration', 'reject': 'reject'}
_V130_HOST = 'veldo-host.example.ts.net'
_V130_ORIGIN = 'https://' + _V130_HOST

# W3C Web Authentication Level 3, section 16 "Test Vectors" (https://www.w3.org/TR/webauthn-3/, fetched
# 2026-09-24), used under the W3C Software and Document License. Hex as published; each public key is the
# COSE x (and y) coordinate read from the registration's attestationObject. Relying party example.org,
# origin https://example.org. Authenticator data flags: 16.6 0x0d (user verified), 16.2 0x19 and 16.11
# 0x01 (user present, not verified); 16.4 carries "crossOrigin": true.
_V130_W3C = {
    '16.6': {
        'alg': -7,
        'x': ('3b8176b7504489cc593046d7988abb7905a742de6ac2cdc748a873c663e90cb1'),
        'y': ('1436d5edc9a75f23999eef9d5950a5c2455514ee1014084720f841a06b828a11'),
        'credential_id': ('3a761a4e1674ad6c4305869435c0eee9c286172c229bb91b48b4ada140c0863417031305cce5b4a27a88d7fe728a5f5a'
            '627de771b4b40e77f187980c124f9fe832d7136010436a056cce716680587d23187cf1fc2c62ae86fc3e508ee9617ffc'
            '74fbc10488ec16ec5e9096328669a898709b655e549738c666c1ae6281dc3b5f733c251d3eefb76ee70a3805ca91bcc1'
            '8e49c8dc7f63ebcb486ba8c3d6ab52b88ff72c6a5bb47c32f3ee8683a3ddc8abf60870448ec8a21b5bdcb183c7dead87'
            '0255575a6df96eb1b6a2a1019780cba9e4887b17ff1164bbbcc10eb0d86ed75984cd3fa3419103024507dfd9ce8f92c5'
            '6af7914cb0bb50b87ba82a312bb7dcd93028dbdcd6adb266979667158335171e3682d37755701edbf9d872846a291d49'
            'e57ef09da1ec637f5052ed2aa7407f7e61827468e94b461844f4c67be5fa9c6055a566f8fdfc29d4bf78a9ff275f552c'
            'c68ba543fa3962eea36fd1ea8453764577d021d0a181efc1f6100ab2e4110039e21ee16970bda7432b6134492155afc1'
            '26295b3a2eccd12c66a68e340969e995e3e8c9c476e395cfc21203414110779474f1c9797406637dbe414f132519d3bf'
            '0ce4f01734ef0e1a12c3ad604ff15d766b1624db6a5a7ccbff7bc35c9908df94aba277e0af48f04ff3d16381c47e5a37'
            'ed3988a67a3b1ecaa926336b33391fff04128f869991c9fabd905b6fe3ceef5f8b630ec1c5d2636d5b1961ad5ca50041'
            '70f6f5e482792aad989b0287fe91e5c479403397152f1fa56aa79b156eb47e6c8ea3eb175c34cfb38ad8e772874639b1'
            '023d4d01395c94e55831671cc022aa6fa1e02a02c2e4abc776f6960e51f83b71a8c0f207b6a347573977812c9aa5480b'
            '0011aa739bd4b76c18c000cc4757cceccb920f007c40c00e37e5ab21476cd9f6054a8fffb55a108f5c706e2cea2049d8'
            '1fd321ff47d2a5761b0800955ab1d4f4889f55a84e2601c684f17a4ade7453ea49591d0b59c8d9a765052f62219cf6ef'
            '4a5dd9539f0617d6ebbebce7c000455475d18449e25c49ef9a1e3efe18c09082ebe2058d7c347defaa92f0664553b805'
            'c7d76bbfce5f330aca220ac90a789380fc479ea0d8793205813cca590a912f699ad52f991a1bc0a503c3ec4b2a696719'
            'e3c26591a87127f7305cc7e72f4c8e39355ebb06a5b1042990f38710ee7aa612ee4374bb82e878585a70a96c2a6b47f1'
            '01a4ff154be4fd76a3167577a5cc54d9167c154c69ac35485e44cc898b719e1be3cc9c0fb5624b8f8a0dae10947a41bf'
            '848b6c1bb33d1006ec077d7e286e3f2a7b4843716390119449fe2721e81a5ed2333d331c7120765da58fadae73c19d9a'
            '8c4509cf8ac1e9d98b799a5274509069739b5823f3fb496663820033426988eefca53e580e0f9e0dfe0992fc2e53a97e'
            '053639f98577058f995bdbd41cefdb'),
        'challenge': ('ef1deba56dce48f674a447ccf63b9599258ce87648e5c396f2ef0ca1da460e3b'),
        'authenticator_data': ('bfabc37432958b063360d3ad6461c9c4735ae7f8edd46592a5e0f01452b2e4b50d00000000'),
        'client_data_json': ('7b2274797065223a22776562617574686e2e676574222c226368616c6c656e6765223a22377833727057334f53505a30'
            '7045664d396a75566d53574d36485a4935634f573875384d6f647047446a73222c226f726967696e223a226874747073'
            '3a2f2f6578616d706c652e6f7267222c2263726f73734f726967696e223a66616c73657d'),
        'signature': ('304502203ecef83fb12a0cae7841055f9f87103a99fd14b424194bbf06c4623d3ee6e3fd022100d2ace346db262b1374'
            'a6b70faa51f518a42ddca13a4125ce6f5052a75bac9fb6'),
    },
    '16.2': {
        'alg': -7,
        'x': ('afefa16f97ca9b2d23eb86ccb64098d20db90856062eb249c33a9b672f26df61'),
        'y': ('930a56b87a2fca66334b03458abf879717c12cc68ed73290af2e2664796b9220'),
        'credential_id': ('f91f391db4c9b2fde0ea70189cba3fb63f579ba6122b33ad94ff3ec330084be4'),
        'challenge': ('39c0e7521417ba54d43e8dc95174f423dee9bf3cd804ff6d65c857c9abf4d408'),
        'authenticator_data': ('bfabc37432958b063360d3ad6461c9c4735ae7f8edd46592a5e0f01452b2e4b51900000000'),
        'client_data_json': ('7b2274797065223a22776562617574686e2e676574222c226368616c6c656e6765223a224f63446e55685158756c5455'
            '506f334a5558543049393770767a7a59425039745a63685879617630314167222c226f726967696e223a226874747073'
            '3a2f2f6578616d706c652e6f7267222c2263726f73734f726967696e223a66616c73657d'),
        'signature': ('3046022100f50a4e2e4409249c4a853ba361282f09841df4dd4547a13a87780218deffcd380221008480ac0f0b935381'
            '74f575bf11a1dd5d78c6e486013f937295ea13653e331e87'),
    },
    '16.4': {
        'alg': -7,
        'x': ('22200a473f90b11078851550d03b4e44a2279f8c4eca27b3153dedfe03e4e97d'),
        'y': ('cbd0be95e746ad6f5a8191be11756e4c0420e72f65b466d39bc56b8b123a9c6e'),
        'credential_id': ('6e1050c0d2ca2f07c755cb2c66a74c64fa43065c18f938354d9915db2bd5ce57'),
        'challenge': ('876aa517ba83fdee65fcffdbca4c84eeae5d54f8041a1fc85c991e5bbb273137'),
        'authenticator_data': ('bfabc37432958b063360d3ad6461c9c4735ae7f8edd46592a5e0f01452b2e4b50500000000'),
        'client_data_json': ('7b2274797065223a22776562617574686e2e676574222c226368616c6c656e6765223a226832716c463771445f65356c'
            '5f505f62796b7945377135645650674547685f49584a6b655737736e4d5463222c226f726967696e223a226874747073'
            '3a2f2f6578616d706c652e6f7267222c2263726f73734f726967696e223a747275652c22657874726144617461223a22'
            '636c69656e74446174614a534f4e206d617920626520657874656e6465642077697468206164646974696f6e616c2066'
            '69656c647320696e20746865206675747572652c207375636820617320746869733a2039327063545644304162792d71'
            '3464746d6a36656667227d'),
        'signature': ('3046022100eb12fcf23b12764c0f122e22371fab92e283879fd798f38ee1841c951b6e40e7022100c76237ff9db77b3c'
            '56f30837cda6a09acfa2e915544e609c0733b1184036d1cf'),
    },
    '16.11': {
        'alg': -8,
        'x': ('44e06ddd331c36a8dc667bab52bcae63486c916aa5e339e6acebaa84934bf832'),
        'credential_id': ('ce9f840ed96599580cd140fbc7bb3230633f50f61041aff73308ae71caa8a2bd'),
        'challenge': ('895957e01c633a698348a2d8a31a54b7db27e8c1c43b2080d79ae2190267bfd2'),
        'authenticator_data': ('bfabc37432958b063360d3ad6461c9c4735ae7f8edd46592a5e0f01452b2e4b50100000000'),
        'client_data_json': ('7b2274797065223a22776562617574686e2e676574222c226368616c6c656e6765223a2269566c583442786a4f6d6d44'
            '534b4c596f7870557439736e364d48454f7943413135726947514a6e763949222c226f726967696e223a226874747073'
            '3a2f2f6578616d706c652e6f7267222c2263726f73734f726967696e223a66616c73657d'),
        'signature': ('f5c59c7e46c34f6f8cc197101ddf9934fa2595f68eb1913a637e8419eb9ba4cfdfc48f85393bc0d40b011f0d6fecb097'
            'd6607525713223a0dc0d453993dae00b'),
    },
}


def _v130_load(name, path):
    spec = _v130_import.spec_from_file_location(name, path)
    module = _v130_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v130_b64url(data):
    return _v130_b64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _v130_message(st, bot, sender, chat, text, reply_to=None):
    """One message as the platform keeps and delivers it (the VELDO-0068 suite's loopback shape)."""
    with st['lock']:
        bot['next'] += 1
        st['tick'] += 1
        message = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
                   'text': text}
        if reply_to is not None:
            held = bot['messages'][(chat['id'], reply_to)]
            message['reply_to_message'] = _v130_copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
        bot['messages'][(chat['id'], message['message_id'])] = message
        return message


class _V130BotApi(_v130_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes, per bot name."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        body = _v130_json.loads(raw) if raw else {}
        _, _, rest = self.path.partition('/bot')
        name, _, method = rest.partition('/')
        bot = st['bots'].get(name)
        if bot is None:
            return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
        if method == 'getMe':
            return self._answer(200, {'ok': True, 'result': dict(bot['user'], can_join_groups=True)})
        if method == 'getUpdates':
            offset = body.get('offset') or 0
            if offset:
                bot['updates'] = [u for u in bot['updates'] if u['update_id'] >= offset]
            return self._answer(200, {'ok': True, 'result': bot['updates'][:body.get('limit') or 100]})
        if method == 'sendMessage':
            chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
            reply = (body.get('reply_parameters') or {}).get('message_id')
            if reply is not None and (chat['id'], reply) not in bot['messages']:
                reply = None
            return self._answer(200, {'ok': True, 'result': _v130_message(st, bot, bot['user'], chat, body['text'], reply)})
        return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

    def _answer(self, code, value):
        payload = _v130_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class _V130Browser:
    """A local passkey stand-in: an openssl key, and ceremony results assembled as WebAuthn lays them out.
    authenticatorData is SHA-256(rp id), one flags byte and a zero signature counter; clientDataJSON is
    the JSON a browser serializes; the signature is openssl's over authenticatorData || SHA-256(clientDataJSON)."""

    def __init__(self, directory, name, algorithm):
        directory.mkdir(exist_ok=True)
        self.key, self.algorithm, self.directory = directory / (name + '.pem'), algorithm, directory
        spec = ['-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256'] if algorithm == -7 else ['-algorithm', 'ED25519']
        _v130_sp.run(['openssl', 'genpkey'] + spec + ['-out', str(self.key)], check=True, capture_output=True, timeout=10)
        self.der = _v130_sp.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'], check=True,
                                capture_output=True, timeout=10).stdout
        self.credential_id = _v130_b64url(_v130_os.urandom(32))
        self.user_handle = None

    def public_key(self):
        return _v130_b64url(self.der)

    def sign(self, message):
        if self.algorithm == -7:
            return _v130_sp.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)], input=message, check=True,
                                capture_output=True, timeout=10).stdout
        data = self.directory / (self.key.stem + '.message')
        data.write_bytes(message)
        return _v130_sp.run(['openssl', 'pkeyutl', '-sign', '-inkey', str(self.key), '-rawin', '-in', str(data)],
                            check=True, capture_output=True, timeout=10).stdout

    @staticmethod
    def client_data(kind, challenge, origin, cross_origin=False):
        value = {'type': kind, 'challenge': challenge, 'origin': origin}
        if cross_origin is not None:
            value['crossOrigin'] = cross_origin
        return _v130_json.dumps(value, separators=(',', ':')).encode()

    def create(self, challenge, origin):
        return {'credential_id': self.credential_id, 'public_key': self.public_key(), 'algorithm': self.algorithm,
                'client_data_json': _v130_b64url(self.client_data('webauthn.create', challenge, origin))}

    def get(self, challenge, origin, rp_id, flags=0x05, kind='webauthn.get', cross_origin=False, user_handle=None,
            signer=None, after=None):
        """One assertion; `signer` signs instead of this key, `after` changes it once it is signed."""
        client = self.client_data(kind, challenge, origin, cross_origin)
        auth = _v130_hashlib.sha256(rp_id.encode()).digest() + bytes([flags]) + b'\x00\x00\x00\x00'
        signature = (signer or self).sign(auth + _v130_hashlib.sha256(client).digest())
        value = {'credential_id': self.credential_id, 'client_data_json': _v130_b64url(client),
                 'authenticator_data': _v130_b64url(auth), 'signature': _v130_b64url(signature),
                 'user_handle': user_handle if user_handle is not None else self.user_handle}
        if after is not None:
            after(value)
        return value


class _V130Absent:
    """What a tree without the API has in its place: no route answers, no verifier, no credential."""
    ROUTES = ()

    def __init__(self):
        self.observations = []
        self.sessions = None

    def handle(self, method, path, headers, raw):
        return 404, [], {'refusal': 'missing_evidence:route', 'error': 'missing_evidence'}

    def route_problems(self):
        return ['no API module is installed']

    def follow(self, record):
        return 0

    def apply(self, packet):
        return {'ok': False, 'reason': 'missing_evidence:no_api_authority'}

    def admit(self, *args, **kwargs):
        return {'outcome': 'refused', 'refusal': 'no_credentials_module'}

    def __call__(self, *args, **kwargs):
        raise RuntimeError('no api signer')


def _v130_checks(base):
    rows = {name: [] for name in _V130_ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """Criterion sections: an exception is recorded as a failure of each named row and the run goes
        on, so every row reports even against code whose interface differs."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:200]), False)
            return True

    IA, WB, WV, EP, ES, SC, SF, SR, RF, RB, EG, EA, MS, DE, DO, TL = _V130_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_webauthn.py': ROOT / ".veldo" / "control_api_webauthn.py",
        'control_api_credentials.py': ROOT / ".veldo" / "control_api_credentials.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_api_signer.py': ROOT / ".veldo" / "control_api_signer.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_channel_enrollment.py': ROOT / ".veldo" / "control_channel_enrollment.py",
        'control_signer_answers.py': ROOT / ".veldo" / "control_signer_answers.py",
        'authority_contract.py': ROOT / ".veldo" / "authority_contract.py",
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
    }
    API_MODULES = ('control_api.py', 'control_api_assertion.py', 'control_api_authority.py', 'control_api_credentials.py',
                   'control_api_signer.py', 'control_api_webauthn.py')
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    organs = base / 'installed'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v130_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        target = organs / name
        if target.exists():
            target.unlink()
        if _v130_Path(source).is_file():
            _v130_shutil.copyfile(source, target)
    here = all((organs / m).is_file() for m in API_MODULES)

    with section(IA):
        scaffold = _v130_load('v130_scaffold', scaffold_path)
        for rel in ['.veldo/' + m for m in API_MODULES]:
            both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
            check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
            check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
            check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
            if both:
                scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
            check(IA, rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                  and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())
        for rel in ('.veldo/authority_contract.py', '.veldo/control_channel_enrollment.py',
                    '.veldo/control_signer_answers.py', '.veldo/init_scaffold.py'):
            check(IA, rel + ' engine copy identical', (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())

    claims = _v130_load('v130_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = _v130_load('v130_keys', organs / 'control_keys.py')
    I = _v130_load('v130_inbox', organs / 'control_assignment.py')
    P = _v130_load('v130_projection', organs / 'control_channel_projection.py')
    V = _v130_load('v130_presentation', organs / 'control_channel_presentation.py')
    EV = _v130_load('v130_attribution', organs / 'control_channel_attribution.py')
    E = _v130_load('v130_enrollment', organs / 'control_channel_enrollment.py')
    A = _v130_load('v130_answers', organs / 'control_signer_answers.py')
    IN = _v130_load('v130_intake', organs / 'control_intake.py')
    ST = _v130_load('v130_settlement', organs / 'control_request_settlement.py')
    SIG = _v130_load('v130_signer', organs / 'control_signer.py')
    contract = _v130_load('v130_contract', organs / 'entity_contract.py')
    W = _v130_load('v130_webauthn', organs / 'control_api_webauthn.py') if here else None
    CR = _v130_load('v130_credentials', organs / 'control_api_credentials.py') if here else None
    AS = _v130_load('v130_assertion', organs / 'control_api_assertion.py') if here else None
    AUTH = _v130_load('v130_authority', organs / 'control_api_authority.py') if here else None
    SG = _v130_load('v130_api_signer', organs / 'control_api_signer.py') if here else None
    API = _v130_load('v130_api', organs / 'control_api.py') if here else None

    keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
    for directory in (keys, protected, edge_dir):
        directory.mkdir()
    keyfile = {who: keys / who for who in ('authority', 'steward', 'steward2', 'owner', 'owner2', 'member', 'pm')}
    keyfile['edge'] = protected / 'edge-telegram'
    keyfile['api-edge'] = protected / 'edge-api'
    keyfile['edge-auth'] = edge_dir / 'edge-auth'
    keyfile['api-auth'] = edge_dir / 'api-auth'
    public = {}
    for who, path in keyfile.items():
        _v130_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v130-' + who, '-f', str(path)],
                     check=True, capture_output=True, timeout=10)
        public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
    private_api_edge = keyfile['api-edge'].read_bytes()

    def sign_as(who, message, namespace='veldo-command'):
        return _v130_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                            capture_output=True, check=True, timeout=10).stdout.decode()

    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return '%s-%d' % (prefix, serial[0])

    def verifies(principal, public_key, message, signature, namespace='veldo-command'):
        """An independent ssh-keygen verification, in a fresh directory of its own."""
        place = base / next_id('verify')
        place.mkdir()
        (place / 'allowed').write_text('%s namespaces="%s" %s\n' % (principal, namespace, public_key))
        (place / 'signature').write_text(signature if isinstance(signature, str) else '')
        done = _v130_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(place / 'allowed'), '-I', principal, '-n', namespace,
                             '-s', str(place / 'signature')], input=message, capture_output=True, timeout=10)
        return done.returncode == 0

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    ids = dict(domain_uuid='api-domain', repository_uuid='api-repository', store_uuid='api-store')
    DOMAIN, PROJECTS = 'api-intake', ('project-a', 'project-b')
    (base / 'authority').mkdir()
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    CM.attach(S)
    K.attach(S)
    repository = base / 'repository'
    repository.mkdir()
    projection = repository / '.veldo' / 'keys' / 'allowed_signers'
    config_path = base / 'authority' / 'signer.json'
    config_path.write_text(_v130_json.dumps({'store': str(db), 'repository': str(repository),
                                             'allowed_signers': str(projection), 'key_directory': str(protected),
                                             'authority_ids': ids}))

    def state():
        return CM.authority_state(S, conn)

    def envelope(command, principal, **over):
        now = state()
        found = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                     request_revision=1, nonce='nonce-' + command['command_id'], expires_at=_v130_time.time() + 600,
                     membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                     command_digest=AC.canonical_command_digest(command))
        found.update(over)
        return found

    def admin(principal, operation, params, enrollee=None):
        command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, principal)
        signature = sign_as(principal, AC.canonical_envelope_bytes(env))
        cosigned = sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal']))) if enrollee else None
        result = CM.admit(S, conn, env, command, signature, ids, _v130_time.time(), enrollee_signature=cosigned,
                          journal_signer=('authority', journal_sign))
        K.publish(S, conn, projection)
        return result

    def enroll_member(who, principal_type, roles, scope):
        admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                              'public_key': public[who], 'independence_group': who, 'scope': scope},
              enrollee=who)

    admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                          'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                          'independence_group': 'steward', 'scope': '*'})
    enroll_member('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority', 'technical_authority'],
                  ['project-a', 'project-b'])
    enroll_member('owner2', 'person', ['project_owner'], ['project-a'])
    enroll_member('member', 'person', [], ['project-z'])
    enroll_member('steward2', 'person', ['membership_steward'], ['project-b'])
    enroll_member('pm', 'service', [], ['project-a'])

    def fixture(eid, kind, data):
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

    chats = {'owner': 5590001, 'owner2': 5590002}
    for who, chat in chats.items():
        fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                     revoked_at=None))
    enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)

    def enroll_edge(params, possession):
        command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge', 'target': 'channel:' + params['channel'],
                   'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, 'steward')
        return enrollment.admit(env, command, sign_as('steward', AC.canonical_envelope_bytes(env)),
                                sign_as(possession, AC.canonical_envelope_bytes(env), 'veldo-edge-possession'))

    enroll_edge({'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                 'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['project-a']}, 'edge')
    # The API's own edge: the VELDO-0067 enrollment, channel "api", a service member with no roles.
    api_edge_enrolled = enroll_edge({'channel': 'api', 'edge_principal': 'api-edge', 'edge_key_id': 'edge-api',
                                     'public_key': public['api-edge'], 'connection_public_key': public['api-auth'],
                                     'scope': ['project-a', 'project-b']}, 'api-edge')
    now = _v130_time.time()
    for who in ('owner', 'owner2'):
        admin(who, 'grant_delegation', {'id': 'delegation-' + who, 'principal': who, 'channel': 'telegram_chat',
                                        'assertion_kinds': ['decision_answer', 'review_disposition'],
                                        'authority_scope': ['project-a'], 'request_version': 1, 'presentation_version': 1,
                                        'expires_at': now + 3600, 'edge_key_id': 'edge-telegram'})

    bots = {'tick': 0, 'bots': {}, 'chats': {}, 'lock': _v130_threading.Lock()}
    handler = type('V130Handler', (_V130BotApi,), {'state': bots})
    bot_server = _v130_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    _v130_threading.Thread(target=bot_server.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d' % bot_server.server_address[1]
    bots['bots']['bot130'] = {'user': {'id': 8000000130, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_api_bot'},
                              'next': 9000, 'update_next': 720000000, 'messages': {}, 'updates': []}
    bot = bots['bots']['bot130']
    people = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize()} for who, chat in chats.items()}
    for person in people.values():
        bots['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}

    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot130'), conn, 'authority',
                            journal_sign, assignment=I)
    settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I, presentation=V,
                               api_edge='api-edge')
    adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth'])
    acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot130'), conn, 'authority',
                           journal_sign, 'telegram-edge', adapter)
    intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=PROJECTS, api_edge='api-edge',
                       journal_signer='authority', sign=journal_sign)
    absent = _V130Absent()
    credentials = (CR.Credentials(S, conn, ids, 'authority', journal_sign, rp_id=_V130_HOST, origin=_V130_ORIGIN,
                                  state_dir=base / 'authority-state') if here else absent)
    authority = (AUTH.ApiAuthority(S, CM, conn, ids=ids, domain=DOMAIN, edge='api-edge', intake=intake,
                                   settlement=settlement, credentials=credentials) if here else absent)
    signer = SG.ApiSigner(config_path, 'edge-api', keyfile['api-auth']) if here else absent
    offset = [0.0]

    def clock():
        return _v130_time.time() + offset[0]

    api_config = {'origin': _V130_ORIGIN, 'rp_id': _V130_HOST, 'host': _V130_HOST, 'domain': DOMAIN, 'ids': ids,
                  'edge': 'api-edge', 'state_dir': str(base / 'api-state')}

    def new_api(state_dir=None):
        if not here:
            return absent
        return API.ControlApi(dict(api_config, state_dir=str(state_dir or base / 'api-state')), authority, signer,
                              clock=clock)

    api = [new_api()]

    COOKIE = '__Host-veldo-session'
    MESSAGES = '/api/v1/domains/%s/messages' % DOMAIN
    ANSWER = '/api/v1/domains/%s/decisions/answer' % DOMAIN

    def call(method, path, body=None, cookie=None, token=None, origin=_V130_ORIGIN, site='same-origin',
             ctype='application/json', host=_V130_HOST, raw=None, on=None):
        """One request to the API's handler: (status, {header: value}, JSON body)."""
        headers = {'Host': host}
        if method == 'POST':
            for name, value in (('Origin', origin), ('Sec-Fetch-Site', site), ('Content-Type', ctype)):
                if value is not None:
                    headers[name] = value
        if cookie is not None:
            headers['Cookie'] = '%s=%s' % (COOKIE, cookie)
        if token is not None:
            headers['X-Veldo-Token'] = token
        payload = raw if raw is not None else (_v130_json.dumps(body).encode() if body is not None else b'')
        status, out, value = (on or api[0]).handle(method, path, headers, payload)
        return status, {k: v for k, v in out}, value

    def refusal(result):
        return (result[2] or {}).get('refusal')

    def seen(result):
        return ' [observed: %s %s]' % (result[0], refusal(result))

    def cookie_of(result):
        text = result[1].get('Set-Cookie') or ''
        first = text.split(';')[0]
        name, _, value = first.partition('=')
        return value if name == COOKIE and value else None

    def journal_count():
        return conn.execute('SELECT count(*) FROM journal').fetchone()[0]

    def entity(eid):
        row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': _v130_json.loads(row[2])}

    def of_kind(kind, request=None):
        found = []
        for eid, version, text in conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (kind,)):
            data = _v130_json.loads(text)
            if request is None or data.get('request_id') == request:
                found.append((eid, version, data))
        return found

    def pending_path(pid):
        return base / 'api-state' / 'pending' / (pid + '.json')

    def register(browser, label, on=None, change_create=None, change_possession=None):
        """The registration and possession ceremonies over the API: (last result, pending id or None)."""
        begun = call('POST', '/api/v1/auth/registration/begin', {'label': label}, on=on)
        if begun[0] != 200:
            return begun, None
        browser.user_handle = begun[2]['user_handle']
        made = browser.create(begun[2]['challenge'], _V130_ORIGIN)
        if change_create is not None:
            change_create(made, begun[2]['challenge'])
        offered = call('POST', '/api/v1/auth/registration/credential', dict(made, registration_id=begun[2]['registration_id']),
                       on=on)
        if offered[0] != 200:
            return offered, None
        proof = browser.get(offered[2]['possession_challenge'], _V130_ORIGIN, _V130_HOST)
        if change_possession is not None:
            change_possession(proof)
        proved = call('POST', '/api/v1/auth/registration/possession',
                      dict({k: v for k, v in proof.items() if k != 'credential_id'},
                           registration_id=begun[2]['registration_id']), on=on)
        return proved, (begun[2]['registration_id'] if proved[0] == 200 else None)

    def steward_command(pending, principal, operation='enroll', signer_name='steward', over=None, tamper=None,
                        key=None, credential_id=None):
        """One enroll_api_credential (or revoke) command signed at the host: its observation and what it wrote."""
        cid = next_id('credential')
        if operation == 'enroll':
            command = CR.enrollment_command(pending, principal, cid) if CR is not None else {'command_id': cid}
        else:
            command = {'command_id': cid, 'operation': 'revoke_api_credential',
                       'target': CR.target(credential_id) if CR is not None else None,
                       'parameters': {'credential_id': credential_id}, 'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, signer_name, **(over or {}))
        signature = sign_as(key or signer_name, AC.canonical_envelope_bytes(env))
        if tamper is not None:
            tamper(command, env)
        before = journal_count()
        got = credentials.admit(env, command, signature)
        return dict(got, wrote=journal_count() - before)

    def enrolled(browser, principal, label):
        """Register a passkey over the API, then enroll it with the steward's signed command."""
        result, pid = register(browser, label)
        if pid is None:
            return {'outcome': 'refused', 'refusal': 'registration:%s' % refusal(result)}
        return steward_command(_v130_json.loads(pending_path(pid).read_text()), principal)

    def sign_in(browser, on=None, **change):
        issued = call('POST', '/api/v1/auth/challenge', {}, on=on)
        if issued[0] != 200:
            return issued, None, None
        assertion = browser.get(issued[2]['challenge'], _V130_ORIGIN, _V130_HOST, **change)
        done = call('POST', '/api/v1/auth/sign-in', assertion, on=on)
        return done, cookie_of(done), (done[2] or {}).get('csrf_token')

    def signed_command(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    def spelled_digest(value):
        return 'sha256:' + _v130_hashlib.sha256(_v130_json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                                  ensure_ascii=True).encode()).hexdigest()

    def open_request(alias, touchpoint='admission', owner='owner', requester='pm'):
        """Terms, the inbox request, its framing and its presentation: (request id, receipt)."""
        target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % alias, 'digest': spelled_digest(alias)}
        body = dict(ids, operation='terms', terms=alias, principal=requester, command_id=next_id('terms'),
                    nonce=next_id('terms-nonce'), touchpoint=touchpoint, target=target, proposal=None,
                    required_roles=[], quorum=None)
        subject = settlement.terms(signed_command(requester, body)).get('subject')
        inbox.apply(signed_command(requester, dict(ids, operation='open', alias=alias, principal=requester,
                                                   command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                       kind='decision', owner=owner, scope=['project-a'],
                                                       deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                       brief='Decide %s.' % alias, choices=list(_V130_CHOICES),
                                                       subject=subject))))
        rid = I.assignment_id(ids['repository_uuid'], alias)
        frame(alias, requester, 1)
        presenter.present(rid)
        return rid, presenter.current(rid) or {}

    def frame(alias, requester, version):
        presenter.frame(signed_command(requester, dict(ids, operation='frame', alias=alias, principal=requester,
                                                       request_version=version,
                                                       risk_statement='Low: a wrong choice costs one review cycle.',
                                                       command_id=next_id('f'), nonce=next_id('fn'))))

    def revise(alias, requester='pm'):
        rid = I.assignment_id(ids['repository_uuid'], alias)
        inbox.apply(signed_command(requester, dict(ids, operation='revise', alias=alias, principal=requester,
                                                   command_id=next_id('c'), nonce=next_id('n'), request_version=1,
                                                   changes={'brief': 'Revised brief for %s.' % alias})))
        frame(alias, requester, 2)
        presenter.present(rid)
        return presenter.current(rid) or {}

    def telegram_reply(receipt, text, who='owner'):
        sender = people[who]
        chat = bots['chats'][sender['id']]
        with bots['lock']:
            bot['update_next'] += 1
            update_id = bot['update_next']
        bot['updates'].append({'update_id': update_id, 'message': _v130_message(
            bots, bot, sender, chat, text, (receipt.get('message_ids') or [None])[-1])})
        acquirer.acquire()
        return settlement.run()

    def answer_body(receipt, choice='accept', rationale='answered from the phone'):
        return {'request_id': receipt.get('request_id'), 'request_version': receipt.get('request_version'),
                'presentation_id': receipt.get('presentation_id'), 'presentation_digest': receipt.get('brief_digest'),
                'presentation_version': receipt.get('presentation_version'), 'choice': choice, 'rationale': rationale}

    def assertion_for(principal, credential_id, operation, parameters, **over):
        """An API assertion as the API builds it, for the checks that drive the signer and authority directly."""
        at = _v130_time.time()
        expected = ({parameters['request_id']: parameters['request_version'],
                     parameters['presentation_id']: parameters['presentation_version']}
                    if operation == 'answer_decision' else {})
        value = dict(ids, schema='veldo.api_assertion/v1', domain=DOMAIN, channel='api', edge='api-edge',
                     edge_key_id='edge-api', request_id=next_id('api-direct'), principal=principal,
                     credential_id=credential_id, session='direct', operation=operation, target='direct',
                     parameters=parameters, expected_versions=expected, issued_at=at, expires_at=at + 60)
        value.update(over)
        return value

    def edge_signed(assertion, derived=None):
        """The api edge key's own signatures, made here as a signer that checks nothing would (for the
        authority's independent recheck)."""
        derived = AS.domain_request(assertion) if (derived is None and AS is not None) else derived
        return {'assertion': assertion, 'signature': sign_as('api-edge', S.canonical_bytes(assertion)),
                'domain_signature': sign_as('api-edge', S.canonical_bytes(derived)) if derived is not None else None}

    def signer_call(request, identity='edge-api', connection='api-auth'):
        return SIG.call(config_path, request, identity, keyfile[connection])

    phone = _V130Browser(base / 'browsers', 'owner-phone', -7)
    desktop = _V130Browser(base / 'browsers', 'owner-desktop', -8)
    laptop = _V130Browser(base / 'browsers', 'owner-laptop', -7)
    phone2 = _V130Browser(base / 'browsers', 'owner2-phone', -7)
    member_phone = _V130Browser(base / 'browsers', 'member-phone', -7)
    steward_phone = _V130Browser(base / 'browsers', 'steward-phone', -8)
    stranger = _V130Browser(base / 'browsers', 'stranger', -7)

    def verify(credential, assertion, challenge, origin=_V130_ORIGIN, rp_id=_V130_HOST):
        if W is None:
            return ['no verifier is installed']
        return W.assertion_problems(credential, assertion, challenge, origin, rp_id, base / 'verify-state')

    try:
        # webauthn/stand-in-browser: real ES256 and Ed25519 signatures over bytes laid out by hand.
        with section(WB):
            for browser in (phone, desktop):
                browser.user_handle = _v130_b64url(_v130_os.urandom(16))
                kind = 'ES256' if browser.algorithm == -7 else 'Ed25519'
                credential = {'credential_id': browser.credential_id, 'public_key': browser.public_key(),
                              'algorithm': browser.algorithm, 'user_handle': browser.user_handle}
                challenge = _v130_b64url(_v130_os.urandom(32))
                got = verify(credential, browser.get(challenge, _V130_ORIGIN, _V130_HOST), challenge)
                check(WB, '%s: a user-verified assertion over the issued challenge verifies [observed %s]' % (kind, got), got == [])

                def flip(field, at):
                    def change(value):
                        raw = bytearray(_v130_b64.urlsafe_b64decode(value[field] + '=' * (-len(value[field]) % 4)))
                        raw[at] ^= 0x01
                        value[field] = _v130_b64url(bytes(raw))
                    return change

                cases = (
                    ('a registration ceremony offered as a sign-in', browser.get(challenge, _V130_ORIGIN, _V130_HOST,
                                                                               kind='webauthn.create'), 'wrong_ceremony'),
                    ('another challenge', browser.get(_v130_b64url(_v130_os.urandom(32)), _V130_ORIGIN, _V130_HOST),
                     'wrong_challenge'),
                    ('another origin', browser.get(challenge, 'https://evil.example', _V130_HOST), 'wrong_origin'),
                    ('crossOrigin true', browser.get(challenge, _V130_ORIGIN, _V130_HOST, cross_origin=True), 'cross_origin'),
                    ('another relying party id', browser.get(challenge, _V130_ORIGIN, 'evil.example'), 'wrong_relying_party'),
                    ('user verified without user present', browser.get(challenge, _V130_ORIGIN, _V130_HOST, flags=0x04),
                     'user_not_present'),
                    ('no user verification', browser.get(challenge, _V130_ORIGIN, _V130_HOST, flags=0x01), 'user_not_verified'),
                    ('another user handle', browser.get(challenge, _V130_ORIGIN, _V130_HOST,
                                                        user_handle=_v130_b64url(_v130_os.urandom(16))), 'wrong_user_handle'),
                    ('authenticator data changed after signing', browser.get(challenge, _V130_ORIGIN, _V130_HOST,
                                                                             after=flip('authenticator_data', 36)),
                     'signature_invalid'),
                    ('the signature changed', browser.get(challenge, _V130_ORIGIN, _V130_HOST, after=flip('signature', 8)),
                     'signature_invalid'),
                    ('signed by another key', browser.get(challenge, _V130_ORIGIN, _V130_HOST, signer=stranger),
                     'signature_invalid'))
                for label, assertion, name in cases:
                    got = verify(credential, assertion, challenge)
                    check(WB, '%s: %s is refused as %s [observed %s]' % (kind, label, name, got), got == [name])
                wrong = verify(dict(credential, algorithm=-257), browser.get(challenge, _V130_ORIGIN, _V130_HOST), challenge)
                check(WB, '%s: an algorithm other than ES256 and Ed25519 is not accepted (%s)' % (kind, wrong),
                      wrong == ['signature_invalid'] and W is not None and W.key_problem(browser.public_key(), -257)
                      == 'unsupported_algorithm')
            other = verify({'credential_id': phone.credential_id, 'public_key': desktop.public_key(), 'algorithm': -7,
                            'user_handle': phone.user_handle}, phone.get(challenge, _V130_ORIGIN, _V130_HOST), challenge)
            check(WB, 'an Ed25519 key offered as ES256 is refused (%s)' % other, other == ['signature_invalid'])
            left = sorted(p.name for p in (base / 'verify-state').rglob('*')) if (base / 'verify-state').is_dir() else None
            mode = _v130_stat.S_IMODE((base / 'verify-state' / 'verify').stat().st_mode) \
                if (base / 'verify-state' / 'verify').is_dir() else None
            check(WB, 'OpenSSL verifies in a 0700 directory that keeps no key, signature or message afterwards',
                  left == ['verify'] and mode == 0o700)

        # webauthn/independent-vectors: the W3C's own assertions, made by an implementation that is not ours.
        with section(WV):
            origin, rp = 'https://example.org', 'example.org'

            def vector(name):
                x = _V130_W3C[name]
                prefix = ('3059301306072a8648ce3d020106082a8648ce3d03010703420004' if x['alg'] == -7
                          else '302a300506032b6570032100')
                der = bytes.fromhex(prefix + x['x'] + x.get('y', ''))
                credential = {'credential_id': _v130_b64url(bytes.fromhex(x['credential_id'])),
                              'public_key': _v130_b64url(der), 'algorithm': x['alg'], 'user_handle': None}
                assertion = {'credential_id': credential['credential_id'],
                             'client_data_json': _v130_b64url(bytes.fromhex(x['client_data_json'])),
                             'authenticator_data': _v130_b64url(bytes.fromhex(x['authenticator_data'])),
                             'signature': _v130_b64url(bytes.fromhex(x['signature'])), 'user_handle': None}
                message = bytes.fromhex(x['authenticator_data']) + _v130_hashlib.sha256(
                    bytes.fromhex(x['client_data_json'])).digest()
                return credential, assertion, _v130_b64url(bytes.fromhex(x['challenge'])), der, message, bytes.fromhex(x['signature'])

            def raw_verifies(alg, der, message, signature):
                return W is not None and W.openssl_verifies(alg, der, message, signature, base / 'verify-state')

            credential, assertion, challenge, der, message, signature = vector('16.6')
            got = verify(credential, assertion, challenge, origin, rp)
            check(WV, 'W3C 16.6 (ES256, user verified, a 1023-byte credential id) verifies [observed %s]' % got, got == [])
            bent = dict(assertion, signature=_v130_b64url(signature[:-1] + bytes([signature[-1] ^ 1])))
            check(WV, 'W3C 16.6 with its signature changed is refused',
                  verify(credential, bent, challenge, origin, rp) == ['signature_invalid'])
            check(WV, 'W3C 16.6 at another origin or relying party is refused',
                  verify(credential, assertion, challenge, _V130_ORIGIN, rp) == ['wrong_origin']
                  and verify(credential, assertion, challenge, origin, _V130_HOST) == ['wrong_relying_party'])
            credential, assertion, challenge, der, message, signature = vector('16.2')
            check(WV, 'W3C 16.2 (ES256): its signature verifies with OpenSSL, and the assertion is refused for no user '
                      'verification', raw_verifies(-7, der, message, signature)
                  and verify(credential, assertion, challenge, origin, rp) == ['user_not_verified'])
            credential, assertion, challenge, der, message, signature = vector('16.4')
            check(WV, 'W3C 16.4 (ES256, crossOrigin true): its signature verifies, and the assertion is refused as cross-origin',
                  raw_verifies(-7, der, message, signature)
                  and verify(credential, assertion, challenge, origin, rp) == ['cross_origin'])
            credential, assertion, challenge, der, message, signature = vector('16.11')
            check(WV, 'W3C 16.11 (Ed25519): its signature verifies with OpenSSL and not over a changed message, and the '
                      'assertion is refused for no user verification',
                  raw_verifies(-8, der, message, signature) and not raw_verifies(-8, der, message + b'x', signature)
                  and verify(credential, assertion, challenge, origin, rp) == ['user_not_verified'])

        # enrollment/pending-grants-nothing: a registration over the API grants nothing until a steward signs.
        with section(EP):
            before = journal_count()
            result, pid = register(phone, 'Owner phone')
            path = pending_path(pid) if pid else None
            check(EP, 'the registration and possession ceremonies make one pending registration' + seen(result),
                  result[0] == 200 and pid is not None and path.is_file()
                  and (result[2] or {}).get('outcome') == 'pending_steward_enrollment')
            check(EP, 'the pending registration is a 0600 file in a 0700 directory, showing the key fingerprint and label',
                  path is not None and _v130_stat.S_IMODE(path.stat().st_mode) == 0o600
                  and _v130_stat.S_IMODE(path.parent.stat().st_mode) == 0o700
                  and result[2].get('fingerprint') == (W.fingerprint(phone.public_key()) if W else None)
                  and result[2].get('label') == 'Owner phone')
            done, cookie, _t = sign_in(phone)
            check(EP, 'the pending credential cannot sign in' + seen(done),
                  done[0] == 401 and refusal(done) == 'unauthenticated:unknown_credential' and cookie is None)
            check(EP, 'nothing was written to the store by registering or by the refused sign-in', journal_count() == before)
            bad, _ = register(stranger, 'Wrong origin', change_create=lambda m, c: m.update(
                client_data_json=_v130_b64url(_V130Browser.client_data('webauthn.create', c, 'https://evil.example'))))
            check(EP, 'a registration ceremony from another origin is refused' + seen(bad),
                  bad[0] == 401 and refusal(bad) == 'unauthenticated:wrong_origin')
            bad, _ = register(stranger, 'Wrong challenge', change_create=lambda m, c: m.update(
                client_data_json=_v130_b64url(_V130Browser.client_data('webauthn.create', c[::-1], _V130_ORIGIN))))
            check(EP, 'a registration ceremony over another challenge is refused' + seen(bad),
                  bad[0] == 401 and refusal(bad) == 'unauthenticated:wrong_challenge')
            bad, _ = register(stranger, 'Other key', change_possession=lambda p: p.update(
                signature=stranger.get('x', _V130_ORIGIN, _V130_HOST, signer=laptop)['signature']))
            check(EP, 'a possession proof not signed by the offered key is refused' + seen(bad),
                  bad[0] == 401 and refusal(bad) == 'unauthenticated:signature_invalid')
            limited = new_api(base / 'api-limit')
            outcomes = [call('POST', '/api/v1/auth/registration/begin', {'label': 'try %d' % n}, on=limited)[0]
                        for n in range(4)]
            fourth = call('POST', '/api/v1/auth/registration/begin', {'label': 'try 5'}, on=limited)
            check(EP, 'at most three registrations are pending at a time [observed %s]' % outcomes,
                  outcomes == [200, 200, 200, 503] and refusal(fourth) == 'unavailable_service:pending_limit')

        # enrollment/steward-signed: only a steward's signed command at the host makes a credential.
        with section(ES):
            pending = _v130_json.loads(pending_path(pid).read_text()) if pid else {'binding': {}, 'proof': {}}
            _r2, pid2 = register(phone2, 'Owner2 phone')
            other_pending = _v130_json.loads(pending_path(pid2).read_text()) if pid2 else {'binding': {}, 'proof': {}}

            def relabel(command, env):
                command['parameters']['binding']['label'] = 'Relabelled'

            expired = _v130_copy.deepcopy(pending)
            expired['binding']['expires_at'] = _v130_time.time() - 1
            stolen = {'binding': pending['binding'], 'proof': other_pending['proof']}
            for label, got, name in (
                    ('a current member who is not a steward', steward_command(pending, 'owner', signer_name='member'),
                     'policy_refused'),
                    ('a service', steward_command(pending, 'owner', signer_name='pm'), 'not_a_person'),
                    ('a steward whose scope does not cover the principal\'s',
                     steward_command(pending, 'owner', signer_name='steward2'), 'scope_refused'),
                    ('a principal never enrolled', steward_command(pending, 'ghost'), 'principal_not_member'),
                    ('a service principal', steward_command(pending, 'pm'), 'principal_not_member'),
                    ('an envelope against a stale membership version',
                     steward_command(pending, 'owner', over={'membership_version': state()['membership_version'] - 1}),
                     'envelope_refused'),
                    ('an envelope for another store', steward_command(pending, 'owner', over={'store_uuid': 'other'}),
                     'envelope_refused'),
                    ('the label changed after signing', steward_command(pending, 'owner', tamper=relabel), 'envelope_refused'),
                    ('the steward\'s envelope signed by another key', steward_command(pending, 'owner', key='owner'),
                     'signature_invalid'),
                    ('an expired pending registration', steward_command(expired, 'owner'), 'registration_expired'),
                    ('another registration\'s possession proof', steward_command(stolen, 'owner'), 'possession_unproven')):
                check(ES, 'refused with nothing written: %s (%s) [observed %s, %s, %s written]'
                      % (label, name, got.get('outcome'), got.get('refusal'), got.get('wrote')),
                      got.get('outcome') == 'refused' and got.get('refusal') == name and got.get('wrote') == 0)
            roles_before = (AC.membership_entry(state()['membership'], 'owner') or {}).get('roles')
            accepted = steward_command(pending, 'owner')
            check(ES, 'the steward\'s signed enrollment of the owner\'s own passkey is accepted [observed %s]'
                  % accepted.get('refusal'), accepted.get('outcome') == 'accepted' and accepted.get('wrote') == 1)
            kept = CR.record(S.materialized_state(conn)['entities'], phone.credential_id) if CR else None
            check(ES, 'the record holds the principal, credential, key, algorithm, user handle, relying party, origin, '
                      'label, effective time, proof and envelope, and grants no role',
                  kept is not None and kept['principal'] == 'owner' and kept['public_key'] == phone.public_key()
                  and kept['algorithm'] == -7 and kept['user_handle'] == phone.user_handle and kept['rp_id'] == _V130_HOST
                  and kept['origin'] == _V130_ORIGIN and kept['label'] == 'Owner phone'
                  and isinstance(kept['effective_at'], float) and kept['enrolled_by'] == 'steward'
                  and kept['envelope'].get('principal') == 'steward'
                  and roles_before and (AC.membership_entry(state()['membership'], 'owner') or {}).get('roles') == roles_before)
            check(ES, 'the record verifies on its own: its possession proof rechecks with OpenSSL',
                  kept is not None and W.possession_problems(kept['proof']['binding'], kept['proof']['assertion'],
                                                             _V130_ORIGIN, _V130_HOST, base / 'verify-state') == [])
            again = steward_command(pending, 'owner2')
            check(ES, 'a credential id or key already held is refused as credential_in_use',
                  again.get('refusal') == 'credential_in_use' and again.get('wrote') == 0)
            check(ES, 'no API route and no API assertion enrolls a credential',
                  not any('enroll' in str(r.operation) for r in getattr(API, 'ROUTES', ()))
                  and AS is not None and 'enroll_api_credential' not in AS.OPERATIONS)
            for browser, who, label in ((phone2, 'owner2', None), (desktop, 'owner', 'Owner desktop'),
                                        (laptop, 'owner', 'Owner laptop'), (member_phone, 'member', 'Member phone'),
                                        (steward_phone, 'steward', 'Steward phone')):
                got = (steward_command(other_pending, who) if label is None else enrolled(browser, who, label))
                check(ES, 'the %s passkey of %s is enrolled [observed %s]' % (label or 'phone', who, got.get('refusal')),
                      got.get('outcome') == 'accepted')
            check(ES, 'an enrolled registration is no longer pending', pid is not None and not pending_path(pid).exists()
                  and pid2 is not None and not pending_path(pid2).exists())

        # session/cookie-and-expiry: a server-side session from one passkey tap, and every way it ends.
        with section(SC):
            issued = call('POST', '/api/v1/auth/challenge', {})
            proof = phone.get((issued[2] or {}).get('challenge', ''), _V130_ORIGIN, _V130_HOST)
            done = call('POST', '/api/v1/auth/sign-in', proof)
            cookie, token = cookie_of(done), (done[2] or {}).get('csrf_token')
            attributes = [a.strip() for a in (done[1].get('Set-Cookie') or '').split(';')]
            check(SC, 'a verified passkey sign-in makes a session for the credential\'s principal' + seen(done),
                  done[0] == 200 and cookie and done[2].get('principal') == 'owner'
                  and done[2].get('credential_id') == phone.credential_id)
            check(SC, 'the cookie is __Host-veldo-session, Secure, HttpOnly, SameSite=Strict, Path=/, with no Domain '
                      '[observed %s]' % attributes[1:],
                  sorted(attributes[1:]) == ['HttpOnly', 'Path=/', 'SameSite=Strict', 'Secure']
                  and cookie is not None and len(_v130_b64.urlsafe_b64decode(cookie + '=' * (-len(cookie) % 4))) == 32)
            sessions = getattr(api[0], 'sessions', None)
            held = repr(getattr(sessions, '_by_hash', {}))
            check(SC, 'the API keeps only the cookie\'s SHA-256, never the cookie',
                  cookie is not None and cookie not in held
                  and _v130_hashlib.sha256(cookie.encode()).hexdigest() in getattr(sessions, '_by_hash', {}))
            read = call('GET', '/api/v1/auth/session', cookie=cookie)
            check(SC, 'the session read returns the principal and the same anti-forgery token' + seen(read),
                  read[0] == 200 and read[2].get('principal') == 'owner' and read[2].get('csrf_token') == token
                  and token and len(_v130_b64.urlsafe_b64decode(token + '=' * (-len(token) % 4))) == 32)
            replay = call('POST', '/api/v1/auth/sign-in', proof)
            check(SC, 'a sign-in assertion replayed over its used challenge is refused' + seen(replay),
                  replay[0] == 401 and refusal(replay) == 'unauthenticated:challenge' and cookie_of(replay) is None)
            late = call('POST', '/api/v1/auth/challenge', {})
            offset[0] = 121
            stale = call('POST', '/api/v1/auth/sign-in', phone.get(late[2].get('challenge', ''), _V130_ORIGIN, _V130_HOST))
            offset[0] = 0
            check(SC, 'a challenge older than 120 seconds is refused' + seen(stale),
                  stale[0] == 401 and refusal(stale) == 'unauthenticated:challenge')
            again, cookie2, _t2 = sign_in(phone)
            check(SC, 'each sign-in makes a new session cookie', cookie2 is not None and cookie2 != cookie)
            offset[0] = 20 * 60
            alive = call('GET', '/api/v1/auth/session', cookie=cookie2)
            offset[0] = 40 * 60
            still = call('GET', '/api/v1/auth/session', cookie=cookie2)
            offset[0] = 40 * 60 + 30 * 60 + 5
            idle = call('GET', '/api/v1/auth/session', cookie=cookie2)
            offset[0] = 0
            check(SC, 'a session touched within 30 minutes lives, and ends 30 minutes after its last request'
                  + seen(idle), alive[0] == 200 and still[0] == 200 and idle[0] == 401
                  and refusal(idle) == 'unauthenticated:session_expired')
            _d, cookie3, _t3 = sign_in(phone)
            statuses = []
            for step in range(1, 30):
                offset[0] = step * 25 * 60
                statuses.append(call('GET', '/api/v1/auth/session', cookie=cookie3)[0])
            offset[0] = 0
            check(SC, 'a session in steady use ends 12 hours after sign-in [observed %s]' % statuses,
                  statuses[:28] == [200] * 28 and statuses[28] == 401)
            out = call('POST', '/api/v1/auth/sign-out', {}, cookie=cookie, token=token)
            after = call('GET', '/api/v1/auth/session', cookie=cookie)
            check(SC, 'sign-out ends the session and clears the cookie' + seen(after),
                  out[0] == 200 and 'Max-Age=0' in (out[1].get('Set-Cookie') or '') and after[0] == 401
                  and refusal(after) == 'unauthenticated:no_session')
            _a, c_phone, t_phone = sign_in(phone)
            _b, c_desk, _t_desk = sign_in(desktop)
            _c, c_other, _t_other = sign_in(phone2)
            everywhere = call('POST', '/api/v1/auth/sign-out-everywhere', {}, cookie=c_phone, token=t_phone)
            check(SC, 'sign out everywhere ends every session of the member and no one else\'s' + seen(everywhere),
                  everywhere[0] == 200 and call('GET', '/api/v1/auth/session', cookie=c_desk)[0] == 401
                  and call('GET', '/api/v1/auth/session', cookie=c_phone)[0] == 401
                  and call('GET', '/api/v1/auth/session', cookie=c_other)[0] == 200)
            _d, c_restart, _t = sign_in(phone)
            first = api[0]
            api[0] = new_api()
            check(SC, 'an API restart ends every session', c_restart is not None
                  and call('GET', '/api/v1/auth/session', cookie=c_restart)[0] == 401)
            events = getattr(first, 'observations', [])
            logged = _v130_json.dumps(events)
            check(SC, 'observations name the route, principal, credential and session handle, never a cookie or token',
                  bool(events) and all(v not in logged for v in (cookie, cookie2, token))
                  and any(e.get('route') == 'auth.session' and e.get('principal') == 'owner' and e.get('session')
                          and e.get('credential_id') == phone.credential_id for e in events))

        # A fresh signed-in session per principal for the rows below.
        _s, owner_cookie, owner_token = sign_in(phone)
        _s, owner2_cookie, owner2_token = sign_in(phone2)
        _s, member_cookie, member_token = sign_in(member_phone)
        _s, steward_cookie, steward_token = sign_in(steward_phone)
        _s, laptop_cookie, laptop_token = sign_in(laptop)
        _s, desktop_cookie, desktop_token = sign_in(desktop)
        write_routes = [r for r in getattr(API, 'ROUTES', ()) if r.session and r.method == 'POST']
        receipt_f = {'request_id': 'r', 'request_version': 1, 'presentation_id': 'p', 'brief_digest': 'd',
                     'presentation_version': 1}
        bodies = {'auth.sign_out': {}, 'auth.sign_out_everywhere': {}, 'auth.revoke_credential': {'credential_id': 'x'},
                  'messages.send': {'text': 'hello'}, 'decisions.answer': answer_body(receipt_f)}

        def path_of(route, domain=DOMAIN):
            return route.path.replace('{domain}', domain)

        # session/forgery-refused: a write carries the token, a same-origin Origin and JSON, or nothing happens.
        with section(SF):
            check(SF, 'the write routes are derived from the published table [observed %s]' % [r.name for r in write_routes],
                  sorted(r.name for r in write_routes) == sorted(bodies))
            for route in write_routes:
                before = journal_count()
                for label, over in (('no anti-forgery token', {'token': None}), ('another token', {'token': 'x' * 43}),
                                    ('another origin', {'origin': 'https://evil.example'}), ('no Origin', {'origin': None}),
                                    ('a cross-site fetch', {'site': 'cross-site'}), ('a same-site fetch', {'site': 'same-site'}),
                                    ('a form content type', {'ctype': 'application/x-www-form-urlencoded'}),
                                    ('a text/plain body', {'ctype': 'text/plain'})):
                    kw = dict({'cookie': owner_cookie, 'token': owner_token}, **over)
                    got = call('POST', path_of(route), bodies[route.name], **kw)
                    check(SF, '%s: %s is refused unauthorized' % (route.name, label) + seen(got),
                          got[0] == 403 and str(refusal(got)).startswith('unauthorized:'))
                check(SF, '%s: nothing was written and the session lives' % route.name,
                      journal_count() == before and call('GET', '/api/v1/auth/session', cookie=owner_cookie)[0] == 200)
            sign_in_route = call('POST', '/api/v1/auth/challenge', {}, origin='https://evil.example')
            check(SF, 'a ceremony from another origin is refused' + seen(sign_in_route), sign_in_route[0] == 403)
            wrong_host = call('GET', '/api/v1/auth/session', cookie=owner_cookie, host='evil.example')
            check(SF, 'a request naming another Host is refused' + seen(wrong_host),
                  wrong_host[0] == 400 and refusal(wrong_host) == 'invalid_input:host')
            big = call('POST', MESSAGES, cookie=owner_cookie, token=owner_token,
                       raw=_v130_json.dumps({'text': 'x' * (70 * 1024)}).encode())
            check(SF, 'a body over 64 KiB is refused' + seen(big), big[0] == 400 and refusal(big) == 'invalid_input:body_too_large')
            reads = call('GET', '/api/v1/auth/session', cookie=owner_cookie, token=None)
            check(SF, 'a read needs no token and changes nothing', reads[0] == 200)

        # routes/every-family: every route of the published table, each family's refusals and its valid use.
        with section(RF):
            table = list(getattr(API, 'ROUTES', ()))
            check(RF, 'the route table and the registered handlers agree [observed %s]' % api[0].route_problems(),
                  table and api[0].route_problems() == [])
            check(RF, 'phase 1 publishes the auth, messages and decisions families',
                  sorted({r.family for r in table}) == ['auth', 'decisions', 'messages'])
            for route in [r for r in table if r.session]:
                body = bodies.get(route.name) if route.method == 'POST' else None
                before = journal_count()
                none = call(route.method, path_of(route), body)
                bogus = call(route.method, path_of(route), body, cookie=_v130_b64url(_v130_os.urandom(32)), token='x')
                _e, e_cookie, e_token = sign_in(phone)
                offset[0] = 31 * 60
                expired = call(route.method, path_of(route), body, cookie=e_cookie, token=e_token)
                offset[0] = 0
                check(RF, '%s: no session, an unknown cookie and an expired session are each unauthenticated%s%s%s'
                      % (route.name, seen(none), seen(bogus), seen(expired)),
                      none[0] == 401 and refusal(none) == 'unauthenticated:no_session' and bogus[0] == 401
                      and refusal(bogus) == 'unauthenticated:no_session' and expired[0] == 401
                      and refusal(expired) == 'unauthenticated:session_expired' and journal_count() == before)
                if '{domain}' in route.path:
                    other = call('POST', path_of(route, 'another-domain'), body, cookie=owner_cookie, token=owner_token)
                    check(RF, '%s: another domain is unauthorized' % route.name + seen(other),
                          other[0] == 403 and refusal(other) == 'unauthorized:domain' and journal_count() == before)
            role = call('POST', '/api/v1/auth/credentials/revoke', {'credential_id': laptop.credential_id},
                        cookie=owner_cookie, token=owner_token)
            check(RF, 'auth: a member who is not a steward cannot revoke a credential' + seen(role),
                  role[0] == 403 and 'policy_refused' in str(refusal(role))
                  and CR is not None and CR.current(state(), laptop.credential_id, _v130_time.time())[1] is None)
            outsider = call('POST', MESSAGES, {'text': 'please build this'}, cookie=member_cookie, token=member_token)
            check(RF, 'messages: a member whose scope covers no served project is unauthorized' + seen(outsider),
                  outsider[0] == 403 and refusal(outsider) == 'unauthorized:no_project')
            rf_rid, rf_receipt = open_request('rf1')
            wrong_owner = call('POST', ANSWER, answer_body(rf_receipt), cookie=owner2_cookie, token=owner2_token)
            check(RF, 'decisions: a member who is not the presented owner is unauthorized' + seen(wrong_owner),
                  wrong_owner[0] == 403 and 'not_owner' in str(refusal(wrong_owner)) and not of_kind('request_settlement', rf_rid))
            ok_auth = call('GET', '/api/v1/auth/session', cookie=owner_cookie)
            ok_message = call('POST', MESSAGES, {'text': 'Route check for project-a'}, cookie=owner_cookie, token=owner_token)
            ok_answer = call('POST', ANSWER, answer_body(rf_receipt), cookie=owner_cookie, token=owner_token)
            check(RF, 'a valid current enrollment is served in every family%s%s%s'
                  % (seen(ok_auth), seen(ok_message), seen(ok_answer)),
                  ok_auth[0] == 200 and ok_message[0] == 200 and ok_message[2].get('outcome') == 'proposed'
                  and ok_answer[0] == 200 and ok_answer[2].get('outcome') == 'settled')

        # routes/body-actor-refused: the speaker is the session's member; a body naming one is refused.
        with section(RB):
            for route in write_routes:
                before = journal_count()
                for field in ('principal', 'actor', 'actor_id', 'decider'):
                    got = call('POST', path_of(route), dict(bodies[route.name], **{field: 'owner'}),
                               cookie=owner2_cookie, token=owner2_token)
                    check(RB, '%s: a body naming %s is refused invalid_input' % (route.name, field) + seen(got),
                          got[0] == 400 and refusal(got) == 'invalid_input:actor_field')
                extra = call('POST', path_of(route), dict(bodies[route.name], unexpected=True),
                             cookie=owner2_cookie, token=owner2_token)
                check(RB, '%s: an unknown field is refused, never ignored' % route.name + seen(extra),
                      extra[0] == 400 and refusal(extra) == 'invalid_input:fields')
                if route.required:
                    short = call('POST', path_of(route), {k: v for k, v in bodies[route.name].items() if k != route.required[0]},
                                 cookie=owner2_cookie, token=owner2_token)
                    check(RB, '%s: a missing field is refused' % route.name + seen(short),
                          short[0] == 400 and refusal(short) == 'invalid_input:fields')
                check(RB, '%s: nothing was written' % route.name, journal_count() == before)
            rb_rid, rb_receipt = open_request('rb1')
            before = journal_count()
            forged = call('POST', ANSWER, dict(answer_body(rb_receipt), actor_id='owner'), cookie=owner2_cookie,
                          token=owner2_token)
            check(RB, 'a decision authorized with the body actor_id is refused as impersonation, and nothing is settled'
                  + seen(forged), forged[0] == 400 and refusal(forged) == 'invalid_input:actor_field'
                  and journal_count() == before and not of_kind('request_settlement', rb_rid)
                  and not of_kind('settlement_api_answer', rb_rid)
                  and (entity(rb_rid) or {}).get('data', {}).get('state') in I.PENDING)
            own = call('POST', ANSWER, answer_body(rb_receipt), cookie=owner_cookie, token=owner_token)
            check(RB, 'control: the owner\'s own session answers the same decision' + seen(own),
                  own[0] == 200 and own[2].get('outcome') == 'settled')

        # session/revocation-ends: a revoked credential or membership ends the session, even in flight.
        with section(SR):
            ui = call('POST', '/api/v1/auth/credentials/revoke', {'credential_id': desktop.credential_id},
                      cookie=steward_cookie, token=steward_token)
            kept = CR.record(S.materialized_state(conn)['entities'], desktop.credential_id) if CR else None
            last = S.export_journal(conn)[-1]
            check(SR, 'a steward\'s own session revokes a credential through the edge; the journal actor is the steward'
                  + seen(ui), ui[0] == 200 and (ui[2] or {}).get('outcome') == 'revoked' and kept is not None
                  and kept.get('revoked_by') == 'steward' and kept.get('revoked_at') is not None
                  and last.get('principal') == 'steward')
            gone = call('GET', '/api/v1/auth/session', cookie=desktop_cookie)
            check(SR, 'the revoked credential\'s session ends' + seen(gone),
                  gone[0] == 401 and str(refusal(gone)).startswith('unauthenticated:'))
            # In flight: an assertion signed while the credential was current, revoked before it executes.
            flying = assertion_for('owner', laptop.credential_id, 'send_message',
                                   {'text': 'in flight', 'project': 'project-a', 'clarifies': None})
            try:
                signature, domain_signature = signer(flying)
            except Exception:  # noqa: BLE001 - the tree without the API has no signer; the row fails below
                signature, domain_signature = None, None
            host_revoke = steward_command(None, None, operation='revoke', credential_id=laptop.credential_id)
            revoked_record = S.export_journal(conn)[-1]
            before = journal_count()
            late = authority.apply({'assertion': flying, 'signature': signature, 'domain_signature': domain_signature})
            check(SR, 'an assertion signed before a revocation is refused by the authority\'s own recheck [observed %s]'
                  % late.get('reason'), signature is not None and host_revoke.get('outcome') == 'accepted'
                  and late.get('ok') is False and late.get('reason') == 'unauthenticated:credential_revoked'
                  and journal_count() == before)
            ended = api[0].follow(revoked_record)
            check(SR, 'following the journal ends the revoked credential\'s sessions at once [observed %s]' % ended,
                  ended == 1 and api[0].sessions.find(laptop_cookie)[1] == 'no_session')
            _m, doomed_cookie, _dt = sign_in(member_phone)
            admin('steward', 'revoke_membership', {'principal': 'member', 'revoked_at': _v130_time.time()})
            ended = api[0].follow(S.export_journal(conn)[-1])
            check(SR, 'following a revoke_membership ends every session of the member at once [observed %s]' % ended,
                  ended == 2 and api[0].sessions.find(doomed_cookie)[1] == 'no_session'
                  and api[0].sessions.find(member_cookie)[1] == 'no_session')
            check(SR, 'revoke_membership ends the member\'s credentials with it',
                  CR is not None and CR.current(state(), member_phone.credential_id, _v130_time.time())[1]
                  == 'principal_not_member')
            _x, relogin, _y = sign_in(member_phone)
            check(SR, 'a revoked member cannot sign in again', relogin is None)

        # edge/signer-api-purpose: the protected signer signs one thing for the api edge, after its own checks.
        with section(EG):
            good = assertion_for('owner', phone.credential_id, 'send_message',
                                 {'text': 'signed by the edge', 'project': 'project-a', 'clarifies': None})
            request = {'operation': 'sign_api_assertion', 'channel': 'api', 'edge_key_id': 'edge-api', 'assertion': good}
            signed = signer_call(request)
            derived = AS.domain_request(good) if AS is not None else None
            check(EG, 'a current member\'s assertion is signed, with its derived intake request [observed %s]'
                  % signed.get('refusal'), signed.get('accepted') is True
                  and verifies('api-edge', public['api-edge'], S.canonical_bytes(good), signed.get('signature'))
                  and derived is not None and derived.get('principal') == 'owner'
                  and verifies('api-edge', public['api-edge'], S.canonical_bytes(derived), signed.get('domain_signature')))
            for label, over, name in (
                    ('an answer-signing request', dict(request, operation='sign_answer'), 'forbidden-purpose'),
                    ('a request with a key path', dict(request, key_path='/tmp/key'), 'key-path'),
                    ('a request with another field', dict(request, extra=1), 'forbidden-purpose'),
                    ('an assertion with another field', dict(request, assertion=dict(good, actor='owner')), 'forbidden-purpose'),
                    ('an assertion for another operation', dict(request, assertion=dict(good, operation='enroll_api_credential')),
                     'forbidden-purpose'),
                    ('a request for another channel', dict(request, channel='telegram_chat'), 'channel-mismatch'),
                    ('an assertion naming another edge', dict(request, assertion=dict(good, edge='telegram-edge')),
                     'edge-mismatch'),
                    ('an assertion for another store', dict(request, assertion=dict(good, store_uuid='other')),
                     'wrong-authority'),
                    ('an expired assertion', dict(request, assertion=dict(good, issued_at=good['issued_at'] - 120,
                                                                         expires_at=good['expires_at'] - 120)),
                     'assertion-expired'),
                    ('a principal who does not hold the credential', dict(request, assertion=dict(good, principal='owner2')),
                     'credential-not-current'),
                    ('a revoked credential', dict(request, assertion=dict(good, credential_id=desktop.credential_id)),
                     'credential-not-current'),
                    ('a principal with no credential', dict(request, assertion=dict(good, principal='pm')),
                     'credential-not-current')):
                got = signer_call(over)
                check(EG, 'the signer refuses %s (%s) [observed %s]' % (label, name, got.get('refusal')),
                      got.get('accepted') is False and got.get('refusal') == name and 'signature' not in got)
            other_key = signer_call(request, connection='edge-auth')
            check(EG, 'a caller without the api edge\'s connection key is unauthenticated',
                  other_key.get('refusal') == 'unauthenticated-channel')
            telegram = signer_call({'operation': 'sign_api_assertion', 'channel': 'telegram_chat',
                                    'edge_key_id': 'edge-telegram', 'assertion': good}, 'edge-telegram', 'edge-auth')
            check(EG, 'the Telegram edge cannot have an API assertion signed', telegram.get('accepted') is False)
            outputs = [_v130_json.dumps(getattr(signer, 'results', [])), _v130_json.dumps(getattr(api[0], 'observations', [])),
                       _v130_json.dumps(getattr(authority, 'observations', []))]
            check(EG, 'the API holds no key: the edge key is read only by the signer and reaches no output',
                  here and not any(isinstance(v, _v130_Path) for v in vars(signer).values() if v == keyfile['api-edge'])
                  and all(private_api_edge.decode() not in blob for blob in outputs))

        # edge/authority-recheck: the authority decides again, whatever the signer signed.
        with section(EA):
            def message_assertion(text, principal='owner', **over):
                return assertion_for(principal, phone.credential_id, 'send_message',
                                     {'text': text, 'project': 'project-a', 'clarifies': None}, **over)

            valid = message_assertion('recheck control')
            try:
                pair = signer(valid)
            except Exception:  # noqa: BLE001 - no signer on the tree without the API
                pair = (None, None)
            packet = {'assertion': valid, 'signature': pair[0], 'domain_signature': pair[1]}
            before = journal_count()
            tampered = dict(packet, assertion=dict(valid, parameters=dict(valid['parameters'], text='changed after signing')))
            skewed = message_assertion('from another domain', domain='another-domain')
            wrong_request = dict(edge_signed(message_assertion('other request')))
            wrong_request['domain_signature'] = sign_as('api-edge', S.canonical_bytes(
                AS.domain_request(message_assertion('not the one asserted')))) if AS is not None else None
            late_authority = (AUTH.ApiAuthority(S, CM, conn, ids=ids, domain=DOMAIN, edge='api-edge', intake=intake,
                                                settlement=settlement, credentials=credentials,
                                                clock=lambda: _v130_time.time() + 61) if here else absent)
            for label, got, name in (
                    ('an assertion changed after signing', authority.apply(tampered), 'unauthenticated:signature'),
                    ('an assertion signed by the owner, not the edge',
                     authority.apply(dict(packet, signature=sign_as('owner', S.canonical_bytes(valid)))),
                     'unauthenticated:signature'),
                    ('an assertion naming another edge', authority.apply(edge_signed(message_assertion('x', edge='telegram-edge'))),
                     'unauthenticated:edge'),
                    ('an assertion replayed after its expiry', late_authority.apply(packet), 'unauthenticated:expired'),
                    ('a principal who does not hold the named credential',
                     authority.apply(edge_signed(message_assertion('impersonation', principal='owner2'))),
                     'unauthenticated:credential_of_another_principal'),
                    ('a credential nobody holds',
                     authority.apply(edge_signed(assertion_for('owner', 'unknown-credential', 'send_message',
                                                               {'text': 'nobody', 'project': 'project-a', 'clarifies': None}))),
                     'unauthenticated:unknown_credential'),
                    ('an assertion for another domain', authority.apply(edge_signed(skewed)), 'unauthorized:domain'),
                    ('an edge signature over another intake request than the assertion names',
                     authority.apply(wrong_request), 'unauthenticated:signature'),
                    ('an operation outside the assertion contract',
                     authority.apply(edge_signed(dict(message_assertion('x'), operation='enroll_api_credential'), derived={})),
                     'invalid_input:assertion')):
                check(EA, 'the authority refuses %s (%s) [observed %s]' % (label, name, got.get('reason')),
                      got.get('ok') is False and got.get('reason') == name)
            check(EA, 'nothing was written by any refused assertion', journal_count() == before)
            first = authority.apply(packet)
            written = journal_count()
            repeated = authority.apply(packet)
            check(EA, 'the valid assertion executes once; the same request id again writes nothing [observed %s, %s]'
                  % (first.get('reason'), (repeated.get('result') or {}).get('repeated')),
                  first.get('ok') is True and repeated.get('ok') is True
                  and (repeated.get('result') or {}).get('repeated') is True and journal_count() == written)
            record = next((o for o in getattr(authority, 'observations', []) if o.get('request_id') == valid['request_id']), {})
            check(EA, 'the authority observes the operation, principal, credential, session and assertion digest',
                  record.get('operation') == 'send_message' and record.get('principal') == 'owner'
                  and record.get('credential_id') == phone.credential_id and record.get('session') == 'direct'
                  and str(record.get('assertion_digest')).startswith('sha256:'))

        # messages/common-intake: a plain-text message from the API is a VELDO-0126 intake request, unchanged.
        with section(MS):
            text = '  Add a dark mode to the factory dashboard, see OPS-142.\nKeep the old palette too.  '
            before = journal_count()
            sent = call('POST', MESSAGES, {'text': text, 'project': 'project-a'}, cookie=owner_cookie, token=owner_token)
            source = intake.source('api_request', (sent[2] or {}).get('api_request_id'))
            proposal = intake.proposal((sent[2] or {}).get('proposal_id')) if sent[0] == 200 else None
            check(MS, 'the message is proposed by the common intake for the session\'s member' + seen(sent),
                  sent[0] == 200 and sent[2].get('outcome') == 'proposed' and source is not None
                  and source['principal'] == 'owner' and source['text'] == text
                  and proposal is not None and proposal['state'] == 'PROPOSED' and proposal['project'] == 'project-a')
            check(MS, 'the source is the API\'s: channel api, the edge, the request id and the request digest',
                  source is not None and source['source_kind'] == 'api_request'
                  and source['command']['provenance'].get('channel') == 'api'
                  and source['command']['provenance'].get('edge') == 'api-edge'
                  and source['command']['provenance'].get('request_id') == sent[2].get('api_request_id'))
            kinds = sorted({c['kind'] for r in S.export_journal(conn)[before:] for c in r['transition'].values()})
            check(MS, 'intake admits nothing itself: the write is intake records only [observed %s]' % kinds,
                  kinds == ['intake_proposal', 'intake_source'])
            inboxed = call('POST', MESSAGES, {'text': 'Something for later'}, cookie=owner_cookie, token=owner_token)
            check(MS, 'a message naming no project is kept with the question naming the candidates' + seen(inboxed),
                  inboxed[0] == 200 and inboxed[2].get('outcome') == 'inbox'
                  and (inboxed[2].get('question') or {}).get('candidates') == ['project-a', 'project-b'])
            resolved = call('POST', MESSAGES, {'text': 'It is for project-a', 'clarifies': inboxed[2].get('proposal_id')},
                            cookie=owner_cookie, token=owner_token)
            check(MS, 'a follow-up naming the proposal resolves it into an objective' + seen(resolved),
                  resolved[0] == 200 and resolved[2].get('outcome') == 'resolved')

        # decisions/exact-settlement: an answer names the versions the owner saw and settles under VELDO-0068.
        with section(DE):
            d1, r1 = open_request('de1')
            before_settle = journal_count()
            answered = call('POST', ANSWER, answer_body(r1, 'accept', 'looks right to me'), cookie=owner_cookie,
                            token=owner_token)
            settled = of_kind('request_settlement', d1)
            api_answers = of_kind('settlement_api_answer', d1)
            check(DE, 'the owner\'s answer at the current request and presentation versions settles' + seen(answered),
                  answered[0] == 200 and answered[2].get('outcome') == 'settled' and len(settled) == 1
                  and settled[0][2]['ruling'] == 'approve' and settled[0][2]['principals'] == ['owner']
                  and settled[0][2]['originating_channel'] == 'api' and settled[0][2]['edge_principal'] == 'api-edge'
                  and settled[0][2]['rationale'] == 'looks right to me')
            check(DE, 'the recorded answer is the session\'s member on channel api, under the request id the API issued',
                  len(api_answers) == 1 and api_answers[0][2]['principal'] == 'owner' and api_answers[0][2]['channel'] == 'api'
                  and api_answers[0][2]['answer_id'] == answered[2].get('api_request_id')
                  and api_answers[0][2]['presentation_version'] == r1.get('presentation_version'))
            d2, first = open_request('de2')
            second = revise('de2')
            before = journal_count()
            stale = call('POST', ANSWER, answer_body(first), cookie=owner_cookie, token=owner_token)
            check(DE, 'an answer to the presentation the owner saw before a revision is refused as stale' + seen(stale),
                  stale[0] == 409 and 'stale_presentation' in str(refusal(stale)) and journal_count() == before
                  and not of_kind('request_settlement', d2))
            current = call('POST', ANSWER, answer_body(second, 'reject', 'not now'), cookie=owner_cookie, token=owner_token)
            check(DE, 'the answer to the current presentation settles' + seen(current),
                  current[0] == 200 and current[2].get('outcome') == 'settled'
                  and [s[2]['ruling'] for s in of_kind('request_settlement', d2)] == ['reject'])
            d4, r4 = open_request('de4')
            before = journal_count()
            unowned = call('POST', ANSWER, answer_body(r4), cookie=owner2_cookie, token=owner2_token)
            unoffered = call('POST', ANSWER, answer_body(r4, 'maybe'), cookie=owner_cookie, token=owner_token)
            check(DE, 'another owner\'s answer is unauthorized and an unoffered choice invalid, nothing written%s%s'
                  % (seen(unowned), seen(unoffered)),
                  unowned[0] == 403 and 'not_owner' in str(refusal(unowned)) and unoffered[0] == 400
                  and 'unmatched_choice' in str(refusal(unoffered)) and journal_count() == before
                  and not of_kind('request_settlement', d4))

        # decisions/one-ruling: Telegram and the UI answering one request give one terminal ruling.
        with section(DO):
            d3, r3 = open_request('do1')
            telegram_reply(r3, 'accept: as discussed')
            first_ruling = of_kind('request_settlement', d3)
            before = journal_count()
            ui_late = call('POST', ANSWER, answer_body(r3, 'reject', 'changed my mind'), cookie=owner_cookie,
                           token=owner_token)
            after = of_kind('request_settlement', d3)
            check(DO, 'after Telegram settles, the UI answer is refused and settles nothing' + seen(ui_late),
                  len(first_ruling) == 1 and first_ruling[0][2]['originating_channel'] == 'telegram_chat'
                  and ui_late[0] == 409 and journal_count() == before)
            check(DO, 'one terminal ruling with unchanged provenance: the Telegram settlement, version 1, as it was',
                  after == first_ruling and len(after) == 1 and after[0][1] == 1 and after[0][2]['ruling'] == 'approve'
                  and not of_kind('settlement_api_answer', d3)
                  and (entity(d3) or {}).get('data', {}).get('state') == 'SATISFIED')
            d5, r5 = open_request('do2')
            ui_first = call('POST', ANSWER, answer_body(r5, 'reject', 'from the desk'), cookie=owner_cookie,
                            token=owner_token)
            telegram_reply(r5, 'accept: from the phone')
            ruled = of_kind('request_settlement', d5)
            check(DO, 'after the UI settles, a Telegram answer adds no second ruling' + seen(ui_first),
                  ui_first[0] == 200 and len(ruled) == 1 and ruled[0][1] == 1 and ruled[0][2]['ruling'] == 'reject'
                  and ruled[0][2]['originating_channel'] == 'api')

        # transport/loopback-only: plain HTTP on a loopback address only, behind the host's TLS terminator.
        with section(TL):
            for host in ('0.0.0.0', '192.168.1.10', '::', 'localhost', _V130_HOST):
                try:
                    server = API.listen(api[0], host, 0) if API is not None else None
                    refused = server is None
                    if server is not None:
                        server.server_close()
                except Exception as exc:  # noqa: BLE001 - the refusal is the named Refused
                    refused = getattr(exc, 'code', None) == 'invalid_input:listen'
                check(TL, 'the API refuses to listen on %s' % host, refused and API is not None)
            server = API.listen(api[0], '127.0.0.1', 0) if API is not None else None
            if server is not None:
                _v130_threading.Thread(target=server.serve_forever, daemon=True).start()
                port = server.server_address[1]

                def http(method, path, body=b'', headers=None):
                    connection = _v130_client.HTTPConnection('127.0.0.1', port, timeout=10)
                    try:
                        connection.request(method, path, body=body, headers=headers or {})
                        response = connection.getresponse()
                        return response.status, dict(response.getheaders()), response.read()
                    finally:
                        connection.close()

                wire = http('POST', '/api/v1/auth/challenge', b'{}', {'Host': _V130_HOST, 'Origin': _V130_ORIGIN,
                                                                      'Content-Type': 'application/json'})
                check(TL, 'over real loopback HTTP a challenge is served with Strict-Transport-Security and no-store',
                      wire[0] == 200 and wire[1].get('Strict-Transport-Security', '').startswith('max-age=')
                      and wire[1].get('Cache-Control') == 'no-store' and b'challenge' in wire[2]
                      and server.server_address[0] == '127.0.0.1')
                other = http('GET', '/api/v1/auth/session', headers={'Host': 'evil.example'})
                unauthenticated = http('GET', '/api/v1/auth/session', headers={'Host': _V130_HOST})
                huge = http('POST', '/api/v1/auth/challenge', b'x' * (65 * 1024),
                            {'Host': _V130_HOST, 'Origin': _V130_ORIGIN, 'Content-Type': 'application/json'})
                check(TL, 'another Host is refused, a missing session is unauthenticated and a body over 64 KiB is too '
                          'large, each with Strict-Transport-Security [observed %s %s %s]' % (other[0], unauthenticated[0], huge[0]),
                      other[0] == 400 and unauthenticated[0] == 401 and huge[0] == 413
                      and all(r[1].get('Strict-Transport-Security') for r in (other, unauthenticated, huge)))
                server.shutdown()
                server.server_close()
            else:
                check(TL, 'the API listens on loopback', False)
    finally:
        bot_server.shutdown()
        bot_server.server_close()
        conn.close()
    return rows


_v130_started = _v130_time.monotonic()
# The store and keys live in memory-backed /dev/shm when it exists and is writable (Linux), as the other
# store suites do; elsewhere the platform's temporary directory is used.
_v130_fast = '/dev/shm' if _v130_os.path.isdir('/dev/shm') and _v130_os.access('/dev/shm', _v130_os.W_OK) else None
with _v130_temp.TemporaryDirectory(prefix='v130-', dir=_v130_fast) as _v130_dir:
    _v130_rows = _v130_checks(_v130_Path(_v130_dir))
for _v130_name, _v130_observed in _v130_rows.items():
    _v130_ok = bool(_v130_observed) and all(ok for _, ok in _v130_observed)
    if not _v130_ok:
        for _v130_label, _v130_one in _v130_observed:
            if not _v130_one:
                print('  VELDO-0130 %s detail: %s' % (_v130_name, _v130_label))
    expect('VELDO-0130 ' + _v130_name, _v130_ok)
print('VELDO-0130 suite seconds: %.3f' % (_v130_time.monotonic() - _v130_started))
