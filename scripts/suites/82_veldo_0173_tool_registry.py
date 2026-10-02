"""VELDO-0173 the launch tool set and the full tool registry, through real Runner, receiver and exec wrapper.

The store, accounts, reservations, claims, dispatches and qualification checks are production code. The
fake Claude Code applies `--tools` and `--disallowedTools` to the registry the committed extractor read
from the pinned 2.1.281 bytes, as the binary turns both into deny rules over its registry, and prints the
tools it offers in its init event. The reported-identity wrapper runs locally, so no user service
manager, model, real profile or network is used. Every row reports once.
"""

def _v173_suite():
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
    }
    EXTRACTOR = ROOT / "proof/VELDO-0173" / "extract_tools.py"
    ROWS = ('launch/no-revision', 'launch/registry', 'launch/revision', 'report/tools', 'evidence/registry',
            'evidence/classification', 'baseline/required', 'fixture/extraction', 'fixture/fake-default',
            'format/fake-lines')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn):
        """(value, error): a refusal or a missing function is data for the row, never a raise."""
        try:
            return fn(), None
        except Exception as error:  # noqa: BLE001
            return None, error

    def load(name, path):
        if not Path(path).is_file():
            return None
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fake_spec = importlib.util.spec_from_file_location('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    # VELDO-0172: this suite checks its own fake engine against the live capture at its teardown.
    conform_spec = importlib.util.spec_from_file_location('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)
    live_step = fake_formats.live_step

    # The committed evidence: the registry and classification read from the pinned bytes, the in-run list
    # of the VELDO-0160 build and the 22-name built-in table, all of this tree.
    EVIDENCE = json.loads((TREE / 'proof' / 'VELDO-0173' / 'claude-tools.json').read_text())
    FORMS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['claude_code']['tool_forms']
    IN_RUN = list(FORMS['in_run']['tools'])
    TABLE22 = list(FORMS['builtin_tools'])
    REGISTRY = [t['name'] for t in EVIDENCE['registry']]
    UNREGISTERED = sorted(EVIDENCE['unregistered_in_run'])
    LIVE = ('CronList', 'CronDelete', 'EnterWorktree', 'ExitWorktree', 'ListAgents', 'ScheduleWakeup', 'ReportFindings')
    # Tools that act outside the run: other sessions, the owner's devices, claude.ai pages and projects,
    # cloud routines and self-hosted runners.
    OUTSIDE = ('RemoteTrigger', 'SendMessage', 'PushNotification', 'Artifact', 'ArtifactComments', 'ArtifactData',
               'ArtifactCheck', 'AppifactRepl', 'ClaudeDesign', 'DesignSync', 'Projects', 'ShareOnboardingGuide')
    VERSION = '2.1.281'

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='v173-', dir=fast))
    connections = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v173_store', mods / 'control_store.py')
        L = load('v173_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        HELPER = load('v173_helper', mods / 'accounts.py')
        EL = load('v173_eligibility', mods / 'control_eligibility.py')
        SIG = load('v173_signer', mods / 'control_signer.py')
        GP = load('v173_git', mods / 'git_process.py')
        CLM = D.CLM
        E = L.ENGINES['claude_code']
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-173', 'repository-173', 'builder-173', 'linux-host-173'
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
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        # The owner's account record, over a profile the local helper prepares.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        HELPER.account_add('acct-c1', root=str(helper_root), provider='claude_code')
        fields = HELPER.registration('acct-c1', host=HOST, root=str(helper_root))
        reservations.configure('policy/acct-c1', 'account', 'acct-c1', dict(BIG), now=time.time())
        accounts.register('register/acct-c1', fields['account'], fields['provider'], fields['label'],
                          fields['profiles'], concurrency=1, now=time.time())
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
        (src / 'README').write_text('tool registry source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fake Claude Code: it records its argv, answers the initialize handshake, offers the tools the
        # 2.1.281 binary would (its registry, narrowed by --tools and less --disallowedTools) in its init
        # event, then prints what its packet scripts.
        markers = base / 'markers'
        markers.mkdir()
        fake = '''#!%s -B
import json, os, sys, time
from pathlib import Path
markers = Path(MARKERS)
REGISTRY = TOOL_REGISTRY
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
own = {'engine': ENGINE, 'pid': os.getpid(), 'dispatch': dispatch, 'argv': sys.argv[1:]}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
def emit(event):
    text = json.dumps(event)
    with open(markers / ('%%d.out' %% os.getpid()), 'a') as out:
        out.write(text + chr(10))
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def option(names):
    # As the binary's option parser reads them: --name=value is one value; --name takes the words after
    # it until the next option (the options are variadic).
    present, values, argv, n = False, [], sys.argv[1:], 0
    while n < len(argv):
        head, joined, value = argv[n].partition('=')
        if joined and head in names:
            present = True
            values.append(value)
        elif argv[n] in names:
            present = True
            while n + 1 < len(argv) and not (len(argv[n + 1]) > 1 and argv[n + 1][0] == '-'):
                n += 1
                values.append(argv[n])
        n += 1
    return present, values
def split(values):
    # The binary's list reading: commas and spaces separate names outside parentheses.
    found = []
    for value in values:
        word, inside = '', False
        for ch in value:
            if ch in '()':
                inside = ch == '('
                word += ch
            elif ch in ', ' and not inside:
                if word.strip():
                    found.append(word.strip())
                word = ''
            else:
                word += ch
        if word.strip():
            found.append(word.strip())
    return found
def stream_input():
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
                      'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'},
                                   'pid': os.getpid()}}}
            emit(complete_event(answer))
        elif message.get('type') == 'user':
            if message.get('shouldQuery') is False:
                emit(own['init'])
                emit(complete_event({'type': 'result', 'subtype': 'success', 'is_error': False,
                                     'num_turns': 0, 'result': '',
                                     'usage': {'input_tokens': 0, 'output_tokens': 0}}))
                continue
            content = (message.get('message') or {}).get('content')
            return json.loads(content) if isinstance(content, str) and content.strip() else {}
narrowed, named = option(('--tools',))
_, denied = option(('--disallowedTools', '--disallowed-tools'))
kept = split(named)
offered = [t for t in REGISTRY if t in kept] if narrowed and [k.lower() for k in kept] != ['default'] else list(REGISTRY)
offered = [t for t in offered if t not in set(split(denied))]
own['init'] = complete_event({'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'tools': offered,
               'claude_code_version': '2.1.281', 'cwd': str(Path.cwd()), 'mcp_servers': [],
               'model': 'fixture-model', 'permissionMode': 'default', 'slash_commands': [],
               'output_style': 'default', 'skills': [], 'plugins': [],
               'uuid': 'fixture-init', 'session_id': 'fixture-session'})
(markers / ('%%d.json' %% os.getpid())).write_text(json.dumps(own))
if '--mcp-config' in sys.argv: own['init']['plugins'] = []
packet = stream_input()
if '--mcp-config' not in sys.argv: emit(own['init'])
payload = packet.get('payload') or {}
for step in payload.get('script') or []:
    if 'line' in step:
        emit(step['line'])
(markers / ('%%d.done' %% os.getpid())).write_text('done')
sys.exit(payload.get('code', 0))
''' % (sys.executable,)
        fake = fake_formats.embed(fake).replace('TOOL_REGISTRY', repr(REGISTRY))

        def fake_engine(name):
            # The markers directory and the engine's name are written into the fake: a pinned engine's argv
            # is its qualified flags and baseline, so nothing of the suite's can ride on it.
            return (fake.replace('Path(MARKERS)', 'Path(%r)' % str(markers))
                        .replace("'engine': ENGINE,", "'engine': %r," % name))
        versions = base / 'versions'
        versions.mkdir()
        (versions / VERSION).write_text(fake_engine('claude'))
        (versions / VERSION).chmod(0o755)
        # This installation's record: the fake's digest, the qualified flags, baseline and session names of
        # the version, and (VELDO-0173) the shipped record's tool registry and classification.
        shipped = json.loads((ROOT / '.veldo' / 'runtime' / 'claude-qualification.json').read_text())
        shipped_entry = shipped['versions'][VERSION]
        entry = {'sha256': 'sha256:' + hashlib.sha256((versions / VERSION).read_bytes()).hexdigest(),
                 'flags': ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json'],
                 'environment': {'DISABLE_AUTOUPDATER': '1'}, 'baseline': E.BASELINE,
                 'session_environment': E.session_environment(versions / VERSION)}
        for key in ('tool_registry', 'tool_classification'):
            if key in shipped_entry:
                entry[key] = shipped_entry[key]
        record_path = mods / 'runtime' / 'claude-qualification.json'
        (mods / 'runtime').mkdir()
        record_path.write_text(json.dumps({'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code',
                                           'versions': {VERSION: entry}}))
        factory = base / 'factory'
        factory.mkdir(mode=0o700)
        E.pin(VERSION, versions=str(versions), state_root=str(factory))
        config = base / 'receiver.json'
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(base / 'receipts'), 'state_root': str(factory),
            'adapters': {'claude': {'identity': 'reported', 'engine': 'claude_code', 'environment': {'TZ': 'UTC'},
                                    'executable': {'version': VERSION}, 'argv': wrapper}}}))
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        inherited = {'PATH': os.environ['PATH'], 'HOME': str(base / 'home'), 'TZ': 'UTC'}
        (base / 'home').mkdir()

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30, environment=inherited)
        runner = L.Runner(gate, reservations, dispatches, invoke, account='acct-c1')

        # Stream lines in the shapes the installed CLI prints, on VELDO-0172's shared constructors.
        SESSION = 'session-173-' + os.urandom(4).hex()

        def c_usage(inp, out):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': 0,
                    'cache_read_input_tokens': 0,
                    'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0},
                    'service_tier': 'standard'}

        @live_step
        def c_msg(mid, inp, out):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': 'uuid-' + os.urandom(6).hex(),
                             'session_id': SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'fixture-model',
                                         'content': [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out)}}}

        @live_step
        def c_rate(status, reset, kind='five_hour'):
            return {'line': {'type': 'rate_limit_event', 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION,
                             'rate_limit_info': {'status': status, 'rateLimitType': kind, 'resetsAt': int(reset)}}}

        @live_step
        def c_result(inp, out, turns=1, text='done'):
            return {'line': {'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4,
                             'is_error': False, 'num_turns': turns, 'result': text, 'stop_reason': 'end_turn',
                             'total_cost_usd': 0, 'usage': c_usage(inp, out),
                             'modelUsage': {'fixture-model': {'inputTokens': inp, 'outputTokens': out,
                                                              'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0,
                                                              'webSearchRequests': 0, 'costUSD': 0,
                                                              'contextWindow': 200000, 'maxOutputTokens': 32000}},
                             'permission_denials': [], 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION}}

        def submit(unit, configuration):
            """(launch, record): a real dispatch of one normal turn under `configuration`."""
            job = dict(holder=HOLDER, source=str(src), revision='HEAD',
                       payload={'task': 'work the unit', 'script': [c_msg('msg-173', 3, 3),
                                                                    c_rate('allowed', 2000000000), c_result(3, 4)]},
                       adapter='claude', configuration=configuration, deadline=time.time() + 40)
            launch, _ = attempt(lambda: runner.submit(admitted(unit), 'build', **job))
            record, _ = attempt(lambda: runner.wait(launch)) if launch is not None else (None, None)
            return launch, record or {}

        def markers_of(launch):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if launch is not None and data.get('dispatch') == launch.dispatch_id:
                    found.append(data)
            return found

        def options_of(argv):
            """{option: [names]} of the tool options a run was started with, each `--option=value`."""
            found = {}
            for arg in argv or []:
                head, joined, value = arg.partition('=')
                if joined and head in ('--tools', '--disallowedTools'):
                    found.setdefault(head, []).extend(n for n in value.split(',') if n)
            return found

        def event_of(launch, kind):
            return next((e for e in (launch.messages if launch else []) if e.get('event') == kind), {})

        # AC1: a run with no role revision bound is offered exactly the in-run list, the rest switched off.
        launch, record = submit('unit-unbound', {})
        observed = markers_of(launch)
        own = observed[0] if len(observed) == 1 else {}
        init = set((own.get('init') or {}).get('tools') or [])
        options = options_of(own.get('argv'))
        check('launch/no-revision', 'one engine ran the dispatch to its end',
              record.get('state') == 'exited' and len(observed) == 1)
        check('launch/no-revision', 'the tools option names exactly the in-run list %s' % options.get('--tools'),
              options.get('--tools') == sorted(IN_RUN) and len(IN_RUN) == 18)
        check('launch/no-revision', 'the init event offers the in-run list the binary registers, %s missing only %s'
              % (sorted(init), sorted(set(IN_RUN) - init)),
              init == set(IN_RUN) & set(REGISTRY) and sorted(set(IN_RUN) - init) == UNREGISTERED == ['REPL'])
        check('launch/no-revision', 'RemoteTrigger is absent from the init event', bool(init) and 'RemoteTrigger' not in init)
        check('launch/no-revision', 'SendMessage, PushNotification and the claude.ai-writing tools are absent %s'
              % sorted(init.intersection(OUTSIDE)), bool(init) and not init.intersection(OUTSIDE))
        check('launch/no-revision', 'no self_hosted_runner tool is offered',
              bool(init) and not [t for t in init if t.startswith('self_hosted_runner')])
        unbound = (launch, own, options)

        # AC1: the disallowedTools option is the binary's full registry less the launch tool set.
        disallowed = set(options.get('--disallowedTools') or [])
        check('launch/registry', 'disallowedTools is the full registry less the launch tool set [%s extra, %s missing]'
              % (sorted(disallowed - (set(REGISTRY) - set(IN_RUN))), sorted((set(REGISTRY) - set(IN_RUN)) - disallowed)),
              bool(disallowed) and disallowed == set(REGISTRY) - set(IN_RUN))
        check('launch/registry', 'ReportFindings is switched off at launch', 'ReportFindings' in disallowed)
        check('launch/registry', 'every tool the live init offered beyond the in-run list is switched off',
              set(LIVE) - set(IN_RUN) <= disallowed)
        check('launch/registry', 'every registry tool is either launched or switched off, and none is both',
              set(REGISTRY) <= disallowed | set(options.get('--tools') or []) and not disallowed & set(IN_RUN))

        # AC1: a bound role revision's native tools are the launch tool set, beyond the in-run list too.
        granted = ['Bash', 'Edit', 'EnterWorktree', 'Read', 'ReportFindings']
        # VELDO-0127: the accepted writer replaces this suite's former hand-built role revision.
        C127 = load('v173_agent_config', mods / 'control_agent_config.py')
        configs = C127.Configurations(S, writer, domain=DOMAIN, repository=REPOSITORY, signer='owner', sign=sign)
        for base_revision in range(7):
            configs.save({'role': 'builder-173', 'engine': 'claude_code',
                          'native_tools': [{'name': name, 'load': 'always'} for name in granted],
                          'mcp': [], 'skills': [], 'instructions': [], 'settings': {'model': 'fixture-model'}},
                         principal='owner', base=base_revision, command_id='role-173-' + str(base_revision))
        revision = {'role': 'builder-173', 'revision': 7, 'native_tools': granted}
        launch, record = submit('unit-revision', {'role': 'builder-173', 'revision': 7})
        observed = markers_of(launch)
        own = observed[0] if len(observed) == 1 else {}
        init = set((own.get('init') or {}).get('tools') or [])
        options = options_of(own.get('argv'))
        disallowed = set(options.get('--disallowedTools') or [])
        check('launch/revision', 'one engine ran the bound revision\'s dispatch to its end',
              record.get('state') == 'exited' and len(observed) == 1)
        check('launch/revision', 'the tools option names exactly the revision\'s native tools %s' % options.get('--tools'),
              options.get('--tools') == sorted(granted))
        check('launch/revision', 'no granted tool is switched off, and every other registry tool is',
              disallowed == set(REGISTRY) - set(granted) and not disallowed & set(granted))
        check('launch/revision', 'the init event offers exactly the granted tools %s' % sorted(init),
              init == set(granted))
        check('launch/revision', 'an in-run tool the revision does not grant is switched off',
              {'WebSearch', 'Agent'} <= disallowed and not {'WebSearch', 'Agent'} & init)
        revised = (launch, own)
        launch, record = submit('unit-no-list', {'role_revision': {'role': 'builder-173', 'revision': 8}})
        check('launch/revision', 'a bound revision with no native tool list is refused by name before spawn',
              record.get('state') == 'refused' and record.get('refusal') == 'invalid_input:role_revision'
              and not markers_of(launch))

        # Observability: each launch names its tools, its revision and its pinned version, never a value.
        report = event_of(unbound[0], 'baseline').get('baseline') or {}
        tools = report.get('tools') or {}
        check('report/tools', 'an unbound launch reports the in-run source, its launch set and what it switched off',
              tools.get('source') == 'in_run' and tools.get('launch') == sorted(IN_RUN)
              and tools.get('disallowed') == sorted(set(REGISTRY) - set(IN_RUN)) and tools.get('revision') is None)
        check('report/tools', 'the report joins the dispatch and the pinned version whose record it applied',
              report.get('dispatch_id') == (unbound[0].dispatch_id if unbound[0] else None)
              and report.get('executable') == {'engine': 'claude_code', 'version': VERSION, 'sha256': entry['sha256']})
        report = event_of(revised[0], 'baseline').get('baseline') or {}
        tools = report.get('tools') or {}
        check('report/tools', 'a bound launch reports the revision by role and number and its granted tools',
              tools.get('source') == 'role_revision' and tools.get('launch') == sorted(granted)
              and tools.get('revision') == {'role': 'builder-173', 'revision': 7})

        # AC1 and AC2: the shipped record carries the registry the pinned bytes hold and its classification.
        extractor = load('v173_extractor', EXTRACTOR if EXTRACTOR.is_file() else TREE / 'proof/VELDO-0173/extract_tools.py')
        pinned_binary = Path('/home/dmitry/.local/share/claude/versions/2.1.281')
        fresh, error = attempt(lambda: extractor.extract(pinned_binary, TREE / 'proof/VELDO-0062/cli-formats.json'))
        fresh = fresh or {}
        data = pinned_binary.read_bytes() if pinned_binary.is_file() else b''
        at_offsets = [t['name'] for t in fresh.get('registry') or []
                      if data[t['name_offset']:t['name_offset'] + len(t['name']) + 2] != ('"%s"' % t['name']).encode()]
        registry = shipped_entry.get('tool_registry') or []
        check('evidence/registry', 'the shipped registry is a fresh extraction of the pinned bytes [%s]' % error,
              error is None and bool(registry) and registry == fresh.get('tool_registry')
              and shipped_entry.get('sha256') == fresh.get('sha256') == 'sha256:' + hashlib.sha256(data).hexdigest())
        check('evidence/registry', 'every registered tool\'s name is its quoted literal at its recorded offset %s'
              % at_offsets[:3], bool(fresh.get('registry')) and not at_offsets)
        check('evidence/registry', 'the registry holds the live init\'s tools and the outward ones the table lacks',
              set(LIVE) | set(OUTSIDE) <= set(registry) and len(registry) >= 25
              and not set(LIVE) <= set(TABLE22) and 'ReportFindings' not in TABLE22)
        check('evidence/registry', 'every in-run tool is registered but the compiled-out REPL slot',
              set(IN_RUN) - set(registry) == {'REPL'} and data.find(b'function mr(){return null}') == (
                  (fresh.get('unregistered_in_run') or {}).get('REPL') or {}).get('offset'))
        classification = shipped_entry.get('tool_classification') or {}
        check('evidence/classification', 'every registry tool is classified in_run or outward',
              bool(registry) and set(registry) <= set(classification)
              and all(row.get('class') in ('in_run', 'outward') for row in classification.values()))
        check('evidence/classification', 'the in-run tools equal the in-run list of the VELDO-0160 build',
              sorted(n for n, row in classification.items() if row.get('class') == 'in_run') == sorted(IN_RUN))
        check('evidence/classification', 'outward is every registry tool off that list',
              {n for n, row in classification.items() if row.get('class') == 'outward'} == set(registry) - set(IN_RUN))
        hints = {t['name']: t.get('hint') for t in fresh.get('registry') or []}
        check('evidence/classification', 'each reason is read from the tool\'s own definition',
              bool(classification) and classification == fresh.get('tool_classification')
              and all(row.get('reason') and (hints.get(n) is None or hints[n] in row['reason'])
                      for n, row in classification.items()))

        # AC2: a record without the registry or its classification, or leaving a tool unclassified, launches nothing.
        installed = record_path.read_bytes()
        for label, change in (
                ('no tool registry', lambda e: e.pop('tool_registry', None)),
                ('no tool classification', lambda e: e.pop('tool_classification', None)),
                ('a null tool registry', lambda e: e.update(tool_registry=None)),
                ('one registry tool (ReportFindings) left unclassified',
                 lambda e: (e.get('tool_classification') or {}).pop('ReportFindings', None))):
            altered = json.loads(installed)
            change(altered['versions'][VERSION])
            record_path.write_text(json.dumps(altered))
            try:
                launch, record = submit('unit-' + label.split()[1].strip('(') + '-' + os.urandom(3).hex(), {})
            finally:
                record_path.write_bytes(installed)
            check('baseline/required', label + ': refused by name before anything is spawned',
                  record.get('state') == 'refused' and record.get('refusal') == 'missing_evidence:engine_baseline:' + VERSION
                  and not markers_of(launch))
            check('baseline/required', label + ': counted once as a refused baseline',
                  sum(e.get('metrics', {}).get('engine_baseline_refused', 0) for e in (launch.messages if launch else [])) == 1)

        # Controls: the committed evidence is what the extractor reads now; the fake reacts to both options.
        check('fixture/extraction', 'the committed inventory equals a fresh extraction and is what the record carries',
              bool(fresh) and fresh == EVIDENCE and len(EVIDENCE['registry']) == len(set(REGISTRY)))
        check('fixture/extraction', 'every registry entry has its module, offsets and slot',
              all(t.get('module') and t.get('name_offset', -1) >= 0 and t.get('definition_offset', -1) >= 0
                  and t.get('slot') for t in EVIDENCE['registry']))

        def direct(*extra):
            packet = {'payload': {'script': []}}
            env = dict(inherited, VELDO_DISPATCH_ID='control-' + os.urandom(4).hex())
            done = subprocess.run([str(versions / VERSION)] + list(extra), input=json.dumps(packet), env=env,
                                  capture_output=True, text=True, timeout=15)
            found = [json.loads(p.read_text()) for p in sorted(markers.glob('*.json'))]
            found = [m for m in found if m.get('dispatch') == env['VELDO_DISPATCH_ID']]
            return done.returncode, (found[0].get('init') or {}).get('tools') if len(found) == 1 else None
        code, offered = direct()
        check('fixture/fake-default', 'with neither option the fake offers the whole registry, RemoteTrigger among it',
              code == 0 and offered == REGISTRY and 'RemoteTrigger' in offered and 'ReportFindings' in offered)
        code, offered = direct('--tools', 'Read,Bash', '--disallowedTools=Bash')
        check('fixture/fake-default', 'the fake narrows to --tools in both forms and removes --disallowedTools',
              code == 0 and offered == ['Read'])

        # Every line the fake printed is an event of the binary's own table, every field known.
        formats = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())

        def conforms(value, schema):
            kind = schema.get('type')
            if value is None:
                return bool(schema.get('nullable')) or kind == 'any'
            if kind == 'any':
                return True
            if kind == 'object':
                fields = schema.get('fields') or {}
                return (isinstance(value, dict) and not set(value) - set(fields)
                        and all(conforms(value[k], f) if k in value else bool(f.get('optional'))
                                for k, f in fields.items()))
            if kind == 'record':
                return isinstance(value, dict) and all(conforms(v, schema['values']) for v in value.values())
            if kind == 'array':
                return isinstance(value, list) and all(conforms(v, schema.get('items') or {'type': 'any'}) for v in value)
            if kind == 'literal':
                return value == schema.get('value')
            if kind == 'enum':
                return value in (schema.get('values') or [])
            if kind == 'number':
                return type(value) in (int, float) and (not schema.get('int') or type(value) is int)
            if kind == 'boolean':
                return type(value) is bool
            if kind == 'string':
                return isinstance(value, str)
            return False
        printed, bad = set(), []
        for out in sorted(markers.glob('*.out')):
            for raw in out.read_text().splitlines():
                event = json.loads(raw)
                kind = event.get('type')
                name = kind + '/' + event.get('subtype', '') if kind in ('system', 'result') else kind
                schema = formats['claude_code']['events'].get(name)
                if schema is None or not conforms(event, schema):
                    bad.append(name)
                printed.add(name)
        check('format/fake-lines', 'every line the fake printed is an event of the binary\'s own table [%s %s]'
              % (sorted(printed), bad[:4]),
              not bad and {'control_response', 'system/init', 'assistant', 'rate_limit_event', 'result/success'} <= printed)
    except Exception as exc:
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        fake_capture = conform_formats.conform_fake(locals(), '0173_tool_registry')
        for connection in connections:
            connection.close()
        shutil.rmtree(base)
    for name, observed in rows.items():
        ok = bool(observed) and all(value for _, value in observed)
        for label, value in observed:
            if not value:
                print('  VELDO-0173 %s detail: %s' % (name, label))
        expect('VELDO-0173 ' + name, ok)
    for line in conform_formats.describe('0173_tool_registry', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0173_tool_registry', bool(fake_capture[1]) and not fake_capture[0])
    print('VELDO-0173 suite seconds: %.3f' % (time.monotonic() - started))


_v173_suite()
