"""Pinned feature defaults must not broaden an accepted role, even behind login gates."""
def _v127_feature_defaults():
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
    # Independently enumerated from the retained pinned features list. These are
    # the added overrides; the preexisting shell/view/agents/goals controls also
    # participate in every mapped grant's complete configuration comparison.
    added = ['apps', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access',
             'computer_use', 'hooks', 'image_generation', 'in_app_browser',
             'in_app_local_automation', 'mentions_v2', 'plugins', 'remote_plugin',
             'skill_mcp_dependency_install', 'skill_search', 'tool_suggest', 'workspace_dependencies',
             'sleep_tool', 'unified_exec', 'unified_exec_tty']
    mapped = {'shell': ['shell_tool', 'unified_exec', 'unified_exec_tty'],
              'clock': ['sleep_tool'], 'view_image': ['view_image'],
              'multi_agent': ['multi_agent'], 'sub_agents': ['multi_agent']}
    names = ['defaults/' + n for n in added] + ['mapped/' + n for n in mapped] + ['defaults/unknown']
    rows = {name: [] for name in names}
    def check(row, condition, detail=''):
        rows[row].append(bool(condition))
        if not condition:
            print('  VELDO-0127 ' + row + ' detail: ' + detail)
    wire = load('v127_features_wire', TREE / 'proof/VELDO-0127/wire_fixture.py')
    factory = load('v127_features_factory', TREE / 'proof/VELDO-0127/factory.py')
    f = None
    with tempfile.TemporaryDirectory(prefix='v127-features-') as temp:
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

            flags, error, tools, _ = launch([])
            for feature in added:
                check('defaults/' + feature, feature in defaults and error is None
                      and flags.get(feature) is False, str((error, flags.get(feature))))
            for grant, features in mapped.items():
                flags, error, tools, _ = launch([grant])
                enabled = set(features)
                controlled = set(added) | {'shell_tool', 'view_image', 'multi_agent', 'goals'}
                exact = all(flags.get(n) is (n in enabled) for n in controlled)
                delivered = set(X.NATIVE_TOOL_MAPPING[grant]) <= set(tools or [])
                check('mapped/' + grant, error is None and exact and delivered,
                      str((error, exact, delivered)))
            # The real qualification writer reads an installed binary's feature
            # output; only that external output gains the future feature here.
            fixture['stdout'] += 'future_role_tool stable true\n'
            listing.write_text(json.dumps(fixture))
            f.codex_qualification.write_text(json.dumps(X.qualification(str(f.vendored), catalog=True)))
            _, error, tools, args = launch([])
            check('defaults/unknown', error == 'configuration_stop:codex_unknown_default_feature:future_role_tool'
                  and tools is None and not args, str((error, tools, bool(args))))
        except Exception as error:
            for row in rows:
                check(row, False, 'raised ' + type(error).__name__ + ': ' + str(error)[:160])
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
    for row, values in rows.items():
        expect('VELDO-0127 ' + row, bool(values) and all(values))

_v127_feature_defaults()
