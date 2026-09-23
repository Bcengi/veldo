"""Telegram projection of the assignment inbox with durable message correlation (VELDO-0064).

WHAT THIS MODULE IS. The ordinary outbound Telegram projection of pending person assignments.
For every valid pending inbox entry that has no projection at its current request version, it
renders the presentation bytes from the inbox brief and keeps one `channel_projection` entity
per (assignment, request version). The record binds the assignment id, the entity version and the
request version presented, and the digest of the exact bytes. A changed request version is a new
presentation and a new message.

INTENT BEFORE SEND. The record is committed as a `pending` intent BEFORE the message is sent
through the Telegram Bot API `sendMessage` method, and a second store command completes it with
what the platform returned: its chat identity, its message identity, its date and the text it
stored. If the intent cannot be written, nothing is sent. If the completion cannot be written,
the intent stays `pending`: its outcome is unknown and it is never sent again automatically,
by this run or any later one, whatever projector finds it. Only a definite platform refusal
(`refused`: the platform answered and published nothing) is attempted again, as a new attempt
of the same record.

WHAT THE PLATFORM SAID IS WHAT IS KEPT. The chat identity recorded is the one the platform
returned, not the configured address (Telegram accepts `@name` and answers with the numeric
chat id). A response whose echoed text differs from the bytes sent is refused. A transport
failure after the request may have reached the platform is recorded as `unknown_outcome` with
no message identity, so nothing is blindly sent again; looking the message up and recovering an
unknown or pending record is Release 2 work.

NOT AUTHORITY. A projection is a proxy of the inbox. Nothing here reads an answer, settles a
request or changes an assignment. Presentation receipts and supersession are VELDO-0065, answer
acquisition and attribution VELDO-0066, edge signing VELDO-0067, activation of the live edge
VELDO-0073. The bot token is supplied by the caller's custody and never logged or stored.
Standard library only.
"""
import hashlib
import json
import time
import urllib.error
import urllib.request

SCHEMA = 'veldo.channel_projection/v1'
ENTITY_KIND = 'channel_projection'
OPERATION = 'channel_projection_record'
CHANNEL = 'telegram_chat'
# The outcomes of one record. `pending` is the committed intent before the send completes.
OUTCOMES = ('pending', 'sent', 'refused', 'unknown_outcome')
# Only a definite refusal, where the platform answered and published nothing, is attempted again.
RETRYABLE = ('refused',)
INTENT_FIELDS = ('schema', 'channel', 'assignment_id', 'assignment_version', 'request_version',
                 'presentation_digest', 'presentation', 'configured_chat')
PLATFORM_FIELDS = ('chat_id', 'message_id', 'date', 'text')
# What a record that is not attempted again reports on a later run.
SETTLED = {'sent': ('already_projected', None), 'pending': ('unknown_outcome', 'incomplete_projection'),
           'unknown_outcome': ('unknown_outcome', 'unknown_outcome')}


class EdgeRefused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def presentation_digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def projection_id(assignment, request_version):
    return 'projection:%s:%s:%d' % (CHANNEL, assignment, request_version)


def render(brief):
    """The exact presentation text for one valid brief: plain text, no markup, no trailing space.
    Owner, scope, deadline and budget are shown as the inbox holds them."""
    c = brief['content']
    budget = ', '.join('%s=%s' % (unit, c['budget'][unit]) for unit in sorted(c['budget']))
    lines = [
        'Veldo needs your %s' % c['kind'].replace('_', ' '),
        'Assignment: %s' % brief['id'],
        'Request version: %d' % c['request_version'],
        'Owner: %s' % c['owner'],
        'Scope: %s' % ', '.join(c['scope']),
        'Deadline: %s' % c['deadline'],
        'Budget: %s' % budget,
        'Subject: %s %s %s' % (c['subject']['kind'], c['subject']['ref'], c['subject']['digest']),
        'Choices: %s' % ' | '.join(c['choices']),
        '',
        ' '.join(c['brief'].split()),
    ]
    return '\n'.join(line.rstrip() for line in lines)


class TelegramEdge:
    """The Bot API sendMessage call. `base_url` is the Bot API origin; `chat` is the configured
    owner chat address; `token` comes from the caller's secret custody."""

    def __init__(self, base_url, token, chat, timeout=10):
        if not isinstance(base_url, str) or not base_url.startswith(('https://', 'http://127.0.0.1:')):
            raise EdgeRefused('invalid_input', 'the Bot API origin is https, or a loopback test endpoint')
        if not isinstance(token, str) or not token or not chat:
            raise EdgeRefused('invalid_input', 'a token and a chat are required')
        self.base_url, self._token, self.chat, self.timeout = base_url.rstrip('/'), token, chat, timeout

    def send(self, text):
        body = json.dumps({'chat_id': self.chat, 'text': text, 'disable_web_page_preview': True}).encode()
        request = urllib.request.Request('%s/bot%s/sendMessage' % (self.base_url, self._token), data=body,
                                         method='POST', headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                answer = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            # The platform answered and refused: nothing was published.
            raise EdgeRefused('channel_refused', 'HTTP %d' % exc.code) from None
        except (urllib.error.URLError, OSError, ValueError):
            raise EdgeRefused('unknown_outcome', 'no readable platform answer') from None
        result = answer.get('result') if isinstance(answer, dict) and answer.get('ok') is True else None
        chat = result.get('chat') if isinstance(result, dict) else None
        if (not isinstance(chat, dict) or type(chat.get('id')) is not int
                or type(result.get('message_id')) is not int or type(result.get('date')) is not int
                or not isinstance(result.get('text'), str)):
            raise EdgeRefused('unknown_outcome', 'platform answer lacks message identity')
        return {'chat_id': chat['id'], 'message_id': result['message_id'], 'date': result['date'],
                'text': result['text']}


def _record_transition(params, before):
    """The two registered phases of one record. `intent` creates the record, or starts a new
    attempt of a refused one, as `pending`. `complete` finishes that pending attempt from the
    platform's answer: a definite refusal, no answer at all (unknown), or the returned identity."""
    pid, phase = params.get('projection_id'), params.get('phase')
    if not isinstance(pid, str) or phase not in ('intent', 'complete'):
        raise ValueError('a projection record names its id and phase')
    current = before.get(pid, {}).get('data')
    if phase == 'intent':
        record = params.get('record')
        if not isinstance(record, dict) or set(record) != set(INTENT_FIELDS):
            raise ValueError('an intent carries exactly the presentation it binds')
        if current is not None and current.get('outcome') not in RETRYABLE:
            raise ValueError('only a definite refusal is attempted again')
        data = dict(record, attempt=current['attempt'] + 1 if current else 1, outcome='pending', chat_id=None,
                    message_id=None, platform_date=None, platform_text=None, refusal=None)
        return {pid: {'kind': ENTITY_KIND, 'data': data}}
    if current is None or current.get('outcome') != 'pending' or current.get('attempt') != params.get('attempt'):
        raise ValueError('a completion finishes the pending attempt it names')
    platform, refusal = params.get('platform'), params.get('refusal')
    data = dict(current)
    if refusal is not None:
        if not isinstance(refusal, str) or platform is not None:
            raise ValueError('a refusal names its code and carries no platform answer')
        data.update(outcome='refused', refusal=refusal)
    elif platform is None:
        data.update(outcome='unknown_outcome')
    else:
        if (not isinstance(platform, dict) or set(platform) != set(PLATFORM_FIELDS)
                or not all(type(platform[k]) is int for k in ('chat_id', 'message_id', 'date'))
                or not isinstance(platform['text'], str)):
            raise ValueError('a platform answer carries its chat, message, date and text')
        data.update(outcome='sent', chat_id=platform['chat_id'], message_id=platform['message_id'],
                    platform_date=platform['date'], platform_text=platform['text'])
    return {pid: {'kind': ENTITY_KIND, 'data': data}}


class Projection:
    """Projects one inbox to one Telegram edge and records correlation through the store."""

    def __init__(self, store, inbox, edge, conn, journal_signer, sign, authority_generation=1, clock=time.time):
        self.store, self.inbox, self.edge, self.conn = store, inbox, edge, conn
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation, self.clock = authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._serial = 0

        def transition(params, before):
            try:
                return _record_transition(params, before)
            except ValueError as exc:
                raise store.StoreRefused('invalid_input', str(exc))
        conn.command_registry[OPERATION] = {'transition': transition,
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}

    def _result(self, assignment, versions, outcome, reason, **extra):
        accepted = outcome in ('sent', 'already_projected')
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.inbox.ids, operation='project', channel=CHANNEL,
                                      assignment_id=assignment, accepted_versions=versions,
                                      outcome=outcome, reason=reason, **extra))
        result = dict({'assignment_id': assignment, 'outcome': outcome}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    def record(self, pid):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=? AND kind=?',
                                (pid, ENTITY_KIND)).fetchone()
        return None if row is None else dict(json.loads(row[1]), entity_version=row[0])

    def correlation(self, assignment):
        """The projection records of one assignment, by request version."""
        rows = self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (ENTITY_KIND,)).fetchall()
        records = [json.loads(r[0]) for r in rows]
        return {r['request_version']: r for r in records if r.get('assignment_id') == assignment}

    def _commit(self, params, expected):
        """One store command of one phase; returns the record it committed."""
        self._serial += 1
        pid = params['projection_id']
        command_id = '%s:%s:%s:%.6f:%d' % (OPERATION, params['phase'], pid, self.clock(), self._serial)
        command = dict(command_id=command_id, principal=self.journal_signer, operation=OPERATION,
                       parameters=params, expected_versions=expected, artifact_digests=[], nonce=command_id)
        self.store.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)
        return self.record(pid)

    def _send(self, text):
        """What the platform said, as the completion parameters of the pending attempt."""
        try:
            sent = self.edge.send(text)
        except EdgeRefused as exc:
            return {'platform': None, 'refusal': None if exc.code == 'unknown_outcome' else exc.code}
        if sent['text'].encode('utf-8') != text.encode('utf-8'):
            return {'platform': None, 'refusal': 'presentation_mismatch'}
        return {'platform': sent, 'refusal': None}

    def _project(self, entry):
        aid = entry['id']
        pid = projection_id(aid, entry['request_version'])
        versions = {aid: entry['version']}
        existing = self.record(pid)
        if existing is not None and existing['outcome'] not in RETRYABLE:
            outcome, reason = SETTLED[existing['outcome']]
            return self._result(aid, versions, outcome, reason, projection_id=pid)
        brief = self.inbox.brief(aid)
        if not brief['valid'] or brief['version'] != entry['version']:
            return self._result(aid, versions, 'refused', 'stale_subject')
        text = render(brief)
        record = dict(schema=SCHEMA, channel=CHANNEL, assignment_id=aid, assignment_version=entry['version'],
                      request_version=entry['request_version'], presentation_digest=presentation_digest(text.encode('utf-8')),
                      presentation=text, configured_chat=self.edge.chat)
        expected = dict(versions, **{pid: existing['entity_version'] if existing else 0})
        try:
            intent = self._commit(dict(phase='intent', projection_id=pid, record=record), expected)
            completion = self._send(text)
        except self.store.StoreRefused as exc:
            return self._result(aid, versions, 'refused', exc.code)  # no intent, so nothing was sent
        try:
            done = self._commit(dict(phase='complete', projection_id=pid, attempt=intent['attempt'], **completion),
                                {pid: intent['entity_version']})
        except self.store.StoreRefused as exc:
            # The intent stays pending: the outcome is unknown and is never sent again. What the
            # platform answered is reported here so it is not silently lost.
            platform = completion['platform'] or {}
            return self._result(aid, versions, 'unknown_outcome', exc.code, projection_id=pid,
                                platform={k: platform.get(k) for k in ('chat_id', 'message_id', 'date')})
        return self._result(aid, versions, done['outcome'], done['refusal'], projection_id=pid)

    def project(self):
        """Attempt each pending entry that has no settled record at its request version; return
        one result per pending entry."""
        return [self._project(entry) for entry in self.inbox.index()['entries'] if entry['category'] == 'pending']

    def metrics(self):
        records = {e['id']: self.record(projection_id(e['id'], e['request_version']))
                   for e in self.inbox.index()['entries'] if e['category'] == 'pending'}
        return dict(self.counts,
                    pending=sum(1 for r in records.values() if r is None or r['outcome'] in RETRYABLE),
                    unknown=sum(1 for r in records.values() if r is not None and r['outcome'] in ('pending', 'unknown_outcome')))
