"""VELDO-0060: the Claude Code adapter, launched from its pinned executable, returning validated artifacts.

Run: python3 scripts/selftest.py --suite 78_veldo_0060_claude_adapter

Only shared ROOT and expect are consumed. One temporary tree, in the owner's runtime directory so no
protected target of the isolated clone sits beneath a temporary directory, holds the installed .veldo
copy the suite loads AND the launch receiver process executes, so a registered mutation of a production
module reaches both. Real: a SQLite control store with OpenSSH journal signatures, the owner's account
records over a profile the local helper prepares, VELDO-0036 reservations under their production
authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git source repository bound to the store, a
VELDO-0042 isolated clone confined with Landlock, the VELDO-0039 Runner and receiver processes and the
trusted wrapper that execs the engine.

The engine is a fake `claude` this suite writes, installed as version 2.1.281 in a versions directory
of the installer's shape and copied under the factory state root by the production `pin`; the suite's
installed qualification record names that copy's digest. The fake records how it was started (argv,
environment, working directory, process identity) and what the store held for its invocation, then
prints the stream its packet scripts. Every line it prints is built in the shape Claude Code 2.1.281
prints (proof/VELDO-0062/cli-formats.json, read out of the binary), every option it is started with
must be one the binary's main command declares (proof/VELDO-0060/cli-options.json, read out of the
same binary), and the two format rows check both. The perturbations the artifact rows need (a
truncated line, a line that is not JSON, a result without its usage, a stream without its result)
are each built from a conforming line and checked as exactly that perturbation. No real engine runs,
nothing logs in and no credential exists.

Most launches go through the wrapper without a containment group (`identity: reported`), where a stop
kills the worker's session and the dispatch is then unknown, because that path cannot confirm the engine
ended. The contained rows run BOTH engines, Claude Code and Codex (the same fake laid out as a Codex vendor
package and qualified by control_engine_codex.qualification), on the local Linux contained launch through
the one receiver path: each dispatch in its own VELDO-0040 transient scope under the owner's systemd user
manager, in a slice of this run's own (stopped, and its failed units cleared, at the end; no unit is
installed), its profile's systemd-run a shim that records every spawn by its dispatch before it becomes
the real one. There the bind, the scope, the Landlock clone entrance, the pinned exec, the cooperative
and forced stops, a descendant that outlives the group's SIGTERM, the artifact and the exit record are
each observed. The floor row drives VELDO-0049's FloorAuthority over the same store. Each row is
reported once.
"""


def _v60_suite():
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
    import uuid

    # The installed CLI's formats and command line, extracted from its binary. Read beside this suite
    # file, so a run against another tree (the red record's) checks the same tables.
    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    FORMATS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['claude_code']
    OPTIONS = json.loads((TREE / 'proof' / 'VELDO-0060' / 'cli-options.json').read_text())['claude_code']
    VERSION = '2.1.281'

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
    }
    ROWS = ('lifecycle/registration', 'lifecycle/pinned-launch',
            'pin/unexpected-launch', 'pin/copy', 'pin/shipped-qualification',
            'artifact/complete', 'artifact/missing-result', 'artifact/exits', 'artifact/malformed-output',
            'artifact/missing-usage', 'artifact/exit-record', 'floor/missing-result',
            'stop/requested', 'stop/descendant-alive',
            'caps/before-launch', 'caps/allowance-states', 'caps/stop-at-cap',
            'contained/bind', 'contained/scope', 'contained/clone-entry', 'contained/pinned-exec',
            'contained/stop-cooperative', 'contained/stop-forced', 'contained/stop-descendant',
            'contained/artifact', 'contained/exit-record',
            'format/fake-lines', 'format/fake-argv')
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

    def sha(data):
        return 'sha256:' + hashlib.sha256(data).hexdigest()

    def file_sha(path):
        return sha(Path(path).read_bytes())

    started = time.monotonic()
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v60-', dir=runtime if os.path.isdir(runtime) else None))
    # The contained rows' transient scopes live in a slice of this run's own, stopped at its end.
    slice_name = 'v60%s.slice' % os.urandom(4).hex()
    tools = dict(os.environ)
    contained_launches = []
    connections = []
    escaped = []  # descendants a stop left alive on purpose, ended at the suite's end
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v60_store', mods / 'control_store.py')
        L = load('v60_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = getattr(RES, 'ACC', None)
        E = getattr(L, 'ENGINES', {}).get('claude_code')  # the receiver's own load of the engine module
        HELPER = load('v60_helper', mods / 'accounts.py')
        EL = load('v60_eligibility', mods / 'control_eligibility.py')
        SIG = load('v60_signer', mods / 'control_signer.py')
        GP = load('v60_git', mods / 'git_process.py')
        CL = load('v60_clone', mods / 'control_clone.py')
        CT = load('v60_containment', mods / 'control_containment.py')
        X = getattr(L, 'ENGINES', {}).get('codex')  # the receiver's own load of the Codex engine module
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-60', 'repository-60', 'builder-60', 'linux-host-60'
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
        member('floor-service', 'service', ['result_acceptance'])
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        # The owner's Claude Code accounts, over profiles the local helper prepares.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign) if ACC else None
        helper_root = base / 'helper'
        profiles = {}
        for account, provider in (('acct-60a', 'claude_code'), ('acct-60b', 'claude_code'), ('acct-60x', 'codex')):
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider))
            profiles[account] = (record or {}).get('config_dir')
            fields, _ = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields and accounts is not None:
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=time.time())

        def roles_only(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            return 'reservation_service' in (json.loads(row[0]) if row else {}).get('roles', [])
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=getattr(RES, 'service_authority', roles_only), signer='runner',
                                        sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        for account in profiles:
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        projects = set()

        def project(name, **caps):
            if name not in projects:
                projects.add(name)
                put('project:' + name, 'project', dict(name=name))
                reservations.configure('policy/' + name, 'project', name, dict(BIG, **caps), now=time.time())
            return name

        def admitted(unit, proj='journey-60', **caps):
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

        # The source repository, bound to the store so the clone provisioner reads it.
        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'README').write_text('adapter source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # The fake engine: it records how it was started and what the store held for its invocation, then
        # prints what its packet scripts. Its store, marker directory and domain are written into it, since
        # its argv is exactly the qualified flags.
        markers = base / 'markers'
        markers.mkdir()
        fake = '''#!%(python)s -B
import json, os, signal, sqlite3, subprocess, sys, time
from pathlib import Path
store, markers, domain = %(store)r, Path(%(markers)r), %(domain)r
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
key = 'reservation:invocation:' + json.dumps([domain, 'invocation/' + dispatch], separators=(',', ':'))
try:
    db = sqlite3.connect('file:%%s?mode=ro' %% store, uri=True, timeout=10)
    row = db.execute('SELECT data FROM entities WHERE id=?', (key,)).fetchone()
    seen = json.loads(row[0]) if row else None
    db.close()
except Exception as error:
    seen = {'error': repr(error)}
def start(pid):
    stat = open('/proc/%%d/stat' %% pid).read()
    return stat[stat.rindex(')') + 2:].split()[19]
own = {'pid': os.getpid(), 'start': start(os.getpid()), 'sid': os.getsid(0), 'pgid': os.getpgid(0),
       'dispatch': dispatch, 'argv': sys.argv, 'cwd': os.getcwd(), 'invocation': seen,
       'env': {k: os.environ.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'DISABLE_AUTOUPDATER', 'VELDO_ACCOUNT',
                                              'VELDO_CLONE')},
       'cgroup': next((l[3:] for l in open('/proc/self/cgroup').read().splitlines() if l.startswith('0::')), None),
       'names': sorted(os.environ)}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
out = open(markers / ('%%d.out' %% os.getpid()), 'wb')
children = []
for step in payload.get('script') or []:
    if 'line' in step or 'raw' in step:
        data = (json.dumps(step['line']) + chr(10)).encode() if 'line' in step else step['raw'].encode('latin-1')
        out.write(data)
        out.flush()
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    elif 'sleep' in step:
        time.sleep(step['sleep'])
    elif 'ignore_term' in step:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    elif 'probe' in step:
        try:
            with open(step['probe'], 'x') as handle:
                handle.write('written by the worker')
            outcome = 'written'
        except OSError as error:
            outcome = type(error).__name__
        with open(markers / ('%%d.probe' %% os.getpid()), 'a') as handle:
            handle.write(json.dumps([step['probe'], outcome]) + chr(10))
    elif 'descendant' in step:
        # The descendant says it is ready once its SIGTERM disposition is set, so a stop never races its start.
        body = ('import sys, time; open(sys.argv[1], "w").close(); time.sleep(%%d)' if step.get('cooperative') else
                'import signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); open(sys.argv[1], "w").close(); '
                'time.sleep(%%d)')
        ready = markers / ('ready-%%d-%%d' %% (os.getpid(), len(children)))
        child = subprocess.Popen([sys.executable, '-c', body %% step['descendant'], str(ready)], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=bool(step.get('escape')))
        until = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < until:
            time.sleep(0.01)
        children.append({'pid': child.pid, 'start': start(child.pid), 'escape': bool(step.get('escape'))})
        (markers / ('%%d.children' %% os.getpid())).write_text(json.dumps(children))
    elif 'signal' in step:
        out.close()
        os.kill(os.getpid(), step['signal'])
        time.sleep(5)
out.close()
(markers / ('%%d.done' %% os.getpid())).write_text('done')
sys.exit(payload.get('code', 0))
''' % {'python': sys.executable, 'store': str(db), 'markers': str(markers), 'domain': DOMAIN}
        # The installer's layout: ~/.local/share/claude/versions/<version>, here a directory of this run's.
        versions = base / 'home' / '.local' / 'share' / 'claude' / 'versions'
        versions.mkdir(parents=True)
        (versions / VERSION).write_text(fake)
        (versions / VERSION).chmod(0o755)
        FAKE_SHA = file_sha(versions / VERSION)
        # This installation's qualification record: the qualified flags and settings of the version, and the
        # digest of the executable this suite installed as that version. Built from the extracted tables,
        # never from the production record (the shipped record is checked on its own row).
        errors = FORMATS['events']['result/error']['fields']['subtype']['values']
        test_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {
            VERSION: {'sha256': FAKE_SHA, 'flags': ['--print', '--output-format', 'stream-json', '--verbose'],
                      'environment': {'DISABLE_AUTOUPDATER': '1'},
                      'terminal_protocol': {'output': 'stream-json', 'terminal_event': 'result',
                                            'success_subtype': 'success', 'error_subtypes': errors}}}}
        (mods / 'runtime').mkdir()
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps(test_record, indent=1))
        QUALIFIED = test_record['versions'][VERSION]
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        pinned = factory / 'engines' / 'claude_code' / VERSION
        pinned_binding, pin_error = attempt(lambda: E.pin(VERSION, versions=str(versions), state_root=str(factory)))
        pin_mode = (os.lstat(pinned).st_mode & 0o777) if pinned.exists() else None

        # Codex for the contained rows (VELDO-0061's adapter on the same receiver path): the same fake laid out
        # as its vendor package and qualified by the production writer; a copy with one byte changed after
        # qualification is the pin's refusal case.
        def codex_package(name, extra=b''):
            root = base / 'packages' / name
            vendored = root / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
            vendored.parent.mkdir(parents=True)
            (root / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
            vendored.write_bytes(fake.encode() + extra)
            vendored.chmod(0o755)
            return vendored
        CODEX_BIN = codex_package('codex')
        CODEX_CHANGED = codex_package('codex-changed')
        codex_qualification = base / 'codex-qualification.json'
        codex_record, codex_error = attempt(lambda: X.qualification(str(CODEX_BIN)))
        if codex_record is not None:
            codex_qualification.write_text(json.dumps(codex_record))
        with open(CODEX_CHANGED, 'ab') as handle:
            handle.write(b'# changed after it was qualified\n')
        CODEX_FLAGS = list(getattr(X, 'FLAGS', ()) or ())
        # The profile of the contained launch: its systemd-run records every spawn by its dispatch, then becomes
        # the real one, so a spawn for a refused dispatch is seen.
        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        shim = base / 'systemd-run'
        shim.write_text('#!/bin/sh\nprintf %%s "$VELDO_DISPATCH_ID" > "%s/spawn-$$"\nexec %s "$@"\n'
                        % (markers, real_systemd_run))
        shim.chmod(0o755)
        GRACE = 0.4
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': GRACE, 'kill_grace_seconds': GRACE, 'systemd_run': str(shim)}

        receipts = state / 'receipts'
        artifacts = state / 'artifacts'
        config = base / 'receiver.json'
        # Every process the receiver spawns first writes a spawn marker naming its dispatch, then execs the
        # trusted wrapper (the same pid): a spawn is recorded even when its engine never runs.
        spawn = ['/bin/sh', '-c', 'printf %s "$VELDO_DISPATCH_ID" > "$0/spawn-$$"; exec "$@"', str(markers)]
        wrapper = spawn + [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '--']
        pinned_exe = {'version': VERSION}
        receiver_config = {
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(receipts), 'artifacts': str(artifacts), 'state_root': str(factory),
            'adapters': {
                'claude': {'identity': 'reported', 'engine': 'claude_code', 'executable': pinned_exe, 'argv': wrapper},
                'claude-clone': {'identity': 'reported', 'engine': 'claude_code', 'executable': pinned_exe,
                                 'argv': wrapper + entering},
                'claude-unknown': {'identity': 'reported', 'engine': 'claude_code', 'executable': {'version': '9.9.9'},
                                   'argv': wrapper},
                'claude-updater-on': {'identity': 'reported', 'engine': 'claude_code', 'executable': pinned_exe,
                                      'environment': {'DISABLE_AUTOUPDATER': '0'}, 'argv': wrapper},
                # The local Linux contained launch: no transport, the receiver starts its trusted wrapper in the
                # dispatch's own scope, and the adapter's argv is the clone entrance (then the engine).
                'claude-contained': {'engine': 'claude_code', 'executable': pinned_exe, 'argv': entering},
                'claude-contained-unknown': {'engine': 'claude_code', 'executable': {'version': '9.9.9'},
                                             'argv': entering},
                'codex-contained': {'engine': 'codex', 'executable': str(CODEX_BIN),
                                    'qualification': str(codex_qualification),
                                    'argv': entering + [str(CODEX_BIN)] + CODEX_FLAGS},
                'codex-contained-changed': {'engine': 'codex', 'executable': str(CODEX_CHANGED),
                                            'qualification': str(codex_qualification),
                                            'argv': entering + [str(CODEX_CHANGED)] + CODEX_FLAGS}},
            'profile': profile}
        config.write_text(json.dumps(receiver_config))
        stateless = base / 'receiver-stateless.json'
        stateless.write_text(json.dumps(dict(receiver_config, state_root=None)))
        CONFIGURATION = {'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        clones = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)])
        provisioned = {}
        using = [config]

        def invoke(contract):
            if contract['capability']['adapter'] == 'claude-clone' or '-contained' in contract['capability']['adapter']:
                provisioned[contract['dispatch_id']] = clones.create(contract)
            launch = L.invoke(using[0], contract, dispatches, accept_seconds=30)
            if '-contained' in contract['capability']['adapter']:
                contained_launches.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]

        # Every step a fake was scripted to print, for the format rows: ('line', event) or
        # ('perturbed', kind, conforming source event, bytes printed).
        printed_steps = []

        def job(adapter, script, code=0, deadline=40, resume=None):
            for step in script if not adapter.startswith('codex') else ():
                if 'line' in step:
                    printed_steps.append(('line', step['line']))
                elif 'raw' in step:
                    printed_steps.append(('perturbed', step['kind'], step['source'], step['raw']))
            payload = {'task': 'work the unit', 'script': [{k: v for k, v in s.items() if k not in ('kind', 'source')}
                                                          for s in script], 'code': code}
            if resume:
                payload['resume'] = resume
            return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

        def run(account, unit, adapter, script, wait=True, **kwargs):
            launch = runner(account).submit(unit, 'build', **job(adapter, script, **kwargs))
            record = runner(account).wait(launch) if wait else None
            return launch, record

        def engine_markers(dispatch_id):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    data['done'] = (markers / ('%d.done' % data['pid'])).exists()
                    out = markers / ('%d.out' % data['pid'])
                    data['printed'] = out.read_bytes() if out.exists() else b''
                    kids = markers / ('%d.children' % data['pid'])
                    data['children'] = json.loads(kids.read_text()) if kids.exists() else []
                    found.append(data)
            return found

        def marker_wait(dispatch_id, timeout=15.0, children=0):
            # A dispatch that ended or was refused writes no more markers: a broken build fails fast.
            end = time.time() + timeout
            while time.time() < end:
                found = engine_markers(dispatch_id)
                if found and len(found[0]['children']) >= children:
                    return found[0]
                if rec(dispatch_id).get('state') in ('refused', 'exited', 'unknown'):
                    return found[0] if found else {}
                time.sleep(0.02)
            return {}

        def spawned(dispatch_id, timeout=0.0):
            end = time.time() + timeout
            while True:
                found = [p for p in sorted(markers.glob('spawn-*')) if p.read_text() == dispatch_id]
                if found or time.time() >= end:
                    return len(found)
                time.sleep(0.02)

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def invocation(dispatch_id):
            found = entity(RES.entity('invocation', [DOMAIN, 'invocation/' + dispatch_id]))
            return (found or {}).get('data') or {}

        def journal_seq(prefix):
            row = writer.execute('SELECT MIN(seq) FROM journal WHERE substr(command_id, 1, ?) = ?',
                                 (len(prefix), prefix)).fetchone()
            return row[0] if row else None

        def artifact_file(dispatch_id):
            path = artifacts / (hashlib.sha256(('invocation/' + dispatch_id).encode()).hexdigest() + '.json')
            if not path.exists():
                return None, None
            return json.loads(path.read_text()), (path.stat().st_mode & 0o777)

        def returned(launch):
            # The artifact document the receiver reported to the runner, read from the file its report names
            # and checked against the report's digest, verdict and completeness (none from a tree without
            # this work, or when the report does not match its file).
            report = getattr(launch, 'artifact', None) or {}
            path = Path(report.get('path') or '/nonexistent')
            if not path.is_file():
                return None
            data = path.read_bytes()
            found = json.loads(data)
            if ('sha256:' + hashlib.sha256(data).hexdigest() != report.get('digest')
                    or report.get('verdict') != found.get('verdict') or report.get('complete') != found.get('complete')):
                return None
            return found

        def slot_outcome(account, dispatch_id):
            return (runner(account).retirements.entries.get(dispatch_id) or {}).get('outcome')

        def alive(pid, start):
            try:
                stat = Path('/proc/%d/stat' % pid).read_text()
            except OSError:
                return False
            fields = stat[stat.rindex(')') + 2:].split()
            return fields[19] == start and fields[0] != 'Z'

        def nothing_ran(dispatch_id):
            return not engine_markers(dispatch_id) and not spawned(dispatch_id) and not invocation(dispatch_id)

        # Stream lines in the shape Claude Code 2.1.281 prints (the format row checks each one).
        SESSION = 'session-60-' + os.urandom(4).hex()

        def c_usage(inp, out, read=0, create=0):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': create,
                    'cache_read_input_tokens': read,
                    'cache_creation': {'ephemeral_5m_input_tokens': create, 'ephemeral_1h_input_tokens': 0},
                    'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}, 'service_tier': 'standard'}

        def c_init():
            return {'line': {'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'claude_code_version': VERSION,
                             'cwd': '/work', 'tools': ['Read', 'Edit', 'Bash'], 'mcp_servers': [],
                             'model': 'configured-model', 'permissionMode': 'default', 'slash_commands': [],
                             'output_style': 'default', 'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION}}

        def c_msg(mid, inp, out):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()),
                             'session_id': SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'configured-model',
                                         'content': [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out)}}}

        def c_result(inp, out, turns, text='done'):
            return {'line': {
                'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False,
                'num_turns': turns, 'result': text, 'stop_reason': 'end_turn', 'total_cost_usd': 0,
                'usage': c_usage(inp, out),
                'modelUsage': {'configured-model': {'inputTokens': inp, 'outputTokens': out, 'cacheReadInputTokens': 0,
                                                    'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                                    'contextWindow': 200000, 'maxOutputTokens': 32000}},
                'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': SESSION}}

        def c_error(subtype, inp, out, turns):
            return {'line': {
                'type': 'result', 'subtype': subtype, 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': True,
                'num_turns': turns, 'stop_reason': None, 'total_cost_usd': 0, 'usage': c_usage(inp, out),
                'modelUsage': {'configured-model': {'inputTokens': inp, 'outputTokens': out, 'cacheReadInputTokens': 0,
                                                    'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                                    'contextWindow': 200000, 'maxOutputTokens': 32000}},
                'permission_denials': [], 'errors': ['the run ended at its turn limit'], 'uuid': str(uuid.uuid4()),
                'session_id': SESSION}}

        def c_rate(status, reset, kind='five_hour'):
            return {'line': {'type': 'rate_limit_event', 'rate_limit_info': {'status': status, 'rateLimitType': kind,
                                                                             'resetsAt': int(reset)},
                             'uuid': str(uuid.uuid4()), 'session_id': SESSION}}

        # The perturbations, each of a conforming line: its bytes cut short, or a field it requires removed.
        def truncated(step):
            text = json.dumps(step['line'])
            return {'raw': text[:len(text) // 2] + '\n', 'kind': 'truncated', 'source': step['line']}

        def not_json(step):
            return {'raw': 'Error: ' + json.dumps(step['line'])[:40] + '\n', 'kind': 'not_json', 'source': step['line']}

        def without(step, field):
            event = {k: v for k, v in step['line'].items() if k != field}
            return {'raw': json.dumps(event) + '\n', 'kind': 'without:' + field, 'source': step['line']}

        def normal(inp=3, out=2, text='done'):
            return [c_init(), c_msg('m-%s' % os.urandom(3).hex(), inp, out), c_result(inp, out, 1, text)]

        # AC1: the lifecycle, from the installed adapter registration, driven in an isolated clone.
        normal_run = {}
        with region('lifecycle/registration', 'lifecycle/pinned-launch'):
            text = 'the unit is done ' + os.urandom(4).hex()
            unit = admitted('VELDO-6001-clone')
            launch, record = run('acct-60a', unit, 'claude-clone', normal(text=text))
            own = engine_markers(launch.dispatch_id)
            own = own[0] if len(own) == 1 else {}
            normal_run.update(launch=launch, record=record or {}, own=own, text=text, unit=unit)
            argv = own.get('argv') or []
            handle = provisioned.get(launch.dispatch_id)
            work = clones._paths(handle)['work'] if handle is not None else None
            head = GP.run(['git', '-C', str(work), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() \
                if work else None
            env = own.get('env') or {}
            info = os.lstat(pinned) if pinned.exists() else None
            check('lifecycle/pinned-launch', 'the engine ran once, to its end, from the pinned copy under the factory '
                  'state root: a regular file whose digest is the qualified one, not the installer\'s versioned file '
                  'and not a link [%s, %s]' % (argv[:1], pin_error),
                  (record or {}).get('state') == 'exited' and own.get('done') is True
                  and argv[:1] == [str(pinned)] and info is not None and not os.path.islink(pinned)
                  and (info.st_mode & 0o170000) == 0o100000 and file_sha(pinned) == QUALIFIED['sha256'] == FAKE_SHA
                  and str(pinned) != str(versions / VERSION) and str(factory) in str(pinned))
            check('lifecycle/pinned-launch', 'its arguments are exactly the version\'s qualified flags [%s]' % argv[1:],
                  argv[1:] == QUALIFIED['flags'])
            check('lifecycle/pinned-launch', 'its environment turns the updater off and carries the recorded account\'s '
                  'profile [%s, %s]' % (env.get('DISABLE_AUTOUPDATER'), env.get('CLAUDE_CONFIG_DIR')),
                  env.get('DISABLE_AUTOUPDATER') == '1' and env.get('CLAUDE_CONFIG_DIR') == profiles['acct-60a'])
            check('lifecycle/pinned-launch', 'it ran in its isolated clone, at the accepted commit [%s, %s]'
                  % (own.get('cwd'), head),
                  work is not None and own.get('cwd') == str(work) and env.get('VELDO_CLONE') == str(work)
                  and head == ((record or {}).get('contract') or {}).get('source', {}).get('commit'))

            # Every lifecycle operation of the registration, each observed on this run or the stop run below.
            lifecycle = list(((getattr(E, 'REGISTRATION', None) or {}).get('lifecycle') or {}))
            accepted_at = journal_seq('dispatch/accept/%s/' % launch.dispatch_id)
            ran_at = journal_seq('dispatch/run/%s/' % launch.dispatch_id)
            call = invocation(launch.dispatch_id)
            stored, mode = artifact_file(launch.dispatch_id)
            normal_run['observed'] = {
                'launch': spawned(launch.dispatch_id) == 1 and argv[:1] == [str(pinned)],
                'accept': None not in (accepted_at, ran_at) and accepted_at < ran_at,
                'observe': call.get('state') == 'settled' and bool(call.get('reports')),
                'exit': (record or {}).get('state') == 'exited' and ((record or {}).get('termination') or {}).get(
                    'returncode') == 0,
                'artifacts': stored is not None and stored == returned(launch) and mode == 0o600}

        # AC2 on the same run: the artifact of a complete invocation.
        with region('artifact/complete'):
            launch, record, own = normal_run['launch'], normal_run['record'], normal_run['own']
            artifact = returned(launch) or {}
            stored, mode = artifact_file(launch.dispatch_id)
            lines = [line for line in (own.get('printed') or b'').split(b'\n') if line]
            result_line = next((line for line in lines if json.loads(line).get('type') == 'result'), None)
            termination = record.get('termination') or {}
            call = invocation(launch.dispatch_id)
            check('artifact/complete', 'a zero exit with its result: the artifact is complete, its terminal record '
                  'the result the engine printed, bound to its line and the receiver\'s own output digest [%s, %s]'
                  % (artifact.get('verdict'), artifact.get('problems')),
                  artifact.get('verdict') == 'complete' and artifact.get('complete') is True
                  and (artifact.get('terminal') or {}).get('subtype') == 'success'
                  and (artifact.get('terminal') or {}).get('result_digest') == sha(normal_run['text'].encode())
                  and result_line is not None and artifact.get('terminal_receipt') == sha(result_line)
                  and (artifact.get('stream') or {}).get('output_digest') == termination.get('output_digest')
                  and (artifact.get('stream') or {}).get('lines') == len(lines) == 3)
            check('artifact/complete', 'the artifact is kept 0600 in the artifacts directory, the same one the runner was '
                  'given, bound to the dispatch, invocation and pinned digest [%s]' % mode,
                  stored == artifact and mode == 0o600 and artifact.get('dispatch_id') == launch.dispatch_id
                  and artifact.get('invocation') == 'invocation/' + launch.dispatch_id
                  and (artifact.get('executable') or {}).get('sha256') == FAKE_SHA)
            check('artifact/complete', 'the invocation and the worker slot are completed [%s, %s]'
                  % (call.get('outcome'), slot_outcome('acct-60a', launch.dispatch_id)),
                  call.get('outcome') == 'completed' and call.get('state') == 'settled'
                  and slot_outcome('acct-60a', launch.dispatch_id) == 'completed')

        # AC1: a changed digest, an unknown version, a link, a missing copy, no state root and a configured
        # updater are each refused before acceptance: nothing spawned, nothing reserved.
        with region('pin/unexpected-launch'):
            cases = []
            check('pin/unexpected-launch', 'the pinned copy exists to be changed [%s]' % pin_error, pinned.is_file())
            if not pinned.is_file():
                pinned.parent.mkdir(parents=True, exist_ok=True)
                pinned.write_text(fake)  # so each case below runs and reds by its own assertion
            original = pinned.read_bytes()
            pinned.chmod(0o755)
            with open(pinned, 'ab') as handle:
                handle.write(b'# changed after it was pinned\n')
            launch, record = run('acct-60a', admitted('VELDO-6002-changed'), 'claude', normal())
            cases.append(('a pinned copy whose digest changed', launch.dispatch_id, record,
                          'binding_mismatch:engine_digest'))
            pinned.write_bytes(original)
            launch, record = run('acct-60a', admitted('VELDO-6002-restored'), 'claude', normal())
            check('pin/unexpected-launch', 'the copy restored to its qualified bytes launches again [%s]'
                  % (record or {}).get('state'),
                  (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1)
            launch, record = run('acct-60a', admitted('VELDO-6002-unknown'), 'claude-unknown', normal())
            cases.append(('an unknown version', launch.dispatch_id, record, 'invalid_input:engine_version:9.9.9'))
            moved = factory / 'moved'
            os.replace(pinned, moved)
            os.symlink(str(versions / VERSION), str(pinned))  # the qualified bytes, reached through a link
            launch, record = run('acct-60a', admitted('VELDO-6002-link'), 'claude', normal())
            cases.append(('a pinned path that is a link to the qualified bytes', launch.dispatch_id, record,
                          'binding_mismatch:engine_executable'))
            os.unlink(pinned)
            launch, record = run('acct-60a', admitted('VELDO-6002-missing'), 'claude', normal())
            cases.append(('a missing pinned copy', launch.dispatch_id, record, 'missing_evidence:engine_executable'))
            os.replace(moved, pinned)
            using[0] = stateless
            try:
                launch, record = run('acct-60a', admitted('VELDO-6002-stateless'), 'claude', normal())
            finally:
                using[0] = config
            cases.append(('a receiver naming no state root', launch.dispatch_id, record,
                          'missing_authority:engine_state_root'))
            launch, record = run('acct-60a', admitted('VELDO-6002-updater'), 'claude-updater-on', normal())
            cases.append(('an adapter configuring the updater on', launch.dispatch_id, record,
                          'invalid_input:adapter_environment:DISABLE_AUTOUPDATER'))
            for label, dispatch_id, record, expected in cases:
                check('pin/unexpected-launch', '%s: refused by name before acceptance, nothing spawned or reserved '
                      '[%s]' % (label, (record or {}).get('refusal')),
                      (record or {}).get('refusal') == expected and rec(dispatch_id).get('state') == 'refused'
                      and nothing_ran(dispatch_id))

        # AC1: the pin itself copies only the qualified bytes, never through a link.
        with region('pin/copy'):
            check('pin/copy', 'the pin copied the installer\'s versioned file under the state root: a new regular '
                  'file, read and execute only, of the qualified digest [%s, %s]' % (pinned_binding, pin_error),
                  isinstance(pinned_binding, dict) and pinned_binding.get('path') == str(pinned)
                  and pinned_binding.get('sha256') == FAKE_SHA and not os.path.islink(pinned)
                  and pin_mode == 0o555
                  and os.lstat(pinned).st_ino != os.lstat(versions / VERSION).st_ino)
            other = base / 'other-versions'
            other.mkdir()
            (other / VERSION).write_text(fake + '# another build\n')
            elsewhere = state / 'factory-other'
            elsewhere.mkdir(mode=0o700)
            _, changed = attempt(lambda: E.pin(VERSION, versions=str(other), state_root=str(elsewhere)))
            left = sorted(p.name for p in (elsewhere / 'engines' / 'claude_code').glob('*')) \
                if (elsewhere / 'engines' / 'claude_code').is_dir() else []
            check('pin/copy', 'a versioned file of another digest is refused by name and nothing is left in place '
                  '[%s, %s]' % (changed, left), changed == 'binding_mismatch:engine_digest' and not left)
            linked = base / 'linked-versions'
            linked.mkdir()
            os.symlink(str(versions / VERSION), str(linked / VERSION))
            _, through = attempt(lambda: E.pin(VERSION, versions=str(linked), state_root=str(elsewhere)))
            _, unknown = attempt(lambda: E.pin('9.9.9', versions=str(versions), state_root=str(elsewhere)))
            check('pin/copy', 'a versioned path that is a link (the auto-updating link\'s shape) and an unqualified '
                  'version are refused by name [%s, %s]' % (through, unknown),
                  through == 'binding_mismatch:engine_source' and unknown == 'invalid_input:engine_version:9.9.9'
                  and not (elsewhere / 'engines' / 'claude_code' / VERSION).exists())

        # AC1: the qualification record this repository ships for the real 2.1.281.
        with region('pin/shipped-qualification'):
            shipped_path = ROOT / 'engine' / 'runtime' / 'claude-qualification.json'
            installed_path = ROOT / '.veldo' / 'runtime' / 'claude-qualification.json'
            shipped = json.loads(shipped_path.read_text()) if shipped_path.is_file() else {}
            entry = (shipped.get('versions') or {}).get(VERSION) or {}
            check('pin/shipped-qualification', 'the canonical record and its installed copy are byte-identical, and '
                  'the scaffold lays it beside the engine module [%s]' % shipped_path.is_file(),
                  shipped_path.is_file() and installed_path.is_file()
                  and shipped_path.read_bytes() == installed_path.read_bytes()
                  and ('runtime/claude-qualification.json', '.veldo/runtime/claude-qualification.json')
                  in [tuple(a) for a in getattr(load('v60_scaffold', PRODUCTION['init_scaffold.py']),
                                                '_RUNTIME_ASSETS', [])])
            check('pin/shipped-qualification', 'its 2.1.281 digest is the installed binary\'s, as both extractions read '
                  'it [%s]' % entry.get('sha256'),
                  entry.get('sha256') == FORMATS['sha256'] == OPTIONS['sha256'] and FORMATS['version'] == VERSION)
            flags = entry.get('flags') or []
            declared = OPTIONS['options']
            check('pin/shipped-qualification', 'its flags are the binary\'s own: each an option of the main command, '
                  'the output format one of its choices, stream JSON with print mode carrying verbose, and the updater '
                  'switch one the binary reads [%s]' % flags,
                  flags == QUALIFIED['flags'] and all(f in declared for f in flags if f.startswith('-'))
                  and flags[flags.index('--output-format') + 1] in declared['--output-format']['choices']
                  and '--print' in flags and '--verbose' in flags
                  and set(entry.get('environment') or {}) == {'DISABLE_AUTOUPDATER'} <= set(OPTIONS['environment']))
            rate = FORMATS['events']['rate_limit_event']['fields']['rate_limit_info']['fields']['rateLimitType']['values']
            check('pin/shipped-qualification', 'its terminal protocol, login and reported windows are the binary\'s '
                  '[%s]' % entry.get('terminal_protocol'),
                  (entry.get('terminal_protocol') or {}).get('error_subtypes') == errors
                  and (entry.get('terminal_protocol') or {}).get('success_subtype') == 'success'
                  and (entry.get('authentication') or {}).get('mode') == 'subscription'
                  and 'none' in FORMATS['events']['system/init']['fields']['apiKeySource']['values']
                  and entry.get('rate_limit_windows') == rate
                  and set(entry.get('usage_units') or ()) == {'invocations', 'wall_seconds', 'tokens', 'messages'})

        # AC2: live exits and perturbed stream bytes, each through the production decoder in the receiver.
        exit_records = {}

        def artifact_of(account, name, script, code=0, **caps):
            proj = project('p-' + name, **caps) if caps else 'journey-60'
            launch, record = run(account, admitted('VELDO-6003-' + name, proj), 'claude', script, code=code)
            return launch, record or {}, returned(launch) or {}, invocation(launch.dispatch_id)

        with region('artifact/missing-result'):
            script = normal()
            launch, record, artifact, call = artifact_of('acct-60a', 'no-result', script[:2], tokens=10 ** 6)
            exit_records['no-result'] = (launch, record)
            nxt, nrecord = run('acct-60a', admitted('VELDO-6003-no-result-next', 'p-no-result'), 'claude', normal())
            check('artifact/missing-result', 'a zero exit with its terminal record removed is not a completion: the '
                  'artifact says missing_result [%s, %s, %s]' % (record.get('state'), (record.get('termination') or {})
                                                                .get('returncode'), artifact.get('verdict')),
                  record.get('state') == 'exited' and (record.get('termination') or {}).get('returncode') == 0
                  and artifact.get('verdict') == 'missing_result' and artifact.get('complete') is False
                  and artifact.get('terminal') is None)
            check('artifact/missing-result', 'its invocation and worker slot are failed, never completed [%s, %s]'
                  % (call.get('outcome'), slot_outcome('acct-60a', launch.dispatch_id)),
                  call.get('outcome') == 'failed' and slot_outcome('acct-60a', launch.dispatch_id) == 'failed')
            check('artifact/missing-result', 'its usage stays unknown and its reservation retained: the next invocation '
                  'under the same cap is refused, nothing launched [%s, %s]' % (call.get('unknown'),
                                                                               (nrecord or {}).get('refusal')),
                  call.get('state') == 'unknown' and 'tokens' in (call.get('unknown') or [])
                  and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                  and nothing_ran(nxt.dispatch_id))

        with region('artifact/exits'):
            outcomes = []
            for name, script, code, verdict, problems in (
                    ('nonzero', normal(), 3, 'nonzero_exit', ['nonzero_exit']),
                    ('signal', normal()[:2] + [{'signal': int(signal.SIGABRT)}], 0, 'signal', ['signal', 'missing_result']),
                    ('error-result', [c_init(), c_msg('m-err', 2, 2), c_error('error_max_turns', 2, 2, 1)], 1,
                     'nonzero_exit', ['nonzero_exit', 'engine_error']),
                    ('error-result-zero', [c_init(), c_msg('m-err0', 2, 2), c_error('error_during_execution', 2, 2, 1)],
                     0, 'engine_error', ['engine_error'])):
                launch, record, artifact, call = artifact_of('acct-60a', name, script, code=code)
                termination = record.get('termination') or {}
                outcomes.append((name, termination.get('returncode'), termination.get('signal'), artifact.get('verdict'),
                                 call.get('outcome')))
                check('artifact/exits', '%s: the artifact is %s with %s, the invocation and slot failed [%s]'
                      % (name, verdict, problems, outcomes[-1]),
                      record.get('state') == 'exited' and artifact.get('verdict') == verdict
                      and artifact.get('problems') == problems and artifact.get('complete') is False
                      and call.get('outcome') == 'failed' and slot_outcome('acct-60a', launch.dispatch_id) == 'failed'
                      and (termination.get('signal') == int(signal.SIGABRT) if name == 'signal'
                           else termination.get('returncode') == code))
                if name.startswith('error-result'):
                    check('artifact/exits', '%s: the terminal record is the error result, its subtype and errors kept '
                          '[%s]' % (name, artifact.get('terminal')),
                          (artifact.get('terminal') or {}).get('subtype') == script[-1]['line']['subtype']
                          and (artifact.get('terminal') or {}).get('errors') == script[-1]['line']['errors']
                          and (artifact.get('terminal') or {}).get('is_error') is True)

        with region('artifact/malformed-output'):
            for name, bad in (('truncated', truncated(c_msg('m-cut', 5, 5))), ('not-json', not_json(c_init()))):
                script = [c_init(), bad, c_msg('m-%s' % name, 2, 2), c_result(2, 2, 1)]
                launch, record, artifact, call = artifact_of('acct-60a', 'malformed-' + name, script)
                check('artifact/malformed-output', '%s line in an otherwise complete stream with a zero exit: the '
                      'artifact is malformed_output, one of four lines, the result still decoded [%s, %s]'
                      % (name, artifact.get('verdict'), artifact.get('stream')),
                      record.get('state') == 'exited' and artifact.get('verdict') == 'malformed_output'
                      and artifact.get('problems') == ['malformed_output']
                      and (artifact.get('stream') or {}).get('malformed') == 1
                      and (artifact.get('stream') or {}).get('lines') == 4
                      and (artifact.get('terminal') or {}).get('subtype') == 'success'
                      and call.get('outcome') == 'failed')

        # AC2 at the dispatch authority: the exit record binds the artifact's verdict and digest, and the
        # one completion gate (control_dispatch.completed) reads it for the runner and the floor alike.
        with region('artifact/exit-record'):
            cases = (('complete', normal_run['launch'], normal_run['record'], 'complete', True),
                     ('missing result', exit_records['no-result'][0], exit_records['no-result'][1], 'missing_result', False))
            for label, launch, record, verdict, complete in cases:
                report = getattr(launch, 'artifact', None) or {}
                bound = rec(launch.dispatch_id).get('artifact')
                check('artifact/exit-record', '%s: the exit record binds the artifact the runner was given, its verdict '
                      '%s, completeness and digest, the digest of the file the report names [%s]' % (label, verdict, bound),
                      bound == {'verdict': verdict, 'complete': complete, 'digest': report.get('digest')}
                      and returned(launch) is not None and (returned(launch) or {}).get('verdict') == verdict)
                check('artifact/exit-record', '%s: the completion gate reads that record as %s [%s]'
                      % (label, 'complete' if complete else 'not complete', (record.get('termination') or {})),
                      getattr(D, 'completed', lambda r: None)(rec(launch.dispatch_id)) is complete
                      and (rec(launch.dispatch_id).get('termination') or {}).get('returncode') == 0)

        # The floor: a zero exit with its terminal record removed is not a completed build, and the floor
        # refuses to accept it, while the complete run's build passes the dispatch check (then lacks proof).
        with region('floor/missing-result'):
            DSP = load('v60_dispatch', mods / 'dispatch.py')
            floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(src),
                                       projections=str(base / 'projections'), principal='floor-service',
                                       signer='floor-service', sign=sign)
            commit = GP.run(['git', '-C', str(src), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()

            def accept_build(launch):
                # The claim the build ran under, as its accepted contract binds it.
                try:
                    floor.accept_build(launch.contract['unit'], commit=commit, gate={'green': True, 'detail': 'suite'},
                                       holder=HOLDER, generation=(launch.contract.get('claim') or {}).get('generation'))
                    return 'accepted'
                except DSP.FloorRefused as error:
                    return error.code
            missing_launch, missing_record = exit_records['no-result']
            missing = accept_build(missing_launch)
            control = accept_build(normal_run['launch'])
            check('floor/missing-result', 'a build dispatch that exited 0 with its terminal record removed: the floor '
                  'refuses to accept the build, for want of a completed build dispatch [%s, %s]'
                  % ((missing_record.get('termination') or {}).get('returncode'), missing),
                  missing_record.get('state') == 'exited' and (missing_record.get('termination') or {}).get('returncode') == 0
                  and missing == 'missing_evidence:build_dispatch' and floor.record(missing_launch.contract['unit']) is None)
            check('floor/missing-result', 'control: the complete run\'s build dispatch passes the floor\'s dispatch check '
                  'and is refused next for its absent proof [%s]' % control,
                  control == 'missing_evidence:proof/absent')
            floor.close()

        with region('artifact/missing-usage'):
            script = normal()
            script[-1] = without(script[-1], 'modelUsage')
            launch, record, artifact, call = artifact_of('acct-60b', 'no-usage', script, tokens=10 ** 6)
            nxt, nrecord = run('acct-60b', admitted('VELDO-6003-no-usage-next', 'p-no-usage'), 'claude', normal())
            check('artifact/missing-usage', 'a result without its usage: the artifact keeps the terminal record, and '
                  'the invocation\'s tokens stay unknown with its reservation retained, the next invocation refused '
                  '[%s, %s, %s]' % (artifact.get('verdict'), call.get('unknown'), (nrecord or {}).get('refusal')),
                  (artifact.get('terminal') or {}).get('subtype') == 'success' and call.get('state') == 'unknown'
                  and call.get('unknown') == ['tokens'] and call.get('charge', {}).get('messages') == 1
                  and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                  and nothing_ran(nxt.dispatch_id))

        # AC3: an ordinary stop through the wrapper, with a real descendant of the worker in its session.
        with region('stop/requested', 'lifecycle/registration'):
            proj = project('p-stop', tokens=10 ** 6)
            launch, _ = run('acct-60b', admitted('VELDO-6004-stop', proj), 'claude',
                            [c_init(), c_msg('m-stop', 4, 4), {'descendant': 60}, {'sleep': 30}] + normal()[1:],
                            wait=False)
            own = marker_wait(launch.dispatch_id, children=1)
            asked = launch.stop('owner')
            record = runner('acct-60b').wait(launch)
            own = engine_markers(launch.dispatch_id)
            own = own[0] if own else {}
            kids = own.get('children') or []
            call = invocation(launch.dispatch_id)
            artifact = returned(launch) or {}
            nxt, nrecord = run('acct-60b', admitted('VELDO-6004-stop-next', proj), 'claude', normal())
            check('stop/requested', 'the stop reached the worker: it and its descendant in its session are gone, it '
                  'never finished [%s, %s, %s]' % (asked, (launch.supervision or {}).get('cause'), kids),
                  asked is True and own.get('done') is False and len(kids) == 1 and not alive(own['pid'], own['start'])
                  and not alive(kids[0]['pid'], kids[0]['start'])
                  and (launch.supervision or {}).get('cause') == 'requested')
            check('stop/requested', 'its original invocation records the stop: the same invocation of the same dispatch '
                  'and account, cancelled, its tokens unknown and reservation retained [%s, %s, %s]'
                  % (call.get('outcome'), call.get('state'), (nrecord or {}).get('refusal')),
                  call.get('outcome') == 'cancelled' and call.get('dispatch') == launch.dispatch_id
                  and call.get('context', {}).get('account') == 'acct-60b' and call.get('state') == 'unknown'
                  and (nrecord or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens')
            check('stop/requested', 'the artifact is stopped, killed by a signal, and the wrapper path records the '
                  'dispatch unknown rather than ended [%s, %s, %s]'
                  % (artifact.get('problems'), (record or {}).get('state'), (record or {}).get('reason')),
                  artifact.get('verdict') == 'stopped' and 'signal' in (artifact.get('problems') or [])
                  and artifact.get('complete') is False and (record or {}).get('state') == 'unknown')
            normal_run.setdefault('observed', {})['stop'] = asked is True and (launch.supervision or {}).get('cause') \
                == 'requested' and not alive(own.get('pid', 0), own.get('start'))
            observed = normal_run.get('observed') or {}
            check('lifecycle/registration', 'the installed registration lists exactly the lifecycle operations, and '
                  'each was driven and observed on these runs [%s, %s]' % (lifecycle, observed),
                  lifecycle == ['accept', 'launch', 'observe', 'stop', 'exit', 'artifacts']
                  and all(observed.get(name) is True for name in lifecycle))

        with region('stop/descendant-alive'):
            launch, _ = run('acct-60b', admitted('VELDO-6005-escape'), 'claude',
                            [c_init(), {'descendant': 60, 'escape': True}, {'sleep': 30}] + normal()[1:], wait=False)
            own = marker_wait(launch.dispatch_id, children=1)
            launch.stop('owner')
            record = runner('acct-60b').wait(launch)
            kids = (engine_markers(launch.dispatch_id) or [{}])[0].get('children') or []
            escaped.extend(kids)
            living = [k for k in kids if alive(k['pid'], k['start'])]
            check('stop/descendant-alive', 'a descendant that left the worker\'s session is still alive after the stop, '
                  'and the dispatch is not recorded as ended while it lives [%s, %s, %d alive]'
                  % ((record or {}).get('state'), (record or {}).get('reason'), len(living)),
                  own.get('pid') is not None and not alive(own['pid'], own['start']) and len(living) == 1
                  and (record or {}).get('state') != 'exited' and (record or {}).get('state') == 'unknown'
                  and slot_outcome('acct-60b', launch.dispatch_id) == 'unknown')

        # AC4: each invocation's caps are checked before its launch.
        with region('caps/before-launch'):
            unit = admitted('VELDO-6006-boundaries', invocations=3)
            for boundary, resume in (('initial', None), ('retry', None), ('follow_on', SESSION)):
                launch, record = run('acct-60a', unit, 'claude', normal(), resume=resume)
                own = engine_markers(launch.dispatch_id)
                seen = (own[0] if own else {}).get('invocation') or {}
                call = invocation(launch.dispatch_id)
                reserved_at, ran_at = journal_seq('call/' + launch.dispatch_id), journal_seq('dispatch/run/%s/'
                                                                                             % launch.dispatch_id)
                check('caps/before-launch', '%s: reserved as %s before the engine started, which saw its pending '
                      'reservation, one launch [%s, %s, %d]' % (boundary, boundary, call.get('boundary'),
                                                                seen.get('state'), len(own)),
                      call.get('boundary') == boundary == seen.get('boundary') and seen.get('state') == 'pending'
                      and len(own) == 1 and spawned(launch.dispatch_id) == 1 and (record or {}).get('state') == 'exited'
                      and None not in (reserved_at, ran_at) and reserved_at < ran_at)
            for boundary, resume in (('retry', None), ('follow_on', SESSION)):
                launch, record = run('acct-60a', unit, 'claude', normal(), resume=resume)
                late = spawned(launch.dispatch_id, timeout=2.0) or bool(marker_wait(launch.dispatch_id, timeout=0.3))
                check('caps/before-launch', '%s past the unit\'s invocation cap: refused before launch, nothing spawned '
                      '[%s, %s]' % (boundary, (record or {}).get('refusal'), late),
                      (record or {}).get('refusal') == 'missing_authority:allowance:usage_cap:unit:invocations'
                      and not late and not invocation(launch.dispatch_id)
                      and reservations.balances('unit', unit)['invocations'] == 3)

        with region('caps/allowance-states'):
            unit = admitted('VELDO-6007-available', tokens=100)
            launch, record = run('acct-60a', unit, 'claude', normal(5, 5))
            call = invocation(launch.dispatch_id)
            charge = call.get('charge') or {}
            check('caps/allowance-states', 'available allowance: launched once and settled with the CLI\'s tokens and '
                  'messages, one invocation and its wall time [%s]' % charge,
                  (record or {}).get('state') == 'exited' and len(engine_markers(launch.dispatch_id)) == 1
                  and call.get('state') == 'settled' and charge.get('tokens') == 10 and charge.get('messages') == 1
                  and charge.get('invocations') == 1 and charge.get('wall_seconds', 0) > 0)
            launch, record = run('acct-60a', admitted('VELDO-6007-exhausted', invocations=0), 'claude', normal())
            check('caps/allowance-states', 'exhausted allowance: refused by name, nothing launched [%s]'
                  % (record or {}).get('refusal'),
                  (record or {}).get('refusal') == 'missing_authority:allowance:usage_cap:unit:invocations'
                  and nothing_ran(launch.dispatch_id))
            proj = project('p-unknown', tokens=1000)
            first, _ = run('acct-60a', admitted('VELDO-6007-unknown-a', proj), 'claude', [c_init()])
            launch, record = run('acct-60a', admitted('VELDO-6007-unknown-b', proj), 'claude', normal())
            check('caps/allowance-states', 'unknown allowance (an earlier call reported no usage): refused by name, '
                  'nothing launched [%s]' % (record or {}).get('refusal'),
                  invocation(first.dispatch_id).get('state') == 'unknown'
                  and (record or {}).get('refusal') == 'missing_authority:allowance:unknown_allowance:tokens'
                  and nothing_ran(launch.dispatch_id))
            reset = int(time.time()) + 3600
            run('acct-60b', admitted('VELDO-6007-window-a'), 'claude', [c_init(), c_rate('rejected', reset)] + normal()[1:])
            launch, record = run('acct-60b', admitted('VELDO-6007-window-b'), 'claude', normal())
            window = ((ACC.read(writer, 'acct-60b') if ACC else {}) or {}).get('windows', {}).get('five_hour') or {}
            check('caps/allowance-states', 'a rate-limit window the CLI reported rejected refuses the account\'s next '
                  'invocation until its reset, nothing launched [%s, %s]' % (window.get('reset_at'),
                                                                           (record or {}).get('refusal')),
                  window.get('status') == 'rejected' and window.get('reset_at') == reset
                  and (record or {}).get('refusal') == 'missing_authority:allowance:rate_limited:five_hour'
                  and nothing_ran(launch.dispatch_id))

        with region('caps/stop-at-cap'):
            unit = admitted('VELDO-6008-cap', tokens=1000)
            began = time.monotonic()
            launch, record = run('acct-60a', unit, 'claude', [c_init(), c_msg('m-a', 400, 200), {'sleep': 0.2},
                                                              c_msg('m-b', 400, 200), {'sleep': 30}, c_result(800, 400, 2)])
            elapsed = time.monotonic() - began
            own = engine_markers(launch.dispatch_id)
            call = invocation(launch.dispatch_id)
            check('caps/stop-at-cap', 'the report that reached the token cap stopped the worker, which never '
                  'finished; the invocation is cancelled with what the CLI reported and its wall time [%.1f s, %s, %s]'
                  % (elapsed, (launch.supervision or {}).get('cause'), call.get('observed')),
                  len(own) == 1 and own[0]['done'] is False and elapsed < 20
                  and (launch.supervision or {}).get('cause') == 'usage_cap' and call.get('outcome') == 'cancelled'
                  and call.get('observed', {}).get('tokens') == 1200 and call.get('charge', {}).get('invocations') == 1
                  and call.get('charge', {}).get('wall_seconds', 0) > 0
                  and (returned(launch) or {}).get('verdict') == 'stopped')

        # The local Linux contained launch (0060 review blocker 2), for both engines through the one receiver
        # path: each dispatch in its own transient scope in this run's slice, entering its clone through the
        # Landlock entrance, the pinned executable exec'd by the process the dispatch recorded, stopped
        # cooperatively and by force, its artifact and its exit record.
        CONTAINED = ('contained/bind', 'contained/scope', 'contained/clone-entry', 'contained/pinned-exec',
                     'contained/stop-cooperative', 'contained/stop-forced', 'contained/stop-descendant',
                     'contained/artifact', 'contained/exit-record')
        codex_lines = []

        def x_normal(ident, inp=900, out=100):
            lines = [{'type': 'thread.started', 'thread_id': ident}, {'type': 'turn.started'},
                     {'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'reasoning'}},
                     {'type': 'item.completed', 'item': {'id': 'item_1', 'type': 'agent_message'}},
                     {'type': 'turn.completed', 'usage': {'input_tokens': inp, 'cached_input_tokens': 0,
                                                          'output_tokens': out, 'reasoning_output_tokens': 0}}]
            codex_lines.extend(lines)
            return [{'line': line} for line in lines]
        ENGINE_CASES = {
            'claude': {'adapter': 'claude-contained', 'refused': 'claude-contained-unknown', 'account': 'acct-60a',
                       'refusal': 'invalid_input:engine_version:9.9.9', 'exe': str(pinned),
                       'flags': QUALIFIED['flags'], 'sha256': FAKE_SHA, 'profile': 'CLAUDE_CONFIG_DIR',
                       'normal': lambda: normal(), 'start': lambda: [c_init()]},
            'codex': {'adapter': 'codex-contained', 'refused': 'codex-contained-changed', 'account': 'acct-60x',
                      'refusal': 'stale_subject:engine_digest', 'exe': str(CODEX_BIN), 'flags': CODEX_FLAGS,
                      'sha256': (codex_record or {}).get('sha256'), 'profile': 'CODEX_HOME',
                      'normal': lambda: x_normal('thread-' + os.urandom(3).hex()),
                      'start': lambda: x_normal('thread-' + os.urandom(3).hex())[:2]}}
        STOPS = {
            # The engine ends on the cooperative request; its descendant ends on the group's SIGTERM.
            'cooperative': lambda: [{'descendant': 60, 'cooperative': True}, {'sleep': 30}],
            # The engine ignores the request and its descendant, started first, ends on the group's SIGTERM:
            # only the kill ends the engine.
            'forced': lambda: [{'descendant': 60, 'cooperative': True}, {'ignore_term': True}, {'sleep': 30}],
            # The engine ends on the request and leaves a descendant that ignores every SIGTERM: only the
            # group's kill ends it, and the dispatch must not be recorded ended while it lives.
            'descendant': lambda: [{'descendant': 60}, {'sleep': 30}]}
        runs60 = {}
        with region(*CONTAINED):
            for engine, case in ENGINE_CASES.items():
                probe = str(clones_root / ('probe-%s-%s' % (engine, os.urandom(3).hex())))
                launch, record = run(case['account'], admitted('VELDO-6010-' + engine), case['adapter'],
                                     [{'probe': probe}] + case['normal']())
                runs60[(engine, 'normal')] = (launch, record or {}, probe)
                launch, record = run(case['account'], admitted('VELDO-6011-' + engine), case['refused'], case['normal']())
                runs60[(engine, 'refused')] = (launch, record or {}, None)
                for stop, script in STOPS.items():
                    launch, _ = run(case['account'], admitted('VELDO-6012-%s-%s' % (engine, stop)), case['adapter'],
                                    case['start']() + script(), wait=False)
                    own = marker_wait(launch.dispatch_id, children=1)
                    asked_at = time.monotonic()
                    asked = launch.stop('owner')
                    record = runner(case['account']).wait(launch)
                    ended_at = time.monotonic()
                    kids = (engine_markers(launch.dispatch_id) or [{}])[0].get('children') or []
                    # What was alive the moment the dispatch's end was read.
                    living = {'engine': bool(own) and alive(own['pid'], own['start']),
                              'descendant': any(alive(k['pid'], k['start']) for k in kids)}
                    escaped.extend(kids)
                    runs60[(engine, stop)] = (launch, record or {}, {'asked': asked, 'took': ended_at - asked_at,
                                                                     'own': own, 'kids': kids, 'living': living})

            for engine, case in ENGINE_CASES.items():
                launch, record, probe = runs60[(engine, 'normal')]
                own = (engine_markers(launch.dispatch_id) or [{}])[0]
                history = [h.get('state') for h in rec(launch.dispatch_id).get('history') or []]
                accepted_at = journal_seq('dispatch/accept/%s/' % launch.dispatch_id)
                ran_at = journal_seq('dispatch/run/%s/' % launch.dispatch_id)
                check('contained/bind', '%s: bound before acceptance and launched once in its own scope, accepted '
                      'before it ran [%s, %s spawns]' % (engine, history, spawned(launch.dispatch_id)),
                      history == ['prepared', 'accepted', 'running', 'exited'] and spawned(launch.dispatch_id) == 1
                      and None not in (accepted_at, ran_at) and accepted_at < ran_at)
                refused, refused_record, _ = runs60[(engine, 'refused')]
                check('contained/bind', '%s: an unbindable executable on the contained path is refused %s before '
                      'acceptance, with no scope spawned and nothing reserved [%s]'
                      % (engine, case['refusal'], refused_record.get('refusal')),
                      refused_record.get('refusal') == case['refusal']
                      and [h.get('state') for h in rec(refused.dispatch_id).get('history') or []] == ['prepared', 'refused']
                      and nothing_ran(refused.dispatch_id))

                group = getattr(launch, 'group', None) or {}
                unit_name = CT.unit_name(launch.dispatch_id)
                gone = CT.populated(CT.CGROUP / str(group.get('cgroup') or 'none').lstrip('/'))
                check('contained/scope', '%s: the engine ran in its dispatch\'s own transient scope in this run\'s '
                      'slice, the group the receiver reported, empty once it ended [%s, %s]'
                      % (engine, own.get('cgroup'), group),
                      group.get('unit') == unit_name and group.get('slice') == slice_name
                      and own.get('cgroup') == group.get('cgroup') and str(own.get('cgroup')).endswith(
                          '/%s/%s' % (slice_name, unit_name))
                      and (launch.supervision or {}).get('empty') is True and gone in (None, False))

                handle = provisioned.get(launch.dispatch_id)
                paths = clones._paths(handle) if handle is not None else {}
                entered = [json.loads(x.read_text()) for x in sorted((Path(paths['root']) / 'entered').glob('*.json'))] \
                    if paths else []
                process = record.get('process') or {}
                work = paths.get('work')
                head = GP.run(['git', '-C', str(work), 'rev-parse', 'HEAD'], capture_output=True,
                              text=True).stdout.strip() if work else None
                probed = [json.loads(x) for x in ((markers / ('%d.probe' % own['pid'])).read_text().splitlines()
                                                    if own.get('pid') and (markers / ('%d.probe' % own['pid'])).exists()
                                                    else [])]
                check('contained/clone-entry', '%s: it entered its own clone through the Landlock entrance as the '
                      'process the dispatch recorded, in its scope, and ran in the clone at the accepted commit [%s]'
                      % (engine, entered),
                      len(entered) == 1 and entered[0].get('dispatch_id') == launch.dispatch_id
                      and entered[0].get('pid') == process.get('pid') == own.get('pid')
                      and entered[0].get('cgroup') == group.get('cgroup') and own.get('cwd') == work
                      and (own.get('env') or {}).get('VELDO_CLONE') == work
                      and head == ((record.get('contract') or {}).get('source') or {}).get('commit'))
                check('contained/clone-entry', '%s: confined: its write into the clone root was denied, nothing '
                      'written [%s]' % (engine, probed),
                      probed == [[probe, 'PermissionError']] and not os.path.exists(probe))

                env = own.get('env') or {}
                check('contained/pinned-exec', '%s: the process the dispatch recorded is the pinned executable, exec\'d '
                      'with exactly its qualified flags, the qualified digest on disk [%s]' % (engine, own.get('argv')),
                      own.get('argv') == [case['exe']] + list(case['flags']) and process.get('start') == own.get('start')
                      and file_sha(case['exe']) == case['sha256'] and case['sha256'])
                check('contained/pinned-exec', '%s: with the updater off and the recorded account\'s own profile [%s]'
                      % (engine, env.get('DISABLE_AUTOUPDATER')),
                      env.get('DISABLE_AUTOUPDATER') == '1' and env.get(case['profile']) == profiles[case['account']])

                found = returned(launch) or {}
                stored, mode = artifact_file(launch.dispatch_id)
                parent_mode = (artifacts.stat().st_mode & 0o777) if artifacts.is_dir() else None
                check('contained/artifact', '%s: a complete artifact of this engine, bound to its dispatch, invocation '
                      'and pinned executable, kept 0600 in a 0700 directory [%s, %s]'
                      % (engine, found.get('verdict'), found.get('executable')),
                      found.get('verdict') == 'complete' and found.get('complete') is True
                      and found.get('engine') == getattr(L.ENGINES.get({'claude': 'claude_code', 'codex': 'codex'}[engine]),
                                                         'PROVIDER', None)
                      and found.get('dispatch_id') == launch.dispatch_id and stored == found and mode == 0o600
                      and parent_mode == 0o700 and (found.get('executable') or {}).get('sha256') == case['sha256']
                      and (found.get('executable') or {}).get('path') == case['exe'])
                if engine == 'codex':
                    check('contained/artifact', 'codex: its document verifies from its own lines [%s]'
                          % found.get('verdict'), bool(found) and getattr(X, 'verify', lambda d: False)(found))

                termination = record.get('termination') or {}
                bound = rec(launch.dispatch_id).get('artifact')
                call = invocation(launch.dispatch_id)
                check('contained/exit-record', '%s: the exit is recorded for the recorded process, exit 0, binding '
                      'the complete artifact the runner was given; invocation and slot completed [%s, %s, %s]'
                      % (engine, termination.get('returncode'), bound, slot_outcome(case['account'], launch.dispatch_id)),
                      record.get('state') == 'exited' and termination.get('returncode') == 0
                      and termination.get('signal') is None
                      and bound == {'verdict': 'complete', 'complete': True, 'digest': (launch.artifact or {}).get('digest')}
                      and getattr(D, 'completed', lambda r: None)(rec(launch.dispatch_id)) is True
                      and call.get('outcome') == 'completed' and call.get('state') == 'settled'
                      and slot_outcome(case['account'], launch.dispatch_id) == 'completed')

                for stop, row in (('cooperative', 'contained/stop-cooperative'), ('forced', 'contained/stop-forced'),
                                  ('descendant', 'contained/stop-descendant')):
                    launch, record, seen = runs60[(engine, stop)]
                    supervision = launch.supervision or {}
                    steps = [s.get('step') for s in supervision.get('steps') or []]
                    termination = record.get('termination') or {}
                    process = record.get('process') or {}
                    call = invocation(launch.dispatch_id)
                    found = returned(launch) or {}
                    check(row, '%s: the stop reached the receiver and the dispatch is recorded exited, stopped on '
                          'request, its group empty, for the process it recorded [%s, %s]'
                          % (engine, record.get('state'), supervision.get('cause')),
                          seen['asked'] is True and record.get('state') == 'exited' and supervision.get('cause') == 'requested'
                          and supervision.get('empty') is True and process.get('pid') == seen['own'].get('pid')
                          and process.get('start') == seen['own'].get('start'))
                    check(row, '%s: when that end was read, the engine and its descendant were gone [%s]'
                          % (engine, seen['living']), len(seen['kids']) == 1
                          and seen['living'] == {'engine': False, 'descendant': False})
                    check(row, '%s: its original invocation is cancelled, its usage unknown and retained, and its '
                          'artifact names it, never complete [%s, %s]' % (engine, call.get('outcome'), found.get('verdict')),
                          call.get('outcome') == 'cancelled' and call.get('state') == 'unknown'
                          and found.get('invocation') == 'invocation/' + launch.dispatch_id
                          and found.get('complete') is False and (rec(launch.dispatch_id).get('artifact') or {}).get(
                              'complete') is False)
                    if stop == 'cooperative':
                        check(row, '%s: it ended on the cooperative request, never killed, well within the graces '
                              '[%s, %.2fs, %s]' % (engine, steps, seen['took'], termination),
                              'kill' not in steps and steps[:1] == ['cooperative'] and seen['took'] < 5
                              and termination.get('signal') == int(signal.SIGTERM))
                    elif stop == 'forced':
                        check(row, '%s: an engine ignoring the request is killed with its group after the configured '
                              'graces, within their bound [%s, %.2fs, %s]' % (engine, steps, seen['took'], termination),
                              steps == ['cooperative', 'terminate', 'kill'] and termination.get('signal') == int(signal.SIGKILL)
                              and supervision.get('graces') == {'stop_grace_seconds': GRACE, 'kill_grace_seconds': GRACE}
                              and 2 * GRACE - 0.1 <= seen['took'] <= 2 * GRACE + 4.0)
                    else:
                        check(row, '%s: the engine ended on the request and its descendant outlived the group\'s '
                              'SIGTERM: only the kill ended it, and the dispatch was recorded ended after [%s, %s]'
                              % (engine, steps, termination),
                              termination.get('signal') == int(signal.SIGTERM) and 'kill' in steps
                              and supervision.get('empty_monotonic') is not None
                              and steps[-1:] == ['kill'])

        # The fixtures, checked against the tables extracted from the installed binary.
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

        def event_name(line):
            if line.get('type') == 'system':
                return 'system/' + str(line.get('subtype'))
            if line.get('type') == 'result':
                return 'result/success' if line.get('subtype') == 'success' else 'result/error'
            return line.get('type')

        def problems_of(line):
            name = event_name(line)
            return ['%s: an event the CLI does not print' % name] if name not in FORMATS['events'] \
                else conform(line, FORMATS['events'][name], name)

        with region('format/fake-lines'):
            lines = [s[1] for s in printed_steps if s[0] == 'line']
            problems = [p for line in lines for p in problems_of(line)]
            kinds = {event_name(line) for line in lines}
            check('format/fake-lines', 'every one of the %d lines the fake was scripted to print conforms to the format '
                  'the installed binary %s declares, and the fixtures print every event the adapter reads [%s, %s]'
                  % (len(lines), FORMATS['version'], problems[:4], sorted({'system/init', 'assistant', 'result/success',
                                                                          'result/error', 'rate_limit_event'} - kinds)),
                  len(lines) > 60 and not problems
                  and {'system/init', 'assistant', 'result/success', 'result/error', 'rate_limit_event'} <= kinds)
            codex_events = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['codex']['events']
            codex_items = json.loads((TREE / 'proof' / 'VELDO-0061' / 'codex-exec.json').read_text())['item']
            codex_problems = [p for line in codex_lines for p in (
                conform(line, codex_events[line['type']], line['type']) if line.get('type') in codex_events
                else [str(line.get('type')) + ': an event exec does not print'])]
            codex_problems += [line['item'] for line in codex_lines if 'item' in line and (
                line['item'].get('type') not in codex_items['kinds']
                or conform(line['item'], codex_items['items'][line['item']['type']], 'item'))]
            check('format/fake-lines', 'every one of the %d Codex lines the contained rows scripted is an event the '
                  'installed Codex binary declares, its item an exec item of a declared kind [%s]'
                  % (len(codex_lines), codex_problems[:3]), len(codex_lines) >= 10 and not codex_problems)
            perturbed = [s for s in printed_steps if s[0] == 'perturbed']
            wrong = []
            for _, kind, source, raw in perturbed:
                text = json.dumps(source)
                exact = {'truncated': raw == text[:len(text) // 2] + '\n', 'not_json': raw == 'Error: ' + text[:40] + '\n'}
                if kind.startswith('without:'):
                    field = kind.split(':', 1)[1]
                    event = json.loads(raw)
                    exact[kind] = (event == {k: v for k, v in source.items() if k != field} and field in source
                                   and any(field + ': required and missing' in p for p in problems_of(event)))
                if problems_of(source) or not exact.get(kind):
                    wrong.append((kind, problems_of(source)[:2]))
            check('format/fake-lines', 'each of the %d perturbed lines is exactly its perturbation of a line that '
                  'conforms: cut short, not JSON, or a result without the usage the schema requires [%s]'
                  % (len(perturbed), wrong[:3]),
                  len(perturbed) >= 3 and not wrong
                  and {'truncated', 'not_json', 'without:modelUsage'} == {p[1] for p in perturbed})

        with region('format/fake-argv'):
            # Claude Code's starts: the contained rows' Codex starts are Codex's own command line.
            starts = [m for m in (json.loads(p.read_text()) for p in sorted(markers.glob('*.json')))
                      if m['argv'][:1] != [str(CODEX_BIN)]]
            argvs = [m['argv'][1:] for m in starts]
            declared = OPTIONS['options']
            undeclared = []
            for argv in argvs:
                n = 0
                while n < len(argv):
                    option = declared.get(argv[n])
                    if option is None:
                        undeclared.append(argv[n])
                        break
                    if option['value'] == 'required':
                        value = argv[n + 1] if n + 1 < len(argv) else None
                        if value is None or (option['choices'] and value not in option['choices']):
                            undeclared.append('%s %s' % (argv[n], value))
                        n += 2
                    else:
                        n += 1
            needs = OPTIONS['requires']['--output-format=stream-json']
            unmet = [a for a in argvs if 'stream-json' in a and needs['with'] in a and needs['needs'] not in a]
            check('format/fake-argv', 'the fake was started %d times, each only with options the binary\'s main '
                  'command declares, values among their choices, and stream JSON in print mode with verbose [%s, %s]'
                  % (len(argvs), undeclared[:3], unmet[:1]),
                  len(argvs) >= 15 and not undeclared and not unmet and all(a == QUALIFIED['flags'] for a in argvs))
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        # The contained rows' scopes: the run's slice stopped, its failed units cleared, nothing installed.
        with contextlib.suppress(Exception):
            subprocess.run(['systemctl', '--user', 'stop', slice_name], capture_output=True, timeout=20, env=tools,
                           stdin=subprocess.DEVNULL)
        with contextlib.suppress(Exception):
            mine = sorted({CT.unit_name(launch.dispatch_id) for launch in contained_launches})
            listed = subprocess.run(['systemctl', '--user', 'list-units', '--all', '--plain', '--no-legend', *mine],
                                    capture_output=True, text=True, timeout=20, env=tools, stdin=subprocess.DEVNULL)
            loaded = [line.split()[0] for line in listed.stdout.splitlines() if line.split()]
            if mine and loaded:
                subprocess.run(['systemctl', '--user', 'reset-failed', *loaded], capture_output=True, timeout=20,
                               env=tools, stdin=subprocess.DEVNULL)
        for launch in contained_launches:
            with contextlib.suppress(Exception):
                if launch.child is not None and launch.child.poll() is None:
                    launch.child.kill()
                    launch.child.wait(timeout=10)
        for kid in escaped:
            with contextlib.suppress(OSError):
                stat = Path('/proc/%d/stat' % kid['pid']).read_text()
                if stat[stat.rindex(')') + 2:].split()[19] == kid['start']:
                    os.kill(kid['pid'], signal.SIGKILL)
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
                    print('  VELDO-0060 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0060 %s detail: no check ran' % name)
        expect('VELDO-0060 ' + name, ok)
    print('VELDO-0060 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session. The gate's mutation stage runs every suite without XDG_RUNTIME_DIR; the receiver, its
# systemd tools and this suite's own systemctl reach the user manager through /run/user/<uid> for this run.
_v60_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v60_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v60_suite()
finally:
    if _v60_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v60_session
