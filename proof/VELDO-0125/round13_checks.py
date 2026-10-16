"""Round 13 regressions: real queue permissions and versioned profile migration."""
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch


def cases(T, helper):
    def migration(base):
        old = helper('r13_legacy', 'proof/VELDO-0124/checks.py')
        paths, profile, evidence, facts, request = old.fixture(base)
        profile = dict(profile, schema='veldo.macos_worker_profile/v1',
                       heartbeat_seconds=.02, heartbeat_window_seconds=.08)
        evidence['profile_digest'] = old.P.digest(profile)
        migrated = old.P.migrate(profile)
        assert profile['schema'].endswith('/v1') and 'heartbeat_seconds' in profile
        assert migrated['schema'].endswith('/v2')
        assert not any('heartbeat' in key for key in migrated)
        old.refused(lambda: old.P.qualify(migrated, evidence, facts, 'codex',
                    migrated['engines']['codex']['configuration_digest']), 'missing_evidence:')
        fresh = dict(evidence, profile_digest=old.P.digest(migrated))
        host = old.M.Supervisor(migrated, fresh, backend=old.FakeOS(facts, temp=paths['usertemp']))
        request['environment'].update(host.run_environment(request['contract']['dispatch_id'], request['scratch']))
        assert host.start(request).wait()['state'] == 'exited'

    def missing_index(base):
        P = helper('r13_mac', 'proof/VELDO-0125/macos_event_fixture.py')
        host, backend, request, paths = P.start(base / 'host')
        (host.root / '.live-slots.json').unlink()
        w = T.load('control_worker')
        config = dict(runs=str(base / 'runs'))
        config_path = base / 'config.json'
        config_path.write_text(json.dumps(config))
        w.install_resumer = lambda *args: None  # Already loaded, byte-identical launch agent.
        calls = []
        def receive(config, request):
            P.M.Supervisor(host.profile, host.qualification, backend=backend, migrate=False)
            calls.append(request)
            return dict(record=dict(state='exited'), host_released=True)
        w.receive_locked = receive
        output = io.StringIO()
        with patch.object(w.sys, 'stdin', io.StringIO('{"dispatch_id":"new"}\n')), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                w.main(config_path)
            except P.P.Refused as error:
                assert str(error) == 'unavailable_service:slot_migration_required'
        entries = w.OUT.entries(config, ready_only=True)
        assert len(entries) == 1, 'migration refusal parked the dispatch'
        assert entries[0]['attempts'] == 1 and entries[0]['due'] > w.time.time()
        assert not output.getvalue(), 'Linux was told the migration refusal was parked'
        # QueueDirectories starts the drain even when bootstrap did not run on upgrade.
        P.M.Supervisor(host.profile, host.qualification, backend=backend)
        with patch.object(w.time, 'time', return_value=entries[0]['due']):
            w.resume_pending(config, drain=True)
        assert len(calls) == 1 and not w.OUT.entries(config)

    def refused_recovery(base):
        for transient in (True, False):
            root = base / str(transient)
            root.mkdir()
            w = T.load('control_worker')
            config = dict(runs=str(root))
            config_path = root / 'config.json'
            config_path.write_text(json.dumps(config))
            due = w.time.time() + 300
            orphan = dict(request=dict(dispatch_id='orphan'), due=due, attempts=7)
            with w.OUT.locked(config) as locked:
                w.OUT.move(locked, w.OUT.locate(locked, 'orphan'), '.active', w.CL.durable_json, orphan)
            calls = []
            def fail(config, request):
                calls.append(request['dispatch_id'])
                raise OSError('offline') if transient else w.C.P.Refused('unauthorized:denied')
            w.receive_locked = fail
            w.install_resumer = lambda *args: None
            with patch.object(w.sys, 'stdin', io.StringIO('{"dispatch_id":"incoming"}\n')), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    w.main(config_path)
                except OSError:
                    assert transient
            assert orphan in w.OUT.entries(config, ready_only=True), 'refused receiver skipped orphan recovery'
            assert calls == ['incoming'], 'receiver attempted backlog network delivery'

    def unwritable_recorder(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='unwritable')
        (base / '.parked').mkdir()  # Reach rename, rather than failing mkdir first.
        w.OUT.enqueue(config, request, w.CL.durable_json)
        def fail(config, request):
            # Both JSON recording and parking now fail at the real filesystem.
            base.chmod(0o500)
            (base / '.active').chmod(0o500)
            raise OSError('authority offline')
        w.receive_locked = fail
        output = io.StringIO()
        caught = False
        try:
            with contextlib.redirect_stderr(output):
                try:
                    w.resume_pending(config, drain=True)
                except w.RecorderFailure:
                    caught = True
        finally:
            base.chmod(0o700)
            (base / '.active').chmod(0o700)
        assert caught, 'unwritable outbox silently swallowed recorder failure'
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        assert any(r['operation'] == 'worker_delivery_recorder_failed' for r in records), records
        parking = [r for r in records if r.get('operation') == 'worker_delivery_park_failed']
        assert len(parking) == 1 and ' -> ' in parking[0]['reason'], records
        retained = base / '.active' / w.OUT.key(request['dispatch_id'])
        assert json.loads(retained.read_text())['request'] == request
        assert not list((base / '.pending').iterdir())

    def unreadable_orphan(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        with w.OUT.locked(config) as root:
            bad = w.OUT.move(root, w.OUT.locate(root, 'unreadable'), '.active', w.CL.durable_json,
                             dict(request=dict(dispatch_id='unreadable'), due=0, attempts=0))
        bad.chmod(0)
        w.OUT.enqueue(config, dict(dispatch_id='healthy'), w.CL.durable_json)
        calls = []
        w.receive_locked = lambda config, request: calls.append(request['dispatch_id']) or dict(host_released=True)
        output = io.StringIO()
        try:
            with contextlib.redirect_stderr(output):
                for _ in range(2):
                    w.resume_pending(config, drain=True)
            assert calls == ['healthy'], 'unreadable orphan prevented healthy delivery'
            assert not w.OUT.entries(config), 'recovery left a relaunch condition'
            assert 'worker_recovery_failed' in output.getvalue(), 'recovery failure was silent'
            assert (base / '.parked' / bad.name).exists(), 'unreadable orphan was not isolated'
        finally:
            for path in (bad, base / '.parked' / bad.name):
                if path.exists():
                    path.chmod(0o600)

    return {'AC1/v1-profile-migration': migration,
            'AC3/missing-index-retries': missing_index,
            'AC3/refused-receiver-recovers-orphans': refused_recovery,
            'AC3/unwritable-outbox-reports-failure': unwritable_recorder,
            'AC3/unreadable-active-isolated': unreadable_orphan}
