"""VELDO-0165 session environment hygiene, through real Runner, receiver and exec wrapper.

The store, accounts, reservations, claims, dispatches and qualifier writers are production code.
Fake engines and a local stdio MCP server are fixtures. The reported-identity wrapper runs locally,
so no user service manager, model, real profile or network is used. Every row reports once.
"""

def _v165_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    ROWS = ('strip/claude', 'strip/codex', 'strip/future-names', 'strip/own-values',
            'refuse/claude', 'refuse/codex', 'mcp/prefixed-tools', 'evidence/qualified',
            'fixture/extraction', 'fixture/mcp-control')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn):
        """(value, error): a refusal or a missing function is data for the row, never a raise."""
        try:
            return fn(), None
        except Exception as error:  # noqa: BLE001
            return None, error

    def code(error):
        return getattr(error, 'code', type(error).__name__) if error is not None else None

    def load(name, path):
        if not Path(path).is_file():
            return None
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='v165-', dir=fast))
    connections = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v165_store', mods / 'control_store.py')
        L = load('v165_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        HELPER = load('v165_helper', mods / 'accounts.py')
        EL = load('v165_eligibility', mods / 'control_eligibility.py')
        SIG = load('v165_signer', mods / 'control_signer.py')
        GP = load('v165_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-165', 'repository-165', 'builder-165', 'linux-host-165'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        connections.append(writer)
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='setup', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', sign, 1)

        def member(principal, kind, roles):
            put(principal, 'membership', dict(principal_type=kind, roles=roles, scope=[REPOSITORY],
                                              revoked_at=None, expires_at=None))
        member('runner', 'service', ['reservation_service'])
        member('launch-receiver', 'service', ['reservation_service'])
        member('owner', 'person', ['project_owner'])
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        # The owner's account records, over profiles the local helper prepares for either provider.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}

        def register(account, provider, concurrency=1, directory=None):
            """Prepare the account's profile and register it once; the refusal's code, or None."""
            record, error = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider,
                                                               config_dir=directory))
            if record is None:
                return code(error)
            profiles.setdefault(account, record['config_dir'])
            fields = HELPER.registration(account, host=HOST, root=str(helper_root))
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
            _, error = attempt(lambda: accounts.register('register/' + account, fields['account'], fields['provider'],
                                                         fields['label'], fields['profiles'], concurrency=concurrency,
                                                         now=time.time()))
            return code(error)
        for account, provider in [('acct-c1', 'claude_code'), ('acct-x1', 'codex')]:
            error = register(account, provider)
            check('strip/' + ('claude' if provider == 'claude_code' else 'codex'),
                  'account registered by production writer', error is None)
        projects = set()

        def admitted(unit, proj='journey'):
            if proj not in projects:
                projects.add(proj)
                put('project:' + proj, 'project', dict(name=proj))
                reservations.configure('policy/' + proj, 'project', proj, dict(BIG), now=time.time())
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project=proj,
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=20, wall_seconds=10 ** 6),
                                   now=time.time())
            cid = CLM.claim_id(REPOSITORY, unit)
            serial[0] += 1
            S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=HOLDER, operation='claim_operation',
                                   nonce='claim-%d' % serial[0], artifact_digests=[],
                                   expected_versions={unit: entity(unit)['version'],
                                                      'backlog:' + unit: entity('backlog:' + unit)['version'], cid: 0},
                                   parameters=dict(action='claim', unit_id=unit, backlog_item_uuid='backlog:' + unit,
                                                   claim_id=cid, holder=HOLDER, generation=0, capabilities=[],
                                                   repository_uuid=REPOSITORY)), HOLDER, sign, 1)
            return unit

        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'README').write_text('session hygiene source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fake engines: each records its birth environment, then prints what its packet scripts,
        # waiting on a file where the script says, and exits with the scripted code.
        markers = base / 'markers'
        markers.mkdir()
        engines = base / 'bin'
        engines.mkdir()
        server = base / 'mcp-server.py'
        server.write_text('import json,sys\n'
                          'for line in sys.stdin:\n'
                          ' r=json.loads(line)\n'
                          ' print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{"tools":['
                          '{"name":"read","inputSchema":{"type":"object"}},'
                          '{"name":"write","inputSchema":{"type":"object"}}]}}),flush=True)\n')
        fake = '''#!%s -B
import json, os, sys, time, subprocess
from pathlib import Path
if sys.argv[1:3] == ['login', 'status']:
    # VELDO-0156: the receiver's check before acceptance, on a ChatGPT login; the 0.154.0 binary prints its
    # login status on stderr.
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
markers = Path(MARKERS)
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
own = {'engine': ENGINE, 'pid': os.getpid(), 'dispatch': dispatch, 'started': time.time(),
       'env': dict(os.environ)}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
def stream_input():
    # VELDO-0155: stream JSON input (--input-format stream-json) as the 2.1.281 binary reads it: the initialize
    # control request is answered with the login (the binary's Kfe(), a claude.ai subscription here), the user
    # message's content is the prompt; without it the whole input is the prompt.
    at = sys.argv.index('--input-format') if '--input-format' in sys.argv else -1
    if at < 0 or sys.argv[at + 1:at + 2] != ['stream-json']:
        raw = sys.stdin.buffer.read()
        return json.loads(raw) if raw.strip() else {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return {}
        message = json.loads(line)
        if message.get('type') == 'control_request' and (message.get('request') or {}).get('subtype') == 'initialize':
            answer = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                      'response': {'account': {'subscriptionType': 'Claude Max', 'apiProvider': 'firstParty'},
                                   'pid': os.getpid()}}}
            sys.stdout.write(json.dumps(answer) + chr(10))
            sys.stdout.flush()
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            return json.loads(content) if isinstance(content, str) and content.strip() else {}
packet = stream_input()
if own['engine'] == 'claude':
    server_config = (packet.get('configuration') or {}).get('mcp_servers') or {}
    tools = []
    for name, config in server_config.items():
        request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}) + chr(10)
        answer = subprocess.run([config['command']] + config['args'], input=request,
                                capture_output=True, text=True, check=True, timeout=5)
        for tool in json.loads(answer.stdout)['result']['tools']:
            # Exact gate in the binary: only SDK servers can opt out of Fa(server, tool).
            plain = config['type'] == 'sdk' and os.environ.get('CLAUDE_AGENT_SDK_MCP_NO_PREFIX')
            tools.append(tool['name'] if plain else 'mcp__' + name + '__' + tool['name'])
    own['init'] = {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'tools': tools,
                   'claude_code_version': '2.1.281', 'cwd': str(Path.cwd()),
                   'mcp_servers': [{'name': n, 'status': 'connected'} for n in server_config],
                   'model': 'fixture-model', 'permissionMode': 'default', 'slash_commands': [],
                   'output_style': 'default', 'skills': [], 'plugins': [],
                   'uuid': 'fixture-init', 'session_id': 'fixture-session'}
    (markers / ('%%d.json' %% os.getpid())).write_text(json.dumps(own))
    print(json.dumps(own['init']), flush=True)
payload = packet.get('payload') or {}
for step in payload.get('script') or []:
    if 'line' in step:
        sys.stdout.write(json.dumps(step['line']) + chr(10))
        sys.stdout.flush()
    elif 'sleep' in step:
        time.sleep(step['sleep'])
    elif 'wait' in step:
        end = time.time() + 30
        while not os.path.exists(step['wait']) and time.time() < end:
            time.sleep(0.02)
(markers / ('%%d.done' %% os.getpid())).write_text(json.dumps({'ended': time.time()}))
sys.exit(payload.get('code', 0))
''' % (sys.executable,)

        def fake_engine(name):
            # The markers directory and the engine's name are written into the fake: a pinned engine's argv
            # is its qualified flags, so nothing of the suite's can ride on it.
            return (fake.replace('Path(MARKERS)', 'Path(%r)' % str(markers))
                        .replace("'engine': ENGINE,", "'engine': %r," % name))
        # VELDO-0060: a Claude Code adapter runs only its pinned, qualified version. The fake claude is
        # installed as that version, this installation's qualification record names its digest, and the
        # production pin copies it under the factory state root.
        versions = base / 'versions'
        versions.mkdir()
        (versions / '2.1.281').write_text(fake_engine('claude'))
        (versions / '2.1.281').chmod(0o755)
        # VELDO-0155: the version is qualified with stream JSON input (the fake answers the initialize handshake
        # with a subscription login) and, where the engine module has one, the everything-off baseline.
        claude_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {'2.1.281': {
            'sha256': 'sha256:' + hashlib.sha256((versions / '2.1.281').read_bytes()).hexdigest(),
            'flags': ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json'],
            'environment': {'DISABLE_AUTOUPDATER': '1'}}}}
        CLAUDE_ENGINE = getattr(L, 'ENGINES', {}).get('claude_code')
        if getattr(CLAUDE_ENGINE, 'BASELINE', None) is not None:
            claude_record['versions']['2.1.281']['baseline'] = CLAUDE_ENGINE.BASELINE
            if hasattr(CLAUDE_ENGINE, 'session_environment'):
                claude_record['versions']['2.1.281']['session_environment'] = CLAUDE_ENGINE.session_environment(versions / '2.1.281')
        (mods / 'runtime').mkdir()
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps(claude_record))
        factory = base / 'factory'
        factory.mkdir(mode=0o700)
        pin = getattr(getattr(L, 'ENGINES', {}).get('claude_code'), 'pin', None)
        if pin is not None:
            pin('2.1.281', versions=str(versions), state_root=str(factory))
        # VELDO-0061: a Codex adapter launches a pinned vendor binary inside its package, with the qualified
        # flags, checked against a qualification record the production writer makes.
        package = engines / 'codex-package'
        vendored = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        vendored.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        vendored.write_text(fake_engine('codex'))
        vendored.chmod(0o755)
        CODEX_ENGINE = getattr(L, 'ENGINES', {}).get('codex')
        codex_qualification = base / 'codex-qualification.json'
        if hasattr(CODEX_ENGINE, 'qualification'):
            codex_qualification.write_text(json.dumps(CODEX_ENGINE.qualification(str(vendored))))
        config = base / 'receiver.json'
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(base / 'receipts'), 'state_root': str(factory),
            'adapters': {
                'claude': {'identity': 'reported', 'engine': 'claude_code', 'environment': {'TZ': 'UTC'},
                           'executable': {'version': '2.1.281'}, 'argv': wrapper},
                'codex': {'identity': 'reported', 'engine': 'codex', 'environment': {'TZ': 'UTC'},
                          'executable': str(vendored), 'qualification': str(codex_qualification),
                          'argv': wrapper + [str(vendored)] + list(getattr(CODEX_ENGINE, 'FLAGS', ()))}}}))
        CONFIGURATION = {'mcp_servers': {'tracker': {'type': 'sdk', 'command': sys.executable, 'args': [str(server)]}}}
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)

        inherited = {'PATH': os.environ['PATH'], 'HOME': str(base / 'home'), 'TZ': 'UTC'}
        (base / 'home').mkdir()
        original = ('CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_SESSION_ID',
                    'CLAUDE_CODE_SESSION_ATTENDED', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_EXECPATH',
                    'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID',
                    'CLAUDE_EFFORT', 'AI_AGENT', 'CODEX_THREAD_ID', 'CLAUDE_AGENT_SDK_MCP_NO_PREFIX')
        future = tuple(p + 'VELDO_FUTURE_' + os.urandom(5).hex().upper()
                       for p in ('CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX', 'CLAUDE_CODE_'))
        planted = original + future
        inherited.update({n: 'planted-' + os.urandom(8).hex() for n in planted})
        inherited.update({'CLAUDE_CONFIG_DIR': str(base / 'wrong-claude'),
                          'CODEX_HOME': str(base / 'wrong-codex'),
                          'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '0', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '0'})
        token = base / 'subscription-fixture'
        own_token = 'fixture-' + os.urandom(12).hex()
        token.write_text(own_token)
        token.chmod(0o600)
        configuration = json.loads(config.read_text())
        configuration['subscription_tokens'] = {'acct-c1': str(token)}
        config.write_text(json.dumps(configuration))
        inherited['CLAUDE_CODE_OAUTH_TOKEN'] = 'inherited-' + os.urandom(12).hex()

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30, environment=inherited)
        explicit = {}

        def pinned(account):
            if account not in explicit:
                explicit[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return explicit[account]

        def job(adapter, script, code_=0, deadline=40):
            if adapter == 'codex':
                script = [{'line': {'type': 'thread.started', 'thread_id': 'thread-165'}}] + list(script)
            return dict(holder=HOLDER, source=str(src), revision='HEAD',
                        payload={'task': 'work the unit', 'script': script, 'code': code_}, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

        def submit(unit, adapter, script, code_=0, via=None):
            """(launch, error): a real dispatch on the account `via` names."""
            use = pinned(via)
            return attempt(lambda: use.submit(admitted(unit), 'build', **job(adapter, script, code_)))

        def finish(launch, via=None):
            if launch is None:
                return {}
            record, _ = attempt(lambda: pinned(via).wait(launch))
            return record or {}

        def markers_of(dispatch_id):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    done = markers / ('%d.done' % data['pid'])
                    data['ended'] = json.loads(done.read_text())['ended'] if done.exists() else None
                    found.append(data)
            return found

        launches = {}
        for engine, account in (('claude', 'acct-c1'), ('codex', 'acct-x1')):
            launch, error = submit('unit-' + engine, engine, [], via=account)
            record = finish(launch, via=account)
            observed = markers_of(launch.dispatch_id) if launch else []
            own = observed[0] if len(observed) == 1 else {}
            launches[engine] = (launch, record, own)
            names = set(own.get('env') or {})
            report = next((e['baseline'] for e in (launch.messages if launch else [])
                           if e.get('event') == 'baseline'), {})
            check('strip/' + engine, 'real wrapper spawned one engine and removed every planted name',
                  error is None and record.get('state') == 'exited' and bool(names)
                  and not names.intersection(planted))
            check('strip/' + engine, 'removed names and executable identity reported without values',
                  set(planted) <= set(report.get('removed') or [])
                  and report.get('dispatch_id') == (launch.dispatch_id if launch else None)
                  and (report.get('executable') or {}).get('version') == ('2.1.281' if engine == 'claude' else '0.154.0')
                  and not any(inherited[n] in json.dumps(report) for n in planted))
            check('strip/future-names', engine + ': unlisted future names removed by all four prefixes',
                  bool(names) and not names.intersection(future))
            env = own.get('env') or {}
            profile = 'CLAUDE_CONFIG_DIR' if engine == 'claude' else 'CODEX_HOME'
            check('strip/own-values', engine + ': account profile and baseline restored after strip',
                  env.get(profile) == profiles[account] and env.get('DISABLE_AUTOUPDATER') == '1'
                  and 'VELDO_ENGINE_ENVIRONMENT' not in env and not set(planted).intersection(env))
            if engine == 'claude':
                check('strip/own-values', 'baseline and own subscription token replace inherited values',
                      env.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY') == '1'
                      and env.get('CLAUDE_CODE_DISABLE_CLAUDE_MDS') == '1'
                      and env.get('CLAUDE_CODE_OAUTH_TOKEN') == own_token)

        check('mcp/prefixed-tools', 'configured SDK server tools retain their names in the init event',
              launches['claude'][2].get('init', {}).get('tools') == ['mcp__tracker__read', 'mcp__tracker__write'])

        # Remove each kind of qualification evidence separately, then drive a real dispatch.
        for engine, account, path, version in (
                ('claude', 'acct-c1', mods / 'runtime' / 'claude-qualification.json', '2.1.281'),
                ('codex', 'acct-x1', codex_qualification, '0.154.0')):
            original_record = json.loads(path.read_text())
            for missing in ('strip_prefixes', 'session_environment'):
                altered = json.loads(json.dumps(original_record))
                entry = altered['versions'][version] if engine == 'claude' else altered
                if missing == 'strip_prefixes':
                    entry['baseline'].pop(missing, None)
                else:
                    entry.pop(missing, None)
                path.write_text(json.dumps(altered))
                launch, error = submit('missing-' + engine + '-' + missing, engine, [], via=account)
                record = finish(launch, via=account)
                check('refuse/' + engine, missing + ': refused by name before spawn',
                      error is None and record.get('refusal') == 'missing_evidence:engine_baseline:' + version
                      and record.get('state') == 'refused' and not markers_of(launch.dispatch_id))
            path.write_text(json.dumps(original_record))

        for engine, version, module in (('claude', '2.1.281', CLAUDE_ENGINE), ('codex', '0.154.0', CODEX_ENGINE)):
            evidence = json.loads((TREE / 'proof' / 'VELDO-0165' / (engine + '-environment.json')).read_text())
            shipped = json.loads((ROOT / '.veldo' / 'runtime' / (engine + '-qualification.json')).read_text())
            entry = shipped['versions'][version] if engine == 'claude' else shipped
            prefixes = (entry.get('baseline') or {}).get('strip_prefixes') or []
            check('evidence/qualified', engine + ': qualification carries prefixes, names and pinned digest',
                  prefixes == ['CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX']
                  and entry.get('session_environment') == evidence['session_names']
                  and bool(entry.get('session_environment')) and entry['sha256'] == evidence['sha256']
                  and all(n.startswith(tuple(prefixes)) or n in L.EXEC_STRIPPED for n in evidence['parent_session_names']))
            check('fixture/extraction', engine + ': extracted offsets and parent names present',
                  len(evidence['names']) > 100 and all(v and all(isinstance(x, int) and x >= 0 for x in v)
                                                     for v in evidence['names'].values())
                  and bool(evidence['parent_session_names'])
                  and not set(future).intersection(evidence['names']))
        check('evidence/qualified', 'MCP override named explicitly in baseline',
              'CLAUDE_AGENT_SDK_MCP_NO_PREFIX' in CLAUDE_ENGINE.BASELINE.get('strip_names', []))

        # Positive control: the same fake and SDK server outside the wrapper lose the prefix.
        control_env = dict(inherited, VELDO_DISPATCH_ID='control')
        packet = {'configuration': CONFIGURATION, 'payload': {}}
        done = subprocess.run([str(versions / '2.1.281')], input=json.dumps(packet), env=control_env,
                              capture_output=True, text=True, timeout=10)
        control = markers_of('control')
        check('fixture/mcp-control', 'SDK gate is supported by binary bytes and reacts to inherited override',
              done.returncode == 0 and len(control) == 1
              and control[0]['init']['tools'] == ['read', 'write']
              and 'e.config.type==="sdk"&&a.CLAUDE_AGENT_SDK_MCP_NO_PREFIX' in
              json.loads((TREE / 'proof' / 'VELDO-0165' / 'claude-environment.json').read_text())['mcp_naming']['text'])
    except Exception as exc:
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        for connection in connections:
            connection.close()
        shutil.rmtree(base)
    for name, observed in rows.items():
        ok = bool(observed) and all(value for _, value in observed)
        for label, value in observed:
            if not value:
                print('  VELDO-0165 %s detail: %s' % (name, label))
        expect('VELDO-0165 ' + name, ok)
    print('VELDO-0165 suite seconds: %.3f' % (time.monotonic() - started))


_v165_suite()
