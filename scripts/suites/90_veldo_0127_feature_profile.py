"""The complete generated feature table is valid TOML and accepted by pinned Codex."""
def _v127_feature_profile():
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
    rows = {'profile/parse-values': [], 'profile/pinned-tools': []}
    def check(row, condition, detail=''):
        rows[row].append(bool(condition))
        if not condition:
            print('  VELDO-0127 ' + row + ' detail: ' + detail)
    # Independent value oracle for the retained listing. Non-tool features keep
    # their existing omission; every other recorded feature is explicitly set.
    non_tools = set('''auth_elicitation code_mode_host collaboration_modes compaction_image_budget
        content_item_kinds enable_request_compression fast_mode guardian_approval in_app_chat
        in_app_dictation in_app_updates item_ids personality plugin_sharing remote_compaction_v2
        resize_all_images shell_snapshot sqlite steer terminal_resize_reflow tool_call_mcp_elicitation
        tool_search_always_defer_mcp_tools tui_app_server unbounded_connection_retries unified_exec_zsh_fork'''.split())
    def expected(listing, grants):
        flags = {line.split()[0]: False for line in listing.splitlines() if line.split()[0] not in non_tools}
        mapped = {'shell_tool': 'shell', 'unified_exec': 'shell', 'unified_exec_tty': 'shell',
                  'sleep_tool': 'clock', 'view_image': 'view_image'}
        for feature, grant in mapped.items():
            if feature in flags:
                flags[feature] = grant in grants
        flags.update(shell_tool='shell' in grants, apply_patch_freeform='apply_patch' in grants,
                     view_image='view_image' in grants, goals=False,
                     multi_agent=bool(set(grants) & {'multi_agent', 'sub_agents'}))
        flags['multi_agent_v2'] = {'enabled': flags['multi_agent']}
        return flags
    wire = load('profile_wire', TREE / 'proof/VELDO-0127/wire_fixture.py')
    fixture = load('profile_fixture', TREE / 'proof/VELDO-0127/profile_fixture.py')
    factory = load('profile_factory', TREE / 'proof/VELDO-0127/factory.py')
    f = None
    with tempfile.TemporaryDirectory(prefix='v127-feature-profile-') as temp:
        base = Path(temp)
        fault = base / 'fault'
        fault.write_text('')
        recorded = json.loads((TREE / 'proof/VELDO-0127/features-fixture.json').read_text())
        catalog = base / 'catalog-fixture.json'
        catalog.write_bytes((TREE / 'proof/VELDO-0127/catalog-fixture.json').read_bytes())
        listing_path = base / 'features-fixture.json'
        listing_path.write_text(json.dumps(recorded))
        try:
            f = factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))
            L, X, C = f.L, f.X, f.config_api
            rich = ['shell', 'clock', 'view_image', 'sub_agents', 'apply_patch']
            cases = [(recorded['stdout'], [], 'gpt-6-astra'),
                     (recorded['stdout'], ['shell'], 'gpt-6-astra'),
                     (recorded['stdout'], rich, 'gpt-6-astra'),
                     (recorded['stdout'], ['shell', 'view_image', 'sub_agents', 'apply_patch'], 'gpt-5.5')]
            for number, (listing, grants, model) in enumerate(cases):
                listing_path.write_text(json.dumps(dict(recorded, stdout=listing)))
                # Records, revisions and generated files all come from real writers.
                f.codex_qualification.write_text(json.dumps(X.qualification(str(f.vendored), catalog=True)))
                bound = X.bind({'executable': str(f.vendored), 'qualification': str(f.codex_qualification)})
                d = f.role('codex', 'profile-' + str(number))
                d.update(skills=[], instructions=[], mcp=[])
                d['settings']['model'] = model
                d['native_tools'] = [{'name': n, 'load': 'always'} for n in grants]
                f.save(d)
                binding = C.bind(f.writer, f.DOMAIN, f.REPOSITORY, {'role': d['role']})
                revision = binding['role_revision']
                capability = L.HANDOFF.materialize(f.writer, f.DOMAIN, f.REPOSITORY, revision,
                                                  {'project': f.src, 'factory': base})
                receiver = object.__new__(L.Receiver)
                receiver.config = {'runs': str(base / 'runs')}
                receiver.binding = dict(bound, revision=revision, capability=capability,
                                        configured_environment={}, environment={})
                receiver.login = {'engine': X, 'record': f.accounts.get('acct-x1')}
                receiver.host, receiver.token, receiver.metering = f.HOST, None, None
                receiver.credentials = L.DL.resolve(f.writer, f.DOMAIN, binding, keystore=f.keystore)
                events = []
                receiver.emit = events.append
                refusal = None
                try:
                    argv, _ = receiver._baseline('profile-' + str(number),
                                                [str(f.vendored)] + list(X.FLAGS), dict(f.inherited), False)
                except L.DL.Undeliverable as problem:
                    refusal = problem.code
                config = Path(receiver.run) / L.RUN_CONFIG
                text = (config / 'config.toml').read_text()
                parsed, error = {}, ''
                try:
                    parsed = tomllib.loads(text)
                except tomllib.TOMLDecodeError as problem:
                    error = str(problem)
                want = expected(listing, grants)
                check('profile/parse-values', not error and parsed.get('features') == want,
                      str((number, error, parsed.get('features'), want)))
                check('profile/pinned-tools', refusal is None, str((number, refusal)))
                if refusal is not None:
                    continue
                overrides = [argv[i + 1] for i, arg in enumerate(argv) if arg == '-c'
                             and argv[i + 1].split('=', 1)[0].startswith('features')]
                check('profile/pinned-tools', len(overrides) == 1 and overrides[0].startswith('features='),
                      str((number, 'feature override count', len(overrides))))
                if len(overrides) == 1:
                    check('profile/pinned-tools', tomllib.loads(overrides[0]).get('features') == want,
                          'CLI feature values differ from the accepted grants')
                for read_profile in (False, True):
                    observation = fixture.capture(wire.BINARY, argv, config, read_profile=read_profile)
                    bodies = observation['requests']
                    difference = L.HANDOFF.codex_tool_difference(bodies[0], receiver.binding['expected']) if bodies else 'no request'
                    check('profile/pinned-tools', observation['exact_profile'] and bool(bodies) and difference is None,
                          str((number, read_profile, difference, observation['stderr'] if not bodies else '')))
        except Exception as error:
            for row in rows:
                check(row, False, 'raised ' + type(error).__name__ + ': ' + str(error)[:200])
        finally:
            if f:
                for connection in f.connections:
                    connection.close()
    for row, values in rows.items():
        expect('VELDO-0127 ' + row, bool(values) and all(values))

_v127_feature_profile()
