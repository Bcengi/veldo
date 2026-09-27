"""VELDO-0160: every registered subscription account at once, off an account at its limit, and a
limited run classified and decided re-run or ask, over a real store.

Run: python3 scripts/selftest.py --suite 78_veldo_0160_account_pool

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
suite loads AND the launch receiver process executes, so a registered mutation of a production module
reaches both. Real: a SQLite control store with OpenSSH journal signatures, the account records
(control_accounts) the owner registers over profiles .veldo/accounts.py prepares, VELDO-0036
reservations under their production authorization with the account pool choosing inside them
(control_account_pool), VELDO-0052's Gate, VELDO-0031 claims, a Git source repository, the VELDO-0039
Runner and receiver processes and the trusted wrapper that execs the engine. The engines are fake
`claude` and `codex` executables this suite writes: each records the environment it was started with,
then prints the stream lines its packet scripts (waiting where the script says, on a file this suite
creates) and exits with the scripted code. Every line is built in a shape the installed CLIs print
(Claude Code 2.1.281's stream JSON with its usage-limit message, Codex 0.154.0's exec JSON with its
usage-limit message and MCP tool-call item), and the two format rows check every line against
proof/VELDO-0062/cli-formats.json, the table extract_formats.py reads out of the real binaries. The
re-run-or-ask decision reads fixture records in the form the specification's Notes give, whose engine
payloads are lines of the same formats. No real engine runs, nothing logs in and no credential exists.
Worker launches go through the wrapper without a containment group (`identity: reported`), so the
systemd user manager is never touched. Each row is reported once.
"""


def _v160_suite():
    import contextlib
    import datetime
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
    import uuid

    FORMATS_PATH = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2] \
        / 'proof' / 'VELDO-0062' / 'cli-formats.json'
    FORMATS = json.loads(FORMATS_PATH.read_text())

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
        'control_account_limit.py': ROOT / ".veldo" / "control_account_limit.py",
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'control_reservation_runtime.py': ROOT / ".veldo" / "control_reservation_runtime.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('pool/per-account-isolation', 'pool/one-registration', 'pool/concurrent',
            'limit/stream-exhausted', 'limit/rate-limit-result', 'limit/claude-rejected-texts',
            'decision/rerun', 'decision/ask', 'decision/unreadable-asks', 'decision/same-id-write',
            'decision/unknown-forms', 'decision/redacted-name', 'decision/tool-free-forms', 'format/tool-forms',
            'decision/repl-inner-call', 'decision/task-progress-tool', 'decision/frame-tool-names',
            'decision/subagent-calls', 'decision/no-write-server-reruns', 'decision/nested-work-asks',
            'decision/nested-constructs', 'decision/unconfigured-call-asks', 'decision/remote-agent-asks',
            'pool/moved-off', 'pool/added-account', 'pool/one-run-while-unknown',
            'pool/usage-observes', 'pool/selection-order', 'pool/until-earliest',
            'install/assets', 'format/claude-fake-lines', 'format/codex-fake-lines')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    @contextlib.contextmanager
    def region(*names):
        try:
            yield
        except Exception as exc:  # noqa: BLE001 - a raise reds its rows, never skips them
            for row in names:
                check(row, 'the row ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)

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
    base = Path(tempfile.mkdtemp(prefix='v160-', dir=fast))
    connections = []
    released = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v160_store', mods / 'control_store.py')
        L = load('v160_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        # A tree without this work (the red record's) has no pool and no decision: the rows then fail by
        # their own assertions rather than by a raise.
        POOL = getattr(RES, 'POOL', None)
        LIMIT = load('v160_limit', mods / 'control_account_limit.py')
        HELPER = load('v160_helper', mods / 'accounts.py')
        EL = load('v160_eligibility', mods / 'control_eligibility.py')
        SIG = load('v160_signer', mods / 'control_signer.py')
        GP = load('v160_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-160', 'repository-160', 'builder-160', 'linux-host-160'
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

        events = []
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign,
                                        observe=events.append)
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
        POOLED = [('acct-c1', 'claude_code'), ('acct-c2', 'claude_code'), ('acct-c3', 'claude_code'),
                  ('acct-x1', 'codex')]
        setup_errors = [(a, register(a, p)) for a, p in POOLED]
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
        (src / 'README').write_text('pool source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fake engines: each records its birth environment, then prints what its packet scripts,
        # waiting on a file where the script says, and exits with the scripted code.
        markers = base / 'markers'
        markers.mkdir()
        gates = base / 'gates'
        gates.mkdir()
        engines = base / 'bin'
        engines.mkdir()
        fake = '''#!%s -B
import json, os, sys, time
from pathlib import Path
if sys.argv[1:3] == ['login', 'status']:
    # VELDO-0156: the receiver's check before acceptance, on a ChatGPT login; the 0.154.0 binary prints its
    # login status on stderr.
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
markers = Path(MARKERS)
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
own = {'engine': ENGINE, 'pid': os.getpid(), 'dispatch': dispatch, 'started': time.time(),
       'env': {k: os.environ.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'VELDO_ACCOUNT')}}
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
        CONFIGURATION = {'mcp_servers': {'tracker': {'command': 'tracker-mcp', 'args': []}}, 'tools': ['Read', 'Bash']}
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30)
        ADAPTERS = {'claude': {'engine': 'claude_code', 'host': HOST}, 'codex': {'engine': 'codex', 'host': HOST}}
        pool, pool_error = attempt(lambda: POOL.Pool(ADAPTERS))
        # The one process that prepares every pooled dispatch.
        runner = L.Runner(gate, reservations, dispatches, invoke, account=pool)
        explicit = {}

        def pinned(account):
            if account not in explicit:
                explicit[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return explicit[account]

        fixture_lines = []

        def job(adapter, script, code_=0, deadline=40):
            if adapter == 'codex':
                script = [x_thread()] + list(script)
            fixture_lines.extend((adapter, step['line']) for step in script if 'line' in step)
            return dict(holder=HOLDER, source=str(src), revision='HEAD',
                        payload={'task': 'work the unit', 'script': script, 'code': code_}, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

        def submit(unit, adapter, script, code_=0, via=None):
            """(launch, error): a pooled dispatch, or one on the account `via` names."""
            use = pinned(via) if via else runner
            return attempt(lambda: use.submit(admitted(unit), 'build', **job(adapter, script, code_)))

        def finish(launch, via=None):
            if launch is None:
                return {}
            record, _ = attempt(lambda: (pinned(via) if via else runner).wait(launch))
            return record or {}

        def gate_file(name):
            return str(gates / name)

        def release(name):
            Path(gate_file(name)).write_text('go')
            released.append(name)

        def account_of(launch):
            return ((getattr(launch, 'contract', None) or {}).get('reservation') or {}).get('account')

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def running(launch):
            return launch is not None and getattr(launch, 'result', None) == 'accepted'

        def markers_of(dispatch_id):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    done = markers / ('%d.done' % data['pid'])
                    data['ended'] = json.loads(done.read_text())['ended'] if done.exists() else None
                    found.append(data)
            return found

        def invocation(dispatch_id):
            found = entity(RES.entity('invocation', [DOMAIN, 'invocation/' + dispatch_id]))
            return (found or {}).get('data') or {}

        def worker(dispatch_id):
            found = entity(RES.entity('worker', [DOMAIN, dispatch_id]))
            return (found or {}).get('data') or {}

        def account_record(account):
            return ACC.read(writer, account) or {}

        def history(record, action):
            return next((h['at'] for h in record.get('history') or [] if h.get('action') == action), None)

        def wait_until(predicate, timeout=15.0):
            end = time.time() + timeout
            while time.time() < end:
                if predicate():
                    return True
                time.sleep(0.05)
            return predicate()

        # Stream lines in the shapes the installed CLIs print (the format rows check each one).
        SESSION = 'session-160-' + os.urandom(4).hex()

        def c_usage(inp, out):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': 0,
                    'cache_read_input_tokens': 0,
                    'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0},
                    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}, 'service_tier': 'standard'}

        def c_init():
            return {'line': {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'claude_code_version': '2.1.281',
                             'cwd': '/work', 'tools': ['Read', 'Bash'],
                             'mcp_servers': [{'name': 'tracker', 'status': 'connected'}], 'model': 'configured-model',
                             'permissionMode': 'default', 'slash_commands': [], 'output_style': 'default', 'skills': [],
                             'plugins': [], 'uuid': str(uuid.uuid4()), 'session_id': SESSION}}

        def c_msg(mid, inp, out, content=None):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'configured-model',
                                         'content': content or [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out)}}}

        def c_api_error(text):
            # The binary's API error message: an assistant message wrapping the error, `error` its kind.
            return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION, 'error': 'rate_limit', 'is_api_error_message': True,
                             'api_error_status': 429,
                             'message': {'type': 'message', 'role': 'assistant', 'model': '<synthetic>',
                                         'content': [{'type': 'text', 'text': text}], 'stop_reason': 'stop_sequence',
                                         'stop_sequence': '', 'usage': c_usage(0, 0)}}}

        def c_model_usage(inp, out):
            return {'configured-model': {'inputTokens': inp, 'outputTokens': out, 'cacheReadInputTokens': 0,
                                         'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                         'contextWindow': 200000, 'maxOutputTokens': 32000}}

        def c_result(inp, out, turns=1, text='done', error=False, status=None):
            line = {'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': error,
                    'num_turns': turns, 'result': text, 'stop_reason': 'stop_sequence' if error else 'end_turn',
                    'total_cost_usd': 0, 'usage': c_usage(inp, out), 'modelUsage': c_model_usage(inp, out),
                    'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': SESSION}
            if status is not None:
                line['api_error_status'] = status
            return {'line': line}

        def c_failed(errors):
            return {'line': {'type': 'result', 'subtype': 'error_during_execution', 'duration_ms': 5,
                             'duration_api_ms': 4, 'is_error': True, 'num_turns': 1, 'stop_reason': None,
                             'total_cost_usd': 0, 'usage': c_usage(1, 1), 'modelUsage': c_model_usage(1, 1),
                             'permission_denials': [], 'errors': list(errors), 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION}}

        def c_rate(status, reset, kind='five_hour', utilization=None):
            info = {'status': status, 'rateLimitType': kind}
            if reset is not None:
                info['resetsAt'] = int(reset)
            if utilization is not None:
                info['utilization'] = utilization
            return {'line': {'type': 'rate_limit_event', 'rate_limit_info': info, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION}}

        CLIMIT = FORMATS['claude_code'].get('usage_limit') or {}

        def c_clock(stated, now):
            """The reset time as Claude Code states it, from the binary's format pieces, in UTC."""
            at = datetime.datetime.fromtimestamp(stated, datetime.timezone.utc)
            clock = '%d%s%s' % (at.hour % 12 or 12, ':%02d' % at.minute if at.minute else '', 'am' if at.hour < 12 else 'pm')
            if stated - now > 86400:
                year = ', %d' % at.year if at.year != datetime.datetime.fromtimestamp(now, datetime.timezone.utc).year else ''
                clock = '%s %d%s, %s' % (CLIMIT['months'][at.month - 1], at.day, year, clock)
            return clock + ' (UTC)'

        def c_limit_text(window, stated, now):
            """The usage-limit message of the rate-limit result: the binary's template, its name of the window
            and its reset piece."""
            if not CLIMIT:
                return "You've hit your limit"
            text = CLIMIT['message'] + CLIMIT['names'][window]
            return text + (CLIMIT['resets'] + c_clock(stated, now) if stated is not None else '')

        def x_thread():
            return {'line': {'type': 'thread.started', 'thread_id': 'thread-160-' + os.urandom(4).hex()}}

        def x_started():
            return {'line': {'type': 'turn.started'}}

        def x_done(inp, out):
            return {'line': {'type': 'turn.completed', 'usage': {
                'input_tokens': inp, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': out,
                'reasoning_output_tokens': 0}}}

        def x_error(message):
            return {'line': {'type': 'error', 'message': message}}

        def x_failed(message):
            return {'line': {'type': 'turn.failed', 'error': {'message': message}}}

        XLIMIT = FORMATS['codex']['usage_limit']

        def x_limit_message(stated):
            """Codex's usage-limit message with the minute `stated` as its reset, in the engine's zone (UTC)."""
            at = datetime.datetime.fromtimestamp(stated, datetime.timezone.utc)
            clock = '%d:%02d %s' % (at.hour % 12 or 12, at.minute, 'AM' if at.hour < 12 else 'PM')
            if at.date() != datetime.datetime.now(datetime.timezone.utc).date():
                day = at.day
                suffix = 'th' if 11 <= day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                clock = '%s %d%s, %d %s' % (('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                              'Dec')[at.month - 1], day, suffix, at.year, clock)
            return XLIMIT['message'] + '.' + XLIMIT['retry_at'][0] + clock + '.'

        def x_item(kind, item_id, server, tool, status, result=None):
            item = {'id': item_id, 'type': 'mcp_tool_call', 'server': server, 'tool': tool,
                    'arguments': {'issue': 'CEO-1'}, 'status': status}
            if result is not None:
                item['result'] = result
            return {'type': kind, 'item': item}

        def end_of_minute(ts):
            return (int(ts) // 60) * 60 + 60

        # AC1: three Claude Code accounts and one Codex account run at once, each on its own profile.
        with region('pool/per-account-isolation', 'pool/concurrent'):
            check('pool/per-account-isolation', 'the owner registered the four accounts once each over prepared '
                  'profiles [%s]' % setup_errors, not [e for _, e in setup_errors if e])
            check('pool/per-account-isolation', 'the Runner takes the account pool [%s]' % code(pool_error), pool is not None)
            tokens = {'acct-c1': (3, 4), 'acct-c2': (5, 6), 'acct-c3': (7, 8), 'acct-x1': (9, 10)}
            launches = []
            for n, adapter in enumerate(('claude', 'claude', 'claude', 'codex')):
                if adapter == 'claude':
                    script = [c_init(), c_rate('allowed', time.time() + 7200, 'five_hour', 0.2 + 0.1 * n),
                              c_msg('m-%d' % n, 1, 1), {'wait': gate_file('ac1')}, c_result(*tokens[POOLED[n][0]])]
                else:
                    script = [x_started(), {'wait': gate_file('ac1')}, x_done(*tokens['acct-x1'])]
                launch, error = submit('VELDO-16001-%d' % n, adapter, script)
                launches.append((adapter, launch, error))
            accepted = [launch for _, launch, _ in launches if running(launch)]
            check('pool/concurrent', 'the four dispatches were each accepted and running before any ended [%s]'
                  % [(a, code(e), getattr(launch, 'result', None)) for a, launch, e in launches], len(accepted) == 4)
            # Released only once every engine process is up, so each was alive before any ended.
            wait_until(lambda: all(markers_of(launch.dispatch_id) for launch in accepted), timeout=20)
            release('ac1')
            ended = [(adapter, launch, finish(launch)) for adapter, launch, _ in launches]
            chosen = [account_of(launch) for _, launch, _ in ended]
            check('pool/per-account-isolation', 'the pool spread the three Claude Code dispatches over the three Claude '
                  'Code accounts and the Codex one onto the Codex account [%s]' % chosen,
                  sorted(chosen[:3], key=str) == ['acct-c1', 'acct-c2', 'acct-c3'] and chosen[3] == 'acct-x1')
            profile_seen = []
            for adapter, launch, record in ended:
                account = account_of(launch)
                if launch is None or account is None:
                    check('pool/per-account-isolation', '%s: a dispatch was prepared' % adapter, False)
                    continue
                own = (markers_of(launch.dispatch_id) or [{}])[0]
                env = own.get('env') or {}
                variable = 'CODEX_HOME' if adapter == 'codex' else 'CLAUDE_CONFIG_DIR'
                other = 'CLAUDE_CONFIG_DIR' if adapter == 'codex' else 'CODEX_HOME'
                profile_seen.append(env.get(variable))
                check('pool/per-account-isolation', '%s: the engine ran on exactly its own account\'s registered profile '
                      '(%s) and no other provider\'s, named as that account [%s, %s]'
                      % (account, variable, env.get(variable), env.get('VELDO_ACCOUNT')),
                      record.get('state') == 'exited' and bool(env.get(variable))
                      and env.get(variable) == profiles.get(account) == (account_record(account).get('profiles') or {}).get(HOST)
                      and env.get(other) is None and env.get('VELDO_ACCOUNT') == account)
                call = invocation(launch.dispatch_id)
                check('pool/per-account-isolation', '%s: the invocation was reserved and settled on that account, with '
                      'the tokens its own CLI reported [%s, %s]' % (account, (call.get('context') or {}).get('account'),
                                                                     call.get('charge')),
                      (call.get('context') or {}).get('account') == account and call.get('state') == 'settled'
                      and (call.get('charge') or {}).get('tokens') == sum(tokens[account]))
                trace = worker(launch.dispatch_id).get('selection') or {}
                check('pool/per-account-isolation', '%s: the slot records the pool\'s choice, its candidates and the '
                      'windows read at selection [%s]' % (account, trace.get('chosen')),
                      trace.get('chosen') == account and account in [c['account'] for c in trace.get('candidates') or []]
                      and isinstance(trace.get('windows'), dict))
            check('pool/per-account-isolation', 'the four engines ran on four different profiles [%d]' % len(set(profile_seen)),
                  len(profile_seen) == 4 and len(set(profile_seen)) == 4)
            counted, error = attempt(lambda: POOL.metrics(reservations._records()))
            check('pool/per-account-isolation', 'the metrics count one dispatch on each account [%s]'
                  % ((counted or {}).get('dispatches'), ),
                  (counted or {}).get('dispatches') == {a: 1 for a in tokens})
            shown, error = attempt(lambda: ACC.usage(reservations, accounts))
            charged = {a: ((shown or {}).get('account', {}).get(a) or {}).get('totals', {}).get('tokens') for a in tokens}
            check('pool/per-account-isolation', 'each account\'s shown usage is its own run\'s tokens [%s]' % charged,
                  charged == {a: sum(t) for a, t in tokens.items()})
            spans = [(history(record, 'run'), history(record, 'exit')) for _, _, record in ended]
            check('pool/concurrent', 'the four runs\' recorded start and end times overlap [%s]' % spans,
                  len(spans) == 4 and all(s is not None and e is not None for s, e in spans)
                  and max(s for s, _ in spans) < min(e for _, e in spans))
            lived = [(m.get('started'), m.get('ended')) for _, launch, _ in ended if launch is not None
                     for m in markers_of(launch.dispatch_id)]
            check('pool/concurrent', 'the four engine processes were alive at the same time [%d]' % len(lived),
                  len(lived) == 4 and all(s and e for s, e in lived) and max(s for s, _ in lived) < min(e for _, e in lived))

        # AC4: new work moves off an account at its limit until its reported reset.
        with region('pool/moved-off'):
            reset = int(time.time()) + 12
            exhaust, error = submit('VELDO-16002-exhaust', 'claude',
                                    [c_init(), c_msg('mx', 1, 1), c_rate('rejected', reset, 'five_hour')], 1, via='acct-c1')
            finish(exhaust, via='acct-c1')
            window = (account_record('acct-c1').get('windows') or {}).get('five_hour') or {}
            check('pool/moved-off', 'acct-c1\'s CLI reported its window exhausted, recorded with its reset [%s]' % window,
                  window.get('status') == 'rejected' and window.get('reset_at') == reset)
            spawned_on_c1 = len([p for p in markers.glob('*.json') if json.loads(p.read_text())['env'].get('VELDO_ACCOUNT') == 'acct-c1'])
            moved = []
            for n in range(2):
                launch, error = submit('VELDO-16002-%d' % n, 'claude', [c_init(), {'wait': gate_file('moved')},
                                                                       c_result(1, 1)])
                moved.append((launch, error))
            check('pool/moved-off', 'while acct-c1 is at its limit every new dispatch went to another Claude Code account '
                  '[%s]' % [(account_of(l), code(e)) for l, e in moved],
                  all(running(l) for l, _ in moved) and sorted(account_of(l) for l, _ in moved) == ['acct-c2', 'acct-c3'])
            waiting, error = submit('VELDO-16002-wait', 'claude', [c_init(), c_result(1, 1)])
            passed = getattr(error, 'passed', None) or {}
            check('pool/moved-off', 'the dispatches above were offered before acct-c1\'s reported reset [%.1f s left]'
                  % (reset - time.time()), time.time() < reset)
            seen = [e for e in events if e.get('outcome') == 'refused' and str(e.get('refusal', '')).startswith('no_account')]
            check('pool/moved-off', 'the refusal is observed with each account\'s reason [%s]'
                  % (seen[-1] if seen else None), bool(seen) and seen[-1].get('passed') == passed)
            check('pool/moved-off', 'with the other two at their concurrency, the next dispatch waits: refused before '
                  'anything is prepared, "no account until" acct-c1\'s reported reset, acct-c1 passed over at its limit '
                  '[%s, %s]' % (code(error), passed),
                  waiting is None and code(error) == 'no_account_until:%d' % reset
                  and passed.get('acct-c1') == 'account_limit:five_hour'
                  and passed.get('acct-c2') == passed.get('acct-c3') == 'account_concurrency')
            later = len([p for p in markers.glob('*.json') if json.loads(p.read_text())['env'].get('VELDO_ACCOUNT') == 'acct-c1'])
            on_c1 = [r for r in (json.loads(d) for (d,) in writer.execute(
                "SELECT data FROM entities WHERE kind='subscription_reservation'"))
                if r.get('type') == 'worker' and (r.get('context') or {}).get('account') == 'acct-c1']
            check('pool/moved-off', 'nothing was sent to acct-c1 before its reset: no slot and no process after its '
                  'exhausting run [%d slots, %d processes]' % (len(on_c1), later - spawned_on_c1),
                  len(on_c1) == 2 and later == spawned_on_c1)
            release('moved')
            for launch, _ in moved:
                finish(launch)
            wait_until(lambda: time.time() > reset + 0.5, timeout=15)
            after = []
            for n in range(2):
                launch, error = submit('VELDO-16002-busy-%d' % n, 'claude', [c_init(), {'wait': gate_file('reset')},
                                                                            c_result(1, 1)])
                after.append((launch, error))
            back, error = submit('VELDO-16002-back', 'claude', [c_init(), {'wait': gate_file('reset')}, c_result(1, 1)])
            check('pool/moved-off', 'at its reported reset acct-c1 takes work again [%s, %s]'
                  % ([account_of(l) for l, _ in after], (account_of(back), code(error))),
                  running(back) and account_of(back) == 'acct-c1'
                  and sorted(account_of(l) for l, _ in after) == ['acct-c2', 'acct-c3'])
            release('reset')
            for launch, _ in after + [(back, None)]:
                finish(launch)

        # AC4: an account registered while work runs takes work with nothing restarted, and admits one run at a
        # time until its first observation.
        with region('pool/added-account', 'pool/one-run-while-unknown'):
            busy = []
            for n in range(3):
                launch, error = submit('VELDO-16003-%d' % n, 'claude', [c_init(), {'wait': gate_file('added')},
                                                                       c_result(1, 1)])
                busy.append(launch)
            check('pool/added-account', 'the three Claude Code accounts are each running a worker [%s]'
                  % [account_of(l) for l in busy],
                  all(running(l) for l in busy) and sorted(account_of(l) for l in busy) == ['acct-c1', 'acct-c2', 'acct-c3'])
            me = L.process_identity(os.getpid())
            workers = {l.dispatch_id: rec(l.dispatch_id).get('process') for l in busy if l is not None}
            error = register('acct-c4', 'claude_code', concurrency=2)
            check('pool/added-account', 'the owner registered and prepared a fourth Claude Code account while they run '
                  '[%s]' % error, error is None and account_record('acct-c4').get('status') == 'active')
            first, error = submit('VELDO-16003-new', 'claude', [c_init(), {'wait': gate_file('observe')},
                                                               c_rate('allowed', time.time() + 7200, 'five_hour', 0.05),
                                                               {'wait': gate_file('added')}, c_result(1, 1)])
            check('pool/added-account', 'the next dispatch launched on the new account [%s, %s]'
                  % (account_of(first), code(error)), running(first) and account_of(first) == 'acct-c4')
            same = [dispatch for dispatch, process in workers.items()
                    if process and rec(dispatch).get('state') == 'running'
                    and {k: v for k, v in L.process_identity(process['pid']).items() if k in ('pid', 'start', 'boot_id')}
                    == {k: process.get(k) for k in ('pid', 'start', 'boot_id')}]
            check('pool/added-account', 'the process that prepares dispatches and every running worker kept its process '
                  'identity and start time [%d of %d workers]' % (len(same), len(workers)),
                  L.process_identity(os.getpid()) == me and len(same) == len(workers) == 3)
            second, error = submit('VELDO-16003-unknown', 'claude', [c_init(), c_result(1, 1)])
            passed = getattr(error, 'passed', None) or {}
            check('pool/one-run-while-unknown', 'before its first observation the new account runs one: a second unit '
                  'offered with it waits, the new account passed over at its one-run bound [%s, %s]'
                  % (code(error), passed.get('acct-c4')),
                  second is None and code(error) == 'no_account' and passed.get('acct-c4') == 'account_unobserved:one_run')
            release('observe')
            observed = wait_until(lambda: bool(account_record('acct-c4').get('windows')))
            check('pool/one-run-while-unknown', 'the running unit reported the account\'s first observation [%s]'
                  % account_record('acct-c4').get('windows'), observed)
            again, error = submit('VELDO-16003-unknown-again', 'claude', [c_init(), {'wait': gate_file('added')},
                                                                         c_result(1, 1)])
            check('pool/one-run-while-unknown', 'after it the waiting unit launched on the new account, its second run '
                  'at once [%s, %s]' % (account_of(again), code(error)),
                  running(again) and account_of(again) == 'acct-c4' and rec(first.dispatch_id).get('state') == 'running')
            release('added')
            for launch in busy + [first, again]:
                finish(launch)

        # AC4: usage its CLI reported is an account's first observation too, the only one Codex gives, so a
        # Codex account is not held at one run for ever.
        with region('pool/usage-observes'):
            error = register('acct-x2', 'codex', concurrency=2)
            check('pool/usage-observes', 'the owner registered a second Codex account, concurrency two [%s]' % error,
                  error is None)
            seed, error = submit('VELDO-16005-seed', 'codex', [x_started(), x_done(2, 3)], via='acct-x2')
            finish(seed, via='acct-x2')
            call = invocation(seed.dispatch_id) if seed is not None else {}
            check('pool/usage-observes', 'its one run reported usage and no rate-limit window [%s, %s]'
                  % (call.get('observed'), account_record('acct-x2').get('windows')),
                  call.get('state') == 'settled' and (call.get('observed') or {}).get('tokens') == 5
                  and not account_record('acct-x2').get('windows'))
            held = []
            for n in range(3):
                launch, error = submit('VELDO-16005-%d' % n, 'codex', [x_started(), {'wait': gate_file('usage')},
                                                                      x_done(1, 1)])
                held.append((launch, error))
            check('pool/usage-observes', 'observed by its usage alone, acct-x2 admits its concurrency: three Codex '
                  'dispatches run at once, two of them on acct-x2 [%s]' % [(account_of(l), code(e)) for l, e in held],
                  all(running(l) for l, _ in held)
                  and sorted(account_of(l) for l, _ in held) == ['acct-x1', 'acct-x2', 'acct-x2'])
            release('usage')
            for launch, _ in held:
                finish(launch)

        # AC4 and the Notes' order: the lowest last reported utilization on the tightest window, an unknown one
        # after every known one, then the fewest active runs, then the least recently used.
        with region('pool/selection-order'):
            for account, used in (('acct-c2', 0.7), ('acct-c3', 0.1), ('acct-c4', 0.1)):
                launch, error = submit('VELDO-16006-%s' % account, 'claude',
                                       [c_init(), c_rate('allowed', time.time() + 7200, 'five_hour', used),
                                        c_msg('mu-' + account, 1, 1), c_result(1, 1)], via=account)
                finish(launch, via=account)
            shown, error = attempt(lambda: {a: POOL.utilization(account_record(a), time.time())
                                            for a in ('acct-c1', 'acct-c2', 'acct-c3', 'acct-c4')})
            check('pool/selection-order', 'the idle Claude Code accounts last reported 0.7 (acct-c2), 0.1 (acct-c3, then '
                  'acct-c4, used last) and nothing current (acct-c1) [%s, %s]' % (shown, code(error)),
                  shown == {'acct-c1': None, 'acct-c2': 0.7, 'acct-c3': 0.1, 'acct-c4': 0.1})
            chosen, error = submit('VELDO-16006-pick', 'claude', [c_init(), {'wait': gate_file('order')}, c_result(1, 1)])
            order = [c.get('account') for c in (worker(chosen.dispatch_id).get('selection') or {}).get('candidates') or []] \
                if chosen is not None else []
            check('pool/selection-order', 'the dispatch went to the lowest utilization and, of the two at 0.1, to the '
                  'one used least recently, acct-c3 [%s, %s]' % (account_of(chosen), code(error)),
                  running(chosen) and account_of(chosen) == 'acct-c3')
            check('pool/selection-order', 'the candidates are ranked lowest utilization first, least recently used '
                  'first among equals, the unknown last [%s]' % order,
                  order == ['acct-c3', 'acct-c4', 'acct-c2', 'acct-c1'])
            release('order')
            finish(chosen)

        # AC4 and the Notes: with no candidate the dispatch waits "no account until" the EARLIEST time an account
        # reopens, an account reopening only when every window it has exhausted has reset.
        with region('pool/until-earliest'):
            now = int(time.time())
            exhausted = {'acct-c1': [('five_hour', now + 900)], 'acct-c2': [('five_hour', now + 600)],
                         'acct-c3': [('five_hour', now + 300), ('seven_day', now + 1500)],
                         'acct-c4': [('five_hour', now + 1200)]}
            for account, windows in exhausted.items():
                launch, error = submit('VELDO-16007-%s' % account, 'claude', [c_init(), c_msg('mz-' + account, 1, 1)]
                                       + [c_rate('rejected', at, kind) for kind, at in windows], 1, via=account)
                finish(launch, via=account)
            recorded = {a: sorted((w, ((account_record(a).get('windows') or {}).get(w) or {}).get('reset_at'))
                                  for w, _ in ws) for a, ws in exhausted.items()}
            check('pool/until-earliest', 'each Claude Code account\'s CLI reported its windows exhausted, recorded with '
                  'their resets [%s]' % recorded, recorded == {a: sorted(ws) for a, ws in exhausted.items()})
            waiting, error = submit('VELDO-16007-wait', 'claude', [c_init(), c_result(1, 1)])
            passed = getattr(error, 'passed', None) or {}
            check('pool/until-earliest', 'with every Claude Code account at its limit the dispatch waits until the '
                  'earliest reopening, acct-c2\'s in 600 s, not acct-c3\'s five-hour reset in 300 s (its weekly window '
                  'stays exhausted to 1500 s) nor the latest [%s, %s]' % (code(error), passed),
                  waiting is None and code(error) == 'no_account_until:%d' % (now + 600)
                  and all(str(passed.get(a)).startswith('account_limit:') for a in exhausted))

        # AC2: a run its account's limit stopped is classified account_limit with its window and reset; no other.
        with region('limit/stream-exhausted', 'limit/rate-limit-result'):
            for account, provider in (('acct-l1', 'claude_code'), ('acct-l2', 'claude_code'), ('acct-l3', 'claude_code'),
                                      ('acct-l4', 'codex'), ('acct-l5', 'codex'), ('acct-l6', 'codex'),
                                      ('acct-l7', 'claude_code')):
                error = register(account, provider)
                if error:
                    check('limit/stream-exhausted', 'registered %s [%s]' % (account, error), False)
            now = time.time()
            stated = now + 7200 + 37
            cases = (
                ('limit/stream-exhausted', 'Claude Code', 'acct-l1', 'claude',
                 [c_init(), c_msg('ms', 1, 1), c_rate('rejected', stated, 'seven_day', 1.0)],
                 {'window': 'seven_day', 'reset_at': int(stated), 'signal': 'stream'}),
                ('limit/rate-limit-result', 'Claude Code', 'acct-l2', 'claude',
                 [c_init(), c_api_error(c_limit_text('five_hour', stated, now)),
                  c_result(0, 0, text=c_limit_text('five_hour', stated, now), error=True, status=429)],
                 {'window': 'five_hour', 'reset_at': end_of_minute(stated), 'signal': 'result'}),
                ('limit/stream-exhausted', 'Codex', 'acct-l4', 'codex',
                 [x_started(), x_error(x_limit_message(stated))],
                 {'window': 'usage_limit', 'reset_at': end_of_minute(stated), 'signal': 'stream'}),
                ('limit/rate-limit-result', 'Codex', 'acct-l5', 'codex',
                 [x_started(), x_failed(x_limit_message(stated))],
                 {'window': 'usage_limit', 'reset_at': end_of_minute(stated), 'signal': 'result'}),
                ('limit/stream-exhausted', 'Claude Code', 'acct-l3', 'claude',
                 [c_init(), c_msg('mf', 1, 1), c_failed(['the tool failed'])], None),
                ('limit/rate-limit-result', 'Claude Code (a 429 that is not the account\'s limit)', 'acct-l3', 'claude',
                 [c_init(), c_api_error((CLIMIT.get('not_account') or ['Server is temporarily limiting requests'])[0]),
                  c_result(0, 0, text=(CLIMIT.get('not_account') or ['Server is temporarily limiting requests'])[0],
                           error=True, status=429)], None),
                ('limit/stream-exhausted', 'Claude Code (a window reported exhausted, then open again)', 'acct-l7',
                 'claude', [c_init(), c_rate('rejected', stated, 'five_hour'), c_rate('allowed', stated, 'five_hour', 0.5),
                            c_msg('mo', 1, 1), c_failed(['the tool failed'])], None),
                ('limit/stream-exhausted', 'Codex', 'acct-l6', 'codex',
                 [x_started(), x_failed('internal error; agent loop died unexpectedly')], None))
            for row, engine, account, adapter, script, expected in cases:
                launch, error = submit('VELDO-16004-%s-%d' % (account, len(fixture_lines)), adapter, script, 1, via=account)
                record = finish(launch, via=account)
                call = invocation(launch.dispatch_id) if launch is not None else {}
                windows = account_record(account).get('windows') or {}
                if expected is None:
                    check(row, '%s: an ordinary nonzero exit ends as the failure it is, not account_limit, and records '
                          'no exhausted window on the account [%s, %s, %s]' % (engine, call.get('outcome'), call.get('limit'),
                                                                              sorted(windows)),
                          record.get('state') == 'exited' and call.get('outcome') == 'failed' and 'limit' not in call
                          and not any(w.get('status') == 'rejected' for w in windows.values()))
                    continue
                recorded = windows.get(expected['window']) or {}
                check(row, '%s: the run is classified account_limit with its window and reset time [%s, %s]'
                      % (engine, call.get('outcome'), call.get('limit')),
                      record.get('state') == 'exited' and call.get('outcome') == 'account_limit'
                      and call.get('limit') == expected)
                check(row, '%s: the window and reset time are recorded on the account, exhausted [%s]' % (engine, recorded),
                      recorded.get('status') == 'rejected' and recorded.get('reset_at') == expected['reset_at']
                      and recorded.get('source_dispatch') == launch.dispatch_id)
                counted, error = attempt(lambda: POOL.metrics(reservations._records()))
                check(row, '%s: the metrics count the run ended account_limit on its account and window [%s]'
                      % (engine, ((counted or {}).get('account_limit') or {}).get(account)),
                      ((counted or {}).get('account_limit') or {}).get(account) == {expected['window']: 1})

        # AC2: Claude Code's other texts for the account refused, read out of the binary, each end account_limit.
        with region('limit/claude-rejected-texts'):
            REJECTED = CLIMIT.get('rejected') or []
            now = time.time()
            stated = now + 5400 + 23
            texts = [(REJECTED[0] if REJECTED else 'none') + CLIMIT.get('resets', '') + c_clock(stated, now)
                     + CLIMIT.get('progress_saved', '')]
            texts += [t + CLIMIT['admin_suffix'] if t in (CLIMIT.get('admin_suffixed') or []) else t for t in REJECTED]
            check('limit/claude-rejected-texts', 'the binary gives its rejected-status texts, the out-of-credits, org, '
                  'seat, service, admin and $0-group ones [%d]' % len(REJECTED), len(REJECTED) == 8)
            refused = []
            for n, text in enumerate(texts):
                account = 'acct-r%d' % n
                error = register(account, 'claude_code')
                launch, error = (None, error) if error else submit(
                    'VELDO-16008-%d' % n, 'claude',
                    [c_init(), c_api_error(text), c_result(0, 0, text=text, error=True, status=429)], 1, via=account)
                refused.append((account, text, launch, error))
            for account, text, launch, error in refused:
                record = finish(launch, via=account)
                call = invocation(launch.dispatch_id) if launch is not None else {}
                window = (account_record(account).get('windows') or {}).get('unified') or {}
                expected = {'window': 'unified', 'reset_at': end_of_minute(stated) if text == texts[0] else None,
                            'signal': 'result'}
                check('limit/claude-rejected-texts', '%r: the run is classified account_limit, the unified window with '
                      'the reset it states, recorded exhausted on the account [%s, %s, %s, %s]'
                      % (text, code(error), call.get('outcome'), call.get('limit'), window.get('status')),
                      record.get('state') == 'exited' and call.get('outcome') == 'account_limit'
                      and call.get('limit') == expected and window.get('status') == 'rejected'
                      and window.get('reset_at') == expected['reset_at'])

        # AC3: the re-run-or-ask decision over fixture records in the form the Notes give.
        def record_of(lines):
            """A fixture record: every line in sequence, with its receive time, stream, redaction and payload."""
            return [{'sequence': n, 'received_at': 1790000000.0 + n / 10, 'stream': stream, 'redacted': [],
                     'payload': payload} for n, (stream, payload) in enumerate(lines, 1)]

        def tool_use(block_id, name):
            return {'type': 'tool_use', 'id': block_id, 'name': name, 'input': {'issue': 'CEO-1'}}

        def claude_record(names):
            lines = [('wrapper', {'schema': 'veldo.launch_identity/v1'}), ('engine', c_init()['line'])]
            for n, name in enumerate(names):
                message = c_msg('md-%d' % n, 1, 1, [tool_use('toolu_%d' % n, name)])['line']
                lines += [('engine', message), ('engine', message)]  # a message is streamed more than once
            lines += [('stderr', 'warning: slow tool'), ('engine', c_result(1, 1)['line'])]
            for _, payload in lines:
                if isinstance(payload, dict) and payload.get('type') in ('system', 'assistant', 'result'):
                    fixture_lines.append(('claude', payload))
            return record_of(lines)

        def codex_record(calls):
            lines = [('engine', x_thread()['line']), ('engine', x_started()['line'])]
            for n, (server, tool) in enumerate(calls):
                lines += [('engine', x_item('item.started', 'item_%d' % n, server, tool, 'in_progress')),
                          ('engine', x_item('item.completed', 'item_%d' % n, server, tool, 'completed',
                                            {'content': [], 'structured_content': None}))]
            lines += [('engine', x_done(1, 1)['line'])]
            fixture_lines.extend(('codex', payload) for stream, payload in lines if stream == 'engine')
            return record_of(lines)
        SERVERS = [{'name': 'tracker', 'catalog_id': 'mcp_server:tracker', 'revision': 3},
                   {'name': 'wiki', 'catalog_id': 'mcp_server:wiki', 'revision': 1}]
        MARKS = [{'catalog_id': 'mcp_server:tracker', 'revision': 3, 'read_only_tools': ['get_issue', 'search']},
                 {'catalog_id': 'mcp_server:wiki', 'revision': 1, 'read_only_tools': []}]

        def decide(record, provider, servers=None):
            if LIMIT is None:
                return None, 'no decision module'
            found, error = attempt(lambda: LIMIT.decide(record, SERVERS if servers is None else servers, MARKS,
                                                        provider))
            return found, code(error)

        # The call-by-call rules alone (the third rule). A record showing a construct that can run hidden nested work
        # never reaches them through `decide` (a write-capable server asks first, decision/nested-work-asks; none
        # re-runs, decision/no-write-server-reruns), so the rows that judge how they read such a record drive them.
        def by_calls(record, provider):
            if LIMIT is None or not callable(getattr(LIMIT, 'decide_by_calls', None)):
                return None, 'no call-by-call decision'
            found, error = attempt(lambda: LIMIT.decide_by_calls(record, SERVERS, MARKS, provider))
            return found, code(error)

        def named(found):
            return sorted((c['sequence'], c['server'], c['tool'], c['catalog_id'], c['revision'], c['reason'])
                      for c in (found or {}).get('calls') or [])

        with region('decision/rerun', 'decision/ask'):
            for provider, build, wrap in (('claude_code', claude_record, lambda s, t: 'mcp__%s__%s' % (s, t)),
                                          ('codex', codex_record, lambda s, t: (s, t))):
                none = build(['Bash'] if provider == 'claude_code' else [])
                reads = build([wrap('tracker', 'get_issue'), wrap('tracker', 'search')])
                for label, record in (('no MCP call', none), ('only calls to tools marked read-only', reads)):
                    found, error = decide(record, provider)
                    check('decision/rerun', '%s, %s: decided re-run, naming no call [%s, %s]'
                          % (provider, label, (found or {}).get('decision'), error),
                          (found or {}).get('decision') == 'rerun' and (found or {}).get('calls') == []
                          and (found or {}).get('mcp_calls') == (0 if record is none else 2)
                          and (found or {}).get('basis') == 'calls')
                writes = build([wrap('tracker', 'get_issue'), wrap('tracker', 'add_comment')])
                unmarked = build([wrap('wiki', 'read_page')])
                elsewhere = build([wrap('mailer', 'send')])
                first = 5  # the first line showing the second call of a two-call record, in both engines' records
                for label, record, expected in (
                        ('a call to a tool not marked read-only', writes,
                         [(first, 'tracker', 'add_comment', 'mcp_server:tracker', 3, 'not_marked_read_only')]),
                        ('a call to a tool of a server whose revision marks nothing', unmarked,
                         [(first - 2, 'wiki', 'read_page', 'mcp_server:wiki', 1, 'not_marked_read_only')]),
                        ('a call to a server the configuration does not list', elsewhere,
                         [(first - 2, 'mailer', 'send', None, None, 'unconfigured_call')])):
                    found, error = decide(record, provider)
                    basis = 'unconfigured_call' if record is elsewhere else 'calls'
                    check('decision/ask', '%s, %s: decided ask, naming exactly that call [%s, %s]'
                          % (provider, label, (found or {}).get('decision'), named(found) or error),
                          (found or {}).get('decision') == 'ask' and named(found) == expected
                          and (found or {}).get('basis') == basis)
                # The call-by-call rules alone name an unlisted server's call too (`decide` asks first, by the call
                # that contradicts the configuration, decision/unconfigured-call-asks).
                found, error = by_calls(elsewhere, provider)
                check('decision/ask', '%s, the call-by-call rules alone: a call to a server the configuration does not '
                      'list asks, naming it [%s, %s]' % (provider, (found or {}).get('decision'), named(found) or error),
                      (found or {}).get('decision') == 'ask'
                      and named(found) == [(first - 2, 'mailer', 'send', None, None, 'server_not_configured')])
                gap = [dict(line) for line in writes]
                gap[2]['sequence'] = 9
                found, error = decide(gap, provider)
                check('decision/ask', '%s: a record with a gap in its sequence is refused by name, never decided [%s]'
                      % (provider, error), found is None and error == 'invalid_input:record_sequence')

        # AC3, fail safe: an engine line the decision cannot read (VELDO-0141 AC4's redaction can make one) asks,
        # naming that line, never decides re-run.
        with region('decision/unreadable-asks'):
            for provider in ('claude_code', 'codex'):
                if provider == 'claude_code':
                    head = [('wrapper', {'schema': 'veldo.launch_identity/v1'}), ('engine', c_init()['line'])]
                    tail = [('engine', c_result(1, 1)['line'])]
                    write = c_msg('mr', 1, 1, [tool_use('toolu_r', 'mcp__tracker__add_comment')])['line']
                    inner = write['message']['content'][0]['input']
                    nameless = c_msg('mn', 1, 1, [dict(tool_use('toolu_n', 'x'), name=None)])['line']
                    readable = c_msg('mb', 1, 1, [dict(tool_use('toolu_b', 'Bash'),
                                                       input={'command': '[REDACTED:known_pattern]'})])['line']
                else:
                    head = [('engine', x_thread()['line']), ('engine', x_started()['line'])]
                    tail = [('engine', x_done(1, 1)['line'])]
                    write = x_item('item.started', 'item_r', 'tracker', 'add_comment', 'in_progress')
                    inner = write['item']['arguments']
                    nameless = x_item('item.started', 'item_n', None, 'add_comment', 'in_progress')
                    readable = dict(x_thread()['line'], thread_id='[REDACTED:high_entropy]')
                text = json.dumps(write)
                spanned = text.replace(json.dumps(inner), '[REDACTED:high_entropy]')
                forms = (('its JSON text truncated', text[:-3], []),
                         ('a redacted span in place of its input, breaking the JSON', spanned, ['high_entropy']),
                         ('the whole payload redacted', '[redacted]', ['known_pattern']),
                         ('its event wrapped in a list', [write], []),
                         ('a tool call whose %s is not a string' % ('name' if provider == 'claude_code' else 'server'),
                          nameless, []))
                for label, payload, kinds in forms:
                    record = record_of(head + [('engine', payload)] + tail)
                    record[len(head)]['redacted'] = kinds
                    found, error = decide(record, provider)
                    expected = [(len(head) + 1, None, None, None, None, 'redacted_unreadable' if kinds else 'unreadable')]
                    check('decision/unreadable-asks', '%s, an engine line holding a write with %s: decided ask, naming that '
                          'line [%s, %s]' % (provider, label, (found or {}).get('decision'), named(found) or error),
                          spanned != text and (found or {}).get('decision') == 'ask' and named(found) == expected)
                record = record_of(head + [('engine', readable)] + tail)
                record[len(head)]['redacted'] = ['known_pattern']
                found, error = decide(record, provider)
                check('decision/unreadable-asks', '%s: a redacted line whose event still reads is decided by its calls '
                      '(none here: re-run) [%s, %s]' % (provider, (found or {}).get('decision'), named(found) or error),
                      (found or {}).get('decision') == 'rerun' and named(found) == [])

        # AC3: one call id shown first as a read-only call and then naming a write counts the write.
        with region('decision/same-id-write'):
            for provider in ('claude_code', 'codex'):
                if provider == 'claude_code':
                    lines = [('engine', c_init()['line'])] + [
                        ('engine', c_msg('ms-%s' % tool, 1, 1, [tool_use('toolu_same', 'mcp__tracker__' + tool)])['line'])
                        for tool in ('get_issue', 'add_comment')] + [('engine', c_result(1, 1)['line'])]
                else:
                    lines = [('engine', x_thread()['line']), ('engine', x_started()['line']),
                             ('engine', x_item('item.started', 'item_same', 'tracker', 'get_issue', 'in_progress')),
                             ('engine', x_item('item.completed', 'item_same', 'tracker', 'add_comment', 'completed',
                                               {'content': [], 'structured_content': None})),
                             ('engine', x_done(1, 1)['line'])]
                found, error = decide(record_of(lines), provider)
                at = 3 if provider == 'claude_code' else 4
                check('decision/same-id-write', '%s: the id shown read-only and then naming a write is decided ask, naming '
                      'the write [%s, %s]' % (provider, (found or {}).get('decision'), named(found) or error),
                      (found or {}).get('decision') == 'ask'
                      and named(found) == [(at, 'tracker', 'add_comment', 'mcp_server:tracker', 3, 'not_marked_read_only')])

        # AC3, fail closed (the lead's decision): a tool-call form the decision does not recognize is an unknown
        # call and asks, naming its line and form; the forms are the binaries' own (cli-formats.json tool_forms).
        CFORMS = FORMATS['claude_code'].get('tool_forms') or {}
        XFORMS = FORMATS['codex'].get('tool_forms') or {}

        def c_line(kind, **fields):
            return dict({'type': kind, 'uuid': str(uuid.uuid4()), 'session_id': SESSION}, **fields)

        def c_user(content):
            return c_line('user', message={'role': 'user', 'content': content}, parent_tool_use_id=None)

        def c_stream(event):
            return c_line('stream_event', event=event, parent_tool_use_id=None)

        def c_blocks(blocks):
            return c_msg('mu-%s' % os.urandom(3).hex(), 1, 1, blocks)['line']

        def x_any(kind, item_id, **fields):
            return {'type': 'item.started', 'item': dict({'id': item_id, 'type': kind}, **fields)}

        def forms(found):
            return sorted((c['sequence'], c['reason'], c.get('form')) for c in (found or {}).get('calls') or [])

        c_head = [('wrapper', {'schema': 'veldo.launch_identity/v1'}), ('engine', c_init()['line'])]
        c_tail = [('engine', c_result(1, 1)['line'])]
        x_head = [('engine', x_thread()['line']), ('engine', x_started()['line'])]
        x_tail = [('engine', x_done(1, 1)['line'])]
        # (engine, what, lines, the form each names, the table that lists it or None for a type no table lists)
        UNKNOWN = (
            ('claude_code', 'an mcp_tool_use block', [c_blocks([{'type': 'mcp_tool_use', 'id': 'mcptoolu_1',
                                                                 'name': 'add_comment', 'server_name': 'tracker',
                                                                 'input': {}}])],
             'mcp_tool_use', 'response_blocks'),
            ('claude_code', 'an mcp_tool_result block', [c_blocks([{'type': 'mcp_tool_result', 'tool_use_id': 'mcptoolu_2',
                                                                    'is_error': False, 'content': []}])],
             'mcp_tool_result', 'response_blocks'),
            ('claude_code', 'a server_tool_use block', [c_blocks([{'type': 'server_tool_use', 'id': 'srvtoolu_1',
                                                                   'name': 'web_fetch', 'input': {}}])],
             'server_tool_use', 'response_blocks'),
            ('claude_code', 'a stream_event starting a tool_use block',
             [c_stream({'type': 'content_block_start', 'index': 0,
                        'content_block': tool_use('toolu_s1', 'mcp__tracker__add_comment')})],
             'stream_event:tool_use', 'response_blocks'),
            ('claude_code', 'a stream_event starting a message that holds a tool_use',
             [c_stream({'type': 'message_start', 'message': {'id': 'ms-1', 'role': 'assistant',
                                                             'content': [tool_use('toolu_s2', 'Bash')]}})],
             'stream_event:tool_use', 'response_blocks'),
            ('claude_code', 'a stream_event of a type the schema does not name',
             [c_stream({'type': 'unlisted_stream_event'})], 'stream_event:unlisted_stream_event', None),
            ('claude_code', 'a user tool_result for an id never seen',
             [c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_never', 'content': 'commented'}])],
             'tool_result', 'request_blocks'),
            ('claude_code', 'a tool_use block in a user message', [c_user([tool_use('toolu_u', 'mcp__tracker__search')])],
             'tool_use', 'request_blocks'),
            ('claude_code', 'a tool_progress for an id never seen',
             [c_line('tool_progress', tool_use_id='toolu_never', tool_name='Bash',
                     parent_tool_use_id=None, elapsed_time_seconds=1)], 'tool_progress', 'messages'),
            ('claude_code', 'a tool_use_summary of an id never seen',
             [c_line('tool_use_summary', summary='commented', preceding_tool_use_ids=['toolu_never'])],
             'tool_use_summary', 'messages'),
            ('claude_code', 'a content block of a type no table lists', [c_blocks([{'type': 'unlisted_block', 'id': 'x1'}])],
             'unlisted_block', None),
            ('claude_code', 'a message of a type no table lists', [c_line('unlisted_message')],
             'message:unlisted_message', None),
            ('claude_code', 'a system message of a subtype no table lists', [c_line('system', subtype='unlisted_subtype')],
             'message:system/unlisted_subtype', None),
            # The frames the CLI writes outside the message union whose schema may carry a tool call.
            ('claude_code', 'a can_use_tool control request (outside the message union)',
             [{'type': 'control_request', 'request_id': 'req-1',
               'request': {'subtype': 'can_use_tool', 'tool_name': 'mcp__tracker__add_comment', 'input': {},
                           'tool_use_id': 'toolu_perm'}}], 'message:control_request', 'frames'),
            ('claude_code', 'a control response (outside the message union)',
             [{'type': 'control_response', 'response': {'subtype': 'success', 'request_id': 'req-2', 'response': {}}}],
             'message:control_response', 'frames'),
            ('claude_code', 'a transcript mirror (outside the message union)',
             [{'type': 'transcript_mirror', 'filePath': '/work/t.jsonl', 'entries': [{'type': 'assistant'}]}],
             'message:transcript_mirror', 'frames'),
            ('codex', 'a dynamic_tool_call item', [x_any('dynamic_tool_call', 'item_d', tool='add_comment',
                                                         arguments={}, status='in_progress')],
             'dynamic_tool_call', 'thread_items'),
            ('codex', 'a collab_agent_tool_call item', [x_any('collab_agent_tool_call', 'item_c', tool='spawn_agent',
                                                              status='in_progress')],
             'collab_agent_tool_call', 'thread_items'),
            ('codex', 'a sub_agent_activity item', [x_any('sub_agent_activity', 'item_a')], 'sub_agent_activity',
             'thread_items'),
            ('codex', "exec's own collab_tool_call item (a sub-agent call)",
             [x_any('collab_tool_call', 'item_cc', tool='spawn_agent', status='in_progress')], 'collab_tool_call',
             'exec_items'),
            ('codex', 'an item of a type no table lists', [x_any('unlisted_item', 'item_x')], 'unlisted_item', None),
            ('codex', 'an event of a type no table lists', [{'type': 'turn.unlisted'}], 'event:turn.unlisted', None),
        )
        with region('decision/unknown-forms'):
            for provider, what, lines, form, table in UNKNOWN:
                head, tail = (c_head, c_tail) if provider == 'claude_code' else (x_head, x_tail)
                found, error = by_calls(record_of(head + [('engine', line) for line in lines] + tail), provider)
                at = len(head) + 1
                check('decision/unknown-forms', '%s, %s: decided ask, naming that line as an unknown call of form %s '
                      '[%s, %s]' % (provider, what, form, (found or {}).get('decision'), forms(found) or error),
                      (found or {}).get('decision') == 'ask' and forms(found) == [(at, 'unknown_call', form)]
                      and named(found) == [(at, None, None, None, None, 'unknown_call')]
                      and (found or {}).get('mcp_calls') == 0)

        # A redacted line whose tool name is neither mcp__ nor one the binary lists as built in may be a redacted
        # MCP tool's name: redacted_unreadable. A built-in name, or an MCP name that still reads, is decided as is.
        with region('decision/redacted-name'):
            renamed = {r.get('name') for r in CFORMS.get('builtin_renamed') or ()}
            for name, expected in (('[REDACTED:known_pattern]', [(3, None, None, None, None, 'redacted_unreadable')]),
                                   ('NotebookRead', [(3, None, None, None, None, 'redacted_unreadable')]),
                                   ('Agent', []), ('Read', []), ('mcp__tracker__get_issue', [])):
                record = record_of(c_head + [('engine', c_blocks([tool_use('toolu_x', name)]))] + c_tail)
                record[len(c_head)]['redacted'] = ['known_pattern']
                found, error = by_calls(record, 'claude_code')
                check('decision/redacted-name', 'a redacted line whose tool_use is named %r: decided %s [%s, %s]'
                      % (name, 'ask' if expected else 're-run', (found or {}).get('decision'), named(found) or error),
                      (found or {}).get('decision') == ('ask' if expected else 'rerun') and named(found) == expected
                      and (name in (CFORMS.get('builtin_tools') or ())) == (name == 'Read')
                      and (name in renamed) == (name == 'Agent'))

        # Negative control: every tool-free or built-in form, and a result, progress and summary of a call the
        # record showed, is no MCP call, so the fail-closed reading does not ask for everything.
        with region('decision/tool-free-forms'):
            claude_free = [
                c_blocks([{'type': 'text', 'text': 'working'}, {'type': 'thinking', 'thinking': 'x', 'signature': 's'},
                          {'type': 'redacted_thinking', 'data': 'd'}, tool_use('toolu_bash', 'Bash')]),
                c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_bash', 'content': 'ok'},
                        {'type': 'text', 'text': 'go on'}]),
                c_user('a plain prompt'),
                c_line('tool_progress', tool_use_id='toolu_bash', tool_name='Bash', parent_tool_use_id=None,
                       elapsed_time_seconds=1),
                c_line('tool_use_summary', summary='ran a command', preceding_tool_use_ids=['toolu_bash']),
                c_stream({'type': 'message_start', 'message': {'id': 'ms-2', 'role': 'assistant', 'content': []}}),
                c_stream({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
                c_stream({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'x'}}),
                c_stream({'type': 'content_block_stop', 'index': 0}),
                c_line('system', subtype='hook_started', hook_id='h', hook_name='n', hook_event='e'),
                c_line('auth_status', isAuthenticating=False, output=[]),
                # The frames outside the message union whose schema provably carries no tool call.
                {'type': 'keep_alive'}, {'type': 'control_cancel_request', 'request_id': 'req-3'},
                c_line('active_goal', value=None), c_line('system', subtype='task_summary', detail=None),
                c_line('system', subtype='post_turn_summary', summarizes_uuid='u', status_category='c',
                       status_detail='d', needs_action='n'),
                c_line('autocompact_state', value={'enabled': True, 'effective_window': 1, 'threshold': 1,
                                                   'enforced': False, 'source': 'auto'}),
                # Built-in names a frame carries: the REPL tool's inner Read, a heartbeat of the Bash call, a task
                # whose last tool and workflow agent ran built-in tools.
                c_blocks([tool_use('toolu_repl', 'REPL')]),
                c_line('tool_progress', tool_use_id='toolu_repl', tool_name='REPL', parent_tool_use_id=None,
                       elapsed_time_seconds=0, repl_call={'inner_tool_name': 'Read', 'inner_tool_input': {},
                                                          'inner_tool_use_id': 'toolu_inner', 'phase': 'start'}),
                c_line('tool_progress', tool_use_id='toolu_bash', tool_name='Bash', parent_tool_use_id=None,
                       elapsed_time_seconds=31, heartbeat=True),
                # A sub-agent whose one call is shown under its task: its count matches the calls shown.
                c_blocks([tool_use('toolu_agent1', 'Agent')]),
                c_line('system', subtype='task_started', task_id='task-1', tool_use_id='toolu_agent1', description='d',
                       task_type='local_agent'),
                dict(c_blocks([tool_use('toolu_child1', 'Bash')]), parent_tool_use_id='toolu_agent1'),
                c_line('system', subtype='task_progress', task_id='task-1', tool_use_id='toolu_agent1', description='d',
                       usage={'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}, last_tool_name='Bash',
                       workflow_progress=[{'type': 'workflow_agent', 'index': 0, 'lastToolName': 'Read'}]),
                c_line('system', subtype='task_notification', task_id='task-1', tool_use_id='toolu_agent1',
                       status='completed', output_file='', summary='done',
                       usage={'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}),
                c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_agent1', 'content': 'done'}])]
            codex_free = [x_any(kind, 'item_%s' % kind) for kind in
                          ('agent_message', 'reasoning', 'todo_list', 'error', 'command_execution', 'file_change',
                           'web_search')]
            for provider, lines, head, tail in (('claude_code', claude_free, c_head, c_tail),
                                                ('codex', codex_free, x_head, x_tail)):
                found, error = by_calls(record_of(head + [('engine', line) for line in lines] + tail), provider)
                check('decision/tool-free-forms', '%s: %d lines of tool-free and built-in forms decide re-run, naming no '
                      'call [%s, %s]' % (provider, len(lines), (found or {}).get('decision'), forms(found) or error),
                      (found or {}).get('decision') == 'rerun' and (found or {}).get('calls') == [])

        def c_progress(ident, name, **fields):
            return c_line('tool_progress', tool_use_id=ident, tool_name=name, parent_tool_use_id=None,
                          elapsed_time_seconds=0, **fields)

        def c_repl(inner):
            return c_progress('toolu_repl', 'REPL', repl_call=inner)

        def c_task(**fields):
            return c_line('system', subtype='task_progress', task_id='task-160', tool_use_id='toolu_agent',
                          description='review', usage={'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}, **fields)

        def inner(name, **fields):
            return dict({'inner_tool_name': name, 'inner_tool_input': {'issue': 'CEO-1'}, 'inner_tool_use_id': 'toolu_i1',
                         'phase': 'start'}, **fields)

        def judged(what, row, lines, decision, expected, reads, head=None):
            """A Claude Code record of `lines` after its init (and `head`), decided: `expected` is the calls it names
            as (sequence, reason, server, tool, form) and `reads` the MCP calls it counts."""
            before = c_head + [('engine', line) for line in head or ()]
            found, error = by_calls(record_of(before + [('engine', line) for line in lines] + c_tail), 'claude_code')
            got = sorted((c['sequence'], c['reason'], c['server'], c['tool'], c.get('form'))
                         for c in (found or {}).get('calls') or [])
            check(row, '%s: decided %s [%s, %s, %s MCP calls]' % (what, decision, (found or {}).get('decision'),
                                                               got or error, (found or {}).get('mcp_calls')),
                  (found or {}).get('decision') == decision and got == sorted(expected)
                  and (found or {}).get('mcp_calls') == reads)

        # BLOCKING: the REPL tool's inner calls reach the stream only as a tool_progress of the REPL call carrying a
        # repl_call (the binary's emitters; its schema omits the field), never as tool_use blocks.
        repl_head = [c_blocks([tool_use('toolu_repl', 'REPL')])]
        repl_tail = [c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_repl', 'content': 'ok'}])]
        with region('decision/repl-inner-call'):
            at = len(c_head) + 2
            judged('an MCP write made inside the REPL tool (the checker\'s reproduction)', 'decision/repl-inner-call',
                   [c_repl(inner('mcp__tracker__add_comment'))] + repl_tail, 'ask',
                   [(at, 'not_marked_read_only', 'tracker', 'add_comment', None)], 1, repl_head)
            judged('an MCP write inside the REPL tool, in its end phase only', 'decision/repl-inner-call',
                   [c_repl(inner('mcp__wiki__write_page', phase='end'))] + repl_tail, 'ask',
                   [(at, 'not_marked_read_only', 'wiki', 'write_page', None)], 1, repl_head)
            judged('a REPL inner tool neither mcp__ nor built in', 'decision/repl-inner-call',
                   [c_repl(inner('RemoteTrigger'))] + repl_tail, 'ask',
                   [(at, 'unknown_call', None, None, 'repl_call:RemoteTrigger')], 0, repl_head)
            for what, value in (('a repl_call that is not an object', 'mcp__tracker__add_comment'),
                                ('a repl_call without its inner tool name', {'inner_tool_use_id': 'toolu_i1'}),
                                ('a repl_call whose inner tool name is not a string', inner(['mcp__tracker__add_comment']))):
                judged(what, 'decision/repl-inner-call', [c_repl(value)] + repl_tail, 'ask',
                       [(at, 'unreadable', None, None, None)], 0, repl_head)
            judged('a read-only MCP call inside the REPL tool (negative control)', 'decision/repl-inner-call',
                   [c_repl(inner('mcp__tracker__get_issue'))] + repl_tail, 'rerun', [], 1, repl_head)
            judged('a built-in tool inside the REPL tool (negative control)', 'decision/repl-inner-call',
                   [c_repl(inner('Read'))] + repl_tail, 'rerun', [], 0, repl_head)

        # A task's progress names the last tool it ran, and each workflow agent's (entries its schema omits).
        agent_head = [c_blocks([tool_use('toolu_agent', 'Agent')]),
                      c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_agent', 'content': 'started'}]),
                      c_line('system', subtype='task_started', task_id='task-160', tool_use_id='toolu_agent',
                             description='review', task_type='local_agent')]
        def c_child(parent, blocks):
            """A sub-agent's assistant message as the binary forwards it: its task's id as parent_tool_use_id."""
            return dict(c_blocks(blocks), parent_tool_use_id=parent)

        with region('decision/task-progress-tool'):
            at = len(c_head) + len(agent_head) + 1
            # The task's progress counts one call and the record shows none under it: also an unknown call.
            unshown = (at, 'unknown_call', None, None, 'task_tool_uses')
            judged('a background task whose last tool is an MCP write (the checker\'s reproduction)',
                   'decision/task-progress-tool', [c_task(last_tool_name='mcp__tracker__add_comment')], 'ask',
                   [(at, 'not_marked_read_only', 'tracker', 'add_comment', None), unshown], 1, agent_head)
            judged('the same last tool on two progress lines is one call', 'decision/task-progress-tool',
                   [c_task(last_tool_name='mcp__wiki__write_page')] * 2, 'ask',
                   [(at, 'not_marked_read_only', 'wiki', 'write_page', None), unshown], 1, agent_head)
            judged('a workflow agent whose last tool is an MCP write', 'decision/task-progress-tool',
                   [c_task(last_tool_name='review agent',
                           workflow_progress=[{'type': 'workflow_phase', 'index': 0},
                                              {'type': 'workflow_agent', 'index': 1,
                                               'lastToolName': 'mcp__tracker__add_comment'}])], 'ask',
                   [(at, 'not_marked_read_only', 'tracker', 'add_comment', None), unshown], 1, agent_head)
            for what, fields in (('a last tool name that is not a string', {'last_tool_name': 7}),
                                 ('workflow progress that is not a list', {'workflow_progress': 'agent 1'}),
                                 ('a workflow progress entry that is not an object', {'workflow_progress': ['agent 1']})):
                judged(what, 'decision/task-progress-tool', [c_task(**fields)], 'ask',
                       [(at, 'unreadable', None, None, None), unshown], 0, agent_head)
            # Negative controls: the task's one call is shown under it, so its count names nothing more.
            judged('a task whose last tool is a read-only MCP call (negative control)', 'decision/task-progress-tool',
                   [c_task(last_tool_name='mcp__tracker__search')], 'rerun', [], 2,
                   agent_head + [c_child('toolu_agent', [tool_use('toolu_c1', 'mcp__tracker__search')])])
            judged('a task whose last tool is built in (negative control)', 'decision/task-progress-tool',
                   [c_task(last_tool_name='Bash')], 'rerun', [], 0,
                   agent_head + [c_child('toolu_agent', [tool_use('toolu_c1', 'Bash')])])

        # BLOCKING (the lead's decision, fail closed): an agent a sub-agent starts has its messages dropped (the
        # binary forwards them only with forwardSubagentText), so its calls show no block and its task's progress
        # names only the last tool of each message. Its task's count of its own calls (usage.tool_uses) still
        # reaches the stream, and every call it counts that the record does not show under it asks.
        def t_started(task, depth):
            return c_line('system', subtype='task_started', task_id='task-' + task, tool_use_id=task,
                          description='d', task_type='local_agent', spawn_depth=depth)

        def t_progress(task, last, count, **fields):
            return c_line('system', subtype='task_progress', task_id='task-' + task, tool_use_id=task, description='d',
                          usage=dict({'total_tokens': 1, 'tool_uses': count, 'duration_ms': 1}, **fields.pop('usage', {}))
                          if count is not None else fields.pop('usage'), last_tool_name=last, **fields)

        def t_done(task, usage):
            return c_line('system', subtype='task_notification', task_id='task-' + task, tool_use_id=task,
                          status='completed', output_file='', summary='done', **({} if usage is None else {'usage': usage}))

        def t_result(task, parent=None):
            return dict(c_user([{'type': 'tool_result', 'tool_use_id': task, 'content': 'done'}]), parent_tool_use_id=parent)

        def counted(found):
            return sorted((c.get('task'), c.get('unshown')) for c in (found or {}).get('calls') or []
                          if c.get('form') == 'task_tool_uses')

        def subagent(what, lines, decision, expected, reads, tasks, as_text=False):
            """judged, and the tasks each shortfall names with its size ([(task, unshown)])."""
            judged(what, 'decision/subagent-calls', lines, decision, expected, reads)
            record = record_of(c_head + [('engine', json.dumps(line) if as_text else line) for line in lines] + c_tail)
            found, error = by_calls(record, 'claude_code')
            check('decision/subagent-calls', '%s%s: the shortfalls name %s [%s]'
                  % (what, ' (as JSON text)' if as_text else '', tasks, counted(found) or error),
                  counted(found) == tasks and (found or {}).get('decision') == decision)

        u_write, u_read = tool_use('toolu_w2', 'mcp__tracker__add_comment'), tool_use('toolu_r2', 'Read')
        with region('decision/subagent-calls'):
            # The checker's reproduction: the depth-2 agent's reply [an MCP write, Read] shows only its last tool.
            nested = [c_blocks([tool_use('t1', 'Agent')]), t_started('t1', 1),
                      c_child('t1', [tool_use('t2', 'Agent')]), t_progress('t1', 'Agent', 1), t_started('t2', 2),
                      t_progress('t2', 'Read', 2), t_done('t2', {'total_tokens': 1, 'tool_uses': 2, 'duration_ms': 1}),
                      t_result('t2', 't1'), t_done('t1', {'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}),
                      t_result('t1')]
            at = len(c_head) + 6
            for as_text in (False, True):
                subagent('a depth-2 agent\'s hidden MCP write (the checker\'s reproduction)', nested, 'ask',
                         [(at, 'unknown_call', None, None, 'task_tool_uses')], 0, [('t2', 2)], as_text)
            # A depth-1 agent whose calls are all shown and read-only still re-runs.
            shown = [c_blocks([tool_use('t1', 'Agent')]), t_started('t1', 1),
                     c_child('t1', [tool_use('c1', 'Read')]), t_progress('t1', 'Read', 1),
                     c_child('t1', [tool_use('c2', 'mcp__tracker__search')]), t_progress('t1', 'mcp__tracker__search', 2)]
            subagent('a depth-1 agent whose calls are all shown and read-only (negative control)',
                     shown + [t_done('t1', {'total_tokens': 1, 'tool_uses': 2, 'duration_ms': 1}), t_result('t1')],
                     'rerun', [], 2, [])
            subagent('a task end that reports no usage (negative control)', shown + [t_done('t1', None), t_result('t1')],
                     'rerun', [], 2, [])
            # A count that exceeds the calls shown by one asks, naming the task and the one call.
            subagent('a task whose end counts one call more than the record shows', shown
                     + [t_done('t1', {'total_tokens': 1, 'tool_uses': 3, 'duration_ms': 1}), t_result('t1')],
                     'ask', [(len(c_head) + 7, 'unknown_call', None, None, 'task_tool_uses')], 2, [('t1', 1)])
            subagent('a task whose progress counts one call more than the record shows', shown[:-1]
                     + [t_progress('t1', 'mcp__tracker__search', 3), t_result('t1')],
                     'ask', [(len(c_head) + 6, 'unknown_call', None, None, 'task_tool_uses')], 2, [('t1', 1)])
            # A count that cannot be read, or one lower than the task reported before, is unreadable.
            end = len(c_head) + 7
            for what, frame in (
                    ('a task_progress whose usage has no count of calls', t_progress('t1', 'Read', None,
                                                                                usage={'total_tokens': 1})),
                    ('a task_progress whose count is not a whole number', t_progress('t1', 'Read', '2')),
                    ('a task_progress whose count is negative', t_progress('t1', 'Read', -1)),
                    ('a task_progress whose usage is not an object', t_progress('t1', 'Read', None, usage='2 calls')),
                    ('a task_progress without its task\'s id', dict(t_progress('t1', 'Read', 2), tool_use_id=None)),
                    ('a task end whose usage has no count of calls', t_done('t1', {'total_tokens': 1})),
                    ('a task end whose count is lower than its progress reported', t_done('t1', {'total_tokens': 1,
                                                                                         'tool_uses': 1}))):
                subagent(what, shown + [frame, t_result('t1')], 'ask', [(end, 'unreadable', None, None, None)], 2, [])
            subagent('a depth-2 agent whose reply was one hidden MCP write, named as its last tool', [
                c_blocks([tool_use('t1', 'Agent')]), c_child('t1', [tool_use('t2', 'Agent')]), t_started('t2', 2),
                t_progress('t2', 'mcp__tracker__add_comment', 1), t_result('t2', 't1'), t_result('t1')], 'ask',
                [(len(c_head) + 4, 'not_marked_read_only', 'tracker', 'add_comment', None),
                 (len(c_head) + 4, 'unknown_call', None, None, 'task_tool_uses')], 1, [('t2', 1)])

        # The other frames that carry a tool's name: a tool_progress's own tool, and an assistant message's MCP
        # attribution and batch tool names.
        with region('decision/frame-tool-names'):
            at = len(c_head) + 2
            judged('a tool_progress of a shown call naming an MCP write', 'decision/frame-tool-names',
                   [c_progress('toolu_repl', 'mcp__tracker__add_comment', heartbeat=True)], 'ask',
                   [(at, 'not_marked_read_only', 'tracker', 'add_comment', None)], 1, repl_head)
            judged('an MCP write and its heartbeat are one call', 'decision/frame-tool-names',
                   [c_progress('toolu_w', 'mcp__tracker__add_comment', heartbeat=True)], 'ask',
                   [(at - 1, 'not_marked_read_only', 'tracker', 'add_comment', None)], 1,
                   [c_blocks([tool_use('toolu_w', 'mcp__tracker__add_comment')])])
            judged('an assistant message an MCP tool produced', 'decision/frame-tool-names',
                   [dict(c_blocks([{'type': 'text', 'text': 'x'}]), attribution_mcp_server='tracker',
                         attribution_mcp_tool='add_comment')], 'ask',
                   [(at - 1, 'not_marked_read_only', 'tracker', 'add_comment', None)], 1)
            judged('an assistant message decomposed from a batch holding an MCP write', 'decision/frame-tool-names',
                   [dict(c_blocks([tool_use('toolu_s', 'Bash')]),
                         batch_tool_uses=[{'id': 'toolu_b', 'name': 'mcp__wiki__write_page'}])], 'ask',
                   [(at - 1, 'not_marked_read_only', 'wiki', 'write_page', None)], 1)
            judged('an MCP attribution that is not a name', 'decision/frame-tool-names',
                   [dict(c_blocks([{'type': 'text', 'text': 'x'}]), attribution_mcp_server=['tracker'])], 'ask',
                   [(at - 1, 'unreadable', None, None, None)], 0)
            judged('a heartbeat of a shown built-in call (negative control)', 'decision/frame-tool-names',
                   [c_progress('toolu_repl', 'REPL', heartbeat=True)], 'rerun', [], 0, repl_head)

        # THE STRUCTURAL RULES (the lead's decision): the stream cannot be made to show every nested call, so the
        # configuration decides first. The checker's reproduction: a sub-agent runs a skill that forks (context: fork);
        # the fork's messages (skill_progress) are dropped at depth 2 and its end notification carries no count, so the
        # record shows no call and no shortfall.
        forked = [c_blocks([tool_use('t1', 'Agent')]), t_started('t1', 1), c_child('t1', [tool_use('s1', 'Skill')]),
                  t_progress('t1', 'Skill', 1), dict(t_started('s1', 2), description='/deploy', skip_transcript=True),
                  dict(t_done('s1', None), skip_transcript=True, ambient=True), t_result('s1', 't1'),
                  t_done('t1', {'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}), t_result('t1')]
        at = len(c_head) + 1
        FORKED_NESTED = [(at, 'agent', 'tool:Agent'), (at + 1, 'task_frames', 'system/task_started'),
                         (at + 2, 'nested_progress', 'parent_tool_use_id'), (at + 2, 'skill', 'tool:Skill'),
                         (at + 3, 'skill', 'tool:Skill'), (at + 3, 'task_frames', 'system/task_progress'),
                         (at + 4, 'task_frames', 'system/task_started'),
                         (at + 5, 'task_frames', 'system/task_notification'),
                         (at + 6, 'nested_progress', 'parent_tool_use_id'),
                         (at + 7, 'task_frames', 'system/task_notification')]
        READ_ONLY = [{'name': 'tracker', 'catalog_id': 'mcp_server:tracker', 'revision': 3, 'tools': ['get_issue', 'search']},
                     {'name': 'wiki', 'catalog_id': 'mcp_server:wiki', 'revision': 1, 'tools': []}]

        def hidden(found):
            return sorted((c['sequence'], c.get('construct'), c.get('form')) for c in (found or {}).get('calls') or []
                          if c.get('reason') == 'nested_work')

        def c_rec(lines, as_text=False):
            return record_of(c_head + [('engine', json.dumps(line) if as_text else line) for line in lines] + c_tail)

        def x_rec(lines):
            return record_of(x_head + [('engine', line) for line in lines] + x_tail)

        x_collab = [x_any('collab_tool_call', 'item_cc', tool='spawn_agent', status='in_progress')]
        with region('decision/no-write-server-reruns'):
            # 1. No MCP server with a tool not marked read-only: the run could not have written through MCP.
            for what, record, provider, servers in (
                    ('the checker\'s forked skill, only read-only tools configured', c_rec(forked), 'claude_code',
                     READ_ONLY),
                    ('the checker\'s forked skill as JSON text, only read-only tools configured', c_rec(forked, True),
                     'claude_code', READ_ONLY),
                    ('a depth-2 agent\'s hidden MCP write, no MCP server configured', c_rec(nested), 'claude_code', []),
                    ('exec\'s own sub-agent call, no MCP server configured', x_rec(x_collab), 'codex', [])):
                found, error = decide(record, provider, servers)
                check('decision/no-write-server-reruns', '%s: decided re-run whatever the stream shows [%s, %s, %s]'
                      % (what, (found or {}).get('decision'), (found or {}).get('basis'), named(found) or error),
                      (found or {}).get('decision') == 'rerun' and (found or {}).get('calls') == []
                      and (found or {}).get('basis') == 'no_write_capable_server'
                      and (found or {}).get('mcp_calls') is None)
            gap = c_rec(nested)
            gap[3]['sequence'] = 9
            found, error = decide(gap, 'claude_code', [])
            check('decision/no-write-server-reruns', 'a record with a gap in its sequence is still refused by name [%s]'
                  % error, found is None and error == 'invalid_input:record_sequence')
            found, error = decide(c_rec(forked), 'claude_code', [dict(READ_ONLY[0], tools='read')])
            check('decision/no-write-server-reruns', 'a server whose tools are neither all nor a list is refused by '
                  'name [%s]' % error, found is None and error == 'invalid_input:configuration')
            # Negative controls: a configuration giving a tool not marked read-only (listed, or all tools) is
            # write-capable, and the same record asks.
            for what, servers in (('a listed tool not marked read-only', [dict(READ_ONLY[0], tools=['get_issue', 'add_comment'])]),
                                  ('all its tools', [dict(READ_ONLY[0], tools='all')]),
                                  ('its tools unlisted (all of them)', [{k: v for k, v in READ_ONLY[0].items() if k != 'tools'}]),
                                  ('a revision that marks nothing', [dict(READ_ONLY[1], tools=['read_page'])])):
                found, error = decide(c_rec(forked), 'claude_code', servers)
                check('decision/no-write-server-reruns', 'the forked skill with a server giving %s: write-capable, '
                      'decided ask [%s, %s, %s]' % (what, (found or {}).get('decision'), (found or {}).get('basis'), error),
                      (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'nested_work'
                      and LIMIT is not None and LIMIT.write_capable(servers, MARKS) == [servers[0]['name']])

        with region('decision/nested-work-asks'):
            # 2. A write-capable server and any construct that can run hidden nested work: ask, naming each line.
            for as_text in (False, True):
                found, error = decide(c_rec(forked, as_text), 'claude_code')
                check('decision/nested-work-asks', 'the checker\'s forked skill%s, a write-capable server configured: '
                      'decided ask, naming each construct line [%s, %s, %s]'
                      % (' (as JSON text)' if as_text else '', (found or {}).get('decision'), (found or {}).get('basis'),
                         hidden(found) or error),
                      (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'nested_work'
                      and hidden(found) == FORKED_NESTED and named(found) == sorted(
                          (n, None, None, None, None, 'nested_work') for n, _, _ in FORKED_NESTED))
            found, error = by_calls(c_rec(forked), 'claude_code')
            check('decision/nested-work-asks', 'the call-by-call rules alone see no call in it [%s, %s]'
                  % ((found or {}).get('decision'), named(found) or error),
                  (found or {}).get('decision') == 'rerun' and named(found) == [])
            normal = shown + [t_done('t1', {'total_tokens': 1, 'tool_uses': 2, 'duration_ms': 1}), t_result('t1')]
            found, error = decide(c_rec(normal), 'claude_code')
            check('decision/nested-work-asks', 'a normal run whose Agent\'s calls are all shown and read-only, a '
                  'write-capable server configured: decided ask, naming the Agent line [%s, %s]'
                  % ((found or {}).get('decision'), hidden(found)[:2] or error),
                  (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'nested_work'
                  and hidden(found)[:1] == [(len(c_head) + 1, 'agent', 'tool:Agent')]
                  and by_calls(c_rec(normal), 'claude_code')[0].get('decision') == 'rerun')
            found, error = decide(c_rec(nested), 'claude_code')
            check('decision/nested-work-asks', 'a depth-2 agent\'s hidden MCP write: decided ask, naming the constructs '
                  'beside the calls the call-by-call rules name [%s]' % (forms(found) or error),
                  (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'nested_work'
                  and (len(c_head) + 6, 'unknown_call', 'task_tool_uses') in forms(found)
                  and (len(c_head) + 1, 'agent', 'tool:Agent') in hidden(found))
            found, error = decide(x_rec(x_collab), 'codex')
            check('decision/nested-work-asks', 'codex, exec\'s own sub-agent call: decided ask, naming it as nested work '
                  'and as an unknown call [%s]' % (forms(found) or error),
                  (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'nested_work'
                  and forms(found) == [(len(x_head) + 1, 'nested_work', 'item:collab_tool_call'),
                                       (len(x_head) + 1, 'unknown_call', 'collab_tool_call')])

        # Each construct class the binaries' tables list, alone in a record, asks naming exactly that construct.
        CONSTRUCTS = (
            ('claude_code', 'agent', 'an Agent tool call', [c_blocks([tool_use('toolu_a', 'Agent')])], ['tool:Agent']),
            ('claude_code', 'agent', 'a Task tool call (its old name)', [c_blocks([tool_use('toolu_a', 'Task')])],
             ['tool:Task']),
            ('claude_code', 'agent', 'a SendMessage to a teammate', [c_blocks([tool_use('toolu_a', 'SendMessage')])],
             ['tool:SendMessage']),
            ('claude_code', 'skill', 'a Skill tool call', [c_blocks([tool_use('toolu_k', 'Skill')])], ['tool:Skill']),
            ('claude_code', 'repl', 'a REPL tool call', [c_blocks([tool_use('toolu_r', 'REPL')])], ['tool:REPL']),
            ('claude_code', 'repl', 'a REPL inner call on a heartbeat of another tool',
             [c_blocks([tool_use('toolu_b', 'Bash')]), c_progress('toolu_b', 'Bash', repl_call=inner('Read'))],
             ['tool_progress:repl_call']),
            ('claude_code', 'workflow', 'a Workflow tool call', [c_blocks([tool_use('toolu_f', 'Workflow')])],
             ['tool:Workflow']),
            ('claude_code', 'workflow', 'a RunWorkflow tool call (its alias)', [c_blocks([tool_use('toolu_f', 'RunWorkflow')])],
             ['tool:RunWorkflow']),
            ('claude_code', 'cron', 'a CronCreate that is not durable (a prompt scheduled in the session)',
             [c_blocks([dict(tool_use('toolu_n', 'CronCreate'), input={'cron': '*/5 * * * *', 'prompt': 'p'})])],
             ['tool:CronCreate']),
            ('claude_code', 'task_frames', 'a background shell task started',
             [c_line('system', subtype='task_started', task_id='b1', tool_use_id=None, description='d',
                     task_type='local_bash')], ['system/task_started']),
            ('claude_code', 'task_frames', 'a task moved to the background',
             [c_line('system', subtype='task_updated', task_id='b1', patch={'is_backgrounded': True})],
             ['system/task_updated']),
            ('claude_code', 'nested_progress', 'a message a sub-agent produced',
             [dict(c_blocks([{'type': 'text', 'text': 'x'}]), parent_tool_use_id='toolu_elsewhere')],
             ['parent_tool_use_id']),
            ('claude_code', 'nested_progress', 'a forked skill\'s progress frame',
             [{'type': 'progress', 'toolUseID': 'skill_m1', 'data': {'type': 'skill_progress', 'agentId': 'a1',
                                                                     'message': {'type': 'assistant'}}}],
             ['progress:skill_progress']),
            ('claude_code', 'fork', 'a forked skill\'s result',
             [dict(c_user('forked'), tool_use_result={'success': True, 'commandName': 'deploy', 'status': 'forked',
                                                      'agentId': 'a1', 'result': 'launched'})],
             ['tool_use_result:forked']),
            ('codex', 'collab', 'exec\'s own sub-agent call', x_collab, ['item:collab_tool_call']),
            ('codex', 'collab', 'the core\'s collab agent call',
             [x_any('collab_agent_tool_call', 'item_c', tool='spawn_agent', status='in_progress')],
             ['item:collab_agent_tool_call']),
            ('codex', 'sub_agent', 'the core\'s sub-agent activity', [x_any('sub_agent_activity', 'item_a')],
             ['item:sub_agent_activity']),
        )
        with region('decision/nested-constructs'):
            for provider, construct, what, lines, expected in CONSTRUCTS:
                record = c_rec(lines) if provider == 'claude_code' else x_rec(lines)
                found, error = decide(record, provider)
                head = c_head if provider == 'claude_code' else x_head
                want = [(len(head) + len(lines), construct, form) for form in expected]
                check('decision/nested-constructs', '%s, %s (%s): decided ask, naming exactly that construct [%s]'
                      % (provider, what, construct, hidden(found) or error),
                      (found or {}).get('decision') == 'ask' and hidden(found) == want)
            workflow = c_line('system', subtype='task_started', task_id='w1', tool_use_id=None, description='spec',
                              task_type='local_workflow', workflow_name='spec')
            found, error = decide(c_rec([workflow]), 'claude_code')
            check('decision/nested-constructs', 'a workflow\'s task started: a task frame and a workflow\'s [%s]'
                  % (hidden(found) or error), hidden(found) == [
                      (len(c_head) + 1, 'task_frames', 'system/task_started'),
                      (len(c_head) + 1, 'workflow', 'system/task_started:workflow_name')])
            # A RemoteTrigger call asks first by the rule for an agent started outside the run
            # (decision/remote-agent-asks); rule 2's table names it too.
            remote = c_rec([c_blocks([dict(tool_use('toolu_t', 'RemoteTrigger'), input={'action': 'list'})])])
            listed = attempt(lambda: LIMIT.nested(remote, 'claude_code'))[0] if LIMIT is not None else None
            found, error = decide(remote, 'claude_code')
            check('decision/nested-constructs', 'claude_code, a RemoteTrigger call (remote): rule 2 names exactly that '
                  'construct, and the decision asks [%s, %s]' % (listed, (found or {}).get('basis') or error),
                  listed == [{'sequence': len(c_head) + 1, 'construct': 'remote', 'form': 'tool:RemoteTrigger'}]
                  and (found or {}).get('decision') == 'ask')
            classes = {construct for _, construct, _, _, _ in CONSTRUCTS} | {'remote'}
            declared = (set(CFORMS.get('nested_work', {}).get('tools') or ())
                        | {key for key in CFORMS.get('nested_work') or {} if key in ('task_frames', 'fork')}
                        | {'nested_progress'} | {key for key in XFORMS.get('nested_work') or {} if key != 'source'})
            check('decision/nested-constructs', 'every construct class the binaries\' tables list is driven [%s]'
                  % sorted(classes ^ declared), classes == declared and len(classes) == 11)
            # Negative control: the same kinds of lines without the construct name no nested work.
            found, error = decide(c_rec([c_blocks([tool_use('toolu_b', 'Bash')]),
                                         c_line('system', subtype='permission_denied', tool_name='Agent',
                                                tool_use_id='toolu_d'),
                                         c_user([{'type': 'tool_result', 'tool_use_id': 'toolu_b', 'content': 'ok'}])]),
                                  'claude_code')
            check('decision/nested-constructs', 'a Bash call, a denied Agent call and its result name no nested work '
                  '[%s, %s]' % ((found or {}).get('decision'), hidden(found) or error),
                  (found or {}).get('decision') == 'rerun' and hidden(found) == [] and (found or {}).get('basis') == 'calls')

        # The lead's decision: a visible call the configuration does not give the run contradicts the configuration
        # and asks, naming the line, before every other rule (even with only read-only servers configured).
        with region('decision/unconfigured-call-asks'):
            selected = [dict(READ_ONLY[0], tools=['get_issue']), READ_ONLY[1]]
            for provider in ('claude_code', 'codex'):
                if provider == 'claude_code':
                    def u_rec(server, tool):
                        return c_rec([c_blocks([tool_use('toolu_u', 'mcp__%s__%s' % (server, tool))])])
                    u_at = len(c_head) + 1
                else:
                    def u_rec(server, tool):
                        return x_rec([x_item('item.started', 'item_u', server, tool, 'in_progress')])
                    u_at = len(x_head) + 1
                for what, record, servers, expected in (
                        ('a call to a server the configuration does not list, only read-only servers configured',
                         u_rec('mailer', 'send'), READ_ONLY, [(u_at, 'mailer', 'send', None, None, 'unconfigured_call')]),
                        ('a call to a tool marked read-only that the configuration does not give the run',
                         u_rec('tracker', 'search'), selected,
                         [(u_at, 'tracker', 'search', 'mcp_server:tracker', 3, 'unconfigured_call')])):
                    found, error = decide(record, provider, servers)
                    check('decision/unconfigured-call-asks', '%s, %s: decided ask, naming that line [%s, %s, %s]'
                          % (provider, what, (found or {}).get('decision'), (found or {}).get('basis'),
                             named(found) or error),
                          (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'unconfigured_call'
                          and named(found) == expected and (found or {}).get('mcp_calls') == 1
                          and LIMIT is not None and LIMIT.write_capable(servers, MARKS) == [])
                # Negative control: the same record calling a listed read-only tool the run is given re-runs.
                for what, record, servers in (('a listed read-only tool', u_rec('tracker', 'get_issue'), READ_ONLY),
                                              ('the one tool the configuration gives', u_rec('tracker', 'get_issue'),
                                               selected)):
                    found, error = decide(record, provider, servers)
                    check('decision/unconfigured-call-asks', '%s, a call to %s, only read-only servers configured: '
                          'decided re-run [%s, %s, %s]' % (provider, what, (found or {}).get('decision'),
                                                           (found or {}).get('basis'), named(found) or error),
                          (found or {}).get('decision') == 'rerun' and (found or {}).get('calls') == []
                          and (found or {}).get('basis') == 'no_write_capable_server')

        # The lead's decision: a call that starts an agent outside the run (a RemoteTrigger call, whose create and run
        # start a cloud agent routine that keeps the account's claude.ai connectors, or a durable CronCreate, whose
        # prompt fires after the run) may act whatever the configuration, so it asks under every configuration.
        with region('decision/remote-agent-asks'):
            def r_use(ident, name, **given):
                return c_blocks([dict(tool_use(ident, name), input=given)])

            def r_done(ident):
                return c_user([{'type': 'tool_result', 'tool_use_id': ident, 'content': 'ok'}])

            def outside(found):
                return sorted((c['sequence'], c.get('construct'), c.get('form')) for c in (found or {}).get('calls') or []
                              if c.get('reason') == 'remote_agent')
            # The checker's reproduction: a routine created with the account's connectors, then run.
            routine = [r_use('toolu_q', 'ToolSearch', query='select:RemoteTrigger'), r_done('toolu_q'),
                       r_use('toolu_c', 'RemoteTrigger', action='create',
                             body={'prompt': 'comment on CEO-1', 'mcp_connections': ['Atlassian']}), r_done('toolu_c'),
                       r_use('toolu_r', 'RemoteTrigger', action='run', trigger_id='t'), r_done('toolu_r')]
            at = len(c_head) + 1
            CONFIGURATIONS = (('no MCP server', []), ('only read-only tools', READ_ONLY), ('a write-capable server', None))
            OUTSIDE = (
                ('a routine created with the account\'s connectors and run (the checker\'s reproduction)', routine,
                 [(at + 2, 'remote', 'tool:RemoteTrigger'), (at + 4, 'remote', 'tool:RemoteTrigger')]),
                ('a routine listed (any RemoteTrigger call)', [r_use('toolu_l', 'RemoteTrigger', action='list')],
                 [(at, 'remote', 'tool:RemoteTrigger')]),
                ('a durable CronCreate (the checker\'s reproduction)',
                 [r_use('toolu_k', 'CronCreate', cron='*/5 * * * *', prompt='post a comment', durable=True), r_done('toolu_k')],
                 [(at, 'cron', 'tool:CronCreate:durable')]),
                ('a CronCreate durable as the text "true"',
                 [r_use('toolu_k', 'CronCreate', cron='*/5 * * * *', prompt='p', durable='true')],
                 [(at, 'cron', 'tool:CronCreate:durable')]),
                ('a durable CronCreate as the REPL tool\'s inner call',
                 [r_use('toolu_repl', 'REPL', code='x'),
                  c_repl(inner('CronCreate', inner_tool_input={'cron': '0 9 * * *', 'prompt': 'p', 'durable': True}))],
                 [(at + 1, 'cron', 'tool:CronCreate:durable')]),
                ('a CronCreate named where its input is not given (a task\'s last tool)',
                 [c_task(last_tool_name='CronCreate')], [(at, 'cron', 'tool:CronCreate:durable')]))
            for what, lines, expected in OUTSIDE:
                for label, servers in CONFIGURATIONS:
                    found, error = decide(c_rec(lines), 'claude_code', servers)
                    check('decision/remote-agent-asks', '%s, %s configured: decided ask, naming each such line [%s, %s, %s]'
                          % (what, label, (found or {}).get('decision'), (found or {}).get('basis'), outside(found) or error),
                          (found or {}).get('decision') == 'ask' and (found or {}).get('basis') == 'remote_agent'
                          and outside(found) == expected
                          and all(c.get('reason') == 'remote_agent' for c in (found or {}).get('calls') or []))
            found, error = decide(c_rec(routine, True), 'claude_code', [])
            check('decision/remote-agent-asks', 'the checker\'s routine held as JSON text, no MCP server: decided ask, '
                  'naming each such line [%s]' % (outside(found) or error), (found or {}).get('basis') == 'remote_agent'
                  and outside(found) == [(at + 2, 'remote', 'tool:RemoteTrigger'), (at + 4, 'remote', 'tool:RemoteTrigger')])
            # Beside it, a call that contradicts the configuration is named too.
            both = c_rec([r_use('toolu_l', 'RemoteTrigger', action='list'),
                          c_blocks([tool_use('toolu_u', 'mcp__mailer__send')])])
            found, error = decide(both, 'claude_code', READ_ONLY)
            check('decision/remote-agent-asks', 'a RemoteTrigger call and a call to an unlisted server: decided ask, naming '
                  'both [%s]' % (forms(found) or error),
                  (found or {}).get('basis') == 'remote_agent'
                  and forms(found) == [(at, 'remote_agent', 'tool:RemoteTrigger'), (at + 1, 'unconfigured_call', None)])
            # Negative controls: a CronCreate that is not durable, and loading RemoteTrigger's schema, start nothing
            # outside the run: with only read-only tools they re-run, and with a write-capable server rule 2 decides.
            session = (('its durable field left out', {}), ('durable false', {'durable': False}),
                       ('durable as the text "false"', {'durable': 'false'}))
            for what, given in session:
                lines = [r_use('toolu_n', 'CronCreate', cron='*/5 * * * *', prompt='p', **given), r_done('toolu_n')]
                found, error = decide(c_rec(lines), 'claude_code', READ_ONLY)
                again, _ = decide(c_rec(lines), 'claude_code')
                check('decision/remote-agent-asks', 'a CronCreate with %s: re-run with only read-only tools, and asked '
                      'by rule 2 with a write-capable server [%s, %s]' % (what, (found or {}).get('basis') or error,
                                                                           hidden(again)),
                      (found or {}).get('decision') == 'rerun' and (found or {}).get('basis') == 'no_write_capable_server'
                      and (again or {}).get('basis') == 'nested_work' and hidden(again) == [(at, 'cron', 'tool:CronCreate')])
            found, error = decide(c_rec(routine[:2]), 'claude_code', READ_ONLY)
            check('decision/remote-agent-asks', 'RemoteTrigger\'s schema loaded and never called: re-run [%s, %s]'
                  % ((found or {}).get('basis'), error), (found or {}).get('decision') == 'rerun'
                  and (found or {}).get('basis') == 'no_write_capable_server')
            # The checker's normal runs keep their decisions.
            with_agent = [c_blocks([tool_use('t1', 'Agent')]), t_started('t1', 1),
                          c_child('t1', [tool_use('a1', 'mcp__tracker__get_issue')]),
                          dict(c_user([{'type': 'tool_result', 'tool_use_id': 'a1', 'content': 'ok'}]), parent_tool_use_id='t1'),
                          t_done('t1', {'total_tokens': 1, 'tool_uses': 1, 'duration_ms': 1}), t_result('t1')]
            reads = [r_use('toolu_a', 'Read', file_path='/work/README'), r_done('toolu_a'),
                     c_blocks([tool_use('toolu_m', 'mcp__tracker__get_issue')]), r_done('toolu_m'),
                     r_use('toolu_b', 'Bash', command='ls'), r_done('toolu_b')]
            for what, lines, servers, decision, basis in (
                    ('an Agent whose one call is read-only, only read-only tools', with_agent, READ_ONLY, 'rerun',
                     'no_write_capable_server'),
                    ('an Agent with no MCP server', with_agent[:1] + with_agent[-1:], [], 'rerun', 'no_write_capable_server'),
                    ('reads only, a write-capable server', reads, None, 'rerun', 'calls'),
                    ('an Agent, a write-capable server', with_agent, None, 'ask', 'nested_work')):
                found, error = decide(c_rec(lines), 'claude_code', servers)
                check('decision/remote-agent-asks', 'the checker\'s normal run, %s: decided %s by %s [%s, %s]'
                      % (what, decision, basis, (found or {}).get('decision'), (found or {}).get('basis') or error),
                      (found or {}).get('decision') == decision and (found or {}).get('basis') == basis
                      and outside(found) == [])

        # The readers' tables are the binaries' own; each listed fixture form is one they list, each unlisted one not.
        with region('format/tool-forms'):
            CE, XE = getattr(L, 'ENGINES', {}).get('claude_code'), getattr(L, 'ENGINES', {}).get('codex')
            claude_tables = {'messages': {tuple(m) for m in CFORMS.get('messages') or ()},
                             'response_blocks': list(CFORMS.get('response_blocks') or ()),
                             'request_blocks': list(CFORMS.get('request_blocks') or ()),
                             'stream_events': list(CFORMS.get('stream_events') or ()),
                             'builtin_tools': set(CFORMS.get('builtin_tools') or ())}
            module_tables = {'messages': set(getattr(CE, 'MESSAGES', ())),
                             'response_blocks': list(getattr(CE, 'RESPONSE_BLOCKS', ())),
                             'request_blocks': list(getattr(CE, 'REQUEST_BLOCKS', ())),
                             'stream_events': list(getattr(CE, 'STREAM_EVENTS', ())),
                             'builtin_tools': set(getattr(CE, 'BUILTIN_TOOLS', ()))}
            check('format/tool-forms', 'claude_code: the reader\'s message, block, streaming event and built-in tool '
                  'tables are the binary\'s own [%s]' % [k for k in claude_tables if claude_tables[k] != module_tables[k]],
                  claude_tables == module_tables and len(claude_tables['messages']) > 40
                  and set(getattr(CE, 'TOOL_FREE_REQUEST', ())) <= set(claude_tables['request_blocks'])
                  and set(getattr(CE, 'TOOL_FREE_BLOCKS', ())) <= set(claude_tables['response_blocks']))
            renamed = {r['name']: tuple(r['aliases']) for r in CFORMS.get('builtin_renamed') or ()}
            check('format/tool-forms', 'claude_code: the built-in names are BUILTIN_TOOL_NAMES and the current name of '
                  'each tool it lists under an old one (%s) [%s, %s]' % (renamed, getattr(CE, 'BUILTIN_RENAMED', None),
                                                                       sorted(set(getattr(CE, 'BUILTIN', ())) ^ (
                                                                           claude_tables['builtin_tools'] | set(renamed)))),
                  renamed == {'Agent': ('Task',)} and getattr(CE, 'BUILTIN_RENAMED', None) == renamed
                  and set(getattr(CE, 'BUILTIN', ())) == claude_tables['builtin_tools'] | set(renamed))
            binary_fields = {(tag, path) for source in ('tool_fields', 'emitted_tool_fields')
                             for tag, paths in (CFORMS.get(source) or {}).items() for path in paths}
            module_fields = {(tag, path) for tag, paths in (getattr(CE, 'TOOL_FIELDS', None) or {}).items()
                             for path in paths}
            reads = {(tag, path) for tag, paths in (getattr(CE, 'TOOL_FIELDS', None) or {}).items()
                     for path, how in paths.items() if how == 'call'}
            check('format/tool-forms', 'claude_code: every field of the binary\'s messages that names a tool, declared '
                  'or emitted, is in the reader\'s table, and the tool names that ran are read as calls [%s, %s]'
                  % (sorted(binary_fields ^ module_fields)[:6], sorted(reads)),
                  binary_fields == module_fields and len(binary_fields) > 40
                  and reads == {('tool_progress', 'tool_name'), ('tool_progress', 'repl_call.inner_tool_name'),
                                ('system/task_progress', 'last_tool_name'),
                                ('system/task_progress', 'workflow_progress.lastToolName'),
                                ('assistant', 'attribution_mcp_tool'), ('assistant', 'batch_tool_uses')})
            by_kind = {how: {(tag, path) for tag, paths in (getattr(CE, 'TOOL_FIELDS', None) or {}).items()
                             for path, kind in paths.items() if kind == how} for how in ('task', 'count')}
            binary_tasks = CFORMS.get('task_counts') or {}
            module_tasks = getattr(CE, 'TASK_COUNTS', None) or {}
            check('format/tool-forms', 'claude_code: a task\'s count of its calls is read from the frames, fields and '
                  'parent the binary writes it in, and codex reports none [%s, %s, %s]'
                  % (binary_tasks.get('frames'), module_tasks, sorted(by_kind['count'])),
                  sorted(module_tasks.get('frames') or ()) == binary_tasks.get('frames')
                  == ['system/task_notification', 'system/task_progress']
                  and all(module_tasks.get(key) == binary_tasks.get(key) for key in ('count', 'task', 'parent'))
                  and binary_tasks.get('counts') == 'tool_use'
                  and binary_tasks.get('nested_forwarded_only_with') == 'forwardSubagentText'
                  and by_kind['count'] == {(tag, binary_tasks.get('count')) for tag in binary_tasks.get('frames') or ()}
                  and by_kind['task'] == {(tag, 'tool_use_id') for tag in ('system/task_notification',
                                                                          'system/task_progress', 'system/task_started')}
                  | {('assistant', binary_tasks.get('parent'))}
                  and XE is not None and getattr(XE, 'Tasks', 'absent') is None and callable(getattr(CE, 'Tasks', None)))
            frames = {(f[0], f[1]): f[2] for f in CFORMS.get('frames') or ()}
            check('format/tool-forms', 'claude_code: the frames outside the message union the reader takes as tool-free '
                  'are the ones whose schema provably carries no tool call [%s, %s]'
                  % (sorted(frames), sorted(map(str, getattr(CE, 'TOOL_FREE_FRAMES', ())))),
                  set(getattr(CE, 'TOOL_FREE_FRAMES', ())) == {tag for tag, free in frames.items() if free}
                  and {('control_request', None), ('control_response', None), ('transcript_mirror', None)}
                  == {tag for tag, free in frames.items() if not free}
                  and not set(frames) & claude_tables['messages'])
            c_nested, x_nested = CFORMS.get('nested_work') or {}, XFORMS.get('nested_work') or {}
            module_nested = dict(getattr(CE, 'NESTED', None) or {})
            binary_nested = {k: v for k, v in c_nested.items() if k not in ('tools', 'source')}
            check('format/tool-forms', 'the construct tables that can run hidden nested work are the binaries\' own '
                  '[%s, %s]' % (sorted(c_nested.get('tools') or {}), sorted(x_nested)),
                  {k: sorted(v) for k, v in (getattr(CE, 'NESTED_TOOLS', None) or {}).items()} == c_nested.get('tools')
                  and json.loads(json.dumps(module_nested)) == binary_nested
                  and {k: sorted(v) for k, v in (getattr(XE, 'NESTED_ITEMS', None) or {}).items()}
                  == {k: v for k, v in x_nested.items() if k != 'source'}
                  and set(c_nested.get('tools') or ()) == {'agent', 'cron', 'remote', 'repl', 'skill', 'workflow'}
                  and c_nested.get('remote_agent') == {'tools': ['RemoteTrigger'], 'durable': {
                      'tool': 'CronCreate', 'field': 'durable', 'off': [False, 'false']}}
                  and c_nested.get('tools', {}).get('agent', [])[:1] == ['Agent']
                  and 'system/task_started' in (c_nested.get('task_frames') or ()))
            exec_items = set(XFORMS.get('exec_items') or ())
            known = (set(getattr(XE, 'TOOL_FREE_ITEMS', ())) | set(getattr(XE, 'BUILTIN_ITEMS', ()))
                     | set(getattr(XE, 'SUBAGENT_ITEMS', ())) | {str(getattr(XE, 'MCP_ITEM', ''))})
            check('format/tool-forms', 'codex: the reader\'s item and event tables are exec\'s own, its own '
                  'collab_tool_call a sub-agent call [%s, %s]'
                  % (sorted(known ^ exec_items), sorted(map(str, set(getattr(XE, 'EVENTS', ())) ^ set(FORMATS['codex']['events'])))),
                  known == exec_items and len(exec_items) == 9 and 'collab_tool_call' in exec_items
                  and set(getattr(XE, 'SUBAGENT_ITEMS', ())) == {'collab_tool_call'}
                  and not set(getattr(XE, 'SUBAGENT_ITEMS', ())) & (set(getattr(XE, 'TOOL_FREE_ITEMS', ()))
                                                                    | set(getattr(XE, 'BUILTIN_ITEMS', ())))
                  and set(getattr(XE, 'EVENTS', ())) == set(FORMATS['codex']['events']))
            listed = {'response_blocks': set(claude_tables['response_blocks']),
                      'request_blocks': set(claude_tables['request_blocks']),
                      'messages': {m[0] for m in claude_tables['messages']},
                      'frames': {tag[0] for tag, free in frames.items() if not free},
                      'thread_items': set(XFORMS.get('thread_items') or ()), 'exec_items': exec_items}
            every = {'claude_code': set().union(listed['response_blocks'], listed['request_blocks'], listed['messages'],
                                                listed['frames'], claude_tables['stream_events'],
                                                {m[1] for m in claude_tables['messages'] if m[1]}),
                     'codex': set().union(listed['thread_items'], exec_items, FORMATS['codex']['events'])}
            wrong = []
            for provider, what, lines, form, table in UNKNOWN:
                tag = form.split(':')[-1].split('/')[-1]  # the type tag the form names
                if (tag not in listed[table]) if table else (tag in every[provider]):
                    wrong.append(what)
            check('format/tool-forms', 'each unknown-call fixture form is one the binaries list (the named ones) or one '
                  'no table lists (the unlisted ones) [%s]' % wrong, not wrong and bool(CFORMS) and bool(XFORMS)
                  and {'dynamic_tool_call', 'collab_agent_tool_call', 'sub_agent_activity'} <= listed['thread_items']
                  and not {'dynamic_tool_call', 'collab_agent_tool_call', 'sub_agent_activity'} & exec_items)

        # Installation: both new modules laid down by the scaffold, the engine copies identical.
        with region('install/assets'):
            scaffold = load('v160_scaffold', mods / 'init_scaffold.py')
            rels = ('.veldo/control_account_pool.py', '.veldo/control_account_limit.py')
            touched = rels + tuple('.veldo/' + m for m in PRODUCTION)
            check('install/assets', 'the scaffold lays down the account pool and the decision [%s]'
                  % [r for r in rels if r not in scaffold._FILES], all(r in scaffold._FILES for r in rels)
                  and not any(r in scaffold.REQUIRED_SUBSTRATE for r in rels))
            check('install/assets', 'every engine copy of a module this work touches is identical [%s]'
                  % [r for r in touched if not ((ROOT / 'engine' / r).is_file() and (ROOT / r).is_file()
                                               and (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes())],
                  all((ROOT / 'engine' / r).is_file() and (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes()
                      for r in touched))

        # AC1: an account is registered once; the same login under another name is a second registration.
        with region('pool/one-registration'):
            error = register('acct-c1', 'claude_code')
            check('pool/one-registration', 'registering acct-c1 again is refused by name [%s]' % error,
                  error in ('DuplicateAccountError', 'duplicate_account:acct-c1'))
            _, error = attempt(lambda: accounts.register('register/again-c1', 'acct-c1', 'claude_code', 'again',
                                                         {HOST: profiles['acct-c1']}, now=time.time()))
            check('pool/one-registration', 'the store refuses a second record of acct-c1 by name [%s]' % code(error),
                  code(error) == 'duplicate_account:acct-c1')
            for other, provider, directory in (('acct-c1-again', 'claude_code', profiles['acct-c1']),
                                               ('acct-x1-again', 'codex', profiles['acct-x1'] + os.sep)):
                _, error = attempt(lambda: accounts.register('register/' + other, other, provider, other,
                                                             {HOST: directory}, now=time.time()))
                owner = other.replace('-again', '')
                check('pool/one-registration', 'the login of %s registered under another name (%s) is refused by '
                      'name, and no second record exists [%s]' % (owner, other, code(error)),
                      code(error) == 'duplicate_account:' + owner and ACC.read(writer, other) is None)
            _, error = attempt(lambda: accounts.register('register/acct-c5', 'acct-c5', 'claude_code', 'fifth',
                                                         {HOST: str(base / 'profiles' / 'fifth')}, now=time.time()))
            check('pool/one-registration', 'a new login is registered [%s]' % code(error),
                  error is None and ACC.read(writer, 'acct-c5') is not None)

        # The fixtures: every line a fake engine or a fixture record carries, checked against the format table
        # extract_formats.py read out of the installed binary.
        def conform(value, schema, path):
            kind = schema.get('type')
            if value is None:
                return [] if schema.get('nullable') else [path + ': null where the schema has no null']
            if kind == 'object':
                if not isinstance(value, dict):
                    return [path + ': not an object']
                fields = schema.get('fields') or {}
                found = [path + '.' + k + ': not in the schema' for k in value if k not in fields]
                for k, field in fields.items():
                    if k in value:
                        found += conform(value[k], field, path + '.' + k)
                    elif not field.get('optional'):
                        found.append(path + '.' + k + ': required and missing')
                return found
            if kind == 'literal':
                return [] if value == schema.get('value') else [path + ': not %r' % schema.get('value')]
            if kind == 'enum':
                return [] if isinstance(value, str) and (schema.get('values') is None or value in schema['values']) \
                    else [path + ': %r not one of the enum' % value]
            if kind == 'number':
                ok_number = isinstance(value, (int, float)) and not isinstance(value, bool)
                return [] if ok_number and (not schema.get('int') or isinstance(value, int)) else [path + ': not a number']
            if kind == 'string':
                return [] if isinstance(value, str) else [path + ': not a string']
            if kind == 'boolean':
                return [] if isinstance(value, bool) else [path + ': not a boolean']
            if kind == 'array':
                if not isinstance(value, list):
                    return [path + ': not an array']
                return [p for i, item in enumerate(value) for p in conform(item, schema.get('items') or {}, '%s[%d]' % (path, i))]
            if kind == 'record':
                if not isinstance(value, dict):
                    return [path + ': not a record']
                return [p for k, item in value.items() for p in conform(item, schema.get('values') or {}, path + '.' + k)]
            if kind == 'union':
                return [] if any(not conform(value, option, path) for option in schema.get('anyOf') or []) \
                    else [path + ': matches no member of the union']
            return []

        def event_name(engine, line):
            if engine == 'codex':
                return line.get('type')
            if line.get('type') == 'system':
                return 'system/' + str(line.get('subtype'))
            if line.get('type') == 'result':
                return 'result/success' if line.get('subtype') == 'success' else 'result/error'
            return line.get('type')

        with region('format/claude-fake-lines', 'format/codex-fake-lines'):
            for engine, adapter, row, needed in (
                    ('claude_code', 'claude', 'format/claude-fake-lines',
                     ('assistant', 'result/success', 'result/error', 'rate_limit_event')),
                    ('codex', 'codex', 'format/codex-fake-lines', ('turn.completed', 'turn.failed', 'error',
                                                                     'item.started', 'item.completed'))):
                table = FORMATS[engine]
                events = table['events']
                lines = [line for owner, line in fixture_lines if owner == adapter]
                problems = []
                for line in lines:
                    name = event_name(engine, line)
                    if name not in events:
                        problems.append('%s: an event the CLI does not print' % name)
                        continue
                    problems += conform(line, events[name], name)
                    item = line.get('item') if engine == 'codex' else None
                    if isinstance(item, dict):
                        schema = (table.get('items') or {}).get(item.get('type'))
                        problems += conform(item, schema, name + '.item') if schema else [name + '.item: no item schema']
                check(row, '%s: every one of the %d lines the fakes and the fixture records carry conforms to the format '
                      'the installed binary %s (%s) declares [%s]' % (engine, len(lines), table.get('version'),
                                                                     table.get('sha256', '')[:19], problems[:4]),
                      len(lines) > 20 and not problems)
                kinds = {event_name(engine, line) for line in lines}
                check(row, '%s: the fixtures print every event the readers classify and decide from [%s]'
                      % (engine, sorted(set(needed) - kinds)), set(needed) <= kinds and set(needed) <= set(events))
            texts = [line.get('result') for owner, line in fixture_lines
                     if owner == 'claude' and line.get('type') == 'result' and line.get('is_error') is True
                     and line.get('subtype') == 'success']
            pieces = CLIMIT.get('message') and CLIMIT.get('resets') and CLIMIT.get('names') and CLIMIT.get('rejected')
            others = tuple(CLIMIT.get('rejected') or ())
            template = [t for t in texts if t.startswith(CLIMIT['message'] + CLIMIT['names']['five_hour'] + CLIMIT['resets'])
                        and t.endswith(' (UTC)')]
            plain = [t for t in texts if t in CLIMIT['not_account']]
            rest = [t for t in texts if t not in template and t not in plain]
            check('format/claude-fake-lines', 'claude_code: each rate-limit result text is the binary\'s own usage-limit '
                  'message (its template, a name of its window table, its reset piece and time format), its 429 text '
                  'that is not the account\'s limit, or one of its rejected-status texts with its own suffixes [%s]' % texts,
                  bool(pieces) and len(template) == 1 and len(plain) == 1 and len(rest) == len(others) + 1
                  and all(t.startswith(others) for t in rest) and all(any(t.startswith(o) for t in rest) for o in others))
            messages = [line.get('message') or (line.get('error') or {}).get('message') for owner, line in fixture_lines
                        if owner == 'codex' and line.get('type') in ('error', 'turn.failed')]
            table = {e['message'] for e in FORMATS['codex']['errors']}
            check('format/codex-fake-lines', 'codex: each error the fakes print is the binary\'s own: its usage-limit '
                  'message and retry phrase, or a message of its error table [%s]' % messages,
                  len(messages) == 3 and all(m.startswith(XLIMIT['message'] + '.' + XLIMIT['retry_at'][0]) or m in table
                                             for m in messages))
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        with contextlib.suppress(Exception):
            for name in ('ac1', 'moved', 'reset', 'observe', 'added', 'usage', 'order'):
                if name not in released:
                    (base / 'gates' / name).write_text('go')
        for conn in connections:
            with contextlib.suppress(Exception):
                conn.close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0160 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0160 %s detail: no check ran' % name)
        expect('VELDO-0160 ' + name, ok)
    print('VELDO-0160 suite seconds: %.3f' % (time.monotonic() - started))


_v160_suite()
