"""Telegram progress and completion reports from committed journal events (VELDO-0128, PLAN-0019 W91).

WHAT THIS MODULE IS. The ordinary outbound report of the factory's progress to its owner. It walks the
committed control journal of the activated ingress's one store, in journal order, after an explicit
starting sequence, and derives one report for every record that commits an ENABLED event. REGISTRY is
the declared event set, each with its handler:

  objective_accepted   an objective record entering ACCEPTED (VELDO-0077's acceptance through settlement);
  decision_awaiting    a VELDO-0064 inbox decision request offered at a new request version (a grooming or
                       admission wait), named by the touchpoint of the settlement terms it binds;
  work_progress        a VELDO-0039 dispatch record entering accepted, running, exited, refused or unknown
                       (work assigned to a worker and the worker's progress);
  gate_result          an execution unit leaving VERIFYING or REVIEWING along a declared R13 edge (the gate
                       or the review passed, or rejected it with a failure receipt);
  stop                 a VELDO-0075 andon stop recorded;
  completion           a confirmed landing: VELDO-0051's spec.shipped, derived by its own public reader
                       (control_event_projection.Projection.derive) from a revision_landed receipt for the
                       exact unit and a confirmed publication of its dispatch. Nothing else is a completion:
                       a build-only attempt, an exited dispatch, an accepted artifact or a unit state is not.

A REPORT IS A PROJECTION. It states the committed fact of its source record and the next action or the
evidence, and it writes only its own `telegram_report` record through its registered store command
(`telegram_report_record`, the only writer of that kind, control_store.declare_owners). It never admits,
settles, resumes or completes anything, and no model output is read. A pending decision (a waiting
request or a stop) is sent as a reply to the request's CURRENT presentation and names it; a request with
no published presentation says so. Unknown or unavailable state is said plainly. A stop is reported once,
as progress: the andon's own request and its notice are the decision message, so the andon's request is
never reported again as a waiting decision and a revised stop is not a new report.

ONLY THE CONFIGURED OWNER'S ENROLLED CHAT, ONLY THROUGH THE ACTIVATED EDGE. The reporter is configured with
the owner principal it reports to; that principal's VELDO-0064 chat enrollment names the chat. Every send
goes through the ingress's presentation edge, which asks the VELDO-0073 activation gate, and the gate
sends only to the enrolled owner's chat of a current activation. A reporter whose edge is not the
ingress's gated edge is refused at construction.

WHAT WAS SENT IS WHAT IS RECORDED. One record per (event, source record, owner), keyed so a second run
sends nothing again. The record is committed as a `pending` intent before the send and completed with
what the platform returned: `sent` with the chat, message identity, date and stored text; `anomaly` when
the platform stored other text or placed it in another chat; `refused` with the gate's or the platform's
refusal by name (nothing was published, the record is visibly unsent); `unknown_outcome` when no readable
answer came back. The source event is never touched: the record names it by journal sequence, command,
record digest, entity and entity digest (and, for a completion, the spec.shipped event id and receipt).
No record is sent again automatically, whatever its outcome (retry, lost-send lookup and recovery are
Release 2).

OBSERVABILITY. Every report is observed with domain, repository, project, event, report id, source
sequence, accepted versions, outcome, named refusal and its error class (invalid input, missing
authority, stale subject, unavailable service, missing evidence, unknown outcome; unknown is never
success). metrics() counts accepted and refused operations, the pending source events not yet reported
and the unsent reports. No report text, token or signature is observed. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

SCHEMA = 'veldo.telegram_report/v1'
KIND = 'telegram_report'
OPERATION = 'telegram_report_record'
OWNER = 'VELDO-0128 telegram report'
WRITES = ('entities', 'journal', 'commands', 'nonces')
CHANNEL = 'telegram_chat'
OUTCOMES = ('pending', 'sent', 'anomaly', 'refused', 'unknown_outcome')
UNSENT = ('pending', 'refused', 'unknown_outcome')
PLATFORM_FIELDS = ('chat_id', 'message_id', 'date', 'text')
UNAVAILABLE = 'unavailable'

# The source kinds, each the committing service's own vocabulary.
OBJECTIVE_KIND, ACCEPTED = 'objective', 'ACCEPTED'                    # control_objective (VELDO-0077)
ASSIGNMENT_KIND, DECISION = 'assignment', 'decision'                  # control_assignment (VELDO-0064)
PENDING_STATES = ('OFFERED', 'ACCEPTED', 'IN_PROGRESS')               # control_assignment.CATEGORIES pending
TERMS_KIND = 'settlement_terms'                                       # control_request_settlement.TERMS_KIND
DISPATCH_KIND = 'dispatch'                                            # control_dispatch.RECORD_KIND
PROGRESS_STATES = ('accepted', 'running', 'exited', 'refused', 'unknown')
UNIT_KIND = 'execution_unit'                                          # entity_contract R13
STOP_KIND, STOPPED = 'andon_stop', 'stopped'                          # control_andon (VELDO-0075)
# The R13 edges out of the gate and review stations, with the receipt each edge requires.
GATE_EDGES = {('VERIFYING', 'REVIEWING'): ('gate', 'passed'), ('VERIFYING', 'FAILED'): ('gate', 'rejected'),
              ('REVIEWING', 'READY_TO_LAND'): ('review', 'passed'), ('REVIEWING', 'FAILED'): ('review', 'rejected')}

# The declared event set: (event, source entity kinds, handler). The completion handler reads VELDO-0051's
# journal projection instead of one entity kind.
REGISTRY = (
    ('objective_accepted', (OBJECTIVE_KIND,), '_objective'),
    ('decision_awaiting', (ASSIGNMENT_KIND,), '_awaiting'),
    ('work_progress', (DISPATCH_KIND,), '_progress'),
    ('gate_result', (UNIT_KIND,), '_gate'),
    ('stop', (STOP_KIND,), '_stop'),
    ('completion', None, '_completions'),
)

TAXONOMY = {'invalid_input': 'invalid_input', 'no_enrolled_chat': 'missing_authority',
            'invalid_enrollment': 'missing_authority', 'chat_not_enrolled': 'missing_authority',
            'not_activated': 'missing_authority', 'edge_stopped': 'missing_authority',
            'owner_not_current': 'missing_authority', 'stale_enrollment': 'stale_subject',
            'stale_configuration': 'stale_subject', 'stale_key': 'stale_subject',
            'qualification_expired': 'stale_subject', 'missing_qualification': 'missing_evidence',
            'channel_refused': 'unavailable_service', 'unavailable_service': 'unavailable_service',
            'stale_version': 'stale_subject', 'unknown_outcome': 'unknown_outcome'}


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code = code


def _organ(name):
    spec = importlib.util.spec_from_file_location('telegram_report_' + name.split('.')[0],
                                                  Path(__file__).resolve().with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def _shown(value):
    """A value as the report shows it: the value, or `unavailable` said plainly."""
    return str(value) if value is not None and value != '' else UNAVAILABLE


def report_id(event, domain, repository, owner, seq, source):
    """One report per (event, source record, owner)."""
    body = json.dumps([event, domain, repository, owner, seq, source], separators=(',', ':'))
    return 'telegram-report:' + hashlib.sha256(body.encode()).hexdigest()[:40]


def text_digest(text):
    return 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()


def events():
    """The declared event names, in REGISTRY order."""
    return tuple(name for name, _kinds, _handler in REGISTRY)


def _record_transition(params, before):
    """The two phases of one report record: `intent` creates it `pending` before any send; `complete`
    finishes that pending record from what the send returned. Nothing else is written."""
    rid, phase = params.get('report_id'), params.get('phase')
    if not isinstance(rid, str) or phase not in ('intent', 'complete'):
        raise ValueError('a report record names its id and phase')
    current = (before.get(rid) or {}).get('data')
    if phase == 'intent':
        record = params.get('record')
        if current is not None:
            raise ValueError('a report is recorded once and never sent again automatically')
        if not isinstance(record, dict) or record.get('schema') != SCHEMA or record.get('report_id') != rid:
            raise ValueError('an intent carries the report it binds')
        data = dict(record, outcome='pending', refusal=None, chat_id=None, message_id=None, platform_date=None,
                    platform_text=None, anomalies=[])
        return {rid: {'kind': KIND, 'data': data}}
    if current is None or current.get('outcome') != 'pending':
        raise ValueError('a completion finishes the pending record it names')
    platform, refusal = params.get('platform'), params.get('refusal')
    data = dict(current)
    if refusal is not None:
        if not _text(refusal) or platform is not None:
            raise ValueError('a refusal names its code and carries no platform answer')
        data.update(outcome='refused', refusal=refusal)
    elif platform is None:
        data.update(outcome='unknown_outcome')
    else:
        if (not isinstance(platform, dict) or set(platform) != set(PLATFORM_FIELDS)
                or not all(type(platform[k]) is int for k in ('chat_id', 'message_id', 'date'))
                or not isinstance(platform['text'], str)):
            raise ValueError('a platform answer carries its chat, message, date and text')
        found = []
        if platform['text'] != data['text']:
            found.append('presentation_mismatch')
        if platform['chat_id'] != data['enrolled_chat']:
            found.append('chat_mismatch')
        data.update(outcome='anomaly' if found else 'sent', chat_id=platform['chat_id'],
                    message_id=platform['message_id'], platform_date=platform['date'],
                    platform_text=platform['text'], anomalies=found)
    return {rid: {'kind': KIND, 'data': data}}


class Reporter:
    """The report projection of one activated ingress's store to one configured owner.

    `ingress` is a control_channel_ingress.Ingress (its inbox, presenter and gate share its connection);
    `owner` the principal whose enrolled chat receives the reports; `project` the project the reports
    name; `since` the journal sequence after which committed events are reported (an explicit
    coordinate: nothing before it is reported)."""

    def __init__(self, ingress, *, owner, project, since, clock=time.time):
        inbox, presenter, gate = ingress.inbox, ingress.presenter, getattr(ingress, 'gate', None)
        if inbox is None or presenter is None or gate is None or not (
                inbox.conn is ingress.conn and presenter.conn is ingress.conn and gate.conn is ingress.conn):
            raise Refused('invalid_input', 'the reporter has one authority: the ingress store connection')
        edge = getattr(presenter, 'edge', None)
        if edge is None or getattr(edge, 'activation', None) is not gate:
            raise Refused('invalid_input', 'every report goes through the activated edge of the ingress')
        if not _text(owner) or not _text(project) or type(since) is not int or since < 0:
            raise Refused('invalid_input', 'the reporter names its owner, its project and the sequence it starts after')
        self.ingress, self.conn, self.presenter, self.gate, self.edge = ingress, ingress.conn, presenter, gate, edge
        self.S, self.P = inbox.store, presenter.P
        self.ids = dict(inbox.ids)
        self.journal_signer, self.sign = inbox.journal_signer, inbox.sign
        self.authority_generation = inbox.authority_generation
        self.owner, self.project, self.since, self.clock = owner, project, since, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._serial = 0
        database = next((row[2] for row in self.conn.execute('PRAGMA database_list') if row[1] == 'main'), None)
        if not _text(database):
            raise Refused('invalid_input', 'the ingress store is a file')
        EP = _organ('control_event_projection.py')
        # VELDO-0051's public reader of confirmed landings over the same journal; nothing is published.
        self._landings = EP.Projection(self.S, database, domain=self.ids['domain_uuid'],
                                       repository=self.ids['repository_uuid'], root=Path(database).parent)

        def transition(params, before):
            try:
                return _record_transition(params, before)
            except ValueError as exc:
                raise self.S.StoreRefused('invalid_input', str(exc))
        self.conn.command_registry[OPERATION] = {'transition': transition, 'writes': WRITES}
        self.S.declare_owners(self.conn, OWNER, kinds={KIND: (OPERATION,)}, module=__file__)

    # Reading.

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def _rows(self):
        return [(seq, command, digest, json.loads(transition), committed) for seq, command, digest, transition, committed
                in self.conn.execute('SELECT j.seq, j.command_id, j.record_digest, j.transition, p.committed_at FROM journal j '
                                     'LEFT JOIN publication p ON p.seq = j.seq ORDER BY j.seq')]

    def record(self, rid):
        e = self._entity(rid)
        return dict(e['data'], entity_version=e['version']) if e is not None and e['kind'] == KIND else None

    def records(self):
        return [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (KIND,))]

    def sources(self):
        """Every enabled event committed after `since`, in journal order: one source per report."""
        rows = self._rows()
        found, state = [], {}
        for seq, command, digest, changes, _committed in rows:
            if seq > self.since:
                for eid in sorted(changes):
                    entry = changes[eid] if isinstance(changes[eid], dict) else {}
                    for event, kinds, handler in REGISTRY:
                        if kinds is None or entry.get('kind') not in kinds:
                            continue
                        fact = getattr(self, handler)(eid, entry, state.get(eid), state)
                        if fact is not None:
                            found.append(self._source(event, seq, command, digest, eid, entry, fact))
            state.update(changes)
        for event, kinds, handler in REGISTRY:
            if kinds is None:
                found += getattr(self, handler)(rows)
        return sorted(found, key=lambda s: (s['source']['journal_seq'], s['source']['entity_id'], s['event']))

    def _source(self, event, seq, command, digest, eid, entry, fact):
        source = {'journal_seq': seq, 'command_id': command, 'record_digest': digest, 'entity_id': eid,
                  'entity_kind': entry.get('kind'), 'entity_digest': entry.get('digest')}
        source.update(fact.pop('source_extra', {}))
        return dict(fact, event=event, source=source)

    # The handlers: each returns the fact its committed record carries, or None.

    @staticmethod
    def _data(entry):
        return entry.get('data') if isinstance((entry or {}).get('data'), dict) else {}

    def _objective(self, eid, entry, prior, state):
        data, before = self._data(entry), self._data(prior)
        if data.get('state') != ACCEPTED or before.get('state') == ACCEPTED:
            return None
        acceptance = data.get('acceptance') if isinstance(data.get('acceptance'), dict) else {}
        return {'unit': None, 'run': None, 'project': data.get('project'),
                'headline': 'Objective accepted',
                'fact': 'objective %s accepted at revision %s (bound digest %s)'
                        % (eid, _shown(data.get('accepted_revision')), _shown(data.get('bound_digest'))),
                'next': 'Features may now be proposed under it; the acceptance admits none of them.',
                'evidence': 'settlement %s, receipt %s' % (_shown(acceptance.get('settlement_id')),
                                                          _shown(acceptance.get('receipt_id')))}

    def _stop_request(self, request, state):
        """Whether `request` is an andon stop's own request (its notice is the decision message)."""
        return any((v or {}).get('kind') == STOP_KIND and self._data(v).get('request_id') == request
                   for v in state.values())

    def _awaiting(self, eid, entry, prior, state):
        data, before = self._data(entry), self._data(prior)
        if (data.get('kind') != DECISION or data.get('state') not in PENDING_STATES
                or data.get('request_version') == before.get('request_version') or self._stop_request(eid, state)):
            return None
        subject = data.get('subject') if isinstance(data.get('subject'), dict) else {}
        terms = self._data(state.get(subject.get('ref'))) if subject.get('kind') == TERMS_KIND else {}
        return {'unit': data.get('unit_id'), 'run': None, 'project': None, 'request': eid,
                'request_version': data.get('request_version'),
                'headline': 'Decision waiting: %s' % _shown(terms.get('touchpoint')).replace('_', ' '),
                'fact': 'request %s version %s offered to %s by %s: %s'
                        % (eid, _shown(data.get('request_version')), _shown(data.get('owner')),
                           _shown(data.get('requested_by')), ' '.join(str(data.get('brief') or UNAVAILABLE).split())),
                'next': None, 'evidence': None}

    def _progress(self, eid, entry, prior, state):
        data, before = self._data(entry), self._data(prior)
        status = data.get('state')
        if status not in PROGRESS_STATES or status == before.get('state'):
            return None
        contract = data.get('contract') if isinstance(data.get('contract'), dict) else {}
        run = data.get('dispatch_id') or contract.get('dispatch_id')
        termination = data.get('termination') if isinstance(data.get('termination'), dict) else {}
        said = {'accepted': ('Work assigned', 'the receiver accepted the dispatch; the worker is launching.'),
                'running': ('Work running', 'no action; the worker is running.'),
                'exited': ('Work exited', 'the worker exited with status %s; this is not a completion, the gate '
                                          'and review follow.' % _shown(termination.get('exit_status'))),
                'refused': ('Work refused', 'nothing ran; the dispatch is closed.'),
                'unknown': ('Work outcome unknown', 'the launch or its outcome could not be established; nothing '
                                                    'is assumed and a stop is owed.')}[status]
        return {'unit': contract.get('unit'), 'run': run, 'project': None, 'headline': said[0],
                'fact': 'dispatch %s of unit %s at station %s is %s (worker %s)'
                        % (_shown(run), _shown(contract.get('unit')), _shown(contract.get('station')), status,
                           _shown(contract.get('worker'))),
                'next': said[1], 'evidence': None}

    def _gate(self, eid, entry, prior, state):
        data, before = self._data(entry), self._data(prior)
        edge = GATE_EDGES.get((before.get('state'), data.get('state')))
        if edge is None:
            return None
        station, verdict = edge
        receipt = data.get('failure_receipt') if verdict == 'rejected' else data.get('%s_receipt' % station)
        return {'unit': eid, 'run': data.get('dispatch_id'), 'project': None,
                'headline': '%s %s' % (station.capitalize(), verdict),
                'fact': 'the %s %s unit %s: %s -> %s' % (station, verdict, eid, before.get('state'), data.get('state')),
                'next': ('the unit goes back through its stations; nothing lands.' if verdict == 'rejected'
                         else 'the unit moves to %s.' % data.get('state')),
                'evidence': 'receipt %s' % _shown(receipt)}

    def _stop(self, eid, entry, prior, state):
        data = self._data(entry)
        if data.get('state') != STOPPED or prior is not None:
            return None
        resolving = data.get('resolving') if isinstance(data.get('resolving'), dict) else {}
        return {'unit': data.get('unit'), 'run': eid, 'project': None, 'request': data.get('request_id'),
                'request_version': None,
                'headline': 'Stopped: unit %s at the %s station' % (_shown(data.get('unit')), _shown(data.get('station'))),
                'fact': 'stop %s raised by %s interrupts %s; effect %s; awaiting %s'
                        % (eid, _shown(data.get('raised_by')), _shown(data.get('interrupted_state')),
                           _shown(data.get('effect')), _shown(resolving.get('principal'))),
                'next': None, 'evidence': None}

    def _completions(self, rows):
        """Completion: only VELDO-0051's spec.shipped, from a confirmed landing receipt of the exact unit
        and dispatch. Every other record is not a completion."""
        shipped, _judged = self._landings.derive(rows, 0)
        receipts = {}
        for _seq, _command, _digest, changes, _committed in rows:
            for eid, entry in changes.items():
                if isinstance(entry, dict) and entry.get('kind') == 'completion_receipt':
                    receipts[(_seq, eid)] = self._data(entry)
        found = []
        for event in shipped:
            if event['journal_seq'] <= self.since:
                continue
            receipt = receipts.get((event['journal_seq'], event['receipt'])) or {}
            landing = receipt.get('publication_receipt') if isinstance(receipt.get('publication_receipt'), dict) else {}
            fact = {'unit': event['unit'], 'run': event['dispatch_id'], 'project': None,
                    'headline': 'Completed: unit %s landed' % event['unit'],
                    'fact': 'unit %s landed revision %s through dispatch %s (confirmed at the remote)'
                            % (event['unit'], event['commit'], event['dispatch_id']),
                    'next': None,
                    'evidence': 'proof %s, implementation %s, receipt %s %s, event spec.shipped %s'
                                % (_shown(landing.get('proof_digest')), _shown(event.get('implementation_commit')),
                                   event['receipt'], _shown(event.get('receipt_digest')), event['id']),
                    'revision': event['commit'], 'proof': landing.get('proof_digest'),
                    'source_extra': {'event_id': event['id'], 'receipt': event['receipt']}}
            entry = {'kind': 'completion_receipt', 'digest': event.get('receipt_digest')}
            found.append(self._source('completion', event['journal_seq'], event['command_id'],
                                      event['record_digest'], event['receipt'], entry, fact))
        return found

    # Rendering.

    def _presentation(self, request):
        """(reply_to, line) for a pending decision: its current presentation, or none said plainly."""
        item = self._entity(request) if _text(request) else None
        now = self._data(item).get('state') if item else None
        current = self.presenter.current(request) if _text(request) else None
        messages = (current or {}).get('message_ids') or []
        if not current or not messages:
            return None, 'Presentation: none published yet; the request is %s.' % _shown(now)
        return messages[-1], ('Decide on presentation %s (message %s, request version %s); the request is %s now.'
                              % (current.get('presentation_id') or current.get('id'), messages[-1],
                                 _shown(current.get('request_version')), _shown(now)))

    def render(self, source):
        """(text, reply_to): plain text, no markup; the committed fact, its next action or evidence, and
        its source identity."""
        reply_to, nxt = None, source.get('next')
        if source['event'] in ('decision_awaiting', 'stop'):
            reply_to, nxt = self._presentation(source.get('request'))
        s = source['source']
        lines = ['Veldo: %s' % source['headline'],
                 'Project: %s | Domain: %s | Repository: %s' % (source.get('project') or self.project,
                                                                  self.ids['domain_uuid'], self.ids['repository_uuid']),
                 'Unit: %s | Run: %s' % (source.get('unit') or 'none', source.get('run') or 'none'),
                 'Fact: %s' % source['fact']]
        if nxt:
            lines.append('Next: %s' % nxt)
        if source.get('evidence'):
            lines.append('Evidence: %s' % source['evidence'])
        lines.append('Source: journal %s, command %s, record %s, entity %s %s'
                     % (s['journal_seq'], s['command_id'], s['record_digest'], s['entity_id'], _shown(s['entity_digest'])))
        return '\n'.join(line.rstrip() for line in lines), reply_to

    # Writing.

    def _commit(self, params, expected):
        self._serial += 1
        rid = params['report_id']
        command_id = '%s:%s:%s:%.6f:%d' % (OPERATION, params['phase'], rid, self.clock(), self._serial)
        command = dict(command_id=command_id, principal=self.journal_signer, operation=OPERATION, parameters=params,
                       expected_versions=expected, artifact_digests=[], nonce=command_id)
        self.S.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)
        return self.record(rid)

    def _enrollment(self):
        """(refusal, enrollment): the configured owner's own enrolled chat, or the named reason there is none."""
        eid = self.P.enrollment_id(self.owner)
        found = self._entity(eid)
        if found is None:
            return 'no_enrolled_chat', None
        if self.P.enrollment_problems(found['kind'], found['data'], self.owner):
            return 'invalid_enrollment', None
        return None, {'id': eid, 'version': found['version'], 'chat': found['data']['chat_id']}

    def _send(self, chat, text, reply_to):
        """The completion parameters of a pending record: what the platform answered, a refusal by name,
        or neither (unknown)."""
        try:
            sent = self.edge.send(chat, text, reply_to)
        except self.P.EdgeRefused as exc:
            unknown = exc.code == 'unknown_outcome'
            return {'platform': None, 'refusal': None if unknown else exc.code}
        except Exception:
            return {'platform': None, 'refusal': None}
        return {'platform': {k: sent[k] for k in PLATFORM_FIELDS}, 'refusal': None}

    def _observe(self, source, rid, outcome, reason, versions=None):
        accepted = outcome in ('sent', 'already_reported')
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.ids, operation='report', project=self.project, event=source['event'],
                                      report_id=rid, unit=source.get('unit'), run=source.get('run'),
                                      journal_seq=source['source']['journal_seq'],
                                      accepted_versions=dict(versions or {}), outcome=outcome, reason=reason,
                                      error_class=None if accepted else taxonomy(reason)))
        result = {'report_id': rid, 'event': source['event'], 'outcome': outcome}
        if reason is not None:
            result['reason'] = reason
        return result

    def report(self, source):
        s = source['source']
        rid = report_id(source['event'], self.ids['domain_uuid'], self.ids['repository_uuid'], self.owner,
                        s['journal_seq'], s['entity_id'])
        existing = self.record(rid)
        if existing is not None:
            outcome = 'already_reported' if existing['outcome'] == 'sent' else existing['outcome']
            return self._observe(source, rid, outcome, existing.get('refusal') if outcome == 'refused' else None)
        refusal, enrollment = self._enrollment()
        text, reply_to = self.render(source)
        record = dict(schema=SCHEMA, report_id=rid, channel=CHANNEL, event=source['event'],
                      project=source.get('project') or self.project, domain_uuid=self.ids['domain_uuid'],
                      repository_uuid=self.ids['repository_uuid'], unit=source.get('unit'), run=source.get('run'),
                      source=dict(s), owner=self.owner, enrollment_id=(enrollment or {}).get('id'),
                      enrollment_version=(enrollment or {}).get('version'),
                      enrolled_chat=(enrollment or {}).get('chat'), reply_to=reply_to,
                      revision=source.get('revision'), proof=source.get('proof'), text=text,
                      text_digest=text_digest(text), reported_at=self.clock())
        versions = {rid: 0}
        if enrollment is not None:
            versions[enrollment['id']] = enrollment['version']
        try:
            intent = self._commit(dict(phase='intent', report_id=rid, record=record), versions)
        except self.S.StoreRefused as exc:
            return self._observe(source, rid, 'refused', exc.code, versions)  # no intent, nothing sent
        completion = ({'platform': None, 'refusal': refusal} if refusal
                      else self._send(enrollment['chat'], text, reply_to))
        try:
            done = self._commit(dict(phase='complete', report_id=rid, **completion), {rid: intent['entity_version']})
        except self.S.StoreRefused as exc:
            return self._observe(source, rid, 'unknown_outcome', exc.code, versions)  # the intent stays pending
        reason = ','.join(done['anomalies']) if done['outcome'] == 'anomaly' else done['refusal']
        if done['outcome'] == 'unknown_outcome':
            reason = 'unknown_outcome'
        return self._observe(source, rid, done['outcome'], reason, versions)

    def run(self):
        """Report every enabled event committed after `since` that has no record yet; one result each."""
        return [self.report(source) for source in self.sources()]

    def unsent(self):
        """The reports that were not delivered, with their named refusal: visibly unsent."""
        return [r for r in self.records() if r.get('owner') == self.owner and r.get('outcome') in UNSENT]

    def metrics(self):
        mine = {r['report_id']: r for r in self.records() if r.get('owner') == self.owner}
        pending = []
        for source in self.sources():
            s = source['source']
            rid = report_id(source['event'], self.ids['domain_uuid'], self.ids['repository_uuid'], self.owner,
                            s['journal_seq'], s['entity_id'])
            if rid not in mine:
                pending.append(rid)
        return dict(self.counts, pending=pending, sent=sum(1 for r in mine.values() if r['outcome'] == 'sent'),
                    unsent=sorted(r['report_id'] for r in mine.values() if r['outcome'] in UNSENT),
                    anomalies=sum(1 for r in mine.values() if r['outcome'] == 'anomaly'))
