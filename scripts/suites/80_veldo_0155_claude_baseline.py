"""VELDO-0155: every Claude Code run starts on the everything-off baseline, behind the paid-API guard and the
environment strip.

Run: python3 scripts/selftest.py --suite 80_veldo_0155_claude_baseline

Only shared ROOT and expect are consumed. One temporary tree in the owner's runtime directory holds the
installed .veldo copy the suite loads AND the launch receiver, wrapper and clone entrance execute, so a
registered mutation of a production module reaches all of them. Real: a SQLite control store with OpenSSH
journal signatures, the owner's account records over profiles the local helper prepares, VELDO-0036
reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git source
bound to the store, VELDO-0042 clones confined with Landlock, the VELDO-0039 Runner and receiver processes,
the trusted wrapper and VELDO-0040 transient scopes under the owner's systemd user manager in a slice of
the run's own (stopped, and its failed units cleared, at the end; no unit is installed).

The engine is a fake `claude`, pinned as 2.1.281 by the production `pin` and qualified in this
installation's record with the module's baseline. What it loads is decided by the gates of the binary
itself (proof/VELDO-0155/claude-baseline.json, read out of the 2.1.281 bytes, written into the fake): a
settings file only from an enabled setting source or the `--settings` file, an MCP server of the
profile or the clone only from an enabled source and never under `--strict-mcp-config`, the claude.ai
connectors of the login (a fixture in the profile stands in for the service's answer) only without it,
the bundled and the enabled sources' skills only without `--disable-slash-commands`, the instruction
files only from an enabled source and without CLAUDE_CODE_DISABLE_CLAUDE_MDS, auto memory unless
CLAUDE_CODE_DISABLE_AUTO_MEMORY, the hooks of the loaded settings unless their merge sets
`disableAllHooks`, and an Anthropic profile in XDG_CONFIG_HOME or HOME ahead of the claude.ai login. It
records how it was started, what it loaded (its debug log) and its runtime directory as it found it, then
prints the init event in the binary's own shape (the apiKeySource its packet scripts, else the one its
environment makes), waits, marks its first model turn and prints the turn. No real engine runs, nothing
logs in, no credential exists (every token and key is assembled at run time). Each row is reported once.
"""


def _v155_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import uuid

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    TABLE = json.loads((TREE / 'proof' / 'VELDO-0155' / 'claude-baseline.json').read_text())
    FORMATS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['claude_code']
    OPTIONS = json.loads((TREE / 'proof' / 'VELDO-0060' / 'cli-options.json').read_text())['claude_code']
    VERSION = '2.1.281'
    INPUT = TABLE['input_protocol']
    FLAGS = ['--print', '--output-format', 'stream-json', '--verbose'] + list(INPUT['flags'])

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
    }
    ROWS = ('baseline/qualified', 'baseline/planted-settings', 'baseline/planted-server', 'baseline/planted-skill',
            'baseline/planted-instructions', 'baseline/planted-memory', 'baseline/planted-hook',
            'paid-api/read-back', 'paid-api/token-file', 'paid-api/stop', 'paid-api/every-init', 'paid-api/profile-login',
            'strip/read-back', 'strip/private-runtime-directory', 'strip/user-manager',
            'fixture/planted-control', 'format/fake-lines')
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
    base = Path(tempfile.mkdtemp(prefix='v155-', dir=runtime if os.path.isdir(runtime) else None))
    slice_name = 'v155%s.slice' % os.urandom(4).hex()
    tools = dict(os.environ)
    contained = []
    connections = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v155_store', mods / 'control_store.py')
        L = load('v155_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = getattr(RES, 'ACC', None)
        E = getattr(L, 'ENGINES', {}).get('claude_code')
        HELPER = load('v155_helper', mods / 'accounts.py')
        EL = load('v155_eligibility', mods / 'control_eligibility.py')
        SIG = load('v155_signer', mods / 'control_signer.py')
        GP = load('v155_git', mods / 'git_process.py')
        CL = load('v155_clone', mods / 'control_clone.py')
        CT = load('v155_containment', mods / 'control_containment.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-155', 'repository-155', 'builder-155', 'linux-host-155'
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

        # The owner's Claude Code accounts: a plain one, one configured with a subscription token, one whose
        # token file anybody can read, one per Anthropic profile row, and one whose login a fixture scripts.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign) if ACC else None
        helper_root = base / 'helper'
        profiles = {}
        ACCOUNTS = ('acct-155a', 'acct-155t', 'acct-155u', 'acct-155h', 'acct-155x', 'acct-155k')
        for account in ACCOUNTS:
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider='claude_code'))
            profiles[account] = (record or {}).get('config_dir')
            fields, _ = attempt(lambda: HELPER.registration(account, host=HOST, root=str(helper_root)))
            if fields and accounts is not None:
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=time.time())
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        for account in profiles:
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        put('project:journey-155', 'project', dict(name='journey-155'))
        reservations.configure('policy/journey-155', 'project', 'journey-155', dict(BIG), now=time.time())

        def admitted(unit):
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project='journey-155',
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

        # THE PLANTED ITEMS. In the source repository, so every clone carries them: project and local settings
        # (a planted output style and a hook), a project MCP server, a project skill and a project CLAUDE.md.
        PLANTED_STYLE = 'v155-planted-style'
        SERVERS = {'profile': 'v155-profile-server', 'clone': 'v155-clone-server', 'connector': 'v155-claudeai-connector'}
        SKILLS = {'profile': 'v155-profile-skill', 'clone': 'v155-clone-skill'}
        HOOKS = {'profile': 'echo v155-profile-hook', 'clone': 'echo v155-clone-hook'}
        CONNECTORS = 'v155-claudeai-connectors.json'
        LOGIN = 'v155-login.json'

        def hooked(command):
            return {'SessionStart': [{'hooks': [{'type': 'command', 'command': command}]}]}
        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / '.claude' / 'skills' / SKILLS['clone']).mkdir(parents=True)
        (src / '.claude' / 'settings.json').write_text(json.dumps({'outputStyle': PLANTED_STYLE,
                                                                   'hooks': hooked(HOOKS['clone'])}))
        (src / '.claude' / 'settings.local.json').write_text(json.dumps({'outputStyle': PLANTED_STYLE}))
        (src / '.claude' / 'skills' / SKILLS['clone'] / 'SKILL.md').write_text('---\nname: %s\n---\nplanted\n'
                                                                                % SKILLS['clone'])
        (src / '.mcp.json').write_text(json.dumps({'mcpServers': {SERVERS['clone']: {'command': 'true'}}}))
        (src / 'CLAUDE.md').write_text('v155 planted project instructions\n')
        (src / 'README').write_text('baseline source\n')
        # What a relative XDG_CONFIG_HOME and a relative credentials_path reach: in the clone, the engine's
        # working directory, where the binary resolves them.
        RELATIVE_XDG, RELATIVE_CREDENTIALS = 'v155-relative', 'v155-relative-credentials.json'
        (src / RELATIVE_XDG / 'anthropic' / 'configs').mkdir(parents=True)
        (src / RELATIVE_XDG / 'anthropic' / 'configs' / 'default.json').write_text(
            json.dumps({'authentication': {'type': 'oidc_federation'}}))
        (src / RELATIVE_CREDENTIALS).write_text('v155 planted relative profile credentials\n')
        # Forced: a local settings file is one a user's global excludes may ignore.
        GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # In every account profile: user settings (the planted style and a hook), a user MCP server, the claude.ai
        # connectors of its login, a user skill and a user CLAUDE.md; its auto memory is planted per clone below.
        def plant_profile(directory):
            directory = Path(directory)
            (directory / 'skills' / SKILLS['profile']).mkdir(parents=True, exist_ok=True)
            (directory / 'settings.json').write_text(json.dumps({'outputStyle': PLANTED_STYLE,
                                                                 'hooks': hooked(HOOKS['profile'])}))
            (directory / '.claude.json').write_text(json.dumps({'mcpServers': {SERVERS['profile']: {'command': 'true'}}}))
            (directory / CONNECTORS).write_text(json.dumps({'connectors': [SERVERS['connector']]}))
            (directory / 'skills' / SKILLS['profile'] / 'SKILL.md').write_text('---\nname: %s\n---\nplanted\n'
                                                                              % SKILLS['profile'])
            (directory / 'CLAUDE.md').write_text('v155 planted profile instructions\n')
        for directory in profiles.values():
            if directory:
                plant_profile(directory)

        def slug(path):
            return ''.join(c if c.isalnum() else '-' for c in str(path))

        def plant_memory(directory, work):
            memory = Path(directory) / 'projects' / slug(work) / 'memory'
            memory.mkdir(parents=True, exist_ok=True)
            (memory / 'MEMORY.md').write_text('v155 planted auto memory\n')

        # The fake engine: what it may load is the binary's own gate table, written into it.
        markers = base / 'markers'
        markers.mkdir()
        fake_table = {'bundled': list(TABLE['bundled_skills'][:2]), 'connectors': CONNECTORS, 'login': LOGIN,
                      'profile_types': list(TABLE['profile']['types']['values']), 'version': VERSION,
                      'subscription_provider': INPUT['providers']['subscription'],
                      'subscription': INPUT['subscriptions']['values'][2]}
        fake = '''#!@@PYTHON@@ -B
import json, os, sys, time, uuid
from pathlib import Path
markers, TABLE = Path(@@MARKERS@@), json.loads(@@TABLE@@)
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
def option(name):
    for at, arg in enumerate(argv):
        if arg == name:
            return argv[at + 1] if at + 1 < len(argv) else None
        if arg.startswith(name + '='):
            return arg[len(name) + 1:]
    return None
def truthy(value):
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'on')
def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError, TypeError):
        return None
def read_text(path):
    try:
        return Path(path).read_text()
    except OSError:
        return None
profile = Path(env.get('CLAUDE_CONFIG_DIR') or Path(env.get('HOME', '/nonexistent')) / '.claude')
given = option('--setting-sources')
sources = ['user', 'project', 'local'] if given is None else [s.strip() for s in given.split(',') if s.strip()]
layers = []
for source, path in (('user', profile / 'settings.json'), ('project', cwd / '.claude' / 'settings.json'),
                     ('local', cwd / '.claude' / 'settings.local.json')):
    data = read_json(path)
    if source in sources and isinstance(data, dict):
        layers.append([source, str(path), data])
flag_path = option('--settings')
flag_settings = read_json(flag_path) if flag_path else None
if isinstance(flag_settings, dict):
    layers.append(['flag', flag_path, flag_settings])
merged = {}
for _, _, data in layers:
    merged.update(data)
hooks = [] if merged.get('disableAllHooks') is True else [[s, p, d['hooks']] for s, p, d in layers if d.get('hooks')]
strict = '--strict-mcp-config' in argv
mcp_path = option('--mcp-config')
mcp_config = read_json(mcp_path) if mcp_path else None
servers = [{'name': n, 'status': 'connected', 'source': 'dynamic'} for n in sorted((mcp_config or {}).get('mcpServers') or {})]
if not strict:
    if 'user' in sources:
        servers += [{'name': n, 'status': 'connected', 'source': 'user'}
                    for n in sorted((read_json(profile / '.claude.json') or {}).get('mcpServers') or {})]
    if 'project' in sources:
        servers += [{'name': n, 'status': 'connected', 'source': 'project'}
                    for n in sorted((read_json(cwd / '.mcp.json') or {}).get('mcpServers') or {})]
    servers += [{'name': n, 'status': 'connected', 'source': 'claudeai'}
                for n in sorted((read_json(profile / TABLE['connectors']) or {}).get('connectors') or [])]
skills = []
if '--disable-slash-commands' not in argv:
    skills += list(TABLE['bundled'])
    if 'user' in sources:
        skills += sorted(p.name for p in (profile / 'skills').glob('*') if (p / 'SKILL.md').is_file())
    if 'project' in sources:
        skills += sorted(p.name for p in (cwd / '.claude' / 'skills').glob('*') if (p / 'SKILL.md').is_file())
instructions = []
if not truthy(env.get('CLAUDE_CODE_DISABLE_CLAUDE_MDS')):
    if 'user' in sources and (profile / 'CLAUDE.md').is_file():
        instructions.append(str(profile / 'CLAUDE.md'))
    if 'project' in sources and (cwd / 'CLAUDE.md').is_file():
        instructions.append(str(cwd / 'CLAUDE.md'))
memory_on = not truthy(env.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY')) and merged.get('autoMemoryEnabled', True) is not False
memory_dir = profile / 'projects' / ''.join(c if c.isalnum() else '-' for c in str(cwd)) / 'memory'
memory = [str(memory_dir / 'MEMORY.md')] if memory_on and (memory_dir / 'MEMORY.md').is_file() else []
xdg, home = (env.get('XDG_CONFIG_HOME') or '').strip(), (env.get('HOME') or '').strip()
store = env.get('ANTHROPIC_CONFIG_DIR') or (str(Path(xdg) / 'anthropic') if xdg else str(Path(home) / '.config' / 'anthropic') if home else None)
auth = 'claude.ai'
if store:
    active = (read_text(Path(store) / 'active_config') or '').strip() or 'default'
    config = (read_json(Path(store) / 'configs' / (active + '.json')) or {}).get('authentication') or {}
    kind = config.get('type')
    # A user_oauth profile counts only with its credentials (relative paths are the process's own, as here).
    credentials = config.get('credentials_path') or str(Path(store) / 'credentials' / (active + '.json'))
    if kind in TABLE['profile_types'] and (kind != 'user_oauth' or (read_text(credentials) or '').strip()):
        auth = 'profile'
# The login the binary's Mc() finds: a token the environment names, else the profile, else claude.ai. What its
# key lookup and backend switches find in the profile (a key helper, a managed key, a cloud backend) a fixture
# of the profile states, standing in for them.
login = read_json(profile / TABLE['login']) or {}
if auth == 'claude.ai' and env.get('CLAUDE_CODE_OAUTH_TOKEN'):
    auth = 'CLAUDE_CODE_OAUTH_TOKEN'
source = login.get('tokenSource') or auth
key = login.get('apiKeySource') or ('ANTHROPIC_API_KEY' if env.get('ANTHROPIC_API_KEY') else None)
api_key_source = key or 'none'
provider = login.get('apiProvider') or TABLE['subscription_provider']
# Kfe(): the account the initialize answer carries.
account = {'apiProvider': provider}
if provider == TABLE['subscription_provider']:
    if source in ('CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR'):
        account['tokenSource'] = source
    elif source == 'claude.ai' and key is None and login.get('subscriber', True):
        account['subscriptionType'] = login.get('subscription', TABLE['subscription'])
    elif source != 'profile':
        account['tokenSource'] = source
    if key:
        account['apiKeySource'] = key
place = env.get('XDG_RUNTIME_DIR')
try:
    info = os.stat(place)
    runtime = {'path': place, 'dir': os.path.isdir(place), 'entries': sorted(os.listdir(place)),
               'mode': info.st_mode & 0o7777, 'uid': info.st_uid}
except (OSError, TypeError):
    runtime = {'path': place, 'dir': False}
def start(pid):
    stat = open('/proc/%d/stat' % pid).read()
    return stat[stat.rindex(')') + 2:].split()[19]
own = {'pid': os.getpid(), 'start': start(os.getpid()), 'dispatch': env.get('VELDO_DISPATCH_ID', ''), 'argv': sys.argv,
       'cwd': str(cwd), 'names': sorted(env), 'runtime': runtime,
       'env': {k: env.get(k) for k in ('CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS',
                                       'CLAUDE_CODE_DISABLE_AUTO_MEMORY', 'DISABLE_AUTOUPDATER', 'XDG_RUNTIME_DIR', 'HOME')},
       'cgroup': next((l[3:] for l in open('/proc/self/cgroup').read().splitlines() if l.startswith('0::')), None),
       'files': {'settings': flag_settings, 'mcp': mcp_config},
       'debug': {'sources': sources, 'settings_files': [p for _, p, _ in layers], 'hooks': hooks, 'servers': servers,
                 'skills': skills, 'instructions': instructions, 'memory': memory, 'memory_on': memory_on,
                 'strict': strict, 'auth': auth, 'api_key_source': api_key_source, 'account': account}}
(markers / ('%d.tmp' % os.getpid())).write_text(json.dumps(own))
(markers / ('%d.tmp' % os.getpid())).rename(markers / ('%d.json' % os.getpid()))
out = open(markers / ('%d.out' % os.getpid()), 'w')
def emit(event):
    text = json.dumps(event)
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def note(kind, data):
    with open(markers / ('%d.input' % os.getpid()), 'a') as handle:
        handle.write(json.dumps([kind, data]) + chr(10))
# Stream JSON input as the binary reads it: the initialize control request answered with the account, the user
# message's content the prompt; the input closing with no prompt ends the run with nothing printed. Without
# --input-format stream-json the whole input is the prompt.
if option('--input-format') == 'stream-json':
    packet = None
    while packet is None:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get('type') == 'control_request' and (message.get('request') or {}).get('subtype') == 'initialize':
            note('initialize', message['request_id'])
            emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                                                           'response': {'account': account, 'pid': os.getpid()}}})
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            note('user', content)
            packet = json.loads(content) if content.strip() else {}
    if packet is None:
        out.close()
        sys.exit(0)
else:
    raw = sys.stdin.buffer.read()
    note('text', raw.decode())
    packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
session = 'session-155-' + uuid.uuid4().hex[:8]
usage = {'input_tokens': 3, 'output_tokens': 2, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
# One init event per turn, each with the apiKeySource the packet scripts, else the one the login makes.
turns = 0
for scripted in payload.get('inits') or [api_key_source]:
    init = {'type': 'system', 'subtype': 'init', 'cwd': str(cwd), 'session_id': session, 'tools': ['Read', 'Edit', 'Bash'],
            'mcp_servers': servers, 'model': 'configured-model', 'permissionMode': 'default', 'slash_commands': skills,
            'apiKeySource': scripted, 'claude_code_version': TABLE['version'],
            'output_style': merged.get('outputStyle', 'default'), 'agents': [], 'skills': skills, 'plugins': [],
            'uuid': str(uuid.uuid4())}
    if memory_on:
        init['memory_paths'] = {'auto': str(memory_dir)}
    emit(init)
    time.sleep(float(payload.get('turn_delay', 0)))
    # Here the real engine sends a model request: marked, so a stop before it is seen.
    with open(markers / ('%d.turn' % os.getpid()), 'a') as handle:
        handle.write('a turn' + chr(10))
    turns += 1
    emit({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()), 'session_id': session,
          'message': {'id': 'msg-' + uuid.uuid4().hex[:8], 'type': 'message', 'role': 'assistant',
                      'model': 'configured-model', 'content': [], 'stop_reason': None, 'stop_sequence': None,
                      'usage': usage}})
emit({'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False, 'num_turns': turns,
      'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0, 'usage': usage,
      'modelUsage': {'configured-model': {'inputTokens': 3 * turns, 'outputTokens': 2 * turns, 'cacheReadInputTokens': 0,
                                          'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                          'contextWindow': 200000, 'maxOutputTokens': 32000}},
      'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session})
out.close()
(markers / ('%d.done' % os.getpid())).write_text('done')
'''.replace('@@PYTHON@@', sys.executable).replace('@@MARKERS@@', repr(str(markers))).replace(
            '@@TABLE@@', repr(json.dumps(fake_table)))
        versions = base / 'home' / '.local' / 'share' / 'claude' / 'versions'
        versions.mkdir(parents=True)
        (versions / VERSION).write_text(fake)
        (versions / VERSION).chmod(0o755)
        FAKE_SHA = file_sha(versions / VERSION)
        test_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {
            VERSION: {'sha256': FAKE_SHA, 'flags': list(FLAGS), 'environment': {'DISABLE_AUTOUPDATER': '1'}}}}
        if getattr(E, 'BASELINE', None) is not None:
            test_record['versions'][VERSION]['baseline'] = E.BASELINE
            if hasattr(E, 'session_environment'):
                test_record['versions'][VERSION]['session_environment'] = E.session_environment(versions / VERSION)
        (mods / 'runtime').mkdir()
        record_path = mods / 'runtime' / 'claude-qualification.json'
        record_path.write_text(json.dumps(test_record, indent=1))
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        pinned = factory / 'engines' / 'claude_code' / VERSION
        pinned_binding, pin_error = attempt(lambda: E.pin(VERSION, versions=str(versions), state_root=str(factory)))
        if not pinned.exists():
            # A tree whose pin refuses this record: the copy the launches would bind, for its rows to red by assertion.
            pinned.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(versions / VERSION, pinned)
            pinned.chmod(0o555)

        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        shim = base / 'systemd-run'
        shim.write_text('#!/bin/sh\nprintf %%s "$VELDO_DISPATCH_ID" > "%s/spawn-$$"\nexec %s "$@"\n'
                        % (markers, real_systemd_run))
        shim.chmod(0o755)
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4, 'systemd_run': str(shim)}
        # The subscription token of acct-155t, a file of this account's own nobody else reads; acct-155u's
        # anybody can read. Assembled at run time: no credential exists.
        subscription_value = 'v155-subscription-' + os.urandom(8).hex()
        tokens = state / 'tokens'
        tokens.mkdir(mode=0o700)
        (tokens / 'acct-155t').write_text(subscription_value + '\n')
        (tokens / 'acct-155t').chmod(0o600)
        (tokens / 'acct-155u').write_text('v155-readable-' + os.urandom(8).hex() + '\n')
        (tokens / 'acct-155u').chmod(0o644)
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '--']
        config = base / 'receiver.json'
        receiver_config = {
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(state / 'receipts'), 'artifacts': str(state / 'artifacts'),
            'state_root': str(factory), 'profile': profile,
            'subscription_tokens': {'acct-155t': str(tokens / 'acct-155t'), 'acct-155u': str(tokens / 'acct-155u')},
            'adapters': {'claude': {'engine': 'claude_code', 'executable': {'version': VERSION}, 'argv': entering}}}
        config.write_text(json.dumps(receiver_config))

        # The receiver's environment: the owner's, with the SSH agent, the session bus (the real one, which the
        # receiver's own systemd tools may use) and the Git tokens planted, and every paid-API name planted.
        def planted(name):
            return 'v155-planted-%s-%s' % (name.lower(), os.urandom(4).hex())
        STRIPPED = ('SSH_AUTH_SOCK', 'SSH_AGENT_PID', 'DBUS_SESSION_BUS_ADDRESS', 'GH_TOKEN', 'GITHUB_TOKEN')
        PAID = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX',
                'CLAUDE_CODE_USE_FOUNDRY', 'CLAUDE_CODE_OAUTH_TOKEN')
        RECEIVER_ENV = dict(os.environ)
        for name in STRIPPED + PAID:
            RECEIVER_ENV[name] = planted(name)
        RECEIVER_ENV['SSH_AUTH_SOCK'] = str(base / 'agent.sock')
        RECEIVER_ENV['SSH_AGENT_PID'] = str(os.getpid())
        RECEIVER_ENV['DBUS_SESSION_BUS_ADDRESS'] = os.environ.get('DBUS_SESSION_BUS_ADDRESS') or 'unix:path=%s/bus' % runtime
        environments = [RECEIVER_ENV]

        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        clones, _ = attempt(lambda: CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root),
                                              protected=[str(private)], engines=[str(factory / 'engines')]))
        if clones is None:
            clones = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)])
        provisioned = {}

        def invoke(contract):
            handle = clones.create(contract)
            provisioned[contract['dispatch_id']] = handle
            account = contract['reservation']['account']
            if profiles.get(account):
                plant_memory(profiles[account], clones._paths(handle)['work'])
            launch = L.invoke(config, contract, dispatches, accept_seconds=30, environment=environments[0])
            contained.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]
        CONFIGURATION = {'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}
        units = [0]

        def run(account, delay=0.0, inits=None, environment=None, login=None):
            units[0] += 1
            payload = {'task': 'work the unit', 'turn_delay': delay}
            if inits is not None:
                payload['inits'] = list(inits)
            # The login fixture of the account's profile: what the binary's key lookup and backend switches find.
            fixture = Path(profiles.get(account) or '/nonexistent') / LOGIN
            if login is not None:
                fixture.write_text(json.dumps(login))
            elif fixture.exists():
                fixture.unlink()
            environments[0] = environment or RECEIVER_ENV
            try:
                launch = runner(account).submit(admitted('VELDO-155%02d' % units[0]), 'build', holder=HOLDER, source=str(src),
                                                revision='HEAD', payload=payload, adapter='claude',
                                                configuration=CONFIGURATION, deadline=time.time() + 40)
                record = runner(account).wait(launch)
            finally:
                environments[0] = RECEIVER_ENV
            return launch, record or {}

        def own_of(dispatch_id):
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    turned = markers / ('%d.turn' % data['pid'])
                    data['turns'] = len(turned.read_text().splitlines()) if turned.exists() else 0
                    data['turned'] = data['turns'] > 0
                    given = markers / ('%d.input' % data['pid'])
                    data['input'] = [json.loads(x) for x in given.read_text().splitlines()] if given.exists() else []
                    data['prompted'] = any(kind in ('user', 'text') for kind, _ in data['input'])
                    out = markers / ('%d.out' % data['pid'])
                    data['printed'] = [json.loads(x) for x in out.read_text().splitlines()] if out.exists() else []
                    return data
            return {}

        def spawned(dispatch_id):
            return len([p for p in markers.glob('spawn-*') if p.read_text() == dispatch_id])

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def history(dispatch_id):
            return [h.get('state') for h in rec(dispatch_id).get('history') or []]

        def invocation(dispatch_id):
            found = entity(RES.entity('invocation', [DOMAIN, 'invocation/' + dispatch_id]))
            return (found or {}).get('data') or {}

        def artifact(launch):
            report = getattr(launch, 'artifact', None) or {}
            path = Path(report.get('path') or '/nonexistent')
            return json.loads(path.read_text()) if path.is_file() else {}

        def reported(launch):
            return next((m.get('baseline') for m in getattr(launch, 'messages', []) or []
                         if isinstance(m, dict) and m.get('event') == 'baseline'), None) or {}

        def init_of(own):
            return next((e for e in own.get('printed') or [] if e.get('type') == 'system'), {})

        # The launches: the normal run, a second run of it, the token account's, the unreadable token file's,
        # one per login the initialize answer can name that is not a subscription, one whose second init event
        # names an API key, and the Anthropic profile logins, absolute and relative.
        normal_launch, normal_record = run('acct-155a', delay=0.3)
        normal = own_of(normal_launch.dispatch_id)
        second_launch, second_record = run('acct-155a')
        second = own_of(second_launch.dispatch_id)
        token_launch, token_record = run('acct-155t', delay=0.3)
        token_own = own_of(token_launch.dispatch_id)
        bad_launch, bad_record = run('acct-155u')
        sources = [s for s in TABLE['api_key_sources'] if s != 'none']
        providers = [v for v in INPUT['providers']['values'] if v != INPUT['providers']['subscription']]
        token_sources = [v for v in INPUT['token_sources']['values'] if v != INPUT['token_sources']['subscription_token']]
        # Each scripted login: (name, the fixture, the stop it must make). The answer of a profile login names
        # neither a subscription nor a token; a token source is one found where the binary finds no subscriber.
        LOGINS = ([('apiKeySource:' + v, {'apiKeySource': v}, 'paid_api:apiKeySource:' + v) for v in sources]
                  + [('apiProvider:' + v, {'apiProvider': v}, 'paid_api:apiProvider:' + v) for v in providers]
                  + [('tokenSource:' + v, {'tokenSource': v, 'subscriber': False}, 'paid_api:tokenSource:' + v)
                     for v in token_sources]
                  + [('profile', {'tokenSource': 'profile'}, 'paid_api:subscriptionType:None')]
                  + [('subscriptionType:' + v, {'subscription': v}, 'paid_api:subscriptionType:' + v)
                     for v in INPUT['subscriptions']['values'] if v not in INPUT['subscriptions']['values'][:4]])
        stops = {name: (run('acct-155k', delay=2.0, login=fixture), stop) for name, fixture, stop in LOGINS}
        later_launch, later_record = run('acct-155a', delay=0.3, inits=['none', sources[0]])
        later = own_of(later_launch.dispatch_id)
        fake_home, fake_xdg = base / 'fake-home', base / 'fake-xdg'
        for store, kind in ((fake_home / '.config' / 'anthropic', 'user_oauth'), (fake_xdg / 'anthropic', 'oidc_federation')):
            (store / 'configs').mkdir(parents=True)
            (store / 'credentials').mkdir()
            (store / 'configs' / 'default.json').write_text(json.dumps({'authentication': {'type': kind}}))
            (store / 'credentials' / 'default.json').write_text('v155 planted profile credentials\n')
        relative_home = base / 'fake-home-relative'
        (relative_home / '.config' / 'anthropic' / 'configs').mkdir(parents=True)
        (relative_home / '.config' / 'anthropic' / 'configs' / 'default.json').write_text(
            json.dumps({'authentication': {'type': 'user_oauth', 'credentials_path': RELATIVE_CREDENTIALS}}))
        # The profile environments: (reached through, environment, the type it plants).
        PROFILE_ENVS = {'user_oauth': ('HOME', {'HOME': str(fake_home)}),
                        'oidc_federation': ('XDG_CONFIG_HOME', {'XDG_CONFIG_HOME': str(fake_xdg)}),
                        'relative XDG_CONFIG_HOME': ('XDG_CONFIG_HOME relative', {'XDG_CONFIG_HOME': RELATIVE_XDG}),
                        'relative credentials_path': ('HOME, credentials relative', {'HOME': str(relative_home)})}
        PROFILE_TYPE = {'user_oauth': 'user_oauth', 'oidc_federation': 'oidc_federation',
                        'relative XDG_CONFIG_HOME': 'oidc_federation', 'relative credentials_path': 'user_oauth'}
        profile_runs = {name: run('acct-155x' if 'XDG' in how else 'acct-155h', delay=0.3,
                                  environment=dict(RECEIVER_ENV, **extra))
                        for name, (how, extra) in PROFILE_ENVS.items()}
        run_dirs_after = {name: os.path.exists(reported(launch).get('run', {}).get('root') or '/nonexistent/x')
                          for name, launch in (('normal', normal_launch), ('second', second_launch))}

        # The unguarded control: the same fake started directly, with no baseline, in a clone of the same source
        # and the same profile, and once more under each planted Anthropic profile.
        control_work = base / 'control-work'
        GP.run(['git', 'clone', '-q', str(src), str(control_work)], check=True, capture_output=True)
        plant_memory(profiles['acct-155a'], control_work)

        def control(extra_env=None, handshake=False):
            env = {'PATH': os.environ.get('PATH', os.defpath), 'HOME': str(base / 'home'), 'LANG': 'C.UTF-8',
                   'CLAUDE_CONFIG_DIR': profiles['acct-155a'], 'VELDO_DISPATCH_ID': 'control-%s' % uuid.uuid4().hex,
                   'XDG_RUNTIME_DIR': runtime}
            env.update(extra_env or {})
            # The prompt as the user message of stream JSON input, after the initialize request for the handshake's
            # own control.
            prompt = json.dumps({'type': 'user', 'message': {'role': 'user', 'content': '{}'}, 'parent_tool_use_id': None})
            request = json.dumps({'type': 'control_request', 'request_id': 'v155-control',
                                  'request': {'subtype': 'initialize'}})
            given = ((request + '\n') if handshake else '') + prompt + '\n'
            done = subprocess.run([str(versions / VERSION)] + FLAGS, cwd=str(control_work), env=env,
                                  input=given.encode(), capture_output=True, timeout=30)
            return own_of(env['VELDO_DISPATCH_ID']), done.returncode
        unguarded, unguarded_code = control()
        shaken, _ = control(handshake=True)
        profile_controls = {name: control(extra) for name, (_, extra) in PROFILE_ENVS.items()}

        # A version whose record does not list the baseline: refused before acceptance, nothing spawned.
        installed_record = record_path.read_bytes()
        record_path.write_text(json.dumps({'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code',
                                           'versions': {VERSION: dict(test_record['versions'][VERSION], baseline=None)}}))
        try:
            unqualified_launch, unqualified_record = run('acct-155a')
        finally:
            record_path.write_bytes(installed_record)
        # A version whose record does not qualify stream JSON input: refused before acceptance, nothing spawned.
        record_path.write_text(json.dumps({'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code',
                                           'versions': {VERSION: dict(test_record['versions'][VERSION],
                                                                      flags=FLAGS[:-len(INPUT['flags'])])}}))
        try:
            textual_launch, textual_record = run('acct-155a')
        finally:
            record_path.write_bytes(installed_record)

        debug = normal.get('debug') or {}
        init = init_of(normal)
        names_of = lambda servers: {s.get('name') for s in servers or []}

        # AC1: the everything-off baseline, one row per planted item.
        with region('baseline/qualified'):
            argv = normal.get('argv') or []
            settings_path = next((argv[i + 1] for i, a in enumerate(argv[:-1]) if a == '--settings'), None)
            config_dir = str(Path(settings_path).parent) if settings_path else None
            switches = TABLE['switches']
            expected = (FLAGS + [switches['setting_sources']['name'], switches['setting_sources']['value'],
                                 '--settings', '%s/settings.json' % config_dir, '--mcp-config', '%s/mcp.json' % config_dir,
                                 switches['strict_mcp_config']['name'], switches['disable_slash_commands']['name']])
            check('baseline/qualified', 'the run started from the pinned copy with the qualified flags and then exactly '
                  'the baseline, every option one the binary declares: no setting source, the run\'s --settings and '
                  '--mcp-config files, strict MCP and slash commands off [%s]' % argv[1:],
                  normal_record.get('state') == 'exited' and argv[:1] == [str(pinned)] and argv[1:] == expected
                  and all(a in OPTIONS['options'] for a in argv[1:] if a.startswith('--'))
                  and config_dir is not None and '--bare' not in argv and '--safe-mode' not in argv)
            env = normal.get('env') or {}
            files = normal.get('files') or {}
            check('baseline/qualified', 'the generated files are the run\'s own: its settings turn every hook off and its '
                  'MCP configuration lists no server; both instruction files and auto memory are off by the binary\'s '
                  'own switches [%s, %s, %s]' % (files, env.get('CLAUDE_CODE_DISABLE_CLAUDE_MDS'),
                                                 env.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY')),
                  files.get('settings') == {switches['disable_all_hooks']['name']: True}
                  and files.get('mcp') == {'mcpServers': {}}
                  and env.get(switches['disable_claude_mds']['name']) == '1'
                  and env.get(switches['disable_auto_memory']['name']) == '1')
            shipped = json.loads((ROOT / 'engine' / 'runtime' / 'claude-qualification.json').read_text())
            entry = (shipped.get('versions') or {}).get(VERSION) or {}
            named = set((entry.get('baseline') or {}).get('options') or []) | set(((entry.get('baseline') or {})
                                                                                  .get('environment') or {}))
            check('baseline/qualified', 'the shipped 2.1.281 record qualifies the version with the module\'s baseline, '
                  'every switch in it one the binary\'s own table reads [%s]' % sorted(named),
                  entry.get('baseline') == getattr(E, 'BASELINE', None) and entry.get('baseline') is not None
                  # VELDO-0165: LANG and TERM are the configured locale and terminal, set after the wrapper's strip,
                  # not switches of the binary's table.
                  and named - {'', 'LANG', 'TERM'} <= {s['name'] for s in switches.values()}
                  and (entry.get('baseline') or {}).get('settings') == {'disableAllHooks': True})
            check('baseline/qualified', 'a version whose record does not list the baseline is refused by name before '
                  'acceptance, nothing spawned [%s]' % unqualified_record.get('refusal'),
                  unqualified_record.get('refusal') == 'missing_evidence:engine_baseline:' + VERSION
                  and history(unqualified_launch.dispatch_id) == ['prepared', 'refused']
                  and not spawned(unqualified_launch.dispatch_id))

        with region('baseline/planted-settings'):
            check('baseline/planted-settings', 'no settings file of the profile or the clone loaded: only the run\'s own '
                  '(user, project and local sources off), and the planted output style is not the run\'s [%s, %s]'
                  % (debug.get('settings_files'), init.get('output_style')),
                  bool(debug) and debug.get('sources') == [] and len(debug.get('settings_files') or []) == 1
                  and str((debug.get('settings_files') or [''])[0]).endswith('/config/settings.json')
                  and init.get('output_style') != PLANTED_STYLE and init.get('output_style') == 'default')

        with region('baseline/planted-server'):
            check('baseline/planted-server', 'no MCP server of the profile, the clone or the login\'s claude.ai '
                  'connectors is in the init event\'s list, which holds exactly the run\'s (none) [%s]'
                  % init.get('mcp_servers'),
                  'mcp_servers' in init and init.get('mcp_servers') == [] and debug.get('strict') is True
                  and not names_of(init.get('mcp_servers')) & set(SERVERS.values()))

        with region('baseline/planted-skill'):
            listed = set(init.get('skills') or []) | set(init.get('slash_commands') or [])
            check('baseline/planted-skill', 'no skill of the profile or the clone, and none the binary bundles, is in the '
                  'init event\'s skills or slash commands [%s]' % sorted(listed),
                  'skills' in init and 'slash_commands' in init and not listed)

        with region('baseline/planted-instructions'):
            check('baseline/planted-instructions', 'no instruction file of the profile or the clone loaded, per the '
                  'debug log [%s]' % debug.get('instructions'),
                  bool(debug) and debug.get('instructions') == [])

        with region('baseline/planted-memory'):
            check('baseline/planted-memory', 'auto memory is off: the init event names no memory directory and the '
                  'planted MEMORY.md did not load [%s, %s]' % (init.get('memory_paths'), debug.get('memory')),
                  bool(init) and 'memory_paths' not in init and debug.get('memory_on') is False and debug.get('memory') == [])

        with region('baseline/planted-hook'):
            check('baseline/planted-hook', 'no hook of the profile or the clone registered, per the debug log [%s]'
                  % debug.get('hooks'), bool(debug) and debug.get('hooks') == [])

        # AC2: no paid-API credential reaches the engine; an account's own subscription token does.
        with region('paid-api/read-back'):
            names = set(normal.get('names') or [])
            check('paid-api/read-back', 'planted in the caller\'s environment, none of the API keys, bearer token, '
                  'Bedrock, Vertex and Foundry switches or the subscription token reached the plain account\'s engine '
                  '[%s]' % sorted(names & set(PAID)), bool(names) and not names & set(PAID))
            token_names = set(token_own.get('names') or [])
            got = (token_own.get('env') or {}).get('CLAUDE_CODE_OAUTH_TOKEN')
            check('paid-api/read-back', 'the account configured with a subscription token ran with that account\'s own '
                  'token as CLAUDE_CODE_OAUTH_TOKEN, never the caller\'s, and with no other of the planted names [%s]'
                  % sorted(token_names & set(PAID)),
                  token_record.get('state') == 'exited' and got == subscription_value and got != RECEIVER_ENV['CLAUDE_CODE_OAUTH_TOKEN']
                  and token_names & set(PAID) == {'CLAUDE_CODE_OAUTH_TOKEN'})
            report, token_report = reported(normal_launch), reported(token_launch)
            text = json.dumps([report, token_report])
            check('paid-api/read-back', 'the receiver reported the names it removed, never a value: every planted name '
                  'for the plain account, the token account\'s token named as configured [%s]'
                  % sorted(set(report.get('removed') or []) & set(PAID)),
                  set(PAID) <= set(report.get('removed') or []) and token_report.get('token') is True
                  and subscription_value not in text and not any(RECEIVER_ENV[n] in text for n in PAID))

        with region('paid-api/token-file'):
            check('paid-api/token-file', 'an account whose token file anybody can read is refused by name before '
                  'acceptance, nothing spawned or reserved [%s]' % bad_record.get('refusal'),
                  bad_record.get('refusal') == 'missing_authority:subscription_token:acct-155u'
                  and history(bad_launch.dispatch_id) == ['prepared', 'refused'] and not spawned(bad_launch.dispatch_id)
                  and not invocation(bad_launch.dispatch_id))

        # AC3: a run not on a subscription login is stopped by name before its first turn: the prompt is held until
        # the initialize answer names a subscription login, and every init event is read.
        with region('paid-api/stop'):
            for name, ((launch, record), stop) in stops.items():
                own = own_of(launch.dispatch_id)
                found = artifact(launch)
                check('paid-api/stop', '%s: the run whose initialize answer names it is stopped by name before any '
                      'prompt is written, no init and no model turn: stopped for its login, the invocation cancelled '
                      '[%s, %s, %s, %s]' % (name, (launch.supervision or {}).get('cause'), (found.get('login') or {}).get('stop'),
                                            [k for k, _ in own.get('input') or []], own.get('turns')),
                      bool(own) and [k for k, _ in own.get('input') or []] == ['initialize'] and own.get('prompted') is False
                      and not init_of(own) and own.get('turned') is False
                      and record.get('state') == 'exited' and (launch.supervision or {}).get('cause') == 'paid_api'
                      and (found.get('login') or {}).get('stop') == stop
                      and found.get('verdict') == 'stopped' and invocation(launch.dispatch_id).get('outcome') == 'cancelled')
            check('paid-api/stop', 'every login the binary\'s answer can name that is not a subscription was fed: each '
                  'apiKeySource other than none, each backend but the first-party one, each token source but the '
                  'account\'s own subscription token, an Anthropic profile, and each subscriptionType label but the '
                  'Enterprise, Team, Max and Pro ones (the binary\'s default "Claude API") [%d]' % len(stops),
                  len(stops) == (len(TABLE['api_key_sources']) - 1) + (len(INPUT['providers']['values']) - 1)
                  + (len(INPUT['token_sources']['values']) - 1) + 1 + (len(INPUT['subscriptions']['values']) - 4)
                  and len(sources) >= 8 and len(providers) >= 7
                  and 'subscriptionType:Claude API' in stops and INPUT['subscriptions']['values'][:4]
                  == ['Claude Enterprise', 'Claude Team', 'Claude Max', 'Claude Pro'])
            # The four subscription labels confirm the login in the production Guard, each fed the binary's answer.
            def confirmed(label):
                guard = E.Guard()
                guard.opening(b'{}')
                answer = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': guard.request_id,
                          'response': {'account': {'subscriptionType': label, 'apiProvider': 'firstParty'}}}}
                stopped = guard.feed((json.dumps(answer) + '\n').encode())
                return stopped is None and guard.confirmed is True and guard.release() is not None
            for label in INPUT['subscriptions']['values'][:4]:
                found, error = attempt(lambda: confirmed(label))
                check('paid-api/stop', 'the answer naming %s confirms the login and releases the prompt [%s]'
                      % (label, error), found is True)
            for name, launch, own in (('subscription', normal_launch, normal), ('subscription token', token_launch, token_own)):
                found = artifact(launch)
                given = own.get('input') or []
                prompt = json.loads(given[-1][1]) if len(given) == 2 and given[-1][0] == 'user' else {}
                check('paid-api/stop', '%s: the initialize request first, its answer confirming the login, then the '
                      'dispatch packet as the prompt; the run whose init event reports none takes its first turn and '
                      'completes [%s, %s, %s]' % (name, [k for k, _ in given], init_of(own).get('apiKeySource'),
                                                  found.get('verdict')),
                      [k for k, _ in given] == ['initialize', 'user'] and prompt.get('dispatch_id') == launch.dispatch_id
                      and init_of(own).get('apiKeySource') == 'none' and own.get('turned') is True
                      and found.get('verdict') == 'complete' and (found.get('login') or {}).get('source') == 'none'
                      and (found.get('login') or {}).get('stop') is None)
            check('paid-api/stop', 'a version whose record does not qualify stream JSON input is refused by name before '
                  'acceptance, nothing spawned [%s]' % textual_record.get('refusal'),
                  textual_record.get('refusal') == 'missing_evidence:engine_input_protocol:' + VERSION
                  and history(textual_launch.dispatch_id) == ['prepared', 'refused'] and not spawned(textual_launch.dispatch_id))

        with region('paid-api/every-init'):
            found = artifact(later_launch)
            inits = [e for e in later.get('printed') or [] if e.get('type') == 'system']
            check('paid-api/every-init', 'a run confirmed on its login whose second init event names an API key is '
                  'stopped by name before that turn: one turn taken, the invocation cancelled [%s, %s, %s]'
                  % ([e.get('apiKeySource') for e in inits], later.get('turns'), (found.get('login') or {}).get('stop')),
                  later.get('prompted') is True and [e.get('apiKeySource') for e in inits] == ['none', sources[0]]
                  and later.get('turns') == 1 and later_record.get('state') == 'exited'
                  and (later_launch.supervision or {}).get('cause') == 'paid_api'
                  and (found.get('login') or {}).get('stop') == 'paid_api:apiKeySource:' + sources[0]
                  and invocation(later_launch.dispatch_id).get('outcome') == 'cancelled')

        with region('paid-api/profile-login'):
            for name, (launch, record) in profile_runs.items():
                kind, (how, _) = PROFILE_TYPE[name], PROFILE_ENVS[name]
                own_control, _ = profile_controls[name]
                check('paid-api/profile-login', '%s: an Anthropic profile the engine environment reaches (%s, resolved '
                      'where the engine resolves it) is refused by name before acceptance, nothing spawned or reserved '
                      '[%s]' % (name, how, record.get('refusal')),
                      record.get('refusal') == 'paid_api:anthropic_profile:' + kind
                      and history(launch.dispatch_id) == ['prepared', 'refused'] and not spawned(launch.dispatch_id)
                      and not own_of(launch.dispatch_id) and not invocation(launch.dispatch_id))
                check('paid-api/profile-login', '%s: started without the guard in a clone, the engine takes that profile '
                      'ahead of the claude.ai login and its init reports apiKeySource none, which no init event can show '
                      '[%s]' % (name, (own_control.get('debug') or {}).get('auth')),
                      (own_control.get('debug') or {}).get('auth') == 'profile'
                      and init_of(own_control).get('apiKeySource') == 'none')

        # AC4: the trusted wrapper's strip and the engine's own runtime directory.
        with region('strip/read-back'):
            names = set(normal.get('names') or [])
            check('strip/read-back', 'planted in the receiver\'s environment, the SSH agent, the session bus and the Git '
                  'tokens are absent from the engine\'s [%s]' % sorted(names & set(STRIPPED)),
                  bool(names) and not names & set(STRIPPED))
            check('strip/read-back', 'the receiver reported them removed [%s]'
                  % sorted(set(reported(normal_launch).get('removed') or []) & set(STRIPPED)),
                  set(STRIPPED) <= set(reported(normal_launch).get('removed') or []))

        with region('strip/private-runtime-directory'):
            place = normal.get('runtime') or {}
            argv = normal.get('argv') or []
            settings_path = next((argv[i + 1] for i, a in enumerate(argv[:-1]) if a == '--settings'), '/none/x')
            config_dir = str(Path(settings_path).parent)
            run = reported(normal_launch).get('run') or {}
            receiver_runtime = RECEIVER_ENV.get('XDG_RUNTIME_DIR') or runtime
            check('strip/private-runtime-directory', 'the engine\'s XDG_RUNTIME_DIR is an empty directory of the run\'s '
                  'own, 0700 and this account\'s, the one the receiver reported [%s]' % place,
                  place.get('dir') is True and place.get('entries') == [] and place.get('mode') == 0o700
                  and place.get('uid') == os.getuid() and place.get('path') == run.get('runtime'))
            check('strip/private-runtime-directory', 'never the receiver\'s runtime directory, never the directory '
                  'holding the run\'s generated configuration nor one above it [%s, %s, %s]'
                  % (place.get('path'), receiver_runtime, config_dir),
                  bool(place.get('path')) and os.path.realpath(place['path']) != os.path.realpath(receiver_runtime)
                  and os.path.realpath(place['path']) != os.path.realpath(config_dir)
                  and not (os.path.realpath(config_dir) + '/').startswith(os.path.realpath(place['path']) + '/')
                  and config_dir == run.get('config'))
            other = (second.get('runtime') or {}).get('path')
            check('strip/private-runtime-directory', 'each run has its own, removed with the run [%s, %s, %s]'
                  % (place.get('path'), other, run_dirs_after),
                  other and other != place.get('path') and run_dirs_after == {'normal': False, 'second': False})

        with region('strip/user-manager'):
            group = getattr(normal_launch, 'group', None) or {}
            supervision = normal_launch.supervision or {}
            check('strip/user-manager', 'the receiver kept the session bus its own systemd-run and systemctl use: the run '
                  'was created in its own transient scope in this run\'s slice, the engine inside it, and systemctl read '
                  'the scope\'s result once it was empty, while the engine had no session bus [%s, %s]'
                  % (group, supervision.get('result')),
                  normal_record.get('state') == 'exited' and group.get('slice') == slice_name
                  and str(normal.get('cgroup') or '').endswith('/%s/%s' % (slice_name, CT.unit_name(normal_launch.dispatch_id)))
                  and supervision.get('empty') is True and supervision.get('result') == 'success'
                  and 'DBUS_SESSION_BUS_ADDRESS' not in (normal.get('names') or []))

        with region('fixture/planted-control'):
            d = unguarded.get('debug') or {}
            loaded = {'settings': len(d.get('settings_files') or []) == 3,
                      'servers': names_of(d.get('servers')) >= set(SERVERS.values()),
                      'skills': set(d.get('skills') or []) >= set(SKILLS.values()) | set(fake_table['bundled']),
                      'instructions': len(d.get('instructions') or []) == 2,
                      'memory': len(d.get('memory') or []) == 1, 'hooks': len(d.get('hooks') or []) == 2}
            check('fixture/planted-control', 'started without the baseline in the same clone and profile, the fake loads '
                  'every planted item where the binary\'s gates would [%s, %s, exit %s]'
                  % (loaded, d.get('settings_files'), unguarded_code),
                  unguarded_code == 0 and all(loaded.values()))

        with region('format/fake-lines'):
            events = FORMATS['events']
            printed = [e for own in (normal, token_own, unguarded, shaken) for e in own.get('printed') or []]
            # The initialize answer, in the shape the binary's control response and Kfe() account give it.
            fields = set(re.findall(r'(\w+):(?:ie\?\.\w+|He\(\))', INPUT['account']['text']))
            answers = [e for e in printed if e.get('type') == 'control_response']
            bad = [('control_response', sorted(e)) for e in answers
                   if set(e) != {'type', 'response'} or (e['response'] or {}).get('subtype') != 'success'
                   or not isinstance((e['response'] or {}).get('request_id'), str)
                   or not set(((e['response'] or {}).get('response') or {}).get('account') or {'?': 1}) <= fields]
            answered = [e for e in shaken.get('printed') or [] if e.get('type') == 'control_response']
            if (len(fields) != 6 or len(answered) != 1
                    or (answered[0].get('response') or {}).get('request_id') != 'v155-control'):
                bad.append(('control_response', len(answered), sorted(fields)))
            for event in [e for e in printed if e.get('type') != 'control_response']:
                key = 'system/init' if event.get('type') == 'system' else (
                    'result/success' if event.get('type') == 'result' else event.get('type'))
                fields = (events.get(key) or {}).get('fields') or {}
                required = {f for f, v in fields.items() if not v.get('optional')}
                if not fields or set(event) - set(fields) or required - set(event):
                    bad.append((key, sorted(set(event) - set(fields)), sorted(required - set(event))))
            check('format/fake-lines', 'every line the fake printed is an event of the binary\'s own schema, with its '
                  'required fields, the initialize answer in the shape of its control response [%d lines, %s]'
                  % (len(printed), bad[:2]), len(printed) >= 7 and not bad)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
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
                    print('  VELDO-0155 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0155 %s detail: no check ran' % name)
        expect('VELDO-0155 ' + name, ok)
    print('VELDO-0155 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session: the receiver, its systemd tools and this suite's own systemctl reach the user manager
# through /run/user/<uid> for this run when the gate's environment names none.
_v155_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v155_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v155_suite()
finally:
    if _v155_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v155_session
