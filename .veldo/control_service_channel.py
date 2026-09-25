#!/usr/bin/env python3
"""The authority service's Telegram channel: the VELDO-0073 ingress, run by the running service, and
the owner's activation commands applied to it (VELDO-0138).

WHAT THIS MODULE IS. The part of the authority service (control_service.py) that owns the lifetime of
the Telegram ingress. An installation that names a channel ingress configuration (the
veldo.telegram_ingress/v1 host configuration, copied into the protected configuration at install)
opens it at `serve` with VELDO-0073's production construction, control_channel_ingress.open_ingress,
unchanged, and closes it when the service stops. Nothing else in the service reads the token file or
talks to the Bot API.

INERT UNTIL ACTIVATED. With no activation record the ingress is constructed and the service serves as
before: each pass asks the VELDO-0073 gate first (Ingress.wake), which refuses not_activated before a
byte leaves, and a refused pass presents nothing, acquires nothing and writes nothing. The same holds
for a stopped record (edge_stopped) and every other gate refusal.

ONE PASS. Every POLL_SECONDS the serve loop runs `Channel.tick`: wake canonical acquisition (the gate
decides, the settlement service settles only answers the platform returned), then present every
pending inbox request whose current presentation is not the one current authority requires
(Presenter.publish), then, inside a qualification run, record the qualification once its legs are
complete. The gate re-reads the activation record at every exchange, so the owner's stop takes effect
at the next exchange of the running service, without a restart, and nothing about a pending request
changes: it stays pending, and the platform keeps every update not yet acquired, since the
acquisition cursor moves only past kept evidence.

THE OWNER'S COMMANDS. A channel_activation_authorize packet the service's Authority accepted (the
request signature, the peer and the workspace coordinate judged as for every request) is handed to the
ingress's own Activations organ, which admits only the owner's own OpenSSH-signed envelope over the
exact action and parameters and refuses anyone else by name with nothing written. `status` reports,
read only, what the owner's command surface (control_channel_activation.main, `veldo channel`) needs
to build a command: the configured origin and edge key, the authority coordinates and versions, the
current record and, in a qualification run, the qualification the service recorded for it.

THE QUALIFICATION THE SERVICE RECORDS. The qualification record binds every exchange the gate made in
the run, which only the process that made them holds, so the running service records it
(Activations.qualify, unchanged) once, in a qualification run, a request it presented has settled from
the owner's acquired answer. Its unauthorized leg is an update from an unenrolled sender: one the
platform returned in the run when there is one, and otherwise, because the owner has no second person
(Telegram 29047), one update from an unenrolled sender id acquired from an in-process loopback
stand-in of a separate probe bot (PROBE_BOT_ID, with its own acquisition cursor, so the platform's
updates are never confirmed by it), whose provenance the record marks `stand_in`, as VELDO-0073's live
runner did. The owner then signs the activation over that record's id and digest with his enrolled
key. A restart ends a run's exchanges with the process (restart recovery is Release 2): a restarted
run is qualified again.

THE QUALIFICATION REQUEST. A qualification needs one decision request presented to the owner and
answered by him. When the running service accepts the owner's qualify command, the channel opens ONE
decision request addressed to him, as the factory's qualification requester: the service member that
`veldo factory setup` enrolls by the owner's own signed command (VELDO-0139), whose key is REQUESTER_KEY
in the protected key directory that holds the configuration's journal key. It is opened through the
ingress's own settlement terms, inbox and presenter, each command signed by the requester's key, and
the service presents it on its next pass like any pending request. Its alias is derived from the
qualify command's id alone, and every pass of a qualifying run makes sure it exists, so a pass after a
restart finds the one already opened and never opens a second, and a run whose opening was cut short
opens it then. An installation without the requester key (a factory not laid down by setup) opens
nothing and qualifies on whatever request its operators open.

THE OWNER'S STANDING DELEGATION (VELDO-0140). The protected signer signs the owner's answers under his
one standing delegation to the edge (control_signer_answers). He grants or renews it with `veldo channel
delegate`: a VELDO-0025 grant_delegation, or a supersede_delegation naming his current one, signed with
his enrolled key and sent to the running service, which hands it here. `delegate` admits it only when it
is the owner's own signature over his own standing delegation of answers to this edge (a current person
member holding project_owner, enrolled on this channel's chat, and the edge's recorded owner when it has
a record), then through control_membership.admit, which judges the envelope, the signature and the
policy and commits it; the renewed delegation is superseded, never deleted. Anyone else is refused by
name with nothing written.

NO SILENT REFUSAL (VELDO-0140). When a pass acquires an answer of his that the edge could not have
signed, the service replies once to that message in his chat, through the presenter's gated send,
saying why: no delegation, an expired one (renew it), or the signer's named refusal. When his standing
delegation is within control_signer_answers.RENEW_NOTICE_SECONDS of expiring (or has expired unseen), he
is told once per delegation, in his enrolled chat, to renew it. Each message is recorded before it is
sent, so a redelivery or a later pass never repeats it.

A RESTART keeps the edge exactly as the owner left it, because the service holds no state of its own
about it: the record in the store decides every exchange.

Observations carry identities, digests, counts, states and named refusals, never the token, message
text or a signature. Standard library only.
"""
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import threading
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('service_channel_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IN = _organ('control_channel_ingress')
ACT = _organ('control_channel_activation')
EV = _organ('control_channel_attribution')
ST = _organ('control_request_settlement')
I = _organ('control_assignment')
V = _organ('control_channel_presentation')
A = _organ('control_signer_answers')

CHANNEL = ACT.CHANNEL
AUTHORIZE = ACT.AUTHORIZE
POLL_SECONDS = 1.0
# The in-memory observation lists each pass leaves behind are kept to this many entries; the durable
# record is the store and the service's observation log.
OBSERVATION_LIMIT = 256
# The separate probe bot of the unauthorized leg: its own evidence ids and its own acquisition cursor.
PROBE_BOT_ID = 1
PROBE_TOKEN = 'unauthorized-probe'
# The factory's qualification requester (VELDO-0139): a service member enrolled by the owner at setup,
# whose key file is this name in the protected key directory, and the one scope it opens requests in.
REQUESTER = 'qualification-requester'
REQUESTER_KEY = 'qualification-requester'
REQUESTER_SCOPE = 'channel-qualification'
REQUEST_CHOICES = ['accept', 'return_for_elaboration', 'reject']
# The owner's grant and renewal of his standing delegation (VELDO-0140): VELDO-0025 membership commands,
# of the assertion kinds an owner answers on this edge, lasting at most MAX_DELEGATION_DAYS.
DELEGATION_OPERATIONS = ('grant_delegation', 'supersede_delegation')
DELEGATION_KINDS = ('decision_answer', 'review_disposition')
MAX_DELEGATION_DAYS = 366
RENEWAL_PREFIX = 'delegation-renewal:'


def qualification_alias(run):
    """The alias of the one qualification request of the run started by qualify command `run`."""
    return 'qualification-' + hashlib.sha256(str(run).encode()).hexdigest()[:32]


def requester_key(config):
    """The qualification requester's key: REQUESTER_KEY beside the configuration's journal key."""
    key = (config.get('journal') or {}).get('key') if isinstance(config.get('journal'), dict) else None
    return os.path.join(os.path.dirname(key), REQUESTER_KEY) if isinstance(key, str) and os.path.isabs(key) else None


def _code(exc):
    return getattr(exc, 'code', None) or type(exc).__name__


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def installable(path, binding, principal, journal_key, repositories):
    """The ingress configuration an installation copies, refused by name unless it is VELDO-0073's
    configuration of THIS authority: its store, domain and store identities, generation, a repository
    the instance serves, and the service's own journal principal and key."""
    try:
        config = IN.load_config(path)
    except Exception as exc:  # noqa: BLE001 - the ingress module names its own refusal
        raise Refused('invalid_input:channel_ingress:' + _code(exc), str(path)) from None
    ids = config.get('authority_ids') if isinstance(config.get('authority_ids'), dict) else {}
    journal = config.get('journal') if isinstance(config.get('journal'), dict) else {}
    checks = (('store', str(config.get('store_path')) == binding['store_path']),
              ('domain', ids.get('domain_uuid') == binding['domain_uuid']),
              ('store_uuid', ids.get('store_uuid') == binding['store_uuid']),
              ('repository', ids.get('repository_uuid') in repositories),
              ('generation', config.get('authority_generation') == binding['authority_generation']),
              ('journal', journal.get('principal') == principal and journal.get('key') == journal_key),
              ('channel', config.get('channel') == CHANNEL))
    for name, ok in checks:
        if not ok:
            raise Refused('invalid_input:channel_ingress:' + name, 'the ingress configuration is not this authority\'s')
    return Path(path).read_bytes()


def open_channel(path, clock=time.time):
    """(Channel, None) for an installation's ingress configuration, (None, refusal) when it cannot be
    constructed, and (None, None) when the installation names none."""
    if not path:
        return None, None
    try:
        return Channel(path, clock), None
    except Exception as exc:  # noqa: BLE001 - the service keeps serving; the refusal is reported by name
        return None, _code(exc)


class Channel:
    """The ingress of one running authority service and its owner's commands."""

    def __init__(self, config_path, clock=time.time):
        self.clock = clock
        self.config = IN.load_config(config_path)
        self.ingress = IN.open_ingress(config_path, clock)
        self.passes, self.last, self.run = 0, None, None
        self.requests = []
        key = requester_key(self.config)
        self.requester = None
        if key and os.path.isfile(key):
            IN._private_file(key, 'the qualification requester key')
            self.requester = (REQUESTER, ACT.ssh_signer(key))

    def close(self):
        self.ingress.conn.close()

    # -- reading ---------------------------------------------------------------------------------

    def _entity(self, eid):
        row = self.ingress.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def record(self):
        return self.ingress.gate.current()

    def status(self):
        """What the owner's command surface reads: configuration, coordinates, versions, the record and
        the run's recorded qualification. Read only; no token, no text."""
        ing = self.ingress
        record = self.record()
        state = ACT.CM.authority_state(ing.activations.S, ing.conn)
        qualification = None
        if record and record.get('state') == 'qualifying':
            found = self._entity(ACT.qualification_id(CHANNEL, record.get('command_id')))
            if found and found['kind'] == ACT.QUALIFICATION_KIND:
                data = found['data']
                qualification = {'id': data.get('qualification_id'), 'digest': ACT.digest(data),
                                 'request_id': data.get('request_id'), 'platform': data.get('platform'),
                                 'bot_id': data.get('bot_id'), 'recorded_at': data.get('recorded_at'),
                                 'unauthorized_provenance': (data.get('unauthorized') or {}).get('provenance')}
        shown = None
        if record:
            shown = {k: record.get(k) for k in ('state', 'origin', 'platform', 'owner', 'edge_key_id', 'command_id',
                                                'authorized_by', 'authorized_at', 'expires_at', 'qualification_id',
                                                'qualification_digest', 'bot_id', 'stopped_from', 'entity_version')}
        run = self.run or {}
        edge = (self.config.get('signer') or {}).get('edge_key_id')
        owner = (record or {}).get('owner')
        member = ACT.AC.membership_entry(state['membership'], owner) if owner else None
        delegations = [{'id': d['id'], 'principal': d.get('principal'), 'standing': ACT.CM.standing(d),
                        'expires_at': d.get('expires_at'), 'authority_scope': d.get('authority_scope'),
                        'assertion_kinds': d.get('assertion_kinds')}
                       for d in state['delegations'] if d.get('channel') == CHANNEL and d.get('edge_key_id') == edge
                       and d.get('superseded_by') is None and d.get('revoked_at') is None]
        return {'available': True, 'channel': CHANNEL, 'origin': (self.config.get('bot_api') or {}).get('origin'),
                'platform': ACT.platform_of((self.config.get('bot_api') or {}).get('origin')),
                'edge_key_id': (self.config.get('signer') or {}).get('edge_key_id'),
                'authority_ids': dict(ing.activations.ids), 'membership_version': state['membership_version'],
                'delegation_version': state['delegation_version'], 'record': shown, 'qualification': qualification,
                'delegations': delegations, 'owner_scope': (member or {}).get('scope'),
                'delegation': A.standing_status(state, owner, CHANNEL, edge, self.clock()) if owner else None,
                'run': {'id': run.get('id'), 'answered': sorted(run.get('answers', {})),
                        'refusal': run.get('refusal'), 'request': run.get('request')} if run else None,
                'requests': [dict(r) for r in self.requests[-8:]],
                'passes': self.passes, 'last_pass': self.last, 'pending': ing.metrics().get('pending'),
                'gate': dict(ing.gate.counts)}

    # -- the owner's commands --------------------------------------------------------------------

    def authorize(self, packet):
        """Apply one owner-signed channel_activation_authorize packet through the ingress's own
        Activations organ. Returns the organ's observation; nothing is written unless it is accepted."""
        packet = packet if isinstance(packet, dict) else {}
        envelope, command, signature = packet.get('envelope'), packet.get('command'), packet.get('signature')
        if isinstance(command, dict) and command.get('operation') in DELEGATION_OPERATIONS:
            return self.delegate(envelope, command, signature)
        outcome = self.ingress.activations.authorize(envelope if isinstance(envelope, dict) else {}, command,
                                                     signature if isinstance(signature, str) else '')
        if outcome.get('outcome') == 'accepted' and outcome.get('action') == 'qualify':
            record = self.record() or {}
            if record.get('state') == 'qualifying' and record.get('command_id') == outcome.get('command_id'):
                self.open_request(record)
        return outcome

    def delegate(self, envelope, command, signature):
        """The owner's grant or renewal of his standing delegation to this edge (VELDO-0140): admitted only
        when it is his own signature over his own standing delegation of answers to this edge, then by
        control_membership.admit. Returns {outcome, reason, action, delegation_id, supersedes}; nothing is
        written unless it is accepted."""
        ing = self.ingress
        S, CM, AC = ing.presenter.store, ing.presenter.membership, ACT.AC
        params = (command.get('parameters') if isinstance(command, dict) else None) or {}
        shown = {'action': 'delegate', 'delegation_id': params.get('id'), 'supersedes': params.get('supersedes')}
        now = self.clock()
        try:
            if not isinstance(envelope, dict) or not isinstance(signature, str) or not signature.strip():
                raise Refused('signature_invalid', 'the owner signs his delegation')
            state = CM.authority_state(S, ing.conn)
            signer = envelope.get('principal')
            entry = AC.membership_entry(state['membership'], signer)
            if not AC.active_member(entry, now)[0]:
                raise Refused('not_current_member')
            key = AC.active_key(state['keyring'], signer, now)
            if key is None or not AC.ssh_keygen_verify(AC.canonical_envelope_bytes(envelope), signature,
                                                       AC.allowed_signers_line(signer, key['public_key']), signer)[0]:
                raise Refused('signature_invalid')
            if entry.get('principal_type') != 'person':
                raise Refused('not_a_person')
            if ACT.OWNER_ROLE not in (entry.get('roles') or []):
                raise Refused('policy_refused', 'the owner delegates his answers: the signer holds %s' % ACT.OWNER_ROLE)
            record = self.record() or {}
            chat = self._entity(ing.presenter.P.enrollment_id(signer))
            if (params.get('principal') != signer or (record.get('owner') is not None and signer != record['owner'])
                    or chat is None or ing.presenter.P.enrollment_problems(chat['kind'], chat['data'], signer)):
                raise Refused('not_owner', 'the owner grants or renews his own delegation')
            edge = (self.config.get('signer') or {}).get('edge_key_id')
            kinds = params.get('assertion_kinds')
            expires = params.get('expires_at')
            if (params.get('channel') != CHANNEL or params.get('edge_key_id') != edge or not CM.standing(params)
                    or not isinstance(kinds, list) or not kinds or not set(kinds) <= set(DELEGATION_KINDS)
                    or not isinstance(expires, (int, float)) or isinstance(expires, bool)
                    or not now < expires <= now + MAX_DELEGATION_DAYS * 86400):
                raise Refused('invalid_input', 'a standing delegation of his answers to this edge, for at most %d days'
                              % MAX_DELEGATION_DAYS)
            current = sorted(d['id'] for d in state['delegations']
                             if d.get('principal') == signer and d.get('channel') == CHANNEL and d.get('edge_key_id') == edge
                             and d.get('superseded_by') is None and d.get('revoked_at') is None)
            if command.get('operation') == 'grant_delegation' and current:
                raise Refused('invalid_input', 'he holds a delegation to this edge: a renewal supersedes it')
            if command.get('operation') == 'supersede_delegation' and params.get('supersedes') not in current:
                raise Refused('invalid_input', 'a renewal supersedes his current delegation to this edge')
            committed = CM.admit(S, ing.conn, envelope, command, signature, dict(ing.activations.ids), now,
                                 journal_signer=(ing.activations.journal_signer, ing.activations.sign))
        except Refused as exc:
            return dict(shown, outcome='refused', reason=exc.code)
        except CM.MembershipRefused as exc:
            return dict(shown, outcome='refused', reason=exc.code if exc.code in ACT.REFUSALS else 'policy_refused')
        return dict(shown, outcome='accepted', reason=None, seq=(committed or {}).get('seq'))

    def open_request(self, record):
        """Make sure the one qualification request of `record`'s run exists and is framed: settlement
        terms, then the inbox request addressed to the recorded owner, then the requester's framing,
        each signed by the requester's key and each skipped when already committed. Returns what it did."""
        run = record.get('command_id')
        if self.requester is None:
            return self._opened(run, None, 'skipped', 'no_requester')
        ing = self.ingress
        S, ids = ing.activations.S, dict(ing.activations.ids)
        principal, sign = self.requester
        alias = qualification_alias(run)
        rid = ing.presenter.inbox_request(alias)

        def signed(body):
            return {'command': body, 'signature': sign(S.canonical_bytes(body))}
        try:
            if self._entity(rid) is None:
                tid = ST.terms_id(ids['repository_uuid'], alias)
                terms = self._entity(tid)
                if terms is None:
                    shown = ing.settlement.terms(signed(dict(
                        ids, operation='terms', terms=alias, principal=principal, command_id=alias + ':terms',
                        nonce=alias + ':terms', touchpoint='grooming',
                        target={'kind': 'channel_qualification', 'ref': 'channel-qualification:%s' % run,
                                'digest': 'sha256:' + hashlib.sha256(str(run).encode()).hexdigest()},
                        proposal=None, required_roles=[], quorum=None)))
                    subject = shown.get('subject')
                    if not subject:
                        return self._opened(run, rid, 'refused', 'terms:%s' % shown.get('reason'))
                else:
                    subject = {'kind': ST.SUBJECT_KIND, 'ref': tid, 'digest': ST.digest(terms['data'])}
                expires = record.get('expires_at') or self.clock()
                opened = ing.inbox.apply(signed(dict(
                    ids, operation='open', alias=alias, principal=principal, command_id=alias + ':open',
                    nonce=alias + ':open', assignment=dict(
                        kind='decision', owner=record.get('owner'), scope=[REQUESTER_SCOPE],
                        deadline=time.strftime(I.DEADLINE_FORMAT, time.gmtime(expires)),
                        budget={'owner_minutes': max(1, int((expires - self.clock()) // 60))},
                        brief='Qualification of the Telegram edge: reply accept to this message to show that this '
                              'chat answers the factory. Nothing else changes.',
                        choices=list(REQUEST_CHOICES), subject=subject))))
                if not opened.get('ok'):
                    return self._opened(run, rid, 'refused', 'open:%s' % opened.get('reason'))
            if self._entity(V.framing_id(rid)) is None:
                framed = ing.presenter.frame(signed(dict(
                    ids, operation='frame', alias=alias, principal=principal, request_version=1,
                    command_id=alias + ':frame', nonce=alias + ':frame',
                    risk_statement='Low: answering settles this qualification request and nothing else.')))
                if framed.get('outcome') != 'accepted':
                    return self._opened(run, rid, 'refused', 'frame:%s' % framed.get('reason'))
        except Exception as exc:  # noqa: BLE001 - refused by name; the pass goes on
            return self._opened(run, rid, 'refused', _code(exc))
        return self._opened(run, rid, 'open', None)

    def _opened(self, run, rid, outcome, reason):
        shown = {'run': run, 'request_id': rid, 'outcome': outcome, 'reason': reason}
        self.requests.append(shown)
        del self.requests[:-OBSERVATION_LIMIT]
        return shown

    # -- one pass --------------------------------------------------------------------------------

    def tick(self):
        """Wake acquisition, present pending requests, and inside a qualification run record its
        qualification once complete. A gate refusal ends the pass with nothing presented or written.
        Returns the pass summary, with `notable` set when it did something or its outcome changed."""
        ing = self.ingress
        record = self.record()
        run_id = record.get('command_id') if record and record.get('state') == 'qualifying' else None
        if run_id != (self.run or {}).get('id'):
            # A new qualification run binds only the exchanges made in it.
            del ing.gate.exchanges[:]
            self.run = {'id': run_id, 'answers': {}, 'strangers': [], 'tried': set(), 'recorded': None,
                        'refusal': None, 'request': None, 'retry_at': 0, 'retry_every': 1} if run_id else None
        if (self.run is not None and (self.run['request'] or {}).get('outcome') not in ('open', 'skipped')
                and self.passes >= self.run['retry_at'] and self.clock() < (record.get('expires_at') or 0)):
            # Until the run's one request is open: every step is skipped when already committed, so a
            # retry (or a restart, which finds it by its alias) completes an interrupted opening and never
            # opens a second. A refusal is retried with a doubling wait, at most every 64 passes.
            self.run['request'] = self.open_request(record)
            if self.run['request'].get('outcome') != 'open':
                self.run['retry_at'] = self.passes + self.run['retry_every']
                self.run['retry_every'] = min(self.run['retry_every'] * 2, 64)
        woke = ing.wake({'source': 'authority_service', 'pass': self.passes})
        self.passes += 1
        published, recorded = [], None
        told = []
        if woke.get('outcome') == 'woken':
            published = [r.get('outcome') for r in ing.presenter.publish()]
            told = self.tell_unsigned(woke.get('acquired') or []) + self.tell_renewal(record)
            if self.run is not None:
                recorded = self._qualification(woke)
        sent = sum(1 for outcome in published if outcome == 'published')
        summary = {'outcome': woke.get('outcome'), 'reason': woke.get('reason'),
                   'state': (record or {}).get('state'), 'acquired': len(woke.get('acquired', [])),
                   'settled': len(woke.get('settled', [])), 'published': sent, 'told': told}
        if recorded:
            summary['qualification'] = recorded
        previous = self.last or {}
        summary['notable'] = bool(summary['acquired'] or summary['settled'] or sent or recorded or told
                                  or any(previous.get(k) != summary[k] for k in ('outcome', 'reason', 'state')))
        self.last = {k: v for k, v in summary.items() if k != 'notable'}
        self._trim()
        return summary

    # -- no silent refusal of the owner's answers (VELDO-0140) ------------------------------------

    def _standing(self, principal):
        ing = self.ingress
        state = ing.presenter.membership.authority_state(ing.presenter.store, ing.conn)
        return A.standing_status(state, principal, CHANNEL, (self.config.get('signer') or {}).get('edge_key_id'),
                                 self.clock())

    @staticmethod
    def _day(when):
        return time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(when))

    def why_unsigned(self, refusal, standing):
        """The one sentence the owner is told when an answer of his could not be signed."""
        renew = 'Renew it with veldo channel delegate, then reply to the request again.'
        if standing['status'] == 'none':
            return 'Your answer was not counted: you hold no delegation that lets this chat sign your answers. ' + renew
        if standing['status'] == 'expired':
            return ('Your answer was not counted: your delegation for answering here expired on %s. %s'
                    % (self._day(standing['expires_at']), renew))
        if refusal in ('request-mismatch', 'presentation-mismatch'):
            return ('Your answer was not counted: the request changed after that message. Reply to its latest message.')
        return 'Your answer was not counted: the signer refused it (%s).' % refusal

    def tell_unsigned(self, acquired):
        """Tell the owner, once per message, why each answer of his this pass acquired was not signed."""
        ing = self.ingress
        results = getattr(ing.acquirer.edge_sign, 'results', None) or []
        told = []
        for row in acquired:
            if row.get('outcome') != 'refused' or row.get('reason') != 'unavailable_service' or not row.get('evidence_id'):
                continue
            evidence = ing.acquirer.evidence(row['evidence_id']) or {}
            fields = evidence.get('fields') or {}
            if not evidence.get('principal') or not evidence.get('request_id'):
                continue
            refusal = next((r.get('refusal') for r in reversed(results)
                            if (r.get('diagnostic') or {}).get('evidence_id') == row['evidence_id']), None)
            standing = self._standing(evidence['principal'])
            before = len(ing.presenter.observations)
            ing.presenter._tell({'chat_id': fields.get('chat_id'), 'platform_message_id': fields.get('message_id')},
                                {'request_id': evidence['request_id']},
                                self.why_unsigned(refusal or 'signing-unavailable', standing))
            if len(ing.presenter.observations) > before:
                told.append({'kind': 'unsigned', 'evidence_id': row['evidence_id'], 'status': standing['status'],
                             'refusal': refusal, 'outcome': ing.presenter.observations[-1].get('outcome')})
        return told

    def tell_renewal(self, record):
        """Tell the recorded owner once per delegation, in his enrolled chat, that his standing delegation
        is about to expire (or has expired) and how to renew it."""
        owner = (record or {}).get('owner')
        if not owner:
            return []
        standing = self._standing(owner)
        if standing['status'] not in ('expiring', 'expired'):
            return []
        ing = self.ingress
        presenter = ing.presenter
        tid = RENEWAL_PREFIX + standing['delegation_id']
        chat = self._entity(presenter.P.enrollment_id(owner))
        if self._entity(tid) is not None or chat is None:
            return []
        verb = 'expired on' if standing['status'] == 'expired' else 'expires on'
        text = ('Your delegation for answering here %s %s. Renew it with veldo channel delegate --principal %s '
                '--key <your enrolled key>.' % (verb, self._day(standing['expires_at']), owner))
        told = {'schema': 'veldo.presentation_tell/v1', 'channel': CHANNEL, 'request_id': None,
                'chat_id': chat['data'].get('chat_id'), 'message_id': None, 'text': text,
                'delegation_id': standing['delegation_id'], 'expires_at': standing['expires_at']}
        try:
            presenter._commit(V.TELL_OPERATION, dict(tell_id=tid, tell=told), {tid: 0}, command_id=tid)
        except presenter.store.StoreRefused:
            return []
        sent = presenter._send(told['chat_id'], text, None)
        return [{'kind': 'renewal', 'delegation_id': standing['delegation_id'], 'status': standing['status'],
                 'outcome': 'sent' if sent['platform'] else 'not_sent'}]

    def _trim(self):
        ing = self.ingress
        ing.gate.exchanges[:] = [x for x in ing.gate.exchanges if x.get('mode') == 'qualifying']
        for holder in (ing, ing.gate, ing.activations, ing.acquirer, ing.presenter, ing.settlement, ing.inbox):
            kept = getattr(holder, 'observations', None)
            if isinstance(kept, list) and len(kept) > OBSERVATION_LIMIT:
                del kept[:-OBSERVATION_LIMIT]

    # -- the qualification run -------------------------------------------------------------------

    def _qualification(self, woke):
        ing, run = self.ingress, self.run
        for row in woke.get('acquired', []):
            if row.get('outcome') == 'answered' and row.get('request_id') and row.get('evidence_id'):
                run['answers'][row['request_id']] = row['evidence_id']
            elif row.get('reason') == 'unknown_sender' and row.get('evidence_id'):
                run['strangers'].append(row['evidence_id'])
        if run['recorded']:
            return None
        for request, evidence in sorted(run['answers'].items()):
            receipt = ing.presenter.current(request) or {}
            if (request, evidence) in run['tried'] or not ing.settlement.settlement(request, receipt.get('request_version')):
                continue
            run['tried'].add((request, evidence))
            stranger = run['strangers'][-1] if run['strangers'] else self._unauthorized_probe()
            try:
                qid, qdigest, _record = ing.activations.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement,
                                                                request, evidence, stranger)
            except Exception as exc:  # noqa: BLE001 - refused by name, nothing written
                run['refusal'] = _code(exc)
                return {'outcome': 'refused', 'reason': run['refusal'], 'request_id': request}
            run['recorded'] = {'id': qid, 'digest': qdigest, 'request_id': request}
            return {'outcome': 'recorded', 'id': qid, 'digest': qdigest, 'request_id': request}
        return None

    def _unauthorized_probe(self):
        """One update from an unenrolled sender id, acquired from an in-process loopback stand-in of the
        separate probe bot, and refused as unknown_sender. Returns its evidence id, or None."""
        acquirer = self.ingress.acquirer
        record = self.record() or {}
        chat = record.get('enrolled_chat')
        if type(chat) is not int:
            return None
        cursor = acquirer._entity(EV.cursor_id(PROBE_BOT_ID))
        update_id = max(1, ((cursor or {}).get('data') or {}).get('next_offset', 0))
        sender = {'id': chat + 1, 'is_bot': False, 'first_name': 'Unenrolled'}
        update = {'update_id': update_id, 'message': {'message_id': update_id, 'from': sender,
                                                      'chat': {'id': sender['id'], 'type': 'private'},
                                                      'date': int(self.clock()), 'text': 'accept: an unenrolled sender'}}
        answers = {'getMe': {'id': PROBE_BOT_ID, 'is_bot': True, 'first_name': 'probe'}, 'getUpdates': [update]}

        class Probe(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length') or 0))
                method = self.path.rsplit('/', 1)[-1]
                body = json.dumps({'ok': method in answers, 'result': answers.get(method)}).encode()
                self.send_response(200 if method in answers else 404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Probe)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        saved = acquirer.edge
        try:
            acquirer.edge = type(saved)(acquirer.P, 'http://127.0.0.1:%d' % server.server_address[1], PROBE_TOKEN)
            acquirer.acquire()
        except Exception:  # noqa: BLE001 - the qualification then refuses by name (unauthorized_unproven)
            return None
        finally:
            acquirer.edge = saved
            server.shutdown()
            server.server_close()
        found = acquirer.evidence(EV.evidence_id(PROBE_BOT_ID, update_id)) or {}
        return found.get('evidence_id') if found.get('reason') == 'unknown_sender' else None
