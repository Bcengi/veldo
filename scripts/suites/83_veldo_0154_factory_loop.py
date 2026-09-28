"""VELDO-0154: the factory loop runs inside the installed authority service, woken only by commits, run ends
and account resets, and re-dispatches or asks the owner at an account limit.

Run: python3 scripts/selftest.py --suite 83_veldo_0154_factory_loop

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and the
installer copies its fixed executable from, so a registered mutation of a production module reaches the
installed service and the launch receiver it starts. Real: an enrolled Git clone and this host's trust file,
OpenSSH enrollment, request, command and journal signatures, the SQLite store the service is configured with
(read back through connections of this suite's own), control_service.install laying the instance down with its
work configuration, the INSTALLED service process running its installed executable on its installed
configuration (the unit's ExecStart, run as a child of this suite: no unit is loaded into the user manager, and
the installer's daemon-reload goes to a recording stand-in), its socket reached through control_client, the
owner's projects activated and one paused through VELDO-0076's project service, the owner's Codex accounts
registered over profiles .veldo/accounts.py prepares, VELDO-0036 reservations under their production
authorization, VELDO-0031 claims, the VELDO-0039 Runner inside the service with the launch receiver processes
it starts from the installed receiver configuration, the trusted wrapper that execs the engine, VELDO-0141's
execution records, VELDO-0160's account pool and re-run-or-ask decision, and VELDO-0064's inbox, whose owner
answers arrive as signed packets through the service. The engine is a fake `codex` laid out as the vendor
package and qualified by the production writer: it prints the lines of Codex 0.154.0's exec JSON (its usage-limit
message with its reset minute, and its MCP tool-call item) that a script file of this suite names for its unit,
station and attempt, waiting on a file where the script says, and exits with the scripted code. Worker launches
go through the wrapper without a containment group (`identity: reported`). No real engine runs, nothing logs in
and no credential exists. Each row is reported once.
"""


def _v154_suite():
    import contextlib
    import datetime
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import time

    FORMATS_PATH = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2] \
        / 'proof' / 'VELDO-0062' / 'cli-formats.json'
    FORMATS = json.loads(FORMATS_PATH.read_text())
    XLIMIT = FORMATS['codex']['usage_limit']

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
    }
    ROWS = ('install/assets', 'loop/runner-in-service', 'loop/journal-wake-offers', 'loop/review-offered',
            'loop/receiver-death', 'loop/rerun-another-account', 'loop/ask-before-rerun', 'loop/owner-yes-reruns',
            'loop/owner-no-stops', 'loop/reset-timer-wake', 'loop/no-other-timer')
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

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='v154-', dir=fast))
    run_id = os.urandom(4).hex()
    service_proc = [None]
    connections = []
    try:
        mods = base / 'src' / '.veldo'
        (mods / 'services').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for source in sorted((ROOT / '.veldo' / 'services').iterdir()):
            if source.is_file():
                shutil.copyfile(source, mods / 'services' / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        CS = load('v154_service', mods / 'control_service.py')
        CC = load('v154_client', mods / 'control_client.py')
        E = load('v154_enrollment', mods / 'control_enrollment.py')
        S = load('v154_store', mods / 'control_store.py')
        AC = load('v154_contract', mods / 'authority_contract.py')
        EL = load('v154_eligibility', mods / 'control_eligibility.py')
        SIG = load('v154_signer', mods / 'control_signer.py')
        GP = load('v154_git', mods / 'git_process.py')
        CLM = load('v154_claim', mods / 'control_claim.py')
        CM = load('v154_membership', mods / 'control_membership.py')
        PJ = load('v154_project', mods / 'control_project.py')
        RES = load('v154_reservations', mods / 'control_reservations.py')
        ACC = RES.ACC
        HELPER = load('v154_helper', mods / 'accounts.py')
        CODEX = load('v154_codex', mods / 'control_engine_codex.py')
        HOST_ID = 'host-154'
        HOST = socket.gethostname()
        DOMAIN, STORE, REPO = 'dom154' + run_id, 'store154' + run_id, 'repo154' + run_id
        BUILDER, REVIEWER = 'builder-154', 'reviewer-154'

        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('owner',):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / who)], check=True,
                           capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = (private / (who + '.pub')).read_text().strip()
        # The authority's journal key, in the key directory the installer then uses as it finds it.
        keys = base / 'keys' / 'authority'
        keys.mkdir(parents=True, mode=0o700)
        os.chmod(str(keys), 0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'veldo-authority', '-f', str(keys / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        os.chmod(str(keys / 'journal'), 0o600)
        public['authority'] = (keys / 'journal.pub').read_text().strip()

        def signer(path, namespace):
            def sign(data):
                return SIG.sign_bytes(path, data, namespace)
            return sign
        owner_sign = signer(private / 'owner', AC.SIGNATURE_NAMESPACE)
        journal_sign = signer(keys / 'journal', 'veldo-journal')

        trust_dir = base / 'trust'
        trust_dir.mkdir(mode=0o700)
        signers_file = trust_dir / 'enrollment_signers'
        signers_file.write_text(AC.allowed_signers_line('owner', public['owner'], EL.ENROLLMENT_NAMESPACE) + '\n')
        trust_file = trust_dir / 'host_trust.json'
        trust_file.write_text(json.dumps({'schema': EL.HOST_TRUST_SCHEMA, 'host_identity': HOST_ID,
                                          'enrollment_signers': str(signers_file)}))
        workspace = base / 'clone-a'
        GP.run(['git', 'init', '-q', str(workspace)], check=True, capture_output=True)
        (workspace / 'README').write_text('factory loop source\n')
        GP.run(['git', '-C', str(workspace), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        store_path = base / 'authority' / 'control.sqlite3'
        binding = E.enroll(str(workspace), DOMAIN, STORE, str(store_path), HOST_ID, 1,
                           signer(private / 'owner', EL.ENROLLMENT_NAMESPACE), 'owner', 'enrolled', repository_uuid=REPO)
        verify = EL.HostTrust(HOST_ID, str(signers_file)).verifier('owner', str(workspace))
        ids = {'domain_uuid': DOMAIN, 'repository_uuid': REPO, 'store_uuid': STORE}

        # The store the service is configured with, set up by the owner before installation.
        setup = S.open_store(str(store_path))
        connections.append(setup)
        setup.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                     'writes': ('entities', 'journal', 'commands', 'nonces')}
        serial = [0]

        def next_id(prefix):
            serial[0] += 1
            return '%s-%s-%d' % (prefix, run_id, serial[0])

        def version_of(identity):
            row = setup.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            return row[0] if row else 0

        def put(identity, kind, data):
            command = next_id('setup')
            S.execute(setup, dict(command_id=command, principal='setup', operation='upsert_entity', nonce=command,
                                  artifact_digests=[], expected_versions={identity: version_of(identity)},
                                  parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', journal_sign, 1)

        for who, kind, roles in (('owner', 'person', ['project_owner']), ('authority', 'service', ['reservation_service']),
                                 ('launch-receiver', 'service', ['reservation_service']), (BUILDER, 'agent_run', []),
                                 (REVIEWER, 'agent_run', [])):
            put(who, 'membership', dict(principal_type=kind, roles=roles, scope='*', revoked_at=None, expires_at=None))
        for who in ('owner', 'authority'):
            put('key:%s:1' % who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))

        # The owner's projects, through VELDO-0076's project service: one active, one paused.
        projects = PJ.Projects(S, CM, setup, ids, 'setup', journal_sign, stop=lambda dispatch_id, reason: False)

        def project_command(operation, name, **fields):
            body = dict(ids, operation=operation, project=name, principal='owner', command_id=next_id('pc'),
                        nonce=next_id('pn'), **fields)
            return projects.apply({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})
        activations = {}
        for name in ('journey', 'halted'):
            activations[name] = project_command(
                'activate', name, owner='owner', charter={'purpose': 'Deliver the %s work.' % name, 'exclusions': []},
                execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                coordination_budget={'capacity': 20, 'invocations': 200, 'wall_seconds': 10 ** 6, 'owner_minutes': 60})

        # The owner's Codex accounts, each with its own profile on this host, and the reservation ceilings.
        reserving = RES.Reservations(S, setup, domain=DOMAIN, repository=REPO, principal='authority',
                                     authorize=RES.service_authority, signer='authority', sign=journal_sign)
        BIG = dict(capacity=50, invocations=500, wall_seconds=10 ** 7)
        helper_root = base / 'helper'
        ACCOUNTS = ('acct-x1', 'acct-x2', 'acct-x3', 'acct-x4')
        for account in ACCOUNTS:
            reserving.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        for name in ('journey', 'halted'):
            reserving.configure('policy/' + name, 'project', name, dict(BIG), now=time.time())

        def unit(name, project='journey'):
            put(name, 'execution_unit', dict(state='READY', repository_uuid=REPO, backlog_item_uuid='backlog:' + name,
                                             requirements=[], eligible_holders=[BUILDER], project=project,
                                             scope_digest='sha256:scope-' + name, revision=1, depends_on=[],
                                             producer=BUILDER))
            put('backlog:' + name, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPO))
            put('admission:' + name, 'admission', dict(unit=name, state='accepted', scope_digest='sha256:scope-' + name))
            reserving.configure('policy/' + name, 'unit', name, dict(capacity=10, invocations=50, wall_seconds=10 ** 6),
                                now=time.time())
            return name

        def claim(name):
            """The unit's assignment to the builder: its claim (VELDO-0031), written as the builder holds it."""
            cid = CLM.claim_id(REPO, name)
            command = next_id('claim')
            S.execute(setup, dict(command_id=command, principal=BUILDER, operation='claim_operation', nonce=command,
                                  artifact_digests=[], expected_versions={name: version_of(name),
                                                                          'backlog:' + name: version_of('backlog:' + name),
                                                                          cid: version_of(cid)},
                                  parameters=dict(action='claim', unit_id=name, backlog_item_uuid='backlog:' + name,
                                                  claim_id=cid, holder=BUILDER, generation=0, capabilities=[],
                                                  repository_uuid=REPO)), BUILDER, journal_sign, 1)
            return name

        U = {key: 'VELDO-9154-' + key for key in ('U1', 'U2', 'UP', 'UX', 'B1', 'B2', 'B3', 'W', 'L1', 'L2', 'L3', 'L4')}
        for key, name in sorted(U.items()):
            unit(name, 'halted' if key == 'UP' else 'journey')
        # The paused project's unit was assigned before its project was paused.
        claim(U['UP'])
        paused = project_command('pause', 'halted', reason='owner review', project_version=version_of('project:halted'))

        # The fake Codex, laid out as the vendor package and qualified by the production writer.
        markers, gates, scripts = base / 'markers', base / 'gates', base / 'scripts'
        for directory in (markers, gates, scripts):
            directory.mkdir()
        fake = '''#!%s -B
import json, os, sys, time
from pathlib import Path
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
markers, scripts = Path(MARKERS), Path(SCRIPTS)
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
key = '%%s.%%s' %% (packet.get('unit'), packet.get('station'))
attempt = len(list(markers.glob(key + '.*.json')))
own = {'pid': os.getpid(), 'dispatch': packet.get('dispatch_id'), 'unit': packet.get('unit'),
       'station': packet.get('station'), 'attempt': attempt, 'started': time.time(), 'home': os.environ.get('CODEX_HOME')}
(markers / ('%%s.%%d.tmp' %% (key, attempt))).write_text(json.dumps(own))
os.rename(str(markers / ('%%s.%%d.tmp' %% (key, attempt))), str(markers / ('%%s.%%d.json' %% (key, attempt))))
try:
    attempts = json.loads((scripts / (key + '.json')).read_text())
except (OSError, ValueError):
    attempts = [{'script': [], 'code': 3}]
chosen = attempts[min(attempt, len(attempts) - 1)]
for step in chosen['script']:
    if 'line' in step:
        sys.stdout.write(json.dumps(step['line']) + chr(10))
        sys.stdout.flush()
    elif 'wait' in step:
        end = time.time() + 150
        while not os.path.exists(step['wait']) and time.time() < end:
            time.sleep(0.02)
sys.exit(chosen['code'])
''' % (sys.executable,)
        package = base / 'bin' / 'codex-package'
        vendored = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        vendored.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        vendored.write_text(fake.replace('Path(MARKERS)', 'Path(%r)' % str(markers))
                            .replace('Path(SCRIPTS)', 'Path(%r)' % str(scripts)))
        vendored.chmod(0o755)
        qualification = base / 'codex-qualification.json'
        qualification.write_text(json.dumps(CODEX.qualification(str(vendored))))

        # The installation: its fixed executable, its receiver configuration and the work configuration.
        install_root, unit_dir = base / 'install', base / 'units'
        service_id = CS.CC.service_id(binding)
        installed_bin = install_root / service_id / 'bin'
        wrapper = [sys.executable, '-B', str(installed_bin / 'control_launch.py'), 'exec']
        ADAPTERS = {'codex': {'identity': 'reported', 'engine': 'codex', 'environment': {'TZ': 'UTC'},
                              'executable': str(vendored), 'qualification': str(qualification),
                              'argv': wrapper + [str(vendored)] + list(CODEX.FLAGS)}}
        ROLE = dict(adapter='codex', configuration={'tools': ['Read', 'Edit']}, seconds=240)
        WORK = {'schema': 'veldo.factory_work/v1', 'repositories': {REPO: {
            'builder': dict(ROLE, identity=BUILDER, payload={'task': 'build the unit'}),
            'reviewers': [dict(ROLE, identity=REVIEWER, payload={'task': 'review the unit'})]}}}
        work_file = base / 'work.json'
        work_file.write_text(json.dumps(WORK))
        PROFILE = {'kind': 'linux-systemd', 'slice': 'v154%s.slice' % run_id, 'lock': str(base / 'workers.lock'),
                   'concurrency': 4, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
                   'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}

        class Recording:
            """The installer's systemd runner: records its daemon-reload, so no unit reaches the user manager."""
            def __init__(self):
                self.calls = []

            def run(self, args):
                self.calls.append(list(args))
                return 0, '', ''
        systemd = Recording()
        installed, install_error = None, None
        try:
            installed = CS.install([str(workspace)], host_trust=str(trust_file), key_directory=str(keys),
                                   install_root=str(install_root), unit_dir=str(unit_dir), profile=PROFILE,
                                   adapters=ADAPTERS, writable=[str(base / 'work')], runner=systemd,
                                   work=str(work_file))
        except Exception as error:  # noqa: BLE001 - a refused installation reds every row by assertion
            install_error = '%s %s' % (getattr(error, 'code', type(error).__name__), getattr(error, 'detail', error))
        config = json.loads(Path(installed['config']).read_text()) if installed else {}
        # The owner registers his accounts with the installed code, which owns the account records from then on
        # (control_accounts declares them its own, bound to the file that declares them).
        registered = []
        if installed is not None:
            accounts = load('v154_installed_accounts', installed_bin / 'control_accounts.py').Accounts(
                S, setup, principal='owner', signer='owner', sign=journal_sign)
            for account in ACCOUNTS:
                HELPER.account_add(account, root=str(helper_root), provider='codex')
                fields = HELPER.registration(account, host=HOST, root=str(helper_root))
                registered.append(accounts.register('register/' + account, fields['account'], fields['provider'],
                                                    fields['label'], fields['profiles'], concurrency=1, now=time.time()))
        observations = Path(config.get('observations') or base / 'no-observations.jsonl')

        # -- what the suite reads back, each through a connection or file of its own --------------------------
        def independent(sql, *params):
            conn = sqlite3.connect('file:%s?mode=ro' % store_path, uri=True, timeout=10)
            try:
                return conn.execute(sql, params).fetchall()
            finally:
                conn.close()

        def entity(identity):
            found = independent('SELECT kind, data FROM entities WHERE id=?', identity)
            return {'kind': found[0][0], 'data': json.loads(found[0][1])} if found else None

        def dispatches(name=None, station=None):
            found = [json.loads(data) for (data,) in independent("SELECT data FROM entities WHERE kind='dispatch'")]
            found = [r for r in found if (name is None or r['contract']['unit'] == name)
                     and (station is None or r['contract']['station'] == station)]
            return sorted(found, key=lambda r: (r['contract']['unit'], r['contract']['station'], r['contract']['attempt']))

        def worker_slot(dispatch_id):
            return (entity(RES.entity('worker', [DOMAIN, dispatch_id])) or {}).get('data') or {}

        def invocation(dispatch_id):
            return (entity(RES.entity('invocation', [DOMAIN, 'invocation/' + dispatch_id])) or {}).get('data') or {}

        def assignments():
            return [json.loads(data) for (data,) in independent("SELECT data FROM entities WHERE kind='assignment'")]

        def passes():
            found = []
            try:
                text = observations.read_text()
            except OSError:
                return found
            for line in text.splitlines():
                try:
                    seen = json.loads(line)
                except ValueError:
                    continue
                if isinstance(seen, dict) and seen.get('kind') == 'loop' and seen.get('operation') == 'loop_pass':
                    found.append(seen)
            return found

        def last_pass():
            found = passes()
            return found[-1]['pass'] if found else 0

        def live():
            proc = service_proc[0]
            return proc is not None and proc.poll() is None

        # Every wait of the suite draws on one budget, so a defect that stops the loop ends the run promptly.
        budget = time.monotonic() + 300

        def bounded(timeout):
            return max(0.0, min(timeout, budget - time.monotonic())) if live() else 0

        def wait_pass(predicate, after, timeout=30.0):
            """The first pass numbered after `after` for which `predicate` holds, or None; at once when no service
            runs, so a tree without this work fails its rows by their assertions, promptly."""
            end = time.time() + bounded(timeout)
            while True:
                for seen in passes():
                    if seen['pass'] > after and predicate(seen):
                        return seen
                if time.time() >= end or not live():
                    return None
                time.sleep(0.05)

        def wait_until(predicate, timeout=30.0):
            end = time.time() + bounded(timeout)
            while time.time() < end and live():
                if predicate():
                    return True
                time.sleep(0.05)
            return predicate()

        def dig(value, *keys):
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
            return value

        def offered(seen, name=None, station=None):
            return [o for o in (seen or {}).get('offered') or [] if (name is None or o['unit'] == name)
                    and (station is None or o['station'] == station)]

        def ended(seen, name=None):
            return [e for e in (seen or {}).get('ended') or [] if name is None or e['unit'] == name]

        def proc_stat(pid):
            if not isinstance(pid, int):
                return None
            try:
                text = Path('/proc/%d/stat' % pid).read_text()
            except OSError:
                return None
            return text[text.rindex(')') + 2:].split()

        def alive(identity):
            fields = proc_stat((identity or {}).get('pid') or 0) if isinstance((identity or {}).get('pid'), int) else None
            return bool(fields) and fields[19] == identity.get('start') and fields[0] != 'Z'

        def switches(pid):
            if not isinstance(pid, int):
                return None
            try:
                for line in Path('/proc/%d/status' % pid).read_text().splitlines():
                    if line.startswith('voluntary_ctxt_switches:'):
                        return int(line.split()[1])
            except (OSError, ValueError):
                return None
            return None

        def send(payload):
            try:
                return CC.send(str(workspace), payload, E, verify, owner_sign, HOST_ID, timeout=90)
            except Exception as error:  # noqa: BLE001 - a refused request is data for the row
                return {'refused': getattr(error, 'reason', type(error).__name__)}

        def note():
            """A signed store command through the service that advances the journal: the journal wake."""
            eid = next_id('note:154')
            body = dict(command_id=next_id('cmd'), principal='owner', operation='upsert_entity', nonce=next_id('nonce'),
                        artifact_digests=[], expected_versions={eid: 0},
                        parameters=dict(entity_id=eid, kind='note', data={'n': serial[0]}), **ids)
            return send({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})

        def answer(record, ruling):
            """The owner's signed answer to a loop question, sent through the service (VELDO-0064)."""
            body = dict(ids, operation='answer', alias=record.get('alias'), principal='owner', command_id=next_id('answer'),
                        nonce=next_id('an'), request_version=record.get('request_version'), ruling=ruling)
            return send({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})

        def script(name, station, attempts):
            (scripts / ('%s.%s.json' % (name, station))).write_text(json.dumps(attempts))

        def gate(name):
            return str(gates / name)

        def release(name):
            Path(gate(name)).write_text('go')

        def thread():
            return {'line': {'type': 'thread.started', 'thread_id': 'thread-154-' + os.urandom(4).hex()}}

        def turn():
            return {'line': {'type': 'turn.started'}}

        def done():
            return {'line': {'type': 'turn.completed', 'usage': {
                'input_tokens': 3, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': 4,
                'reasoning_output_tokens': 0}}}

        def failed(message):
            return {'line': {'type': 'turn.failed', 'error': {'message': message}}}

        def limit_message(stated):
            """Codex's usage-limit message with the minute `stated` as its reset, in the engine's zone (UTC)."""
            at = datetime.datetime.fromtimestamp(stated, datetime.timezone.utc)
            clock = '%d:%02d %s' % (at.hour % 12 or 12, at.minute, 'AM' if at.hour < 12 else 'PM')
            if at.date() != datetime.datetime.now(datetime.timezone.utc).date():
                day = at.day
                suffix = 'th' if 11 <= day % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                clock = '%s %d%s, %d %s' % (('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                              'Dec')[at.month - 1], day, suffix, at.year, clock)
            return XLIMIT['message'] + '.' + XLIMIT['retry_at'][0] + clock + '.'

        def mcp_call(kind, status, result=None):
            item = {'id': 'item_1', 'type': 'mcp_tool_call', 'server': 'tracker', 'tool': 'add_comment',
                    'arguments': {'issue': 'CEO-1'}, 'status': status}
            if result is not None:
                item['result'] = result
            return {'line': {'type': kind, 'item': item}}

        def end_of_minute(ts):
            return (int(ts) // 60) * 60 + 60

        SUCCESS = {'script': [thread(), turn(), done()], 'code': 0}
        FAILS = {'script': [thread(), turn(), failed('internal error; agent loop died unexpectedly')], 'code': 1}

        def limited(stated, call=False, wait=None):
            steps = [thread(), turn()] + ([{'wait': gate(wait)}] if wait else [])
            if call:
                steps += [mcp_call('item.started', 'in_progress'),
                          mcp_call('item.completed', 'completed', {'content': [], 'structured_content': None})]
            return {'script': steps + [failed(limit_message(stated))], 'code': 1}

        def held(name):
            return {'script': [thread(), turn(), {'wait': gate(name)}, done()], 'code': 0}

        for key in ('UP', 'UX'):
            script(U[key], 'build', [SUCCESS])

        # AC1: the installed service with the Runner inside it, and its assets.
        with region('install/assets'):
            names = ('control_service.py', 'control_launch.py', 'control_reservations.py', 'control_account_pool.py')
            same = {name: (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                    for name in names}
            check('install/assets', 'each engine copy is byte-identical to its .veldo copy [%s]' % same, all(same.values()))
            closure = (installed or {}).get('closure') or []
            check('install/assets', 'the installation lays down its work configuration 0600 and the fixed executable '
                  'carries the loop\'s organs [%s, %s]' % (install_error, [n for n in ('control_account_limit.py',
                                                                                        'control_assignment.py',
                                                                                        'entity_contract.py',
                                                                                        'control_account_pool.py')
                                                                                   if n not in closure]),
                  installed is not None and config.get('work') == str(Path(installed['home']) / 'config' / 'work.json')
                  and oct(os.stat(config['work']).st_mode & 0o777) == '0o600'
                  and json.loads(Path(config['work']).read_text()) == WORK
                  and all(n in closure for n in ('control_account_limit.py', 'control_assignment.py',
                                                 'entity_contract.py', 'control_account_pool.py'))
                  and all((installed_bin / n).read_bytes() == (mods / n).read_bytes() for n in PRODUCTION)
                  and [c[0] for c in systemd.calls] == ['daemon-reload'])
            check('install/assets', 'a work configuration naming a repository this instance does not serve is refused '
                  'by name before anything is written',
                  _refused_install(CS, base, workspace, trust_file, keys, PROFILE, ADAPTERS, WORK, REPO, Recording)
                  == 'invalid_input:work:repository')

        # The installed service: the unit's ExecStart, run on its installed configuration.
        service_err = base / 'service.err'
        if installed is not None:
            environment = {k: v for k, v in os.environ.items() if k != 'NOTIFY_SOCKET'}
            with open(str(service_err), 'wb') as err:
                service_proc[0] = subprocess.Popen([config['python'], config['executable'], 'serve', installed['config']],
                                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err,
                                                   env=environment)
            wait_until(lambda: os.path.exists(config['socket']), 30)
        service_pid = service_proc[0].pid if service_proc[0] is not None else None
        booted = time.time()

        # AC1: a packet that advanced the journal wakes one pass, which offers every assigned eligible unit.
        phase1 = {}
        with region('loop/runner-in-service', 'loop/journal-wake-offers', 'loop/review-offered'):
            script(U['U1'], 'build', [held('u1')])
            script(U['U1'], 'review', [SUCCESS])
            script(U['U2'], 'build', [held('u2-never')])
            # Nothing starts a pass while nothing woke the loop, the service's own start included.
            time.sleep(1.5)
            phase1['quiet_start'] = passes()
            claim(U['U1'])
            claim(U['U2'])
            before = last_pass()
            phase1['note'] = note()
            first = wait_pass(lambda p: True, before, 60)
            phase1['first'] = first
            both = offered(first, station='build')
            wanted = {U['U1'], U['U2']}
            check('loop/journal-wake-offers', 'the signed packet that advanced the journal started one pass, with the '
                  'journal as its only source [%s, %s]' % (phase1['note'], (first or {}).get('sources')),
                  first is not None and first['sources'] == ['journal'])
            check('loop/journal-wake-offers', 'the pass offered every assigned eligible unit, and only those, each to the '
                  'Runner with this host and one of the owner\'s accounts [%s]'
                  % [(o['unit'], o.get('account'), o.get('host'), o.get('result')) for o in both],
                  {o['unit'] for o in both} == wanted and len(both) == 2
                  and all(o['host'] == HOST and o['account'] in ACCOUNTS and o['result'] == 'accepted' for o in both)
                  and len({o['account'] for o in both}) == 2)
            stored = {name: dispatches(name, 'build') for name in wanted}
            check('loop/journal-wake-offers', 'each offer is a prepared dispatch in the store on the account the pass names '
                  '[%s]' % {n: [(r['state'], r['contract']['reservation']['account']) for r in v] for n, v in stored.items()},
                  all(len(v) == 1 and v[0]['contract']['reservation']['account']
                      == next((o['account'] for o in both if o['unit'] == n), None) for n, v in stored.items()))
            halted = [r for r in (first or {}).get('refused') or [] if r['unit'] == U['UP']]
            check('loop/journal-wake-offers', 'the paused project\'s assigned unit is not offered: the Gate refuses it '
                  'project_not_active:PAUSED [%s, %s]' % (paused.get('ok'), halted),
                  paused.get('ok') is True and len(halted) == 1 and 'project_not_active:PAUSED' in halted[0]['refusals']
                  and not dispatches(U['UP']))
            check('loop/journal-wake-offers', 'an unassigned unit is neither offered nor refused, and nothing ran before '
                  'the packet [%s]' % [(p['pass'], p['sources']) for p in phase1['quiet_start']],
                  not dispatches(U['UX']) and all(U['UX'] not in (o['unit'] for o in offered(first))
                                                  for _ in [0]) and phase1['quiet_start'] == [])

            # The Runner is inside the installed service: its pass log, its principal, its receiver processes.
            u1 = (stored.get(U['U1']) or [{}])[0]
            wait_until(lambda: (dispatches(U['U1'], 'build') or [{}])[0].get('state') == 'running', 30)
            u1 = (dispatches(U['U1'], 'build') or [{}])[0]
            receiver = u1.get('receiver') or {}
            prepared_by = independent("SELECT principal FROM journal WHERE substr(command_id, 1, ?) = ?",
                                      len('dispatch/prepare/%s/' % u1.get('dispatch_id')),
                                      'dispatch/prepare/%s/' % u1.get('dispatch_id'))
            parent = (proc_stat(receiver.get('pid')) or [None, None])[1] if isinstance(receiver.get('pid'), int) else None
            lock = {}
            with contextlib.suppress(OSError, ValueError):
                lock = json.loads(Path(config.get('lock') or base / 'no-lock').read_text())
            status = send({'operation': 'inspect', 'entity_ids': []})
            loop_status = ((status or {}).get('result') or status or {}).get('loop') or {}
            check('loop/runner-in-service', 'the installed service process holds the authority lock, its log holds the '
                  'pass, its principal prepared the dispatch and the launch receiver is its child process '
                  '[%s, %s, %s, %s]' % (lock.get('pid'), service_pid, prepared_by, parent),
                  service_pid is not None and lock.get('pid') == service_pid and bool(passes())
                  and prepared_by == [('authority',)] and parent is not None and int(parent) == service_pid)
            check('loop/runner-in-service', 'the service reports its factory loop available with the passes it ran '
                  '[%s]' % loop_status, loop_status.get('available') is True and loop_status.get('passes', 0) >= 1)

            # AC1: a build ending on its launch pipe leads to its review being offered with no other input.
            mark = last_pass()
            release('u1')
            ending = wait_pass(lambda p: bool(ended(p, U['U1'])), mark, 60)
            phase1['ending'] = ending
            review = offered(ending, U['U1'], 'review')
            build_record = (dispatches(U['U1'], 'build') or [{}])[0]
            check('loop/review-offered', 'the build\'s end on its launch pipe started a pass whose only source is the run\'s '
                  'end, and nothing else ran between [%s, %s]' % ((ending or {}).get('sources'),
                                                                 [(p['pass'], p['sources']) for p in passes() if p['pass'] > mark]),
                  ending is not None and ending['sources'] == ['run_end'] and ending['pass'] == mark + 1)
            check('loop/review-offered', 'the pass settled the build as exited and offered its review, following that '
                  'build, from its commit, to an independent reviewer [%s, %s]'
                  % (ended(ending, U['U1']), [(o['station'], o['follows'], o['identity']) for o in review]),
                  [(e['station'], e['state']) for e in ended(ending, U['U1'])] == [('build', 'exited')]
                  and len(review) == 1 and review[0]['follows'] == build_record.get('dispatch_id')
                  and review[0]['identity'] == REVIEWER and review[0]['commit'] == dig(build_record, 'contract', 'source', 'commit'))
            reviews = dispatches(U['U1'], 'review')
            check('loop/review-offered', 'the review is a dispatch in the store [%s]' % [(r['state'], r['contract']['attempt'])
                                                                                       for r in reviews],
                  len(reviews) == 1 and reviews[0]['dispatch_id'] == review[0]['dispatch_id'] if review else False)
            wait_pass(lambda p: bool([e for e in ended(p, U['U1']) if e['station'] == 'review']), mark, 60)

        # AC2: a receiver that dies mid-run still wakes the loop; its run is outcome_unknown, its account slot free.
        with region('loop/receiver-death'):
            for key in ('B1', 'B2', 'B3'):
                script(U[key], 'build', [{'script': [thread(), turn(), {'wait': gate('blockers')},
                                                     failed('internal error; agent loop died unexpectedly')], 'code': 1}])
                claim(U[key])
            script(U['W'], 'build', [{'script': [thread(), turn(), {'wait': gate('w')},
                                                 failed('internal error; agent loop died unexpectedly')], 'code': 1}])
            claim(U['W'])
            mark = last_pass()
            note()
            filled = wait_pass(lambda p: 'journal' in p['sources'], mark, 60)
            victim = (dispatches(U['U2'], 'build') or [{}])[0]
            account = victim.get('contract', {}).get('reservation', {}).get('account')
            waiting = [w for w in (filled or {}).get('waiting') or [] if w['unit'] == U['W']]
            check('loop/receiver-death', 'with every other account busy, the waiting unit waits for an account [%s, %s]'
                  % ([(o['unit'], o['account']) for o in offered(filled)], waiting),
                  len(offered(filled)) == 3 and len(waiting) == 1 and victim.get('state') == 'running')
            receiver = victim.get('receiver') or {}
            worker = victim.get('process') or {}
            killed = False
            fields = proc_stat(receiver['pid']) if isinstance(receiver.get('pid'), int) else None
            if fields and fields[19] == receiver.get('start'):
                mark = last_pass()
                os.kill(receiver['pid'], signal.SIGKILL)
                killed = True
            death = wait_pass(lambda p: bool(ended(p, U['U2'])), mark, 60)
            time.sleep(2.0)
            after = [p for p in passes() if p['pass'] > mark]
            record = (dispatches(U['U2'], 'build') or [{}])[0]
            slot = worker_slot(victim.get('dispatch_id', ''))
            call = invocation(victim.get('dispatch_id', ''))
            took = offered(death, U['W'], 'build')
            check('loop/receiver-death', 'killing the receiver mid-run started exactly one pass, whose only source is the '
                  'run\'s end [%s, %s]' % (killed, [(p['pass'], p['sources']) for p in after]),
                  killed and death is not None and len(after) == 1 and death['sources'] == ['run_end'])
            check('loop/receiver-death', 'the run is recorded outcome_unknown under its original dispatch, its receiver '
                  'lost [%s, %s]' % ((record.get('state'), record.get('reason')), ended(death, U['U2'])),
                  record.get('dispatch_id') == victim.get('dispatch_id') and record.get('state') == 'unknown'
                  and record.get('reason') == 'outcome_unknown'
                  and [(e['state'], e['reason'], e['receiver_lost']) for e in ended(death, U['U2'])]
                  == [('unknown', 'outcome_unknown', True)])
            check('loop/receiver-death', 'its usage reservation is retained: the worker slot is not retired and the '
                  'invocation keeps its reserved charge, unsettled [%s, %s, %s]'
                  % (slot.get('retired'), call.get('state'), call.get('charge')),
                  slot.get('retired') is False and call.get('state') == 'pending' and call.get('charge') == call.get('reserved')
                  and bool(call.get('reserved')))
            check('loop/receiver-death', 'its account slot is freed once its worker is gone, and the next dispatch, in '
                  'that same pass, takes it [%s, %s, %s]' % (alive(worker), (death or {}).get('released'),
                                                             [(o['unit'], o['account']) for o in took]),
                  not alive(worker) and bool(slot.get('account_released'))
                  and [r['dispatch_id'] for r in (death or {}).get('released') or []] == [victim.get('dispatch_id')]
                  and len(took) == 1 and took[0]['account'] == account)
            check('loop/receiver-death', 'the unit\'s next station is not offered as if the run had succeeded [%s]'
                  % dispatches(U['U2'], 'review'),
                  not dispatches(U['U2'], 'review') and not any(offered(p, U['U2']) for p in after))
            mark = last_pass()
            release('blockers')
            release('w')
            wait_until(lambda: all((dispatches(U[k], 'build') or [{}])[0].get('state') == 'exited'
                                   for k in ('B1', 'B2', 'B3', 'W')), 60)
            wait_until(lambda: sum(len(ended(p)) for p in passes() if p['pass'] > mark) >= 4, 30)

        # AC3: a run that ended account_limit is dispatched again on another account, or put to the owner.
        far = time.time() + 3 * 3600
        exhausted = []
        with region('loop/rerun-another-account'):
            script(U['L1'], 'build', [limited(far, wait='l1'), SUCCESS])
            script(U['L1'], 'review', [SUCCESS])
            claim(U['L1'])
            mark = last_pass()
            note()
            # While the run works, the workspace moves on: a re-run is from the run's own accepted commit, not HEAD.
            wait_until(lambda: (dispatches(U['L1'], 'build') or [{}])[0].get('state') == 'running', 30)
            (workspace / 'NEWS').write_text('moved on\n')
            GP.run(['git', '-C', str(workspace), 'add', 'NEWS'], check=True, capture_output=True)
            GP.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'moved on'],
                   check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            head = GP.run(['git', '-C', str(workspace), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                          text=True).stdout.strip()
            mark = last_pass()
            release('l1')
            decided = wait_pass(lambda p: bool([d for d in p.get('decisions') or [] if d['unit'] == U['L1']]), mark, 60)
            first_run = (dispatches(U['L1'], 'build') or [{}])[0]
            first_account = first_run.get('contract', {}).get('reservation', {}).get('account')
            exhausted.append(first_account)
            again = offered(decided, U['L1'], 'build')
            decision = [d for d in (decided or {}).get('decisions') or [] if d['unit'] == U['L1']]
            check('loop/rerun-another-account', 'the run ended account_limit with its account\'s window and reset, and '
                  'VELDO-0160\'s decision over its execution record is re-run [%s, %s]'
                  % (invocation(first_run.get('dispatch_id', '')).get('outcome'), decision),
                  invocation(first_run.get('dispatch_id', '')).get('outcome') == 'account_limit'
                  and [(d['decision'], d['basis']) for d in decision] == [('rerun', 'no_write_capable_server')]
                  and (decided or {}).get('sources') == ['run_end'])
            check('loop/rerun-another-account', 'one new dispatch of the same station, under a new dispatch identity, on '
                  'another account of the role\'s engine, from the same accepted commit [%s]'
                  % [(o['attempt'], o['account'], o['rerun_of'], o['commit']) for o in again],
                  len(again) == 1 and again[0]['rerun_of'] == first_run.get('dispatch_id')
                  and again[0]['dispatch_id'] != first_run.get('dispatch_id') and again[0]['attempt'] == 2
                  and again[0]['account'] in ACCOUNTS and again[0]['account'] != first_account
                  and again[0]['adapter'] == 'codex' and again[0]['commit'] == dig(first_run, 'contract', 'source', 'commit')
                  and again[0]['commit'] != head)
            wait_until(lambda: [r['state'] for r in dispatches(U['L1'])] == ['exited', 'exited', 'exited'], 60)
            reset_at = dig(ACC.read(setup, first_account) if first_account else None, 'windows', 'usage_limit', 'reset_at')
            ended_at = next((h['at'] for h in first_run.get('history') or [] if h.get('state') == 'exited'), None)
            onto = [r for r in dispatches() if r['contract']['reservation']['account'] == first_account
                    and r['history'][0]['at'] > (ended_at or 0)]
            check('loop/rerun-another-account', 'nothing is sent to the exhausted account before its reported reset '
                  '[%s, %s]' % (reset_at, [r['dispatch_id'] for r in onto]),
                  isinstance(reset_at, (int, float)) and reset_at > time.time() and onto == [])

        with region('loop/ask-before-rerun', 'loop/owner-yes-reruns', 'loop/owner-no-stops'):
            for key in ('L2', 'L3'):
                script(U[key], 'build', [limited(far, call=True), SUCCESS])
                script(U[key], 'review', [SUCCESS])
                claim(U[key])
            mark = last_pass()
            note()
            wait_until(lambda: len([a for p in passes() if p['pass'] > mark for a in p.get('asked') or []]) >= 2, 60)
            asked = [a for p in passes() if p['pass'] > mark for a in p.get('asked') or []]
            runs = {key: (dispatches(U[key], 'build') or [{}])[0] for key in ('L2', 'L3')}
            exhausted += [r.get('contract', {}).get('reservation', {}).get('account') for r in runs.values()]
            questions = {a['subject']['ref']: a for a in assignments() if (a.get('subject') or {}).get('kind')
                         == 'account_limit_rerun'}
            for key in ('L2', 'L3'):
                question = questions.get(runs[key].get('dispatch_id')) or {}
                named = [a for a in asked if a['unit'] == U[key]]
                check('loop/ask-before-rerun', '%s: a run whose record shows a call to an MCP tool not marked read-only '
                      'raised one ordinary decision request to the project\'s owner, naming the call [%s, %s]'
                      % (key, [(a['outcome'], a['owner'], [(c['server'], c['tool'], c['reason']) for c in a['calls']])
                               for a in named], (question.get('kind'), question.get('state'), question.get('owner'))),
                      len(named) == 1 and named[0]['outcome'] is True and named[0]['owner'] == 'owner'
                      and [(c['server'], c['tool'], c['reason']) for c in named[0]['calls']]
                      == [('tracker', 'add_comment', 'unconfigured_call')]
                      and question.get('kind') == 'decision' and question.get('owner') == 'owner'
                      and question.get('state') == 'OFFERED' and question.get('choices') == ['rerun', 'stop']
                      and 'tracker/add_comment' in (question.get('brief') or ''))
            # Another wake: still nothing dispatched, and no second question, while he has not answered.
            mark = last_pass()
            note()
            idle = wait_pass(lambda p: 'journal' in p['sources'], mark, 60)
            check('loop/ask-before-rerun', 'no dispatch until he answers: another pass leaves both units awaiting him and '
                  'asks nothing again [%s, %s]' % ((idle or {}).get('awaiting'), [len(dispatches(U[k])) for k in ('L2', 'L3')]),
                  idle is not None and sorted(a['unit'] for a in idle.get('awaiting') or []) == sorted([U['L2'], U['L3']])
                  and not idle.get('asked') and all(len(dispatches(U[k])) == 1 for k in ('L2', 'L3'))
                  and not offered(idle, U['L2']) and not offered(idle, U['L3']))

            # His yes dispatches it as a re-run would.
            mark = last_pass()
            yes = answer(questions.get(runs['L2'].get('dispatch_id')) or {}, 'rerun')
            rerun = wait_pass(lambda p: bool(offered(p, U['L2'], 'build')), mark, 60)
            again = offered(rerun, U['L2'], 'build')
            check('loop/owner-yes-reruns', 'his answer arrived as a signed packet through the service and its pass '
                  'dispatched the same station on another account from the same commit [%s, %s, %s]'
                  % (yes, (rerun or {}).get('sources'), [(o['attempt'], o['account'], o['rerun_of']) for o in again]),
                  rerun is not None and rerun['sources'] == ['journal'] and len(again) == 1
                  and again[0]['rerun_of'] == runs['L2'].get('dispatch_id') and again[0]['attempt'] == 2
                  and again[0]['account'] not in exhausted
                  and again[0]['commit'] == dig(runs['L2'], 'contract', 'source', 'commit'))
            wait_until(lambda: [r['state'] for r in dispatches(U['L2'])] == ['exited', 'exited', 'exited'], 60)

            # His no leaves the unit stopped.
            mark = last_pass()
            no = answer(questions.get(runs['L3'].get('dispatch_id')) or {}, 'stop')
            stop = wait_pass(lambda p: 'journal' in p['sources'], mark, 60)
            mark = last_pass()
            note()
            later = wait_pass(lambda p: 'journal' in p['sources'], mark, 60)
            check('loop/owner-no-stops', 'his stop leaves the unit stopped, in that pass and the next [%s, %s, %s]'
                  % (no, [s['unit'] for s in (stop or {}).get('stopped') or []], [len(dispatches(U['L3']))]),
                  stop is not None and [s['unit'] for s in stop.get('stopped') or []] == [U['L3']]
                  and later is not None and [s['unit'] for s in later.get('stopped') or []] == [U['L3']]
                  and len(dispatches(U['L3'])) == 1 and not offered(stop, U['L3']) and not offered(later, U['L3']))

        # AC1 and AC4: a unit waiting for an account's reported reset wakes a pass at that reset and at no other time.
        with region('loop/reset-timer-wake', 'loop/no-other-timer'):
            # The reset is the end of a minute (Codex states its reset to the minute): wait for one far enough ahead
            # to watch the service for longer than every interval it uses.
            wait_until(lambda: 15 <= end_of_minute(time.time()) - time.time() <= 50, 70)
            reset = end_of_minute(time.time())
            script(U['L4'], 'build', [limited(reset - 30), SUCCESS])
            script(U['L4'], 'review', [SUCCESS])
            claim(U['L4'])
            mark = last_pass()
            note()
            waiting = wait_pass(lambda p: bool([w for w in p.get('waiting') or [] if w['unit'] == U['L4']]), mark, 60)
            first_run = (dispatches(U['L4'], 'build') or [{}])[0]
            quiet_from = last_pass()
            switched = switches(service_pid) if service_pid else None
            watched_from = time.time()
            wait_until(lambda: time.time() >= reset - 1.0, 70)
            quiet = [p for p in passes() if p['pass'] > quiet_from]
            watched = time.time() - watched_from
            switched = (switches(service_pid) or 0) - (switched or 0)
            woke = wait_pass(lambda p: 'account_reset' in p['sources'], quiet_from, 30)
            time.sleep(0.5)
            resets = [p for p in passes() if p['pass'] > quiet_from and 'account_reset' in p['sources']]
            between = [p for p in passes() if woke is not None and quiet_from < p['pass'] < woke['pass']]
            intervals = (getattr(CS, 'ACCEPT_SECONDS', 0.25), getattr(getattr(CS, 'CH', None), 'POLL_SECONDS', 1.0))
            entry = [w for w in (waiting or {}).get('waiting') or [] if w['unit'] == U['L4']]
            check('loop/reset-timer-wake', 'the unit waits for the account\'s reported reset, and the pass set its timer to '
                  'that earliest reset [%s, %s, %s]' % (entry, (waiting or {}).get('timer'), reset),
                  len(entry) == 1 and entry[0]['until'] == reset and entry[0]['rerun_of'] == first_run.get('dispatch_id')
                  and waiting['timer'] == reset)
            again = offered(woke, U['L4'], 'build')
            check('loop/reset-timer-wake', 'at the reset the timer started a pass whose only source is the reset, and it '
                  'offered the waiting unit on the account the reset freed [%s, %s]'
                  % ((woke or {}).get('sources'), [(o['account'], o['attempt']) for o in again]),
                  woke is not None and woke['sources'] == ['account_reset'] and woke['at'] >= reset and len(again) == 1
                  and again[0]['account'] == dig(first_run, 'contract', 'reservation', 'account') and again[0]['attempt'] == 2)
            check('loop/no-other-timer', 'with the unit waiting, no journal advance and no run ending, no pass started for '
                  '%.1f s, longer than every interval the service uses, while its accept timeout kept waking it '
                  '[%s, %s switches]' % (watched, [(p['pass'], p['sources']) for p in quiet], switched),
                  quiet == [] and watched > 2 * max(intervals) and switched >= int(watched / intervals[0] / 2))
            check('loop/no-other-timer', 'exactly one pass started at the reset, and none between the unit\'s wait and '
                  'it [%s, %s]' % ([(p['pass'], p['sources'], round(p['at'] - reset, 3)) for p in resets],
                                   [(p['pass'], p['sources']) for p in between]),
                  woke is not None and resets == [woke] and between == [])
            check('loop/no-other-timer', 'across the whole run every pass came from a wake source, the service\'s start '
                  'included none, and the reset timer started only that one [%s]'
                  % sorted({tuple(p['sources']) for p in passes()}),
                  phase1.get('quiet_start') == [] and bool(passes())
                  and all(set(p['sources']) <= {'journal', 'run_end', 'account_reset'} and p['sources'] for p in passes())
                  and len([p for p in passes() if 'account_reset' in p['sources']]) == 1)
            wait_until(lambda: [r['state'] for r in dispatches(U['L4'])] == ['exited', 'exited', 'exited'], 60)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        with contextlib.suppress(Exception):
            for name in ('u1', 'u2-never', 'blockers', 'w', 'l1'):
                (base / 'gates' / name).write_text('go')
        proc = service_proc[0]
        if proc is not None and proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        with contextlib.suppress(Exception):
            text = (base / 'service.err').read_text()[-1500:]
            if text.strip():
                print('  VELDO-0154 service stderr: %s' % text.replace('\n', ' | '))
        for conn in connections:
            with contextlib.suppress(Exception):
                conn.close()
        time.sleep(0.5)
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0154 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0154 %s detail: no check ran' % name)
        expect('VELDO-0154 ' + name, ok)
    print('VELDO-0154 suite seconds: %.3f' % (time.monotonic() - started))


def _refused_install(CS, base, workspace, trust_file, keys, profile, adapters, work, repository, recording):
    """The refusal of an installation whose work configuration names a repository the instance does not serve,
    into a probe tree of its own, and only when nothing was left behind; None when it was accepted."""
    import json
    from pathlib import Path
    probe = base / 'probe'
    wrong = dict(work, repositories={'repo-elsewhere': work['repositories'][repository]})
    (base / 'work-elsewhere.json').write_text(json.dumps(wrong))
    try:
        CS.install([str(workspace)], host_trust=str(trust_file), key_directory=str(keys),
                   install_root=str(probe / 'install'), unit_dir=str(probe / 'units'), profile=profile,
                   adapters=adapters, writable=[str(base / 'work')], runner=recording(),
                   work=str(base / 'work-elsewhere.json'))
    except Exception as error:  # noqa: BLE001 - the refusal, or what else ended it, is data for the row
        left = sorted(str(p) for p in probe.rglob('*')) if probe.is_dir() else []
        return getattr(error, 'code', type(error).__name__) if not left else 'left:%s' % left
    return None


_v154_suite()
