"""VELDO-0141: every worker run's full live execution record, redacted before it is kept, served to the UI's live
terminal view through the authenticated API.

Run: python3 scripts/selftest.py --suite 82_veldo_0141_execution_record

Only shared ROOT and expect are consumed. One temporary tree in the owner's runtime directory holds the installed
.veldo copy the suite loads AND the launch receiver, wrapper and clone entrance execute, so a registered mutation of
a production module reaches all of them. Real: a SQLite control store with OpenSSH journal signatures, memberships
enrolled through VELDO-0025's signed commands (the owner's bootstrap and a member of another project; the runner and
the launch receiver hold the reservation service role as VELDO-0062's suites write it), the owner's account records over profiles the local helper prepares, VELDO-0036 reservations,
VELDO-0052's Gate, VELDO-0031 claims, a Git source bound to the store, VELDO-0042 clones confined with Landlock, the
VELDO-0039 Runner and receiver processes, the trusted wrapper and VELDO-0040 transient scopes under the owner's
systemd user manager in a slice of the run's own, and the VELDO-0130 API: passkeys registered and signed in through
its own ceremonies (an openssl key assembles each WebAuthn result) and enrolled by the steward's signed command, its
ApiAuthority holding the authority's lock, its hint socket (control_client_api.Hints) receiving the launch
receiver's record hints, its event-stream writer, and its service-socket call carried by control_service_api.

The engines are fakes: a `claude` pinned as 2.1.281 and qualified with the module's baseline, and a Codex laid out as
the vendor package and qualified by the production writer. Each prints only lines of the binaries' own tables
(proof/VELDO-0062/cli-formats.json; proof/VELDO-0141/stream-formats.json for the user and stream_event messages, each
engine's error-stream line and Codex's login status line), really runs its unit's commands and edits its file in the
clone, and keeps its own copy of every line it printed on each stream, which the record is compared with. The Claude
Code fake prints partial messages only with --include-partial-messages and a subagent's text only with
--forward-subagent-text, as the binary does. The planted resolver of AC4 is a function the receiver process adds to
control_launch.RESOLVERS before it runs (a driver that loads the installed module and calls its main). The fake's
handshake answer names an email and an organization as the binary's does; the path and URL rows judge the live
run's own init and tool lines and typical real paths through the production redact. No real engine
runs, nothing logs in and no credential exists (every value is assembled at run time). Each row is reported once.
"""


def _v141_suite():
    import contextlib
    import fcntl
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import queue
    import random
    import re
    import secrets
    import shutil
    import string
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import uuid
    from unittest import mock

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    FORMATS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())
    STREAM = json.loads((TREE / 'proof' / 'VELDO-0141' / 'stream-formats.json').read_text())
    OPTIONS = json.loads((TREE / 'proof' / 'VELDO-0060' / 'cli-options.json').read_text())['claude_code']
    SWITCHES = json.loads((TREE / 'proof' / 'VELDO-0155' / 'claude-baseline.json').read_text())['switches']
    CODEX_ITEMS = json.loads((TREE / 'proof' / 'VELDO-0061' / 'codex-exec.json').read_text())['item']
    VERSION = '2.1.281'

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_execution_record.py': ROOT / ".veldo" / "control_execution_record.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_client_api.py': ROOT / ".veldo" / "control_client_api.py",
        'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
    }
    ROWS = ('record/claude-complete', 'record/codex-complete', 'record/stream-options',
            'api/live', 'api/cursor', 'api/refusals', 'api/no-secret-served', 'api/service-call',
            'route/served-lines', 'route/committed',
            'redaction/planted-value', 'redaction/known-pattern', 'redaction/kinds-field', 'redaction/exact-set',
            'redaction/paths-kept', 'redaction/path-segment', 'redaction/url-component', 'redaction/account-fields',
            'fixture/planted-control', 'format/fake-lines',
            'redaction/partial-blocks', 'redaction/clone-relative-paths', 'redaction/encoded-values',
            'api/scope-before-existence', 'api/registration-race', 'api/slow-reader', 'route/unknown-committed',
            'redaction/thinking-and-unknown', 'redaction/live-paths', 'redaction/offset-encodings',
            'redaction/clone-leaf-candidates', 'redaction/uppercase-hex', 'redaction/clone-without-git',
            'api/byte-pages', 'api/fast-catchup', 'route/runner-unknown')
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

    started = time.monotonic()
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v141-', dir=runtime if os.path.isdir(runtime) else None))
    slice_name = 'v141%s.slice' % os.urandom(4).hex()
    tools = dict(os.environ)
    contained, connections, closers = [], [], []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v141_store', mods / 'control_store.py')
        L = load('v141_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        E = L.ENGINES['claude_code']
        X = L.ENGINES['codex']
        ER, _ = attempt(lambda: load('v141_record', mods / 'control_execution_record.py'))
        SS = load('v141_scan', mods / 'secret_scan.py')
        HELPER = load('v141_helper', mods / 'accounts.py')
        EL = load('v141_eligibility', mods / 'control_eligibility.py')
        SIG = load('v141_signer', mods / 'control_signer.py')
        GP = load('v141_git', mods / 'git_process.py')
        CL = load('v141_clone', mods / 'control_clone.py')
        CT = load('v141_containment', mods / 'control_containment.py')
        CM = load('v141_membership', mods / 'control_membership.py')
        AC = load('v141_contract', mods / 'authority_contract.py')
        API = load('v141_api', mods / 'control_api.py')
        AUTH = load('v141_authority', mods / 'control_api_authority.py')
        CAm = load('v141_client_api', mods / 'control_client_api.py')
        SAPI = load('v141_service_api', mods / 'control_service_api.py')
        CR, IN = AUTH.CR, AUTH.AS.IN
        CLM = D.CLM
        CM.attach(S)
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-141', 'repository-141', 'builder-141', 'linux-host-141'
        PROJECT, OTHER, INTAKE = 'journey-141', 'other-141', 'intake-141'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPOSITORY, store_uuid='store-141')
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        people = base / 'people'
        people.mkdir(mode=0o700)
        public = {}
        for who in ('owner', 'outsider'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v141-' + who, '-f', str(people / who)],
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

        # Membership through VELDO-0025's signed commands: the owner's bootstrap (steward and project owner), then a
        # person of another project.
        def envelope(command, principal):
            now = CM.authority_state(S, writer)
            return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                        membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))

        def admin(principal, operation, params, enrollee=None):
            command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                       'artifact_digests': [], 'expected_versions': {}}
            env = envelope(command, principal)
            signature = sign_as(principal, AC.canonical_envelope_bytes(env))
            cosigned = (sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
                        if enrollee else None)
            return CM.admit(S, writer, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                            journal_signer=('authority', sign))
        admin('owner', 'enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                            'roles': ['membership_steward', 'project_owner'], 'public_key': public['owner'],
                                            'independence_group': 'owner', 'scope': '*'})
        admin('owner', 'enroll_principal', {'principal': 'outsider', 'principal_type': 'person', 'roles': ['project_owner'],
                                            'public_key': public['outsider'], 'independence_group': 'outsider',
                                            'scope': [OTHER]}, enrollee='outsider')
        # The runner and the launch receiver hold the reservation service role, which no membership command grants
        # (control_reservations.service_authority reads it from the member's record): written as VELDO-0062's suites do.
        for who in ('runner', 'launch-receiver'):
            put(who, 'membership', dict(principal_type='service', roles=['reservation_service'], scope=[REPOSITORY],
                                        revoked_at=None, expires_at=None))
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        # The owner's accounts: Claude Code plain, Claude Code with a subscription token, and Codex.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}
        for account, provider in (('acct-141a', 'claude_code'), ('acct-141t', 'claude_code'), ('acct-141c', 'codex')):
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider))
            profiles[account] = (record or {}).get('config_dir')
            fields, _ = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields:
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=time.time())
        if profiles.get('acct-141c'):
            (Path(profiles['acct-141c']) / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt'}))
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

        # The source: a file the unit edits.
        EDIT = {'path': 'NOTES.md', 'old': 'first draft of the notes', 'new': 'second draft of the notes'}
        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        relative_file = 'worker_sources/components/build_output/traceback_execution_record_review.py'
        (src / relative_file).parent.mkdir(parents=True)
        (src / relative_file).write_text('review file\n')
        (src / EDIT['path']).write_text('# notes\n' + EDIT['old'] + '\n')
        GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # THE FAKE CLAUDE CODE. Its lines are the binary's own shapes; it runs the unit's commands and makes its edit
        # in the clone, and keeps its own copy of each line it prints on each stream.
        markers = base / 'markers'
        markers.mkdir()
        claude_table = {'version': VERSION, 'certs': STREAM['claude_code']['stderr']['extra_certs']['text'],
                        'change': 'The file %s has been updated successfully.'}
        fake_claude = '''#!@@PYTHON@@ -B
import json, os, subprocess, sys, time, uuid
from pathlib import Path
markers, TABLE = Path(@@MARKERS@@), json.loads(@@TABLE@@)
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
pid = os.getpid()
def option(name):
    for at, arg in enumerate(argv):
        if arg == name:
            return argv[at + 1] if at + 1 < len(argv) else None
    return None
own = {'pid': pid, 'dispatch': env.get('VELDO_DISPATCH_ID', ''), 'argv': sys.argv, 'cwd': str(cwd)}
(markers / ('%d.tmp' % pid)).write_text(json.dumps(own))
(markers / ('%d.tmp' % pid)).rename(markers / ('%d.json' % pid))
out = open(markers / ('%d.out' % pid), 'w')
err = open(markers / ('%d.err' % pid), 'w')
pace = [0.05]
def emit(event):
    text = json.dumps(event)
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
    time.sleep(pace[0])
def warn(text):
    err.write(text + chr(10))
    err.flush()
    sys.stderr.write(text + chr(10))
    sys.stderr.flush()
# The binary's own warning on its error stream when NODE_EXTRA_CA_CERTS names a file it cannot load.
certs = env.get('NODE_EXTRA_CA_CERTS')
if certs and not os.path.exists(certs):
    warn(TABLE['certs'].replace('{path}', certs))
packet = None
if option('--input-format') == 'stream-json':
    while packet is None:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get('type') == 'control_request' and (message.get('request') or {}).get('subtype') == 'initialize':
            account = {'apiProvider': 'firstParty', 'email': 'owner.%s@example.invalid' % uuid.uuid4().hex[:8],
                       'organization': str(uuid.uuid4())}
            if env.get('CLAUDE_CODE_OAUTH_TOKEN'):
                account['tokenSource'] = 'CLAUDE_CODE_OAUTH_TOKEN'
            else:
                account['subscriptionType'] = 'Claude Max'
            emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                                                           'response': {'account': account, 'pid': pid}}})
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            packet = json.loads(content) if content.strip() else {}
if packet is None:
    out.close()
    sys.exit(0)
payload = packet.get('payload') or {}
pace[0] = float(payload.get('pace', 0.05))
values = {'planted': env.get('V141_PLANTED', ''), 'token': env.get('CLAUDE_CODE_OAUTH_TOKEN', ''),
          'high': payload.get('high', ''), 'pattern': payload.get('pattern', ''), 'control': payload.get('control', '')}
def fill(text):
    for name, value in values.items():
        text = text.replace('{' + name + '}', value)
    return text
partial, forward = '--include-partial-messages' in argv, '--forward-subagent-text' in argv
session = str(uuid.uuid4())
usage = {'input_tokens': 3, 'output_tokens': 2, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
emit({'type': 'system', 'subtype': 'init', 'cwd': str(cwd), 'session_id': session, 'tools': ['Bash', 'Edit', 'Task'],
      'mcp_servers': [], 'model': 'configured-model', 'permissionMode': 'default', 'slash_commands': [],
      'apiKeySource': 'none', 'claude_code_version': TABLE['version'], 'output_style': 'default', 'agents': [],
      'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4())})
def assistant(content, parent=None):
    emit({'type': 'assistant', 'parent_tool_use_id': parent, 'uuid': str(uuid.uuid4()), 'session_id': session,
          'message': {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant',
                      'model': 'configured-model', 'content': content, 'stop_reason': None, 'stop_sequence': None,
                      'usage': usage}})
def partial_text(text, parent=None):
    if partial:
        emit({'type': 'stream_event', 'event': {'type': 'content_block_delta', 'index': 0,
                                                'delta': {'type': 'text_delta', 'text': text}},
              'parent_tool_use_id': parent, 'uuid': str(uuid.uuid4()), 'session_id': session})
def result_of(tool, text, is_error, structured, parent=None):
    emit({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool,
                                                                    'content': text, 'is_error': is_error}]},
          'parent_tool_use_id': parent, 'tool_use_result': structured})
def bash(command, parent=None):
    tool = 'toolu_' + uuid.uuid4().hex[:20]
    assistant([{'type': 'tool_use', 'id': tool, 'name': 'Bash', 'input': {'command': command}}], parent)
    done = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True, cwd=str(cwd), env=dict(env))
    text = (done.stdout + done.stderr).rstrip(chr(10))
    if done.returncode:
        text = 'Exit code %d' % done.returncode + chr(10) + text
    result_of(tool, text, bool(done.returncode), {'stdout': done.stdout, 'stderr': done.stderr, 'interrupted': False,
                                                  'isImage': False}, parent)
for text in payload.get('warn') or []:
    warn(fill(text))
partial_text('Working the unit.')
assistant([{'type': 'text', 'text': 'Working the unit.'}])
if payload.get('command'):
    bash(payload['command'])
if payload.get('failing'):
    bash(payload['failing'])
edit = payload.get('edit')
if edit:
    tool = 'toolu_' + uuid.uuid4().hex[:20]
    path = cwd / edit['path']
    assistant([{'type': 'tool_use', 'id': tool, 'name': 'Edit', 'input': {'file_path': str(path),
                                                                         'old_string': edit['old'],
                                                                         'new_string': edit['new']}}])
    path.write_text(path.read_text().replace(edit['old'], edit['new']))
    (markers / ('%d.edited' % pid)).write_text(path.read_text())
    result_of(tool, TABLE['change'] % path, False, {'filePath': str(path), 'oldString': edit['old'],
                                                    'newString': edit['new']})
if payload.get('subagent'):
    task = 'toolu_' + uuid.uuid4().hex[:20]
    assistant([{'type': 'tool_use', 'id': task, 'name': 'Task', 'input': {'description': 'a subagent',
                                                                         'prompt': 'check the notes',
                                                                         'subagent_type': 'general-purpose'}}])
    if forward:
        partial_text(payload['subagent'], task)
        assistant([{'type': 'text', 'text': payload['subagent']}], task)
    result_of(task, 'the subagent is done', False, {'status': 'completed'})
for text in payload.get('say') or []:
    assistant([{'type': 'text', 'text': fill(text)}])
emit({'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False, 'num_turns': 1,
      'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0, 'usage': usage,
      'modelUsage': {'configured-model': {'inputTokens': 3, 'outputTokens': 2, 'cacheReadInputTokens': 0,
                                          'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                          'contextWindow': 200000, 'maxOutputTokens': 32000}},
      'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session})
out.close()
err.close()
'''.replace('@@PYTHON@@', sys.executable).replace('@@MARKERS@@', repr(str(markers))).replace(
            '@@TABLE@@', repr(json.dumps(claude_table)))
        versions = base / 'home' / '.local' / 'share' / 'claude' / 'versions'
        versions.mkdir(parents=True)
        (versions / VERSION).write_text(fake_claude)
        (versions / VERSION).chmod(0o755)
        FLAGS = ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json']
        test_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {
            VERSION: {'sha256': file_sha(versions / VERSION), 'flags': list(FLAGS),
                      'environment': {'DISABLE_AUTOUPDATER': '1'}, 'baseline': getattr(E, 'BASELINE', None)}}}
        (mods / 'runtime').mkdir(exist_ok=True)
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps(test_record, indent=1))
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        pinned = factory / 'engines' / 'claude_code' / VERSION
        attempt(lambda: E.pin(VERSION, versions=str(versions), state_root=str(factory)))

        # THE FAKE CODEX, laid out as the vendor package: exec --json lines of the binary's table.
        codex_table = {'prompt': STREAM['codex']['stderr']['prompt_from_stdin']['text'],
                       'logged_in': STREAM['codex']['login_status']['chatgpt'],
                       'change_kind': 'update' if 'update' in CODEX_ITEMS['change_kinds'] else None}
        fake_codex = '''#!@@PYTHON@@ -B
import json, os, subprocess, sys, time
from pathlib import Path
markers, TABLE = Path(@@MARKERS@@), json.loads(@@TABLE@@)
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
home = Path(env.get('CODEX_HOME') or '/nonexistent')
def login():
    try:
        return json.loads((home / 'auth.json').read_text()).get('auth_mode')
    except (OSError, ValueError):
        return None
if argv[:2] == ['login', 'status']:
    if login() == 'chatgpt':
        print(TABLE['logged_in'])
        sys.exit(0)
    sys.exit(1)
pid = os.getpid()
own = {'pid': pid, 'dispatch': env.get('VELDO_DISPATCH_ID', ''), 'argv': sys.argv, 'cwd': str(cwd)}
(markers / ('%d.tmp' % pid)).write_text(json.dumps(own))
(markers / ('%d.tmp' % pid)).rename(markers / ('%d.json' % pid))
out = open(markers / ('%d.out' % pid), 'w')
err = open(markers / ('%d.err' % pid), 'w')
def emit(event):
    text = json.dumps(event)
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
    time.sleep(0.05)
# exec reads its prompt from standard input when none is given, and says so on its error stream.
err.write(TABLE['prompt'] + chr(10))
err.flush()
sys.stderr.write(TABLE['prompt'] + chr(10))
sys.stderr.flush()
packet = json.loads(sys.stdin.buffer.read() or b'{}')
payload = packet.get('payload') or {}
emit({'type': 'thread.started', 'thread_id': 'thread-141-%d' % pid})
emit({'type': 'turn.started'})
number = [0]
def item(kind, **fields):
    number[0] += 1
    return dict(fields, id='item_%d' % number[0], type=kind)
for command in [c for c in (payload.get('command'), payload.get('failing')) if c]:
    started = item('command_execution', aggregated_output='', status='in_progress')
    emit({'type': 'item.started', 'item': started})
    done = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True, cwd=str(cwd), env=dict(env))
    emit({'type': 'item.completed', 'item': dict(started, aggregated_output=done.stdout + done.stderr,
                                                 exit_code=done.returncode,
                                                 status='completed' if done.returncode == 0 else 'failed')})
edit = payload.get('edit')
if edit:
    path = cwd / edit['path']
    path.write_text(path.read_text().replace(edit['old'], edit['new']))
    emit({'type': 'item.completed', 'item': item('file_change', changes=[{'path': str(path), 'kind': TABLE['change_kind']}],
                                                  status='completed')})
if payload.get('error'):
    emit({'type': 'item.completed', 'item': item('error', message=payload['error'])})
emit({'type': 'item.completed', 'item': item('agent_message')})
emit({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0, 'output_tokens': 2,
                                          'reasoning_output_tokens': 0}})
out.close()
err.close()
'''.replace('@@PYTHON@@', sys.executable).replace('@@MARKERS@@', repr(str(markers))).replace(
            '@@TABLE@@', repr(json.dumps(codex_table)))
        package = base / 'packages' / 'codex'
        CODEX_BIN = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        CODEX_BIN.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        CODEX_BIN.write_text(fake_codex)
        CODEX_BIN.chmod(0o755)
        codex_record_path = base / 'codex-qualification.json'
        codex_record, _ = attempt(lambda: X.qualification(str(CODEX_BIN)))
        codex_record_path.write_text(json.dumps(codex_record or {}))

        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4, 'systemd_run': real_systemd_run}
        # The token of acct-141t, a file of this account's own nobody else reads; assembled at run time.
        token_value = 'v141-subscription-' + os.urandom(8).hex()
        tokens = state / 'tokens'
        tokens.mkdir(mode=0o700)
        (tokens / 'acct-141t').write_text(token_value + '\n')
        (tokens / 'acct-141t').chmod(0o600)
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '--']
        api_state = base / 'api-state'
        hints_path = api_state / 'hints.sock'
        records_dir = factory / 'records'
        missing_certs = str(base / 'no-such-extra-certs.pem')
        config = base / 'receiver.json'
        receiver_config = {
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(state / 'receipts'), 'artifacts': str(state / 'artifacts'),
            'state_root': str(factory), 'profile': profile, 'record_hints': [str(hints_path)],
            'subscription_tokens': {'acct-141t': str(tokens / 'acct-141t')},
            'adapters': {'claude': {'engine': 'claude_code', 'executable': {'version': VERSION}, 'argv': entering,
                                    'environment': {'NODE_EXTRA_CA_CERTS': missing_certs}},
                         'codex': {'engine': 'codex', 'executable': str(CODEX_BIN), 'qualification': str(codex_record_path),
                                   'argv': entering + [str(CODEX_BIN)] + list(getattr(X, 'FLAGS', ()) or ())}}}
        config.write_text(json.dumps(receiver_config))
        RECEIVER_ENV = dict(os.environ)
        RECEIVER_ENV['DBUS_SESSION_BUS_ADDRESS'] = (os.environ.get('DBUS_SESSION_BUS_ADDRESS')
                                                    or 'unix:path=%s/bus' % runtime)

        # THE PLANTED RESOLVER (AC4): the receiver process adds it to control_launch.RESOLVERS, then runs as ever.
        # Its value has no known pattern and low entropy; it reaches the engine as V141_PLANTED.
        pick = random.SystemRandom()
        while True:
            planted = '.'.join(w + ''.join(pick.choice('bcdfghjkmnpqrstvwxz') for _ in range(3))
                               for w in ('amber', 'harbor', 'lantern'))
            if SS.shannon(planted) < SS.ENTROPY_THRESHOLD and not SS.scan_text(planted):
                break
        while True:
            high = secrets.token_urlsafe(30).replace('-', 'x').replace('_', 'y')
            if not any(rx.search(high) for rx, _ in SS.PATTERNS) and SS.shannon(high) >= SS.ENTROPY_THRESHOLD:
                break
        pattern_token = 'gh' + 'p_' + ''.join(pick.choice(string.ascii_letters + string.digits) for _ in range(36))
        control_word = 'plain.control.' + ''.join(pick.choice('bcdfghjkm') for _ in range(4))
        planted_file = base / 'planted-value'
        planted_file.write_text(planted)
        planted_file.chmod(0o600)
        PLANTED_KIND = 'v141_planted'
        driver = base / 'planted_receiver.py'
        driver.write_text(
            'import importlib.util, sys\n'
            'spec = importlib.util.spec_from_file_location("control_launch", %r)\n'
            'L = importlib.util.module_from_spec(spec)\n'
            'spec.loader.exec_module(L)\n'
            'VALUE = open(%r).read()\n'
            'def planted(receiver, contract, adapter, environment):\n'
            '    environment["V141_PLANTED"] = VALUE\n'
            '    return [(%r, VALUE)]\n'
            'getattr(L, "RESOLVERS", []).append(planted)\n'
            'L.main()\n' % (str(mods / 'control_launch.py'), str(planted_file), PLANTED_KIND))

        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        clones = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)],
                           engines=[str(factory / 'engines'), str(base / 'packages')])
        mode = {'planted': False}

        def invoke(contract):
            clones.create(contract)
            if not mode['planted']:
                launch = L.invoke(config, contract, dispatches, accept_seconds=30, environment=RECEIVER_ENV)
            else:
                child = subprocess.Popen([sys.executable, '-B', str(driver), str(config)], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=RECEIVER_ENV)
                child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
                child.stdin.flush()
                launch = L.Launch(child, contract, dispatches, time.time).start(30)
            contained.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]

        # THE API: the authority's judge on this store (holding its lock), the ControlApi over it, and its hint socket.
        HOST_NAME = 'veldo-141.example.invalid'
        ORIGIN = 'https://' + HOST_NAME
        lock_held = os.open(str(db.parent / 'authority.lock'), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock_held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        closers.append(lambda: os.close(lock_held))
        credentials = CR.Credentials(S, writer, ids, 'authority', sign, rp_id=HOST_NAME, origin=ORIGIN,
                                     state_dir=base / 'credential-state')
        intake = IN.Intake(S, CM, AC, None, writer, domain=INTAKE, projects=(PROJECT, OTHER), api_edge='api-edge',
                           journal_signer='authority', sign=sign)
        extra = {'records': str(records_dir)} if 'records' in AUTH.ApiAuthority.__init__.__code__.co_varnames else {}
        authority = AUTH.ApiAuthority(S, CM, writer, ids=ids, domain=INTAKE, edge='api-edge', intake=intake,
                                      settlement=None, credentials=credentials, authority_lock=lock_held, **extra)
        api = API.ControlApi({'origin': ORIGIN, 'rp_id': HOST_NAME, 'host': HOST_NAME, 'domain': INTAKE, 'ids': ids,
                              'edge': 'api-edge', 'state_dir': str(api_state)}, authority, None)
        hinted = queue.Queue()
        hints = CAm.Hints(hints_path, lambda hint: (hinted.put(hint), {'queued': True})[1])
        closers.append(hints.close)
        COOKIE = '__Host-veldo-session'
        RECORD = '/api/v1/domains/%s/runs/record' % INTAKE
        STREAM_PATH = '/api/v1/domains/%s/runs/record/stream' % INTAKE

        def call(method, path, body=None, cookie=None, token=None, extra=None):
            headers = dict(extra or {}, Host=HOST_NAME)
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

        def refusal(result):
            return result[2].get('refusal') if isinstance(result[2], dict) else None

        def b64(data):
            import base64
            return base64.urlsafe_b64encode(data).decode().rstrip('=')

        class Passkey:
            """An openssl P-256 key and the WebAuthn results a browser assembles with it."""

            def __init__(self, name):
                self.key = people / (name + '.pem')
                subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out',
                                str(self.key)], check=True, capture_output=True, timeout=10)
                self.der = subprocess.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'],
                                          check=True, capture_output=True, timeout=10).stdout
                self.credential_id, self.user_handle = b64(os.urandom(32)), None

            def client(self, kind, challenge):
                return json.dumps({'type': kind, 'challenge': challenge, 'origin': ORIGIN, 'crossOrigin': False},
                                  separators=(',', ':')).encode()

            def get(self, challenge):
                client = self.client('webauthn.get', challenge)
                auth = hashlib.sha256(HOST_NAME.encode()).digest() + bytes([0x05]) + b'\x00\x00\x00\x00'
                signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)],
                                           input=auth + hashlib.sha256(client).digest(), check=True,
                                           capture_output=True, timeout=10).stdout
                return {'credential_id': self.credential_id, 'client_data_json': b64(client),
                        'authenticator_data': b64(auth), 'signature': b64(signature), 'user_handle': self.user_handle}

        def enroll_passkey(principal):
            """Register over the API's ceremonies, then the steward's signed enroll_api_credential."""
            key = Passkey(principal)
            begun = call('POST', '/api/v1/auth/registration/begin', {'label': principal})
            key.user_handle = begun[2]['user_handle']
            offered = call('POST', '/api/v1/auth/registration/credential', {
                'registration_id': begun[2]['registration_id'], 'credential_id': key.credential_id,
                'public_key': b64(key.der), 'algorithm': -7,
                'client_data_json': b64(key.client('webauthn.create', begun[2]['challenge']))})
            proof = key.get(offered[2]['possession_challenge'])
            call('POST', '/api/v1/auth/registration/possession',
                 dict({k: v for k, v in proof.items() if k != 'credential_id'}, registration_id=begun[2]['registration_id']))
            pending = json.loads((api_state / 'pending' / (begun[2]['registration_id'] + '.json')).read_text())
            command = CR.enrollment_command(pending, principal, next_id('credential'))
            env = envelope(command, 'owner')
            credentials.admit(env, command, sign_as('owner', AC.canonical_envelope_bytes(env)))
            return key

        def sign_in(key):
            issued = call('POST', '/api/v1/auth/challenge', {})
            done = call('POST', '/api/v1/auth/sign-in', key.get(issued[2]['challenge']))
            text = done[1].get('Set-Cookie') or ''
            name, _, value = text.split(';')[0].partition('=')
            return (value if name == COOKIE else None), (done[2] or {}).get('csrf_token')
        owner_key, outsider_key = enroll_passkey('owner'), enroll_passkey('outsider')
        owner_cookie, owner_token = sign_in(owner_key)
        outsider_cookie, _ = sign_in(outsider_key)

        def consume(stream, into):
            """A browser reading one event stream: the API's own writer, each write timestamped."""
            def write(data):
                into.append((time.time(), data))
            thread = threading.Thread(target=API.serve_stream, args=(stream, write, 5), daemon=True)
            thread.start()
            return thread

        def frames_of(writes):
            """The SSE frames written: (arrival time, id, event, data)."""
            found = []
            for at, data in writes:
                for block in data.decode().split('\n\n'):
                    fields = dict(line.split(': ', 1) for line in block.split('\n') if ': ' in line and not line.startswith(':'))
                    if 'data' in fields:
                        found.append((at, fields.get('id'), fields.get('event'), json.loads(fields['data'])))
            return found

        def serve_hints(until):
            """Deliver the record hints the receiver sends, on this thread (the store's), until `until()` holds; then
            until none has come for a while."""
            delivered = []
            quiet, bound = None, time.monotonic() + 90
            while time.monotonic() < bound:
                try:
                    hint = hinted.get(timeout=0.05)
                except queue.Empty:
                    hint = None
                if hint is not None:
                    delivered.append((hint, api.deliver(hint)))
                    quiet = None
                elif until():
                    quiet = quiet or time.monotonic()
                    if time.monotonic() - quiet > 1.2:
                        return delivered
            return delivered

        units = []

        def live_run(account, adapter, payload, while_running=None, planted_run=False):
            """Submit, act while the worker runs (open a stream), deliver hints as they come, then wait."""
            units.append(len(units) + 1)
            unit = admitted('VELDO-141%02d' % units[-1])
            mode['planted'] = planted_run
            try:
                launch = runner(account).submit(unit, 'build', holder=HOLDER, source=str(src), revision='HEAD',
                                                payload=payload, adapter=adapter,
                                                configuration={'tools': ['Bash', 'Edit'], 'model': 'configured-model'},
                                                deadline=time.time() + 60)
            finally:
                mode['planted'] = False
            opened = while_running(launch) if while_running else None
            delivered = serve_hints(lambda: launch.child is None or launch.child.poll() is not None)
            record = runner(account).wait(launch) or {}
            delivered += serve_hints(lambda: True)
            return launch, record, opened, delivered

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

        def kept(dispatch_id):
            """(header, lines) of the kept record file, read here."""
            if ER is None:
                return None, []
            path = Path(ER.path(str(records_dir), dispatch_id))
            if not path.is_file():
                return None, []
            raw = path.read_bytes().split(b'\n')[:-1]
            return json.loads(raw[0]), [json.loads(x) for x in raw[1:]]

        MARK = re.compile(r'\[REDACTED:([^\]]+)\]')

        def _pattern(rx):
            source = rx.pattern
            return '(?i:%s)' % source[4:] if source.startswith('(?i)') else '(?:%s)' % source

        def same(payload, emitted, resolved=None):
            """Whether a kept payload is the emitted line with only redacted spans replaced, each span what its marker
            names: a value of `resolved` ({kind: value}) in a form a line carries it, a match of one of the scanner's
            patterns, or a high-entropy span of its candidate shape (never a hex digest's)."""
            resolved = resolved or {}
            if not isinstance(payload, str):
                return False
            if '[REDACTED:' not in payload:
                return payload == emitted
            parts, shape, kinds = MARK.split(payload), '^', []
            for at, part in enumerate(parts):
                if at % 2 == 0:
                    shape += re.escape(part)
                    continue
                kinds.append(part)
                if part in resolved:
                    value = resolved[part]
                    forms = {value, json.dumps(value)[1:-1], json.dumps(value, ensure_ascii=False)[1:-1]}
                    shape += '(' + '|'.join(re.escape(f) for f in sorted(forms, key=len, reverse=True)) + ')'
                elif part.startswith('pattern:'):
                    shape += '(' + '|'.join(_pattern(rx) for rx, _ in SS.PATTERNS) + ')'
                elif part == 'entropy':
                    shape += '(' + SS._CANDIDATE.pattern + ')'
                elif part.startswith('account:'):
                    shape += r'((?:[^"\\]|\\.)*)'
                else:
                    return False
            found = re.match(shape + '$', emitted, re.DOTALL)
            return bool(found) and all(kind != 'entropy' or (not SS._is_digest(gap) and SS.shannon(gap) >= SS.ENTROPY_THRESHOLD)
                                       for kind, gap in zip(kinds, found.groups()))

        def judge(dispatch_id, own, resolved=None):
            """The complete-record check: every line the engine printed on each stream, in order, the wrapper's
            identity line first, gapless sequences in the receiver's time order; [] when it holds, else what not."""
            header, lines = kept(dispatch_id)
            problems = []
            if header is None or header.get('dispatch_id') != dispatch_id:
                problems.append('no record bound to the dispatch')
            if [x.get('seq') for x in lines] != list(range(1, len(lines) + 1)):
                problems.append('sequences not gapless')
            at = [x.get('at') for x in lines]
            if not all(isinstance(t, (int, float)) for t in at) or at != sorted(at):
                problems.append('receive times not in order')
            for stream in ('engine', 'stderr'):
                got = [x.get('payload') for x in lines if x.get('stream') == stream]
                wanted = (own.get('lines') or {}).get(stream) or []
                if len(got) != len(wanted) or not wanted:
                    problems.append('%s: %d kept of %d printed' % (stream, len(got), len(wanted)))
                elif not all(same(g, w, resolved) for g, w in zip(got, wanted)):
                    problems.append('%s: a kept line is not the printed one' % stream)
            wrapper = [x for x in lines if x.get('stream') == 'wrapper']
            identity = json.loads(wrapper[0]['payload']) if len(wrapper) == 1 else {}
            if not lines or lines[0].get('stream') != 'wrapper' or (identity.get('process') or {}).get('pid') != own.get('pid'):
                problems.append('the wrapper identity line is not the first, naming the engine')
            if set(x.get('stream') for x in lines) - {'engine', 'stderr', 'wrapper'}:
                problems.append('a line of another stream')
            return problems

        def events_of(dispatch_id):
            return [json.loads(x['payload']) for x in kept(dispatch_id)[1] if x.get('stream') == 'engine'
                    and x.get('payload', '').startswith('{')]

        def page(dispatch_id, after, cookie=None):
            return call('GET', RECORD + '?dispatch=%s&after=%d' % (dispatch_id, after), cookie=cookie or owner_cookie)

        def all_pages(dispatch_id, after=0):
            served, answers = [], []
            while True:
                got = page(dispatch_id, after)
                answers.append(got)
                lines = (got[2] or {}).get('lines') if isinstance(got[2], dict) else None
                if got[0] != 200 or not lines:
                    return served, answers
                served += lines
                after = lines[-1]['seq']

        # THE RUNS. The Claude Code run followed live from the first cursor by the owner's stream.
        main_writes = []
        CLAUDE_PAYLOAD = {'task': 'work the unit', 'pace': 0.12,
                          'command': "printf 'v141 command output\\n'; printf 'v141 command error\\n' >&2",
                          'failing': "printf 'v141 failing error\\n' >&2; exit 3",
                          'edit': dict(EDIT), 'subagent': 'v141 subagent text', 'say': ['v141 done', relative_file]}

        ended = {'writes': []}

        def follow_from_start(launch):
            opened = call('GET', STREAM_PATH + '?dispatch=%s&after=0' % launch.dispatch_id, cookie=owner_cookie)
            thread = consume(opened[2], main_writes) if isinstance(opened[2], API.Stream) else None
            # An ended session: a second session of the owner follows the same live record, then signs out.
            cookie, token = sign_in(owner_key)
            followed = call('GET', STREAM_PATH + '?dispatch=%s&after=0' % launch.dispatch_id, cookie=cookie)
            if isinstance(followed[2], API.Stream):
                ended['thread'] = consume(followed[2], ended['writes'])
            ended['followed'] = followed
            ended['signed_out'] = call('POST', '/api/v1/auth/sign-out', {}, cookie=cookie, token=token)
            ended['after'] = page(launch.dispatch_id, 0, cookie=cookie)
            return opened, thread
        main_launch, main_record, main_opened, main_hints = live_run('acct-141a', 'claude', CLAUDE_PAYLOAD,
                                                                     follow_from_start)
        main_own = own_of(main_launch.dispatch_id)
        if main_opened and main_opened[1] is not None:
            main_opened[1].join(10)
        codex_launch, codex_record, _, _ = live_run('acct-141c', 'codex', {
            'task': 'work the unit', 'command': "printf 'v141 codex output\\n'; printf 'v141 codex error\\n' >&2",
            'failing': "printf 'v141 codex failing\\n' >&2; exit 2", 'edit': dict(EDIT), 'error': 'v141 codex error item'})
        codex_own = own_of(codex_launch.dispatch_id)
        # The AC4 run: the planted resolver's value, the account's subscription token, a known-pattern token and a
        # low-entropy word no resolver names, printed in the command's output, the error stream and the messages.
        planted_payload = {
            'task': 'work the unit', 'pace': 0.03, 'high': high, 'pattern': pattern_token, 'control': control_word,
            'command': ("printf '%s\\n' \"$V141_PLANTED\"; printf 'held %s in output\\n' \"$V141_PLANTED\"; "
                        "printf '%s\\n' \"$V141_PLANTED\" >&2"),
            'warn': ['{planted}', 'stderr joined {high}{planted}', 'token {token}', 'pattern {pattern}', 'control {control}'],
            'say': ['{planted}', 'joined {high}{planted}', 'pattern {pattern}', 'control {control}']}
        planted_launch, planted_record, _, _ = live_run('acct-141t', 'claude', planted_payload, planted_run=True)
        planted_own = own_of(planted_launch.dispatch_id)
        planted_header, planted_lines = kept(planted_launch.dispatch_id)
        planted_summary = next((m.get('record') for m in planted_launch.messages or []
                                if isinstance(m, dict) and m.get('event') in ('exited', 'unknown')), None) or {}

        # AC1: the complete record of each engine's run.
        with region('record/claude-complete'):
            problems = judge(main_launch.dispatch_id, main_own)
            header, lines = kept(main_launch.dispatch_id)
            check('record/claude-complete', 'every line the Claude Code worker printed on its output and its error stream '
                  'was kept, in order, after the wrapper\'s identity line, with gapless sequences and receive times [%s, %d '
                  'lines, %d printed]' % (problems, len(lines), sum(len(v) for v in (main_own.get('lines') or {}).values())),
                  main_record.get('state') == 'exited' and not problems)
            events = events_of(main_launch.dispatch_id)
            blocks = [b for e in events if e.get('type') in ('assistant', 'user')
                      for b in ((e.get('message') or {}).get('content') or []) if isinstance(b, dict)]
            uses = {b.get('name'): b.get('input') for b in blocks if b.get('type') == 'tool_use'}
            results = [b for b in blocks if b.get('type') == 'tool_result']
            text = json.dumps(events)
            check('record/claude-complete', 'the record holds every tool call with its input (the command, the failing '
                  'command, the edit, the subagent), each result with the command\'s output and its error stream, the '
                  'failed command as an error, and the edit made in the clone [%s, %d results]' % (sorted(uses), len(results)),
                  set(uses) == {'Bash', 'Edit', 'Task'} and (uses.get('Edit') or {}).get('new_string') == EDIT['new']
                  and len(results) == 4 and any(r.get('is_error') is True for r in results)
                  and 'v141 command output' in text and 'v141 command error' in text and 'v141 failing error' in text
                  and (main_own.get('lines') or {}).get('stderr')
                  and [x['payload'] for x in lines if x['stream'] == 'stderr'] and all(
                      same(k, w) for k, w in zip([x['payload'] for x in lines if x['stream'] == 'stderr'],
                                                 main_own['lines']['stderr'])))
            edited = markers / ('%s.edited' % main_own.get('pid'))
            check('record/claude-complete', 'the edit the record shows was made in the clone\'s file',
                  edited.is_file() and EDIT['new'] in edited.read_text() and EDIT['old'] not in edited.read_text())

        with region('record/codex-complete'):
            problems = judge(codex_launch.dispatch_id, codex_own)
            items = [e.get('item') or {} for e in events_of(codex_launch.dispatch_id) if e.get('type') == 'item.completed']
            kinds = [i.get('type') for i in items]
            outputs = ' '.join(str(i.get('aggregated_output')) for i in items if i.get('type') == 'command_execution')
            stderr_kept = [x['payload'] for x in kept(codex_launch.dispatch_id)[1] if x.get('stream') == 'stderr']
            check('record/codex-complete', 'every line the Codex worker printed on its output and its error stream was '
                  'kept, in order, after the wrapper\'s identity line [%s]' % problems,
                  codex_record.get('state') == 'exited' and not problems)
            check('record/codex-complete', 'the record holds both commands with their output and error stream, the failed '
                  'one\'s exit code, the file change, the error item, the error stream\'s own line [%s, %s]'
                  % (kinds, stderr_kept),
                  kinds.count('command_execution') == 2 and 'file_change' in kinds and 'error' in kinds
                  and 'v141 codex output' in outputs and 'v141 codex error' in outputs and 'v141 codex failing' in outputs
                  and any(i.get('exit_code') == 2 for i in items)
                  and stderr_kept == [STREAM['codex']['stderr']['prompt_from_stdin']['text']])

        with region('record/stream-options'):
            argv = main_own.get('argv') or []
            wanted = [SWITCHES.get(n, {}).get('name') for n in ('include_partial_messages', 'forward_subagent_text')]
            events = events_of(main_launch.dispatch_id)
            subagent = [e for e in events if e.get('parent_tool_use_id')]
            partials = [e for e in events if e.get('type') == 'stream_event']
            check('record/stream-options', 'the Claude Code run carried --verbose, --include-partial-messages and '
                  '--forward-subagent-text, each an option the binary declares and the qualified baseline lists [%s]'
                  % argv[1:],
                  '--verbose' in argv and all(w and w in argv and w in OPTIONS['options'] for w in wanted)
                  and all(w in ((getattr(E, 'BASELINE', None) or {}).get('stream_options') or []) for w in wanted))
            shipped = json.loads((ROOT / 'engine' / 'runtime' / 'claude-qualification.json').read_text())
            check('record/stream-options', 'the shipped 2.1.281 record qualifies the baseline with them',
                  ((shipped.get('versions') or {}).get(VERSION) or {}).get('baseline') == getattr(E, 'BASELINE', None)
                  and all(w in (((shipped['versions'][VERSION]).get('baseline') or {}).get('stream_options') or [])
                          for w in wanted))
            check('record/stream-options', 'the subagent\'s forwarded text and the partial messages are in the record '
                  '[%d subagent, %d partial]' % (len(subagent), len(partials)),
                  any(e.get('type') == 'assistant' and 'v141 subagent text' in json.dumps(e) for e in subagent)
                  and len(partials) >= 2 and any(e.get('parent_tool_use_id') for e in partials))

        # AC2 and AC3: the route, live and from cursors.
        main_frames = frames_of(main_writes)
        header, main_lines = kept(main_launch.dispatch_id)
        exited_at = next((h.get('at') for h in (main_record.get('history') or []) if h.get('state') == 'exited'), None)

        with region('api/live'):
            served = [x for _, _, _, f in main_frames for x in f.get('lines') or []]
            live = [at for at, _, event, f in main_frames if f.get('lines') and exited_at and at < exited_at]
            closing = [f for _, _, event, f in main_frames if event == 'closed']
            check('api/live', 'the owner followed the run from the first cursor while it wrote: frames of kept lines '
                  'arrived before the exit was recorded, each woken by a record hint [%d frames, %d before the exit, %d '
                  'hints]' % (len(main_frames), len(live), len(main_hints)),
                  main_opened and main_opened[0][0] == 200 and len(live) >= 2
                  and len([h for h, _ in main_hints if h.get('dispatch_id') == main_launch.dispatch_id]) >= 2)
            check('api/live', 'after the run ended the stream served the rest and closed as ended, having served every '
                  'kept line once, in sequence [%d served, %d kept, %s]'
                  % (len(served), len(main_lines), [c.get('reason') for c in closing]),
                  [x.get('seq') for x in served] == list(range(1, len(main_lines) + 1)) and bool(main_lines)
                  and closing and closing[-1].get('reason') == 'ended')
            ids_seen = [int(i) for _, i, event, _ in main_frames if event == 'record' and i is not None]
            check('api/live', 'each frame is a record frame whose id is its cursor, the last one the committed count',
                  ids_seen and ids_seen == sorted(ids_seen) and ids_seen[-1] == len(main_lines))

        with region('api/cursor'):
            middle = len(main_lines) // 2
            resumed_writes = []
            resumed = call('GET', STREAM_PATH + '?dispatch=%s&after=0' % main_launch.dispatch_id, cookie=owner_cookie,
                           extra={'Last-Event-ID': str(middle)})
            if isinstance(resumed[2], API.Stream):
                consume(resumed[2], resumed_writes).join(10)
            again = [x for _, _, _, f in frames_of(resumed_writes) for x in f.get('lines') or []]
            check('api/cursor', 'a stream resumed with Last-Event-ID %d serves exactly the lines after it, then closes as '
                  'ended [%s]' % (middle, [x.get('seq') for x in again][:3]),
                  resumed[0] == 200 and [x.get('seq') for x in again] == list(range(middle + 1, len(main_lines) + 1))
                  and any(e == 'closed' and f.get('reason') == 'ended' for _, _, e, f in frames_of(resumed_writes)))
            got = page(main_launch.dispatch_id, middle)
            check('api/cursor', 'a page from the middle cursor starts after it [%s]' % got[0],
                  got[0] == 200 and [x['seq'] for x in got[2].get('lines') or []][:1] == [middle + 1])

        with region('api/refusals'):
            outside = page(main_launch.dispatch_id, 0, cookie=outsider_cookie)
            unknown = page('dispatch/VELDO-14199/' + uuid.uuid4().hex, 0)
            past = page(main_launch.dispatch_id, len(main_lines) + 5)
            check('api/refusals', 'a member whose scope does not cover the run\'s project is refused by name, nothing '
                  'served [%s %s]' % (outside[0], refusal(outside)),
                  outside[0] == 403 and refusal(outside) == 'unauthorized:out_of_scope' and 'lines' not in (outside[2] or {}))
            check('api/refusals', 'an unknown run and a cursor past the end are refused by name, never an empty record '
                  '[%s %s, %s %s]' % (unknown[0], refusal(unknown), past[0], refusal(past)),
                  unknown[0] == 404 and refusal(unknown) == 'missing_evidence:unknown_run'
                  and past[0] == 400 and refusal(past) == 'invalid_input:cursor_past_end')
            # The ended session: signed out while the run was writing.
            if ended.get('thread') is not None:
                ended['thread'].join(10)
            after_out = ended.get('after') or (0, {}, {})
            closes = [f.get('reason') for _, _, e, f in frames_of(ended['writes']) if e == 'closed']
            check('api/refusals', 'a session that ended while the run was writing is refused by name, and the record '
                  'stream it had open closed as it ended, before the run did [%s %s, %s]'
                  % (after_out[0], refusal(after_out), closes),
                  (ended.get('signed_out') or (0,))[0] == 200 and after_out[0] == 401
                  and refusal(after_out) == 'unauthenticated:no_session'
                  and isinstance((ended.get('followed') or (0, {}, None))[2], API.Stream) and closes == ['signed_out'])
            outsider_stream = call('GET', STREAM_PATH + '?dispatch=%s' % main_launch.dispatch_id, cookie=outsider_cookie)
            check('api/refusals', 'nor is a stream opened for a member outside the scope [%s %s]'
                  % (outsider_stream[0], refusal(outsider_stream)),
                  outsider_stream[0] == 403 and refusal(outsider_stream) == 'unauthorized:out_of_scope')

        # The planted run as served: every page from the first cursor, and its live stream.
        planted_served, planted_answers = all_pages(planted_launch.dispatch_id)
        planted_writes = []
        planted_stream = call('GET', STREAM_PATH + '?dispatch=%s' % planted_launch.dispatch_id, cookie=owner_cookie)
        if isinstance(planted_stream[2], API.Stream):
            consume(planted_stream[2], planted_writes).join(10)
        words = planted.split('.')

        def leaks(text):
            """Which secrets a text holds: any word of the planted value, the token, the known-pattern token."""
            found = [w for w in words if w in text]
            found += [n for n, v in (('token', token_value), ('pattern', pattern_token), ('high', high)) if v in text]
            return found

        with region('api/no-secret-served'):
            served_text = json.dumps([a[2] for a in planted_answers if isinstance(a[2], dict)]) + ''.join(
                d.decode() for _, d in planted_writes)
            check('api/no-secret-served', 'every page and every stream frame the API served of the planted run holds no '
                  'part of the planted value, the subscription token, the known-pattern token or the high-entropy span '
                  '[%s, %d lines served]' % (leaks(served_text), len(planted_served)),
                  len(planted_served) == len(planted_lines) and len(planted_served) > 10 and not leaks(served_text)
                  and served_text.count('[REDACTED:%s]' % PLANTED_KIND) >= 8)
            printed = '\n'.join(sum(((planted_own.get('lines') or {}).get(s) or [] for s in ('engine', 'stderr')), []))
            check('api/no-secret-served', 'while the run printed each of them [%s]' % sorted(set(leaks(printed))),
                  set(leaks(printed)) == set(words) | {'token', 'pattern', 'high'})

        with region('api/service-call'):
            # The API process reaches the authority only over the service socket: control_client_api's call, carried
            # by control_service_api's dispatch to this judge (the transport itself stood in).
            service = object.__new__(SAPI.ServiceApi)
            service.authority, service.instance, service.counts = authority, 'v141-service', {'calls': 0, 'refused': 0}
            asked = []

            def send(workspace, command, enrollment, verify, sign_request, host, timeout=30.0):
                asked.append(command)
                return {'accepted': True, 'result': service.call(command)}
            CAm.CC.send = send
            remote = CAm.ServiceAuthority('/v141-workspace', None, 'v141-host', None)
            answer, error = attempt(lambda: remote.record('owner', main_launch.dispatch_id, 0, 512))
            refused, _ = attempt(lambda: remote.record('outsider', main_launch.dispatch_id, 0, 512))
            check('api/service-call', 'the record call over the service socket serves the owner the same lines the file '
                  'holds, and refuses the outsider by name [%s, %s]' % (error, (refused or {}).get('reason')),
                  isinstance(answer, dict) and answer.get('ok') is True
                  and [x.get('payload') for x in answer.get('lines') or []] == [x.get('payload') for x in main_lines]
                  and bool(main_lines) and (refused or {}).get('reason') == 'unauthorized:out_of_scope'
                  and asked and asked[0].get('call') == 'record')

        with region('route/served-lines'):
            served, _ = all_pages(main_launch.dispatch_id)
            fields = ('seq', 'at', 'stream', 'redacted', 'payload')
            check('route/served-lines', 'the route served every kept line of the run, as kept: count, order, sequence, '
                  'receive time, stream, redaction marks and payload, nothing merged, dropped, reordered or replaced '
                  '[%d served, %d kept]' % (len(served), len(main_lines)),
                  bool(main_lines) and [[x.get(f) for f in fields] for x in served]
                  == [[x.get(f) for f in fields] for x in main_lines])
            live_lines = [x for _, _, _, f in main_frames for x in f.get('lines') or []]
            check('route/served-lines', 'and so did the live stream', [[x.get(f) for f in fields] for x in live_lines]
                  == [[x.get(f) for f in fields] for x in main_lines] and bool(main_lines))
            printed = (main_own.get('lines') or {}).get('engine') or []
            engine_served = [x.get('payload') for x in served if x.get('stream') == 'engine']
            check('route/served-lines', 'every engine event served is the one the engine printed: each tool call with its '
                  'input and result, each command\'s output, the edit and the error [%d of %d]'
                  % (len(engine_served), len(printed)),
                  len(engine_served) == len(printed) and printed and all(same(s, p) for s, p in zip(engine_served, printed)))

        with region('route/committed'):
            final = page(main_launch.dispatch_id, len(main_lines))
            committed = main_record.get('execution_record') or {}
            path = Path(ER.path(str(records_dir), main_launch.dispatch_id)) if ER is not None else Path('/nonexistent')
            check('route/committed', 'after the run ended the route names it ended with the committed line count and '
                  'digest, the exit record\'s, which the kept file matches [%s, %s]' % (final[0], committed),
                  final[0] == 200 and final[2].get('ended') is True and final[2].get('committed') == committed
                  and committed.get('lines') == len(main_lines) and path.is_file()
                  and committed.get('digest') == file_sha(path) and committed.get('bytes') == path.stat().st_size)
            # A record that no longer matches its commitment is refused by name, never served: one line's text
            # changed in place (the same lines and bytes), and one line more.
            copied = path.read_bytes() if path.is_file() else b''
            tampers = {'a line changed': copied.replace(b'v141 done', b'v141 DONE'),
                       'a line added': copied + (json.dumps({'seq': len(main_lines) + 1, 'payload': 'x'}) + '\n').encode()}
            seen = {}
            for name, data in tampers.items():
                if path.is_file():
                    path.write_bytes(data)
                seen[name] = page(main_launch.dispatch_id, 0)
                if path.is_file():
                    path.write_bytes(copied)
            check('route/committed', 'a record whose file no longer matches the committed digest is refused by name '
                  '[%s]' % {n: (s[0], refusal(s)) for n, s in seen.items()},
                  copied.count(b'v141 done') == 1 and all(s[0] == 500 and refusal(s) == 'unknown_outcome:record_digest'
                                                          for s in seen.values()))
            # A record shown for another run: the Codex run's file in this run's place is refused by name.
            other = Path(ER.path(str(records_dir), codex_launch.dispatch_id)) if ER is not None else Path('/nonexistent')
            if path.is_file() and other.is_file():
                path.write_bytes(other.read_bytes())
            swapped = page(main_launch.dispatch_id, 0)
            if path.is_file():
                path.write_bytes(copied)
            check('route/committed', 'another run\'s record in this run\'s place is refused as bound to another run '
                  '[%s %s]' % (swapped[0], refusal(swapped)),
                  other.is_file() and swapped[0] == 500 and refusal(swapped) == 'unknown_outcome:record_binding'
                  and page(main_launch.dispatch_id, 0)[0] == 200)
            check('route/committed', 'the record file is the receiver\'s alone: 0600 in a 0700 directory',
                  path.is_file() and path.stat().st_mode & 0o777 == 0o600 and records_dir.stat().st_mode & 0o777 == 0o700)

        # AC4: exact-value replacement before the scanner.
        with region('redaction/planted-value'):
            everything = '\n'.join(x.get('payload', '') for x in planted_lines)
            marker = '[REDACTED:%s]' % PLANTED_KIND
            printed = {s: (planted_own.get('lines') or {}).get(s) or [] for s in ('engine', 'stderr')}
            pairs = []
            for s in ('engine', 'stderr'):
                pairs += list(zip([x.get('payload', '') for x in planted_lines if x.get('stream') == s], printed[s]))
            counted = all(k.count(marker) == p.count(planted) for k, p in pairs)
            places = {'alone in the command output': any('"stdout": "%s\\n' % planted in p for p in printed['engine']),
                      'inside the command output': any('held %s in output' % planted in p for p in printed['engine']),
                      'in the error stream': planted in printed['stderr'],
                      'joined to a high-entropy span': any(high + planted in p for p in printed['engine'] + printed['stderr'])}
            check('redaction/planted-value', 'the planted resolver\'s value, printed alone, inside a command\'s output, in '
                  'the error stream and joined to a high-entropy span, is replaced wherever it was printed by the marker '
                  'naming its kind, and no line holds any part of it [%s, %s]' % (leaks(everything), counted),
                  planted_record.get('state') == 'exited' and len(pairs) == len(planted_lines) - 1 and counted
                  and not [w for w in words if w in everything] and everything.count(marker) >= 8
                  and all(places.values()))
            joined = [x for x in planted_lines if 'joined' in x.get('payload', '')]
            check('redaction/planted-value', 'the joined span: the value replaced whole and the high-entropy rest '
                  'redacted by the scanner [%s]' % [x.get('redacted') for x in joined],
                  len(joined) == 2 and all(marker in x['payload'] and '[REDACTED:entropy]' in x['payload']
                                           and PLANTED_KIND in x.get('redacted') and 'entropy' in x.get('redacted')
                                           for x in joined))
            check('redaction/planted-value', 'the receiver named the planted kind and the subscription token among the '
                  'run\'s resolved values and redactions, never a value [%s]' % planted_summary.get('resolved_kinds'),
                  set(planted_summary.get('resolved_kinds') or []) >= {PLANTED_KIND, 'subscription_token'}
                  and not leaks(json.dumps(planted_summary)))

        with region('redaction/known-pattern'):
            shaped = [x for x in planted_lines if 'pattern ' in x.get('payload', '')]
            check('redaction/known-pattern', 'the token of a known pattern is redacted by the scanner in the messages and '
                  'the error stream, its kind named [%s]' % [x.get('redacted') for x in shaped],
                  len(shaped) == 2 and all('[REDACTED:pattern:github_token]' in x['payload']
                                           and 'pattern:github_token' in x['redacted'] for x in shaped)
                  and pattern_token not in '\n'.join(x['payload'] for x in planted_lines))
            tokened = [x for x in planted_lines if x.get('stream') == 'stderr' and x.get('payload', '').startswith('token ')]
            check('redaction/known-pattern', 'the account\'s subscription token, a resolved value, is replaced as one '
                  '[%s]' % [x.get('payload') for x in tokened],
                  len(tokened) == 1 and tokened[0]['payload'] == 'token [REDACTED:subscription_token]'
                  and tokened[0]['redacted'] == ['subscription_token'])

        with region('redaction/kinds-field'):
            wrong = [x.get('seq') for x in planted_lines + main_lines
                     if sorted(set(MARK.findall(x.get('payload', '')))) != x.get('redacted')]
            check('redaction/kinds-field', 'each kept line\'s redaction field names exactly the kinds replaced in it [%s]'
                  % wrong[:5], planted_lines and main_lines and not wrong
                  and any(x.get('redacted') for x in planted_lines) and any(not x.get('redacted') for x in planted_lines))

        with region('redaction/exact-set'):
            controlled = [x for x in planted_lines if 'control ' in x.get('payload', '')]
            check('redaction/exact-set', 'a low-entropy word no resolver named is kept as printed: the receiver replaces '
                  'exactly the run\'s set [%s]' % [x.get('payload')[-60:] for x in controlled],
                  len(controlled) == 2 and all(control_word in x['payload'] for x in controlled))
            judged = judge(planted_launch.dispatch_id, planted_own,
                           resolved={PLANTED_KIND: planted, 'subscription_token': token_value})
            check('redaction/exact-set', 'and every other line is the printed one with only redacted spans replaced [%s]'
                  % judged, not judged)


        # THE PATH AND URL RULE: the record's entropy step scores a rooted path by segment and a URL by component,
        # through the production redact and in the live run's own lines.
        def redacted(text, resolved=None):
            got, error = attempt(lambda: ER.redact(text, resolved if resolved is not None else ER.Resolved()))
            return tuple(got) if isinstance(got, tuple) else ('', ['raised:%s' % error])

        def whole_high(text):
            """Whether the scanner's rule, judging each candidate of `text` whole, would replace one."""
            return any(not SS._is_digest(t) and SS.shannon(t) >= SS.ENTROPY_THRESHOLD for t in SS._CANDIDATE.findall(text))

        def fresh():
            while True:
                value = ''.join(pick.choice(string.ascii_letters + string.digits) for _ in range(40))
                if not any(rx.search(value) for rx, _ in SS.PATTERNS) and SS.shannon(value) >= SS.ENTROPY_THRESHOLD:
                    return value
        ENTROPY = '[REDACTED:entropy]'

        def printed_of(own, kind):
            return [x for x in (own.get('lines') or {}).get('engine') or [] if '"type": "%s"' % kind in x]

        with region('redaction/paths-kept'):
            init_printed = [x for x in printed_of(main_own, 'system') if '"subtype": "init"' in x]
            init_kept = [x for x in main_lines if x.get('stream') == 'engine' and '"subtype": "init"' in x.get('payload', '')]
            cwd = json.loads(init_printed[0]).get('cwd', '') if init_printed else ''
            check('redaction/paths-kept', 'the live run\'s init line is kept as printed, its working directory (the clone '
                  'under the runtime directory, which the scanner judging it whole would replace) whole [%s]'
                  % [x.get('payload', '')[:120] for x in init_kept],
                  len(init_printed) == 1 and len(init_kept) == 1 and init_kept[0].get('payload') == init_printed[0]
                  and init_kept[0].get('redacted') == [] and cwd.startswith(runtime) and whole_high(cwd))
            edit_printed = [x for x in printed_of(main_own, 'assistant') if '"name": "Edit"' in x]
            edit_kept = [x for x in main_lines if x.get('stream') == 'engine' and '"name": "Edit"' in x.get('payload', '')]
            file_path = (((json.loads(edit_printed[0]).get('message') or {}).get('content') or [{}])[0].get('input')
                         or {}).get('file_path', '') if edit_printed else ''
            check('redaction/paths-kept', 'the Edit tool call\'s input is kept as printed, its absolute file path whole [%s]'
                  % [x.get('payload', '')[-160:] for x in edit_kept],
                  len(edit_printed) == 1 and len(edit_kept) == 1 and edit_kept[0].get('payload') == edit_printed[0]
                  and edit_kept[0].get('redacted') == [] and file_path.startswith(cwd) and whole_high(file_path))
            def named(prefix, size):
                """A named digest (a clone's directory, a pinned copy's digest) the scanner judging it whole replaces."""
                while True:
                    value = prefix + secrets.token_hex(size)
                    if SS.shannon(value) >= SS.ENTROPY_THRESHOLD:
                        return value
            typical = [cwd + '/src',
                       '/home/dmitry/projects/veldo-worktrees/build-veldo-0141/.veldo/control_launch.py',
                       '/var/lib/veldo/factory/engines/claude_code/2.1.281/%s/claude' % hashlib.sha256(
                           cwd.encode()).hexdigest(),
                       STREAM['codex']['binary'],
                       '%s/state/clones/%s/work' % (runtime, named('clone-', 16)),
                       '/var/lib/veldo/factory/engines/claude_code/2.1.281/%s/claude' % named('sha256-', 32)]
            lines_of = ['cd %s && python3 %s' % (typical[0], typical[1]),
                        json.dumps({'type': 'tool_use', 'input': {'command': 'ls ' + typical[2], 'cwd': typical[3]}})]
            kept_typical = [redacted(t) for t in typical + lines_of]
            check('redaction/paths-kept', 'typical real paths (a clone path under the runtime directory, its clone '
                  'directory named by a digest, a worktree\'s control_launch.py, a pinned engine path with its version '
                  'and a digest segment, bare and named, Codex\'s vendor binary), alone and inside a command and a tool input, are kept whole, each one the scanner judging '
                  'it whole replaces [%s]' % [k[0][:90] for k, t in zip(kept_typical, typical + lines_of) if k[0] != t],
                  all(k == (t, []) for k, t in zip(kept_typical, typical + lines_of)) and all(whole_high(t) for t in typical))

        with region('redaction/path-segment'):
            secret = fresh()
            prefix, suffix = '/home/dmitry/projects/veldo-worktrees/build-veldo-0141/', '/notes.txt'
            embedded = prefix + secret + suffix
            got = redacted(embedded)
            check('redaction/path-segment', 'a path with an embedded 40-character random segment keeps the rest and '
                  'replaces that segment [%s]' % got[0], got == (prefix + ENTROPY + suffix, ['entropy']))
            as_input = json.dumps({'type': 'tool_use', 'input': {'file_path': embedded}})
            got = redacted(as_input)
            check('redaction/path-segment', 'likewise inside a tool input [%s]' % got[0][-90:],
                  got == (as_input.replace(secret, ENTROPY), ['entropy']) and secret not in got[0])
            second = fresh()
            windows = 'C:\\Users\\dmitry\\%s\\file.txt' % second
            got = redacted(json.dumps({'path': windows}))
            check('redaction/path-segment', 'and in a backslash-separated path, as JSON carries it [%s]' % got[0],
                  got == (json.dumps({'path': windows}).replace(second, ENTROPY), ['entropy']))
            resolved = ER.Resolved() if ER is not None else None
            if resolved is not None:
                resolved.add(PLANTED_KIND, planted)
            inside = '/home/dmitry/work/%s/%s%s/notes' % (planted, high, planted)
            got = redacted(inside, resolved)
            check('redaction/path-segment', 'a resolved value inside a path is replaced first, whole, and a high-entropy '
                  'segment joined to it still goes [%s]' % got[0],
                  got == ('/home/dmitry/work/[REDACTED:%s]/%s[REDACTED:%s]/notes' % (PLANTED_KIND, ENTROPY, PLANTED_KIND),
                          sorted(['entropy', PLANTED_KIND]))
                  and not any(w in got[0] for w in words))

        with region('redaction/url-component'):
            value = fresh()
            url = 'https://api.example.com/v1/repos/owner/name?access_token=%s&page=2' % value
            got = redacted(url)
            check('redaction/url-component', 'a URL with a token query value keeps its host, path and key and replaces '
                  'only the value [%s]' % got[0], got == (url.replace(value, ENTROPY), ['entropy']))
            segment = fresh()
            url = 'https://api.example.com/v1/%s/items?page=2' % segment
            got = redacted(json.dumps({'url': url}))
            check('redaction/url-component', 'and a high-entropy path segment of a URL goes, the rest kept [%s]' % got[0],
                  got == (json.dumps({'url': url}).replace(segment, ENTROPY), ['entropy']))
            plain = 'https://api.example.com/v1/repos/veldo-worktrees/build-veldo-0141/pulls?state=open&per_page=100'
            check('redaction/url-component', 'an ordinary URL the scanner judging it whole replaces is kept whole',
                  redacted(plain) == (plain, []) and whole_high(plain))

        with region('redaction/account-fields'):
            for label, own, lines_ in (('the plain login', main_own, main_lines), ('the token login', planted_own,
                                                                                    planted_lines)):
                answer = printed_of(own, 'control_response')
                account = ((json.loads(answer[0]).get('response') or {}).get('response') or {}).get('account') or {} \
                    if len(answer) == 1 else {}
                kept_answer = [x for x in lines_ if x.get('stream') == 'engine'
                               and '"type": "control_response"' in x.get('payload', '')]
                shown = json.loads(kept_answer[0]['payload']) if len(kept_answer) == 1 else {}
                shown_account = ((shown.get('response') or {}).get('response') or {}).get('account') or {}
                everything = '\n'.join(x.get('payload', '') for x in lines_)
                check('redaction/account-fields', '%s: the handshake answer\'s email and organization are replaced by '
                      'field and appear nowhere in the record; how the run logged in is kept [%s %s]'
                      % (label, shown_account, [x.get('redacted') for x in kept_answer]),
                      account.get('email') and account.get('organization')
                      and shown_account.get('email') == '[REDACTED:account:email]'
                      and shown_account.get('organization') == '[REDACTED:account:organization]'
                      and {'account:email', 'account:organization'} <= set(kept_answer[0].get('redacted') or [])
                      and account['email'] not in everything and account['organization'] not in everything
                      and {k: v for k, v in shown_account.items() if k not in ('email', 'organization')}
                      == {k: v for k, v in account.items() if k not in ('email', 'organization')})
            ids = {'accountUuid': str(uuid.uuid4()), 'organizationUuid': str(uuid.uuid4()),
                   'email': 'owner.%s@example.invalid' % uuid.uuid4().hex[:8]}
            init = json.dumps(dict({'type': 'system', 'subtype': 'init', 'cwd': cwd, 'apiKeySource': 'none'}, **ids))
            got = redacted(init)
            wanted = init
            for field, value_ in ids.items():
                wanted = wanted.replace(value_, '[REDACTED:account:%s]' % field)
            check('redaction/account-fields', 'an init line\'s account and organization uuid and email are replaced by '
                  'field, its working directory kept [%s]' % got[0],
                  got == (wanted, sorted('account:' + f for f in ids)) and cwd in got[0])

        with region('fixture/planted-control'):
            check('fixture/planted-control', 'the planted value has no known pattern and low entropy: the scanner alone '
                  'finds nothing in it [%.2f bits]' % SS.shannon(planted),
                  not SS.scan_text(planted) and SS.shannon(planted) < SS.ENTROPY_THRESHOLD)
            glued = [t for t in SS._CANDIDATE.findall('joined ' + high + planted) if SS.shannon(t) >= SS.ENTROPY_THRESHOLD]
            rest = ('joined ' + high + planted).replace(glued[0], '[REDACTED:entropy]') if glued else ''
            check('fixture/planted-control', 'joined to the high-entropy span, the scanner run first takes the value\'s '
                  'first part with the span and leaves the rest, so only exact replacement first removes it all [%s]'
                  % rest[-40:], len(glued) == 1 and glued[0].endswith(words[0]) and planted not in rest
                  and words[1] in rest and words[2] in rest)
            check('fixture/planted-control', 'the known-pattern token is one the scanner\'s patterns find',
                  any(rx.search(pattern_token) for rx, why in SS.PATTERNS if 'GitHub' in why))

        # Review regressions exercise the same recorder, authority and stream used above.
        with region('redaction/partial-blocks'):
            if ER is None:
                check('redaction/partial-blocks', 'the recorder exists', False)
            else:
                resolved = ER.Resolved()
                resolved.add(PLANTED_KIND, planted)
                directory_ = base / 'partial-records'
                recorder = ER.Recorder(directory_, dict(header, dispatch_id='partial-review'), resolved)
                printed, affected = [], {}
                def partial(event, parent=None):
                    envelope = {'type': 'stream_event', 'event': event, 'session_id': 'review',
                                'parent_tool_use_id': parent}
                    printed.append(envelope)
                    recorder.feed('engine', (json.dumps(envelope) + '\n').encode())
                for index, field, width in ((0, 'text', 7), (1, 'partial_json', 9)):
                    content = ('ordinary output ' * 30 + planted + ' and ' + pattern_token + ' done ' * 60)
                    if field == 'partial_json':
                        content = json.dumps({'file_path': '/w/output', 'content': content})
                    partial({'type': 'content_block_start', 'index': index, 'content_block': {}})
                    for offset in range(0, len(content), width):
                        part = content[offset:offset + width]
                        partial({'type': 'content_block_delta', 'index': index,
                                 'delta': {'type': 'text_delta' if field == 'text' else 'input_json_delta', field: part}})
                        wanted = set()
                        for value, kind in ((planted, PLANTED_KIND), (pattern_token, 'pattern:github_token')):
                            start = content.index(value)
                            if offset < start + len(value) and offset + len(part) > start:
                                wanted.add(kind)
                        if wanted:
                            affected[len(printed)] = wanted
                    live = ER.read(directory_, 'partial-review', 0, 10000)['lines']
                    check('redaction/partial-blocks', 'safe output is live before block stop',
                          len(live) > index * 20 + 10 and len(live) < len(printed))
                    partial({'type': 'content_block_stop', 'index': index})
                committed = recorder.close()
                served = ER.read(directory_, 'partial-review', 0, 10000, committed=committed)['lines']
                joined = {0: '', 1: ''}
                clean = len(served) == len(printed)
                for line in served:
                    item = json.loads(line['payload'])['event']
                    delta = item.get('delta') or {}
                    if delta:
                        joined[item['index']] += delta.get('text', delta.get('partial_json', ''))
                    if line['seq'] in affected:
                        clean &= affected[line['seq']] <= set(line['redacted'])
                check('redaction/partial-blocks', 'every fragment of each value has a named replacement',
                      clean and all(planted not in value and pattern_token not in value for value in joined.values())
                      and all(not any(word in value for word in planted.split('.')) for value in joined.values()))
                recorder = ER.Recorder(directory_, {'dispatch_id': 'start-review'}, resolved)
                for event in ({'type': 'content_block_start', 'index': 0,
                               'content_block': {'type': 'text', 'text': planted[:4]}},
                              {'type': 'content_block_delta', 'index': 0,
                               'delta': {'type': 'text_delta', 'text': planted[4:]}},
                              {'type': 'content_block_stop', 'index': 0}):
                    recorder.feed('engine', (json.dumps({'type': 'stream_event', 'event': event}) + '\n').encode())
                committed = recorder.close()
                lines = ER.read(directory_, 'start-review', 0, 100, committed=committed)['lines']
                check('redaction/partial-blocks', 'initial block text participates in delta redaction',
                      len(lines) == 3 and all(PLANTED_KIND in line['redacted'] for line in lines[:2]))
                # Patterns can grow beyond any fixed tail, including whitespace before an assigned value.
                recorder = ER.Recorder(directory_, {'dispatch_id': 'unbounded-review'}, resolved)
                recorder.feed('engine', (json.dumps({'type': 'stream_event', 'event': {'type': 'content_block_start',
                    'index': 0, 'content_block': {}}}) + '\n').encode())
                opaque = fresh() * 20
                assigned = 'to' + 'ken' + ' ' * 600 + '= ' + chr(34) + 'low' * 6 + chr(34)
                long_pattern = pattern_token + 'a' * 600
                content = assigned + ' next ' + long_pattern + ' next ' + opaque + ' done'
                for offset in range(0, len(content), 7):
                    recorder.feed('engine', (json.dumps({'type': 'stream_event', 'event': {
                        'type': 'content_block_delta', 'index': 0,
                        'delta': {'type': 'text_delta', 'text': content[offset:offset + 7]}}}) + '\n').encode())
                committed = recorder.close()
                lines = ER.read(directory_, 'unbounded-review', 0, 10000, committed=committed)['lines']
                deltas = [line for line in lines if 'text_delta' in line['payload']]
                expected = [(0, len(assigned), 'pattern:credential_assigned_as_a_literal'),
                            (content.index(long_pattern), content.index(long_pattern) + len(long_pattern), 'pattern:github_token'),
                            (content.index(opaque), content.index(opaque) + len(opaque), 'entropy')]
                check('redaction/partial-blocks', 'unbounded pattern and entropy spans never release an affected fragment',
                      all(kind in line['redacted'] for i, line in enumerate(deltas) for low, high, kind in expected
                          if i * 7 < high and (i + 1) * 7 > low))
                # Interleaved message identities and message-end flushing without a block stop.
                recorder = ER.Recorder(directory_, {'dispatch_id': 'interleaved-review'}, resolved)
                for parent in ('first', 'second'):
                    recorder.feed('engine', (json.dumps({'type': 'stream_event', 'parent_tool_use_id': parent,
                        'event': {'type': 'message_start', 'message': {'id': parent}}}) + '\n').encode())
                for offset in range(0, len(planted), 3):
                    for parent in ('first', 'second'):
                        recorder.feed('engine', (json.dumps({'type': 'stream_event', 'parent_tool_use_id': parent,
                            'event': {'type': 'content_block_delta', 'index': 0,
                                      'delta': {'type': 'text_delta', 'text': planted[offset:offset + 3]}}}) + '\n').encode())
                for parent in ('first', 'second'):
                    recorder.feed('engine', (json.dumps({'type': 'stream_event', 'parent_tool_use_id': parent,
                        'event': {'type': 'message_stop'}}) + '\n').encode())
                live = ER.read(directory_, 'interleaved-review', 0, 10000)['lines']
                recorder.close()
                check('redaction/partial-blocks', 'message end flushes isolated blocks with all fragments marked',
                      len(live) > 10 and all(PLANTED_KIND in line['redacted'] for line in live
                                            if 'text_delta' in line['payload']))

        with region('redaction/clone-relative-paths'):
            check('redaction/clone-relative-paths', 'receiver uses its bound clone, not its own working directory',
                  whole_high(relative_file) and any(relative_file in (line.get('payload') or '') for line in main_lines)
                  and any(relative_file in (line.get('payload') or '') for line in all_pages(main_launch.dispatch_id)[0]))
            if ER is None or not hasattr(ER, 'clone_paths'):
                check('redaction/clone-relative-paths', 'clone path snapshot exists', False)
            else:
                clone = base / 'path-clone'
                clone.mkdir()
                GP.run(['git', 'init', '-q', str(clone)], check=True)
                names = GP.run(['git', '-C', str(TREE), 'ls-files', '-z'], capture_output=True).stdout.decode().split('\0')
                names = [n for n in names if n and not n.startswith('.git')]
                for name in names:
                    target = clone / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('first\n')
                GP.run(['git', '-C', str(clone), 'add', '.'], check=True)
                for name in names:
                    (clone / name).write_text('second\n')
                extra_path = 'untracked/review_execution_record_output_file.py'
                (clone / extra_path).parent.mkdir()
                (clone / extra_path).touch()
                paths = ER.Resolved()
                paths.paths = ER.clone_paths(clone, root=clone)
                outputs = [GP.run(['git', '-C', str(clone), *args], capture_output=True, text=True).stdout
                           for args in (['diff', '--stat', '--stat-width=240'], ['status', '--short'])]
                outputs += ['  File "%s", line 1024, in receive\n' % name for name in names]
                outputs += ['\n'.join(names), extra_path]
                check('redaction/clone-relative-paths', 'git stat, status and every traceback keep clone file names',
                      len(names) > 1000 and all(ER.redact(out, paths)[0] == out for out in outputs))
                paths.paths = ER.clone_paths(clone / 'scripts', root=clone)
                check('redaction/clone-relative-paths', 'cwd and root relative names both resolve',
                      'suites/82_veldo_0141_execution_record.py' in paths.paths
                      and 'scripts/suites/82_veldo_0141_execution_record.py' in paths.paths)
                opaque = fresh()[:20] + '/' + fresh()
                request_id = 'veldo-initialize-' + os.urandom(8).hex()
                while not whole_high(request_id):
                    request_id = 'veldo-initialize-' + os.urandom(8).hex()
                check('redaction/clone-relative-paths', 'slash-bearing opaque value goes and handshake id stays',
                      ER.redact(opaque, paths)[0] == ENTROPY and ER.redact(request_id, paths)[0] == request_id)

        with region('redaction/clone-without-git'):
            row = 'redaction/clone-without-git'
            for layout in ('gitfile', 'fsmonitor'):
                clone = base / ('hostile-' + layout)
                cwd = clone / 'nested'
                cwd.mkdir(parents=True)
                root_name = fresh() + '.py'
                cwd_name = fresh() + '.py'
                (clone / root_name).touch()
                (cwd / cwd_name).touch()
                marker = base / ('marker-' + uuid.uuid4().hex)
                hook = base / ('monitor-' + uuid.uuid4().hex)
                hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
                hook.chmod(0o700)
                metadata = base / ('elsewhere-' + uuid.uuid4().hex) if layout == 'gitfile' else clone / '.git'
                metadata.mkdir()
                (metadata / 'objects').mkdir()
                (metadata / 'refs').mkdir()
                (metadata / 'HEAD').write_text('ref: refs/heads/fixture\n')
                (metadata / 'config').write_text('[core]\nrepositoryformatversion = 0\nfsmonitor = ' + str(hook) + '\n')
                if layout == 'gitfile':
                    (clone / '.git').write_text('gitdir: ' + str(metadata) + '\n')
                calls = []

                def spy_run(argv, **kwargs):
                    calls.append(argv)
                    return subprocess.CompletedProcess(argv, 1, stdout='', stderr='')

                def spy_popen(*args, **kwargs):
                    calls.append(args)
                    raise AssertionError('recorder attempted to start a process')

                with mock.patch.object(subprocess, 'run', spy_run), mock.patch.object(subprocess, 'Popen', spy_popen):
                    resolved = ER.Resolved()
                    resolved.paths = ER.clone_paths(cwd, root=clone)
                    payload = root_name + ' nested/' + cwd_name + ' ' + cwd_name
                    recorder = ER.Recorder(base / ('records-' + layout), {'dispatch_id': layout}, resolved)
                    recorder.line('engine', payload.encode())
                    committed = recorder.close()
                    lines = ER.read(base / ('records-' + layout), layout, 0, 100, committed=committed)['lines']
                    check(row, layout + ' keeps root and cwd paths readable',
                          len(lines) == 1 and lines[0]['payload'] == payload)
                    fallback = ER.Resolved()
                    fallback.paths = ER.clone_paths(cwd)
                    check(row, layout + ' without a supplied root falls back only to cwd',
                          fallback.paths.root == str(cwd) and ER.redact(cwd_name, fallback)[0] == cwd_name
                          and ER.redact(root_name, fallback)[0] != root_name)
                    check(row, 'absent cwd supplies no membership', ER.clone_paths(None, root=clone) == ())
                    receiver = object.__new__(L.Receiver)
                    receiver.contract = main_launch.contract
                    receiver.host, receiver.binding = HOST, None
                    receiver.config = {'clone_root': str(clone), 'records': str(base / ('receiver-' + layout))}
                    receiver._engine_cwd = lambda *args: str(cwd)
                    with mock.patch.object(L, 'RESOLVERS', []):
                        receiver._record({'argv': []}, {})
                    receiver.recorder.line('engine', payload.encode())
                    receiver.recorder.close()
                    check(row, layout + ' receiver passes its configured clone root',
                          receiver.resolved.paths.root == str(clone)
                          and L.ER.redact(payload, receiver.resolved)[0] == payload)
                check(row, layout + ' never starts a process or triggers fsmonitor', not calls and not marker.exists())

        with region('redaction/encoded-values'):
            import base64
            import urllib.parse
            resolved = ER.Resolved() if ER else None
            value = ' '.join(planted.split('.')) + '"\\' + planted
            if resolved is not None:
                resolved.add(PLANTED_KIND, value)
            variants = [base64.b64encode(value.encode()).decode(), urllib.parse.quote(value, safe=''),
                        urllib.parse.quote_plus(value), value.upper(), json.dumps(json.dumps({'value': value}))]
            nested = json.dumps({'value': value})
            for _ in range(8):
                nested = json.dumps(nested)
                variants.append(nested)
            for variant in variants:
                kept_, kinds = redacted(variant, resolved)
                check('redaction/encoded-values', 'encoded resolved value has an exact named replacement',
                      PLANTED_KIND in kinds and variant != kept_ and planted.split('.')[0] not in kept_)

        with region('api/scope-before-existence'):
            existing = page(main_launch.dispatch_id, 0, cookie=outsider_cookie)
            absent = page('review-absent', 0, cookie=outsider_cookie)
            absent_stream = call('GET', STREAM_PATH + '?dispatch=review-absent', cookie=outsider_cookie)
            check('api/scope-before-existence', 'outsider receives the same refusal for present and absent dispatches',
                  existing[0] == absent[0] == absent_stream[0] == 403
                  and refusal(existing) == refusal(absent) == refusal(absent_stream) == 'unauthorized:out_of_scope')

        with region('api/registration-race'):
            if not hasattr(api, '_record_page'):
                check('api/registration-race', 'record route exists', False)
            else:
                original_page, original_fill = api._record_page, api._fill_record
                for window in ('page', 'fill'):
                    once = []
                    def race_page(principal, dispatch_id, after):
                        answer = original_page(principal, dispatch_id, after)
                        if not once:
                            once.append(True)
                            if window == 'page':
                                api.deliver_record({'dispatch_id': dispatch_id, 'seq': answer['total']})
                            return dict(answer, ended=False)
                        return answer
                    def race_fill(stream, answer, always=False):
                        original_fill(stream, answer, always)
                        if window == 'fill' and always:
                            api.deliver_record({'dispatch_id': stream.dispatch_id, 'seq': answer['total']})
                    api._record_page, api._fill_record = race_page, race_fill
                    try:
                        response = call('GET', STREAM_PATH + '?dispatch=' + main_launch.dispatch_id, cookie=owner_cookie)
                        check('api/registration-race', 'end in the first %s window closes the stream' % window,
                              response[0] == 200 and getattr(response[2], 'closed', None) == 'ended')
                    finally:
                        api._record_page, api._fill_record = original_page, original_fill

        with region('api/registration-race'):
            if hasattr(api, '_fill_record'):
                stream = API.RecordStream('h', 'owner', 'c', 0, 'concurrent-review')
                entered, release, second_queued, second_started = [threading.Event() for _ in range(4)]
                original_put = stream.put
                def held_put(frame):
                    if frame['cursor'] == 1:
                        entered.set()
                        release.wait(3)
                    original_put(frame)
                    if frame['cursor'] == 2:
                        second_queued.set()
                stream.put = held_put
                def fill_second():
                    second_started.set()
                    api._fill_record(stream, {'lines': [{'seq': 1}, {'seq': 2}], 'total': 2})
                first = threading.Thread(target=api._fill_record, args=(stream, {'lines': [{'seq': 1}], 'total': 1}))
                second = threading.Thread(target=fill_second)
                first.start()
                ready = entered.wait(3)
                second.start()
                second_started.wait(3)
                second_queued.wait(1)
                release.set()
                first.join(3)
                second.join(3)
                frames = [stream.next(0), stream.next(0)]
                check('api/registration-race', 'initial catch-up and concurrent hint keep cursor and frame order',
                      ready and not first.is_alive() and not second.is_alive()
                      and [frame.get('cursor') for kind, frame in frames if kind == 'frame'] == [1, 2])

        with region('api/slow-reader'):
            if not hasattr(API, 'RecordStream'):
                check('api/slow-reader', 'record stream exists', False)
            else:
                stream = API.RecordStream('h', 'owner', 'c', 0, 'review')
                for cursor in range(1, 101):
                    stream.put({'cursor': cursor, 'lines': [{'payload': 'output'}]})
                received = []
                for _ in range(102):
                    kind, frame = stream.next(0)
                    if kind != 'frame':
                        break
                    received.append(frame['cursor'])
                check('api/slow-reader', 'overflow ends by name after a bounded contiguous prefix',
                      stream.closed == 'slow_reader' and kind == 'closed' and frame == 'slow_reader'
                      and 0 < len(received) <= 32 and received == list(range(1, len(received) + 1)))
                # Resume the actual ended run at the last delivered sequence.
                resume = page(main_launch.dispatch_id, min(len(received), len(main_lines)))
                check('api/slow-reader', 'cursor resumes without skipping a line', resume[0] == 200
                      and resume[2]['lines'] == main_lines[min(len(received), len(main_lines)):])
                large = API.RecordStream('h', 'owner', 'c', 0, 'review')
                large.put({'cursor': 1, 'lines': [{'payload': 'x' * (5 * 1024 * 1024)}]})
                check('api/slow-reader', 'one oversized line can advance an empty queue',
                      large.closed is None and large.next(0)[0] == 'frame')

        with region('route/unknown-committed'):
            # Force the containment observation after a real worker finishes. The unknown transition, journal,
            # record commitment and authority reads are production paths.
            original_driver = driver.read_text()
            inject = ('original_reap = L.Receiver._reap\n'
                      'def uncertain(self, *args, **kwargs):\n'
                      '    result = original_reap(self, *args, **kwargs)\n'
                      '    self.supervision["empty"] = False\n'
                      '    return result\n'
                      'L.Receiver._reap = uncertain\n')
            driver.write_text(original_driver.replace('L.main()\n', inject + 'L.main()\n'))
            try:
                unknown_launch, unknown_record, _, _ = live_run('acct-141a', 'claude',
                    {'task': 'unknown review', 'pace': 0.01}, planted_run=True)
            finally:
                driver.write_text(original_driver)
            commitment = unknown_record.get('execution_record')
            check('route/unknown-committed', 'unknown end commits the received record',
                  unknown_record.get('state') == 'unknown' and isinstance(commitment, dict))
            if ER and commitment:
                response = page(unknown_launch.dispatch_id, 0)
                check('route/unknown-committed', 'authority serves the committed unknown end',
                      response[0] == 200 and response[2]['ended'] and response[2]['committed'] == commitment)
                location = Path(ER.path(records_dir, unknown_launch.dispatch_id))
                original = location.read_bytes()
                try:
                    for changed in (original[:-1], original + b'{}\n', original.replace(b'engine', b'Engine', 1)):
                        location.write_bytes(changed)
                        check('route/unknown-committed', 'tampering with unknown record is refused',
                              refusal(page(unknown_launch.dispatch_id, 0)) == 'unknown_outcome:record_digest')
                finally:
                    location.write_bytes(original)

        with region('redaction/thinking-and-unknown'):
            if ER is None:
                check('redaction/thinking-and-unknown', 'recorder exists', False)
            else:
                resolved = ER.Resolved()
                resolved.add(PLANTED_KIND, planted)
                for dtype, fields in (('thinking_delta', ('thinking',)),
                                      ('future_delta', ('first', 'second'))):
                    rid = 'generic-' + dtype
                    rec = ER.Recorder(base / 'generic-records', {'dispatch_id': rid}, resolved)
                    content = 'ordinary words ' * 30 + planted + ' next ' + pattern_token + ' done ' * 70
                    def send_generic(event):
                        rec.feed('engine', (json.dumps({'type': 'stream_event', 'event': event}) + '\n').encode())
                    send_generic({'type': 'content_block_start', 'index': 0, 'content_block': {}})
                    for offset in range(0, len(content), 7):
                        send_generic({'type': 'content_block_delta', 'index': 0,
                                      'delta': dict({f: content[offset:offset + 7] for f in fields}, type=dtype)})
                    live = ER.read(base / 'generic-records', rid, 0, 10000)['lines']
                    if dtype == 'future_delta':
                        check('redaction/thinking-and-unknown', 'unknown deltas wait for block stop', len(live) == 1)
                    send_generic({'type': 'content_block_stop', 'index': 0})
                    commitment = rec.close()
                    final = ER.read(base / 'generic-records', rid, 0, 10000, commitment)['lines']
                    for lines in (live, final):
                        fragments = {field: '' for field in fields}
                        clean = True
                        for line in lines:
                            delta = json.loads(line['payload'])['event'].get('delta', {})
                            for field in fields:
                                fragments[field] += delta.get(field, '')
                            if delta:
                                index = line['seq'] - 2
                                for secret, kind in ((planted, PLANTED_KIND), (pattern_token, 'pattern:github_token')):
                                    low = content.index(secret)
                                    if index * 7 < low + len(secret) and (index + 1) * 7 > low:
                                        clean &= kind in line['redacted']
                        check('redaction/thinking-and-unknown', 'every affected fragment is redacted live and at end',
                              clean and all(secret[i:i + 8] not in value for value in fragments.values()
                                            for secret in (planted, pattern_token) for i in range(len(secret) - 7)))
                    check('redaction/thinking-and-unknown', 'all original lines survive',
                          len(final) == 2 + (len(content) + 6) // 7)

        with region('redaction/live-paths'):
            if ER is None:
                check('redaction/live-paths', 'recorder exists', False)
            else:
                clone = base / 'live-path-clone'
                directory_ = clone / 'src/components'
                directory_.mkdir(parents=True)
                old = 'src/components/ReviewExecutionRecordPanelView.tsx'
                (clone / old).touch()
                resolved = ER.Resolved()
                resolved.paths = ER.clone_paths(clone, root=clone)
                new = 'src/components/NewlyCreatedDuringTheRunPanelView.tsx'
                (clone / new).touch()
                dash = chr(45) * 2
                output = '\n'.join(['diff ' + dash + 'git a/' + old + ' b/' + old,
                                    chr(45) * 3 + ' a/' + old, '+++ b/' + old, '?? ' + new,
                                    ' .../suites/82_veldo_0141_execution_record.py | 3 +',
                                    'src/components/new.py'])
                check('redaction/live-paths', 'diff prefixes, new files, truncations and safe new leaves survive',
                      ER.redact(output, resolved)[0] == output)
                opaque = fresh()[:20] + '/' + fresh()
                short_leaf = 'src/' + fresh()[:28]
                while not whole_high(short_leaf) or SS.shannon(short_leaf[4:]) < SS.ENTROPY_THRESHOLD:
                    short_leaf = 'src/' + fresh()[:28]
                outside = base / 'outside-paths'
                outside.mkdir()
                hidden = fresh()
                (outside / hidden).touch()
                (clone / 'link').symlink_to(outside, target_is_directory=True)
                check('redaction/live-paths', 'nonexistent opaque keys and symlink escapes remain redacted',
                      ER.redact(opaque, resolved)[0] == ENTROPY
                      and whole_high(short_leaf) and ER.redact(short_leaf, resolved)[0] == ENTROPY
                      and hidden not in ER.redact('link/' + hidden, resolved)[0])

        with region('redaction/clone-leaf-candidates'):
            clone = base / 'candidate-leaf-clone'
            clone.mkdir()
            resolved = ER.Resolved()
            resolved.paths = ER.clone_paths(clone, root=clone)
            while True:
                candidate = ''.join(pick.choice(string.ascii_letters + string.digits) for _ in range(36))
                leaf = candidate + '.' * 30
                if whole_high(candidate) and SS.shannon(leaf) < SS.ENTROPY_THRESHOLD:
                    break
            text = 'checking %s ok' % leaf
            check('redaction/clone-leaf-candidates', 'a low entropy leaf cannot hide a scanner candidate',
                  ER.redact(text, resolved) == ('checking %s%s ok' % (ENTROPY, '.' * 30), ['entropy']))
            (clone / leaf).touch()
            check('redaction/clone-leaf-candidates', 'a real clone file leaf stays readable',
                  ER.redact(text, resolved) == (text, []))

        with region('redaction/uppercase-hex'):
            resolved = ER.Resolved()
            resolved.add(PLANTED_KIND, planted)
            lower = planted.encode().hex()
            upper = lower.upper()
            check('redaction/uppercase-hex', 'hex cases differ and both carry the resolved marker',
                  lower != upper and all(ER.redact('value %s done' % value, resolved)
                                        == ('value %s done' % ER.marker(PLANTED_KIND), [PLANTED_KIND])
                                        for value in (lower, upper)))

        with region('redaction/offset-encodings'):
            import base64
            resolved = ER.Resolved() if ER else None
            if resolved is not None:
                resolved.add(PLANTED_KIND, planted)
            variants = [planted.encode().hex()]
            for prefix in ('u:', 'us:', 'user:', 'KEY=', 'KEYS=', 'KEYSS='):
                variants.append(base64.b64encode((prefix + planted).encode()).decode())
            for value in variants:
                text, kinds = redacted(value, resolved)
                check('redaction/offset-encodings', 'offset base64 and lowercase hex carry the resolved marker',
                      value != text and PLANTED_KIND in kinds)

        with region('api/byte-pages'):
            if ER is None or not hasattr(API, 'RecordStream'):
                check('api/byte-pages', 'record route exists', False)
            else:
                # Serve a large record through the real authorized route with its committed digest.
                location = Path(ER.path(records_dir, main_launch.dispatch_id))
                original = location.read_bytes()
                original_dispatch = writer.execute('SELECT data FROM entities WHERE id=?',
                                                   ('dispatch:' + main_launch.dispatch_id,)).fetchone()[0]
                record = json.loads(original_dispatch)
                lines = [dict(seq=i + 1, stream='engine', at=0, redacted=[], payload='x' * 9000) for i in range(600)]
                large_data = original.split(b'\n', 1)[0] + b'\n' + b''.join(ER.encode(line) for line in lines)
                record['execution_record'] = dict(lines=len(lines), bytes=len(large_data),
                                                  digest='sha256:' + hashlib.sha256(large_data).hexdigest())
                try:
                    location.write_bytes(large_data)
                    writer.execute('UPDATE entities SET data=? WHERE id=?',
                                   (json.dumps(record), 'dispatch:' + main_launch.dispatch_id))
                    stream = API.RecordStream('h', 'owner', 'c', 0, main_launch.dispatch_id)
                    frames = []
                    def large_reader():
                        while True:
                            kind, frame = stream.next(1)
                            if kind == 'closed':
                                return
                            if kind == 'frame':
                                frames.append(frame)
                    reader = threading.Thread(target=large_reader)
                    reader.start()
                    api._fill_record(stream, api._record_page(stream.principal, stream.dispatch_id, 0), always=True)
                    reader.join(3)
                    stream.close('test_end')
                    reader.join(3)
                    check('api/byte-pages', '512 by 9 KB is split into byte bounded pages without closure',
                          stream.closed == 'ended' and len(frames) > 4
                          and all(len(json.dumps(f).encode()) < 1100000 for f in frames)
                          and [line for f in frames for line in f['lines']] == lines)
                    # At least one line, even when a single line exceeds the byte budget.
                    singleton = ER.Recorder(base / 'oversized', {'dispatch_id': 'one'}, None)
                    singleton.line('engine', b'x' * (5 * 1024 * 1024))
                    commitment = singleton.close()
                    check('api/byte-pages', 'an oversized line advances the authority cursor',
                          len(ER.read(base / 'oversized', 'one', 0, 512, commitment)['lines']) == 1)
                finally:
                    location.write_bytes(original)
                    writer.execute('UPDATE entities SET data=? WHERE id=?',
                                   (original_dispatch, 'dispatch:' + main_launch.dispatch_id))

        with region('api/fast-catchup'):
            if not hasattr(API, 'RecordStream'):
                check('api/fast-catchup', 'record stream exists', False)
            else:
                import types
                stream = API.RecordStream('h', 'owner', 'c', 0, 'fast')
                drained = threading.Event()
                received, readable = [], [True]
                def fast_page(principal, dispatch, after):
                    if after and readable[0]:
                        readable[0] = drained.wait(0.5)
                        drained.clear()
                    lines = [dict(seq=i, payload='ordinary output ' * 13)
                             for i in range(after + 1, min(100000, after + 512) + 1)]
                    return dict(lines=lines, cursor=lines[-1]['seq'], total=100000, ended=True)
                fake = types.SimpleNamespace(_record_page=fast_page)
                fake._fill_record_locked = lambda *a, **k: API.ControlApi._fill_record_locked(fake, *a, **k)
                def fast_reader():
                    while True:
                        kind, frame = stream.next(1)
                        if kind == 'closed':
                            return
                        if kind == 'frame':
                            received.extend(line['seq'] for line in frame['lines'])
                            drained.set()
                reader = threading.Thread(target=fast_reader)
                reader.start()
                API.ControlApi._fill_record(fake, stream, fast_page('owner', 'fast', 0), always=True)
                reader.join(3)
                stream.close('test_end')
                reader.join(3)
                check('api/fast-catchup', 'reader drains while pages are read and catches up 100k lines',
                      readable[0] and not reader.is_alive() and stream.closed == 'ended'
                      and received == list(range(1, 100001)))

        with region('route/runner-unknown'):
            # Run both runner fallback paths over a real journal-backed dispatch and authority route.
            for state_, reason in (('accepted', 'launch_evidence_missing'), ('running', 'outcome_unknown')):
                original_dispatch = writer.execute('SELECT data FROM entities WHERE id=?',
                                                   ('dispatch:' + main_launch.dispatch_id,)).fetchone()[0]
                dispatch = json.loads(original_dispatch)
                location = Path(ER.path(records_dir, main_launch.dispatch_id)) if ER else None
                original_bytes = location.read_bytes() if location and location.exists() else None
                dispatch.update(state=state_, execution_record=None)
                writer.execute('UPDATE entities SET data=? WHERE id=?',
                               (json.dumps(dispatch), 'dispatch:' + main_launch.dispatch_id))
                launch = L.Launch(None, main_launch.contract, dispatches, time.time)
                launch.records = str(records_dir)
                try:
                    if state_ == 'accepted':
                        launch._settle(lost=True)
                        settled = launch.record
                    else:
                        settled = launch.wait(timeout=0)
                    commitment = settled.get('execution_record')
                    check('route/runner-unknown', reason + ' commits the final bytes',
                          settled.get('state') == 'unknown' and isinstance(commitment, dict)
                          and original_bytes is not None and commitment.get('digest') ==
                          'sha256:' + hashlib.sha256(original_bytes).hexdigest())
                    if original_bytes is not None:
                        location.write_bytes(original_bytes.replace(b'engine', b'Engine', 1))
                        check('route/runner-unknown', reason + ' refuses a changed byte',
                              refusal(page(main_launch.dispatch_id, 0)) == 'unknown_outcome:record_digest')
                finally:
                    if original_bytes is not None:
                        location.write_bytes(original_bytes)
                    writer.execute('UPDATE entities SET data=? WHERE id=?',
                                   (original_dispatch, 'dispatch:' + main_launch.dispatch_id))

        with region('format/fake-lines'):
            events = FORMATS['claude_code']['events']
            extra_events = STREAM['claude_code']['events']
            printed = [json.loads(x) for own in (main_own, planted_own) for x in (own.get('lines') or {}).get('engine') or []]
            bad = []
            for event in printed:
                kind = event.get('type')
                key = {'system': 'system/init', 'result': 'result/success'}.get(kind, kind)
                schema = events.get(key) or extra_events.get(key) or {}
                if kind == 'control_response':
                    continue
                table = schema.get('fields') or {}
                required = {f for f, v in table.items() if not v.get('optional')}
                if not table or set(event) - set(table) or required - set(event):
                    bad.append((key, sorted(set(event) - set(table)), sorted(required - set(event))))
            codex_events = FORMATS['codex']['events']
            for line in (codex_own.get('lines') or {}).get('engine') or []:
                event = json.loads(line)
                table = (codex_events.get(event.get('type')) or {}).get('fields') or {}
                if not table or set(event) - set(table):
                    bad.append((event.get('type'), sorted(set(event) - set(table))))
                item_ = event.get('item')
                if isinstance(item_, dict):
                    fields_ = ((CODEX_ITEMS['items'].get(item_.get('type')) or {}).get('fields')) or {}
                    if not fields_ or set(item_) - set(fields_):
                        bad.append(('item/' + str(item_.get('type')), sorted(set(item_) - set(fields_))))
            stderr_text = STREAM['claude_code']['stderr']['extra_certs']['text'].replace('{path}', missing_certs)
            check('format/fake-lines', 'every event line the fakes printed is one of the binaries\' own schemas with its '
                  'required fields, and each error-stream line the binary\'s own [%d lines, %s]' % (len(printed), bad[:3]),
                  len(printed) >= 15 and not bad and stderr_text in ((main_own.get('lines') or {}).get('stderr') or []))
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
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
                    print('  VELDO-0141 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0141 %s detail: no check ran' % name)
        expect('VELDO-0141 ' + name, ok)
    print('VELDO-0141 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session: the receiver, its systemd tools and this suite's own systemctl reach the user manager
# through /run/user/<uid> for this run when the gate's environment names none.
_v141_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v141_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v141_suite()
finally:
    if _v141_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v141_session
