"""VELDO-0185: factory setup lays down the dispatch configuration, so work runs on both engines on every account.

Run: python3 scripts/selftest.py --suite 106_veldo_0185_dispatch_setup

Only shared ROOT and expect are consumed. VELDO-0171's installed-host fixture (scripts/suites/85_veldo_0171_setup_api.py,
reused through proof/VELDO-0185/fixture.py as VELDO-0203 reuses it) lays every host down with the real setup module
through its own command surface, into scratch, with that fixture's user manager stand-in running the installed units'
ExecStart, its Tailscale stand-in and its loopback Bot API. The host's account registry is accounts.py's own file
under each workspace's Git common directory, written by accounts.py `account_add`; nothing of this host's own
registry or logins is read. The engines are generated fakes (VELDO-0172's shared constructors) installed where
VELDO-0186 locates them: each prints the installed CLIs' stream shape, answers Claude Code's `auth status` and
Codex's `login status` from a marker file in the account's own profile directory, and is pinned, bound and launched
by the installed engine. The worker runs contained under this host's real user manager (the fixture's
linux-systemd profile). No real key, login, token or credential is read, and none is printed.
"""


def _v185_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import socket
    import sqlite3
    import stat
    import subprocess
    import sys
    import contextlib
    import io
    import tarfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_dispatch.py': ROOT / ".veldo" / "control_factory_setup_dispatch.py",
        'control_factory_setup_trust.py': ROOT / ".veldo" / "control_factory_setup_trust.py",
        'control_factory_setup_records.py': ROOT / ".veldo" / "control_factory_setup_records.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
    }
    ROWS = ('fresh/team', 'fresh/adapters', 'fresh/one-engine', 'loop/configured', 'reservation/principals',
            'reservation/state-root', 'fresh/registered', 'login/named', 'login/receiver-refuses', 'every-account',
            'rerun/changes-nothing', 'rerun/over-earlier-host', 'install/asset', 'format/fake-lines',
            # The Codex review of e016df9b (R1 to R4), and the Codex roles' model.
            'login/retry-excludes', 'login/recheck', 'rerun/missing-state-root', 'team/workers', 'team/newest-model')
    rows = {name: [] for name in ROWS}
    # The engine before this change: the whole .veldo of main at 294e1933 (VELDO-0139, 0171, 0186, 0189, 0203, 0204).
    BEFORE = '294e1933'

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """An exception is recorded as a failure of each named row, and the run goes on (as suite 85 does)."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None and issubclass(kind, Exception):
                for name in self.names:
                    check(name, 'the section ran to its end (raised %s: %s)' % (kind.__name__, str(value)[:200]), False)
                return True
            return False

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    here = Path(__suite_file__).resolve().parents[2]

    def codex_tools():
        """The wire names of the reviewer's Codex grants as setup gives them (none before this change)."""
        path = Path(PRODUCTION['control_factory_setup_dispatch.py'])
        if not path.is_file():
            return []
        grants = load('v185_grants', path).NATIVE_TOOLS['codex']['independent_review']
        mapping = load('v185_codex_mapping', PRODUCTION['control_engine_codex.py']).NATIVE_TOOL_MAPPING
        return sorted({name for grant in grants for name in mapping.get(grant, [grant])})

    def code_mode():
        """The qualified catalog's code-mode models, whose runs the binary also gives its runner tools."""
        modes = load('v185_codex_modes', PRODUCTION['control_engine_codex.py']).MODEL_TOOL_MODES
        return sorted(slug for slug, mode in modes.items() if mode == 'code_mode_only')

    def newest_model():
        """The newest model of the shipped qualified Codex catalog, read here independently of setup: of its listed
        models not retired in favour of another (no `upgrade`), the one of the lowest priority, the catalog's own
        order, newest first."""
        record = json.loads((ROOT / '.veldo' / 'runtime' / 'codex-qualification.json').read_text())
        listed = [m for m in record['model_catalog']['models'] if m.get('visibility') == 'list' and not m.get('upgrade')]
        return min(listed, key=lambda m: m['priority'])['slug'], listed
    helper = load('v185_fixture', here / 'proof/VELDO-0185/fixture.py')
    conform_formats = load('v185_conform', ROOT / 'proof/VELDO-0172/compare_formats.py')
    fake_formats = load('v185_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    # One generated executable serves both engines: it is Codex when its path names codex. It answers each
    # engine's own login status from a marker in the account's profile, and prints each CLI's stream.
    fake = fake_formats.embed(r'''#!@@PYTHON@@ -B
import json, os, sys, uuid
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if sys.argv[1:3] == ['auth', 'status']:
    logged = (Path(os.environ.get('CLAUDE_CONFIG_DIR') or '/nonexistent') / '.credentials.json').is_file()
    sys.stdout.write(json.dumps({'loggedIn': logged, 'authMethod': 'claude.ai' if logged else 'none',
                                 'apiProvider': 'firstParty'}, indent=2) + chr(10))
    sys.exit(0 if logged else 1)
if sys.argv[1:3] == ['login', 'status']:
    logged = (Path(os.environ.get('CODEX_HOME') or '/nonexistent') / 'auth.json').is_file()
    sys.stderr.write(('Logged in using ChatGPT' if logged else 'Not logged in') + chr(10))
    sys.exit(0 if logged else 1)
if sys.argv[1:2] == ['exec']:
    import tomllib, urllib.request
    config = {}
    def merge(into, value):
        for key, item in value.items():
            if isinstance(item, dict):
                merge(into.setdefault(key, {}), item)
            else:
                into[key] = item
    for at, arg in enumerate(sys.argv):
        if arg == '-c' and at + 1 < len(sys.argv):
            try:
                merge(config, tomllib.loads(sys.argv[at + 1]))
            except tomllib.TOMLDecodeError:
                pass
    if config.get('model_provider') == 'role_observation':
        # A role-bound run's tool observation (VELDO-0127): the definitions the pinned binary sends its model
        # for the reviewer's grants, posted once to the receiver's loopback endpoint, which refuses the turn.
        provider = config['model_providers']['role_observation']
        # A code-mode model's binary also sends its runner tools, as the qualified binary does (VELDO-0127).
        names = @@CODEX_TOOLS@@ + (['exec', 'wait'] if config.get('model') in @@CODE_MODE@@ else [])
        body = json.dumps({'model': config.get('model'), 'tools': [{'type': 'function', 'name': name}
                                                                    for name in names]}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(provider['base_url'] + '/responses', data=body,
                                                          headers={'Content-Type': 'application/json'}), timeout=10)
        except Exception:
            pass
        sys.exit(1)
if sys.argv[1:3] == ['mcp', 'list']:
    # A role-bound Codex run's MCP table, read before exec: the role selects no server.
    sys.stdout.write('[]' + chr(10))
    sys.exit(0)
usage = {'input_tokens': 3, 'output_tokens': 3, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0,
         'cache_creation': {'ephemeral_1h_input_tokens': 0, 'ephemeral_5m_input_tokens': 0},
         'server_tool_use': {'web_fetch_requests': 0, 'web_search_requests': 0}, 'service_tier': 'standard'}
if 'codex' not in Path(sys.argv[0]).name:
    # A role-bound run's launch tool set (--tools=...) is what its init event reports, with the engine's own
    # plugins off as the run's generated settings turn them off; a run bound to no role reports its defaults.
    bound = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--tools=')]
    tools = [t for t in (bound[0].split(',') if bound else ['Read']) if t]
    session = str(uuid.uuid4())
    def init():
        event = complete_event({'type': 'system', 'subtype': 'init', 'cwd': str(Path.cwd()), 'session_id': session,
                                'tools': tools, 'mcp_servers': [], 'model': 'configured-model',
                                'permissionMode': 'default', 'slash_commands': [], 'apiKeySource': 'none',
                                'claude_code_version': '2.1.281', 'output_style': 'default', 'agents': [],
                                'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4())})
        if bound:
            event['plugins'] = []
        print(json.dumps(event), flush=True)
    while True:
        line = sys.stdin.readline()
        if not line:
            sys.exit(3)
        message = json.loads(line)
        if message.get('type') == 'control_request':
            emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                  'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
        elif message.get('type') == 'user' and message.get('shouldQuery') is False:
            # The capability probe of a role-bound run: its init, then a result of no turn.
            init()
            emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 0, 'result': '',
                  'session_id': session, 'usage': {'input_tokens': 0, 'output_tokens': 0}})
        elif message.get('type') == 'user':
            break
    init()
    emit({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()), 'session_id': session,
          'message': {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant',
                      'model': 'configured-model', 'content': [], 'stop_reason': None, 'stop_sequence': None,
                      'usage': dict(usage)}})
    usage['output_tokens'] = 4
    emit({'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4, 'is_error': False,
          'num_turns': 1, 'result': 'done', 'stop_reason': 'end_turn', 'total_cost_usd': 0, 'usage': usage,
          'modelUsage': {'fixture': {'inputTokens': 3, 'outputTokens': 4, 'cacheReadInputTokens': 0,
                                     'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                                     'contextWindow': 200000, 'maxOutputTokens': 32000}},
          'permission_denials': [], 'uuid': str(uuid.uuid4()), 'session_id': session})
else:
    sys.stdin.read()
    emit({'type': 'thread.started', 'thread_id': str(uuid.uuid4())})
    emit({'type': 'turn.started'})
    emit({'type': 'item.completed', 'item': {'id': 'answer', 'type': 'agent_message', 'text': 'done'}})
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0,
          'cache_write_input_tokens': 0, 'output_tokens': 2, 'reasoning_output_tokens': 0}}), flush=True)
'''.replace('@@PYTHON@@', sys.executable).replace('@@CODEX_TOOLS@@', repr(codex_tools()))
       .replace('@@CODE_MODE@@', repr(code_mode())))
    fake_capture = (['teardown not reached'], [])
    # The owner's accounts as his case has them: three Claude Code and one Codex, one Claude Code logged out.
    # Fresh accounts tie on utilization, active runs and last use, so the pool chooses by id.
    # Refuse the very first build, before any healthy worker can affect selection or timing.
    ACCOUNTS = (('claude-a', 'claude_code', False), ('claude-b', 'claude_code', True), ('claude-c', 'claude_code', True),
                ('codex-a', 'codex', True))
    LOGGED_OUT = 'claude-a'

    def exercise(h):
        F, S, CEN, base = h['F'], h['S'], h['CEN'], h['base']
        AR = load('v185_accounts', h['mods'] / 'accounts.py')
        scaffold = load('v185_scaffold', h['mods'] / 'init_scaffold.py')
        check('install/asset', 'the dispatch module is in the scaffold inventory, with every setup module',
              '.veldo/control_factory_setup_dispatch.py' in scaffold._FILES
              and '.veldo/control_factory_setup.py' in scaffold._FILES)
        # The installed Codex record of the generated binary carries the shipped record's bundled model catalog and
        # feature listing, as `qualification(catalog=True)` records them from the real binary (VELDO-0127).
        record_path = h['mods'] / 'runtime' / 'codex-qualification.json'
        shipped = json.loads((ROOT / '.veldo' / 'runtime' / 'codex-qualification.json').read_text())
        record = json.loads(record_path.read_text())
        record.update({k: shipped[k] for k in ('feature_listing', 'model_catalog', 'model_catalog_digest',
                                               'model_tool_modes', 'native_tool_mapping') if k in shipped})
        record_path.write_text(json.dumps(record))
        L = load('v185_launch', h['mods'] / 'control_launch.py')
        RES = L.D.RES
        owner = h['owner']
        hostname = socket.gethostname()

        def registry(clone, accounts):
            """The host's account registry as `veldo account add` writes it, under the clone's Git common directory."""
            root = os.path.join(CEN.git_common_dir(str(clone)), 'veldo')
            for name, provider, logged in accounts:
                profile = base / 'profiles' / clone.name / name
                profile.mkdir(parents=True, mode=0o700)
                if logged:
                    (profile / ('.credentials.json' if provider == 'claude_code' else 'auth.json')).write_text('{}\n')
                AR.account_add(name, config_dir=str(profile), root=root, provider=provider)
            return root

        def host(suffix, accounts, module=None):
            root, workspace = h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix)
            registry(workspace, accounts)
            # Each host is laid down over a fresh Tailscale stand-in state, as suite 85 resets it between hosts.
            h['ts'].set('ready')
            units = base / ('units-' + suffix)
            manager = h['Manager'](units)
            h['managers'].append(manager)
            args = (root, workspace, base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix), units, manager)
            if module is None:
                code, report = h['setup'](*args)
            else:
                # An earlier setup module through its own command surface, with the fixture's Tailscale stand-in and
                # port (the fixture's helper gives those to its current module only), never the host's own CLI.
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = module.main(['setup', '--state-root', str(root), '--owner', owner, '--owner-key',
                                        str(h['owner_key']), '--workspace', str(workspace), '--chat', str(h['chat']),
                                        '--token-file', str(h['token_file'])],
                                       host_trust=str(args[2]), install_root=str(args[3]), unit_dir=str(units),
                                       profile=h['profile'], writable=[], runner=manager, origin=h['url'],
                                       tailscale=[h['ts'].path], api_port=h['port'])
                try:
                    report = json.loads(out.getvalue().strip().splitlines()[-1])
                except (ValueError, IndexError):
                    report = {'unparsed': out.getvalue()[-300:]}
            return dict(root=root, workspace=workspace, args=args, manager=manager, units=units, code=code,
                        report=report, store=root / 'authority' / 'control.sqlite3', install=args[3])

        def rows_of(store, sql, *params):
            conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True, timeout=10)
            try:
                return conn.execute(sql, params).fetchall()
            finally:
                conn.close()

        def entity(store, identity):
            found = rows_of(store, 'SELECT kind, data FROM entities WHERE id=?', identity)
            return (found[0][0], json.loads(found[0][1])) if found else (None, None)

        def journal(store):
            return h['journal'](store)

        def steps_of(report):
            return {s.get('step'): s for s in report.get('steps') or []}

        # ---- the owner's host: four accounts, one Claude Code account logged out ----------------------------
        main = host('main', ACCOUNTS)
        report, store, root = main['report'], main['store'], main['root']
        ok = main['code'] == 0 and report.get('outcome') == 'set_up'
        for row in ROWS:
            if row not in ('format/fake-lines', 'install/asset') and (ok or row not in ('fresh/one-engine', 'rerun/over-earlier-host')):
                check(row, 'setup laid the owner\'s host down [%s %s]' % (report.get('outcome'), report.get('reason')), ok)
        if not ok:
            return
        config_path = Path(report['home']) / 'config' / 'service.json'
        config = json.loads(config_path.read_text())
        receivers = {path: json.loads(Path(path).read_text()) for path in (config['receiver']['configs'] or {}).values()}
        ids = report['authority_ids']
        repository = ids['repository_uuid']
        steps = steps_of(report)
        TR = load('v185_routes', h['mods'] / 'control_team_routes.py')
        CG = load('v185_config', h['mods'] / 'control_agent_config.py')
        CT = TR.CT
        team = (entity(store, TR.default_id(1))[1] or {}).get('team') or {}

        with section('fresh/team'):
            # AC1: the default team, saved by the owner's signed commands through VELDO-0203, read back.
            _kind, head = entity(store, TR.HEAD)
            _kind, saved = entity(store, TR.default_id(1))
            team = (saved or {}).get('team') or {}
            engines = {role: spec.get('engines') for role, spec in (team.get('roles') or {}).items()}
            check('fresh/team', 'the default team is at revision 1, saved by the owner, with the four required roles on '
                  'the walkthrough\'s engines [%s]' % engines,
                  (head or {}).get('revision') == 1 and (saved or {}).get('saved_by') == owner
                  and engines == {'project_manager': ['claude_code'], 'elaboration': ['claude_code'],
                                  'implementation': ['claude_code'], 'independent_review': ['codex']})
            conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True)
            try:
                configurations = {role: CG.read(conn, ids['domain_uuid'], repository, role, 1) for role in CT.REQUIRED_ROLES}
            except CG.Refused as error:
                configurations = {'refused': error.code}
            finally:
                conn.close()
            check('fresh/team', 'one capability configuration revision per role, its engine the team\'s, each referenced by '
                  'the team [%s]' % {r: (c.get('engine'), c.get('revision')) for r, c in configurations.items()
                                     if isinstance(c, dict)},
                  set(configurations) == set(CT.REQUIRED_ROLES)
                  and all(c.get('engine') == engines[r][0] and c.get('revision') == 1 for r, c in configurations.items())
                  and all(team['roles'][r]['capability_configuration'] == {'role': r, 'revision': 1} for r in CT.REQUIRED_ROLES))
            records = journal(store)
            owner_saves = [r for r in records if r['command_id'].endswith(('-default-team',)) or '-configuration-' in r['command_id']]
            check('fresh/team', 'five owner revisions in the journal, each signed by the owner\'s command, its nonce its '
                  'command id [%s]' % [(r['command_id'], r['principal']) for r in owner_saves],
                  len(owner_saves) == 5 and all(r['principal'] == owner and r['nonce'] == r['command_id'] for r in owner_saves))
            _kind, project = entity(store, 'project:factory')
            # VELDO-0143: the factory project runs on a small repository of its own, under the state root, that holds
            # only its team configuration, never on the workspace's.
            factory = steps.get('factory_repository', {})
            factory_files = sorted(os.listdir(factory['path'])) if os.path.isdir(factory.get('path') or '') else None
            check('fresh/team', 'the factory project is active, owned by the owner, on its own repository [%s]'
                  % {k: (project or {}).get(k) for k in ('owner', 'state', 'execution_repository')},
                  (project or {}).get('owner') == owner and (project or {}).get('state') == 'ACTIVE'
                  and (project or {}).get('execution_repository') == factory.get('repository_uuid')
                  and factory.get('repository_uuid') not in (None, repository)
                  and factory_files == ['.git', 'team.json'])
            check('fresh/team', 'setup reports each dispatch step done [%s]' % sorted(
                  (n, steps.get(n, {}).get('outcome')) for n in ('work_configuration', 'reservation_principals',
                                                                 'factory_project', 'default_team', 'account_registration',
                                                                 'reservation_policies')),
                  all(steps.get(n, {}).get('outcome') == 'done' for n in (
                      'work_configuration', 'reservation_principals', 'factory_project', 'default_team',
                      'account_registration', 'reservation_policies')))

        with section('team/newest-model'):
            # The Codex roles start on the newest model of the qualified catalog, never an older one by default.
            newest, listed = newest_model()
            conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True)
            try:
                saved_model = (CG.read(conn, ids['domain_uuid'], repository, 'independent_review', 1).get('settings')
                               or {}).get('model')
            finally:
                conn.close()
            priority = {m['slug']: m['priority'] for m in listed}
            check('team/newest-model', 'the Codex reviewer\'s saved configuration names the newest model of the qualified '
                  'catalog, no listed model newer [%s; newest %s; listed %s]'
                  % (saved_model, newest, sorted((m['priority'], m['slug']) for m in listed)),
                  saved_model == newest and saved_model in priority
                  and all(m['priority'] >= priority[saved_model] for m in listed))

        with section('fresh/adapters'):
            # AC1: the adapters and the work configuration, through the installer's options.
            engines186 = h['engines186']
            vendor = str(Path(engines186['vendor']).resolve())
            for path, receiver in sorted(receivers.items()):
                adapters = receiver.get('adapters') or {}
                check('fresh/adapters', 'the receiver names both adapters: Claude Code its pinned version, Codex its vendor '
                      'binary, each checking the account login [%s]' % {k: v.get('executable') for k, v in adapters.items()},
                      set(adapters) == {'claude_code', 'codex'}
                      and adapters['claude_code'].get('executable') == {'version': engines186['version']}
                      and adapters['claude_code'].get('engine') == 'claude_code'
                      and adapters['codex'].get('executable') == vendor and adapters['codex'].get('argv', [None])[0] == vendor
                      and all(a.get('account_login') is True for a in adapters.values()))
            work_path = config.get('work')
            work = json.loads(Path(work_path).read_text()) if work_path and Path(work_path).is_file() else {}
            line = (work.get('repositories') or {}).get(repository) or {}
            builder, reviewers = line.get('builder') or {}, line.get('reviewers') or []
            check('fresh/adapters', 'the installed work configuration is 0600 and names the enrolled repository [%s]'
                  % work_path, work_path == str(Path(report['home']) / 'config' / 'work.json')
                  and oct(stat.S_IMODE(os.stat(work_path).st_mode)) == '0o600'
                  and work.get('schema') == 'veldo.factory_work/v1' and list(work.get('repositories') or {}) == [repository])
            check('fresh/adapters', 'its builder comes from the implementation role and its reviewer from independent_review, '
                  'each with control_service ROLE_FIELDS [%s, %s]' % (builder, reviewers),
                  set(builder) == set(h['CS'].ROLE_FIELDS) and builder.get('identity') == team['roles']['implementation']['workers'][0]
                  and builder.get('adapter') == 'claude_code'
                  and builder.get('configuration') == {'role': 'implementation', 'revision': 1}
                  and builder.get('seconds') == team['roles']['implementation']['budget']['wall_seconds']
                  and len(reviewers) == 1 and set(reviewers[0]) == set(h['CS'].ROLE_FIELDS)
                  and reviewers[0].get('identity') == team['roles']['independent_review']['workers'][0]
                  and reviewers[0].get('adapter') == 'codex'
                  and reviewers[0].get('configuration') == {'role': 'independent_review', 'revision': 1})
            check('fresh/adapters', 'the work configuration setup wrote is the one installed',
                  bool(work) and (root / 'host' / 'work.json').is_file()
                  and (root / 'host' / 'work.json').read_text() == Path(work_path).read_text())

        with section('fresh/registered'):
            # AC4: every account the registry lists has its store record with the fields registration prints.
            for name, provider, _logged in ACCOUNTS:
                _kind, record = entity(store, 'account:' + name)
                fields = AR.registration(name, root=os.path.join(CEN.git_common_dir(str(main['workspace'])), 'veldo'))
                check('fresh/registered', '%s: one store record with the fields registration prints [%s]'
                      % (name, {k: (record or {}).get(k) for k in ('provider', 'label', 'concurrency')}),
                      record is not None and record.get('provider') == fields['provider'] == provider
                      and record.get('label') == fields['label'] and record.get('profiles') == fields['profiles']
                      and record.get('concurrency') == 1 and record.get('status') == 'active')
                journaled = [r for r in records if r['command_id'] == 'register/' + name]
                check('fresh/registered', '%s: registered by command register/%s as the owner' % (name, name),
                      len(journaled) == 1 and journaled[0]['principal'] == owner)
                _kind, policy = entity(store, RES.entity('policy', [ids['domain_uuid'], 'account', name]))
                check('fresh/registered', '%s: its VELDO-0204 reservation policy exists before the service starts [%s]'
                      % (name, (policy or {}).get('caps')), bool((policy or {}).get('caps')))
            enrolled = next((i for i, r in enumerate(records) if 'reservation_service' in json.dumps(r['transition'])
                             and r['principal'] == owner), None)
            provisioned = next((i for i, r in enumerate(records) if r['command_id'].startswith('reservation-policy/')), None)
            registered_at = [i for i, r in enumerate(records) if r['command_id'].startswith('register/')]
            check('fresh/registered', 'the accounts were registered after the reservation enrollment and before the '
                  'policies [%s, %s, %s]' % (enrolled, registered_at, provisioned),
                  enrolled is not None and provisioned is not None and registered_at
                  and enrolled < min(registered_at) and max(registered_at) < provisioned)

        with section('login/named'):
            # AC4: setup names the account not logged in, with its login step, and the others carry on.
            logins = {e['account']: e for e in (steps.get('account_login') or {}).get('accounts') or []}
            check('login/named', 'setup checked every account\'s own login [%s]'
                  % {k: (v.get('outcome'), v.get('login')) for k, v in logins.items()},
                  set(logins) == {a[0] for a in ACCOUNTS}
                  and all(logins[n]['outcome'] == ('logged_in' if logged else 'refused') for n, _p, logged in ACCOUNTS))
            out = logins.get(LOGGED_OUT) or {}
            record = AR.get(LOGGED_OUT, os.path.join(CEN.git_common_dir(str(main['workspace'])), 'veldo'))
            check('login/named', 'the logged-out account is refused by name with its login step [%s]'
                  % {k: out.get(k) for k in ('refusal', 'login', 'login_step')},
                  out.get('refusal') == 'missing_authority:account_login:' + LOGGED_OUT and out.get('login') == 'not_logged_in'
                  and out.get('login_step') == AR.login_step(record)
                  and (steps.get('account_login') or {}).get('refusals') == ['missing_authority:account_login:' + LOGGED_OUT])
            check('login/named', 'setup still laid the factory down and reports one account not logged in',
                  report.get('outcome') == 'set_up' and (report.get('dispatch') or {}).get('metrics', {}).get('not_logged_in') == 1)

        with section('reservation/principals'):
            # AC2: the two principals hold the reservation_service role by the owner's signed enrollment.
            for principal in ('authority', 'launch-receiver'):
                _kind, member = entity(store, principal)
                journaled = [r for r in records if r['principal'] == owner and principal in r['transition']
                             and 'enroll_principal' in r['command_id']]
                check('reservation/principals', '%s holds reservation_service, enrolled by the owner\'s signed command [%s]'
                      % (principal, (member or {}).get('roles')),
                      'reservation_service' in ((member or {}).get('roles') or []) and len(journaled) == 1)

        with section('reservation/state-root'):
            # AC2: the state root in every receiver, and what resolves under it.
            for path, receiver in sorted(receivers.items()):
                check('reservation/state-root', 'the receiver carries the state root, and its records, runs and pinned engine '
                      'resolve under it [%s]' % receiver.get('state_root'),
                      receiver.get('state_root') == str(root)
                      and str(L.ER.directory(receiver)).startswith(str(root) + '/')
                      and str(L.runs_root(receiver)).startswith(str(root) + '/')
                      and 'claude_code' in (receiver.get('adapters') or {})
                      and L.ENGINES['claude_code'].bind(receiver['adapters']['claude_code'], receiver['state_root'])['path']
                      .startswith(str(root) + '/'))

        with section('loop/configured', 'every-account', 'login/receiver-refuses', 'reservation/principals'):
            # ---- the installed factory runs: loop configured, units built and reviewed on every account ------------
            unit = report['unit']
            started = main['manager'].start(unit)
            check('loop/configured', 'the installed authority started [%s]' % (started,), started[0] == 0)
            if started[0]:
                raise RuntimeError('the installed authority did not start')
            try:
                status = h['service_send'](root, {'operation': 'inspect', 'entity_ids': []})
                loop = ((status or {}).get('result') or {}).get('loop') or {}
                check('loop/configured', 'the running service\'s loop is available and configured, with no refusal [%s]'
                      % {k: loop.get(k) for k in ('available', 'configured', 'refusal')},
                      loop.get('available') is True and loop.get('configured') is True and not loop.get('refusal'))
                if loop.get('configured') is True:
                    journey(h, main, ids, L, RES)
                else:
                    for row in ('every-account', 'login/receiver-refuses'):
                        check(row, 'the installed service has a configured loop to dispatch through', False)
            finally:
                main['manager'].stop(unit)

        with section('login/retry-excludes', 'login/recheck'):
            # R1, R2: the production Line and pool over a store of their own, with the main host's receiver adapters
            # and state root, so the Line reads each account's login with the pinned engine as the receiver does.
            from types import SimpleNamespace
            CSm = h['CS']
            POOL = CSm.L.D.RES.POOL
            receiver = receivers[sorted(receivers)[0]]

            def memory(accounts, refused_on):
                conn = sqlite3.connect(':memory:')
                conn.execute('CREATE TABLE entities (id TEXT PRIMARY KEY, kind TEXT, data TEXT)')
                for name, utilization, profile in accounts:
                    windows = ({'five_hour': dict(status='allowed', utilization=utilization, reset_at=time.time() + 86400)}
                               if utilization is not None else {})
                    conn.execute('INSERT INTO entities VALUES (?, ?, ?)', (CSm.L.ACC.entity_id(name), CSm.L.ACC.KIND, json.dumps(
                        dict(id=name, provider='claude_code', status='active', concurrency=1,
                             profiles={hostname: str(profile)}, windows=windows))))
                contract = dict(repository=repository, unit='v185-r', station='build', reservation={'account': refused_on},
                                capability={'adapter': 'claude_code', 'configuration': {}},
                                input={'context': {'holder': 'builder'}, 'payload': {}}, source={'commit': 'abc'})
                record = dict(dispatch_id='v185-refused', state='refused', contract=contract,
                              refusal=CSm.L.ACCOUNT_LOGIN + refused_on, history=[{'state': 'refused', 'at': 1}])
                conn.execute('INSERT INTO entities VALUES (?, ?, ?)', ('v185-refused', CSm.L.D.RECORD_KIND, json.dumps(record)))
                return conn, record

            def line_on(conn):
                line = CSm.Line.__new__(CSm.Line)
                line.service, line.repository = SimpleNamespace(conn=conn), repository
                line.engines = {name: adapter['engine'] for name, adapter in receiver['adapters'].items()}
                line.adapters, line.state_root, line.host = receiver['adapters'], receiver['state_root'], hostname
                line.roles = {'builder': {'identity': 'builder'}}
                offers = []
                line.offer = lambda report, unit, station, role, **kwargs: offers.append(kwargs)
                return line, offers

            # R1: the review's case, the logged-out account at a lower utilization than the healthy one.
            profiles = base / 'v185-retry-profiles'
            for name in ('v185-out', 'v185-healthy'):
                (profiles / name).mkdir(parents=True, mode=0o700)
            (profiles / 'v185-healthy' / '.credentials.json').write_text('{}\n')
            conn, record = memory([('v185-out', 0.1, profiles / 'v185-out'), ('v185-healthy', 0.8, profiles / 'v185-healthy')],
                                  'v185-out')
            line, offers = line_on(conn)
            line.limited(record, {'refused': []})
            check('login/retry-excludes', 'the retry reads the refused account\'s login again and passes it, still not '
                  'logged in, to the pool as excluded [%s]' % offers, len(offers) == 1 and offers[0].get('exclude') == ['v185-out'])
            ledger, chosen = {}, []
            for request in ({'engine': 'claude_code', 'host': hostname},
                            {'engine': 'claude_code', 'host': hostname, 'exclude': ['v185-out']}):
                for n in range(3):
                    choice = POOL.choose(conn, ledger, request, time.time(), lambda account: None)
                    chosen.append(choice['account'])
                    ledger['v185-%d' % len(chosen)] = dict(type='worker', context={'account': choice['account']},
                                                           retired=True, reserved_seq=100 + len(chosen))
            excluded = POOL.choose(conn, {}, {'engine': 'claude_code', 'host': hostname, 'exclude': ['v185-out']},
                                   time.time(), lambda account: None)
            check('login/retry-excludes', 'the pool never chooses the login-refused account while the healthy one can '
                  'take the work, though its utilization is lower, excluded or not [%s; passed %s]'
                  % (chosen, excluded.get('trace', {}).get('passed')),
                  chosen == ['v185-healthy'] * 6
                  and excluded.get('trace', {}).get('passed', {}).get('v185-out') == 'account_login:excluded')
            conn.close()

            # R2: the only account refuses, logs in, and is offered the unit again.
            only = base / 'v185-recheck-profile'
            only.mkdir(mode=0o700)
            conn, record = memory([('v185-only', None, only)], 'v185-only')
            line, offers = line_on(conn)
            waiting = {'refused': []}
            line.limited(record, waiting)
            named = (waiting['refused'] or [{}])[0]
            check('login/recheck', 'not logged in when read again, the only account is excluded and the unit waits, named '
                  'with the login read [%s; offers %s]' % (named, offers),
                  not offers and named.get('refusals') == [CSm.L.ACCOUNT_LOGIN + 'none_left']
                  and named.get('logins') == {'v185-only': 'not_logged_in'})
            (only / '.credentials.json').write_text('{}\n')
            again = {'refused': []}
            line.limited(record, again)
            check('login/recheck', 'logged in again, the same account is offered the unit again with nothing excluded '
                  '[%s; %s]' % (offers, again), len(offers) == 1 and not offers[0].get('exclude') and not again['refused'])
            picked = POOL.choose(conn, {}, {'engine': 'claude_code', 'host': hostname}, time.time(), lambda account: None)
            check('login/recheck', 'the pool chooses it, the one account left, despite its earlier refusal [%s]'
                  % picked.get('account'), picked.get('account') == 'v185-only')
            conn.close()

        with section('reservation/principals'):
            # AC2: a slot reserved as each principal, through the production authorization.
            writer = S.open_store(str(store))
            try:
                IN = load('v185_ingress', h['mods'] / 'control_channel_ingress.py')
                _principal, sign = IN.journal_signer({'principal': 'authority', 'key': str(root / 'keys' / 'journal')})
                for principal, engine in (('authority', 'codex'), ('launch-receiver', 'claude_code')):
                    reservations = RES.Reservations(S, writer, domain=ids['domain_uuid'], repository=repository,
                                                    principal=principal, authorize=RES.service_authority, signer=principal,
                                                    sign=sign)
                    try:
                        reservations.reserve_pooled('v185-probe-' + principal, 'v185-probe-' + principal,
                                                    {'engine': engine, 'host': hostname}, 'factory', 'v185-u1', now=time.time())
                        refusal = None
                    except Exception as error:  # noqa: BLE001 - the reservation service's refusal is the row's data
                        refusal = getattr(error, 'code', type(error).__name__)
                    check('reservation/principals', '%s reserves an account slot through the reservation service [%s]'
                          % (principal, refusal), refusal is None)
            finally:
                writer.close()

        with section('rerun/changes-nothing'):
            # ---- AC3: a second run over the complete host changes nothing ---------------------------------------
            trees = (root, main['install'], main['units'])
            # The store is read first: a reader's shared-memory index exists before both snapshots.
            head = journal(store)
            before = h['snapshot'](*trees)
            code, again = h['setup'](*main['args'])
            after = h['snapshot'](*trees)
            changed = h['changes'](before, after)
            outcomes = steps_of(again)
            check('rerun/changes-nothing', 'the second run answers already_set_up, every step already done, deferred or '
                  'checked [%s %s %s]' % (again.get('outcome'), again.get('reason'),
                                          sorted((n, s.get('outcome')) for n, s in outcomes.items())),
                  code == 0 and again.get('outcome') == 'already_set_up'
                  and all(s.get('outcome') in ('already_done', 'deferred', 'checked', 'refused') for s in outcomes.values())
                  and (outcomes.get('account_login') or {}).get('outcome') == 'refused')
            check('rerun/changes-nothing', 'every file under the state root, install root and unit directory is byte for '
                  'byte the same [%s]' % (changed,), changed == ([], [], []))
            check('rerun/changes-nothing', 'nothing pinned or installed again [%s]' % again.get('pins_made'),
                  again.get('pins_made') == 0)
            check('rerun/changes-nothing', 'the journal head is unchanged [%s]'
                  % [r['command_id'] for r in journal(store)[len(head):]], journal(store) == head)

        with section('rerun/missing-state-root'):
            # R3: a receiver that lacks the state_root key is repaired as one holding it as null.
            lacking = sorted(receivers)[0]
            held = json.loads(Path(lacking).read_text())
            held.pop('state_root', None)
            Path(lacking).write_text(json.dumps(held, indent=1, sort_keys=True) + '\n')
            code, repaired = h['setup'](*main['args'])
            added = (steps_of(repaired).get('receiver_configuration') or {}).get('added') or []
            check('rerun/missing-state-root', 'setup run again over a receiver lacking its state_root key succeeds and adds '
                  'it [%s %s %s]' % (code, repaired.get('reason'), added),
                  code == 0 and json.loads(Path(lacking).read_text()).get('state_root') == str(root)
                  and {'path': lacking, 'keys': ['state_root']} in added)

        with section('team/workers'):
            # R4: every worker the default team names is enrolled, so the owner's application of it staffs a project.
            records = journal(store)
            for worker in ('elaborator', 'builder', 'reviewer'):
                kind, member = entity(store, worker)
                journaled = [r for r in records if r['principal'] == owner and worker in r['transition']
                             and 'enroll_principal' in r['command_id']]
                check('team/workers', '%s is enrolled, a service principal of its own independence group, by the owner\'s '
                      'signed command [%s]' % (worker, {k: (member or {}).get(k) for k in ('principal_type', 'independence_group',
                                                                                          'scope', 'revoked_at')}),
                      kind == 'membership' and member.get('principal_type') == 'service'
                      and member.get('independence_group') == worker and member.get('revoked_at') is None and len(journaled) == 1)
            D = load('v185_team_dispatch', h['mods'] / 'control_factory_setup_dispatch.py')
            ACT = load('v185_team_activation', h['mods'] / 'control_channel_activation.py')
            owner_sign = ACT.ssh_signer(h['owner_key'])
            lock = h['F'].take_lock(str(root))
            writer = D.Store(Path(report['home']) / 'bin', root / 'host' / 'ingress.json', owner, owner_sign, lock)
            try:
                routes = writer.revisions()[1].team_routes
                default = routes.read_default(1)
                command = dict(writer.ids, operation='propose', project='factory', principal=owner, command_id='v185-team',
                               nonce='v185-team', team_version=0, team=default['team'])
                answer = routes.teams.apply(dict(command=command, signature=owner_sign(writer.S.canonical_bytes(command))))
            finally:
                writer.close()
                os.close(lock)
            check('team/workers', 'the owner\'s signed proposal staffing factory with the saved default team is accepted '
                  '[%s %s]' % (answer.get('reason'), answer.get('problems')), answer.get('ok') is True)

        with section('fresh/one-engine'):
            # ---- AC1, one engine: a registry naming only Claude Code puts all four roles on it -------------------
            one = host('one', (('solo-a', 'claude_code', True),))
            one_steps = steps_of(one['report'])
            check('fresh/one-engine', 'setup laid the host down [%s]' % one['report'].get('reason'),
                  one['code'] == 0 and one['report'].get('outcome') == 'set_up')
            if one['code'] == 0:
                _kind, solo = entity(one['store'], TR.default_id(1))
                one_config = json.loads((Path(one['report']['home']) / 'config' / 'service.json').read_text())
                one_receiver = json.loads(Path(next(iter(one_config['receiver']['configs'].values()))).read_text())
                one_work = json.loads(Path(one_config['work']).read_text()) if one_config.get('work') else {}
                line = (one_work.get('repositories') or {}).get(one['report']['authority_ids']['repository_uuid']) or {}
                check('fresh/one-engine', 'the installation names a work configuration [%s]' % one_config.get('work'),
                      bool(line))
                check('fresh/one-engine', 'all four roles on Claude Code, one adapter, both work roles on it [%s]'
                      % {r: s.get('engines') for r, s in ((solo or {}).get('team') or {}).get('roles', {}).items()},
                      all(s.get('engines') == ['claude_code'] for s in ((solo or {}).get('team') or {}).get('roles', {}).values())
                      and set(one_receiver.get('adapters') or {}) == {'claude_code'}
                      and line.get('builder', {}).get('adapter') == (line.get('reviewers') or [{}])[0].get('adapter')
                      == 'claude_code'
                      and (one_steps.get('account_login') or {}).get('outcome') == 'checked')

        # ---- AC3: over a host laid down before this change, only these steps write ---------------------------
        with section('rerun/over-earlier-host'):
            earlier(h, host, journal, steps_of, entity)

    def journey(h, main, ids, L, RES):
        """Units submitted after setup are built and reviewed through the installed service and receiver alone."""
        S, root, store, owner = h['S'], main['root'], main['store'], h['owner']
        repository, domain = ids['repository_uuid'], ids['domain_uuid']
        CLM = load('v185_claim', h['mods'] / 'control_claim.py')
        IN = load('v185_journey_ingress', h['mods'] / 'control_channel_ingress.py')
        principal, sign = IN.journal_signer({'principal': 'authority', 'key': str(root / 'keys' / 'journal')})
        names = ['v185-u%d' % n for n in range(1, 4)]
        writer = S.open_store(str(store))
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}
        serial = [0]

        def version(identity):
            return (writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone() or (0,))[0]

        def put(identity, kind, data):
            serial[0] += 1
            command = 'v185-put-%d' % serial[0]
            S.execute(writer, dict(command_id=command, principal=principal, operation='upsert_entity', nonce=command,
                                   artifact_digests=[], expected_versions={identity: version(identity)},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), principal, sign, 1)
        try:
            for name in names:
                put(name, 'execution_unit', dict(state='READY', repository_uuid=repository, backlog_item_uuid='backlog:' + name,
                                                 requirements=[], eligible_holders=['builder'], project='factory',
                                                 scope_digest='sha256:scope-' + name, revision=1, depends_on=[],
                                                 producer='builder', risk='standard'))
                put('backlog:' + name, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=repository))
                put('admission:' + name, 'admission', dict(unit=name, state='accepted', scope_digest='sha256:scope-' + name))
                cid = CLM.claim_id(repository, name)
                S.execute(writer, dict(command_id='v185-claim-' + name, principal='builder', operation='claim_operation',
                                       nonce='v185-claim-' + name, artifact_digests=[],
                                       expected_versions={name: version(name), 'backlog:' + name: version('backlog:' + name),
                                                          cid: version(cid)},
                                       parameters=dict(action='claim', unit_id=name, backlog_item_uuid='backlog:' + name,
                                                       claim_id=cid, holder='builder', generation=0, capabilities=[],
                                                       repository_uuid=repository)), 'builder', sign, 1)
        finally:
            writer.close()

        # The submission's last command goes through the running service: the journal wake of its loop.
        def note(n):
            body = dict(ids, command_id='v185-note-%d' % n, principal=owner, operation='upsert_entity',
                        nonce='v185-note-nonce-%d' % n, artifact_digests=[], expected_versions={'v185-note-%d' % n: 0},
                        parameters=dict(entity_id='v185-note-%d' % n, kind='note', data={'n': n}))
            return h['service_send'](root, {'command': body, 'signature': h['sign_with'](h['owner_key'], S.canonical_bytes(body))})
        woke = note(1)
        check('every-account', 'the submission reached the running service [%s]' % ((woke or {}).get('result') or woke),
              ((woke or {}).get('result') or {}).get('ok') is True)

        def dispatches():
            return [json.loads(d) for (d,) in sqlite3.connect('file:%s?mode=ro' % store, uri=True).execute(
                'SELECT data FROM entities WHERE kind=?', (L.D.RECORD_KIND,)).fetchall()]

        def finished(found):
            return all(any(r['contract']['unit'] == name and r['contract']['station'] == 'review' and L.D.completed(r)
                           for r in found) for name in names)

        home = Path(main['report']['home'])

        def retries(found):
            refused_ids = [r['dispatch_id'] for r in found if r['contract']['reservation']['account'] == LOGGED_OUT]
            # Dispatch state and the completed loop-pass observation are separate writes. Wait for both;
            # ignore an unfinished final line while the service appends its observation.
            passes = [json.loads(line) for line in (home / 'state' / 'observations.jsonl').read_text().splitlines(True)
                      if line.endswith('\n') and '"loop_pass"' in line]
            reruns = [o for p in passes for o in p.get('offered') or [] if o.get('rerun_of') in refused_ids]
            return refused_ids, reruns

        # Success needs the evidence the rows assert, not a wall-clock quiet period. Keep the overall
        # deadline as a failure bound. A completed journey with a terminal login violation can fail now.
        # The bound stays under the gate's per-worker budget (check_gate_mutations.WORKER_BUDGET, 120 s):
        # a mutant that never produces the evidence must fail here, inside the suite, so its cleanup runs;
        # a worker killed at the budget leaves its /dev/shm scratch behind and the stage goes red on that.
        # The journey takes about 12 s alone and well under a minute under gate load.
        deadline, found, refused_ids, reruns = time.monotonic() + 90, [], [], []
        while time.monotonic() < deadline:
            found = dispatches()
            refused_ids, reruns = retries(found)
            out = [r for r in found if r['dispatch_id'] in refused_ids]
            violated = any(r['state'] not in L.D.HOLDING and
                           (r['state'] != 'refused' or r.get('refusal') != L.ACCOUNT_LOGIN + LOGGED_OUT) for r in out)
            retried = (set(o.get('rerun_of') for o in reruns) == set(refused_ids)
                       and all(any(r['dispatch_id'] == o.get('dispatch_id')
                                   and r['contract']['reservation']['account'] != LOGGED_OUT for r in found)
                               for o in reruns))
            if finished(found) and refused_ids and (violated or retried):
                break
            time.sleep(1)
        by_account = {}
        for record in found:
            contract = record['contract']
            by_account.setdefault(contract['reservation']['account'], []).append(
                (contract['unit'], contract['station'], record['state'], L.D.completed(record), record.get('refusal')))
            if record['state'] == 'exited' and not L.D.completed(record):
                print('VELDO-0185 journey: %s %s exited without completion: %s %s' % (
                    contract['unit'], contract['station'], record.get('termination'),
                    {k: v for k, v in record.items() if k not in ('contract', 'termination')}))
                try:
                    receiver = json.loads(Path(next(iter(json.loads((Path(main['report']['home']) / 'config' / 'service.json')
                                                                     .read_text())['receiver']['configs'].values()))).read_text())
                    page = L.ER.read(L.ER.directory(receiver), record['dispatch_id'], 0, 50)
                    for kept in page['lines']:
                        print('VELDO-0185 journey line: %s' % json.dumps(kept)[:600])
                except Exception as error:  # noqa: BLE001
                    print('VELDO-0185 journey line: unreadable %s' % error)
        check('every-account', 'every unit was built and reviewed, each to a completion [%s]' % by_account, finished(found))
        for name, provider, logged in ACCOUNTS:
            runs = [r for r in by_account.get(name, []) if r[3]]
            if logged:
                check('every-account', '%s (%s) ran at least one build or review to a completion' % (name, provider),
                      bool(runs))
        codex_runs = [r for r in by_account.get('codex-a', []) if r[3]]
        check('every-account', 'the Codex account ran the reviews and Claude Code the builds [%s]' % codex_runs,
              codex_runs and all(r[1] == 'review' for r in codex_runs)
              and all(r[1] == 'build' for n in ('claude-b', 'claude-c') for r in by_account.get(n, []) if r[3]))

        # AC4: the logged-out account takes no work: refused before spawn, and the unit is offered elsewhere.
        check('login/receiver-refuses', 'the first build was offered to the logged-out account',
              any(r['contract']['unit'] == names[0] and r['contract']['station'] == 'build'
                  and r['contract']['attempt'] == 1 and r['contract']['reservation']['account'] == LOGGED_OUT
                  for r in found))
        out = by_account.get(LOGGED_OUT, [])
        check('login/receiver-refuses', 'every dispatch on the logged-out account was refused by name before spawn [%s]'
              % out, out and all(r[2] == 'refused' and r[4] == 'missing_authority:account_login:' + LOGGED_OUT
                                 for r in out))
        invocations = rows_count = [d for d in refused_ids if sqlite3.connect('file:%s?mode=ro' % store, uri=True).execute(
            'SELECT 1 FROM entities WHERE id=?', (RES.entity('invocation', [domain, 'invocation/' + d]),)).fetchone()]
        check('login/receiver-refuses', 'no invocation was reserved for a refused dispatch [%s]' % rows_count,
              refused_ids and not invocations)
        check('login/receiver-refuses', 'the Line offered each refused unit\'s station again on another account at its '
              'next pass [%s]' % [(o.get('unit'), o.get('station'), o.get('rerun_of')) for o in reruns],
              len(reruns) == len(refused_ids) and {o.get('rerun_of') for o in reruns} == set(refused_ids)
              and all(any(r['dispatch_id'] == o.get('dispatch_id') and r['contract']['reservation']['account'] != LOGGED_OUT
                          for r in found) for o in reruns))
        # R1: the installed service read the refused account's login again and passed it to the pool as excluded.
        conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True)
        try:
            workers = {w.get('dispatch'): w for w in (json.loads(d) for (d,) in conn.execute(
                "SELECT data FROM entities WHERE kind='subscription_reservation'")) if w.get('type') == 'worker'}
        finally:
            conn.close()
        traces = [(workers.get(o.get('dispatch_id')) or {}).get('selection') or {} for o in reruns]
        check('login/retry-excludes', 'each retry of a dispatch refused for its login chose another account, the refused '
              'one passed over as excluded [%s]' % [(t.get('chosen'), (t.get('passed') or {}).get(LOGGED_OUT)) for t in traces],
              traces and all(t.get('chosen') not in (None, LOGGED_OUT)
                             and (t.get('passed') or {}).get(LOGGED_OUT) == 'account_login:excluded' for t in traces))

        # AC2: both principals reserved through the reservation service in the journey.
        records = h['journal'](store)
        workers = {r['principal'] for r in records if any(k.startswith(RES.PREFIX + 'worker:') for k in r['transition'])}
        calls = {r['principal'] for r in records if any(k.startswith(RES.PREFIX + 'invocation:') for k in r['transition'])}
        check('reservation/principals', 'the service reserved worker slots as authority and the receiver its calls as '
              'launch-receiver [%s, %s]' % (sorted(workers), sorted(calls)),
              'authority' in workers and 'launch-receiver' in calls)

    def earlier(h, host, journal, steps_of, entity):
        """A host laid down by the engine before this change (its whole .veldo, from history), then set up again."""
        row = 'rerun/over-earlier-host'
        shipped = h['_git_process'].run(['git', '-C', str(ROOT), 'archive', '--format=tar', BEFORE, '.veldo'],
                                        capture_output=True)
        older = h['base'] / ('engine-' + BEFORE)
        older.mkdir()
        if shipped.returncode or not shipped.stdout:
            check(row, 'the engine of %s is in history' % BEFORE, False)
            return
        with tarfile.open(fileobj=io.BytesIO(shipped.stdout)) as archive:
            archive.extractall(str(older), filter='data')
        # The fixture's engine records (its generated engines' digests) replace the shipped ones, as in the current tree.
        for name in ('claude-qualification.json', 'codex-qualification.json'):
            (older / '.veldo' / 'runtime' / name).write_bytes((h['mods'] / 'runtime' / name).read_bytes())
        F0 = load('v185_setup_before', older / '.veldo' / 'control_factory_setup.py')
        laid = host('earlier', ACCOUNTS, module=F0)
        check(row, 'the earlier engine laid a host down [%s %s]' % (laid['report'].get('outcome'), laid['report'].get('reason')),
              laid['code'] == 0 and laid['report'].get('outcome') == 'set_up')
        if laid['code'] != 0:
            return
        store = laid['store']
        TR = load('v185_earlier_routes', h['mods'] / 'control_team_routes.py')
        check(row, 'that host has no default team, no reservation principal and no account record',
              entity(store, TR.HEAD)[0] is None and entity(store, 'authority')[0] is None
              and entity(store, 'account:claude-a')[0] is None)
        # One receiver holds its state root as null, as an installation not made by setup leaves it.
        laid_config = json.loads((Path(laid['report']['home']) / 'config' / 'service.json').read_text())
        nulled = sorted(laid_config['receiver']['configs'].values())[0]
        held = json.loads(Path(nulled).read_text())
        held['state_root'] = None
        Path(nulled).write_text(json.dumps(held, indent=1, sort_keys=True) + '\n')
        head = journal(store)
        code, report = h['setup'](*laid['args'])
        steps = steps_of(report)
        mine = {'work_configuration', 'receiver_configuration', 'reservation_principals', 'factory_project', 'default_team',
                'account_registration', 'reservation_policies'}
        # VELDO-0142: the current setup records the workspace repository with its Git identity, so a host the
        # earlier engine laid down without one gains it in this same run.
        if 'git_identities' in __import__('inspect').signature(h['F'].setup).parameters:
            mine.add('git_identities')
        wrote ={name for name, s in steps.items() if s.get('outcome') == 'done'}
        check(row, 'the run adds exactly these steps, after the engine upgrade the changed engine needs [%s %s %s]'
              % (report.get('outcome'), report.get('reason'), sorted(wrote)),
              code == 0 and report.get('outcome') == 'set_up' and wrote == mine | {'engine_upgrade'})
        if code != 0:
            return
        added = journal(store)[len(head):]
        ours = re.compile(r'setup-enroll_principal-[0-9a-f]{8}-[0-9a-f]{12}|setup-[0-9a-f]{8}-[0-9a-f]{8}-'
                          r'(factory-project|default-team|configuration-[a-z_]+)|register/[a-z0-9.-]+|reservation-policy/.+')
        foreign = [r['command_id'] for r in added if not ours.fullmatch(r['command_id'])]
        check(row, 'every journal record it added is one of these steps [%s]' % foreign, added and not foreign)
        _kind, member = entity(store, 'launch-receiver')
        check(row, 'the store now holds the team, the principals\' role and every account',
              entity(store, TR.HEAD)[0] is not None and 'reservation_service' in ((member or {}).get('roles') or [])
              and all(entity(store, 'account:' + a[0])[0] == 'account' for a in ACCOUNTS))
        config = json.loads((Path(report['home']) / 'config' / 'service.json').read_text())
        receiver = json.loads(Path(next(iter(config['receiver']['configs'].values()))).read_text())
        added = (steps.get('receiver_configuration') or {}).get('added') or []
        check(row, 'the installation gained its work configuration, the receiver its adapters and the state root it '
              'held as null [%s]' % added,
              config.get('work') and Path(config['work']).is_file()
              and set(receiver.get('adapters') or {}) == {'claude_code', 'codex'}
              and json.loads(Path(nulled).read_text()).get('state_root') == str(laid['root'])
              and {'path': nulled, 'keys': ['adapters', 'state_root']} in added)
        trees = (laid['root'], laid['install'], laid['units'])
        head = journal(store)
        before = h['snapshot'](*trees)
        code, third = h['setup'](*laid['args'])
        check(row, 'a third run changes nothing [%s]' % (h['changes'](before, h['snapshot'](*trees)),),
              code == 0 and third.get('outcome') == 'already_set_up' and h['snapshot'](*trees) == before
              and journal(store) == head)

    def teardown(h):
        nonlocal fake_capture
        base, fake = h['base'], h['engines186']['fake']
        L = load('v185_format_launch', h['mods'] / 'control_launch.py')
        try:
            pass
        finally:
            fake_capture = conform_formats.conform_fake(locals(), '0185_dispatch_setup')
            check('format/fake-lines', 'generated CLI lines conform to the capture', not fake_capture[0] and bool(fake_capture[1]))

    try:
        helper.run(ROOT, PRODUCTION, exercise, teardown, fake)
    except Exception as error:
        for row in rows:
            check(row, 'ran to its end (raised ' + type(error).__name__ + ': ' + str(error)[:250] + ')', False)
    for line in conform_formats.describe('0185_dispatch_setup', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0185_dispatch_setup', not fake_capture[0])
    for row, observations in rows.items():
        for label, passed in observations:
            if not passed or os.environ.get('VELDO_0185_DETAILS'):
                print('VELDO-0185 ' + row + (' detail: ' if not passed else ' observed: ') + label)
        failed = [label for label, passed in observations if not passed]
        # A false row carries its first failed observation after its colon, which mutation workers keep.
        expect('VELDO-0185 ' + row + (': ' + failed[0][:300] if failed else ''), len(observations) >= 1 and not failed)


_v185_suite()
