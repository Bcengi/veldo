"""VELDO-0234: factory setup can put the API on its own tailnet HTTPS port, so a host whose HTTPS root serves another
app keeps it.

Run: python3 scripts/selftest.py --suite 127_veldo_0234_https_port

Only shared ROOT and expect are consumed. VELDO-0171's installed-host fixture (scripts/suites/85_veldo_0171_setup_api.py,
reused as VELDO-0227 reuses it: its setup preamble and its cleanup, never its behavior rows) lays every host down with
the real setup module through its own command surface, into scratch, with that fixture's user manager stand-in running
the installed authority and API units' ExecStart, its loopback Bot API and its Tailscale stand-in
(scripts/suites/support/v171_tailscale.py), whose captured Serve status is edited here to hold another app's
`/ proxy http://127.0.0.1:8002` on the tailnet name's 443. Passkeys are the fixture's software ES256 authenticators;
their ceremonies go over HTTP to the installed API process's loopback listener with Host <name>:<port> and Origin
https://<name>:<port>, as a browser sends them on a port other than 443. The host laid down before this change is laid
by the whole .veldo of commit 043c2ef6 (the tip this change is built on), taken from the repository's history with
`git archive`. No real key, token, login or Tailscale is touched.
"""


def _v234_suite():
    import ast
    import contextlib
    import hashlib
    import http.client
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import tarfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_api.py': ROOT / ".veldo" / "control_factory_setup_api.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('port/option-values', 'port/serve-own-port', 'port/root-occupied', 'port/own-port-occupied',
            'origin/configurations', 'origin/first-enrollment', 'origin/443-unchanged',
            'rerun/same-port', 'rerun/other-port', 'rerun/pre-change-host')
    OV, SP, RO, OO, OC, FE, UN, RS, RP, PC = ROWS
    rows = {name: [] for name in ROWS}
    # The engine this change is built on: its setup knows only 443.
    BEFORE = '043c2ef6'
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def fixture(exercise):
        """Run VELDO-0171's setup preamble with this suite's production copies, then `exercise`, then its cleanup."""
        source = (ROOT / 'scripts/suites/85_veldo_0171_setup_api.py').read_text()
        prefix = source[:source.index('    try:\n        takes =')]
        function = next(n for n in ast.parse(prefix).body if isinstance(n, ast.FunctionDef))
        assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION' for t in n.targets))
        lines = prefix.splitlines(keepends=True)
        lines[assignment.lineno - 1:assignment.end_lineno] = ['    PRODUCTION = __production__\n']
        cleanup = source[source.index('    finally:\n        close_runtime()'):source.index('    if profiler is not None:')]
        body = '    try:\n        __exercise__(dict(locals(), ROOT=ROOT))\n' + cleanup
        ns = dict(ROOT=ROOT, __production__=PRODUCTION, __exercise__=exercise)
        exec(compile(''.join(lines) + body + '\n_v171_suite()\n', __file__, 'exec'), ns)

    def exercise(h):
        F, CS, base, ts, W = h['F'], h['CS'], h['base'], h['ts'], h['W']
        snapshot, changes, journal = h['snapshot'], h['changes'], h['journal']
        NAME, port = h['NAME'], h['port']
        TARGET = 'http://127.0.0.1:%d' % port
        # The other app on the tailnet name's HTTPS root, as the owner's host holds it.
        NEIGHBOR = {'TCP': {'443': {'HTTPS': True}},
                    'Web': {NAME + ':443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:8002'}}}}}
        HOST, ORIGIN = NAME + ':8443', 'https://%s:8443' % NAME
        READS = [list(r) for r in (['version'], ['status', '--json'], ['serve', 'status', '--json'], ['debug', 'prefs'],
                                   ['serve', '--help'])]

        def status():
            return json.loads(__import__('subprocess').run([ts.path, 'serve', 'status', '--json'], capture_output=True,
                                                           text=True, timeout=30).stdout)

        def steps_of(report):
            return {s.get('step'): s.get('outcome') for s in report.get('steps') or []}

        def host(suffix):
            root, workspace = h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix)
            units = base / ('units-' + suffix)
            manager = h['Manager'](units)
            h['managers'].append(manager)
            args = (root, workspace, base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix), units, manager)
            return dict(root=root, workspace=workspace, args=args, manager=manager)

        def refused_writing_nothing(row, label, args, expected, **argv):
            ts.clear()
            before, served = snapshot(base), status()
            code, shown = h['setup'](*args, **argv)
            changed, added, removed = changes(before, snapshot(base))
            serves = [c for c in ts.invocations() if c not in READS]
            check(row, '%s: refused as %s, writing nothing and no Serve write [%s %s %s %s]'
                  % (label, expected, shown.get('reason'), shown.get('detail'), (changed + added + removed)[:3], serves),
                  code == 1 and shown.get('reason') == expected and not (changed or added or removed)
                  and not serves and status() == served)
            return shown

        # ---- AC1: the option's values, each refused one before anything is written ---------------------------------
        ts.set('ready', neighbors=NEIGHBOR)
        trial = host('values')
        for value in ('444', '80', '0', '8080', '65536', 'https', ''):
            refused_writing_nothing(OV, '--https-port %r' % value, trial['args'], 'invalid_input:https_port',
                                    **{'--https-port': value})
        check(OV, 'the ports the option takes are exactly the HTTPS ports Tailscale Serve offers [%s]'
              % (getattr(h['FA'], 'HTTPS_PORTS', None),), getattr(h['FA'], 'HTTPS_PORTS', None) == (443, 8443, 10000))

        # ---- AC1: the chosen port, held by the other app or by another target, is refused as occupied ----------------
        shown = refused_writing_nothing(RO, 'port 443 named, the root serving the other app', trial['args'],
                                        'invalid_input:tailscale_serve:occupied', **{'--https-port': '443'})
        check(RO, 'the refusal names the port [%s]' % shown.get('detail'), '443' in str(shown.get('detail')))
        shown = refused_writing_nothing(RO, 'no option (443 by default), the root serving the other app', trial['args'],
                                        'invalid_input:tailscale_serve:occupied')
        check(RO, 'the default\'s refusal names port 443 [%s]' % shown.get('detail'), '443' in str(shown.get('detail')))
        elsewhere = {'TCP': dict(NEIGHBOR['TCP'], **{'8443': {'HTTPS': True}}),
                     'Web': dict(NEIGHBOR['Web'], **{HOST: {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:9'}}}})}
        ts.set('ready', neighbors=elsewhere)
        shown = refused_writing_nothing(OO, 'port 8443 already mapped to another target', trial['args'],
                                        'invalid_input:tailscale_serve:occupied', **{'--https-port': '8443'})
        check(OO, 'the refusal names port 8443 [%s]' % shown.get('detail'), '8443' in str(shown.get('detail')))
        funneled = {'TCP': dict(NEIGHBOR['TCP'], **{'8443': {'HTTPS': True}}), 'Web': dict(NEIGHBOR['Web']),
                    'AllowFunnel': {HOST: True}}
        ts.set('ready', neighbors=funneled)
        shown = refused_writing_nothing(OO, 'port 8443 funneled', trial['args'], 'invalid_input:tailscale_serve:occupied',
                                        **{'--https-port': '8443'})
        check(OO, 'the funneled refusal names port 8443 [%s]' % shown.get('detail'), '8443' in str(shown.get('detail')))

        # ---- AC1: port 8443 sets up beside the other app on 443 -----------------------------------------------------
        ts.set('ready', neighbors=NEIGHBOR)
        ts.clear()
        own = host('own')
        code, report = h['setup'](*own['args'], **{'--https-port': '8443'})
        log = ts.invocations()
        if code != 0 or report.get('outcome') != 'set_up':
            for row in ROWS:
                if not rows[row] or row not in (OV, RO, OO):
                    check(row, 'setup on port 8443 beside the other app completed [%s]'
                          % {k: report.get(k) for k in ('outcome', 'reason', 'detail')}, False)
            return
        writes = [c for c in log if c not in READS]
        check(SP, 'the invocation log shows exactly one Serve write, `serve --bg --https=8443 %s` [%s]' % (TARGET, writes),
              writes == [['serve', '--bg', '--https=8443', TARGET]])
        check(SP, 'nothing invoked names 443 [%s]' % [c for c in log if any('443' in a and '8443' not in a for a in c)],
              not any(any('443' in a and '8443' not in a for a in c) for c in log))
        now = status()
        check(SP, 'the Serve status keeps the other app\'s root and adds only 8443 to the API [%s]' % now,
              now == {'TCP': {'443': {'HTTPS': True}, '8443': {'HTTPS': True}},
                      'Web': {NAME + ':443': NEIGHBOR['Web'][NAME + ':443'], HOST: {'Handlers': {'/': {'Proxy': TARGET}}}}})
        api = report.get('api') or {}
        check(SP, 'the report names the port, the origin, the Serve mapping done and the mappings left alone [%s]'
              % {k: api.get(k) for k in ('https_port', 'origin', 'serve')},
              api.get('https_port') == 8443 and api.get('origin') == ORIGIN
              and (api.get('serve') or {}).get('mapping') == 'done'
              and (api.get('serve') or {}).get('left_alone') == [NAME + ':443']
              and steps_of(report).get('tailscale_serve') == 'done')
        check(SP, 'the report carries no key or token', h['token'] not in json.dumps(report)
              and 'PRIVATE KEY' not in json.dumps(report))

        # ---- AC2: every configuration carries https://<name>:8443, the relying party the bare name ------------------
        home = Path(report['home'])
        service_path, copied = own['root'] / 'host' / 'api-service.json', home / 'config' / 'api-service.json'
        service = json.loads(service_path.read_text())
        process = json.loads((home / 'config' / 'api-process.json').read_text())
        check(OC, 'veldo.api_service/v1: origin https://<name>:8443, rp_id <name> [%s %s]'
              % (service.get('origin'), service.get('rp_id')),
              service.get('schema') == 'veldo.api_service/v1' and service.get('origin') == ORIGIN
              and service.get('rp_id') == NAME and copied.read_bytes() == service_path.read_bytes())
        check(OC, 'veldo.api_process/v1: api.origin https://<name>:8443, api.host <name>:8443, api.rp_id <name> [%s]'
              % {k: (process.get('api') or {}).get(k) for k in ('origin', 'host', 'rp_id')},
              (process.get('api') or {}).get('origin') == ORIGIN and (process.get('api') or {}).get('host') == HOST
              and (process.get('api') or {}).get('rp_id') == NAME)
        check(OC, 'the setup report\'s origin and tailnet name [%s %s]' % (api.get('origin'), api.get('tailnet_name')),
              api.get('origin') == ORIGIN and api.get('tailnet_name') == NAME)

        # ---- AC2 (declared falsifier): VELDO-0171 AC3's first enrollment on port 8443 -------------------------------
        responses = []

        def call(method, path, body=None, cookie=None, host_header=HOST, origin=ORIGIN):
            headers = {'Host': host_header}
            if method == 'POST':
                headers.update({'Origin': origin, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json'})
            if cookie:
                headers['Cookie'] = '__Host-veldo-session=' + cookie
            try:
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
                answer = conn.getresponse()
                raw = answer.read()
                got = (answer.status, answer.getheaders(), json.loads(raw) if raw else None)
                conn.close()
            except (OSError, ValueError, http.client.HTTPException) as exc:
                got = (0, [], {'refusal': 'no_answer:%s' % type(exc).__name__})
            responses.append((method, path, got[0], (got[2] or {}).get('refusal') if isinstance(got[2], dict) else None))
            return got

        def register(browser, label):
            begun = call('POST', '/api/v1/auth/registration/begin', {'label': label})
            if begun[0] != 200:
                return begun, None, None
            browser.user_handle = begun[2]['user_handle']
            created = browser.create(begun[2]['challenge'], ORIGIN)
            offered = call('POST', '/api/v1/auth/registration/credential',
                           dict(created, registration_id=begun[2]['registration_id']))
            if offered[0] != 200:
                return offered, None, begun
            proof = browser.get(offered[2]['possession_challenge'], ORIGIN, NAME)
            proved = call('POST', '/api/v1/auth/registration/possession',
                          dict({k: v for k, v in proof.items() if k != 'credential_id'},
                               registration_id=begun[2]['registration_id']))
            return proved, ((proved[2] or {}).get('fingerprint') if proved[0] == 200 else None), begun

        unit = report['unit']
        api_unit = 'veldo-api-' + unit[len('veldo-authority-'):]
        manager = own['manager']
        began = CS.start(unit, manager)
        with contextlib.ExitStack() as stop:
            stop.callback(CS.stop, unit, manager)
            check(FE, 'the API runs with the authority service [%s %s]' % (began.get('ActiveState'), manager.alive(api_unit)),
                  began.get('ActiveState') == 'active' and manager.alive(api_unit))
            bare = call('GET', '/api/v1/auth/session', host_header=NAME)
            check(FE, 'a request naming the bare name as Host is refused: the API requires <name>:8443 [%s %s]'
                  % (bare[0], (bare[2] or {}).get('refusal')), (bare[2] or {}).get('refusal') == 'invalid_input:host')
            phone, tablet = h['Browser']('v234-phone'), h['Browser']('v234-tablet')
            first, phone_print, begun = register(phone, 'phone')
            second, tablet_print, _ = register(tablet, 'tablet')
            check(FE, 'two passkeys register with Host <name>:8443 and Origin https://<name>:8443 [%s %s]'
                  % ((first[2] or {}).get('refusal') or first[0], (second[2] or {}).get('refusal') or second[0]),
                  phone_print is not None and tablet_print is not None)
            check(FE, 'the registration names the bare name as relying party [%s]' % ((begun or [0, 0, {}])[2] or {}).get('rp_id'),
                  ((begun or [0, 0, {}])[2] or {}).get('rp_id') == NAME)
            # The registration's origin check against the origin setup configured, as the API makes it.
            client = phone.create('v234-challenge', ORIGIN)['client_data_json']
            problems = W.registration_problems(client, 'v234-challenge', (process.get('api') or {}).get('origin'),
                                               phone.credential_id, phone.public_key(), -7)
            check(FE, 'a browser\'s clientData origin https://<name>:8443 passes the configured origin check [%s]'
                  % problems, not problems)
            code, listed = h['passkey'](own['root'])
            shown = sorted((p.get('label'), p.get('fingerprint'), p.get('origin')) for p in listed.get('pending') or [])
            check(FE, 'veldo factory passkey lists both, each bound to https://<name>:8443 [%s]' % shown,
                  code == 0 and shown == sorted([('phone', phone_print, ORIGIN), ('tablet', tablet_print, ORIGIN)]))
            code, signed = h['passkey'](own['root'], '--sign', phone_print or W.fingerprint(phone.public_key()))
            check(FE, 'the owner signs the phone\'s by its fingerprint and the service admits it [%s %s]'
                  % (signed.get('outcome'), signed.get('reason')),
                  code == 0 and signed.get('outcome') == 'enrolled'
                  and (signed.get('enrolled') or {}).get('fingerprint') == phone_print)
            pending_dir = own['root'] / 'api' / 'pending'
            bindings = [json.loads(p.read_text()).get('binding') or {} for p in sorted(pending_dir.glob('*.json'))]
            check(FE, 'every binding names rp_id <name> and origin https://<name>:8443 [%s]'
                  % sorted({(b.get('rp_id'), b.get('origin')) for b in bindings}),
                  bindings and all(b.get('rp_id') == NAME and b.get('origin') == ORIGIN for b in bindings))
            issued = call('POST', '/api/v1/auth/challenge', {})
            assertion = phone.get((issued[2] or {}).get('challenge'), ORIGIN, NAME) if issued[0] == 200 else {}
            done = call('POST', '/api/v1/auth/sign-in', assertion) if assertion else (0, [], {})
            cookie = (next((v for k, v in done[1] if k.lower() == 'set-cookie'), '') or '').split(';')[0].partition('=')[2]
            session = call('GET', '/api/v1/auth/session', cookie=cookie) if cookie else (0, [], {})
            check(FE, 'it signs in and the session names the owner [%s %s %s]'
                  % (done[0], (done[2] or {}).get('refusal'), (session[2] or {}).get('principal')),
                  done[0] == 200 and session[0] == 200 and (session[2] or {}).get('principal') == h['owner'])
            auth = __import__('base64').urlsafe_b64decode((assertion.get('authenticator_data') or '') + '==')
            check(FE, 'the challenge names rp id <name> and the authenticator data\'s rp id hash is SHA-256(<name>)',
                  (issued[2] or {}).get('rp_id') == NAME and auth[:32] == hashlib.sha256(NAME.encode()).digest())
            # The credential record the authority committed.
            from_store = h['read_store'](own['root'] / 'authority' / 'control.sqlite3', lambda c: [
                json.loads(r[0]) for r in c.execute("SELECT data FROM entities WHERE id LIKE 'api-credential:%'")])
            check(FE, 'the committed credential record names rp_id <name> and origin https://<name>:8443 [%s]'
                  % [(r.get('rp_id'), r.get('origin')) for r in from_store],
                  len(from_store) == 1 and from_store[0].get('rp_id') == NAME and from_store[0].get('origin') == ORIGIN)

        # ---- AC3: a re-run with the same port changes nothing; another port is refused ------------------------------
        binding = Path(h['CEN'].binding_path(str(own['workspace'])))
        trees = (own['root'], own['args'][3], own['args'][4], own['args'][2].parent, binding)
        store = own['root'] / 'authority' / 'control.sqlite3'
        ts.clear()
        head, before, served = journal(store), snapshot(*trees), status()
        code, again = h['setup'](*own['args'], **{'--https-port': '8443'})
        changed, added, removed = changes(before, snapshot(*trees))
        check(RS, 'a re-run with --https-port 8443 is accepted and reports every step already done [%s %s]'
              % (again.get('outcome'), again.get('reason')),
              code == 0 and again.get('outcome') == 'already_set_up'
              and all(s.get('outcome') in ('already_done', 'deferred') for s in again.get('steps') or []))
        check(RS, 'every file is byte for byte the same [%s]' % (changed + added + removed)[:4],
              not (changed or added or removed))
        check(RS, 'the journal head and the Serve status are unchanged and no Serve write ran [%s]'
              % [c for c in ts.invocations() if c not in READS],
              journal(store) == head and status() == served and all(c in READS for c in ts.invocations()))
        check(RS, 'the re-run reports port 8443 and the mapping already done [%s]' % (again.get('api') or {}).get('serve'),
              (again.get('api') or {}).get('https_port') == 8443
              and ((again.get('api') or {}).get('serve') or {}).get('mapping') == 'already_done')
        held = service_path.read_bytes()
        for other in ('443', '10000'):
            ts.clear()
            head, before, served = journal(store), snapshot(base), status()
            code, shown = h['setup'](*own['args'], **{'--https-port': other})
            changed, added, removed = changes(before, snapshot(base))
            check(RP, 'a re-run with --https-port %s is refused as invalid_input:state_root:holds_https_port, writing '
                  'nothing [%s %s]' % (other, shown.get('reason'), (changed + added + removed)[:3]),
                  code == 1 and shown.get('reason') == 'invalid_input:state_root:holds_https_port'
                  and not (changed or added or removed) and journal(store) == head and status() == served
                  and all(c in READS for c in ts.invocations()))
        check(RP, 'api-service.json is unchanged', service_path.read_bytes() == held)

        # ---- AC2: on 443 every configuration is byte for byte what the setup before this change writes ---------------
        shipped = h['_git_process'].run(['git', '-C', str(ROOT), 'archive', '--format=tar', BEFORE, '.veldo'],
                                        capture_output=True)
        older = base / ('engine-' + BEFORE)
        older.mkdir()
        if shipped.returncode or not shipped.stdout:
            for row in (UN, PC):
                check(row, 'the engine of %s is in history' % BEFORE, False)
            return
        with tarfile.open(fileobj=io.BytesIO(shipped.stdout)) as archive:
            archive.extractall(str(older), filter='data')
        # The fixture's engine records (its generated engines' digests) replace the shipped ones, as in the current tree.
        for name in ('claude-qualification.json', 'codex-qualification.json', 'engines.json'):
            (older / '.veldo' / 'runtime' / name).write_bytes((h['mods'] / 'runtime' / name).read_bytes())
        F0 = load('v234_setup_before', older / '.veldo' / 'control_factory_setup.py')
        ts.set('ready')
        ts.clear()
        root443 = host('root443')
        code, report443 = h['setup'](*root443['args'])
        if code != 0 or report443.get('outcome') != 'set_up':
            check(UN, 'setup on 443 completed [%s]' % {k: report443.get(k) for k in ('outcome', 'reason', 'detail')}, False)
        else:
            home443 = Path(report443['home'])
            laid = json.loads((root443['root'] / 'host' / 'ingress.json').read_text())
            ids = {k: laid['authority_ids'][k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid')}
            plan = {'store': str(root443['root'] / 'authority' / 'control.sqlite3'), 'keys': str(root443['root'] / 'keys'),
                    'workspace': os.path.realpath(str(root443['workspace'])), 'root': str(root443['root']),
                    'host_trust': laid['host_trust']}
            api0 = {'connection_key': str(root443['root'] / 'edge' / 'api-auth'), 'state_dir': str(root443['root'] / 'api')}
            wanted_service = F0.api_service_text(plan, ids, NAME)
            wanted_process = F0.api_process_text(plan, ids, api0, NAME, port)
            check(UN, 'host/api-service.json on 443 is byte for byte what the setup of %s writes (origin https://<name>)'
                  % BEFORE, (root443['root'] / 'host' / 'api-service.json').read_text() == wanted_service
                  and json.loads(wanted_service).get('origin') == 'https://' + NAME)
            check(UN, 'api-process.json on 443 is byte for byte what the setup of %s writes (host <name>)' % BEFORE,
                  (home443 / 'config' / 'api-process.json').read_text() == wanted_process
                  and json.loads(wanted_process)['api']['host'] == NAME)
            writes = [c for c in ts.invocations() if c not in READS]
            check(UN, 'the one Serve write names 443 and the report origin https://<name> [%s %s]'
                  % (writes, (report443.get('api') or {}).get('origin')),
                  writes == [['serve', '--bg', '--https=443', TARGET]]
                  and (report443.get('api') or {}).get('origin') == 'https://' + NAME
                  and (report443.get('api') or {}).get('https_port') == 443)

        # ---- AC3: a host laid down by the commit before this change, re-run without the option --------------------
        ts.set('ready')
        ts.clear()
        prior = host('prior')
        root, workspace, args = prior['root'], prior['workspace'], prior['args']
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = F0.main(['setup', '--state-root', str(root), '--owner', h['owner'], '--owner-key', str(h['owner_key']),
                            '--workspace', str(workspace), '--chat', str(h['chat']), '--token-file', str(h['token_file'])],
                           host_trust=str(args[2]), install_root=str(args[3]), unit_dir=str(args[4]),
                           profile=h['profile'], writable=[], runner=prior['manager'], origin=h['url'],
                           tailscale=[ts.path], api_port=port,
                           **__import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))[
                               'setup_options'](getattr(F0, 'setup', None)))
        try:
            laid_report = json.loads(out.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            laid_report = {'unparsed': out.getvalue()[-300:]}
        if code != 0 or laid_report.get('outcome') != 'set_up':
            check(PC, 'the setup of %s laid a host down [%s]' % (BEFORE, {k: laid_report.get(k)
                                                                         for k in ('outcome', 'reason', 'detail')}), False)
            return
        home0 = Path(laid_report['home'])
        binding0 = Path(h['CEN'].binding_path(str(workspace)))
        bin0 = str(home0 / 'bin')
        service_json = str(home0 / 'config' / 'service.json')
        engine_keys = ('closure', 'runtime_assets', 'template')
        store0 = root / 'authority' / 'control.sqlite3'

        def held_files():
            # The installed engine (bin/) and the service record's engine keys are VELDO-0189's upgrade's to replace
            # whenever the engine changes, and SQLite's own -wal and -shm beside the store change under any reader;
            # the store is compared by its full dump, every other file byte for byte.
            found = {k: v for k, v in snapshot(root, args[3], args[4], args[2].parent, binding0).items()
                     if not k.startswith(bin0 + '/') and k != bin0 and k != service_json
                     and not k.startswith(str(store0) + '-')}
            record = json.loads(Path(service_json).read_text())
            dump = h['read_store'](store0, lambda c: list(c.iterdump()))
            return found, ({k: v for k, v in record.items() if k not in engine_keys}, dump)
        ts.clear()
        (before, record_before), head, served = held_files(), journal(store0), status()
        code, rerun = h['setup'](*args)
        (after, record_after) = held_files()
        changed, added, removed = changes(before, after)
        check(PC, 'the re-run without the option is accepted [%s %s, done: %s]'
              % (rerun.get('outcome'), rerun.get('reason'), [k for k, v in steps_of(rerun).items() if v == 'done']),
              code == 0 and rerun.get('outcome') in ('set_up', 'already_set_up'))
        check(PC, 'it reads the host as port 443: report origin https://<name>, mapping already done [%s]'
              % {k: (rerun.get('api') or {}).get(k) for k in ('https_port', 'origin', 'serve')},
              (rerun.get('api') or {}).get('https_port') == 443 and (rerun.get('api') or {}).get('origin') == 'https://' + NAME
              and ((rerun.get('api') or {}).get('serve') or {}).get('mapping') == 'already_done')
        check(PC, 'every file outside the installed engine is byte for byte the same, the store\'s dump too, and the '
              'service record apart from its engine keys [%s]' % (changed + added + removed)[:4],
              not (changed or added or removed) and record_after == record_before)
        check(PC, 'the journal head and the Serve status are unchanged and no Serve write ran [%s]'
              % [c for c in ts.invocations() if c not in READS],
              journal(store0) == head and status() == served and all(c in READS for c in ts.invocations()))

    try:
        fixture(exercise)
    except Exception as error:  # noqa: BLE001
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0234_DETAILS'):
                print('  VELDO-0234 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0234 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0234 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0234 suite seconds: %.3f' % (time.monotonic() - started))


_v234_suite()
