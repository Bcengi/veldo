"""Telegram projection of the assignment inbox with durable message correlation (VELDO-0064).

WHAT THIS MODULE IS. The ordinary outbound Telegram projection of pending person assignments.
For every valid pending inbox entry that has no projection at its current request version, it
renders the presentation bytes from the inbox brief, sends them through the Telegram Bot API
`sendMessage` method, and commits one `channel_projection` entity carrying what the platform
returned: its chat identity, its message identity, its date and the text it stored. The record
binds the assignment id, the entity version and the request version that were presented, and the
digest of the exact bytes sent. One record per (assignment, request version), so a re-run sends
nothing twice. A changed request version is a new presentation and a new message.

WHAT THE PLATFORM SAID IS WHAT IS KEPT. The chat identity recorded is the one the platform
returned, not the configured address (Telegram accepts `@name` and answers with the numeric
chat id). A response whose echoed text differs from the bytes sent is refused. A transport
failure after the request may have reached the platform is recorded as `unknown_outcome` with
no message identity, so nothing is blindly sent again; looking the message up and recovering is
Release 2 work.

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
OUTCOMES = ('sent', 'unknown_outcome')


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
    pid = params.get('projection_id')
    record = params.get('record')
    if not isinstance(pid, str) or pid in before or not isinstance(record, dict) \
            or record.get('outcome') not in OUTCOMES:
        raise ValueError('a projection record is new and names its outcome')
    return {pid: {'kind': ENTITY_KIND, 'data': record}}


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

    def _observe(self, assignment, versions, outcome, reason):
        accepted = outcome in ('sent', 'already_projected')
        self.counts['accepted' if accepted else 'refused'] += 1
        self.observations.append(dict(self.inbox.ids, operation='project', channel=CHANNEL,
                                      assignment_id=assignment, accepted_versions=versions,
                                      outcome=outcome, reason=reason))

    def record(self, pid):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=? AND kind=?',
                                (pid, ENTITY_KIND)).fetchone()
        return None if row is None else dict(json.loads(row[1]), entity_version=row[0])

    def correlation(self, assignment):
        """The projection records of one assignment, by request version."""
        rows = self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (ENTITY_KIND,)).fetchall()
        records = [json.loads(r[0]) for r in rows]
        return {r['request_version']: r for r in records if r.get('assignment_id') == assignment}

    def project(self):
        """Send each unprojected pending version once; return one result per pending entry."""
        results = []
        for entry in self.inbox.index()['entries']:
            if entry['category'] != 'pending':
                continue
            pid = projection_id(entry['id'], entry['request_version'])
            versions = {entry['id']: entry['version']}
            if self.record(pid) is not None:
                self._observe(entry['id'], versions, 'already_projected', None)
                results.append({'assignment_id': entry['id'], 'outcome': 'already_projected', 'projection_id': pid})
                continue
            brief = self.inbox.brief(entry['id'])
            if not brief['valid'] or brief['version'] != entry['version']:
                self._observe(entry['id'], versions, 'refused', 'stale_subject')
                results.append({'assignment_id': entry['id'], 'outcome': 'refused', 'reason': 'stale_subject'})
                continue
            text = render(brief)
            body = text.encode('utf-8')
            record = dict(schema=SCHEMA, channel=CHANNEL, assignment_id=entry['id'], assignment_version=entry['version'],
                          request_version=entry['request_version'], presentation_digest=presentation_digest(body),
                          presentation=text, configured_chat=self.edge.chat)
            try:
                sent = self.edge.send(text)
            except EdgeRefused as exc:
                if exc.code != 'unknown_outcome':
                    self._observe(entry['id'], versions, 'refused', exc.code)
                    results.append({'assignment_id': entry['id'], 'outcome': 'refused', 'reason': exc.code})
                    continue
                record.update(outcome='unknown_outcome', chat_id=None, message_id=None, platform_date=None)
            else:
                if sent['text'].encode('utf-8') != body:
                    self._observe(entry['id'], versions, 'refused', 'presentation_mismatch')
                    results.append({'assignment_id': entry['id'], 'outcome': 'refused', 'reason': 'presentation_mismatch'})
                    continue
                record.update(outcome='sent', chat_id=sent['chat_id'], message_id=sent['message_id'],
                              platform_date=sent['date'])
            self._serial += 1
            command_id = '%s:%s:%.6f:%d' % (OPERATION, pid, self.clock(), self._serial)
            command = dict(command_id=command_id, principal=self.journal_signer, operation=OPERATION,
                           parameters=dict(projection_id=pid, record=record), expected_versions={pid: 0},
                           artifact_digests=[record['presentation_digest']], nonce=command_id)
            try:
                self.store.execute(self.conn, command, self.journal_signer, self.sign, self.authority_generation)
            except self.store.StoreRefused as exc:
                self._observe(entry['id'], versions, 'unknown_outcome', exc.code)
                results.append({'assignment_id': entry['id'], 'outcome': 'unknown_outcome', 'reason': exc.code})
                continue
            self._observe(entry['id'], versions, record['outcome'], None)
            results.append({'assignment_id': entry['id'], 'outcome': record['outcome'], 'projection_id': pid})
        return results

    def metrics(self):
        unprojected = sum(1 for e in self.inbox.index()['entries'] if e['category'] == 'pending'
                          and self.record(projection_id(e['id'], e['request_version'])) is None)
        return dict(self.counts, pending=unprojected)
