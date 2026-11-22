"""VELDO-0253: committed trees, atomic refusal, widening, Git saves and durable pins.

Git and SQLite are real. The decision fixture is an explicit owner-decision seam;
ordinary signed settlement is checked separately. All waits are event waits with
120-second hang detectors, independent of host speed.
"""


def _v253_suite():
    import contextlib
    import importlib.util
    import json
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
    }
    rows = ('ac1/whole-commit', 'ac1/committed-only', 'ac1/schema', 'ac1/notification',
            'ac2/widening-waits', 'ac2/exact-decision', 'ac2/superseded', 'ac2/classification',
            'ac3/one-source', 'ac3/stale-parent', 'ac3/layout-only', 'ac3/external-edit', 'ac3/push-refused',
            'ac4/pinned-survives', 'ac2/signed-settlement', 'ac2/forged-settlement',
            'ac1/setup-import', 'ac4/migrated-pins')
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
            check('ac1/committed-only', loader.reconcile()['outcome'] == 'accepted' and loader.live['installation.yaml'] == settings)
            _, problems = loader.validate(dict(files, **{'runs/current.json': b'{}',
                'projects/bad.yaml': WF.canonical({'account': 'absent'}),
                'connectors/local.yaml': WF.canonical(dict(connector, credential='literal')),
                'services/mail.yaml': WF.canonical({'schema': 'veldo.outside_service/v1', 'base_url': 'https://mail.example',
                                                   'credential': {'secret': 'missing'}})}))
            check('ac1/schema', 'installation_unknown_file:runs/current.json' in problems
                  and any(':account:unknown_reference' in p for p in problems)
                  and any(p.startswith('installation_secret_inline:') for p in problems)
                  and 'installation_secret_missing:missing' in problems)
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
                                  {'connectors/x.yaml': dict(connector, allowed_tools=[])}) == [])
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
            commit({'installation.yaml': settings})
            loader.reconcile()
            edited['budget']['steps'] = 10
            saved = workflows.save({'definition': edited}, principal='owner', base=2,
                base_commit=loader.accepted_commit, command_id='push-refused')
            check('ac3/push-refused', saved.get('push_refusal') == 'installation_push_failed:remote_refused'
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
            setup = load('v253_setup', mods / 'control_installation_setup.py')
            migration = S.open_store(root / 'migration' / 'authority.sqlite3')
            try:
                S.execute(migration, command, 'setup', sign, 1)
                legacy = WF.Workflows(S, migration, domain='domain', repository='repository', signer='setup', sign=sign)
                legacy.save({'definition': definition}, principal='owner', base=0)
                legacy.save({'definition': edited}, principal='owner', base=1)
                before = legacy.versions('example')
                imported = setup.create(S, migration, root / 'imported', settings=dict(settings, git={'branch': 'main'}),
                    identity=identity, domain='domain', repository='repository', signer='setup', sign=sign,
                    secret_exists=lambda name: False, observe=events.append)
                repeated = setup.create(S, migration, root / 'imported', settings=settings,
                    identity=identity, domain='domain', repository='repository', signer='setup', sign=sign,
                    secret_exists=lambda name: False, observe=events.append)
                check('ac1/setup-import', imported['outcome'] == 'accepted' and repeated['outcome'] == 'already_done'
                      and imported['commit'] == repeated['commit'] and legacy.versions('example') == before)
                check('ac4/migrated-pins', WU.pinned(S, migration, 'domain', 'repository', pinned) == definition
                      and WF._entity_row(migration, 'workflow-definition:' + WF.definition_digest(definition)) is not None)
            finally:
                migration.close()
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
                token = 'signed-fixture-' + eid
                S.execute(conn, dict(command_id=token, principal='setup', operation='upsert_entity', nonce=token,
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
                  and loader.accepted_commit == signed_commit and bool(loader.record()['decision']))
        except Exception as error:
            errors.append(type(error).__name__ + ': ' + str(error))
        finally:
            conn.close()
    for row in rows:
        if row not in emitted:
            check(row, False)
    if errors:
        print('VELDO-0253 fixture errors:', errors)


_v253_suite()
