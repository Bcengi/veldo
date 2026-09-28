"""VELDO-0186: real factory setup, asset census and installed receiver engine bindings.

The only substituted platform seam is host containment qualification. The suite writes a real store,
generated signing keys, enrollment, service files and pins. No service starts and no engine executes.
"""


def _v186_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import stat
    import subprocess
    import tempfile

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_engines.py': ROOT / ".veldo" / "control_factory_setup_engines.py",
    }
    ROWS = ('runtime/assets', 'runtime/missing', 'bind/engines', 'engines/unlisted', 'engines/digest',
            'runtime/setup-missing', 'runtime/modes', 'engines/version', 'metrics/pins', 'metrics/binds')
    rows = {name: [] for name in ROWS}

    def check(row, label, ok):
        rows[row].append((label, bool(ok)))

    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:
            return None, getattr(error, 'code', type(error).__name__)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    base = Path(tempfile.mkdtemp(prefix='v186-', dir='/dev/shm'))
    mods = base / 'src/.veldo'
    shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
    for name, source in PRODUCTION.items():
        if source.is_file():
            shutil.copyfile(source, mods / name)
    fixtures = load('v186_fixtures', TREE / 'proof/VELDO-0186/fixtures.py')
    engines = fixtures.install(ROOT, base, mods)
    fake = engines['fake']
    compare_formats = load('v186_compare', TREE / 'proof/VELDO-0172/compare_formats.py')
    L = load('v186_launch', mods / 'control_launch.py')
    F = load('v186_factory', mods / 'control_factory_setup.py')
    CS = load('v186_service', mods / 'control_service.py')
    git = load('v186_git', mods / 'git_process.py')
    # Host qualification is unrelated to the two criteria. Never contact the user's service manager.
    CS.C.qualify = lambda profile: {'qualified': True, 'refusal': None}
    original_organ = F.organ
    F.organ = lambda name: CS if name == 'control_service' else original_organ(name)
    original_path = os.environ.get('PATH', '')

    class Manager:
        def __init__(self):
            self.calls = []

        def run(self, args):
            self.calls.append(args)
            return 0, '', ''

    manager = Manager()
    owner_key = base / 'owner'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(owner_key)],
                   check=True, capture_output=True, env=F._quiet_env())
    token = base / 'bot-token'
    token.write_text(str(123456) + ':' + ('fixture' * 6))
    token.chmod(0o600)
    serial = [0]

    def fresh():
        serial[0] += 1
        home = base / ('case%d' % serial[0])
        home.mkdir()
        state = home / 'state'
        state.mkdir(mode=0o700)
        workspace = home / 'workspace'
        git.run(['git', 'init', '-q', str(workspace)], check=True, capture_output=True)
        (workspace / 'README').write_text('fixture\n')
        git.run(['git', '-C', str(workspace), 'add', 'README'], check=True, capture_output=True)
        git.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture'],
                identity=('Fixture', 'fixture@example.invalid'), check=True, capture_output=True)
        kwargs = dict(host_trust=str(home / 'trust/host.json'), install_root=str(home / 'install'),
                      unit_dir=str(home / 'units'), profile={}, writable=[], runner=manager)
        args = (str(state), 'owner', str(owner_key), str(workspace), 12345, str(token))
        return home, args, kwargs

    try:
        os.environ['PATH'] = str(engines['path']) + os.pathsep + original_path
        # A future loaded module uses both literal forms already used by production modules.
        with (mods / 'control_engine_claude.py').open('a') as handle:
            handle.write("\n_FUTURE_ASSET = 'runtime/future.json'\n")
        (mods / 'runtime/future.json').write_text('{"future": true}\n')
        with (mods / 'control_engine_claude.py').open('a') as handle:
            handle.write("_NESTED_ASSET = 'runtime/nested/future.json'\n")
        (mods / 'runtime/nested').mkdir()
        (mods / 'runtime/nested/future.json').write_text('{}\n')
        home, args, kwargs = fresh()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = F.main(['setup', '--state-root', args[0], '--owner', args[1], '--owner-key', args[2],
                           '--workspace', args[3], '--chat', str(args[4]), '--token-file', args[5]], **kwargs)
        report = json.loads(output.getvalue())
        check('runtime/assets', 'production setup succeeded', code == 0)
        installed = Path(report.get('home', home / 'absent')) / 'bin'
        config_path = installed.parent / 'config/service.json'
        config = json.loads(config_path.read_text()) if config_path.is_file() else {}
        expected = ['runtime/claude-qualification.json', 'runtime/codex-qualification.json',
                    'runtime/langgraph-records.json', 'runtime/future.json', 'runtime/nested/future.json']
        for name in expected:
            target = installed / name
            check('runtime/assets', name + ' installed with digest', target.is_file()
                  and target.read_bytes() == (mods / name).read_bytes()
                  and config.get('runtime_assets', {}).get(name) == 'sha256:' + hashlib.sha256(target.read_bytes()).hexdigest())
        check('runtime/assets', 'reported assets and count', report.get('runtime_assets') == config.get('runtime_assets')
              and report.get('runtime_assets_installed') == len(expected))
        check('runtime/assets', 'only daemon reload requested', manager.calls == [['daemon-reload']])

        for name in ('runtime', 'runtime/nested'):
            target = installed / name
            check('runtime/modes', name + ' fixed at mode 0500',
                  target.is_dir() and stat.S_IMODE(target.stat().st_mode) == 0o500)

        receiver, error = attempt(lambda: load('v186_installed_receiver', installed / 'control_launch.py'))
        check('bind/engines', 'installed receiver loads', error is None)
        receiver_paths = config.get('receiver', {}).get('configs', {})
        receiver_config = json.loads(Path(next(iter(receiver_paths.values()))).read_text()) if receiver_paths else {}
        state_root = receiver_config.get('state_root')
        check('bind/engines', 'installed receiver names the factory state root', state_root == args[0])
        pinned = Path(args[0]) / 'engines/claude_code' / engines['version']
        check('bind/engines', 'pinned copy exists at mode 0555', pinned.is_file()
              and not pinned.is_symlink() and stat.S_IMODE(pinned.stat().st_mode) == 0o555
              and pinned.read_bytes() == engines['source'].read_bytes())
        recorded_path = Path(args[0]) / 'host/engines.json'
        recorded = json.loads(recorded_path.read_text()) if recorded_path.is_file() else {}
        for engine, adapter in [('claude_code', {'executable': {'version': engines['version']}}),
                                ('codex', {'executable': str(engines['vendor'])})]:
            bound, error = attempt(lambda: receiver.ENGINES[engine].bind(adapter, state_root))
            check('bind/engines', engine + ' binds through installed engine protocol: ' + str(error), error is None)
            summary = {key: bound[key] for key in ('path', 'version', 'sha256')} if bound else None
            check('bind/engines', engine + ' uses the fixed executable', bound is not None
                  and bound['path'] == str(pinned if engine == 'claude_code' else engines['vendor']))
            check('bind/engines', engine + ' recorded binding equals installed binding',
                  summary is not None and recorded.get(engine) == summary == report.get('engines', {}).get(engine))
        check('bind/engines', 'pin count', report.get('pins_made') == 1)
        helper, error = attempt(lambda: F.organ('control_factory_setup_engines'))
        check('metrics/pins', 'production pin counter available', error is None)
        for bindings, wanted in ((recorded, 1), ({'codex': recorded.get('codex', {})}, 0), ({}, 0)):
            count, error = attempt(lambda: helper.count_pins(args[0], bindings))
            check('metrics/pins', 'real pin inventory counts ' + str(wanted), error is None and count == wanted)
        check('metrics/pins', 'setup reports its real pins', report.get('pins_made') == int(pinned.is_file()))

        events = []
        worker, error = attempt(lambda: receiver.Receiver(receiver_config, events.append))
        check('metrics/binds', 'installed receiver constructed', error is None)
        if worker is not None:
            try:
                result, error = attempt(lambda: worker._bind({}, 'no-engine'))
                check('metrics/binds', 'non-engine bind has no refused count',
                      error is None and result is None and not events)
                for engine, source in (('claude_code', pinned), ('codex', engines['vendor'])):
                    if not source.is_file():
                        check('metrics/binds', engine + ' source exists', False)
                        continue
                    original = source.read_bytes()
                    mode = stat.S_IMODE(source.stat().st_mode)
                    source.chmod(0o700)
                    source.write_bytes(original + b'\n# changed after setup\n')
                    source.chmod(mode)
                    worker.login = {'engine': receiver.ENGINES[engine]}
                    adapter = {'executable': {'version': engines['version']} if engine == 'claude_code' else str(source)}
                    result, error = attempt(lambda: worker._bind(adapter, 'changed-engine'))
                    check('metrics/binds', engine + ' refused bind counted once: ' + str((result, error, events[-1:])), error is None
                          and result in ('binding_mismatch:engine_digest', 'stale_subject:engine_digest')
                          and len(events) > 0 and events[-1].get('engine') == engine
                          and events[-1].get('refusal') == result
                          and events[-1].get('metrics', {}).get('binds_refused') == 1)
                    source.chmod(0o700)
                    source.write_bytes(original)
                    source.chmod(mode)
                check('metrics/binds', 'two refused engine binds counted',
                      sum(event.get('metrics', {}).get('binds_refused', 0) for event in events) == 2)
            finally:
                worker.close()


        # Real installer, same enrollment, another service destination. Missing source is refused before writes.
        (mods / 'runtime/future.json').unlink()
        missing_root = home / 'missing-install'
        _result, error = attempt(lambda: CS.install([args[3]], host_trust=kwargs['host_trust'],
            key_directory=str(Path(args[0]) / 'keys'), install_root=str(missing_root),
            unit_dir=str(home / 'missing-units'), profile={}, writable=[], runner=manager))
        check('runtime/missing', 'absent source named without installation: ' + str(error),
              error == 'missing_evidence:runtime_asset:runtime/future.json' and not missing_root.exists())
        _home, neg_args, neg_kwargs = fresh()
        _result, error = attempt(lambda: F.setup(*neg_args, **neg_kwargs))
        check('runtime/setup-missing', 'setup names missing source before any state writes: ' + str(error),
              error == 'missing_evidence:runtime_asset:runtime/future.json'
              and not list(Path(neg_args[0]).iterdir()))
        (mods / 'runtime/future.json').write_text('{"future": true}\n')

        link = engines['path'] / 'claude'
        unversioned = engines['source'].with_name('cli.js')
        unversioned.write_bytes(engines['source'].read_bytes())
        unversioned.chmod(0o755)
        link.unlink()
        link.symlink_to(unversioned)
        _home, neg_args, neg_kwargs = fresh()
        _result, error = attempt(lambda: F.setup(*neg_args, **neg_kwargs))
        check('engines/version', 'non-versioned Claude target names the missing version: ' + str(error),
              error == 'missing_evidence:engine_version:claude_code' and not list(Path(neg_args[0]).iterdir()))
        link.unlink()
        link.symlink_to(engines['source'])

        # Each refusal passes through the factory writer with fresh valid inputs.
        for engine in ('claude_code', 'codex'):
            manifest = json.loads(engines['manifest'].read_text())
            if engine == 'claude_code':
                link = engines['path'] / 'claude'
                unknown = engines['source'].with_name('9.9.9')
                unknown.write_bytes(engines['source'].read_bytes())
                unknown.chmod(0o755)
                link.unlink()
                link.symlink_to(unknown)
            else:
                engines['manifest'].write_text(json.dumps(dict(manifest, version='9.9.9')))
            _home, neg_args, neg_kwargs = fresh()
            _result, error = attempt(lambda: F.setup(*neg_args, **neg_kwargs))
            check('engines/unlisted', engine + ' unknown version refused before writing: ' + str(error),
                  error == 'missing_evidence:engine_baseline:9.9.9' and not list(Path(neg_args[0]).iterdir()))
            if engine == 'claude_code':
                link.unlink()
                link.symlink_to(engines['source'])
            else:
                engines['manifest'].write_text(json.dumps(manifest))
            source = engines['source'] if engine == 'claude_code' else engines['vendor']
            original = source.read_bytes()
            source.write_bytes(original + b'\n# different bytes\n')
            _home, neg_args, neg_kwargs = fresh()
            _result, error = attempt(lambda: F.setup(*neg_args, **neg_kwargs))
            check('engines/digest', engine + ' changed digest refused before writing: ' + str(error),
                  error == 'binding_mismatch:engine_digest' and not list(Path(neg_args[0]).iterdir()))
            source.write_bytes(original)
    except Exception as error:
        # Infrastructure errors cannot masquerade as successful red proof.
        for row in ROWS:
            check(row, 'section raised ' + type(error).__name__ + ': ' + str(error)[:160], False)
    finally:
        os.environ['PATH'] = original_path
        issues, trace = compare_formats.conform_fake(locals(), '0186_setup_assets')
        expect('VELDO-0172 fake/capture:0186_setup_assets', not issues)
        for line in compare_formats.describe('0186_setup_assets', issues, trace):
            print(line)
        for directory, _dirs, _files in os.walk(base):
            os.chmod(directory, 0o700)
        shutil.rmtree(base)
    for row, observations in rows.items():
        for label, ok in observations:
            if not ok:
                print('  VELDO-0186 %s detail: %s' % (row, label))
        expect('VELDO-0186 ' + row, bool(observations) and all(ok for _, ok in observations))


_v186_suite()
