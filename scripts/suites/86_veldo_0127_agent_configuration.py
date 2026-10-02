"""Accepted role revisions through both production adapters, Runner and receiver."""
def _v127_suite():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import sys
    import tempfile

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    PRODUCTION = {
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    EVIDENCE_PATH = ROOT / "." / "proof/VELDO-0127/evidence.py"
    LIVE_PATH = ROOT / "." / "proof/VELDO-0127/live.py"
    ROWS = ('revision/history', 'handoff/claude', 'handoff/codex', 'dispatch/binding', 'dispatch/refusal',
            'launch/push', 'launch/unlisted', 'launch/instructions', 'live/claude', 'live/codex', 'format/fake-lines',
            'review/skill-commit', 'review/skill-git-boundary', 'review/probe-terminal', 'review/init-bound', 'review/slash-collision',
            'review/marker-debug', 'review/codex-tools', 'review/codex-mode', 'review/codex-capture',
            'catalog/fields', 'catalog/grants', 'catalog/integrity', 'wire/normalization', 'wire/resources', 'wire/no-server')
    rows = {name: [] for name in ROWS}
    def check(row, label, condition):
        rows[row].append((label, bool(condition)))
    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:
            return None, getattr(error, 'code', type(error).__name__)
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    ff = load('v127_formats', TREE / 'proof/VELDO-0172/fake_formats.py')
    conform_formats = load('v127_conform', TREE / 'proof/VELDO-0172/compare_formats.py')
    live_step = ff.live_step
    base = Path(tempfile.mkdtemp(prefix='v127-', dir='/run/user/' + str(os.getuid())))
    markers = base / 'markers'
    markers.mkdir()
    f = None
    fake_capture = ([], [])
    fake = '''#!PYTHON -B
import json, os, sys, subprocess, tomllib
from pathlib import Path
P = '-' * 2
markers = Path(MARKERS)
engine = ENGINE
args = sys.argv[1:]
def value(name, default=None):
    for i, arg in enumerate(args):
        if arg == P + name: return args[i+1]
        if arg.startswith(P + name + '='): return arg.split('=', 1)[1]
    return default
def emit(event):
    event = complete_event(event)
    line = json.dumps(event)
    with (markers / (str(os.getpid()) + '.out')).open('a') as out: out.write(line + chr(10))
    print(line, flush=True)
config = {}
for i, arg in enumerate(args):
    if arg == '-c':
        parsed = tomllib.loads(args[i+1])
        def merge(a,b):
            for k,v in b.items():
                if isinstance(v,dict): merge(a.setdefault(k,{}),v)
                else: a[k]=v
        merge(config, parsed)
if args[:3] == ['debug', 'models', P + 'bundled']:
    print(Path(CATALOG_FIXTURE).read_text())
    sys.exit(0)
if args[:2] == ['features', 'list']:
    print(json.loads(Path(CATALOG_FIXTURE).with_name('features-fixture.json').read_text())['stdout'], end='')
    sys.exit(0)
if args[:2] == ['login', 'status']:
    print('Logged in using ChatGPT', file=sys.stderr)
    sys.exit(0)
if config.get('model_catalog_json'):
    # As the real Codex: every configuration load, `mcp list` and `mcp get` included, reads model_catalog_json
    # and refuses to start when the file is missing or names no model.
    catalog_path = Path(config['model_catalog_json'])
    if not catalog_path.is_file() or not json.loads(catalog_path.read_text()).get('models'):
        print('Error: failed to load configuration', file=sys.stderr)
        sys.exit(1)
if 'mcp' in args:
    # As Codex 0.154: `mcp` takes no exec option, reads CODEX_HOME's config.toml under its -c overrides, and
    # lists servers without their tools, which `mcp get` prints.
    if P + 'ignore-user-config' in args:
        print("error: unexpected argument '" + P + "ignore-user-config' found", file=sys.stderr)
        sys.exit(2)
    home = Path(os.environ.get('CODEX_HOME') or Path(os.environ['HOME']) / '.codex')
    servers = tomllib.loads((home / 'config.toml').read_text()).get('mcp_servers', {}) if (home / 'config.toml').is_file() else {}
    for name, entry in config.get('mcp_servers', {}).items():
        servers.setdefault(name, {}).update(entry)
    rest = args[args.index('mcp') + 1:]
    if rest[:1] == ['list']:
        print(json.dumps([{'name': k, 'enabled': True, 'transport': {'type': 'stdio', 'command': v.get('command')}}
                          for k, v in servers.items()]))
        sys.exit(0)
    if rest[:1] == ['get'] and rest[1] in servers:
        entry = servers[rest[1]]
        print(json.dumps({'name': rest[1], 'enabled': True, 'transport': {'type': 'stdio', 'command': entry.get('command')},
                          'enabled_tools': entry.get('enabled_tools'), 'disabled_tools': None}))
        sys.exit(0)
    sys.exit(1)
def server_tools(entry):
    env = {'PATH': os.environ['PATH']}
    env.update(entry.get('env', {}))
    env.update({k: os.environ[k] for k in entry.get('env_vars',[])})
    requests = [{'jsonrpc':'2.0','id':1,'method':'initialize'}, {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
    p = subprocess.run([entry['command']] + entry.get('args',[]), input=''.join(json.dumps(r)+chr(10) for r in requests),
                       capture_output=True, text=True, env=env, timeout=10)
    answer = [json.loads(x) for x in p.stdout.splitlines()]
    return [t['name'] for a in answer if a.get('id') == 2 for t in a.get('result',{}).get('tools',[])]
own = {'argv':args, 'dispatch':os.environ.get('VELDO_DISPATCH_ID'), 'engine':engine}
if engine == 'claude':
    # As Claude Code 2.1.281: its built-in plugins, bundled skills, built-in skills and built-in commands
    # load unless the generated settings turn them off; `--disable-slash-commands` withdraws every skill
    # and the Skill tool; the init event comes only when a first user message arrives, and a message
    # with shouldQuery false draws it and a zero-turn result without any turn.
    mcp_path = value('mcp-config')
    settings = json.loads(Path(value('settings')).read_text()) if value('settings') else {}
    servers = json.loads(Path(mcp_path).read_text())['mcpServers'] if mcp_path else {}
    tools = [n for n in value('tools','Read').split(',') if n]
    denied = value('disallowedTools','').split(',')
    for name,entry in servers.items(): tools += ['mcp__'+name+'__'+n for n in server_tools(entry)]
    tools = [n for n in tools if n not in denied]
    no_skills = P + 'disable-slash-commands' in args
    if no_skills: tools = [n for n in tools if n != 'Skill']
    plugin = value('plugin-dir')
    skills = ['veldo-role:' + p.parent.name for p in Path(plugin).glob('skills/*/SKILL.md')] if plugin else []
    overrides = settings.get('skillOverrides') or {}
    engine_skills = ([] if settings.get('disableBundledSkills') else ['deep-research', 'code-review']) + [
        n for n in ('design', 'doctor') if overrides.get(n) != 'off']
    skills = [] if no_skills else skills + engine_skills
    commands = [] if no_skills else ['clear', 'compact', 'init']
    plugins = [{'name':'veldo-role','path':plugin,'source':'veldo-role@inline'}] if plugin else []
    plugins += [{'name':n.split('@')[0],'path':'builtin','source':n} for n in ('agents-md@builtin', 'telemetry@builtin')
                if (settings.get('enabledPlugins') or {}).get(n) is not False]
    init = complete_event({'type':'system','subtype':'init','tools':tools,'apiKeySource':'none',
                          'mcp_servers':[{'name':n,'status':'connected'} for n in servers],
                          'skills':skills,'slash_commands':skills + commands,'plugins':plugins,
                          'model':value('model','fixture-model')})
    # The launch set as computed, an empty list included (the format completion fills empty lists).
    init.update(tools=tools, mcp_servers=[{'name':n,'status':'connected'} for n in servers], skills=skills,
                slash_commands=skills + commands, plugins=plugins)
    fault = (markers / 'fault').read_text() if (markers / 'fault').exists() else ''
    if fault == 'slash': init['slash_commands'].append('collision')
    if fault == 'skill': init['skills'].append('unlisted')
    if fault == 'tool': init['tools'].append('UnlistedTool')
    if fault == 'missing': init['tools'] = [t for t in init['tools'] if t != 'mcp__jira__jira_search']
    own['init'] = init
    own['instructions'] = Path(value('append-system-prompt-file')).read_text() if value('append-system-prompt-file') else ''
    if value('debug-file'):
        Path(value('debug-file')).write_text('Role instruction discovery disabled' + chr(10))
    (markers / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
    reported = False
    received = []
    for raw in sys.stdin:
        message = json.loads(raw)
        received.append({k: message.get(k) for k in ('type', 'shouldQuery')} if message.get('type') == 'user' else
                        {'type': message.get('type')})
        if message.get('type') == 'user':
            received[-1]['content'] = message['message']['content']
        (markers / (str(os.getpid()) + '.input')).write_text(json.dumps(received))
        if message.get('type') == 'control_request':
            listed = [{'name': n, 'description': n, 'argumentHint': ''} for n in skills if n.startswith('veldo-role:')]
            listed += [{'name': n, 'description': n, 'argumentHint': '', 'builtin': True}
                       for n in engine_skills + commands if not no_skills]
            if fault == 'slash': listed += [{'name':'collision','builtin':True}, {'name':'collision','builtin':False}]
            emit({'type':'control_response','response':{'subtype':'success','request_id':message['request_id'],
                  'response':{'account':{'subscriptionType':'Claude Team','apiProvider':'firstParty'},'pid':os.getpid(),
                              'commands': listed}}})
        elif message.get('type') == 'user':
            if fault == 'no-init': continue
            if not reported:
                reported = True
                with (markers / (str(os.getpid()) + '.out')).open('a') as out: out.write(json.dumps(init) + chr(10))
                print(json.dumps(init), flush=True)
            if message.get('shouldQuery') is False:
                if fault == 'probe-exit': os.close(0)
                emit({'type':'result','subtype':'success','is_error':False,'num_turns':0,'result':'',
                      'usage':{'input_tokens':0,'output_tokens':0}})
                if fault == 'probe-exit': sys.exit(0)
                continue
            packet = json.loads(message['message']['content'])
            break
    else: sys.exit(0)
else:
    own['configuration'] = config
    import importlib.util
    spec = importlib.util.spec_from_file_location('wire_fixture', WIRE_FIXTURE)
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    if config.get('model_provider') in ('loopback', 'role_observation'):
        sys.exit(wire.forward(args, config))
    own['mcp_tools'] = {n: [t for t in server_tools(e) if t in e.get('enabled_tools',[])]
                       for n,e in config.get('mcp_servers',{}).items()}
    # The stream-format probe has no bound role or generated model catalog.
    own['model_catalog'] = json.loads(Path(config['model_catalog_json']).read_text()) if config.get('model_catalog_json') else {}
    own['wire'] = wire.capture(config) if config.get('model_catalog_json') else {}
    (markers / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
    packet = json.loads(sys.stdin.read())
    if Path('.git').exists():
        Path('delivered.txt').write_text('worker output')
        subprocess.run(['git','add','-A'], check=True, capture_output=True)
        subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                        '-c','commit.gpgsign=false','commit',P+'allow-empty','-qm','Worker delivery'], check=True, capture_output=True)
        own['committed_paths'] = subprocess.run(['git','ls-tree','-r',P+'name-only','HEAD'],
                                               check=True,capture_output=True,text=True).stdout.splitlines()
        (markers / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
(markers / (str(os.getpid()) + '.turn')).write_text('first turn')
for step in (packet.get('payload') or {}).get('script',[]):
    if 'line' in step: emit(step['line'])
'''
    fake = ff.embed(fake.replace('PYTHON', sys.executable))
    def fake_engine(name):
        return fake.replace('WIRE_FIXTURE', repr(str(TREE / 'proof/VELDO-0127/wire_fixture.py'))).replace('CATALOG_FIXTURE', repr(str(TREE / 'proof/VELDO-0127/catalog-fixture.json'))).replace('MARKERS', repr(str(markers))).replace('ENGINE', repr(name))
    @live_step
    def c_msg(mid, inp, out):
        return {'line': {'type': 'assistant', 'message': {'id': mid, 'usage': {'input_tokens': inp, 'output_tokens': out}}}}
    @live_step
    def c_rate(status, reset):
        return {'line': {'type': 'rate_limit_event', 'rate_limit_info': {'status': status, 'resetsAt': int(reset)}}}
    @live_step
    def c_result(inp, out, turns=1):
        return {'line': {'type': 'result', 'subtype': 'success', 'num_turns': turns,
                         'usage': {'input_tokens': inp, 'output_tokens': out}}}
    @live_step
    def x_thread():
        return {'line': {'type': 'thread.started'}}
    @live_step
    def x_started():
        return {'line': {'type': 'turn.started'}}
    @live_step
    def x_message():
        return {'line': {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'done'}}}
    @live_step
    def x_done(inp, out):
        return {'line': {'type': 'turn.completed', 'usage': {'input_tokens': inp, 'output_tokens': out}}}
    try:
        if not all(Path(p).is_file() for p in PRODUCTION.values()):
            for row in ROWS:
                check(row, 'accepted role handoff is absent in this tree', False)
        else:
            fixture = load('v127_factory', TREE / 'proof/VELDO-0127/factory.py')
            # A fake run ends in a second; a run held past this deadline (a prompt never released) is stopped
            # by it and reds its row.
            f = fixture.factory(ROOT, base, PRODUCTION, fake_engine, deadline_seconds=30)
            L = f.L
            C = f.config_api
            def payload(engine):
                script = [c_msg('role-message', 30, 3), c_rate('allowed', 2000000000), c_result(30, 4)] if engine == 'claude' else [
                    x_thread(), x_started(), x_message(), x_done(30, 4)]
                return {'task': 'Read the role instructions', 'script': script}
            claude_blocked = False
            def run(engine, unit, configuration):
                if engine == 'claude' and claude_blocked:
                    return None, {}, {}, 'configuration_stop:init_missing'
                contract, error = attempt(lambda: f.prepare(engine, unit, configuration, payload(engine)))
                if contract is None:
                    return None, {}, {}, error
                work, error = attempt(lambda: f.launch(engine, contract))
                record, error = attempt(lambda: f.finish(engine, work)) if work else ({}, error)
                own = next((json.loads(p.read_text()) for p in markers.glob('*.json')
                            if json.loads(p.read_text()).get('dispatch') == contract['dispatch_id']), {})
                return work, record or {}, own, error
            a = f.save(f.role('claude'))
            before = copy.deepcopy(a)
            b = f.save(dict(f.role('claude'), settings={'model': 'fixture-model'}), 1)
            old = C.read(f.writer, f.DOMAIN, f.REPOSITORY, 'claude', 1)
            _, stale = attempt(lambda: f.save(f.role('claude'), 0))
            _, unauthorized = attempt(lambda: f.save(f.role('claude'), 2, 'runner'))
            embedded = f.role('claude'); embedded['mcp'][0]['environment'] = {}
            _, invalid = attempt(lambda: f.save(embedded, 2))
            check('revision/history', 'accepted revisions remain immutable, linked and digest-bound',
                  old == before and a['revision'] == 1 and b['revision'] == 2 and b['previous'] == a['digest']
                  and b['digest'] != a['digest'] and bool(stale) and unauthorized == 'unauthorized:agent_owner'
                  and invalid == 'invalid_input:agent_mcp')
            for engine in ('claude','codex'):
                if engine == 'codex':
                    direct_role = f.role(engine)
                    direct_role['settings']['model'] = 'gpt-5.5'
                    f.save(direct_role)
                    accepted = C.bind(f.writer, f.DOMAIN, f.REPOSITORY,
                                      {'role': 'codex', 'revision': 1})['role_revision']
                    capability = L.HANDOFF.materialize(f.writer, f.DOMAIN, f.REPOSITORY, accepted,
                                                      {'project': f.src, 'factory': base})
                    foreign = base / 'foreign'
                    f.GP.run(['git', 'init', '-q', str(foreign)], check=True, capture_output=True)
                    prior_git_dir = os.environ.get('GIT_DIR')
                    try:
                        os.environ['GIT_DIR'] = str(foreign / '.git')
                        links, stage_error = attempt(lambda: L.HANDOFF.stage_skills(capability, base))
                    finally:
                        if prior_git_dir is None:
                            os.environ.pop('GIT_DIR', None)
                        else:
                            os.environ['GIT_DIR'] = prior_git_dir
                    rule = '/.agents/skills/inspect'
                    check('review/skill-git-boundary', 'skill exclusion stays in the project despite ambient Git selectors',
                          stage_error is None and bool(links)
                          and rule in (f.src / '.git/info/exclude').read_text()
                          and rule not in (foreign / '.git/info/exclude').read_text())
                    for link in links or []:
                        link.unlink()
                    # The account profile's own MCP server, which exec never loads (--ignore-user-config): the
                    # listing must read exactly the table exec is handed, never this profile's config.toml.
                    profile = Path(f.HELPER.resolve('acct-x1', root=str(f.helper_root)))
                    (profile / 'config.toml').write_text('[mcp_servers.profile_only]\ncommand = "/bin/false"\n')
                work, record, own, error = run(engine, 'handoff-' + engine, {'role': engine})
                check('handoff/' + engine, 'the Runner and receiver complete the accepted role',
                      record.get('state') == 'exited' and f.D.completed(record) and bool(own))
                contract = record.get('contract') or {}
                bound = ((contract.get('capability') or {}).get('configuration') or {}).get('role_revision', {})
                check('handoff/' + engine, 'dispatch records accepted revision and model',
                      bound.get('digest') and bound.get('settings') == {'model':'fixture-model' if engine == 'claude' else 'gpt-5.5'})
                reports = [m.get('credentials') for m in (work.messages if work else []) if m.get('event') == 'credentials']
                check('handoff/' + engine, 'only selected catalog credential source reaches this run',
                      bool(reports) and reports[0].get('credentials') == ['jira'])
                artifact = next((m['artifact'] for m in (work.messages if work else []) if m.get('event') == 'artifact'), {})
                document = json.loads(Path(artifact['path']).read_text()) if artifact.get('path') else {}
                # A run refused before its engine started has no execution record: its rows red by assertion.
                page = (attempt(lambda: f.L.ER.read(f.state / 'records', work.dispatch_id, 0, 10000,
                                                    record.get('execution_record')))[0] if work else None) or {}
                contexts = [json.loads(r['payload']).get('first_turn_context') for r in page.get('lines', [])
                            if r['stream'] == 'wrapper' and 'first_turn_context' in r['payload']]
                check('launch/instructions', engine + ': first turn context retained in the bound execution record',
                      isinstance(document.get('first_turn_context'), int) and document['first_turn_context'] > 0 and contexts == [document.get('first_turn_context')])
                if engine == 'claude':
                    check('launch/instructions', 'Claude debug evidence survives run-directory teardown',
                          any('Role instruction discovery disabled' in r['payload'] for r in page.get('lines',[])
                              if r['stream'] == 'stderr'))
                    init = own.get('init', {})
                    check('handoff/claude', 'exact native and selected Jira MCP tools',
                          set(init.get('tools',[])) == {'Read','PushNotification','Skill','mcp__jira__jira_search'}
                          and init.get('mcp_servers') == [{'name':'jira','status':'connected'}])
                    denied = next((v.split('=',1)[1].split(',') for v in own.get('argv',[])
                                   if v.startswith('-'*2+'disallowedTools=')), [])
                    check('launch/push', 'PushNotification is offered and never disallowed',
                          'PushNotification' in init.get('tools',[]) and 'PushNotification' not in denied)
                    pid = next((p.stem for p in markers.glob('*.json')
                                if json.loads(p.read_text()).get('dispatch') == (work.dispatch_id if work else '')), '')
                    received = json.loads((markers / (pid + '.input')).read_text()) if (markers / (pid + '.input')).is_file() else []
                    users = [m for m in received if m['type'] == 'user']
                    check('handoff/claude', 'an empty no-turn probe draws init before the prompt is written',
                          [m['type'] for m in received] == ['control_request', 'user', 'user']
                          and users[0] == {'type': 'user', 'shouldQuery': False, 'content': []}
                          and users[1].get('shouldQuery') is None and bool(users[1].get('content')))
                    claude_blocked = not users
                    check('handoff/claude', 'engine plugins, bundled and built-in skills stay off; built-in commands only typed',
                          [p['name'] for p in init.get('plugins', [])] == ['veldo-role'] and init.get('skills') == ['veldo-role:inspect']
                          and set(init.get('slash_commands', [])) - {'veldo-role:inspect'} == {'clear', 'compact', 'init'})
                    check('launch/instructions', 'both listed instruction sources reach generated Claude file',
                          own.get('instructions') == 'Use the listed role instruction.\n\n\nUse the project role instruction.\n')
                else:
                    check('review/skill-commit', 'a commit of everything includes delivery and no staged skill link',
                          'delivered.txt' in own.get('committed_paths', [])
                          and not any(p.startswith('.agents/skills/') for p in own.get('committed_paths', [])))
                    wire = own.get('wire', {'tools':[]})
                    wanted = L.HANDOFF.expected({'revision':bound, 'skills':[]}, {'jira':{'tools':['jira_search']}})
                    compare = getattr(L.HANDOFF, 'codex_tool_difference', None)
                    evidence = load('v127_wire_evidence', EVIDENCE_PATH)
                    observe = getattr(evidence, 'wire_observation', None)
                    observed, obs_error = attempt(lambda: observe(wire, wanted, L.HANDOFF))
                    observed = observed or {}
                    resources = ['list_mcp_resource_templates', 'list_mcp_resources', 'read_mcp_resource']
                    granted = wanted
                    good = compare(wire, granted) if compare else 'absent comparison'
                    extra = copy.deepcopy(wire); extra['tools'].append({'type':'function','name':'ungranted'})
                    missing = {'tools':[{'type':'function','name':'exec_command'}, {'type':'function','name':'update_plan'}]}
                    check('review/codex-tools', 'both directions compare effective definitions with mapped grants',
                          compare is not None and good is None
                          and compare(extra, granted) == 'configuration_stop:codex_unexpected_tool'
                          and observe(extra, wanted, L.HANDOFF).get('unexpected') == ['ungranted']
                          and compare(missing, wanted) == 'configuration_stop:codex_missing_tool')
                    check('review/codex-tools', 'qualification writer and comparator share the shell and plan vocabulary',
                          observed.get('native_tool_mapping', {}).get('shell') == ['exec_command','write_stdin']
                          and json.loads((base / 'codex-qualification.json').read_text()).get('native_tool_mapping') == observed.get('native_tool_mapping')
                          and observed.get('missing') == [] and observed.get('unexpected') == []
                          and observe(missing, wanted, L.HANDOFF).get('missing') == sorted(resources + ['mcp__jira__jira_search', 'write_stdin']))
                    check('wire/resources', 'selected server grants exactly its three resource readers',
                          observed.get('unexpected') == [] and observed.get('missing') == []
                          and observed.get('stop') is None and good is None
                          and set(resources) <= set(observed.get('actual', [])))
                    for resource in resources:
                        reduced = copy.deepcopy(wire)
                        reduced['tools'] = [t for t in reduced['tools']
                            if t.get('function', t).get('name') != resource]
                        check('wire/resources', resource + ': missing reader fails equality',
                              compare(reduced, wanted) == 'configuration_stop:codex_missing_tool')
                    aliases = copy.deepcopy(wire)
                    for tool in aliases['tools']:
                        if 'function' in tool:
                            tool['function']['name'] = 'functions.' + tool['function']['name'].replace('mcp__jira.', 'mcp__jira__')
                    check('wire/normalization', 'direct namespaces and MCP spellings compare to the same grants',
                          good is None and compare(aliases, granted) is None)
                    cfg = own.get('configuration', {})
                    check('handoff/codex', 'generated settings, native features and filtered MCP list match',
                          own.get('mcp_tools') == {'jira':['jira_search']} and cfg.get('model') == 'gpt-5.5'
                          and cfg.get('features',{}).get('shell_tool') is True
                          and cfg.get('features',{}).get('multi_agent') is False)
                    listings = [m.get('listing') for m in (work.messages if work else []) if m.get('event') == 'capability_listing']
                    check('handoff/codex', "Codex's own listing names exactly the generated table, not the profile's",
                          listings == [[{'name': 'jira', 'enabled': True, 'enabled_tools': ['jira_search']}]])
                    # The fake loads model_catalog_json for `mcp` as the real binary does: the per-run catalog must
                    # exist before the listing runs, or the launch stops as configuration_stop:mcp_servers.
                    check('handoff/codex', 'the per-run model catalog is written before Codex lists its MCP table',
                          bool(listings) and record.get('refusal') is None
                          and Path(cfg.get('model_catalog_json', '/nonexistent')).name == 'model-catalog.json')
                    check('launch/instructions', 'Codex gets both sources through developer instructions',
                          'project role instruction' in cfg.get('developer_instructions',''))
            for mode, model in [('code', 'gpt-6-astra'), ('direct', 'gpt-5.5')]:
                body = json.loads((TREE / ('proof/VELDO-0127/request-' + mode + '.json')).read_text())
                wanted = L.HANDOFF.expected({'revision':dict(bound, settings={'model':model}), 'skills':[]},
                                            {'jira':{'tools':['jira_search']}})
                facts, _ = attempt(lambda: evidence.wire_observation(body, wanted, L.HANDOFF))
                check('wire/resources', mode + ': retained binary request equals grants including configured-server readers',
                      facts is not None and facts.get('missing') == [] and facts.get('unexpected') == [] and facts.get('stop') is None)
            qualified = json.loads((base / 'codex-qualification.json').read_text())
            check('wire/no-server', 'qualification records the conditional MCP server grant',
                  qualified.get('native_tool_mapping', {}).get('mcp_server') == resources
                  and qualified.get('mcp_resource_rule') == {
                      'when':'nonempty_mcp_servers', 'mapping':'mcp_server', 'otherwise':[]})
            for model in ('gpt-6-astra', 'gpt-5.5'):
                definition = f.role('codex', 'no-server-' + model)
                definition['settings']['model'] = model
                definition['mcp'] = []
                f.save(definition)
                _, rec, own, _ = run('codex', 'no-server-' + model, {'role':definition['role']})
                revision = rec.get('contract', {}).get('capability', {}).get('configuration', {}).get('role_revision', {})
                wanted = L.HANDOFF.expected({'revision':revision, 'skills':[]}, {})
                wire = own.get('wire', {})
                observed = evidence.wire_observation(wire, wanted, L.HANDOFF)
                check('wire/no-server', model + ': accepted empty server selection exposes no resource readers',
                      f.D.completed(rec) and own.get('configuration', {}).get('mcp_servers', {}) == {}
                      and observed['actual'] == observed['expected'] and observed['stop'] is None
                      and not set(resources) & set(observed['actual']))
                captured = json.loads((TREE / ('proof/VELDO-0127/resources-' + model + '-none.json')).read_text())
                observations = [evidence.wire_observation(r['body'], wanted, L.HANDOFF)
                                for r in captured.get('requests', [])]
                check('wire/no-server', model + ': real loopback capture confirms absence without a server',
                      captured.get('returncode') == 0 and bool(observations)
                      and captured.get('configuration', {}).get('mcp_servers') == {}
                      and all(o['actual'] == o['expected'] and not set(resources) & set(o['actual'])
                              and o['stop'] is None for o in observations))
                for resource in resources:
                    extra = copy.deepcopy(wire)
                    extra.setdefault('tools', []).append({'type':'function', 'name':resource})
                    check('wire/no-server', model + ': unselected reader ' + resource + ' fails closed',
                          compare(extra, wanted) == 'configuration_stop:codex_unexpected_tool')
            modes = json.loads((TREE / 'proof/VELDO-0127/codex-tool-investigation.json').read_text()).get('qualified_model_tool_modes')
            check('review/codex-mode', 'qualification writer retains the empty-profile binary model modes',
                  bool(modes) and qualified.get('model_tool_modes') == modes)
            absent_modes = dict(qualified); absent_modes.pop('model_tool_modes', None)
            _, absent_stop = attempt(lambda: L.HANDOFF.X.qualified_baseline(None, absent_modes))
            check('review/codex-mode', 'a qualification without model modes cannot bind',
                  absent_stop == 'missing_evidence:codex_model_tool_modes')
            catalog = qualified.get('model_catalog') or {}
            check('catalog/integrity', 'qualification captures the fake binary bundled catalog with its digest',
                  catalog == json.loads((TREE / 'proof/VELDO-0127/catalog-fixture.json').read_text())
                  and qualified.get('model_catalog_digest') == f.config_api.digest(catalog))
            role_model = getattr(L.HANDOFF, 'codex_model', None)
            for model in ('gpt-6-astra', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'):
                definition = f.role('codex', 'restricted-' + model)
                definition['settings']['model'] = model
                accepted = f.save(definition)
                work, rec, own, error = run('codex', 'mode-' + model, {'role':definition['role']})
                check('review/codex-mode', model + ': Code Mode runs with unchanged model and generated catalog',
                      rec.get('state') == 'exited' and f.D.completed(rec) and bool(own.get('model_catalog'))
                      and own.get('configuration', {}).get('model') == accepted['settings']['model'] == model)
                original = next((m for m in catalog.get('models', []) if m['slug'] == model), {})
                expected_entry = copy.deepcopy(original)
                expected_entry.pop('multi_agent_version', None)
                expected_entry.update(experimental_supported_tools=[], apply_patch_tool_type=None, supports_search_tool=False)
                check('catalog/fields', model + ': exactly four permitted fields change',
                      bool(original) and own.get('model_catalog') == dict(catalog, models=[expected_entry]))
                wanted = L.HANDOFF.expected({'revision':rec.get('contract', {}).get('capability', {}).get('configuration', {}).get('role_revision',
                                                 dict(native_tools=['shell','update_plan'], settings={'model':model})), 'skills':[]},
                                          {'jira':{'tools':['jira_search']}})
                obs, _ = attempt(lambda: evidence.wire_observation(own.get('wire', {}), wanted, L.HANDOFF))
                check('wire/normalization', model + ': runner and nested declarations expose every grant',
                      obs is not None and obs.get('missing') == [] and obs.get('unexpected') == []
                      and set(obs.get('actual', [])) == {'exec','wait','exec_command','write_stdin','update_plan','mcp__jira__jira_search', *resources})
                if model == 'gpt-6-astra':
                    granted_wire = wanted
                    check('review/codex-tools', 'Code Mode equality includes runner and nested declarations',
                          compare(own.get('wire', {}), granted_wire) is None)
                    bound_revision = dict(native_tools=['shell','update_plan'], settings={'model':model})
                    for label, altered in [('absent', dict(qualified, model_catalog=None)),
                                           ('digest', dict(qualified, model_catalog_digest='changed'))]:
                        _, stop = attempt(lambda: role_model(altered, bound_revision))
                        check('catalog/integrity', label + ': unusable override retains named Code Mode stop',
                              stop == 'configuration_stop:codex_code_mode_model')
                        check('review/codex-mode', label + ': override failure stops closed',
                              stop == 'configuration_stop:codex_code_mode_model')
            for grants in (['sub_agents'], ['apply_patch'], ['clock'], ['request_user_input_async'], ['tool_search'],
                           ['sub_agents','apply_patch','clock','request_user_input_async','tool_search']):
                name = 'grants-' + '-'.join(grants)
                definition = f.role('codex', name)
                definition['settings']['model'] = 'gpt-6-astra'
                definition['native_tools'] += [{'name':n, 'load':'always'} for n in grants]
                _, save_error = attempt(lambda: f.save(definition))
                _, rec, own, _ = run('codex', name, {'role':name}) if save_error is None else (None, {}, {}, None)
                if 'tool_search' in grants:
                    check('catalog/grants', name + ': undeliverable search grant is refused at save',
                          save_error == 'unsupported_configuration:codex_tool:gpt-6-astra:tool_search')
                    continue
                entry = next(iter(own.get('model_catalog', {}).get('models', [])), {})
                original = next((m for m in catalog.get('models', []) if m['slug'] == 'gpt-6-astra'), {})
                wanted_entry = copy.deepcopy(original)
                if 'sub_agents' not in grants: wanted_entry.pop('multi_agent_version', None)
                if 'apply_patch' not in grants: wanted_entry['apply_patch_tool_type'] = None
                if 'tool_search' not in grants: wanted_entry['supports_search_tool'] = False
                wanted_entry['experimental_supported_tools'] = [n for n in original.get('experimental_supported_tools', [])
                    if {'send_user_message_async':'request_user_input_async','clock':'clock'}.get(n,n) in grants]
                check('catalog/grants', name + ': accepted grants preserve only the requested catalog fields',
                      rec.get('state') == 'exited' and f.D.completed(rec) and entry == wanted_entry and bool(original))
            # A prepared A is launched after B has been saved, so the receiver must not reread the head.
            pending = f.prepare('claude', 'bound-a', {'role':'claude','revision':1}, payload('claude'))
            updated = f.role('claude'); updated['native_tools'] = [{'name':'Read','load':'always'}]
            f.save(updated, 2)
            work = f.launch('claude', pending) if not claude_blocked else None
            record = f.finish('claude', work) if work else {}
            _, later, later_own, _ = run('claude', 'bound-b', {'role':'claude'})
            earlier = record.get('contract', {}).get('capability', {}).get('configuration', {}).get('role_revision', {})
            next_revision = later.get('contract',{}).get('capability',{}).get('configuration',{}).get('role_revision',{})
            check('dispatch/binding', 'a launch stays on A after B is saved and next dispatch uses B',
                  earlier == pending['capability']['configuration']['role_revision'] and earlier['revision'] == 1
                  and next_revision.get('revision') == 3 and later_own.get('init',{}).get('tools') == ['Read','mcp__jira__jira_search'])
            deferred = f.role('claude','deferred',True)
            deferred['skills'][0]['load'] = 'when assigned'
            deferred['native_tools'].append({'name':'Bash', 'load':'when assigned'})
            deferred['instructions'].append({'source':'factory','path':'not-present.md','load':'when assigned'})
            f.save(deferred)
            _, rec, own, _ = run('claude','deferred',{'role':'deferred'})
            check('launch/unlisted', 'unassigned server, skill and instruction never load; the granted Skill tool stays',
                  rec.get('state') == 'exited' and f.D.completed(rec) and 'Bash' not in own.get('init',{}).get('tools',[])
                  and 'Skill' in own.get('init',{}).get('tools',[])
                  and own.get('init',{}).get('skills') == []
                  and own.get('init',{}).get('plugins') == []
                  and own.get('init',{}).get('mcp_servers') == [{'name':'jira','status':'connected'}])
            # The runner stops the receiver once it reads the end, so staged links go with the run directory,
            # before the end is reported, never in close() alone (a race that left a dangling link in the clone).
            unstage_run = base / 'unstage-run'
            (unstage_run / 'config/role-skills/inspect').mkdir(parents=True)
            unstage_link = base / 'unstage-link'
            unstage_link.symlink_to(unstage_run / 'config/role-skills/inspect', target_is_directory=True)
            receiver = object.__new__(f.L.Receiver)
            receiver.run, receiver.supervision, receiver.role_skills = str(unstage_run), {'empty': True}, [unstage_link]
            receiver._remove_run()
            check('review/skill-commit', 'staged role skills are removed with the run, before its end is reported',
                  not unstage_link.is_symlink() and not unstage_run.exists() and receiver.role_skills == [])
            source_skill = f.src / '.agents/skills/inspect/SKILL.md'
            source_skill.parent.mkdir(parents=True, exist_ok=True)
            source_skill.write_text((base / 'SKILL.md').read_text())
            f.configurations.save({'skill':'inspect','source':'project','path':'.agents/skills/inspect/SKILL.md'},
                                  kind=C.KINDS[1], principal='owner', base=1, command_id='project-skill')
            skill_role = f.role('codex', 'project-skill')
            skill_role['skills'][0]['revision'] = 2
            f.save(skill_role)
            _, listed, _, _ = run('codex', 'listed-project-skill', {'role':'project-skill'})
            check('launch/unlisted', 'a listed project skill is allowed and its source survives teardown',
                  f.D.completed(listed) and source_skill.is_file())
            no_skill = f.role('codex', 'no-project-skill'); no_skill['skills'] = []
            f.save(no_skill)
            _, rejected, _, _ = run('codex', 'unlisted-project-skill', {'role':'no-project-skill'})
            check('launch/unlisted', 'an unlisted project skill is refused before the first turn',
                  rejected.get('refusal','').startswith('invalid_input:engine_clone:'))
            source_skill.unlink()
            source_skill.parent.rmdir()
            for fault, row in [('skill','launch/unlisted'),('tool','dispatch/refusal'),('missing','handoff/claude')]:
                (markers / 'fault').write_text(fault)
                work, rec, own, _ = run('claude','fault-'+fault,{'role':'claude','revision':1})
                turns = [p for p in markers.glob('*.turn') if (markers / (p.stem+'.json')).exists()
                         and json.loads((markers / (p.stem+'.json')).read_text()).get('dispatch') == (work.dispatch_id if work else '')]
                check(row, fault + ': launch mismatch stops before prompt release',
                      bool(work) and not f.D.completed(rec) and not turns
                      and any(m.get('supervision',{}).get('cause') == 'configuration_stop'
                              for m in work.messages))
            for fault, row, stop in [('probe-exit', 'review/probe-terminal', 'configuration_stop:prompt_write_failed'),
                                     ('no-init', 'review/init-bound', 'configuration_stop:init_missing'),
                                     ('slash', 'review/slash-collision', 'configuration_stop:slash_commands')]:
                (markers / 'fault').write_text(fault)
                started = __import__('time').monotonic()
                work, rec, own, _ = run('claude', 'review-' + fault, {'role':'claude','revision':1})
                elapsed = __import__('time').monotonic() - started
                artifact = next((m['artifact'] for m in (work.messages if work else []) if m.get('event') == 'artifact'), {})
                document = json.loads(Path(artifact['path']).read_text()) if artifact.get('path') else {}
                check(row, 'production run refuses by name within the init bound',
                      bool(work) and not f.D.completed(rec) and document.get('login', {}).get('stop') == stop and elapsed < 15)
                if fault == 'probe-exit':
                    check(row, 'zero-turn probe never becomes the terminal record',
                          document.get('terminal') is None and (document.get('probe', {}).get('result') or {}).get('num_turns') == 0)
            (markers / 'fault').unlink()
            for name, change in [('setting', lambda d: d['settings'].update(unsupported=True)),
                                 ('tool', lambda d: d['mcp'][0].update(tools=['absent']))]:
                definition = f.role('claude',name); change(definition); f.save(definition)
                work, rec, own, error = run('claude','refused-'+name,{'role':name})
                check('dispatch/refusal', name + ': required unsupported capability has a named stop',
                      rec.get('state') == 'refused' and rec.get('refusal') == (
                          'unsupported_configuration:engine_settings' if name == 'setting'
                          else 'unavailable_service:mcp_tools:jira') and not own)
            _, rejected, own, _ = run('claude', 'unaccepted-role', {'role_revision':{'role':'invented','revision':1,'native_tools':['Read']}})
            check('revision/history', 'a caller cannot invent an accepted role revision',
                  rejected.get('refusal') == 'invalid_input:role_revision' and not own)
            for field in ('native_tools', 'mcp', 'skills', 'instructions'):
                invalid_mode = f.role('claude', 'mode-' + field)
                invalid_mode[field][0]['load'] = 'default'
                _, error = attempt(lambda: f.save(invalid_mode))
                check('revision/history', field + ': every item requires an explicit supported load mode', bool(error))
            ordinary = json.dumps(list(f.writer.execute('SELECT * FROM journal')), default=str) + json.dumps(f.changes) + ''.join(r[0] for r in f.writer.execute('SELECT data FROM entities'))
            check('revision/history', 'no resolved credential value enters ordinary views',
                  all(v not in ordinary for v in f.values.values()))
            check('format/fake-lines', 'shared constructors produce both completed stream protocols',
                  bool(list(markers.glob('*.out'))))
            evidence = load('v127_live_evidence', EVIDENCE_PATH)
            # Exercise relocation and a semantic no-op even in the standalone suite. Keep
            # the supplied driver (including mutations), but resolve its unchanged loopback
            # dependency from this suite's tree: loopback itself needs the repository assets.
            driver_copy = base / 'capture-driver' / 'live.py'
            driver_copy.parent.mkdir()
            driver_copy.write_bytes(LIVE_PATH.read_bytes() + b'\n# Capture relocation control.\n')
            live = load('v127_live_driver', driver_copy)
            live.HERE = TREE / 'proof/VELDO-0127'
            capture_role = f.role('codex', 'codex-always')
            capture_role['settings']['model'] = 'gpt-6-astra'
            f.save(capture_role)
            direct, error = attempt(lambda: live.capture(f, 'codex', 'always', False, evidence))
            check('review/codex-capture', 'lead driver records the loopback tools beside its production run (capture error=%s)' % error,
                  direct is not None and bool(direct.get('wire_tools'))
                  and direct.get('wire_tools') == [evidence.wire_observation(r['body'], direct['expected'], L.HANDOFF)
                                                 for r in direct.get('wire_capture', {}).get('requests', [])]
                  and direct['configuration']['model'] == direct['revision']['settings']['model'] == 'gpt-6-astra'
                  and direct.get('model_catalog', {}).get('models', [{}])[0].get('tool_mode') == 'code_mode_only')
            select_model = getattr(live, 'codex_model', None)
            accepted_models = []
            for model in ('gpt-6-astra', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'):
                try:
                    if select_model: select_model(model, L.HANDOFF.X)
                    accepted_models.append(True)
                except SystemExit:
                    accepted_models.append(False)
            check('review/codex-capture', 'lead accepts Code Mode models without substitution and rejects unknown models',
                  select_model is not None and select_model('gpt-5.5', L.HANDOFF.X) == 'gpt-5.5' and all(accepted_models))
            try:
                if select_model: select_model('unknown-model', L.HANDOFF.X)
                unknown_refused = False
            except SystemExit:
                unknown_refused = True
            check('review/codex-capture', 'unknown model is refused', unknown_refused)
            # The driver reads the same real writer's fake-engine execution record.
            f.save(f.role('claude', 'claude-always'))
            captured, error = attempt(lambda: live.capture(f, 'claude', 'always', True, evidence)) if not claude_blocked else (None, None)
            check('review/marker-debug', 'planted debug instruction loads are rejected, with a discovery control recorded',
                  captured is not None and hasattr(evidence, 'debug_problems')
                  and bool(evidence.debug_problems(captured, {'ran':True, 'returncode':0, 'debug_lines':['Loaded CLAUDE.md']})))
            if captured is not None and hasattr(evidence, 'debug_problems'):
                clean = dict(captured, debug_lines=[])
                check('review/marker-debug', 'no positive debug control is explicitly context-size-only',
                      not evidence.debug_problems(clean, {'ran':True, 'returncode':0, 'debug_lines':[], 'qualification':'context-size-only'})
                      and bool(evidence.debug_problems(clean, {'ran':True, 'returncode':0, 'debug_lines':[]})))
                check('review/probe-terminal', 'live capture retains zero-turn result and assistant count before prompt',
                      ((captured.get('probe') or {}).get('result') or {}).get('num_turns') == 0
                      and (captured.get('probe') or {}).get('assistants_before_prompt') == 0)
            for engine in ('claude','codex'):
                path = TREE / ('proof/VELDO-0127/' + engine + '-live.json')
                data, error = attempt(lambda: json.loads(path.read_text()))
                data = data if isinstance(data, dict) else {}
                evidence = load('v127_live_evidence', EVIDENCE_PATH)
                problems = evidence.problems(TREE, engine, data, f.L.HANDOFF)
                check('live/' + engine, '; '.join(problems), not problems)
    except Exception as error:
        for row in ROWS:
            check(row, 'the run ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:180]), False)
    finally:
        if f is not None:
            fake_capture = conform_formats.conform_fake(locals(), '0127_agent_configuration')
            for connection in f.connections: connection.close()
            __import__('subprocess').run(['systemctl', '-'*2+'user', 'stop', f.slice_name],
                                        env=f.inherited, capture_output=True, timeout=20)
        shutil.rmtree(base)
    for row, observed in rows.items():
        for label, ok in observed:
            if not ok: print('  VELDO-0127 %s detail: %s' % (row,label))
        expect('VELDO-0127 ' + row, bool(observed) and all(ok for _,ok in observed))
    if f is not None:
        for line in conform_formats.describe('0127_agent_configuration', *fake_capture): print(line)
        expect('VELDO-0172 fake/capture:0127_agent_configuration', bool(fake_capture[1]) and not fake_capture[0])

_v127_suite()
