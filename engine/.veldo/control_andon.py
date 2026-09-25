"""Andon stops and their authorized resumption through the enrolled channel (VELDO-0075, PLAN-0019 W60, R41).

WHAT THIS MODULE IS. The one service that records an `AWAITING_AUTHORITY` stop of an execution unit,
brings it to the designated authority on Telegram, and resumes the unit only on that authority's
current settlement. It composes what exists and adds no second record of any of it: the VELDO-0064
inbox holds the request, the VELDO-0065 presenter shows it through the VELDO-0073 activated edge,
the VELDO-0066/0067 acquisition and edge signer carry the owner's reply, and the VELDO-0068
settlement service decides it. The stop, the notice correlation and the fresh station contract are
this module's own entity kinds, written only by its registered store command (`andon_transition`).

THE STOP POINTS. STOP_POINTS names every enabled stop point, by the station it interrupts and the
unit states (entity_contract's R13 edges into AWAITING_AUTHORITY) that station holds a unit in:
build (dispatching, running and verifying a build), review (reviewing) and coordination (claimed,
ready to land and landing). Their union is exactly the set of states the lifecycle lets a unit stop
from, and each state belongs to one station.

RAISING NEEDS ONLY AUTHENTICATION. `raise_stop` takes one signed command. The signature is verified
against the signer's active key in the store's committed keyring and the signer must be an active
member of a type the proposal boundary admits (a person, a service or an agent run) whose scope
covers the repository. No role is asked of the requester: a worker that cannot resolve the stop
still records it. The command names the unit, the station, the reason, the resolving authority (the
designated person and the roles the answer requires) and whether an effect of the unit is known to
be unresolved. In ONE store transaction the stop record keeps all of it with the signed command, and
the unit moves to AWAITING_AUTHORITY along its declared edge carrying the interruption. An effect is
unknown when the requester says so OR when a dispatch record of the unit is in the `unknown` state
(control_dispatch: an ambiguous launch holds a stop owed); the requester cannot declare it away.

THE REQUEST. The stop is then asked of its designated authority as an ordinary settlement request:
this service, an enrolled service principal of its own, records the settlement terms (touchpoint
decision_disposition, target the stop by id and digest, required roles the stop's), opens the inbox
assignment addressed to the designated person, frames it with the stop's risk statement and
presents it. A new request version (`revise_stop`: the requester adds to the reason) keeps the
request's status and is framed and presented again.

NOTICES ARE KEYED BY VERSION AND PRESENTATION. `notify` presents the current request version through
the presenter and keeps one `andon_notice` correlation per (request, request version, presentation
id): the chat, the platform's message ids, the presentation digest and version, and the answer path
(reply to that message). A key already kept is suppressed; a new version or a changed presentation is
a new key and is sent. No tracker link is needed or used.

RESUMING NEEDS THE CURRENT SETTLEMENT. `resume` moves the unit back to READY only when the settlement
of the request's CURRENT version exists, is recorded as the assignment's terminal state with its
receipt and typed effect, approves the stop's own target, was answered by the designated person
alone on the presentation that is still the request's current one, and that person is still an
active person member holding the resolving roles over the repository. A notification, a published
presentation, a platform acknowledgement or an answer that did not settle grants nothing. An
unknown-effect stop never resumes on an answer: it stays stopped with its original dispatch and
reservations untouched, whatever was answered (recovery is Release 2). A resumed unit carries a
fresh station contract: a new record naming the station, the next attempt, the unit version it was
issued at and the settlement, receipt and effect that permitted it.

OBSERVABILITY. Every operation is observed with domain, repository, unit, stop, request, accepted
versions, outcome, named refusal and its error class (invalid input, missing authority, stale
subject, unavailable service, missing evidence, unknown outcome; unknown is never success).
metrics() counts accepted and refused operations and lists the stops still pending. No reason text,
signature or key is observed. Not here: recovery, automatic retry, risk disposition of unknown
effects, lost-send and reconnect handling (Release 2). Standard library only.
"""
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import time

SCHEMA = 'veldo.andon_stop/v1'
NOTICE_SCHEMA = 'veldo.andon_notice/v1'
CONTRACT_SCHEMA = 'veldo.andon_station_contract/v1'
STOP_KIND, NOTICE_KIND, CONTRACT_KIND = 'andon_stop', 'andon_notice', 'andon_station_contract'
OPERATION = 'andon_transition'
OWNER = 'VELDO-0075 andon'
WRITES = ('entities', 'journal', 'commands', 'nonces')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
UNIT_KIND, LIFECYCLE = 'execution_unit', 'execution_unit'
STOPPED, RESUMED = 'AWAITING_AUTHORITY', 'READY'
# The settled request's terminal assignment state (control_request_settlement.TERMINAL_STATE).
TERMINAL = 'SATISFIED'
# Every enabled stop point: the station and the unit states it holds a unit in.
STOP_POINTS = {'build': ('DISPATCHING', 'RUNNING', 'VERIFYING'),
               'review': ('REVIEWING',),
               'coordination': ('CLAIMED', 'READY_TO_LAND', 'LANDING')}
EFFECTS = ('clean', 'unknown')
# The dispatch record state that holds a stop owed for an ambiguous launch (control_dispatch).
DISPATCH_KIND, DISPATCH_UNKNOWN = 'dispatch', 'unknown'
# The request each stop is asked as (VELDO-0068 journey touchpoint) and what it offers.
TOUCHPOINT, TARGET_KIND = 'decision_disposition', 'andon_stop'
CHOICES = ('accept', 'return_for_elaboration', 'reject')
RESUME_RULING = 'approve'
RAISE_FIELDS = ('operation', 'principal', 'command_id', 'nonce', 'unit', 'station', 'reason', 'resolving',
                'effect') + COORDINATES
REVISE_FIELDS = ('operation', 'principal', 'command_id', 'nonce', 'stop_id', 'reason') + COORDINATES
DEADLINE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
COMMAND_NAMESPACE = 'veldo-command'
TAXONOMY = {'invalid_input': 'invalid_input', 'not_authorized': 'missing_authority',
            'missing_authority': 'missing_authority', 'stale_subject': 'stale_subject',
            'stale_presentation': 'stale_subject', 'not_stopped': 'stale_subject',
            'missing_evidence': 'missing_evidence', 'no_settlement': 'missing_authority',
            'unavailable_service': 'unavailable_service', 'unknown_outcome': 'unknown_outcome'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def stop_id(repository_uuid, unit, n):
    return 'andon-stop:%s:%s:%d' % (repository_uuid, unit, n)


def request_alias(stop):
    """The inbox alias the stop's request is opened under (the assignment alias grammar)."""
    return 'andon-' + hashlib.sha256(stop.encode()).hexdigest()[:24]


def notice_key(request, request_version, presentation):
    """ONE notice per request, request version and presentation: a new version or a changed
    presentation is a new key, whatever the request's status."""
    return '%s|%d|%s' % (request, request_version, presentation)


def notice_id(key):
    return 'andon-notice:' + hashlib.sha256(key.encode()).hexdigest()


def contract_id(repository_uuid, unit, attempt):
    return 'andon-station-contract:%s:%s:%d' % (repository_uuid, unit, attempt)


def stop_target(stop):
    """The settlement target that names one stop: its id and the digest of what was stopped."""
    core = {k: stop.get(k) for k in ('stop_id', 'unit', 'station', 'interrupted_state', 'raised_by', 'resolving')}
    return {'kind': TARGET_KIND, 'ref': stop['stop_id'], 'digest': digest(core)}


def enabled_states():
    """Every unit state an enabled stop point interrupts, with its station."""
    return {s: station for station, states in STOP_POINTS.items() for s in states}


def service_signer(principal, key):
    """(principal, sign) for this service's own enrolled key: an absolute 0600 file of this account,
    signing commands in the command namespace with no agent consulted."""
    if not _is_str(principal) or not isinstance(key, str) or not os.path.isabs(key):
        raise Refused('invalid_input', 'the andon service names its principal and an absolute key path')
    try:
        info = os.lstat(key)
    except OSError:
        raise Refused('missing_authority', 'the andon service key is absent') from None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Refused('invalid_input', 'the andon service key is this account\'s own 0600 regular file')

    def sign(message):
        done = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', COMMAND_NAMESPACE], input=message,
                              capture_output=True, timeout=10,
                              env={k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')})
        if done.returncode:
            raise Refused('unavailable_service', 'the andon service key did not sign')
        return done.stdout.decode()
    return principal, sign


class Andon:
    """The andon service on the activated ingress's one store connection.

    `ingress` is a control_channel_ingress.Ingress (its inbox, presenter and settlement service share
    the connection); `service` is (principal, sign) for this service's enrolled service key, the
    requester of every stop's request; `scope` is the authority scope the requests are opened in."""

    def __init__(self, ingress, service, *, scope, clock=time.time, deadline_seconds=7 * 86400):
        inbox, presenter, settlement = ingress.inbox, ingress.presenter, ingress.settlement
        if inbox is None or presenter is None or settlement is None or not (
                inbox.conn is ingress.conn and presenter.conn is ingress.conn and settlement.conn is ingress.conn):
            raise Refused('invalid_input', 'the andon has one authority: the ingress store connection')
        if not (isinstance(service, tuple) and len(service) == 2 and _is_str(service[0]) and callable(service[1])):
            raise Refused('invalid_input', 'the andon service is (principal, sign)')
        if not _is_str(scope):
            raise Refused('invalid_input', 'the andon names the scope its requests are opened in')
        self.ingress, self.inbox, self.presenter, self.settlement = ingress, inbox, presenter, settlement
        self.conn = ingress.conn
        self.S, self.CM, self.AC, self.contract = inbox.store, inbox.membership, inbox.AC, inbox.contract
        self.I = settlement.I
        self.ids = dict(inbox.ids)
        self.journal_signer, self.sign = inbox.journal_signer, inbox.sign
        self.authority_generation = inbox.authority_generation
        self.service, self.service_sign = service
        self.scope, self.clock, self.deadline_seconds = scope, clock, deadline_seconds
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._serial = 0
        self.conn.command_registry[OPERATION] = {'transition': self._transition, 'writes': WRITES}
        self.S.declare_owners(self.conn, OWNER, kinds={STOP_KIND: (OPERATION,), NOTICE_KIND: (OPERATION,),
                                                       CONTRACT_KIND: (OPERATION,)}, module=__file__)

    # -- reading ------------------------------------------------------------------------------

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def _of_kind(self, kind):
        return [(r[0], r[1], json.loads(r[2])) for r in
                self.conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (kind,))]

    def stop(self, sid):
        e = self._entity(sid)
        return e['data'] if e is not None and e['kind'] == STOP_KIND else None

    def stops(self):
        return [data for _i, _v, data in self._of_kind(STOP_KIND)]

    def notices(self, sid=None):
        return [data for _i, _v, data in self._of_kind(NOTICE_KIND) if sid is None or data.get('stop_id') == sid]

    def station_contract(self, cid):
        e = self._entity(cid)
        return e['data'] if e is not None and e['kind'] == CONTRACT_KIND else None

    def unknown_dispatches(self, unit):
        """The dispatches of `unit` in this repository whose outcome is unknown (a stop owed)."""
        found = []
        for eid, _v, data in self._of_kind(DISPATCH_KIND):
            contract = data.get('contract') if isinstance(data, dict) else None
            if (isinstance(contract, dict) and contract.get('unit') == unit
                    and contract.get('repository') in (self.ids['repository_uuid'], None)
                    and data.get('state') == DISPATCH_UNKNOWN):
                found.append(eid)
        return found

    def _observe(self, operation, outcome, reason, *, stop=None, unit=None, request=None, versions=None, **extra):
        accepted = reason is None
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.ids, operation=operation, stop_id=stop, unit=unit, request_id=request,
                                      accepted_versions=dict(versions or {}), outcome=outcome, reason=reason,
                                      error_class=None if accepted else taxonomy(reason)))
        result = dict({'outcome': outcome, 'stop_id': stop, 'unit': unit, 'request_id': request}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    def _verified(self, packet, fields, operation):
        """(command, member entry, key, authority state) of a signed command whose signer is an
        active member the proposal boundary admits, scoped over this repository. No role is asked."""
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii()):
            raise Refused('invalid_input', 'an andon command is a signed mapping')
        c = packet['command']
        if (set(c) != set(fields) or c.get('operation') != operation
                or any(c.get(k) != v for k, v in self.ids.items())
                or not all(_is_str(c.get(k)) for k in ('principal', 'command_id', 'nonce'))):
            raise Refused('invalid_input', 'the command carries exactly the %s fields for this authority' % operation)
        now = self.clock()
        state = self.CM.authority_state(self.S, self.conn)
        principal = c['principal']
        entry = self.AC.membership_entry(state['membership'], principal)
        if not self.AC.active_member(entry, now)[0]:
            raise Refused('not_authorized', 'the requester is not an active member')
        if entry.get('principal_type') not in self.AC.BOUNDARIES['proposal_commit']:
            raise Refused('not_authorized', 'the requester is not a person, service or agent run')
        if not (self.CM.scope_covers(entry.get('scope'), self.scope)
                or self.CM.scope_covers(entry.get('scope'), self.ids['repository_uuid'])):
            raise Refused('not_authorized', 'the requester\'s scope does not cover this repository')
        key = self.AC.active_key(state['keyring'], principal, now)
        if key is None or not self.AC.ssh_keygen_verify(self.S.canonical_bytes(c), packet['signature'],
                                                         self.AC.allowed_signers_line(principal, key['public_key']),
                                                         principal)[0]:
            raise Refused('not_authorized', 'the command signature does not verify')
        return c, entry, key, state

    def _commit(self, params, expected, principal, command_id, nonce):
        command = dict(command_id=command_id, principal=principal, operation=OPERATION, parameters=params,
                       expected_versions=expected, artifact_digests=[], nonce=nonce)
        return self.S.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)

    def _pinned(self, state, *principals):
        """The versions of the authority inputs a decision read: each member, its key and the versions entity."""
        seen = state['entities']
        versions = {self.CM.VERSIONS_ENTITY: seen.get(self.CM.VERSIONS_ENTITY, {}).get('version', 0)}
        for p in principals:
            versions[p] = seen.get(p, {}).get('version', 0)
        return versions

    # -- the registered transition --------------------------------------------------------------

    def _transition(self, params, before):
        refused = self.S.StoreRefused
        action = params.get('action')
        if action == 'raise':
            sid, unit = params['stop']['stop_id'], params['unit_id']
            if sid in before:
                raise refused('stale_subject', 'this stop is recorded already')
            u = before.get(unit) or {}
            if u.get('kind') != UNIT_KIND or u['data'].get('state') != params['stop']['interrupted_state']:
                raise refused('stale_subject', 'the unit is no longer where it was stopped')
            ok, why = self.contract.transition(LIFECYCLE, u['data']['state'], STOPPED, {'interruption_recorded': True})
            if not ok:
                raise refused('transition_refused', why)
            data = dict(u['data'], state=STOPPED, interruption=params['interruption'])
            return {sid: {'kind': STOP_KIND, 'data': params['stop']}, unit: {'kind': UNIT_KIND, 'data': data}}
        if action == 'revise':
            sid = params['stop_id']
            s = before.get(sid) or {}
            if s.get('kind') != STOP_KIND or s['data'].get('state') != 'stopped':
                raise refused('stale_subject', 'the stop is not pending')
            return {sid: {'kind': STOP_KIND, 'data': dict(s['data'], reason=params['reason'],
                                                          revisions=list(s['data'].get('revisions') or [])
                                                          + [params['revision']])}}
        if action == 'notice':
            nid = params['notice']['notice_id']
            if nid in before:
                raise refused('stale_subject', 'this notice is kept already')
            return {nid: {'kind': NOTICE_KIND, 'data': params['notice']}}
        if action == 'resume':
            sid, unit, cid = params['stop_id'], params['unit_id'], params['contract']['contract_id']
            s, u = before.get(sid) or {}, before.get(unit) or {}
            if cid in before:
                raise refused('stale_subject', 'this station contract exists already')
            if (s.get('kind') != STOP_KIND or s['data'].get('state') != 'stopped' or u.get('kind') != UNIT_KIND
                    or u['data'].get('state') != STOPPED or (u['data'].get('interruption') or {}).get('stop_id') != sid):
                raise refused('stale_subject', 'the unit is not stopped by this stop')
            ok, why = self.contract.transition(LIFECYCLE, STOPPED, RESUMED, params['evidence'])
            if not ok:
                raise refused('transition_refused', why)
            data = dict(u['data'], state=RESUMED, interruption=None, station_contract=cid)
            return {sid: {'kind': STOP_KIND, 'data': dict(s['data'], state='resumed', resumption=params['permission'])},
                    unit: {'kind': UNIT_KIND, 'data': data},
                    cid: {'kind': CONTRACT_KIND, 'data': params['contract']}}
        raise refused('invalid_input', 'unknown andon action')

    # -- raising a stop -------------------------------------------------------------------------

    def raise_stop(self, packet):
        """Record one AWAITING_AUTHORITY stop from any authenticated requester, then ask its
        designated authority. Returns the stop, the request and the first notice's outcome."""
        c = (packet or {}).get('command') if isinstance(packet, dict) else None
        c = c if isinstance(c, dict) else {}
        unit = c.get('unit') if isinstance(c.get('unit'), str) else None
        try:
            c, entry, key, state = self._verified(packet, RAISE_FIELDS, 'raise')
            if c['station'] not in STOP_POINTS:
                raise Refused('invalid_input', 'the station is not an enabled stop point')
            if not _is_str(c['reason']) or not _is_str(c['unit']):
                raise Refused('invalid_input', 'a stop names its unit and its reason')
            if c['effect'] not in EFFECTS:
                raise Refused('invalid_input', 'the effect is clean or unknown')
            resolving = c['resolving']
            if (not isinstance(resolving, dict) or set(resolving) != {'principal', 'roles'}
                    or not _is_str(resolving.get('principal')) or not isinstance(resolving.get('roles'), list)
                    or not resolving['roles'] or not all(r in self.AC.ROLES for r in resolving['roles'])):
                raise Refused('invalid_input', 'the resolving authority names a person and the roles an answer requires')
            now = self.clock()
            designated = self.AC.membership_entry(state['membership'], resolving['principal'])
            if (not self.AC.active_member(designated, now)[0] or designated.get('principal_type') != 'person'
                    or not set(resolving['roles']) <= set(designated.get('roles') or [])
                    or not self.CM.scope_covers(designated.get('scope'), self.scope)):
                raise Refused('invalid_input', 'the designated authority is an active person holding the resolving roles')
            u = state['entities'].get(unit) or {}
            if u.get('kind') != UNIT_KIND or u['data'].get('repository_uuid') != self.ids['repository_uuid']:
                raise Refused('invalid_input', 'the unit is an execution unit of this repository')
            held = u['data'].get('state')
            if held not in STOP_POINTS[c['station']]:
                raise Refused('stale_subject', 'the unit is %s, not at a %s stop point' % (held, c['station']))
            outstanding = self.unknown_dispatches(unit)
            effect = 'unknown' if c['effect'] == 'unknown' or outstanding else 'clean'
            n = 1 + sum(1 for s in self.stops() if s.get('unit') == unit)
            sid = stop_id(self.ids['repository_uuid'], unit, n)
            alias = request_alias(sid)
            stop = {'schema': SCHEMA, 'stop_id': sid, 'unit': unit, 'station': c['station'], 'interrupted_state': held,
                    'reason': c['reason'], 'effect': effect, 'declared_effect': c['effect'],
                    'outstanding_effects': outstanding, 'raised_by': c['principal'],
                    'raised_by_type': entry.get('principal_type'), 'resolving': {'principal': resolving['principal'],
                                                                                 'roles': sorted(set(resolving['roles']))},
                    'raised': {'command': c, 'signature': packet['signature'], 'key_id': key['key_id']},
                    'request_id': self.I.assignment_id(self.ids['repository_uuid'], alias),
                    'request_alias': alias, 'state': 'stopped', 'raised_at': now, 'revisions': [], 'resumption': None,
                    'domain_uuid': self.ids['domain_uuid'], 'repository_uuid': self.ids['repository_uuid']}
            interruption = {'stop_id': sid, 'station': c['station'], 'interrupted_state': held, 'effect': effect,
                            'resolving': stop['resolving'], 'outstanding_effects': outstanding}
            expected = dict(self._pinned(state, c['principal'], resolving['principal']),
                            **{sid: 0, unit: u['version'], key['key_id']: state['entities'].get(key['key_id'], {}).get('version', 0)})
            expected.update({d: self._entity(d)['version'] for d in outstanding})
            self._commit(dict(action='raise', stop=stop, unit_id=unit, interruption=interruption), expected,
                         c['principal'], c['command_id'], c['nonce'])
        except Refused as exc:
            return self._observe('raise', 'refused', exc.code, unit=unit)
        except self.S.StoreRefused as exc:
            return self._observe('raise', 'refused', 'stale_subject' if exc.code in ('stale_version', 'nonce_consumed',
                                                                                     'command_content_conflict')
                                 else 'invalid_input' if exc.code != 'transition_refused' else 'stale_subject', unit=unit)
        except sqlite3.Error:
            return self._observe('raise', 'refused', 'unavailable_service', unit=unit)
        result = self._observe('raise', 'stopped', None, stop=sid, unit=unit, request=stop['request_id'],
                               versions=expected, effect=effect, station=c['station'])
        result['request'] = self._open_request(self.stop(sid))
        result['notice'] = self.notify(sid) if result['request'].get('outcome') == 'opened' else None
        return result

    # -- the request ----------------------------------------------------------------------------

    def _service_command(self, sid, what, body):
        """A command of this service about one stop, signed with its key. Its id and nonce are derived
        from the stop, so asking again replays the one recorded command."""
        body = dict(self.ids, principal=self.service, command_id='andon:%s:%s' % (sid, what),
                    nonce='andon-nonce:%s:%s' % (sid, what), **body)
        return {'command': body, 'signature': self.service_sign(self.S.canonical_bytes(body))}

    def _brief(self, stop):
        lines = ['Andon stop at the %s station of unit %s (it was %s).' % (stop['station'], stop['unit'],
                                                                           stop['interrupted_state']),
                 'Reason: %s' % stop['reason'],
                 'Raised by %s (%s). Resolving authority: %s with %s.' % (
                     stop['raised_by'], stop['raised_by_type'], stop['resolving']['principal'],
                     ', '.join(stop['resolving']['roles']))]
        if stop['effect'] == 'unknown':
            lines.append('An external effect of this unit has an unknown outcome%s. No answer can resume it: it stays '
                         'stopped with its original dispatch and reservations until that outcome is reconciled.'
                         % (' (%s)' % ', '.join(stop['outstanding_effects']) if stop['outstanding_effects'] else ''))
        else:
            lines.append('accept resumes the unit to READY with a fresh %s station contract; reject or '
                         'return_for_elaboration keeps it stopped.' % stop['station'])
        for i, more in enumerate(stop.get('revisions') or [], 2):
            lines.append('Update %d: %s' % (i, more['reason']))
        return '\n'.join(lines)

    def _risk(self, stop):
        if stop['effect'] == 'unknown':
            return ('Unknown external effect: resuming could repeat or conflict with an effect whose outcome is not '
                    'known, so this stop does not resume on an answer.')
        return 'The unit stays stopped at %s until the resolving authority settles this request.' % stop['station']

    def _open_request(self, stop):
        sid, alias = stop['stop_id'], stop['request_alias']
        rid = stop['request_id']
        if self.inbox.read(rid) is not None:
            return {'outcome': 'opened', 'request_id': rid, 'replayed': True}
        terms = self.settlement.terms(self._service_command(sid, 'terms', dict(
            operation='terms', terms=alias, touchpoint=TOUCHPOINT, target=stop_target(stop),
            proposal={'resume': stop['unit'], 'station': stop['station'], 'stop_id': sid},
            required_roles=list(stop['resolving']['roles']), quorum=None)))
        if terms.get('outcome') != 'recorded':
            return {'outcome': 'refused', 'stage': 'terms', 'reason': terms.get('reason'), 'request_id': rid}
        deadline = time.strftime(DEADLINE_FORMAT, time.gmtime(self.clock() + self.deadline_seconds))
        opened = self.inbox.apply(self._service_command(sid, 'open', dict(
            operation='open', alias=alias, assignment=dict(
                kind='decision', owner=stop['resolving']['principal'], scope=[self.scope], deadline=deadline,
                budget={'owner_minutes': 15}, brief=self._brief(stop), choices=list(CHOICES),
                subject=terms['subject']))))
        if not opened.get('ok'):
            return {'outcome': 'refused', 'stage': 'open', 'reason': opened.get('reason'), 'request_id': rid}
        framed = self._frame(stop, 1)
        if framed.get('outcome') != 'accepted':
            return {'outcome': 'refused', 'stage': 'frame', 'reason': framed.get('reason'), 'request_id': rid}
        return {'outcome': 'opened', 'request_id': rid, 'request_version': 1}

    def _frame(self, stop, version):
        return self.presenter.frame(self._service_command(stop['stop_id'], 'frame-%d' % version, dict(
            operation='frame', alias=stop['request_alias'], request_version=version, risk_statement=self._risk(stop))))

    def revise_stop(self, packet):
        """The requester adds to a pending stop's reason: a new request version with the same status,
        framed and presented again."""
        c = (packet or {}).get('command') if isinstance(packet, dict) else None
        c = c if isinstance(c, dict) else {}
        sid = c.get('stop_id') if isinstance(c.get('stop_id'), str) else None
        try:
            c, entry, key, state = self._verified(packet, REVISE_FIELDS, 'revise')
            stop = self.stop(sid)
            if stop is None:
                raise Refused('invalid_input', 'no such stop')
            if stop['state'] != 'stopped':
                raise Refused('not_stopped', 'the stop is not pending')
            if c['principal'] != stop['raised_by']:
                raise Refused('not_authorized', 'only the requester adds to its stop')
            if not _is_str(c['reason']):
                raise Refused('invalid_input', 'a revision names what it adds')
            item = self.inbox.read(stop['request_id'])
            if item is None or item['data'] is None or item['data']['state'] not in self.I.PENDING:
                raise Refused('stale_subject', 'the stop\'s request is not pending')
            version = item['data']['request_version']
            revision = {'reason': c['reason'], 'by': c['principal'], 'command': c, 'signature': packet['signature'],
                        'request_version': version + 1}
            expected = dict(self._pinned(state, c['principal']), **{sid: self._entity(sid)['version']})
            self._commit(dict(action='revise', stop_id=sid, reason=stop['reason'], revision=revision), expected,
                         c['principal'], c['command_id'], c['nonce'])
        except Refused as exc:
            return self._observe('revise', 'refused', exc.code, stop=sid)
        except self.S.StoreRefused as exc:
            return self._observe('revise', 'refused', 'stale_subject' if exc.code != 'malformed_command'
                                 else 'invalid_input', stop=sid)
        except sqlite3.Error:
            return self._observe('revise', 'refused', 'unavailable_service', stop=sid)
        stop = self.stop(sid)
        revised = self.inbox.apply(self._service_command(sid, 'revise-%d' % version, dict(
            operation='revise', alias=stop['request_alias'], request_version=version,
            changes={'brief': self._brief(stop)})))
        if not revised.get('ok'):
            return self._observe('revise', 'refused', revised.get('reason') or 'unknown_outcome', stop=sid,
                                 unit=stop['unit'], request=stop['request_id'])
        framed = self._frame(stop, version + 1)
        if framed.get('outcome') != 'accepted':
            return self._observe('revise', 'refused', framed.get('reason') or 'unknown_outcome', stop=sid,
                                 unit=stop['unit'], request=stop['request_id'])
        result = self._observe('revise', 'revised', None, stop=sid, unit=stop['unit'], request=stop['request_id'],
                               versions=expected, request_version=version + 1)
        result['notice'] = self.notify(sid)
        return result

    # -- the notice -----------------------------------------------------------------------------

    def notify(self, sid):
        """Present the stop's current request version to its designated authority through the activated
        edge, once per (request, request version, presentation), and keep the correlation."""
        stop = self.stop(sid) if isinstance(sid, str) else None
        if stop is None:
            return self._observe('notify', 'refused', 'invalid_input', stop=sid)
        rid = stop['request_id']
        item = self.inbox.read(rid)
        if item is None or item['data'] is None:
            return self._observe('notify', 'refused', 'missing_evidence', stop=sid, unit=stop['unit'], request=rid)
        data = item['data']
        refusal, record, _versions = self.presenter.compose(rid)
        if refusal:
            return self._observe('notify', 'refused', 'missing_authority' if refusal == 'missing_authority'
                                 else 'stale_subject', stop=sid, unit=stop['unit'], request=rid)
        pid = record['presentation_id'] if record is not None else self.presenter.head(rid)['current']
        key = notice_key(rid, data['request_version'], pid)
        nid = notice_id(key)
        if self._entity(nid) is not None:
            return self._observe('notify', 'suppressed', None, stop=sid, unit=stop['unit'], request=rid,
                                 notice_id=nid, presentation_id=pid)
        shown = self.presenter.present(rid)
        receipt = self.presenter.receipt(shown.get('presentation_id') or pid) or {}
        if shown.get('outcome') not in ('published', 'already_presented') or receipt.get('outcome') != 'published':
            return self._observe('notify', 'refused', 'unavailable_service' if shown.get('reason') != 'not_activated'
                                 else 'missing_authority', stop=sid, unit=stop['unit'], request=rid,
                                 presentation_id=pid, presented=shown.get('outcome'))
        notice = {'schema': NOTICE_SCHEMA, 'notice_id': nid, 'key': key, 'stop_id': sid, 'request_id': rid,
                  'request_version': data['request_version'], 'request_state': data['state'],
                  'presentation_id': receipt['presentation_id'], 'presentation_version': receipt['presentation_version'],
                  'presentation_digest': receipt['brief_digest'], 'channel': receipt.get('channel'),
                  'chat_id': receipt.get('chat_id'), 'message_ids': list(receipt.get('message_ids') or []),
                  'message_id': receipt.get('message_id'), 'published_at': receipt.get('published_at'),
                  'answer_path': {'reply_to_message_id': receipt.get('message_id'), 'choices': list(receipt.get('choices') or []),
                                  'form': '<choice>: <your reason>'},
                  'noticed_at': self.clock()}
        self._serial += 1
        command_id = 'andon-notice:%s:%d:%d' % (nid, data['request_version'], self._serial)
        try:
            self._commit(dict(action='notice', notice=notice), {nid: 0, rid: item['version'],
                                                                receipt['presentation_id']: receipt['entity_version']},
                         self.journal_signer, command_id, command_id)
        except self.S.StoreRefused as exc:
            return self._observe('notify', 'refused', 'stale_subject' if exc.code == 'stale_version' else 'unknown_outcome',
                                 stop=sid, unit=stop['unit'], request=rid, presentation_id=pid)
        return self._observe('notify', 'notified', None, stop=sid, unit=stop['unit'], request=rid, notice_id=nid,
                             presentation_id=receipt['presentation_id'], message_id=receipt.get('message_id'))

    # -- resuming -------------------------------------------------------------------------------

    def _permission(self, stop, item, state, now):
        """What permits resuming: the settlement of the request's CURRENT version by the designated
        authority, with its receipt and typed effect, on the presentation that is still current."""
        rid, data = stop['request_id'], item['data']
        version = data['request_version']
        settled = self.settlement.settlement(rid, version)
        if settled is None:
            raise Refused('no_settlement', 'no settlement of the current request version')
        reference = data.get('settlement') or {}
        if data.get('state') != TERMINAL or reference.get('settlement_id') != settled.get('settlement_id'):
            raise Refused('missing_evidence', 'the request\'s terminal state does not name this settlement')
        receipt = self._entity(settled.get('receipt_id') or '')
        effect = self._entity(settled.get('effect_id') or '')
        if (receipt is None or receipt['data'].get('settlement_digest') != digest(settled)
                or receipt['data'].get('request_version') != version):
            raise Refused('missing_evidence', 'the settlement has no receipt that binds it')
        if (effect is None or effect['data'].get('target') != stop_target(stop)
                or effect['data'].get('request_version') != version):
            raise Refused('missing_evidence', 'the settlement\'s effect does not name this stop')
        if settled.get('ruling') != RESUME_RULING:
            raise Refused('missing_authority', 'the ruling was %s, not to resume' % settled.get('ruling'))
        designated = stop['resolving']['principal']
        if settled.get('principals') != [designated]:
            raise Refused('not_authorized', 'the settlement is not the designated authority\'s alone')
        entry = self.AC.membership_entry(state['membership'], designated)
        if (not self.AC.active_member(entry, now)[0] or entry.get('principal_type') != 'person'
                or not set(stop['resolving']['roles']) <= set(entry.get('roles') or [])
                or not self.CM.scope_covers(entry.get('scope'), self.scope)):
            raise Refused('not_authorized', 'the designated authority no longer holds the resolving roles')
        head = self.presenter.head(rid)
        shown = self.presenter.receipt(settled.get('presentation_id') or '')
        if (head is None or head.get('current') != settled.get('presentation_id') or shown is None
                or shown.get('request_version') != version or shown.get('brief_digest') != settled.get('presentation_digest')):
            raise Refused('stale_presentation', 'the settled presentation is not the request\'s current one')
        return {'kind': 'settlement', 'settlement_id': settled['settlement_id'], 'receipt_id': settled['receipt_id'],
                'effect_id': settled['effect_id'], 'principal': designated, 'ruling': settled['ruling'],
                'request_version': version, 'presentation_id': settled['presentation_id'],
                'originating_channel': settled.get('originating_channel'), 'settled_at': settled.get('settled_at')}

    def resume(self, sid):
        """Resume a clean decision stop on its designated authority's current settlement, with a
        fresh station contract. An unknown-effect stop never resumes here."""
        stop = self.stop(sid) if isinstance(sid, str) else None
        if stop is None:
            return self._observe('resume', 'refused', 'invalid_input', stop=sid)
        unit, rid = stop['unit'], stop['request_id']
        try:
            if stop['state'] != 'stopped':
                raise Refused('not_stopped', 'the stop is %s' % stop['state'])
            u = self._entity(unit)
            if u is None or u['kind'] != UNIT_KIND or u['data'].get('state') != STOPPED \
                    or (u['data'].get('interruption') or {}).get('stop_id') != sid:
                raise Refused('stale_subject', 'the unit is not stopped by this stop')
            outstanding = sorted(set(stop['outstanding_effects']) | set(self.unknown_dispatches(unit)))
            if stop['effect'] == 'unknown' or outstanding:
                raise Refused('unknown_outcome', 'an external effect of this unit is unreconciled; an answer does not resume it')
            item = self.inbox.read(rid)
            if item is None or item['data'] is None:
                raise Refused('missing_evidence', 'the stop\'s request is not readable')
            now = self.clock()
            state = self.CM.authority_state(self.S, self.conn)
            permission = self._permission(stop, item, state, now)
            attempt = 1 + sum(1 for _i, _v, d in self._of_kind(CONTRACT_KIND) if d.get('unit') == unit)
            cid = contract_id(self.ids['repository_uuid'], unit, attempt)
            contract = {'schema': CONTRACT_SCHEMA, 'contract_id': cid, 'unit': unit, 'station': stop['station'],
                        'attempt': attempt, 'issued_at_unit_version': u['version'] + 1, 'stop_id': sid,
                        'supersedes': u['data'].get('station_contract'), 'permission': permission,
                        'issued_at': now, 'domain_uuid': self.ids['domain_uuid'],
                        'repository_uuid': self.ids['repository_uuid']}
            contract['contract_digest'] = digest(contract)
            expected = dict(self._pinned(state, permission['principal']),
                            **{sid: self._entity(sid)['version'], unit: u['version'], cid: 0, rid: item['version']})
            for eid in (permission.get('settlement_id'), permission.get('receipt_id'), permission.get('effect_id'),
                        permission.get('presentation_id')):
                if isinstance(eid, str) and self._entity(eid) is not None:
                    expected[eid] = self._entity(eid)['version']
            evidence = {'resuming_authority_receipt': True, 'outstanding_effects_reconciled': not outstanding}
            self._serial += 1
            command_id = 'andon-resume:%s:%d:%.6f:%d' % (sid, permission['request_version'], now, self._serial)
            self._commit(dict(action='resume', stop_id=sid, unit_id=unit, contract=contract, permission=permission,
                              evidence=evidence), expected, self.journal_signer, command_id, command_id)
        except Refused as exc:
            return self._observe('resume', 'refused', exc.code, stop=sid, unit=unit, request=rid)
        except self.S.StoreRefused as exc:
            return self._observe('resume', 'refused', 'stale_subject' if exc.code in ('stale_version', 'transition_refused')
                                 else 'unknown_outcome', stop=sid, unit=unit, request=rid)
        except sqlite3.Error:
            return self._observe('resume', 'refused', 'unavailable_service', stop=sid, unit=unit, request=rid)
        return self._observe('resume', 'resumed', None, stop=sid, unit=unit, request=rid, versions=expected,
                             contract_id=cid, permission=permission)

    def run(self):
        """One pass over the pending stops: present any version not yet noticed, then resume each
        stop whose current settlement permits it. Returns every outcome."""
        results = []
        for stop in self.stops():
            if stop.get('state') != 'stopped':
                continue
            item = self.inbox.read(stop['request_id'])
            if item is not None and item['data'] is not None and item['data']['state'] in self.I.PENDING:
                results.append(self.notify(stop['stop_id']))
            else:
                results.append(self.resume(stop['stop_id']))
        return results

    def metrics(self):
        return dict(self.counts, pending=[s['stop_id'] for s in self.stops() if s.get('state') == 'stopped'],
                    stopped_units=sorted({s['unit'] for s in self.stops() if s.get('state') == 'stopped'}))
