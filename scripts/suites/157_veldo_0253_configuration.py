"""VELDO-0253: committed trees, atomic refusal, widening, Git saves and durable pins.

Git and SQLite are real. The decision fixture is an explicit owner-decision seam;
ordinary signed settlement is checked separately. All waits are event waits with
120-second hang detectors, independent of host speed.
"""


def _v253_suite():
    import contextlib
    import importlib.util
    import json
    import io
    from pathlib import Path
    import select
    import shutil
    import subprocess
    import tempfile

    PRODUCTION = {
        'installation.py': ROOT / ".veldo" / "installation.py",
        'control_installation_config.py': ROOT / ".veldo" / "control_installation_config.py",
        'control_installation_schema.py': ROOT / ".veldo" / "control_installation_schema.py",
        'control_installation_commit.py': ROOT / ".veldo" / "control_installation_commit.py",
        'control_workflow.py': ROOT / ".veldo" / "control_workflow.py",
        'control_workflow_unit.py': ROOT / ".veldo" / "control_workflow_unit.py",
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'control_installation_setup.py': ROOT / ".veldo" / "control_installation_setup.py",
        'installation_schema/schema.json': ROOT / ".veldo" / "installation_schema/schema.json",
    }
    rows = ('ac1/whole-commit', 'ac1/committed-only', 'ac1/schema', 'ac1/notification',
            'ac2/widening-waits', 'ac2/exact-decision', 'ac2/superseded', 'ac2/classification',
            'ac3/one-source', 'ac3/stale-parent', 'ac3/layout-only', 'ac3/external-edit', 'ac3/push-refused',
            'ac4/pinned-survives', 'ac2/signed-settlement', 'ac2/forged-settlement',
            'ac1/setup-import', 'ac4/migrated-pins', 'ac3/signed-owner-save', 'ac1/service-documents',
            'ac3/no-store-writer', 'ac1/private-template', 'ac2/signed-stale', 'ac1/approval-validation',
            'ac4/installation-bindings', 'ac1/last-good-reader',
            # Fix round 1. Each row below runs on its own installation and its own store, so an exception
            # in one row fails that row only and never hides a later one.
            'ac2/binding-removed', 'ac2/connector-removal', 'ac2/memory-server', 'ac2/project-remote',
            'ac2/other-widening', 'ac2/narrowing-direct', 'ac1/cross-references', 'ac1/plain-credential',
            'ac1/unread-secret-import', 'ac3/working-copy-follows',
            # Fix round 2: the installation's space section. One row per kind of widening change.
            'ac2/space-enabled', 'ac2/space-protect-removed', 'ac2/space-engine-added', 'ac2/space-root-added',
            'ac2/space-narrowing-direct',
            # Fix round 3: each remaining space setting is tested on the side it belongs to.
            'ac2/space-safeguard-loosened', 'ac2/space-unread-direct')
    emitted, errors = set(), []

    def check(row, condition):
        emitted.add(row)
        expect('VELDO-0253 ' + row, bool(condition))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='v253-') as temporary:
        root = Path(temporary)
        mods = root / 'engine'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__', '*.sqlite3', '*.db'))
        for name, path in PRODUCTION.items():
            shutil.copyfile(path, mods / name)
        S = load('v253_store', mods / 'control_store.py')
        C = load('v253_config', mods / 'control_installation_config.py')
        WF = load('v253_workflow', mods / 'control_workflow.py')
        WU = load('v253_unit', mods / 'control_workflow_unit.py')
        SIG = load('v253_signer', mods / 'control_signer.py')
        private = root / 'journal'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private)],
                       check=True, capture_output=True, timeout=120)
        sign = lambda data: SIG.sign_bytes(private, data, 'veldo-journal')
        conn = S.open_store(root / 'store' / 'authority.sqlite3')
        try:
            command = dict(command_id='member', principal='setup', operation='upsert_entity', nonce='member',
                artifact_digests=[], expected_versions={'owner': 0}, parameters=dict(entity_id='owner', kind='membership',
                data=dict(principal_type='person', roles=['project_owner'], scope='*', revoked_at=None, expires_at=None)))
            S.execute(conn, command, 'setup', sign, 1)
            identity = {'name': 'Example Owner', 'email': 'owner@example.com'}
            repo = C.I.Repository.create(root / 'installation')
            remote = root / 'remote.git'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True, timeout=120)
            settings = {'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Example Owner', 'role_id': 'owner'},
                        'git_identities': {'owner': identity}, 'git': {'branch': 'main', 'remote': str(remote)},
                        'accounts': {'primary': {'label': 'Example'}}}
            connector = {'command': 'local-tools', 'tools': ['read', 'write'], 'allowed_tools': ['read'], 'never': []}
            files = {'installation.yaml': WF.canonical(settings), 'connectors/local.yaml': WF.canonical(connector)}
            initial = repo.commit(files, None, identity, 'Initial installation')
            repo.publish(initial, None)

            class Decisions:
                def __init__(self):
                    self.requests, self.approvals, self.closed = {}, {}, []
                def request(self, proposal):
                    self.requests.setdefault(proposal['commit'], proposal)
                def approved(self, proposal):
                    return self.approvals.get((proposal['commit'], proposal['widening_digest']))
                def stale(self, proposal):
                    self.closed.append(proposal['commit'])
                def approve(self, proposal):
                    self.approvals[(proposal['commit'], proposal['widening_digest'])] = 'owner-decision:' + proposal['commit']
            decisions, events, notices = Decisions(), [], []
            loader = C.Loader(S, conn, repo, domain='domain', workflow_repository='repository', signer='setup', sign=sign,
                secret_exists=lambda name: name == 'present', decisions=decisions, observe=events.append, notify=notices.append)
            assert loader.reconcile(bootstrap=True)['outcome'] == 'accepted'
            workflows = WF.Workflows(S, conn, domain='domain', repository='repository', signer='setup', sign=sign)

            def commit(changes, parent=None):
                parent = repo.head() if parent is None else parent
                tree = dict(repo.snapshot(parent)['files'])
                for path, value in changes.items():
                    if value is None:
                        tree.pop(path, None)
                    else:
                        tree[path] = WF.canonical(value)
                result = repo.commit(tree, parent, identity, 'Change installation')
                repo.publish(result, parent)
                return result

            bad = commit({'projects/new.yaml': {'account': 'primary'},
                          'connectors/local.yaml': dict(connector, unknown=True)})
            refused = loader.reconcile()
            check('ac1/whole-commit', refused['outcome'] == 'refused' and loader.accepted_commit == initial
                  and 'projects/new.yaml' not in loader.live
                  and 'installation_invalid:connectors/local.yaml:$.unknown:unknown_key' in refused['problems'])
            repo.publish(initial, bad)
            (root / 'installation' / 'installation.yaml').write_text('not: committed\n')
            accepted_reader = C.I.load(environ={C.I.ENVIRONMENT: repo.folder}, stream=io.StringIO())
            check('ac1/committed-only', loader.reconcile()['outcome'] == 'accepted'
                  and loader.live['installation.yaml'] == accepted_reader.settings() == settings)
            _, problems = loader.validate(dict(files, **{'runs/current.json': b'{}',
                'projects/bad.yaml': WF.canonical({'account': 'absent'}),
                'connectors/local.yaml': WF.canonical(dict(connector, credential='literal')),
                'services/mail.yaml': WF.canonical({'schema': 'veldo.outside_service/v1', 'base_url': 'https://mail.example',
                                                   'credential': {'secret': 'missing'}})}))
            check('ac1/schema', 'installation_unknown_file:runs/current.json' in problems
                  and any(':account:unknown_reference' in p for p in problems)
                  and any(p.startswith('installation_secret_inline:') for p in problems)
                  and 'installation_secret_missing:missing' in problems)
            service_files = dict(files, **{
                'services/catalog.yaml': WF.canonical({'schema': 'veldo.outside_service/v1',
                    'base_url': 'https://catalog.example', 'openapi': 'catalog.openapi.json',
                    'tools_snapshot': 'catalog.tools.json'}),
                'services/catalog.openapi.json': WF.canonical({'openapi': '3.1.0',
                    'info': {'title': 'Catalog', 'version': '1'}, 'paths': {'/items': {'get': {
                        'responses': {'200': {'description': 'Items', 'content': {'application/json': {
                            'schema': {'type': 'object', 'properties': {'id': {'type': 'string'},
                                                                     'password': {'type': 'string'}},
                                       'required': ['id'], 'additionalProperties': False}}}}}}}}}),
                'services/catalog.tools.json': WF.canonical({'tools': [{'name': 'read', 'input_schema': {
                    'type': 'object', 'properties': {'id': {'type': 'string'}}, 'required': ['id']}}]})})
            _, valid_service = loader.validate(service_files)
            service_files.pop('services/catalog.tools.json')
            _, missing_service = loader.validate(service_files)
            check('ac1/service-documents', not valid_service and
                  'installation_invalid:services/catalog.yaml:tools_snapshot:unknown_reference' in missing_service)
            with contextlib.closing(C.I.RefChanges(repo)) as watch:
                widened = commit({'connectors/local.yaml': dict(connector, allowed_tools=['read', 'write'])})
                ready = select.select([watch], [], [], 120)[0]
                if ready:
                    watch.consume()
                check('ac1/notification', bool(ready) and repo.head() == widened)
            waiting = loader.reconcile()
            check('ac2/widening-waits', waiting['outcome'] == 'waiting' and loader.accepted_commit == initial
                  and loader.live['connectors/local.yaml']['allowed_tools'] == ['read'])
            proposal = decisions.requests[widened]
            decisions.approvals[(widened, 'sha256:wrong')] = 'wrong'
            still_waiting = loader.reconcile()['outcome'] == 'waiting'
            decisions.approve(proposal)
            accepted = loader.reconcile()
            check('ac2/exact-decision', still_waiting and accepted['outcome'] == 'accepted'
                  and loader.record()['decision'] == 'owner-decision:' + widened)
            pending = commit({'projects/new.yaml': {'account': 'primary'}})
            loader.reconcile()
            following = commit({'projects/new.yaml': None})
            loader.reconcile()
            check('ac2/superseded', pending in decisions.closed and loader.accepted_commit == following)
            kinds = [('roles/r.yaml', {'capabilities': ['shell']}), ('teams/t.yaml', {'roles': ['r']}),
                     ('schedules/s.yaml', {'when': 'daily'}),
                     ('projects/p.yaml', {'render_command': ['render']}),
                     ('services/s.yaml', {'base_url': 'https://service.example'})]
            check('ac2/classification', all(C.V.widening({}, {path: value}) for path, value in kinds)
                  and C.V.widening({'connectors/x.yaml': connector},
                                  {'connectors/x.yaml': dict(connector, allowed_tools=[])}) == []
                  and C.V.widening({'installation.yaml': {'accounts': {'one': {'label': 'Old', 'concurrency': 2}},
                        'owner': {'display_name': 'Old', 'role_id': 'owner'}}},
                      {'installation.yaml': {'accounts': {'one': {'label': 'New', 'concurrency': 1}},
                        'owner': {'display_name': 'New', 'role_id': 'owner'}}}) == []
                  and C.V.widening({'projects/p.yaml': {'deploy_targets': [{'destination': 'example'}]}},
                                   {'projects/p.yaml': {'deploy_targets': []}}) == []
                  and C.V.widening({'roles/r.yaml': {'configuration': {'engine': 'codex', 'mcp': [
                        {'server': 'local', 'revision': 1, 'tools': ['read', 'write']}]}}},
                      {'roles/r.yaml': {'configuration': {'engine': 'codex', 'mcp': [
                        {'server': 'local', 'revision': 1, 'tools': ['read']}]}}}) == [])
            unsafe = WU.shipped()
            next(edge for edge in unsafe['transitions'] if edge['id'] == 'gated')['to'] = 'land'
            parent = repo.head()
            _, errors_in_tree = loader.validate(dict(repo.snapshot()['files'], **{
                'workflows/code.json': WF.canonical(unsafe), 'workflows/code.layout.json': b'{}'}))
            try:
                workflows.save({'definition': unsafe}, principal='owner', base=0,
                               base_commit=loader.accepted_commit, command_id='unsafe-workflow')
                refusal = None
            except Exception as error:
                refusal = getattr(error, 'code', None)
            check('ac1/approval-validation', refusal == 'invalid_input:missing_owner_approval:land'
                  and any(p.endswith(':invalid_input:missing_owner_approval:land') for p in errors_in_tree)
                  and repo.head() == parent == loader.accepted_commit)
            definition = {'schema': 'veldo.workflow/v1', 'id': 'example', 'entry': 'build', 'terminal': ['done'],
                'nodes': {'build': {'kind': 'build', 'config': {}}, 'done': {'kind': 'end', 'config': {}}},
                'transitions': [{'id': 'built', 'from': 'build', 'port': 'done', 'to': 'done'}],
                'references': {}, 'budget': {'steps': 8}}
            saved = workflows.save({'definition': definition, 'layout': {}}, principal='owner', base=0,
                                   base_commit=loader.accepted_commit, command_id='canvas-one')
            document = workflows.load('example')
            source = document.get('source') or {}
            check('ac3/one-source', saved.get('commit') == repo.head() == loader.accepted_commit
                  and source.get('commit') == repo.head() and document['definition'] == definition
                  and repo.snapshot()['files']['workflows/example.json'] == WF.canonical(definition))
            pinned = WU.pin(definition, document['version'])
            source_commit = source['commit']
            prior = loader.accepted_commit
            changed = commit({'notes/new.txt': {'text': 'A note'}})
            try:
                workflows.save({'definition': definition}, principal='owner', base=1, base_commit=prior, command_id='stale')
                stale = False
            except Exception as error:
                stale = getattr(error, 'code', None) == 'stale_version'
            check('ac3/stale-parent', stale and repo.head() == changed and loader.accepted_commit == prior)
            loader.reconcile()
            layout = {'nodes': {'build': {'x': 12, 'y': 24}}}
            saved = workflows.save({'definition': definition, 'layout': layout}, principal='owner', base=1,
                base_commit=loader.accepted_commit, command_id='layout')
            check('ac3/layout-only', saved['version'] == 1 and workflows.load('example')['layout'] == layout)
            edited = json.loads(json.dumps(definition))
            edited['budget']['steps'] = 9
            commit({'workflows/example.json': edited})
            loader.reconcile()
            check('ac3/external-edit', workflows.load('example')['version'] == 2
                  and workflows.load('example')['definition'] == edited)
            settings['git']['remote'] = str(root / 'absent.git')
            remote_change = commit({'installation.yaml': settings})
            remote_waiting = loader.reconcile()
            decisions.approve(decisions.requests[remote_change])
            loader.reconcile()
            edited['budget']['steps'] = 10
            saved = workflows.save({'definition': edited}, principal='owner', base=2,
                base_commit=loader.accepted_commit, command_id='push-refused')
            check('ac3/push-refused', saved.get('push_refusal') == 'installation_push_failed:remote_refused'
                  and remote_waiting['outcome'] == 'waiting'
                  and loader.accepted_commit == saved['commit'])
            orphan = repo.commit({'installation.yaml': WF.canonical(settings)}, None, identity, 'Replace history')
            repo.publish(orphan, repo.head())
            repo.git('reflog', 'expire', '--expire=all', '--all')
            repo.git('gc', '--prune=now')
            try:
                repo.git('cat-file', '-e', source_commit)
                gone = False
            except C.I.InstallationError:
                gone = True
            check('ac4/pinned-survives', gone and WU.pinned(S, conn, 'domain', 'repository', pinned) == definition)
            restarted = C.Loader(S, conn, repo, domain='domain', workflow_repository='repository', signer='setup', sign=sign,
                secret_exists=lambda name: name == 'present', decisions=decisions, observe=events.append)
            check('ac1/last-good-reader', gone and accepted_reader.settings() == restarted.live['installation.yaml']
                  and C.I.load(environ={C.I.ENVIRONMENT: repo.folder}, stream=io.StringIO()).settings()
                  == restarted.live['installation.yaml'])
            loader = restarted
            setup = load('v253_setup', mods / 'control_installation_setup.py')
            migration = S.open_store(root / 'migration' / 'authority.sqlite3')
            try:
                S.execute(migration, command, 'setup', sign, 1)
                S.execute(migration, dict(command_id='import-account', principal='setup', operation='upsert_entity',
                    nonce='import-account', artifact_digests=[], expected_versions={'account:primary': 0},
                    parameters=dict(entity_id='account:primary', kind='account',
                        data={'id': 'primary', 'provider': 'codex', 'concurrency': 1})), 'setup', sign, 1)
                settings['accounts']['primary']['binary'] = '/opt/example-engine'
                capabilities = {'role': 'builder', 'engine': 'codex', 'native_tools': [{'name': 'shell', 'load': 'always'}],
                                'mcp': [], 'skills': [], 'instructions': [], 'settings': {}}
                imported_records = [
                    ('agent_configuration:builder:head', 'agent_configuration_head', {'role': 'builder', 'revision': 1}),
                    ('agent_configuration:builder:1', 'agent_configuration', capabilities),
                    ('default-team:head', 'default_team_head', {'revision': 1}),
                    ('default-team:1', 'default_team_revision', {'team': {'roles': {}}})]
                for eid, kind, data in imported_records:
                    S.execute(migration, dict(command_id='import-' + eid, principal='setup', operation='upsert_entity',
                        nonce='import-' + eid, artifact_digests=[], expected_versions={eid: 0},
                        parameters=dict(entity_id=eid, kind=kind, data=data)), 'setup', sign, 1)
                legacy = WF.Workflows(S, migration, domain='domain', repository='repository', signer='setup', sign=sign)
                legacy.save({'definition': definition}, principal='owner', base=0)
                legacy.save({'definition': edited}, principal='owner', base=1)
                before = legacy.history('example')
                imported = setup.create(S, migration, root / 'imported', settings=dict(settings, git={'branch': 'main'}),
                    identity=identity, domain='domain', repository='repository', signer='setup', sign=sign,
                    secret_exists=lambda name: False, observe=events.append)
                repeated = setup.create(S, migration, root / 'imported', settings=settings,
                    identity=identity, domain='domain', repository='repository', signer='setup', sign=sign,
                    secret_exists=lambda name: False, observe=events.append)
                check('ac1/setup-import', imported['outcome'] == 'accepted' and repeated['outcome'] == 'already_done'
                      and imported['commit'] == repeated['commit'] and legacy.history('example') == before
                      and legacy.load('example')['source']['commit'] == imported['commit']
                      and migration.installation_loader.live['installation.yaml']['accounts']['primary'] == {
                          'label': 'Example', 'binary': '/opt/example-engine', 'provider': 'codex', 'concurrency': 1}
                      and migration.installation_loader.live['roles/builder.yaml']['configuration'] == capabilities
                      and migration.installation_loader.live['teams/default.yaml']['configuration'] == {'roles': {}})
                check('ac4/migrated-pins', WU.pinned(S, migration, 'domain', 'repository', pinned) == definition
                      and WF._entity_row(migration, 'workflow-definition:' + WF.definition_digest(definition)) is not None)
                reader = S.open_store(root / 'migration' / 'authority.sqlite3')
                try:
                    detached = WF.Workflows(S, reader, domain='domain', repository='repository', signer='setup', sign=sign)
                    try:
                        detached.save({'definition': definition}, principal='owner', base=2)
                        refused_writer = False
                    except WF.Refused as error:
                        refused_writer = error.code == 'installation_managed'
                    check('ac3/no-store-writer', refused_writer and detached.history('example') == before)
                    projects_module = load('v253_projects', mods / 'control_project.py')
                    membership = load('v253_membership', mods / 'control_membership.py')
                    coordinates = dict(domain_uuid='domain', repository_uuid='repository', store_uuid='store')
                    projects = projects_module.Projects(S, membership, reader, coordinates, 'setup', sign,
                                                        stop=lambda _: None)
                    refused_binding = projects.apply({'command': dict(coordinates, operation=projects_module.BIND,
                        project='example', principal='owner', command_id='legacy-binding', nonce='legacy-binding'),
                        'signature': 'unsigned'})
                    try:
                        projects._bind(reader, {}, {}, {})
                        refused_transition = False
                    except projects_module.Refused as error:
                        refused_transition = error.code == 'installation_managed'
                    imported_loader = migration.installation_loader
                    imported_repo = imported_loader.repo
                    code = WU.shipped()
                    code['budget']['steps'] -= 1
                    imported_files = dict(imported_repo.snapshot()['files'], **{
                        'workflows/code.json': WF.canonical(code), 'workflows/code.layout.json': b'{}',
                        'projects/example.yaml': WF.canonical({'workflows': {'default': {'workflow': 'code'}}})})
                    binding_commit = imported_repo.commit(imported_files, imported_repo.head(), identity, 'Bind code')
                    imported_repo.publish(binding_commit, imported_repo.head())
                    imported_loader.decisions = decisions
                    waiting_binding = imported_loader.reconcile()
                    assert waiting_binding['outcome'] == 'waiting', waiting_binding
                    decisions.approve(decisions.requests[binding_commit])
                    accepted_binding = imported_loader.reconcile()
                    bound_pin, bound_code = WU.resolve(S, migration, 'domain', 'repository', {'name': 'example'})
                    default_pin, default_code = WU.resolve(S, migration, 'domain', 'repository', {'name': 'other'})
                    check('ac4/installation-bindings', refused_binding['reason'] == 'installation_managed'
                          and refused_transition and waiting_binding['outcome'] == 'waiting'
                          and accepted_binding['outcome'] == 'accepted' and bound_code == default_code == code
                          and bound_pin == default_pin and bound_pin['version'] == 1)
                finally:
                    reader.close()
            finally:
                migration.close()
            fresh = S.open_store(root / 'fresh' / 'authority.sqlite3')
            try:
                fresh_settings = {'schema': 'veldo.installation/v1', 'git': {'branch': 'main', 'remote': str(remote)}}
                fresh_remote = root / 'fresh-remote.git'
                subprocess.run(['git', 'init', '--bare', str(fresh_remote)], check=True, capture_output=True, timeout=120)
                fresh_settings['git']['remote'] = str(fresh_remote)
                first = setup.create(S, fresh, root / 'fresh-installation', settings=fresh_settings,
                    identity=identity, domain='fresh-domain', repository='repository', signer='setup', sign=sign,
                    secret_exists=lambda name: False, observe=events.append)
                fresh_repo = setup.I.Repository(root / 'fresh-installation')
                sent = subprocess.run(['git', '--git-dir', str(fresh_remote), 'rev-parse', 'refs/heads/main'],
                                      check=True, capture_output=True, text=True, timeout=120).stdout.strip()
                check('ac1/private-template', first['outcome'] == 'accepted' and sent == first['commit']
                      and fresh_repo.git('rev-list', '--count', 'HEAD').strip() == '1'
                      and set(fresh_repo.snapshot()['files']) == {'installation.yaml'}
                      and (root / 'fresh-installation').stat().st_mode & 0o777 == 0o700
                      and fresh_repo.git('status', '--porcelain') == '')
            finally:
                fresh.close()
            claims = load('v253_claims', mods / 'control_claim.py')
            claims.S = S
            A = load('v253_assignment', mods / 'control_assignment.py')
            P = load('v253_projection', mods / 'control_channel_projection.py')
            V = load('v253_presenter', mods / 'control_channel_presentation.py')
            ST = load('v253_settlement', mods / 'control_request_settlement.py')
            D = load('v253_decisions', mods / 'control_installation_decision.py')
            contract = load('v253_contract', mods / 'entity_contract.py')
            keys = {}
            def fixture(eid, kind, data):
                before = WF._entity_row(conn, eid)
                command_id = 'signed-fixture-' + eid
                S.execute(conn, dict(command_id=command_id, principal='setup', operation='upsert_entity', nonce=command_id,
                    artifact_digests=[], expected_versions={eid: before['version'] if before else 0},
                    parameters=dict(entity_id=eid, kind=kind, data=data)), 'setup', sign, 1)
            for who in ('owner', 'pm', 'api-edge'):
                keys[who] = root / ('key-' + who)
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys[who])],
                               check=True, capture_output=True, timeout=120)
                fixture(who, 'membership', dict(principal_type='person' if who == 'owner' else 'service',
                    roles=['project_owner'] if who == 'owner' else [], scope='*', independence_group=who,
                    revoked_at=None, expires_at=None))
                fixture('key:' + who, 'verification_key', dict(principal=who, effective_at=0,
                    public_key=' '.join(keys[who].with_suffix('.pub').read_text().split()[:2])))
            fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner',
                     chat_id=25301, revoked_at=None))
            class Edge:
                serial = 0
                def send(self, chat, text, reply_to):
                    self.serial += 1
                    return dict(chat_id=chat, message_id=self.serial, date=1, text=text, reply_to_message_id=reply_to)
            ids = dict(domain_uuid='domain', repository_uuid='repository', store_uuid='store')
            inbox = A.Inbox(S, claims.CM, claims, contract, conn, ids, 'setup', sign)
            presenter = V.Presenter(S, claims.CM, P, inbox, Edge(), conn, 'setup', sign, assignment=A)
            settlement = ST.Settlement(S, claims.CM, inbox, presenter, conn, 'setup', sign,
                                      assignment=A, presentation=V, api_edge='api-edge')
            command_sign = lambda who, data: SIG.sign_bytes(keys[who], data, 'veldo-command')
            loader.decisions = D.Decisions(settlement, 'owner', 'pm', lambda data: command_sign('pm', data))
            loader.reconcile()
            signed_base = loader.accepted_commit
            signed_commit = commit({'projects/signed.yaml': {'account': 'primary'}})
            outcome = loader.reconcile()
            proposal = loader.status()['proposal']
            request = A.assignment_id('repository', loader.decisions.alias(proposal))
            published = presenter.present(request)
            receipt = presenter.current(request)
            if not receipt:
                raise AssertionError(('presentation', outcome, published, settlement.observations))
            body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id='installation-answer',
                principal='owner', request_id=request, request_version=receipt['request_version'],
                presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                presentation_version=receipt['presentation_version'], choice='approve', rationale='Approve exact widening')
            forged = settlement.api_answer({'answer': body, 'signature': command_sign('owner', S.canonical_bytes(body))})
            check('ac2/forged-settlement', forged['outcome'] == 'refused' and loader.reconcile()['outcome'] == 'waiting')
            settled = settlement.api_answer({'answer': body, 'signature': command_sign('api-edge', S.canonical_bytes(body))})
            result = loader.reconcile()
            check('ac2/signed-settlement', settled['outcome'] != 'refused' and result['outcome'] == 'accepted'
                  and loader.accepted_commit == signed_commit and bool(loader.record()['decision'])
                  and inbox.read(request)['data']['configuration_commit'] == signed_base)
            owner_definition = WU.shipped()
            owner_base = loader.accepted_commit
            waiting = workflows.save({'definition': owner_definition}, principal='owner', base=0,
                                     base_commit=owner_base, command_id='owner-proposal')
            proposal = loader.status()['proposal']
            request = A.assignment_id('repository', loader.decisions.alias(proposal))
            presenter.present(request)
            receipt = presenter.current(request)
            body = dict(body, answer_id='owner-save-answer', request_id=request,
                request_version=receipt['request_version'], presentation_id=receipt['presentation_id'],
                presentation_digest=receipt['brief_digest'], presentation_version=receipt['presentation_version'])
            save_command = dict(configuration_commit=waiting['commit'], operation='save_workflow', principal='owner')
            approval = {'command': save_command, 'signature': command_sign('owner', S.canonical_bytes(save_command)),
                        'answer': {'answer': body, 'signature': command_sign('api-edge', S.canonical_bytes(body))}}
            saved = workflows.save({'definition': owner_definition}, principal='owner', base=0,
                base_commit=owner_base, command_id='owner-signed-save', approval=approval)
            check('ac3/signed-owner-save', waiting['outcome'] == 'waiting' and saved['outcome'] == 'accepted'
                  and saved['commit'] == waiting['commit'] == loader.accepted_commit
                  and workflows.load('code')['version'] == 1 and bool(loader.record()['decision']))
            commit({'schedules/pending.yaml': {'when': 'daily'}})
            waiting = loader.reconcile()
            proposal = loader.status()['proposal']
            request = A.assignment_id('repository', loader.decisions.alias(proposal))
            replacement = commit({'schedules/pending.yaml': None})
            reconciled = loader.reconcile()
            check('ac2/signed-stale', waiting['outcome'] == 'waiting' and reconciled['outcome'] == 'accepted'
                  and loader.accepted_commit == replacement and inbox.read(request)['data']['state'] == 'CANCELED')
        except Exception as error:
            errors.append(type(error).__name__ + ': ' + str(error))
        finally:
            conn.close()
        _v253_fix_rows(root, mods, load, check, errors)
    for row in rows:
        if row not in emitted:
            check(row, False)
    if errors:
        print('VELDO-0253 fixture errors:', errors)


def _v253_fix_rows(root, mods, load, check, errors):
    """Fix round 1: authority changes that wait, cross references, plain credentials, Veldo-made commits."""
    import json
    import os
    import subprocess

    S = load('v253f_store', mods / 'control_store.py')
    C = load('v253f_config', mods / 'control_installation_config.py')
    WF = load('v253f_workflow', mods / 'control_workflow.py')
    WU = load('v253f_unit', mods / 'control_workflow_unit.py')
    SIG = load('v253f_signer', mods / 'control_signer.py')
    setup = load('v253f_setup', mods / 'control_installation_setup.py')
    private = root / 'fix-journal'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private)],
                   check=True, capture_output=True, timeout=120)
    sign = lambda data: SIG.sign_bytes(private, data, 'veldo-journal')
    member = dict(command_id='member', principal='setup', operation='upsert_entity', nonce='member',
        artifact_digests=[], expected_versions={'owner': 0}, parameters=dict(entity_id='owner', kind='membership',
        data=dict(principal_type='person', roles=['project_owner'], scope='*', revoked_at=None, expires_at=None)))
    identity = {'name': 'Example Owner', 'email': 'owner@example.com'}
    settings = {'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Example Owner', 'role_id': 'owner'},
                'git_identities': {'owner': identity}, 'git': {'branch': 'main'},
                'accounts': {'primary': {'label': 'Example'}}, 'ports': {'api': 8080, 'web': 8443}}
    gated = WU.shipped()
    gated['id'] = 'gated'
    connector = {'command': 'local-tools', 'args': ['--read-only'], 'environment': {'LOG_LEVEL': 'info'},
                 'tools': ['read', 'write'], 'allowed_tools': ['read', 'write'], 'never': []}
    service = {'schema': 'veldo.outside_service/v1', 'base_url': 'https://service.example', 'body_limit': 1024}
    opened, serial, notices = [], [0], []
    # Built at run time so no credential-format literal is ever committed with this suite.
    plain = 'gh' + 'p_' + 'Q7' * 18

    class Pending:
        """No owner decision ever arrives: whatever waits for one must stay out of the live configuration."""
        def __init__(self):
            self.requests = []
        def request(self, proposal):
            self.requests.append(proposal)
        def approved(self, proposal):
            return None
        def stale(self, proposal):
            pass

    def store(place):
        conn = S.open_store(place / 'authority.sqlite3')
        opened.append(conn)
        S.execute(conn, member, 'setup', sign, 1)
        return conn

    def installation(extra):
        serial[0] += 1
        place = root / ('fix-%d' % serial[0])
        conn = store(place)
        repo = C.I.Repository.create(place / 'installation')
        tree = {'installation.yaml': WF.canonical(settings)}
        tree.update({path: WF.canonical(value) for path, value in extra.items()})
        first = repo.commit(tree, None, identity, 'Initial installation')
        repo.publish(first, None)
        loader = C.Loader(S, conn, repo, domain='domain', workflow_repository='repository', signer='setup',
            sign=sign, secret_exists=lambda name: name == 'present', decisions=Pending(), notify=notices.append,
            observe=lambda event: None)
        started = loader.reconcile(bootstrap=True)
        if started['outcome'] != 'accepted':
            raise AssertionError(('fixture', started))
        return loader, place

    def change(loader, changes):
        repo = loader.repo
        parent = repo.head()
        tree = dict(repo.snapshot(parent)['files'])
        for path, value in changes.items():
            if value is None:
                tree.pop(path)
            else:
                tree[path] = WF.canonical(value)
        made = repo.commit(tree, parent, identity, 'Change installation')
        repo.publish(made, parent)
        return made, loader.reconcile()

    def live(loader):
        return json.dumps(loader.live, sort_keys=True)

    def waits(start, changes, key):
        """The commit waits for the owner, names the widening key, and nothing of it is live."""
        loader, _ = installation(start)
        before, held = loader.accepted_commit, live(loader)
        made, result = change(loader, changes)
        return (result['outcome'] == 'waiting' and loader.accepted_commit == before and live(loader) == held
                and key in [item['key'] for item in result['widening']]
                and loader.decisions.requests[-1]['commit'] == made)

    def direct(start, changes):
        """Allowed directly by the spec: valid and live at once, with no owner decision requested."""
        loader, _ = installation(start)
        made, result = change(loader, changes)
        return (result['outcome'] == 'accepted' and loader.accepted_commit == made and result['widening'] == []
                and loader.decisions.requests == [] and loader.record()['classification'] == 'non_widening')

    def refused(start, changes, problem):
        """The whole commit is refused with the problem named, and the last good configuration stays."""
        loader, _ = installation(start)
        before, held = loader.accepted_commit, live(loader)
        _, result = change(loader, changes)
        return (result['outcome'] == 'refused' and problem in result['problems']
                and loader.accepted_commit == before and live(loader) == held)

    def isolated(row, body):
        try:
            check(row, body())
        except Exception as error:
            errors.append(row + ': ' + type(error).__name__ + ': ' + str(error))
            check(row, False)

    # Authority changes that must wait for the owner's decision.
    with_gated = {'workflows/gated.json': gated, 'projects/p.yaml': {'workflows': {'default': {'workflow': 'gated'}}}}
    code = WU.shipped()
    code['budget']['steps'] -= 1
    isolated('ac2/binding-removed', lambda: (
        waits(with_gated, {'projects/p.yaml': {}}, 'projects/p.yaml:workflows')
        and waits(with_gated, {'projects/p.yaml': None}, 'projects/p.yaml:workflows')
        and waits({'workflows/code.json': code}, {'workflows/code.json': None}, 'workflows/code.json:$')))
    without = lambda field: {key: value for key, value in connector.items() if key != field}
    isolated('ac2/connector-removal', lambda: (
        waits({'connectors/c.yaml': connector}, {'connectors/c.yaml': without('args')}, 'connectors/c.yaml:args')
        and waits({'connectors/c.yaml': connector}, {'connectors/c.yaml': without('environment')},
                  'connectors/c.yaml:environment')))
    server = {'command': '/opt/example/memory-server', 'args': ['--data', 'memory']}
    isolated('ac2/memory-server', lambda: (
        waits({}, {'memory/m.yaml': {'servers': {'s': server}}}, 'memory/m.yaml:servers')
        and waits({'memory/m.yaml': {'servers': {'s': server}}},
                  {'memory/m.yaml': {'servers': {'s': dict(server, args=['--data', 'other'])}}}, 'memory/m.yaml:servers')))
    landing = {'landing_destination': 'land_locally', 'remote': 'git@example.com:team/project.git',
               'repository': 'team/project', 'trunk': 'main'}
    isolated('ac2/project-remote', lambda: all(
        waits({'projects/p.yaml': landing}, {'projects/p.yaml': dict(landing, **{field: value})}, 'projects/p.yaml:' + field)
        for field, value in (('landing_destination', 'land_and_push'), ('remote', 'git@other.example:x/project.git'),
                             ('repository', 'other/project'), ('trunk', 'release'))))
    isolated('ac2/other-widening', lambda: (
        waits({}, {'installation.yaml': dict(settings, bot={'token': {'secret': 'present'}})}, 'installation.yaml:bot')
        and waits({}, {'installation.yaml': dict(settings, trackers={'t': {'site': 'https://tracker.example'}})},
                  'installation.yaml:trackers')
        and waits({}, {'installation.yaml': dict(settings, receiver={'inbound_file_cap': 10 ** 9})},
                  'installation.yaml:receiver.inbound_file_cap')
        and waits({'services/s.yaml': service}, {'services/s.yaml': dict(service, body_limit=10 ** 9)},
                  'services/s.yaml:body_limit')))
    # Changes the spec allows directly: narrowing.
    isolated('ac2/narrowing-direct', lambda: (
        direct({'connectors/c.yaml': connector}, {'connectors/c.yaml': dict(connector, allowed_tools=['read'])})
        and direct({'connectors/c.yaml': connector}, {'connectors/c.yaml': dict(connector, never=['write'])})
        and direct({}, {'installation.yaml': dict(settings, ports={'api': 8080})})
        and direct({'connectors/c.yaml': connector}, {'connectors/c.yaml': None})
        and direct({'projects/q.yaml': {'account': 'primary'}}, {'projects/q.yaml': None})
        and direct({'schedules/s.yaml': {'when': 'daily'}}, {'schedules/s.yaml': None})
        and direct({'memory/m.yaml': {'servers': {'s': server}}}, {'memory/m.yaml': {'servers': {}}})
        and direct({'services/s.yaml': service}, {'services/s.yaml': dict(service, body_limit=512)})
        and direct({'services/s.yaml': service}, {'services/s.yaml': None})))
    # The space section decides what Veldo may remove. A change that lets it remove more or protect less
    # waits for the owner; a change that removes less applies at once.
    mb = 1 << 20
    space = {'enabled': False, 'time_zone': 'UTC',
             'pools': {'host': {'floor': 2000 * mb, 'needs': {'build': 400 * mb, 'review': 100 * mb, 'gate': 600 * mb}}},
             'engines': ['default'],
             'scratch_roots': {'roots': ['/srv/example/scratch'], 'session_pattern': 'sessions/{session_id}'},
             'build_roots': ['/srv/example/build'], 'plain_repositories': [], 'client_accounts': [],
             'protect': {'paths': ['/srv/example/precious'], 'volumes': ['prod_db_*'], 'containers': ['prod-*'],
                         'images': ['base-*'], 'networks': ['prod-net'], 'compose_projects': ['prod']}}
    with_space = lambda section: {'installation.yaml': dict(settings, space=section)}
    spaced = lambda **keys: with_space(dict(space, **keys))
    protect = lambda **keys: spaced(protect=dict(space['protect'], **keys))
    isolated('ac2/space-enabled', lambda: (
        waits(with_space(space), spaced(enabled=True), 'installation.yaml:space.enabled')
        and waits({}, spaced(enabled=True), 'installation.yaml:space.enabled')))
    isolated('ac2/space-protect-removed', lambda: all(
        waits(with_space(space), protect(**{name: []}), 'installation.yaml:space.protect.' + name)
        for name in ('paths', 'volumes', 'containers', 'images', 'networks', 'compose_projects')))
    isolated('ac2/space-engine-added', lambda: (
        waits(with_space(space), spaced(engines=['default', 'prod-engine']), 'installation.yaml:space.engines')))
    repository = {'repository': '/srv/example/plain', 'worktree_root': '/srv/example/plain-worktrees'}
    isolated('ac2/space-root-added', lambda: (
        waits(with_space(space), spaced(build_roots=['/srv/example/build', '/srv']), 'installation.yaml:space.build_roots')
        and waits(with_space(space), spaced(scratch_roots=dict(space['scratch_roots'], roots=['/srv/example/scratch', '/srv'])),
                  'installation.yaml:space.scratch_roots.roots')
        and waits(with_space(space), spaced(plain_repositories=[repository]), 'installation.yaml:space.plain_repositories')
        and waits(with_space(space), spaced(client_accounts=['/srv/example/client']), 'installation.yaml:space.client_accounts')))
    wider = dict(space, enabled=True, engines=['default', 'spare'], build_roots=['/srv/example/build', '/srv/example/old'])
    isolated('ac2/space-narrowing-direct', lambda: (
        direct(with_space(wider), with_space(dict(wider, enabled=False)))
        and direct(with_space(wider), with_space(dict(wider, engines=['default'])))
        and direct(with_space(wider), with_space(dict(wider, build_roots=['/srv/example/build'])))
        and direct(with_space(wider), with_space(dict(wider, protect=dict(space['protect'], volumes=['prod_db_*', 'keep_*']))))
        and direct(with_space(wider), {'installation.yaml': settings})))
    # A changed session pattern adopts other directories as scratch, a process reader frees in-use work for
    # removal, and a lowered or dropped floor admits runs on less free disk: each waits for the owner.
    pool = space['pools']['host']
    reader = 'a' * 64
    isolated('ac2/space-safeguard-loosened', lambda: (
        waits(with_space(space), spaced(scratch_roots=dict(space['scratch_roots'], session_pattern='{session_id}')),
              'installation.yaml:space.scratch_roots.session_pattern')
        and waits(with_space(space), spaced(process_reader=reader), 'installation.yaml:space.process_reader')
        and waits(spaced(process_reader=reader), spaced(process_reader='b' * 64), 'installation.yaml:space.process_reader')
        and waits(with_space(space), spaced(pools={'host': dict(pool, floor=1000 * mb)}), 'installation.yaml:space.pools.host')
        and waits(with_space(space), spaced(pools={}), 'installation.yaml:space.pools.host')))
    # Nothing reads the time zone or a pool's needs at runtime, so changing them cannot let Veldo remove
    # more: they apply at once, as do a raised floor, an added pool and a reader removed.
    isolated('ac2/space-unread-direct', lambda: (
        direct(with_space(space), spaced(time_zone='Europe/Berlin'))
        and direct(with_space(space), spaced(pools={'host': dict(pool, needs=dict(pool['needs'], build=100 * mb))}))
        and direct(with_space(space), spaced(pools={'host': dict(pool, floor=3000 * mb)}))
        and direct(with_space(space), spaced(pools={'host': pool, 'spare': pool}))
        and direct(spaced(process_reader=reader), spaced(process_reader='none'))))
    references = [
        ({'schedules/s.yaml': {'when': 'daily', 'workflow': 'nosuch'}},
         'installation_invalid:schedules/s.yaml:workflow:unknown_reference'),
        ({'schedules/s.yaml': {'when': 'daily', 'project': 'nosuch'}},
         'installation_invalid:schedules/s.yaml:project:unknown_reference'),
        ({'projects/p.yaml': {'deploy_targets': {'site': {'service': 'nosuch'}}}},
         'installation_invalid:projects/p.yaml:deploy_targets.site.service:unknown_reference'),
        ({'memory/m.yaml': {'servers': {'s': {'service': 'nosuch'}}}},
         'installation_invalid:memory/m.yaml:servers.s.service:unknown_reference'),
        ({'memory/m.yaml': {'stores': {'notes': {'server': 'nosuch', 'path': 'notes'}}}},
         'installation_invalid:memory/m.yaml:stores.notes.server:unknown_reference')]
    valid = {'installation.yaml': settings, 'services/s.yaml': service,
             'projects/p.yaml': {'deploy_targets': {'site': {'service': 's'}}},
             'schedules/n.yaml': {'when': 'daily', 'workflow': 'code', 'project': 'p'},
             'memory/m.yaml': {'servers': {'s': {'service': 's'}}, 'stores': {'notes': {'server': 's', 'path': 'notes'}}}}
    isolated('ac1/cross-references', lambda: (
        all(refused({}, changes, problem) for changes, problem in references)
        and installation({})[0].validate({path: WF.canonical(value) for path, value in valid.items()})[1] == []))

    def credentials():
        loader, place = installation({'connectors/c.yaml': connector})
        before, held = loader.accepted_commit, live(loader)
        values = ('hunter2hunter2', 'plainvalue123456', 'plainvalue654321', 'plainvalue000000', plain)
        environment = dict(zip(('DB_PASSWORD', 'GITHUB_TOKEN', 'SSH_KEY', 'CLIENT_SECRET'), values), LOG_LEVEL='info')
        _, result = change(loader, {'connectors/c.yaml': dict(connector, environment=environment)})
        named = all('installation_secret_inline:connectors/c.yaml:$.environment.' + key in result['problems']
                    for key in ('DB_PASSWORD', 'GITHUB_TOKEN', 'SSH_KEY', 'CLIENT_SECRET'))
        _, reference = change(loader, {'connectors/c.yaml': dict(connector, environment={'API_TOKEN': {'secret': 'present'}})})
        _, inline = change(loader, {'connectors/c.yaml': dict(connector, environment={'LOG_LEVEL': plain})})
        loader.conn.commit()
        stored = b''.join(path.read_bytes() for path in place.glob('authority.sqlite3*'))
        told = json.dumps(notices)
        leaked = any(value in told or value.encode() in stored for value in values)
        return (result['outcome'] == reference['outcome'] == inline['outcome'] == 'refused' and named
                and any(p.startswith('installation_invalid:connectors/c.yaml:$.environment.API_TOKEN:')
                        for p in reference['problems'])
                and 'installation_secret_inline:connectors/c.yaml:$.environment.LOG_LEVEL' in inline['problems']
                and loader.accepted_commit == before and live(loader) == held and not leaked)
    isolated('ac1/plain-credential', credentials)

    def unread_import():
        folder = root / 'fix-import'
        repo = C.I.Repository.create(folder)
        (folder / 'notes').mkdir()
        (folder / 'notes' / 'call.txt').write_text('The token is ' + plain + '\n')
        (folder / 'installation.yaml').write_text(json.dumps(settings))
        remote = root / 'fix-import-remote.git'
        subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True, timeout=120)
        conn = store(root / 'fix-import-store')
        try:
            setup.create(S, conn, folder, settings=dict(settings, git={'branch': 'main', 'remote': str(remote)}),
                identity=identity, domain='domain', repository='repository', signer='setup', sign=sign,
                secret_exists=lambda name: False, observe=notices.append)
            seen = None
        except Exception as error:
            seen = getattr(error, 'code', None)
        try:
            repo.head()
            committed = True
        except C.I.InstallationError:
            committed = False
        sent = subprocess.run(['git', '--git-dir', str(remote), 'for-each-ref'], capture_output=True, text=True,
                              timeout=120).stdout
        return seen == 'installation_secret_inline:notes/call.txt:$' and not committed and sent == ''
    isolated('ac1/unread-secret-import', unread_import)

    def working_copy():
        conn = store(root / 'fix-checkout-store')
        folder = root / 'fix-checkout'
        first = setup.create(S, conn, folder, settings=settings, identity=identity, domain='domain',
            repository='repository', signer='setup', sign=sign, secret_exists=lambda name: False,
            observe=lambda event: None)
        loader = conn.installation_loader
        workflows = WF.Workflows(S, conn, domain='domain', repository='repository', signer='setup', sign=sign)
        definition = {'schema': 'veldo.workflow/v1', 'id': 'example', 'entry': 'build', 'terminal': ['done'],
            'nodes': {'build': {'kind': 'build', 'config': {}}, 'done': {'kind': 'end', 'config': {}}},
            'transitions': [{'id': 'built', 'from': 'build', 'port': 'done', 'to': 'done'}],
            'references': {}, 'budget': {'steps': 8}}
        saved = workflows.save({'definition': definition, 'layout': {}}, principal='owner', base=0,
                               base_commit=first['commit'], command_id='checkout-save')
        clean = loader.repo.git('status', '--porcelain') == ''
        followed = (folder / 'workflows' / 'example.json').read_bytes() == WF.canonical(definition)
        # The owner's ordinary `git commit -a` after the save keeps the save.
        (folder / 'notes').mkdir(exist_ok=True)
        (folder / 'notes' / 'owner.txt').write_text('An owner note\n')
        environment = dict(GIT_AUTHOR_NAME='Example Owner', GIT_AUTHOR_EMAIL='owner@example.com',
                           GIT_COMMITTER_NAME='Example Owner', GIT_COMMITTER_EMAIL='owner@example.com',
                           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, HOME=str(root),
                           PATH=os.environ['PATH'])
        for command in (['add', 'notes/owner.txt'], ['commit', '-q', '-a', '-m', 'Owner note']):
            subprocess.run(['git', '-C', str(folder), *command], check=True, capture_output=True, timeout=120,
                           env=environment)
        kept = loader.repo.snapshot()['files'].get('workflows/example.json') == WF.canonical(definition)
        loader.reconcile()
        # A dirty checkout is never touched by a save: the owner's edit stays exactly as written.
        (folder / 'installation.yaml').write_text('owner edit in progress\n')
        workflows.save({'definition': dict(definition, budget={'steps': 9}), 'layout': {}}, principal='owner',
                       base=1, base_commit=loader.accepted_commit, command_id='dirty-save')
        untouched = ((folder / 'installation.yaml').read_text() == 'owner edit in progress\n'
                     and (folder / 'workflows' / 'example.json').read_bytes() == WF.canonical(definition))
        return saved['commit'] != first['commit'] and clean and followed and kept and untouched
    isolated('ac3/working-copy-follows', working_copy)
    for conn in opened:
        conn.close()


_v253_suite()
