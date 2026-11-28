"""VELDO-0147 rows: the login delivered to a Mac run, the refusal of an outside-service credential, and the
Mac run's ordered output kept as its execution record on the main node. The real Mac runs are under
proof/VELDO-0147/."""


def _v147_login():
    import importlib.util
    import io
    import json
    from pathlib import Path
    import tempfile

    # The registered falsifiers of the login module replace this path with a defective copy.
    login_module = ROOT / ".veldo" / "project_runner_macos_login.py"
    spec = importlib.util.spec_from_file_location('v147_login', login_module)
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    now = 1_900_000_000.0  # a fixed instant: frame() takes the clock as an argument

    def refused(call, code):
        try:
            call()
        except L.Refused as error:
            assert error.code == code, error.code
            return
        raise AssertionError('not refused: ' + code)

    def claude(base, **oauth):
        values = dict(accessToken='access-value-147', refreshToken='refresh-value-147', subscriptionType='pro',
                      expiresAt=(now + 7200) * 1000, scopes=['user:inference'])
        values.update(oauth)
        Path(base, '.credentials.json').write_text(json.dumps({'claudeAiOauth': values}))
        return base

    def claude_frame(base):
        body, values = L.frame('claude_code', claude(base), 'd-147', 'acct-test', now=now)
        document = json.loads(body)
        assert document['schema'] == L.SCHEMA and set(document['files']) == {'.credentials.json'}
        assert values == ['access-value-147']
        assert b'refresh-value-147' not in body and b'refreshToken' not in body
        assert json.loads(document['files']['.credentials.json'])['claudeAiOauth']['accessToken'] == 'access-value-147'

    def claude_refusals(base):
        refused(lambda: L.frame('claude_code', claude(base, expiresAt=(now + 60) * 1000), 'd', 'a', now=now),
                'unavailable_service:login_expires_before_run')
        refused(lambda: L.frame('claude_code', claude(base, subscriptionType=None), 'd', 'a', now=now),
                'unsupported_configuration:no_subscription_login')
        refused(lambda: L.frame('gemini', claude(base), 'd', 'a', now=now), 'unsupported_configuration:engine')
        # The login must outlive the run's own deadline by the margin, not only the next half hour.
        refused(lambda: L.frame('claude_code', claude(base), 'd', 'a', now=now, deadline=now + 6000),
                'unavailable_service:login_expires_before_run')
        assert L.frame('claude_code', claude(base), 'd', 'a', now=now, deadline=now + 5000)[1] == ['access-value-147']

    def codex_frame(base):
        import base64

        def access(expires):
            # An access credential shaped as Codex keeps it: a JWT whose payload carries `exp`.
            payload = base64.urlsafe_b64encode(json.dumps(dict(exp=expires)).encode()).decode().rstrip('=')
            return 'header147.' + payload + '.signature147'

        def write(token, **top):
            auth = dict(OPENAI_API_KEY=None, last_refresh='2026-11-26T00:00:00Z', auth_mode='chatgpt',
                        tokens=dict(id_token='id-147', access_token=token, refresh_token='ref-147', account_id='x'))
            auth.update(top)
            Path(base, 'auth.json').write_text(json.dumps(auth))
        good = access(now + 7200)
        write(good, added_by_a_later_build='top-level-secret-147')
        body, values = L.frame('codex', base, 'd', 'codex-test', now=now)
        assert b'ref-147' not in body and sorted(values) == sorted([good, 'id-147'])
        sent = json.loads(json.loads(body)['files']['auth.json'])
        # The field the pinned binary requires is present and empty: nothing on the Mac can rotate the login.
        assert sent['tokens']['refresh_token'] == ''
        # Named top-level fields only: one a later build adds is not sent.
        assert set(sent) == {'OPENAI_API_KEY', 'auth_mode', 'last_refresh', 'tokens'}, sorted(sent)
        assert b'top-level-secret-147' not in body and sent['OPENAI_API_KEY'] is None
        # An access credential that ends before the run could, or whose end cannot be read, is refused by name.
        write(access(now + 60))
        refused(lambda: L.frame('codex', base, 'd', 'a', now=now), 'unavailable_service:login_expires_before_run')
        write(good)
        refused(lambda: L.frame('codex', base, 'd', 'a', now=now, deadline=now + 6000),
                'unavailable_service:login_expires_before_run')
        assert L.frame('codex', base, 'd', 'a', now=now, deadline=now + 5000)[1]
        write('not-a-jwt-147')
        refused(lambda: L.frame('codex', base, 'd', 'a', now=now), 'unavailable_service:login_expires_before_run')
        write(good, OPENAI_API_KEY='sk-147')
        refused(lambda: L.frame('codex', base, 'd', 'a', now=now), 'unsupported_configuration:no_subscription_login')

    def login_disk(base):
        # The Mac's disk steps over a recorded hdiutil, diskutil and mount (Linux has none; the real ones are
        # the Mac run's evidence). The disk's device nodes end readable by their owner only before the login is
        # written; a node that will not take that mode refuses the login; and close detaches a disk only when
        # the mount table shows it on this base's own mount point.
        from types import SimpleNamespace
        from unittest.mock import patch
        import os
        import shutil
        mounts, calls, chmod = {}, [], os.chmod
        nodes = [base / 'disk99', base / 'rdisk99']

        def run(argv):
            calls.append(argv[:2])
            out = ''
            if argv[:2] == ['/usr/bin/hdiutil', 'attach']:
                out = '/dev/disk99          \n'
                for node in nodes:
                    node.write_bytes(b'')
                    chmod(node, 0o640)  # as macOS could hand them out: group read
            elif argv[0] == '/usr/sbin/diskutil':
                mounts[str(Path(argv[3]).resolve())] = argv[4]
            elif argv[0] == '/sbin/mount':
                out = ''.join('%s on %s (hfs, local, nodev, nosuid, noowners)\n' % (d, m) for m, d in mounts.items())
            elif argv[:2] == ['/usr/bin/hdiutil', 'detach']:
                for place in [m for m, d in mounts.items() if d == argv[3]]:
                    del mounts[place]
                    for item in Path(place).iterdir():  # the volume's files go with the disk
                        item.unlink()
            return SimpleNamespace(returncode=0, stdout=out)
        frame = io.BytesIO(L.frame('claude_code', claude(base), 'd-147', 'acct-test', now=now)[0])
        with patch.object(L, '_run', run), patch.object(L, '_nodes', lambda device: [str(node) for node in nodes]):
            target = base / 'login'
            report = L.open_profile(target, frame)
            assert report['device_modes']['attached'] == {'disk99': '0o640', 'rdisk99': '0o640'}, report['device_modes']
            assert report['device_modes']['final'] == {'disk99': '0o600', 'rdisk99': '0o600'}, report['device_modes']
            assert all(node.stat().st_mode & 0o777 == 0o600 for node in nodes)
            assert (target / 'profile' / '.credentials.json').stat().st_mode & 0o777 == 0o600
            closed = L.close_profile(target)
            assert closed['status'] == 'closed' and closed['detached'] is True and not target.exists(), closed
            assert calls.count(['/usr/bin/hdiutil', 'detach']) == 1
            # A base left from before a restart: its kept name now belongs to a disk mounted somewhere else.
            stale, other = base / 'stale', base / 'another-run'
            (stale / 'profile').mkdir(parents=True)
            other.mkdir()
            (stale / 'device').write_text('/dev/disk99\n')
            mounts[str(other.resolve())] = '/dev/disk99'
            closed = L.close_profile(stale)
            assert closed['status'] == 'closed' and closed['detached'] is None and not stale.exists(), closed
            assert calls.count(['/usr/bin/hdiutil', 'detach']) == 1, 'a disk mounted elsewhere was detached'
            assert mounts == {str(other.resolve()): '/dev/disk99'}
            # A disk that stays mounted is reported as left behind, and its name is kept for the next close.
            held = base / 'held'
            (held / 'profile').mkdir(parents=True)
            (held / 'device').write_text('/dev/disk77\n')
            mounts[str((held / 'profile').resolve())] = '/dev/disk77'
            failing = lambda argv: SimpleNamespace(returncode=1, stdout='') if argv[:2] == ['/usr/bin/hdiutil', 'detach'] else run(argv)
            with patch.object(L, '_run', failing):
                closed = L.close_profile(held)
            assert closed['status'] == 'left_behind' and closed['detached'] is False, closed
            assert (held / 'device').read_text() == '/dev/disk77\n'
            assert L.close_profile(held)['status'] == 'closed' and not held.exists()
            # A node that keeps a group or other bit: no login is written and the disk it attached goes.
            frame.seek(0)
            with patch.object(L.os, 'chmod', lambda *arguments, **named: None):
                refused(lambda: L.open_profile(base / 'open-node', frame), 'unavailable_service:ram_disk_private')
            assert not (base / 'open-node').exists() and calls[-1] != ['/usr/sbin/diskutil', 'mount']
            assert calls.count(['/usr/sbin/diskutil', 'mount']) == 1

    def mac_side_refusals(base):
        # Every malformed frame is refused before a directory or RAM disk is made.
        class Stream:
            def __init__(self, data):
                self.buffer = io.BytesIO(data)
        good = json.dumps(dict(schema=L.SCHEMA, engine='claude_code', files={'.credentials.json': '{}'}))
        for data, code in ((json.dumps(dict(json.loads(good), schema='other')), 'invalid_input:frame'),
                           (json.dumps(dict(json.loads(good), files={'.credentials.json': '{}', 'x': ''})),
                            'invalid_input:frame_files'),
                           ('x' * (L.MAX_FRAME + 1), 'invalid_input:frame_size')):
            target = Path(base, 'login')
            refused(lambda: L.open_profile(target, Stream(data.encode())), code)
            assert not target.exists()
        Path(base, 'exists').mkdir()
        refused(lambda: L.open_profile(Path(base, 'exists'), Stream(good.encode())), 'stale_version:profile_base_exists')

    # The registered falsifiers (scripts/check_teeth_mutations.py, finding 147) replace these production
    # paths with a defective copy inside a complete module tree; every row below loads its modules from there.
    profile_module = ROOT / ".veldo" / "project_runner_macos_profile.py"
    control_module = ROOT / ".veldo" / "project_runner_macos_control.py"

    def mac_checks(directory):
        import os
        os.environ['VELDO_0124_MODULES'] = str(Path(directory))
        try:
            loaded = importlib.util.spec_from_file_location('v147_checks', ROOT / 'proof/VELDO-0124/checks.py')
            checks = importlib.util.module_from_spec(loaded)
            loaded.loader.exec_module(checks)
            return checks
        finally:
            os.environ.pop('VELDO_0124_MODULES', None)

    def unexpected_launch(base):
        # AC1 falsifier: the Mac's pinned executable changes after it was bound; the Mac host must refuse
        # before anything is launched, so no engine the qualification did not bind ever runs.
        T = mac_checks(profile_module.parent)
        host, osx, request, paths = T.start(base)
        engine = request['engine']
        pinned = base / 'pinned-engine'
        pinned.write_bytes(b'#!/bin/sh\nexit 0\n')
        host.profile['engines'][engine]['argv'][0] = str(pinned)
        host.profile['engines'][engine]['binary_digest'] = T.P.file_digest(str(pinned))
        T.evidence_fixture(host.profile, host.qualification)
        T.P.qualify(host.profile, host.qualification, host.os.facts(), engine,
                    request['contract']['capability']['configuration_digest'])  # bound: admitted
        with open(pinned, 'ab') as stream:
            stream.write(b'# changed after binding\n')
        T.refused(lambda: host.start(request), 'stale_version:engine_binary')
        assert osx.bootstraps == 0

    def paid_api_stop(base):
        # AC2 falsifier: OPENAI_API_KEY must never reach the Mac engine environment: an adapter that
        # configures it is refused by name, and the inherited set never carries it.
        loaded = importlib.util.spec_from_file_location('v147_control', control_module)
        C = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(C)

        class Host:
            class os:
                @staticmethod
                def facts():
                    return {'host': 'mac-147'}

            @staticmethod
            def run_environment(dispatch, scratch):
                return {'HOME': scratch + '/home'}
        account = dict(id='codex-147', status='active', provider='codex', profiles={'mac-147': str(base / 'login')})
        login, environment = C.engine_environment(Host, account, 'd-147', str(base), {})
        assert login == str(base / 'login') and environment['CODEX_HOME'] == login
        assert 'OPENAI_API_KEY' not in environment and 'CODEX_API_KEY' not in environment
        for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
            try:
                C.engine_environment(Host, account, 'd-147', str(base), {key: 'sk-planted-147'})
            except Exception as error:
                assert getattr(error, 'code', '') == 'invalid_input:adapter_environment:' + key, error
            else:
                raise AssertionError('paid-API key reached the Mac engine environment: ' + key)

    def codex_roots(base):
        # AC2: the Mac run's sandbox denies the keychain service Codex reads its root certificates from, so
        # a Codex run is pointed at the system's root file; a Claude Code run is not. Which roots a run
        # trusts is never the configuration's to say: a configured root file or directory is refused by name.
        loaded = importlib.util.spec_from_file_location('v147_control_roots', control_module)
        C = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(C)

        class Host:
            class os:
                @staticmethod
                def facts():
                    return {'host': 'mac-147'}

            @staticmethod
            def run_environment(dispatch, scratch):
                return {'HOME': scratch + '/home'}
        codex = dict(id='codex-147', status='active', provider='codex', profiles={'mac-147': str(base / 'login')})
        claude = dict(id='claude-147', status='active', provider='claude_code',
                      profiles={'mac-147': str(base / 'claude')})
        assert C.engine_environment(Host, codex, 'd-147', str(base), {})[1].get('SSL_CERT_FILE') == '/etc/ssl/cert.pem'
        assert 'SSL_CERT_FILE' not in C.engine_environment(Host, claude, 'd-147', str(base), {})[1]
        for account in (codex, claude):
            for variable in ('SSL_CERT_FILE', 'SSL_CERT_DIR'):
                try:
                    C.engine_environment(Host, account, 'd-147', str(base), {variable: str(base / 'roots.pem')})
                except Exception as error:
                    assert getattr(error, 'code', '') == 'invalid_input:adapter_environment:' + variable, error
                else:
                    raise AssertionError('a configured root list reached the Mac engine environment: ' + variable)

    launch_module = ROOT / ".veldo" / "control_launch.py"
    worker_module = ROOT / ".veldo" / "control_worker.py"
    record_module = ROOT / ".veldo" / "control_execution_record.py"
    service_module = ROOT / ".veldo" / "control_worker_service.py"
    # A registered falsifier replaces one of the paths above with its defective copy, which sits in a
    # complete module tree. Every relay row loads all its modules from that one tree, or from production.
    modules_tree = next((module.parent for module in (launch_module, worker_module, record_module, service_module,
                                                      login_module)
                         if module.parent != profile_module.parent), profile_module.parent)

    def relay_fixture(base):
        """The VELDO-0125 authority fixture over this tree's modules, with one prepared Claude dispatch whose
        account's main-node profile holds a subscription login good far past any run."""
        import os
        os.environ['VELDO_0125_MODULES'] = str(modules_tree)
        try:
            loaded = importlib.util.spec_from_file_location('v147_relay', ROOT / 'proof/VELDO-0125/checks.py')
            T = importlib.util.module_from_spec(loaded)
            loaded.loader.exec_module(T)
        finally:
            os.environ.pop('VELDO_0125_MODULES', None)
        f = T.Fixture(base / 'authority')
        launch = T.W.SV.L
        profile = base / 'main-profile'
        profile.mkdir()
        claude(profile, expiresAt=4_102_444_800_000)
        record = dict(id='account', status='active', provider='claude_code', profiles={'main': str(profile)})
        launch.ACC.read = lambda conn, account: record if account == 'account' else None
        # The catalog as the launcher reads it: `tracker` names a credential, `notes` names none. A test selects
        # one by filling `selected`. Nothing may resolve a reference: the keystore entry raises.
        catalog = {'tracker': dict(id='tracker', environment={}, headers={'Authorization': {'reference': 'keychain:veldo/tracker-token'}}),
                   'notes': dict(id='notes', environment={'MODE': {'literal': 'read'}}, headers={})}
        selected = []
        launch.DL.selections = lambda configuration: list(selected)
        launch.DL.MC.revision_id = lambda domain, server, revision: server
        launch.DL.MC.entity = lambda conn, identity: dict(kind=launch.DL.MC.KIND, data=catalog[identity]) if identity in catalog else None

        def resolved(*arguments, **named):
            raise AssertionError('a keystore reference was resolved for a Mac run')
        launch.DL.resolve = resolved
        f.selected = selected
        return T, f, launch

    def sink(base):
        import sys
        received = base / 'received'
        return received, dict(argv=[sys.executable, '-c', 'import sys; open(sys.argv[1], "wb").write(sys.stdin.buffer.read())',
                                    str(received)], login='delivered', main_host='main')

    def relay_frames(base):
        # AC4 on the relay transport: the binding line is identity only and the login is the one frame after
        # it. No outside-service credential value is sent anywhere: a run that selects a server needing one
        # is refused by name before a receiver is contacted, and nothing is resolved.
        T, f, launch = relay_fixture(base)
        try:
            contract = f.prepare(required=['macos'], engine='claude_code')['contract']
            assert launch.remote_frames(dict(argv=['x']), contract, f.conn) == ([], None, [])
            received, receiver = sink(base)
            started = launch.invoke_remote(receiver, contract, f.ds)
            assert started.result == 'pending', (started.result, (started.record or {}).get('refusal'))
            started.child.wait(timeout=T.WAIT_HANG_SECONDS)
            lines = received.read_bytes().splitlines()
            assert len(lines) == 2, len(lines)
            packet = json.loads(lines[0])
            assert set(packet) == {'dispatch_id', 'contract_digest', 'domain', 'repository'}, sorted(packet)
            values = (b'access-value-147', b'refresh-value-147')
            assert not any(value in lines[0] for value in values), 'a credential value is in the packet'
            login = json.loads(lines[1])
            assert login['schema'] == L.SCHEMA and login['dispatch'] == contract['dispatch_id'] and login['account'] == 'account'
            assert b'access-value-147' in lines[1] and b'refresh' not in lines[1]
            report = started.delivered
            assert report['credentials'] == [] and report['routes'] == [] and report['account'] == 'account'
            assert report['login_frame'] and 'secrets_frame' not in report
            started.stop()
            kept = json.dumps([report, contract, f.ds.record(contract['dispatch_id'])]).encode()
            f.conn.commit()
            kept += b''.join(path.read_bytes() for path in sorted(f.store.parent.glob(f.store.name + '*')))
            assert not any(value in kept for value in values), 'a credential value was kept on the main node'
        finally:
            f.close()

    def mcp_refused(base):
        # A run on a remote host starts its engine with no MCP server, so a configuration that selects one is
        # refused by name before a receiver is contacted: a server that needs a credential and one that needs
        # none, and whether or not the receiver is one the login is delivered to. Nothing is resolved.
        T, f, launch = relay_fixture(base)
        try:
            received, delivered = sink(base)
            plain = dict(argv=delivered['argv'])
            for number, (server, receiver) in enumerate((('tracker', delivered), ('notes', delivered),
                                                         ('tracker', plain), ('notes', plain))):
                del f.selected[:]
                f.selected.append((server, 1))
                unit = 'unit-mcp-%d' % number
                f.res.configure('policy/' + unit, 'unit', unit, dict(capacity=20, invocations=20, wall_seconds=4000), now=f.clock())
                contract = f.prepare(dispatch='dispatch/mcp-%d' % number, required=['macos'], engine='claude_code', unit=unit)['contract']
                refused_launch = launch.invoke_remote(receiver, contract, f.ds)
                assert refused_launch.result == 'refused' and refused_launch.child is None, (server, refused_launch.result)
                assert refused_launch.record['refusal'] == 'unsupported_configuration:mcp_on_remote:' + server, refused_launch.record['refusal']
                assert refused_launch.delivered['refusal'] == refused_launch.record['refusal']
                assert 'no MCP server' in refused_launch.delivered['reason'] and not received.exists()
        finally:
            f.close()

    def relay_refusal(base):
        # A login that cannot be delivered refuses the dispatch by name and contacts no receiver.
        T, f, launch = relay_fixture(base)
        try:
            contract = f.prepare(required=['macos'], engine='claude_code')['contract']
            launch.ACC.read = lambda conn, account: None
            received, receiver = sink(base)
            refused_launch = launch.invoke_remote(receiver, contract, f.ds)
            assert refused_launch.result == 'refused' and refused_launch.child is None
            assert refused_launch.record['refusal'] == 'missing_authority:account', refused_launch.record['refusal']
            assert not received.exists()
        finally:
            f.close()

    def mac_delivery(base):
        # The Mac receiver's side: the one login frame checked before a disk is made, any other line refused
        # by name (a secrets frame among them), and nothing left after close.
        login, _ = L.frame('claude_code', claude(base), 'd-147', 'acct-test', now=now)
        secrets = json.dumps(dict(schema='veldo.macos_secrets_frame/v1', dispatch='d-147', account='acct-test',
                                  credentials=['tracker-token'], files={'mcp.json': '{}'})).encode()
        target = base / 'login'
        for lines, arguments, code in (
                (None, ('d-147', 'acct-test', 'claude_code'), 'missing_evidence:login_frame'),
                ([secrets], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([login], ('d-other', 'acct-test', 'claude_code'), 'binding_mismatch:login_frame'),
                ([login], ('d-147', 'acct-other', 'claude_code'), 'binding_mismatch:login_frame'),
                ([login], ('d-147', 'acct-test', 'codex'), 'binding_mismatch:login_frame'),
                ([login, secrets], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([login, login], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([b'{"schema": "other"}'], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([b'x' * (L.MAX_FRAME + 1)], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame_size')):
            refused(lambda: L.Delivery(lines, target, *arguments), code)
        assert not target.exists()
        assert not hasattr(L, 'secrets_frame') and not hasattr(L, 'write_secrets') and not hasattr(L.Delivery, 'secrets')
        delivery = L.Delivery([login.decode()], target, 'd-147', 'acct-test', 'claude_code')
        mounted = []

        def fake_open(directory, stream):
            # Linux has no hdiutil: the mount is a plain directory here; the real one is the Mac run's evidence.
            assert json.loads(stream.read())['files']
            (Path(directory) / 'profile').mkdir(parents=True, mode=0o700)
            mounted.append(Path(directory) / 'profile')
            return dict(status='open')

        def fake_close(directory):
            import shutil
            shutil.rmtree(directory)
            mounted.clear()
            return dict(status='closed')
        real = L.open_profile, L.close_profile
        L.open_profile, L.close_profile = fake_open, fake_close
        try:
            assert delivery.open() == str(target / 'profile')
            assert sorted(path.name for path in target.iterdir()) == ['profile'] and not any((target / 'profile').iterdir())
            assert delivery.close() == dict(status='closed') and not target.exists()
            assert delivery.close() == dict(status='closed')  # a second close finds nothing and changes nothing
        finally:
            L.open_profile, L.close_profile = real

    # ---- AC3: the Mac run's output, kept on the main node as its execution record -------------------------

    # What the fixture engine prints: both streams, a line carrying the delivered login's value, and a last
    # line with no newline. Whole lines per write, flushed, so each is one chunk of its pipe.
    ENGINE = ('import sys\n'
              'for number in range(3):\n'
              '    sys.stdout.write("out %d token=access-value-147\\n" % number); sys.stdout.flush()\n'
              '    sys.stderr.write("err %d\\n" % number); sys.stderr.flush()\n'
              'sys.stdout.write("last out, no newline"); sys.stdout.flush()\n')
    # The Mac's half, run as the receiver's transport: it reads the binding and the login frame, runs the
    # fixture engine under the production wrapper's pump, sends the ordered file with the production
    # receiver's Relay, and leaves the wrapper's totals where the row reads them. `alter` changes one chunk
    # between the Mac and the main node.
    MAC = ('import importlib.util, json, os, subprocess, sys\n'
           'modules, work, alter = sys.argv[1], sys.argv[2], sys.argv[3]\n'
           'sys.path.insert(0, modules)\n'
           'def load(name):\n'
           '    spec = importlib.util.spec_from_file_location("mac_" + name, os.path.join(modules, name + ".py"))\n'
           '    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module\n'
           'wrapper, worker = load("project_runner_macos_wrapper"), load("control_worker")\n'
           'frames = worker.S\n'
           'sys.stdin.readline(); sys.stdin.readline()\n'
           'class Channel:\n'
           '    count = 0\n'
           '    def write(self, data):\n'
           '        parsed = frames.parse(data)\n'
           '        if alter == "noend" and parsed and parsed[0] == frames.END:\n'
           '            return\n'
           '        if alter == "alter" and parsed and parsed[0] == "stderr":\n'
           '            Channel.count += 1\n'
           '            if Channel.count == 1:\n'
           '                data = frames.chunk("stderr", parsed[1].replace(b"err", b"ERR"))\n'
           '        sys.stdout.buffer.write(data)\n'
           '    def flush(self):\n'
           '        sys.stdout.buffer.flush()\n'
           'relay = worker.Relay(Channel())\n'
           'relay.start(os.path.join(work, frames.FILE))\n'
           'tally = frames.Tally()\n'
           'child = subprocess.Popen([sys.executable, os.path.join(work, "engine.py")], stdin=subprocess.DEVNULL,\n'
           '                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n'
           'wake = os.pipe()\n'
           'with open(os.path.join(work, "engine.out"), "wb", buffering=0) as out, \\\n'
           '        open(os.path.join(work, "engine.err"), "wb", buffering=0) as err, \\\n'
           '        open(os.path.join(work, frames.FILE), "wb", buffering=0) as framed:\n'
           '    whole = wrapper.pump([("stdout", child.stdout, out), ("stderr", child.stderr, err)], framed, tally, wake[0])\n'
           'child.wait()\n'
           'relay.finish()\n'
           'with open(os.path.join(work, "totals.json"), "w") as stream:\n'
           '    json.dump(dict(whole=whole, totals=tally.totals()), stream)\n'
           'print(json.dumps(dict(state="exited")), flush=True)\n')

    def mac_run(base, alter='whole', transport=None):
        """One prepared Mac dispatch run to its signed end: (T, f, launch module, started launch, contract,
        the Mac's work directory, the wrapper's totals). The signed result carries the wrapper's totals."""
        import sys
        T, f, launch = relay_fixture(base)
        work = base / 'mac'
        work.mkdir()
        (work / 'engine.py').write_text(ENGINE)
        (work / 'mac.py').write_text(MAC)
        contract = f.prepare(required=['macos'], engine='claude_code')['contract']
        f.start()
        client = f.client()
        receiver = dict(argv=transport or [sys.executable, str(work / 'mac.py'), str(modules_tree), str(work), alter],
                        login='delivered', main_host='main')
        started = launch.invoke_remote(receiver, contract, f.ds)
        assert started.result == 'pending', (started.result, (started.record or {}).get('refusal'))
        binding = T.launch(client, contract['dispatch_id'])
        totals = None
        if transport is None:
            started.child.wait(timeout=T.WAIT_HANG_SECONDS)
            kept = json.loads((work / 'totals.json').read_text())
            assert kept['whole'], 'the wrapper could not write a chunk'
            totals = kept['totals']
        return T, f, launch, started, contract, work, totals, client, binding

    def expected_lines(work, frames):
        """The lines the engine emitted on the Mac, in the order of the Mac's one ordered file: (record
        stream, text). A stream's last line with no newline comes at the end, as the record keeps it."""
        pending, lines = {'stdout': b'', 'stderr': b''}, []
        for raw in (work / frames.FILE).read_bytes().splitlines():
            name, data = frames.parse(raw)
            *whole, pending[name] = (pending[name] + data).split(b'\n')
            lines += [(name, line.decode()) for line in whole]
        return lines + [(name, rest.decode()) for name, rest in pending.items() if rest]

    def complete_record(base):
        # AC3, the Mac complete-record check: the record kept on the main node holds, line by line and in the
        # order of the Mac's ordered stream, what the engine emitted there, the error stream included, with
        # the delivered login's value replaced; the totals this node computed equal the ones the Mac signed.
        T, f, launch, started, contract, work, totals, client, binding = mac_run(base)
        try:
            frames, ER, dispatch = launch.MS, launch.ER, contract['dispatch_id']
            assert totals['stderr']['lines'] == 3 and totals['stdout']['lines'] == 4, totals
            assert (work / 'engine.err').read_bytes() == b'err 0\nerr 1\nerr 2\n'
            client.result(binding, dict(T.observation(), streams=totals), references={})
            record = started.wait(timeout=T.WAIT_HANG_SECONDS)
            assert record['state'] == 'exited' and record['execution_record'] == {'streams': totals}, record.get('execution_record')
            assert started.received['ended'] and started.received['streams'] == totals, started.received
            assert started.record_refusal is None, started.record_refusal
            records = ER.directory({'store': str(f.store)})
            page = ER.read(records, dispatch, 0, 1000, committed=record['execution_record'])
            emitted = expected_lines(work, frames)
            assert [name for name, _ in emitted if name == 'stderr'] and len(emitted) == 7, emitted
            assert [text for name, text in emitted if name == 'stdout'][:3] == ['out %d token=access-value-147' % n for n in range(3)]
            kept = [({'engine': 'stdout', 'stderr': 'stderr'}[line['stream']], line['payload']) for line in page['lines']]
            marker = ER.marker('subscription_token')
            assert kept == [(name, text.replace('access-value-147', marker)) for name, text in emitted], (kept, emitted)
            assert [line['seq'] for line in page['lines']] == list(range(1, 8))
            assert b'access-value-147' not in Path(ER.path(records, dispatch)).read_bytes()
            assert all('subscription_token' in line['redacted'] for line in page['lines'] if marker in line['payload'])
        finally:
            f.close()

    def altered_chunk(base):
        # One chunk changed between the Mac and the main node, same length: the main node's totals no longer
        # equal the signed ones, so the launch names the refusal and every reader of the record is refused.
        T, f, launch, started, contract, work, totals, client, binding = mac_run(base, alter='alter')
        try:
            ER, dispatch = launch.ER, contract['dispatch_id']
            client.result(binding, dict(T.observation(), streams=totals), references={})
            record = started.wait(timeout=T.WAIT_HANG_SECONDS)
            assert record['state'] == 'exited' and record['execution_record'] == {'streams': totals}
            assert started.received['ended'] and started.received['streams']['stdout'] == totals['stdout']
            assert started.received['streams']['stderr']['bytes'] == totals['stderr']['bytes']
            assert started.received['streams']['stderr']['sha256'] != totals['stderr']['sha256']
            assert started.record_refusal == 'unknown_outcome:record_incomplete', started.record_refusal
            records = ER.directory({'store': str(f.store)})
            try:
                ER.read(records, dispatch, 0, 1000, committed=record['execution_record'])
            except ER.Refused as error:
                assert error.code == 'unknown_outcome:record_incomplete', error.code
            else:
                raise AssertionError('an altered record was served')
        finally:
            f.close()

    def resumed_run(base):
        # A run whose channel ended before the engine did (the receiver crashed and the run was resumed with
        # no channel): the Mac still signs what the engine printed, the main node received none of it, and
        # the record is refused by name; so is one whose receiver kept nothing at all. A signed result whose
        # totals are malformed is refused before it ends the dispatch.
        import sys
        # The transport prints its last line and then more than one read of other lines, so the launch ends
        # it with output still in the pipe and takes that through its own line reader (found on the real Mac).
        T, f, launch, started, contract, work, totals, client, binding = mac_run(
            base, transport=[sys.executable, '-c', 'import sys; sys.stdin.read(); '
                             'sys.stdout.write(\'{"state": "ended"}\\n\' + (\'x\' * 999 + \'\\n\') * 100); sys.stdout.flush()'])
        try:
            frames, ER, dispatch = launch.MS, launch.ER, contract['dispatch_id']
            tally = frames.Tally()
            tally.feed('stdout', b'printed after the channel ended\n')
            tally.feed('stderr', b'and an error line\n')
            signed = tally.totals()
            T.refused(lambda: client.result(binding, dict(T.observation(), streams=dict(signed, stdout={'lines': 1})),
                                            references={}), 'invalid_input:streams')
            assert f.ds.record(dispatch)['state'] == 'running'
            client.result(binding, dict(T.observation(), streams=signed), references={})
            record = started.wait(timeout=T.WAIT_HANG_SECONDS)
            assert record['state'] == 'exited' and record['execution_record'] == {'streams': signed}
            assert not started.received['ended'] and started.received['streams']['stdout']['bytes'] == 0
            assert started.last_line and started.pending == b'', 'the launch left unread lines'
            assert started.record_refusal == 'unknown_outcome:record_incomplete', started.record_refusal
            records = ER.directory({'store': str(f.store)})

            def refused_by_name():
                try:
                    ER.read(records, dispatch, 0, 1000, committed=record['execution_record'])
                except ER.Refused as error:
                    return error.code
                return None
            assert refused_by_name() == 'unknown_outcome:record_incomplete'
            Path(ER.received_path(ER.path(records, dispatch))).unlink()
            assert refused_by_name() == 'unknown_outcome:record_incomplete'
        finally:
            f.close()

    def refused_read(ER, records, dispatch, record):
        """The refusal of the API's read of an ended run's record: it passes what the exit committed."""
        assert record['state'] == 'exited' and record['execution_record'] is not None, record.get('execution_record')
        try:
            ER.read(records, dispatch, 0, 1000, committed=record['execution_record'])
        except ER.Refused as error:
            return error.code
        return None

    def missing_end_frame(base):
        # Every chunk arrived and the totals equal the signed ones, but the channel stopped before the end
        # frame: that is not a finished stream, and the record is refused by name.
        T, f, launch, started, contract, work, totals, client, binding = mac_run(base, alter='noend')
        try:
            ER, dispatch = launch.ER, contract['dispatch_id']
            client.result(binding, dict(T.observation(), streams=totals), references={})
            record = started.wait(timeout=T.WAIT_HANG_SECONDS)
            assert started.received['streams'] == totals and started.received['ended'] is False, started.received
            assert started.record_refusal == 'unknown_outcome:record_incomplete', started.record_refusal
            assert refused_read(ER, ER.directory({'store': str(f.store)}), dispatch, record) == 'unknown_outcome:record_incomplete'
        finally:
            f.close()

    def unsigned_streams(base):
        # A Mac that lost a chunk signs that it has no totals: the result is refused by name and ends nothing.
        # A Mac whose result names no totals at all (an older wrapper) ends the run, and the exit commits that
        # there are none, so the API's read of the record this node kept is refused by name, not served.
        T, f, launch, started, contract, work, totals, client, binding = mac_run(base)
        try:
            ER, dispatch = launch.ER, contract['dispatch_id']
            T.refused(lambda: client.result(binding, dict(T.observation(), streams=None), references={}),
                      'missing_evidence:streams')
            assert f.ds.record(dispatch)['state'] == 'running'
            client.result(binding, T.observation(), references={})
            record = started.wait(timeout=T.WAIT_HANG_SECONDS)
            assert record['state'] == 'exited' and record['execution_record'] == {'streams': None}, record.get('execution_record')
            assert started.received['ended'] and started.received['streams'] == totals, started.received
            assert started.record_refusal == 'unknown_outcome:record_incomplete', started.record_refusal
            records = ER.directory({'store': str(f.store)})
            assert Path(ER.path(records, dispatch)).stat().st_size > 0
            assert refused_read(ER, records, dispatch, record) == 'unknown_outcome:record_incomplete'
        finally:
            f.close()

    def worker(name):
        loaded = importlib.util.spec_from_file_location(name, modules_tree / 'control_worker.py')
        W = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(W)
        return W

    def stalled_channel(base):
        # The main node's channel is stalled but not closed, so the sender's write does not return. The
        # receiver stops waiting for it after its bound and sends nothing more, the end frame included.
        import threading
        W = worker('v147_worker_stalled')
        frames, release, writes = W.S, threading.Event(), []

        class Channel:
            def write(self, data):
                writes.append(data)
                if len(writes) == 1:
                    release.wait(WAITS.WAIT_HANG_SECONDS)  # the stalled write; the row releases it itself

            def flush(self):
                pass
        relay = W.Relay(Channel())
        relay.JOIN_SECONDS = 0.2
        (base / frames.FILE).write_bytes(frames.chunk('stdout', b'one line\n'))
        relay.start(base / frames.FILE)
        sender = relay.thread
        try:
            relay.finish()
            assert relay.broken and relay.stalled and sender.is_alive(), (relay.broken, relay.stalled)
            assert len(writes) == 1, 'something was written to a stalled channel'
        finally:
            release.set()
            sender.join(WAITS.WAIT_HANG_SECONDS)
        # The same channel once it moves again: a relay that is not stalled ends with its end frame.
        whole = W.Relay(Channel())
        whole.start(base / frames.FILE)
        whole.finish()
        assert not whole.stalled and len(writes) == 3 and frames.parse(writes[-1])[0] == frames.END, len(writes)

    def login_left_behind(base):
        # The Mac cannot detach the login's disk. The result it signs says so, and the slot is not retired:
        # the release stays pending until a later close removes the login.
        import os
        from types import SimpleNamespace
        W = worker('v147_worker_release')
        key = base / 'signing-key'
        key.write_text('')
        (base / 'run').mkdir()
        login = base / 'login'
        login.mkdir()
        calls, signed, status = [], [], ['left_behind']

        def close_profile(directory):
            if status[0] == 'closed':
                Path(directory).rmdir()
            return dict(status=status[0], detached=status[0] == 'closed')
        real, real_c = W.organ, W.C.organ
        W.organ = lambda name: SimpleNamespace(close_profile=close_profile) if name == 'project_runner_macos_login' else real(name)
        W.C.organ = lambda name: SimpleNamespace(identity=lambda pid: dict(pid=pid)) if name == 'project_runner_macos_os' else real_c(name)

        class Host:
            profile = dict(signing_keys=[str(key)], runtime_seconds=5)
            delivered_login = login
            os = SimpleNamespace(facts=lambda: dict(host='mac-147', platform='darwin'))
            run_environment = staticmethod(lambda dispatch, scratch: {'HOME': scratch + '/home'})
            preflight = staticmethod(lambda request: None)
            release_authority = staticmethod(lambda *arguments: calls.append('release_authority'))

            @staticmethod
            def start(request):
                return SimpleNamespace(directory=base, temp=None, process=dict(pid=1), state='exited',
                                       wait=lambda: dict(state='exited', termination=dict(returncode=0)),
                                       retirement=lambda: {}, stop=lambda reason: None)

        class Client:
            signing_key, outbox = str(key.resolve()), None
            launch = staticmethod(lambda binding, phase, **fields: dict(record=dict(acceptance='accepted-147')))

            @staticmethod
            def result(binding, observation, usage=None, references=None):
                signed.append(observation)
                return dict(host_released=True, record=dict(state='exited'))

            @staticmethod
            def retired(binding):
                calls.append('retired')
                return dict(host_released=True, record=dict(state='exited'))
        contract = dict(input=dict(context=dict(host_route=dict(runtime_profile=W.C.P.digest(Host.profile), platform='darwin'))),
                        reservation=dict(account='codex-147'), capability=dict(adapter='codex', configuration={}))
        binding = dict(host='mac-147', dispatch_id='d-147', contract_digest='sha256:' + '0' * 64)
        account = dict(id='codex-147', status='active', provider='codex', profiles={'mac-147': str(login / 'profile')})
        delivery = SimpleNamespace(close=lambda: close_profile(login) if login.exists() else None)
        try:
            W.run(Client, Host, 'd-147', str(base / 'run' / 'clone'), str(base / 'run' / 'scratch'), account,
                  collect=lambda started, observation: (None, {}), claim=dict(contract=contract, binding=binding),
                  delivery=delivery)
        except W.OUT.WaitingForRelease as error:
            assert str(error) == 'login_left_behind', str(error)
        else:
            raise AssertionError('the slot was retired with the login still on the Mac')
        assert signed and signed[-1]['login'] == dict(status='left_behind', detached=False), signed
        assert calls == [] and login.exists(), calls
        # A later try (the resumer's) that can remove it retires the slot.
        status[0] = 'closed'
        W.apply_release(Client, Host, binding, dict(host_released=True, record=dict(state='exited')))
        assert calls == ['release_authority', 'retired'] and not login.exists(), calls

    def wrapper_stream(base):
        # The production wrapper, whole, over a real child with two pipes: engine.out and engine.err hold
        # what the engine printed, the one ordered file holds the same bytes by stream, and result.json
        # carries the totals the Mac signs.
        import hashlib
        import os
        import subprocess
        import sys
        from unittest.mock import patch
        loaded = importlib.util.spec_from_file_location('v147_wrapper', modules_tree / 'project_runner_macos_wrapper.py')
        wrapper = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(wrapper)
        frames = wrapper.stream_frames
        executable = str(Path(sys.executable).resolve())
        (base / 'engine.py').write_text(ENGINE)
        (base / 'request.json').write_text(json.dumps(dict(
            engine='codex', login_profile=str(base), argv=[executable, str(base / 'engine.py')],
            binary_digest='sha256:' + hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
            startup_seconds=2, dispatch_id='wrapper-147', clone=str(base), environment=dict(os.environ), sandbox='',
            kill_grace_seconds=1, settle_seconds=1)))
        real_popen = subprocess.Popen

        def launch(argv, **named):
            named.pop('process_group')
            return real_popen(argv[3:], start_new_session=True, **named)  # without the macOS sandbox prefix

        def wait_file(path, seconds):
            path.write_text('{"runtime_seconds": 600}')
            return True
        wrapper.identity = lambda pid: {'pid': pid}
        wrapper.coalition = lambda pid: 1
        wrapper.coalition_members = lambda job: [os.getpid()]
        wrapper.wait_file = wait_file
        with patch.object(wrapper.os, 'getpgrp', return_value=os.getpid()), patch.object(wrapper.subprocess, 'Popen', launch):
            assert wrapper.main(base) == 0
        out, err = (base / 'engine.out').read_bytes(), (base / 'engine.err').read_bytes()
        assert err == b'err 0\nerr 1\nerr 2\n' and out.endswith(b'last out, no newline') and out.count(b'\n') == 3
        result = json.loads((base / 'result.json').read_text())
        assert result['returncode'] == 0 and not frames.problems(result['streams'])
        assert result['streams'] == {
            'stdout': {'lines': 4, 'bytes': len(out), 'sha256': hashlib.sha256(out).hexdigest()},
            'stderr': {'lines': 3, 'bytes': len(err), 'sha256': hashlib.sha256(err).hexdigest()}}, result['streams']
        tally, joined = frames.Tally(), {'stdout': b'', 'stderr': b''}
        for raw in (base / frames.FILE).read_bytes().splitlines():
            name, data = frames.parse(raw)
            tally.feed(name, data)
            joined[name] += data
        assert joined == {'stdout': out, 'stderr': err} and tally.totals() == result['streams']

    for name, test in {'AC3/mac-complete-record': complete_record, 'AC3/mac-altered-chunk-refused': altered_chunk,
                       'AC3/mac-missing-end-frame-refused': missing_end_frame,
                       'AC3/mac-unsigned-streams-refused': unsigned_streams,
                       'AC3/mac-stalled-channel-does-not-hold-the-result': stalled_channel,
                       'AC4/remote-mcp-selection-refused': mcp_refused,
                       'AC4/mac-login-left-behind-holds-release': login_left_behind,
                       'AC4/mac-login-disk-private-and-own': login_disk,
                       'AC3/mac-resumed-run-record-refused': resumed_run, 'AC3/mac-wrapper-ordered-stream': wrapper_stream,
                       'AC4/mac-no-value-in-packet': relay_frames, 'AC4/relay-login-refused-by-name': relay_refusal,
                       'AC4/mac-delivery-checked-and-removed': mac_delivery,
                       'AC4/claude-frame-access-only': claude_frame, 'AC1/claude-frame-refusals': claude_refusals,
                       'AC2/codex-frame-access-only': codex_frame, 'AC4/mac-frame-refusals': mac_side_refusals,
                       'AC1/mac-unexpected-launch': unexpected_launch, 'AC2/mac-paid-api-stop': paid_api_stop,
                       'AC2/mac-codex-root-certificates': codex_roots}.items():
        with tempfile.TemporaryDirectory(prefix='v147-login-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0147 ' + name, True)
            except Exception as error:
                print('  ' + name + ': ' + type(error).__name__ + ': ' + str(error)[:250])
                expect('VELDO-0147 ' + name, False)


_v147_login()
