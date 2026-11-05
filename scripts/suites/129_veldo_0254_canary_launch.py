"""VELDO-0254 AC1: the real-launch canary row. Canary credentials in the keystore, no catalog server selected, one
real launch of each launch kind on each engine the engines record names; nothing the run can read holds a canary.

Run: python3 scripts/selftest.py --suite 129_veldo_0254_canary_launch

Only shared ROOT and expect are consumed. One temporary tree in the owner's runtime directory holds the installed
.veldo copy (the checkout's modules with the production copies of PRODUCTION laid over them) that the suite loads
AND the launch receivers, the trusted wrapper and the clone entrance execute, so a registered mutation of a
production module reaches all of them. Real: a SQLite control store with OpenSSH journal signatures, the owner
enrolled through control_membership's signed command, control_accounts records over profiles .veldo/accounts.py
prepares, VELDO-0036 reservations, the VELDO-0052 Gate, VELDO-0031 claims, a Git source bound to the store,
VELDO-0042 clones, the VELDO-0039 Runner and launch receiver processes, the trusted wrapper (control_launch.py exec)
and VELDO-0040 transient scopes under the owner's systemd user manager in a slice of the run's own, stopped at its
end; the VELDO-0174 conversation authority and its production ConversationLine offering a turn to a conversation
receiver process; and control_service_projects' NewProjectPass starting the repository provisioner.

THE KEYSTORE is the Linux Secret Service seam (control_credential_keystore.SecretService) over a generated fake
`secret-tool` first on every PATH the suite and the receivers use, exactly as suite 85_veldo_0158 builds it, so the
real keyring is never reached. It holds one canary per fixture service (fixture-mail, fixture-tracker), each value
random at run time and set through the seam. No dispatch configuration and no role selects a catalog server.

THE ENGINES are fakes on VELDO-0172's shared constructors: a `claude` pinned as the engines record's version and a
Codex laid out as its vendor package and qualified by the production writer. Every invocation of either writes a
dump of its own os.environ, its argv, its working directory and the bytes of every regular file it can read under
its workspace and scratch: its working directory (the clone work tree, or the conversation directory), HOME,
XDG_RUNTIME_DIR, its account profile and every fixture path its environment or command line names (its run's own
configuration and runtime directories among them). The suite reads those dumps and checks that no canary is in
them, as a substring and through secret_scan.scan holding the canaries. Kinds and engines: an engine run (a project
dispatch through Runner.submit) and a conversation turn (ConversationLine.offer), each on claude_code and codex; a
workflow step's engine reasoning is a coordination dispatch on the same Runner.submit and receiver launch
(control_workflow_cycle_pm), so the engine-run launches cover it; a project process (the repository provisioner)
runs no engine, so its environment and command line are read from /proc as it starts. No real engine runs, nothing
logs in and no real credential exists. Writes only temporary fixtures in the owner's runtime directory.
"""

# VELDO-0230: the qualified versions are the engines record's (python3 .veldo/qualify.py writes it), never typed.
ENGINES_RECORD = __import__('json').loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())


def _v254c_suite():
    import ast
    import base64
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
    import types

    CLAUDE_VERSION = ENGINES_RECORD['claude_code']['version']
    CODEX_PACKAGE_VERSION = ENGINES_RECORD['codex']['package_version']
    FORMATS = json.loads((ROOT / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())
    STREAM = json.loads((ROOT / 'proof' / 'VELDO-0141' / 'stream-formats.json').read_text())
    CODEX_ITEMS = json.loads((ROOT / 'proof' / 'VELDO-0061' / 'codex-exec.json').read_text())['item']

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_credential_keystore.py': ROOT / ".veldo" / "control_credential_keystore.py",
        'secretref.py': ROOT / ".veldo" / "secretref.py",
        'secret_scan.py': ROOT / ".veldo" / "secret_scan.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_projects.py': ROOT / ".veldo" / "control_service_projects.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    ROWS = ('ac1/canary-keystore', 'ac1/canary-engine-run', 'ac1/canary-conversation', 'ac1/canary-workflow-step',
            'ac1/canary-project-process', 'format/fake-lines')
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
        except Exception as error:  # noqa: BLE001 - a refusal is data for the row
            return None, getattr(error, 'code', type(error).__name__ + ':' + str(error)[:200])

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def file_sha(path):
        return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def canary():
        # Random upper case letters and digits after a fixed word: no format of the scan's list matches it.
        return 'CANARY' + base64.b32encode(os.urandom(25)).decode().rstrip('=')

    fake_formats = load('v254c_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    # VELDO-0172: this suite checks its own fake engines against the live capture at its teardown.
    conform_formats = load('v254c_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')

    started = time.monotonic()
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v254c-', dir=runtime if os.path.isdir(runtime) else None))
    slice_name = 'v254c%s.slice' % os.urandom(4).hex()
    tools = dict(os.environ)
    contained, connections, provisioners = [], [], []
    saved_environment = {name: os.environ.get(name) for name in ('PATH', 'HOME', 'DBUS_SESSION_BUS_ADDRESS')}
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            target = mods / name
            target.unlink(missing_ok=True)
            if Path(source).is_file():
                shutil.copyfile(source, target)
        (mods / 'runtime').mkdir(exist_ok=True)
        S = load('v254c_store', mods / 'control_store.py')
        L = load('v254c_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        E = L.ENGINES['claude_code']
        X = L.ENGINES['codex']
        SS = load('v254c_scan', mods / 'secret_scan.py')
        HELPER = load('v254c_helper', mods / 'accounts.py')
        EL = load('v254c_eligibility', mods / 'control_eligibility.py')
        SIG = load('v254c_signer', mods / 'control_signer.py')
        GP = load('v254c_git', mods / 'git_process.py')
        CL = load('v254c_clone', mods / 'control_clone.py')
        CT = load('v254c_containment', mods / 'control_containment.py')
        CM = load('v254c_membership', mods / 'control_membership.py')
        AC = load('v254c_contract', mods / 'authority_contract.py')
        KS = load('v254c_keystore', mods / 'control_credential_keystore.py')
        SV = load('v254c_service', mods / 'control_service.py')
        NP = load('v254c_projects', mods / 'control_service_projects.py')
        CLM = D.CLM
        CM.attach(S)
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-254c', 'repository-254c', 'builder-254c', 'linux-host-254c'
        PROJECT = 'journey-254c'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPOSITORY, store_uuid='store-254c')
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        people = base / 'people'
        people.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v254c-owner', '-f', str(people / 'owner')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        owner_public = ' '.join((people / 'owner.pub').read_text().split()[:2])
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def sign_as(who, message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(people / who), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=10).stdout.decode()

        db = state / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        connections.append(writer)
        serial = [0]

        def next_id(prefix):
            serial[0] += 1
            return '%s-%d' % (prefix, serial[0])

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            current = entity(identity)
            number = next_id('setup')
            S.execute(writer, dict(command_id=number, principal='setup', operation='upsert_entity', nonce=number,
                                   artifact_digests=[], expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', sign, 1)

        def admin(principal, operation, params):
            command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                       'artifact_digests': [], 'expected_versions': {}}
            now = CM.authority_state(S, writer)
            env = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                       request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                       membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                       command_digest=AC.canonical_command_digest(command))
            return CM.admit(S, writer, env, command, sign_as(principal, AC.canonical_envelope_bytes(env)), ids, time.time(),
                            journal_signer=('authority', sign))
        admin('owner', 'enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                            'roles': ['membership_steward', 'project_owner'], 'public_key': owner_public,
                                            'independence_group': 'owner', 'scope': '*'})
        # The project runner and its receiver hold the reservation service role for the repository; the conversation
        # line and the conversation receiver hold it for the domain (a turn has no repository).
        for who, scope in (('runner', [REPOSITORY]), ('launch-receiver', [REPOSITORY]),
                           ('conversation-service', '*'), ('conversation-receiver', '*')):
            put(who, 'membership', dict(principal_type='service', roles=['reservation_service'], scope=scope,
                                        revoked_at=None, expires_at=None))
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        # The owner's accounts: one Claude Code, one Codex. Each engine's model login is its account profile.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}
        for account, provider in (('acct-254c', 'claude_code'), ('acct-254x', 'codex')):
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider))
            profiles[account] = (record or {}).get('config_dir')
            fields, _ = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields:
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=time.time())
        if profiles.get('acct-254x'):
            (Path(profiles['acct-254x']) / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt'}))
        ENGINE_ACCOUNT = {'claude_code': 'acct-254c', 'codex': 'acct-254x'}
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        for account in profiles:
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        put('project:' + PROJECT, 'project', dict(name=PROJECT))
        reservations.configure('policy/' + PROJECT, 'project', PROJECT, dict(BIG), now=time.time())

        def admitted(unit):
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project=PROJECT,
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=20, wall_seconds=10 ** 6),
                                   now=time.time())
            cid = CLM.claim_id(REPOSITORY, unit)
            number = next_id('claim')
            S.execute(writer, dict(command_id=number, principal=HOLDER, operation='claim_operation', nonce=number,
                                   artifact_digests=[],
                                   expected_versions={unit: entity(unit)['version'],
                                                      'backlog:' + unit: entity('backlog:' + unit)['version'], cid: 0},
                                   parameters=dict(action='claim', unit_id=unit, backlog_item_uuid='backlog:' + unit,
                                                   claim_id=cid, holder=HOLDER, generation=0, capabilities=[],
                                                   repository_uuid=REPOSITORY)), HOLDER, sign, 1)
            return unit

        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'NOTES.md').write_text('# notes\n')
        (src / 'app').mkdir()
        (src / 'app' / 'main.py').write_text('print("fixture")\n')
        GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](Path(S.__file__).parent, writer, DOMAIN, {REPOSITORY: str(src)})
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # THE KEYSTORE: a generated secret-tool, first on every PATH, never the real keyring (as suite 85_0158).
        # Its items live in the service's own store directory, which no run is handed; only the tool's directory
        # is on PATH.
        keystore = base / 'keystore'
        keystore.mkdir(mode=0o700)
        (keystore / 'bin').mkdir(mode=0o700)
        tool = keystore / 'bin' / 'secret-tool'
        tool.write_text('''#!@@PYTHON@@ -B
import hashlib, json, pathlib, sys
home = pathlib.Path(__file__).parent.parent
action, args = sys.argv[1], sys.argv[2:]
data = sys.stdin.buffer.read()
label = '-' * 2 + 'label='
has_label = bool(args and args[0].startswith(label))
if has_label:
    args = args[1:]
attributes = dict(zip(args[::2], args[1::2]))
with (home / 'calls').open('a') as out:
    out.write(json.dumps({'action': action, 'argv': sys.argv[1:], 'bytes': len(data)}) + chr(10))
if len(args) % 2 or (action == 'store' and not has_label):
    sys.exit(2)
identity = hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest()
place = home / ('item-' + identity)
if action == 'store':
    place.write_bytes(data)
elif action == 'lookup':
    if not place.exists():
        sys.exit(1)
    sys.stdout.buffer.write(place.read_bytes())
elif action == 'clear':
    place.unlink(missing_ok=True)
else:
    sys.exit(2)
'''.replace('@@PYTHON@@', sys.executable))
        tool.chmod(0o700)
        os.environ['PATH'] = str(keystore / 'bin') + os.pathsep + (saved_environment['PATH'] or '/usr/bin:/bin')

        def calls():
            path = keystore / 'calls'
            return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

        # THE CANARIES: one per fixture service, random at run time, set through the keystore seam.
        CANARIES = {'fixture-mail': canary(), 'fixture-tracker': canary()}
        seam = KS.SecretService(str(tool))
        for name, value in CANARIES.items():
            seam.set(name, value)
        held_back = {name: seam.get('keychain', name) for name in CANARIES}
        calls_at_setup = len(calls())

        # THE FAKE ENGINES. Each invocation dumps what it can read; then it speaks its binary's protocol.
        markers = base / 'markers'
        markers.mkdir()
        dump = '''
def dump_run():
    import re as _re
    fixture = str(BASE)
    paths = set()
    found = [os.getcwd()] + [str(v) for v in os.environ.values()] + [str(a) for a in sys.argv]
    for text in found:
        for path in _re.findall(_re.escape(fixture) + '/[^ "\\',:;=\\\\[\\\\]{}]*', text):
            paths.add(path.rstrip('/'))
    roots = set()
    for name in ('HOME', 'TMPDIR', 'XDG_RUNTIME_DIR', 'CLAUDE_CONFIG_DIR', 'CODEX_HOME'):
        if os.environ.get(name):
            paths.add(os.environ[name])
    paths.add(os.getcwd())
    outside = []
    for path in sorted(paths):
        if not os.path.isabs(path) or not (path + '/').startswith(fixture + '/') or path == fixture:
            outside.append(path)
            continue
        if os.path.isdir(path):
            roots.add(os.path.realpath(path))
        elif os.path.isfile(path):
            roots.add(os.path.realpath(os.path.dirname(path)))
    skip = {os.path.realpath(str(MARKERS)), os.path.realpath(str(KEYSTORE))}
    files, pruned, denied, seen, total, truncated = {}, [], 0, set(), 0, False
    for root in sorted(roots):
        for directory, names, leaves in os.walk(root, followlinks=False):
            for name in list(names):
                if os.path.realpath(os.path.join(directory, name)) in skip:
                    pruned.append(os.path.join(directory, name))
                    names.remove(name)
            for name in leaves:
                path = os.path.join(directory, name)
                real = os.path.realpath(path)
                if real in seen or os.path.islink(path) or not os.path.isfile(path):
                    continue
                seen.add(real)
                if len(files) >= 4000 or total > 64 * 1024 * 1024:
                    truncated = True
                    continue
                try:
                    with open(path, 'rb') as handle:
                        data = handle.read(4 * 1024 * 1024 + 1)
                except OSError:
                    denied += 1
                    continue
                if len(data) > 4 * 1024 * 1024:
                    truncated = True
                total += len(data)
                files[path] = data.decode('latin-1')
    record = {'pid': os.getpid(), 'argv': list(sys.argv), 'env': dict(os.environ), 'cwd': os.getcwd(),
              'dispatch': os.environ.get('VELDO_DISPATCH_ID', ''), 'roots': sorted(roots), 'outside': outside,
              'pruned': pruned, 'denied': denied, 'truncated': truncated, 'files': files, 'at': time.time()}
    temporary = MARKERS / ('dump-%d.tmp' % os.getpid())
    temporary.write_text(json.dumps(record))
    temporary.rename(MARKERS / ('dump-%d-%s.json' % (os.getpid(), uuid.uuid4().hex[:8])))
'''
        fake_claude = '''#!@@PYTHON@@ -B
import json, os, sys, time, uuid
from pathlib import Path
MARKERS = Path(@@MARKERS@@)
BASE = Path(@@BASE@@)
KEYSTORE = Path(@@KEYSTORE@@)
@@DUMP@@
dump_run()
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
pid = os.getpid()
dispatch = env.get('VELDO_DISPATCH_ID', '')
def option(name):
    for at, arg in enumerate(argv):
        if arg == name:
            return argv[at + 1] if at + 1 < len(argv) else None
    return None
out = open(MARKERS / ('%d.out' % pid), 'w')
def emit(event, keep=()):
    filled = complete_event(event)
    for field in keep:
        filled[field] = event.get(field, [])
    text = json.dumps(filled)
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def tools_of():
    for arg in argv:
        if arg.startswith('-' * 2 + 'tools='):
            return [t for t in arg.partition('=')[2].split(',') if t]
    return []
def mcp_of():
    path = option(@@MCP@@)
    try:
        return sorted((json.loads(Path(path).read_text()).get('mcpServers') or {})) if path else []
    except (OSError, ValueError):
        return []
packet, probed = None, False
if option(@@INPUT@@) == 'stream-json':
    while packet is None:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get('type') == 'control_request' and (message.get('request') or {}).get('subtype') == 'initialize':
            emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                                                           'response': {'account': {'apiProvider': 'firstParty',
                                                                                    'subscriptionType': 'Claude Team'},
                                                                        'pid': pid}}})
        elif message.get('type') == 'user' and message.get('shouldQuery') is False:
            # The capability probe of a role-bound run: the init event of what this launch configured, and a
            # zero-turn result, before any model request.
            probed = True
            emit({'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'tools': tools_of(),
                  'mcp_servers': [{'name': n, 'status': 'connected'} for n in mcp_of()], 'plugins': [], 'skills': [],
                  'slash_commands': [], 'claude_code_version': @@VERSION@@, 'model': 'configured-model',
                  'session_id': str(uuid.uuid4()), 'cwd': str(cwd)}, keep=('plugins', 'skills', 'slash_commands'))
            emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 0, 'result': '',
                  'usage': {'input_tokens': 0, 'output_tokens': 0}})
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            packet = json.loads(content) if isinstance(content, str) and content.strip() else {}
packet = packet or {}
own = {'pid': pid, 'dispatch': dispatch, 'argv': sys.argv, 'cwd': str(cwd), 'env': dict(env), 'probed': probed,
       'packet': packet}
(MARKERS / ('%d.tmp' % pid)).write_text(json.dumps(own))
(MARKERS / ('%d.tmp' % pid)).rename(MARKERS / ('%d.json' % pid))
session = str(uuid.uuid4())
usage = {'input_tokens': 3, 'output_tokens': 3, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
if not probed:
    emit({'type': 'system', 'subtype': 'init', 'cwd': str(cwd), 'session_id': session, 'tools': ['Bash'],
          'mcp_servers': [], 'model': 'configured-model', 'permissionMode': 'default', 'slash_commands': [],
          'apiKeySource': 'none', 'claude_code_version': @@VERSION@@, 'output_style': 'default', 'agents': [],
          'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4())})
emit({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()), 'session_id': session,
      'message': {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant',
                  'model': 'configured-model', 'content': [{'type': 'text', 'text': 'Worked the turn.'}],
                  'stop_reason': None, 'stop_sequence': None, 'usage': usage}})
usage['output_tokens'] = 4
emit({'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False, 'num_turns': 1,
      'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0, 'usage': usage,
      'modelUsage': {'configured-model': {'inputTokens': 3, 'outputTokens': 4, 'cacheReadInputTokens': 0,
                                          'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                          'contextWindow': 200000, 'maxOutputTokens': 32000}},
      'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session})
out.close()
'''
        fake_codex = '''#!@@PYTHON@@ -B
import json, os, sys, time, tomllib, urllib.request, uuid
from pathlib import Path
MARKERS = Path(@@MARKERS@@)
BASE = Path(@@BASE@@)
KEYSTORE = Path(@@KEYSTORE@@)
@@DUMP@@
dump_run()
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
pid = os.getpid()
dispatch = env.get('VELDO_DISPATCH_ID', '')
home = Path(env.get('CODEX_HOME') or '/nonexistent')
if argv[:2] == ['login', 'status']:
    try:
        mode = json.loads((home / 'auth.json').read_text()).get('auth_mode')
    except (OSError, ValueError):
        mode = None
    if mode == 'chatgpt':
        # The qualified Codex binary prints its login status on stderr.
        print('Logged in using ChatGPT', file=sys.stderr)
        sys.exit(0)
    sys.exit(1)
overrides = {}
for at, arg in enumerate(argv):
    if arg == '-c' and at + 1 < len(argv):
        key, _, value = argv[at + 1].partition('=')
        overrides[key] = tomllib.loads('v = ' + value)['v']
if argv[:2] == ['mcp', 'list']:
    # No catalog server is selected: the generated table is empty.
    sys.stdout.write('[]' + chr(10))
    sys.exit(0)
if overrides.get('model_provider') == 'role_observation':
    # The receiver's capability observation: the launch's tool definitions sent to its loopback endpoint.
    names = ['update_plan'] if (overrides.get('tools.update_plan') or {}).get('enabled') else []
    url = overrides['model_providers.role_observation']['base_url'] + '/responses'
    body = {'tools': [{'type': 'function', 'name': n} for n in names]}
    try:
        urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(),
                                                      {'Content-Type': 'application/json'}))
    except Exception:
        pass
    sys.exit(0)
out = open(MARKERS / ('%d.out' % pid), 'w')
def emit(event):
    text = json.dumps(complete_event(event))
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
packet = json.loads(sys.stdin.buffer.read() or b'{}')
own = {'pid': pid, 'dispatch': dispatch, 'argv': sys.argv, 'cwd': str(cwd), 'env': dict(env), 'packet': packet}
(MARKERS / ('%d.tmp' % pid)).write_text(json.dumps(own))
(MARKERS / ('%d.tmp' % pid)).rename(MARKERS / ('%d.json' % pid))
emit({'type': 'thread.started', 'thread_id': 'thread-254-%d' % pid})
emit({'type': 'turn.started'})
emit({'type': 'item.completed', 'item': {'id': 'item_last', 'type': 'agent_message', 'text': 'done'}})
emit({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0,
                                          'output_tokens': 4, 'reasoning_output_tokens': 0}})
out.close()
'''

        def filled(source):
            return (source.replace('@@DUMP@@', dump).replace('@@PYTHON@@', sys.executable)
                    .replace('@@MARKERS@@', repr(str(markers))).replace('@@BASE@@', repr(str(base)))
                    .replace('@@KEYSTORE@@', repr(str(keystore))).replace('@@VERSION@@', repr(CLAUDE_VERSION))
                    .replace('@@MCP@@', repr(E.BASELINE['mcp_option'])).replace('@@INPUT@@', repr(E.INPUT_FLAGS[0])))
        fake_claude = fake_formats.embed(filled(fake_claude))
        fake_codex = fake_formats.embed(filled(fake_codex))

        def fake_engine(name):
            # Each engine's generated executable, as VELDO-0172's census reads it back.
            return fake_claude if name == 'claude' else fake_codex

        # The run's scratch: HOME is a fixture directory of the suite's own (the receiver's environment names it).
        scratch_home = base / 'home'
        versions = scratch_home / '.local' / 'share' / 'claude' / 'versions'
        versions.mkdir(parents=True)
        (versions / CLAUDE_VERSION).write_text(fake_claude)
        (versions / CLAUDE_VERSION).chmod(0o755)
        # The shipped qualification entry of the engines record's version, bound to this fake's bytes (as suite 123's
        # conversation journey writes it): it serves both the project run and the role-bound conversation turn.
        shipped = json.loads((ROOT / '.veldo' / 'runtime' / 'claude-qualification.json').read_text())['versions'][CLAUDE_VERSION]
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps({
            'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code',
            'versions': {CLAUDE_VERSION: dict(shipped, sha256=file_sha(versions / CLAUDE_VERSION),
                                              session_environment=E.session_environment(versions / CLAUDE_VERSION))}},
            indent=1))
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        E.pin(CLAUDE_VERSION, versions=str(versions), state_root=str(factory))
        package = base / 'packages' / 'codex'
        CODEX_BIN = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        CODEX_BIN.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': CODEX_PACKAGE_VERSION}))
        CODEX_BIN.write_text(fake_codex)
        CODEX_BIN.chmod(0o755)
        codex_record_path = base / 'codex-qualification.json'
        codex_record_path.write_text(json.dumps(X.qualification(str(CODEX_BIN))))
        # The conversation receiver's Codex record also carries its model catalog (VELDO-0230), as suite 123 writes it.
        conversation_codex = X.qualification(str(CODEX_BIN))
        catalog = {'models': [{'slug': 'fixture-codex-model', 'experimental_supported_tools': [],
                               'apply_patch_tool_type': None, 'supports_search_tool': False}]}
        conversation_codex.update(feature_listing='shell_tool stable true\n', model_catalog=catalog,
                                  model_catalog_digest=X.catalog_digest(catalog), model_tool_modes=X.catalog_modes(catalog))
        # The handoff reads the granted tools from the installed record, so it is the installation's own.
        conversation_codex_path = mods / 'runtime' / 'codex-qualification.json'
        conversation_codex_path.write_text(json.dumps(conversation_codex))

        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4, 'systemd_run': real_systemd_run}
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '-' * 2]
        runs_dir = factory / 'runs'
        config = base / 'receiver.json'
        # VELDO-0170: ordinary launch fixtures name installed host trust; no settlements are trusted.
        receiver_host_trust = Path(db).parent / 'receiver-host-trust.json'
        receiver_enrollment_signers = receiver_host_trust.with_name('receiver-enrollment-signers')
        receiver_enrollment_signers.write_text('')
        receiver_host_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                                     enrollment_signers=str(receiver_enrollment_signers))))
        receiver_host_trust.chmod(0o600)
        common = {'host_trust': str(receiver_host_trust), 'store': str(db), 'journal_key': str(private / 'journal'),
                  'domain': DOMAIN, 'authority_generation': 1, 'host': HOST, 'receipts': str(state / 'receipts'),
                  'artifacts': str(state / 'artifacts'), 'state_root': str(factory), 'profile': profile}
        config.write_text(json.dumps(dict(common, principal='launch-receiver', workspace=str(base), repository=REPOSITORY,
            adapters={'claude': {'engine': 'claude_code', 'executable': {'version': CLAUDE_VERSION}, 'argv': entering},
                      'codex': {'engine': 'codex', 'executable': str(CODEX_BIN), 'qualification': str(codex_record_path),
                                'argv': entering + [str(CODEX_BIN)] + list(X.FLAGS)}})))
        conversation_config = base / 'conversation-receiver.json'
        conversation_config.write_text(json.dumps(dict(common, principal='conversation-receiver',
                                                       receiver_kind='conversation', adapters={
            'claude': {'engine': 'claude_code', 'executable': {'version': CLAUDE_VERSION}, 'argv': []},
            'codex': {'engine': 'codex', 'executable': str(CODEX_BIN), 'qualification': str(conversation_codex_path),
                      'argv': [str(CODEX_BIN)] + list(X.FLAGS)}})))
        conversation_config.chmod(0o600)
        session_bus = tools.get('DBUS_SESSION_BUS_ADDRESS') or 'unix:path=%s/bus' % runtime
        RECEIVER_ENV = dict(os.environ, HOME=str(scratch_home), DBUS_SESSION_BUS_ADDRESS=session_bus)

        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_all'](Path(CL.__file__).parent, writer)
        clones = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)],
                           engines=[str(factory / 'engines'), str(base / 'packages')])

        def invoke(contract):
            clones.create(contract)
            launch = L.invoke(config, contract, dispatches, accept_seconds=30, environment=RECEIVER_ENV)
            contained.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account,
                                            runs=str(runs_dir), profile=profile)
            return runners[account]

        # No catalog server is selected by any launch.
        CONFIGURATION = {'tools': ['Bash'], 'model': 'configured-model', 'mcp': []}

        def dumps_now():
            return set(p.name for p in markers.glob('dump-*.json'))

        def read_dumps(names):
            return [json.loads((markers / n).read_text()) for n in sorted(names)]

        def own_of(dispatch_id):
            for path in sorted(markers.glob('[0-9]*.json')):
                data = json.loads(path.read_text())
                if dispatch_id and data.get('dispatch') == dispatch_id:
                    found = markers / ('%d.out' % data['pid'])
                    data['lines'] = found.read_text().split('\n')[:-1] if found.exists() else []
                    return data
            return {}

        combos = {}

        # THE ENGINE RUNS: one project dispatch per engine, through Runner.submit, the receiver and the wrapper.
        for engine, adapter in (('claude_code', 'claude'), ('codex', 'codex')):
            before = dumps_now()
            unit = admitted('VELDO-254C%02d' % (len(combos) + 1))
            account = ENGINE_ACCOUNT[engine]
            launch, error = attempt(lambda: runner(account).submit(
                unit, 'build', holder=HOLDER, source=str(src), revision='HEAD', payload={'task': 'work the unit'},
                adapter=adapter, configuration=CONFIGURATION, deadline=time.time() + 60))
            record = (attempt(lambda: runner(account).wait(launch))[0] or {}) if launch is not None else {}
            combos[('engine run', engine)] = dict(
                launch=launch, record=record, error=error, own=own_of(launch.dispatch_id) if launch else {},
                dumps=read_dumps(dumps_now() - before), account=account,
                configuration=(launch.contract['capability']['configuration'] if launch else None))

        # THE CONVERSATION TURNS: the production ConversationLine offers one turn per engine to the conversation
        # receiver process; the Line's invoke inherits this process's environment, so its HOME and session bus are
        # the receiver environment's for these launches.
        os.environ['HOME'] = RECEIVER_ENV['HOME']
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = session_bus
        service_conn = SV.S.open_store(str(db))
        connections.append(service_conn)
        CV = SV.CV
        conversations = CV.Conversations(SV.S, service_conn, domain=DOMAIN, principal='conversation-service',
                                         signer='conversation-service', sign=sign, state_root=str(factory))
        roles, revisions = {}, {}
        for role_name, engine, native, settings in (('assistant', 'claude_code', 'Read', {}),
                                                    ('assistant_codex', 'codex', 'update_plan',
                                                     {'model': 'fixture-codex-model'})):
            saved = {'role': role_name, 'engine': engine, 'native_tools': [{'name': native, 'load': 'always'}],
                     'mcp': [], 'skills': [], 'instructions': [], 'settings': settings, 'revision': 1, 'previous': None}
            saved['digest'] = CV.CFG.digest(saved)
            put('configuration:' + role_name, 'agent_configuration', saved)
            revisions[role_name] = saved
            roles[role_name] = {'kind': 'specialist', 'capability_configuration': {'role': role_name, 'revision': 1},
                                'workers': [role_name + '-worker'], 'responsibilities': ['assist'],
                                'expertise': ['general'], 'proposal_permissions': [], 'engines': [engine],
                                'budget': {'capacity': 4, 'invocations': 20, 'wall_seconds': 90, 'tokens': 100000,
                                           'messages': 100},
                                'independence': {'distinct_from': []}}
        put('default-team:1', 'default_team_revision', {'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner',
                                                       'assertion_digest': 'sha256:fixture', 'previous': None,
                                                       'digest': 'sha256:default-one'})
        put('default-team:head', 'default_team_head', {'revision': 1})
        ended_seen = []
        service = types.SimpleNamespace(conn=service_conn, domain=DOMAIN, principal='conversation-service', generation=1,
                                        sign=sign, conversations=lambda: conversations)
        line = SV.ConversationLine(types.SimpleNamespace(service=service, saw_end=lambda l, x: ended_seen.append(x)),
                                   str(conversation_config))
        caps = {'capacity': 10, 'invocations': 100, 'wall_seconds': 1000, 'tokens': 1000000, 'messages': 1000}
        for role_name, engine in (('assistant', 'claude_code'), ('assistant_codex', 'codex')):
            identity = 'canary-' + engine.replace('_', '-')
            conversations.open(identity, owner='owner', role=role_name, intake_digest='sha256:' + identity)
            turn = conversations.message(identity, identity + '-1', 'sha256:' + identity + '-1', owner='owner')
            subjects = ([('account', a['id']) for a in SV.L.D.RES.POOL.accounts(service_conn)]
                        + [('project', identity), ('unit', identity)])
            for scope, subject in subjects:
                key = SV.L.D.RES.entity('policy', [DOMAIN, scope, subject])
                if service_conn.execute('SELECT 1 FROM entities WHERE id=?', (key,)).fetchone() is None:
                    line.reservations.configure('v254c-policy/%s/%s' % (scope, subject), scope, subject, dict(caps),
                                                now=time.time())
            before = dumps_now()
            report = {key: [] for key in ('offered', 'conversation_offered', 'waiting', 'refused', 'released', 'ended',
                                          'faults')}
            launch, error = attempt(lambda: line.offer(turn, report))
            if launch is not None and launch.child is not None:
                end = time.time() + 60
                while time.time() < end and not launch.pump():
                    time.sleep(0.02)
                contained.append(launch)
            record = (attempt(lambda: line.runner.wait(launch, timeout=30))[0] or {}) if launch is not None else {}
            combos[('conversation turn', engine)] = dict(
                launch=launch, record=record, error=error or (report['refused'] or [None])[0],
                own=own_of(launch.dispatch_id) if launch else {}, dumps=read_dumps(dumps_now() - before),
                account=(launch.contract['reservation']['account'] if launch else None),
                configuration=(launch.contract['capability']['configuration'] if launch else None),
                directory=(conversations.read(identity) or {}).get('directory'))
        os.environ['HOME'] = saved_environment['HOME'] if saved_environment['HOME'] is not None else os.environ['HOME']
        if saved_environment['DBUS_SESSION_BUS_ADDRESS'] is None:
            os.environ.pop('DBUS_SESSION_BUS_ADDRESS', None)
        else:
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = saved_environment['DBUS_SESSION_BUS_ADDRESS']

        # THE PROJECT PROCESS: control_service_projects starts the repository provisioner; it runs no engine. Its
        # environment and command line are read from /proc while it is stopped right after its start.
        provisioner_config = base / 'provisioner.json'
        provisioner_config.write_text('{}\n')
        provisioner_config.chmod(0o600)
        new_projects = NP.NewProjectPass(types.SimpleNamespace(config={'provisioner': str(provisioner_config)}), {})
        project_process = {}
        started_event, project_process['error'] = attempt(lambda: new_projects.provision(
            {'id': 'decision-254c', 'proposal': {'repository': 'repository-254c-new'}}))
        project_process['event'] = started_event or {}
        one = new_projects.running.get('decision-254c')
        if one is not None:
            process = one.process
            provisioners.append(process)
            with contextlib.suppress(OSError):
                os.kill(process.pid, signal.SIGSTOP)
            try:
                project_process['environ'] = (Path('/proc') / str(process.pid) / 'environ').read_bytes()
                project_process['cmdline'] = (Path('/proc') / str(process.pid) / 'cmdline').read_bytes()
            except OSError:
                project_process['environ'] = project_process['cmdline'] = b''
            with contextlib.suppress(OSError):
                os.kill(process.pid, signal.SIGCONT)
            end = time.time() + 30
            while time.time() < end and not one.pump():
                time.sleep(0.02)
            project_process['exit'] = process.poll()
            project_process['output'] = one.output.decode('utf-8', 'replace')

        SECRETS = sorted(CANARIES.values())

        def leaked_in(text):
            return [name for name, value in sorted(CANARIES.items()) if value in text]

        def scanned(dumps):
            files = []
            for at, one_dump in enumerate(dumps):
                files += [('%d/environment/%s' % (at, k), str(v).encode('utf-8', 'surrogateescape'))
                          for k, v in sorted(one_dump.get('env', {}).items())]
                files += [('%d/command/%d' % (at, n), str(a).encode('utf-8', 'surrogateescape'))
                          for n, a in enumerate(one_dump.get('argv') or [])]
                files += [('%d/file%s' % (at, p), t.encode('latin-1')) for p, t in sorted((one_dump.get('files') or {}).items())]
            report = SS.scan('run_end', PROJECT, files, held=SECRETS)
            return report, files

        def judge(row, kind, engine):
            got = combos.get((kind, engine)) or {}
            tag = '%s on %s' % (kind, engine)
            record = got.get('record') or {}
            own = got.get('own') or {}
            dumps = got.get('dumps') or []
            main = [d for d in dumps if d.get('pid') == own.get('pid')]
            env = own.get('env') or {}
            seen = [(m.get('event'), m.get('refusal') or m.get('reason') or m.get('error'))
                    for m in (got['launch'].messages if got.get('launch') else []) if isinstance(m, dict)]
            check(row, '%s: the run started through the Runner, the receiver and the wrapper and completed [%s %s %s %s]'
                  % (tag, record.get('state'), record.get('refusal') or record.get('reason'), got.get('error'), seen[-6:]),
                  got.get('error') is None and record.get('state') == 'exited' and D.completed(record) and bool(own)
                  and own.get('dispatch') == (got['launch'].dispatch_id if got.get('launch') else None))
            account_record = next((a for a in SV.L.D.RES.POOL.accounts(service_conn) if a['id'] == got.get('account')), {})
            login_name = 'CLAUDE_CONFIG_DIR' if engine == 'claude_code' else 'CODEX_HOME'
            check(row, '%s: the engine\'s model login is used as before, its account\'s profile [%s=%s, account %s]'
                  % (tag, login_name, env.get(login_name), got.get('account')),
                  bool(env.get(login_name)) and env.get(login_name) == profiles.get(got.get('account'))
                  and got.get('account') == ENGINE_ACCOUNT[engine] and bool(account_record))
            check(row, '%s: no catalog server was selected [%s]' % (tag, (got.get('configuration') or {}).get('mcp')),
                  got.get('configuration') is not None and not (got['configuration'].get('mcp') or []))
            roots = sorted({r for d in main for r in d.get('roots') or []})
            workspace = got.get('directory') if kind == 'conversation turn' else None
            cwd = own.get('cwd') or ''
            in_place = (cwd == workspace) if workspace else cwd.startswith(str(clones_root) + os.sep)
            check(row, '%s: every file it can read under its workspace and scratch was read: its working directory, '
                  'HOME, its runtime and run directories and its profile [%d dumps, %d files, %d denied, roots %s, '
                  'outside %s, pruned %s]'
                  % (tag, len(dumps), sum(len(d.get('files') or {}) for d in dumps), sum(d.get('denied', 0) for d in dumps),
                     roots, sorted({o for d in main for o in d.get('outside') or []}),
                     sorted({p for d in main for p in d.get('pruned') or []})),
                  len(main) == 1 and in_place and os.path.realpath(cwd) in roots
                  and os.path.realpath(env.get('HOME') or '/') in roots and env.get('HOME') == str(scratch_home)
                  and os.path.realpath(env.get('XDG_RUNTIME_DIR') or '/') in roots
                  and any(r.startswith(os.path.realpath(str(runs_dir)) + os.sep) for r in roots)
                  and os.path.realpath(env.get(login_name) or '/') in roots
                  and all(not d.get('truncated') for d in dumps)
                  and not [o for d in main for o in d.get('outside') or [] if o in (cwd, env.get('HOME'))]
                  and not [p for d in dumps for p in d.get('pruned') or [] if os.path.realpath(p) == os.path.realpath(str(keystore))]
                  and sum(len(d.get('files') or {}) for d in main) > 3)
            text = '\n'.join(json.dumps(d.get('env')) + '\0'.join(d.get('argv') or [])
                             + ''.join((d.get('files') or {}).values()) for d in dumps)
            where = sorted({'%s:%s' % (name, place) for d in dumps for name, value in CANARIES.items()
                            for place in (['environment'] if value in json.dumps(d.get('env')) else [])
                            + (['command'] if value in '\0'.join(d.get('argv') or []) else [])
                            + [p for p, t in (d.get('files') or {}).items() if value in t]})
            check(row, '%s: no canary is in its environment, its command line or any file it can read [%s]'
                  % (tag, where), bool(dumps) and not leaked_in(text) and not where)
            report, files = scanned(dumps)
            held = [f for f in report['findings'] if f['kind'] == SS.HELD_KIND]
            check(row, '%s: the one scan entry holding the canaries finds none [%d files, %s]'
                  % (tag, report['files'], [(f['file'], f['line']) for f in held][:6]),
                  bool(files) and report['files'] == len(files) and not held)

        with region('ac1/canary-keystore'):
            check('ac1/canary-keystore', 'the keystore (the Secret Service seam over the fake secret-tool) holds a '
                  'canary for each fixture service, read back through the seam [%s]' % sorted(CANARIES),
                  held_back == CANARIES and len(set(CANARIES.values())) == 2
                  and all(v.startswith('CANARY') and len(v) > 30 for v in CANARIES.values()))
            check('ac1/canary-keystore', 'no format of the scan\'s list matches a canary, so only the canary row can '
                  'find one', not [f for f in SS.scan('run_end', PROJECT, [('canaries', '\n'.join(SECRETS).encode())])['findings']])
            asked = [c for c in calls()[calls_at_setup:] if c['action'] == 'lookup' and c['argv'][-1] in CANARIES]
            check('ac1/canary-keystore', 'no launch asked the keystore for a canary [%d lookups of %s]'
                  % (len(asked), sorted({c['argv'][-1] for c in asked})), not asked)

        with region('ac1/canary-engine-run'):
            for engine in ('claude_code', 'codex'):
                judge('ac1/canary-engine-run', 'engine run', engine)

        with region('ac1/canary-conversation'):
            for engine in ('claude_code', 'codex'):
                judge('ac1/canary-conversation', 'conversation turn', engine)
                got = combos.get(('conversation turn', engine)) or {}
                check('ac1/canary-conversation', 'conversation turn on %s: the turn ran in its conversation directory '
                      'through the conversation receiver, with no repository [%s]' % (engine, (got.get('own') or {}).get('cwd')),
                      bool(got.get('launch')) and got['launch'].contract.get('subject_kind') == 'conversation'
                      and got['launch'].contract.get('repository') is None
                      and (got.get('own') or {}).get('cwd') == got.get('directory'))

        with region('ac1/canary-workflow-step'):
            # A workflow step reaches an engine only as a coordination dispatch on the ordinary Runner: the same
            # Runner.submit, receiver and wrapper the engine runs above took, with no launch contract of its own.
            tree = ast.parse((mods / 'control_workflow_cycle_pm.py').read_text())
            submits = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == 'submit' and isinstance(n.func.value, ast.Attribute)
                       and n.func.value.attr == 'runner' and n.args and isinstance(n.args[1], ast.Constant)
                       and n.args[1].value == 'coordination']
            spawns = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                      and n.attr in ('Popen', 'execve', 'execv', 'invoke', 'Receiver')]
            check('ac1/canary-workflow-step', 'workflow step on claude_code and codex: its engine reasoning is a '
                  'coordination dispatch through Runner.submit, the path the engine runs above took [%d submits, %d '
                  'other launch calls]' % (len(submits), len(spawns)), len(submits) == 1 and not spawns)
            check('ac1/canary-workflow-step', 'workflow step on claude_code and codex: both engine runs through that '
                  'path held no canary',
                  all(ok for label, ok in rows['ac1/canary-engine-run']) and len(rows['ac1/canary-engine-run']) >= 10)

        with region('ac1/canary-project-process'):
            environ = project_process.get('environ') or b''
            cmdline = project_process.get('cmdline') or b''
            check('ac1/canary-project-process', 'project process (repository provisioner, no engine): '
                  'NewProjectPass.provision started it and its environment and command line were read from /proc '
                  '[%s, %d environment bytes, %s]' % (project_process['event'].get('outcome'), len(environ),
                                                       cmdline.split(b'\0')[2:3]),
                  project_process['event'].get('outcome') == 'started' and len(environ) > 0
                  and cmdline.split(b'\0')[2:3] == [str(mods / NP.PROTECTED_EFFECTS['repository_provisioning']).encode()])
            check('ac1/canary-project-process', 'project process: no canary is in its environment, its command line or '
                  'its configuration file',
                  bool(environ) and not leaked_in(environ.decode('latin-1') + cmdline.decode('latin-1')
                                                  + provisioner_config.read_text()))
            report = SS.scan('run_end', PROJECT, [('environment', environ), ('command', cmdline),
                                                  ('configuration', provisioner_config.read_bytes())], held=SECRETS)
            check('ac1/canary-project-process', 'project process: the one scan entry holding the canaries finds none',
                  report['files'] == 3 and not [f for f in report['findings'] if f['kind'] == SS.HELD_KIND])
            check('ac1/canary-project-process', 'project process: it ended on its own, refusing the fixture '
                  'configuration [exit %s, %s]' % (project_process.get('exit'), project_process.get('output', '')[:120]),
                  project_process.get('exit') is not None and '"ok": false' in project_process.get('output', ''))

        with region('format/fake-lines'):
            events = FORMATS['claude_code']['events']
            extra_events = STREAM['claude_code']['events']
            codex_events = FORMATS['codex']['events']
            kinds = dict(CODEX_ITEMS['items'], **FORMATS['codex']['items'])
            bad, printed = [], 0
            for (kind, engine), got in sorted(combos.items()):
                for raw in (got.get('own') or {}).get('lines') or []:
                    event = json.loads(raw)
                    printed += 1
                    if engine == 'claude_code':
                        name = event.get('type')
                        key = {'system': 'system/init', 'result': 'result/success'}.get(name, name)
                        if name == 'control_response':
                            continue
                        table = ((events.get(key) or extra_events.get(key)) or {}).get('fields') or {}
                        required = {f for f, v in table.items() if not v.get('optional')}
                        if not table or set(event) - set(table) or required - set(event):
                            bad.append((kind, key, sorted(set(event) - set(table)), sorted(required - set(event))))
                    else:
                        table = (codex_events.get(event.get('type')) or {}).get('fields') or {}
                        if not table or set(event) - set(table):
                            bad.append((kind, event.get('type'), sorted(set(event) - set(table))))
                        item = event.get('item')
                        if isinstance(item, dict):
                            fields = ((kinds.get(item.get('type')) or {}).get('fields')) or {}
                            if not fields or set(item) - set(fields):
                                bad.append((kind, 'item/' + str(item.get('type')), sorted(set(item) - set(fields))))
            check('format/fake-lines', 'every event line the fakes printed is one of the binaries\' own schemas with its '
                  'required fields [%d lines, %s]' % (printed, bad[:3]), printed >= 12 and not bad)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        fake_capture = conform_formats.conform_fake(locals(), '0254_canary_launch')
        for name, value in saved_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        for process in provisioners:
            with contextlib.suppress(Exception):
                os.kill(process.pid, signal.SIGCONT)
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        with contextlib.suppress(Exception):
            subprocess.run(['systemctl', '--user', 'stop', slice_name], capture_output=True, timeout=20, env=tools,
                           stdin=subprocess.DEVNULL)
        with contextlib.suppress(Exception):
            mine = sorted({CT.unit_name(launch.dispatch_id) for launch in contained})
            listed = subprocess.run(['systemctl', '--user', 'list-units', '--all', '--plain', '--no-legend', *mine],
                                    capture_output=True, text=True, timeout=20, env=tools, stdin=subprocess.DEVNULL)
            loaded = [one.split()[0] for one in listed.stdout.splitlines() if one.split()]
            if mine and loaded:
                subprocess.run(['systemctl', '--user', 'reset-failed', *loaded], capture_output=True, timeout=20,
                               env=tools, stdin=subprocess.DEVNULL)
        for launch in contained:
            with contextlib.suppress(Exception):
                if launch.child is not None and launch.child.poll() is None:
                    launch.child.kill()
                    launch.child.wait(timeout=10)
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
                    print('  VELDO-0254 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0254 %s detail: no check ran' % name)
        expect('VELDO-0254 ' + name, ok)
    for one in conform_formats.describe('0254_canary_launch', *fake_capture):
        print(one)
    expect('VELDO-0172 fake/capture:0254_canary_launch', bool(fake_capture[1]) and not fake_capture[0])
    print('VELDO-0254 canary launch suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session: the receiver, its systemd tools and this suite's own systemctl reach the user manager
# through /run/user/<uid> for this run when the gate's environment names none.
_v254c_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v254c_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v254c_suite()
finally:
    if _v254c_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v254c_session
