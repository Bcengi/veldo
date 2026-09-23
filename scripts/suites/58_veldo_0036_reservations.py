"""Reservation behavior over real SQLite, competing clients and a real descendant.

Only shared ROOT and expect are consumed. All stores/processes/files are temporary.
Adapter fixtures exercise the reservation seam; they do not qualify live CLI engines.
"""

def _v36_suite():
    import ctypes
    import hashlib
    import hmac
    import importlib.util
    import json
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    import tempfile
    import threading

    def load(path):
        spec = importlib.util.spec_from_file_location('v36_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    reservations = load(ROOT / ".veldo" / "control_reservations.py")
    runtime = load(ROOT / ".veldo" / "control_reservation_runtime.py")
    # Real files and SQLite locks on tmpfs avoid paying disk durability latency for
    # every mutation. Crash/durability qualification is explicitly outside Release 1.
    fast_temp = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v36-', dir=fast_temp) as directory:
        base = Path(directory)
        serial = 0
        connections = []
        key = os.urandom(32)
        def sign(data):
            return hmac.new(key, data, hashlib.sha256).hexdigest()

        def authority(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            member = json.loads(row[0]) if row else {}
            return member.get('roles') == ['reservation_service'] and member.get('revoked_at') is None

        def open_service(path):
            store = load(ROOT / '.veldo' / 'control_store.py')
            conn = store.open_store(path)
            connections.append(conn)
            events = []
            service = reservations.Reservations(store, conn, domain='domain', repository='repository',
                principal='runner', authorize=authority, signer='authority', sign=sign, observe=events.append)
            return service, events

        def fixture(overrides=None, policy_scope=None):
            nonlocal serial
            serial += 1
            service, events = open_service(base / ('store-%s.sqlite3' % serial))
            service.store.execute(service.conn, dict(command_id='member', operation='upsert_entity',
                parameters=dict(entity_id='runner', kind='membership', data=dict(roles=['reservation_service'])),
                principal='owner', nonce='member', expected_versions={'runner': 0}, artifact_digests=[]),
                'authority', sign, 1)
            for scope, subject in zip(reservations.SCOPES, ('account', 'project', 'unit')):
                caps = dict(capacity=10, invocations=10, wall_seconds=100)
                if overrides and (policy_scope is None or scope == policy_scope):
                    caps.update(overrides)
                service.configure('policy-' + scope, scope, subject, caps, now=1)
            return service, events

        def worker(service, dispatch='worker'):
            return service.reserve_worker('dispatch-' + dispatch, dispatch, 'account', 'project', 'unit', now=2)

        def call(service, name='call', boundary='initial', wall=5):
            return service.reserve_call(name, 'worker', name, boundary, wall, now=3)

        def refusal(fn):
            try:
                fn()
            except (reservations.Refused,) as error:
                return error.code
            return None

        try:
            # AC1: below, exactly equal, above each applicable ceiling and real balances.
            ceiling_ok = True
            for scope in reservations.SCOPES:
                for cap in (0, 1, 2):
                    service, events = fixture({'capacity': cap}, scope)
                    outcomes = [refusal(lambda n=n: worker(service, 'w' + str(n))) for n in range(3)]
                    ceiling_ok &= outcomes[:cap] == [None] * cap and all(outcomes[cap:])
                    ceiling_ok &= service.balances(scope, scope)['capacity'] == cap
                for unit in ('invocations', 'wall_seconds'):
                    for cap in ((0, 5, 10) if unit == 'wall_seconds' else (0, 1, 2)):
                        service, _ = fixture({unit: cap}, scope)
                        worker(service)
                        for n in range(3):
                            error = refusal(lambda n=n: call(service, 'i' + str(n), wall=5))
                            amount = (n + 1) * (5 if unit == 'wall_seconds' else 1)
                            ceiling_ok &= (error is None) == (amount <= cap)
                        ceiling_ok &= service.balances(scope, scope)[unit] == min(cap, 15 if unit == 'wall_seconds' else 3)
                for unit in ('tokens', 'messages'):
                    for usage in (4, 5, 6):
                        service, _ = fixture({unit: 5}, scope)
                        worker(service)
                        call(service)
                        service.report('usage', 'call', 1, dict(invocations=1, wall_seconds=1, **{unit: usage}), final=True, now=4)
                        error = refusal(lambda: call(service, 'next'))
                        ceiling_ok &= (error is None) == (usage < 5)
                        ceiling_ok &= service.balances(scope, scope)[unit] == usage
            expect('VELDO-0036 reservations/ceilings', ceiling_ok)

            # Two connections take their pre-command snapshots together. Only the transition's
            # transaction may judge the last slot. Mutating it to use that snapshot overallocates.
            race_ok = True
            for usage_race in (False, True):
                service, _ = fixture({'capacity': 10 if usage_race else 1, 'invocations': 1})
                if usage_race:
                    worker(service)
                path = service.conn.execute('PRAGMA database_list').fetchone()[2]
                barrier = threading.Barrier(2)
                outcomes, errors = [], []
                def contender(n):
                    store = load(ROOT / '.veldo' / 'control_store.py')
                    conn = store.open_store(path)
                    client = reservations.Reservations(store, conn, domain='domain', repository='repository',
                        principal='runner', authorize=authority, signer='authority', sign=sign)
                    execute = store.execute
                    def together(*args, **kwargs):
                        barrier.wait(timeout=5)
                        return execute(*args, **kwargs)
                    store.execute = together
                    try:
                        outcomes.append(refusal(lambda: call(client, 'race' + str(n))) if usage_race
                                        else refusal(lambda: worker(client, 'race' + str(n))))
                    except Exception as error:
                        errors.append(repr(error))
                    finally:
                        conn.close()
                clients = [threading.Thread(target=contender, args=(n,)) for n in range(2)]
                for client in clients:
                    client.start()
                for client in clients:
                    client.join(timeout=7)
                if errors or any(c.is_alive() for c in clients):
                    raise RuntimeError(('reservation competition did not finish', errors))
                resource = 'invocations' if usage_race else 'capacity'
                race_ok &= outcomes.count(None) == 1 and service.balances('account', 'account')[resource] == 1
            expect('VELDO-0036 reservations/atomic-last-slot', race_ok)

            # AC2: enumerate the registered engines and ALL their invocation boundaries.
            ordering_ok = set(runtime.ADAPTERS) == {'claude_code', 'codex'}
            for adapter, boundaries in runtime.ADAPTERS.items():
                ordering_ok &= set(boundaries) == {'initial', 'retry', 'follow_on'}
                for boundary in boundaries:
                    service, events = fixture({'invocations': 1})
                    worker(service)
                    launches, stops = [], []
                    configuration = {'mcp_servers': ['configured-server'], 'tools': ['configured-tool']}
                    def launch(ident, config):
                        launches.append((ident, config is configuration,
                            service.balances('account', 'account')['invocations']))
                    guard = runtime.InvocationGuard(service, adapter, launch, stops.append)
                    guard.invoke('first', 'worker', 'first', boundary, 5, configuration, now=3)
                    # A replay never launches a second time.
                    guard.invoke('first', 'worker', 'first', boundary, 5, configuration, now=3)
                    denied = refusal(lambda: guard.invoke('second', 'worker', 'second', boundary, 5, configuration, now=4))
                    ordering_ok &= bool(denied) and launches == [('first', True, 1)] and stops == ['worker']
                    ordering_ok &= events[-1]['outcome'] == 'refused'
                    ordering_ok &= service.status()['refused'] == 1 and service.status()['pending'] == 1
                    ordering_ok &= all(e['domain'] == 'domain' and e['repository'] == 'repository'
                                       and e['request'] and 'accepted_versions' in e for e in events)
            service, _ = fixture()
            worker(service)
            service.store.execute(service.conn, dict(command_id='revoke', operation='upsert_entity',
                parameters=dict(entity_id='runner', kind='membership', data=dict(roles=['reservation_service'], revoked_at=3)),
                principal='owner', nonce='revoke', expected_versions={'runner': 1}, artifact_digests=[]),
                'authority', sign, 1)
            ordering_ok &= refusal(lambda: call(service)) == 'missing_authority'
            expect('VELDO-0036 reservations/pre-call-order', ordering_ok)

            controls_ok = True
            for unit in ('tokens', 'messages'):
                service, _ = fixture({unit: 5})
                worker(service)
                stops = []
                guard = runtime.InvocationGuard(service, 'codex', lambda *a: None, stops.append)
                guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
                controls_ok &= refusal(lambda: call(service, 'unknown-next')) == 'unknown_allowance:' + unit
                guard.observe('report', 'call', 1, {unit: 5}, now=4)
                controls_ok &= stops == ['worker'] and bool(refusal(lambda: call(service, 'exhausted-next')))
            service, _ = fixture()
            worker(service)
            stops = []
            guard = runtime.InvocationGuard(service, 'claude_code', lambda *a: None, stops.append)
            guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
            guard.observe('tick', 'call', 1, {}, now=8)
            controls_ok &= stops == ['worker']
            for unit in ('invocations', 'tokens', 'messages', 'wall_seconds'):
                for remaining in (None, 0, 5):
                    service, _ = fixture()
                    worker(service)
                    service.window('window', 'account', unit, remaining, 20, 1, now=2)
                    error = refusal(lambda: call(service))
                    controls_ok &= (error is None) == (remaining == 5)
                    if remaining == 0:
                        error = refusal(lambda: service.reserve_call('after-reset', 'worker', 'after-reset', 'retry', 5, now=20))
                        controls_ok &= error is None
                        service.window('refresh', 'account', unit, 5, 40, 2, now=21)
                        controls_ok &= service._records()[service._policy_id('account', 'account')]['windows']['subscription']['watermark'] == 2
            # A refresh cannot erase an unfinished call; a later conclusive report is
            # still charged against that observed allowance, even across its watermark.
            service, _ = fixture()
            worker(service)
            service.window('window', 'account', 'tokens', 5, 20, 1, now=2)
            call(service)
            service.report('partial', 'call', 1, {'tokens': 1}, now=4)
            service.window('refresh', 'account', 'tokens', 5, 30, 2, now=5)
            controls_ok &= refusal(lambda: call(service, 'unknown-after-refresh')) == 'unknown_window_usage'
            service.report('final', 'call', 2, dict(invocations=1, wall_seconds=1, tokens=5, messages=1),
                           final=True, outcome='completed', now=6)
            controls_ok &= refusal(lambda: call(service, 'spent-after-refresh')) == 'window_exhausted'
            service, _ = fixture({'invocations': 1})
            worker(service)
            stops = []
            guard = runtime.InvocationGuard(service, 'codex', lambda *a: None, stops.append)
            guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
            guard.observe('completed', 'call', 1, dict(invocations=1, wall_seconds=1), final=True, outcome='completed', now=4)
            controls_ok &= stops == ['worker']
            service, _ = fixture()
            worker(service)
            service.window('hourly', 'account', 'tokens', 5, 20, 1, now=2, window_id='hourly')
            service.window('weekly', 'account', 'tokens', 0, 50, 1, now=2, window_id='weekly')
            controls_ok &= refusal(lambda: call(service, 'blocked-weekly')) == 'window_exhausted'
            service.window('hourly-refresh', 'account', 'tokens', 10, 30, 2, now=3, window_id='hourly')
            controls_ok &= refusal(lambda: call(service, 'still-weekly')) == 'window_exhausted'
            service.window('weekly-refresh', 'account', 'tokens', 5, 60, 2, now=3, window_id='weekly')
            stops = []
            guard = runtime.InvocationGuard(service, 'codex', lambda *a: None, stops.append)
            guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
            guard.observe('window-cap', 'call', 1, {'tokens': 5}, now=4)
            controls_ok &= stops == ['worker']
            expect('VELDO-0036 reservations/usage-controls', controls_ok)

            # AC3: cumulative reports, duplicates and conservative unknown charges.
            service, _ = fixture()
            worker(service)
            call(service)
            normal = dict(invocations=1, wall_seconds=2, tokens=7, messages=3)
            service.report('report', 'call', 1, normal, final=True, outcome='completed', now=4)
            once = service.balances('account', 'account')
            service.report('report', 'call', 1, normal, final=True, outcome='completed', now=4)
            service.report('duplicate', 'call', 1, normal, final=True, outcome='completed', now=4)
            settled_ok = once == service.balances('account', 'account') == dict(capacity=1, **normal)
            settled_ok &= refusal(lambda: service.report('conflict', 'call', 1, {}, now=5)) == 'report_conflict'
            records = service.store.export_journal(service.conn)
            settled_ok &= all(hmac.compare_digest(r['signature'], sign(service.store.journal_signed_bytes(r))) for r in records)
            expect('VELDO-0036 reservations/settles-once', settled_ok)

            unknown_ok = True
            for outcome in ('timeout', 'cancelled', None):
                service, _ = fixture({'invocations': 1, 'wall_seconds': 5})
                worker(service)
                call(service)
                service.report('missing', 'call', 1, {}, final=True, outcome=outcome, now=9)
                unknown_ok &= service.balances('account', 'account')['invocations'] == 1
                unknown_ok &= service.balances('account', 'account')['wall_seconds'] == 5
                unknown_ok &= bool(refusal(lambda: call(service, 'next')))
                unknown_ok &= service.status()['unknown'] == 1
            expect('VELDO-0036 reservations/unknown-retained', unknown_ok)

            # R1: a partial observation is not a conclusive final usage total.
            partial_final_ok = True
            for outcome in ('timeout', 'cancelled', None):
                for partial in (1, 7):
                    service, _ = fixture({'wall_seconds': 5})
                    worker(service)
                    call(service)
                    service.report('partial', 'call', 1, {'wall_seconds': partial}, now=4)
                    service.report('final', 'call', 2, {}, final=True, outcome=outcome, now=8)
                    partial_final_ok &= service.balances('account', 'account')['wall_seconds'] == max(5, partial)
                    partial_final_ok &= refusal(lambda: call(service, 'retry', 'retry', 4)) == 'usage_cap:account:wall_seconds'
            expect('VELDO-0036 reservations/partial-final-retained', partial_final_ok)

            # R2: reporting failure cannot leave a real worker alive, even before deadline.
            report_failure_ok = True
            for tick in (4, 8):
                service, _ = fixture()
                worker(service)
                processes, stops, report_liveness = [], [], []
                def launch_child(invocation, configuration):
                    child = subprocess.Popen([sys.executable, '-c',
                        'import time; print("ready", flush=True); time.sleep(60)'],
                        stdout=subprocess.PIPE, text=True)
                    processes.append(child)
                    assert child.stdout.readline().strip() == 'ready'
                def stop_child(dispatch):
                    stops.append(dispatch)
                    for child in processes:
                        if child.poll() is None:
                            child.terminate()
                            child.wait(timeout=5)
                guard = runtime.InvocationGuard(service, 'codex', launch_child, stop_child)
                try:
                    guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
                    service.store.execute(service.conn, dict(command_id='revoke', operation='upsert_entity',
                        parameters=dict(entity_id='runner', kind='membership',
                                        data=dict(roles=['reservation_service'], revoked_at=4)),
                        principal='owner', nonce='revoke', expected_versions={'runner': 1}, artifact_digests=[]),
                        'authority', sign, 1)
                    original_report = service.report
                    def reporting(*args, **kwargs):
                        report_liveness.append(processes[0].poll() is None)
                        return original_report(*args, **kwargs)
                    service.report = reporting
                    error = refusal(lambda: guard.observe('tick', 'call', 1, {}, now=tick))
                    report_failure_ok &= error == 'missing_authority'
                    report_failure_ok &= stops == ['worker'] and processes[0].poll() is not None
                    if tick == 8:
                        report_failure_ok &= report_liveness == [False]
                finally:
                    for child in processes:
                        if child.poll() is None:
                            child.kill()
                        child.wait(timeout=5)
                        child.stdout.close()
            expect('VELDO-0036 reservations/report-failure-stops', report_failure_ok)

            # R3: running workers obey every current scope's ceilings after reconfiguration.
            current_caps_ok = True
            for scope in reservations.SCOPES:
                for unit in ('wall_seconds', 'tokens', 'messages', 'capacity', 'invocations'):
                    service, _ = fixture()
                    worker(service)
                    stops = []
                    guard = runtime.InvocationGuard(service, 'codex', lambda *args: None, stops.append)
                    guard.invoke('call', 'worker', 'call', 'initial', 5, {}, now=3)
                    before = guard.observe('before', 'call', 1, {}, now=3)
                    current_caps_ok &= not before['stop_required'] and not stops
                    caps = dict(capacity=10, invocations=10, wall_seconds=100)
                    caps[unit] = 0 if unit in ('capacity', 'invocations') else 1
                    service.configure('lower', scope, scope, caps, now=4)
                    usage = {unit: 2} if unit in ('wall_seconds', 'tokens', 'messages') else {}
                    result = guard.observe('after', 'call', 2, usage, now=5)
                    current_caps_ok &= result['stop_required'] and stops == ['worker']
            expect('VELDO-0036 reservations/current-caps', current_caps_ok)

            # AC4: a REAL exited parent and its still-live descendant. Become the temporary
            # subreaper so we can reap that orphan ourselves; no process or zombie is leaked.
            libc = ctypes.CDLL(None, use_errno=True)
            original = ctypes.c_int()
            if libc.prctl(37, ctypes.byref(original), 0, 0, 0) != 0 or libc.prctl(36, 1, 0, 0, 0) != 0:
                raise RuntimeError('real descendant fixture needs Linux subreaper')
            child_pid = None
            parent = None
            try:
                parent = subprocess.Popen([sys.executable, '-c',
                    'import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],'
                    'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)'],
                    stdout=subprocess.PIPE, text=True)
                child_pid = int(parent.stdout.readline())
                parent.wait(timeout=5)
                service, _ = fixture({'capacity': 1})
                worker(service)
                call(service)
                clone = base / 'clone'
                service.report('retained-before-exit', 'call', 1, {}, final=True, outcome='timeout', now=3)
                outcome = 'unknown'
                child_alive = True
                def lifecycle(dispatch):
                    os.kill(child_pid, 0) if child_alive else None
                    return dict(terminated=parent.poll() is not None and not child_alive,
                                cleaned=not clone.exists(), outcome=outcome)
                retirement_ok = refusal(lambda: service.retire('live', 'worker', lifecycle, now=4)) == 'worker_alive'
                retirement_ok &= bool(refusal(lambda: worker(service, 'replacement-live')))
                os.kill(child_pid, signal.SIGKILL)
                os.waitpid(child_pid, 0)
                child_pid = None
                child_alive = False
                service, _ = fixture({'capacity': 1})
                worker(service)
                call(service)
                clone.mkdir()
                outcome = None
                retirement_ok &= refusal(lambda: service.retire('dirty', 'worker', lifecycle, now=5)) == 'cleanup_incomplete'
                clone.rmdir()
                retirement_ok &= refusal(lambda: service.retire('outcome', 'worker', lifecycle, now=6)) == 'missing_outcome'
                outcome = 'unknown'
                retirement_ok &= refusal(lambda: service.retire('accounting', 'worker', lifecycle, now=7)) == 'missing_accounting'
                service.report('unknown', 'call', 1, {}, final=True, outcome='timeout', now=8)
                service.retire('retired', 'worker', lifecycle, now=9)
                retirement_ok &= service.balances('account', 'account')['capacity'] == 0
                retirement_ok &= service.balances('account', 'account')['wall_seconds'] == 5
                retirement_ok &= refusal(lambda: worker(service, 'replacement')) is None
                expect('VELDO-0036 reservations/retirement', retirement_ok)
            finally:
                if child_pid:
                    os.kill(child_pid, signal.SIGKILL)
                    os.waitpid(child_pid, 0)
                if parent:
                    parent.wait(timeout=5)
                    parent.stdout.close()
                libc.prctl(36, original.value, 0, 0, 0)
        finally:
            for conn in connections:
                conn.close()

_v36_suite()
