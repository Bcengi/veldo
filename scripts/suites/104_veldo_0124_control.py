"""Real signed SQLite dispatch/account/reservation records across the fake Mac boundary."""


def _v124_control():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    import subprocess
    import tempfile

    spec = importlib.util.spec_from_file_location('v124_checks_control', ROOT / 'proof/VELDO-0125/macos_event_fixture.py')
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    C = T.load('project_runner_macos_control')
    D, S, RES = C.D, C.D.S, C.D.RES
    SIG = T.load('control_signer')

    def scenario(base, engine='codex', boundary='initial', mode='natural', exhausted=False):
        host, backend, request, paths = T.start(base, mode)
        private = paths['authority'] / 'journal'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private)],
                       check=True, capture_output=True, timeout=10)
        sign = lambda data: SIG.sign_bytes(private, data, 'veldo-journal')
        conn = S.open_store(str(paths['authority'] / 'control.sqlite3'))
        S.execute(conn, dict(command_id='setup', principal='owner', operation='upsert_entity', nonce='setup',
                             expected_versions={'receiver': 0}, artifact_digests=[], parameters=dict(
                                 entity_id='receiver', kind='membership', data=dict(principal_type='service',
                                     roles=['reservation_service'], scope=['repo'], revoked_at=None, expires_at=None))),
                  'owner', sign, 1)
        reservations = RES.Reservations(S, conn, domain='domain', repository='repo', principal='receiver',
                                        authorize=RES.service_authority, signer='receiver', sign=sign)
        accounts = C.ACC.Accounts(S, conn, principal='receiver', signer='receiver', sign=sign,
                                  authorize=lambda conn, command: True)
        accounts.register('account', 'account', engine, 'fixture subscription',
                          {backend.facts()['host']: str(paths['login'])}, now=backend.wall())
        for scope, subject in (('account', 'account'), ('project', 'project'), ('unit', 'unit')):
            reservations.configure('policy/' + scope, scope, subject,
                                    dict(capacity=2, invocations=1 if exhausted else 5, wall_seconds=20),
                                    now=backend.wall())
        dispatch = request['contract']['dispatch_id']
        reservations.reserve_worker('slot', dispatch, 'account', 'project', 'unit', now=backend.wall())
        entity = RES.entity('worker', ['domain', dispatch])
        version, digest = conn.execute('SELECT version, digest FROM entities WHERE id=?', (entity,)).fetchone()
        contract = request['contract']
        contract.update(unit='unit', station='review', attempt=2 if boundary == 'retry' else 1,
                        input=dict(decision=dict(decision_id='admitted-review', station='review', unit='unit',
                                                inputs={'source': contract['source']}), context={},
                                   payload={'resume': 'session'} if boundary == 'follow_on' else {}),
                        reservation=dict(entity=entity, version=version, digest=digest, account='account',
                                         project='project'), claim=None, authority_generation=1)
        contract['input']['payload_digest'] = D.digest(contract['input']['payload'])
        contract['capability']['adapter'] = engine
        dispatches = D.Dispatches(S, conn, domain='domain', repository='repo', principal='receiver',
                                  signer='receiver', sign=sign)
        if boundary == 'retry':
            prior = copy.deepcopy(contract)
            prior['dispatch_id'], prior['attempt'] = 'dispatch/prior', 1
            reservations.reserve_worker('prior-slot', prior['dispatch_id'], 'account', 'project', 'unit',
                                        now=backend.wall())
            prior_entity = RES.entity('worker', ['domain', prior['dispatch_id']])
            prior_version, prior_digest = conn.execute('SELECT version, digest FROM entities WHERE id=?',
                                                       (prior_entity,)).fetchone()
            prior['reservation'].update(entity=prior_entity, version=prior_version, digest=prior_digest)
            dispatches.prepare(prior, now=backend.wall())
            dispatches.refuse(prior['dispatch_id'], D.digest(prior), 'fixture_prior_refused', now=backend.wall())
        dispatches.prepare(contract, now=backend.wall())
        identity = dict(backend.process, platform='linux', principal='receiver')
        clean = [False]
        receiver = C.Receiver(dispatches, reservations, accounts, host, identity,
                              recheck=lambda c: None, cleanup=lambda d: clean[0], clock=backend.wall)
        original = backend.bootstrap
        observations = []

        def bootstrap(*args):
            record = dispatches.record(dispatch)
            calls = [r for r in reservations._records().values() if r['type'] == 'invocation']
            observations.append(dict(state=record['state'], acceptance=dispatches.receipt(dispatch, 'accept'),
                                     boundaries=[r['boundary'] for r in calls]))
            assert record['state'] == 'accepted' and observations[-1]['acceptance']
            assert any(r['state'] == 'pending' and r['boundary'] == boundary for r in calls)
            original(*args)

        backend.bootstrap = bootstrap
        if exhausted:
            reservations.reserve_call('exhaust', dispatch, 'earlier', 'initial', .3, now=backend.wall())
        return (receiver, contract, paths, backend, host, reservations, dispatches, conn, clean, observations)

    def accepted(base):
        for engine in T.P.ENGINES:
            receiver, contract, paths, backend, host, reservations, dispatches, conn, clean, seen = scenario(
                base / engine, engine)
            try:
                run = receiver.start(contract, str(paths['clone']), str(paths['scratch']))
                assert dispatches.record(run.dispatch)['state'] == 'running'
                assert seen[0]['state'] == 'accepted' and seen[0]['boundaries'] == ['initial']
                born = T.M.read(run.directory / 'request.json')['environment']
                variable = C.ACC.PROFILES[engine]
                assert born[variable] == str(paths['login'])
                # Production sets the run scoped HOME and TMPDIR, never the owner's.
                assert born['HOME'] == str(paths['scratch'].resolve()) + '/home'
                assert born['TMPDIR'].startswith(str(paths['usertemp'].resolve()) + '/veldo-')
                assert {k: born[k] for k in ('HOME', 'TMPDIR', 'TMP', 'TEMP')} == host.run_environment(
                    run.dispatch, str(paths['scratch']))
                assert born['VELDO_DISPATCH_ACCEPTANCE'] == dispatches.receipt(run.dispatch, 'accept')
                assert receiver.wait(run.dispatch)['state'] == 'exited'
                assert not D.completed(dispatches.record(run.dispatch))
            finally:
                conn.close()

    def caps(base):
        for engine in T.P.ENGINES:
            for boundary in ('initial', 'retry', 'follow_on'):
                receiver, contract, paths, backend, host, reservations, ds, conn, clean, seen = scenario(
                    base / (engine + boundary), engine, boundary, exhausted=True)
                try:
                    T.refused(lambda: receiver.start(contract, str(paths['clone']), str(paths['scratch'])),
                              'usage_cap:')
                    assert backend.bootstraps == 0 and not seen
                    assert not reservations.worker(contract['dispatch_id'])['retired']
                finally:
                    conn.close()

    def refusals(base):
        receiver, contract, paths, backend, host, reservations, ds, conn, clean, seen = scenario(base)
        try:
            changed = copy.deepcopy(contract)
            changed['source']['commit'] = '0' * 40
            T.refused(lambda: receiver.start(changed, str(paths['clone']), str(paths['scratch'])),
                      'binding_mismatch:contract_digest')
            host.profile['eligible'] = True
            host.qualification = None
            T.refused(lambda: receiver.start(contract, str(paths['clone']), str(paths['scratch'])),
                      'missing_evidence:macos_qualification')
            dispatch = contract['dispatch_id']
            assert ds.record(dispatch)['state'] == 'refused' and ds.receipt(dispatch, 'accept') is None
            assert backend.bootstraps == 0 and not seen
        finally:
            conn.close()

    def boundaries(base):
        for boundary in ('retry', 'follow_on'):
            receiver, contract, paths, backend, host, reservations, ds, conn, clean, seen = scenario(
                base / boundary, boundary=boundary)
            try:
                run = receiver.start(contract, str(paths['clone']), str(paths['scratch']))
                assert seen[0]['boundaries'] == [boundary]
                receiver.wait(run.dispatch)
            finally:
                conn.close()

    def retirement(base):
        receiver, contract, paths, backend, host, reservations, ds, conn, clean, seen = scenario(base)
        try:
            run = receiver.start(contract, str(paths['clone']), str(paths['scratch']))
            receiver.wait(run.dispatch)
            T.refused(lambda: receiver.retire(run.dispatch), 'cleanup_incomplete')
            clean[0] = True
            T.refused(lambda: receiver.retire(run.dispatch), 'missing_accounting')
            assert not reservations.worker(run.dispatch)['retired'] and host.status()['pending'] == 1
            entry = receiver.runs[run.dispatch]
            entry['guard'].observe('receipt', entry['invocation'], 1, {'wall_seconds': .06, 'invocations': 1},
                                   final=True, outcome='cancelled', now=backend.wall())
            receiver.retire(run.dispatch)
            assert reservations.worker(run.dispatch)['retired'] and host.status()['pending'] == 0
        finally:
            conn.close()

    def unknown(base):
        # The wrapper is lost with the engine's SIGKILL: exit seen, coalition empty,
        # cleanup done and accounting closed, but no result. Only the unknown outcome
        # guard stands between this and retiring the reservation.
        receiver, contract, paths, backend, host, reservations, ds, conn, clean, seen = scenario(base, mode='killed')
        try:
            run = receiver.start(contract, str(paths['clone']), str(paths['scratch']))
            assert receiver.wait(run.dispatch)['state'] == 'unknown'
            assert [s['stage'] for s in run.steps] == ['terminate', 'kill']
            assert not (run.directory / 'result.json').exists()
            clean[0] = True
            entry = receiver.runs[run.dispatch]
            entry['guard'].observe('unknown-receipt', entry['invocation'], 1, {}, final=True, outcome='timeout',
                                   now=backend.wall())
            assert run.retirement() == dict(terminated=True, cleaned=True, outcome_known=False,
                                            observer='macos_supervisor')
            T.refused(lambda: receiver.retire(run.dispatch), 'unknown_outcome:retirement')
            assert not reservations.worker(run.dispatch)['retired'], 'reservation retired with an unknown outcome'
            assert ds.active('unit', 'review')['state'] == 'unknown'
            assert reservations.balances('account', 'account')['invocations'] == 1
            assert host.status()['pending'] == 1
            T.refused(lambda: receiver.start(contract, str(paths['clone']), str(paths['scratch'])),
                      'stale_version:not_prepared')
        finally:
            conn.close()

    for name, test in {'AC1/accepted-store': accepted, 'AC1/refusals': refusals, 'AC2/precall-caps': caps,
                       'AC2/invocation-boundaries': boundaries, 'AC3/retirement-obligations': retirement,
                       'AC3/unknown-charge': unknown}.items():
        with tempfile.TemporaryDirectory(prefix='v124-control-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0124 ' + name, True)
            except Exception as error:
                print('  ' + name + ': ' + type(error).__name__ + ': ' + str(error)[:250])
                expect('VELDO-0124 ' + name, False)


_v124_control()
