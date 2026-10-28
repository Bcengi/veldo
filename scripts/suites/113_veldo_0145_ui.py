"""VELDO-0145: the UI's page and assets served by the API from its own origin, factory data refused before a
passkey session, the UI's route table traced to the API's, and the UI's dependency policy.

Run: python3 scripts/selftest.py --suite 113_veldo_0145_ui

The API is the real control_api.ControlApi on the real control_api.listen (loopback, real HTTP), with an
authority stand-in that records every call it receives: the page rows and the unauthenticated rows must
reach it zero times. The UI directory is a fixture build (index.html, a hashed script, a font, a file
outside it to escape to). The route-trace row reads the UI's own engine/ui/src/api/routes.json; the
dependency row reads engine/ui/package.json, package-lock.json and dependency-policy.json, and judges a
lockfile with a tiered package added, which must be refused. Browser checks of the same criteria live in
engine/ui/e2e (Playwright, a real factory harness); their red and green records are in proof/VELDO-0145.
Mutation workers replace the production copies named in PRODUCTION below, never assertions or fixtures.
Where the UI module is absent (the pre-change tree), the API serves no page, and each row fails by its
own assertions.
"""


def _v145_suite():
    import copy
    import http.client
    import importlib.util
    import json
    import os
    from pathlib import Path
    import tempfile
    import threading

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_ui.py': ROOT / ".veldo" / "control_api_ui.py",
    }
    rows = {}

    def check(row, label, ok):
        rows.setdefault(row, []).append((label, bool(ok)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='v145-') as directory:
        base = Path(directory)
        organs = base / 'installed'
        organs.mkdir()
        for source in sorted((ROOT / '.veldo').glob('control_api*.py')) + [ROOT / '.veldo' / n for n in (
                'secret_scan.py', 'control_workflow.py', 'control_keys.py', 'control_membership.py',
                'authority_contract.py')]:
            if source.is_file():
                (organs / source.name).write_bytes(source.read_bytes())
        for name, source in PRODUCTION.items():
            target = organs / name
            if target.exists():
                target.unlink()
            if Path(source).is_file():
                target.write_bytes(Path(source).read_bytes())
        for needed in ROOT.joinpath('.veldo').glob('*.py'):
            if not (organs / needed.name).exists():
                (organs / needed.name).write_bytes(needed.read_bytes())
        API = load('v145_api', organs / 'control_api.py')
        UI = load('v145_ui', organs / 'control_api_ui.py') if (organs / 'control_api_ui.py').is_file() else None

        class Authority:
            """Records every call; answers as an authority with nothing in it would."""
            calls = []

            def __getattr__(self, name):
                def call(*args, **kwargs):
                    self.calls.append(name)
                    return {'ok': False, 'reason': 'missing_evidence:nothing', 'taxonomy': 'missing_evidence'}
                return call

            def inspect(self, ids):
                self.calls.append('inspect')
                return {'entities': {}}

        authority = Authority()
        ui_dir = base / 'dist'
        (ui_dir / 'assets').mkdir(parents=True)
        (ui_dir / 'index.html').write_text('<!doctype html><title>Veldo</title><script type="module" src="/assets/app-1a2b.js"></script>')
        (ui_dir / 'assets' / 'app-1a2b.js').write_text('console.log(1)')
        (ui_dir / 'assets' / 'face-9f.woff2').write_bytes(b'wOF2fixture')
        (ui_dir / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (ui_dir / 'assets' / 'notes.exe').write_bytes(b'MZ')
        (base / 'secret.txt').write_text('outside the UI')
        os.symlink(base / 'secret.txt', ui_dir / 'assets' / 'escape.js')
        host = 'veldo-ui.example.ts.net'
        config = {'origin': 'https://' + host, 'rp_id': host, 'host': host, 'domain': 'ui145',
                  'ids': {'domain_uuid': 'd', 'repository_uuid': 'r', 'store_uuid': 's'}, 'edge': 'api-edge',
                  'state_dir': str(base / 'state'), 'ui': str(ui_dir)}
        api = API.ControlApi(config, authority, lambda assertion: (None, None))
        # The pre-change API takes no UI directory (it is named in the configuration, which it ignores).
        server = API.listen(api, '127.0.0.1', 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        def get(path, method='GET', headers=None, body=None):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            sent = dict({'Host': host}, **(headers or {}))
            connection.request(method, path, body=body, headers=sent)
            response = connection.getresponse()
            data = response.read()
            out = (response.status, {k.lower(): v for k, v in response.getheaders()}, data)
            connection.close()
            return out

        def refusal(answer):
            try:
                return json.loads(answer[2]).get('refusal')
            except ValueError:
                return None

        # AC1 ui/page-served: the page and its built assets come from the API's own origin under its policy.
        before = len(authority.calls)
        page = get('/runs')
        check('ui/page-served', 'a screen path is the page (index.html, text/html, never cached)',
              page[0] == 200 and page[2].startswith(b'<!doctype html>') and page[1].get('content-type', '').startswith('text/html')
              and page[1].get('cache-control') == 'no-store')
        deep = get('/runs/dispatch/VELDO-1/abc')
        check('ui/page-served', 'a nested screen path is the page too', deep[0] == 200 and deep[2] == page[2])
        script = get('/assets/app-1a2b.js')
        check('ui/page-served', 'a built script is served as JavaScript and cached as immutable',
              script[0] == 200 and script[2] == b'console.log(1)' and script[1].get('content-type', '').startswith('text/javascript')
              and 'immutable' in script[1].get('cache-control', ''))
        font = get('/assets/face-9f.woff2')
        check('ui/page-served', 'a built font is served as font/woff2', font[0] == 200 and font[1].get('content-type') == 'font/woff2')
        icon = get('/favicon.svg')
        check('ui/page-served', 'the icon is served as SVG', icon[0] == 200 and icon[1].get('content-type') == 'image/svg+xml')
        head = get('/runs', method='HEAD')
        check('ui/page-served', 'HEAD answers the page with no body', head[0] == 200 and head[2] == b'')
        everything = [page, deep, script, font, icon, head]
        check('ui/page-served', "every page response carries the API's same-origin policy, HSTS and nosniff",
              all(r[1].get('content-security-policy') == API.CSP and r[1].get('strict-transport-security')
                  and r[1].get('x-content-type-options') == 'nosniff' for r in everything))
        check('ui/page-served', 'the policy allows nothing inline and only this origin',
              "script-src 'self'" in API.CSP and 'unsafe-inline' not in API.CSP and "frame-ancestors 'none'" in API.CSP)
        refused = {
            'another host': (get('/runs', headers={'Host': 'elsewhere.example'}), 'invalid_input:host'),
            'a dot segment': (get('/assets/../../secret.txt'), 'invalid_input:path'),
            'an escaped dot segment': (get('/assets/%2e%2e/%2e%2e/secret.txt'), 'invalid_input:path'),
            'a hidden file': (get('/.env'), 'invalid_input:path'),
            'a missing asset': (get('/assets/none-00.js'), 'missing_evidence:asset'),
            'a type outside the table': (get('/assets/notes.exe'), 'missing_evidence:asset'),
            'a link out of the UI directory': (get('/assets/escape.js'), 'missing_evidence:asset'),
        }
        for label, (answer, expected) in refused.items():
            check('ui/page-served', '%s is refused as %s [observed %s %s]' % (label, expected, answer[0], refusal(answer)),
                  answer[0] in (400, 404) and refusal(answer) == expected and b'outside the UI' not in answer[2]
                  and answer[1].get('content-security-policy') == API.CSP)
        check('ui/page-served', 'no page request reached the authority', len(authority.calls) == before)
        bare = API.ControlApi(dict(config, ui=str(base / 'not-built')), authority, lambda a: (None, None))
        bare_server = API.listen(bare, '127.0.0.1', 0)
        threading.Thread(target=bare_server.serve_forever, daemon=True).start()
        connection = http.client.HTTPConnection('127.0.0.1', bare_server.server_address[1], timeout=10)
        connection.request('GET', '/runs', headers={'Host': host})
        unbuilt = connection.getresponse()
        unbuilt_body = unbuilt.read()
        connection.close()
        check('ui/page-served', 'a host with no built UI names that',
              unbuilt.status == 404 and json.loads(unbuilt_body).get('refusal') == 'missing_evidence:ui_not_built')
        bare_server.shutdown()

        # AC1 ui/unauthenticated-access: every factory data route refuses a request with no passkey session.
        before = len(authority.calls)
        session_routes = [r for r in API.ROUTES if r.session]
        for route in session_routes:
            path = route.path.replace('{domain}', 'ui145')
            if route.method == 'GET':
                query = '&'.join('%s=1' % f for f in route.required)
                answer = get(path + ('?' + query if query else ''))
            else:
                answer = get(path, method='POST', body=json.dumps({f: 1 for f in route.required}),
                             headers={'Origin': 'https://' + host, 'Content-Type': 'application/json',
                                      'Sec-Fetch-Site': 'same-origin'})
            body = {}
            try:
                body = json.loads(answer[2])
            except ValueError:
                pass
            check('ui/unauthenticated-access', '%s %s without a session is 401 unauthenticated and carries no data '
                  '[observed %s %s]' % (route.method, route.name, answer[0], body.get('refusal')),
                  answer[0] == 401 and str(body.get('refusal', '')).startswith('unauthenticated:')
                  and set(body) <= {'refusal', 'error'})
        check('ui/unauthenticated-access', 'every read model and the record routes need a session',
              all(r.session for r in API.ROUTES if r.family in ('reads', 'events', 'decisions', 'messages', 'configuration')))
        check('ui/unauthenticated-access', 'no unauthenticated request reached the authority [%s]' % authority.calls[before:],
              len(authority.calls) == before)
        server.shutdown()

        # AC1 ui/route-trace: every route the UI calls is a published API route, with its exact fields.
        def read_json(path, default):
            try:
                return json.loads(Path(path).read_text())
            except (OSError, ValueError):
                return default

        table = read_json(ROOT / 'engine' / 'ui' / 'src' / 'api' / 'routes.json', {}).get('routes', {})
        check('ui/route-trace', 'the UI publishes its route table', bool(table))
        published = {r.name: r for r in API.ROUTES}
        for name, spec in sorted(table.items()):
            route = published.get(name)
            check('ui/route-trace', '%s is published with the same method, path and fields' % name,
                  route is not None and route.method == spec['method'] and route.path == spec['path']
                  and list(route.required) == spec['required'] and list(route.optional) == spec['optional'])
        check('ui/route-trace', 'the UI calls the routes its screens need',
              {'auth.session', 'auth.challenge', 'auth.sign_in', 'auth.registration_begin', 'auth.registration_credential',
               'auth.registration_possession', 'auth.sign_out', 'reads.decisions', 'reads.workers', 'decisions.answer',
               'runs.record', 'runs.record_stream'} <= set(table))
        check('ui/route-trace', 'the session answer names the domain the UI addresses its routes to',
              "'domain': self.domain" in (organs / 'control_api.py').read_text())

        # AC4 ui/dependency-policy: the lockfile and served packages against the owner's provenance rules.
        ui = ROOT / 'engine' / 'ui'
        lock = read_json(ui / 'package-lock.json', {'packages': {}})
        policy = read_json(ui / 'dependency-policy.json', {'direct': {}})
        package = read_json(ui / 'package.json', {'dependencies': {}})
        judge = getattr(UI, 'dependency_problems', None)
        found = judge(lock, policy, package) if judge else ['no dependency policy check']
        for problem in found[:20]:
            print('  VELDO-0145 ui/dependency-policy problem: %s' % problem)
        check('ui/dependency-policy', 'the accepted lockfile meets the policy', judge is not None and found == [])
        tiered = copy.deepcopy(lock)
        tiered['packages']['node_modules/primevue'] = dict(tiered['packages'].get('node_modules/primevue', {}), version='5.0.4',
                                                           license='SEE LICENSE IN LICENSE.md')
        tiered['packages']['node_modules/@primeui/license-manager'] = {'version': '1.1.0', 'license': 'SEE LICENSE IN LICENSE.md'}
        refused_tiers = judge(tiered, policy, package) if judge else []
        check('ui/dependency-policy', 'a package with free and paid tiers in the lockfile is refused [%s]' % refused_tiers[:3],
              any('primevue@5.0.4: denied' in p for p in refused_tiers)
              and any('@primeui/license-manager' in p and 'denied' in p for p in refused_tiers))
        chinese = copy.deepcopy(lock)
        chinese['packages']['node_modules/element-plus'] = {'version': '2.9.0', 'license': 'MIT'}
        check('ui/dependency-policy', 'a Chinese-origin UI library is refused',
              judge is not None and any('element-plus' in p and 'denied' in p for p in judge(chinese, policy, package)))
        loose = dict(package, dependencies=dict(package.get('dependencies', {}), vue='^' + package.get('dependencies', {}).get('vue', '3')))
        check('ui/dependency-policy', 'a direct dependency without an exact version is refused',
              judge is not None and any('vue' in p and 'exact' in p for p in judge(lock, policy, loose)))
        check('ui/dependency-policy', 'every direct dependency records its license, origin, tier and reason',
              bool(policy.get('direct')) and all(all(e.get(f) for f in ('version', 'license', 'origin', 'tier', 'why'))
                                                 for e in policy['direct'].values()))

    for name in ('ui/page-served', 'ui/unauthenticated-access', 'ui/route-trace', 'ui/dependency-policy'):
        observed = rows.get(name, [])
        ok = bool(observed) and all(o for _, o in observed)
        for label, one in observed:
            if not one:
                print('  VELDO-0145 %s detail: %s' % (name, label))
        expect('VELDO-0145 ' + name, ok)


_v145_suite()
