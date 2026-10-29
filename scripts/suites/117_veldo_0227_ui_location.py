"""VELDO-0227: factory setup tells the installed API where the factory UI is, so no one edits its configuration.

Run: python3 scripts/selftest.py --suite 117_veldo_0227_ui_location

Only shared ROOT and expect are consumed. VELDO-0171's installed-host fixture (scripts/suites/85_veldo_0171_setup_api.py,
reused here as VELDO-0185 reuses it: its setup preamble and its cleanup, never its behavior rows) lays every host down
with the real setup module through its own command surface, into scratch, with that fixture's user manager stand-in
running the installed authority and API units' ExecStart, its Tailscale stand-in and its loopback Bot API. The factory
UI is a fixture build (an index.html and one asset) laid in the workspace by init_scaffold's own --ui step
(init_scaffold.lay_ui). The host laid down before this change is laid by the whole .veldo of commit 1aee02d4 (the tip
this change is built on), taken from the repository's history with `git archive`. Every page request goes over HTTP to
the installed API process's loopback listener with the tailnet name as Host. No real key, token or credential is read.
"""


def _v227_suite():
    import ast
    import contextlib
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
    ROWS = ('ui/fresh-config', 'ui/served', 'ui/report-absent', 'ui/report-present', 'ui/rerun-unchanged',
            'ui/upgrade-pre-change', 'ui/differs-refused')
    FC, SV, RA, RP, RU, UP, DF = ROWS
    rows = {name: [] for name in ROWS}
    # The engine this change is built on (VELDO-0145's tip): its setup writes no `ui`.
    BEFORE = '1aee02d4'
    INDEX = b'<!doctype html><title>v227 factory</title><script src="/assets/app-v227.js"></script>\n'
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
        F, FA, CS, base, ts = h['F'], h['FA'], h['CS'], h['base'], h['ts']
        scaffold = load('v227_scaffold', h['mods'] / 'init_scaffold.py')
        templates = base / 'ui-templates'
        (templates / 'ui' / 'dist' / 'assets').mkdir(parents=True)
        (templates / 'ui' / 'package.json').write_text('{"name": "v227-ui", "private": true}\n')
        (templates / 'ui' / 'dist' / 'index.html').write_bytes(INDEX)
        (templates / 'ui' / 'dist' / 'assets' / 'app-v227.js').write_text('document.title = "v227";\n')
        NAME = h['NAME']

        def page(path='/'):
            """GET `path` from the installed API's loopback listener with the tailnet name as Host."""
            try:
                conn = http.client.HTTPConnection('127.0.0.1', h['port'], timeout=5)
                conn.request('GET', path, headers={'Host': NAME})
                answer = conn.getresponse()
                got = (answer.status, dict((k.lower(), v) for k, v in answer.getheaders()), answer.read())
                conn.close()
                return got
            except (OSError, http.client.HTTPException) as exc:
                return 0, {}, type(exc).__name__.encode()

        def refusal(got):
            try:
                return json.loads(got[2]).get('refusal')
            except (ValueError, AttributeError):
                return None

        def served(got):
            return (got[0] == 200 and got[2] == INDEX and got[1].get('content-security-policy') == h['API'].CSP
                    and 'text/html' in (got[1].get('content-type') or ''))

        def process_of(home):
            path = Path(home) / 'config' / 'api-process.json'
            return path, (json.loads(path.read_text()) if path.is_file() else {})

        def steps_of(report):
            return {s.get('step'): s.get('outcome') for s in report.get('steps') or []}

        def host(suffix, module=None):
            root, workspace = h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix)
            ts.set('ready')
            units = base / ('units-' + suffix)
            manager = h['Manager'](units)
            h['managers'].append(manager)
            args = (root, workspace, base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix), units, manager)
            if module is None:
                code, report = h['setup'](*args)
            else:
                # An earlier setup module through its own command surface, with the fixture's Tailscale stand-in and
                # port (the fixture's helper gives those to its current module only), never the host's own CLI.
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = module.main(['setup', '--state-root', str(root), '--owner', h['owner'], '--owner-key',
                                        str(h['owner_key']), '--workspace', str(workspace), '--chat', str(h['chat']),
                                        '--token-file', str(h['token_file'])],
                                       host_trust=str(args[2]), install_root=str(args[3]), unit_dir=str(units),
                                       profile=h['profile'], writable=[], runner=manager, origin=h['url'],
                                       tailscale=[ts.path], api_port=h['port'])
                try:
                    report = json.loads(out.getvalue().strip().splitlines()[-1])
                except (ValueError, IndexError):
                    report = {'unparsed': out.getvalue()[-300:]}
            return dict(root=root, workspace=workspace, args=args, manager=manager, code=code, report=report)

        # ---- a fresh host, set up before any UI is laid ---------------------------------------------------------
        fresh = host('fresh')
        report = fresh['report']
        if fresh['code'] != 0 or report.get('outcome') != 'set_up':
            for row in ROWS:
                check(row, 'veldo factory setup laid a fresh host down [%s]'
                      % {k: report.get(k) for k in ('outcome', 'reason', 'detail')}, False)
            return
        workspace, manager = fresh['workspace'], fresh['manager']
        expected = os.path.join(str(workspace), '.veldo', 'ui')
        unit, home = report['unit'], Path(report['home'])
        api_unit = 'veldo-api-' + unit[len('veldo-authority-'):]
        process_path, process = process_of(home)
        absent = ('no UI laid yet: run init_scaffold.py --ui %s from a Veldo source checkout after npm ci && npm run '
                  'build in engine/ui' % workspace)

        # AC1: the API process configuration names <workspace>/.veldo/ui, and it is the API's only source.
        check(FC, 'the API process configuration names the workspace\'s UI directory [%s]' % (process.get('api') or {}).get('ui'),
              (process.get('api') or {}).get('ui') == expected)
        check(FC, 'it names it inside the api object only, and the installed bin/ carries no UI beside the module',
              'ui' not in process and not (home / 'bin' / 'ui').exists())
        check(FC, 'the configuration stays 0600 [%s]' % oct(process_path.stat().st_mode & 0o777),
              process_path.stat().st_mode & 0o777 == 0o600)

        # AC2: the report names the directory and says no UI is laid yet, with the step that lays it.
        shown = (report.get('api') or {}).get('ui') or {}
        check(RA, 'with no UI laid the report names the directory and the step that lays it [%s]' % shown,
              shown == {'directory': expected, 'state': absent})

        # AC1: the owner starts the service; the API answers ui_not_built until the UI is laid, then serves it.
        began = CS.start(unit, manager)
        before = page('/')
        check(SV, 'the API runs with the authority service [%s %s]' % (began.get('ActiveState'), manager.alive(api_unit)),
              began.get('ActiveState') == 'active' and manager.alive(api_unit))
        check(SV, 'before the UI is laid GET / answers missing_evidence:ui_not_built [%s %s]' % (before[0], refusal(before)),
              before[0] == 404 and refusal(before) == 'missing_evidence:ui_not_built')
        laid = scaffold.lay_ui(templates, workspace)
        check(SV, 'init_scaffold --ui lays the build at the workspace\'s .veldo/ui [%s]' % scaffold.ui_message(laid),
              laid.get('laid') is True and laid.get('path') == expected)
        after = page('/')
        check(SV, 'GET / on the installed API now answers the laid index.html under the API\'s content security policy, '
              'with no edit of its configuration [%s %s %s]' % (after[0], refusal(after), after[1].get('content-security-policy')),
              served(after))
        asset = page('/assets/app-v227.js')
        check(SV, 'the laid asset is served from the same directory [%s]' % asset[0],
              asset[0] == 200 and asset[2] == (templates / 'ui' / 'dist' / 'assets' / 'app-v227.js').read_bytes())

        # AC1 and AC2: a second run changes nothing in the configuration and says the built UI is present.
        held = process_path.read_bytes()
        code, again = h['setup'](*fresh['args'])
        check(RU, 'a second run is accepted and leaves the API configuration byte for byte [%s %s]'
              % (again.get('outcome'), steps_of(again).get('api_process_configuration')),
              code == 0 and process_path.read_bytes() == held
              and steps_of(again).get('api_process_configuration') == 'already_done')
        shown = (again.get('api') or {}).get('ui') or {}
        check(RP, 'with the UI laid the report names the directory and says the built UI is present [%s]' % shown,
              shown == {'directory': expected, 'state': 'built UI present'})
        check(RU, 'the API still serves the laid UI after the second run', served(page('/')))
        CS.stop(unit, manager)

        # AC1: a configuration that differs in more than the missing `ui` is refused by name, as before this change.
        original = process_path.read_bytes()
        planted = json.loads(original)
        planted['api'].pop('ui')
        planted['listen']['host'] = '127.0.0.2'
        for label, data in (('lacks ui and listens elsewhere', planted),
                            ('names another UI directory', dict(json.loads(original), api=dict(
                                json.loads(original)['api'], ui=str(base / 'elsewhere'))))):
            process_path.write_text(FA.text(data))
            os.chmod(str(process_path), 0o600)
            written = process_path.read_bytes()
            code, refused = h['setup'](*fresh['args'])
            check(DF, '%s: refused as invalid_input:state_root:differs:<its path>, left as it is [%s]'
                  % (label, refused.get('reason')),
                  code == 1 and refused.get('reason') == 'invalid_input:state_root:differs:' + str(process_path)
                  and process_path.read_bytes() == written)
        process_path.write_bytes(original)
        os.chmod(str(process_path), 0o600)

        # ---- a host laid down by the setup before this change -----------------------------------------------------
        shipped = h['_git_process'].run(['git', '-C', str(ROOT), 'archive', '--format=tar', BEFORE, '.veldo'],
                                        capture_output=True)
        older = base / ('engine-' + BEFORE)
        older.mkdir()
        if shipped.returncode or not shipped.stdout:
            check(UP, 'the engine of %s is in history' % BEFORE, False)
            return
        with tarfile.open(fileobj=io.BytesIO(shipped.stdout)) as archive:
            archive.extractall(str(older), filter='data')
        # The fixture's engine records (its generated engines' digests) replace the shipped ones, as in the current tree.
        for name in ('claude-qualification.json', 'codex-qualification.json'):
            (older / '.veldo' / 'runtime' / name).write_bytes((h['mods'] / 'runtime' / name).read_bytes())
        F0 = load('v227_setup_before', older / '.veldo' / 'control_factory_setup.py')
        prior = host('prior', module=F0)
        if prior['code'] != 0 or prior['report'].get('outcome') != 'set_up':
            check(UP, 'the setup of %s laid a host down [%s]' % (BEFORE, {k: prior['report'].get(k)
                                                                         for k in ('outcome', 'reason', 'detail')}), False)
            return
        unit_b, home_b, manager_b = prior['report']['unit'], Path(prior['report']['home']), prior['manager']
        api_unit_b = 'veldo-api-' + unit_b[len('veldo-authority-'):]
        path_b, old = process_of(home_b)
        expected_b = os.path.join(str(prior['workspace']), '.veldo', 'ui')
        check(UP, 'the pre-change setup wrote an API configuration without `ui` [%s]' % sorted(old.get('api') or {}),
              isinstance(old.get('api'), dict) and 'ui' not in old['api'])
        CS.start(unit_b, manager_b)
        scaffold.lay_ui(templates, prior['workspace'])
        stale = page('/')
        check(UP, 'that host\'s API cannot find the laid UI [%s %s]' % (stale[0], refusal(stale)),
              refusal(stale) == 'missing_evidence:ui_not_built')
        code, upgraded = h['setup'](*prior['args'])
        path_b, new = process_of(home_b)
        check(UP, 'the run over it is accepted and reports the configuration step done [%s %s %s]'
              % (upgraded.get('outcome'), upgraded.get('reason'), steps_of(upgraded).get('api_process_configuration')),
              code == 0 and steps_of(upgraded).get('api_process_configuration') == 'done')
        check(UP, 'the configuration is upgraded in place with only api.ui added [%s]' % (new.get('api') or {}).get('ui'),
              (new.get('api') or {}).get('ui') == expected_b
              and dict(new, api={k: v for k, v in new['api'].items() if k != 'ui'}) == old
              and path_b.stat().st_mode & 0o777 == 0o600)
        check(UP, 'the running API is restarted onto it and serves the laid UI [%s %s]'
              % (manager_b.alive(api_unit_b), page('/')[0]), manager_b.alive(api_unit_b) and served(page('/')))
        held = path_b.read_bytes()
        code, third = h['setup'](*prior['args'])
        check(UP, 'a further run changes nothing [%s %s]' % (third.get('outcome'), steps_of(third).get('api_process_configuration')),
              code == 0 and path_b.read_bytes() == held and steps_of(third).get('api_process_configuration') == 'already_done')
        CS.stop(unit_b, manager_b)

    try:
        fixture(exercise)
    except Exception as error:  # noqa: BLE001
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:250]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0227_DETAILS'):
                print('  VELDO-0227 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0227 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0227 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0227 suite seconds: %.3f' % (time.monotonic() - started))


_v227_suite()
