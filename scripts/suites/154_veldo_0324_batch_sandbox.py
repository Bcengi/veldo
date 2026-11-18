"""VELDO-0324: batch Signal and recorded launcher scratch, with real files and git.

Supplied ledger, real owner enrollment, fixture process table and empty engine.
The future batch lifecycle and act prerequisites are fixture stand-ins only.
The confined command is a stand-in at prepared_launch; launch and its locks run.
"""


def _v324_suite():
    import copy
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import traceback
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_batch_service.py': ROOT / ".veldo" / "control_batch_service.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_batch.py': ROOT / ".veldo" / "control_batch.py",
        'agent_sandbox.py': ROOT / "scripts" / "agent_sandbox.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
    }
    rows = {}

    def check(row, message, condition):
        rows.setdefault(row, []).append((message, bool(condition)))

    def drive(row, operation):
        try:
            operation(row)
        except Exception:
            check(row, traceback.format_exc()[-1800:], False)

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v324_' + name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='v324-') as temporary:
        base = Path(temporary).resolve()
        installed = base / 'installed'
        mods = installed / '.veldo'
        mods.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        (installed / 'scripts').mkdir()
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, (installed / 'scripts' if name == 'agent_sandbox.py' else mods) / name)
        BA, CL, SP, S, CFG, YAML, K, P, RM, KP, SG, GP, CM = [load(name, mods / (name + '.py')) for name in (
            'control_batch', 'control_clone', 'control_space', 'control_store', 'control_space_config',
            'yamlish', 'control_space_kinds', 'control_space_probe', 'control_space_remove',
            'control_space_keep', 'control_space_signal', 'git_process', 'control_membership')]
        BS = load('batch_service', mods / 'control_batch_service.py')
        SB = load('sandbox', installed / 'scripts/agent_sandbox.py')
        repo, state, scratch, proc, borrows = [base / name for name in ('main', 'state', 'scratch', 'proc', 'borrows')]
        for path in (repo, state, scratch, proc, borrows):
            path.mkdir()

        def git(where, *args):
            return GP.run(['git', '-C', str(where), *args], capture_output=True, text=True,
                          identity=('Fixture', 'fixture@example.invalid'), check=True).stdout.strip()

        git(repo, 'init', '-q', '-b', 'main')
        (repo / 'work.txt').write_text('committed work\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-q', '-m', 'base')
        head = git(repo, 'rev-parse', 'HEAD')
        (repo / '.veldo').mkdir()
        installation = base / 'installation'
        installation.mkdir()
        (installation / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture', 'role_id': 'owner'},
            'space': {'enabled': 'true', 'time_zone': 'UTC',
                      'pools': {'host': {'floor': 0, 'needs': {'build': 0, 'review': 0, 'gate': 0}}},
                      'engines': ['fixture'], 'scratch_roots': {'roots': [str(scratch)],
                          'session_pattern': 'sessions/{working_folder}/{session_id}'},
                      'build_roots': [], 'plain_repositories': [], 'client_accounts': [],
                      'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [],
                                  'networks': [], 'compose_projects': []}}}))
        config = CFG.read(environ={'VELDO_INSTALLATION': str(installation)}, stream=io.StringIO())
        project = dict(CFG.read_project(str(repo), YAML.read, config=config, stream=io.StringIO()), repository=str(repo))
        conn = S.open_store(str(state / 'control.sqlite3'))
        registry = copy.deepcopy(K.REGISTRY)
        table = registry['tables'][registry['version']]
        table['rows']['agent_repository']['run_finished'] = {'action': 'remove', 'after': ['worktree']}
        table['ends_on']['agent_repository'] = ['run_finished'] + list(table['ends_on']['agent_repository'])
        kinds = types.SimpleNamespace(due=lambda event, items, queued=None, look=None:
            K.due(event, items, queued=queued, look=look, registry=registry))
        L = SP.Ledger(S, conn, 'authority', lambda data: 'stub:' + S.digest_of(data.decode()),
                      config=config, projects=[project], state_root=str(state),
                      lifecycle={'version': registry['version'], **{key: table[key] for key in ('events', 'ends_on')}},
                      host='fixture', device=lambda path: 'device')
        assert L.set_pool('host', 'filesystem', device='device')['ok']
        owner = {'scope': {'type': 'project', 'id': project['project']}, 'ticket': 'VELDO-9324',
                 'run': {'id': 'run-324', 'station': 'build'}, 'lane': 'lane-324'}
        AC = CM.AC
        key = state / 'owner-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        public = key.with_suffix('.pub').read_text().strip()

        def sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=data, capture_output=True, check=True).stdout.decode()

        CM.attach(S)
        command = {'command_id': 'enroll-fixture-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public,
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        ids = {'domain_uuid': 'fixture-domain', 'repository_uuid': 'fixture-repository', 'store_uuid': 'fixture-store'}
        authority = CM.authority_state(S, conn)
        now = time.time()
        envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='enroll-owner', expires_at=now + 600,
                        membership_version=authority['membership_version'], delegation_version=authority['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        CM.admit(S, conn, envelope, command, sign(AC.canonical_envelope_bytes(envelope)), ids, now,
                 enrollee_signature=None, journal_signer=('authority', lambda data: 'stub:' + S.digest_of(data.decode())))
        mode = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': owner['scope'], 'mode': 'act'},
                'command_id': 'mode-324', 'nonce': 'mode-324'}
        blocked = L.set_mode({'command': mode, 'signature': sign(S.canonical_bytes(mode))}, CM, now)
        check('safety/act-unbuilt', 'the real prerequisite check refuses act', not blocked['ok'] and not L.acts(owner['scope']))
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        assert L.set_mode({'command': mode, 'signature': sign(S.canonical_bytes(mode))}, CM, now)['ok']

        def client(argv, cwd=None):
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if argv[3:5] == ['container', 'ls']:
                return 0, ''
            return 1, 'fixture engine has no objects'

        space = {'ledger': L, 'probe': P, 'kinds': kinds, 'remover': RM,
                 'free': lambda pool: shutil.disk_usage(base).free,
                 'keep': lambda identity, record: KP.keep(L, identity, record),
                 'owner_live': lambda owner: {'conclusive': True, 'group_empty': True},
                 'run': client, 'proc': str(proc), 'borrow_root': str(borrows)}

        def at(path):
            return next(((identity, record) for identity, record in L.items().items()
                         if record['locator'].get('path') == str(path)), (None, {}))

        def declare(kind, path, parent=None):
            creation = CL.SpaceCreator(space, owner)
            with creation.item(kind, path, parent=parent):
                path.mkdir()
            return at(path)[0]

        def finish(paths):
            return CL.space_signal(space, 'run_finished', paths, 'suite.run_finished')

        def batch(name):
            parent = scratch / name
            parent.mkdir()
            b = object.__new__(BA.Batch)
            b.space, b.space_owner, b.repo_root, b.workspace_root = space, owner, str(repo), str(parent)
            b.record = {'id': 'batch-' + name}
            b.records, b.events, b.project = state / 'batch-records', [], project['project']
            b.clock, b.observe = time.time, lambda event: None
            path = b._isolated_clone()
            git(path, 'checkout', '-q', '-b', 'main', head)
            observation = parent / 'observation'
            declare('scratch', observation)
            (observation / 'output').write_text('rebuildable output')
            b.record['observation_dir'] = str(observation)
            return b, path, observation

        def kept(identity):
            record = L.item(identity)['kept']
            return record and all(git(repo, 'rev-parse', ref) == commit for ref, commit in record['refs'].items())

        def clean(row):
            b, path, observation = batch('clean')
            identity = at(path)[0]
            b.discard()
            check(row, 'both outcomes removed and commits verified in the main repository',
                  not path.exists() and not observation.exists() and L.item(identity)['state'] == 'removed' and kept(identity)
                  and not b.record['space_deferred'] and L.item(identity)['removal']['emitter'] == 'batch.discard')
        drive('ac1/clean', clean)

        def holder(row):
            b, path, observation = batch('holder')
            process = subprocess.Popen([sys.executable, '-c',
                'import sys; f=open(sys.argv[1]); print("ready", flush=True); sys.stdin.read()', str(path / 'work.txt')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            entry = proc / str(process.pid)
            entry.symlink_to(Path('/proc') / str(process.pid), target_is_directory=True)
            try:
                assert process.stdout.readline().strip() == 'ready'
                b.discard()
                check(row, 'an open file holds the clone and names in_use on both records',
                      (path / 'work.txt').is_file() and (path / 'work.txt').read_text() == 'committed work\n'
                      and at(path)[1]['state'] == 'deferred' and at(path)[1]['deferral']['rule'] == 'in_use'
                      and b.record['space_deferred'][str(path)] == 'space_deferred:in_use')
            finally:
                process.communicate(timeout=10)
                entry.unlink()
        drive('ac1/open-file', holder)

        def failed_keep(row):
            b, path, observation = batch('failed-keep')
            b.space = dict(space, keep=lambda *args: {'ok': False, 'reason': 'fixture save failed'})
            b.discard()
            check(row, 'a failed save refuses removal and leaves committed bytes',
                  (path / 'work.txt').is_file() and (path / 'work.txt').read_text() == 'committed work\n'
                  and at(path)[1]['deferral']['rule'] == 'keep_failed')
        drive('safety/keep-failure', failed_keep)

        def dirty(row):
            b, path, observation = batch('dirty')
            (path / '.git/info').mkdir(exist_ok=True)
            (path / '.git/info/exclude').write_text('local.secret\n')
            (path / 'local.secret').write_text('ignored only-copy work')
            (path / 'notes').write_text('untracked only-copy work')
            b.discard()
            check(row, 'unsaved batch files remain byte for byte',
                  (path / 'local.secret').is_file() and (path / 'local.secret').read_text() == 'ignored only-copy work'
                  and (path / 'notes').read_text() == 'untracked only-copy work'
                  and at(path)[1]['state'] == 'deferred')
        drive('safety/unsaved-batch', dirty)

        KEEP = load('owner_keep', ROOT / 'scripts' / 'suites' / 'support' / 'space_owner_keep.py')
        keep_desk = KEEP.Desk(mods, S, CM, AC, conn, ids, lambda data: 'stub:' + S.digest_of(data.decode()),
                              sign, state, now, tag='v324_desk')

        def owner_keep(path):
            # The owner's Keep is the signed space_disposition command and nothing else (VELDO-0318).
            # The batch clone has a request of its own (VELDO-0347 AC3): it is kept through that
            # request, the owner's settled answer and the owner's packet. The Ledger raises no
            # request for a scratch folder, so the sandbox scratch's settled request is planted, and
            # the signature, the membership check and the transition are the Ledger's.
            identity = at(path)[0]
            assert L.signal('run_finished', CL.space_named(L, 'run_finished', [str(path)]))['ok']
            claimed = L.outcome(identity, 'kept', {'owner_keep': {'at': time.time()}}, principal='owner')
            assert not claimed['ok'] and claimed.get('reason') == 'not_authorized', claimed
            assert not L.item(identity).get('owner_keep') and L.item(identity)['state'] == 'due'
            record = L.item(identity)
            if record['kind'] == 'agent_repository' and L._clone_row(record):
                asked = KEEP.reserve(L, RM, identity, probe=P)
                assert asked['ok'], asked
                settled, edge_alone, marked = keep_desk.owner_keeps(L, identity, SP.ITEM_KIND)
                assert settled.get('outcome') == 'settled' and not edge_alone['ok'], (settled, edge_alone)
            else:
                assert record['kind'] == 'scratch', record['kind']
                marked = KEEP.keep_planted(L, S, CM, conn, SP.ITEM_KIND, identity, sign, now)
            assert marked['ok'], marked
            return copy.deepcopy(L.item(identity))

        def kept_batch(row):
            b, path, observation = batch('owner-kept')
            (path / 'notes').write_text('the owner keeps this')
            before = owner_keep(path)
            sibling = scratch / 'other-run'
            declare('scratch', sibling)
            b.discard()
            check(row, 'owner Keep and another item of the same owner are not signalled',
                  (path / 'notes').is_file() and (path / 'notes').read_text() == 'the owner keeps this'
                  and at(path)[1] == before and before['owner_keep']['by'] == 'owner'
                  and at(sibling)[1]['state'] == 'present' and sibling.is_dir())
        drive('safety/owner-keep-batch', kept_batch)

        def evidence(row):
            b, path, observation = batch('evidence')
            evidence_path = observation.parent / 'gate-evidence'
            declare('evidence', evidence_path)
            (evidence_path / 'proof.txt').write_text('only copy of the gate proof')
            b.record['observation_dir'] = str(evidence_path)
            b.discard()
            check(row, 'real observation classification is evidence and its proof stays',
                  (evidence_path / 'proof.txt').read_text() == 'only copy of the gate proof'
                  and at(evidence_path)[1]['kind'] == 'evidence' and at(evidence_path)[1]['state'] == 'kept')
        drive('ac1/evidence', evidence)

        # A batch without its ledger (VELDO-0304's decision, upheld at assembly): the clone goes through
        # the removers' standalone entry after the look and the keep step. Its unique commits are kept
        # in the main repository first; a missing ledger is no refusal. A deferral only when the keep
        # step cannot keep (an untracked only copy here) or the clone is in use. The observation folder
        # is evidence: it stays, named kept.
        def no_ledger(row):
            b, path, observation = batch('no-ledger')
            (path / 'unique').write_text('only in the clone')
            git(path, 'add', 'unique')
            git(path, 'commit', '-q', '-m', 'unique work')
            unique = git(path, 'rev-parse', 'HEAD')
            b.space = None
            b.discard()
            entry = b.record['space_outcomes'].get(str(path), {})
            reachable = [ref for ref in entry.get('refs') or {}
                         if subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', unique, ref],
                                           capture_output=True).returncode == 0]
            check(row, 'a batch without its ledger keeps the clone\'s unique work in main, then removes the clone: '
                  + str((entry, b.record['space_deferred'])),
                  not path.exists() and entry.get('state') == 'removed' and bool(reachable)
                  and observation.is_dir() and (observation / 'output').read_text() == 'rebuildable output'
                  and b.record['space_deferred'] == {str(observation): 'space_deferred:kept'})
            b, path, observation = batch('no-ledger-unsaved')
            (path / 'notes').write_text('untracked only-copy work')
            b.space = None
            b.discard()
            check(row, 'what the keep step cannot keep defers the clone, byte for byte: '
                  + str(b.record['space_deferred']),
                  (path / 'notes').read_text() == 'untracked only-copy work'
                  and b.record['space_deferred'].get(str(path), 'space_deferred:removed') not in
                  ('space_deferred:removed', 'space_deferred:gone'))
        drive('safety/batch-no-ledger', no_ledger)

        def saved_deferral(row):
            b, path, observation = batch('saved-deferral')
            b.space = None
            b._write()
            events = []
            b.observe = events.append
            b.discard()
            saved = json.loads((b.records / (b.record['id'] + '.json')).read_text())
            expected = {str(observation): 'space_deferred:kept'}
            check(row, 'the saved batch retains the no-ledger outcomes and an emitted discard outcome',
                  saved.get('space_deferred') == expected and saved.get('space_outcomes') == b.record['space_outcomes']
                  and any(e['operation'] == 'discard' and e['outcome'] == 'deferred'
                          and e.get('space_deferred') == expected for e in saved.get('log', []))
                  and len(events) == 1 and events[0]['operation'] == 'discard'
                  and saved['space_outcomes'][str(path)]['state'] == 'removed' and not path.exists()
                  and observation.is_dir())
        drive('ac1/saved-deferral', saved_deferral)

        def reassembly(row):
            b, path, observation = batch('reassembly')
            b.space = None
            old_id = b.record['id']
            b.authority = object.__new__(BA.Authority)
            b.trunk, b.destination, b.follows, b.hook = 'main', BA.LAND_LOCALLY, old_id, None
            b.assemble([])
            b.discard()
            saved = json.loads((b.records / (b.record['id'] + '.json')).read_text())
            previous = json.loads((b.records / (old_id + '.json')).read_text())
            expected = {str(observation): 'space_deferred:kept'}
            check(row, 'reassembly and a later discard retain earlier outcomes on both saved records',
                  saved.get('space_deferred') == previous.get('space_deferred') == expected
                  and saved.get('space_outcomes') == previous.get('space_outcomes')
                  and saved['space_outcomes'][str(path)]['state'] == 'removed' and not path.exists())
        drive('ac1/saved-reassembly', reassembly)

        # Gate, approval and landing decisions are stand-ins; discard, request writes
        # and the SQLite readback are the real production path for every terminal arm.
        for terminal in ('landed', 'stopped', 'refused', 'reland-failed', 'red', 'not-started'):
            def saved_request(row, terminal=terminal):
                b, path, observation = batch('request-' + terminal)
                b.space = None
                b.record['state'] = 'red' if terminal == 'reland-failed' else terminal
                def land():
                    if terminal == 'refused':
                        raise BS.BT.Refused('unavailable_service:fixture')
                    return {'ok': terminal == 'landed',
                            'outcome': 'trunk_moved' if terminal == 'reland-failed' else terminal,
                            'refusal': BS.BT.STOPPED if terminal == 'stopped' else None}
                b.land, b.reland = land, lambda: {'ok': False}
                line = object.__new__(BS.BatchLine)
                line.store, line.conn, line.signer = S, conn, 'authority'
                line.sign, line.generation, line.clock = L.sign, 1, time.time
                line.repository, line.held = str(repo), {}
                requested = terminal in ('red', 'not-started')
                rid = 'request-' + terminal
                request = {'project': project['project'], 'repository': str(repo),
                           'state': BS.REQUESTED if requested else BS.AWAITING}
                BS._upsert(S, conn, line.signer, line.sign, 1, rid, BS.REQUEST_KIND, request)
                if not requested:
                    line.held[rid] = b
                line._batch = lambda request: b
                with patch.object(BS.BT, 'run', lambda *a: {'outcome': terminal.replace('-', '_')}):
                    line.pass_once()
                saved = BS._row(conn, rid)['data']
                expected = {str(observation): 'space_deferred:kept'}
                check(row, 'saved request includes the discard outcomes: the clone removed after the keep '
                           'step, the evidence kept',
                      saved.get('space_deferred') == expected and bool(saved.get('space_outcomes'))
                      and saved['space_outcomes'][str(path)]['state'] == 'removed' and not path.exists()
                      and observation.is_dir())
                # Keep this still-requested fixture out of the next independent pass.
                line.held.clear()
                if saved['state'] == BS.REQUESTED:
                    BS._upsert(S, conn, line.signer, line.sign, 1, rid, BS.REQUEST_KIND, dict(saved, state='fixture-done'))
            drive('ac1/saved-request-' + terminal, saved_request)

        def observation_end(row):
            b, path, _ = batch('observation-end')
            b.record.update(state='assembled', watermark=head)
            b.installation, b.gate_runs, b.gate_timeout = str(installed), 0, None
            b.tell = lambda *args: None
            cv = BA._organ('control_verification')
            def refused_gate(*args, **kwargs):
                raise cv.Refused('fixture_gate')
            with patch.object(cv, 'observe_gate', refused_gate):
                b.gate()
            evidence = Path(b.record['observation_dir'])
            (evidence / 'proof').write_text('reviewer evidence')
            identity, record = at(evidence)
            b.discard()
            events = record.get('ends_on', {}).get('events') or []
            check(row, 'the actual gate observation is evidence and survives batch end',
                  record['kind'] == 'evidence' and L.item(identity)['state'] == 'kept'
                  and (evidence / 'proof').read_text() == 'reviewer evidence')
            check(row, 'its end list is the evidence kind default: the verdict, the ticket end and the project end',
                  events == list(table['ends_on']['evidence'])
                  and all(event in events for event in ('verdict_recorded', 'ticket_ended', 'project_ended')))
        drive('ac1/observation-end', observation_end)

        def no_end_option(row):
            path = scratch / 'chosen-end'
            try:
                result = L.declare('evidence', {'path': str(path)}, owner, 'seam', ends_on=['verdict_recorded'])
                refused = not result['ok']
            except TypeError:
                refused = True
            check(row, 'declare takes no end list from its caller and makes no item for one',
                  refused and at(path)[0] is None and not path.exists()
                  and 'ends_on' not in SP.COMMAND_PARAMETERS[SP.DECLARE])
        drive('safety/no-end-option', no_end_option)

        def bad_paths(row):
            b, path, observation = batch('bad-paths')
            (path / 'notes').write_text('work behind a refused locator')
            link = path.parent / 'link'
            link.symlink_to(path)
            for locator in (str(link), str(path.parent / 'unused' / '..' / path.name)):
                b.record['clone'] = locator
                before = copy.deepcopy(L.items())
                b.discard()
                check(row, 'a link or parent segment signals no item and preserves planted work',
                      (path / 'notes').read_text() == 'work behind a refused locator'
                      and L.items() == before and bool(b.record['space_deferred']))
        drive('safety/batch-locators', bad_paths)

        def launch(name, prepared=None, recorded=True, wiring=space, installation_present=True):
            root = scratch / name
            if recorded:
                parent_item = declare('scratch', root)
            else:
                root.mkdir()
                parent_item = None
            seen = []
            def command(*args):
                path = args[4]
                seen.append(path)
                if prepared:
                    prepared(path)
                return 7
            env = {'VELDO_SPACE_LABEL': owner['run']['id'] if recorded else '', 'TMPDIR': str(root),
                   'XDG_STATE_HOME': str(state),
                   'VELDO_INSTALLATION': str(installation if installation_present else base / 'absent-installation')}
            with patch.dict(os.environ, env), patch.object(SB, 'prepared_launch', command), \
                    patch.object(SB.tempfile, 'gettempdir', lambda: str(root)):
                code = SB.launch(base / 'unused-config', repo, ['fixture-command'], space=wiring)
            return code, root, parent_item, seen

        def recorded(row):
            observed = []
            original = L.declare
            def declaration(kind, locator, *args, **kwargs):
                if Path(locator['path']).name.startswith(SB.SCRATCH_PREFIX):
                    observed.append(not Path(locator['path']).exists())
                return original(kind, locator, *args, **kwargs)
            def prepare(path):
                # Shut against writing, and listable: the reader sees all of it, and the remover has
                # to open each folder to empty it. A folder nobody can list is the next row
                # (VELDO-0347 AC2 holds such a scratch as unread; before it this row shut both
                # folders with mode 0).
                (path / 'shut/inner').mkdir(parents=True)
                (path / 'shut/inner/output').write_text('disposable scratch')
                (path / 'shut/inner').chmod(0o500)
                (path / 'shut').chmod(0o500)
            with patch.object(L, 'declare', declaration):
                code, root, parent_item, seen = launch('recorded', prepare)
            path = seen[0]
            identity, record = at(path)
            check(row, 'declared before creation; parent and complete owner; no launcher delete',
                  code == 7 and observed == [True] and path.is_dir() and record.get('state') == 'present'
                  and record.get('parent') == parent_item and record.get('owner') == owner)
            finish([root])
            check(row, 'run finished removes child and root, including shut directories',
                  not root.exists() and L.item(identity)['state'] == 'removed' and L.item(parent_item)['state'] == 'removed')
        drive('ac2/recorded', recorded)

        def unlistable(row):
            # VELDO-0347 AC2: a folder beneath the scratch that cannot be listed holds the item as
            # unread. Nothing is removed, the run's end says why, and what is in it is whole.
            def prepare(path):
                (path / 'shut/inner').mkdir(parents=True)
                (path / 'shut/inner/output').write_text('nobody read this')
                (path / 'shut/inner').chmod(0)
                (path / 'shut').chmod(0)
            code, root, parent_item, seen = launch('unlistable', prepare)
            path = seen[0]
            identity = at(path)[0]
            try:
                finish([root])
                held, parent = L.item(identity), L.item(parent_item)
                check(row, 'a scratch the reader cannot list is held as unread, with its parent [%s %s %s]'
                      % (held['state'], (held.get('deferral') or {}).get('found', {}).get('states'), parent['state']),
                      code == 7 and held['state'] == 'deferred' and parent['state'] == 'deferred'
                      and held['deferral'].get('refused_by') == 'children'
                      and (held['deferral'].get('found') or {}).get('states') == {'path:' + str(path): 'unread'}
                      and path.is_dir() and root.is_dir())
            finally:
                (path / 'shut').chmod(0o700)
                (path / 'shut/inner').chmod(0o700)
            check(row, 'the folder is as it was, and what is in it is whole',
                  sorted(str(one.relative_to(path)) for one in path.rglob('*')) == ['shut', 'shut/inner', 'shut/inner/output']
                  and (path / 'shut/inner/output').read_text() == 'nobody read this')
        drive('ac2/unlistable-held', unlistable)

        def lock_and_login(row):
            attempts = []
            def prepare(path):
                (path / 'marker').write_text('held scratch')
                finish([path])
                attempts.append(at(path)[1])
            code, root, parent_item, seen = launch('held-lock', prepare)
            path = seen[0]
            check(row, 'the launcher lock defers its scratch as in_use',
                  attempts[0]['state'] == 'deferred' and attempts[0]['deferral']['rule'] == 'in_use' and path.exists())
            journal = borrows / path.name
            journal.mkdir()
            (journal / 'borrow.json').write_text('{}')
            finish([path])
            check(row, 'an unsettled borrowed login defers and keeps its only bytes',
                  at(path)[1]['deferral']['rule'] == 'in_use' and (path / 'marker').read_text() == 'held scratch')
            (journal / 'recovery.json').write_text('{}')
            finish([root])
            check(row, 'settlement allows the ending event', not root.exists())
        drive('ac2/lock-and-login', lock_and_login)

        def failed_launch(row):
            observed = []
            def prepare(path):
                (path / 'partial').write_text('failed run scratch')
                observed.append(path)
                raise ValueError('fixture launch failure')
            try:
                launch('failed-launch', prepare)
                raised = False
            except ValueError:
                raised = True
            path = observed[0]
            check(row, 'a failed recorded launch leaves its scratch present and unlocked',
                  raised and (path / 'partial').read_text() == 'failed run scratch'
                  and at(path)[1]['state'] == 'present' and not P.scratch(path, borrows)['lock_held'])
            finish([path.parent])
            check(row, 'the run event removes failed-launch scratch through its item', not path.exists())
        drive('ac2/failed-launch', failed_launch)

        def sandbox_work(row):
            code, root, parent_item, seen = launch('nested-work')
            path = seen[0]
            nested = path / 'repository'
            nested.mkdir()
            git(nested, 'init', '-q', '-b', 'main')
            (nested / 'notes').write_text('only committed copy')
            git(nested, 'add', '.')
            git(nested, 'commit', '-q', '-m', 'work')
            tip = git(nested, 'rev-parse', 'HEAD')
            finish([root])
            check(row, 'a repository beneath launcher scratch holds the scratch and its parent',
                  nested.is_dir() and git(nested, 'rev-parse', 'HEAD') == tip
                  and at(path)[1]['state'] == 'deferred' and root.exists())
        drive('safety/sandbox-repository', sandbox_work)

        def kept_sandbox(row):
            code, root, parent_item, seen = launch('kept-sandbox')
            path = seen[0]
            (path / 'notes').write_text('owner kept scratch work')
            before = owner_keep(path)
            finish([root])
            check(row, 'owner Keep holds its scratch root with bytes and identity unchanged',
                  (path / 'notes').is_file() and (path / 'notes').read_text() == 'owner kept scratch work'
                  and at(path)[1] == before and root.exists())
        drive('safety/owner-keep-sandbox', kept_sandbox)

        for installed_case in (False, True):
            def stale(row, installed_case=installed_case):
                root = scratch / ('stale-' + str(installed_case))
                root.mkdir()
                old = root / 'veldo-agent-two-days-old'
                old.mkdir()
                (old / 'work').write_text('old is no permission to delete')
                before = time.time() - 2 * 24 * 60 * 60
                os.utime(old, (before, before))
                env = {'VELDO_SPACE_LABEL': '', 'TMPDIR': str(root), 'XDG_STATE_HOME': str(state),
                       'VELDO_INSTALLATION': str(installation if installed_case else base / 'absent')}
                with patch.dict(os.environ, env), patch.object(SB, 'prepared_launch', lambda *args: 0), \
                        patch.object(SB.tempfile, 'gettempdir', lambda: str(root)):
                    SB.launch(base / 'unused', repo, ['fixture-command'])
                check(row, 'two fixture days old, lock free, still byte equal after another start',
                      old.is_dir() and (old / 'work').read_text() == 'old is no permission to delete')
            drive('ac3/' + ('installation' if installed_case else 'no-installation'), stale)

        def standalone(row):
            code, root, parent_item, seen = launch('standalone', recorded=False, wiring=None, installation_present=False)
            check(row, 'adopter starts and returns its status, removing only its own scratch',
                  code == 7 and len(seen) == 1 and not seen[0].exists() and not list(root.iterdir()))
        drive('ac4/standalone', standalone)

        def foreign_parent(row):
            root = scratch / 'foreign-run-root'
            foreign_owner = dict(owner, run={'id': 'another-run', 'station': 'build'})
            with CL.SpaceCreator(space, foreign_owner).item('scratch', root):
                root.mkdir()
            (root / 'work').write_text('another run owns this')
            before, ran = copy.deepcopy(L.items()), []
            env = {'VELDO_SPACE_LABEL': owner['run']['id'], 'TMPDIR': str(root), 'XDG_STATE_HOME': str(state)}
            with patch.dict(os.environ, env), patch.object(SB, 'prepared_launch', lambda *a: ran.append(True)):
                try:
                    SB.launch(base / 'unused', repo, ['fixture-command'], space=space)
                    failed = False
                except RuntimeError as error:
                    failed = 'unavailable_service:space_ledger' in str(error)
            check(row, 'another run scratch root refuses before creation, declaration or command',
                  failed and not ran and L.items() == before and list(root.iterdir()) == [root / 'work']
                  and (root / 'work').read_text() == 'another run owns this')
        drive('safety/foreign-run-parent', foreign_parent)

        def refused(row):
            root = scratch / 'unavailable'
            declare('scratch', root)
            env = {'VELDO_SPACE_LABEL': owner['run']['id'], 'TMPDIR': str(root)}
            for wiring in (None, {}, {'ledger': types.SimpleNamespace(items=lambda: {})}):
                ran = []
                with patch.dict(os.environ, env), patch.object(SB, 'prepared_launch', lambda *a: ran.append(True)):
                    try:
                        SB.launch(base / 'unused', repo, ['fixture-command'], space=wiring)
                        failed = False
                    except Exception as error:
                        failed = 'unavailable_service:space_ledger' in str(error)
                check(row, 'recorded label with no usable ledger refuses before creation or run', failed and not ran and not list(root.iterdir()))
            linked = scratch / 'linked-root'
            linked.symlink_to(root)
            for name in (str(linked), str(root / '..' / root.name)):
                with patch.dict(os.environ, dict(env, TMPDIR=name)):
                    try:
                        SB.scratch_creation(space, os.environ)
                        failed = False
                    except RuntimeError:
                        failed = True
                check(row, 'parent segments and links refuse', failed)
        drive('safety/recorded-refusal', refused)
        conn.close()

    for row, checks in rows.items():
        failed = [message for message, passed in checks if not passed]
        expect('VELDO-0324 ' + row + ': ' + ('; '.join(failed) if failed else '%d checks' % len(checks)), not failed)


_v324_suite()
