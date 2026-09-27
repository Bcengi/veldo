"""VELDO-0166: the production Metering writer and profile helper, using generated local fixtures."""


def _v166_suite():
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
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'accounts.py': ROOT / ".veldo" / "accounts.py",
    }
    rows = {name: [] for name in ('windows/five-hour', 'windows/qualified-set',
                                  'windows/status-only-named', 'windows/missing-reset-receipts',
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
    with tempfile.TemporaryDirectory(prefix='v166-', dir='/dev/shm') as directory:
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
            def observe(name, line):
                register(name)
                contract = dict(dispatch_id='dispatch/' + name, unit='unit/' + name,
                                reservation=dict(account=name, project='project'))
                receiver = SimpleNamespace(login={'engine': C}, config={'store': str(base / 'store.sqlite3')})
                reservations = L.D.RES.Reservations(S, conn, domain='domain', repository='repo',
                                                   principal='receiver', signer='receiver', sign=sign,
                                                   authorize=L.D.RES.service_authority)
                meter = L.Metering(receiver, contract, reservations, accounts, lambda *args: None)
                meter.started()
                try:
                    # The real receiver path, including chunk buffering, private raw receipts and account writes.
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
            info['status'] = 'allowed_warning'
            line = json.dumps(event).encode()
            windows, meter, kept = observe('missing', line)
            check('windows/missing-reset-receipts', 'missing reset stays absent; unreadable entry skipped; named fallback retained',
                  set(windows) == {'five_hour', 'seven_day'} and windows['five_hour']['reset_at'] is None
                  and windows['seven_day']['reset_at'] == 1790960400 and not meter.errors
                  and all(w['source_dispatch'] == 'dispatch/missing' for w in windows.values())
                  and kept[1:] == [line, line]
                  and meter.receipts == ['sha256:' + hashlib.sha256(line).hexdigest()] * 2)

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
