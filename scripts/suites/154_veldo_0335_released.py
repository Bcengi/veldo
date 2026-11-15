"""VELDO-0335: real journal, signed packets, worker processes, git, keeper and removers.

Only ROOT and expect are shared. The fixture supplies declarations, membership records,
act eligibility, free bytes, and a private process table. No Docker engine is contacted.
The service wiring is explicit, as in suite 149. Every filesystem change is in this suite's
temporary tree. Mutation runs replace the named production files before any organ loads.
"""


def _v335_suite():
    import importlib.util
    import importlib.machinery
    import io
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import socket
    import subprocess
    import tempfile
    import threading
    import time
    import uuid

    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_consumer.py': ROOT / ".veldo" / "control_space_consumer.py",
        'control_space_worker.py': ROOT / ".veldo" / "control_space_worker.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
    }
    CLI_PATH = ROOT / "bin" / "veldo"
    rows = {}

    def check(name, condition, detail=''):
        rows.setdefault(name, []).append(bool(condition))
        if not condition:
            print('VELDO-0335 detail %s: %s' % (name, detail))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0335-') as directory:
        base = Path(directory).resolve()
        mods = base / '.veldo'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        SVC = load('v335_service', mods / 'control_service.py')
        C = SVC.SPACE_CONSUMER
        W, S, CM = C.WORKER, SVC.S, SVC.CM
        SP, P, K, RM, KP, spool = W.SP, W.PROBE, W.KINDS, W.REMOVE, W.KEEP, W.SPOOL
        GP = load('v335_git', mods / 'git_process.py')
        state, scratch, trees, proc = [base / name for name in ('state', 'scratch', 'trees', 'proc')]
        for path in (state, scratch, trees, proc):
            path.mkdir()
        repo = base / 'repository'
        repo.mkdir()

        def git(where, *args):
            done = GP.run(['git', '-C', str(where), *args], capture_output=True, text=True,
                          identity=('Fixture', 'fixture@example.invalid'), timeout=30)
            if done.returncode:
                raise RuntimeError(done.stderr)
            return done.stdout.strip()

        git(repo, 'init', '-q', '-b', 'main')
        (repo / '.gitignore').write_text('build/\n')
        (repo / 'source').write_text('first\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-q', '-m', 'first')
        first = git(repo, 'rev-parse', 'HEAD')
        (repo / 'source').write_text('second\n')
        git(repo, 'add', 'source')
        git(repo, 'commit', '-q', '-m', 'second')
        tip = git(repo, 'rev-parse', 'HEAD')
        git(repo, 'branch', 'landing', tip)
        key = base / 'owner-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True, timeout=20)

        def sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-command'],
                                  input=data, capture_output=True, check=True, timeout=20).stdout.decode()

        conn = S.open_store(str(state / 'store.sqlite3'))
        journal_sign = lambda data: 'fixture:' + S.digest_of(data.decode())
        for who, typ, roles in [('owner', 'person', ['project_owner']), (SP.OBSERVER, 'service', [])]:
            for identity, kind, data in [
                (who, 'membership', dict(principal_type=typ, roles=roles, scope='*',
                                         revoked_at=None, expires_at=None)),
                ('key:' + who, 'verification_key', dict(principal=who, public_key=Path(str(key) + '.pub').read_text(),
                                                       effective_at=0))]:
                cid = uuid.uuid4().hex
                S.execute(conn, dict(command_id=cid, principal='authority', operation='upsert_entity',
                    nonce=cid, artifact_digests=[], expected_versions={identity: 0},
                    parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', journal_sign, 1)
        scope = {'type': 'project', 'id': 'orchard'}
        project = dict(project='orchard', repository=str(repo), worktree_root=str(trees),
                       landing_refs=['landing'], protect=[], build_output=['build/'])
        config = dict(present=True, enabled=True, engines=[], scratch_roots={'roots': [str(scratch)]},
                      build_roots=[], plain_repositories=[], protect=[], pools={'disk': {'floor': 0}})
        ledger = SP.Ledger(S, conn, 'authority', journal_sign, config=config, state_root=str(state),
                           projects=[project], lifecycle=K.LIFECYCLE, host='fixture', device=lambda path: 'disk')
        ledger.set_pool('disk', 'filesystem', device='disk')
        check('safety/act-unbuilt', not ledger.acts(scope) and ledger._act_refusal(scope) is not None)
        # Act eligibility is the later tickets' fixture. The real ledger still refuses the switch.
        ledger.acts = lambda scope: True
        observations = []
        service = object.__new__(SVC.Service)
        service.config = {'space_landing': {'orchard': {'trunk': 'main'}}}
        service.conn, service.loop, service.api = conn, None, None
        service.space_seen, service.projects_due = None, False
        service._log = observations.append
        service.space = {'ledger': ledger, 'proc': str(proc), 'free': lambda pool: 1000000000}

        def drain(timeout=30, allow_failure=False):
            until = time.monotonic() + timeout
            while service.space_pipes() and time.monotonic() < until:
                for descriptor in select.select(list(service.space_pipes()), [], [], 0.1)[0]:
                    service.space_readable(descriptor)
            if service.space_pipes():
                raise RuntimeError('worker did not finish')
            if not allow_failure and observations and observations[-1].get('ok') is False:
                raise RuntimeError('worker refused: %s' % observations[-1])

        def declare(kind, path, owner, **more):
            answer = ledger.declare(kind, {'path': str(path)}, owner, 'seam', **more)
            if not answer['ok']:
                raise RuntimeError(answer)
            ledger.confirm(answer['item'])
            return answer['item']

        def worktree(name, start=first):
            path = trees / name
            git(repo, 'worktree', 'add', '-q', '-b', name, str(path), tip)
            owner = {'scope': scope, 'ticket': name}
            identity = declare('worktree', path, owner, start=start, branch=name)
            branched = ledger.rebranch(identity, name, start)
            if not branched['ok']:
                raise RuntimeError(branched)
            return identity, path, branched['branch_item'], owner

        def event(kind='ref_changed', subject=None, wake=True):
            before = service.watermark()
            subject = subject or dict(repository=str(repo), ref='refs/heads/main', old=first, new=tip)
            answer = ledger.event(kind, subject, {'hook': 'reference-transaction' if kind == 'ref_changed'
                                                 else 'session', 'host': 'fixture'})
            if not answer['ok']:
                raise RuntimeError(answer)
            if wake:
                service.hint_after(before)
                drain()
            return answer['event']

        loader = importlib.machinery.SourceFileLoader('v335_cli', str(CLI_PATH))
        cli_spec = importlib.util.spec_from_loader('v335_cli', loader)
        cli = importlib.util.module_from_spec(cli_spec)
        cli_spec.loader.exec_module(cli)
        cli.ROOT = base
        packets = []

        class Signed:
            """The CLI's explicit transport seam, with real signatures and Ledger acceptance."""
            def __getattr__(self, name):
                return getattr(ledger, name)

            def apply(self, command):
                command = dict(command, nonce=uuid.uuid4().hex, issued_at=time.time())
                packet = dict(command=command, signature=sign(S.canonical_bytes(command)))
                packets.append(packet)
                return ledger.accept(packet, CM, time.time())

        wired = {'ledger': Signed()}

        def call(verb, args):
            out, err = io.StringIO(), io.StringIO()
            status = verb(args, space=wired, stdout=out, stderr=err)
            return status, json.loads(out.getvalue()) if out.getvalue() else {}, err.getvalue()

        def record(kind, path, ticket, parent=None):
            args = ['--kind', kind, '--path', str(path), '--ticket', ticket]
            if parent:
                args += ['--parent', parent]
            status, out, err = call(cli.space_record, args)
            if status:
                raise RuntimeError(err)
            return out['item']

        def confirm(identity):
            status, out, err = call(cli.space_record, ['--confirm', identity])
            if status:
                raise RuntimeError(err)

        def pair(name, unique=False):
            agent_path = trees / name
            inner_path = agent_path / 'inner'
            agent = record('agent_repository', agent_path, name)
            inner = record('worktree', inner_path, name, agent)
            git(trees, 'clone', '-q', str(repo), str(agent_path))
            git(agent_path, 'worktree', 'add', '-q', '-b', name, str(inner_path), tip)
            confirm(agent)
            confirm(inner)
            if unique:
                (inner_path / 'only-commit').write_text('unlanded work')
                git(inner_path, 'add', 'only-commit')
                git(inner_path, 'commit', '-q', '-m', 'unlanded')
            else:
                git(repo, 'branch', name, tip)
            return agent, agent_path, inner, inner_path

        def release_call(paths, force=False):
            args = ['--type', 'released']
            for path in paths:
                args += ['--path', str(path)]
            if force:
                args += ['--force']
            return call(cli.space_event, args)

        def release(paths, wake=True):
            before = service.watermark()
            status, out, err = release_call(paths)
            # The public call records one observation. Only the later journal wake may remove.
            check('ac1/returns-before-removal', status == 0 and all(path.exists() for path in paths)
                  and ledger.event_record(out['event'])['state'] == 'received')
            if status:
                return status, out, err
            if wake:
                service.hint_after(before)
                drain()
            return status, out, err

        agent, agent_path, inner, inner_path = pair('complete')
        (inner_path / 'lost-log').write_text('commit held only in the private log')
        git(inner_path, 'add', 'lost-log')
        git(inner_path, 'commit', '-q', '-m', 'log-only')
        log_tip = git(inner_path, 'rev-parse', 'HEAD')
        git(inner_path, 'reset', '-q', '--hard', tip)
        git(inner_path, 'reset', '-q', '--hard', tip)
        (agent_path / 'private-log').write_text('repository commit held only by its log')
        git(agent_path, 'add', 'private-log')
        git(agent_path, 'commit', '-q', '-m', 'private-log')
        agent_tip = git(agent_path, 'rev-parse', 'HEAD')
        git(agent_path, 'reset', '-q', '--hard', tip)
        git(agent_path, 'reset', '-q', '--hard', tip)
        status, out, err = release([agent_path, inner_path])
        result = ledger.event_record(out['event'])['result'] if out.get('event') else {}
        removed = [one['item'] for one in (result or {}).get('outcomes', []) if one['outcome'] == 'removed']
        check('ac1/released-pair', status == 0 and not agent_path.exists() and not inner_path.exists()
              and removed == [inner, agent], (status, err, result, ledger.item(inner), ledger.item(agent)))
        keep = ledger.item(inner).get('kept') or {}
        check('safety/kept-in-main', bool(keep.get('refs')) and keep.get('repository') == str(repo)
              and log_tip in git(repo, 'rev-list', *keep['refs']).splitlines(), keep)
        agent_keep = ledger.item(agent).get('kept') or {}
        check('safety/repository-kept', bool(agent_keep.get('refs')) and agent_keep.get('repository') == str(repo)
              and agent_tip in git(repo, 'rev-list', *agent_keep['refs']).splitlines(), agent_keep)
        emitter = (ledger.item(inner).get('removal') or {}).get('emitter') or {}
        check('ac1/owner-and-event', emitter.get('owners', {}).get(inner) == ledger.item(inner)['owner']
              and emitter.get('event_record') == out.get('event') and emitter.get('worker') != os.getpid())
        check('ac1/signed-observer', any(packet['command']['operation'] == SP.EVENT
              and packet['command']['principal'] == SP.OBSERVER for packet in packets))

        recorded = ledger.event_record(out['event']) if out.get('event') else {}
        check('cli/verb-emitter', recorded.get('emitter') == {'verb': 'event', 'host': ledger.host}, recorded)
        status, _, err = release_call([agent_path, inner_path])
        check('rv/twice', status == 1 and 'space_release_no_item:' in err, err)

        # A host observation must never stand in for the owner's Abandon.
        agent, agent_path, inner, inner_path = pair('abandon-refused')
        refusal = wired['ledger'].apply(dict(principal=SP.OBSERVER, operation=SP.SIGNAL,
            command_id=uuid.uuid4().hex, parameters=dict(event='worktree_abandoned',
                subject={'items': [{'item': inner, 'version': ledger._row(inner, SP.ITEM_KIND)[0]}]})))
        check('safety/host-abandon', refusal.get('reason') == 'space_not_permitted:space_abandon'
              and ledger.item(inner)['state'] == 'present' and inner_path.is_dir() and agent_path.is_dir())

        # All names are checked in the transaction: a bad member refuses the whole event.
        fleet, fleet_path, _, _ = worktree('fleet')
        status, _, err = release_call([inner_path, fleet_path])
        check('ac2/seam-refused', status == 1 and 'space_release_creator:' + fleet in err
              and ledger.item(fleet)['state'] == 'present' and ledger.item(inner)['state'] == 'present', err)
        status, _, err = release_call([trees / 'unrecorded'])
        check('ac2/no-item', status == 1 and 'space_release_no_item:' in err, err)
        for path in (str(inner_path / '..' / 'inner'), str(trees / 'linked')):
            if path.endswith('/linked'):
                os.symlink(inner_path, path)
            answer = ledger.event('released', {'paths': [path]}, {'hook': 'event', 'host': 'fixture'})
            check('safety/locators', not answer['ok'] and answer.get('reason') in
                  ('space_locator_parent', 'space_locator_link'), answer)
        for subject in ({}, {'paths': []}, {'paths': ['relative']}, {'paths': [None]},
                        {'paths': [str(inner_path)], 'force': True},
                        {'paths': [str(inner_path)], 'items': [fleet]}):
            answer = ledger.event('released', subject, {'hook': 'event', 'host': 'fixture'})
            check('safety/envelope', not answer['ok'], answer)
        packet = packets[-1]
        check('safety/signature-expiry', not ledger.accept(dict(packet, signature='forged'), CM, time.time())['ok'])
        check('safety/signature-expiry', ledger.accept(packet, CM,
              packet['command']['issued_at'] + SP.PACKET_AGE + 1).get('reason') == 'space_packet_expired')

        agent, agent_path, inner, inner_path = pair('unique', unique=True)
        unlanded = git(inner_path, 'rev-parse', 'HEAD')
        for attempt in range(2):
            status, out, err = release([agent_path, inner_path])
            held = ledger.item(inner)
            check('ac3/unique', status == 0
                  and held['state'] == 'deferred' and held['deferral']['rule'] == 'unique_work'
                  and agent_path.is_dir() and inner_path.is_dir()
                  and git(inner_path, 'rev-parse', 'HEAD') == unlanded
                  and (inner_path / 'only-commit').read_text() == 'unlanded work', (err, held))
            before, sent = ledger.events(), len(packets)
            status, out, err = release_call([agent_path, inner_path], force=True)
            check('cli/force-refused', status == 1 and 'invalid_input:force' in err
                  and ledger.events() == before and len(packets) == sent, (status, err))
            check('ac3/unique-force', status == 1 and 'invalid_input:force' in err
                  and ledger.item(inner)['state'] == 'deferred'
                  and agent_path.is_dir() and inner_path.is_dir()
                  and git(inner_path, 'rev-parse', 'HEAD') == unlanded
                  and (inner_path / 'only-commit').read_text() == 'unlanded work', err)

        # R1: the unreleased child holds its repository, including its unlanded commit.
        agent, agent_path, inner, inner_path = pair('repository-only', unique=True)
        unlanded = git(inner_path, 'rev-parse', 'HEAD')
        status, _, err = release([agent_path])
        held = ledger.item(agent)
        check('rv/repository-held-by-worktree', status == 0 and held['state'] == 'deferred'
              and inner in held.get('deferral', {}).get('held_by', [])
              and ledger.item(inner)['state'] == 'present' and inner_path.is_dir()
              and git(inner_path, 'rev-parse', 'HEAD') == unlanded
              and (inner_path / 'only-commit').read_text() == 'unlanded work', held)

        # R2: the repository has a private branch with no worktree on it.
        agent, agent_path, inner, inner_path = pair('private-side')
        git(agent_path, 'checkout', '-q', '-b', 'side')
        (agent_path / 'side-work').write_text('private branch work')
        git(agent_path, 'add', 'side-work')
        git(agent_path, 'commit', '-q', '-m', 'private side')
        side = git(agent_path, 'rev-parse', 'HEAD')
        git(agent_path, 'checkout', '-q', 'main')
        status, _, err = release([agent_path, inner_path])
        held = ledger.item(agent)
        check('rv/private-branch', status == 0 and held['state'] == 'deferred'
              and held.get('deferral', {}).get('rule') == 'unique_work'
              and 'refs/heads/side' in held.get('deferral', {}).get('found', {}).get('not_across', [])
              and agent_path.is_dir() and not inner_path.exists()
              and git(agent_path, 'rev-parse', 'side') == side
              and git(agent_path, 'show', 'side:side-work') == 'private branch work', held)

        # R3: an operation in progress takes precedence over the untracked draft.
        agent, agent_path, inner, inner_path = pair('git-locked')
        (inner_path / 'draft').write_text('draft during git operation')
        lock = Path(git(inner_path, 'rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_text('operation in progress')
        status, _, err = release([agent_path, inner_path])
        held = ledger.item(inner)
        check('rv/git-lock-and-draft', status == 0 and held['state'] == 'deferred'
              and held.get('deferral', {}).get('rule') == 'in_use'
              and held.get('deferral', {}).get('refused_by') == 'process_use'
              and agent_path.is_dir() and inner_path.is_dir()
              and (inner_path / 'draft').read_text() == 'draft during git operation'
              and lock.read_text() == 'operation in progress', held)

        agent, agent_path, inner, inner_path = pair('keep-failed')
        service.space_consumer.given['keep'] = lambda identity, item: {'ok': False, 'said': 'save refused'}
        status, out, err = release([agent_path, inner_path])
        service.space_consumer.given.pop('keep')
        check('safety/keep-failure', status == 0 and agent_path.is_dir() and inner_path.is_dir()
              and ledger.item(inner)['deferral']['rule'] == 'keep_failed', ledger.item(inner))

        agent, agent_path, inner, inner_path = pair('owner-kept')
        (inner_path / 'draft').write_text('owner retained work')
        ledger.signal('contained', {'items': [{'item': inner, 'version': ledger._row(inner, SP.ITEM_KIND)[0]}]})
        kept = ledger.outcome(inner, 'kept', {'owner_keep': {'at': 100}}, principal='owner')
        if not kept['ok']:
            raise RuntimeError(kept)
        release([agent_path, inner_path])
        check('safety/owner-keep', ledger.item(inner)['state'] == 'kept' and agent_path.is_dir()
              and (inner_path / 'draft').read_text() == 'owner retained work')

        agent, agent_path, inner, inner_path = pair('unsaved')
        with open(agent_path / '.git' / 'info' / 'exclude', 'a') as stream:
            stream.write('\nsettings.local\n')
        (inner_path / 'settings.local').write_text('ignored work')
        (inner_path / 'draft').write_text('untracked work')
        release([agent_path, inner_path])
        check('safety/unsaved', agent_path.is_dir() and (inner_path / 'settings.local').read_text() == 'ignored work'
              and (inner_path / 'draft').read_text() == 'untracked work')

        agent, agent_path, inner, inner_path = pair('report')
        ledger.acts = lambda scope: False
        release([agent_path, inner_path])
        check('safety/report', inner_path.is_dir() and agent_path.is_dir()
              and ledger.item(inner)['state'] == 'due')
        ledger.acts = lambda scope: True

        agent, agent_path, inner, inner_path = pair('protected')
        (inner_path / 'draft').write_text('protected work')
        status, out, err = release([agent_path, inner_path], wake=False)
        ledger.protect.append({'type': 'path', 'value': str(inner_path), 'engines': []})
        service.hint_after(0)
        drain()
        check('safety/protected-after-receipt', status == 0 and agent_path.is_dir()
              and (inner_path / 'draft').read_text() == 'protected work'
              and ledger.item(inner)['deferral']['rule'] == 'protected', ledger.item(inner))
        status, _, err = release_call([inner_path])
        check('safety/protected-at-receipt', status == 1 and 'space_protected:' in err, err)

        before = ledger.events()
        answer = ledger.event('released', {'paths': [str(inner_path)]},
                              {'verb': 'event', 'host': ledger.host})
        check('safety/ledger-protected-at-receipt', not answer['ok']
              and answer.get('reason') == 'space_protected:path:' + str(inner_path)
              and ledger.events() == before and (inner_path / 'draft').read_text() == 'protected work', answer)

        # The CLI's own emitter stands for released only: no other kind is recorded from the verb.
        for kind, subject in (('ref_changed', {'repository': str(repo), 'ref': 'refs/heads/main',
                                               'old': tip, 'new': tip}),
                              ('session_ended', {'session': 'cli-emitter', 'pid': os.getpid()})):
            before = ledger.events()
            answer = ledger.event(kind, subject, {'verb': 'event', 'host': ledger.host})
            check('safety/cli-emitter-released-only', not answer['ok']
                  and answer.get('reason') == 'invalid_input:emitter' and ledger.events() == before,
                  (kind, answer))

        # Do not re-resolve a received observation after a later declaration takes its path.
        agent, agent_path, inner, inner_path = pair('identity')
        status, out, err = release([inner_path], wake=False)
        if status == 0:
            old = ledger.event_record(out['event'])
            renamed = dict(old, subject=dict(old['subject'], items=[fleet]))
            check('safety/bound-identity', W.selected(ledger, renamed)[1] == [])
            legacy = dict(old, subject={'paths': [str(inner_path)]})
            check('safety/bound-identity', W.selected(ledger, legacy)[1] == [])
        else:
            check('safety/bound-identity', False, err)
        service.hint_after(0)
        drain()

        for name in PRODUCTION:
            check('canon', (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
        check('canon', (ROOT / 'engine/bin/veldo').read_bytes() == (ROOT / 'bin/veldo').read_bytes())
        conn.close()
    for name, checks in rows.items():
        expect('VELDO-0335 ' + name, bool(checks) and all(checks))


_v335_suite()
