"""VELDO-0232: Antigravity's CLI as the third engine, through the qualify command's own steps and a real Runner,
receiver and exec wrapper.

Run: python3 scripts/selftest.py --suite 127_veldo_0232_antigravity

Only shared ROOT, expect and fast_temp are consumed. The fake agy is a shell script that execs a Python fixture and
carries, after that line, the byte forms the committed extractor reads (the step type enum and the harness tool
fields of its protobuf descriptors, the changelog sentences naming the stream's events and finished reasons, the
credential names, the refusal text and the load places), built from the qualified record's own tables; its help
and version are the record's. The store, accounts, reservations, claims, dispatches, the receiver and its wrapper
are production code; the reported-identity wrapper runs locally, so no user service manager, model, real account
or network is used. Writes only temporary files.
"""

# VELDO-0232: the qualified Antigravity is the engines record's (python3 .veldo/qualify.py writes it), never typed.
AGY_ENGINES = __import__('json').loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())


def _v232_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_engine_antigravity.py': ROOT / ".veldo" / "control_engine_antigravity.py",
        'qualify.py': ROOT / ".veldo" / "qualify.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'accounts.py': ROOT / ".veldo" / "accounts.py",
        'control_account_limit.py': ROOT / ".veldo" / "control_account_limit.py",
        'control_reservation_runtime.py': ROOT / ".veldo" / "control_reservation_runtime.py",
    }
    EXTRACTOR = ROOT / 'proof' / 'VELDO-0232' / 'extract_agy.py'
    ROWS = ('qualify/record', 'qualify/new-items', 'qualify/rerun-bytes', 'qualify/output', 'pin/copy',
            'pin/pinned-path', 'bind/stale', 'launch/flags', 'launch/settings', 'launch/environment',
            'launch/tool-outside-role', 'launch/role-mcp', 'launch/profile', 'launch/clone', 'stream/record',
            'stream/meter', 'stream/missing-result', 'stream/verdicts', 'stream/limit', 'stream/tool-calls',
            'accounts/profile', 'accounts/credential-refused', 'accounts/paid-path',
            'accounts/one-registration', 'accounts/pool')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn):
        """(value, error): a refusal, or the qualify command's SystemExit, is data for the row, never a raise."""
        try:
            return fn(), None
        except (Exception, SystemExit) as error:  # noqa: BLE001
            return None, error

    def code(error):
        return getattr(error, 'code', type(error).__name__) if error is not None else None

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    VERSION = AGY_ENGINES['antigravity']['version']
    shipped = json.loads((ROOT / '.veldo' / 'runtime' / 'antigravity-qualification.json').read_text())
    TABLES = shipped['tables']
    base = Path(tempfile.mkdtemp(prefix='v232-', dir=fast_temp()))
    connections = []

    def camel(name):
        return ''.join(part.capitalize() for part in name.split('_'))

    def blob(tables, steps=(), tools=()):
        """The byte forms the extractor reads, from a record's tables plus `steps` and `tools`."""
        out = []
        for step in sorted(set(tables['stream']['step_types']) | set(steps)):
            name = b'CORTEX_STEP_TYPE_' + step.upper().encode()
            out.append(b'\x0a' + bytes([len(name)]) + name + b'\x10\x01')
        step_tools = {'invoke_subagent', 'browser_subagent', 'mcp_tool'}
        for tool in sorted(set(tables['tool_registry']) | set(tools)):
            if tool in step_tools:
                continue
            field = (tool + '_config') if tool == 'tool_search' else tool
            kind = 'ToolSearchConfig' if tool == 'tool_search' else camel(tool) + 'ToolConfig'
            out.append(b'\x0a' + bytes([len(field)]) + field.encode() + b'\x18\x01 \x01(\x0b2'
                       + bytes([len(kind) + 26]) + b'.antigravity.localharness.' + kind.encode() + b'R')
        events = tables['stream']['events']
        out.append(('emits typed %s, and terminal `%s` events.' % (
            ', '.join('`%s`' % e for e in events[:-1]), events[-1])).encode())
        reasons = tables['stream']['finished_reasons']
        out.append(('Added a `finished_reason` field to the result that says why a turn ended early, %s, or `%s` '
                    'for any other failure; the field is omitted when the turn finishes normally.' % (
                        ', '.join('`%s` when x' % r for r in reasons[:-1]), reasons[-1])).encode())
        out += [n.encode() for n, held in tables['credentials'].items() if held]
        out += [b'json:"cache_read_tokens"', b'AGY_ERROR: {}']
        out += [text.encode() for text, _ in tables['limits']['refusals']]
        out += [(p['path'] + '/').encode() for kind in ('profile', 'clone') for p in tables['load_places'][kind]]
        out += [n.encode() for n in tables['session_environment']]
        return b'\x00'.join(out) + b'\x00'

    markers = base / 'markers'
    markers.mkdir()
    impl = base / 'fake_agy.py'
    help_text = 'Usage of agy:\n' + ''.join('  %-30s fixture\n' % o for o in TABLES['options']) + \
        '\nAvailable subcommands:\n' + ''.join('  %-15s fixture\n' % c for c in TABLES['subcommands'])
    impl.write_text('''import json, os, sys, time
from pathlib import Path
binary, args = sys.argv[1], sys.argv[2:]
if args[:1] == ['--version']:
    print(%(version)r)
    sys.exit(0)
if args[:1] == ['--help']:
    sys.stdout.write(%(help)r)
    sys.exit(0)
settings = None
if '--settings' in args:
    settings = json.loads(Path(args[args.index('--settings') + 1]).read_text())
line = sys.stdin.readline()
try:
    message = json.loads(line)
    packet = json.loads(message['message']['content'])
except (ValueError, KeyError, TypeError):
    message, packet = None, {}
own = {'binary': binary, 'argv': args, 'env': dict(os.environ), 'settings': settings, 'stdin': line,
       'message': message, 'cwd': os.getcwd(), 'dispatch': os.environ.get('VELDO_DISPATCH_ID', ''), 'pid': os.getpid()}
markers = Path(%(markers)r)
(markers / ('%%d.json' %% os.getpid())).write_text(json.dumps(own))
payload = packet.get('payload') or {}
for step in payload.get('script') or []:
    if 'line' in step:
        text = json.dumps(step['line'])
    elif 'raw' in step:
        text = step['raw']
    else:
        time.sleep(step.get('sleep', 0))
        continue
    with open(markers / ('%%d.out' %% os.getpid()), 'a') as out:
        out.write(text + chr(10))
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
sys.exit(payload.get('code', 0))
''' % {'version': VERSION, 'help': help_text, 'markers': str(markers)})

    def fake(path, steps=(), tools=()):
        path.write_bytes(('#!/bin/sh\nexec %s -B %s "$0" "$@"\n' % (sys.executable, impl)).encode()
                         + blob(TABLES, steps, tools))
        path.chmod(0o755)
        return path

    try:
        # The tree the qualify command writes: the modules (with their runtime records) and the extractor.
        tree = base / 'tree'
        mods = tree / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copytree(ROOT / '.veldo' / 'runtime', mods / 'runtime')
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        (tree / 'proof' / 'VELDO-0232').mkdir(parents=True)
        shutil.copyfile(EXTRACTOR, tree / 'proof' / 'VELDO-0232' / 'extract_agy.py')
        Q = load('v232_qualify', mods / 'qualify.py')
        decisions = json.loads((mods / 'runtime' / 'capability-decisions.json').read_text())
        factory = base / 'factory'
        factory.mkdir(mode=0o700)

        def qualify(binary, state_root):
            """The qualify command's Antigravity steps: the extractor in write mode, then the record and the pin."""
            done = subprocess.run([sys.executable, '-B', str(tree / 'proof/VELDO-0232/extract_agy.py'),
                                   '--antigravity', str(binary)], cwd=tree, capture_output=True, text=True,
                                  timeout=120)
            if done.returncode:
                raise RuntimeError('extractor: ' + done.stderr[-300:])
            written = ['proof/VELDO-0232/agy-tables.json']
            entry, pinned = Q.antigravity_entry(binary, state_root)
            agy = Q.antigravity_step(tree, binary, entry, pinned, decisions, written)
            return entry, pinned, agy, written, Q.antigravity_lines(entry, agy, pinned)

        # AC1: the record the qualified tables reproduce, then a newer binary with one more step type and tool.
        first = fake(base / 'agy-first')
        result, error = attempt(lambda: qualify(first, factory))
        check('qualify/record', 'the command qualifies the fake [%s]' % code(error), error is None)
        entry, pinned, agy, written, lines = result if result else ({}, None, {}, [], [])
        check('qualify/record', 'the engines entry names the version, the pinned copy and the digest',
              entry.get('version') == VERSION and entry.get('sha256') == Q.digest(first)
              and pinned == factory.resolve() / 'engines' / 'antigravity' / VERSION
              and entry.get('binary') == Q.home_form(pinned))
        check('qualify/record', 'the record holds the tables the module reads',
              agy.get('tool_registry') == TABLES['tool_registry']
              and agy.get('stream', {}).get('step_types') == TABLES['stream']['step_types']
              and agy.get('environment') == {'AGY_CLI_DISABLE_AUTO_UPDATE': '1'}
              and set(agy.get('tool_classification') or {}) == set(TABLES['tool_registry']))
        check('qualify/record', 'the same tables bring nothing new', agy.get('new_capabilities') == [])
        before = {name: (tree / name).read_bytes() for name in ('.veldo/runtime/antigravity-qualification.json',
                                                                'proof/VELDO-0232/agy-tables.json')}
        again, error = attempt(lambda: qualify(first, factory))
        check('qualify/rerun-bytes', 'run twice on the same binary, every file holds the same bytes [%s]' % code(error),
              error is None and all((tree / name).read_bytes() == data for name, data in before.items())
              and again[4] == lines)
        NEW_STEP, NEW_TOOL = 'veldo_fixture_step', 'veldo_fixture_tool'
        newer = fake(base / 'agy-newer', steps=[NEW_STEP], tools=[NEW_TOOL])
        result, error = attempt(lambda: qualify(newer, factory))
        check('qualify/new-items', 'the newer binary qualifies [%s]' % code(error), error is None)
        entry2, pinned2, agy2, written2, lines2 = result if result else ({}, None, {}, [], [])
        items = {(i['kind'], i['name']): i for i in agy2.get('new_capabilities') or []}
        check('qualify/new-items', 'the new step type and the new tool are listed with their decision',
              items.get(('step_types', NEW_STEP), {}).get('decision') == 'unevaluated'
              and items.get(('tools', NEW_TOOL), {}).get('decision') == 'unevaluated'
              and all(i.get('reason') for i in items.values()))
        check('qualify/new-items', 'the new tool is outward and the new step type stays out of the reader',
              (agy2.get('tool_classification') or {}).get(NEW_TOOL, {}).get('class') == 'outward'
              and NEW_STEP not in (agy2.get('stream') or {}).get('step_types', [NEW_STEP]))
        check('qualify/output', 'the output names the engine, its pinned copy and each new item with its decision',
              any(l.startswith('qualified antigravity %s (' % VERSION) and entry2.get('sha256', '?') in l for l in lines2)
              and any(l == 'pinned antigravity %s' % pinned2 for l in lines2)
              and 'new antigravity step_types %s: unevaluated' % NEW_STEP in ' '.join(lines2)
              and 'new antigravity tools %s: unevaluated' % NEW_TOOL in ' '.join(lines2))
        check('qualify/output', 'it writes the record to every runtime copy and pins the copy',
              '.veldo/runtime/antigravity-qualification.json' in written2 and str(pinned2) in written2)
        A = load('v232_engine', mods / 'control_engine_antigravity.py')
        record = A.load_qualification(mods / 'runtime' / 'antigravity-qualification.json')
        info = os.lstat(pinned2) if pinned2 else None
        check('pin/copy', 'the pinned copy is a regular 0555 file holding the qualified bytes',
              info is not None and (info.st_mode & 0o7777) == 0o555 and pinned2.read_bytes() == newer.read_bytes()
              and record['sha256'] == Q.digest(pinned2))
        bound, error = attempt(lambda: A.bind({'executable': {'version': VERSION}}, str(factory), record))
        check('qualify/new-items', 'a launch of the newly qualified binary binds [%s]' % code(error),
              error is None and bound['path'] == str(pinned2))
        extra, error = attempt(lambda: A.baseline(bound, {'config': str(base / 'cfg-probe')}, {}))
        check('qualify/new-items', 'and its baseline is laid [%s]' % code(error),
              error is None and NEW_TOOL in json.loads(extra['files']['settings.json'])['permissions']['deny'])
        # bind refuses a version or a digest the record does not name, before anything is accepted.
        _, error = attempt(lambda: A.bind({'executable': {'version': VERSION + '.9'}}, str(factory), record))
        check('bind/stale', 'another version is refused by name', code(error) == 'stale_subject:engine_version')
        other = base / 'factory-other'
        (other / 'engines' / 'antigravity').mkdir(parents=True, mode=0o700)
        shutil.copyfile(first, other / 'engines' / 'antigravity' / VERSION)
        (other / 'engines' / 'antigravity' / VERSION).chmod(0o555)
        _, error = attempt(lambda: A.bind({'executable': {'version': VERSION}}, str(other), record))
        check('bind/stale', 'a pinned copy whose digest differs is refused by name',
              code(error) == 'stale_subject:engine_digest')
        broken = json.loads(json.dumps(record))
        broken['baseline'] = dict(broken['baseline'], options=['--sandbox'])
        _, error = attempt(lambda: A.bind({'executable': {'version': VERSION}}, str(factory), broken))
        check('bind/stale', 'a record without the module baseline is refused by name',
              code(error) == 'missing_evidence:engine_baseline:' + VERSION)

        # THE LAUNCH HARNESS (AC2-AC4): the production store, accounts, reservations, claims and receiver.
        S = load('v232_store', mods / 'control_store.py')
        L = load('v232_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        HELPER = load('v232_helper', mods / 'accounts.py')
        EL = load('v232_eligibility', mods / 'control_eligibility.py')
        SIG = load('v232_signer', mods / 'control_signer.py')
        GP = load('v232_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-232', 'repository-232', 'builder-232', 'linux-host-232'
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
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}

        def register(account, provider, directory=None):
            record_, error_ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider,
                                                                 config_dir=directory))
            if record_ is None:
                return code(error_)
            profiles.setdefault(account, record_['config_dir'])
            fields = HELPER.registration(account, host=HOST, root=str(helper_root))
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
            _, error_ = attempt(lambda: accounts.register('register/' + account, fields['account'], fields['provider'],
                                                          fields['label'], fields['profiles'], now=time.time()))
            return code(error_)
        for account in ('acct-a1', 'acct-a2', 'acct-a3'):
            check('accounts/profile', account + ' registered by the production writers',
                  register(account, 'antigravity') is None)
        check('accounts/profile', 'a Claude Code account beside them', register('acct-c1', 'claude_code') is None)
        check('accounts/profile', 'the account is one folder that is the engine HOME, logged in by agy there',
              HELPER.PROFILE_ENV.get('antigravity') == 'HOME'
              and HELPER.login_step(HELPER.get('acct-a1', str(helper_root))).startswith(
                  'HOME=%s agy' % profiles['acct-a1']))
        # AC4: one folder, one registration.
        HELPER.account_add('acct-a1-again', root=str(helper_root), provider='antigravity',
                           config_dir=profiles['acct-a1'])
        fields = HELPER.registration('acct-a1-again', host=HOST, root=str(helper_root))
        _, error = attempt(lambda: accounts.register('register/acct-a1-again', fields['account'], fields['provider'],
                                                     fields['label'], fields['profiles'], now=time.time()))
        check('accounts/one-registration', 'a second registration of one folder is refused by name [%s]' % code(error),
              code(error) == 'duplicate_account:acct-a1' and ACC.read(writer, 'acct-a1-again') is None)

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
        (src / 'README').write_text('antigravity source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        config = base / 'receiver.json'
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        trust = Path(db).parent / 'receiver-host-trust.json'
        signers = trust.with_name('receiver-enrollment-signers')
        signers.write_text('')
        trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                         enrollment_signers=str(signers))))
        trust.chmod(0o600)
        config.write_text(json.dumps({
            'host_trust': str(trust), 'store': str(db), 'journal_key': str(private / 'journal'),
            'principal': 'launch-receiver', 'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY,
            'authority_generation': 1, 'host': HOST, 'receipts': str(base / 'receipts'),
            'artifacts': str(base / 'artifacts'), 'state_root': str(factory),
            'adapters': {
                'agy': {'identity': 'reported', 'engine': 'antigravity', 'environment': {'TZ': 'UTC'},
                        'executable': {'version': VERSION}, 'argv': wrapper},
                'agy-key': {'identity': 'reported', 'engine': 'antigravity',
                            'environment': {'TZ': 'UTC', 'GEMINI_API_KEY': 'fixture-' + os.urandom(6).hex()},
                            'executable': {'version': VERSION}, 'argv': wrapper}}}))
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        (base / 'home').mkdir()
        planted = {'ANTIGRAVITY_LS_ADDRESS': '127.0.0.1:' + str(40000 + os.getpid() % 1000),
                   'AGY_FIXTURE_' + os.urandom(4).hex().upper(): 'parent', 'JETSKI_FIXTURE': 'parent',
                   'CLAUDECODE': '1', 'CODEX_THREAD_ID': 'parent', 'GEMINI_API_KEY': 'inherited-' + os.urandom(6).hex(),
                   'GOOGLE_CLOUD_PROJECT': 'inherited-project'}
        inherited = dict({'PATH': os.environ['PATH'], 'HOME': str(base / 'home'), 'TZ': 'UTC'}, **planted)

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30, environment=inherited)
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]

        # The stream forms the fake prints (suite 128 compares them with the recorded real run).
        FORMS = load('v232_forms', ROOT / 'scripts' / 'suites' / 'support' / 'v232_agy_forms.py')
        CONV = FORMS.CONVERSATION
        TOOLS = list(TABLES['tool_registry'])
        step, result = FORMS.step, FORMS.result

        def init():
            return FORMS.init(TOOLS)

        def submit(unit, script, code_=0, via='acct-a1', adapter='agy', deadline=40):
            job = dict(holder=HOLDER, source=str(src), revision='HEAD',
                       payload={'task': 'work the unit', 'script': script, 'code': code_}, adapter=adapter,
                       configuration={}, deadline=time.time() + deadline)
            return attempt(lambda: runner(via).submit(admitted(unit), 'build', **job))

        def finish(launch, via='acct-a1'):
            if launch is None:
                return {}
            record_, _ = attempt(lambda: runner(via).wait(launch))
            return record_ or {}

        def marker(dispatch_id):
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    out = markers / ('%d.out' % data['pid'])
                    data['printed'] = out.read_text().splitlines() if out.exists() else []
                    return data
            return {}

        def events(launch, name):
            return [e for e in (launch.messages if launch else []) if e.get('event') == name]

        def artifact(launch):
            found = events(launch, 'artifact')
            path = (found[-1].get('artifact') or {}).get('path') if found else None
            return json.loads(Path(path).read_text()) if path and Path(path).is_file() else {}

        # A whole normal run: init, a model step, an in-run tool step, the result.
        normal = [init(), step(0, 'planner_response'), step(1, 'view_file', 'view_file'), result(120, 30, cache=100)]
        launch, error = submit('unit-normal', normal)
        state = finish(launch)
        own = marker(launch.dispatch_id if launch else None)
        doc = artifact(launch)
        check('stream/meter', 'the normal run exits and its artifact is complete [%s %s]' % (code(error), state.get('state')),
              error is None and state.get('state') == 'exited' and doc.get('verdict') == 'complete')
        check('pin/pinned-path', 'the launch runs the pinned copy', own.get('binary') == str(pinned2))
        flags = list(A.FLAGS)
        argv = own.get('argv') or []
        packet_text = json.dumps(((own.get('message') or {}).get('message') or {}).get('content'))
        check('launch/flags', 'print mode, stream JSON out and in, no slash commands, no prompts, no print timeout',
              argv[:len(flags)] == flags and argv[len(flags):len(flags) + 1] == ['--settings']
              and not set(argv) & {'--remote-agent', '--remote-control'})
        check('launch/flags', 'the prompt is the stream-json message on stdin, never in argv',
              (own.get('message') or {}).get('type') == 'user' and 'work the unit' in packet_text
              and not any('work the unit' in a for a in argv))
        registry = record['tool_registry']
        in_run = sorted(n for n, r in record['tool_classification'].items() if r['class'] == 'in_run')
        check('launch/settings', 'the session settings deny every registry tool outside the in-run set',
              (own.get('settings') or {}).get('permissions', {}).get('deny') == sorted(set(registry) - set(in_run))
              and 'search_web' in own['settings']['permissions']['deny'])
        env = own.get('env') or {}
        check('launch/environment', 'no planted parent-session or credential name reaches the engine [%s]'
              % sorted(set(planted) & set(env)), bool(env) and not set(planted) & set(env))
        check('launch/environment', 'the auto-update switch is set and HOME is the account folder',
              env.get('AGY_CLI_DISABLE_AUTO_UPDATE') == '1' and env.get('HOME') == profiles['acct-a1']
              and env.get('LANG') == 'C.UTF-8' and env.get('TERM') == 'dumb')
        check('accounts/profile', 'the run is charged to the account its dispatch recorded',
              any(json.loads(p.read_text().splitlines()[0]).get('account') == 'acct-a1'
                  and launch.dispatch_id in p.read_text().splitlines()[0]
                  for p in (base / 'receipts').glob('*.jsonl')))
        check('stream/record', 'every stdout line is the artifact\'s line as printed',
              bool(own.get('printed')) and doc.get('lines') == own.get('printed'))
        check('stream/record', 'the init event\'s tool list is kept', doc.get('init_tools') == TOOLS)
        check('stream/meter', 'the meter charges input and output from the result, cache reads once',
              any('"usage"' in line for p in (base / 'receipts').glob('*.jsonl') for line in p.read_text().splitlines()))
        meter = A.Meter()
        meter.feed(b''.join((json.dumps(s['line']) + '\n').encode() for s in normal))
        check('stream/meter', 'tokens are the result usage input and output', meter.final() == {'tokens': 150, 'messages': 1}
              and meter.session() == {'provider': 'antigravity', 'id': CONV, 'tokens': 150, 'charged': 'whole'})

        # AC3: a zero exit whose result line is missing is never a completion; its usage stays unknown.
        launch, error = submit('unit-missing', [init(), step(0, 'planner_response')])
        state = finish(launch)
        doc = artifact(launch)
        check('stream/missing-result', 'a zero exit without its result is missing_result [%s]' % doc.get('verdict'),
              error is None and state.get('state') == 'exited' and doc.get('verdict') == 'missing_result'
              and doc.get('complete') is False)
        meter = A.Meter()
        meter.feed(b''.join((json.dumps(s['line']) + '\n').encode() for s in [init(), step(0, 'planner_response')]))
        check('stream/missing-result', 'its usage is unknown (no tokens charged)', meter.final() == {})

        # AC2 (L2): a tool call outside the role's set stops the run by name.
        outside = [init(), step(0, 'search_web', 'search_web'), {'sleep': 20}, result(1, 1)]
        launch, error = submit('unit-outside', outside)
        state = finish(launch)
        doc = artifact(launch)
        stops = events(launch, 'engine_stop')
        check('launch/tool-outside-role', 'the run is stopped by name, never complete [%s %s]'
              % (doc.get('verdict'), [s.get('stop') for s in stops]),
              error is None and doc.get('verdict') == 'stopped'
              and (doc.get('login') or {}).get('stop') == 'configuration_stop:tool_outside_role'
              and any(s.get('stop') == 'configuration_stop:tool_outside_role' and s.get('account') == 'acct-a1'
                      and s.get('dispatch_id') == launch.dispatch_id for s in stops))

        # AC2: an account folder holding a rule the binary loads is refused before acceptance; nothing is deleted.
        rule = Path(profiles['acct-a1']) / '.gemini' / 'config' / 'rules.md'
        rule.parent.mkdir(parents=True)
        rule.write_text('always do something else\n')
        launch, error = submit('unit-rule', normal)
        state = finish(launch)
        check('launch/profile', 'the account folder\'s rule refuses the run by name [%s]' % state.get('refusal'),
              state.get('state') == 'refused' and state.get('refusal') == 'invalid_input:engine_profile:.gemini/config/rules.md'
              and not marker(launch.dispatch_id if launch else None) and rule.is_file())
        refused = events(launch, 'refused')
        check('launch/profile', 'the refusal is logged with the dispatch and the account',
              any(e.get('dispatch_id') == launch.dispatch_id and e.get('account') == 'acct-a1' for e in refused))
        rule.unlink()
        (Path(profiles['acct-a1']) / '.gemini' / 'config').joinpath('mcp_config.json').write_text('')
        problem = A.profile_problem(bound, {'HOME': profiles['acct-a1']}, None)
        check('launch/profile', 'the binary\'s own empty server file and project bookkeeping load nothing',
              problem is None)

        # AC2: the clone's and its parents' instruction files and .agents folders, by name.
        clone = base / 'clone'
        (clone / 'work' / 'sub').mkdir(parents=True)
        (clone / '.git').mkdir()
        check('launch/clone', 'a clean clone holds nothing', A.profile_problem(bound, {}, str(clone / 'work' / 'sub')) is None)
        (clone / 'AGENTS.md').write_text('x\n')
        check('launch/clone', 'an instruction file in a parent up to the project root is refused by name',
              A.profile_problem(bound, {}, str(clone / 'work' / 'sub')) == 'invalid_input:engine_clone:../../AGENTS.md')
        (clone / 'AGENTS.md').unlink()
        (clone / 'work' / '.agents' / 'rules').mkdir(parents=True)
        check('launch/clone', 'an .agents folder holding anything is refused by name',
              A.profile_problem(bound, {}, str(clone / 'work' / 'sub')) == 'invalid_input:engine_clone:../.agents/rules')

        # AC2 (L1): a role for this engine that selects an MCP server is refused when saved.
        CFG = load('v232_config', mods / 'control_agent_config.py')
        role = dict(role='reviewer', engine='antigravity', native_tools=[{'name': 'view_file', 'load': 'always'}],
                    mcp=[{'server': 'tracker', 'revision': 1, 'tools': 'all', 'load': 'always'}], skills=[],
                    instructions=[], settings={})
        _, error = attempt(lambda: CFG.validate(role))
        check('launch/role-mcp', 'a role selecting an MCP server is refused when saved [%s]' % code(error),
              code(error) == 'invalid_input:agent_mcp_servers:antigravity')
        _, error = attempt(lambda: CFG.validate(dict(role, mcp=[])))
        check('launch/role-mcp', 'the same role without a server is accepted', error is None)
        _, error = attempt(lambda: A.tool_options(bound, {'native_tools': ['view_file'], 'mcp': [{'server': 'x'}]}))
        check('launch/role-mcp', 'and a bound revision naming one is refused before acceptance',
              code(error) == 'invalid_input:agent_mcp_servers:antigravity')

        # AC4: a credential from the adapter's configuration, and a paid path in the account folder's settings.
        launch, error = submit('unit-key', normal, adapter='agy-key')
        state = finish(launch)
        check('accounts/credential-refused', 'GEMINI_API_KEY configured on the adapter is refused by name [%s]'
              % state.get('refusal'), state.get('refusal') == 'invalid_input:adapter_environment:GEMINI_API_KEY'
              and not marker(launch.dispatch_id if launch else None))
        settings = Path(profiles['acct-a1']) / '.gemini' / 'antigravity-cli' / 'settings.json'
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({'theme': 'dark', 'useAiCredits': True}))
        launch, error = submit('unit-credits', normal)
        state = finish(launch)
        check('accounts/paid-path', 'an account folder that turns AI credits on is refused by name [%s]'
              % state.get('refusal'), state.get('refusal') == 'paid_api:antigravity_login:ai_credits'
              and not marker(launch.dispatch_id if launch else None))
        for key, value, kind in (('billingModel', 'payAsYouGo', 'pay_as_you_go'), ('apiKey', 'k', 'api_key'),
                                 ('cloudProject', 'p', 'cloud_project'), ('apiProvider', 'vertex', 'model_api_provider')):
            settings.write_text(json.dumps({key: value}))
            check('accounts/paid-path', key + ' is refused as ' + kind,
                  A.login_problem(bound, {'HOME': profiles['acct-a1']}) == 'paid_api:antigravity_login:' + kind)
        settings.write_text(json.dumps({'theme': 'dark', 'useAiCredits': False}))
        check('accounts/paid-path', 'settings with every paid path off pass',
              A.login_problem(bound, {'HOME': profiles['acct-a1']}) is None)
        check('accounts/credential-refused', 'every credential name of the binary is the engine\'s list',
              {n for n, held in record['credentials'].items() if held} <= set(A.CREDENTIALS)
              and {'GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'AGY_ADC_AUTH'} <= set(A.CREDENTIALS))

        # AC1: the unpinned source changes (the updater rewrote it); the next launch still runs the pinned copy.
        newer.write_bytes(newer.read_bytes() + b'# rewritten by its updater\n')
        launch, error = submit('unit-updated', normal)
        state = finish(launch)
        own = marker(launch.dispatch_id if launch else None)
        check('pin/pinned-path', 'after the source changes, the launch binds and runs the pinned copy [%s]'
              % state.get('refusal'), state.get('state') == 'exited' and own.get('binary') == str(pinned2))

        # AC3 (L5): the individual quota is an account_limit window with a relative reset.
        quota = 'Individual quota reached for the Gemini models. Resets in 4h23m.'
        observed_at = time.time()
        launch, error = submit('unit-quota', [init(), step(0, 'error_message', text=quota),
                                              result(5, 0, text=quota, reason='error')], code_=3, via='acct-a2')
        state = finish(launch, via='acct-a2')
        windows = (ACC.read(writer, 'acct-a2') or {}).get('windows') or {}
        window = windows.get('individual_quota') or {}
        reset = window.get('reset_at')
        check('stream/limit', 'the quota line is the account\'s window with its reset [%s]' % windows,
              window.get('status') == 'rejected' and isinstance(reset, (int, float)) and reset % 60 == 0
              and observed_at + 4 * 3600 + 23 * 60 <= reset <= time.time() + 4 * 3600 + 24 * 60)
        meter = A.Meter(clock=lambda: 1000.0)
        meter.feed((json.dumps(result(1, 1, text=quota, reason='error')['line']) + '\n').encode())
        check('stream/limit', 'the reset is the observation time plus the duration, rounded up to the minute',
              meter.limit() == {'window': 'individual_quota', 'reset_at': 1000 - 1000 % 60 + 60 + 4 * 3600 + 23 * 60,
                                'signal': 'result'})
        meter = A.Meter(clock=lambda: 1000.0)
        meter.bind({'limits': record['limits']})
        meter.feed((json.dumps(step(2, 'error_message', text='Your AI credits balance is too low to continue.')['line'])
                    + '\n').encode())
        check('stream/limit', 'the AI credits refusal is a window with no reset',
              meter.limit() == {'window': 'ai_credits', 'reset_at': None, 'signal': 'stream'})
        POOL = load('v232_pool', mods / 'control_account_pool.py')
        pool, error = attempt(lambda: POOL.Pool({'agy': {'engine': 'antigravity', 'host': HOST}}))
        check('accounts/pool', 'the pool takes an Antigravity adapter [%s]' % code(error), error is None)
        choice = POOL.choose(writer, {}, {'engine': 'antigravity', 'host': HOST}, time.time(), lambda a: None)
        check('accounts/pool', 'the next run moves off the account at its limit, to another Antigravity account',
              choice.get('account') in ('acct-a1', 'acct-a3')
              and (choice.get('trace') or {}).get('passed', {}).get('acct-a2') == 'account_limit:individual_quota')
        LIM = load('v232_limit', mods / 'control_account_limit.py')
        lines = [{'sequence': n + 1, 'received_at': 1.0, 'stream': 'engine', 'redacted': False,
                  'payload': json.dumps(s['line'])} for n, s in enumerate(normal)]
        decision, error = attempt(lambda: LIM.decide(lines, [], [], 'antigravity'))
        check('accounts/pool', 'the re-run-or-ask decision reads an Antigravity record [%s]' % code(error),
              error is None and decision.get('decision') == 'rerun')
        RTM = load('v232_runtime', mods / 'control_reservation_runtime.py')
        check('accounts/pool', 'its invocations are reserved like the other engines\'',
              RTM.ADAPTERS.get('antigravity') == RTM.ADAPTERS.get('codex'))

        # AC3: every verdict of its own.
        def verdict(script, termination, cause=None, vocabulary=None):
            terminal = A.Terminal(vocabulary or record['stream'])
            for item in script:
                terminal.feed(((item if isinstance(item, str) else json.dumps(item['line'])) + '\n').encode())
            terminal.close()
            return terminal.verdict(termination, cause)
        ok = {'returncode': 0, 'signal': None, 'deadline_stop': False}
        cases = {
            'complete': verdict(normal, ok),
            'finished:print_timeout': verdict(normal[:-1] + [result(1, 1, reason='print_timeout')], ok),
            'finished:interrupted': verdict(normal[:-1] + [result(1, 1, reason='interrupted')], ok),
            'finished:error': verdict(normal[:-1] + [result(1, 1, reason='error')], ok),
            'agent_error': verdict(normal[:-1] + ['AGY_ERROR: {"short_error": "x"}'], dict(ok, returncode=3)),
            'nonzero_exit': verdict(normal, dict(ok, returncode=1)),
            'signal': verdict(normal, dict(ok, returncode=None, signal=9)),
            'deadline': verdict(normal, dict(ok, deadline_stop=True)),
            'malformed_output': verdict(normal[:1] + [step(1, 'not_a_step_type')] + normal[1:], ok),
            'stopped': verdict(normal, ok, 'configuration_stop'),
            'missing_result': verdict(normal[:-1], ok)}
        check('stream/verdicts', 'each ending has its own verdict [%s]' % {k: v for k, v in cases.items() if k != v},
              all(k == v for k, v in cases.items()))
        check('stream/verdicts', 'a line outside the vocabulary, or unparsable, is malformed_output',
              verdict(normal[:1] + ['not json'] + normal[1:], ok) == 'malformed_output'
              and verdict([{'line': {'type': 'unknown_event'}}] + normal, ok) == 'malformed_output')

        # AC3: tool calls by canonical name, fail closed; nested work.
        mcp = step(3, 'mcp_tool')['line']
        mcp['tool_info'] = {'server': 'tracker', 'tool': 'search', 'name': 'search'}
        check('stream/tool-calls', 'an MCP step names its server and tool',
              A.tool_calls(mcp) == [{'id': '3', 'server': 'tracker', 'tool': 'search'}])
        check('stream/tool-calls', 'an in-run tool and a tool-free step are no MCP call',
              A.tool_calls(step(1, 'view_file', 'view_file')['line']) == []
              and A.tool_calls(step(0, 'planner_response')['line']) == [])
        check('stream/tool-calls', 'an unlisted form is unknown and an unreadable one unreadable',
              A.tool_calls(step(4, 'browser_click_element')['line'])[0].get('unknown') == 'step:browser_click_element'
              and A.tool_calls({'type': 'step_update', 'step_type': 'mcp_tool', 'tool_info': {}})[0].get('unreadable')
              and A.tool_calls({'type': 'other'})[0].get('unknown') == 'event:other')
        check('stream/tool-calls', 'nested work names the subagent tools and subagent_info',
              A.nested_work(step(5, 'invoke_subagent', 'invoke_subagent')['line']) == [('subagent', 'step:invoke_subagent')]
              and A.nested_work(step(6, 'planner_response', subagent_info={'conversation_id': 'c', 'log_uri': 'u'})['line'])
              == [('subagent', 'subagent_info')])

    except (Exception, SystemExit) as error:  # noqa: BLE001
        import traceback
        for row in ROWS:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:200]
                  + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass
        for path in base.rglob('*'):
            try:
                if path.is_dir() and not path.is_symlink():
                    path.chmod(0o700)
            except OSError:
                pass
        shutil.rmtree(base, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0232 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v232_suite()
