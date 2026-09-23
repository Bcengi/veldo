"""Assignment inbox and Telegram projection over a real signed SQLite store (VELDO-0064).

Criterion rows collect every observation, including negative requests. The claim is taken
through the real claim receiver, the waiting worker is a real child process speaking signed
JSON lines, Telegram sends go over real HTTP to a loopback Bot API endpoint that answers with
the platform's sendMessage shape, and every journal record carries a real OpenSSH signature.
Mutation workers replace one production module copy below, never assertions or fixtures. The
claim organ loads its sibling organs from its own directory, so the suite copies the installed
organs into one directory and then the claim organ from its own anchor.
"""
import http.server as _v64_http
import importlib.util as _v64_import
import json as _v64_json
from pathlib import Path as _v64_Path
import shutil as _v64_shutil
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
        if st['mode'] == 'limit':
            return self._answer(429, {'ok': False, 'error_code': 429, 'description': 'Too Many Requests: retry after 1'})
        st['requests'].append((body.get('chat_id'), body.get('text')))
        chat = st['chats'].get(body.get('chat_id'), body.get('chat_id'))
        st['next'] += 1
        # 'normalize': the platform stores and echoes a normalized text (a collapsed blank line).
        text = body['text'].replace('\n\n', '\n') if st['mode'] == 'normalize' else body['text']
        message = {'message_id': st['next'], 'date': 1790000000 + st['next'],
                   'chat': {'id': chat, 'type': 'private'}, 'text': text}
        st['messages'][(chat, st['next'])] = text.encode('utf-8')
        if st['mode'] == 'drop':
            self.close_connection = True
            return  # published, but the answer never reaches the caller
        # Published, and then an answer that is not Telegram's own refusal reaches the caller.
        if st['mode'] == 'gateway':
            return self._raw(502, b'<html>502 Bad Gateway</html>')
        if st['mode'] == 'telegram5xx':
            return self._answer(500, {'ok': False, 'error_code': 500, 'description': 'Internal Server Error'})
        if st['mode'] == 'proxy4xx':
            return self._raw(403, b'<html>403 Forbidden</html>')
        if st['mode'] == 'garbage':
            self.close_connection = True
            self.wfile.write(b'garbage\r\n\r\n')  # no HTTP status line at all
            return
        self._answer(200, {'ok': True, 'result': message})

    def _raw(self, code, payload):
        self.send_response(code)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
                                  'inbox/unauthorized-admission', 'inbox/parked-unit-unclaimable',
                                  'inbox/release-derived-from-claim', 'inbox/admit-verifies-owner-signature',
                                  'projection/intent-before-send', 'projection/echo-mismatch-kept',
                                  'projection/owner-enrolled-chat', 'projection/returned-chat-checked',
                                  'projection/only-telegram-refusal-retried', 'projection/protocol-error-unknown',
                                  'inbox/answer-survives-key-rotation')}

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
    organs = base / 'organs'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v64_shutil.copyfile(source, organs / source.name)
    _v64_shutil.copyfile(ROOT / ".veldo" / "control_claim.py", organs / 'control_claim.py')
    claims = _v64_load('v64_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    I = _v64_load('v64_inbox', ROOT / ".veldo" / "control_assignment.py")
    P = _v64_load('v64_projection', ROOT / ".veldo" / "control_channel_projection.py")

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'owner', 'worker-a', 'worker-b', 'stranger', 'pm', 'pm-b', 'reviewer', 'auditor',
                'rotator', 'rotator-new', 'rotator-next'):
        _v64_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v64-' + who, '-f', str(keys / who)],
                    check=True, capture_output=True, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()
    journal_signed = []
    sign_plan = []  # pending journal signatures: False makes that one store write fail unsigned

    def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
        signature = _v64_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                capture_output=True, check=True, timeout=10).stdout.decode()
        return signature

    def journal_sign(message):
        if sign_plan and not sign_plan.pop(0):
            return None
        signature = sign_as('authority', message, 'veldo-journal')
        journal_signed.append((message, signature))
        return signature

    ids = dict(domain_uuid='inbox-domain', repository_uuid='inbox-repository', store_uuid='inbox-store')
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    serial = [0]

    def fixture(eid, kind, data, principal='authority', pins=()):
        # `pins`: further entities whose current versions the write binds, as a forger may.
        serial[0] += 1
        current = S.materialized_state(conn)['entities']
        expected = {i: current.get(i, {}).get('version', 0) for i in (eid, *pins)}
        return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal=principal, operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions=expected, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    members = {'owner': dict(principal_type='person', roles=['project_owner'], scope=['project-a']),
               'worker-a': dict(principal_type='agent_run', roles=[], scope='*'),
               'worker-b': dict(principal_type='agent_run', roles=[], scope='*'),
               'stranger': dict(principal_type='person', roles=[], scope=['project-b']),
               'pm': dict(principal_type='service', roles=[], scope=['project-a']),
               'pm-b': dict(principal_type='service', roles=[], scope=['project-b']),
               'reviewer': dict(principal_type='person', roles=[], scope=['project-a']),
               'auditor': dict(principal_type='person', roles=[], scope=['project-a']),
               'rotator': dict(principal_type='person', roles=[], scope=['project-a'])}
    for who, data in members.items():
        fixture(who, 'membership', dict(data, revoked_at=None, expires_at=None))
        fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
    fixture('backlog', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=ids['repository_uuid']))
    for unit in ('unit-1', 'unit-2'):
        fixture(unit, 'execution_unit', dict(state='READY', repository_uuid=ids['repository_uuid'],
                                             backlog_item_uuid='backlog', requirements=[], eligible_holders=['worker-a']))
    for unit in ('unit-3', 'unit-4', 'unit-5'):
        fixture(unit, 'execution_unit', dict(state='READY', repository_uuid=ids['repository_uuid'],
                                             backlog_item_uuid='backlog', requirements=[], eligible_holders=['worker-b']))

    receiver = claims.Receiver(conn, ids, 'authority', journal_sign)
    try:
        I.Inbox(_v64_load('v64_other_store', ROOT / '.veldo' / 'control_store.py'), CM, claims, contract, conn, ids,
                'authority', journal_sign)
        check('inbox/states-and-authority', 'a store module other than the claim organ\'s is refused', False)
    except I.Refused as exc:
        check('inbox/states-and-authority', 'a store module other than the claim organ\'s is refused', exc.code == 'invalid_input')
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    counter = [0]

    def command(who, operation, alias, **fields):
        counter[0] += 1
        body = dict(ids, operation=operation, alias=alias, principal=who, command_id='c-%d' % counter[0],
                    nonce='n-%d' % counter[0], **fields)
        return inbox.apply({'command': body, 'signature': sign_as(who, S.canonical_bytes(body))})

    def content(kind, owner='owner', unit=None, deadline='2026-10-01T17:00:00Z', budget=None, brief=None,
                scope=None):
        return dict(kind=kind, owner=owner, scope=scope or ['project-a'], deadline=deadline,
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
        exit_code = worker.wait(timeout=2)
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

    # --- the parked unit is not claimable; the blocked work resumes only through admission ---------
    parked = 'inbox/parked-unit-unclaimable'

    def claim_packet(who, unit, command_id, operation='claim'):
        body = dict(ids, operation=operation, unit_id=unit, principal=who, command_id=command_id,
                    nonce=command_id + '-n', generation=0, capabilities=[])
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    check(parked, 'the released claim names the assignment the unit waits for', claim_now.get('parked_on') == w1)
    reclaim = receiver.apply(claim_packet('worker-a', 'unit-1', 'c-reclaim-1'))
    check(parked, 'a claim on the parked unit is refused as parked', reclaim == {'ok': False, 'reason': 'parked'})
    inspected = receiver.apply(claim_packet('worker-a', 'unit-1', 'c-inspect-1', 'inspect'))
    check(parked, 'inspection reports the unit parked', inspected.get('ok') is False and inspected.get('reason') == 'parked')
    early = command('worker-a', 'resume', 'W-1', request_version=1, capabilities=[])
    check(parked, 'resume before the owner answers is refused as not answered', early == {'ok': False, 'reason': 'not_answered'})
    check(parked, 'the claim is unchanged by every refusal', (entity(cid) or {}).get('data') == claim_now)
    w1_answer = command('owner', 'answer', 'W-1', request_version=1, ruling='accept')
    check(parked, 'control: the owner answer admits the blocked work',
          w1_answer.get('ok') is True and inbox.admit(w1)['admitted'] is True)
    person_resume = command('stranger', 'resume', 'W-1', request_version=1, capabilities=[])
    check(parked, 'a person cannot take the claim by resuming', person_resume.get('ok') is False)
    plain = receiver.apply(claim_packet('worker-a', 'unit-1', 'c-reclaim-2'))
    check(parked, 'admission does not reopen a plain claim', plain == {'ok': False, 'reason': 'parked'})
    resumed = command('worker-a', 'resume', 'W-1', request_version=1, capabilities=[])
    taken = (entity(cid) or {}).get('data', {})
    check(parked, 'resume after admission takes the claim again at the next generation',
          resumed.get('ok') is True and taken.get('state') == 'owned' and taken.get('holder') == 'worker-a'
          and taken.get('generation') == claim_now.get('generation', 0) + 1 and taken.get('resumed_from') == w1
          and not taken.get('parked_on'))
    twice = command('worker-a', 'resume', 'W-1', request_version=1, capabilities=[])
    check(parked, 'a second resume is refused while the claim is owned', twice.get('ok') is False)

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

    # --- the unit an assignment parks is the requester's own claim, never a field it writes -------
    derived = 'inbox/release-derived-from-claim'
    r1_id, r2_id, r3_id = (I.assignment_id(ids['repository_uuid'], a) for a in ('R-1', 'R-2', 'R-3'))
    cid3, cid4 = (claims.claim_id(ids['repository_uuid'], u) for u in ('unit-3', 'unit-4'))
    gen3 = receiver.apply(claim_packet('worker-b', 'unit-3', 'c-claim-3')).get('claim', {}).get('generation')
    opened_r1 = command('worker-b', 'open', 'R-1', claim_generation=gen3, assignment=content('decision'))
    claim3 = (entity(cid3) or {}).get('data', {})
    check(derived, 'an open that names no unit parks the requester\'s own claim',
          opened_r1.get('ok') is True and opened_r1.get('released_claim') == cid3
          and claim3.get('state') == 'released' and claim3.get('holder') is None and claim3.get('parked_on') == r1_id)
    check(derived, 'the stored assignment blocks the unit of that claim',
          (entity(r1_id) or {}).get('data', {}).get('unit_id') == 'unit-3')
    check(derived, 'nothing waits after the derived release', inbox.waiting_resources() == [])
    gen4 = receiver.apply(claim_packet('worker-b', 'unit-4', 'c-claim-4')).get('claim', {}).get('generation')
    no_generation = command('worker-b', 'open', 'R-2', assignment=content('decision'))
    check(derived, 'a holder naming no claim generation is refused and opens nothing',
          no_generation == {'ok': False, 'reason': 'invalid_input'} and entity(r2_id) is None
          and (entity(cid4) or {}).get('data', {}).get('state') == 'owned')
    foreign = command('worker-b', 'open', 'R-2', claim_generation=gen4, assignment=content('decision', unit='unit-1'))
    check(derived, 'naming a unit other than the requester\'s claim is refused',
          foreign == {'ok': False, 'reason': 'not_owner'} and entity(r2_id) is None)
    several = command('worker-a', 'open', 'R-2', claim_generation=1, assignment=content('decision', unit='unit-1'))
    check(derived, 'a requester holding several claims is refused', several == {'ok': False, 'reason': 'invalid_input'}
          and entity(r2_id) is None)
    opened_r3 = command('worker-b', 'open', 'R-3', claim_generation=gen4, assignment=content('decision'))
    check(derived, 'the next open parks the requester\'s remaining claim', opened_r3.get('released_claim') == cid4
          and (entity(r3_id) or {}).get('data', {}).get('unit_id') == 'unit-4' and inbox.waiting_resources() == [])
    # A claim taken between the inbox's read and its commit: the injected clock is read after the
    # authority state, so the claim below lands inside that window through the real receiver.
    raced = []

    def racing_clock():
        if not raced:
            raced.append(receiver.apply(claim_packet('worker-b', 'unit-5', 'c-claim-5')))
        return _v64_time.time()
    registered = conn.command_registry[I.OPERATION]
    racing = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign, clock=racing_clock)
    counter[0] += 1
    body = dict(ids, operation='open', alias='R-race', principal='worker-b', command_id='c-%d' % counter[0],
                nonce='n-%d' % counter[0], assignment=content('decision'))
    race = racing.apply({'command': body, 'signature': sign_as('worker-b', S.canonical_bytes(body))})
    conn.command_registry[I.OPERATION] = registered
    check(derived, 'a claim taken while the open is in flight refuses the open',
          raced and raced[0].get('ok') is True and race == {'ok': False, 'reason': 'stale_subject'}
          and entity(I.assignment_id(ids['repository_uuid'], 'R-race')) is None)

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
        'unknown unit': command('pm', 'open', 'T-unit', assignment=content('decision', unit='no-such-unit')),
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
    api = {'token': 'sandbox-bot', 'mode': 'ok', 'next': 7000, 'messages': {}, 'chats': {}, 'requests': []}

    def enroll(principal, chat, filed_as=None):
        # The enrollment id is spelled here, not taken from the module under test.
        return fixture('channel-enrollment:telegram_chat:' + (filed_as or principal), 'channel_enrollment',
                       dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=principal,
                            chat_id=chat, revoked_at=None))
    enroll('owner', 5550001)
    handler = type('V64Handler', (_V64BotApi,), {'state': api})
    server = _v64_http.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = _v64_threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        edge = P.TelegramEdge('http://127.0.0.1:%d' % server.server_address[1], api['token'])
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
        published = len(api['messages'])
        refused = [r for r in projection.project() if r['outcome'] != 'already_projected']
        p_refused = I.assignment_id(ids['repository_uuid'], 'P-refused')
        refusal = projection.record(P.projection_id(p_refused, 1)) or {}
        check('projection/send-outcomes', 'a platform refusal publishes nothing and records the refusal',
              [r['outcome'] for r in refused] == ['refused'] and len(api['messages']) == published
              and refusal.get('outcome') == 'refused' and refusal.get('message_id') is None)
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

        # --- the intent is committed before the send; an unknown send is never repeated -----------
        intent_row = 'projection/intent-before-send'
        command('pm', 'open', 'P-intent', assignment=content('decision'))
        p_intent = I.assignment_id(ids['repository_uuid'], 'P-intent')
        published = len(api['messages'])
        sign_plan[:] = [False]  # the intent write is refused
        no_intent = [r for r in projection.project() if r['assignment_id'] == p_intent]
        sign_plan[:] = []  # an unconsumed plan never reaches a later write
        check(intent_row, 'an intent that cannot be written sends nothing and records nothing',
              [(r['outcome'], r.get('reason')) for r in no_intent] == [('refused', 'incomplete_transaction')]
              and len(api['messages']) == published and projection.record(P.projection_id(p_intent, 1)) is None)
        retried = [r for r in projection.project() if r['assignment_id'] == p_intent]
        record_intent = projection.record(P.projection_id(p_intent, 1)) or {}
        check(intent_row, 'the next run writes the intent, sends once and completes it',
              [r['outcome'] for r in retried] == ['sent'] and len(api['messages']) == published + 1
              and record_intent.get('outcome') == 'sent' and record_intent.get('attempt') == 1
              and type(record_intent.get('message_id')) is int)
        command('pm', 'open', 'P-complete', assignment=content('decision'))
        p_complete = I.assignment_id(ids['repository_uuid'], 'P-complete')
        published = len(api['messages'])
        sign_plan[:] = [True, False]  # the intent commits; the completion write is refused
        lost = [r for r in projection.project() if r['assignment_id'] == p_complete]
        sign_plan[:] = []  # an unconsumed plan never reaches a later write
        pending_intent = projection.record(P.projection_id(p_complete, 1)) or {}
        check(intent_row, 'a completion that cannot be written leaves the committed intent, reported unknown',
              [(r['outcome'], r.get('reason')) for r in lost] == [('unknown_outcome', 'incomplete_transaction')]
              and len(api['messages']) == published + 1 and pending_intent.get('outcome') == 'pending'
              and pending_intent.get('attempt') == 1 and pending_intent.get('message_id') is None)
        check(intent_row, 'the platform identity of the unrecorded send is reported, not dropped',
              lost and (lost[0].get('platform') or {}).get('message_id') == api['next'])
        later = [r for _ in range(2) for r in projection.project() if r['assignment_id'] == p_complete]
        check(intent_row, 'a send whose outcome is unknown is never repeated',
              len(api['messages']) == published + 1
              and [(r['outcome'], r.get('reason')) for r in later] == [('unknown_outcome', 'incomplete_projection')] * 2)
        check(intent_row, 'metrics expose the unknown outcome', projection.metrics().get('unknown', 0) >= 1)

        # --- an echoed text that differs keeps the returned identity as a named anomaly ----------
        echo_row = 'projection/echo-mismatch-kept'
        command('pm', 'open', 'P-echo', assignment=content('decision'))
        p_echo = I.assignment_id(ids['repository_uuid'], 'P-echo')
        published = len(api['messages'])
        api['mode'] = 'normalize'
        echoed = [r for r in projection.project() if r['assignment_id'] == p_echo]
        api['mode'] = 'ok'
        anomaly = projection.record(P.projection_id(p_echo, 1)) or {}
        stored_bytes = api['messages'].get((anomaly.get('chat_id'), anomaly.get('message_id')))
        check(echo_row, 'the returned identity is kept, recorded as the named anomaly',
              [(r['outcome'], r.get('reason')) for r in echoed] == [('anomaly', 'presentation_mismatch')]
              and anomaly.get('outcome') == 'anomaly' and anomaly.get('anomalies') == ['presentation_mismatch']
              and type(anomaly.get('message_id')) is int and stored_bytes is not None)
        check(echo_row, 'the record keeps the platform\'s stored text beside the bytes sent',
              stored_bytes is not None and (anomaly.get('platform_text') or '').encode('utf-8') == stored_bytes
              and anomaly.get('presentation') != anomaly.get('platform_text')
              and P.presentation_digest((anomaly.get('presentation') or '').encode('utf-8')) == anomaly.get('presentation_digest'))
        later = [r for _ in range(2) for r in projection.project() if r['assignment_id'] == p_echo]
        check(echo_row, 'the anomalous message is never sent again',
              len(api['messages']) == published + 1
              and [(r['outcome'], r.get('reason')) for r in later] == [('anomaly', 'presentation_mismatch')] * 2)
        check(echo_row, 'metrics count the anomaly, not pending work', projection.metrics().get('anomalies', 0) >= 1)

        check('projection/send-outcomes', 'the token is never recorded',
              all(api['token'] not in _v64_json.dumps(o) for o in projection.observations)
              and api['token'] not in _v64_json.dumps(S.materialized_state(conn)['entities']))
        check('projection/send-outcomes', 'projection metrics count refusals and unprojected work',
              projection.metrics()['refused'] >= 2 and projection.metrics()['pending'] == 0)
        # --- each assignment goes to the chat enrolled for ITS owner ------------------------------
        routed = 'projection/owner-enrolled-chat'
        enroll('stranger', 5550002)
        enroll('owner', 5550001, filed_as='auditor')  # filed under the auditor, naming the owner
        command('pm-b', 'open', 'O-stranger', assignment=content('decision', owner='stranger', scope=['project-b']))
        command('pm', 'open', 'O-reviewer', assignment=content('decision', owner='reviewer'))
        command('pm', 'open', 'O-auditor', assignment=content('decision', owner='auditor'))
        o_stranger, o_reviewer, o_auditor = (I.assignment_id(ids['repository_uuid'], a)
                                             for a in ('O-stranger', 'O-reviewer', 'O-auditor'))
        asked = len(api['requests'])
        routing = {r['assignment_id']: r for r in projection.project()}
        new_requests = api['requests'][asked:]
        stranger_record = projection.record(P.projection_id(o_stranger, 1)) or {}
        check(routed, 'the stranger\'s assignment reaches the stranger\'s own chat only',
              [(chat, 'Owner: stranger' in text.split('\n')) for chat, text in new_requests] == [(5550002, True)]
              and routing[o_stranger]['outcome'] == 'sent' and stranger_record.get('chat_id') == 5550002)
        check(routed, 'the record binds the owner and the enrollment it routed by',
              stranger_record.get('owner') == 'stranger' and stranger_record.get('enrolled_chat') == 5550002
              and stranger_record.get('enrollment_id') == 'channel-enrollment:telegram_chat:stranger'
              and stranger_record.get('enrollment_version') == 1)
        check(routed, 'an owner with no enrolled chat gets a named refusal and no message',
              (routing[o_reviewer]['outcome'], routing[o_reviewer].get('reason')) == ('refused', 'no_enrolled_chat')
              and projection.record(P.projection_id(o_reviewer, 1)) is None)
        check(routed, 'an enrollment filed for one owner that names another is refused',
              (routing[o_auditor]['outcome'], routing[o_auditor].get('reason')) == ('refused', 'invalid_enrollment')
              and projection.record(P.projection_id(o_auditor, 1)) is None)
        enrolled = {5550001: 'owner', 5550002: 'stranger'}
        check(routed, 'no chat ever received another owner\'s assignment',
              api['requests'] and all('Owner: %s' % enrolled.get(chat) in text.split('\n') for chat, text in api['requests']))
        asked = len(api['requests'])
        again = {r['assignment_id']: r for r in projection.project()}
        check(routed, 'the refused owners stay refused and nothing is sent', len(api['requests']) == asked
              and again[o_reviewer].get('reason') == 'no_enrolled_chat' and again[o_auditor].get('reason') == 'invalid_enrollment')
        check(routed, 'the refused owners stay visible as unprojected work', projection.metrics()['pending'] == 2)
        try:
            P.TelegramEdge('http://127.0.0.1:%d' % server.server_address[1], api['token'], 5550001)
            check(routed, 'an edge given one configured chat is refused', False)
        except TypeError:
            check(routed, 'an edge given one configured chat is refused', True)
        # --- a message the platform placed in another chat is a named anomaly, never sent -------
        chat_row = 'projection/returned-chat-checked'
        command('pm', 'open', 'P-chat', assignment=content('decision'))
        p_chat = I.assignment_id(ids['repository_uuid'], 'P-chat')
        asked = len(api['requests'])
        api['chats'][5550001] = 5559999  # the platform answers that it published into another chat
        placed = [r for r in projection.project() if r['assignment_id'] == p_chat]
        del api['chats'][5550001]
        misplaced = projection.record(P.projection_id(p_chat, 1)) or {}
        check(chat_row, 'a message placed in another chat is the named anomaly, not a sent projection',
              [(r['outcome'], r.get('reason')) for r in placed] == [('anomaly', 'chat_mismatch')]
              and misplaced.get('outcome') == 'anomaly' and misplaced.get('anomalies') == ['chat_mismatch'])
        check(chat_row, 'the record keeps the chat the platform returned beside the enrolled chat',
              misplaced.get('chat_id') == 5559999 and misplaced.get('enrolled_chat') == 5550001
              and api['messages'].get((5559999, misplaced.get('message_id'))) == (misplaced.get('presentation') or '').encode('utf-8'))
        later = [r for _ in range(2) for r in projection.project() if r['assignment_id'] == p_chat]
        check(chat_row, 'the misplaced message is never sent again', len(api['requests']) == asked + 1
              and [(r['outcome'], r.get('reason')) for r in later] == [('anomaly', 'chat_mismatch')] * 2)
        # --- only Telegram's own 4xx refusal proves nothing was published ---------------------
        retry_row = 'projection/only-telegram-refusal-retried'
        for mode in ('gateway', 'telegram5xx', 'proxy4xx'):
            command('pm', 'open', 'P-' + mode, assignment=content('decision'))
            p_mode = I.assignment_id(ids['repository_uuid'], 'P-' + mode)
            asked = len(api['requests'])
            api['mode'] = mode
            answered_once = [r for r in projection.project() if r['assignment_id'] == p_mode]
            api['mode'] = 'ok'
            later = [r for _ in range(2) for r in projection.project() if r['assignment_id'] == p_mode]
            recorded = projection.record(P.projection_id(p_mode, 1)) or {}
            check(retry_row, mode + ': a reply after delivery that is not Telegram\'s own refusal is unknown',
                  [r['outcome'] for r in answered_once] == ['unknown_outcome'] and recorded.get('outcome') == 'unknown_outcome'
                  and recorded.get('attempt') == 1 and recorded.get('message_id') is None)
            check(retry_row, mode + ': the message is published once and never sent again',
                  len(api['requests']) == asked + 1 and [r['outcome'] for r in later] == ['unknown_outcome'] * 2)
        # Additive control: Telegram's own refusal, a 4xx answer with ok false, is attempted again.
        command('pm', 'open', 'P-limit', assignment=content('decision'))
        p_limit = I.assignment_id(ids['repository_uuid'], 'P-limit')
        asked = len(api['requests'])
        api['mode'] = 'limit'
        limited = [r['outcome'] for r in projection.project() if r['assignment_id'] == p_limit]
        api['mode'] = 'ok'
        retried = [r['outcome'] for r in projection.project() if r['assignment_id'] == p_limit]
        check(retry_row, 'control: Telegram\'s own 4xx refusal publishes nothing and is attempted again',
              limited == ['refused'] and retried == ['sent'] and len(api['requests']) == asked + 1
              and (projection.record(P.projection_id(p_limit, 1)) or {}).get('attempt') == 2)
        # --- a malformed reply is an unknown outcome with an observation; the loop goes on -----
        protocol_row = 'projection/protocol-error-unknown'

        def attempt(projector):
            try:
                return projector.project()
            except Exception as exc:  # recorded as a failed check, so the suite finishes its rows
                return [{'assignment_id': None, 'outcome': 'raised ' + type(exc).__name__}]
        garbled = []
        for alias in ('P-garbled-1', 'P-garbled-2'):
            command('pm', 'open', alias, assignment=content('decision'))
            garbled.append(I.assignment_id(ids['repository_uuid'], alias))
        asked, observed = len(api['requests']), len(projection.observations)
        api['mode'] = 'garbage'
        garbage_run = attempt(projection)
        try:
            probe = projection.edge.send(5550001, 'probe')
        except P.EdgeRefused as exc:
            probe = exc.code
        except Exception as exc:
            probe = 'raised ' + type(exc).__name__
        api['mode'] = 'ok'
        check(protocol_row, 'the edge answers a malformed status line as unknown_outcome, never raising',
              probe == 'unknown_outcome')
        check(protocol_row, 'one run over malformed replies returns a result for every entry, each unknown',
              [r['outcome'] for r in garbage_run if r['assignment_id'] in garbled] == ['unknown_outcome'] * 2
              and len(api['requests']) == asked + 3)
        seen = [o for o in projection.observations[observed:] if o['assignment_id'] in garbled]
        check(protocol_row, 'each malformed reply leaves an observation of the unknown outcome',
              [o['outcome'] for o in seen] == ['unknown_outcome'] * 2
              and all((projection.record(P.projection_id(a, 1)) or {}).get('outcome') == 'unknown_outcome' for a in garbled))
        later = [r for _ in range(2) for r in attempt(projection) if r['assignment_id'] in garbled]
        check(protocol_row, 'later runs finish and send neither again',
              len(api['requests']) == asked + 3 and [r['outcome'] for r in later] == ['unknown_outcome'] * 4)

        class _RaisingEdge:
            def send(self, chat, text):
                raise RuntimeError('an edge outside the projection module')
        raised = []
        for alias in ('P-raising-1', 'P-raising-2'):
            command('pm', 'open', alias, assignment=content('decision'))
            raised.append(I.assignment_id(ids['repository_uuid'], alias))
        raising = P.Projection(S, inbox, _RaisingEdge(), conn, 'authority', journal_sign)
        raising_run = attempt(raising)
        check(protocol_row, 'whatever an edge raises after the intent is an unknown outcome and the loop goes on',
              [r['outcome'] for r in raising_run if r['assignment_id'] in raised] == ['unknown_outcome'] * 2
              and [o['outcome'] for o in raising.observations if o['assignment_id'] in raised] == ['unknown_outcome'] * 2
              and all((projection.record(P.projection_id(a, 1)) or {}).get('outcome') == 'unknown_outcome' for a in raised))
        try:
            P.TelegramEdge('http://example.invalid', api['token'])
            check('projection/send-outcomes', 'a plain-HTTP remote origin is refused', False)
        except P.EdgeRefused as exc:
            check('projection/send-outcomes', 'a plain-HTTP remote origin is refused', exc.code == 'invalid_input')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)

    # --- an answer verifies against the key active when it was accepted, whatever rotates later ---
    rotated = 'inbox/answer-survives-key-rotation'

    def signed_with(key_file, who, operation, alias, **fields):
        counter[0] += 1
        body = dict(ids, operation=operation, alias=alias, principal=who, command_id='c-%d' % counter[0],
                    nonce='n-%d' % counter[0], **fields)
        return inbox.apply({'command': body, 'signature': sign_as(key_file, S.canonical_bytes(body))})
    cid5 = claims.claim_id(ids['repository_uuid'], 'unit-5')
    rot1, rot2, rot3 = (I.assignment_id(ids['repository_uuid'], a) for a in ('K-rot-1', 'K-rot-2', 'K-rot-3'))
    opened_rot1 = command('worker-b', 'open', 'K-rot-1', claim_generation=(entity(cid5) or {}).get('data', {}).get('generation'),
                          assignment=content('decision', owner='rotator'))
    answered_rot1 = command('rotator', 'answer', 'K-rot-1', request_version=1, ruling='accept')
    # An accepted rotation: the old key is retired, a new key takes effect, and both are kept (R38).
    rotated_at = _v64_time.time()
    fixture('key-rotator', 'verification_key', dict(principal='rotator', public_key=public['rotator'], effective_at=0,
                                                    retired_at=rotated_at))
    fixture('key-rotator-2', 'verification_key', dict(principal='rotator', public_key=public['rotator-new'],
                                                      effective_at=rotated_at))
    check(rotated, 'an owner answer accepted before a rotation is still admitted after it',
          opened_rot1.get('released_claim') == cid5 and answered_rot1.get('ok') is True and inbox.admit(rot1)['admitted'] is True)
    command('pm', 'open', 'K-rot-2', assignment=content('decision', owner='rotator'))
    retired_sign = signed_with('rotator', 'rotator', 'answer', 'K-rot-2', request_version=1, ruling='accept')
    check(rotated, 'control: the retired key signs no new answer', retired_sign == {'ok': False, 'reason': 'not_authorized'})
    answered_rot2 = signed_with('rotator-new', 'rotator', 'answer', 'K-rot-2', request_version=1, ruling='reject')
    # The reviewer's form: the key entity is replaced in place by another public key.
    fixture('key-rotator-2', 'verification_key', dict(principal='rotator', public_key=public['rotator-next'],
                                                      effective_at=rotated_at))
    check(rotated, 'an answer whose key entity was later replaced in place is still admitted',
          answered_rot2.get('ok') is True and inbox.admit(rot2)['admitted'] is True and inbox.admit(rot1)['admitted'] is True)
    resumed_rot1 = command('worker-b', 'resume', 'K-rot-1', request_version=1, capabilities=[])
    claim5 = (entity(cid5) or {}).get('data', {})
    check(rotated, 'the unit parked on the rotated answer resumes; it is not parked for good',
          resumed_rot1.get('ok') is True and claim5.get('state') == 'owned' and claim5.get('holder') == 'worker-b'
          and claim5.get('resumed_from') == rot1)
    # Negative control: a revocation dated at or before the acceptance reaches back into history.
    opened_rot3 = command('worker-b', 'open', 'K-rot-3', claim_generation=claim5.get('generation'),
                          assignment=content('decision', owner='rotator'))
    before_rot3 = _v64_time.time()
    answered_rot3 = signed_with('rotator-next', 'rotator', 'answer', 'K-rot-3', request_version=1, ruling='accept')
    admitted_rot3 = inbox.admit(rot3)['admitted']
    fixture('key-rotator-2', 'verification_key', dict(principal='rotator', public_key=public['rotator-next'],
                                                      effective_at=rotated_at, revoked_at=before_rot3))
    check(rotated, 'control: a key revoked from before the acceptance admits nothing it signed',
          opened_rot3.get('ok') is True and answered_rot3.get('ok') is True and admitted_rot3 is True
          and inbox.admit(rot3)['reason'] == 'missing_authority')
    check(rotated, 'control: that revocation does not reach an answer signed with another key',
          inbox.admit(rot2)['admitted'] is True and inbox.admit(rot1)['admitted'] is True)

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
    fixture(I.assignment_id('other-repository', 'Y-1'), 'assignment', dict(held, alias='Y-1', repository_uuid='other-repository'))
    invalid_ids = [I.assignment_id(ids['repository_uuid'], a) for a in ('X-state', 'X-kind', 'X-tamper')]
    after = {e['id']: e for e in inbox.index()['entries']}
    check('inbox/visible-invalid', "another repository's assignment is not in this inbox",
          I.assignment_id('other-repository', 'Y-1') not in after)
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
    t_answer = I.assignment_id(ids['repository_uuid'], 'T-answer')
    genuine_answer = entity(t_answer)['data']['answer']
    fixture(forged, 'assignment', dict(held, alias='X-forged', unit_id=None, state='SUBMITTED', answer=genuine_answer))
    command('pm', 'open', 'X-rewritten', assignment=content('decision'))
    command('owner', 'answer', 'X-rewritten', request_version=1, ruling='accept')
    rewritten = I.assignment_id(ids['repository_uuid'], 'X-rewritten')
    fixture(rewritten, 'assignment', dict(entity(rewritten)['data'], brief='A different question.'))
    command('pm', 'open', 'X-revoked', assignment=content('decision'))
    revoked_answer = command('owner', 'answer', 'X-revoked', request_version=1, ruling='reject')
    admissions = {
        'displayed assigned status on a pending record': inbox.admit(labelled),
        'displayed assigned status on an invalid record': inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-state')),
        'answer copied onto another record by a service write': inbox.admit(forged),
        'answered record rewritten by a service write after the answer': inbox.admit(rewritten),
        'declined': inbox.admit(I.assignment_id(ids['repository_uuid'], 'T-decline')),
        'canceled': inbox.admit(I.assignment_id(ids['repository_uuid'], 'T-cancel')),
        'pending': inbox.admit(aliases['acknowledgement']),
        'absent': inbox.admit(I.assignment_id(ids['repository_uuid'], 'nothing')),
    }
    genuine = inbox.admit(t_answer)
    before_revocation = inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-revoked'))
    # --- admission verifies the owner's own signature over the exact answer ------------------------
    signed_row = 'inbox/admit-verifies-owner-signature'
    stored_answer = entity(t_answer)['data']['answer']
    owner_signers = base / 'owner_signers'
    owner_signers.write_text('owner namespaces="%s" %s\n' % (AC.SIGNATURE_NAMESPACE, public['owner']))
    answer_sig = base / 'answer.sig'
    answer_sig.write_text(stored_answer.get('signature') or '')
    answer_verified = _v64_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(owner_signers), '-I', 'owner', '-n',
                                   AC.SIGNATURE_NAMESPACE, '-s', str(answer_sig)],
                                  input=S.canonical_bytes(stored_answer.get('command') or {}), capture_output=True, timeout=10)
    signed_command = stored_answer.get('command') or {}
    check(signed_row, 'the record keeps the owner\'s signed answer, verifiable with ssh-keygen alone',
          answer_verified.returncode == 0 and signed_command.get('alias') == 'T-answer'
          and signed_command.get('ruling') == stored_answer.get('ruling') == 'accept')
    # A generic upsert naming the owner as principal, carrying an answer the owner never signed.
    command('pm', 'open', 'F-1', assignment=content('decision'))
    f1 = I.assignment_id(ids['repository_uuid'], 'F-1')
    upsert_id = 'fixture-%d' % (serial[0] + 1)
    unsigned = dict(ids, operation='answer', alias='F-1', principal='owner', command_id=upsert_id, nonce='n-f1',
                    request_version=1, ruling='accept')
    wrote = fixture(f1, 'assignment', dict(entity(f1)['data'], state='SUBMITTED', answer=dict(
        principal='owner', ruling='accept', request_version=1, command_id=upsert_id, command=unsigned,
        signature=sign_as('stranger', S.canonical_bytes(unsigned)))), principal='owner')
    forged_admit = inbox.admit(f1)
    check(signed_row, 'an upsert naming the owner, with an answer the owner never signed, is not admitted',
          wrote['command_id'] == upsert_id and forged_admit == {'admitted': False, 'reason': 'missing_authority',
                                                                'assignment_id': f1, 'version': 2})
    # The owner's genuine signature over another assignment's answer, carried by a forged record
    # whose write also pins the owner's key, so only the binding of the signed command refuses it.
    command('pm', 'open', 'F-2', assignment=content('decision'))
    f2 = I.assignment_id(ids['repository_uuid'], 'F-2')
    upsert_id = 'fixture-%d' % (serial[0] + 1)
    fixture(f2, 'assignment', dict(entity(f2)['data'], state='SUBMITTED', answer=dict(
        stored_answer, command_id=upsert_id)), principal='owner', pins=('key-owner',))
    check(signed_row, 'a genuine owner signature over another answer is not admitted',
          inbox.admit(f2)['reason'] == 'missing_authority')
    check(signed_row, 'control: the owner\'s own signed answer admits', genuine['admitted'] is True)

    fixture('owner', 'membership', dict(members['owner'], revoked_at=_v64_time.time() - 1, expires_at=None))
    admissions['answer whose owner is no longer a member'] = inbox.admit(I.assignment_id(ids['repository_uuid'], 'X-revoked'))
    for label, result in admissions.items():
        check('inbox/unauthorized-admission', 'refused: ' + label, result['admitted'] is False)
    check('inbox/unauthorized-admission', 'refusals are named',
          admissions['displayed assigned status on a pending record']['reason'] == 'not_answered'
          and admissions['displayed assigned status on an invalid record']['reason'] == 'invalid_record'
          and admissions['answer copied onto another record by a service write']['reason'] == 'missing_authority'
          and admissions['answered record rewritten by a service write after the answer']['reason'] == 'missing_authority'
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
