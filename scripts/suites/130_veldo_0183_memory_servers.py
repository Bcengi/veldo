"""VELDO-0183: the owner's ava-memory, knowledge graph, claude-mem and memory_kb servers are catalog MCP servers over
the one memory store, every ChromaDB write goes through one store server per store, no server is handed a paid
model API, and every memory call is in the run's record.

Run: python3 scripts/selftest.py --suite 130_veldo_0183_memory_servers

Only shared ROOT and expect are consumed. VELDO-0171's installed-host fixture, reused through proof/VELDO-0185/fixture.py
as suite 129 reuses it, lays a host down with the real setup module, into scratch, with that fixture's user manager
stand-in (which runs each unit's ExecStart and waits for its READY=1), Tailscale stand-in and loopback Bot API. The
owner's memory is proof/VELDO-0183/fixtures.py's synthetic stores under scratch: a FastMCP stand-in, a
Chroma-like store that loses writes when two processes open it, the knowledge graph's WAL SQLite and a claude-mem
search server. The engines are one generated fake: it answers each engine's login status and, for the subscription
extraction behind smart add, prints facts as Claude Code's JSON output prints a result. Conversation turns are a
generated fake engine that starts the MCP servers its configuration names, prints an init event and each tool call
in Claude Code's stream JSON shapes; its output is kept by the real execution record (VELDO-0141). Credentials go to
a fake keystore. No real engine, login, paid API, keyring, memory store or memory server is read or started.
"""


def _v183_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import sqlite3
    import subprocess
    import sys
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which setup installs and every server, bridge and command here runs) takes each of them.
    PRODUCTION = {
        'control_memory_servers.py': ROOT / ".veldo" / "control_memory_servers.py",
        'control_memory_store.py': ROOT / ".veldo" / "control_memory_store.py",
        'control_memory_kb.py': ROOT / ".veldo" / "control_memory_kb.py",
        'control_mcp_catalog.py': ROOT / ".veldo" / "control_mcp_catalog.py",
        'control_factory_setup_memory.py': ROOT / ".veldo" / "control_factory_setup_memory.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    ROWS = ('AC1/catalog-records', 'AC1/role-selections', 'AC1/init', 'AC1/real-layout', 'AC1/setup-step',
            'AC2/paid-api', 'AC2/smart-add', 'AC2/tools-work',
            'AC3/record', 'AC3/cross-conversation', 'AC3/own-copy-falsifier',
            'AC4/store-units', 'AC4/open-refused', 'AC4/assistant-entries', 'AC4/one-opener', 'AC4/all-written',
            'observability')
    rows = {name: [] for name in ROWS}
    FOUR = ('ava-memory', 'knowledge-graph', 'claude-mem', 'memory-kb')

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def refusal(call):
        try:
            call()
        except Exception as error:  # noqa: BLE001
            return getattr(error, 'code', type(error).__name__ + ': ' + str(error)[:200])
        return None

    here = Path(__suite_file__).resolve().parents[2]
    helper = load('v183_setup_fixture', here / 'proof/VELDO-0185/fixture.py')
    FIX = load('v183_fixtures', here / 'proof/VELDO-0183/fixtures.py')
    # One generated executable serves both engines (Codex when its path names codex): each login status, and Claude
    # Code's print mode with JSON output for the extraction, which notes its profile and whether a paid-API key
    # reached it, then answers each sentence of its input as one fact.
    fake = r'''#!@@PYTHON@@ -B
import json, os, sys
from pathlib import Path
if sys.argv[1:3] == ['auth', 'status']:
    logged = (Path(os.environ.get('CLAUDE_CONFIG_DIR') or '/nonexistent') / '.credentials.json').is_file()
    sys.stdout.write(json.dumps({'loggedIn': logged, 'authMethod': 'claude.ai' if logged else 'none',
                                 'apiProvider': 'firstParty'}, indent=2) + chr(10))
    sys.exit(0 if logged else 1)
if sys.argv[1:3] == ['login', 'status']:
    logged = (Path(os.environ.get('CODEX_HOME') or '/nonexistent') / 'auth.json').is_file()
    sys.stderr.write(('Logged in using ChatGPT' if logged else 'Not logged in') + chr(10))
    sys.exit(0 if logged else 1)
if '-p' in sys.argv and 'json' in sys.argv:
    text = sys.stdin.read()
    profile = os.environ.get('CLAUDE_CONFIG_DIR')
    with open(Path(profile) / 'extractions.log', 'a') as out:
        out.write(json.dumps({'profile': profile, 'paid': sorted(n for n in os.environ if n.endswith('_API_KEY'))}) + chr(10))
    facts = [s.strip() for s in text.split('.') if s.strip()]
    sys.stdout.write(json.dumps({'type': 'result', 'subtype': 'success', 'result': json.dumps({'facts': facts})}))
    sys.exit(0)
sys.exit(2)
'''.replace('@@PYTHON@@', sys.executable)
    ACCOUNTS = (('claude-a', 'claude_code'), ('claude-b', 'claude_code'), ('codex-a', 'codex'))
    # A conversation turn: starts each server its MCP configuration names as Claude Code starts a stdio server,
    # prints the init event listing them with every tool each registers, then each planned call as a tool use and
    # its tool result, in Claude Code's stream JSON shapes.
    turn_engine = r'''import json, os, subprocess, sys
config, plan = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
def emit(value):
    sys.stdout.write(json.dumps(value) + chr(10)); sys.stdout.flush()
def rpc(proc, message):
    proc.stdin.write(json.dumps(message) + chr(10)); proc.stdin.flush()
    if 'id' not in message:
        return {}
    for line in proc.stdout:
        answer = json.loads(line)
        if answer.get('id') == message['id']:
            return answer
    return {}
servers, events = {}, []
for name, entry in sorted(config['mcpServers'].items()):
    env = {k: os.environ[k] for k in ('PATH', 'HOME') if k in os.environ}
    env.update(entry.get('env') or {})
    proc = subprocess.Popen([entry['command']] + entry['args'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env, text=True)
    init = rpc(proc, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18',
                      'capabilities': {}, 'clientInfo': {'name': 'fake', 'version': '1'}}})
    rpc(proc, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    listed = rpc(proc, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}})
    tools = [t['name'] for t in (listed.get('result') or {}).get('tools') or []]
    servers[name] = (proc, tools, 'connected' if 'result' in init and 'result' in listed else 'failed')
emit({'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'session_id': plan['session'],
      'tools': plan['native'] + ['mcp__%s__%s' % (n, t) for n, (_, tools, _) in sorted(servers.items()) for t in tools],
      'mcp_servers': [{'name': n, 'status': s} for n, (_, _, s) in sorted(servers.items())],
      'slash_commands': [], 'skills': [], 'plugins': [], 'model': plan.get('model')})
for index, (server, tool, arguments) in enumerate(plan['calls']):
    use = 'toolu_%s_%d' % (plan['session'], index)
    emit({'type': 'assistant', 'message': {'id': 'msg_%d' % index, 'role': 'assistant', 'content': [
        {'type': 'tool_use', 'id': use, 'name': 'mcp__%s__%s' % (server, tool), 'input': arguments}]}})
    answer = rpc(servers[server][0], {'jsonrpc': '2.0', 'id': 100 + index, 'method': 'tools/call',
                                     'params': {'name': tool, 'arguments': arguments}}) if server in servers else {}
    result = answer.get('result') or {}
    emit({'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'tool_result', 'tool_use_id': use, 'is_error': bool(result.get('isError') or 'error' in answer),
         'content': result.get('content') or [{'type': 'text', 'text': json.dumps(answer.get('error'))}]}]}})
emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'done', 'session_id': plan['session']})
for proc, _, _ in servers.values():
    proc.stdin.close(); proc.wait(10)
'''

    class Keystore:
        """The fake keystore the credential writer stores into: values by reference, never the real keyring."""

        def __init__(self):
            self.values = {}

        def set(self, name, value):
            self.values[name] = value

        def delete(self, name):
            self.values.pop(name, None)

    def exercise(h):
        base, CEN, mods = h['base'], h['CEN'], h['mods']
        AR = load('v183_accounts', mods / 'accounts.py')
        MS = load('v183_servers', mods / 'control_memory_servers.py')
        CG = load('v183_config', mods / 'control_agent_config.py')
        HANDOFF = load('v183_handoff', mods / 'control_agent_config_handoff.py')
        CONV = load('v183_conversation', mods / 'control_conversation.py')
        ER = load('v183_record', mods / 'control_execution_record.py')
        S, IN, ACT = h['claims'].S, h['IN'], load('v183_activation', mods / 'control_channel_activation.py')
        owner, owner_key = h['owner'], h['owner_key']
        root, workspace = h['fresh_root']('state-v183'), h['clone']('clone-v183')
        registry = os.path.join(CEN.git_common_dir(str(workspace)), 'veldo')
        profiles = {}
        for name, provider in ACCOUNTS:
            profile = base / 'profiles' / name
            profile.mkdir(parents=True, mode=0o700)
            (profile / ('.credentials.json' if provider == 'claude_code' else 'auth.json')).write_text('{}\n')
            AR.account_add(name, config_dir=str(profile), root=registry, provider=provider)
            profiles[name] = profile
        h['ts'].set('ready')
        units = base / 'units-v183'
        manager = h['Manager'](units)
        h['managers'].append(manager)
        code, report = h['setup'](root, workspace, base / 'trust-v183' / 'host.json', base / 'install-v183', units,
                                  manager)
        print('  VELDO-0183 setup:', code, report.get('outcome'), report.get('reason'))
        if code != 0 or report.get('outcome') != 'set_up':
            for row in ROWS:
                check(row, 'setup laid the host down [%s %s]' % (report.get('outcome'), report.get('reason')), False)
            return
        root = Path(report['state_root'])
        # The writers the store binds its records to are the installed engine's, as setup's own store steps use.
        installed = Path(report['home']) / 'bin'
        MC = load('v183_catalog', installed / 'control_mcp_catalog.py')
        MEM = load('v183_memory', installed / 'control_memory.py')
        CRED = load('v183_credential', installed / 'control_credential.py')
        store_path = Path(report['store'])
        laid = json.loads((root / 'host' / 'ingress.json').read_text())
        ids = laid['authority_ids']
        domain, repository = ids['domain_uuid'], ids['repository_uuid']
        principal, journal_sign = IN.journal_signer(laid['journal'])
        owner_sign = ACT.ssh_signer(str(owner_key))
        host = socket.gethostname()

        # THE OWNER'S MEMORY: the fixture stores, the memory record by his signed command (VELDO-0182), and memory_kb's
        # passphrase saved as a credential of his.
        manifest = FIX.build(base / 'stores', host)
        definition = MEM.normalize(manifest)
        original_assistant = Path(manifest['assistant_mcp']).read_bytes()
        keystore = Keystore()
        passphrase = 'kb-passphrase-' + os.urandom(12).hex()
        conn = S.open_store(str(store_path))
        try:
            command = dict(ids, command_id='v183-memory-record', operation=MEM.SAVE, principal=owner,
                           parameters=dict(definition=definition, base=0))
            MEM.Memory(S, conn, ids, principal, journal_sign).admit(
                dict(command=command, signature=owner_sign(S.canonical_bytes(command))))
            credentials = CRED.Credentials(S, conn, domain=domain, repository=repository, signer=principal,
                                           sign=journal_sign, keystore=keystore)
            credentials.apply(CRED.SET, dict(id='JARVIS_PASSPHRASE', base=0, label='memory_kb', value=passphrase),
                              principal=owner, command_id='v183-credential-kb')
            credentials.apply(CRED.SET, dict(id='ANTHROPIC_API_KEY', base=0, label='paid', value='sk-not-real'),
                              principal=owner, command_id='v183-credential-paid')
        finally:
            conn.close()

        # THE SERVERS STEP, as `veldo memory servers` runs it: with the host's user manager stand-in and unit dir.
        events = []
        step = MS.setup_servers(root, str(owner_key), runner=manager, unit_dir=str(units),
                                install_root=str(base / 'install-v183'), python=sys.executable, factory=str(mods),
                                host=host, observe=events.append)
        print('  VELDO-0183 servers step:', step['outcome'], step['catalog'], step['roles'])
        conn = sqlite3.connect('file:%s?mode=ro' % store_path, uri=True, timeout=30)
        try:
            records = {}
            for server in FOUR:
                head = MC.entity(conn, MC.head_id(domain, server))
                records[server] = MC.entity(conn, MC.revision_id(domain, server, head['data']['revision']))['data'] \
                    if head else None
            bound = {}
            for role in ('assistant', 'assistant_codex'):
                with contextlib.suppress(Exception):
                    bound[role] = CONV.role_at(conn, role)[1]
        finally:
            conn.close()
        memory_revision = step['memory_revision']
        factory_module = str(mods / 'control_factory_setup_memory.py')
        mem, graph, kb, plugin = (definition['parts'][p] for p in ('ava_memory', 'knowledge_graph', 'memory_kb',
                                                                    'claude_mem'))

        # ---- AC1: the four catalog records and the roles' selections ----
        check('AC1/catalog-records', 'the four records are saved [%s]' % sorted(s for s, r in records.items() if r),
              all(records.values()))
        if not all(records.values()):
            for row in ROWS:
                check(row, 'the servers step saved the records', False)
            return
        ava, kg, cm, mkb = (records[s] for s in FOUR)
        check('AC1/catalog-records', 'ava-memory is the bridge to the mem0_memory store server [%s]' % ava['arguments'],
              ava['command'] == sys.executable and ava['arguments'][:5] == ['-B', factory_module, 'bridge', 'ava_memory',
                                                                          '--state-root']
              and ava['arguments'][ava['arguments'].index('--catalog-revision') + 1] == str(ava['revision'])
              and ava['arguments'][ava['arguments'].index('--memory-revision') + 1] == str(memory_revision))
        check('AC1/catalog-records', 'knowledge-graph is its interpreter running its mcp_server.py',
              kg['command'] == graph['interpreter'] and kg['arguments'] == [str(Path(graph['code']) / 'mcp_server.py')])
        check('AC1/catalog-records', 'claude-mem is its search server\'s command from the manifest',
              [cm['command']] + cm['arguments'] == plugin['command'])
        check('AC1/catalog-records', 'memory-kb is the bridge to the memory_kb store server, its passphrase the '
              'record\'s credential reference',
              mkb['arguments'][:4] == ['-B', factory_module, 'bridge', 'memory_kb']
              and mkb['environment'] == {'JARVIS_PASSPHRASE': {'reference': CRED.reference(domain, 'JARVIS_PASSPHRASE')}})
        check('AC1/catalog-records', 'every record is a stdio record on this host, with no literal in its environment',
              all(r['transport'] == 'stdio' and r['hosts'] == [host]
                  and all('reference' in v for v in r['environment'].values()) for r in records.values()))
        KBM = load('v183_kb', mods / 'control_memory_kb.py')
        check('AC1/catalog-records', 'memory-kb\'s tools are its subcommands but setup-passphrase',
              sorted(t['name'] for t in KBM.tools()) == sorted(['search', 'index-file', 'index-dir', 'index-telegram',
                                                                'stats', 'list', 'delete', 'clear']))
        # The module layout memory_kb's cli.py imports and ava-memory's mcp_server.py tools, as the lead read them
        # from the owner's code. Every function a memory-kb tool reaches must be one of these, and the fixture is
        # built to exactly this layout, so a tool mapped to a function the real code does not have fails here.
        REAL_KB = {('search', 'kb.store', 'search'), ('search', 'kb.store', 'search_all'),
                   ('index-file', 'kb.indexers.file', 'index_file'),
                   ('index-dir', 'kb.indexers.file', 'index_directory'),
                   ('index-telegram', 'kb.indexers.telegram', 'index_conversation'),
                   ('stats', 'kb.store', 'get_stats'), ('list', 'kb.store', 'list_documents'),
                   ('delete', 'kb.store', 'delete'), ('clear', 'chromadb', 'PersistentClient.delete_collection')}
        REAL_SIGNATURES = {'kb.store.list_documents': ['collection', 'limit'], 'kb.store.delete': ['collection', 'doc_id'],
                           'kb.indexers.telegram.index_conversation': ['message', 'metadata', 'classification']}
        REAL_AVA = {'memory_search': "(query, limit=10, category='')",
                    'memory_add': "(text, category='general', source='')", 'memory_add_smart': '(text)',
                    'memory_stats': '()', 'memory_delete': '(memory_id)', 'memory_get_all': '(limit=50)'}
        mapped = set(KBM.targets())
        check('AC1/real-layout', 'every memory-kb tool maps to a function memory_kb\'s cli.py calls [not real: %s; '
              'missing: %s]' % (sorted(mapped - REAL_KB), sorted(REAL_KB - mapped)), mapped == REAL_KB)
        probe = base / 'layout-probe.py'
        probe.write_text(r'''import importlib, inspect, json, os, sys
code, part = sys.argv[1], sys.argv[2]
sys.path.insert(0, code); os.chdir(code)
out = {}
if part == 'memory_kb':
    for tool, module, attribute in json.loads(sys.argv[3]):
        try:
            target = importlib.import_module(module)
            for name in attribute.split('.'):
                target = getattr(target, name)
            out['%s.%s' % (module, attribute)] = list(inspect.signature(target).parameters)
        except Exception as error:
            out['%s.%s' % (module, attribute)] = 'missing: %s' % error
    gone = []
    for module, attribute in (('kb.indexer', None), ('kb.store', 'stats'), ('kb.store', 'delete_document'),
                              ('kb.store', 'clear_collection')):
        try:
            found = importlib.import_module(module)
            if attribute is None or hasattr(found, attribute):
                gone.append('%s.%s' % (module, attribute))
        except ImportError:
            pass
    out['guessed_names_present'] = gone
else:
    import mcp_server
    out = {name: str(inspect.signature(fn)) for name, (fn, _) in mcp_server.mcp._tools.items()}
    out['server_name'] = mcp_server.mcp.name
print(json.dumps(out))
''')
        layout = {}
        for part in ('memory_kb', 'ava_memory'):
            done = subprocess.run([definition['parts'][part]['interpreter'], '-B', str(probe),
                                   definition['parts'][part]['code'], part, json.dumps(sorted(KBM.targets()))],
                                  capture_output=True, text=True, timeout=120)
            layout[part] = json.loads(done.stdout or '{}')
        kb_layout = layout['memory_kb']
        check('AC1/real-layout', 'each function a memory-kb tool reaches resolves in the fixture kb package, built to '
              'the real layout [%s]' % kb_layout,
              len([k for k in kb_layout if k != 'guessed_names_present']) == len(REAL_KB)
              and not [v for v in kb_layout.values() if isinstance(v, str)]
              and all(kb_layout.get(k, [])[:len(v)] == v for k, v in REAL_SIGNATURES.items()))
        check('AC1/real-layout', 'the fixture carries none of the guessed names the real code does not have [%s]'
              % kb_layout.get('guessed_names_present'), kb_layout.get('guessed_names_present') == [])
        check('AC1/real-layout', 'the fixture ava-memory is FastMCP ava-memory with mcp_server.py\'s six tools and '
              'their signatures [%s]' % layout['ava_memory'],
              layout['ava_memory'] == dict(REAL_AVA, server_name='ava-memory'))
        for role, engine in (('assistant', 'claude_code'), ('assistant_codex', 'codex')):
            revision = bound.get(role) or {}
            memory = [m for m in revision.get('mcp') or [] if m['server'] in FOUR]
            check('AC1/role-selections', '%s selects all four, every tool, always, at their saved revisions [%s]'
                  % (role, memory),
                  revision.get('engine') == engine and sorted(m['server'] for m in memory) == sorted(FOUR)
                  and all(m['tools'] == 'all' and m['load'] == 'always' and m['revision'] == records[m['server']]['revision']
                          for m in memory))
            check('AC1/role-selections', '%s\'s selection is a new role revision the default team names' % role,
                  revision.get('revision', 0) >= 2 and revision.get('previous'))
        check('AC1/role-selections', 'one default team revision names both new role revisions',
              any(s.startswith('default_team:') for s in step['roles']))

        # The turns: each engine's MCP configuration from the role's selections and the catalog, as the receiver
        # hands it (a credential reference resolved from the keystore), and the run's record kept by VELDO-0141.
        engine_path = base / 'turn-engine.py'
        engine_path.write_text(turn_engine)

        def config_of(revision, catalog=None):
            catalog = catalog or records
            servers = {}
            for item in revision['mcp']:
                record = catalog[item['server']]
                env = {}
                for name, value in record['environment'].items():
                    env[name] = value['literal'] if 'literal' in value else keystore.values[value['reference'].split(':', 1)[1]]
                servers[item['server']] = {'command': record['command'], 'args': record['arguments'], 'env': env}
            return {'mcpServers': servers}

        def turn(name, account, revision, calls, catalog=None):
            """One turn on `account`: its record lines and the tool results by call index."""
            directory = base / 'turns' / name
            directory.mkdir(parents=True)
            (directory / 'mcp.json').write_text(json.dumps(config_of(revision, catalog)))
            native = [t['name'] for t in revision['native_tools']]
            (directory / 'plan.json').write_text(json.dumps(dict(session=name, native=native, calls=calls,
                                                                 model=revision['settings'].get('model'))))
            env = {k: os.environ[k] for k in ('PATH', 'HOME') if k in os.environ}
            env['CLAUDE_CONFIG_DIR' if 'codex' not in account else 'CODEX_HOME'] = str(profiles[account])
            resolved = ER.Resolved()
            resolved.add('mcp_credential', passphrase)
            recorder = ER.Recorder(directory / 'records', dict(dispatch_id='turn-' + name, contract_digest='sha256:0',
                                                              unit='u', station='s', project='p', account=account,
                                                              host=host), resolved)
            proc = subprocess.run([sys.executable, '-B', str(engine_path), str(directory / 'mcp.json'),
                                   str(directory / 'plan.json')], capture_output=True, env=env, timeout=600)
            recorder.feed('engine', proc.stdout)
            recorder.close()
            lines = [json.loads(l) for l in Path(recorder.path).read_text().splitlines()]
            # What the engine printed, as the receiver reads it before it keeps a line, and the record of it.
            printed = proc.stdout.decode().splitlines()
            events = [json.loads(l) for l in printed]
            results = [b for e in events if e.get('type') == 'user' for b in e['message']['content']]
            texts = [' '.join(c.get('text', '') for c in r['content']) for r in results]
            return dict(lines=lines, printed=printed, events=events, results=results, texts=texts,
                        stderr=proc.stderr, resolved=resolved)

        # ---- AC1: the init event of a turn on each engine lists the four connected, with every tool each has ----
        for role in ('assistant', 'assistant_codex'):
            revision = bound[role]
            capability = {'revision': dict(revision, native_tools=[t['name'] for t in revision['native_tools']]),
                          'skills': []}
            servers = [records[m['server']] for m in revision['mcp']]
            for server in servers:
                for name, value in server['environment'].items():
                    value.clear()
                    value['literal'] = keystore.values[CRED.reference(domain, 'JARVIS_PASSPHRASE').split(':', 1)[1]]
            try:
                inventory = HANDOFF.inventory(capability, servers)
                wanted = HANDOFF.expected(capability, inventory)
            except Exception as error:  # noqa: BLE001
                inventory, wanted = {}, {'error': getattr(error, 'code', str(error))}
            finally:
                for server in servers:
                    for name, value in server['environment'].items():
                        value.clear()
                        value['reference'] = CRED.reference(domain, 'JARVIS_PASSPHRASE')
            done = turn('init-' + role, 'claude-a' if role == 'assistant' else 'codex-a', revision, [])
            init = next((e for e in done['events'] if e.get('subtype') == 'init'), {})
            listed = {s['name']: s['status'] for s in init.get('mcp_servers') or []}
            print('  VELDO-0183 AC1 %s init servers: %s extra %s missing %s' % (role, listed,
                  sorted(set(init.get('tools') or []) - set(wanted.get('tools') or [])),
                  sorted(set(wanted.get('tools') or []) - set(init.get('tools') or []))))
            check('AC1/init', '%s: the init event lists the four servers, each connected [%s]' % (role, listed),
                  listed == {s: 'connected' for s in FOUR})
            check('AC1/init', '%s: every tool each server registers is offered, as the role revision expects [%s %s]'
                  % (role, wanted.get('error'), HANDOFF.difference(init, wanted) if 'error' not in wanted else ''),
                  inventory and set(inventory) == set(FOUR)
                  and all(entry['tools'] == entry['offered'] and entry['offered'] for entry in inventory.values())
                  and HANDOFF.difference(init, wanted) is None)

        # ---- AC2: no paid-API name in any catalog record ----
        lock = h['F'].take_lock(str(root))
        conn = S.open_store(str(store_path))
        try:
            catalog = MC.Catalog(S, conn, domain=domain, repository=repository, signer=principal, sign=journal_sign)
            head = MC.entity(conn, MC.head_id(domain, 'ava-memory'))['data']['revision']
            paid_ref = dict(ava, environment={'ANTHROPIC_API_KEY': {'reference': CRED.reference(domain, 'ANTHROPIC_API_KEY')}})
            paid_ref.pop('revision')
            code_ref = refusal(lambda: catalog.save(paid_ref, principal=owner, base=head, command_id='v183-paid-1'))
            renamed = dict(paid_ref, environment={'MEM0_EXTRACTOR': {'reference': CRED.reference(domain, 'ANTHROPIC_API_KEY')}})
            code_named = refusal(lambda: catalog.save(renamed, principal=owner, base=head, command_id='v183-paid-2'))
            other = dict(id='weather', label='weather', transport='stdio', command='/bin/true', arguments=[], url=None,
                         environment={'OPENAI_API_KEY': {'literal': '~/no-key-here'}}, headers={}, hosts=[host],
                         read_only_tools=[])
            code_other = refusal(lambda: catalog.save(other, principal=owner, base=0, command_id='v183-paid-3'))
            after = MC.entity(conn, MC.head_id(domain, 'ava-memory'))['data']['revision']
            saved_other = MC.entity(conn, MC.head_id(domain, 'weather'))
            refused_events = [o for o in catalog.observations if o.get('outcome') == 'refused']
        finally:
            conn.close()
            os.close(lock)
        print('  VELDO-0183 AC2 refusals:', code_ref, code_named, code_other)
        check('AC2/paid-api', 'ava-memory with ANTHROPIC_API_KEY as its credential is refused by name, no revision saved',
              code_ref == 'invalid_input:mcp_server:paid_api:ANTHROPIC_API_KEY' and after == head)
        check('AC2/paid-api', 'a reference to the saved ANTHROPIC_API_KEY credential under another name is refused too',
              code_named == 'invalid_input:mcp_server:paid_api:ANTHROPIC_API_KEY')
        check('AC2/paid-api', 'for every catalog record, not only memory: OPENAI_API_KEY in another server refused',
              code_other == 'invalid_input:mcp_server:paid_api:OPENAI_API_KEY' and saved_other is None)
        check('AC2/paid-api', 'each refusal is observed by name',
              len(refused_events) == 3 and MS.metrics([], refused_events)['catalog_paid_api_refused'] == 3)

        # ---- AC2, AC3: a conversation's turn calls every memory tool; smart add on the subscription ----
        check('AC2/smart-add', 'no paid-API key anywhere in the suite\'s environment',
              not [n for n in os.environ if n in MC.paid_api_names() and n.endswith(('_API_KEY', '_AUTH_TOKEN'))])
        doc = base / 'session-summary.md'
        doc.write_text('Last week session summary: the deploy moved to Fridays. Unlock with %s.' % passphrase)
        notes = base / 'notes'
        notes.mkdir()
        (notes / 'a.md').write_text('Directory note alpha')
        calls_a = [
            ['ava-memory', 'memory_add', {'text': 'Rule from conversation A: tests before merge'}],
            ['ava-memory', 'memory_add_smart', {'text': 'The owner prefers short replies. The build runs at night.'}],
            ['ava-memory', 'memory_search', {'query': 'tests before merge'}],
            ['ava-memory', 'memory_stats', {}],
            ['ava-memory', 'memory_get_all', {'limit': 5}],
            ['ava-memory', 'memory_delete', {'memory_id': 'seed-memory'}],
            ['knowledge-graph', 'kg_add_entity', {'type': 'Decision', 'name': 'Conversation A decision',
                                                  'description': 'Graph fact from conversation A'}],
            ['knowledge-graph', 'kg_search', {'query': 'Graph fact from conversation A'}],
            ['memory-kb', 'index-file', {'path': str(doc)}],
            ['memory-kb', 'index-dir', {'path': str(notes), 'collection': 'research'}],
            ['memory-kb', 'index-telegram', {'message': 'Telegram thread about the garden', 'chat_id': '5590171',
                                             'classification': 'personal'}],
            ['memory-kb', 'search', {'query': 'deploy moved to Fridays'}],
            ['memory-kb', 'search', {'query': 'Directory note alpha', 'collection': 'research'}],
            ['memory-kb', 'stats', {}],
            ['memory-kb', 'list', {'collection': 'files', 'limit': 50}],
            ['memory-kb', 'delete', {'collection': 'files', 'doc_id': 'seed-document'}],
            ['memory-kb', 'clear', {'collection': 'research'}],
            ['memory-kb', 'search', {'query': 'Directory note alpha', 'collection': 'research'}],
            ['claude-mem', 'search', {'query': 'flaky build'}],
            ['claude-mem', 'get_observations', {'ids': '1'}],
        ]
        # The falsifier's own copy of the data directories, taken before conversation A writes: what a conversation
        # handed its own copy would read.
        copy_root = base / 'stores-copy'
        shutil.copytree(base / 'stores', copy_root, symlinks=True,
                        ignore=shutil.ignore_patterns('veldo-store.lock', '__pycache__'))
        copied = {}
        for server in ('ava-memory', 'knowledge-graph'):
            copied[server] = json.loads(json.dumps(records[server]).replace(str(base / 'stores'), str(copy_root)))
        copied['ava-memory'] = dict(copied['ava-memory'], command=str(copy_root / 'python'),
                                    arguments=['-B', str(copy_root / 'mem0_memory' / 'mcp_server.py')])
        a = turn('conversation-a', 'claude-a', bound['assistant'], calls_a)
        for (server, tool, _), result, text in zip(calls_a, a['results'], a['texts']):
            check('AC2/tools-work', '%s %s answers without error [%s]' % (server, tool, text[:120]),
                  not result['is_error'])
        check('AC2/tools-work', 'every call was answered', len(a['results']) == len(calls_a))
        searched = [n for n, c in enumerate(calls_a) if c[:2] == ['memory-kb', 'search'] and c[2].get('collection')]
        check('AC2/tools-work', 'memory_kb search in one collection found the directory note, and after clear '
              'nothing [%s]' % [a['texts'][n][:80] for n in searched if n < len(a['texts'])],
              len(searched) == 2 and len(a['texts']) == len(calls_a) and 'Directory note alpha' in a['texts'][searched[0]]
              and json.loads(a['texts'][searched[1]] or 'null') == [])
        smart = a['texts'][1] if len(a['texts']) > 1 else ''
        extraction = {}
        with contextlib.suppress(ValueError, IndexError, KeyError, TypeError):
            extraction = json.loads(a['results'][1]['content'][0]['text'])['extraction']
        receipts = [json.loads(p.read_text()) for p in sorted((root / 'memory' / 'extractions').glob('*.json'))] \
            if (root / 'memory' / 'extractions').is_dir() else []
        logged = [json.loads(l) for name, _ in ACCOUNTS for l in
                  ((profiles[name] / 'extractions.log').read_text().splitlines()
                   if (profiles[name] / 'extractions.log').is_file() else [])]
        print('  VELDO-0183 AC2 smart add:', smart[-300:], extraction, receipts and receipts[-1].get('account'))
        verify_a = turn('verify-smart', 'claude-b', bound['assistant'],
                        [['ava-memory', 'memory_search', {'query': 'The owner prefers short replies'}],
                         ['ava-memory', 'memory_search', {'query': 'The build runs at night'}]])
        check('AC2/smart-add', 'memory_add_smart saved both extracted memories [%s]' % verify_a['texts'],
              len(verify_a['texts']) == 2 and 'prefers short replies' in verify_a['texts'][0]
              and 'runs at night' in verify_a['texts'][1])
        check('AC2/smart-add', 'its extraction is a run on a registered Claude Code subscription account [%s]'
              % receipts,
              len(receipts) == 1 and receipts[0]['outcome'] == 'done' and receipts[0]['engine'] == 'claude_code'
              and receipts[0]['account'] in ('claude-a', 'claude-b') and receipts[0]['facts'] == 2
              and extraction.get('run') == receipts[0]['run'] and extraction.get('account') == receipts[0]['account']
              and receipts[0]['account'] in [c['account'] for c in receipts[0]['selection']['candidates']])
        check('AC2/smart-add', 'Claude Code ran in that account\'s profile and no paid-API key reached it [%s]' % logged,
              len(logged) == 1 and receipts and logged[0]['profile'] == str(profiles[receipts[0]['account']])
              and logged[0]['paid'] == [] and receipts[0]['paid_api_names_handed'] == [])

        # ---- AC3: every call in the record; another conversation and the assistant find A's writes ----
        uses = [b for e in a['events'] if e.get('type') == 'assistant' for b in e['message']['content']
                if b.get('type') == 'tool_use']
        kept = [l for l in a['lines'][1:] if l.get('stream') == 'engine']
        check('AC3/record', 'the turn\'s record keeps every line the engine printed, each redacted as every line is',
              [l['payload'] for l in kept] == [ER.redact(line, a['resolved'])[0] for line in a['printed']])
        check('AC3/record', 'each memory call is a tool use with its input and the next line its result',
              [(u['name'], u['input']) for u in uses] == [('mcp__%s__%s' % (s, t), args) for s, t, args in calls_a]
              and len(a['results']) == len(uses) and all(r['tool_use_id'] == u['id'] for r, u in zip(a['results'], uses))
              and sum('"tool_use"' in l['payload'] for l in kept) == len(calls_a)
              and sum('"tool_result"' in l['payload'] for l in kept) == len(calls_a))
        raw = '\n'.join(l.get('payload', '') for l in a['lines'])
        check('AC3/record', 'memory_kb\'s passphrase, in a document a search returned, is never kept; its marker is',
              passphrase in '\n'.join(a['printed']) and passphrase not in raw and '[REDACTED:mcp_credential]' in raw
              and any('mcp_credential' in l.get('redacted', []) for l in a['lines']))
        counted = MS.metrics(a['lines'])
        check('AC3/record', 'memory tool calls are counted per server and tool from the record [%s]' % counted,
              counted['memory_tool_calls'].get('memory-kb/index-file') == 1
              and counted['memory_tool_calls'].get('ava-memory/memory_add_smart') == 1
              and counted['memory_servers_failed'] == 0)
        finds = [['ava-memory', 'memory_search', {'query': 'tests before merge'}],
                 ['knowledge-graph', 'kg_search', {'query': 'Graph fact from conversation A'}],
                 ['memory-kb', 'search', {'query': 'deploy moved to Fridays'}]]

        def found(texts):
            return (len(texts) == 3 and 'tests before merge' in texts[0] and 'Graph fact from conversation A' in texts[1]
                    and 'deploy moved to Fridays' in texts[2])
        b = turn('conversation-b', 'claude-b', bound['assistant'], finds)
        print('  VELDO-0183 AC3 conversation B:', [t[:80] for t in b['texts']])
        check('AC3/cross-conversation', 'conversation B, on another account, finds all three', found(b['texts']))
        assistant_config = json.loads(Path(manifest['assistant_mcp']).read_text())
        assistant_config['mcpServers']['knowledge-graph'] = {'command': graph['interpreter'],
                                                             'args': [str(Path(graph['code']) / 'mcp_server.py')]}
        assistant_config['mcpServers'].pop('other', None)
        for entry in assistant_config['mcpServers'].values():
            entry.setdefault('env', {})['JARVIS_PASSPHRASE'] = passphrase
        owner_dir = base / 'turns' / 'assistant'
        owner_dir.mkdir(parents=True)
        (owner_dir / 'mcp.json').write_text(json.dumps(assistant_config))
        (owner_dir / 'plan.json').write_text(json.dumps(dict(session='assistant', native=[], calls=finds)))
        own = subprocess.run([sys.executable, '-B', str(engine_path), str(owner_dir / 'mcp.json'), str(owner_dir / 'plan.json')],
                             capture_output=True, text=True, timeout=600)
        own_texts = [' '.join(c.get('text', '') for c in b2['content']) for e in map(json.loads, own.stdout.splitlines())
                     if e.get('type') == 'user' for b2 in e['message']['content']]
        check('AC3/cross-conversation', 'the owner\'s assistant\'s servers, started as its configuration starts them, '
              'find all three', found(own_texts))
        command = subprocess.run([sys.executable, '-B', factory_module, 'kb', '--state-root', str(root), 'search',
                                  'deploy moved to Fridays'], capture_output=True, text=True, timeout=120)
        check('AC3/cross-conversation', 'and memory_kb\'s command line through `veldo memory kb` finds the document',
              command.returncode == 0 and 'deploy moved to Fridays' in command.stdout)

        own_copy = turn('conversation-b-copy', 'claude-b', dict(bound['assistant'], mcp=[
            m for m in bound['assistant']['mcp'] if m['server'] in ('ava-memory', 'knowledge-graph')]),
            finds[:2], catalog=copied)
        print('  VELDO-0183 AC3 own copy:', [t[:80] for t in own_copy['texts']])
        check('AC3/own-copy-falsifier', 'with its own copy of the data directory, B\'s search is empty, so the '
              'cross-conversation row fails on it',
              len(own_copy['texts']) == 2 and 'tests before merge' not in own_copy['texts'][0]
              and 'Graph fact from conversation A' not in own_copy['texts'][1] and not found(own_copy['texts']))

        # ---- AC4: the store servers, their units and the assistant's entries ----
        for part in MS.STORES:
            entry = definition['parts'][part]
            unit = units / MS.unit_name(part)
            text = unit.read_text() if unit.is_file() else ''
            check('AC4/store-units', '%s: one user unit runs the part\'s interpreter on the factory\'s store server in '
                  'its code directory' % part,
                  ('ExecStart=%s -B %s %s' % (entry['interpreter'], mods / 'control_memory_store.py', part)) in text
                  and 'WorkingDirectory=%s' % entry['code'] in text and 'Type=notify' in text)
            sock = Path(MS.socket_path(root, part))
            check('AC4/store-units', '%s: its socket under the state root opens only for the owner\'s account' % part,
                  sock.is_socket() and (sock.stat().st_mode & 0o777) == 0o600
                  and (sock.parent.stat().st_mode & 0o777) == 0o700 and str(sock).startswith(str(root)))
            phases = [(e['part'], e['phase']) for e in step['events'] if e.get('point') == 'memory_check']
            check('AC4/store-units', '%s: its first start ran inside VELDO-0182\'s check, the copy taken once [%s]'
                  % (part, phases),
                  phases.index((part, 'before')) < phases.index((part, 'after'))
                  and (root / 'memory' / 'copies' / part).is_dir())
        server_pids = {part: manager.pid(MS.unit_name(part)) for part in MS.STORES}
        print('  VELDO-0183 store servers:', server_pids)
        # A second opener: another store server for the same store, and a store held open by another process. A
        # start that is not refused serves until stopped, so each is given 20 seconds and then stopped.
        def start(argv):
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            try:
                out, _ = proc.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
                out = ''
            return subprocess.CompletedProcess(argv, proc.returncode, out, '')
        entry = definition['parts']['ava_memory']
        second = start([entry['interpreter'], '-B', str(mods / 'control_memory_store.py'), 'ava_memory',
                        '--code', entry['code'], '--data', MS.store_data(definition, 'ava_memory'),
                        '--socket', str(base / 'second.sock'), '--state-root', str(root), '--python', sys.executable])
        check('AC4/open-refused', 'a second store server on the same store is refused, naming the holder [%s]'
              % second.stdout.strip(),
              json.loads(second.stdout or '{}').get('reason')
              == 'conflict:memory_store_open:ava_memory:%d' % server_pids['ava_memory'])
        held = base / 'held'
        shutil.copytree(base / 'stores' / 'memory_kb', held, ignore=shutil.ignore_patterns('veldo-store.lock'))
        holder = subprocess.Popen([sys.executable, '-c', 'import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);'
                                   'c.execute("select 1");print("open",flush=True);sys.stdin.read()',
                                   str(held / 'data' / 'chromadb' / 'chroma.sqlite3')],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            holder.stdout.readline()
            refused = start([entry['interpreter'], '-B', str(mods / 'control_memory_store.py'), 'memory_kb',
                             '--code', str(held), '--data', str(held / 'data' / 'chromadb'),
                             '--socket', str(base / 'held.sock'), '--state-root', str(root), '--python', sys.executable])
        finally:
            holder.stdin.close()
            holder.wait(10)
        check('AC4/open-refused', 'a store another process holds open is refused by name before it is opened [%s]'
              % refused.stdout.strip(),
              json.loads(refused.stdout or '{}').get('reason') == 'conflict:memory_store_open:memory_kb:%d' % holder.pid
              and not (base / 'held.sock').exists())
        rewritten = json.loads(Path(manifest['assistant_mcp']).read_text())['mcpServers']
        kept = step['assistant_mcp'].get('previous')
        check('AC4/assistant-entries', 'the assistant\'s ava-memory and memory-kb entries are the bridge, its other '
              'entries untouched',
              rewritten['ava-memory']['args'][:4] == ['-B', factory_module, 'bridge', 'ava_memory']
              and rewritten['memory-kb']['args'][:4] == ['-B', factory_module, 'bridge', 'memory_kb']
              and rewritten['other'] == json.loads(original_assistant)['mcpServers']['other'])
        check('AC4/assistant-entries', 'the previous bytes are kept for the rollback',
              kept and Path(kept).read_bytes() == original_assistant and (Path(kept).stat().st_mode & 0o777) == 0o600)
        phases = [(e['part'], e['phase']) for e in step['events'] if e.get('point') == 'memory_check']
        check('AC4/assistant-entries', 'the rewrite ran inside the check for each part [%s]' % phases,
              phases[-4:] == [('ava_memory', 'before'), ('memory_kb', 'before'), ('ava_memory', 'after'),
                              ('memory_kb', 'after')])
        again = MS.setup_servers(root, str(owner_key), runner=manager, unit_dir=str(units),
                                 install_root=str(base / 'install-v183'), python=sys.executable, factory=str(mods),
                                 host=host)
        check('AC4/assistant-entries', 'a second run leaves entries that name the bridge alone and saves nothing [%s]'
              % again['outcome'],
              again['outcome'] == 'already_done' and again['assistant_mcp']['outcome'] == 'already_done'
              and Path(manifest['assistant_mcp']).read_text() == json.dumps({'mcpServers': rewritten}, indent=2) + '\n')

        # The writers at once: one through a conversation's catalog bridge and one through the assistant's entry on
        # each ChromaDB store, and `veldo memory kb` on memory_kb's store, each adding 200; /proc sampled meanwhile.
        COUNT = 200
        files = base / 'writes'
        for writer in ('bridge', 'assistant', 'command'):
            (files / writer).mkdir(parents=True)
            for i in range(COUNT):
                (files / writer / ('%03d.md' % i)).write_text('kb %s document %03d' % (writer, i))
        results, errors = {}, []
        sampled = {part: [] for part in MS.STORES}
        stop = threading.Event()

        def sample():
            while not stop.is_set():
                for part in MS.STORES:
                    sampled[part].append(FIX.holders(MS.store_data(definition, part), {os.getpid()}))
                time.sleep(0.05)

        def session(name, command, arguments, tool, inputs):
            try:
                env = {k: os.environ[k] for k in ('PATH', 'HOME') if k in os.environ}
                proc = subprocess.Popen([command] + arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=env, text=True)
                messages = [dict(jsonrpc='2.0', id=0, method='initialize', params={})]
                messages += [dict(jsonrpc='2.0', id=i + 1, method='tools/call', params=dict(name=tool, arguments=x))
                             for i, x in enumerate(inputs)]
                out, _ = proc.communicate('\n'.join(json.dumps(m) for m in messages) + '\n', timeout=900)
                answers = [json.loads(l) for l in out.splitlines()][1:]
                bad = [a for a in answers if 'result' not in a or a['result'].get('isError')]
                if bad or len(answers) != len(inputs):
                    errors.append('%s: %d answers, first refused %s' % (name, len(answers), json.dumps(bad[:1])[:300]))
                results[name] = [json.loads(a['result']['content'][0]['text']) for a in answers
                                 if 'result' in a and not a['result'].get('isError')]
            except Exception as error:  # noqa: BLE001
                errors.append('%s: %s' % (name, error))

        def commands():
            found = []
            try:
                for i in range(COUNT):
                    done = subprocess.run([sys.executable, '-B', factory_module, 'kb', '--state-root', str(root),
                                           'index-file', str(files / 'command' / ('%03d.md' % i))],
                                          capture_output=True, text=True, timeout=120)
                    try:
                        found.append(json.loads(json.loads(done.stdout)['content'][0]['text']))
                    except ValueError:
                        errors.append('kb/command %d: %s %s' % (i, done.stdout[-300:], done.stderr[-600:]))
                        return
                results['kb/command'] = found
            except Exception as error:  # noqa: BLE001
                errors.append('kb/command: %s' % error)
        entries = json.loads(Path(manifest['assistant_mcp']).read_text())['mcpServers']
        writers = [
            threading.Thread(target=session, args=('ava/bridge', ava['command'], ava['arguments'], 'memory_add',
                                                   [{'text': 'ava bridge memory %03d' % i} for i in range(COUNT)])),
            threading.Thread(target=session, args=('ava/assistant', entries['ava-memory']['command'],
                                                   entries['ava-memory']['args'], 'memory_add',
                                                   [{'text': 'ava assistant memory %03d' % i} for i in range(COUNT)])),
            threading.Thread(target=session, args=('kb/bridge', mkb['command'], mkb['arguments'], 'index-file',
                                                   [{'path': str(files / 'bridge' / ('%03d.md' % i))} for i in range(COUNT)])),
            threading.Thread(target=session, args=('kb/assistant', entries['memory-kb']['command'],
                                                   entries['memory-kb']['args'], 'index-file',
                                                   [{'path': str(files / 'assistant' / ('%03d.md' % i))} for i in range(COUNT)])),
            threading.Thread(target=commands)]
        sampler = threading.Thread(target=sample)
        sampler.start()
        for writer in writers:
            writer.start()
        for writer in writers:
            writer.join()
        stop.set()
        sampler.join()
        counts = {name: len(value) for name, value in results.items()}
        print('  VELDO-0183 AC4 writers:', counts, errors[:3])
        for part in MS.STORES:
            seen = sampled[part]
            others = sorted({pid for s in seen for pid in s} - {server_pids[part]})
            check('AC4/one-opener', '%s: its files were held open by exactly its store server throughout [%d samples, '
                  'others %s]' % (part, len(seen), others),
                  seen and all(s == {server_pids[part]} for s in seen))
        mem_ids = [r['id'] for name in ('ava/bridge', 'ava/assistant') for r in results.get(name, [])]
        kb_ids = [i for name in ('kb/bridge', 'kb/assistant', 'kb/command') for r in results.get(name, []) for i in r]
        check('AC4/all-written', 'every write was answered [%s %s]' % (counts, errors[:2]),
              not errors and len(mem_ids) == 2 * COUNT and len(kb_ids) == 3 * COUNT
              and len(set(mem_ids)) == 2 * COUNT and len(set(kb_ids)) == 3 * COUNT)
        # A fresh process after all end: every memory found by id and by search, through the part's own functions.
        verify = base / 'verify.py'
        verify.write_text(r'''import json, os, sys
part, code, wanted = sys.argv[1], sys.argv[2], json.loads(open(sys.argv[3]).read())
sys.path.insert(0, code); os.chdir(code)
if part == 'ava_memory':
    from memory_store import get_store
    store = get_store()
    by_id = [i for i, text in wanted if (store.get(i) or {}).get('memory') == text]
    by_search = [i for i, text in wanted if any(r['id'] == i for r in store.search(text, limit=10))]
else:
    from kb import store
    by_id = [i for i, text in wanted if store._get_collection('files').get(ids=[i])['documents'] == [text]]
    by_search = [i for i, text in wanted if any(r['id'] == i for r in store.search('files', text, n_results=10))]
print(json.dumps(dict(by_id=len(by_id), by_search=len(by_search), total=len(wanted))))
''')
        wanted_mem = [[r['id'], r['memory']] for name in ('ava/bridge', 'ava/assistant') for r in results.get(name, [])]
        wanted_kb = [[i, (files / writer / ('%03d.md' % n)).read_text()]
                     for writer, name in (('bridge', 'kb/bridge'), ('assistant', 'kb/assistant'), ('command', 'kb/command'))
                     for n, r in enumerate(results.get(name, [])) for i in r]
        for part, wanted_rows, total in (('ava_memory', wanted_mem, 2 * COUNT), ('memory_kb', wanted_kb, 3 * COUNT)):
            listing = base / ('wanted-%s.json' % part)
            listing.write_text(json.dumps(wanted_rows))
            done = subprocess.run([definition['parts'][part]['interpreter'], '-B', str(verify), part,
                                   definition['parts'][part]['code'], str(listing)], capture_output=True, text=True,
                                  timeout=300)
            answer = json.loads(done.stdout or '{}')
            print('  VELDO-0183 AC4 %s found: %s' % (part, answer))
            check('AC4/all-written', '%s: all %d memories found by id and by search from a fresh process [%s]'
                  % (part, total, answer), answer == dict(by_id=total, by_search=total, total=total))

        # ---- Observability: the store servers' journal lines name parts, sockets, tools and revisions only ----
        logs = '\n'.join(Path(p).read_text(errors='replace') for p in manager.logs)
        lines = [json.loads(l) for l in logs.splitlines() if l.startswith('{')]
        starts = [l for l in lines if l.get('event') == 'memory_store_start']
        calls = [l for l in lines if l.get('event') == 'memory_call']
        check('observability', 'each store server logs its start and lock with its part and socket',
              {l['part'] for l in starts} == set(MS.STORES) and all(l.get('socket') and l.get('lock') for l in starts))
        check('observability', 'each catalog call is logged with its server, catalog and memory record revisions',
              any(l.get('server') == 'ava-memory' and l.get('catalog_revision') == ava['revision']
                  and l.get('memory_revision') == memory_revision for l in calls))
        check('observability', 'no memory content and no credential in the store servers\' lines',
              'tests before merge' not in logs and 'deploy moved' not in logs and passphrase not in logs)
        check('observability', 'the servers step observed each catalog revision with the memory record revision',
              {e['server'] for e in events if e.get('point') == 'memory_catalog_revision'} == set(FOUR)
              and all(e['memory_revision'] == memory_revision for e in events if e.get('point') == 'memory_catalog_revision'))

        setup_step(h, profiles, host)

    def setup_step(h, profiles, host):
        """AC1's setup: `veldo factory setup` with the memory manifest, on VELDO-0182's claude-mem worker fixture (its
        preflight's probe, as VELDO-0182's suite runs it), lays the four records and both role revisions down with no
        separate command, and its rerun saves nothing."""
        base, CEN, mods = h['base'], h['CEN'], h['mods']
        AR = load('v183s_accounts', mods / 'accounts.py')
        F182 = load('v183s_fixtures182', here / 'proof/VELDO-0182/fixtures.py')
        root, workspace = h['fresh_root']('state-v183s'), h['clone']('clone-v183s')
        registry = os.path.join(CEN.git_common_dir(str(workspace)), 'veldo')
        for name, provider in ACCOUNTS:
            AR.account_add(name, config_dir=str(profiles[name]), root=registry, provider=provider)
        manifest = FIX.build(base / 'stores-setup', host)
        manifest['parts']['claude_mem'] = F182.build(base / 'stores-182', host)['parts']['claude_mem']
        manifest_path = base / 'memory-setup.json'
        manifest_path.write_text(json.dumps(manifest))
        units = base / 'units-v183s'
        manager = h['Manager'](units)
        h['managers'].append(manager)
        bun_dir = F182.bun(base / 'bun-v183s')
        saved_path, saved_uv = os.environ['PATH'], {n: os.environ.pop(n) for n in list(os.environ) if n.startswith('UV_')}
        os.environ['PATH'] = str(bun_dir) + os.pathsep + saved_path
        os.environ['UV_CACHE_DIR'] = str(F182.uv_cache(base / 'owner-uv-v183s'))
        try:
            def run():
                return h['setup'](root, workspace, base / 'trust-v183s' / 'host.json', base / 'install-v183s', units,
                                  manager, **{'--memory': str(manifest_path)})
            code, report = run()
            print('  VELDO-0183 setup with memory:', code, report.get('outcome'), report.get('reason'))
            first = next((s for s in report.get('steps') or [] if s.get('step') == 'memory_servers'), {})
            check('AC1/setup-step', 'factory setup with the memory manifest ran the servers step [%s %s %s]'
                  % (code, report.get('reason'), {k: first.get(k) for k in ('outcome', 'catalog_saved', 'roles')}),
                  code == 0 and report.get('outcome') == 'set_up' and first.get('outcome') == 'done')
            if code != 0:
                return
            store_path = Path(report['store'])
            installed = Path(report['home']) / 'bin'
            MC = load('v183s_catalog', installed / 'control_mcp_catalog.py')
            CONV = load('v183s_conversation', mods / 'control_conversation.py')
            domain = json.loads((Path(report['state_root']) / 'host' / 'ingress.json').read_text())['authority_ids'][
                'domain_uuid']

            def read():
                conn = sqlite3.connect('file:%s?mode=ro' % store_path, uri=True, timeout=30)
                try:
                    heads = {server: (MC.entity(conn, MC.head_id(domain, server)) or {}).get('data') for server in FOUR}
                    bound = {}
                    for role in ('assistant', 'assistant_codex'):
                        with contextlib.suppress(Exception):
                            bound[role] = CONV.role_at(conn, role)[1]
                    return heads, bound, conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
                finally:
                    conn.close()
            heads, bound, journal = read()
            check('AC1/setup-step', 'the four catalog records are saved by setup itself [%s]'
                  % sorted(s for s, r in heads.items() if r), all(heads.values()))
            for role in ('assistant', 'assistant_codex'):
                revision = bound.get(role) or {}
                check('AC1/setup-step', '%s\'s new revision from setup selects all four, every tool, always [%s]'
                      % (role, revision.get('revision')),
                      revision.get('revision', 0) >= 2 and revision.get('previous')
                      and sorted(m['server'] for m in revision.get('mcp') or [] if m['server'] in FOUR) == sorted(FOUR)
                      and all(m['tools'] == 'all' and m['load'] == 'always'
                              for m in revision.get('mcp') or [] if m['server'] in FOUR))
            check('AC1/setup-step', 'setup started both store servers', sorted(
                s.get('part') for s in first.get('stores') or [] if s.get('outcome') == 'started') == sorted(MS_STORES))
            code2, again = run()
            second = next((s for s in again.get('steps') or [] if s.get('step') == 'memory_servers'), {})
            heads2, bound2, journal2 = read()
            print('  VELDO-0183 setup rerun:', code2, again.get('outcome'), second.get('outcome'), journal, journal2)
            check('AC1/setup-step', 'the rerun runs the same step and saves nothing [%s %s %s, journal %s to %s]'
                  % (code2, again.get('outcome'), second.get('outcome'), journal, journal2),
                  code2 == 0 and second.get('outcome') == 'already_done' and not second.get('catalog_saved')
                  and not second.get('roles') and journal2 == journal and heads2 == heads and bound2 == bound)
        finally:
            os.environ['PATH'] = saved_path
            os.environ.pop('UV_CACHE_DIR', None)
            os.environ.update(saved_uv)

    MS_STORES = ('ava_memory', 'memory_kb')

    def teardown(h):
        pass

    try:
        helper.run(ROOT, PRODUCTION, exercise, teardown, fake)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in rows:
            check(row, 'ran to its end (raised ' + type(error).__name__ + ': ' + str(error)[:250] + ')', False)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0183 detail:', row, '; '.join(failed))
        expect('VELDO-0183 ' + row, bool(rows[row]) and not failed)


_v183_suite()
