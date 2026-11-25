"""Account-pool installer assets, independently of the real dispatch scenarios."""

def _v160_assets():
    import contextlib
    import importlib.util
    from pathlib import Path
    import shutil
    import tempfile

    PRODUCTION = {
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
        'control_account_limit.py': ROOT / ".veldo" / "control_account_limit.py",
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'control_reservation_runtime.py': ROOT / ".veldo" / "control_reservation_runtime.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    rows = {'install/assets': []}
    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    @contextlib.contextmanager
    def region(*names):
        try:
            yield
        except Exception as exc:  # noqa: BLE001 - a raise reds its rows, never skips them
            for row in names:
                check(row, 'the row ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)

    def load(name, path):
        if not Path(path).is_file():
            return None
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='v160-assets-', dir=fast_temp()) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        # Installation: both new modules laid down by the scaffold, the engine copies identical.
        with region('install/assets'):
            scaffold = load('v160_scaffold', mods / 'init_scaffold.py')
            rels = ('.veldo/control_account_pool.py', '.veldo/control_account_limit.py')
            touched = rels + tuple('.veldo/' + m for m in PRODUCTION)
            check('install/assets', 'the scaffold lays down the account pool and the decision [%s]'
                  % [r for r in rels if r not in scaffold._FILES], all(r in scaffold._FILES for r in rels)
                  and not any(r in scaffold.REQUIRED_SUBSTRATE for r in rels))
            check('install/assets', 'every engine copy of a module this work touches is identical [%s]'
                  % [r for r in touched if not ((ROOT / 'engine' / r).is_file() and (ROOT / r).is_file()
                                               and (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes())],
                  all((ROOT / 'engine' / r).is_file() and (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes()
                      for r in touched))

    for name, observed in rows.items():
        for label, ok in observed:
            if not ok:
                print('  VELDO-0160 %s detail: %s' % (name, label))
        expect('VELDO-0160 ' + name, bool(observed) and all(ok for _, ok in observed))

_v160_assets()
