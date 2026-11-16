"""VELDO-0315: explicit discovery, crash recovery, startup and durable ending-event retries.

Real temporary Git repositories, worktrees, SQLite ledger and owner signatures. The
process table and Docker client are fixture readers. The two unfinished act checks
are supplied only by the fixture. No host engine, protected data or live capture.
"""


def _v315_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import traceback
    import select
    import time
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_space_reconcile.py': ROOT / ".veldo" / "control_space_reconcile.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_consumer.py': ROOT / ".veldo" / "control_space_consumer.py",
        'veldo': ROOT / "bin" / "veldo",
    }
    rows = {}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v315_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0315-') as temporary:
        base = Path(temporary).resolve()
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        R = load('reconcile', mods / 'control_space_reconcile.py')
        SV = load('service', mods / 'control_service.py')
        SP, P, RM, KP, SIG, K = R.organs()
        CFG, YAML, GP = [load(name, mods / (name + '.py'))
                         for name in ('control_space_config', 'yamlish', 'git_process')]
        S, CM, AC = SV.S, SV.CM, SV.CM.AC
        key = base / 'owner'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        public = key.with_suffix('.pub').read_text()

        def sign(message):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True).stdout.decode()

        def git(where, *args):
            result = GP.run(['git', '-C', str(where), *args], identity=('Fixture', 'fixture@example.invalid'),
                            capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(result.stderr)
            return result.stdout.strip()

        class Fixture:
            def __init__(self, name):
                self.root = base / name
                self.root.mkdir()
                self.repo, self.state, self.scratch, self.build, self.proc = [self.root / part for part in
                    ('orchard', 'state', 'scratch', 'build', 'proc')]
                self.plain = self.root / 'plain'
                for directory in (self.repo, self.state, self.scratch, self.build, self.proc, self.plain):
                    directory.mkdir()
                for repo in (self.repo, self.plain):
                    git(repo, 'init', '-q', '-b', 'main')
                    (repo / 'tracked').write_text('base\n')
                    git(repo, 'add', 'tracked')
                    git(repo, 'commit', '-q', '-m', 'base')
                self.installation = self.root / 'installation'
                self.installation.mkdir()
                self.protected = self.state / 'protected'
                section = {'enabled': 'true', 'time_zone': 'UTC',
                    'pools': {'host': {'floor': 0, 'needs': {'build': 0, 'review': 0, 'gate': 0}}},
                    'engines': ['fixture'], 'scratch_roots': {'roots': [str(self.scratch)],
                        'session_pattern': 'sessions/{working_folder}/{session_id}'},
                    'build_roots': [str(self.build)], 'plain_repositories': [
                        {'repository': str(self.plain), 'worktree_root': str(self.root / 'plain-trees')}],
                    'client_accounts': [], 'protect': {'paths': [str(self.protected)], 'volumes': ['real-data'],
                        'containers': ['places'], 'images': ['minio/minio'], 'networks': [], 'compose_projects': ['places']}}
                (self.installation / 'installation.yaml').write_text(YAML.dump({
                    'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture', 'role_id': 'owner'},
                    'space': section}))
                self.cfg = CFG.read(environ={'VELDO_INSTALLATION': str(self.installation)}, stream=io.StringIO())
                self.project = dict(CFG.read_project(str(self.repo), YAML.read, config=self.cfg, stream=io.StringIO()),
                                    repository=str(self.repo), branch_pattern=['ticket/{ticket}'], build_output=['build'])
                self.trees = Path(self.project['worktree_root'])
                self.trees.mkdir()
                self.conn = S.open_store(str(self.state / 'store.sqlite3'))
                self.serial = 0
                self.journal = lambda data: 'stub:' + S.digest_of(data.decode())
                CM.attach(S)
                ids = {'domain_uuid': 'domain', 'repository_uuid': 'repository', 'store_uuid': 'store'}
                command = {'command_id': 'owner', 'operation': 'enroll_principal', 'target': 'authority',
                    'parameters': {'principal': 'owner', 'principal_type': 'person', 'roles': ['membership_steward', 'project_owner'],
                        'public_key': public, 'independence_group': 'owner', 'scope': '*'},
                    'artifact_digests': [], 'expected_versions': {}}
                membership = CM.authority_state(S, self.conn)
                envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id='owner', principal='owner', request_revision=1,
                    nonce='owner-nonce', expires_at=1600, membership_version=membership['membership_version'],
                    delegation_version=membership['delegation_version'], command_digest=AC.canonical_command_digest(command))
                answer = CM.admit(S, self.conn, envelope, command, sign(AC.canonical_envelope_bytes(envelope)), ids, 1000,
                                 enrollee_signature=None, journal_signer=('authority', self.journal))
                assert answer['committed'], answer
                GI = load('control_git_identity', mods / 'control_git_identity.py')
                credential = next(field for field in GI.FIELDS if field.endswith('_credential'))
                GI.configure_identities(self.conn, 'domain', [dict(id='fixture', label='Fixture',
                    author_name='Fixture', author_email='fixture@example.invalid', remote_host='github.com',
                    remote_owner='fixture', projects_root=str(self.root), default_visibility='private',
                    api_token='keychain:fixture', **{credential: {'kind': 'ssh', 'reference': 'keychain:fixture'}})],
                    {'repository': {'path': str(self.repo), 'identity': 'fixture'}})
                S.bind_repositories(self.conn, 'domain', {'repository': str(self.repo)})
                self.L = SP.Ledger(S, self.conn, 'authority', self.journal, config=self.cfg, projects=[self.project],
                                  state_root=str(self.state), lifecycle=K.LIFECYCLE, host='fixture')
                assert self.L.set_pool('host', 'filesystem', device=self.L.device(str(self.state)))['ok']
                self.scope = {'type': 'project', 'id': 'orchard'}
                self.owner = {'scope': self.scope, 'ticket': 'VELDO-9315'}
                self.space = {'ledger': self.L, 'probe': P, 'kinds': K, 'remover': RM,
                    'keep': KP.keeper(self.L), 'free': lambda pool: shutil.disk_usage(self.root).free,
                    'run': self.client, 'proc': str(self.proc),
                    'owner_live': lambda owner: {'conclusive': True, 'group_empty': True}}
                self.L.act_checks = {name: lambda scope: None for name, ticket in SP.ACT_CONDITIONS}
                self.mode('act')
                (self.root / 'signers').write_text('')
                self.service = SV.Service(dict(ids, principal='authority', authority_generation=1,
                    repositories={'repository': [str(self.repo)]}, enrollment_signers=str(self.root / 'signers'),
                    observations=str(self.state / 'observations.jsonl'), journal_key=str(key),
                    installation=str(self.installation), state_root=str(self.state), host_identity='fixture',
                    store_path=str(self.state / 'store.sqlite3')), self.conn)
                self.service.sign = self.journal
                self.service.space = self.space

            def client(self, argv, cwd=None):
                if argv[0] != 'docker':
                    return P._run(argv, cwd)
                if argv[4] == 'ls':
                    return 0, ''
                return 1, 'Error: No such object'

            def mode(self, mode):
                self.serial += 1
                command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': self.scope, 'mode': mode},
                           'command_id': 'mode-%d' % self.serial, 'nonce': 'mode-nonce-%d' % self.serial}
                answer = self.L.set_mode({'command': command, 'signature': sign(S.canonical_bytes(command))}, CM, 1000)
                assert answer['ok'], answer

            def put(self, name, kind, data):
                self.serial += 1
                old = self.conn.execute('SELECT version FROM entities WHERE id=?', (name,)).fetchone()
                answer = S.execute(self.conn, {'command_id': 'fixture-%d' % self.serial, 'nonce': 'fixture-%d' % self.serial,
                    'principal': 'authority', 'operation': 'upsert_entity', 'artifact_digests': [],
                    'expected_versions': {name: old[0] if old else 0},
                    'parameters': {'entity_id': name, 'kind': kind, 'data': data}}, 'authority', self.journal, 1)
                assert self.conn.execute('SELECT 1 FROM entities WHERE id=?', (name,)).fetchone(), answer

            def tree(self, name, branch=None, repository=None):
                path = self.trees / name
                git(repository or self.repo, 'worktree', 'add', '-q', *(['-b', branch] if branch else ['--detach']), str(path), 'HEAD')
                return path

            def item(self, path, kind='scratch', owner=None):
                if kind == 'scratch':
                    path.mkdir(parents=True, exist_ok=True)
                    (path / 'planted').write_text('declared run scratch\n')
                answer = self.L.declare(kind, {'path': str(path)}, owner or self.owner, 'seam')
                assert answer['ok'], answer
                assert self.L.confirm(answer['item'])['ok']
                return answer['item']

            def due(self, identity):
                version = self.L._row(identity, SP.ITEM_KIND)[0]
                answer = self.L.signal('ticket_ended', {'items': [{'item': identity, 'version': version}]})
                assert answer['ok'], answer

            def removing(self, identity, carrier=None):
                self.due(identity)
                facts = {'event': 'ticket_ended', 'emitter': {'process': 'fixture', 'owner': self.owner}}
                if carrier is not None:
                    facts['carrier'] = carrier
                answer = self.L.outcome(identity, 'removing', facts)
                assert answer['ok'], answer

            def run(self, discover=False):
                reconciler = R.Reconciler(self.space)
                if not discover:
                    reconciler.discover = lambda: None
                return reconciler.run()

            def at(self, path):
                return next(((identity, item) for identity, item in self.L.items().items()
                             if item['locator'].get('path') == str(path) and item['state'] not in ('removed', 'gone')), (None, {}))

            def end(self, ticket='VELDO-9315'):
                return {'event': 'ticket_ended', 'transition': 'item_complete', 'command_id': 'complete:' + ticket,
                        'project': 'orchard', 'tickets': [ticket], 'seq': 42, 'entity': 'backlog:' + ticket}

        fixtures = []

        def case(name, body):
            rows.setdefault(name, [])
            try:
                fixture = Fixture(name.replace('/', '-'))
                fixtures.append(fixture)
                body(fixture, name)
            except Exception:
                check(name, traceback.format_exc(), False)

        def unknown(f, row):
            path = f.scratch / 'unknown'
            path.mkdir()
            (path / 'only-copy').write_text('work without an owner')
            loose = f.scratch / 'loose-work'
            loose.write_text('unowned loose file')
            f.protected.mkdir()
            (f.protected / 'data').write_text('protected fixture')
            result = f.run(True)
            check(row, 'unowned folder is a report and its planted work stays', result['ok'] and
                  f.at(path)[1].get('owner') is None and (path / 'only-copy').exists()
                  and (path / 'only-copy').read_text() == 'work without an owner')
            check(row, 'protect entry has no item', f.at(f.protected)[0] is None and (f.protected / 'data').exists())
            check(row, 'loose files are reports with no owner', f.at(loose)[0] is not None
                  and f.at(loose)[1].get('owner') is None and loose.read_text() == 'unowned loose file')

        case('ac1/no-owner', unknown)

        def trees(f, row):
            mapped, unmapped = f.tree('mapped', 'ticket/VELDO-9315'), f.tree('unmapped', 'personal')
            plain_path = f.root / 'plain-trees' / 'one'
            git(f.plain, 'worktree', 'add', '-q', '--detach', str(plain_path), 'HEAD')
            (mapped / 'build').mkdir()
            (mapped / '.gitignore').write_text('build/\n')
            (mapped / 'build' / 'generated').write_text('output')
            external = f.build / mapped.name
            external.mkdir()
            (external / 'output').write_text('output')
            session = f.scratch / 'sessions' / mapped.name / 'session-1'
            session.mkdir(parents=True)
            agent = f.trees / 'agent.git'
            git(f.repo, 'clone', '-q', '--bare', '--shared', str(f.repo), str(agent))
            child = f.trees / 'agent-child'
            git(agent, 'worktree', 'add', '-q', '-b', 'ticket/VELDO-9316', str(child), 'HEAD')
            result = f.run(True)
            check(row, 'mapped and unmapped worktrees keep exact scopes', result['ok'] and
                  f.at(mapped)[1].get('owner', {}).get('ticket') == 'VELDO-9315' and
                  f.at(unmapped)[1].get('owner') == {'scope': f.scope})
            check(row, 'plain repository worktree adopted, repository itself absent',
                  f.at(plain_path)[1].get('owner') == {'scope': {'type': 'plain_repository', 'id': str(f.plain)}}
                  and f.at(f.plain)[0] is None)
            check(row, 'agent repository and linked child recorded', f.at(agent)[1].get('form') == 'agent'
                  and f.at(child)[1].get('parent') == f.at(agent)[0])
            check(row, 'both build forms have the worktree parent: ' + repr(result['findings']),
                  all(f.at(path)[1].get('parent') == f.at(mapped)[0] for path in (mapped / 'build', external)))
            check(row, 'session pattern records session and scope',
                  f.at(session)[1].get('owner') == {'scope': f.scope, 'session': 'session-1'})
            git(unmapped, 'switch', '-q', '-c', 'another')
            f.run(True)
            check(row, 'recorded branch is refreshed', f.at(unmapped)[1].get('branch') == 'refs/heads/another')

        case('ac1/table', trees)

        def repositories(f, row):
            batch, candidate, mistaken = [f.state / name for name in ('batch', 'candidate', 'mistaken')]
            for path in (batch, candidate, mistaken):
                git(f.repo, 'clone', '-q', str(f.repo), str(path))
                (path / 'only-commit').write_text('unique commit for ' + path.name)
                git(path, 'add', 'only-commit')
                git(path, 'commit', '-q', '-m', 'work')
            tip = git(batch, 'rev-parse', 'HEAD')
            observation = f.state / 'observation'
            observation.mkdir()
            f.put('batch:one', 'batch', {'project': 'orchard', 'clone': str(batch), 'observation_dir': str(observation),
                                        'state': 'discarded'})
            f.put('landing:one', 'landing', {'project': 'orchard', 'workspace': str(candidate), 'lane': 'land-1'})
            f.put('batch:wrong', 'batch', {'project': 'orchard', 'observation_dir': str(mistaken)})
            result = f.run(True)
            check(row, 'batch and candidate are private repositories with forms: ' + repr(result['findings']), result['ok'] and
                  f.at(batch)[1].get('form') == 'batch_clone' and f.at(candidate)[1].get('form') == 'candidate_workspace')
            check(row, 'ended batch keeps its unique commit', batch.exists() and git(batch, 'rev-parse', 'HEAD') == tip)
            check(row, 'repository is never scratch or build output', f.at(mistaken)[1].get('owner') is None
                  and (mistaken / 'only-commit').exists())

        case('ac1/private-forms', repositories)

        def clone(f, row):
            root = f.state / 'clones' / 'clone-1'
            root.mkdir(parents=True)
            work, scratch = root / 'work', root / 'scratch'
            git(f.repo, 'clone', '-q', str(f.repo), str(work))
            scratch.mkdir()
            f.put('dispatch:run-1', 'dispatch', {'dispatch_id': 'run-1', 'contract': {
                'unit': 'VELDO-9315', 'station': 'build', 'reservation': {'project': 'orchard'}}})
            (root / 'clone.json').write_text(json.dumps({'schema': 'veldo.worker_clone/v1', 'root': str(root),
                'work': str(work), 'unit': 'VELDO-9315', 'domain': 'domain', 'repository': 'repository',
                'users': [{'role': 'worker', 'dispatch_id': 'run-1', 'scratch': str(scratch)}]}))
            run = f.state / 'runs' / 'run-1'
            run.mkdir(parents=True)
            sandbox = run / 'veldo-sandbox-1'
            sandbox.mkdir()
            f.run(True)
            check(row, 'manifest work is a worker clone with root parent', f.at(work)[1].get('form') == 'worker_clone'
                  and f.at(work)[1].get('parent') == f.at(root)[0])
            check(row, 'clone scratch, run and sandbox have the recorded dispatch',
                  all(f.at(path)[1].get('owner', {}).get('run', {}).get('id') == 'run-1'
                      for path in (scratch, run, sandbox)))

        case('ac1/worker-clone', clone)

        def missing(f, row):
            empty = f.scratch / 'missing'
            identity = f.item(empty)
            shutil.rmtree(empty)
            f.run()
            check(row, 'two missing names mark gone', f.L.item(identity)['state'] == 'gone')
            path = f.tree('changed')
            identity = f.item(path, 'worktree')
            f.removing(identity)
            (path / 'private').write_text('saved')
            assert KP.keep(f.L, identity, f.L.item(identity), snapshot=True)['ok']
            marked = Path(RM.marked(str(path), identity))
            git(f.repo, 'worktree', 'move', str(path), str(marked))
            (marked / 'private').write_text('only new work')
            f.run()
            check(row, 'changed marked worktree is restored and deferred, never gone',
                  path.exists() and (path / 'private').read_text() == 'only new work'
                  and f.L.item(identity)['state'] == 'deferred' and f.L.item(identity)['deferral']['rule'] == 'keep_failed')
            private = f.state / 'private-clone'
            git(f.repo, 'clone', '-q', str(f.repo), str(private))
            identity = f.item(private, 'agent_repository')
            f.removing(identity)
            (private / 'private').write_text('saved clone work')
            assert KP.keep(f.L, identity, f.L.item(identity), snapshot=True)['ok']
            marked = Path(RM.marked(str(private), identity))
            private.rename(marked)
            (marked / 'private').write_text('new clone work after save')
            f.run()
            check(row, 'changed marked private repository is restored with its new file', private.exists()
                  and (private / 'private').read_text() == 'new clone work after save'
                  and f.L.item(identity)['state'] == 'deferred'
                  and f.L.item(identity)['deferral']['rule'] == 'keep_failed')

        case('ac2/marked-not-gone', missing)

        def complete(f, row):
            path = f.scratch / 'half'
            identity = f.item(path)
            f.removing(identity)
            path.rename(RM.marked(str(path), identity))
            result = f.run()
            check(row, 'crashed scratch removal completes through remover', result['counts']['completed'] == 1
                  and f.L.item(identity)['state'] == 'removed' and not path.exists())
            work = f.tree('kept')
            item = f.item(work, 'worktree')
            head = git(work, 'rev-parse', 'HEAD')
            f.removing(item)
            assert KP.keep(f.L, item, f.L.item(item))['ok']
            f.run()
            held = f.L.item(item).get('kept') or {}
            check(row, 'whole saved worktree retries rules and keeps head in main', not work.exists()
                  and f.L.item(item)['state'] == 'removed' and head in held.get('refs', {}).values()
                  and KP.verify(f.L, item)['ok'])

        case('ac2/completion', complete)

        def failures(f, row):
            path = f.tree('no-record')
            identity = f.item(path, 'worktree')
            f.removing(identity)
            (path / 'only-copy').write_text('work')
            f.run()
            check(row, 'missing keep record defers and retains work', f.L.item(identity)['deferral']['rule'] == 'keep_failed'
                  and (path / 'only-copy').read_text() == 'work')
            path = f.tree('snapshot')
            identity = f.item(path, 'worktree')
            f.removing(identity)
            (path / 'private').write_text('saved work')
            assert KP.keep(f.L, identity, f.L.item(identity), snapshot=True)['ok']
            attempt = f.L.item(identity)['kept']['snapshots'][0]
            Path(attempt['path'], 'work', 'private').write_text('bad digest')
            result = f.run()
            check(row, 'bad saved digest refuses completion and is reported', path.exists()
                  and f.L.item(identity)['deferral']['rule'] == 'keep_failed'
                  and any(one['why'] == 'kept_work_missing' for one in result['findings']))
            reported = f.scratch / 'reported'
            reported.mkdir()
            (reported / 'only-copy').write_text('unowned work')
            f.L.report('scratch', {'path': str(reported)}, {'why': 'no owner'})
            f.run()
            check(row, 'reported work is never removed', (reported / 'only-copy').exists()
                  and (reported / 'only-copy').read_text() == 'unowned work')

        case('ac2/keep-failure', failures)

        def carrier(f, row):
            path = f.scratch / 'active'
            identity = f.item(path)
            before = P.carrier()
            f.removing(identity, dict(before, seq=10))
            f.space['proc'] = '/proc'
            snapshot = f.L.item(identity)
            f.run()
            check(row, 'live carrier is unchanged and no second remover gets its work',
                  path.exists() and f.L.item(identity) == snapshot)
            f.space['proc'] = str(f.proc)
            f.run()
            check(row, 'dead carrier resumes', not path.exists() and f.L.item(identity)['state'] == 'removed')
            path = f.scratch / 'unread-carrier'
            identity = f.item(path)
            f.removing(identity, {'pid': None, 'started': None, 'unread': 'denied', 'seq': 11})
            snapshot = f.L.item(identity)
            f.run()
            check(row, 'unread carrier is live', path.exists() and f.L.item(identity) == snapshot)

        case('ac5/live-carrier', carrier)

        def stale_read(f, row):
            path = f.scratch / 'racing'
            identity = f.item(path)
            f.due(identity)
            read = f.L.item
            taken = []
            proc = f.proc / '12345'
            proc.mkdir()
            (proc / 'stat').write_text('12345 (remover) S ' + '0 ' * 18 + '77 0\n')

            def race(item):
                old = read(item)
                if item == identity and not taken:
                    taken.append(True)
                    answer = f.L.outcome(item, 'removing', {'event': 'ticket_ended',
                        'carrier': {'pid': 12345, 'started': 77, 'seq': 1}})
                    assert answer['ok'], answer
                    path.rename(RM.marked(str(path), item))
                    taken.append(read(item))
                return old

            with patch.object(f.L, 'item', race):
                f.run()
            check(row, 'a remover taking the item after the first read keeps its marked folder and record',
                  len(taken) == 2 and read(identity) == taken[1] and not path.exists()
                  and Path(RM.marked(str(path), identity), 'planted').is_file())

        case('ac5/stale-read', stale_read)

        def shared_lock(f, row):
            for operation in ('signal', 'reconcile'):
                path = f.scratch / operation
                identity = f.item(path)
                if operation == 'reconcile':
                    f.removing(identity)
                    path.rename(RM.marked(str(path), identity))
                else:
                    f.due(identity)
                read, write = os.pipe()
                with f.L.item_lock(identity):
                    child = os.fork()
                    if child == 0:
                        os.close(read)
                        registry = dict(f.L.conn.command_registry)
                        f.L.conn.close()
                        f.L.conn = S.open_store(str(f.state / 'store.sqlite3'))
                        f.L.conn.command_registry.update(registry)
                        os.write(write, b'R')
                        try:
                            if operation == 'reconcile':
                                f.run()
                            else:
                                given = {k: v for k, v in f.space.items()
                                         if k not in ('ledger', 'probe', 'kinds', 'remover')}
                                SIG._carry(f.L, P, K, RM, 'ticket_ended', [identity], **given)
                            os.write(write, b'D')
                        finally:
                            os._exit(0)
                    os.close(write)
                    assert os.read(read, 1) == b'R'
                    blocked = not select.select([read], [], [], 3)[0]
                    whole = (Path(RM.marked(str(path), identity), 'planted').is_file() and not path.exists()
                             if operation == 'reconcile' else (path / 'planted').is_file())
                ready = select.select([read], [], [], 30)[0]
                finished = bool(ready) and os.read(read, 1) == b'D'
                if not ready:
                    os.kill(child, 9)
                os.waitpid(child, 0)
                os.close(read)
                check(row, operation + ' waits on the remover lock and rereads after release',
                      blocked and whole and finished and f.L.item(identity)['state'] == 'removed')

        case('ac5/shared-lock', shared_lock)

        def missing_keep(f, row):
            path = f.tree('missing-keep')
            identity = f.item(path, 'worktree')
            f.removing(identity)
            git(f.repo, 'worktree', 'remove', str(path))
            f.run()
            record = f.L.item(identity)
            check(row, 'a removing worktree absent at both names without keep is explicitly deferred',
                  record['state'] == 'deferred' and record['deferral']['rule'] == 'keep_failed'
                  and record['deferral']['refused_by'] == 'reconcile')

        case('ac2/missing-keep', missing_keep)

        def unread(f, row):
            path = f.scratch / 'closed' / 'item'
            identity = f.item(path)
            path.parent.chmod(0)
            try:
                result = f.run()
                check(row, 'unread parent never marks item gone', f.L.item(identity)['state'] != 'gone')
            finally:
                path.parent.chmod(0o700)
            check(row, 'unread work stays', (path / 'planted').exists())
            original = os.lstat

            def fail(where, *args, **kwargs):
                if str(where) in (str(path), path.name):
                    raise PermissionError('fixture EACCES')
                return original(where, *args, **kwargs)

            with patch.object(R.os, 'lstat', fail):
                try:
                    R.places(str(path), identity, RM)
                    refused = False
                except (OSError, RM._Refusal):
                    refused = True
            check(row, 'lstat error is not not-found, including for uid zero', refused)

        case('ac5/unread-path', unread)

        def due(f, row):
            path = f.scratch / 'due'
            identity = f.item(path)
            f.cfg['enabled'] = False
            f.due(identity)
            f.run()
            check(row, 'switch off retains due item', path.exists() and f.L.item(identity)['state'] == 'due')
            f.cfg['enabled'] = True
            f.mode('report')
            f.run()
            check(row, 'report mode retains unconfirmed due item', path.exists() and f.L.item(identity)['state'] == 'due')
            f.mode('act')
            f.run()
            record = f.L.item(identity)
            check(row, 'switch on carries due through rules and records carrier', not path.exists()
                  and record['state'] == 'removed' and record['removal']['carrier']['pid'] == os.getpid()
                  and type(record['removal']['carrier']['seq']) is int
                  and record['removal']['emitter']['owners'][identity] == f.owner)

        case('ac6/due', due)

        def concurrent(f, row):
            path = f.scratch / 'contended'
            identity = f.item(path)
            f.due(identity)
            original = f.L.outcome
            writes = []

            def compete(item, outcome, facts, **kwargs):
                if outcome == 'removing' and not writes:
                    won = original(item, outcome, dict(facts, winner='live Signal'), **kwargs)
                    assert won['ok'], won
                    writes.append(f.L.item(item))
                return original(item, outcome, facts, **kwargs)

            with patch.object(f.L, 'outcome', compete):
                f.run()
            check(row, 'one removing write wins; loser writes no item outcome and runs no remover',
                  len(writes) == 1 and f.L.item(identity) == writes[0] and (path / 'planted').exists())

        case('ac6/concurrent', concurrent)

        def kept(f, row):
            path = f.tree('owner-kept')
            identity = f.item(path, 'worktree')
            (path / 'only-copy').write_text('owner work')
            f.due(identity)
            answer = f.L.outcome(identity, 'kept', {'owner_keep': {'at': 1000}}, principal='owner')
            assert answer['ok'], answer
            record = f.L.item(identity)
            f.run(True)
            check(row, 'owner Keep survives discovery and recovery', f.L.item(identity) == record
                  and (path / 'only-copy').read_text() == 'owner work')

        case('loss/owner-keep', kept)

        def startup(f, row):
            f.mode('report')
            path = f.tree('on-start', 'ticket/VELDO-9315')
            order = []

            replayed = f.state / 'replayed'

            def replay():
                replayed.write_text(str(os.getpid()))

            answer = f.service.space_start(replay=replay)
            order.append('dispatch')
            check(row, 'immediate dispatch sees adopted item after synchronous replay', answer['ok'] and
                  f.at(path)[0] is not None and order == ['dispatch']
                  and replayed.is_file() and replayed.read_text() != str(os.getpid()))
            f.service.space_worker_start(reconcile=f.service.space_received_reconcile)
            check(row, 'no received event needs no second startup reconcile', f.service.space_consumer.active is None)
            records = f.conn.execute("SELECT COUNT(*) FROM entities WHERE kind='space_reconcile'").fetchone()[0]
            with patch.object(SV.time, 'time', return_value=365 * 86400 + 1000):
                for _ in range(3):
                    f.service.space_pass()
            after = f.conn.execute("SELECT COUNT(*) FROM entities WHERE kind='space_reconcile'").fetchone()[0]
            check('ac4/no-schedule', 'one year without event leaves exactly one reconcile', records == after == 1)
            answer = f.service.space_start(replay=lambda: (_ for _ in ()).throw(ValueError('unread spool')))
            check(row, 'startup failure is named and service still answers',
                  answer['reason'].startswith('space_reconcile_failed:') and isinstance(f.service.watermark(), int))

        case('ac3/startup', startup)

        def before_reconciler(f, row):
            adapter = f.service.space_docker = Docker(f.L)
            with patch.object(SV.SPACE_RECONCILE.Reconciler, 'run', side_effect=AssertionError('must not run')) as run:
                answer = f.service.space_start(replay=lambda: (_ for _ in ()).throw(ValueError('missing keys')))
            check(row, 'failure before Reconciler.run still starts Docker and subscribes every engine',
                  not answer['ok'] and run.call_count == 0 and adapter.starts == 1
                  and set(adapter.streams) == set(f.L.engines))

        def stop_reaps(f, row):
            reading, writing = os.pipe()
            try:
                f.service.space_consumer._spawn(lambda: os.read(reading, 1))
                pid = f.service.space_consumer.active[1]
                f.service.space_stop()
                try:
                    waited = os.waitpid(pid, os.WNOHANG)
                    reaped = False
                    if waited == (0, 0):
                        os.waitpid(pid, 0)
                except ChildProcessError:
                    reaped = True
                check(row, 'space_stop has reaped its active child, with no zombie in proc',
                      reaped and not Path('/proc/%d' % pid).exists())
            finally:
                os.close(reading)
                os.close(writing)

        case('ac7/stop-reaps', stop_reaps)

        def failed_task(f, row):
            # The second re-review's finding 2, in its probe's shape: a record is received while a
            # worker task runs, and the task then fails, or its worker is lost.
            consumer = f.service.space_consumer

            def drain():
                deadline = time.monotonic() + 60
                while consumer.active and time.monotonic() < deadline:
                    for fd in select.select(list(consumer.pipes()), [], [], 0.1)[0]:
                        consumer.readable(fd)

            for number, (how, ending) in enumerate((('refused', lambda: {'ok': False, 'reason': 'fixture_refusal'}),
                                                    ('lost', lambda: os._exit(3)))):
                reading, writing = os.pipe()

                def task(ending=ending, reading=reading):
                    os.read(reading, 1)
                    return ending()
                ticket = consumer.submit(('reconcile', 'fixture', how), task)
                event = f.L.event('session_ended', {'session': 'during-' + how, 'cwd': str(f.root), 'pid': 12345,
                                                    'started': 77 + number}, {'hook': 'session-end', 'host': 'fixture'})
                assert event['ok'], event
                consumer.advance()  # the journal advance of that record: the worker is busy with the task
                busy = consumer.active is not None and f.L.event_record(event['event'])['state'] == 'received'
                os.write(writing, b'x')
                drain()
                os.close(reading)
                os.close(writing)
                check(row, 'a record received while a task ran is consumed after the task ended %s [%s %s]'
                      % (how, ticket['answer'], f.L.event_record(event['event'])['state']),
                      busy and ticket['done'] and ticket['answer'].get('ok') is False
                      and ticket['answer'].get('reason') == ('fixture_refusal' if how == 'refused' else 'space_worker_lost')
                      and f.L.event_record(event['event'])['state'] == 'consumed' and consumer.active is None)
            f.service.space_stop()

        case('ac3/failed-task-advances', failed_task)

        class Docker:
            def __init__(self, ledger):
                self.ledger, self.streams, self.starts, self.snapshots = ledger, {}, 0, 0
                self.stopped = False

            def start(self):
                self.starts += 1
                if self.streams:
                    return {}
                self.streams['fixture'] = True
                return {'fixture': self.snapshot('fixture')}

            def snapshot(self, engine):
                self.snapshots += 1
                return {'read': True, 'counts': {}}

            def readable(self, fd):
                return {'events': 1}

            def pipes(self):
                return {}

            def stop(self):
                self.stopped = True
                self.streams.clear()

        case('ac3/failure-before-reconciler', before_reconciler)

        def docker_retry(f, row):
            adapter = f.service.space_docker = Docker(f.L)
            original = SV.SPACE_RECONCILE.Reconciler.discover
            calls = f.state / 'discover-calls'

            def fail_once(reconciler):
                with calls.open('a') as stream:
                    stream.write('called\n')
                if len(calls.read_text().splitlines()) == 1:
                    raise OSError('disk unread on first start')
                return original(reconciler)

            with patch.object(SV.SPACE_RECONCILE.Reconciler, 'discover', fail_once):
                answer = f.service.space_start(replay=lambda: None)
                check(row, 'a failed disk comparison still leaves Docker subscribed with one snapshot',
                      not answer['ok'] and adapter.streams and adapter.snapshots == 1)
                f.service.docker_readable(1)
                while f.service.space_consumer.active:
                    f.service.space_wait()
            check(row, 'next engine event retries and clears the refusal',
                  len(calls.read_text().splitlines()) == 2 and f.service.space_refusal is None and adapter.streams)
            adapter.streams.clear()
            f.service.space_reconcile()
            check(row, 'on demand starts a missing stream and consumes its snapshot once',
                  bool(adapter.streams) and adapter.snapshots == 2)

        case('ac3/docker-retry', docker_retry)

        def serve_order(f, row):
            path = f.tree('serve-start', 'ticket/VELDO-9315')
            service = f.service
            spool = SV.SPACE_CONSUMER.WORKER.SPOOL
            f.put(SP.OBSERVER, 'membership', dict(principal_type='service', roles=[], scope='*',
                  revoked_at=None, expires_at=None))
            f.put('key:' + SP.OBSERVER, 'verification_key', dict(principal=SP.OBSERVER,
                  public_key=public, effective_at=0))
            observer_key = Path(SP.key_path(SP.OBSERVER, str(f.installation)))
            observer_key.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(key, observer_key)
            observer_key.chmod(0o600)
            work = f.state / 'work.json'
            work.write_text(json.dumps({'schema': SV.WORK_SCHEMA, 'repositories': {
                'orchard': {'land': {'remote': 'origin', 'trunk': 'main'}}}}))
            work.chmod(0o600)
            service.config['work'] = str(work)
            folder = spool.spool_folder(str(f.state))
            tip = git(f.repo, 'rev-parse', 'HEAD')
            spool.put(folder, spool.entry('ref_changed', dict(repository=str(f.repo),
                ref='refs/heads/main', old=tip, new=tip), 'reference-transaction', 'fixture'))
            real_select = select.select
            queued = f.L.event('session_ended', {'session': 'serve', 'cwd': str(f.root), 'pid': 12345, 'started': 77},
                               {'hook': 'session-end', 'host': 'fixture'})
            assert queued['ok'], queued
            service.config.update(socket=str(f.state / 'authority.sock'), lock=str(f.state / 'authority.lock'), unit='fixture')
            adapter = service.space_docker = Docker(f.L)
            order, handlers = [], {}
            open_store, opened = SV.S.open_store, []

            def open_service(path):
                opened.append(path)
                return f.conn if len(opened) == 1 else open_store(path)

            start, worker = service.space_start, service.space_worker_start
            launches = f.state / 'replay-git-pids'
            popen = subprocess.Popen

            def observed_popen(argv, *args, **kwargs):
                if argv and os.path.basename(str(argv[0])) == 'git':
                    with launches.open('a') as stream:
                        stream.write(str(os.getpid()) + '\n')
                return popen(argv, *args, **kwargs)


            def start_once(*args, **kwargs):
                with patch.object(subprocess, 'Popen', observed_popen):
                    result = start(*args, **kwargs)
                order.append('reconcile')
                return result

            def start_worker(*args, **kwargs):
                order.append('worker')
                return worker(*args, **kwargs)

            def dispatch(*args):
                order.append('dispatch')
                check(row, 'first dispatch sees the reconciled worktree', f.at(path)[0] is not None)
                deadline = time.monotonic() + 60
                while service.space_consumer.active and time.monotonic() < deadline:
                    for fd in real_select(list(service.space_pipes()), [], [], 0.1)[0]:
                        service.space_readable(fd)
                pids = launches.read_text().splitlines() if launches.exists() else []
                check('ac3/replay-worker', 'pending spool git is started only by the worker across space_start',
                      bool(pids) and str(os.getpid()) not in pids)
                changed = [record for _, record in f.L.events() if record['type'] == 'ref_changed']
                check('ac3/serve-trunk-replay', 'real serve reads land before open_loop, records and consumes trunk',
                      not spool.pending(folder) and len(changed) == 1 and changed[0]['state'] == 'consumed')
                import threading
                import socket
                held_read, held_write = os.pipe()
                release_read, release_write = os.pipe()
                item = f.at(path)[0]

                def latched():
                    with f.L.item_lock(item):
                        os.write(held_write, b'held')
                        os.read(release_read, 1)
                service.space_consumer._spawn(latched)
                os.read(held_read, 4)
                answered = []

                def packet():
                    try:
                        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                            client.settimeout(10)
                            client.connect(str(Path(folder) / spool.SOCKET))
                            client.sendall(json.dumps({'call': 'about', 'repository': str(f.repo),
                                                       'path': None}).encode())
                            client.shutdown(socket.SHUT_WR)
                            answered.append(json.loads(client.recv(65536)))
                    finally:
                        os.write(release_write, b'x')
                sender = threading.Thread(target=packet)
                sender.start()
                service.space_refusal = 'fixture retry'
                for _ in range(20):
                    service.docker_readable(1)
                check('ac3/retry-coalesced', 'twenty engine events queue at most one retry behind the active worker',
                      list(service.space_consumer.tasks) == [('retry',)])
                with patch.object(SV.select, 'select', real_select):
                    answer = service.space_reconcile('cli')
                sender.join(12)
                check('ac3/reconcile-responsive', 'a packet is answered while reconcile waits for the worker latch',
                      bool(answered) and answered[0].get('served') and answer['ok'])
                for fd in (held_read, held_write, release_read, release_write):
                    os.close(fd)
                handlers[SV.signal.SIGTERM](SV.signal.SIGTERM, None)
                return None

            with contextlib.ExitStack() as stack:
                for obj, name, value in (
                    (SV, 'load_config', lambda path: service.config),
                    (SV, 'acquire', lambda *args: os.open(service.config['lock'], os.O_CREAT | os.O_RDWR, 0o600)),
                    (SV, 'previous_engine', lambda config: None), (SV, 'installed_engine', lambda config: str(mods)),
                    (SV.S, 'open_store', open_service), (SV.S, 'rebind_owners', lambda *a, **k: None),
                    (SV.S, 'drop_previous_owners', lambda *a, **k: None), (SV, 'Service', lambda *args: service),
                    (service, 'take_on', lambda: None), (service, 'announce_api', lambda: None),
                    (service, 'space_start', start_once), (service, 'space_worker_start', start_worker),
                    (SV.CH, 'open_channel', lambda *args: (None, None)),
                    (SV.SA, 'open_api', lambda *args: (None, None)), (SV, 'open_loop', lambda *args: (None, None)),
                    (SV.signal, 'signal', lambda sig, handler: handlers.update({sig: handler})),
                    (SV, 'notify', lambda *args: None), (SV.CC, 'serve_one', dispatch),
                    (SV.select, 'select', lambda reads, *args: ([reads[0]], [], []))):
                    stack.enter_context(patch.object(obj, name, value))
                SV.serve('fixture')
            check(row, 'real serve starts once before worker and dispatch, then stops the worker and engines',
                  order == ['reconcile', 'worker', 'dispatch'] and service.space_consumer.active is None
                  and service.space_pipes() == {} and adapter.stopped)

        case('ac7/serve-order', serve_order)

        def received(f, row):
            service = f.service
            marker = f.state / 'after-received'
            subject = {'session': 'ended', 'cwd': str(f.root), 'pid': 12345, 'started': 77}
            event = f.L.event('session_ended', subject, {'hook': 'session-end', 'host': 'fixture'})
            assert event['ok'], event
            identity = event['event']

            def after():
                assert f.L.event_record(identity)['state'] == 'consumed'
                marker.write_text('after received')
                service.space_received_reconcile()

            service.space_worker_start(reconcile=after)
            deadline = time.monotonic() + 60
            while service.space_consumer.active and time.monotonic() < deadline:
                for fd in select.select(list(service.space_pipes()), [], [], 0.1)[0]:
                    service.space_readable(fd)
            service.space_stop()
            check(row, 'received hook record drains before the child reconciliation and all workers are reaped',
                  f.L.event_record(identity)['state'] == 'consumed' and marker.is_file()
                  and service.space_consumer.active is None)

        case('ac7/received-hook', received)

        def cli(f, row):
            one = f.item(f.scratch / 'project-one')
            other = f.item(f.scratch / 'project-other', owner={'scope': {'type': 'project', 'id': 'other'}})
            f.due(one)
            f.due(other)
            held = f.L.item(other)
            from importlib.machinery import SourceFileLoader
            CLI = types.ModuleType('v315_cli')
            CLI.__file__ = str(mods / 'veldo')
            exec(SourceFileLoader('v315_cli', str(mods / 'veldo')).get_code('v315_cli'), CLI.__dict__)
            real = SV._organ
            request = []
            binding = {'domain_uuid': 'domain', 'repository_uuid': 'repository', 'store_uuid': 'store', 'enrolled_by': 'owner'}

            def send(workspace, packet, *args, **kwargs):
                request.append(packet)
                return {'accepted': True, 'result': f.service.apply(packet, binding)}

            def organ(name):
                if name == 'control_client':
                    return types.SimpleNamespace(send=send)
                if name == 'control_enrollment':
                    return types.SimpleNamespace(read_binding=lambda path: binding)
                if name == 'control_eligibility':
                    return types.SimpleNamespace(load_host_trust=lambda path: types.SimpleNamespace(
                        verifier=lambda *args: None, host_identity='fixture'))
                return real(name)

            with patch.object(SV, '_organ', organ), patch.object(CLI, '_mod', return_value=SV), contextlib.redirect_stdout(io.StringIO()):
                code = CLI.main(['space', 'reconcile', '--workspace', str(f.repo), '--principal', 'owner',
                                 '--key', str(key), '--project', 'orchard'])
            check(row, 'CLI signs an owner request through service; only the selected project is reconciled',
                  code == 0 and len(request) == 1 and f.L.item(one)['state'] == 'removed'
                  and f.L.item(other) == held and (f.scratch / 'project-other' / 'planted').is_file())
            check('cli/non-owner', 'CLI transport reaches the service for authorization checks', bool(request))
            if not request:
                return
            packet = request[0]
            packet['command']['parameters']['project'] = None
            refused = f.service.apply(packet, binding)
            check(row, 'changing signed project selection is refused', not refused.get('ok') and f.L.item(other) == held)
            with patch.object(f.L, 'acts', return_value=True), patch.object(SV, '_organ', organ), \
                    patch.object(CLI, '_mod', return_value=SV), contextlib.redirect_stdout(io.StringIO()):
                code = CLI.main(['space', 'reconcile', '--workspace', str(f.repo), '--principal', 'owner',
                                 '--key', str(key)])
            check(row, 'omitting project reaches the service for all projects',
                  code == 0 and len(request) == 2 and request[-1]['command']['parameters']['project'] is None
                  and f.L.item(other)['state'] == 'removed')
            f.put('visitor', 'membership', dict(principal_type='person', roles=[], scope='*',
                  revoked_at=None, expires_at=None))
            f.put('key:visitor', 'verification_key', dict(principal='visitor', public_key=public, effective_at=0))
            before = f.service.watermark()
            output = io.StringIO()
            with patch.object(SV, '_organ', organ), patch.object(CLI, '_mod', return_value=SV), \
                    contextlib.redirect_stdout(output):
                code = CLI.main(['space', 'reconcile', '--workspace', str(f.repo), '--principal', 'visitor',
                                 '--key', str(key)])
            check('cli/non-owner', 'a valid signature by an active non-owner cannot reconcile',
                  code != 0 and 'unauthorized:space_reconcile' in output.getvalue()
                  and f.service.watermark() == before)
            f.service.space_stop()

        case('cli/service-project', cli)

        def project_children(f, row):
            parent = f.scratch / 'selected-parent'
            identity = f.item(parent)
            child = parent / 'other-project'
            foreign = f.item(child, owner={'scope': {'type': 'project', 'id': 'other'}})
            f.due(identity)
            held = f.L.item(foreign)
            answer = f.service.space_reconcile('cli', project='orchard')
            check(row, 'project selection preserves a live child from another project inside its due parent',
                  answer['ok'] and f.L.item(identity)['state'] == 'deferred'
                  and f.L.item(foreign) == held and (child / 'planted').is_file())

        case('cli/foreign-child', project_children)

        def api_reconcile(f, row):
            import fcntl
            AUTH = load('api_authority', mods / 'control_api_authority.py')
            API = load('api', mods / 'control_api.py')
            AS, CRD, EN = AUTH.AS, AUTH.CR, AUTH.E
            f.put('api-edge', 'membership', {'principal_type': 'service', 'roles': [],
                'scope': ['repository'], 'revoked_at': None, 'expires_at': None})
            f.put(AC.edge_channel(AS.CHANNEL)['edge_key_id'], 'verification_key', {
                'schema': EN.SCHEMA, 'channel': AS.CHANNEL, 'principal': 'api-edge', 'public_key': public,
                'effective_at': 0, 'retired_at': None, 'revoked_at': None})
            f.put(CRD.entity_id('cred-owner'), CRD.KIND, {'credential_id': 'cred-owner', 'principal': 'owner',
                'effective_at': 0, 'revoked_at': None})
            item = f.item(f.scratch / 'api-item')
            f.due(item)
            descriptor = os.open(f.state / AUTH.LOCK_NAME, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                ids = {'domain_uuid': 'domain', 'repository_uuid': 'repository', 'store_uuid': 'store'}
                authority = AUTH.ApiAuthority(S, CM, f.conn, ids=ids, domain='domain', edge='api-edge',
                    intake=None, settlement=None, credentials=None, authority_lock=descriptor)
                authority.space_reconcile = f.service.space_reconcile
                now = time.time()
                assertion = dict(ids, schema=AS.SCHEMA, domain='domain', channel=AS.CHANNEL, edge='api-edge',
                    edge_key_id=AC.edge_channel(AS.CHANNEL)['edge_key_id'], request_id='api-reconcile',
                    principal='owner', credential_id='cred-owner', session='session-owner', operation='reconcile_space',
                    target='space', parameters={'project': 'orchard'}, expected_versions={}, issued_at=now,
                    expires_at=now + AS.LIFETIME)
                packet = {'assertion': assertion, 'signature': sign(S.canonical_bytes(assertion)), 'domain_signature': None}
                answer = authority.apply(packet)
                route = next(route for route in API.ROUTES if route.name == 'space.reconcile')
                check(row, 'the signed API action reaches the service and removes its due item',
                      answer['ok'] and answer['result']['outcome'] == 'reconciled'
                      and f.L.item(item)['state'] == 'removed' and route.operation == 'reconcile_space'
                      and authority.commands()['reconcile_space'] == SP.RECONCILE)
            finally:
                os.close(descriptor)

        case('api/service-project', api_reconcile)

        def bootstrap(f, row):
            f.service.space = None
            f.service.space_docker = Docker(f.L)
            started = f.service.space_start(replay=lambda: None, reconcile=lambda: {'ok': True})
            wired = f.service.space
            if not started['ok'] or wired is None:
                check(row, 'service start must install its ledger before ending events', False)
                return
            f.service.space_docker = None
            f.L = wired['ledger']
            f.L.act_checks = {name: lambda scope: None for name, ticket in SP.ACT_CONDITIONS}
            f.mode('act')
            f.space = dict(wired, run=f.client, proc=str(f.proc), owner_live=f.space['owner_live'])
            f.service.space = f.space
            path = f.scratch / 'completed'
            identity = f.item(path)
            found = f.end()
            transition = {'backlog:one': {'kind': 'backlog_item', 'data': {'state': 'DONE', 'project': 'orchard',
                'decomposition': [{'unit': 'VELDO-9315'}], 'history': [{'source': 'ACTIVE', 'target': 'DONE',
                    'operation': 'complete', 'command_id': 'complete:VELDO-9315'}]}}}
            events = f.service.space_events([{'seq': 1, 'command_id': found['command_id'], 'transition': transition}])
            for event in events:
                f.service.space_send(event)
            check(row, 'installation-built ledger sends completed ticket and removes its scratch',
                  wired is not None and len(events) == 1 and not path.exists() and f.L.item(identity)['state'] == 'removed')
            work = f.tree('abandon')
            item = f.item(work, 'worktree')
            version = f.L._row(item, SP.ITEM_KIND)[0]
            answer = f.service.space_abandon(item, version, 'owner', cause='owner_abandon')
            check(row, 'installation-built ledger serves owner Abandon with keep step',
                  answer['sent'] and not work.exists() and KP.verify(f.L, item)['ok'])

        case('ac7/bootstrap', bootstrap)

        def retry(f, row):
            first, second = f.scratch / 'first', f.scratch / 'second'
            one = f.item(first)
            two = f.item(second, owner={'scope': f.scope, 'ticket': 'VELDO-9316'})
            original = f.service._space_signal

            def fail(*args, **kwargs):
                raise OSError('locked store')

            with patch.object(f.service, '_space_signal', fail):
                f.service.space_send(f.end())
                f.service.space_send(f.end('VELDO-9316'))
            pending = R.EndingEvents(str(f.state)).pending()
            check(row, 'failed sends are durable with transition, subject and command', len(pending) == 2 and
                  all(record['attempts'] == 1 and record['event']['found']['transition'] == 'item_complete'
                      and record['event']['found']['command_id'] for name, record in pending))

            def fail_first(out, event, subjects, emitter, principal=None):
                if emitter['command_id'] == 'complete:VELDO-9315':
                    raise OSError('still locked')
                return original(out, event, subjects, emitter, principal)

            with patch.object(f.service, '_space_signal', fail_first):
                answer = f.service.space_reconcile()
            check(row, 'one raising event retains its count; the other is delivered', first.exists() and not second.exists()
                  and len(R.EndingEvents(str(f.state)).pending()) == 1
                  and R.EndingEvents(str(f.state)).pending()[0][1]['attempts'] == 2)
            f.service.space_start(replay=lambda: None)
            check(row, 'startup retries remaining event and clears pending only on return', not first.exists()
                  and f.L.item(one)['state'] == f.L.item(two)['state'] == 'removed'
                  and R.EndingEvents(str(f.state)).pending() == [])

        case('ac8/retry-events', retry)
        for fixture in fixtures:
            fixture.service.space_stop()
            fixture.conn.close()
    for row, assertions in rows.items():
        detail = '; '.join(label for label, ok in assertions if not ok)
        expect('space315/' + row + (': ' + detail if detail else ''), bool(assertions) and all(ok for _, ok in assertions))


_v315_suite()
