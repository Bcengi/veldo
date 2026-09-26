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
    ROWS = ('login/recorded-account-profile', 'login/no-paid-api', 'login/configured-environment',
            'login/substitution-refused', 'login/fleet-provider',
            'usage/reserved-before-launch', 'usage/allowance-states', 'usage/competing-remainder',
            'usage/cap-stops-worker', 'usage/rate-limit-reset',
            'settle/once', 'settle/model-usage', 'settle/resumed-delta', 'settle/resumed-other-session',
            'settle/missing-retained', 'settle/timeout-retained',
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
        # x2 to x5 each take one Codex limit observation: a future stated reset, none stated, a stated
        # minute that already ended, and a workspace out of credits.
        REGISTERED = [('acct-c1', 'claude_code'), ('acct-c2', 'claude_code'), ('acct-c3', 'claude_code'),
                      ('acct-x1', 'codex'), ('acct-x2', 'codex'), ('acct-x3', 'codex'), ('acct-x4', 'codex'),
                      ('acct-x5', 'codex')]
        for account, provider in REGISTERED:
            register(account, provider)
        register('acct-paused', 'claude_code', status='paused')
        register('acct-mac', 'claude_code', hosts=['mac-host-62'])
        REGISTERED += [('acct-paused', 'claude_code'), ('acct-mac', 'claude_code')]
        ALL = tuple(a for a, _ in REGISTERED) + ('acct-none',)

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
        # The login variables planted in the caller's environment: every name of every list the binaries
        # hold (from the extracted table, never from production), each with the outcome its list decides,
        # the names the reviews found passing, and a probe of every stripped family a later CLI could add a
        # name to. From what the engine inherits, a list's login and setting names and every family name are
        # stripped; its kept names (general proxy, CA, runtime, cloud, tool credentials, the names the binary
        # says are not secrets) reach the engine, as does a name no list or family covers.
        FAMILY = ('ANTHROPIC_', 'OPENAI_', 'CODEX_', 'CLAUDE_CODE_USE_')
        PROFILE_VARS = ('CLAUDE_CONFIG_DIR', 'CODEX_HOME')
        HOME_NAMES = ('HOME', 'XDG_CONFIG_HOME', 'APPDATA', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'PROGRAMDATA')

        def decisions():
            """Each listed name's decision over every list: strip over setting over model over keep."""
            rank = {'keep': 0, 'model': 1, 'setting': 2, 'strip': 3}
            found = {}
            for engine in ('claude_code', 'codex'):
                for table in FORMATS[engine]['credential_tables']:
                    for name in table['names']:
                        decision = ((table.get('exceptions') or {}).get(name) or {}).get('decision', table['decision'])
                        if name not in found or rank[decision] > rank[found[name]]:
                            found[name] = decision
            return found
        DECIDED = decisions()
        LISTED = sorted(DECIDED)
        TABLED = sorted(n for n, d in DECIDED.items() if d == 'strip')
        LOGINS = TABLED
        SETTINGS_LISTED = sorted(n for n, d in DECIDED.items() if d == 'setting')
        MODEL_LISTED = sorted(n for n, d in DECIDED.items() if d == 'model')
        NINE = ['CODEX_ACCESS_TOKEN', 'CLAUDE_CODE_USE_ANTHROPIC_AWS', 'ANTHROPIC_AWS_API_KEY', 'CLAUDE_CODE_USE_GATEWAY',
                'CLAUDE_CODE_USE_MANTLE', 'CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD', 'ANTHROPIC_FOUNDRY_AUTH_TOKEN',
                'CLAUDE_CODE_OAUTH_REFRESH_TOKEN', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN']
        # The third review's: redirects of the OAuth store, host credentials, settings, API and bridge.
        REDIRECTS = ['CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_HOST_CREDS_FILE', 'CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST',
                     'CLAUDE_CODE_MANAGED_SETTINGS_PATH', 'CLAUDE_CODE_REMOTE_SETTINGS_PATH', 'CLAUDE_CODE_API_BASE_URL',
                     'USE_STAGING_OAUTH', 'USE_LOCAL_OAUTH', 'CLAUDE_BRIDGE_BASE_URL', 'CLAUDE_CODE_FEDERATION_CACHE_DIR',
                     'CLAUDE_BG_SOCKET_TOKENS_PATH']
        probe = os.urandom(3).hex().upper()
        FAMILIES = ['ANTHROPIC_V62_' + probe, 'OPENAI_V62_' + probe, 'CODEX_V62_' + probe, 'CLAUDE_CODE_USE_V62_' + probe]

        def inherited_outcome(name):
            if name in PROFILE_VARS or name.startswith(FAMILY) or DECIDED.get(name) in ('strip', 'setting'):
                return 'strip'
            return 'keep'
        STRIPPED = sorted({n for n in LISTED if inherited_outcome(n) == 'strip'} | set(NINE) | set(REDIRECTS)
                          | set(FAMILIES))
        # Kept, planted: every kept listed name but the home names (the receiver's own tools need the real
        # ones; they are checked to arrive unchanged), a neutral name, count and threshold settings.
        KEPT = sorted({n for n in LISTED if inherited_outcome(n) == 'keep' and n not in HOME_NAMES}
                      | {'V62_NEUTRAL_' + probe, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS'})
        # What the Claude adapter configures: the model table, the settings and a threshold setting, each of
        # which must reach the engine with its configured value; the Codex adapter a setting of its family.
        CONFIGURED_CLAUDE = sorted(set(MODEL_LISTED) | set(SETTINGS_LISTED) | {'CLAUDE_CODE_IDLE_TOKEN_THRESHOLD'})
        CONFIGURED_CODEX = ['CODEX_CA_CERTIFICATE', 'RUST_LOG']
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
       'env': {k: os.environ.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'VELDO_ACCOUNT')},
       'values': dict(os.environ)}
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
                           'environment': {name: plant('adapter-' + name.lower()) for name in CONFIGURED_CLAUDE},
                           'argv': wrapper + [str(engines / 'claude'), str(db), str(markers), DOMAIN]},
                'codex': {'identity': 'reported', 'engine': 'codex',
                          'environment': {name: plant('adapter-' + name.lower()) for name in CONFIGURED_CODEX},
                          'argv': wrapper + [str(engines / 'codex'), str(db), str(markers), DOMAIN]},
                # Adapters configuring a login: refused by name when the configuration is loaded.
                'claude-api-key': {'identity': 'reported', 'engine': 'claude_code',
                                   'environment': {'ANTHROPIC_MODEL': 'configured-model',
                                                   'ANTHROPIC_API_KEY': plant('adapter-anthropic')},
                                   'argv': wrapper + [str(engines / 'claude'), str(db), str(markers), DOMAIN]},
                'claude-oauth-store': {'identity': 'reported', 'engine': 'claude_code',
                                       'environment': {'CLAUDE_SECURESTORAGE_CONFIG_DIR': str(base / 'elsewhere')},
                                       'argv': wrapper + [str(engines / 'claude'), str(db), str(markers), DOMAIN]},
                'codex-endpoint': {'identity': 'reported', 'engine': 'codex',
                                   'environment': {'OPENAI_BASE_URL': 'http://127.0.0.1:9/v1'},
                                   'argv': wrapper + [str(engines / 'codex'), str(db), str(markers), DOMAIN]}}}))
        CONFIGURED = json.loads(config.read_text())['adapters']
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

        def job(adapter, script, code=0, deadline=40, resume=None, thread=None):
            if adapter.startswith('codex'):
                # `codex exec --json` opens every stream with its thread (a resumed one with the thread it resumes).
                script = [x_thread(thread or (resume if resume else None))] + list(script)
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

        def c_running(lines):
            """The running total the latest result in these Claude Code lines states (modelUsage over every
            model), or None without one."""
            found = None
            for line in lines:
                event = json.loads(line)
                models = event.get('modelUsage') if event.get('type') == 'result' else None
                if isinstance(models, dict):
                    total = sum(m.get(k) or 0 for m in models.values() for k in (
                        'inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens'))
                    found = total if found is None else max(found, total)
            return found

        def own_tokens(dispatch_id):
            """This suite's reading of what one stored receipt charges: its recomputed total, except that a
            Claude Code invocation resuming a session (its contract's `resume`) whose own lines report that
            session is charged its result's running total less the running total of the latest earlier receipt
            of that session; with no such earlier total, or a running total below it, only what its own messages
            streamed. One whose lines report another session is charged its whole recomputed total."""
            header, lines = receipt_read(dispatch_id)
            found = recompute(header['provider'], lines)
            resume = (((rec(dispatch_id).get('contract') or {}).get('input') or {}).get('payload') or {}).get('resume')
            reported = [json.loads(line).get('session_id') for line in lines if json.loads(line).get('session_id')]
            if header['provider'] != 'claude_code' or not resume or (reported[-1] if reported else None) != resume:
                return found['tokens']
            order = invocation(dispatch_id).get('accepted_seq')
            earlier = []
            # An invocation the ledger never accepted cannot be placed after an earlier one: only its own messages.
            for path in (receipts.glob('*.jsonl') if order is not None else ()):
                raw = path.read_bytes().split(b'\n')
                other, other_lines = json.loads(raw[0]), [line for line in raw[1:] if line]
                if other['provider'] != 'claude_code' or other['dispatch_id'] == dispatch_id:
                    continue
                if (invocation(other['dispatch_id']).get('accepted_seq') or 0) >= order:
                    continue
                if any(json.loads(line).get('session_id') == resume for line in other_lines):
                    earlier.append((invocation(other['dispatch_id']).get('accepted_seq') or 0, c_running(other_lines)))
            prior = max(earlier)[1] if earlier else None
            running = c_running(lines)
            streamed = recompute('claude_code', [line for line in lines if json.loads(line).get('type') == 'assistant'])
            if prior is None or running is None or running < prior:
                return streamed['tokens']
            return max(streamed['tokens'], running - prior)

        def receipts_by_account():
            totals = {}
            for path in sorted(receipts.glob('*.jsonl')):
                raw = path.read_bytes().split(b'\n')
                header = json.loads(raw[0])
                account = ((rec(header['dispatch_id']).get('contract') or {}).get('reservation') or {}).get('account')
                found = recompute(header['provider'], [line for line in raw[1:] if line])
                total = totals.setdefault(account, {'invocations': 0, 'tokens': 0, 'messages': 0})
                total['invocations'] += 1
                total['tokens'] += own_tokens(header['dispatch_id'])
                total['messages'] += found['messages']
            return totals

        def receipts_tokens(dispatch_id):
            header, lines = receipt_read(dispatch_id)
            return own_tokens(dispatch_id) if header else None

        # Stream lines in the shapes the installed CLIs print (the format rows check each one against
        # the table extracted from the binaries). Claude Code 2.1.281's stream JSON:
        SESSION = 'session-62-' + os.urandom(4).hex()

        def c_usage(inp, out, read=0, create=0):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': create,
                    'cache_read_input_tokens': read,
                    'cache_creation': {'ephemeral_5m_input_tokens': create, 'ephemeral_1h_input_tokens': 0},
                    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}, 'service_tier': 'standard'}

        def c_init(session=None):
            return {'line': {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'claude_code_version': '2.1.281',
                             'cwd': '/work', 'tools': ['Read', 'Edit', 'Bash'],
                             'mcp_servers': [{'name': 'tracker', 'status': 'connected'}], 'model': 'configured-model',
                             'permissionMode': 'default', 'slash_commands': [], 'output_style': 'default', 'skills': [],
                             'plugins': [], 'uuid': str(uuid.uuid4()), 'session_id': session or SESSION}}

        def c_msg(mid, inp, out, read=0, create=0, parent=None, session=None):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': parent, 'uuid': str(uuid.uuid4()),
                             'session_id': session or SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'configured-model',
                                         'content': [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out, read, create)}}}

        def c_result(inp, out, turns, cache=0, models=None, main=None, session=None):
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
                'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session or SESSION}}

        def c_rate(status, reset, kind='five_hour', utilization=None):
            info = {'status': status, 'rateLimitType': kind}
            if reset is not None:
                info['resetsAt'] = int(reset)
            if utilization is not None:
                info['utilization'] = utilization
            return {'line': {'type': 'rate_limit_event', 'rate_limit_info': info, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION}}

        # Codex 0.154.0's exec JSON and its usage-limit message.
        def x_thread(thread=None):
            return {'line': {'type': 'thread.started', 'thread_id': thread or 'thread-62-' + os.urandom(4).hex()}}

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

        def x_clock(stated, zone=None, now=None):
            """The local time Codex states for a reset: the minute `stated` in `zone` (this process's own zone
            when None, which the engine inherits), with the date when it is not the day of `now`."""
            import datetime
            import zoneinfo
            tz = zoneinfo.ZoneInfo(zone) if zone else None
            at = datetime.datetime.fromtimestamp(stated, tz) if tz else datetime.datetime.fromtimestamp(stated)
            today = (datetime.datetime.fromtimestamp(now if now is not None else time.time(), tz) if tz
                     else datetime.datetime.fromtimestamp(now if now is not None else time.time()))
            clock = '%d:%02d %s' % (at.hour % 12 or 12, at.minute, 'AM' if at.hour < 12 else 'PM')
            if at.date() != today.date():
                day = at.day
                suffix = 'th' if 11 <= day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                clock = '%s %d%s, %d %s' % (('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                                  'Dec')[at.month - 1], day, suffix, at.year, clock)
            return clock

        def x_limit_message(stated, zone=None, now=None):
            """The usage-limit message Codex prints, from the binary's own pieces: the minute `stated` as its
            reset (in the engine's local time, or `zone`), or none."""
            if stated is None:
                return LIMIT['message'] + '.' + LIMIT['retry_later'][0]
            return LIMIT['message'] + '.' + LIMIT['retry_at'][0] + x_clock(stated, zone, now) + '.'

        def ok(adapter, inp=1, out=1):
            """A normal, complete report of one small invocation, in the adapter's own format."""
            return [c_result(inp, out, 1)] if adapter.startswith('claude') else [x_started(), x_done(inp, out)]

        # AC1: the login of the account the dispatch recorded, never the caller's; no paid API.
        with region('login/recorded-account-profile', 'login/no-paid-api', 'login/configured-environment'):
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
                values = own.get('values') or {}
                adapter = 'codex' if account.startswith('acct-x') else 'claude'
                wanted = CONFIGURED[adapter]['environment']
                # A name the adapter configures arrives with the configured value, and the account's own profile
                # variable with its profile (the rows above), never with the caller's.
                leaked = sorted(n for n in set(STRIPPED) & names
                                if (n not in wanted and n not in PROFILE_VARS) or values.get(n) == caller[n])
                check('login/no-paid-api', '%s: no login variable reached the engine: none of the %d names the '
                      'binaries\' lists strip, the redirects and names the reviews found, or the family probes, all '
                      'planted in the caller\'s environment [%s]' % (account, len(STRIPPED), leaked[:12]),
                      bool(names) and not leaked)
                missing = sorted(n for n in KEPT if n not in wanted and values.get(n) != caller[n])
                homes = sorted(n for n in HOME_NAMES if n in os.environ and values.get(n) != os.environ[n])
                check('login/no-paid-api', '%s: what is not a login still reached it unchanged: the %d kept names of '
                      'the lists (general proxy, CA, runtime, cloud, tool credentials, the not-secret thresholds and '
                      'usage settings), a neutral name, a count setting and the home names [%s, %s]'
                      % (account, len(KEPT), missing[:8], homes), bool(names) and not missing and not homes)
                dropped = sorted(n for n, v in wanted.items() if values.get(n) != v)
                check('login/configured-environment', '%s: every name its adapter configures reached the engine with '
                      'its configured value, though the same names were planted otherwise in the caller\'s: %s [%s]'
                      % (account, 'the model table, the settings and a threshold' if adapter == 'claude'
                         else 'a setting of its family and a neutral one', dropped[:8]),
                      bool(values) and not dropped and len(wanted) >= (25 if adapter == 'claude' else 2))
            check('login/recorded-account-profile', 'the two Claude Code accounts ran on two different profiles',
                  (seen['acct-c1'][2].get('env') or {}).get('CLAUDE_CONFIG_DIR')
                  != (seen['acct-c2'][2].get('env') or {}).get('CLAUDE_CONFIG_DIR'))
            check('login/recorded-account-profile', 'the owner registered every account [%s]'
                  % [r for r in registered if r[1]], len(registered) == len(REGISTERED) and not [r for r in registered if r[1]])
            lists = {t['name'] for e in ('claude_code', 'codex') for t in FORMATS[e]['credential_tables']}
            check('login/no-paid-api', 'every name of every extracted list, the nine, the redirects and the probes '
                  'were planted [%d listed in %d lists, %d stripped, %d kept]' % (len(LISTED), len(lists), len(STRIPPED),
                                                                                len(KEPT)),
                  {'sensitive_env', 'fd_tokens', 'session_secrets', 'host_creds_env', 'not_secrets', 'model_config',
                   'auth_endpoint', 'sqlite_home'} <= lists and len(TABLED) >= 130
                  and set(NINE) | set(REDIRECTS) <= set(TABLED)
                  and set(LISTED) - set(HOME_NAMES) <= set(STRIPPED) | set(KEPT)
                  and all(caller.get(name) for name in STRIPPED + KEPT))

        # AC1, the adapter's configuration: never silently reduced; a login in it refused by name.
        with region('login/configured-environment'):
            for adapter, account, name in (('claude-api-key', 'acct-c1', 'ANTHROPIC_API_KEY'),
                                           ('claude-oauth-store', 'acct-c1', 'CLAUDE_SECURESTORAGE_CONFIG_DIR'),
                                           ('codex-endpoint', 'acct-x1', 'OPENAI_BASE_URL')):
                launch, record = run(account, admitted('VELDO-6216-' + adapter), adapter, ok(adapter))
                check('login/configured-environment', '%s configures %s: refused by name when its configuration is '
                      'loaded, nothing launched or reserved [%s]' % (adapter, name, (record or {}).get('refusal')),
                      (record or {}).get('refusal') == 'invalid_input:adapter_environment:' + name
                      and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id)
                      and not invocation(launch.dispatch_id))
            # The production refusal over every listed name: each login is refused, nothing else is.
            credentials = getattr(L, 'CREDENTIALS', None)
            logins = sorted(set(LOGINS) | set(REDIRECTS) | set(NINE))
            passed = [n for n in logins if not attempt(lambda: ACC.refused({n: 'x'}, credentials))[0]]
            others = sorted(set(MODEL_LISTED) | set(SETTINGS_LISTED) | set(KEPT) | {'CODEX_CA_CERTIFICATE'})
            blocked = [n for n in others if attempt(lambda: ACC.refused({n: 'x'}, credentials))[0]]
            check('login/configured-environment', 'configured, each of the %d login names of the lists is refused '
                  'and none of the %d model, setting or kept names is [%s, %s]' % (len(logins), len(others), passed[:6],
                                                                                   blocked[:6]),
                  len(logins) >= 130 and not passed and not blocked and set(MODEL_LISTED) <= set(others))

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
            codex_profiles = {profiles[a] for a, provider in REGISTERED if provider == 'codex'}
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
            for account, adapter in (('acct-c1', 'claude'), ('acct-x1', 'codex')):
                unit = admitted('VELDO-6204-' + adapter, invocations=3)
                first = 'session-62-first-' + os.urandom(4).hex()
                # The follow-on resumes the initial invocation's session, and prints the running total the
                # real CLI prints for it: the earlier turns' 3 tokens and its own 3.
                scripts = {
                    'claude': {'initial': [c_result(2, 1, 1, session=first)], 'retry': [c_result(2, 1, 1)],
                               'follow_on': [c_result(4, 2, 1, session=first)]},
                    'codex': {'initial': [x_started(), x_done(2, 1)], 'retry': [x_started(), x_done(2, 1)],
                              'follow_on': [x_started(), x_done(2, 1)]}}[adapter]
                for boundary, resume in (('initial', None), ('retry', None), ('follow_on', first)):
                    script = scripts[boundary]
                    launch, record = run(account, unit, adapter, script, resume=resume,
                                         thread=first if boundary == 'initial' else None)
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
                launch, record = run(account, unit, adapter, script, resume=first)
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
            # Claude Code: a reported window whose reset is an hour away refuses its account; at the pure seams
            # that take a clock, one second before the reset is refused and the reset itself is allowed.
            now = int(time.time())
            reset = now + 3600
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
                  and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id))
            before, _ = attempt(lambda: ACC.blocking(account_record('acct-c3'), reset - 1))
            at, _ = attempt(lambda: ACC.blocking(account_record('acct-c3'), reset))
            seam_unit = admitted('VELDO-6208-claude-seam')
            context = dict(domain=DOMAIN, repository=REPOSITORY, account='acct-c3', project='journey', unit=seam_unit)
            _, check_before = attempt(lambda: reservations._check(context, {'invocations': 1}, reservations._records(),
                                                                  reset - 1))
            _, check_at = attempt(lambda: reservations._check(context, {'invocations': 1}, reservations._records(),
                                                              reset))
            check('usage/rate-limit-reset', 'claude: the account record and the reservation check refuse one second '
                  'before the reported reset and allow at it [%s, %s, %s, %s]' % (before, at, check_before, check_at),
                  before == ['five_hour'] and at == [] and check_before == 'rate_limited:five_hour' and check_at is None)
            # Another account whose reported reset already ended takes work.
            launch, record = run('acct-c2', admitted('VELDO-6208-claude-c'), 'claude',
                                 [c_rate('rejected', now - 60, 'five_hour', 1.0), c_result(1, 1, 1)])
            launch, record = run('acct-c2', admitted('VELDO-6208-claude-d'), 'claude', ok('claude'))
            check('usage/rate-limit-reset', 'claude: an account whose reported reset already ended takes work [%s, %s]'
                  % ((account_record('acct-c2').get('windows') or {}).get('five_hour'), (record or {}).get('state')),
                  ((account_record('acct-c2').get('windows') or {}).get('five_hour') or {}).get('reset_at') == now - 60
                  and (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1)

            # Codex, on the production reader with a fixed clock and zone: the stated minute's end is the reset
            # (the same local minute in another zone is another instant), refused a second before it, allowed at it.
            X = getattr(L, 'ENGINES', {}).get('codex')  # absent before the change: the rows red by assertion
            fixed = 1790000000
            for zone in ('UTC', 'America/New_York', 'Asia/Kolkata'):
                for stated in (fixed // 60 * 60 + 7200, fixed // 60 * 60 + 3 * 86400):
                    message = x_limit_message(stated, zone, fixed)
                    meter, _ = attempt(lambda: X.Meter(clock=lambda: fixed, zone=zone))
                    seen = [o for o in (meter.feed((json.dumps(x_error(message)['line']) + '\n').encode()) if meter
                                        else []) if o['kind'] == 'window']
                    direct, _ = attempt(lambda: X.limit_reset(message, fixed, zone))
                    window = dict(status='rejected', reset_at=(seen[0]['reset_at'] if seen else None))
                    record = {'windows': {'usage_limit': window}}
                    check('usage/rate-limit-reset', 'codex, %s, "%s": the reset is the end of the stated minute, '
                          'refused one second before it and allowed at it [%s, %s]' % (zone, message[-24:], direct,
                                                                                    window['reset_at']),
                          len(seen) == 1 and seen[0]['window_id'] == 'usage_limit' and direct == stated + 60
                          == window['reset_at'] and attempt(lambda: ACC.blocking(record, stated + 59))[0] == ['usage_limit']
                          and attempt(lambda: ACC.blocking(record, stated + 60))[0] == [])
            # Every message of the binary's error table, on the production reader: each exhaustion is its window,
            # the usage-limit forms with the reset their retry phrase states or none, the rest with none; nothing
            # else in the table records a window.
            ERRORS = FORMATS['codex']['errors']

            def filled(entry, retry):
                text = entry['message']
                if entry['window'] == 'usage_limit':
                    pieces = text.split('{}')
                    # the model or plan sentence, then the retry phrase as the last argument
                    return ''.join(p + ('configured-model' if i < len(pieces) - 2 else retry if i == len(pieces) - 2
                                        else '') for i, p in enumerate(pieces))
                return text.replace('{}', 'x')
            misread = []
            for entry in ERRORS:
                retries = ((LIMIT['retry_at'][1] + x_clock(fixed // 60 * 60 + 600, 'UTC', fixed) + '.',
                            fixed // 60 * 60 + 660), (LIMIT['retry_later'][1], None)) \
                    if entry['window'] == 'usage_limit' else (('', None),)
                for retry, expected in retries:
                    if entry['window'] == 'usage_limit' and not entry['message'].rsplit('{}', 2)[-2].endswith(','):
                        retry = retry.replace(' or try', ' Try')  # after a full stop the phrase opens a sentence
                    message = filled(entry, retry)
                    windows, failure = attempt(lambda: [
                        o for meter in [X.Meter(clock=lambda: fixed, zone='UTC')] for chunk in (x_error(message), x_failed(message))
                        for o in meter.feed((json.dumps(chunk['line']) + '\n').encode()) if o['kind'] == 'window'])
                    windows = windows or []
                    wanted = [] if entry['window'] is None else [(entry['window'], 'rejected', expected)]
                    got = [(o['window_id'], o['status'], o['reset_at']) for o in windows]
                    if got != wanted or failure:
                        misread.append((message[:60], got, wanted, failure))
            exhaustions = [e for e in ERRORS if e['window']]
            check('usage/rate-limit-reset', 'codex: every one of the %d messages of the binary\'s error table is read as '
                  'its window or as none, the %d exhaustions each once, with the reset stated or none [%s]'
                  % (len(ERRORS), len(exhaustions), misread[:3]),
                  len(ERRORS) >= 40 and {'usage_limit', 'workspace_credits', 'workspace_spend_cap', 'quota', 'plan'}
                  == {e['window'] for e in exhaustions} and not misread)
            # End to end, no wait: a stated minute two hours away refuses its account; none stated keeps its account
            # refused however long; a stated minute that already ended lets its account take work; a workspace out
            # of credits refuses its account with no reset.
            now = int(time.time())
            future = now // 60 * 60 + 7200
            past = now // 60 * 60 - 60
            credits = next(e['message'] for e in ERRORS if e['window'] == 'workspace_credits')
            for account, message, window, expected in (
                    ('acct-x2', x_limit_message(future), 'usage_limit', future + 60),
                    ('acct-x3', x_limit_message(None), 'usage_limit', None),
                    ('acct-x4', x_limit_message(past), 'usage_limit', past + 60),
                    ('acct-x5', credits, 'workspace_credits', None)):
                launch, record = run(account, admitted('VELDO-6208-%s-a' % account), 'codex',
                                     [x_started(), x_error(message), x_failed(message)], code=1)
                stored = (account_record(account).get('windows') or {}).get(window) or {}
                check('usage/rate-limit-reset', 'codex %s: "%s" is recorded on the account as the exhausted %s window, '
                      'its reset %s, from its dispatch [%s]' % (account, message[-32:], window, expected, stored),
                      stored.get('status') == 'rejected' and stored.get('reset_at') == expected
                      and stored.get('source_dispatch') == launch.dispatch_id)
                launch, record = run(account, admitted('VELDO-6208-%s-b' % account), 'codex', ok('codex'))
                if account == 'acct-x4':
                    check('usage/rate-limit-reset', 'codex acct-x4: its stated minute already ended, so it takes work '
                          '[%s]' % (record or {}).get('state'),
                          (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1)
                    continue
                check('usage/rate-limit-reset', 'codex %s: a new invocation is refused by name and nothing launches '
                      '[%s]' % (account, (record or {}).get('refusal')),
                      (record or {}).get('refusal') == 'missing_authority:allowance:rate_limited:' + window
                      and not engine_markers(launch.dispatch_id) and not spawned(launch.dispatch_id))
                if expected is None:
                    blocked, _ = attempt(lambda: ACC.blocking(account_record(account), time.time() + 10 ** 7))
                    check('usage/rate-limit-reset', 'codex %s: with no reset stated the account stays refused however '
                          'long, until a later observation says otherwise [%s]' % (account, blocked), blocked == [window])

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
                    receipts=last.get('receipts', ()), now=time.time(),
                    **({'session': last['session']} if 'session' in last else {})))
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

        # A resumed session's first result carries the earlier turns: only the difference is charged.
        with region('settle/resumed-delta'):
            def settle_run(account, unit, script, resume=None, thread=None, adapter='claude'):
                launch, record = run(account, unit, adapter, script, resume=resume, thread=thread)
                return launch, invocation(launch.dispatch_id)
            opus = 'claude-opus-4-7'
            chain = 'session-62-chain-' + os.urandom(4).hex()
            unit = admitted('VELDO-6217-chain')
            calls = []
            for resume, own, running in ((None, (10, 200, 3000, 400), (10, 200, 3000, 400)),
                                         (chain, (5, 100, 1500, 0), (15, 300, 4500, 400)),
                                         (chain, (1, 10, 0, 0), (16, 310, 4500, 400))):
                mid = 'chain-%d' % len(calls)
                launch, call = settle_run('acct-c1', unit, [c_init(session=chain),
                                                            c_msg(mid, *own, session=chain),
                                                            c_result(*running[:2], 1, models={opus: running},
                                                                     session=chain)], resume=resume)
                calls.append((launch, call, sum(own), sum(running)))
            charged = [c.get('charge', {}).get('tokens') for _, c, _, _ in calls]
            check('settle/resumed-delta', 'claude: a session and two follow-ons resuming it, each printing the running '
                  'total the CLI prints, are charged their own share, not the running total [%s charged, %s own, %s '
                  'running]' % (charged, [o for _, _, o, _ in calls], [r for _, _, _, r in calls]),
                  charged == [3610, 1605, 11] and all(c.get('state') == 'settled' for _, c, _, _ in calls)
                  and reservations.balances('unit', unit)['tokens'] == calls[-1][3] == 5226)
            settled = reservations.session('claude_code', chain) if hasattr(reservations, 'session') else None
            check('settle/resumed-delta', 'claude: the ledger settles the session with the running total of the last '
                  'invocation that ran it, read back by session id [%s]' % settled,
                  (settled or {}).get('tokens') == 5226
                  and (settled or {}).get('invocation') == 'invocation/' + calls[-1][0].dispatch_id)
            # An earlier total that is unknown makes this one unknown, never the whole total: a session no
            # invocation settled, one settled without a running total, and a running total below the settled one.
            fresh = 'session-62-fresh-' + os.urandom(4).hex()
            silent = 'session-62-silent-' + os.urandom(4).hex()
            low = 'session-62-low-' + os.urandom(4).hex()
            proj = project('p-resume-unknown')
            settle_run('acct-c1', admitted('VELDO-6217-silent-a', proj), [c_init(session=silent),
                                                                        c_msg('silent-a', 7, 3, session=silent)])
            settle_run('acct-c1', admitted('VELDO-6217-low-a', proj), [c_init(session=low),
                                                                     c_result(10, 200, 1, models={opus: (10, 200, 3000, 400)},
                                                                              session=low)])
            for label, session in (('a session no invocation settled', fresh),
                                   ('a session settled without a running total', silent),
                                   ('a running total below the settled one', low)):
                running = (1, 1, 1000, 0) if session == low else (40, 60, 9000, 0)
                launch, call = settle_run('acct-c1', admitted('VELDO-6217-%s-b' % session[11:16], proj),
                                          [c_init(session=session), c_msg(session + '-b', 3, 4, session=session),
                                           c_result(*running[:2], 1, models={opus: running}, session=session)],
                                          resume=session)
                check('settle/resumed-delta', 'claude: resuming %s leaves the tokens unknown and keeps what its own '
                      'messages streamed, never the whole running total [%s, %s, %s]'
                      % (label, call.get('state'), call.get('unknown'), call.get('charge', {}).get('tokens')),
                      call.get('state') == 'unknown' and call.get('unknown') == ['tokens']
                      and call.get('charge', {}).get('tokens') == 7 and call.get('charge', {}).get('messages') == 1)
            # Codex: the binary does not say whether turn.completed is the thread's total; a resumed thread is
            # charged the sum its own completed turns report, never less.
            thread = 'thread-62-chain-' + os.urandom(4).hex()
            unit = admitted('VELDO-6217-codex')
            first_launch, first_call = settle_run('acct-x1', unit, [x_started(), x_done(100, 50)], thread=thread,
                                                  adapter='codex')
            launch, call = settle_run('acct-x1', unit, [x_started(), x_done(120, 60)], resume=thread, adapter='codex')
            check('settle/resumed-delta', 'codex: a follow-on resuming a thread is charged what its own completed turn '
                  'reports, never less [%s, %s]' % (first_call.get('charge', {}).get('tokens'),
                                                    call.get('charge', {}).get('tokens')),
                  first_call.get('charge', {}).get('tokens') == 150 and call.get('state') == 'settled'
                  and call.get('charge', {}).get('tokens') == 180)

        # The contract resumes session S (settled 1000), but the CLI reports a fresh session N with 5000: the
        # difference is taken only when the CLI reports the resumed session, so N's whole total is charged.
        with region('settle/resumed-other-session'):
            opus = 'claude-opus-4-7'
            named = 'session-62-named-' + os.urandom(4).hex()
            other = 'session-62-other-' + os.urandom(4).hex()
            unit = admitted('VELDO-6218-other')
            first, _ = run('acct-c1', unit, 'claude', [c_init(session=named), c_msg('named-a', 1, 1, session=named),
                                                        c_result(1, 1, 1, models={opus: (400, 600, 0, 0)}, session=named)])
            first_call = invocation(first.dispatch_id)
            launch, _ = run('acct-c1', unit, 'claude', [c_init(session=other), c_msg('other-a', 2, 3, session=other),
                                                         c_result(2, 3, 1, models={opus: (2000, 3000, 0, 0)}, session=other)],
                            resume=named)
            call = invocation(launch.dispatch_id)
            check('settle/resumed-other-session', 'claude: a follow-on whose contract resumes %s (settled %s) but whose '
                  'CLI reports another session with a running total of 5000 is charged all 5000, not the difference '
                  '[%s charged, %s]' % ('the named session', first_call.get('charge', {}).get('tokens'),
                                        call.get('charge', {}).get('tokens'), call.get('state')),
                  first_call.get('charge', {}).get('tokens') == 1000 and call.get('state') == 'settled'
                  and call.get('charge', {}).get('tokens') == 5000)
            recorded = call.get('session') or {}
            untouched = (reservations.session('claude_code', named) or {}).get('tokens')
            # The named session resumed again, now reported by the CLI: the difference, 1200 less 1000.
            again, _ = run('acct-c1', unit, 'claude', [c_init(session=named), c_msg('named-b', 1, 1, session=named),
                                                        c_result(1, 1, 1, models={opus: (500, 700, 0, 0)}, session=named)],
                           resume=named)
            matched = invocation(again.dispatch_id)
            check('settle/resumed-other-session', 'claude: the ledger records which case charged each invocation: the '
                  'other session whole as another session than the one resumed, the named session\'s settled total '
                  'untouched by it, a resumption the CLI reports as the named session as the difference, and the '
                  'initial invocation as whole [%s; %s; %s; %s charged %s]'
                  % (recorded, untouched, first_call.get('session'), matched.get('session'),
                     matched.get('charge', {}).get('tokens')),
                  recorded.get('id') == other and recorded.get('tokens') == 5000
                  and recorded.get('charged') == 'whole_other_session' and untouched == 1000
                  and (first_call.get('session') or {}).get('charged') == 'whole'
                  and (matched.get('session') or {}).get('charged') == 'difference'
                  and matched.get('charge', {}).get('tokens') == 200)

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
            table = {e['message'] for e in FORMATS['codex']['errors'] if e['window'] not in (None, 'usage_limit')}
            check('format/codex-fake-lines', 'codex: each limit message the fake prints is the binary\'s own: a usage-limit '
                  'message built from its message, retry phrases and time formats, or an exhaustion message of its '
                  'error table [%s]' % [m for m in messages if not pattern.match(m or '') and m not in table][:2],
                  len(messages) >= 8 and all(pattern.match(m or '') or m in table for m in messages)
                  and any('again at' in m for m in messages) and any('later' in m for m in messages)
                  and any(m in table for m in messages))
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
