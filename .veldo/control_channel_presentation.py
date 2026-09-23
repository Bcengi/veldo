"""Versioned Telegram presentation receipts and presentation-bound answers (VELDO-0065, PLAN-0019 W50, R72).

WHAT THIS MODULE IS. What the owner was shown, kept as immutable receipts in the control store,
and the one check that decides whether an answer from Telegram may settle. A presentation is
composed from current authority only: the inbox assignment at its current request version
(VELDO-0064), the risk statement its requester signed for that version (`frame`), an authority
statement derived from the owner's current membership, and the owner's enrolled chat. Its
rendered bytes are what Telegram shows, and the receipt binds them.

THREE DIGESTS, NEVER ONE. The request digest covers the request identity, its version and every
accepted content field, so two revisions with equal content are two requests (R09). The subject
digests are the digests of what the request is about, copied from the assignment's subject. The
presentation digest (`brief_digest`, the authority contract's name) is the digest of the exact
rendered bytes. The presentation key is (request, request version, presentation digest), so a
revised text is always a new presentation and a reused key can never suppress it.

RECEIPTS ARE IMMUTABLE. One `channel_presentation` receipt per presentation key. It is committed
as a `pending` intent before the Bot API `sendMessage` call and completed once from what the
platform returned: its chat, its message identity, its date and the text it stored. A published
receipt, an anomaly and an unknown outcome are never written again; only a definite platform
refusal starts a new attempt of the same receipt. The receipt carries every R72 field: request id
and version, full request digest, subject digests, rendered brief bytes, risk and authority
statements, offered choices, channel identity, external conversation id (chat), external
presentation id (message) and publication time (the platform's date).

VISIBLE SUPERSESSION. The current presentation of a request on this channel is named by one
`channel_presentation_head` entity. A replacement names the presentation it supersedes in its own
bytes and is sent as a Telegram reply to the superseded message, so the link is visible in the
chat; the platform's returned reply identity is checked against it. The head moves in the same
transaction that confirms the replacement's publication, and the superseded receipt is left as it
was.

ANSWERS NAME WHAT WAS SHOWN. An answer is a canonical Telegram assertion signed by the channel
edge with the channel's restricted key: the presentation it addresses (id, digest, version), its
ruling and its rationale, and the platform's own message id, sender id, timestamp, chat and the
message it replies to. It settles only when the named receipt is confirmed published, is the
head's current presentation, and still binds the current request, framing, authority statement,
choices and enrolled chat. Everything else refuses by name. The owner answers a request version
once. The answer record is the assertion `authority_contract.settle` consumes (VELDO-0068 performs
the one settlement): its ruling is in the contract's RULINGS vocabulary, mapped from the offered
choice in CHOICE_RULINGS and nowhere else, beside the choice the owner typed, the rationale and
the edge's signature. No second settlement record is written here.

WHAT IT IS NOT. Not canonical acquisition of updates from the platform (VELDO-0066), edge
enrollment and delegation (VELDO-0067), settlement, quorum and decision effects (VELDO-0068), or
interrupted publication and lost-acknowledgement recovery (Release 2). The bot token is supplied
by the caller's custody and never logged or stored. Standard library only.
"""
import hashlib
import http.client
import json
import sqlite3
import time
import urllib.error
import urllib.request

SCHEMA = 'veldo.channel_presentation/v1'
HEAD_SCHEMA = 'veldo.channel_presentation_head/v1'
FRAMING_SCHEMA = 'veldo.presentation_framing/v1'
ANSWER_SCHEMA = 'veldo.presentation_answer/v1'
RECEIPT_KIND = 'channel_presentation'
HEAD_KIND = 'channel_presentation_head'
FRAMING_KIND = 'presentation_framing'
ANSWER_KIND = 'presentation_answer'
RECORD_OPERATION = 'channel_presentation_record'
FRAME_OPERATION = 'presentation_frame'
ANSWER_OPERATION = 'presentation_answer'
CHANNEL = 'telegram_chat'
OUTCOMES = ('pending', 'published', 'anomaly', 'refused', 'unknown_outcome')
ANOMALIES = ('presentation_mismatch', 'chat_mismatch', 'supersession_mismatch')
RETRYABLE = ('refused',)
# The accepted content of a request, in the request digest beside its identity and version.
REQUEST_FIELDS = ('kind', 'owner', 'scope', 'deadline', 'budget', 'brief', 'choices', 'subject', 'unit_id',
                  'requested_by')
# What an answered receipt must still share with current authority before its answer settles.
BOUND_FIELDS = ('request_id', 'request_version', 'request_digest', 'subject_digests', 'risk_statement',
                'framed_by', 'authority_statement', 'choices', 'owner', 'enrolled_chat')
INTENT_FIELDS = ('schema', 'channel', 'request_id', 'request_version', 'request_digest', 'request',
                 'assignment_version', 'subject_digests', 'presentation_version', 'risk_statement', 'framed_by',
                 'framing_id', 'rulings',
                 'framing_version', 'authority_statement', 'choices', 'owner', 'enrollment_id', 'enrollment_version',
                 'enrolled_chat', 'supersedes', 'reply_to', 'rendered', 'brief_digest', 'presentation_id')
PLATFORM_FIELDS = ('chat_id', 'message_id', 'date', 'text', 'reply_to_message_id')
ATTRIBUTION_FIELDS = ('platform_message_id', 'sender_id', 'platform_timestamp', 'chat_id', 'reply_to_message_id')
REFERENCE_FIELDS = ('presentation_id', 'presentation_digest', 'presentation_version')
# Every named refusal and the error class it belongs to; unknown is never labeled success.
REFUSALS = {'invalid_input': 'invalid_input', 'missing_rationale': 'invalid_input',
            'not_authorized': 'missing_authority', 'not_owner': 'missing_authority',
            'missing_authority': 'missing_authority',
            'missing_presentation': 'missing_evidence', 'unknown_presentation': 'missing_evidence',
            'unseen_presentation': 'missing_evidence', 'evidence_mismatch': 'missing_evidence',
            'answer_before_publication': 'invalid_input',
            'missing_framing': 'missing_evidence', 'no_enrolled_chat': 'missing_evidence',
            'invalid_enrollment': 'missing_evidence',
            'superseded_presentation': 'stale_subject', 'stale_presentation': 'stale_subject',
            'stale_subject': 'stale_subject', 'already_answered': 'stale_subject', 'unmapped_choice': 'invalid_input',
            'stale_version': 'stale_subject',
            'presentation_mismatch': 'missing_evidence', 'chat_mismatch': 'missing_evidence',
            'supersession_mismatch': 'missing_evidence',
            'channel_refused': 'unavailable_service', 'incomplete_transaction': 'unavailable_service',
            'unavailable_service': 'unavailable_service', 'unknown_outcome': 'unknown_outcome'}
# The one place an offered choice becomes a ruling of authority_contract.RULINGS (and the one
# acknowledgement word); a decision whose choices do not all map here is not presented.
CHOICE_RULINGS = {'accept': 'approve', 'approve': 'approve', 'reject': 'reject',
                  'return_for_elaboration': 'return_for_elaboration', 'acknowledged': 'acknowledged'}
SETTLED_OUTCOMES = {'pending': 'unknown_outcome', 'unknown_outcome': 'unknown_outcome', 'anomaly': 'anomaly'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def _digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def bytes_digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def request_digest(request_id, request_version, content):
    """The full request digest: identity, version and every accepted content field (R09, R72)."""
    body = {'request_id': request_id, 'request_version': request_version}
    body.update({k: content.get(k) for k in REQUEST_FIELDS})
    return _digest(body)


def subject_digests(content):
    subject = content.get('subject') or {}
    return [{'kind': subject.get('kind'), 'ref': subject.get('ref'), 'digest': subject.get('digest')}]


def presentation_id(request_id, request_version, digest):
    """The presentation key: request, request version and presentation content digest (R72)."""
    return 'presentation:%s:%s:%d:%s' % (CHANNEL, request_id, request_version, digest.split(':', 1)[-1])


def head_id(request_id):
    return 'presentation-head:%s:%s' % (CHANNEL, request_id)


def framing_id(request_id):
    return 'presentation-framing:%s' % request_id


def answer_id(request_id, request_version, principal):
    """One answer per principal per request version: what settlement counts, by distinct principal."""
    return 'presentation-answer:%s:%d:%s' % (request_id, request_version, principal)


def answer_command_id(chat, message):
    return 'presentation-answer:%s:%d:%d' % (CHANNEL, chat, message)


def ruling_of(choice):
    return CHOICE_RULINGS.get(choice)


def _words(text):
    return ' '.join(str(text).split())


def authority_statement(request_id, request_version, owner, entry):
    """Who may answer and what an answer does, derived from the owner's current membership."""
    roles = ', '.join(sorted(entry.get('roles') or [])) or 'no roles'
    scope = entry.get('scope')
    scope = scope if isinstance(scope, str) else ', '.join(scope or [])
    return ('Only %s answers this, as a person member (%s) for scope %s. An answer names this presentation '
            'and settles request %s version %d once.' % (owner, roles, scope, request_id, request_version))


def render(record):
    """The exact bytes shown, from the receipt's own bound fields: plain text, no markup."""
    c = record['request']
    budget = ', '.join('%s=%s' % (unit, c['budget'][unit]) for unit in sorted(c['budget']))
    lines = ['Veldo needs your %s' % c['kind'].replace('_', ' '),
             'Request: %s' % record['request_id'],
             'Request version: %d' % record['request_version'],
             'Request digest: %s' % record['request_digest'],
             'Presentation version: %d' % record['presentation_version']]
    prior = record.get('supersedes')
    if prior:
        lines.append('Supersedes: presentation version %s, message %s. Only this message can be answered.'
                     % (prior['presentation_version'], prior['message_id']))
    lines += ['Owner: %s' % c['owner'],
              'Scope: %s' % ', '.join(c['scope']),
              'Deadline: %s' % c['deadline'],
              'Budget: %s' % budget,
              'Subject: %s' % '; '.join('%s %s %s' % (s['kind'], s['ref'], s['digest']) for s in record['subject_digests']),
              'Risk (stated by %s): %s' % (record['framed_by'], _words(record['risk_statement'])),
              'Authority: %s' % record['authority_statement'],
              'Choices: %s' % ' | '.join(record['choices']),
              '',
              _words(c['brief']),
              '',
              'Answer by replying to this message: <choice>: <your reason>']
    return '\n'.join(line.rstrip() for line in lines)


def receipt_problems(receipt, platform=None, retrieved=True):
    """Why a receipt does not bind what the owner was shown, by name. Every bound field is recomputed
    from the receipt's own request snapshot; `platform` is what the platform returns for the
    receipt's (chat, message): {'text', 'date'}, or None when it has nothing there. With
    `retrieved` false the receipt is checked on its own, without the platform."""
    if not isinstance(receipt, dict):
        return ['a receipt is a mapping']
    missing = [f for f in INTENT_FIELDS + ('outcome', 'external_id', 'published_at') if f not in receipt]
    if missing:
        return ['receipt lacks %s' % f for f in missing]
    problems = []
    try:
        if receipt['channel'] != CHANNEL or receipt['schema'] != SCHEMA:
            problems.append('receipt is not a %s %s receipt' % (SCHEMA, CHANNEL))
        if receipt['request_digest'] != request_digest(receipt['request_id'], receipt['request_version'], receipt['request']):
            problems.append('request digest does not cover the request identity, version and content')
        if receipt['subject_digests'] != subject_digests(receipt['request']):
            problems.append('subject digests are not the request subject')
        if receipt['choices'] != receipt['request'].get('choices'):
            problems.append('choices are not the request choices')
        if receipt['rulings'] != [ruling_of(c) for c in receipt['choices']]:
            problems.append('rulings are not the contract rulings of the choices')
        if receipt['rendered'] != render(receipt):
            problems.append('rendered bytes are not the rendering of the bound fields')
        if receipt['brief_digest'] != bytes_digest(receipt['rendered'].encode('utf-8')):
            problems.append('presentation digest is not the digest of the rendered bytes')
        if receipt['presentation_id'] != presentation_id(receipt['request_id'], receipt['request_version'], receipt['brief_digest']):
            problems.append('presentation id is not the key of request, version and presentation digest')
    except (KeyError, TypeError, AttributeError, ValueError):
        problems.append('receipt fields are malformed')
        return problems
    if receipt['outcome'] != 'published':
        return problems
    if (type(receipt.get('chat_id')) is not int or type(receipt.get('message_id')) is not int
            or receipt['external_id'] != '%s:%s' % (receipt.get('chat_id'), receipt.get('message_id'))):
        problems.append('external identity is not the platform chat and message')
    if receipt.get('platform_text') != receipt['rendered']:
        problems.append('the platform text is not the rendered bytes')
    if not retrieved:
        return problems
    if platform is None:
        problems.append('the platform holds no message at the recorded chat and message')
    else:
        if platform.get('text') != receipt['rendered']:
            problems.append('the platform message is not the rendered bytes')
        if platform.get('date') != receipt['published_at']:
            problems.append('publication time is not the platform date')
    return problems


def binding_mismatches(receipt, current):
    """The bound fields in which an answered receipt differs from current authority."""
    return [f for f in BOUND_FIELDS if receipt.get(f) != current.get(f)]


class TelegramPresentationEdge:
    """The Bot API sendMessage call for presentations. A replacement is sent as a reply to the
    message it supersedes. `projection` is the VELDO-0064 projection module, whose refusal
    classification is reused: only Telegram's own 4xx error answer proves nothing was published."""

    def __init__(self, projection, base_url, token, *, timeout=10):
        self.P = projection
        if not isinstance(base_url, str) or not base_url.startswith(('https://', 'http://127.0.0.1:')):
            raise projection.EdgeRefused('invalid_input', 'the Bot API origin is https, or a loopback test endpoint')
        if not isinstance(token, str) or not token:
            raise projection.EdgeRefused('invalid_input', 'a token is required')
        self.base_url, self._token, self.timeout = base_url.rstrip('/'), token, timeout

    def send(self, chat, text, reply_to=None):
        EdgeRefused = self.P.EdgeRefused
        if type(chat) is not int or (reply_to is not None and type(reply_to) is not int):
            raise EdgeRefused('invalid_input', 'a send names a numeric chat and an optional numeric message')
        payload = {'chat_id': chat, 'text': text, 'disable_web_page_preview': True}
        if reply_to is not None:
            payload['reply_parameters'] = {'message_id': reply_to, 'allow_sending_without_reply': False}
        request = urllib.request.Request('%s/bot%s/sendMessage' % (self.base_url, self._token),
                                         data=json.dumps(payload).encode(), method='POST',
                                         headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                answer = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if not 400 <= exc.code < 500 or not self.P.telegram_refusal(exc, exc.code):
                raise EdgeRefused('unknown_outcome', 'HTTP %d is not a definite refusal' % exc.code) from None
            raise EdgeRefused('channel_refused', 'HTTP %d' % exc.code) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            raise EdgeRefused('unknown_outcome', 'no readable platform answer (%s)' % type(exc).__name__) from None
        result = answer.get('result') if isinstance(answer, dict) and answer.get('ok') is True else None
        chat_obj = result.get('chat') if isinstance(result, dict) else None
        if (not isinstance(chat_obj, dict) or type(chat_obj.get('id')) is not int
                or type(result.get('message_id')) is not int or type(result.get('date')) is not int
                or not isinstance(result.get('text'), str)):
            raise EdgeRefused('unknown_outcome', 'platform answer lacks message identity')
        replied = result.get('reply_to_message')
        replied = replied.get('message_id') if isinstance(replied, dict) else None
        return {'chat_id': chat_obj['id'], 'message_id': result['message_id'], 'date': result['date'],
                'text': result['text'], 'reply_to_message_id': replied if type(replied) is int else None}


def _anomalies(record, platform):
    found = []
    if platform['text'] != record['rendered']:
        found.append('presentation_mismatch')
    if platform['chat_id'] != record['enrolled_chat']:
        found.append('chat_mismatch')
    if platform['reply_to_message_id'] != record['reply_to']:
        found.append('supersession_mismatch')
    return found


def _record_transition(params, before):
    """`intent` creates a receipt, or a new attempt of a refused one, as `pending`. `complete`
    finishes that attempt from the platform's answer; a confirmed publication moves the head in
    the same transaction. A completed receipt is never written again."""
    pid, hid, phase = params.get('presentation_id'), params.get('head_id'), params.get('phase')
    if not isinstance(pid, str) or not isinstance(hid, str) or phase not in ('intent', 'complete'):
        raise ValueError('a presentation record names its id, head and phase')
    current = before.get(pid, {}).get('data')
    if phase == 'intent':
        record = params.get('record')
        if not isinstance(record, dict) or set(record) != set(INTENT_FIELDS) or record['presentation_id'] != pid:
            raise ValueError('an intent carries exactly the presentation it binds')
        if current is not None and current.get('outcome') not in RETRYABLE:
            raise ValueError('a receipt is immutable; only a definite refusal is attempted again')
        data = dict(record, attempt=current['attempt'] + 1 if current else 1, outcome='pending', chat_id=None,
                    message_id=None, external_id=None, published_at=None, platform_text=None,
                    reply_to_message_id=None, refusal=None, anomalies=[])
        return {pid: {'kind': RECEIPT_KIND, 'data': data}}
    if current is None or current.get('outcome') != 'pending' or current.get('attempt') != params.get('attempt'):
        raise ValueError('a completion finishes the pending attempt it names')
    platform, refusal = params.get('platform'), params.get('refusal')
    data = dict(current)
    changes = {}
    if refusal is not None:
        if not isinstance(refusal, str) or platform is not None:
            raise ValueError('a refusal names its code and carries no platform answer')
        data.update(outcome='refused', refusal=refusal)
    elif platform is None:
        data.update(outcome='unknown_outcome')
    else:
        if (not isinstance(platform, dict) or set(platform) != set(PLATFORM_FIELDS)
                or not all(type(platform[k]) is int for k in ('chat_id', 'message_id', 'date'))
                or not isinstance(platform['text'], str)
                or not (platform['reply_to_message_id'] is None or type(platform['reply_to_message_id']) is int)):
            raise ValueError('a platform answer carries its chat, message, date, text and reply')
        found = _anomalies(data, platform)
        data.update(outcome='anomaly' if found else 'published', chat_id=platform['chat_id'],
                    message_id=platform['message_id'], external_id='%d:%d' % (platform['chat_id'], platform['message_id']),
                    published_at=platform['date'], platform_text=platform['text'],
                    reply_to_message_id=platform['reply_to_message_id'], anomalies=found)
    if data['outcome'] == 'published':
        head = before.get(hid, {}).get('data') or {}
        prior = (data['supersedes'] or {}).get('presentation_id')
        if head.get('current') != prior:
            raise ValueError('the presentation this one supersedes is no longer current')
        superseded = dict(head.get('superseded') or {})
        if prior:
            superseded[prior] = pid
        changes[hid] = {'kind': HEAD_KIND, 'data': {
            'schema': HEAD_SCHEMA, 'channel': CHANNEL, 'request_id': data['request_id'], 'current': pid,
            'presentation_version': data['presentation_version'],
            'published': list(head.get('published') or []) + [pid], 'superseded': superseded}}
    changes[pid] = {'kind': RECEIPT_KIND, 'data': data}
    return changes


def _write_new(params, before, kinds):
    """Create each named entity exactly once."""
    changes = {}
    for key, kind in kinds:
        eid, data = params.get(key + '_id'), params.get(key)
        if not isinstance(eid, str) or not isinstance(data, dict) or eid in before:
            raise ValueError('%s %r already exists or is malformed' % (kind, eid))
        changes[eid] = {'kind': kind, 'data': data}
    return changes


class Presenter:
    """Presents one inbox on Telegram, keeps the receipts and decides presentation-bound answers.

    `store`, `membership`, `projection` and `assignment` are the control_store, control_membership,
    control_channel_projection and control_assignment modules; `inbox` is the VELDO-0064 Inbox on the
    same connection, whose KINDS give each assignment kind the assertion kind an answer carries.
    `sign(bytes) -> text` signs journal records as `journal_signer`. Observations record identity,
    accepted versions and outcome, never rendered text, rationale, signatures or the token."""

    def __init__(self, store, membership, projection, inbox, edge, conn, journal_signer, sign,
                 authority_generation=1, clock=time.time, *, assignment):
        self.store, self.membership, self.P, self.inbox, self.edge = store, membership, projection, inbox, edge
        self.assignment = assignment
        self.AC = membership.AC
        self.conn, self.ids = conn, dict(inbox.ids)
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation, self.clock = authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._serial = 0

        def guarded(fn):
            def transition(params, before):
                try:
                    return fn(params, before)
                except ValueError as exc:
                    raise store.StoreRefused('invalid_input', str(exc))
            return transition
        writes = ('entities', 'journal', 'commands', 'nonces')
        conn.command_registry[RECORD_OPERATION] = {'transition': guarded(_record_transition), 'writes': writes}
        conn.command_registry[FRAME_OPERATION] = {'transition': guarded(self._frame_transition), 'writes': writes}
        conn.command_registry[ANSWER_OPERATION] = {
            'transition': guarded(lambda p, b: _write_new(p, b, (('answer', ANSWER_KIND),))),
            'writes': writes}

    # reading

    def _entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def _data(self, eid, kind):
        e = self._entity(eid)
        return None if e is None or e['kind'] != kind else dict(e['data'], entity_version=e['version'])

    def receipt(self, pid):
        return self._data(pid, RECEIPT_KIND)

    def head(self, request):
        return self._data(head_id(request), HEAD_KIND)

    def current(self, request):
        """The current confirmed presentation of a request on this channel, or None."""
        h = self.head(request)
        return self.receipt(h['current']) if h else None

    def receipts(self, request):
        rows = self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (RECEIPT_KIND,)).fetchall()
        return [json.loads(r[0]) for r in rows if json.loads(r[0]).get('request_id') == request]

    def receipt_for_message(self, chat, message):
        for (text,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (RECEIPT_KIND,)):
            data = json.loads(text)
            if data.get('outcome') == 'published' and data.get('chat_id') == chat and data.get('message_id') == message:
                return data
        return None

    def answer_record(self, request, version, principal):
        return self._data(answer_id(request, version, principal), ANSWER_KIND)

    def _observe(self, operation, request, versions, outcome, reason, **extra):
        accepted = outcome in ('accepted', 'published', 'already_presented', 'answered')
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.ids, operation=operation, channel=CHANNEL, request_id=request,
                                      accepted_versions=versions, outcome=outcome, reason=reason,
                                      error_class=None if accepted else 'unknown_outcome' if outcome == 'unknown_outcome'
                                      else REFUSALS.get(reason, 'unavailable_service'), **extra))
        result = dict({'request_id': request, 'outcome': outcome}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    def bindings(self, request):
        """(refusal, bindings, versions): what a presentation of `request` must bind now, from
        current authority only: the pending assignment, its framing at this request version, the
        owner's membership and the owner's enrolled chat."""
        brief = self.inbox.brief(request)
        if not brief.get('valid') or brief.get('category') != 'pending':
            return 'stale_subject', None, {}
        c = brief['content']
        versions = {request: brief['version'], self.membership.VERSIONS_ENTITY:
                    (self._entity(self.membership.VERSIONS_ENTITY) or {}).get('version', 0)}
        framing = self._entity(framing_id(request))
        versions[framing_id(request)] = framing['version'] if framing else 0
        fdata = framing['data'] if framing and framing['kind'] == FRAMING_KIND else {}
        state = self.membership.authority_state(self.store, self.conn)
        if (fdata.get('request_version') != c['request_version'] or not _is_str(fdata.get('risk_statement'))
                or not self._framing_signed(request, framing, state, c)):
            return 'missing_framing', None, versions
        entry = self.AC.membership_entry(state['membership'], c['owner'])
        active, _ = self.AC.active_member(entry, self.clock())
        if not active or entry['principal_type'] != 'person' or not self.membership.scope_covers(entry.get('scope'), c['scope']):
            return 'missing_authority', None, versions
        versions[c['owner']] = entry['entity_version']
        eid = self.P.enrollment_id(c['owner'])
        enrollment = self._entity(eid)
        if enrollment is None:
            return 'no_enrolled_chat', None, versions
        if self.P.enrollment_problems(enrollment['kind'], enrollment['data'], c['owner']):
            return 'invalid_enrollment', None, versions
        versions[eid] = enrollment['version']
        content = {k: c.get(k) for k in REQUEST_FIELDS}
        rulings = [ruling_of(choice) for choice in c['choices']]
        acknowledgement = self.assignment.KINDS.get(c['kind']) == 'acknowledgement'
        if not all(r == 'acknowledged' if acknowledgement else r in self.AC.RULINGS for r in rulings):
            return 'unmapped_choice', None, versions
        return None, {
            'request_id': request, 'request_version': c['request_version'], 'assignment_version': brief['version'],
            'request': content, 'request_digest': request_digest(request, c['request_version'], content),
            'subject_digests': subject_digests(content), 'risk_statement': fdata['risk_statement'],
            'framing_id': framing_id(request), 'framing_version': framing['version'], 'framed_by': fdata['framed_by'],
            'authority_statement': authority_statement(request, c['request_version'], c['owner'], entry),
            'choices': list(c['choices']), 'rulings': rulings, 'owner': c['owner'], 'enrollment_id': eid,
            'enrollment_version': enrollment['version'], 'enrolled_chat': enrollment['data']['chat_id']}, versions

    # framing: the requester's signed risk statement

    def _frame_transition(self, params, before):
        fid, request = params.get('framing_id'), params.get('request_id')
        framing = params.get('framing')
        if not isinstance(framing, dict) or fid != framing_id(request):
            raise ValueError('a framing names its request')
        current = before.get(request, {}).get('data') or {}
        if current.get('request_version') != framing.get('request_version'):
            raise ValueError('the framing names another request version')
        return {fid: {'kind': FRAMING_KIND, 'data': framing}}

    def _framing_signed(self, request, framing, state, content):
        """Whether a stored framing counts. It re-verifies, from the store's own records, everything
        frame() checked: the entity's current version was written by the registered frame operation
        with exactly this framing (the journal record's command digest is recomputed from the framing
        and the versions it pinned, so a framing written by any other store command frames nothing);
        the signed command is the frame command for this request and version, with this statement,
        by the requester; the requester is still an active member entitled to propose in the
        request's scope; and the signature verifies with the requester's key as it stood when the
        STORE accepted the command (the publication record's committed time, never a field the
        writer supplies). A revocation dated at or before that acceptance refuses; a later one
        strands nothing."""
        fid, data, version = framing_id(request), framing['data'], framing['version']
        signed = data.get('signed') if isinstance(data.get('signed'), dict) else {}
        command, signature = signed.get('command'), signed.get('signature')
        principal = data.get('framed_by')
        if (not isinstance(command, dict) or not isinstance(signature, str) or not signature.isascii()
                or principal != content['requested_by'] or command.get('principal') != principal
                or command.get('operation') != 'frame' or not _is_str(command.get('alias'))
                or self.inbox_request(command['alias']) != request
                or command.get('request_version') != data.get('request_version')
                or _words(command.get('risk_statement', '')) != data.get('risk_statement')
                or command.get('command_id') != data.get('command_id')
                or any(command.get(k) != v for k, v in self.ids.items())
                or not isinstance(data.get('expected_versions'), dict)):
            return False
        written = None
        for seq, command_id, digest, transition in self.conn.execute(
                'SELECT seq, command_id, command_digest, transition FROM journal WHERE instr(transition, ?) > 0 '
                'ORDER BY seq DESC', (json.dumps(fid),)):
            entry = json.loads(transition).get(fid)
            if entry is not None:
                written = (seq, command_id, digest, entry)
                break
        if (written is None or written[3].get('version') != version
                or written[3].get('digest') != self.store.digest_of({'kind': FRAMING_KIND, 'data': data, 'version': version})):
            return False
        accepted_by = dict(command_id=written[1], principal=principal, operation=FRAME_OPERATION,
                           parameters=dict(framing_id=fid, request_id=request, framing=data),
                           expected_versions=data['expected_versions'], artifact_digests=[], nonce=command.get('nonce'))
        if written[1] != command['command_id'] or self.store.command_digest(accepted_by) != written[2]:
            return False
        publication = self.store.publication_row_for_command(self.conn, written[1]) or {}
        at = publication.get('committed_at')
        if type(at) not in (int, float):
            return False
        key = next((k for k in state['keyring'] if k.get('key_id') == data.get('key_id')
                    and k.get('principal') == principal and _is_str(k.get('public_key'))), None)
        if key is None or self.AC.active_key([key], principal, at) is None:
            return False
        entry = self.AC.membership_entry(state['membership'], principal)
        if (not self.AC.active_member(entry, self.clock())[0]
                or entry['principal_type'] not in self.AC.BOUNDARIES['proposal_commit']
                or not self.membership.scope_covers(entry.get('scope'), content['scope'])):
            return False
        return self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), signature,
                                         self.AC.allowed_signers_line(principal, key['public_key']), principal)[0]

    def frame(self, packet):
        """Record the risk statement the requester signed for the current request version. Only the
        requester frames: no one else, a project owner included, replaces what the requester stated.
        A changed statement makes the current presentation stale."""
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        request = None
        try:
            if not isinstance(packet, dict) or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii():
                raise Refused('invalid_input', 'a framing is a signed command')
            required = ('alias', 'principal', 'command_id', 'nonce', 'risk_statement')
            if (command.get('operation') != 'frame' or not all(_is_str(command.get(k)) for k in required)
                    or any(command.get(k) != v for k, v in self.ids.items())):
                raise Refused('invalid_input', 'invalid framing command or authority coordinates')
            request = self.inbox_request(command['alias'])
            principal, now = command['principal'], self.clock()
            state = self.membership.authority_state(self.store, self.conn)
            key = self.AC.active_key(state['keyring'], principal, now)
            if not key or not self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                         self.AC.allowed_signers_line(principal, key['public_key']),
                                                         principal)[0]:
                raise Refused('not_authorized', 'the framing signature does not verify')
            brief = self.inbox.brief(request)
            if not brief.get('valid') or brief.get('category') != 'pending':
                raise Refused('stale_subject', 'only a pending request is framed')
            c = brief['content']
            if command.get('request_version') != c['request_version']:
                raise Refused('stale_subject', 'the framing names another request version')
            entry = self.AC.membership_entry(state['membership'], principal)
            active, _ = self.AC.active_member(entry, now)
            if (not active or entry['principal_type'] not in self.AC.BOUNDARIES['proposal_commit']
                    or not self.membership.scope_covers(entry.get('scope'), c['scope'])
                    or principal != c['requested_by']):
                raise Refused('not_authorized', 'only the requester frames a request')
            fid = framing_id(request)
            versions = {request: brief['version'], fid: (self._entity(fid) or {}).get('version', 0),
                        principal: entry['entity_version'], key['key_id']: (self._entity(key['key_id']) or {}).get('version', 0),
                        self.membership.VERSIONS_ENTITY: (self._entity(self.membership.VERSIONS_ENTITY) or {}).get('version', 0)}
            framing = {'schema': FRAMING_SCHEMA, 'request_id': request, 'request_version': c['request_version'],
                       'risk_statement': _words(command['risk_statement']), 'framed_by': principal,
                       'command_id': command['command_id'], 'key_id': key['key_id'], 'expected_versions': versions,
                       'signed': {'command': command, 'signature': packet['signature']}}
            self.store.execute(self.conn, dict(command_id=command['command_id'], principal=principal,
                                               operation=FRAME_OPERATION,
                                               parameters=dict(framing_id=fid, request_id=request, framing=framing),
                                               expected_versions=versions, artifact_digests=[], nonce=command['nonce']),
                               self.journal_signer, self.sign, self.authority_generation)
        except (Refused, self.store.StoreRefused) as exc:
            return self._observe('frame', request, {}, 'refused', exc.code)
        except sqlite3.Error:
            return self._observe('frame', request, {}, 'refused', 'unavailable_service')
        return self._observe('frame', request, versions, 'accepted', None)

    def inbox_request(self, alias):
        return 'assignment:%s:%s' % (self.ids['repository_uuid'], alias)

    # publication

    def _commit(self, operation, params, expected, principal=None, command_id=None):
        self._serial += 1
        command_id = command_id or '%s:%s:%s:%.6f:%d' % (operation, params.get('phase', ''), params.get('presentation_id', ''),
                                                        self.clock(), self._serial)
        command = dict(command_id=command_id, principal=principal or self.journal_signer, operation=operation,
                       parameters=params, expected_versions=expected, artifact_digests=[], nonce=command_id)
        return self.store.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)

    def _send(self, chat, text, reply_to):
        try:
            sent = self.edge.send(chat, text, reply_to)
        except self.P.EdgeRefused as exc:
            unknown = exc.code == 'unknown_outcome'
            return {'platform': None, 'refusal': None if unknown else exc.code}
        except Exception:
            return {'platform': None, 'refusal': None}
        return {'platform': sent, 'refusal': None}

    def compose(self, request):
        """(refusal, record, versions): the presentation current authority requires now. The
        record is None when the current presentation still binds current authority."""
        refusal, b, versions = self.bindings(request)
        if refusal:
            return refusal, None, versions
        hid = head_id(request)
        head = self.head(request)
        versions[hid] = head['entity_version'] if head else 0
        prior = self.receipt(head['current']) if head else None
        if prior is not None and not binding_mismatches(prior, b):
            return None, None, versions
        record = dict(b, schema=SCHEMA, channel=CHANNEL, presentation_version=(head or {}).get('presentation_version', 0) + 1,
                      supersedes=None, reply_to=None)
        if prior:
            record['supersedes'] = {'presentation_id': prior['presentation_id'],
                                    'presentation_version': prior['presentation_version'],
                                    'chat_id': prior['chat_id'], 'message_id': prior['message_id']}
            record['reply_to'] = prior['message_id'] if prior['chat_id'] == b['enrolled_chat'] else None
        record['rendered'] = render(record)
        record['brief_digest'] = bytes_digest(record['rendered'].encode('utf-8'))
        record['presentation_id'] = presentation_id(request, b['request_version'], record['brief_digest'])
        return None, record, versions

    def present(self, request):
        """Present one request as current authority requires: nothing when its current presentation
        already is that, never again when an earlier attempt's outcome is unknown."""
        refusal, record, versions = self.compose(request)
        if refusal:
            return self._observe('publish', request, versions, 'refused', refusal)
        if record is None:
            return self._observe('publish', request, versions, 'already_presented', None,
                                 presentation_id=self.head(request)['current'])
        pid, hid = record['presentation_id'], head_id(request)
        if self.answer_record(request, record['request_version'], record['owner']):
            return self._observe('publish', request, versions, 'answered', None, presentation_id=pid)
        existing = self.receipt(pid)
        if existing is not None and existing['outcome'] not in RETRYABLE:
            outcome = SETTLED_OUTCOMES.get(existing['outcome'], 'anomaly')
            reason = ','.join(existing['anomalies']) if outcome == 'anomaly' else 'unknown_outcome'
            return self._observe('publish', request, versions, outcome, reason, presentation_id=pid)
        try:
            self._commit(RECORD_OPERATION, dict(phase='intent', presentation_id=pid, head_id=hid, record=record),
                         dict(versions, **{pid: existing['entity_version'] if existing else 0}))
        except self.store.StoreRefused as exc:
            return self._observe('publish', request, versions, 'refused', exc.code, presentation_id=pid)
        intent = self.receipt(pid)
        completion = self._send(record['enrolled_chat'], record['rendered'], record['reply_to'])
        try:
            self._commit(RECORD_OPERATION, dict(phase='complete', presentation_id=pid, head_id=hid,
                                                attempt=intent['attempt'], **completion),
                         {pid: intent['entity_version'], hid: versions[hid]})
        except self.store.StoreRefused as exc:
            return self._observe('publish', request, versions, 'unknown_outcome', exc.code, presentation_id=pid)
        done = self.receipt(pid)
        reason = {'published': None, 'refused': done['refusal'], 'unknown_outcome': 'unknown_outcome'}.get(
            done['outcome'], ','.join(done['anomalies']))
        return self._observe('publish', request, versions, done['outcome'], reason, presentation_id=pid)

    def publish(self):
        """Present every pending inbox entry whose current presentation is not the one current
        authority requires; return one result per pending entry."""
        return [self.present(e['id']) for e in self.inbox.index()['entries'] if e['category'] == 'pending']

    # answers

    def canonical_answer(self, message, edge_principal):
        """The canonical assertion the Telegram edge signs for one owner reply, from the Bot API
        message object the platform delivered: its own message id, sender id, date, chat and the
        presentation message it replies to. Text is `<choice>: <reason>`. Automation refuses."""
        sender, chat = message.get('from') or {}, message.get('chat') or {}
        reply = message.get('reply_to_message') or {}
        if sender.get('is_bot') is not False:
            raise Refused('not_owner', 'an answer comes from a person, never from automation')
        receipt = self.receipt_for_message(chat.get('id'), reply.get('message_id'))
        if receipt is None:
            raise Refused('unknown_presentation', 'the reply addresses no published presentation')
        choice, _, rationale = (message.get('text') or '').partition(':')
        choice = choice.strip()
        return dict(self.ids, schema=ANSWER_SCHEMA, channel=CHANNEL,
                    assertion_kind=self.assignment.KINDS.get(receipt['request']['kind']),
                    authority_scope=list(receipt['request']['scope']),
                    edge_principal=edge_principal, edge_key_id=self.AC.CHANNELS[CHANNEL]['edge_key_id'],
                    principal=receipt['owner'], request_id=receipt['request_id'],
                    request_version=receipt['request_version'], presentation_id=receipt['presentation_id'],
                    presentation_digest=receipt['brief_digest'], presentation_version=receipt['presentation_version'],
                    choice=choice, ruling=ruling_of(choice), rationale=_words(rationale),
                    attribution={'platform_message_id': message.get('message_id'), 'sender_id': sender.get('id'),
                                 'platform_timestamp': message.get('date'), 'chat_id': chat.get('id'),
                                 'reply_to_message_id': reply.get('message_id')})

    def _edge_key(self, state, edge, now):
        wanted = self.AC.CHANNELS[CHANNEL]['edge_key_id']
        keys = [k for k in state['keyring'] if k.get('key_id') == wanted]
        return self.AC.active_key(keys, edge, now)

    def answer(self, packet):
        """Decide one signed canonical Telegram answer; settle the request version on acceptance."""
        a = packet.get('assertion') if isinstance(packet, dict) else None
        a = a if isinstance(a, dict) else {}
        try:
            result = self._answer(packet, a)
        except Refused as exc:
            return self._observe('answer', a.get('request_id'), {}, 'refused', exc.code,
                                 presentation_id=a.get('presentation_id'))
        except self.store.StoreRefused as exc:
            # An input read for the decision changed before the commit, or the answer was written
            # first by another command: nothing was written by this one.
            reason = {'stale_version': 'stale_subject', 'invalid_input': 'already_answered'}.get(exc.code, exc.code)
            return self._observe('answer', a.get('request_id'), {}, 'refused', reason,
                                 presentation_id=a.get('presentation_id'))
        except sqlite3.Error:
            return self._observe('answer', a.get('request_id'), {}, 'refused', 'unavailable_service')
        return result

    def _answer(self, packet, a):
        if not isinstance(packet, dict) or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii():
            raise Refused('invalid_input', 'an answer is a signed canonical assertion')
        if (a.get('schema') != ANSWER_SCHEMA or a.get('channel') != CHANNEL
                or not _is_str(a.get('edge_principal')) or any(a.get(k) != v for k, v in self.ids.items())):
            raise Refused('invalid_input', 'not a canonical Telegram answer for this authority')
        edge, now = a['edge_principal'], self.clock()
        state = self.membership.authority_state(self.store, self.conn)
        key = self._edge_key(state, edge, now)
        if key is None or a.get('edge_key_id') != key['key_id']:
            raise Refused('not_authorized', 'the edge signs only with the channel\'s restricted key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(a), packet['signature'],
                                                self.AC.allowed_signers_line(edge, key['public_key']), edge)
        if not verified:
            raise Refused('not_authorized', 'the answer signature does not verify')
        edge_entry = self.AC.membership_entry(state['membership'], edge)
        if not self.AC.active_member(edge_entry, now)[0] or edge_entry['principal_type'] != 'service':
            raise Refused('not_authorized', 'the edge is not an active service member')
        if not all(a.get(k) is not None for k in REFERENCE_FIELDS):
            raise Refused('missing_presentation', 'an answer names the presentation it addresses')
        pid = a['presentation_id']
        receipt = self.receipt(pid) if isinstance(pid, str) else None
        if receipt is None or any(a.get(k) != receipt[f] for k, f in (
                ('presentation_digest', 'brief_digest'), ('presentation_version', 'presentation_version'),
                ('request_id', 'request_id'), ('request_version', 'request_version'), ('channel', 'channel'))):
            raise Refused('unknown_presentation', 'no receipt is the presentation this answer names')
        if receipt['outcome'] != 'published':
            raise Refused('unseen_presentation', 'the named presentation has no confirmed publication')
        if receipt_problems(receipt, retrieved=False):
            raise Refused('unknown_presentation', 'the named receipt does not bind its own shown bytes')
        ev = a.get('attribution') if isinstance(a.get('attribution'), dict) else {}
        if (not all(type(ev.get(f)) is int for f in ATTRIBUTION_FIELDS)
                or ev['chat_id'] != receipt['chat_id'] or ev['reply_to_message_id'] != receipt['message_id']):
            raise Refused('evidence_mismatch', 'the platform evidence does not reply to the named presentation message')
        if ev['platform_timestamp'] < receipt['published_at']:
            raise Refused('answer_before_publication', 'the platform dates the answer before the presentation it answers')
        if ev['sender_id'] != receipt['enrolled_chat'] or a.get('principal') != receipt['owner']:
            raise Refused('not_owner', 'the sender is not the owner the presentation was shown to')
        request = receipt['request_id']
        head = self.head(request)
        if head is None or head['current'] != pid:
            raise Refused('superseded_presentation', 'the named presentation is not the current one')
        refusal, current, versions = self.bindings(request)
        if refusal or binding_mismatches(receipt, current):
            raise Refused('stale_presentation', 'the named presentation no longer binds the current request')
        if not self.membership.scope_covers(edge_entry.get('scope'), receipt['request']['scope']):
            raise Refused('not_authorized', 'the edge scope does not cover the request')
        # The assertion is what authority_contract.settle reads: its kind, ruling and scope must be
        # the ones this request and its offered choice give, spelled in the contract vocabulary.
        if (a.get('choice') not in receipt['choices'] or a.get('ruling') != ruling_of(a.get('choice'))
                or a.get('assertion_kind') != self.assignment.KINDS.get(receipt['request']['kind'])
                or a.get('authority_scope') != list(receipt['request']['scope'])):
            raise Refused('invalid_input', 'the choice is not offered, or its ruling, kind or scope is not the contract\'s')
        if not _is_str(a.get('rationale')):
            raise Refused('missing_rationale', 'an answer records its rationale')
        aid = answer_id(request, receipt['request_version'], receipt['owner'])
        if self._entity(aid) is not None:
            raise Refused('already_answered', 'the owner has answered this request version')
        versions.update({pid: receipt['entity_version'], head_id(request): head['entity_version'], aid: 0,
                         edge: edge_entry['entity_version'], key['key_id']: (self._entity(key['key_id']) or {}).get('version', 0)})
        answer = {'schema': ANSWER_SCHEMA, 'channel': CHANNEL, 'request_id': request,
                  'request_version': receipt['request_version'], 'request_digest': receipt['request_digest'],
                  'presentation_id': pid, 'presentation_digest': receipt['brief_digest'],
                  'presentation_version': receipt['presentation_version'], 'principal': receipt['owner'],
                  'assertion_kind': a['assertion_kind'], 'choice': a['choice'], 'ruling': a['ruling'],
                  'rationale': a['rationale'], 'attribution': dict(ev),
                  'edge_principal': edge, 'edge_key_id': key['key_id'],
                  'assertion': a, 'signature': packet['signature'], 'accepted_at': now}
        self._commit(ANSWER_OPERATION, dict(answer_id=aid, answer=answer), versions, principal=edge,
                     command_id=answer_command_id(ev['chat_id'], ev['platform_message_id']))
        return self._observe('answer', request, versions, 'accepted', None, presentation_id=pid, answer_id=aid,
                             ruling=a['ruling'])

    def metrics(self):
        """Accepted and refused operations, pending entries not presented as current authority
        requires, and receipts whose outcome is unknown or anomalous."""
        pending = 0
        for entry in self.inbox.index()['entries']:
            if entry['category'] != 'pending' or self.answer_record(entry['id'], entry['request_version'], entry['owner']):
                continue
            refusal, record, _ = self.compose(entry['id'])
            if refusal or record is not None:
                pending += 1
        rows = [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM entities WHERE kind=?', (RECEIPT_KIND,))]
        return dict(self.counts, pending=pending,
                    unknown=sum(1 for r in rows if r.get('outcome') in ('pending', 'unknown_outcome')),
                    anomalies=sum(1 for r in rows if r.get('outcome') == 'anomaly'))
