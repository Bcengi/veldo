"""VELDO-0359 B1: fixture-only query journey, scope, lifecycle and switch.

Real signed workspace bindings, SQLite transactions and Unix sockets. No engine,
confinement or live store. Lifecycle launch prerequisites use explicit stand-ins;
the production Receiver.launch/acceptance and Runner reaping paths remain in use.
Synchronization is by events, pipes and process exit. HANG is the one hang detector
(120 s); no row's result depends on a deadline being met. The protocol's own deadline
is raised to HANG everywhere except in the two rows that exercise its refusal.
"""


def _v359_query_suite():
    import contextlib
    import copy
    import importlib.machinery
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
    rows = {k: [] for k in ('query/journey', 'query/scope', 'query/lifecycle', 'query/cost', 'switch/off',
                            'paths/canon')}
    HANG = 120  # seconds: detects a hang, never decides a row

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
                    if k not in ('decision_id', 'follows', 'offer', 'selection', 'at', 'oldest_pending_age_seconds')}
        if isinstance(value, (tuple, list)):
            return [stable(v) for v in value]
        return value

    def stopped(fn):
        try:
            fn()
            return None
        except Exception as error:
            return getattr(error, 'code', getattr(error, 'reason', type(error).__name__))

    with tempfile.TemporaryDirectory(prefix='v359-', dir=fast_temp()) as directory, contextlib.ExitStack() as stack:
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
        # The run-side client is the copy the entry gate loads once and keeps.
        QC = EL._late('control_run_query')
        for module in (Q, QC, L.RQ):
            stack.enter_context(patch.object(module, 'SECONDS', HANG))
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

        journey_log = base / 'records' / 'journey.query.log'
        server = Q.Server(config, 'journey', log=str(journey_log)).start()
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

        operations = set()

        def compare(label, fn):
            direct_events.clear()
            remote_events.clear()
            a, b = fn(direct), fn(remote)
            operations.update(e.get('operation') for e in remote_events)
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

            run_check = compare('plan run-check', lambda gate: output(lambda: PL.cmd_run_check(str(plan), 'VELDO-9359', eligibility=gate)))
            check('query/journey', 'plan run-check reaches build', run_check[0] == 0)
            compare('plan bundle', lambda gate: output(lambda: PL.cmd_bundle(str(plan), 'VELDO-9359', eligibility=gate)))
            check('query/journey', 'plan hash', output(lambda: PL.cmd_hash(str(plan)))[0] == 0)
            compare('frontier claimable and offers', lambda gate: FR.claimable(repo_root=repo, eligibility=gate))
            compare('frontier withheld', lambda gate: FR.withheld(repo_root=repo, eligibility=gate))
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
        check('query/scope', 'oversized context', stopped(lambda: remote.decide('selection', 'VELDO-9359', context={'body': 'x' * Q.MAX_BYTES})) == 'unavailable_service:run_query')
        check('query/scope', 'extra path refused', stopped(lambda: Q._exchange(server.path, {'operation': 'completion', 'unit': 'VELDO-9359', 'path': str(db)})) == 'coordinate_not_served')
        check('query/scope', 'immutable coordinates', stopped(lambda: setattr(remote, 'repository_uuid', 'repo-two')) == 'AttributeError')
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
        logged = [line.split(' ') for line in journey_log.read_text().splitlines()]
        check('query/scope', 'log holds only request name and outcome', bool(logged) and all(
            len(line) == 2 and line[0] in (*Q.REQUESTS, 'malformed')
            and line[1] in ('ok', 'coordinate_not_served', 'unavailable_service:run_query') for line in logged)
            and sum(server.counts.values()) == len(logged) and 'VELDO-9359' not in journey_log.read_text())
        # Freeze every nested metadata projection; injected record bodies never cross.
        real_decide = Q.EL.Gate.decide
        def planted_decide(gate, *args, **kwargs):
            answer = real_decide(gate, *args, **kwargs)
            answer['private_body'] = {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'}
            for item in answer['inputs'].values():
                item['private_body'] = {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'}
            if 'architecture' in answer:
                architecture = answer['architecture']
                architecture['private_body'] = {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'}
                for item in architecture['validator'].values():
                    item['private_body'] = {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'}
                for key in ('artifact', 'accepted'):
                    if isinstance(architecture[key], dict):
                        architecture[key]['private_body'] = {'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'}
            return answer
        before = remote.decide('selection', 'VELDO-9359')
        with patch.object(Q.EL.Gate, 'decide', planted_decide):
            after = remote.decide('selection', 'VELDO-9359')
        check('query/scope', 'all approved metadata without planted bodies', stable(before) == stable(after)
              and 'BODY_MUST_STAY_SERVER_SIDE' not in json.dumps(after))
        for event in remote_events:
            if event.get('schema') == Q.SCHEMA:
                planted = dict(event, private_body={'sentinel': 'BODY_MUST_STAY_SERVER_SIDE'})
                check('query/scope', 'frozen event including approved metadata', Q._event(planted) == event)
        for key in ('accepted', 'artifact'):
            malformed = json.loads(json.dumps(before))
            malformed['architecture'][key] = {}
            with patch.object(Q, '_exchange', return_value={'answer': malformed, 'events': []}):
                check('query/scope', 'incomplete architecture ' + key,
                      stopped(lambda: remote.decide('selection', 'VELDO-9359')) == 'unavailable_service:run_query')
        for malformed in ({}, {'answer': dict.fromkeys(Q.FACTS, 'false'), 'events': []},
                          {'answer': dict(dict.fromkeys(Q.FACTS, False), extra='body'), 'events': []},
                          {'answer': dict.fromkeys(Q.FACTS, False), 'events': [{'operation': 'build'}]}):
            with patch.object(Q, '_exchange', return_value=malformed):
                check('query/scope', 'malformed reply named', stopped(lambda: remote.completion('VELDO-9359')) == 'unavailable_service:run_query')

        DSP = FR._floor_authority()
        for state, extra in (('handoff', {'build': {'dispatch': 'build-dispatch'}, 'reviews': [{'dispatch': 'review-dispatch'}]}),
                             ('returned', {'returned_to': 'ready'})):
            put(DSP.floor_id('repo-one', 'VELDO-9359'), DSP.FLOOR_KIND, dict(state=state, **extra))
            floor = compare('floor stored ' + state, lambda gate: gate.floor_entry('VELDO-9359', 'ready'))
            check('query/journey', 'floor record metadata ' + state, floor['state'] == state and floor['version'] > 0)
            compare('frontier with stored ' + state, lambda gate: FR.claimable(repo_root=repo, eligibility=gate))
            compare('work floor join ' + state, lambda gate: FR.floor_station('VELDO-9359', repo_root=repo, eligibility=gate))
        landing = {k: k + '/fixture' for k in ('implementation_commit', 'proof_digest', 'reviewed_source_digest',
                   'old_remote_tip', 'candidate_commit', 'tested_tree', 'gate_invocation', 'remote_confirmation',
                   'replication_receipt', 'dispatch_id')}
        landing.update(unit_id='VELDO-9359', gate_output_location='outside/fixture')
        receipts = {
            'attempt_finished': dict(trusted_exit=True, accounting_observation='observation', containment_empty=True),
            'artifact_accepted': dict(station='review', artifact_digests=['sha256:fixture'], acceptor='fixture'),
            'revision_landed': dict(publication_receipt=landing, remote_confirmation='refs/heads/main',
                                    replicated=True, spec_shipped_event='fixture-event'),
            'objective_satisfied': dict(signed_assessment='assessment', accepted_objective_revision=1, assessor='fixture'),
        }
        for fact, data in receipts.items():
            put('receipt:' + fact, 'completion_receipt', dict(fact=fact, subject={'id': 'VELDO-9359', 'revision': 1}, **data))
        completed = compare('all completion facts', lambda gate: gate.completion('VELDO-9359'))
        check('query/journey', 'all completion facts present and true', completed == dict.fromkeys(Q.FACTS, True))
        compare('landed floor', lambda gate: gate.floor_entry('VELDO-9359', 'ready', gate.landed('VELDO-9359')))
        check('query/journey', 'callbacks of every kind were compared [%s]' % sorted(map(str, operations)),
              {'invalid_record', 'decision_dependency'} <= operations and len(operations) >= 4)

        # Cost: a floor entry, a request or an entry gate loads no module once its organ is held, and a
        # frontier pass over a store-holding gate (the marker-present path) loads none at all, as before B1.
        executed = []
        real_exec = importlib.machinery.SourceFileLoader.exec_module

        def counting(loader, module):
            executed.append(module.__name__)
            return real_exec(loader, module)

        ENTRIES = 25
        EL2 = load('v359_eligibility_fresh', mods / 'control_eligibility.py')
        fresh = EL2.enrolled_gate(repo, trust)
        stack.callback(fresh.close)
        FR._floor_entry(direct, 'VELDO-9359', 'ready')  # the frontier holds its floor authority, as at base
        with patch.object(importlib.machinery.SourceFileLoader, 'exec_module', counting):
            passed = [FR._floor_entry(fresh, unit, 'ready') for _ in range(ENTRIES) for unit in ('VELDO-9359', 'VELDO-9360')]
        check('query/cost', 'frontier pass over a direct gate loads no module [%s]' % executed[:4],
              not executed and 'frontier' not in EL2._LATE and len(passed) == 2 * ENTRIES
              and stable(passed[0]) == stable(direct.floor_entry('VELDO-9359', 'ready')))
        fresh.floor_entry('VELDO-9359', 'ready')  # any other caller: the frontier is loaded once and kept
        with patch.object(importlib.machinery.SourceFileLoader, 'exec_module', counting):
            for _ in range(ENTRIES):
                fresh.floor_entry('VELDO-9359', 'ready')
                direct.floor_entry('VELDO-9359', 'ready')
        check('query/cost', 'direct floor entries reload nothing [%s]' % executed[:4], not executed)
        with patch.object(importlib.machinery.SourceFileLoader, 'exec_module', counting):
            for _ in range(ENTRIES):
                remote.floor_entry('VELDO-9359', 'ready')
                remote.replication_status()
                EL.entry_gate(repo).close()
        check('query/cost', 'served floor entries, replication and entry gates reload nothing [%s]' % executed[:4],
              not executed)
        # An actual local replica still opens outside the authority directory in query mode.
        replica_path = Path(EL.E.git_common_dir(repo)) / S.DB_RELATIVE
        replica = S.open_store(str(replica_path))
        replica.close()
        with patch.object(sqlite3, 'connect', no_client_store):
            check('query/journey', 'status local replica present', RS._replication(repo, time.time(), eligibility=remote)['present'])
            model = RS.status(root=repo, eligibility=remote, control_db=str(db))
            check('query/journey', 'status model and text', model['replication']['present'] and model['store_guard']['state'] == 'on'
                  and 'configuration for later launches' in RS.render_text(model))

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
        with patch.object(sqlite3, 'connect', no_client_store), patch.dict(os.environ, {'VELDO_CONTROL_DB': str(db)}):
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
                    release.wait(HANG)
            worker = threading.Thread(target=stall)
            worker.start()
            try:
                with patch.object(Q, 'SECONDS', .1):
                    check('query/scope', 'transport deadline', stopped(lambda: Q.RemoteGate(repo, fake_path)) == 'unavailable_service:run_query')
                # The refusal above is the protocol's; that the peer was reached is an event, waited for.
                check('query/scope', 'transport connected and stalled', accepted.wait(HANG))
            finally:
                release.set()
                worker.join(HANG)
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
                unblock.wait(HANG)
                raise OSError('fixture readiness')
            if failure == 'connection':
                with patch.object(candidate, '_gate', side_effect=OSError('fixture connection')):
                    check('query/lifecycle', 'connection failure', stopped(candidate.start) == 'unavailable_service:run_query')
            else:
                result = []
                with patch.object(candidate, '_gate', side_effect=delayed_gate), patch.object(Q, 'SECONDS', .1):
                    starter = threading.Thread(target=lambda: result.append(stopped(candidate.start)))
                    starter.start()
                    assert opened.wait(HANG)
                    starter.join(HANG)
                    unblock.set()
                    candidate.thread.join(HANG)
                check('query/lifecycle', 'ready deadline', result == ['unavailable_service:run_query'])
            check('query/lifecycle', failure + ' cleanup', not candidate.path.parent.exists())
        bound, listen = threading.Event(), threading.Event()
        first = Q.Server(config, 'paused-A')
        real_listen = socket.socket.listen
        def pause_listen(sock, *args):
            if sock.getsockname() == str(first.path):
                bound.set()
                assert listen.wait(HANG)
            return real_listen(sock, *args)
        results = []
        with patch.object(socket.socket, 'listen', pause_listen):
            starter = threading.Thread(target=lambda: results.append(stopped(first.start)))
            starter.start()
            assert bound.wait(HANG)
            later = Q.Server(other_config, 'starting-B').start()
            check('query/lifecycle', 'A survives B startup', first.path.exists())
            listen.set()
            starter.join(HANG)
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

        # Production Receiver.launch and _spawn, with only prerequisite/engine seams replaced.
        # The payload is a tiny Python process; its stdin is the event that ends the run.
        payload = base / 'payload.py'
        payload.write_text("""import importlib.util, json, os, sqlite3, sys
from pathlib import Path
query = os.environ.get('VELDO_RUN_QUERY')
opened = False
built = False
flood = None
if query:
    def forbidden(*args, **kwargs):
        raise RuntimeError('run attempted a direct store open')
    sqlite3.connect = forbidden
    spec = importlib.util.spec_from_file_location('payload_eligibility', sys.argv[2])
    EL = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(EL)
    RQ = EL._late('control_run_query')
    RQ.SECONDS = 120  # a hang detector here; the fixture never waits for a deadline
    gate = EL.entry_gate(sys.argv[3])
    built = gate.decide('direct_execution', 'VELDO-9359')['eligible']
    gate.close()
    if 'flood' in sys.argv[4:]:
        # More request lines than a pipe holds, asked while the Runner side is not reading.
        flood = 0
        for _ in range(3000):
            try:
                flood += 'answer' in RQ._exchange(query, {'operation': 'hello'})
            except RQ.Refused:
                break
    if 'stray' in sys.argv[4:]:
        (Path(query).parent / 'dropped-by-run').write_text('dropped by the run')
else:
    conn = sqlite3.connect(sys.argv[1])
    conn.execute('SELECT 1 FROM entities LIMIT 1').fetchone()
    conn.close()
    opened = True
print(json.dumps({'query': query, 'store_open': opened, 'build_reached': built, 'flood': flood}), flush=True)
sys.stdin.buffer.read(1)
""")
        harness = base / 'receiver.py'
        harness.write_text("""import importlib.util, json, os, subprocess, sys, threading, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('fixture_launch', sys.argv[2])
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
sys.argv = [sys.argv[0], sys.argv[1]]
L.RQ.SECONDS = 120  # a hang detector here; the fixture never waits for a deadline
RECEIVERS = []
def endpoint_state(dispatch):
    place = L.RQ.endpoint(dispatch)
    return {'directory': os.path.lexists(place.parent), 'socket': os.path.lexists(place)}
real_scan = L.launch_scan
def scan(config, dispatch_id, project, environment, argv, own=()):
    # What the VELDO-0254 launch scan was told is Veldo's own, by name only.
    RECEIVERS[0].emit({'event': 'scan_probe', 'own': sorted(
        name for name in ('VELDO_RUN_QUERY', 'VELDO_DISPATCH_ACCEPTANCE') if environment.get(name) in own)})
    return real_scan(config, dispatch_id, project, environment, argv, own=own)
L.launch_scan = scan
# The end's scan and space belong to other briefs: the end is reported as report_end reports it.
L.report_end = lambda receiver, contract, event: receiver.emit(event)
class Dispatches:
    def __init__(self, receiver):
        self.receiver = receiver
        self.state = 'prepared'
    def record(self, dispatch):
        return {'state': self.state, 'contract_digest': L.D.digest(self.receiver.config['fixture_contract'])}
    def accept(self, *args, **kwargs):
        r = self.receiver
        ready = r.query_server is not None and r.query_server.ready.is_set()
        r.emit({'event': 'accept_probe', 'ready': ready, 'path': str(r.query_server.path) if ready else None})
        if r.config.get('fail_accept'):
            raise L.D.Refused('fixture_accept_refused')
        self.state = 'accepted'
    def receipt(self, *args):
        return 'fixture-acceptance'
    def refuse(self, *args, **kwargs):
        self.state = 'refused'
    def run(self, *args, **kwargs):
        self.state = 'running'
    def exit(self, dispatch, *args, **kwargs):
        # The production _finish records the end here: what the receiver had done to its endpoint by then.
        self.state = 'exited'
        self.receiver.emit({'event': 'end_probe', **endpoint_state(dispatch)})
class Receiver(L.Receiver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatches = Dispatches(self)
        RECEIVERS.append(self)
        self.off_thread = []
        write = self.emit
        def emit(message):
            if threading.current_thread() is not threading.main_thread():
                # Counted, not written: only the receiver's own thread may use the launch pipe.
                self.off_thread.append(message.get('event'))
                return
            write(message)
        self.emit = emit
    def close(self):
        super().close()
        dispatch = self.config['fixture_contract']['dispatch_id']
        self.emit({'event': 'closed', **endpoint_state(dispatch)})
    def _remove_run(self): pass
    def _ended(self): return {}
    def _recheck(self, *args): pass
    def _qualify(self, *args): pass
    def _login(self, *args): pass
    def _bind(self, *args): pass
    def _space_end(self, *args): pass
    def _resolve_credentials(self, *args): pass
    def _space_given(self, dispatch, argv, environment, adapter): return environment
    def _record(self, adapter, environment): pass
    def _invoke(self, contract, acceptance, adapter):
        if self.config.get('flip_after_sample'):
            Path(self.store_guard['path']).write_text('later launches')
        return self._spawn(contract['dispatch_id'], acceptance, adapter)
    def _contained(self, dispatch, argv, environment, cwd=None):
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
    def _reap(self, worker, contract, carry, **kwargs):
        payload = json.loads(worker.stdout.readline())
        self.emit({'event': 'payload', 'pid': worker.pid, 'off_thread': list(self.off_thread), **payload})
        if self.config.get('wait_payload'):
            sys.stdin.buffer.read(1)
        if worker.poll() is None:
            try:
                worker.stdin.write(b'x'); worker.stdin.flush()
            except BrokenPipeError: pass
        code = worker.wait(timeout=120)
        self.emit({'event': 'payload_exit', 'code': code})
        self.supervision = {'cause': None, 'empty': True}
        return {'code': code, 'deadline_stop': False}
L.Receiver = Receiver
L.main()
""")
        real_popen = L.subprocess.Popen
        children = []
        def spawn_receiver(argv, **kwargs):
            # invoke owns the receiver as in production; its executable is this fixture harness.
            argv = [sys.executable, '-B', str(harness), argv[-1], str(mods / 'control_launch.py')]
            child = real_popen(argv, **kwargs)
            children.append(child)
            return child
        def read_event(child, pending, wanted):
            deadline = time.monotonic() + HANG
            while True:
                while b'\n' in pending[0]:
                    line, _, pending[0] = pending[0].partition(b'\n')
                    value = json.loads(line)
                    child.fixture_launch.pending = line + b'\n'
                    child.fixture_launch._take()
                    pending[1].append(value)
                    if value.get('event') in wanted:
                        return value
                with selectors.DefaultSelector() as sel:
                    sel.register(child.stdout, selectors.EVENT_READ)
                    assert sel.select(max(.001, deadline - time.monotonic())), 'receiver event deadline'
                    data = os.read(child.stdout.fileno(), 65536)
                assert data, ('receiver ended before event', wanted, pending[1])
                pending[0] += data
                assert time.monotonic() < deadline, 'receiver event deadline'
        def run_fixture(label, **options):
            cfg = dict(config, state_root=str(base / 'state'), adapters={'fixture': {'argv': [
                sys.executable, '-B', str(payload), str(db), str(mods / 'control_eligibility.py'), str(repo),
                *options.pop('payload_args', ())]}})
            cfg.update(options)
            cfg_path = base / (label + '.json')
            contract = dict(dispatch_id=label, unit='VELDO-9359', station='build', capability={'adapter': 'fixture'},
                            reservation={'project': 'fixture'}, input={'context': {}}, deadline=time.time() + 60)
            cfg['fixture_contract'] = contract
            cfg_path.write_text(json.dumps(cfg))
            with patch.object(L.subprocess, 'Popen', spawn_receiver), patch.object(L.Launch, 'start', lambda self, seconds: self):
                launch = L.invoke(str(cfg_path), contract, None)
            launch.child.fixture_launch = launch
            launch.fixture_pending = [b'', []]
            return launch, launch.fixture_pending
        def reap(launch):
            launch.child.wait(timeout=HANG)
            # Lines this fixture read from the pipe but has not handed over are the Launch's too.
            launch.pending, launch.fixture_pending[0] = launch.fixture_pending[0] + launch.pending, b''
            launch._end_receiver()
        for label, ending in (('normal-end', 'normal'), ('killed-engine', 'engine'), ('killed-receiver', 'receiver')):
            launch, pending = run_fixture(label, wait_payload=True)
            seen = read_event(launch.child, pending, {'payload'})
            path = Q.endpoint(label)
            accepted_events = [e for e in pending[1] if e.get('event') == 'accept_probe']
            check('query/lifecycle', label + ' ready before acceptance', accepted_events and accepted_events[0]['ready']
                  and seen['query'] == str(path) and Path(path).exists() and seen['build_reached'] and not seen['store_open'])
            gone = {'directory': False, 'socket': False}
            if ending == 'engine':
                os.kill(seen['pid'], signal.SIGKILL)
                launch.child.stdin.write(b'x'); launch.child.stdin.flush()
                # The receiver's own answer, given as its production _finish records the end and before
                # the Runner reaps it: the Runner's removal cannot stand in for the receiver's.
                check('query/lifecycle', label + ' removed by the receiver before its end is recorded',
                      read_event(launch.child, pending, {'end_probe'}) | {'event': 0} == gone | {'event': 0})
                reap(launch)
            elif ending == 'receiver':
                # The actual supervising Launch owns cleanup after observing its receiver exit.
                launch.child.kill()
                launch._end_receiver()
                # End only the fixture payload the receiver left behind.
                with contextlib.suppress(ProcessLookupError):
                    os.kill(seen['pid'], signal.SIGKILL)
            else:
                launch.child.stdin.write(b'x'); launch.child.stdin.flush()
                check('query/lifecycle', label + ' removed by the receiver before its end is recorded',
                      read_event(launch.child, pending, {'end_probe'}) | {'event': 0} == gone | {'event': 0})
                reap(launch)
            check('query/lifecycle', label + ' endpoint removed', not path.parent.exists())
            check('query/lifecycle', label + ' left nothing to record', launch.query_left is None)
            check('query/lifecycle', label + ' receiver exited', launch.returncode is not None)
            if ending != 'receiver':
                check('query/lifecycle', label + ' query counts collected', bool(launch.query_counts))
        launch, pending = run_fixture('accept-refusal', fail_accept=True)
        refused = read_event(launch.child, pending, {'refused'})
        closed = read_event(launch.child, pending, {'closed'})
        probe = next(e for e in pending[1] if e.get('event') == 'accept_probe')
        reap(launch)
        check('query/lifecycle', 'later refusal removes endpoint', refused['refusal'] == 'fixture_accept_refused'
              and not Q.endpoint('accept-refusal').parent.exists() and not any(e.get('event') == 'payload' for e in pending[1]))
        check('query/lifecycle', 'later refusal: made, then removed by the receiver itself',
              probe['ready'] and closed | {'event': 0} == {'directory': False, 'socket': False, 'event': 0})
        bad_cfg = dict(config, host_trust=str(base / 'missing-trust'))
        # Creation and readiness failures reach the receiver's pre-acceptance refusal, not a spawn.
        for label, change in (('launch-creation-failure', {}), ('launch-reader-failure', {'host_trust': bad_cfg['host_trust']})):
            path = Q.endpoint(label)
            if not change:
                path.parent.mkdir()
            launch, pending = run_fixture(label, **change)
            refused = read_event(launch.child, pending, {'refused'})
            # No endpoint ownership was acquired on collision: preserve the existing directory.
            reap(launch)
            check('query/lifecycle', label, refused['refusal'] == 'unavailable_service:run_query'
                  and not any(e.get('event') in ('accepted', 'payload') for e in pending[1])
                  and (bool(change) or path.parent.exists()))
        # A Runner that is not reading: the run asks more than a pipe of request lines holds. Every answer
        # arrives, because the serving thread writes its log to a file and nothing to the launch pipe.
        launch, pending = run_fixture('unread-pipe', payload_args=['flood'])
        seen = read_event(launch.child, pending, {'payload'})
        scan_probe = next(e for e in pending[1] if e.get('event') == 'scan_probe')
        reap(launch)
        flood_log = Path(Q.log_path(L.ER.directory({'state_root': str(base / 'state')}), 'unread-pipe'))
        flood_lines = flood_log.read_text().splitlines() if flood_log.exists() else []
        check('query/lifecycle', 'answers do not wait for the Runner to read [%s %s]' % (seen['flood'], seen['off_thread'][:3]),
              seen['flood'] == 3000 and seen['off_thread'] == [])
        check('query/lifecycle', 'each request logged to a file, counts once on the pipe',
              flood_lines.count('hello ok') >= 3000 and (launch.query_counts or {}).get('hello:ok', 0) >= 3000
              and len(launch.messages) < 40 and sum(1 for m in launch.messages if m.get('event') == 'run_query_end') == 1
              and not any(m.get('event') == 'run_query' for m in launch.messages))
        check('query/scope', 'launch scan: the query variable is own, the acceptance is not added [%s]' % scan_probe['own'],
              scan_probe['own'] == ['VELDO_RUN_QUERY'])
        # A file the run drops in its endpoint directory: cleanup leaves it and says so, the production
        # _finish still records the end, the receiver exits cleanly and the Runner's removal does not raise.
        launch, pending = run_fixture('stray-file', payload_args=['stray'])
        seen = read_event(launch.child, pending, {'payload'})
        read_event(launch.child, pending, {'closed'})  # the receiver's last line, whatever came before it
        ended = next((e for e in pending[1] if e.get('event') == 'end_probe'), {'directory': None, 'socket': None})
        exited = next((e for e in pending[1] if e.get('event') in ('exited', 'failed')), {'event': None})
        raised = stopped(lambda: reap(launch))
        stray = Q.endpoint('stray-file').parent
        receiver_log = Path(launch.receiver_log).read_text() if launch.receiver_log else ''
        check('query/lifecycle', 'stray file: end recorded, endpoint left and recorded [%s %s %s %s]' % (
            raised, launch.returncode, launch.query_left, sorted(x.name for x in stray.iterdir()) if stray.exists() else None),
              raised is None and launch.returncode == 0 and ended['directory'] and not ended['socket']
              and exited['event'] == 'exited' and launch.query_left == 'left:ENOTEMPTY'
              and [x.name for x in stray.iterdir()] == ['dropped-by-run']
              and receiver_log.count('run query endpoint left:ENOTEMPTY') == 2)
        def removal(*arguments):
            try:
                return Q.remove(*arguments)
            except Exception as error:
                return 'raised:' + type(error).__name__
        check('query/lifecycle', 'stray file: removal reports, never raises',
              removal(stray / 'query.sock') == 'left:ENOTEMPTY'
              and removal(stray / 'query.sock', (0, 0)) == 'left:replaced' and stray.exists())
        (stray / 'dropped-by-run').unlink()
        check('query/lifecycle', 'stray file: removal of the emptied directory', removal(stray / 'query.sock') is None
              and not stray.exists() and removal(stray / 'query.sock') is None)
        # Sample once: changing the marker after acceptance never changes this run's query variable.
        launch, pending = run_fixture('sample-once', flip_after_sample=True)
        seen = read_event(launch.child, pending, {'payload'})
        reap(launch)
        check('switch/off', 'single held sample', seen['query'] == str(Q.endpoint('sample-once')))
        marker = db.parent / 'store-guard.off'
        check('switch/off', 'fixture created marker only', marker.exists())
        launch, pending = run_fixture('marker-off')
        seen = read_event(launch.child, pending, {'payload'})
        reap(launch)
        accepted_event = next(e for e in pending[1] if e.get('event') == 'accepted')
        check('switch/off', 'marker restores direct reads and removes inherited variable', seen['query'] is None and seen['store_open']
              and accepted_event['store_guard']['state'] == 'off' and accepted_event['store_guard']['path'] == str(marker))
        marker.unlink()
        # An invalid marker refuses the launch itself by name, before acceptance: never treated as off.
        for invalid in ('symlink', 'directory'):
            if invalid == 'symlink':
                marker.symlink_to(db)
            else:
                marker.mkdir()
            launch, pending = run_fixture('marker-' + invalid)
            read_event(launch.child, pending, {'closed'})  # the receiver's last line, whatever came before it
            refused = next((e for e in pending[1] if e.get('event') == 'refused'), {'refusal': None})
            reap(launch)
            check('switch/off', invalid + ' marker refuses the launch by name', refused['refusal'] == 'invalid_input:layout:switch'
                  and not any(e.get('event') in ('accept_probe', 'accepted', 'payload') for e in pending[1])
                  and not Q.endpoint('marker-' + invalid).parent.exists())
            if invalid == 'symlink':
                marker.unlink()
            else:
                marker.rmdir()
        # The namespace-less conversation receiver still launches; it grants no repository answers.
        put('unbound', 'execution_unit', dict(revision=1, project='fixture', state='READY'))
        put('unbound-cycle', 'pm_cycle', {k: v for k, v in cycle.items() if k != 'repository'})
        conversation = Q.Server({k: v for k, v in dict(config, receiver_kind='conversation').items()
                                 if k not in ('repository', 'workspace')}, 'conversation').start()
        check('query/scope', 'conversation has no repository',
              stopped(lambda: Q.RemoteGate(repo, conversation.path)) == 'run_query:other_repository')
        # A raw client of that socket gets no record, including one that names no repository.
        for request in ({'operation': 'completion', 'unit': 'unbound'},
                        {'operation': 'floor_entry', 'unit': 'unbound', 'word': 'ready', 'landed': False},
                        {'operation': 'decide', 'station': 'selection', 'unit': 'unbound', 'context': None, 'ticket': None},
                        {'operation': 'decide', 'station': 'coordination', 'unit': 'unbound-cycle', 'context': None, 'ticket': None},
                        {'operation': 'decision_blockers', 'unit': 'VELDO-9359', 'references': []}):
            check('query/scope', 'conversation serves no record: ' + request['operation'] + ' ' + request['unit'],
                  stopped(lambda: Q._exchange(conversation.path, request)) == 'coordinate_not_served')
        check('query/scope', 'conversation still answers hello',
              Q._exchange(conversation.path, {'operation': 'hello'})['answer']['repository_uuid'] is None)
        conversation.close()

        marker = db.parent / 'store-guard.off'
        check('switch/off', 'absent means on', Q.switch(db)['state'] == 'on')
        risky = object.__new__(L.Receiver)
        risky.config, risky.runner, risky.query_server = config, {'runner': 'confined'}, None
        risky.emit = lambda event: None
        check('query/scope', 'risky runner has no query endpoint', risky._prepare_query({'dispatch_id': 'risky'}, {}) is None
              and risky.query_server is None and not Q.endpoint('risky').parent.exists())
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
