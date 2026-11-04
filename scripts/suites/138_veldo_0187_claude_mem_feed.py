"""VELDO-0187: every conversation turn reaches claude-mem's session history through a factory-side feed built from the
redacted record, so the owner's assistant and later conversations find it.

Run: python3 scripts/selftest.py --suite 138_veldo_0187_claude_mem_feed

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support), the production
conversation authority, VELDO-0174's conversation Line with real receiver subprocesses over fake pinned engines
(support/v174_journey.py, as suite 130_veldo_0176 drives them): the fake Claude Code prints a tool result carrying
the account's resolved subscription token and keeps it in its held session; the fake Codex prints a tool result
carrying the keystore credential its role's catalog server is delivered (a generated `secret-tool` first on PATH,
never the real keyring) and keeps it in its held session. claude-mem is the suite's own fixture plugin
(proof/VELDO-0187/fixtures.py): hook scripts that post four requests to its worker, qualified from that hook code,
at a qualified and an unqualified version, a fixture worker on loopback in a thread that writes what it is fed into
its own claude-mem.db, and VELDO-0183's claude-mem search server over that database, started as the catalog record
names it and as the plugin's .mcp.json names it. The Codex engine runs locally in its own transient user scope
(systemd-run, as suite 128's), since the receiver delivers catalog credentials only to a contained run: the suite
needs the systemd user manager. No real engine, login, claude-mem store or worker, or network. Writes only
temporary fixtures.
"""


def _v187_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import sys
    import tempfile
    import time

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which the receivers run) takes each of them.
    PRODUCTION = {
        'control_memory_feed.py': ROOT / ".veldo" / "control_memory_feed.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_factory_setup_memory.py': ROOT / ".veldo" / "control_factory_setup_memory.py",
    }
    ROWS = ('AC1/record', 'AC1/qualified', 'AC1/unqualified', 'AC1/loopback', 'AC1/no-credential',
            'AC2/one-session', 'AC2/record-order', 'AC2/redaction', 'AC2/feed-log',
            'AC3/found', 'AC3/pending', 'AC3/loop-pass', 'observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    H = load('v187_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v187_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v187_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    FX = load('v187_fixtures', ROOT / 'proof/VELDO-0187/fixtures.py')
    F183 = load('v187_f183', ROOT / 'proof/VELDO-0183/fixtures.py')
    base = Path(tempfile.mkdtemp(prefix='v187-', dir=fast_temp()))
    saved_path = os.environ.get('PATH')
    fixtures, factories, workers, servers = [], [], [], []

    # THE FAKE ENGINES: VELDO-0174's handshake and init, with the session each engine keeps in its profile (as suite
    # 130_veldo_0176's). After its marker a run holds while `hold-<conversation>` exists, prints a tool result carrying
    # its resolved credential (Claude Code: the account's subscription token; Codex: the keystore value its catalog
    # server is delivered as SERVER_TOKEN), keeps that result in its held session, and replies.
    INIT = "    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools,\n"
    SESSION_CODE = r'''    import re as _re, uuid as _uuid
    RESUMED = args[args.index('--resume') + 1] if '--resume' in args else None
    _dir = Path(os.environ.get('CLAUDE_CONFIG_DIR', '/nonexistent')) / 'projects' / _re.sub(r'[^a-zA-Z0-9]', '-', os.getcwd())
    SESSION = RESUMED if RESUMED and (_dir / (RESUMED + '.jsonl')).exists() else 'session-' + _uuid.uuid4().hex[:12]
    TRANSCRIPT = _dir / (SESSION + '.jsonl')
'''
    OWN = "own = {'engine':ENGINE,'tools':tools,"
    BODY = r'''import uuid
given = packet.get('payload') or {}
conversation = str(given.get('conversation'))
account = os.environ.get('VELDO_ACCOUNT')
if ENGINE == 'codex':
    home = Path(os.environ['CODEX_HOME'])
    RESUMED = args[args.index('resume') + 1] if 'resume' in args else None
    found = sorted(home.glob('sessions/**/rollout-*-%s.jsonl' % RESUMED)) if RESUMED else []
    if found:
        SESSION, TRANSCRIPT = RESUMED, found[-1]
    else:
        SESSION = 'thread-' + uuid.uuid4().hex[:12]
        TRANSCRIPT = home / 'sessions/2026/11/04' / ('rollout-2026-11-04T00-00-00-' + SESSION + '.jsonl')
def keep(said):
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with TRANSCRIPT.open('a') as handle: handle.write(json.dumps(said) + '\n')
own = {'engine':ENGINE,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),'argv':args,'packet':packet,
       'session':SESSION,'account':account,'environment':sorted(os.environ)}
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
while (MARKERS / ('hold-' + conversation)).exists(): time.sleep(.02)
turn = given.get('turn')
keep({'turn': turn, 'part': 'started', 'account': account})
if ENGINE == 'codex':
    emit({'type':'thread.started','thread_id':SESSION})
    emit({'type':'turn.started'})
    value = os.environ.get('SERVER_TOKEN', '')
    emit({'type':'item.completed','item':{'id':'cmd-%d' % os.getpid(),'type':'command_execution',
          'command':'cat vault.txt','aggregated_output':'resolved credential ' + value,'exit_code':0,
          'status':'completed'}})
    keep({'turn': turn, 'tool_result': 'resolved credential ' + value})
    reply = 'turn %s on codex: the lighthouse keeper logs every ship' % turn
    emit({'type':'item.completed','item':{'id':'say-%d' % os.getpid(),'type':'agent_message','text':reply}})
    emit({'type':'turn.completed','usage':{'input_tokens':12,'cached_input_tokens':0,'output_tokens':3}})
else:
    value = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')
    uid = 'toolu_cred_%d' % os.getpid()
    emit({'type':'assistant','session_id':SESSION,'message':{'id':'use-' + uid,'type':'message','role':'assistant',
          'content':[{'type':'tool_use','id':uid,'name':'Read','input':{'file_path':'credentials.txt'}}],
          'usage':{'input_tokens':1,'output_tokens':1}}})
    emit({'type':'user','session_id':SESSION,'message':{'role':'user','content':[{'type':'tool_result',
          'tool_use_id':uid,'content':'resolved credential ' + value}]}})
    keep({'turn': turn, 'tool_result': 'resolved credential ' + value})
    reply = 'turn %s on claude_code: the harbour plan moves the cranes north' % turn
    emit({'type':'rate_limit_event','session_id':SESSION,'rate_limit_info':{'status':'allowed',
          'rateLimitType':'five_hour','utilization':.25,'resetsAt':int(time.time())+3600}})
    emit({'type':'assistant','session_id':SESSION,'message':{'id':'say-%d' % os.getpid(),'type':'message',
          'role':'assistant','content':[{'type':'text','text':reply}],'usage':{'input_tokens':1,'output_tokens':1}}})
    emit({'type':'result','subtype':'success','is_error':False,'num_turns':1,'result':reply,'session_id':SESSION,
          'usage':{'input_tokens':12,'output_tokens':3}})
keep({'turn': turn, 'part': 'done'})
'''

    # The Codex role's catalog server, as Codex's own `mcp list` and `mcp get` report the table it is handed.
    MCP_LIST = "    if args[:2] == ['mcp','list']:\n        print('[]'); sys.exit(0)\n"
    MCP_NEW = r'''    if args[:1] == ['mcp']:
        _servers = dict(cfg.get('mcp_servers') or {})
        for _key, _value in cfg.items():
            if _key.startswith('mcp_servers.'):
                _servers.setdefault(_key.split('.')[1], {})
        if args[1] == 'list':
            print(json.dumps([{'name': n, 'enabled': True} for n in sorted(_servers)])); sys.exit(0)
        if args[1] == 'get':
            _table = _servers.get(args[2]) if isinstance(_servers.get(args[2]), dict) else {}
            print(json.dumps({'name': args[2], 'enabled': True,
                              'enabled_tools': list(_table.get('enabled_tools') or ['echo'])})); sys.exit(0)
'''

    # Its tool declarations to the role observation's loopback model: the server's tool and the resource readers.
    OBSERVED = "        body = {'tools': [{'type':'function','name':t} for t in tools]}\n"
    OBSERVED_NEW = r'''        _named = list(cfg.get('mcp_servers') or {}) + sorted({k.split('.')[1] for k in cfg if k.startswith('mcp_servers.')})
        if _named:
            tools = tools + ['mcp__%s__echo' % n for n in _named] + ['list_mcp_resource_templates', 'list_mcp_resources',
                                                                    'read_mcp_resource']
        body = {'tools': [{'type':'function','name':t} for t in tools]}
'''

    def fake_source():
        source = J.FAKE
        if source.count(MCP_LIST) != 1 or source.count(OBSERVED) != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        source = source.replace(MCP_LIST, MCP_NEW).replace(OBSERVED, OBSERVED_NEW)
        if source.count(INIT) != 1 or source.count(OWN) != 1 or source.count("'session_id':'fixture-session'") != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        if source.count("'num_turns':0,") != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        source = source.replace(INIT, SESSION_CODE + INIT).replace("'session_id':'fixture-session'", "'session_id':SESSION")
        source = source.replace("'num_turns':0,", "'num_turns':0,'session_id':SESSION,")
        return source[:source.index(OWN)] + BODY

    def install(tag, index):
        f = F.fixture(ROOT, base, H, load, tag, index, PRODUCTION)
        fixtures.append(f)
        mods = f['root'] / 'modules'
        CV = load('v187_conversation_' + tag, mods / 'control_conversation.py')
        CS = load('v187_service_' + tag, mods / 'control_service.py')
        CS.CV = CV
        authority = f['authority']
        domain = authority.ids['domain_uuid']
        observations = []
        f['observations'] = observations
        f['conversations'] = CV.Conversations(authority.S, authority.conn, domain=domain, principal='authority',
                                              signer='authority', sign=authority.journal_sign,
                                              state_root=f['root'] / 'state', observe=observations.append)
        saved, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved
        # THE KEYSTORE: a generated secret-tool first on PATH, and the Codex role's catalog server whose environment
        # names the keystore credential (VELDO-0158), delivered to the Codex engine as SERVER_TOKEN.
        keystore = f['root'] / 'keystore'
        keystore.mkdir(mode=0o700)
        tool = keystore / 'secret-tool'
        tool.write_text('''#!%s -B
import hashlib, json, pathlib, sys
home = pathlib.Path(__file__).parent
action, args = sys.argv[1], [a for a in sys.argv[2:] if not a.startswith('--label=')]
data = sys.stdin.buffer.read()
place = home / ('item-' + hashlib.sha256(json.dumps(dict(zip(args[::2], args[1::2])), sort_keys=True).encode()).hexdigest())
if action == 'store':
    place.write_bytes(data)
elif action == 'lookup':
    if not place.exists():
        sys.exit(1)
    sys.stdout.buffer.write(place.read_bytes())
else:
    sys.exit(2)
''' % sys.executable)
        tool.chmod(0o700)
        os.environ['PATH'] = str(keystore) + os.pathsep + (saved_path or '/usr/bin:/bin')
        server = f['root'] / 'mcp-server.py'
        server.write_text('''import json, sys
for raw in sys.stdin:
    message = json.loads(raw)
    if 'id' not in message:
        continue
    if message['method'] == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'fixture', 'version': '1'}}
    elif message['method'] == 'tools/list':
        result = {'tools': [{'name': 'echo', 'description': 'echo', 'inputSchema': {'type': 'object'}}]}
    else:
        result = {}
    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}), flush=True)
''')
        hashed = hashlib.sha256((domain + '/vault-token').encode()).hexdigest()
        reference = 'keychain:veldo/' + hashed
        codex_value = 'v187-vault-%s' % os.urandom(8).hex()
        attributes = {'application': 'veldo', 'credential': 'veldo/' + hashed}
        (keystore / ('item-' + hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest())
         ).write_text(codex_value)
        authority.fixture('credential:' + hashed, 'credential', {'id': 'vault-token', 'label': 'vault',
                                                                'reference': reference, 'set_at': time.time(),
                                                                'set_by': 'owner'})
        MC = CV.CFG.MC
        definition = {'id': 'vault', 'label': 'vault', 'transport': 'stdio', 'command': sys.executable,
                      'arguments': [str(server)], 'url': None,
                      'environment': {'SERVER_TOKEN': {'reference': reference}}, 'headers': {},
                      'hosts': ['127.0.0.1'], 'read_only_tools': []}
        authority.fixture(MC.revision_id(domain, 'vault', 1), MC.KIND, dict(definition, revision=1))
        authority.fixture(MC.head_id(domain, 'vault'), MC.HEAD_KIND, {'id': 'vault', 'revision': 1})
        revision = f['revisions']['assistant_codex']
        revision['mcp'] = [{'server': 'vault', 'revision': 1, 'tools': 'all', 'load': 'always'}]
        revision['digest'] = CV.CFG.digest({k: v for k, v in revision.items() if k != 'digest'})
        authority.fixture('configuration:assistant_codex', 'agent_configuration', revision)
        accounts = load('v187_accounts_' + tag, mods / 'control_accounts.py').Accounts(
            authority.S, authority.conn, principal='owner', signer='authority', sign=authority.journal_sign)
        config = json.loads(receiver.read_text())
        tokens = {'codex': codex_value}
        for provider in ('claude_code', 'codex'):
            account = 'account-%s-1' % provider
            profile = f['root'] / ('profile-' + account)
            profile.mkdir(parents=True)
            accounts.register('account-register-' + account, account, provider, account, {f['host']: str(profile)},
                              concurrency=1, now=time.time())
            if provider == 'claude_code':
                value = 'v187-token-%s' % os.urandom(8).hex()
                path = f['root'] / ('token-' + account)
                path.write_text(value)
                path.chmod(0o600)
                tokens['claude_code'] = value
                config.setdefault('subscription_tokens', {})[account] = str(path)
        # The Codex engine runs LOCALLY, contained in its own transient scope (as suite 128's), since the receiver
        # delivers catalog credentials only to a contained Linux engine run (VELDO-0158).
        X = load('v187_codex_' + tag, mods / 'control_engine_codex.py')
        executable = config['adapters']['codex']['executable']
        config['adapters']['codex'] = {'engine': 'codex', 'executable': executable,
                                       'qualification': config['adapters']['codex']['qualification'],
                                       'argv': [executable] + list(X.FLAGS)}
        config['profile'] = {'kind': 'linux-systemd', 'slice': 'v187%s.slice' % os.urandom(4).hex(),
                             'lock': str(f['root'] / 'slice.lock'), 'concurrency': 16, 'runtime_seconds': 120,
                             'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20, 'tasks_max': 256,
                             'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4,
                             'systemd_run': shutil.which('systemd-run') or '/usr/bin/systemd-run'}
        receiver.write_text(json.dumps(config))
        f.update(CV=CV, CS=CS, receiver=receiver, markers=markers, mods=mods, tokens=tokens, config=config)
        return f

    def observed(markers):
        found = {}
        for path in markers.glob('*.json'):
            if path.name.split('.')[0].isdigit() and path.name.count('.') == 1:
                value = json.loads(path.read_text())
                found[value.get('dispatch')] = value
        return found

    def runs_of(markers, identity):
        return [v for v in observed(markers).values() if ((v.get('packet') or {}).get('payload') or {})
                .get('conversation') == identity]

    def start_loop(f):
        from types import SimpleNamespace
        CS, authority, events = f['CS'], f['authority'], []
        service = SimpleNamespace(
            config={'receiver': {'conversations': str(f['receiver'])}, 'journal_key': str(authority.keyfile['authority'])},
            conn=authority.conn, domain=authority.ids['domain_uuid'], principal='authority', generation=1,
            sign=authority.journal_sign, conversations=lambda: f['conversations'], _log=events.append,
            repositories={}, store=authority.ids['store_uuid'],
            watermark=lambda: authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0],
            inbox=lambda coordinate: CS.I.Inbox(
                CS.S, CS.CM, CS.CLM, CS.ENT, authority.conn,
                {'domain_uuid': authority.ids['domain_uuid'], 'repository_uuid': coordinate,
                 'store_uuid': authority.ids['store_uuid']}, 'authority', authority.journal_sign, 1))
        wrapper = f['root'] / 'receiver-driver.py'
        wrapper.write_text('import runpy,sys\nsys.stderr=open(' + repr(str(f['root'] / 'receiver-errors.log'))
                           + ", 'a')\nrunpy.run_path(" + repr(str(f['mods'] / 'control_launch.py'))
                           + ",run_name='__main__')\n")
        CS.L.RECEIVER = str(wrapper)
        factory = CS.FactoryLoop(service, None)
        lock = CS.acquire(str(authority.db.parent / 'authority.lock'), {'principal': 'authority'})
        factory.lock = lock
        factories.append((factory, lock))
        factory.start()
        return factory, events

    def release_lock(lock_value):
        close = getattr(lock_value, 'close', None)
        if close:
            close()
        elif isinstance(lock_value, int):
            try:
                os.close(lock_value)
            except OSError:
                pass

    def turns(f, identity):
        return f['conversations'].turns(identity)

    def settled(f, identity, count):
        saved = turns(f, identity)
        return len(saved) >= count and saved[count - 1].get('state') == 'ended'

    def say(f, identity, text):
        return f['conversations'].message(identity, text, 'sha256:' + identity + text, owner='owner')

    def run_turn(f, factory, identity, text, count, seconds=40):
        say(f, identity, text)
        J.pass_(factory)
        return F.drive(factory, lambda: settled(f, identity, count), seconds)

    def feed_log(f, identity):
        path = Path(f['conversations'].read(identity)['directory']) / 'claude-mem' / 'feed.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []

    def capture(turn):
        return (turn.get('claude_mem') or {})

    def FX_digest(path):
        return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

    try:
        f = install('main', 87)
        CV, markers, authority, mods = f['CV'], f['markers'], f['authority'], f['mods']
        conversations = f['conversations']
        FEED = load('v187_feed', mods / 'control_memory_feed.py')
        SM = load('v187_setup_memory', mods / 'control_factory_setup_memory.py')
        MS = load('v187_memory_servers', mods / 'control_memory_servers.py')
        state = f['root'] / 'state'
        stores = base / 'stores'
        manifest = F183.build(stores, f['host'])
        interpreter = Path(manifest['parts']['ava_memory']['interpreter'])

        # AC1: the qualification record, read from the fixture version's own hook code at qualification.
        QUALIFIED, UNLISTED = '10.6.2-v187', '10.9.9-v187'
        code, data = FX.plugin(stores, QUALIFIED, F183.CLAUDE_MEM, interpreter)
        worker = FX.Worker(data)
        workers.append(worker)
        record_file = mods / FEED.QUALIFICATION
        written = FEED.record_qualified(code, record_file)
        entry = written['versions'].get(QUALIFIED) or {}
        shipped = json.loads((ROOT / '.veldo/runtime/claude-mem-qualification.json').read_text())
        check('AC1/record', 'the shipped record is the qualification schema, listing versions by hook digests',
              shipped.get('schema') == FEED.RECORD_SCHEMA and isinstance(shipped.get('versions'), dict)
              and all(set(v) >= {'hooks', 'requests', 'address'} for v in shipped['versions'].values()))
        check('AC1/record', 'the fixture version is qualified from its own hook code: every hook script\'s digest',
              entry.get('hooks') == {'hooks/hooks.json': FX_digest(code / 'hooks/hooks.json'),
                                     **{'scripts/' + s: FX_digest(code / 'scripts' / s)
                                        for s, _p, _b in FX.ROUTES.values()}})
        check('AC1/record', 'each of the four requests its hooks send, with its fields, read from the scripts',
              {k: (v['method'], v['path'], v['fields']) for k, v in (entry.get('requests') or {}).items()} == {
                  'start': ('POST', '/api/sessions/start', ['contentSessionId', 'project', 'cwd']),
                  'prompt': ('POST', '/api/sessions/init', ['contentSessionId', 'project', 'prompt', 'promptNumber']),
                  'observation': ('POST', '/api/sessions/observations',
                                  ['contentSessionId', 'tool_name', 'tool_input', 'tool_response', 'cwd']),
                  'summary': ('POST', '/api/sessions/summarize', ['contentSessionId', 'last_assistant_message'])})
        check('AC1/record', 'the worker\'s loopback address, read from the scripts',
              (entry.get('address') or {}).get('host') == '127.0.0.1' and entry['address'].get('port') == 37777)
        refusals = {}
        for name, routes, host in (
                ('paid', dict(FX.ROUTES, Stop=('summarize.js', '/api/sessions/summarize',
                                               'contentSessionId: input.session_id, ANTHROPIC_API_KEY: input.key')),
                 '127.0.0.1'),
                ('far', FX.ROUTES, '192.0.2.7'),
                ('missing', {k: v for k, v in FX.ROUTES.items() if k != 'PostToolUse'}, '127.0.0.1')):
            other, _other_data = FX.plugin(base / ('refused-' + name), '0.0.' + str(len(refusals)), 'pass', interpreter,
                                           host=host, routes=routes)
            try:
                FEED.qualify(other)
                refusals[name] = None
            except FEED.Refused as error:
                refusals[name] = error.code
        check('AC1/record', 'hook code with a paid-API field, a non-loopback address or a missing request is not '
              'qualified, by name [%s]' % refusals,
              refusals == {'paid': 'invalid_input:claude_mem:paid_api:ANTHROPIC_API_KEY', 'far': FEED.NOT_LOOPBACK,
                           'missing': 'missing_evidence:claude_mem_request:observation'})

        # Setup reads the installed version from VELDO-0182's claude-mem part (setup's memory step).
        definition = json.loads(json.dumps(manifest))
        definition['parts']['claude_mem'] = dict(code=str(code), data=str(data),
                                                 command=[str(interpreter), '-B', str(code / 'search.py'), str(data)])
        report = SM.apply({'root': str(state)}, {'definition': definition, 'previous': {'definition': definition},
                                                 'outcome': 'already_done'}, None, None, None, None, None)
        setting = FEED.read_setting(state) or {}
        print('  VELDO-0187 setup:', report.get('claude_mem_feed'))
        check('AC1/qualified', 'setup\'s memory step reads the installed version and records it qualified',
              report.get('claude_mem_feed') == {'version': QUALIFIED, 'state': 'qualified', 'refusal': None,
                                                'qualification': FEED.digest(entry)}
              and setting.get('address') == {'host': '127.0.0.1', 'port': worker.port}
              and oct(FEED.setting_path(state).stat().st_mode & 0o777) == '0o600')

        factory, _events = start_loop(f)

        # AC3 and AC2: turn 1 on the Claude Code account while the worker is down; turn 2 on the Codex account, the
        # worker started while it runs.
        conversations.open('remember', owner='owner', role='assistant', intake_digest='sha256:remember')
        run_turn(f, factory, 'remember', 'remember the blue harbour plan', 1)
        first = turns(f, 'remember')[0]
        directory = Path(conversations.read('remember')['directory'])
        pending_files = sorted(p.name for p in (directory / 'claude-mem' / 'pending').glob('*.json'))
        print('  VELDO-0187 turn 1:', first.get('account'), first.get('outcome'), capture(first), pending_files)
        check('AC3/pending', 'turn 1, fed while the worker does not answer, stays pending in the conversation\'s '
              'directory by name', first.get('outcome') == 'completed' and pending_files == ['00000001.json']
              and capture(first).get('state') == 'pending' and capture(first).get('reason') == FEED.UNAVAILABLE)
        version = conversations.read('remember')['version']
        conversations.change_role('remember', version, 'assistant_codex', owner='owner')
        (markers / 'hold-remember').write_text('1')
        say(f, 'remember', 'and the lighthouse logbook')
        J.pass_(factory)
        J.eventually(lambda: len(runs_of(markers, 'remember')) >= 2, 30)
        running = turns(f, 'remember')[1].get('state')
        worker.start()
        (markers / 'hold-remember').unlink()
        F.drive(factory, lambda: settled(f, 'remember', 2), 40)
        F.drive(factory, lambda: capture(turns(f, 'remember')[1]).get('state') == 'captured', 10)
        first, second = turns(f, 'remember')
        received = list(worker.received)
        bodies = [r['body'] or {} for r in received]
        print('  VELDO-0187 turn 2:', second.get('account'), second.get('outcome'), running, capture(second),
              [(r['path'], (r['body'] or {}).get('promptNumber')) for r in received])
        numbers = [b.get('promptNumber') for b in bodies if b.get('promptNumber') is not None]
        states = [s['state'] for s in first.get('claude_mem_states') or []]
        check('AC3/pending', 'the worker was started while turn 2 ran, and turn 1\'s feed was sent, before turn 2\'s',
              running == 'dispatched' and numbers == [1, 2]
              and max((i for i, r in enumerate(received) if 'credentials.txt' in json.dumps(r['body'])), default=10 ** 6)
              < min((i for i, r in enumerate(received) if 'cat vault.txt' in json.dumps(r['body'])), default=-1))
        check('AC3/pending', 'the turn record shows pending, then captured; nothing stays pending',
              [s for n, s in enumerate(states) if n == 0 or states[n - 1] != s] == ['pending', 'captured']
              and any(s.get('reason') == FEED.UNAVAILABLE for s in first.get('claude_mem_states') or [])
              and capture(second).get('state') == 'captured'
              and not list((directory / 'claude-mem' / 'pending').glob('*.json')))

        # AC3: found by the catalog server a later conversation is given, and by the assistant's own search server.
        catalog = MS.definitions(definition, sys.executable, str(mods), str(state), 1,
                                 {s: 1 for s, _p in MS.SERVERS})['claude-mem']
        later = FX.Stdio(catalog['command'], catalog['arguments'])
        servers.append(later)
        assistant_entry = json.loads((code / '.mcp.json').read_text())['mcpServers']['claude-mem']
        own = FX.Stdio(assistant_entry['command'], assistant_entry['args'])
        servers.append(own)
        found = {name: {query: bool(client.search(query)) for query in ('blue harbour plan', 'lighthouse logbook')}
                 for name, client in (('catalog', later), ('assistant', own))}
        print('  VELDO-0187 search:', found)
        check('AC3/pending', 'after turn 2 both turns are found: turn 1 was never lost [%s]' % found,
              found['catalog'] == {'blue harbour plan': True, 'lighthouse logbook': True})
        check('AC3/found', 'a later conversation\'s claude-mem search tool (the catalog record) finds turn 1\'s message',
              found['catalog']['blue harbour plan'] and catalog['command'] == str(interpreter))
        check('AC3/found', 'the owner\'s assistant\'s claude-mem search server, as its plugin starts it, finds it too',
              found['assistant']['blue harbour plan'] and found['assistant']['lighthouse logbook'])
        replies = {name: bool(client.search('harbour plan moves the cranes')) for name, client in
                   (('catalog', later), ('assistant', own))}
        check('AC3/found', 'and turn 1\'s reply [%s]' % replies, all(replies.values()))

        # AC2: one session across accounts and engines, every request from the redacted record, in its order.
        sessions = {b.get('contentSessionId') for b in bodies}
        check('AC2/one-session', 'turn 1 ran on the Claude Code account and turn 2 on the Codex account',
              first.get('account') == 'account-claude_code-1' and second.get('account') == 'account-codex-1'
              and first.get('outcome') == second.get('outcome') == 'completed')
        check('AC2/one-session', 'both turns joined one claude-mem session, the conversation\'s [%s]' % sessions,
              sessions == {FEED.session_of('remember')} and capture(first).get('session') == FEED.session_of('remember')
              and capture(second).get('session') == FEED.session_of('remember'))
        check('AC2/one-session', 'the conversation\'s first feed started it, once',
              [r['path'] for r in received].count('/api/sessions/start') == 1
              and received[0]['path'] == '/api/sessions/start')
        expected = []
        for turn in (first, second):
            lines = conversations.record_lines('remember', turn['sequence'], turn['dispatch_id'])
            read = CV.turn_from_record(lines or [])
            expected += [('/api/sessions/init', read['message'])]
            expected += [('/api/sessions/observations', json.dumps(call['input'], sort_keys=True), call['result'])
                         for call in read['calls']]
            expected += [('/api/sessions/summarize', read['reply'])]
        sent = []
        for r in received[1:]:
            b = r['body'] or {}
            if r['path'] == '/api/sessions/observations':
                sent.append((r['path'], json.dumps(b.get('tool_input'), sort_keys=True), b.get('tool_response')))
            else:
                sent.append((r['path'], b.get('prompt') if r['path'] == '/api/sessions/init'
                             else b.get('last_assistant_message')))
        print('  VELDO-0187 requests:', [s[0].rsplit('/', 1)[-1] for s in sent])
        check('AC2/record-order', 'the prompt, each tool call as an observation and the reply with the summary '
              'request, each turn in its record\'s order, every value its redacted record\'s',
              sent == expected and len(expected) == 6)
        check('AC2/record-order', 'the owner\'s messages and the replies are the turns\' own',
              [b.get('prompt') for b in bodies if 'prompt' in b] == ['remember the blue harbour plan',
                                                                      'and the lighthouse logbook']
              and [b.get('last_assistant_message') for b in bodies if 'last_assistant_message' in b]
              == [first.get('reply'), second.get('reply')])
        everything = json.dumps(received) + (directory / 'claude-mem' / 'feed.jsonl').read_text()
        held = [Path((t.get('session') or {}).get('capture') or '/nonexistent/v187') for t in (first, second)]
        check('AC2/redaction', 'each held session itself carries its turn\'s resolved credential value',
              all(p.is_file() for p in held) and f['tokens']['claude_code'] in held[0].read_text()
              and f['tokens']['codex'] in held[1].read_text())
        observations_sent = [b for r, b in zip(received, bodies) if r['path'] == '/api/sessions/observations']
        check('AC2/redaction', 'neither credential value reached the worker or the feed log',
              f['tokens']['claude_code'] not in everything and f['tokens']['codex'] not in everything)
        check('AC2/redaction', 'the tool results the worker observed are the records\' redacted ones',
              len(observations_sent) == 2 and all('resolved credential [REDACTED' in str(b.get('tool_response'))
                                                  for b in observations_sent))
        log = feed_log(f, 'remember')
        taken = [e for e in log if e.get('status') == 200]
        check('AC2/feed-log', 'each request is kept in the conversation\'s feed log with its digest and the worker\'s '
              'answer', len(taken) == len(received) and all(
                  e['digest'] == FEED.digest(e['request']['body']) and e['answer'] in ({'status': 'queued'},
                  {'status': 'started', 'sessionDbId': FEED.session_of('remember')}) for e in taken)
              and [e['request']['body'] for e in taken] == bodies)
        check('AC2/feed-log', 'the attempts the down worker did not take are kept too, by name',
              any(e.get('error') == FEED.UNAVAILABLE and e.get('sequence') == 1 for e in log)
              and oct((directory / 'claude-mem' / 'feed.jsonl').stat().st_mode & 0o777) == '0o600')
        headers = {name.lower() for r in received for name in r['headers']}
        check('AC1/no-credential', 'requests carry no header but the content type and the transport\'s own [%s]'
              % sorted(headers), headers <= {'host', 'content-type', 'content-length', 'user-agent',
                                             'accept-encoding', 'connection'})
        paid = FEED.paid_names()
        check('AC1/no-credential', 'no field any request carries is a paid-API or login name',
              paid and not any(name in paid for b in bodies for name in b))
        check('AC1/qualified', 'a qualified version is fed: only its four qualified routes, on its loopback worker',
              {r['path'] for r in received} == {v['path'] for v in entry['requests'].values()}
              and capture(second).get('requests') == {'prompt': 1, 'observation': 1, 'summary': 1})

        # AC3: a feed the worker did not take is sent on the next loop pass after it answers, without a new turn.
        worker.stop()
        conversations.open('backlog', owner='owner', role='assistant', intake_digest='sha256:backlog')
        run_turn(f, factory, 'backlog', 'the backlog tide table', 1)
        waiting_turn = turns(f, 'backlog')[0]
        worker.start()
        before = len(worker.received)
        J.pass_(factory)
        passed = turns(f, 'backlog')[0]
        print('  VELDO-0187 loop pass:', capture(waiting_turn), capture(passed), len(worker.received) - before)
        check('AC3/loop-pass', 'a turn that ended while the worker was down is pending, then captured by the next loop '
              'pass after the worker answers', capture(waiting_turn).get('state') == 'pending'
              and capture(passed).get('state') == 'captured' and capture(passed).get('late') is True
              and len(worker.received) - before == 4 and later.search('backlog tide table'))

        # AC1: an installed version the record does not list gets no feed: every turn not captured, nothing sent.
        unlisted, unlisted_data = FX.plugin(base / 'unlisted', UNLISTED, F183.CLAUDE_MEM, interpreter)
        other_worker = FX.Worker(unlisted_data)
        workers.append(other_worker)
        other_worker.start()
        unlisted_definition = json.loads(json.dumps(definition))
        unlisted_definition['parts']['claude_mem'].update(code=str(unlisted), data=str(unlisted_data))
        report_unlisted = SM.claude_mem_feed(str(state), unlisted_definition)
        conversations.open('unlisted', owner='owner', role='assistant', intake_digest='sha256:unlisted')
        run_turn(f, factory, 'unlisted', 'the unlisted orchard', 1)
        run_turn(f, factory, 'unlisted', 'the unlisted orchard again', 2)
        J.pass_(factory)
        unlisted_turns = turns(f, 'unlisted')
        print('  VELDO-0187 unlisted:', report_unlisted, [capture(t) for t in unlisted_turns],
              len(other_worker.received))
        check('AC1/unqualified', 'setup records the unlisted version refused by name',
              report_unlisted == {'version': UNLISTED, 'state': 'refused',
                                  'refusal': 'missing_evidence:claude_mem_version:' + UNLISTED, 'qualification': None})
        check('AC1/unqualified', 'every turn is recorded not captured by name',
              [capture(t).get('state') for t in unlisted_turns] == ['not_captured', 'not_captured']
              and {capture(t).get('reason') for t in unlisted_turns} == {'missing_evidence:claude_mem_version:' + UNLISTED})
        check('AC1/unqualified', 'and the fixture worker at the unqualified version received nothing [%d]'
              % len(other_worker.received), other_worker.received == [])
        # The qualified version number over hook code that differs from the record is not qualified either.
        changed, changed_data = FX.plugin(base / 'changed', QUALIFIED, F183.CLAUDE_MEM, interpreter)
        (changed / 'scripts' / 'summarize.js').write_text((changed / 'scripts' / 'summarize.js').read_text() + '// x\n')
        changed_definition = json.loads(json.dumps(definition))
        changed_definition['parts']['claude_mem'].update(code=str(changed), data=str(changed_data))
        check('AC1/unqualified', 'a listed version whose hook scripts differ from the record is refused the same way',
              SM.claude_mem_feed(str(state), changed_definition)['refusal']
              == 'missing_evidence:claude_mem_version:' + QUALIFIED)

        # AC1: a worker address that is not loopback gets no feed.
        (data / 'settings.json').write_text(json.dumps({'CLAUDE_MEM_WORKER_HOST': '192.0.2.9',
                                                        'CLAUDE_MEM_WORKER_PORT': str(worker.port)}))
        report_far = SM.claude_mem_feed(str(state), definition)
        before = len(worker.received)
        conversations.open('faraway', owner='owner', role='assistant', intake_digest='sha256:faraway')
        run_turn(f, factory, 'faraway', 'the faraway beacon', 1)
        far_turn = turns(f, 'faraway')[0]
        refused_send = None
        try:
            FEED.send({'address': {'host': '192.0.2.9', 'port': worker.port}},
                      {'method': 'POST', 'path': '/api/sessions/init', 'body': {}})
        except FEED.Refused as error:
            refused_send = error.code
        print('  VELDO-0187 not loopback:', report_far, capture(far_turn), refused_send)
        check('AC1/loopback', 'a worker address that is not loopback is refused by name at setup',
              report_far['state'] == 'refused' and report_far['refusal'] == FEED.NOT_LOOPBACK)
        check('AC1/loopback', 'its turns are recorded not captured by that name and nothing is sent',
              capture(far_turn).get('state') == 'not_captured' and capture(far_turn).get('reason') == FEED.NOT_LOOPBACK
              and len(worker.received) == before)
        check('AC1/loopback', 'the feed itself sends only to a loopback address', refused_send == FEED.NOT_LOOPBACK)

        # OBSERVABILITY: each feed logged with conversation, turn, session, request kinds and digests, answers and
        # capture states, joined to its execution record and qualification; never turn content. Metrics counted.
        events = [o for o in f['observations'] if o.get('operation') == 'claude_mem_feed']
        joined = [o for o in events if o.get('conversation') == 'remember' and o.get('capture') == 'pending'
                  and o.get('requests')]
        committed = {t['sequence']: ((authority.conn.execute('SELECT data FROM entities WHERE id=?',
                                                              ('dispatch:' + t['dispatch_id'],)).fetchone() or ['{}'])[0])
                     for t in (first, second)}
        check('observability', 'each feed is logged with its turn, session, request kinds and digests, joined to its '
              'execution record and qualification record',
              len(joined) == 2 and all(o.get('session') == FEED.session_of('remember')
                                       and o.get('qualification') == FEED.digest(entry)
                                       and o.get('execution_record') and o['execution_record'] in committed[o['sequence']]
                                       and all(set(r) == {'kind', 'digest'} for r in o['requests']) for o in joined))
        check('observability', 'each request\'s answer and each capture state (pending, captured, not captured with its '
              'reason) is logged', any(o.get('status') == 200 for o in events)
              and {o.get('capture') for o in events} >= {'pending', 'captured', 'not_captured'}
              and any(o.get('reason') == FEED.UNAVAILABLE for o in events))
        text = json.dumps(events)
        check('observability', 'never turn content',
              not any(s in text for s in ('blue harbour', 'lighthouse', 'cranes north', 'resolved credential',
                                          f['tokens']['claude_code'], f['tokens']['codex'])))
        metrics = conversations.status().get('claude_mem') or {}
        print('  VELDO-0187 metrics:', metrics)
        check('observability', 'turns captured, pending, not captured by reason, requests by kind and late feeds are '
              'counted', metrics.get('captured') == 3 and metrics.get('pending') == 0
              and metrics.get('not_captured') == {'missing_evidence:claude_mem_version:' + UNLISTED: 2,
                                                  FEED.NOT_LOOPBACK: 1}
              and metrics.get('requests') == {'start': 2, 'prompt': 3, 'observation': 3, 'summary': 3}
              and metrics.get('late') == 2)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        for client in servers:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
        for value in workers:
            value.stop()
        for factory_value, lock_value in factories:
            try:
                for launch in list(factory_value.conversation.runner.launches.values()):
                    launch.stop('requested')
            except Exception:  # noqa: BLE001
                pass
            release_lock(lock_value)
        for value in fixtures:
            value['authority'].conn.close()
        if saved_path is not None:
            os.environ['PATH'] = saved_path
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0187 detail:', row, '; '.join(failed))
        expect('VELDO-0187 ' + row, bool(rows[row]) and not failed)


_v187_suite()
