"""VELDO-0275 AC1: runs use only the approved engine version, pinned by digest.

Run: python3 scripts/selftest.py --suite 130_veldo_0275_approved_engine

Only shared ROOT and expect are consumed. One temporary tree holds an installed .veldo copy with this change's
production modules (PRODUCTION) laid over it, so a registered mutation of any of them reaches every row. Its
runtime holds the engines record and the two qualification records, each naming a small fake approved binary
(the shipped records' entries re-keyed to the fake version and digest); beside each approved binary a newer
version is installed, and the `claude` and `codex` on PATH run the newer one. Nothing is executed: setup's
check reads bytes, the pin copies them, and the binding hashes them.

Rows:
- approved/stays-on-approved: with a newer version installed and on PATH, setup's check resolves the approved
  Claude Code version and the approved Codex binary (the installer's kept copy the engines record names), the
  pinned approved version binds, and a launch naming the newer version, or the newer Codex binary, is refused
  engine_not_approved.
- approved/changed-bytes: the approved Claude Code pinned copy and the approved Codex binary, their bytes
  changed after approval: each binding is refused engine_not_approved, and so is setup's check.
"""


def _v275_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_factory_setup_engines.py': ROOT / ".veldo" / "control_factory_setup_engines.py",
    }
    ROWS = ('approved/stays-on-approved', 'approved/changed-bytes')
    STAYS, CHANGED = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    APPROVED, NEWER = '1.0.0', '1.0.1'
    VENDOR = 'vendor/x86_64-unknown-linux-musl/bin/codex'

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(path):
        return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:  # noqa: BLE001
            return None, getattr(error, 'code', type(error).__name__ + ': ' + str(error)[:200])

    class Refused(Exception):
        def __init__(self, code, detail=''):
            self.code = code
            super().__init__(code)

    def binary(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\n# fake engine %s, never executed by this suite\nexit 97\n' % text)
        path.chmod(0o755)
        return path

    def codex_package(root, version, text):
        root.mkdir(parents=True, exist_ok=True)
        (root / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': version + '-linux-x64'}))
        vendor = binary(root / VENDOR, text)
        binary(root / 'bin' / 'codex.js', 'codex shim ' + version)
        return vendor

    def exercise(base):
        mods = base / 'src' / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        # The installer's versioned copies: the approved one and a newer one beside it.
        versions = base / 'home' / '.local/share/claude/versions'
        approved_claude = binary(versions / APPROVED, 'claude approved')
        newer_claude = binary(versions / NEWER, 'claude newer')
        kept = base / 'home' / '.local/share/codex-versions' / APPROVED / 'node_modules/@openai/codex-linux-x64'
        approved_codex = codex_package(kept, APPROVED, 'codex approved')
        on_path = base / 'npm' / 'lib/node_modules/@openai/codex'
        newer_codex = codex_package(on_path, NEWER, 'codex newer')
        bindir = base / 'bin'
        bindir.mkdir()
        (bindir / 'claude').symlink_to(newer_claude)
        (bindir / 'codex').symlink_to(on_path / 'bin' / 'codex.js')
        # The approval: the engines record and the qualification records, as qualify.py writes them together.
        runtime = mods / 'runtime'
        shipped = json.loads((ROOT / '.veldo/runtime/claude-qualification.json').read_text())
        entry = dict(next(iter(shipped['versions'].values())), sha256=sha(approved_claude),
                     source=str(approved_claude), pinned='<state root>/engines/claude_code/' + APPROVED)
        (runtime / 'claude-qualification.json').write_text(json.dumps(dict(shipped, versions={APPROVED: entry})))
        codex_record = json.loads((ROOT / '.veldo/runtime/codex-qualification.json').read_text())
        codex_record.update(version=APPROVED, package_version=APPROVED + '-linux-x64', executable=VENDOR,
                            sha256=sha(approved_codex))
        (runtime / 'codex-qualification.json').write_text(json.dumps(codex_record))
        engines = json.loads((runtime / 'engines.json').read_text())
        engines['claude_code'].update(version=APPROVED, binary=str(approved_claude), sha256=sha(approved_claude))
        engines['codex'].update(version=APPROVED, package_version=APPROVED + '-linux-x64', binary=str(approved_codex),
                                sha256=sha(approved_codex))
        (runtime / 'engines.json').write_text(json.dumps(engines, indent=1, sort_keys=True) + '\n')

        C = load('v275_claude', mods / 'control_engine_claude.py')
        X = load('v275_codex', mods / 'control_engine_codex.py')
        S = load('v275_setup_engines', mods / 'control_factory_setup_engines.py')
        state = base / 'state'
        state.mkdir(mode=0o700)

        original = os.environ.get('PATH', '')
        os.environ['PATH'] = str(bindir) + os.pathsep + original
        try:
            # approved/stays-on-approved: setup resolves the approved binaries, whatever PATH runs.
            plan, error = attempt(lambda: S.check(Refused))
            check(STAYS, 'setup resolves the approved Claude Code version, not the newer one on PATH [%s, %s]'
                  % (error, (plan or {}).get('claude_code')),
                  error is None and plan['claude_code'] == {'version': APPROVED, 'versions': str(versions)})
            check(STAYS, 'setup resolves the approved Codex binary, not the newer one on PATH [%s, %s]'
                  % (error, (plan or {}).get('codex')),
                  error is None and plan['codex'] == {'executable': str(approved_codex), 'sha256': sha(approved_codex)})
            bound, error = attempt(lambda: S.install(str(state), str(mods), plan, Refused))
            check(STAYS, 'setup pins and binds the approved versions [%s, %s]' % (error, bound),
                  error is None and bound['claude_code']['version'] == APPROVED
                  and bound['claude_code']['sha256'] == sha(approved_claude)
                  and bound['codex'] == {'version': APPROVED, 'path': str(approved_codex), 'sha256': sha(approved_codex)})
            launched, error = attempt(lambda: C.bind({'executable': {'version': APPROVED}}, str(state)))
            check(STAYS, 'a launch binds the pinned approved Claude Code [%s]' % error,
                  error is None and launched['sha256'] == sha(approved_claude)
                  and launched['path'] == str(C.pinned_path(str(state), APPROVED)))
            _, error = attempt(lambda: C.pin(NEWER, versions=str(versions), state_root=str(state)))
            check(STAYS, 'the newer installed Claude Code is never pinned [%s]' % error,
                  error == 'engine_not_approved' and not C.pinned_path(str(state), NEWER).exists())
            _, error = attempt(lambda: C.bind({'executable': {'version': NEWER}}, str(state)))
            check(STAYS, 'a launch naming the newer Claude Code is refused [%s]' % error, error == 'engine_not_approved')
            launched, error = attempt(lambda: X.bind({'executable': str(approved_codex)}))
            check(STAYS, 'a launch binds the approved Codex binary [%s]' % error,
                  error is None and launched['sha256'] == sha(approved_codex) and launched['version'] == APPROVED)
            _, error = attempt(lambda: X.bind({'executable': str(newer_codex)}))
            check(STAYS, 'a launch naming the newer Codex binary is refused [%s]' % error, error == 'engine_not_approved')

            # approved/changed-bytes: the approved binaries change after approval.
            pinned = C.pinned_path(str(state), APPROVED)
            for engine, path in (('claude_code', pinned), ('codex', approved_codex)):
                before, mode = path.read_bytes(), path.stat().st_mode & 0o7777
                path.chmod(0o755)
                path.write_bytes(before + b'# changed after approval\n')
                path.chmod(mode)
                if engine == 'claude_code':
                    _, error = attempt(lambda: C.bind({'executable': {'version': APPROVED}}, str(state)))
                else:
                    _, error = attempt(lambda: X.bind({'executable': str(approved_codex)}))
                check(CHANGED, 'the %s binding of changed approved bytes is refused [%s]' % (engine, error),
                      error == 'engine_not_approved')
                path.chmod(0o755)
                path.write_bytes(before)
                path.chmod(mode)
            for engine, path in (('claude_code', approved_claude), ('codex', approved_codex)):
                before = path.read_bytes()
                path.write_bytes(before + b'# changed after approval\n')
                _, error = attempt(lambda: S.check(Refused))
                check(CHANGED, 'setup refuses the changed approved %s [%s]' % (engine, error),
                      error == 'engine_not_approved')
                path.write_bytes(before)
            _, error = attempt(lambda: S.check(Refused))
            check(CHANGED, 'with the approved bytes restored setup resolves them again [%s]' % error, error is None)
        finally:
            os.environ['PATH'] = original

    try:
        with tempfile.TemporaryDirectory(prefix='v275-') as directory:
            exercise(Path(directory))
    except Exception as error:  # noqa: BLE001
        for name in ROWS:
            check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0275_DETAILS'):
                print('  VELDO-0275 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0275 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0275 suite seconds: %.3f' % (time.monotonic() - started))


_v275_suite()
