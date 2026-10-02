"""Every listed tool source is explicit; invalid qualification listings stop before launch."""
def _v127_feature_listing():
    import importlib.util
    import json
    from pathlib import Path
    import tempfile
    import tomllib

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    PRODUCTION = {
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:
            return None, getattr(error, 'code', type(error).__name__)
    off_sources = ['memories', 'recommended_plugins', 'request_permissions_tool',
                   'standalone_web_search', 'enable_mcp_apps', 'guardianv2.thread_context']
    names = ['explicit/' + n for n in off_sources] + ['explicit/mapped-default-off',
             'explicit/unknown-default-off', 'listing/missing', 'listing/empty', 'listing/malformed']
    rows = {name: [] for name in names}
    def check(row, condition, detail=''):
        rows[row].append(bool(condition))
        if not condition:
            print('  VELDO-0127 ' + row + ' detail: ' + detail)
    wire = load('v127_features_wire', TREE / 'proof/VELDO-0127/wire_fixture.py')
    factory = load('v127_features_factory', TREE / 'proof/VELDO-0127/factory.py')
    f = None
    with tempfile.TemporaryDirectory(prefix='v127-listing-') as temp:
        base = Path(temp)
        fault = base / 'fault'
        fault.write_text('')
        fixture = json.loads((TREE / 'proof/VELDO-0127/features-fixture.json').read_text())
        catalog = base / 'catalog-fixture.json'
        catalog.write_bytes((TREE / 'proof/VELDO-0127/catalog-fixture.json').read_bytes())
        listing = base / 'features-fixture.json'
        listing.write_text(json.dumps(fixture))
        defaults = {line.split()[0] for line in fixture['stdout'].splitlines() if line.split()[-1] == 'true'}
        try:
            f = factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))
            L, X, C = f.L, f.X, f.config_api
            serial = [0]
            def launch(grants):
                serial[0] += 1
                d = f.role('codex', 'features-' + str(serial[0]))
                d.update(skills=[], instructions=[], mcp=[])
                d['settings']['model'] = 'gpt-6-astra'
                d['native_tools'] = [{'name': n, 'load': 'always'} for n in grants]
                f.save(d)
                binding = C.bind(f.writer, f.DOMAIN, f.REPOSITORY, {'role': d['role']})
                revision = binding['role_revision']
                capability = L.HANDOFF.materialize(f.writer, f.DOMAIN, f.REPOSITORY, revision,
                                                  {'project': f.src, 'factory': base})
                bound = X.bind({'executable': str(f.vendored), 'qualification': str(f.codex_qualification)})
                receiver = object.__new__(L.Receiver)
                receiver.config = {'runs': str(base / 'runs')}
                receiver.binding = dict(bound, revision=revision, capability=capability,
                                        configured_environment={}, environment={})
                receiver.login = {'engine': X, 'record': f.accounts.get('acct-x1')}
                receiver.host, receiver.token, receiver.metering = f.HOST, None, None
                receiver.credentials = L.DL.resolve(f.writer, f.DOMAIN, binding, keystore=f.keystore)
                events = []
                receiver.emit = events.append
                # Absence of argv in the stop case proves no preflight worker ran.
                args_path = fault.with_suffix('.args.json')
                args_path.write_text('[]')
                _, error = attempt(lambda: receiver._baseline('features-' + str(serial[0]),
                                   [str(f.vendored)] + list(X.FLAGS), dict(f.inherited), False))
                args = json.loads(args_path.read_text())
                config = {}
                def merge(a, b):
                    for key, value in b.items():
                        if isinstance(value, dict):
                            merge(a.setdefault(key, {}), value)
                        else:
                            a[key] = value
                for i, arg in enumerate(args):
                    if arg == '-c':
                        merge(config, tomllib.loads(args[i + 1]))
                tools = next((e['tools'] for e in events if e.get('event') == 'capability_tools'), None)
                return config.get('features', {}), error, tools, args

            def qualify(stdout, missing=False):
                # The external listing is the fixture seam. Every record starts
                # at the production writer; missing deletes just that field.
                listing.write_text(json.dumps(dict(fixture, stdout=stdout)))
                record = X.qualification(str(f.vendored), catalog=True)
                if missing:
                    record.pop('feature_listing')
                f.codex_qualification.write_text(json.dumps(record))

            flags, error, tools, args = launch([])
            for feature in off_sources:
                check('explicit/' + feature, feature not in defaults and error is None
                      and flags.get(feature) is False and set(tools or []) == {'exec', 'wait'} and bool(args),
                      str((error, flags.get(feature), tools)))

            # Each refusal has a valid-listing positive control, including the
            # new explicit default-off value. Baseline refusal logic already
            # exists; the control is the changed behavior in these paired rows.
            valid = error is None and flags.get('standalone_web_search') is False and set(tools or []) == {'exec', 'wait'} and bool(args)
            for kind in ('missing', 'empty', 'malformed'):
                row = 'listing/' + kind
                check(row, valid, 'valid listing explicitly disables standalone_web_search and launches')
                stdout = {'missing': fixture['stdout'], 'empty': '',
                          'malformed': fixture['stdout'] + 'broken_feature stable maybe\n'}[kind]
                qualify(stdout, missing=kind == 'missing')
                _, error, tools, args = launch([])
                check(row, error == 'configuration_stop:codex_feature_listing'
                      and tools is None and not args, str((error, tools, bool(args))))

            # A mapped feature must follow the grant even if its recorded default
            # changes to false. Both granted and ungranted launches reach the wire.
            changed = ''.join(('sleep_tool stable false\n' if line.split()[0] == 'sleep_tool' else line + '\n')
                              for line in fixture['stdout'].splitlines())
            qualify(changed)
            for grants in ([], ['clock']):
                flags, error, tools, args = launch(grants)
                expected = {'exec', 'wait'} | (set(X.NATIVE_TOOL_MAPPING['clock']) if grants else set())
                check('explicit/mapped-default-off', error is None and flags.get('sleep_tool') is bool(grants)
                      and set(tools or []) == expected and bool(args), str((grants, error, flags.get('sleep_tool'), tools)))

            qualify(fixture['stdout'] + 'future_role_tool stable false\n')
            flags, error, tools, args = launch([])
            check('explicit/unknown-default-off', error is None and flags.get('future_role_tool') is False
                  and set(tools or []) == {'exec', 'wait'} and bool(args), str((error, flags.get('future_role_tool'), tools)))
        except Exception as error:
            for row in rows:
                check(row, False, 'raised ' + type(error).__name__ + ': ' + str(error)[:160])
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
    for row, values in rows.items():
        expect('VELDO-0127 ' + row, bool(values) and all(values))

_v127_feature_listing()
