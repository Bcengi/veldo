"""VELDO-0145: the UI's page and assets served by the API from its own origin, factory data refused before a
passkey session, the UI's route table traced to the API's, and the UI's dependency policy.

Run: python3 scripts/selftest.py --suite 113_veldo_0145_ui

The API is the real control_api.ControlApi on the real control_api.listen (loopback, real HTTP), with an
authority stand-in that records every call it receives: the page rows and the unauthenticated rows must
reach it zero times. The UI directory is a fixture build (index.html, a hashed script, a font, a file
outside it to escape to). The route-trace row reads the UI's own engine/ui/src/api/routes.json; the
dependency row reads engine/ui/package.json, package-lock.json and dependency-policy.json, and judges a
lockfile with a tiered package added, which must be refused. The installed row lays a fixture build through
init_scaffold.lay_ui into a scratch factory root and serves it from the API installed there. The out-of-scope row
builds the browser tests' own real factory (engine/ui/e2e/harness.py) from this suite's installed copies and answers
a decision over the API as a member whose scope a steward narrowed. The scaffold row runs init_scaffold.scaffold
over a copy of engine/ (no ui/, then a fixture source, then a fixture build) with and without the UI requested,
and asks git whether the laid UI is ignored. Browser checks of the same criteria live in
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
    import shutil
    import subprocess
    import tempfile
    import threading

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_ui.py': ROOT / ".veldo" / "control_api_ui.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
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

        # AC1 ui/installed: the repository's own install path (init_scaffold) lays the built UI beside the installed
        # API module, and the API installed there serves it with no `ui` in its configuration. A rebuild replaces it
        # whole; an unchanged build is left as it is; no build lays nothing and says so.
        scaffold = load('v145_scaffold', PRODUCTION['init_scaffold.py'])
        lay = getattr(scaffold, 'lay_ui', None)
        templates, root = base / 'templates', base / 'factory-root'
        build = templates / 'ui' / 'dist'
        (build / 'assets').mkdir(parents=True)
        first_index = '<!doctype html><title>Veldo</title><script type="module" src="/assets/app-1.js"></script>'
        (build / 'index.html').write_text(first_index)
        (build / 'assets' / 'app-1.js').write_text('console.log("first build")')
        (root / '.veldo').mkdir(parents=True)
        for module in organs.glob('*.py'):
            (root / '.veldo' / module.name).write_bytes(module.read_bytes())
        laid = lay(templates, root) if lay else {}
        check('ui/installed', 'the built UI is laid at .veldo/ui [%s]' % laid,
              laid.get('laid') is True and (root / '.veldo' / 'ui' / 'index.html').read_text() == first_index)
        installed_api = load('v145_api_installed', root / '.veldo' / 'control_api.py')
        installed_ui = load('v145_ui_installed', root / '.veldo' / 'control_api_ui.py')
        check('ui/installed', 'the installed API module finds the laid UI beside it',
              installed_ui.directory({}) == (root / '.veldo' / 'ui').resolve())
        installed = installed_api.ControlApi(dict(config, ui=None, state_dir=str(base / 'state-installed')), authority,
                                             lambda assertion: (None, None))
        listener = installed_api.listen(installed, '127.0.0.1', 0)
        threading.Thread(target=listener.serve_forever, daemon=True).start()

        def fetch(path):
            conn = http.client.HTTPConnection('127.0.0.1', listener.server_address[1], timeout=10)
            conn.request('GET', path, headers={'Host': host})
            got = conn.getresponse()
            return got.status, got.read().decode('utf-8', 'replace')
        try:
            check('ui/installed', 'the installed API serves the laid page and its assets',
                  fetch('/') == (200, first_index) and fetch('/assets/app-1.js') == (200, 'console.log("first build")'))
            (build / 'assets' / 'app-1.js').unlink()
            second_index = first_index.replace('app-1.js', 'app-2.js')
            (build / 'index.html').write_text(second_index)
            (build / 'assets' / 'app-2.js').write_text('console.log("second build")')
            again = lay(templates, root) if lay else {}
            check('ui/installed', 'a rebuilt UI replaces the laid one whole, leaving no stale file [%s]' % again,
                  again.get('laid') is True and fetch('/') == (200, second_index)
                  and fetch('/assets/app-1.js')[0] == 404 and not (root / '.veldo' / 'ui.replaced').exists())
            check('ui/installed', 'an unchanged build is left as it is',
                  lay is not None and lay(templates, root).get('reason') == 'current')
        finally:
            listener.shutdown()
            listener.server_close()
        bare = lay(base / 'no-templates', base / 'bare-root') if lay else {}
        check('ui/installed', 'with no build nothing is laid, and the report names it [%s]' % bare,
              bare.get('reason') in ('not_built', 'no_source') and not (base / 'bare-root' / '.veldo' / 'ui').exists())

        # AC1 ui/scaffold-opt-in: a plain scaffold never lays the UI, even with a build present, so what it lays does
        # not depend on the checkout's build state; --ui (scaffold(ui=True)) lays it at .veldo/ui, where the API
        # module laid beside it serves it, and the repository ignores it. Without a build the report names the right
        # step: build here when this install has the UI source, or (a composed pack, no ui/) build in a source
        # checkout. The templates are a copy of engine/ without ui/, given a fixture source and build step by step.
        copied = base / 'templates-copy'
        shutil.copytree(ROOT / 'engine', copied, symlinks=True,
                        ignore=lambda d, names: ['ui'] if Path(d) == ROOT / 'engine' else [])

        def scaffold_into(name, **kw):
            try:
                return scaffold.scaffold(base / name, templates=copied, **kw)
            except Exception as exc:  # the pre-change scaffold takes no `ui`
                return {'error': '%s: %s' % (type(exc).__name__, exc)}

        def message(ui):
            say = getattr(scaffold, 'ui_message', None)
            return say(ui) if say else ''

        pack = scaffold_into('pack-plain')
        check('ui/scaffold-opt-in', 'a plain scaffold reports no UI and lays none [%s]' % pack.get('ui', pack.get('error')),
              'error' not in pack and pack.get('ui') is None and not (base / 'pack-plain' / '.veldo' / 'ui').exists())
        pack_ui = scaffold_into('pack-ui', ui=True).get('ui') or {}
        check('ui/scaffold-opt-in', 'a requested UI from a pack (no ui/ source) is not laid and the hint sends the '
              'adopter to a source checkout, not to a path the pack lacks [%s] [%s]' % (pack_ui, message(pack_ui)),
              pack_ui.get('reason') == 'no_source' and 'carries no UI source' in message(pack_ui)
              and 'run npm ci && npm run build in %s' % (copied / 'ui') not in message(pack_ui)
              and not (base / 'pack-ui' / '.veldo' / 'ui').exists())
        (copied / 'ui').mkdir()
        (copied / 'ui' / 'package.json').write_text('{"name": "veldo-factory-ui"}')
        unbuilt = scaffold_into('source-unbuilt', ui=True).get('ui') or {}
        check('ui/scaffold-opt-in', 'a requested UI whose source is here but not built names the build in that source '
              '[%s] [%s]' % (unbuilt, message(unbuilt)),
              unbuilt.get('reason') == 'not_built'
              and 'run npm ci && npm run build in %s' % (copied / 'ui') in message(unbuilt))
        shutil.copytree(build, copied / 'ui' / 'dist')
        built_plain = scaffold_into('built-plain')
        check('ui/scaffold-opt-in', 'with a build present, a plain scaffold still lays no UI [%s]'
              % built_plain.get('ui', built_plain.get('error')),
              'error' not in built_plain and built_plain.get('ui') is None
              and not (base / 'built-plain' / '.veldo' / 'ui').exists())
        built_ui = scaffold_into('built-ui', ui=True).get('ui') or {}
        laid_at = base / 'built-ui' / '.veldo' / 'ui'
        check('ui/scaffold-opt-in', 'a requested UI is laid at .veldo/ui, beside the API module that serves it [%s]' % built_ui,
              built_ui.get('laid') is True and (laid_at / 'index.html').read_bytes() == (build / 'index.html').read_bytes()
              and (base / 'built-ui' / '.veldo' / 'control_api_ui.py').is_file())
        (base / 'built-ui').mkdir(exist_ok=True)  # the pre-change scaffold refuses before it makes the target
        git = dict(cwd=str(base / 'built-ui'), capture_output=True, text=True, timeout=30)
        subprocess.run(['git', 'init', '-q'], **git)
        ignored = subprocess.run(['git', 'check-ignore', '-q', '.veldo/ui/index.html'], **git).returncode == 0
        listed = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], **git).stdout
        check('ui/scaffold-opt-in', 'the repository ignores the laid UI: no file under .veldo/ui is listed as its work',
              ignored and '.veldo/ui/' not in listed and '.veldo/control_api_ui.py' in listed)
        again = scaffold_into('built-ui', ui=True).get('ui') or {}
        check('ui/scaffold-opt-in', 'laying the same build again leaves it as it is [%s]' % again,
              again.get('reason') == 'current' and again.get('files') == built_ui.get('files'))

        # AC3 ui/out-of-scope: an answer from a member whose scope no longer covers the request's project is refused
        # by that name (control_api_authority, answer_decision) and settles nothing. The factory is the browser
        # tests' own (engine/ui/e2e/harness.py): a real signed store, presenter, settlement, API authority, protected
        # signer and ControlApi, built from this suite's installed copies; the member signs in with a passkey over the
        # API. Controls: the same member's answer settles while in scope, and an answer naming a record that is not an
        # assignment (the only kind settlement answers) is refused and settles nothing.
        harness = load('v145_harness', ROOT / 'engine' / 'ui' / 'e2e' / 'harness.py')
        (base / 'factory').mkdir()
        factory = harness.Factory(base / 'factory', ui_dir, organs)
        try:
            answer = '/api/v1/domains/%s/decisions/answer' % harness.DOMAIN
            cookie, token = factory.session('mover')

            def answer_body(alias, choice='accept'):
                receipt = factory.on_thread(factory.presenter.current, factory.requests[alias]) or {}
                return {'request_id': receipt.get('request_id'), 'request_version': receipt.get('request_version'),
                        'presentation_id': receipt.get('presentation_id'), 'presentation_digest': receipt.get('brief_digest'),
                        'presentation_version': receipt.get('presentation_version'), 'choice': choice,
                        'rationale': 'answered in the gate'}

            def scope(projects):
                factory.on_thread(factory.admin, 'steward', 'change_roles',
                                  {'principal': 'mover', 'roles': ['project_owner', 'admission_authority'], 'scope': projects})

            # The member may rule on the admission these requests ask (so an in-scope answer can settle).
            scope(['project-a'])
            factory.on_thread(factory.open_request, 'scope-kept', 'mover')
            factory.on_thread(factory.open_request, 'scope-lost', 'mover')
            kept = factory.call('POST', answer, answer_body('scope-kept'), cookie, token)
            check('ui/out-of-scope', 'in scope, the member\'s answer settles [observed %s %s]' % (kept[0], kept[2]),
                  kept[0] == 200 and kept[2].get('outcome') == 'settled'
                  and len(factory.on_thread(factory.settlements, 'scope-kept')) == 1)
            body = answer_body('scope-lost')
            scope(['project-b'])
            lost = factory.call('POST', answer, body, cookie, token)
            check('ui/out-of-scope', 'after a steward narrows the scope away from the project, the answer is refused '
                  'unauthorized:out_of_scope [observed %s %s]' % (lost[0], lost[2]),
                  lost[0] == 403 and lost[2].get('refusal') == 'unauthorized:out_of_scope')
            check('ui/out-of-scope', 'the refused answer settled nothing',
                  factory.on_thread(factory.settlements, 'scope-lost') == [])
            scope(['project-a'])
            other = factory.on_thread(lambda: factory.conn.execute(
                "SELECT id FROM entities WHERE kind='dispatch' ORDER BY id LIMIT 1").fetchone()[0])
            foreign = factory.call('POST', answer, dict(body, request_id=other), cookie, token)
            check('ui/out-of-scope', 'an answer naming a record that is not an assignment is refused and settles nothing '
                  '[observed %s %s]' % (foreign[0], foreign[2]),
                  foreign[0] >= 400 and foreign[2].get('refusal') and factory.on_thread(factory.settlements, 'scope-lost') == [])
        finally:
            factory.pool.shutdown()

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
        # VELDO-0229: a package that declares no license is refused unless the policy records its license and evidence.
        undeclared = copy.deepcopy(lock)
        undeclared['packages']['node_modules/unlicensed-probe'] = {'version': '1.0.0'}
        bare = judge(undeclared, policy, package) if judge else []
        vouched_policy = copy.deepcopy(policy)
        vouched_policy.setdefault('licenses', {}).setdefault('recorded', {})['unlicensed-probe@1.0.0'] = {
            'license': 'MIT', 'evidence': 'probe'}
        vouched = judge(undeclared, vouched_policy, package) if judge else []
        check('ui/dependency-policy', 'a package that declares no license is refused unless its license is recorded',
              judge is not None and any('unlicensed-probe@1.0.0: license None' in p for p in bare)
              and not any('unlicensed-probe' in p for p in vouched))
        loose = dict(package, dependencies=dict(package.get('dependencies', {}), vue='^' + package.get('dependencies', {}).get('vue', '3')))
        check('ui/dependency-policy', 'a direct dependency without an exact version is refused',
              judge is not None and any('vue' in p and 'exact' in p for p in judge(lock, policy, loose)))
        check('ui/dependency-policy', 'every direct dependency records its license, origin, tier and reason',
              bool(policy.get('direct')) and all(all(e.get(f) for f in ('version', 'license', 'origin', 'tier', 'why'))
                                                 for e in policy['direct'].values()))

    for name in ('ui/page-served', 'ui/unauthenticated-access', 'ui/route-trace', 'ui/dependency-policy', 'ui/installed',
                 'ui/scaffold-opt-in', 'ui/out-of-scope'):
        observed = rows.get(name, [])
        ok = bool(observed) and all(o for _, o in observed)
        for label, one in observed:
            if not one:
                print('  VELDO-0145 %s detail: %s' % (name, label))
        expect('VELDO-0145 ' + name, ok)


_v145_suite()
