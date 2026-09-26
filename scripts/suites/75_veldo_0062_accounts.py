"""VELDO-0062: provider subscription logins and live usage accounting, over a real store.

Run: python3 scripts/selftest.py --suite 75_veldo_0062_accounts

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
suite loads AND the launch receiver process executes, so a registered mutation of a production module
reaches both. Real: a SQLite control store with OpenSSH journal signatures, the account records
(control_accounts) registered by the owner over profiles .veldo/accounts.py prepares, VELDO-0036
reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git source
repository, the VELDO-0039 Runner and receiver processes, and the trusted wrapper that execs the engine.
The engines are fake `claude` and `codex` executables this suite writes: each records the environment
it was started with and what the store held for its invocation at its start, then prints the stream
lines its packet scripts and exits. Every line is built in a shape the installed CLIs print (Claude Code
2.1.281's stream JSON, Codex 0.154.0's exec JSON and its usage-limit message), and the two format rows
check every line against proof/VELDO-0062/cli-formats.json, the table extract_formats.py reads out of
the real binaries, so a CLI whose format moved reds a row once the table is regenerated, with no live
run. The planted login variables are every name the binaries' credential tables list, plus probes of
each stripped family. Before the wrapper, a shell step records every spawn by its dispatch, so a
process spawned for a refused invocation is seen even when its engine never runs. No real engine runs, nothing logs in and no credential exists: planted paid-API
values are assembled at run time. The worker launches go through the wrapper without a containment
group (`identity: reported`), because a contained launch needs the systemd user manager, which this
suite never touches; the engine environment, the pre-launch reservation and the metering are the same
code on both paths. Each row is reported once: the cases of a row are parts of it.
"""


def _v62_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import re
    import threading
    import time
    import uuid

    # The installed CLIs' formats and credential tables, extracted from their binaries. Read beside this
    # suite file, so a run against another tree (the red record's) checks the same table.
    FORMATS_PATH = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2] \
        / 'proof' / 'VELDO-0062' / 'cli-formats.json'
    FORMATS = json.loads(FORMATS_PATH.read_text())

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'control_reservation_runtime.py': ROOT / ".veldo" / "control_reservation_runtime.py",
        'accounts.py': ROOT / ".veldo" / "accounts.py",
        'fleet.py': ROOT / ".veldo" / "fleet.py",
    }
    ROWS = ('login/recorded-account-profile', 'login/no-paid-api', 'login/substitution-refused', 'login/fleet-provider',
            'usage/reserved-before-launch', 'usage/allowance-states', 'usage/competing-remainder',
            'usage/cap-stops-worker', 'usage/rate-limit-reset',
            'settle/once', 'settle/model-usage', 'settle/missing-retained', 'settle/timeout-retained',
            'settle/cancel-retained',
            'attribution/stored-account', 'attribution/measurement-removed', 'attribution/watermark',
            'format/claude-fake-lines', 'format/codex-fake-lines')
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
        try:
            return fn(), None
        except Exception as error:  # noqa: BLE001 - a refusal or a missing function is data for the row
            return None, getattr(error, 'code', type(error).__name__)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='v62-', dir=fast))
    connections = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v62_store', mods / 'control_store.py')
        L = load('v62_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        # A tree without this work (the red record's) has no account records: the rows then fail by
        # their own assertions rather than by a raise.
        ACC = getattr(RES, 'ACC', None)
        HELPER = load('v62_helper', mods / 'accounts.py')
        EL = load('v62_eligibility', mods / 'control_eligibility.py')
        SIG = load('v62_signer', mods / 'control_signer.py')
        GP = load('v62_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-62', 'repository-62', 'builder-62', 'linux-host-62'
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

        # The owner's account records, over profiles the local helper prepares for either provider.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign) if ACC else None
        helper_root = base / 'helper'
        profiles = {}
        registered = []

        def register(account, provider, hosts=None, status='active'):
            record, error = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider))
            if record is None:
                record = {'config_dir': str(base / 'profiles' / account)}
                os.makedirs(record['config_dir'], mode=0o700)
            profiles[account] = record['config_dir']
            fields, error = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields is None or accounts is None:
                registered.append((account, error or 'no account records'))
                return
            if hosts is not None:
                fields['profiles'] = {host: record['config_dir'] for host in hosts}
            accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                              fields['profiles'], now=time.time())
            if status != 'active':
                accounts.status('status/' + account, account, status, now=time.time())
            registered.append((account, None))
        for account, provider in (('acct-c1', 'claude_code'), ('acct-c2', 'claude_code'), ('acct-c3', 'claude_code'),
                                  ('acct-x1', 'codex'), ('acct-x2', 'codex'), ('acct-x3', 'codex')):
            register(account, provider)
        register('acct-paused', 'claude_code', status='paused')
        register('acct-mac', 'claude_code', hosts=['mac-host-62'])
        ALL = ('acct-c1', 'acct-c2', 'acct-c3', 'acct-x1', 'acct-x2', 'acct-x3', 'acct-paused', 'acct-mac', 'acct-none')

        def roles_only(conn, command):
            # Only where the tree has no production reservation authority (the red record's).
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            return 'reservation_service' in (json.loads(row[0]) if row else {}).get('roles', [])
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=getattr(RES, 'service_authority', roles_only), signer='runner',
                                        sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        for account in ALL:
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        projects = set()

        def project(name, **caps):
            if name not in projects:
                projects.add(name)
                put('project:' + name, 'project', dict(name=name))
                reservations.configure('policy/' + name, 'project', name, dict(BIG, **caps), now=time.time())
            return name

        def admitted(unit, proj='journey', **caps):
            project(proj)
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project=proj,
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit,
                                   dict(dict(capacity=5, invocations=20, wall_seconds=10 ** 6), **caps), now=time.time())
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
        (src / 'README').write_text('usage source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fake engines. Each records its birth environment and the invocation record the store
        # holds for its dispatch at its start, then prints what its packet scripts and exits.
        markers = base / 'markers'
        markers.mkdir()
        engines = base / 'bin'
        engines.mkdir()
        # The login variables planted in the caller's environment: every name the binaries' credential
        # tables this work strips list (from the extracted table, never from production), the nine the
        # finding named, and a probe of every stripped family a later CLI could add a name to. Kept: a
        # neutral variable, a Claude Code count setting and the tool credentials of the tables kept.
        TABLED = sorted({n for engine in ('claude_code', 'codex') for table in FORMATS[engine]['credential_tables']
                         if table['decision'] == 'strip' for n in table['names']})
        NINE = ['CODEX_ACCESS_TOKEN', 'CLAUDE_CODE_USE_ANTHROPIC_AWS', 'ANTHROPIC_AWS_API_KEY', 'CLAUDE_CODE_USE_GATEWAY',
                'CLAUDE_CODE_USE_MANTLE', 'CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD', 'ANTHROPIC_FOUNDRY_AUTH_TOKEN',
                'CLAUDE_CODE_OAUTH_REFRESH_TOKEN', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN']
        probe = os.urandom(3).hex().upper()
        FAMILIES = ['ANTHROPIC_V62_' + probe, 'OPENAI_V62_' + probe, 'CODEX_V62_' + probe, 'CLAUDE_CODE_USE_V62_' + probe,
                    'CLAUDE_CODE_V62_%s_TOKEN' % probe, 'CLAUDE_V62_%s_API_KEY' % probe, 'CLAUDE_V62_%s_OAUTH' % probe]
        STRIPPED = sorted(set(TABLED) | set(NINE) | set(FAMILIES))
        KEPT = ['V62_NEUTRAL_' + probe, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS', 'AWS_SECRET_ACCESS_KEY', 'HF_TOKEN']
        fake = '''#!%s -B
import json, os, sqlite3, sys, time
from pathlib import Path
store, markers, domain = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
key = 'reservation:invocation:' + json.dumps([domain, 'invocation/' + dispatch], separators=(',', ':'))
try:
    db = sqlite3.connect('file:%%s?mode=ro' %% store, uri=True, timeout=10)
    row = db.execute('SELECT data FROM entities WHERE id=?', (key,)).fetchone()
    seen = json.loads(row[0]) if row else None
    db.close()
except Exception as error:
    seen = {'error': repr(error)}
own = {'engine': Path(sys.argv[0]).name, 'pid': os.getpid(), 'dispatch': dispatch, 'started': time.time(),
       'invocation': seen, 'names': sorted(os.environ),
       'env': {k: os.environ.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'VELDO_ACCOUNT')}}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
out = open(markers / ('%%d.out' %% os.getpid()), 'w')
for step in payload.get('script') or []:
    if 'line' in step:
        text = json.dumps(step['line'])
        out.write(text + chr(10))
        out.flush()
        sys.stdout.write(text + chr(10))
        sys.stdout.flush()
    elif 'sleep' in step:
        time.sleep(step['sleep'])
out.close()
(markers / ('%%d.done' %% os.getpid())).write_text('done')
sys.exit(payload.get('code', 0))
''' % (sys.executable,)
        for name in ('claude', 'codex'):
            (engines / name).write_text(fake)
            (engines / name).chmod(0o755)
        receipts = base / 'receipts'
        config = base / 'receiver.json'
        # Every process the receiver spawns first writes a spawn marker naming its dispatch, then execs
        # the trusted wrapper (the same pid): a spawn is recorded even when its engine never runs.
        spawn = ['/bin/sh', '-c', 'printf %s "$VELDO_DISPATCH_ID" > "$0/spawn-$$"; exec "$@"', str(markers)]
        wrapper = spawn + [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        planted = {}

        def plant(name):
            planted[name] = 'planted-' + os.urandom(6).hex()
            return planted[name]
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(receipts),
            'adapters': {
                'claude': {'identity': 'reported', 'engine': 'claude_code',
                           'environment': {'ANTHROPIC_API_KEY': plant('adapter-anthropic')},
                           'argv': wrapper + [str(engines / 'claude'), str(db), str(markers), DOMAIN]},
                'codex': {'identity': 'reported', 'engine': 'codex',
                          'environment': {'OPENAI_API_KEY': plant('adapter-openai')},
                          'argv': wrapper + [str(engines / 'codex'), str(db), str(markers), DOMAIN]}}}))
        CONFIGURATION = {'mcp_servers': {'tracker': {'command': 'tracker-mcp', 'args': []}},
                         'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        environment = [None]

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30, environment=environment[0])
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]

        # Every line a fake engine is scripted to print, by adapter, for the format rows.
        fixture_lines = []

        def job(adapter, script, code=0, deadline=40, resume=None):
            if adapter == 'codex':
                script = [x_thread()] + list(script)  # `codex exec --json` opens every stream with its thread.
            fixture_lines.extend((adapter, step['line']) for step in script if 'line' in step)
            payload = {'task': 'work the unit', 'script': script, 'code': code}
            if resume:
                payload['resume'] = resume
            return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

        def run(account, unit, adapter, script, env=None, wait=True, **kwargs):
            environment[0] = env
            try:
                launch = runner(account).submit(unit, 'build', **job(adapter, script, **kwargs))
            finally:
                environment[0] = None
            record = runner(account).wait(launch) if wait else None
            return launch, record

        def engine_markers(dispatch_id):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    data['done'] = (markers / ('%d.done' % data['pid'])).exists()
                    printed = markers / ('%d.out' % data['pid'])
                    data['printed'] = [line.encode() for line in printed.read_text().split('\n') if line] \
                        if printed.exists() else []
                    found.append(data)
            return found

        def spawned(dispatch_id, timeout=0.0):
            # The processes spawned for a dispatch, waiting up to `timeout` for a late one.
            end = time.time() + timeout
            while True:
                found = [path for path in sorted(markers.glob('spawn-*')) if path.read_text() == dispatch_id]
                if found or time.time() >= end:
                    return len(found)
                time.sleep(0.02)

        def marker_wait(dispatch_id, timeout=15.0):
            end = time.time() + timeout
            while time.time() < end:
                found = engine_markers(dispatch_id)
                if found:
                    return found[0]
                time.sleep(0.02)
            return {}

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def invocation(dispatch_id):
            found = entity(RES.entity('invocation', [DOMAIN, 'invocation/' + dispatch_id]))
            return (found or {}).get('data') or {}

        def refusal_of(launch):
            return (rec(launch.dispatch_id) or {}).get('refusal')


        def account_record(account):
            return (ACC.read(writer, account) if ACC else None) or {}

        def usage_shown():
            shown, error = attempt(lambda: ACC.usage(reservations, accounts))
            return shown or {'account': {}, 'project': {}, 'unit': {}, 'error': error}

        def journal_seq(prefix):
            row = writer.execute('SELECT MIN(seq) FROM journal WHERE substr(command_id, 1, ?) = ?',
                                 (len(prefix), prefix)).fetchone()
            return row[0] if row else None

        # The stored raw receipts, read and totalled by this suite's own reading of the CLI lines.
        def receipt_file(dispatch_id):
            return receipts / (hashlib.sha256(('invocation/' + dispatch_id).encode()).hexdigest() + '.jsonl')

        def receipt_read(dispatch_id):
            path = receipt_file(dispatch_id)
            if not path.exists():
                return {}, []
            raw = path.read_bytes().split(b'\n')
            return json.loads(raw[0]), [line for line in raw[1:] if line]

        def receipt_header(dispatch_id):
            return receipt_read(dispatch_id)[0]

        def receipt_lines(dispatch_id):
            return receipt_read(dispatch_id)[1]

        def receipt_private(dispatch_id):
            path = receipt_file(dispatch_id)
            return (path.exists() and (path.stat().st_mode & 0o777) == 0o600
                    and (path.parent.stat().st_mode & 0o777) == 0o700)

        def recompute(provider, lines, stream=False):
            """This suite's own reading of CLI lines: Claude Code's tokens are the latest result's
            modelUsage over every model (the four token counts), never below the distinct assistant
            messages' own counts (nested breakdowns never added); Codex's the completed turns'. A stored
            receipt keeps only the lines that reported usage, so each completion in it is one turn;
            over the whole printed `stream` a completion counts only when it closes an open turn."""
            events = [json.loads(line) for line in lines]

            def n(value):
                return value if isinstance(value, int) and not isinstance(value, bool) else 0
            if provider in ('claude', 'claude_code'):
                messages, tokens, turns = {}, None, 0
                for event in events:
                    if event.get('type') == 'assistant':
                        message = event.get('message') or {}
                        usage = message.get('usage') or {}
                        messages[message.get('id')] = max(messages.get(message.get('id'), 0), sum(
                            n(usage.get(k)) for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens',
                                                      'cache_read_input_tokens')))
                    if event.get('type') == 'result':
                        turns = max(turns, n(event.get('num_turns')))
                        models = event.get('modelUsage')
                        if isinstance(models, dict):
                            total = sum(n(m.get(k)) for m in models.values() for k in (
                                'inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens'))
                            tokens = total if tokens is None else max(tokens, total)
                streamed = sum(messages.values())
                return {'tokens': streamed if tokens is None else max(streamed, tokens),
                        'messages': max(len(messages), turns)}
            done, open_turn = [], False
            for event in events:
                if event.get('type') == 'turn.started':
                    open_turn = True
                elif event.get('type') == 'turn.completed' and (open_turn or not stream):
                    done.append(event)  # a completion closes the turn it answers; one with none open is a repeat
                    open_turn = False
            return {'tokens': sum(n(e['usage'].get('input_tokens')) + n(e['usage'].get('output_tokens')) for e in done),
                    'messages': len(done)}

        def receipts_by_account():
            totals = {}
            for path in sorted(receipts.glob('*.jsonl')):
                raw = path.read_bytes().split(b'\n')
                header = json.loads(raw[0])
                account = ((rec(header['dispatch_id']).get('contract') or {}).get('reservation') or {}).get('account')
                found = recompute(header['provider'], [line for line in raw[1:] if line])
                total = totals.setdefault(account, {'invocations': 0, 'tokens': 0, 'messages': 0})
                total['invocations'] += 1
                total['tokens'] += found['tokens']
                total['messages'] += found['messages']
            return totals

        def receipts_tokens(dispatch_id):
            header, lines = receipt_read(dispatch_id)
            return recompute(header.get('provider'), lines)['tokens'] if header else None

        # Stream lines in the shapes the installed CLIs print (the format rows check each one against
        # the table extracted from the binaries). Claude Code 2.1.281's stream JSON:
        SESSION = 'session-62-' + os.urandom(4).hex()

        def c_usage(inp, out, read=0, create=0):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': create,
                    'cache_read_input_tokens': read,
                    'cache_creation': {'ephemeral_5m_input_tokens': create, 'ephemeral_1h_input_tokens': 0},
                    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}, 'service_tier': 'standard'}

        def c_init():
            return {'line': {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'claude_code_version': '2.1.281',
                             'cwd': '/work', 'tools': ['Read', 'Edit', 'Bash'],
                             'mcp_servers': [{'name': 'tracker', 'status': 'connected'}], 'model': 'configured-model',
                             'permissionMode': 'default', 'slash_commands': [], 'output_style': 'default', 'skills': [],
                             'plugins': [], 'uuid': str(uuid.uuid4()), 'session_id': SESSION}}

        def c_msg(mid, inp, out, read=0, create=0, parent=None):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': parent, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'configured-model',
                                         'content': [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out, read, create)}}}

        def c_result(inp, out, turns, cache=0, models=None, main=None):
            # `usage` is the main loop's; `modelUsage` per model over every call, the total accounted.
            models = models or {'configured-model': (inp, out, cache, 0)}
            return {'line': {
                'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False,
                'num_turns': turns, 'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0,
                'usage': c_usage(*(main or (inp, out, cache, 0))),
                'modelUsage': {name: {'inputTokens': i, 'outputTokens': o, 'cacheReadInputTokens': r,
                                      'cacheCreationInputTokens': c, 'webSearchRequests': 0, 'costUSD': 0,
                                      'contextWindow': 200000, 'maxOutputTokens': 32000}
                               for name, (i, o, r, c) in models.items()},
                'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': SESSION}}

        def c_rate(status, reset, kind='five_hour', utilization=None):
            info = {'status': status, 'rateLimitType': kind}
            if reset is not None:
                info['resetsAt'] = int(reset)
            if utilization is not None:
                info['utilization'] = utilization
            return {'line': {'type': 'rate_limit_event', 'rate_limit_info': info, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION}}

        # Codex 0.154.0's exec JSON and its usage-limit message.
        def x_thread():
            return {'line': {'type': 'thread.started', 'thread_id': 'thread-62-' + os.urandom(4).hex()}}

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

        LIMIT = FORMATS['codex']['usage_limit']

        def x_limit_message(reset):
            """The usage-limit message Codex prints, from the binary's own pieces: a stated reset in the
            local time of this process (the engine inherits its zone), or none."""
            if reset is None:
                return LIMIT['message'] + '.' + LIMIT['retry_later'][0]
            at, now = time.localtime(reset), time.localtime()
            clock = '%d:%02d %s' % (at.tm_hour % 12 or 12, at.tm_min, 'AM' if at.tm_hour < 12 else 'PM')
            if (at.tm_year, at.tm_yday) != (now.tm_year, now.tm_yday):
                day = at.tm_mday
                suffix = 'th' if 11 <= day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                clock = '%s %d%s, %d %s' % (('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                                  'Dec')[at.tm_mon - 1], day, suffix, at.tm_year, clock)
            return LIMIT['message'] + '.' + LIMIT['retry_at'][0] + clock + '.'

        def ok(adapter, inp=1, out=1):
            """A normal, complete report of one small invocation, in the adapter's own format."""
            return [c_result(inp, out, 1)] if adapter == 'claude' else [x_started(), x_done(inp, out)]

        # AC2, first because its minute must pass: Codex's usage-limit message, one stating its reset (the
        # end of the minute it names, within the next minute) and one stating none.
        limited = {'stated': None}
        with region('usage/rate-limit-reset'):
            minute = (int(time.time()) + 8) // 60 * 60
            limited['stated'] = minute + 60
            for account, stated in (('acct-x2', minute), ('acct-x3', None)):
                message = x_limit_message(stated)
                launch, record = run(account, admitted('VELDO-6208-%s-a' % account), 'codex',
                                     [x_started(), x_error(message), x_failed(message)], code=1)
                limited[account] = launch.dispatch_id
            for account, codex_reset in (('acct-x2', limited['stated']), ('acct-x3', None)):
                stored = (account_record(account).get('windows') or {}).get('usage_limit') or {}
                check('usage/rate-limit-reset', 'codex %s: the usage-limit message is recorded on the account as an '
                      'exhausted window, its reset %s, from its dispatch [%s]'
                      % (account, 'the end of the minute it stated' if codex_reset else 'unknown, none stated', stored),
                      stored.get('status') == 'rejected' and stored.get('reset_at') == codex_reset
                      and stored.get('source_dispatch') == limited.get(account))
                launch, record = run(account, admitted('VELDO-6208-%s-b' % account), 'codex', ok('codex'))
                check('usage/rate-limit-reset', 'codex %s: inside the reported window a new invocation is refused by '
                      'name and nothing launches [%s]' % (account, (record or {}).get('refusal')),
                      (record or {}).get('refusal') == 'missing_authority:allowance:rate_limited:usage_limit'
                      and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id)
                      and (codex_reset is None or time.time() < codex_reset))

        # AC1: the login of the account the dispatch recorded, never the caller's; no paid API.
        with region('login/recorded-account-profile', 'login/no-paid-api'):
            caller = dict(os.environ, CLAUDE_CONFIG_DIR=profiles['acct-c3'], CODEX_HOME=profiles['acct-x2'],
                          VELDO_ACCOUNT='acct-c3')
            for name in STRIPPED + KEPT:
                caller[name] = plant('caller-' + name.lower())
            seen = {}
            for account, adapter, script in (('acct-c1', 'claude', [c_init(), c_msg('m1', 3, 2), c_result(3, 2, 1)]),
                                             ('acct-c2', 'claude', [c_result(1, 1, 1)]),
                                             ('acct-x1', 'codex', [x_started(), x_done(2, 1)])):
                launch, record = run(account, admitted('VELDO-6201-' + account), adapter, script, env=caller)
                found = engine_markers(launch.dispatch_id)
                seen[account] = (launch, record or {}, found[0] if len(found) == 1 else {})
            for account, (launch, record, own) in seen.items():
                recorded = ((record.get('contract') or {}).get('reservation') or {}).get('account')
                variable = 'CODEX_HOME' if account.startswith('acct-x') else 'CLAUDE_CONFIG_DIR'
                other = 'CLAUDE_CONFIG_DIR' if variable == 'CODEX_HOME' else 'CODEX_HOME'
                env = own.get('env') or {}
                check('login/recorded-account-profile', '%s: the dispatch recorded the account the Runner selected and '
                      'its engine ran once, to its end [%s, %s]' % (account, recorded, record.get('state')),
                      recorded == account and record.get('state') == 'exited' and own.get('done') is True)
                check('login/recorded-account-profile', '%s: %s is that account\'s registered profile on this host, '
                      'not the caller\'s [%s]' % (account, variable, env.get(variable)),
                      bool(env.get(variable)) and env.get(variable) == profiles[account]
                      == (account_record(account).get('profiles') or {}).get(HOST) and env.get(variable) != caller[variable])
                check('login/recorded-account-profile', '%s: no other provider\'s profile reached it [%s]'
                      % (account, env.get(other)), env.get(other) is None)
                check('login/recorded-account-profile', '%s: its ambient account label is the recorded one [%s]'
                      % (account, env.get('VELDO_ACCOUNT')), env.get('VELDO_ACCOUNT') == account)
                names = set(own.get('names') or ())
                leaked = sorted(set(STRIPPED + ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']) & names)
                check('login/no-paid-api', '%s: no login variable reached the engine: none of the %d the binaries\' '
                      'credential tables list, the nine the finding named or the family probes, planted in the '
                      'caller\'s environment and in the adapter\'s [%s]' % (account, len(TABLED), leaked[:12]),
                      bool(names) and not leaked)
                check('login/no-paid-api', '%s: what is not a login still reached it: a neutral variable, a count '
                      'setting and the tool credentials of the kept tables [%s]'
                      % (account, sorted(set(KEPT) - names)), bool(names) and set(KEPT) <= names)
            check('login/recorded-account-profile', 'the two Claude Code accounts ran on two different profiles',
                  (seen['acct-c1'][2].get('env') or {}).get('CLAUDE_CONFIG_DIR')
                  != (seen['acct-c2'][2].get('env') or {}).get('CLAUDE_CONFIG_DIR'))
            check('login/recorded-account-profile', 'the owner registered every account [%s]'
                  % [r for r in registered if r[1]], len(registered) == 8 and not [r for r in registered if r[1]])
            check('login/no-paid-api', 'every tabled name, the nine and the probes were planted [%d tabled, %d]'
                  % (len(TABLED), len(STRIPPED)), len(TABLED) >= 60 and set(NINE) <= set(TABLED)
                  and all(caller.get(name) for name in STRIPPED + KEPT))

        with region('login/substitution-refused'):
            cases = []
            for field in ('account', 'unit', 'station'):
                unit = admitted('VELDO-6202-' + field)
                contract = runner('acct-c1').prepare(unit, 'build', **job('claude', ok('claude')))
                tampered = json.loads(json.dumps(contract))
                if field == 'account':
                    tampered['reservation']['account'] = 'acct-c2'
                elif field == 'unit':
                    tampered['unit'] = 'VELDO-6201-acct-c2'
                else:
                    tampered['station'] = 'review'
                launch = L.invoke(config, tampered, dispatches, accept_seconds=30)
                launch.wait()
                cases.append((field, contract['dispatch_id'], rec(contract['dispatch_id']).get('refusal'),
                              'binding_mismatch:contract_digest'))
            unit = admitted('VELDO-6202-expiry')
            contract = runner('acct-c1').prepare(unit, 'build', **job('claude', ok('claude'), deadline=1.0))
            time.sleep(1.3)
            launch = L.invoke(config, contract, dispatches, accept_seconds=30)
            launch.wait()
            cases.append(('expiry', contract['dispatch_id'], rec(contract['dispatch_id']).get('refusal'), 'deadline_passed'))
            for account, adapter, expected in (
                    ('acct-paused', 'claude', 'missing_authority:account_status:paused'),
                    ('acct-mac', 'claude', 'missing_authority:account_profile:' + HOST),
                    ('acct-x1', 'claude', 'invalid_input:account_provider:codex:claude_code'),
                    ('acct-c1', 'codex', 'invalid_input:account_provider:claude_code:codex'),
                    ('acct-none', 'claude', 'missing_authority:account')):
                launch, record = run(account, admitted('VELDO-6203-%s-%s' % (account, adapter)), adapter,
                                     ok(adapter))
                cases.append((account + '/' + adapter, launch.dispatch_id, (record or {}).get('refusal'), expected))
            for name, dispatch_id, refusal, expected in cases:
                check('login/substitution-refused', '%s substituted or unusable: refused by name, nothing launched, '
                      'nothing reserved [%s]' % (name, refusal),
                      refusal == expected and rec(dispatch_id).get('state') == 'refused'
                      and not engine_markers(dispatch_id) and not spawned(dispatch_id) and not invocation(dispatch_id))

        # AC1, the fleet's in-session workers: a Claude Code session takes only a Claude Code login.
        with region('login/fleet-provider'):
            FL = load('v62_fleet', mods / 'fleet.py')
            started_envs = []

            def start(worker_id, env):
                started_envs.append(dict(env))
                return {'worker': worker_id}
            pool, pool_error = attempt(lambda: FL.make_in_session_spawner(start, accounts_root=str(helper_root)))
            claude_profiles = sorted(profiles[a] for a in ('acct-c1', 'acct-c2', 'acct-c3', 'acct-paused', 'acct-mac'))
            codex_profiles = {profiles[a] for a in ('acct-x1', 'acct-x2', 'acct-x3')}
            if pool is not None:
                spawner, capacity = pool
                for n in range(capacity):
                    spawner.spawn('w-62-%d' % n, None)
            given = sorted(env.get('CLAUDE_CONFIG_DIR') for env in started_envs)
            check('login/fleet-provider', 'the default fleet pool is the registered Claude Code accounts, each worker '
                  'on its own Claude profile, no Codex profile handed to a Claude session [%s, %d workers]'
                  % (pool_error, len(started_envs)),
                  pool is not None and pool[1] == 5 and given == claude_profiles and not codex_profiles & set(given))
            for label, kwargs in (('pinned', {'account': 'acct-x1'}), ('listed', {'accounts': ['acct-c1', 'acct-x2']})):
                before, error, made = len(started_envs), None, None
                try:
                    made = FL.make_in_session_spawner(start, accounts_root=str(helper_root), **kwargs)
                except Exception as exc:  # noqa: BLE001 - the refusal is data for the row
                    error = exc
                if made is not None:
                    attempt(lambda: made[0].spawn('w-62-x', None))
                own = FL.ACCT  # the fleet's own load of the helper
                check('login/fleet-provider', 'a Codex account %s for a Claude fleet is refused by name before any '
                      'worker starts [%s: %s]' % (label, type(error).__name__, str(error)[:160]),
                      made is None and isinstance(error, own.AccountError)
                      and not isinstance(error, own.UnknownAccountError) and 'codex' in str(error)
                      and len(started_envs) == before)

        # AC2: every invocation boundary checked and reserved before its launch.
        with region('usage/reserved-before-launch'):
            order = []
            for account, adapter, script in (('acct-c1', 'claude', [c_result(2, 1, 1)]),
                                             ('acct-x1', 'codex', [x_started(), x_done(2, 1)])):
                unit = admitted('VELDO-6204-' + adapter, invocations=3)
                for boundary, resume in (('initial', None), ('retry', None), ('follow_on', 'session-' + adapter)):
                    launch, record = run(account, unit, adapter, script, resume=resume)
                    own = engine_markers(launch.dispatch_id)
                    seen = (own[0] if own else {}).get('invocation') or {}
                    call = invocation(launch.dispatch_id)
                    reserved_at = journal_seq('call/' + launch.dispatch_id)
                    ran_at = journal_seq('dispatch/run/%s/' % launch.dispatch_id)
                    order.append((adapter, boundary, call.get('boundary'), seen.get('state'), seen.get('boundary'),
                                  len(own), (record or {}).get('state')))
                    check('usage/reserved-before-launch', '%s %s: reserved as %s before the engine started, which saw its '
                          'pending reservation at its start, one launch [%s, %s, %d]'
                          % (adapter, boundary, boundary, call.get('boundary'), seen.get('state'), len(own)),
                          call.get('boundary') == boundary and seen.get('state') == 'pending'
                          and seen.get('boundary') == boundary and len(own) == 1 and spawned(launch.dispatch_id) == 1
                          and (record or {}).get('state') == 'exited'
                          and None not in (reserved_at, ran_at) and reserved_at < ran_at)
                launch, record = run(account, unit, adapter, script, resume='session-' + adapter)
                # A process spawned before the check has written its spawn marker within this wait, even
                # when its engine never ran; an engine started before the check, its own marker.
                late = spawned(launch.dispatch_id, timeout=3.0) or bool(marker_wait(launch.dispatch_id, timeout=0.5))
                check('usage/reserved-before-launch', '%s follow-on past the unit\'s invocation cap: refused before '
                      'launch, nothing spawned [%s, %s]' % (adapter, (record or {}).get('refusal'), late),
                      (record or {}).get('refusal') == 'missing_authority:allowance:usage_cap:unit:invocations'
                      and not late and not invocation(launch.dispatch_id)
                      and reservations.balances('unit', unit)['invocations'] == 3)

        with region('usage/allowance-states'):
            for account, adapter, done in (('acct-c1', 'claude', [c_result(5, 5, 1)]),
                                           ('acct-x1', 'codex', [x_started(), x_done(5, 5)])):
                unit = admitted('VELDO-6205-%s-available' % adapter, tokens=100)
                launch, record = run(account, unit, adapter, done)
                check('usage/allowance-states', '%s available allowance: launched once and settled [%s, %s]'
                      % (adapter, (record or {}).get('state'), invocation(launch.dispatch_id).get('state')),
                      (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1
                      and invocation(launch.dispatch_id).get('state') == 'settled'
                      and invocation(launch.dispatch_id).get('charge', {}).get('tokens') == 10)
                unit = admitted('VELDO-6205-%s-exhausted' % adapter, invocations=0)
                launch, record = run(account, unit, adapter, done)
                check('usage/allowance-states', '%s exhausted allowance: refused by name, nothing launched [%s]'
                      % (adapter, (record or {}).get('refusal')),
                      (record or {}).get('refusal') == 'missing_authority:allowance:usage_cap:unit:invocations'
                      and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id))
                proj = project('p-unknown-' + adapter, tokens=1000)
                unit = admitted('VELDO-6205-%s-unknown-a' % adapter, proj)
                first, first_record = run(account, unit, adapter, [])
                unit = admitted('VELDO-6205-%s-unknown-b' % adapter, proj)
                launch, record = run(account, unit, adapter, done)
                check('usage/allowance-states', '%s unknown allowance (an earlier call reported no tokens): refused by '
                      'name, nothing launched [%s]' % (adapter, (record or {}).get('refusal')),
                      invocation(first.dispatch_id).get('state') == 'unknown'
                      and (record or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                      and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id))

        with region('usage/competing-remainder'):
            proj = project('p-race', invocations=1)
            contracts = [runner('acct-c1').prepare(admitted('VELDO-6206-%d' % n, proj), 'build',
                                                   **job('claude', [{'sleep': 0.3}, c_result(1, 1, 1)]))
                         for n in range(2)]
            barrier = threading.Barrier(2)
            launched = [None, None]

            def contend(n):
                # Each contender reads the records on a connection of its own thread.
                mine = S.open_store(str(db))
                connections.append(mine)
                own = D.Dispatches(S, mine, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                   signer='runner', sign=sign)
                barrier.wait()
                launch = L.invoke(config, contracts[n], own, accept_seconds=30)
                launch.wait()
                launched[n] = launch
            threads = [threading.Thread(target=contend, args=(n,)) for n in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(60)
            states = sorted((rec(c['dispatch_id']).get('state'), rec(c['dispatch_id']).get('refusal')) for c in contracts)
            starts = sum(len(engine_markers(c['dispatch_id'])) for c in contracts)
            spawns = sum(spawned(c['dispatch_id']) for c in contracts)
            check('usage/competing-remainder', 'two invocations for one remaining invocation: one launched, the other '
                  'refused by name [%s, %d launches, %d spawns]' % (states, starts, spawns),
                  states == [('exited', None), ('refused', 'missing_authority:allowance:usage_cap:project:invocations')]
                  and starts == 1 and spawns == 1 and reservations.balances('project', proj)['invocations'] == 1)

        with region('usage/cap-stops-worker'):
            for account, adapter, script in (
                    ('acct-c1', 'claude', [c_msg('m1', 400, 200), {'sleep': 0.2}, c_msg('m2', 400, 200), {'sleep': 30},
                                           c_result(800, 400, 2)]),
                    ('acct-x1', 'codex', [x_started(), x_done(800, 400), {'sleep': 30}, x_started(), x_done(1, 1)])):
                unit = admitted('VELDO-6207-' + adapter, tokens=1000)
                began = time.monotonic()
                launch, record = run(account, unit, adapter, script)
                elapsed = time.monotonic() - began
                own = engine_markers(launch.dispatch_id)
                call = invocation(launch.dispatch_id)
                check('usage/cap-stops-worker', '%s: the report that reached the token cap stopped the worker, which '
                      'never finished [%.1f s, %s, %s]' % (adapter, elapsed, (launch.supervision or {}).get('cause'),
                                                          call.get('outcome')),
                      len(own) == 1 and own[0]['done'] is False and elapsed < 20
                      and (launch.supervision or {}).get('cause') == 'usage_cap'
                      and call.get('outcome') == 'cancelled' and call.get('observed', {}).get('tokens') == 1200
                      and call.get('charge', {}).get('invocations') == 1)

        with region('usage/rate-limit-reset'):
            reset = int(time.time()) + 5
            launch, record = run('acct-c3', admitted('VELDO-6208-claude-a'), 'claude',
                                 [c_rate('rejected', reset, 'five_hour', 1.0), c_result(1, 1, 1)])
            stored = (account_record('acct-c3').get('windows') or {}).get('five_hour') or {}
            check('usage/rate-limit-reset', 'claude: the reported window is recorded on the account with its reported '
                  'reset and source dispatch [%s]' % stored,
                  stored.get('status') == 'rejected' and stored.get('reset_at') == reset
                  and stored.get('source_dispatch') == launch.dispatch_id)
            launch, record = run('acct-c3', admitted('VELDO-6208-claude-b'), 'claude', ok('claude'))
            check('usage/rate-limit-reset', 'claude: inside the reported window a new invocation is refused by name '
                  'and nothing launches [%s]' % (record or {}).get('refusal'),
                  (record or {}).get('refusal') == 'missing_authority:allowance:rate_limited:five_hour'
                  and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id) and time.time() < reset)
            blocked, _ = attempt(lambda: ACC.blocking(account_record('acct-x3'), time.time() + 10 ** 7))
            check('usage/rate-limit-reset', 'codex acct-x3: with no reset stated the account stays refused however '
                  'long, until a later observation says otherwise [%s]' % blocked, blocked == ['usage_limit'])
            while time.time() < reset + 0.2:
                time.sleep(0.1)
            launch, record = run('acct-c3', admitted('VELDO-6208-claude-c'), 'claude', ok('claude'))
            check('usage/rate-limit-reset', 'claude: at the reported reset the account takes work again [%s]'
                  % (record or {}).get('state'),
                  (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1)
            # Codex's stated reset is checked at the end of the suite, when its minute has passed.

        # AC3: one settlement per invocation and sequence; incomplete reports keep their reservation.
        with region('settle/once'):
            expected = {'claude': {'tokens': 160, 'messages': 1}, 'codex': {'tokens': 300, 'messages': 1}}
            settled = {}
            for account, adapter, script in (
                    ('acct-c1', 'claude', [c_msg('m1', 100, 50), c_msg('m1', 100, 50), c_result(100, 50, 1, cache=10),
                                           c_result(100, 50, 1, cache=10)]),
                    ('acct-x1', 'codex', [x_started(), x_done(200, 100), x_done(200, 100)])):
                unit = admitted('VELDO-6209-' + adapter)
                launch, record = run(account, unit, adapter, script)
                call = invocation(launch.dispatch_id)
                settled[adapter] = (launch, call, unit)
                check('settle/once', '%s: a normal report settles the CLI\'s own totals once, the repeated lines '
                      'counted once [%s, %s]' % (adapter, call.get('charge'), call.get('state')),
                      call.get('state') == 'settled' and call.get('outcome') == 'completed'
                      and {k: call.get('charge', {}).get(k) for k in ('tokens', 'messages', 'invocations')}
                      == dict(expected[adapter], invocations=1)
                      and reservations.balances('unit', unit)['tokens'] == expected[adapter]['tokens'])
                # The same report delivered again settles nothing twice; a changed one is refused.
                last = call.get('reports', {}).get(str(call.get('sequence')), {})
                balance = reservations.balances('unit', unit)
                again, again_error = attempt(lambda: reservations.report(
                    'redeliver/' + launch.dispatch_id, 'invocation/' + launch.dispatch_id, last.get('sequence'),
                    last.get('usage'), final=last.get('final'), outcome=last.get('outcome'),
                    receipts=last.get('receipts', ()), now=time.time()))
                changed, changed_error = attempt(lambda: reservations.report(
                    'conflict/' + launch.dispatch_id, 'invocation/' + launch.dispatch_id, last.get('sequence'),
                    dict(last.get('usage') or {}, tokens=1), final=True, outcome='completed', now=time.time()))
                check('settle/once', '%s: a duplicate delivery changes no balance, a conflicting one is refused [%s, %s]'
                      % (adapter, again_error, changed_error),
                      again_error is None and reservations.balances('unit', unit) == balance
                      and changed_error == 'report_conflict')
            # Independently, from the stored raw receipts: each ledger digest is its line's, and the totals
            # recomputed from the lines equal the balances in each declared unit.
            for adapter, (launch, call, unit) in settled.items():
                lines = receipt_lines(launch.dispatch_id)
                digests = ['sha256:' + hashlib.sha256(line).hexdigest() for line in lines]
                ledger = sorted({d for report in call.get('reports', {}).values() for d in report.get('receipts', [])})
                recomputed = recompute(adapter, lines)
                own = engine_markers(launch.dispatch_id)
                printed = recompute(adapter, own[0]['printed'], stream=True) if own else None
                check('settle/once', '%s: the raw receipts are private and every ledger digest is a stored line\'s, the '
                      'totals recomputed from them equal the balance and the lines the engine itself printed '
                      '[%s, %s]' % (adapter, recomputed, printed),
                      bool(lines) and ledger == sorted(set(digests)) and recomputed == expected[adapter] == printed
                      and receipt_private(launch.dispatch_id))

        # The CLI's own conclusive total counts every model call, subagents and sidechains included.
        with region('settle/model-usage'):
            unit = admitted('VELDO-6215-model-usage')
            models = {'claude-opus-4-7': (20, 3000, 60000, 8000), 'claude-haiku-4-5': (100, 600, 25000, 4900)}
            script = [c_init(), c_msg('mu-main', 12, 500, read=4000, create=500),
                      c_msg('mu-sub', 10, 400, read=3000, create=590, parent='toolu_62_subagent'),
                      c_result(12, 500, 1, models=models, main=(12, 500, 4000, 500))]
            launch, record = run('acct-c1', unit, 'claude', script)
            call = invocation(launch.dispatch_id)
            header, lines = receipt_read(launch.dispatch_id)
            own = engine_markers(launch.dispatch_id)
            total = sum(sum(v) for v in models.values())
            main_loop = 12 + 500 + 4000 + 500
            check('settle/model-usage', 'claude: a main-loop message, a subagent message and a result settle the '
                  'result\'s modelUsage over every model, not its main-loop usage [%s settled, %d modelUsage, %d main '
                  'loop]' % (call.get('charge', {}).get('tokens'), total, main_loop),
                  total == 101620 and call.get('state') == 'settled'
                  and call.get('charge', {}).get('tokens') == total != main_loop
                  and call.get('charge', {}).get('messages') == 2
                  and reservations.balances('unit', unit)['tokens'] == total)
            check('settle/model-usage', 'claude: the stored raw receipt, read by this suite, and the lines the engine '
                  'printed recompute the same total [%s, %s]'
                  % (recompute('claude', lines) if lines else None,
                     recompute('claude', own[0]['printed'], stream=True) if own else None),
                  bool(lines) and bool(own) and recompute('claude', lines)['tokens'] == total
                  == recompute('claude', own[0]['printed'], stream=True)['tokens'])
            # In process, on the production reader: a result with no modelUsage (a shape 2.1.281 never prints,
            # so no fake engine prints it) leaves the tokens unknown, never zero and never the main loop's.
            meter, meter_error = attempt(lambda: L.ENGINES['claude_code'].Meter())
            final = None
            if meter is not None:
                bare = dict(c_result(12, 500, 1)['line'])
                del bare['modelUsage']
                meter.feed((json.dumps(c_msg('mu-bare', 12, 500)['line']) + '\n').encode())
                meter.feed((json.dumps(bare) + '\n').encode())
                final = meter.final()
            check('settle/model-usage', 'claude: a result without modelUsage settles its messages and leaves its '
                  'tokens unknown [%s, %s]' % (final, meter_error),
                  isinstance(final, dict) and 'tokens' not in final and final.get('messages') == 1)

        with region('settle/missing-retained'):
            for account, adapter, script in (('acct-c1', 'claude', [c_msg('m1', 70, 30)]),
                                             ('acct-x1', 'codex', [x_started()])):
                proj = project('p-missing-' + adapter, tokens=10 ** 6)
                launch, record = run(account, admitted('VELDO-6210-%s-a' % adapter, proj), adapter, script)
                call = invocation(launch.dispatch_id)
                nxt, nrecord = run(account, admitted('VELDO-6210-%s-b' % adapter, proj), adapter, ok(adapter))
                check('settle/missing-retained', '%s: no conclusive report leaves tokens and messages unknown, keeps '
                      'the invocation and what was seen, and refuses the next invocation [%s, %s, %s]'
                      % (adapter, call.get('state'), call.get('unknown'), (nrecord or {}).get('refusal')),
                      (record or {}).get('state') == 'exited' and call.get('state') == 'unknown'
                      and sorted(call.get('unknown') or []) == ['messages', 'tokens']
                      and call.get('charge', {}).get('invocations') == 1
                      and call.get('charge', {}).get('tokens', 0) == (100 if adapter == 'claude' else 0)
                      and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                      and not engine_markers(nxt.dispatch_id))

        with region('settle/timeout-retained'):
            for account, adapter in (('acct-c1', 'claude'), ('acct-x1', 'codex')):
                proj = project('p-timeout-' + adapter, tokens=10 ** 6, invocations=2)
                launch, record = run(account, admitted('VELDO-6211-%s-a' % adapter, proj), adapter,
                                     [{'sleep': 30}] + ok(adapter), deadline=3)
                call = invocation(launch.dispatch_id)
                nxt, nrecord = run(account, admitted('VELDO-6211-%s-b' % adapter, proj), adapter, ok(adapter))
                check('settle/timeout-retained', '%s: an accepted invocation stopped at its deadline keeps its '
                      'reservation, and the next invocation is refused [%s, %s, %s]'
                      % (adapter, call.get('outcome'), call.get('state'), (nrecord or {}).get('refusal')),
                      call.get('outcome') == 'timeout' and call.get('state') == 'unknown'
                      and call.get('charge', {}).get('invocations') == 1
                      and call.get('charge', {}).get('wall_seconds', 0) >= 2
                      and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                      and not engine_markers(nxt.dispatch_id)
                      and reservations.balances('project', proj)['invocations'] == 1)

        with region('settle/cancel-retained'):
            for account, adapter in (('acct-c1', 'claude'), ('acct-x1', 'codex')):
                proj = project('p-cancel-' + adapter, tokens=10 ** 6)
                launch, _ = run(account, admitted('VELDO-6212-%s-a' % adapter, proj), adapter,
                                [{'sleep': 30}] + ok(adapter), wait=False)
                marker_wait(launch.dispatch_id)
                launch.stop('owner')
                record = runner(account).wait(launch)
                call = invocation(launch.dispatch_id)
                nxt, nrecord = run(account, admitted('VELDO-6212-%s-b' % adapter, proj), adapter, ok(adapter))
                check('settle/cancel-retained', '%s: a cancelled invocation keeps its reservation, and the next '
                      'invocation is refused [%s, %s, %s]'
                      % (adapter, call.get('outcome'), call.get('state'), (nrecord or {}).get('refusal')),
                      call.get('outcome') == 'cancelled' and call.get('state') == 'unknown'
                      and call.get('charge', {}).get('invocations') == 1
                      and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                      and not engine_markers(nxt.dispatch_id))

        # AC4: usage and remaining allowance attributed to the stored account, project and unit.
        with region('attribution/stored-account'):
            ambient = dict(os.environ, VELDO_ACCOUNT='acct-c3', CLAUDE_CONFIG_DIR=profiles['acct-c3'],
                           CODEX_HOME=profiles['acct-x2'])
            journey = {}
            for account, adapter, script in (
                    ('acct-c1', 'claude', [c_init(), c_rate('allowed', time.time() + 3600, 'seven_day', 0.25),
                                           c_msg('j1', 11, 7), c_result(11, 7, 1)]),
                    ('acct-c2', 'claude', [c_init(), c_rate('allowed_warning', time.time() + 3600, 'seven_day', 0.5),
                                           c_msg('j2', 13, 5), c_result(13, 5, 1)]),
                    ('acct-x1', 'codex', [x_started(), x_done(17, 3)])):
                launch, record = run(account, admitted('VELDO-6213-' + account), adapter, script, env=ambient)
                journey[account] = launch.dispatch_id
            shown = usage_shown()
            truth = receipts_by_account()
            for account in ('acct-c1', 'acct-c2', 'acct-x1', 'acct-c3', 'acct-x2'):
                row = shown['account'].get(account) or {}
                totals = row.get('totals') or {}
                check('attribution/stored-account', '%s: the shown totals equal its stored receipts, grouped by the '
                      'account each dispatch recorded [%s vs %s]' % (account, totals, truth.get(account)),
                      {k: totals.get(k) for k in ('invocations', 'tokens', 'messages')}
                      == truth.get(account, {'invocations': 0, 'tokens': 0, 'messages': 0})
                      and totals.get('invocations', 0) == reservations.balances('account', account)['invocations']
                      and row.get('label') == account)
            for account, dispatch_id in journey.items():
                header = receipt_header(dispatch_id)
                recorded = ((rec(dispatch_id).get('contract') or {}).get('reservation') or {}).get('account')
                if account == 'acct-x1':
                    # `codex exec --json` reports no window while the allowance lasts: only the receipts.
                    check('attribution/stored-account', '%s: the receipts are attributed to the recorded account, not '
                          'the ambient label [%s]' % (account, header.get('account')),
                          header.get('account') == account == recorded)
                    continue
                stored = ((shown['account'].get(account) or {}).get('windows') or {}).get('seven_day') or {}
                check('attribution/stored-account', '%s: the receipts and the reported window are attributed to the '
                      'recorded account, not the ambient label [%s, %s]'
                      % (account, header.get('account'), stored.get('source_dispatch') == dispatch_id),
                      header.get('account') == account == recorded
                      and stored.get('source_dispatch') == dispatch_id and stored.get('status') == 'allowed')
            ambient_windows = [w for account in ('acct-c3', 'acct-x2')
                               for w in (account_record(account).get('windows') or {}).values()
                               if w.get('source_dispatch') in journey.values()]
            check('attribution/stored-account', 'no window of these runs reached the ambient accounts [%d]'
                  % len(ambient_windows), not ambient_windows)
            unit_rows = shown['unit']
            check('attribution/stored-account', 'each unit and the journey project show the same totals as their '
                  'receipts', all((unit_rows.get('VELDO-6213-' + a) or {}).get('totals', {}).get('tokens')
                                  == receipts_tokens(d) for a, d in journey.items())
                  and (shown['project'].get('journey') or {}).get('totals', {}).get('tokens')
                  == reservations.balances('project', 'journey')['tokens'])

        with region('attribution/measurement-removed'):
            unit = admitted('VELDO-6214-silent', tokens=500)
            launch, record = run('acct-c2', unit, 'claude', [])
            shown = usage_shown()
            row = shown['unit'].get(unit) or {}
            check('attribution/measurement-removed', 'an invocation that reported nothing keeps its allocation: one '
                  'invocation and its wall time shown, tokens and messages unknown and the token remainder unknown, '
                  'never counted as unused [%s]' % row,
                  (record or {}).get('state') == 'exited'
                  and (row.get('totals') or {}).get('invocations') == 1
                  and (row.get('totals') or {}).get('wall_seconds', 0) > 0
                  and row.get('unknown') == ['messages', 'tokens'] and row.get('open') == 1
                  and (row.get('remaining') or {}).get('tokens', 0) is None
                  and (row.get('remaining') or {}).get('invocations') == 19)

        with region('attribution/watermark'):
            shown = usage_shown()
            latest = {}
            for seq, command_id, transition in writer.execute('SELECT seq, command_id, transition FROM journal'):
                if not command_id.startswith('usage/'):
                    continue
                for identity, change in json.loads(transition).items():
                    data = change.get('data') or {}
                    if data.get('type') == 'invocation':
                        for scope in ('account', 'project', 'unit'):
                            key = (scope, data['context'][scope])
                            latest[key] = max(latest.get(key, 0), seq)
            compared = [(scope, subject, (shown[scope].get(subject) or {}).get('watermark'), seq)
                        for (scope, subject), seq in sorted(latest.items())]
            check('attribution/watermark', 'every account, project and unit shows as its watermark the journal '
                  'sequence of its latest recorded usage [%d subjects, %s]'
                  % (len(compared), [c for c in compared if c[2] != c[3]][:3]),
                  len(compared) > 20 and all(shown_seq == seq for _, _, shown_seq, seq in compared))

        # AC2, Codex's stated reset: refused inside it (above), the account takes work again once it passed.
        with region('usage/rate-limit-reset'):
            while limited['stated'] is not None and time.time() < limited['stated'] + 0.2:
                time.sleep(0.2)
            launch, record = run('acct-x2', admitted('VELDO-6208-acct-x2-c'), 'codex', ok('codex'))
            check('usage/rate-limit-reset', 'codex: once the stated reset passed the account takes work again [%s]'
                  % (record or {}).get('state'),
                  (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1)

        # The fixtures: every line a fake engine was scripted to print, checked against the format table
        # extract_formats.py read out of the installed binary. A CLI whose format moved (after the table
        # is regenerated) reds these rows, not a live run.
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

        def limit_pattern():
            pieces = {'%-I': r'\d{1,2}', '%M': r'\d{2}', '%p': '(?:AM|PM)', '%b': '[A-Z][a-z]{2}', '%-d': r'\d{1,2}',
                      '%Y': r'\d{4}', '{suffix}': '(?:%s)' % '|'.join(LIMIT['suffixes'])}
            clocks = []
            for spec in LIMIT['formats']:
                pattern = re.escape(spec)
                for key, value in pieces.items():
                    pattern = pattern.replace(re.escape(key), value)
                clocks.append(pattern)
            retry = '|'.join(re.escape(p) + '(?:%s)' % '|'.join(clocks) + r'\.' for p in LIMIT['retry_at'])
            later = '|'.join(re.escape(p) for p in LIMIT['retry_later'])
            return re.compile(re.escape(LIMIT['message']) + r'\.(?:%s|%s)$' % (retry, later))

        with region('format/claude-fake-lines', 'format/codex-fake-lines'):
            for engine, adapter, row, needed in (
                    ('claude_code', 'claude', 'format/claude-fake-lines', ('assistant', 'result/success', 'rate_limit_event')),
                    ('codex', 'codex', 'format/codex-fake-lines', ('turn.completed', 'turn.failed', 'error'))):
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
                check(row, '%s: every one of the %d lines the fake was scripted to print conforms to the format the '
                      'installed binary %s (%s) declares [%s]' % (engine, len(lines), table.get('version'),
                                                                 table.get('sha256', '')[:19], problems[:4]),
                      len(lines) > 20 and not problems)
                kinds = {event_name(engine, line) for line in lines}
                check(row, '%s: the fixtures print every event the reader settles from, and the table has each [%s]'
                      % (engine, sorted(set(needed) - kinds - set(events))), set(needed) <= kinds and set(needed) <= set(events))
            limit_lines = [line for owner, line in fixture_lines if owner == 'codex' and line.get('type') in ('error', 'turn.failed')]
            messages = [line.get('message') or (line.get('error') or {}).get('message') for line in limit_lines]
            pattern = limit_pattern()
            check('format/codex-fake-lines', 'codex: each usage-limit message the fake prints is built from the binary\'s '
                  'own message, retry phrases and time formats [%s]' % [m for m in messages if not pattern.match(m or '')][:2],
                  len(messages) >= 4 and all(pattern.match(m or '') for m in messages)
                  and any('again at' in m for m in messages) and any('later' in m for m in messages))
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
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
                    print('  VELDO-0062 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0062 %s detail: no check ran' % name)
        expect('VELDO-0062 ' + name, ok)
    print('VELDO-0062 suite seconds: %.3f' % (time.monotonic() - started))


_v62_suite()
