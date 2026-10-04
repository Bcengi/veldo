"""VELDO-0167: installed records, live subscriber fan-out, additive older-host setup.

Only ROOT and expect are consumed. The 0171 fixture supplies isolated setup, the
installed authority and API processes, generated keys and passkeys, and loopback
transport stand-ins. A plain Python worker is launched by the installed receiver's
spawn and reap interfaces. Dispatches and reservations use their production writers.
"""


def _v167_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import socket
    import subprocess
    import sys
    import threading
    import time
    from urllib.parse import urlencode

    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_records.py': ROOT / ".veldo" / "control_factory_setup_records.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_execution_record.py': ROOT / ".veldo" / "control_execution_record.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    here = Path(globals().get('__suite_file__', ROOT / 'scripts/suites/91_veldo_0167_setup_records.py')).resolve().parents[2]
    review_spec = importlib.util.spec_from_file_location('v167_review', here / 'proof/VELDO-0167/review_rows.py')
    review = importlib.util.module_from_spec(review_spec)
    review_spec.loader.exec_module(review)
    rows = {name: [] for name in ('installed-record', 'late-subscriber', 'older-host') + review.ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def exercise(h):
        base, load = h['base'], h['load']
        setup, clone, fresh = h['setup'], h['clone'], h['fresh_root']
        workspace, root = clone('clone-records'), fresh('state-records')
        trust, install, units = base / 'trust/host.json', base / 'install', base / 'units'
        manager = h['Manager'](units)
        h['managers'].append(manager)
        args = (root, workspace, trust, install, units, manager)
        code, report = setup(*args)
        for row in rows:
            check(row, 'setup succeeds: ' + str(report.get('reason')), code == 0)
        if code:
            return
        home = Path(report['home'])
        config_path = home / 'config/service.json'
        installed = json.loads(config_path.read_text())
        receivers = sorted(installed['receiver']['configs'].values())
        configs = [Path(p) for p in receivers] + [root / 'host/api-service.json', home / 'config/api-service.json']
        records = str(root / 'records')
        check('installed-record', 'one private records directory exists at setup',
              Path(records).is_dir() and Path(records).stat().st_mode & 0o777 == 0o700)
        for path in configs:
            check('installed-record', str(path.name) + ' shares records', json.loads(path.read_text()).get('records') == records)
        for path in receivers:
            held = json.loads(Path(path).read_text())
            check('late-subscriber', 'receiver names service, no subscriber registry or fixed list',
                  held.get('record_hint_service') == installed['socket'] and 'record_hints' not in held
                  and 'api-subscribers' not in Path(path).read_text())

        # A host from before this step: remove only its keys from production-written files.
        # Null and absent keys both occur; unrelated bytes must survive their upgrade.
        original = {}
        for i, path in enumerate(configs):
            value = json.loads(path.read_text())
            for key in ('records', 'record_hint_service'):
                if key in value:
                    if i % 2:
                        value[key] = None
                    else:
                        del value[key]
            path.write_text(json.dumps(value, indent=3, sort_keys=False) + '\n')
            original[path] = path.read_bytes()
        Path(records).rmdir() if Path(records).is_dir() else None
        h['state_of'](installed['store_path'])
        before = h['snapshot'](root, install, units, trust.parent, workspace / '.git/veldo')
        code, rerun = setup(*args)
        check('older-host', 'older host upgrades: ' + str(rerun.get('reason')), code == 0)
        check('older-host', 'creates private records directory',
              Path(records).is_dir() and Path(records).stat().st_mode & 0o777 == 0o700)
        for path in configs:
            now = json.loads(path.read_text())
            own = ['records'] + (['record_hint_service'] if str(path) in receivers else [])
            check('older-host', path.name + ' adds keys', all(now.get(k) == (records if k == 'records' else installed['socket']) for k in own))
            # Remove only the insertions or null replacements and recover every original byte.
            text = path.read_text()
            import re
            old = json.loads(original[path])
            for key in reversed(own):
                if key in old:
                    text = re.sub(r'("' + key + r'"\s*:\s*)"[^"\n]*"', lambda m: m[1] + 'null', text)
                else:
                    text = re.sub(r',\n "' + key + r'": "[^"\n]*"', '', text)
            check('older-host', path.name + ' preserves other bytes', text.encode() == original[path])
        after = h['snapshot'](root, install, units, trust.parent, workspace / '.git/veldo')
        changed, added, removed = h['changes'](before, after)
        check('older-host', 'only record configurations and directory change: ' + str((changed, added, removed)),
              set(changed) <= {str(p) for p in configs} and set(added) <= {records} and not removed)
        again_before = after
        code, again = setup(*args)
        check('older-host', 'second rerun is byte-identical', code == 0 and again.get('outcome') == 'already_set_up'
              and again_before == h['snapshot'](root, install, units, trust.parent, workspace / '.git/veldo'))
        # Refuse changed non-owned values before any file is written.
        for path, key, remove in [(Path(receivers[0]), 'principal', False), (configs[-1], 'origin', False),
                                  (Path(receivers[0]), 'principal', True)]:
            saved = path.read_bytes()
            value = json.loads(saved)
            if remove:
                value.pop(key)
            else:
                value[key] = 'different'
            path.write_text(json.dumps(value, indent=1, sort_keys=True) + '\n')
            before = h['snapshot'](root, install, units, trust.parent)
            code, refused = setup(*args)
            check('older-host', 'names differing ' + path.name, code == 1
                  and refused.get('reason') == 'invalid_input:state_root:differs:' + str(path)
                  and before == h['snapshot'](root, install, units, trust.parent))
            path.write_bytes(saved)

        review.interrupted(h, check, args, configs)

        # Configure a plain fixture adapter through the installed receiver's spawn seam.
        # No vendor engine, login, model, network, or hand-written execution record.
        L = load('v167_installed_launch', home / 'bin/control_launch.py')
        receiver_config = json.loads(Path(receivers[0]).read_text())
        CM = L.D.CM
        CM.attach(L.S)
        receiver = L.Receiver(receiver_config, lambda event: None)
        D, RES = L.D, L.D.RES
        principal = 'record-runner'
        key = base / 'record-runner-key'
        h['keygen'](key, principal)
        command = dict(command_id='enroll-record-runner', operation='enroll_principal', target='authority',
                       parameters=dict(principal=principal, principal_type='service', roles=[],
                                       public_key=h['derived'](key), independence_group=principal, scope=['*']),
                       artifact_digests=[], expected_versions={})
        state = CM.authority_state(L.S, receiver.conn)
        env = dict(report['authority_ids'], schema=h['AC'].ENVELOPE_SCHEMA, command_id=command['command_id'],
                   principal=h['owner'], request_revision=1, nonce='record-runner-enrollment',
                   expires_at=time.time() + 600, membership_version=state['membership_version'],
                   delegation_version=state['delegation_version'], command_digest=h['AC'].canonical_command_digest(command))
        CM.admit(L.S, receiver.conn, env, command,
                      h['sign_with'](h['owner_key'], h['AC'].canonical_envelope_bytes(env)),
                      report['authority_ids'], time.time(),
                      enrollee_signature=h['sign_with'](key, h['AC'].canonical_envelope_bytes(dict(env, principal=principal))),
                      journal_signer=(receiver_config['principal'], receiver.sign))
        h['K'].publish(L.S, receiver.conn, str(root / 'host/allowed_signers'))
        dispatches = D.Dispatches(L.S, receiver.conn, domain=receiver_config['domain'], repository=receiver_config['repository'],
                                  principal=principal, signer=principal, sign=receiver.sign)
        reservations = RES.Reservations(L.S, receiver.conn, domain=receiver_config['domain'],
                                        repository=receiver_config['repository'], principal=principal,
                                        authorize=lambda conn, command: True, signer=principal, sign=receiver.sign)
        dispatch_id, account, unit = 'dispatch/records-fixture', 'fixture-account', 'record-unit'
        project = receiver_config['repository']
        for scope, subject in [('account', account), ('project', project), ('unit', unit)]:
            reservations.configure('config/' + scope, scope, subject,
                                   dict(capacity=2, invocations=10, wall_seconds=1000), now=time.time())
        reservations.reserve_worker('reserve/records', dispatch_id, account, project, unit, now=time.time())
        eid = RES.entity('worker', [receiver_config['domain'], dispatch_id])
        slot = receiver.conn.execute('SELECT version, digest FROM entities WHERE id=?', (eid,)).fetchone()
        contract = dict(schema=D.SCHEMA, dispatch_id=dispatch_id, domain=receiver_config['domain'], repository=project,
                        unit=unit, station='review', attempt=1,
                        source=L.resolve_source(str(workspace), 'HEAD'),
                        input=dict(decision=dict(decision_id='fixture-review', station='review', unit=unit, inputs={'fixture': 1}),
                                   context={}, payload={}, payload_digest=D.digest({})),
                        capability=dict(adapter='fixture', configuration={}, configuration_digest=D.digest({})),
                        reservation=dict(entity=eid, version=slot[0], digest=slot[1], account=account, project=project),
                        claim=None, deadline=time.time() + 45, authority_generation=1)
        dispatches.prepare(contract, now=time.time())
        dispatches.accept(dispatch_id, D.digest(contract), dict(L.process_identity(os.getpid()), principal=principal), now=time.time())
        receiver.contract = contract
        release_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        release_path = str(base / 'release.sock')
        release_socket.bind(release_path)
        release_socket.listen(1)
        release_socket.settimeout(10)
        worker_source = "import sys, socket\nprint('first record line', flush=True)\ns=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\ns.connect(sys.argv[1])\ns.recv(1)\nprint('late record line', flush=True)\nprint('fixture error line', file=sys.stderr, flush=True)\n"
        worker = receiver._spawn(dispatch_id, 'fixture-acceptance', dict(argv=[sys.executable, '-c', worker_source, release_path], identity='reported'))
        review.hints(h, check, home, installed, receiver)
        process = L.process_identity(worker.pid)
        dispatches.run(dispatch_id, D.digest(contract), process, now=time.time())
        # _reap consumes the real stdout and stderr streams and calls Recorder's real writer and hints.
        outcome, errors = [], []
        def reap():
            try:
                outcome.append(receiver._reap(worker, contract, b'', process=process, contract_digest=D.digest(contract)))
            except Exception as exc:
                errors.append(type(exc).__name__ + ':' + str(exc))
        thread = threading.Thread(target=reap)
        thread.start()
        release_peer, _ = release_socket.accept()
        opened = []
        try:
            h['CS'].start(report['unit'], manager)
            h['listening'](manager.pid('veldo-api-' + report['unit'][len('veldo-authority-'):]) or 0)
            browser = h['Browser']('records-owner')
            offered, fingerprint = h['register'](browser, 'records owner')
            if fingerprint:
                h['passkey'](root, '--sign', fingerprint)
            signed, cookie = h['sign_in'](browser)
            check('installed-record', 'owner signs in to installed API: ' + str((offered[0], signed[0], (signed[2] or {}).get('refusal'))), signed[0] == 200 and bool(cookie))
            live = h['call']('GET', '/api/v1/domains/' + receiver_config['domain'] + '/runs/record?'
                             + urlencode(dict(dispatch=dispatch_id, after=0)), cookie=cookie)
            check('installed-record', 'installed route serves while worker is running', live[0] == 200
                  and 'first record line' in json.dumps(live[2]) and worker.poll() is None)
            # Separate processes run the installed API constructor and signed subscription.
            import select
            observed = [[], []]
            for i in range(2):
                api_config = json.loads((home / 'config/api-process.json').read_text())
                api_config['api']['state_dir'] = str(base / ('subscriber%d' % i))
                path = h['private'](base / ('api%d.json' % i), json.dumps(api_config))
                client = subprocess.Popen([sys.executable, str(here / 'proof/VELDO-0167/subscriber.py'),
                                           str(home / 'bin/control_client_api.py'), str(path)],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                opened.append(client)
                ready = select.select([client.stdout], [], [], 5)[0]
                line = json.loads(client.stdout.readline()) if ready else {}
                check('late-subscriber', 'API process subscribed while worker is alive',
                      line.get('ready') is True and worker.poll() is None)
            release_peer.sendall(b'x')
            release_peer.close()
            release_socket.close()
            thread.join(10)
            for i, client in enumerate(opened):
                ready = select.select([client.stdout], [], [], 4)[0]
                raw = client.stdout.readline() if ready else b''
                if raw:
                    observed[i].append(json.loads(raw))
            check('late-subscriber', 'both live APIs receive the next record hint',
                  all(any(hint.get('dispatch_id') == dispatch_id and hint.get('seq', 0) >= 1
                          and hint.get('instance') and hint.get('sequence', 0) >= 1 for hint in seen) for seen in observed))
            check('installed-record', 'receiver reaps fixture run', not thread.is_alive() and not errors and bool(outcome))
            if outcome:
                dispatches.exit(dispatch_id, D.digest(contract), process, outcome[0], now=time.time(), execution_record=receiver.committed)
                receiver._ended()
            got = h['call']('GET', '/api/v1/domains/' + receiver_config['domain'] + '/runs/record?' + urlencode(dict(dispatch=dispatch_id, after=0)), cookie=cookie)
            check('installed-record', 'installed API serves lines: ' + str(got[2]), got[0] == 200
                  and all(line in json.dumps(got[2]) for line in ('first record line', 'late record line', 'fixture error line')))
            observations = [json.loads(line) for line in (home / 'state/observations.jsonl').read_text().splitlines()]
            hints = [o for o in observations if o.get('operation') == 'record_hint']
            check('late-subscriber', 'service records fan-out counts, dispatch and instance, never lines',
                  any(o.get('dispatch_id') == dispatch_id and o.get('sent', 0) >= 3 and o.get('instance') for o in hints)
                  and 'late record line' not in json.dumps(hints))
            # The running service reads configuration at startup. Upgrading its record key
            # names the restart without making an unsolicited lifecycle change.
            api_service_path = home / 'config/api-service.json'
            value = json.loads(api_service_path.read_text())
            value.pop('records', None)
            api_service_path.write_text(json.dumps(value, indent=1, sort_keys=True) + '\n')
            code, running_upgrade = setup(*args)
            check('older-host', 'running configuration upgrade names the restart', code == 0
                  and ('systemctl --user restart ' + report['unit']) in str(running_upgrade.get('next')))
        finally:
            if worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=5)
            thread.join(5)
            for client in opened:
                client.stdin.close()
                try:
                    client.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    client.terminate()
                    client.wait(timeout=5)
            receiver.close()
        manager.stop(report['unit'])
        review.older_engine(h, check)
        review.restart(h, check, here)

    here = Path(globals().get('__suite_file__', ROOT / 'scripts/suites/91_veldo_0167_setup_records.py')).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('v167_fixture', here / 'proof/VELDO-0167/fixture.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    conform_spec = importlib.util.spec_from_file_location('v167_formats', here / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)
    fake_capture = (['fixture teardown did not run'], [])

    def teardown(h):
        nonlocal fake_capture
        # VELDO-0186 constructs these inert installation bytes with fake_formats.embed.
        # They deliberately emit no vendor protocol, so no captured events are credited.
        fake_capture = conform_formats.conform_fake(
            dict(base=h['base'], fake=h['engines186']['fake']), '0167_setup_records')

    try:
        fixture.run(ROOT, PRODUCTION, exercise, teardown)
    except Exception as exc:
        for row in rows:
            check(row, 'ran to its end (raised ' + type(exc).__name__ + ': ' + str(exc)[:350] + ')', False)
    for line in conform_formats.describe('0167_setup_records', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0167_setup_records', not fake_capture[0])
    for row, observations in rows.items():
        for label, passed in observations:
            if not passed:
                print('VELDO-0167 ' + row + ' detail: ' + label)
        expect('VELDO-0167 ' + row, bool(observations) and all(passed for _, passed in observations))


_v167_suite()
