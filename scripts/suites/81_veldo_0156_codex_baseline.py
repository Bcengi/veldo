"""VELDO-0156: every Codex run starts on the everything-off baseline, behind the paid-API guard and the
environment strip.

Run: python3 scripts/selftest.py --suite 81_veldo_0156_codex_baseline

Only shared ROOT and expect are consumed. One temporary tree in the owner's runtime directory holds the
installed .veldo copy the suite loads AND the launch receiver, wrapper and clone entrance execute, so a
registered mutation of a production module reaches all of them. Real: a SQLite control store with OpenSSH
journal signatures, the owner's account records over profiles the local helper prepares, VELDO-0036
reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git source
bound to the store, VELDO-0042 clones confined with Landlock, the VELDO-0039 Runner and receiver processes,
the trusted wrapper and VELDO-0040 transient scopes under the owner's systemd user manager in a slice of
the run's own (stopped, and its failed units cleared, at the end; no unit is installed).

The engine is a fake Codex laid out as the vendor package and qualified by the production writer
(control_engine_codex.qualification), whose record carries the module's baseline. What it loads is the
0.154.0 binary's own gates (proof/VELDO-0156/codex-baseline.json, read out of its bytes and `exec
--help`, and codex-rendered.json, what its own offline renderer puts in the prompt): the profile's
config.toml unless `--ignore-user-config`, the profile's and the clone's rules unless `--ignore-rules`,
the clone's AGENTS.md unless `project_doc_max_bytes` is 0 (its default 32768), the profile's own
AGENTS.override.md, else AGENTS.md, always, the skills of the profile (with the bundled set in its
.system unless `skills.bundled.enabled` is false), HOME/.agents and the clone's .agents and .codex in its
skills section unless `skills.include_instructions` is false, and, whatever that says, the body of each such
skill the prompt names (`$name`) in its model request (codex-mentions.json, the real binary's request
captured on loopback), the login's ChatGPT connectors (a fixture in the profile stands in for the backend's answer) unless the
apps feature is off, the hooks of its effective configuration, and the login of the profile's auth.json file (a fixture that
names only its kind) unless the credentials store is another than the file; with `forced_login_method`
chatgpt it refuses an API-key login with the binary's own message before any turn. `login status` it
answers with the binary's own lines. It records how it was started, its effective configuration and
what it loaded, and its runtime directory as it found it, then prints the exec events, marking its first
model turn. No real engine runs, nothing logs in, no credential exists. Each row is reported once.
"""


def _v156_suite():
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
    import time
    import uuid

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    TABLE = json.loads((TREE / 'proof' / 'VELDO-0156' / 'codex-baseline.json').read_text())
    RENDERED = json.loads((TREE / 'proof' / 'VELDO-0156' / 'codex-rendered.json').read_text())
    MENTIONS = json.loads((TREE / 'proof' / 'VELDO-0156' / 'codex-mentions.json').read_text())
    EVENTS = json.loads((TREE / 'proof' / 'VELDO-0062' / 'cli-formats.json').read_text())['codex']['events']

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    ROWS = ('baseline/qualified', 'baseline/planted-user-config', 'baseline/planted-rules',
            'baseline/planted-project-doc', 'baseline/planted-hook', 'baseline/planted-profile-instructions',
            'baseline/planted-skill-profile', 'baseline/planted-skill-home', 'baseline/planted-skill-clone',
            'baseline/planted-skill-clone-codex', 'baseline/planted-skill-bundled', 'baseline/connectors-off',
            'paid-api/read-back', 'paid-api/stop', 'paid-api/file-login', 'paid-api/engine-refusal',
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

    fake_spec = importlib.util.spec_from_file_location('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    live_step = fake_formats.live_step

    started = time.monotonic()
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v156-', dir=runtime if os.path.isdir(runtime) else None))
    slice_name = 'v156%s.slice' % os.urandom(4).hex()
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
        S = load('v156_store', mods / 'control_store.py')
        L = load('v156_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = getattr(RES, 'ACC', None)
        X = getattr(L, 'ENGINES', {}).get('codex')
        HELPER = load('v156_helper', mods / 'accounts.py')
        EL = load('v156_eligibility', mods / 'control_eligibility.py')
        SIG = load('v156_signer', mods / 'control_signer.py')
        GP = load('v156_git', mods / 'git_process.py')
        CL = load('v156_clone', mods / 'control_clone.py')
        CT = load('v156_containment', mods / 'control_containment.py')
        CLM = D.CLM
        FLAGS = list(getattr(X, 'FLAGS', ()) or ())
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-156', 'repository-156', 'builder-156', 'linux-host-156'
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

        # The owner's Codex accounts: logged in through ChatGPT, not logged in, and logged in with an API key,
        # and two ChatGPT profiles holding their own AGENTS.md and AGENTS.override.md. Each profile's auth.json
        # is a fixture naming only the kind of login, which the fake reads.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign) if ACC else None
        helper_root = base / 'helper'
        profiles = {}
        LOGINS = {'acct-156a': 'chatgpt', 'acct-156n': None, 'acct-156k': 'apikey', 'acct-156g': 'chatgpt',
                  'acct-156o': 'chatgpt', 'acct-156s': 'chatgpt'}
        for account in LOGINS:
            record, _ = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider='codex'))
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
        put('project:journey-156', 'project', dict(name='journey-156'))
        reservations.configure('policy/journey-156', 'project', 'journey-156', dict(BIG), now=time.time())

        def admitted(unit):
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project='journey-156',
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

        # THE PLANTED ITEMS. The clone's (committed to the source): a project document and project rules; a skill
        # in .agents and in .codex each on a branch of its own, and both on a third for the unguarded control.
        MODEL, INSTRUCTIONS, HOOK = 'v156-planted-model', 'v156 planted developer instructions', 'echo v156-planted-hook'
        SKILLS = {'profile': 'v156-profile-skill', 'home': 'v156-home-skill', 'clone': 'v156-clone-skill',
                  'clone-codex': 'v156-clone-codex-skill'}
        BUNDLED = list(RENDERED['skills']['without_switch']['bundled_installed'])
        CONNECTOR, CONNECTORS = 'v156-chatgpt-connector', 'v156-chatgpt-connectors.json'

        def skill(directory, name):
            (directory / name).mkdir(parents=True, exist_ok=True)
            (directory / name / 'SKILL.md').write_text('---\nname: %s\ndescription: planted\n---\nbody\n' % name)
        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / '.codex' / 'rules').mkdir(parents=True)
        (src / 'AGENTS.md').write_text('v156 planted project document\n')
        (src / '.codex' / 'rules' / 'v156-clone.rules').write_text('prefix_rule(pattern = ["v156-clone"], decision = "allow")\n')
        (src / 'README').write_text('baseline source\n')
        GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        main_branch = GP.run(['git', '-C', str(src), 'rev-parse', '--abbrev-ref', 'HEAD'], check=True,
                             capture_output=True, text=True).stdout.strip()
        for branch, places in (('skills-agents', ('.agents',)), ('skills-codex', ('.codex',)),
                               ('skills-all', ('.agents', '.codex'))):
            GP.run(['git', '-C', str(src), 'checkout', '-q', '-b', branch, main_branch], check=True, capture_output=True)
            for place in places:
                skill(src / place / 'skills', SKILLS['clone' if place == '.agents' else 'clone-codex'])
            GP.run(['git', '-C', str(src), 'add', '-A', '-f'], check=True, capture_output=True)
            GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', branch], check=True,
                   capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        GP.run(['git', '-C', str(src), 'checkout', '-q', main_branch], check=True, capture_output=True)
        S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})

        # The engine's HOME, a directory of this run's, and another whose .agents holds a skill.
        engine_home = base / 'home'
        engine_home.mkdir()
        skills_home = base / 'home-skills'
        skill(skills_home / '.agents' / 'skills', SKILLS['home'])
        # Every profile's: a user configuration (a model, developer instructions and a hook), user rules, the
        # bundled skills the binary installs into its .system, and the ChatGPT connectors of its login; two hold
        # their own instruction file, and one (and the unguarded control's) a skill of its own.
        for account, directory in profiles.items():
            if not directory:
                continue
            directory = Path(directory)
            (directory / 'rules').mkdir(parents=True, exist_ok=True)
            (directory / 'config.toml').write_text('model = "%s"\ndeveloper_instructions = "%s"\n\n[hooks]\n'
                                                   'session_start = [{ command = "%s" }]\n' % (MODEL, INSTRUCTIONS, HOOK))
            (directory / 'rules' / 'v156-profile.rules').write_text('prefix_rule(pattern = ["v156-profile"], '
                                                                     'decision = "allow")\n')
            if LOGINS[account]:
                (directory / 'auth.json').write_text(json.dumps({'auth_mode': LOGINS[account]}))
            if account in ('acct-156s', 'acct-156g'):
                skill(directory / 'skills', SKILLS['profile'])
            for name in BUNDLED:
                skill(directory / 'skills' / '.system', name)
            (directory / CONNECTORS).write_text(json.dumps({'connectors': [CONNECTOR]}))
        if profiles.get('acct-156g'):
            (Path(profiles['acct-156g']) / 'AGENTS.md').write_text('v156 planted profile instructions\n')
        if profiles.get('acct-156o'):
            (Path(profiles['acct-156o']) / 'AGENTS.override.md').write_text('v156 planted profile override\n')

        markers = base / 'markers'
        markers.mkdir()
        fake_table = {'default_doc_bytes': TABLE['configuration']['project_doc_max_bytes']['default'],
                      'default_store': TABLE['configuration']['cli_auth_credentials_store']['default'],
                      'refusal': TABLE['engine_refusal']['text'], 'connectors': CONNECTORS,
                      'instructions': list(TABLE['profile_instructions']['files']),
                      'status': {'chatgpt': 'Logged in using ChatGPT', 'apikey': 'Logged in using an API key - ****',
                                 'none': 'Not logged in'}}
        fake = '''#!@@PYTHON@@ -B
import json, os, re, sys, time, tomllib, uuid
from pathlib import Path
markers, TABLE = Path(@@MARKERS@@), json.loads(@@TABLE@@)
argv, env, cwd = sys.argv[1:], os.environ, Path.cwd()
home = Path(env.get('CODEX_HOME') or Path(env.get('HOME', '/nonexistent')) / '.codex')
def merge(into, more):
    for key, value in more.items():
        if isinstance(value, dict) and isinstance(into.get(key), dict):
            merge(into[key], value)
        else:
            into[key] = value
    return into
def overrides(args):
    found = {}
    for at, arg in enumerate(args):
        if arg in ('--enable', '--disable') and at + 1 < len(args):
            merge(found, {'features': {args[at + 1]: arg == '--enable'}})
        if arg == '-c' and at + 1 < len(args) and '=' in args[at + 1]:
            key, _, value = args[at + 1].partition('=')
            try:
                merge(found, tomllib.loads('%s = %s' % (key, value)))
            except tomllib.TOMLDecodeError:
                merge(found, tomllib.loads('%s = %s' % (key, json.dumps(value))))
    return found
def user_config():
    try:
        return tomllib.loads((home / 'config.toml').read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}
def login(effective):
    if effective.get('cli_auth_credentials_store', TABLE['default_store']) != 'file':
        return None  # nothing in this host's keyring
    try:
        return json.loads((home / 'auth.json').read_text()).get('auth_mode')
    except (OSError, ValueError):
        return None
if argv[:2] == ['login', 'status']:
    effective = merge(user_config(), overrides(argv[2:]))
    kind = login(effective)
    (markers / ('status-%d.json' % os.getpid())).write_text(json.dumps({'argv': sys.argv, 'home': str(home)}))
    print(TABLE['status'].get(kind or 'none', TABLE['status']['none']), file=sys.stderr)
    sys.exit(0 if kind else 1)
ignore_user = '--ignore-user-config' in argv
effective = merge({} if ignore_user else user_config(), overrides(argv))
rules = [] if '--ignore-rules' in argv else sorted(str(p) for p in list((home / 'rules').glob('*.rules'))
                                                   + list((cwd / '.codex' / 'rules').glob('*.rules')))
doc_bytes = effective.get('project_doc_max_bytes', TABLE['default_doc_bytes'])
docs = [str(cwd / 'AGENTS.md')] if doc_bytes and (cwd / 'AGENTS.md').is_file() else []
own_docs = [str(home / n) for n in TABLE['instructions'] if (home / n).is_file()][:1]
bundled = ((effective.get('skills') or {}).get('bundled') or {}).get('enabled', True) is not False
places = [home / 'skills', Path(env.get('HOME', '/nonexistent')) / '.agents' / 'skills', cwd / '.agents' / 'skills',
          cwd / '.codex' / 'skills'] + ([home / 'skills' / '.system'] if bundled else [])
available = [p.name for place in places for p in sorted(place.glob('*')) if (p / 'SKILL.md').is_file()]
skills = available if (effective.get('skills') or {}).get('include_instructions', True) is not False else []
try:
    connectors = json.loads((home / TABLE['connectors']).read_text()).get('connectors') or []
except (OSError, ValueError):
    connectors = []
if (effective.get('features') or {}).get('apps', True) is False:
    connectors = []
who = login(effective)
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
       'cwd': str(cwd), 'names': sorted(env), 'runtime': runtime, 'effective': effective,
       'env': {k: env.get(k) for k in ('CODEX_HOME', 'XDG_RUNTIME_DIR', 'DISABLE_AUTOUPDATER')},
       'cgroup': next((l[3:] for l in open('/proc/self/cgroup').read().splitlines() if l.startswith('0::')), None),
       'debug': {'user_config': not ignore_user, 'rules': rules, 'docs': docs, 'hooks': effective.get('hooks'),
                 'profile_instructions': own_docs, 'skills': skills, 'connectors': connectors,
                 'login': who, 'forced': effective.get('forced_login_method'),
                 'store': effective.get('cli_auth_credentials_store', TABLE['default_store'])}}
(markers / ('%d.tmp' % os.getpid())).write_text(json.dumps(own))
(markers / ('%d.tmp' % os.getpid())).rename(markers / ('%d.json' % os.getpid()))
raw = sys.stdin.buffer.read()
out = open(markers / ('%d.out' % os.getpid()), 'w')
def emit(event):
    text = json.dumps(event)
    out.write(text + chr(10))
    out.flush()
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
# The model request: a skill the prompt names ($name, a JSON string too) has its body in it whatever the skills
# section says.
named = sorted(set(re.findall(r'[$]([A-Za-z0-9_.:-]+)', raw.decode('utf-8', 'replace'))))
request = {'named': named, 'bodies': sorted(name for name in available if name in named), 'listed': skills}
if own['debug']['forced'] == 'chatgpt' and who == 'apikey':
    emit({'type': 'error', 'message': TABLE['refusal']})
    sys.exit(1)
if who is None:
    emit({'type': 'error', 'message': 'Not logged in'})
    sys.exit(1)
emit({'type': 'thread.started', 'thread_id': 'thread-156-' + uuid.uuid4().hex[:8]})
emit({'type': 'turn.started'})
# Here the real engine sends its first model request: marked, so a refusal before it is seen.
(markers / ('%d.request' % os.getpid())).write_text(json.dumps(request))
(markers / ('%d.turn' % os.getpid())).write_text('the first turn')
emit({'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'agent_message', 'text': 'done'}})
emit({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': 2,
                                          'reasoning_output_tokens': 0}})
out.close()
(markers / ('%d.done' % os.getpid())).write_text('done')
'''.replace('@@PYTHON@@', sys.executable).replace('@@MARKERS@@', repr(str(markers))).replace(
            '@@TABLE@@', repr(json.dumps(fake_table)))
        fake = fake_formats.embed(fake)
        package = base / 'packages' / 'codex'
        CODEX_BIN = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        CODEX_BIN.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        CODEX_BIN.write_text(fake)
        CODEX_BIN.chmod(0o755)
        record_path = base / 'codex-qualification.json'
        codex_record, _ = attempt(lambda: X.qualification(str(CODEX_BIN)))
        record_path.write_text(json.dumps(codex_record or {}))
        unqualified_path = base / 'codex-unqualified.json'
        unqualified_path.write_text(json.dumps({k: v for k, v in (codex_record or {}).items() if k != 'baseline'}))

        real_systemd_run = shutil.which('systemd-run', path=tools.get('PATH', os.defpath)) or '/usr/bin/systemd-run'
        shim = base / 'systemd-run'
        shim.write_text('#!/bin/sh\nprintf %%s "$VELDO_DISPATCH_ID" > "%s/spawn-$$"\nexec %s "$@"\n'
                        % (markers, real_systemd_run))
        shim.chmod(0o755)
        profile = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                   'runtime_seconds': 120, 'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 0.4, 'kill_grace_seconds': 0.4, 'systemd_run': str(shim)}
        factory = state / 'factory'
        factory.mkdir(mode=0o700)
        clones_root, caches_root = state / 'clones', state / 'caches'
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', str(clones_root), '--']
        config = base / 'receiver.json'
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(state / 'receipts'), 'artifacts': str(state / 'artifacts'),
            'state_root': str(factory), 'profile': profile,
            'adapters': {
                'codex': {'engine': 'codex', 'executable': str(CODEX_BIN), 'qualification': str(record_path),
                          'argv': entering + [str(CODEX_BIN)] + FLAGS},
                'codex-unqualified': {'engine': 'codex', 'executable': str(CODEX_BIN),
                                      'qualification': str(unqualified_path), 'argv': entering + [str(CODEX_BIN)] + FLAGS}}}))

        def planted(name):
            return 'v156-planted-%s-%s' % (name.lower(), os.urandom(4).hex())
        STRIPPED = ('SSH_AUTH_SOCK', 'SSH_AGENT_PID', 'DBUS_SESSION_BUS_ADDRESS', 'GH_TOKEN', 'GITHUB_TOKEN')
        PAID = ('OPENAI_API_KEY', 'CODEX_API_KEY')
        RECEIVER_ENV = dict(os.environ)
        for name in STRIPPED + PAID:
            RECEIVER_ENV[name] = planted(name)
        RECEIVER_ENV['SSH_AUTH_SOCK'] = str(base / 'agent.sock')
        RECEIVER_ENV['SSH_AGENT_PID'] = str(os.getpid())
        RECEIVER_ENV['DBUS_SESSION_BUS_ADDRESS'] = os.environ.get('DBUS_SESSION_BUS_ADDRESS') or 'unix:path=%s/bus' % runtime
        RECEIVER_ENV['HOME'] = str(engine_home)

        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        clones, _ = attempt(lambda: CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root),
                                              protected=[str(private)], engines=[str(base / 'packages')]))
        if clones is None:
            clones = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)])

        # The receiver's environment of the run under way: its HOME is another for the planted HOME skill's run.
        HOME_OF = {}

        def invoke(contract):
            clones.create(contract)
            launch = L.invoke(config, contract, dispatches, accept_seconds=30, environment=dict(RECEIVER_ENV, **HOME_OF))
            contained.append(launch)
            return launch
        runners = {}

        def runner(account):
            if account not in runners:
                runners[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return runners[account]
        CONFIGURATION = {'tools': ['shell'], 'mcp_servers': {}, 'model': 'configured-model'}
        # Every run's prompt names each planted skill and the bundled set, as a task may.
        NAMED = sorted(SKILLS.values()) + sorted(BUNDLED)
        TASK = 'work the unit with ' + ' and '.join('$' + name for name in NAMED)
        units = [0]

        def run(account, adapter='codex', revision='HEAD', home=None):
            units[0] += 1
            HOME_OF.clear()
            HOME_OF.update({'HOME': str(home)} if home else {})
            try:
                launch = runner(account).submit(admitted('VELDO-156%02d' % units[0]), 'build', holder=HOLDER,
                                                source=str(src), revision=revision, payload={'task': TASK},
                                                adapter=adapter, configuration=CONFIGURATION, deadline=time.time() + 40)
                return launch, runner(account).wait(launch) or {}
            finally:
                HOME_OF.clear()

        def own_of(dispatch_id):
            for path in sorted(markers.glob('[0-9]*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    data['turned'] = (markers / ('%d.turn' % data['pid'])).exists()
                    request = markers / ('%d.request' % data['pid'])
                    data['request'] = json.loads(request.read_text()) if request.exists() else None
                    out = markers / ('%d.out' % data['pid'])
                    data['printed'] = [json.loads(x) for x in out.read_text().splitlines()] if out.exists() else []
                    return data
            return {}

        def status_calls(home):
            return [json.loads(p.read_text()) for p in sorted(markers.glob('status-*.json'))
                    if json.loads(p.read_text()).get('home') == str(home)]

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

        # The launches: the normal run on a ChatGPT login and a second of it, the runs on no login and on an
        # API-key login, the API-key run again with the adapter's own stop off (the engine-refusal row only),
        # and a binary whose record does not list the baseline.
        normal_launch, normal_record = run('acct-156a')
        normal = own_of(normal_launch.dispatch_id)
        second_launch, second_record = run('acct-156a')
        second = own_of(second_launch.dispatch_id)
        none_launch, none_record = run('acct-156n')
        key_launch, key_record = run('acct-156k')
        installed_codex = (mods / 'control_engine_codex.py').read_bytes()
        if hasattr(X, 'login_problem'):
            with open(mods / 'control_engine_codex.py', 'ab') as handle:
                handle.write(b'\n\ndef login_problem(bound, environment, cwd=None):  # the adapter\'s own stop off, this row only\n'
                             b'    return None\n')
        try:
            refusal_launch, refusal_record = run('acct-156k')
        finally:
            (mods / 'control_engine_codex.py').write_bytes(installed_codex)
        refused_own = own_of(refusal_launch.dispatch_id)
        unqualified_launch, unqualified_record = run('acct-156a', adapter='codex-unqualified')
        instructed = {name: run(account) for name, account in (('AGENTS.md', 'acct-156g'),
                                                               ('AGENTS.override.md', 'acct-156o'))}
        # A skill in each place no switch keeps a named skill out of: the profile's, the engine HOME's and the
        # clone's .agents and .codex.
        skilled = {'profile': run('acct-156s'), 'home': run('acct-156a', home=skills_home),
                   'clone': run('acct-156a', revision='skills-agents'),
                   'clone-codex': run('acct-156a', revision='skills-codex')}
        # An engine working below its project root reads the root's skills too (the binary walks up to the nearest
        # .git): the production check, called on such a directory.
        project = base / 'project-156'
        GP.run(['git', 'init', '-q', str(project)], check=True, capture_output=True)
        skill(project / '.agents' / 'skills', SKILLS['clone'])
        (project / 'sub').mkdir()
        (base / 'profile-empty').mkdir()
        below, _ = attempt(lambda: X.profile_problem({}, {'CODEX_HOME': str(base / 'profile-empty'), 'HOME': str(engine_home)},
                                                     str(project / 'sub')))
        run_dirs_after = {name: os.path.exists(reported(launch).get('run', {}).get('root') or '/nonexistent/x')
                          for name, launch in (('normal', normal_launch), ('second', second_launch))}

        # The unguarded control: the same fake started directly with the qualified flags alone, in a clone of
        # the source's branch holding both clone skills, the HOME holding a skill and the ChatGPT profile that
        # holds its own AGENTS.md and a skill, the same prompt on its input.
        control_work = base / 'control-work'
        GP.run(['git', 'clone', '-q', '-b', 'skills-all', str(src), str(control_work)], check=True, capture_output=True)
        control_id = 'control-%s' % uuid.uuid4().hex
        done = subprocess.run([str(CODEX_BIN)] + FLAGS, cwd=str(control_work),
                              input=json.dumps({'payload': {'task': TASK}}).encode(), capture_output=True,
                              timeout=30, env={'PATH': os.environ.get('PATH', os.defpath), 'LANG': 'C.UTF-8',
                                               'HOME': str(skills_home), 'CODEX_HOME': profiles['acct-156g'],
                                               'VELDO_DISPATCH_ID': control_id, 'XDG_RUNTIME_DIR': runtime})
        unguarded, unguarded_code = own_of(control_id), done.returncode

        debug = normal.get('debug') or {}
        effective = normal.get('effective') or {}

        # AC1: the everything-off baseline, one row per planted item.
        with region('baseline/qualified'):
            argv = normal.get('argv') or []
            options = [o for o in ('--ignore-user-config', '--ignore-rules') if o in TABLE['options']]
            options += [a for name, entry in sorted((TABLE.get('features') or {}).items()) if entry['value'] is False
                        and '--disable' in TABLE['options'] for a in ('--disable', name)]
            generated = TABLE['configuration']
            expected = FLAGS + options
            toml = lambda value: json.dumps(value) if isinstance(value, str) else str(value).lower()
            for key in sorted(generated):
                expected += ['-c', '%s=%s' % (key, toml(generated[key]['value']))]
            check('baseline/qualified', 'the run started the pinned vendor binary with the qualified flags and then '
                  'exactly the baseline: the two exec options, the apps feature off, no project document, the ChatGPT '
                  'login forced, the file credentials store, the bundled skills off and no skills section, every name '
                  'the binary\'s own [%s]' % argv[1:],
                  normal_record.get('state') == 'exited' and argv[:1] == [str(CODEX_BIN)] and argv[1:] == expected
                  and len(options) == 4 and 'hooks' not in effective
                  and (effective.get('skills') or {}).get('include_instructions') is False)
            check('baseline/qualified', 'the generated configuration is kept in the run\'s own configuration directory, '
                  'as passed [%s]' % reported(normal_launch).get('files'),
                  reported(normal_launch).get('files') == ['config.toml'])
            shipped = json.loads((ROOT / 'engine' / 'runtime' / 'codex-qualification.json').read_text())
            base_line = shipped.get('baseline') or {}
            check('baseline/qualified', 'the shipped 0.154.0 record qualifies the binary with the module\'s baseline, '
                  'every option and key in it the binary\'s own [%s]' % base_line,
                  base_line == getattr(X, 'BASELINE', None) and base_line
                  and set(base_line.get('options') or []) <= set(TABLE['options']) | set(TABLE.get('features') or {})
                  and {k: v for k, v in (base_line.get('configuration') or {}).items()}
                  == {k: v['value'] for k, v in generated.items()})
            check('baseline/qualified', 'a binary whose record does not list the baseline is refused by name before '
                  'acceptance, nothing spawned [%s]' % unqualified_record.get('refusal'),
                  unqualified_record.get('refusal') == 'missing_evidence:engine_baseline:0.154.0'
                  and history(unqualified_launch.dispatch_id) == ['prepared', 'refused']
                  and not spawned(unqualified_launch.dispatch_id))

        with region('baseline/planted-user-config'):
            check('baseline/planted-user-config', 'the account profile\'s config.toml did not load: its model and '
                  'developer instructions are not the run\'s effective configuration [%s]' % sorted(effective),
                  bool(normal) and debug.get('user_config') is False and effective.get('model') != MODEL
                  and effective.get('developer_instructions') != INSTRUCTIONS)

        with region('baseline/planted-rules'):
            check('baseline/planted-rules', 'no rules of the profile or the clone loaded [%s]' % debug.get('rules'),
                  bool(normal) and debug.get('rules') == [])

        with region('baseline/planted-project-doc'):
            check('baseline/planted-project-doc', 'the clone\'s AGENTS.md did not load: the project document budget '
                  'is zero [%s, %s]' % (debug.get('docs'), effective.get('project_doc_max_bytes')),
                  bool(normal) and debug.get('docs') == [] and effective.get('project_doc_max_bytes') == 0)

        with region('baseline/planted-hook'):
            check('baseline/planted-hook', 'no hook is in the run\'s effective configuration: the profile\'s is neither '
                  'loaded nor copied into the generated one [%s]' % debug.get('hooks'),
                  bool(normal) and debug.get('hooks') is None and 'hooks' not in effective)

        with region('baseline/planted-profile-instructions'):
            for name, (launch, record) in instructed.items():
                check('baseline/planted-profile-instructions', 'a profile holding its own %s, which the binary reads '
                      'into every prompt whatever the baseline says, is refused by that name before acceptance, nothing '
                      'spawned or reserved [%s]' % (name, record.get('refusal')),
                      record.get('refusal') == 'invalid_input:engine_profile:' + name
                      and history(launch.dispatch_id) == ['prepared', 'refused'] and not spawned(launch.dispatch_id)
                      and not own_of(launch.dispatch_id) and not invocation(launch.dispatch_id))
            observed = RENDERED['profile_instructions']
            check('baseline/planted-profile-instructions', 'the binary\'s own offline renderer put each planted file in '
                  'the prompt under the baseline and no switch tried removes it; the plain profile\'s run loaded none '
                  '[%s]' % debug.get('profile_instructions'),
                  observed['agents_md']['present']['profile_agents_md'] is True
                  and observed['agents_override_md']['present']['profile_agents_override_md'] is True
                  and all(observed['candidates'].values()) and debug.get('profile_instructions') == [])

        # One row per place the binary reads a skill from. A skill the prompt names loads whatever the skills
        # section says (the real binary's request, codex-mentions.json): the profile's, HOME's and the clone's are
        # refused before acceptance, the bundled ones (the profile's .system) kept out by skills.bundled.enabled.
        request = normal.get('request') or {}
        captured, earlier = MENTIONS['baseline']['present'], MENTIONS['previous_baseline']['present']
        controls = sorted(k for k in captured if k.startswith('control_'))
        for row, key, where, refusal in (
                ('baseline/planted-skill-profile', 'profile', 'skill_profile',
                 'invalid_input:engine_profile:skills/' + SKILLS['profile']),
                ('baseline/planted-skill-home', 'home', 'skill_home_agents',
                 'invalid_input:engine_home:.agents/skills/' + SKILLS['home']),
                ('baseline/planted-skill-clone', 'clone', 'skill_clone_agents',
                 'invalid_input:engine_clone:.agents/skills/' + SKILLS['clone']),
                ('baseline/planted-skill-clone-codex', 'clone-codex', 'skill_clone_codex',
                 'invalid_input:engine_clone:.codex/skills/' + SKILLS['clone-codex'])):
            with region(row):
                launch, record = skilled[key]
                check(row, 'a %s skill, which the binary loads into the model request when the prompt names it whatever '
                      'the baseline says, is refused by that name before acceptance: nothing spawned or reserved, no model '
                      'request [%s]' % (key, record.get('refusal')),
                      record.get('refusal') == refusal and history(launch.dispatch_id) == ['prepared', 'refused']
                      and not spawned(launch.dispatch_id) and not own_of(launch.dispatch_id)
                      and not invocation(launch.dispatch_id))
                check(row, 'the plain run\'s prompt named that skill and its model request carries no skill body [%s]'
                      % request, SKILLS[key] in (request.get('named') or []) and request.get('bodies') == [])
                check(row, 'the real binary\'s own model request: that skill\'s body is in it when the prompt names it, '
                      'under the previous baseline, this one and every other switch tried, and the places around it that '
                      'the binary does not read hold nothing it loads [%s]' % where,
                      earlier[where] is True and captured[where] is True
                      and all(found[where] is True for found in MENTIONS['candidates'].values())
                      and not any(captured[k] or earlier[k] for k in controls) and len(controls) == 4)
                if key == 'clone':
                    check(row, 'an engine working below the project root is refused for the root\'s skill as well [%s]'
                          % below, below == 'invalid_input:engine_clone:../.agents/skills/' + SKILLS['clone'])

        with region('baseline/planted-skill-bundled'):
            skills_off = effective.get('skills') or {}
            check('baseline/planted-skill-bundled', 'the profile\'s .system holds the bundled set and the prompt names '
                  'each; skills.bundled.enabled is false in the run\'s effective configuration and its model request '
                  'carries none of their bodies and lists no skill [%s, %s]' % (skills_off, request),
                  bool(normal) and (skills_off.get('bundled') or {}).get('enabled') is False
                  and set(BUNDLED) <= set(request.get('named') or []) and request.get('bodies') == []
                  and request.get('listed') == [] and bool(BUNDLED)
                  and all((Path(profiles['acct-156a']) / 'skills' / '.system' / n / 'SKILL.md').is_file() for n in BUNDLED))
            preinstalled = MENTIONS['baseline_bundled_preinstalled']
            check('baseline/planted-skill-bundled', 'the real binary\'s own model request: the bundled imagegen body is in '
                  'it when the prompt names it under the previous baseline, and not under this one, also with the '
                  'bundled set already installed in the profile [%s, %s]' % (earlier['bundled'], preinstalled['present']),
                  earlier['bundled'] is True and captured['bundled'] is False and preinstalled['present']['bundled'] is False
                  and preinstalled['bundled_installed'] is True)

        with region('baseline/connectors-off'):
            features = TABLE.get('features') or {}
            shipped_options = ((json.loads((ROOT / 'engine' / 'runtime' / 'codex-qualification.json').read_text())
                                .get('baseline') or {}).get('options') or [])
            pairs = list(zip(argv, argv[1:]))
            check('baseline/connectors-off', 'the launch and the shipped record carry --disable apps, the apps feature '
                  'off in the run\'s effective configuration, and none of the login\'s ChatGPT connectors loaded '
                  '[%s, %s]' % ((effective.get('features') or {}), debug.get('connectors')),
                  ('--disable', 'apps') in pairs and ('--disable', 'apps') in list(zip(shipped_options, shipped_options[1:]))
                  and (effective.get('features') or {}).get('apps') is False and debug.get('connectors') == []
                  and features.get('apps', {}).get('value') is False)
            check('baseline/connectors-off', 'the binary\'s own feature table: apps on by default, off under '
                  '--disable apps [%s]' % RENDERED['apps'],
                  RENDERED['apps']['default']['enabled'] is True and RENDERED['apps']['disabled']['enabled'] is False)

        # AC2: no paid-API credential variable reaches the engine.
        with region('paid-api/read-back'):
            names = set(normal.get('names') or [])
            check('paid-api/read-back', 'planted in the caller\'s environment, OPENAI_API_KEY and CODEX_API_KEY are absent '
                  'from the engine\'s [%s]' % sorted(names & set(PAID)), bool(names) and not names & set(PAID))
            report = reported(normal_launch)
            check('paid-api/read-back', 'the receiver reported both removed, never a value [%s]'
                  % sorted(set(report.get('removed') or []) & set(PAID)),
                  set(PAID) <= set(report.get('removed') or [])
                  and not any(RECEIVER_ENV[n] in json.dumps(report) for n in PAID))

        # AC3: a run not logged in through ChatGPT is stopped by name before its first turn.
        with region('paid-api/stop'):
            for name, launch, record, kind in (('no login', none_launch, none_record, 'not_logged_in'),
                                               ('an API-key login', key_launch, key_record, 'api_key')):
                check('paid-api/stop', '%s: refused by name before acceptance, nothing spawned or reserved and no turn '
                      'sent [%s]' % (name, record.get('refusal')),
                      record.get('refusal') == 'paid_api:codex_login:' + kind
                      and history(launch.dispatch_id) == ['prepared', 'refused'] and not spawned(launch.dispatch_id)
                      and not own_of(launch.dispatch_id) and not invocation(launch.dispatch_id))
            calls = status_calls(profiles['acct-156k']) + status_calls(profiles['acct-156n'])
            check('paid-api/stop', 'the check is the binary\'s own login status, read from the file store and never with '
                  'the login method forced, so it logs no login out [%d calls]' % len(calls),
                  len(calls) >= 2 and all('cli_auth_credentials_store="file"' in c['argv']
                                          and not any('forced_login_method' in a for a in c['argv']) for c in calls))

        with region('paid-api/file-login'):
            found = artifact(normal_launch)
            check('paid-api/file-login', 'the ChatGPT profile\'s run took its first turn on the login read from its '
                  'profile\'s file, and completed [%s, %s, %s]' % (debug.get('login'), debug.get('store'), found.get('verdict')),
                  normal.get('turned') is True and debug.get('login') == 'chatgpt' and debug.get('store') == 'file'
                  and found.get('verdict') == 'complete' and normal_record.get('state') == 'exited')
            calls = status_calls(profiles['acct-156a'])
            check('paid-api/file-login', 'the file store is the generated configuration\'s own, not the binary\'s '
                  'default, and the binary\'s login status read that login from it before acceptance [%s, %d calls]'
                  % (effective.get('cli_auth_credentials_store'), len(calls)),
                  effective.get('cli_auth_credentials_store') == 'file'
                  and any('cli_auth_credentials_store="file"' in c['argv'] for c in calls))

        with region('paid-api/engine-refusal'):
            printed = refused_own.get('printed') or []
            found = artifact(refusal_launch)
            check('paid-api/engine-refusal', 'with the adapter\'s own stop off, the API-key profile\'s engine itself '
                  'refused the login with the binary\'s message because the ChatGPT method is forced: no turn, no '
                  'completion [%s, %s]' % (printed[:1], found.get('verdict')),
                  bool(refused_own) and (refused_own.get('debug') or {}).get('forced') == 'chatgpt'
                  and printed == [{'type': 'error', 'message': TABLE['engine_refusal']['text']}]
                  and refused_own.get('turned') is False and refusal_record.get('state') == 'exited'
                  and (refusal_record.get('termination') or {}).get('returncode') != 0 and found.get('complete') is False)

        # AC4: the trusted wrapper's strip and the engine's own runtime directory.
        with region('strip/read-back'):
            names = set(normal.get('names') or [])
            check('strip/read-back', 'planted in the receiver\'s environment, the SSH agent, the session bus and the Git '
                  'tokens are absent from the Codex engine\'s [%s]' % sorted(names & set(STRIPPED)),
                  bool(names) and not names & set(STRIPPED))
            check('strip/read-back', 'the receiver reported them removed',
                  set(STRIPPED) <= set(reported(normal_launch).get('removed') or []))

        with region('strip/private-runtime-directory'):
            place = normal.get('runtime') or {}
            run_dirs = reported(normal_launch).get('run') or {}
            config_dir = run_dirs.get('config') or '/none'
            receiver_runtime = RECEIVER_ENV.get('XDG_RUNTIME_DIR') or runtime
            check('strip/private-runtime-directory', 'the engine\'s XDG_RUNTIME_DIR is an empty directory of the run\'s '
                  'own, 0700 and this account\'s, the one the receiver reported [%s]' % place,
                  place.get('dir') is True and place.get('entries') == [] and place.get('mode') == 0o700
                  and place.get('uid') == os.getuid() and place.get('path') == run_dirs.get('runtime'))
            check('strip/private-runtime-directory', 'never the receiver\'s runtime directory, never the directory '
                  'holding the run\'s generated configuration nor one above it [%s, %s, %s]'
                  % (place.get('path'), receiver_runtime, config_dir),
                  bool(place.get('path')) and os.path.realpath(place['path']) != os.path.realpath(receiver_runtime)
                  and os.path.realpath(place['path']) != os.path.realpath(config_dir)
                  and not (os.path.realpath(config_dir) + '/').startswith(os.path.realpath(place['path']) + '/'))
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
            e = unguarded.get('effective') or {}
            loaded = {'user_config': e.get('model') == MODEL and e.get('developer_instructions') == INSTRUCTIONS,
                      'rules': len(d.get('rules') or []) == 2, 'docs': len(d.get('docs') or []) == 1,
                      'hooks': bool(d.get('hooks')), 'profile_instructions': len(d.get('profile_instructions') or []) == 1,
                      'skills': set(d.get('skills') or []) >= set(SKILLS.values()) | set(BUNDLED),
                      'named': set((unguarded.get('request') or {}).get('bodies') or []) >= set(SKILLS.values()) | set(BUNDLED),
                      'connectors': d.get('connectors') == [CONNECTOR]}
            check('fixture/planted-control', 'started with the qualified flags alone in the same clone and profile, the '
                  'fake loads every planted item where the binary\'s gates would [%s, exit %s]' % (loaded, unguarded_code),
                  unguarded_code == 0 and all(loaded.values()))

        with region('format/fake-lines'):
            printed = [e for own in (normal, second, refused_own) for e in own.get('printed') or []]
            bad = [e for e in printed if e.get('type') not in EVENTS
                   or set(e) - set(EVENTS[e['type']]['fields'])]
            check('format/fake-lines', 'every line the fake printed is an exec event of the binary\'s own table '
                  '[%d lines, %s]' % (len(printed), bad[:2]), len(printed) >= 9 and not bad)
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        if globals().get('__engine_observer__'):
            __engine_observer__(locals())
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
                    print('  VELDO-0156 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0156 %s detail: no check ran' % name)
        expect('VELDO-0156 ' + name, ok)
    print('VELDO-0156 suite seconds: %.3f' % (time.monotonic() - started))


# The owner's session: the receiver, its systemd tools and this suite's own systemctl reach the user manager
# through /run/user/<uid> for this run when the gate's environment names none.
_v156_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v156_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v156_suite()
finally:
    if _v156_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v156_session
