"""VELDO-0178: the authenticated API serves the owner's conversations and their turns, and every turn's execution
record is kept and served live only to the conversation's owner.

Run: python3 scripts/selftest.py --suite 133_veldo_0178_conversation_api

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support) with the owner
(scope: one project) and a colleague, a current person member of the same domain holding project_owner over the
universal scope; the production API (control_api.ControlApi) over the production judge (control_api_authority.
ApiAuthority) holding the authority's lock, its every write an assertion the API edge's real key signs for the
session's member and the judge verifies (the api channel edge enrolled by the steward's signed command), its event
feed VELDO-0051's publication of this store, its sessions created in the API's own session table for credentials
the store holds (the passkey ceremonies are suite 71's); the production VELDO-0126 intake and VELDO-0174
conversation authority; VELDO-0174's conversation Line with a real receiver subprocess over a fake pinned Claude Code
(support/v174_journey.py, the fake's output from this suite), whose account has a fixture subscription token, the
resolved credential value the fake prints in a command's output; the receiver's record hints on a socket of this
suite, handed to the API as its hint socket hands them. No real engine, login, Telegram, user unit or network.
Writes only temporary fixtures.
"""


def _v178_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import queue
    import shutil
    import socket
    import tempfile
    import threading
    import time
    from types import SimpleNamespace

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which the API, the judge, the conversations and the receiver run) takes each of them.
    PRODUCTION = {
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api_models_scope.py': ROOT / ".veldo" / "control_api_models_scope.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_execution_record.py': ROOT / ".veldo" / "control_execution_record.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
    }
    ROWS = ('AC1/routes', 'AC1/list', 'AC1/serve', 'AC1/other-member', 'AC1/commands', 'AC1/stale-and-unknown',
            'AC1/message-field', 'AC1/events', 'AC1/observability',
            'AC2/record-kept', 'AC2/header', 'AC2/owner-live', 'AC2/after-end', 'AC2/other-member', 'AC2/neither',
            'AC2/observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    if not all(Path(p).is_file() for p in PRODUCTION.values()):
        for row in ROWS:
            expect('VELDO-0178 ' + row, False)
        return
    H = load('v178_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v178_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v178_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    base = Path(tempfile.mkdtemp(prefix='v178-', dir=fast_temp()))
    stops, factories = [], []

    # THE FAKE ENGINE: VELDO-0174's handshake and init, then for a conversation's turn: a tool call (a Bash command),
    # the command's output carrying the resolved subscription token, an error line on its error stream, a marker,
    # a hold while `hold-<conversation>` exists, then its reply. It keeps its own copy of its error stream.
    OWN = "own = {'engine':ENGINE,'tools':tools,"
    BODY = r'''own = {'engine':ENGINE,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),'argv':args,'packet':packet}
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
given = packet.get('payload') or {}
conversation, turn = str(given.get('conversation')), given.get('turn')
value = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')
uid = 'toolu_v178_%d' % os.getpid()
emit({'type':'assistant','message':{'id':'use-' + uid,'type':'message','role':'assistant',
      'content':[{'type':'tool_use','id':uid,'name':'Bash','input':{'command':'cat deploy.env'}}],
      'usage':{'input_tokens':1,'output_tokens':1}}})
emit({'type':'user','message':{'role':'user','content':[{'type':'tool_result','tool_use_id':uid,
      'content':'DEPLOY_TOKEN=' + value}]}})
error = 'v178 fixture error: the deploy step of turn %s failed' % turn
with (MARKERS / ('stderr-%s-%s.txt' % (conversation, turn))).open('a') as kept: kept.write(error + '\n')
sys.stderr.write(error + '\n'); sys.stderr.flush()
(MARKERS / ('midway-%s-%s' % (conversation, turn))).write_text('1')
while (MARKERS / ('hold-' + conversation)).exists(): time.sleep(.02)
reply = 'Turn %s of %s: the deploy step failed; here is why.' % (turn, conversation)
emit({'type':'rate_limit_event','rate_limit_info':{'status':'allowed','rateLimitType':'five_hour',
      'utilization':.25,'resetsAt':int(time.time())+3600}})
emit({'type':'assistant','message':{'id':'message-one','type':'message','role':'assistant',
      'content':[{'type':'text','text':reply}],'usage':{'input_tokens':12,'output_tokens':3}}})
emit({'type':'result','subtype':'success','is_error':False,'num_turns':1,'result':reply,
      'usage':{'input_tokens':12,'output_tokens':3}})
'''

    def fake_source():
        source = J.FAKE
        if source.count(OWN) != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        return source[:source.index(OWN)] + BODY

    hints = queue.Queue()

    def hint_socket(path):
        """The receiver's record hint socket: each hint received, queued for this thread to hand to the API."""
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(16)
        server.settimeout(.2)
        running = [True]

        def serve():
            while running[0]:
                try:
                    peer, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return
                with peer:
                    data = b''
                    peer.settimeout(2)
                    try:
                        while True:
                            chunk = peer.recv(65536)
                            if not chunk:
                                break
                            data += chunk
                    except OSError:
                        pass
                try:
                    hints.put(json.loads(data.decode()))
                except ValueError:
                    pass
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

        def stop():
            running[0] = False
            server.close()
            thread.join(2)
        return stop

    try:
        f = F.fixture(ROOT, base, H, load, 'api178', 78, PRODUCTION, providers=('claude_code',))
        mods, authority = f['root'] / 'modules', f['authority']
        S, CM, AC, ids = authority.S, authority.CM, authority.AC, authority.ids
        domain = ids['domain_uuid']
        CV = load('v178_conversation', mods / 'control_conversation.py')
        CS = load('v178_service', mods / 'control_service.py')
        CS.CV = CV
        IN = load('v178_intake', mods / 'control_intake.py')
        API = load('v178_api', mods / 'control_api.py')
        AUTH = load('v178_judge', mods / 'control_api_authority.py')
        ER = load('v178_record', mods / 'control_execution_record.py')
        EVP = load('v178_publication', mods / 'control_event_projection.py')
        CR, AS = AUTH.CR, AUTH.AS
        observations = []
        conversations = CV.Conversations(S, authority.conn, domain=domain, principal='authority', signer='authority',
                                         sign=authority.journal_sign, state_root=f['root'] / 'state',
                                         observe=observations.append)
        f['conversations'] = conversations
        saved, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved
        # The account and its subscription token, a resolved credential value of every run on it (VELDO-0141).
        accounts = load('v178_accounts', mods / 'control_accounts.py').Accounts(
            S, authority.conn, principal='owner', signer='authority', sign=authority.journal_sign)
        account = 'account-claude_code-1'
        profile = f['root'] / ('profile-' + account)
        profile.mkdir(parents=True)
        accounts.register('account-register-' + account, account, 'claude_code', account, {f['host']: str(profile)},
                          concurrency=1, now=time.time())
        token = 'v178-token-' + os.urandom(8).hex()
        token_path = f['root'] / ('token-' + account)
        token_path.write_text(token)
        token_path.chmod(0o600)
        hint_dir = base / 'hints'
        hint_dir.mkdir(mode=0o700)
        stops.append(hint_socket(hint_dir / 'record.sock'))
        config = json.loads(receiver.read_text())
        config['subscription_tokens'] = {account: str(token_path)}
        config['record_hints'] = [str(hint_dir / 'record.sock')]
        receiver.write_text(json.dumps(config))
        records = ER.directory(config)

        # The members: the owner (one project) and a colleague of the same domain over the universal scope.
        authority.fixture('colleague', 'membership', {'principal_type': 'person', 'roles': ['project_owner'],
                                                      'scope': '*', 'revoked_at': None, 'expires_at': None})
        project = 'activation-repository'
        authority.fixture('project:' + project, 'project', {'name': project, 'owner': 'owner', 'state': 'ACTIVE',
                                                            'ticket_key_prefixes': []})
        for who in ('owner', 'colleague'):
            cid = 'v178-passkey-' + who
            authority.fixture(CR.entity_id(cid), CR.KIND, {'credential_id': cid, 'principal': who, 'effective_at': 0,
                                                           'revoked_at': None, 'label': who})
        # The API's own edge (VELDO-0067, channel "api"), its own principal and key, enrolled by the steward's
        # signed command.
        import subprocess
        edge_key = base / 'edge-api-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v178-api-edge', '-f', str(edge_key)],
                       check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        edge_public = ' '.join(edge_key.with_name(edge_key.name + '.pub').read_text().split()[:2])

        def edge_sign(message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(edge_key), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=10).stdout.decode()
        EDGE = 'api-edge-178'
        edge = {'channel': 'api', 'edge_principal': EDGE, 'edge_key_id': 'edge-api', 'public_key': edge_public,
                'connection_public_key': authority.public['settler'], 'scope': [project]}
        command = {'command_id': authority.next_id('edge'), 'operation': 'enroll_channel_edge',
                   'target': 'channel:api', 'parameters': edge, 'artifact_digests': [], 'expected_versions': {}}
        envelope = authority.envelope(command, 'steward')
        enrolled = authority.E.Enrollment(S, authority.conn, ids, 'authority', authority.journal_sign,
                                          projection=authority.projection).admit(
            envelope, command, authority.sign_as('steward', AC.canonical_envelope_bytes(envelope)),
            edge_sign(AC.canonical_envelope_bytes(envelope), 'veldo-edge-possession'))
        print('  VELDO-0178 api edge:', {k: v for k, v in (enrolled or {}).items() if k in ('outcome', 'reason', 'refusal',
                                                                                         'detail')})

        # The service loop's stand-in (as suite 131): the production FactoryLoop over the conversation receiver.
        service = SimpleNamespace(
            config={'receiver': {'conversations': str(receiver)}, 'journal_key': str(authority.keyfile['authority'])},
            conn=authority.conn, domain=domain, principal='authority', generation=1, sign=authority.journal_sign,
            conversations=lambda: conversations, _log=lambda event: None, repositories={}, store=ids['store_uuid'],
            watermark=lambda: authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0])
        wrapper = f['root'] / 'receiver-driver.py'
        wrapper.write_text('import runpy,sys\nsys.stderr=open(' + repr(str(f['root'] / 'receiver-errors.log'))
                           + ", 'a')\nrunpy.run_path(" + repr(str(mods / 'control_launch.py')) + ",run_name='__main__')\n")
        CS.L.RECEIVER = str(wrapper)
        factory = CS.FactoryLoop(service, None)
        lock = CS.acquire(str(authority.db.parent / 'authority.lock'), {'principal': 'authority'})
        factory.lock = lock
        factories.append((factory, lock))
        factory.start()

        # THE API: the production judge on the authority's connection, holding its lock, and the production API.
        # The production VELDO-0066 Acquirer over a loopback Bot API stand-in (nothing is sent on it): intake's
        # judge of a current person.
        P = load('v178_projection', mods / 'control_channel_projection.py')
        V = load('v178_presentation', mods / 'control_channel_presentation.py')
        EV = load('v178_attribution', mods / 'control_channel_attribution.py')
        I = load('v178_inbox', mods / 'control_assignment.py')
        contract = load('v178_contract', mods / 'entity_contract.py')
        bot = {'id': 8000000178, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_v178_bot'}
        url, _bot_api, stop_bot = H.stand_in({'bot178': bot})
        stops.append(stop_bot)
        inbox = I.Inbox(S, CM, authority.claims, contract, authority.conn, ids, 'authority', authority.journal_sign)
        presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot178'), authority.conn,
                                'authority', authority.journal_sign, assignment=I)
        acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot178'), authority.conn,
                               'authority', authority.journal_sign, EDGE, lambda b: edge_sign(b))
        intake = IN.Intake(S, CM, AC, acquirer, authority.conn, domain=domain, projects=[project], api_edge=EDGE,
                           journal_signer='authority', sign=authority.journal_sign, conversations=conversations)
        (base / 'publication').mkdir()
        publication = EVP.Projection(S, str(authority.db), domain=ids['domain_uuid'],
                                     repository=ids['repository_uuid'], root=str(base / 'publication'))
        api = []
        judged = []
        # The pre-change judge takes no conversations: then each row fails by its own assertions (the red record).
        import inspect
        held = {'conversations': conversations} if 'conversations' in inspect.signature(
            AUTH.ApiAuthority).parameters else {}
        judge = AUTH.ApiAuthority(S, CM, authority.conn, ids=ids, domain=domain, edge=EDGE, intake=intake,
                                  settlement=None, credentials=None, publication=publication, authority_lock=lock,
                                  records=records, observe=judged.append, **held,
                                  notify=lambda hint: api[0].deliver(hint) if api else None)

        def signer(assertion):
            derived = AS.domain_request(assertion)
            return (edge_sign(S.canonical_bytes(assertion)),
                    edge_sign(S.canonical_bytes(derived)) if derived is not None else None)

        host = 'veldo.v178.test'
        called = []
        api.append(API.ControlApi({'origin': 'https://' + host, 'rp_id': host, 'host': host, 'domain': domain,
                                   'ids': ids, 'edge': EDGE, 'state_dir': str(base / 'api-state')},
                                  judge, signer, observe=called.append))
        ui = api[0]
        sessions = {who: ui.sessions.create(who, 'v178-passkey-' + who) for who in ('owner', 'colleague')}
        prefix = '/api/v1/domains/%s/' % domain

        def call(method, route, body=None, who='owner', query=None, headers=None):
            cookie, session = sessions[who]
            sent = {'Host': host, 'Cookie': '%s=%s' % (API.COOKIE, cookie)}
            if method == 'POST':
                sent.update({'Origin': 'https://' + host, 'Sec-Fetch-Site': 'same-origin',
                             'Content-Type': 'application/json', API.TOKEN_HEADER: session['token']})
            sent.update(headers or {})
            path = prefix + route
            if query:
                from urllib.parse import urlencode
                path += '?' + urlencode(query)
            status, _headers, value = ui.handle(method, path, sent, json.dumps(body or {}).encode()
                                                if method == 'POST' else b'')
            return status, value

        def refusal(answer):
            return (answer[1] or {}).get('refusal') if isinstance(answer[1], dict) else None

        def journal_count():
            return authority.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def events_of(who, after=0):
            """Every event the feed serves `who` after `after`, page after page to the head."""
            found, seen = [], after
            while True:
                status, page = call('GET', 'events', who=who, query={'after': seen})
                if status != 200:
                    return found, status
                fresh = [e for e in page.get('events') or [] if e['seq'] > seen]
                found += fresh
                head = page.get('cursor', fresh[-1]['seq'] if fresh else seen)
                if head <= seen or head >= page['watermark']['seq']:
                    return found, status
                seen = head

        def kinds_in(events):
            return {e['kind'] for event in events for e in event['entities']}

        def ids_in(events):
            return {e['id'] for event in events for e in event['entities']}

        READS = ('objectives', 'work', 'workers', 'runs', 'decisions', 'proof', 'spend', 'configuration')

        def colleague_leaks(conversation, dispatch, source):
            """Every id the colleague is served, on his whole event feed and on every read model, that carries the
            owner's conversation id or the turn's dispatch id, or is the turn's intake source (review-2026-11-04
            finding 1), with where it was served."""
            marks = [m for m in (conversation, dispatch) if isinstance(m, str) and m]
            def leaked(identity):
                return isinstance(identity, str) and (identity == source or any(m in identity for m in marks))
            found = sorted('events:' + i for i in ids_in(events_of('colleague')[0]) if leaked(i))
            for name in READS:
                status, answer = call('GET', name, who='colleague')
                if status != 200:
                    found.append('%s:status-%s' % (name, status))
                    continue
                found += sorted('%s:%s' % (name, item.get('id')) for items in (answer.get('items') or {}).values()
                                for item in items if leaked(item.get('id')))
            return found

        def drain_hints():
            delivered = []
            while True:
                try:
                    hint = hints.get_nowait()
                except queue.Empty:
                    return delivered
                delivered.append(ui.deliver(hint))

        # AC1/routes: the published table.
        table = {r.name: r for r in API.ROUTES}
        wanted = {'conversations.read': ('GET', (), ('conversation',)),
                  'conversations.open': ('POST', (), ('role',)),
                  'conversations.close': ('POST', ('conversation', 'version'), ()),
                  'conversations.set_role': ('POST', ('conversation', 'version', 'role'), ()),
                  'conversations.attach_project': ('POST', ('conversation', 'version', 'project'), ())}
        check('AC1/routes', 'the published table carries the five conversation routes with their exact fields',
              all(name in table and (table[name].method, table[name].required, table[name].optional) == shape
                  and table[name].session for name, shape in wanted.items()))
        check('AC1/routes', 'every route has its handler [%s]' % ui.route_problems(), ui.route_problems() == [])
        check('AC1/routes', 'messages.send carries the conversation field',
              'conversation' in table['messages.send'].optional)
        check('AC1/routes', 'each command route sends VELDO-0174\'s typed command',
              [getattr(table.get(n), 'operation', None) for n in ('conversations.open', 'conversations.close',
                                                                  'conversations.set_role',
                                                                  'conversations.attach_project')]
              == [CV.OPEN, CV.CLOSE, CV.ROLE, CV.ATTACH]
              and all(judge.commands().get(op) == CV.OPERATION for op in (CV.OPEN, CV.CLOSE, CV.ROLE, CV.ATTACH)))

        # AC1/commands: the owner opens a conversation; the colleague opens one of his own.
        opened = call('POST', 'conversations/open', {})
        talk = (opened[1] or {}).get('conversation')
        theirs_opened = call('POST', 'conversations/open', {'role': 'assistant'}, who='colleague')
        theirs = (theirs_opened[1] or {}).get('conversation')
        print('  VELDO-0178 opened:', opened[0], refusal(opened), talk, theirs_opened[0], theirs)
        if opened[0] != 200:
            # A tree without the route (the red record): the conversation is opened by the conversation authority
            # itself, so the turn still runs and the record rows judge that tree's record scope.
            talk = 'c-v178-direct'
            conversations.open(talk, owner='owner', intake_digest='sha256:v178-direct', command_id='v178-direct')
        open_row = authority.conn.execute('SELECT data FROM entities WHERE id=?', (CV.conversation_id(talk),)).fetchone() \
            if talk else None
        open_record = json.loads(open_row[0]) if open_row else {}
        check('AC1/commands', 'conversations.open sends the open command as the session\'s member [%s %s]'
              % (opened[0], refusal(opened)), opened[0] == 200 and opened[1].get('outcome') == 'opened'
              and opened[1].get('version') == 1 and open_record.get('owner') == 'owner'
              and open_record.get('status') == 'open' and open_record.get('role') == CV.DEFAULT_ROLE)

        # AC1/message-field: his first message names the conversation and is its first turn.
        words = 'why did the deploy step fail this morning?'
        sent = call('POST', 'messages', {'text': words, 'conversation': talk})
        first = (conversations.turns(talk) or [{}])[0] if talk else {}
        check('AC1/message-field', 'messages.send with the conversation field makes his message its next turn [%s %s]'
              % (sent[0], refusal(sent)), sent[0] == 200 and sent[1].get('outcome') == 'turn'
              and first.get('sequence') == 1 and first.get('state') == 'waiting')
        foreign = call('POST', 'messages', {'text': 'let me in', 'conversation': talk}, who='colleague')
        check('AC1/message-field', 'the colleague\'s message naming it is refused by name and makes no turn [%s]'
              % refusal(foreign), foreign[0] == 403 and 'missing_authority:conversation_owner' in str(refusal(foreign))
              and len(conversations.turns(talk)) == 1)

        # The turn runs; it holds after its tool call, its credential output and its error line.
        if talk:
            (markers / ('hold-' + talk)).write_text('1')
        J.pass_(factory)
        midway = F.drive(factory, lambda: talk and (markers / ('midway-%s-1' % talk)).exists()
                         and (conversations.turns(talk) or [{}])[0].get('state') == 'dispatched', 60)
        turn = (conversations.turns(talk) or [{}])[0] if talk else {}
        dispatch_id = turn.get('dispatch_id')
        print('  VELDO-0178 midway:', midway, dispatch_id)
        # Finding 1: while the turn runs, nothing of it is served the colleague on his feed or any read model.
        leaks_running = colleague_leaks(talk, dispatch_id, turn.get('intake_command'))

        def lines_until(who, want, seconds=20):
            """runs.record read by `who` from cursor 0 until `want(answer)` holds or `seconds` pass."""
            end = time.monotonic() + seconds
            while True:
                got = call('GET', 'runs/record', who=who, query={'dispatch': dispatch_id or 'none', 'after': 0})
                if got[0] != 200 or want(got[1]) or time.monotonic() > end:
                    return got
                F.drive(factory, lambda: False, .2)

        def printed(answer, needle):
            return any(needle in line['payload'] for line in (answer or {}).get('lines') or ())

        live = lines_until('owner', lambda a: printed(a, 'v178 fixture error'))
        check('AC2/owner-live', 'the owner reads the running turn\'s record from cursor 0 [%s %s]'
              % (live[0], refusal(live)), live[0] == 200 and live[1].get('ended') is False
              and printed(live[1], '"tool_use"') and printed(live[1], 'v178 fixture error')
              and live[1]['run'].get('state') == 'running')
        check('AC2/owner-live', 'the served run names its conversation and turn',
              live[0] == 200 and live[1]['run'].get('conversation') == talk and live[1]['run'].get('turn') == 1
              and live[1]['run'].get('project') is None)
        stream_status, stream = call('GET', 'runs/record/stream', query={'dispatch': dispatch_id or 'none', 'after': 0})
        first_frame = stream.next(1) if stream_status == 200 else ('none', None)
        cursor = (first_frame[1] or {}).get('cursor') if first_frame[0] == 'frame' else None
        check('AC2/owner-live', 'the owner follows it live on runs.record_stream [%s]' % stream_status,
              stream_status == 200 and first_frame[0] == 'frame' and bool(first_frame[1]['lines'])
              and cursor == live[1].get('total'))
        other_live = call('GET', 'runs/record', who='colleague', query={'dispatch': dispatch_id or 'none', 'after': 0})
        other_stream = call('GET', 'runs/record/stream', who='colleague',
                            query={'dispatch': dispatch_id or 'none', 'after': 0})
        check('AC2/other-member', 'the colleague is refused the running turn\'s record by name [%s %s]'
              % (other_live[0], refusal(other_live)), other_live[0] == 403
              and 'missing_authority:conversation_owner' in str(refusal(other_live)) and 'lines' not in other_live[1])
        check('AC2/other-member', 'and its live stream [%s %s]' % (other_stream[0], refusal(other_stream)),
              other_stream[0] == 403 and 'missing_authority:conversation_owner' in str(refusal(other_stream)))

        # The turn ends; the receiver's hints wake the owner's stream, which closes once every line is out.
        if talk:
            (markers / ('hold-' + talk)).unlink()
        ended = F.drive(factory, lambda: (conversations.turns(talk) or [{}])[0].get('state') == 'ended', 60)
        F.drive(factory, lambda: False, .5)
        delivered = drain_hints()
        frames = [first_frame[1]] if first_frame[0] == 'frame' else []
        closed = None
        while True:
            kind, frame = stream.next(.5) if stream_status == 200 else ('closed', None)
            if kind == 'frame':
                frames.append(frame)
                continue
            closed = frame if kind == 'closed' else None
            break
        turn = (conversations.turns(talk) or [{}])[0] if talk else {}
        print('  VELDO-0178 ended:', ended, turn.get('outcome'), len(delivered), closed)
        after = call('GET', 'runs/record', query={'dispatch': dispatch_id or 'none', 'after': cursor or 0})
        whole = call('GET', 'runs/record', query={'dispatch': dispatch_id or 'none', 'after': 0})
        dispatch = json.loads(authority.conn.execute('SELECT data FROM entities WHERE id=?',
                                                     ('dispatch:' + str(dispatch_id),)).fetchone()[0]) \
            if dispatch_id else {}
        committed = dispatch.get('execution_record') or {}
        check('AC2/after-end', 'after the run the owner reads the rest from his cursor, with its committed count '
              '[%s %s]' % (after[0], refusal(after)), after[0] == 200 and after[1].get('ended') is True
              and after[1].get('total') == committed.get('lines') and bool(after[1]['lines'])
              and after[1]['lines'][0]['seq'] == (cursor or 0) + 1 and printed(after[1], '"result"'))
        streamed = [line for frame in frames for line in frame['lines']]
        check('AC2/owner-live', 'the receiver\'s hints fill the owner\'s stream to the last line, then it closes as '
              'ended [%d frames, %s]' % (len(frames), closed), closed == 'ended' and bool(delivered)
              and [line['seq'] for line in streamed] == list(range(1, (committed.get('lines') or -1) + 1)))
        other_after = call('GET', 'runs/record', who='colleague', query={'dispatch': dispatch_id or 'none', 'after': 0})
        check('AC2/other-member', 'after the run the colleague is still refused by name, with no line [%s %s]'
              % (other_after[0], refusal(other_after)), other_after[0] == 403
              and 'missing_authority:conversation_owner' in str(refusal(other_after)))

        # AC2/record-kept: the record is the run's whole output, redacted the same way, bound to the turn.
        out_lines = []
        for path in markers.glob('*.out'):
            text = path.read_text()
            if dispatch_id and ('toolu_v178_' in text):
                out_lines = [line for line in text.splitlines() if line]
        stdout = [line for line in (whole[1] or {}).get('lines') or () if line['stream'] == 'engine']
        stderr = [line for line in (whole[1] or {}).get('lines') or () if line['stream'] == 'stderr']
        mark = ER.marker('subscription_token')
        credential = [line for line in stdout if 'DEPLOY_TOKEN=' in line['payload']]

        def as_kept(out):
            """A printed line as VELDO-0141 keeps it: the resolved value and the handshake's account email replaced."""
            return out.replace(token, mark).replace('"email": "fixture"', '"email": "%s"' % ER.marker('account:email'))
        check('AC2/record-kept', 'every line the engine printed is kept, in order, nothing dropped [%d of %d]'
              % (len(stdout), len(out_lines)), whole[0] == 200 and len(out_lines) > 3 and len(stdout) == len(out_lines)
              and all(line['payload'] == as_kept(out) for line, out in zip(stdout, out_lines)))
        check('AC2/record-kept', 'the tool call and the error line are kept as printed',
              printed(whole[1], '"tool_use"') and printed(whole[1], 'cat deploy.env')
              and [line['payload'] for line in stderr if 'v178 fixture' in line['payload']]
              == [l for l in (markers / ('stderr-%s-1.txt' % talk)).read_text().splitlines()] if talk else False)
        check('AC2/record-kept', 'the resolved credential value is replaced before the scanner, as a project run\'s is',
              len(credential) == 1 and 'subscription_token' in credential[0]['redacted']
              and ('DEPLOY_TOKEN=' + mark) in credential[0]['payload'] and token not in credential[0]['payload'])
        raw = Path(ER.path(records, dispatch_id)).read_bytes() if dispatch_id else b''
        check('AC2/record-kept', 'the value is nowhere in the kept file, and the file is the committed one',
              bool(raw) and token.encode() not in raw and committed.get('bytes') == len(raw))
        header = json.loads(raw.splitlines()[0]) if raw else {}
        check('AC2/header', 'the record\'s header names the conversation id and the turn sequence [%s]'
              % {k: header.get(k) for k in ('unit', 'station', 'conversation', 'turn')},
              header.get('conversation') == talk and header.get('turn') == 1 and header.get('dispatch_id') == dispatch_id)

        # AC2/neither: a run with neither a project nor a conversation is served to nobody.
        authority.fixture('dispatch:dispatch/v178-orphan/a1', 'dispatch', dict(
            schema='veldo.dispatch/v1', dispatch_id='dispatch/v178-orphan/a1', state='exited',
            contract={'unit': 'v178-orphan', 'station': 'build', 'reservation': {'project': None, 'account': account}}))
        orphan = [call('GET', 'runs/record', who=who, query={'dispatch': 'dispatch/v178-orphan/a1', 'after': 0})
                  for who in ('owner', 'colleague')]
        check('AC2/neither', 'a run with no project and no conversation is refused to every member, universal scope '
              'included [%s]' % [refusal(o) for o in orphan],
              all(o[0] == 403 and refusal(o) == 'unauthorized:out_of_scope' for o in orphan))

        # AC1/list and serve, after the turn.
        listed = call('GET', 'conversations')
        mine = [c for c in (listed[1] or {}).get('conversations') or [] if c.get('id') == talk]
        check('AC1/list', 'the owner lists his conversation with its id, status, role, turn count and last activity '
              '[%s %s]' % (listed[0], refusal(listed)), listed[0] == 200 and len(mine) == 1
              and mine[0]['status'] == 'open' and mine[0]['role'] == CV.DEFAULT_ROLE and mine[0]['turns'] == 1
              and isinstance(mine[0]['last_activity'], float)
              and mine[0]['last_activity'] >= (turn.get('ended_at') or 0))
        check('AC1/list', 'and only his own', [c['id'] for c in listed[1]['conversations']] == [talk]
              if listed[0] == 200 else False)
        served = call('GET', 'conversations', query={'conversation': talk or 'none'})
        turns = (served[1] or {}).get('turns') or []
        check('AC1/serve', 'one conversation is served with every turn\'s sequence, message, reply, outcome, dispatch id '
              'and account [%s %s]' % (served[0], refusal(served)),
              served[0] == 200 and len(turns) == 1 and turns[0]['sequence'] == 1 and turns[0]['message'] == words
              and turns[0]['reply'] == turn.get('reply') and (turns[0]['reply'] or '').startswith('Turn 1 of')
              and turns[0]['outcome'] == 'completed' and turns[0]['dispatch_id'] == dispatch_id
              and turns[0]['account'] == account)
        check('AC1/serve', 'with the conversation\'s id, status, role and version',
              served[0] == 200 and {k: served[1]['conversation'].get(k) for k in ('id', 'status', 'role', 'version')}
              == {'id': talk, 'status': 'open', 'role': CV.DEFAULT_ROLE, 'version': 1})

        # AC1/other-member: the colleague sees no conversation of the owner's anywhere.
        their_list = call('GET', 'conversations', who='colleague')
        their_serve = call('GET', 'conversations', who='colleague', query={'conversation': talk or 'none'})
        check('AC1/other-member', 'the colleague\'s list holds only his own conversation [%s]'
              % [c.get('id') for c in (their_list[1] or {}).get('conversations') or []],
              their_list[0] == 200 and [c['id'] for c in their_list[1]['conversations']] == [theirs])
        check('AC1/other-member', 'the served conversation is refused to him by name, with nothing of it [%s %s]'
              % (their_serve[0], refusal(their_serve)), their_serve[0] == 403
              and 'missing_authority:conversation_owner' in str(refusal(their_serve))
              and words not in json.dumps(their_serve[1]) and 'turns' not in their_serve[1])
        workers_owner = call('GET', 'workers')
        workers_other = call('GET', 'workers', who='colleague')
        def dispatches_of(answer):
            return [d['id'] for d in ((answer[1] or {}).get('items') or {}).get('dispatch') or []]
        check('AC1/other-member', 'the turn\'s dispatch is in the owner\'s workers read and not in his',
              'dispatch:' + str(dispatch_id) in dispatches_of(workers_owner)
              and 'dispatch:' + str(dispatch_id) not in dispatches_of(workers_other)
              and workers_other[0] == 200)

        # AC1/commands: role, attach and close, each on the version he saw.
        role = call('POST', 'conversations/role', {'conversation': talk, 'version': 1, 'role': 'assistant'})
        attach = call('POST', 'conversations/attach', {'conversation': talk, 'version': 2, 'project': project})
        record = conversations.read(talk) or {}
        check('AC1/commands', 'set_role and attach_project send VELDO-0174\'s commands on his versions [%s %s %s %s]'
              % (role[0], refusal(role), attach[0], refusal(attach)),
              role[0] == 200 and role[1].get('outcome') == 'role_changed' and role[1].get('version') == 2
              and attach[0] == 200 and attach[1].get('outcome') == 'attached' and attach[1].get('version') == 3
              and record.get('project') == project and record.get('version') == 3)
        before = journal_count()
        stale = call('POST', 'conversations/close', {'conversation': talk, 'version': 2})
        unknown = call('POST', 'conversations/close', {'conversation': 'c-none-178', 'version': 1})
        theirs_close = call('POST', 'conversations/close', {'conversation': talk, 'version': 3}, who='colleague')
        theirs_role = call('POST', 'conversations/role', {'conversation': talk, 'version': 3, 'role': 'assistant'},
                           who='colleague')
        unknown_read = call('GET', 'conversations', query={'conversation': 'c-none-178'})
        check('AC1/stale-and-unknown', 'a command on a stale version is refused stale_version [%s %s]'
              % (stale[0], refusal(stale)), stale[0] == 409 and refusal(stale) == 'stale_version')
        check('AC1/stale-and-unknown', 'an unknown conversation is refused invalid_input:conversation:unknown '
              '[%s %s %s]' % (unknown[0], refusal(unknown), refusal(unknown_read)),
              unknown[0] == 400 and refusal(unknown) == 'invalid_input:conversation:unknown'
              and unknown_read[0] == 400 and refusal(unknown_read) == 'invalid_input:conversation:unknown')
        check('AC1/other-member', 'his commands on it are refused by name [%s %s]'
              % (refusal(theirs_close), refusal(theirs_role)),
              all(r[0] == 403 and 'missing_authority:conversation_owner' in str(refusal(r))
                  for r in (theirs_close, theirs_role)))
        check('AC1/stale-and-unknown', 'no refused command wrote anything', journal_count() == before
              and (conversations.read(talk) or {}).get('version') == 3)

        # AC1/events: his feed carries every conversation event; the colleague's none of them. A close is seen live.
        mark_seq = authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        owner_stream = call('GET', 'events/stream', query={'after': mark_seq})
        other_stream = call('GET', 'events/stream', who='colleague', query={'after': mark_seq})
        for opened_stream in (owner_stream, other_stream):
            if opened_stream[0] == 200:
                while opened_stream[1].next(.1)[0] == 'frame':
                    pass
        closed_call = call('POST', 'conversations/close', {'conversation': talk, 'version': 3})

        def frames_of(answer):
            got = []
            while answer[0] == 200:
                kind, frame = answer[1].next(.5)
                if kind != 'frame':
                    break
                got += frame.get('events') or []
            return got
        live_owner, live_other = frames_of(owner_stream), frames_of(other_stream)
        check('AC1/commands', 'conversations.close closes it on its version [%s %s]'
              % (closed_call[0], refusal(closed_call)), closed_call[0] == 200
              and closed_call[1].get('outcome') == 'closed' and (conversations.read(talk) or {}).get('status') == 'closed')
        conversation_entity, turn_entity = CV.conversation_id(talk or ''), CV.turn_id(talk or '', 1)
        mine_events, _s = events_of('owner')
        theirs_events, _s2 = events_of('colleague')

        def commands_on(events, entity):
            return [e['command_id'] for e in events if entity in {x['id'] for x in e['entities']}]
        on_conversation = commands_on(mine_events, conversation_entity)
        on_turn = commands_on(mine_events, turn_entity)
        request_ids = [a[1].get('api_request_id') for a in (opened, role, attach, closed_call) if a[0] == 200]
        check('AC1/events', 'his feed carries the conversation opened, changed and closed, each by its command '
              '[%d]' % len(on_conversation), len(request_ids) == 4 and on_conversation == request_ids)
        check('AC1/events', 'and its turn waiting, started and ended with its reply kept [%s]'
              % [c.split('/')[1] if c.startswith('conversation/') else 'intake' for c in on_turn],
              len(on_turn) == 3 and on_turn[1].startswith('conversation/' + CV.DISPATCH + '/')
              and on_turn[2].startswith('conversation/' + CV.END + '/'))
        check('AC1/events', 'the close reached his open stream live; the colleague\'s stream got nothing of it',
              conversation_entity in ids_in(live_owner) and conversation_entity not in ids_in(live_other))
        their_kinds = kinds_in(theirs_events)
        check('AC1/events', 'the colleague\'s feed has nothing of the owner\'s conversation, its turn or its dispatch, '
              'and his own conversation\'s opening [%s]' % sorted(k for k in their_kinds if 'conversation' in k),
              not ({conversation_entity, turn_entity, 'dispatch:' + str(dispatch_id)} & ids_in(theirs_events))
              and CV.conversation_id(theirs or '') in ids_in(theirs_events))
        # Finding 1: once the turn has ended (its run index released, its reservations retired) and the conversation
        # closed, still no id of it anywhere he reads.
        leaks_ended = colleague_leaks(talk, dispatch_id, turn.get('intake_command'))
        check('AC1/events', 'no id carrying the owner\'s conversation or its turn\'s dispatch, nor the turn\'s intake '
              'source, on the colleague\'s feed or any read model, while the turn ran %s or after it ended %s'
              % (leaks_running, leaks_ended), bool(talk and dispatch_id and turn.get('intake_command'))
              and not leaks_running and not leaks_ended)

        # AC1/observability: each conversation route call with its principal, route, conversation id, outcome and
        # the request id its command carries; counted by route and outcome; never a message's text.
        conv_calls = [e for e in called if str(e.get('route')).startswith('conversations.')
                      or (e.get('route') == 'messages.send' and 'conversation' in e)]
        joined = {row[0] for row in authority.conn.execute('SELECT command_id FROM journal')}
        check('AC1/observability', 'each call is observed with its principal, route, conversation and outcome',
              conv_calls and all({'principal', 'route', 'conversation', 'outcome', 'request_id'} <= set(e)
                                 for e in conv_calls)
              and any(e['route'] == 'conversations.read' and e['principal'] == 'colleague'
                      and e['conversation'] == talk and e['outcome'] == 'refused'
                      and 'conversation_owner' in str(e['refusal']) for e in conv_calls)
              and any(e['route'] == 'conversations.open' and e['conversation'] == talk for e in conv_calls))
        check('AC1/observability', 'each accepted command call joins the journal command it sent',
              all(e['request_id'] in joined for e in conv_calls
                  if e['outcome'] == 'accepted' and e['route'] != 'conversations.read' and e['route'] != 'messages.send'))
        metrics = getattr(ui, 'conversation_metrics', dict)()
        check('AC1/observability', 'calls are counted by route and outcome [%s]' % metrics,
              metrics.get('conversations.close', {}).get('refused') == 3
              and metrics.get('conversations.close', {}).get('accepted') == 1
              and metrics.get('conversations.read', {}).get('refused') == 2)
        logged = json.dumps(called) + json.dumps(judged)
        check('AC1/observability', 'no message text, reply or session cookie is logged',
              words not in logged and 'deploy step failed' not in logged
              and not any(sessions[w][0] in logged for w in sessions))

        # AC2/observability: each read of a turn's record with its dispatch, joined to its conversation.
        reads = [e for e in judged if e.get('operation') == 'turn_record']
        check('AC2/observability', 'each turn record read is observed with its dispatch, conversation and turn',
              any(e['principal'] == 'owner' and e['outcome'] == 'served' and e['dispatch'] == dispatch_id
                  and e['conversation'] == talk and e['turn'] == 1 for e in reads)
              and any(e['principal'] == 'colleague' and e['outcome'] == 'refused' for e in reads))
        check('AC2/observability', 'reads refused for scope are counted [%s]'
              % {k: v for k, v in judge.counts.items() if 'turn_record' in k},
              judge.counts.get('turn_records_refused:missing_authority:conversation_owner', 0) >= 3)
        check('AC2/observability', 'no record payload or credential value is logged',
              token not in logged and 'cat deploy.env' not in logged)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for name in ROWS:
            check(name, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        for factory_value, lock_value in factories:
            try:
                for launch in list(factory_value.conversation.runner.launches.values()):
                    launch.stop('requested')
            except Exception:  # noqa: BLE001
                pass
            try:
                os.close(lock_value)
            except OSError:
                pass
        for stop in stops:
            stop()
        shutil.rmtree(base, ignore_errors=True)
    for name in ROWS:
        failed = [label for label, ok in rows[name] if not ok] or ([] if rows[name] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0178 detail:', name, '; '.join(failed))
        expect('VELDO-0178 ' + name, bool(rows[name]) and not failed)


_v178_suite()
