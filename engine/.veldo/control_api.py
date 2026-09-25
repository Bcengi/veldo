#!/usr/bin/env python3
"""The authenticated factory API: passkey sign-in, server-side sessions, messages and decisions (VELDO-0130).

WHAT THIS MODULE IS. An ingress service over existing domain commands, never a second store or
scheduler. It serves plain HTTP with the standard library's ThreadingHTTPServer on a loopback address
only (`listen` refuses any other), behind the TLS terminator on the host (Tailscale Serve, the owner's
choice) that forwards with the Host header preserved. It refuses any Host but the configured name, caps
request bodies at 64 KiB and sends Strict-Transport-Security on every response.

THE ROUTES are one published table, ROUTES: each route's name, method, path, family, whether it needs a
session, its exact body fields and the authority operation it asks for. The handlers are registered by
route name, and `route_problems` compares the two, so a route without a handler or a handler without a
route is a defect the suite names. Phase 1 publishes the auth, messages and decisions families; the read
models, the event stream and the configuration actions extend the same table.

SIGN-IN. The owner signs in with a passkey (WebAuthn Level 2, discoverable, user verification required,
attestation "none"), verified by control_api_webauthn against the credential the authority holds
(control_api_credentials), read through the authority's inspection. A challenge is 32 random bytes,
single use, and expires after 120 seconds. Registration is the first half of enrollment: the
registration ceremony, then at once the possession ceremony whose challenge is the digest of the
registration binding; the result is a pending registration in a 0600 file, 15 minutes, at most three at
a time, showing the key's fingerprint. It grants nothing: only the steward's enroll_api_credential at the
host makes a credential, and no route here can enroll one.

SESSIONS (`Sessions`) live in this process's memory behind one interface (create, find, touch, end, end
by credential, end by principal); a restart ends every session, pending registration and challenge. The
cookie __Host-veldo-session is 32 random bytes, Secure, HttpOnly, SameSite=Strict, Path=/, no Domain, and
only its SHA-256 is kept. Each session has an anti-forgery token of 32 random bytes, returned by sign-in
and the session read, sent as a header on every write and compared with hmac.compare_digest. Every write
also needs Origin equal to the configured origin, Sec-Fetch-Site same-origin when present and
Content-Type application/json; reads change nothing. Idle expiry is 30 minutes after the last
authenticated request, the absolute lifetime 12 hours. Every request checks the session first and then
reads from the authority that its credential is current and its principal a current person member, so a
revocation or a role change applies on the next request; `follow` ends the affected sessions at once
from committed journal records.

THE EDGE. The API is its own principal, the enrolled channel "api" edge. For each accepted write it
builds one control_api_assertion from the session alone, has the protected signer's "api" purpose sign
it (the API never reads the key), and hands it to the authority (control_api_authority), which verifies
it again and executes the existing command. Every route has an exact-field body: a body carrying
principal, actor, actor_id, decider or any unknown field is refused invalid_input, never ignored.

REFUSALS are the error taxonomy: unauthenticated 401 (no session, expired, revoked, a failed assertion),
unauthorized 403 (forgery checks, domain, role or scope), invalid_input 400, stale_version 409,
missing_evidence 404, unavailable_service 503, unknown_outcome 500. Logs name the operation, principal,
credential id, session handle and refusal, never a cookie, token, challenge, key or signature.

WHAT IT IS NOT. Not the read models, live events or configuration actions (phase 2 of VELDO-0130), not
the service socket transport (the phase that wires control_service), not rate limiting or sessions
surviving a restart (Release 2). Standard library only.
"""
import collections
import hashlib
import hmac
import http.server
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('control_api_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


W = organ('control_api_webauthn')
CR = organ('control_api_credentials')
AS = organ('control_api_assertion')
AC = CR.AC

COOKIE = '__Host-veldo-session'
TOKEN_HEADER = 'X-Veldo-Token'
BODY_LIMIT = 64 * 1024
CHALLENGE_SECONDS = 120
PENDING_SECONDS = 15 * 60
PENDING_LIMIT = 3
IDLE_SECONDS = 30 * 60
ABSOLUTE_SECONDS = 12 * 3600
HSTS = 'max-age=31536000'
# Body fields that name who is speaking. The speaker is the session's member; a body naming one is refused.
ACTOR_FIELDS = ('principal', 'actor', 'actor_id', 'decider')
STATUS = {'unauthenticated': 401, 'unauthorized': 403, 'invalid_input': 400, 'stale_version': 409,
          'missing_evidence': 404, 'unavailable_service': 503, 'unknown_outcome': 500}

Route = collections.namedtuple('Route', 'name method path family session required optional operation')
# THE PUBLISHED ROUTE TABLE. `session` False is a sign-in or registration ceremony (it authenticates);
# every other route needs a current session, and every POST is a write with the anti-forgery checks.
ROUTES = (
    Route('auth.challenge', 'POST', '/api/v1/auth/challenge', 'auth', False, (), (), None),
    Route('auth.sign_in', 'POST', '/api/v1/auth/sign-in', 'auth', False,
          ('credential_id', 'client_data_json', 'authenticator_data', 'signature', 'user_handle'), (), None),
    Route('auth.registration_begin', 'POST', '/api/v1/auth/registration/begin', 'auth', False, ('label',), (), None),
    Route('auth.registration_credential', 'POST', '/api/v1/auth/registration/credential', 'auth', False,
          ('registration_id', 'credential_id', 'public_key', 'algorithm', 'client_data_json'), (), None),
    Route('auth.registration_possession', 'POST', '/api/v1/auth/registration/possession', 'auth', False,
          ('registration_id', 'client_data_json', 'authenticator_data', 'signature', 'user_handle'), (), None),
    Route('auth.session', 'GET', '/api/v1/auth/session', 'auth', True, (), (), None),
    Route('auth.sign_out', 'POST', '/api/v1/auth/sign-out', 'auth', True, (), (), None),
    Route('auth.sign_out_everywhere', 'POST', '/api/v1/auth/sign-out-everywhere', 'auth', True, (), (), None),
    Route('auth.revoke_credential', 'POST', '/api/v1/auth/credentials/revoke', 'auth', True, ('credential_id',), (),
          'revoke_credential'),
    Route('messages.send', 'POST', '/api/v1/domains/{domain}/messages', 'messages', True, ('text',),
          ('project', 'clarifies'), 'send_message'),
    Route('decisions.answer', 'POST', '/api/v1/domains/{domain}/decisions/answer', 'decisions', True,
          ('request_id', 'request_version', 'presentation_id', 'presentation_digest', 'presentation_version', 'choice',
           'rationale'), (), 'answer_decision'),
)


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def error_class(code):
    head = str(code).split(':', 1)[0]
    return head if head in STATUS else 'unknown_outcome'


def _pattern(path):
    return re.compile('^' + re.escape(path).replace(re.escape('{domain}'), '(?P<domain>[A-Za-z0-9._-]{1,128})') + '$')


def match(method, path):
    """(route, path parameters) of a request, or (None, {})."""
    for route in ROUTES:
        found = _pattern(route.path).match(path)
        if found and route.method == method:
            return route, found.groupdict()
    return None, {}


def body_problem(route, body):
    """Why a request body is not the route's exact body, or None."""
    if not isinstance(body, dict):
        return 'invalid_input:body'
    if any(f in body for f in ACTOR_FIELDS):
        return 'invalid_input:actor_field'
    if set(body) - set(route.required) - set(route.optional) or set(route.required) - set(body):
        return 'invalid_input:fields'
    return None


class Sessions:
    """Server-side sessions in this process's memory: create, find, touch, end, end by credential and end
    by principal. Only the SHA-256 of a cookie is kept; the handle names a session in logs."""

    def __init__(self, clock=time.time):
        self.clock, self._lock, self._by_hash = clock, threading.Lock(), {}

    @staticmethod
    def _hash(cookie):
        return hashlib.sha256(cookie.encode('ascii', 'replace')).hexdigest()

    def create(self, principal, credential_id):
        cookie, now = W.b64url(secrets.token_bytes(32)), self.clock()
        session = {'handle': secrets.token_hex(8), 'principal': principal, 'credential_id': credential_id,
                   'token': W.b64url(secrets.token_bytes(32)), 'created': now, 'seen': now}
        with self._lock:
            self._by_hash[self._hash(cookie)] = session
        return cookie, dict(session)

    def find(self, cookie):
        """(session, None) for a live session, else (None, the reason); an expired session is ended."""
        if not isinstance(cookie, str) or not cookie:
            return None, 'no_session'
        key, now = self._hash(cookie), self.clock()
        with self._lock:
            session = self._by_hash.get(key)
            if session is None:
                return None, 'no_session'
            if now - session['seen'] > IDLE_SECONDS or now - session['created'] > ABSOLUTE_SECONDS:
                del self._by_hash[key]
                return None, 'session_expired'
            return dict(session), None

    def touch(self, handle):
        with self._lock:
            for session in self._by_hash.values():
                if session['handle'] == handle:
                    session['seen'] = self.clock()

    def _end(self, keep):
        with self._lock:
            gone = [k for k, s in self._by_hash.items() if not keep(s)]
            for k in gone:
                del self._by_hash[k]
        return len(gone)

    def end(self, handle):
        return self._end(lambda s: s['handle'] != handle)

    def end_by_credential(self, credential_id):
        return self._end(lambda s: s['credential_id'] != credential_id)

    def end_by_principal(self, principal):
        return self._end(lambda s: s['principal'] != principal)

    def count(self):
        with self._lock:
            return len(self._by_hash)


class ControlApi:
    """The API of one domain. `config` names origin (https://<name>), rp_id, host (the name the Host
    header must carry), domain, ids (domain_uuid, repository_uuid, store_uuid), edge (the api edge's
    principal) and state_dir (0700). `authority` answers inspect(entity_ids) and apply(packet)
    (control_api_authority.ApiAuthority on the authority's connection); `signer(assertion)` returns
    (signature, domain signature) from the protected signer (control_api_signer.ApiSigner)."""

    def __init__(self, config, authority, signer, clock=time.time, observe=None):
        self.origin, self.rp_id, self.host = config['origin'], config['rp_id'], config['host']
        self.domain, self.edge = config['domain'], config['edge']
        self.ids = {f: config['ids'][f] for f in AS.IDS}
        self.state_dir = Path(config['state_dir'])
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        (self.state_dir / 'pending').mkdir(mode=0o700, exist_ok=True)
        self.authority, self.signer, self.clock = authority, signer, clock
        self.sessions = Sessions(clock)
        self._lock = threading.Lock()
        self._challenges = {}
        self._registrations = {}
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.handlers = {'auth.challenge': self._challenge, 'auth.sign_in': self._sign_in,
                         'auth.registration_begin': self._registration_begin,
                         'auth.registration_credential': self._registration_credential,
                         'auth.registration_possession': self._registration_possession,
                         'auth.session': self._session_read, 'auth.sign_out': self._sign_out,
                         'auth.sign_out_everywhere': self._sign_out_everywhere,
                         'auth.revoke_credential': self._write, 'messages.send': self._write,
                         'decisions.answer': self._write}

    def route_problems(self):
        """Every route without a handler and every handler without a route, by name; [] when they agree."""
        names = [r.name for r in ROUTES]
        return (['route without a handler: ' + n for n in names if n not in self.handlers]
                + ['handler without a route: ' + n for n in self.handlers if n not in names]
                + ['route named twice: ' + n for n in set(names) if names.count(n) > 1])

    # the request

    def handle(self, method, path, headers, raw):
        """(status, response headers, JSON body) for one request. `headers` is a case-insensitive
        mapping (http.client's Message or a dict with canonical names); `raw` the body bytes."""
        extra, about = [], {'route': None, 'principal': None, 'credential_id': None, 'session': None}
        try:
            status, value = self._handle(method, path, headers, raw, extra, about)
        except Refused as exc:
            status, value = STATUS[error_class(exc.code)], {'refusal': exc.code, 'error': error_class(exc.code)}
        event = dict(about, outcome='accepted' if status < 400 else 'refused',
                     refusal=value.get('refusal') if status >= 400 else None, status=status)
        self.observations.append(event)
        self.observe(event)
        out = [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'),
               ('Strict-Transport-Security', HSTS), ('X-Content-Type-Options', 'nosniff')] + extra
        return status, out, value

    def _handle(self, method, path, headers, raw, extra, about):
        if (headers.get('Host') or '') != self.host:
            raise Refused('invalid_input:host', 'the request names another host')
        route, params = match(method, path.split('?', 1)[0])
        if route is None:
            raise Refused('missing_evidence:route', 'no such route')
        about['route'] = route.name
        write = method == 'POST'
        if write:
            if (headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                raise Refused('unauthorized:content_type', 'a write is application/json')
            if headers.get('Origin') != self.origin:
                raise Refused('unauthorized:origin', 'a write comes from the configured origin')
            if headers.get('Sec-Fetch-Site') not in (None, 'same-origin'):
                raise Refused('unauthorized:fetch_site', 'a write is same-origin')
        session = None
        if route.session:
            session = self._current_session(headers, about)
            if write and not hmac.compare_digest(str(headers.get(TOKEN_HEADER) or '').encode(), session['token'].encode()):
                raise Refused('unauthorized:token', 'the anti-forgery token does not match')
        if 'domain' in params and params['domain'] != self.domain:
            raise Refused('unauthorized:domain', 'this API serves another domain')
        body = {}
        if write:
            if len(raw) > BODY_LIMIT:
                raise Refused('invalid_input:body_too_large', 'at most 64 KiB')
            try:
                body = json.loads(raw.decode('utf-8')) if raw else {}
            except (UnicodeDecodeError, ValueError):
                raise Refused('invalid_input:body', 'the body is JSON') from None
            problem = body_problem(route, body)
            if problem:
                raise Refused(problem, 'the body carries exactly the route\'s fields')
        if session is not None:
            self.sessions.touch(session['handle'])
        return self.handlers[route.name](route, body, session, extra)

    def _cookie(self, headers):
        for part in str(headers.get('Cookie') or '').split(';'):
            name, _, value = part.strip().partition('=')
            if name == COOKIE:
                return value
        return None

    def _current_session(self, headers, about):
        session, why = self.sessions.find(self._cookie(headers))
        if session is None:
            raise Refused('unauthenticated:' + why, 'sign in with a passkey')
        about.update(principal=session['principal'], credential_id=session['credential_id'], session=session['handle'])
        why = self._credential_problem(session['credential_id'], session['principal'])[1]
        if why:
            self.sessions.end_by_credential(session['credential_id'])
            raise Refused('unauthenticated:' + why, 'the credential or membership is no longer current')
        return session

    def _credential_problem(self, credential_id, principal=None):
        """(record, reason) from the authority's inspection: the credential, then its principal."""
        seen = self.authority.inspect([CR.entity_id(credential_id)]).get('entities') or {}
        found = CR.record(seen, credential_id)
        if found is None:
            return None, 'unknown_credential'
        member = self.authority.inspect([found['principal']]).get('entities') or {}
        state = {'entities': seen, 'membership': [dict(e['data'], principal=eid) for eid, e in member.items()
                                                  if e.get('kind') == 'membership']}
        return CR.current(state, credential_id, time.time(), principal=principal)

    # sign-in

    def _challenge(self, route, body, session, extra):
        challenge, now = W.b64url(secrets.token_bytes(32)), self.clock()
        with self._lock:
            self._challenges = {c: t for c, t in self._challenges.items() if now - t <= CHALLENGE_SECONDS}
            self._challenges[challenge] = now
        return 200, {'challenge': challenge, 'rp_id': self.rp_id, 'timeout_ms': CHALLENGE_SECONDS * 1000,
                     'user_verification': 'required'}

    def _take_challenge(self, client_data_json):
        """The challenge a ceremony's client data names, consumed: single use, 120 seconds; else None."""
        raw = W.unb64url(client_data_json)
        try:
            named = json.loads(raw.decode('utf-8')).get('challenge') if raw else None
        except (UnicodeDecodeError, ValueError, AttributeError):
            named = None
        with self._lock:
            issued = self._challenges.pop(named, None) if isinstance(named, str) else None
        return named if issued is not None and self.clock() - issued <= CHALLENGE_SECONDS else None

    def _sign_in(self, route, body, session, extra):
        challenge = self._take_challenge(body['client_data_json'])
        if challenge is None:
            raise Refused('unauthenticated:challenge', 'no unused challenge of this API')
        found, why = self._credential_problem(body['credential_id'])
        if found is None or why:
            raise Refused('unauthenticated:' + (why or 'unknown_credential'), 'no current credential')
        if found.get('rp_id') != self.rp_id or found.get('origin') != self.origin:
            raise Refused('unauthenticated:relying_party', 'the credential is another relying party\'s')
        problems = W.assertion_problems(found, body, challenge, self.origin, self.rp_id, self.state_dir)
        if problems:
            raise Refused('unauthenticated:' + problems[0], 'the assertion does not verify')
        cookie, made = self.sessions.create(found['principal'], found['credential_id'])
        extra.append(('Set-Cookie', '%s=%s; Secure; HttpOnly; SameSite=Strict; Path=/' % (COOKIE, cookie)))
        return 200, self._session_view(made)

    def _session_view(self, session):
        return {'principal': session['principal'], 'credential_id': session['credential_id'],
                'csrf_token': session['token'], 'idle_expires_at': session['seen'] + IDLE_SECONDS,
                'expires_at': session['created'] + ABSOLUTE_SECONDS}

    def _session_read(self, route, body, session, extra):
        return 200, self._session_view(dict(session, seen=self.clock()))

    def _sign_out(self, route, body, session, extra):
        self.sessions.end(session['handle'])
        extra.append(('Set-Cookie', '%s=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' % COOKIE))
        return 200, {'outcome': 'signed_out'}

    def _sign_out_everywhere(self, route, body, session, extra):
        ended = self.sessions.end_by_principal(session['principal'])
        extra.append(('Set-Cookie', '%s=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' % COOKIE))
        return 200, {'outcome': 'signed_out', 'sessions_ended': ended}

    # registration, the first half of enrollment

    def _pending_files(self):
        now, live = time.time(), []
        for path in sorted((self.state_dir / 'pending').glob('*.json')):
            try:
                expires = json.loads(path.read_text())['binding']['expires_at']
            except (OSError, ValueError, KeyError, TypeError):
                expires = 0
            if expires <= now:
                path.unlink(missing_ok=True)
            else:
                live.append(path)
        return live

    def _registration_begin(self, route, body, session, extra):
        label = body['label']
        if not isinstance(label, str) or not label.strip() or len(label) > CR.LABEL_LIMIT or not label.isprintable():
            raise Refused('invalid_input:label', 'a label is printable text of at most %d characters' % CR.LABEL_LIMIT)
        now = time.time()
        with self._lock:
            self._registrations = {k: r for k, r in self._registrations.items() if r['expires_at'] > now}
            if len(self._registrations) + len(self._pending_files()) >= PENDING_LIMIT:
                raise Refused('unavailable_service:pending_limit', 'at most three pending registrations')
            rid, challenge = secrets.token_hex(16), W.b64url(secrets.token_bytes(32))
            self._registrations[rid] = {'label': label, 'challenge': challenge, 'user_handle': W.new_user_handle(),
                                        'expires_at': now + PENDING_SECONDS, 'binding': None}
            made = dict(self._registrations[rid])
        return 200, {'registration_id': rid, 'challenge': challenge, 'user_handle': made['user_handle'],
                     'rp_id': self.rp_id, 'algorithms': list(W.ALGORITHMS), 'user_verification': 'required',
                     'resident_key': 'required', 'attestation': 'none'}

    def _registration(self, rid):
        with self._lock:
            found = self._registrations.get(rid) if isinstance(rid, str) else None
        if found is None or found['expires_at'] <= time.time():
            raise Refused('unauthenticated:registration', 'no such pending registration')
        return found

    def _registration_credential(self, route, body, session, extra):
        found = self._registration(body['registration_id'])
        problems = W.registration_problems(body['client_data_json'], found['challenge'], self.origin,
                                           body['credential_id'], body['public_key'], body['algorithm'])
        if problems:
            raise Refused('unauthenticated:' + problems[0], 'the registration ceremony does not verify')
        binding = {'schema': W.BINDING_SCHEMA, 'rp_id': self.rp_id, 'origin': self.origin,
                   'credential_id': body['credential_id'], 'public_key': body['public_key'],
                   'algorithm': body['algorithm'], 'label': found['label'], 'user_handle': found['user_handle'],
                   'nonce': secrets.token_hex(16), 'expires_at': found['expires_at']}
        with self._lock:
            found['binding'] = binding
        return 200, {'possession_challenge': W.binding_challenge(binding), 'user_handle': found['user_handle']}

    def _registration_possession(self, route, body, session, extra):
        found = self._registration(body['registration_id'])
        binding = found.get('binding')
        if binding is None:
            raise Refused('unauthenticated:registration', 'the registration ceremony comes first')
        proof = {k: body[k] for k in CR.PROOF_FIELDS}
        problems = W.possession_problems(binding, proof, self.origin, self.rp_id, self.state_dir)
        if problems:
            raise Refused('unauthenticated:' + problems[0], 'the possession ceremony does not verify')
        path = self.state_dir / 'pending' / (body['registration_id'] + '.json')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(json.dumps({'binding': binding, 'proof': proof}, sort_keys=True))
        with self._lock:
            self._registrations.pop(body['registration_id'], None)
        shown = CR.describe({'binding': binding})
        return 200, dict(shown, pending_id=body['registration_id'], outcome='pending_steward_enrollment')

    # writes through the edge

    def _write(self, route, body, session, extra):
        parameters = {f: body.get(f) for f in route.required + route.optional}
        now = time.time()
        request_id = 'api-' + secrets.token_hex(16)
        expected = ({parameters['request_id']: parameters['request_version'],
                     parameters['presentation_id']: parameters['presentation_version']}
                    if route.operation == 'answer_decision' else {})
        target = {'send_message': self.domain, 'answer_decision': str(parameters.get('request_id')),
                  'revoke_credential': 'api_credential'}[route.operation]
        assertion = dict(self.ids, schema=AS.SCHEMA, domain=self.domain, channel=AS.CHANNEL, edge=self.edge,
                         edge_key_id=AC.edge_channel(AS.CHANNEL)['edge_key_id'], request_id=request_id,
                         principal=session['principal'], credential_id=session['credential_id'],
                         session=session['handle'], operation=route.operation, target=target,
                         parameters=parameters, expected_versions=expected, issued_at=now,
                         expires_at=now + AS.LIFETIME)
        if AS.shape_problems(assertion):
            raise Refused('invalid_input:parameters', '; '.join(AS.shape_problems(assertion)))
        try:
            signature, domain_signature = self.signer(assertion)
        except Exception as error:  # noqa: BLE001 - a signer refusal is named, never a signature
            code = getattr(error, 'code', 'signing-unavailable')
            if code == 'credential-not-current':
                self.sessions.end_by_credential(session['credential_id'])
                raise Refused('unauthenticated:credential_not_current', 'the credential is no longer current') from None
            raise Refused('unavailable_service:signer:' + str(code), 'the protected signer did not sign') from None
        answer = self.authority.apply({'assertion': assertion, 'signature': signature, 'domain_signature': domain_signature})
        if not answer.get('ok'):
            code = str(answer.get('reason'))
            klass = answer.get('taxonomy') or 'unknown_outcome'
            raise Refused((klass if klass in STATUS else 'unknown_outcome') + ':' + code, 'refused by the authority')
        if route.operation == 'revoke_credential':
            self.sessions.end_by_credential(parameters['credential_id'])
        result = answer.get('result') or {}
        keep = ('outcome', 'proposal_id', 'question_id', 'question', 'project', 'repeated', 'request_id', 'answer',
                'settlement', 'ruling')
        return 200, dict({k: result[k] for k in keep if k in result}, api_request_id=request_id)

    # following the journal

    def follow(self, record):
        """End every session a committed journal record ends: an api_credential written revoked, or a
        membership written revoked. Returns how many sessions ended."""
        ended = 0
        for eid, change in ((record or {}).get('transition') or {}).items():
            data = (change or {}).get('data') or {}
            if change.get('kind') == CR.KIND and data.get('revoked_at') is not None:
                ended += self.sessions.end_by_credential(data.get('credential_id'))
            elif change.get('kind') == 'membership' and data.get('revoked_at') is not None:
                ended += self.sessions.end_by_principal(eid)
        return ended


def is_loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def listen(api, host, port):
    """A ThreadingHTTPServer for `api` on a loopback address only; anything else refuses."""
    if not is_loopback(host):
        raise Refused('invalid_input:listen', 'the API listens on a loopback address only')

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def _serve(self, method):
            length = self.headers.get('Content-Length')
            try:
                size = int(length) if length is not None else 0
            except ValueError:
                size = -1
            if size < 0 or size > BODY_LIMIT:
                # The body is never read: the connection closes after the refusal.
                self.close_connection = True
                status, value = 413, {'refusal': 'invalid_input:body_too_large', 'error': 'invalid_input'}
                headers = [('Content-Type', 'application/json'), ('Strict-Transport-Security', HSTS),
                           ('Connection', 'close')]
            else:
                raw = self.rfile.read(size) if size else b''
                status, headers, value = api.handle(method, self.path, self.headers, raw)
            payload = json.dumps(value, sort_keys=True).encode()
            self.send_response(status)
            for name, content in headers:
                self.send_header(name, content)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self._serve('GET')

        def do_POST(self):
            self._serve('POST')

    server = http.server.ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
