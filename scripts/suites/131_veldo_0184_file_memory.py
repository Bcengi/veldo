"""VELDO-0184: the file memory directory is handed to every run whose role lists it, on either engine and any
account, and its index load and every memory file read and write are in the record.

Run: python3 scripts/selftest.py --suite 131_veldo_0184_file_memory

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support), the production
conversation authority and VELDO-0174's conversation Line with real receiver subprocesses (support/v174_journey.py)
over fake pinned engines generated here from VELDO-0174's, as another host's adapters (no worker group, so no user
manager). The memory record is VELDO-0182's fixture manifest (proof/VELDO-0182/fixtures.py) in a temporary directory.
The fake Claude Code applies auto memory as the 2.1.281 bytes do (proof/VELDO-0184/engine-memory-forms.json): on
unless CLAUDE_CODE_DISABLE_AUTO_MEMORY or `autoMemoryEnabled` false, in the flag settings' `autoMemoryDirectory`
else the account profile's projects/<cwd>/memory, named in its init event's `memory_paths` with a trailing
separator, the index loaded into its context. The fake Codex keeps its workspace-write sandbox: a write outside the
working directory and the configured writable roots is refused. Fake engines only: no real engine, login, memory
store or paid API. Writes only temporary fixtures.
"""


def _v184_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
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
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_memory_file.py': ROOT / ".veldo" / "control_memory_file.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_memory_servers.py': ROOT / ".veldo" / "control_memory_servers.py",
    }
    ROWS = ('AC1/role-item', 'AC1/settings', 'AC1/memory-path', 'AC1/without', 'AC1/qualified', 'AC1/mismatch-stop',
            'AC1/absent', 'AC2/configuration', 'AC2/write', 'AC2/later-read', 'AC2/qualified',
            'AC3/loaded-at-launch', 'AC3/tool-lines', 'AC3/no-content', 'AC3/observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def refusal(call):
        try:
            call()
        except Exception as error:  # noqa: BLE001
            return getattr(error, 'code', type(error).__name__)
        return None

    def sha(data):
        return 'sha256:' + hashlib.sha256(data).hexdigest()

    H = load('v184_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v184_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v184_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    FIX = load('v184_memory_fixtures', ROOT / 'proof/VELDO-0182/fixtures.py')
    base = Path(tempfile.mkdtemp(prefix='v184-', dir=fast_temp()))
    fixtures = []
    lock = factory = None

    # THE FAKE ENGINES: VELDO-0174's, with auto memory as the 2.1.281 binary applies it (Claude Code), the
    # workspace-write sandbox (Codex), and the memory scenario in the markers directory after the release.
    LITERALS = "# MemoriesToml generate_memories use_memories SandboxWorkspaceWrite writable_roots developer_instructions\n"
    INIT_END = "            'cwd':os.getcwd()}\n"
    INIT_MEMORY = INIT_END + r'''    flag_settings = json.loads(Path(args[args.index('--settings')+1]).read_text()) if '--settings' in args else {}
    profile = Path(os.environ.get('CLAUDE_CONFIG_DIR') or (Path.home() / '.claude'))
    profile_memory = str(profile / 'projects' / re.sub('[^A-Za-z0-9]', '-', os.getcwd()) / 'memory')
    switch = os.environ.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY', '')
    memory_on = switch.lower() not in ('1', 'true', 'yes', 'on') and flag_settings.get('autoMemoryEnabled', True) is not False
    memory_dir = flag_settings.get('autoMemoryDirectory') or profile_memory
    memory_scenario = json.loads((MARKERS / 'memory-scenario.json').read_text()) if (MARKERS / 'memory-scenario.json').exists() else {}
    if memory_scenario.get('claude_memory') == 'profile':
        memory_dir = profile_memory
    index_loaded = None
    if memory_on:
        init['memory_paths'] = {'auto': memory_dir.rstrip('/') + '/'}
        index_file = Path(memory_dir) / 'MEMORY.md'
        index_loaded = index_file.read_text() if index_file.exists() else None
    (MARKERS / (str(os.getpid()) + '.init.json')).write_text(json.dumps({
        'dispatch': os.environ.get('VELDO_DISPATCH_ID'), 'memory_on': memory_on, 'memory_dir': memory_dir,
        'index': index_loaded, 'settings': flag_settings, 'switch': os.environ.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY'),
        'environment': sorted(os.environ), 'profile': str(profile), 'argv': args}))
'''
    RELEASE = "while not (MARKERS / 'release').exists(): time.sleep(.02)\n"
    CLAUDE_WORK = RELEASE + r'''memory_scenario = json.loads((MARKERS / 'memory-scenario.json').read_text()) if (MARKERS / 'memory-scenario.json').exists() else {}
memory_done = {}
def use(name, given, result):
    uid = 'toolu_' + name.lower() + '_' + str(os.getpid()) + '_' + str(len(memory_done))
    emit({'type':'assistant','message':{'id':'use-'+uid,'type':'message','role':'assistant',
          'content':[{'type':'tool_use','id':uid,'name':name,'input':given}],'usage':{'input_tokens':1,'output_tokens':1}}})
    emit({'type':'user','message':{'role':'user','content':[{'type':'tool_result','tool_use_id':uid,'content':result}]}})
    memory_done[uid] = [name, given, result]
if ENGINE != 'codex':
    seen = json.loads((MARKERS / (str(os.getpid()) + '.init.json')).read_text())
    did, modes = os.environ.get('VELDO_DISPATCH_ID', ''), memory_scenario.get('claude', {})
    mode = next((v for k, v in modes.items() if '/' + k + '/' in did), modes.get('*'))
    if seen['memory_on'] and mode:
        d = Path(seen['memory_dir'])
        if mode.get('read') is not None:
            use('Read', {'file_path': str(d / 'MEMORY.md')}, (d / 'MEMORY.md').read_text())
            for name in mode['read']:
                use('Read', {'file_path': str(d / name)}, (d / name).read_text())
        if mode.get('write'):
            name, text, line = mode['write']
            (d / name).write_text(text)
            use('Write', {'file_path': str(d / name), 'content': text}, 'File created successfully at: ' + str(d / name))
            old = (d / 'MEMORY.md').read_text()
            (d / 'MEMORY.md').write_text(old + line + '\n')
            use('Edit', {'file_path': str(d / 'MEMORY.md'), 'old_string': old, 'new_string': old + line + '\n'},
                'The file ' + str(d / 'MEMORY.md') + ' has been updated.')
    (MARKERS / (str(os.getpid()) + '.memory.json')).write_text(json.dumps(memory_done))
'''
    TURN_STARTED = "    emit({'type':'turn.started'})\n"
    CODEX_WORK = TURN_STARTED + r'''    memory_scenario = json.loads((MARKERS / 'memory-scenario.json').read_text()) if (MARKERS / 'memory-scenario.json').exists() else {}
    developer = cfg.get('developer_instructions') or ''
    found = re.search(r'Your file memory is the directory (/\S+?), shared', developer)
    sandbox = cfg.get('sandbox_workspace_write') or {}
    roots = ([os.getcwd()] + list(sandbox.get('writable_roots') or [])) if cfg.get('sandbox_mode') == 'workspace-write' else []
    def writable(path):
        real = os.path.realpath(path)
        return any(os.path.commonpath([real, os.path.realpath(r)]) == os.path.realpath(r) for r in roots)
    memory_done = {'directory': found.group(1) if found else None}
    if found and memory_scenario.get('codex'):
        name, text, line = memory_scenario['codex']
        d = Path(found.group(1))
        target, index = d / name, d / 'MEMORY.md'
        emit({'type':'item.started','item':{'id':'memory-read','type':'command_execution','command':'cat ' + str(index),
              'aggregated_output':'','exit_code':None,'status':'in_progress'}})
        emit({'type':'item.completed','item':{'id':'memory-read','type':'command_execution','command':'cat ' + str(index),
              'aggregated_output':index.read_text(),'exit_code':0,'status':'completed'}})
        if writable(target) and writable(index):
            target.write_text(text)
            index.write_text(index.read_text() + line + '\n')
            emit({'type':'item.completed','item':{'id':'memory-write','type':'file_change','status':'completed',
                  'changes':[{'path':str(target),'kind':'add'},{'path':str(index),'kind':'update'}]}})
            memory_done['write'] = 'written'
        else:
            emit({'type':'item.completed','item':{'id':'memory-write','type':'command_execution',
                  'command':'apply_patch ' + str(target),'aggregated_output':'Read-only file system (os error 30)',
                  'exit_code':1,'status':'failed'}})
            memory_done['write'] = 'refused'
    memory_done['config'] = {k: cfg.get(k) for k in ('sandbox_mode', 'sandbox_workspace_write', 'developer_instructions',
                                                     'memories.generate_memories', 'memories.use_memories')}
    memory_done['codex_home'] = os.environ.get('CODEX_HOME')
    (MARKERS / (str(os.getpid()) + '.memory.json')).write_text(json.dumps(memory_done))
'''

    def fake_source():
        source = J.FAKE
        for old in (INIT_END, RELEASE, TURN_STARTED):
            if source.count(old) != 1:
                raise RuntimeError('the VELDO-0174 fake engine moved')
        first, rest = source.split('\n', 1)
        return (first + '\n' + LITERALS + rest).replace(INIT_END, INIT_MEMORY).replace(RELEASE, CLAUDE_WORK).replace(
            TURN_STARTED, CODEX_WORK)

    def observed(markers):
        found = {}
        for path in markers.glob('*.json'):
            if path.name.split('.')[0].isdigit() and path.name.count('.') == 1:
                value = json.loads(path.read_text())
                for kind in ('init', 'memory'):
                    extra = markers / ('%s.%s.json' % (path.stem, kind))
                    value[kind] = json.loads(extra.read_text()) if extra.exists() else None
                found[value.get('dispatch')] = value
        # A run stopped before its prompt wrote only its init marker.
        for path in markers.glob('*.init.json'):
            value = json.loads(path.read_text())
            found.setdefault(value.get('dispatch'), {'dispatch': value.get('dispatch'), 'init': value, 'packet': None})
        return found

    try:
        # A production copy that does not exist (a tree before this change) is left out, so its rows red by assertion.
        f = F.fixture(ROOT, base, H, load, 'memory', 84, {k: v for k, v in PRODUCTION.items() if Path(v).is_file()})
        fixtures.append(f)
        mods = f['root'] / 'modules'
        CV = load('v184_conversation', mods / 'control_conversation.py')
        CS = load('v184_service', mods / 'control_service.py')
        CS.CV = CV
        C = load('v184_engine_claude', mods / 'control_engine_claude.py')
        X = load('v184_engine_codex', mods / 'control_engine_codex.py')
        CFG = load('v184_agent_config', mods / 'control_agent_config.py')
        M = load('v184_memory', mods / 'control_memory.py')
        ER = load('v184_records', mods / 'control_execution_record.py')
        authority = f['authority']
        domain = authority.ids['domain_uuid']
        conversations = CV.Conversations(authority.S, authority.conn, domain=domain, principal='authority',
                                         signer='authority', sign=authority.journal_sign,
                                         state_root=f['root'] / 'state')
        f['conversations'] = conversations

        # THE MEMORY RECORD (VELDO-0182): the fixture manifest's five parts, the file memory a directory with its index.
        manifest = FIX.build(base / 'memories', host=f['host'])
        definition = M.normalize(manifest)
        directory = definition['parts']['file_memory']['data']
        index = Path(directory) / 'MEMORY.md'
        authority.fixture(M.HEAD, M.KIND, dict(schema='veldo.memory_store/v1', revision=1, owner='owner',
                                               definition=definition, signed_command={}, signature=''))

        # THE ENGINES, pinned and qualified over the fixture's modules (VELDO-0174's), as another host's adapters.
        saved_fake, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved_fake
        config = json.loads(receiver.read_text())

        # THE ROLES: `assistant` without the item, `assistant_memory` the same revision listing it, and
        # `assistant_codex` listing it on Codex's workspace-write sandbox.
        revisions = f['revisions']
        codex_role = revisions['assistant_codex']
        codex_role['settings'] = {'model': 'fixture-codex-model', 'sandbox_mode': 'workspace-write'}
        codex_role['file_memory'] = {'load': 'always'}
        memory_role = dict(revisions['assistant'], role='assistant_memory', file_memory={'load': 'always'})
        for name, revision in (('assistant_codex', codex_role), ('assistant_memory', memory_role)):
            revision.pop('digest', None)
            revision['digest'] = CFG.digest(revision)
            authority.fixture('configuration:' + name, 'agent_configuration', revision)
        roles = dict(f['roles'])
        roles['assistant_memory'] = dict(roles['assistant'], capability_configuration={'role': 'assistant_memory',
                                                                                       'revision': 1})
        authority.fixture('default-team:1', 'default_team_revision', {
            'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner', 'assertion_digest': 'sha256:fixture',
            'previous': None, 'digest': 'sha256:default-one'})
        accounts_module = load('v184_accounts', mods / 'control_accounts.py')
        accounts = accounts_module.Accounts(authority.S, authority.conn, principal='owner', signer='authority',
                                            sign=authority.journal_sign)
        profiles = {}
        for provider, number in (('claude_code', 1), ('claude_code', 2), ('codex', 1)):
            account = 'account-%s-%d' % (provider, number)
            profiles[account] = f['root'] / ('profile-' + account)
            profiles[account].mkdir(parents=True)
            accounts.register('account-register-' + account, account, provider, account,
                              {f['host']: str(profiles[account])}, concurrency=1, now=time.time())

        factory, lock, events = J.loop(f, CS, receiver)
        launched = []
        launch_prepared = factory.conversation.runner.launch_prepared

        def keeping(contract):
            launch = launch_prepared(contract)
            launched.append(launch)
            return launch
        factory.conversation.runner.launch_prepared = keeping

        def launch_of(identity):
            return next((l for l in launched if ('/' + identity + '/') in (getattr(l, 'dispatch_id', '') or '')), None)

        def messages(identity, event):
            launch = launch_of(identity)
            return [m for m in (getattr(launch, 'messages', None) or []) if isinstance(m, dict) and m.get('event') == event]

        def record_lines(identity):
            launch = launch_of(identity)
            path = Path(ER.path(ER.directory(config), launch.dispatch_id)) if launch else None
            return [json.loads(l) for l in path.read_text().splitlines()] if path and path.exists() else []

        def record_events(identity):
            found = []
            for line in record_lines(identity)[1:]:
                try:
                    found.append((line['stream'], json.loads(line.get('payload') or 'null')))
                except ValueError:
                    pass
            return found

        def launch_line(identity):
            return next((p['file_memory'] for s, p in record_events(identity)
                         if s == 'wrapper' and isinstance(p, dict) and 'file_memory' in p), None)

        def run_of(identity):
            return next((v for d, v in observed(markers).items() if d and ('/' + identity + '/') in d), {})

        def ended(identity):
            saved = conversations.turns(identity)
            return bool(saved) and saved[-1].get('state') == 'ended'

        def turns(identities, scenario, release=True, seconds=40):
            """Open each conversation with its role and send one turn each; the release marker held back until every
            engine has its prompt when `release` is False at first (the turns then run at once)."""
            (markers / 'memory-scenario.json').write_text(json.dumps(scenario))
            if (markers / 'release').exists():
                (markers / 'release').unlink()
            for identity, role in identities:
                conversations.open(identity, owner='owner', role=role, intake_digest='sha256:' + identity)
                conversations.message(identity, identity + '-1', 'sha256:' + identity + '-1', owner='owner')
            J.pass_(factory)
            if not release:
                F.drive(factory, lambda: all(run_of(i).get('packet') for i, _ in identities)
                        or all(ended(i) for i, _ in identities), seconds)
            (markers / 'release').touch()
            F.drive(factory, lambda: all(ended(i) for i, _ in identities), seconds)
            return [conversations.turns(i)[-1] if conversations.turns(i) else {} for i, _ in identities]

        def refused(identity):
            return next((m.get('refusal') for m in messages(identity, 'refused')), None)

        # ---- AC1: the item and the roles setup saves -------------------------------------------------------------
        plain_definition = {k: revisions['assistant'][k] for k in CFG.FIELDS}
        check('AC1/role-item', 'a capability configuration may list the file memory item, always or when assigned',
              refusal(lambda: CFG.validate(dict(plain_definition, file_memory={'load': 'always'}))) is None
              and refusal(lambda: CFG.validate(dict(plain_definition, file_memory={'load': 'when assigned'}))) is None)
        check('AC1/role-item', 'a revision without the item stays valid, and a malformed item is refused by name',
              refusal(lambda: CFG.validate(plain_definition)) is None
              and refusal(lambda: CFG.validate(dict(plain_definition, file_memory={'load': 'sometimes'})))
              == 'invalid_input:agent_file_memory'
              and refusal(lambda: CFG.validate(dict(plain_definition, file_memory='always'))) == 'invalid_input:agent_file_memory')
        MS = load('v184_memory_servers', mods / 'control_memory_servers.py')
        wanted = MS.selected(dict(revisions['assistant'], mcp=[]), {s: 1 for s, _ in MS.SERVERS})
        check('AC1/role-item', 'the new revision of each assistant role the setup step saves lists the item always [%s]'
              % wanted.get('file_memory'), wanted.get('file_memory') == {'load': 'always'}
              and refusal(lambda: CFG.validate(wanted)) is None and MS.ROLES == ('assistant', 'assistant_codex'))
        source = (mods / 'control_memory_servers.py').read_text()
        check('AC1/role-item', 'setup saves a new role revision when only the item is missing (its skip compares it)',
              "accepted.get('file_memory') == wanted['file_memory']" in source)

        # ---- AC1: two accounts at once with the item, one role without ------------------------------------------
        before = index.read_bytes()
        rule_claude = ('rule-claude.md', 'Always answer the owner in short paragraphs.\n',
                       '- [Short paragraphs](rule-claude.md) - how to answer the owner')
        scenario = {'claude': {'claude-one': {'read': ['fact-0.md']}, 'claude-two': {'write': list(rule_claude)}}}
        first = turns([('claude-one', 'assistant_memory'), ('claude-two', 'assistant_memory')], scenario, release=False)
        one, two = run_of('claude-one'), run_of('claude-two')
        accounts_used = sorted(filter(None, ((one.get('init') or {}).get('profile'), (two.get('init') or {}).get('profile'))))
        print('  VELDO-0184 AC1 two accounts:', accounts_used, 'outcomes:', [t.get('outcome') for t in first],
              'refusals:', refused('claude-one'), refused('claude-two'))
        check('AC1/memory-path', 'the two turns ran on the two Claude Code accounts, one each',
              accounts_used == sorted(str(profiles['account-claude_code-%d' % n]) for n in (1, 2)))
        for identity, value in (('claude-one', one), ('claude-two', two)):
            seen = value.get('init') or {}
            settings = seen.get('settings') or {}
            check('AC1/settings', '%s: the generated settings turn auto memory on in the record\'s directory [%s]'
                  % (identity, {k: settings.get(k) for k in ('autoMemoryEnabled', 'autoMemoryDirectory')}),
                  settings.get('autoMemoryEnabled') is True and settings.get('autoMemoryDirectory') == directory)
            check('AC1/settings', '%s: the launch leaves CLAUDE_CODE_DISABLE_AUTO_MEMORY unset [%s]'
                  % (identity, seen.get('switch')),
                  bool(seen) and 'CLAUDE_CODE_DISABLE_AUTO_MEMORY' not in (seen.get('environment') or ['x']))
            init = next((e for e in (value.get('events') or []) if e.get('subtype') == 'init'), None)
            paths = seen.get('memory_dir')
            check('AC1/memory-path', '%s: the init event\'s memory paths name exactly the handed directory, not the '
                  'account profile\'s [%s, profile %s]' % (identity, paths, seen.get('profile')),
                  seen.get('memory_on') is True and paths == directory and value.get('packet') is not None
                  and refused(identity) is None)
        check('AC1/memory-path', 'both turns ended completed [%s]' % [t.get('outcome') for t in first],
              [t.get('outcome') for t in first] == ['completed', 'completed'])
        check('AC1/memory-path', 'whichever account ran it, the directory is the one memory record\'s',
              (one.get('init') or {}).get('memory_dir') == (two.get('init') or {}).get('memory_dir') == directory)
        after_two = index.read_bytes()

        plain = turns([('plain', 'assistant')], {})
        plain_run = run_of('plain')
        seen = plain_run.get('init') or {}
        check('AC1/without', 'a role without the item keeps auto memory off: the switch set, no memory setting [%s %s]'
              % (seen.get('switch'), {k: v for k, v in (seen.get('settings') or {}).items() if 'Memory' in k}),
              seen.get('switch') == '1' and not any('Memory' in k for k in (seen.get('settings') or {})))
        check('AC1/without', 'its init event names no memory directory and it loaded no index',
              bool(seen) and seen.get('memory_on') is False and seen.get('index') is None
              and plain_run.get('packet') is not None)
        check('AC1/without', 'its record has no file memory launch line and no file memory event',
              launch_line('plain') is None and not messages('plain', 'file_memory')
              and [t.get('outcome') for t in plain] == ['completed'])
        # Every other part of the baseline is unchanged: the same options (run paths aside), settings and names.
        def shape(identity):
            reported = next((m['baseline'] for m in messages(identity, 'baseline')), {})
            run_config = (reported.get('run') or {}).get('config') or '/nonexistent'
            return [o.replace(run_config, '<config>') for o in reported.get('options') or []]
        one_settings = dict((one.get('init') or {}).get('settings') or {})
        for key in ('autoMemoryEnabled', 'autoMemoryDirectory'):
            one_settings.pop(key, None)
        check('AC1/settings', 'every other part of the baseline is unchanged: options, settings and environment names',
              shape('claude-one') == shape('plain') and bool(shape('plain'))
              and one_settings == (seen.get('settings') or {'x': 1})
              and sorted(set((one.get('init') or {}).get('environment') or []) | {'CLAUDE_CODE_DISABLE_AUTO_MEMORY'})
              == sorted(set(seen.get('environment') or [])))

        # A binary that keeps its auto memory in the account profile: stopped by name before its first turn.
        stopped = turns([('claude-profile', 'assistant_memory')], {'claude_memory': 'profile'})
        stopped_run = run_of('claude-profile')
        stops = messages('claude-profile', 'file_memory_stopped')
        check('AC1/mismatch-stop', 'init memory paths naming the account profile\'s directory stop the run by name '
              '[%s]' % [s.get('refusal') for s in stops],
              [s.get('refusal') for s in stops] == ['binding_mismatch:engine_memory']
              and (stopped_run.get('init') or {}).get('memory_dir', '').startswith(str(f['root'] / 'profile-')))
        check('AC1/mismatch-stop', 'before its first turn: the prompt never reached the engine [%s]'
              % [t.get('outcome') for t in stopped],
              bool(stopped_run.get('init')) and stopped_run.get('packet') is None and ended('claude-profile')
              and [t.get('outcome') for t in stopped] != ['completed'])

        # A version whose record lacks the form, on either engine: refused by name, nothing spawned.
        claude_record_path = mods / 'runtime/claude-qualification.json'
        codex_record_path = Path(config['adapters']['codex']['qualification'])
        kept = {p: p.read_text() for p in (claude_record_path, codex_record_path)}
        try:
            record = json.loads(kept[claude_record_path])
            for entry in record['versions'].values():
                entry.pop('file_memory', None)
            claude_record_path.write_text(json.dumps(record))
            record = json.loads(kept[codex_record_path])
            record.pop('file_memory', None)
            codex_record_path.write_text(json.dumps(record))
            unqualified = turns([('claude-unqualified', 'assistant_memory'), ('codex-unqualified', 'assistant_codex'),
                                 ('plain-unqualified', 'assistant')], {})
        finally:
            for path, text in kept.items():
                path.write_text(text)
        version = C.qualified(next(iter(json.loads(kept[claude_record_path])['versions'])),
                              json.loads(kept[claude_record_path]))
        claude_version = next(iter(json.loads(kept[claude_record_path])['versions']))
        codex_version = json.loads(kept[codex_record_path])['version']
        check('AC1/qualified', 'a Claude Code version whose record lacks the form launches no run that lists the item '
              '[%s]' % refused('claude-unqualified'),
              refused('claude-unqualified') == 'missing_evidence:engine_baseline:' + claude_version
              and not run_of('claude-unqualified'))
        check('AC1/qualified', 'a role without the item still runs on that version [%s]' % unqualified[2].get('outcome'),
              unqualified[2].get('outcome') == 'completed')
        check('AC2/qualified', 'a Codex version whose record lacks the form launches no run that lists the item [%s %s %s %s]'
              % (refused('codex-unqualified'), [m.get('event') for m in getattr(launch_of('codex-unqualified'), 'messages', None) or []], unqualified[1], bool(run_of('codex-unqualified'))),
              refused('codex-unqualified') == 'missing_evidence:engine_baseline:' + codex_version
              and not run_of('codex-unqualified'))
        shipped = json.loads((ROOT / '.veldo/runtime/claude-qualification.json').read_text())
        engines = json.loads((ROOT / '.veldo/runtime/engines.json').read_text())
        forms_path = ROOT / 'proof/VELDO-0184/engine-memory-forms.json'
        forms = json.loads(forms_path.read_text()) if forms_path.exists() else {}
        check('AC1/qualified', 'the pinned 2.1.281 record lists the form, read from its bytes (every literal found)',
              shipped['versions'][engines['claude_code']['version']].get('file_memory') == getattr(C, 'FILE_MEMORY', 'absent')
              and version.get('file_memory') == getattr(C, 'FILE_MEMORY', 'absent')
              and (forms.get('claude_code') or {}).get('sha256') == engines['claude_code']['sha256']
              and (forms.get('claude_code') or {}).get('file_memory') == getattr(C, 'FILE_MEMORY', 'absent')
              and all(r.get('offset') is not None for r in (forms.get('claude_code') or {}).get('found') or [None]))
        shipped_codex = json.loads((ROOT / '.veldo/runtime/codex-qualification.json').read_text())
        check('AC2/qualified', 'the pinned 0.154.0 record lists the form, read from its bytes (every literal found)',
              shipped_codex.get('file_memory') == getattr(X, 'FILE_MEMORY', 'absent') and shipped_codex['version'] == engines['codex']['version']
              and (forms.get('codex') or {}).get('sha256') == engines['codex']['sha256']
              and (forms.get('codex') or {}).get('file_memory') == getattr(X, 'FILE_MEMORY', 'absent')
              and all(r.get('offset') is not None for r in (forms.get('codex') or {}).get('found') or [None]))
        bare = base / 'bare-codex'
        executable = F.probe_binary(bare, [], {}, '/usr/bin/python3')
        check('AC2/qualified', 'the qualification writer lists the form only for a binary carrying its every key',
              'file_memory' not in X.qualification(str(executable))
              and json.loads(codex_record_path.read_text()).get('file_memory') == getattr(X, 'FILE_MEMORY', 'absent'))

        # A memory directory absent at launch: refused by name before anything is accepted.
        hidden = index.with_name('MEMORY.hidden')
        index.rename(hidden)
        try:
            absent = turns([('claude-absent', 'assistant_memory'), ('codex-absent', 'assistant_codex')], {})
        finally:
            hidden.rename(index)
        check('AC1/absent', 'a run that lists the item, its index gone, is refused invalid_input:memory:file:absent on '
              'either engine [%s %s]' % (refused('claude-absent'), refused('codex-absent')),
              refused('claude-absent') == refused('codex-absent') == 'invalid_input:memory:file:absent'
              and not run_of('claude-absent') and not run_of('codex-absent'))

        # ---- AC2: Codex reads the index in its instructions and writes the same directory --------------------------
        rule_codex = ('rule-codex.md', 'Meetings are never booked before ten.\n',
                      '- [No early meetings](rule-codex.md) - when meetings may be booked')
        before_codex = index.read_bytes()
        codex_turn = turns([('codex-writer', 'assistant_codex')], {'codex': list(rule_codex)})
        writer = run_of('codex-writer')
        done = writer.get('memory') or {}
        cfg = done.get('config') or {}
        instructions = cfg.get('developer_instructions') or ''
        check('AC2/configuration', 'the generated configuration adds the directory to the workspace-write sandbox\'s '
              'writable roots [%s]' % cfg.get('sandbox_workspace_write'),
              cfg.get('sandbox_mode') == 'workspace-write'
              and directory in ((cfg.get('sandbox_workspace_write') or {}).get('writable_roots') or []))
        check('AC2/configuration', 'its developer instructions hold the layout paragraph and the index as it stood, '
              'with the rule the other engine saved',
              ('Keep one fact per file there' in instructions and directory in instructions
               and instructions.endswith(before_codex.decode()) and rule_claude[2] in instructions))
        check('AC2/configuration', 'Codex\'s own memory feature is off [%s %s]'
              % (cfg.get('memories.generate_memories'), cfg.get('memories.use_memories')),
              cfg.get('memories.generate_memories') is False and cfg.get('memories.use_memories') is False)
        check('AC2/write', 'the Codex run wrote a new memory file and updated the index in the record\'s directory [%s]'
              % done.get('write'),
              done.get('write') == 'written' and (Path(directory) / rule_codex[0]).read_text() == rule_codex[1]
              and index.read_text().endswith(rule_codex[2] + '\n') and [t.get('outcome') for t in codex_turn] == ['completed'])
        codex_home = Path(done.get('codex_home') or '/nonexistent')
        check('AC2/write', 'nothing was written in the account profile [%s]' % sorted(p.name for p in codex_home.glob('*')),
              codex_home == profiles['account-codex-1'] and not any(codex_home.rglob('rule-codex.md')))
        after_codex = index.read_bytes()

        later = turns([('claude-later', 'assistant_memory')], {'claude': {'*': {'read': [rule_codex[0]]}}})
        reader = run_of('claude-later')
        reads = list(((reader.get('memory') or {}) or {}).values())
        check('AC2/later-read', 'a later Claude Code run loads the index Codex updated and reads the new file',
              (reader.get('init') or {}).get('index') == after_codex.decode()
              and any(r[0] == 'Read' and r[1].get('file_path') == str(Path(directory) / rule_codex[0])
                      and r[2] == rule_codex[1] for r in reads)
              and [t.get('outcome') for t in later] == ['completed'])

        # ---- AC3: the launch line and every memory file read and write in the record ------------------------------
        for identity, loaded in (('claude-one', before), ('claude-two', before), ('codex-writer', before_codex),
                                 ('claude-later', after_codex)):
            line = launch_line(identity) or {}
            check('AC3/loaded-at-launch', '%s: the launch line names the directory, the form and the index digest as '
                  'loaded [%s]' % (identity, line),
                  line.get('directory') == directory and line.get('form') and line.get('index_digest') == sha(loaded)
                  and line.get('memory_revision') == 1
                  and (line.get('qualification') or {}).get('version') in (claude_version, codex_version))
        check('AC3/loaded-at-launch', 'the editing run\'s launch line has the index before it, the next run\'s the '
              'index after it, and they differ',
              (launch_line('codex-writer') or {}).get('index_digest') == sha(before_codex)
              and (launch_line('claude-later') or {}).get('index_digest') == sha(after_codex)
              and sha(before_codex) != sha(after_codex))
        forms_used = {(launch_line(i) or {}).get('form') for i in ('claude-one', 'codex-writer')}
        check('AC3/loaded-at-launch', 'the form named is each engine\'s own [%s]' % sorted(filter(None, forms_used)),
              forms_used == {getattr(C, 'FILE_MEMORY_FORM', 'absent'), getattr(X, 'FILE_MEMORY_FORM', 'absent')})

        def tool_lines(identity):
            calls, results = {}, {}
            for stream, event in record_events(identity):
                if stream != 'engine' or not isinstance(event, dict):
                    continue
                for block in ((event.get('message') or {}).get('content') or []) if event.get('type') in ('assistant', 'user') else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        calls[block['id']] = (block['name'], block['input'])
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        results[block['tool_use_id']] = block['content']
                item = event.get('item') or {}
                if event.get('type') == 'item.completed' and item.get('type') in ('file_change', 'command_execution'):
                    calls[item['id']] = (item['type'], item.get('changes') or item.get('command'))
                    results[item['id']] = item.get('status') if item['type'] == 'file_change' else item.get('aggregated_output')
            return {k: (v[0], v[1], results.get(k)) for k, v in calls.items()}
        for identity, value in (('claude-one', one), ('claude-two', two), ('claude-later', reader)):
            made = (value.get('memory') or {})
            kept_lines = tool_lines(identity)
            check('AC3/tool-lines', '%s: every memory file read, write and edit is a tool call line with its input and '
                  'result [%d made, %d kept]' % (identity, len(made), len(kept_lines)),
                  bool(made) and all(uid in kept_lines and kept_lines[uid][0] == call[0] and kept_lines[uid][1] == call[1]
                                     and kept_lines[uid][2] == call[2] for uid, call in made.items()))
        codex_lines = tool_lines('codex-writer')
        check('AC3/tool-lines', 'codex-writer: its index read and its file change are item lines with their input and '
              'result', codex_lines.get('memory-write', (None,))[0] == 'file_change'
              and codex_lines['memory-write'][2] == 'completed'
              and [c['path'] for c in codex_lines['memory-write'][1]] == [str(Path(directory) / rule_codex[0]), str(index)]
              and codex_lines.get('memory-read', (None, None, None))[2] == before_codex.decode())

        events_text = json.dumps([launch.messages for launch in launched if getattr(launch, 'messages', None)])
        line_text = json.dumps([launch_line(i) for i in ('claude-one', 'codex-writer', 'claude-later')])
        receipts = list((Path(config['state_root']) / 'memory' / 'launches').glob('*.json'))
        receipt_text = ''.join(p.read_text() for p in receipts)
        content = [rule_claude[1].strip(), rule_codex[1].strip(), 'Synthetic index']
        check('AC3/no-content', 'no launch event, launch line or memory receipt carries memory content',
              bool(receipts) and not any(c in events_text or c in line_text or c in receipt_text for c in content))
        reported = next((m['baseline'] for m in messages('codex-writer', 'baseline')), {})
        check('AC3/no-content', 'the Codex baseline report names its developer instructions by digest only',
              any(o.startswith('developer_instructions=<sha256:') for o in reported.get('options') or [])
              and reported.get('file_memory', {}).get('directory') == directory)
        handed_events = [m for launch in launched for m in (getattr(launch, 'messages', None) or [])
                         if isinstance(m, dict) and m.get('event') == 'file_memory']
        per_engine = {}
        for event in handed_events:
            for engine, count in ((event.get('metrics') or {}).get('file_memory_runs') or {}).items():
                per_engine[engine] = per_engine.get(engine, 0) + count
        check('AC3/observability', 'runs handed the file memory are counted per engine [%s]' % per_engine,
              per_engine.get('claude_code', 0) >= 3 and per_engine.get('codex', 0) >= 1
              and all(e.get('memory_revision') == 1 and e.get('index_digest') and e.get('qualification') for e in handed_events))
        check('AC3/observability', 'a run stopped for a memory path mismatch is counted [%s]'
              % [s.get('metrics') for s in stops],
              [(s.get('metrics') or {}).get('file_memory_mismatch_stops') for s in stops] == [1])
        receipt = next((json.loads(p.read_text()) for p in receipts
                        if json.loads(p.read_text()).get('dispatch_id') == getattr(launch_of('codex-writer'), 'dispatch_id', None)), {})
        check('AC3/observability', 'the durable memory receipt binds the handoff to the record revision and the '
              'qualification', (receipt.get('file_memory') or {}).get('index_digest') == sha(before_codex)
              and receipt.get('revision') == 1)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        if factory is not None:
            try:
                running = list(factory.conversation.runner.launches.values())
                for launch in running:
                    launch.stop('requested')
                F.drive(factory, lambda: all(launch.ended for launch in running), 20)
            except Exception:  # noqa: BLE001
                pass
        if lock is not None:
            close = getattr(lock, 'close', None)
            if close:
                close()
        for value in fixtures:
            value['authority'].conn.close()
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0184 detail:', row, '; '.join(failed))
        expect('VELDO-0184 ' + row, bool(rows[row]) and not failed)


_v184_suite()
