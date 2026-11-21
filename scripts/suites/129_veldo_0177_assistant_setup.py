"""VELDO-0177 AC2: factory setup gives the default team an assistant role on each engine, by the owner's signed
commands, and a second setup run saves nothing again.

Run: python3 scripts/selftest.py --suite 129_veldo_0177_assistant_setup

Only shared ROOT and expect are consumed. VELDO-0171's installed-host fixture, reused through
proof/VELDO-0185/fixture.py as suite 106 reuses it, lays a host down with the real setup module through its own
command surface, into scratch, with that fixture's user manager stand-in, Tailscale stand-in and loopback Bot API. The
host's account registry is accounts.py's own file under the workspace's Git common directory (one Claude Code and one
Codex account, both logged in by a marker in their profiles). The engines are one generated fake that answers each
engine's login status and nothing else: setup launches no run. Its VELDO-0172 read-back at teardown alone passes the
fake the fixture argument that makes it print each CLI's stream (compare_formats.conform_fake), so any other call of
it still exits 2. No real key, login, token or credential is read.
"""


def _v177_setup_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import socket
    import sqlite3
    import sys

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_dispatch.py': ROOT / ".veldo" / "control_factory_setup_dispatch.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
    }
    ROWS = ('AC2/setup-saves', 'AC2/owner-signed', 'AC2/rerun-saves-nothing', 'AC2/workers-enrolled',
            'format/fake-lines')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    here = Path(__suite_file__).resolve().parents[2]
    helper = load('v177_setup_fixture', here / 'proof/VELDO-0185/fixture.py')
    conform_formats = load('v177_conform', ROOT / 'proof/VELDO-0172/compare_formats.py')
    fake_formats = load('v177_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    # One generated executable serves both engines: it is Codex when its path names codex. It answers each engine's
    # own login status from a marker in the account's profile; setup runs nothing else of it. Only VELDO-0172's
    # teardown read-back passes it READBACK first, and only then does it print each CLI's stream (VELDO-0172).
    READBACK = '--veldo-0172-format-readback'
    fake = fake_formats.embed(r'''#!@@PYTHON@@ -B
import json, os, sys, uuid
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if sys.argv[1:2] == [@@READBACK@@]:
    session = str(uuid.uuid4())
    if 'codex' not in Path(sys.argv[0]).name:
        opening = json.loads(sys.stdin.readline())
        if opening.get('type') != 'control_request':
            sys.exit(3)
        emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': opening['request_id'],
              'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
        sys.stdin.readline()
        emit({'type': 'system', 'subtype': 'init', 'cwd': str(Path.cwd()), 'session_id': session, 'tools': ['Read'],
              'mcp_servers': [], 'model': 'configured-model', 'uuid': str(uuid.uuid4())})
        emit({'type': 'assistant', 'session_id': session, 'message': {'content': [{'type': 'text', 'text': 'done'}],
              'usage': {'input_tokens': 2, 'output_tokens': 3}}})
        emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'done', 'session_id': session,
              'usage': {'input_tokens': 2, 'output_tokens': 4}})
    else:
        sys.stdin.read()
        emit({'type': 'thread.started', 'thread_id': session})
        emit({'type': 'turn.started'})
        emit({'type': 'item.completed', 'item': {'id': 'answer', 'type': 'agent_message', 'text': 'done'}})
        emit({'type': 'turn.completed', 'usage': {'input_tokens': 2, 'output_tokens': 4}})
    sys.exit(0)
if sys.argv[1:3] == ['auth', 'status']:
    logged = (Path(os.environ.get('CLAUDE_CONFIG_DIR') or '/nonexistent') / '.credentials.json').is_file()
    sys.stdout.write(json.dumps({'loggedIn': logged, 'authMethod': 'claude.ai' if logged else 'none',
                                 'apiProvider': 'firstParty'}, indent=2) + chr(10))
    sys.exit(0 if logged else 1)
if sys.argv[1:3] == ['login', 'status']:
    logged = (Path(os.environ.get('CODEX_HOME') or '/nonexistent') / 'auth.json').is_file()
    sys.stderr.write(('Logged in using ChatGPT' if logged else 'Not logged in') + chr(10))
    sys.exit(0 if logged else 1)
sys.exit(2)
'''.replace('@@PYTHON@@', sys.executable).replace('@@READBACK@@', repr(READBACK)))
    fake_capture = (['teardown not reached'], [])
    ACCOUNTS = (('claude-a', 'claude_code'), ('codex-a', 'codex'))

    def exercise(h):
        base, CEN = h['base'], h['CEN']
        AR = load('v177_accounts', h['mods'] / 'accounts.py')
        D = load('v177_dispatch', h['mods'] / 'control_factory_setup_dispatch.py')
        TR = load('v177_routes', h['mods'] / 'control_team_routes.py')
        CG = load('v177_config', h['mods'] / 'control_agent_config.py')
        E = load('v177_claude', h['mods'] / 'control_engine_claude.py')
        owner = h['owner']
        root, workspace = h['fresh_root']('state-v177'), h['clone']('clone-v177')
        registry = os.path.join(CEN.git_common_dir(str(workspace)), 'veldo')
        for name, provider in ACCOUNTS:
            profile = base / 'profiles' / name
            profile.mkdir(parents=True, mode=0o700)
            (profile / ('.credentials.json' if provider == 'claude_code' else 'auth.json')).write_text('{}\n')
            AR.account_add(name, config_dir=str(profile), root=registry, provider=provider)
        h['ts'].set('ready')
        units = base / 'units-v177'
        manager = h['Manager'](units)
        h['managers'].append(manager)
        args = (root, workspace, base / 'trust-v177' / 'host.json', base / 'install-v177', units, manager)
        code, report = h['setup'](*args)
        store = root / 'authority' / 'control.sqlite3'
        print('  VELDO-0177 setup:', code, report.get('outcome'), report.get('reason'))

        def entity(identity):
            conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True, timeout=10)
            try:
                found = conn.execute('SELECT kind, data FROM entities WHERE id=?', (identity,)).fetchone()
            finally:
                conn.close()
            return json.loads(found[1]) if found else None

        def read(role, revision):
            conn = sqlite3.connect('file:%s?mode=ro' % store, uri=True, timeout=10)
            try:
                return CG.read(conn, report['authority_ids']['domain_uuid'], report['authority_ids']['repository_uuid'],
                               role, revision)
            except CG.Refused:
                return None
            finally:
                conn.close()
        if code != 0 or report.get('outcome') != 'set_up':
            for row in ROWS:
                check(row, 'setup laid the host down [%s %s]' % (report.get('outcome'), report.get('reason')), False)
            return
        head = entity(TR.HEAD) or {}
        first, second = entity(TR.default_id(1)) or {}, entity(TR.default_id(2)) or {}
        roles = (second.get('team') or {}).get('roles') or {}
        print('  VELDO-0177 default team head %s, revision 2 roles %s' % (head.get('revision'), sorted(roles)))
        check('AC2/setup-saves', 'the default team\'s head is revision 2: VELDO-0185\'s team at revision 1, and one '
              'revision adding both assistant roles to it',
              head.get('revision') == 2 and set(roles) == set((first.get('team') or {}).get('roles') or {})
              | {'assistant', 'assistant_codex'} and second.get('previous') == first.get('digest')
              and all(roles[r] == first['team']['roles'][r] for r in first['team']['roles']))
        assistant, codex = read('assistant', 1), read('assistant_codex', 1)
        engines = json.loads((h['mods'] / 'runtime/engines.json').read_text())
        version = engines['claude_code']['version']
        qualified = E.qualified_tools(version, E.qualified(version))
        in_run = set(qualified['in_run']) & set(qualified['registry'])
        granted = {t['name'] for t in (assistant or {}).get('native_tools') or []}
        print('  VELDO-0177 assistant tools:', sorted(granted))
        check('AC2/setup-saves', '`assistant` is on Claude Code, granting the pinned version\'s in-run tools with '
              'WebSearch and WebFetch, all always',
              assistant and assistant['engine'] == 'claude_code' and granted == in_run | {'WebSearch', 'WebFetch'}
              and all(t['load'] == 'always' for t in assistant['native_tools'])
              and not granted & {'AskUserQuestion'})
        codex_tools = {t['name'] for t in (codex or {}).get('native_tools') or []}
        check('AC2/setup-saves', '`assistant_codex` is on Codex: its workspace-write sandbox with network access and '
              'web search, all always [%s %s]' % (sorted(codex_tools), (codex or {}).get('settings')),
              codex and codex['engine'] == 'codex' and 'web_search' in codex_tools
              and {'shell', 'apply_patch'} <= codex_tools
              and all(t['load'] == 'always' for t in codex['native_tools'])
              and codex['settings'].get('sandbox_mode') == 'workspace-write'
              and codex['settings'].get('network_access') == 'enabled' and codex['settings'].get('model'))
        check('AC2/setup-saves', 'each assistant role names its one capability revision',
              roles.get('assistant', {}).get('capability_configuration') == {'role': 'assistant', 'revision': 1}
              and roles.get('assistant_codex', {}).get('capability_configuration')
              == {'role': 'assistant_codex', 'revision': 1}
              and roles['assistant']['engines'] == ['claude_code'] and roles['assistant_codex']['engines'] == ['codex']
              and read('assistant', 2) is None and read('assistant_codex', 2) is None)
        records = h['journal'](store)
        saves = [r for r in records if r['principal'] == owner and any(
            key in r['transition'] for key in ('assistant', 'default-team:2', 'default_team_head'))]
        mine = [r for r in records if r['command_id'].endswith(('-configuration-assistant', '-configuration-assistant_codex',
                                                                 '-assistant-team'))]
        print('  VELDO-0177 assistant saves:', [(r['command_id'], r['principal']) for r in mine])
        check('AC2/owner-signed', 'one capability configuration revision each and one default team revision, three '
              'owner commands, each its nonce its command id',
              len(mine) == 3 and all(r['principal'] == owner and r['nonce'] == r['command_id'] for r in mine)
              and saves)
        workers = {w: entity(w) for w in ('assistant', 'assistant-codex')}
        check('AC2/workers-enrolled', 'each assistant role\'s worker is enrolled, as every default team worker is',
              roles.get('assistant', {}).get('workers') == ['assistant']
              and roles.get('assistant_codex', {}).get('workers') == ['assistant-codex']
              and all(w and w.get('revoked_at') is None for w in workers.values()))

        trees = (root, args[3], units)
        before_head = h['journal'](store)
        before = h['snapshot'](*trees)
        code, again = h['setup'](*args)
        after = h['snapshot'](*trees)
        check('AC2/rerun-saves-nothing', 'a second setup run answers already_set_up [%s %s]'
              % (again.get('outcome'), again.get('reason')), code == 0 and again.get('outcome') == 'already_set_up')
        check('AC2/rerun-saves-nothing', 'and saves nothing again: the journal head is unchanged [%s]'
              % [r['command_id'] for r in h['journal'](store)[len(before_head):]],
              h['journal'](store) == before_head)
        check('AC2/rerun-saves-nothing', 'and changes no file [%s]' % (h['changes'](before, after),),
              h['changes'](before, after) == ([], [], []))

    def teardown(h):
        nonlocal fake_capture
        base, fake = h['base'], h['engines186']['fake']
        L = load('v177_format_launch', h['mods'] / 'control_launch.py')

        def readback_args(engine, base):
            return [READBACK]
        try:
            pass
        finally:
            fake_capture = conform_formats.conform_fake(locals(), '0177_assistant_setup')
            check('format/fake-lines', 'the generated CLI lines conform to the capture %s' % (fake_capture[0][:4],),
                  not fake_capture[0] and bool(fake_capture[1]))

    try:
        helper.run(ROOT, PRODUCTION, exercise, teardown, fake)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in rows:
            check(row, 'ran to its end (raised ' + type(error).__name__ + ': ' + str(error)[:250] + ')', False)
    for line in conform_formats.describe('0177_assistant_setup', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0177_assistant_setup', bool(fake_capture[1]) and not fake_capture[0])
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0177 detail:', row, '; '.join(failed))
        expect('VELDO-0177 ' + row, bool(rows[row]) and not failed)


_v177_setup_suite()
