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
            'limit/stream-exhausted', 'limit/rate-limit-result',
            'decision/rerun', 'decision/ask',
            'pool/moved-off', 'pool/added-account', 'pool/one-run-while-unknown',
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
markers = Path(sys.argv[1])
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
own = {'engine': Path(sys.argv[0]).name, 'pid': os.getpid(), 'dispatch': dispatch, 'started': time.time(),
       'env': {k: os.environ.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'VELDO_ACCOUNT')}}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
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
        for name in ('claude', 'codex'):
            (engines / name).write_text(fake)
            (engines / name).chmod(0o755)
        config = base / 'receiver.json'
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(base / 'receipts'),
            'adapters': {
                'claude': {'identity': 'reported', 'engine': 'claude_code', 'environment': {'TZ': 'UTC'},
                           'argv': wrapper + [str(engines / 'claude'), str(markers)]},
                'codex': {'identity': 'reported', 'engine': 'codex', 'environment': {'TZ': 'UTC'},
                          'argv': wrapper + [str(engines / 'codex'), str(markers)]}}}))
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

        # AC2: a run its account's limit stopped is classified account_limit with its window and reset; no other.
        with region('limit/stream-exhausted', 'limit/rate-limit-result'):
            for account, provider in (('acct-l1', 'claude_code'), ('acct-l2', 'claude_code'), ('acct-l3', 'claude_code'),
                                      ('acct-l4', 'codex'), ('acct-l5', 'codex'), ('acct-l6', 'codex')):
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

        def decide(record, provider):
            if LIMIT is None:
                return None, 'no decision module'
            found, error = attempt(lambda: LIMIT.decide(record, SERVERS, MARKS, provider))
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
                          and (found or {}).get('mcp_calls') == (0 if record is none else 2))
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
                         [(first - 2, 'mailer', 'send', None, None, 'server_not_configured')])):
                    found, error = decide(record, provider)
                    check('decision/ask', '%s, %s: decided ask, naming exactly that call [%s, %s]'
                          % (provider, label, (found or {}).get('decision'), named(found) or error),
                          (found or {}).get('decision') == 'ask' and named(found) == expected)
                gap = [dict(line) for line in writes]
                gap[2]['sequence'] = 9
                found, error = decide(gap, provider)
                check('decision/ask', '%s: a record with a gap in its sequence is refused by name, never decided [%s]'
                      % (provider, error), found is None and error == 'invalid_input:record_sequence')

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
            pieces = CLIMIT.get('message') and CLIMIT.get('resets') and CLIMIT.get('names')
            check('format/claude-fake-lines', 'claude_code: each rate-limit result text is the binary\'s own usage-limit '
                  'message (its template, a name of its window table, its reset piece and time format) or its 429 text '
                  'that is not the account\'s limit [%s]' % texts,
                  bool(pieces) and len(texts) == 2 and any(
                      t.startswith(CLIMIT['message'] + CLIMIT['names']['five_hour'] + CLIMIT['resets']) and t.endswith(' (UTC)')
                      for t in texts) and any(t in CLIMIT['not_account'] for t in texts))
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
            for name in ('ac1', 'moved', 'reset', 'observe', 'added'):
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
