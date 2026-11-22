"""VELDO-0359 B1: fixture-only query journey, scope, lifecycle and switch.

Real signed workspace bindings, SQLite transactions and Unix sockets. No engine,
confinement or live store. Lifecycle launch prerequisites use explicit stand-ins;
the production Receiver.launch/acceptance and Runner reaping paths remain in use.
Synchronization is by events, pipes and process exit; deadlines detect hangs only.
"""


def _v359_query_suite():
    import contextlib
    import copy
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import selectors
    import shutil
    import signal
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_run_query.py': ROOT / ".veldo" / "control_run_query.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'frontier.py': ROOT / ".veldo" / "frontier.py",
        'runstatus.py': ROOT / ".veldo" / "runstatus.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    rows = {k: [] for k in ('query/journey', 'query/scope', 'query/lifecycle', 'switch/off', 'paths/canon')}

    def check(row, label, value):
        rows[row].append((label, bool(value)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def stable(value):
        if isinstance(value, dict):
            return {k: stable(v) for k, v in value.items()
                    if k not in ('decision_id', 'follows', 'at', 'oldest_pending_age_seconds')}
        if isinstance(value, (tuple, list)):
            return [stable(v) for v in value]
        return value

    def stopped(fn):
        try:
            fn()
            return None
        except Exception as error:
            return getattr(error, 'code', getattr(error, 'reason', type(error).__name__))

    with tempfile.TemporaryDirectory(prefix='v359-', dir='/tmp') as directory, contextlib.ExitStack() as stack:
        base = Path(directory)
        mods = base / 'repo' / '.veldo'
        mods.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        Q = load('v359_query', mods / 'control_run_query.py')
        EL = Q.EL
        L = load('v359_launch', mods / 'control_launch.py')
        S = L.S
        runtime = base / 'rt'
        runtime.mkdir()
        stack.enter_context(patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(runtime)}))
        os.environ.pop('VELDO_RUN_QUERY', None)
        GP = EL._organ('git_process')
        host = base / 'host'
        host.mkdir()
        key = host / 'key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True, capture_output=True)
        public = key.with_suffix('.pub').read_text().split()[:2]
        signers = host / 'signers'
        signers.write_text('fixture namespaces="veldo-enrollment" %s\n' % ' '.join(public))
        trust_path = host / 'trust.json'
        trust_path.write_text(json.dumps(dict(schema=EL.HOST_TRUST_SCHEMA, host_identity='fixture-host',
                                             enrollment_signers=str(signers))))
        trust = EL.load_host_trust(str(trust_path))
        db = base / 'store' / 'fixture.sqlite3'
        writer = S.open_store(str(db))
        stack.callback(writer.close)
        serial = [0]
        written = {}

        def put(identity, kind, data):
            serial[0] += 1
            version = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            S.execute(writer, dict(command_id='c%d' % serial[0], principal='fixture', operation='upsert_entity',
                                  nonce='n%d' % serial[0], artifact_digests=[],
                                  expected_versions={identity: version[0] if version else 0},
                                  parameters=dict(entity_id=identity, kind=kind, data=data)),
                      'fixture', lambda body: 'fixture-signature', 1)
            written[identity] = copy.deepcopy(data)

        def enroll(repo, repository):
            repo.mkdir(exist_ok=True)
            GP.run(['git', '-C', str(repo), 'init', '-q'], check=True, capture_output=True)
            GP.run(['git', '-C', str(repo), 'commit', '-q', '--allow-empty', '-m', 'fixture'],
                   identity=('Fixture', 'fixture@example.invalid'), check=True, capture_output=True)
            def sign(body):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-enrollment'],
                                      input=body, check=True, capture_output=True).stdout.decode()
            EL.E.enroll(str(repo), 'domain', 'fixture-store', str(db), 'fixture-host', 1, sign, 'fixture',
                        '2026-01-01T00:00:00Z', repository_uuid=repository)
            return dict(store=str(db), workspace=str(repo), domain='domain', repository=repository,
                        authority_generation=1, host_trust=str(trust_path), principal='fixture', journal_key=str(key))

        repo = mods.parent
        config = enroll(repo, 'repo-one')
        other_repo = base / 'other'
        other_config = enroll(other_repo, 'repo-two')
        (repo / 'specs').mkdir()
        (repo / 'plans').mkdir()
        plan = repo / 'plans' / 'PLAN-9359-fixture.md'
        plan.write_text('---\nschema: veldo.plan/v1\nid: PLAN-9359\ntitle: Fixture\nstatus: ready\nrevision: 1\n'
                        'work:\n  - item: W1\n    spec: VELDO-9359\n    order: 1\n---\nFixture.\n')
        for unit in ('VELDO-9359', 'VELDO-9360'):
            (repo / 'specs' / (unit + '-fixture.md')).write_text(
                '---\nschema: veldo.spec/v1\nid: %s\ntitle: Fixture\nstatus: ready\nrisk: low\n'
                'owner: fixture\nlane: standalone\ndepends_on: []\n---\nFixture.\n' % unit)
            put(unit, 'execution_unit', dict(repository_uuid='repo-one', revision=1, state='READY',
                    backlog_item_uuid='backlog:' + unit, project='fixture', plan='PLAN-9359',
                    depends_on=[] if unit == 'VELDO-9359' else ['absent-dependency'], scope_digest='sha256:scope',
                    producer='builder', approvals_required=[], sentinel='BODY_MUST_STAY_SERVER_SIDE'))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid='repo-one'))
            put('admission:' + unit, 'admission', dict(state='accepted', unit=unit, scope_digest='sha256:scope'))
        put('foreign', 'execution_unit', dict(repository_uuid='repo-two', revision=1, project='fixture', state='READY'))
        put('member', 'membership', dict(principal_type='person', roles=['project_owner'], status='active', scope=['fixture']))
        put('project:fixture', 'project', dict(name='fixture'))
        put('plan:PLAN-9359', 'plan', dict(status='ready', revision=1))
        put('authority:domain', 'authority', dict(state='active', generation=1))
        put('bad-settlement', 'decision_settlement', {'decision': []})
        put('decision:foreign', 'decision', dict(decision_id='foreign', blocks=['foreign']))
        put('decision:local', 'decision', dict(decision_id='local', blocks=['VELDO-9360']))

        logs = []
        server = Q.Server(config, 'journey', logs.append).start()
        stack.callback(server.close)
        remote_events, direct_events = [], []
        remote = Q.RemoteGate(repo, server.path, remote_events.append)
        direct = EL.enrolled_gate(repo, trust, direct_events.append)
        stack.callback(direct.close)
        stack.callback(remote.close)
        # The same production entries obtain the remote through the enrolled constructor.
        stack.enter_context(patch.dict(os.environ, {Q.VARIABLE: str(server.path)}))
        built = EL.entry_gate(repo, observe=remote_events.append)
        check('query/journey', 'entry uses remote and wired gate passes through',
              built.repository_uuid == 'repo-one' and not hasattr(built, 'conn')
              and EL.entry_gate(repo, direct) is direct)
        built.close()
        client_opens = []
        original_connect = sqlite3.connect
        client_thread = threading.get_ident()

        def no_client_store(database, *args, **kwargs):
            if threading.get_ident() == client_thread and str(db) in str(database):
                client_opens.append(str(database))
                raise sqlite3.OperationalError('fixture store inaccessible to client')
            return original_connect(database, *args, **kwargs)

        def compare(label, fn):
            direct_events.clear()
            remote_events.clear()
            a, b = fn(direct), fn(remote)
            check('query/journey', label, stable(a) == stable(b) and stable(direct_events) == stable(remote_events))
            return b

        with patch.object(sqlite3, 'connect', no_client_store):
            for station in EL.STATION_PREDICATES:
                compare('station ' + station, lambda gate, station=station: gate.decide(station, 'VELDO-9359', context={'holder': 'builder', 'reviewer': 'reviewer'}))
            compare('missing dependency held', lambda gate: gate.decide('direct_execution', 'VELDO-9360'))
            compare('missing unit held', lambda gate: gate.decide('selection', 'missing'))
            compare('inline decision references', lambda gate: gate.decision_blockers('VELDO-9360', ['decision:local']))
            compare('completion missing', lambda gate: gate.completion('missing'))
            compare('completion', lambda gate: gate.completion('VELDO-9359'))
            compare('landed', lambda gate: gate.landed('VELDO-9359'))
            compare('floor ready', lambda gate: gate.floor_entry('VELDO-9359', 'ready'))
            compare('floor absent review', lambda gate: gate.floor_entry('missing', 'review'))
            decision = compare('build admission', lambda gate: gate.decide('direct_execution', 'VELDO-9359'))
            check('query/journey', 'build reached', decision['eligible'])
            ticket = remote.decide('selection', 'VELDO-9359')
            put('admission:VELDO-9359', 'admission', dict(written['admission:VELDO-9359'], state='held'))
            changed = compare('committed change and stale ticket', lambda gate: gate.decide('direct_execution', 'VELDO-9359', ticket=ticket))
            check('query/journey', 'fresh state', 'stale_input:admission' in changed['refusals'] and not changed['eligible'])
            put('admission:VELDO-9359', 'admission', dict(written['admission:VELDO-9359'], state='accepted'))
            PL = load('v359_plan', mods / 'plan.py')
            FR = load('v359_frontier', mods / 'frontier.py')
            WS = load('v359_work_state', mods / 'work_state.py')
            RS = load('v359_status', mods / 'runstatus.py')
            EX = load('v359_executor', mods / 'executor.py')

            def output(fn):
                capture = io.StringIO()
                with contextlib.redirect_stdout(capture):
                    rc = fn()
                return rc, capture.getvalue()

            compare('plan run-check', lambda gate: output(lambda: PL.cmd_run_check(str(plan), 'VELDO-9359', eligibility=gate)))
            compare('plan bundle', lambda gate: output(lambda: PL.cmd_bundle(str(plan), 'VELDO-9359', eligibility=gate)))
            check('query/journey', 'plan hash', output(lambda: PL.cmd_hash(str(plan)))[0] == 0)
            compare('frontier claimable and offers', lambda gate: FR.claimable(repo_root=repo, eligibility=gate))
            compare('frontier withheld and observations', lambda gate: FR.withheld(repo_root=repo, eligibility=gate))
            compare('completion_view explicit gate', lambda gate: WS.completion_view(['VELDO-9359', 'missing'], root=repo, eligibility=gate))
            executor = EX.Executor(types.SimpleNamespace(reviewer_identity='reviewer'), context={'holder': 'builder'})
            compare('executor context and ticket', lambda gate: executor._decide(gate, 'VELDO-9359', 'review', ticket))
            compare('replication', lambda gate: remote.replication_status() if gate is remote else
                    Q._organ('control_replica').replication_status(direct.conn, S, time.time()))
            check('query/journey', 'status authority override', RS._replication(repo, time.time(), str(db), remote)['present'])
            check('query/journey', 'status default replica', RS._replication(repo, time.time(), eligibility=remote)['present'] is False)
            for path in (db.parent / 'another.sqlite3', db.parent / 'sidecar'):
                check('query/scope', 'status refuses other store paths',
                      RS._replication(repo, time.time(), str(path), remote) ==
                      {'present': False, 'reason': 'coordinate_not_served:store_override'})
            alias = base / 'alias.sqlite3'
            alias.symlink_to(db)
            check('query/journey', 'status resolves own override alias', RS._replication(repo, time.time(), str(alias), remote)['present'])

        # Coordination uses the accepted pm cycle, not the execution-unit check.
        PM = Q._organ('control_workflow_cycle_pm')
        put('team:fixture', 'team', {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'})
        put('snapshot', 'snapshot', {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'})
        put('manager', 'membership', dict(principal_type='person', roles=['project_owner'], status='active', scope=['fixture']))
        cycle = dict(project='fixture', domain='domain', repository='repo-one', state='running', manager='manager',
                     snapshot=PM.ref(PM.row(writer, 'snapshot')), team=PM.ref(PM.row(writer, 'team:fixture')),
                     configuration={}, accepted_commit='fixture')
        put('cycle', 'pm_cycle', cycle)
        put('foreign-cycle', 'pm_cycle', dict(cycle, repository='repo-two'))
        coordination = compare('valid coordination', lambda gate: gate.decide('coordination', 'cycle', context={'holder': 'manager'}))
        check('query/journey', 'coordination eligible', coordination['eligible'])
        put('cycle', 'pm_cycle', dict(cycle, accepted_commit='changed'))
        stale = compare('coordination stale ticket', lambda gate: gate.decide('coordination', 'cycle', context={'holder': 'manager'}, ticket=coordination))
        check('query/journey', 'coordination stale named', 'stale_input:coordination' in stale['refusals'])
        missing = compare('missing cycle', lambda gate: gate.decide('coordination', 'missing-cycle'))
        check('query/journey', 'missing cycle named', missing['refusals'] == ['missing_authority:pm_cycle'])
        for unit in ('foreign', 'member', 'cycle'):
            for fn in (lambda unit=unit: remote.decide('selection', unit), lambda unit=unit: remote.completion(unit),
                       lambda unit=unit: remote.floor_entry(unit, 'ready'), lambda unit=unit: remote.decision_blockers(unit)):
                check('query/scope', 'work scope ' + unit, stopped(fn) == 'coordinate_not_served')
        for unit in ('foreign-cycle', 'VELDO-9359'):
            check('query/scope', 'coordination scope ' + unit,
                  stopped(lambda: remote.decide('coordination', unit)) == 'coordinate_not_served')
        check('query/scope', 'foreign reference', stopped(lambda: remote.decision_blockers('VELDO-9359', ['decision:foreign'])) == 'coordinate_not_served')
        check('query/scope', 'other checkout', stopped(lambda: Q.RemoteGate(other_repo, server.path)) == 'run_query:other_repository')
        for name in ('conn', '_reading', 'unit_record', 'read', 'open_dispatch', 'launch', 'handle', 'close_dispatch', 'dispatch'):
            check('query/scope', 'unsupported ' + name, stopped(lambda: getattr(remote, name)) == 'run_query:unsupported:' + name
                  and not hasattr(remote, name))
        for operation in ('sql', 'landed', 'launch', 'read', 'dispatch'):
            check('query/scope', 'unlisted ' + operation,
                  stopped(lambda: Q._exchange(server.path, {'operation': operation})) == 'coordinate_not_served')
        second = Q.Server(other_config, 'second').start()
        stack.callback(second.close)
        other = Q.RemoteGate(other_repo, second.path)
        check('query/scope', 'two concurrent repositories', other.decide('selection', 'foreign')['inputs']['unit']['id'] == 'foreign'
              and remote.decide('selection', 'VELDO-9359')['inputs']['unit']['id'] == 'VELDO-9359')
        check('query/scope', 'second cannot query first', stopped(lambda: other.completion('VELDO-9359')) == 'coordinate_not_served')
        answer = remote.decide('selection', 'VELDO-9359')
        check('query/scope', 'frozen decisions and identities', set(answer) == set(Q.DECISION)
              and all(set(v) == ({'members', 'digest'} if 'members' in v else {'id', 'version', 'digest', 'definition'})
                      for v in answer['inputs'].values()) and 'BODY_MUST_STAY_SERVER_SIDE' not in json.dumps(answer))
        check('query/scope', 'frozen completion floor replication', set(remote.completion('VELDO-9359')) == set(Q.FACTS)
              and set(remote.floor_entry('VELDO-9359', 'ready')) == set(Q.FLOOR)
              and set(remote.replication_status()) == set(Q.REPLICATION))
        check('query/scope', 'counts log only request and outcome', bool(logs) and all(set(v) == {'event', 'request', 'outcome'} for v in logs))
        # Read-only connection, created on the serving thread; a request never leaves a transaction.
        probes = []
        real_answer = Q._answer
        def inspect_reader(gate, request):
            probes.append(dict(thread=threading.get_ident(), transaction=gate.conn.in_transaction,
                               write=stopped(lambda: gate.conn.execute('CREATE TABLE forbidden(x)'))))
            return real_answer(gate, request)
        with patch.object(Q, '_answer', inspect_reader):
            Q._exchange(server.path, {'operation': 'hello'})
        probe = probes[0]
        check('query/scope', 'thread owns read-only transaction', probe['thread'] != client_thread and probe['transaction']
              and probe['write'] == 'OperationalError')
        check('query/journey', 'zero client opens', not client_opens)

        # Dead endpoint and malformed/timeout transport never fall back to a store open.
        with patch.object(sqlite3, 'connect', no_client_store):
            server.close()
            check('query/scope', 'dead receiver', stopped(lambda: remote.completion('VELDO-9359')) == 'unavailable_service:run_query')
            check('query/lifecycle', 'run endpoint removed', not server.path.parent.exists())
            accepted, release = threading.Event(), threading.Event()
            fake_path = runtime / 'fake.sock'
            fake = socket.socket(socket.AF_UNIX)
            fake.bind(str(fake_path))
            fake.listen()
            def stall():
                with fake.accept()[0] as client:
                    accepted.set()
                    release.wait(10)
            worker = threading.Thread(target=stall)
            worker.start()
            try:
                with patch.object(Q, 'SECONDS', .1):
                    check('query/scope', 'transport deadline', stopped(lambda: Q.RemoteGate(repo, fake_path)) == 'unavailable_service:run_query')
                check('query/scope', 'transport connected before timeout', accepted.is_set())
            finally:
                release.set()
                worker.join(10)
                fake.close()
                fake_path.unlink()
            check('query/scope', 'no attempted fallback', not client_opens)
            with patch.dict(os.environ, {Q.VARIABLE: ''}):
                check('query/journey', 'unset query falsifier reaches refused direct open',
                      stopped(lambda: EL.entry_gate(repo, trust=trust)) == 'unavailable_service:store' and len(client_opens) == 1)

        # Creation/readiness failures, exclusive ownership, no startup sweep.
        collision = Q.endpoint('collision')
        collision.parent.mkdir()
        (collision.parent / 'keep').write_text('existing owner')
        check('query/lifecycle', 'exclusive creation refuses and preserves other owner',
              stopped(lambda: Q.Server(config, 'collision').start()) == 'unavailable_service:run_query'
              and (collision.parent / 'keep').read_text() == 'existing owner')
        for method in ('bind', 'listen'):
            candidate = Q.Server(config, method)
            with patch.object(socket.socket, method, side_effect=OSError('fixture')):
                check('query/lifecycle', method + ' failure', stopped(candidate.start) == 'unavailable_service:run_query')
            check('query/lifecycle', method + ' cleanup', not candidate.path.parent.exists())
        for failure in ('connection', 'ready'):
            candidate = Q.Server(config, failure)
            opened, unblock = threading.Event(), threading.Event()
            def delayed_gate():
                opened.set()
                unblock.wait(10)
                raise OSError('fixture readiness')
            if failure == 'connection':
                with patch.object(candidate, '_gate', side_effect=OSError('fixture connection')):
                    check('query/lifecycle', 'connection failure', stopped(candidate.start) == 'unavailable_service:run_query')
            else:
                result = []
                with patch.object(candidate, '_gate', side_effect=delayed_gate), patch.object(Q, 'SECONDS', .1):
                    starter = threading.Thread(target=lambda: result.append(stopped(candidate.start)))
                    starter.start()
                    assert opened.wait(10)
                    starter.join(10)
                    unblock.set()
                    candidate.thread.join(10)
                check('query/lifecycle', 'ready deadline', result == ['unavailable_service:run_query'])
            check('query/lifecycle', failure + ' cleanup', not candidate.path.parent.exists())
        bound, listen = threading.Event(), threading.Event()
        first = Q.Server(config, 'paused-A')
        real_listen = socket.socket.listen
        def pause_listen(sock, *args):
            if sock.getsockname() == str(first.path):
                bound.set()
                assert listen.wait(10)
            return real_listen(sock, *args)
        results = []
        with patch.object(socket.socket, 'listen', pause_listen):
            starter = threading.Thread(target=lambda: results.append(stopped(first.start)))
            starter.start()
            assert bound.wait(10)
            later = Q.Server(other_config, 'starting-B').start()
            check('query/lifecycle', 'A survives B startup', first.path.exists())
            listen.set()
            starter.join(10)
        check('query/lifecycle', 'A answers after listen', results == [None]
              and stopped(lambda: Q.RemoteGate(repo, first.path).completion('missing')) is None)
        first.close()
        later.close()
        leftover = Q.endpoint('dead-receiver-and-runner')
        leftover.parent.mkdir()
        stale = socket.socket(socket.AF_UNIX)
        stale.bind(str(leftover))
        stale.close()
        later = Q.Server(config, 'new-dispatch').start()
        check('query/lifecycle', 'leftover does not affect next launch', leftover.exists()
              and Q.RemoteGate(repo, later.path).repository_uuid == 'repo-one')
        later.close()

        marker = db.parent / 'store-guard.off'
        check('switch/off', 'absent means on', Q.switch(db)['state'] == 'on')
        marker.write_text('off')
        before = marker.read_bytes()
        for mode, body in ((0o000, ''), (0o600, 'arbitrary contents')):
            marker.chmod(0o600)
            marker.write_text(body)
            marker.chmod(mode)
            check('switch/off', 'mode and contents ignored', Q.switch(db)['state'] == 'off')
        marker.chmod(0o600)
        check('switch/off', 'status OFF', 'store guard: OFF' in RS.render_text({'store_guard': RS._store_guard(repo)}))
        marker.unlink()
        for invalid in ('symlink', 'directory', 'owner', 'stat'):
            if invalid == 'symlink':
                marker.symlink_to(db)
            elif invalid == 'directory':
                marker.mkdir()
            elif invalid == 'owner':
                marker.write_text('fixture')
            if invalid == 'owner':
                with patch.object(Q.os, 'getuid', return_value=os.getuid() + 1):
                    sample = Q.switch(db)
            elif invalid == 'stat':
                with patch.object(Path, 'lstat', side_effect=PermissionError('fixture')):
                    sample = Q.switch(db)
            else:
                sample = Q.switch(db)
            check('switch/off', invalid + ' named refusal', sample['state'] == 'invalid' and sample['reason'] == 'invalid_input:layout:switch')
            if invalid == 'directory':
                marker.rmdir()
            elif invalid != 'stat':
                marker.unlink()
        check('switch/off', 'status on', 'store guard: on' in RS.render_text({'store_guard': RS._store_guard(repo)}))
        check('paths/canon', 'both trees', all((ROOT / 'engine/.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                                           for name in PRODUCTION))
        check('paths/canon', 'scaffold module list', '".veldo/control_run_query.py"' in (mods / 'init_scaffold.py').read_text())

    for row, checks in rows.items():
        failures = [name for name, ok in checks if not ok]
        expect('v359 ' + row + ': ' + ('PASS' if not failures else '; '.join(failures)), bool(checks) and not failures)


_v359_query_suite()
