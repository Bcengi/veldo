"""VELDO-0158: each Linux run receives exactly its servers' credentials, resolved from the keystore just before
spawn and added to the run's redaction set.

Run: python3 scripts/selftest.py --suite 85_veldo_0158_credential_delivery

Only shared ROOT and expect are consumed. One temporary tree in the owner's runtime directory holds the installed
.veldo copy the suite loads AND the launch receiver, wrapper and clone entrance execute, so a registered mutation of
a production module reaches all of them. Real: a SQLite control store with OpenSSH journal signatures, the owner
enrolled through VELDO-0025's signed command, the API edge enrolled through VELDO-0067's, the owner's passkey
registered and signed in through the VELDO-0130 API's own ceremonies (an openssl key assembles each WebAuthn
result), every credential set and every MCP server saved through that API's routes (VELDO-0144: the credential
route and the catalog route, on its ApiAuthority with the authority's lock), the owner's account records over
profiles the local helper prepares, VELDO-0036 reservations, VELDO-0052's Gate, VELDO-0031 claims, a Git source
bound to the store, VELDO-0042 clones confined with Landlock, the VELDO-0039 Runner and receiver processes, the
trusted wrapper and VELDO-0040 transient scopes under the owner's systemd user manager in a slice of the run's own.

The Secret Service is a generated fake `secret-tool` first on every PATH the suite and the receiver use, speaking
libsecret's command line (values on standard input, attributes as arguments; a mode file makes it locked or
unreachable), so the real keyring is never reached. The protected API signer is replaced by the API edge's own
generated key signing in the command namespace the authority verifies. The engines are fakes on VELDO-0172's
shared constructors: a `claude` pinned as 2.1.281 and qualified with the module's baseline, which starts each
stdio server its generated MCP configuration names with that entry's environment, and a Codex laid out as the
vendor package and qualified by the production writer, which starts each stdio server of its `-c mcp_servers`
table with the binary's small default environment, the table's literals and each `env_vars` name taken from its
own environment. Each calls its servers' one tool (the fixture server answers with the credential it was given)
and prints what it got, alone, inside a command's output and on its error stream. While both are running, the
suite reads every process of the account from /proc. No real engine runs, nothing logs in and no real credential
exists (every value is assembled at run time). Each row is reported once.
"""


def _v158_suite():
    import contextlib
    import fcntl
    import hashlib
    import importlib.util
    import inspect
    import json
    import os
    from pathlib import Path
    import random
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time
    import types

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    FORMATS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())
    STREAM = json.loads((TREE / 'proof' / 'VELDO-0141' / 'stream-formats.json').read_text())
    CODEX_ITEMS = json.loads((TREE / 'proof' / 'VELDO-0061' / 'codex-exec.json').read_text())['item']
    VERSION = '2.1.281'

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_credential_delivery.py': ROOT / ".veldo" / "control_credential_delivery.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_credential.py': ROOT / ".veldo" / "control_credential.py",
        'control_credential_keystore.py': ROOT / ".veldo" / "control_credential_keystore.py",
        'secretref.py': ROOT / ".veldo" / "secretref.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    ROWS = ('delivery/claude-private-file', 'delivery/codex-environment', 'delivery/command-lines',
            'delivery/own-server-only', 'delivery/not-in-packet-contract-journal', 'delivery/private-dir-removed',
            'delivery/report',
            'refusal/keystore-locked', 'refusal/keystore-unreachable', 'refusal/reference-not-found',
            'refusal/no-credential-launches',
            'redaction/claude-keystore-value', 'redaction/codex-keystore-value', 'redaction/per-run-set',
            'redaction/claude-bare-bearer', 'refusal/env-collision',
            'orphan/run-directory-removed', 'orphan/start-sweep', 'orphan/live-run-kept',
            'fixture/route-set', 'fixture/control-word', 'format/fake-lines')
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

    def file_sha(path):
        return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

    fake_spec = importlib.util.spec_from_file_location('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    # VELDO-0172: this suite checks its own fake engines against the live capture at its teardown.
    conform_spec = importlib.util.spec_from_file_location('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)

    started = time.monotonic()
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v158-', dir=runtime if os.path.isdir(runtime) else None))
    slice_name = 'v158%s.slice' % os.urandom(4).hex()
    tools = dict(os.environ)
    contained, connections, closers = [], [], []
    saved_path = os.environ.get('PATH')
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
        S = load('v158_store', mods / 'control_store.py')
        L = load('v158_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        E = L.ENGINES['claude_code']
        X = L.ENGINES['codex']
        ER = load('v158_record', mods / 'control_execution_record.py')
        SS = load('v158_scan', mods / 'secret_scan.py')
        HELPER = load('v158_helper', mods / 'accounts.py')
        EL = load('v158_eligibility', mods / 'control_eligibility.py')
        SIG = load('v158_signer', mods / 'control_signer.py')
        GP = load('v158_git', mods / 'git_process.py')
        CL = load('v158_clone', mods / 'control_clone.py')
        CT = load('v158_containment', mods / 'control_containment.py')
        CM = load('v158_membership', mods / 'control_membership.py')
        AC = load('v158_contract', mods / 'authority_contract.py')
        API = load('v158_api', mods / 'control_api.py')
        AUTH = load('v158_authority', mods / 'control_api_authority.py')
        CHE = load('v158_enrollment', mods / 'control_channel_enrollment.py')
        KS = load('v158_keystore', mods / 'control_credential_keystore.py')
        SV = load('v158_service', mods / 'control_service.py')
        CR, IN, MC, CV = AUTH.CR, AUTH.AS.IN, AUTH.MC, AUTH.CV
        CLM = D.CLM
        CM.attach(S)
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-158', 'repository-158', 'builder-158', 'linux-host-158'
        PROJECT, INTAKE = 'journey-158', 'intake-158'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPOSITORY, store_uuid='store-158')
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        people = base / 'people'
        people.mkdir(mode=0o700)
        public = {}
        for who in ('owner', 'api-edge', 'api-auth'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v158-' + who, '-f', str(people / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = ' '.join((people / (who + '.pub')).read_text().split()[:2])
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

        def envelope(command, principal):
            now = CM.authority_state(S, writer)
            return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                        membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))

        def admin(principal, operation, params):
            command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                       'artifact_digests': [], 'expected_versions': {}}
            env = envelope(command, principal)
            return CM.admit(S, writer, env, command, sign_as(principal, AC.canonical_envelope_bytes(env)), ids, time.time(),
                            journal_signer=('authority', sign))
        admin('owner', 'enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                            'roles': ['membership_steward', 'project_owner'], 'public_key': public['owner'],
                                            'independence_group': 'owner', 'scope': '*'})
        # The runner and the launch receiver hold the reservation service role, as VELDO-0062's suites write it.
        for who in ('runner', 'launch-receiver'):
            put(who, 'membership', dict(principal_type='service', roles=['reservation_service'], scope=[REPOSITORY],
                                        revoked_at=None, expires_at=None))
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}
        # The API's own edge (VELDO-0067): channel "api", a service member with no roles, admitted by the steward.
        enrollment = CHE.Enrollment(S, writer, ids, 'authority', sign)
        edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge', 'target': 'channel:api',
                        'parameters': {'channel': 'api', 'edge_principal': 'api-edge', 'edge_key_id': 'edge-api',
                                       'public_key': public['api-edge'], 'connection_public_key': public['api-auth'],
                                       'scope': [PROJECT]}, 'artifact_digests': [], 'expected_versions': {}}
        edge_env = envelope(edge_command, 'owner')
        edge_enrolled = enrollment.admit(edge_env, edge_command, sign_as('owner', AC.canonical_envelope_bytes(edge_env)),
                                         sign_as('api-edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

        # The owner's accounts: one Claude Code, one Codex.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}
        for account, provider in (('acct-158c', 'claude_code'), ('acct-158x', 'codex')):
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider))
            profiles[account] = (record or {}).get('config_dir')
            fields, _ = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields:
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=time.time())
        if profiles.get('acct-158x'):
            (Path(profiles['acct-158x']) / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt'}))
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
        GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # THE KEYSTORE: a generated secret-tool, first on every PATH, never the real keyring.
        keystore = base / 'keystore'
        keystore.mkdir(mode=0o700)
        tool = keystore / 'secret-tool'
        tool.write_text('''#!@@PYTHON@@ -B
import hashlib, json, pathlib, sys
home = pathlib.Path(__file__).parent
action, args = sys.argv[1], sys.argv[2:]
data = sys.stdin.buffer.read()
label = '-' * 2 + 'label='
has_label = bool(args and args[0].startswith(label))
if has_label:
    args = args[1:]
attributes = dict(zip(args[::2], args[1::2]))
mode = (home / 'mode').read_text() if (home / 'mode').exists() else ''
with (home / 'calls').open('a') as out:
    out.write(json.dumps({'action': action, 'argv': sys.argv[1:], 'bytes': len(data), 'mode': mode}) + chr(10))
if len(args) % 2 or (action == 'store' and not has_label):
    sys.exit(2)
if mode:
    sys.stderr.write('collection locked' if mode == 'locked' else 'service unreachable')
    sys.exit(1)
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
        os.environ['PATH'] = str(keystore) + os.pathsep + (saved_path or '/usr/bin:/bin')

        def calls():
            path = keystore / 'calls'
            return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

        def item_of(reference):
            attributes = {'application': 'veldo', 'credential': reference.split(':', 1)[1]}
            return keystore / ('item-' + hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest())

        # THE MCP SERVER FIXTURE: one tool, `credential`, answering with the variables its arguments name as it was
        # started with them; it keeps its own environment where the suite reads it.
        markers = base / 'markers'
        markers.mkdir()
        server = base / 'mcp-server.py'
        server.write_text('''import json, os, sys
from pathlib import Path
name, wanted = sys.argv[1], sys.argv[2:]
Path(@@MARKERS@@, 'server-%s-%d.json' % (name, os.getpid())).write_text(json.dumps(
    {'server': name, 'pid': os.getpid(), 'env': dict(os.environ), 'dispatch': os.environ.get('V158_DISPATCH', '')}))
for line in sys.stdin:
    request = json.loads(line)
    if request.get('method') == 'tools/list':
        result = {'tools': [{'name': 'credential', 'inputSchema': {'type': 'object'}}]}
    else:
        result = {'content': [{'type': 'text', 'text': os.environ.get(wanted[0], '') if wanted else ''}]}
    sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}) + chr(10))
    sys.stdout.flush()
'''.replace('@@MARKERS@@', repr(str(markers))))

        # What both fakes share: start each stdio server, call its tool, hold while the suite reads /proc.
        common = '''
def serve(servers, environment_of):
    got, children = {}, []
    for name, entry in sorted(servers.items()):
        if entry.get('command') is None:
            continue
        child = subprocess.Popen([entry['command']] + list(entry.get('args') or []), stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, text=True, env=dict(environment_of(entry), V158_DISPATCH=dispatch))
        child.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                      'params': {'name': 'credential', 'arguments': {}}}) + chr(10))
        child.stdin.flush()
        got[name] = json.loads(child.stdout.readline())['result']['content'][0]['text']
        children.append(child)
    return got, children
def hold(children, payload):
    if payload.get('hold'):
        (markers / ('%d.ready' % pid)).write_text('ready')
        end = time.time() + 30
        while not os.path.exists(payload['hold']) and time.time() < end:
            time.sleep(0.02)
    for child in children:
        child.stdin.close()
        child.wait(timeout=10)
def printed(got, payload):
    shown = [got[n] for n in payload.get('print') or [] if got.get(n)]
    if payload.get('foreign'):
        shown.append(Path(payload['foreign']).read_text())
    return shown
'''
        fake_claude = '''#!@@PYTHON@@ -B
import json, os, subprocess, sys, time, uuid
from pathlib import Path
markers = Path(@@MARKERS@@)
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
pid = os.getpid()
dispatch = env.get('VELDO_DISPATCH_ID', '')
def option(name):
    for at, arg in enumerate(argv):
        if arg == name:
            return argv[at + 1] if at + 1 < len(argv) else None
    return None
@@COMMON@@
mcp_path = option(@@MCP@@)
mcp = {}
if mcp_path:
    info = {'path': mcp_path, 'file_mode': os.stat(mcp_path).st_mode & 0o777,
            'dir_mode': os.stat(os.path.dirname(mcp_path)).st_mode & 0o777}
    mcp = json.loads(Path(mcp_path).read_text())
else:
    info = {}
own = {'pid': pid, 'dispatch': dispatch, 'argv': sys.argv, 'cwd': str(cwd), 'env': dict(env), 'mcp': mcp, 'mcp_file': info}
out = open(markers / ('%d.out' % pid), 'w')
err = open(markers / ('%d.err' % pid), 'w')
def emit(event):
    text = json.dumps(complete_event(event))
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def warn(text):
    err.write(text + chr(10))
    err.flush()
    sys.stderr.write(text + chr(10))
    sys.stderr.flush()
packet = None
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
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            packet = json.loads(content) if content.strip() else {}
packet = packet or {}
own['packet'] = packet
(markers / ('%d.tmp' % pid)).write_text(json.dumps(own))
(markers / ('%d.tmp' % pid)).rename(markers / ('%d.json' % pid))
payload = packet.get('payload') or {}
servers = (mcp.get('mcpServers') or {})
# The binary starts a stdio server with its own environment and the entry's env.
got, children = serve({n: e for n, e in servers.items() if e.get('type') == 'stdio'},
                      lambda entry: dict(env, **(entry.get('env') or {})))
hold(children, payload)
session = str(uuid.uuid4())
usage = {'input_tokens': 3, 'output_tokens': 3, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
emit({'type': 'system', 'subtype': 'init', 'cwd': str(cwd), 'session_id': session, 'tools': ['Bash'],
      'mcp_servers': [], 'model': 'configured-model', 'permissionMode': 'default', 'slash_commands': [],
      'apiKeySource': 'none', 'claude_code_version': @@VERSION@@, 'output_style': 'default', 'agents': [],
      'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4())})
def assistant(content):
    emit({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()), 'session_id': session,
          'message': {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant',
                      'model': 'configured-model', 'content': content, 'stop_reason': None, 'stop_sequence': None,
                      'usage': usage}})
def result_of(tool, text, structured):
    emit({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool,
                                                                    'content': text, 'is_error': False}]},
          'parent_tool_use_id': None, 'tool_use_result': structured})
assistant([{'type': 'text', 'text': 'Working the unit.'}])
for name in sorted(got):
    tool = 'toolu_' + uuid.uuid4().hex[:20]
    assistant([{'type': 'tool_use', 'id': tool, 'name': 'mcp__%s__credential' % name, 'input': {}}])
    result_of(tool, got[name], [{'type': 'text', 'text': got[name]}])
# The credentials of each named http server's Authorization header, without the scheme, as a run may print them.
bare = [((servers.get(n) or {}).get('headers') or {}).get('Authorization', '').partition(' ')[2]
        for n in payload.get('bare') or []]
for value in printed(got, payload) + [b for b in bare if b]:
    assistant([{'type': 'text', 'text': value}])
    tool = 'toolu_' + uuid.uuid4().hex[:20]
    command = "printf 'held %s in output' '" + value + "'"
    assistant([{'type': 'tool_use', 'id': tool, 'name': 'Bash', 'input': {'command': command}}])
    done = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True, cwd=str(cwd), env=dict(env))
    result_of(tool, done.stdout, {'stdout': done.stdout, 'stderr': done.stderr, 'interrupted': False, 'isImage': False})
    warn(value)
if payload.get('control'):
    assistant([{'type': 'text', 'text': payload['control']}])
usage['output_tokens'] = 4
emit({'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False, 'num_turns': 1,
      'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0, 'usage': usage,
      'modelUsage': {'configured-model': {'inputTokens': 3, 'outputTokens': 4, 'cacheReadInputTokens': 0,
                                          'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                          'contextWindow': 200000, 'maxOutputTokens': 32000}},
      'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session})
out.close()
err.close()
'''
        fake_codex = '''#!@@PYTHON@@ -B
import json, os, subprocess, sys, time, tomllib
from pathlib import Path
markers = Path(@@MARKERS@@)
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
        # The 0.154.0 binary prints its login status on stderr.
        print('Logged in using ChatGPT', file=sys.stderr)
        sys.exit(0)
    sys.exit(1)
@@COMMON@@
overrides = {}
for at, arg in enumerate(argv):
    if arg == '-c' and at + 1 < len(argv):
        key, _, value = argv[at + 1].partition('=')
        overrides[key] = tomllib.loads('v = ' + value)['v']
table = overrides.get('mcp_servers') or {}
own = {'pid': pid, 'dispatch': dispatch, 'argv': sys.argv, 'cwd': str(cwd), 'env': dict(env), 'mcp_servers': table}
out = open(markers / ('%d.out' % pid), 'w')
err = open(markers / ('%d.err' % pid), 'w')
def emit(event):
    text = json.dumps(complete_event(event))
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def warn(text):
    err.write(text + chr(10))
    err.flush()
    sys.stderr.write(text + chr(10))
    sys.stderr.flush()
packet = json.loads(sys.stdin.buffer.read() or b'{}')
own['packet'] = packet
(markers / ('%d.tmp' % pid)).write_text(json.dumps(own))
(markers / ('%d.tmp' % pid)).rename(markers / ('%d.json' % pid))
payload = packet.get('payload') or {}
# The binary starts a stdio server with its small default environment, the table's env and each env_vars name
# taken from its own environment.
DEFAULT = ('HOME', 'LANG', 'LOGNAME', 'PATH', 'SHELL', 'TERM', 'TMPDIR', 'TZ', 'USER')
got, children = serve(table, lambda entry: dict({n: env[n] for n in DEFAULT if n in env},
                                                **dict(entry.get('env') or {}),
                                                **{n: env[n] for n in entry.get('env_vars') or [] if n in env}))
hold(children, payload)
emit({'type': 'thread.started', 'thread_id': 'thread-158-%d' % pid})
emit({'type': 'turn.started'})
number = [0]
def item(kind, **fields):
    number[0] += 1
    return dict(fields, id='item_%d' % number[0], type=kind)
for name in sorted(got):
    emit({'type': 'item.completed', 'item': item('mcp_tool_call', server=name, tool='credential', arguments={},
                                                  result={'content': [{'type': 'text', 'text': got[name]}]},
                                                  error=None, status='completed')})
for value in printed(got, payload):
    command = "printf 'held %s in output' '" + value + "'"
    done = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True, cwd=str(cwd), env=dict(env))
    emit({'type': 'item.completed', 'item': item('command_execution', aggregated_output=done.stdout, exit_code=0,
                                                  status='completed')})
    warn(value)
    emit({'type': 'item.completed', 'item': {'id': 'item_v%d' % number[0], 'type': 'agent_message', 'text': value}})
emit({'type': 'item.completed', 'item': {'id': 'item_last', 'type': 'agent_message',
                                         'text': payload.get('control') or 'done'}})
emit({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0,
                                          'output_tokens': 4, 'reasoning_output_tokens': 0}})
out.close()
err.close()
'''

        def filled(source):
            return (source.replace('@@COMMON@@', common).replace('@@PYTHON@@', sys.executable)
                    .replace('@@MARKERS@@', repr(str(markers))).replace('@@VERSION@@', repr(VERSION))
                    .replace('@@MCP@@', repr(E.BASELINE['mcp_option'])).replace('@@INPUT@@', repr(E.INPUT_FLAGS[0])))
        fake_claude = fake_formats.embed(filled(fake_claude))
        fake_codex = fake_formats.embed(filled(fake_codex))

        def fake_engine(name):
            # Each engine's generated executable, as VELDO-0172's census reads it back.
            return fake_claude if name == 'claude' else fake_codex
        versions = base / 'home' / '.local' / 'share' / 'claude' / 'versions'
        versions.mkdir(parents=True)
        (versions / VERSION).write_text(fake_claude)
        (versions / VERSION).chmod(0o755)
        FLAGS = ['-' * 2 + 'print', '-' * 2 + 'output-format', 'stream-json', '-' * 2 + 'verbose'] + list(E.INPUT_FLAGS)
        test_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {
            VERSION: {'sha256': file_sha(versions / VERSION), 'flags': list(FLAGS),
                      'environment': {'DISABLE_AUTOUPDATER': '1'}, 'baseline': E.BASELINE,
                      'session_environment': E.session_environment(versions / VERSION)}}}
        (mods / 'runtime').mkdir(exist_ok=True)
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps(test_record, indent=1))
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        E.pin(VERSION, versions=str(versions), state_root=str(factory))
        package = base / 'packages' / 'codex'
        CODEX_BIN = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        CODEX_BIN.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        CODEX_BIN.write_text(fake_codex)
        CODEX_BIN.chmod(0o755)
        codex_record_path = base / 'codex-qualification.json'
        codex_record_path.write_text(json.dumps(X.qualification(str(CODEX_BIN))))

        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4, 'systemd_run': real_systemd_run}
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '-' * 2]
        records_dir = factory / 'records'
        runs_dir = factory / 'runs'
        config = base / 'receiver.json'
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(state / 'receipts'), 'artifacts': str(state / 'artifacts'),
            'state_root': str(factory), 'profile': profile,
            'adapters': {'claude': {'engine': 'claude_code', 'executable': {'version': VERSION}, 'argv': entering},
                         'codex': {'engine': 'codex', 'executable': str(CODEX_BIN), 'qualification': str(codex_record_path),
                                   'argv': entering + [str(CODEX_BIN)] + list(X.FLAGS)}}}))
        RECEIVER_ENV = dict(os.environ)
        RECEIVER_ENV['DBUS_SESSION_BUS_ADDRESS'] = (tools.get('DBUS_SESSION_BUS_ADDRESS')
                                                    or 'unix:path=%s/bus' % runtime)

        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
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
                # The receiver's runs root and this host's worker profile, as the service's line passes them; a Runner
                # that takes neither (the tree before VELDO-0158's fix) is built without, so its rows red by assertion.
                known = inspect.signature(L.Runner).parameters
                where = {k: v for k, v in (('runs', str(runs_dir)), ('profile', profile)) if k in known}
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account, **where)
            return runners[account]

        # THE API (VELDO-0130, VELDO-0144): the authority's judge on this store holding its lock, with the catalog and
        # the credential commands; its edge's signature is the API edge key's own.
        HOST_NAME = 'veldo-158.example.invalid'
        ORIGIN = 'https://' + HOST_NAME
        lock_held = os.open(str(db.parent / 'authority.lock'), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock_held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        closers.append(lambda: os.close(lock_held))
        credentials = CR.Credentials(S, writer, ids, 'authority', sign, rp_id=HOST_NAME, origin=ORIGIN,
                                     state_dir=base / 'credential-state')
        intake = IN.Intake(S, CM, AC, None, writer, domain=INTAKE, projects=(PROJECT,), api_edge='api-edge',
                           journal_signer='authority', sign=sign)
        commands = dict(domain=DOMAIN, repository=REPOSITORY, signer='authority', sign=sign)
        catalog = MC.Catalog(S, writer, **commands)
        mcp_credentials = CV.Credentials(S, writer, keystore=KS.SecretService(str(tool)), **commands)
        authority = AUTH.ApiAuthority(S, CM, writer, ids=ids, domain=INTAKE, edge='api-edge', intake=intake,
                                      settlement=None, credentials=credentials, authority_lock=lock_held,
                                      catalog=catalog, mcp_credentials=mcp_credentials)

        def edge_signer(assertion):
            return sign_as('api-edge', S.canonical_bytes(assertion), AC.SIGNATURE_NAMESPACE), None
        api_state = base / 'api-state'
        api = API.ControlApi({'origin': ORIGIN, 'rp_id': HOST_NAME, 'host': HOST_NAME, 'domain': INTAKE, 'ids': ids,
                              'edge': 'api-edge', 'state_dir': str(api_state)}, authority, edge_signer)
        COOKIE = '__Host-veldo-session'

        def call(method, path, body=None, cookie=None, token=None):
            headers = {'Host': HOST_NAME}
            if method == 'POST':
                headers.update({'Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json'})
            if cookie is not None:
                headers['Cookie'] = '%s=%s' % (COOKIE, cookie)
            if token is not None:
                headers['X-Veldo-Token'] = token
            payload = json.dumps(body).encode() if body is not None else b''
            try:
                status, out, value = api.handle(method, path, headers, payload)
            except Exception as error:  # noqa: BLE001 - a handler that raises is an unknown outcome, recorded
                return 500, {}, {'refusal': 'raised:%s' % type(error).__name__}
            return status, dict(out), value

        def b64(data):
            import base64
            return base64.urlsafe_b64encode(data).decode().rstrip('=')
        passkey = people / 'owner.pem'
        subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out',
                        str(passkey)], check=True, capture_output=True, timeout=10)
        der = subprocess.run(['openssl', 'pkey', '-in', str(passkey), '-pubout', '-outform', 'DER'],
                             check=True, capture_output=True, timeout=10).stdout
        credential_id, handle = b64(os.urandom(32)), {}

        def client(kind, challenge):
            return json.dumps({'type': kind, 'challenge': challenge, 'origin': ORIGIN, 'crossOrigin': False},
                              separators=(',', ':')).encode()

        def webauthn_get(challenge):
            data = client('webauthn.get', challenge)
            auth = hashlib.sha256(HOST_NAME.encode()).digest() + bytes([0x05]) + b'\x00\x00\x00\x00'
            signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(passkey)],
                                       input=auth + hashlib.sha256(data).digest(), check=True,
                                       capture_output=True, timeout=10).stdout
            return {'credential_id': credential_id, 'client_data_json': b64(data), 'authenticator_data': b64(auth),
                    'signature': b64(signature), 'user_handle': handle.get('user')}
        begun = call('POST', '/api/v1/auth/registration/begin', {'label': 'owner'})
        handle['user'] = begun[2]['user_handle']
        offered = call('POST', '/api/v1/auth/registration/credential', {
            'registration_id': begun[2]['registration_id'], 'credential_id': credential_id, 'public_key': b64(der),
            'algorithm': -7, 'client_data_json': b64(client('webauthn.create', begun[2]['challenge']))})
        proof = webauthn_get(offered[2]['possession_challenge'])
        call('POST', '/api/v1/auth/registration/possession',
             dict({k: v for k, v in proof.items() if k != 'credential_id'}, registration_id=begun[2]['registration_id']))
        pending = json.loads((api_state / 'pending' / (begun[2]['registration_id'] + '.json')).read_text())
        passkey_command = CR.enrollment_command(pending, 'owner', next_id('credential'))
        passkey_env = envelope(passkey_command, 'owner')
        credentials.admit(passkey_env, passkey_command, sign_as('owner', AC.canonical_envelope_bytes(passkey_env)))
        issued = call('POST', '/api/v1/auth/challenge', {})
        signed_in = call('POST', '/api/v1/auth/sign-in', webauthn_get(issued[2]['challenge']))
        owner_cookie = (signed_in[1].get('Set-Cookie') or '').split(';')[0].partition('=')[2]
        owner_token = (signed_in[2] or {}).get('csrf_token')
        MCP = '/api/v1/domains/%s/mcp/' % INTAKE

        # THE CREDENTIALS: values with no known pattern and low entropy, assembled at run time, each set through the
        # credential route; the Atlassian one is a bearer Authorization header's value.
        pick = random.SystemRandom()

        def planted(words):
            while True:
                value = '.'.join(w + ''.join(pick.choice('bcdfghjkmnpqrstvwxz') for _ in range(3)) for w in words)
                if SS.shannon(value) < SS.ENTROPY_THRESHOLD and not SS.scan_text(value):
                    return value
        VALUES = {'tracker-token': planted(('amber', 'harbor', 'lantern')),
                  'notes-token': planted(('cedar', 'meadow', 'pebble')),
                  'atlassian-token': 'Bearer ' + planted(('willow', 'copper', 'summit')),
                  'other-token': planted(('violet', 'canyon', 'ember')),
                  'gone-token': planted(('maple', 'river', 'stone')),
                  'clash-token': planted(('hazel', 'orchard', 'tide'))}
        BEARER = VALUES['atlassian-token'].split(' ', 1)[1]
        control_word = 'plain.control.' + ''.join(pick.choice('bcdfghjkm') for _ in range(4))
        REFS, set_answers = {}, {}
        for identity, value in VALUES.items():
            answer = call('POST', MCP + 'credentials/set', {'id': identity, 'label': identity, 'base': 0, 'value': value},
                          cookie=owner_cookie, token=owner_token)
            set_answers[identity] = answer
            REFS[identity] = (answer[2] or {}).get('reference') or 'keychain:veldo/absent'

        def stdio(identity, names, environment):
            return dict(id=identity, label=identity, transport='stdio', command=sys.executable,
                        arguments=['-B', str(server), identity] + list(names), url=None, environment=environment,
                        headers={}, hosts=['linux'], read_only_tools=['credential'])
        DEFINITIONS = {
            'tracker': stdio('tracker', ['TRACKER_TOKEN'], {'MODE': {'literal': 'read'},
                                                                    'TRACKER_TOKEN': {'reference': REFS['tracker-token']}}),
            'notes': stdio('notes', ['NOTES_TOKEN'], {'NOTES_TOKEN': {'reference': REFS['notes-token']}}),
            'atlassian': dict(id='atlassian', label='Atlassian', transport='http', command=None, arguments=[],
                              url='https://mcp.atlassian.example.invalid/v1/mcp', environment={},
                              headers={'Authorization': {'reference': REFS['atlassian-token']}}, hosts=['linux'],
                              read_only_tools=['jira.search']),
            'plain': stdio('plain', ['MODE'], {'MODE': {'literal': 'owner-selected'}}),
            'other': stdio('other', ['OTHER_TOKEN'], {'OTHER_TOKEN': {'reference': REFS['other-token']}}),
            'gone': stdio('gone', ['GONE_TOKEN'], {'GONE_TOKEN': {'reference': REFS['gone-token']}}),
            # A credential named for a variable the Codex engine already has: inherited, and set by its account.
            'clash-path': stdio('clash-path', ['PATH'], {'PATH': {'reference': REFS['clash-token']}}),
            'clash-home': stdio('clash-home', ['CODEX_HOME'], {'CODEX_HOME': {'reference': REFS['clash-token']}}),
        }
        saves = {name: call('POST', MCP + 'catalog/save', {'definition': d, 'base': 0}, cookie=owner_cookie,
                            token=owner_token) for name, d in DEFINITIONS.items()}

        with region('fixture/route-set'):
            stored = [json.loads(r[0]) for r in writer.execute("SELECT data FROM entities WHERE kind='credential'")]
            check('fixture/route-set', 'every credential was set through the API credential route on the signed-in '
                  'passkey session and its value is only in the keystore [%s]'
                  % {k: (a[0], (a[2] or {}).get('refusal')) for k, a in set_answers.items()},
                  signed_in[0] == 200 and edge_enrolled.get('outcome') == 'accepted'
                  and all(a[0] == 200 and (a[2] or {}).get('outcome') == 'written' for a in set_answers.values())
                  and all(item_of(REFS[k]).read_text() == v for k, v in VALUES.items())
                  and sorted(d['id'] for d in stored) == sorted(VALUES)
                  and all(set(d) == {'id', 'label', 'reference', 'set_at', 'set_by'} for d in stored))
            check('fixture/route-set', 'every server was saved through the catalog route as its first revision [%s]'
                  % {k: (a[0], (a[2] or {}).get('refusal')) for k, a in saves.items()},
                  all(a[0] == 200 and (a[2] or {}).get('revision') == 1 for a in saves.values()))

        def selected(*names):
            return {'tools': ['Bash'], 'model': 'configured-model',
                    'mcp': [{'server': name, 'revision': 1} for name in names]}
        units = []

        def dispatch(account, adapter, configuration, payload, during=None):
            """Submit, act while the worker runs, then wait: (launch, record, submit error, during's answer)."""
            units.append(len(units) + 1)
            unit = admitted('VELDO-158%02d' % units[-1])
            launch, error = attempt(lambda: runner(account).submit(
                unit, 'build', holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter=adapter,
                configuration=configuration, deadline=time.time() + 60))
            seen = during(launch) if during and launch is not None else None
            record = (attempt(lambda: runner(account).wait(launch))[0] or {}) if launch is not None else {}
            return launch, record, error, seen

        def own_of(dispatch_id):
            for path in sorted(markers.glob('[0-9]*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    lines = {}
                    for stream, suffix in (('engine', '.out'), ('stderr', '.err')):
                        found = markers / ('%d%s' % (data['pid'], suffix))
                        lines[stream] = found.read_text().split('\n')[:-1] if found.exists() else []
                    data['lines'] = lines
                    return data
            return {}

        def servers_of(dispatch_id):
            return {data['server']: data for data in (json.loads(p.read_text()) for p in sorted(markers.glob('server-*.json')))
                    if data.get('dispatch') == dispatch_id}

        def kept(dispatch_id):
            path = Path(ER.path(str(records_dir), dispatch_id))
            if not path.is_file():
                return None, []
            raw = path.read_bytes().split(b'\n')[:-1]
            return json.loads(raw[0]), [json.loads(x) for x in raw[1:]]

        SECRETS = sorted(set(VALUES.values()) | {BEARER})

        def census(holder):
            """While the run holds: every process of this account, from /proc, and which of them hold a value in their
            command line or their environment; then the run is released."""
            ready = markers / 'never'
            end = time.time() + 30
            while time.time() < end:
                owned = own_of(holder['launch'].dispatch_id)
                ready = markers / ('%s.ready' % owned.get('pid'))
                if owned and ready.exists():
                    break
                time.sleep(0.02)
            found = {'inspected': 0, 'cmdline': {}, 'environ': {}, 'ready': ready.exists()}
            for entry in Path('/proc').glob('[0-9]*'):
                try:
                    if entry.stat().st_uid != os.getuid():
                        continue
                    commandline = (entry / 'cmdline').read_bytes()
                    environment = (entry / 'environ').read_bytes()
                except OSError:
                    continue
                found['inspected'] += 1
                for value in SECRETS:
                    if value.encode() in commandline:
                        found['cmdline'].setdefault(int(entry.name), []).append(value)
                    if value.encode() in environment:
                        found['environ'].setdefault(int(entry.name), []).append(value)
                if int(entry.name) in found['environ']:
                    with contextlib.suppress(OSError):
                        found.setdefault('cgroup', {})[int(entry.name)] = (entry / 'cgroup').read_text()
            Path(holder['hold']).write_text('go')
            return found

        def holding(name):
            holder = {'hold': str(base / ('hold-' + name))}
            return holder, (lambda launch: census(dict(holder, launch=launch)))

        def run_dirs():
            return sorted(p.name for p in runs_dir.iterdir()) if runs_dir.is_dir() else []

        def report_of(launch, event='credentials'):
            for message in (launch.messages if launch else []):
                if isinstance(message, dict) and message.get('event') == event:
                    return message.get('credentials') or {} if event == 'credentials' else message
            return {}

        # THE RUNS. Claude Code and Codex, each selecting the tracker and notes stdio servers and the Atlassian http one.
        MAIN = selected('tracker', 'notes', 'atlassian')
        runs = {}
        for engine, account in (('claude', 'acct-158c'), ('codex', 'acct-158x')):
            holder, during = holding(engine)
            payload = {'task': 'work the unit', 'hold': holder['hold'], 'print': ['tracker', 'notes'],
                       'bare': ['atlassian'], 'control': control_word}
            launch, record, error, seen = dispatch(account, engine, MAIN, payload, during)
            runs[engine] = dict(launch=launch, record=record, error=error, census=seen or {},
                                own=own_of(launch.dispatch_id) if launch else {},
                                servers=servers_of(launch.dispatch_id) if launch else {},
                                header_lines=kept(launch.dispatch_id) if launch else (None, []), runs_after=run_dirs())
        # Another run, whose configuration selects only the other server, prints the tracker's value too (read from a
        # file of the suite's own): it was never resolved for this run.
        foreign = base / 'foreign-value'
        foreign.write_text(VALUES['tracker-token'])
        holder, during = holding('other')
        other_launch, other_record, other_error, _ = dispatch(
            'acct-158x', 'codex', selected('other'),
            {'task': 'work the unit', 'hold': holder['hold'], 'print': ['other'], 'foreign': str(foreign)}, during)
        other_own = own_of(other_launch.dispatch_id) if other_launch else {}
        lookups_main = [c for c in calls() if c['action'] == 'lookup']

        # AC2: the keystore locked, unreachable, and a reference that resolves to nothing.
        refused = {}
        for case, mode_, engine, account, server_ in (
                ('locked', 'locked', 'claude', 'acct-158c', 'tracker'),
                ('unreachable', 'unreachable', 'codex', 'acct-158x', 'tracker'),
                ('not-found', '', 'claude', 'acct-158c', 'gone')):
            (keystore / 'mode').write_text(mode_)
            if case == 'not-found':
                item_of(REFS['gone-token']).unlink(missing_ok=True)
            before = len(calls())
            launch, record, error, _ = dispatch(account, engine, selected(server_), {'task': 'work the unit'})
            refused[case] = dict(launch=launch, record=record, error=error, calls=calls()[before:],
                                 own=own_of(launch.dispatch_id) if launch else {}, runs_after=run_dirs())
            if case == 'locked':
                # The same locked state: a run whose configuration needs no credential launches normally.
                before = len(calls())
                launch, record, error, _ = dispatch(account, engine, selected('plain'), {'task': 'work the unit'})
                refused['none-needed'] = dict(launch=launch, record=record, error=error, calls=calls()[before:],
                                              own=own_of(launch.dispatch_id) if launch else {},
                                              servers=servers_of(launch.dispatch_id) if launch else {})
        (keystore / 'mode').write_text('')

        # A Codex credential named for a variable the engine already has, refused by name before any engine exists.
        collided = {}
        for name_, server_ in (('PATH', 'clash-path'), ('CODEX_HOME', 'clash-home')):
            before = len(calls())
            launch, record, error, _ = dispatch('acct-158x', 'codex', selected(server_), {'task': 'work the unit'})
            collided[name_] = dict(launch=launch, record=record, error=error, calls=calls()[before:],
                                   own=own_of(launch.dispatch_id) if launch else {}, runs_after=run_dirs())

        # A DEAD RECEIVER (VELDO-0154's orphan path): once the run holds, its configuration written, the receiver is
        # sent SIGKILL by its exact pid, checked against the identity it recorded at acceptance.
        def run_dir_of(launch):
            return runs_dir / hashlib.sha256(launch.dispatch_id.encode()).hexdigest()[:32] if launch else None

        def killing(launch):
            seen = {'ready': False, 'killed': False}
            end = time.time() + 30
            while time.time() < end:
                owned = own_of(launch.dispatch_id)
                if owned and (markers / ('%s.ready' % owned.get('pid'))).exists():
                    seen['ready'] = True
                    break
                time.sleep(0.02)
            owned = own_of(launch.dispatch_id)
            config_path = (owned.get('mcp_file') or {}).get('path')
            with contextlib.suppress(OSError):
                seen['config_text'] = Path(config_path).read_text() if config_path else None
            seen['config_path'] = config_path
            seen['dir_before'] = run_dir_of(launch).is_dir()
            receiver = (dispatches.record(launch.dispatch_id) or {}).get('receiver') or {}
            child = launch.child
            if child is not None and child.poll() is None and receiver.get('pid') == child.pid:
                identity, _ = attempt(lambda: L.process_identity(child.pid))
                if identity and identity.get('start') == receiver.get('start'):
                    os.kill(child.pid, signal.SIGKILL)
                    seen['killed'] = True
            return seen

        def group_gone(launch):
            group = (launch.group or {}) if launch else {}
            return bool(group.get('cgroup')) and CT.populated(CT.CGROUP / group['cgroup'].lstrip('/')) is not True

        # Claude Code, its receiver killed: its orphan release removes the run directory once the run is gone.
        orphan = {}
        holder, _unused = holding('orphan')
        launch, record, error, seen = dispatch('acct-158c', 'claude', selected('tracker'),
                                               {'task': 'work the unit', 'hold': holder['hold']}, killing)
        orphan.update(launch=launch, record=record, error=error, seen=seen or {},
                      dir_after_wait=bool(launch) and run_dir_of(launch).is_dir(),
                      alive_after_wait=bool(launch) and not group_gone(launch))
        released, orphan['release_error'] = attempt(lambda: runner('acct-158c').orphaned(launch)) if launch else ([], None)
        orphan.update(released=released or [], dir_after=bool(launch) and run_dir_of(launch).exists(),
                      config_after=bool((seen or {}).get('config_path')) and Path(seen['config_path']).exists(),
                      gone_after=group_gone(launch))

        # Codex, its receiver killed and its orphan never released: the service's start keeps the directory while the
        # run is alive and removes it at the start after the run has ended.
        work_path = base / 'work.json'
        work_path.write_text(json.dumps({'schema': SV.WORK_SCHEMA, 'repositories': {REPOSITORY: {}}}))
        work_path.chmod(0o600)
        service_conn = SV.S.open_store(str(db))
        connections.append(service_conn)

        def service_start():
            logged = []
            service = types.SimpleNamespace(config={'receiver': {'configs': {REPOSITORY: str(config)}}},
                                            conn=service_conn, domain=DOMAIN, principal='runner', sign=sign, generation=1,
                                            _log=logged.append)
            loop, refusal = SV.open_loop({'work': str(work_path)}, service)
            swept = [x for x in logged if x.get('operation') == 'runs_swept']
            return {'loop': loop is not None, 'refusal': refusal,
                    'swept': ((swept[-1].get('swept') or {}).get(REPOSITORY) if swept else None)}
        restart = {}
        holder_b, _unused = holding('restart')
        launch_b, record_b, error_b, seen_b = dispatch('acct-158x', 'codex', selected('tracker'),
                                                       {'task': 'work the unit', 'hold': holder_b['hold']}, killing)
        restart.update(launch=launch_b, record=record_b, error=error_b, seen=seen_b or {},
                       dir_after_wait=bool(launch_b) and run_dir_of(launch_b).is_dir())
        restart['alive_at_first'] = bool(launch_b) and not group_gone(launch_b)
        restart['first'] = service_start()
        restart['dir_after_first'] = bool(launch_b) and run_dir_of(launch_b).is_dir()
        # The run ends: released, it writes to its dead receiver's pipe and exits, and its group empties.
        Path(holder_b['hold']).write_text('go')
        end = time.time() + 20
        while launch_b and not group_gone(launch_b) and time.time() < end:
            time.sleep(0.05)
        restart['gone_before_second'] = group_gone(launch_b)
        restart['dir_before_second'] = bool(launch_b) and run_dir_of(launch_b).is_dir()
        restart['second'] = service_start()
        restart['dir_after_second'] = bool(launch_b) and run_dir_of(launch_b).exists()

        claude, codex = runs['claude'], runs['codex']
        engine_pids = {name: r['own'].get('pid') for name, r in runs.items()}
        server_pids = {name: {s['pid'] for s in r['servers'].values()} for name, r in runs.items()}

        # AC1: Claude Code's values reach it through its generated MCP configuration in the run's private directory.
        with region('delivery/claude-private-file'):
            own = claude['own']
            mcp = (own.get('mcp') or {}).get('mcpServers') or {}
            info = own.get('mcp_file') or {}
            path = Path(info.get('path') or '/nonexistent')
            check('delivery/claude-private-file', 'the run exited through the real receiver and wrapper [%s %s]'
                  % (claude['record'].get('state'), claude['error']),
                  claude['error'] is None and claude['record'].get('state') == 'exited' and bool(own))
            check('delivery/claude-private-file', 'the generated MCP configuration holds exactly the selected servers, each '
                  'credential value included where its definition names it [%s]' % sorted(mcp),
                  sorted(mcp) == ['atlassian', 'notes', 'tracker']
                  and (mcp.get('tracker') or {}).get('env') == {'MODE': 'read', 'TRACKER_TOKEN': VALUES['tracker-token']}
                  and (mcp.get('notes') or {}).get('env') == {'NOTES_TOKEN': VALUES['notes-token']}
                  and (mcp.get('atlassian') or {}).get('headers') == {'Authorization': VALUES['atlassian-token']}
                  and (mcp.get('atlassian') or {}).get('url') == DEFINITIONS['atlassian']['url']
                  and (mcp.get('tracker') or {}).get('args') == DEFINITIONS['tracker']['arguments'])
            engine_env = own.get('env') or {}
            check('delivery/claude-private-file', 'the file is 0600 in a 0700 directory of the run\'s own under the factory '
                  'state root, outside the clone and never the engine\'s runtime directory [%s]' % info,
                  info.get('file_mode') == 0o600 and info.get('dir_mode') == 0o700
                  and path.parent.parent.parent == runs_dir and runs_dir.parent == factory
                  and not str(path).startswith(str(clones_root)) and not str(path).startswith(own.get('cwd') or '/')
                  and engine_env.get('XDG_RUNTIME_DIR') not in (None, str(path.parent))
                  and not str(path).startswith(engine_env.get('XDG_RUNTIME_DIR') or '/'))
            check('delivery/claude-private-file', 'the engine\'s own environment and command line hold no value; each '
                  'server received its credential in its environment from the file',
                  not [v for v in SECRETS if v in json.dumps(engine_env) or v in json.dumps(own.get('argv'))]
                  and (claude['servers'].get('tracker') or {}).get('env', {}).get('TRACKER_TOKEN') == VALUES['tracker-token']
                  and (claude['servers'].get('notes') or {}).get('env', {}).get('NOTES_TOKEN') == VALUES['notes-token'])

        # AC1: Codex's values reach its engine environment under the names its servers' definitions give them.
        with region('delivery/codex-environment'):
            own = codex['own']
            table = own.get('mcp_servers') or {}
            engine_env = own.get('env') or {}
            header_variable = (table.get('atlassian') or {}).get('bearer_token_env_var')
            check('delivery/codex-environment', 'the run exited through the real receiver and wrapper [%s %s]'
                  % (codex['record'].get('state'), codex['error']),
                  codex['error'] is None and codex['record'].get('state') == 'exited' and bool(own))
            check('delivery/codex-environment', 'the generated mcp_servers table names each stdio credential by its '
                  'variable in env_vars and the Atlassian bearer token by bearer_token_env_var, literals only in env [%s]'
                  % table,
                  sorted(table) == ['atlassian', 'notes', 'tracker']
                  and table['tracker'].get('env_vars') == ['TRACKER_TOKEN'] and table['tracker'].get('env') == {'MODE': 'read'}
                  and table['notes'].get('env_vars') == ['NOTES_TOKEN'] and 'env' not in table['notes']
                  and isinstance(header_variable, str) and table['atlassian'].get('url') == DEFINITIONS['atlassian']['url']
                  and not [v for v in SECRETS if v in json.dumps(table)])
            check('delivery/codex-environment', 'the engine environment carries each value under that name',
                  engine_env.get('TRACKER_TOKEN') == VALUES['tracker-token']
                  and engine_env.get('NOTES_TOKEN') == VALUES['notes-token']
                  and isinstance(header_variable, str) and engine_env.get(header_variable) == BEARER)
            check('delivery/codex-environment', 'each stdio server received its credential through env_vars',
                  (codex['servers'].get('tracker') or {}).get('env', {}).get('TRACKER_TOKEN') == VALUES['tracker-token']
                  and (codex['servers'].get('notes') or {}).get('env', {}).get('NOTES_TOKEN') == VALUES['notes-token'])

        # AC1: no launched process carries a value on its command line; only where the route puts it, in an environment.
        with region('delivery/command-lines'):
            for engine in ('claude', 'codex'):
                seen = runs[engine]['census']
                holders = set(seen.get('environ') or {})
                wanted = set(server_pids[engine]) | ({engine_pids[engine]} if engine == 'codex' else set())
                unit = CT.unit_name(runs[engine]['launch'].dispatch_id) if runs[engine]['launch'] else None
                inside = {pid for pid, group in (seen.get('cgroup') or {}).items() if unit and unit in group}
                check('delivery/command-lines', engine + ': every process of the account was read while the run held '
                      '[%d read, ready %s]' % (seen.get('inspected', 0), seen.get('ready')),
                      seen.get('ready') is True and seen.get('inspected', 0) > 3 and len(server_pids[engine]) == 2)
                check('delivery/command-lines', engine + ': no process holds any value on its command line [%s]'
                      % sorted(seen.get('cmdline') or {}),
                      seen.get('ready') is True and not seen.get('cmdline'))
                # Codex's values are its engine environment's, which the wrapper held until it became the engine (its
                # forked heartbeat keeps that block); every holder is a process of the run's own containment group.
                check('delivery/command-lines', engine + ': the environments holding a value are its servers\''
                      + (' and its engine\'s, all inside the run\'s own group' if engine == 'codex' else ' alone')
                      + ' [%s, wanted %s, inside %s]' % (sorted(holders), sorted(wanted), sorted(inside)),
                      seen.get('ready') is True and bool(wanted) and holders == inside
                      and (holders == wanted if engine == 'claude' else wanted <= holders))
            check('delivery/command-lines', 'every keystore lookup carried the reference alone, never a value',
                  bool(lookups_main) and all(not [v for v in SECRETS if v in ' '.join(c['argv'])] for c in calls()))

        # AC1: a server receives its own credential and no other server's.
        with region('delivery/own-server-only'):
            for engine in ('claude', 'codex'):
                servers = runs[engine]['servers']
                tracker_env = json.dumps((servers.get('tracker') or {}).get('env') or {})
                notes_env = json.dumps((servers.get('notes') or {}).get('env') or {})
                check('delivery/own-server-only', engine + ': the tracker server holds none of the notes credential and '
                      'the notes server none of the tracker\'s',
                      sorted(servers) == ['notes', 'tracker']
                      and VALUES['tracker-token'] in tracker_env and VALUES['notes-token'] not in tracker_env
                      and VALUES['notes-token'] in notes_env and VALUES['tracker-token'] not in notes_env
                      and not [v for v in (VALUES['other-token'], VALUES['gone-token'], BEARER) if v in tracker_env + notes_env])
            looked = [c['argv'][-1] for c in lookups_main]
            names = {k: REFS[k].split(':', 1)[1] for k in REFS}
            check('delivery/own-server-only', 'the keystore was asked only for the selected servers\' credentials [%d lookups]'
                  % len(looked),
                  looked.count(names['tracker-token']) == 2 and looked.count(names['notes-token']) == 2
                  and looked.count(names['atlassian-token']) == 2 and looked.count(names['other-token']) == 1
                  and names['gone-token'] not in looked)

        # AC1: never through the packet, the contract or the journal.
        with region('delivery/not-in-packet-contract-journal'):
            launches = [r['launch'] for r in runs.values()] + [other_launch]
            contracts = json.dumps([l.contract for l in launches if l]) + json.dumps([dispatches.record(l.dispatch_id)
                                                                                     for l in launches if l])
            packets = json.dumps([r['own'].get('packet') for r in runs.values()] + [other_own.get('packet')])
            store_bytes = b''.join(p.read_bytes() for p in db.parent.glob('control.sqlite3*') if p.is_file())
            journal = json.dumps([list(r) for r in writer.execute('SELECT * FROM journal')])
            messages = json.dumps([m for l in launches if l for m in l.messages])
            delivered = [(runs[e]['servers'].get('tracker') or {}).get('env', {}).get('TRACKER_TOKEN') for e in runs]
            check('delivery/not-in-packet-contract-journal', 'the contracts and dispatch records name the selected '
                  'revisions and hold no value, though both runs\' servers received it [%d delivered]'
                  % delivered.count(VALUES['tracker-token']),
                  delivered == [VALUES['tracker-token']] * 2
                  and all(l and l.contract['capability']['configuration'].get('mcp') for l in launches)
                  and not [v for v in SECRETS if v in contracts])
            check('delivery/not-in-packet-contract-journal', 'the packets the engines read hold no value',
                  all(r['own'].get('packet') for r in runs.values()) and not [v for v in SECRETS if v in packets])
            check('delivery/not-in-packet-contract-journal', 'the journal and every byte of the store hold no value, nor '
                  'anything the receiver reported [%d journal rows]' % writer.execute('SELECT COUNT(*) FROM journal').fetchone()[0],
                  len(store_bytes) > 0 and journal.count('dispatch') > 0
                  and not [v for v in SECRETS if v.encode() in store_bytes or v in journal or v in messages])

        # AC1: the run's private directory is removed when it is reaped.
        with region('delivery/private-dir-removed'):
            for engine in ('claude', 'codex'):
                run_dir = hashlib.sha256(runs[engine]['launch'].dispatch_id.encode()).hexdigest()[:32] \
                    if runs[engine]['launch'] else None
                check('delivery/private-dir-removed', engine + ': the run\'s directory is gone once it was reaped',
                      run_dir is not None and runs[engine]['record'].get('state') == 'exited'
                      and run_dir not in runs[engine]['runs_after'] and not (runs_dir / run_dir).exists())
            check('delivery/private-dir-removed', 'the Claude Code configuration file the engine read, holding the '
                  'values, is gone',
                  bool((claude['own'].get('mcp_file') or {}).get('path'))
                  and VALUES['tracker-token'] in json.dumps(claude['own'].get('mcp') or {})
                  and not Path(claude['own']['mcp_file']['path']).exists())
            check('delivery/private-dir-removed', 'a refused launch leaves no run directory [%s]' % run_dirs(),
                  all(not r['runs_after'] for r in refused.values() if 'runs_after' in r) and not run_dirs())

        # AC1: the receiver reports the revisions, credential ids and routes, never a value.
        with region('delivery/report'):
            for engine, route in (('claude', 'private_file'), ('codex', 'engine_environment')):
                report = report_of(runs[engine]['launch'])
                check('delivery/report', engine + ': the credentials event names each revision, credential id and its '
                      'route [%s]' % report,
                      report.get('servers') == [{'id': n, 'revision': 1} for n in ('tracker', 'notes', 'atlassian')]
                      and report.get('credentials') == ['atlassian-token', 'notes-token', 'tracker-token']
                      and sorted(r['credential'] for r in report.get('routes') or []) == report.get('credentials')
                      and all(r['route'] == route for r in report.get('routes') or [])
                      and (report.get('metrics') or {}).get('credentials_resolved') == 3
                      and not [v for v in SECRETS if v in json.dumps(report)])

        # AC2: a credential that cannot be resolved refuses the launch by name, before any engine exists.
        for case, row, reason, server_ in (('locked', 'refusal/keystore-locked', 'keystore_locked', 'tracker'),
                                           ('unreachable', 'refusal/keystore-unreachable', 'keystore_unreachable', 'tracker'),
                                           ('not-found', 'refusal/reference-not-found', 'reference_not_found', 'gone')):
            with region(row):
                got = refused[case]
                identity = 'gone-token' if case == 'not-found' else 'tracker-token'
                name = REFS[identity].split(':', 1)[1]
                event = report_of(got['launch'], 'refused')
                check(row, 'the dispatch is refused as credential_unavailable:%s [%s %s]'
                      % (identity, got['record'].get('state'), got['record'].get('refusal')),
                      got['error'] is None and got['record'].get('state') == 'refused'
                      and got['record'].get('refusal') == 'credential_unavailable:' + identity
                      and (got['launch'].result if got['launch'] else None) == 'refused')
                check(row, 'the keystore was asked for that reference and no engine process was started [%d calls]'
                      % len(got['calls']),
                      any(c['action'] == 'lookup' and c['argv'][-1] == name for c in got['calls'])
                      and not got['own'] and got['launch'] is not None
                      and not [m for m in got['launch'].messages if m.get('event') == 'running'])
                check(row, 'the refusal names the selected revision, the credential and the reason, never a value [%s]'
                      % event.get('credentials'),
                      (event.get('credentials') or {}).get('servers') == [{'id': server_, 'revision': 1}]
                      and (event.get('credentials') or {}).get('credential') == identity
                      and (event.get('credentials') or {}).get('reason') == reason
                      and not [v for v in SECRETS if v in json.dumps(event)])

        with region('refusal/no-credential-launches'):
            got = refused['none-needed']
            check('refusal/no-credential-launches', 'with the keystore still locked, a run whose configuration needs no '
                  'credential launches normally with its server [%s %s]' % (got['record'].get('state'), got['error']),
                  got['error'] is None and got['record'].get('state') == 'exited' and bool(got['own'])
                  and (got['servers'].get('plain') or {}).get('env', {}).get('MODE') == 'owner-selected'
                  and not [c for c in got['calls'] if c['action'] == 'lookup'])

        # AC3: every value resolved for a run is replaced in its execution record.
        MARKER = ER.marker('mcp_credential')

        def words(value):
            return [w for w in value.replace('Bearer ', '').split('.') if w]
        for engine, row in (('claude', 'redaction/claude-keystore-value'), ('codex', 'redaction/codex-keystore-value')):
            with region(row):
                own = runs[engine]['own']
                _header, lines = runs[engine]['header_lines']
                everything = '\n'.join(x.get('payload', '') for x in lines)
                printed_engine = (own.get('lines') or {}).get('engine') or []
                printed_err = (own.get('lines') or {}).get('stderr') or []
                places = {'alone': any(json.dumps(VALUES['tracker-token']) in p for p in printed_engine),
                          'command output': any('held %s in output' % VALUES['tracker-token'] in p for p in printed_engine),
                          'error stream': VALUES['tracker-token'] in printed_err}
                pairs = list(zip([x.get('payload', '') for x in lines if x.get('stream') == 'engine'], printed_engine)) + \
                    list(zip([x.get('payload', '') for x in lines if x.get('stream') == 'stderr'], printed_err))
                counted = [k.count(MARKER) >= p.count(VALUES['tracker-token']) + p.count(VALUES['notes-token'])
                           for k, p in pairs]
                leaked = [w for v in (VALUES['tracker-token'], VALUES['notes-token']) for w in words(v) if w in everything]
                check(row, 'the run printed the keystore values alone, inside a command\'s output and on its error stream '
                      '[%s]' % places, runs[engine]['record'].get('state') == 'exited' and all(places.values()))
                check(row, 'every occurrence is replaced by the marker naming its kind and no line holds any part of '
                      'either value [%s, %d lines]' % (leaked, len(lines)),
                      len(pairs) == len(printed_engine) + len(printed_err) and len(pairs) > 5 and all(counted)
                      and not leaked and everything.count(MARKER) >= 6)
                redacted = [x for x in lines if MARKER in x.get('payload', '')]
                check(row, 'each such line\'s redaction field names the kind [%d lines]' % len(redacted),
                      redacted and all('mcp_credential' in (x.get('redacted') or []) for x in redacted))

        with region('redaction/per-run-set'):
            _header, lines = kept(other_launch.dispatch_id) if other_launch else (None, [])
            everything = '\n'.join(x.get('payload', '') for x in lines)
            check('redaction/per-run-set', 'a run selecting only the other server exited, its own value replaced [%s]'
                  % other_record.get('state'),
                  other_error is None and other_record.get('state') == 'exited'
                  and not [w for w in words(VALUES['other-token']) if w in everything] and MARKER in everything)
            check('redaction/per-run-set', 'the tracker value resolved for the other runs is not in its set: printed by '
                  'this run, it is kept as printed',
                  VALUES['tracker-token'] in everything
                  and VALUES['tracker-token'] in '\n'.join((other_own.get('lines') or {}).get('stderr') or []))

        # The bearer token Claude Code's generated configuration holds, printed without its scheme.
        with region('redaction/claude-bare-bearer'):
            own = claude['own']
            _header, lines = claude['header_lines']
            everything = '\n'.join(x.get('payload', '') for x in lines)
            printed_engine = (own.get('lines') or {}).get('engine') or []
            printed_err = (own.get('lines') or {}).get('stderr') or []
            places = {'alone': any(json.dumps(BEARER) in p for p in printed_engine),
                      'command output': any('held %s in output' % BEARER in p for p in printed_engine),
                      'error stream': BEARER in printed_err}
            pairs = list(zip([x.get('payload', '') for x in lines if x.get('stream') == 'engine'], printed_engine)) + \
                list(zip([x.get('payload', '') for x in lines if x.get('stream') == 'stderr'], printed_err))
            bare_pairs = [(k, p) for k, p in pairs if BEARER in p]
            leaked = [w for w in words(BEARER) if w in everything]
            check('redaction/claude-bare-bearer', 'the Claude Code run printed the bearer token without its scheme alone, '
                  'inside a command\'s output and on its error stream [%s]' % places,
                  claude['record'].get('state') == 'exited' and all(places.values())
                  and not any(VALUES['atlassian-token'] in p for p in printed_engine + printed_err))
            check('redaction/claude-bare-bearer', 'every occurrence is replaced by the marker naming its kind and no line '
                  'holds any part of the token [%s, %d lines]' % (leaked, len(bare_pairs)),
                  len(pairs) == len(printed_engine) + len(printed_err) and len(bare_pairs) >= 3
                  and all(k.count(MARKER) >= p.count(BEARER) for k, p in bare_pairs) and not leaked)

        # A Codex credential never replaces a variable the engine already has.
        with region('refusal/env-collision'):
            for name_, got in sorted(collided.items()):
                event = report_of(got['launch'], 'refused')
                check('refusal/env-collision', '%s: the dispatch is refused as invalid_input:mcp_delivery:env_collision:%s '
                      '[%s %s]' % (name_, name_, got['record'].get('state'), got['record'].get('refusal')),
                      got['error'] is None and got['record'].get('state') == 'refused'
                      and got['record'].get('refusal') == 'invalid_input:mcp_delivery:env_collision:' + name_)
                check('refusal/env-collision', '%s: the credential was resolved, no engine process started and no run '
                      'directory is left [%s]' % (name_, got['runs_after']),
                      any(c['action'] == 'lookup' for c in got['calls']) and not got['own']
                      and not [m for m in (got['launch'].messages if got['launch'] else []) if m.get('event') == 'running']
                      and not got['runs_after'])
                check('refusal/env-collision', '%s: the refusal names the credential and never its value' % name_,
                      (event.get('credentials') or {}).get('credential') == 'clash-token'
                      and not [v for v in SECRETS if v in json.dumps(event)])

        # A dead receiver removes no run directory: its orphan release does, once the run is gone.
        with region('orphan/run-directory-removed'):
            seen = orphan['seen']
            check('orphan/run-directory-removed', 'the receiver was sent SIGKILL while the run held, its generated MCP '
                  'configuration holding the value in the run directory [%s]'
                  % {k: v for k, v in seen.items() if k != 'config_text'},
                  seen.get('ready') and seen.get('killed') and seen.get('dir_before')
                  and VALUES['tracker-token'] in (seen.get('config_text') or '')
                  and str(seen.get('config_path') or '').startswith(str(run_dir_of(orphan['launch'])) + os.sep))
            check('orphan/run-directory-removed', 'the run is recorded outcome_unknown and, still alive, keeps its '
                  'directory [%s, dir %s, alive %s]' % (orphan['record'].get('state'), orphan['dir_after_wait'],
                                                        orphan['alive_after_wait']),
                  orphan['record'].get('state') == 'unknown' and orphan['dir_after_wait'] and orphan['alive_after_wait'])
            check('orphan/run-directory-removed', 'after the orphan release the run is gone and so are its directory and '
                  'the configuration file holding the value [%s %s, dir %s, file %s]'
                  % (orphan['released'], orphan['release_error'], orphan['dir_after'], orphan['config_after']),
                  orphan['launch'] is not None and orphan['released'] == [orphan['launch'].dispatch_id]
                  and orphan['gone_after'] and not orphan['dir_after'] and not orphan['config_after'])

        with region('orphan/live-run-kept'):
            seen = restart['seen']
            check('orphan/live-run-kept', 'the Codex run\'s receiver was sent SIGKILL while the run held and the run is '
                  'recorded outcome_unknown [%s %s]' % ({k: v for k, v in seen.items() if k != 'config_text'},
                                                         restart['record'].get('state')),
                  seen.get('ready') and seen.get('killed') and seen.get('dir_before')
                  and restart['record'].get('state') == 'unknown' and restart['dir_after_wait'])
            check('orphan/live-run-kept', 'the service\'s start, its dispatch settled but its run alive, keeps the run\'s '
                  'directory [%s, alive %s, dir %s]' % (restart['first'], restart['alive_at_first'],
                                                        restart['dir_after_first']),
                  restart['launch'] is not None and restart['first']['loop'] and restart['alive_at_first']
                  and restart['dir_after_first'] and isinstance(restart['first']['swept'], list)
                  and restart['launch'].dispatch_id not in restart['first']['swept'])

        with region('orphan/start-sweep'):
            check('orphan/start-sweep', 'once the run ended, nothing had removed its directory before the next start '
                  '[gone %s, dir %s]' % (restart['gone_before_second'], restart['dir_before_second']),
                  restart['gone_before_second'] and restart['dir_before_second'])
            check('orphan/start-sweep', 'the service\'s next start removes the directory left from before and names its '
                  'dispatch [%s, dir %s]' % (restart['second'], restart['dir_after_second']),
                  restart['launch'] is not None and restart['second']['loop']
                  and restart['second']['swept'] == [restart['launch'].dispatch_id] and not restart['dir_after_second'])

        with region('fixture/control-word'):
            for engine in ('claude', 'codex'):
                _header, lines = runs[engine]['header_lines']
                check('fixture/control-word', engine + ': a low-entropy word no credential names is kept as printed',
                      bool(lines) and control_word in '\n'.join(x.get('payload', '') for x in lines))

        with region('format/fake-lines'):
            events = FORMATS['claude_code']['events']
            extra_events = STREAM['claude_code']['events']
            bad, printed = [], 0
            for own in (claude['own'], refused['none-needed']['own']):
                for line in (own.get('lines') or {}).get('engine') or []:
                    event = json.loads(line)
                    printed += 1
                    kind = event.get('type')
                    key = {'system': 'system/init', 'result': 'result/success'}.get(kind, kind)
                    if kind == 'control_response':
                        continue
                    table = ((events.get(key) or extra_events.get(key)) or {}).get('fields') or {}
                    required = {f for f, v in table.items() if not v.get('optional')}
                    if not table or set(event) - set(table) or required - set(event):
                        bad.append((key, sorted(set(event) - set(table)), sorted(required - set(event))))
            codex_events = FORMATS['codex']['events']
            kinds = dict(CODEX_ITEMS['items'], **FORMATS['codex']['items'])
            for own in (codex['own'], other_own):
                for line in (own.get('lines') or {}).get('engine') or []:
                    event = json.loads(line)
                    printed += 1
                    table = (codex_events.get(event.get('type')) or {}).get('fields') or {}
                    if not table or set(event) - set(table):
                        bad.append((event.get('type'), sorted(set(event) - set(table))))
                    item = event.get('item')
                    if isinstance(item, dict):
                        fields = ((kinds.get(item.get('type')) or {}).get('fields')) or {}
                        if not fields or set(item) - set(fields):
                            bad.append(('item/' + str(item.get('type')), sorted(set(item) - set(fields))))
            check('format/fake-lines', 'every event line the fakes printed is one of the binaries\' own schemas with its '
                  'required fields [%d lines, %s]' % (printed, bad[:3]), printed >= 20 and not bad)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        fake_capture = conform_formats.conform_fake(locals(), '0158_credential_delivery')
        if saved_path is None:
            os.environ.pop('PATH', None)
        else:
            os.environ['PATH'] = saved_path
        for close in reversed(closers):
            with contextlib.suppress(Exception):
                close()
        with contextlib.suppress(Exception):
            subprocess.run(['systemctl', '--user', 'stop', slice_name], capture_output=True, timeout=20, env=tools,
                           stdin=subprocess.DEVNULL)
        with contextlib.suppress(Exception):
            mine = sorted({CT.unit_name(launch.dispatch_id) for launch in contained})
            listed = subprocess.run(['systemctl', '--user', 'list-units', '--all', '--plain', '--no-legend', *mine],
                                    capture_output=True, text=True, timeout=20, env=tools, stdin=subprocess.DEVNULL)
            loaded = [line.split()[0] for line in listed.stdout.splitlines() if line.split()]
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
                    print('  VELDO-0158 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0158 %s detail: no check ran' % name)
        expect('VELDO-0158 ' + name, ok)
    for line in conform_formats.describe('0158_credential_delivery', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0158_credential_delivery', bool(fake_capture[1]) and not fake_capture[0])
    print('VELDO-0158 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session: the receiver, its systemd tools and this suite's own systemctl reach the user manager
# through /run/user/<uid> for this run when the gate's environment names none.
_v158_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v158_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v158_suite()
finally:
    if _v158_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v158_session
