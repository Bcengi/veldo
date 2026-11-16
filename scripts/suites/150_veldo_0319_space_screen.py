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
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
    }
    ROWS = ('ac1/per-project-ticket-kind', 'ac1/totals', 'ac1/deferred-counts', 'ac1/plain-and-no-project',
            'ac1/worktrees',
            'ac2/in-use-folder', 'ac2/every-pending', 'ac2/requests', 'ac2/removed',
            'ac3/routes-signed', 'ac3/unsigned-refused', 'ac3/not-owner-refused', 'ac3/owner-accepted',
            'ac3/no-dead-route',
            'ac4/pools-numbers', 'ac4/record-reaches-read',
            'scope/member', 'scope/digest', 'redact/locator', 'words/deferrals', 'canon/synced')
    rows = {name: [] for name in ROWS}
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
        check(R, 'the four reads are GET routes that need a session and take no field',
              all(routes[name].method == 'GET' and routes[name].session is True and routes[name].operation is None
                  and routes[name].required == () and routes[name].optional == () for name in MO.SPACE_VIEWS)
              and list(MO.SPACE_VIEWS) == ['space.pools', 'space.usage', 'space.pending', 'space.removed'])
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
        later = ('adopt', 'confirm', 'reject', 'mode', 'restore', 'kept')
        check(R, 'no route is published for Adopt, Confirm, Wrong, the mode switch, restore or kept: each comes with '
                 'its own ticket [%s]' % sorted(name for name in routes if name.startswith('space.')),
              sorted(name for name in routes if name.startswith('space.')) == sorted(
                  ['space.reconcile', 'space.abandon'] + list(MO.SPACE_VIEWS))
              and all(post('olga', name, {})[0] == 404 for name in later))
        check(R, 'the action contract offers no space action without a route',
              sorted(action.name for action in MO.ACTIONS if action.module == 'control_space') == [
                  'space_reconcile', 'worktree_abandon'] and all(
                  action.route for action in MO.ACTIONS if action.module == 'control_space'))

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

        R = 'canon/synced'
        check(R, 'the engine canon of the three API modules equals the repository\'s copy',
              all((ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                  for name in PRODUCTION))
        text = PRODUCTION['control_api_models.py'].read_text() + PRODUCTION['control_api_authority.py'].read_text()
        check(R, 'the space reads open no file and no filesystem figure: no open, statvfs or disk_usage in the two '
                 'modules that make them',
              not any(word in text for word in ('statvfs', 'disk_usage', 'os.walk', 'os.scandir', 'subprocess')))

    try:
        with contextlib.ExitStack() as wired:
            exercise(Path(wired.enter_context(tempfile.TemporaryDirectory(prefix='v319-'))).resolve(), wired)
    except Exception as error:  # noqa: BLE001
        for name in ROWS:
            if not rows[name]:
                check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
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
