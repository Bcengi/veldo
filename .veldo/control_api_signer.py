#!/usr/bin/env python3
"""The protected signer's "api" purpose: typed API assertions for a session's member (VELDO-0130).

WHAT THIS MODULE IS. The part of the VELDO-0027 protected signer that serves the authenticated API's
enrolled edge (channel "api", control_channel_enrollment). control_signer hands every request whose
authenticated identity is an enrolled channel edge key to control_signer_answers, which hands the api
edge's, whole, to `issue` here. The edge authenticates with the connection key its enrollment recorded
(a fresh challenge signed over the request digest, as every VELDO-0027 connection does). It may ask
for one thing: a signature over one API assertion (control_api_assertion) and over the one domain
command that assertion derives. Arbitrary bytes, a command or envelope, an assertion with a field more
or less, a request naming key material: each refuses by name and signs nothing.

WHAT THE SIGNER CHECKS, INDEPENDENTLY OF THE API. In the authority's committed state, under the
signer's store lock: the edge key is current and the edge a current service member, and the published
allowed_signers file is the accepted projection; the request's and the assertion's channel and edge are
the enrollment's; the assertion names this authority; it is live (issued no later than now, expiring
60 seconds after issue and not yet expired); and the principal it names holds the named api_credential,
which is current, and is a current person member. Only then are both values signed, with the edge key
from the key directory the signer's fixed configuration names, in the authority contract's command
namespace, which is exactly what VELDO-0126 intake and VELDO-0068 settlement verify with the edge's key.

`ApiSigner` is the API process's side: it builds the request and calls the signer process; the API
never holds or reads the signing key.

WHAT IT IS NOT. Not the authority's recheck (control_api_authority verifies the signature, the
credential and the member again at execution). Diagnostics carry identities and the named refusal,
never the assertion's text, a key, a path or a signature. Standard library only.
"""
import importlib.util
import json
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('api_signer_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E = organ('control_channel_enrollment')
K, CM, AC = E.K, E.CM, E.AC
S = organ('control_store')
AS = organ('control_api_assertion')
CR = organ('control_api_credentials')
OPERATION = 'sign_api_assertion'
REQUEST_FIELDS = ('operation', 'channel', 'edge_key_id', 'assertion')
REFUSALS = {'unauthenticated-channel': 'unauthenticated', 'key-path': 'invalid_input',
            'forbidden-purpose': 'invalid_input', 'revoked-key': 'unauthorized', 'edge-not-current': 'unauthorized',
            'projection-mismatch': 'unavailable_service', 'channel-mismatch': 'unauthorized',
            'edge-mismatch': 'unauthorized', 'wrong-authority': 'invalid_input', 'assertion-expired': 'stale_version',
            'credential-not-current': 'unauthenticated', 'key-custody': 'unavailable_service',
            'signing-unavailable': 'unavailable_service'}
UNAUTHENTICATED = {'accepted': False, 'refusal': 'unauthenticated-channel',
                   'diagnostic': {'edge_key_id': None, 'principal': None, 'request_id': None,
                                  'refusal': 'unauthenticated-channel'},
                   'metrics': {'unauthenticated-channel': 1}}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def _judge(state, config, request, identity, entry, now, diagnostic):
    a = request['assertion']
    diagnostic.update(principal=a['principal'], request_id=a['request_id'], operation=a['operation'])
    if not E.active(entry, now):
        raise Refused('revoked-key', 'the edge key is retired, revoked or not yet effective')
    member = AC.membership_entry(state['membership'], entry['principal'])
    if not AC.active_member(member, now)[0] or member.get('principal_type') != 'service':
        raise Refused('edge-not-current', 'the edge is not a current service member')
    try:
        body = Path(config['allowed_signers']).read_text()
    except (OSError, KeyError, TypeError):
        body = None
    if body != K.projection(state) or AC.allowed_signers_line(entry['principal'], entry['public_key']) not in body.splitlines():
        raise Refused('projection-mismatch', 'the published key file is not the accepted projection')
    if request.get('channel') != entry['channel'] or a['channel'] != entry['channel']:
        raise Refused('channel-mismatch', 'the edge signs for its own channel only')
    if request.get('edge_key_id') != identity or a['edge_key_id'] != identity or a['edge'] != entry['principal']:
        raise Refused('edge-mismatch', 'the assertion names another edge')
    ids = config.get('authority_ids') if isinstance(config.get('authority_ids'), dict) else {}
    if any(not isinstance(ids.get(f), str) or a[f] != ids[f] for f in AS.IDS):
        raise Refused('wrong-authority', 'the assertion names another authority')
    if AS.time_problem(a, now):
        raise Refused('assertion-expired', 'the assertion is not live')
    _record, why = CR.current(state, a['credential_id'], now, principal=a['principal'])
    if why:
        raise Refused('credential-not-current', why)


def issue(state, config, request, challenge, identity, authentication, now, canonical, digest, sign_bytes, auth_namespace):
    """Authenticate the api edge, judge its request and sign only an API assertion and its derived
    domain command. The arguments are control_signer_answers.issue's, which are control_signer's own."""
    entry = E.edge_record(state, identity)
    message = canonical({'challenge': challenge, 'request_digest': digest(request)})
    ok, _ = AC.ssh_keygen_verify(message, authentication if isinstance(authentication, str) else '',
                                 AC.allowed_signers_line(identity, entry['connection_public_key'], auth_namespace),
                                 identity, auth_namespace)
    if not ok:
        return json.loads(json.dumps(UNAUTHENTICATED))
    diagnostic = {'operation': None, 'channel': entry['channel'], 'edge_key_id': identity, 'principal': None,
                  'request_id': None, 'outcome': None, 'refusal': None, 'error_class': None}

    def signed(value):
        path = (Path(config['key_directory']) / identity).resolve()
        if path.is_relative_to(Path(config['repository']).resolve()):
            raise Refused('key-custody', 'the edge key is outside every repository')
        try:
            return sign_bytes(path, S.canonical_bytes(value), AC.SIGNATURE_NAMESPACE)
        except Exception:  # noqa: BLE001 - a custody failure signs nothing and is named
            raise Refused('signing-unavailable', 'the edge key did not sign') from None

    try:
        if not isinstance(request, dict):
            raise Refused('forbidden-purpose', 'a request is a mapping')
        if any(f in request for f in ('key_path', 'private_key', 'path')):
            raise Refused('key-path', 'a request never names key material')
        if request.get('operation') != OPERATION or set(request) != set(REQUEST_FIELDS):
            raise Refused('forbidden-purpose', 'the api edge asks only for an API assertion signature')
        assertion = request.get('assertion')
        if AS.shape_problems(assertion):
            raise Refused('forbidden-purpose', 'the value is not one API assertion')
        _judge(state, config, request, identity, entry, now, diagnostic)
        derived = AS.domain_request(assertion)
        signature = signed(assertion)
        domain_signature = signed(derived) if derived is not None else None
        return {'accepted': True, 'signature': signature, 'domain_signature': domain_signature,
                'diagnostic': dict(diagnostic, outcome='accepted'), 'metrics': {'accepted': 1}}
    except Refused as exc:
        return {'accepted': False, 'refusal': exc.code,
                'diagnostic': dict(diagnostic, outcome='refused', refusal=exc.code, error_class=REFUSALS.get(exc.code)),
                'metrics': {exc.code: 1}}


class ApiSigner:
    """The API process's signer: every assertion goes to the protected signer as one sign_api_assertion
    request, authenticated with the edge's connection key. Returns (signature, domain signature); a
    refusal raises Refused with the signer's name for it. `results` keeps outcomes without signatures."""

    def __init__(self, config_path, identity, connection_key):
        self.config_path, self.identity, self.connection_key = config_path, identity, connection_key
        self.results = []

    def __call__(self, assertion):
        signer = organ('control_signer')
        request = {'operation': OPERATION, 'channel': AS.CHANNEL, 'edge_key_id': self.identity, 'assertion': assertion}
        try:
            result = signer.call(self.config_path, request, self.identity, self.connection_key)
        except Exception:  # noqa: BLE001 - an unreachable signer is an unavailable service, never a signature
            result = {'accepted': False, 'refusal': 'signing-unavailable'}
        self.results.append({k: result.get(k) for k in ('accepted', 'refusal', 'diagnostic', 'signer_pid')})
        if not result.get('accepted'):
            raise Refused(result.get('refusal') or 'signing-unavailable', 'the protected signer refused')
        return result['signature'], result.get('domain_signature')
