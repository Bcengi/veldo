"""VELDO-0177: a conversation acts in its own workspace with exactly its role's tools and servers, inside the same
containment and credential rules as project runs, and works on a fresh clone of a project attached to it.

Run: python3 scripts/selftest.py --suite 128_veldo_0177_conversation_workspace

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support), the production
conversation authority and VELDO-0174's conversation Line with real receiver subprocesses (support/v174_journey.py)
over fake pinned engines generated here from VELDO-0174's, launched locally: each turn runs contained in a VELDO-0040
worker group, a transient scope of the owner's systemd user manager in a slice of this run's own, stopped at its end.
MCP credentials resolve through a generated fake `secret-tool` first on PATH, never the real keyring. The loopback
page a turn fetches is served here. Fake engines only: no real Claude Code or Codex runs, no login, no network
beyond loopback. Writes only temporary fixtures.
"""


def _v177_suite():
    import hashlib
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

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which the receivers run) takes each of them.
    PRODUCTION = {
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        'control_factory_setup_dispatch.py': ROOT / ".veldo" / "control_factory_setup_dispatch.py",
    }
    ROWS = ('AC1/workspace-made', 'AC1/isolation', 'AC1/contained', 'AC1/credentials', 'AC1/launch-guards',
            'AC1/workspace-refused', 'AC1/observability',
            'AC2/offered-tools', 'AC2/codex-launch', 'AC2/turn-record',
            'AC3/attach-clone', 'AC3/scope', 'AC3/no-publication', 'AC3/attach-again', 'AC3/observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def refusal(call):
        try:
            call()
        except Exception as error:  # noqa: BLE001
            return getattr(error, 'code', type(error).__name__)
        return None

    def git(*args, cwd=None, check=True):
        done = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
        if check and done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(args[:2]), done.stderr[-300:]))
        return done.stdout

    H = load('v177_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v177_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v177_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    base = Path(tempfile.mkdtemp(prefix='v177-', dir=fast_temp()))
    slice_name = 'v177%s.slice' % os.urandom(4).hex()
    saved_path, saved_key = os.environ.get('PATH'), os.environ.get('ANTHROPIC_API_KEY')
    lock = factory = server = None
    fixtures = []

    # THE FAKE ENGINES: VELDO-0174's, which also record their working directory, their cgroup (the worker group),
    # their environment's names, and Claude Code's generated MCP configuration (the credential file) with its path;
    # after the release they follow the scenario in the markers directory: edit a file, run a command and fetch
    # the loopback page with the tools they were offered (`work`), or read the attached clone's history, commit in
    # it and try to push (`project`), each written as a tool call and its result on the stream.
    OWN = "(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))\n"
    OWN_NEW = r'''own['cgroup'] = Path('/proc/self/cgroup').read_text()
own['environment'] = sorted(os.environ)
own['mcp_path'] = args[args.index('--mcp-config')+1] if '--mcp-config' in args else None
own['mcp_text'] = Path(own['mcp_path']).read_text() if own['mcp_path'] else None
own['config'] = opts() if ENGINE == 'codex' else None
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
'''
    RELEASE = "while not (MARKERS / 'release').exists(): time.sleep(.02)\n"
    WORK = r'''import subprocess
scenario = json.loads((MARKERS / 'scenario.json').read_text()) if (MARKERS / 'scenario.json').exists() else {}
done = {}
def use(name, given, result):
    uid = 'toolu_' + name.lower() + '_' + str(os.getpid())
    emit({'type':'assistant','message':{'id':'use-'+uid,'type':'message','role':'assistant',
          'content':[{'type':'tool_use','id':uid,'name':name,'input':given}],'usage':{'input_tokens':1,'output_tokens':1}}})
    emit({'type':'user','message':{'role':'user','content':[{'type':'tool_result','tool_use_id':uid,'content':result}]}})
    done[name] = result
if ENGINE != 'codex' and scenario.get('mode') == 'work':
    if 'Edit' in tools:
        Path('notes.txt').write_text('drafted by the turn\n')
        use('Edit', {'file_path':'notes.txt','old_string':'','new_string':'drafted by the turn'}, 'edited notes.txt')
    if 'Bash' in tools:
        ran = subprocess.run(['sh','-c','echo ran > ran.txt; cat ran.txt; pwd'],capture_output=True,text=True).stdout
        use('Bash', {'command':'echo ran > ran.txt; cat ran.txt; pwd'}, ran)
    if 'WebFetch' in tools:
        page = urllib.request.urlopen(scenario['url'], timeout=10).read().decode()
        use('WebFetch', {'url':scenario['url'],'prompt':'read it'}, page)
    if own['mcp_text']:
        servers = json.loads(own['mcp_text']).get('mcpServers', {})
        leaked = [v for s in servers.values() for v in (s.get('env') or {}).values()]
        emit({'type':'assistant','message':{'id':'leak','type':'message','role':'assistant',
              'content':[{'type':'text','text':'credential ' + ' '.join(leaked)}],'usage':{'input_tokens':1,'output_tokens':1}}})
if ENGINE != 'codex' and scenario.get('mode') == 'project':
    clone = scenario['clone']
    log = subprocess.run(['git','-C',clone,'log','--format=%H %s'],capture_output=True,text=True).stdout
    use('Bash', {'command':'git log'}, log)
    Path(clone, 'turn.txt').write_text('changed by the turn\n')
    subprocess.run(['git','-C',clone,'add','turn.txt'],capture_output=True)
    commit = subprocess.run(['git','-C',clone,'-c','user.name=Turn','-c','user.email=turn@example.invalid',
                             'commit','-qm','turn change'],capture_output=True,text=True)
    use('Bash', {'command':'git commit'}, str(commit.returncode))
    push = subprocess.run(['git','-C',clone,'push','origin','HEAD:refs/heads/conversation-change'],
                          capture_output=True,text=True)
    use('Bash', {'command':'git push'}, str(push.returncode) + ' ' + push.stderr[-200:])
    done['log'] = log
    done['commit'] = commit.returncode
    done['push'] = push.returncode
(MARKERS / (str(os.getpid()) + '.work.json')).write_text(json.dumps(done))
'''
    # As the binary does, the init event lists each configured MCP server's tools, read from the server itself.
    INIT = "    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools,\n"
    INIT_NEW = r'''    mcp_tools = []
    if '--mcp-config' in args:
        import subprocess as listing
        configured = json.loads(Path(args[args.index('--mcp-config')+1]).read_text()).get('mcpServers', {})
        for server_name, server in configured.items():
            answer = listing.run([server['command']] + list(server.get('args') or []), capture_output=True, text=True,
                                 input=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/list'}) + chr(10),
                                 env=dict(os.environ, **(server.get('env') or {})), timeout=10)
            for line in answer.stdout.splitlines():
                mcp_tools += ['mcp__%s__%s' % (server_name, t['name'])
                              for t in json.loads(line).get('result', {}).get('tools', [])]
    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools + mcp_tools,
'''
    CODEX_TOOLS = "    tools = ['update_plan'] if cfg.get('tools.update_plan', {}).get('enabled') else []\n"
    CODEX_TOOLS_NEW = ("    tools = json.loads((MARKERS / 'codex-tools.json').read_text()) "
                       "if (MARKERS / 'codex-tools.json').exists() else []\n")

    def fake_source():
        source = J.FAKE
        for old in (OWN, RELEASE, CODEX_TOOLS, INIT):
            if source.count(old) != 1:
                raise RuntimeError('the VELDO-0174 fake engine moved')
        return source.replace(OWN, OWN_NEW).replace(RELEASE, RELEASE + WORK).replace(CODEX_TOOLS, CODEX_TOOLS_NEW).replace(INIT, INIT_NEW)

    def observed(markers):
        found = {}
        for path in markers.glob('*.json'):
            if path.name.split('.')[0].isdigit() and path.name.count('.') == 1:
                value = json.loads(path.read_text())
                work = markers / (path.stem + '.work.json')
                value['work'] = json.loads(work.read_text()) if work.exists() else None
                out = markers / (path.stem + '.out')
                value['events'] = ([json.loads(x) for x in out.read_text().splitlines()] if out.exists() else [])
                found[value.get('dispatch')] = value
        return found

    # The loopback page a turn fetches.
    class Page(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = b'loopback page for VELDO-0177'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Page)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        page_url = 'http://127.0.0.1:%d/page' % server.server_address[1]

        f = F.fixture(ROOT, base, H, load, 'workspace', 77, PRODUCTION)
        fixtures.append(f)
        mods = f['root'] / 'modules'
        CV = load('v177_conversation', mods / 'control_conversation.py')
        CS = load('v177_service', mods / 'control_service.py')
        CS.CV = CV
        D = load('v177_setup_dispatch', mods / 'control_factory_setup_dispatch.py')
        HO = load('v177_handoff', mods / 'control_agent_config_handoff.py')
        authority = f['authority']
        domain = authority.ids['domain_uuid']
        observations = []
        conversations = CV.Conversations(authority.S, authority.conn, domain=domain, principal='authority',
                                         signer='authority', sign=authority.journal_sign,
                                         state_root=f['root'] / 'state', observe=observations.append)
        f['conversations'] = conversations

        # THE KEYSTORE: a generated secret-tool first on PATH; one credential per server.
        keystore = base / 'keystore'
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
        # VELDO-0165: a login variable in the receiver's environment never reaches an engine.
        os.environ['ANTHROPIC_API_KEY'] = 'planted-receiver-login-v177'
        # THE MCP SERVER: a stdio fixture answering initialize and tools/list with one tool, `echo`.
        mcp_server = base / 'mcp-server.py'
        mcp_server.write_text('''import json, sys
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
        values = {}
        for server_id in ('alpha', 'beta'):
            digest = hashlib.sha256((domain + '/' + server_id + '-token').encode()).hexdigest()
            reference = 'keychain:veldo/' + digest
            values[server_id] = 'secret-%s-%s' % (server_id, os.urandom(6).hex())
            attributes = {'application': 'veldo', 'credential': 'veldo/' + digest}
            (keystore / ('item-' + hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest())
             ).write_text(values[server_id])
            authority.fixture('credential:' + digest, 'credential',
                              {'id': server_id + '-token', 'label': server_id, 'reference': reference,
                               'set_at': time.time(), 'set_by': 'owner'})
            definition = {'id': server_id, 'label': server_id, 'transport': 'stdio', 'command': sys.executable,
                          'arguments': [str(mcp_server)], 'url': None,
                          'environment': {'SERVER_TOKEN': {'reference': reference}}, 'headers': {},
                          'hosts': ['127.0.0.1'], 'read_only_tools': []}
            MC = CV.CFG.MC
            authority.fixture(MC.revision_id(domain, server_id, 1), MC.KIND, dict(definition, revision=1))
            authority.fixture(MC.head_id(domain, server_id), MC.HEAD_KIND, {'id': server_id, 'revision': 1})

        # THE ENGINES, pinned and qualified over the fixture's modules (VELDO-0174's), run LOCALLY: the receiver
        # starts each in its own containment group, as an installed host's adapters do (control_factory_setup
        # adapters: no transport wrapper).
        saved_fake, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved_fake
        config = json.loads(receiver.read_text())
        X = load('v177_codex', mods / 'control_engine_codex.py')
        adapters = config['adapters']
        adapters['claude_code'] = {'engine': 'claude_code', 'executable': adapters['claude_code']['executable'],
                                   'argv': []}
        codex_executable = adapters['codex']['executable']
        adapters['codex'] = {'engine': 'codex', 'executable': codex_executable,
                             'qualification': adapters['codex']['qualification'],
                             'argv': [codex_executable] + list(X.FLAGS)}
        systemd_run = shutil.which('systemd-run') or '/usr/bin/systemd-run'
        config['profile'] = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'),
                             'concurrency': 16, 'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400,
                             'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 0.4,
                             'kill_grace_seconds': 0.4, 'systemd_run': systemd_run}
        receiver.write_text(json.dumps(config))

        # THE ROLES: setup's assistant definitions (AC2), the Claude Code ones each selecting its own server.
        engines_record = json.loads((ROOT / '.veldo/runtime/engines.json').read_text())

        class SetupRefused(Exception):
            def __init__(self, code, detail=''):
                super().__init__(code)
                self.code = code
        model = 'fixture-codex-model'
        revisions = {}
        for role, setup_role, server_id in (('assistant', 'assistant', 'alpha'), ('assistant_two', 'assistant', 'beta'),
                                            ('assistant_codex', 'assistant_codex', None)):
            definition = dict(D.assistant_definition(setup_role, engines_record, {'codex': model}, SetupRefused),
                              role=role)
            if server_id:
                definition['mcp'] = [{'server': server_id, 'revision': 1, 'tools': 'all', 'load': 'always'}]
            saved = dict(definition, revision=1, previous=None)
            saved['digest'] = CV.CFG.digest(saved)
            authority.fixture('configuration:' + role, 'agent_configuration', saved)
            revisions[role] = saved
        roles = dict(f['roles'])
        roles['assistant_two'] = dict(roles['assistant'], capability_configuration={'role': 'assistant_two',
                                                                                    'revision': 1})
        authority.fixture('default-team:1', 'default_team_revision', {
            'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner', 'assertion_digest': 'sha256:fixture',
            'previous': None, 'digest': 'sha256:default-one'})
        # The Codex binary's declared tools for the role, as the qualified binary declares them (VELDO-0127).
        wanted = {'tools': [t['name'] for t in revisions['assistant_codex']['native_tools']], 'mcp_servers': [],
                  'model': model}
        (markers / 'codex-tools.json').write_text(json.dumps(HO.codex_expected_tools(wanted, {})))

        accounts_module = load('v177_accounts', mods / 'control_accounts.py')
        accounts = accounts_module.Accounts(authority.S, authority.conn, principal='owner', signer='authority',
                                            sign=authority.journal_sign)
        for provider, number in (('claude_code', 1), ('claude_code', 2), ('codex', 1)):
            account = 'account-%s-%d' % (provider, number)
            profile = f['root'] / ('profile-' + account)
            profile.mkdir(parents=True)
            accounts.register('account-register-' + account, account, provider, account, {f['host']: str(profile)},
                              concurrency=1, now=time.time())

        factory, lock, events = J.loop(f, CS, receiver)
        # Every launch the Line makes, kept after the Runner lets an ended one go, so its messages can be read.
        launched = []
        launch_prepared = factory.conversation.runner.launch_prepared

        def keeping(contract):
            launch = launch_prepared(contract)
            launched.append(launch)
            return launch
        factory.conversation.runner.launch_prepared = keeping

        def record_events(dispatch_id):
            """The engine events a run's execution record keeps, each payload parsed."""
            ER = load('v177_records', mods / 'control_execution_record.py')
            path = Path(ER.path(ER.directory(config), dispatch_id))
            found = []
            for line in (path.read_text().splitlines() if path.exists() else []):
                try:
                    found.append(json.loads(json.loads(line).get('payload') or 'null'))
                except ValueError:
                    pass
            return [e for e in found if isinstance(e, dict)]

        def used(dispatch_id):
            """{tool name: its result, or None when the record's redaction left its line unreadable} of the tool
            calls a run's record keeps."""
            kept = record_events(dispatch_id)
            calls = {c['id']: c['name'] for e in kept if e.get('type') == 'assistant'
                     for c in e['message'].get('content') or [] if c.get('type') == 'tool_use'}
            results = {calls.get(r.get('tool_use_id')): r.get('content') for e in kept if e.get('type') == 'user'
                       for r in e['message'].get('content') or [] if r.get('type') == 'tool_result'}
            return dict({name: None for name in calls.values()}, **results)

        def turn_of(identity, text):
            return conversations.message(identity, identity + '-' + text, 'sha256:' + identity + text, owner='owner')

        def ended(identity, count=1):
            saved = conversations.turns(identity)
            return len(saved) >= count and saved[count - 1].get('state') == 'ended'

        # ---- AC1: two conversations' turns at once ---------------------------------------------------------------
        (markers / 'scenario.json').write_text(json.dumps({'mode': 'work', 'url': page_url}))
        first = conversations.open('first', owner='owner', role='assistant', intake_digest='sha256:first')
        second = conversations.open('second', owner='owner', role='assistant_two', intake_digest='sha256:second')
        for record in (first, second):
            workspace = Path(record['directory']) / 'workspace'
            check('AC1/workspace-made', 'the open command made the workspace under the conversation\'s directory, 0700',
                  workspace.is_dir() and oct(workspace.stat().st_mode & 0o777) == '0o700'
                  and CV.workspace_of(record) == str(workspace))
        check('AC1/workspace-made', 'each conversation\'s workspace is its own',
              CV.workspace_of(first) != CV.workspace_of(second))
        turn_of('first', 'one')
        turn_of('second', 'one')
        J.pass_(factory)
        both = J.eventually(lambda: len([v for v in observed(markers).values() if v.get('packet')]) >= 2, 30)
        runs = observed(markers)
        by_conversation = {}
        for dispatch, value in runs.items():
            for identity in ('first', 'second'):
                if dispatch and ('/' + identity + '/') in dispatch:
                    by_conversation[identity] = value
        a, b = by_conversation.get('first') or {}, by_conversation.get('second') or {}
        check('AC1/isolation', 'both turns ran at once (each engine started before either was released)',
              both and a and b)
        (markers / 'release').touch()
        F.drive(factory, lambda: ended('first') and ended('second'), 40)
        workspaces = {'first': CV.workspace_of(conversations.read('first')),
                      'second': CV.workspace_of(conversations.read('second'))}
        print('  VELDO-0177 AC1 working directories:', a.get('cwd'), b.get('cwd'), 'outcomes:',
              [t.get('outcome') for t in conversations.turns('first') + conversations.turns('second')])
        check('AC1/isolation', 'each engine\'s working directory is its own conversation\'s workspace',
              a.get('cwd') == workspaces['first'] and b.get('cwd') == workspaces['second'])
        check('AC1/isolation', 'the two working directories differ and neither names the other\'s',
              a.get('cwd') and b.get('cwd') and a['cwd'] != b['cwd']
              and workspaces['second'] not in json.dumps(a) and workspaces['first'] not in json.dumps(b))
        check('AC1/isolation', 'the two worker groups differ and neither names the other\'s',
              a.get('cgroup') and b.get('cgroup') and a['cgroup'] != b['cgroup']
              and a['cgroup'].strip() not in json.dumps(b) and b['cgroup'].strip() not in json.dumps(a))
        check('AC1/isolation', 'the two credential files differ and neither names the other\'s',
              a.get('mcp_path') and b.get('mcp_path') and a['mcp_path'] != b['mcp_path']
              and a['mcp_path'] not in json.dumps(b) and b['mcp_path'] not in json.dumps(a))
        check('AC1/isolation', 'the turns ended completed',
              [t.get('outcome') for t in conversations.turns('first') + conversations.turns('second')]
              == ['completed', 'completed'])
        for identity, value in (('first', a), ('second', b)):
            cgroup = (value.get('cgroup') or '').strip()
            check('AC1/contained', '%s: the engine runs in a transient scope of this run\'s worker slice [%s]'
                  % (identity, cgroup), slice_name in cgroup and '.scope' in cgroup)
        check('AC1/contained', 'the turns launched through the conversation Line\'s Runner with the profile\'s caps',
              factory.conversation.runner.profile == config['profile']
              and all(launch.group and launch.group.get('cgroup')
                      for launch in factory.conversation.runner.launches.values()))
        own = {'first': ('alpha', 'beta'), 'second': ('beta', 'alpha')}
        for identity, value in (('first', a), ('second', b)):
            mine, theirs = own[identity]
            text = value.get('mcp_text') or ''
            check('AC1/credentials', '%s: its credential file holds exactly its role\'s server and credential'
                  % identity, mine in json.loads(text or '{}').get('mcpServers', {})
                  and values[mine] in text and theirs not in json.loads(text or '{}').get('mcpServers', {})
                  and values[theirs] not in text)
            run_root = Path(J.load('v177_launch_paths', mods / 'control_launch.py').runs_root(config))
            check('AC1/credentials', '%s: the credential file is in its own run\'s private directory, removed with it'
                  % identity, str(value.get('mcp_path') or '').startswith(str(run_root) + os.sep)
                  and not Path(value.get('mcp_path') or '/nonexistent/x').exists())
            ER = load('v177_records', mods / 'control_execution_record.py')
            record_path = Path(ER.path(ER.directory(config), value.get('dispatch')))
            kept = record_path.read_text() if record_path.exists() else ''
            check('AC1/credentials', '%s: the value the engine printed is redacted from its execution record'
                  % identity, bool(kept) and 'credential ' in kept and values[mine] not in kept
                  and values[theirs] not in kept)
        for identity, value in (('first', a), ('second', b)):
            argv = value.get('argv') or []
            check('AC1/launch-guards', '%s: VELDO-0165\'s strip: the receiver\'s login variable is not in the engine'
                  % identity, 'ANTHROPIC_API_KEY' not in (value.get('environment') or []))
            check('AC1/launch-guards', '%s: VELDO-0173\'s switch-off: every registry tool outside the role is '
                  'disallowed' % identity, any(x.startswith('--disallowedTools=') for x in argv)
                  and 'AskUserQuestion' in next((x for x in argv if x.startswith('--disallowedTools=')), ''))
            check('AC1/launch-guards', '%s: VELDO-0155\'s baseline: the generated MCP configuration and strict MCP'
                  % identity, '--mcp-config' in argv and '--strict-mcp-config' in argv)

        # A contract naming another conversation's workspace: prepared by the Runner, refused by the receiver.
        L = CS.L
        original = L._organ

        def swapped(name):
            module = original(name)
            if name == 'control_conversation':
                module.workspace_of = lambda record, _w=workspaces['first']: _w
            return module
        before_runs = set(observed(markers))
        turn_of('second', 'two')
        L._organ = swapped
        try:
            J.pass_(factory)
        finally:
            L._organ = original
        F.drive(factory, lambda: ended('second', 2), 30)
        refused = conversations.turns('second')[1]
        check('AC1/workspace-refused', 'a turn whose contract names another conversation\'s workspace is refused '
              'by name [%s]' % refused.get('outcome'),
              refused.get('outcome') == 'binding_mismatch:conversation_workspace')
        record = factory.conversation.dispatches.record(refused.get('dispatch_id')) or {}
        check('AC1/workspace-refused', 'before anything is spawned: the dispatch is refused, never accepted, and no '
              'engine ran', record.get('state') == 'refused' and set(observed(markers)) == before_runs)
        status = conversations.status()
        check('AC1/observability', 'the turns refused for a workspace mismatch are counted [%s]'
              % status.get('workspace_refusals'), status.get('workspace_refusals') == 1)
        turn_events = [m for launch in launched for m in launch.messages if m.get('event') == 'conversation_turn']
        joined = {e['conversation']: e for e in turn_events}
        check('AC1/observability', 'each turn\'s launch names its conversation, workspace, worker group, role '
              'revision, tools, servers and credential references [%s]' % sorted(joined),
              set(joined) == {'first', 'second'}
              and all(joined[i]['workspace'] == workspaces[i] and (joined[i]['group'] or {}).get('cgroup')
                      and joined[i]['role_revision']['revision'] == 1 and joined[i]['tools']
                      for i in joined)
              and joined['first']['servers'] == ['alpha'] and joined['second']['servers'] == ['beta']
              and joined['first']['credentials'] == ['alpha-token']
              and joined['second']['credentials'] == ['beta-token'])
        check('AC1/observability', 'never a credential value in any turn event or conversation observation',
              all(v not in json.dumps(turn_events) + json.dumps(observations) for v in values.values()))
        check('AC1/observability', 'turns are counted by role revision [%s]' % status.get('turns_by_role_revision'),
              status.get('turns_by_role_revision', {}).get('1', 0) >= 2)

        # ---- AC2: the offered tools, the Codex launch and a working turn's record -------------------------------
        for identity, value in (('first', a), ('second', b)):
            role = 'assistant' if identity == 'first' else 'assistant_two'
            granted = sorted(t['name'] for t in revisions[role]['native_tools'] if t['load'] == 'always')
            init = next((e for e in value.get('events') or [] if e.get('subtype') == 'init'), {})
            print('  VELDO-0177 AC2 %s init tools: %s' % (identity, init.get('tools')))
            check('AC2/offered-tools', '%s: WebFetch and WebSearch are in the init event' % identity,
                  {'WebFetch', 'WebSearch'} <= set(init.get('tools') or []))
            granted = sorted(granted + ['mcp__%s__echo' % m['server'] for m in revisions[role]['mcp']])
            check('AC2/offered-tools', '%s: the init event\'s tools are exactly the revision\'s, its server\'s '
                  'tool among them' % identity, sorted(init.get('tools') or []) == granted)
            check('AC2/offered-tools', '%s: the init event\'s servers are exactly the revision\'s' % identity,
                  sorted(s['name'] for s in init.get('mcp_servers') or [])
                  == sorted(m['server'] for m in revisions[role]['mcp']))
        check('AC2/offered-tools', 'setup\'s assistant grant: the pinned version\'s in-run tools with WebSearch and '
              'WebFetch, all always', set(t['name'] for t in revisions['assistant']['native_tools'])
              >= {'Bash', 'Edit', 'Read', 'WebFetch', 'WebSearch'}
              and all(t['load'] == 'always' for t in revisions['assistant']['native_tools']))
        kept = used(a.get('dispatch'))
        workspace = Path(workspaces['first'])
        print('  VELDO-0177 AC2 the turn record\'s tool calls:', sorted(k for k in kept if k))
        check('AC2/turn-record', 'the turn edited a file in its workspace, and its record keeps the Edit call',
              (workspace / 'notes.txt').read_text() == 'drafted by the turn\n' and kept.get('Edit') == 'edited notes.txt')
        # The command's output names the workspace path, which the record's entropy redaction rewrites.
        check('AC2/turn-record', 'the turn ran a command in its workspace, and its record keeps the Bash call',
              (workspace / 'ran.txt').read_text() == 'ran\n' and 'Bash' in kept
              and (observed(markers).get(a.get('dispatch'), {}).get('work') or {}).get('Bash')
              == 'ran\n' + str(workspace) + '\n')
        check('AC2/turn-record', 'the turn fetched the loopback page, and its record keeps the WebFetch call',
              kept.get('WebFetch') == 'loopback page for VELDO-0177')

        (markers / 'release').unlink()
        (markers / 'scenario.json').write_text(json.dumps({'mode': 'none'}))
        before_runs = set(observed(markers))
        conversations.open('codexed', owner='owner', role='assistant_codex', intake_digest='sha256:codexed')
        turn_of('codexed', 'one')
        J.pass_(factory)
        J.eventually(lambda: len(set(observed(markers)) - before_runs) >= 1, 30)
        (markers / 'release').touch()
        F.drive(factory, lambda: ended('codexed'), 40)
        codex_run = next((v for k, v in observed(markers).items() if k not in before_runs), {})
        cfg = codex_run.get('config') or {}
        print('  VELDO-0177 AC2 codex outcome:', [t.get('outcome') for t in conversations.turns('codexed')])
        check('AC2/codex-launch', 'the Codex turn ran in its own workspace and completed',
              codex_run.get('cwd') == CV.workspace_of(conversations.read('codexed'))
              and [t.get('outcome') for t in conversations.turns('codexed')] == ['completed'])
        check('AC2/codex-launch', 'its launch: the workspace-write sandbox with network access, live web search '
              '[%s %s %s]' % (cfg.get('sandbox_mode'), cfg.get('sandbox_workspace_write'), cfg.get('web_search')),
              cfg.get('sandbox_mode') == 'workspace-write'
              and cfg.get('sandbox_workspace_write') == {'network_access': True} and cfg.get('web_search') == 'live')
        check('AC2/codex-launch', 'its shell, edit and plan tools on, exactly the revision\'s',
              sorted(codex_run.get('tools') or []) == sorted(HO.codex_expected_tools(wanted, {})))

        # ---- AC3: attach a fixture project, read its history, commit in the clone, try to push ------------------
        project_repo = base / 'project-repository'
        project_repo.mkdir()
        git('init', '-q', '-b', 'main', str(project_repo))
        for number in (1, 2, 3):
            (project_repo / 'file.txt').write_text('revision %d\n' % number)
            git('-C', str(project_repo), 'add', 'file.txt')
            git('-C', str(project_repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-qm', 'project commit %d' % number)
        repository_uuid = 'fixture-project-repository'
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](
            mods, authority.conn, domain, {repository_uuid: str(project_repo)})
        authority.S.bind_repositories(authority.conn, domain, {repository_uuid: str(project_repo)})
        authority.fixture('project:fixture-project', 'project',
                          {'name': 'fixture-project', 'owner': 'owner', 'execution_repository': repository_uuid})
        authority.fixture('project:foreign-project', 'project',
                          {'name': 'foreign-project', 'owner': 'steward', 'execution_repository': repository_uuid})
        # Another owner's project whose execution repository is bound nowhere here (VELDO-0177 fix round 2, F1).
        authority.fixture('project:foreign-unbound', 'project',
                          {'name': 'foreign-unbound', 'owner': 'steward', 'execution_repository': 'never-bound-here'})
        owner_roles = CV._row(authority.conn, 'owner')['data']['roles']
        authority.admin('steward', 'change_roles', {'principal': 'owner', 'roles': owner_roles,
                                                    'scope': ['activation-repository', 'fixture-project',
                                                              'foreign-project', 'foreign-unbound']})
        service = CS.Service(J.service_config(f, CS), authority.conn)
        service._conversations = conversations

        def owner_command(operation, parameters, who='owner'):
            command = dict(authority.ids, operation=operation, parameters=parameters, principal=who,
                           command_id=authority.next_id('v177'), nonce=authority.next_id('v177-nonce'))
            packet = {'command': command, 'signature': authority.sign_as(who, authority.S.canonical_bytes(command))}
            return service.conversation_command(packet, command, authority.ids['repository_uuid'], {})
        trunk = git('-C', str(project_repo), 'rev-parse', 'HEAD').strip()
        project_refs = git('-C', str(project_repo), 'for-each-ref')
        opened = owner_command(CV.OPEN, {'conversation': 'attached'})
        attached = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 1, 'project': 'fixture-project'})
        record = (attached.get('conversation') or {})
        entry = (record.get('attachments') or [{}])[-1]
        clone = Path(entry.get('clone') or '/nonexistent/v177')
        check('AC3/attach-clone', 'the signed attach_project on the current version is accepted [%s]'
              % attached.get('reason'), opened.get('ok') and attached.get('ok') and record.get('version') == 2)
        check('AC3/attach-clone', 'the clone is under the workspace\'s projects/<project> directory, recorded with '
              'the trunk commit', str(clone).startswith(os.path.join(CV.workspace_of(record), 'projects',
                                                                     'fixture-project') + os.sep)
              and entry.get('commit') == trunk and entry.get('project') == 'fixture-project')
        clone_log = git('-C', str(clone), 'log', '--format=%s', check=False).split('\n') if clone.is_dir() else []
        check('AC3/attach-clone', 'the clone is at the trunk commit with the full history [%s]' % clone_log[:3],
              clone.is_dir() and git('-C', str(clone), 'rev-parse', 'HEAD').strip() == trunk
              and clone_log[:3] == ['project commit 3', 'project commit 2', 'project commit 1']
              and git('-C', str(clone), 'rev-parse', '--is-shallow-repository').strip() == 'false')
        check('AC3/attach-clone', 'an isolated clone: its own object store, no alternate, no worktree link',
              clone.is_dir() and (clone / '.git').is_dir()
              and not (clone / '.git/objects/info/alternates').exists()
              and str(project_repo) not in (clone / '.git/config').read_text())
        foreign = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 2, 'project': 'foreign-project'})
        check('AC3/scope', 'a project outside the owner\'s own is refused by name, and nothing is cloned [%s]'
              % foreign.get('reason'), foreign == {'ok': False, 'reason': 'missing_authority:project'}
              and not (Path(CV.workspace_of(record)) / 'projects' / 'foreign-project').exists()
              and conversations.read('attached')['version'] == 2)
        # Observed, not inferred from the refusal: every repository lookup and trunk read the attach makes is
        # recorded while another owner's project with an unbound repository is attached.
        reads, real_source, real_bound = [], CV.project_source, CV.S.bound_repository

        def source_seen(conn, domain_, project):
            reads.append(('project_source', project))
            return real_source(conn, domain_, project)

        def bound_seen(conn, domain_, repository):
            reads.append(('bound_repository', repository))
            return real_bound(conn, domain_, repository)
        CV.project_source, CV.S.bound_repository = source_seen, bound_seen
        try:
            unbound = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 2,
                                                'project': 'foreign-unbound'})
        finally:
            CV.project_source, CV.S.bound_repository = real_source, real_bound
        check('AC3/scope', 'another owner\'s project with an unbound repository is refused by name, its repository '
              'never read [%s %s]' % (unbound.get('reason'), reads),
              unbound == {'ok': False, 'reason': 'missing_authority:project'} and reads == []
              and not (Path(CV.workspace_of(record)) / 'projects' / 'foreign-unbound').exists()
              and conversations.read('attached')['version'] == 2)
        authority.admin('steward', 'change_roles', {'principal': 'owner', 'roles': owner_roles,
                                                    'scope': ['activation-repository']})
        unscoped = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 2, 'project': 'fixture-project'})
        authority.admin('steward', 'change_roles', {'principal': 'owner', 'roles': owner_roles,
                                                    'scope': ['activation-repository', 'fixture-project']})
        check('AC3/scope', 'a project the owner\'s scope does not cover is refused by name [%s]'
              % unscoped.get('reason'), unscoped == {'ok': False, 'reason': 'missing_authority:project'}
              and len(list((Path(CV.workspace_of(record)) / 'projects' / 'fixture-project').iterdir())) == 1)
        stale = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 1, 'project': 'fixture-project'})
        check('AC3/scope', 'an attach on a stale version is refused [%s]' % stale.get('reason'),
              stale.get('reason') == 'stale_version')

        (markers / 'release').unlink()
        (markers / 'scenario.json').write_text(json.dumps({'mode': 'project', 'clone': str(clone)}))
        before_runs = set(observed(markers))
        turn_of('attached', 'one')
        J.pass_(factory)
        J.eventually(lambda: len(set(observed(markers)) - before_runs) >= 1, 30)
        (markers / 'release').touch()
        F.drive(factory, lambda: ended('attached'), 40)
        project_run = next((v for k, v in observed(markers).items() if k not in before_runs), {})
        did = project_run.get('work') or {}
        check('AC3/no-publication', 'the turn read the clone\'s history and committed in it [%s]' % did.get('commit'),
              'project commit 1' in (did.get('log') or '') and did.get('commit') == 0
              and git('-C', str(clone), 'log', '-1', '--format=%s').strip() == 'turn change')
        check('AC3/no-publication', 'its push failed and the fixture remote\'s refs are unchanged [%s]'
              % did.get('push'), did.get('push') not in (None, 0)
              and git('-C', str(project_repo), 'for-each-ref') == project_refs
              and git('-C', str(project_repo), 'rev-parse', 'HEAD').strip() == trunk)
        config_text = (clone / '.git/config').read_text()
        check('AC3/no-publication', 'the clone has no remote, no Git identity and no credential helper',
              git('-C', str(clone), 'remote').strip() == '' and '[user]' not in config_text
              and '[remote' not in config_text and 'credential' not in config_text and 'pushurl' not in config_text)

        (project_repo / 'file.txt').write_text('revision 4\n')
        git('-C', str(project_repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qam', 'project commit 4')
        newer = git('-C', str(project_repo), 'rev-parse', 'HEAD').strip()
        again = owner_command(CV.ATTACH, {'conversation': 'attached', 'version': 2, 'project': 'fixture-project'})
        listed = (again.get('conversation') or {}).get('attachments') or []
        second_clone = Path((listed[-1] if listed else {}).get('clone') or '/nonexistent/v177')
        check('AC3/attach-again', 'attaching again takes a new clone beside the old one, at the newer trunk commit',
              again.get('ok') and len(listed) == 2 and second_clone.parent == clone.parent and second_clone != clone
              and git('-C', str(second_clone), 'rev-parse', 'HEAD').strip() == newer
              and git('-C', str(clone), 'log', '-1', '--format=%s').strip() == 'turn change')
        attaches = [o for o in observations if o.get('operation') == 'project_attach']
        check('AC3/observability', 'each attach is recorded with its project, trunk commit and clone path [%s]'
              % [(o.get('project'), o.get('outcome')) for o in attaches],
              [(o.get('project'), o.get('commit'), o.get('clone')) for o in attaches]
              == [('fixture-project', trunk, str(clone)), ('fixture-project', newer, str(second_clone))])
        check('AC3/observability', 'project attaches are counted [%s]' % conversations.status().get('project_attaches'),
              conversations.status().get('project_attaches') == 2)
        project_turn = [m for launch in launched for m in launch.messages
                        if m.get('event') == 'conversation_turn' and m.get('conversation') == 'attached']
        check('AC3/observability', 'the turn\'s launch is joined to the clone of its attached project',
              len(project_turn) == 1 and project_turn[0]['attached']
              == [{'project': 'fixture-project', 'commit': trunk, 'clone': str(clone)}])
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        if factory is not None:
            try:
                for launch in list(factory.conversation.runner.launches.values()):
                    launch.stop('requested')
            except Exception:  # noqa: BLE001
                pass
        if lock is not None:
            close = getattr(lock, 'close', None)
            if close:
                close()
        for value in fixtures:
            value['authority'].conn.close()
        if server is not None:
            server.shutdown()
        subprocess.run(['systemctl', '--user', 'stop', slice_name], capture_output=True, timeout=30)
        if saved_path is None:
            os.environ.pop('PATH', None)
        else:
            os.environ['PATH'] = saved_path
        if saved_key is None:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        else:
            os.environ['ANTHROPIC_API_KEY'] = saved_key
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0177 detail:', row, '; '.join(failed))
        expect('VELDO-0177 ' + row, bool(rows[row]) and not failed)


_v177_suite()
