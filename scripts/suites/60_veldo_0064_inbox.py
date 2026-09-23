"""Assignment inbox and Telegram projection over a real signed SQLite store (VELDO-0064).

Criterion rows collect every observation, including negative requests. The claim is taken
through the real claim receiver, the waiting worker is a real child process speaking signed
JSON lines, Telegram sends go over real HTTP to a loopback Bot API endpoint that answers with
the platform's sendMessage shape, and every journal record carries a real OpenSSH signature.
Mutation workers replace one production module copy below, never assertions or fixtures.
"""
import http.server as _v64_http
import importlib.util as _v64_import
import json as _v64_json
from pathlib import Path as _v64_Path
import subprocess as _v64_sp
import sys as _v64_sys
import tempfile as _v64_temp
import threading as _v64_threading
import time as _v64_time


def _v64_load(name, path):
    spec = _v64_import.spec_from_file_location(name, path)
    module = _v64_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_V64_WORKER = r'''
import json, subprocess, sys
key, namespace, ids, unit, alias, content = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4], sys.argv[5], json.loads(sys.argv[6])
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
def signed(command):
    signature = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", key, "-n", namespace], input=canonical(command),
                               capture_output=True, check=True, timeout=10).stdout.decode()
    return {"command": command, "signature": signature}
def ask(command):
    print(json.dumps({"packet": signed(command)}), flush=True)
    return json.loads(sys.stdin.readline())["result"]
claim = ask(dict(ids, operation="claim", unit_id=unit, principal="worker-a", command_id="w-claim", nonce="w-claim-n",
                 generation=0, capabilities=[]))
if not claim.get("ok"):
    sys.exit(3)
reply = ask(dict(ids, operation="open", alias=alias, principal="worker-a", command_id="w-open", nonce="w-open-n",
                 claim_generation=claim["claim"]["generation"], assignment=content))
if reply.get("ok") and reply.get("stop_requester"):
    sys.exit(0)
sys.stdin.readline()  # a worker that is not told to stop waits here for the person's answer
sys.exit(4)
'''


class _V64BotApi(_v64_http.BaseHTTPRequestHandler):
    """Loopback endpoint with the Bot API sendMessage request and answer shapes."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        st = self.state
        body = _v64_json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path != '/bot%s/sendMessage' % st['token']:
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})
        if st['mode'] == 'refuse':
            return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: chat not found'})
        chat = st['chats'].get(body.get('chat_id'))
        st['next'] += 1
        message = {'message_id': st['next'], 'date': 1790000000 + st['next'],
                   'chat': {'id': chat, 'type': 'private'}, 'text': body['text']}
        st['messages'][(chat, st['next'])] = body['text'].encode('utf-8')
        if st['mode'] == 'drop':
            self.close_connection = True
            return  # published, but the answer never reaches the caller
        self._answer(200, {'ok': True, 'result': message})

    def _answer(self, code, value):
        payload = _v64_json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _v64_checks(base):
    rows = {name: [] for name in ('install/assets', 'inbox/states-and-authority', 'inbox/waiting-resources',
                                  'projection/correlation', 'projection/send-outcomes', 'inbox/visible-invalid',
                                  'inbox/unauthorized-admission')}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    scaffold = _v64_load('v64_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
    created, skipped = [], []
    for rel in ('.veldo/control_assignment.py', '.veldo/control_channel_projection.py'):
        check('install/assets', rel + ' installed by the scaffold', rel in scaffold._FILES)
        check('install/assets', rel + ' engine copy identical', (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
        scaffold._lay(ROOT / 'engine' / rel, base / 'installed' / rel, rel, created, skipped)
        check('install/assets', rel + ' laid by the installer', (base / 'installed' / rel).read_bytes() == (ROOT / rel).read_bytes())

    contract = _v64_load('v64_contract', ROOT / '.veldo' / 'entity_contract.py')
    claims = _v64_load('v64_claims', ROOT / '.veldo' / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    I = _v64_load('v64_inbox', ROOT / ".veldo" / "control_assignment.py")
    P = _v64_load('v64_projection', ROOT / ".veldo" / "control_channel_projection.py")

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'owner', 'worker-a', 'stranger', 'pm'):
        _v64_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v64-' + who, '-f', str(keys / who)],
                    check=True, capture_output=True, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()
    journal_signed = []

    def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
        signature = _v64_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                capture_output=True, check=True, timeout=10).stdout.decode()
        return signature

    def journal_sign(message):
        signature = sign_as('authority', message, 'veldo-journal')
        journal_signed.append((message, signature))
        return signature

    ids = dict(domain_uuid='inbox-domain', repository_uuid='inbox-repository', store_uuid='inbox-store')
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    serial = [0]

    def fixture(eid, kind, data):
        serial[0] += 1
        entity = S.materialized_state(conn)['entities'].get(eid, {})
        return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: entity.get('version', 0)}, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    members = {'owner': dict(principal_type='person', roles=['project_owner'], scope=['project-a']),
               'worker-a': dict(principal_type='agent_run', roles=[], scope='*'),
               'stranger': dict(principal_type='person', roles=[], scope=['project-b']),
               'pm': dict(principal_type='service', roles=[], scope=['project-a'])}
    for who, data in members.items():
        fixture(who, 'membership', dict(data, revoked_at=None, expires_at=None))
        fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
    fixture('backlog', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=ids['repository_uuid']))
    for unit in ('unit-1', 'unit-2'):
        fixture(unit, 'execution_unit', dict(state='READY', repository_uuid=ids['repository_uuid'],
                                             backlog_item_uuid='backlog', requirements=[], eligible_holders=['worker-a']))

    receiver = claims.Receiver(conn, ids, 'authority', journal_sign)
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    counter = [0]

    def command(who, operation, alias, **fields):
        counter[0] += 1
        body = dict(ids, operation=operation, alias=alias, principal=who, command_id='c-%d' % counter[0],
                    nonce='n-%d' % counter[0], **fields)
        return inbox.apply({'command': body, 'signature': sign_as(who, S.canonical_bytes(body))})

    def content(kind, owner='owner', unit=None, deadline='2026-10-01T17:00:00Z', budget=None, brief=None):
        return dict(kind=kind, owner=owner, scope=['project-a'], deadline=deadline,
                    budget=budget or {'owner_minutes': 15}, brief=brief or 'Choose how %s proceeds.' % kind,
                    choices=['accept', 'reject'] if kind != 'acknowledgement' else ['acknowledged'],
                    subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md', 'digest': 'sha256:' + '1' * 64},
                    unit_id=unit)

    def entity(eid):
        return S.materialized_state(conn)['entities'].get(eid)

    # --- AC1: the requester stops and releases its claim; nothing waits for the answer ---------------
    states = tuple(contract.LIFECYCLES['assignment']['states'])
    check('inbox/states-and-authority', 'every schema state has exactly one category', set(states) == set(I.CATEGORIES))
    check('inbox/states-and-authority', 'enabled categories are categories of the schema',
          set(I.ENABLED_CATEGORIES) <= set(I.CATEGORIES.values()) and
          set(I.ENABLED_CATEGORIES) == {'pending', 'answered', 'declined', 'canceled'})
    script = base / 'worker.py'
    script.write_text(_V64_WORKER)
    worker = _v64_sp.Popen([_v64_sys.executable, str(script), str(keys / 'worker-a'), AC.SIGNATURE_NAMESPACE,
                            _v64_json.dumps(ids), 'unit-1', 'W-1', _v64_json.dumps(content('decision', unit='unit-1'))],
                           stdin=_v64_sp.PIPE, stdout=_v64_sp.PIPE, text=True)
    replies = []
    for handler in (receiver.apply, inbox.apply):
        line = worker.stdout.readline()
        if not line:
            break
        result = handler(_v64_json.loads(line)['packet'])
        replies.append(result)
        worker.stdin.write(_v64_json.dumps({'result': {k: v for k, v in result.items() if k != 'receipt'}}) + '\n')
        worker.stdin.flush()
    try:
        exit_code = worker.wait(timeout=3)
    except _v64_sp.TimeoutExpired:
        exit_code = None
        worker.kill()
        worker.wait()
    worker.stdin.close()
    worker.stdout.close()
    w1 = I.assignment_id(ids['repository_uuid'], 'W-1')
    cid = claims.claim_id(ids['repository_uuid'], 'unit-1')
    check('inbox/waiting-resources', 'the worker claimed the unit through the claim receiver',
          len(replies) == 2 and replies[0].get('ok') is True)
    check('inbox/waiting-resources', 'opening the assignment was accepted and parks the unit',
          len(replies) == 2 and replies[1].get('ok') is True and replies[1].get('released_claim') == cid)
    check('inbox/waiting-resources', 'the worker process exited instead of waiting', exit_code == 0)
    claim_now = (entity(cid) or {}).get('data', {})
    check('inbox/waiting-resources', 'the claim is released in the store', claim_now.get('state') == 'released'
          and claim_now.get('holder') is None)
    check('inbox/waiting-resources', 'no claim is pending at the claim receiver', cid not in receiver.pending())
    check('inbox/waiting-resources', 'no pending assignment holds a claim', inbox.waiting_resources() == [])
    opened = (entity(w1) or {}).get('data', {})
    check('inbox/waiting-resources', 'claim release and assignment committed in one journal record',
          len(replies) == 2 and set(replies[1]['receipt']['after_versions']) >= {w1, cid}
          and opened.get('state') == 'OFFERED')
    # Additive control: the check sees a held claim when one exists.
    claim2 = receiver.apply({'command': dict(ids, operation='claim', unit_id='unit-2', principal='worker-a',
                                             command_id='c-claim-2', nonce='n-claim-2', generation=0, capabilities=[]),
                             'signature': sign_as('worker-a', S.canonical_bytes(dict(ids, operation='claim', unit_id='unit-2',
                                                  principal='worker-a', command_id='c-claim-2', nonce='n-claim-2',
                                                  generation=0, capabilities=[])))})
    check('inbox/waiting-resources', 'control: a second unit is claimed', claim2.get('ok') is True)
    other = command('owner', 'open', 'W-2', assignment=content('decision', unit='unit-2'))
    check('inbox/waiting-resources', 'control: a person cannot park a claim held by another principal',
          other == {'ok': False, 'reason': 'not_owner'})
    held = dict(content('decision', unit='unit-2'), schema=I.SCHEMA, alias='W-3', actor_kind='person', state='OFFERED',
                requested_by='pm', request_version=1, answer=None, disposition=None, **{k: ids[k] for k in ('domain_uuid', 'repository_uuid')})
    fixture(I.assignment_id(ids['repository_uuid'], 'W-3'), 'assignment', held)
    seen = inbox.waiting_resources()
    check('inbox/waiting-resources', 'control: a pending assignment over a held claim is reported',
          [r['claim_id'] for r in seen] == [claims.claim_id(ids['repository_uuid'], 'unit-2')])
    cancel_w3 = command('pm', 'cancel', 'W-3', request_version=1)
    check('inbox/waiting-resources', 'control: the fixture assignment is canceled again', cancel_w3.get('ok') is True
          and inbox.waiting_resources() == [])

    # Every enabled kind is opened by the PM service or the owner; three more reach each terminal category.
    aliases = {}
    for kind in sorted(I.KINDS):
        result = command('pm', 'open', 'K-' + kind, assignment=content(kind))
        aliases[kind] = I.assignment_id(ids['repository_uuid'], 'K-' + kind)
        check('inbox/states-and-authority', 'open %s accepted and stops the requester' % kind,
              result.get('ok') is True and result.get('stop_requester') is True)
    for alias in ('T-answer', 'T-decline', 'T-cancel'):
        check('inbox/states-and-authority', alias + ' opened', command('pm', 'open', alias, assignment=content('decision')).get('ok'))
    answered = command('owner', 'answer', 'T-answer', request_version=1, ruling='accept')
    declined = command('owner', 'decline', 'T-decline', request_version=1)
    canceled = command('pm', 'cancel', 'T-cancel', request_version=1)
    check('inbox/states-and-authority', 'owner answer, owner decline and requester cancel accepted',
          answered.get('ok') and declined.get('ok') and canceled.get('ok'))
    refusals = {
        'stranger answers': command('stranger', 'answer', 'K-decision', request_version=1, ruling='accept'),
        'worker answers': command('worker-a', 'answer', 'K-decision', request_version=1, ruling='accept'),
        'stale version': command('owner', 'answer', 'K-decision', request_version=2, ruling='accept'),
        'unoffered ruling': command('owner', 'answer', 'K-decision', request_version=1, ruling='maybe'),
        'answer after cancel': command('owner', 'answer', 'T-cancel', request_version=1, ruling='accept'),
        'agent owner': command('pm', 'open', 'T-agent', assignment=content('decision', owner='worker-a')),
        'stranger cancels': command('stranger', 'cancel', 'K-decision', request_version=1),
        'forged signature': inbox.apply({'command': dict(ids, operation='cancel', alias='K-decision', principal='pm',
                                                         command_id='c-forged', nonce='n-forged', request_version=1),
                                         'signature': sign_as('stranger', b'other bytes')}),
    }
    for label, result in refusals.items():
        check('inbox/states-and-authority', 'refused: ' + label, result.get('ok') is False)
    check('inbox/states-and-authority', 'refusal names are specific',
          refusals['stale version']['reason'] == 'stale_subject' and refusals['stranger answers']['reason'] == 'not_authorized'
          and refusals['worker answers']['reason'] == 'not_authorized')
    index = inbox.index()
    by_id = {e['id']: e for e in index['entries']}
    stored = S.materialized_state(conn)['entities']
    authority = CM.authority_state(S, conn)
    categories = {by_id[I.assignment_id(ids['repository_uuid'], a)]['category'] for a in ('T-answer', 'T-decline', 'T-cancel')}
    check('inbox/states-and-authority', 'answered, declined and canceled reach their categories',
          categories == {'answered', 'declined', 'canceled'})
    check('inbox/states-and-authority', 'every enabled category is observed through real commands',
          set(I.ENABLED_CATEGORIES) <= {e['category'] for e in index['entries']})
    check('inbox/states-and-authority', 'the index watermark is the journal head',
          index['watermark'] == conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0])
    for entry in index['entries']:
        if not entry['valid']:
            continue
        data = stored[entry['id']]['data']
        check('inbox/states-and-authority', entry['id'] + ' shows stored owner, scope, deadline and budget',
              (entry['owner'], entry['scope'], entry['deadline'], entry['budget'], entry['request_version'], entry['version'])
              == (data['owner'], data['scope'], data['deadline'], data['budget'], data['request_version'], stored[entry['id']]['version']))
        member = AC.membership_entry(authority['membership'], entry['owner'])
        check('inbox/states-and-authority', entry['id'] + ' owner is a current person member',
              member is not None and member['principal_type'] == 'person' and AC.active_member(member, _v64_time.time())[0])
    pending = [e for e in index['entries'] if e['category'] == 'pending']
    check('inbox/states-and-authority', 'metrics expose pending work', inbox.metrics()['pending'] == len(pending)
          and inbox.metrics()['refused'] >= len(refusals))
    check('inbox/states-and-authority', 'observations carry identity and outcome, never text',
          all(set(o) >= {'operation', 'assignment_id', 'outcome', 'reason', 'accepted_versions'} and 'brief' not in o
              and 'signature' not in o for o in inbox.observations))
    check('inbox/states-and-authority', 'nothing waits while answers are outstanding', inbox.waiting_resources() == [])

    # --- AC2: Telegram projection keeps the platform's chat and message identity --------------------
    api = {'token': 'sandbox-bot', 'mode': 'ok', 'next': 7000, 'messages': {}, 'chats': {'@veldo_owner': 5550001}}
    handler = type('V64Handler', (_V64BotApi,), {'state': api})
    server = _v64_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v64_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        edge = P.TelegramEdge('http://127.0.0.1:%d' % server.server_address[1], api['token'], '@veldo_owner')
        projection = P.Projection(S, inbox, edge, conn, 'authority', journal_sign)
        first = projection.project()
        pending = [e for e in inbox.index()['entries'] if e['category'] == 'pending']
        check('projection/correlation', 'every pending entry was sent once',
              sorted(r['outcome'] for r in first) == ['sent'] * len(pending) and len(api['messages']) == len(pending))
        kinds_sent = set()
        for entry in pending:
            record = projection.record(P.projection_id(entry['id'], entry['request_version']))
            retrieved = api['messages'].get(((record or {}).get('chat_id'), (record or {}).get('message_id')))
            check('projection/correlation', entry['id'] + ' keeps the returned chat and message identity',
                  record is not None and record['chat_id'] == 5550001 and retrieved is not None)
            check('projection/correlation', entry['id'] + ' bytes retrieved from the platform match the record',
                  retrieved is not None and P.presentation_digest(retrieved) == record['presentation_digest']
                  and retrieved == record['presentation'].encode('utf-8'))
            check('projection/correlation', entry['id'] + ' binds the inbox request version',
                  record is not None and record['request_version'] == entry['request_version']
                  and record['assignment_version'] == entry['version'])
            kinds_sent.add(entry['kind'])
            text = (retrieved or b'').decode('utf-8')
            check('inbox/states-and-authority', entry['id'] + ' Telegram shows owner, scope, deadline and budget',
                  all(line in text.split('\n') for line in (
                      'Owner: %s' % entry['owner'], 'Scope: %s' % ', '.join(entry['scope']),
                      'Deadline: %s' % entry['deadline'], 'Request version: %d' % entry['request_version'],
                      'Budget: ' + ', '.join('%s=%s' % (u, entry['budget'][u]) for u in sorted(entry['budget'])))))
        check('projection/correlation', 'every enabled assignment kind reached Telegram', kinds_sent == set(I.KINDS))
        again = projection.project()
        check('projection/correlation', 'a re-run sends nothing twice',
              all(r['outcome'] == 'already_projected' for r in again) and len(api['messages']) == len(pending))
        revised = command('pm', 'revise', 'K-decision', request_version=1,
                          changes={'deadline': '2026-10-03T12:00:00Z', 'budget': {'owner_minutes': 30}})
        check('projection/correlation', 'a revision is accepted', revised.get('ok') is True)
        third = projection.project()
        k1 = aliases['decision']
        history = projection.correlation(k1)
        check('projection/correlation', 'the changed version is a new message; older versions are kept',
              [r['outcome'] for r in third].count('sent') == 1 and sorted(history) == [1, 2]
              and history[1]['message_id'] != history[2]['message_id'])
        current = inbox.index()
        k1_entry = {e['id']: e for e in current['entries']}[k1]
        latest = history.get(k1_entry['request_version'], {})
        check('projection/correlation', 'the current record matches the inbox request version and platform bytes',
              latest.get('request_version') == 2 and latest.get('chat_id') == 5550001
              and api['messages'].get((latest.get('chat_id'), latest.get('message_id'))) == latest.get('presentation', '').encode('utf-8')
              and 'Deadline: 2026-10-03T12:00:00Z' in latest.get('presentation', ''))
        # Refusal and unknown outcome at the platform boundary.
        api['mode'] = 'refuse'
        command('owner', 'open', 'P-refused', assignment=content('acknowledgement'))
        refused = [r for r in projection.project() if r['outcome'] != 'already_projected']
        p_refused = I.assignment_id(ids['repository_uuid'], 'P-refused')
        check('projection/send-outcomes', 'a platform refusal publishes and records nothing',
              [r['outcome'] for r in refused] == ['refused'] and projection.record(P.projection_id(p_refused, 1)) is None)
        api['mode'] = 'drop'
        before = len(api['messages'])
        lost = [r for r in projection.project() if r['outcome'] != 'already_projected']
        dropped = projection.record(P.projection_id(p_refused, 1))
        check('projection/send-outcomes', 'a lost answer is recorded as unknown, never as sent',
              [r['outcome'] for r in lost] == ['unknown_outcome'] and dropped is not None
              and dropped['outcome'] == 'unknown_outcome' and dropped['message_id'] is None)
        api['mode'] = 'ok'
        projection.project()
        check('projection/send-outcomes', 'an unknown outcome is not blindly sent again', len(api['messages']) == before + 1)
        check('projection/send-outcomes', 'the token is never recorded',
              all(api['token'] not in _v64_json.dumps(o) for o in projection.observations)
              and api['token'] not in _v64_json.dumps(S.materialized_state(conn)['entities']))
        check('projection/send-outcomes', 'projection metrics count refusals and unprojected work',
              projection.metrics()['refused'] >= 2 and projection.metrics()['pending'] == 0)
        try:
            P.TelegramEdge('http://example.invalid', api['token'], '@veldo_owner')
            check('projection/send-outcomes', 'a plain-HTTP remote origin is refused', False)
        except P.EdgeRefused as exc:
            check('projection/send-outcomes', 'a plain-HTTP remote origin is refused', exc.code == 'invalid_input')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)

    # --- AC3: views describe; only current authority admits --------------------------------------
    k1_brief = inbox.brief(k1)
    check('inbox/visible-invalid', 'the changed version reads as current accepted content',
          k1_brief['valid'] and k1_brief['content']['request_version'] == 2
          and k1_brief['content']['deadline'] == '2026-10-03T12:00:00Z'
          and k1_brief['version'] == _v64_stored_version(conn, k1)
          and k1_brief['content'] == {k: entity(k1)['data'].get(k) for k in k1_brief['content']})
    pending_brief = inbox.brief(aliases['review_disposition'])
    check('inbox/visible-invalid', 'a pending version reads as current accepted content',
          pending_brief['valid'] and pending_brief['category'] == 'pending'
          and pending_brief['content']['owner'] == 'owner' and pending_brief['content']['request_version'] == 1)
    bad_state = dict(held, alias='X-state', state='ASSIGNED', display_status='assigned', assignee='worker-a', unit_id=None)
    fixture(I.assignment_id(ids['repository_uuid'], 'X-state'), 'assignment', bad_state)
    fixture('assignment:inbox-repository:X-kind', 'note', {'text': 'looks like an assignment'})
    tampered = I.assignment_id(ids['repository_uuid'], 'X-tamper')
    fixture(tampered, 'assignment', dict(held, alias='X-tamper', unit_id=None))
    conn.execute('UPDATE entities SET data=? WHERE id=?',
                 (_v64_json.dumps(dict(held, alias='X-tamper', unit_id=None, owner='stranger'), sort_keys=True), tampered))
    invalid_ids = [I.assignment_id(ids['repository_uuid'], a) for a in ('X-state', 'X-kind', 'X-tamper')]
    after = {e['id']: e for e in inbox.index()['entries']}
    for eid in invalid_ids:
        entry = after.get(eid)
        check('inbox/visible-invalid', eid + ' is listed as invalid with its problems',
              entry is not None and entry['valid'] is False and entry['category'] == 'invalid' and entry['problems'])
        check('inbox/visible-invalid', eid + ' index entry carries no content', entry is not None
              and not {'owner', 'state', 'deadline', 'budget', 'kind'} & set(entry))
        brief = inbox.brief(eid)
        check('inbox/visible-invalid', eid + ' brief is visibly invalid', brief['valid'] is False
              and 'content' not in brief and brief['category'] == 'invalid')
    check('inbox/visible-invalid', 'invalid records are not pending work', inbox.metrics()['pending']
          == sum(1 for e in after.values() if e['category'] == 'pending'))

    labelled = I.assignment_id(ids['repository_uuid'], 'X-label')
    fixture(labelled, 'assignment', dict(held, alias='X-label', unit_id=None, display_status='assigned', assignee='worker-a'))
    forged = I.assignment_id(ids['repository_uuid'], 'X-forged')
    fixture(forged, 'assignment', dict(held, alias='X-forged', unit_id=None, state='SUBMITTED',
                                       answer=dict(principal='owner', ruling='accept', request_version=1,
                                                   command_id=answered['receipt']['command_id'])))
    command('pm', 'open', 'X-revoked', assignment=content('decision'))
    revoked_answer = command('owner', 'answer', 'X-revoked', request_version=1, ruling='reject')
    t_answer = I.assignment_id(ids['repository_uuid'], 'T-answer')
    admissions = {
        'displayed assigned status on a pending record': inbox.admit(labelled),
        'displayed assigned status on an invalid record': inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-state')),
        'answer copied onto another record by a service write': inbox.admit(forged),
        'declined': inbox.admit(I.assignment_id(ids['repository_uuid'], 'T-decline')),
        'canceled': inbox.admit(I.assignment_id(ids['repository_uuid'], 'T-cancel')),
        'pending': inbox.admit(aliases['acknowledgement']),
        'absent': inbox.admit(I.assignment_id(ids['repository_uuid'], 'nothing')),
    }
    genuine = inbox.admit(t_answer)
    before_revocation = inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-revoked'))
    fixture('owner', 'membership', dict(members['owner'], revoked_at=_v64_time.time() - 1, expires_at=None))
    admissions['answer whose owner is no longer a member'] = inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-revoked'))
    for label, result in admissions.items():
        check('inbox/unauthorized-admission', 'refused: ' + label, result['admitted'] is False)
    check('inbox/unauthorized-admission', 'refusals are named',
          admissions['displayed assigned status on a pending record']['reason'] == 'not_answered'
          and admissions['displayed assigned status on an invalid record']['reason'] == 'invalid_record'
          and admissions['answer copied onto another record by a service write']['reason'] == 'missing_authority'
          and admissions['answer whose owner is no longer a member']['reason'] == 'missing_authority')
    check('inbox/unauthorized-admission', 'control: the owner answer admits while the owner is current',
          genuine['admitted'] is True and revoked_answer.get('ok') is True and before_revocation['admitted'] is True)

    # Every journal signature verifies with the authority key.
    allowed = base / 'allowed_signers'
    allowed.write_text('authority ' + public['authority'] + '\n')
    for message, signature in journal_signed[-3:] + journal_signed[:2]:
        sig = base / 'journal.sig'
        sig.write_text(signature)
        verified = _v64_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'authority', '-n', 'veldo-journal',
                                '-s', str(sig)], input=message, capture_output=True, timeout=10)
        check('install/assets', 'journal record signature verifies', verified.returncode == 0)
    conn.close()
    return rows


def _v64_stored_version(conn, eid):
    row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
    return row[0] if row else 0


_v64_started = _v64_time.monotonic()
with _v64_temp.TemporaryDirectory(prefix='v64-') as _v64_dir:
    _v64_rows = _v64_checks(_v64_Path(_v64_dir))
for _v64_name, _v64_observed in _v64_rows.items():
    _v64_ok = bool(_v64_observed) and all(ok for _, ok in _v64_observed)
    if not _v64_ok:
        for _v64_label, _v64_one in _v64_observed:
            if not _v64_one:
                print('  VELDO-0064 %s detail: %s' % (_v64_name, _v64_label))
    expect('VELDO-0064 ' + _v64_name, _v64_ok)
print('VELDO-0064 suite seconds: %.3f' % (_v64_time.monotonic() - _v64_started))
