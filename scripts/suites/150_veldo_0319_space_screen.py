"""VELDO-0319: the console's Space screen, at the API. The reads the screen shows and the owner's commands.

Run: python3 scripts/selftest.py --suite 150_veldo_0319_space_screen

Only shared ROOT and expect are consumed. A real control store, the real space Ledger (control_space.Ledger) on
it, the real API authority (control_api_authority.ApiAuthority) on the same connection and the real API edge
(control_api.ControlApi) over that authority. Every space record the rows read was written by the Ledger's own
commands: pools, holds placed and admitted, items declared, confirmed, measured, signalled, deferred, removed,
kept and gone, a worktree's own decision request and a review group with its one request.

AC1 (rows ac1/*). space.usage's figures per project, ticket and kind equal the sums the suite makes of the
  ledger's item records, the plain repository and no project are rows of their own, a deferred and a due item
  count, a removed and a gone one do not, and the totals row is the sum of all.
  Falsifier (declared): sum only present items; ac1/totals and ac1/deferred-counts turn red.
AC2 (rows ac2/*). space.pending lists every due and every deferred item with its reason in words, the event it
  was refused at, its retry events and its open decision request, a review group's worktrees under their one
  request by index; space.removed lists every removal, newest first, with its event, size and free space before
  and after.
  Falsifier (declared): hide deferred items; ac2/in-use-folder finds nothing and turns red.
AC3 (rows ac3/*), as amended by the lead on 2026-11-16 (the spec's History): space.reconcile and space.abandon
  are signed owner commands, published POST routes with an operation, and the four reads are GET routes that
  need a session. A request with no session is refused each (401), a session without the anti-forgery token is
  refused each write (403), a member who is not the owner is refused each command by the authority
  (unauthorized:not_owner), nothing is written and the service's entries are never called; the owner's
  session reaches them with the item, the version and the signing owner. There is no route for Adopt, Confirm,
  Wrong or the mode switch, and the action contract names none: each comes with its own ticket.
  Falsifier (declared): accept Abandon as a plain read route; ac3/unsigned-refused turns red.
AC4 (rows ac4/*). space.pools gives a waiting hold and, for a report-mode scope, an advised hold with need,
  free, held and floor as the Ledger recorded them, the pool's floor and what is held on it, and names the run
  whose dispatch carries the hold. The reads change with the record: the same read after one Ledger command
  serves the new record at a later watermark, with nothing kept between reads. The screen's side of AC4 (the
  record stream with the page's clock stopped, the runs list) is suite 150_veldo_0319_space_ui.
scope/* A member scoped to one project is served that project's items and holds only, and no plain repository
  or no-project row; a member of no project is refused; an entity whose digest does not verify is a problem and
  is in no figure. redact/* A path is served; a part of a path the secret scanner finds is replaced, and an
  identity is kept. words/* The reason of every deferral the rules and the removers name.

STAND-INS. The membership, the credential records, the api edge's key record and the authority's lock are
fixture records (suite 71 exercises the API's own sign-in). Assertions are signed by a fixture edge key in
place of the protected signer. The service's two entries (control_service.Service.space_reconcile and
.space_abandon, suites 156 and 149) are recording functions: this suite shows who reaches them, not what they
do. The intake is an object that names the domain's projects. Deferrals are written by the Ledger's outcome
command with the facts the rules of control_space_signal give (their shapes are read from that module's
docstrings); no probe runs and nothing is removed from disk.
"""


def _v319_suite():
    import contextlib
    import fcntl
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
    }
    ROWS = ('ac1/per-project-ticket-kind', 'ac1/totals', 'ac1/deferred-counts', 'ac1/plain-and-no-project',
            'ac1/worktrees',
            'cost/removed-index', 'cost/carried-index', 'cost/flat-when-doubled', 'cost/same-answers',
            'ac2/removal-stamp', 'ac2/in-use-folder', 'ac2/every-pending', 'ac2/requests', 'ac2/removed',
            'ac3/routes-signed', 'ac3/unsigned-refused', 'ac3/not-owner-refused', 'ac3/owner-accepted',
            'ac3/no-dead-route',
            'ac5/keep-applied', 'ac5/console-bytes',
            'ac6/edge-alone-refused', 'ac6/other-member-refused', 'ac6/revoked-refused', 'ac6/other-command-refused',
            'ac6/settled-keep-only', 'ac6/ssh-as-before', 'ac6/owner-only',
            'ac7/answered-not-signed', 'ac7/member-own-request',
            'ac4/pools-numbers', 'ac4/record-reaches-read',
            'scope/member', 'scope/digest', 'redact/locator', 'words/deferrals', 'canon/synced')
    rows = {name: [] for name in ROWS}
    KEEP_ROWS = ('ac5/', 'ac6/', 'ac7/')
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def exercise(base, wired):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        API = load('v319_api', mods / 'control_api.py')
        AUTH = load('v319_api_authority', mods / 'control_api_authority.py')
        MO = AUTH.MO
        S = load('v319_store', mods / 'control_store.py')
        CM = load('v319_membership', mods / 'control_membership.py')
        SP = load('v319_space', mods / 'control_space.py')
        CFG = load('v319_space_config', mods / 'control_space_config.py')
        YAML = load('v319_yamlish', mods / 'yamlish.py')
        K = load('v319_space_kinds', mods / 'control_space_kinds.py')
        ST = load('v319_settlement', mods / 'control_request_settlement.py')
        AS, CRD, EN, AC = AUTH.AS, AUTH.CR, AUTH.E, AUTH.AC
        GIB, MIB = 1024 ** 3, 1024 ** 2

        # ---- the installation and its projects, read from disk as the Ledger's callers read them ----------
        folder = base / 'installation'
        folder.mkdir()
        PLAIN = base / 'projects' / 'tools'
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {'enabled': 'true', 'time_zone': 'Europe/Lisbon',
                      'pools': {'host': {'floor': 20 * GIB, 'needs': {'build': 4 * GIB, 'review': 1 * GIB, 'gate': 6 * GIB}},
                                'desktop': {'floor': 8 * GIB, 'needs': {'build': 0, 'review': 0, 'gate': 3 * GIB}}},
                      'engines': ['default', 'desktop-linux'],
                      'scratch_roots': {'roots': [str(base / 'scratch')],
                                        'session_pattern': 'sessions/{working_folder}/{session_id}'},
                      'build_roots': [str(base / 'build')],
                      'plain_repositories': [{'repository': str(PLAIN), 'worktree_root': str(base / 'projects' / 'tools-worktrees')}],
                      'client_accounts': [str(base / 'client-a')],
                      'protect': {'paths': [str(base / 'protected')], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                                  'images': ['store/objects'], 'networks': ['atlas_*'], 'compose_projects': ['ledgerdb']}}}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(base / 'home')}, stream=io.StringIO())
        PROJECTS = []
        for name in ('orchard', 'meadow'):
            repository = base / 'projects' / name
            (repository / '.veldo').mkdir(parents=True)
            PROJECTS.append(dict(CFG.read_project(str(repository), YAML.read, config=CONFIG, stream=io.StringIO()),
                                 repository=str(repository)))
        ORCHARD, MEADOW = (project['project'] for project in PROJECTS)
        for made_folder in (PLAIN, base / 'scratch', base / 'build', base / 'state', base / 'projects' / 'tools-worktrees'):
            made_folder.mkdir(parents=True, exist_ok=True)

        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'edge', '-f', str(private / 'edge')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        edge_public = ' '.join((private / 'edge.pub').read_text().split()[:2])

        def sign_edge(message):
            quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / 'edge'), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        conn = S.open_store(str(db))
        wired.callback(conn.close)
        DOMAIN, REPO = 'domain-319', 'repository-319'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-319')
        serial = [0]

        def row_of(identity):
            found = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'data': json.loads(found[2])} if found else None

        def version(identity):
            return (row_of(identity) or {}).get('version', 0)

        def put(identity, kind, data):
            serial[0] += 1
            return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority',
                                        operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                                        expected_versions={identity: version(identity)},
                                        parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', sign, 1)

        def journal_head():
            return conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        # The members: olga, the owner (project_owner, every scope); pavel, a person with every scope and no
        # role; mira, a project owner scoped to orchard; nobody, a person of a project this domain does not serve.
        MEMBERS = {'olga': (['project_owner'], '*'), 'pavel': ([], '*'), 'mira': (['project_owner'], [ORCHARD]),
                   'nobody': ([], ['elsewhere'])}
        for who, (roles, scope) in MEMBERS.items():
            put(who, 'membership', {'principal_type': 'person', 'roles': roles, 'scope': scope, 'revoked_at': None,
                                    'expires_at': None})
            put(CRD.entity_id('cred-' + who), CRD.KIND, {'credential_id': 'cred-' + who, 'principal': who,
                                                         'effective_at': 0, 'revoked_at': None})
        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO], 'revoked_at': None,
                                        'expires_at': None})
        put('api-edge', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO], 'revoked_at': None,
                                       'expires_at': None})
        put(AC.edge_channel(AS.CHANNEL)['edge_key_id'], 'verification_key', {
            'schema': EN.SCHEMA, 'channel': AS.CHANNEL, 'principal': 'api-edge', 'public_key': edge_public,
            'effective_at': 0, 'retired_at': None, 'revoked_at': None})

        L = SP.Ledger(S, conn, 'authority', sign, config=CONFIG, projects=PROJECTS, state_root=str(base / 'state'),
                      lifecycle=K.LIFECYCLE, host='fixture-host', device=lambda path: 'dev-host')
        for made_pool in (L.set_pool('host', 'filesystem', device='dev-host'),
                          L.set_pool('desktop', 'engine_image', engine='desktop-linux', backing='host')):
            if not made_pool.get('ok'):
                raise RuntimeError('the fixture pool: %s' % made_pool.get('reason'))

        # ---- the items, each brought to its state by the Ledger's own commands ----------------------------
        made = {}

        def declare(name, kind, path, owner, size=None, event='run_finished', **more):
            os.makedirs(path, exist_ok=True)
            result = L.declare(kind, {'path': path}, owner, 'seam', **more)
            if not result.get('ok'):
                raise RuntimeError('the fixture item %s: %s' % (name, result.get('reason')))
            identity = result['item']
            L.confirm(identity)
            if size is not None:
                L.measure(identity, size, event)
            made[name] = identity
            return identity

        def owner(project, ticket, run, station='build'):
            return {'scope': {'type': 'project', 'id': project}, 'ticket': ticket, 'run': {'id': run, 'station': station}}

        def accepted(result):
            if not result.get('ok'):
                raise RuntimeError('a fixture command was refused: %s' % result.get('reason'))
            return result
        roots = {project['project']: project['worktree_root'] for project in PROJECTS}
        build = str(base / 'build')
        T1, T2, T3 = 'VELDO-9601', 'VELDO-9602', 'VELDO-9603'
        declare('tree', 'worktree', roots[ORCHARD] + '/' + T1, owner(ORCHARD, T1, 'run-1'), 3 * GIB, branch='veldo-9601',
                start='a' * 40)
        declare('build', 'build_output', build + '/orchard-9601', owner(ORCHARD, T1, 'run-1'), 5 * GIB)
        declare('build2', 'build_output', build + '/orchard-9601-b', owner(ORCHARD, T1, 'run-1b'), 1 * GIB)
        declare('unmeasured', 'build_output', build + '/orchard-9602-new', owner(ORCHARD, T2, 'run-2'))
        declare('busy', 'build_output', build + '/orchard-9602-in-use', owner(ORCHARD, T2, 'run-2'), 4 * GIB + 100 * MIB)
        declare('due', 'build_output', build + '/orchard-9602-due', owner(ORCHARD, T2, 'run-2b'), 2 * GIB)
        declare('removed', 'build_output', build + '/orchard-9603-old', owner(ORCHARD, T3, 'run-3'), 7 * GIB)
        declare('removed2', 'build_output', build + '/orchard-9603-older', owner(ORCHARD, T3, 'run-3b'), 6 * GIB)
        declare('gone', 'build_output', build + '/orchard-9603-gone', owner(ORCHARD, T3, 'run-3c'), 9 * GIB)
        declare('solo', 'worktree', roots[ORCHARD] + '/' + T2, owner(ORCHARD, T2, 'run-2'), 600 * MIB, event='ticket_ended',
                branch='veldo-9602', start='b' * 40)
        for index in (1, 2, 3):
            declare('review%d' % index, 'worktree', roots[ORCHARD] + '/review-%d' % index,
                    {'scope': {'type': 'project', 'id': ORCHARD}, 'run': {'id': 'review-%d' % index, 'station': 'review'}},
                    100 * MIB * index, event='ticket_ended')
        declare('m-tree', 'worktree', roots[MEADOW] + '/VELDO-9701', owner(MEADOW, 'VELDO-9701', 'run-m'), 1 * GIB,
                branch='veldo-9701', start='c' * 40)
        declare('plain', 'build_output', build + '/tools-experiment',
                {'scope': {'type': 'plain_repository', 'id': str(PLAIN)}}, 350 * MIB, event='reconcile')
        declare('scratch', 'scratch', str(base / 'scratch') + '/session-41',
                {'scope': {'type': 'no_project'}, 'session': 'session-41'}, 64 * MIB, event='session_started')

        def defer(name, event, subject, facts):
            accepted(L.signal(event, subject))
            accepted(L.outcome(made[name], 'deferred', dict({'event': event, 'emitter': {'process': 'fixture'},
                                                             'action': 'remove', 'carrier': None}, **facts)))
        IN_USE = {'rule': 'in_use', 'refused_by': 'process_use', 'order': 4,
                  'retry': list(K.LIFECYCLE['ends_on']['build_output']),
                  'found': {'processes': [{'pid': 4412, 'command': 'vite', 'uses': ['cwd']}], 'containers': [],
                            'git': {'read': True, 'files': [], 'worktree_locked': False},
                            'unread': {'processes': [], 'table': None, 'engines': [], 'git': None, 'folders': None}}}

        def unique(files):
            names = ['notes/file-%d.md' % n for n in range(files)]
            return {'rule': 'unique_work', 'refused_by': 'unique_work', 'order': 5,
                    'retry': list(K.LIFECYCLE['ends_on']['worktree']),
                    'found': {'cases': [1, 3], 'branch': None, 'commit': 'd' * 40, 'modified': names[:1], 'staged': [],
                              'untracked': names[1:], 'operation': None, 'unlanded': None,
                              'more': {'modified': 0, 'staged': 0, 'untracked': 0}}}
        # The in-use folder is deferred twice (two attempts); the due folder stays due.
        defer('busy', 'run_finished', {'items': [{'item': made['busy'], 'version': version(made['busy'])}]}, IN_USE)
        defer('busy', 'ticket_ended', {'items': [{'item': made['busy'], 'version': version(made['busy'])}]}, IN_USE)
        accepted(L.signal('run_finished', {'items': [{'item': made['due'], 'version': version(made['due'])}]}))
        # Two removals, the older first, through removing; one item found missing.
        for name, before, after in (('removed2', 24 * GIB, 30 * GIB), ('removed', 30 * GIB, 37 * GIB)):
            accepted(L.signal('run_finished', {'items': [{'item': made[name], 'version': version(made[name])}]}))
            facts = {'event': 'run_finished', 'emitter': {'process': 'fixture'}, 'action': 'remove', 'carrier': None}
            accepted(L.outcome(made[name], 'removing', dict(facts)))
            accepted(L.outcome(made[name], 'removed', dict(facts, method='rmtree', bytes=after - before,
                                                           bytes_source='measured', pool='host', pool_free_before=before,
                                                           pool_free_after=after, freed=after - before, host=None)))
        accepted(L.gone(made['gone']))

        # A worktree's own decision request, and a review group with its one request.
        def entry(name, files):
            path = L.item(made[name])['locator']['path']
            return {'item': made[name], 'path': path, 'branch': None, 'unheld_commits': False, 'kept_branch': None,
                    'files': ['notes/file-%d.md' % n for n in range(files)], 'commits': [],
                    'restore': 'veldo space restore ' + made[name]}
        named = lambda name: {'items': [{'item': made[name], 'version': version(made[name])}]}  # noqa: E731
        defer('solo', 'ticket_ended', named('solo'), unique(3))
        solo = accepted(L.request_disposition(made['solo'], {'discard': ST.SPACE_DISCARD, 'worktrees': [entry('solo', 3)]},
                                              None))['request']
        group_id = None
        for index in (1, 2, 3):
            name = 'review%d' % index
            defer(name, 'ticket_ended', named(name), unique(index))
            joined = accepted(L.request_group(made[name], entry(name, index), None, at=1794830000.0))
            group_id = joined['group']
        group = L.group(group_id)

        # The holds: one waiting and one advised, judged with numbers; one admitted; one released.
        def hold(name, answer, need, project, reason=None, used=None):
            identity = 'dispatch/' + S.digest_of(name).split(':')[-1]
            accepted(L.place_hold(identity, {'host': need}, {'host': 'declared'}, scope={'type': 'project', 'id': project}))
            if answer != 'placed':
                accepted(L.admit(identity, answer if answer != 'released' else 'admitted', reason=reason, used=used))
            if answer == 'released':
                accepted(L.release(identity))
            made['hold-' + name] = SP.hold_id(identity)
            return identity
        numbers = lambda need, free, held: {'pool': 'host', 'need': need, 'free': free, 'held': held, 'floor': 20 * GIB}  # noqa: E731
        hold('admitted', 'admitted', 10 * GIB, ORCHARD)
        carried = hold('advised', 'advised', 6 * GIB, ORCHARD, numbers(6 * GIB, 38 * GIB, 10 * GIB), used={'host': 2 * GIB})
        hold('waiting', 'waiting', 12 * GIB, MEADOW, numbers(12 * GIB, 41 * GIB, 14 * GIB))
        hold('released', 'released', 30 * GIB, MEADOW)
        # The dispatch that carries the advised hold (control_dispatch: contract.space).
        DISPATCH = 'dispatch/VELDO-9601/' + 'e' * 32
        put('dispatch:' + DISPATCH, 'dispatch', {'schema': 'veldo.dispatch/v1', 'dispatch_id': DISPATCH, 'state': 'running',
                                                 'contract': {'unit': T1, 'station': 'build', 'attempt': 1,
                                                              'reservation': {'project': ORCHARD, 'account': 'a'},
                                                              'space': {'hold': carried, 'needs': {'host': 6 * GIB}}}})

        # ---- the authority and the API edge --------------------------------------------------------------
        lock_held = os.open(str(db.parent / AUTH.LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
        wired.callback(os.close, lock_held)
        fcntl.flock(lock_held, fcntl.LOCK_EX | fcntl.LOCK_NB)

        class Intake:
            projects = [ORCHARD, MEADOW]
        API_DOMAIN = 'orchard-factory'
        authority = AUTH.ApiAuthority(S, CM, conn, ids=ids, domain=API_DOMAIN, edge='api-edge', intake=Intake(),
                                      settlement=None, credentials=None, authority_lock=lock_held)
        asked = {'reconcile': [], 'abandon': []}
        authority.space_reconcile = lambda started_by, project=None: (
            asked['reconcile'].append((started_by, project)) or {'ok': True, 'counts': {'matched': 3}})

        def abandon(item, version=None, by=None, cause=None):
            asked['abandon'].append({'item': item, 'version': version, 'by': by, 'cause': cause})
            return {'sent': True, 'removed': [], 'deferred': [], 'discard_required': [item]}
        authority.space_abandon = abandon
        HOST = 'console.fixture.example'
        api = API.ControlApi({'origin': 'https://' + HOST, 'rp_id': HOST, 'host': HOST, 'domain': API_DOMAIN, 'ids': ids,
                              'edge': 'api-edge', 'state_dir': str(base / 'api-state')}, authority,
                             lambda assertion: (sign_edge(S.canonical_bytes(assertion)), None))
        sessions = {who: api.sessions.create(who, 'cred-' + who) for who in MEMBERS}
        base_path = '/api/v1/domains/%s/space/' % API_DOMAIN

        def get(who, view, cookie=True):
            headers = {'Host': HOST}
            if who and cookie:
                headers['Cookie'] = '%s=%s' % (API.COOKIE, sessions[who][0])
            status, _headers, body = api.handle('GET', base_path + view, headers, b'')
            return status, body

        def post(who, action, body, token=True, method='POST'):
            headers = {'Host': HOST, 'Content-Type': 'application/json', 'Origin': 'https://' + HOST}
            if who:
                headers['Cookie'] = '%s=%s' % (API.COOKIE, sessions[who][0])
                if token:
                    headers[API.TOKEN_HEADER] = sessions[who][1]['token']
            try:
                status, _headers, answer = api.handle(method, base_path + action, headers, json.dumps(body).encode())
            except Exception as error:  # noqa: BLE001 - a request the edge could not judge is named, never a pass
                return 'raised', {'refusal': type(error).__name__}
            return status, answer

        def read(who, view):
            status, body = get(who, view)
            if status != 200:
                raise RuntimeError('the read %s for %s: %s %s' % (view, who, status, body.get('refusal')))
            return body

        # ---- AC1 -----------------------------------------------------------------------------------------
        def sums(visible=lambda record: True):
            """The suite's own sums of the Ledger's item records that are still there, by scope, ticket, kind."""
            out = {}
            for identity, record in L.items().items():
                if record['state'] not in SP.LIVE or not visible(record):
                    continue
                scope = record['owner']['scope']
                size = (record.get('size') or {}).get('bytes')
                keys = [('total',), (scope['type'], scope.get('id')), (scope['type'], scope.get('id'), record['owner'].get('ticket')),
                        (scope['type'], scope.get('id'), record['owner'].get('ticket'), record['kind'])]
                for key in keys:
                    cell = out.setdefault(key, {'bytes': 0, 'items': 0, 'unmeasured': 0})
                    cell['items'] += 1
                    cell['bytes'] += size or 0
                    cell['unmeasured'] += size is None
            return out

        def served(usage):
            out = {('total',): usage['total']}
            for scope in usage['scopes']:
                key = (scope['scope']['type'], scope['scope']['id'])
                out[key] = scope
                for ticket in scope['tickets']:
                    out[key + (ticket['ticket'],)] = ticket
                    for kind in ticket['kinds']:
                        out[key + (ticket['ticket'], kind['kind'])] = kind
            return {key: {field: cell[field] for field in ('bytes', 'items', 'unmeasured')} for key, cell in out.items()}

        usage = read('olga', 'usage')
        want, have = sums(), served(usage)
        R = 'ac1/per-project-ticket-kind'
        check(R, 'every sum the suite makes of the ledger\'s item records by project, ticket and kind is a figure of '
                 'the read, and the read has no other [%d sums, %d figures]' % (len(want), len(have)),
              set(want) == set(have) and len(want) > 12)
        check(R, 'each figure equals its sum: bytes, items and the items never measured [%s]'
                 % sorted(str(key) for key in want if want[key] != have.get(key))[:3],
              all(want[key] == have.get(key) for key in want))
        orchard_build = have.get(('project', ORCHARD, T1, 'build_output'))
        check(R, 'two build folders of one ticket are one figure: 6 GiB in 2 items [%s]' % (orchard_build,),
              orchard_build == {'bytes': 6 * GIB, 'items': 2, 'unmeasured': 0})
        kind_row = next(kind for scope in usage['scopes'] for ticket in scope['tickets'] for kind in ticket['kinds']
                        if ticket['ticket'] == T1 and kind['kind'] == 'worktree')
        check(R, 'each kind names the event its sizes were measured at [%s]' % kind_row.get('measured_at'),
              kind_row.get('measured_at') == ['run_finished'])
        R = 'ac1/totals'
        total = sum((record.get('size') or {}).get('bytes') or 0 for record in L.items().values() if record['state'] in SP.LIVE)
        check(R, 'the totals row is the sum of every item that is still there, the deferred and the due ones '
                 'included, and of none that was removed or is gone [%s of %s]' % (usage['total']['bytes'], total),
              usage['total']['bytes'] == total and usage['total']['items'] == len(
                  [1 for record in L.items().values() if record['state'] in SP.LIVE])
              and usage['total']['unmeasured'] == 1)
        check(R, 'the totals row is the sum of the scope rows, and each scope row of its tickets',
              usage['total']['bytes'] == sum(scope['bytes'] for scope in usage['scopes'])
              and all(scope['bytes'] == sum(ticket['bytes'] for ticket in scope['tickets']) for scope in usage['scopes']))
        R = 'ac1/deferred-counts'
        states = {name: L.item(made[name])['state'] for name in ('busy', 'due', 'solo', 'removed', 'gone')}
        check(R, 'the fixture holds a deferred and a due folder, a deferred worktree, a removed and a gone folder '
                 '[%s]' % states,
              states == {'busy': 'deferred', 'due': 'due', 'solo': 'deferred', 'removed': 'removed', 'gone': 'gone'})
        t2 = have.get(('project', ORCHARD, T2, 'build_output'))
        check(R, 'the deferred in-use folder and the due folder are in their ticket\'s build output figure with the '
                 'folder never measured: 6.1 GiB in 3 items, 1 not measured [%s]' % (t2,),
              t2 == {'bytes': 4 * GIB + 100 * MIB + 2 * GIB, 'items': 3, 'unmeasured': 1})
        check(R, 'the ticket whose every item was removed or is gone has no row',
              not any(key[2:3] == (T3,) for key in have))
        R = 'ac1/plain-and-no-project'
        tops = [(scope['scope']['type'], scope['scope']['id']) for scope in usage['scopes']]
        check(R, 'the projects come first, then each plain repository and then no project, each a row of its own '
                 '[%s]' % [top[0] for top in tops],
              tops == [('project', MEADOW), ('project', ORCHARD), ('plain_repository', str(PLAIN)), ('no_project', None)]
              or tops == [('project', ORCHARD), ('project', MEADOW), ('plain_repository', str(PLAIN)), ('no_project', None)])
        check(R, 'the plain repository holds its 350 MiB and no project the session\'s 64 MiB of scratch',
              have.get(('plain_repository', str(PLAIN))) == {'bytes': 350 * MIB, 'items': 1, 'unmeasured': 0}
              and have.get(('no_project', None)) == {'bytes': 64 * MIB, 'items': 1, 'unmeasured': 0})
        R = 'ac1/worktrees'
        trees = {tree['id']: tree for tree in usage['worktrees']}
        can = sorted(identity for identity, record in L.items().items()
                     if record['kind'] == 'worktree' and record['state'] in ('present', 'kept', 'deferred')
                     and 'worktree_abandoned' in record['ends_on']['events'])
        check(R, 'the worktrees an Abandon can be sent for are listed, each at the version its record is at [%d]'
                 % len(trees),
              sorted(trees) == can and len(can) == 6
              and all(tree['version'] == version(identity) for identity, tree in trees.items()))

        # ---- AC2 -----------------------------------------------------------------------------------------
        pending = read('olga', 'pending')
        by_id = {item['id']: item for item in pending['items']}
        R = 'ac2/in-use-folder'
        busy = by_id.get(made['busy']) or {}
        check(R, 'the deferred in-use folder is listed, with its path, its owner and its size [%s]' % busy.get('state'),
              busy.get('state') == 'deferred' and busy.get('locator') == build + '/orchard-9602-in-use'
              and busy.get('bytes') == 4 * GIB + 100 * MIB and busy.get('owner', {}).get('ticket') == T2)
        check(R, 'its reason is in words, with the rule that refused, the event it was refused at and the number of '
                 'attempts [%s | %s %s %s]' % (busy.get('reason'), busy.get('rule'), busy.get('refused_at'), busy.get('attempts')),
              busy.get('reason') == 'in use by process 4412' and busy.get('rule') == 'in_use'
              and busy.get('refused_at') == 'ticket_ended' and busy.get('attempts') == 2)
        check(R, 'its retry events are its own ending events, and it has no decision request [%s]' % busy.get('retry'),
              busy.get('retry') == list(K.LIFECYCLE['ends_on']['build_output']) and busy.get('request') is None)
        R = 'ac2/every-pending'
        waiting = sorted(identity for identity, record in L.items().items() if record['state'] in ('due', 'deferred'))
        check(R, 'every due and every deferred item of the ledger is listed and nothing else [%d of %d]'
                 % (len(by_id), len(waiting)),
              sorted(by_id) == waiting and len(waiting) == 6)
        due = by_id.get(made['due']) or {}
        check(R, 'the due item says the event that made it due and has no reason yet [%s %s]'
                 % (due.get('due_event'), due.get('reason')),
              due.get('state') == 'due' and due.get('due_event') == 'run_finished' and due.get('reason') is None)
        check(R, 'a worktree with work in no commit says so with the number of files [%s]'
                 % (by_id.get(made['solo']) or {}).get('reason'),
              (by_id.get(made['solo']) or {}).get('reason') == 'uncommitted changes in 3 files'
              and (by_id.get(made['review1']) or {}).get('reason') == 'uncommitted changes in 1 file')
        R = 'ac2/requests'
        requests = {request['alias']: request for request in pending['requests']}
        check(R, 'the worktree\'s own request is listed by the alias its record holds, with that one worktree '
                 '[%s]' % sorted(requests)[:2],
              (by_id.get(made['solo']) or {}).get('request') == solo['alias'] and solo['alias'] in requests
              and requests[solo['alias']]['members'] == [{'item': made['solo'], 'index': None}]
              and requests[solo['alias']]['group'] is None)
        ours = requests.get(group['request']['alias']) or {}
        check(R, 'the three review worktrees share the group\'s one request, each with the index the record gave it '
                 '[%s]' % ours.get('members'),
              ours.get('group') == group_id and ours.get('members') == [
                  {'item': made['review%d' % index], 'index': index} for index in (1, 2, 3)]
              and all((by_id.get(made['review%d' % index]) or {}).get('request') == group['request']['alias']
                      and (by_id.get(made['review%d' % index]) or {}).get('index') == index for index in (1, 2, 3)))
        check(R, 'the request names the indexes it offers an answer of their own for, the group\'s day and its '
                 'sequence [%s %s %s]' % (ours.get('picks'), ours.get('day'), ours.get('sequence')),
              ours.get('picks') == group['request']['proposal']['picks'] and ours.get('picks')
              and ours.get('day') == group['day'] and ours.get('sequence') == 1)
        R = 'ac2/removed'
        removed = read('olga', 'removed')['items']
        gone_ids = [identity for identity, record in L.items().items() if record['state'] == 'removed']
        check(R, 'every removal of the ledger is listed and nothing else, the newest first [%s]'
                 % [item['locator'].rsplit('/', 1)[-1] for item in removed],
              [item['id'] for item in removed] == [made['removed'], made['removed2']] and sorted(gone_ids) == sorted(
                  item['id'] for item in removed) and removed[0]['seq'] > removed[1]['seq'])
        first = removed[0] if removed else {}
        check(R, 'each has its event, its size and the pool\'s free space before and after '
                 '[%s %s %s %s]' % (first.get('event'), first.get('bytes'), first.get('free_before'), first.get('free_after')),
              first.get('event') == 'run_finished' and first.get('bytes') == 7 * GIB and first.get('pool') == 'host'
              and first.get('free_before') == 30 * GIB and first.get('free_after') == 37 * GIB
              and removed[1].get('free_before') == 24 * GIB and removed[1].get('free_after') == 30 * GIB)
        check(R, 'a removed item is in no pending row and in no usage figure',
              not set(gone_ids) & set(by_id) and usage['total']['bytes'] == total)

        # ---- AC3 -----------------------------------------------------------------------------------------
        R = 'ac3/routes-signed'
        routes = {route.name: route for route in API.ROUTES}
        check(R, 'Reconcile and Abandon are POST routes that need a session and carry an operation the assertion '
                 'knows [%s %s]' % (routes['space.reconcile'].operation, routes['space.abandon'].operation),
              all(routes[name].method == 'POST' and routes[name].session is True
                  and routes[name].operation in AS.OPERATIONS for name in ('space.reconcile', 'space.abandon'))
              and routes['space.abandon'].required == ('item', 'version')
              and routes['space.reconcile'].required == ('project',))
        # Restated as the property it guards (the amendment of 2026-11-16): every space read, whichever
        # ticket adds it, is a GET route that needs a session and takes no field. No list of names is pinned.
        check(R, 'every space read (each entry of SPACE_VIEWS) is a GET route that needs a session and takes no '
                 'field, and every GET route named space.* is one of them [%s]' % list(MO.SPACE_VIEWS),
              len(MO.SPACE_VIEWS) >= 4 and all(
                  name in routes and routes[name].method == 'GET' and routes[name].session is True
                  and routes[name].operation is None and routes[name].required == ()
                  and routes[name].optional == () for name in MO.SPACE_VIEWS)
              and sorted(name for name in routes if name.startswith('space.') and routes[name].method == 'GET')
              == sorted(MO.SPACE_VIEWS))
        check(R, 'every route has its handler and every handler its route [%s]' % api.route_problems()[:2],
              api.route_problems() == [])
        actions = {action.name: action for action in MO.ACTIONS}
        check(R, 'the action contract names both with their routes and the command each executes',
              actions['space_reconcile'].route == 'space.reconcile' and actions['worktree_abandon'].route == 'space.abandon'
              and authority.commands().get('abandon_worktree') == SP.SIGNAL
              and authority.commands().get('reconcile_space') == SP.RECONCILE)
        mirror = json.loads((ROOT / 'engine' / 'ui' / 'src' / 'api' / 'routes.json').read_text())['routes']
        check(R, 'the UI\'s route table holds each space route as the API publishes it',
              all(mirror.get(name) == {'method': routes[name].method, 'path': routes[name].path,
                                       'required': list(routes[name].required), 'optional': list(routes[name].optional)}
                  for name in routes if name.startswith('space.')))

        R = 'ac3/unsigned-refused'
        tree_id, shown = made['tree'], version(made['tree'])
        head, before = journal_head(), {key: len(value) for key, value in asked.items()}
        applied = authority.counts['accepted'] + authority.counts['refused']
        nobody_post = [post(None, 'reconcile', {'project': None}), post(None, 'abandon', {'item': tree_id, 'version': shown})]
        check(R, 'with no session, Reconcile and Abandon are each refused as unauthenticated [%s]'
                 % [(status, answer.get('refusal')) for status, answer in nobody_post],
              all(status == 401 and answer.get('refusal') == 'unauthenticated:no_session' for status, answer in nobody_post))
        as_read = [post(None, 'abandon', {}, method='GET'),
                   get(None, 'abandon?item=%s&version=%d' % (tree_id, shown)),
                   get('olga', 'abandon?item=%s&version=%d' % (tree_id, shown)), get('olga', 'reconcile')]
        check(R, 'Abandon and Reconcile are no read: a GET of either, with no session and with the owner\'s, finds no '
                 'route [%s]' % [(status, answer.get('refusal')) for status, answer in as_read],
              all(status == 404 and answer.get('refusal') == 'missing_evidence:route' for status, answer in as_read))
        no_token = [post('olga', 'reconcile', {'project': None}, token=False),
                    post('olga', 'abandon', {'item': tree_id, 'version': shown}, token=False)]
        check(R, 'the owner\'s session without its anti-forgery token is refused each write [%s]'
                 % [(status, answer.get('refusal')) for status, answer in no_token],
              all(status == 403 and answer.get('refusal') == 'unauthorized:token' for status, answer in no_token))
        unread = [get(None, view) for view in ('pools', 'usage', 'pending', 'removed')]
        check(R, 'with no session each of the four reads is refused as unauthenticated',
              all(status == 401 and body.get('refusal') == 'unauthenticated:no_session' for status, body in unread))
        check(R, 'none of them reached the authority\'s judgment or the service: nothing was applied, nothing was '
                 'written and no entry was called',
              authority.counts['accepted'] + authority.counts['refused'] == applied and journal_head() == head
              and {key: len(value) for key, value in asked.items()} == before
              and L.item(tree_id)['state'] == 'present' and version(tree_id) == shown)

        R = 'ac3/not-owner-refused'
        for who, why in (('pavel', 'a person who holds no project_owner role'),
                         ('mira', 'a project owner whose scope is one project and not the space scope')):
            answers = [post(who, 'reconcile', {'project': None}), post(who, 'abandon', {'item': tree_id, 'version': shown})]
            check(R, '%s is refused Reconcile and Abandon by the authority, by name [%s]'
                     % (why, [(status, answer.get('refusal')) for status, answer in answers]),
                  all(status == 403 and answer.get('refusal') == 'unauthorized:not_owner' for status, answer in answers))
        check(R, 'the service\'s entries were never called and nothing was written',
              {key: len(value) for key, value in asked.items()} == before and journal_head() == head
              and version(tree_id) == shown)

        R = 'ac3/owner-accepted'
        status, answer = post('olga', 'reconcile', {'project': ORCHARD})
        check(R, 'the owner\'s Reconcile is accepted and reaches the service\'s entry as the console\'s, for the '
                 'project named [%s %s %s]' % (status, answer.get('outcome'), asked['reconcile'][-1:]),
              status == 200 and answer.get('outcome') == 'reconciled' and asked['reconcile'] == [('console', ORCHARD)])
        status, answer = post('olga', 'reconcile', {'project': None})
        check(R, 'with no project it is a reconcile of all [%s]' % asked['reconcile'][-1:],
              status == 200 and asked['reconcile'][-1] == ('console', None))
        status, answer = post('olga', 'abandon', {'item': tree_id, 'version': shown})
        last = (asked['abandon'] or [{}])[-1]
        check(R, 'the owner\'s Abandon is accepted and reaches the service\'s entry with the item, the version shown, '
                 'the signing owner and its cause [%s %s]' % (status, last),
              status == 200 and answer.get('outcome') == 'abandoned' and len(asked['abandon']) == 1
              and last == {'item': tree_id, 'version': shown, 'by': 'olga', 'cause': 'owner_abandon'}
              and answer.get('discard_required') == [tree_id])
        status, answer = post('olga', 'abandon', {'item': tree_id})
        check(R, 'an Abandon without its version is refused as invalid input and reaches no entry [%s %s]'
                 % (status, answer.get('refusal')),
              status == 400 and len(asked['abandon']) == 1)
        observed = [event for event in authority.observations if event.get('operation') in ('reconcile_space', 'abandon_worktree')]
        check(R, 'each command the authority judged is observed with its principal and its outcome [%d]' % len(observed),
              len(observed) == 7 and [event['outcome'] for event in observed].count('accepted') == 3
              and all(event.get('principal') in MEMBERS for event in observed))

        R = 'ac3/no-dead-route'
        # Restated as the property it guards (the amendment of 2026-11-16), so a later ticket adds its route
        # without editing this row: every POST route named space.* reaches a Ledger command that has a
        # transition, through an operation, an authority branch and an action; and no owner action the Ledger
        # names without a transition has a route.
        def dead(table, actions_now, commands, transitions, operations=AS.OPERATIONS):
            found = []
            for route in table:
                if not route.name.startswith('space.') or route.method != 'POST':
                    continue
                command = commands.get(route.operation)
                if route.operation not in operations:
                    found.append(route.name + ': no operation')
                elif command is None:
                    found.append(route.name + ': no authority branch')
                elif not any(action.route == route.name and action.operation == route.operation
                             and action.module == 'control_space' for action in actions_now):
                    found.append(route.name + ': no action')
                elif command not in transitions:
                    found.append(route.name + ': its command %s has no transition' % command)
            return found
        transitions = set(conn.command_registry) & set(SP.OWNER_ACTIONS + SP.OPERATIONS + (SP.MODE,))
        posts = sorted(route.name for route in API.ROUTES if route.name.startswith('space.') and route.method == 'POST')
        check(R, 'every POST route named space.* carries an operation, has an authority branch and an action, and its '
                 'command is a Ledger operation that has a transition %s [%s]' % (posts, dead(
                     API.ROUTES, MO.ACTIONS, authority.commands(), transitions)[:2]),
              len(posts) >= 3 and 'space.keep' in posts
              and dead(API.ROUTES, MO.ACTIONS, authority.commands(), transitions) == [])
        handled = []
        for route in API.ROUTES:
            if route.name.startswith('space.') and route.method == 'POST':
                # The authority has a branch when the owner's call is judged there, not answered as unknown.
                status, answer = post('pavel', route.name.split('.', 1)[1], {field: None for field in route.required})
                handled.append((route.name, status, answer.get('refusal')))
        check(R, 'and the authority judges each: a person who is not the owner is refused by name, never served and '
                 'never unknown [%s]' % handled,
              all(status == 403 and refusal == 'unauthorized:not_owner' for _name, status, refusal in handled))
        # An owner action the Ledger names and has no transition for (a later ticket's command, or one that is
        # carried by another command, as the owner's Abandon is carried by the signal): no route's command is
        # it, and its name answers 404 unless a published route of that name passed the check above.
        unbuilt = [name for name in SP.OWNER_ACTIONS if name not in conn.command_registry]
        words = {name: name[len('space_'):].replace('_group', '') for name in unbuilt}
        absent = sorted(word for word in words.values() if 'space.' + word not in routes)
        check(R, 'no owner action the Ledger names without a transition is the command of a route or of an action, and '
                 'a POST to the name of each that has no route answers 404 %s' % absent,
              bool(unbuilt) and all(command not in authority.commands().values() for command in unbuilt)
              and not any(getattr(SP, str(action.command), None) in unbuilt for action in MO.ACTIONS
                          if action.module == 'control_space')
              and bool(absent) and all(post('olga', word, {})[0] == 404 for word in absent))
        check(R, 'the action contract offers no space action without a route',
              all(action.route in routes for action in MO.ACTIONS if action.module == 'control_space'))
        # The row has teeth: a published route whose command has no transition turns it red.
        ghost = API.Route('space.ghost', 'POST', '/api/v1/domains/{domain}/space/ghost', 'work', True, ('item',), (),
                          'ghost_space')
        acted = MO.ACTIONS + (type(MO.ACTIONS[0])('ghost', 'space.ghost', 'ghost_space', 'control_space', 'REJECT',
                                                  'VELDO-0319'),)
        known = tuple(AS.OPERATIONS) + ('ghost_space',)
        check(R, 'a route whose command has no transition is found, and so is one with no operation, no branch or '
                 'no action',
              dead(API.ROUTES + (ghost,), acted, dict(authority.commands(), ghost_space=unbuilt[0]), transitions, known)
              == ['space.ghost: its command %s has no transition' % unbuilt[0]]
              and dead(API.ROUTES + (ghost,), acted, authority.commands(), transitions, known) == ['space.ghost: no authority branch']
              and dead(API.ROUTES + (ghost,), MO.ACTIONS, dict(authority.commands(), ghost_space=SP.SIGNAL), transitions,
                       known) == ['space.ghost: no action']
              and dead(API.ROUTES + (ghost,), acted, authority.commands(), transitions) == ['space.ghost: no operation'])

        # ---- AC4 -----------------------------------------------------------------------------------------
        R = 'ac4/pools-numbers'
        pools = read('olga', 'pools')
        host = next(pool for pool in pools['pools'] if pool['name'] == 'host')
        desktop = next(pool for pool in pools['pools'] if pool['name'] == 'desktop')
        check(R, 'each pool has its floor, and what is held on it is what the admitted and the advised holds still '
                 'hold: 10 GiB and 6 GiB less the 2 GiB the run\'s own items use [%s]' % host.get('held'),
              host.get('floor') == 20 * GIB and host.get('held') == 14 * GIB and desktop.get('floor') == 8 * GIB
              and desktop.get('held') == 0 and desktop.get('returns_space') is False and desktop.get('backing') == 'host')
        wait = (host.get('waiting') or [{}])[0]
        check(R, 'the waiting run is listed with need, free, held and floor as the Ledger recorded them, and its '
                 'project [%s]' % {field: wait.get(field) for field in ('need', 'free', 'held', 'floor')},
              len(host['waiting']) == 1 and wait.get('id') == made['hold-waiting'] and wait.get('state') == 'waiting'
              and (wait.get('need'), wait.get('free'), wait.get('held'), wait.get('floor')) == (12 * GIB, 41 * GIB, 14 * GIB, 20 * GIB)
              and wait.get('scope') == {'type': 'project', 'id': MEADOW} and wait.get('run') is None)
        advised = (host.get('advised') or [{}])[0]
        check(R, 'in report mode the run that would have waited is listed as advised with the same four numbers, and '
                 'the run whose dispatch carries the hold is named [%s]' % (advised.get('run'),),
              len(host['advised']) == 1 and advised.get('id') == made['hold-advised'] and advised.get('state') == 'advised'
              and (advised.get('need'), advised.get('free'), advised.get('held'), advised.get('floor')) == (6 * GIB, 38 * GIB, 10 * GIB, 20 * GIB)
              and advised.get('run') == {'dispatch': DISPATCH, 'unit': T1, 'station': 'build'})
        check(R, 'an admitted and a released hold are in neither list',
              not {made['hold-admitted'], made['hold-released']} & {entry_['id'] for entry_ in host['waiting'] + host['advised']})

        R = 'ac4/record-reaches-read'
        mark = pools['watermark']['seq']
        fresh = hold('late', 'waiting', 9 * GIB, ORCHARD, numbers(9 * GIB, 33 * GIB, 14 * GIB))
        again = read('olga', 'pools')
        host2 = next(pool for pool in again['pools'] if pool['name'] == 'host')
        check(R, 'a hold the Ledger records after a read is in the next read, at a later watermark, with its '
                 'numbers [%s to %s]' % (mark, again['watermark']['seq']),
              again['watermark']['seq'] > mark and again['freshness'] == 'live'
              and sorted(entry_['id'] for entry_ in host2['waiting']) == sorted([made['hold-waiting'], SP.hold_id(fresh)]))
        accepted(L.release(fresh))
        accepted(L.release(hold('gone', 'waiting', 1 * GIB, ORCHARD, numbers(1 * GIB, 1 * GIB, 0))))
        third = read('olga', 'pools')
        check(R, 'and when the Ledger releases it, it leaves the next read: nothing is kept between reads',
              [entry_['id'] for entry_ in next(pool for pool in third['pools'] if pool['name'] == 'host')['waiting']]
              == [made['hold-waiting']] and third['watermark']['seq'] > again['watermark']['seq'])
        reads_before = journal_head()
        for view in ('pools', 'usage', 'pending', 'removed'):
            read('olga', view)
        check(R, 'a read writes nothing: the journal is where it was after all four',
              journal_head() == reads_before)

        # ---- scope, digest, redaction, words ---------------------------------------------------------------
        R = 'scope/member'
        own = read('mira', 'usage')
        mine = sums(lambda record: record['owner']['scope'] == {'type': 'project', 'id': ORCHARD})
        check(R, 'a member scoped to one project is served that project\'s figures only: no other project, no plain '
                 'repository and no "no project" row [%s]' % [scope['scope'] for scope in own['scopes']],
              [(scope['scope']['type'], scope['scope']['id']) for scope in own['scopes']] == [('project', ORCHARD)]
              and served(own) == mine)
        own_pools = read('mira', 'pools')
        own_host = next(pool for pool in own_pools['pools'] if pool['name'] == 'host')
        check(R, 'the pools are the installation\'s and are served, with the holds of that project only',
              len(own_pools['pools']) == 2 and own_host['waiting'] == []
              and [entry_['id'] for entry_ in own_host['advised']] == [made['hold-advised']])
        check(R, 'that member\'s pending rows and worktrees are that project\'s',
              all(item['owner']['scope']['id'] == ORCHARD for item in read('mira', 'pending')['items'])
              and made['m-tree'] not in {tree['id'] for tree in own['worktrees']})
        refused = [get('nobody', view) for view in ('pools', 'usage', 'pending', 'removed')]
        check(R, 'a member of no project this domain serves is refused each read by name [%s]'
                 % sorted({body.get('refusal') for _status, body in refused}),
              all(status == 403 and body.get('refusal') == 'unauthorized:no_project' for status, body in refused))
        check(R, 'a read model that is not a space view is still refused by name, and the space model itself is not '
                 'a read [%s]' % authority.read('space', 'olga').get('reason'),
              authority.read('space', 'olga').get('reason') == 'missing_evidence:read_model'
              and authority.read('space.kept', 'olga').get('reason') == 'missing_evidence:read_model')

        R = 'scope/digest'
        victim = made['build2']
        conn.execute('UPDATE entities SET data=replace(data, ?, ?) WHERE id=?',
                     (str(1 * GIB), str(900 * GIB), victim))
        conn.commit()
        tampered = read('olga', 'usage')
        check(R, 'an item whose bytes do not match its digest is reported as a problem and is in no figure '
                 '[%s]' % tampered['problems'][:1],
              tampered['problems'] == [{'id': victim, 'kind': 'space_item', 'refusal': 'missing_evidence:entity_digest'}]
              and tampered['total']['bytes'] == total - 1 * GIB and tampered['total']['items'] == usage['total']['items'] - 1)
        conn.execute('UPDATE entities SET data=replace(data, ?, ?) WHERE id=?', (str(900 * GIB), str(1 * GIB), victim))
        conn.commit()
        check(R, 'and with its bytes back it is counted again', read('olga', 'usage')['total'] == usage['total'])

        R = 'redact/locator'
        long_path = roots[ORCHARD] + '/' + T1
        check(R, 'a worktree\'s path, which the secret scanner reads as one long token, is served whole '
                 '[%s]' % bool(MO.SCAN.scan_text(long_path)),
              bool(MO.SCAN.scan_text(long_path)) and trees[made['tree']]['locator'] == long_path
              and not any('locator' in path for path in usage['redacted']))
        secret = 'ghp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8'
        view = MO.space_view(conn, 'pending', {'items': {'space_item': [
            {'id': 'space:item:' + secret, 'version': 1, 'data': {
                'kind': 'build_output', 'state': 'deferred', 'owner': {'scope': {'type': 'project', 'id': ORCHARD}},
                'locator': {'path': '/srv/build/' + secret + '/out'},
                'deferral': {'rule': 'protected', 'found': {'entry': secret}}}}],
            'space_hold': [], 'space_review_group': [], 'space_pool': []},
            'problems': [], 'redacted': [], 'watermark': {'seq': 1}, 'freshness': 'live'}, True)
        shown_item = view['items'][0]
        check(R, 'a part of a path the scanner finds is replaced and the rest is served; a credential in any other '
                 'text is replaced whole; the item\'s identity is kept [%s | %s]' % (shown_item['locator'], shown_item['reason']),
              shown_item['locator'] == '/srv/build/' + MO.MARKER + '/out' and shown_item['reason'] == MO.MARKER
              and shown_item['id'] == 'space:item:' + secret and secret not in json.dumps(
                  dict(shown_item, id='')) and '$.pending.items[0].reason' in view['redacted'])

        R = 'words/deferrals'
        W = MO.deferral_words
        cases = (
            ({'rule': 'in_use', 'refused_by': 'process_use', 'found': {'processes': [{'pid': 7}, {'pid': 8}]}},
             'in use by 2 processes (7, 8)'),
            ({'rule': 'in_use', 'refused_by': 'owner_live', 'found': {'process': {'pid': 4412, 'live': True}}},
             'in use by process 4412'),
            ({'rule': 'in_use', 'refused_by': 'owner_live', 'found': {'run': {'id': 'run-9', 'station': 'build'}, 'gate': None, 'read': None}},
             'its run run-9 is not known to have ended'),
            ({'rule': 'in_use', 'refused_by': 'children', 'found': {'items': ['a', 'b'], 'states': {}}},
             'holds 2 items that are still there'),
            ({'rule': 'in_use', 'refused_by': 'process_use', 'found': {'processes': [], 'containers': [{'id': 'c'}], 'git': {}}},
             'mounted by 1 container'),
            ({'rule': 'in_use', 'refused_by': 'process_use', 'found': {'processes': [], 'containers': [], 'git': {'read': False}}},
             'whether it is in use could not be read'),
            ({'rule': 'in_use', 'refused_by': 'registry', 'reason': 'held', 'held_by': ['x']}, 'waits for 1 item inside it'),
            ({'rule': 'unique_work', 'found': {'cases': [1], 'modified': ['a'], 'staged': ['b'], 'untracked': [],
                                               'more': {'modified': 0, 'staged': 0, 'untracked': 40}}},
             'uncommitted changes in 42 files'),
            ({'rule': 'unique_work', 'found': {'cases': [5], 'modified': [], 'staged': [], 'untracked': [], 'unlanded': 'f' * 40,
                                               'more': {}}}, 'commits that are not landed'),
            ({'rule': 'unique_work', 'found': {'unread': 'not the top of a git worktree'}}, 'its work could not be read'),
            ({'rule': 'unique_work', 'found': {'no_space_worktree': '/x', 'classification': 'no_space'}},
             'kept after a run that ended with no space left'),
            ({'rule': 'protected', 'found': {'entry': 'atlas-*', 'how': 'name'}}, 'on the protect list (atlas-*)'),
            ({'rule': 'not_in_ledger', 'found': {}}, 'what is at its place is not what the ledger recorded'),
            ({'rule': 'keep_failed', 'found': {}}, 'its work could not be saved first, so it was not removed'),
            ({'rule': 'remove_refused', 'found': {'said': {'ok': False}}}, 'the remover refused it'),
            ({'rule': 'a_later_rule'}, 'deferred by the rule a_later_rule'), ({}, 'no reason is recorded'), (None, 'no reason is recorded'))
        wrong = [(deferral, W(deferral)) for deferral, words in cases if W(deferral) != words]
        check(R, 'every deferral the rules and the removers name has its sentence, and an unknown one names its '
                 'rule [%s]' % wrong[:1], not wrong)
        named = {words for _deferral, words in cases}
        signal_text = (mods / 'control_space_signal.py').read_text()
        check(R, 'the deferral names are the ones control_space_signal and the removers write',
              all(("'%s'" % name) in signal_text for name in ('in_use', 'unique_work', 'protected', 'not_in_ledger',
                                                               'remove_refused', 'keep_failed')) and len(named) == 17)

        R = 'ac2/removal-stamp'
        for identity in gone_ids:
            stamp = L.item(identity)['removal'].get('seq')
            check(R, 'the Ledger stamps the removal with its actual journal order',
                  type(stamp) is int and stamp > 0)
            if type(stamp) is int:
                committed = conn.execute('SELECT after_versions FROM journal WHERE seq=?', (stamp,)).fetchone()
                check(R, 'the stamped record wrote this item',
                      committed is not None and identity in json.loads(committed[0]))
        # Count SQLite virtual-machine steps, not wall time: the rendered result stays fixed
        # while both the journal and unrelated dispatch population grow by 4096 records.
        def cost(view):
            steps = [0]
            def step():
                steps[0] += 1
                return 0
            conn.set_progress_handler(step, 1)
            try:
                answer = read('olga', view)
            finally:
                conn.set_progress_handler(None, 0)
            return steps[0], answer
        # One dispatch with a later hold stands before the first count. A lookup by a hold's exact name
        # ends on the first later name in the index, one step, however many follow: with none at all
        # the first count would be that one step short and the row would compare an edge, not growth.
        put('dispatch:cost-edge', 'dispatch', {'contract': {'space': {'hold': 'unrelated-edge'},
                                                            'reservation': {'project': ORCHARD}}})

        def whole_store_state():
            """authority_state as it was before this fix: every entity of the store read and parsed."""
            st = S.materialized_state(conn)['entities']
            membership, delegations, keyring = [], [], []
            for eid, e in st.items():
                if e['kind'] == 'membership':
                    membership.append(dict(e['data'], principal=eid, entity_version=e['version']))
                elif e['kind'] == 'delegation':
                    delegations.append(dict(e['data'], id=eid, entity_version=e['version']))
                elif e['kind'] == 'verification_key':
                    keyring.append(dict(e['data'], key_id=eid))
            versions = st.get(CM.VERSIONS_ENTITY, {}).get('data', {})
            return {'membership': membership, 'delegations': delegations, 'keyring': keyring, 'entities': st,
                    'membership_version': int(versions.get('membership_version', 0)),
                    'delegation_version': int(versions.get('delegation_version', 0)),
                    'versions_entity_version': st.get(CM.VERSIONS_ENTITY, {}).get('version', 0)}

        R = 'cost/same-answers'
        PARTS = ('membership', 'delegations', 'keyring', 'membership_version', 'delegation_version',
                 'versions_entity_version')
        old, new = whole_store_state(), CM.authority_state(S, conn)
        check(R, 'the keys and the authority\'s own records are the ones a read of the whole store gave, in '
                 'the same order [%d members, %d keys]' % (len(new['membership']), len(new['keyring'])),
              list(old) == list(new) and all(old[part] == new[part] for part in PARTS)
              and len(new['membership']) >= len(MEMBERS))
        others = [eid for eid, e in old['entities'].items() if e['kind'] not in CM.AUTHORITY_KINDS]
        steps = [0]
        def count():
            steps[0] += 1
            return 0
        conn.set_progress_handler(count, 1)
        try:
            one = [(eid in new['entities'], new['entities'].get(eid), new['entities'][eid]) for eid in others[:3]]
        finally:
            conn.set_progress_handler(None, 0)
        check(R, 'a record that is not the authority\'s is read by its id when asked for, the same record '
                 '[3 of %d in %d steps]' % (len(others), steps[0]),
              len(others) >= 3 and 0 < steps[0] < 200
              and one == [(True, old['entities'][eid], old['entities'][eid]) for eid in others[:3]])
        check(R, 'a record the store never held is absent, by every way of asking',
              'no-such-record' not in new['entities'] and new['entities'].get('no-such-record', 7) == 7
              and new['entities'].get('no-such-record') is None)
        fresh = CM.authority_state(S, conn)
        check(R, 'every record by its id is the whole read\'s record [%d]' % len(old['entities']),
              all(fresh['entities'].get(eid) == e for eid, e in old['entities'].items()))
        check(R, 'asked whole, the map is the whole read\'s: equal, in the same order, the same length, the '
                 'same canonical bytes, and a plain copy of it too',
              new['entities'] == old['entities'] and list(new['entities']) == list(old['entities'])
              and len(new['entities']) == len(old['entities'])
              and list(new['entities'].items()) == list(old['entities'].items())
              and S.canonical_bytes(new['entities']) == S.canonical_bytes(old['entities'])
              and dict(CM.authority_state(S, conn)['entities']) == old['entities']
              and json.dumps(CM.authority_state(S, conn)['entities'], sort_keys=True)
              == json.dumps(old['entities'], sort_keys=True))
        # The snapshot holds across a later commit: a record rewritten, and one created, after the read.
        moved, born = others[0], 'dispatch:cost-born-later'
        by_id, by_whole = CM.authority_state(S, conn), CM.authority_state(S, conn)
        put(moved, old['entities'][moved]['kind'], dict(old['entities'][moved]['data'], rewritten_after_the_read=True))
        put(born, 'dispatch', {'contract': {'space': {'hold': 'unrelated-born'}, 'reservation': {'project': ORCHARD}}})
        check(R, 'a record rewritten after the read is still the record the read saw, and one created after '
                 'it is absent: by its id',
              by_id['entities'].get(moved) == old['entities'][moved] and born not in by_id['entities']
              and by_id['entities'].get(born) is None)
        check(R, 'and asked whole: the map is still the one the read saw',
              by_whole['entities'] == old['entities'] and list(by_whole['entities']) == list(old['entities']))
        after = whole_store_state()
        check(R, 'a read made after the commit sees the commit',
              CM.authority_state(S, conn)['entities'].get(moved) == after['entities'][moved]
              and after['entities'][moved] != old['entities'][moved] and born in CM.authority_state(S, conn)['entities'])
        put(moved, old['entities'][moved]['kind'], old['entities'][moved]['data'])
        # Every space read, for every member, answered through the whole-store read and through this one.
        def answers():
            return {(who, view): get(who, view[len('space.'):]) for who in MEMBERS for view in MO.SPACE_VIEWS}
        indexed, kept = answers(), CM.authority_state
        CM.authority_state = lambda _store, _conn: whole_store_state()
        try:
            whole = answers()
        finally:
            CM.authority_state = kept
        differing = sorted(key for key in whole if S.canonical_bytes(whole[key]) != S.canonical_bytes(indexed[key]))
        check(R, 'every space read answers every member the same bytes through the whole-store read and through '
                 'the indexed one [%d reads, %d served, differing %s]'
                 % (len(whole), sum(1 for status, _body in whole.values() if status == 200), differing[:2]),
              not differing and len(whole) == len(MEMBERS) * len(MO.SPACE_VIEWS)
              and any(status == 200 for status, _body in whole.values())
              and any(status != 200 for status, _body in whole.values()))

        small = {view: cost(view) for view in ('removed', 'pools')}
        for n in range(4096):
            put('dispatch:cost-%d' % n, 'dispatch',
                {'contract': {'space': {'hold': 'unrelated-%d' % n},
                              'reservation': {'project': ORCHARD}}})
        large = {view: cost(view) for view in ('removed', 'pools')}
        for view, row, field in (('removed', 'cost/removed-index', 'items'),
                                 ('pools', 'cost/carried-index', 'pools')):
            before_steps, before_answer = small[view]
            after_steps, after_answer = large[view]
            check(row, 'same SQL steps with 4096 more journal entries and dispatches: %d -> %d'
                  % (before_steps, after_steps), before_steps == after_steps)
            check(row, 'the full authority read still serves the same records',
                  before_answer[field] == after_answer[field])

        R = 'cost/flat-when-doubled'
        held = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
        for n in range(held):
            put('dispatch:cost-double-%d' % n, 'dispatch',
                {'contract': {'space': {'hold': 'unrelated-double-%d' % n},
                              'reservation': {'project': ORCHARD}}})
        doubled = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
        twice = {view: cost(view) for view in ('removed', 'pools')}
        for view, field in (('removed', 'items'), ('pools', 'pools')):
            check(R, 'space.%s costs the same SQL steps with the store doubled (%d to %d records): %d -> %d -> %d'
                  % (view, held, doubled, small[view][0], large[view][0], twice[view][0]),
                  doubled >= 2 * held > 8192 and small[view][0] == large[view][0] == twice[view][0])
            check(R, 'and space.%s serves the same records' % view, twice[view][1][field] == large[view][1][field])

        R = 'canon/synced'
        check(R, 'the engine canon of the API and Ledger modules equals the repository\'s copy',
              all((ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                  for name in PRODUCTION))
        text = PRODUCTION['control_api_models.py'].read_text() + PRODUCTION['control_api_authority.py'].read_text()
        check(R, 'the space reads open no file and no filesystem figure: no open, statvfs or disk_usage in the two '
                 'modules that make them',
              not any(word in text for word in ('statvfs', 'disk_usage', 'os.walk', 'os.scandir', 'subprocess')))

    def keep_world(base, wired):
        """AC5 to AC7 (the amendment of 2026-11-16): the owner's Keep, signed by the owner's passkey and sent
        on space.keep. A second store with members enrolled by the membership's own command, the real
        settlement (inbox, presenter, Settlement), the real Ledger, authority and API edge. The passkey is a
        local stand-in: an openssl P-256 key, with clientDataJSON and authenticatorData assembled as WebAuthn
        lays them out (suite 71 exercises the browser's own ceremony). The service's entry is the one line
        control_service.Service.space_keep is: the Ledger's disposition with only='keep'."""
        import base64
        import hashlib
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        API = load('v319k_api', mods / 'control_api.py')
        AUTH = load('v319k_api_authority', mods / 'control_api_authority.py')
        claims = load('v319k_claim', mods / 'control_claim.py')
        S, CM, AC = claims.S, claims.CM, claims.AC
        I, V, P, ST, contract, SP, CFG, K = (load('v319k_' + name, mods / (name + '.py')) for name in (
            'control_assignment', 'control_channel_presentation', 'control_channel_projection',
            'control_request_settlement', 'entity_contract', 'control_space', 'control_space_config',
            'control_space_kinds'))
        AS, CRD, EN = AUTH.AS, AUTH.CR, AUTH.E
        b64 = lambda data: base64.urlsafe_b64encode(data).rstrip(b'=').decode()  # noqa: E731
        quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
        keys, public = {}, {}
        for who in ('steward', 'owner', 'second', 'plain', 'requester', 'api-edge'):
            keys[who] = base / ('key-' + who)
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys[who])], check=True,
                           capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = ' '.join(keys[who].with_suffix('.pub').read_text().split()[:2])

        def sign(who, message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[who]), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def journal_sign(message):
            return sign('steward', message, 'veldo-journal')
        serial = [0]

        def next_id():
            serial[0] += 1
            return 'keep-fixture-%d' % serial[0]
        ids = dict(domain_uuid='domain-319k', repository_uuid='repository-319k', store_uuid='store-319k')
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        conn = S.open_store(str(db))
        wired.callback(conn.close)
        CM.attach(S)

        def member(who, principal_type, roles):
            state = CM.authority_state(S, conn)
            command = dict(command_id=next_id(), operation='enroll_principal', target='authority',
                           parameters=dict(principal=who, principal_type=principal_type, roles=roles,
                                           public_key=public[who], independence_group=who, scope='*'),
                           artifact_digests=[], expected_versions={})
            envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='steward',
                            request_revision=1, nonce=next_id(), expires_at=time.time() + 600,
                            membership_version=state['membership_version'], delegation_version=state['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            done = CM.admit(S, conn, envelope, command, sign('steward', AC.canonical_envelope_bytes(envelope)), ids,
                            time.time(), enrollee_signature=None if who == 'steward' else
                            sign(who, AC.canonical_envelope_bytes(dict(envelope, principal=who))),
                            journal_signer=('steward', journal_sign))
            if not done.get('ok', done.get('outcome') in ('accepted', 'admitted', None)) and done.get('reason'):
                raise RuntimeError('the fixture member %s: %s' % (who, done))
        member('steward', 'person', ['membership_steward', 'project_owner'])
        owner_roles = ['project_owner', 'admission_authority', 'priority_authority', 'technical_authority']
        member('owner', 'person', owner_roles)
        member('second', 'person', owner_roles)
        member('plain', 'person', [])
        member('requester', 'service', [])
        member('api-edge', 'service', [])

        def put(identity, kind, data):
            row = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            return S.execute(conn, dict(command_id=next_id(), nonce=next_id(), principal='steward',
                                        operation='upsert_entity', artifact_digests=[],
                                        expected_versions={identity: row[0] if row else 0},
                                        parameters=dict(entity_id=identity, kind=kind, data=data)),
                             'steward', journal_sign, 1)
        for who, chat in (('owner', 31901), ('second', 31902)):
            put('channel-enrollment:telegram_chat:' + who, 'channel_enrollment', dict(
                schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                revoked_at=None))
        put(AC.edge_channel(AS.CHANNEL)['edge_key_id'], 'verification_key', {
            'schema': EN.SCHEMA, 'channel': AS.CHANNEL, 'principal': 'api-edge', 'public_key': public['api-edge'],
            'effective_at': 0, 'retired_at': None, 'revoked_at': None})

        class Transport:
            sent = []

            def send(self, chat, text, reply_to):
                self.sent.append(text)
                return dict(chat_id=chat, message_id=len(self.sent), date=int(time.time()), text=text,
                            reply_to_message_id=reply_to)
        inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'steward', journal_sign)
        presenter = V.Presenter(S, CM, P, inbox, Transport(), conn, 'steward', journal_sign, assignment=I)
        settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'steward', journal_sign, assignment=I,
                                   presentation=V, api_edge='api-edge')

        # ---- the passkeys: one of the owner, a second of the owner that is then revoked, one of `second` ----
        HOST = 'console.fixture.example'
        ORIGIN = 'https://' + HOST

        class Passkey:
            def __init__(self, name, principal, revoked=False):
                self.key = base / ('passkey-' + name + '.pem')
                subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256',
                                '-out', str(self.key)], check=True, capture_output=True, timeout=20)
                der = subprocess.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'],
                                     check=True, capture_output=True, timeout=20).stdout
                self.credential_id, self.user_handle = b64(os.urandom(32)), b64(os.urandom(16))
                put(CRD.entity_id(self.credential_id), CRD.KIND, {
                    'schema': CRD.SCHEMA, 'principal': principal, 'credential_id': self.credential_id,
                    'public_key': b64(der), 'algorithm': -7, 'user_handle': self.user_handle, 'rp_id': HOST,
                    'origin': ORIGIN, 'label': name, 'effective_at': 0, 'revoked_at': 1 if revoked else None,
                    'revoked_by': 'steward' if revoked else None, 'enrolled_by': 'steward', 'proof': None,
                    'envelope': None, 'command_id': 'fixture'})

            def assertion(self, command, origin=ORIGIN, rp_id=HOST):
                """The ceremony the console runs: the challenge is SHA-256 of the command's canonical bytes."""
                challenge = b64(hashlib.sha256(S.canonical_bytes(command)).digest())
                client = json.dumps({'type': 'webauthn.get', 'challenge': challenge, 'origin': origin,
                                     'crossOrigin': False}, separators=(',', ':')).encode()
                data = hashlib.sha256(rp_id.encode()).digest() + bytes([0x05]) + b'\x00\x00\x00\x00'
                signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)],
                                           input=data + hashlib.sha256(client).digest(), check=True,
                                           capture_output=True, timeout=20).stdout
                return {'credential_id': self.credential_id, 'client_data_json': b64(client),
                        'authenticator_data': b64(data), 'signature': b64(signature), 'user_handle': self.user_handle}
        PASS = {'owner': Passkey('owner', 'owner'), 'owner-revoked': Passkey('owner-old', 'owner', revoked=True),
                'second': Passkey('second', 'second'), 'plain': Passkey('plain', 'plain')}

        # ---- the Ledger and its worktrees, each deferred with unique work by the Ledger's own commands --------
        repo, trees, state = base / 'repo', base / 'trees', base / 'state'
        for folder in (repo, trees, state):
            folder.mkdir()
        config = CFG.check({'enabled': True, 'time_zone': 'UTC',
                            'pools': {'host': {'floor': 0, 'needs': {'build': 1, 'review': 1, 'gate': 1}}},
                            'engines': ['fixture'],
                            'scratch_roots': {'roots': [], 'session_pattern': 'sessions/{working_folder}/{session_id}'},
                            'build_roots': [], 'plain_repositories': [{'repository': str(repo), 'worktree_root': str(trees)}],
                            'client_accounts': [], 'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [],
                                                               'networks': [], 'compose_projects': []}})
        L = SP.Ledger(S, conn, 'steward', journal_sign, config=config, state_root=str(state), host='fixture',
                      lifecycle=K.LIFECYCLE, device=lambda path: 'dev-host')
        L.passkeys = {'origin': ORIGIN, 'rp_id': HOST, 'state_dir': str(base / 'passkey-state')}
        if not L.set_pool('host', 'filesystem', device='dev-host').get('ok'):
            raise RuntimeError('the fixture pool')
        scope = {'type': 'plain_repository', 'id': str(repo)}
        requester = ('requester', lambda data: sign('requester', data))

        def accepted(result):
            if not result.get('ok'):
                raise RuntimeError('a fixture command was refused: %s %s' % (result.get('reason'), result.get('detail')))
            return result

        def version(identity):
            return conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]

        def deferred(label, review=False):
            path = str(trees / label)
            os.makedirs(path)
            owner = ({'scope': scope, 'run': {'id': label, 'station': 'review'}} if review
                     else {'scope': scope, 'ticket': 'VELDO-97' + label[-2:], 'run': {'id': 'run-' + label, 'station': 'build'}})
            more = {} if review else {'branch': label, 'start': 'a' * 40}
            item = accepted(L.declare('worktree', {'path': path}, owner, 'seam', **more))['item']
            accepted(L.confirm(item))
            accepted(L.measure(item, 1024, 'ticket_ended'))
            accepted(L.signal('ticket_ended', {'items': [{'item': item, 'version': version(item)}]}))
            accepted(L.outcome(item, 'deferred', {
                'event': 'ticket_ended', 'emitter': {'process': 'fixture'}, 'action': 'remove', 'carrier': None,
                'rule': 'unique_work', 'refused_by': 'unique_work', 'order': 5,
                'retry': list(K.LIFECYCLE['ends_on']['worktree']),
                'found': {'cases': [1, 3], 'branch': None, 'commit': 'd' * 40, 'modified': ['notes/a.md'], 'staged': [],
                          'untracked': [], 'operation': None, 'unlanded': None,
                          'more': {'modified': 0, 'staged': 0, 'untracked': 0}}}))
            return item

        def entry(item):
            return {'item': item, 'path': L.item(item)['locator']['path'], 'branch': None, 'unheld_commits': False,
                    'kept_branch': None, 'files': ['notes/a.md'], 'commits': [], 'restore': 'veldo space restore ' + item}

        def asked(label):
            item = deferred(label)
            accepted(L.request_disposition(item, {'discard': ST.SPACE_DISCARD, 'worktrees': [entry(item)]}, None))
            published = L.publish_disposition(item, settlement, inbox, presenter, requester, 'owner')
            if not published.get('ok'):
                raise RuntimeError('the fixture request: %s' % (published,))
            return item, published['request']

        def request_of(item):
            return I.assignment_id(ids['repository_uuid'], L.item(item)['disposition']['alias'])

        def settle(rid, choice, who='owner'):
            presenter.present(rid)
            receipt = presenter.current(rid)
            body = dict(ids, schema=ST.API_SCHEMA, edge='api-edge', answer_id=next_id(), principal=who,
                        request_id=rid, request_version=receipt['request_version'],
                        presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                        presentation_version=receipt['presentation_version'], choice='accept ' + choice,
                        rationale='Owner answer')
            result = settlement.api_answer(dict(answer=body, signature=sign('api-edge', S.canonical_bytes(body))))
            if result.get('outcome') != 'settled':
                raise RuntimeError('the fixture answer: %s' % (result,))

        # ---- the authority and the API edge, with the service's entry for the Keep packet ---------------------
        lock_held = os.open(str(db.parent / AUTH.LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
        wired.callback(os.close, lock_held)
        fcntl.flock(lock_held, fcntl.LOCK_EX | fcntl.LOCK_NB)

        class Intake:
            projects = ['orchard']
        authority = AUTH.ApiAuthority(S, CM, conn, ids=ids, domain='orchard-factory', edge='api-edge', intake=Intake(),
                                      settlement=settlement, credentials=None, authority_lock=lock_held)
        reached = []

        def space_keep(packet):
            reached.append(packet)
            return L.disposition(packet, CM, time.time(), only='keep')
        authority.space_keep, authority.space_signing = space_keep, HOST
        api = API.ControlApi({'origin': ORIGIN, 'rp_id': HOST, 'host': HOST, 'domain': 'orchard-factory', 'ids': ids,
                              'edge': 'api-edge', 'state_dir': str(base / 'api-state')}, authority,
                             lambda assertion: (sign('api-edge', S.canonical_bytes(assertion), AC.SIGNATURE_NAMESPACE), None))
        sessions = {who: api.sessions.create(who, PASS[who].credential_id) for who in ('owner', 'second', 'plain')}
        space = '/api/v1/domains/orchard-factory/space/'

        def post(who, body, token=True):
            headers = {'Host': HOST, 'Content-Type': 'application/json', 'Origin': ORIGIN}
            if who:
                headers['Cookie'] = '%s=%s' % (API.COOKIE, sessions[who][0])
                if token:
                    headers[API.TOKEN_HEADER] = sessions[who][1]['token']
            try:
                status, _headers, answer = api.handle('POST', space + 'keep', headers, json.dumps(body).encode())
            except Exception as error:  # noqa: BLE001 - a request the edge could not judge is named, never a pass
                return 'raised', {'refusal': '%s: %s' % (type(error).__name__, error)}
            return status, answer

        def pending():
            headers = {'Host': HOST, 'Cookie': '%s=%s' % (API.COOKIE, sessions['owner'][0])}
            status, _headers, body = api.handle('GET', space + 'pending', headers, b'')
            if status != 200:
                raise RuntimeError('the pending read: %s %s' % (status, body.get('refusal')))
            return body

        def command(item, rid, who='owner', at=None):
            """The Keep command as the console builds it: the item at the version the pending read shows."""
            return {'principal': who, 'operation': 'space_disposition', 'command_id': next_id(), 'nonce': next_id(),
                    'parameters': {'item': item, 'version': version(item) if at is None else at, 'request': rid}}

        def body_of(made, signature):
            return dict(made['parameters'], packet={'command': made, 'signature': signature})

        def keep(item, rid, who='owner', passkey=None, session=None, at=None):
            made = command(item, rid, who, at)
            return post(session or who, body_of(made, PASS[passkey or who].assertion(made)))

        def untouched(item, was):
            record = L.item(item)
            return record['state'] == 'deferred' and not record.get('owner_keep') and version(item) == was

        def said(answer):
            return '%s %s' % (answer[0], answer[1].get('refusal') or answer[1].get('outcome'))

        # ---- AC5: an answered Keep is applied by the one signed packet ------------------------------------
        R = 'ac5/keep-applied'
        a, rid_a = asked('tree-01')
        settle(rid_a, 'keep')
        row = next(one for one in pending()['items'] if one['id'] == a)
        check(R, 'once the Keep answer has settled, the item is still deferred: the settlement applies no Keep, and '
                 'the read names the request and says it is answered and not signed [%s %s]'
                 % (row.get('answered'), row.get('request_id')),
              L.item(a)['state'] == 'deferred' and row.get('answered') == 'keep' and row.get('request_id') == rid_a
              and row.get('version') == version(a))
        head = conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        answer = keep(a, rid_a)
        record = L.item(a)
        written = [(seq, sorted(json.loads(transition)), principal) for seq, transition, principal in
                   conn.execute('SELECT seq, transition, principal FROM journal WHERE seq>? ORDER BY seq', (head,))]
        check(R, 'the owner\'s passkey-signed packet on space.keep is accepted and the Ledger writes owner_keep by that '
                 'owner and moves the item from deferred to kept in one command, the owner\'s own on the journal [%s %s]'
                 % (said(answer), [(seq, principal) for seq, _wrote, principal in written]),
              answer[0] == 200 and answer[1].get('outcome') == 'kept' and answer[1].get('state') == 'kept'
              and record['state'] == 'kept' and record.get('owner_keep') == {'by': 'owner'}
              and [(wrote, principal) for _seq, wrote, principal in written] == [([a], 'owner')])
        check(R, 'and it is no longer pending', not any(one['id'] == a for one in pending()['items']))
        again = keep(a, rid_a)
        check(R, 'a second packet for the kept item is refused by name and writes nothing [%s]' % said(again),
              again[0] == 409 and L.item(a) == record)

        R = 'ac5/console-bytes'
        fixed = {'principal': 'owner', 'operation': 'space_disposition', 'command_id': 'keep-0001', 'nonce': 'nonce-0001',
                 'parameters': {'item': 'space:item:\u00e9t\u00e9/"quoted"', 'version': 7, 'request': 'assignment:r:alias-1'}}
        digest = b64(hashlib.sha256(S.canonical_bytes(fixed)).digest())
        spec = (ROOT / 'engine' / 'ui' / 'src' / 'features' / 'space' / 'keep.spec.ts').read_text()
        check(R, 'the console\'s unit row pins the store\'s canonical bytes and their digest for the same command '
                 '[%s]' % digest,
              json.dumps(S.canonical_bytes(fixed).decode()) in spec and "'%s'" % digest in spec)
        check(R, 'the Ledger\'s challenge for a command is SHA-256 of those bytes, unpadded base64url',
              json.loads(base64.urlsafe_b64decode(PASS['owner'].assertion(fixed)['client_data_json'] + '=='))['challenge']
              == digest)

        # ---- AC6: the Ledger verifies the passkey itself ---------------------------------------------------
        R = 'ac6/edge-alone-refused'
        b, rid_b = asked('tree-02')
        settle(rid_b, 'keep')
        was = version(b)
        made = command(b, rid_b)
        calls = len(reached)
        bare = [post('owner', body_of(made, {'credential_id': PASS['owner'].credential_id})),
                post('owner', body_of(made, {}))]
        check(R, 'the owner\'s session and the edge\'s signature alone keep nothing: a packet with no assertion '
                 'reaches the Ledger and is refused not_authorized [%s]' % [said(one) for one in bare],
              all(one[0] == 403 and one[1].get('refusal') == 'unauthorized:not_authorized' for one in bare)
              and len(reached) == calls + 2 and untouched(b, was))
        shapes = [post('owner', body_of(made, None)), post('owner', body_of(made, 'edge')),
                  post('owner', dict(made['parameters'], packet=None))]
        check(R, 'a packet with no signature mapping is refused as invalid input before any entry is called [%s]'
                 % [said(one) for one in shapes],
              all(one[0] == 400 for one in shapes) and len(reached) == calls + 2 and untouched(b, was))
        elsewhere = [post('owner', body_of(made, PASS['owner'].assertion(made, origin='https://evil.example'))),
                     post('owner', body_of(made, PASS['owner'].assertion(made, rp_id='evil.example')))]
        check(R, 'an assertion made for another origin or relying party is refused [%s]' % [said(one) for one in elsewhere],
              all(one[0] == 403 and one[1].get('refusal') == 'unauthorized:not_authorized' for one in elsewhere)
              and untouched(b, was))
        held, L.passkeys = L.passkeys, None
        none = post('owner', body_of(made, PASS['owner'].assertion(made)))
        L.passkeys = held
        check(R, 'a Ledger that was given no relying party takes no passkey [%s]' % said(none),
              none[0] == 403 and untouched(b, was))

        R = 'ac6/other-member-refused'
        others = [keep(b, rid_b, passkey='second'),               # the owner's command under another member's passkey
                  keep(b, rid_b, who='second', session='second')]  # another owner's own command: not the one who answered
        check(R, 'a credential of another member signs no Keep for the owner, and another owner who did not answer '
                 'signs none either [%s]' % [said(one) for one in others],
              all(one[0] == 403 and one[1].get('refusal') == 'unauthorized:not_authorized' for one in others)
              and untouched(b, was))
        forged = command(b, rid_b)
        swapped = post('second', body_of(forged, PASS['owner'].assertion(forged)))
        check(R, 'a packet whose command names another principal than the session\'s is refused as invalid input '
                 '[%s]' % said(swapped), swapped[0] == 400 and untouched(b, was))

        R = 'ac6/revoked-refused'
        revoked = keep(b, rid_b, passkey='owner-revoked')
        check(R, 'a revoked credential of the owner signs no Keep [%s]' % said(revoked),
              revoked[0] == 403 and revoked[1].get('refusal') == 'unauthorized:not_authorized' and untouched(b, was))

        R = 'ac6/other-command-refused'
        c, rid_c = asked('tree-03')
        settle(rid_c, 'keep')
        was_c = version(c)
        signed = command(b, rid_b)
        proof = PASS['owner'].assertion(signed)
        moved = [('another item', dict(signed, parameters={'item': c, 'version': was_c, 'request': rid_c})),
                 ('another request', dict(signed, parameters=dict(signed['parameters'], request=rid_c))),
                 ('another version', dict(signed, parameters=dict(signed['parameters'], version=was + 1))),
                 ('another command id', dict(signed, command_id=next_id()))]
        answers = [(what, post('owner', body_of(other, proof))) for what, other in moved]
        check(R, 'an assertion made over the Keep of one item keeps no other: sent naming another item, request, '
                 'version or command it is refused [%s]' % [(what, said(one)) for what, one in answers],
              all(one[0] == 403 and one[1].get('refusal') == 'unauthorized:not_authorized' for _what, one in answers)
              and untouched(b, was) and untouched(c, was_c))
        true = post('owner', body_of(signed, proof))
        check(R, 'and the same assertion with its own command is accepted [%s]' % said(true),
              true[0] == 200 and L.item(b)['state'] == 'kept' and untouched(c, was_c))

        R = 'ac6/settled-keep-only'
        d, rid_d = asked('tree-04')
        settle(rid_d, 'discard')
        e, rid_e = asked('tree-05')
        was_d, was_e = version(d), version(e)
        wrong, open_ = keep(d, rid_d), keep(e, rid_e)
        check(R, 'space.keep applies only a request settled as Keep: a signed packet for a request settled as '
                 'Discard is refused by name and the item is not made due [%s]' % said(wrong),
              wrong[0] == 400 and wrong[1].get('refusal') == 'invalid_input:space_disposition_choice'
              and untouched(d, was_d))
        check(R, 'a signed packet for a request with no settled answer is refused by name [%s]' % said(open_),
              open_[0] == 404 and open_[1].get('refusal') == 'missing_evidence:space_disposition_unsettled'
              and untouched(e, was_e))
        rows_now = {one['id']: one for one in pending()['items']}
        check(R, 'the read says neither is an answered Keep',
              rows_now[d].get('answered') is None and rows_now[e].get('answered') is None
              and rows_now[e].get('request_id') == rid_e)

        R = 'ac6/ssh-as-before'
        made = command(c, rid_c)
        taken = L.disposition({'command': made, 'signature': sign('owner', S.canonical_bytes(made))}, CM, time.time())
        check(R, 'a Keep signed with the owner\'s SSH key is taken as before [%s]' % taken.get('reason'),
              taken.get('ok') and L.item(c)['state'] == 'kept' and L.item(c).get('owner_keep') == {'by': 'owner'})
        made = command(d, rid_d)
        other = L.disposition({'command': made, 'signature': sign('second', S.canonical_bytes(made))}, CM, time.time())
        check(R, 'and one signed with another member\'s key is refused as before [%s]' % other.get('reason'),
              not other.get('ok') and other.get('reason') == 'not_authorized' and untouched(d, was_d))

        R = 'ac6/owner-only'
        made = command(e, rid_e)
        full = body_of(made, PASS['owner'].assertion(made))
        calls = len(reached)
        refused = [post(None, full), post('owner', full, token=False),
                   post('plain', body_of(dict(made, principal='plain'), PASS['plain'].assertion(dict(made, principal='plain'))))]
        check(R, 'with no session space.keep is unauthenticated, without the anti-forgery token it is refused, and a '
                 'person who is not the owner is refused by the authority; no entry is called [%s]'
                 % [said(one) for one in refused],
              [one[0] for one in refused] == [401, 403, 403] and refused[2][1].get('refusal') == 'unauthorized:not_owner'
              and len(reached) == calls and untouched(e, was_e))

        # ---- AC7: a Keep that settled and was not applied ---------------------------------------------------
        R = 'ac7/answered-not-signed'
        settle(rid_e, 'keep')
        shown = next(one for one in pending()['items'] if one['id'] == e)
        check(R, 'a settled Keep with no packet is listed under Pending removal as answered and not signed, with the '
                 'request its packet names and the relying party it is signed for [%s]' % shown.get('answered'),
              shown.get('answered') == 'keep' and shown.get('request_id') == rid_e and shown.get('state') == 'deferred'
              and pending().get('signing') == HOST)
        old = command(e, rid_e)
        old_proof = PASS['owner'].assertion(old)
        accepted(L.measure(e, 2048, 'reconcile'))
        stale = post('owner', body_of(old, old_proof))
        check(R, 'the packet signed before the item\'s version moved is refused as stale and keeps nothing [%s]'
                 % said(stale),
              stale[0] == 409 and stale[1].get('refusal') == 'stale_version:space_item' and L.item(e)['state'] == 'deferred')
        fresh = next(one for one in pending()['items'] if one['id'] == e)
        signed_now = keep(e, rid_e, at=fresh['version'])
        check(R, 'Sign Keep signs a new packet at the version the read shows now, and it is applied [%s]'
                 % said(signed_now),
              fresh['version'] == shown['version'] + 1 and fresh.get('answered') == 'keep' and signed_now[0] == 200
              and L.item(e)['state'] == 'kept' and L.item(e).get('owner_keep') == {'by': 'owner'})

        R = 'ac7/member-own-request'
        members = [deferred('review-%d' % n, review=True) for n in (1, 2, 3)]
        gid = None
        for item in members:
            gid = accepted(L.request_group(item, entry(item), None, at=1794830000.0))['group']
        published = L.publish_disposition(members[0], settlement, inbox, presenter, requester, 'owner')
        first = request_of(members[0])
        settle(first, 'keep w2')
        raised = L.publish_disposition(members[0], settlement, inbox, presenter, requester, 'owner')
        current = request_of(members[0])
        listed = {one['id']: one for one in pending()['items']}
        check(R, 'after the group moved on, the member answered Keep is listed under its own request, the alias it '
                 'kept, as answered and not signed; the others are under the group\'s new request and are not [%s %s]'
                 % (published.get('ok'), raised.get('ok')),
              current != first and request_of(members[1]) == first and request_of(members[2]) == current
              and L.group(gid)['request']['number'] == 2
              and listed[members[1]].get('request_id') == first and listed[members[1]].get('answered') == 'keep'
              and all(listed[item].get('request_id') == current and listed[item].get('answered') is None
                      for item in (members[0], members[2])))
        was_m = version(members[1])
        wrong = keep(members[1], current)
        check(R, 'a packet that names the group\'s current request for that member is refused and the member stays '
                 'deferred [%s]' % said(wrong),
              wrong[0] in (404, 409) and untouched(members[1], was_m))
        other = keep(members[0], first)
        check(R, 'a packet for a member the Keep did not name keeps nothing [%s]' % said(other),
              other[0] in (404, 409) and L.item(members[0])['state'] == 'deferred')
        own = keep(members[1], first)
        check(R, 'the packet naming the member\'s own request keeps that member alone [%s]' % said(own),
              own[0] == 200 and L.item(members[1])['state'] == 'kept'
              and L.item(members[1]).get('owner_keep') == {'by': 'owner'}
              and all(L.item(item)['state'] == 'deferred' and not L.item(item).get('owner_keep')
                      for item in (members[0], members[2])))

    try:
        with contextlib.ExitStack() as wired:
            exercise(Path(wired.enter_context(tempfile.TemporaryDirectory(prefix='v319-'))).resolve(), wired)
    except Exception as error:  # noqa: BLE001
        for name in ROWS:
            if not rows[name] and not name.startswith(KEEP_ROWS):
                check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    try:
        with contextlib.ExitStack() as wired:
            keep_world(Path(wired.enter_context(tempfile.TemporaryDirectory(prefix='v319k-'))).resolve(), wired)
    except Exception as error:  # noqa: BLE001
        import traceback
        where = traceback.extract_tb(error.__traceback__)[-1]
        for name in ROWS:
            if not rows[name] and name.startswith(KEEP_ROWS):
                check(name, 'ran to its end (raised %s: %s at line %s)' % (type(error).__name__, str(error)[:300],
                                                                          where.lineno), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0319_DETAILS'):
                print('  VELDO-0319 space319/%s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0319 space319/%s detail: no check ran' % name)
        expect('VELDO-0319 space319/' + name, ok)
    print('VELDO-0319 suite seconds: %.3f' % (time.monotonic() - started))


_v319_suite()
