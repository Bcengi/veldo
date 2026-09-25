#!/usr/bin/env python3
"""The protected signer's one purpose for an enrolled channel edge: answer assertions (VELDO-0067 AC2, R38).

WHAT THIS MODULE IS. The part of the VELDO-0027 protected signer that serves an edge enrolled by
control_channel_enrollment. control_signer hands it every request whose authenticated identity is an
enrolled channel edge key, whatever the request asks, so the edge is judged by its purpose alone. The
edge authenticates with the connection key its enrollment recorded (a fresh challenge signed over the
request digest, exactly as a VELDO-0027 connection does). It may then ask for one thing: a signature
over the canonical bytes of one answer assertion the VELDO-0065 presenter builds and VELDO-0066 attributes.
Everything else, arbitrary bytes, a membership or other administrative command, an assertion with any
field more or less than the canonical answer, a request naming a key path, refuses by name and signs
nothing.

WHAT THE SIGNER CHECKS, INDEPENDENTLY OF THE EDGE. In the authority's own committed state, under the
signer's store lock: the edge key is current (effective, not retired or revoked) and the edge a current
service member, and the authority's published allowed_signers file is the accepted projection; the
request's and the assertion's channel and edge identity are the enrollment's; the assertion names this
authority; the canonical evidence VELDO-0066 keeps binds it: the evidence record exists, verifies
against the update it retains, is not yet decided, is a person's own new message in their own private
chat, and the assertion's attribution is exactly that evidence's fields and identity; the actor is the
one principal whose VELDO-0064 enrollment is that sender's chat, a current person member; the
presentation the assertion names is a published VELDO-0065 receipt of the assertion's request and
version, with its digest and version, that the evidence replies to as published, shown to that actor,
and the assertion's scope is that request's; the request is still at the version the assertion answers
and that presentation is still the request's current one (a revised request or a replaced presentation
refuses by name: request-mismatch, presentation-mismatch); and the delegation the request names is
current (its version is the store's, not superseded, not revoked) and binds that principal, channel,
edge key and assertion kind, covers the scope and has not expired. The membership organ's delegated-use
predicate then judges the same delegation conjunctively. Only then is the answer signed, with the edge
key from the key directory the signer's fixed configuration names.

A STANDING DELEGATION (VELDO-0140). The owner's delegation to the edge names no request or presentation
version (control_membership.standing): one delegation signs his answer to whatever request version and
presentation is current, because the binding to the exact request, presentation and evidence is judged
above, per assertion, against the committed state. A pinned VELDO-0067 delegation (both versions
integers) still covers exactly its versions. The owner renews it before it expires by superseding it
with his own signed command (veldo channel delegate, applied by the running service); `standing_status`
names what the service tells him when it is missing, expired or about to expire.

THE SIGNATURE. The signature is over `control_store.canonical_bytes(assertion)` in the authority
contract's command namespace, because that is exactly what the VELDO-0065 answer acceptance verifies
with the edge's enrolled key. It cannot stand for a command: the signer signs only a value with the
canonical answer's exact fields, and no command or envelope has them.

THE API EDGE (VELDO-0130). An enrolled edge of channel "api" is handed, whole, to control_api_signer,
whose one purpose is the typed API assertion; it never reaches the answer purpose below, and a Telegram
edge never reaches that one.

WHAT IT IS NOT. Not acceptance (the presenter rechecks the edge and the actor at acceptance), not
settlement (VELDO-0068), not ingress activation (VELDO-0073). Diagnostics carry identities, versions and
the named refusal, never the assertion's text, a key, a path or a signature. Standard library only.
"""
import importlib.util
import json
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('signer_answers_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E = organ('control_channel_enrollment')
K, CM, AC = E.K, E.CM, E.AC
S = organ('control_store')
V = organ('control_channel_presentation')
EV = organ('control_channel_attribution')
P = organ('control_channel_projection')
OPERATION = 'sign_answer'
# The request an answer names is an inbox assignment (control_assignment.ENTITY_KIND).
REQUEST_KIND = 'assignment'
# The owner is told to renew his standing delegation this long before it expires (VELDO-0140).
RENEW_NOTICE_SECONDS = 7 * 86400
REQUEST_FIELDS = ('operation', 'channel', 'edge_key_id', 'delegation_id', 'delegation_version', 'assertion')
IDS = ('domain_uuid', 'repository_uuid', 'store_uuid')
# The canonical Telegram answer: VELDO-0065's canonical_answer, with VELDO-0066's attributed principal
# and evidence identity. Exactly these fields; a value with any other field is not an answer.
ANSWER_FIELDS = IDS + ('schema', 'channel', 'assertion_kind', 'authority_scope', 'edge_principal', 'edge_key_id',
                       'principal', 'request_id', 'request_version', 'presentation_id', 'presentation_digest',
                       'presentation_version', 'choice', 'ruling', 'rationale', 'attribution')
ATTRIBUTION_FIELDS = ('platform_message_id', 'sender_id', 'platform_timestamp', 'chat_id', 'reply_to_message_id',
                      'update_id', 'evidence_id', 'evidence_digest', 'bot_id', 'chat_type', 'sender_type')
REFUSALS = {'unauthenticated-channel': 'missing_authority', 'key-path': 'invalid_input',
            'forbidden-purpose': 'invalid_input', 'revoked-key': 'missing_authority',
            'edge-not-current': 'missing_authority', 'projection-mismatch': 'unavailable_service',
            'channel-mismatch': 'missing_authority', 'edge-mismatch': 'missing_authority',
            'wrong-authority': 'invalid_input', 'missing-evidence': 'missing_evidence',
            'actor-mismatch': 'missing_authority', 'actor-not-current': 'missing_authority',
            'request-mismatch': 'stale_subject', 'presentation-mismatch': 'stale_subject',
            'scope-refused': 'missing_authority', 'stale-delegation': 'stale_subject',
            'delegation-refused': 'missing_authority', 'delegation-expired': 'missing_authority',
            'key-custody': 'unavailable_service', 'signing-unavailable': 'unavailable_service'}
# What an unauthenticated caller learns: the VELDO-0027 answer, field for field, and nothing stored.
UNAUTHENTICATED = {'accepted': False, 'refusal': 'unauthenticated-channel',
                   'diagnostic': {'key_id': None, 'principal': None, 'assertion_kind': None,
                                  'delegation_revision': None, 'refusal': 'unauthenticated-channel'},
                   'metrics': {'unauthenticated-channel': 1}}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def edge_entry(state, identity):
    """The enrolled channel edge key an authenticated identity names, or None: only the key id the
    authority contract gives an enrollable channel, recorded by control_channel_enrollment."""
    record = E.edge_record(state, identity)
    if record is None or record.get('channel') not in E.ENROLLABLE or identity != E.edge_key_id(record['channel']):
        return None
    return record


def shape_problems(a):
    """Why a value is not one canonical answer assertion, by name; [] when it is."""
    if not isinstance(a, dict) or set(a) != set(ANSWER_FIELDS):
        return ['an answer assertion has exactly the canonical answer fields']
    problems = []
    if a['schema'] != V.ANSWER_SCHEMA or a['assertion_kind'] not in AC.ASSERTION_KINDS:
        problems.append('the assertion is a %s of a contract assertion kind' % V.ANSWER_SCHEMA)
    if not isinstance(a['attribution'], dict):
        problems.append('the attribution is a mapping')
    if not all(_text(a[f]) for f in IDS + ('channel', 'edge_principal', 'edge_key_id', 'principal', 'request_id',
                                           'presentation_id', 'presentation_digest')):
        problems.append('identities are named')
    if type(a['request_version']) is not int or type(a['presentation_version']) is not int:
        problems.append('versions are integers')
    if not (isinstance(a['authority_scope'], list) and a['authority_scope'] and all(_text(s) for s in a['authority_scope'])):
        problems.append('the scope is a non-empty list of named scopes')
    if not all(v is None or isinstance(v, str) for v in (a['choice'], a['ruling'], a['rationale'])):
        problems.append('the choice, ruling and rationale are text')
    return problems


def _enrollments(state):
    """{principal: chat} of every valid VELDO-0064 Telegram enrollment, each at its principal's own id."""
    found = {}
    for eid, entity in state['entities'].items():
        data = entity.get('data') if isinstance(entity.get('data'), dict) else {}
        principal = data.get('principal')
        if (entity.get('kind') == P.ENROLLMENT_KIND and isinstance(principal, str) and eid == P.enrollment_id(principal)
                and not P.enrollment_problems(entity['kind'], data, principal)):
            found[principal] = data['chat_id']
    return found


def _evidence(state, attribution):
    """The canonical evidence record the attribution names, bound to it, or a refusal."""
    if not isinstance(attribution, dict) or set(attribution) != set(ATTRIBUTION_FIELDS):
        raise Refused('missing-evidence', 'the attribution names its canonical evidence and nothing else')
    eid = attribution['evidence_id']
    entity = state['entities'].get(eid) if isinstance(eid, str) else None
    record = (entity or {}).get('data')
    if not entity or entity.get('kind') != EV.EVIDENCE_KIND or EV.evidence_problems(record):
        raise Refused('missing-evidence', 'no canonical evidence record binds the update it retains')
    if record.get('outcome') != 'acquired':
        raise Refused('missing-evidence', 'the evidence is already decided')
    f = record['fields']
    message = (record.get('source') or {}).get('message') if isinstance(record.get('source'), dict) else None
    if (f['update_kind'] != 'message' or not isinstance(message, dict) or EV.missing_fields(f)
            or EV.automation_reason(message) or EV.is_forward(message)
            or f['chat_type'] != 'private' or f['chat_id'] != f['sender_id']):
        raise Refused('missing-evidence', 'the evidence is not a person\'s own new message in their private chat')
    wanted = {'platform_message_id': f['message_id'], 'sender_id': f['sender_id'], 'platform_timestamp': f['date'],
              'chat_id': f['chat_id'], 'reply_to_message_id': f['reply_to_message_id'], 'update_id': f['update_id'],
              'evidence_id': record['evidence_id'], 'evidence_digest': record['source_digest'],
              'bot_id': record['bot_id'], 'chat_type': f['chat_type'], 'sender_type': 'person'}
    if attribution != wanted:
        raise Refused('missing-evidence', 'the attribution is not the evidence\'s own fields and identity')
    return record, entity.get('version'), message


def _judge(state, config, request, identity, entry, now, diagnostic):
    """Every check after the purpose, in the committed state; returns nothing or raises Refused."""
    a = request['assertion']
    diagnostic.update(principal=a['principal'], request_id=a['request_id'], presentation_id=a['presentation_id'],
                      evidence_id=a['attribution'].get('evidence_id'), delegation_id=request.get('delegation_id'))
    versions = diagnostic['accepted_versions']
    versions.update(membership_version=state['membership_version'], delegation_version=state['delegation_version'])
    # The edge is current: its key signs now, and it is a current service member.
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
    # Channel and edge identity are the enrollment's, which the connection authenticated.
    if request.get('channel') != entry['channel'] or a['channel'] != entry['channel']:
        raise Refused('channel-mismatch', 'the edge signs for its own channel only')
    if request.get('edge_key_id') != identity or a['edge_key_id'] != identity or a['edge_principal'] != entry['principal']:
        raise Refused('edge-mismatch', 'the assertion names another edge')
    ids = config.get('authority_ids') if isinstance(config.get('authority_ids'), dict) else {}
    if any(not _text(ids.get(f)) or a[f] != ids[f] for f in IDS):
        raise Refused('wrong-authority', 'the assertion names another authority')
    # Canonical evidence, then the actor it establishes.
    record, evidence_version, message = _evidence(state, a['attribution'])
    versions[record['evidence_id']] = evidence_version
    f = record['fields']
    senders = sorted(p for p, chat in _enrollments(state).items() if chat == f['sender_id'])
    if senders != [a['principal']]:
        raise Refused('actor-mismatch', 'the actor is the one principal enrolled on the sender\'s chat')
    person = AC.membership_entry(state['membership'], a['principal'])
    if not AC.active_member(person, now)[0] or person.get('principal_type') != 'person':
        raise Refused('actor-not-current', 'the actor is not a current person member')
    # The presentation and request the evidence answers.
    shown = state['entities'].get(a['presentation_id'])
    receipt = (shown or {}).get('data')
    if (not shown or shown.get('kind') != V.RECEIPT_KIND or receipt.get('outcome') != 'published'
            or V.receipt_problems(receipt, retrieved=False)):
        raise Refused('presentation-mismatch', 'the assertion names no published presentation receipt')
    versions[a['presentation_id']] = shown.get('version')
    if (receipt['request_id'], receipt['request_version']) != (a['request_id'], a['request_version']):
        raise Refused('request-mismatch', 'the presentation is of another request or version')
    if (receipt['brief_digest'] != a['presentation_digest'] or receipt['presentation_version'] != a['presentation_version']
            or receipt['channel'] != a['channel']):
        raise Refused('presentation-mismatch', 'the assertion does not name the presentation as published')
    asked = state['entities'].get(a['request_id']) or {}
    versions[a['request_id']] = asked.get('version')
    if asked.get('kind') != REQUEST_KIND or (asked.get('data') or {}).get('request_version') != a['request_version']:
        raise Refused('request-mismatch', 'the request is no longer at the version the assertion answers')
    head = state['entities'].get(V.head_id(a['request_id'])) or {}
    if head.get('kind') != V.HEAD_KIND or (head.get('data') or {}).get('current') != a['presentation_id']:
        raise Refused('presentation-mismatch', 'the presentation is no longer the request\'s current one')
    if (f['chat_id'] != receipt['chat_id'] or f['reply_chat_id'] != receipt['chat_id']
            or f['reply_to_message_id'] not in (receipt.get('message_ids') or [])
            or EV.replied_problems(receipt, message.get('reply_to_message') or {}, record['bot_id'])):
        raise Refused('presentation-mismatch', 'the evidence does not reply to the named presentation as published')
    if receipt['owner'] != a['principal']:
        raise Refused('actor-mismatch', 'the presentation was shown to another principal')
    if a['authority_scope'] != list((receipt.get('request') or {}).get('scope') or []):
        raise Refused('scope-refused', 'the assertion\'s scope is not its request\'s')
    if not CM.scope_covers(member.get('scope'), a['authority_scope']):
        raise Refused('scope-refused', 'the edge\'s scope does not cover the request')
    # The delegation the request names, every dimension.
    if request.get('delegation_version') != state['delegation_version']:
        raise Refused('stale-delegation', 'the request names a delegation version that is not current')
    d = next((x for x in state['delegations'] if x.get('id') == request.get('delegation_id')), None)
    if d is None:
        raise Refused('delegation-refused', 'the request names no delegation')
    versions[d['id']] = d.get('entity_version')
    if d.get('superseded_by') is not None:
        raise Refused('stale-delegation', 'the delegation is superseded')
    if d.get('revoked_at') is not None and d['revoked_at'] <= now:
        raise Refused('delegation-refused', 'the delegation is revoked')
    if d.get('principal') != a['principal']:
        raise Refused('actor-mismatch', 'the delegation is another principal\'s')
    if d.get('channel') != a['channel']:
        raise Refused('channel-mismatch', 'the delegation is for another channel')
    if d.get('edge_key_id') != identity:
        raise Refused('edge-mismatch', 'the delegation binds another edge key')
    if a['assertion_kind'] not in (d.get('assertion_kinds') or []):
        raise Refused('forbidden-purpose', 'the delegation does not permit this assertion kind')
    if not CM.standing(d) and d.get('request_version') != a['request_version']:
        raise Refused('request-mismatch', 'the delegation binds another request version')
    if not CM.standing(d) and d.get('presentation_version') != a['presentation_version']:
        raise Refused('presentation-mismatch', 'the delegation binds another presentation version')
    if not CM.scope_covers(d.get('authority_scope'), a['authority_scope']):
        raise Refused('scope-refused', 'the delegation does not cover the scope')
    if not _number(d.get('expires_at')) or d['expires_at'] <= now:
        raise Refused('delegation-expired', 'the delegation has expired')
    envelope = {'principal': a['principal'], 'delegation_id': d['id'], 'delegation_version': request['delegation_version']}
    requirement = {'scope': None, 'boundary': 'decision_settlement', 'subject_digest': a['presentation_digest']}
    if CM.delegated_use_problems(state, envelope, a, requirement, now):
        raise Refused('delegation-refused', 'the delegated-use predicate refuses')


def issue(state, config, request, challenge, identity, authentication, now, canonical, digest, sign_bytes, auth_namespace):
    """Authenticate an enrolled edge, judge its request and sign only a canonical answer. `state` is the
    committed authority state read under control_signer's store lock; `canonical`, `digest`,
    `sign_bytes` and `auth_namespace` are control_signer's own, so the connection proof and the key
    handling are the VELDO-0027 ones."""
    entry = edge_entry(state, identity)
    if entry['channel'] in E.API_CHANNELS:
        # VELDO-0130: the authenticated API's edge has its own one purpose, typed API assertions.
        return organ('control_api_signer').issue(state, config, request, challenge, identity, authentication, now,
                                                 canonical, digest, sign_bytes, auth_namespace)
    message = canonical({'challenge': challenge, 'request_digest': digest(request)})
    ok, _ = AC.ssh_keygen_verify(message, authentication if isinstance(authentication, str) else '',
                                 AC.allowed_signers_line(identity, entry['connection_public_key'], auth_namespace),
                                 identity, auth_namespace)
    if not ok:
        return json.loads(json.dumps(UNAUTHENTICATED))
    diagnostic = {'operation': request.get('operation') if isinstance(request, dict) else None,
                  'channel': entry['channel'], 'edge_key_id': identity, 'principal': None, 'request_id': None,
                  'presentation_id': None, 'evidence_id': None, 'delegation_id': None, 'accepted_versions': {},
                  'outcome': None, 'refusal': None, 'error_class': None}

    def signed(value):
        """The edge key's signature over one value's canonical bytes, from the signer's own custody."""
        path = (Path(config['key_directory']) / identity).resolve()
        if path.is_relative_to(Path(config['repository']).resolve()):
            raise Refused('key-custody', 'the edge key is outside every repository')
        try:
            signature = sign_bytes(path, S.canonical_bytes(value), AC.SIGNATURE_NAMESPACE)
        except Exception:  # noqa: BLE001 - a custody failure signs nothing and is named, never raised past the signer
            raise Refused('signing-unavailable', 'the edge key did not sign') from None
        return {'accepted': True, 'signature': signature, 'diagnostic': dict(diagnostic, outcome='accepted'),
                'metrics': {'accepted': 1}}

    try:
        if not isinstance(request, dict):
            raise Refused('forbidden-purpose', 'a request is a mapping')
        if any(f in request for f in ('key_path', 'private_key', 'path')):
            raise Refused('key-path', 'a request never names key material')
        if request.get('operation') != OPERATION or set(request) - set(REQUEST_FIELDS):
            raise Refused('forbidden-purpose', 'an edge asks only for an answer signature')
        answer = request.get('assertion')
        if shape_problems(answer):
            raise Refused('forbidden-purpose', 'the value is not one canonical answer assertion')
        _judge(state, config, request, identity, entry, now, diagnostic)
        return signed(answer)
    except Refused as exc:
        return {'accepted': False, 'refusal': exc.code,
                'diagnostic': dict(diagnostic, outcome='refused', refusal=exc.code, error_class=REFUSALS.get(exc.code)),
                'metrics': {exc.code: 1}}


def delegation_for(state, assertion, identity, now):
    """The id of the one current delegation of the assertion's principal for its channel, this edge key,
    its kind and scope, standing or pinned to the assertion's request and presentation version, or None
    (the signer then refuses)."""
    a = assertion if isinstance(assertion, dict) else {}
    found = [d['id'] for d in state['delegations']
             if d.get('principal') == a.get('principal') and d.get('channel') == a.get('channel')
             and d.get('edge_key_id') == identity and d.get('superseded_by') is None and d.get('revoked_at') is None
             and _number(d.get('expires_at')) and d['expires_at'] > now
             and a.get('assertion_kind') in (d.get('assertion_kinds') or [])
             and (CM.standing(d) or (d.get('request_version') == a.get('request_version')
                                     and d.get('presentation_version') == a.get('presentation_version')))
             and CM.scope_covers(d.get('authority_scope'), a.get('authority_scope'))]
    return found[0] if len(found) == 1 else None


def standing_status(state, principal, channel, identity, now, notice=RENEW_NOTICE_SECONDS):
    """What the owner is told about his standing delegation to this edge: {'status', 'delegation_id',
    'expires_at'} with status 'current', 'expiring' (it expires within `notice` seconds), 'expired' or
    'none' (he holds no standing delegation that is neither superseded nor revoked). Read only."""
    held = [d for d in state['delegations']
            if d.get('principal') == principal and d.get('channel') == channel and d.get('edge_key_id') == identity
            and CM.standing(d) and d.get('superseded_by') is None
            and (d.get('revoked_at') is None or d['revoked_at'] > now) and _number(d.get('expires_at'))]
    if not held:
        return {'status': 'none', 'delegation_id': None, 'expires_at': None}
    d = max(held, key=lambda x: (x['expires_at'], x['id']))
    status = ('expired' if d['expires_at'] <= now else 'expiring' if d['expires_at'] - now <= notice else 'current')
    return {'status': status, 'delegation_id': d['id'], 'expires_at': d['expires_at']}


class EdgeSigner:
    """The Telegram edge's `edge_sign(bytes) -> text`, the seam VELDO-0066's Acquirer signs through. Every
    answer it is handed goes to the protected signer as one sign_answer request under the principal's
    current delegation, authenticated with the edge's connection key; the edge never holds the signing
    key. `store` and `membership` are the control_store and control_membership modules on `conn`, read
    only to name the delegation. A refusal raises; `results` keeps each outcome without the signature."""

    def __init__(self, store, membership, conn, config_path, identity, connection_key, clock=time.time):
        self.store, self.membership, self.conn = store, membership, conn
        self.config_path, self.identity, self.connection_key, self.clock = config_path, identity, connection_key, clock
        self.results = []
        self._signer = None

    def request(self, assertion):
        state = self.membership.authority_state(self.store, self.conn)
        return {'operation': OPERATION, 'channel': assertion.get('channel'), 'edge_key_id': self.identity,
                'delegation_id': delegation_for(state, assertion, self.identity, self.clock()),
                'delegation_version': state['delegation_version'], 'assertion': assertion}

    def __call__(self, message):
        assertion = json.loads(message)
        if not isinstance(assertion, dict) or self.store.canonical_bytes(assertion) != message:
            raise Refused('forbidden-purpose', 'the edge signs the canonical bytes of one answer')
        if self._signer is None:
            self._signer = organ('control_signer')
        result = self._signer.call(self.config_path, self.request(assertion), self.identity, self.connection_key)
        self.results.append({k: result.get(k) for k in ('accepted', 'refusal', 'diagnostic', 'signer_pid')})
        if not result.get('accepted'):
            raise Refused(result.get('refusal') or 'signing-unavailable', 'the protected signer refused')
        return result['signature']
