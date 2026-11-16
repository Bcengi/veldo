"""VELDO-0317: full-pool receiver ends, retries and preserved work.

Real temporary store, Ledger, Signal, rules, folder remover, Runner and factory Line.
Eligibility, source, free bytes, empty engine responses and the process table are fixtures.
Only scratch made in this suite is removed. No live engine or host process reader is used.
"""


def _v317_suite():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import traceback
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v317_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0317-') as temporary:
        base = Path(temporary)
        mods = base / '.veldo'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('launch', mods / 'control_launch.py')
        A, D, RES = L.ADMISSION, L.D, L.D.RES
        S = load('store', mods / 'control_store.py')
        SP = load('space', mods / 'control_space.py')
        CFG = load('config', mods / 'control_space_config.py')
        YAML = load('yaml', mods / 'yamlish.py')
        K = load('kinds', mods / 'control_space_kinds.py')
        SV = load('service', mods / 'control_service.py')
        CON = load('consumer', mods / 'control_space_consumer.py')
        SIG = load('signal', mods / 'control_space_signal.py')

        def sign(message):
            return 'fixture:' + S.digest_of(message.decode())

        class Fixture:
            def __init__(self, name, act=True):
                self.root = base / name
                self.repo = self.root / 'project'
                (self.repo / '.veldo').mkdir(parents=True)
                self.file = self.repo / '.veldo' / 'space.yaml'
                self.file.write_text('needs: {}\n')
                self.state = self.root / 'state'
                self.state.mkdir()
                config = CFG.check({'enabled': True, 'time_zone': 'UTC',
                    'pools': {'host': {'floor': 20, 'needs': {'build': 100, 'review': 100, 'gate': 100}},
                              'image': {'floor': 10, 'needs': {'build': 40, 'review': 40, 'gate': 40}}},
                    'engines': ['fixture'], 'scratch_roots': {'roots': [str(self.root / 'scratch')],
                        'session_pattern': 'sessions/{working_folder}/{session_id}'},
                    'build_roots': [], 'plain_repositories': [], 'client_accounts': [],
                    'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [],
                                'networks': [], 'compose_projects': []}})
                project = dict(CFG.read_project(str(self.repo), YAML.read, config=config), repository=str(self.repo))
                self.conn = S.open_store(str(self.root / 'store.sqlite3'))
                self.ledger = SP.Ledger(S, self.conn, 'runner', sign, config=config,
                    state_root=str(self.state), host='fixture', projects=[project],
                    lifecycle={'version': K.REGISTRY['version'],
                               **{k: K.REGISTRY['tables'][K.REGISTRY['version']][k] for k in ('events', 'ends_on')}})
                A.accepted(self.ledger.set_pool('host', 'filesystem', device=self.ledger.device(str(self.repo))))
                A.accepted(self.ledger.set_pool('image', 'engine_image', engine='fixture', backing='host'))
                self.scope = {'type': 'project', 'id': 'project'}
                # Mode prerequisites have their own suites. Seed their accepted outcome here only.
                if act:
                    self.seed(SP.mode_id(self.scope), SP.MODE_KIND, {'scope': self.scope, 'mode': 'act'})
                self.seed('runner', 'membership', dict(principal_type='service', roles=['reservation_service'],
                    scope=['repository'], revoked_at=None, expires_at=None))
                self.seed('project:project', 'project', {'name': 'project'})
                self.free = {'host': 10000, 'image': 1000}
                self.reads = []
                self.space = {'ledger': self.ledger, 'free': self.read_free}
                self.reservations = RES.Reservations(S, self.conn, domain='domain', repository='repository',
                    principal='runner', authorize=lambda conn, command: True, signer='runner', sign=sign)
                self.dispatches = D.Dispatches(S, self.conn, domain='domain', repository='repository',
                    principal='runner', signer='runner', sign=sign)
                for scope, subject in [('account', 'account'), ('project', 'project')]:
                    self.reservations.configure('policy/' + subject, scope, subject,
                        dict(capacity=50, invocations=100, wall_seconds=10000), now=time.time())
                self.gate = types.SimpleNamespace(unit_record=lambda unit: {'project': 'project'},
                    require=self.decision, decide=lambda station, unit, context=None:
                    dict(self.decision(station, unit, context), eligible=True))
                self.started = []
                self.units = set()
                self.runner = L.Runner(self.gate, self.reservations, self.dispatches, self.invoke,
                                       account='account', space=self.space)
                # Existing sweeps test containment and removal elsewhere. No run is left in this fixture.
                self.runner.sweep = lambda: None

            def seed(self, identity, kind, data):
                encoded = json.dumps(data, sort_keys=True)
                self.conn.execute('INSERT OR REPLACE INTO entities(id,kind,version,digest,data) VALUES(?,?,?,?,?)',
                                  (identity, kind, 1, D.digest(data), encoded))
                self.conn.commit()

            def read_free(self, pool):
                self.reads.append((os.getpid(), pool['name']))
                return self.free[pool['name']]

            def decision(self, station, unit, context=None):
                return dict(decision_id='decision', station=station, unit=unit, domain_uuid='domain',
                            watermark=1, inputs={'fixture': True})

            def offer(self, unit='unit', station='review', submit=False):
                if unit not in self.units:
                    self.reservations.configure('policy/' + unit, 'unit', unit,
                        dict(capacity=10, invocations=100, wall_seconds=10000), now=time.time())
                    self.units.add(unit)
                with patch.object(L.CFG, 'bind', lambda *args: args[-1]), patch.object(
                        L, 'resolve_source', lambda *args: {'commit': 'a' * 40, 'tree': 'b' * 40}):
                    return (self.runner.submit if submit else self.runner.prepare)(unit, station,
                        holder='builder', source=str(self.repo), revision='HEAD', payload={'task': 'fixture'},
                        adapter='fixture', configuration={}, deadline=time.time() + 60)

            def invoke(self, contract):
                identity = dict(platform='linux', host='fixture', boot_id='fixture', pid=os.getpid(), start='1')
                self.dispatches.accept(contract['dispatch_id'], D.digest(contract),
                                       dict(identity, principal='runner'), now=time.time())
                child = subprocess.run([sys.executable, '-c', 'print("started")'], capture_output=True, check=True)
                self.started.append(child.stdout)
                self.dispatches.run(contract['dispatch_id'], D.digest(contract), identity, now=time.time())
                record = self.dispatches.record(contract['dispatch_id'])
                return types.SimpleNamespace(owned=True, contract=contract, dispatch_id=contract['dispatch_id'],
                    record=record, result='accepted', pump=lambda **kwargs: False)

            def request(self, unit='unit', station='build'):
                return A.prepare(self.space, repository='repository', project='project', unit=unit,
                                 station=station, attempt=1)

            def no_dispatch(self):
                return not self.conn.execute("SELECT 1 FROM entities WHERE kind IN ('dispatch','dispatch_active')").fetchone()

            def slots(self):
                return [json.loads(row[0]) for row in self.conn.execute(
                    "SELECT data FROM entities WHERE kind='subscription_reservation'")
                    if json.loads(row[0]).get('type') == 'worker']

            def close(self):
                self.conn.close()

        fixtures = []
        consumer = None
        def fixture(name, act=True):
            f = Fixture(name, act)
            fixtures.append(f)
            return f

        def refused(call):
            try:
                return call(), None
            except Exception as error:
                return None, error

        P = load('probe', mods / 'control_space_probe.py')
        R = load('remove', mods / 'control_space_remove.py')
        KP = load('keep', mods / 'control_space_keep.py')

        def wire(f):
            proc = f.root / 'proc'
            proc.mkdir(exist_ok=True)
            f.space.update(probe=P, kinds=K, remover=R, proc=str(proc),
                keep=KP.keeper(f.ledger), owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                run=lambda argv, cwd=None: (0, '') if argv[0] == 'docker' else P._run(argv, cwd))

        def git(path, *args):
            return subprocess.run(['git', '-C', str(path), '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', *args], capture_output=True, check=True).stdout.decode().strip()

        def worktree(f):
            git(f.repo, 'init', '-q')
            (f.repo / 'source').write_text('original\n')
            git(f.repo, 'add', '.')
            git(f.repo, 'commit', '-q', '-m', 'fixture')
            tree = Path(f.ledger.projects[0]['worktree_root']) / 'review'
            tree.parent.mkdir(parents=True)
            git(f.repo, 'worktree', 'add', '-q', '-b', 'review', str(tree))
            return tree

        def run(f, free=19, text='No space left on device', code=1, tree=None, stream='stderr', artifact=False):
            contract = f.offer()
            identity = dict(platform='linux', host='fixture', boot_id='fixture', pid=os.getpid(), start='1')
            digest, did = D.digest(contract), contract['dispatch_id']
            f.dispatches.accept(did, digest, dict(identity, principal='runner'), now=time.time())
            f.dispatches.run(did, digest, identity, now=time.time())
            directory = f.root / 'scratch' / ('run-' + did.rsplit('/', 1)[1])
            directory.mkdir(parents=True)
            owner = {'scope': f.scope, 'run': {'id': did, 'station': 'review'}}
            item = A.accepted(f.ledger.declare('scratch', {'path': str(directory)}, owner, 'seam', pool='host'))['item']
            A.accepted(f.ledger.confirm(item))
            tree_item = None
            if tree is not None:
                tree_item = A.accepted(f.ledger.declare('worktree', {'path': str(tree)}, owner, 'seam', pool='host'))['item']
                A.accepted(f.ledger.confirm(tree_item))
            receiver = object.__new__(L.Receiver)
            receiver.space, receiver.dispatches, receiver.config = f.space, f.dispatches, {}
            receiver.run, receiver.run_dispatch = str(directory), did
            receiver.space_run = {'worktree': str(tree) if tree else None, 'owner': owner}
            receiver.run_census, receiver.run_end, receiver.run_removal = None, None, None
            receiver.role_skills, receiver.run_sent = [], False
            receiver.metering, receiver.recorder, receiver.committed = None, None, None
            receiver.control, receiver._exit_group = None, None
            receiver.events = []
            receiver.emit = receiver.events.append
            program = 'import sys; sys.stdin.read(); '
            if tree:
                program += 'from pathlib import Path; Path(' + repr(str(tree / 'notes')) + ').write_text("unfinished work"); '
            program += 'print(' + repr(text) + ',file=sys.' + stream + '); sys.exit(' + str(code) + ')'
            worker = subprocess.Popen([sys.executable, '-c', program], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                termination = receiver._reap(worker, contract, process=identity, contract_digest=digest)
                f.free['host'] = free
                order = []
                original_free = f.space['free']
                def read(pool):
                    order.append(('free', f.dispatches.record(did)['state']))
                    return original_free(pool)
                f.space['free'] = read
                if artifact:
                    receiver.metering = types.SimpleNamespace(settle=lambda *args: None,
                        report={'verdict': 'failed', 'complete': False, 'digest': 'sha256:' + 'c' * 64})
                with patch.object(L, 'run_end_scan', lambda *args: None):
                    receiver._finish(termination, contract, digest, identity, False)
                f.space['free'] = original_free
                return f.dispatches.record(did), receiver, tree_item, order
            finally:
                if worker.poll() is None:
                    worker.kill()
                worker.wait()

        def line(f):
            result = object.__new__(SV.Line)
            result.repository, result.runner, result.gate = 'repository', f.runner, f.gate
            result.service = types.SimpleNamespace(domain='domain', conn=f.conn)
            result._rows = lambda kind: [json.loads(row[0]) for row in f.conn.execute(
                'SELECT data FROM entities WHERE kind=?', (kind,))]
            result.invocation = lambda identity: None
            return result

        def report():
            return {name: [] for name in ('stopped', 'asked', 'waiting', 'offered', 'refused')}

        try:
            for mode in (True, False):
                f = fixture('confirmed-' + str(mode), act=mode)
                wire(f)
                record, receiver, _, order = run(f)
                end = record.get('space_end') or {}
                check('ac1/refunded', 'confirmed classification and taxon', end.get('classification') ==
                      'environment_failure:no_space' and end.get('class') == 'unavailable_service')
                check('ac1/refunded', 'no failed attempt charged', f.dispatches.attempts('unit', 'review') == 0)
                check('ac1/refunded', 'environment failure is not a measured finished run',
                      A.finished(f.ledger, 'project', 'review') == [])
                check('ac1/order', 'snapshot before exit and cleanup', order[:2] == [('free', 'running')] * 2)
                check('ac1/order', 'snapshot keeps both pools', end.get('pools') == [
                    {'pool': 'host', 'free': 19, 'floor': 20}, {'pool': 'image', 'free': 1000, 'floor': 10}])
                check('ac1/order', 'end conclusive and hold released', record['state'] == 'exited'
                      and f.dispatches.active('unit', 'review') is None
                      and f.ledger.hold(record['contract']['space']['hold'])['state'] == 'released')
                raw_end = {key: end[key] for key in ('classification', 'class', 'pools', 'worktree')}
                f.dispatches.exit(record['dispatch_id'], D.digest(record['contract']), record['process'],
                    record['termination'], now=record['history'][-1]['at'], space_end=raw_end)
                check('ac1/replayed-end', 'replayed exit never refunds twice',
                      f.dispatches.attempts('unit', 'review') == 0
                      and f.dispatches.record(record['dispatch_id']) == record)
                if mode:
                    one = line(f)
                    calls = []
                    one.rerun = lambda rec, rep: calls.append(refused(f.offer))
                    one.limited(record, report())
                    check('ac1/behind-admission', 'repeat waits before new record', len(calls) == 1
                          and calls[0][0] is None and getattr(calls[0][1], 'code', '') == 'space_wait:host'
                          and len(one._rows('dispatch')) == 1 and f.dispatches.attempts('unit', 'review') == 0)
                    before = len(f.reads)
                    f.free['host'] = 10000
                    refused(f.offer)
                    check('ac1/behind-admission', 'manual free does not poll', len(f.reads) == before)
                    A.accepted(f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS}))
                    next_contract = f.offer()
                    check('ac1/behind-admission', 'marked retry keeps attempt number', next_contract['attempt'] == 1)

            f = fixture('quoted-error')
            wire(f)
            first, _, _, _ = run(f, free=10000, text='test quoted ENOSPC; assertion failed for another reason', stream='stdout', artifact=True)
            one, offers = line(f), []
            one.space_andon = lambda *args: None
            def repeat(record, rep):
                offers.append(run(f, free=10000, text='test quoted ENOSPC; assertion failed for another reason', artifact=True)[0])
            one.rerun = repeat
            one.limited(first, report())
            check('ac2/repeat-once', 'first unknown and repeated once', (first.get('space_end') or {}).get('classification') ==
                  'unknown_outcome:no_space_unconfirmed' and len(offers) == 1 and first['artifact'] is None)
            if offers:
                second = offers[0]
                one.limited(second, report())
                check('ac2/repeat-once', 'second records the red without a third run', len(offers) == 1
                      and second['termination']['returncode'] == 1 and not D.completed(second)
                      and not (second.get('space_end') or {}).get('retry')
                      and f.dispatches.attempts('unit', 'review') == 2 and (second.get('artifact') or {}).get('verdict') == 'failed')
                check('ac2/restart', 'latest finds repeat', one.latest()[('unit', 'review')]['dispatch_id'] == second['dispatch_id'])

            for name, free, text, code, classification in (
                ('floor', 20, 'ENOSPC', 1, 'unknown_outcome:no_space_unconfirmed'),
                ('success', 1, 'ENOSPC', 0, None),
                ('ordinary', 1, 'assertion failed', 1, None)):
                f = fixture(name)
                wire(f)
                record, _, _, _ = run(f, free=free, text=text, code=code)
                check('classification/' + name, 'result', (record.get('space_end') or {}).get('classification') == classification)
            f = fixture('artifact-incomplete')
            wire(f)
            record, receiver, _, _ = run(f, code=0, artifact=True)
            check('classification/incomplete', 'failed artifact is not a successful end',
                  (record.get('space_end') or {}).get('classification') == 'environment_failure:no_space'
                  and not D.completed(record) and not any(e['event'] == 'artifact' for e in receiver.events))
            scanner = A.NoSpaceOutput()
            scanner.feed('stdout', b'No space left ')
            scanner.feed('stderr', b'on device')
            check('classification/streams', 'streams cannot fabricate a token', not scanner.found)
            scanner.feed('stdout', b'on device')
            check('classification/streams', 'split token retained', scanner.found)
            f.space['free'] = lambda pool: (_ for _ in ()).throw(OSError('unread'))
            outcome = A.classify_end(f.space, {'returncode': 1}, True)
            check('classification/unread', 'unread never confirms', outcome['classification'] == 'unknown_outcome:no_space_unconfirmed')

            f = fixture('kept-review')
            wire(f)
            tree = worktree(f)
            record, receiver, item, _ = run(f, tree=tree)
            check('ac3/work-retained', 'review scratch stays with exact edit', (tree / 'notes').is_file()
                  and (tree / 'notes').read_text() == 'unfinished work' and f.ledger.item(item)['state'] == 'deferred'
                  and (f.ledger.item(item).get('deferral') or {}).get('rule') == 'unique_work')
            # Reconstruct the rule module to model later retirement or reconnect; the stop is durable.
            signal_again = load('signal_again', mods / 'control_space_signal.py')
            answer = signal_again.signal(f.ledger, 'run_finished', {'run': record['dispatch_id']},
                                         **{k: v for k, v in f.space.items() if k != 'ledger'})
            check('ac3/reconnect', 'later removal retains edit', answer['ok'] and (tree / 'notes').is_file())
            f.free['host'] = 10000
            contract = f.offer()
            recovery = contract['input']['payload'].get('space_recovery') or {}
            check('ac3/next-brief', 'prepared brief identifies kept work', str(tree) in recovery.get('worktrees', [])
                  and 'uncommitted changes' in recovery.get('brief', '') and str(tree) in recovery.get('brief', ''))
            check('ac3/next-brief', 'brief covered by payload digest', D.digest(contract['input']['payload']) == contract['input']['payload_digest'])

            f = fixture('bounded')
            wire(f)
            first, _, _, _ = run(f)
            f.free['host'] = 10000
            second, _, _, _ = run(f)
            one = line(f)
            check('ac4/two-stop', 'two uncharged ends', f.dispatches.attempts('unit', 'review') == 0)
            check('ac4/two-stop', 'durable andon', (second.get('space_end') or {}).get('andon') is True
                  and (second.get('space_end') or {}).get('consecutive') == 2)
            check('ac4/two-stop', 'equal attempt latest is newest', one.latest()[('unit', 'review')]['dispatch_id'] == second['dispatch_id'])
            repeated, wakes = [], []
            consumer = CON.Consumer(f.ledger)
            one.service.space_consumer = consumer
            one.loop = types.SimpleNamespace(wake=lambda *args: wakes.append(args))
            def inbox(repo):
                return types.SimpleNamespace(read=lambda identity: one.service.conn.execute(
                    "SELECT data FROM entities WHERE id=?", (identity,)).fetchone())
            one.service.inbox = inbox
            def notice(inbox, alias, unit, brief, choices, subject, key):
                data = dict(unit=unit, brief=brief, subject=subject, pid=os.getpid())
                assert one.service.conn is f.ledger.conn
                encoded = json.dumps(data, sort_keys=True)
                one.service.conn.execute('INSERT INTO entities(id,kind,version,digest,data) VALUES(?,?,?,?,?)',
                    (SV.I.assignment_id('repository', alias), 'fixture_notice', 1, D.digest(data), encoded))
                one.service.conn.commit()
                return 'owner', {'ok': True}
            one.open_question = notice
            def unbounded(*args):
                f.free['host'] = 10000
                repeated.append(run(f)[0])
            one.rerun = unbounded
            for _ in range(3):
                one.limited(second, report())
            while consumer.active:
                poller = select.poll()
                poller.register(consumer.active[0], select.POLLIN | select.POLLHUP)
                if not poller.poll(10000):
                    raise RuntimeError('owner notice worker did not complete')
                consumer.readable(consumer.active[0])
            one.limited(second, report())
            notices = [json.loads(raw) for (raw,) in f.conn.execute("SELECT data FROM entities WHERE kind='fixture_notice'")]
            check('ac4/two-stop', 'one owner notice and no third repeat', len(notices) == 1 and not repeated)
            check('ac4/off-loop', 'delivery in worker and completion wakes', len(notices) == 1
                  and notices[0]['pid'] != os.getpid() and len(wakes) == 1)
            consumer.stop()
            consumer = None
            f.free['host'] = 10000
            contract, error = refused(f.offer)
            check('ac4/two-stop', 'direct prepare also stops before reservation', contract is None
                  and getattr(error, 'code', '') == 'environment_failure:no_space:andon')
            check('ac4/two-stop', 'only two dispatch records exist', len(one._rows('dispatch')) == 2)

            f = fixture('consecutive-reset')
            wire(f)
            run(f)
            f.free['host'] = 10000
            run(f, free=10000, text='ordinary failed test')
            f.free['host'] = 10000
            third, _, _, _ = run(f)
            check('ac4/reset', 'ordinary end breaks consecutive failures', (third.get('space_end') or {}).get('consecutive') == 1
                  and not (third.get('space_end') or {}).get('andon'))
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            if consumer is not None:
                consumer.stop()
            for f in fixtures:
                f.close()
        for row, checks in sorted(rows.items()):
            bad = '; '.join(label for label, good in checks if not good)
            if bad:
                print('DETAIL space317/' + row + ': ' + bad)
            good = bool(checks) and all(good for _, good in checks)
            print('ROW space317/' + row + ': ' + ('passed' if good else 'failed'))
            expect('space317/' + row, good)


_v317_suite()
