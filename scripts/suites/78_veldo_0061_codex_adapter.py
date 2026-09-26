"""VELDO-0061: the Codex adapter qualified on Linux: its registered lifecycle, the pinned vendor
executable, its terminal output as validated artifacts, its ordinary stop and its pre-launch caps.

Run: python3 scripts/selftest.py --suite 78_veldo_0061_codex_adapter

Only shared ROOT and expect are consumed. One temporary tree, in the owner's runtime directory so the
VELDO-0042 clone layout has no protected target beneath a temporary directory, holds the installed
.veldo copy (with its runtime/codex-qualification.json) the runner loads and the receiver, trusted
wrapper and clone entrance execute, so a registered mutation of a production module reaches all of
them. Real: a SQLite control store with OpenSSH journal signatures, Codex account records registered by
the owner over profiles .veldo/accounts.py prepares, VELDO-0036 reservations under their production
authority, VELDO-0052's Gate, VELDO-0031 claims, a Git source bound in the store, a VELDO-0042 clone per
dispatch entered through its Landlock entrance, the VELDO-0039 Runner and receiver processes, the
VELDO-0040 containment scopes under the owner's systemd user manager (transient scopes in a slice of
this run's own, stopped at its end; no unit is installed) and the kernel's cgroup, pidfd and /proc files.

The engine is the installed Codex 0.154.0 vendor binary where no model runs (`exec --json --help`, with
a fixture CODEX_HOME), and otherwise a fake Codex laid out as a vendor package, qualified by the
production writer, that prints the stream its packet scripts. Every line a fake prints is built from the
binary's own tables (VELDO-0062's cli-formats.json for the events, VELDO-0061's codex-exec.json for the
items) and the format row checks each one against them. No model runs, nothing logs in, no credential
exists and ~/.codex is never read. The profile's systemd-run is a shim that records every spawn by its
dispatch before it becomes the real systemd-run, so a spawn for a refused invocation is seen. Each row
is reported once: the cases of a row are parts of it.
"""


def _v61_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time

    HERE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    FORMATS = json.loads((HERE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['codex']
    EXEC = json.loads((HERE / 'proof' / 'VELDO-0061' / 'codex-exec.json').read_text())
    REAL = FORMATS['binary']
    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('lifecycle/registered', 'lifecycle/normal-run', 'lifecycle/actual-binary',
            'pin/unexpected-launch', 'pin/qualified-record',
            'artifacts/normal-exit', 'artifacts/missing-result', 'artifacts/malformed-output',
            'artifacts/missing-usage', 'artifacts/nonzero-and-signal',
            'stop/cooperative', 'stop/forced', 'stop/termination',
            'caps/boundaries', 'caps/refused-before-launch', 'caps/stop-at-cap', 'caps/observed',
            'format/codex-fake-lines')
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
    run_id = os.urandom(4).hex()
    slice_name = 'v61%s.slice' % run_id
    tools = dict(os.environ)
    runtime = tools.get('XDG_RUNTIME_DIR') or ''

    def systemctl(*args):
        return subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=20,
                              env=tools, stdin=subprocess.DEVNULL)

    base = Path(tempfile.mkdtemp(prefix='v61-', dir=runtime if os.path.isdir(runtime) else None))
    connections, launches, observed, stopped = [], [], {}, {}
    globals()['_V61_OBSERVED'] = observed
    try:
        mods = base / 'installed' / '.veldo'
        (mods / 'runtime').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        INSTALLED_QUALIFICATION = ROOT / '.veldo' / 'runtime' / 'codex-qualification.json'
        if INSTALLED_QUALIFICATION.is_file():
            shutil.copyfile(INSTALLED_QUALIFICATION, mods / 'runtime' / 'codex-qualification.json')
        S = load('v61_store', mods / 'control_store.py')
        L = load('v61_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = getattr(RES, 'ACC', None)
        X = getattr(L, 'ENGINES', {}).get('codex')
        HELPER = load('v61_helper', mods / 'accounts.py')
        EL = load('v61_eligibility', mods / 'control_eligibility.py')
        SIG = load('v61_signer', mods / 'control_signer.py')
        GP = load('v61_git', mods / 'git_process.py')
        CL = load('v61_clone', mods / 'control_clone.py')
        CT = load('v61_containment', mods / 'control_containment.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-61', 'repository-61', 'builder-61', 'linux-host-61'
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = state / 'authority' / 'control.sqlite3'
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

        # The owner's Codex accounts, over profiles the local helper prepares.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign) if ACC else None
        helper_root = base / 'helper'
        profiles, registered = {}, []
        for account in ('acct-x1', 'acct-x2', 'acct-real'):
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider='codex'))
            if record is None:
                record = {'config_dir': str(base / 'profiles' / account)}
                os.makedirs(record['config_dir'], mode=0o700)
            profiles[account] = record['config_dir']
            fields, error = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields is None or accounts is None:
                registered.append((account, error or 'no account records'))
                continue
            accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                              fields['profiles'], now=time.time())
            registered.append((account, None))
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        for account in ('acct-x1', 'acct-x2', 'acct-real'):
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        put('project:journey', 'project', dict(name='journey'))
        reservations.configure('policy/journey', 'project', 'journey', dict(BIG), now=time.time())

        def admitted(unit, **caps):
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project='journey',
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

        home = base / 'home'
        (home / 'projects').mkdir(parents=True)
        src = home / 'projects' / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True, stdin=subprocess.DEVNULL)
        (src / 'README').write_text('codex adapter source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True, stdin=subprocess.DEVNULL)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        clones = CL.Clones(dispatches, clones=str(state / 'clones'), caches=str(state / 'caches'), protected=[str(private)])

        # The fake Codex and its descendants. Each process marks <tag>.<name> with its pid, start time and
        # cgroup; the engine also records its argv, working directory, environment and packet, and each
        # SIGTERM it or a descendant takes is logged.
        markers = base / 'markers'
        markers.mkdir()
        common = '''import json, os, signal, subprocess, sys, time
from pathlib import Path
def facts(role):
    stat = Path('/proc/self/stat').read_text()
    return {'role': role, 'pid': os.getpid(), 'start': stat[stat.rindex(')') + 2:].split()[19],
            'cgroup': next(l[3:] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::'))}
def mark(markers, tag, name, data):
    temporary = Path(markers) / ('%s.%s.%d.tmp' % (tag, name, os.getpid()))
    temporary.write_text(json.dumps(data))
    os.replace(temporary, Path(markers) / ('%s.%s' % (tag, name)))
def log(markers, tag, name, what):
    with open(Path(markers) / ('%s.%s.%s' % (tag, name, what)), 'a') as handle:
        handle.write('%r\\n' % time.monotonic())
'''
        child = base / 'child61.py'
        child.write_text(common + '''markers, tag, name, kind = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
def on_term(signum, frame):
    log(markers, tag, name, 'term')
    if kind != 'stubborn':
        os._exit(143)
signal.signal(signal.SIGTERM, on_term)
mark(markers, tag, name, facts(name))
end = time.monotonic() + 60
while time.monotonic() < end:
    time.sleep(0.05)
''')
        fake = ('#!%s -B\n' % sys.executable) + common + '''markers = sys.argv[-1]
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
tag = dispatch.rsplit('/', 1)[-1]
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
def on_term(signum, frame):
    log(markers, tag, 'worker', 'term')
    if payload.get('on_term') != 'ignore':
        os._exit(143)
signal.signal(signal.SIGTERM, on_term)
for name, kind in payload.get('descendants') or []:
    subprocess.Popen([sys.executable, '-B', %r, markers, tag, name, kind], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL)
own = facts('worker')
own.update(argv=sys.argv, cwd=os.getcwd(), environment=dict(os.environ), packet=packet)
mark(markers, tag, 'worker', own)
printed = open(Path(markers) / (tag + '.out'), 'wb')
for step in payload.get('script') or []:
    if 'sleep' in step:
        time.sleep(step['sleep'])
        continue
    if 'kill' in step:
        os.kill(os.getpid(), step['kill'])
        time.sleep(10)
        continue
    data = ((json.dumps(step['line']) if 'line' in step else step['raw']) + '\\n').encode()
    printed.write(data)
    printed.flush()
    sys.stdout.buffer.write(data)
    sys.stdout.flush()
printed.close()
mark(markers, tag, 'exit', {'at': time.monotonic()})
sys.exit(payload.get('code', 0))
''' % str(child)

        def package(name, version='0.154.0-linux-x64', extra=b''):
            """A fake Codex vendor package: its manifest and the vendored binary at the real package path."""
            root = base / 'packages' / name
            vendored = root / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
            vendored.parent.mkdir(parents=True)
            (root / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': version}))
            vendored.write_bytes(fake.encode() + extra)
            vendored.chmod(0o755)
            return vendored
        GOOD = package('good')
        qualification_path = base / 'fake-qualification.json'
        written, written_error = attempt(lambda: X.qualification(str(GOOD)))
        if written is not None:
            qualification_path.write_text(json.dumps(written))
        FLAGS = list(getattr(X, 'FLAGS', ('exec', '--json')))
        # The perturbed executables: the qualified package with one byte changed after qualification, a newer
        # version of it, a link to the qualified binary, and the package manager's own `codex` link.
        CHANGED = package('changed', extra=b'#')
        NEWER = package('newer', version='0.155.0-linux-x64')
        (base / 'links').mkdir()
        LINK = base / 'links' / 'codex'
        LINK.symlink_to(GOOD)
        # ~/.nvm/.../bin/codex, the shim the package manager links: found beside the node the package is under.
        NPM_LINK = None
        for parent in Path(REAL).parents:
            if (parent / 'bin' / 'codex').is_symlink():
                NPM_LINK = str(parent / 'bin' / 'codex')
                break

        # Every contained spawn: the profile's systemd-run records its dispatch, then becomes the real one.
        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        shim = base / 'systemd-run'
        shim.write_text('#!/bin/sh\nprintf %%s "$VELDO_DISPATCH_ID" > "%s/spawn-$$"\nexec %s "$@"\n'
                        % (markers, real_systemd_run))
        shim.chmod(0o755)
        GRACE = 0.4
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': GRACE, 'kill_grace_seconds': GRACE, 'systemd_run': str(shim)}

        def adapter(executable, qualification=str(qualification_path), flags=None, extra=(str(markers),), **more):
            argv = [str(executable)] + (FLAGS if flags is None else flags) + list(extra)
            found = {'engine': 'codex', 'executable': str(executable), 'argv': clones.adapter(argv)}
            if qualification is not None:
                found['qualification'] = qualification
            found.update(more)
            return found
        ADAPTERS = {
            'codex': adapter(GOOD),
            'codex-changed': adapter(CHANGED),
            'codex-newer': adapter(NEWER),
            'codex-link': adapter(LINK),
            'codex-npm-link': adapter(NPM_LINK or '/nonexistent/bin/codex', qualification=None),
            'codex-flags': adapter(GOOD, flags=['exec']),
            # The installed binary, pinned by the installed qualification record; `--help` so no model runs.
            'codex-real': adapter(REAL, qualification=None, extra=('--help',), environment={'COLUMNS': '100'}),
        }
        config = base / 'receiver.json'
        config.write_text(json.dumps({'store': str(db), 'journal_key': str(private / 'journal'),
                                      'principal': 'launch-receiver', 'workspace': str(base), 'domain': DOMAIN,
                                      'repository': REPOSITORY, 'authority_generation': 1, 'host': HOST,
                                      'receipts': str(base / 'receipts'), 'artifacts': str(base / 'artifacts'),
                                      'profile': profile, 'adapters': ADAPTERS}))
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        provisioned = {}

        def receive(contract):
            # VELDO-0129 composes the clone with the launch; here each dispatch's clone is provisioned from its
            # accepted contract before the receiver is invoked, and the adapter's argv enters it.
            provisioned[contract['dispatch_id']] = attempt(lambda: clones.create(contract))
            launch = L.invoke(config, contract, dispatches, accept_seconds=30)
            launches.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, receive, account=account)
            return runners[account]

        CONFIGURATION = {'tools': ['shell'], 'mcp_servers': {}, 'model': 'configured-model'}
        fixture_lines = []

        def thread(ident):
            return {'type': 'thread.started', 'thread_id': ident}

        def item(event, ident, kind, **fields):
            return {'type': event, 'item': dict({'id': ident, 'type': kind}, **fields)}

        def completed(input_tokens, output_tokens, **more):
            usage = dict({'input_tokens': input_tokens, 'cached_input_tokens': 0, 'output_tokens': output_tokens,
                          'reasoning_output_tokens': 0}, **more)
            return {'type': 'turn.completed', 'usage': usage}

        def normal(ident, input_tokens=1200, output_tokens=300):
            """One turn as exec prints it: the thread, the turn, a command's start and completion, a reasoning
            and an agent message item, and the turn's completion with its usage."""
            return [thread(ident), {'type': 'turn.started'},
                    item('item.started', 'item_0', 'command_execution', aggregated_output='', status='in_progress'),
                    item('item.completed', 'item_0', 'command_execution', aggregated_output='README\n', exit_code=0,
                         status='completed'),
                    item('item.completed', 'item_1', 'reasoning'),
                    item('item.completed', 'item_2', 'agent_message'),
                    completed(input_tokens, output_tokens)]

        def job(script, code=0, deadline=40, resume=None, **payload):
            fixture_lines.extend(step['line'] for step in script if 'line' in step and not step.get('perturbed'))
            payload = dict(payload, task='work the unit', script=script, code=code)
            if resume:
                payload['resume'] = resume
            return payload, deadline

        def submit(account, unit, adapter_name, script=(), code=0, deadline=40, resume=None, **payload):
            body, deadline = job([dict(line=x) if isinstance(x, dict) and 'type' in x else x for x in script], code,
                                 deadline, resume, **payload)
            return runner(account).submit(unit, 'build', holder=HOLDER, source=str(src), revision='HEAD', payload=body,
                                          adapter=adapter_name, configuration=CONFIGURATION,
                                          deadline=time.time() + deadline)

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def tag(launch):
            return launch.dispatch_id.rsplit('/', 1)[-1]

        def marker(launch, name, timeout=10.0):
            path = markers / ('%s.%s' % (tag(launch), name))
            end = time.time() + (timeout if launch.result == 'accepted' else 0.05)
            while not path.exists() and time.time() < end:
                time.sleep(0.02)
            return json.loads(path.read_text()) if path.exists() else {}

        def printed(launch):
            path = markers / ('%s.out' % tag(launch))
            return [line for line in path.read_bytes().split(b'\n') if line] if path.exists() else []

        def spawns(launch):
            return len([p for p in markers.glob('spawn-*') if p.read_text() == launch.dispatch_id])

        def invocation(launch):
            found = entity(RES.entity('invocation', [DOMAIN, 'invocation/' + launch.dispatch_id]))
            return (found or {}).get('data') or {}

        def journal_seq(prefix):
            row = writer.execute('SELECT MIN(seq) FROM journal WHERE substr(command_id, 1, ?) = ?',
                                 (len(prefix), prefix)).fetchone()
            return row[0] if row else None

        def slot(launch):
            return (entity(RES.entity('worker', [DOMAIN, launch.dispatch_id])) or {}).get('data') or {}

        def receipt_lines(launch):
            path = base / 'receipts' / (hashlib.sha256(('invocation/' + launch.dispatch_id).encode()).hexdigest() + '.jsonl')
            return [line for line in path.read_bytes().split(b'\n')[1:] if line] if path.exists() else []

        def document(launch):
            """The artifact document the receiver reported with the exit, read from its file and checked
            against the digest it reported; {} when there is none or it does not match."""
            reported = getattr(launch, 'artifacts', None) or {}
            path = Path(reported.get('path') or '/nonexistent')
            if not path.is_file():
                return {}
            data = path.read_bytes()
            if 'sha256:' + hashlib.sha256(data).hexdigest() != reported.get('digest'):
                return {}
            return dict(json.loads(data), _private=(path.stat().st_mode & 0o777) == 0o600
                        and (path.parent.stat().st_mode & 0o777) == 0o700, _reported=reported)

        def verified(found):
            return bool(found) and getattr(X, 'verify', lambda d: False)({k: v for k, v in found.items()
                                                                          if not k.startswith('_')})

        def proc_start(pid):
            try:
                stat = Path('/proc/%d/stat' % pid).read_text()
                return stat[stat.rindex(')') + 2:].split()[19]
            except (OSError, ValueError, IndexError, TypeError):
                return None

        def living(facts):
            return bool(facts) and proc_start(facts.get('pid') or 0) == facts.get('start')

        def wait_for(predicate, seconds=10.0):
            end = time.time() + seconds
            while time.time() < end:
                if predicate():
                    return True
                time.sleep(0.02)
            return bool(predicate())

        def finish(account, launch):
            """Wait for the dispatch's end, recording what was alive the moment its record was read."""
            record = runner(account).wait(launch, timeout=60)
            return record or {}

        units = {name: admitted(unit, **caps) for name, unit, caps in (
            ('main', 'VELDO-9601', dict(invocations=3)), ('missing', 'VELDO-9602', dict(tokens=10 ** 6)),
            ('malformed', 'VELDO-9603', {}), ('usage', 'VELDO-9604', dict(tokens=10 ** 6)),
            ('failed', 'VELDO-9605', {}), ('nonzero', 'VELDO-9606', {}), ('signal', 'VELDO-9607', {}),
            ('cooperative', 'VELDO-9608', {}), ('forced', 'VELDO-9609', {}), ('termination', 'VELDO-9610', {}),
            ('cap', 'VELDO-9611', dict(tokens=1000)), ('limit', 'VELDO-9612', {}), ('limited', 'VELDO-9613', {}),
            ('real', 'VELDO-9614', {}), ('changed', 'VELDO-9615', {}), ('newer', 'VELDO-9616', {}),
            ('link', 'VELDO-9617', {}), ('npm', 'VELDO-9618', {}), ('flags', 'VELDO-9619', {}))}
        L1_STREAM = normal('thread-9601')
        LIMIT = "You've hit your usage limit. Try again later."
        runs, ended = {}, {}
        try:
            # Phase 1: every independent launch, submitted one after another, then each waited for.
            runs['normal'] = ('acct-x1', submit('acct-x1', units['main'], 'codex', L1_STREAM))
            # The same stream with its terminal record removed, a line exec never prints and one that is not
            # JSON, and a completion whose usage the CLI left out.
            runs['missing'] = ('acct-x1', submit('acct-x1', units['missing'], 'codex', normal('thread-9602')[:-1]))
            runs['malformed'] = ('acct-x1', submit('acct-x1', units['malformed'], 'codex', normal('thread-9603')[:3] + [
                {'raw': 'Reading prompt from stdin...', 'perturbed': True},
                {'line': {'type': 'turn.progress', 'usage': {}}, 'perturbed': True}] + normal('thread-9603')[3:]))
            runs['usage'] = ('acct-x1', submit('acct-x1', units['usage'], 'codex',
                                                normal('thread-9604')[:-1] + [{'type': 'turn.completed', 'usage': {}}]))
            runs['failed'] = ('acct-x1', submit('acct-x1', units['failed'], 'codex', normal('thread-9605')[:-1] + [
                {'type': 'error', 'message': 'stream disconnected before completion'},
                {'type': 'turn.failed', 'error': {'message': 'stream disconnected before completion'}}], code=1))
            runs['nonzero'] = ('acct-x1', submit('acct-x1', units['nonzero'], 'codex', normal('thread-9606'), code=3))
            runs['signal'] = ('acct-x1', submit('acct-x1', units['signal'], 'codex',
                                                 normal('thread-9607')[:3] + [{'kill': int(signal.SIGKILL)}]))
            runs['cap'] = ('acct-x1', submit('acct-x1', units['cap'], 'codex', normal('thread-9611')[:4] + [
                completed(1400, 100), {'sleep': 8}, {'type': 'turn.started'}, completed(10, 10)]))
            runs['limit'] = ('acct-x2', submit('acct-x2', units['limit'], 'codex', [
                thread('thread-9612'), {'type': 'turn.started'}, {'type': 'error', 'message': LIMIT},
                {'type': 'turn.failed', 'error': {'message': LIMIT}}], code=1))
            runs['real'] = ('acct-real', submit('acct-real', units['real'], 'codex-real'))
            for name, adapter_name in (('changed', 'codex-changed'), ('newer', 'codex-newer'), ('link', 'codex-link'),
                                       ('npm', 'codex-npm-link'), ('flags', 'codex-flags')):
                runs[name] = ('acct-x1', submit('acct-x1', units[name], adapter_name, normal('thread-' + name)))
            for name in list(runs):
                account, launch = runs[name]
                ended[name] = finish(account, launch)

            # Phase 2: the stops. Each engine blocks until stopped; its descendants are started first.
            BLOCK = [thread('thread-stop'), {'type': 'turn.started'}, {'sleep': 30}]
            runs['cooperative'] = ('acct-x1', submit('acct-x1', units['cooperative'], 'codex', BLOCK,
                                                      descendants=[['helper', 'cooperative']]))
            runs['forced'] = ('acct-x1', submit('acct-x1', units['forced'], 'codex', BLOCK, on_term='ignore',
                                                 descendants=[['helper', 'stubborn']]))
            runs['termination'] = ('acct-x1', submit('acct-x1', units['termination'], 'codex', BLOCK,
                                                      descendants=[['helper', 'stubborn']]))
            for name in ('cooperative', 'forced', 'termination'):
                account, launch = runs[name]
                marker(launch, 'worker')
                marker(launch, 'helper')
                stopped[name] = {'asked': time.monotonic(), 'ok': launch.stop()}
            alive_at_end = {}
            for name in ('cooperative', 'forced', 'termination'):
                account, launch = runs[name]
                ended[name] = finish(account, launch)
                stopped[name]['ended'] = time.monotonic()
                alive_at_end[name] = {role: living(marker(launch, role, 0.5)) for role in ('worker', 'helper')}

            # Phase 3: the retry of the main unit, the retry of the unit whose usage stayed unknown and a launch on
            # the account whose usage limit was reported.
            runs['retry'] = ('acct-x1', submit('acct-x1', units['main'], 'codex', normal('thread-retry', 700, 100)))
            runs['unknown'] = ('acct-x1', submit('acct-x1', units['missing'], 'codex', normal('thread-9602b')))
            runs['limited'] = ('acct-x2', submit('acct-x2', units['limited'], 'codex', normal('thread-9613')))
            for name in ('retry', 'unknown', 'limited'):
                account, launch = runs[name]
                ended[name] = finish(account, launch)
            # Phase 4: the follow-on resuming the first thread, then one more invocation past the unit's cap of three.
            runs['follow'] = ('acct-x1', submit('acct-x1', units['main'], 'codex', normal('thread-9601', 500, 50),
                                                resume='thread-9601'))
            ended['follow'] = finish('acct-x1', runs['follow'][1])
            runs['exhausted'] = ('acct-x1', submit('acct-x1', units['main'], 'codex', normal('thread-over')))
            ended['exhausted'] = finish('acct-x1', runs['exhausted'][1])
        except Exception as exc:  # noqa: BLE001 - a failed launch phase is data for every row
            for name in ROWS:
                check(name, 'the launch phases ran to their end (they raised %s: %s)' % (type(exc).__name__,
                                                                                         str(exc)[:300]), False)

        def get(name):
            return runs.get(name, (None, None))[1]

        def history(launch):
            return [h.get('state') for h in rec(launch.dispatch_id).get('history') or []]

        # What each run did, kept for a reader of this run (globals()['_V61_OBSERVED']); no row reads it.
        for name, (_, launch) in runs.items():
            found = document(launch)
            observed[name] = {'result': launch.result, 'history': history(launch), 'refusal': rec(launch.dispatch_id).get('refusal'),
                              'termination': rec(launch.dispatch_id).get('termination'), 'spawns': spawns(launch),
                              'supervision': {k: (launch.supervision or {}).get(k) for k in ('cause', 'steps', 'empty')},
                              'verdict': found.get('verdict'), 'malformed': found.get('malformed'),
                              'invocation': {k: invocation(launch).get(k) for k in ('boundary', 'state', 'outcome', 'unknown',
                                                                                     'observed')},
                              'stopped': stopped.get(name)}

        # AC1: the lifecycle and the pin
        with region('lifecycle/registered'):
            registration = getattr(X, 'REGISTRATION', {}) or {}
            operations = set(registration.get('lifecycle') or ())
            named = {'accept', 'launch', 'observe', 'stop', 'exit', 'artifacts'}
            check('lifecycle/registered', 'the installed Codex adapter registration enumerates exactly the six lifecycle '
                  'operations the specification names [%s]' % sorted(operations), operations == named)
            installed = json.loads((mods / 'runtime' / 'codex-qualification.json').read_text()) \
                if (mods / 'runtime' / 'codex-qualification.json').is_file() else {}
            check('lifecycle/registered', 'the registration\'s flags are the installed qualification\'s, and every '
                  'configured Codex adapter launches with them [%s %s]' % (registration.get('flags'), installed.get('flags')),
                  list(registration.get('flags') or ()) == installed.get('flags') == FLAGS and FLAGS
                  and all(a['argv'][a['argv'].index(a['executable']) + 1:][:len(FLAGS)] == FLAGS
                          for n, a in ADAPTERS.items() if n != 'codex-flags'))
            normal_launch, stop_launch = get('normal'), get('cooperative')
            seen = {
                'accept': normal_launch is not None and history(normal_launch)[:3] == ['prepared', 'accepted', 'running'],
                'launch': normal_launch is not None and spawns(normal_launch) == 1
                and (rec(normal_launch.dispatch_id).get('process') or {}).get('pid') == marker(normal_launch, 'worker').get('pid'),
                'observe': normal_launch is not None and len(receipt_lines(normal_launch)) == 1,
                'stop': stop_launch is not None and (stop_launch.supervision or {}).get('cause') == 'requested'
                and rec(stop_launch.dispatch_id).get('state') == 'exited',
                'exit': normal_launch is not None and rec(normal_launch.dispatch_id).get('state') == 'exited',
                'artifacts': normal_launch is not None and document(normal_launch).get('verdict') == 'result',
            }
            check('lifecycle/registered', 'each registered operation was driven through the trusted runner on the '
                  'qualified configuration and observed [%s]' % sorted(k for k, v in seen.items() if not v),
                  operations and all(seen.get(op) for op in operations))

        with region('lifecycle/normal-run'):
            launch = get('normal')
            record = rec(launch.dispatch_id)
            contract = record.get('contract') or {}
            engine = marker(launch, 'worker')
            env = engine.get('environment') or {}
            acceptance = dispatches.receipt(launch.dispatch_id, 'accept')
            check('lifecycle/normal-run', 'accepted, then running, then exited under one dispatch, the recorded process '
                  'is the engine that printed [%s]' % history(launch),
                  launch.result == 'accepted' and history(launch) == ['prepared', 'accepted', 'running', 'exited']
                  and (record.get('process') or {}).get('pid') == engine.get('pid')
                  and (record.get('process') or {}).get('start') == engine.get('start'))
            handle, clone_error = provisioned.get(launch.dispatch_id, (None, 'none'))
            work = Path(handle.paths.get('work', '/nonexistent')) if handle else None
            head = GP.run(['git', '-C', str(work), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() \
                if work else None
            check('lifecycle/normal-run', 'the engine ran in its own clone, at the accepted commit [%s %s]'
                  % (engine.get('cwd'), clone_error),
                  work is not None and engine.get('cwd') == str(work) and head == contract.get('source', {}).get('commit')
                  and env.get('VELDO_CLONE') == str(work))
            check('lifecycle/normal-run', 'it was the pinned vendor binary with the qualified flags, as configured '
                  '[%s]' % engine.get('argv'),
                  engine.get('argv') == [str(GOOD)] + FLAGS + [str(markers)])
            packet = engine.get('packet') or {}
            check('lifecycle/normal-run', 'it was handed exactly the accepted source, input and tool configuration',
                  packet.get('source') == contract.get('source') and packet.get('payload') == contract['input']['payload']
                  and packet.get('configuration') == contract['capability']['configuration'] == CONFIGURATION)
            check('lifecycle/normal-run', 'its environment names its dispatch, the acceptance it launched under, its '
                  'account\'s own profile and DISABLE_AUTOUPDATER=1 [%s]' % env.get('DISABLE_AUTOUPDATER'),
                  env.get('VELDO_DISPATCH_ID') == launch.dispatch_id and env.get('VELDO_DISPATCH_ACCEPTANCE') == acceptance
                  and acceptance and env.get('CODEX_HOME') == profiles['acct-x1'] and env.get('DISABLE_AUTOUPDATER') == '1')
            found = document(launch)
            check('lifecycle/normal-run', 'the stream was observed as it came (its usage line kept as a receipt) and its '
                  'artifact document returned with the exit, naming the pinned executable [%s]' % found.get('executable'),
                  receipt_lines(launch) == [printed(launch)[-1]] and found.get('lines') == [x.decode() for x in printed(launch)]
                  and (found.get('executable') or {}).get('sha256') == (json.loads(qualification_path.read_text())
                                                                         if qualification_path.is_file() else {}).get('sha256')
                  and found.get('dispatch_id') == launch.dispatch_id and found.get('_private'))

        with region('lifecycle/actual-binary'):
            launch = get('real')
            record = rec(launch.dispatch_id)
            termination = record.get('termination') or {}
            direct = subprocess.run([REAL, 'exec', '--json', '--help'], capture_output=True, timeout=60,
                                    stdin=subprocess.DEVNULL,
                                    env={'PATH': '/usr/bin:/bin', 'HOME': str(home), 'LANG': 'C.UTF-8', 'COLUMNS': '100',
                                         'CODEX_HOME': str(base / 'direct-codex-home')})
            check('lifecycle/actual-binary', 'the installed Codex 0.154.0 vendor binary, pinned by the installed '
                  'qualification, was launched through the trusted runner in its clone and exited 0 [%s %s]'
                  % (history(launch), termination),
                  history(launch) == ['prepared', 'accepted', 'running', 'exited'] and termination.get('returncode') == 0
                  and spawns(launch) == 1)
            check('lifecycle/actual-binary', 'what it printed is what that binary prints for the same arguments, byte '
                  'for byte (%d bytes)' % termination.get('output_bytes', 0),
                  direct.returncode == 0 and termination.get('output_digest') == 'sha256:' + hashlib.sha256(direct.stdout).hexdigest()
                  and termination.get('output_bytes') == len(direct.stdout) > 1000)
            handle, clone_error = provisioned.get(launch.dispatch_id, (None, 'none'))
            entered = [json.loads(x.read_text()) for x in sorted((Path(handle.paths['root']) / 'entered').glob('*.json'))] \
                if handle else []
            check('lifecycle/actual-binary', 'it entered its own clone as the process the dispatch recorded, inside the '
                  'dispatch\'s containment scope [%s %s]' % (entered, clone_error),
                  len(entered) == 1 and entered[0].get('dispatch_id') == launch.dispatch_id
                  and entered[0].get('pid') == (record.get('process') or {}).get('pid')
                  and str(entered[0].get('cgroup', '')).endswith('/' + CT.unit_name(launch.dispatch_id)))
            found = document(launch)
            check('lifecycle/actual-binary', 'its zero exit with no terminal record is no completion: its artifact '
                  'document is malformed output (help text), the invocation failed and the slot was not returned '
                  'completed [%s %s]' % (found.get('verdict'), invocation(launch).get('outcome')),
                  found.get('verdict') == 'malformed_output' and found.get('completed') is False and verified(found)
                  and invocation(launch).get('outcome') == 'failed'
                  and (slot(launch).get('retirement') or {}).get('outcome') == 'failed'
                  and (found.get('executable') or {}).get('sha256') == FORMATS['sha256'])

        with region('pin/unexpected-launch'):
            expected = {'changed': 'stale_subject:engine_digest', 'newer': 'stale_subject:engine_version',
                        'link': 'invalid_input:engine_link', 'npm': 'invalid_input:engine_link',
                        'flags': 'invalid_input:engine_flags'}
            for name, refusal in expected.items():
                launch = get(name)
                record = rec(launch.dispatch_id)
                check('pin/unexpected-launch', '%s: refused %s before acceptance, with nothing spawned, reserved or run '
                      '[%s %s spawns=%d]' % (name, refusal, record.get('refusal'), history(launch), spawns(launch)),
                      launch.result == 'refused' and record.get('refusal') == refusal
                      and history(launch) == ['prepared', 'refused'] and spawns(launch) == 0 and not invocation(launch)
                      and not marker(launch, 'worker'))
            check('pin/unexpected-launch', 'the package manager\'s codex link exists and is a link [%s]' % NPM_LINK,
                  NPM_LINK is not None and os.path.islink(NPM_LINK))
            check('pin/unexpected-launch', 'the changed binary differs from the qualified one by the one byte added after '
                  'qualification', CHANGED.read_bytes() == GOOD.read_bytes() + b'#')
            launch = get('normal')
            check('pin/unexpected-launch', 'control: the qualified binary launched, once', spawns(launch) == 1
                  and launch.result == 'accepted')

        with region('pin/qualified-record'):
            installed = json.loads(INSTALLED_QUALIFICATION.read_text()) if INSTALLED_QUALIFICATION.is_file() else {}
            fresh, error = attempt(lambda: X.qualification(REAL))
            check('pin/qualified-record', 'the installed qualification record is what the production writer makes of '
                  'the installed vendor binary now [%s]' % error, installed and fresh == installed)
            check('pin/qualified-record', 'it names Codex 0.154.0, the vendor path inside @openai/codex, the digest both '
                  'extracted tables read from the binary, and the qualified flags',
                  installed.get('version') == FORMATS['version'] == EXEC['version'] == '0.154.0'
                  and installed.get('sha256') == FORMATS['sha256'] == EXEC['sha256']
                  and installed.get('executable') == 'vendor/x86_64-unknown-linux-musl/bin/codex'
                  and installed.get('package') == '@openai/codex' and installed.get('flags') == ['exec', '--json']
                  and sorted(installed.get('terminal_protocol', {}).get('events', [])) == sorted(EXEC['events'])
                  and installed.get('terminal_protocol', {}).get('item_kinds') == EXEC['item']['kinds'])
            scaffold = load('v61_scaffold', mods / 'init_scaffold.py')
            engine_copy = ROOT / 'engine' / 'runtime' / 'codex-qualification.json'
            check('pin/qualified-record', 'init lays it down beside the module that reads it, from a canonical engine copy '
                  'identical to it', ('runtime/codex-qualification.json', '.veldo/runtime/codex-qualification.json')
                  in list(scaffold._RUNTIME_ASSETS) and engine_copy.is_file()
                  and engine_copy.read_bytes() == INSTALLED_QUALIFICATION.read_bytes()
                  and Path(getattr(X, 'QUALIFICATION', '/nonexistent')) == mods / 'runtime' / 'codex-qualification.json')

        # AC2: terminal output as artifacts
        with region('artifacts/normal-exit'):
            launch = get('normal')
            found = document(launch)
            check('artifacts/normal-exit', 'a zero exit whose last turn closed with turn.completed is a result: its '
                  'thread, turn and items as printed [%s]' % found.get('verdict'),
                  found.get('verdict') == 'result' and found.get('completed') is True
                  and found.get('terminal') == 'turn.completed' and found.get('thread') == 'thread-9601'
                  and found.get('turns') == 1 and found.get('malformed') == []
                  and [(i['id'], i['type']) for i in found.get('items') or []]
                  == [('item_0', 'command_execution'), ('item_1', 'reasoning'), ('item_2', 'agent_message')]
                  and all(json.loads(found['lines'][i['line']])['item']['id'] == i['id'] for i in found['items']))
            check('artifacts/normal-exit', 'the invocation settled completed and its slot was returned completed',
                  invocation(launch).get('outcome') == 'completed' and invocation(launch).get('state') == 'settled'
                  and (slot(launch).get('retirement') or {}).get('outcome') == 'completed')
            tampered = {k: v for k, v in found.items() if not k.startswith('_')}
            tampered['verdict'] = 'malformed_output'
            check('artifacts/normal-exit', 'the document verifies from its own lines, and one with its verdict changed '
                  'does not', verified(found) and not getattr(X, 'verify', lambda d: True)(tampered))

        with region('artifacts/missing-result'):
            launch = get('missing')
            found = document(launch)
            call = invocation(launch)
            check('artifacts/missing-result', 'the normal stream with its terminal record removed, exit 0: missing_result, '
                  'never completion [%s]' % found.get('verdict'),
                  (rec(launch.dispatch_id).get('termination') or {}).get('returncode') == 0
                  and found.get('verdict') == 'missing_result' and found.get('completed') is False
                  and found.get('lines') == [json.dumps(x) for x in normal('thread-9602')[:-1]] and verified(found))
            check('artifacts/missing-result', 'the invocation settled failed and the worker slot was returned failed, not '
                  'completed [%s %s]' % (call.get('outcome'), (slot(launch).get('retirement') or {}).get('outcome')),
                  call.get('outcome') == 'failed' and (slot(launch).get('retirement') or {}).get('outcome') == 'failed')
            check('artifacts/missing-result', 'its tokens and messages stay unknown and their reservation is retained '
                  '[%s %s]' % (call.get('state'), call.get('unknown')),
                  call.get('state') == 'unknown' and set(call.get('unknown') or ()) == {'tokens', 'messages'})

        with region('artifacts/malformed-output'):
            launch = get('malformed')
            found = document(launch)
            check('artifacts/malformed-output', 'a line that is not JSON and an event exec does not print make the '
                  'output malformed, both named, never completion [%s %s]' % (found.get('verdict'), found.get('malformed')),
                  found.get('verdict') == 'malformed_output' and found.get('malformed') == [3, 4]
                  and found.get('terminal') == 'turn.completed' and verified(found)
                  and invocation(launch).get('outcome') == 'failed')

        with region('artifacts/missing-usage'):
            launch = get('usage')
            found = document(launch)
            call = invocation(launch)
            check('artifacts/missing-usage', 'a completed turn whose usage the CLI left out is a result with its usage '
                  'unknown: the reservation is retained, never counted zero [%s %s %s]'
                  % (found.get('verdict'), call.get('state'), call.get('observed')),
                  found.get('verdict') == 'result' and call.get('outcome') == 'completed' and call.get('state') == 'unknown'
                  and 'tokens' in (call.get('unknown') or ()) and 'tokens' not in (call.get('observed') or {}))

        with region('artifacts/nonzero-and-signal'):
            cases = (('failed', 'turn_failed', {'returncode': 1, 'signal': None}),
                     ('nonzero', 'nonzero_exit', {'returncode': 3, 'signal': None}),
                     ('signal', 'signal', {'returncode': None, 'signal': int(signal.SIGKILL)}))
            for name, verdict, exit_status in cases:
                launch = get(name)
                found = document(launch)
                termination = rec(launch.dispatch_id).get('termination') or {}
                check('artifacts/nonzero-and-signal', '%s: the live exit %s is %s, the invocation failed [%s %s]'
                      % (name, exit_status, verdict, found.get('verdict'), termination),
                      {k: termination.get(k) for k in exit_status} == exit_status and found.get('verdict') == verdict
                      and found.get('completed') is False and invocation(launch).get('outcome') == 'failed'
                      and verified(found))
            call = invocation(get('signal'))
            check('artifacts/nonzero-and-signal', 'the signalled invocation\'s usage stays unknown, its reservation '
                  'retained', call.get('state') == 'unknown')

        # AC3: ordinary stop
        def stop_rows(name, row, worker_signalled):
            launch = get(name)
            record = rec(launch.dispatch_id)
            supervision = launch.supervision or {}
            termination = record.get('termination') or {}
            engine = marker(launch, 'worker')
            check(row, '%s: the stop was asked of the receiver and the dispatch recorded exited, stopped on request, '
                  'its group empty [%s %s]' % (name, history(launch), supervision.get('cause')),
                  stopped[name]['ok'] and history(launch)[-1:] == ['exited'] and supervision.get('cause') == 'requested'
                  and supervision.get('empty') is True)
            check(row, '%s: every process of the worker is gone: the engine and its descendant [%s]'
                  % (name, alive_at_end[name]), alive_at_end[name] == {'worker': False, 'helper': False})
            check(row, '%s: the exit recorded is the stopped engine\'s own, under the process identity it ran as [%s]'
                  % (name, termination),
                  (record.get('process') or {}).get('pid') == engine.get('pid')
                  and (record.get('process') or {}).get('start') == engine.get('start')
                  and (termination.get('signal') == int(signal.SIGKILL) if worker_signalled
                       else termination.get('returncode') == 143))
            call = invocation(launch)
            found = document(launch)
            check(row, '%s: its original invocation is recorded cancelled with its usage unknown and retained, and its '
                  'artifacts name it, with no result [%s %s]' % (name, call.get('outcome'), found.get('verdict')),
                  call.get('invocation') == 'invocation/' + launch.dispatch_id and call.get('outcome') == 'cancelled'
                  and call.get('state') == 'unknown' and found.get('invocation') == call.get('invocation')
                  and found.get('verdict') in ('missing_result', 'signal') and found.get('completed') is False)
            return supervision

        with region('stop/cooperative'):
            supervision = stop_rows('cooperative', 'stop/cooperative', False)
            took = stopped['cooperative']['ended'] - stopped['cooperative']['asked']
            steps = [s.get('step') for s in supervision.get('steps') or []]
            check('stop/cooperative', 'the engine ended on the cooperative request, before any forced step [%s %.2fs]'
                  % (steps, took), 'kill' not in steps and took < 5)

        with region('stop/forced'):
            supervision = stop_rows('forced', 'stop/forced', True)
            took = stopped['forced']['ended'] - stopped['forced']['asked']
            steps = [s.get('step') for s in supervision.get('steps') or []]
            graces = supervision.get('graces') or {}
            check('stop/forced', 'an engine that ignores the request is killed with its group after the configured '
                  'graces, within their bound [%s %.2fs %s]' % (steps, took, graces),
                  'kill' in steps and graces == {'stop_grace_seconds': GRACE, 'kill_grace_seconds': GRACE}
                  and 2 * GRACE - 0.1 <= took <= 2 * GRACE + 4.0)

        with region('stop/termination'):
            supervision = stop_rows('termination', 'stop/termination', False)
            log = markers / ('%s.helper.term' % tag(get('termination')))
            check('stop/termination', 'the engine left a descendant that ignores the request, and the stop is recorded '
                  'only after that descendant was killed with the group [%s]' % supervision.get('steps'),
                  log.exists() and supervision.get('empty') is True and 'kill' in [s.get('step') for s in
                                                                                    supervision.get('steps') or []])

        # AC4: the caps before launch
        with region('caps/boundaries'):
            for name, boundary in (('normal', 'initial'), ('retry', 'retry'), ('follow', 'follow_on')):
                launch = get(name)
                call = invocation(launch)
                run_seq = journal_seq('dispatch/run/' + launch.dispatch_id + '/')
                check('caps/boundaries', '%s: the %s invocation was reserved against its caps before its engine was '
                      'spawned (reservation %s before the running record %s), and it ran the pinned binary'
                      % (name, boundary, call.get('accepted_seq'), run_seq),
                      call.get('boundary') == boundary and isinstance(call.get('accepted_seq'), int)
                      and isinstance(run_seq, int) and call['accepted_seq'] < run_seq and spawns(launch) == 1
                      and document(launch).get('verdict') == 'result')

        with region('caps/refused-before-launch'):
            cases = (('exhausted', 'the fourth invocation of a unit capped at three'),
                     ('unknown', 'a retry under a token cap whose earlier usage is unknown'),
                     ('limited', 'an account whose usage limit Codex reported'))
            for name, what in cases:
                launch = get(name)
                record = rec(launch.dispatch_id)
                check('caps/refused-before-launch', '%s: %s is refused by name before launch, with zero spawns and no '
                      'engine run [%s spawns=%d]' % (name, what, record.get('refusal'), spawns(launch)),
                      launch.result == 'refused' and str(record.get('refusal')).startswith('missing_authority:allowance:')
                      and spawns(launch) == 0 and not marker(launch, 'worker') and not receipt_lines(launch))
            check('caps/refused-before-launch', 'the unknown one is refused for its unknown allowance, after the '
                  'invocation that left it unknown ran [%s]' % rec(get('unknown').dispatch_id).get('refusal'),
                  'unknown' in str(rec(get('unknown').dispatch_id).get('refusal'))
                  and document(get('missing')).get('verdict') == 'missing_result')
            windows = ((ACC.read(writer, 'acct-x2') if ACC else None) or {}).get('windows') or {}
            check('caps/refused-before-launch', 'the limited account carries the usage_limit window Codex reported, '
                  'rejected with no reset stated, from the invocation that saw it [%s]' % windows,
                  (windows.get('usage_limit') or {}).get('status') == 'rejected'
                  and (windows.get('usage_limit') or {}).get('reset_at') is None
                  and (windows.get('usage_limit') or {}).get('source_dispatch') == get('limit').dispatch_id
                  and document(get('limit')).get('verdict') == 'turn_failed')

        with region('caps/stop-at-cap'):
            launch = get('cap')
            supervision = launch.supervision or {}
            call = invocation(launch)
            check('caps/stop-at-cap', 'the report that reached the unit\'s token cap stopped the worker before its '
                  'next turn [%s %s]' % (supervision.get('cause'), call.get('observed')),
                  supervision.get('cause') == 'usage_cap' and call.get('outcome') == 'cancelled'
                  and not marker(launch, 'exit', 0.1) and (call.get('observed') or {}).get('tokens') == 1500
                  and len(printed(launch)) == 5)
            found = document(launch)
            check('caps/stop-at-cap', 'the capped invocation returned what it printed up to the stop as its artifacts, '
                  'never as a completion [%s]' % found.get('verdict'),
                  found.get('lines') == [x.decode() for x in printed(launch)] and found.get('completed') is False
                  and found.get('invocation') == call.get('invocation') and verified(found))

        with region('caps/observed'):
            for name in ('normal', 'retry', 'follow'):
                launch = get(name)
                call = invocation(launch)
                found = document(launch)
                lines = [json.loads(x) for x in found.get('lines') or []]
                tokens = sum(e['usage']['input_tokens'] + e['usage']['output_tokens'] for e in lines
                             if e.get('type') == 'turn.completed')
                observed = call.get('observed') or {}
                check('caps/observed', '%s: one invocation, its wall time and the tokens and messages the CLI reported in '
                      'the stream the adapter returned [%s]' % (name, observed),
                      observed.get('invocations') == 1 and 0 < observed.get('wall_seconds', 0) < 60
                      and observed.get('tokens') == tokens > 0 and observed.get('messages') == 1
                      and call.get('state') == 'settled')
            balances = reservations.balances('unit', units['main'])
            check('caps/observed', 'the unit\'s balance is the three invocations that ran and their reported tokens '
                  '[%s]' % balances, balances.get('invocations') == 3 and balances.get('tokens') == 1500 + 800 + 550)

        # the fixtures
        with region('format/codex-fake-lines'):
            events, kinds = FORMATS['events'], EXEC['item']['items']

            def conform(value, schema):
                kind = schema.get('type')
                if kind == 'any':
                    return True
                if kind == 'literal':
                    return value == schema['value']
                if kind == 'string':
                    return isinstance(value, str)
                if kind == 'number':
                    return isinstance(value, int) and not isinstance(value, bool) if schema.get('int') else \
                        isinstance(value, (int, float))
                if kind == 'enum':
                    return value in schema['values']
                if kind == 'object':
                    fields = schema.get('fields') or {}
                    return isinstance(value, dict) and set(value) <= set(fields) and all(
                        k in value or fields[k].get('optional') for k in fields) and all(
                        conform(v, fields[k]) for k, v in value.items())
                return False
            problems = []
            for line in fixture_lines:
                schema = events.get(line.get('type'))
                if schema is None or not conform(line, schema):
                    problems.append(line)
                elif 'item' in line and not (line['item'].get('type') in kinds
                                             and conform(line['item'], kinds[line['item']['type']])):
                    problems.append(line)
            check('format/codex-fake-lines', 'every one of the %d lines the fakes were scripted to print is an event the '
                  'installed binary declares, its item an exec item of a declared kind with only exec\'s own fields '
                  '[%s]' % (len(fixture_lines), problems[:3]), len(fixture_lines) > 40 and not problems)
            printed_kinds = {line.get('type') for line in fixture_lines}
            check('format/codex-fake-lines', 'the fakes print every event the adapter reads, and no event outside '
                  'exec\'s eight [%s]' % sorted(printed_kinds),
                  {'thread.started', 'turn.started', 'turn.completed', 'turn.failed', 'item.started', 'item.completed',
                   'error'} <= printed_kinds <= set(EXEC['events']) == set(events))
            templates = [e['message'] for e in FORMATS['errors'] if e.get('window') == 'usage_limit']
            check('format/codex-fake-lines', 'the usage-limit message the fake prints is one of the binary\'s own '
                  'forms with its no-reset phrase', any(form.replace('{}', phrase) == LIMIT for form in templates
                                                        for phrase in FORMATS['usage_limit']['retry_later']))
            check('format/codex-fake-lines', 'the extracted item table matches the installed binary now',
                  subprocess.run([sys.executable, '-B', str(HERE / 'proof' / 'VELDO-0061' / 'extract_items.py'), '--check'],
                                 capture_output=True, timeout=120, stdin=subprocess.DEVNULL).returncode == 0)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        for launch in launches:
            with contextlib.suppress(Exception):
                if launch.child is not None and launch.child.poll() is None:
                    launch.child.kill()
                    launch.child.wait(timeout=10)
        with contextlib.suppress(Exception):
            systemctl('stop', slice_name)
        with contextlib.suppress(Exception):
            mine = sorted({CT.unit_name(launch.dispatch_id) for launch in launches})
            loaded = [line.split()[0] for line in systemctl('list-units', '--all', '--plain', '--no-legend',
                                                            *mine).stdout.splitlines() if line.split()]
            if loaded:
                systemctl('reset-failed', *loaded)
        # Whatever a defective build left running (a descendant that escaped its stop) is ended here.
        for leftover in sorted(markers.glob('*.*')) if 'markers' in dir() else ():
            with contextlib.suppress(Exception):
                facts = json.loads(leftover.read_text())
                if isinstance(facts, dict) and facts.get('pid') and proc_start(facts['pid']) == facts.get('start'):
                    os.kill(facts['pid'], signal.SIGKILL)
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
                    print('  VELDO-0061 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0061 %s detail: no check ran' % name)
        expect('VELDO-0061 ' + name, ok)
    print('VELDO-0061 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session. The gate's mutation stage runs every suite without XDG_RUNTIME_DIR; the receiver, its
# systemd tools and this suite's own systemctl reach the user manager through /run/user/<uid> for this run.
_v61_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v61_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v61_suite()
finally:
    if _v61_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v61_session
