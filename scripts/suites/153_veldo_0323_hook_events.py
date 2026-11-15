"""VELDO-0323: real journal, signed packets, worker processes, git, keeper and removers.

Only ROOT and expect are shared. The fixture supplies declarations, membership records,
act eligibility, free bytes, and a private process table. No Docker engine is contacted.
The service wiring is explicit, as in suite 149. Every filesystem change is in this suite's
temporary tree. Mutation runs replace the named production files before any organ loads.
"""


def _v323_suite():
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
    }
    rows = {}

    def check(name, condition, detail=''):
        rows.setdefault(name, []).append(bool(condition))
        if not condition:
            print('VELDO-0323 detail %s: %s' % (name, detail))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0323-') as directory:
        base = Path(directory).resolve()
        mods = base / '.veldo'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        SVC = load('v323_service', mods / 'control_service.py')
        C = SVC.SPACE_CONSUMER
        W, S, CM = C.WORKER, SVC.S, SVC.CM
        SP, P, K, RM, KP, spool = W.SP, W.PROBE, W.KINDS, W.REMOVE, W.KEEP, W.SPOOL
        GP = load('v323_git', mods / 'git_process.py')
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

        def drain(timeout=300, allow_failure=False, exits=False):
            # A worker's pipe is waited for. A held client's process descriptor is waited for only
            # when the row has just ended that client (exits).
            def busy():
                return service.space_consumer.active or (exits and service.space_pipes())
            until = time.monotonic() + timeout
            while busy() and time.monotonic() < until:
                for descriptor in select.select(list(service.space_pipes()), [], [], 0.1)[0]:
                    service.space_readable(descriptor)
            if busy():
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

        wt, path, branch, owner = worktree('complete')
        (path / 'log-only').write_text('commit no branch holds')
        git(path, 'add', 'log-only')
        git(path, 'commit', '-q', '-m', 'log only')
        log_commit = git(path, 'rev-parse', 'HEAD')
        git(path, 'reset', '-q', '--hard', tip)
        git(path, 'reset', '-q', '--hard', tip)
        build = path / 'build'
        build.mkdir()
        (build / 'generated').write_text('reproducible')
        output = declare('build_output', build, owner, parent=wt)
        real_time = time.time
        frozen = real_time()
        time.time = lambda: frozen
        try:
            record = event()
            check('ac1/journal-advance', time.time() == frozen)
        finally:
            time.time = real_time
        kept = ledger.item(wt).get('kept') or {}
        check('ac1/journal-advance', not path.exists() and ledger.item(wt)['state'] == 'removed', ledger.item(wt))
        check('ac1/keep-and-order', bool(kept.get('refs')) and all(
            git(repo, 'rev-parse', name) == value for name, value in kept.get('refs', {}).items()))
        check('safety/log-only-kept', bool(kept.get('refs'))
              and log_commit in git(repo, 'rev-list', *kept.get('refs', {})).splitlines())
        result = ledger.event_record(record)['result'] or {'outcomes': []}
        removed = [one['item'] for one in result.get('outcomes', []) if one.get('outcome') == 'removed']
        check('ac1/keep-and-order', removed.index(output) < removed.index(wt) if wt in removed and output in removed else False)
        check('ac1/branch-kept', ledger.item(branch)['state'] == 'kept' and bool(ledger.item(branch).get('contained'))
              and git(repo, 'rev-parse', 'complete') == tip)
        emitter = (ledger.item(wt).get('removal') or {}).get('emitter') or {}
        check('ac1/trace', emitter.get('event_record') == record and emitter.get('worker') != os.getpid()
              and (emitter.get('owners') or {}).get(wt) == owner)

        wt2, path2, _branch2, _owner2 = worktree('declared-landing')
        event(subject=dict(repository=str(repo), ref='refs/heads/landing', old=first, new=tip))
        check('ac1/declared-landing', not path2.exists())
        # An agent worktree's commits must survive removal of the private repository itself.
        git(repo, 'branch', 'agent-complete', tip)
        agent_path = trees / 'agent-repository'
        git(trees, 'clone', '-q', str(repo), str(agent_path))
        agent_owner = {'scope': scope, 'ticket': 'agent-complete'}
        agent = declare('agent_repository', agent_path, agent_owner)
        inner_path = agent_path / 'inner'
        git(agent_path, 'worktree', 'add', '-q', '-b', 'agent-complete', str(inner_path), tip)
        inner = declare('worktree', inner_path, agent_owner, parent=agent, branch='agent-complete', start=first)
        ledger.rebranch(inner, 'agent-complete', first)
        (inner_path / 'agent-log').write_text('only in the private object store')
        git(inner_path, 'add', 'agent-log')
        git(inner_path, 'commit', '-q', '-m', 'private log commit')
        agent_log = git(inner_path, 'rev-parse', 'HEAD')
        git(inner_path, 'reset', '-q', '--hard', tip)
        git(inner_path, 'reset', '-q', '--hard', tip)
        event()
        inner_kept = ledger.item(inner).get('kept') or {}
        check('safety/agent-kept-in-main', not agent_path.exists() and ledger.item(agent)['state'] == 'removed'
              and inner_kept.get('repository') == str(repo) and bool(inner_kept.get('refs'))
              and agent_log in git(repo, 'rev-list', *inner_kept['refs']).splitlines(), ledger.item(agent))
        at_start, start_path, _b, _o = worktree('at-start', start=tip)
        event()
        check('ac1/not-past-start', start_path.is_dir() and ledger.item(at_start)['state'] == 'present')
        absent = event(subject=dict(repository=str(repo), ref='refs/heads/main', old=tip, new='1' * 40))
        check('ac1/missing-commit', (ledger.event_record(absent)['result'] or {}).get('items') == [])

        dirty, dirty_path, _b, _o = worktree('dirty')
        (dirty_path / 'draft').write_text('only untracked work')
        hidden, hidden_path, _b, _o = worktree('hidden')
        with open(repo / '.git' / 'info' / 'exclude', 'a') as stream:
            stream.write('\nsettings.local\n')
        (hidden_path / 'settings.local').write_text('only ignored work')
        failed, failed_path, _b, _o = worktree('keep-failure')
        protected, protected_path, _b, _o = worktree('owner-kept')
        (protected_path / 'draft').write_text('owner work')
        ledger.signal('contained', {'items': [{'item': protected, 'version': ledger._row(protected, SP.ITEM_KIND)[0]}]})
        answer = ledger.outcome(protected, 'kept', {'owner_keep': {'at': 100}}, principal='owner')
        if not answer['ok']:
            raise RuntimeError(answer)
        def keeper(identity, item):
            if identity == failed:
                return {'ok': False, 'said': 'fixture cannot save'}
            return KP.keep(ledger, identity, item)
        service.space_consumer.given['keep'] = keeper
        event()
        service.space_consumer.given.pop('keep')
        check('safety/planted-work', (dirty_path / 'draft').read_text() == 'only untracked work'
              and (hidden_path / 'settings.local').read_text() == 'only ignored work')
        check('safety/keep-failure', failed_path.is_dir() and ledger.item(failed)['state'] == 'deferred'
              and ledger.item(failed)['deferral']['rule'] == 'keep_failed')
        check('safety/owner-keep', ledger.item(protected)['state'] == 'kept'
              and (protected_path / 'draft').read_text() == 'owner work')

        # Count all git reads made by the service during a hundred-branch event.
        for number in range(100):
            name = 'recorded-%03d' % number
            git(repo, 'branch', name, tip)
            made = ledger.declare('branch', {'repository': str(repo), 'ref': name}, {'scope': scope},
                                  'seam', start=first)
            ledger.confirm(made['item'])
        # The count is taken where a process is made, so it holds every git command of the service
        # process, by whatever function it is reached. A child's commands are not the service's.
        parent_calls = []
        parent_pid = os.getpid()
        real_popen = subprocess.Popen
        def counted(args=None, *rest, **more):
            argv = list(args) if isinstance(args, (list, tuple)) else [args]
            if os.getpid() == parent_pid and os.path.basename(str(argv[0])) == 'git':
                parent_calls.append(argv)
            return real_popen(args, *rest, **more)
        subprocess.Popen = counted
        try:
            event()
            during = len(parent_calls)
            git(repo, 'rev-parse', 'HEAD')
        finally:
            subprocess.Popen = real_popen
        check('ac2/no-service-git', during == 0, str(during))
        # The counter is not blind: the fixture's own git command, made the same way, is counted.
        check('ac2/no-service-git', len(parent_calls) == during + 1, str(len(parent_calls)))

        # A real pipe latch in the remover child. Another signed packet is answered while held.
        held, held_path, _b, _o = worktree('latched')
        latch, entered = base / 'latch', base / 'entered'
        os.mkfifo(latch)
        def latched(which, latch, entered):
            class Latched:
                left = staticmethod(RM.left)
                @staticmethod
                def remove(ledger, probe, identity, item, **given):
                    if identity == which:
                        entered.write_text(str(os.getpid()))
                        with open(latch, 'rb') as stream:
                            stream.read(1)
                    return RM.remove(ledger, probe, identity, item, **given)
            return Latched

        def release(latch):
            # Never waits for a reader: the byte is there for the remover whenever it gets to the latch.
            descriptor = os.open(latch, os.O_RDWR | os.O_NONBLOCK)
            os.write(descriptor, b'x')
            return descriptor

        def held_child(entered):
            # Waits for the service's child to reach the latch, however slow the host is, and stops
            # when there is no child or the child has answered without getting there.
            until = time.monotonic() + 300
            while time.monotonic() < until:
                if entered.exists() and entered.read_text():
                    return int(entered.read_text())
                active = service.space_consumer.active
                if not active or select.select([active[0]], [], [], 0.01)[0]:
                    break
            return int(entered.read_text()) if entered.exists() and entered.read_text() else None

        def consumed():
            return [identity for (text,) in conn.execute('SELECT transition FROM journal ORDER BY seq')
                    for identity, change in json.loads(text).items()
                    if change['kind'] == SP.EVENT_KIND and change['data']['state'] == 'consumed']

        service.space_consumer.given['remover'] = latched(held, latch, entered)
        # One descriptor the service says it holds, and one it does not: something handed down to it.
        owned_file, inherited_file = base / 'service-owned', base / 'inherited'
        owned_fd = os.open(owned_file, os.O_CREAT | os.O_RDWR, 0o600)
        inherited_fd = os.open(inherited_file, os.O_CREAT | os.O_RDWR, 0o600)
        service.space_owned = [owned_fd]
        e1 = event(wake=False)
        service.hint_after(service.watermark() - 1)
        child = held_child(entered)
        child_open = set()
        if child:
            for name in os.listdir('/proc/%d/fd' % child):
                try:
                    child_open.add(os.readlink('/proc/%d/fd/%s' % (child, name)))
                except OSError:
                    pass
        check('ac2/only-service-descriptors', str(owned_file) not in child_open, sorted(child_open))
        check('ac2/only-service-descriptors', str(inherited_file) in child_open, sorted(child_open))
        service.space_owned = []
        os.close(owned_fd)
        os.close(inherited_fd)
        listener = service.space_listen()
        request = dict(operation=SP.EVENT, principal=SP.OBSERVER, command_id=uuid.uuid4().hex,
                       nonce=uuid.uuid4().hex, issued_at=time.time(), parameters=dict(type='ref_changed',
                       subject=dict(repository=str(repo), ref='refs/heads/main', old=first, new=tip),
                       emitter={'hook': 'reference-transaction', 'host': 'fixture'}))
        packet = {'command': request, 'signature': sign(S.canonical_bytes(request))}
        answers = []
        def ask():
            answers.append(spool.Remote(listener.getsockname()).accept(packet))
        thread = threading.Thread(target=ask)
        thread.start()
        service.space_packet(listener)
        thread.join(60)
        check('ac2/responsive', entered.exists() and bool(answers) and answers[0].get('ok')
              and held_path.exists() and ledger.event_record(e1)['state'] == 'received', answers)
        check('ac3/oldest-once', bool(answers) and ledger.event_record(answers[0].get('event'))['state'] == 'received')
        released = release(latch)
        drain()
        os.close(released)
        listener.close()
        service.space_consumer.given.pop('remover')
        e2 = answers[0]['event']
        check('ac3/oldest-once', ledger.event_record(e1)['state'] == ledger.event_record(e2)['state'] == 'consumed'
              and ledger.event_record(e1)['result']['worker'] != ledger.event_record(e2)['result']['worker'])
        consumed_order = consumed()
        check('ac3/oldest-once', e1 in consumed_order and e2 in consumed_order
              and consumed_order.index(e1) < consumed_order.index(e2))
        signals = conn.execute('SELECT COUNT(*) FROM journal WHERE command_id=?', ('space-hook:' + e1,)).fetchone()[0]
        service.space = service.space
        service.space_start()
        drain()
        check('ac3/restart', signals == 1 and conn.execute('SELECT COUNT(*) FROM journal WHERE command_id=?',
              ('space-hook:' + e1,)).fetchone()[0] == 1 and ledger.event_record(e1)['state'] == 'consumed')
        check('ac3/consumed-refused', ledger.consumed(e1, {'items': []}).get('reason') == 'space_event_consumed')
        before = service.watermark()
        replayed = ledger.accept(packet, CM, time.time())
        check('ac3/packet-replay', replayed.get('replayed') and replayed.get('event') == e2
              and service.watermark() == before)

        # Three records are received before any child starts, so the order is chosen: oldest first.
        queued = [event(subject=dict(repository=str(repo), ref='refs/heads/main', old=tip, new=digit * 40),
                        wake=False) for digit in '234']
        service.hint_after(service.watermark() - 1)
        drain()
        order = [identity for identity in consumed() if identity in queued]
        check('ac3/oldest-first', order == queued, [queued.index(identity) for identity in order])

        # A replacement service: a second consumer on the same store and state root, started while
        # the first one's child is held in a remover. Its child waits for the lock. Then it reads
        # again under the lock: the first record is consumed, so it takes the next one.
        locked, locked_path, _b, _o = worktree('locked')
        latch2, entered2 = base / 'latch2', base / 'entered2'
        os.mkfifo(latch2)
        service.space_consumer.given['remover'] = latched(locked, latch2, entered2)
        l1 = event(wake=False)
        l2 = event(subject=dict(repository=str(repo), ref='refs/heads/main', old=tip, new='5' * 40), wake=False)
        service.hint_after(service.watermark() - 1)
        first_child = held_child(entered2)
        second_seen = []
        second = C.Consumer(ledger, dict(service.space_consumer.given), landing=service.space_consumer.landing,
                            observe=second_seen.append)
        second.advance()
        second_child = second.active[1] if second.active else None
        waited = bool(second.active) and not select.select(list(second.pipes()), [], [], 3)[0]
        check('ac3/one-worker', bool(first_child) and waited and locked_path.exists()
              and ledger.event_record(l1)['state'] == ledger.event_record(l2)['state'] == 'received',
              [first_child, second_child, waited, second_seen])
        released = release(latch2)
        until = time.monotonic() + 300
        while second.pipes() and time.monotonic() < until:
            for descriptor in select.select(list(second.pipes()), [], [], 0.1)[0]:
                second.readable(descriptor)
        drain(allow_failure=True)
        os.close(released)
        service.space_consumer.given.pop('remover')
        r1, r2 = ledger.event_record(l1), ledger.event_record(l2)
        check('ac3/one-worker', r1['state'] == 'consumed' and (r1['result'] or {}).get('worker') == first_child
              and not (r1['result'] or {}).get('recovered') and consumed().count(l1) == 1
              and conn.execute('SELECT COUNT(*) FROM journal WHERE command_id=?',
                               ('space-hook:' + l1,)).fetchone()[0] == 1
              and not locked_path.exists() and ledger.item(locked)['state'] == 'removed'
              and observations[-1].get('ok') is True, [r1, observations[-1]])
        check('ac3/read-again-under-lock', r2['state'] == 'consumed' and consumed().count(l2) == 1
              and (r2['result'] or {}).get('worker') == second_child and len(second_seen) == 1
              and not second_seen[0].get('already_consumed'), [r2, second_child, second_seen])
        # The next record gets a worker of its own, whatever the row above left behind.
        event(subject=dict(repository=str(repo), ref='refs/heads/main', old=tip, new='6' * 40))

        # A stop after Signal's journal write must not signal the same event again on restart.
        recovery, recovery_path, _b, _o = worktree('recovery')
        saved_consumed = ledger.consumed
        ledger.acts = lambda scope: False
        ledger.consumed = lambda *args, **kwargs: {'ok': False, 'reason': 'fixture_stop_after_signal'}
        recovery_event = event(wake=False)
        service.hint_after(service.watermark() - 1)
        drain(allow_failure=True)
        ledger.consumed = saved_consumed
        ledger.acts = lambda scope: True
        service.space = service.space
        service.space_start()
        drain()
        check('ac3/recover-after-signal', ledger.event_record(recovery_event)['state'] == 'consumed'
              and ledger.event_record(recovery_event)['result'].get('recovered')
              and ledger.item(recovery)['state'] == 'due' and recovery_path.exists()
              and conn.execute('SELECT COUNT(*) FROM journal WHERE command_id=?',
                               ('space-hook:' + recovery_event,)).fetchone()[0] == 1)

        # The actual spool replay runs in a child, followed by event children, then reconcile.
        spooled, spooled_path, _b, _o = worktree('spooled')
        folder = spool.spool_folder(str(state))
        spool.put(folder, spool.entry('ref_changed', dict(repository=str(repo), ref='refs/heads/main',
                  old=first, new=tip), 'reference-transaction', 'fixture'))
        def packet_sign(operation, parameters, command_id, nonce):
            command = dict(principal=SP.OBSERVER, operation=operation, parameters=parameters,
                           command_id=command_id, nonce=nonce, issued_at=time.time())
            return {'command': command, 'signature': sign(S.canonical_bytes(command))}
        local = spool.Local(ledger, CM, landing=service.config['space_landing'])
        reconciled = base / 'reconciled'
        def reconcile():
            reconciled.write_text(json.dumps({'exists': spooled_path.exists(), 'pending': [identity for identity,
                record in ledger.events() if record['state'] == 'received']}))
        service.space_start(replay=lambda: spool.replay(folder, local, packet_sign, seconds=None), reconcile=reconcile)
        drain()
        check('ac3/spool-before-reconcile', not spool.pending(folder) and reconciled.exists()
              and json.loads(reconciled.read_text()) == {'exists': False, 'pending': []})

        def session(name, scope, process):
            path = scratch / name
            path.mkdir()
            (path / 'scratch').write_text(name)
            identity = declare('scratch', path, {'scope': scope, 'session': name}, process=process)
            return identity, path
        dead = {'pid': 99999999, 'started': 1}
        live = P.process(os.getpid())
        os.symlink('/proc/' + str(os.getpid()), proc / str(os.getpid()))
        ended, ended_path = session('ended', scope, dead)
        event('session_ended', dict(session='ended', cwd=str(base), **dead))
        check('ac4/session-ended', not ended_path.exists() and ledger.item(ended)['state'] == 'removed')
        nested, nested_path = session('scratch-repository', scope, dead)
        git(nested_path, 'init', '-q', '-b', 'main')
        git(nested_path, 'add', 'scratch')
        git(nested_path, 'commit', '-q', '-m', 'only copy')
        nested_tip = git(nested_path, 'rev-parse', 'HEAD')
        event('session_ended', dict(session='scratch-repository', cwd=str(base), **dead))
        check('safety/session-work-kept', nested_path.is_dir()
              and git(nested_path, 'rev-parse', 'HEAD') == nested_tip)
        none, none_path = session('no-project', {'type': 'no_project'}, dead)
        other, other_path = session('other-project', {'type': 'project', 'id': 'other'}, dead)
        alive, alive_path = session('alive', scope, {'pid': live['pid'], 'started': live['start']})
        os.utime(alive_path / 'scratch', (0, 0))
        unread, unread_path = session('unread', scope, {'pid': 987654, 'started': 1})
        (proc / '987654').mkdir()
        (proc / '987654' / 'stat').write_text('unreadable record')
        # An unread process stat must not select scratch. Rule 4's table below is empty for dead sessions.
        unread_selected = W.selected(ledger, {'type': 'session_started', 'subject': {},
                                            'emitter': {'host': 'fixture'}}, proc=str(proc))[1]
        check('ac4/unread-stays', unread not in unread_selected)
        table = W.PROBE._table
        W.PROBE._table = lambda proc: {'read': False}
        try:
            check('ac4/unread-stays', not W._ended(dead, str(proc)))
        finally:
            W.PROBE._table = table
        (proc / '987654' / 'stat').unlink()
        (proc / '987654').rmdir()
        event('session_started', dict(session='new', cwd=str(base), pid=live['pid'], started=live['start']))
        check('ac4/host-wide', not none_path.exists() and not other_path.exists(),
              [ledger.item(none), ledger.item(other)])
        check('ac4/live-no-age', alive_path.is_dir() and ledger.item(alive)['state'] == 'present')

        # The SessionEnd hook runs inside its client, so the record arrives while the client is alive.
        # It is not dropped: the scratch is left deferred by rule 3 and the record names it. Nothing
        # is asked again on a clock. The kernel reports the client's end, and that is the event.
        def client_session(name):
            client = subprocess.Popen(['sleep', '600'])
            os.symlink('/proc/%d' % client.pid, proc / str(client.pid))
            process = {'pid': client.pid, 'started': P.process(client.pid)['start']}
            identity, path = session(name, scope, process)
            return client, process, identity, path

        def exit_records(origin):
            return [(identity, record) for identity, record in ledger.events()
                    if record['emitter'].get('after') == origin]

        clients = []
        frozen = real_time()
        time.time = lambda: frozen
        try:
            client, process, waiting, waiting_path = client_session('client-alive')
            clients.append(client)
            early = event('session_ended', dict(session='client-alive', cwd=str(base), **process))
            record, item = ledger.event_record(early), ledger.item(waiting)
            deferral = item.get('deferral') or {}
            check('ac4/ended-while-alive-held', waiting_path.is_dir() and item['state'] == 'deferred'
                  and deferral.get('rule') == 'in_use' and deferral.get('refused_by') == 'owner_live'
                  and (deferral.get('emitter') or {}).get('event_record') == early
                  and record['state'] == 'consumed'
                  and [(one['item'], one['why']) for one in (record['result'] or {}).get('held', [])]
                  == [(waiting, 'client_alive')], [item, record])
            pipes = list(service.space_pipes())
            quiet = len(pipes) == 1 and not select.select(pipes, [], [], 0.5)[0]
            check('ac4/re-judged-at-client-exit', quiet and waiting_path.is_dir() and not exit_records(early),
                  [pipes, exit_records(early)])
            # Ended and collected by its parent, as a client's shell does: a process not yet
            # collected is one rule 4 cannot read, and it would defer the scratch once more.
            client.terminate()
            client.wait()
            drain(exits=True)
            exits = exit_records(early)
            removal = (ledger.item(waiting).get('removal') or {}).get('emitter') or {}
            check('ac4/re-judged-at-client-exit', len(exits) == 1 and exits[0][1]['emitter']['hook'] == 'client-exit'
                  and exits[0][1]['type'] == 'session_ended' and exits[0][1]['state'] == 'consumed'
                  and not waiting_path.exists() and ledger.item(waiting)['state'] == 'removed'
                  and removal.get('event_record') == exits[0][0] and not service.space_pipes()
                  and time.time() == frozen, [exits, ledger.item(waiting)])

            # A service that starts again holds the client of every scratch left deferred that way.
            client, process, again, again_path = client_session('client-alive-restart')
            clients.append(client)
            early = event('session_ended', dict(session='client-alive-restart', cwd=str(base), **process))
            for descriptor in list(service.space_consumer.watched):
                os.close(descriptor)
            service.space = service.space
            service.space_start()
            drain()
            check('ac4/held-across-restart', len(service.space_pipes()) == 1 and again_path.is_dir()
                  and ledger.item(again)['state'] == 'deferred', ledger.item(again))
            # Ended and collected by its parent, as a client's shell does: a process not yet
            # collected is one rule 4 cannot read, and it would defer the scratch once more.
            client.terminate()
            client.wait()
            drain(exits=True)
            check('ac4/held-across-restart', len(exit_records(early)) == 1 and not again_path.exists()
                  and ledger.item(again)['state'] == 'removed', ledger.item(again))
        finally:
            time.time = real_time
            for client in clients:
                client.kill()
                client.wait()
        check('safety/signature-expiry', not ledger.accept(dict(packet, signature='forged'), CM, time.time())['ok'])
        check('safety/signature-expiry', ledger.accept(packet, CM, request['issued_at'] + SP.PACKET_AGE + 1)
              .get('reason') == 'space_packet_expired')
        for where in (str(repo / '..' / repo.name), str(base / 'linked-repository')):
            if where.endswith('linked-repository'):
                os.symlink(repo, where)
            bad = ledger.event('ref_changed', dict(repository=where, ref='refs/heads/main', old=first, new=tip),
                               {'hook': 'reference-transaction', 'host': 'fixture'})
            check('safety/locators', not bad['ok'] and bad.get('reason') in
                  ('space_locator_parent', 'space_locator_link'), bad)
        loader = importlib.machinery.SourceFileLoader('v323_cli', str(ROOT / 'bin/veldo'))
        cli_spec = importlib.util.spec_from_loader('v323_cli', loader)
        cli = importlib.util.module_from_spec(cli_spec)
        cli_spec.loader.exec_module(cli)
        cli.ROOT = base
        before = service.watermark()
        for args in (['--type', 'released', '--path', str(alive_path)],
                     ['--type', 'session_started', '--session', 's-1'],
                     ['--type', 'session_ended', '--session', 's-1', '--path', str(alive_path)],
                     ['--type', 'ref_changed', '--repository', str(repo), '--ref', 'refs/heads/main', '--new', tip]):
            out, err = io.StringIO(), io.StringIO()
            status = cli.space_event(args, space={'ledger': ledger}, stdout=out, stderr=err)
            check('compatibility/cli-envelope-refused', status == 1 and out.getvalue() == ''
                  and 'refused invalid_input:emitter' in err.getvalue(), err.getvalue())
        check('compatibility/cli-envelope-refused', before == service.watermark())
        scaffold = load('v323_scaffold', mods / 'init_scaffold.py')
        absent_modules = [name for name in SVC.closure() if '.veldo/' + name not in scaffold._FILES]
        check('compatibility/installed-closure', absent_modules == [], absent_modules)
        for name in PRODUCTION:
            check('canon', (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
        conn.close()
    for name, checks in rows.items():
        expect('VELDO-0323 ' + name, bool(checks) and all(checks))


_v323_suite()
