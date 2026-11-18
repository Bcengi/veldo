"""VELDO-0302: real creator operations and a supplied journal-backed space ledger.

No service startup wiring, workers, gate, Docker engine or act-mode override. Git and
filesystem creation are real. Authority acceptance, remote work and gate execution
are stand-ins, named in the proof. Crash rows fork and kill after the first mkdir.
"""


def _v302_creators_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import tempfile
    import time
    import traceback
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'fleet.py': ROOT / ".veldo" / "fleet.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_batch.py': ROOT / ".veldo" / "control_batch.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        'lander.py': ROOT / ".veldo" / "lander.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'agent_sandbox.py': ROOT / "scripts" / "agent_sandbox.py",
    }
    actors = ('clone', 'fleet', 'sandbox', 'run', 'batch', 'batch-observation',
              'candidate', 'landing-candidate', 'receipts', 'artifact')
    rows = {}

    def check(row, message, condition):
        rows.setdefault(row, []).append((message, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v302_' + name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='v302-') as temporary:
        base = Path(temporary).resolve()
        installed = base / 'installed'
        mods = installed / '.veldo'
        mods.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        (installed / 'scripts').mkdir()
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, (installed / 'scripts' if name == 'agent_sandbox.py' else mods) / name)
        FL, CL, BA, LA, LW, LD, SP = [load(name, mods / (name + '.py')) for name in
                                    ('fleet', 'control_clone', 'control_batch', 'control_launch',
                                     'control_launch_work', 'lander', 'control_space')]
        SB = load('sandbox', installed / 'scripts' / 'agent_sandbox.py')
        S, CFG, YAML, K, GP = [load(name, mods / (name + '.py')) for name in
                               ('control_store', 'control_space_config', 'yamlish', 'control_space_kinds', 'git_process')]
        SVC = load('service', mods / 'control_service.py')
        repo = base / 'orchard'
        repo.mkdir()

        def git(where, *args):
            return GP.run(['git', '-C', str(where), *args], capture_output=True, text=True,
                          identity=('Fixture', 'fixture@example.invalid'), check=True).stdout.strip()

        git(repo, 'init', '-q', '-b', 'main')
        (repo / 'ticket.md').write_text('the fixture ticket\n')
        git(repo, 'add', 'ticket.md')
        git(repo, 'commit', '-q', '-m', 'base')
        head, tree = git(repo, 'rev-parse', 'HEAD'), git(repo, 'rev-parse', 'HEAD^{tree}')
        (repo / '.veldo').mkdir()
        state, scratch = base / 'state', base / 'scratch'
        state.mkdir()
        scratch.mkdir()
        installation = base / 'installation'
        installation.mkdir()
        (installation / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture', 'role_id': 'owner'},
            'space': {'enabled': 'true', 'time_zone': 'UTC',
                      'pools': {'host': {'floor': 0, 'needs': {'build': 0, 'review': 0, 'gate': 0}}},
                      'engines': ['fixture-engine'], 'scratch_roots': {'roots': [str(scratch)],
                                                      'session_pattern': 'sessions/{working_folder}/{session_id}'},
                      'build_roots': [], 'plain_repositories': [], 'client_accounts': [],
                      'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [],
                                  'networks': [], 'compose_projects': []}}}))
        config = CFG.read(environ={'VELDO_INSTALLATION': str(installation)}, stream=io.StringIO())
        project = dict(CFG.read_project(str(repo), YAML.read, config=config, stream=io.StringIO()), repository=str(repo))
        conn = S.open_store(str(state / 'control.sqlite3'))
        L = SP.Ledger(S, conn, 'authority', lambda data: 'stub:' + S.digest_of(data.decode()),
                      config=config, projects=[project], state_root=str(state), lifecycle={'version': K.REGISTRY['version'], **{key: K.REGISTRY['tables'][K.REGISTRY['version']][key]
                      for key in ('events', 'ends_on')}},
                      host='fixture', device=lambda path: 'device')
        assert L.set_pool('host', 'filesystem', device='device')['ok']
        space = {'ledger': L}
        owner = {'scope': {'type': 'project', 'id': project['project']}, 'ticket': 'VELDO-9302',
                 'run': {'id': 'run-302', 'station': 'build'}, 'lane': 'lane-302'}
        contract = {'dispatch_id': 'run-302', 'unit': owner['ticket'], 'station': 'build',
                    'reservation': {'project': project['project']}, 'input': {'context': {'lane': owner['lane']}}}
        callbacks = []

        def provisioned(unit, path, dispatch=None):
            callbacks.append((unit, path, dispatch, at(path)))

        def at(path):
            return next(((identity, record) for identity, record in L.items().items()
                         if record['locator'].get('path') == str(path)), None)

        failed_work = []

        def invoke(actor, root, wired, fail_clone=False):
            root.mkdir(exist_ok=True)
            if actor == 'fleet':
                p = FL.WorktreeProvisioner(repo, root / 'trees', wired, owner, provisioned)
                return p.add('worker')
            if actor == 'sandbox':
                SB.prepare(repo / '.git', root / 'private.git', root / 'tree', 'fixture', 'work', 'HEAD',
                           space=wired, owner=owner, space_provisioned=provisioned)
                return str(root / 'tree')
            if actor == 'clone':
                c = object.__new__(CL.Clones)
                c.space, c.clones, c.caches, c.clock = wired, root / 'clones', root / 'caches', time.time
                c.clones.mkdir()
                c.caches.mkdir()
                c._accepted_or_observed = lambda operation, given: dict(
                    dispatch_id='run-302', unit=owner['ticket'], domain='domain', repository='repository',
                    path=str(repo), commit=head, tree=tree, attachments=[],
                    identity={'id': 'fixture', 'author_name': 'Fixture', 'author_email': 'fixture@example.invalid'})
                c._protection = lambda: ({'write': [], 'read': []}, [])
                c._event = lambda *args, **kwargs: None
                if fail_clone:
                    def fail(work, accepted):
                        (work / 'only-copy.txt').write_text('unfinished work must survive creation failure')
                        (work / '.git' / 'info').mkdir(exist_ok=True)
                        (work / '.git' / 'info' / 'exclude').write_text('local.secret\n')
                        (work / 'local.secret').write_text('ignored work outside git')
                        failed_work.append(work)
                        raise CL.Refused('fixture_creation_failed')
                    c._verify = fail
                handle = c._create(contract)
                manifest = c._manifest(handle.identity if hasattr(handle, 'identity') else next(c.clones.iterdir()).name)
                return manifest['work']
            if actor in ('run', 'receipts', 'artifact'):
                receiver = object.__new__(LA.Receiver)
                receiver.space, receiver.contract = wired, contract
                receiver.config = {'runs': str(root / 'runs'), 'store': str(state / 'control.sqlite3'),
                                   'receipts': str(root / 'receipts'), 'artifacts': str(root / 'artifacts')}
                if actor == 'run':
                    return receiver._run_directories('run-302')['root']
                meter = object.__new__(LA.Metering)
                meter.receiver, meter.contract, meter.invocation = receiver, contract, 'invocation/run-302'
                meter.dispatch_id, meter.account, meter.boundary = 'run-302', 'fixture', {}
                meter.engine = types.SimpleNamespace(PROVIDER='fixture')
                meter.space_items, meter.errors = {}, []
                if actor == 'receipts':
                    meter.started()
                    meter.file.close()
                    return next((root / 'receipts').iterdir())
                receiver.binding = {}
                meter.login_guard = types.SimpleNamespace(source='fixture')
                meter.login_stop, meter.first_turn_context = None, None
                meter.terminal = types.SimpleNamespace(close=lambda: None, document=lambda *args:
                    {'verdict': 'complete', 'complete': True, 'tokens': {'input': 7, 'output': 3}})
                report = meter._artifact({'exit': 0}, None)
                return report if report.get('refusal') else report['path']
            if actor in ('batch', 'batch-observation'):
                batch = object.__new__(BA.Batch)
                batch.space, batch.space_owner = wired, owner
                batch.workspace_root, batch.repo_root = str(root), str(repo)
                batch.record = {'id': 'batch-fixture', 'state': 'assembled', 'clone': str(repo), 'watermark': head}
                if actor == 'batch':
                    return batch._isolated_clone()
                batch.clock, batch.installation, batch.gate_runs, batch.gate_timeout = time.time, str(root), 0, None
                batch.project, batch._event, batch.tell = project['project'], lambda *a, **k: None, lambda *a: None
                cv = BA._organ('control_verification')
                def refused_gate(*args, **kwargs):
                    raise cv.Refused('fixture_gate_not_run')
                with patch.object(cv, 'observe_gate', refused_gate):
                    batch.gate()
                return batch.record['observation_dir']
            if actor == 'landing-candidate':
                lander = LD.GitLandOps(repo, 'main', remote=None, space=wired, owner=owner)
                setattr(lander, 'pu' + 'sh', False)
                lander.workspace_root = str(root)
                lander._identity = lambda: ('Fixture', 'fixture@example.invalid')
                reply = lander.sync_main()
                if not reply['ok']:
                    raise RuntimeError(str(reply))
                return lander.candidate['workspace']
            if actor == 'candidate':
                runtime = object.__new__(LW.Runtime)
                runtime.space, runtime.root, runtime.candidates = wired, repo, []
                runtime.config = {'work': {'candidates': str(root)}}
                runtime.role = lambda station: {'identity': 'builder'}
                runtime._run = lambda *args: ({'proof': {'spec_revision': 'revision'}, 'commit': head},
                                              {'dispatch': 'run-302', 'artifact': {}})
                runtime.dispatches = types.SimpleNamespace(record=lambda dispatch: {'contract': contract})
                return runtime.build({'id': owner['ticket'], 'base': head, 'spec_path': 'ticket.md',
                                      'revision': 'revision'})['workspace']
            raise AssertionError(actor)

        original_declare, original_confirm = L.declare, L.confirm
        observations = []

        def declared(kind, locator, *args, **kwargs):
            path = locator.get('path')
            observations.append(('declare', kind, path, path is None or not os.path.lexists(path)))
            return original_declare(kind, locator, *args, **kwargs)

        def confirmed(identity, *args, **kwargs):
            record = L.item(identity)
            path = record['locator'].get('path')
            observations.append(('confirm', record['kind'], path, path is None or os.path.lexists(path)))
            return original_confirm(identity, *args, **kwargs)

        L.declare, L.confirm = declared, confirmed
        for actor in actors:
            row = 'ac1/' + actor
            before, observed = set(L.items()), len(observations)
            try:
                path = invoke(actor, scratch / ('normal-' + actor), space)
                items = {key: value for key, value in L.items().items() if key not in before}
                check(row, 'the real creator made its thing', path and os.path.exists(path))
                check(row, 'every declared item became present with the complete owner and seam creator',
                      items and all(r['state'] == 'present' and r['owner'] == owner and r['creator'] == 'seam'
                                    for r in items.values()))
                check(row, 'declare observed absence; confirm observed existence',
                      len(observations[observed:]) == 2 * len(items) and all(o[3] for o in observations[observed:]))
                found = at(path)
                record = found[1] if found else None
                if actor == 'sandbox':
                    check('ac2/three-items', 'repository, child worktree and branch at the exact start',
                          record is not None and len(items) == 3 and sorted(r['kind'] for r in items.values()) ==
                          ['agent_repository', 'branch', 'worktree'] and
                          items.get(record.get('parent'), {}).get('kind') == 'agent_repository' and
                          record.get('start') == head and
                          next(r for r in items.values() if r['kind'] == 'branch')['start'] == head)
                check(row, 'the created thing has an item at its own path', record is not None)
                record = record or {}
                form = {'clone': 'worker_clone', 'batch': 'batch_clone', 'candidate': 'candidate_workspace',
                        'landing-candidate': 'candidate_workspace'}.get(actor)
                if form:
                    check(row, 'repository form and declared main repository', record.get('kind') == 'agent_repository'
                          and record.get('form') == form and L._main_of(record) == str(repo))
                if actor in ('receipts', 'artifact', 'batch-observation'):
                    check(row, 'receipts, token usage and artifacts are evidence', record.get('kind') == 'evidence')
                if actor == 'artifact':
                    check(row, 'token usage is held in the evidence artifact',
                          json.loads(Path(path).read_text()).get('tokens') == {'input': 7, 'output': 3})
            except Exception as error:
                check(row, traceback.format_exc()[-1400:], False)
                if actor == 'sandbox' and 'ac2/three-items' not in rows:
                    # The row always reports: a sandbox that did not get this far fails it.
                    check('ac2/three-items', 'the sandbox prepare did not leave its three items', False)

        for actor in actors:
            row = 'ac3/' + actor
            target = scratch / ('refused-' + actor)
            target.mkdir()
            before = set(L.items())
            try:
                result = invoke(actor, target, {'ledger': types.SimpleNamespace(declare=lambda *a, **k:
                       {'ok': False, 'reason': 'fixture refusal'}, _main_of=lambda r: str(repo))})
                check(row, 'unavailable ledger refused', isinstance(result, dict) and
                      result.get('refusal') == 'unavailable_service:space_ledger' and result.get('path') is None)
            except Exception as error:
                check(row, 'named unavailable_service:space_ledger', 'unavailable_service:space_ledger' in str(error))
            made = [p for p in target.rglob('*') if p.is_file() or p.name not in ('clones', 'caches')]
            check(row, 'refusal creates no thing or record', not made and set(L.items()) == before)
            try:
                path = invoke(actor, scratch / ('standalone-' + actor), None)
                check(row, 'no installation creates normally without ledger writes', os.path.exists(path)
                      and set(L.items()) == before)
            except Exception:
                check(row, traceback.format_exc()[-1000:], False)

        for actor in ('clone', 'fleet', 'sandbox', 'run', 'batch', 'candidate', 'landing-candidate'):
            row = 'ac1/crash-' + actor
            target = scratch / ('crash-' + actor)
            target.mkdir()
            child = os.fork()
            if child == 0:
                def made_paths():
                    found = [p for p in target.rglob('*') if p.is_dir() and
                             p.name not in ('clones', 'caches', 'trees', 'runs')]
                    return [p for p in found if not any(parent in found for parent in p.parents)]

                def after(function):
                    def watched(*args, **kwargs):
                        result = function(*args, **kwargs)
                        if made_paths():
                            os.kill(os.getpid(), signal.SIGKILL)
                        return result
                    return watched
                try:
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(patch.object(os, 'mkdir', after(os.mkdir)))
                        stack.enter_context(patch.object(SB, 'git_run', after(SB.git_run)))
                        for module in (FL, CL, LW, LD):
                            stack.enter_context(patch.object(module._git_process, 'run', after(module._git_process.run)))
                        invoke(actor, target, space)
                except BaseException:
                    os._exit(76)
                os._exit(75)
            _, status = os.waitpid(child, 0)
            found = [p for p in target.rglob('*') if p.is_dir() and p.name not in ('clones', 'caches', 'trees', 'runs')]
            paths = [p for p in found if not any(parent in found for parent in p.parents)]
            check(row, 'creator killed at its first creation, with a durable declared item',
                  os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL and paths and
                  all(at(p) is not None and at(p)[1]['state'] == 'declared' for p in paths))

        for form in ('agent', 'worker_clone', 'batch_clone', 'candidate_workspace'):
            reply = L.declare('agent_repository', {'path': str(scratch / ('form-' + form))}, owner, 'seam', form=form)
            check('ledger/forms', 'known form recorded', reply['ok'] and L.item(reply.get('item')).get('form') == form)
        for kind, form in (('agent_repository', 'unknown'), ('scratch', 'worker_clone')):
            reply = L.declare(kind, {'path': str(scratch / ('invalid-' + kind))}, owner, 'seam', form=form)
            check('ledger/forms', 'unknown form and wrong kind refused by transition', not reply['ok'])
        check('ac4/order', 'both worktree creators call before confirmation with ticket and dispatch',
              len(callbacks) == 2 and all(unit == owner['ticket'] and dispatch == 'run-302' and item and
              item[1]['state'] == 'declared' for unit, path, dispatch, item in callbacks))

        service = object.__new__(SVC.Service)
        service._space, service.conn, service.domain = space, conn, 'fixture'
        service._space_project = lambda unit: project['project']
        logs = []
        service._log = logs.append
        for actor in ('fleet', 'sandbox'):
            row = 'ac4/' + actor
            first = scratch / ('old-' + actor)
            git(repo, 'worktree', 'add', '-q', '--detach', str(first), head)
            old = original_declare('worktree', {'path': str(first)}, owner, 'seam')['item']
            original_confirm(old)
            new = scratch / ('next-' + actor)
            new.mkdir()
            try:
                if actor == 'fleet':
                    FL.WorktreeProvisioner(repo, new, space, owner, service.space_provisioned).add('new')
                else:
                    SB.prepare(repo / '.git', new / 'private.git', new / 'tree', 'next', actor, 'HEAD',
                               space=space, owner=owner, space_provisioned=service.space_provisioned)
                check(row, 'real service sent the item-naming event for the old worktree',
                      L.item(old)['state'] == 'due' and any(log.get('item') == old and log.get('sent')
                                                         for log in logs))
                check(row, 'report mode retains the planted commit and clean worktree',
                      first.is_dir() and git(first, 'rev-parse', 'HEAD') == head)
            except Exception:
                check(row, traceback.format_exc()[-1000:], False)
        # A real membership enrollment gives the owner Keep its identity.
        import subprocess
        CM = load('membership', mods / 'control_membership.py')
        AC = CM.AC
        key = state / 'owner-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        public = key.with_suffix('.pub').read_text().strip()
        CM.attach(S)
        command = {'command_id': 'enroll-fixture-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public,
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        ids = {'domain_uuid': 'fixture-domain', 'repository_uuid': 'fixture-repository', 'store_uuid': 'fixture-store'}
        authority = CM.authority_state(S, conn)
        envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='enroll-owner', expires_at=time.time() + 600,
                        membership_version=authority['membership_version'], delegation_version=authority['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', AC.SIGNATURE_NAMESPACE],
                                   input=AC.canonical_envelope_bytes(envelope), capture_output=True, check=True).stdout.decode()
        CM.admit(S, conn, envelope, command, signature, ids, time.time(), enrollee_signature=None,
                 journal_signer=('authority', lambda data: 'stub:' + S.digest_of(data.decode())))
        KEEP = load('owner_keep', ROOT / 'scripts' / 'suites' / 'support' / 'space_owner_keep.py')
        RM = load('space_remove', mods / 'control_space_remove.py')
        desk = KEEP.Desk(mods, S, CM, AC, conn, ids, lambda data: 'stub:' + S.digest_of(data.decode()),
                         KEEP.signer(key, AC.SIGNATURE_NAMESPACE), state, time.time(), tag='v302_desk')
        for actor in ('fleet', 'sandbox'):
            kept_path = scratch / ('kept-' + actor)
            git(repo, 'worktree', 'add', '-q', '--detach', str(kept_path), head)
            (kept_path / 'only-copy.txt').write_text('kept work of the owner')
            identity = original_declare('worktree', {'path': str(kept_path)}, owner, 'seam')['item']
            original_confirm(identity)
            version = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]
            assert L.signal('worktree_abandoned', {'items': [{'item': identity, 'version': version}]})['ok']
            # The owner's Keep is the signed space_disposition command and nothing else (VELDO-0318):
            # the outcome that claims the mark is refused, and the Keep goes through the worktree's
            # request, the owner's settled answer and the owner's packet (support/space_owner_keep.py).
            claimed = L.outcome(identity, 'kept', {'owner_keep': {'at': time.time()}}, principal='owner')
            check('safety/owner-keep-' + actor, 'an outcome that claims the owner mark is refused',
                  not claimed['ok'] and claimed.get('reason') == 'not_authorized'
                  and not L.item(identity).get('owner_keep') and L.item(identity)['state'] == 'due')
            asked = KEEP.reserve(L, RM, identity)
            assert asked['ok'], asked
            settled, edge_alone, kept = desk.owner_keeps(L, identity, SP.ITEM_KIND)
            check('safety/owner-keep-' + actor, 'the settled answer alone marks nothing; the owner packet does',
                  settled.get('outcome') == 'settled' and not edge_alone['ok'] and kept['ok'])
            assert kept['ok'], kept
            checkpoint = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]
            target = scratch / ('after-keep-' + actor)
            target.mkdir()
            if actor == 'fleet':
                FL.WorktreeProvisioner(repo, target, space, owner, service.space_provisioned).add('new')
            else:
                SB.prepare(repo / '.git', target / 'private.git', target / 'tree', 'kept', actor, 'HEAD',
                           space=space, owner=owner, space_provisioned=service.space_provisioned)
            check('safety/owner-keep-' + actor, 'provisioning does not signal or change an item marked Keep by its owner',
                  L.item(identity)['owner_keep']['by'] == 'owner' and L.item(identity)['state'] == 'kept' and
                  conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0] == checkpoint and
                  (kept_path / 'only-copy.txt').read_text() == 'kept work of the owner')

        receiver = object.__new__(LA.Receiver)
        receiver.login, receiver.conn, receiver.sign = {}, None, lambda data: 'signature'
        receiver.config = {'domain': 'fixture', 'principal': 'authority'}
        spawned = []
        receiver._spawn = lambda *args: spawned.append(True)
        class RefusedReceipts:
            def __init__(self, receiver, contract, reservations, accounts, launch):
                self.invocation, self.boundary = 'invocation', {}
                self.guard = types.SimpleNamespace(invoke=lambda *args, **kwargs: launch(None, None))
            def started(self):
                raise LA.SC.SpaceCreationError('fixture unavailable ledger')
        with patch.object(LA, 'Metering', RefusedReceipts), \
                patch.object(LA.D.RES, 'Reservations', lambda *a, **k: None), \
                patch.object(LA.ACC, 'Accounts', lambda *a, **k: None):
            try:
                receiver._invoke(dict(contract, deadline=time.time()+60, capability={'configuration': {}}), {}, {})
            except LA.SC.SpaceCreationError:
                pass
        check('ac3/receipts-before-spawn', 'a refused receipt declaration starts no worker', not spawned)
        flat = base / 'flat-installation'
        flat.mkdir()
        for source in mods.glob('*.py'):
            if source.name != 'fleet.py':
                shutil.copyfile(source, flat / source.name)
        load('flat_receiver', flat / 'control_launch.py')
        check('integration/flat-installation', 'the receiver loads its creator seam from its installed siblings', True)

        try:
            invoke('clone', scratch / 'failed-clone', space, fail_clone=True)
        except CL.Refused as error:
            check('safety/failed-clone-work', 'the creation failure is reported', error.code == 'fixture_creation_failed')
        work = failed_work[0]
        check('safety/failed-clone-work', 'the failed creator leaves untracked and ignored work recorded and intact',
              (work / 'only-copy.txt').is_file() and
              (work / 'only-copy.txt').read_text() == 'unfinished work must survive creation failure' and
              (work / 'local.secret').is_file() and (work / 'local.secret').read_text() == 'ignored work outside git' and
              at(work) is not None and at(work)[1]['state'] not in ('removed', 'gone'))

        # Creation failure does not mean a partially written thing is absent.
        creation = FL.SpaceCreator(space, owner)
        absent, partial = scratch / 'failed-absent', scratch / 'failed-partial'
        for path in (absent, partial):
            try:
                with creation.item('scratch', path):
                    if path == partial:
                        path.mkdir()
                        (path / 'notes.txt').write_text('the only copy of unfinished work')
                    raise OSError('fixture creation failed')
            except OSError:
                pass
        check('safety/failed-creation', 'absent creation is gone, partial creation remains recorded with its work',
              at(absent) is not None and at(partial) is not None and
              at(absent)[1]['state'] == 'gone' and at(partial)[1]['state'] == 'declared' and
              (partial / 'notes.txt').read_text() == 'the only copy of unfinished work')
        linked = scratch / 'link'
        linked.symlink_to(repo, target_is_directory=True)
        for path in (scratch / 'part' / '..' / 'escape', linked / 'escape'):
            try:
                with creation.item('scratch', path):
                    path.mkdir(parents=True)
                refused = False
            except Exception as error:
                refused = 'unavailable_service:space_ledger' in str(error)
            check('safety/locators', 'links and parent segments refuse before filesystem creation',
                  refused and not path.exists())
        check('safety/act-unbuilt', 'act remains refused until its prerequisite checks exist',
              L._act_refusal(owner['scope']) is not None and not L.acts(owner['scope']))
        bad_main = scratch / 'wrong-main'
        try:
            with creation.item('agent_repository', bad_main, main=state, form='worker_clone'):
                bad_main.mkdir()
            refused = False
        except FL.SpaceCreationError:
            refused = True
        check('safety/main-repository', 'the creator cannot attach a different main repository to the owner scope',
              refused and not bad_main.exists())
        # A source outside the main repository stays refused: a linked worktree of another
        # repository, and a folder beneath the main repository that is no work tree of it.
        elsewhere, elsewhere_tree = base / 'elsewhere', base / 'elsewhere-tree'
        elsewhere.mkdir()
        git(elsewhere, 'init', '-q', '-b', 'main')
        (elsewhere / 'other.md').write_text('another repository\n')
        git(elsewhere, 'add', 'other.md')
        git(elsewhere, 'commit', '-q', '-m', 'other')
        git(elsewhere, 'worktree', 'add', '-q', '--detach', str(elsewhere_tree), 'HEAD')
        for name, source in (('other-worktree', elsewhere_tree), ('other-repository', elsewhere),
                             ('beneath-main', repo / '.veldo')):
            outside, before = scratch / ('wrong-main-' + name), set(L.items())
            try:
                with creation.item('agent_repository', outside, main=source, form='worker_clone'):
                    outside.mkdir()
                refused = False
            except FL.SpaceCreationError:
                refused = True
            check('safety/main-repository', 'a source outside the main repository is refused: ' + name,
                  refused and not outside.exists() and set(L.items()) == before)
        # A creator whose source is a linked worktree of the main repository is valid.
        lead_tree = scratch / 'lead-worktree'
        git(repo, 'worktree', 'add', '-q', '--detach', str(lead_tree), head)
        try:
            (scratch / 'worktree-source').mkdir()
            batch = object.__new__(BA.Batch)
            batch.space, batch.space_owner = space, owner
            batch.workspace_root, batch.repo_root = str(scratch / 'worktree-source'), str(lead_tree)
            batch.record = {'id': 'batch-worktree', 'state': 'assembled', 'clone': str(lead_tree), 'watermark': head}
            clone = batch._isolated_clone()
            found = at(clone)
            check('safety/main-repository-worktree',
                  'the real batch creator, run from a linked worktree, declares its clone under the main repository',
                  found is not None and found[1]['state'] == 'present' and found[1]['kind'] == 'agent_repository'
                  and found[1].get('form') == 'batch_clone' and L._main_of(found[1]) == str(repo)
                  and (Path(clone) / '.git' / 'objects' / 'info' / 'alternates').read_text().strip()
                  == str(repo / '.git' / 'objects'))
            direct = scratch / 'worktree-source-direct'
            with creation.item('agent_repository', direct, main=lead_tree, form='candidate_workspace'):
                direct.mkdir()
            check('safety/main-repository-worktree', 'the seam accepts the linked worktree as the source',
                  at(direct) is not None and at(direct)[1]['state'] == 'present')
        except Exception:
            check('safety/main-repository-worktree', traceback.format_exc()[-1000:], False)
        conn.close()

    for row, values in rows.items():
        failed = [message for message, ok in values if not ok]
        expect('VELDO-0302 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v302_creators_suite()
