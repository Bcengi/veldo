"""VELDO-0166: the production Metering writer and profile helper, using generated local fixtures."""


def _v166_suite():
    import contextlib
    import io
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import stat
    import subprocess
    import tempfile
    from types import SimpleNamespace

    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'accounts.py': ROOT / ".veldo" / "accounts.py",
    }
    rows = {name: [] for name in ('windows/five-hour', 'windows/qualified-set',
                                  'windows/status-only-named', 'windows/missing-reset-receipts',
                                  'windows/rejection-kept', 'windows/named-fallback',
                                  'windows/named-precedence', 'windows/rejection-reset-filled',
                                  'windows/clear', 'windows/unnamed-rejection',
                                  'windows/clear-active-rejection', 'observability/counts-and-log',
                                  'profiles/existing', 'profiles/created')}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # The spec's 2.1.281 source line, byte for byte, including its whitespace and all fields.
    raw = b'{"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "resetsAt": 1790960400, "rateLimitType": "seven_day", "utilization": 0.7, "isUsingOverage": false, "unifiedWindows": {"five_hour": {"utilization": 0.3, "resetsAt": 1790487000}, "seven_day": {"utilization": 0.7, "resetsAt": 1790960400}}}, "uuid": "531e8e6b-8253-4b0a-92dc-255c5111efee", "session_id": "918dd621-97a8-44cf-ab38-4d3e1b9e588e"}'
    account_logs = io.StringIO()
    with tempfile.TemporaryDirectory(prefix='v166-', dir='/dev/shm') as directory, contextlib.redirect_stderr(account_logs):
        base = Path(directory)
        mods = base / 'modules'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('v166_launch', mods / 'control_launch.py')
        H = load('v166_helper', mods / 'accounts.py')
        S, A, C = L.S, L.ACC, L.ENGINES['claude_code']
        SIG = load('v166_signer', mods / 'control_signer.py')
        key = base / 'journal'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        conn = S.open_store(str(base / 'store.sqlite3'))
        def sign(data):
            return SIG.sign_bytes(key, data, 'veldo-journal')
        try:
            # Real store membership writer and production authority, with a generated journal key.
            for name, kind, roles in [('owner', 'person', ['project_owner']),
                                      ('receiver', 'service', ['reservation_service'])]:
                S.execute(conn, dict(command_id='member/' + name, principal='setup', operation='upsert_entity',
                                     nonce='member/' + name, artifact_digests=[], expected_versions={name: 0},
                                     parameters=dict(entity_id=name, kind='membership', data=dict(
                                         principal_type=kind, roles=roles, revoked_at=None, expires_at=None))),
                          'setup', sign, 1)
            accounts = A.Accounts(S, conn, principal='owner', signer='owner', sign=sign)
            def register(name):
                H.account_add(name, root=str(base / 'registry'))
                fields = H.registration(name, host='host', root=str(base / 'registry'))
                accounts.principal = 'owner'
                accounts.register('register/' + name, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], now=1)
                accounts.principal = 'receiver'
            def observe(name, *lines):
                register(name)
                contract = dict(dispatch_id='dispatch/' + name, unit='unit/' + name,
                                reservation=dict(account=name, project='project'))
                events = []
                receiver = SimpleNamespace(login={'engine': C}, config={'store': str(base / 'store.sqlite3')},
                                           emit=events.append, events=events)
                reservations = L.D.RES.Reservations(S, conn, domain='domain', repository='repo',
                                                   principal='receiver', signer='receiver', sign=sign,
                                                   authorize=L.D.RES.service_authority)
                meter = L.Metering(receiver, contract, reservations, accounts, lambda *args: None)
                meter.started()
                try:
                    # The real receiver path, including chunk buffering, private raw receipts and account writes.
                    for line in lines:
                        meter.feed(line[:37])
                        meter.feed(line[37:] + b'\n')
                    meter.file.flush()
                    path = base / 'receipts' / (hashlib.sha256(meter.invocation.encode()).hexdigest() + '.jsonl')
                    kept = path.read_bytes().splitlines()
                    return accounts.get(name)['windows'], meter, kept
                finally:
                    meter.file.close()
            windows, meter, kept = observe('live', raw)
            five = windows.get('five_hour', {})
            seven = windows.get('seven_day', {})
            check('windows/five-hour', 'both live windows, resets and utilization reach the account',
                  set(windows) == {'five_hour', 'seven_day'} and five.get('utilization') == 0.3
                  and five.get('reset_at') == 1790487000 and seven.get('utilization') == 0.7
                  and seven.get('reset_at') == 1790960400 and not meter.errors)
            check('windows/five-hour', 'each raw receipt retained and attributed to its invocation and account',
                  kept[1:] == [raw, raw] and json.loads(kept[0])['account'] == 'live'
                  and json.loads(kept[0])['dispatch_id'] == 'dispatch/live'
                  and meter.receipts == ['sha256:' + hashlib.sha256(raw).hexdigest()] * 2)

            qualified = json.loads((ROOT / 'engine/runtime/claude-qualification.json').read_text())
            names = qualified['versions']['2.1.281']['rate_limit_windows']
            event = json.loads(raw)
            info = event['rate_limit_info']
            info['unifiedWindows'] = {name: dict(utilization=(i + 1) / 10, resetsAt=1790960400 + i)
                                      for i, name in enumerate(names)}
            info['rateLimitType'] = 'seven_day'
            # As in the live line, the named window's own fields equal its unifiedWindows entry.
            info['utilization'] = info['unifiedWindows']['seven_day']['utilization']
            info['resetsAt'] = info['unifiedWindows']['seven_day']['resetsAt']
            windows, meter, kept = observe('qualified', json.dumps(event).encode())
            check('windows/qualified-set', 'every qualified window recorded once with its own values',
                  set(windows) == set(names) and len(kept) == len(names) + 1 and not meter.errors
                  and all(windows.get(name, {}).get('utilization') == (i + 1) / 10
                          and windows.get(name, {}).get('reset_at') == 1790960400 + i
                          for i, name in enumerate(names)))
            for status in ('rejected', 'allowed_warning', 'allowed'):
                info['status'] = status
                windows, meter, _ = observe('status-' + status, json.dumps(event).encode())
                check('windows/status-only-named', status + ' belongs only to seven_day',
                      set(windows) == set(names) and not meter.errors
                      and windows['seven_day']['status'] == ('rejected' if status == 'rejected' else 'allowed')
                      and all(windows[n]['status'] is None for n in names if n != 'seven_day')
                      and A.blocking({'windows': windows}, 1) == (['seven_day'] if status == 'rejected' else []))

            info['unifiedWindows'] = {'five_hour': {'utilization': 0.3}, 'seven_day_opus': None}
            info.update(status='allowed_warning', resetsAt=1790960400, utilization=0.7)
            line = json.dumps(event).encode()
            windows, meter, kept = observe('missing', line)
            check('windows/missing-reset-receipts', 'missing reset stays absent; unreadable entry skipped; named fallback retained',
                  set(windows) == {'five_hour', 'seven_day'} and windows['five_hour']['reset_at'] is None
                  and windows['seven_day']['reset_at'] == 1790960400 and not meter.errors
                  and all(w['source_dispatch'] == 'dispatch/missing' for w in windows.values())
                  and kept[1:] == [line, line]
                  and meter.receipts == ['sha256:' + hashlib.sha256(line).hexdigest()] * 2)

            # A window reported beside the named one never lifts a rejection still in force (VELDO-0160's
            # blocking), while a rejection whose reset has passed is replaced by the report as it came.
            import time
            for label, reset, kept_status in (('in-force', int(time.time()) + 3600, 'rejected'),
                                              ('passed', int(time.time()) - 3600, None)):
                first = json.loads(raw)
                first['rate_limit_info'].update(status='rejected', rateLimitType='five_hour', resetsAt=reset,
                                                utilization=1.0)
                first['rate_limit_info']['unifiedWindows']['five_hour'] = {'utilization': 1.0, 'resetsAt': reset}
                second = json.loads(raw)
                second['rate_limit_info']['unifiedWindows']['five_hour'] = {'utilization': 0.4, 'resetsAt': reset + 60}
                windows, meter, kept = observe('kept-' + label, json.dumps(first).encode(), json.dumps(second).encode())
                five = windows.get('five_hour', {})
                check('windows/rejection-kept', '%s: five_hour after a seven_day event beside it [%s]' % (label, five),
                      not meter.errors and set(windows) == {'five_hour', 'seven_day'}
                      and five.get('status') == kept_status
                      and five.get('reset_at') == (reset if kept_status else reset + 60)
                      and A.blocking({'windows': windows}, time.time()) == (['five_hour'] if kept_status else [])
                      and windows['seven_day']['status'] == 'allowed' and len(kept) == 5)

            def rate(info):
                return json.dumps(dict(type='rate_limit_event', rate_limit_info=info)).encode()

            reset = int(time.time()) + 3600
            line = rate(dict(status='rejected', rateLimitType='five_hour', unifiedWindows={
                'five_hour': dict(utilization=1.0, resetsAt=reset)}))
            windows, meter, kept = observe('fallback', line)
            five = windows.get('five_hour', {})
            check('windows/named-fallback', 'named map supplies both absent fields and the stream reset',
                  not meter.errors and set(windows) == {'five_hour'} and len(kept) == 2
                  and five.get('status') == 'rejected' and five.get('reset_at') == reset
                  and five.get('utilization') == 1.0
                  and (meter.meter.limit() or {}).get('reset_at') == reset)

            # Older fake engines report zero-valued companions. Explicit fields still win,
            # independently for each field, including an explicit zero.
            for suffix, fields, expected in (
                    ('both', dict(resetsAt=reset, utilization=1.0), (reset, 1.0)),
                    ('reset', dict(resetsAt=reset), (reset, 0.2)),
                    ('util', dict(utilization=0.0), (reset + 60, 0.0))):
                line = rate(dict(status='rejected', rateLimitType='five_hour', **fields, unifiedWindows={
                    'five_hour': dict(utilization=0.2, resetsAt=reset + 60),
                    'seven_day': dict(utilization=0.4, resetsAt=reset + 120)}))
                windows, meter, _ = observe('precedence-' + suffix, line)
                five = windows.get('five_hour', {})
                check('windows/named-precedence', suffix + ': each explicit field wins independently',
                      not meter.errors and set(windows) == {'five_hour', 'seven_day'}
                      and (five.get('reset_at'), five.get('utilization')) == expected
                      and (meter.meter.limit() or {}).get('reset_at') == expected[0])

            for label, reset in (('future', int(time.time()) + 3600), ('past', int(time.time()) - 3600)):
                first = rate(dict(status='rejected', rateLimitType='five_hour'))
                second = rate(dict(status='allowed_warning', rateLimitType='seven_day', unifiedWindows={
                    'five_hour': dict(utilization=0.4, resetsAt=reset),
                    'seven_day': dict(utilization=0.7, resetsAt=int(time.time()) + 7200)}))
                windows, meter, _ = observe('filled-' + label, first, second)
                five = windows.get('five_hour', {})
                check('windows/rejection-reset-filled', label + ': later companion fills an unknown reset',
                      not meter.errors and five.get('reset_at') == reset and five.get('status') == 'rejected'
                      and five.get('source_dispatch') == 'dispatch/filled-' + label
                      and A.blocking({'windows': windows}, time.time()) == (['five_hour'] if label == 'future' else [])
                      and A.blocking({'windows': windows}, reset + 1) == [])

            pool = load('v166_pool', mods / 'control_account_pool.py')
            def pool_state(name, now):
                choice = pool.choose(conn, {}, dict(engine='claude_code', host='host'), now, lambda account: None)
                trace = choice.get('trace', choice)
                return trace.get('passed', {}).get(name), any(
                    candidate['account'] == name for candidate in trace.get('candidates', []))

            now = int(time.time())
            for suffix, reset in (('no-reset', None), ('reset', now + 3600)):
                fields = dict(status='rejected')
                if reset is not None:
                    fields.update(resetsAt=reset, utilization=1.0)
                name = 'unnamed-' + suffix
                line = rate(fields)
                windows, meter, kept = observe(name, line)
                unified = windows.get('unified', {})
                check('windows/unnamed-rejection', suffix + ': the stream limit is stored with its receipt',
                      not meter.errors and set(windows) == {'unified'}
                      and unified.get('status') == 'rejected' and unified.get('reset_at') == reset
                      and unified.get('source_dispatch') == 'dispatch/' + name
                      and meter.meter.limit() == dict(window='unified', reset_at=reset, signal='stream')
                      and kept[1:] == [line]
                      and meter.receipts == ['sha256:' + hashlib.sha256(line).hexdigest()])
                check('windows/unnamed-rejection', suffix + ': the real pool refuses until reset or indefinitely',
                      pool_state(name, now) == ('account_limit:unified', False)
                      and pool_state(name, reset - 1 if reset is not None else now + 10**12)
                          == ('account_limit:unified', False)
                      and (reset is None or pool_state(name, reset) == (None, True)))

            for suffix, reset in (('no-reset', None), ('future-reset', now + 3600)):
                first = rate(dict(status='rejected', rateLimitType='five_hour', resetsAt=reset))
                clear = rate(dict(status='allowed', isUsingOverage=False, unifiedWindows={
                    'five_hour': dict(utilization=0.1, resetsAt=now + 7200),
                    'seven_day': dict(utilization=0.3, resetsAt=now + 14400)}))
                name = 'clear-active-' + suffix
                windows, meter, kept = observe(name, first, clear)
                check('windows/clear-active-rejection', suffix + ': Meter and pool both reopen on a clear event',
                      not meter.errors and set(windows) == {'five_hour', 'seven_day'}
                      and meter.meter.limit() is None and pool_state(name, now) == (None, True)
                      and all(w['status'] is None for w in windows.values())
                      and windows.get('five_hour', {}).get('reset_at') == now + 7200
                      and windows.get('five_hour', {}).get('utilization') == 0.1
                      and kept[1:] == [first, clear, clear])

            passed = int(time.time()) - 60
            first = rate(dict(status='rejected', rateLimitType='five_hour', resetsAt=passed, utilization=1.0))
            clear = rate(dict(status='allowed', isUsingOverage=False, unifiedWindows={
                'five_hour': dict(utilization=0.1, resetsAt=passed + 7200),
                'seven_day': dict(utilization=0.3, resetsAt=passed + 14400)}))
            windows, meter, kept = observe('clear', first, clear)
            check('windows/clear', 'clear updates only reported windows and lifts the stream rejection',
                  not meter.errors and set(windows) == {'five_hour', 'seven_day'}
                  and meter.meter.limit() is None and A.blocking({'windows': windows}, time.time()) == []
                  and all(w['status'] is None for w in windows.values())
                  and windows.get('five_hour', {}).get('utilization') == 0.1
                  and windows.get('seven_day', {}).get('reset_at') == passed + 14400
                  and kept[1:] == [first, clear, clear])

            first = json.loads(raw)
            first['rate_limit_info']['status'] = 'rejected'
            windows, meter, _ = observe('observable', json.dumps(first).encode(), raw)
            expected_counts = {('seven_day', 'rejected'): 1, ('seven_day', 'allowed'): 1, ('five_hour', None): 2}
            check('observability/counts-and-log', 'count each observation by window and reported status',
                  not meter.errors and getattr(meter, 'window_counts', {}) == expected_counts)
            logs = meter.receiver.events
            check('observability/counts-and-log', 'window logs join receipt, values, account and invocation',
                  len(logs) == 4 and all(
                      event.get('event') == 'window_observed' and event.get('account') == 'observable'
                      and event.get('dispatch_id') == 'dispatch/observable'
                      and event.get('invocation') == meter.invocation
                      and event.get('receipt') == meter.receipts[i]
                      and event.get('metrics') == {'window_observations': 1}
                      and event.get('window') == ('seven_day' if i % 2 == 0 else 'five_hour')
                      and event.get('status') == (('rejected' if i == 0 else 'allowed') if i % 2 == 0 else None)
                      and event.get('utilization') == (0.7 if i % 2 == 0 else 0.3)
                      and event.get('reset_at') == (1790960400 if i % 2 == 0 else 1790487000)
                      for i, event in enumerate(logs)))
            before_counts = dict(getattr(H, 'ADDED_COUNTS', {}))
            start_logs = len(account_logs.getvalue())
            private = 'private-' + os.urandom(8).hex()
            for state in ('created', 'existing'):
                profile = base / ('observable-' + state)
                if state == 'existing':
                    profile.mkdir()
                    (profile / 'settings.json').write_text(private)
                H.account_add('observable-' + state, config_dir=str(profile), root=str(base / 'registry'),
                              private_note=private)
            after_counts = getattr(H, 'ADDED_COUNTS', {})
            added = [json.loads(line) for line in account_logs.getvalue()[start_logs:].splitlines()]
            check('observability/counts-and-log', 'account additions count both directory states and log only facts',
                  all(after_counts.get(state, 0) - before_counts.get(state, 0) == 1 for state in ('created', 'existing'))
                  and len(added) == 2 and all(event == dict(event='account_added', account='observable-' + state,
                      directory=str(base / ('observable-' + state)), directory_state=state,
                      metrics={'accounts_added': 1}) for state, event in zip(('created', 'existing'), added)))

            for provider in ('claude_code', 'codex'):
                existing = base / ('existing-' + provider)
                existing.mkdir(mode=0o755)
                existing.chmod(0o755)
                content = existing / 'settings.json'
                content.write_text('{"theme": "dark"}\n')
                before = (stat.S_IMODE(existing.stat().st_mode), content.read_bytes(), content.stat().st_mtime_ns)
                record = H.account_add('existing-' + provider, config_dir=str(existing),
                                       root=str(base / 'registry'), provider=provider)
                after = (stat.S_IMODE(existing.stat().st_mode), content.read_bytes(), content.stat().st_mtime_ns)
                check('profiles/existing', provider + ' existing mode, contents and registration preserved',
                      before == after and record['config_dir'] == str(existing)
                      and H.get(record['name'], root=str(base / 'registry')) == record
                      and record.get('directory_state') == 'existing' and list(existing.iterdir()) == [content])
                created = base / ('created-' + provider)
                old_mask = os.umask(0o022)
                try:
                    record = H.account_add('created-' + provider, config_dir=str(created),
                                           root=str(base / 'registry'), provider=provider)
                finally:
                    os.umask(old_mask)
                check('profiles/created', provider + ' new directory created exactly 0700 and recorded as created',
                      stat.S_IMODE(created.stat().st_mode) == 0o700 and not list(created.iterdir())
                      and record.get('directory_state') == 'created'
                      and H.resolve(record['name'], root=str(base / 'registry')) == str(created))
        finally:
            conn.close()
    for row, checks in rows.items():
        failed = [label for label, ok in checks if not ok]
        expect('VELDO-0166 ' + row + ': ' + '; '.join(failed), bool(checks) and not failed)
        for label in failed:
            print('VELDO-0166 detail: ' + row + ': ' + label)


_v166_suite()
