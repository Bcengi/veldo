"""VELDO-0133: ask what becomes of work whose person assignment is declined, canceled or expired.

Only shared ROOT and expect are consumed. One temporary tree holds an installed .veldo copy; the two
production anchors below are the registered mutation driver's seams, so a mutation of the inbox or the
claim organ reaches every reader (the claim organ loads its sibling organs from its own directory). The
store is the real SQLite authority with OpenSSH journal and command signatures. Each blocked unit is
claimed and parked by a real child worker process that claims through the claim Receiver, opens its
person assignment and exits. Disposition questions reach Telegram through the ordinary VELDO-0064
projection over real HTTP to a loopback Bot API endpoint (never a real Telegram service or token), and
an `other` instruction reaches the real VELDO-0126 Intake on the same store through its public
attested submission, read back through the intake's own reader. The answer carries real evidence: a
message the addressee sent in their own chat, taken by the real VELDO-0066 Acquirer from the loopback
getUpdates, or a request packet the API edge signed. The intake's third production anchor lets a
mutation of the attested submission reach the suite as well.

THE SET IS DERIVED. The criterion rows are keyed by (reason, principal type, role), derived from the
inbox's PARKED_REASONS and the proposal_commit boundary (authority_contract.BOUNDARIES), so a reason or
a principal type added later with no row reds `disposition/set-derived`. The reasons that are not in
the set are named below with why.

TWO STORE FIXTURES, BECAUSE NO RELEASE 1 COMMAND PRODUCES THEM. No command produces EXPIRED, so the
expired record is written to the store as a fixture over a unit really parked by its worker. No person
can hold a claim (the claim boundary admits agent runs and services), so a person requester's
assignment over a parked unit is laid the same way: the worker parks the unit and a fixture names a
person as the requester; the cancel itself is the person's real signed command.

When the change is absent (the pre-change tree, for the red record) the inbox refuses ask and dispose
and opens no question, and the suite's own assertions fail; nothing is skipped by a raise.
"""


def _v133_suite():
    import collections
    import contextlib
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {'control_assignment.py': ROOT / ".veldo" / "control_assignment.py",
                  'control_claim.py': ROOT / ".veldo" / "control_claim.py",
                  'control_intake.py': ROOT / ".veldo" / "control_intake.py"}
    PREFIX = 'VELDO-0133 '
    # PARKED_REASONS outside the AC1 set, and why each is outside it.
    NOT_ASKED = {'awaiting_answer': 'the owner has not answered yet; the answer is its way back',
                 'ready_to_resume': 'resume is its way back',
                 'invalid_assignment': 'an unreadable or forged record: out of review scope',
                 'missing_assignment': 'no record at all: out of review scope',
                 'awaiting_disposition': 'the disposition question itself is waiting',
                 'ready_to_dispose': 'dispose is its way back',
                 'routed_to_intake': 'asked again through ask, driven by the walk'}

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    observed, emitted, raised, regions = {}, set(), [], []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok = False
                name = '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        observed.setdefault('failed_parts', {})[label] = failed
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    class BotApi(http.server.BaseHTTPRequestHandler):
        """Loopback getMe, getUpdates and sendMessage with the Bot API request and answer shapes;
        records every sendMessage."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            if self.path == '/bot%s/getMe' % st['token']:
                return self._answer(200, {'ok': True, 'result': dict(st['bot'], can_join_groups=True,
                                                                     can_read_all_group_messages=False,
                                                                     supports_inline_queries=False)})
            if self.path == '/bot%s/getUpdates' % st['token']:
                offset = body.get('offset') or 0
                if offset:
                    st['updates'] = [u for u in st['updates'] if u['update_id'] >= offset]
                return self._answer(200, {'ok': True, 'result': st['updates'][:body.get('limit') or 100]})
            if self.path != '/bot%s/sendMessage' % st['token']:
                return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})
            st['requests'].append((body.get('chat_id'), body.get('text')))
            st['next'] += 1
            message = {'message_id': st['next'], 'date': 1790300000 + st['next'], 'from': dict(st['bot']),
                       'chat': {'id': body.get('chat_id'), 'type': 'private'}, 'text': body.get('text')}
            st['messages'][(body.get('chat_id'), st['next'])] = body.get('text')
            self._answer(200, {'ok': True, 'result': message})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    worker_script = r'''
import json, subprocess, sys
key, namespace, ids, principal, unit, alias, content = (sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4],
                                                        sys.argv[5], sys.argv[6], json.loads(sys.argv[7]))
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
def ask(command):
    signature = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", key, "-n", namespace], input=canonical(command),
                               capture_output=True, check=True, timeout=20).stdout.decode()
    print(json.dumps({"packet": {"command": command, "signature": signature}}), flush=True)
    return json.loads(sys.stdin.readline())["result"]
claim = ask(dict(ids, operation="claim", unit_id=unit, principal=principal, command_id="w-claim-" + alias,
                 nonce="w-claim-n-" + alias, generation=0, capabilities=[]))
if not claim.get("ok"):
    sys.exit(3)
reply = ask(dict(ids, operation="open", alias=alias, principal=principal, command_id="w-open-" + alias,
                 nonce="w-open-n-" + alias, claim_generation=claim["claim"]["generation"], assignment=content))
if reply.get("ok") and reply.get("stop_requester"):
    sys.exit(0)
sys.stdin.readline()  # a worker that is not told to stop waits here for the person's answer
sys.exit(4)
'''

    servers, children = [], []
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v133-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, path in PRODUCTION.items():
            shutil.copyfile(path, mods / name)
        conn = None
        try:
            with region('install/assets'):
                scaffold = load('v133_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
                parts = []
                for rel in ('.veldo/control_assignment.py', '.veldo/control_claim.py', '.veldo/control_intake.py'):
                    laid = base / 'laid' / rel
                    scaffold._lay(ROOT / 'engine' / rel, laid, rel, [], [])
                    parts += [(rel + ' installed by the scaffold', rel in scaffold._FILES),
                              (rel + ' engine copy identical', (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                              (rel + ' laid by the installer', laid.is_file() and laid.read_bytes() == (ROOT / rel).read_bytes())]
                check('install/assets', parts)

            claims = load('v133_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            contract = load('v133_contract', mods / 'entity_contract.py')
            I = load('v133_inbox', mods / 'control_assignment.py')
            P = load('v133_projection', mods / 'control_channel_projection.py')
            V = load('v133_presentation', mods / 'control_channel_presentation.py')
            A = load('v133_attribution', mods / 'control_channel_attribution.py')
            IN = load('v133_intake', mods / 'control_intake.py')
            CHOICES = list(getattr(I, 'DISPOSITION_CHOICES', ('close', 'backlog', 'other')))

            keys = base / 'keys'
            keys.mkdir(mode=0o700)
            public = {}
            people = ('olga', 'alice', 'pete', 'paula', 'sam', 'rita', 'dora', 'mallory', 'zed1', 'zed2', 'wide')
            services = ('worker', 'svc', 'pm', 'api-edge', 'telegram-edge')
            olds = ('old-alice', 'old-pete', 'old-paula', 'old-olga')
            for who in ('authority',) + people + services + olds:
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v133-' + who, '-f', str(keys / who)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = (keys / (who + '.pub')).read_text().strip()

            def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(message):
                return sign_as('authority', message, 'veldo-journal')

            DOMAIN, REPO = 'disposition-domain', 'disposition-repository'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='disposition-store')
            conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
            serial = [0]

            def fixture(eid, kind, data):
                serial[0] += 1
                current = S.materialized_state(conn)['entities']
                S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                     parameters=dict(entity_id=eid, kind=kind, data=data),
                                     expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                     nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

            def entity(eid):
                return S.materialized_state(conn)['entities'].get(eid)

            members = {'olga': ('person', ['project_owner'], ['proj-a', 'ops']), 'alice': ('person', [], ['proj-a']),
                       'pete': ('person', [], ['proj-a']), 'paula': ('person', ['project_owner'], ['ops']),
                       'sam': ('person', [], ['ops']), 'rita': ('person', [], ['proj-a']), 'dora': ('person', [], ['proj-a']),
                       'mallory': ('person', [], ['proj-a', 'ops']), 'zed1': ('person', ['project_owner'], ['proj-z']),
                       'zed2': ('person', ['project_owner'], ['proj-z']), 'wide': ('person', [], ['proj-a', 'proj-z']),
                       'worker': ('agent_run', [], '*'),
                       'svc': ('service', [], '*'), 'pm': ('service', [], ['proj-a', 'ops', 'proj-z']),
                       'api-edge': ('service', [], '*'), 'telegram-edge': ('service', [], ['proj-a'])}
            for who, (kind, roles, scope) in members.items():
                fixture(who, 'membership', dict(principal_type=kind, roles=roles, scope=scope, revoked_at=None, expires_at=None))
                if who != 'telegram-edge':
                    fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
            for old in olds:  # an earlier key of each addressee, revoked long before any answer
                fixture('key-' + old, 'verification_key', dict(principal=old[4:], public_key=public[old], effective_at=0,
                                                               revoked_at=1))
            fixture(AC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
                    dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
            chats = {'alice': 7330001, 'pete': 7330002, 'paula': 7330003, 'olga': 7330004, 'wide': 7330009}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            fixture('project:proj-a', 'project', dict(name='proj-a', state='ACTIVE'))
            fixture('objective:a1', 'objective', dict(project_uuid='project:proj-a', state='ACTIVE'))
            fixture('project:proj-z', 'project', dict(name='proj-z', state='ACTIVE'))
            fixture('objective:z1', 'objective', dict(project_uuid='project:proj-z', state='ACTIVE'))

            # The AC1 set: (reason, principal type that ended it, role), with the person expected to be asked.
            CASES = [
                dict(name='c1', key=('declined', 'person', 'owner'), owner='alice', requester='worker',
                     end=('alice', 'decline'), expect='alice', why='decliner', ruling='other', arrival='telegram'),
                dict(name='c2', key=('canceled', 'person', 'requester'), owner='alice', requester='worker', relabel='pete',
                     end=('pete', 'cancel'), expect='pete', why='canceler', ruling='close', sibling=True),
                dict(name='c3', key=('canceled', 'person', 'project_owner'), owner='sam', scope=['ops'], requester='worker',
                     end=('paula', 'cancel'), expect='paula', why='canceler', ruling='backlog'),
                dict(name='c4', key=('canceled', 'agent_run', 'requester'), owner='alice', requester='worker', revise=True,
                     end=('worker', 'cancel'), expect='olga', why='project_owner', ruling='other', arrival='api'),
                dict(name='c5', key=('canceled', 'service', 'requester'), owner='alice', requester='svc',
                     end=('svc', 'cancel'), expect='olga', why='project_owner', ruling='backlog'),
                dict(name='c6', key=('expired', None, None), owner='alice', requester='worker', expire=True,
                     end=('pm', 'ask'), expect='olga', why='project_owner', ruling='close'),
                dict(name='c7', key=('answer_not_admitted', None, 'revoked_key'), owner='rita', requester='worker',
                     revoke=True, end=('pm', 'ask'), expect='olga', why='project_owner', ruling='other', arrival='telegram'),
            ]
            # Beside the set: no project owner resolves (no chain; two owners), a decline that blocks no unit,
            # and an addressee with no enrolled chat whose answer is later struck by a back-dated revocation.
            EXTRA = [dict(name='n1', owner='alice', requester='worker', end=('worker', 'cancel'), chain=None),
                     dict(name='n2', owner='zed1', scope=['proj-z'], requester='worker', expire=True, end=('pm', 'ask'),
                          chain='objective:z1'),
                     dict(name='n4', owner='dora', requester='worker', end=('dora', 'decline'), expect='dora')]
            for case in CASES + EXTRA:
                case['unit'], case['backlog'], case['alias'] = 'unit-' + case['name'], 'backlog:' + case['name'], 'S-' + case['name']
                case['source'] = I.assignment_id(REPO, case['alias'])
                case['cid'] = claims.claim_id(REPO, case['unit'])
                case.setdefault('scope', ['proj-a'])
                chain = case.get('chain', 'objective:a1')
                fixture(case['backlog'], 'backlog_item', dict(dict(state='PRIORITIZED', repository_uuid=REPO),
                                                              **({'objective_uuid': chain} if chain else {})))
                fixture(case['unit'], 'execution_unit', dict(state='READY', repository_uuid=REPO, backlog_item_uuid=case['backlog'],
                                                             requirements=[], eligible_holders=['worker', 'svc']))
            fixture('unit-c2-sibling', 'execution_unit', dict(state='READY', repository_uuid=REPO, backlog_item_uuid='backlog:c2',
                                                              requirements=[], eligible_holders=['worker']))

            BOT = 8133000001
            api = {'token': 'disposition-bot', 'next': 9000, 'messages': {}, 'requests': [], 'updates': [],
                   'bot': {'id': BOT, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_disposition_bot'}}
            bot_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), type('V133BotApi', (BotApi,), {'state': api}))
            servers.append(bot_server)
            threading.Thread(target=bot_server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % bot_server.server_address[1]

            reader = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, reader, V.TelegramPresentationEdge(P, url, api['token']), conn, 'authority',
                                    journal_sign, assignment=I)
            acquirer = A.Acquirer(S, CM, P, V, presenter, A.TelegramAcquisitionEdge(P, url, api['token']), conn,
                                  'authority', journal_sign, 'telegram-edge', lambda m: sign_as('telegram-edge', m))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=('proj-a', 'proj-z'), api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign,
                               asker=V.TelegramPresentationEdge(P, url, api['token']))
            try:
                inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign, intake=intake)
            except TypeError:  # the pre-change inbox takes no intake
                inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            receiver = claims.Receiver(conn, ids, 'authority', journal_sign)
            projection = P.Projection(S, inbox, P.TelegramEdge(url, api['token']), conn, 'authority', journal_sign)
            counter = [0]

            def command(who, operation, alias, key=None, beside=None, **fields):
                counter[0] += 1
                body = dict(ids, operation=operation, alias=alias, principal=who, command_id='c133-%d' % counter[0],
                            nonce='n133-%d' % counter[0], **fields)
                packet = {'command': body, 'signature': sign_as(key or who, S.canonical_bytes(body))}
                packet.update(beside or {})
                return inbox.apply(packet)

            def claim(who, unit):
                counter[0] += 1
                body = dict(ids, operation='claim', unit_id=unit, principal=who, command_id='k133-%d' % counter[0],
                            nonce='kn133-%d' % counter[0], generation=0, capabilities=[])
                return receiver.apply({'command': body, 'signature': sign_as(who, S.canonical_bytes(body))})

            def content(case):
                return dict(kind='decision', owner=case['owner'], scope=list(case['scope']), deadline='2026-10-01T17:00:00Z',
                            budget={'owner_minutes': 15}, brief='Choose how the work proceeds.', choices=['accept', 'reject'],
                            subject={'kind': 'specification', 'ref': 'specs/EXAMPLE.md', 'digest': 'sha256:' + '1' * 64},
                            unit_id=case['unit'])

            def park(case):
                """A real child worker claims the unit through the Receiver, opens the assignment and exits."""
                child = subprocess.Popen([sys.executable, '-c', worker_script, str(keys / case['requester']),
                                          AC.SIGNATURE_NAMESPACE, json.dumps(ids), case['requester'], case['unit'],
                                          case['alias'], json.dumps(content(case))],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                children.append(child)
                replies = []
                for handler in (receiver.apply, inbox.apply):
                    line = child.stdout.readline()
                    if not line:
                        break
                    result = handler(json.loads(line)['packet'])
                    replies.append(result)
                    child.stdin.write(json.dumps({'result': {k: v for k, v in result.items() if k != 'receipt'}}) + '\n')
                    child.stdin.flush()
                try:
                    code = child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    code = child.wait()
                child.stdin.close()
                child.stdout.close()
                return replies, code

            def questions(source):
                """The disposition questions about `source`, read from the store itself, oldest round first."""
                found = [dict(e, id=eid) for eid, e in S.materialized_state(conn)['entities'].items()
                         if e['kind'] == 'assignment' and isinstance(e.get('data'), dict)
                         and e['data'].get('kind') == 'disposition'
                         and (e['data'].get('disposition_of') or {}).get('assignment_id') == source]
                return sorted(found, key=lambda e: e['data']['disposition_of'].get('round', 0))

            def question(case, round_=1):
                found = questions(case['source'])
                return found[round_ - 1] if len(found) >= round_ else None

            def parked_by_unit():
                return {p.get('unit_id'): p for p in inbox.parked_units()}

            def held(case):
                c = (entity(case['cid']) or {}).get('data') or {}
                return c.get('state') != 'released' or c.get('holder') is not None

            INTAKE = ('intake_source', 'intake_proposal', 'intake_question')

            def intake_rows():
                return sorted(conn.execute('SELECT id, version FROM entities WHERE kind IN (?,?,?)', INTAKE).fetchall())

            def snapshot(case):
                return tuple((e or {}).get('version') and ((e or {}).get('version'), json.dumps((e or {}).get('data'), sort_keys=True))
                             for e in (entity(case['unit']), entity(case['backlog']), entity(case['cid']))) + (tuple(intake_rows()),)

            updates = [500000000]

            def sent(sender, chat, text, chat_type='private'):
                """One message `sender` sends in `chat`, delivered by the loopback getUpdates and kept by the
                real Acquirer; returns the id of its kept evidence."""
                api['next'] += 1
                updates[0] += 1
                where = {'id': chat, 'type': chat_type}
                where.update({'first_name': 'Person'} if chat_type == 'private' else {'title': 'Team'})
                api['updates'].append({'update_id': updates[0], 'message': {
                    'message_id': api['next'], 'date': 1790400000 + api['next'], 'text': text, 'chat': where,
                    'from': {'id': sender, 'is_bot': False, 'first_name': 'Person', 'language_code': 'en'}}})
                acquirer.acquire()
                return A.evidence_id(BOT, updates[0])

            def api_request(principal, request_id, text, signer='api-edge'):
                body = {'schema': IN.API_SCHEMA, 'domain': DOMAIN, 'request_id': request_id, 'edge': 'api-edge',
                        'principal': principal, 'text': text, 'project': None, 'clarifies': None}
                return {'request': body, 'signature': sign_as(signer, S.canonical_bytes(body))}

            def arrival(case, who=None):
                """Real evidence of where the answer arrived: a message the addressee sent in their own chat,
                or a request the API edge signed for them."""
                who = who or case['expect']
                counter[0] += 1
                if case.get('arrival') == 'api':
                    packet = api_request(who, 'req-%s-answer-%d' % (case['name'], counter[0]), 'Other: see the instruction.')
                    return dict(packet, source_kind='api_request')
                return {'source_kind': 'telegram_message', 'evidence_id': sent(chats[who], chats[who], 'Other, see the instruction.')}

            def arrival_source(arrived):
                """(kind, id) of the source the evidence names, read from the evidence itself."""
                if arrived.get('source_kind') == 'api_request':
                    return 'api_request', (arrived.get('request') or {}).get('request_id')
                kept = acquirer.evidence(arrived.get('evidence_id') or '') or {}
                fields = kept.get('fields') or {}
                return 'telegram_message', '%s:%s:%s' % (kept.get('bot_id'), fields.get('chat_id'), fields.get('message_id'))

            def instruction(case):
                # Words that name other rulings, a blank line and a trailing space: nothing is inferred and
                # the text is kept exactly as signed.
                return ('Close the %s thread and move the rest to the backlog?\n\nNo: hand it to the platform team '
                        'and ask Igor first. ' % case['name'])

            steps = collections.defaultdict(dict)  # case name -> step -> what the walk read

            def walk(step, cases):
                listed = parked_by_unit()
                metrics = inbox.metrics()
                waiting = inbox.waiting_resources()
                for case in cases:
                    entry = listed.get(case['unit'])
                    was_held = held(case)
                    found = questions(case['source'])
                    latest = (found[-1] if found else {}).get('data') or {}
                    reached = {'opened': len(found) == 1 and latest.get('state') == 'OFFERED',
                               'answered': len(found) == 1 and latest.get('state') == 'SUBMITTED',
                               'disposed': len(found) == 1 and entity('assignment-disposition:' + found[-1]['id']) is not None,
                               'asked_again': len(found) == 2 and latest.get('state') == 'OFFERED'}.get(step, False)
                    attempt = claim('worker', case['unit'])
                    steps[case['name']][step] = dict(
                        reason=(entry or {}).get('reason'), listed=entry is not None, entry=entry, claim=attempt, reached=reached,
                        held_before=was_held, waiting=waiting, alive=[c.pid for c in children if c.poll() is None],
                        by_reason=metrics.get('parked_by_reason'),
                        counted=collections.Counter(p.get('reason') for p in listed.values()))

            # --- AC1: every way an assignment ends without admitting opens one question ---------------------
            with region('disposition/question-opened', 'disposition/set-derived', 'disposition/addressee',
                        'disposition/no-project-owner'):
                reasons = [r for r in I.PARKED_REASONS if r not in NOT_ASKED]
                derived = set()
                for r in reasons:
                    if r == 'declined':
                        derived.add((r, 'person', 'owner'))
                    elif r == 'canceled':
                        derived.update((r, t, 'requester') for t in AC.BOUNDARIES['proposal_commit'])
                        derived.add((r, 'person', 'project_owner'))
                    elif r == 'answer_not_admitted':
                        derived.add((r, None, 'revoked_key'))
                    else:
                        derived.add((r, None, None))
                keyed = {c['key'] for c in CASES}
                check('disposition/set-derived', [
                    ('every case is a member of the derived set, and the set has no member without a case', keyed == derived),
                    ('the inbox asks for exactly the derived reasons', set(getattr(I, 'DISPOSITION_REASONS', ())) == set(reasons)),
                    ('every reason outside the set is named with why', set(I.PARKED_REASONS) - set(reasons) <= set(NOT_ASKED)),
                    ('the inbox reports the question states as parked reasons',
                     {'awaiting_disposition', 'ready_to_dispose', 'routed_to_intake'} <= set(I.PARKED_REASONS)),
                    ('the arrival kinds are the intake source kinds', tuple(getattr(I, 'ARRIVAL_KINDS', ())) == IN.SOURCE_KINDS)])

                for case in CASES + EXTRA:
                    case['parked'], case['exit'] = park(case)
                    if case.get('relabel'):
                        fixture(case['source'], 'assignment', dict(entity(case['source'])['data'], requested_by=case['relabel']))
                    if case.get('revise'):
                        case['revised'] = command('worker', 'revise', case['alias'], request_version=1,
                                                  changes={'deadline': '2026-10-02T12:00:00Z'})
                    if case.get('expire'):
                        fixture(case['source'], 'assignment', dict(entity(case['source'])['data'], state='EXPIRED'))
                    if case.get('revoke'):
                        before_answer = time.time()
                        case['source_answer'] = command(case['owner'], 'answer', case['alias'], request_version=1, ruling='accept')
                        fixture('key-' + case['owner'], 'verification_key', dict(
                            principal=case['owner'], public_key=public[case['owner']], effective_at=0, revoked_at=before_answer))
                    source = (entity(case['source']) or {}).get('data') or {}
                    case['request_version'] = source.get('request_version')
                    case['reason_before'] = (parked_by_unit().get(case['unit']) or {}).get('reason')
                    who, how = case['end']
                    case['ended'] = command(who, how, case['alias'], request_version=case['request_version'])
                    case['questions'] = questions(case['source'])
                # A decline of an assignment that blocks no unit: pm opens it without holding a claim.
                loose = command('pm', 'open', 'S-n3', assignment=dict(content(dict(owner='alice', scope=['proj-a'], unit=None))))
                loose_end = command('alice', 'decline', 'S-n3', request_version=1)
                n3 = I.assignment_id(REPO, 'S-n3')

                parts = []
                for case in CASES:
                    q = (case['questions'] or [None])[0]
                    data, receipt = (q or {}).get('data') or {}, case['ended'].get('receipt') or {}
                    of = data.get('disposition_of') or {}
                    n = case['name']
                    parts += [
                        (n + ': the worker parked the unit and exited', case['exit'] == 0 and len(case['parked']) == 2
                         and case['parked'][1].get('released_claim') == case['cid']),
                        (n + ': before the question the unit read awaiting_answer, or its reason when ask opens it',
                         case['reason_before'] == (case['key'][0] if case['end'][1] == 'ask' else 'awaiting_answer')),
                        (n + ': the end was accepted', case['ended'].get('ok') is True),
                        (n + ': exactly one question is open', len(case['questions']) == 1),
                        (n + ': it offers close, backlog and other', data.get('choices') == ['close', 'backlog', 'other']),
                        (n + ': it names the source assignment and request version',
                         of.get('assignment_id') == case['source'] and of.get('request_version') == case['request_version']
                         and case['request_version'] == (2 if case.get('revise') else 1)),
                        (n + ': it names the blocked unit', of.get('unit_id') == case['unit'] and data.get('unit_id') == case['unit']),
                        (n + ': it is pending in the inbox', q is not None and {e['id']: e for e in inbox.index()['entries']}
                         .get(q['id'], {}).get('category') == 'pending'),
                        (n + ': it names how the work ended', of.get('ended_as') == case['key'][0])]
                    if case['end'][1] != 'ask':
                        parts.append((n + ': the question committed in the decline or cancel\'s own transaction',
                                      q is not None and {q['id'], case['source']} <= set(receipt.get('after_versions') or {})))
                    else:
                        parts.append((n + ': ask opened it and left the source as it was',
                                      (entity(case['source']) or {}).get('data', {}).get('state') in ('EXPIRED', 'SUBMITTED')))
                parts += [('a decline of work that blocks no unit is accepted', loose.get('ok') is True and loose_end.get('ok') is True),
                          ('and opens no question', questions(n3) == [])]
                check('disposition/question-opened', parts)

                parts = []
                for case in CASES + [EXTRA[2]]:
                    q = (case['questions'] or [None])[0]
                    data = (q or {}).get('data') or {}
                    parts.append((case['name'] + ': asked ' + case['expect'], data.get('owner') == case['expect']))
                    if 'why' in case:
                        parts.append((case['name'] + ': why ' + case['why'],
                                      (data.get('disposition_of') or {}).get('addressed_as') == case['why']))
                check('disposition/addressee', parts)

                n1, n2 = EXTRA[0], EXTRA[1]
                check('disposition/no-project-owner', [
                    ('a cancel whose unit has no ownership chain is accepted', n1['ended'].get('ok') is True),
                    ('it names no_project_owner and opens no question',
                     n1['ended'].get('question_refusal') == 'no_project_owner' and n1['questions'] == []),
                    ('the unit stays visible under its original reason', (parked_by_unit().get(n1['unit']) or {}).get('reason') == 'canceled'),
                    ('ask for expired work in a project with two owners is refused no_project_owner',
                     n2['ended'] == {'ok': False, 'reason': 'no_project_owner'} and n2['questions'] == []),
                    ('neither owner is guessed', not any(((q.get('data') or {}).get('owner') in ('zed1', 'zed2'))
                                                         for q in questions(n2['source']))),
                    ('the expired unit stays visible as expired', (parked_by_unit().get(n2['unit']) or {}).get('reason') == 'expired'),
                    ('ask on the canceled unit is refused, not guessed',
                     command('pm', 'ask', n1['alias'], request_version=1).get('ok') is False and questions(n1['source']) == [])])

            # --- AC1: the ordinary projection sends each question to its addressee's own chat ------------------
            with region('disposition/projected-to-own-chat'):
                asked = len(api['requests'])
                results = {r['assignment_id']: r for r in projection.project()}
                new = api['requests'][asked:]
                parts = []
                for case in CASES:
                    q = (case['questions'] or [None])[0]
                    qid = (q or {}).get('id')
                    record = projection.record(P.projection_id(qid, 1)) if qid else None
                    text = api['messages'].get(((record or {}).get('chat_id'), (record or {}).get('message_id'))) or ''
                    lines = text.split('\n')
                    parts += [(case['name'] + ': sent', (results.get(qid) or {}).get('outcome') == 'sent'),
                              (case['name'] + ': in the chat enrolled for ' + case['expect'],
                               record is not None and record.get('chat_id') == chats[case['expect']]
                               and record.get('enrolled_chat') == chats[case['expect']]),
                              (case['name'] + ': the platform holds it there naming the addressee, choices and source',
                               'Owner: %s' % case['expect'] in lines and 'Choices: close | backlog | other' in lines
                               and any(case['source'] in line for line in lines))]
                n4 = EXTRA[2]
                n4q = ((n4['questions'] or [None])[0] or {}).get('id')
                parts += [('an addressee with no enrolled chat is refused no_enrolled_chat',
                           n4q is not None and (results.get(n4q) or {}).get('reason') == 'no_enrolled_chat'),
                          ('and nothing about it is sent to any chat', n4q is not None and not any(n4q in (t or '') for _, t in new)),
                          ('every message went to the chat of the owner it names',
                           bool(new) and all('Owner: %s' % {v: k for k, v in chats.items()}.get(chat) in (t or '').split('\n')
                                             for chat, t in new))]
                check('disposition/projected-to-own-chat', parts)

            # --- AC4 opened; AC3 dispose before the answer ------------------------------------------------------
            with region('disposition/dispose-once'):
                walk('opened', CASES)
                early = {}
                for case in CASES:
                    q = question(case)
                    before = snapshot(case)
                    early[case['name']] = (command('pm', 'dispose', q['data']['alias'], request_version=1) if q else {},
                                           before == snapshot(case))

            # --- AC2: only the addressee's own signed answer, with what its ruling needs, is taken ---------------
            with region('disposition/answer-refusals', 'disposition/unsigned-instruction', 'disposition/question-only-answered',
                        'disposition/valid-answers-admitted'):
                refusals, beside, only, valid = [], [], [], []
                for case in CASES:
                    q = question(case)
                    if q is None:
                        for rows in (refusals, beside, only, valid):
                            rows.append((case['name'] + ': a question to answer', False))
                        continue
                    alias, who, n = q['data']['alias'], case['expect'], case['name']
                    ruling = case['ruling']
                    body = {'instruction': instruction(case), 'arrived_on': arrival(case)} if ruling == 'other' else {}
                    before = snapshot(case)
                    forms = {
                        'a signature that does not verify': (command(who, 'answer', alias, key='mallory', request_version=1,
                                                                     ruling=ruling, **body), 'not_authorized'),
                        'an answer signed by another active member': (command('mallory', 'answer', alias, request_version=1,
                                                                             ruling=ruling, **body), 'not_authorized'),
                        'a stale request version': (command(who, 'answer', alias, request_version=2, ruling=ruling, **body),
                                                    'stale_subject'),
                        'a ruling not offered': (command(who, 'answer', alias, request_version=1, ruling='accept'), 'not_authorized'),
                        'other with empty text': (command(who, 'answer', alias, request_version=1, ruling='other', instruction='',
                                                          arrived_on=arrival(case)), 'invalid_input'),
                        'other with blank text': (command(who, 'answer', alias, request_version=1, ruling='other',
                                                          instruction=' \n\t', arrived_on=arrival(case)), 'invalid_input'),
                        'a key revoked before the answer': (command(who, 'answer', alias, key='old-' + who if 'old-' + who in public
                                                                    else 'mallory', request_version=1, ruling=ruling, **body),
                                                            'not_authorized'),
                    }
                    for label, (result, reason) in forms.items():
                        refusals.append((n + ': ' + label + ' refused ' + reason, result == {'ok': False, 'reason': reason}))
                    refusals.append((n + ': the refused forms change no unit, backlog item, claim or intake', snapshot(case) == before))
                    unsigned = command(who, 'answer', alias, request_version=1, ruling='other', arrived_on=arrival(case),
                                       beside={'instruction': instruction(case)})
                    beside += [(n + ': other whose text is beside the signed command is refused invalid_input',
                                unsigned == {'ok': False, 'reason': 'invalid_input'}),
                               (n + ': and nothing changed', snapshot(case) == before
                                and (entity(q['id']) or {}).get('version') == q['version'])]
                    declined = command(who, 'decline', alias, request_version=1)
                    canceled = command(q['data'].get('requested_by') or 'pm', 'cancel', alias, request_version=1)
                    revised = command('pm', 'revise', alias, request_version=1, changes={'brief': 'Something else.'})
                    only += [(n + ': a decline of the question is refused', declined == {'ok': False, 'reason': 'invalid_input'}),
                             (n + ': a cancel of the question is refused', canceled == {'ok': False, 'reason': 'invalid_input'}),
                             (n + ': a revision of the question is refused', revised.get('ok') is False),
                             (n + ': the question is still pending, unchanged', (entity(q['id']) or {}).get('version') == q['version']
                              and (entity(q['id']) or {}).get('data', {}).get('state') == 'OFFERED'),
                             (n + ': and the unit, backlog item, claim and intake too', snapshot(case) == before)]
                    case['answer_body'] = body
                    case['answered'] = command(who, 'answer', alias, request_version=1, ruling=ruling, **body)
                    stored = ((entity(q['id']) or {}).get('data') or {}).get('answer') or {}
                    valid += [(n + ': the addressee\'s ' + ruling + ' is accepted', case['answered'].get('ok') is True),
                              (n + ': it is admitted by the inbox admission check', inbox.admit(q['id']).get('admitted') is True),
                              (n + ': the signed command keeps the instruction as written',
                               ruling != 'other' or (stored.get('command') or {}).get('instruction') == instruction(case))]
                opened = command('pm', 'open', 'S-forged', assignment=dict(
                    content(dict(owner='alice', scope=['proj-a'], unit=None)), kind='disposition', choices=['close', 'backlog', 'other']))
                only.append(('a disposition question cannot be opened by open', opened == {'ok': False, 'reason': 'invalid_input'}))
                check('disposition/answer-refusals', refusals)
                check('disposition/unsigned-instruction', beside)
                check('disposition/question-only-answered', only)
                check('disposition/valid-answers-admitted', valid)

            # --- the answer whose key is revoked from before its acceptance disposes nothing ---------------------
            with region('disposition/revoked-answer-not-disposed'):
                n4 = EXTRA[2]
                q = question(n4)
                parts = [('the question to the unenrolled addressee exists', q is not None)]
                if q is not None:
                    before_answer = time.time()
                    answered = command('dora', 'answer', q['data']['alias'], request_version=1, ruling='backlog')
                    admitted = inbox.admit(q['id']).get('admitted')
                    fixture('key-dora', 'verification_key', dict(principal='dora', public_key=public['dora'], effective_at=0,
                                                                 revoked_at=before_answer))
                    before = snapshot(n4)
                    disposed = command('pm', 'dispose', q['data']['alias'], request_version=1)
                    parts += [('control: the answer was accepted and admitted before the revocation',
                               answered.get('ok') is True and admitted is True),
                              ('the revocation reaches back: admission refuses it', inbox.admit(q['id']).get('reason') == 'missing_authority'),
                              ('dispose is refused missing_authority', disposed == {'ok': False, 'reason': 'missing_authority'}),
                              ('nothing changed', snapshot(n4) == before and not held(n4)),
                              ('the unit still waits for its disposition',
                               (parked_by_unit().get(n4['unit']) or {}).get('reason') == 'awaiting_disposition')]
                check('disposition/revoked-answer-not-disposed', parts)

            # --- AC3: dispose applies exactly the admitted answer, once ------------------------------------------
            with region('disposition/dispose-close', 'disposition/close-spares-siblings', 'disposition/dispose-backlog',
                        'disposition/dispose-other', 'disposition/dispose-once'):
                walk('answered', CASES)
                for case in CASES:
                    q = question(case)
                    case['claim_before'] = claim('worker', case['unit'])
                    case['before'] = snapshot(case)
                    case['intake_before'] = intake_rows()
                    case['disposed'] = command('pm', 'dispose', q['data']['alias'], request_version=1) if q else {}
                    case['after'] = {k: entity(case[k]) for k in ('unit', 'backlog', 'cid')}
                    case['intake_after'] = intake_rows()
                    case['record'] = entity('assignment-disposition:' + q['id']) if q else None
                walk('disposed', CASES)
                for case in CASES:
                    q = question(case)
                    case['intake_pre_again'] = intake_rows()
                    case['again'] = command('pm', 'dispose', q['data']['alias'], request_version=1) if q else {}
                    case['intake_again'] = intake_rows()
                    case['claim_after'] = steps[case['name']]['disposed']['claim']

                def mark_ok(case, data):
                    mark = (data or {}).get('disposition') or {}
                    q = question(case) or {}
                    return (mark.get('question') == q.get('id') and mark.get('ruling') == 'close'
                            and mark.get('principal') == case['expect']
                            and mark.get('answer_command_id') == (((q.get('data') or {}).get('answer')) or {}).get('command_id'))

                parts = []
                for case in (c for c in CASES if c['ruling'] == 'close'):
                    n, unit = case['name'], (case['after']['unit'] or {}).get('data') or {}
                    parts += [(n + ': dispose is accepted', case['disposed'].get('ok') is True and case['disposed'].get('ruling') == 'close'),
                              (n + ': the unit is CANCELED carrying the disposition', unit.get('state') == 'CANCELED' and mark_ok(case, unit)),
                              (n + ': a claim before it was refused as parked', case['claim_before'] == {'ok': False, 'reason': 'parked'}),
                              (n + ': a claim after it is refused', case['claim_after'].get('ok') is False),
                              (n + ': the intake is unchanged', case['intake_after'] == case['intake_before'])]
                c6 = next(c for c in CASES if c['name'] == 'c6')
                backlog6 = (c6['after']['backlog'] or {}).get('data') or {}
                parts.append(('c6: its backlog item, with no other open unit, is CANCELED carrying the disposition',
                              backlog6.get('state') == 'CANCELED' and mark_ok(c6, backlog6)))
                check('disposition/dispose-close', parts)

                c2 = next(c for c in CASES if c['name'] == 'c2')
                backlog2 = c2['after']['backlog'] or {}
                record2 = (c2['record'] or {}).get('data') or {}
                check('disposition/close-spares-siblings', [
                    ('the closed unit is CANCELED', ((c2['after']['unit'] or {}).get('data') or {}).get('state') == 'CANCELED'),
                    ('the backlog item that owns an open sibling is left as it was',
                     backlog2.get('version') == (c2['before'][1] or (None,))[0]
                     and (backlog2.get('data') or {}).get('state') == 'ACTIVE'),
                    ('the sibling unit is untouched', ((entity('unit-c2-sibling') or {}).get('data') or {}).get('state') == 'READY'),
                    ('the recorded disposition says so', record2.get('backlog_item_left') is True
                     and record2.get('open_siblings') == ['unit-c2-sibling'])])

                parts = []
                for case in (c for c in CASES if c['ruling'] == 'backlog'):
                    n = case['name']
                    now_claim = (case['after']['cid'] or {}).get('data') or {}
                    unit, backlog = case['after']['unit'] or {}, case['after']['backlog'] or {}
                    parts += [(n + ': dispose is accepted', case['disposed'].get('ok') is True),
                              (n + ': a claim before it was refused as parked', case['claim_before'] == {'ok': False, 'reason': 'parked'}),
                              (n + ': the park is cleared: released, no holder, no parked_on',
                               now_claim.get('state') == 'released' and now_claim.get('holder') is None and 'parked_on' not in now_claim),
                              (n + ': the unit and its backlog item are unchanged',
                               (unit.get('version'), backlog.get('version')) == (case['before'][0][0], case['before'][1][0])
                               and (backlog.get('data') or {}).get('state') in ('PRIORITIZED', 'ACTIVE')),
                              (n + ': an ordinary claim by an eligible holder then succeeds',
                               case['claim_after'].get('ok') is True and (case['claim_after'].get('claim') or {}).get('holder') == 'worker'),
                              (n + ': the intake is unchanged', case['intake_after'] == case['intake_before'])]
                check('disposition/dispose-backlog', parts)

                parts = []
                for case in (c for c in CASES if c['ruling'] == 'other'):
                    n = case['name']
                    pid = case['disposed'].get('proposal_id')
                    proposal = intake.proposal(pid) if pid else None
                    arrived = case.get('answer_body', {}).get('arrived_on') or {}
                    source = intake.source(*arrival_source(arrived)) if arrived else None
                    trace = (source or {}).get('command', {}).get('provenance') or {}
                    entry = steps[n]['disposed'].get('entry') or {}
                    parts += [(n + ': dispose is accepted and names a proposal', case['disposed'].get('ok') is True and bool(pid)),
                              (n + ': the intake\'s own reader holds the instruction exactly as signed',
                               proposal is not None and proposal.get('text') == instruction(case)),
                              (n + ': attributed to the answering person, in the unit\'s project',
                               proposal is not None and proposal.get('principal') == case['expect'] and proposal.get('project') == 'proj-a'
                               and proposal.get('state') == 'PROPOSED' and proposal.get('proposal') == 'objective'),
                              (n + ': under the source it arrived on', source is not None and source.get('source_kind') == arrived.get('source_kind')
                               and source.get('proposal_id') == pid),
                              (n + ': with the signed answer\'s command identity beside it',
                               source is not None and (trace.get('attested') or {}).get('disposition', {})
                               .get('answer_command_id') == ((question(case) or {}).get('data', {}).get('answer') or {}).get('command_id')),
                              (n + ': authenticated by the intake itself: the addressee\'s own chat, or the API edge',
                               trace.get('chat_id') == chats[case['expect']] if arrived.get('source_kind') == 'telegram_message'
                               else trace.get('edge') == 'api-edge' and trace.get('request_digest') == IN.digest(arrived.get('request'))),
                              (n + ': no unit, backlog item or claim changed', [e and e.get('version') for e in case['after'].values()]
                               == [x and x[0] for x in case['before'][:3]]),
                              (n + ': a claim before and after is refused as parked',
                               case['claim_before'] == {'ok': False, 'reason': 'parked'}
                               and case['claim_after'] == {'ok': False, 'reason': 'parked'}),
                              (n + ': the unit stays parked as routed_to_intake naming the proposal',
                               entry.get('reason') == 'routed_to_intake' and entry.get('proposal_id') == pid),
                              (n + ': the recorded disposition keeps the instruction verbatim',
                               ((case['record'] or {}).get('data') or {}).get('instruction') == instruction(case))]
                check('disposition/dispose-other', parts)

                parts = []
                for case in CASES:
                    n = case['name']
                    first, unchanged = early.get(n, ({}, False))
                    parts.append((n + ': dispose before the answer is refused not_answered and changes nothing',
                                  first == {'ok': False, 'reason': 'not_answered'} and unchanged))
                    if case['ruling'] == 'other':
                        parts.append((n + ': a second dispose returns the same proposal and writes nothing',
                                      case['again'].get('ok') is True and case['again'].get('proposal_id') == case['disposed'].get('proposal_id')
                                      and case['intake_again'] == case['intake_pre_again']))
                    else:
                        parts.append((n + ': a second dispose is refused stale_subject', case['again'] == {'ok': False, 'reason': 'stale_subject'}))
                check('disposition/dispose-once', parts)

            # --- AC4: other is asked again; the walk reads every step ----------------------------------------
            with region('disposition/ask-again', 'disposition/awaiting-disposition', 'disposition/walk-holds-nothing'):
                others = [c for c in CASES if c['ruling'] == 'other']
                parts = []
                for case in others:
                    case['asked_again'] = command('pm', 'ask', case['alias'], request_version=case['request_version'])
                    case['asked_twice'] = command('pm', 'ask', case['alias'], request_version=case['request_version'])
                    q2 = question(case, 2)
                    parts += [(case['name'] + ': asked again after other', case['asked_again'].get('ok') is True and q2 is not None),
                              (case['name'] + ': of ' + case['expect'] + ' again',
                               ((q2 or {}).get('data') or {}).get('owner') == case['expect']),
                              (case['name'] + ': a second ask while it is open is refused stale_subject',
                               case['asked_twice'] == {'ok': False, 'reason': 'stale_subject'} and len(questions(case['source'])) == 2)]
                c6 = next(c for c in CASES if c['name'] == 'c6')
                parts.append(('ask for closed work is refused', command('pm', 'ask', c6['alias'], request_version=1).get('ok') is False
                              and len(questions(c6['source'])) == 1))
                walk('asked_again', others)
                check('disposition/ask-again', parts)

                expected = {'opened': 'awaiting_disposition', 'answered': 'ready_to_dispose', 'asked_again': 'awaiting_disposition'}
                parts = []
                for case in CASES:
                    for step, seen in sorted(steps[case['name']].items()):
                        want = expected.get(step) or ('routed_to_intake' if case['ruling'] == 'other' else None)
                        parts.append(('%s %s: reads %s' % (case['name'], step, want),
                                      seen['reason'] == want and seen['listed'] is (want is not None)))
                        parts.append(('%s %s: parked_by_reason counts each' % (case['name'], step),
                                      seen['by_reason'] == dict(seen['counted'])))
                check('disposition/awaiting-disposition', parts)

                parts = []
                for case in CASES:
                    for step, seen in sorted(steps[case['name']].items()):
                        free = step == 'disposed' and case['ruling'] in ('close', 'backlog')
                        parts += [('%s %s: the step was reached' % (case['name'], step), seen['reached'] is True),
                                  ('%s %s: no claim held' % (case['name'], step), seen['held_before'] is False),
                                  ('%s %s: no worker process alive' % (case['name'], step), seen['alive'] == []),
                                  ('%s %s: nothing waits holding a claim' % (case['name'], step), seen['waiting'] == []),
                                  ('%s %s: a claim is refused as parked until close or backlog' % (case['name'], step),
                                   free or seen['claim'] == {'ok': False, 'reason': 'parked'})]
                check('disposition/walk-holds-nothing', parts)

            with region('disposition/observability'):
                obs = inbox.observations
                text = json.dumps(obs, sort_keys=True, default=str)
                ended = [o for o in obs if o.get('operation') in ('decline', 'cancel', 'ask') and (o.get('disposition') or {}).get('question_id')]
                disposes = [o for o in obs if o.get('operation') == 'dispose']
                counted = inbox.metrics().get('dispositions') or {}
                check('disposition/observability', [
                    ('each opened question is observed with its source, unit, addressee and why',
                     len(ended) >= len(CASES) and all({'source_assignment', 'unit_id', 'addressee', 'addressed_as', 'question_id'}
                                                      <= set(o['disposition']) for o in ended)),
                    ('each dispose is observed with its question and ruling', disposes and all(
                        (o.get('disposition') or {}).get('question_id') for o in disposes)),
                    ('accepted dispositions are counted by outcome',
                     counted.get('accepted') == {'close': 2, 'backlog': 2, 'other': 6}),
                    ('refused dispositions are counted by outcome', (counted.get('refused') or {}).get('close') == 2
                     and (counted.get('refused') or {}).get('backlog', 0) >= 3),
                    ('no instruction text, brief or signature is logged',
                     not any(instruction(c) in text or json.dumps(instruction(c))[1:-1] in text for c in CASES)
                     and 'What becomes of unit' not in text and 'SSH SIGNATURE' not in text)])
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait()
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])
    observed['raised'] = raised
    globals()['_V133_OBSERVED'] = observed


_v133_started = __import__('time').monotonic()
_v133_suite()
print('VELDO-0133 suite seconds: %.3f' % (__import__('time').monotonic() - _v133_started))
